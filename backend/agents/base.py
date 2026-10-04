"""Shared agent base class."""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from backend.llm.client import LLMClient
from backend.llm.prompt_loader import load_prompt
from backend.models.enums import AgentRole, Persona
from backend.models.messages import Citation, Step
from backend.models.project_context import ProjectContext

STEP_SCHEMA: dict[str, Any] = {
    "type": "object",
    "properties": {
        "steps": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "title": {"type": "string"},
                    "instruction": {"type": "string"},
                    "why": {"type": "string"},
                    "expected_outcome": {"type": "string"},
                    "how_to_verify": {"type": "string"},
                    "if_it_fails": {"type": "string"},
                    "code": {"type": "string"},
                    "language": {"type": "string"},
                },
                "required": ["title", "instruction", "why"],
            },
        }
    },
    "required": ["steps"],
}


@dataclass
class AgentContext:
    """Inputs shared by all agents."""

    user_msg: str
    context: ProjectContext
    persona: Persona = Persona.INTERMEDIATE
    citations: list[Citation] = field(default_factory=list)
    notes: list[str] = field(default_factory=list)
    evidence_text: str = ""

    def citation_block(self) -> str:
        """Render citations for prompt injection."""
        if not self.citations:
            return "No retrieved sources. Flag any claim as ASSUMED."
        rows = []
        for i, c in enumerate(self.citations, 1):
            rows.append(
                f"[{i}] {c.component} {c.version} | {c.doc_type.value} | "
                f"{c.section} | conf={c.confidence}\n{c.snippet}"
            )
        return "\n\n".join(rows)


class Agent:
    """Base class for all agents."""

    role: AgentRole
    prompt_name: str

    def __init__(self, llm: LLMClient) -> None:
        self.llm = llm

    def system_prompt(self) -> str:
        """Compose system prompt: shared rules plus role prompt."""
        return f"{load_prompt('system')}\n\n{load_prompt(self.prompt_name)}"

    def user_prompt(self, ctx: AgentContext, extra: str = "") -> str:
        """Compose the user prompt."""
        parts = [
            f"PERSONA: {ctx.persona.value}",
            f"PROJECT CONTEXT:\n{ctx.context.summary()}",
            f"SOURCES:\n{ctx.citation_block()}",
        ]
        if ctx.notes:
            parts.append("NOTES:\n" + "\n".join(ctx.notes))
        if ctx.evidence_text:
            parts.append(f"USER EVIDENCE:\n{ctx.evidence_text}")
        if extra:
            parts.append(extra)
        parts.append(f"REQUEST:\n{ctx.user_msg}")
        return "\n\n".join(parts)

    @staticmethod
    def parse_steps(data: Any, citations: list[Citation]) -> list[Step]:
        """Convert structured output into Step models."""
        raw = data.get("steps", []) if isinstance(data, dict) else []
        steps: list[Step] = []
        for i, item in enumerate(raw, 1):
            if not isinstance(item, dict) or not item.get("title"):
                continue
            steps.append(
                Step(
                    index=i,
                    title=str(item.get("title", "")),
                    instruction=str(item.get("instruction", "")),
                    why=str(item.get("why", "")),
                    expected_outcome=str(item.get("expected_outcome", "")),
                    how_to_verify=str(item.get("how_to_verify", "")),
                    if_it_fails=str(item.get("if_it_fails", "")),
                    code=str(item.get("code", "")),
                    language=str(item.get("language", "")),
                    citations=citations[:2],
                )
            )
        return steps