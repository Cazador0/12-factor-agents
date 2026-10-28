"""Render, parse and edit intake files in the extension template's shape.

``render`` is used once, to write the Draft. After that every change is a small in-place edit
(tick a box, fill an Answer line, change a table cell, append a log row) so nothing an earlier
round recorded can be dropped by a rewrite.
"""

from __future__ import annotations

import re
from datetime import date

from .. import markdown as md
from .model import Intake, Option, Question, Row
from .rows import BY_ID

_FIELD = re.compile(r"^\*\*(Status|Scope|Feature|Slug|Created|Idea type)\*\*:\s*(.*)$")
_QHEAD = re.compile(
    r"^Q(\d+)\s*·\s*(.*?)\s*·\s*([CST]\d+(?:\s*,\s*[CST]\d+)*|defaults)\s*·\s*impact\s+(\w+)\s*×\s*uncertainty\s+(\w+)\s*$"
)
_OPT = re.compile(r"^- \[( |x|X)\] \*\*([A-D])\. (.+?)\*\* — (.*?)(?:\s+\*\(Recommended: (.*)\)\*)?\s*$")
_OTHER = re.compile(r"^- \[( |x|X)\] \*\*Other\*\*:\s*(.*)$")
_ANSWER = re.compile(r"^\*\*Answer\*\*:\s*(.*)$")
LETTERS = "ABCD"
GROUP_TITLES = {
    "C": "Constitution rows: constitution-ready",
    "S": "Spec rows: spec-ready",
    "T": "Plan rows: plan-ready",
}
LOG_HEADER = ["Round", "Questions", "Answered", "Rows sufficient", "Notes"]


# ---------------------------------------------------------------- render


def render_question(q: Question) -> list[str]:
    out = [f"### {q.id} · {q.header} · {q.row} · impact {q.impact} × uncertainty {q.uncertainty}", "", q.text]
    if q.multi_select:
        out.append("*Multi-select.*")
    if q.generic:
        out.append("*Generic scaffold — sharpen to the idea before asking.*")
    out.append("")
    for i, opt in enumerate(q.options):
        letter = LETTERS[i]
        tick = "x" if letter in q.chosen else " "
        rec = f" *(Recommended: {opt.why or 'fits the idea best'})*" if opt.recommended else ""
        out.append(f"- [{tick}] **{letter}. {opt.label}** — {opt.description}{rec}")
    other_tick = "x" if q.state == "other" else " "
    other_text = _other_words(q.answer) if q.state == "other" else "____"
    out += [f"- [{other_tick}] **Other**: {other_text}", "", f"**Answer**: {q.answer}"]
    if q.note:
        out.append(f"**Note**: {q.note}")
    return out


def _other_words(answer: str) -> str:
    m = re.search(r'"(.*)"', answer)
    return m.group(1) if m else answer


def render(intake: Intake) -> str:
    today = intake.session_date or intake.created
    lines = [
        f"# Intake: {intake.title}",
        "",
        f"**Status**: {intake.status}",
        f"**Scope**: {intake.scope}",
        f"**Feature**: {intake.feature}",
        f"**Slug**: {intake.slug}",
        f"**Created**: {intake.created}",
        f"**Idea type**: {intake.idea_type}",
        "",
        "## Idea",
        "",
        *[f"> {ln}" if ln else ">" for ln in intake.idea.splitlines()],
        "",
        f"**Sources read**: {intake.sources}",
        "",
        "## Working interpretation",
        "",
        intake.interpretation or "[1–2 neutral sentences: what is proposed, for whom, to what end.]",
        "",
        "## Sufficiency check",
        "",
        "<!-- Status is one of: Missing | Partial | Sufficient | Delegated | N/A | Open -->",
    ]
    for prefix, title in GROUP_TITLES.items():
        rows = [r for r in intake.rows if r.id.startswith(prefix)]
        if not rows:
            continue
        lines += ["", f"### {title}", ""]
        lines += md.render_table(
            ["#", "Row", "Status", "Evidence", "Still needed"],
            [[r.id, r.name, r.status, r.evidence, r.still_needed] for r in rows],
        )
    lines += ["", "## Assumptions", ""]
    lines += [f"- {a}" for a in intake.assumptions] or ["- None yet."]
    lines += ["", "## Question bank", ""]
    for q in intake.questions:
        lines += render_question(q) + [""]
    lines += ["## Clarifications", "", f"### Session {today}"]
    lines += ["", *intake.clarifications] if intake.clarifications else []
    lines += ["", "## Session Log", ""]
    lines += md.render_table(LOG_HEADER, [[r.get(h, "") for h in LOG_HEADER] for r in intake.session_log])
    lines += ["", "## Open Items", ""]
    lines += [f"- {o}" for o in intake.open_items] or ["- None."]
    lines += ["", "## Phase Refinements", ""]
    return "\n".join(lines).rstrip("\n") + "\n"


# ---------------------------------------------------------------- parse


def parse(text: str) -> Intake:
    lines = text.splitlines()
    title = next((ln[len("# Intake: ") :].strip() for ln in lines if ln.startswith("# Intake: ")), "Untitled")
    fields: dict[str, str] = {}
    for ln in lines:
        m = _FIELD.match(ln)
        if m and m.group(1) not in fields:
            fields[m.group(1)] = m.group(2).strip()
    idea_block = md.section_text(text, "Idea", 2)
    idea_lines = [ln[1:].lstrip() if ln.startswith(">") else None for ln in idea_block.splitlines()]
    idea = "\n".join(x for x in idea_lines if x is not None).strip()
    src = re.search(r"^\*\*Sources read\*\*:\s*(.*)$", idea_block, flags=re.M)
    interp = md.section_text(text, "Working interpretation", 2).strip()

    rows: list[Row] = []
    for title_ in GROUP_TITLES.values():
        for r in md.parse_table(md.section_text(text, title_, 3)):
            if r.get("#"):
                rows.append(
                    Row(
                        id=r["#"],
                        name=r.get("Row", BY_ID.get(r["#"]).name if r["#"] in BY_ID else r["#"]),
                        status=r.get("Status", "Missing") if r.get("Status") in _STATUSES else "Missing",
                        evidence=r.get("Evidence", "—"),
                        still_needed=r.get("Still needed", "—"),
                    )
                )

    assumptions = [
        ln[2:].strip()
        for ln in md.section_text(text, "Assumptions", 2).splitlines()
        if ln.startswith("- ") and ln.strip() != "- None yet."
    ]
    questions = _parse_questions(lines)
    clar_block = md.section_text(text, "Clarifications", 2)
    clarifications = [ln.strip() for ln in clar_block.splitlines() if ln.strip().startswith("- Q:")]
    sess = re.search(r"^### Session (\S+)", clar_block, flags=re.M)
    log = md.parse_table(md.section_text(text, "Session Log", 2))
    open_items = [
        ln[2:].strip()
        for ln in md.section_text(text, "Open Items", 2).splitlines()
        if ln.startswith("- ") and ln.strip() != "- None."
    ]
    return Intake(
        title=title,
        status=fields.get("Status", "Draft"),
        scope="project" if fields.get("Scope", "").startswith("project") else "feature",
        feature=fields.get("Feature", "pending"),
        slug=fields.get("Slug", ""),
        created=fields.get("Created", date.today().isoformat()),
        idea_type=fields.get("Idea type", "other"),
        idea=idea,
        sources=src.group(1).strip() if src else "none",
        interpretation=interp,
        rows=rows,
        assumptions=assumptions,
        questions=questions,
        clarifications=clarifications,
        session_date=sess.group(1) if sess else None,
        session_log=log,
        open_items=open_items,
    )


_STATUSES = {"Missing", "Partial", "Sufficient", "Delegated", "N/A", "Open"}


def _parse_questions(lines: list[str]) -> list[Question]:
    bank = md.find_section(lines, "Question bank", 2)
    if not bank:
        return []
    out: list[Question] = []
    for sec in md.sections(lines):
        if sec.level != 3 or not (bank.start < sec.start < bank.end):
            continue
        m = _QHEAD.match(sec.title)
        if not m:
            continue
        body = lines[sec.start + 1 : sec.end]
        text_lines, options, chosen, answer, note = [], [], [], "pending", None
        multi = generic = False
        other_ticked = False
        for ln in body:
            s = ln.strip()
            if om := _OPT.match(s):
                options.append(
                    Option(label=om.group(3), description=om.group(4), recommended=bool(om.group(5)), why=om.group(5))
                )
                if om.group(1).lower() == "x":
                    chosen.append(om.group(2))
            elif oth := _OTHER.match(s):
                other_ticked = oth.group(1).lower() == "x"
            elif am := _ANSWER.match(s):
                answer = am.group(1).strip()
            elif s.startswith("**Note**:"):
                note = s[len("**Note**:") :].strip()
            elif s == "*Multi-select.*":
                multi = True
            elif s.startswith("*Generic scaffold"):
                generic = True
            elif s and not options and not s.startswith("<!--"):
                text_lines.append(s)
        state = _state_from_answer(answer, other_ticked)
        rnd = re.search(r"round (\d+)", answer)
        tries = 1 if state == "unknown" else (2 if state == "open" and "not sure" in answer else 0)
        out.append(
            Question(
                id=f"Q{m.group(1)}",
                header=m.group(2),
                row=m.group(3),
                impact=m.group(4) if m.group(4) in {"high", "medium", "low"} else "medium",
                uncertainty=m.group(5) if m.group(5) in {"high", "medium", "low"} else "medium",
                text=" ".join(text_lines),
                options=options,
                multi_select=multi,
                generic=generic,
                state=state,
                chosen=chosen,
                answer=answer,
                note=note,
                round=int(rnd.group(1)) if rnd else None,
                tries=tries,
            )
        )
    return out


def _state_from_answer(answer: str, other_ticked: bool) -> str:
    a = answer.strip()
    if a == "pending" or not a:
        return "pending"
    if a.startswith("Not asked"):
        return "not-asked"
    if a.startswith("Delegated"):
        return "delegated"
    if a.startswith("Open"):
        return "open"
    if a.startswith("Unknown"):
        return "unknown"
    if a.startswith("Other") or other_ticked:
        return "other"
    return "answered"


# ---------------------------------------------------------------- in-place edits


def set_field(text: str, name: str, value: str) -> str:
    return md.replace_line(text, rf"^\*\*{re.escape(name)}\*\*:", f"**{name}**: {value}")


def replace_question(text: str, q: Question) -> str:
    """Swap one question's block for its re-rendered form; every other block stays byte-identical."""
    lines = text.splitlines()
    sec = md.find_section(lines, q.id, 3)
    if not sec:
        bank = md.find_section(lines, "Question bank", 2)
        insert = bank.end if bank else len(lines)
        while insert - 1 > (bank.start if bank else 0) and not lines[insert - 1].strip():
            insert -= 1
        lines[insert:insert] = ["", *render_question(q)]
        return "\n".join(lines).rstrip("\n") + "\n"
    end = sec.end
    while end - 1 > sec.start and not lines[end - 1].strip():
        end -= 1
    lines[sec.start : end] = render_question(q)
    return "\n".join(lines).rstrip("\n") + "\n"


def update_row(text: str, row: Row) -> str:
    return md.update_table_row(
        text, "#", row.id, {"Status": row.status, "Evidence": row.evidence, "Still needed": row.still_needed}
    )


def append_clarification(text: str, line: str, session: str) -> str:
    lines = text.splitlines()
    sec = md.find_section(lines, f"Session {session}", 3)
    if sec is None:
        return md.append_to_section(text, "Clarifications", ["", f"### Session {session}", "", line], level=2)
    return md.append_to_section(text, f"Session {session}", [line], level=3)


def append_log(text: str, row: dict[str, str]) -> str:
    lines = text.splitlines()
    sec = md.find_section(lines, "Session Log", 2)
    cells = "| " + " | ".join(str(row.get(h, "")).replace("|", "\\|") for h in LOG_HEADER) + " |"
    if not sec:
        return md.append_to_section(text, "Session Log", md.render_table(LOG_HEADER, []) + [cells], level=2)
    last_table = max((i for i in range(sec.start, sec.end) if lines[i].strip().startswith("|")), default=None)
    if last_table is None:
        return md.append_to_section(text, "Session Log", md.render_table(LOG_HEADER, []) + [cells], level=2)
    lines.insert(last_table + 1, cells)
    return "\n".join(lines).rstrip("\n") + "\n"


def append_bullet(text: str, section: str, bullet: str, placeholder: str) -> str:
    lines = text.splitlines()
    sec = md.find_section(lines, section, 2)
    if sec:
        for i in range(sec.start, sec.end):
            if lines[i].strip() == placeholder:
                lines[i] = f"- {bullet}"
                return "\n".join(lines).rstrip("\n") + "\n"
    return md.append_to_section(text, section, [f"- {bullet}"], level=2)


def replace_bullet(text: str, section: str, old: str, new: str) -> str:
    lines = text.splitlines()
    sec = md.find_section(lines, section, 2)
    if sec:
        for i in range(sec.start, sec.end):
            if lines[i].strip() == f"- {old}":
                lines[i] = f"- {new}"
                break
    return "\n".join(lines).rstrip("\n") + "\n"


def set_interpretation(text: str, interpretation: str) -> str:
    lines = text.splitlines()
    sec = md.find_section(lines, "Working interpretation", 2)
    if not sec:
        return text
    lines[sec.start + 1 : sec.end] = ["", interpretation, ""]
    return "\n".join(lines).rstrip("\n") + "\n"
