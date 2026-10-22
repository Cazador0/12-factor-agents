"""Multiple-choice cards: build AskUserQuestion payloads, lint them, and read answers back."""

from __future__ import annotations

import re
from dataclasses import dataclass

from .model import Option, Question

REC = " (Recommended)"
DELEGATE = re.compile(r"\b(you decide|your call|up to you|decide during|you choose|dealer's choice)\b", re.I)
UNKNOWN = re.compile(r"^\s*(not sure|don't know|dont know|no idea|skip|unsure|\?)\s*\.?\s*$", re.I)
STOP = re.compile(r"\b(that's enough|thats enough|wrap up|stop here|wrap up now)\b", re.I)


def to_card(q: Question) -> dict:
    """One ``AskUserQuestion`` entry. The recommended option leads and carries the tool's suffix."""
    ordered = sorted(q.options, key=lambda o: not o.recommended) if not q.multi_select else q.options
    options = []
    for opt in ordered:
        label = opt.label + (REC if opt.recommended and not q.multi_select else "")
        options.append({"label": label, "description": opt.description})
    return {"question": q.text, "header": q.header, "multiSelect": q.multi_select, "options": options}


def lint_card(card: dict) -> list[str]:
    """The card rules from the intake start command, step 3f."""
    problems: list[str] = []
    text = str(card.get("question", ""))
    if not text.strip().endswith("?"):
        problems.append("question must be a complete sentence ending with '?'")
    if len(text.split()) < 4:
        problems.append("question reads like a bare label; write a full question")
    if "pick all that apply" in text.lower():
        problems.append("drop '(pick all that apply)'; the card shows multi-select itself")
    header = str(card.get("header", ""))
    if not header or len(header) > 12:
        problems.append(f"header must be 1–12 characters (got {len(header)})")
    opts = card.get("options") or []
    if not 2 <= len(opts) <= 4:
        problems.append(f"needs 2–4 options (got {len(opts)})")
    seen = set()
    for i, opt in enumerate(opts):
        label = str(opt.get("label", "")).removesuffix(REC)
        words = len(label.split())
        if not 1 <= words <= 5:
            problems.append(f"option {i + 1} label must be 1–5 words (got {words})")
        if "," in label:
            problems.append(f"option {i + 1} label must not contain commas")
        if label.strip().lower() in {"other", "other…", "something else"}:
            problems.append("no hand-made 'Other'; the tool adds a free-text choice")
        if not str(opt.get("description", "")).strip():
            problems.append(f"option {i + 1} needs a one-line implication")
        key = label.strip().lower()
        if key in seen:
            problems.append(f"option {i + 1} duplicates another option")
        seen.add(key)
    if not card.get("multiSelect"):
        recs = [i for i, o in enumerate(opts) if str(o.get("label", "")).endswith(REC)]
        if recs and recs != [0]:
            problems.append("the recommended option must come first")
    return problems


def lint_question(q: Question) -> list[str]:
    problems = lint_card(to_card(q))
    if not q.multi_select and not any(o.recommended for o in q.options):
        problems.append("single-choice questions need a recommended option")
    return problems


@dataclass
class Reading:
    state: str  # answered | other | delegated | unknown | stop
    letters: list[str]
    words: str | None = None
    note: str | None = None


def _norm(label: str) -> str:
    return re.sub(r"\s+", " ", label.removesuffix(REC).strip().lower())


def read_answer(q: Question, raw: str | list[str] | None, note: str | None = None) -> Reading:
    """Map what the tool returned onto the question's options."""
    if raw is None or (isinstance(raw, str) and not raw.strip()):
        return Reading("unknown", [], note=note)
    parts = raw if isinstance(raw, list) else ([p for p in raw.split(",")] if q.multi_select else [raw])
    by_label = {_norm(o.label): "ABCD"[i] for i, o in enumerate(q.options)}
    letters, leftovers = [], []
    for part in parts:
        key = _norm(str(part))
        if key in by_label:
            letters.append(by_label[key])
        elif re.fullmatch(r"[a-d]", key):
            letters.append(key.upper())
        elif key:
            leftovers.append(str(part).strip())
    if letters and not leftovers:
        if any(_is_delegate_option(q.options["ABCD".index(x)]) for x in letters):
            return Reading("delegated", letters, note=note)
        return Reading("answered", sorted(set(letters)), note=note)
    words = ", ".join(leftovers) if leftovers else str(raw)
    if STOP.search(words):
        return Reading("stop", [], words, note)
    if DELEGATE.search(words):
        return Reading("delegated", [], words, note)
    if UNKNOWN.match(words):
        return Reading("unknown", [], words, note)
    return Reading("other", letters, words, note)


def _is_delegate_option(opt: Option) -> bool:
    return bool(DELEGATE.search(opt.label))
