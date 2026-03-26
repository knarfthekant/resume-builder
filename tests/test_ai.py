from __future__ import annotations

import unittest
from pathlib import Path
from unittest.mock import patch

from pydantic import ValidationError

from app.ai.service import AISelectionService
from app.ai.types import SelectedBullet, SelectedSection, SelectionSuggestion
from app.data_loader import load_bullet_library, load_resume_profile
from app.selection import SelectionValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class AITypesTests(unittest.TestCase):
    def test_selection_suggestion_schema_round_trip(self) -> None:
        suggestion = SelectionSuggestion(
            summary_id="ai_automation",
            experience=[SelectedSection(entry_id="ziyutec", bullets=[SelectedBullet(bullet_id="ziyutec_rag")])],
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

    def test_ai_service_retries_after_validation_failure(self) -> None:
        profile = load_resume_profile(PROJECT_ROOT / "data" / "profiles" / "general.yaml")
        library = load_bullet_library(PROJECT_ROOT / "data" / "bullets" / "general.yaml")

        invalid = SelectionSuggestion(
            summary_id="ai_automation",
            experience=[
                SelectedSection(
                    entry_id="ziyutec",
                    bullets=[SelectedBullet(bullet_id="ziyutec_sdlc")],
                )
            ],
            projects=[],
        )
        valid = SelectionSuggestion(
            summary_id="ai_automation",
            experience=[
                SelectedSection(
                    entry_id="ziyutec",
                    bullets=[
                        SelectedBullet(bullet_id="ziyutec_sdlc"),
                        SelectedBullet(bullet_id="ziyutec_system_design"),
                        SelectedBullet(bullet_id="ziyutec_rbac"),
                        SelectedBullet(bullet_id="ziyutec_rag"),
                    ],
                )
            ],
            projects=[
                SelectedSection(
                    entry_id="mini_vlm",
                    bullets=[
                        SelectedBullet(bullet_id="vlm_model"),
                        SelectedBullet(bullet_id="vlm_training_pipeline"),
                    ],
                ),
                SelectedSection(
                    entry_id="mini_vllm",
                    bullets=[
                        SelectedBullet(bullet_id="vllm_engine"),
                        SelectedBullet(bullet_id="vllm_scheduler"),
                    ],
                )
            ],
        )

        class FakeGraph:
            def __init__(self) -> None:
                self.calls: list[dict] = []
                self._results = [invalid, valid]

            def invoke(self, state: dict) -> dict:
                self.calls.append(state)
                return {"suggestion": self._results.pop(0)}

        fake_graph = FakeGraph()

        with (
            patch("app.ai.service.create_openrouter_client", return_value=object()),
            patch("app.ai.service.build_selection_graph", return_value=fake_graph),
        ):
            result = AISelectionService().suggest(
                profile,
                library,
                "Need strong AI retrieval and workflow automation work.",
            )

        self.assertEqual(result.selection.summary_id, "ai_automation")
        self.assertEqual(len(fake_graph.calls), 2)
        self.assertIn("Validation error:", fake_graph.calls[1]["feedback"])

    def test_ai_service_raises_after_retry_limit(self) -> None:
        profile = load_resume_profile(PROJECT_ROOT / "data" / "profiles" / "general.yaml")
        library = load_bullet_library(PROJECT_ROOT / "data" / "bullets" / "general.yaml")

        invalid = SelectionSuggestion(
            experience=[
                SelectedSection(
                    entry_id="ziyutec",
                    bullets=[SelectedBullet(bullet_id="ziyutec_sdlc")],
                )
            ],
            projects=[],
        )

        class FakeGraph:
            def invoke(self, state: dict) -> dict:
                del state
                return {"suggestion": invalid}

        with (
            patch("app.ai.service.create_openrouter_client", return_value=object()),
            patch("app.ai.service.build_selection_graph", return_value=FakeGraph()),
        ):
            with self.assertRaises(SelectionValidationError):
                AISelectionService().suggest(
                    profile,
                    library,
                    "Need strong AI retrieval and workflow automation work.",
                )


if __name__ == "__main__":
    unittest.main()
