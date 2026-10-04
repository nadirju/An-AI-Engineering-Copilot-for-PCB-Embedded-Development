"""Evidence uploader (images, logs, configs)."""

from __future__ import annotations

import logging

import streamlit as st

from backend.models import Evidence
from frontend.state import get_session

logger = logging.getLogger(__name__)

_IMAGE_TYPES = ("png", "jpg", "jpeg", "webp")
_TEXT_TYPES = ("txt", "log", "csv", "json", "ioc", "c", "h", "cpp", "ini", "cfg", "md")
_MAX_TEXT = 20_000


def render_uploader() -> None:
    """Render the uploader and attach new files to the session."""
    sess = get_session()
    nonce = st.session_state["uploader_nonce"]
    files = st.file_uploader(
        "Attach screenshot, log, or config",
        type=list(_IMAGE_TYPES + _TEXT_TYPES),
        accept_multiple_files=True,
        key=f"uploader_{nonce}",
    )
    known = {(e.name, len(e.image_bytes or e.text)) for e in sess.evidence}
    for f in files or []:
        data = f.getvalue()
        ext = f.name.rsplit(".", 1)[-1].lower() if "." in f.name else ""
        if ext in _IMAGE_TYPES:
            item = Evidence(
                name=f.name,
                media_type=f.type or "image/png",
                image_bytes=data,
            )
        else:
            text = data.decode("utf-8", errors="replace")[:_MAX_TEXT]
            item = Evidence(name=f.name, media_type=f.type or "text/plain", text=text)
        if (item.name, len(item.image_bytes or item.text)) in known:
            continue
        sess.add_evidence(item)
        logger.info("Attached evidence %s", item.name)
    if sess.evidence:
        st.caption("Evidence: " + ", ".join(e.name for e in sess.evidence))


def latest_image() -> bytes | None:
    """Return the most recent uploaded image bytes, if any."""
    for e in reversed(get_session().evidence):
        if e.image_bytes:
            return e.image_bytes
    return None