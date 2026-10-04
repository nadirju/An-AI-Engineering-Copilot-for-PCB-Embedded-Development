"""End-to-end SPI-DMA demo path with a mocked LLM."""

from __future__ import annotations

import asyncio
from typing import Any, AsyncIterator, Iterator, Optional

import pytest

from backend.config import reset_settings_cache
from backend.llm.client import LLMClient
from backend.models import Done, EDATool, Mode, ProjectContext, Step, Trace
from backend.rag.store import reset_store_cache


class MockLLM(LLMClient):
    """Deterministic LLM keyed on the requested output schema."""

    async def complete(
        self,
        system: str,
        user: str,
        schema: Optional[dict[str, Any]] = None,
        max_tokens: int = 2048,
    ) -> str | dict[str, Any]:
        props = (schema or {}).get("properties", {})
        if "retrieval_queries" in props:
            return {
                "objective": "Configure SPI1 with DMA for BME280",
                "domain": "firmware",
                "tool": "STM32CubeIDE/CubeMX",
                "version": "1.15",
                "component": "SPI1",
                "subtasks": ["Configure SPI1", "Configure DMA", "Verify bus"],
                "retrieval_queries": ["STM32 SPI DMA", "BME280 SPI"],
            }
        if "fault_tree" in props:
            return {
                "fault_tree": ["Power", "Wiring", "SPI mode"],
                "most_likely_cause": "CPHA mismatch",
                "steps": [self._step("Check SPI mode")],
                "resolved": False,
                "next_action": "Capture CS/SCK/MISO with a logic analyzer",
            }
        if "steps" in props:
            return {"steps": [self._step("Set SPI1 to Full-Duplex Master"),
                              self._step("Add SPI1_RX and SPI1_TX DMA requests")]}
        return "ok"

    @staticmethod
    def _step(title: str) -> dict[str, str]:
        return {
            "title": title,
            "instruction": "Open the .ioc file, Connectivity, SPI1.",
            "why": "BME280 needs SPI mode 0 at no more than 10 MHz.",
            "expected_outcome": "CubeMX shows baud rate 5.25 MBits/s",
            "how_to_verify": "Logic analyzer shows 8 SCK pulses per byte and CS low for the frame",
            "if_it_fails": "Re-check CPOL and CPHA.",
        }

    async def stream(self, system: str, user: str, max_tokens: int = 2048) -> AsyncIterator[str]:
        yield "ok"

    async def vision(self, system: str, user: str, image_bytes: bytes,
                     media_type: str = "image/png", max_tokens: int = 1024) -> str:
        return '{"observed":"CS high","expected":"CS low","verdict":"mismatch","fix":"Drive CS low"}'


@pytest.fixture()
def env(monkeypatch: pytest.MonkeyPatch) -> Iterator[None]:
    monkeypatch.setenv("CHROMA_MODE", "memory")
    monkeypatch.setenv("EMBEDDING_PROVIDER", "hash")
    reset_settings_cache()
    reset_store_cache()
    from backend.services.seed import seed_knowledge_base

    seed_knowledge_base()
    yield
    reset_store_cache()
    reset_settings_cache()


def _context() -> ProjectContext:
    return ProjectContext(
        mcu="STM32F401",
        sensors=["BME280"],
        interfaces=["SPI"],
        firmware_tool=EDATool.STM32,
        firmware_tool_version="1.15",
        pcb_tool=EDATool.ALTIUM,
    )


async def _collect(stream: AsyncIterator[Any]) -> list[Any]:
    return [e async for e in stream]


def test_guide_spi_dma_produces_verified_steps(env: None) -> None:
    from backend.services.chat_service import ChatService

    svc = ChatService(llm=MockLLM(), tool="STM32CubeIDE/CubeMX", version="1.15")
    events = asyncio.run(_collect(svc.guide("How do I configure SPI in STM32CubeIDE?", _context())))
    steps = [e for e in events if isinstance(e, Step)]
    assert steps
    assert all(s.how_to_verify and s.expected_outcome for s in steps)
    traces = [e.event.node for e in events if isinstance(e, Trace)]
    for node in ("classify", "plan", "retrieve", "generate", "validate", "conclude"):
        assert node in traces
    done = events[-1]
    assert isinstance(done, Done)
    assert done.resolved


def test_generate_and_debug_paths(env: None) -> None:
    from backend.services.chat_service import ChatService

    svc = ChatService(llm=MockLLM(), tool="Altium Designer")
    gen = asyncio.run(_collect(svc.generate("Route SPI and CS constraints", _context())))
    assert any(isinstance(e, Step) and e.how_to_verify for e in gen)
    dbg = asyncio.run(_collect(svc.debug("STM32 cannot talk to BME280", [], _context())))
    done = dbg[-1]
    assert isinstance(done, Done)
    assert done.fault_tree == ["Power", "Wiring", "SPI mode"]
    assert any(isinstance(e, Step) for e in dbg)


def test_mode_enum_has_six_modes() -> None:
    assert len(list(Mode)) == 6