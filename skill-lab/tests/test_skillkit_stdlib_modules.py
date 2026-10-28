"""Tests for _skillkit.stdlib_modules: stdlib detection with a Python 3.9 fallback."""

from __future__ import annotations

import sys
import types
import unittest
from unittest import mock

from tests import skillkit_support  # noqa: F401
from _skillkit import stdlib_modules as sm

# Top-level modules that existed in 3.9 and were removed later (PEP 594 and friends).
REMOVED_AFTER_39 = {
    "_bootlocale",
    "_peg_parser",
    "binhex",
    "formatter",
    "parser",
    "symbol",
    "asynchat",
    "asyncore",
    "distutils",
    "imp",
    "smtpd",
    "aifc",
    "audioop",
    "cgi",
    "cgitb",
    "chunk",
    "crypt",
    "imghdr",
    "mailcap",
    "msilib",
    "nis",
    "nntplib",
    "ossaudiodev",
    "pipes",
    "sndhdr",
    "spwd",
    "sunau",
    "telnetlib",
    "uu",
    "xdrlib",
    "lib2to3",
    "_crypt",
    "_msi",
    "_sha256",
    "_sha512",
    "_bootsubprocess",
    "_compression",
}


class TestIsStdlib(unittest.TestCase):
    def test_common_modules(self):
        for name in (
            "os",
            "os.path",
            "json",
            "argparse",
            "typing",
            "__future__",
            "urllib.request",
            "http.server",
            "unittest.mock",
            "fcntl",
            "msvcrt",
            "winreg",
            "sys",
            "builtins",
        ):
            with self.subTest(name=name):
                self.assertTrue(sm.is_stdlib(name))

    def test_third_party_and_invalid(self):
        for name in ("requests", "yaml", "jsonschema", "pydantic", "_skillkit", "", ".relative", "typesafe_sdk"):
            with self.subTest(name=name):
                self.assertFalse(sm.is_stdlib(name))

    def test_fallback_without_stdlib_module_names(self):
        fake_sys = types.SimpleNamespace(builtin_module_names=("sys", "builtins"))
        with mock.patch.object(sm, "sys", fake_sys):
            self.assertTrue(sm.is_stdlib("graphlib"))
            self.assertTrue(sm.is_stdlib("distutils.core"))
            self.assertFalse(sm.is_stdlib("tomllib"), "tomllib arrived in 3.11")
            self.assertFalse(sm.is_stdlib("requests"))
            self.assertEqual(sm.current_stdlib_modules(), sm.PY39_STDLIB_MODULES | {"sys", "builtins"})

    def test_portable_requires_python39_and_current(self):
        self.assertTrue(sm.is_portable_stdlib("json"))
        self.assertFalse(sm.is_portable_stdlib("tomllib"))
        if sys.version_info >= (3, 12):
            self.assertFalse(sm.is_portable_stdlib("distutils"), "gone in 3.12")

    def test_known_stdlib_does_not_depend_on_the_interpreter(self):
        fake_sys = types.SimpleNamespace(builtin_module_names=("sys", "builtins"))
        with mock.patch.object(sm, "sys", fake_sys):  # a Python 3.9 without the newer modules
            for name in ("tomllib", "annotationlib", "compression.zstd", "distutils", "json"):
                with self.subTest(name=name):
                    self.assertTrue(sm.is_known_stdlib(name))
            self.assertFalse(sm.is_portable_stdlib("tomllib"))
        for name in ("requests", "_skillkit", "", ".relative"):
            with self.subTest(name=name):
                self.assertFalse(sm.is_known_stdlib(name))

    def test_top_level(self):
        self.assertEqual(sm.top_level("a.b.c"), "a")
        self.assertEqual(sm.top_level("a"), "a")


class TestPython39List(unittest.TestCase):
    def test_list_shape(self):
        self.assertEqual(len(sm.PY39_STDLIB_MODULES), 308)
        for name in ("__future__", "typing", "graphlib", "zoneinfo", "asyncio", "_json", "nt", "posix"):
            with self.subTest(name=name):
                self.assertIn(name, sm.PY39_STDLIB_MODULES)
        for name in ("tomllib", "_tokenize", "_typing", "__main__", "test"):
            with self.subTest(name=name):
                self.assertNotIn(
                    name, sm.PY39_STDLIB_MODULES, "newer modules, __main__ and the test suite are excluded"
                )

    @unittest.skipUnless(hasattr(sys, "stdlib_module_names"), "needs Python 3.10+")
    def test_consistent_with_running_interpreter(self):
        current = set(sys.stdlib_module_names)
        unexplained = sm.PY39_STDLIB_MODULES - current - REMOVED_AFTER_39
        self.assertEqual(unexplained, set(), "3.9 modules missing from this Python must be known removals")
        unlisted = current - sm.PY39_STDLIB_MODULES - sm.POST_PY39_STDLIB_MODULES
        self.assertEqual(unlisted, set(), "modules added since 3.9 must be in POST_PY39_STDLIB_MODULES")

    def test_post_39_list_holds_only_newer_modules(self):
        self.assertEqual(sm.PY39_STDLIB_MODULES & sm.POST_PY39_STDLIB_MODULES, frozenset())
        self.assertIn("tomllib", sm.POST_PY39_STDLIB_MODULES)
        self.assertFalse({"__main__", "test"} & sm.POST_PY39_STDLIB_MODULES)


if __name__ == "__main__":
    unittest.main()
