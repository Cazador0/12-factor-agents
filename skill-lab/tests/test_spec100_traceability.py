"""SPEC-100 hygiene: required headings, and traceability that resolves to real files and tests."""

from __future__ import annotations

import ast
import os
import re
import unittest

from tests import skillkit_support as support

SPEC_DIR = os.path.join(support.LAB_ROOT, "specs", "100-contracts-skillkit")
REQUIRED_HEADINGS = [
    "## User Scenarios & Testing",
    "## Requirements",
    "### Functional Requirements",
    "### Key Entities",
    "## Success Criteria",
    "## Assumptions",
    "## Non-goals",
    "## Contracts",
    "## Error semantics",
    "## Security",
    "## Runtime compatibility",
]


def read(path):
    with open(path, "r", encoding="utf-8") as handle:
        return handle.read()


def test_methods(path):
    """Map class name -> set of test method names defined in a test file."""
    tree = ast.parse(read(path))
    return {
        node.name: {
            item.name for item in node.body if isinstance(item, ast.FunctionDef) and item.name.startswith("test_")
        }
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


class TestSpec100(unittest.TestCase):
    def setUp(self):
        self.spec = read(os.path.join(SPEC_DIR, "spec.md"))
        self.trace = support.load_json(os.path.join(SPEC_DIR, "traceability.json"))

    def test_headings(self):
        self.assertIn("SPEC-100", self.spec)
        for heading in REQUIRED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertRegex(self.spec, r"(?m)^%s\b" % re.escape(heading))
        self.assertRegex(self.spec, r"\*\*Given\*\* .+\*\*When\*\* .+\*\*Then\*\*")
        self.assertRegex(self.spec, r"\*\*SC-001\*\*")

    def test_requirements_match_traceability(self):
        in_spec = re.findall(r"\*\*(FR-\d{3})\*\*", self.spec)
        traced = [item["id"] for item in self.trace["requirements"]]
        self.assertEqual(self.trace["spec"], "SPEC-100")
        self.assertEqual(in_spec, traced)
        self.assertEqual(in_spec, ["FR-%03d" % n for n in range(1, len(in_spec) + 1)], "numbered without gaps")

    def test_paths_and_test_ids_resolve(self):
        for item in self.trace["requirements"]:
            with self.subTest(requirement=item["id"]):
                self.assertTrue(item["implemented_by"])
                self.assertTrue(item["verified_by"])
                for path in item["implemented_by"]:
                    self.assertTrue(os.path.exists(os.path.join(support.REPO_ROOT, path)), path)
                for test_id in item["verified_by"]:
                    file_part, class_name, method = test_id.split("::")
                    path = os.path.join(support.REPO_ROOT, file_part)
                    self.assertTrue(os.path.isfile(path), file_part)
                    self.assertIn(method, test_methods(path).get(class_name, set()), test_id)


if __name__ == "__main__":
    unittest.main()
