"""Tests for the validation agent."""

from __future__ import annotations

from typing import Any, AsyncIterator, Optional

import pytest

from backend.agents.validation import ValidationAgent, is_measurable
from backend.llm.client import LLMClient
from backend.models import Step


class FixLLM(LLMClient):
    """Returns a measurable revision for any step."""

    async def complete(
        self,
        system: str,
        user: str,
        schema: Optional[dict[str, Any]] = None,
        max_tokens: int = 2048,
    ) -> str | dict[str, Any]:
        return {
            "revisions": [
                {
                    "title": "Wire CS",
                    "expected_outcome": "CS falls to 0 V before the first SCK edge",
                    "how_to_verify": "Logic analyzer shows CS low for the full 2 byte frame",
                }
            ]
        }

    async def stream(self, system: str, user: str, max_tokens: int = 2048) -> AsyncIterator[str]:
        yield ""

    async def vision(self, system: str, user: str, image_bytes: bytes,
                     media_type: str = "image/png", max_tokens: int = 1024) -> str:
        return ""


def test_is_measurable() -> None:
    assert is_measurable("Register 0xD0 reads 0x60 after the first transfer")
    assert is_measurable("SCK idles low at 0 V with 8 pulses per byte")
    assert not is_measurable("Make sure it works")
    assert not is_measurable("")


def test_check_steps_flags_vague_steps() -> None:
    agent = ValidationAgent(FixLLM())
    good = Step(title="Read ID", expected_outcome="ID register returns 0x60",
                how_to_verify="Print the byte read from 0xD0 and compare with 0x60")
    bad = Step(title="Wire CS", expected_outcome="It works", how_to_verify="Look at it")
    results = agent.check_steps([good, bad])
    assert [r.passed for r in results] == [True, False]
    assert agent.failing_titles(results) == ["Wire CS"]


@pytest.mark.asyncio
async def test_revise_repairs_failing_step() -> None:
    import asyncio

    agent = ValidationAgent(FixLLM())
    bad = Step(title="Wire CS", expected_outcome="It works", how_to_verify="Look at it")
    revised = await asyncio.wait_for(agent.revise([bad], ["Wire CS"]), timeout=5)
    results = agent.check_steps(revised)
    assert results[0].passed