"""Tests for _skillkit.jsonpointer (RFC 6901)."""

from __future__ import annotations

import unittest

from tests import skillkit_support  # noqa: F401
from _skillkit import jsonpointer as jp


class TestResolve(unittest.TestCase):
    # The example document from RFC 6901 section 5.
    DOC = {"foo": ["bar", "baz"], "": 0, "a/b": 1, "c%d": 2, "e^f": 3, "g|h": 4, "i\\j": 5, 'k"l': 6, " ": 7, "m~n": 8}

    def test_rfc6901_examples(self):
        cases = {
            "": self.DOC,
            "/foo": ["bar", "baz"],
            "/foo/0": "bar",
            "/": 0,
            "/a~1b": 1,
            "/c%d": 2,
            "/e^f": 3,
            "/g|h": 4,
            "/i\\j": 5,
            '/k"l': 6,
            "/ ": 7,
            "/m~0n": 8,
        }
        for pointer, expected in cases.items():
            with self.subTest(pointer=pointer):
                self.assertEqual(jp.resolve(self.DOC, pointer), expected)

    def test_tilde_decoding_order(self):
        self.assertEqual(jp.resolve({"~1": "x"}, "/~01"), "x")

    def test_missing_member_and_index(self):
        for pointer in ("/nope", "/foo/2", "/foo/-", "/foo/01", "/foo/x", "/foo/0/deeper", "/foo/-1"):
            with self.subTest(pointer=pointer), self.assertRaises(jp.PointerError):
                jp.resolve(self.DOC, pointer)

    def test_syntax_errors(self):
        for pointer in ("foo", "#/foo", "/a~2", "/a~"):
            with self.subTest(pointer=pointer), self.assertRaises(jp.PointerSyntaxError):
                jp.resolve(self.DOC, pointer)
        with self.assertRaises(jp.PointerSyntaxError):
            jp.resolve(self.DOC, 5)

    def test_syntax_error_is_also_a_pointer_error(self):
        self.assertTrue(issubclass(jp.PointerSyntaxError, jp.PointerError))

    def test_null_values_resolve(self):
        self.assertIsNone(jp.resolve({"a": None}, "/a"))


class TestExistsAndHelpers(unittest.TestCase):
    def test_exists(self):
        doc = {"errors": [{"code": "X", "path": None}]}
        self.assertTrue(jp.exists(doc, "/errors/0/path"))
        self.assertFalse(jp.exists(doc, "/errors/1"))
        self.assertTrue(jp.exists(doc, ""))

    def test_exists_propagates_syntax_errors(self):
        with self.assertRaises(jp.PointerSyntaxError):
            jp.exists({}, "errors")

    def test_escape_join_split(self):
        self.assertEqual(jp.escape("a/b~c"), "a~1b~0c")
        self.assertEqual(jp.join("/payload", "a/b", 0), "/payload/a~1b/0")
        self.assertEqual(jp.join("", "x"), "/x")
        self.assertEqual(jp.split("/a~1b/~0/"), ["a/b", "~", ""])
        self.assertEqual(jp.split(""), [])


if __name__ == "__main__":
    unittest.main()
