from __future__ import annotations

from datetime import datetime
from pathlib import Path

from app.compiler import compile_latex
from app.config import load_config
from app.data_loader import load_bullet_catalog, load_resume_profile
from app.models import AppConfig, GenerationResult, PipelineRequest
from app.renderer import render_main_template
from app.selector import ContentSelector, StaticContentSelector


class ResumePipeline:
    def __init__(self, config: AppConfig, selector: ContentSelector | None = None) -> None:
        self.config = config
        self.selector = selector or StaticContentSelector()

    def run(self, request: PipelineRequest | None = None) -> GenerationResult:
        request = request or PipelineRequest()
        profile_rel = request.profile_name or self.config.active_profile
        bullets_rel = request.bullets_catalog_name or self.config.active_bullets_catalog
        compile_pdf_enabled = self.config.compile_pdf if request.compile_pdf is None else request.compile_pdf

        profile_path = self.config.data_root / profile_rel
        bullets_path = self.config.data_root / bullets_rel
        profile_data = load_resume_profile(profile_path)
        bullets_data = load_bullet_catalog(bullets_path)
        render_context = self.selector.select(profile_data, bullets_data, job_description=request.job_description)

        output_dir = self._create_output_dir()
        rendered_main = render_main_template(self.config.template_root, output_dir, render_context)

        pdf_path = None
        if compile_pdf_enabled:
            pdf_path = compile_latex(output_dir, rendered_main.name)

        return GenerationResult(output_dir=output_dir, rendered_main=rendered_main, pdf_path=pdf_path)

    def _create_output_dir(self) -> Path:
        timestamp = datetime.now().strftime("%Y%m%d-%H%M%S")
        base_name = f"resume-{timestamp}"
        candidate = self.config.output_root / base_name
        suffix = 1
        while candidate.exists():
            suffix += 1
            candidate = self.config.output_root / f"{base_name}-{suffix}"
        candidate.mkdir(parents=True, exist_ok=False)
        return candidate


def run_generation(request: PipelineRequest | None = None, config: AppConfig | None = None) -> GenerationResult:
    active_config = config or load_config()
    pipeline = ResumePipeline(active_config)
    return pipeline.run(request=request)
