"""Markdown document ingestion with YAML front-matter."""

from __future__ import annotations

import hashlib
import logging
import re
from pathlib import Path
from typing import Any

import yaml

from backend.rag.store import get_collection

logger = logging.getLogger(__name__)

_FRONT = re.compile(r"\A---\s*\n(.*?)\n---\s*\n(.*)\Z", re.DOTALL)
REQUIRED_KEYS: tuple[str, ...] = (
    "tool",
    "version",
    "component",
    "doc_type",
    "section",
    "publication_date",
    "url",
)


def parse_document(text: str) -> tuple[dict[str, Any], str]:
    """Split YAML front-matter from the body.

    Args:
        text: Raw markdown.

    Returns:
        Tuple of (metadata, body).

    Raises:
        ValueError: If front-matter is missing or incomplete.
    """
    m = _FRONT.match(text)
    if not m:
        raise ValueError("Document lacks YAML front-matter")
    meta = yaml.safe_load(m.group(1)) or {}
    missing = [k for k in REQUIRED_KEYS if k not in meta]
    if missing:
        raise ValueError(f"Front-matter missing keys: {missing}")
    return {k: str(meta[k]) for k in REQUIRED_KEYS}, m.group(2).strip()


def chunk_body(body: str, max_chars: int = 900) -> list[str]:
    """Split text into paragraph-based chunks.

    Args:
        body: Document body.
        max_chars: Soft chunk size limit.

    Returns:
        A list of non-empty chunks.
    """
    chunks: list[str] = []
    current = ""
    for para in re.split(r"\n\s*\n", body):
        para = para.strip()
        if not para:
            continue
        if current and len(current) + len(para) > max_chars:
            chunks.append(current)
            current = para
        else:
            current = f"{current}\n\n{para}".strip()
    if current:
        chunks.append(current)
    return chunks


def ingest_file(path: Path) -> int:
    """Ingest one document if not already present.

    Args:
        path: Markdown file path.

    Returns:
        Number of chunks added (0 when skipped).
    """
    raw = path.read_text(encoding="utf-8")
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:12]
    coll = get_collection()
    existing = coll.get(where={"source_file": path.name}, limit=1)
    if existing and existing.get("ids"):
        if existing["metadatas"][0].get("digest") == digest:
            logger.debug("Skipping already-ingested %s", path.name)
            return 0
        coll.delete(where={"source_file": path.name})
    meta, body = parse_document(raw)
    chunks = chunk_body(body)
    ids = [f"{path.stem}-{digest}-{i}" for i in range(len(chunks))]
    metas = [
        {**meta, "source_file": path.name, "digest": digest, "chunk": i}
        for i in range(len(chunks))
    ]
    coll.add(ids=ids, documents=chunks, metadatas=metas)
    logger.info("Ingested %s (%d chunks)", path.name, len(chunks))
    return len(chunks)


def ingest_directory(directory: Path) -> int:
    """Ingest every markdown file in a directory.

    Args:
        directory: Directory containing ``*.md`` files.

    Returns:
        Total chunks added.
    """
    total = 0
    for path in sorted(directory.glob("*.md")):
        try:
            total += ingest_file(path)
        except ValueError as exc:
            logger.error("Skipping %s: %s", path.name, exc)
    return total