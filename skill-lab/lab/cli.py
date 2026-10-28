"""Subcommand registry and the plumbing every ``skill-lab`` command shares.

``COMMANDS`` maps each subcommand to ``module:function``. Modules are imported
lazily, so a command whose module is missing (``bench`` and ``score`` belong to
SPEC-102/104 and may not be installed yet) fails alone with
``COMMAND_UNAVAILABLE`` while every other command keeps working. Adding a
command means adding one row here and a module with ``main(argv) -> int``.

Each command prints exactly one ``envelope.v1`` on stdout (``run_command``),
accepts ``--pretty``, ``--now`` and ``--repo``, and uses the CONVENTIONS §3
exit codes. ``skill-lab --help`` and ``<command> --help`` print plain text and
exit 0, like any script's ``--help``.
"""

from __future__ import annotations

import importlib
import os
import sys
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Sequence

from . import LAB_VERSION, paths
from _skillkit import EXIT_OK, EXIT_USAGE, envelope
from _skillkit import cli as skcli
from _skillkit.envelope import ScriptError

PRODUCER = "skill-lab"
"""``producer.skill`` of every lab envelope."""


class Command(NamedTuple):
    module: str
    function: str
    summary: str


COMMANDS: Dict[str, Command] = {
    "validate": Command("lab.validate", "main", "check skills against every [V] rule in CONVENTIONS.md"),
    "sync": Command("lab.sync", "main", "vendor _skillkit and contract schemas into skills (--check: report drift)"),
    "install": Command("lab.install", "main", "link or copy skills into .agents/skills and .claude/skills"),
    "catalog": Command("lab.catalog", "main", "generate skills/CATALOG.json (--check: compare only)"),
    "new": Command("lab.scaffold", "main", "scaffold skills/<name>/ and its spec from the template"),
    "doctor": Command(
        "lab.doctor", "main", "report the toolchain, layout, installs, env presence and endpoint reachability"
    ),
    "test": Command("lab.testrun", "main", "run the lab and per-skill unittest suites and aggregate the counts"),
    "bench": Command("lab.bench", "main", "run benchmark cases (SPEC-102)"),
    "score": Command("lab.score", "main", "score skills against their release gates (SPEC-104)"),
}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Dispatch ``skill-lab <command> [options]`` and return the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] in ("-h", "--help"):
        sys.stdout.write(usage())
        return EXIT_OK
    if args and args[0] == "--version":
        sys.stdout.write("skill-lab %s\n" % LAB_VERSION)
        return EXIT_OK
    if not args or args[0].startswith("-"):
        return _fail(args, "USAGE", "missing command; run 'skill-lab --help' for the list")
    name, rest = args[0], args[1:]
    command = COMMANDS.get(name)
    if command is None:
        return _fail(rest, "USAGE", "unknown command %r; expected one of: %s" % (name, ", ".join(COMMANDS)))
    entry = _load(name, command)
    if isinstance(entry, ScriptError):
        return _fail(rest, entry.code, entry.message)
    return entry(rest)


def usage() -> str:
    """Plain-text help for ``skill-lab --help``."""
    width = max(len(name) for name in COMMANDS)
    lines = ["usage: skill-lab <command> [options]", "", "commands:"]
    lines += ["  %-*s  %s" % (width, name, command.summary) for name, command in COMMANDS.items()]
    lines += [
        "",
        "Run 'skill-lab <command> --help' for its options. Every command prints one JSON",
        "envelope (envelope.v1) on stdout; exit codes: 0 ok, 1 checked and failed,",
        "2 usage or input error, 3 external failure, 4 refused by policy.",
    ]
    return "\n".join(lines) + "\n"


def _load(name: str, command: Command) -> Any:
    """Import a command's entry point, or return the ScriptError explaining why it is unavailable."""
    try:
        module = importlib.import_module(command.module)
    except ModuleNotFoundError as exc:
        if exc.name != command.module:
            return ScriptError("INTERNAL", "importing %s failed: %s" % (command.module, exc))
        return ScriptError(
            "COMMAND_UNAVAILABLE",
            "'%s' is not available in this lab build (module %s not found)" % (name, command.module),
        )
    except Exception as exc:  # noqa: BLE001 - a broken command must still print one envelope
        return ScriptError("INTERNAL", "importing %s failed: %s: %s" % (command.module, type(exc).__name__, exc))
    entry = getattr(module, command.function, None)
    if not callable(entry):
        return ScriptError(
            "COMMAND_UNAVAILABLE", "'%s': %s has no callable %s()" % (name, command.module, command.function)
        )
    return entry


def _fail(argv: Sequence[str], code: str, message: str) -> int:
    def body() -> Any:
        raise ScriptError(code, message, exit_code=EXIT_USAGE)

    return run_command(body, command="skill-lab", kind="lab-cli", argv=argv)


# ---------------------------------------------------------------------------
# Plumbing shared by the command modules
# ---------------------------------------------------------------------------


def command_parser(command: str, description: str) -> skcli.SkillArgumentParser:
    """Parser with the lab's common flags: ``--pretty``, ``--now`` and ``--repo``.

    Usage errors raise ``ScriptError("USAGE")`` so the command still prints one envelope.
    """
    parser = skcli.base_parser(description, common=False, prog="skill-lab " + command)
    parser.add_argument("--pretty", action="store_true", help="indent the JSON envelope for humans")
    parser.add_argument("--now", metavar="ISO-8601", help="timestamp to use instead of the clock")
    parser.add_argument(
        "--repo",
        metavar="DIR",
        default=paths.DEFAULT_REPO_ROOT,
        help="repository root that holds skills/ and skill-lab/ (default: this lab's repository)",
    )
    return parser


def layout_from(args: Any) -> paths.Layout:
    """The ``Layout`` for ``--repo``; refuses a repository root that does not exist."""
    layout = paths.Layout.at(args.repo)
    if not os.path.isdir(layout.repo_root):
        raise ScriptError("REPO_NOT_FOUND", "repository root is not a directory", path=args.repo)
    return layout


def run_command(body: Callable[[], Any], *, command: str, kind: str, argv: Sequence[str]) -> int:
    """Run ``body()`` under ``envelope.run_script`` with the lab as producer."""
    return envelope.run_script(body, skill=PRODUCER, script=command, version=LAB_VERSION, kind=kind, argv=list(argv))


def rule_code(rule: str) -> str:
    """``frontmatter.name-pattern`` -> ``FRONTMATTER_NAME_PATTERN`` (an envelope error code)."""
    return rule.upper().replace(".", "_").replace("-", "_")


def capped(messages: List[dict], limit: int = 20) -> List[dict]:
    """At most ``limit`` messages, then one ``TRUNCATED`` note (envelopes allow 50)."""
    if len(messages) <= limit:
        return messages
    hidden = len(messages) - limit
    note = envelope.error("TRUNCATED", "%d more not shown; see the payload for the full list" % hidden)
    return messages[:limit] + [note]
