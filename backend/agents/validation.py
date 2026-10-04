"""Validation agent: every step needs a measurable outcome."""

from __future__ import annotations

import logging
import re
from typing import Any

from backend.agents.base import Agent
from backend.models.enums import AgentRole
from backend.models.messages import Step, ValidationResult

logger = logging.getLogger(__name__)

VALIDATION_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "results": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "step": {"type": "string"},
                    "expected_outcome": {"type": "string"},
                    "how_to_verify": {"type": "string"},
                    "confidence": {"type": "number"},
                    "passed": {"type": "boolean"},
                },
                "required": ["step", "expected_outcome", "how_to_verify", "passed"],
            },
        }
    },
    "required": ["results"],
}

_MEASURABLE = re.compile(
    r"(\d|\bV\b|\bmV\b|\bMHz\b|\bkHz\b|\bns\b|\bus\b|\bms\b|0x[0-9a-fA-F]+|"
    r"\bHAL_OK\b|\blogic\b|waveform|\bbyte|\bregister|\bflag\b|\bbuilds?\b|"
    r"\bwithout errors?\b|\bshows?\b|\bappears?\b|\breads?\b|\breturns?\b|"
    r"\bDRC\b|\bpasses\b|\bidle\b|\bhigh\b|\blow\b)",
    re.IGNORECASE,
)
_MIN_LEN = 12


def is_measurable(text: str) -> bool:
    """Heuristic check that a criterion is observable/measurable.

    Args:
        text: Verification or expected-outcome text.

    Returns:
        True when the text is non-trivial and names an observable quantity.
    """
    t = text.strip()
    return len(t) >= _MIN_LEN and bool(_MEASURABLE.search(t))


class ValidationAgent(Agent):
    """Checks that each step carries a measurable verification criterion."""

    role = AgentRole.VALIDATION
    prompt_name = "validation"

    def check_steps(self, steps: list[Step]) -> list[ValidationResult]:
        """Deterministically validate steps.

        Args:
            steps: Generated steps.

        Returns:
            One :class:`ValidationResult` per step.
        """
        results: list[ValidationResult] = []
        for s in steps:
            ok = is_measurable(s.expected_outcome) and is_measurable(s.how_to_verify)
            conf = s.confidence
            if s.citations:
                conf = max(conf, min(c.confidence for c in s.citations))
            results.append(
                ValidationResult(
                    step=s.title,
                    expected_outcome=s.expected_outcome,
                    how_to_verify=s.how_to_verify,
                    confidence=round(conf if ok else min(conf, 0.3), 3),
                    passed=ok,
                )
            )
        return results

    def failing_titles(self, results: list[ValidationResult]) -> list[str]:
        """Return titles of steps that failed validation."""
        return [r.step for r in results if not r.passed]

    async def revise(self, steps: list[Step], failing: list[str]) -> list[Step]:
        """Ask the LLM to repair steps lacking measurable criteria.

        Args:
            steps: Current steps.
            failing: Titles needing revision.

        Returns:
            Revised steps (unchanged ones are preserved).
        """
        if not failing:
            return steps
        payload = "\n".join(
            f"- {s.title}: instruction={s.instruction!r}"
            for s in steps
            if s.title in failing
        )
        schema: dict[str, Any] = {
            "type": "object",
            "properties": {
                "revisions": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "title": {"type": "string"},
                            "expected_outcome": {"type": "string"},
                            "how_to_verify": {"type": "string"},
                        },
                        "required": ["title", "expected_outcome", "how_to_verify"],
                    },
                }
            },
            "required": ["revisions"],
        }
        try:
            data = await self.llm.complete(
                self.system_prompt(),
                "Add a measurable expected_outcome and how_to_verify to each step.\n"
                + payload,
                schema=schema,
                max_tokens=1500,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Validation revise failed: %s", exc)
            return steps
        fixes = {
            str(r.get("title")): r
            for r in (data.get("revisions", []) if isinstance(data, dict) else [])
            if isinstance(r, dict)
        }
        out: list[Step] = []
        for s in steps:
            fix = fixes.get(s.title)
            if fix:
                s = s.model_copy(
                    update={
                        "expected_outcome": str(fix.get("expected_outcome", "")),
                        "how_to_verify": str(fix.get("how_to_verify", "")),
                    }
                )
            out.append(s)
        return out