"""Engineering Knowledge agent: grounded explanations."""

from __future__ import annotations

from typing import AsyncIterator

from backend.agents.base import Agent, AgentContext
from backend.models.enums import AgentRole


class KnowledgeAgent(Agent):
    """Answers conceptual questions grounded in retrieved sources."""

    role = AgentRole.KNOWLEDGE
    prompt_name = "knowledge"

    async def explain(self, ctx: AgentContext) -> str:
        """Return a complete grounded answer."""
        out = await self.llm.complete(
            self.system_prompt(), self.user_prompt(ctx), max_tokens=1800
        )
        return out if isinstance(out, str) else str(out)

    def explain_stream(self, ctx: AgentContext) -> AsyncIterator[str]:
        """Stream a grounded answer."""
        return self.llm.stream(
            self.system_prompt(), self.user_prompt(ctx), max_tokens=1800
        )