from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.ai.client import AIConfigurationError, create_openrouter_client
from app.ai.graph import build_selection_graph
from app.ai.types import SelectionSuggestion
from app.env import DEFAULT_ENV_PATH
from app.models import AppConfig, BulletLibrary, ResumeProfile, ResumeSelection
from app.selection import ManualSelectionService, SelectionValidationError


@dataclass(slots=True)
class AISuggestionResult:
    suggestion: SelectionSuggestion
    selection: ResumeSelection


class AISelectionService:
    def __init__(self, config: AppConfig | None = None, env_path: Path = DEFAULT_ENV_PATH) -> None:
        self.config = config
        self.env_path = env_path
        self.max_attempts = 3

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
        active_feedback = feedback.strip()
        active_previous = previous_suggestion
        last_error = ""

        for attempt in range(1, self.max_attempts + 1):
            result = graph.invoke(
                {
                    "job_description": job_description,
                    "feedback": active_feedback,
                    "previous_suggestion": active_previous.model_dump_json(indent=2)
                    if active_previous
                    else "",
                }
            )
            suggestion = result["suggestion"]
            try:
                selection = self._to_selection(profile, library, suggestion)
                return AISuggestionResult(suggestion=suggestion, selection=selection)
            except SelectionValidationError as exc:
                last_error = str(exc)
                if attempt >= self.max_attempts:
                    break
                active_feedback = self._build_retry_feedback(
                    user_feedback=feedback,
                    validation_error=last_error,
                    attempt=attempt,
                )
                active_previous = suggestion

        raise SelectionValidationError(
            "AI could not satisfy the resume selection constraints after "
            f"{self.max_attempts} attempts. Last error: {last_error}"
        )

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

    def _build_retry_feedback(self, *, user_feedback: str, validation_error: str, attempt: int) -> str:
        parts = []
        if user_feedback.strip():
            parts.append(f"Original user feedback:\n{user_feedback.strip()}")
        parts.append(
            "Your previous suggestion was invalid. You must fix it and return a fully valid selection.\n"
            f"Validation error: {validation_error}\n"
            "Recheck all min/max entry-count constraints and all min/max bullets per selected entry.\n"
            "If an entry is selected, it must include at least the required minimum bullets.\n"
            "If an entry is not selected, omit it or leave it with zero bullets.\n"
            f"Retry attempt: {attempt + 1}"
        )
        return "\n\n".join(parts)
