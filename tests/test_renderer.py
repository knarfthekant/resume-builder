from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.data_loader import load_bullet_library, load_resume_profile
from app.renderer import render_main_template
from app.selection import ManualSelectionService, SelectionApplier

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class RendererTests(unittest.TestCase):
    def test_render_main_template(self) -> None:
        template_root = PROJECT_ROOT / "templates" / "resume"
        profile = load_resume_profile(PROJECT_ROOT / "data" / "profiles" / "general.yaml")
        library = load_bullet_library(PROJECT_ROOT / "data" / "bullets" / "general.yaml")
        selection = ManualSelectionService().build_default_selection(profile, library)
        context = SelectionApplier().build_render_context(profile, library, selection)

        with tempfile.TemporaryDirectory() as temp_dir:
            main_path = render_main_template(template_root, Path(temp_dir), context)
            text = main_path.read_text(encoding="utf-8")
            experience_text = (Path(temp_dir) / "sections" / "experience.tex").read_text(encoding="utf-8")
            self.assertIn("Frank Shan", text)
            self.assertIn("\\input{sections/education}", text)
            self.assertIn("global B2B marketplace", experience_text)


if __name__ == "__main__":
    unittest.main()
