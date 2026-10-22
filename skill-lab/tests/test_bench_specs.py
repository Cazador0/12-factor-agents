"""SPEC-102/103/104 hygiene: required headings, and traceability that resolves to real files and tests."""

from __future__ import annotations

import ast
import os
import re
import unittest

from tests import skillkit_support as support

SPECS = {
    "SPEC-102": "102-bench-runtimes-graders",
    "SPEC-103": "103-jev-grader",
    "SPEC-104": "104-scoring-gates",
}
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
    tree = ast.parse(read(path))
    return {
        node.name: {
            item.name for item in node.body if isinstance(item, ast.FunctionDef) and item.name.startswith("test_")
        }
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


class TestLabSpecs(unittest.TestCase):
    def each(self):
        for spec_id, folder in SPECS.items():
            directory = os.path.join(support.LAB_ROOT, "specs", folder)
            yield (
                spec_id,
                read(os.path.join(directory, "spec.md")),
                support.load_json(os.path.join(directory, "traceability.json")),
            )

    def test_headings_and_scenarios(self):
        for spec_id, spec, _ in self.each():
            with self.subTest(spec=spec_id):
                self.assertIn("**Spec**: %s" % spec_id, spec)
                for heading in REQUIRED_HEADINGS:
                    self.assertRegex(spec, r"(?m)^%s\b" % re.escape(heading))
                self.assertRegex(spec, r"\*\*Given\*\* .+\*\*When\*\* .+\*\*Then\*\*")
                self.assertRegex(spec, r"\*\*SC-001\*\*")

    def test_requirements_match_traceability(self):
        for spec_id, spec, trace in self.each():
            with self.subTest(spec=spec_id):
                in_spec = re.findall(r"\*\*(FR-\d{3})\*\*", spec)
                self.assertEqual(trace["spec"], spec_id)
                self.assertEqual(in_spec, [item["id"] for item in trace["requirements"]])
                self.assertEqual(in_spec, ["FR-%03d" % n for n in range(1, len(in_spec) + 1)], "numbered without gaps")

    def test_paths_and_test_ids_resolve(self):
        for spec_id, _, trace in self.each():
            for item in trace["requirements"]:
                with self.subTest(spec=spec_id, requirement=item["id"]):
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
