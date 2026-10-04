"""Logging configuration."""

from __future__ import annotations

import logging

_CONFIGURED: bool = False


def configure_logging(level: str = "INFO") -> None:
    """Configure root logging once.

    Args:
        level: Logging level name, e.g. ``"INFO"``.
    """
    global _CONFIGURED
    if _CONFIGURED:
        return
    logging.basicConfig(
        level=getattr(logging, level.upper(), logging.INFO),
        format="%(asctime)s %(levelname)-7s %(name)s: %(message)s",
    )
    for noisy in ("httpx", "chromadb", "urllib3", "httpcore"):
        logging.getLogger(noisy).setLevel(logging.WARNING)
    _CONFIGURED = True