"""Repository layout, skill discovery and file-tree helpers shared by the lab commands.

Every path the lab touches derives from one repository root (``Layout``), so
the commands work the same on the real repository and on a scratch copy built
by a test. The default root is the parent of ``skill-lab/``, found from this
file's location; ``--repo DIR`` overrides it.
"""

from __future__ import annotations

import dataclasses
import filecmp
import os
import shutil
import tempfile
from typing import Dict, Iterable, List, NamedTuple, Optional, Sequence, Tuple

LAB_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DEFAULT_REPO_ROOT = os.path.dirname(LAB_ROOT)

SKILL_FILE = "SKILL.md"
MANAGED_MARKER = ".skill-lab-managed"
"""Marker file that identifies an installed copy as owned by ``skill-lab install``."""

RUNTIMES = ("zed", "claude", "codex")
RUNTIME_SKILL_DIRS = {
    "zed": (".agents", "skills"),
    "codex": (".agents", "skills"),
    "claude": (".claude", "skills"),
}
"""Discovery folder of each runtime, relative to a project root or to ``~``."""

_IGNORED_DIRS = frozenset({"__pycache__"})
_IGNORED_SUFFIXES = (".pyc", ".pyo")


@dataclasses.dataclass(frozen=True)
class Layout:
    """The CONVENTIONS §1 layout below one repository root."""

    repo_root: str

    @classmethod
    def at(cls, repo_root: Optional[str] = None) -> "Layout":
        return cls(os.path.abspath(repo_root or DEFAULT_REPO_ROOT))

    @property
    def skills_dir(self) -> str:
        return os.path.join(self.repo_root, "skills")

    @property
    def lab_root(self) -> str:
        return os.path.join(self.repo_root, "skill-lab")

    @property
    def skillkit_dir(self) -> str:
        return os.path.join(self.lab_root, "shared", "_skillkit")

    @property
    def schemas_dir(self) -> str:
        return os.path.join(self.lab_root, "contracts", "schemas")

    @property
    def specs_dir(self) -> str:
        return os.path.join(self.lab_root, "specs")

    @property
    def templates_dir(self) -> str:
        return os.path.join(self.lab_root, "templates", "skill")

    @property
    def lab_tests_dir(self) -> str:
        return os.path.join(self.lab_root, "tests")

    @property
    def catalog_path(self) -> str:
        return os.path.join(self.skills_dir, "CATALOG.json")

    @property
    def conventions_path(self) -> str:
        return os.path.join(self.lab_root, "docs", "CONVENTIONS.md")

    def skill_dir(self, name: str) -> str:
        return os.path.join(self.skills_dir, name)

    def rel(self, path: str) -> str:
        """``path`` relative to the repository root, with ``/`` separators."""
        return display_path(path, self.repo_root)


def display_path(path: str, root: str, prefix: str = "") -> str:
    """Show ``path`` relative to ``root`` (``prefix`` prepended) when it lies inside it."""
    absolute = os.path.abspath(path)
    root = os.path.abspath(root)
    if not lexically_within(absolute, root):
        return absolute.replace(os.sep, "/")
    relative = os.path.relpath(absolute, root).replace(os.sep, "/")
    return prefix + ("" if relative == "." else relative)


def lexically_within(path: str, root: str) -> bool:
    """True when normalised ``path`` is ``root`` or below it, without resolving symlinks."""
    path, root = os.path.normcase(os.path.normpath(path)), os.path.normcase(os.path.normpath(root))
    try:
        return os.path.commonpath([path, root]) == root
    except ValueError:  # different drives on Windows
        return False


# ---------------------------------------------------------------------------
# Skill discovery
# ---------------------------------------------------------------------------


def _candidate_folders(layout: Layout) -> List[str]:
    if not os.path.isdir(layout.skills_dir):
        return []
    return sorted(
        entry
        for entry in os.listdir(layout.skills_dir)
        if not entry.startswith(("_", ".")) and os.path.isdir(os.path.join(layout.skills_dir, entry))
    )


def skill_names(layout: Layout) -> List[str]:
    """Folders directly under ``skills/`` that contain ``SKILL.md`` (``_``/``.`` folders ignored)."""
    return [
        name for name in _candidate_folders(layout) if os.path.isfile(os.path.join(layout.skills_dir, name, SKILL_FILE))
    ]


def non_skill_folders(layout: Layout) -> List[str]:
    """Folders directly under ``skills/`` without a ``SKILL.md``."""
    return [
        name
        for name in _candidate_folders(layout)
        if not os.path.isfile(os.path.join(layout.skills_dir, name, SKILL_FILE))
    ]


def entry_scripts(skill_dir: str) -> List[str]:
    """Absolute paths of ``scripts/*.py`` entry points (names not starting with ``_``), sorted."""
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return []
    return [
        os.path.join(scripts_dir, name)
        for name in sorted(os.listdir(scripts_dir))
        if name.endswith(".py") and not name.startswith("_") and os.path.isfile(os.path.join(scripts_dir, name))
    ]


def helper_modules(skill_dir: str) -> List[str]:
    """Python files under ``scripts/`` that are not entry points and not the vendored ``_skillkit``."""
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return []
    found = []
    for relative in list_tree(scripts_dir, exclude_top=("_skillkit",)):
        if not relative.endswith(".py"):
            continue
        if "/" not in relative and not relative.startswith("_"):
            continue  # an entry script
        found.append(os.path.join(scripts_dir, *relative.split("/")))
    return found


def local_module_names(skill_dir: str) -> List[str]:
    """Top-level names a script may import from its own ``scripts/`` folder."""
    scripts_dir = os.path.join(skill_dir, "scripts")
    if not os.path.isdir(scripts_dir):
        return []
    names = set()
    for entry in os.listdir(scripts_dir):
        full = os.path.join(scripts_dir, entry)
        if entry.endswith(".py") and os.path.isfile(full):
            names.add(entry[:-3])
        elif os.path.isdir(full) and entry not in _IGNORED_DIRS:
            names.add(entry)
    return sorted(names)


def case_files(skill_dir: str) -> List[str]:
    """Absolute paths of ``evals/cases/*.json``, sorted by file name."""
    cases_dir = os.path.join(skill_dir, "evals", "cases")
    if not os.path.isdir(cases_dir):
        return []
    return [
        os.path.join(cases_dir, name)
        for name in sorted(os.listdir(cases_dir))
        if name.endswith(".json") and os.path.isfile(os.path.join(cases_dir, name))
    ]


def canonical_schema_files(layout: Layout) -> List[str]:
    """File names of the canonical contracts (``<name>.v<N>.schema.json``), sorted."""
    if not os.path.isdir(layout.schemas_dir):
        return []
    return sorted(
        name
        for name in os.listdir(layout.schemas_dir)
        if name.endswith(".schema.json") and os.path.isfile(os.path.join(layout.schemas_dir, name))
    )


# ---------------------------------------------------------------------------
# File trees
# ---------------------------------------------------------------------------


def is_ignored(name: str) -> bool:
    """Generated files that never count as content (``__pycache__``, ``*.pyc``)."""
    return name in _IGNORED_DIRS or name.endswith(_IGNORED_SUFFIXES)


def list_tree(root: str, *, exclude_top: Sequence[str] = ()) -> List[str]:
    """Relative ``/``-separated paths of every file below ``root``, sorted.

    Generated files are skipped, and so are top-level entries named in
    ``exclude_top``. Symlinked directories are followed (as ``copytree``
    does) unless they loop back to an ancestor.
    """
    found: List[str] = []
    _walk(root, "", tuple(exclude_top), frozenset({os.path.realpath(root)}), found)
    return sorted(found)


def _walk(directory: str, prefix: str, exclude_top: Tuple[str, ...], ancestors: frozenset, found: List[str]) -> None:
    for entry in sorted(os.listdir(directory)):
        if is_ignored(entry) or (not prefix and entry in exclude_top):
            continue
        full = os.path.join(directory, entry)
        if os.path.isdir(full):
            real = os.path.realpath(full)
            if real not in ancestors:
                _walk(full, prefix + entry + "/", exclude_top, ancestors | {real}, found)
        else:
            found.append(prefix + entry)


class TreeDiff(NamedTuple):
    """How ``actual`` differs from ``expected``; empty lists mean identical content."""

    missing: List[str]
    extra: List[str]
    changed: List[str]

    def __bool__(self) -> bool:
        return bool(self.missing or self.extra or self.changed)

    def describe(self, limit: int = 5) -> str:
        parts = []
        for label, items in (("changed", self.changed), ("missing", self.missing), ("extra", self.extra)):
            if items:
                shown = ", ".join(items[:limit]) + (" (+%d more)" % (len(items) - limit) if len(items) > limit else "")
                parts.append("%s %s" % (label, shown))
        return "; ".join(parts)


def compare_trees(expected: str, actual: str, *, exclude_top: Sequence[str] = ()) -> TreeDiff:
    """Compare two folders file by file (bytes), ignoring generated files."""
    want = set(list_tree(expected, exclude_top=exclude_top)) if os.path.isdir(expected) else set()
    have = set(list_tree(actual, exclude_top=exclude_top)) if os.path.isdir(actual) else set()
    changed = [
        rel
        for rel in sorted(want & have)
        if not files_equal(os.path.join(expected, *rel.split("/")), os.path.join(actual, *rel.split("/")))
    ]
    return TreeDiff(sorted(want - have), sorted(have - want), changed)


def files_equal(left: str, right: str) -> bool:
    """Byte-for-byte equality of two regular files (False when either is missing)."""
    if not (os.path.isfile(left) and os.path.isfile(right)):
        return False
    return filecmp.cmp(left, right, shallow=False)


def copy_file_atomic(source: str, destination: str) -> None:
    """Copy bytes to a temporary file beside ``destination`` and rename it into place."""
    directory = os.path.dirname(os.path.abspath(destination))
    os.makedirs(directory, exist_ok=True)
    handle, temp_path = tempfile.mkstemp(prefix=".%s." % os.path.basename(destination), suffix=".tmp", dir=directory)
    try:
        with os.fdopen(handle, "wb") as out, open(source, "rb") as src:
            shutil.copyfileobj(src, out)
        shutil.copymode(source, temp_path)
        os.replace(temp_path, destination)
    except BaseException:
        if os.path.exists(temp_path):
            os.unlink(temp_path)
        raise


def remove_path(path: str) -> None:
    """Delete a file, a symlink (never its target) or a whole directory tree."""
    if os.path.islink(path) or os.path.isfile(path):
        os.unlink(path)
    elif os.path.isdir(path):
        shutil.rmtree(path)


def prune_empty_dirs(root: str) -> None:
    """Remove empty directories below ``root`` (``root`` itself is kept)."""
    for directory, _dirnames, _filenames in os.walk(root, topdown=False):
        if directory != root and not os.listdir(directory):
            os.rmdir(directory)


def unique(items: Iterable[str]) -> List[str]:
    """Items in first-seen order without duplicates."""
    seen: Dict[str, None] = {}
    for item in items:
        seen.setdefault(item, None)
    return list(seen)


def split_csv(values: Optional[Sequence[str]]) -> List[str]:
    """Flatten repeatable, comma-separated option values (``--runtime zed,claude``)."""
    result: List[str] = []
    for value in values or ():
        result.extend(part.strip() for part in value.split(",") if part.strip())
    return unique(result)


def runtime_dirs(runtimes: Sequence[str]) -> List[Tuple[Tuple[str, str], List[str]]]:
    """Group runtimes by the discovery folder they share: ``[((".agents", "skills"), ["codex", "zed"]), ...]``."""
    grouped: Dict[Tuple[str, str], List[str]] = {}
    for runtime in runtimes:
        grouped.setdefault(RUNTIME_SKILL_DIRS[runtime], []).append(runtime)
    return [(folder, sorted(names)) for folder, names in sorted(grouped.items())]
