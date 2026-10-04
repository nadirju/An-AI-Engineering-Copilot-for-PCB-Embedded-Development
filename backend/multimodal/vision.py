"""Screenshot analysis returning observed / expected / verdict / fix."""

from __future__ import annotations

import json
import logging
import re

from backend.llm.client import LLMClient
from backend.llm.prompt_loader import load_prompt
from backend.models.enums import Verdict
from backend.models.messages import VisionResult

logger = logging.getLogger(__name__)

_JSON = re.compile(r"\{.*\}", re.DOTALL)


def _media_type(data: bytes) -> str:
    if data.startswith(b"\x89PNG"):
        return "image/png"
    if data.startswith(b"\xff\xd8"):
        return "image/jpeg"
    if data[:4] == b"RIFF" and data[8:12] == b"WEBP":
        return "image/webp"
    return "image/png"


async def analyze_image(
    llm: LLMClient, image_bytes: bytes, question: str, project_summary: str = ""
) -> VisionResult:
    """Analyse a screenshot against the user's question.

    Args:
        llm: LLM client with vision support.
        image_bytes: Raw image bytes.
        question: Short question about the image.
        project_summary: Project context text.

    Returns:
        A :class:`VisionResult`; ``INCONCLUSIVE`` on any failure.
    """
    system = (
        load_prompt("system")
        + "\n\nYou analyse engineering screenshots. Reply with ONLY a JSON object with keys "
        '"observed", "expected", "verdict" (match|mismatch|inconclusive), "fix".'
    )
    user = f"Project:\n{project_summary}\n\nQuestion: {question}"
    try:
        raw = await llm.vision(system, user, image_bytes, _media_type(image_bytes))
    except Exception as exc:  # noqa: BLE001
        logger.error("Vision call failed: %s", exc)
        return VisionResult(observed="Image analysis unavailable.", verdict=Verdict.INCONCLUSIVE)
    m = _JSON.search(raw)
    if not m:
        return VisionResult(observed=raw[:500], verdict=Verdict.INCONCLUSIVE)
    try:
        d = json.loads(m.group(0))
        verdict = Verdict(str(d.get("verdict", "inconclusive")).lower())
    except (json.JSONDecodeError, ValueError):
        return VisionResult(observed=raw[:500], verdict=Verdict.INCONCLUSIVE)
    return VisionResult(
        observed=str(d.get("observed", "")),
        expected=str(d.get("expected", "")),
        verdict=verdict,
        fix=str(d.get("fix", "")),
    )