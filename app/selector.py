from __future__ import annotations

from app.models import BulletLibrary, ResumeProfile, ResumeSelection
from app.selection import ManualSelectionService, SelectionApplier


class ManualSelectionServiceAdapter:
    """Compatibility wrapper around the new manual selection path."""

    def __init__(self) -> None:
        self._manual = ManualSelectionService()
        self._applier = SelectionApplier()

    def select(self, profile: ResumeProfile, library: BulletLibrary, selection: ResumeSelection | None = None) -> dict:
        active_selection = selection or self._manual.build_default_selection(profile, library)
        return self._applier.build_render_context(profile, library, active_selection)
