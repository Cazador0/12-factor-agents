"""Package-level rules for _skillkit: stdlib-only, Python 3.9 syntax, no unsafe calls."""

from __future__ import annotations

import ast
import json
import os
import subprocess
import sys
import unittest

from tests import skillkit_support
import _skillkit
from _skillkit import stdlib_modules

EXPECTED_MODULES = {
    "__init__",
    "assertions",
    "cli",
    "envelope",
    "frontmatter",
    "fsutil",
    "ids",
    "jsonpointer",
    "jsonschema_mini",
    "redact",
    "schemas",
    "stdlib_modules",
    "timeutil",
}
TYPE_NAMES = {"int", "str", "float", "bool", "bytes", "list", "dict", "tuple", "set", "frozenset", "type", "object"}


def module_sources():
    for filename in sorted(os.listdir(skillkit_support.SKILLKIT_DIR)):
        if filename.endswith(".py"):
            path = os.path.join(skillkit_support.SKILLKIT_DIR, filename)
            with open(path, "r", encoding="utf-8") as handle:
                yield filename[:-3], path, handle.read()


class TestPackageConstants(unittest.TestCase):
    def test_version_and_exit_codes(self):
        self.assertRegex(_skillkit.SKILLKIT_VERSION, r"^\d+\.\d+\.\d+$")
        self.assertEqual(_skillkit.SKILLKIT_VERSION, "0.1.0")
        self.assertEqual(
            (
                _skillkit.EXIT_OK,
                _skillkit.EXIT_FAIL,
                _skillkit.EXIT_USAGE,
                _skillkit.EXIT_EXTERNAL,
                _skillkit.EXIT_REFUSED,
            ),
            (0, 1, 2, 3, 4),
        )
        self.assertEqual(_skillkit.EXIT_CODES, (0, 1, 2, 3, 4))

    def test_module_inventory(self):
        """The SPEC-100 modules exist; later specs may add modules, which the source rules below also cover."""
        self.assertLessEqual(EXPECTED_MODULES, {name for name, _, _ in module_sources()})

    def test_root_import_is_light(self):
        probe = (
            "import sys; sys.path.insert(0, sys.argv[1]); import _skillkit, json;"
            "print(json.dumps(sorted(m for m in sys.modules if m.startswith('_skillkit.'))))"
        )
        output = subprocess.run(
            [sys.executable, "-I", "-c", probe, skillkit_support.SHARED_DIR], check=True, capture_output=True, text=True
        ).stdout
        self.assertEqual(json.loads(output), [])


class TestSourceRules(unittest.TestCase):
    def test_docstring_then_future_import(self):
        for name, _, source in module_sources():
            with self.subTest(module=name):
                tree = ast.parse(source)
                self.assertIsInstance(tree.body[0], ast.Expr, "module docstring first")
                self.assertTrue(ast.get_docstring(tree))
                second = tree.body[1]
                self.assertIsInstance(second, ast.ImportFrom)
                self.assertEqual((second.module, [a.name for a in second.names]), ("__future__", ["annotations"]))

    def test_python39_grammar(self):
        for name, path, source in module_sources():
            with self.subTest(module=name):
                ast.parse(source, filename=path, feature_version=(3, 9))

    def test_no_runtime_pep604_unions(self):
        for name, _, source in module_sources():
            tree = ast.parse(source)
            annotation_nodes = set()
            for node in ast.walk(tree):
                for field in ("annotation", "returns"):
                    value = getattr(node, field, None)
                    if value is not None:
                        annotation_nodes.update(id(n) for n in ast.walk(value))
            for node in ast.walk(tree):
                if isinstance(node, ast.BinOp) and isinstance(node.op, ast.BitOr) and id(node) not in annotation_nodes:
                    sides = (node.left, node.right)
                    typeish = any(
                        (isinstance(s, ast.Name) and s.id in TYPE_NAMES)
                        or (isinstance(s, ast.Constant) and s.value is None)
                        for s in sides
                    )
                    with self.subTest(module=name, line=node.lineno):
                        self.assertFalse(typeish, "X | Y type union outside an annotation breaks Python 3.9")

    def test_imports_are_portable_stdlib_or_relative(self):
        for name, _, source in module_sources():
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Import):
                    modules = [alias.name for alias in node.names]
                elif isinstance(node, ast.ImportFrom) and node.level == 0:
                    modules = [node.module]
                else:
                    continue
                for module in modules:
                    with self.subTest(module=name, imports=module):
                        self.assertTrue(stdlib_modules.is_portable_stdlib(module), module)

    def test_no_eval_exec_or_shell(self):
        for name, _, source in module_sources():
            for node in ast.walk(ast.parse(source)):
                if isinstance(node, ast.Call):
                    func = node.func
                    with self.subTest(module=name, line=node.lineno):
                        self.assertFalse(isinstance(func, ast.Name) and func.id in ("eval", "exec", "compile"))
                        for keyword in node.keywords:
                            self.assertFalse(
                                keyword.arg == "shell"
                                and isinstance(keyword.value, ast.Constant)
                                and keyword.value.value is True
                            )

    def test_no_python310_only_apis(self):
        """Attributes and call forms that do not exist on Python 3.9 (getattr fallbacks are fine)."""
        forbidden_attributes = {("itertools", "pairwise"), ("sys", "stdlib_module_names"), ("int", "bit_count")}
        for name, _, source in module_sources():
            for node in ast.walk(ast.parse(source)):
                with self.subTest(module=name, line=getattr(node, "lineno", 0)):
                    if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Name):
                        self.assertNotIn((node.value.id, node.attr), forbidden_attributes)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                        self.assertNotIn(node.func.id, ("aiter", "anext"))
                        if node.func.id == "zip":
                            self.assertNotIn("strict", [k.arg for k in node.keywords])


if __name__ == "__main__":
    unittest.main()
