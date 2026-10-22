"""skill-lab validate: check skills against every rule marked [V] in CONVENTIONS.md.

Output is a ``validation-report.v1`` payload: one entry per skill with its
findings (``rule``, ``severity``, ``message``, ``path``). Exit 0 when no skill
has an error finding (warnings are allowed), 1 otherwise, 2 for usage errors.

Rules always checked (CONVENTIONS §1-§6, §9):

- ``frontmatter.*``  the portable YAML subset and the §2 field rules; the
  description length target (350-900 chars) and "Use when" are warnings;
- ``body.*``         ≤ 250 lines and ≤ 12 KB, required headings in order, a
  numbered Procedure, and relative links (and skill paths in inline code)
  that resolve inside the skill folder;
- ``references.*``   ≤ 300 lines, a table of contents above 100 (warnings);
- ``scripts.*``      shebang, docstring, ``from __future__ import annotations``,
  executable bit, Python 3.9 grammar, stdlib-only imports (AST), no
  ``shell=True``/``eval``/``exec``, and ``--help`` exits 0 (20 s timeout);
- ``vendor.*``       vendored ``_skillkit`` and schemas identical to canonical,
  only known contracts in ``assets/schemas``, envelope schema present;
- ``evals.*``        every case is a valid ``benchmark-case.v1`` for this skill
  with ``id`` == file name, scripts and fixtures exist, and the tier minimums
  (≥ 4 deterministic, ≥ 2 agentic, ≥ 3 positive + ≥ 1 negative trigger);
- ``tests.missing``  at least one ``tests/test_*.py``;
- ``spec.*``         ``skill-lab/specs/NNN-*`` for ``metadata.spec`` with a
  ``spec.md`` and a ``traceability.json`` whose paths and test ids exist and
  whose every FR is traced and verified;
- ``install.*``      ``.agents/skills/<name>`` and ``.claude/skills/<name>``
  show the skill (missing is a warning, stale or foreign an error);
- ``scaffold.todo``  ``TODO(scaffold)`` markers left by ``skill-lab new`` (warning).

Runtime profiles (``--runtime zed,claude,codex``, default all) add: zed, a
flat ``skills/`` layout, ``SKILL.md`` ≤ 100 KB and a BOM as an error; zed and
codex, ``.agents/skills`` parity; claude, ``.claude/skills`` parity.

The catalog budget (names + descriptions of all skills ≤ 50 KB, warning above
40 KB) is reported in ``payload.catalog`` and as an envelope error or warning.
New rules hook in by appending a function to ``SKILL_CHECKS``.
"""

from __future__ import annotations

import ast
import concurrent.futures
import os
import re
import subprocess
import sys
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Sequence, Set, Tuple
from urllib.parse import unquote

from . import LAB_VERSION
from . import catalog as labcatalog
from . import cli as labcli
from . import install, paths
from _skillkit import EXIT_FAIL, EXIT_OK, frontmatter, jsonschema_mini, schemas, stdlib_modules
from _skillkit.cli import loads_strict, parse_now, to_iso
from _skillkit.envelope import ScriptError, ScriptResult, compact, error
from _skillkit.redact import SECRET_ENV_VARS

PROFILES = ("zed", "claude", "codex")
ERROR, WARNING = "error", "warning"

MAX_BODY_LINES = 250
MAX_BODY_BYTES = 12 * 1024
ZED_MAX_SKILL_FILE_BYTES = 100 * 1024
DESCRIPTION_TARGET = (350, 900)
HELP_TIMEOUT_S = 20
REFERENCE_MAX_LINES = 300
REFERENCE_TOC_LINES = 100
MIN_DETERMINISTIC, MIN_AGENTIC, MIN_TRIGGER_POSITIVE, MIN_TRIGGER_NEGATIVE = 4, 2, 3, 1
TODO_MARKER = "TODO(scaffold)"
SHEBANG = "#!/usr/bin/env python3"

REQUIRED_SECTIONS = ("When to use", "Inputs", "Procedure", "Outputs", "Guardrails", "Resources")
SECTION_ORDER = (
    "When to use",
    "When not to use",
    "Inputs",
    "Procedure",
    "Outputs",
    "Guardrails",
    "Resources",
    "Runtime notes",
)

_HEADING_RE = re.compile(r"^(#{1,6})[ \t]+(.*?)[ \t]*#*[ \t]*$")
_FENCE_RE = re.compile(r"^[ \t]{0,3}(```|~~~)")
_CODE_SPAN_RE = re.compile(r"`([^`\n]+)`")
_INLINE_LINK_RE = re.compile(r"!?\[[^\]\n]*\]\(\s*<?([^)\s>]+)>?(?:\s+(?:\"[^\"]*\"|'[^']*'|\([^)]*\)))?\s*\)")
_REFERENCE_LINK_RE = re.compile(r"^[ \t]{0,3}\[[^\]\n]+\]:[ \t]*<?([^\s>]+)>?")
_SCHEME_RE = re.compile(r"^[A-Za-z][A-Za-z0-9+.-]*:")
_SKILL_PATH_TOKEN_RE = re.compile(r"^(?:references|scripts|assets|evals)/[A-Za-z0-9_./-]+$")
_NUMBERED_STEP_RE = re.compile(r"^[ \t]*\d+[.)][ \t]+\S")
_TOC_HEADING_RE = re.compile(r"^#{1,3}[ \t]+(?:table of )?contents\b", re.IGNORECASE)
_FR_RE = re.compile(r"\*\*(FR-\d{3})\*\*")


class Finding(NamedTuple):
    rule: str
    severity: str
    message: str
    path: Optional[str]

    def to_dict(self) -> dict:
        return {"rule": self.rule, "severity": self.severity, "message": compact(self.message, 500), "path": self.path}


class Context:
    """One skill under validation: its paths, parsed SKILL.md, and the findings so far."""

    def __init__(self, layout: paths.Layout, name: str, profiles: Sequence[str], *, run_scripts: bool, shared: dict):
        self.layout = layout
        self.name = name
        self.dir = layout.skill_dir(name)
        self.profiles = tuple(profiles)
        self.run_scripts = run_scripts
        self.shared = shared
        self.findings: List[Finding] = []
        self.raw_size = 0
        self.fm: Optional[frontmatter.FrontmatterResult] = None
        self.has_frontmatter = False
        self.uses_skillkit = False
        self.spec_dir: Optional[str] = None

    def path(self, *parts: str) -> str:
        return os.path.join(self.dir, *parts)

    def rel(self, path: str) -> str:
        return self.layout.rel(path)

    def add(self, rule: str, severity: str, message: str, path: Optional[str] = None) -> None:
        self.findings.append(Finding(rule, severity, message, path))

    def error(self, rule: str, message: str, path: Optional[str] = None) -> None:
        self.add(rule, ERROR, message, path)

    def warn(self, rule: str, message: str, path: Optional[str] = None) -> None:
        self.add(rule, WARNING, message, path)

    @property
    def metadata(self) -> dict:
        value = self.fm.data.get("metadata") if self.fm is not None else None
        return value if isinstance(value, dict) else {}


# ---------------------------------------------------------------------------
# Frontmatter and body (CONVENTIONS §2)
# ---------------------------------------------------------------------------


def check_frontmatter(ctx: Context) -> None:
    skill_md = ctx.path(paths.SKILL_FILE)
    rel = ctx.rel(skill_md)
    try:
        with open(skill_md, "rb") as handle:
            raw = handle.read()
        text = raw.decode("utf-8")
    except OSError as exc:
        ctx.error("frontmatter.unreadable", "cannot read SKILL.md: %s" % (exc.strerror or exc), rel)
        return
    except UnicodeDecodeError:
        ctx.error("frontmatter.unreadable", "SKILL.md is not valid UTF-8", rel)
        return
    ctx.raw_size = len(raw)
    ctx.fm = parsed = frontmatter.parse(text, source=rel)
    if parsed.bom:
        severity = ERROR if "zed" in ctx.profiles else WARNING
        ctx.add(
            "frontmatter.bom", severity, "SKILL.md starts with a UTF-8 BOM; Zed's reader does not skip it", rel + ":1"
        )
    for issue in parsed.issues:
        ctx.error(_slug("frontmatter", issue.keyword), issue.message, issue.path)
    ctx.has_frontmatter = not any(i.keyword.endswith("_delimiter") for i in parsed.issues)
    if not parsed.ok:
        return  # field rules on a half-parsed block would only repeat these errors
    for issue in frontmatter.lint(parsed, folder_name=ctx.name, source=rel):
        ctx.error(_slug("frontmatter", issue.keyword), issue.message, issue.path)
    _check_description_style(ctx, parsed, rel)
    if parsed.data.get("disable-model-invocation") is True:
        ctx.warn(
            "frontmatter.disable-model-invocation",
            "disable-model-invocation is only for skills that perform consequential writes (none this release)",
            "%s:%d" % (rel, parsed.lines.get("disable-model-invocation", 1)),
        )


def _check_description_style(ctx: Context, parsed: frontmatter.FrontmatterResult, rel: str) -> None:
    description = parsed.data.get("description")
    if not isinstance(description, str) or not description.strip():
        return
    where = "%s:%d" % (rel, parsed.lines.get("description", 1))
    low, high = DESCRIPTION_TARGET
    if not low <= len(description) <= high:
        ctx.warn(
            "frontmatter.description-length",
            "description is %d chars; aim for %d-%d" % (len(description), low, high),
            where,
        )
    if "use when" not in description.lower():
        ctx.warn(
            "frontmatter.description-use-when", "description should say 'Use when ...' with trigger phrases", where
        )


def check_body(ctx: Context) -> None:
    if ctx.fm is None or not ctx.has_frontmatter:
        return
    rel = ctx.rel(ctx.path(paths.SKILL_FILE))
    body, start = ctx.fm.body, ctx.fm.body_start_line
    lines = _lines(body)
    if len(lines) > MAX_BODY_LINES:
        ctx.error("body.too-many-lines", "body has %d lines; limit %d" % (len(lines), MAX_BODY_LINES), rel)
    size = len(body.encode("utf-8"))
    if size > MAX_BODY_BYTES:
        ctx.error("body.too-large", "body is %d bytes; limit %d" % (size, MAX_BODY_BYTES), rel)
    outline = _outline(lines)
    _check_headings(ctx, outline, rel, start)
    _check_procedure(ctx, outline, lines, rel, start)
    for index, text, from_code in _link_targets(lines):
        _check_target(ctx, text, "%s:%d" % (rel, start + index), from_code=from_code)


class _Heading(NamedTuple):
    level: int
    title: str
    index: int


def _lines(text: str) -> List[str]:
    lines = text.split("\n")
    if lines and lines[-1] == "":
        lines.pop()
    return [line[:-1] if line.endswith("\r") else line for line in lines]


def _code_lines(lines: Sequence[str]) -> Set[int]:
    """Indexes of lines inside fenced code blocks (fence lines included)."""
    inside: Set[int] = set()
    fence: Optional[str] = None
    for index, line in enumerate(lines):
        match = _FENCE_RE.match(line)
        if fence is None and match:
            fence = match.group(1)
            inside.add(index)
        elif fence is not None:
            inside.add(index)
            if line.strip().startswith(fence):
                fence = None
    return inside


def _outline(lines: Sequence[str]) -> List[_Heading]:
    code = _code_lines(lines)
    headings = []
    for index, line in enumerate(lines):
        match = None if index in code else _HEADING_RE.match(line)
        if match:
            headings.append(_Heading(len(match.group(1)), match.group(2), index))
    return headings


def _check_headings(ctx: Context, outline: List[_Heading], rel: str, start: int) -> None:
    titles = [h for h in outline if h.level == 1]
    if not outline or outline[0].level != 1:
        ctx.error("body.title", "the body must start with one '# <Title>' heading", rel)
    elif len(titles) > 1:
        ctx.error("body.title", "only one '# ' heading is allowed", "%s:%d" % (rel, start + titles[1].index))
    sections = [h for h in outline if h.level == 2]
    known = {name.lower(): name for name in SECTION_ORDER}
    seen: Dict[str, _Heading] = {}
    for heading in sections:
        key = " ".join(heading.title.split()).lower()
        if key not in known:
            continue
        if key in seen:
            ctx.error(
                "body.heading-duplicate",
                "'## %s' appears more than once" % known[key],
                "%s:%d" % (rel, start + heading.index),
            )
            continue
        seen[key] = heading
    for name in REQUIRED_SECTIONS:
        if name.lower() not in seen:
            ctx.error("body.heading-missing", "required heading '## %s' is missing" % name, rel)
    found_order = sorted(seen, key=lambda key: seen[key].index)
    expected_order = [name.lower() for name in SECTION_ORDER if name.lower() in seen]
    if found_order != expected_order:
        ctx.error(
            "body.heading-order",
            "headings must follow the order: %s" % ", ".join(known[key] for key in expected_order),
            "%s:%d" % (rel, start + seen[found_order[0]].index) if found_order else rel,
        )
    notes = seen.get("runtime notes")
    if notes is not None and sections and sections[-1] is not notes:
        ctx.error(
            "body.heading-order", "'## Runtime notes' must be the last section", "%s:%d" % (rel, start + notes.index)
        )


def _check_procedure(ctx: Context, outline: List[_Heading], lines: Sequence[str], rel: str, start: int) -> None:
    sections = [h for h in outline if h.level <= 2]
    for position, heading in enumerate(sections):
        if heading.level == 2 and " ".join(heading.title.split()).lower() == "procedure":
            end = sections[position + 1].index if position + 1 < len(sections) else len(lines)
            if not any(_NUMBERED_STEP_RE.match(line) for line in lines[heading.index + 1 : end]):
                ctx.error(
                    "body.procedure-not-numbered",
                    "'## Procedure' must be numbered steps (1. 2. 3.)",
                    "%s:%d" % (rel, start + heading.index),
                )
            return


def _link_targets(lines: Sequence[str]) -> List[Tuple[int, str, bool]]:
    """``(line index, target, from_inline_code)`` for every link and skill path outside code fences."""
    code = _code_lines(lines)
    found = []
    for index, line in enumerate(lines):
        if index in code:
            continue
        for span in _CODE_SPAN_RE.findall(line):
            for token in span.split():
                token = token.rstrip(".,;:)")
                if _SKILL_PATH_TOKEN_RE.match(token):
                    found.append((index, token, True))
        prose = _CODE_SPAN_RE.sub("", line)
        found.extend((index, target, False) for target in _INLINE_LINK_RE.findall(prose))
        found.extend((index, target, False) for target in _REFERENCE_LINK_RE.findall(prose))
    return found


def _check_target(ctx: Context, target: str, where: str, *, from_code: bool) -> None:
    if not from_code and (_SCHEME_RE.match(target) or target.startswith(("#", "//"))):
        return  # URLs, mail links and in-page anchors
    relative = unquote(target.split("#", 1)[0].split("?", 1)[0])
    if not relative:
        return
    if relative.startswith("/") or "\\" in relative or re.match(r"^[A-Za-z]:", relative):
        ctx.error("body.link-escapes", "link %r must be a relative path inside the skill folder" % target, where)
        return
    resolved = os.path.normpath(os.path.join(ctx.dir, relative))
    if not paths.lexically_within(resolved, ctx.dir):
        ctx.error("body.link-escapes", "link %r leaves the skill folder; skills must be self-contained" % target, where)
    elif not os.path.exists(resolved):
        ctx.error("body.link-broken", "%r does not exist in the skill folder" % relative, where)


def check_references(ctx: Context) -> None:
    references = ctx.path("references")
    if not os.path.isdir(references):
        return
    for relative in paths.list_tree(references):
        if not relative.endswith(".md"):
            continue
        path = os.path.join(references, *relative.split("/"))
        try:
            with open(path, "r", encoding="utf-8") as handle:
                lines = _lines(handle.read())
        except (OSError, UnicodeDecodeError):
            ctx.error("references.unreadable", "reference is not readable UTF-8 text", ctx.rel(path))
            continue
        if len(lines) > REFERENCE_MAX_LINES:
            ctx.warn(
                "references.too-long",
                "%d lines; keep references to %d" % (len(lines), REFERENCE_MAX_LINES),
                ctx.rel(path),
            )
        if len(lines) > REFERENCE_TOC_LINES and not _has_toc(lines):
            ctx.warn(
                "references.no-toc", "over %d lines without a table of contents" % REFERENCE_TOC_LINES, ctx.rel(path)
            )


def _has_toc(lines: Sequence[str]) -> bool:
    head = lines[:40]
    return any(_TOC_HEADING_RE.match(line) or "](#" in line for line in head)


# ---------------------------------------------------------------------------
# Scripts (CONVENTIONS §3)
# ---------------------------------------------------------------------------


def check_scripts(ctx: Context) -> None:
    entries = paths.entry_scripts(ctx.dir)
    helpers = paths.helper_modules(ctx.dir)
    local = set(paths.local_module_names(ctx.dir)) | {"_skillkit"}
    runnable = [path for path in entries if _check_source(ctx, path, local, entry=True)]
    for path in helpers:
        _check_source(ctx, path, local, entry=False)
    if ctx.run_scripts and runnable:
        _check_help(ctx, runnable)


def _check_source(ctx: Context, path: str, local: Set[str], *, entry: bool) -> bool:
    """Static checks for one Python file; returns False when it cannot be parsed."""
    rel = ctx.rel(path)
    try:
        with open(path, "rb") as handle:
            source = handle.read().decode("utf-8")
    except (OSError, UnicodeDecodeError):
        ctx.error("scripts.unreadable", "not readable UTF-8 Python source", rel)
        return False
    if entry and _lines(source)[:1] != [SHEBANG]:
        ctx.error("scripts.shebang", "first line must be exactly %r" % SHEBANG, rel + ":1")
    try:
        tree = ast.parse(source, filename=rel, feature_version=(3, 9))
    except SyntaxError as exc:
        ctx.error("scripts.syntax", "%s (checked with Python 3.9 grammar)" % exc.msg, "%s:%s" % (rel, exc.lineno or 1))
        return False
    if ast.get_docstring(tree) is None:
        ctx.error("scripts.docstring", "a module docstring must follow the shebang", rel)
    if not _has_future_annotations(tree):
        ctx.error("scripts.future-import", "'from __future__ import annotations' must follow the docstring", rel)
    _check_imports(ctx, tree, rel, local)
    _check_dangerous_calls(ctx, tree, rel)
    if entry and os.name != "nt" and not os.stat(path).st_mode & 0o111:
        ctx.error("scripts.executable", "entry script is not executable (chmod +x)", rel)
    return True


def _has_future_annotations(tree: ast.Module) -> bool:
    return any(
        isinstance(node, ast.ImportFrom)
        and node.module == "__future__"
        and any(a.name == "annotations" for a in node.names)
        for node in tree.body
    )


def _check_imports(ctx: Context, tree: ast.Module, rel: str, local: Set[str]) -> None:
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            modules = [alias.name for alias in node.names]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            modules = [node.module]
        else:
            continue
        for module in modules:
            top = stdlib_modules.top_level(module)
            if top == "_skillkit":
                ctx.uses_skillkit = True
            if top in local or stdlib_modules.is_portable_stdlib(module):
                continue
            where = "%s:%d" % (rel, node.lineno)
            if stdlib_modules.is_known_stdlib(module):
                ctx.error(
                    "scripts.import-not-portable",
                    "%r is not in the standard library of both Python 3.9 and %d.%d" % (module, *sys.version_info[:2]),
                    where,
                )
            else:
                ctx.error(
                    "scripts.import-third-party",
                    "%r is not in the standard library; scripts are stdlib-only" % module,
                    where,
                )


def _check_dangerous_calls(ctx: Context, tree: ast.Module, rel: str) -> None:
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        where = "%s:%d" % (rel, node.lineno)
        if isinstance(node.func, ast.Name) and node.func.id in ("eval", "exec"):
            ctx.error("scripts.eval-exec", "%s() is forbidden; untrusted text is data" % node.func.id, where)
        for keyword in node.keywords:
            if keyword.arg == "shell" and isinstance(keyword.value, ast.Constant) and keyword.value.value is True:
                ctx.error("scripts.shell-true", "subprocess with shell=True is forbidden; pass a list of args", where)


def _check_help(ctx: Context, scripts: Sequence[str]) -> None:
    workers = min(8, len(scripts))
    with concurrent.futures.ThreadPoolExecutor(max_workers=workers) as pool:
        outcomes = list(pool.map(lambda script: _run_help(script, ctx.dir), scripts))
    for script, problem in zip(scripts, outcomes):  # noqa: B905 - strict= needs Python 3.10
        if problem:
            ctx.error("scripts.help", problem, ctx.rel(script))


def _run_help(script: str, cwd: str) -> Optional[str]:
    """Run ``script --help`` with list args; return a problem description or None."""
    try:
        proc = subprocess.run(
            [sys.executable, script, "--help"],
            cwd=cwd,
            env=script_env(),
            stdin=subprocess.DEVNULL,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            timeout=HELP_TIMEOUT_S,
        )
    except subprocess.TimeoutExpired:
        return "--help did not finish within %ds" % HELP_TIMEOUT_S
    except OSError as exc:
        return "--help could not run: %s" % (exc.strerror or exc)
    if proc.returncode != 0:
        tail = proc.stderr.decode("utf-8", "replace").strip().splitlines()[-1:] or ["no stderr"]
        return "--help exited %d: %s" % (proc.returncode, tail[0])
    return None


def script_env() -> Dict[str, str]:
    """Environment for running skill scripts: no secrets, no bytecode written into skill folders."""
    env = {key: value for key, value in os.environ.items() if key not in SECRET_ENV_VARS and key != "SKILLKIT_DEBUG"}
    env["PYTHONDONTWRITEBYTECODE"] = "1"
    return env


# ---------------------------------------------------------------------------
# Vendored copies (CONVENTIONS §1, §9.2)
# ---------------------------------------------------------------------------


def check_vendored(ctx: Context) -> None:
    layout = ctx.layout
    scripts_dir = ctx.path("scripts")
    vendored = os.path.join(scripts_dir, "_skillkit")
    if os.path.isdir(vendored) and not os.path.islink(vendored):
        diff = paths.compare_trees(layout.skillkit_dir, vendored)
        if diff:
            ctx.error(
                "vendor.skillkit-drift",
                "vendored _skillkit differs from canonical: %s (run skill-lab sync)" % diff.describe(),
                ctx.rel(vendored),
            )
    elif os.path.lexists(vendored):
        ctx.error(
            "vendor.skillkit-drift",
            "scripts/_skillkit must be a vendored folder, not a link or file",
            ctx.rel(vendored),
        )
    elif ctx.uses_skillkit:
        ctx.error(
            "vendor.skillkit-missing",
            "scripts import _skillkit but no vendored copy exists (run skill-lab sync)",
            ctx.rel(scripts_dir),
        )

    schemas_dir = ctx.path("assets", "schemas")
    canonical = set(paths.canonical_schema_files(layout))
    present = (
        sorted(n for n in os.listdir(schemas_dir) if not paths.is_ignored(n)) if os.path.isdir(schemas_dir) else []
    )
    for name in present:
        path = os.path.join(schemas_dir, name)
        if name not in canonical:
            ctx.error("vendor.schema-unknown", "not a canonical contract in skill-lab/contracts/schemas", ctx.rel(path))
        elif not paths.files_equal(os.path.join(layout.schemas_dir, name), path):
            ctx.error("vendor.schema-drift", "differs from the canonical contract (run skill-lab sync)", ctx.rel(path))
    if os.path.isdir(scripts_dir) and "envelope.v1.schema.json" not in present:
        ctx.error(
            "vendor.envelope-missing",
            "assets/schemas/envelope.v1.schema.json is required (run skill-lab sync)",
            ctx.rel(schemas_dir),
        )


# ---------------------------------------------------------------------------
# Evals (CONVENTIONS §5)
# ---------------------------------------------------------------------------


def check_evals(ctx: Context) -> None:
    counts = {"deterministic": 0, "agentic": 0, "positive": 0, "negative": 0}
    seen: Dict[str, str] = {}
    for path in paths.case_files(ctx.dir):
        case = _load_case(ctx, path)
        if case is None:
            continue
        rel = ctx.rel(path)
        stem = os.path.basename(path)[: -len(".json")]
        if case["id"] != stem:
            ctx.error("evals.case-id-mismatch", "id %r must equal the file name %r" % (case["id"], stem), rel)
        if case["id"] in seen:
            ctx.error("evals.case-id-duplicate", "id %r is also used by %s" % (case["id"], seen[case["id"]]), rel)
        seen.setdefault(case["id"], rel)
        if case["skill"] != ctx.name:
            ctx.error("evals.case-skill-mismatch", "skill %r must be %r" % (case["skill"], ctx.name), rel)
        _check_case_paths(ctx, case, rel)
        tier = case["tier"]
        if tier == "trigger":
            counts["positive" if case["expect_skill"] == ctx.name else "negative"] += 1
        else:
            counts[tier] += 1
    cases_dir = ctx.rel(ctx.path("evals", "cases"))
    for key, minimum, label in (
        ("deterministic", MIN_DETERMINISTIC, "deterministic"),
        ("agentic", MIN_AGENTIC, "agentic"),
        ("positive", MIN_TRIGGER_POSITIVE, "positive trigger"),
        ("negative", MIN_TRIGGER_NEGATIVE, "negative trigger"),
    ):
        if counts[key] < minimum:
            rule = "evals.%s-count" % label.replace(" ", "-")
            ctx.error(rule, "%d valid %s case(s); at least %d required" % (counts[key], label, minimum), cases_dir)


def _load_case(ctx: Context, path: str) -> Optional[dict]:
    rel = ctx.rel(path)
    try:
        with open(path, "r", encoding="utf-8") as handle:
            case = loads_strict(handle.read())
    except (OSError, UnicodeDecodeError, ValueError) as exc:
        ctx.error("evals.case-unreadable", "not strict UTF-8 JSON: %s" % exc, rel)
        return None
    issues = jsonschema_mini.validate(case, ctx.shared["case_schema"])
    for issue in issues[:3]:
        ctx.error("evals.case-schema", "%s: %s" % (issue.path or "/", issue.message), rel)
    if len(issues) > 3:
        ctx.error("evals.case-schema", "%d more schema issue(s)" % (len(issues) - 3), rel)
    return None if issues else case


def _check_case_paths(ctx: Context, case: dict, rel: str) -> None:
    tier = case["tier"]
    if tier == "deterministic":
        run = case["run"]
        if not os.path.isfile(ctx.path(*run["script"].split("/"))):
            ctx.error("evals.case-script-missing", "run.script %r does not exist" % run["script"], rel)
        if "stdin_file" in run and not os.path.exists(ctx.path(*run["stdin_file"].split("/"))):
            ctx.error("evals.fixture-missing", "run.stdin_file %r does not exist" % run["stdin_file"], rel)
        for arg in run["args"]:
            if _SKILL_PATH_TOKEN_RE.match(arg) and not os.path.exists(os.path.normpath(ctx.path(*arg.split("/")))):
                ctx.warn("evals.arg-path-missing", "argument %r names a skill path that does not exist" % arg, rel)
    elif tier == "agentic":
        for fixture in case["fixtures"]:
            if not os.path.exists(ctx.path(*fixture.split("/"))):
                ctx.error("evals.fixture-missing", "fixture %r does not exist" % fixture, rel)
        name, version = schemas.parse_urn(case["output_schema"])
        if schemas.schema_filename(name, version) not in ctx.shared["canonical_schemas"]:
            ctx.error(
                "evals.output-schema-unknown",
                "output_schema %s is not a canonical contract" % case["output_schema"],
                rel,
            )
    else:
        expected = case["expect_skill"]
        if expected is not None and expected != ctx.name and expected not in ctx.shared["skills"]:
            ctx.warn("evals.trigger-unknown-skill", "expect_skill %r is not a skill in skills/" % expected, rel)


def check_tests(ctx: Context) -> None:
    tests_dir = ctx.path("tests")
    found = os.path.isdir(tests_dir) and any(
        name.startswith("test_") and name.endswith(".py") for name in os.listdir(tests_dir)
    )
    if not found:
        ctx.error("tests.missing", "at least one tests/test_*.py (unittest) is required", ctx.rel(tests_dir))


# ---------------------------------------------------------------------------
# Spec and traceability (CONVENTIONS §6)
# ---------------------------------------------------------------------------


def check_spec(ctx: Context) -> None:
    spec_id = ctx.metadata.get("spec")
    if not isinstance(spec_id, str) or not frontmatter.SPEC_ID_RE.match(spec_id):
        return  # already reported by the frontmatter rules
    number = spec_id[len("SPEC-") :]
    specs_dir = ctx.layout.specs_dir
    matches = sorted(
        entry
        for entry in (os.listdir(specs_dir) if os.path.isdir(specs_dir) else [])
        if entry.startswith(number + "-") and os.path.isdir(os.path.join(specs_dir, entry))
    )
    specs_rel = ctx.rel(specs_dir)
    if not matches:
        ctx.error("spec.missing", "no folder %s/%s-<name> for %s" % (specs_rel, number, spec_id), specs_rel)
        return
    if len(matches) > 1:
        ctx.error("spec.ambiguous", "several folders for %s: %s" % (spec_id, ", ".join(matches)), specs_rel)
        return
    ctx.spec_dir = folder = os.path.join(specs_dir, matches[0])
    if matches[0] != "%s-%s" % (number, ctx.name):
        ctx.warn("spec.folder-name", "spec folder should be named %s-%s" % (number, ctx.name), ctx.rel(folder))
    spec_md = os.path.join(folder, "spec.md")
    spec_text = _read_text(spec_md)
    if spec_text is None:
        ctx.error("spec.md-missing", "spec.md is missing or unreadable", ctx.rel(spec_md))
    _check_traceability(ctx, spec_id, os.path.join(folder, "traceability.json"), spec_text or "")


def _check_traceability(ctx: Context, spec_id: str, path: str, spec_text: str) -> None:
    rel = ctx.rel(path)
    text = _read_text(path)
    if text is None:
        ctx.error("spec.traceability-missing", "traceability.json is missing or unreadable", rel)
        return
    try:
        trace = loads_strict(text)
    except ValueError as exc:
        ctx.error("spec.traceability-invalid", "not strict JSON: %s" % exc, rel)
        return
    requirements = trace.get("requirements") if isinstance(trace, dict) else None
    if not isinstance(requirements, list) or not all(_is_requirement(item) for item in requirements):
        ctx.error(
            "spec.traceability-invalid",
            "expected {spec, requirements: [{id, implemented_by: [...], verified_by: [...]}]}",
            rel,
        )
        return
    if trace.get("spec") != spec_id:
        ctx.error("spec.traceability-mismatch", "spec is %r; expected %r" % (trace.get("spec"), spec_id), rel)
    for item in requirements:
        if not item["verified_by"]:
            ctx.error("spec.fr-unverified", "%s has no verified_by entry" % item["id"], rel)
        severity = WARNING if item.get("planned") is True else ERROR
        for reference in item["implemented_by"] + item["verified_by"]:
            problem = _trace_problem(ctx, reference)
            if problem:
                ctx.add(problem[0], severity, "%s: %s" % (item["id"], problem[1]), rel)
    traced = {item["id"] for item in requirements}
    for fr in sorted(set(_FR_RE.findall(spec_text)) - traced):
        ctx.error("spec.fr-untraced", "%s is in spec.md but not in traceability.json" % fr, rel)


def _is_requirement(item: Any) -> bool:
    return (
        isinstance(item, dict)
        and isinstance(item.get("id"), str)
        and all(
            isinstance(item.get(key), list) and all(isinstance(v, str) for v in item[key])
            for key in ("implemented_by", "verified_by")
        )
    )


def _trace_problem(ctx: Context, reference: str) -> Optional[Tuple[str, str]]:
    """Return ``(rule, message)`` when a traceability path or test id does not resolve."""
    parts = reference.split("::")
    root = ctx.layout.repo_root
    resolved = os.path.normpath(os.path.join(root, *parts[0].split("/")))
    if not parts[0] or os.path.isabs(parts[0]) or not paths.lexically_within(resolved, root):
        return "spec.trace-path-missing", "%r is not a path inside the repository" % reference
    if not os.path.exists(resolved):
        return "spec.trace-path-missing", "%r does not exist" % parts[0]
    if len(parts) == 1 or not parts[0].endswith(".py"):
        return None
    tests = ctx.shared["test_index"].setdefault(resolved, _test_index(resolved))
    if len(parts) != 3 or parts[2] not in tests.get(parts[1], ()):
        return "spec.trace-test-missing", "%r is not a test method in that file" % reference
    return None


def _test_index(path: str) -> Dict[str, Set[str]]:
    """Map class name -> test method names defined in a unittest file."""
    try:
        with open(path, "r", encoding="utf-8") as handle:
            tree = ast.parse(handle.read())
    except (OSError, UnicodeDecodeError, SyntaxError, ValueError):
        return {}
    return {
        node.name: {
            item.name
            for item in node.body
            if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)) and item.name.startswith("test")
        }
        for node in tree.body
        if isinstance(node, ast.ClassDef)
    }


def _read_text(path: str) -> Optional[str]:
    try:
        with open(path, "r", encoding="utf-8") as handle:
            return handle.read()
    except (OSError, UnicodeDecodeError):
        return None


# ---------------------------------------------------------------------------
# Install parity, runtime limits, scaffold markers
# ---------------------------------------------------------------------------


def check_install(ctx: Context) -> None:
    runtimes = [name for name in ctx.profiles if name in paths.RUNTIME_SKILL_DIRS]
    for target_dir, names in install.runtime_targets(ctx.layout.repo_root, runtimes):
        dest = os.path.join(target_dir, ctx.name)
        state = install.classify(ctx.layout, dest, ctx.dir)
        if state == install.MISSING:
            ctx.warn(
                "install.not-installed",
                "not installed for %s (run skill-lab install)" % ", ".join(names),
                ctx.rel(dest),
            )
        elif state not in install.INSTALLED:
            ctx.error(
                "install.parity",
                "%s shows %s content, not skills/%s (run skill-lab install)" % (", ".join(names), state, ctx.name),
                ctx.rel(dest),
            )


def check_zed_limits(ctx: Context) -> None:
    if "zed" in ctx.profiles and ctx.raw_size > ZED_MAX_SKILL_FILE_BYTES:
        ctx.error(
            "zed.skill-file-too-large",
            "SKILL.md is %d bytes; Zed refuses files over %d" % (ctx.raw_size, ZED_MAX_SKILL_FILE_BYTES),
            ctx.rel(ctx.path(paths.SKILL_FILE)),
        )


def check_todo_markers(ctx: Context) -> None:
    # assets/ is excluded: output templates (skill-forge ships the scaffold) may carry the marker on purpose.
    files = [
        ctx.path(*relative.split("/"))
        for relative in paths.list_tree(ctx.dir)
        if relative.endswith((".md", ".py", ".json")) and not relative.startswith(("scripts/_skillkit/", "assets/"))
    ]
    if ctx.spec_dir:
        files += [os.path.join(ctx.spec_dir, name) for name in ("spec.md", "traceability.json")]
    for path in files:
        text = _read_text(path)
        if text and TODO_MARKER in text:
            line = text[: text.index(TODO_MARKER)].count("\n") + 1
            count = text.count(TODO_MARKER)
            ctx.warn(
                "scaffold.todo",
                "%d %s marker(s) left to fill in" % (count, TODO_MARKER),
                "%s:%d" % (ctx.rel(path), line),
            )


SKILL_CHECKS: List[Callable[[Context], None]] = [
    check_frontmatter,
    check_body,
    check_references,
    check_scripts,
    check_vendored,
    check_evals,
    check_tests,
    check_spec,
    check_install,
    check_zed_limits,
    check_todo_markers,
]
"""Per-skill checks, run in order. Later rules hook in by appending here."""


# ---------------------------------------------------------------------------
# Repository level
# ---------------------------------------------------------------------------


def validate_skill(
    layout: paths.Layout, name: str, profiles: Sequence[str], *, run_scripts: bool, shared: dict
) -> dict:
    """Run every check for one skill and return its ``skill_result`` entry."""
    ctx = Context(layout, name, profiles, run_scripts=run_scripts, shared=shared)
    for check in SKILL_CHECKS:
        check(ctx)
    findings = [finding.to_dict() for finding in ctx.findings]
    return {"name": name, "ok": not any(f["severity"] == ERROR for f in findings), "findings": findings}


def _flat_layout_results(layout: paths.Layout) -> List[dict]:
    """Zed only discovers skills/<name>/SKILL.md; report folders that hide nested skills."""
    results = []
    for folder in paths.non_skill_folders(layout):
        root = layout.skill_dir(folder)
        nested = [rel for rel in paths.list_tree(root) if rel.endswith("/" + paths.SKILL_FILE)]
        if nested:
            finding = Finding(
                "zed.flat-layout",
                ERROR,
                "nested skills are not discovered by Zed: %s; move them to skills/<name>/" % ", ".join(nested[:5]),
                layout.rel(root),
            )
            results.append({"name": folder, "ok": False, "findings": [finding.to_dict()]})
    return results


def validate_repo(
    layout: paths.Layout,
    *,
    names: Optional[Sequence[str]] = None,
    profiles: Sequence[str] = PROFILES,
    run_scripts: bool = True,
) -> Tuple[List[dict], dict, List[dict], List[dict]]:
    """Validate skills; return ``(skill results, catalog, global errors, global warnings)``."""
    all_names = paths.skill_names(layout)
    shared = {
        "case_schema": schemas.load_schema("benchmark-case", [layout.schemas_dir]),
        "canonical_schemas": set(paths.canonical_schema_files(layout)),
        "skills": set(all_names),
        "test_index": {},
    }
    targets = list(names) if names else all_names
    results = [validate_skill(layout, name, profiles, run_scripts=run_scripts, shared=shared) for name in targets]
    if "zed" in profiles and not names:
        results.extend(_flat_layout_results(layout))

    errors: List[dict] = []
    warnings: List[dict] = []
    if not all_names:
        warnings.append(error("NO_SKILLS", "no skill folders with SKILL.md under skills/", "skills"))
    if not run_scripts:
        warnings.append(error("SCRIPTS_NOT_RUN", "--no-run: the --help check was skipped"))
    document, skipped = labcatalog.build_catalog(layout)
    size = document["catalog_bytes"]
    if size > labcatalog.CATALOG_LIMIT_BYTES:
        errors.append(
            error(
                "CATALOG_BUDGET_EXCEEDED",
                "names + descriptions are %d bytes; Zed's limit is %d" % (size, labcatalog.CATALOG_LIMIT_BYTES),
                "skills",
            )
        )
    elif size > labcatalog.CATALOG_WARN_BYTES:
        warnings.append(
            error(
                "CATALOG_BUDGET_NEAR",
                "names + descriptions are %d bytes; warn above %d, limit %d"
                % (size, labcatalog.CATALOG_WARN_BYTES, labcatalog.CATALOG_LIMIT_BYTES),
                "skills",
            )
        )
    if all_names:
        current = labcatalog.read_current(layout)
        if current is None:
            warnings.append(
                error(
                    "CATALOG_MISSING",
                    "skills/CATALOG.json does not exist; run skill-lab catalog",
                    "skills/CATALOG.json",
                )
            )
        elif current != labcatalog.render(document):
            warnings.append(
                error(
                    "CATALOG_STALE", "skills/CATALOG.json is out of date; run skill-lab catalog", "skills/CATALOG.json"
                )
            )
    catalog = {"bytes": size, "limit": labcatalog.CATALOG_LIMIT_BYTES}
    return results, catalog, errors, warnings + skipped


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    """``skill-lab validate [--skill NAME]... [--runtime zed,claude,codex|all] [--no-run]``."""
    return labcli.run_command(lambda: _run(argv), command="validate", kind="validation-report", argv=argv)


def _run(argv: Sequence[str]) -> ScriptResult:
    parser = labcli.command_parser("validate", "Check skills against every [V] rule in CONVENTIONS.md.")
    parser.add_argument("--skill", action="append", metavar="NAME", help="validate only this skill (repeatable)")
    parser.add_argument(
        "--runtime",
        action="append",
        metavar="LIST",
        help="runtime profiles: zed, claude, codex or all, comma-separated or repeated (default: all)",
    )
    parser.add_argument("--no-run", action="store_true", help="do not execute scripts (skips the --help check)")
    args = parser.parse_args(list(argv))
    layout = labcli.layout_from(args)
    profiles = parse_profiles(args.runtime)
    names = _selected(layout, args.skill)
    now = parse_now(args.now)

    results, catalog, global_errors, global_warnings = validate_repo(
        layout, names=names, profiles=profiles, run_scripts=not args.no_run
    )
    findings = [finding for result in results for finding in result["findings"]]
    error_count = sum(1 for f in findings if f["severity"] == ERROR) + len(global_errors)
    warning_count = sum(1 for f in findings if f["severity"] == WARNING) + len(global_warnings)
    ok = error_count == 0
    payload = {
        "schema_version": 1,
        "target": _target(names),
        "runtime_profiles": list(profiles),
        "ok": ok,
        "skills": results,
        "catalog": catalog,
        "summary": {"errors": error_count, "warnings": warning_count},
        "lab_version": LAB_VERSION,
        "generated_at": to_iso(now),
    }
    if ok:
        return ScriptResult(EXIT_OK, payload, [], labcli.capped(global_warnings))
    finding_errors = [
        error(labcli.rule_code(f["rule"]), "%s: %s" % (result["name"], f["message"]), f["path"])
        for result in results
        for f in result["findings"]
        if f["severity"] == ERROR
    ]
    return ScriptResult(
        EXIT_FAIL, payload, labcli.capped(global_errors + finding_errors), labcli.capped(global_warnings)
    )


def parse_profiles(values: Optional[Sequence[str]]) -> Tuple[str, ...]:
    """``--runtime`` values to an ordered tuple of profiles; ``all`` (or nothing) means every runtime."""
    requested = paths.split_csv(values)
    if not requested or "all" in requested:
        return PROFILES
    unknown = [name for name in requested if name not in PROFILES]
    if unknown:
        raise ScriptError(
            "USAGE", "unknown runtime %s; expected zed, claude, codex or all" % ", ".join(unknown), path="--runtime"
        )
    return tuple(name for name in PROFILES if name in requested)


def _selected(layout: paths.Layout, requested: Optional[Sequence[str]]) -> Optional[List[str]]:
    if not requested:
        return None
    available = set(paths.skill_names(layout))
    wanted = paths.unique(requested)
    missing = [name for name in wanted if name not in available]
    if missing:
        raise ScriptError("SKILL_NOT_FOUND", "no skill folder with SKILL.md: %s" % ", ".join(missing), path="skills")
    return wanted


def _target(names: Optional[Sequence[str]]) -> str:
    if not names:
        return "skills"
    return compact(", ".join("skills/" + name for name in names), 500)


def _slug(prefix: str, keyword: str) -> str:
    return "%s.%s" % (prefix, keyword.replace("_", "-"))
