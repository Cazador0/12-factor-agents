"""Tests for _skillkit.jsonschema_mini: every supported keyword and its edge cases."""

from __future__ import annotations

import unittest

from tests import skillkit_support  # noqa: F401  (puts _skillkit on sys.path)
from _skillkit import jsonschema_mini as js
from _skillkit.jsonschema_mini import Issue, SchemaError, validate


def keywords(issues):
    return [issue.keyword for issue in issues]


class TestTypeKeyword(unittest.TestCase):
    def test_each_json_type(self):
        samples = {
            "object": {},
            "array": [],
            "string": "",
            "number": 1.5,
            "integer": 3,
            "boolean": True,
            "null": None,
        }
        for type_name, value in samples.items():
            with self.subTest(type_name=type_name):
                self.assertEqual(validate(value, {"type": type_name}), [])

    def test_booleans_are_not_integers_or_numbers(self):
        self.assertEqual(keywords(validate(True, {"type": "integer"})), ["type"])
        self.assertEqual(keywords(validate(False, {"type": "number"})), ["type"])

    def test_integral_float_is_an_integer(self):
        self.assertEqual(validate(1.0, {"type": "integer"}), [])
        self.assertEqual(keywords(validate(1.5, {"type": "integer"})), ["type"])

    def test_integer_is_a_number(self):
        self.assertEqual(validate(7, {"type": "number"}), [])

    def test_type_list(self):
        schema = {"type": ["string", "null"]}
        self.assertEqual(validate(None, schema), [])
        self.assertEqual(validate("x", schema), [])
        issues = validate(3, schema)
        self.assertEqual(keywords(issues), ["type"])
        self.assertIn("one of string, null", issues[0].message)

    def test_tuple_is_an_array(self):
        self.assertEqual(validate(("a",), {"type": "array"}), [])

    def test_invalid_type_value_is_a_schema_error(self):
        with self.assertRaises(SchemaError):
            validate(1, {"type": "int"})
        with self.assertRaises(SchemaError):
            validate(1, {"type": []})


class TestEnumConst(unittest.TestCase):
    def test_enum(self):
        schema = {"enum": ["APPROVE", "CHANGES_REQUESTED"]}
        self.assertEqual(validate("APPROVE", schema), [])
        self.assertEqual(keywords(validate("approve", schema)), ["enum"])

    def test_enum_with_null(self):
        self.assertEqual(validate(None, {"enum": ["a", None]}), [])

    def test_const_uses_json_equality(self):
        self.assertEqual(validate(1.0, {"const": 1}), [])
        self.assertEqual(keywords(validate(True, {"const": 1})), ["const"])
        self.assertEqual(keywords(validate(0, {"const": False})), ["const"])
        self.assertEqual(validate({"b": [1, 2], "a": None}, {"const": {"a": None, "b": [1.0, 2]}}), [])
        self.assertEqual(keywords(validate([1, 2], {"const": [2, 1]})), ["const"])

    def test_enum_must_be_an_array(self):
        with self.assertRaises(SchemaError):
            validate("a", {"enum": "a"})


class TestNumericKeywords(unittest.TestCase):
    def test_minimum_maximum_inclusive(self):
        schema = {"minimum": 0, "maximum": 3}
        for value in (0, 3, 1.5):
            self.assertEqual(validate(value, schema), [])
        self.assertEqual(keywords(validate(-1, schema)), ["minimum"])
        self.assertEqual(keywords(validate(3.01, schema)), ["maximum"])

    def test_exclusive_bounds(self):
        schema = {"exclusiveMinimum": 0.35, "exclusiveMaximum": 1}
        self.assertEqual(validate(0.5, schema), [])
        self.assertEqual(keywords(validate(0.35, schema)), ["exclusiveMinimum"])
        self.assertEqual(keywords(validate(1, schema)), ["exclusiveMaximum"])

    def test_numeric_keywords_ignore_other_types(self):
        schema = {"minimum": 5}
        self.assertEqual(validate("1", schema), [])
        self.assertEqual(validate(True, schema), [], "booleans are not numbers")

    def test_bad_limit_is_a_schema_error(self):
        with self.assertRaises(SchemaError):
            validate(1, {"minimum": "0"})


class TestStringKeywords(unittest.TestCase):
    def test_length_counts_code_points(self):
        schema = {"minLength": 2, "maxLength": 2}
        self.assertEqual(validate("\U0001f600é", schema), [])
        self.assertEqual(keywords(validate("a", schema)), ["minLength"])
        self.assertEqual(keywords(validate("abc", schema)), ["maxLength"])

    def test_pattern_is_an_unanchored_search(self):
        self.assertEqual(validate("xxT001yy", {"pattern": "T[0-9]{3}"}), [])
        self.assertEqual(keywords(validate("T01", {"pattern": "^T[0-9]{3,}$"})), ["pattern"])

    def test_pattern_digit_class_is_ascii(self):
        bengali_four = "৪"
        self.assertEqual(keywords(validate("T00" + bengali_four, {"pattern": "^T\\d{3}$"})), ["pattern"])

    def test_string_keywords_ignore_other_types(self):
        self.assertEqual(validate(12, {"pattern": "^a$", "minLength": 5}), [])

    def test_invalid_pattern_is_a_schema_error(self):
        with self.assertRaises(SchemaError):
            validate("a", {"pattern": "("})
        with self.assertRaises(SchemaError):
            validate("a", {"pattern": 5})

    def test_bad_length_is_a_schema_error(self):
        with self.assertRaises(SchemaError):
            validate("a", {"minLength": -1})
        with self.assertRaises(SchemaError):
            validate("a", {"maxLength": True})


class TestFormatDateTime(unittest.TestCase):
    VALID = [
        "2026-10-22T08:00:00Z",
        "2026-10-22T08:00:00.123456Z",
        "2026-10-22T08:00:00+05:30",
        "2026-10-22T08:00:00-00:00",
        "2026-10-22t08:00:00z",
        "2024-02-29T00:00:00Z",
        "1998-12-31T23:59:60Z",
        "1998-12-31T15:59:60.123-08:00",
    ]
    INVALID = [
        "2026-10-22",
        "2026-10-22T08:00:00",
        "2026-10-22 08:00:00Z",
        "2026-13-01T00:00:00Z",
        "2026-02-29T00:00:00Z",
        "2026-04-31T00:00:00Z",
        "2026-10-22T24:00:00Z",
        "2026-10-22T08:60:00Z",
        "1998-12-31T23:59:61Z",
        "1998-12-31T23:58:60Z",
        "1998-12-31T22:59:60Z",
        "2026-10-22T08:00:00+24:00",
        "2026-10-22T08:00:00+05:60",
        "2026-10-22T08:00:00.Z",
        "2026-10-2৪T08:00:00Z",
        "not a date",
        "",
    ]

    def test_valid(self):
        for value in self.VALID:
            with self.subTest(value=value):
                self.assertEqual(validate(value, {"format": "date-time"}), [])

    def test_invalid(self):
        for value in self.INVALID:
            with self.subTest(value=value):
                self.assertEqual(keywords(validate(value, {"format": "date-time"})), ["format"])

    def test_format_ignores_non_strings_and_other_formats(self):
        self.assertEqual(validate(5, {"format": "date-time"}), [])
        self.assertEqual(validate("nope", {"format": "email"}), [])


class TestArrayKeywords(unittest.TestCase):
    def test_items(self):
        schema = {"items": {"type": "integer"}}
        self.assertEqual(validate([1, 2], schema), [])
        issues = validate([1, "x", 3, None], schema)
        self.assertEqual([i.path for i in issues], ["/1", "/3"])

    def test_prefix_items_then_items(self):
        schema = {"prefixItems": [{"const": "a"}, {"const": "b"}], "items": {"type": "integer"}}
        self.assertEqual(validate(["a", "b", 1, 2], schema), [])
        self.assertEqual(validate(["a"], schema), [], "shorter arrays are fine")
        issues = validate(["a", "x", "y"], schema)
        self.assertEqual([(i.path, i.keyword) for i in issues], [("/1", "const"), ("/2", "type")])

    def test_items_false_forbids_extra_items(self):
        schema = {"prefixItems": [{"type": "string"}], "items": False}
        self.assertEqual(validate(["a"], schema), [])
        self.assertEqual(keywords(validate(["a", "b"], schema)), ["false"])

    def test_min_max_items(self):
        schema = {"minItems": 1, "maxItems": 2}
        self.assertEqual(keywords(validate([], schema)), ["minItems"])
        self.assertEqual(keywords(validate([1, 2, 3], schema)), ["maxItems"])

    def test_unique_items_uses_json_equality(self):
        schema = {"uniqueItems": True}
        self.assertEqual(keywords(validate([1, 1.0], schema)), ["uniqueItems"])
        self.assertEqual(validate([1, True], schema), [], "true is not 1")
        self.assertEqual(validate([0, False], schema), [])
        self.assertEqual(keywords(validate([{"a": 1, "b": 2}, {"b": 2, "a": 1}], schema)), ["uniqueItems"])
        self.assertEqual(validate([[1, 2], [2, 1]], schema), [])
        self.assertEqual(validate([1, 1], {"uniqueItems": False}), [])

    def test_array_keywords_ignore_other_types(self):
        self.assertEqual(validate("abc", {"items": {"type": "integer"}, "minItems": 5}), [])

    def test_items_must_be_a_schema(self):
        with self.assertRaises(SchemaError):
            validate([1], {"items": [{"type": "integer"}]})


class TestObjectKeywords(unittest.TestCase):
    SCHEMA = {
        "type": "object",
        "required": ["id", "name"],
        "properties": {"id": {"type": "integer"}, "name": {"type": "string"}},
        "additionalProperties": False,
    }

    def test_valid_object(self):
        self.assertEqual(validate({"id": 1, "name": "x"}, self.SCHEMA), [])

    def test_required_points_at_the_missing_member(self):
        issues = validate({"id": 1}, self.SCHEMA)
        self.assertEqual(issues, [Issue("/name", "required", "required property 'name' is missing")])

    def test_additional_properties_false(self):
        issues = validate({"id": 1, "name": "x", "zeta": 1, "alpha": 2}, self.SCHEMA)
        self.assertEqual(
            [(i.path, i.keyword) for i in issues],
            [("/alpha", "additionalProperties"), ("/zeta", "additionalProperties")],
        )

    def test_additional_properties_schema(self):
        schema = {"type": "object", "additionalProperties": {"enum": ["passed", "failed", "not_run"]}}
        self.assertEqual(validate({"AC-01": "passed"}, schema), [])
        issues = validate({"AC-01": "done"}, schema)
        self.assertEqual([(i.path, i.keyword) for i in issues], [("/AC-01", "enum")])

    def test_member_names_are_escaped_in_paths(self):
        schema = {"properties": {"a/b": {"type": "integer"}, "c~d": {"type": "integer"}}}
        issues = validate({"a/b": "x", "c~d": "y"}, schema)
        self.assertEqual([i.path for i in issues], ["/a~1b", "/c~0d"])

    def test_object_keywords_ignore_other_types(self):
        self.assertEqual(validate([1], {"required": ["a"], "properties": {}, "additionalProperties": False}), [])

    def test_nested_paths(self):
        schema = {"properties": {"tasks": {"items": {"properties": {"id": {"pattern": "^T[0-9]{3,}$"}}}}}}
        issues = validate({"tasks": [{"id": "T001"}, {"id": "X"}]}, schema)
        self.assertEqual(issues[0].path, "/tasks/1/id")


class TestCombinators(unittest.TestCase):
    def test_one_of_exactly_one(self):
        schema = {"oneOf": [{"type": "integer"}, {"minimum": 2}]}
        self.assertEqual(validate(1, schema), [], "only the first matches")
        self.assertEqual(validate(2.5, schema), [], "only the second matches")
        both = validate(3, schema)
        self.assertEqual(keywords(both), ["oneOf"])
        self.assertIn("more than one", both[0].message)
        self.assertIn("0, 1", both[0].message)
        none = validate("x", {"oneOf": [{"type": "integer"}, {"type": "null"}]})
        self.assertEqual(keywords(none), ["oneOf"])
        self.assertIn("not valid under any", none[0].message)

    def test_one_of_failure_names_the_closest_branch(self):
        schema = {
            "oneOf": [
                {"type": "object", "required": ["a", "b", "c"]},
                {"type": "object", "required": ["z"]},
            ]
        }
        issues = validate({"a": 1, "b": 2}, schema)
        self.assertIn("closest is #0", issues[0].message)
        self.assertIn("'c'", issues[0].message)

    def test_failure_messages_quote_rule_and_branch_descriptions(self):
        schema = {
            "description": "APPROVE requires no blockers.",
            "anyOf": [
                {"properties": {"result": {"const": "CHANGES_REQUESTED"}}},
                {
                    "description": "A clean verdict.",
                    "properties": {"blockers": {"maxItems": 0}},
                    "required": ["x", "y"],
                },
            ],
        }
        message = validate({"result": "APPROVE", "blockers": [1]}, schema)[0].message
        self.assertIn("[rule: APPROVE requires no blockers]", message)
        self.assertIn("closest is #0:", message)
        message = validate({"result": "APPROVE"}, dict(schema, anyOf=list(reversed(schema["anyOf"]))))[0].message
        self.assertIn("closest is #1:", message)
        clean_first = {"anyOf": [{"description": "A clean verdict.", "maxItems": 0}, {"type": "object"}]}
        self.assertIn("closest is #0 (A clean verdict):", validate([1], clean_first)[0].message)
        long_rule = {"description": "x" * 121, "oneOf": [{"type": "string"}, {"type": "null"}]}
        self.assertNotIn("[rule:", validate(1, long_rule)[0].message)
        ambiguous = {"description": "Exactly one tier.", "oneOf": [{"type": "integer"}, {"minimum": 0}]}
        self.assertIn("[rule: Exactly one tier]", validate(1, ambiguous)[0].message)

    def test_ref_branches_and_not_are_described(self):
        root = {
            "$defs": {"det": {"description": "deterministic tier", "required": ["run"]}},
            "oneOf": [{"$ref": "#/$defs/det"}, {"required": ["prompt"]}],
        }
        self.assertIn("closest is #0 (deterministic tier):", validate({}, root)[0].message)
        forbid = {"not": {"description": "Members of other tiers", "required": ["prompt"]}}
        self.assertEqual(
            validate({"prompt": 1}, forbid)[0].message,
            "must not be valid under the 'not' schema [rule: Members of other tiers]",
        )

    def test_any_of(self):
        schema = {"anyOf": [{"type": "string"}, {"minimum": 10}]}
        self.assertEqual(validate("x", schema), [])
        self.assertEqual(validate(11, schema), [])
        self.assertEqual(keywords(validate(3, schema)), ["anyOf"])

    def test_all_of_reports_every_sub_issue(self):
        schema = {"allOf": [{"type": "integer"}, {"minimum": 5}]}
        self.assertEqual(validate(6, schema), [])
        self.assertEqual(keywords(validate(4.5, schema)), ["type", "minimum"])

    def test_not(self):
        schema = {"not": {"required": ["prompt"]}}
        self.assertEqual(validate({"run": {}}, schema), [])
        self.assertEqual(keywords(validate({"prompt": "x"}, schema)), ["not"])

    def test_boolean_schemas(self):
        self.assertEqual(validate(1, True), [])
        self.assertEqual(keywords(validate(1, False)), ["false"])
        self.assertEqual(keywords(validate({"a": 1}, {"properties": {"a": False}})), ["false"])

    def test_empty_combinator_list_is_a_schema_error(self):
        for keyword in ("oneOf", "anyOf", "allOf"):
            with self.subTest(keyword=keyword), self.assertRaises(SchemaError):
                validate(1, {keyword: []})


class TestRef(unittest.TestCase):
    ROOT = {
        "$defs": {
            "task_id": {"type": "string", "pattern": "^T[0-9]{3,}$"},
            "task": {"type": "object", "properties": {"id": {"$ref": "#/$defs/task_id"}}, "required": ["id"]},
            "a/b": {"const": 1},
        },
        "type": "array",
        "items": {"$ref": "#/$defs/task"},
    }

    def test_ref_resolves_nested_defs(self):
        self.assertEqual(validate([{"id": "T001"}], self.ROOT), [])
        issues = validate([{"id": "T1"}], self.ROOT)
        self.assertEqual([(i.path, i.keyword) for i in issues], [("/0/id", "pattern")])

    def test_ref_with_escaped_pointer(self):
        root = dict(self.ROOT, items={"$ref": "#/$defs/a~1b"})
        self.assertEqual(validate([1], root), [])
        self.assertEqual(keywords(validate([2], root)), ["const"])

    def test_ref_siblings_also_apply(self):
        root = {"$defs": {"s": {"type": "string"}}, "$ref": "#/$defs/s", "maxLength": 2}
        self.assertEqual(keywords(validate("abc", root)), ["maxLength"])

    def test_explicit_root(self):
        subschema = {"$ref": "#/$defs/task_id"}
        self.assertEqual(validate("T123", subschema, root=self.ROOT), [])

    def test_unresolvable_and_remote_refs_are_schema_errors(self):
        with self.assertRaises(SchemaError):
            validate(1, {"$ref": "#/$defs/missing"})
        with self.assertRaises(SchemaError):
            validate(1, {"$ref": "https://example.com/schema.json"})


class TestDeterminismAndHelpers(unittest.TestCase):
    def test_issue_order_is_stable(self):
        schema = {
            "type": "object",
            "required": ["b", "a"],
            "properties": {"x": {"type": "string"}, "c": {"type": "string"}},
            "additionalProperties": False,
        }
        instance = {"x": 1, "c": 2, "zz": 0, "yy": 0}
        first = validate(instance, schema)
        self.assertEqual(first, validate(dict(reversed(list(instance.items()))), schema))
        self.assertEqual(
            [(i.path, i.keyword) for i in first],
            [
                ("/b", "required"),
                ("/a", "required"),
                ("/c", "type"),
                ("/x", "type"),
                ("/yy", "additionalProperties"),
                ("/zz", "additionalProperties"),
            ],
        )

    def test_too_deep_instance_is_an_issue_not_a_crash(self):
        deep = current = []
        for _ in range(5000):
            current.append([])
            current = current[0]
        self.assertEqual(
            validate(deep, {"items": {"$ref": "#"}}), [Issue("", "depth", "instance is nested too deeply to validate")]
        )

    def test_annotations_are_ignored(self):
        schema = {
            "$schema": "x",
            "$id": "y",
            "title": "t",
            "description": "d",
            "examples": [1],
            "default": 2,
            "$comment": "c",
        }
        self.assertEqual(validate("anything", schema), [])

    def test_is_valid(self):
        self.assertTrue(js.is_valid(1, {"type": "integer"}))
        self.assertFalse(js.is_valid("1", {"type": "integer"}))

    def test_issue_to_error(self):
        error = Issue("/a", "type", "expected string, got integer").to_error(prefix="/payload")
        self.assertEqual(
            error, {"code": "SCHEMA_INVALID", "message": "type: expected string, got integer", "path": "/payload/a"}
        )

    def test_issues_to_errors_truncates(self):
        issues = [Issue("/%d" % n, "type", "bad") for n in range(25)]
        errors = js.issues_to_errors(issues, limit=3)
        self.assertEqual(len(errors), 4)
        self.assertEqual(errors[-1]["code"], "ISSUES_TRUNCATED")
        self.assertIn("22 more", errors[-1]["message"])
        self.assertEqual(len(js.issues_to_errors(issues[:2], limit=3)), 2)

    def test_json_type_of(self):
        cases = [
            (None, "null"),
            (True, "boolean"),
            (1, "integer"),
            (1.0, "integer"),
            (1.5, "number"),
            ("s", "string"),
            ([], "array"),
            ({}, "object"),
            (float("inf"), "number"),
        ]
        for value, expected in cases:
            with self.subTest(value=value):
                self.assertEqual(js.json_type_of(value), expected)

    def test_json_equal(self):
        self.assertTrue(js.json_equal({"a": [1, {"b": None}]}, {"a": [1.0, {"b": None}]}))
        self.assertFalse(js.json_equal({"a": 1}, {"a": 1, "b": 2}))
        self.assertFalse(js.json_equal(1, "1"))
        self.assertFalse(js.json_equal(False, None))


class TestUnsupportedKeywords(unittest.TestCase):
    def test_subset_schema_is_clean(self):
        schema = {
            "$schema": "https://json-schema.org/draft/2020-12/schema",
            "$id": "urn:x",
            "title": "t",
            "description": "d",
            "type": "object",
            "properties": {"a": {"oneOf": [{"type": "string", "format": "date-time"}, {"not": {"type": "null"}}]}},
            "additionalProperties": {"items": {"$ref": "#/$defs/x"}, "prefixItems": [True]},
            "$defs": {"x": {"anyOf": [{"allOf": [{"enum": [1]}]}]}},
            "examples": [{"if": "ignored inside annotations"}],
        }
        self.assertEqual(js.unsupported_keywords(schema), [])

    def test_reports_nested_unsupported_keywords_sorted(self):
        schema = {
            "type": "object",
            "properties": {
                "a": {"type": "string", "if": {"const": "x"}, "then": {}},
                "b": {"type": "object", "patternProperties": {"^x": {}}, "propertyNames": {"pattern": "^a"}},
            },
            "$defs": {"c": {"minProperties": 1}},
            "dependentRequired": {},
        }
        self.assertEqual(
            js.unsupported_keywords(schema),
            ["dependentRequired", "if", "minProperties", "patternProperties", "propertyNames", "then"],
        )

    def test_reports_unsupported_format_and_remote_ref(self):
        schema = {
            "properties": {"e": {"format": "email"}, "r": {"$ref": "other.json#/x"}, "p": {"$ref": "#/properties/e"}}
        }
        self.assertEqual(js.unsupported_keywords(schema), ["$ref:#/properties/e", "$ref:other.json#/x", "format:email"])

    def test_property_names_that_look_like_keywords_are_not_keywords(self):
        schema = {"properties": {"if": {"type": "string"}, "format": {"type": "string"}}}
        self.assertEqual(js.unsupported_keywords(schema), [])


if __name__ == "__main__":
    unittest.main()
