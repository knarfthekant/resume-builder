from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ai.client import AIConfigurationError, create_openrouter_client
from app.ai.graph import build_selection_graph
from app.ai.types import SelectionSuggestion
from app.env import DEFAULT_ENV_PATH
from app.models import AppConfig, BulletLibrary, ResumeProfile, ResumeSelection
from app.selection import ManualSelectionService


@dataclass(slots=True)
class AISuggestionResult:
    suggestion: SelectionSuggestion
    selection: ResumeSelection


class AISelectionService:
    def __init__(self, config: AppConfig | None = None, env_path: Path = DEFAULT_ENV_PATH) -> None:
        self.config = config
        self.env_path = env_path

    def suggest(
        self,
        profile: ResumeProfile,
        library: BulletLibrary,
        job_description: str,
        feedback: str = "",
        previous_suggestion: SelectionSuggestion | None = None,
    ) -> AISuggestionResult:
        model = create_openrouter_client(self.config, self.env_path)
        graph = build_selection_graph(model, profile, library)
        result = graph.invoke(
            {
                "job_description": job_description,
                "feedback": feedback,
                "previous_suggestion": previous_suggestion.model_dump_json(indent=2)
                if previous_suggestion
                else "",
            }
        )
        suggestion = result["suggestion"]
        selection = self._to_selection(profile, library, suggestion)
        return AISuggestionResult(suggestion=suggestion, selection=selection)

    def _to_selection(
        self,
        profile: ResumeProfile,
        library: BulletLibrary,
        suggestion: SelectionSuggestion,
    ) -> ResumeSelection:
        selection = ResumeSelection(
            summary_id=suggestion.summary_id,
            summary_rewrite=suggestion.summary_rewrite or "",
            experience={
                section.entry_id: [bullet.bullet_id for bullet in section.bullets]
                for section in suggestion.experience
            },
            projects={
                section.entry_id: [bullet.bullet_id for bullet in section.bullets]
                for section in suggestion.projects
            },
            rewrites={
                bullet.bullet_id: bullet.rewritten_text
                for section in [*suggestion.experience, *suggestion.projects]
                for bullet in section.bullets
                if bullet.rewritten_text
            },
        )
        return ManualSelectionService().validate_selection(profile, library, selection)
