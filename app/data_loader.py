from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.models import (
    BulletLibrary,
    BulletOption,
    CertificateEntry,
    EducationEntry,
    ExperienceEntryDefinition,
    ProjectEntryDefinition,
    ResumeProfile,
    SkillGroup,
)


def _read_yaml(path: Path) -> dict[str, Any]:
    with path.open("r", encoding="utf-8") as handle:
        payload = yaml.safe_load(handle) or {}
    if not isinstance(payload, dict):
        raise ValueError(f"Expected mapping in {path}")
    return payload


def _require_string(data: dict[str, Any], key: str, *, context: str) -> str:
    value = data.get(key)
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"Expected non-empty string for '{key}' in {context}")
    return value


def _optional_string(data: dict[str, Any], key: str) -> str:
    value = data.get(key, "")
    if value is None:
        return ""
    if not isinstance(value, str):
        raise ValueError(f"Expected string for '{key}'")
    return value


def _require_int(data: dict[str, Any], key: str, *, context: str) -> int:
    value = data.get(key)
    if not isinstance(value, int) or value < 0:
        raise ValueError(f"Expected non-negative integer for '{key}' in {context}")
    return value


def _list_of_dicts(value: Any, *, key: str, context: str) -> list[dict[str, Any]]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, dict) for item in value):
        raise ValueError(f"Expected list of mappings for '{key}' in {context}")
    return value


def _list_of_strings(value: Any, *, key: str, context: str) -> list[str]:
    if value is None:
        return []
    if not isinstance(value, list) or any(not isinstance(item, str) for item in value):
        raise ValueError(f"Expected list of strings for '{key}' in {context}")
    return value


def _ensure_unique_ids(options: list[BulletOption], *, context: str) -> None:
    seen: set[str] = set()
    duplicates: list[str] = []
    for option in options:
        if option.id in seen:
            duplicates.append(option.id)
        seen.add(option.id)
    if duplicates:
        raise ValueError(f"Duplicate bullet ids in {context}: {', '.join(sorted(set(duplicates)))}")


def load_resume_profile(path: Path) -> ResumeProfile:
    raw = _read_yaml(path)
    context = str(path)

    education = [
        EducationEntry(
            institution=_require_string(item, "institution", context=context),
            degree=_require_string(item, "degree", context=context),
            date_range=_require_string(item, "date_range", context=context),
            gpa=_optional_string(item, "gpa"),
        )
        for item in _list_of_dicts(raw.get("education"), key="education", context=context)
    ]

    skills = [
        SkillGroup(
            category=_require_string(item, "category", context=context),
            items=_require_string(item, "items", context=context),
        )
        for item in _list_of_dicts(raw.get("skills"), key="skills", context=context)
    ]

    certificates = [
        CertificateEntry(
            date=_require_string(item, "date", context=context),
            issuer=_require_string(item, "issuer", context=context),
            name=_require_string(item, "name", context=context),
            cert_url=_optional_string(item, "cert_url"),
            cert_label=_optional_string(item, "cert_label"),
        )
        for item in _list_of_dicts(raw.get("certificates"), key="certificates", context=context)
    ]

    experience_entries = [
        ExperienceEntryDefinition(
            id=_require_string(item, "id", context=context),
            title=_require_string(item, "title", context=context),
            location=_require_string(item, "location", context=context),
            date_range=_require_string(item, "date_range", context=context),
            company=_require_string(item, "company", context=context),
            max_bullets=_require_int(item, "max_bullets", context=context),
        )
        for item in _list_of_dicts(raw.get("experience_entries"), key="experience_entries", context=context)
    ]

    project_entries = [
        ProjectEntryDefinition(
            id=_require_string(item, "id", context=context),
            name=_require_string(item, "name", context=context),
            tech_stack=_require_string(item, "tech_stack", context=context),
            max_bullets=_require_int(item, "max_bullets", context=context),
            link_url=_optional_string(item, "link_url"),
            link_label=_optional_string(item, "link_label"),
        )
        for item in _list_of_dicts(raw.get("project_entries"), key="project_entries", context=context)
    ]

    profile = ResumeProfile(
        candidate_name=_require_string(raw, "candidate_name", context=context),
        email=_require_string(raw, "email", context=context),
        phone=_require_string(raw, "phone", context=context),
        linkedin_url=_require_string(raw, "linkedin_url", context=context),
        linkedin_handle=_require_string(raw, "linkedin_handle", context=context),
        github_url=_require_string(raw, "github_url", context=context),
        github_handle=_require_string(raw, "github_handle", context=context),
        portfolio_url=_optional_string(raw, "portfolio_url"),
        portfolio_label=_optional_string(raw, "portfolio_label"),
        education=education,
        skills=skills,
        certificates=certificates,
        experience_entries=experience_entries,
        project_entries=project_entries,
    )
    _ensure_unique_entry_ids(profile, context=context)
    return profile


def _load_bullet_options(value: Any, *, key: str, context: str) -> list[BulletOption]:
    items = _list_of_dicts(value, key=key, context=context)
    options = [
        BulletOption(
            id=_require_string(item, "id", context=context),
            text=_require_string(item, "text", context=context),
            tags=_list_of_strings(item.get("tags"), key="tags", context=context),
            evidence=_optional_string(item, "evidence"),
        )
        for item in items
    ]
    _ensure_unique_ids(options, context=f"{context}:{key}")
    return options


def _ensure_unique_entry_ids(profile: ResumeProfile, *, context: str) -> None:
    experience_ids = [entry.id for entry in profile.experience_entries]
    project_ids = [entry.id for entry in profile.project_entries]
    if len(set(experience_ids)) != len(experience_ids):
        raise ValueError(f"Duplicate experience entry ids in {context}")
    if len(set(project_ids)) != len(project_ids):
        raise ValueError(f"Duplicate project entry ids in {context}")


def load_bullet_library(path: Path) -> BulletLibrary:
    raw = _read_yaml(path)
    context = str(path)

    experience = raw.get("experience", {})
    if not isinstance(experience, dict):
        raise ValueError(f"Expected mapping for 'experience' in {context}")
    project_section = raw.get("projects", {})
    if not isinstance(project_section, dict):
        raise ValueError(f"Expected mapping for 'projects' in {context}")

    return BulletLibrary(
        summary_options=_load_bullet_options(raw.get("summary_options"), key="summary_options", context=context),
        experience={
            key: _load_bullet_options(value, key=key, context=context)
            for key, value in experience.items()
            if isinstance(key, str)
        },
        projects={
            key: _load_bullet_options(value, key=key, context=context)
            for key, value in project_section.items()
            if isinstance(key, str)
        },
    )


def list_relative_yaml_files(root: Path, relative_dir: str) -> list[str]:
    target_dir = root / relative_dir
    if not target_dir.exists():
        return []
    return sorted(str(path.relative_to(root)) for path in target_dir.rglob("*.yaml"))
