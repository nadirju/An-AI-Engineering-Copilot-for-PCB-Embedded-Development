"""Tests for the project context and session store."""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from backend.context.session_store import SessionStore
from backend.models import EDATool, Evidence, PinMapping, ProjectContext


def test_summary_contains_key_fields() -> None:
    ctx = ProjectContext(
        mcu="STM32F401",
        sensors=["BME280"],
        pin_map=[PinMapping(signal="SCK", pin="PA5")],
        pcb_tool=EDATool.ALTIUM,
        pcb_tool_version="24",
    )
    text = ctx.summary()
    assert "STM32F401" in text
    assert "BME280" in text
    assert "SCK=PA5" in text
    assert "Altium Designer 24" in text


def test_strict_types_rejected() -> None:
    with pytest.raises(ValidationError):
        ProjectContext(mcu=5)  # type: ignore[arg-type]


def test_extra_fields_forbidden() -> None:
    with pytest.raises(ValidationError):
        ProjectContext(unknown_field="x")  # type: ignore[call-arg]


def test_session_store_reset_and_evidence_cap() -> None:
    store = SessionStore()
    for i in range(15):
        store.add_evidence(Evidence(name=f"log{i}.txt", text="x"))
    assert len(store.evidence) == 10
    assert store.evidence[-1].name == "log14.txt"
    store.context = ProjectContext(mcu="ESP32")
    store.reset()
    assert store.context.mcu == ""
    assert store.evidence == []
    assert store.history == []