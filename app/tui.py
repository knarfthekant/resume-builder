from __future__ import annotations

from pathlib import Path

from textual.app import App, ComposeResult
from textual.containers import Horizontal, Vertical
from textual.message import Message
from textual.widgets import Button, Checkbox, Footer, Header, Input, Label, Select, Static

from app.config import DEFAULT_CONFIG_PATH, load_config, save_config
from app.data_loader import list_relative_yaml_files
from app.models import AppConfig, PipelineRequest
from app.pipeline import run_generation


class GenerationFinished(Message):
    def __init__(self, output: str, success: bool) -> None:
        self.output = output
        self.success = success
        super().__init__()


class ResumeBuilderApp(App[None]):
    CSS = """
    Screen {
        layout: vertical;
    }

    #body {
        height: 1fr;
        padding: 1 2;
    }

    #main-grid {
        height: auto;
    }

    .column {
        width: 1fr;
        padding-right: 2;
    }

    .field {
        margin-bottom: 1;
    }

    #actions {
        margin-top: 1;
    }

    #status {
        height: 1fr;
        border: round $surface;
        padding: 1;
    }
    """

    BINDINGS = [("q", "quit", "Quit")]

    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        super().__init__()
        self.config_path = config_path
        self.config = load_config(config_path)

    def compose(self) -> ComposeResult:
        profiles = self._profile_options()
        yield Header()
        with Vertical(id="body"):
            yield Label("Resume Builder", classes="field")
            with Horizontal(id="main-grid"):
                with Vertical(classes="column"):
                    yield Input(str(self.config.template_root), id="template_root", classes="field")
                    yield Input(str(self.config.data_root), id="data_root", classes="field")
                    yield Input(str(self.config.output_root), id="output_root", classes="field")
                    yield Select(profiles, value=self.config.active_profile, id="active_profile", classes="field")
                    yield Input(self.config.active_bullets_catalog, id="active_bullets_catalog", classes="field")
                    yield Checkbox("Compile PDF", value=self.config.compile_pdf, id="compile_pdf", classes="field")
                    with Horizontal(id="actions"):
                        yield Button("Save Config", id="save_config", variant="primary")
                        yield Button("Generate Resume", id="generate_resume", variant="success")
                with Vertical(classes="column"):
                    yield Static(self._status_text("Ready."), id="status")
        yield Footer()

    def on_mount(self) -> None:
        self.query_one("#template_root", Input).placeholder = "Template root"
        self.query_one("#data_root", Input).placeholder = "Data root"
        self.query_one("#output_root", Input).placeholder = "Output root"
        self.query_one("#active_bullets_catalog", Input).placeholder = "bullets/general.yaml"

    def _profile_options(self) -> list[tuple[str, str]]:
        profiles = list_relative_yaml_files(self.config.data_root, "profiles")
        if self.config.active_profile not in profiles:
            profiles.append(self.config.active_profile)
        return [(profile, profile) for profile in sorted(profiles)]

    def _read_config_from_form(self) -> AppConfig:
        return AppConfig(
            template_root=Path(self.query_one("#template_root", Input).value).expanduser().resolve(),
            data_root=Path(self.query_one("#data_root", Input).value).expanduser().resolve(),
            output_root=Path(self.query_one("#output_root", Input).value).expanduser().resolve(),
            active_profile=str(self.query_one("#active_profile", Select).value),
            active_bullets_catalog=self.query_one("#active_bullets_catalog", Input).value,
            compile_pdf=self.query_one("#compile_pdf", Checkbox).value,
        )

    def _status_text(self, message: str) -> str:
        return (
            "Current config\n"
            f"- config file: {self.config_path}\n"
            f"- active profile: {self.config.active_profile}\n"
            f"- active bullets: {self.config.active_bullets_catalog}\n"
            f"- compile pdf: {self.config.compile_pdf}\n\n"
            f"{message}"
        )

    def on_button_pressed(self, event: Button.Pressed) -> None:
        if event.button.id == "save_config":
            self._save_config()
        elif event.button.id == "generate_resume":
            self._generate_resume()

    def on_generation_finished(self, message: GenerationFinished) -> None:
        self.query_one("#status", Static).update(self._status_text(message.output))

    def _save_config(self) -> None:
        self.config = self._read_config_from_form()
        save_config(self.config, self.config_path)
        self.query_one("#status", Static).update(self._status_text("Config saved."))

    def _generate_resume(self) -> None:
        self._save_config()
        try:
            result = run_generation(
                PipelineRequest(
                    profile_name=self.config.active_profile,
                    bullets_catalog_name=self.config.active_bullets_catalog,
                    compile_pdf=self.config.compile_pdf,
                ),
                config=self.config,
            )
        except Exception as exc:  # noqa: BLE001
            self.post_message(GenerationFinished(f"Generation failed:\n{exc}", success=False))
            return

        pdf_text = str(result.pdf_path) if result.pdf_path else "not generated"
        self.post_message(
            GenerationFinished(
                "Generation succeeded.\n"
                f"- output dir: {result.output_dir}\n"
                f"- main.tex: {result.rendered_main}\n"
                f"- pdf: {pdf_text}",
                success=True,
            )
        )
