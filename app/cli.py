from __future__ import annotations

import argparse
from pathlib import Path

from prompt_toolkit.application import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.document import Document
from prompt_toolkit.filters import Condition
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.layout import ConditionalContainer, HSplit, Layout, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl

from app.config import DEFAULT_CONFIG_PATH, load_config, save_config
from app.data_loader import list_relative_yaml_files
from app.models import PipelineRequest
from app.pipeline import run_generation

MENU_ITEMS: list[tuple[str, str]] = [
    ("generate", "generate resume"),
    ("profile", "select active profile"),
    ("bullets", "select bullets catalog"),
    ("compile", "toggle pdf compilation"),
    ("template_root", "edit template root"),
    ("data_root", "edit data root"),
    ("output_root", "edit output root"),
    ("show", "show current config"),
    ("exit", "exit"),
]

ANSI_RESET = "\x1b[0m"
ANSI_TITLE = "\x1b[38;5;111m"
ANSI_ACCENT = "\x1b[38;5;111m"
ANSI_MUTED = "\x1b[38;5;245m"
ANSI_NOTICE = "\x1b[38;5;114m"
ANSI_SELECTED = "\x1b[1;38;5;16;48;5;117m"
ANSI_MESSAGE = "\x1b[38;5;223m"
TITLE_ART = [
"██████╗░███████╗░██████╗██╗░░░██╗███╗░░░███╗███████╗  ██████╗░██╗░░░██╗██╗██╗░░░░░██████╗░███████╗██████╗░",
"██╔══██╗██╔════╝██╔════╝██║░░░██║████╗░████║██╔════╝  ██╔══██╗██║░░░██║██║██║░░░░░██╔══██╗██╔════╝██╔══██╗",
"██████╔╝█████╗░░╚█████╗░██║░░░██║██╔████╔██║█████╗░░  ██████╦╝██║░░░██║██║██║░░░░░██║░░██║█████╗░░██████╔╝",
"██╔══██╗██╔══╝░░░╚═══██╗██║░░░██║██║╚██╔╝██║██╔══╝░░  ██╔══██╗██║░░░██║██║██║░░░░░██║░░██║██╔══╝░░██╔══██╗",
"██║░░██║███████╗██████╔╝╚██████╔╝██║░╚═╝░██║███████╗  ██████╦╝╚██████╔╝██║███████╗██████╔╝███████╗██║░░██║",
"╚═╝░░╚═╝╚══════╝╚═════╝░░╚═════╝░╚═╝░░░░░╚═╝╚══════╝  ╚═════╝░░╚═════╝░╚═╝╚══════╝╚═════╝░╚══════╝╚═╝░░╚═╝",
]
TITLE_RULE = "─" * 90


class ResumeBuilderCLI:
    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = config_path
        self.config = load_config(config_path)

        self.mode = "menu"
        self.selection_index = 0
        self.notice = "ready"

        self.choice_action: str | None = None
        self.choice_title = ""
        self.choice_items: list[str] = []
        self.choice_current = ""

        self.input_field: str | None = None
        self.input_title = ""
        self.input_buffer = Buffer()

        self.message_title = ""
        self.message_body = ""

        self.application: Application[None] | None = None
        self.body_window: Window | None = None
        self.input_window: Window | None = None

    def reload(self) -> None:
        self.config = load_config(self.config_path)

    def save(self) -> None:
        save_config(self.config, self.config_path)

    def format_status(self) -> str:
        return (
            f"config file : {self.config_path}\n"
            f"template    : {self.config.template_root}\n"
            f"data        : {self.config.data_root}\n"
            f"output      : {self.config.output_root}\n"
            f"profile     : {self.config.active_profile}\n"
            f"bullets     : {self.config.active_bullets_catalog}\n"
            f"compile pdf : {'yes' if self.config.compile_pdf else 'no'}"
        )

    def list_profiles(self) -> list[str]:
        profiles = list_relative_yaml_files(self.config.data_root, "profiles")
        if self.config.active_profile not in profiles:
            profiles.append(self.config.active_profile)
        return sorted(profiles)

    def list_bullets_catalogs(self) -> list[str]:
        catalogs = list_relative_yaml_files(self.config.data_root, "bullets")
        if self.config.active_bullets_catalog not in catalogs:
            catalogs.append(self.config.active_bullets_catalog)
        return sorted(catalogs)

    def set_active_profile(self, value: str) -> None:
        self.config.active_profile = value
        self.save()

    def set_active_bullets_catalog(self, value: str) -> None:
        self.config.active_bullets_catalog = value
        self.save()

    def set_compile_pdf(self, value: bool) -> None:
        self.config.compile_pdf = value
        self.save()

    def update_path(self, field_name: str, value: str) -> None:
        resolved = Path(value).expanduser().resolve()
        if field_name == "template_root":
            self.config.template_root = resolved
        elif field_name == "data_root":
            self.config.data_root = resolved
        elif field_name == "output_root":
            self.config.output_root = resolved
        else:
            raise ValueError(f"Unknown config field: {field_name}")
        self.save()

    def generate_resume(self) -> str:
        result = run_generation(
            PipelineRequest(
                profile_name=self.config.active_profile,
                bullets_catalog_name=self.config.active_bullets_catalog,
                compile_pdf=self.config.compile_pdf,
            ),
            config=self.config,
        )
        pdf_text = str(result.pdf_path) if result.pdf_path else "not generated"
        return (
            f"output directory : {result.output_dir}\n"
            f"rendered latex   : {result.rendered_main}\n"
            f"pdf              : {pdf_text}"
        )

    def render_text(self) -> str:
        header = [*TITLE_ART, TITLE_RULE, ""]
        if self.mode == "menu":
            return "\n".join(header + self._render_menu_lines())
        if self.mode == "choice":
            return "\n".join(header + self._render_choice_lines())
        if self.mode == "input":
            return "\n".join(header + self._render_input_lines())
        if self.mode == "message":
            return "\n".join(header + self._render_message_lines())
        return "\n".join(header + ["unknown mode"])

    def render_ansi(self) -> str:
        styled_lines: list[str] = []
        for line in self.render_text().splitlines():
            if line in TITLE_ART or line in {TITLE_RULE}:
                styled_lines.append(f"{ANSI_TITLE}{line}{ANSI_RESET}")
                continue
            if line.startswith("┌") or line.startswith("└"):
                styled_lines.append(f"{ANSI_ACCENT}{line}{ANSI_RESET}")
                continue
            if line.startswith("│ >"):
                styled_lines.append(f"{ANSI_SELECTED}{line}{ANSI_RESET}")
                continue
            if line.startswith("│"):
                styled_lines.append(
                    f"{ANSI_ACCENT}│{ANSI_RESET}"
                    + line[1:-1]
                    + f"{ANSI_ACCENT}{line[-1]}{ANSI_RESET}"
                )
                continue
            if line.startswith("keys:"):
                styled_lines.append(f"{ANSI_MUTED}{line}{ANSI_RESET}")
                continue
            if line.startswith("status:"):
                styled_lines.append(f"{ANSI_NOTICE}{line}{ANSI_RESET}")
                continue
            if self.mode == "message" and line and not line.startswith("│"):
                styled_lines.append(f"{ANSI_MESSAGE}{line}{ANSI_RESET}")
                continue
            styled_lines.append(line)
        return "\n".join(styled_lines)

    def _render_menu_lines(self) -> list[str]:
        config_box = self._box_lines("config", self.format_status().splitlines())
        action_lines = []
        for index, (_, label) in enumerate(MENU_ITEMS):
            prefix = "> " if index == self.selection_index else "  "
            action_lines.append(f"{prefix}{label}")
        action_box = self._box_lines("actions", action_lines)
        return config_box + [""] + action_box + [
            "",
            "keys: up/down or j/k move, enter select, q quit",
            f"status: {self.notice}",
        ]

    def _box_lines(self, title: str, lines: list[str]) -> list[str]:
        inner_width = max(len(title) + 2, *(len(line) for line in lines)) + 2
        title_text = f" {title} "
        top = "┌" + title_text + ("─" * (inner_width - len(title_text))) + "┐"
        content = [f"│ {line.ljust(inner_width - 2)} │" for line in lines]
        bottom = "└" + ("─" * inner_width) + "┘"
        return [top, *content, bottom]

    def _render_choice_lines(self) -> list[str]:
        choice_lines = [f"current: {self.choice_current}", ""]
        for index, item in enumerate(self.choice_items):
            prefix = "> " if index == self.selection_index else "  "
            choice_lines.append(f"{prefix}{item}")
        return self._box_lines(self.choice_title, choice_lines) + [
            "",
            "keys: up/down or j/k move, enter choose, esc back",
        ]

    def _render_input_lines(self) -> list[str]:
        current_value = ""
        if self.input_field:
            current_value = str(getattr(self.config, self.input_field))
        details = [
            f"current: {current_value}",
            "",
            "type a new value below",
        ]
        return self._box_lines(self.input_title, details) + ["", "keys: enter save, esc back"]

    def _render_message_lines(self) -> list[str]:
        return self._box_lines(self.message_title, self.message_body.splitlines() or [""]) + [
            "",
            "keys: enter back, q quit",
        ]

    def _invalidate(self) -> None:
        if self.application is not None:
            self.application.invalidate()

    def _focus_main(self) -> None:
        if self.application is not None and self.body_window is not None:
            self.application.layout.focus(self.body_window)

    def _focus_input(self) -> None:
        if self.application is not None and self.input_window is not None:
            self.application.layout.focus(self.input_window)

    def move_selection(self, delta: int) -> None:
        if self.mode == "menu":
            self.selection_index = (self.selection_index + delta) % len(MENU_ITEMS)
        elif self.mode == "choice" and self.choice_items:
            self.selection_index = (self.selection_index + delta) % len(self.choice_items)
        self._invalidate()

    def enter_choice_mode(self, action: str, title: str, items: list[str], current: str) -> None:
        self.mode = "choice"
        self.choice_action = action
        self.choice_title = title
        self.choice_items = items
        self.choice_current = current
        self.selection_index = items.index(current) if current in items else 0
        self._focus_main()
        self._invalidate()

    def enter_input_mode(self, field_name: str, title: str) -> None:
        self.mode = "input"
        self.input_field = field_name
        self.input_title = title
        current = str(getattr(self.config, field_name))
        self.input_buffer.set_document(Document(text=current, cursor_position=len(current)), bypass_readonly=True)
        self._focus_input()
        self._invalidate()

    def open_message(self, title: str, body: str) -> None:
        self.mode = "message"
        self.message_title = title
        self.message_body = body
        self._focus_main()
        self._invalidate()

    def reset_to_menu(self, notice: str | None = None) -> None:
        self.mode = "menu"
        self.choice_action = None
        self.choice_title = ""
        self.choice_items = []
        self.choice_current = ""
        self.input_field = None
        self.input_title = ""
        self.message_title = ""
        self.message_body = ""
        if notice is not None:
            self.notice = notice
        self._focus_main()
        self._invalidate()

    def activate_current_menu_item(self) -> bool:
        action = MENU_ITEMS[self.selection_index][0]
        if action == "generate":
            try:
                self.open_message("generation complete", self.generate_resume())
            except Exception as exc:  # noqa: BLE001
                self.open_message("generation failed", str(exc))
            return True
        if action == "profile":
            self.enter_choice_mode("profile", "select profile", self.list_profiles(), self.config.active_profile)
            return True
        if action == "bullets":
            self.enter_choice_mode(
                "bullets",
                "select bullets catalog",
                self.list_bullets_catalogs(),
                self.config.active_bullets_catalog,
            )
            return True
        if action == "compile":
            current = "true" if self.config.compile_pdf else "false"
            self.enter_choice_mode("compile", "toggle pdf compilation", ["true", "false"], current)
            return True
        if action in {"template_root", "data_root", "output_root"}:
            self.enter_input_mode(action, f"edit {action}")
            return True
        if action == "show":
            self.open_message("current config", self.format_status())
            return True
        if action == "exit":
            return False
        raise ValueError(f"Unknown action: {action}")

    def apply_current_choice(self) -> None:
        if not self.choice_items or self.choice_action is None:
            self.reset_to_menu()
            return
        selected = self.choice_items[self.selection_index]
        if self.choice_action == "profile":
            self.set_active_profile(selected)
            self.reset_to_menu(f"profile set to {selected}")
            return
        if self.choice_action == "bullets":
            self.set_active_bullets_catalog(selected)
            self.reset_to_menu(f"bullets set to {selected}")
            return
        if self.choice_action == "compile":
            self.set_compile_pdf(selected == "true")
            self.reset_to_menu(f"compile pdf set to {selected}")
            return
        raise ValueError(f"Unknown choice action: {self.choice_action}")

    def submit_input(self, value: str) -> None:
        if self.input_field is None:
            self.reset_to_menu()
            return
        cleaned = value.strip()
        if not cleaned:
            self.reset_to_menu("no change applied")
            return
        self.update_path(self.input_field, cleaned)
        self.reset_to_menu(f"{self.input_field} updated")

    def _build_key_bindings(self) -> KeyBindings:
        bindings = KeyBindings()

        menu_or_choice = Condition(lambda: self.mode in {"menu", "choice"})
        menu_mode = Condition(lambda: self.mode == "menu")
        choice_mode = Condition(lambda: self.mode == "choice")
        input_mode = Condition(lambda: self.mode == "input")
        message_mode = Condition(lambda: self.mode == "message")
        overlay_mode = Condition(lambda: self.mode in {"choice", "input", "message"})
        non_input_mode = Condition(lambda: self.mode != "input")

        @bindings.add("up", filter=menu_or_choice)
        @bindings.add("k", filter=menu_or_choice)
        def _move_up(event) -> None:
            del event
            self.move_selection(-1)

        @bindings.add("down", filter=menu_or_choice)
        @bindings.add("j", filter=menu_or_choice)
        def _move_down(event) -> None:
            del event
            self.move_selection(1)

        @bindings.add("enter", filter=menu_mode)
        def _enter_menu(event) -> None:
            if not self.activate_current_menu_item():
                event.app.exit()

        @bindings.add("enter", filter=choice_mode)
        def _enter_choice(event) -> None:
            del event
            self.apply_current_choice()

        @bindings.add("enter", filter=input_mode)
        def _enter_input(event) -> None:
            del event
            self.submit_input(self.input_buffer.text)

        @bindings.add("enter", filter=message_mode)
        def _enter_message(event) -> None:
            del event
            self.reset_to_menu()

        @bindings.add("escape", filter=overlay_mode)
        def _escape(event) -> None:
            del event
            self.reset_to_menu("cancelled")

        @bindings.add("q", filter=non_input_mode)
        def _quit(event) -> None:
            event.app.exit()

        @bindings.add("c-c")
        def _ctrl_c(event) -> None:
            event.app.exit()

        return bindings

    def _build_application(self) -> Application[None]:
        body_control = FormattedTextControl(lambda: ANSI(self.render_ansi()))
        self.body_window = Window(content=body_control, always_hide_cursor=True)

        input_prompt = Window(
            content=FormattedTextControl(lambda: ANSI(f"{ANSI_ACCENT}value > {ANSI_RESET}")),
            width=8,
            dont_extend_width=True,
            always_hide_cursor=True,
        )
        self.input_window = Window(content=BufferControl(buffer=self.input_buffer), height=1)

        root = HSplit(
            [
                self.body_window,
                ConditionalContainer(
                    content=VSplit([input_prompt, self.input_window]),
                    filter=Condition(lambda: self.mode == "input"),
                ),
            ]
        )

        return Application(
            layout=Layout(root, focused_element=self.body_window),
            key_bindings=self._build_key_bindings(),
            full_screen=True,
            mouse_support=False,
        )

    def run(self) -> None:
        self.reload()
        self.application = self._build_application()
        self._focus_main()
        self.application.run()


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resume-builder")
    subparsers = parser.add_subparsers(dest="command")

    generate_parser = subparsers.add_parser("generate", help="Render and compile a resume.")
    generate_parser.add_argument("--profile", help="Relative path under data/ to the active profile YAML.")
    generate_parser.add_argument("--bullets", help="Relative path under data/ to the bullet catalog YAML.")
    generate_parser.add_argument("--job-description", help="Reserved future input for AI selection.")
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


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()

    if args.command == "generate":
        result = run_generation(
            PipelineRequest(
                profile_name=args.profile,
                bullets_catalog_name=args.bullets,
                job_description=args.job_description,
                compile_pdf=False if args.no_compile else None,
            )
        )
        print(f"Output directory: {result.output_dir}")
        print(f"Rendered LaTeX: {result.rendered_main}")
        if result.pdf_path:
            print(f"PDF: {result.pdf_path}")
        else:
            print("PDF: not generated")
        return

    if args.command in {None, "cli", "tui"}:
        config_path = getattr(args, "config", DEFAULT_CONFIG_PATH)
        ResumeBuilderCLI(config_path=config_path).run()
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
