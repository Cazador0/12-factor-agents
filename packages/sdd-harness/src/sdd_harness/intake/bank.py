"""The question bank: rank by impact × uncertainty and pick each round's questions."""

from __future__ import annotations

from dataclasses import dataclass, field

from ..reasoning import ReasoningRecorder
from .model import SETTLED, Intake, Option, Question
from .rows import BY_ID, GROUP_ORDER, OPENING_ROWS


def scaffold_question(intake: Intake, row_id: str) -> Question | None:
    """The next unused scaffold for a row: its opener, then its follow-ups; ``None`` once exhausted."""
    rowdef = BY_ID[row_id]
    mine = [q for q in intake.questions if row_id in q.rows]
    used = {q.text for q in mine}
    # A row that already has a question needs its follow-ups, never its opener again (a re-ask).
    variants = rowdef.followups if mine else (rowdef.scaffold, *rowdef.followups)
    sc = next((v for v in variants if v and v["text"] not in used), None)
    if sc is None:
        return None
    options = [Option(**o) for o in sc["options"]]
    multi = bool(sc.get("multi_select"))
    if not multi and options:
        options[0] = options[0].model_copy(update={"recommended": True, "why": "the usual starting point"})
    return Question(
        id=intake.next_qid(),
        header=sc["header"],
        row=row_id,
        text=sc["text"],
        options=options,
        impact="high" if rowdef.priority <= 2 or row_id in OPENING_ROWS else "medium",
        uncertainty="high",
        multi_select=multi,
        generic=True,
    )


def sort_key(q: Question, round_no: int) -> tuple:
    rowdef = BY_ID.get(q.rows[0] if q.rows else q.row)
    group = GROUP_ORDER.get(rowdef.group, 9) if rowdef else 9
    opening = 0 if (round_no <= 1 and any(r in OPENING_ROWS for r in q.rows)) else 1
    num = int(q.id[1:]) if q.id[1:].isdigit() else 999
    return (group, opening, -q.score, rowdef.priority if rowdef else 9, num)


@dataclass
class RoundPlan:
    kind: str  # questions | checkin | done
    round: int
    questions: list[Question] = field(default_factory=list)
    progress: str = ""
    reasoning: object | None = None
    card: dict | None = None
    new_questions: list[Question] = field(default_factory=list)


def unsettled_rows(intake: Intake) -> list[str]:
    return [r.id for r in intake.rows if r.status not in SETTLED and r.status != "Open"]


def choose(intake: Intake, per_round: int, round_no: int) -> tuple[list[Question], list[Question], ReasoningRecorder]:
    """Pick up to ``per_round`` questions for the unsettled rows, adding scaffolds where a row has none."""
    why = ReasoningRecorder(f"Which questions should round {round_no} ask?")
    gaps = unsettled_rows(intake)
    s_gaps = why.observe(f"Unsettled rows: {', '.join(gaps) or 'none'}", ["intake: Sufficiency check"])
    new: list[Question] = []
    for row_id in gaps:
        has_open = any(row_id in q.rows and q.state in {"pending", "unknown"} for q in intake.questions)
        if not has_open and row_id in BY_ID:
            q = scaffold_question(intake, row_id)
            if q is None:  # scaffolds exhausted: the host must write a sharper follow-up
                why.ask(f"{row_id} still needs: {intake.row(row_id).still_needed if intake.row(row_id) else '?'}")
                continue
            intake.questions.append(q)
            new.append(q)
    if new:
        why.infer(
            f"Rows with no open question get a generic scaffold to sharpen: {', '.join(q.row for q in new)}",
            builds_on=[s_gaps],
        )
    candidates = [
        q
        for q in intake.questions
        if q.state in {"pending", "unknown"} and any(r in gaps for r in q.rows) and q.tries < 2
    ]
    candidates.sort(key=lambda q: sort_key(q, round_no))
    picked: list[Question] = []
    rows_used: set[str] = set()
    for q in candidates:  # first pass: one question per row
        if len(picked) >= per_round:
            break
        if not set(q.rows) & rows_used:
            picked.append(q)
            rows_used.update(q.rows)
    for q in candidates:  # second pass: fill remaining slots
        if len(picked) >= per_round:
            break
        if q not in picked:
            picked.append(q)
    s_rank = why.infer(
        "Ranked by group (constitution, spec, plan), opening rows in round 1, then impact × uncertainty, "
        "then speckit.specify's priority (scope, security and privacy, experience, technical)",
        builds_on=[s_gaps],
    )
    for q in picked:
        why.observe(
            f"{q.id} ({q.row}, score {q.score}{', generic' if q.generic else ''}): {q.text}",
            [f"intake: Question bank › {q.id}"],
        )
    why.infer(f"Selected {', '.join(q.id for q in picked) or 'nothing'}", builds_on=[s_rank])
    return picked, new, why


def checkin_due(intake: Intake, every: int) -> bool:
    rnd = intake.round
    if rnd == 0 or rnd % every:
        return False
    return not any(str(r.get("Round", "")).startswith(f"check-in after {rnd}") for r in intake.session_log)


def checkin_card(intake: Intake) -> dict:
    settled = [BY_ID[r.id].plain for r in intake.rows if r.status in SETTLED and r.id in BY_ID]
    thin = [BY_ID[r.id].plain for r in intake.rows if r.status not in SETTLED and r.id in BY_ID]
    text = (
        f"We have enough for {', '.join(settled[:4]) or 'the basics'}; "
        f"still thin: {', '.join(thin[:4]) or 'nothing'}. Keep going?"
    )
    return {
        "question": text,
        "header": "Keep going",
        "multiSelect": False,
        "options": [
            {"label": "Keep going (Recommended)", "description": "Ask the next round of questions."},
            {"label": "Wrap up now", "description": "Finish with what we have; gaps become open items."},
        ],
    }


def assumption_check_due(intake: Intake) -> bool:
    ok, n = intake.counts("S")
    unconfirmed = [a for a in intake.assumptions if a.endswith("— unconfirmed")]
    asked = any(q.header == "Defaults" for q in intake.questions)
    return bool(n) and ok >= max(1, n - 2) and bool(unconfirmed) and not asked


def assumption_question(intake: Intake) -> Question:
    unconfirmed = [a for a in intake.assumptions if a.endswith("— unconfirmed")][:4]
    options = []
    for a in unconfirmed:
        label_id = a.split(":", 1)[0].strip()
        body = a.split(":", 1)[1].rsplit("— unconfirmed", 1)[0].strip() if ":" in a else a
        options.append(Option(label=f"Keep {label_id}", description=body))
    if len(options) == 1:
        options.append(Option(label="Change it", description="Leave the default out and ask about it instead."))
    return Question(
        id=intake.next_qid(),
        header="Defaults",
        row="S10",
        text="Which of these defaults should stay as written?",
        options=options,
        impact="medium",
        uncertainty="medium",
        multi_select=True,
    )
