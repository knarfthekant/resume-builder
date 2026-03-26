from __future__ import annotations

from pathlib import Path

from langchain_openai import ChatOpenAI

from app.config import load_config
from app.env import DEFAULT_ENV_PATH, get_openrouter_api_key
from app.models import AppConfig


class AIConfigurationError(RuntimeError):
    pass


def create_openrouter_client(config: AppConfig | None = None, env_path: Path = DEFAULT_ENV_PATH):
    config = config or load_config()
    api_key = get_openrouter_api_key(env_path)
    if not api_key:
        raise AIConfigurationError("OPENROUTER_API_KEY is not configured. Run AI setup from the CLI first.")

    return ChatOpenAI(
        model=config.openrouter_model,
        api_key=api_key,
        base_url=config.openrouter_base_url,
        temperature=0,
    )
