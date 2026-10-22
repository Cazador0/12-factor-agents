"""SPEC-101 hygiene: required headings, traceability that resolves, and a rule catalog that matches the code."""

from __future__ import annotations

import ast
import json
import os
import re
import unittest

from tests import test_lab_core_fixtures as fx

SPEC_DIR = os.path.join(fx.LAB_ROOT, "specs", "101-lab-core")
VALIDATE_SOURCE = os.path.join(fx.LAB_ROOT, "lab", "validate.py")
REQUIRED_HEADINGS = (
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
)
RULE_FAMILIES = "frontmatter|body|references|scripts|vendor|evals|tests|spec|install|zed|scaffold"
RULE_LITERAL = re.compile(r'"((?:%s)\.[a-z0-9-]+)"' % RULE_FAMILIES)
DYNAMIC_RULES = (
    "evals.deterministic-count",
    "evals.agentic-count",
    "evals.positive-trigger-count",
    "evals.negative-trigger-count",
)


def read(path):
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def test_methods(path):
    tree = ast.parse(read(path))
    return {
        node.name: {item.name for item in node.body if isinstance(item, ast.FunctionDef)}
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


class TestSpec101(unittest.TestCase):
    def setUp(self):
        self.spec = read(os.path.join(SPEC_DIR, "spec.md"))
        self.trace = json.loads(read(os.path.join(SPEC_DIR, "traceability.json")))

    def test_headings_and_scenarios(self):
        self.assertIn("**Spec**: SPEC-101", self.spec)
        for heading in REQUIRED_HEADINGS:
            with self.subTest(heading=heading):
                self.assertRegex(self.spec, r"(?m)^%s\b" % re.escape(heading))
        self.assertRegex(self.spec, r"\*\*Given\*\* .+\*\*When\*\* .+\*\*Then\*\*")
        self.assertRegex(self.spec, r"\*\*SC-001\*\*")

    def test_requirements_match_traceability(self):
        in_spec = re.findall(r"\*\*(FR-\d{3})\*\*", self.spec)
        self.assertEqual(self.trace["spec"], "SPEC-101")
        self.assertEqual(in_spec, [item["id"] for item in self.trace["requirements"]])
        self.assertEqual(in_spec, ["FR-%03d" % n for n in range(1, len(in_spec) + 1)], "numbered without gaps")

    def test_paths_and_test_ids_resolve(self):
        for item in self.trace["requirements"]:
            with self.subTest(requirement=item["id"]):
                self.assertTrue(item["implemented_by"])
                self.assertTrue(item["verified_by"])
                for path in item["implemented_by"]:
                    self.assertTrue(os.path.exists(os.path.join(fx.REPO_ROOT, path)), path)
                for test_id in item["verified_by"]:
                    file_part, class_name, method = test_id.split("::")
                    methods = test_methods(os.path.join(fx.REPO_ROOT, file_part)).get(class_name, set())
                    self.assertIn(method, methods, test_id)

    def test_rule_catalog_lists_every_rule_the_validator_emits(self):
        emitted = set(RULE_LITERAL.findall(read(VALIDATE_SOURCE))) - {"spec.md"} | set(DYNAMIC_RULES)
        catalog = self.spec.split("## Rule catalog", 1)[1].split("\n## ", 1)[0]
        documented = set(re.findall(r"`([a-z]+\.[a-z0-9-]+)`", catalog))
        self.assertEqual(sorted(emitted - documented), [])

    def test_every_documented_rule_has_a_test(self):
        catalog = self.spec.split("## Rule catalog", 1)[1].split("\n## ", 1)[0]
        documented = set(re.findall(r"`([a-z]+\.[a-z0-9-]+)`", catalog)) - {"lab.validate"}
        tests_dir = os.path.join(fx.LAB_ROOT, "tests")
        test_text = "\n".join(
            read(os.path.join(tests_dir, name)) for name in os.listdir(tests_dir) if name.startswith("test_lab_core_")
        )
        self.assertEqual(sorted(rule for rule in documented if '"%s"' % rule not in test_text), [])


if __name__ == "__main__":
    unittest.main()
