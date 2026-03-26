from __future__ import annotations

import unittest
from pathlib import Path

from app.data_loader import load_bullet_library, load_resume_profile
from app.models import ResumeSelection
from app.selection import ManualSelectionService, SelectionApplier, SelectionValidationError

PROJECT_ROOT = Path(__file__).resolve().parent.parent


class SelectionTests(unittest.TestCase):
    def setUp(self) -> None:
        self.profile = load_resume_profile(PROJECT_ROOT / "data" / "profiles" / "general.yaml")
        self.library = load_bullet_library(PROJECT_ROOT / "data" / "bullets" / "general.yaml")
        self.service = ManualSelectionService()

    def test_default_selection_builds_valid_context(self) -> None:
        selection = self.service.build_default_selection(self.profile, self.library)
        context = SelectionApplier().build_render_context(self.profile, self.library, selection)
        self.assertTrue(context["highlights"]["summary"])
        self.assertGreaterEqual(len(context["experience"]), 1)
        self.assertLessEqual(len(context["projects"]), self.profile.max_project_entries)

    def test_invalid_selection_raises_for_unknown_bullet(self) -> None:
        with self.assertRaises(SelectionValidationError):
            self.service.validate_selection(
                self.profile,
                self.library,
                ResumeSelection(
                    experience={"ziyutec": ["missing_bullet", "ziyutec_rag", "ziyutec_rbac", "ziyutec_auth"]},
                    projects={
                        "resume_builder": ["resume_builder_agent", "resume_builder_hitl"],
                        "mini_vllm": ["vllm_engine", "vllm_scheduler"],
                    },
                ),
            )

    def test_invalid_selection_raises_for_over_limit(self) -> None:
        with self.assertRaises(SelectionValidationError):
            self.service.validate_selection(
                self.profile,
                self.library,
                ResumeSelection(
                    experience={
                        "ziyutec": [
                            "ziyutec_sdlc",
                            "ziyutec_system_design",
                            "ziyutec_rbac",
                            "ziyutec_transactions",
                            "ziyutec_caching",
                            "ziyutec_workflow_agent",
                            "ziyutec_rag",
                        ]
                    },
                    projects={
                        "resume_builder": ["resume_builder_agent", "resume_builder_hitl"],
                        "mini_vllm": ["vllm_engine", "vllm_scheduler"],
                    },
                ),
            )

    def test_invalid_selection_raises_for_too_few_entry_bullets(self) -> None:
        with self.assertRaises(SelectionValidationError):
            self.service.validate_selection(
                self.profile,
                self.library,
                ResumeSelection(
                    experience={"ziyutec": ["ziyutec_sdlc"]},
                    projects={
                        "resume_builder": ["resume_builder_agent", "resume_builder_hitl"],
                        "mini_vllm": ["vllm_engine", "vllm_scheduler"],
                    },
                ),
            )

    def test_invalid_selection_raises_for_too_few_project_entries(self) -> None:
        with self.assertRaises(SelectionValidationError):
            self.service.validate_selection(
                self.profile,
                self.library,
                ResumeSelection(
                    experience={
                        "ziyutec": [
                            "ziyutec_sdlc",
                            "ziyutec_rbac",
                            "ziyutec_rag",
                            "ziyutec_auth",
                        ]
                    },
                    projects={
                        "resume_builder": ["resume_builder_agent", "resume_builder_hitl"],
                    },
                ),
            )


if __name__ == "__main__":
    unittest.main()
