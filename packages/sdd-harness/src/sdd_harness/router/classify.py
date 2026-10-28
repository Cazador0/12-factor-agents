"""Lifecycle stages and the three catalog classes.

- **Core**: the skill for a Spec Kit lifecycle stage (constitution … converge, plus intake).
- **Useful support**: research, authoring, evaluation, diagram, Git or delivery work.
- **Conditional**: tied to a technology, service, domain or format; used only when the spec, the
  plan or the person calls for it.
"""

from __future__ import annotations

import re

STAGES: dict[str, tuple[str, ...]] = {
    "intake": ("intake", "rough idea", "idea", "what if", "hunch"),
    "assess": ("assess", "go/no-go", "triage an idea", "worth building"),
    "constitution": ("constitution", "principles", "governance", "project rules"),
    "specify": ("specify", "specification", "spec.md", "requirements", "user stories", "write a spec"),
    "clarify": ("clarify", "ambiguit", "clarification"),
    "plan": ("plan", "architecture", "design the", "technical context", "data model", "storage layer", "stack"),
    "checklist": ("checklist", "quality checklist"),
    "tasks": ("tasks", "task list", "break down", "breakdown", "work items"),
    "analyze": ("analyze", "consistency", "cross-artifact"),
    "implement": ("implement", "build it", "write the code", "coding"),
    "converge": ("converge", "remaining work", "gaps against the spec"),
    "refine": ("refine", "unbacked", "decision ledger", "what the phase decided"),
    "route": ("route", "which skill", "find a skill", "catalog"),
    "bug": ("bug", "defect", "regression", "broken"),
    "issues": ("taskstoissues", "issues from tasks", "gitea issues", "github issues"),
}

SUPPORT = (
    "research",
    "review",
    "code-review",
    "test",
    "testing",
    "eval",
    "benchmark",
    "debug",
    "document",
    "documentation",
    "docs",
    "author",
    "writing",
    "diagram",
    "mermaid",
    "git",
    "commit",
    "pull request",
    "deploy",
    "release",
    "ci",
    "standup",
    "architecture",
    "system-design",
    "tech-debt",
    "security",
    "simplify",
    "skill-creator",
    "create skills",
    "context",
    "agent context",
    "incident",
)
CONDITIONAL = (
    "pdf",
    "docx",
    "word",
    "xlsx",
    "excel",
    "pptx",
    "powerpoint",
    "slack",
    "gmail",
    "calendar",
    "salesforce",
    "hubspot",
    "figma",
    "canva",
    "notion",
    "asana",
    "jira",
    "linear",
    "snowflake",
    "bigquery",
    "databricks",
    "finance",
    "legal",
    "sales",
    "marketing",
    "hr",
    "payroll",
    "tax",
    "invoice",
    "ocaml",
    "gif",
    "browser",
    "chrome",
    "computer use",
    "brand",
    "theme",
    "art",
    "canvas",
)
LIFECYCLE_PREFIXES = ("speckit-", "sdd-")


def _has(text: str, words: tuple[str, ...]) -> bool:
    t = text.lower()
    return any(re.search(rf"(?<![a-z]){re.escape(w)}(?![a-z])", t) for w in words)


def stage_of(name: str, description: str) -> str | None:
    """The lifecycle stage a skill serves, judged from its name first, then its description."""
    n = name.lower()
    for prefix in LIFECYCLE_PREFIXES:
        if n.startswith(prefix):
            rest = n[len(prefix) :]
            segs = rest.split("-")
            if segs[-1] in STAGES:  # the command is the last segment: speckit-intake-refine → refine
                return segs[-1]
            for seg in reversed(segs):
                if seg in STAGES:
                    return seg
            if "intake" in rest:
                return "intake"
            if "ledger" in rest:
                return "refine"
            if "router" in rest:
                return "route"
    if n.startswith(LIFECYCLE_PREFIXES):
        for stage, words in STAGES.items():
            if _has(description, words):
                return stage
    return None


def classify(name: str, description: str, stage: str | None) -> str:
    if stage and name.lower().startswith(LIFECYCLE_PREFIXES):
        return "Core"
    text = f"{name} {description}"
    if _has(name, CONDITIONAL) or (_has(text, CONDITIONAL) and not _has(name, SUPPORT)):
        return "Conditional"
    if _has(text, SUPPORT):
        return "Useful support"
    return "Conditional"


_INFLECT = r"(?:s|es|ed|ing|ning|ned|ation|ations)?"


def _word_rx(w: str) -> re.Pattern[str]:
    """Whole words with common inflections: 'plan' matches 'planning', never 'plants'."""
    if " " in w or not w.isalpha():
        return re.compile(rf"(?<![a-z]){re.escape(w)}")
    return re.compile(rf"(?<![a-z]){re.escape(w)}{_INFLECT}(?![a-z])")


def task_stage(task: str) -> str | None:
    """The stage a task names ('plan the storage layer' → plan), or None."""
    t = task.lower()
    m = re.search(r"/?speckit[-.](\w+)", t)
    if m and m.group(1) in STAGES:
        return m.group(1)
    best, best_pos = None, len(t) + 1
    for stage, words in STAGES.items():
        for w in words:
            hit = _word_rx(w).search(t)
            if hit and hit.start() < best_pos:
                best, best_pos = stage, hit.start()
    return best


IDEA_SHAPES = re.compile(
    r"^(an?|the)\s+\w+.*\b(that|which|to|for)\b|\bwhat if\b|\bi (want|need|wish)\b|\bidea\b|\bhow about\b|"
    r"\bwouldn't it be\b|\bsomething (that|to)\b",
    re.I,
)


def looks_like_rough_idea(task: str) -> bool:
    """A rough idea names no lifecycle stage and no skill, and reads like a proposal."""
    if task_stage(task) not in (None, "intake"):
        return False
    if re.search(r"\b[a-z]+(?:-[a-z0-9]+){1,}\b", task) and "-" in task:  # a skill-like name
        return False
    return bool(IDEA_SHAPES.search(task.strip())) or len(task.split()) <= 3 and task_stage(task) == "intake"
