"""Citation chips."""

from __future__ import annotations

import html

import streamlit as st

from backend.models import Citation


def chip_html(c: Citation) -> str:
    """Render one citation chip as HTML.

    Args:
        c: Citation to render.

    Returns:
        An anchor element with a tooltip.
    """
    tip = (
        f"{c.tool} | {c.component} | v{c.version or '?'} | {c.doc_type.value} | "
        f"{c.section} | {c.publication_date} | confidence {c.confidence:.2f}"
        f"{' | SECONDARY SOURCE' if c.doc_type.is_secondary else ''}"
    )
    cls = "hw-chip low" if c.confidence < 0.7 or c.assumed else "hw-chip"
    href = html.escape(c.url or "#", quote=True)
    return (
        f'<a class="{cls}" href="{href}" target="_blank" rel="noopener" '
        f'title="{html.escape(tip, quote=True)}">{html.escape(c.label)}</a>'
    )


def render_chips(citations: list[Citation]) -> None:
    """Render a row of citation chips.

    Args:
        citations: Citations to show (deduplicated by label).
    """
    seen: set[str] = set()
    chips: list[str] = []
    for c in citations:
        if c.label in seen:
            continue
        seen.add(c.label)
        chips.append(chip_html(c))
    if chips:
        st.markdown(
            '<span class="hw-label">Sources</span><br>' + "".join(chips),
            unsafe_allow_html=True,
        )