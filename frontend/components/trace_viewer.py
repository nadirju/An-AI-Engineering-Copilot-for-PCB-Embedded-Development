"""Live agent trace viewer."""

from __future__ import annotations

import html

import streamlit as st

from backend.models import TraceEvent


def trace_line(ev: TraceEvent) -> str:
    """Format one trace event as HTML."""
    role = ev.role.value if ev.role else "system"
    return (
        f'<div class="hw-trace"><b>{html.escape(ev.node)}</b> '
        f"[{html.escape(role)}] {html.escape(ev.detail)}</div>"
    )


def render_trace(events: list[TraceEvent]) -> None:
    """Render the agent loop trace.

    Args:
        events: Trace events in execution order.
    """
    st.markdown('<span class="hw-label">Agent trace</span>', unsafe_allow_html=True)
    if not events:
        st.caption("No run yet. Planner → Retrieval → Reasoning → Validation → Conclude.")
        return
    st.markdown("".join(trace_line(e) for e in events), unsafe_allow_html=True)