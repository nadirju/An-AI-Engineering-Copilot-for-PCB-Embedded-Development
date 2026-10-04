"""ChromaDB store access."""

from __future__ import annotations

import logging
from functools import lru_cache
from pathlib import Path
from typing import Any

import chromadb

from backend.config import PROJECT_ROOT, get_settings
from backend.rag.embeddings import get_embedder

logger = logging.getLogger(__name__)

COLLECTION_NAME = "hw_copilot_docs"


@lru_cache(maxsize=1)
def _client() -> Any:
    s = get_settings()
    if s.chroma_mode.lower() == "memory":
        logger.info("Using in-memory Chroma")
        return chromadb.EphemeralClient()
    path = Path(s.chroma_path)
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    path.mkdir(parents=True, exist_ok=True)
    logger.info("Using persistent Chroma at %s", path)
    return chromadb.PersistentClient(path=str(path))


def get_collection() -> Any:
    """Return the shared Chroma collection, creating it if needed.

    Returns:
        A Chroma collection bound to the configured embedder.
    """
    return _client().get_or_create_collection(
        name=COLLECTION_NAME,
        embedding_function=get_embedder(),
        metadata={"hnsw:space": "cosine"},
    )


def reset_store_cache() -> None:
    """Clear cached client (used by tests)."""
    _client.cache_clear()