"""skill-lab test: run the lab's and every skill's unittest suites and aggregate the counts.

Suites, each in its own ``python -m unittest discover`` subprocess (with this
interpreter, so ``python3.9 skill-lab/bin/skill-lab test`` tests on 3.9):

- ``skill-lab``: ``-s skill-lab/tests -t skill-lab`` with cwd = the repository
  root, exactly the command CI runs;
- ``skills/<name>``: ``-s tests`` with cwd = the skill folder. The top-level
  directory is ``tests/`` itself, so a skill needs no ``__init__.py`` and two
  skills may reuse test module names. Skill tests locate their files from
  ``__file__`` (the scaffold's ``tests/test_example.py`` shows how).

``--skill NAME`` (repeatable) runs only those skills; ``--lab-only`` only the
lab suite. ``PYTHONDONTWRITEBYTECODE=1`` keeps ``__pycache__`` out of skill
folders. A suite's counts come from unittest's own summary lines; a suite that
prints none (an import crash, a timeout) is ``error``. Exit 1 when any suite
failed or errored. A skill without ``tests/`` is reported as ``missing``
(``skill-lab validate`` treats that as an error).
"""

from __future__ import annotations

import os
import re
import subprocess
import sys
import time
from typing import Any, Dict, List, NamedTuple, Optional, Sequence

from . import cli as labcli
from . import paths
from _skillkit import EXIT_FAIL, EXIT_OK
from _skillkit.envelope import ScriptError, ScriptResult, compact, error
from _skillkit.redact import redact_text

DEFAULT_TIMEOUT_S = 1800
LOG_TAIL_LINES = 30
STATUSES = ("passed", "failed", "error", "no_tests", "missing")
COUNT_KEYS = ("ran", "passed", "failed", "errored", "skipped")

_RAN_RE = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)
_RESULT_RE = re.compile(r"^(OK|FAILED|NO TESTS RAN)(?: \(([^)]*)\))?\s*$", re.MULTILINE)

PAYLOAD_SCHEMA: Dict[str, Any] = {
    "description": "lab-test payload: per-suite unittest counts and their totals.",
    "type": "object",
    "required": ["schema_version", "python", "ok", "suites", "totals"],
    "properties": {
        "schema_version": {"const": 1},
        "python": {"type": "string"},
        "ok": {"type": "boolean"},
        "suites": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["name", "path", "status", "duration_ms", "log_tail"] + list(COUNT_KEYS),
                "properties": dict(
                    {
                        "name": {"type": "string"},
                        "path": {"type": "string"},
                        "status": {"enum": list(STATUSES)},
                        "duration_ms": {"type": "integer", "minimum": 0},
                        "log_tail": {
                            "type": "array",
                            "items": {"type": "string", "maxLength": 300},
                            "maxItems": LOG_TAIL_LINES,
                        },
                    },
                    **{key: {"type": "integer", "minimum": 0} for key in COUNT_KEYS},
                ),
                "additionalProperties": False,
            },
        },
        "totals": {
            "type": "object",
            "required": ["suites"] + list(COUNT_KEYS),
            "properties": {key: {"type": "integer", "minimum": 0} for key in ("suites",) + COUNT_KEYS},
            "additionalProperties": False,
        },
    },
    "additionalProperties": False,
}


class Counts(NamedTuple):
    ran: int
    passed: int
    failed: int
    errored: int
    skipped: int


class Suite(NamedTuple):
    name: str
    path: str
    cwd: str
    args: List[str]


def parse_summary(output: str) -> Optional[Counts]:
    """Counts from unittest's ``Ran N tests`` and ``OK``/``FAILED (...)`` lines, or None."""
    ran_match = list(_RAN_RE.finditer(output))
    result_match = list(_RESULT_RE.finditer(output))
    if not ran_match or not result_match:
        return None
    ran = int(ran_match[-1].group(1))
    details: Dict[str, int] = {}
    for part in (result_match[-1].group(2) or "").split(","):
        key, _, value = part.strip().partition("=")
        if value.isdigit():
            details[key.strip()] = int(value)
    failed = details.get("failures", 0) + details.get("unexpected successes", 0)
    errored = details.get("errors", 0)
    skipped = details.get("skipped", 0)
    return Counts(ran, max(0, ran - failed - errored - skipped), failed, errored, skipped)


def suites_for(layout: paths.Layout, skills: Sequence[str], *, include_lab: bool) -> List[Suite]:
    suites = []
    if include_lab:
        suites.append(
            Suite(
                "skill-lab",
                layout.rel(layout.lab_tests_dir),
                layout.repo_root,
                ["discover", "-s", layout.lab_tests_dir, "-t", layout.lab_root],
            )
        )
    for name in skills:
        skill_dir = layout.skill_dir(name)
        suites.append(
            Suite(
                "skills/" + name, layout.rel(os.path.join(skill_dir, "tests")), skill_dir, ["discover", "-s", "tests"]
            )
        )
    return suites


def run_suite(suite: Suite, *, timeout: float) -> dict:
    """Run one suite and return its payload entry."""
    entry: Dict[str, Any] = {"name": suite.name, "path": suite.path, "log_tail": []}
    entry.update({key: 0 for key in COUNT_KEYS})
    if suite.name != "skill-lab" and not os.path.isdir(os.path.join(suite.cwd, "tests")):
        entry.update(status="missing", duration_ms=0)
        return entry
    started = time.monotonic()
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    try:
        proc = subprocess.run(
            [sys.executable, "-m", "unittest"] + suite.args,
            cwd=suite.cwd,
            env=env,
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            timeout=timeout,
        )
        output, returncode = proc.stdout.decode("utf-8", "replace"), proc.returncode
    except subprocess.TimeoutExpired as exc:
        output = (exc.output or b"").decode("utf-8", "replace") + "\nTIMEOUT after %ds" % timeout
        returncode = None
    entry["duration_ms"] = int((time.monotonic() - started) * 1000)
    counts = parse_summary(output) if returncode is not None else None
    if counts is None:
        status = "error"
    else:
        entry.update(counts._asdict())
        if counts.ran == 0:
            status = "no_tests"
        elif returncode == 0 and counts.failed == 0 and counts.errored == 0:
            status = "passed"
        else:
            status = "failed"
    entry["status"] = status
    if status not in ("passed", "no_tests"):
        entry["log_tail"] = [
            compact(redact_text(line)) for line in output.splitlines()[-LOG_TAIL_LINES:] if line.strip()
        ]
    return entry


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    """``skill-lab test [--skill NAME]... [--lab-only] [--timeout S]``."""
    return labcli.run_command(lambda: _run(argv), command="test", kind="lab-test", argv=argv)


def _run(argv: Sequence[str]) -> ScriptResult:
    parser = labcli.command_parser("test", "Run the lab and per-skill unittest suites and aggregate the counts.")
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--skill", action="append", metavar="NAME", help="run only this skill's tests (repeatable)")
    group.add_argument("--lab-only", action="store_true", help="run only skill-lab/tests")
    parser.add_argument(
        "--timeout", type=float, default=DEFAULT_TIMEOUT_S, metavar="S", help="per-suite timeout in seconds"
    )
    args = parser.parse_args(list(argv))
    layout = labcli.layout_from(args)
    if args.timeout <= 0:
        raise ScriptError("USAGE", "--timeout must be positive", path="--timeout")
    available = paths.skill_names(layout)
    if args.skill:
        missing = [name for name in paths.unique(args.skill) if name not in available]
        if missing:
            raise ScriptError(
                "SKILL_NOT_FOUND", "no skill folder with SKILL.md: %s" % ", ".join(missing), path="skills"
            )
        skills = paths.unique(args.skill)
    else:
        skills = [] if args.lab_only else available
    suites = [
        run_suite(suite, timeout=args.timeout) for suite in suites_for(layout, skills, include_lab=not args.skill)
    ]
    totals = {key: sum(suite[key] for suite in suites) for key in COUNT_KEYS}
    totals["suites"] = len(suites)
    bad = [suite for suite in suites if suite["status"] in ("failed", "error")]
    payload = {
        "schema_version": 1,
        "python": "%d.%d.%d" % sys.version_info[:3],
        "ok": not bad,
        "suites": suites,
        "totals": totals,
    }
    warnings = [
        error(
            "SUITE_" + suite["status"].upper(),
            "%s: %s" % (suite["name"], "no tests/ folder" if suite["status"] == "missing" else "no tests ran"),
            suite["path"],
        )
        for suite in suites
        if suite["status"] in ("missing", "no_tests")
    ]
    if bad:
        errors = [
            error(
                "TESTS_" + ("FAILED" if s["status"] == "failed" else "ERRORED"),
                "%s: %d failed, %d errored of %d" % (s["name"], s["failed"], s["errored"], s["ran"]),
                s["path"],
            )
            for s in bad
        ]
        return ScriptResult(EXIT_FAIL, payload, labcli.capped(errors), labcli.capped(warnings))
    return ScriptResult(EXIT_OK, payload, [], labcli.capped(warnings))
