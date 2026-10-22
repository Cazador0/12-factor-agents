"""Strict parser for the portable SKILL.md frontmatter subset (CONVENTIONS §2).

The subset parses identically in Zed (serde_yaml), Claude Code, Codex and
here. ``parse(text)`` accepts exactly:

- an opening line ``---`` and a closing line that is exactly ``---`` (LF, CRLF
  or end of file), as in Zed's ``extract_frontmatter``; leading whitespace is
  skipped like Rust's ``trim_start()``, and a leading UTF-8 BOM is skipped too
  (``bom`` records it so a validator can warn);
- top-level ``key: value`` lines, where the value is a plain scalar or a
  one-line double-quoted scalar whose only escapes are ``\\"`` and ``\\\\``;
- one ``metadata:`` map whose entries are indented exactly two spaces;
- ``true``/``false`` as booleans, and blank lines.

Everything else is reported as an ``Issue`` (path ``<source>:<line>``):
tabs, comments, block scalars, flow collections, lists, anchors, aliases,
tags, single quotes, multi-line values, other escapes, duplicate keys,
nested maps, control characters, missing delimiters, and plain values that
some YAML parser would not read as a string (``yes``, ``1.0``, ``null``,
``2026-10-22``; quote those).

``lint(result)`` then applies the field rules of §2 (allowed keys, name
pattern, quoted description, metadata keys, and so on).
"""

from __future__ import annotations

import dataclasses
import re
from typing import Any, Dict, List, Optional, Tuple

from .jsonschema_mini import Issue

ALLOWED_KEYS = ("name", "description", "license", "compatibility", "metadata", "disable-model-invocation")
REQUIRED_KEYS = ("name", "description", "metadata")
REQUIRED_METADATA_KEYS = ("version", "family", "spec", "author")
FAMILIES = ("roles", "speckit-gitea", "control-plane", "audit", "meta")
RESERVED_NAMES = ("create-skill",)
MAX_NAME_LENGTH = 64
MAX_DESCRIPTION_LENGTH = 1024
MAX_COMPATIBILITY_LENGTH = 500

NAME_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
SEMVER_RE = re.compile(r"^(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)\.(0|[1-9][0-9]*)(-[0-9A-Za-z.-]+)?(\+[0-9A-Za-z.-]+)?$")
SPEC_ID_RE = re.compile(r"^SPEC-[0-9]{3}$")

_KEY_LINE_RE = re.compile(r"^([A-Za-z0-9_][A-Za-z0-9_.-]*):(?:[ ]+(.*))?$")
_CONTROL_RE = re.compile("[\x00-\x08\x0b-\x1f\x7f\x85\u2028\u2029]")
_LEADING_INDICATORS = "-?:,[]{}#&*!|>'\"%@`"
_INDICATOR_PROBLEMS = {
    "|": ("block_scalar", "block scalars ('|', '>') are not allowed"),
    ">": ("block_scalar", "block scalars ('|', '>') are not allowed"),
    "[": ("flow_collection", "flow collections ('[', '{') are not allowed"),
    "{": ("flow_collection", "flow collections ('[', '{') are not allowed"),
    "&": ("anchor", "anchors and aliases are not allowed"),
    "*": ("anchor", "anchors and aliases are not allowed"),
    "!": ("tag", "tags are not allowed"),
    "'": ("single_quoted", "use double quotes, not single quotes"),
    "#": ("comment", "comments are not allowed in frontmatter"),
}
_AMBIGUOUS_PLAIN = [
    re.compile(pattern)
    for pattern in (
        r"^(?:null|Null|NULL|~)$",
        r"^(?:true|True|TRUE|false|False|FALSE|yes|Yes|YES|no|No|NO|on|On|ON|off|Off|OFF|y|Y|n|N)$",
        r"^[-+]?(?:[0-9][0-9_]*(?:\.[0-9_]*)?|\.[0-9][0-9_]*)(?:[eE][-+]?[0-9]+)?$",
        r"^[-+]?0(?:x[0-9a-fA-F_]+|o[0-7_]+|b[01_]+)$",
        r"^[-+]?\.(?:inf|Inf|INF)$",
        r"^\.(?:nan|NaN|NAN)$",
        r"^[-+]?[0-9][0-9_]*(?::[0-5]?[0-9])+(?:\.[0-9_]*)?$",
        r"^[0-9]{4}-[0-9]{1,2}-[0-9]{1,2}(?:[Tt ].*)?$",
    )
]


@dataclasses.dataclass
class FrontmatterResult:
    """Outcome of ``parse``.

    ``data`` maps keys to values in file order (``metadata`` is a dict);
    ``body`` is everything after the closing delimiter; ``body_start_line``
    is the 1-based line of the body's first line in the original text;
    ``issues`` is empty exactly when the frontmatter is inside the subset.
    ``styles`` and ``lines`` give each key's scalar style (``plain``,
    ``double`` or ``map``) and line number, with metadata entries keyed as
    ``metadata.<key>``.
    """

    data: Dict[str, Any]
    body: str
    body_start_line: int
    issues: List[Issue]
    styles: Dict[str, str] = dataclasses.field(default_factory=dict)
    lines: Dict[str, int] = dataclasses.field(default_factory=dict)
    bom: bool = False

    @property
    def ok(self) -> bool:
        return not self.issues


def parse(text: str, *, source: str = "SKILL.md") -> FrontmatterResult:
    """Parse the frontmatter of ``text`` (a whole SKILL.md); never raises."""
    bom = text.startswith("\ufeff")
    if bom:
        text = text[1:]
    stripped = text.lstrip()
    first_line = text[: len(text) - len(stripped)].count("\n") + 1
    lines = stripped.split("\n")
    parser = _Parser(source, first_line)

    if _strip_cr(lines[0]) != "---":
        message = (
            "file must start with a '---' line"
            if not lines[0].startswith("---")
            else "opening delimiter must be exactly '---'"
        )
        parser.issue(0, "missing_open_delimiter", message)
        return parser.result("", first_line, bom)
    closing = next((i for i in range(1, len(lines)) if _strip_cr(lines[i]) == "---"), None)
    if closing is None:
        parser.issue(0, "missing_close_delimiter", "no closing '---' line")
        return parser.result("", first_line, bom)

    for index in range(1, closing):
        parser.feed(index, _strip_cr(lines[index]))
    parser.finish()
    return parser.result("\n".join(lines[closing + 1 :]), first_line + closing + 1, bom)


def _strip_cr(line: str) -> str:
    return line[:-1] if line.endswith("\r") else line


class _Parser:
    """Line-by-line state machine for the subset."""

    def __init__(self, source: str, first_line: int) -> None:
        self.source = source
        self.first_line = first_line
        self.data: Dict[str, Any] = {}
        self.styles: Dict[str, str] = {}
        self.lines: Dict[str, int] = {}
        self.issues: List[Issue] = []
        self.open_map: Optional[str] = None

    def issue(self, index: int, keyword: str, message: str) -> None:
        self.issues.append(Issue("%s:%d" % (self.source, self.first_line + index), keyword, message))

    def result(self, body: str, body_start_line: int, bom: bool) -> FrontmatterResult:
        return FrontmatterResult(self.data, body, body_start_line, self.issues, self.styles, self.lines, bom)

    def feed(self, index: int, line: str) -> None:
        if "\t" in line:
            self.issue(index, "tab", "tabs are not allowed in frontmatter")
            return
        if _CONTROL_RE.search(line):
            self.issue(index, "control_character", "control characters are not allowed")
            return
        if line.strip(" ") == "":
            return
        content = line.lstrip(" ")
        indent = len(line) - len(content)
        if content.startswith("#"):
            self.issue(index, "comment", "comments are not allowed in frontmatter")
        elif content == "-" or content.startswith("- "):
            self.issue(index, "list", "lists are not allowed in frontmatter")
        elif indent == 0:
            self.open_map = None
            self._top_level(index, content)
        elif indent == 2 and self.open_map is not None:
            self._map_entry(index, content)
        else:
            self.issue(
                index,
                "bad_indent",
                "unexpected indentation; values must fit on one line and only metadata entries are indented (2 spaces)",
            )

    def finish(self) -> None:
        for key, style in self.styles.items():
            if style == "map" and not self.data[key]:
                self.issue(self.lines[key] - self.first_line, "empty_map", "%r has no entries" % key)

    def _top_level(self, index: int, content: str) -> None:
        parsed = self._key_value(index, content)
        if parsed is None:
            return
        key, value_text = parsed
        if key in self.data:
            self.issue(index, "duplicate_key", "duplicate key %r" % key)
            return
        if value_text == "":
            if key != "metadata":
                self.issue(index, "empty_value", "key %r has no value" % key)
                return
            self.data[key], self.styles[key], self.lines[key] = {}, "map", self.first_line + index
            self.open_map = key
            return
        if key == "metadata":
            keyword, message = _leading_indicator_problem(value_text) or (
                "bad_metadata",
                "'metadata' must be a map of indented 'key: value' lines",
            )
            self.issue(index, keyword, message)
            return
        scalar = self._scalar(index, value_text)
        if scalar is not None:
            self.data[key], self.styles[key] = scalar
            self.lines[key] = self.first_line + index

    def _map_entry(self, index: int, content: str) -> None:
        parsed = self._key_value(index, content)
        if parsed is None:
            return
        key, value_text = parsed
        container = self.data[self.open_map]
        if key in container:
            self.issue(index, "duplicate_key", "duplicate key %r in %r" % (key, self.open_map))
            return
        if value_text == "":
            self.issue(index, "nested_map", "%r entries must be scalars; nested maps are not allowed" % self.open_map)
            return
        scalar = self._scalar(index, value_text)
        if scalar is not None:
            full_key = "%s.%s" % (self.open_map, key)
            container[key], self.styles[full_key] = scalar
            self.lines[full_key] = self.first_line + index

    def _key_value(self, index: int, content: str) -> Optional[Tuple[str, str]]:
        match = _KEY_LINE_RE.match(content)
        if match is None:
            self.issue(index, "bad_line", "expected 'key: value' with a plain key")
            return None
        return match.group(1), (match.group(2) or "").rstrip(" ")

    def _scalar(self, index: int, text: str) -> Optional[Tuple[Any, str]]:
        if text.startswith('"'):
            return self._double_quoted(index, text)
        if text in ("true", "false"):
            return text == "true", "plain"
        if any(pattern.match(text) for pattern in _AMBIGUOUS_PLAIN):
            self.issue(
                index, "ambiguous_scalar", "plain value %r is not a string in every YAML parser; quote it" % text
            )
            return None
        problem = _leading_indicator_problem(text)
        if problem is not None:
            self.issue(index, problem[0], problem[1])
            return None
        if " #" in text:
            self.issue(index, "comment", "' #' starts a comment in YAML; quote the value")
            return None
        if ": " in text or text.endswith(":"):
            self.issue(index, "bad_plain_scalar", "':' in a plain value is ambiguous; quote the value")
            return None
        return text, "plain"

    def _double_quoted(self, index: int, text: str) -> Optional[Tuple[Any, str]]:
        chars: List[str] = []
        position = 1
        while position < len(text):
            char = text[position]
            if char == "\\":
                following = text[position + 1 : position + 2]
                if following not in ('"', "\\"):
                    self.issue(index, "bad_escape", 'only \\" and \\\\ escapes are allowed')
                    return None
                chars.append(following)
                position += 2
                continue
            if char == '"':
                rest = text[position + 1 :].strip(" ")
                if rest == "":
                    return "".join(chars), "double"
                keyword = "comment" if rest.startswith("#") else "trailing_content"
                self.issue(index, keyword, "nothing may follow the closing quote")
                return None
            chars.append(char)
            position += 1
        self.issue(index, "unterminated_string", "double-quoted value must close on the same line")
        return None


def _leading_indicator_problem(text: str) -> Optional[Tuple[str, str]]:
    """Name the YAML construct a value starting with an indicator would be."""
    first = text[0]
    if first not in _LEADING_INDICATORS:
        return None
    if text == "-" or text.startswith("- "):
        return "list", "lists are not allowed in frontmatter"
    return _INDICATOR_PROBLEMS.get(first, ("bad_plain_scalar", "a plain value may not start with %r; quote it" % first))


# ---------------------------------------------------------------------------
# Field rules (CONVENTIONS §2)
# ---------------------------------------------------------------------------


def lint(result: FrontmatterResult, *, folder_name: Optional[str] = None, source: str = "SKILL.md") -> List[Issue]:
    """Check parsed frontmatter against the §2 field rules.

    Run it after ``parse`` (it inspects ``data``, ``styles`` and ``lines``).
    ``folder_name``, when given, must equal ``name``.
    """
    checker = _FieldChecker(result, source)
    checker.check_keys()
    checker.check_name(folder_name)
    checker.check_quoted_text("description", MAX_DESCRIPTION_LENGTH, required=True)
    checker.check_quoted_text("compatibility", MAX_COMPATIBILITY_LENGTH, required=False)
    checker.check_license()
    checker.check_metadata()
    checker.check_disable_model_invocation()
    return checker.issues


class _FieldChecker:
    def __init__(self, result: FrontmatterResult, source: str) -> None:
        self.data = result.data
        self.styles = result.styles
        self.lines = result.lines
        self.source = source
        self.issues: List[Issue] = []

    def add(self, key: str, keyword: str, message: str) -> None:
        line = self.lines.get(key) or self.lines.get(key.split(".")[0])
        path = "%s:%d" % (self.source, line) if line else self.source
        self.issues.append(Issue(path, keyword, message))

    def check_keys(self) -> None:
        for key in self.data:
            if key not in ALLOWED_KEYS:
                self.add(key, "unknown_key", "key %r is not allowed (allowed: %s)" % (key, ", ".join(ALLOWED_KEYS)))
        for key in REQUIRED_KEYS:
            if key not in self.data:
                self.add(key, "missing_key", "required key %r is missing" % key)

    def check_name(self, folder_name: Optional[str]) -> None:
        name = self.data.get("name")
        if name is None:
            return
        if not isinstance(name, str) or not NAME_RE.match(name) or len(name) > MAX_NAME_LENGTH:
            self.add("name", "name_pattern", "name must match ^[a-z0-9]+(-[a-z0-9]+)*$ and be at most 64 chars")
        elif name in RESERVED_NAMES:
            self.add("name", "name_reserved", "%r is a Zed built-in skill name" % name)
        elif folder_name is not None and name != folder_name:
            self.add("name", "name_folder_mismatch", "name %r must equal the folder name %r" % (name, folder_name))

    def check_quoted_text(self, key: str, limit: int, *, required: bool) -> None:
        if key not in self.data:
            return
        value = self.data[key]
        if self.styles.get(key) != "double" or not isinstance(value, str):
            self.add(key, "not_double_quoted", "%r must be a double-quoted string" % key)
            return
        if required and not value.strip():
            self.add(key, "empty_value", "%r must not be empty" % key)
        if len(value) > limit:
            self.add(key, "too_long", "%r is %d chars, limit %d" % (key, len(value), limit))

    def check_license(self) -> None:
        if "license" in self.data and not isinstance(self.data["license"], str):
            self.add("license", "not_string", "'license' must be a string")

    def check_metadata(self) -> None:
        metadata = self.data.get("metadata")
        if not isinstance(metadata, dict):
            return
        for key in REQUIRED_METADATA_KEYS:
            if key not in metadata:
                self.add("metadata", "missing_metadata_key", "metadata.%s is required" % key)
        for key, value in metadata.items():
            if not isinstance(value, str):
                self.add("metadata." + key, "not_string", "metadata.%s must be a string" % key)
        rules = (
            ("version", lambda v: SEMVER_RE.match(v), 'metadata.version must be semver like "0.1.0"'),
            ("family", lambda v: v in FAMILIES, "metadata.family must be one of %s" % ", ".join(FAMILIES)),
            ("spec", lambda v: SPEC_ID_RE.match(v), "metadata.spec must look like SPEC-001"),
            ("author", lambda v: v.strip(), "metadata.author must not be empty"),
        )
        for key, accept, message in rules:
            value = metadata.get(key)
            if isinstance(value, str) and not accept(value):
                self.add("metadata." + key, "bad_metadata_value", message)

    def check_disable_model_invocation(self) -> None:
        key = "disable-model-invocation"
        if key in self.data and not isinstance(self.data[key], bool):
            self.add(key, "not_boolean", "%r must be true or false" % key)
