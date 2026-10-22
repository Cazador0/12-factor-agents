"""``skill-lab score``: one skill's release readiness against explicit gates (SPEC-104).

Inputs, each measured or explicitly reported as unavailable:

* static: the validator report for the skill (``--validation FILE``, else
  ``lab.validate`` in-process, else ``bin/skill-lab validate``), scored with
  the transparent rubric below;
* tests: the skill's own ``tests/test_*.py`` run with ``unittest``;
* bench: the latest ``benchmark-run`` in ``skill-lab/benchmarks/runs`` that
  has results for the skill (or ``--run PATH``);
* gates: ``benchmarks/criteria/_defaults.json`` merged with
  ``benchmarks/criteria/<skill>.json`` (``success-criteria.v1``).

Static rubric: start at 100; minus 25 per validator error and 5 per warning;
minus 10 when the description has no "Use when", 5 when it is outside 350-900
characters, 5 when the "Use when" clause names fewer than 2 trigger phrases;
clamped to 0..100. Findings in ``ENVIRONMENT_RULES`` (install state of this
machine) are not counted.

A gate whose metric was not measured never passes. It is ``not_run`` and
blocks ``release_ready``, unless the defaults mark it
``optional_when_unavailable`` (with an ``optional_reason``) and ``--strict``
is not given; then it is ``skipped``, listed in the warnings, and
``release_ready`` means "every gate that could run here passed"
(CONVENTIONS §9.6). Exit 0 when release-ready, 1 when not, 2 on bad input.
"""

from __future__ import annotations

import contextlib
import copy
import importlib.util
import io
import operator
import os
import re
import subprocess
import sys
from typing import Any, Callable, Dict, List, Mapping, NamedTuple, Optional, Sequence, Tuple

from _skillkit import EXIT_FAIL, EXIT_OK, cli, envelope, frontmatter, schemas, timeutil
from _skillkit.envelope import ScriptError, ScriptResult
from _skillkit.jsonschema_mini import validate

from . import cli as labcli
from . import graders, paths

SCHEMA_DIRS = (os.path.join(paths.LAB_ROOT, "contracts", "schemas"),)
DEFAULTS_PATH = os.path.join(paths.LAB_ROOT, "benchmarks", "criteria", "_defaults.json")
CRITERIA_DIR = os.path.join("benchmarks", "criteria")
RUNS_DIR = os.path.join("benchmarks", "runs")
RUN_FILE = "benchmark-run.json"
TESTS_TIMEOUT = 600.0
VALIDATOR_TIMEOUT = 300.0

ERROR_PENALTY = 25
WARNING_PENALTY = 5
# Validator findings about this machine's install state, not the skill's quality: validate still
# reports them, but they do not count against the static score.
ENVIRONMENT_RULES = frozenset({"install.not-installed"})
DESCRIPTION_BAND = (350, 900)
HEURISTICS = (
    ("use-when", 10, 'description has no "Use when" clause'),
    ("length-band", 5, "description is outside 350-900 characters"),
    ("trigger-phrases", 5, 'the "Use when" clause names fewer than 2 trigger phrases'),
)

TIER_COUNTS = ("cases", "passed", "failed", "errored", "skipped")
KNOWN_METRICS = tuple(
    ["static.score", "static.errors", "static.warnings"]
    + ["tests.%s" % key for key in ("ran", "passed", "failed", "errored", "skipped", "pass_rate")]
    + ["bench.%s.%s" % (tier, key) for tier in graders.TIERS for key in TIER_COUNTS + ("pass_rate",)]
    + ["bench.deterministic.schema_valid_rate", "bench.agentic.schema_valid_rate", "bench.trigger.accuracy"]
    + ["bench.jev.judgments", "bench.jev.uncertain_rate"]
)
_OPS: Dict[str, Callable[[float, float], bool]] = {
    "gte": operator.ge,
    "lte": operator.le,
    "gt": operator.gt,
    "lt": operator.lt,
    "eq": lambda actual, threshold: abs(actual - threshold) <= 1e-9,
}
_USE_WHEN_RE = re.compile(r"use when\b(.*?)(?:\bdo not use\b|$)", re.IGNORECASE | re.DOTALL)
_QUOTED_RE = re.compile(r"\"[^\"]+\"|'[^']+'|`[^`]+`|“[^”]+”")
_SPLIT_RE = re.compile(r",|;|\bor\b", re.IGNORECASE)
_RAN_RE = re.compile(r"^Ran (\d+) tests? in ", re.MULTILINE)
_OUTCOME_RE = re.compile(r"^(OK|FAILED)(?: \(([^)]*)\))?\s*$", re.MULTILINE)


class Measured(NamedTuple):
    """A measured input, or None plus why it is unavailable."""

    value: Any
    reason: str


class TestCounts(NamedTuple):
    ran: int
    passed: int
    failed: int
    errored: int
    skipped: int


def main(argv: Optional[Sequence[str]] = None) -> int:
    """Entry point for ``skill-lab score``; prints one envelope and returns the exit code."""
    argv = list(sys.argv[1:] if argv is None else argv)
    return labcli.run_command(lambda: score(argv), command="score", kind="skill-score", argv=argv)


def build_parser() -> cli.SkillArgumentParser:
    parser = labcli.command_parser("score", "Score one skill against its release gates.")
    parser.add_argument("--skill", required=True, metavar="NAME")
    parser.add_argument("--run", metavar="PATH", help="benchmark-run.json (or its folder) instead of the latest run")
    parser.add_argument(
        "--criteria", metavar="FILE", help="success-criteria file (default benchmarks/criteria/<skill>.json)"
    )
    parser.add_argument("--defaults", metavar="FILE", help="default gates (default the lab's _defaults.json)")
    parser.add_argument("--validation", metavar="FILE", help="validation-report (envelope or payload) to use")
    parser.add_argument("--no-tests", action="store_true", help="do not run the skill's unit tests")
    parser.add_argument("--strict", action="store_true", help="optional gates may not be skipped")
    return parser


def score(argv: Sequence[str]) -> ScriptResult:
    args = build_parser().parse_args(list(argv))
    now = cli.parse_now(args.now)
    layout = labcli.layout_from(args)
    if not frontmatter.NAME_RE.match(args.skill):
        raise ScriptError("USAGE", "--skill must be a skill name like review-verifier", path="--skill")
    skill_dir = layout.skill_dir(args.skill)
    skill_file = os.path.join(skill_dir, paths.SKILL_FILE)
    if not os.path.isfile(skill_file):
        raise ScriptError("SKILL_NOT_FOUND", "no SKILL.md for skill %s" % args.skill, path=layout.rel(skill_dir))
    parsed = frontmatter.parse(cli.read_text(skill_file), source=layout.rel(skill_file))
    warnings: List[Dict[str, Any]] = []

    validation = load_validation(args, layout)
    static_score, findings, heuristic_notes = static_rubric(parsed, validation, layout.rel(skill_file))
    warnings.extend(envelope.error("STATIC_HEURISTIC", text) for text in heuristic_notes)
    tests = Measured(None, "unit tests not run (--no-tests)") if args.no_tests else run_unit_tests(skill_dir)
    run_doc, run_warnings = load_run(args, layout)
    warnings.extend(run_warnings)
    results = [r for r in run_doc.value["results"] if r["skill"] == args.skill] if run_doc.value else []
    values, reasons = collect_metrics(static_score, findings, validation, tests, results, run_doc)

    gates = [evaluate_gate(gate, values, reasons, strict=args.strict) for gate in load_criteria(args, layout)]
    counts = tests.value
    tests_failed = (counts.failed + counts.errored) if counts else 0
    release_ready = tests_failed == 0 and all(gate["passed"] or gate.get("skipped") for gate in gates)
    payload = {
        "schema_version": 1,
        "skill": args.skill,
        "version": skill_version(parsed, warnings),
        "static": {"score": static_score, "findings": findings},
        "tests": {
            "passed": counts.passed if counts else 0,
            "failed": tests_failed,
            "skipped": counts.skipped if counts else 0,
        },
        "bench": {tier: _tier_summary(results, tier) for tier in graders.TIERS},
        "gates": gates,
        "release_ready": release_ready,
        "run_id": run_doc.value["run_id"] if run_doc.value else None,
        "computed_at": cli.to_iso(now),
    }
    issues = schemas.validate_payload("skill-score", payload, SCHEMA_DIRS)
    if issues:
        raise ScriptError("RESULT_INVALID", "skill-score invalid at %s: %s" % (issues[0].path, issues[0].message))
    warnings.extend(gate_warnings(gates, release_ready))
    errors = [] if release_ready else [not_ready_error(gates, tests_failed)]
    return ScriptResult(EXIT_OK if release_ready else EXIT_FAIL, payload, errors, labcli.capped(warnings))


# ---------------------------------------------------------------------------
# Static score
# ---------------------------------------------------------------------------


def static_rubric(
    parsed: frontmatter.FrontmatterResult, validation: Measured, source: str
) -> Tuple[float, Dict[str, int], List[str]]:
    """``(score, findings, notes)``; without a validator report the frontmatter lint stands in (partial)."""
    if validation.value is not None:
        errors, warnings = validation.value
    else:
        errors, warnings = len(parsed.issues) + len(frontmatter.lint(parsed, source=source)), 0
    description = parsed.data.get("description")
    failed = description_heuristics(description if isinstance(description, str) else "")
    total = 100 - ERROR_PENALTY * errors - WARNING_PENALTY * warnings - sum(penalty for _, penalty, _ in failed)
    notes = ["%s (-%d)" % (message, penalty) for _, penalty, message in failed]
    return float(max(0, min(100, total))), {"errors": errors, "warnings": warnings}, notes


def description_heuristics(description: str) -> List[Tuple[str, int, str]]:
    """The ``HEURISTICS`` entries the description fails."""
    clause = _USE_WHEN_RE.search(description)
    failed = []
    for check_id, penalty, message in HEURISTICS:
        if check_id == "use-when":
            ok = clause is not None
        elif check_id == "length-band":
            ok = DESCRIPTION_BAND[0] <= len(description) <= DESCRIPTION_BAND[1]
        else:
            ok = clause is not None and trigger_phrases(clause.group(1)) >= 2
        if not ok:
            failed.append((check_id, penalty, message))
    return failed


def trigger_phrases(clause: str) -> int:
    """Quoted phrases in a "Use when" clause, or else its comma/semicolon/"or"-separated parts."""
    quoted = _QUOTED_RE.findall(clause)
    if quoted:
        return len(quoted)
    sentence = clause.split(". ")[0]
    return len([part for part in _SPLIT_RE.split(sentence) if part.strip(" .")])


def load_validation(args: Any, layout: paths.Layout) -> Measured:
    """``((errors, warnings), "")`` for the skill, or ``(None, reason)``."""
    if args.validation:
        report, source = _report_from(cli.read_json(args.validation), args.validation), args.validation
    else:
        report, source = run_validator(args.skill, layout)
        if report is None:
            return Measured(None, source)
    issues = schemas.validate_payload("validation-report", report, SCHEMA_DIRS)
    if issues:
        raise ScriptError(
            "VALIDATION_INVALID",
            "validation report invalid at %s: %s" % (issues[0].path, issues[0].message),
            path=source,
        )
    entry = next((skill for skill in report["skills"] if skill["name"] == args.skill), None)
    if entry is None:
        return Measured(None, "the validation report has no entry for %s" % args.skill)
    severities = [finding["severity"] for finding in entry["findings"] if finding["rule"] not in ENVIRONMENT_RULES]
    return Measured((severities.count("error"), severities.count("warning")), "")


def run_validator(skill: str, layout: paths.Layout) -> Tuple[Optional[dict], str]:
    """Run ``skill-lab validate --skill NAME --repo ROOT``: ``(report, source)`` or ``(None, reason)``.

    ``lab.validate`` runs in-process when it is importable; otherwise
    ``bin/skill-lab validate`` runs as a subprocess.
    """
    argv = ["--skill", skill, "--repo", layout.repo_root]
    if importlib.util.find_spec("lab.validate") is not None:
        from . import validate as validator

        code, text = capture_envelope(validator.main, argv)
        return report_from_output(code, text, "lab.validate")
    command = os.path.join(paths.LAB_ROOT, "bin", "skill-lab")
    if not os.path.isfile(command):
        return None, "skill-lab validate is not available (no lab.validate module or bin/skill-lab)"
    try:
        completed = subprocess.run(
            [sys.executable, command, "validate"] + argv, capture_output=True, timeout=VALIDATOR_TIMEOUT, check=False
        )
    except (OSError, subprocess.TimeoutExpired) as exc:
        return None, "skill-lab validate could not run: %s" % exc
    return report_from_output(
        completed.returncode, completed.stdout.decode("utf-8", "replace"), "bin/skill-lab validate"
    )


def capture_envelope(entry: Callable[[List[str]], int], argv: List[str]) -> Tuple[int, str]:
    """Call a command's ``main(argv)`` in-process and return ``(exit_code, stdout text)``."""
    raw = io.BytesIO()
    captured = io.TextIOWrapper(raw, encoding="utf-8", write_through=True)
    try:
        with contextlib.redirect_stdout(captured):
            code = entry(argv)
    finally:
        captured.flush()
        captured.detach()
    return code, raw.getvalue().decode("utf-8", "replace")


def report_from_output(code: int, text: str, source: str) -> Tuple[Optional[dict], str]:
    """The validation-report payload from a validator's envelope, or ``(None, reason)``."""
    try:
        document = cli.loads_strict(text)
    except ValueError:
        return None, "%s printed no JSON envelope (exit %d)" % (source, code)
    if (
        code not in (EXIT_OK, EXIT_FAIL)
        or not isinstance(document, dict)
        or not isinstance(document.get("payload"), dict)
    ):
        codes = [error.get("code") for error in document.get("errors", [])] if isinstance(document, dict) else []
        return None, "%s did not produce a report (exit %d, errors %s)" % (source, code, codes or "none")
    return document["payload"], source


def _report_from(document: Any, source: str) -> dict:
    """A validation-report payload from an envelope or a bare payload."""
    if isinstance(document, dict) and document.get("schema") == envelope.ENVELOPE_SCHEMA:
        if document.get("kind") != "validation-report" or not isinstance(document.get("payload"), dict):
            raise ScriptError("VALIDATION_INVALID", "envelope carries no validation-report payload", path=source)
        return document["payload"]
    if not isinstance(document, dict):
        raise ScriptError("VALIDATION_INVALID", "not a validation-report document", path=source)
    return document


def skill_version(parsed: frontmatter.FrontmatterResult, warnings: List[Dict[str, Any]]) -> str:
    metadata = parsed.data.get("metadata")
    version = metadata.get("version") if isinstance(metadata, dict) else None
    if isinstance(version, str) and frontmatter.SEMVER_RE.match(version):
        return version
    warnings.append(envelope.error("VERSION_UNKNOWN", "SKILL.md has no semver metadata.version; reporting 0.0.0"))
    return "0.0.0"


# ---------------------------------------------------------------------------
# Unit tests
# ---------------------------------------------------------------------------


def run_unit_tests(skill_dir: str, timeout: float = TESTS_TIMEOUT) -> Measured:
    """Run ``tests/test_*.py`` with ``unittest`` in a clean environment and count the outcomes."""
    tests_dir = os.path.join(skill_dir, "tests")
    if not os.path.isdir(tests_dir) or not any(
        n.startswith("test_") and n.endswith(".py") for n in os.listdir(tests_dir)
    ):
        return Measured(None, "the skill has no tests/test_*.py")
    env = {name: os.environ[name] for name in ("PATH", "SYSTEMROOT", "HOME", "TMPDIR") if name in os.environ}
    env.update({"PYTHONDONTWRITEBYTECODE": "1", "PYTHONHASHSEED": "0", "PYTHONUTF8": "1"})
    argv = [sys.executable, "-m", "unittest", "discover", "-s", tests_dir, "-p", "test_*.py"]
    try:
        completed = subprocess.run(argv, cwd=skill_dir, env=env, capture_output=True, timeout=timeout, check=False)
    except subprocess.TimeoutExpired:
        return Measured(None, "unit tests did not finish within %.0fs" % timeout)
    except OSError as exc:
        return Measured(None, "unit tests could not start: %s" % exc)
    counts = parse_unittest_output(completed.stderr.decode("utf-8", "replace"))
    if counts is None:
        return Measured(None, "unittest output not understood (exit %d)" % completed.returncode)
    return Measured(counts, "")


def parse_unittest_output(text: str) -> Optional[TestCounts]:
    """Counts from unittest's summary (``Ran N tests`` + ``OK``/``FAILED (failures=1, ...)``)."""
    if "NO TESTS RAN" in text:
        return TestCounts(0, 0, 0, 0, 0)
    ran, outcome = _RAN_RE.findall(text), _OUTCOME_RE.findall(text)
    if not ran or not outcome:
        return None
    details: Dict[str, int] = {}
    for part in outcome[-1][1].split(","):
        key, _, value = part.strip().partition("=")
        if value.isdigit():
            details[key.strip()] = int(value)
    total = int(ran[-1])
    failed = details.get("failures", 0) + details.get("unexpected successes", 0)
    errored, skipped = details.get("errors", 0), details.get("skipped", 0)
    return TestCounts(total, max(0, total - failed - errored - skipped), failed, errored, skipped)


# ---------------------------------------------------------------------------
# Benchmark runs and metrics
# ---------------------------------------------------------------------------


def load_run(args: Any, layout: paths.Layout) -> Tuple[Measured, List[Dict[str, Any]]]:
    """The run to score: ``--run``, else the latest run with results for the skill."""
    if args.run:
        path = os.path.join(args.run, RUN_FILE) if os.path.isdir(args.run) else args.run
        document = cli.read_json(path)
        issues = schemas.validate_payload("benchmark-run", document, SCHEMA_DIRS)
        if issues:
            raise ScriptError(
                "RUN_INVALID", "benchmark-run invalid at %s: %s" % (issues[0].path, issues[0].message), path=path
            )
        return Measured(document, ""), []
    runs_dir = os.path.join(layout.lab_root, RUNS_DIR)
    candidates, warnings = [], []
    for name in sorted(os.listdir(runs_dir)) if os.path.isdir(runs_dir) else []:
        path = os.path.join(runs_dir, name, RUN_FILE)
        if not os.path.isfile(path):
            continue
        try:
            document = cli.read_json(path)
        except ScriptError as exc:
            warnings.append(envelope.error("RUN_IGNORED", exc.message, layout.rel(path)))
            continue
        if schemas.validate_payload("benchmark-run", document, SCHEMA_DIRS):
            warnings.append(envelope.error("RUN_IGNORED", "not a valid benchmark-run", layout.rel(path)))
        elif any(result["skill"] == args.skill for result in document["results"]):
            candidates.append(document)
    if not candidates:
        return Measured(
            None, "no benchmark run in %s has results for %s" % (layout.rel(runs_dir), args.skill)
        ), warnings
    latest = max(candidates, key=lambda doc: (timeutil.parse_rfc3339(doc["started_at"]), doc["run_id"]))
    return Measured(latest, ""), warnings


def collect_metrics(
    static_score: float,
    findings: Mapping[str, int],
    validation: Measured,
    tests: Measured,
    results: Sequence[Mapping[str, Any]],
    run_doc: Measured,
) -> Tuple[Dict[str, Optional[float]], Dict[str, str]]:
    """Every ``KNOWN_METRICS`` value (None when unmeasured) and, for each None, why."""
    values: Dict[str, Optional[float]] = {name: None for name in KNOWN_METRICS}
    reasons: Dict[str, str] = {}
    if validation.value is not None:
        values.update(
            {"static.score": static_score, "static.errors": findings["errors"], "static.warnings": findings["warnings"]}
        )
    else:
        partial = "validator report unavailable (%s); partial score %.0f from frontmatter lint only" % (
            validation.reason,
            static_score,
        )
        reasons.update({name: partial for name in ("static.score", "static.errors", "static.warnings")})
    _test_metrics(tests, values, reasons)
    for tier in graders.TIERS:
        _tier_metrics(tier, [r for r in results if r["tier"] == tier], run_doc, values, reasons)
    values["bench.trigger.accuracy"] = values["bench.trigger.pass_rate"]
    if values["bench.trigger.accuracy"] is None:
        reasons["bench.trigger.accuracy"] = reasons.get("bench.trigger.pass_rate", "not measured")
    _jev_metrics([r for r in results if r["tier"] == "agentic"], values, reasons)
    return values, reasons


def _test_metrics(tests: Measured, values: Dict[str, Optional[float]], reasons: Dict[str, str]) -> None:
    names = ["tests.%s" % key for key in ("ran", "passed", "failed", "errored", "skipped", "pass_rate")]
    counts = tests.value
    if counts is None:
        reasons.update({name: tests.reason for name in names})
        return
    graded = counts.passed + counts.failed + counts.errored
    values.update(
        {
            "tests.ran": counts.ran,
            "tests.passed": counts.passed,
            "tests.failed": counts.failed,
            "tests.errored": counts.errored,
            "tests.skipped": counts.skipped,
            "tests.pass_rate": counts.passed / graded if graded else None,
        }
    )
    if not graded:
        reasons["tests.pass_rate"] = "no unit test ran (or every test was skipped)"


def _tier_metrics(
    tier: str,
    results: Sequence[Mapping[str, Any]],
    run_doc: Measured,
    values: Dict[str, Optional[float]],
    reasons: Dict[str, str],
) -> None:
    prefix = "bench.%s." % tier
    names = [prefix + key for key in TIER_COUNTS + ("pass_rate", "schema_valid_rate")]
    if not results:
        reason = run_doc.reason or "run %s has no %s results for this skill" % (run_doc.value["run_id"], tier)
        reasons.update({name: reason for name in names})
        return
    summary = graders.tier_summary(results)
    values.update({prefix + "cases": summary["total"], prefix + "pass_rate": summary["pass_rate"]})
    values.update({prefix + key: summary[key] for key in TIER_COUNTS[1:]})
    if summary["pass_rate"] is None:
        first = next(r["skip_reason"] for r in results if r["status"] == "skipped")
        reasons[prefix + "pass_rate"] = graders.note("all %d %s cases were skipped: %s" % (len(results), tier, first))
    checked = [r["schema_valid"] for r in results if r.get("schema_valid") is not None]
    if tier in ("deterministic", "agentic"):
        values[prefix + "schema_valid_rate"] = checked.count(True) / len(checked) if checked else None
        if not checked:
            reasons[prefix + "schema_valid_rate"] = "no %s case checked schema validity" % tier


def _jev_metrics(
    results: Sequence[Mapping[str, Any]], values: Dict[str, Optional[float]], reasons: Dict[str, str]
) -> None:
    judgments = [judgment for result in results for judgment in result["judgments"]]
    graded = [result for result in results if result["status"] != "skipped"]
    values["bench.jev.judgments"] = len(judgments) if graded else None
    if judgments:
        values["bench.jev.uncertain_rate"] = sum(1 for j in judgments if j["band"] == "uncertain") / len(judgments)
        return
    reason = "no Jev judgments were made" if graded else reasons.get("bench.agentic.pass_rate", "no agentic results")
    reasons["bench.jev.uncertain_rate"] = reason
    if not graded:
        reasons["bench.jev.judgments"] = reason


def _tier_summary(results: Sequence[Mapping[str, Any]], tier: str) -> Optional[Dict[str, Any]]:
    selected = [r for r in results if r["tier"] == tier]
    return graders.tier_summary(selected) if selected else None


# ---------------------------------------------------------------------------
# Criteria and gates
# ---------------------------------------------------------------------------


def defaults_schema() -> Dict[str, Any]:
    """``_defaults.json``: success-criteria gates plus ``optional_when_unavailable`` and its reason."""
    contract = schemas.load_schema("success-criteria", SCHEMA_DIRS)
    gate = copy.deepcopy(contract["properties"]["gates"]["items"])
    gate["properties"].update(
        {"optional_when_unavailable": {"type": "boolean"}, "optional_reason": {"$ref": "#/$defs/line"}}
    )
    gate["anyOf"] = [
        {"not": {"required": ["optional_when_unavailable"]}},
        {"properties": {"optional_when_unavailable": {"const": False}}},
        {"required": ["optional_reason"]},
    ]
    return {
        "type": "object",
        "required": ["schema_version", "gates"],
        "properties": {
            "schema_version": {"const": 1},
            "description": {"type": "string"},
            "gates": {"type": "array", "items": gate, "minItems": 1},
        },
        "additionalProperties": False,
        "$defs": contract["$defs"],
    }


def load_criteria(args: Any, layout: paths.Layout) -> List[Dict[str, Any]]:
    """Default gates, overridden and extended by the skill's success-criteria file."""
    defaults_path = args.defaults or DEFAULTS_PATH
    defaults = cli.read_json(defaults_path)
    issues = validate(defaults, defaults_schema())
    if issues:
        raise ScriptError(
            "CRITERIA_INVALID", "defaults invalid at %s: %s" % (issues[0].path, issues[0].message), path=defaults_path
        )
    skill_path = args.criteria or os.path.join(layout.lab_root, CRITERIA_DIR, args.skill + ".json")
    overrides: List[Dict[str, Any]] = []
    if args.criteria or os.path.isfile(skill_path):
        document = cli.read_json(skill_path)
        issues = schemas.validate_payload("success-criteria", document, SCHEMA_DIRS)
        if issues:
            raise ScriptError("CRITERIA_INVALID", "%s: %s" % (issues[0].path, issues[0].message), path=skill_path)
        if document["skill"] != args.skill:
            raise ScriptError(
                "CRITERIA_INVALID", "criteria are for %s, not %s" % (document["skill"], args.skill), path=skill_path
            )
        overrides = document["gates"]
    gates = merge_gates(defaults["gates"], overrides)
    for gate in gates:
        if gate["metric"] not in KNOWN_METRICS:
            raise ScriptError(
                "UNKNOWN_METRIC", "gate %s uses unknown metric %s" % (gate["id"], gate["metric"]), path=skill_path
            )
    return gates


def merge_gates(defaults: Sequence[Mapping[str, Any]], overrides: Sequence[Mapping[str, Any]]) -> List[Dict[str, Any]]:
    """Apply a skill's gates on top of the defaults.

    A skill gate replaces the default gate with the same ``id`` or, failing
    that, the not yet replaced default gate on the same ``metric``, and keeps
    that default's optionality. Any other skill gate is appended and is
    mandatory: success-criteria.v1 has no optionality field.
    """
    merged: List[Dict[str, Any]] = [dict(gate) for gate in defaults]
    replaced = [False] * len(merged)
    seen = set()
    for gate in overrides:
        if gate["id"] in seen:
            raise ScriptError("CRITERIA_INVALID", "gate id %s appears twice" % gate["id"])
        seen.add(gate["id"])
        index = _matching_default(merged, replaced, gate)
        if index is None:
            merged.append(dict(gate))
            replaced.append(True)
            continue
        replacement = dict(gate)
        for key in ("optional_when_unavailable", "optional_reason"):
            if key in merged[index]:
                replacement[key] = merged[index][key]
        merged[index], replaced[index] = replacement, True
    return merged


def _matching_default(merged: List[Dict[str, Any]], replaced: List[bool], gate: Mapping[str, Any]) -> Optional[int]:
    for key in ("id", "metric"):
        for index, candidate in enumerate(merged):
            if not replaced[index] and candidate[key] == gate[key]:
                return index
    return None


def evaluate_gate(
    gate: Mapping[str, Any], values: Mapping[str, Optional[float]], reasons: Mapping[str, str], *, strict: bool
) -> Dict[str, Any]:
    """A ``gate_result``; ``reason`` starts with its status (``fail``, ``not_run`` or ``skipped``)."""
    actual = values[gate["metric"]]
    result: Dict[str, Any] = {
        "id": gate["id"],
        "metric": gate["metric"],
        "op": gate["op"],
        "actual": actual,
        "threshold": gate["threshold"],
        "passed": False,
        "skipped": False,
        "reason": None,
    }
    if actual is None:
        why = reasons.get(gate["metric"], "not measured")
        if gate.get("optional_when_unavailable") and not strict:
            text = "skipped: %s (optional when unavailable: %s)" % (why, gate["optional_reason"])
            result.update(skipped=True, reason=graders.note(text))
        else:
            result["reason"] = graders.note("not_run: " + why)
        return result
    result["passed"] = _OPS[gate["op"]](actual, gate["threshold"])
    if not result["passed"]:
        result["reason"] = "fail: %s %s %s does not hold" % (_number(actual), gate["op"], _number(gate["threshold"]))
    return result


def gate_status(gate: Mapping[str, Any]) -> str:
    """``pass``, ``fail``, ``not_run`` or ``skipped`` for a gate result."""
    if gate["passed"]:
        return "pass"
    if gate.get("skipped"):
        return "skipped"
    return "not_run" if gate["actual"] is None else "fail"


def gate_warnings(gates: Sequence[Mapping[str, Any]], release_ready: bool) -> List[Dict[str, Any]]:
    """One warning per gate that did not run, plus a note when readiness covers only part of the gates."""
    warnings = []
    for index, gate in enumerate(gates):
        status = gate_status(gate)
        if status in ("skipped", "not_run"):
            code = "GATE_SKIPPED" if status == "skipped" else "GATE_NOT_RUN"
            warnings.append(envelope.error(code, "%s: %s" % (gate["id"], gate["reason"]), "/gates/%d" % index))
    skipped = [gate["id"] for gate in gates if gate_status(gate) == "skipped"]
    if release_ready and skipped:
        message = "release_ready covers only the gates that could run here; skipped: %s" % ", ".join(skipped)
        warnings.append(envelope.error("RELEASE_READY_OFFLINE", message))
    return warnings


def not_ready_error(gates: Sequence[Mapping[str, Any]], tests_failed: int) -> Dict[str, Any]:
    by_status: Dict[str, List[str]] = {}
    for gate in gates:
        by_status.setdefault(gate_status(gate), []).append(gate["id"])
    parts = ["%s: %s" % (status, ", ".join(by_status[status])) for status in ("fail", "not_run") if status in by_status]
    if tests_failed:
        parts.append("%d unit tests failed or errored" % tests_failed)
    return envelope.error("NOT_RELEASE_READY", "; ".join(parts) or "not release-ready")


def _number(value: float) -> str:
    return ("%.4f" % value).rstrip("0").rstrip(".") if isinstance(value, float) else str(value)


if __name__ == "__main__":
    sys.exit(main())
