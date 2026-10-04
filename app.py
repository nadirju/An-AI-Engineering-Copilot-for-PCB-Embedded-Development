"""Streamlit entry point for the Hardware Engineering Copilot."""

from __future__ import annotations

import logging

import streamlit as st

from backend.config import get_settings
from backend.logging_config import configure_logging
from backend.services.seed import seed_knowledge_base
from frontend.components.chat import render_history, run_turn
from frontend.components.context_panel import render_context_panel
from frontend.components.sidebar import render_sidebar
from frontend.components.trace_viewer import render_trace
from frontend.components.uploader import render_uploader
from frontend.layout import render_header, render_key_banner, split_columns
from frontend.state import get_session, init_state
from frontend.styles import inject_styles

st.set_page_config(page_title="HW Copilot", page_icon="🔧", layout="wide")
configure_logging(get_settings().log_level)
logger = logging.getLogger(__name__)


@st.cache_resource(show_spinner="Indexing knowledge base...")
def _seed() -> int:
    """Seed the knowledge base once per process."""
    try:
        return seed_knowledge_base()
    except Exception as exc:  # noqa: BLE001 - never crash the UI on seeding
        logger.error("Seeding failed: %s", exc)
        return 0


def main() -> None:
    """Compose the page."""
    inject_styles()
    init_state()
    _seed()
    render_sidebar()
    render_header()
    key_ok = render_key_banner()
    render_context_panel()
    prompt = st.chat_input(
        "Ask about your hardware workflow...", disabled=not key_ok
    )
    main_col, rail = split_columns(st.session_state["show_trace"])
    sess = get_session()
    with main_col:
        render_history()
        with st.expander("Attach evidence (screenshot / log / config)"):
            render_uploader()
        if prompt:
            sess.last_trace.clear()
            run_turn(prompt)
    if rail is not None:
        with rail:
            render_trace(sess.last_trace)


main()