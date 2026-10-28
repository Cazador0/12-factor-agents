"""skill-lab dispatcher (SPEC-101 FR-001): the command table, lazy imports, one envelope per run."""

from __future__ import annotations

import io
import json
import os
import subprocess
import sys
import tempfile
import unittest
from contextlib import redirect_stdout
from unittest import mock

from tests import test_lab_core_fixtures as fx

from lab import cli

BIN = os.path.join(fx.LAB_ROOT, "bin", "skill-lab")
OWN_COMMANDS = ("validate", "sync", "install", "catalog", "new", "doctor", "test")


class TestCommandTable(unittest.TestCase):
    def test_every_command_is_registered(self):
        self.assertEqual(
            list(cli.COMMANDS), ["validate", "sync", "install", "catalog", "new", "doctor", "test", "bench", "score"]
        )
        self.assertEqual(cli.COMMANDS["bench"].module, "lab.bench")
        self.assertEqual(cli.COMMANDS["score"].module, "lab.score")

    def test_own_commands_import_and_expose_main(self):
        for name in OWN_COMMANDS:
            with self.subTest(command=name):
                entry = cli._load(name, cli.COMMANDS[name])
                self.assertTrue(callable(entry), entry)

    def test_each_own_command_help_exits_0_without_an_envelope(self):
        for name in OWN_COMMANDS:
            with self.subTest(command=name):
                stdout = io.StringIO()
                with redirect_stdout(stdout):
                    code = cli.main([name, "--help"])
                self.assertEqual(code, 0)
                self.assertIn("usage: skill-lab %s" % name, stdout.getvalue())
                self.assertIn("--repo", stdout.getvalue())


class TestDispatch(unittest.TestCase):
    def dispatch(self, argv):
        code, envelope = fx.run(cli.main, argv)
        fx.assert_envelope(self, envelope, code)
        return code, envelope

    def test_help_and_version(self):
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(cli.main(["--help"]), 0)
        for name in cli.COMMANDS:
            self.assertIn("  " + name, stdout.getvalue())
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            self.assertEqual(cli.main(["--version"]), 0)
        self.assertEqual(stdout.getvalue(), "skill-lab 0.1.0\n")

    def test_missing_and_unknown_commands(self):
        for argv in ([], ["--pretty"], ["frobnicate"]):
            with self.subTest(argv=argv):
                code, envelope = self.dispatch(argv)
                self.assertEqual(code, 2)
                self.assertEqual(envelope["errors"][0]["code"], "USAGE")
                self.assertEqual(envelope["kind"], "lab-cli")

    def test_missing_module_is_command_unavailable(self):
        table = dict(cli.COMMANDS, bench=cli.Command("lab.no_such_module", "main", "x"))
        with mock.patch.object(cli, "COMMANDS", table):
            code, envelope = self.dispatch(["bench", "--tier", "deterministic"])
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "COMMAND_UNAVAILABLE")
        self.assertIn("'bench'", envelope["errors"][0]["message"])

    def test_broken_module_is_internal_not_a_traceback(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "broken_lab_cmd_xyz.py"), "w", encoding="utf-8") as handle:
                handle.write("import no_such_dependency_xyz\n")
            sys.path.insert(0, tmp)
            try:
                table = dict(cli.COMMANDS, score=cli.Command("broken_lab_cmd_xyz", "main", "x"))
                with mock.patch.object(cli, "COMMANDS", table):
                    code, envelope = self.dispatch(["score"])
            finally:
                sys.path.remove(tmp)
                sys.modules.pop("broken_lab_cmd_xyz", None)
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "INTERNAL")

    def test_module_without_main(self):
        table = dict(cli.COMMANDS, score=cli.Command("lab.paths", "main", "x"))
        with mock.patch.object(cli, "COMMANDS", table):
            code, envelope = self.dispatch(["score"])
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "COMMAND_UNAVAILABLE"))

    def test_rule_codes(self):
        self.assertEqual(cli.rule_code("frontmatter.name-pattern"), "FRONTMATTER_NAME_PATTERN")
        messages = [{"code": "X", "message": str(i), "path": None} for i in range(25)]
        capped = cli.capped(messages)
        self.assertEqual(len(capped), 21)
        self.assertEqual(capped[-1]["code"], "TRUNCATED")


class TestExecutable(unittest.TestCase):
    """bin/skill-lab as a real process, the way agents and CI run it."""

    def run_bin(self, *args, cwd=None):
        env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
        return subprocess.run(
            [sys.executable, BIN] + list(args),
            cwd=cwd,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=120,
        )

    def test_is_an_executable_python3_script(self):
        self.assertTrue(os.access(BIN, os.X_OK))
        with open(BIN, encoding="utf-8") as handle:
            self.assertEqual(handle.readline(), "#!/usr/bin/env python3\n")

    def test_prints_exactly_one_envelope_from_any_directory(self):
        repo = fx.Repo.for_test(self)
        with tempfile.TemporaryDirectory() as elsewhere:
            proc = self.run_bin("validate", "--repo", repo.root, "--no-run", cwd=elsewhere)
        self.assertEqual(proc.returncode, 0, proc.stderr)
        lines = proc.stdout.decode("utf-8").splitlines()
        self.assertEqual(len(lines), 1)
        self.assertEqual(json.loads(lines[0])["kind"], "validation-report")

    def test_pretty_output(self):
        repo = fx.Repo.for_test(self)
        proc = self.run_bin("catalog", "--check", "--repo", repo.root, "--pretty")
        self.assertEqual(proc.returncode, 1)
        text = proc.stdout.decode("utf-8")
        self.assertTrue(text.startswith("{\n  "))
        self.assertEqual(json.loads(text)["errors"][0]["code"], "CATALOG_MISSING")


if __name__ == "__main__":
    unittest.main()
