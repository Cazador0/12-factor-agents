"""skill-lab install: make skills discoverable by Zed, Codex and Claude Code.

Each runtime discovers skills in one folder (SOURCES.md):

- Zed and Codex: ``<project>/.agents/skills/<name>`` or ``~/.agents/skills/<name>``
- Claude Code:   ``<project>/.claude/skills/<name>`` or ``~/.claude/skills/<name>``

The default installs into the repository itself with **relative** symlinks
(``.agents/skills/x -> ../../skills/x``), so a clone works anywhere.
``--global`` installs into the home folder with absolute symlinks.
``--mode copy`` copies the folder instead and drops a ``.skill-lab-managed``
marker in it, for file systems or runtimes that do not follow symlinks.

Safety: an existing path the lab does not manage (not a symlink into
``skills/``, not a marked copy) is never touched. The run is refused with
``INSTALL_CONFLICT`` (exit 4) before anything changes, unless ``--force``.
``--dry-run`` prints the plan; ``--check`` verifies parity and exits 1 when
any skill is missing or stale. Managed entries whose skill no longer exists
are removed, except when ``--skill`` narrows the run.
"""

from __future__ import annotations

import json
import os
import shutil
import tempfile
from typing import Any, Dict, List, NamedTuple, Optional, Sequence

from . import cli as labcli
from . import paths
from _skillkit import EXIT_FAIL, EXIT_OK, EXIT_REFUSED, EXIT_USAGE
from _skillkit.envelope import ScriptError, ScriptResult, error

MISSING, LINKED, COPIED, STALE, FOREIGN, ORPHAN = "missing", "linked", "copied", "stale", "foreign", "orphan"
STATES = (MISSING, LINKED, COPIED, STALE, FOREIGN, ORPHAN)
INSTALLED = (LINKED, COPIED)
"""States in which the runtime sees exactly the skill's current content."""

ACTIONS = ("create", "replace", "remove", "none", "refuse")
MODES = ("symlink", "copy")

PAYLOAD_SCHEMA: Dict[str, Any] = {
    "description": "lab-install payload: the install plan (or parity check) and its outcome.",
    "type": "object",
    "required": [
        "schema_version",
        "scope",
        "root",
        "mode",
        "runtimes",
        "check",
        "dry_run",
        "force",
        "entries",
        "summary",
        "ok",
    ],
    "properties": {
        "schema_version": {"const": 1},
        "scope": {"enum": ["project", "global"]},
        "root": {"type": "string"},
        "mode": {"enum": list(MODES)},
        "runtimes": {"type": "array", "items": {"enum": list(paths.RUNTIMES)}, "minItems": 1, "uniqueItems": True},
        "check": {"type": "boolean"},
        "dry_run": {"type": "boolean"},
        "force": {"type": "boolean"},
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["skill", "runtimes", "path", "state", "action"],
                "properties": {
                    "skill": {"type": "string"},
                    "runtimes": {"type": "array", "items": {"enum": list(paths.RUNTIMES)}, "minItems": 1},
                    "path": {"type": "string"},
                    "state": {"enum": list(STATES)},
                    "action": {"enum": list(ACTIONS)},
                },
                "additionalProperties": False,
            },
        },
        "summary": {
            "type": "object",
            "required": list(ACTIONS),
            "properties": {action: {"type": "integer", "minimum": 0} for action in ACTIONS},
            "additionalProperties": False,
        },
        "ok": {"type": "boolean"},
    },
    "additionalProperties": False,
}


class Entry(NamedTuple):
    """One skill in one discovery folder: what is there now and what install would do."""

    skill: str
    runtimes: List[str]
    dest: str
    state: str
    action: str


# ---------------------------------------------------------------------------
# Inspection (also used by validate and doctor)
# ---------------------------------------------------------------------------


def classify(layout: paths.Layout, dest: str, skill_dir: Optional[str]) -> str:
    """State of ``dest`` relative to the skill it should show (``skill_dir`` None: the skill is gone)."""
    if not os.path.lexists(dest):
        return MISSING
    managed = is_managed(layout, dest)
    if skill_dir is None:
        return ORPHAN if managed else FOREIGN
    if os.path.islink(dest):
        if os.path.realpath(dest) == os.path.realpath(skill_dir):
            return LINKED
        return STALE if managed else FOREIGN
    if managed:
        return STALE if paths.compare_trees(skill_dir, dest, exclude_top=(paths.MANAGED_MARKER,)) else COPIED
    return FOREIGN


def is_managed(layout: paths.Layout, dest: str) -> bool:
    """True for a symlink into ``skills/`` (even a dangling one) or a copy carrying the marker."""
    if os.path.islink(dest):
        target = os.readlink(dest)
        lexical = os.path.normpath(target if os.path.isabs(target) else os.path.join(os.path.dirname(dest), target))
        return paths.lexically_within(lexical, layout.skills_dir) or paths.lexically_within(
            lexical, os.path.realpath(layout.skills_dir)
        )
    return os.path.isdir(dest) and os.path.isfile(os.path.join(dest, paths.MANAGED_MARKER))


def runtime_targets(root: str, runtimes: Sequence[str]) -> List[tuple]:
    """``[(discovery_dir, [runtimes sharing it]), ...]`` below ``root``."""
    return [(os.path.join(root, *folder), names) for folder, names in paths.runtime_dirs(runtimes)]


# ---------------------------------------------------------------------------
# Planning and applying
# ---------------------------------------------------------------------------


def plan(
    layout: paths.Layout,
    *,
    root: str,
    runtimes: Sequence[str],
    mode: str,
    skills: Sequence[str],
    prune: bool,
    force: bool,
) -> List[Entry]:
    """Every entry the install touches, sorted by discovery folder then skill."""
    entries = []
    known = set(paths.skill_names(layout))
    for target_dir, names in runtime_targets(root, runtimes):
        for skill in sorted(skills):
            dest = os.path.join(target_dir, skill)
            state = classify(layout, dest, layout.skill_dir(skill))
            entries.append(Entry(skill, names, dest, state, _action(state, mode, force)))
        if prune and os.path.isdir(target_dir):
            for orphan in sorted(set(os.listdir(target_dir)) - known):
                dest = os.path.join(target_dir, orphan)
                if classify(layout, dest, None) == ORPHAN:
                    entries.append(Entry(orphan, names, dest, ORPHAN, "remove"))
    return entries


def _action(state: str, mode: str, force: bool) -> str:
    if state == MISSING:
        return "create"
    if (state == LINKED and mode == "symlink") or (state == COPIED and mode == "copy"):
        return "none"
    if state == FOREIGN:
        return "replace" if force else "refuse"
    return "replace"  # stale, or installed in the other mode


def apply(layout: paths.Layout, entries: Sequence[Entry], *, mode: str, relative: bool) -> None:
    """Carry out a plan that contains no ``refuse`` actions."""
    for entry in entries:
        if entry.action == "remove":
            paths.remove_path(entry.dest)
        elif entry.action in ("create", "replace"):
            skill_dir = layout.skill_dir(entry.skill)
            if mode == "symlink":
                _install_symlink(skill_dir, entry.dest, relative=relative)
            else:
                _install_copy(layout, entry.skill, skill_dir, entry.dest)


def _install_symlink(skill_dir: str, dest: str, *, relative: bool) -> None:
    parent = os.path.dirname(dest)
    os.makedirs(parent, exist_ok=True)
    target = os.path.relpath(skill_dir, parent) if relative else os.path.realpath(skill_dir)
    if os.path.lexists(dest):
        paths.remove_path(dest)
    try:
        os.symlink(target, dest, target_is_directory=True)
    except OSError as exc:
        raise ScriptError(
            "SYMLINK_FAILED",
            "cannot create a symlink here (%s); use --mode copy" % (exc.strerror or exc),
            path=dest,
            exit_code=EXIT_USAGE,
        ) from None


def _install_copy(layout: paths.Layout, skill: str, skill_dir: str, dest: str) -> None:
    """Copy into a temporary sibling, add the marker, then swap it into place."""
    parent = os.path.dirname(dest)
    os.makedirs(parent, exist_ok=True)
    staging_root = tempfile.mkdtemp(prefix=".%s." % skill, dir=parent)
    try:
        staged = os.path.join(staging_root, skill)
        shutil.copytree(
            skill_dir, staged, ignore=shutil.ignore_patterns("__pycache__", "*.pyc", "*.pyo", paths.MANAGED_MARKER)
        )
        marker = {"managed_by": "skill-lab", "skill": skill, "source": layout.rel(skill_dir)}
        with open(os.path.join(staged, paths.MANAGED_MARKER), "w", encoding="utf-8") as handle:
            handle.write(json.dumps(marker, sort_keys=True) + "\n")
        if os.path.lexists(dest):
            paths.remove_path(dest)
        os.replace(staged, dest)
    finally:
        shutil.rmtree(staging_root, ignore_errors=True)


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    """``skill-lab install [--global | --project DIR] [--runtime R] [--mode M] [--dry-run] [--check] [--force]``."""
    return labcli.run_command(lambda: _run(argv), command="install", kind="lab-install", argv=argv)


def _parser():
    parser = labcli.command_parser(
        "install", "Install skills into the discovery folders of Zed, Codex and Claude Code."
    )
    scope = parser.add_mutually_exclusive_group()
    scope.add_argument(
        "--global", dest="global_scope", action="store_true", help="install into ~/.agents/skills and ~/.claude/skills"
    )
    scope.add_argument("--project", metavar="DIR", help="project root to install into (default: the repository root)")
    parser.add_argument(
        "--runtime",
        action="append",
        metavar="LIST",
        help="comma-separated runtimes: zed, codex, claude (default: all; zed and codex share .agents/skills)",
    )
    parser.add_argument("--mode", choices=MODES, default="symlink", help="symlink (default) or copy with a marker file")
    parser.add_argument("--skill", action="append", metavar="NAME", help="install only this skill (repeatable)")
    parser.add_argument("--dry-run", action="store_true", help="print the plan without changing anything")
    parser.add_argument(
        "--check", action="store_true", help="verify install parity without changing anything; exit 1 on drift"
    )
    parser.add_argument("--force", action="store_true", help="replace existing paths the lab does not manage")
    return parser


def _run(argv: Sequence[str]) -> ScriptResult:
    args = _parser().parse_args(list(argv))
    layout = labcli.layout_from(args)
    runtimes = _runtimes(args.runtime)
    skills = _skills(layout, args.skill)
    scope, root = _root(layout, args)
    entries = plan(
        layout,
        root=root,
        runtimes=runtimes,
        mode=args.mode,
        skills=skills,
        prune=not args.skill,
        force=args.force,
    )
    refused = [entry for entry in entries if entry.action == "refuse"]
    if args.check:
        ok = all(entry.state in INSTALLED for entry in entries)
    else:
        ok = not refused
        if ok and not args.dry_run:
            apply(layout, entries, mode=args.mode, relative=scope == "project")
    payload = _payload(args, scope, root, runtimes, entries, ok)
    warnings = [] if skills else [error("NO_SKILLS", "no skills under skills/ to install", "skills")]
    if args.check and not ok:
        drift = [entry for entry in entries if entry.state not in INSTALLED]
        errors = [_entry_error("INSTALL_DRIFT", entry, root, scope) for entry in drift]
        return ScriptResult(EXIT_FAIL, payload, labcli.capped(errors), warnings)
    if refused:
        errors = [_entry_error("INSTALL_CONFLICT", entry, root, scope) for entry in refused]
        return ScriptResult(EXIT_REFUSED, payload, labcli.capped(errors), warnings)
    return ScriptResult(EXIT_OK, payload, [], warnings)


def _runtimes(values: Optional[Sequence[str]]) -> List[str]:
    runtimes = paths.split_csv(values) or list(paths.RUNTIMES)
    unknown = [name for name in runtimes if name not in paths.RUNTIMES]
    if unknown:
        raise ScriptError(
            "USAGE", "unknown runtime %s; expected zed, codex or claude" % ", ".join(unknown), path="--runtime"
        )
    return sorted(runtimes)


def _skills(layout: paths.Layout, requested: Optional[Sequence[str]]) -> List[str]:
    available = paths.skill_names(layout)
    if not requested:
        return available
    missing = [name for name in paths.unique(requested) if name not in available]
    if missing:
        raise ScriptError("SKILL_NOT_FOUND", "no skill folder with SKILL.md: %s" % ", ".join(missing), path="skills")
    return paths.unique(requested)


def _root(layout: paths.Layout, args: Any) -> tuple:
    if args.global_scope:
        return "global", os.path.expanduser("~")
    root = os.path.abspath(args.project) if args.project else layout.repo_root
    if not os.path.isdir(root):
        raise ScriptError("PROJECT_NOT_FOUND", "project root is not a directory", path=args.project)
    return "project", root


def _display(path: str, root: str, scope: str) -> str:
    return paths.display_path(path, root, prefix="~/" if scope == "global" else "")


def _entry_error(code: str, entry: Entry, root: str, scope: str) -> dict:
    where = _display(entry.dest, root, scope)
    if code == "INSTALL_CONFLICT":
        message = "%s exists and is not managed by skill-lab; move it away or pass --force" % where
    else:
        message = "%s is %s for %s" % (where, entry.state, ", ".join(entry.runtimes))
    return error(code, message, where)


def _payload(args: Any, scope: str, root: str, runtimes: List[str], entries: List[Entry], ok: bool) -> dict:
    summary = {action: 0 for action in ACTIONS}
    for entry in entries:
        summary[entry.action] += 1
    return {
        "schema_version": 1,
        "scope": scope,
        "root": "~" if scope == "global" else root.replace(os.sep, "/"),
        "mode": args.mode,
        "runtimes": runtimes,
        "check": bool(args.check),
        "dry_run": bool(args.dry_run),
        "force": bool(args.force),
        "entries": [
            {
                "skill": entry.skill,
                "runtimes": entry.runtimes,
                "path": _display(entry.dest, root, scope),
                "state": entry.state,
                "action": entry.action,
            }
            for entry in entries
        ],
        "summary": summary,
        "ok": ok,
    }
