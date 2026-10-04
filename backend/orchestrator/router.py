"""Routing decisions for the graph."""

from __future__ import annotations

from backend.models.enums import Mode
from backend.orchestrator.state import GraphState

STEP_MODES: frozenset[Mode] = frozenset(
    {Mode.GUIDE, Mode.GENERATE, Mode.DEBUG, Mode.SHOW}
)


def route_target(state: GraphState) -> str:
    """Pick the retrieval path (all modes retrieve first)."""
    return "retrieve"


def reason_target(state: GraphState) -> str:
    """Pick which generation path follows reasoning."""
    return "generate"


def after_validate(state: GraphState) -> str:
    """Decide whether to loop back to reasoning or conclude.

    Loops back to ``reason`` when new evidence arrived or when validation
    flagged steps missing measurable criteria (bounded by revisions).

    Returns:
        ``"feedback"`` or ``"conclude"``.
    """
    if state.get("new_evidence"):
        return "feedback"
    results = state.get("validation", [])
    failing = [r for r in results if not r.passed]
    if failing and state.get("revisions", 0) < state.get("max_revisions", 2):
        return "feedback"
    return "conclude"