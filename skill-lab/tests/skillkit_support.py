"""Shared paths and helpers for the contract and skillkit tests.

Importing this module puts ``skill-lab/shared`` on ``sys.path`` so tests can
``import _skillkit`` exactly as a vendored skill script does. Paths are
derived from this file, so the tests run from any working directory.
"""

from __future__ import annotations

import contextlib
import io
import json
import os
import re
import sys
from typing import Any, Dict, Iterator, List, Optional

TESTS_DIR = os.path.dirname(os.path.abspath(__file__))
LAB_ROOT = os.path.dirname(TESTS_DIR)
REPO_ROOT = os.path.dirname(LAB_ROOT)
SHARED_DIR = os.path.join(LAB_ROOT, "shared")
SKILLKIT_DIR = os.path.join(SHARED_DIR, "_skillkit")
SCHEMA_DIR = os.path.join(LAB_ROOT, "contracts", "schemas")
EXAMPLE_DIR = os.path.join(LAB_ROOT, "contracts", "examples")
CONVENTIONS_PATH = os.path.join(LAB_ROOT, "docs", "CONVENTIONS.md")

if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)


def load_json(path: str) -> Any:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


def schema_path(name: str) -> str:
    return os.path.join(SCHEMA_DIR, "%s.v1.schema.json" % name)


def example_path(name: str) -> str:
    return os.path.join(EXAMPLE_DIR, "%s.v1.example.json" % name)


def load_schema(name: str) -> Any:
    return load_json(schema_path(name))


def load_example(name: str) -> Any:
    return load_json(example_path(name))


def catalog_names() -> List[str]:
    """Contract names from the CONVENTIONS §4 "Contract catalog" table, in order."""
    with open(CONVENTIONS_PATH, "r", encoding="utf-8") as handle:
        text = handle.read()
    section = text.split("### Contract catalog", 1)[1].split("\n## ", 1)[0]
    return re.findall(r"^\| `([a-z0-9-]+)` \|", section, flags=re.MULTILINE)


def schema_files() -> Dict[str, str]:
    """Map contract name -> schema path for every file in contracts/schemas."""
    result = {}
    for filename in sorted(os.listdir(SCHEMA_DIR)):
        if filename.endswith(".v1.schema.json"):
            result[filename[: -len(".v1.schema.json")]] = os.path.join(SCHEMA_DIR, filename)
    return result


class Captured:
    """stdout/stderr captured as text, with a binary buffer like a real stream."""

    def __init__(self) -> None:
        self.raw = io.BytesIO()
        self.stream = io.TextIOWrapper(self.raw, encoding="utf-8", write_through=True)

    def text(self) -> str:
        self.stream.flush()
        return self.raw.getvalue().decode("utf-8")


@contextlib.contextmanager
def captured_stderr() -> Iterator[io.StringIO]:
    buffer = io.StringIO()
    original = sys.stderr
    sys.stderr = buffer
    try:
        yield buffer
    finally:
        sys.stderr = original


@contextlib.contextmanager
def env(**values: Optional[str]) -> Iterator[None]:
    """Temporarily set (or, with None, unset) environment variables."""
    saved = {name: os.environ.get(name) for name in values}
    try:
        for name, value in values.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
        yield
    finally:
        for name, value in saved.items():
            if value is None:
                os.environ.pop(name, None)
            else:
                os.environ[name] = value
