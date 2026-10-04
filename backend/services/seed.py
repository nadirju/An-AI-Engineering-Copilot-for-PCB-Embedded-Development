"""Idempotent seeding of the knowledge base."""

from __future__ import annotations

import logging

from backend.config import DOCS_DIR
from backend.rag.ingestion import ingest_directory

logger = logging.getLogger(__name__)


def seed_knowledge_base() -> int:
    """Ingest ``data/docs/*.md`` into Chroma, skipping unchanged documents.

    Returns:
        Number of chunks added in this call (0 when already seeded).
    """
    if not DOCS_DIR.is_dir():
        logger.warning("Docs directory missing: %s", DOCS_DIR)
        return 0
    added = ingest_directory(DOCS_DIR)
    logger.info("Seeding complete: %d new chunks", added)
    return added