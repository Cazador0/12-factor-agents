"""Contract catalog tests: every schema exists, stays in the keyword subset, is closed,
validates its example, and rejects crafted violations of each rule and invariant.

When the third-party ``jsonschema`` package is importable, every example and
crafted instance is also cross-checked against it (``TestDifferential``);
otherwise that class is skipped.
"""

from __future__ import annotations

import copy
import json
import os
import re
import unittest

from tests import skillkit_support as support
from _skillkit import jsonpointer
from _skillkit.jsonschema_mini import SchemaError, unsupported_keywords, validate

try:
    import jsonschema as reference
except ImportError:  # pragma: no cover - depends on the environment
    reference = None

DRAFT = "https://json-schema.org/draft/2020-12/schema"
DOCUMENT_CONTRACTS = {"envelope", "benchmark-case"}  # identified by a "schema" URN, not schema_version
OPEN_OBJECTS = {
    ("envelope", "/properties/payload"),
    ("mutation-request", "/properties/params"),
    ("gitea-plan", "/properties/operations/items/properties/request/properties/body"),
    ("benchmark-case", "/$defs/jev_content/anyOf/1"),
}
HEAD = "4f2c9a1e7b3d5f60a8c2e1d9b7f4a3c2e1d0b9a8"
_DELETE = object()


def changed(name, *changes):
    """Deep copy of example ``name`` with ``(pointer, value)`` changes applied.

    ``value`` may be ``_DELETE`` to remove the member; a pointer ending in
    ``/-`` appends to an array.
    """
    doc = copy.deepcopy(support.load_example(name))
    for pointer, value in changes:
        tokens = jsonpointer.split(pointer)
        parent = jsonpointer.resolve(doc, jsonpointer.join("", *tokens[:-1]))
        last = tokens[-1]
        if isinstance(parent, list):
            if last == "-":
                parent.append(value)
            elif value is _DELETE:
                del parent[int(last)]
            else:
                parent[int(last)] = value
        elif value is _DELETE:
            del parent[last]
        else:
            parent[last] = value
    return doc


def walk(schema, pointer=""):
    """Yield (pointer, subschema) for every schema object in a schema document."""
    if not isinstance(schema, dict):
        return
    yield pointer, schema
    for keyword in ("properties", "$defs"):
        for key, sub in schema.get(keyword, {}).items():
            yield from walk(sub, jsonpointer.join(pointer, keyword, key))
    for keyword in ("prefixItems", "oneOf", "anyOf", "allOf"):
        for index, sub in enumerate(schema.get(keyword, [])):
            yield from walk(sub, jsonpointer.join(pointer, keyword, index))
    for keyword in ("additionalProperties", "items", "not"):
        if isinstance(schema.get(keyword), dict):
            yield from walk(schema[keyword], jsonpointer.join(pointer, keyword))


# --------------------------------------------------------------------------
# Crafted instances. Each invalid case breaks exactly one rule of its contract.
# --------------------------------------------------------------------------

JUDGMENT_NOUL = {
    "id": "cites-evidence",
    "type": "noul",
    "instructions": "Every blocker in the verdict cites a test, file:line or artifact as evidence.",
    "criteria": {"true": "All blockers cite concrete evidence.", "false": "At least one blocker is unsupported."},
    "state_from": ["output", "fixtures"],
    "pass_if": {"gte": 0.8},
}
JUDGMENT_SCORE = {
    "id": "verdict-clarity",
    "type": "score",
    "instructions": {"task": "Rate how actionable the summary is."},
    "criteria": ["Not actionable", "Partly actionable", "Fully actionable"],
    "state_from": ["output"],
    "pass_if": {"gte": 1.5},
}
JUDGMENT_CHOICE = {
    "id": "result-kind",
    "type": "choice",
    "instructions": "Which verdict does the evidence support?",
    "criteria": {"APPROVE": "No requirement fails.", "CHANGES_REQUESTED": None, "BLOCKED_BY_ENV": ["env", "missing"]},
    "state_from": ["fixtures", "prompt", "skill"],
    "pass_if": {"eq": "CHANGES_REQUESTED"},
}
AGENTIC_CASE = {
    "schema": "urn:skill-lab:schema:benchmark-case:v1",
    "schema_version": 1,
    "id": "verdict-cites-evidence",
    "skill": "review-verifier",
    "tier": "agentic",
    "description": "The model returns a schema-valid verdict whose blockers cite evidence.",
    "prompt": "Review PR 211 against specs/042-session-refresh/spec.md using the evidence in the fixtures.",
    "fixtures": ["evals/fixtures/pr-211-evidence.json", "evals/fixtures/spec.md"],
    "output_schema": "urn:skill-lab:schema:review-verdict:v1",
    "expect": {"schema_valid": True, "assertions": [{"path": "/result", "op": "eq", "value": "CHANGES_REQUESTED"}]},
    "judgments": [JUDGMENT_NOUL, JUDGMENT_SCORE, JUDGMENT_CHOICE],
    "timeout_s": 300,
}
TRIGGER_CASE = {
    "schema": "urn:skill-lab:schema:benchmark-case:v1",
    "id": "routes-review-request",
    "skill": "review-verifier",
    "tier": "trigger",
    "description": "A plain review request routes to review-verifier.",
    "query": "Can you independently verify PR 211 against its spec and give me a verdict?",
    "expect_skill": "review-verifier",
}


def case(base="deterministic", **changes):
    """A benchmark case of tier ``base`` with top-level members replaced (or removed)."""
    templates = {"agentic": AGENTIC_CASE, "trigger": TRIGGER_CASE}
    doc = copy.deepcopy(templates[base]) if base in templates else support.load_example("benchmark-case")
    for key, value in changes.items():
        if value is _DELETE:
            doc.pop(key, None)
        else:
            doc[key] = value
    return doc


def judgment(base, **changes):
    doc = copy.deepcopy(base)
    doc.update(changes)
    return case("agentic", judgments=[doc])


AGENTIC_RESULT = {
    "schema_version": 1,
    "case_id": "verdict-cites-evidence",
    "skill": "review-verifier",
    "tier": "agentic",
    "runtime": "zed-ollama-local",
    "model": "synthetic-test-model",
    "status": "fail",
    "schema_valid": True,
    "assertions": [{"path": "/result", "op": "eq", "passed": True, "actual": "CHANGES_REQUESTED"}],
    "judgments": [
        {
            "id": "cites-evidence",
            "type": "noul",
            "value": 0.5,
            "pass": False,
            "band": "uncertain",
            "needs_human": True,
            "confidence": None,
            "request_id": None,
        }
    ],
    "duration_ms": 1,
    "jev_mode": "replay",
    "notes": ["Synthetic shape fixture for schema tests; not a model result."],
}


def result(**changes):
    doc = copy.deepcopy(AGENTIC_RESULT)
    doc.update(changes)
    return doc


FACTORS = support.load_example("twelve-factor-scorecard")["factors"]

VALID = {
    "envelope": [
        (
            "failed run without payload",
            changed(
                "envelope",
                ("/ok", False),
                ("/payload", None),
                ("/errors", [{"code": "INPUT_NOT_FOUND", "message": "file not found", "path": "x.json"}]),
            ),
        ),
        (
            "minimal error without path",
            changed("envelope", ("/ok", False), ("/errors", [{"code": "X", "message": ""}])),
        ),
    ],
    "mutation-request": [
        (
            "create with null version and string id",
            changed(
                "mutation-request",
                ("/expected_version", None),
                ("/target", {"type": "branch", "id": "agent/pse/184-x"}),
            ),
        ),
        (
            "minimal",
            changed(
                "mutation-request",
                ("/repository", _DELETE),
                ("/lease_id", _DELETE),
                ("/params", _DELETE),
                ("/requested_at", _DELETE),
            ),
        ),
    ],
    "task-graph": [
        ("cyclic graph has no waves", changed("task-graph", ("/waves", []), ("/cycles", [["T003", "T005", "T003"]])))
    ],
    "spec-readiness": [
        (
            "ready",
            changed(
                "spec-readiness",
                ("/ready", True),
                ("/checks/1/status", "pass"),
                ("/missing", []),
                ("/traceability/uncovered", []),
                ("/traceability/covered", 8),
            ),
        ),
        ("nfr uncovered", changed("spec-readiness", ("/traceability/uncovered", ["NFR-002"]))),
    ],
    "issue-contract": [("not created yet", changed("issue-contract", ("/issue_ref", None), ("/dependencies", [])))],
    "implementation-evidence": [
        ("no migrations", changed("implementation-evidence", ("/migrations", {"present": False})))
    ],
    "review-verdict": [
        (
            "blocked by environment",
            changed(
                "review-verdict",
                ("/result", "BLOCKED_BY_ENV"),
                ("/blockers", []),
                ("/requirements", {"covered": 10, "failed": 0, "unverified": 4}),
            ),
        ),
        ("changes requested by failed requirement", changed("review-verdict", ("/blockers", []))),
        ("approve", support.load_example("envelope")["payload"]),
    ],
    "quality-gate": [("failing gate", changed("quality-gate", ("/categories/e2e/status", "fail"), ("/passed", False)))],
    "session-checkpoint": [
        (
            "fresh session",
            changed(
                "session-checkpoint",
                ("/issue", None),
                ("/spec", None),
                ("/branch", None),
                ("/head_commit", None),
                ("/lease", {}),
            ),
        )
    ],
    "normalized-event": [
        (
            "issue-less event",
            changed(
                "normalized-event",
                ("/issue", _DELETE),
                ("/pull_request", _DELETE),
                ("/commit", _DELETE),
                ("/next_action", None),
            ),
        )
    ],
    "lease": [
        (
            "released",
            changed(
                "lease",
                ("/status", "released"),
                ("/released_at", "2026-10-22T08:30:00Z"),
                ("/release_reason", "PR opened"),
            ),
        )
    ],
    "transition-decision": [
        ("refused", changed("transition-decision", ("/allowed", False), ("/preconditions/1/met", False))),
        ("wait", changed("transition-decision", ("/action", "WAIT"), ("/to_state", None))),
    ],
    "merge-decision": [
        ("auto merge", changed("merge-decision", ("/decision", "AUTO_MERGE"), ("/policy_paths_touched", []))),
        ("blocked by failed gate", changed("merge-decision", ("/decision", "BLOCKED"), ("/gates/1/status", "fail"))),
    ],
    "task-issue-map": [("empty map", changed("task-issue-map", ("/tasks", {})))],
    "sync-drift-report": [
        ("in sync", changed("sync-drift-report", ("/in_sync", True), ("/drift", []), ("/summary", {})))
    ],
    "gitea-plan": [("array body", changed("gitea-plan", ("/operations/0/request/body", [1, 2])))],
    "twelve-factor-scorecard": [("no commit", changed("twelve-factor-scorecard", ("/commit", None)))],
    "validation-report": [
        (
            "all ok",
            changed(
                "validation-report",
                ("/ok", True),
                ("/skills", [support.load_example("validation-report")["skills"][1]]),
            ),
        )
    ],
    "benchmark-case": [
        ("agentic", case("agentic")),
        ("trigger positive", case("trigger")),
        ("trigger negative", case("trigger", expect_skill=None, id="no-skill-for-weather")),
        (
            "deterministic with stdin and env",
            case(
                run={
                    "script": "scripts/sub/plan_dag.py",
                    "args": [],
                    "stdin_file": "evals/fixtures/tasks.md",
                    "env": {"LANG": "C"},
                }
            ),
        ),
        (
            "exists without value",
            case(expect={"exit_code": 0, "schema_valid": True, "assertions": [{"path": "/payload", "op": "exists"}]}),
        ),
        ("deterministic without judgments", case(judgments=_DELETE, schema_version=1)),
    ],
    "benchmark-result": [("agentic replay with uncertain judgment", result())],
    "benchmark-run": [("empty run", changed("benchmark-run", ("/results", []), ("/summary", {})))],
    "success-criteria": [
        (
            "minimal gate",
            changed(
                "success-criteria",
                ("/gates", [{"id": "g", "metric": "tests.failed", "op": "eq", "threshold": 0, "rationale": "r"}]),
            ),
        )
    ],
    "skill-score": [
        (
            "not ready",
            changed("skill-score", ("/release_ready", False), ("/gates/0/passed", False), ("/bench/agentic", None)),
        )
    ],
}

INVALID = {
    "envelope": [
        ("missing payload", changed("envelope", ("/payload", _DELETE))),
        ("extra member", changed("envelope", ("/extra", 1))),
        ("wrong schema urn", changed("envelope", ("/schema", "urn:skill-lab:schema:envelope:v2"))),
        ("ok with errors", changed("envelope", ("/errors", [{"code": "X", "message": "m"}]))),
        ("ok with null payload", changed("envelope", ("/payload", None))),
        ("lowercase error code", changed("envelope", ("/ok", False), ("/errors", [{"code": "bad", "message": "m"}]))),
        ("date without time", changed("envelope", ("/created_at", "2026-10-22"))),
        ("impossible date", changed("envelope", ("/created_at", "2026-02-30T00:00:00Z"))),
        ("message too long", changed("envelope", ("/warnings/0/message", "x" * 301))),
        ("bad kind schema", changed("envelope", ("/kind_schema", "urn:x"))),
        ("producer version not semver", changed("envelope", ("/producer/version", "1.0"))),
    ],
    "mutation-request": [
        ("no expected version", changed("mutation-request", ("/expected_version", _DELETE))),
        ("unknown role", changed("mutation-request", ("/actor_role", "admin"))),
        ("raw action", changed("mutation-request", ("/action", "move"))),
        ("issue zero", changed("mutation-request", ("/target/id", 0))),
        ("multi-line reason", changed("mutation-request", ("/reason", "a\nb"))),
        ("extra member", changed("mutation-request", ("/force", True))),
    ],
    "task-graph": [
        ("short task id", changed("task-graph", ("/tasks/0/id", "T1"))),
        ("story label", changed("task-graph", ("/tasks/2/story", "Story 1"))),
        ("absolute write domain", changed("task-graph", ("/tasks/0/write_domains", ["/etc/**"]))),
        ("parent write domain", changed("task-graph", ("/tasks/0/write_domains", ["src/../../x"]))),
        ("unknown edge kind", changed("task-graph", ("/edges/0/kind", "implicit"))),
        ("empty wave", changed("task-graph", ("/waves/0", []))),
        ("duplicate dependency", changed("task-graph", ("/tasks/4/depends_on", ["T003", "T003"]))),
    ],
    "spec-readiness": [
        ("ready while failing", changed("spec-readiness", ("/ready", True))),
        ("unknown status", changed("spec-readiness", ("/checks/0/status", "skipped"))),
        ("success criterion is not a requirement", changed("spec-readiness", ("/traceability/uncovered", ["SC-001"]))),
    ],
    "issue-contract": [
        ("no tasks", changed("issue-contract", ("/task_ids", []))),
        ("short ac id", changed("issue-contract", ("/acceptance_criteria/0/id", "AC-1"))),
        ("unknown risk", changed("issue-contract", ("/risk", "severe"))),
        ("hash dependency", changed("issue-contract", ("/dependencies", ["#177"]))),
        ("zero dependency", changed("issue-contract", ("/dependencies", [0]))),
        ("no verification", changed("issue-contract", ("/required_verification", []))),
        ("ownership incomplete", changed("issue-contract", ("/ownership/review", _DELETE))),
    ],
    "implementation-evidence": [
        ("unknown ac status", changed("implementation-evidence", ("/acceptance_criteria/AC-01", "done"))),
        ("md5 digest", changed("implementation-evidence", ("/checks/0/log_digest", "md5:abc"))),
        ("uppercase sha", changed("implementation-evidence", ("/base_commit", "ABCDEF1"))),
        ("quality-gate vocabulary", changed("implementation-evidence", ("/checks/0/status", "pass"))),
        ("migrations without present", changed("implementation-evidence", ("/migrations", {"paths": []}))),
    ],
    "review-verdict": [
        ("approve with blockers", changed("review-verdict", ("/result", "APPROVE"))),
        (
            "approve with unverified",
            changed(
                "review-verdict",
                ("/result", "APPROVE"),
                ("/blockers", []),
                ("/requirements", {"covered": 13, "failed": 0, "unverified": 1}),
            ),
        ),
        ("changes requested without reason", changed("review-verdict", ("/blockers", []), ("/requirements/failed", 0))),
        ("blocker without evidence", changed("review-verdict", ("/blockers/0/evidence", []))),
        ("unknown result", changed("review-verdict", ("/result", "REJECT"))),
    ],
    "quality-gate": [
        ("passed with applicable not_run", changed("quality-gate", ("/categories/e2e/status", "not_run"))),
        ("not applicable but pass", changed("quality-gate", ("/categories/dependency_scan/status", "pass"))),
        ("passed with blocking finding", changed("quality-gate", ("/review/blocking_findings", 1))),
        ("passed while not converged", changed("quality-gate", ("/spec/converged", False))),
        ("passed while behind base", changed("quality-gate", ("/branch/current_with_base", False))),
        (
            "passed with incomplete traceability",
            changed("quality-gate", ("/requirements_traceability/complete", False)),
        ),
        ("implicit applicability", changed("quality-gate", ("/categories/lint/applicable", _DELETE))),
    ],
    "session-checkpoint": [
        ("bad decision id", changed("session-checkpoint", ("/decisions/0/id", "D1"))),
        ("too many completed items", changed("session-checkpoint", ("/completed", ["step"] * 51))),
        ("multi-line goal", changed("session-checkpoint", ("/goal", "line one\nline two"))),
        ("unknown role", changed("session-checkpoint", ("/role", "admin"))),
        ("lease extra member", changed("session-checkpoint", ("/lease/holder", "x"))),
        ("branch with space", changed("session-checkpoint", ("/branch", "agent/pse/184 x"))),
    ],
    "normalized-event": [
        ("camel case event type", changed("normalized-event", ("/event_type", "ReviewApproved"))),
        ("unknown actor role", changed("normalized-event", ("/actor/role", "bot"))),
        ("no signature flag", changed("normalized-event", ("/signature_verified", _DELETE))),
        ("repository without owner", changed("normalized-event", ("/repository", "factory"))),
    ],
    "lease": [
        ("unknown status", changed("lease", ("/status", "revoked"))),
        ("version zero", changed("lease", ("/version", 0))),
        ("bad expiry", changed("lease", ("/expires_at", "in one hour"))),
        ("unknown resource type", changed("lease", ("/resource/type", "file"))),
    ],
    "transition-decision": [
        ("allowed with unmet precondition", changed("transition-decision", ("/preconditions/1/met", False))),
        ("display-name state", changed("transition-decision", ("/from_state", "In Progress"))),
        ("lowercase action", changed("transition-decision", ("/action", "move_to_review"))),
        ("unknown state", changed("transition-decision", ("/to_state", "MERGED"))),
    ],
    "merge-decision": [
        ("auto merge touching policy", changed("merge-decision", ("/decision", "AUTO_MERGE"))),
        (
            "auto merge high risk",
            changed(
                "merge-decision", ("/decision", "AUTO_MERGE"), ("/policy_paths_touched", []), ("/risk_class", "high")
            ),
        ),
        (
            "auto merge with not_run gate",
            changed(
                "merge-decision",
                ("/decision", "AUTO_MERGE"),
                ("/policy_paths_touched", []),
                ("/gates/2/status", "not_run"),
            ),
        ),
        (
            "auto merge without gates",
            changed("merge-decision", ("/decision", "AUTO_MERGE"), ("/policy_paths_touched", []), ("/gates", [])),
        ),
        ("human approval despite failed gate", changed("merge-decision", ("/gates/0/status", "fail"))),
        ("no reasons", changed("merge-decision", ("/reasons", []))),
    ],
    "task-issue-map": [
        ("issue zero", changed("task-issue-map", ("/tasks/T031/gitea_issue", 0))),
        ("unknown state", changed("task-issue-map", ("/tasks/T031/state", "merged"))),
        ("short blocker id", changed("task-issue-map", ("/tasks/T032/blocked_by", ["T31"]))),
        ("extra member in entry", changed("task-issue-map", ("/tasks/T031/url", "https://x"))),
    ],
    "sync-drift-report": [
        ("in sync with drift", changed("sync-drift-report", ("/in_sync", True))),
        ("out of sync without drift", changed("sync-drift-report", ("/drift", []))),
        ("unknown drift kind", changed("sync-drift-report", ("/drift/0/kind", "renamed"))),
        ("negative count", changed("sync-drift-report", ("/summary/missing_issue", -1))),
    ],
    "gitea-plan": [
        ("unknown method", changed("gitea-plan", ("/operations/0/request/method", "OPTIONS"))),
        ("path outside api", changed("gitea-plan", ("/operations/0/request/path", "/repos/acme/factory/issues"))),
        ("path traversal", changed("gitea-plan", ("/operations/0/request/path", "/api/v1/../admin/users"))),
        ("absolute url", changed("gitea-plan", ("/operations/0/request/path", "https://gitea.local/api/v1/repos"))),
        ("no body member", changed("gitea-plan", ("/operations/0/request/body", _DELETE))),
        ("camel case op", changed("gitea-plan", ("/operations/0/op", "CreateIssue"))),
    ],
    "twelve-factor-scorecard": [
        ("eleven factors", changed("twelve-factor-scorecard", ("/factors/11", _DELETE))),
        ("thirteen factors", changed("twelve-factor-scorecard", ("/factors/-", copy.deepcopy(FACTORS[0])))),
        (
            "out of order",
            changed(
                "twelve-factor-scorecard",
                ("/factors/0", copy.deepcopy(FACTORS[1])),
                ("/factors/1", copy.deepcopy(FACTORS[0])),
            ),
        ),
        ("score four", changed("twelve-factor-scorecard", ("/factors/0/score", 4))),
        ("wrong max total", changed("twelve-factor-scorecard", ("/max_total", 30))),
        ("unknown grade", changed("twelve-factor-scorecard", ("/grade", "A+"))),
        ("absolute evidence path", changed("twelve-factor-scorecard", ("/factors/0/evidence/0/path", "/etc/passwd"))),
    ],
    "validation-report": [
        ("ok report with failing skill", changed("validation-report", ("/ok", True))),
        ("ok skill with error finding", changed("validation-report", ("/skills/0/ok", True))),
        ("unknown severity", changed("validation-report", ("/skills/1/findings/0/severity", "info"))),
        ("unknown runtime", changed("validation-report", ("/runtime_profiles", ["vscode"]))),
        ("rule with spaces", changed("validation-report", ("/skills/0/findings/0/rule", "Frontmatter Name"))),
    ],
    "benchmark-case": [
        ("deterministic with prompt", case(prompt="x")),
        ("deterministic without run", case(run=_DELETE)),
        ("deterministic with judgments", case(judgments=[JUDGMENT_NOUL])),
        ("exit code five", case(expect={"exit_code": 5, "schema_valid": True, "assertions": []})),
        ("script outside scripts", case(run={"script": "../evil.py", "args": []})),
        ("non-python script", case(run={"script": "scripts/run.sh", "args": []})),
        (
            "unknown op",
            case(
                expect={
                    "exit_code": 1,
                    "schema_valid": True,
                    "assertions": [{"path": "/ok", "op": "approx", "value": 1}],
                }
            ),
        ),
        (
            "eq without value",
            case(expect={"exit_code": 1, "schema_valid": True, "assertions": [{"path": "/ok", "op": "eq"}]}),
        ),
        (
            "path is not a pointer",
            case(expect={"exit_code": 1, "schema_valid": True, "assertions": [{"path": "errors/0", "op": "exists"}]}),
        ),
        (
            "bad pointer escape",
            case(expect={"exit_code": 1, "schema_valid": True, "assertions": [{"path": "/a~2", "op": "exists"}]}),
        ),
        ("bad id", case(id="Rejects_Unexecuted")),
        ("unknown tier", case(tier="unit")),
        ("wrong schema urn", case(schema="urn:skill-lab:schema:benchmark-case:v2")),
        ("schema_version two", case(schema_version=2)),
        ("agentic without judgments", case("agentic", judgments=_DELETE)),
        ("agentic with run", case("agentic", run={"script": "scripts/x.py", "args": []})),
        (
            "agentic expect with exit code",
            case("agentic", expect={"exit_code": 0, "schema_valid": True, "assertions": []}),
        ),
        ("agentic bad output schema", case("agentic", output_schema="review-verdict")),
        ("trigger with expect", case("trigger", expect={"schema_valid": True, "assertions": []})),
        ("trigger without expect_skill", case("trigger", expect_skill=_DELETE)),
        ("trigger with uppercase skill", case("trigger", expect_skill="Review-Verifier")),
        ("noul with eq rule", judgment(JUDGMENT_NOUL, pass_if={"eq": "yes"})),
        ("noul threshold inside uncertain band", judgment(JUDGMENT_NOUL, pass_if={"gte": 0.3})),
        ("noul without false criterion", judgment(JUDGMENT_NOUL, criteria={"true": "yes"})),
        ("choice with gte rule", judgment(JUDGMENT_CHOICE, pass_if={"gte": 1})),
        ("score with one level", judgment(JUDGMENT_SCORE, criteria=["only"])),
        ("score with map criteria", judgment(JUDGMENT_SCORE, criteria={"a": "b"})),
        ("empty state_from", judgment(JUDGMENT_NOUL, state_from=[])),
        ("unknown state source", judgment(JUDGMENT_NOUL, state_from=["model"])),
        ("box judgments are not supported", judgment(JUDGMENT_NOUL, type="box")),
        ("numeric instructions", judgment(JUDGMENT_NOUL, instructions=5)),
    ],
    "benchmark-result": [
        (
            "pass with failed assertion",
            result(status="pass", judgments=[], assertions=[{"path": "/result", "op": "eq", "passed": False}]),
        ),
        ("pass with failed judgment", result(status="pass")),
        ("pass with invalid schema", result(status="pass", judgments=[], schema_valid=False)),
        ("skipped without reason", result(status="skipped", judgments=[], assertions=[])),
        ("error without error", result(status="error")),
        ("judgments without jev", result(jev_mode="off")),
        ("uncertain counted as pass", result(judgments=[dict(AGENTIC_RESULT["judgments"][0], **{"pass": True})])),
        (
            "uncertain not flagged",
            result(judgments=[{k: v for k, v in AGENTIC_RESULT["judgments"][0].items() if k != "needs_human"}]),
        ),
        ("unknown status", result(status="passed")),
        ("negative duration", result(duration_ms=-1)),
    ],
    "benchmark-run": [
        ("result without schema_version", changed("benchmark-run", ("/results/0/schema_version", _DELETE))),
        ("pass rate above one", changed("benchmark-run", ("/summary/deterministic/pass_rate", 1.5))),
        (
            "unknown tier summary",
            changed(
                "benchmark-run",
                ("/summary/unit", copy.deepcopy(support.load_example("benchmark-run")["summary"]["deterministic"])),
            ),
        ),
        ("result breaks its invariant", changed("benchmark-run", ("/results/0/assertions/0/passed", False))),
        ("skipped result without reason", changed("benchmark-run", ("/results/1/skip_reason", _DELETE))),
    ],
    "success-criteria": [
        ("no gates", changed("success-criteria", ("/gates", []))),
        ("unknown op", changed("success-criteria", ("/gates/0/op", "approx"))),
        ("metric with spaces", changed("success-criteria", ("/gates/0/metric", "Bench Pass"))),
        ("unknown tier", changed("success-criteria", ("/gates/0/tier", "unit"))),
        ("no rationale", changed("success-criteria", ("/gates/0/rationale", _DELETE))),
    ],
    "skill-score": [
        ("ready with failed tests", changed("skill-score", ("/tests/failed", 1))),
        ("ready with failed gate", changed("skill-score", ("/gates/0/passed", False))),
        ("unmeasured gate passed", changed("skill-score", ("/gates/3/actual", None))),
        ("skipped gate without reason", changed("skill-score", ("/gates/1/reason", _DELETE))),
        ("skipped gate passed", changed("skill-score", ("/gates/1/passed", True), ("/gates/1/actual", 0.9))),
        ("score above 100", changed("skill-score", ("/static/score", 101))),
        ("missing tier", changed("skill-score", ("/bench/trigger", _DELETE))),
    ],
}


class TestCatalog(unittest.TestCase):
    def test_catalog_has_the_23_documented_contracts(self):
        names = support.catalog_names()
        self.assertEqual(len(names), 23)
        self.assertEqual(len(set(names)), 23)

    def test_every_catalog_contract_has_a_schema(self):
        self.assertLessEqual(set(support.catalog_names()), set(support.schema_files()))

    def test_every_schema_has_an_example(self):
        examples = {
            f[: -len(".v1.example.json")] for f in os.listdir(support.EXAMPLE_DIR) if f.endswith(".v1.example.json")
        }
        self.assertEqual(examples, set(support.schema_files()))

    def test_readme_lists_every_contract(self):
        """Every schema file, including ones added by later specs, is documented in the README table."""
        with open(os.path.join(support.LAB_ROOT, "contracts", "README.md"), "r", encoding="utf-8") as handle:
            readme = handle.read()
        for name in support.schema_files():
            with self.subTest(name=name):
                self.assertRegex(readme, r"\| `%s` \|" % re.escape(name))

    def test_crafted_cases_cover_every_contract(self):
        self.assertEqual(set(INVALID), set(support.catalog_names()))
        self.assertEqual(set(VALID), set(support.catalog_names()))


class TestSchemaFiles(unittest.TestCase):
    def schemas(self):
        for name, path in support.schema_files().items():
            yield name, support.load_json(path)

    def test_identity_and_annotations(self):
        for name, schema in self.schemas():
            with self.subTest(name=name):
                self.assertEqual(schema["$schema"], DRAFT)
                self.assertEqual(schema["$id"], "urn:skill-lab:schema:%s:v1" % name)
                self.assertTrue(schema["title"].strip())
                self.assertGreater(len(schema["description"]), 40)
                self.assertEqual(schema["type"], "object")

    def test_only_the_keyword_subset(self):
        for name, schema in self.schemas():
            with self.subTest(name=name):
                self.assertEqual(unsupported_keywords(schema), [])

    def test_every_object_schema_is_explicitly_closed(self):
        for name, schema in self.schemas():
            for pointer, sub in walk(schema):
                types = sub.get("type")
                if types != "object" and not (isinstance(types, list) and "object" in types):
                    continue
                with self.subTest(name=name, pointer=pointer):
                    self.assertIn("additionalProperties", sub, "object schemas must declare additionalProperties")
                    if sub["additionalProperties"] is True:
                        self.assertIn((name, pointer), OPEN_OBJECTS, "open objects must be on the allowlist")
                    else:
                        self.assertNotEqual(
                            sub["additionalProperties"], {}, "an empty schema is an open object in disguise"
                        )

    def test_open_object_allowlist_is_current(self):
        found = set()
        for name, schema in self.schemas():
            for pointer, sub in walk(schema):
                if sub.get("additionalProperties") is True:
                    found.add((name, pointer))
        self.assertEqual(found, OPEN_OBJECTS)

    def test_top_level_is_closed(self):
        for name, schema in self.schemas():
            with self.subTest(name=name):
                self.assertIs(schema["additionalProperties"], False)

    def test_schema_version_rules(self):
        for name, schema in self.schemas():
            with self.subTest(name=name):
                if name in DOCUMENT_CONTRACTS:
                    self.assertIn("schema", schema["required"])
                    self.assertEqual(schema["properties"]["schema"], {"const": "urn:skill-lab:schema:%s:v1" % name})
                else:
                    self.assertIn("schema_version", schema["required"])
                    self.assertEqual(schema["properties"]["schema_version"]["const"], 1)
                    self.assertEqual(schema["properties"]["schema_version"]["type"], "integer")

    def test_refs_resolve_and_defs_are_used(self):
        for name, schema in self.schemas():
            refs = set()
            for _, sub in walk(schema):
                if "$ref" in sub:
                    refs.add(sub["$ref"])
            with self.subTest(name=name):
                for ref in refs:
                    self.assertTrue(ref.startswith("#/$defs/"), ref)
                    jsonpointer.resolve(schema, ref[1:])
                self.assertEqual(
                    {"#/$defs/" + key for key in schema.get("$defs", {})}, refs, "every $def is referenced"
                )

    def test_benchmark_run_embeds_benchmark_result(self):
        result_schema = support.load_schema("benchmark-result")
        run_schema = support.load_schema("benchmark-run")
        embedded = {k: v for k, v in run_schema["$defs"]["benchmark_result"].items() if k != "description"}
        expected = {
            k: v for k, v in result_schema.items() if k not in ("$schema", "$id", "title", "description", "$defs")
        }
        self.assertEqual(embedded, expected)
        for key, definition in result_schema["$defs"].items():
            with self.subTest(definition=key):
                self.assertEqual(run_schema["$defs"][key], definition)

    def test_tier_summary_is_shared(self):
        self.assertEqual(
            support.load_schema("benchmark-run")["$defs"]["tier_summary"],
            support.load_schema("skill-score")["$defs"]["tier_summary"],
        )

    def test_common_definitions_agree_across_files(self):
        seen = {}
        for name, schema in self.schemas():
            for key, definition in schema.get("$defs", {}).items():
                if key in seen:
                    with self.subTest(definition=key, first=seen[key][0], second=name):
                        self.assertEqual(definition, seen[key][1])
                else:
                    seen[key] = (name, definition)


class TestExamples(unittest.TestCase):
    def test_every_example_validates(self):
        for name in support.schema_files():
            with self.subTest(name=name):
                self.assertEqual(validate(support.load_example(name), support.load_schema(name)), [])

    def test_envelope_example_wraps_a_valid_review_verdict(self):
        env = support.load_example("envelope")
        self.assertEqual(env["kind"], "review-verdict")
        self.assertEqual(validate(env["payload"], support.load_schema("review-verdict")), [])

    def test_benchmark_case_example_is_the_conventions_example(self):
        with open(support.CONVENTIONS_PATH, "r", encoding="utf-8") as handle:
            text = handle.read()
        block = text.split("## 5. Evals and benchmarks", 1)[1].split("```json", 1)[1].split("```", 1)[0]
        self.assertEqual(json.loads(block), support.load_example("benchmark-case"))


FAMILIES = {
    "envelope": ["envelope"],
    "coordination": [
        "mutation-request",
        "lease",
        "normalized-event",
        "transition-decision",
        "merge-decision",
        "session-checkpoint",
    ],
    "planning": ["task-graph", "spec-readiness", "issue-contract", "task-issue-map", "sync-drift-report", "gitea-plan"],
    "evidence": ["implementation-evidence", "review-verdict", "quality-gate"],
    "audit": ["twelve-factor-scorecard", "validation-report"],
    "benchmark": ["benchmark-case", "benchmark-result", "benchmark-run", "success-criteria", "skill-score"],
}


class TestContractFamilies(unittest.TestCase):
    """Each family: examples validate, crafted valid variants pass, every crafted violation is rejected."""

    def check_family(self, family):
        for name in FAMILIES[family]:
            schema = support.load_schema(name)
            with self.subTest(name=name, case="example"):
                self.assertEqual(validate(support.load_example(name), schema), [])
            for label, instance in VALID[name]:
                with self.subTest(name=name, case=label):
                    self.assertEqual(validate(instance, schema), [])
            for label, instance in INVALID[name]:
                with self.subTest(name=name, case=label):
                    self.assertNotEqual(validate(instance, schema), [], "must be rejected")

    def test_families_partition_the_catalog(self):
        names = [name for members in FAMILIES.values() for name in members]
        self.assertEqual(sorted(names), sorted(support.catalog_names()))

    def test_envelope_family(self):
        self.check_family("envelope")

    def test_coordination_family(self):
        self.check_family("coordination")

    def test_planning_family(self):
        self.check_family("planning")

    def test_evidence_family(self):
        self.check_family("evidence")

    def test_audit_family(self):
        self.check_family("audit")

    def test_benchmark_family(self):
        self.check_family("benchmark")


class TestRobustness(unittest.TestCase):
    def test_mini_never_raises_on_contract_schemas(self):
        junk = [None, 0, "x", [], {}, {"schema_version": 1}, [{}], {"schema_version": True}]
        for name in support.schema_files():
            schema = support.load_schema(name)
            for instance in junk:
                with self.subTest(name=name, instance=instance):
                    try:
                        self.assertNotEqual(validate(instance, schema), [])
                    except SchemaError as exc:  # pragma: no cover - would be a schema bug
                        self.fail("schema error: %s" % exc)


@unittest.skipIf(reference is None, "third-party jsonschema not installed; differential test skipped")
class TestDifferential(unittest.TestCase):
    """jsonschema_mini must agree with the reference implementation on validity."""

    def reference_validator(self, schema):
        checker = reference.Draft202012Validator.FORMAT_CHECKER
        return reference.Draft202012Validator(schema, format_checker=checker)

    def instances(self):
        for name in support.schema_files():
            yield name, "example", support.load_example(name)
            for label, instance in VALID.get(name, []):
                yield name, "valid: " + label, instance
            for label, instance in INVALID.get(name, []):
                yield name, "invalid: " + label, instance

    def test_reference_checks_date_time(self):
        checker = reference.Draft202012Validator.FORMAT_CHECKER
        if "date-time" not in checker.checkers:
            self.skipTest("reference date-time checking needs rfc3339-validator; format cases compare as annotations")
        self.assertFalse(self.reference_validator({"format": "date-time"}).is_valid("2026-02-30T00:00:00Z"))

    def test_schemas_are_valid_draft_2020_12(self):
        for name, path in support.schema_files().items():
            with self.subTest(name=name):
                reference.Draft202012Validator.check_schema(support.load_json(path))

    def test_validity_agrees_on_every_instance(self):
        formats_checked = "date-time" in reference.Draft202012Validator.FORMAT_CHECKER.checkers
        compared = 0
        for name, label, instance in self.instances():
            if not formats_checked and label in (
                "invalid: date without time",
                "invalid: impossible date",
                "invalid: bad expiry",
            ):
                continue
            schema = support.load_schema(name)
            with self.subTest(name=name, case=label):
                mine = validate(instance, schema) == []
                theirs = self.reference_validator(schema).is_valid(instance)
                self.assertEqual(mine, theirs)
                compared += 1
        self.assertGreater(compared, 150)

    def test_keyword_level_agreement(self):
        cases = [
            ({"type": "integer"}, [1, 1.0, 1.5, True, "1", None]),
            ({"type": "number"}, [1, 1.5, True, "1"]),
            ({"uniqueItems": True}, [[1, 1.0], [1, True], [0, False], [{"a": 1}, {"a": 1.0}], [[1], [True]]]),
            ({"const": {"a": [1, 2.0]}}, [{"a": [1.0, 2]}, {"a": [2, 1]}, {"a": [True, 2]}]),
            ({"enum": [1, "1", None]}, [1.0, "1", None, True, False, 0]),
            ({"minLength": 2, "maxLength": 3}, ["\U0001f600\U0001f600", "a", "abcd", 5]),
            ({"pattern": "^T[0-9]{3,}$"}, ["T001", "T01", "xT001", 7]),
            ({"prefixItems": [{"type": "string"}], "items": False}, [["a"], ["a", "b"], [], [1]]),
            ({"oneOf": [{"type": "integer"}, {"minimum": 2}]}, [1, 2.5, 3, "x"]),
            ({"not": {"required": ["a"]}}, [{"a": 1}, {"b": 1}, []]),
            ({"exclusiveMinimum": 0.35, "maximum": 1}, [0.35, 0.36, 1, 1.01, True]),
            (
                {"format": "date-time"},
                [
                    "2026-10-22T08:00:00Z",
                    "2026-10-22t08:00:00z",
                    "2026-10-22T08:00:00+05:30",
                    "2026-10-22T08:00:00",
                    "2026-13-01T00:00:00Z",
                    "2024-02-29T00:00:00Z",
                    "2026-02-29T00:00:00Z",
                    "2026-10-22T08:00:00.5Z",
                    12,
                ],
            ),
        ]
        formats_checked = "date-time" in reference.Draft202012Validator.FORMAT_CHECKER.checkers
        for schema, instances in cases:
            if "format" in schema and not formats_checked:
                continue
            for instance in instances:
                with self.subTest(schema=schema, instance=instance):
                    self.assertEqual(
                        validate(instance, schema) == [], self.reference_validator(schema).is_valid(instance)
                    )


if __name__ == "__main__":
    unittest.main()
