"""Present skills to a model the way the Zed Agent does, for runtimes that are not Zed.

This is an *emulation* of Zed's skill loading, so results are labelled
``<runtime>-zed-emulation``, never as Zed itself. Two pieces are mirrored from
zed-industries/zed (main, read 2026-10-22):

* The catalog: the "## Agent Skills" section of
  ``crates/agent/src/templates/system_prompt.hbs`` (the ``{{#if has_skills}}``
  block). ``name`` and ``description`` go through Handlebars ``{{...}}``,
  which HTML-escapes them (handlebars-rust's default ``html_escape``, since
  ``crates/agent/src/templates.rs`` registers no other escape function);
  ``location`` uses ``{{{...}}}`` and is not escaped. Skills with
  ``disable-model-invocation: true`` are left out (``select_catalog_skills``).
* The activation envelope: ``render_skill_envelope`` in
  ``crates/agent/src/tools/skill_tool.rs``. ``name``, source, worktree and
  directory are XML-escaped with ``quick_xml::escape::escape``; the body is
  ``trim()``-ed and only literal ``<skill_content`` / ``</skill_content`` tags
  are neutralised (``neutralize_envelope_tags``), so other Markdown HTML passes
  through. (The crate README says the body is fully escaped; the code does
  not do that, and the code is what the model sees.)

A slash-command activation (``/skill-name``) injects that envelope as a user
message, so ``user_prompt`` puts it first, then the fixtures the model would
otherwise read with ``read_file``, then the task. The rest of Zed's system
prompt is reduced to its opening paragraph: tool-use rules, communication
guidance and project rules are not reproduced.
"""

from __future__ import annotations

import os
from typing import Dict, List, NamedTuple, Optional, Sequence

from _skillkit import frontmatter

SKILL_FILE = "SKILL.md"
LABEL_SUFFIX = "-zed-emulation"

_PREAMBLE = (
    "You are the Zed coding agent running inside the Zed editor. You help users complete software engineering "
    "tasks by understanding their codebase, making careful changes, and explaining your work clearly. Use your "
    "broad knowledge of programming languages, frameworks, design patterns, and engineering best practices to "
    "solve problems pragmatically.\n\n"
)
_CATALOG_HEADER = (
    "## Agent Skills\n\n"
    "You have access to the following Skills - modular capabilities that provide specialized instructions for "
    "specific tasks. When a user's request matches a Skill's description, use the `skill` tool to retrieve the "
    "full instructions.\n\n"
)
_CATALOG_FOOTER = (
    "To use a Skill:\n"
    "1. Identify when a user's request matches a Skill's description\n"
    "2. Use the `skill` tool with the skill's name to get detailed instructions\n"
    "3. Follow the instructions in the Skill\n"
    "4. If the Skill references additional files, use `read_file` to access them. Paths inside a Skill resolve "
    "relative to that Skill's directory (the parent of its `SKILL.md`).\n\n"
)
_CATALOG_ENTRY = (
    "  <skill>\n    <name>%s</name>\n    <description>%s</description>\n    <location>%s</location>\n  </skill>\n"
)
_HANDLEBARS_ESCAPES = {
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#x27;",
    "`": "&#x60;",
    "=": "&#x3D;",
}
_XML_ESCAPES = {"&": "&amp;", "<": "&lt;", ">": "&gt;", "'": "&apos;", '"': "&quot;"}


class InstalledSkill(NamedTuple):
    name: str
    description: str
    directory: str
    """Absolute path of the skill folder (Zed's ``directory_path``)."""
    skill_file: str
    """Absolute path of ``SKILL.md`` (the catalog ``location``)."""
    disable_model_invocation: bool
    body: str
    """The SKILL.md body after the frontmatter, ``trim()``-ed as Zed's ``read_skill_body`` does."""


def discover(skills_root: str) -> List[InstalledSkill]:
    """Flat scan of ``<skills_root>/<name>/SKILL.md`` (Zed does not recurse), sorted by name.

    Folders whose frontmatter is unusable (no valid name or description) are
    skipped, as Zed refuses to load them.
    """
    if not os.path.isdir(skills_root):
        return []
    skills = []
    for entry in sorted(os.listdir(skills_root)):
        path = os.path.join(skills_root, entry, SKILL_FILE)
        if entry.startswith((".", "_")) or not os.path.isfile(path):
            continue
        skill = load_skill(path)
        if skill is not None:
            skills.append(skill)
    return skills


def load_skill(skill_file: str) -> Optional[InstalledSkill]:
    """Parse one SKILL.md; None when it has no usable name and description."""
    with open(skill_file, "r", encoding="utf-8-sig") as handle:
        parsed = frontmatter.parse(handle.read(), source=SKILL_FILE)
    name, description = parsed.data.get("name"), parsed.data.get("description")
    if not isinstance(name, str) or not frontmatter.NAME_RE.match(name):
        return None
    if not isinstance(description, str) or not description.strip():
        return None
    absolute = os.path.abspath(skill_file)
    return InstalledSkill(
        name=name,
        description=description,
        directory=os.path.dirname(absolute),
        skill_file=absolute,
        disable_model_invocation=parsed.data.get("disable-model-invocation") is True,
        body=parsed.body.strip(),
    )


def catalog_skills(skills: Sequence[InstalledSkill]) -> List[InstalledSkill]:
    """The skills the model may invoke (``disable-model-invocation`` ones are hidden)."""
    return [skill for skill in skills if not skill.disable_model_invocation]


def render_catalog(skills: Sequence[InstalledSkill]) -> str:
    """The "## Agent Skills" system-prompt section; empty when no skill is visible."""
    visible = catalog_skills(skills)
    if not visible:
        return ""
    entries = "".join(
        _CATALOG_ENTRY
        % (_escape(skill.name, _HANDLEBARS_ESCAPES), _escape(skill.description, _HANDLEBARS_ESCAPES), skill.skill_file)
        for skill in visible
    )
    return _CATALOG_HEADER + "<available_skills>\n" + entries + "</available_skills>\n\n" + _CATALOG_FOOTER


def render_skill_envelope(skill: InstalledSkill, *, worktree: Optional[str] = None) -> str:
    """The ``<skill_content>`` envelope for a project-local skill (``render_skill_envelope``)."""
    lines = ['<skill_content name="%s">' % _escape(skill.name, _XML_ESCAPES), "<source>project-local</source>"]
    if worktree:
        lines.append("<worktree>%s</worktree>" % _escape(worktree, _XML_ESCAPES))
    lines.append("<directory>%s</directory>" % _escape(skill.directory, _XML_ESCAPES))
    lines.append("Relative paths in this skill resolve against <directory>.")
    return "\n".join(lines) + "\n\n" + _neutralize_envelope_tags(skill.body.strip()) + "\n</skill_content>\n"


def system_prompt(skills: Sequence[InstalledSkill]) -> str:
    """System prompt for an emulated Zed Agent turn: Zed's opening paragraph plus the catalog section."""
    return _PREAMBLE + render_catalog(skills)


def user_prompt(
    skill: InstalledSkill, task: str, *, fixtures: Optional[Dict[str, str]] = None, worktree: Optional[str] = None
) -> str:
    """The envelope (slash-command activation), then the fixture files, then the task text."""
    parts = [render_skill_envelope(skill, worktree=worktree)]
    for path, content in sorted((fixtures or {}).items()):
        parts.append('<file path="%s">\n%s\n</file>\n' % (_escape(path, _XML_ESCAPES), _neutralize_file_tags(content)))
    parts.append(task)
    return "\n".join(parts)


def runtime_label(runtime_name: str) -> str:
    """``ollama-cloud`` -> ``ollama-cloud-zed-emulation`` (benchmark-result ``runtime``)."""
    return runtime_name + LABEL_SUFFIX


def _escape(text: str, table: Dict[str, str]) -> str:
    return "".join(table.get(char, char) for char in text)


def _neutralize_envelope_tags(text: str) -> str:
    return text.replace("<skill_content", "&lt;skill_content").replace("</skill_content", "&lt;/skill_content")


def _neutralize_file_tags(text: str) -> str:
    return text.replace("</file", "&lt;/file")
