"""skill-lab test (SPEC-101 FR-025, FR-026): unittest suites per skill and for the lab, aggregated."""

from __future__ import annotations

import os
import shutil
import textwrap
import unittest

from tests import test_lab_core_fixtures as fx

from lab import testrun

PASSING = textwrap.dedent(
    """\
    import unittest


    class TestOk(unittest.TestCase):
        def test_one(self):
            pass

        def test_two(self):
            pass

        @unittest.skip("not today")
        def test_skipped(self):
            pass
    """
)

FAILING = textwrap.dedent(
    """\
    import os
    import unittest


    class TestBad(unittest.TestCase):
        def test_fails(self):
            self.fail("token is " + os.environ.get("GITEA_TOKEN", ""))

        def test_errors(self):
            raise RuntimeError("boom")

        def test_passes(self):
            pass
    """
)


class TestParseSummary(unittest.TestCase):
    def test_ok(self):
        self.assertEqual(testrun.parse_summary("....\nRan 4 tests in 0.010s\n\nOK\n"), testrun.Counts(4, 4, 0, 0, 0))

    def test_ok_with_skips(self):
        self.assertEqual(
            testrun.parse_summary("Ran 3 tests in 0.1s\n\nOK (skipped=1)\n"), testrun.Counts(3, 2, 0, 0, 1)
        )

    def test_failed(self):
        output = "Ran 9 tests in 1.0s\n\nFAILED (failures=2, errors=1, skipped=3, expected failures=1)\n"
        self.assertEqual(testrun.parse_summary(output), testrun.Counts(9, 3, 2, 1, 3))

    def test_unexpected_success_counts_as_failure(self):
        output = "Ran 2 tests in 0.1s\n\nFAILED (unexpected successes=1)\n"
        self.assertEqual(testrun.parse_summary(output), testrun.Counts(2, 1, 1, 0, 0))

    def test_no_tests(self):
        self.assertEqual(
            testrun.parse_summary("\nRan 0 tests in 0.000s\n\nNO TESTS RAN\n"), testrun.Counts(0, 0, 0, 0, 0)
        )

    def test_crash_has_no_summary(self):
        self.assertIsNone(testrun.parse_summary("Traceback (most recent call last):\nImportError: x\n"))


class TestCommand(unittest.TestCase):
    def setUp(self):
        self.repo = fx.Repo.for_test(self)
        self.repo.write("skill-lab/tests/__init__.py", "")
        self.repo.write("skill-lab/tests/test_lab.py", PASSING)
        for name in ("good-skill", "bad-skill", "bare-skill"):
            self.repo.write("skills/%s/SKILL.md" % name, fx.skill_md(name, "SPEC-001"))
        self.repo.write("skills/good-skill/tests/test_good.py", PASSING)
        self.repo.write("skills/bad-skill/tests/test_bad.py", FAILING)

    def run_tests(self, *args):
        code, envelope = fx.run(testrun.main, ["--repo", self.repo.root] + list(args))
        fx.assert_envelope(self, envelope, code, testrun.PAYLOAD_SCHEMA)
        return code, envelope

    def suites(self, envelope):
        return {suite["name"]: suite for suite in envelope["payload"]["suites"]}

    def test_aggregates_every_suite(self):
        secret = "ghp_" + "x" * 30
        with fx.support.env(GITEA_TOKEN=secret):
            code, envelope = self.run_tests()
        self.assertEqual(code, 1)
        suites = self.suites(envelope)
        self.assertEqual(list(suites), ["skill-lab", "skills/bad-skill", "skills/bare-skill", "skills/good-skill"])
        self.assertEqual(
            (suites["skill-lab"]["status"], suites["skill-lab"]["ran"], suites["skill-lab"]["skipped"]),
            ("passed", 3, 1),
        )
        bad = suites["skills/bad-skill"]
        self.assertEqual(
            (bad["status"], bad["ran"], bad["passed"], bad["failed"], bad["errored"]), ("failed", 3, 1, 1, 1)
        )
        self.assertTrue(bad["log_tail"])
        self.assertNotIn(secret, "\n".join(bad["log_tail"]))
        self.assertEqual(suites["skills/bare-skill"]["status"], "missing")
        self.assertEqual(suites["skills/good-skill"]["log_tail"], [])
        totals = envelope["payload"]["totals"]
        self.assertEqual(
            (totals["suites"], totals["ran"], totals["failed"], totals["errored"], totals["skipped"]), (4, 9, 1, 1, 2)
        )
        self.assertEqual([e["code"] for e in envelope["errors"]], ["TESTS_FAILED"])
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["SUITE_MISSING"])

    def test_skill_filter_runs_only_those_skills(self):
        code, envelope = self.run_tests("--skill", "good-skill")
        self.assertEqual(code, 0)
        self.assertEqual(list(self.suites(envelope)), ["skills/good-skill"])
        self.assertEqual(envelope["payload"]["totals"]["passed"], 2)
        code, envelope = self.run_tests("--skill", "ghost")
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "SKILL_NOT_FOUND"))

    def test_lab_only(self):
        code, envelope = self.run_tests("--lab-only")
        self.assertEqual(code, 0)
        self.assertEqual(list(self.suites(envelope)), ["skill-lab"])

    def test_skill_tests_run_from_the_skill_folder(self):
        probe = (
            "import os, unittest\n\n"
            "class TestCwd(unittest.TestCase):\n"
            "    def test_cwd(self):\n"
            "        self.assertTrue(os.path.isfile('SKILL.md'))\n"
        )
        self.repo.write("skills/good-skill/tests/test_cwd.py", probe)
        code, envelope = self.run_tests("--skill", "good-skill")
        self.assertEqual(code, 0, envelope["payload"])
        self.assertEqual(self.suites(envelope)["skills/good-skill"]["ran"], 4)

    def test_import_crash_is_an_error(self):
        self.repo.write("skills/good-skill/tests/test_crash.py", "import no_such_module_xyz\n")
        code, envelope = self.run_tests("--skill", "good-skill")
        self.assertEqual(code, 1)
        self.assertIn(self.suites(envelope)["skills/good-skill"]["status"], ("failed", "error"))

    def test_empty_tests_folder_is_reported_not_failed(self):
        shutil.rmtree(self.repo.skill("good-skill", "tests"))
        os.makedirs(self.repo.skill("good-skill", "tests"))
        code, envelope = self.run_tests("--skill", "good-skill")
        self.assertEqual(code, 0)
        self.assertEqual(self.suites(envelope)["skills/good-skill"]["status"], "no_tests")
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["SUITE_NO_TESTS"])

    def test_timeout_is_an_error(self):
        self.repo.write("skills/good-skill/tests/test_slow.py", "import time\ntime.sleep(10)\n")
        code, envelope = self.run_tests("--skill", "good-skill", "--timeout", "1")
        self.assertEqual(code, 1)
        suite = self.suites(envelope)["skills/good-skill"]
        self.assertEqual(suite["status"], "error")
        self.assertIn("TIMEOUT after 1s", suite["log_tail"][-1])

    def test_options_are_validated(self):
        self.assertEqual(self.run_tests("--timeout", "0")[0], 2)
        self.assertEqual(self.run_tests("--lab-only", "--skill", "good-skill")[0], 2)


if __name__ == "__main__":
    unittest.main()
