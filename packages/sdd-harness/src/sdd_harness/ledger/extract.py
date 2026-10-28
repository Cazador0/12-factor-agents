"""Pull the decisions a Spec Kit phase made out of its artifacts.

Each phase leaves a different trail: requirements and assumptions in ``spec.md``, Technical Context
fields and research decisions in the plan, unchecked items in checklists, task lines in ``tasks.md``.
Every decision keeps the file and line it came from.
"""

from __future__ import annotations

import json
import re
import subprocess
from dataclasses import dataclass, field
from pathlib import Path

from ..markdown import sections

PHASES = ("constitution", "specify", "plan", "checklist", "tasks", "analyze", "implement", "converge")
NEEDS = re.compile(r"\[NEEDS CLARIFICATION:?([^\]]*)\]")
_REQ = re.compile(r"^\s*-\s*\*\*((?:FR|SC|NFR)-\d+)\*\*:?\s*(.+)$")
_FIELD = re.compile(r"^\s*\*\*([A-Z][A-Za-z/ ]+?)\*\*:\s*(.+)$")
_TASK = re.compile(r"^\s*-\s*\[( |x|X)\]\s*(T\d{3,})\s*(.*)$")
_CHK = re.compile(r"^\s*-\s*\[ \]\s*(CHK\d+)?\s*(.+)$")
_DECISION = re.compile(r"^\s*[-*]?\s*\*\*Decision\*\*:?\s*(.+)$", re.I)
_SEVERITY = re.compile(r"\b(CRITICAL|HIGH)\b")
PLAN_FIELDS = {
    "Language/Version",
    "Primary Dependencies",
    "Storage",
    "Testing",
    "Target Platform",
    "Project Type",
    "Performance Goals",
    "Constraints",
    "Scale/Scope",
}


@dataclass
class Decision:
    id: str
    text: str
    where: str
    kind: str
    impact: str = "medium"
    needs_clarification: bool = False
    meta: dict = field(default_factory=dict)


def _rel(path: Path, root: Path) -> str:
    try:
        return str(path.relative_to(root))
    except ValueError:
        return str(path)


def _bullets_under(lines: list[str], title: str) -> list[tuple[int, str]]:
    out = []
    for sec in sections(lines):
        if sec.title.lower().startswith(title.lower()):
            for i in range(sec.start + 1, sec.end):
                s = lines[i].strip()
                if s.startswith(("- ", "* ")) and not s.startswith(("- [", "* [")):
                    out.append((i + 1, s[2:].strip()))
    return out


def from_spec(path: Path, root: Path) -> list[Decision]:
    lines = path.read_text("utf-8").splitlines()
    rel = _rel(path, root)
    out: list[Decision] = []
    for i, ln in enumerate(lines, 1):
        if m := _REQ.match(ln):
            kind = "success-criterion" if m.group(1).startswith("SC") else "requirement"
            out.append(Decision(m.group(1), m.group(2).strip(), f"{rel}:{i}", kind, "high", bool(NEEDS.search(ln))))
    for title, kind, impact in (("Assumptions", "assumption", "medium"), ("Edge Cases", "edge-case", "medium")):
        for n, (i, text) in enumerate(_bullets_under(lines, title), 1):
            out.append(
                Decision(f"{kind[:2].upper()}-{n:02d}", text, f"{rel}:{i}", kind, impact, bool(NEEDS.search(text)))
            )
    for sec in sections(lines):
        if m := re.match(r"User Story (\d+)\s*-\s*(.*?)\s*\(Priority:\s*(P\d)\)", sec.title):
            out.append(
                Decision(
                    f"US{m.group(1)}",
                    f"{m.group(2)} ships at priority {m.group(3)}",
                    f"{rel}:{sec.start + 1}",
                    "story-priority",
                    "high",
                )
            )
    seen = {d.where for d in out}
    for i, ln in enumerate(lines, 1):
        if NEEDS.search(ln) and f"{rel}:{i}" not in seen:
            out.append(Decision(f"NC-{i}", ln.strip(), f"{rel}:{i}", "needs-clarification", "high", True))
    return out


def from_constitution(path: Path, root: Path) -> list[Decision]:
    lines = path.read_text("utf-8").splitlines()
    rel = _rel(path, root)
    out: list[Decision] = []
    for sec in sections(lines):
        if sec.level == 3 and re.match(r"^[IVXLC]+\.", sec.title):
            body = " ".join(ln.strip() for ln in lines[sec.start + 1 : sec.end] if ln.strip())[:400]
            out.append(
                Decision(
                    sec.title.split(".", 1)[0],
                    f"{sec.title}: {body}",
                    f"{rel}:{sec.start + 1}",
                    "principle",
                    "high",
                    bool(NEEDS.search(body)),
                )
            )
    for title in ("Additional Constraints", "Development Workflow", "Governance"):
        for n, (i, text) in enumerate(_bullets_under(lines, title), 1):
            out.append(Decision(f"{title[:3].upper()}-{n:02d}", text, f"{rel}:{i}", "constitution-rule", "high"))
    return out


def from_plan(feature_dir: Path, root: Path) -> list[Decision]:
    out: list[Decision] = []
    plan = feature_dir / "plan.md"
    if plan.is_file():
        lines = plan.read_text("utf-8").splitlines()
        for i, ln in enumerate(lines, 1):
            if (m := _FIELD.match(ln)) and m.group(1).strip() in PLAN_FIELDS:
                out.append(
                    Decision(
                        m.group(1).strip(),
                        f"{m.group(1).strip()}: {m.group(2).strip()}",
                        f"{_rel(plan, root)}:{i}",
                        "technical-context",
                        "high",
                        bool(NEEDS.search(ln)),
                    )
                )
    research = feature_dir / "research.md"
    if research.is_file():
        for i, ln in enumerate(research.read_text("utf-8").splitlines(), 1):
            if m := _DECISION.match(ln):
                out.append(
                    Decision(
                        f"R-{i}",
                        m.group(1).strip(),
                        f"{_rel(research, root)}:{i}",
                        "research-decision",
                        "high",
                        bool(NEEDS.search(ln)),
                    )
                )
    model = feature_dir / "data-model.md"
    if model.is_file():
        lines = model.read_text("utf-8").splitlines()
        for sec in sections(lines):
            if sec.level in (2, 3) and sec.title.lower() not in {"entities", "data model", "overview"}:
                out.append(
                    Decision(
                        f"E-{sec.start + 1}",
                        f"Entity {sec.title}",
                        f"{_rel(model, root)}:{sec.start + 1}",
                        "entity",
                        "medium",
                    )
                )
    contracts = feature_dir / "contracts"
    if contracts.is_dir():
        for p in sorted(contracts.iterdir()):
            if p.is_file():
                out.append(Decision(f"K-{p.stem}", f"Contract {p.name}", _rel(p, root), "contract", "medium"))
    return out


def from_checklists(feature_dir: Path, root: Path) -> list[Decision]:
    out: list[Decision] = []
    for path in sorted((feature_dir / "checklists").glob("*.md")):
        for i, ln in enumerate(path.read_text("utf-8").splitlines(), 1):
            if m := _CHK.match(ln):
                out.append(
                    Decision(
                        m.group(1) or f"CHK-{path.stem}-{i}",
                        m.group(2).strip(),
                        f"{_rel(path, root)}:{i}",
                        "checklist-item",
                        "high",
                    )
                )
    return out


def from_tasks(feature_dir: Path, root: Path, converge_only: bool = False) -> list[Decision]:
    path = feature_dir / "tasks.md"
    if not path.is_file():
        return []
    lines = path.read_text("utf-8").splitlines()
    start = 0
    if converge_only:
        start = next((i for i, ln in enumerate(lines) if re.match(r"^#+ .*converge", ln, re.I)), len(lines))
    out: list[Decision] = []
    for i, ln in enumerate(lines[start:], start + 1):
        if m := _TASK.match(ln):
            body = m.group(3)
            traced = bool(re.search(r"\[(US\d+|FR-\d+|SC-\d+)\]|\b(US\d+|FR-\d+)\b", body))
            out.append(
                Decision(
                    m.group(2),
                    body.strip(),
                    f"{_rel(path, root)}:{i}",
                    "task",
                    "medium" if traced else "high",
                    bool(NEEDS.search(body)),
                    {"traced": traced, "parallel": "[P]" in body},
                )
            )
    return out


def from_analyze(findings: Path | None) -> list[Decision]:
    """``/speckit-analyze`` writes no file: pass its report (Markdown or JSON) with ``--findings``."""
    if findings is None or not findings.is_file():
        return []
    text = findings.read_text("utf-8")
    out: list[Decision] = []
    try:
        data = json.loads(text)
        for n, f in enumerate(data if isinstance(data, list) else data.get("findings", []), 1):
            if str(f.get("severity", "")).upper() in {"CRITICAL", "HIGH"}:
                out.append(
                    Decision(
                        f.get("id", f"A{n}"),
                        f.get("summary") or f.get("text", ""),
                        f.get("location", "analyze"),
                        "analyze-finding",
                        "high",
                    )
                )
        return out
    except json.JSONDecodeError:
        pass
    for i, ln in enumerate(text.splitlines(), 1):
        if _SEVERITY.search(ln) and "|" in ln:
            cells = [c.strip() for c in ln.strip().strip("|").split("|")]
            out.append(
                Decision(cells[0] or f"A{i}", " · ".join(cells[1:5]), f"analyze report:{i}", "analyze-finding", "high")
            )
    return out


def from_implement(feature_dir: Path, root: Path, base: str | None) -> list[Decision]:
    """Files changed since ``base`` that no task names: calls implementation made on its own."""
    ref = base or "HEAD"
    out_ = subprocess.run(
        ["git", "-C", str(root), "diff", "--name-only", ref], capture_output=True, text=True, check=False
    )
    changed = [ln for ln in out_.stdout.splitlines() if ln]
    tasks = (feature_dir / "tasks.md").read_text("utf-8") if (feature_dir / "tasks.md").is_file() else ""
    out: list[Decision] = []
    for n, f in enumerate(changed, 1):
        if f.startswith(("specs/", ".specify/")):
            continue
        if f not in tasks and Path(f).name not in tasks:
            out.append(Decision(f"I-{n:02d}", f"Changed {f}, which no task names", f, "unplanned-change", "medium"))
    return out


def extract(
    phase: str, root: Path, feature_dir: Path | None, findings: Path | None = None, base: str | None = None
) -> list[Decision]:
    if phase not in PHASES:
        raise ValueError(f"unknown phase {phase!r}; one of {', '.join(PHASES)}")
    if phase == "constitution":
        return from_constitution(root / ".specify" / "memory" / "constitution.md", root)
    if feature_dir is None:
        raise ValueError("this phase needs a feature directory (FEATURE_DIR)")
    if phase == "specify":
        return from_spec(feature_dir / "spec.md", root)
    if phase == "plan":
        return from_plan(feature_dir, root)
    if phase == "checklist":
        return from_checklists(feature_dir, root)
    if phase == "tasks":
        return from_tasks(feature_dir, root)
    if phase == "converge":
        return from_tasks(feature_dir, root, converge_only=True)
    if phase == "analyze":
        return from_analyze(findings)
    return from_implement(feature_dir, root, base)
