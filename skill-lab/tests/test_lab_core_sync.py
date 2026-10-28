"""skill-lab sync (SPEC-101 FR-013, FR-014): exact vendoring, drift checks, --add-schema."""

from __future__ import annotations

import os
import shutil
import unittest

from tests import test_lab_core_fixtures as fx

from lab import paths, sync, validate

SKILL = "demo-skill"


class SyncTestCase(unittest.TestCase):
    def setUp(self):
        self.repo = fx.Repo.for_test(self)
        self.repo.add_skill(SKILL)
        self.vendored = self.repo.skill(SKILL, "scripts", "_skillkit")
        self.schemas = self.repo.skill(SKILL, "assets", "schemas")

    def sync(self, *args):
        code, envelope = fx.run(sync.main, ["--repo", self.repo.root] + list(args))
        fx.assert_envelope(self, envelope, code, sync.PAYLOAD_SCHEMA)
        return code, envelope

    def assertInSync(self):
        code, envelope = self.sync("--check")
        self.assertEqual(code, 0, envelope["payload"])
        self.assertTrue(envelope["payload"]["in_sync"])
        self.assertFalse(paths.compare_trees(fx.support.SKILLKIT_DIR, self.vendored))


class TestSync(SyncTestCase):
    def test_fresh_fixture_is_in_sync(self):
        self.assertInSync()

    def test_check_reports_every_kind_of_drift_without_writing(self):
        with open(os.path.join(self.vendored, "ids.py"), "a", encoding="utf-8") as handle:
            handle.write("# local edit\n")
        os.remove(os.path.join(self.vendored, "redact.py"))
        self.repo.write("skills/%s/scripts/_skillkit/old_module.py" % SKILL, "")
        self.repo.write_json("skills/%s/assets/schemas/envelope.v1.schema.json" % SKILL, {})
        before = paths.list_tree(self.repo.skill(SKILL))

        code, envelope = self.sync("--check")
        self.assertEqual(code, 1)
        self.assertEqual(envelope["errors"][0]["code"], "VENDOR_DRIFT")
        actions = {(a["op"], os.path.basename(a["path"])) for a in envelope["payload"]["skills"][0]["actions"]}
        self.assertEqual(
            actions,
            {
                ("update", "ids.py"),
                ("create", "redact.py"),
                ("delete", "old_module.py"),
                ("update", "envelope.v1.schema.json"),
            },
        )
        self.assertEqual(envelope["payload"]["drift"], 4)
        self.assertEqual(paths.list_tree(self.repo.skill(SKILL)), before, "--check must not write")

        code, envelope = self.sync()
        self.assertEqual(code, 0)
        self.assertEqual(envelope["payload"]["drift"], 4)
        self.assertInSync()

    def test_pycache_is_ignored_and_kept(self):
        self.repo.write("skills/%s/scripts/_skillkit/__pycache__/ids.cpython-313.pyc" % SKILL, "x")
        self.assertInSync()
        self.sync()
        self.assertTrue(os.path.exists(os.path.join(self.vendored, "__pycache__", "ids.cpython-313.pyc")))

    def test_vendors_into_a_skill_with_bare_scripts(self):
        shutil.rmtree(self.vendored)
        shutil.rmtree(self.repo.skill(SKILL, "assets"))
        code, envelope = self.sync()
        self.assertEqual(code, 0)
        self.assertFalse(paths.compare_trees(fx.support.SKILLKIT_DIR, self.vendored))
        self.assertTrue(os.path.isfile(os.path.join(self.schemas, "envelope.v1.schema.json")))
        self.assertEqual(fx.rules(fx.run(validate.main, ["--repo", self.repo.root, "--no-run"])[1], "error"), [])

    def test_replaces_a_symlinked_skillkit_with_a_real_copy(self):
        shutil.rmtree(self.vendored)
        os.symlink(fx.support.SKILLKIT_DIR, self.vendored)
        self.assertEqual(self.sync("--check")[0], 1)
        self.sync()
        self.assertFalse(os.path.islink(self.vendored))
        self.assertInSync()

    def test_skills_without_scripts_are_never_touched(self):
        self.repo.write("skills/docs-only/SKILL.md", fx.skill_md("docs-only", "SPEC-050"))
        code, envelope = self.sync()
        self.assertEqual(code, 0)
        self.assertEqual(envelope["payload"]["skipped"], [{"name": "docs-only", "reason": "no scripts/ folder"}])
        self.assertEqual(os.listdir(self.repo.skill("docs-only")), ["SKILL.md"])

    def test_refreshes_vendored_schemas_by_file_name(self):
        shutil.copy(fx.support.schema_path("lease"), self.schemas)
        self.repo.write_json("skills/%s/assets/schemas/lease.v1.schema.json" % SKILL, {"old": True})
        code, envelope = self.sync()
        self.assertEqual(code, 0)
        self.assertTrue(
            paths.files_equal(fx.support.schema_path("lease"), os.path.join(self.schemas, "lease.v1.schema.json"))
        )

    def test_unknown_schema_files_are_left_alone_with_a_warning(self):
        self.repo.write_json("skills/%s/assets/schemas/mine.json" % SKILL, {})
        code, envelope = self.sync()
        self.assertEqual(code, 0)
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["UNKNOWN_SCHEMA"])
        self.assertTrue(os.path.exists(os.path.join(self.schemas, "mine.json")))

    def test_skill_filter(self):
        self.repo.add_skill("second-skill")
        os.remove(os.path.join(self.repo.skill("second-skill", "scripts", "_skillkit"), "ids.py"))
        code, envelope = self.sync("--check", "--skill", SKILL)
        self.assertEqual(code, 0)
        self.assertEqual([s["name"] for s in envelope["payload"]["skills"]], [SKILL])
        self.assertEqual(self.sync("--check")[0], 1)
        code, envelope = self.sync("--skill", "ghost")
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "SKILL_NOT_FOUND"))

    def test_empty_repository(self):
        shutil.rmtree(self.repo.skill(SKILL))
        code, envelope = self.sync("--check")
        self.assertEqual(code, 0)
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["NO_SKILLS"])


class TestAddSchema(SyncTestCase):
    def test_adds_one_contract(self):
        for name in ("lease", "lease.v1", "lease.v1.schema.json"):
            with self.subTest(name=name):
                target = os.path.join(self.schemas, "lease.v1.schema.json")
                if os.path.exists(target):
                    os.remove(target)
                code, envelope = self.sync("--add-schema", name, "--skill", SKILL)
                self.assertEqual(code, 0)
                self.assertTrue(paths.files_equal(fx.support.schema_path("lease"), target))
        self.assertInSync()

    def test_check_mode_reports_the_missing_contract(self):
        code, envelope = self.sync("--check", "--add-schema", "lease", "--skill", SKILL)
        self.assertEqual(code, 1)
        self.assertFalse(os.path.exists(os.path.join(self.schemas, "lease.v1.schema.json")))

    def test_needs_exactly_one_skill(self):
        code, envelope = self.sync("--add-schema", "lease")
        self.assertEqual(code, 2)
        self.assertEqual(envelope["errors"][0]["code"], "USAGE")

    def test_unknown_contract(self):
        code, envelope = self.sync("--add-schema", "imaginary", "--skill", SKILL)
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "SCHEMA_NOT_FOUND"))

    def test_skill_without_scripts_is_refused(self):
        self.repo.write("skills/docs-only/SKILL.md", fx.skill_md("docs-only", "SPEC-050"))
        code, envelope = self.sync("--add-schema", "lease", "--skill", "docs-only")
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "SKILL_HAS_NO_SCRIPTS"))


if __name__ == "__main__":
    unittest.main()
