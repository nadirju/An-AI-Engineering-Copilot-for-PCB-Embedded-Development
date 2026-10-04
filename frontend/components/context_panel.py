"""Collapsible project context panel."""

from __future__ import annotations

import streamlit as st

from backend.models import EDATool, PinMapping, ProjectContext
from frontend.state import get_session

_PCB_OPTIONS: list[EDATool | None] = [None, EDATool.ALTIUM, EDATool.KICAD]
_FW_OPTIONS: list[EDATool | None] = [None, EDATool.STM32, EDATool.ESP_IDF]


def _fmt(tool: EDATool | None) -> str:
    return "—" if tool is None else tool.value


def _parse_pins(raw: str) -> list[PinMapping]:
    pins: list[PinMapping] = []
    for line in raw.splitlines():
        line = line.strip()
        if not line or "=" not in line:
            continue
        sig, rest = line.split("=", 1)
        pin, _, note = rest.partition("#")
        pins.append(PinMapping(signal=sig.strip(), pin=pin.strip(), note=note.strip()))
    return pins


def _split(raw: str) -> list[str]:
    return [x.strip() for x in raw.split(",") if x.strip()]


def demo_context() -> ProjectContext:
    """Return the STM32F401 + BME280 demo project."""
    return ProjectContext(
        project_name="Env Sensor Node",
        objective="Read BME280 over SPI1 with DMA and route the SPI bus cleanly",
        mcu="STM32F401CCU6",
        board_revision="A",
        sensors=["BME280"],
        interfaces=["SPI"],
        pin_map=[
            PinMapping(signal="SPI1_SCK", pin="PA5"),
            PinMapping(signal="SPI1_MISO", pin="PA6"),
            PinMapping(signal="SPI1_MOSI", pin="PA7"),
            PinMapping(signal="BME280_CS", pin="PA4", note="GPIO output, active low"),
        ],
        pcb_tool=EDATool.ALTIUM,
        pcb_tool_version="24",
        firmware_tool=EDATool.STM32,
        firmware_tool_version="1.15",
        toolchain="arm-none-eabi-gcc",
        manufacturing_target="4-layer, 1.6 mm FR4",
    )


def render_context_panel() -> None:
    """Render the editable project context."""
    sess = get_session()
    ctx = sess.context
    with st.expander("Project context", expanded=not ctx.mcu):
        if st.button("Load demo: STM32F401 + BME280 + SPI"):
            sess.context = demo_context()
            st.rerun()
        with st.form("context_form"):
            c1, c2, c3 = st.columns(3)
            name = c1.text_input("Project name", ctx.project_name)
            mcu = c2.text_input("MCU / SoC", ctx.mcu)
            rev = c3.text_input("Board revision", ctx.board_revision)
            objective = st.text_input("Objective", ctx.objective)
            s1, s2 = st.columns(2)
            sensors = s1.text_input("Sensors / ICs (comma-separated)", ", ".join(ctx.sensors))
            ifaces = s2.text_input("Interfaces (comma-separated)", ", ".join(ctx.interfaces))
            pins = st.text_area(
                "Pin map (SIGNAL=PIN # note)",
                "\n".join(
                    f"{p.signal}={p.pin}" + (f" # {p.note}" if p.note else "") for p in ctx.pin_map
                ),
                height=110,
            )
            t1, t2, t3, t4 = st.columns(4)
            pcb = t1.selectbox("PCB tool", _PCB_OPTIONS, _PCB_OPTIONS.index(ctx.pcb_tool)
                               if ctx.pcb_tool in _PCB_OPTIONS else 0, format_func=_fmt)
            pcb_v = t2.text_input("PCB version", ctx.pcb_tool_version)
            fw = t3.selectbox("Firmware tool", _FW_OPTIONS, _FW_OPTIONS.index(ctx.firmware_tool)
                              if ctx.firmware_tool in _FW_OPTIONS else 0, format_func=_fmt)
            fw_v = t4.text_input("Firmware version", ctx.firmware_tool_version)
            u1, u2, u3 = st.columns(3)
            toolchain = u1.text_input("Toolchain", ctx.toolchain)
            rtos = u2.text_input("RTOS (optional)", ctx.rtos)
            mfg = u3.text_input("Manufacturing target", ctx.manufacturing_target)
            err = st.text_area("Current error", ctx.current_error, height=70)
            if st.form_submit_button("Save context"):
                sess.context = ProjectContext(
                    project_name=name, objective=objective, mcu=mcu, board_revision=rev,
                    sensors=_split(sensors), interfaces=_split(ifaces), pin_map=_parse_pins(pins),
                    pcb_tool=pcb, pcb_tool_version=pcb_v, firmware_tool=fw,
                    firmware_tool_version=fw_v, toolchain=toolchain, rtos=rtos,
                    manufacturing_target=mfg, current_error=err,
                    evidence_notes=[e.name for e in sess.evidence],
                )
                st.success("Context saved.")