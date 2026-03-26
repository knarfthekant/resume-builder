from __future__ import annotations

import shutil
import subprocess
from pathlib import Path


class LatexCompilationError(RuntimeError):
    pass


class LatexCompilerMissingError(LatexCompilationError):
    pass


def latexmk_install_help() -> str:
    return (
        "latexmk is not installed or not on your PATH.\n\n"
        "Install one of these LaTeX distributions, then retry:\n"
        "- macOS: brew install --cask mactex-no-gui\n"
        "- Ubuntu/Debian: sudo apt install latexmk texlive-latex-recommended texlive-fonts-recommended texlive-latex-extra\n"
        "- Windows: install MiKTeX or TeX Live, then ensure latexmk is on PATH"
    )

def ensure_latexmk_available() -> None:
    if shutil.which("latexmk") is None:
        raise LatexCompilerMissingError(latexmk_install_help())


def compile_latex(output_dir: Path, main_filename: str = "main.tex") -> Path:
    ensure_latexmk_available()
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
