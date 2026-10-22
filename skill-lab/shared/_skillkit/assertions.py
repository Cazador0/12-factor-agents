"""Benchmark assertion operators (CONVENTIONS §5).

An assertion is ``{"path": <JSON Pointer>, "op": <op>, "value": <expected>}``.
``evaluate(doc, assertion)`` returns ``(passed, actual)`` where ``actual`` is
the value found at ``path`` (``None`` when the path is missing; the length for
``len_*`` ops, so large arrays do not bloat results).

A missing path fails every op except ``not_exists``. Operators never coerce
types: ``gte``/``lte``/``gt``/``lt`` compare numbers only (never booleans),
``regex`` applies to strings only, and ``len_*`` to strings, arrays and
objects. ``contains`` means substring for strings, element for arrays and
member name for objects. ``type`` takes a JSON type name or a list of them;
``number`` includes integers, and ``1.0`` is an integer.

A malformed assertion (unknown op, missing ``value``, wrong ``value`` type,
bad pointer, bad regex) raises ``InvalidAssertion``: that is a case-authoring
error, reported by the runner as ``error``, not as a failed check.
"""

from __future__ import annotations

import re
from typing import Any, Callable, Dict, List, Tuple

from . import jsonpointer
from .jsonschema_mini import JSON_TYPES, is_number, is_type, json_equal

OPS = (
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
)
_NO_VALUE_OPS = ("exists", "not_exists")
_MISSING = object()


class InvalidAssertion(ValueError):
    """The assertion itself is malformed."""


def evaluate(doc: Any, assertion: Dict[str, Any]) -> Tuple[bool, Any]:
    """Evaluate one assertion against ``doc``; see the module docstring."""
    path, op, expected = _parse(assertion)
    try:
        actual = jsonpointer.resolve(doc, path)
    except jsonpointer.PointerSyntaxError as exc:
        raise InvalidAssertion(str(exc)) from None
    except jsonpointer.PointerError:
        actual = _MISSING
    if op == "exists":
        return actual is not _MISSING, None if actual is _MISSING else actual
    if op == "not_exists":
        return actual is _MISSING, None if actual is _MISSING else actual
    if actual is _MISSING:
        return False, None
    if op.startswith("len_"):
        return _check_length(op, actual, expected)
    return _OPERATORS[op](actual, expected), actual


def evaluate_all(doc: Any, assertions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Evaluate assertions in order into ``{path, op, passed, actual}`` records."""
    results = []
    for assertion in assertions:
        passed, actual = evaluate(doc, assertion)
        results.append({"path": assertion["path"], "op": assertion["op"], "passed": passed, "actual": actual})
    return results


def _parse(assertion: Any) -> Tuple[str, str, Any]:
    if not isinstance(assertion, dict):
        raise InvalidAssertion("assertion must be an object")
    path, op = assertion.get("path"), assertion.get("op")
    if not isinstance(path, str):
        raise InvalidAssertion("assertion 'path' must be a JSON Pointer string")
    if op not in OPS:
        raise InvalidAssertion("unknown assertion op %r" % (op,))
    if op in _NO_VALUE_OPS:
        return path, op, None
    if "value" not in assertion:
        raise InvalidAssertion("op %r needs a 'value'" % op)
    expected = assertion["value"]
    _check_expected(op, expected)
    return path, op, expected


def _check_expected(op: str, expected: Any) -> None:
    if op in ("in", "not_in") and not isinstance(expected, list):
        raise InvalidAssertion("op %r needs a list value" % op)
    if op in ("gte", "lte", "gt", "lt") and not is_number(expected):
        raise InvalidAssertion("op %r needs a number value" % op)
    if op.startswith("len_") and (isinstance(expected, bool) or not isinstance(expected, int) or expected < 0):
        raise InvalidAssertion("op %r needs a non-negative integer value" % op)
    if op == "regex":
        if not isinstance(expected, str):
            raise InvalidAssertion("op 'regex' needs a string pattern")
        try:
            re.compile(expected)
        except re.error as exc:
            raise InvalidAssertion("invalid regex %r: %s" % (expected, exc)) from None
    if op == "type":
        names = expected if isinstance(expected, list) else [expected]
        if not names or any(name not in JSON_TYPES for name in names):
            raise InvalidAssertion("op 'type' needs JSON type names from %s" % (", ".join(JSON_TYPES),))


def _contains(actual: Any, expected: Any) -> bool:
    if isinstance(actual, str):
        return isinstance(expected, str) and expected in actual
    if isinstance(actual, (list, tuple)):
        return any(json_equal(item, expected) for item in actual)
    if isinstance(actual, dict):
        return isinstance(expected, str) and expected in actual
    return False


def _compare(predicate: Callable[[Any, Any], bool]) -> Callable[[Any, Any], bool]:
    return lambda actual, expected: is_number(actual) and predicate(actual, expected)


def _check_length(op: str, actual: Any, expected: int) -> Tuple[bool, Any]:
    if not isinstance(actual, (str, list, tuple, dict)):
        return False, None
    length = len(actual)
    if op == "len_eq":
        return length == expected, length
    if op == "len_gte":
        return length >= expected, length
    return length <= expected, length


def _is_one_of_types(actual: Any, expected: Any) -> bool:
    names = expected if isinstance(expected, list) else [expected]
    return any(is_type(actual, name) for name in names)


_OPERATORS: Dict[str, Callable[[Any, Any], bool]] = {
    "eq": json_equal,
    "ne": lambda actual, expected: not json_equal(actual, expected),
    "in": lambda actual, expected: any(json_equal(actual, option) for option in expected),
    "not_in": lambda actual, expected: not any(json_equal(actual, option) for option in expected),
    "contains": _contains,
    "not_contains": lambda actual, expected: isinstance(actual, (str, list, tuple, dict))
    and not _contains(actual, expected),
    "regex": lambda actual, expected: isinstance(actual, str) and re.search(expected, actual) is not None,
    "gte": _compare(lambda a, b: a >= b),
    "lte": _compare(lambda a, b: a <= b),
    "gt": _compare(lambda a, b: a > b),
    "lt": _compare(lambda a, b: a < b),
    "type": _is_one_of_types,
}
