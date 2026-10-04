"""Pluggable embedding functions for ChromaDB."""

from __future__ import annotations

import hashlib
import logging
import math
import re
from typing import Protocol

from backend.config import get_settings

logger = logging.getLogger(__name__)

_DIM = 384
_TOKEN = re.compile(r"[a-z0-9_]+")


class Embedder(Protocol):
    """Embedding function protocol."""

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        """Embed a batch of texts."""
        ...


class HashEmbedder:
    """Deterministic, offline, feature-hashing embedder (no API key needed)."""

    def name(self) -> str:
        """Embedder identifier for Chroma."""
        return "hash-embedder-384"

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        return [self._embed(t) for t in input]

    def embed_query(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        """Embed queries (same as documents)."""
        return self(input)

    @staticmethod
    def _embed(text: str) -> list[float]:
        vec = [0.0] * _DIM
        tokens = _TOKEN.findall(text.lower())
        grams = tokens + [f"{a}_{b}" for a, b in zip(tokens, tokens[1:])]
        for g in grams:
            h = int(hashlib.md5(g.encode("utf-8")).hexdigest(), 16)
            vec[h % _DIM] += 1.0 if (h >> 100) & 1 else -1.0
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]


class OpenAIEmbedder:
    """OpenAI embeddings."""

    def __init__(self, api_key: str, model: str) -> None:
        from openai import OpenAI

        self._client = OpenAI(api_key=api_key)
        self._model = model

    def name(self) -> str:
        """Embedder identifier for Chroma."""
        return f"openai-{self._model}"

    def __call__(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        resp = self._client.embeddings.create(model=self._model, input=input)
        return [d.embedding for d in resp.data]

    def embed_query(self, input: list[str]) -> list[list[float]]:  # noqa: A002
        """Embed queries."""
        return self(input)


def get_embedder() -> HashEmbedder | OpenAIEmbedder:
    """Return the embedder chosen by ``EMBEDDING_PROVIDER``.

    Falls back to the hash embedder when the OpenAI key is unavailable.

    Returns:
        An embedding function.
    """
    s = get_settings()
    provider = s.embedding_provider.lower()
    if provider == "openai" and s.openai_api_key:
        return OpenAIEmbedder(s.openai_api_key, s.openai_embedding_model)
    if provider == "openai":
        logger.warning("OPENAI_API_KEY missing; using offline hash embeddings")
    return HashEmbedder()