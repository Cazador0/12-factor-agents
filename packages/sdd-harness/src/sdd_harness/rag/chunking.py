"""Structural chunkers: chunk on meaning boundaries, never on fixed sizes alone.

Markdown → heading and subsection; specs → requirement, success criterion and user story;
tasks → one task; skills → one skill card plus its sections; Python → module-level symbol.
"""

from __future__ import annotations

import ast
import re
from collections.abc import Iterator
from dataclasses import dataclass, field
from pathlib import Path

from ..markdown import sections, split_front_matter

MAX_CHARS = 2400

_SPEC_DIR = re.compile(r"^(\d{3})-")
_REQ = re.compile(r"^\s*-\s*\*\*((?:FR|SC|NFR)-\d+)\*\*:?\s*(.*)$")
_TASK = re.compile(r"^\s*-\s*\[[ xX]\]\s*(T\d{3,})\b(.*)$")
_STORY = re.compile(r"^User Story (\d+)")


@dataclass
class Chunk:
    text: str
    path: str
    kind: str
    heading: str | None = None
    symbol: str | None = None
    spec_id: str | None = None
    extra: dict = field(default_factory=dict)


def spec_id_for(rel_path: str) -> str | None:
    """``specs/001-engineering-control-plane/spec.md`` → ``SPEC-001``."""
    parts = Path(rel_path).parts
    if len(parts) >= 2 and parts[0] == "specs":
        m = _SPEC_DIR.match(parts[1])
        if m:
            return f"SPEC-{m.group(1)}"
    return None


def _split_long(text: str) -> list[str]:
    if len(text) <= MAX_CHARS:
        return [text]
    out, buf = [], ""
    for para in re.split(r"\n\s*\n", text):
        if buf and len(buf) + len(para) + 2 > MAX_CHARS:
            out.append(buf)
            buf = para
        else:
            buf = f"{buf}\n\n{para}" if buf else para
    if buf:
        out.append(buf)
    return out


def chunk_markdown(text: str, rel_path: str, kind: str = "markdown") -> Iterator[Chunk]:
    spec_id = spec_id_for(rel_path)
    lines = text.splitlines()
    secs = [s for s in sections(lines) if s.level <= 4]
    if not secs:
        for part in _split_long(text.strip()):
            if part.strip():
                yield Chunk(part, rel_path, kind, spec_id=spec_id)
        return
    # Preamble before the first heading
    pre = "\n".join(lines[: secs[0].start]).strip()
    if pre:
        yield Chunk(pre, rel_path, kind, heading=None, spec_id=spec_id)
    trail: dict[int, str] = {}
    for idx, sec in enumerate(secs):
        trail[sec.level] = sec.title
        for lvl in [k for k in trail if k > sec.level]:
            del trail[lvl]
        # Own body: up to the next heading of any level
        body_end = secs[idx + 1].start if idx + 1 < len(secs) else len(lines)
        body = "\n".join(lines[sec.start + 1 : body_end]).strip()
        if not body:
            continue
        crumb = " › ".join(trail[k] for k in sorted(trail))
        for part in _split_long(body):
            yield Chunk(f"{crumb}\n\n{part}", rel_path, kind, heading=crumb, spec_id=spec_id)


def chunk_spec(text: str, rel_path: str) -> Iterator[Chunk]:
    """Heading chunks plus one chunk per requirement, criterion and user story."""
    spec_id = spec_id_for(rel_path)
    yield from chunk_markdown(text, rel_path, kind="spec")
    for line in text.splitlines():
        m = _REQ.match(line)
        if m:
            yield Chunk(
                f"{m.group(1)}: {m.group(2).strip()}",
                rel_path,
                "requirement",
                heading=m.group(1),
                symbol=m.group(1),
                spec_id=spec_id,
            )
    lines = text.splitlines()
    for sec in sections(lines):
        m = _STORY.match(sec.title)
        if m:
            body = "\n".join(lines[sec.start : sec.end]).strip()
            yield Chunk(body[:MAX_CHARS], rel_path, "user-story", heading=sec.title, spec_id=spec_id)


def chunk_tasks(text: str, rel_path: str) -> Iterator[Chunk]:
    spec_id = spec_id_for(rel_path)
    for line in text.splitlines():
        m = _TASK.match(line)
        if m:
            yield Chunk(line.strip(), rel_path, "task", heading=m.group(1), symbol=m.group(1), spec_id=spec_id)


def chunk_skill(text: str, rel_path: str) -> Iterator[Chunk]:
    meta, body = split_front_matter(text)
    name = str(meta.get("name") or Path(rel_path).parent.name)
    desc = str(meta.get("description") or "")
    first = body.strip().split("\n## ", 1)[0][:1200]
    yield Chunk(f"Skill {name}\n{desc}\n\n{first}", rel_path, "skill", heading=name, symbol=name)
    for c in chunk_markdown(body, rel_path, kind="skill-section"):
        c.symbol = name
        yield c


def chunk_python(text: str, rel_path: str) -> Iterator[Chunk]:
    try:
        tree = ast.parse(text)
    except SyntaxError:
        yield from chunk_markdown(text, rel_path, kind="code")
        return
    lines = text.splitlines()
    doc = ast.get_docstring(tree)
    if doc:
        yield Chunk(f"module {rel_path}\n{doc}", rel_path, "code", symbol=Path(rel_path).stem)
    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
            start = (node.decorator_list[0].lineno if node.decorator_list else node.lineno) - 1
            src = "\n".join(lines[start : node.end_lineno])
            for part in _split_long(src):
                yield Chunk(part, rel_path, "code", heading=node.name, symbol=node.name)


def chunk_file(path: Path, rel_path: str) -> Iterator[Chunk]:
    try:
        text = path.read_text(encoding="utf-8")
    except (OSError, UnicodeDecodeError):
        return
    name = path.name
    if name == "SKILL.md":
        yield from chunk_skill(text, rel_path)
    elif name == "spec.md":
        yield from chunk_spec(text, rel_path)
    elif name == "tasks.md":
        yield from chunk_markdown(text, rel_path, kind="tasks")
        yield from chunk_tasks(text, rel_path)
    elif path.suffix == ".md":
        kind = "intake" if "intakes" in Path(rel_path).parts else "markdown"
        if rel_path.endswith("memory/constitution.md"):
            kind = "constitution"
        yield from chunk_markdown(text, rel_path, kind=kind)
    elif path.suffix == ".py":
        yield from chunk_python(text, rel_path)
    elif path.suffix in {".yml", ".yaml", ".json", ".toml", ".txt"}:
        for part in _split_long(text.strip()):
            if part.strip():
                yield Chunk(part, rel_path, "config")
