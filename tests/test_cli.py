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

    def test_apply_current_choice_updates_profile(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = default_config()
            config_path = Path(temp_dir) / "config.yaml"
            save_config(config, config_path)

            cli = ResumeBuilderCLI(config_path=config_path)
            cli.enter_choice_mode("profile", "select profile", ["profiles/general.yaml"], "profiles/general.yaml")
            cli.apply_current_choice()

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

            self.assertIn("rendered latex", message)
            self.assertIn("output directory", message)

    def test_submit_input_updates_output_root(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = default_config()
            config_path = Path(temp_dir) / "config.yaml"
            save_config(config, config_path)

            cli = ResumeBuilderCLI(config_path=config_path)
            new_output = Path(temp_dir) / "generated-here"
            cli.enter_input_mode("output_root", "edit output_root")
            cli.submit_input(str(new_output))

            reloaded = ResumeBuilderCLI(config_path=config_path)
            self.assertEqual(reloaded.config.output_root, new_output.resolve())

    def test_render_text_shows_minimal_header(self) -> None:
        cli = ResumeBuilderCLI()
        rendered = cli.render_text()
        self.assertIn("by Frank Shan", rendered)
        self.assertIn("actions", rendered)


if __name__ == "__main__":
    unittest.main()
