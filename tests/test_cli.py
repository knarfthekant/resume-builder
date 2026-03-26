from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.cli import ResumeBuilderCLI
from app.config import default_config, save_config


class CliTests(unittest.TestCase):
    def test_list_options_from_data_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = default_config()
            config.output_root = Path(temp_dir)
            config_path = Path(temp_dir) / "config.yaml"
            save_config(config, config_path)

            cli = ResumeBuilderCLI(config_path=config_path)
            self.assertIn("profiles/general.yaml", cli.list_profiles())
            self.assertIn("bullets/general.yaml", cli.list_bullets_catalogs())

    def test_handle_action_updates_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = default_config()
            config_path = Path(temp_dir) / "config.yaml"
            save_config(config, config_path)

            cli = ResumeBuilderCLI(config_path=config_path)
            cli.prompt_choice = lambda title, values, current: "profiles/general.yaml"
            cli.handle_action("profile")

            reloaded = ResumeBuilderCLI(config_path=config_path)
            self.assertEqual(reloaded.config.active_profile, "profiles/general.yaml")

    def test_generate_resume_returns_success_message(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = default_config()
            config.output_root = Path(temp_dir)
            config.compile_pdf = False
            config_path = Path(temp_dir) / "config.yaml"
            save_config(config, config_path)

            cli = ResumeBuilderCLI(config_path=config_path)
            message = cli.generate_resume()

            self.assertIn("Generation succeeded.", message)
            self.assertIn("Rendered LaTeX:", message)


if __name__ == "__main__":
    unittest.main()
