from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import default_config, save_config
from app.tui import ResumeBuilderApp
from textual.widgets import Button


class TuiTests(unittest.IsolatedAsyncioTestCase):
    async def test_tui_loads_and_wires_generate_button(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = default_config()
            config.output_root = Path(temp_dir)
            config.compile_pdf = False
            config_path = Path(temp_dir) / "config.yaml"
            save_config(config, config_path)

            app = ResumeBuilderApp(config_path=config_path)
            async with app.run_test() as pilot:
                self.assertEqual(app.query_one("#active_bullets_catalog").value, "bullets/general.yaml")
                app.query_one("#generate_resume", Button).press()
                await pilot.pause()
                status = app.query_one("#status").render()
                self.assertIn("Generation succeeded.", str(status))


if __name__ == "__main__":
    unittest.main()
