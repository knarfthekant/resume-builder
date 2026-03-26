from __future__ import annotations

import os
import tempfile
import unittest
from pathlib import Path

from app.env import get_openrouter_api_key, mask_api_key, save_openrouter_api_key


class EnvTests(unittest.TestCase):
    def setUp(self) -> None:
        self.original_key = os.environ.get("OPENROUTER_API_KEY")

    def tearDown(self) -> None:
        if self.original_key is None:
            os.environ.pop("OPENROUTER_API_KEY", None)
        else:
            os.environ["OPENROUTER_API_KEY"] = self.original_key

    def test_save_and_load_openrouter_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            env_path = Path(temp_dir) / ".env"
            save_openrouter_api_key("sk-or-v1-example1234", env_path)
            self.assertEqual(get_openrouter_api_key(env_path), "sk-or-v1-example1234")

    def test_mask_api_key(self) -> None:
        self.assertEqual(mask_api_key(None), "(not configured)")
        self.assertEqual(mask_api_key("abcdefgh"), "********")
        self.assertEqual(mask_api_key("abcdefghijklmnop"), "abcd...mnop")


if __name__ == "__main__":
    unittest.main()
