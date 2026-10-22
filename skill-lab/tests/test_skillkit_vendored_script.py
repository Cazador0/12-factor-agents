"""End to end: a skill script using a vendored _skillkit, run as a real subprocess.

This is the pattern every skill follows (CONVENTIONS §3): the script puts its
own directory on sys.path, imports _skillkit, and prints one envelope.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import textwrap
import unittest

from tests import skillkit_support as support
from _skillkit import schemas

SCRIPT = textwrap.dedent('''\
    #!/usr/bin/env python3
    """Validate a lease document and echo it (test fixture script)."""

    from __future__ import annotations

    import os
    import sys

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

    from _skillkit import EXIT_OK, EXIT_USAGE, cli, envelope, jsonschema_mini, schemas  # noqa: E402


    def main():
        parser = cli.base_parser("Validate a lease.")
        cli.add_input_argument(parser)
        parser.add_argument("--crash", action="store_true")
        args = parser.parse_args()
        if args.crash:
            raise RuntimeError("crash requested with " + os.environ.get("GITEA_TOKEN", ""))
        lease = cli.read_json(args.input)
        issues = schemas.validate_payload("lease", lease)
        if issues:
            errors = jsonschema_mini.issues_to_errors(issues, code="INPUT_SCHEMA_INVALID")
            return EXIT_USAGE, None, errors, []
        return EXIT_OK, lease, [], []


    if __name__ == "__main__":
        sys.exit(envelope.run_script(main, skill="demo-skill", script="check_lease.py", version="0.1.0", kind="lease"))
    ''')


class TestVendoredScript(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls._tmp = tempfile.TemporaryDirectory()
        cls.skill = os.path.join(cls._tmp.name, "skills", "demo-skill")
        scripts = os.path.join(cls.skill, "scripts")
        shutil.copytree(
            support.SKILLKIT_DIR, os.path.join(scripts, "_skillkit"), ignore=shutil.ignore_patterns("__pycache__")
        )
        os.makedirs(os.path.join(cls.skill, "assets", "schemas"))
        for name in ("envelope", "lease"):
            shutil.copy(support.schema_path(name), os.path.join(cls.skill, "assets", "schemas"))
        cls.script = os.path.join(scripts, "check_lease.py")
        with open(cls.script, "w", encoding="utf-8") as handle:
            handle.write(SCRIPT)
        cls.work = os.path.join(cls._tmp.name, "project")
        os.makedirs(cls.work)

    @classmethod
    def tearDownClass(cls):
        cls._tmp.cleanup()

    def run_script(self, *args, env=None):
        environment = {k: v for k, v in os.environ.items() if k != "SKILLKIT_DEBUG"}
        environment.update(env or {})
        proc = subprocess.run(
            [sys.executable, "-I", self.script, *args],
            cwd=self.work,
            capture_output=True,
            text=True,
            encoding="utf-8",
            env=environment,
        )
        doc = json.loads(proc.stdout) if proc.stdout.strip() else None
        if doc is not None and "--pretty" not in args:
            self.assertEqual(proc.stdout.count("\n"), 1, "exactly one compact JSON line")
            self.assertEqual(schemas.validate_envelope(doc, exit_code=proc.returncode), [])
        return proc, doc

    def write_input(self, name, doc):
        path = os.path.join(self.work, name)
        with open(path, "w", encoding="utf-8") as handle:
            json.dump(doc, handle)
        return path

    def test_valid_input(self):
        path = self.write_input("lease.json", support.load_example("lease"))
        proc, doc = self.run_script("--input", path, "--now", "2026-10-22T08:00:00Z")
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(doc["ok"])
        self.assertEqual(doc["created_at"], "2026-10-22T08:00:00Z")
        self.assertEqual(doc["producer"], {"skill": "demo-skill", "script": "check_lease.py", "version": "0.1.0"})

    def test_schema_invalid_input_is_an_input_error(self):
        lease = support.load_example("lease")
        lease["status"] = "stolen"
        proc, doc = self.run_script("--input", self.write_input("bad.json", lease))
        self.assertEqual(proc.returncode, 2)
        self.assertIsNone(doc["payload"])
        self.assertEqual(doc["errors"][0]["code"], "INPUT_SCHEMA_INVALID")
        self.assertEqual(doc["errors"][0]["path"], "/status")

    def test_missing_input_file(self):
        proc, doc = self.run_script("--input", "nope.json", "--pretty")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(doc["errors"][0]["code"], "INPUT_NOT_FOUND")
        self.assertTrue(proc.stdout.startswith("{\n  "))

    def test_usage_error(self):
        proc, doc = self.run_script("--bogus")
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(doc["errors"][0]["code"], "USAGE")
        self.assertIn("usage:", proc.stderr)

    def test_help(self):
        proc = subprocess.run([sys.executable, "-I", self.script, "--help"], capture_output=True, text=True)
        self.assertEqual(proc.returncode, 0)
        self.assertIn("Validate a lease.", proc.stdout)

    def test_crash_is_internal_redacted_and_traceback_free(self):
        proc, doc = self.run_script("--input", "x", "--crash", env={"GITEA_TOKEN": "gitea-secret-value-1"})
        self.assertEqual(proc.returncode, 2)
        self.assertEqual(doc["errors"][0]["code"], "INTERNAL")
        self.assertNotIn("gitea-secret-value-1", proc.stdout + proc.stderr)
        self.assertNotIn("Traceback", proc.stdout + proc.stderr)

    def test_stdin_input(self):
        proc = subprocess.run(
            [sys.executable, "-I", self.script, "--input", "-"],
            input=json.dumps(support.load_example("lease")),
            capture_output=True,
            text=True,
        )
        self.assertEqual(proc.returncode, 0)
        self.assertTrue(json.loads(proc.stdout)["ok"])

    def test_nothing_is_written_inside_the_skill(self):
        before = sorted(os.walk(self.skill))
        self.run_script("--input", self.write_input("lease2.json", support.load_example("lease")))
        after = [entry for entry in sorted(os.walk(self.skill)) if "__pycache__" not in entry[0]]
        self.assertEqual([e for e in before if "__pycache__" not in e[0]], after)


if __name__ == "__main__":
    unittest.main()
