from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.data_loader import load_bullet_library, load_resume_profile

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class DataLoaderTests(unittest.TestCase):
    def test_load_resume_profile(self) -> None:
        profile = load_resume_profile(PROJECT_ROOT / "data" / "profiles" / "general.yaml")
        self.assertEqual(profile.candidate_name, "Frank Shan")
        self.assertGreaterEqual(len(profile.experience_entries), 1)
        self.assertGreaterEqual(len(profile.project_entries), 1)

    def test_load_bullet_library(self) -> None:
        library = load_bullet_library(PROJECT_ROOT / "data" / "bullets" / "general.yaml")
        self.assertIn("ziyutec_marketplace", library.experience)
        self.assertTrue(any(option.id == "ai_automation" for option in library.summary_options))

    def test_invalid_profile_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.yaml"
            path.write_text("candidate_name: Test\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_resume_profile(path)

    def test_duplicate_bullet_ids_raise(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "bullets.yaml"
            path.write_text(
                """
summary_options:
  - id: dup
    text: one
  - id: dup
    text: two
experience: {}
projects: {}
""".strip(),
                encoding="utf-8",
            )
            with self.assertRaises(ValueError):
                load_bullet_library(path)


if __name__ == "__main__":
    unittest.main()
