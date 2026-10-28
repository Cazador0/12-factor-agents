"""Small, in-place Markdown edits: sections, pipe tables and front matter.

Intake files grow over a long session. Rewriting them wholesale is where earlier answers
get dropped, so every writer here edits one section, one table row or one line at a time.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

import yaml

_HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*$")


def split_front_matter(text: str) -> tuple[dict, str]:
    """Return (front matter, body). Missing or invalid front matter yields ``{}``."""
    if not text.startswith("---"):
        return {}, text
    match = re.match(r"\A---\s*\n(.*?)\n---\s*(?:\n|\Z)", text, flags=re.S)
    if not match:
        return {}, text
    try:
        data = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        data = {}
    return (data if isinstance(data, dict) else {}), text[match.end() :]


@dataclass
class Section:
    level: int
    title: str
    start: int  # line index of the heading
    end: int  # line index one past the section's last line


def sections(lines: list[str]) -> list[Section]:
    """Every heading with the span it owns (up to the next heading of the same or higher level)."""
    found: list[tuple[int, int, str]] = []
    in_fence = False
    for i, line in enumerate(lines):
        if line.lstrip().startswith("```"):
            in_fence = not in_fence
            continue
        if in_fence:
            continue
        m = _HEADING.match(line)
        if m:
            found.append((i, len(m.group(1)), m.group(2)))
    out: list[Section] = []
    for idx, (start, level, title) in enumerate(found):
        end = len(lines)
        for nxt_start, nxt_level, _ in found[idx + 1 :]:
            if nxt_level <= level:
                end = nxt_start
                break
        out.append(Section(level, title, start, end))
    return out


def find_section(lines: list[str], title: str, level: int | None = None) -> Section | None:
    """First section whose title equals ``title`` (or starts with it, for ``Q3 · …`` style headings)."""
    for sec in sections(lines):
        if level is not None and sec.level != level:
            continue
        if sec.title == title or sec.title.startswith(title + " ") or sec.title.startswith(title + "·"):
            return sec
    return None


def section_text(text: str, title: str, level: int | None = None) -> str:
    lines = text.splitlines()
    sec = find_section(lines, title, level)
    if not sec:
        return ""
    return "\n".join(lines[sec.start + 1 : sec.end]).strip("\n")


def append_to_section(text: str, title: str, new_lines: list[str], level: int | None = None) -> str:
    """Append lines at the end of a section, before any trailing blank lines."""
    lines = text.splitlines()
    sec = find_section(lines, title, level)
    if not sec:
        heading = "#" * (level or 2) + " " + title
        body = lines + ["", heading, "", *new_lines]
        return "\n".join(body).rstrip("\n") + "\n"
    insert_at = sec.end
    while insert_at - 1 > sec.start and not lines[insert_at - 1].strip():
        insert_at -= 1
    if insert_at - 1 == sec.start and new_lines and new_lines[0].strip():
        new_lines = ["", *new_lines]  # keep a blank line under the heading
    if insert_at < len(lines) and lines[insert_at].strip() and new_lines[-1].strip():
        new_lines = [*new_lines, ""]
    lines[insert_at:insert_at] = new_lines
    return "\n".join(lines).rstrip("\n") + "\n"


def replace_line(text: str, pattern: str, replacement: str, count: int = 1) -> str:
    """Replace the first line matching ``pattern`` (a regex anchored at line start)."""
    lines = text.splitlines()
    rx = re.compile(pattern)
    done = 0
    for i, line in enumerate(lines):
        if rx.match(line):
            lines[i] = replacement
            done += 1
            if done >= count:
                break
    return "\n".join(lines).rstrip("\n") + "\n"


def parse_table(block: str) -> list[dict[str, str]]:
    """Parse the first pipe table in ``block`` into dicts keyed by header."""
    rows = [ln.strip() for ln in block.splitlines() if ln.strip().startswith("|")]
    if len(rows) < 2:
        return []
    header = [c.strip() for c in rows[0].strip("|").split("|")]
    out = []
    for row in rows[2:]:
        cells = [c.strip() for c in _split_row(row)]
        cells += [""] * (len(header) - len(cells))
        out.append(dict(zip(header, cells, strict=False)))
    return out


def _split_row(row: str) -> list[str]:
    # Split on pipes that are not escaped as \|
    inner = row.strip()
    if inner.startswith("|"):
        inner = inner[1:]
    if inner.endswith("|"):
        inner = inner[:-1]
    return [c.replace("\\|", "|") for c in re.split(r"(?<!\\)\|", inner)]


def render_table(header: list[str], rows: list[list[str]]) -> list[str]:
    def esc(cell: str) -> str:
        return str(cell).replace("|", "\\|").replace("\n", " ")

    out = ["| " + " | ".join(header) + " |", "|" + "|".join("---" for _ in header) + "|"]
    out += ["| " + " | ".join(esc(c) for c in row) + " |" for row in rows]
    return out


def update_table_row(text: str, key_column: str, key: str, updates: dict[str, str]) -> str:
    """Update cells of the table row whose ``key_column`` equals ``key``. Other rows are untouched."""
    lines = text.splitlines()
    header: list[str] | None = None
    for i, line in enumerate(lines):
        stripped = line.strip()
        if not stripped.startswith("|"):
            header = None
            continue
        cells = [c.strip() for c in _split_row(stripped)]
        if header is None:
            header = cells
            continue
        if set(stripped.replace("|", "").strip()) <= {"-", ":", " "}:
            continue
        if key_column in header and cells[header.index(key_column)] == key:
            row = dict(zip(header, cells, strict=False))
            row.update(updates)
            lines[i] = "| " + " | ".join(str(row.get(h, "")).replace("|", "\\|") for h in header) + " |"
            return "\n".join(lines).rstrip("\n") + "\n"
    return text
