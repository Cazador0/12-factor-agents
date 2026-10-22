"""skill-lab new: scaffold ``skills/<name>/`` and its spec from ``skill-lab/templates/skill``.

The template renders into a complete skill that passes ``skill-lab validate``
with zero errors as generated: SKILL.md with every required heading, a
contract-following ``scripts/example.py``, the minimum eval inventory (4
deterministic, 2 agentic, 3 + 1 trigger cases) as schema-valid stubs, a unit
test, ``references/README.md``, and a spec stub with complete traceability
under ``skill-lab/specs/NNN-<name>/``. ``_skillkit`` and the envelope schema
are then vendored with the same code as ``skill-lab sync``.

Every place the author must fill in carries ``TODO(scaffold)``, which validate
reports as ``scaffold.todo`` warnings until none remain.

Spec numbers and families follow the CONVENTIONS §6 table: a skill listed
there gets its assigned ``SPEC-NNN`` and family, and ``--spec`` or ``--family``
values that contradict the table exit 2 (``SPEC_ASSIGNED``, ``FAMILY_ASSIGNED``).
Any other skill gets the lowest SPEC-001..099 number that is neither used nor
reserved by the table. A spec written first (spec-first delivery, ADR-0013) at
``skill-lab/specs/NNN-<name>/`` is kept as it is and only the skill is rendered.

Refusals: an invalid name exits 2 (``INVALID_NAME``); a reserved name
(``create-skill``), an existing skill folder, a spec number used by another
spec or skill, or one the table reserves for another skill exits 4.
The skill and its spec are rendered into hidden staging folders and renamed
into place, so a failure never leaves a half-written skill behind.
"""

from __future__ import annotations

import os
import re
import shutil
import tempfile
from typing import Any, Collection, Dict, List, NamedTuple, Optional, Sequence, Tuple

from . import cli as labcli
from . import paths, sync
from _skillkit import EXIT_OK, EXIT_REFUSED, EXIT_USAGE, frontmatter
from _skillkit.cli import parse_now
from _skillkit.envelope import ScriptError, ScriptResult

TEMPLATE_SUFFIX = ".tmpl"
SPEC_TEMPLATE = "_spec"
TODO_MARKER = "TODO(scaffold)"
SKILL_SPEC_NUMBERS = range(1, 100)
"""SPEC-001..099 are skill specs; 100+ belong to the lab and to releases (CONVENTIONS §6)."""

DEFAULT_FAMILY = "meta"
DEFAULT_DESCRIPTION = (
    "TODO(scaffold): replace this description. Say in one sentence what {name} does and which JSON "
    "contract it returns, so an agent can tell it apart from neighbouring skills. Use when the user asks "
    "to <first concrete trigger phrase>, <second trigger phrase>, or <third trigger phrase>. Do not use "
    "for <a neighbouring task>; the <neighbour-skill> skill handles that instead."
)
MAX_AUTHOR_LENGTH = 200

_PLACEHOLDER_RE = re.compile(r"\{\{\s*([a-z_]+)\s*\}\}")
_SPEC_FOLDER_RE = re.compile(r"^([0-9]{3})-")
_CATALOG_HEADING = "## 6. Specs, ADRs, traceability"
_CATALOG_ROW_RE = re.compile(r"^\| SPEC-(0[0-9]{2}) \| `([a-z0-9]+(?:-[a-z0-9]+)*)` \| ([a-z-]+) \|$", re.MULTILINE)

PAYLOAD_SCHEMA: Dict[str, Any] = {
    "description": "lab-scaffold payload: the skill and spec that skill-lab new created (or would create).",
    "type": "object",
    "required": [
        "schema_version",
        "name",
        "spec",
        "family",
        "dry_run",
        "skill_path",
        "spec_path",
        "files",
        "spec_created",
        "todo_marker",
        "next_steps",
    ],
    "properties": {
        "schema_version": {"const": 1},
        "name": {"type": "string", "pattern": "^[a-z0-9]+(-[a-z0-9]+)*$"},
        "spec": {"type": "string", "pattern": "^SPEC-[0-9]{3}$"},
        "family": {"enum": list(frontmatter.FAMILIES)},
        "dry_run": {"type": "boolean"},
        "skill_path": {"type": "string"},
        "spec_path": {"type": "string"},
        "files": {"type": "array", "items": {"type": "string"}, "minItems": 1},
        "spec_created": {
            "type": "boolean",
            "description": "false when an existing skill-lab/specs/NNN-<name>/ was kept instead of rendering the stub",
        },
        "todo_marker": {"const": TODO_MARKER},
        "next_steps": {"type": "array", "items": {"type": "string"}},
    },
    "additionalProperties": False,
}


class TemplateError(ScriptError):
    """The template itself is broken (unknown placeholder, missing folder)."""

    def __init__(self, message: str, path: Optional[str] = None) -> None:
        super().__init__("TEMPLATE_INVALID", message, path=path, exit_code=EXIT_USAGE)


def render_text(text: str, values: Dict[str, str], *, source: str = "template") -> str:
    """Replace every ``{{key}}``; an unknown key is a template bug."""

    def substitute(match: "re.Match[str]") -> str:
        key = match.group(1)
        if key not in values:
            raise TemplateError("unknown placeholder {{%s}}" % key, path=source)
        return values[key]

    return _PLACEHOLDER_RE.sub(substitute, text)


def template_files(layout: paths.Layout) -> List[Tuple[str, str, str]]:
    """``(source, area, relative destination)`` for every template file; area is ``skill`` or ``spec``."""
    root = layout.templates_dir
    if not os.path.isdir(root):
        raise TemplateError("template folder is missing", path=layout.rel(root))
    found = []
    for relative in paths.list_tree(root):
        top = relative.split("/", 1)[0]
        if top.startswith("_") and top != SPEC_TEMPLATE:
            continue  # scaffold-internal documentation
        area, destination = ("spec", relative.split("/", 1)[1]) if top == SPEC_TEMPLATE else ("skill", relative)
        if destination.endswith(TEMPLATE_SUFFIX):
            destination = destination[: -len(TEMPLATE_SUFFIX)]
        found.append((os.path.join(root, *relative.split("/")), area, destination))
    return found


class PlannedSkill(NamedTuple):
    """A skill row of the CONVENTIONS §6 spec table."""

    number: int
    family: str


def planned_skills(layout: paths.Layout) -> Dict[str, PlannedSkill]:
    """Skills that CONVENTIONS §6 assigns a spec number and family; empty when the file is absent."""
    try:
        with open(layout.conventions_path, "r", encoding="utf-8") as handle:
            text = handle.read()
    except (OSError, UnicodeDecodeError):
        return {}
    _before, found, after = text.partition(_CATALOG_HEADING)
    if not found:
        return {}
    section = after.split("\n## ", 1)[0]
    return {
        name: PlannedSkill(int(number), family)
        for number, name, family in _CATALOG_ROW_RE.findall(section)
        if family in frontmatter.FAMILIES
    }


def existing_spec(layout: paths.Layout, name: str) -> Optional[int]:
    """The number of an existing ``skill-lab/specs/NNN-<name>/`` folder, written before the skill."""
    if not os.path.isdir(layout.specs_dir):
        return None
    for entry in sorted(os.listdir(layout.specs_dir)):
        match = _SPEC_FOLDER_RE.match(entry)
        if match and entry[4:] == name and os.path.isdir(os.path.join(layout.specs_dir, entry)):
            return int(match.group(1))
    return None


def used_spec_numbers(layout: paths.Layout, *, ignore: Collection[str] = ()) -> List[int]:
    """Spec numbers taken by a spec folder (except those named in ``ignore``) or by any skill's ``metadata.spec``."""
    used = set()
    if os.path.isdir(layout.specs_dir):
        for entry in os.listdir(layout.specs_dir):
            match = _SPEC_FOLDER_RE.match(entry)
            if match and entry not in ignore:
                used.add(int(match.group(1)))
    for name in paths.skill_names(layout):
        spec = _skill_spec(layout, name)
        if spec:
            used.add(int(spec[len("SPEC-") :]))
    return sorted(used)


def _skill_spec(layout: paths.Layout, name: str) -> Optional[str]:
    try:
        with open(os.path.join(layout.skill_dir(name), paths.SKILL_FILE), "r", encoding="utf-8") as handle:
            metadata = frontmatter.parse(handle.read()).data.get("metadata")
    except (OSError, UnicodeDecodeError):
        return None
    spec = metadata.get("spec") if isinstance(metadata, dict) else None
    return spec if isinstance(spec, str) and frontmatter.SPEC_ID_RE.match(spec) else None


def allocate_spec(layout: paths.Layout, requested: Optional[str], *, name: Optional[str] = None) -> int:
    """The spec number for skill ``name``.

    The number CONVENTIONS §6 assigns to ``name``, or the number of its existing spec folder, wins;
    ``--spec`` must agree with it. Any other skill gets ``--spec`` or the lowest free number the
    table does not reserve.
    """
    planned = planned_skills(layout)
    assigned = planned.get(name) if name else None
    own = existing_spec(layout, name) if name else None
    if assigned is not None and own is not None and assigned.number != own:
        raise ScriptError(
            "SPEC_ASSIGNED",
            "CONVENTIONS §6 assigns SPEC-%03d to %s, but its spec folder is numbered %03d"
            % (assigned.number, name, own),
            path="skill-lab/specs/%03d-%s" % (own, name),
            exit_code=EXIT_USAGE,
        )
    expected = assigned.number if assigned is not None else own
    number = _requested_number(requested) if requested is not None else expected
    if expected is not None and number != expected:
        raise ScriptError(
            "SPEC_ASSIGNED",
            "%s belongs to SPEC-%03d (CONVENTIONS §6 or its spec folder); drop --spec or pass that" % (name, expected),
            path="--spec",
            exit_code=EXIT_USAGE,
        )
    reserved = {entry.number: other for other, entry in planned.items() if other != name}
    used = set(used_spec_numbers(layout, ignore=() if own is None else ("%03d-%s" % (own, name),)))
    if number is None:
        for candidate in SKILL_SPEC_NUMBERS:
            if candidate not in used and candidate not in reserved:
                return candidate
        raise ScriptError("NO_SPEC_NUMBER", "SPEC-001..099 are all taken; pass --spec", exit_code=EXIT_REFUSED)
    if number in reserved:
        raise ScriptError(
            "SPEC_RESERVED",
            "SPEC-%03d is reserved for %s by CONVENTIONS §6" % (number, reserved[number]),
            path="--spec",
            exit_code=EXIT_REFUSED,
        )
    if number in used:
        raise ScriptError(
            "SPEC_EXISTS",
            "SPEC-%03d is already used by a spec folder or a skill" % number,
            path="--spec",
            exit_code=EXIT_REFUSED,
        )
    return number


def _requested_number(requested: str) -> int:
    if not frontmatter.SPEC_ID_RE.match(requested):
        raise ScriptError("INVALID_SPEC", "--spec must look like SPEC-014", path="--spec", exit_code=EXIT_USAGE)
    return int(requested[len("SPEC-") :])


def resolve_family(layout: paths.Layout, name: str, requested: Optional[str]) -> str:
    """``--family``, which must agree with CONVENTIONS §6 for a listed skill; else the table's or ``meta``."""
    assigned = planned_skills(layout).get(name)
    if assigned is None:
        return requested or DEFAULT_FAMILY
    if requested is not None and requested != assigned.family:
        raise ScriptError(
            "FAMILY_ASSIGNED",
            "CONVENTIONS §6 puts %s in family %s" % (name, assigned.family),
            path="--family",
            exit_code=EXIT_USAGE,
        )
    return assigned.family


def check_name(layout: paths.Layout, name: str) -> None:
    """Refuse names that are invalid (exit 2), reserved or already taken (exit 4)."""
    if not frontmatter.NAME_RE.match(name) or len(name) > frontmatter.MAX_NAME_LENGTH:
        raise ScriptError(
            "INVALID_NAME",
            "name must match ^[a-z0-9]+(-[a-z0-9]+)*$ and be at most 64 chars",
            path=name,
            exit_code=EXIT_USAGE,
        )
    if name in frontmatter.RESERVED_NAMES:
        raise ScriptError(
            "SKILL_NAME_RESERVED", "%r is a Zed built-in skill name" % name, path=name, exit_code=EXIT_REFUSED
        )
    if os.path.lexists(layout.skill_dir(name)):
        raise ScriptError(
            "SKILL_EXISTS",
            "skills/%s already exists; refusing to overwrite it" % name,
            path="skills/" + name,
            exit_code=EXIT_REFUSED,
        )


def yaml_quoted(text: str, *, option: str, limit: int) -> str:
    """Escape ``text`` for a one-line double-quoted frontmatter value (only ``\\"`` and ``\\\\``)."""
    if not text.strip() or len(text) > limit or "\n" in text or "\r" in text:
        raise ScriptError(
            "INVALID_TEXT",
            "%s must be one non-empty line of at most %d chars" % (option, limit),
            path=option,
            exit_code=EXIT_USAGE,
        )
    return text.replace("\\", "\\\\").replace('"', '\\"')


def title_of(name: str) -> str:
    return " ".join(part.capitalize() for part in name.split("-"))


# ---------------------------------------------------------------------------
# Command
# ---------------------------------------------------------------------------


def main(argv: Sequence[str]) -> int:
    """``skill-lab new NAME [--family F] [--spec SPEC-NNN] [--description TEXT] [--author TEXT] [--dry-run]``."""
    return labcli.run_command(lambda: _run(argv), command="new", kind="lab-scaffold", argv=argv)


def _parser():
    parser = labcli.command_parser("new", "Scaffold skills/<name>/ and skill-lab/specs/NNN-<name>/ from the template.")
    parser.add_argument("name", help="skill name: lowercase letters, digits and hyphens, at most 64 chars")
    parser.add_argument(
        "--family",
        choices=frontmatter.FAMILIES,
        help="metadata.family (default: the CONVENTIONS §6 family, else %s)" % DEFAULT_FAMILY,
    )
    parser.add_argument(
        "--spec",
        metavar="SPEC-NNN",
        help="spec id (default: the CONVENTIONS §6 number or the existing spec folder's, else the lowest free one)",
    )
    parser.add_argument(
        "--description", metavar="TEXT", help="one-line description (default: a TODO(scaffold) placeholder)"
    )
    parser.add_argument("--author", metavar="TEXT", help="metadata.author (default: a TODO(scaffold) placeholder)")
    parser.add_argument("--dry-run", action="store_true", help="list the files without writing anything")
    return parser


def _run(argv: Sequence[str]) -> ScriptResult:
    args = _parser().parse_args(list(argv))
    layout = labcli.layout_from(args)
    name = args.name
    check_name(layout, name)
    description = yaml_quoted(
        args.description or DEFAULT_DESCRIPTION.format(name=name),
        option="--description",
        limit=frontmatter.MAX_DESCRIPTION_LENGTH,
    )
    author = yaml_quoted(args.author or TODO_MARKER + " author", option="--author", limit=MAX_AUTHOR_LENGTH)
    family = resolve_family(layout, name, args.family)
    number = allocate_spec(layout, args.spec, name=name)
    spec_dir = os.path.join(layout.specs_dir, "%03d-%s" % (number, name))
    keep_spec = os.path.isdir(spec_dir) and not os.path.islink(spec_dir)
    if os.path.lexists(spec_dir) and not keep_spec:
        raise ScriptError("SPEC_EXISTS", "%s already exists" % layout.rel(spec_dir), exit_code=EXIT_REFUSED)
    values = {
        "name": name,
        "title": title_of(name),
        "description": description,
        "family": family,
        "spec_id": "SPEC-%03d" % number,
        "spec_number": "%03d" % number,
        "spec_dir": layout.rel(spec_dir),
        "author": author,
        "date": parse_now(args.now).strftime("%Y-%m-%d"),
    }
    sources = [source for source in template_files(layout) if not (keep_spec and source[1] == "spec")]
    skill_dir = layout.skill_dir(name)
    files = [
        layout.rel(os.path.join(skill_dir if area == "skill" else spec_dir, *dest.split("/")))
        for _src, area, dest in sources
    ]
    vendored = sync.plan_skill(layout, skill_dir)
    files += [layout.rel(action.path) for action in vendored.actions]
    if not args.dry_run:
        _materialise(layout, sources, values, skill_dir, None if keep_spec else spec_dir)
    payload = {
        "schema_version": 1,
        "name": name,
        "spec": values["spec_id"],
        "family": family,
        "dry_run": bool(args.dry_run),
        "skill_path": layout.rel(skill_dir),
        "spec_path": layout.rel(spec_dir),
        "files": sorted(files),
        "spec_created": not keep_spec,
        "todo_marker": TODO_MARKER,
        "next_steps": [
            "Replace every %s marker; 'skill-lab validate --skill %s' lists the files that still have one"
            % (TODO_MARKER, name),
            "skill-lab install --skill %s" % name,
            "skill-lab catalog",
            "skill-lab test --skill %s" % name,
        ],
    }
    return ScriptResult(EXIT_OK, payload)


def _materialise(
    layout: paths.Layout,
    sources: List[Tuple[str, str, str]],
    values: Dict[str, str],
    skill_dir: str,
    spec_dir: Optional[str],
) -> None:
    """Render into hidden staging folders, vendor, then rename into place (``spec_dir`` None: skill only)."""
    os.makedirs(layout.skills_dir, exist_ok=True)
    os.makedirs(layout.specs_dir, exist_ok=True)
    skill_stage_root = tempfile.mkdtemp(prefix=".new-", dir=layout.skills_dir)
    spec_stage_root = tempfile.mkdtemp(prefix=".new-", dir=layout.specs_dir)
    try:
        staged_skill = os.path.join(skill_stage_root, values["name"])
        staged_spec = os.path.join(spec_stage_root, os.path.basename(spec_dir or "spec"))
        for source, area, destination in sources:
            target = os.path.join(staged_skill if area == "skill" else staged_spec, *destination.split("/"))
            _render_file(layout, source, target, values)
        sync.apply_plan(sync.plan_skill(layout, staged_skill))
        os.replace(staged_skill, skill_dir)
        if spec_dir is not None:
            os.replace(staged_spec, spec_dir)
    finally:
        shutil.rmtree(skill_stage_root, ignore_errors=True)
        shutil.rmtree(spec_stage_root, ignore_errors=True)


def _render_file(layout: paths.Layout, source: str, target: str, values: Dict[str, str]) -> None:
    with open(source, "r", encoding="utf-8", newline="") as handle:
        text = handle.read()
    if source.endswith(TEMPLATE_SUFFIX):
        text = render_text(text, values, source=layout.rel(source))
    os.makedirs(os.path.dirname(target), exist_ok=True)
    with open(target, "w", encoding="utf-8", newline="") as handle:
        handle.write(text)
    if target.endswith(".py") and os.path.basename(os.path.dirname(target)) == "scripts":
        os.chmod(target, 0o755)
