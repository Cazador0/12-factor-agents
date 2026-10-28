"""Provenance for every indexed chunk, and the staleness rule that rejects old evidence.

A retrieval result is evidence only when it can describe the current branch: its commit must be an
ancestor of HEAD and the file it came from must still hold the same bytes (Constitution Art. VII).
"""

from __future__ import annotations

import hashlib
import subprocess
from datetime import UTC, datetime
from functools import lru_cache
from pathlib import Path

from pydantic import BaseModel, Field


class Provenance(BaseModel):
    repo: str
    commit_sha: str | None = None
    path: str
    heading: str | None = None
    symbol: str | None = None
    spec_id: str | None = None
    issue_ids: list[int] = Field(default_factory=list)
    kind: str = "text"
    generated: bool = False
    file_sha: str | None = None
    indexed_at: str = Field(default_factory=lambda: datetime.now(UTC).isoformat(timespec="seconds"))


def _git(root: Path, *args: str) -> str | None:
    try:
        out = subprocess.run(["git", "-C", str(root), *args], capture_output=True, text=True, timeout=20, check=False)
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 else None


def head_sha(root: Path) -> str | None:
    return _git(root, "rev-parse", "HEAD")


def repo_name(root: Path) -> str:
    url = _git(root, "config", "--get", "remote.origin.url") or ""
    tail = url.rstrip("/").removesuffix(".git").split("/")[-2:]
    return "/".join(tail) if len(tail) == 2 and all(tail) else root.name


@lru_cache(maxsize=4096)
def _is_ancestor_cached(root: str, sha: str, head: str) -> bool:
    if sha == head:
        return True
    try:
        out = subprocess.run(
            ["git", "-C", root, "merge-base", "--is-ancestor", sha, head],
            capture_output=True,
            timeout=20,
            check=False,
        )
    except (OSError, subprocess.SubprocessError):
        return False
    return out.returncode == 0


def is_ancestor(root: Path, sha: str | None, head: str | None) -> bool:
    if not sha or not head:
        return sha == head  # both unknown (not a git repo): nothing to compare
    return _is_ancestor_cached(str(root), sha, head)


def file_sha(path: Path) -> str | None:
    try:
        return hashlib.sha1(path.read_bytes()).hexdigest()
    except OSError:
        return None


def staleness(root: Path, prov: Provenance, head: str | None = None) -> str | None:
    """Return why a chunk is stale, or ``None`` when it can describe the current tree."""
    head = head if head is not None else head_sha(root)
    if prov.commit_sha and head and not is_ancestor(root, prov.commit_sha, head):
        return f"indexed at {prov.commit_sha[:12]}, which is not an ancestor of HEAD {head[:12]}"
    current = file_sha(root / prov.path)
    if current is None:
        return f"{prov.path} no longer exists"
    if prov.file_sha and current != prov.file_sha:
        return f"{prov.path} changed since it was indexed"
    return None
