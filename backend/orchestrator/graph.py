"""LangGraph state machine: classify -> plan -> route -> retrieve -> reason ->
generate -> validate -> (feedback | conclude)."""

from __future__ import annotations

import logging
from typing import Any, Iterable, Optional

from langgraph.graph import END, StateGraph

from backend.agents import (
    AgentContext,
    DebugAgent,
    ImplementationAgent,
    KnowledgeAgent,
    PlannerAgent,
    ToolSpecialistAgent,
    TutorAgent,
    ValidationAgent,
)
from backend.llm.client import LLMClient
from backend.models.enums import AgentRole, Mode, Persona
from backend.models.messages import Step, TraceEvent
from backend.multimodal.vision import analyze_image
from backend.orchestrator.router import after_validate, route_target
from backend.orchestrator.state import GraphState
from backend.rag.retriever import retrieve

logger = logging.getLogger(__name__)

_TEXT_KEYS: tuple[str, ...] = (
    "task",
    "description",
    "title",
    "text",
    "summary",
    "name",
    "query",
    "step",
    "objective",
)


def _plan_text(item: Any) -> str:
    """Coerce a planner list item (str, dict, model, other) into text.

    Planner output is not guaranteed to match the declared schema, because
    some providers do not enforce it. Strings pass through, dicts are searched
    for a human-readable key, and anything else is stringified.

    Args:
        item: One element of a planner-produced list.

    Returns:
        A non-None string (possibly empty).
    """
    if item is None:
        return ""
    if isinstance(item, str):
        return item.strip()
    if isinstance(item, dict):
        for key in _TEXT_KEYS:
            value = item.get(key)
            if isinstance(value, str) and value.strip():
                return value.strip()
        parts = [str(v).strip() for v in item.values() if isinstance(v, (str, int, float))]
        return " - ".join(p for p in parts if p)
    dump = getattr(item, "model_dump", None)
    if callable(dump):
        return _plan_text(dump())
    return str(item).strip()


def _plan_texts(items: Any) -> list[str]:
    """Coerce a planner list (or a single value) into a list of non-empty strings.

    Args:
        items: A list of planner items, a single item, or ``None``.

    Returns:
        Non-empty text for each item.
    """
    if items is None:
        return []
    if isinstance(items, (str, dict)) or not isinstance(items, Iterable):
        items = [items]
    return [t for t in (_plan_text(i) for i in items) if t]


def _trace(state: GraphState, node: str, role: Optional[AgentRole], detail: str) -> list[TraceEvent]:
    events = list(state.get("trace", []))
    events.append(TraceEvent(node=node, role=role, detail=detail))
    return events


def _ctx(state: GraphState, with_citations: bool = True) -> AgentContext:
    ev = state.get("evidence", [])
    text = "\n".join(f"[{e.name}] {e.text[:1500]}" for e in ev if e.text)
    notes: list[str] = []
    plan = state.get("plan") or {}
    subtasks = _plan_texts(plan.get("subtasks"))
    if subtasks:
        notes.append("Subtasks: " + "; ".join(subtasks))
    if state.get("cause"):
        notes.append(f"Prior diagnosis: {state['cause']}")
    return AgentContext(
        user_msg=state["user_msg"],
        context=state["context"],
        persona=state.get("persona", Persona.INTERMEDIATE),
        citations=state.get("citations", []) if with_citations else [],
        notes=notes,
        evidence_text=text,
    )


def build_graph(llm: LLMClient, max_revisions: int = 2) -> Any:
    """Compile the orchestrator graph.

    Args:
        llm: LLM client shared by all agents.
        max_revisions: Maximum validation bounce count.

    Returns:
        A compiled LangGraph runnable.
    """
    planner = PlannerAgent(llm)
    specialist = ToolSpecialistAgent(llm)
    knowledge = KnowledgeAgent(llm)
    implementer = ImplementationAgent(llm)
    debugger = DebugAgent(llm)
    validator = ValidationAgent(llm)
    tutor = TutorAgent(llm)

    async def classify(state: GraphState) -> dict[str, Any]:
        mode = state["mode"]
        ctx = state["context"]
        tool = state.get("tool") or (
            ctx.firmware_tool.value if ctx.firmware_tool else ""
        )
        detail = f"mode={mode.value} tool={tool or 'unknown'} version={state.get('version') or 'unknown'}"
        return {"trace": _trace(state, "classify", None, detail), "tool": tool}

    async def plan(state: GraphState) -> dict[str, Any]:
        p = await planner.plan(_ctx(state, False), state.get("tool", ""))
        p["subtasks"] = _plan_texts(p.get("subtasks")) or [state["user_msg"]]
        p["retrieval_queries"] = _plan_texts(p.get("retrieval_queries")) or [state["user_msg"]]
        for key in ("objective", "domain", "tool", "version", "component"):
            p[key] = _plan_text(p.get(key))
        return {
            "plan": p,
            "trace": _trace(state, "plan", AgentRole.PLANNER,
                            f"domain={p.get('domain')} subtasks={len(p['subtasks'])}"),
        }

    async def route(state: GraphState) -> dict[str, Any]:
        return {"trace": _trace(state, "route", None, f"next={route_target(state)}")}

    async def do_retrieve(state: GraphState) -> dict[str, Any]:
        p = state.get("plan", {})
        queries = _plan_texts(p.get("retrieval_queries")) or [state["user_msg"]]
        domain = _plan_text(p.get("domain")) or None
        tool = state.get("tool") or None
        seen: dict[str, Any] = {}
        for q in queries[:3]:
            for c in retrieve(q, tool=None if tool in (None, "Unknown") else tool,
                              version=state.get("version"), domain=domain, k=4):
                seen.setdefault(f"{c.component}|{c.section}", c)
        cites = sorted(seen.values(), key=lambda c: c.score, reverse=True)[:6]
        return {
            "citations": cites,
            "trace": _trace(state, "retrieve", AgentRole.KNOWLEDGE, f"{len(cites)} chunks"),
        }

    async def reason(state: GraphState) -> dict[str, Any]:
        detail = "re-reasoning with new evidence" if state.get("new_evidence") else "synthesising"
        updates: dict[str, Any] = {"new_evidence": False}
        if state.get("mode") == Mode.SHOW and state.get("image_bytes"):
            result = await analyze_image(llm, state["image_bytes"], state["user_msg"],
                                         state["context"].summary())
            updates["vision"] = result
            detail = f"vision verdict={result.verdict.value}"
        updates["trace"] = _trace(state, "reason", AgentRole.KNOWLEDGE, detail)
        return updates

    async def generate(state: GraphState) -> dict[str, Any]:
        mode, tool, ver = state["mode"], state.get("tool", ""), state.get("version", "")
        ctx = _ctx(state)
        upd: dict[str, Any] = {}
        role = AgentRole.IMPLEMENTATION
        if mode == Mode.ASK:
            upd["answer"] = await knowledge.explain(ctx)
            role = AgentRole.KNOWLEDGE
        elif mode == Mode.GUIDE:
            upd["steps"] = await specialist.procedure(ctx, tool, ver)
            role = AgentRole.TOOL_SPECIALIST
        elif mode == Mode.GENERATE:
            upd["steps"] = await implementer.implement(ctx, tool, ver)
        elif mode == Mode.DEBUG:
            role = AgentRole.DEBUG
            tree, steps, cause, resolved, nxt = await debugger.diagnose(ctx, tool, ver)
            upd.update(fault_tree=_plan_texts(tree), steps=steps, cause=cause,
                       resolved=resolved, next_action=nxt)
        elif mode == Mode.SHOW:
            role = AgentRole.TOOL_SPECIALIST
            v = state.get("vision")
            if v is not None:
                ctx.notes.append(f"Screenshot analysis: observed={v.observed}; expected={v.expected}; fix={v.fix}")
            upd["steps"] = await specialist.procedure(ctx, tool, ver)
        elif mode == Mode.TRANSLATE:
            role = AgentRole.KNOWLEDGE
            rows_data = await llm.complete(
                knowledge.system_prompt(),
                knowledge.user_prompt(
                    ctx, f"Translate workflow concepts from {state.get('source_tool')} to {state.get('target_tool')}."),
                schema={"type": "object", "properties": {"rows": {"type": "array", "items": {
                    "type": "object", "properties": {"source": {"type": "string"}, "target": {"type": "string"}},
                    "required": ["source", "target"]}}, "summary": {"type": "string"}}, "required": ["rows"]},
                max_tokens=1800,
            )
            d = rows_data if isinstance(rows_data, dict) else {}
            upd["translation_rows"] = [(_plan_text(r.get("source")), _plan_text(r.get("target")))
                                        for r in d.get("rows", []) if isinstance(r, dict)]
            upd["answer"] = _plan_text(d.get("summary"))
        if state.get("persona") == Persona.BEGINNER and (upd.get("steps") or upd.get("answer")):
            material = upd.get("answer") or "\n".join(s.title + ": " + s.instruction for s in upd["steps"])
            upd["tutor_text"] = await tutor.teach(ctx, material)
        upd["trace"] = _trace(state, "generate", role, f"steps={len(upd.get('steps', []))}")
        return upd

    async def validate(state: GraphState) -> dict[str, Any]:
        steps: list[Step] = state.get("steps", [])
        results = validator.check_steps(steps)
        failing = validator.failing_titles(results)
        return {
            "validation": results,
            "max_revisions": max_revisions,
            "trace": _trace(state, "validate", AgentRole.VALIDATION,
                            f"{len(results) - len(failing)}/{len(results)} steps measurable"),
        }

    async def feedback(state: GraphState) -> dict[str, Any]:
        steps = state.get("steps", [])
        failing = validator.failing_titles(state.get("validation", []))
        revised = await validator.revise(steps, failing) if failing else steps
        return {
            "steps": revised,
            "revisions": state.get("revisions", 0) + 1,
            "new_evidence": False,
            "trace": _trace(state, "feedback", AgentRole.VALIDATION,
                            f"revising {len(failing)} step(s)"),
        }

    async def conclude(state: GraphState) -> dict[str, Any]:
        results = state.get("validation", [])
        unmet = [r.step for r in results if not r.passed]
        if unmet:
            concl = "Unresolved: steps lack measurable criteria - " + ", ".join(unmet)
            resolved = False
        else:
            concl = state.get("cause") or "Procedure validated with measurable criteria."
            resolved = state.get("resolved", True)
        return {
            "conclusion": concl,
            "resolved": resolved,
            "trace": _trace(state, "conclude", None, "resolved" if resolved else "needs follow-up"),
        }

    g = StateGraph(GraphState)
    for name, fn in (("classify", classify), ("plan", plan), ("route", route),
                     ("retrieve", do_retrieve), ("reason", reason), ("generate", generate),
                     ("validate", validate), ("feedback", feedback), ("conclude", conclude)):
        g.add_node(name, fn)
    g.set_entry_point("classify")
    g.add_edge("classify", "plan")
    g.add_edge("plan", "route")
    g.add_edge("route", "retrieve")
    g.add_edge("retrieve", "reason")
    g.add_edge("reason", "generate")
    g.add_edge("generate", "validate")
    g.add_conditional_edges("validate", after_validate,
                            {"feedback": "feedback", "conclude": "conclude"})
    g.add_edge("feedback", "validate")
    g.add_edge("conclude", END)
    return g.compile()


async def run_graph(graph: Any, state: GraphState) -> GraphState:
    """Execute the compiled graph.

    Args:
        graph: Compiled graph from :func:`build_graph`.
        state: Initial state.

    Returns:
        The final state.
    """
    state.setdefault("trace", [])
    state.setdefault("revisions", 0)
    result = await graph.ainvoke(state)
    return result  # type: ignore[return-value]