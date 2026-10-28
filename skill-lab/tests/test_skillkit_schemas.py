"""Tests for _skillkit.schemas: locating, loading and applying vendored contracts."""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import sys
import tempfile
import unittest

from tests import skillkit_support
from _skillkit import EXIT_USAGE, schemas
from _skillkit.envelope import ScriptError


class TestLocation(unittest.TestCase):
    def test_canonical_copy_has_no_skill_root(self):
        self.assertIsNone(schemas.skill_root())
        self.assertEqual(schemas.default_schema_dirs(), [skillkit_support.SCHEMA_DIR])

    def test_vendored_copy_finds_its_skill(self):
        with tempfile.TemporaryDirectory() as tmp:
            skill = os.path.join(tmp, "skills", "demo-skill")
            scripts = os.path.join(skill, "scripts")
            shutil.copytree(
                skillkit_support.SKILLKIT_DIR,
                os.path.join(scripts, "_skillkit"),
                ignore=shutil.ignore_patterns("__pycache__"),
            )
            os.makedirs(os.path.join(skill, "assets", "schemas"))
            shutil.copy(skillkit_support.schema_path("lease"), os.path.join(skill, "assets", "schemas"))
            probe = (
                "import json, sys; sys.path.insert(0, sys.argv[1]);"
                "from _skillkit import schemas;"
                "print(json.dumps([schemas.skill_root(), schemas.default_schema_dirs(),"
                " schemas.load_schema('lease')['$id']]))"
            )
            output = subprocess.run(
                [sys.executable, "-I", "-c", probe, scripts], check=True, capture_output=True, text=True
            ).stdout
        root, dirs, schema_id = json.loads(output)
        self.assertEqual(os.path.realpath(root), os.path.realpath(skill))
        self.assertEqual(os.path.realpath(dirs[0]), os.path.realpath(os.path.join(skill, "assets", "schemas")))
        self.assertEqual(schema_id, "urn:skill-lab:schema:lease:v1")


class TestLoad(unittest.TestCase):
    def test_load_by_name(self):
        schema = schemas.load_schema("review-verdict")
        self.assertEqual(schema["$id"], "urn:skill-lab:schema:review-verdict:v1")
        self.assertIs(schemas.load_schema("review-verdict"), schema, "cached")

    def test_search_dirs_order(self):
        with tempfile.TemporaryDirectory() as first, tempfile.TemporaryDirectory() as second:
            with open(os.path.join(second, "lease.v1.schema.json"), "w") as handle:
                json.dump({"title": "second"}, handle)
            self.assertEqual(schemas.load_schema("lease", [first, second])["title"], "second")
            with open(os.path.join(first, "lease.v1.schema.json"), "w") as handle:
                json.dump({"title": "first"}, handle)
            self.assertEqual(schemas.load_schema("lease", [first])["title"], "first")

    def test_missing_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            with self.assertRaises(ScriptError) as ctx:
                schemas.load_schema("lease", [tmp])
        self.assertEqual((ctx.exception.code, ctx.exception.exit_code), ("SCHEMA_NOT_FOUND", EXIT_USAGE))

    def test_unreadable_schema(self):
        with tempfile.TemporaryDirectory() as tmp:
            with open(os.path.join(tmp, "lease.v1.schema.json"), "w") as handle:
                handle.write("{not json")
            with self.assertRaises(ScriptError) as ctx:
                schemas.load_schema("lease", [tmp])
        self.assertEqual(ctx.exception.code, "SCHEMA_UNREADABLE")

    def test_names_cannot_traverse(self):
        for name in ("../envelope", "Lease", "lease.v1", "", None):
            with self.subTest(name=name), self.assertRaises(ScriptError) as ctx:
                schemas.load_schema(name)
            self.assertEqual(ctx.exception.code, "SCHEMA_NAME_INVALID")

    def test_parse_urn(self):
        self.assertEqual(schemas.parse_urn("urn:skill-lab:schema:task-graph:v1"), ("task-graph", 1))
        self.assertEqual(schemas.parse_urn("urn:skill-lab:schema:lease:v12"), ("lease", 12))
        for bad in ("urn:other:lease:v1", "urn:skill-lab:schema:lease:v0", "urn:skill-lab:schema:Lease:v1", 3):
            with self.subTest(bad=bad), self.assertRaises(ScriptError):
                schemas.parse_urn(bad)


class TestValidate(unittest.TestCase):
    def test_validate_payload(self):
        lease = skillkit_support.load_example("lease")
        self.assertEqual(schemas.validate_payload("lease", lease), [])
        lease["status"] = "stolen"
        issues = schemas.validate_payload("lease", lease)
        self.assertEqual([(i.path, i.keyword) for i in issues], [("/status", "enum")])

    def test_validate_envelope_checks_payload_when_ok(self):
        env = skillkit_support.load_example("envelope")
        self.assertEqual(schemas.validate_envelope(env), [])
        env["payload"]["result"] = "LGTM"
        issues = schemas.validate_envelope(env)
        self.assertIn(("/payload/result", "enum"), [(i.path, i.keyword) for i in issues])

    def test_validate_envelope_checks_payload_for_exit_1_only(self):
        env = skillkit_support.load_example("envelope")
        env.update(ok=False, errors=[{"code": "CHANGES_REQUESTED", "message": "x"}])
        env["payload"]["pr"] = 0
        self.assertEqual(schemas.validate_envelope(env, exit_code=2), [])
        self.assertTrue(schemas.validate_envelope(env, exit_code=1))

    def test_envelope_problems_are_reported_before_payload(self):
        env = skillkit_support.load_example("envelope")
        del env["producer"]
        self.assertEqual([(i.path, i.keyword) for i in schemas.validate_envelope(env)], [("/producer", "required")])
        self.assertTrue(schemas.validate_envelope("not an object"))


if __name__ == "__main__":
    unittest.main()
