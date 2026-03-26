from __future__ import annotations

from dataclasses import asdict

from app.models import BulletCatalog, ResumeProfile


class ContentSelector:
    """Seam for future AI-driven bullet selection."""

    def select(
        self,
        profile_data: ResumeProfile,
        bullets_data: BulletCatalog,
        job_description: str | None = None,
    ) -> dict:
        raise NotImplementedError


class StaticContentSelector(ContentSelector):
    """v1 selector: return the profile as-is while keeping future hooks explicit."""

    def select(
        self,
        profile_data: ResumeProfile,
        bullets_data: BulletCatalog,
        job_description: str | None = None,
    ) -> dict:
        render_context = asdict(profile_data)
        render_context["_selection_metadata"] = {
            "job_description_provided": bool(job_description),
            "catalog_sections": {
                "experience": len(bullets_data.experience),
                "projects": len(bullets_data.projects),
                "summary": len(bullets_data.summary),
            },
        }
        return render_context
