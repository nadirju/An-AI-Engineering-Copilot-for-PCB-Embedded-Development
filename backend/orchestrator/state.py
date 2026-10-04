"""Graph state."""

from __future__ import annotations

from typing import Any, Optional, TypedDict

from backend.models.enums import Mode, Persona
from backend.models.messages import (
    Citation,
    Evidence,
    Step,
    TraceEvent,
    ValidationResult,
    VisionResult,
)
from backend.models.project_context import ProjectContext


class GraphState(TypedDict, total=False):
    """State passed between orchestrator nodes."""

    user_msg: str
    mode: Mode
    persona: Persona
    context: ProjectContext
    tool: str
    version: str
    evidence: list[Evidence]
    image_bytes: Optional[bytes]
    plan: dict[str, Any]
    citations: list[Citation]
    steps: list[Step]
    answer: str
    validation: list[ValidationResult]
    revisions: int
    new_evidence: bool
    fault_tree: list[str]
    cause: str
    resolved: bool
    next_action: str
    vision: Optional[VisionResult]
    translation_rows: list[tuple[str, str]]
    source_tool: str
    target_tool: str
    tutor_text: str
    conclusion: str
    trace: list[TraceEvent]