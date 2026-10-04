"""Planner agent: classify and decompose."""

from __future__ import annotations

import logging
from typing import Any

from backend.agents.base import Agent, AgentContext
from backend.models.enums import AgentRole, Domain, EDATool

logger = logging.getLogger(__name__)

PLAN_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "objective": {"type": "string"},
        "domain": {"type": "string", "enum": [d.value for d in Domain]},
        "tool": {"type": "string", "enum": [t.value for t in EDATool]},
        "version": {"type": "string"},
        "component": {"type": "string"},
        "subtasks": {"type": "array", "items": {"type": "string"}},
        "retrieval_queries": {"type": "array", "items": {"type": "string"}},
    },
    "required": ["objective", "domain", "subtasks", "retrieval_queries"],
}


class PlannerAgent(Agent):
    """Understands the objective and produces a structured plan."""

    role = AgentRole.PLANNER
    prompt_name = "planner"

    async def plan(self, ctx: AgentContext, default_tool: str = "") -> dict[str, Any]:
        """Return a plan dict.

        Args:
            ctx: Agent context.
            default_tool: Tool selected in the UI, used as a hint.

        Returns:
            Plan dict with objective, domain, tool, subtasks, queries.
        """
        extra = f"UI-SELECTED TOOL: {default_tool or 'none'}"
        try:
            data = await self.llm.complete(
                self.system_prompt(),
                self.user_prompt(ctx, extra),
                schema=PLAN_SCHEMA,
                max_tokens=1024,
            )
        except Exception as exc:  # noqa: BLE001
            logger.error("Planner failed: %s", exc)
            data = {}
        plan: dict[str, Any] = data if isinstance(data, dict) else {}
        plan.setdefault("objective", ctx.user_msg)
        plan.setdefault("domain", Domain.GENERAL.value)
        plan.setdefault("tool", default_tool or EDATool.UNKNOWN.value)
        plan.setdefault("version", "")
        plan.setdefault("component", "")
        plan.setdefault("subtasks", [ctx.user_msg])
        plan.setdefault("retrieval_queries", [ctx.user_msg])
        return plan