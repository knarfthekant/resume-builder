from __future__ import annotations

from pydantic import BaseModel, Field


class SelectedBullet(BaseModel):
    bullet_id: str
    rewritten_text: str | None = None
    rationale: str | None = None


class SelectedSection(BaseModel):
    entry_id: str
    bullets: list[SelectedBullet] = Field(default_factory=list)


class SelectionSuggestion(BaseModel):
    summary_id: str | None = None
    summary_rewrite: str | None = None
    experience: list[SelectedSection] = Field(default_factory=list)
    projects: list[SelectedSection] = Field(default_factory=list)
    notes: str = ""


class SelectionFeedback(BaseModel):
    feedback: str
