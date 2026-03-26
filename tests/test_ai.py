from __future__ import annotations

import unittest

from pydantic import ValidationError

from app.ai.types import SelectedBullet, SelectedSection, SelectionSuggestion


class AITypesTests(unittest.TestCase):
    def test_selection_suggestion_schema_round_trip(self) -> None:
        suggestion = SelectionSuggestion(
            summary_id="ai_automation",
            experience=[SelectedSection(entry_id="ziyutec_marketplace", bullets=[SelectedBullet(bullet_id="ziyutec_rag")])],
            projects=[],
            notes="Focus on AI alignment.",
        )
        payload = suggestion.model_dump()
        parsed = SelectionSuggestion.model_validate(payload)
        self.assertEqual(parsed.summary_id, "ai_automation")
        self.assertEqual(parsed.experience[0].bullets[0].bullet_id, "ziyutec_rag")

    def test_selection_suggestion_rejects_missing_entry_id(self) -> None:
        with self.assertRaises(ValidationError):
            SelectedSection.model_validate({"bullets": [{"bullet_id": "ziyutec_rag"}]})


if __name__ == "__main__":
    unittest.main()
