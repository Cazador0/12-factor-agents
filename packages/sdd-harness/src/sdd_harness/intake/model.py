"""The intake as data. The Markdown file stays the source of truth; this is its parsed view."""

from __future__ import annotations

from typing import Literal

from pydantic import BaseModel, Field

RowStatus = Literal["Missing", "Partial", "Sufficient", "Delegated", "N/A", "Open"]
Level = Literal["high", "medium", "low"]
LEVEL = {"high": 3, "medium": 2, "low": 1}
SETTLED = {"Sufficient", "Delegated", "N/A"}


class Row(BaseModel):
    id: str
    name: str
    status: RowStatus = "Missing"
    evidence: str = "—"
    still_needed: str = "—"


class Option(BaseModel):
    label: str
    description: str
    recommended: bool = False
    why: str | None = None


class Question(BaseModel):
    id: str
    header: str
    row: str
    text: str
    options: list[Option]
    impact: Level = "medium"
    uncertainty: Level = "medium"
    multi_select: bool = False
    generic: bool = False
    # pending | answered | other | delegated | not-asked | open | unknown
    state: str = "pending"
    chosen: list[str] = Field(default_factory=list)  # option letters
    answer: str = "pending"  # the rendered **Answer** text
    note: str | None = None
    round: int | None = None
    tries: int = 0

    @property
    def rows(self) -> list[str]:
        """A question can feed several rows: ``row`` reads ``S2`` or ``C4, T6``."""
        return [r.strip() for r in self.row.split(",") if r.strip()]

    @property
    def score(self) -> int:
        return LEVEL[self.impact] * LEVEL[self.uncertainty]

    @property
    def is_open(self) -> bool:
        return self.state in {"pending", "unknown"}


class Intake(BaseModel):
    title: str
    status: str = "Draft"
    scope: Literal["project", "feature"] = "feature"
    feature: str = "pending"
    slug: str
    created: str
    idea_type: str = "other"
    idea: str
    sources: str = "none"
    interpretation: str = ""
    rows: list[Row] = Field(default_factory=list)
    assumptions: list[str] = Field(default_factory=list)
    questions: list[Question] = Field(default_factory=list)
    clarifications: list[str] = Field(default_factory=list)
    session_date: str | None = None
    session_log: list[dict[str, str]] = Field(default_factory=list)
    open_items: list[str] = Field(default_factory=list)

    def row(self, row_id: str) -> Row | None:
        return next((r for r in self.rows if r.id == row_id), None)

    def question(self, qid: str) -> Question | None:
        return next((q for q in self.questions if q.id == qid), None)

    def next_qid(self) -> str:
        nums = [int(q.id[1:]) for q in self.questions if q.id[1:].isdigit()]
        return f"Q{(max(nums) if nums else 0) + 1}"

    @property
    def round(self) -> int:
        rounds = [int(r["Round"]) for r in self.session_log if str(r.get("Round", "")).isdigit()]
        return max(rounds) if rounds else 0

    def counts(self, group_prefix: str | None = None) -> tuple[int, int]:
        rows = [r for r in self.rows if group_prefix is None or r.id.startswith(group_prefix)]
        return sum(r.status in SETTLED for r in rows), len(rows)
