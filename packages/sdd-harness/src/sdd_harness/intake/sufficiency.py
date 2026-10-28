"""Rate sufficiency rows from the answers so far.

A row is Sufficient only when its bar is met and nothing it depends on is still open: an unanswered
question feeding it keeps it Partial. Evidence that does not come from a question (a constitution
article, a prior decision, the source document) is preserved, because the host model put it there.
"""

from __future__ import annotations

import re

from .model import SETTLED, Intake, Question, Row
from .rows import BY_ID

_QREF = re.compile(r"\bQ\d+\b")


def _external_evidence(evidence: str) -> str:
    """Evidence text minus question references (which are recomputed every round)."""
    if evidence in {"—", "", "-"}:
        return ""
    parts = [p.strip() for p in evidence.split(";")]
    return "; ".join(p for p in parts if p and not _QREF.fullmatch(p) and not re.fullmatch(r"(Q\d+,?\s*)+", p))


def rate_row(row: Row, questions: list[Question]) -> Row:
    if row.status == "N/A":
        return row
    rowdef = BY_ID.get(row.id)
    required = rowdef.required_answers if rowdef else 1
    mine = [q for q in questions if row.id in q.rows]
    settled = [q for q in mine if q.state in {"answered", "other", "delegated"}]
    open_ = [q for q in mine if q.state in {"pending", "unknown"}]
    gave_up = [q for q in mine if q.state == "open"]
    external = _external_evidence(row.evidence)
    qrefs = ", ".join(q.id for q in settled)
    evidence = "; ".join(x for x in (external, qrefs) if x) or "—"

    if gave_up and not open_ and len(settled) < required:
        return row.model_copy(
            update={"status": "Open", "evidence": evidence, "still_needed": "person could not answer; see Open Items"}
        )
    if not settled:
        if external and row.status == "Sufficient" and not open_:
            return row.model_copy(update={"evidence": evidence})
        status = "Partial" if (external or row.status == "Partial") else "Missing"
        still = row.still_needed if row.still_needed not in {"—", ""} else (rowdef.bar if rowdef else "an answer")
        return row.model_copy(update={"status": status, "evidence": evidence, "still_needed": still})
    if open_:
        pending = ", ".join(q.id for q in open_)
        return row.model_copy(
            update={"status": "Partial", "evidence": evidence, "still_needed": f"answers to {pending}"}
        )
    if len(settled) + (1 if external else 0) >= required:
        status = "Delegated" if all(q.state == "delegated" for q in settled) else "Sufficient"
        return row.model_copy(update={"status": status, "evidence": evidence, "still_needed": "—"})
    missing = required - len(settled) - (1 if external else 0)
    return row.model_copy(
        update={
            "status": "Partial",
            "evidence": evidence,
            "still_needed": f"{missing} more answer(s): {rowdef.bar if rowdef else 'see bar'}",
        }
    )


def rate(intake: Intake) -> list[Row]:
    return [rate_row(r, intake.questions) for r in intake.rows]


def all_settled(intake: Intake) -> bool:
    return all(r.status in SETTLED for r in intake.rows)


def progress_line(intake: Intake, round_no: int, focus: list[str]) -> str:
    spec_ok, spec_n = intake.counts("S")
    parts = [f"Round {round_no}: {spec_ok} of {spec_n} spec rows sufficient"]
    if any(r.id.startswith("C") for r in intake.rows):
        c_ok, c_n = intake.counts("C")
        parts.append(f"{c_ok} of {c_n} constitution rows")
    if any(r.id.startswith("T") for r in intake.rows):
        t_ok, t_n = intake.counts("T")
        parts.append(f"{t_ok} of {t_n} plan rows")
    line = ", ".join(parts)
    if focus:
        line += "; now " + " and ".join(focus[:3])
    return line + "."
