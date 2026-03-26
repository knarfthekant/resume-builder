from __future__ import annotations

from pathlib import Path

from app.ai.types import SelectedBullet, SelectedSection, SelectionSuggestion
from app.models import BulletLibrary, ResumeProfile

SUMMARY_FILENAME = "generation_summary.txt"


def write_generation_summary(output_dir: Path, summary_text: str | None) -> Path | None:
    if not summary_text or not summary_text.strip():
        return None
    summary_path = output_dir / SUMMARY_FILENAME
    summary_path.write_text(summary_text.rstrip() + "\n", encoding="utf-8")
    return summary_path


def build_generation_summary_text(
    *,
    profile_name: str,
    bullet_library_name: str,
    job_description: str,
    suggestion: SelectionSuggestion,
    profile: ResumeProfile,
    library: BulletLibrary,
) -> str:
    lines = [
        "AI Generation Summary",
        "=====================",
        "",
        f"profile: {profile_name}",
        f"library: {bullet_library_name}",
        f"job description: {_single_line(job_description)}",
        "",
    ]

    if suggestion.summary_id:
        lines.append("summary")
        lines.append(f"  id: {suggestion.summary_id}")
        lines.append(f"  text: {_single_line(suggestion.summary_rewrite or _lookup_summary_text(library, suggestion.summary_id))}")
        lines.append("")

    _append_section_lines(
        lines,
        label="experience",
        sections=suggestion.experience,
        profile=profile,
        library=library,
        kind="experience",
    )
    _append_section_lines(
        lines,
        label="projects",
        sections=suggestion.projects,
        profile=profile,
        library=library,
        kind="projects",
    )

    if suggestion.notes.strip():
        lines.append("notes")
        lines.append(f"  {_single_line(suggestion.notes)}")
        lines.append("")

    return "\n".join(lines).rstrip()


def _append_section_lines(
    lines: list[str],
    *,
    label: str,
    sections: list[SelectedSection],
    profile: ResumeProfile,
    library: BulletLibrary,
    kind: str,
) -> None:
    if not sections:
        return
    lines.append(label)
    for section in sections:
        entry_name = _display_entry_name(profile, kind, section.entry_id)
        lines.append(f"  {entry_name} ({section.entry_id})")
        for bullet in section.bullets:
            lines.extend(_bullet_lines(bullet, library))
    lines.append("")


def _bullet_lines(bullet: SelectedBullet, library: BulletLibrary) -> list[str]:
    lines = [f"    - {bullet.bullet_id}: {_single_line(bullet.rewritten_text or _lookup_bullet_text(library, bullet.bullet_id))}"]
    if bullet.rationale:
        lines.append(f"      why: {_single_line(bullet.rationale)}")
    return lines


def _display_entry_name(profile: ResumeProfile, kind: str, entry_id: str) -> str:
    entries = profile.experience_entries if kind == "experience" else profile.project_entries
    for entry in entries:
        if entry.id != entry_id:
            continue
        if kind == "experience":
            return f"{entry.title} @ {entry.company}"
        return entry.name
    return entry_id


def _lookup_summary_text(library: BulletLibrary, summary_id: str) -> str:
    for option in library.summary_options:
        if option.id == summary_id:
            return option.text
    return summary_id


def _lookup_bullet_text(library: BulletLibrary, bullet_id: str) -> str:
    for options in [*library.experience.values(), *library.projects.values()]:
        for option in options:
            if option.id == bullet_id:
                return option.text
    return bullet_id


def _single_line(text: str) -> str:
    return " ".join(text.split())
