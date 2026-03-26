from __future__ import annotations

import subprocess
from pathlib import Path


class LatexCompilationError(RuntimeError):
    pass


def compile_latex(output_dir: Path, main_filename: str = "main.tex") -> Path:
    command = [
        "latexmk",
        "-pdf",
        "-interaction=nonstopmode",
        "-halt-on-error",
        main_filename,
    ]
    result = subprocess.run(
        command,
        cwd=output_dir,
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode != 0:
        raise LatexCompilationError(result.stdout + "\n" + result.stderr)

    pdf_path = output_dir / Path(main_filename).with_suffix(".pdf")
    if not pdf_path.exists():
        raise LatexCompilationError(f"Expected compiled PDF at {pdf_path}")
    return pdf_path
