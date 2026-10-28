"""The skill catalog: every SKILL.md reachable from the configured roots, as a searchable graph.

Nodes are skills (name, description, lifecycle stage, classification, scripts, security tier);
edges are references between skills (one skill's instructions naming another) and shared
extensions (``speckit-intake-*`` siblings). The graph is derived data: ``check`` recomputes the
content hash and reports whether the stored graph is current.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..config import Settings
from ..markdown import split_front_matter
from .classify import classify, stage_of
from .screen import screen_skill

GRAPH_REL = Path(".specify/index/skills-graph.json")


@dataclass
class SkillNode:
    name: str
    description: str
    absolute_path: str
    source: str
    stage: str | None
    classification: str
    tier: int
    findings: list[str] = field(default_factory=list)
    scripts: list[str] = field(default_factory=list)
    references: list[str] = field(default_factory=list)
    content_sha: str = ""

    def card(self) -> str:
        """Text the retriever indexes: name, description, stage and the opening of the body."""
        return f"{self.name}\n{self.description}\nstage: {self.stage or 'none'}\n{self.classification}"


def _source_for(path: Path, settings: Settings) -> str:
    s = str(path)
    if "/.claude/plugins/" in s:
        return "plugin"
    if "/synced/" in s:
        return "synced"
    if str(settings.root) in s:
        return "project"
    if str(Path.home()) in s:
        return "user"
    return "catalog"


def _plugin_of(path: Path) -> str | None:
    """``…/.claude/plugins/synced/<id>/engineering/skills/debug/SKILL.md`` → ``engineering``."""
    parts = path.parts
    if ".claude" in parts and "plugins" in parts and "skills" in parts:
        i = len(parts) - 1 - parts[::-1].index("skills")
        return parts[i - 1] if i > 0 else None
    return None


def discover(settings: Settings, extra_roots: list[Path] | None = None) -> list[Path]:
    roots = list(settings.skill_dirs())
    catalog = settings.catalog_root()
    if catalog != settings.root:
        roots += [catalog / "skills", catalog / ".claude" / "skills", catalog / "catalog"]
    roots += extra_roots or []
    seen: set[Path] = set()
    found: list[Path] = []
    for root in roots:
        if not root.is_dir():
            continue
        for path in sorted(root.rglob("SKILL.md")):
            if any(
                part in {"node_modules", ".git", "evals", "workspace"} or part.endswith("-workspace")
                for part in path.parts
            ):
                continue
            real = path.resolve()
            if real in seen:
                continue
            seen.add(real)
            found.append(path)
    return found


def build_nodes(settings: Settings, extra_roots: list[Path] | None = None) -> list[SkillNode]:
    paths = discover(settings, extra_roots)
    raw: list[tuple[Path, dict, str]] = []
    for path in paths:
        text = path.read_text("utf-8", errors="replace")
        meta, body = split_front_matter(text)
        raw.append((path, meta, body))
    names = {str(m.get("name") or p.parent.name) for p, m, _ in raw}
    names |= {f"{pl}:{n}" for p, m, _ in raw if (pl := _plugin_of(p)) for n in [str(m.get("name") or p.parent.name)]}
    nodes: list[SkillNode] = []
    for path, meta, body in raw:
        name = str(meta.get("name") or path.parent.name)
        plugin = _plugin_of(path)
        if plugin and ":" not in name:
            name = f"{plugin}:{name}"
        desc = re.sub(r"\s+", " ", str(meta.get("description") or "")).strip()
        refs = sorted(n for n in names if n != name and re.search(rf"(?<![\w-])/?{re.escape(n)}(?![\w-])", body))
        tier, findings, scripts = screen_skill(path.parent, body)
        stage = stage_of(name, desc)
        nodes.append(
            SkillNode(
                name=name,
                description=desc,
                absolute_path=str(path.resolve()),
                source=_source_for(path, settings),
                stage=stage,
                classification=classify(name, desc, stage),
                tier=tier,
                findings=findings,
                scripts=scripts,
                references=refs,
                content_sha=hashlib.sha1(path.read_bytes()).hexdigest(),
            )
        )
    return nodes


def edges(nodes: list[SkillNode]) -> list[dict]:
    out = [{"from": n.name, "to": r, "kind": "references"} for n in nodes for r in n.references]
    by_prefix: dict[str, list[str]] = {}
    for n in nodes:
        parts = n.name.split("-")
        if len(parts) >= 3:
            by_prefix.setdefault("-".join(parts[:2]), []).append(n.name)
    for prefix, members in by_prefix.items():
        for a in members:
            for b in members:
                if a < b:
                    out.append({"from": a, "to": b, "kind": f"extension:{prefix}"})
    return out


def graph_hash(nodes: list[SkillNode]) -> str:
    h = hashlib.sha1()
    for n in sorted(nodes, key=lambda x: x.absolute_path):
        h.update(f"{n.absolute_path}:{n.content_sha}\n".encode())
    return h.hexdigest()


def save_graph(settings: Settings, nodes: list[SkillNode]) -> Path:
    path = settings.root / GRAPH_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = {"hash": graph_hash(nodes), "nodes": [asdict(n) for n in nodes], "edges": edges(nodes)}
    path.write_text(json.dumps(payload, indent=1), "utf-8")
    return path


def load_graph(settings: Settings) -> dict | None:
    path = settings.root / GRAPH_REL
    if not path.is_file():
        return None
    return json.loads(path.read_text("utf-8"))


def check(settings: Settings) -> dict:
    nodes = build_nodes(settings)
    current = graph_hash(nodes)
    stored = load_graph(settings)
    if stored is None:
        return {"current": False, "reason": "no stored graph; run build", "skills": len(nodes)}
    old = {n["absolute_path"]: n["content_sha"] for n in stored["nodes"]}
    new = {n.absolute_path: n.content_sha for n in nodes}
    changed = sorted(p for p in new if old.get(p) != new[p])
    removed = sorted(p for p in old if p not in new)
    return {
        "current": stored.get("hash") == current,
        "skills": len(nodes),
        "edges": len(stored.get("edges", [])),
        "changed": changed[:20],
        "removed": removed[:20],
    }


def load_or_build(settings: Settings) -> list[SkillNode]:
    stored = load_graph(settings)
    nodes = build_nodes(settings)
    if stored is None or stored.get("hash") != graph_hash(nodes):
        save_graph(settings, nodes)
    return nodes
