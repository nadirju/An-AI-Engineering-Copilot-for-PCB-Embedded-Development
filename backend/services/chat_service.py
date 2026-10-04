"""Chat service: the only thing the UI calls."""

from __future__ import annotations

import logging
from typing import Any, AsyncIterator, Optional

from backend.config import get_settings
from backend.llm.client import LLMClient, LLMError, get_llm_client
from backend.models.enums import EDATool, Mode, Persona
from backend.models.messages import (
    AgentEvent,
    Citation,
    Done,
    Evidence,
    Step,
    TextChunk,
    Trace,
)
from backend.models.project_context import ProjectContext
from backend.orchestrator.graph import build_graph, run_graph
from backend.orchestrator.state import GraphState

logger = logging.getLogger(__name__)


class ChatService:
    """Streams :class:`AgentEvent` objects for each interaction mode."""

    def __init__(
        self,
        llm: Optional[LLMClient] = None,
        tool: str = "",
        version: str = "",
        persona: Persona = Persona.INTERMEDIATE,
    ) -> None:
        self._llm = llm
        self.tool = tool
        self.version = version
        self.persona = persona

    def configure(self, tool: str, version: str, persona: Persona) -> None:
        """Update UI-selected tool, version and persona."""
        self.tool, self.version, self.persona = tool, version, persona

    def _client(self) -> LLMClient:
        if self._llm is None:
            self._llm = get_llm_client()
        return self._llm

    async def _run(
        self, state: GraphState
    ) -> AsyncIterator[AgentEvent]:
        try:
            graph = build_graph(self._client(), get_settings().max_revisions)
            final = await run_graph(graph, state)
        except LLMError as exc:
            logger.error("LLM error: %s", exc)
            yield TextChunk(text=f"**LLM error:** {exc}")
            yield Done(conclusion="Request failed.", resolved=False,
                       next_action="Check API key and retry.")
            return
        for ev in final.get("trace", []):
            yield Trace(event=ev)
        for c in final.get("citations", []):
            yield c
        if final.get("tutor_text"):
            yield TextChunk(text=final["tutor_text"] + "\n\n")
        if final.get("answer"):
            yield TextChunk(text=final["answer"])
        step: Step
        for step in final.get("steps", []):
            yield step
        yield Done(
            conclusion=final.get("conclusion", ""),
            resolved=final.get("resolved", True),
            next_action=final.get("next_action", ""),
            vision=final.get("vision"),
            translation_rows=final.get("translation_rows", []),
            fault_tree=final.get("fault_tree", []),
            trace=final.get("trace", []),
        )

    def _state(self, user_msg: str, context: ProjectContext, mode: Mode,
               evidence: Optional[list[Evidence]] = None, **extra: Any) -> GraphState:
        state: GraphState = {
            "user_msg": user_msg,
            "mode": mode,
            "persona": self.persona,
            "context": context,
            "tool": self.tool,
            "version": self.version,
            "evidence": evidence or [],
            "new_evidence": False,
            "revisions": 0,
            "trace": [],
        }
        state.update(extra)  # type: ignore[typeddict-item]
        return state

    async def ask(self, user_msg: str, context: ProjectContext,
                  mode: Mode = Mode.ASK) -> AsyncIterator[AgentEvent]:
        """Answer a conceptual question."""
        async for e in self._run(self._state(user_msg, context, mode)):
            yield e

    async def guide(self, user_msg: str, context: ProjectContext) -> AsyncIterator[AgentEvent]:
        """Step-by-step guidance."""
        async for e in self._run(self._state(user_msg, context, Mode.GUIDE)):
            yield e

    async def show(self, user_msg: str, image_bytes: bytes,
                   context: ProjectContext) -> AsyncIterator[AgentEvent]:
        """Visual guidance from a screenshot."""
        st = self._state(user_msg, context, Mode.SHOW, image_bytes=image_bytes)
        async for e in self._run(st):
            yield e

    async def generate(self, user_msg: str, context: ProjectContext) -> AsyncIterator[AgentEvent]:
        """Generate code/config/constraints."""
        async for e in self._run(self._state(user_msg, context, Mode.GENERATE)):
            yield e

    async def debug(self, user_msg: str, evidence: list[Evidence],
                    context: ProjectContext) -> AsyncIterator[AgentEvent]:
        """Systematic fault isolation."""
        st = self._state(user_msg, context, Mode.DEBUG, evidence=evidence,
                         new_evidence=False)
        for ev in evidence:
            if ev.image_bytes:
                st["image_bytes"] = ev.image_bytes
        async for e in self._run(st):
            yield e

    async def translate(self, user_msg: str, source_tool: str, target_tool: str,
                        context: ProjectContext) -> AsyncIterator[AgentEvent]:
        """Map a workflow between tools."""
        st = self._state(user_msg, context, Mode.TRANSLATE,
                         source_tool=source_tool, target_tool=target_tool)
        async for e in self._run(st):
            yield e


_TOOLS = [t.value for t in EDATool if t is not EDATool.UNKNOWN]


def available_tools() -> list[str]:
    """Tool names selectable in the UI."""
    return list(_TOOLS)


def api_key_configured() -> bool:
    """Whether the selected LLM provider has a key."""
    return get_settings().has_llm_key


def get_chat_service() -> ChatService:
    """Create a new chat service instance."""
    return ChatService()