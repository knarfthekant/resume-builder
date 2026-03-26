from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import default_config, load_config, save_config, validate_config


class ConfigTests(unittest.TestCase):
    def test_default_config_uses_project_paths_and_ai_defaults(self) -> None:
        config = default_config()
        self.assertTrue(str(config.template_root).endswith("templates/resume"))
        self.assertTrue(str(config.data_root).endswith("data"))
        self.assertTrue(str(config.output_root).endswith("generated/resumes"))
        self.assertEqual(config.active_profile, "profiles/general.yaml")
        self.assertEqual(config.active_bullet_library, "bullets/general.yaml")
        self.assertEqual(config.openrouter_model, "openai/gpt-5.4-mini")
        self.assertEqual(config.openrouter_base_url, "https://openrouter.ai/api/v1")

    def test_validate_config_resolves_relative_paths_and_old_bullet_key(self) -> None:
        base_dir = Path("/tmp/example")
        config = validate_config(
            {
                "template_root": "templates/resume",
                "data_root": "data",
                "output_root": "generated/resumes",
                "active_profile": "profiles/general.yaml",
                "active_bullets_catalog": "bullets/general.yaml",
                "compile_pdf": True,
                "setup_completed": True,
            },
            base_dir=base_dir,
        )
        self.assertEqual(config.template_root, (base_dir / "templates" / "resume").resolve())
        self.assertEqual(config.data_root, (base_dir / "data").resolve())
        self.assertEqual(config.active_bullet_library, "bullets/general.yaml")
        self.assertTrue(config.setup_completed)

    def test_load_config_creates_file_when_missing(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            config = load_config(config_path)
            self.assertTrue(config_path.exists())
            self.assertEqual(config.active_bullet_library, "bullets/general.yaml")

    def test_save_and_load_round_trip(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = Path(temp_dir) / "config.yaml"
            original = default_config()
            original.setup_completed = True
            save_config(original, config_path)
            loaded = load_config(config_path)
            self.assertEqual(loaded.active_profile, original.active_profile)
            self.assertEqual(loaded.active_bullet_library, original.active_bullet_library)
            self.assertEqual(loaded.openrouter_model, original.openrouter_model)


if __name__ == "__main__":
    unittest.main()
