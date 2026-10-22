"""SPEC-104 gates: metrics, not_run vs skipped, criteria merging, release readiness end to end."""

from __future__ import annotations

import json
import os
import shutil
import tempfile
import unittest

from tests import skillkit_support as support
from tests.test_bench_fakes import NOW, ScratchRepo, captured_stdout
from tests.test_score_static import GOOD_DESCRIPTION
from _skillkit import EXIT_FAIL, EXIT_OK, schemas
from _skillkit.envelope import ScriptError
from _skillkit.jsonschema_mini import validate
from lab import bench, score

DEFAULTS = support.load_json(score.DEFAULTS_PATH)


def result(tier, status, schema_valid=None, judgments=(), skip_reason=None):
    item = {"tier": tier, "status": status, "schema_valid": schema_valid, "judgments": list(judgments), "skill": "s"}
    if status == "skipped":
        item["skip_reason"] = skip_reason or "LIVE_PREREQ_MISSING: no --runtime given"
    return item


def measured_run():
    return score.Measured({"run_id": "run-1"}, "")


class TestDefaults(unittest.TestCase):
    def test_defaults_file_is_valid_and_matches_spec(self):
        self.assertEqual(validate(DEFAULTS, score.defaults_schema()), [])
        gates = {
            gate["metric"]: (gate["op"], gate["threshold"], gate.get("optional_when_unavailable", False))
            for gate in DEFAULTS["gates"]
        }
        self.assertEqual(
            gates,
            {
                "static.score": ("gte", 90, False),
                "tests.pass_rate": ("eq", 1.0, False),
                "bench.deterministic.pass_rate": ("eq", 1.0, False),
                "bench.deterministic.schema_valid_rate": ("eq", 1.0, False),
                "bench.agentic.schema_valid_rate": ("gte", 0.95, True),
                "bench.agentic.pass_rate": ("gte", 0.8, True),
                "bench.trigger.accuracy": ("gte", 0.9, True),
                "bench.jev.uncertain_rate": ("lte", 0.1, True),
            },
        )

    def test_optional_gate_needs_a_reason(self):
        broken = json.loads(json.dumps(DEFAULTS))
        del broken["gates"][4]["optional_reason"]
        self.assertTrue(validate(broken, score.defaults_schema()))

    def test_every_default_metric_is_known(self):
        self.assertTrue(all(gate["metric"] in score.KNOWN_METRICS for gate in DEFAULTS["gates"]))


class TestEvaluateGate(unittest.TestCase):
    GATE = {"id": "g", "metric": "bench.agentic.pass_rate", "op": "gte", "threshold": 0.8}
    OPTIONAL = dict(GATE, optional_when_unavailable=True, optional_reason="needs a runtime")

    def evaluate(self, gate, actual, strict=False):
        return score.evaluate_gate(gate, {gate["metric"]: actual}, {gate["metric"]: "agentic skipped"}, strict=strict)

    def test_pass_and_fail(self):
        self.assertEqual(self.evaluate(self.GATE, 0.8)["passed"], True)
        failed = self.evaluate(self.GATE, 0.5)
        self.assertEqual((failed["passed"], failed["reason"]), (False, "fail: 0.5 gte 0.8 does not hold"))
        self.assertEqual(score.gate_status(failed), "fail")

    def test_unmeasured_mandatory_gate_is_not_run(self):
        gate = self.evaluate(self.GATE, None)
        self.assertEqual((gate["passed"], gate["skipped"], score.gate_status(gate)), (False, False, "not_run"))
        self.assertEqual(gate["reason"], "not_run: agentic skipped")

    def test_unmeasured_optional_gate_is_skipped_unless_strict(self):
        gate = self.evaluate(self.OPTIONAL, None)
        self.assertEqual((gate["passed"], gate["skipped"], score.gate_status(gate)), (False, True, "skipped"))
        self.assertIn("optional when unavailable: needs a runtime", gate["reason"])
        self.assertEqual(score.gate_status(self.evaluate(self.OPTIONAL, None, strict=True)), "not_run")
        self.assertEqual(
            score.gate_status(self.evaluate(self.OPTIONAL, 0.1)), "fail", "optional never hides a measured failure"
        )

    def test_eq_tolerates_float_noise(self):
        gate = {"id": "e", "metric": "tests.pass_rate", "op": "eq", "threshold": 1.0}
        self.assertTrue(score.evaluate_gate(gate, {"tests.pass_rate": 0.1 * 10}, {}, strict=False)["passed"])


class TestMergeGates(unittest.TestCase):
    def test_replace_by_id_then_metric_and_append_new(self):
        overrides = [
            {
                "id": "agentic-quality",
                "metric": "bench.agentic.pass_rate",
                "op": "gte",
                "threshold": 0.67,
                "rationale": "r",
            },
            {
                "id": "trigger-floor",
                "metric": "bench.trigger.accuracy",
                "op": "gte",
                "threshold": 0.83,
                "rationale": "r",
            },
            {"id": "static-clean", "metric": "static.errors", "op": "eq", "threshold": 0, "rationale": "r"},
        ]
        merged = {gate["id"]: gate for gate in score.merge_gates(DEFAULTS["gates"], overrides)}
        self.assertEqual(merged["agentic-quality"]["threshold"], 0.67)
        self.assertTrue(merged["agentic-quality"]["optional_when_unavailable"])
        self.assertNotIn("trigger-routing", merged)
        self.assertTrue(merged["trigger-floor"]["optional_when_unavailable"], "matched by metric, keeps optionality")
        self.assertNotIn("optional_when_unavailable", merged["static-clean"], "new gates are mandatory")
        self.assertEqual(len(merged), len(DEFAULTS["gates"]) + 1)

    def test_duplicate_ids_are_refused(self):
        gate = {"id": "x", "metric": "static.errors", "op": "eq", "threshold": 0, "rationale": "r"}
        with self.assertRaises(ScriptError):
            score.merge_gates([], [gate, gate])


class TestMetrics(unittest.TestCase):
    def collect(self, results, tests=None, validation=(0, 1)):
        tests = tests or score.Measured(score.TestCounts(5, 5, 0, 0, 0), "")
        return score.collect_metrics(
            97.0, {"errors": 0, "warnings": 1}, score.Measured(validation, ""), tests, results, measured_run()
        )

    def test_rates_from_results(self):
        judged = [{"band": "pass"}, {"band": "uncertain"}, {"band": "pass"}, {"band": "fail"}]
        results = [
            result("deterministic", "pass", True),
            result("deterministic", "fail", False),
            result("deterministic", "pass", None),
            result("agentic", "pass", True, judged[:2]),
            result("agentic", "fail", True, judged[2:]),
            result("trigger", "pass"),
            result("trigger", "fail"),
            result("trigger", "skipped"),
        ]
        values, _ = self.collect(results)
        self.assertEqual(values["bench.deterministic.pass_rate"], 2 / 3)
        self.assertEqual(values["bench.deterministic.schema_valid_rate"], 0.5)
        self.assertEqual(values["bench.agentic.schema_valid_rate"], 1.0)
        self.assertEqual(values["bench.trigger.accuracy"], 0.5)
        self.assertEqual(values["bench.trigger.skipped"], 1)
        self.assertEqual(values["bench.jev.uncertain_rate"], 0.25)
        self.assertEqual(values["bench.jev.judgments"], 4)
        self.assertEqual((values["static.score"], values["static.warnings"]), (97.0, 1))
        self.assertEqual(values["tests.pass_rate"], 1.0)

    def test_skipped_tiers_and_missing_inputs_are_unmeasured_with_reasons(self):
        values, reasons = self.collect(
            [result("deterministic", "pass", True), result("agentic", "skipped")],
            tests=score.Measured(None, "the skill has no tests/test_*.py"),
            validation=None,
        )
        self.assertIsNone(values["bench.agentic.pass_rate"])
        self.assertIn("all 1 agentic cases were skipped: LIVE_PREREQ_MISSING", reasons["bench.agentic.pass_rate"])
        self.assertIsNone(values["bench.jev.uncertain_rate"])
        self.assertIsNone(values["bench.trigger.accuracy"])
        self.assertIn("has no trigger results", reasons["bench.trigger.accuracy"])
        self.assertIsNone(values["tests.pass_rate"])
        self.assertEqual(reasons["tests.failed"], "the skill has no tests/test_*.py")
        self.assertIsNone(values["static.score"])
        self.assertIn("partial score 97", reasons["static.score"])


class TestScoreEndToEnd(unittest.TestCase):
    def setUp(self):
        self.repo = ScratchRepo()
        self.addCleanup(self.repo.close)
        self.repo.add_skill("demo-skill", GOOD_DESCRIPTION)
        self.repo.add_echo_script("demo-skill")
        self.repo.write("skills/demo-skill/evals/fixtures/decision.json", support.load_example("transition-decision"))
        self.repo.add_case(
            "demo-skill",
            {
                "id": "det-pass",
                "tier": "deterministic",
                "description": "Echo succeeds.",
                "run": {"script": "scripts/echo.py", "args": ["--input", "evals/fixtures/decision.json"]},
                "expect": {"exit_code": 0, "schema_valid": True, "assertions": []},
            },
        )
        self.repo.add_case(
            "demo-skill",
            {"id": "route", "tier": "trigger", "description": "Routes.", "query": "echo", "expect_skill": "demo-skill"},
        )
        self.repo.write(
            "skills/demo-skill/tests/test_ok.py",
            "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n",
        )
        report = support.load_example("validation-report")
        report["skills"] = [{"name": "demo-skill", "ok": True, "findings": []}]
        report["ok"], report["summary"] = True, {"errors": 0, "warnings": 0}
        self.validation = self.repo.write("validation.json", report)
        bench.run(["--repo", self.repo.root, "--now", NOW, "--tier", "all"], environ={})

    def score(self, *extra):
        argv = [
            "--repo",
            self.repo.root,
            "--skill",
            "demo-skill",
            "--now",
            NOW,
            "--validation",
            self.validation,
        ] + list(extra)
        with captured_stdout() as raw:
            code = score.main(argv)
        document = json.loads(raw.getvalue().decode("utf-8"))
        self.assertEqual(schemas.validate_envelope(document, exit_code=code, search_dirs=[support.SCHEMA_DIR]), [])
        return code, document

    def test_offline_release_ready_lists_skipped_gates(self):
        code, document = self.score()
        payload = document["payload"]
        statuses = {gate["id"]: score.gate_status(gate) for gate in payload["gates"]}
        self.assertEqual(code, EXIT_OK, document)
        self.assertTrue(payload["release_ready"])
        self.assertEqual(
            statuses,
            {
                "static-score": "pass",
                "unit-tests": "pass",
                "deterministic-all-pass": "pass",
                "deterministic-schema-valid": "pass",
                "agentic-schema-valid": "skipped",
                "agentic-quality": "skipped",
                "trigger-routing": "skipped",
                "jev-uncertain": "skipped",
            },
        )
        self.assertEqual(payload["static"], {"score": 100.0, "findings": {"errors": 0, "warnings": 0}})
        self.assertEqual(payload["tests"], {"passed": 1, "failed": 0, "skipped": 0})
        self.assertIsNone(payload["bench"]["agentic"])
        self.assertEqual(payload["bench"]["trigger"]["skipped"], 1)
        codes = [warning["code"] for warning in document["warnings"]]
        self.assertEqual(codes.count("GATE_SKIPPED"), 4)
        self.assertIn("RELEASE_READY_OFFLINE", codes)
        self.assertEqual(payload["version"], "0.1.0")

    def test_strict_mode_turns_skips_into_not_run(self):
        code, document = self.score("--strict")
        self.assertEqual(code, EXIT_FAIL)
        self.assertFalse(document["payload"]["release_ready"])
        self.assertEqual(document["errors"][0]["code"], "NOT_RELEASE_READY")
        self.assertIn("not_run: agentic-schema-valid", document["errors"][0]["message"])

    def test_skill_criteria_add_mandatory_gates(self):
        self.repo.write(
            "skill-lab/benchmarks/criteria/demo-skill.json",
            {
                "schema_version": 1,
                "skill": "demo-skill",
                "gates": [
                    {
                        "id": "live-agentic",
                        "metric": "bench.agentic.cases",
                        "op": "gte",
                        "threshold": 2,
                        "rationale": "Needs live runs.",
                    }
                ],
            },
        )
        code, document = self.score()
        gate = next(g for g in document["payload"]["gates"] if g["id"] == "live-agentic")
        self.assertEqual((code, score.gate_status(gate)), (EXIT_FAIL, "not_run"))

    def test_failing_unit_tests_block_release(self):
        self.repo.write(
            "skills/demo-skill/tests/test_bad.py",
            "import unittest\n\nclass B(unittest.TestCase):\n"
            "    def test_bad(self):\n        raise RuntimeError('x')\n",
        )
        code, document = self.score()
        self.assertEqual(code, EXIT_FAIL)
        self.assertEqual(document["payload"]["tests"], {"passed": 1, "failed": 1, "skipped": 0})

    def test_no_tests_flag_means_not_run(self):
        code, document = self.score("--no-tests")
        gate = next(g for g in document["payload"]["gates"] if g["id"] == "unit-tests")
        self.assertEqual((code, gate["reason"]), (EXIT_FAIL, "not_run: unit tests not run (--no-tests)"))

    def test_explicit_run_and_unknown_metric(self):
        run_dir = os.path.join(self.repo.root, "skill-lab", "benchmarks", "runs")
        explicit = os.path.join(run_dir, os.listdir(run_dir)[0])
        code, document = self.score("--run", explicit)
        self.assertEqual(code, EXIT_OK)
        self.assertTrue(document["payload"]["run_id"].startswith("run-20261022T080000Z-"))
        with tempfile.TemporaryDirectory() as tmp:
            bad = os.path.join(tmp, "c.json")
            with open(bad, "w", encoding="utf-8") as handle:
                json.dump(
                    {
                        "schema_version": 1,
                        "skill": "demo-skill",
                        "gates": [{"id": "x", "metric": "made.up", "op": "eq", "threshold": 0, "rationale": "r"}],
                    },
                    handle,
                )
            code, document = self.score("--criteria", bad)
        self.assertEqual((code, document["errors"][0]["code"]), (2, "UNKNOWN_METRIC"))

    def test_skill_must_be_a_name(self):
        with captured_stdout():
            code = score.main(["--repo", self.repo.root, "--skill", "../skills/demo-skill", "--no-tests"])
        self.assertEqual(code, 2)

    def test_no_run_found(self):
        shutil.rmtree(os.path.join(self.repo.root, "skill-lab", "benchmarks", "runs"))
        code, document = self.score()
        gate = next(g for g in document["payload"]["gates"] if g["id"] == "deterministic-all-pass")
        self.assertEqual(code, EXIT_FAIL)
        self.assertTrue(gate["reason"].startswith("not_run: no benchmark run in skill-lab/benchmarks/runs"))
        self.assertIsNone(document["payload"]["run_id"])


if __name__ == "__main__":
    unittest.main()
