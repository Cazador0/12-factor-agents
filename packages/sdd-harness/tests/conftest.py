from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

CONSTITUTION = """# Test Constitution

## Core Principles

### I. Plain Files
All state lives in plain Markdown in git.

### II. Human Approval
Merges to main MUST wait for a person's approval.

## Additional Constraints

- Gitea is the only forge.

**Version**: 1.0.0
"""


def git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture(autouse=True)
def offline(monkeypatch):
    """Engines must never call out during tests."""
    monkeypatch.setenv("SDD_LLM", "off")


@pytest.fixture
def project(tmp_path: Path) -> Path:
    root = tmp_path / "proj"
    (root / ".specify" / "memory").mkdir(parents=True)
    (root / ".specify" / "memory" / "constitution.md").write_text(CONSTITUTION)
    git(root, "init", "-q")
    git(root, "add", "-A")
    git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", "init")
    return root


def commit(root: Path, msg: str = "change") -> None:
    git(root, "add", "-A")
    git(root, "-c", "user.email=t@t", "-c", "user.name=t", "commit", "-qm", msg)
