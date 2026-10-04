"""In-memory session store (no disk writes)."""

from __future__ import annotations

from dataclasses import dataclass, field

from backend.models.messages import ChatMessage, Evidence, TraceEvent
from backend.models.project_context import ProjectContext


@dataclass
class SessionStore:
    """Holds project context, history, evidence and last trace for a session."""

    context: ProjectContext = field(default_factory=ProjectContext)
    history: list[ChatMessage] = field(default_factory=list)
    evidence: list[Evidence] = field(default_factory=list)
    last_trace: list[TraceEvent] = field(default_factory=list)

    def add_evidence(self, item: Evidence) -> None:
        """Attach evidence, keeping the 10 most recent items."""
        self.evidence.append(item)
        self.evidence = self.evidence[-10:]

    def reset(self) -> None:
        """Clear everything."""
        self.context = ProjectContext()
        self.history.clear()
        self.evidence.clear()
        self.last_trace.clear()