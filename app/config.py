from __future__ import annotations

from dataclasses import asdict
from pathlib import Path
from typing import Any

import yaml

from app.models import AppConfig

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_CONFIG_PATH = PROJECT_ROOT / "config.yaml"


def default_config() -> AppConfig:
    return AppConfig(
        template_root=PROJECT_ROOT / "templates" / "resume",
        data_root=PROJECT_ROOT / "data",
        output_root=PROJECT_ROOT / "generated" / "resumes",
        active_profile="profiles/general.yaml",
        active_bullets_catalog="bullets/general.yaml",
        compile_pdf=True,
    )


def _normalize_path(value: str | Path, *, base: Path) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = (base / path).resolve()
    return path


def _serialize_config(config: AppConfig) -> dict[str, Any]:
    payload = asdict(config)
    for key in ("template_root", "data_root", "output_root"):
        payload[key] = str(payload[key])
    return payload


def validate_config(data: dict[str, Any], *, base_dir: Path) -> AppConfig:
    required = {
        "template_root",
        "data_root",
        "output_root",
        "active_profile",
        "active_bullets_catalog",
        "compile_pdf",
    }
    missing = sorted(required - set(data))
    if missing:
        raise ValueError(f"Missing config keys: {', '.join(missing)}")

    return AppConfig(
        template_root=_normalize_path(data["template_root"], base=base_dir),
        data_root=_normalize_path(data["data_root"], base=base_dir),
        output_root=_normalize_path(data["output_root"], base=base_dir),
        active_profile=str(data["active_profile"]),
        active_bullets_catalog=str(data["active_bullets_catalog"]),
        compile_pdf=bool(data["compile_pdf"]),
    )


def load_config(path: Path = DEFAULT_CONFIG_PATH) -> AppConfig:
    if not path.exists():
        config = default_config()
        save_config(config, path)
        return config

    with path.open("r", encoding="utf-8") as handle:
        raw = yaml.safe_load(handle) or {}
    return validate_config(raw, base_dir=path.parent)


def save_config(config: AppConfig, path: Path = DEFAULT_CONFIG_PATH) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as handle:
        yaml.safe_dump(_serialize_config(config), handle, sort_keys=False)
