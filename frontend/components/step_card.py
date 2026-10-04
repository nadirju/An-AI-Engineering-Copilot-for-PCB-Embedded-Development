"""Step card: instruction, why, verification, expected observation."""

from __future__ import annotations

import html

import streamlit as st

from backend.models import Step
from frontend.components.citation import render_chips


def render_step(step: Step) -> None:
    """Render a procedural step as a rich card.

    Args:
        step: The step to display.
    """
    st.markdown(
        f'<div class="hw-card"><span class="hw-label">Step {step.index}</span>'
        f"<h4>{html.escape(step.title)}</h4></div>",
        unsafe_allow_html=True,
    )
    if step.instruction:
        st.markdown(step.instruction)
    if step.code:
        st.code(step.code, language=step.language or None)
    left, right = st.columns(2)
    with left:
        if step.why:
            st.markdown("**Why**")
            st.markdown(step.why)
        if step.if_it_fails:
            st.markdown("**If it fails**")
            st.markdown(step.if_it_fails)
    with right:
        if step.how_to_verify:
            st.markdown("**How to verify**")
            st.markdown(step.how_to_verify)
        if step.expected_outcome:
            st.markdown("**Expected observation**")
            st.markdown(step.expected_outcome)
    if step.citations:
        render_chips(step.citations)