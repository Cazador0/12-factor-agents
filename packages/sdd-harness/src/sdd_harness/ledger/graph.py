"""Refinement as a LangGraph state machine.

    START ─┬─ build_ledger ─ plan_round ─┬─ ask (interrupt) ─ apply ─┐
           └────────────────┘            │          ▲                │
                                         └─ finish  └── plan_round ──┘

The ledger sidecar is the durable state; the graph checkpoint only holds the round in flight.
"""

from __future__ import annotations

import operator
from pathlib import Path
from typing import Annotated, Any, TypedDict

from langgraph.graph import END, START, StateGraph
from langgraph.types import Command, interrupt

from ..config import Settings
from . import ledger as lg


class RefineState(TypedDict, total=False):
    root: str
    phase: str
    feature_dir: str | None
    findings: str | None
    base: str | None
    sources: list[str]
    sidecar: str
    round: dict | None
    answers: dict | None
    notes: dict | None
    result: dict
    edits: Annotated[list[dict], operator.add]


def _settings(state: RefineState) -> Settings:
    return Settings.load(Path(state["root"]))


def build_node(state: RefineState) -> dict:
    settings = _settings(state)
    fd = Path(state["feature_dir"]) if state.get("feature_dir") else None
    findings = Path(state["findings"]) if state.get("findings") else None
    sources = [Path(x) for x in state.get("sources") or []]
    _, path = lg.build(settings, state["phase"], fd, findings, state.get("base"), sources)
    return {"sidecar": str(path)}


def plan_node(state: RefineState) -> dict:
    settings = _settings(state)
    ledger = lg.load(Path(state["sidecar"]))
    questions = [] if ledger.finished else lg.next_round(ledger, settings.per_round)
    if not questions:
        return {"round": {"kind": "done"}}
    s = lg.summary(ledger)
    if ledger.rounds and ledger.rounds % settings.checkin_every == 0 and ledger.rounds not in ledger.checkins:
        card = {
            "question": f"{s['decisions'] - s['open']} of {s['decisions']} decisions are settled; "
            f"{s['open']} still need your call. Keep going?",
            "header": "Keep going",
            "multiSelect": False,
            "options": [
                {"label": "Keep going (Recommended)", "description": "Ask the next round."},
                {"label": "Wrap up now", "description": "Stop; open items keep their markers."},
            ],
        }
        return {"round": {"kind": "checkin", "number": ledger.rounds, "card": {"questions": [card]}}}
    progress = (
        f"{ledger.phase.capitalize()} refinement, round {ledger.rounds + 1}: "
        f"{s['decisions'] - s['open']} of {s['decisions']} decisions settled; "
        f"{s['conflicting']} conflicting first."
    )
    return {
        "round": {
            "kind": "questions",
            "number": ledger.rounds + 1,
            "progress": progress,
            "card": lg.to_cards(questions),
            "question_ids": [q["id"] for q in questions],
        }
    }


def ask_node(state: RefineState) -> dict:
    payload = {"sidecar": state["sidecar"], **(state.get("round") or {})}
    reply: Any = interrupt(payload) or {}
    if "answers" in reply:
        return {"answers": reply.get("answers") or {}, "notes": reply.get("notes") or {}}
    return {"answers": reply, "notes": {}}


def apply_node(state: RefineState) -> dict:
    if (state.get("round") or {}).get("kind") == "checkin":
        ledger = lg.load(Path(state["sidecar"]))
        ledger.checkins.append(ledger.rounds)
        raw = " ".join(str(v) for v in (state.get("answers") or {}).values())
        ledger.finished = "wrap" in raw.lower()
        lg.save(ledger, Path(state["sidecar"]))
        return {"result": {"finished": ledger.finished, "checkin": True}}
    result = lg.apply(_settings(state), Path(state["sidecar"]), state.get("answers") or {}, state.get("notes"))
    return {"result": result, "edits": result.get("artifact_edits", [])}


def finish_node(state: RefineState) -> dict:
    ledger = lg.load(Path(state["sidecar"]))
    ledger.finished = True
    lg.save(ledger, Path(state["sidecar"]))
    nxt = lg.NEXT_PHASE.get(ledger.phase, "the next phase")
    return {
        "result": {
            **lg.summary(ledger),
            "rounds": ledger.rounds,
            "sidecar": state["sidecar"],
            "intake": ledger.intake,
            "artifact_edits": state.get("edits", []),
            "next": f"When you're ready, the next phase is {nxt}.",
        }
    }


def build_graph(checkpointer=None):
    g = StateGraph(RefineState)
    g.add_node("build_ledger", build_node)
    g.add_node("plan_round", plan_node)
    g.add_node("ask", ask_node)
    g.add_node("apply", apply_node)
    g.add_node("finish", finish_node)
    g.add_conditional_edges(
        START,
        lambda s: "plan_round" if s.get("sidecar") and Path(s["sidecar"]).is_file() else "build_ledger",
        ["plan_round", "build_ledger"],
    )
    g.add_edge("build_ledger", "plan_round")
    g.add_conditional_edges(
        "plan_round", lambda s: "finish" if s["round"]["kind"] == "done" else "ask", ["finish", "ask"]
    )
    g.add_edge("ask", "apply")
    g.add_conditional_edges(
        "apply", lambda s: "finish" if s["result"].get("finished") else "plan_round", ["finish", "plan_round"]
    )
    g.add_edge("finish", END)
    return g.compile(checkpointer=checkpointer)


def run(thread_id: str, payload: dict | Command, checkpointer) -> dict:
    out = build_graph(checkpointer).invoke(payload, {"configurable": {"thread_id": thread_id}})
    pending = out.get("__interrupt__") if isinstance(out, dict) else None
    if pending:
        return {"status": "awaiting_answers", **pending[0].value}
    return {"status": "finished", **(out.get("result") or {})}
