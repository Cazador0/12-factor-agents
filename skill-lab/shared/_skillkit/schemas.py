"""Locate, load and apply the JSON contracts a skill vendors.

Layout when vendored (the normal case)::

    skills/<name>/
      scripts/_skillkit/schemas.py   <- this file
      assets/schemas/<contract>.v1.schema.json

``skill_root()`` is the folder that contains ``scripts/`` (``skills/<name>``).
In the canonical copy (``skill-lab/shared/_skillkit``) there is no skill, so
``skill_root()`` returns None and schemas load from
``skill-lab/contracts/schemas`` instead. Loaded schemas are cached and must be
treated as read-only.
"""

from __future__ import annotations

import json
import os
import re
from typing import Any, Dict, List, Optional, Sequence, Tuple

from . import EXIT_USAGE
from .envelope import ScriptError, URN_PREFIX
from .jsonschema_mini import Issue, validate

_NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_URN_RE = re.compile(r"^urn:skill-lab:schema:([a-z0-9]+(?:-[a-z0-9]+)*):v([1-9][0-9]*)$")
_PACKAGE_DIR = os.path.dirname(os.path.abspath(__file__))
_CACHE: Dict[Tuple[str, int, Tuple[str, ...]], Any] = {}


def skill_root() -> Optional[str]:
    """Return ``skills/<name>`` for a vendored copy, or None for the canonical copy."""
    scripts_dir = os.path.dirname(_PACKAGE_DIR)
    if os.path.basename(scripts_dir) != "scripts":
        return None
    return os.path.dirname(scripts_dir)


def default_schema_dirs() -> List[str]:
    """Directories searched when ``search_dirs`` is not given."""
    root = skill_root()
    if root is not None:
        return [os.path.join(root, "assets", "schemas")]
    lab_root = os.path.dirname(os.path.dirname(_PACKAGE_DIR))
    return [os.path.join(lab_root, "contracts", "schemas")]


def schema_filename(name: str, version: int = 1) -> str:
    """Return ``<name>.v<version>.schema.json`` after checking the name."""
    if not isinstance(name, str) or not _NAME_RE.match(name):
        raise ScriptError(
            "SCHEMA_NAME_INVALID", "contract name must be kebab-case, got %r" % (name,), exit_code=EXIT_USAGE
        )
    return "%s.v%d.schema.json" % (name, version)


def parse_urn(urn: str) -> Tuple[str, int]:
    """Split ``urn:skill-lab:schema:<name>:v<N>`` into ``(name, N)``."""
    match = _URN_RE.match(urn) if isinstance(urn, str) else None
    if match is None:
        raise ScriptError("SCHEMA_URN_INVALID", "not a %s<name>:v<N> URN: %r" % (URN_PREFIX, urn), exit_code=EXIT_USAGE)
    return match.group(1), int(match.group(2))


def load_schema(name: str, search_dirs: Optional[Sequence[str]] = None, version: int = 1) -> Any:
    """Load ``<name>.v<version>.schema.json`` from the first directory that has it.

    Raises ``ScriptError`` ``SCHEMA_NOT_FOUND`` or ``SCHEMA_UNREADABLE``
    (exit 2): a missing vendored schema is an installation problem.
    """
    filename = schema_filename(name, version)
    dirs = tuple(default_schema_dirs() if search_dirs is None else search_dirs)
    key = (name, version, dirs)
    if key not in _CACHE:
        _CACHE[key] = _read_schema(filename, dirs)
    return _CACHE[key]


def _read_schema(filename: str, dirs: Tuple[str, ...]) -> Any:
    for directory in dirs:
        path = os.path.join(directory, filename)
        if not os.path.isfile(path):
            continue
        try:
            with open(path, "r", encoding="utf-8") as handle:
                return json.load(handle)
        except (OSError, ValueError) as exc:
            raise ScriptError(
                "SCHEMA_UNREADABLE", "cannot load schema: %s" % exc, path=path, exit_code=EXIT_USAGE
            ) from None
    raise ScriptError(
        "SCHEMA_NOT_FOUND",
        "schema %s not found in %s" % (filename, ", ".join(dirs) or "(no directories)"),
        exit_code=EXIT_USAGE,
    )


def validate_payload(name: str, payload: Any, search_dirs: Optional[Sequence[str]] = None) -> List[Issue]:
    """Validate ``payload`` against contract ``name`` (v1) and return the issues."""
    return validate(payload, load_schema(name, search_dirs))


def validate_envelope(
    envelope: Any, *, exit_code: Optional[int] = None, search_dirs: Optional[Sequence[str]] = None
) -> List[Issue]:
    """Validate an envelope and, where the contract requires it, its payload.

    The payload is checked against ``kind_schema`` when ``ok`` is true or the
    process exit code was 1 (a completed-but-failing result). Payload issue
    paths are prefixed with ``/payload``.
    """
    issues = validate(envelope, load_schema("envelope", search_dirs))
    if issues or not isinstance(envelope, dict):
        return issues
    if not (envelope.get("ok") is True or exit_code == 1):
        return issues
    name, version = parse_urn(envelope["kind_schema"])
    payload_issues = validate(envelope["payload"], load_schema(name, search_dirs, version))
    return [Issue("/payload" + issue.path, issue.keyword, issue.message) for issue in payload_issues]
