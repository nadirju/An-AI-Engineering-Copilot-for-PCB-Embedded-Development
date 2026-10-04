"""Implementation agent: code and configuration."""

from __future__ import annotations

from backend.agents.base import STEP_SCHEMA, Agent, AgentContext
from backend.models.enums import AgentRole
from backend.models.messages import Step


class ImplementationAgent(Agent):
    """Generates code, configuration, and PCB constraints as steps."""

    role = AgentRole.IMPLEMENTATION
    prompt_name = "implementation"

    async def implement(self, ctx: AgentContext, tool: str, version: str) -> list[Step]:
        """Generate implementation steps with code.

        Args:
            ctx: Agent context.
            tool: Tool name.
            version: Tool version.

        Returns:
            Steps including code and verification fields.
        """
        extra = f"TOOL: {tool}\nVERSION: {version or 'unknown - state assumptions'}"
        data = await self.llm.complete(
            self.system_prompt(),
            self.user_prompt(ctx, extra),
            schema=STEP_SCHEMA,
            max_tokens=4000,
        )
        return self.parse_steps(data, ctx.citations)