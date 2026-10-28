"""Tests for _skillkit.assertions: every benchmark assertion operator."""

from __future__ import annotations

import unittest

from tests import skillkit_support  # noqa: F401
from _skillkit import assertions as asr
from _skillkit.assertions import InvalidAssertion, evaluate

DOC = {
    "ok": False,
    "errors": [{"code": "CHECK_NOT_EXECUTED", "message": "unit has no command", "path": "/checks/0"}],
    "payload": {
        "result": "CHANGES_REQUESTED",
        "count": 3,
        "ratio": 0.75,
        "flag": True,
        "none": None,
        "tags": ["guardrail", "evidence"],
        "map": {"AC-01": "passed"},
        "empty": [],
    },
}


def check(op, path, value=None, **extra):
    assertion = {"path": path, "op": op}
    if value is not None or "value_is_none" in extra:
        assertion["value"] = value
    return evaluate(DOC, assertion)


class TestEquality(unittest.TestCase):
    def test_eq_ne(self):
        self.assertEqual(check("eq", "/errors/0/code", "CHECK_NOT_EXECUTED"), (True, "CHECK_NOT_EXECUTED"))
        self.assertEqual(check("eq", "/payload/count", 3.0), (True, 3))
        self.assertFalse(check("eq", "/payload/flag", 1)[0], "true is not 1")
        self.assertTrue(check("eq", "/payload/map", {"AC-01": "passed"})[0])
        self.assertTrue(check("ne", "/payload/result", "APPROVE")[0])
        self.assertFalse(check("ne", "/payload/count", 3)[0])

    def test_eq_null(self):
        self.assertEqual(check("eq", "/payload/none", None, value_is_none=True), (True, None))

    def test_in_not_in(self):
        self.assertTrue(check("in", "/payload/result", ["APPROVE", "CHANGES_REQUESTED"])[0])
        self.assertFalse(check("in", "/payload/result", ["APPROVE"])[0])
        self.assertTrue(check("not_in", "/payload/result", ["APPROVE"])[0])
        self.assertFalse(check("not_in", "/payload/count", [3.0])[0])


class TestContainment(unittest.TestCase):
    def test_contains(self):
        self.assertTrue(check("contains", "/errors/0/message", "no command")[0])
        self.assertTrue(check("contains", "/payload/tags", "guardrail")[0])
        self.assertTrue(check("contains", "/payload/map", "AC-01")[0])
        self.assertFalse(check("contains", "/payload/tags", "missing")[0])
        self.assertFalse(check("contains", "/payload/count", 3)[0], "scalars contain nothing")
        self.assertFalse(check("contains", "/errors/0/message", 5)[0])

    def test_not_contains(self):
        self.assertTrue(check("not_contains", "/payload/tags", "missing")[0])
        self.assertFalse(check("not_contains", "/payload/tags", "evidence")[0])
        self.assertFalse(check("not_contains", "/payload/count", 1)[0], "type mismatch fails, never passes")

    def test_regex(self):
        self.assertTrue(check("regex", "/errors/0/code", "^CHECK_")[0])
        self.assertTrue(check("regex", "/errors/0/message", "command$")[0])
        self.assertFalse(check("regex", "/payload/count", "3")[0], "regex never coerces")


class TestNumeric(unittest.TestCase):
    def test_comparisons(self):
        self.assertTrue(check("gte", "/payload/ratio", 0.75)[0])
        self.assertFalse(check("gt", "/payload/ratio", 0.75)[0])
        self.assertTrue(check("lte", "/payload/count", 3)[0])
        self.assertTrue(check("lt", "/payload/count", 3.5)[0])
        self.assertFalse(check("gte", "/payload/result", 0)[0], "strings are not numbers")
        self.assertFalse(check("gte", "/payload/flag", 0)[0], "booleans are not numbers")


class TestLength(unittest.TestCase):
    def test_length_ops_return_the_length(self):
        self.assertEqual(check("len_eq", "/errors", 1), (True, 1))
        self.assertEqual(check("len_gte", "/payload/tags", 2), (True, 2))
        self.assertEqual(check("len_lte", "/payload/empty", 0), (True, 0))
        self.assertEqual(check("len_eq", "/payload/result", 17), (True, 17))
        self.assertEqual(check("len_eq", "/payload/map", 1), (True, 1))
        self.assertEqual(check("len_gte", "/payload/count", 0), (False, None))


class TestPresenceAndType(unittest.TestCase):
    def test_exists_not_exists(self):
        self.assertEqual(evaluate(DOC, {"path": "/payload/none", "op": "exists"}), (True, None))
        self.assertEqual(evaluate(DOC, {"path": "/payload/missing", "op": "exists"}), (False, None))
        self.assertEqual(evaluate(DOC, {"path": "/payload/missing", "op": "not_exists"}), (True, None))
        self.assertEqual(evaluate(DOC, {"path": "/ok", "op": "not_exists"}), (False, False))

    def test_missing_path_fails_every_other_op(self):
        for op, value in (
            ("eq", 1),
            ("ne", 1),
            ("in", [1]),
            ("not_in", [1]),
            ("contains", "x"),
            ("not_contains", "x"),
            ("regex", "x"),
            ("gte", 1),
            ("lte", 1),
            ("gt", 1),
            ("lt", 1),
            ("len_eq", 0),
            ("len_gte", 0),
            ("len_lte", 0),
            ("type", "null"),
        ):
            with self.subTest(op=op):
                self.assertEqual(evaluate(DOC, {"path": "/errors/9/code", "op": op, "value": value}), (False, None))

    def test_type(self):
        cases = [
            ("/payload", "object"),
            ("/payload/tags", "array"),
            ("/payload/result", "string"),
            ("/payload/ratio", "number"),
            ("/payload/count", "number"),
            ("/payload/count", "integer"),
            ("/payload/flag", "boolean"),
            ("/payload/none", "null"),
        ]
        for path, type_name in cases:
            with self.subTest(path=path, type_name=type_name):
                self.assertTrue(check("type", path, type_name)[0])
        self.assertFalse(check("type", "/payload/flag", "integer")[0])
        self.assertTrue(check("type", "/payload/none", ["string", "null"])[0])
        self.assertTrue(evaluate({"x": 2.0}, {"path": "/x", "op": "type", "value": "integer"})[0])

    def test_root_pointer(self):
        self.assertTrue(evaluate(DOC, {"path": "", "op": "type", "value": "object"})[0])


class TestInvalidAssertions(unittest.TestCase):
    def test_malformed_assertions_raise(self):
        cases = [
            "not a dict",
            {"op": "eq", "value": 1},
            {"path": "/x", "op": "approximately", "value": 1},
            {"path": "/x", "op": "eq"},
            {"path": "/x", "op": "in", "value": "abc"},
            {"path": "/x", "op": "gte", "value": "1"},
            {"path": "/x", "op": "gte", "value": True},
            {"path": "/x", "op": "len_eq", "value": -1},
            {"path": "/x", "op": "len_eq", "value": 1.5},
            {"path": "/x", "op": "regex", "value": "("},
            {"path": "/x", "op": "regex", "value": 3},
            {"path": "/x", "op": "type", "value": "int"},
            {"path": "/x", "op": "type", "value": []},
            {"path": "x", "op": "exists"},
        ]
        for assertion in cases:
            with self.subTest(assertion=assertion), self.assertRaises(InvalidAssertion):
                evaluate(DOC, assertion)

    def test_ops_match_conventions(self):
        self.assertEqual(
            asr.OPS,
            (
                "eq",
                "ne",
                "in",
                "not_in",
                "contains",
                "not_contains",
                "regex",
                "gte",
                "lte",
                "gt",
                "lt",
                "len_eq",
                "len_gte",
                "len_lte",
                "exists",
                "not_exists",
                "type",
            ),
        )


class TestEvaluateAll(unittest.TestCase):
    def test_records(self):
        records = asr.evaluate_all(
            DOC,
            [
                {"path": "/ok", "op": "eq", "value": False},
                {"path": "/errors", "op": "len_gte", "value": 2},
            ],
        )
        self.assertEqual(
            records,
            [
                {"path": "/ok", "op": "eq", "passed": True, "actual": False},
                {"path": "/errors", "op": "len_gte", "passed": False, "actual": 1},
            ],
        )


if __name__ == "__main__":
    unittest.main()
