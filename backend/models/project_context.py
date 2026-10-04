"""Project context model."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, ConfigDict, Field

from backend.models.enums import EDATool


class PinMapping(BaseModel):
    """A single pin assignment."""

    model_config = ConfigDict(strict=True, extra="forbid")

    signal: str
    pin: str
    note: str = ""


class ProjectContext(BaseModel):
    """Everything the copilot knows about the user's project."""

    model_config = ConfigDict(strict=True, extra="forbid", validate_assignment=True)

    project_name: str = ""
    objective: str = ""
    mcu: str = ""
    board_revision: str = ""
    sensors: list[str] = Field(default_factory=list)
    interfaces: list[str] = Field(default_factory=list)
    pin_map: list[PinMapping] = Field(default_factory=list)
    pcb_tool: Optional[EDATool] = None
    pcb_tool_version: str = ""
    firmware_tool: Optional[EDATool] = None
    firmware_tool_version: str = ""
    toolchain: str = ""
    rtos: str = ""
    manufacturing_target: str = ""
    current_error: str = ""
    evidence_notes: list[str] = Field(default_factory=list)

    def summary(self) -> str:
        """Render a compact text summary for prompts."""
        pins = ", ".join(f"{p.signal}={p.pin}" for p in self.pin_map) or "n/a"
        rows = [
            f"Project: {self.project_name or 'n/a'}",
            f"Objective: {self.objective or 'n/a'}",
            f"MCU/SoC: {self.mcu or 'n/a'}",
            f"Board revision: {self.board_revision or 'n/a'}",
            f"Sensors/ICs: {', '.join(self.sensors) or 'n/a'}",
            f"Interfaces: {', '.join(self.interfaces) or 'n/a'}",
            f"Pin map: {pins}",
            f"PCB tool: {self._tool(self.pcb_tool, self.pcb_tool_version)}",
            f"Firmware tool: {self._tool(self.firmware_tool, self.firmware_tool_version)}",
            f"Toolchain: {self.toolchain or 'n/a'}",
            f"RTOS: {self.rtos or 'n/a'}",
            f"Manufacturing target: {self.manufacturing_target or 'n/a'}",
            f"Current error: {self.current_error or 'none'}",
        ]
        if self.evidence_notes:
            rows.append("Evidence: " + "; ".join(self.evidence_notes))
        return "\n".join(rows)

    @staticmethod
    def _tool(tool: Optional[EDATool], version: str) -> str:
        if tool is None:
            return "n/a"
        return f"{tool.value} {version}".strip()