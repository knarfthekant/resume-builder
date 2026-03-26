from __future__ import annotations

import shutil
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, StrictUndefined

IGNORED_SUFFIXES = {".aux", ".fdb_latexmk", ".fls", ".log", ".out", ".pdf"}


def build_environment(template_root: Path) -> Environment:
    environment = Environment(
        loader=FileSystemLoader(str(template_root)),
        autoescape=False,
        undefined=StrictUndefined,
        block_start_string="[%",
        block_end_string="%]",
        variable_start_string="[[",
        variable_end_string="]]",
        comment_start_string="[#",
        comment_end_string="#]",
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=["jinja2.ext.loopcontrols"],
    )
    environment.globals["enumerate"] = enumerate
    return environment


def _render_template_file(environment: Environment, template_name: str, destination_path: Path, context: dict) -> None:
    rendered = environment.get_template(template_name).render(**context)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(rendered, encoding="utf-8")


def render_template_tree(template_root: Path, output_dir: Path, context: dict) -> Path:
    environment = build_environment(template_root)
    output_dir.mkdir(parents=True, exist_ok=True)

    main_path: Path | None = None
    for source in template_root.rglob("*"):
        relative = source.relative_to(template_root)
        destination = output_dir / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if source.suffix in IGNORED_SUFFIXES:
            continue
        if source.suffix == ".tex":
            _render_template_file(environment, relative.as_posix(), destination, context)
        else:
            shutil.copy2(source, destination)
        if relative == Path("main.tex"):
            main_path = destination

    if main_path is None:
        raise FileNotFoundError(f"Could not find main.tex under {template_root}")
    return main_path


def render_main_template(template_root: Path, output_dir: Path, context: dict) -> Path:
    return render_template_tree(template_root, output_dir, context)
