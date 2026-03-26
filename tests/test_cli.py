from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from app.ai.service import AISuggestionResult
from app.ai.types import SelectedBullet, SelectedSection, SelectionSuggestion
from app.cli import ResumeCLIApp
from app.config import default_config, save_config
from app.models import GenerationResult, ResumeSelection


class FakeAIService:
    def __init__(self) -> None:
        self.calls: list[dict[str, str]] = []

    def suggest(self, profile, library, job_description, feedback="", previous_suggestion=None):  # noqa: ANN001, ANN201
        del profile, library, previous_suggestion
        self.calls.append({"job_description": job_description, "feedback": feedback})
        return AISuggestionResult(
            suggestion=SelectionSuggestion(
                summary_id="ai_automation",
                experience=[
                    SelectedSection(
                        entry_id="ziyutec_marketplace",
                        bullets=[
                            SelectedBullet(
                                bullet_id="ziyutec_rag",
                                rationale="Highlights applied AI retrieval work.",
                            ),
                            SelectedBullet(
                                bullet_id="ziyutec_workflow_agent",
                                rationale="Shows internal automation impact.",
                            ),
                        ],
                    )
                ],
                projects=[
                    SelectedSection(
                        entry_id="resume_builder",
                        bullets=[
                            SelectedBullet(
                                bullet_id="resume_builder_agent",
                                rationale="Directly matches the AI selection workflow.",
                            )
                        ],
                    )
                ],
                notes="Prioritized AI and automation signals.",
            ),
            selection=ResumeSelection(
                summary_id="ai_automation",
                experience={"ziyutec_marketplace": ["ziyutec_rag", "ziyutec_workflow_agent"]},
                projects={"resume_builder": ["resume_builder_agent"]},
            ),
        )


class CliTests(unittest.TestCase):
    def _make_config(self, temp_dir: str, *, setup_completed: bool) -> Path:
        config = default_config()
        config.output_root = Path(temp_dir) / "generated"
        config.setup_completed = setup_completed
        config_path = Path(temp_dir) / "config.yaml"
        save_config(config, config_path)
        return config_path

    def test_first_launch_setup_detects_existing_key(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self._make_config(temp_dir, setup_completed=False)
            app = ResumeCLIApp(
                config_path=config_path,
                api_key_loader=lambda _path: "sk-or-v1-demo1234",
                api_key_saver=lambda value, path: None,
                env_path=Path(temp_dir) / ".env",
            )
            self.assertEqual(app.mode, "setup_choice")
            self.assertIn("keep detected key", app.render_text())

            app.activate_current()

            reloaded = ResumeCLIApp(
                config_path=config_path,
                api_key_loader=lambda _path: "sk-or-v1-demo1234",
                api_key_saver=lambda value, path: None,
                env_path=Path(temp_dir) / ".env",
            )
            self.assertTrue(reloaded.config.setup_completed)

    def test_main_menu_labels_match_new_structure(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self._make_config(temp_dir, setup_completed=True)
            app = ResumeCLIApp(
                config_path=config_path,
                api_key_loader=lambda _path: None,
                api_key_saver=lambda value, path: None,
                env_path=Path(temp_dir) / ".env",
            )
            self.assertEqual(
                app.current_main_menu_labels(),
                ["generate using ai", "generate manually", "edit config", "exit"],
            )
            self.assertIn("generate using ai", app.render_text())

    def test_manual_generation_flow_reaches_generation(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self._make_config(temp_dir, setup_completed=True)
            calls = []

            def _runner(request, config):  # noqa: ANN001, ANN202
                calls.append((request, config))
                output_dir = Path(temp_dir) / "generated" / "manual"
                output_dir.mkdir(parents=True, exist_ok=True)
                rendered_main = output_dir / "main.tex"
                rendered_main.write_text("test", encoding="utf-8")
                return GenerationResult(output_dir=output_dir, rendered_main=rendered_main, pdf_path=None)

            app = ResumeCLIApp(
                config_path=config_path,
                generation_runner=_runner,
                api_key_loader=lambda _path: None,
                api_key_saver=lambda value, path: None,
                env_path=Path(temp_dir) / ".env",
            )

            app.selection_index = 1
            app.activate_current()
            app.activate_current()
            app.activate_current()

            while app.mode == "manual_step":
                app.activate_current()

            self.assertEqual(app.mode, "message")
            self.assertTrue(calls)
            self.assertIsNotNone(calls[0][0].selection)

    def test_ai_review_loop_accepts_feedback_then_generates(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            config_path = self._make_config(temp_dir, setup_completed=True)
            calls = []
            fake_ai = FakeAIService()

            def _runner(request, config):  # noqa: ANN001, ANN202
                calls.append((request, config))
                output_dir = Path(temp_dir) / "generated" / "ai"
                output_dir.mkdir(parents=True, exist_ok=True)
                rendered_main = output_dir / "main.tex"
                rendered_main.write_text("test", encoding="utf-8")
                return GenerationResult(output_dir=output_dir, rendered_main=rendered_main, pdf_path=None)

            app = ResumeCLIApp(
                config_path=config_path,
                generation_runner=_runner,
                ai_service=fake_ai,  # type: ignore[arg-type]
                api_key_loader=lambda _path: "sk-or-v1-demo1234",
                api_key_saver=lambda value, path: None,
                env_path=Path(temp_dir) / ".env",
            )

            app.selection_index = 0
            app.activate_current()
            app.activate_current()
            app.activate_current()
            self.assertEqual(app.mode, "input")

            app.submit_input("Need an AI engineer with RAG and automation experience.")
            self.assertEqual(app.mode, "ai_review")
            self.assertEqual(len(fake_ai.calls), 1)

            app.selection_index = 1
            app.activate_current()
            self.assertEqual(app.mode, "input")
            app.submit_input("Emphasize agent orchestration and developer tooling.")
            self.assertEqual(app.mode, "ai_review")
            self.assertEqual(len(fake_ai.calls), 2)

            app.selection_index = 0
            app.activate_current()
            self.assertEqual(app.mode, "message")
            self.assertTrue(calls)


if __name__ == "__main__":
    unittest.main()
