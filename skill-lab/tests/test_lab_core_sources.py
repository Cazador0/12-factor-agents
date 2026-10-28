"""The lab's own code follows the rules it enforces (SPEC-101 FR-027): Python 3.9, stdlib only, no shell.

Also checks the scaffold template renders with only known placeholders and that
``skill-lab validate`` runs on the real repository without crashing.
"""

from __future__ import annotations

import ast
import json
import os
import unittest

from tests import test_lab_core_fixtures as fx

from _skillkit import envelope, stdlib_modules
from lab import paths, scaffold, validate

LAB_DIR = os.path.join(fx.LAB_ROOT, "lab")
BIN = os.path.join(fx.LAB_ROOT, "bin", "skill-lab")
OWN_MODULES = ("__init__", "catalog", "cli", "doctor", "install", "paths", "scaffold", "sync", "testrun", "validate")
TYPE_NAMES = frozenset({"str", "int", "float", "bool", "bytes", "dict", "list", "tuple", "set", "frozenset", "type"})


def sources():
    files = [os.path.join(LAB_DIR, name + ".py") for name in OWN_MODULES] + [BIN]
    for path in files:
        with open(path, encoding="utf-8") as handle:
            yield path, handle.read()


def annotation_nodes(tree):
    """Every node inside an annotation (those are strings at runtime under PEP 563)."""
    found = set()
    for node in ast.walk(tree):
        roots = []
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)) and node.returns is not None:
            roots.append(node.returns)
        elif isinstance(node, ast.arg) and node.annotation is not None:
            roots.append(node.annotation)
        elif isinstance(node, ast.AnnAssign):
            roots.append(node.annotation)
        for root in roots:
            found.update(id(child) for child in ast.walk(root))
    return found


def is_type_like(node):
    return (isinstance(node, ast.Name) and node.id in TYPE_NAMES) or (
        isinstance(node, ast.Constant) and node.value is None
    )


class TestLabSources(unittest.TestCase):
    def test_python39_grammar_docstring_and_future_import(self):
        for path, text in sources():
            with self.subTest(path=os.path.basename(path)):
                tree = ast.parse(text, feature_version=(3, 9))
                self.assertIsNotNone(ast.get_docstring(tree))
                self.assertTrue(validate._has_future_annotations(tree))

    def test_imports_are_stdlib_lab_or_skillkit(self):
        for path, text in sources():
            tree = ast.parse(text)
            for node in ast.walk(tree):
                if isinstance(node, ast.Import):
                    names = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    names = [node.module]
                else:
                    continue
                for name in names:
                    with self.subTest(path=os.path.basename(path), module=name):
                        top = stdlib_modules.top_level(name)
                        self.assertTrue(top in ("lab", "_skillkit") or stdlib_modules.is_portable_stdlib(name), name)

    def test_no_shell_eval_exec_or_runtime_unions(self):
        for path, text in sources():
            tree = ast.parse(text)
            skip = annotation_nodes(tree)
            for node in ast.walk(tree):
                where = "%s:%d" % (os.path.basename(path), getattr(node, "lineno", 0))
                if isinstance(node, ast.Call):
                    self.assertFalse(isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"), where)
                    for keyword in node.keywords:
                        self.assertFalse(keyword.arg == "shell", where)
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr) and id(node) not in skip:
                    self.assertFalse(
                        is_type_like(node.left) or is_type_like(node.right), "runtime X | Y union at " + where
                    )

    def test_bin_is_executable(self):
        self.assertTrue(os.access(BIN, os.X_OK))


class TestTemplate(unittest.TestCase):
    VALUES = {
        "name": "demo-skill",
        "title": "Demo Skill",
        "description": "d",
        "family": "meta",
        "spec_id": "SPEC-001",
        "spec_number": "001",
        "spec_dir": "skill-lab/specs/001-demo-skill",
        "author": "a",
        "date": "2026-10-22",
    }

    def test_every_template_renders_with_known_placeholders(self):
        layout = paths.Layout.at(fx.REPO_ROOT)
        for source, _area, destination in scaffold.template_files(layout):
            with self.subTest(template=destination):
                with open(source, encoding="utf-8") as handle:
                    text = scaffold.render_text(handle.read(), self.VALUES, source=source)
                self.assertNotIn("{{", text)
                if destination.endswith(".py"):
                    ast.parse(text, feature_version=(3, 9))
                elif destination.endswith(".json") and not destination.endswith("malformed.json"):
                    json.loads(text)

    def test_placeholder_list_in_readme_matches_the_scaffold(self):
        with open(os.path.join(fx.LAB_ROOT, "templates", "skill", "_README.md"), encoding="utf-8") as handle:
            readme = handle.read()
        for key in self.VALUES:
            self.assertIn("{{%s}}" % key, readme)


class TestRealRepository(unittest.TestCase):
    def test_validate_runs_on_this_repository(self):
        code, result = fx.run(validate.main, ["--no-run"])
        self.assertIn(code, (0, 1))
        self.assertEqual(result["kind"], "validation-report")
        self.assertEqual(result["producer"], {"skill": "skill-lab", "script": "validate", "version": "0.1.0"})
        self.assertEqual(result["schema"], envelope.ENVELOPE_SCHEMA)


if __name__ == "__main__":
    unittest.main()
