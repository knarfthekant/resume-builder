from __future__ import annotations

import argparse
from pathlib import Path

from app.config import DEFAULT_CONFIG_PATH
from app.models import PipelineRequest
from app.pipeline import run_generation
from app.tui import ResumeBuilderApp


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="resume-builder")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate_parser = subparsers.add_parser("generate", help="Render and compile a resume.")
    generate_parser.add_argument("--profile", help="Relative path under data/ to the active profile YAML.")
    generate_parser.add_argument("--bullets", help="Relative path under data/ to the bullet catalog YAML.")
    generate_parser.add_argument("--job-description", help="Reserved future input for AI selection.")
    generate_parser.add_argument(
        "--no-compile",
        action="store_true",
        help="Render the LaTeX output without compiling a PDF.",
    )

    tui_parser = subparsers.add_parser("tui", help="Launch the Textual config and generation UI.")
    tui_parser.add_argument(
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

    if args.command == "tui":
        app = ResumeBuilderApp(config_path=args.config)
        app.run()
        return

    parser.error(f"Unknown command: {args.command}")


if __name__ == "__main__":
    main()
