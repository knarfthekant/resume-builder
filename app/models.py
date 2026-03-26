from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class AppConfig:
    template_root: Path
    data_root: Path
    output_root: Path
    active_profile: str
    active_bullet_library: str
    compile_pdf: bool = True
    openrouter_model: str = "openai/gpt-5.4-mini"
    openrouter_base_url: str = "https://openrouter.ai/api/v1"
    setup_completed: bool = False


@dataclass(slots=True)
class EducationEntry:
    institution: str
    degree: str
    date_range: str
    gpa: str = ""


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
class ExperienceEntryDefinition:
    id: str
    title: str
    location: str
    date_range: str
    company: str
    min_bullets: int
    max_bullets: int


@dataclass(slots=True)
class ProjectEntryDefinition:
    id: str
    name: str
    tech_stack: str
    min_bullets: int
    max_bullets: int
    link_url: str = ""
    link_label: str = ""


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
    min_experience_entries: int = 0
    max_experience_entries: int = 0
    min_project_entries: int = 0
    max_project_entries: int = 0
    education: list[EducationEntry] = field(default_factory=list)
    skills: list[SkillGroup] = field(default_factory=list)
    certificates: list[CertificateEntry] = field(default_factory=list)
    experience_entries: list[ExperienceEntryDefinition] = field(default_factory=list)
    project_entries: list[ProjectEntryDefinition] = field(default_factory=list)


@dataclass(slots=True)
class BulletOption:
    id: str
    text: str
    tags: list[str] = field(default_factory=list)


@dataclass(slots=True)
class BulletLibrary:
    summary_options: list[BulletOption] = field(default_factory=list)
    experience: dict[str, list[BulletOption]] = field(default_factory=dict)
    projects: dict[str, list[BulletOption]] = field(default_factory=dict)


@dataclass(slots=True)
class ResumeSelection:
    summary_id: str | None = None
    summary_rewrite: str = ""
    experience: dict[str, list[str]] = field(default_factory=dict)
    projects: dict[str, list[str]] = field(default_factory=dict)
    rewrites: dict[str, str] = field(default_factory=dict)


@dataclass(slots=True)
class PipelineRequest:
    profile_name: str | None = None
    bullet_library_name: str | None = None
    selection: ResumeSelection | None = None
    job_description: str | None = None
    compile_pdf: bool | None = None


@dataclass(slots=True)
class GenerationResult:
    output_dir: Path
    rendered_main: Path
    pdf_path: Path | None = None
