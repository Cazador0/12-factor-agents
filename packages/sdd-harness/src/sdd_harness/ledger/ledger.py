"""The decision ledger: built before any question, written into the intake, answered round by round.

State lives in two places, both in the repository: a ledger table under the intake's
``## Phase Refinements`` (for people) and a JSON sidecar beside it (for the engine). Answers go into
the intake, and into the artifact in its own format; edits that change an artifact's meaning are
returned to the host as ``artifact_edits`` rather than guessed.
"""

from __future__ import annotations

import json
import re
import subprocess
from datetime import date
from pathlib import Path

from pydantic import BaseModel, Field

from .. import markdown as md
from ..config import Settings
from ..intake.cards import lint_card, read_answer
from ..intake.model import Option, Question
from ..rag.bm25 import tokenize
from ..reasoning import TraceLog
from .classify import Classifier, gather
from .extract import Decision, extract

GROUP_ORDER = {"Conflicting": 0, "Unbacked": 1, "Delegated": 2, "Backed": 3}
LEVEL = {"high": 3, "medium": 2, "low": 1}
HEADERS = {
    "requirement": "Requirement",
    "success-criterion": "Success",
    "assumption": "Default",
    "edge-case": "Edge case",
    "story-priority": "Priority",
    "needs-clarification": "Open point",
    "principle": "Principle",
    "constitution-rule": "Rule",
    "technical-context": "Tech choice",
    "research-decision": "Research",
    "entity": "Data model",
    "contract": "Contract",
    "checklist-item": "Checklist",
    "task": "Task",
    "analyze-finding": "Finding",
    "unplanned-change": "Unplanned",
}
NEXT_PHASE = {
    "constitution": "specify",
    "specify": "planning",
    "plan": "tasks",
    "checklist": "tasks",
    "tasks": "implementation",
    "analyze": "implementation",
    "implement": "review",
    "converge": "implementation",
}


class LedgerRow(BaseModel):
    n: int
    id: str
    text: str
    where: str
    kind: str
    impact: str
    group: str
    evidence: list[str] = Field(default_factory=list)
    reason: str = ""
    uncertainty: str = "high"
    conflict_cite: str | None = None
    conflict_text: str | None = None
    question: dict | None = None  # Question model dump
    answer: str = "—"
    round: int | None = None


class Ledger(BaseModel):
    phase: str
    feature_dir: str | None
    intake: str | None
    created: str
    rows: list[LedgerRow]
    rounds: int = 0
    finished: bool = False
    checkins: list[int] = Field(default_factory=list)
    clarifications: list[str] = Field(default_factory=list)

    def pending(self) -> list[LedgerRow]:
        return [r for r in self.rows if r.question and r.answer in {"—", "pending"}]


# ---------------------------------------------------------------- locating


def feature_dir_from_scripts(root: Path) -> Path | None:
    script = root / ".specify" / "scripts" / "bash" / "check-prerequisites.sh"
    if not script.is_file():
        return None
    out = subprocess.run(
        ["bash", str(script), "--json", "--paths-only"], cwd=root, capture_output=True, text=True, check=False
    )
    m = re.search(r'"FEATURE_DIR"\s*:\s*"([^"]+)"', out.stdout)
    return Path(m.group(1)) if m else None


def find_intake(settings: Settings, phase: str, feature_dir: Path | None) -> Path | None:
    base = settings.intakes_dir
    if not base.is_dir():
        return None
    intakes = sorted(base.glob("*/intake.md"))
    if phase == "constitution":
        return next((p for p in intakes if "**Scope**: project" in p.read_text("utf-8")), None)
    if feature_dir is None:
        return None
    rel = str(feature_dir.relative_to(settings.root)) if feature_dir.is_relative_to(settings.root) else str(feature_dir)
    for p in intakes:
        text = p.read_text("utf-8")
        if re.search(rf"^\*\*Feature\*\*:\s*{re.escape(rel)}\s*$", text, re.M):
            return p
    spec = feature_dir / "spec.md"
    spec_terms = set(tokenize(spec.read_text("utf-8")[:3000])) if spec.is_file() else set()
    best, best_s = None, 0.0
    for p in intakes:  # link an Answered feature intake still reading "pending" that holds this idea
        text = p.read_text("utf-8")
        if "**Feature**: pending" not in text or "**Status**: Answered" not in text:
            continue
        idea = set(tokenize(md.section_text(text, "Idea", 2)))
        s = len(idea & spec_terms) / (len(idea) or 1)
        if s > best_s:
            best, best_s = p, s
    if best and best_s >= 0.5:
        best.write_text(md.replace_line(best.read_text("utf-8"), r"^\*\*Feature\*\*:", f"**Feature**: {rel}"), "utf-8")
        return best
    return None


def sidecar_path(settings: Settings, phase: str, intake: Path | None, feature_dir: Path | None) -> Path:
    if intake is not None:
        return intake.parent / f"refine-{phase}.json"
    base = feature_dir if feature_dir is not None else settings.root / ".specify" / "memory"
    return base / "refinements" / f"{phase}.json"


# ---------------------------------------------------------------- questions


def _short(text: str, n: int = 140) -> str:
    text = re.sub(r"\s+", " ", text).strip().rstrip("?.")
    return text if len(text) <= n else text[: n - 1].rsplit(" ", 1)[0] + "…"


def question_for(row: LedgerRow, phase: str, qid: str) -> Question:
    header = HEADERS.get(row.kind, "Decision")[:12]
    nxt = NEXT_PHASE.get(phase, "planning")
    if row.group == "Conflicting":
        return Question(
            id=qid,
            header="Conflict",
            row=row.id,
            text=f"{row.where} says “{_short(row.text, 90)}” but {row.conflict_cite} says "
            f"“{_short(row.conflict_text or '', 90)}”. Which should stand?",
            options=[
                Option(
                    label="Follow the earlier decision",
                    description="Rewrite the artifact line to match it.",
                    recommended=True,
                    why="what you already decided wins over what the phase filled in",
                ),
                Option(label="Keep the new line", description="The artifact stands; the earlier record is updated."),
                Option(label="Mark it open", description="Add a [NEEDS CLARIFICATION] marker for the next phase."),
            ],
            impact="high",
            uncertainty="high",
        )
    if row.kind == "checklist-item":
        return Question(
            id=qid,
            header=header,
            row=row.id,
            text=f"Has this checklist item been checked by a reviewer: “{_short(row.text)}”?",
            options=[
                Option(
                    label="Not yet",
                    description="It stays unchecked until a reviewer confirms it.",
                    recommended=True,
                    why="checklists are never self-approved",
                ),
                Option(label="Yes I checked it", description="Tick the item; you are the reviewer of record."),
                Option(label="Not applicable", description="Strike it with a one-line reason."),
            ],
            impact="high",
            uncertainty="medium",
        )
    if row.kind in {"needs-clarification", "analyze-finding"} or "open clarification" in row.reason:
        return Question(
            id=qid,
            header=header,
            row=row.id,
            text=f"How should this open point be settled: “{_short(row.text)}”?",
            options=[
                Option(
                    label=f"Decide during {nxt}",
                    description=f"Leave it to {nxt}, within limits you already set.",
                    recommended=True,
                    why="keeps the phase moving without inventing an answer",
                ),
                Option(label="Leave it open", description="The marker stays and blocks readiness."),
                Option(label="Drop it from scope", description="Remove the line and note it as out of scope."),
            ],
            impact="high",
            uncertainty="high",
        )
    return Question(
        id=qid,
        header=header,
        row=row.id,
        text=f"The {phase} phase decided this on its own. Should it stay as written: “{_short(row.text)}”?",
        options=[
            Option(
                label="Keep as written",
                description="It becomes your decision of record.",
                recommended=True,
                why="nothing recorded contradicts it",
            ),
            Option(label="Mark it open", description="Add a [NEEDS CLARIFICATION] marker instead."),
            Option(label=f"Decide during {nxt}", description=f"Leave the choice to {nxt} as the agent's call."),
        ],
        impact=row.impact if row.impact in LEVEL else "medium",
        uncertainty=row.uncertainty,
    )


def assumption_check(rows: list[LedgerRow], qid: str) -> Question:
    opts = [Option(label=f"Keep {r.id}", description=_short(r.text, 200)) for r in rows[:4]]
    if len(opts) == 1:
        opts.append(Option(label="Change it", description="Ask about it as its own question."))
    return Question(
        id=qid,
        header="Defaults",
        row="defaults",
        text="Which of these defaults should stay as written?",
        options=opts,
        multi_select=True,
    )


# ---------------------------------------------------------------- build


def build(
    settings: Settings,
    phase: str,
    feature_dir: Path | None,
    findings: Path | None = None,
    base: str | None = None,
    sources: list[Path] | None = None,
) -> tuple[Ledger, Path]:
    root = settings.root
    decisions: list[Decision] = extract(phase, root, feature_dir, findings, base)
    intake = find_intake(settings, phase, feature_dir)
    facts = gather(root, phase, intake, feature_dir, sources, settings.intakes_dir)
    clf = Classifier(facts, settings=settings)
    trace = TraceLog(
        settings.traces_dir,
        f"refine-{phase}-{(feature_dir.name if feature_dir else 'project')}",
        "refine",
        enabled=bool(settings.get("reasoning.traces")),
    )
    rows: list[LedgerRow] = []
    reasoning_md: list[str] = []
    for n, d in enumerate(decisions, 1):
        v = clf.classify(d, phase)
        rows.append(
            LedgerRow(
                n=n,
                id=d.id,
                text=d.text,
                where=d.where,
                kind=d.kind,
                impact=d.impact,
                group=v.group,
                evidence=v.evidence,
                reason=v.reason,
                uncertainty=v.uncertainty,
                conflict_cite=v.conflict_with.cite if v.conflict_with else None,
                conflict_text=v.conflict_with.text if v.conflict_with else None,
                answer="—"
                if v.group in {"Backed"}
                else (
                    "pending"
                    if v.group in {"Unbacked", "Conflicting"}
                    else f"Delegated — agent's call stands: {v.reason}"
                ),
            )
        )
        if v.reasoning is not None:
            reasoning_md.append(v.reasoning.to_markdown())
    # Questions: Conflicting first, then Unbacked by impact × uncertainty; low-impact ones become a default check.
    asked = [r for r in rows if r.group in {"Conflicting", "Unbacked"}]
    asked.sort(key=lambda r: (GROUP_ORDER[r.group], -LEVEL.get(r.impact, 2) * LEVEL.get(r.uncertainty, 2), r.n))
    defaults = [
        r
        for r in asked
        if r.group == "Unbacked"
        and r.impact == "low"
        or (r.kind in {"assumption", "edge-case"} and r.uncertainty != "high" and r.group == "Unbacked")
    ]
    qn = 0
    for r in asked:
        if r in defaults:
            continue
        qn += 1
        r.question = question_for(r, phase, f"R{qn}").model_dump()
    if defaults:
        qn += 1
        q = assumption_check(defaults, f"R{qn}").model_dump()
        for r in defaults[:4]:
            r.question = q
        for r in defaults[4:]:
            qn += 1
            r.question = question_for(r, phase, f"R{qn}").model_dump()
    ledger = Ledger(
        phase=phase,
        feature_dir=settings.rel(feature_dir) if feature_dir else None,
        intake=settings.rel(intake) if intake else None,
        created=date.today().isoformat(),
        rows=rows,
    )
    path = sidecar_path(settings, phase, intake, feature_dir)
    save(ledger, path)
    if intake is not None:
        write_table(intake, ledger)
    ref = trace.write_reasoning("ledger", "\n\n".join(reasoning_md)) if settings.get("reasoning.visible") else None
    counts = {g: sum(r.group == g for r in rows) for g in GROUP_ORDER}
    trace.record(
        "ledger",
        f"Built the {phase} ledger: {counts}",
        "Every decision checked against intake answers, confirmed assumptions, the constitution and "
        "earlier clarifications.",
        evidence=[settings.rel(path)],
        reasoning_ref=ref,
        next_action="ask the Conflicting and Unbacked items",
    )
    return ledger, path


def save(ledger: Ledger, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(ledger.model_dump_json(indent=2), "utf-8")


def load(path: Path) -> Ledger:
    return Ledger.model_validate_json(path.read_text("utf-8"))


def _table(ledger: Ledger) -> list[str]:
    def qcell(r: LedgerRow) -> str:
        return r.question["id"] if r.question else "—"

    return md.render_table(
        ["#", "Decision", "Where", "Group", "Question", "Answer"],
        [
            [
                str(r.n),
                f"{r.id}: {_short(r.text, 90)}",
                r.where,
                r.group + (f" ({', '.join(r.evidence[:2])})" if r.evidence else ""),
                qcell(r),
                r.answer,
            ]
            for r in ledger.rows
        ],
    )


def write_table(intake: Path, ledger: Ledger) -> None:
    """Write or refresh this phase's ledger section; other phases' sections are untouched."""
    text = intake.read_text("utf-8")
    title = f"{ledger.phase.capitalize()} · {ledger.created}"
    body = [*_table(ledger)]
    if ledger.clarifications:
        body += ["", *ledger.clarifications]
    lines = text.splitlines()
    sec = md.find_section(lines, title, 3)
    if sec is None:
        text = md.append_to_section(text, "Phase Refinements", ["", f"### {title}", "", *body], level=2)
    else:
        end = sec.end
        while end - 1 > sec.start and not lines[end - 1].strip():
            end -= 1
        lines[sec.start + 1 : end] = ["", *body]
        text = "\n".join(lines).rstrip("\n") + "\n"
    intake.write_text(text, "utf-8")


# ---------------------------------------------------------------- rounds


def next_round(ledger: Ledger, per_round: int) -> list[dict]:
    seen, out = set(), []
    for r in ledger.pending():
        qid = r.question["id"]
        if qid in seen:
            continue
        seen.add(qid)
        out.append(r.question)
        if len(out) >= per_round:
            break
    return out


def to_cards(questions: list[dict]) -> dict:
    from ..intake.cards import to_card

    cards = [to_card(Question.model_validate(q)) for q in questions]
    return {"questions": cards, "lint": {c["question"]: p for c in cards if (p := lint_card(c))}}


def _mark_open(root: Path, where: str, text: str) -> str | None:
    m = re.match(r"^(.+?):(\d+)$", where)
    if not m:
        return None
    path = root / m.group(1)
    if not path.is_file():
        return None
    lines = path.read_text("utf-8").splitlines()
    i = int(m.group(2)) - 1
    if 0 <= i < len(lines) and "[NEEDS CLARIFICATION" not in lines[i]:
        lines[i] = lines[i].rstrip() + f" [NEEDS CLARIFICATION: confirm “{_short(text, 60)}”]"
        path.write_text("\n".join(lines) + "\n", "utf-8")
        return str(path)
    return None


def _tick_checklist(root: Path, where: str) -> str | None:
    m = re.match(r"^(.+?):(\d+)$", where)
    if not m:
        return None
    path = root / m.group(1)
    lines = path.read_text("utf-8").splitlines()
    i = int(m.group(2)) - 1
    if 0 <= i < len(lines) and "- [ ]" in lines[i]:
        lines[i] = lines[i].replace("- [ ]", "- [x]", 1)
        path.write_text("\n".join(lines) + "\n", "utf-8")
        return str(path)
    return None


def _spec_clarification(feature_dir: Path, line: str) -> None:
    spec = feature_dir / "spec.md"
    if not spec.is_file():
        return
    text = spec.read_text("utf-8")
    session = f"Session {date.today().isoformat()}"
    if md.find_section(text.splitlines(), "Clarifications", 2) is None:
        text = md.append_to_section(text, "Clarifications", [f"### {session}", "", line], level=2)
    elif md.find_section(text.splitlines(), session, 3) is None:
        text = md.append_to_section(text, "Clarifications", ["", f"### {session}", "", line], level=2)
    else:
        text = md.append_to_section(text, session, [line], level=3)
    spec.write_text(text, "utf-8")


def apply(settings: Settings, path: Path, answers: dict, notes: dict | None = None) -> dict:
    """Record one round. Returns what changed and the artifact edits the host still has to make."""
    ledger = load(path)
    root = settings.root
    round_no = ledger.rounds + 1
    asked = next_round(ledger, settings.per_round)
    edits: list[dict] = []
    changed: set[str] = set()
    for qd in asked:
        q = Question.model_validate(qd)
        raw = answers.get(q.text, answers.get(q.id))
        reading = read_answer(q, raw, (notes or {}).get(q.text))
        targets = [r for r in ledger.rows if r.question and r.question["id"] == q.id]
        if reading.state == "stop":
            ledger.finished = True
            break
        labels = [q.options["ABCD".index(x)].label for x in reading.letters] if reading.letters else []
        for r in targets:
            r.round = round_no
            if q.header == "Defaults":
                kept = f"Keep {r.id}" in labels
                r.answer = f"{'Kept' if kept else 'Not kept'} — round {round_no}"
                r.group = "Backed" if kept else "Unbacked"
                if not kept:
                    edits.append({"where": r.where, "action": "revise or ask", "decision": r.text})
                continue
            if reading.state == "unknown":
                r.answer = f"Open — not sure — round {round_no}"
                if f := _mark_open(root, r.where, r.text):
                    changed.add(settings.rel(f))
                continue
            if reading.state == "other":
                r.answer = f'Other — "{reading.words}" — round {round_no}'
                edits.append({"where": r.where, "action": "apply the person's words", "words": reading.words})
                continue
            choice = labels[0] if labels else ""
            if reading.state == "delegated" or choice.startswith("Decide during"):
                r.answer = f"Delegated — agent chose Keep as written: {r.reason or 'phase default'} — round {round_no}"
                r.group = "Delegated"
            elif choice in {"Keep as written", "Keep the new line"}:
                r.answer, r.group = f"{choice} — round {round_no}", "Backed"
                if choice == "Keep the new line":
                    edits.append({"where": r.conflict_cite, "action": "update the earlier record", "to": r.text})
            elif choice in {"Mark it open", "Leave it open", "Not yet"}:
                r.answer = f"{choice} — round {round_no}"
                if choice != "Not yet" and (f := _mark_open(root, r.where, r.text)):
                    changed.add(settings.rel(f))
            elif choice == "Yes I checked it":
                r.answer, r.group = f"Checked by the person — round {round_no}", "Backed"
                if f := _tick_checklist(root, r.where):
                    changed.add(settings.rel(f))
            elif choice == "Follow the earlier decision":
                r.answer = f"{choice} — round {round_no}"
                edits.append(
                    {
                        "where": r.where,
                        "action": "rewrite to match",
                        "source": r.conflict_cite,
                        "source_text": r.conflict_text,
                    }
                )
            elif choice in {"Drop it from scope", "Not applicable"}:
                r.answer = f"{choice} — round {round_no}"
                edits.append({"where": r.where, "action": "remove and note as out of scope"})
            else:
                r.answer = f"{choice or reading.words} — round {round_no}"
        answer_text = ", ".join(labels) if labels else (reading.words or reading.state)
        line = f"- Q: {q.text} → A: {answer_text}"
        ledger.clarifications.append(line)
        if ledger.phase == "specify" and ledger.feature_dir:
            _spec_clarification(root / ledger.feature_dir, line)
            changed.add(f"{ledger.feature_dir}/spec.md")
    ledger.rounds = round_no
    if not ledger.pending():
        ledger.finished = True
    save(ledger, path)
    if ledger.intake:
        write_table(root / ledger.intake, ledger)
        changed.add(ledger.intake)
        _log_intake(root / ledger.intake, ledger, round_no, len(asked))
    return {
        "round": round_no,
        "artifact_edits": edits,
        "changed": sorted(changed),
        "finished": ledger.finished,
        **summary(ledger),
    }


def _log_intake(intake: Path, ledger: Ledger, round_no: int, asked: int) -> None:
    from ..intake.document import append_log

    s = summary(ledger)
    intake.write_text(
        append_log(
            intake.read_text("utf-8"),
            {
                "Round": f"{ledger.phase} refine {round_no}",
                "Questions": str(asked),
                "Answered": str(asked),
                "Rows sufficient": "—",
                "Notes": f"Backed {s['backed']}, Delegated {s['delegated']}, still open {s['open']}",
            },
        ),
        "utf-8",
    )


def summary(ledger: Ledger) -> dict:
    return {
        "backed": sum(r.group == "Backed" for r in ledger.rows),
        "delegated": sum(r.group == "Delegated" for r in ledger.rows),
        "open": sum(r.group in {"Unbacked", "Conflicting"} and r.answer in {"—", "pending"} for r in ledger.rows),
        "conflicting": sum(r.group == "Conflicting" for r in ledger.rows),
        "decisions": len(ledger.rows),
    }


def as_dict(ledger: Ledger) -> dict:
    return {**json.loads(ledger.model_dump_json()), "summary": summary(ledger)}


__all__ = [
    "Ledger",
    "LedgerRow",
    "apply",
    "as_dict",
    "build",
    "feature_dir_from_scripts",
    "find_intake",
    "load",
    "next_round",
    "save",
    "summary",
    "to_cards",
]
