"""Session operations on an intake file: create, plan a round, record answers, finish.

Each operation re-reads the file, so a session survives a lost process: the Markdown file is the
memory, and the next round is recomputed from it deterministically.
"""

from __future__ import annotations

import re
from datetime import date
from pathlib import Path

from pydantic import BaseModel, ConfigDict, Field

from ..config import Settings
from ..reasoning import TraceLog
from . import document as doc
from .bank import RoundPlan, assumption_check_due, assumption_question, checkin_card, checkin_due, choose
from .cards import lint_question, read_answer, to_card
from .model import Intake, Option, Question, Row
from .rows import BY_ID, rows_for
from .sufficiency import all_settled, progress_line, rate

# ---------------------------------------------------------------- inputs


class DraftOption(BaseModel):
    model_config = ConfigDict(extra="forbid")
    label: str
    description: str
    recommended: bool = False
    why: str | None = None


class DraftQuestion(BaseModel):
    model_config = ConfigDict(extra="forbid")
    header: str
    row: str
    text: str
    options: list[DraftOption]
    impact: str = "medium"
    uncertainty: str = "medium"
    multi_select: bool = False


class DraftRow(BaseModel):
    model_config = ConfigDict(extra="forbid")
    id: str
    status: str = "Missing"
    evidence: str = "—"
    still_needed: str = "—"


class DraftInput(BaseModel):
    """What the host model (or the Claude draft node) contributes to a Draft intake."""

    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    interpretation: str | None = None
    idea_type: str | None = None
    sources: str | None = None
    software: bool = True
    rows: list[DraftRow] = Field(default_factory=list)

    @classmethod
    def from_host(cls, data: dict) -> DraftInput:
        """Accept ``rows`` as a list of ``{id, …}`` or as a mapping ``{"S1": {…}}``."""
        data = dict(data)
        if isinstance(data.get("rows"), dict):
            data["rows"] = [{"id": k, **v} for k, v in data["rows"].items()]
        return cls.model_validate(data)

    assumptions: list[str] = Field(default_factory=list)
    questions: list[DraftQuestion] = Field(default_factory=list)


# ---------------------------------------------------------------- helpers

_SECRETS = [
    (re.compile(r"(?i)(https?://)[^/\s:@]+:[^/\s@]+@"), r"\1[REDACTED]@"),
    (re.compile(r"\b(sk-(?:ant-)?[A-Za-z0-9_-]{16,})\b"), "[REDACTED]"),
    (re.compile(r"\b(gh[pousr]_[A-Za-z0-9]{20,})\b"), "[REDACTED]"),
    (re.compile(r"\b(AKIA[0-9A-Z]{16})\b"), "[REDACTED]"),
    (re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9._~+/=-]{12,}"), r"\1 [REDACTED]"),
    (re.compile(r"(?i)\b(password|passwd|secret|token|api[_-]?key)\s*[:=]\s*\S+"), r"\1=[REDACTED]"),
]
IDEA_TYPES = {"new-capability", "improvement", "fix", "exploration", "cost-saving", "compliance", "other"}
_STOPWORDS = set("a an the and or to of for in on with that this be is are it i we me my our an app want".split())


def redact(text: str) -> str:
    for rx, repl in _SECRETS:
        text = rx.sub(repl, text)
    return text


def slugify(text: str, max_words: int = 4) -> str:
    raw = re.sub(r"[\s_]+", "-", text.lower())
    raw = re.sub(r"[^a-z0-9-]", "", raw)
    raw = re.sub(r"-{2,}", "-", raw).strip("-")
    words = [w for w in raw.split("-") if w and w not in _STOPWORDS] or [w for w in raw.split("-") if w]
    return "-".join(words[:max_words]) or "idea"


def normalize_slug(slug: str) -> str:
    s = re.sub(r"[\s_]+", "-", slug.lower())
    s = re.sub(r"[^a-z0-9-]", "", s)
    return re.sub(r"-{2,}", "-", s).strip("-")


def unique_dir(base: Path, slug: str) -> Path:
    candidate, n = base / slug, 2
    while candidate.exists():
        candidate, n = base / f"{slug}-{n}", n + 1
    return candidate


def safe_intakes_dir(settings: Settings) -> Path:
    """Refuse when .specify or the intakes folder is a symlink leading outside the project."""
    root = settings.root.resolve()
    target = settings.intakes_dir
    for p in (root / ".specify", target):
        if p.is_symlink() and not p.resolve().is_relative_to(root):
            raise PermissionError(f"{p} is a symlink leading outside the project; refusing to write")
    return target


def detect_scope(root: Path) -> str:
    const = root / ".specify" / "memory" / "constitution.md"
    if not const.is_file():
        return "project"
    return "project" if re.search(r"\[(PROJECT_NAME|PRINCIPLE_\d+_NAME)\]", const.read_text("utf-8")) else "feature"


def _question_from_draft(intake: Intake, dq: DraftQuestion) -> Question:
    options = [Option(**o.model_dump()) for o in dq.options]
    return Question(
        id=intake.next_qid(),
        header=dq.header,
        row=dq.row,
        text=dq.text,
        options=options,
        impact=dq.impact if dq.impact in {"high", "medium", "low"} else "medium",
        uncertainty=dq.uncertainty if dq.uncertainty in {"high", "medium", "low"} else "medium",
        multi_select=dq.multi_select,
    )


def _trace(settings: Settings, slug: str) -> TraceLog:
    return TraceLog(settings.traces_dir, f"intake-{slug}", "intake", enabled=bool(settings.get("reasoning.traces")))


# ---------------------------------------------------------------- operations


def create(
    settings: Settings,
    idea: str,
    *,
    slug: str | None = None,
    scope: str = "auto",
    draft: DraftInput | None = None,
    grounding: list[str] | None = None,
) -> tuple[Path, list[str]]:
    """Write the Draft intake. Returns its path and any lint problems in host-supplied questions."""
    idea = redact(idea.strip())
    if not idea:
        raise ValueError("No idea given; ask for one in a single short sentence.")
    draft = draft or DraftInput()
    base = safe_intakes_dir(settings)
    folder = unique_dir(base, normalize_slug(slug) if slug else slugify(draft.title or idea))
    scope = detect_scope(settings.root) if scope == "auto" else scope
    today = date.today().isoformat()

    rows = [Row(id=r.id, name=r.name) for r in rows_for(scope, draft.software)]
    given = {d.id: d for d in draft.rows}
    for row in rows:
        if not draft.software and row.id.startswith("T"):
            row.status, row.evidence, row.still_needed = "N/A", "idea involves no software", "—"
        if row.id in given:
            d = given[row.id]
            row.status = d.status if d.status in {"Missing", "Partial", "Sufficient", "N/A"} else "Missing"
            row.evidence, row.still_needed = d.evidence, d.still_needed
        if row.status in {"Missing", "Partial"} and row.still_needed in {"—", ""}:
            row.still_needed = BY_ID[row.id].bar

    intake = Intake(
        title=draft.title or idea.split("\n", 1)[0][:80],
        scope=scope,  # type: ignore[arg-type]
        feature="N/A (project scope)" if scope == "project" else "pending",
        slug=folder.name,
        created=today,
        idea_type=draft.idea_type if draft.idea_type in IDEA_TYPES else "other",
        idea=idea,
        sources=draft.sources or "none",
        interpretation=draft.interpretation or "",
        rows=rows,
        assumptions=[f"D{i + 1}: {a}" if not re.match(r"^~*D\d+:", a) else a for i, a in enumerate(draft.assumptions)],
        session_date=today,
    )
    problems: list[str] = []
    for dq in draft.questions:
        if not set(r.strip() for r in dq.row.split(",")) <= {r.id for r in rows}:
            problems.append(f"question '{dq.text}' targets unknown row {dq.row}")
            continue
        q = _question_from_draft(intake, dq)
        issues = lint_question(q)
        if issues:
            problems.append(f"{q.id} ({dq.header}): " + "; ".join(issues))
        intake.questions.append(q)

    intake.rows = rate(intake)
    ok, n = intake.counts()
    settled = [r.id for r in intake.rows if r.status in {"Sufficient", "N/A"}]
    grounded = "; ".join(grounding or []) or "idea only"
    intake.session_log.append(
        {
            "Round": "0",
            "Questions": "—",
            "Answered": "—",
            "Rows sufficient": f"{ok} of {n}",
            "Notes": f"Settled before asking: {', '.join(settled) or 'none'}. Drawn from: {grounded}.",
        }
    )
    folder.mkdir(parents=True, exist_ok=False)
    path = folder / "intake.md"
    path.write_text(doc.render(intake), encoding="utf-8")
    _trace(settings, intake.slug).record(
        "draft",
        f"Wrote Draft intake {settings.rel(path)} ({scope} scope)",
        f"{ok} of {n} rows settled from the idea and its sources; {len(intake.questions)} drafted questions.",
        evidence=grounding or [],
        changed_state=[settings.rel(path)],
        next_action="plan round 1",
    )
    return path, problems


def load(path: Path) -> tuple[str, Intake]:
    text = path.read_text("utf-8")
    return text, doc.parse(text)


def plan_round(settings: Settings, path: Path) -> RoundPlan:
    text, intake = load(path)
    if intake.status.startswith("Answered"):
        return RoundPlan("done", intake.round, progress=f"Intake already reads {intake.status}.")
    if checkin_due(intake, settings.checkin_every):
        return RoundPlan("checkin", intake.round, progress="Check-in", card={"questions": [checkin_card(intake)]})
    intake.rows = rate(intake)
    if all_settled(intake):
        return RoundPlan("done", intake.round, progress="Every row is sufficient, delegated or N/A.")
    round_no = intake.round + 1
    new: list[Question] = []
    if assumption_check_due(intake):
        aq = assumption_question(intake)
        intake.questions.append(aq)
        new.append(aq)
    picked, scaffolds, why = choose(intake, settings.per_round, round_no)
    new += scaffolds
    if new and new[0].header == "Defaults" and new[0] not in picked:
        picked = [new[0], *picked][: settings.per_round]
    if not picked:
        return RoundPlan("done", intake.round, progress="No askable questions remain; open rows become open items.")
    for q in new:  # persist scaffolds so the round is reproducible from the file
        text = doc.replace_question(text, q)
    if new:
        path.write_text(text, encoding="utf-8")
    focus = [BY_ID[q.rows[0]].plain for q in picked if q.rows and q.rows[0] in BY_ID]
    reasoning = why.conclude(f"Round {round_no} asks {', '.join(q.id for q in picked)}")
    return RoundPlan(
        "questions",
        round_no,
        questions=picked,
        progress=progress_line(intake, round_no, focus),
        reasoning=reasoning,
        card={"questions": [to_card(q) for q in picked]},
        new_questions=new,
    )


def _answer_text(q: Question, reading, round_no: int) -> tuple[str, str]:
    """(Answer line, Clarifications answer)."""
    if reading.state == "answered":
        labels = [f"{x}. {q.options['ABCD'.index(x)].label}" for x in reading.letters]
        return f"{'; '.join(labels)} — round {round_no}", "; ".join(lbl.split(". ", 1)[1] for lbl in labels)
    if reading.state == "other":
        return f'Other — "{reading.words}" — round {round_no}', f'"{reading.words}"'
    if reading.state == "delegated":
        rec = next((o for o in q.options if o.recommended), q.options[0] if q.options else None)
        pick = q.options["ABCD".index(reading.letters[0])] if reading.letters and not rec else rec
        label = pick.label if pick else "the recommendation"
        reason = pick.why if pick and pick.why else "recommended from the idea and earlier answers"
        return f"Delegated — agent chose {label}: {reason} — round {round_no}", f"Delegated — agent chose {label}"
    return f"Unknown — person was not sure — round {round_no}", "not sure"


def record(settings: Settings, path: Path, plan: RoundPlan, answers: dict, notes: dict | None = None) -> dict:
    """Write one round's answers into the file in place and re-rate the rows."""
    text, intake = load(path)
    notes = notes or {}
    session = intake.session_date or date.today().isoformat()
    trace = _trace(settings, intake.slug)
    if plan.kind == "checkin":
        raw = next(iter(answers.values()), "") if answers else ""
        stop = "wrap" in str(raw).lower()
        text = doc.append_log(
            text,
            {
                "Round": f"check-in after {intake.round}",
                "Questions": "—",
                "Answered": "—",
                "Rows sufficient": "{} of {}".format(*intake.counts()),
                "Notes": "Person chose to wrap up." if stop else "Person chose to keep going.",
            },
        )
        path.write_text(text, encoding="utf-8")
        trace.record("checkin", "Wrap up" if stop else "Keep going", f"Check-in answer: {raw}")
        return finish(settings, path, stopped=True) if stop else {"stopped": False, "round": intake.round}

    round_no = plan.round
    answered, stop = 0, False
    asked_ids = [q.id for q in plan.questions]
    for planned in plan.questions:
        q = intake.question(planned.id)
        if q is None:
            continue
        raw = answers.get(q.text, answers.get(q.id))
        reading = read_answer(q, raw, notes.get(q.text) or notes.get(q.id))
        if reading.state == "stop":
            stop = True
            continue
        q.round = round_no
        q.note = reading.note or q.note
        line, clar = _answer_text(q, reading, round_no)
        if reading.state == "unknown":
            q.tries += 1
            q.state = "unknown" if q.tries < 2 else "open"
            q.answer = line if q.tries < 2 else f"Open — person was not sure twice — round {round_no}"
        else:
            q.state = reading.state
            q.chosen = reading.letters if reading.state in {"answered", "delegated"} else []
            if reading.state == "delegated" and not q.chosen:
                rec_idx = next((i for i, o in enumerate(q.options) if o.recommended), 0)
                q.chosen = ["ABCD"[rec_idx]] if q.options else []
            q.answer = line
            answered += 1
        if q.header == "Defaults" and reading.state == "answered":
            text = _apply_assumption_check(text, intake, q)
        text = doc.replace_question(text, q)
        if reading.state != "unknown" or q.state == "open":
            text = doc.append_clarification(text, f"- Q: {q.text} → A: {clar}", session)
    intake.rows = rate(intake)
    for row in intake.rows:
        text = doc.update_row(text, row)
    ok, n = intake.counts()
    text = doc.append_log(
        text,
        {
            "Round": str(round_no),
            "Questions": ", ".join(asked_ids),
            "Answered": str(answered),
            "Rows sufficient": f"{ok} of {n}",
            "Notes": "Person asked to stop." if stop else "",
        },
    )
    text = doc.set_field(text, "Status", f"In session (round {round_no})")
    path.write_text(text, encoding="utf-8")
    trace.record(
        "record",
        f"Recorded round {round_no}: {answered} of {len(asked_ids)} answered",
        f"{ok} of {n} rows settled after the round.",
        evidence=[f"{path.name} › {qid}" for qid in asked_ids],
        changed_state=[settings.rel(path)],
        next_action="finish" if stop else "plan the next round",
    )
    if stop:
        return finish(settings, path, stopped=True)
    return {"stopped": False, "round": round_no, "answered": answered, "rows_sufficient": f"{ok} of {n}"}


def _apply_assumption_check(text: str, intake: Intake, q: Question) -> str:
    kept = {q.options["ABCD".index(x)].label.removeprefix("Keep ").strip() for x in q.chosen}
    for opt in q.options:
        if not opt.label.startswith("Keep "):
            continue
        aid = opt.label.removeprefix("Keep ").strip()
        old = next((a for a in intake.assumptions if a.startswith(f"{aid}:")), None)
        if not old:
            continue
        if aid in kept:
            new = old.replace("— unconfirmed", f"— confirmed by {q.id}")
        else:
            new = f"~~{old.replace(' — unconfirmed', '')}~~ not kept at {q.id}; ask about it instead"
            fq = Question(
                id=intake.next_qid(),
                header="Default",
                row="S10",
                text=f"The default '{opt.description}' was not kept. What should happen instead?",
                options=[
                    Option(
                        label="Decide during planning",
                        description="Planning picks within your limits.",
                        recommended=True,
                        why="keeps the session moving",
                    ),
                    Option(label="Leave it out", description="The spec states no default here."),
                ],
                impact="medium",
                uncertainty="high",
            )
            intake.questions.append(fq)
            text = doc.replace_question(text, fq)
        text = doc.replace_bullet(text, "Assumptions", old, new)
    return text


def finish(settings: Settings, path: Path, stopped: bool = False) -> dict:
    """Close the session: unsettled rows become Open items, every question shows its fate."""
    text, intake = load(path)
    intake.rows = rate(intake)
    opened: list[str] = []
    for q in intake.questions:
        if q.state in {"pending", "unknown"}:
            q.state, q.answer = "open", "Open — session ended before it was answered"
            text = doc.replace_question(text, q)
    intake.rows = rate(intake)
    for row in intake.rows:
        if row.status in {"Missing", "Partial", "Open"}:
            cites = ", ".join(q.id for q in intake.questions if row.id in q.rows) or "no question"
            phase = (
                "for planning"
                if row.id.startswith("T")
                else ("for the constitution" if row.id.startswith("C") else "for specify")
            )
            item = (
                f"[NEEDS CLARIFICATION: {BY_ID[row.id].plain if row.id in BY_ID else row.name} — "
                f"{row.still_needed}] — {phase} — row {row.id} was {row.status} when the session ended — "
                f"cites {cites} — UNVERIFIED until the person answers"
            )
            opened.append(item)
            row = row.model_copy(update={"status": "Open"})
        text = doc.update_row(text, row)
    existing = set(intake.open_items)
    for item in opened:
        if item not in existing:
            text = doc.append_bullet(text, "Open Items", item, "- None.")
    n_open = len(set(intake.open_items) | set(opened))
    status = "Answered" if n_open == 0 else f"Answered — {n_open} open items"
    text = doc.set_field(text, "Status", status)
    path.write_text(text, encoding="utf-8")
    _, final = load(path)
    answered = sum(q.state in {"answered", "other", "delegated"} for q in final.questions)
    ok, n = final.counts()
    _trace(settings, final.slug).record(
        "finish",
        f"Set Status: {status}",
        f"{answered} questions answered over {final.round} rounds; {ok} of {n} rows settled.",
        unresolved_questions=opened,
        next_action="hand the intake to /speckit-specify when the person is ready",
    )
    return {
        "stopped": stopped,
        "status": status,
        "path": str(path),
        "answered": answered,
        "rounds": final.round,
        "rows_sufficient": f"{ok} of {n}",
        "open_items": n_open,
    }


def set_row(settings: Settings, path: Path, row_id: str, status: str, evidence: str, still: str = "—") -> None:
    text, intake = load(path)
    row = intake.row(row_id)
    if row is None:
        raise KeyError(row_id)
    text = doc.update_row(text, row.model_copy(update={"status": status, "evidence": evidence, "still_needed": still}))
    path.write_text(text, encoding="utf-8")


def resolve(settings: Settings, path: Path, qid: str, by: str, reason: str) -> None:
    """Mark a bank question settled without asking: ``Not asked — resolved by Q2 (reason)``."""
    text, intake = load(path)
    q = intake.question(qid)
    if q is None:
        raise KeyError(qid)
    q.state, q.answer = "not-asked", f"Not asked — resolved by {by} ({reason})"
    path.write_text(doc.replace_question(text, q), encoding="utf-8")


def add_questions(settings: Settings, path: Path, questions: list[DraftQuestion]) -> list[str]:
    text, intake = load(path)
    problems = []
    for dq in questions:
        q = _question_from_draft(intake, dq)
        issues = lint_question(q)
        if issues:
            problems.append(f"{q.id} ({dq.header}): " + "; ".join(issues))
        intake.questions.append(q)
        text = doc.replace_question(text, q)
    path.write_text(text, encoding="utf-8")
    return problems


def replace_question(settings: Settings, path: Path, qid: str, dq: DraftQuestion) -> list[str]:
    """Rewrite a pending question (e.g. sharpen a generic scaffold to the idea)."""
    text, intake = load(path)
    old = intake.question(qid)
    if old is None or old.state not in {"pending", "unknown"}:
        raise ValueError(f"{qid} is not pending; answered questions are never rewritten")
    q = _question_from_draft(intake, dq).model_copy(update={"id": qid, "tries": old.tries})
    path.write_text(doc.replace_question(text, q), encoding="utf-8")
    return lint_question(q)


def add_assumption(settings: Settings, path: Path, text_: str, citation: str | None = None) -> str:
    text, intake = load(path)
    nums = [int(m.group(1)) for a in intake.assumptions if (m := re.match(r"^~*D(\d+):", a))]
    label = f"D{(max(nums) if nums else 0) + 1}"
    line = f"{label}: {text_} — {citation or 'unconfirmed'}"
    path.write_text(doc.append_bullet(text, "Assumptions", line, "- None yet."), encoding="utf-8")
    return label
