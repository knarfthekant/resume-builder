from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.compiler import LatexCompilerMissingError, compile_latex


class CompilerTests(unittest.TestCase):
    def test_compile_latex_raises_helpful_error_when_latexmk_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            main_path = Path(temp_dir) / "main.tex"
            main_path.write_text("\\documentclass{article}\\begin{document}test\\end{document}", encoding="utf-8")

            with patch("app.compiler.shutil.which", return_value=None):
                with self.assertRaises(LatexCompilerMissingError) as context:
                    compile_latex(Path(temp_dir))

        message = str(context.exception)
        self.assertIn("latexmk is not installed", message)
        self.assertIn("brew install --cask mactex-no-gui", message)


if __name__ == "__main__":
    unittest.main()
