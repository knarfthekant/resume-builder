from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.data_loader import load_bullet_catalog, load_resume_profile


class DataLoaderTests(unittest.TestCase):
    def test_load_resume_profile(self) -> None:
        profile = load_resume_profile(
            Path("/Users/frankshan/Desktop/Job Application/workspace/data/profiles/general.yaml")
        )
        self.assertEqual(profile.candidate_name, "Frank Shan")
        self.assertGreaterEqual(len(profile.experience), 1)
        self.assertIsNotNone(profile.highlights)

    def test_load_bullet_catalog(self) -> None:
        catalog = load_bullet_catalog(
            Path("/Users/frankshan/Desktop/Job Application/workspace/data/bullets/general.yaml")
        )
        self.assertIn("ziyutec", catalog.experience)
        self.assertIn("general", catalog.summary)

    def test_invalid_profile_raises(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            path = Path(temp_dir) / "invalid.yaml"
            path.write_text("candidate_name: Test\n", encoding="utf-8")
            with self.assertRaises(ValueError):
                load_resume_profile(path)


if __name__ == "__main__":
    unittest.main()
