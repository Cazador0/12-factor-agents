"""Minimal JSON Schema (draft 2020-12) validator for the contract keyword subset.

Supported keywords, exactly the CONVENTIONS §4 subset: ``type`` (string or
list), ``properties``, ``required``, ``additionalProperties`` (bool or schema),
``items``, ``prefixItems``, ``enum``, ``const``, ``pattern``, ``minLength``,
``maxLength``, ``minimum``, ``maximum``, ``exclusiveMinimum``,
``exclusiveMaximum``, ``minItems``, ``maxItems``, ``uniqueItems``, ``oneOf``,
``anyOf``, ``allOf``, ``not``, ``$ref`` (local ``#...`` pointers, normally
``#/$defs/<name>``), ``format: date-time`` and ``$defs``. Annotation keys
(``$schema``, ``$id``, ``title``, ``description``, ``examples``, ``default``,
``$comment``) are ignored. Boolean schemas (``true``/``false``) work anywhere a
schema does.

Semantics follow the specification where Python and JSON differ: booleans are
never numbers, ``1.0`` is an integer, ``1 == 1.0`` for ``enum``/``const``/
``uniqueItems``, string length counts code points, and ``pattern`` is an
unanchored search with ASCII ``\\d``/``\\w``/``\\s`` (ECMA-262 behaviour).

``validate`` returns issues in a deterministic order: keywords in a fixed
order, object members sorted by name, array items by index.
"""

from __future__ import annotations

import functools
import math
import re
from typing import Any, Dict, List, NamedTuple
from urllib.parse import unquote

from . import jsonpointer
from .timeutil import is_rfc3339

ANNOTATION_KEYWORDS = frozenset({"$schema", "$id", "title", "description", "examples", "default", "$comment"})
SUPPORTED_KEYWORDS = frozenset(
    {
        "type",
        "properties",
        "required",
        "additionalProperties",
        "items",
        "prefixItems",
        "enum",
        "const",
        "pattern",
        "minLength",
        "maxLength",
        "minimum",
        "maximum",
        "exclusiveMinimum",
        "exclusiveMaximum",
        "minItems",
        "maxItems",
        "uniqueItems",
        "oneOf",
        "anyOf",
        "allOf",
        "not",
        "$ref",
        "format",
        "$defs",
    }
)
SUPPORTED_FORMATS = frozenset({"date-time"})
MAX_RULE_LENGTH = 120
JSON_TYPES = ("object", "array", "string", "number", "integer", "boolean", "null")


class Issue(NamedTuple):
    """One validation problem.

    ``path`` locates the offending value (a JSON Pointer for schema issues,
    ``file:line`` for frontmatter issues), ``keyword`` names the rule that
    failed, and ``message`` is one human-readable line.
    """

    path: str
    keyword: str
    message: str

    def to_error(self, code: str = "SCHEMA_INVALID", prefix: str = "") -> Dict[str, str]:
        """Render as an envelope error object, optionally prefixing the path."""
        return {"code": code, "message": "%s: %s" % (self.keyword, self.message), "path": prefix + self.path}


class SchemaError(ValueError):
    """The schema itself is unusable (bad ``$ref``, bad regex, bad keyword value)."""


# ---------------------------------------------------------------------------
# JSON data model helpers
# ---------------------------------------------------------------------------


def json_type_of(value: Any) -> str:
    """Return the JSON type name of a Python value (integral floats are "integer")."""
    if value is None:
        return "null"
    if isinstance(value, bool):
        return "boolean"
    if isinstance(value, int):
        return "integer"
    if isinstance(value, float):
        return "integer" if math.isfinite(value) and value.is_integer() else "number"
    if isinstance(value, str):
        return "string"
    if isinstance(value, (list, tuple)):
        return "array"
    if isinstance(value, dict):
        return "object"
    return type(value).__name__


def is_type(value: Any, type_name: str) -> bool:
    """Return True when ``value`` is an instance of JSON type ``type_name``."""
    actual = json_type_of(value)
    if type_name == "number":
        return actual in ("number", "integer")
    return actual == type_name


def is_number(value: Any) -> bool:
    """True for ints and floats, never for booleans."""
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def json_equal(left: Any, right: Any) -> bool:
    """JSON equality: ``1 == 1.0``, ``true != 1``, objects compare by members."""
    if is_number(left) and is_number(right):
        return left == right
    left_type, right_type = json_type_of(left), json_type_of(right)
    if left_type != right_type:
        return False
    if left_type == "array":
        return len(left) == len(right) and all(json_equal(a, b) for a, b in zip(left, right))
    if left_type == "object":
        return left.keys() == right.keys() and all(json_equal(left[k], right[k]) for k in left)
    return left == right


# ---------------------------------------------------------------------------
# Validation
# ---------------------------------------------------------------------------


def validate(instance: Any, schema: Any, *, root: Any = None) -> List[Issue]:
    """Validate ``instance`` against ``schema`` and return every issue found.

    ``root`` is the document ``$ref`` pointers resolve against; it defaults to
    ``schema``. Raises ``SchemaError`` when the schema is unusable. An instance
    nested too deeply to walk yields a single ``depth`` issue.
    """
    validator = _Validator(schema if root is None else root)
    try:
        return validator.check(instance, schema, "")
    except RecursionError:
        return [Issue("", "depth", "instance is nested too deeply to validate")]


def is_valid(instance: Any, schema: Any, *, root: Any = None) -> bool:
    """Shorthand for ``not validate(...)``."""
    return not validate(instance, schema, root=root)


class _Validator:
    """Walks one instance against one schema document."""

    def __init__(self, root: Any) -> None:
        self.root = root

    def check(self, instance: Any, schema: Any, path: str) -> List[Issue]:
        if schema is True:
            return []
        if schema is False:
            return [Issue(path, "false", "no value is allowed here")]
        if not isinstance(schema, dict):
            raise SchemaError("schema at instance path %r must be an object or boolean" % (path or "/",))
        issues: List[Issue] = []
        for keyword, method in _KEYWORD_ORDER:
            if keyword in schema:
                issues.extend(method(self, instance, schema[keyword], schema, path))
        return issues

    # -- references and combinators -------------------------------------

    def _ref(self, instance: Any, ref: Any, schema: dict, path: str) -> List[Issue]:
        return self.check(instance, self.resolve_ref(ref), path)

    def resolve_ref(self, ref: Any) -> Any:
        if not isinstance(ref, str) or not ref.startswith("#"):
            raise SchemaError("only local '#...' $ref values are supported, got %r" % (ref,))
        try:
            return jsonpointer.resolve(self.root, unquote(ref[1:]))
        except jsonpointer.PointerError as exc:
            raise SchemaError("unresolvable $ref %r: %s" % (ref, exc)) from None

    def _all_of(self, instance: Any, subschemas: Any, schema: dict, path: str) -> List[Issue]:
        issues: List[Issue] = []
        for subschema in _schema_list("allOf", subschemas):
            issues.extend(self.check(instance, subschema, path))
        return issues

    def _any_of(self, instance: Any, subschemas: Any, schema: dict, path: str) -> List[Issue]:
        branches = _schema_list("anyOf", subschemas)
        results = [self.check(instance, branch, path) for branch in branches]
        if any(not result for result in results):
            return []
        return [Issue(path, "anyOf", _no_branch_message("anyOf", schema, self.described(branches), results))]

    def _one_of(self, instance: Any, subschemas: Any, schema: dict, path: str) -> List[Issue]:
        branches = _schema_list("oneOf", subschemas)
        results = [self.check(instance, branch, path) for branch in branches]
        matches = [index for index, result in enumerate(results) if not result]
        if len(matches) == 1:
            return []
        if not matches:
            return [Issue(path, "oneOf", _no_branch_message("oneOf", schema, self.described(branches), results))]
        indexes = ", ".join(map(str, matches))
        return [
            Issue(path, "oneOf", "is valid under more than one oneOf schema (indexes %s)%s" % (indexes, _rule(schema)))
        ]

    def _not(self, instance: Any, subschema: Any, schema: dict, path: str) -> List[Issue]:
        if self.check(instance, subschema, path):
            return []
        return [Issue(path, "not", "must not be valid under the 'not' schema%s" % _rule(subschema))]

    def described(self, branches: list) -> list:
        """Branches with local ``$ref`` resolved, so their descriptions can be quoted."""
        return [
            self.resolve_ref(b["$ref"]) if isinstance(b, dict) and "$ref" in b and "description" not in b else b
            for b in branches
        ]

    # -- any type ---------------------------------------------------------

    def _type(self, instance: Any, expected: Any, schema: dict, path: str) -> List[Issue]:
        names = [expected] if isinstance(expected, str) else expected
        if not isinstance(names, list) or not names or any(n not in JSON_TYPES for n in names):
            raise SchemaError("invalid 'type' value %r" % (expected,))
        if any(is_type(instance, name) for name in names):
            return []
        wanted = names[0] if len(names) == 1 else "one of " + ", ".join(names)
        return [Issue(path, "type", "expected %s, got %s" % (wanted, json_type_of(instance)))]

    def _enum(self, instance: Any, allowed: Any, schema: dict, path: str) -> List[Issue]:
        if not isinstance(allowed, list):
            raise SchemaError("'enum' must be an array")
        if any(json_equal(instance, option) for option in allowed):
            return []
        return [Issue(path, "enum", "%s is not one of %s" % (_short(instance), _short(allowed)))]

    def _const(self, instance: Any, expected: Any, schema: dict, path: str) -> List[Issue]:
        if json_equal(instance, expected):
            return []
        return [Issue(path, "const", "expected %s, got %s" % (_short(expected), _short(instance)))]

    def _format(self, instance: Any, name: Any, schema: dict, path: str) -> List[Issue]:
        if name != "date-time" or not isinstance(instance, str):
            return []
        if is_rfc3339(instance):
            return []
        return [Issue(path, "format", "%s is not an RFC 3339 date-time" % _short(instance))]

    # -- numbers ----------------------------------------------------------

    def _minimum(self, instance: Any, limit: Any, schema: dict, path: str) -> List[Issue]:
        return self._bound(instance, "minimum", limit, path, lambda v: v >= limit, ">=")

    def _maximum(self, instance: Any, limit: Any, schema: dict, path: str) -> List[Issue]:
        return self._bound(instance, "maximum", limit, path, lambda v: v <= limit, "<=")

    def _exclusive_minimum(self, instance: Any, limit: Any, schema: dict, path: str) -> List[Issue]:
        return self._bound(instance, "exclusiveMinimum", limit, path, lambda v: v > limit, ">")

    def _exclusive_maximum(self, instance: Any, limit: Any, schema: dict, path: str) -> List[Issue]:
        return self._bound(instance, "exclusiveMaximum", limit, path, lambda v: v < limit, "<")

    @staticmethod
    def _bound(instance: Any, keyword: str, limit: Any, path: str, ok: Any, symbol: str) -> List[Issue]:
        if not is_number(limit):
            raise SchemaError("%r must be a number" % (keyword,))
        if not is_number(instance) or ok(instance):
            return []
        return [Issue(path, keyword, "%s must be %s %s" % (_short(instance), symbol, _short(limit)))]

    # -- strings ----------------------------------------------------------

    def _min_length(self, instance: Any, limit: Any, schema: dict, path: str) -> List[Issue]:
        if isinstance(instance, str) and len(instance) < _count("minLength", limit):
            return [Issue(path, "minLength", "length %d is shorter than %d" % (len(instance), limit))]
        return []

    def _max_length(self, instance: Any, limit: Any, schema: dict, path: str) -> List[Issue]:
        if isinstance(instance, str) and len(instance) > _count("maxLength", limit):
            return [Issue(path, "maxLength", "length %d is longer than %d" % (len(instance), limit))]
        return []

    def _pattern(self, instance: Any, pattern: Any, schema: dict, path: str) -> List[Issue]:
        if not isinstance(pattern, str):
            raise SchemaError("'pattern' must be a string")
        if isinstance(instance, str) and not _compile(pattern).search(instance):
            return [Issue(path, "pattern", "%s does not match %r" % (_short(instance), pattern))]
        return []

    # -- arrays -----------------------------------------------------------

    def _prefix_items(self, instance: Any, subschemas: Any, schema: dict, path: str) -> List[Issue]:
        if not isinstance(instance, (list, tuple)):
            return []
        issues: List[Issue] = []
        for index, (item, subschema) in enumerate(zip(instance, _schema_list("prefixItems", subschemas))):
            issues.extend(self.check(item, subschema, jsonpointer.join(path, index)))
        return issues

    def _items(self, instance: Any, subschema: Any, schema: dict, path: str) -> List[Issue]:
        if not isinstance(instance, (list, tuple)):
            return []
        start = len(schema.get("prefixItems", []))
        issues: List[Issue] = []
        for index in range(start, len(instance)):
            issues.extend(self.check(instance[index], subschema, jsonpointer.join(path, index)))
        return issues

    def _min_items(self, instance: Any, limit: Any, schema: dict, path: str) -> List[Issue]:
        if isinstance(instance, (list, tuple)) and len(instance) < _count("minItems", limit):
            return [Issue(path, "minItems", "has %d items, fewer than %d" % (len(instance), limit))]
        return []

    def _max_items(self, instance: Any, limit: Any, schema: dict, path: str) -> List[Issue]:
        if isinstance(instance, (list, tuple)) and len(instance) > _count("maxItems", limit):
            return [Issue(path, "maxItems", "has %d items, more than %d" % (len(instance), limit))]
        return []

    def _unique_items(self, instance: Any, unique: Any, schema: dict, path: str) -> List[Issue]:
        if unique is not True or not isinstance(instance, (list, tuple)):
            return []
        for later in range(1, len(instance)):
            for earlier in range(later):
                if json_equal(instance[earlier], instance[later]):
                    return [Issue(path, "uniqueItems", "items %d and %d are equal" % (earlier, later))]
        return []

    # -- objects ----------------------------------------------------------

    def _required(self, instance: Any, names: Any, schema: dict, path: str) -> List[Issue]:
        if not isinstance(names, list):
            raise SchemaError("'required' must be an array")
        if not isinstance(instance, dict):
            return []
        return [
            Issue(jsonpointer.join(path, name), "required", "required property %r is missing" % (name,))
            for name in names
            if name not in instance
        ]

    def _properties(self, instance: Any, properties: Any, schema: dict, path: str) -> List[Issue]:
        if not isinstance(properties, dict):
            raise SchemaError("'properties' must be an object")
        if not isinstance(instance, dict):
            return []
        issues: List[Issue] = []
        for name in sorted(properties):
            if name in instance:
                issues.extend(self.check(instance[name], properties[name], jsonpointer.join(path, name)))
        return issues

    def _additional_properties(self, instance: Any, subschema: Any, schema: dict, path: str) -> List[Issue]:
        if not isinstance(instance, dict):
            return []
        declared = schema.get("properties", {})
        issues: List[Issue] = []
        for name in sorted(k for k in instance if k not in declared):
            member_path = jsonpointer.join(path, name)
            if subschema is False:
                issues.append(Issue(member_path, "additionalProperties", "property %r is not allowed" % (name,)))
            else:
                issues.extend(self.check(instance[name], subschema, member_path))
        return issues


_KEYWORD_ORDER = (
    ("$ref", _Validator._ref),
    ("type", _Validator._type),
    ("enum", _Validator._enum),
    ("const", _Validator._const),
    ("format", _Validator._format),
    ("minimum", _Validator._minimum),
    ("maximum", _Validator._maximum),
    ("exclusiveMinimum", _Validator._exclusive_minimum),
    ("exclusiveMaximum", _Validator._exclusive_maximum),
    ("minLength", _Validator._min_length),
    ("maxLength", _Validator._max_length),
    ("pattern", _Validator._pattern),
    ("minItems", _Validator._min_items),
    ("maxItems", _Validator._max_items),
    ("uniqueItems", _Validator._unique_items),
    ("prefixItems", _Validator._prefix_items),
    ("items", _Validator._items),
    ("required", _Validator._required),
    ("properties", _Validator._properties),
    ("additionalProperties", _Validator._additional_properties),
    ("allOf", _Validator._all_of),
    ("anyOf", _Validator._any_of),
    ("oneOf", _Validator._one_of),
    ("not", _Validator._not),
)


def _schema_list(keyword: str, value: Any) -> list:
    if not isinstance(value, list) or (keyword != "prefixItems" and not value):
        raise SchemaError("%r must be a non-empty array of schemas" % (keyword,))
    return value


def _count(keyword: str, value: Any) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        raise SchemaError("%r must be a non-negative integer" % (keyword,))
    return value


@functools.lru_cache(maxsize=512)
def _compile(pattern: str) -> re.Pattern:
    try:
        return re.compile(pattern, re.ASCII)
    except re.error as exc:
        raise SchemaError("invalid pattern %r: %s" % (pattern, exc)) from None


def _no_branch_message(keyword: str, schema: dict, branches: list, results: List[List[Issue]]) -> str:
    """Explain a failed anyOf/oneOf: the rule it encodes and the nearest alternative.

    The rule is the short ``description`` of the schema holding the keyword;
    the nearest alternative is the branch with the fewest issues, named by its
    own ``description`` when it has one. Contract invariants rely on this so a
    small model can see why a document was rejected and how to fix it.
    """
    best = min(range(len(results)), key=lambda index: len(results[index]))
    first = results[best][0]
    return "is not valid under any of the %d %s schemas%s; closest is #%d%s: %s at %s: %s" % (
        len(results),
        keyword,
        _rule(schema),
        best,
        _rule(branches[best], brackets=("(", ")")),
        first.keyword,
        first.path or "/",
        first.message,
    )


def _rule(schema: Any, brackets: tuple = ("[rule: ", "]")) -> str:
    """A schema's short description as message context; long ones are omitted."""
    text = schema.get("description") if isinstance(schema, dict) else None
    if not isinstance(text, str) or not text or len(text) > MAX_RULE_LENGTH:
        return ""
    return " %s%s%s" % (brackets[0], text.rstrip("."), brackets[1])


def _short(value: Any, limit: int = 60) -> str:
    text = repr(value)
    return text if len(text) <= limit else text[: limit - 3] + "..."


# ---------------------------------------------------------------------------
# Subset audit
# ---------------------------------------------------------------------------

_SCHEMA_MAP_KEYWORDS = ("properties", "$defs")
_SCHEMA_LIST_KEYWORDS = ("prefixItems", "oneOf", "anyOf", "allOf")
_SCHEMA_VALUE_KEYWORDS = ("additionalProperties", "items", "not")


def unsupported_keywords(schema: Any) -> List[str]:
    """Return the sorted names of keywords outside the supported subset.

    Walks every nested schema. Annotation keys are ignored (and their values,
    such as ``examples``, are not walked). Two value-level violations are also
    reported: ``format:<name>`` for formats other than ``date-time`` and
    ``$ref:<value>`` for references that do not point into ``#/$defs/``.
    """
    found: set = set()
    _audit(schema, found)
    return sorted(found)


def _audit(schema: Any, found: set) -> None:
    if not isinstance(schema, dict):
        return
    for keyword, value in schema.items():
        if keyword in ANNOTATION_KEYWORDS:
            continue
        if keyword not in SUPPORTED_KEYWORDS:
            found.add(keyword)
        elif keyword == "format" and value not in SUPPORTED_FORMATS:
            found.add("format:%s" % (value,))
        elif keyword == "$ref" and not (isinstance(value, str) and value.startswith("#/$defs/")):
            found.add("$ref:%s" % (value,))
        elif keyword in _SCHEMA_MAP_KEYWORDS and isinstance(value, dict):
            for subschema in value.values():
                _audit(subschema, found)
        elif keyword in _SCHEMA_LIST_KEYWORDS and isinstance(value, list):
            for subschema in value:
                _audit(subschema, found)
        elif keyword in _SCHEMA_VALUE_KEYWORDS:
            _audit(value, found)


def issues_to_errors(
    issues: List[Issue], *, code: str = "SCHEMA_INVALID", prefix: str = "", limit: int = 20
) -> List[Dict[str, str]]:
    """Convert issues to envelope errors, keeping at most ``limit`` (Factor 9).

    When issues are dropped, a final ``ISSUES_TRUNCATED`` error says how many.
    """
    errors = [issue.to_error(code, prefix) for issue in issues[:limit]]
    if len(issues) > limit:
        errors.append(
            {
                "code": "ISSUES_TRUNCATED",
                "message": "%d more issues not shown" % (len(issues) - limit),
                "path": prefix or "",
            }
        )
    return errors


__all__ = [
    "Issue",
    "SchemaError",
    "validate",
    "is_valid",
    "unsupported_keywords",
    "json_type_of",
    "is_type",
    "is_number",
    "json_equal",
    "issues_to_errors",
    "ANNOTATION_KEYWORDS",
    "SUPPORTED_KEYWORDS",
    "SUPPORTED_FORMATS",
    "JSON_TYPES",
]
