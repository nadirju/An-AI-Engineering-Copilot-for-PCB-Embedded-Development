"""Load prompt templates from the prompts directory."""

from __future__ import annotations

import logging
from functools import lru_cache

from backend.config import PROMPTS_DIR

logger = logging.getLogger(__name__)


@lru_cache(maxsize=32)
def load_prompt(name: str) -> str:
    """Load ``prompts/<name>.txt``.

    Args:
        name: Prompt file stem, e.g. ``"planner"``.

    Returns:
        The prompt text.

    Raises:
        FileNotFoundError: If the prompt file does not exist.
    """
    path = PROMPTS_DIR / f"{name}.txt"
    if not path.is_file():
        logger.error("Prompt file missing: %s", path)
        raise FileNotFoundError(f"Prompt not found: {path}")
    return path.read_text(encoding="utf-8").strip()