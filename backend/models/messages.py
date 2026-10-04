"""Messages, events, and structured outputs."""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Annotated, Literal, Optional, Union

from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import AgentRole, DocType, Mode, Verdict


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


class Citation(BaseModel):
    """A retrieved source attached to a claim."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["citation"] = "citation"
    tool: str = ""
    version: str = ""
    component: str = ""
    doc_type: DocType = DocType.OFFICIAL_DOC
    section: str = ""
    publication_date: str = ""
    url: str = ""
    snippet: str = ""
    score: float = 0.0
    confidence: float = 1.0
    assumed: bool = False

    @property
    def label(self) -> str:
        """Short chip label."""
        ver = f" {self.version}" if self.version else ""
        return f"{self.component or self.tool}{ver} - {self.section}".strip(" -")


class Step(BaseModel):
    """A procedural step with verification."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["step"] = "step"
    index: int = 0
    title: str
    instruction: str = ""
    why: str = ""
    expected_outcome: str = ""
    how_to_verify: str = ""
    if_it_fails: str = ""
    code: str = ""
    language: str = ""
    confidence: float = 0.5
    citations: list[Citation] = Field(default_factory=list)


class TextChunk(BaseModel):
    """Streamed text."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["text"] = "text"
    text: str


class TraceEvent(BaseModel):
    """One orchestrator node execution record."""

    model_config = ConfigDict(extra="forbid")

    node: str
    role: Optional[AgentRole] = None
    detail: str = ""
    timestamp: str = Field(default_factory=_now)


class Trace(BaseModel):
    """A trace event emitted to the UI."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["trace"] = "trace"
    event: TraceEvent


class Done(BaseModel):
    """End of stream marker."""

    model_config = ConfigDict(extra="forbid")

    kind: Literal["done"] = "done"
    conclusion: str = ""
    resolved: bool = True
    next_action: str = ""
    verdict: Optional[Verdict] = None
    vision: Optional["VisionResult"] = None
    translation_rows: list[tuple[str, str]] = Field(default_factory=list)
    fault_tree: list[str] = Field(default_factory=list)
    trace: list[TraceEvent] = Field(default_factory=list)


AgentEvent = Annotated[
    Union[TextChunk, Citation, Step, Trace, Done],
    Field(discriminator="kind"),
]


class VisionResult(BaseModel):
    """Screenshot analysis output."""

    model_config = ConfigDict(extra="forbid")

    observed: str = ""
    expected: str = ""
    verdict: Verdict = Verdict.INCONCLUSIVE
    fix: str = ""


class ValidationResult(BaseModel):
    """Validation outcome for a single step."""

    model_config = ConfigDict(extra="forbid")

    step: str
    expected_outcome: str = ""
    how_to_verify: str = ""
    confidence: float = 0.0
    passed: bool = False


class Evidence(BaseModel):
    """User-supplied evidence."""

    model_config = ConfigDict(extra="forbid")

    name: str
    media_type: str = "text/plain"
    text: str = ""
    image_bytes: Optional[bytes] = None


class ChatMessage(BaseModel):
    """A stored chat message."""

    model_config = ConfigDict(extra="forbid")

    role: Literal["user", "assistant"]
    content: str = ""
    mode: Mode = Mode.ASK
    steps: list[Step] = Field(default_factory=list)
    citations: list[Citation] = Field(default_factory=list)
    done: Optional[Done] = None


Done.model_rebuild()