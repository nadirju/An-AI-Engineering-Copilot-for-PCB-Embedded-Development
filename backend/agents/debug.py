"""Debug agent: systematic fault isolation."""

from __future__ import annotations

import logging
from typing import Any

from backend.agents.base import STEP_SCHEMA, Agent, AgentContext
from backend.models.enums import AgentRole
from backend.models.messages import Step

logger = logging.getLogger(__name__)

DEBUG_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "fault_tree": {"type": "array", "items": {"type": "string"}},
        "most_likely_cause": {"type": "string"},
        "steps": STEP_SCHEMA["properties"]["steps"],
        "resolved": {"type": "boolean"},
        "next_action": {"type": "string"},
    },
    "required": ["fault_tree", "steps"],
}


class DebugAgent(Agent):
    """Isolates failures through ordered diagnostics."""

    role = AgentRole.DEBUG
    prompt_name = "debug"

    async def diagnose(
        self, ctx: AgentContext, tool: str, version: str
    ) -> tuple[list[str], list[Step], str, bool, str]:
        """Produce a fault tree and diagnostic steps.

        Args:
            ctx: Agent context.
            tool: Tool name.
            version: Tool version.

        Returns:
            Tuple of (fault_tree, steps, most_likely_cause, resolved, next_action).
        """
        extra = f"TOOL: {tool}\nVERSION: {version or 'unknown'}"
        data = await self.llm.complete(
            self.system_prompt(),
            self.user_prompt(ctx, extra),
            schema=DEBUG_SCHEMA,
            max_tokens=3500,
        )
        d: dict[str, Any] = data if isinstance(data, dict) else {}
        steps = self.parse_steps(d, ctx.citations)
        tree = [str(x) for x in d.get("fault_tree", [])]
        return (
            tree,
            steps,
            str(d.get("most_likely_cause", "")),
            bool(d.get("resolved", False)),
            str(d.get("next_action", "")),
        )