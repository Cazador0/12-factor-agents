"""SPEC-102 graders on synthetic cases: deterministic envelopes, model output, Jev bands, summaries."""

from __future__ import annotations

import json
import unittest

from tests import skillkit_support as support
from lab import graders, jev

SCHEMA_DIRS = [support.SCHEMA_DIR]


def envelope_text(exit_code=0, payload=None, **changes):
    document = {
        "schema": "urn:skill-lab:schema:envelope:v1",
        "kind": "transition-decision",
        "kind_schema": "urn:skill-lab:schema:transition-decision:v1",
        "ok": exit_code == 0,
        "producer": {"skill": "kanban-state-machine", "script": "transition.py", "version": "0.1.0"},
        "created_at": "2026-10-22T08:00:00Z",
        "idempotency_key": None,
        "payload": support.load_example("transition-decision") if payload is None else payload,
        "errors": [] if exit_code == 0 else [{"code": "DENIED", "message": "no", "path": None}],
        "warnings": [],
    }
    document.update(changes)
    return json.dumps(document)


def expect(exit_code=0, schema_valid=True, assertions=()):
    return {"exit_code": exit_code, "schema_valid": schema_valid, "assertions": list(assertions)}


class TestDeterministic(unittest.TestCase):
    def grade(self, expectation, exit_code, stdout):
        return graders.grade_deterministic(expectation, exit_code, stdout, schema_dirs=SCHEMA_DIRS)

    def test_pass(self):
        allowed = support.load_example("transition-decision")["allowed"]
        grade = self.grade(
            expect(assertions=[{"path": "/payload/allowed", "op": "eq", "value": allowed}]), 0, envelope_text()
        )
        self.assertEqual((grade.status, grade.schema_valid), ("pass", True))
        self.assertEqual(
            grade.assertions, [{"path": "/payload/allowed", "op": "eq", "passed": True, "actual": allowed}]
        )

    def test_exit_code_mismatch_fails(self):
        grade = self.grade(expect(exit_code=1), 0, envelope_text())
        self.assertEqual(grade.status, "fail")
        self.assertIn("exit code 0, expected 1", grade.notes)

    def test_invalid_payload_fails_schema(self):
        grade = self.grade(expect(), 0, envelope_text(payload={"schema_version": 1}))
        self.assertEqual((grade.status, grade.schema_valid), ("fail", False))
        self.assertTrue(any(note.startswith("envelope invalid: /payload") for note in grade.notes))

    def test_ok_must_match_exit_code(self):
        grade = self.grade(expect(exit_code=1), 1, envelope_text(exit_code=0))
        self.assertFalse(grade.schema_valid)
        self.assertTrue(any("ok is true but the exit code is 1" in note for note in grade.notes))

    def test_non_json_and_empty_stdout(self):
        for stdout in ("Traceback (most recent call last):", "", '{"a": 1}\n{"b": 2}'):
            with self.subTest(stdout=stdout):
                grade = self.grade(expect(assertions=[{"path": "/ok", "op": "exists"}]), 0, stdout)
                self.assertEqual((grade.status, grade.schema_valid), ("fail", False))

    def test_unknown_kind_schema_is_invalid_not_a_crash(self):
        text = envelope_text(kind="no-such-thing", kind_schema="urn:skill-lab:schema:no-such-thing:v1")
        self.assertFalse(self.grade(expect(), 0, text).schema_valid)

    def test_schema_validity_not_required_is_recorded_as_null(self):
        grade = self.grade(expect(exit_code=2, schema_valid=False), 2, "usage: x")
        self.assertEqual((grade.status, grade.schema_valid), ("pass", None))

    def test_malformed_assertion_is_an_error(self):
        grade = self.grade(expect(assertions=[{"path": "/ok", "op": "regex", "value": "("}]), 0, envelope_text())
        self.assertEqual(grade.status, "error")
        self.assertEqual(grade.error["code"], "ASSERTION_INVALID")


class TestModelOutput(unittest.TestCase):
    SCHEMA = {"type": "object", "required": ["n"], "properties": {"n": {"type": "integer"}}}

    def test_valid_output_with_assertions(self):
        grade = graders.grade_output(
            {"schema_valid": True, "assertions": [{"path": "/n", "op": "gte", "value": 2}]}, {"n": 3}, self.SCHEMA
        )
        self.assertEqual((grade.status, grade.schema_valid), ("pass", True))

    def test_invalid_or_missing_output(self):
        bad = graders.grade_output({"schema_valid": True, "assertions": []}, {"n": "x"}, self.SCHEMA)
        self.assertEqual((bad.status, bad.schema_valid), ("fail", False))
        self.assertIn("output invalid (1 issues)", bad.notes[0])
        none = graders.grade_output(
            {"schema_valid": True, "assertions": [{"path": "/n", "op": "exists"}]}, None, self.SCHEMA
        )
        self.assertEqual((none.status, none.schema_valid), ("fail", False))
        self.assertIn("reply contains no JSON document", none.notes)

    def test_large_actual_values_are_summarised(self):
        grade = graders.grade_output(
            {
                "schema_valid": False,
                "assertions": [{"path": "/items", "op": "len_gte", "value": 1}, {"path": "", "op": "exists"}],
            },
            {"items": list(range(500))},
            self.SCHEMA,
        )
        self.assertEqual(grade.assertions[0]["actual"], 500)
        self.assertEqual(grade.assertions[1]["actual"], "<object with 1 keys>")


class TestJudgments(unittest.TestCase):
    def test_noul_bands(self):
        self.assertEqual(graders.noul_band(0.8, 0.8), "pass")
        self.assertEqual(graders.noul_band(0.79, 0.8), "uncertain")
        self.assertEqual(graders.noul_band(0.35, 0.8), "uncertain")
        self.assertEqual(graders.noul_band(0.3499, 0.8), "fail")

    def test_uncertain_noul_fails_and_needs_a_human(self):
        judgment = {"id": "grounded", "type": "noul", "pass_if": {"gte": 0.8}}
        result = graders.grade_judgment(judgment, jev.NoulAnswer(0.5), "r1")
        self.assertEqual(
            result,
            {
                "id": "grounded",
                "type": "noul",
                "request_id": "r1",
                "value": 0.5,
                "pass": False,
                "band": "uncertain",
                "needs_human": True,
            },
        )

    def test_score_and_choice_rules(self):
        score = jev.ScoreAnswer(1.6, 0.7, {}, {})
        self.assertTrue(
            graders.grade_judgment({"id": "s", "type": "score", "pass_if": {"gte": 1.5}}, score, None)["pass"]
        )
        self.assertFalse(
            graders.grade_judgment({"id": "s", "type": "score", "pass_if": {"gte": 1.7}}, score, None)["pass"]
        )
        choice = jev.ChoiceAnswer("calm", 0.9, {"calm": 0.9, "angry": 0.1})
        passed = graders.grade_judgment({"id": "c", "type": "choice", "pass_if": {"eq": "calm"}}, choice, None)
        self.assertEqual(
            (passed["pass"], passed["band"], passed["confidence"], passed["needs_human"]), (True, "pass", 0.9, False)
        )
        self.assertEqual(
            graders.grade_judgment({"id": "c", "type": "choice", "pass_if": {"eq": "angry"}}, choice, None)["band"],
            "fail",
        )

    def test_routing_helpers(self):
        self.assertIsNone(graders.routed_skill("none", "none"))
        self.assertEqual(graders.routed_skill("work-lease", "none"), "work-lease")
        self.assertEqual(graders.top_probabilities({"a": 0.1, "b": 0.7, "c": 0.2, "d": 0.0}), "b=0.70, c=0.20, a=0.10")


class TestSummaries(unittest.TestCase):
    def test_skipped_never_counts_as_passed(self):
        results = [{"tier": "deterministic", "status": s} for s in ("pass", "pass", "fail", "error", "skipped")]
        results += [{"tier": "agentic", "status": "skipped"}]
        summary = graders.summarize(results)
        self.assertEqual(
            summary["deterministic"],
            {"total": 5, "passed": 2, "failed": 1, "errored": 1, "skipped": 1, "pass_rate": 0.5},
        )
        self.assertIsNone(summary["agentic"]["pass_rate"])
        self.assertNotIn("trigger", summary)
        self.assertEqual(summary["overall"]["total"], 6)

    def test_notes_are_single_compact_lines(self):
        text = graders.note("line one\nline two " + "x" * 600)
        self.assertNotIn("\n", text)
        self.assertLessEqual(len(text), 300)


if __name__ == "__main__":
    unittest.main()
