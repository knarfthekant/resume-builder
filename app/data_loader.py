from __future__ import annotations

from pathlib import Path
from typing import Any

import yaml

from app.models import (
    BulletCatalog,
    CertificateEntry,
    EducationEntry,
    ExperienceEntry,
    Highlights,
    ProjectEntry,
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


def load_resume_profile(path: Path) -> ResumeProfile:
    raw = _read_yaml(path)
    context = str(path)

    highlights_data = raw.get("highlights")
    highlights = None
    if highlights_data:
        if not isinstance(highlights_data, dict):
            raise ValueError(f"Expected mapping for 'highlights' in {context}")
        highlights = Highlights(summary=_require_string(highlights_data, "summary", context=context))

    education = [
        EducationEntry(
            institution=_require_string(item, "institution", context=context),
            degree=_require_string(item, "degree", context=context),
            date_range=_require_string(item, "date_range", context=context),
            gpa=_optional_string(item, "gpa"),
        )
        for item in _list_of_dicts(raw.get("education"), key="education", context=context)
    ]

    experience = [
        ExperienceEntry(
            title=_require_string(item, "title", context=context),
            location=_require_string(item, "location", context=context),
            date_range=_require_string(item, "date_range", context=context),
            company=_require_string(item, "company", context=context),
            highlights=_list_of_strings(item.get("highlights"), key="highlights", context=context),
        )
        for item in _list_of_dicts(raw.get("experience"), key="experience", context=context)
    ]

    projects = [
        ProjectEntry(
            name=_require_string(item, "name", context=context),
            tech_stack=_require_string(item, "tech_stack", context=context),
            highlights=_list_of_strings(item.get("highlights"), key="highlights", context=context),
            link_url=_optional_string(item, "link_url"),
            link_label=_optional_string(item, "link_label"),
        )
        for item in _list_of_dicts(raw.get("projects"), key="projects", context=context)
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

    return ResumeProfile(
        candidate_name=_require_string(raw, "candidate_name", context=context),
        email=_require_string(raw, "email", context=context),
        phone=_require_string(raw, "phone", context=context),
        linkedin_url=_require_string(raw, "linkedin_url", context=context),
        linkedin_handle=_require_string(raw, "linkedin_handle", context=context),
        github_url=_require_string(raw, "github_url", context=context),
        github_handle=_require_string(raw, "github_handle", context=context),
        portfolio_url=_optional_string(raw, "portfolio_url"),
        portfolio_label=_optional_string(raw, "portfolio_label"),
        highlights=highlights,
        education=education,
        experience=experience,
        projects=projects,
        skills=skills,
        certificates=certificates,
    )


def load_bullet_catalog(path: Path) -> BulletCatalog:
    raw = _read_yaml(path)
    context = str(path)

    def normalize_mapping_of_lists(key: str) -> dict[str, list[str]]:
        section = raw.get(key, {})
        if section is None:
            return {}
        if not isinstance(section, dict):
            raise ValueError(f"Expected mapping for '{key}' in {context}")
        normalized: dict[str, list[str]] = {}
        for name, items in section.items():
            if not isinstance(name, str):
                raise ValueError(f"Expected string keys in '{key}' in {context}")
            normalized[name] = _list_of_strings(items, key=key, context=context)
        return normalized

    summary = raw.get("summary", {})
    if summary is None:
        summary = {}
    if not isinstance(summary, dict) or any(not isinstance(k, str) or not isinstance(v, str) for k, v in summary.items()):
        raise ValueError(f"Expected string mapping for 'summary' in {context}")

    return BulletCatalog(
        experience=normalize_mapping_of_lists("experience"),
        projects=normalize_mapping_of_lists("projects"),
        summary=summary,
    )


def list_relative_yaml_files(root: Path, relative_dir: str) -> list[str]:
    target_dir = root / relative_dir
    if not target_dir.exists():
        return []
    return sorted(str(path.relative_to(root)) for path in target_dir.rglob("*.yaml"))
