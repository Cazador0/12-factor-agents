"""Durable decision traces and session checkpoints.

A trace records what was decided and why in a form any later session can read back: the decision,
a rationale summary, the evidence it rests on, assumptions, tool results, the state it changed, open
questions and the next action. It never stores a model's hidden reasoning (Constitution Art. IX).
"""

from __future__ import annotations

import json
import secrets
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import yaml
from pydantic import BaseModel, Field


def _now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds")


def new_run_id(prefix: str) -> str:
    return f"{prefix}-{datetime.now(UTC).strftime('%Y%m%dT%H%M%S')}-{secrets.token_hex(3)}"


class DecisionTrace(BaseModel):
    id: str
    run_id: str
    node: str
    actor_role: str = "agent"
    decision: str
    rationale_summary: str
    evidence: list[str] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    tool_results: list[str] = Field(default_factory=list)
    changed_state: list[str] = Field(default_factory=list)
    unresolved_questions: list[str] = Field(default_factory=list)
    next_action: str | None = None
    reasoning_ref: str | None = None  # visible reasoning artifact, relative to the run folder
    timestamp: str = Field(default_factory=_now)


class CheckpointDecision(BaseModel):
    id: str
    summary: str
    source: str | None = None


class SessionCheckpoint(BaseModel):
    role: str
    session_id: str
    issue: int | None = None
    spec: str | None = None
    branch: str | None = None
    head_commit: str | None = None
    goal: str
    completed: list[str] = Field(default_factory=list)
    decisions: list[CheckpointDecision] = Field(default_factory=list)
    evidence: list[str] = Field(default_factory=list)
    blockers: list[str] = Field(default_factory=list)
    next_action: str | None = None
    unresolved_questions: list[str] = Field(default_factory=list)
    written_at: str = Field(default_factory=_now)


class TraceLog:
    """Append-only JSONL log for one run, plus its checkpoint and reasoning artifacts."""

    def __init__(self, traces_dir: Path, run_id: str, actor_role: str = "agent", enabled: bool = True):
        self.dir = traces_dir / run_id
        self.run_id = run_id
        self.actor_role = actor_role
        self.enabled = enabled
        self._count = 0

    @property
    def path(self) -> Path:
        return self.dir / "trace.jsonl"

    def record(self, node: str, decision: str, rationale_summary: str, **fields: Any) -> DecisionTrace:
        self._count += 1
        trace = DecisionTrace(
            id=f"D-{self._count:02d}",
            run_id=self.run_id,
            node=node,
            actor_role=fields.pop("actor_role", self.actor_role),
            decision=decision,
            rationale_summary=rationale_summary,
            **fields,
        )
        if self.enabled:
            self.dir.mkdir(parents=True, exist_ok=True)
            with self.path.open("a", encoding="utf-8") as fh:
                fh.write(trace.model_dump_json() + "\n")
        return trace

    def entries(self) -> list[DecisionTrace]:
        if not self.path.is_file():
            return []
        return [DecisionTrace.model_validate_json(ln) for ln in self.path.read_text("utf-8").splitlines() if ln]

    def write_reasoning(self, name: str, markdown: str) -> str | None:
        if not self.enabled:
            return None
        target = self.dir / "reasoning" / f"{name}.md"
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text(markdown, encoding="utf-8")
        return f"reasoning/{name}.md"  # relative to this run's folder, so committed traces stay portable

    def checkpoint(self, cp: SessionCheckpoint) -> Path | None:
        if not self.enabled:
            return None
        self.dir.mkdir(parents=True, exist_ok=True)
        target = self.dir / "checkpoint.yaml"
        target.write_text(yaml.safe_dump({"session_checkpoint": cp.model_dump()}, sort_keys=False), "utf-8")
        return target

    @staticmethod
    def load_checkpoint(path: Path) -> SessionCheckpoint:
        data = yaml.safe_load(path.read_text("utf-8")) or {}
        return SessionCheckpoint.model_validate(data.get("session_checkpoint", data))

    def summary(self) -> str:
        return json.dumps([e.model_dump(include={"id", "node", "decision"}) for e in self.entries()], indent=2)
