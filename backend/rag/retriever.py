"""Metadata-filtered retrieval with authority-aware reranking."""

from __future__ import annotations

import logging
import re
from typing import Any, Optional

from backend.models.enums import DocType
from backend.models.messages import Citation
from backend.rag.store import get_collection

logger = logging.getLogger(__name__)

_WORD = re.compile(r"[a-z0-9]+")
_UNKNOWN_VERSION_PENALTY = 0.75


def _doc_type(value: str) -> DocType:
    try:
        return DocType(value)
    except ValueError:
        return DocType.COMMUNITY


def _lexical_overlap(query: str, text: str) -> float:
    q = set(_WORD.findall(query.lower()))
    if not q:
        return 0.0
    t = set(_WORD.findall(text.lower()))
    return len(q & t) / len(q)


def _build_where(tool: Optional[str]) -> Optional[dict[str, Any]]:
    if tool:
        return {"tool": tool}
    return None


def retrieve(
    query: str,
    tool: Optional[str] = None,
    version: Optional[str] = None,
    domain: Optional[str] = None,
    k: int = 5,
) -> list[Citation]:
    """Retrieve and rerank citations.

    Filters by tool when provided. When ``version`` is unknown, retrieves across
    versions, labels each citation with its own version, and lowers confidence.
    Higher-authority document types are preferred, and community sources are
    flagged as secondary via a reduced confidence.

    Args:
        query: Search query.
        tool: Tool name filter (exact match on metadata).
        version: Tool version; empty or ``None`` means unknown.
        domain: Optional hint appended to the query for relevance.
        k: Number of citations to return.

    Returns:
        Citations ordered by final score, descending.
    """
    coll = get_collection()
    if coll.count() == 0:
        logger.warning("Retrieval store is empty")
        return []
    full_query = f"{query} {domain}" if domain else query
    n = max(k * 3, 10)
    where = _build_where(tool)
    try:
        res = coll.query(query_texts=[full_query], n_results=n, where=where)
    except Exception as exc:  # noqa: BLE001 - chroma raises varied errors
        logger.error("Chroma query failed: %s", type(exc).__name__)
        return []
    docs = (res.get("documents") or [[]])[0]
    metas = (res.get("metadatas") or [[]])[0]
    dists = (res.get("distances") or [[]])[0]
    if not docs and where is not None:
        res = coll.query(query_texts=[full_query], n_results=n)
        docs = (res.get("documents") or [[]])[0]
        metas = (res.get("metadatas") or [[]])[0]
        dists = (res.get("distances") or [[]])[0]
    version_known = bool(version and version.strip())
    out: list[Citation] = []
    for doc, meta, dist in zip(docs, metas, dists):
        dtype = _doc_type(str(meta.get("doc_type", "")))
        sim = max(0.0, 1.0 - float(dist))
        score = 0.6 * sim + 0.3 * _lexical_overlap(query, doc)
        score += 0.1 * (1.0 - dtype.priority / max(len(list(DocType)) - 1, 1))
        conf = 1.0
        doc_version = str(meta.get("version", ""))
        if not version_known:
            conf *= _UNKNOWN_VERSION_PENALTY
        elif doc_version and doc_version.lower() not in {"any", "all", "*"}:
            if not _version_compatible(str(version), doc_version):
                conf *= 0.6
                score *= 0.8
        if dtype.is_secondary:
            conf *= 0.5
        out.append(
            Citation(
                tool=str(meta.get("tool", "")),
                version=doc_version,
                component=str(meta.get("component", "")),
                doc_type=dtype,
                section=str(meta.get("section", "")),
                publication_date=str(meta.get("publication_date", "")),
                url=str(meta.get("url", "")),
                snippet=doc[:600],
                score=round(score, 4),
                confidence=round(conf, 3),
            )
        )
    out.sort(key=lambda c: c.score, reverse=True)
    return out[:k]


def _version_compatible(requested: str, doc_version: str) -> bool:
    """Loose major-version compatibility check."""
    r = _WORD.findall(requested.lower())
    d = _WORD.findall(doc_version.lower())
    if not r or not d:
        return True
    return r[0] == d[0]