"""Chat history, rich message cards, and streaming turns."""

from __future__ import annotations

import html
import logging
from typing import AsyncIterator

import streamlit as st

from backend.models import (
    AgentEvent,
    ChatMessage,
    Citation,
    Done,
    Mode,
    Step,
    TextChunk,
    Trace,
    Verdict,
)
from frontend.components.citation import render_chips
from frontend.components.step_card import render_step
from frontend.components.uploader import latest_image
from frontend.state import get_session, iterate_events, make_service

logger = logging.getLogger(__name__)


def _render_vision(done: Done) -> None:
    v = done.vision
    if v is None:
        return
    cls = {Verdict.MATCH: "hw-match", Verdict.MISMATCH: "hw-mismatch"}.get(
        v.verdict, "hw-inconclusive"
    )
    st.markdown(
        f'<div class="hw-card"><span class="hw-label">Screenshot analysis</span> '
        f'<span class="hw-badge {cls}">{v.verdict.value.upper()}</span></div>',
        unsafe_allow_html=True,
    )
    st.markdown(f"**Observed:** {v.observed}")
    st.markdown(f"**Expected:** {v.expected}")
    if v.fix:
        st.markdown(f"**Fix:** {v.fix}")


def _render_translation(rows: list[tuple[str, str]]) -> None:
    if not rows:
        return
    body = "".join(
        f"<tr><td>{html.escape(a)}</td><td>{html.escape(b)}</td></tr>" for a, b in rows
    )
    src = html.escape(st.session_state.get("source_tool", "Source"))
    dst = html.escape(st.session_state.get("target_tool", "Target"))
    st.markdown(
        f'<table class="hw-table"><tr><th>{src}</th><th>{dst}</th></tr>{body}</table>',
        unsafe_allow_html=True,
    )


def _render_fault_tree(tree: list[str]) -> None:
    if not tree:
        return
    st.markdown('<span class="hw-label">Fault domain tree</span>', unsafe_allow_html=True)
    st.code("\n".join(f"├─ {n}" for n in tree[:-1]) + f"\n└─ {tree[-1]}", language="text")


def render_done(done: Done) -> None:
    """Render the structured tail of a response.

    Args:
        done: The end-of-stream event.
    """
    _render_vision(done)
    _render_translation(done.translation_rows)
    _render_fault_tree(done.fault_tree)
    if done.conclusion:
        icon = "✅" if done.resolved else "⚠️"
        st.markdown(f"{icon} **Conclusion:** {done.conclusion}")
    if done.next_action:
        st.markdown(f"**Next diagnostic action:** {done.next_action}")


def render_message(msg: ChatMessage) -> None:
    """Render a stored message.

    Args:
        msg: Chat message from history.
    """
    with st.chat_message(msg.role):
        if msg.role == "user":
            st.markdown(msg.content)
            return
        if msg.citations:
            render_chips(msg.citations)
        if msg.content:
            st.markdown(msg.content)
        for s in msg.steps:
            render_step(s)
        if msg.done:
            render_done(msg.done)


def render_history() -> None:
    """Render the whole conversation."""
    for m in get_session().history:
        render_message(m)


def _open_stream(prompt: str) -> AsyncIterator[AgentEvent] | None:
    sess = get_session()
    mode: Mode = st.session_state["mode"]
    svc = make_service()
    ctx = sess.context
    if mode is Mode.SHOW:
        img = latest_image()
        if img is None:
            st.warning("Show Me needs a screenshot. Attach an image below and ask again.")
            return None
        return svc.show(prompt, img, ctx)
    if mode is Mode.DEBUG:
        return svc.debug(prompt, list(sess.evidence), ctx)
    if mode is Mode.TRANSLATE:
        return svc.translate(prompt, st.session_state["source_tool"],
                             st.session_state["target_tool"], ctx)
    if mode is Mode.GUIDE:
        return svc.guide(prompt, ctx)
    if mode is Mode.GENERATE:
        return svc.generate(prompt, ctx)
    return svc.ask(prompt, ctx, Mode.ASK)


def run_turn(prompt: str) -> None:
    """Run one user turn, streaming rich cards as events arrive.

    Args:
        prompt: The user's message.
    """
    sess = get_session()
    mode: Mode = st.session_state["mode"]
    with st.chat_message("user"):
        st.markdown(prompt)
    stream = _open_stream(prompt)
    if stream is None:
        return
    sess.history.append(ChatMessage(role="user", content=prompt, mode=mode))
    msg = ChatMessage(role="assistant", mode=mode)
    with st.chat_message("assistant"):
        cite_ph = st.empty()
        text_ph = st.empty()
        steps_box = st.container()
        done_box = st.container()
        try:
            for ev in iterate_events(stream):
                if isinstance(ev, TextChunk):
                    msg.content += ev.text
                    text_ph.markdown(msg.content)
                elif isinstance(ev, Citation):
                    msg.citations.append(ev)
                    with cite_ph.container():
                        render_chips(msg.citations)
                elif isinstance(ev, Step):
                    msg.steps.append(ev)
                    with steps_box:
                        render_step(ev)
                elif isinstance(ev, Trace):
                    sess.last_trace.append(ev.event)
                elif isinstance(ev, Done):
                    msg.done = ev
                    if ev.trace:
                        sess.last_trace[:] = ev.trace
                    with done_box:
                        render_done(ev)
        except Exception as exc:  # noqa: BLE001 - surface any failure in the UI
            logger.exception("Turn failed")
            st.error(f"Request failed: {exc}")
    sess.history.append(msg)