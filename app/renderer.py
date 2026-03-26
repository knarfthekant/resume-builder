from __future__ import annotations

import re
import shutil
from pathlib import Path

from jinja2 import Environment, StrictUndefined

TOKEN_PATTERN = re.compile(r"<<(.*?)>>", re.DOTALL)
BLOCK_PREFIXES = ("if ", "for ", "elif ", "else", "endif", "endfor")


def build_environment() -> Environment:
    environment = Environment(
        autoescape=False,
        undefined=StrictUndefined,
        variable_start_string="[[",
        variable_end_string="]]",
        comment_start_string="<#",
        comment_end_string="#>",
        trim_blocks=True,
        lstrip_blocks=True,
        extensions=["jinja2.ext.loopcontrols"],
    )
    environment.globals["enumerate"] = enumerate
    return environment


def _convert_token(match: re.Match[str]) -> str:
    content = match.group(1).strip()
    if content.startswith(BLOCK_PREFIXES):
        return f"{{% {content} %}}"
    return f"[[ {content} ]]"


def translate_template(source: str) -> str:
    return TOKEN_PATTERN.sub(_convert_token, source)


def _render_template_file(environment: Environment, source_path: Path, destination_path: Path, context: dict) -> None:
    rendered = environment.from_string(translate_template(source_path.read_text(encoding="utf-8"))).render(**context)
    destination_path.parent.mkdir(parents=True, exist_ok=True)
    destination_path.write_text(rendered, encoding="utf-8")


def render_template_tree(template_root: Path, output_dir: Path, context: dict) -> Path:
    environment = build_environment()
    output_dir.mkdir(parents=True, exist_ok=True)

    main_path: Path | None = None
    for source in template_root.rglob("*"):
        relative = source.relative_to(template_root)
        destination = output_dir / relative
        if source.is_dir():
            destination.mkdir(parents=True, exist_ok=True)
            continue
        if source.suffix == ".tex":
            _render_template_file(environment, source, destination, context)
        else:
            shutil.copy2(source, destination)
        if relative == Path("main.tex"):
            main_path = destination

    if main_path is None:
        raise FileNotFoundError(f"Could not find main.tex under {template_root}")
    return main_path


def render_main_template(template_root: Path, output_dir: Path, context: dict) -> Path:
    return render_template_tree(template_root, output_dir, context)
