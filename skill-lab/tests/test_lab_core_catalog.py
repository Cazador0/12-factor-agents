"""skill-lab catalog (SPEC-101 FR-018, FR-019): deterministic CATALOG.json and --check."""

from __future__ import annotations

import json
import os
import shutil
import unittest

from tests import test_lab_core_fixtures as fx

from _skillkit import jsonschema_mini
from lab import catalog


class TestCatalog(unittest.TestCase):
    def setUp(self):
        self.repo = fx.Repo.for_test(self)
        self.repo.add_skill("zeta-skill")
        self.repo.add_skill("alpha-skill")

    def catalog(self, *args):
        code, envelope = fx.run(catalog.main, ["--repo", self.repo.root] + list(args))
        fx.assert_envelope(self, envelope, code, catalog.PAYLOAD_SCHEMA)
        return code, envelope

    def written(self):
        return json.loads(self.repo.read("skills/CATALOG.json"))

    def test_writes_a_sorted_valid_catalog(self):
        code, envelope = self.catalog()
        self.assertEqual(code, 0)
        self.assertTrue(envelope["payload"]["written"])
        document = self.written()
        self.assertEqual(jsonschema_mini.validate(document, catalog.CATALOG_SCHEMA), [])
        self.assertEqual([s["name"] for s in document["skills"]], ["alpha-skill", "zeta-skill"])
        alpha = document["skills"][0]
        self.assertEqual(alpha["path"], "skills/alpha-skill")
        self.assertEqual(alpha["scripts"], ["scripts/check.py"])
        self.assertEqual(alpha["schemas"], ["envelope.v1.schema.json"])
        self.assertEqual(alpha["eval_counts"], {"deterministic": 4, "agentic": 2, "trigger": 4})
        self.assertEqual((alpha["version"], alpha["family"], alpha["spec"]), ("0.1.0", "meta", "SPEC-002"))
        self.assertEqual(document["generated_by"], "skill-lab catalog")
        expected_bytes = sum(len((s["name"] + s["description"]).encode("utf-8")) for s in document["skills"])
        self.assertEqual(document["catalog_bytes"], expected_bytes)
        self.assertEqual(envelope["payload"]["catalog_bytes"], expected_bytes)

    def test_output_is_byte_stable(self):
        self.catalog()
        first = self.repo.read("skills/CATALOG.json")
        code, envelope = self.catalog()
        self.assertEqual(code, 0)
        self.assertFalse(envelope["payload"]["written"])
        self.assertTrue(envelope["payload"]["in_sync"])
        self.assertEqual(self.repo.read("skills/CATALOG.json"), first)
        self.assertTrue(first.endswith("}\n"))

    def test_check_detects_missing_and_stale_without_writing(self):
        code, envelope = self.catalog("--check")
        self.assertEqual((code, envelope["errors"][0]["code"]), (1, "CATALOG_MISSING"))
        self.assertFalse(os.path.exists(self.repo.path("skills", "CATALOG.json")))
        self.catalog()
        self.assertEqual(self.catalog("--check")[0], 0)
        os.remove(self.repo.skill("alpha-skill", "evals", "cases", "det-1.json"))
        code, envelope = self.catalog("--check")
        self.assertEqual((code, envelope["errors"][0]["code"]), (1, "CATALOG_STALE"))

    def test_unparseable_skill_is_skipped_with_a_warning(self):
        self.repo.write("skills/broken-skill/SKILL.md", "no frontmatter")
        code, envelope = self.catalog()
        self.assertEqual(code, 0)
        self.assertEqual([w["code"] for w in envelope["warnings"]], ["SKILL_SKIPPED"])
        self.assertNotIn("broken-skill", [s["name"] for s in self.written()["skills"]])

    def test_empty_skills_folder(self):
        for name in ("alpha-skill", "zeta-skill"):
            shutil.rmtree(self.repo.skill(name))
        code, envelope = self.catalog()
        self.assertEqual(code, 0)
        self.assertEqual(
            self.written(), {"catalog_bytes": 0, "generated_by": "skill-lab catalog", "schema_version": 1, "skills": []}
        )

    def test_missing_skills_folder(self):
        shutil.rmtree(self.repo.path("skills"))
        code, envelope = self.catalog()
        self.assertEqual((code, envelope["errors"][0]["code"]), (2, "SKILLS_DIR_NOT_FOUND"))


if __name__ == "__main__":
    unittest.main()
