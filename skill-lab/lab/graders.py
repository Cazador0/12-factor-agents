"""Grade benchmark-case outcomes into ``benchmark-result.v1`` fields (SPEC-102).

Pure functions, no I/O: ``lab.bench`` runs scripts, models and Jev and hands
the outcome here.

* deterministic: exit code, envelope validity (envelope plus payload against
  its ``kind_schema``, using the canonical contracts) and assertions.
* agentic: JSON reply, ``output_schema`` validity, assertions, then Jev
  judgments. noul bands (CONVENTIONS §5): ``pass`` >= threshold,
  ``uncertain`` in [0.35, threshold) which fails and needs a human, ``fail``
  below 0.35. score passes at ``score >= gte``; choice passes when the chosen
  label equals ``eq``.
* trigger: the routed skill equals ``expect_skill`` (``null`` means "none").

``expect.schema_valid: false`` means the case does not require a valid
document; the result then records ``schema_valid: null``, because the
contract lets a passing result carry only ``true`` or ``null``.
"""

from __future__ import annotations

from typing import Any, Dict, Iterable, List, Mapping, NamedTuple, Optional, Sequence

from _skillkit import assertions as assertion_ops
from _skillkit import cli, ids
from _skillkit.envelope import ScriptError, compact
from _skillkit.jsonschema_mini import validate
from _skillkit.schemas import validate_envelope

TIERS = ("deterministic", "agentic", "trigger")
UNCERTAIN_FLOOR = 0.35
MAX_ACTUAL_CHARS = 1000
MAX_NOTE = 300


class Grade(NamedTuple):
    status: str
    """``pass``, ``fail`` or ``error``."""
    schema_valid: Optional[bool]
    assertions: List[Dict[str, Any]]
    notes: List[str]
    error: Optional[Dict[str, str]] = None


def grade_deterministic(expect: Mapping[str, Any], exit_code: int, stdout: str, *, schema_dirs: Sequence[str]) -> Grade:
    """Grade one script run against a deterministic case's ``expect``."""
    notes: List[str] = []
    document = _parse_stdout(stdout, notes)
    schema_valid = None
    if expect["schema_valid"]:
        problems = (
            envelope_problems(document, exit_code, schema_dirs) if document is not None else ["stdout is not JSON"]
        )
        schema_valid = not problems
        notes.extend(note("envelope invalid: " + problem) for problem in problems[:3])
    checked = _assertions(document, expect["assertions"])
    if isinstance(checked, Grade):
        return checked._replace(schema_valid=schema_valid, notes=notes + checked.notes)
    if exit_code != expect["exit_code"]:
        notes.append("exit code %d, expected %d" % (exit_code, expect["exit_code"]))
    passed = exit_code == expect["exit_code"] and schema_valid is not False and all(a["passed"] for a in checked)
    notes.extend(_failed_assertion_notes(checked))
    return Grade("pass" if passed else "fail", schema_valid, checked, notes)


def grade_output(expect: Mapping[str, Any], data: Any, output_schema: Mapping[str, Any]) -> Grade:
    """Grade a model's parsed JSON (None when the reply had none) before any judgment."""
    notes: List[str] = []
    schema_valid = None
    if expect["schema_valid"]:
        issues = validate(data, output_schema) if data is not None else None
        schema_valid = issues == []
        if issues is None:
            notes.append("reply contains no JSON document")
        elif issues:
            first = issues[0]
            notes.append(
                note("output invalid (%d issues), first: %s: %s" % (len(issues), first.path or "/", first.message))
            )
    checked = _assertions(data, expect["assertions"])
    if isinstance(checked, Grade):
        return checked._replace(schema_valid=schema_valid, notes=notes + checked.notes)
    passed = schema_valid is not False and all(a["passed"] for a in checked)
    notes.extend(_failed_assertion_notes(checked))
    return Grade("pass" if passed else "fail", schema_valid, checked, notes)


def envelope_problems(document: Any, exit_code: int, schema_dirs: Sequence[str]) -> List[str]:
    """Why ``document`` is not a valid envelope for a process that exited ``exit_code`` (``[]`` when valid)."""
    try:
        issues = validate_envelope(document, exit_code=exit_code, search_dirs=schema_dirs)
    except ScriptError as exc:
        return ["%s: %s" % (exc.code, exc.message)]
    problems = ["%s: %s" % (issue.path or "/", issue.message) for issue in issues]
    if isinstance(document, dict) and isinstance(document.get("ok"), bool) and document["ok"] != (exit_code == 0):
        problems.append("ok is %s but the exit code is %d" % (str(document["ok"]).lower(), exit_code))
    return problems


def noul_band(probability: float, threshold: float) -> str:
    """``pass`` at or above ``threshold``, ``uncertain`` in [0.35, threshold), ``fail`` below 0.35."""
    if probability >= threshold:
        return "pass"
    return "uncertain" if probability >= UNCERTAIN_FLOOR else "fail"


def grade_judgment(judgment: Mapping[str, Any], answer: Any, request_id: Optional[str]) -> Dict[str, Any]:
    """One ``judgment_result`` from a typed Jev answer and the case's ``pass_if``."""
    kind, rule = judgment["type"], judgment["pass_if"]
    result: Dict[str, Any] = {"id": judgment["id"], "type": kind, "request_id": request_id}
    if kind == "noul":
        value: Any = answer.noul
        band = noul_band(value, rule["gte"])
    else:
        value = answer.score if kind == "score" else answer.choice
        passed = value >= rule["gte"] if kind == "score" else value == rule["eq"]
        band = "pass" if passed else "fail"
        result["confidence"] = answer.confidence
    result.update({"value": value, "pass": band == "pass", "band": band, "needs_human": band == "uncertain"})
    return result


def routed_skill(label: str, none_label: str) -> Optional[str]:
    """The routing label as a skill name (``none`` becomes None)."""
    return None if label == none_label else label


def top_probabilities(probabilities: Mapping[str, float], limit: int = 3) -> str:
    """``a=0.81, none=0.10, b=0.05``: the most likely labels, for a result note."""
    ranked = sorted(probabilities.items(), key=lambda item: (-item[1], item[0]))[:limit]
    return ", ".join("%s=%.2f" % (label, value) for label, value in ranked)


def tier_summary(results: Iterable[Mapping[str, Any]]) -> Dict[str, Any]:
    """``{total, passed, failed, errored, skipped, pass_rate}``; skipped cases never count as passed."""
    counts = {"pass": 0, "fail": 0, "error": 0, "skipped": 0}
    for result in results:
        counts[result["status"]] += 1
    graded = counts["pass"] + counts["fail"] + counts["error"]
    return {
        "total": graded + counts["skipped"],
        "passed": counts["pass"],
        "failed": counts["fail"],
        "errored": counts["error"],
        "skipped": counts["skipped"],
        "pass_rate": counts["pass"] / graded if graded else None,
    }


def summarize(results: Sequence[Mapping[str, Any]]) -> Dict[str, Dict[str, Any]]:
    """Summaries for each tier that has results, plus ``overall``."""
    summary = {
        tier: tier_summary(r for r in results if r["tier"] == tier)
        for tier in TIERS
        if any(r["tier"] == tier for r in results)
    }
    summary["overall"] = tier_summary(results)
    return summary


def note(text: str) -> str:
    """One compact result note (the contract allows one line of at most 500 characters)."""
    return compact(text, MAX_NOTE) or "-"


def compact_actual(value: Any) -> Any:
    """Keep assertion ``actual`` values small: large ones become a short description."""
    if value is None or isinstance(value, (bool, int, float)):
        return value
    if len(ids.canonical_json(value)) <= MAX_ACTUAL_CHARS:
        return value
    if isinstance(value, str):
        return value[:200] + "... (%d chars)" % len(value)
    if isinstance(value, list):
        return "<array of %d items>" % len(value)
    return "<object with %d keys>" % len(value)


def _parse_stdout(stdout: str, notes: List[str]) -> Any:
    if not stdout.strip():
        notes.append("stdout is empty")
        return None
    try:
        return cli.loads_strict(stdout)
    except ValueError as exc:
        notes.append(note("stdout is not one JSON document: %s" % exc))
        return None


def _assertions(document: Any, cases: Sequence[Mapping[str, Any]]) -> Any:
    """Evaluated assertions, or an ``error`` Grade when the case's assertions are malformed."""
    try:
        evaluated = assertion_ops.evaluate_all(document, list(cases))
    except assertion_ops.InvalidAssertion as exc:
        error = {"code": "ASSERTION_INVALID", "message": compact(str(exc), 300)}
        return Grade("error", None, [], [], error)
    for item in evaluated:
        item["actual"] = compact_actual(item["actual"])
    return evaluated


def _failed_assertion_notes(checked: Sequence[Mapping[str, Any]], limit: int = 3) -> List[str]:
    failed = [a for a in checked if not a["passed"]]
    notes = [
        note("assertion failed: %s %s (actual %s)" % (a["path"] or "/", a["op"], ids.canonical_json(a["actual"])))
        for a in failed[:limit]
    ]
    if len(failed) > limit:
        notes.append("%d more assertions failed" % (len(failed) - limit))
    return notes
