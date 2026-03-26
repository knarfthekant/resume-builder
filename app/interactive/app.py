from __future__ import annotations

import argparse
import threading
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Callable

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, DynamicContainer, HSplit, Layout, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.styles import Style
from prompt_toolkit.widgets import Frame

from app.ai.client import AIConfigurationError
from app.ai.service import AISuggestionResult, AISelectionService
from app.ai.types import SelectedBullet, SelectedSection, SelectionSuggestion
from app.compiler import LatexCompilationError
from app.config import DEFAULT_CONFIG_PATH, load_config, save_config
from app.data_loader import list_relative_yaml_files, load_bullet_library, load_resume_profile
from app.env import get_openrouter_api_key, mask_api_key, save_openrouter_api_key
from app.interactive.rendering import (
    MARKUP_BOLD_CLOSE,
    MARKUP_BOLD_OPEN,
    MARKUP_KEY_CLOSE,
    MARKUP_KEY_OPEN,
    MARKUP_LABEL_CLOSE,
    MARKUP_LABEL_OPEN,
    box_lines,
    header_lines,
    render_ansi,
)
from app.models import (
    AppConfig,
    BulletLibrary,
    BulletOption,
    PipelineRequest,
    ResumeProfile,
    ResumeSelection,
)
from app.pipeline import run_generation
from app.selection import ManualSelectionService, SelectionValidationError


GenerationRunner = Callable[[PipelineRequest | None, AppConfig | None], object]


@dataclass(slots=True)
class MenuItem:
    value: str
    label: str


@dataclass(slots=True)
class SelectionStep:
    kind: str
    title: str
    entry_id: str | None
    options: list[BulletOption] = field(default_factory=list)
    max_selected: int = 1
    details: list[str] = field(default_factory=list)


@dataclass(slots=True)
class SessionState:
    profile_name: str
    bullet_library_name: str
    profile: ResumeProfile | None = None
    library: BulletLibrary | None = None
    selection: ResumeSelection | None = None
    job_description: str = ""
    ai_suggestion: SelectionSuggestion | None = None


MAIN_MENU_ITEMS = [
    MenuItem("generate_ai", "generate using ai"),
    MenuItem("generate_manual", "generate manually"),
    MenuItem("edit_config", "edit config"),
    MenuItem("exit", "exit"),
]

CONFIG_MENU_ITEMS = [
    MenuItem("compile_pdf", "toggle pdf compilation"),
    MenuItem("template_root", "edit template root"),
    MenuItem("data_root", "edit data root"),
    MenuItem("output_root", "edit output root"),
    MenuItem("openrouter_model", "edit openrouter model"),
    MenuItem("openrouter_base_url", "edit openrouter base url"),
    MenuItem("setup_ai", "run ai setup"),
    MenuItem("back", "back"),
]

AI_REVIEW_MENU_ITEMS = [
    MenuItem("accept", "accept and generate"),
    MenuItem("revise", "tell ai otherwise"),
    MenuItem("cancel", "cancel"),
]

APP_STYLE = Style.from_dict(
    {
        "frame.border": "#87afff",
        "frame.label": "bold #87afff",
    }
)


class ResumeCLIApp:
    def __init__(
        self,
        config_path: Path = DEFAULT_CONFIG_PATH,
        *,
        generation_runner: GenerationRunner = run_generation,
        ai_service: AISelectionService | None = None,
        api_key_loader: Callable[[Path], str | None] | None = None,
        api_key_saver: Callable[[str, Path], None] | None = None,
        env_path: Path | None = None,
    ) -> None:
        self.config_path = config_path
        self.config = load_config(config_path)
        self.env_path = env_path or (self.config_path.parent / ".env")
        self.generation_runner = generation_runner
        self.manual_selection = ManualSelectionService()
        self.ai_service = ai_service or AISelectionService(config=self.config, env_path=self.env_path)
        self.api_key_loader = api_key_loader or get_openrouter_api_key
        self.api_key_saver = api_key_saver or save_openrouter_api_key

        self.mode = "main_menu"
        self.selection_index = 0
        self.notice = "ready"

        self.choice_title = ""
        self.choice_items: list[MenuItem] = []
        self.choice_current = ""
        self.choice_submit_handler: Callable[[str], None] | None = None
        self.choice_cancel_handler: Callable[[], None] | None = None

        self.input_title = ""
        self.input_prompt = "value"
        self.input_multiline = False
        self.input_buffer = Buffer()
        self.input_submit_handler: Callable[[str], None] | None = None
        self.input_cancel_handler: Callable[[], None] | None = None

        self.message_title = ""
        self.message_body = ""
        self.message_close_handler: Callable[[], None] | None = None
        self.loading_title = ""
        self.loading_message = ""
        self.loading_frame_index = 0
        self.loading_active = False
        self.loading_frames = ["[=   ]", "[==  ]", "[=== ]", "[ ===]", "[  ==]", "[   =]"]

        self.session = SessionState(
            profile_name=self.config.active_profile,
            bullet_library_name=self.config.active_bullet_library,
        )
        self.manual_steps: list[SelectionStep] = []
        self.manual_step_index = 0

        self.application: Application[None] | None = None
        self.body_window: Window | None = None
        self.input_control = BufferControl(buffer=self.input_buffer)
        self.single_input_window: Window | None = None
        self.multi_input_window: Window | None = None

        self._enter_initial_mode()

    def reload(self) -> None:
        self.config = load_config(self.config_path)
        self.session.profile_name = self.config.active_profile
        self.session.bullet_library_name = self.config.active_bullet_library
        if not isinstance(self.ai_service, AISelectionService):
            return
        self.ai_service = AISelectionService(config=self.config, env_path=self.env_path)

    def save(self) -> None:
        save_config(self.config, self.config_path)
        if isinstance(self.ai_service, AISelectionService):
            self.ai_service = AISelectionService(config=self.config, env_path=self.env_path)

    def run(self) -> None:
        self.reload()
        self.application = self._build_application()
        if self.mode == "input":
            self._focus_input()
        else:
            self._focus_main()
        try:
            self.application.run()
        except EOFError:
            return

    def list_profiles(self) -> list[str]:
        profiles = list_relative_yaml_files(self.config.data_root, "profiles")
        if self.session.profile_name and self.session.profile_name not in profiles:
            profiles.append(self.session.profile_name)
        return sorted(profiles)

    def list_bullet_libraries(self) -> list[str]:
        libraries = list_relative_yaml_files(self.config.data_root, "bullets")
        if self.session.bullet_library_name and self.session.bullet_library_name not in libraries:
            libraries.append(self.session.bullet_library_name)
        return sorted(libraries)

    def current_main_menu_labels(self) -> list[str]:
        return [item.label for item in MAIN_MENU_ITEMS]

    def format_main_status(self) -> list[str]:
        api_key = self.api_key_loader(self.env_path)
        return [
            f"profile      : {self.config.active_profile}",
            f"bullets      : {self.config.active_bullet_library}",
            f"compile pdf  : {'yes' if self.config.compile_pdf else 'no'}",
            f"ai model     : {self.config.openrouter_model}",
            f"openrouter   : {mask_api_key(api_key)}",
            f"setup done   : {'yes' if self.config.setup_completed else 'no'}",
        ]

    def format_config_status(self) -> list[str]:
        api_key = self.api_key_loader(self.env_path)
        return [
            f"config file   : {self.config_path}",
            f"template root : {self.config.template_root}",
            f"data root     : {self.config.data_root}",
            f"output root   : {self.config.output_root}",
            f"compile pdf   : {'yes' if self.config.compile_pdf else 'no'}",
            f"ai model      : {self.config.openrouter_model}",
            f"base url      : {self.config.openrouter_base_url}",
            f"openrouter    : {mask_api_key(api_key)}",
            f"setup done    : {'yes' if self.config.setup_completed else 'no'}",
        ]

    def render_text(self) -> str:
        lines = header_lines()
        if self.mode == "setup_choice":
            lines.extend(self._render_setup_choice_lines())
        elif self.mode == "main_menu":
            lines.extend(self._render_main_menu_lines())
        elif self.mode == "config_menu":
            lines.extend(self._render_config_lines())
        elif self.mode == "choice":
            lines.extend(self._render_choice_lines())
        elif self.mode == "manual_step":
            lines.extend(self._render_manual_step_lines())
        elif self.mode == "input":
            lines.extend(self._render_input_lines())
        elif self.mode == "ai_review":
            lines.extend(self._render_ai_review_lines())
        elif self.mode == "loading":
            lines.extend(self._render_loading_lines())
        elif self.mode == "message":
            lines.extend(self._render_message_lines())
        else:
            lines.append("unknown mode")
        return "\n".join(lines)

    def render_ansi(self) -> str:
        return render_ansi(self.render_text(), message_mode=self.mode == "message")

    def move_selection(self, delta: int) -> None:
        item_count = 0
        if self.mode in {"setup_choice", "main_menu"}:
            item_count = len(MAIN_MENU_ITEMS) if self.mode == "main_menu" else len(self.choice_items)
        elif self.mode == "config_menu":
            item_count = len(CONFIG_MENU_ITEMS)
        elif self.mode in {"choice", "manual_step", "ai_review"}:
            if self.mode == "choice":
                item_count = len(self.choice_items)
            elif self.mode == "ai_review":
                item_count = len(AI_REVIEW_MENU_ITEMS)
            else:
                item_count = len(self._current_manual_items())

        if item_count:
            self.selection_index = (self.selection_index + delta) % item_count
            self._invalidate()

    def activate_current(self) -> bool:
        if self.mode == "setup_choice":
            selected = self.choice_items[self.selection_index].value
            assert self.choice_submit_handler is not None
            self.choice_submit_handler(selected)
            return True
        if self.mode == "main_menu":
            return self._activate_main_menu_item()
        if self.mode == "config_menu":
            self._activate_config_menu_item()
            return True
        if self.mode == "choice":
            if not self.choice_items or self.choice_submit_handler is None:
                return True
            selected = self.choice_items[self.selection_index].value
            self.choice_submit_handler(selected)
            return True
        if self.mode == "manual_step":
            self._advance_manual_step()
            return True
        if self.mode == "ai_review":
            self._activate_ai_review_item()
            return True
        if self.mode == "loading":
            return True
        if self.mode == "message":
            self.close_message()
            return True
        return True

    def submit_input(self, text: str | None = None) -> None:
        if self.mode != "input" or self.input_submit_handler is None:
            return
        self.input_submit_handler((text if text is not None else self.input_buffer.text).strip())

    def close_message(self) -> None:
        handler = self.message_close_handler or self._enter_main_menu
        self.message_close_handler = None
        handler()

    def toggle_manual_current_option(self) -> None:
        if self.mode != "manual_step":
            return
        step = self._current_manual_step()
        if step is None or step.kind == "summary":
            return
        selection = self._require_session_selection()
        option = step.options[self.selection_index]
        selected_ids = self._selected_ids_for_step(step, selection)
        if option.id in selected_ids:
            selected_ids.remove(option.id)
            self.notice = f"removed {option.id}"
        else:
            if len(selected_ids) >= step.max_selected:
                self.notice = f"max {step.max_selected} bullets for this entry"
                self._invalidate()
                return
            selected_ids.append(option.id)
            self.notice = f"selected {option.id}"
        self._write_selected_ids_for_step(step, selection, selected_ids)
        self._invalidate()

    def back(self) -> bool:
        if self.mode == "setup_choice":
            return False
        if self.mode == "main_menu":
            return False
        if self.mode == "config_menu":
            self._enter_main_menu("back to main menu")
            return True
        if self.mode == "loading":
            return True
        if self.mode == "choice":
            if self.choice_cancel_handler is not None:
                self.choice_cancel_handler()
            return True
        if self.mode == "manual_step":
            self._go_back_manual_step()
            return True
        if self.mode == "input":
            if self.input_cancel_handler is not None:
                self.input_cancel_handler()
            return True
        if self.mode == "ai_review":
            self._enter_main_menu("cancelled ai review")
            return True
        if self.mode == "message":
            self.close_message()
            return True
        return True

    def _enter_initial_mode(self) -> None:
        api_key = self.api_key_loader(self.env_path)
        if not self.config.setup_completed:
            self._start_setup_flow(existing_key=api_key)
        else:
            self._enter_main_menu()

    def _start_setup_flow(self, *, existing_key: str | None) -> None:
        if existing_key:
            masked = mask_api_key(existing_key)

            def _submit(value: str) -> None:
                if value == "keep":
                    self.config.setup_completed = True
                    self.save()
                    self._enter_main_menu("ai setup saved")
                    return
                self._enter_input_mode(
                    title="openrouter api key",
                    prompt="api key",
                    current_text="",
                    multiline=False,
                    submit_handler=self._submit_api_key,
                    cancel_handler=lambda: self._start_setup_flow(existing_key=existing_key),
                )

            self.mode = "setup_choice"
            self.choice_title = "ai setup"
            self.choice_items = [
                MenuItem("keep", f"keep detected key ({masked})"),
                MenuItem("replace", "replace detected key"),
            ]
            self.choice_current = self.choice_items[0].value
            self.choice_submit_handler = _submit
            self.choice_cancel_handler = None
            self.selection_index = 0
            self.notice = "complete ai setup to continue"
            self._focus_main()
            self._invalidate()
            return

        self._enter_input_mode(
            title="openrouter api key",
            prompt="api key",
            current_text="",
            multiline=False,
            submit_handler=self._submit_api_key,
            cancel_handler=self._cancel_initial_setup,
        )
        self.notice = "enter your openrouter api key"

    def _cancel_initial_setup(self) -> None:
        self.open_message(
            "setup required",
            "AI setup is required before using the interactive CLI.\n\nPress enter to exit.",
            close_handler=lambda: self.application.exit() if self.application is not None else None,
        )

    def _submit_api_key(self, value: str) -> None:
        if not value:
            self.notice = "api key cannot be empty"
            self._invalidate()
            return
        self.api_key_saver(value, self.env_path)
        self.config.setup_completed = True
        self.save()
        self._enter_main_menu("ai setup saved")

    def _enter_main_menu(self, notice: str | None = None) -> None:
        self.mode = "main_menu"
        self.selection_index = 0
        if notice is not None:
            self.notice = notice
        self._reset_overlay_state()
        self._focus_main()
        self._invalidate()

    def _enter_config_menu(self, notice: str | None = None) -> None:
        self.mode = "config_menu"
        self.selection_index = 0
        if notice is not None:
            self.notice = notice
        self._reset_overlay_state()
        self._focus_main()
        self._invalidate()

    def _reset_overlay_state(self) -> None:
        self.choice_title = ""
        self.choice_items = []
        self.choice_current = ""
        self.choice_submit_handler = None
        self.choice_cancel_handler = None
        self.input_title = ""
        self.input_prompt = "value"
        self.input_multiline = False
        self.input_buffer.set_document(Document(text="", cursor_position=0), bypass_readonly=True)
        self.input_submit_handler = None
        self.input_cancel_handler = None
        self.message_title = ""
        self.message_body = ""
        self.message_close_handler = None
        self.loading_title = ""
        self.loading_message = ""
        self.loading_frame_index = 0

    def _activate_main_menu_item(self) -> bool:
        action = MAIN_MENU_ITEMS[self.selection_index].value
        if action == "generate_ai":
            self._start_profile_choice(flow="ai")
            return True
        if action == "generate_manual":
            self._start_profile_choice(flow="manual")
            return True
        if action == "edit_config":
            self._enter_config_menu()
            return True
        if action == "exit":
            return False
        raise ValueError(f"Unknown main menu action: {action}")

    def _activate_config_menu_item(self) -> None:
        action = CONFIG_MENU_ITEMS[self.selection_index].value
        if action == "compile_pdf":
            self.config.compile_pdf = not self.config.compile_pdf
            self.save()
            self._enter_config_menu(f"compile pdf set to {'yes' if self.config.compile_pdf else 'no'}")
            return
        if action in {"template_root", "data_root", "output_root"}:
            current_value = str(getattr(self.config, action))
            self._enter_input_mode(
                title=f"edit {action.replace('_', ' ')}",
                prompt="path",
                current_text=current_value,
                multiline=False,
                submit_handler=lambda value, field=action: self._submit_path_update(field, value),
                cancel_handler=lambda: self._enter_config_menu("cancelled"),
            )
            return
        if action in {"openrouter_model", "openrouter_base_url"}:
            current_value = str(getattr(self.config, action))
            self._enter_input_mode(
                title=f"edit {action.replace('_', ' ')}",
                prompt="value",
                current_text=current_value,
                multiline=False,
                submit_handler=lambda value, field=action: self._submit_config_value(field, value),
                cancel_handler=lambda: self._enter_config_menu("cancelled"),
            )
            return
        if action == "setup_ai":
            self._start_setup_flow(existing_key=self.api_key_loader(self.env_path))
            return
        if action == "back":
            self._enter_main_menu("back to main menu")
            return
        raise ValueError(f"Unknown config action: {action}")

    def _submit_path_update(self, field_name: str, value: str) -> None:
        if not value:
            self._enter_config_menu("no change applied")
            return
        resolved = Path(value).expanduser().resolve()
        setattr(self.config, field_name, resolved)
        self.save()
        self._enter_config_menu(f"{field_name} updated")

    def _submit_config_value(self, field_name: str, value: str) -> None:
        if not value:
            self._enter_config_menu("no change applied")
            return
        setattr(self.config, field_name, value)
        self.save()
        self._enter_config_menu(f"{field_name} updated")

    def _start_profile_choice(self, *, flow: str) -> None:
        profile_items = [MenuItem(item, item) for item in self.list_profiles()]
        if not profile_items:
            self.open_message("missing profiles", "No profile YAML files were found under data/profiles.")
            return
        current = self.session.profile_name if flow in {"manual", "ai"} else self.config.active_profile
        self._enter_choice_mode(
            title="select profile",
            items=profile_items,
            current=current,
            submit_handler=lambda value, active_flow=flow: self._submit_profile_choice(active_flow, value),
            cancel_handler=lambda: self._enter_main_menu("cancelled"),
        )

    def _submit_profile_choice(self, flow: str, value: str) -> None:
        self.session.profile_name = value
        self.config.active_profile = value
        self.save()
        self._start_library_choice(flow=flow)

    def _start_library_choice(self, *, flow: str) -> None:
        library_items = [MenuItem(item, item) for item in self.list_bullet_libraries()]
        if not library_items:
            self.open_message("missing bullet libraries", "No bullet YAML files were found under data/bullets.")
            return
        current = self.session.bullet_library_name
        self._enter_choice_mode(
            title="select bullet library",
            items=library_items,
            current=current,
            submit_handler=lambda value, active_flow=flow: self._submit_library_choice(active_flow, value),
            cancel_handler=lambda active_flow=flow: self._start_profile_choice(flow=active_flow),
        )

    def _submit_library_choice(self, flow: str, value: str) -> None:
        self.session.bullet_library_name = value
        self.config.active_bullet_library = value
        self.save()
        if flow == "manual":
            self._start_manual_selection()
            return
        self._start_ai_job_description()

    def _start_manual_selection(self) -> None:
        try:
            self._load_session_content()
            assert self.session.profile is not None
            assert self.session.library is not None
            self.session.selection = self.manual_selection.build_default_selection(self.session.profile, self.session.library)
            self.manual_steps = self._build_manual_steps(self.session.profile, self.session.library)
        except Exception as exc:  # noqa: BLE001
            self.open_message("manual generation failed", str(exc))
            return

        if not self.manual_steps:
            self._generate_current_session("generation complete")
            return

        self.mode = "manual_step"
        self.manual_step_index = 0
        self.selection_index = 0
        self.notice = "adjust selections and press enter to continue"
        self._focus_main()
        self._invalidate()

    def _start_ai_job_description(self) -> None:
        try:
            self._load_session_content()
        except Exception as exc:  # noqa: BLE001
            self.open_message("ai generation failed", str(exc))
            return
        self._enter_input_mode(
            title="job description",
            prompt="jd",
            current_text=self.session.job_description,
            multiline=True,
            submit_handler=self._submit_job_description,
            cancel_handler=lambda: self._start_library_choice(flow="ai"),
        )
        self.notice = "paste the job description, then press ctrl+s"

    def _submit_job_description(self, value: str) -> None:
        if not value:
            self.notice = "job description cannot be empty"
            self._invalidate()
            return
        self.session.job_description = value
        self._request_ai_suggestion(feedback="")

    def _request_ai_suggestion(self, *, feedback: str) -> None:
        assert self.session.profile is not None
        assert self.session.library is not None

        def _worker() -> AISuggestionResult:
            return self.ai_service.suggest(
                self.session.profile,
                self.session.library,
                self.session.job_description,
                feedback=feedback,
                previous_suggestion=self.session.ai_suggestion,
            )

        self._run_waiting_task(
            title="ai selection",
            message="matching job requirements to bullet ids",
            worker=_worker,
            success_handler=self._enter_ai_review,
            error_title="ai selection failed",
        )

    def _enter_ai_review(self, result: AISuggestionResult) -> None:
        self.session.selection = result.selection
        self.session.ai_suggestion = result.suggestion
        self.mode = "ai_review"
        self.selection_index = 0
        self.notice = "review the ai suggestion"
        self._focus_main()
        self._invalidate()

    def _activate_ai_review_item(self) -> None:
        action = AI_REVIEW_MENU_ITEMS[self.selection_index].value
        if action == "accept":
            self._generate_current_session("generation complete")
            return
        if action == "revise":
            self._enter_input_mode(
                title="tell ai otherwise",
                prompt="feedback",
                current_text="",
                multiline=True,
                submit_handler=self._submit_ai_feedback,
                cancel_handler=lambda: self._enter_ai_review(
                    AISuggestionResult(
                        suggestion=self.session.ai_suggestion or SelectionSuggestion(),
                        selection=self.session.selection or ResumeSelection(),
                    )
                ),
            )
            self.notice = "describe what the AI should change, then press ctrl+s"
            return
        if action == "cancel":
            self._enter_main_menu("cancelled ai generation")
            return
        raise ValueError(f"Unknown ai review action: {action}")

    def _submit_ai_feedback(self, value: str) -> None:
        if not value:
            self.notice = "feedback cannot be empty"
            self._invalidate()
            return
        self._request_ai_suggestion(feedback=value)

    def _build_manual_steps(self, profile: ResumeProfile, library: BulletLibrary) -> list[SelectionStep]:
        steps: list[SelectionStep] = []
        if library.summary_options:
            steps.append(
                SelectionStep(
                    kind="summary",
                    title="choose summary",
                    entry_id=None,
                    options=library.summary_options,
                    max_selected=1,
                    details=["select one summary variant"],
                )
            )

        for entry in profile.experience_entries:
            options = library.experience.get(entry.id, [])
            if not options:
                continue
            steps.append(
                SelectionStep(
                    kind="experience",
                    title=f"{entry.title} | {entry.company}",
                    entry_id=entry.id,
                    options=options,
                    max_selected=entry.max_bullets,
                    details=[
                        f"location: {entry.location}",
                        f"dates: {entry.date_range}",
                        f"pick {entry.min_bullets}-{entry.max_bullets} bullets when this entry is included",
                    ],
                )
            )

        for entry in profile.project_entries:
            options = library.projects.get(entry.id, [])
            if not options:
                continue
            details = [f"tech: {entry.tech_stack}", f"pick {entry.min_bullets}-{entry.max_bullets} bullets when included"]
            if entry.link_url:
                details.insert(1, f"link: {entry.link_url}")
            steps.append(
                SelectionStep(
                    kind="projects",
                    title=entry.name,
                    entry_id=entry.id,
                    options=options,
                    max_selected=entry.max_bullets,
                    details=details,
                )
            )
        return steps

    def _advance_manual_step(self) -> None:
        step = self._current_manual_step()
        if step is None:
            self._enter_main_menu()
            return
        selection = self._require_session_selection()
        if step.kind == "summary":
            selected = step.options[self.selection_index].id
            selection.summary_id = selected
            self.notice = f"summary set to {selected}"
        else:
            selected_ids = self._selected_ids_for_step(step, selection)
            if len(selected_ids) > step.max_selected:
                self.notice = f"max {step.max_selected} bullets for this entry"
                self._invalidate()
                return

        if self.manual_step_index >= len(self.manual_steps) - 1:
            self._generate_current_session("generation complete")
            return

        self.manual_step_index += 1
        self.selection_index = 0
        self.notice = "selection saved"
        self._invalidate()

    def _go_back_manual_step(self) -> None:
        if self.manual_step_index == 0:
            self._enter_main_menu("cancelled manual generation")
            return
        self.manual_step_index -= 1
        self.selection_index = 0
        self.notice = "back to previous step"
        self._invalidate()

    def _generate_current_session(self, title: str) -> None:
        def _worker():
            return self.generation_runner(
                PipelineRequest(
                    profile_name=self.session.profile_name,
                    bullet_library_name=self.session.bullet_library_name,
                    selection=self.session.selection,
                    job_description=self.session.job_description or None,
                ),
                self.config,
            )
        message = "rendering LaTeX and compiling PDF" if self.config.compile_pdf else "rendering LaTeX"
        self._run_waiting_task(
            title="resume generation",
            message=message,
            worker=_worker,
            success_handler=lambda result, success_title=title: self._handle_generation_success(success_title, result),
            error_title="generation failed",
        )

    def _handle_generation_success(self, title: str, result) -> None:  # noqa: ANN001
        pdf_line = str(result.pdf_path) if getattr(result, "pdf_path", None) else "not generated"
        self.open_message(
            title,
            "\n".join(
                [
                    f"output directory : {result.output_dir}",
                    f"rendered latex   : {result.rendered_main}",
                    f"pdf              : {pdf_line}",
                ]
            ),
        )

    def _run_waiting_task(
        self,
        *,
        title: str,
        message: str,
        worker: Callable[[], object],
        success_handler: Callable[[object], None],
        error_title: str,
    ) -> None:
        if self.application is None:
            try:
                result = worker()
            except (AIConfigurationError, SelectionValidationError, LatexCompilationError) as exc:
                self.open_message(error_title, str(exc))
                return
            except Exception as exc:  # noqa: BLE001
                self.open_message(error_title, str(exc))
                return
            success_handler(result)
            return

        self.mode = "loading"
        self.loading_title = title
        self.loading_message = message
        self.loading_frame_index = 0
        self.loading_active = True
        self.notice = message
        self._focus_main()
        self._invalidate()

        def _spinner() -> None:
            while self.loading_active:
                time.sleep(0.12)
                if not self.loading_active:
                    break
                self.loading_frame_index = (self.loading_frame_index + 1) % len(self.loading_frames)
                self._invalidate()

        def _runner() -> None:
            try:
                result = worker()
            except (AIConfigurationError, SelectionValidationError, LatexCompilationError) as exc:
                self.loading_active = False
                self.open_message(error_title, str(exc))
                return
            except Exception as exc:  # noqa: BLE001
                self.loading_active = False
                self.open_message(error_title, str(exc))
                return

            self.loading_active = False
            success_handler(result)

        threading.Thread(target=_spinner, daemon=True).start()
        threading.Thread(target=_runner, daemon=True).start()

    def open_message(
        self,
        title: str,
        body: str,
        *,
        close_handler: Callable[[], None] | None = None,
    ) -> None:
        self.mode = "message"
        self.message_title = title
        self.message_body = body
        self.message_close_handler = close_handler or (lambda: self._enter_main_menu("ready"))
        self._focus_main()
        self._invalidate()

    def _load_session_content(self) -> None:
        profile_path = self.config.data_root / self.session.profile_name
        library_path = self.config.data_root / self.session.bullet_library_name
        self.session.profile = load_resume_profile(profile_path)
        self.session.library = load_bullet_library(library_path)

    def _enter_choice_mode(
        self,
        *,
        title: str,
        items: list[MenuItem],
        current: str,
        submit_handler: Callable[[str], None],
        cancel_handler: Callable[[], None],
    ) -> None:
        self.mode = "choice"
        self.choice_title = title
        self.choice_items = items
        self.choice_current = current
        self.choice_submit_handler = submit_handler
        self.choice_cancel_handler = cancel_handler
        current_values = [item.value for item in items]
        self.selection_index = current_values.index(current) if current in current_values else 0
        self._focus_main()
        self._invalidate()

    def _enter_input_mode(
        self,
        *,
        title: str,
        prompt: str,
        current_text: str,
        multiline: bool,
        submit_handler: Callable[[str], None],
        cancel_handler: Callable[[], None],
    ) -> None:
        self.mode = "input"
        self.input_title = title
        self.input_prompt = prompt
        self.input_multiline = multiline
        self.input_submit_handler = submit_handler
        self.input_cancel_handler = cancel_handler
        self.input_buffer.set_document(
            Document(text=current_text, cursor_position=len(current_text)),
            bypass_readonly=True,
        )
        self._focus_input()
        self._invalidate()

    def _render_setup_choice_lines(self) -> list[str]:
        lines = [
            "A detected OpenRouter key was found. Keep it or replace it before entering the app.",
            "",
            f"detected key : {mask_api_key(self.api_key_loader(self.env_path))}",
        ]
        action_lines = self._menu_lines(self.choice_items)
        return box_lines("ai setup", lines) + [""] + box_lines("actions", action_lines) + [
            "",
            "keys: up/down or j/k move, enter select, q quit",
            f"status: {self.notice}",
        ]

    def _render_main_menu_lines(self) -> list[str]:
        status_box = box_lines("current defaults", self.format_main_status())
        action_box = box_lines("actions", self._menu_lines(MAIN_MENU_ITEMS))
        return status_box + [""] + action_box + [
            "",
            "keys: up/down or j/k move, enter select, q quit",
            f"status: {self.notice}",
        ]

    def _render_config_lines(self) -> list[str]:
        config_box = box_lines("current config", self.format_config_status())
        action_box = box_lines("edit config", self._menu_lines(CONFIG_MENU_ITEMS))
        return config_box + [""] + action_box + [
            "",
            "keys: up/down or j/k move, enter select, esc back",
            f"status: {self.notice}",
        ]

    def _render_choice_lines(self) -> list[str]:
        current_line = [f"current: {self.choice_current}", ""]
        choice_box = box_lines(self.choice_title, current_line + self._menu_lines(self.choice_items))
        return choice_box + [
            "",
            "keys: up/down or j/k move, enter select, esc back",
            f"status: {self.notice}",
        ]

    def _render_manual_step_lines(self) -> list[str]:
        step = self._current_manual_step()
        if step is None:
            return ["no manual steps loaded"]
        selection = self._require_session_selection()
        header_box = box_lines(
            "manual generation",
            [
                f"profile      : {self.session.profile_name}",
                f"bullets      : {self.session.bullet_library_name}",
                f"step         : {self.manual_step_index + 1}/{len(self.manual_steps)}",
                f"selection    : {self._selection_summary(step, selection)}",
            ],
        )

        option_lines: list[str] = []
        if step.details:
            option_lines.extend(step.details)
            option_lines.append("")
        for index, option in enumerate(step.options):
            pointer = ">" if index == self.selection_index else " "
            marker = self._option_marker(step, option, selection)
            label = self._truncate(option.text.replace("\n", " "), 102)
            option_lines.append(f"{pointer} {marker} {option.id} :: {label}")

        keys_line = (
            "keys: up/down or j/k move, enter choose, esc back"
            if step.kind == "summary"
            else "keys: up/down or j/k move, space toggle, enter continue, esc back"
        )
        return header_box + [""] + box_lines(step.title, option_lines) + [
            "",
            keys_line,
            f"status: {self.notice}",
        ]

    def _render_input_lines(self) -> list[str]:
        info_lines = [
            f"{MARKUP_LABEL_OPEN}prompt{MARKUP_LABEL_CLOSE} : {self.input_prompt}",
            f"{MARKUP_LABEL_OPEN}mode{MARKUP_LABEL_CLOSE}   : {'multiline' if self.input_multiline else 'single-line'}",
            "",
            "type below inside the input box" if not self.input_multiline else "type or paste inside the input box",
        ]
        key_line = "keys: enter save, esc back" if not self.input_multiline else "keys: ctrl+s save, esc back"
        return box_lines(self.input_title, info_lines) + ["", key_line, f"status: {self.notice}"]

    def _render_ai_review_lines(self) -> list[str]:
        if self.session.ai_suggestion is None or self.session.library is None or self.session.profile is None:
            return ["no ai suggestion loaded"]
        suggestion_box = box_lines("ai suggestion", self._format_ai_suggestion_lines())
        action_box = box_lines("actions", self._menu_lines(AI_REVIEW_MENU_ITEMS))
        return suggestion_box + [""] + action_box + [
            "",
            "keys: up/down or j/k move, enter select, esc back",
            f"status: {self.notice}",
        ]

    def _render_message_lines(self) -> list[str]:
        return box_lines(self.message_title, self.message_body.splitlines() or [""]) + [
            "",
            "keys: enter back, q quit",
            f"status: {self.notice}",
        ]

    def _render_loading_lines(self) -> list[str]:
        return box_lines(
            self.loading_title,
            [
                f"{MARKUP_BOLD_OPEN}{self.loading_frames[self.loading_frame_index]}{MARKUP_BOLD_CLOSE} {self.loading_message}",
                "",
                self._loading_bar(),
                "",
                "Please wait. The interface will resume automatically.",
            ],
        ) + ["", f"status: {self.notice}"]

    def _menu_lines(self, items: list[MenuItem]) -> list[str]:
        lines: list[str] = []
        for index, item in enumerate(items):
            prefix = "> " if index == self.selection_index else "  "
            lines.append(f"{prefix}{item.label}")
        return lines

    def _format_ai_suggestion_lines(self) -> list[str]:
        assert self.session.ai_suggestion is not None
        assert self.session.profile is not None
        assert self.session.library is not None
        lines: list[str] = []
        suggestion = self.session.ai_suggestion
        lines.append(f"{MARKUP_LABEL_OPEN}profile{MARKUP_LABEL_CLOSE} : {self.session.profile_name}")
        lines.append(f"{MARKUP_LABEL_OPEN}library{MARKUP_LABEL_CLOSE} : {self.session.bullet_library_name}")
        lines.append(
            f"{MARKUP_LABEL_OPEN}job desc{MARKUP_LABEL_CLOSE}: "
            f"{self._truncate(self.session.job_description.replace(chr(10), ' '), 96)}"
        )
        lines.append("")

        if suggestion.summary_id:
            summary = self._find_bullet_option(self.session.library.summary_options, suggestion.summary_id)
            lines.append(f"{MARKUP_BOLD_OPEN}summary{MARKUP_BOLD_CLOSE}")
            lines.append(f"  {MARKUP_KEY_OPEN}{suggestion.summary_id}{MARKUP_KEY_CLOSE}")
            lines.append(f"  {self._truncate(suggestion.summary_rewrite or summary.text, 96)}")
            lines.append("")

        lines.extend(self._format_ai_section_lines("experience", suggestion.experience, kind="experience"))
        lines.extend(self._format_ai_section_lines("projects", suggestion.projects, kind="projects"))
        if suggestion.notes:
            lines.append(f"{MARKUP_BOLD_OPEN}notes{MARKUP_BOLD_CLOSE}")
            lines.append(f"  {self._truncate(suggestion.notes, 100)}")
        return lines

    def _format_ai_section_lines(self, label: str, sections: list[SelectedSection], *, kind: str) -> list[str]:
        lines: list[str] = []
        if not sections:
            return lines
        lines.append(f"{MARKUP_BOLD_OPEN}{label}{MARKUP_BOLD_CLOSE}")
        for section in sections:
            lines.append(
                f"  {MARKUP_LABEL_OPEN}{self._display_entry_name(kind, section.entry_id)}{MARKUP_LABEL_CLOSE}"
                f" ({section.entry_id})"
            )
            for bullet in section.bullets:
                lines.extend(self._format_ai_bullet_lines(bullet))
        lines.append("")
        return lines

    def _format_ai_bullet_lines(self, bullet: SelectedBullet) -> list[str]:
        assert self.session.library is not None
        bullet_text = self._lookup_bullet_text(bullet.bullet_id)
        lines = [
            f"    - {MARKUP_KEY_OPEN}{bullet.bullet_id}{MARKUP_KEY_CLOSE} "
            f"{self._truncate(bullet.rewritten_text or bullet_text, 84)}"
        ]
        if bullet.rationale:
            lines.append(
                f"      {MARKUP_LABEL_OPEN}why{MARKUP_LABEL_CLOSE}: "
                f"{self._truncate(bullet.rationale, 84)}"
            )
        return lines

    def _display_entry_name(self, kind: str, entry_id: str) -> str:
        if self.session.profile is None:
            return entry_id
        if kind == "experience":
            for entry in self.session.profile.experience_entries:
                if entry.id == entry_id:
                    return f"{entry.title} @ {entry.company}"
            return entry_id
        for entry in self.session.profile.project_entries:
            if entry.id == entry_id:
                return entry.name
        return entry_id

    def _lookup_bullet_text(self, bullet_id: str) -> str:
        assert self.session.library is not None
        for option in self.session.library.summary_options:
            if option.id == bullet_id:
                return option.text
        for options in [*self.session.library.experience.values(), *self.session.library.projects.values()]:
            for option in options:
                if option.id == bullet_id:
                    return option.text
        return bullet_id

    def _selection_summary(self, step: SelectionStep, selection: ResumeSelection) -> str:
        if step.kind == "summary":
            return selection.summary_id or "(none)"
        selected = self._selected_ids_for_step(step, selection)
        return f"{len(selected)}/{step.max_selected} selected"

    def _option_marker(self, step: SelectionStep, option: BulletOption, selection: ResumeSelection) -> str:
        if step.kind == "summary":
            return "(x)" if selection.summary_id == option.id else "( )"
        selected = self._selected_ids_for_step(step, selection)
        return "[x]" if option.id in selected else "[ ]"

    def _current_manual_step(self) -> SelectionStep | None:
        if not self.manual_steps:
            return None
        return self.manual_steps[self.manual_step_index]

    def _current_manual_items(self) -> list[MenuItem]:
        step = self._current_manual_step()
        if step is None:
            return []
        return [MenuItem(option.id, option.id) for option in step.options]

    def _selected_ids_for_step(self, step: SelectionStep, selection: ResumeSelection) -> list[str]:
        if step.kind == "summary":
            return [selection.summary_id] if selection.summary_id else []
        if step.kind == "experience":
            return list(selection.experience.get(step.entry_id or "", []))
        return list(selection.projects.get(step.entry_id or "", []))

    def _write_selected_ids_for_step(
        self,
        step: SelectionStep,
        selection: ResumeSelection,
        selected_ids: list[str],
    ) -> None:
        if step.kind == "experience":
            selection.experience[step.entry_id or ""] = selected_ids
        elif step.kind == "projects":
            selection.projects[step.entry_id or ""] = selected_ids

    def _require_session_selection(self) -> ResumeSelection:
        if self.session.selection is None:
            self.session.selection = ResumeSelection()
        return self.session.selection

    def _find_bullet_option(self, options: list[BulletOption], option_id: str) -> BulletOption:
        for option in options:
            if option.id == option_id:
                return option
        raise SelectionValidationError(f"Unknown option: {option_id}")

    def _truncate(self, text: str, width: int) -> str:
        collapsed = " ".join(text.split())
        if len(collapsed) <= width:
            return collapsed
        return collapsed[: width - 3] + "..."

    def _loading_bar(self) -> str:
        filled = min(10, self.loading_frame_index + 3)
        return "[" + ("=" * filled).ljust(10, ".") + "]"

    def _input_window_height(self) -> int:
        if not self.input_multiline:
            return 1
        line_count = self.input_buffer.text.count("\n") + 1
        return max(4, min(10, line_count + 1))

    def _invalidate(self) -> None:
        if self.application is not None:
            self.application.invalidate()

    def _focus_main(self) -> None:
        if self.application is not None and self.body_window is not None:
            self.application.layout.focus(self.body_window)

    def _focus_input(self) -> None:
        if self.application is None:
            return
        target = self.multi_input_window if self.input_multiline else self.single_input_window
        if target is not None:
            self.application.layout.focus(target)

    def _build_key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        menu_modes = Condition(lambda: self.mode in {"setup_choice", "main_menu", "config_menu", "choice", "manual_step", "ai_review"})
        message_mode = Condition(lambda: self.mode == "message")
        single_input_mode = Condition(lambda: self.mode == "input" and not self.input_multiline)
        multi_input_mode = Condition(lambda: self.mode == "input" and self.input_multiline)
        non_input_mode = Condition(lambda: self.mode not in {"input", "loading"})
        manual_mode = Condition(lambda: self.mode == "manual_step")

        @bindings.add("up", filter=menu_modes)
        @bindings.add("k", filter=menu_modes)
        def _move_up(event) -> None:
            del event
            self.move_selection(-1)

        @bindings.add("down", filter=menu_modes)
        @bindings.add("j", filter=menu_modes)
        def _move_down(event) -> None:
            del event
            self.move_selection(1)

        @bindings.add("enter", filter=menu_modes)
        @bindings.add("enter", filter=message_mode)
        def _enter(event) -> None:
            if not self.activate_current():
                event.app.exit()

        @bindings.add("enter", filter=single_input_mode)
        def _submit_single_line(event) -> None:
            del event
            self.submit_input()

        @bindings.add("c-s", filter=multi_input_mode)
        def _submit_multi_line(event) -> None:
            del event
            self.submit_input()

        @bindings.add(" ", filter=manual_mode)
        def _toggle_manual(event) -> None:
            del event
            self.toggle_manual_current_option()

        @bindings.add("escape")
        def _escape(event) -> None:
            handled = self.back()
            if not handled:
                event.app.exit()

        @bindings.add("q", filter=non_input_mode)
        def _quit(event) -> None:
            event.app.exit()

        @bindings.add("c-c")
        def _ctrl_c(event) -> None:
            event.app.exit()

        return bindings

    def _build_application(self) -> Application[None]:
        body_control = FormattedTextControl(lambda: ANSI(self.render_ansi()))
        self.body_window = Window(content=body_control, always_hide_cursor=True, dont_extend_height=True)
        self.single_input_window = Window(content=self.input_control, height=1)
        self.multi_input_window = Window(content=self.input_control, height=8, wrap_lines=True)

        def _build_single_input_frame():
            return Frame(self.single_input_window, title=self.input_title, style="class:frame")

        def _build_multi_input_frame():
            self.multi_input_window.height = self._input_window_height()
            return Frame(self.multi_input_window, title=self.input_title, style="class:frame")

        root = HSplit(
            [
                self.body_window,
                ConditionalContainer(
                    content=DynamicContainer(_build_single_input_frame),
                    filter=Condition(lambda: self.mode == "input" and not self.input_multiline),
                ),
                ConditionalContainer(
                    content=DynamicContainer(_build_multi_input_frame),
                    filter=Condition(lambda: self.mode == "input" and self.input_multiline),
                ),
            ]
        )

        return Application(
            layout=Layout(root, focused_element=self.body_window),
            key_bindings=self._build_key_bindings(),
            full_screen=True,
            mouse_support=False,
            style=APP_STYLE,
        )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resume-builder")
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser("generate", help="Render and compile a resume.")
    generate_parser.add_argument("--profile", help="Relative path under data/ to the profile YAML.")
    generate_parser.add_argument(
        "--bullet-library",
        "--bullets",
        dest="bullet_library",
        help="Relative path under data/ to the bullet library YAML.",
    )
    generate_parser.add_argument("--job-description", help="Optional job description stored with the run request.")
    generate_parser.add_argument(
        "--no-compile",
        action="store_true",
        help="Render the LaTeX output without compiling a PDF.",
    )

    cli_parser = subparsers.add_parser("cli", aliases=["tui"], help="Launch the interactive CLI.")
    cli_parser.add_argument(
        "--config",
        type=Path,
        default=DEFAULT_CONFIG_PATH,
        help="Path to the YAML config file.",
    )
    return parser


def main(argv: list[str] | None = None) -> None:
    parser = build_parser()
    args = parser.parse_args(argv)

    if args.command == "generate":
        try:
            result = run_generation(
                PipelineRequest(
                    profile_name=args.profile,
                    bullet_library_name=args.bullet_library,
                    job_description=args.job_description,
                    compile_pdf=False if args.no_compile else None,
                )
            )
        except LatexCompilationError as exc:
            parser.exit(1, f"{exc}\n")
        print(f"Output directory: {result.output_dir}")
        print(f"Rendered LaTeX: {result.rendered_main}")
        if result.pdf_path:
            print(f"PDF: {result.pdf_path}")
        else:
            print("PDF: not generated")
        return

    if args.command in {None, "cli", "tui"}:
        config_path = getattr(args, "config", DEFAULT_CONFIG_PATH)
        ResumeCLIApp(config_path=config_path).run()
        return

    parser.error(f"Unknown command: {args.command}")
