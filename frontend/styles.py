"""Custom CSS: Linear meets oscilloscope."""

from __future__ import annotations

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600&family=JetBrains+Mono:wght@400;500&display=swap');
:root { --bg:#0B0F14; --panel:#11171F; --line:#1E2732; --accent:#2F81F7; --ok:#3FB950; --bad:#F85149; --warn:#D29922; --mut:#8B98A5; }
html, body, [class*="css"] { font-family:'Inter',sans-serif; }
code, pre, .mono { font-family:'JetBrains Mono',monospace !important; }
#MainMenu, footer, header[data-testid="stHeader"] { visibility:hidden; height:0; }
.block-container { padding-top:1.2rem; max-width:1200px; }
section[data-testid="stSidebar"] { background:var(--panel); border-right:1px solid var(--line); }
.hw-title { font-weight:600; letter-spacing:.02em; }
.hw-title span { color:var(--accent); }
.hw-card { background:var(--panel); border:1px solid var(--line); border-left:3px solid var(--accent);
  border-radius:6px; padding:.8rem 1rem; margin:.5rem 0; }
.hw-card h4 { margin:0 0 .4rem 0; font-size:1rem; }
.hw-label { color:var(--mut); font-size:.72rem; text-transform:uppercase; letter-spacing:.08em; }
.hw-chip { display:inline-block; font-family:'JetBrains Mono',monospace; font-size:.72rem;
  padding:.1rem .5rem; margin:.15rem .25rem .15rem 0; border:1px solid var(--accent);
  color:var(--accent); border-radius:999px; text-decoration:none; }
.hw-chip.low { border-color:var(--warn); color:var(--warn); }
.hw-badge { font-family:'JetBrains Mono',monospace; font-size:.72rem; padding:.1rem .45rem; border-radius:4px; }
.hw-match { background:rgba(63,185,80,.15); color:var(--ok); }
.hw-mismatch { background:rgba(248,81,73,.15); color:var(--bad); }
.hw-inconclusive { background:rgba(210,153,34,.15); color:var(--warn); }
.hw-trace { font-family:'JetBrains Mono',monospace; font-size:.75rem; color:var(--mut);
  border-left:1px dashed var(--line); padding-left:.6rem; margin-left:.3rem; }
.hw-trace b { color:var(--accent); }
.hw-banner { background:rgba(210,153,34,.1); border:1px solid var(--warn); border-radius:6px; padding:.8rem 1rem; }
table.hw-table { width:100%; border-collapse:collapse; font-size:.9rem; }
table.hw-table th, table.hw-table td { border:1px solid var(--line); padding:.4rem .6rem; text-align:left; }
table.hw-table th { background:var(--panel); color:var(--accent); }
</style>
"""


def inject_styles() -> None:
    """Inject the global stylesheet into the Streamlit page."""
    import streamlit as st

    st.markdown(CSS, unsafe_allow_html=True)