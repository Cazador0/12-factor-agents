"""Project discovery and the intake extension's layered configuration."""

from __future__ import annotations

import copy
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml

CONFIG_REL = Path(".specify/extensions/intake/intake-config.yml")
LOCAL_CONFIG_REL = Path(".specify/extensions/intake/local-config.yml")

DEFAULTS: dict[str, Any] = {
    "intakes": {"dir": ".specify/intakes"},
    "session": {"per_round": 4, "checkin_every": 5},
    "catalog": {"root": "../intakeSpec", "skill_dirs": [".claude/skills", "~/.claude/skills", "~/.claude/plugins"]},
    "retrieval": {"embeddings": "hashing", "rrf_k": 60, "top_k": 8},
    "reasoning": {"traces": True, "visible": True, "dir": ".specify/traces"},
    "llm": {"provider": "anthropic", "model": "claude-opus-5-5", "effort": "high"},
}


def find_project_root(start: Path | None = None) -> Path:
    """Walk up from ``start`` to the nearest folder holding ``.specify/`` (else ``.git/``)."""
    here = (start or Path.cwd()).resolve()
    for candidate in (here, *here.parents):
        if (candidate / ".specify").is_dir():
            return candidate
    for candidate in (here, *here.parents):
        if (candidate / ".git").exists():
            return candidate
    return here


def _merge(base: dict[str, Any], override: dict[str, Any]) -> dict[str, Any]:
    out = copy.deepcopy(base)
    for key, value in (override or {}).items():
        if isinstance(value, dict) and isinstance(out.get(key), dict):
            out[key] = _merge(out[key], value)
        else:
            out[key] = value
    return out


def _read_yaml(path: Path) -> dict[str, Any]:
    if not path.is_file():
        return {}
    data = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    return data if isinstance(data, dict) else {}


@dataclass
class Settings:
    """Merged settings: defaults, then intake-config.yml, then local-config.yml (which wins)."""

    root: Path
    data: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def load(cls, root: Path | None = None) -> Settings:
        root = find_project_root(root)
        data = _merge(DEFAULTS, _read_yaml(root / CONFIG_REL))
        data = _merge(data, _read_yaml(root / LOCAL_CONFIG_REL))
        return cls(root=root, data=data)

    def get(self, dotted: str, default: Any = None) -> Any:
        node: Any = self.data
        for part in dotted.split("."):
            if not isinstance(node, dict) or part not in node:
                return default
            node = node[part]
        return node

    def path(self, dotted: str) -> Path:
        """Resolve a configured path: ``~`` expands, relative paths hang off the project root."""
        raw = str(self.get(dotted))
        return self.resolve(raw)

    def resolve(self, raw: str) -> Path:
        expanded = Path(os.path.expanduser(raw))
        return expanded if expanded.is_absolute() else (self.root / expanded)

    def rel(self, path: Path | str) -> str:
        """A path relative to the project root when it is inside it, so committed records stay portable."""
        p = Path(path)
        try:
            return str(p.resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(p)

    @property
    def intakes_dir(self) -> Path:
        return self.path("intakes.dir")

    @property
    def per_round(self) -> int:
        return max(1, int(self.get("session.per_round", 4)))

    @property
    def checkin_every(self) -> int:
        return max(1, int(self.get("session.checkin_every", 5)))

    @property
    def traces_dir(self) -> Path:
        return self.path("reasoning.dir")

    def catalog_root(self) -> Path:
        """The intakeSpec catalog root, following the route command's rules.

        ``catalog.root`` (local config wins) is used when it holds ``bin/intakespec``.
        Without a local override, a project that itself has ``bin/intakespec`` is the catalog.
        """
        local = _read_yaml(self.root / LOCAL_CONFIG_REL).get("catalog", {})
        configured = self.path("catalog.root")
        if "root" in local:
            return configured
        if (configured / "bin" / "intakespec").is_file():
            return configured
        if (self.root / "bin" / "intakespec").is_file():
            return self.root
        return configured

    def skill_dirs(self) -> list[Path]:
        return [self.resolve(str(p)) for p in self.get("catalog.skill_dirs", [])]
