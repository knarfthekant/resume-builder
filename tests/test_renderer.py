from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.data_loader import load_bullet_catalog, load_resume_profile
from app.renderer import render_main_template
from app.selector import StaticContentSelector


class RendererTests(unittest.TestCase):
    def test_render_main_template(self) -> None:
        template_root = Path("/Users/frankshan/Desktop/Job Application/workspace/templates/resume")
        profile = load_resume_profile(
            Path("/Users/frankshan/Desktop/Job Application/workspace/data/profiles/general.yaml")
        )
        bullets = load_bullet_catalog(
            Path("/Users/frankshan/Desktop/Job Application/workspace/data/bullets/general.yaml")
        )
        context = StaticContentSelector().select(profile, bullets)

        with tempfile.TemporaryDirectory() as temp_dir:
            main_path = render_main_template(template_root, Path(temp_dir), context)
            text = main_path.read_text(encoding="utf-8")
            self.assertIn("Frank Shan", text)
            self.assertIn("\\input{sections/education}", text)


if __name__ == "__main__":
    unittest.main()
