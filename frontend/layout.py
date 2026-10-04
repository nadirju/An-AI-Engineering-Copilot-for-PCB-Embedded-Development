"""Page-level layout helpers."""

from __future__ import annotations

import streamlit as st
from streamlit.delta_generator import DeltaGenerator

from backend.services.chat_service import api_key_configured


def render_header() -> None:
    """Render the application title bar."""
    st.markdown(
        '<h2 class="hw-title">HW<span>/</span>Copilot '
        '<span class="hw-label">One AI. Every hardware development workflow.</span></h2>',
        unsafe_allow_html=True,
    )


def render_key_banner() -> bool:
    """Show a setup banner when no API key is configured.

    Returns:
        True when the key is configured and the app can call the LLM.
    """
    if api_key_configured():
        return True
    st.markdown(
        '<div class="hw-banner"><b>API key not configured.</b><br>'
        "Set <code>ANTHROPIC_API_KEY</code> in a local <code>.env</code> file, or add it under "
        "<b>Settings &rarr; Secrets</b> on Streamlit Community Cloud. To use OpenAI instead, set "
        "<code>LLM_PROVIDER=openai</code> and <code>OPENAI_API_KEY</code>. "
        "Then reload this page.</div>",
        unsafe_allow_html=True,
    )
    return False


def split_columns(show_trace: bool) -> tuple[DeltaGenerator, DeltaGenerator | None]:
    """Create the main column and the optional right rail.

    Args:
        show_trace: Whether the trace rail is visible.

    Returns:
        Tuple of (main column, rail column or None).
    """
    if not show_trace:
        return st.container(), None
    main, rail = st.columns([3, 1], gap="medium")
    return main, rail