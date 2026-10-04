"""Sidebar controls."""

from __future__ import annotations

import streamlit as st

from backend.models import Mode, Persona
from backend.services.chat_service import api_key_configured, available_tools
from frontend.state import reset_session

MODE_LABELS: dict[Mode, str] = {
    Mode.ASK: "Ask",
    Mode.GUIDE: "Guide Me",
    Mode.SHOW: "Show Me",
    Mode.GENERATE: "Generate",
    Mode.DEBUG: "Debug",
    Mode.TRANSLATE: "Translate",
}


def render_sidebar() -> None:
    """Render tool, version, mode, persona and session controls."""
    with st.sidebar:
        st.markdown('<h3 class="hw-title">HW<span>/</span>Copilot</h3>', unsafe_allow_html=True)
        tools = available_tools()
        st.selectbox("Tool", tools, index=tools.index(st.session_state["tool"]), key="tool")
        st.text_input("Version", key="version", placeholder="e.g. 24.2 / 8.0 / 1.15 / 5.3")
        modes = list(MODE_LABELS)
        st.radio(
            "Mode", modes, index=modes.index(st.session_state["mode"]),
            format_func=lambda m: MODE_LABELS[m], key="mode",
        )
        if st.session_state["mode"] is Mode.TRANSLATE:
            st.selectbox("From", tools, key="source_tool")
            st.selectbox("To", tools, index=min(1, len(tools) - 1), key="target_tool")
        personas = list(Persona)
        st.radio(
            "Persona", personas, index=personas.index(st.session_state["persona"]),
            format_func=lambda p: p.value.capitalize(), key="persona", horizontal=True,
        )
        st.toggle("Show agent trace", key="show_trace")
        if st.button("Reset session", use_container_width=True):
            reset_session()
            st.rerun()
        ok = api_key_configured()
        color = "#3FB950" if ok else "#F85149"
        label = "API key configured" if ok else "API key missing"
        st.markdown(
            f'<span class="mono" style="color:{color}">● {label}</span>',
            unsafe_allow_html=True,
        )