"""Tool Specialist agent: menu paths and configuration fields."""

from __future__ import annotations

import logging

from backend.agents.base import STEP_SCHEMA, Agent, AgentContext
from backend.models.enums import AgentRole
from backend.models.messages import Step

logger = logging.getLogger(__name__)


class ToolSpecialistAgent(Agent):
    """Produces tool-specific, version-aware procedures."""

    role = AgentRole.TOOL_SPECIALIST
    prompt_name = "tool_specialist"

    async def procedure(self, ctx: AgentContext, tool: str, version: str) -> list[Step]:
        """Generate a procedure with menu paths and field names.

        Args:
            ctx: Agent context.
            tool: Tool name.
            version: Tool version (may be empty).

        Returns:
            Steps with verification fields.
        """
        extra = f"TOOL: {tool}\nVERSION: {version or 'unknown - state assumptions'}"
        data = await self.llm.complete(
            self.system_prompt(),
            self.user_prompt(ctx, extra),
            schema=STEP_SCHEMA,
            max_tokens=3000,
        )
        return self.parse_steps(data, ctx.citations)