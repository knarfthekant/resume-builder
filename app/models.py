from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    template_root: Path
    data_root: Path
    output_root: Path
    active_profile: str
    active_bullets_catalog: str
    compile_pdf: bool = True


@dataclass(slots=True)
class Highlights:
    summary: str


@dataclass(slots=True)
class EducationEntry:
    institution: str
    degree: str
    date_range: str
    gpa: str = ""


@dataclass(slots=True)
class ExperienceEntry:
    title: str
    location: str
    date_range: str
    company: str
    highlights: list[str] = field(default_factory=list)


@dataclass(slots=True)
class ProjectEntry:
    name: str
    tech_stack: str
    highlights: list[str] = field(default_factory=list)
    link_url: str = ""
    link_label: str = ""


@dataclass(slots=True)
class SkillGroup:
    category: str
    items: str


@dataclass(slots=True)
class CertificateEntry:
    date: str
    issuer: str
    name: str
    cert_url: str = ""
    cert_label: str = ""


@dataclass(slots=True)
class ResumeProfile:
    candidate_name: str
    email: str
    phone: str
    linkedin_url: str
    linkedin_handle: str
    github_url: str
    github_handle: str
    portfolio_url: str = ""
    portfolio_label: str = ""
    highlights: Highlights | None = None
    education: list[EducationEntry] = field(default_factory=list)
    experience: list[ExperienceEntry] = field(default_factory=list)
    projects: list[ProjectEntry] = field(default_factory=list)
    skills: list[SkillGroup] = field(default_factory=list)
    certificates: list[CertificateEntry] = field(default_factory=list)


@dataclass(slots=True)
class BulletCatalog:
    experience: dict[str, list[str]] = field(default_factory=dict)
    projects: dict[str, list[str]] = field(default_factory=dict)
    summary: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineRequest:
    profile_name: str | None = None
    bullets_catalog_name: str | None = None
    job_description: str | None = None
    compile_pdf: bool | None = None


@dataclass(slots=True)
class GenerationResult:
    output_dir: Path
    rendered_main: Path
    pdf_path: Path | None = None
