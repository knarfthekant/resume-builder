from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.config import default_config
from app.pipeline import ResumePipeline


class PipelineTests(unittest.TestCase):
    def test_generation_creates_timestamped_directory_and_main_tex(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = default_config()
            config.output_root = Path(temp_dir)
            config.compile_pdf = False

            result = ResumePipeline(config).run()

            self.assertTrue(result.output_dir.exists())
            self.assertTrue(result.rendered_main.exists())
            self.assertEqual(result.rendered_main.name, "main.tex")
            self.assertTrue((result.output_dir / "sections" / "education.tex").exists())
            self.assertIsNone(result.pdf_path)

    def test_generation_can_compile_pdf(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config = default_config()
            config.output_root = Path(temp_dir)
            result = ResumePipeline(config).run()
            self.assertIsNotNone(result.pdf_path)
            assert result.pdf_path is not None
            self.assertTrue(result.pdf_path.exists())


if __name__ == "__main__":
    unittest.main()
