"""Tutor agent: beginner-friendly explanations."""

from __future__ import annotations

from backend.agents.base import Agent, AgentContext
from backend.models.enums import AgentRole


class TutorAgent(Agent):
    """Adds short pedagogical explanations for beginners."""

    role = AgentRole.TUTOR
    prompt_name = "tutor"

    async def teach(self, ctx: AgentContext, material: str) -> str:
        """Explain material in beginner terms.

        Args:
            ctx: Agent context.
            material: The technical content to explain.

        Returns:
            A short explanation.
        """
        out = await self.llm.complete(
            self.system_prompt(),
            self.user_prompt(ctx, f"MATERIAL TO EXPLAIN:\n{material}"),
            max_tokens=900,
        )
        return out if isinstance(out, str) else str(out)