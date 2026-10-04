"""Tests for ingestion and retrieval."""

from __future__ import annotations

from typing import Iterator

import pytest

from backend.config import reset_settings_cache
from backend.rag.store import reset_store_cache


@pytest.fixture()
def seeded(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("CHROMA_MODE", "memory")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    reset_settings_cache()
    reset_store_cache()
    from backend.services.seed import seed_knowledge_base

    seed_knowledge_base()
    yield
    reset_store_cache()
    reset_settings_cache()


def test_seed_is_idempotent(seeded: None) -> None:
    from backend.services.seed import seed_knowledge_base

    assert seed_knowledge_base() == 0


def test_retrieves_spi_dma_docs(seeded: None) -> None:
    from backend.rag.retriever import retrieve

    cites = retrieve(
        "configure SPI DMA STM32", tool="STM32CubeIDE/CubeMX", version="1.15", k=4
    )
    assert cites
    assert all(c.tool == "STM32CubeIDE/CubeMX" for c in cites)
    assert all(c.url for c in cites)
    assert cites == sorted(cites, key=lambda c: c.score, reverse=True)


def test_unknown_version_lowers_confidence(seeded: None) -> None:
    from backend.rag.retriever import retrieve

    known = retrieve("BME280 SPI register", tool="STM32CubeIDE/CubeMX", version="any", k=3)
    unknown = retrieve("BME280 SPI register", tool="STM32CubeIDE/CubeMX", version="", k=3)
    assert known and unknown
    assert max(c.confidence for c in unknown) < max(c.confidence for c in known)
    assert all(c.version for c in unknown)


def test_parse_document_requires_front_matter() -> None:
    from backend.rag.ingestion import parse_document

    with pytest.raises(ValueError):
        parse_document("no front matter here")