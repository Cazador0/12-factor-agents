"""SPEC-104 static rubric, description heuristics, unit-test counting and validator plumbing."""

from __future__ import annotations

import json
import os
import tempfile
import types
import unittest

from tests import skillkit_support as support
from tests.test_bench_fakes import ScratchRepo
from _skillkit import envelope, frontmatter
from lab import score

GOOD_DESCRIPTION = (
    "Independently verify a pull request against its spec and return a machine-readable verdict with blockers, "
    "evidence and requirement coverage, so the merge gate can decide without reading prose. Use when the user "
    "asks to review a PR, verify an implementation against its acceptance criteria, or decide whether a change "
    "is approvable. Do not use for writing the implementation itself; that belongs to the PSE skill."
)


def parsed(description):
    text = (
        '---\nname: x\ndescription: "%s"\nmetadata:\n  version: "1.2.3"\n'
        "  family: roles\n  spec: SPEC-003\n  author: t\n---\n# X\n" % description
    )
    return frontmatter.parse(text)


class TestDescriptionHeuristics(unittest.TestCase):
    def test_good_description_passes_every_heuristic(self):
        self.assertTrue(350 <= len(GOOD_DESCRIPTION) <= 900)
        self.assertEqual(score.description_heuristics(GOOD_DESCRIPTION), [])

    def test_each_heuristic(self):
        failed = {check for check, _, _ in score.description_heuristics("Short and vague.")}
        self.assertEqual(failed, {"use-when", "length-band", "trigger-phrases"})
        one_trigger = "x" * 340 + " Use when reviewing."
        self.assertEqual([c for c, _, _ in score.description_heuristics(one_trigger)], ["trigger-phrases"])

    def test_trigger_phrase_counting(self):
        self.assertEqual(score.trigger_phrases(' the user says "review this" or "check the PR".'), 2)
        self.assertEqual(score.trigger_phrases(" reviewing a PR, verifying evidence, or deciding approval."), 3)
        self.assertEqual(score.trigger_phrases(" formatting code. Also, other things, here."), 1)


class TestStaticRubric(unittest.TestCase):
    def test_validator_findings_drive_the_score(self):
        value, findings, notes = score.static_rubric(parsed(GOOD_DESCRIPTION), score.Measured((1, 2), ""), "SKILL.md")
        self.assertEqual((value, findings, notes), (65.0, {"errors": 1, "warnings": 2}, []))

    def test_heuristics_and_clamping(self):
        value, _, notes = score.static_rubric(parsed("Vague."), score.Measured((0, 0), ""), "SKILL.md")
        self.assertEqual(value, 80.0)
        self.assertEqual(len(notes), 3)
        self.assertTrue(notes[0].endswith("(-10)"))
        self.assertEqual(score.static_rubric(parsed("Vague."), score.Measured((9, 0), ""), "SKILL.md")[0], 0.0)

    def test_without_a_validator_the_frontmatter_lint_stands_in(self):
        broken = frontmatter.parse("---\nname: Bad_Name\ndescription: plain\n---\n")
        value, findings, _ = score.static_rubric(broken, score.Measured(None, "unavailable"), "SKILL.md")
        self.assertGreaterEqual(findings["errors"], 2)
        self.assertEqual(findings["warnings"], 0)
        self.assertLess(value, 90)


class TestUnittestCounting(unittest.TestCase):
    def test_parse_summaries(self):
        ok = "....\n" + "-" * 70 + "\nRan 4 tests in 0.01s\n\nOK (skipped=1)\n"
        self.assertEqual(score.parse_unittest_output(ok), score.TestCounts(4, 3, 0, 0, 1))
        failed = "Ran 6 tests in 0.2s\n\nFAILED (failures=1, errors=2, skipped=1, expected failures=1)\n"
        self.assertEqual(score.parse_unittest_output(failed), score.TestCounts(6, 2, 1, 2, 1))
        self.assertEqual(
            score.parse_unittest_output("\nRan 0 tests in 0.000s\n\nNO TESTS RAN\n"), score.TestCounts(0, 0, 0, 0, 0)
        )
        self.assertIsNone(score.parse_unittest_output("Traceback (most recent call last):\n"))

    def test_runs_a_skill_suite(self):
        repo = ScratchRepo()
        self.addCleanup(repo.close)
        skill_dir = repo.add_skill("demo-skill", "d")
        self.assertEqual(score.run_unit_tests(skill_dir).value, None)
        repo.write(
            "skills/demo-skill/tests/test_demo.py",
            "import unittest\n\nclass T(unittest.TestCase):\n    def test_ok(self):\n        pass\n\n"
            "    def test_bad(self):\n        self.fail('no')\n\n"
            "    @unittest.skip('later')\n    def test_skip(self):\n        pass\n",
        )
        measured = score.run_unit_tests(skill_dir)
        self.assertEqual(measured.value, score.TestCounts(3, 1, 1, 0, 1))


class TestValidatorPlumbing(unittest.TestCase):
    REPORT = support.load_example("validation-report")

    def fake_main(self, code, payload):
        def main(argv):
            self.argv = argv
            env = envelope.make_envelope(
                "validation-report",
                payload,
                skill="skill-lab",
                script="validate",
                version="0.1.0",
                ok=code == 0,
                now="2026-10-22T08:00:00Z",
            )
            envelope.emit(env)
            return code

        return main

    def test_capture_and_parse_an_in_process_validator(self):
        code, text = score.capture_envelope(self.fake_main(1, self.REPORT), ["--skill", "x"])
        self.assertEqual((code, self.argv), (1, ["--skill", "x"]))
        report, source = score.report_from_output(code, text, "lab.validate")
        self.assertEqual((report, source), (self.REPORT, "lab.validate"))

    def test_unusable_validator_output(self):
        self.assertIsNone(score.report_from_output(0, "not json", "v")[0])
        code, text = score.capture_envelope(self.fake_main(2, None), [])
        report, reason = score.report_from_output(code, text, "v")
        self.assertIsNone(report)
        self.assertIn("exit 2", reason)

    def test_install_state_findings_do_not_count(self):
        report = json.loads(json.dumps(self.REPORT))
        finding = {"severity": "warning", "message": "m", "path": "p"}
        report["skills"] = [
            {
                "name": "x",
                "ok": False,
                "findings": [
                    dict(finding, rule="install.not-installed"),
                    dict(finding, rule="body.description-length"),
                    dict(finding, rule="frontmatter.description-quoted", severity="error"),
                ],
            }
        ]
        with tempfile.TemporaryDirectory() as tmp:
            path = os.path.join(tmp, "validation.json")
            with open(path, "w", encoding="utf-8") as handle:
                json.dump(report, handle)
            measured = score.load_validation(types.SimpleNamespace(validation=path, skill="x"), None)
        self.assertEqual(measured.value, (1, 1))

    def test_report_from_envelope_or_payload(self):
        env = {"schema": envelope.ENVELOPE_SCHEMA, "kind": "validation-report", "payload": self.REPORT}
        self.assertEqual(score._report_from(env, "f"), self.REPORT)
        self.assertEqual(score._report_from(json.loads(json.dumps(self.REPORT)), "f"), self.REPORT)


if __name__ == "__main__":
    unittest.main()
