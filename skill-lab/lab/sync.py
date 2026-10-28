"""skill-lab sync: vendor the canonical ``_skillkit`` and contract schemas into skills.

Skills never import from ``skill-lab/`` at runtime (CONVENTIONS §1), so each
skill with a ``scripts/`` folder carries:

- ``scripts/_skillkit/``: an exact mirror of ``skill-lab/shared/_skillkit``
  (stale files removed, ``__pycache__`` ignored);
- ``assets/schemas/``: byte-identical copies of the canonical contracts it
  already vendors, always including ``envelope.v1.schema.json``.

``--add-schema NAME --skill X`` vendors one more contract into one skill.
``--check`` computes the same plan without writing and exits 1 when anything
would change. Files in ``assets/schemas`` that are not canonical contracts are
left alone and reported as warnings (``skill-lab validate`` rejects them).
Skills without ``scripts/`` are never touched.
"""

from __future__ import annotations

import os
from typing import Any, Dict, List, NamedTuple, Optional, Sequence

from . import cli as labcli
from . import paths
from _skillkit import EXIT_FAIL, EXIT_OK, EXIT_USAGE
from _skillkit.envelope import ScriptError, ScriptResult, error

ENVELOPE_SCHEMA_FILE = "envelope.v1.schema.json"
OPS = ("create", "update", "delete")

PAYLOAD_SCHEMA: Dict[str, Any] = {
    "description": "lab-sync payload: vendoring actions per skill (planned with --check, applied otherwise).",
    "type": "object",
    "required": ["schema_version", "check", "in_sync", "drift", "skills", "skipped"],
    "properties": {
        "schema_version": {"const": 1},
        "check": {"type": "boolean"},
        "in_sync": {"description": "True when nothing needed to change.", "type": "boolean"},
        "drift": {"description": "Number of actions needed (check) or applied.", "type": "integer", "minimum": 0},
        "skills": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "actions", "unknown_schemas"],
                "properties": {
                    "name": {"type": "string"},
                    "actions": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "required": ["op", "path"],
                            "properties": {"op": {"enum": list(OPS)}, "path": {"type": "string"}},
                            "additionalProperties": False,
                        },
                    },
                    "unknown_schemas": {"type": "array", "items": {"type": "string"}},
                },
                "additionalProperties": False,
            },
        },
        "skipped": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "reason"],
                "properties": {"name": {"type": "string"}, "reason": {"type": "string"}},
                "additionalProperties": False,
            },
        },
    },
    "additionalProperties": False,
}


class Action(NamedTuple):
    """One file operation: ``op`` on ``path`` (absolute), copying from ``source`` for create/update."""

    op: str
    path: str
    source: Optional[str] = None


class SkillPlan(NamedTuple):
    name: str
    skill_dir: str
    actions: List[Action]
    unknown_schemas: List[str]


def plan_skill(layout: paths.Layout, skill_dir: str, *, add_schemas: Sequence[str] = ()) -> SkillPlan:
    """Everything that must change for ``skill_dir`` to match the canonical sources."""
    actions = _skillkit_actions(layout, os.path.join(skill_dir, "scripts", "_skillkit"))
    schema_actions, unknown = _schema_actions(layout, os.path.join(skill_dir, "assets", "schemas"), add_schemas)
    return SkillPlan(os.path.basename(skill_dir), skill_dir, actions + schema_actions, unknown)


def apply_plan(skill_plan: SkillPlan) -> None:
    """Carry out a plan; deletions first, then copies, then empty folders are pruned."""
    for action in skill_plan.actions:
        if action.op == "delete":
            paths.remove_path(action.path)
    for action in skill_plan.actions:
        if action.op in ("create", "update"):
            paths.copy_file_atomic(action.source, action.path)
    vendored = os.path.join(skill_plan.skill_dir, "scripts", "_skillkit")
    if os.path.isdir(vendored):
        paths.prune_empty_dirs(vendored)


def _skillkit_actions(layout: paths.Layout, vendored: str) -> List[Action]:
    canonical = layout.skillkit_dir
    actions: List[Action] = []
    if os.path.lexists(vendored) and (os.path.islink(vendored) or not os.path.isdir(vendored)):
        actions.append(Action("delete", vendored))  # a file or symlink where the package belongs
        existing: List[str] = []
    else:
        existing = paths.list_tree(vendored) if os.path.isdir(vendored) else []
    wanted = paths.list_tree(canonical)
    for relative in wanted:
        source = os.path.join(canonical, *relative.split("/"))
        target = os.path.join(vendored, *relative.split("/"))
        if relative not in existing:
            actions.append(Action("create", target, source))
        elif not paths.files_equal(source, target):
            actions.append(Action("update", target, source))
    for relative in sorted(set(existing) - set(wanted)):
        actions.append(Action("delete", os.path.join(vendored, *relative.split("/"))))
    return actions


def _schema_actions(layout: paths.Layout, schemas_dir: str, add_schemas: Sequence[str]) -> tuple:
    canonical = set(paths.canonical_schema_files(layout))
    present = sorted(
        name for name in (os.listdir(schemas_dir) if os.path.isdir(schemas_dir) else []) if not paths.is_ignored(name)
    )
    unknown = [name for name in present if name not in canonical]
    wanted = sorted({ENVELOPE_SCHEMA_FILE} | {name for name in present if name in canonical} | set(add_schemas))
    actions = []
    for name in wanted:
        source = os.path.join(layout.schemas_dir, name)
        target = os.path.join(schemas_dir, name)
        if name not in present:
            actions.append(Action("create", target, source))
        elif not paths.files_equal(source, target):
            actions.append(Action("update", target, source))
    return actions, unknown


def schema_file_for(layout: paths.Layout, name: str) -> str:
    """Resolve ``--add-schema`` (``lease``, ``lease.v1`` or ``lease.v1.schema.json``) to a canonical file name."""
    if name.endswith(".schema.json"):
        filename = name
    elif ".v" in name:
        filename = name + ".schema.json"
    else:
        filename = name + ".v1.schema.json"
    if filename not in paths.canonical_schema_files(layout):
        raise ScriptError(
            "SCHEMA_NOT_FOUND", "no canonical contract %s" % filename, path="--add-schema", exit_code=EXIT_USAGE
        )
    return filename


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    """``skill-lab sync [--skill NAME]... [--add-schema NAME] [--check]``."""
    return labcli.run_command(lambda: _run(argv), command="sync", kind="lab-sync", argv=argv)


def _run(argv: Sequence[str]) -> ScriptResult:
    parser = labcli.command_parser("sync", "Vendor the canonical _skillkit and contract schemas into each skill.")
    parser.add_argument("--skill", action="append", metavar="NAME", help="sync only this skill (repeatable)")
    parser.add_argument(
        "--add-schema", action="append", metavar="NAME", help="also vendor this contract (needs exactly one --skill)"
    )
    parser.add_argument("--check", action="store_true", help="report drift without writing; exit 1 on drift")
    args = parser.parse_args(list(argv))
    layout = labcli.layout_from(args)
    if not os.path.isdir(layout.skillkit_dir):
        raise ScriptError("CANONICAL_NOT_FOUND", "canonical _skillkit is missing", path=layout.rel(layout.skillkit_dir))

    names = _select(layout, args.skill)
    add = [schema_file_for(layout, name) for name in paths.unique(args.add_schema or [])]
    if add and (not args.skill or len(names) != 1):
        raise ScriptError("USAGE", "--add-schema needs exactly one --skill", path="--add-schema")

    plans, skipped = [], []
    for name in names:
        skill_dir = layout.skill_dir(name)
        if not os.path.isdir(os.path.join(skill_dir, "scripts")):
            if add:
                raise ScriptError("SKILL_HAS_NO_SCRIPTS", "%s has no scripts/ folder; nothing to vendor into" % name)
            skipped.append({"name": name, "reason": "no scripts/ folder"})
            continue
        plans.append(plan_skill(layout, skill_dir, add_schemas=add))
    if not args.check:
        for skill_plan in plans:
            apply_plan(skill_plan)

    drift = sum(len(skill_plan.actions) for skill_plan in plans)
    payload = {
        "schema_version": 1,
        "check": bool(args.check),
        "in_sync": drift == 0,
        "drift": drift,
        "skills": [
            {
                "name": skill_plan.name,
                "actions": [{"op": action.op, "path": layout.rel(action.path)} for action in skill_plan.actions],
                "unknown_schemas": [
                    layout.rel(os.path.join(skill_plan.skill_dir, "assets", "schemas", f))
                    for f in skill_plan.unknown_schemas
                ],
            }
            for skill_plan in plans
        ],
        "skipped": skipped,
    }
    warnings = _warnings(layout, plans, names)
    if args.check and drift:
        errors = [
            error(
                "VENDOR_DRIFT",
                "%s: %d file(s) differ from canonical; run skill-lab sync" % (p.name, len(p.actions)),
                layout.rel(p.skill_dir),
            )
            for p in plans
            if p.actions
        ]
        return ScriptResult(EXIT_FAIL, payload, labcli.capped(errors), warnings)
    return ScriptResult(EXIT_OK, payload, [], warnings)


def _select(layout: paths.Layout, requested: Optional[Sequence[str]]) -> List[str]:
    available = paths.skill_names(layout)
    if not requested:
        return available
    missing = [name for name in paths.unique(requested) if name not in available]
    if missing:
        raise ScriptError("SKILL_NOT_FOUND", "no skill folder with SKILL.md: %s" % ", ".join(missing), path="skills")
    return paths.unique(requested)


def _warnings(layout: paths.Layout, plans: List[SkillPlan], names: List[str]) -> List[dict]:
    warnings = [] if names else [error("NO_SKILLS", "no skills under skills/ to sync", "skills")]
    for skill_plan in plans:
        for filename in skill_plan.unknown_schemas:
            path = layout.rel(os.path.join(skill_plan.skill_dir, "assets", "schemas", filename))
            warnings.append(error("UNKNOWN_SCHEMA", "not a canonical contract; left untouched", path))
    return labcli.capped(warnings)
