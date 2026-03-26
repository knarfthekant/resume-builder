from __future__ import annotations

import argparse
from pathlib import Path

from prompt_toolkit.shortcuts import input_dialog, message_dialog, radiolist_dialog

from app.config import DEFAULT_CONFIG_PATH, load_config, save_config
from app.data_loader import list_relative_yaml_files
from app.models import PipelineRequest
from app.pipeline import run_generation


class ResumeBuilderCLI:
    def __init__(self, config_path: Path = DEFAULT_CONFIG_PATH) -> None:
        self.config_path = config_path
        self.config = load_config(config_path)

    def reload(self) -> None:
        self.config = load_config(self.config_path)

    def save(self) -> None:
        save_config(self.config, self.config_path)

    def format_status(self) -> str:
        return (
            f"Config file: {self.config_path}\n"
            f"Template root: {self.config.template_root}\n"
            f"Data root: {self.config.data_root}\n"
            f"Output root: {self.config.output_root}\n"
            f"Active profile: {self.config.active_profile}\n"
            f"Active bullets: {self.config.active_bullets_catalog}\n"
            f"Compile PDF: {'yes' if self.config.compile_pdf else 'no'}"
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
            "Generation succeeded.\n\n"
            f"Output directory: {result.output_dir}\n"
            f"Rendered LaTeX: {result.rendered_main}\n"
            f"PDF: {pdf_text}"
        )

    def prompt_action(self) -> str | None:
        return radiolist_dialog(
            title="Resume Builder",
            text=self.format_status(),
            values=[
                ("generate", "Generate resume"),
                ("profile", "Select active profile"),
                ("bullets", "Select bullets catalog"),
                ("compile", "Toggle PDF compilation"),
                ("template_root", "Edit template root"),
                ("data_root", "Edit data root"),
                ("output_root", "Edit output root"),
                ("show", "Show current config"),
                ("exit", "Exit"),
            ],
        ).run()

    def prompt_choice(self, title: str, values: list[str], current: str) -> str | None:
        options = [(value, value) for value in values]
        return radiolist_dialog(title=title, text=f"Current: {current}", values=options).run()

    def prompt_text(self, title: str, current: str) -> str | None:
        return input_dialog(title=title, text="Enter a new value:", default=current).run()

    def show_message(self, title: str, text: str) -> None:
        message_dialog(title=title, text=text).run()

    def handle_action(self, action: str) -> bool:
        if action == "generate":
            self.show_message("Resume Builder", self.generate_resume())
            return True
        if action == "profile":
            selected = self.prompt_choice("Select Profile", self.list_profiles(), self.config.active_profile)
            if selected:
                self.set_active_profile(selected)
            return True
        if action == "bullets":
            selected = self.prompt_choice(
                "Select Bullets Catalog",
                self.list_bullets_catalogs(),
                self.config.active_bullets_catalog,
            )
            if selected:
                self.set_active_bullets_catalog(selected)
            return True
        if action == "compile":
            selected = self.prompt_choice(
                "Compile PDF",
                ["true", "false"],
                "true" if self.config.compile_pdf else "false",
            )
            if selected is not None:
                self.set_compile_pdf(selected == "true")
            return True
        if action in {"template_root", "data_root", "output_root"}:
            current_value = str(getattr(self.config, action))
            entered = self.prompt_text(f"Edit {action}", current_value)
            if entered:
                self.update_path(action, entered)
            return True
        if action == "show":
            self.show_message("Current Config", self.format_status())
            return True
        if action == "exit":
            return False
        raise ValueError(f"Unknown action: {action}")

    def run(self) -> None:
        while True:
            self.reload()
            action = self.prompt_action()
            if action is None or action == "exit":
                return
            try:
                if not self.handle_action(action):
                    return
            except Exception as exc:  # noqa: BLE001
                self.show_message("Error", str(exc))


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
