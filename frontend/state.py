"""Streamlit session-state helpers."""

from __future__ import annotations

import asyncio
import logging
from typing import Any, AsyncIterator, Iterator

import streamlit as st

from backend.context.session_store import SessionStore
from backend.models import AgentEvent, Mode, Persona
from backend.services.chat_service import ChatService, available_tools

logger = logging.getLogger(__name__)

_DEFAULTS: dict[str, Any] = {
    "mode": Mode.GUIDE,
    "persona": Persona.INTERMEDIATE,
    "tool": "STM32CubeIDE/CubeMX",
    "version": "",
    "source_tool": "KiCad",
    "target_tool": "Altium Designer",
    "show_trace": True,
    "uploader_nonce": 0,
}


def init_state() -> None:
    """Populate session state with defaults on first run."""
    if "session" not in st.session_state:
        st.session_state["session"] = SessionStore()
    for key, value in _DEFAULTS.items():
        st.session_state.setdefault(key, value)
    tools = available_tools()
    if st.session_state["tool"] not in tools:
        st.session_state["tool"] = tools[0]


def get_session() -> SessionStore:
    """Return the per-browser-session store."""
    return st.session_state["session"]


def reset_session() -> None:
    """Clear context, history, evidence and trace."""
    get_session().reset()
    st.session_state["uploader_nonce"] += 1


def make_service() -> ChatService:
    """Build a chat service for the current sidebar selections.

    A fresh instance is created per turn so async HTTP clients are always
    bound to the event loop that runs the turn.
    """
    return ChatService(
        tool=st.session_state["tool"],
        version=st.session_state["version"],
        persona=st.session_state["persona"],
    )


def iterate_events(stream: AsyncIterator[AgentEvent]) -> Iterator[AgentEvent]:
    """Bridge an async event stream into a synchronous iterator.

    Args:
        stream: Async iterator from ``ChatService``.

    Yields:
        Events in order of arrival.
    """
    loop = asyncio.new_event_loop()
    try:
        while True:
            try:
                yield loop.run_until_complete(stream.__anext__())
            except StopAsyncIteration:
                break
    finally:
        try:
            loop.run_until_complete(stream.aclose())  # type: ignore[attr-defined]
        except (RuntimeError, AttributeError) as exc:
            logger.debug("Stream close skipped: %s", exc)
        loop.close()