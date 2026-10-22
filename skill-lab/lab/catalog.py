"""skill-lab catalog: generate ``skills/CATALOG.json``, the machine-readable skill index.

The catalog lists every skill folder that has a parseable ``SKILL.md``, sorted
by name, with what a router or benchmark needs without opening each folder:
its description, metadata, entry scripts, vendored schemas and eval counts.
``catalog_bytes`` is the size of all names plus descriptions in UTF-8, the
quantity Zed caps at 50 KB (``MAX_SKILL_DESCRIPTIONS_SIZE``).

The file is generated, never hand-edited, and deterministic (no timestamps),
so ``skill-lab catalog --check`` can compare it byte for byte and exit 1 when
it is stale.
"""

from __future__ import annotations

import json
import os
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import cli as labcli
from . import paths
from _skillkit import EXIT_FAIL, EXIT_OK, EXIT_USAGE, frontmatter, fsutil
from _skillkit.cli import loads_strict
from _skillkit.envelope import ScriptError, ScriptResult, error

CATALOG_LIMIT_BYTES = 50 * 1024
"""Zed drops skills beyond 50 KB of names + descriptions (SOURCES.md)."""

CATALOG_WARN_BYTES = 40 * 1024
"""Warn before the budget is reached (80 %)."""

GENERATED_BY = "skill-lab catalog"
TIERS = ("deterministic", "agentic", "trigger")

CATALOG_SCHEMA: Dict[str, Any] = {
    "description": "skills/CATALOG.json as written by skill-lab catalog.",
    "type": "object",
    "required": ["schema_version", "generated_by", "skills", "catalog_bytes"],
    "properties": {
        "schema_version": {"const": 1},
        "generated_by": {"const": GENERATED_BY},
        "catalog_bytes": {"type": "integer", "minimum": 0},
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "required": [
                    "name",
                    "description",
                    "version",
                    "family",
                    "spec",
                    "path",
                    "scripts",
                    "schemas",
                    "eval_counts",
                ],
                "properties": {
                    "name": {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"},
                    "description": {"type": "string", "minLength": 1},
                    "version": {"type": ["string", "null"]},
                    "family": {"type": ["string", "null"]},
                    "spec": {"type": ["string", "null"]},
                    "path": {"type": "string", "pattern": "^skills/[a-z0-9]+(-[a-z0-9]+)*$"},
                    "scripts": {"type": "array", "items": {"type": "string", "pattern": "^scripts/[^/]+\\.py$"}},
                    "schemas": {"type": "array", "items": {"type": "string"}},
                    "eval_counts": {
                        "type": "object",
                        "required": list(TIERS),
                        "properties": {tier: {"type": "integer", "minimum": 0} for tier in TIERS},
                        "additionalProperties": False,
                    },
                },
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}

PAYLOAD_SCHEMA: Dict[str, Any] = {
    "description": "lab-catalog payload: what skill-lab catalog compared and wrote.",
    "type": "object",
    "required": ["schema_version", "path", "check", "written", "in_sync", "skills", "catalog_bytes", "limit"],
    "properties": {
        "schema_version": {"const": 1},
        "path": {"type": "string"},
        "check": {"type": "boolean"},
        "written": {"type": "boolean"},
        "in_sync": {"description": "Whether the file on disk matched before this run.", "type": "boolean"},
        "skills": {"type": "integer", "minimum": 0},
        "catalog_bytes": {"type": "integer", "minimum": 0},
        "limit": {"const": CATALOG_LIMIT_BYTES},
    },
    "additionalProperties": False,
}


def build_catalog(layout: paths.Layout) -> Tuple[dict, List[dict]]:
    """Return the catalog document and warnings for skills that had to be left out."""
    entries, warnings = [], []
    for name in paths.skill_names(layout):
        entry, reason = skill_entry(layout, name)
        if entry is None:
            warnings.append(
                error(
                    "SKILL_SKIPPED",
                    "%s left out of the catalog: %s" % (name, reason),
                    layout.rel(layout.skill_dir(name)),
                )
            )
        else:
            entries.append(entry)
    entries.sort(key=lambda item: item["name"])
    document = {
        "schema_version": 1,
        "generated_by": GENERATED_BY,
        "skills": entries,
        "catalog_bytes": sum(entry_bytes(entry) for entry in entries),
    }
    return document, warnings


def entry_bytes(entry: dict) -> int:
    """UTF-8 bytes of one skill's name plus description (Zed's catalog budget unit)."""
    return len((entry["name"] + entry["description"]).encode("utf-8"))


def skill_entry(layout: paths.Layout, name: str) -> Tuple[Optional[dict], Optional[str]]:
    """One catalog entry, or ``(None, reason)`` when ``SKILL.md`` cannot be indexed."""
    skill_dir = layout.skill_dir(name)
    try:
        with open(os.path.join(skill_dir, paths.SKILL_FILE), "r", encoding="utf-8") as handle:
            parsed = frontmatter.parse(handle.read())
    except (OSError, UnicodeDecodeError) as exc:
        return None, "SKILL.md is unreadable (%s)" % exc
    if not parsed.ok:
        return None, "frontmatter is invalid (run skill-lab validate)"
    description = parsed.data.get("description")
    if not isinstance(description, str) or not description.strip():
        return None, "description is missing"
    metadata = parsed.data.get("metadata")
    metadata = metadata if isinstance(metadata, dict) else {}
    entry = {
        "name": name,
        "description": description,
        "version": _string(metadata.get("version")),
        "family": _string(metadata.get("family")),
        "spec": _string(metadata.get("spec")),
        "path": "skills/" + name,
        "scripts": ["scripts/" + os.path.basename(path) for path in paths.entry_scripts(skill_dir)],
        "schemas": _vendored_schemas(skill_dir),
        "eval_counts": eval_counts(skill_dir),
    }
    return entry, None


def eval_counts(skill_dir: str) -> Dict[str, int]:
    """Cases per tier among the readable ``evals/cases/*.json`` files."""
    counts = {tier: 0 for tier in TIERS}
    for path in paths.case_files(skill_dir):
        try:
            with open(path, "r", encoding="utf-8") as handle:
                case = loads_strict(handle.read())
        except (OSError, UnicodeDecodeError, ValueError):
            continue
        tier = case.get("tier") if isinstance(case, dict) else None
        if tier in counts:
            counts[tier] += 1
    return counts


def render(document: dict) -> str:
    """The exact text written to CATALOG.json (sorted keys, 2-space indent, final newline)."""
    return json.dumps(document, sort_keys=True, ensure_ascii=False, indent=2, allow_nan=False) + "\n"


def read_current(layout: paths.Layout) -> Optional[str]:
    """The catalog file's text, or None when it does not exist or is unreadable."""
    try:
        with open(layout.catalog_path, "r", encoding="utf-8", newline="") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


def _vendored_schemas(skill_dir: str) -> List[str]:
    schemas_dir = os.path.join(skill_dir, "assets", "schemas")
    if not os.path.isdir(schemas_dir):
        return []
    return sorted(name for name in os.listdir(schemas_dir) if name.endswith(".json"))


def _string(value: Any) -> Optional[str]:
    return value if isinstance(value, str) else None


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    """``skill-lab catalog [--check]``."""
    return labcli.run_command(lambda: _run(argv), command="catalog", kind="lab-catalog", argv=argv)


def _run(argv: Sequence[str]) -> ScriptResult:
    parser = labcli.command_parser("catalog", "Generate skills/CATALOG.json from every skill's SKILL.md.")
    parser.add_argument(
        "--check", action="store_true", help="compare with the file on disk without writing; exit 1 when stale"
    )
    args = parser.parse_args(list(argv))
    layout = labcli.layout_from(args)
    if not os.path.isdir(layout.skills_dir):
        raise ScriptError(
            "SKILLS_DIR_NOT_FOUND", "no skills/ folder in the repository", path="skills", exit_code=EXIT_USAGE
        )

    document, warnings = build_catalog(layout)
    text = render(document)
    current = read_current(layout)
    in_sync = current == text
    written = False
    if not args.check and not in_sync:
        fsutil.atomic_write_text(layout.catalog_path, text)
        written = True
    if document["catalog_bytes"] > CATALOG_LIMIT_BYTES:
        warnings.append(
            error(
                "CATALOG_BUDGET_EXCEEDED",
                "names + descriptions are %d bytes; Zed drops skills beyond %d"
                % (document["catalog_bytes"], CATALOG_LIMIT_BYTES),
            )
        )
    payload = {
        "schema_version": 1,
        "path": layout.rel(layout.catalog_path),
        "check": bool(args.check),
        "written": written,
        "in_sync": in_sync,
        "skills": len(document["skills"]),
        "catalog_bytes": document["catalog_bytes"],
        "limit": CATALOG_LIMIT_BYTES,
    }
    if args.check and not in_sync:
        code, message = (
            ("CATALOG_MISSING", "skills/CATALOG.json does not exist")
            if current is None
            else (
                "CATALOG_STALE",
                "skills/CATALOG.json is out of date",
            )
        )
        failure = error(code, message + "; run skill-lab catalog", payload["path"])
        return ScriptResult(EXIT_FAIL, payload, [failure], warnings)
    return ScriptResult(EXIT_OK, payload, [], warnings)
