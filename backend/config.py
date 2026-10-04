"""Application settings with environment and Streamlit-secrets fallback."""

from __future__ import annotations

import logging
import os
from functools import lru_cache
from pathlib import Path
from typing import Any, Literal, Optional

from dotenv import load_dotenv
from pydantic import Field
from pydantic_settings import BaseSettings, SettingsConfigDict

logger = logging.getLogger(__name__)

PROJECT_ROOT: Path = Path(__file__).resolve().parent.parent
PROMPTS_DIR: Path = PROJECT_ROOT / "prompts"
DOCS_DIR: Path = PROJECT_ROOT / "data" / "docs"

_SECRET_KEYS: tuple[str, ...] = (
    "LLM_PROVIDER",
    "EMBEDDING_PROVIDER",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
    "GEMINI_API_KEY",
    "GROQ_API_KEY",
    "ANTHROPIC_MODEL",
    "OPENAI_MODEL",
    "GEMINI_MODEL",
    "GROQ_MODEL",
    "OPENAI_EMBEDDING_MODEL",
    "CHROMA_MODE",
    "CHROMA_PATH",
    "MAX_REVISIONS",
    "LOG_LEVEL",
)

LLMProvider = Literal["anthropic", "openai", "gemini", "groq"]
EmbeddingProvider = Literal["openai", "gemini", "local", "hash"]


def _load_streamlit_secrets() -> dict[str, Any]:
    """Return values from ``st.secrets`` if Streamlit is importable.

    The import is guarded and lazy so the backend has no hard dependency on
    Streamlit and remains usable in tests and scripts.

    Returns:
        A mapping of recognised secret keys to their values (may be empty).
    """
    try:
        import importlib

        st = importlib.import_module("streamlit")
        secrets = st.secrets
        return {k: secrets[k] for k in _SECRET_KEYS if k in secrets}
    except (ImportError, FileNotFoundError, KeyError, AttributeError, RuntimeError):
        return {}
    except Exception as exc:  # noqa: BLE001 - streamlit raises varied errors
        logger.debug("Could not read streamlit secrets: %s", type(exc).__name__)
        return {}


class Settings(BaseSettings):
    """Runtime configuration. Never hard-codes secrets."""

    model_config = SettingsConfigDict(extra="ignore", case_sensitive=False)

    llm_provider: LLMProvider = Field(default="anthropic")
    embedding_provider: EmbeddingProvider = Field(default="openai")
    anthropic_api_key: Optional[str] = Field(default=None)
    openai_api_key: Optional[str] = Field(default=None)
    gemini_api_key: Optional[str] = Field(default=None)
    groq_api_key: Optional[str] = Field(default=None)
    anthropic_model: str = Field(default="claude-sonnet-4-5")
    openai_model: str = Field(default="gpt-4o")
    gemini_model: str = Field(default="gemini-2.0-flash")
    groq_model: str = Field(default="llama-3.3-70b-versatile")
    openai_embedding_model: str = Field(default="text-embedding-3-small")
    chroma_mode: str = Field(default="persistent")
    chroma_path: str = Field(default="./data/chroma")
    max_revisions: int = Field(default=2, ge=0, le=5)
    log_level: str = Field(default="INFO")

    @property
    def has_llm_key(self) -> bool:
        """Whether the key for the selected LLM provider is configured."""
        keys: dict[str, Optional[str]] = {
            "anthropic": self.anthropic_api_key,
            "openai": self.openai_api_key,
            "gemini": self.gemini_api_key,
            "groq": self.groq_api_key,
        }
        return bool(keys.get(self.llm_provider))


def _overlay_secrets() -> None:
    """Copy Streamlit secrets into the process environment when absent."""
    for key, value in _load_streamlit_secrets().items():
        if key not in os.environ and value is not None:
            os.environ[key] = str(value)


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    """Build and cache the application settings.

    Returns:
        The singleton :class:`Settings` instance.
    """
    load_dotenv()
    _overlay_secrets()
    return Settings()


def reset_settings_cache() -> None:
    """Clear the cached settings (used by tests)."""
    get_settings.cache_clear()