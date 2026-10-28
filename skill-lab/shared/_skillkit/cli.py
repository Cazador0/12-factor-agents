"""Command-line plumbing shared by every skill script.

``base_parser`` adds the flags every script accepts (``--pretty``, ``--now``,
``--state-dir``) and turns argparse usage errors into ``ScriptError("USAGE")``
so ``envelope.run_script`` can still print one envelope. Subparsers created
from it inherit that behaviour. Scripts with subcommands can call
``add_common_arguments`` on each subparser so the flags work after the
subcommand name too.

``read_json`` and ``read_text`` read a path or ``-`` (stdin) and fail with
``INPUT_NOT_FOUND``, ``INPUT_UNREADABLE`` or ``INPUT_NOT_JSON`` (exit 2).
JSON input is strict: no NaN/Infinity and no duplicate keys, because two
parsers disagreeing about a duplicated key is a classic injection vector.
"""

from __future__ import annotations

import argparse
import datetime as _dt
import json
import math
import os
import sys
from typing import Any, List, NoReturn, Optional, Tuple

from . import EXIT_USAGE
from .envelope import ScriptError
from .redact import redact_text
from .timeutil import parse_iso8601, to_iso, utc_now

DEFAULT_STATE_DIR = os.path.join(".", ".skill-state")

__all__ = [
    "DEFAULT_STATE_DIR",
    "base_parser",
    "add_common_arguments",
    "add_input_argument",
    "read_json",
    "read_text",
    "loads_strict",
    "parse_now",
    "to_iso",
    "log",
]


class SkillArgumentParser(argparse.ArgumentParser):
    """ArgumentParser that raises ``ScriptError`` instead of exiting on bad usage."""

    def error(self, message: str) -> NoReturn:
        self.print_usage(sys.stderr)
        raise ScriptError("USAGE", message, exit_code=EXIT_USAGE)


def base_parser(description: str, *, common: bool = True, prog: Optional[str] = None) -> SkillArgumentParser:
    """Return a parser with ``--pretty``, ``--now`` and ``--state-dir``.

    Pass ``common=False`` for a subcommand-style script and call
    ``add_common_arguments`` on each subparser instead.
    """
    parser = SkillArgumentParser(prog=prog, description=description)
    if common:
        add_common_arguments(parser)
    return parser


def add_common_arguments(parser: argparse.ArgumentParser) -> argparse.ArgumentParser:
    """Add the flags every script accepts to ``parser`` and return it."""
    parser.add_argument("--pretty", action="store_true", help="indent the JSON envelope for humans")
    parser.add_argument(
        "--now",
        metavar="ISO-8601",
        default=None,
        help="timestamp to use instead of the clock (for deterministic output)",
    )
    parser.add_argument(
        "--state-dir",
        metavar="DIR",
        default=DEFAULT_STATE_DIR,
        help="state root for leases, caches and plans (default: %(default)s)",
    )
    return parser


def add_input_argument(
    parser: argparse.ArgumentParser, *, required: bool = True, help_text: str = "input JSON file, or - for stdin"
) -> argparse.ArgumentParser:
    """Add the conventional ``--input FILE`` flag."""
    parser.add_argument("--input", metavar="FILE", required=required, help=help_text)
    return parser


def read_text(path_or_dash: str, *, encoding: str = "utf-8-sig") -> str:
    """Read a whole text file (or stdin for ``-``) with compact errors."""
    if path_or_dash == "-":
        return sys.stdin.read()
    try:
        with open(path_or_dash, "r", encoding=encoding) as handle:
            return handle.read()
    except FileNotFoundError:
        raise ScriptError("INPUT_NOT_FOUND", "file not found", path=path_or_dash) from None
    except IsADirectoryError:
        raise ScriptError("INPUT_UNREADABLE", "path is a directory, not a file", path=path_or_dash) from None
    except UnicodeDecodeError as exc:
        raise ScriptError(
            "INPUT_NOT_TEXT", "file is not valid %s: %s" % (encoding, exc.reason), path=path_or_dash
        ) from None
    except OSError as exc:
        raise ScriptError("INPUT_UNREADABLE", exc.strerror or str(exc), path=path_or_dash) from None


def read_json(path_or_dash: str) -> Any:
    """Parse strict JSON from a file or stdin (``-``).

    Raises ``ScriptError`` with ``INPUT_NOT_FOUND`` for a missing file and
    ``INPUT_NOT_JSON`` (path ``file:line:column`` where known) for invalid
    JSON, text that is not UTF-8, NaN/Infinity, numbers that overflow to
    infinity, duplicate object keys, or nesting too deep to parse.
    """
    label = "<stdin>" if path_or_dash == "-" else path_or_dash
    try:
        text = read_text(path_or_dash)
    except ScriptError as exc:
        if exc.code != "INPUT_NOT_TEXT":
            raise
        raise ScriptError("INPUT_NOT_JSON", exc.message, path=label) from None
    try:
        return loads_strict(text)
    except json.JSONDecodeError as exc:
        raise ScriptError("INPUT_NOT_JSON", exc.msg, path="%s:%d:%d" % (label, exc.lineno, exc.colno)) from None
    except ValueError as exc:
        raise ScriptError("INPUT_NOT_JSON", str(exc), path=label) from None


def loads_strict(text: str) -> Any:
    """Parse JSON text strictly; raise ``ValueError`` (``JSONDecodeError`` for syntax).

    Rejects NaN/Infinity, numbers that overflow to infinity, duplicate object
    keys, and nesting too deep to parse. Use it for any untrusted JSON that
    does not come through ``read_json``, such as a policy or state file.
    """
    try:
        return json.loads(
            text, object_pairs_hook=_unique_pairs, parse_constant=_reject_constant, parse_float=_finite_float
        )
    except RecursionError:
        raise ValueError("JSON is nested too deeply") from None


def _unique_pairs(pairs: List[Tuple[str, Any]]) -> dict:
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError("duplicate object key %r" % (key,))
        result[key] = value
    return result


def _reject_constant(name: str) -> NoReturn:
    raise ValueError("%s is not valid JSON" % name)


def _finite_float(text: str) -> float:
    value = float(text)
    if not math.isfinite(value):
        raise ValueError("number %s is out of range" % text)
    return value


def parse_now(value: Optional[str]) -> _dt.datetime:
    """Return ``--now`` as an aware UTC datetime, or the current UTC time.

    Accepts RFC 3339 and common ISO 8601 forms (see
    ``timeutil.parse_iso8601``). Raises ``ScriptError("INVALID_NOW")``.
    """
    if value is None or value == "":
        return utc_now()
    try:
        return parse_iso8601(value)
    except ValueError as exc:
        raise ScriptError("INVALID_NOW", "--now must be an ISO 8601 timestamp (%s)" % exc, path="--now") from None


def log(message: str) -> None:
    """Write one redacted human-readable line to stderr (never stdout)."""
    sys.stderr.write(redact_text(str(message)).rstrip("\n") + "\n")
    sys.stderr.flush()
