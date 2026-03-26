from __future__ import annotations

import os
from pathlib import Path

from dotenv import dotenv_values, load_dotenv, set_key

PROJECT_ROOT = Path(__file__).resolve().parent.parent
DEFAULT_ENV_PATH = PROJECT_ROOT / ".env"


def load_environment(env_path: Path = DEFAULT_ENV_PATH) -> None:
    load_dotenv(env_path, override=False)


def get_openrouter_api_key(env_path: Path = DEFAULT_ENV_PATH) -> str | None:
    load_environment(env_path)
    value = os.getenv("OPENROUTER_API_KEY")
    if value:
        return value
    values = dotenv_values(env_path)
    raw = values.get("OPENROUTER_API_KEY")
    return raw if isinstance(raw, str) and raw else None


def save_openrouter_api_key(api_key: str, env_path: Path = DEFAULT_ENV_PATH) -> None:
    env_path.parent.mkdir(parents=True, exist_ok=True)
    if not env_path.exists():
        env_path.write_text("", encoding="utf-8")
    set_key(str(env_path), "OPENROUTER_API_KEY", api_key)
    os.environ["OPENROUTER_API_KEY"] = api_key


def mask_api_key(api_key: str | None) -> str:
    if not api_key:
        return "(not configured)"
    if len(api_key) <= 8:
        return "*" * len(api_key)
    return f"{api_key[:4]}...{api_key[-4:]}"
