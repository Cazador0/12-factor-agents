"""Build, persist and load the derived retrieval index.

The index is a retrieval accelerator, never a source of truth (Constitution Art. VII). It lives in
``.specify/index/`` (gitignored) and is rebuilt from the repository whenever it is missing or stale.
"""

from __future__ import annotations

import fnmatch
import json
import subprocess
from collections.abc import Iterable
from pathlib import Path

from langchain_core.documents import Document

from ..config import Settings
from .chunking import chunk_file
from .embeddings import get_embeddings
from .provenance import Provenance, file_sha, head_sha, repo_name
from .retriever import HybridRetriever

DEFAULT_INCLUDE = (
    "AGENTS.md",
    "CLAUDE.md",
    "README.md",
    "ARCHITECTURE.md",
    "specs/**/*.md",
    "docs/**/*.md",
    "content/*.md",
    ".specify/memory/*.md",
    ".specify/intakes/**/*.md",
    ".claude/skills/**/SKILL.md",
    ".claude/skills/**/references/*.md",
    "extensions/**/*.md",
    "packages/sdd-harness/src/**/*.py",
)
EXCLUDE = ("**/node_modules/**", "**/.venv/**", "**/.git/**", "**/__pycache__/**", ".specify/index/**")
INDEX_DIR = Path(".specify/index")


def _listed_files(root: Path) -> list[str]:
    """Tracked plus untracked-but-not-ignored files, so .gitignore is respected."""
    try:
        out = subprocess.run(
            ["git", "-C", str(root), "ls-files", "-co", "--exclude-standard"],
            capture_output=True,
            text=True,
            timeout=60,
            check=False,
        )
        if out.returncode == 0:
            return [ln for ln in out.stdout.splitlines() if ln]
    except (OSError, subprocess.SubprocessError):
        pass
    return [str(p.relative_to(root)) for p in root.rglob("*") if p.is_file()]


def _match(rel: str, patterns: Iterable[str]) -> bool:
    return any(fnmatch.fnmatch(rel, pat) or fnmatch.fnmatch(rel, pat.replace("**/", "")) for pat in patterns)


def collect_documents(root: Path, include: Iterable[str] = DEFAULT_INCLUDE) -> list[Document]:
    root = root.resolve()
    head = head_sha(root)
    repo = repo_name(root)
    include = tuple(include)
    docs: list[Document] = []
    for rel in sorted(_listed_files(root)):
        if not _match(rel, include) or _match(rel, EXCLUDE):
            continue
        path = root / rel
        if not path.is_file():
            continue
        fsha = file_sha(path)
        for chunk in chunk_file(path, rel):
            prov = Provenance(
                repo=repo,
                commit_sha=head,
                path=rel,
                heading=chunk.heading,
                symbol=chunk.symbol,
                spec_id=chunk.spec_id,
                kind=chunk.kind,
                file_sha=fsha,
            )
            meta = {
                "path": rel,
                "kind": chunk.kind,
                "heading": chunk.heading,
                "symbol": chunk.symbol,
                "spec_id": chunk.spec_id,
                "provenance": prov.model_dump(),
            }
            docs.append(Document(page_content=chunk.text, metadata=meta))
    return docs


def save(root: Path, docs: list[Document]) -> Path:
    out_dir = root / INDEX_DIR
    out_dir.mkdir(parents=True, exist_ok=True)
    path = out_dir / "chunks.jsonl"
    with path.open("w", encoding="utf-8") as fh:
        for d in docs:
            fh.write(json.dumps({"text": d.page_content, "metadata": d.metadata}) + "\n")
    (out_dir / "manifest.json").write_text(
        json.dumps({"head": head_sha(root), "chunks": len(docs)}, indent=2), encoding="utf-8"
    )
    return path


def load(root: Path) -> list[Document] | None:
    path = root / INDEX_DIR / "chunks.jsonl"
    if not path.is_file():
        return None
    docs = []
    for line in path.read_text(encoding="utf-8").splitlines():
        row = json.loads(line)
        docs.append(Document(page_content=row["text"], metadata=row["metadata"]))
    return docs


def is_current(root: Path) -> bool:
    manifest = root / INDEX_DIR / "manifest.json"
    if not manifest.is_file():
        return False
    try:
        data = json.loads(manifest.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        return False
    return data.get("head") == head_sha(root)


def build_retriever(
    settings: Settings | None = None,
    *,
    root: Path | None = None,
    include: Iterable[str] | None = None,
    refresh: bool = False,
    reject_stale: bool = True,
) -> HybridRetriever:
    """Load the persisted index when current, else rebuild it from the repository.

    Uncommitted edits make individual chunks stale (their file hash changes), so a rebuild also
    happens whenever HEAD moved. Callers that need edits picked up immediately pass ``refresh=True``.
    """
    settings = settings or Settings.load(root)
    root = settings.root
    docs = None if (refresh or include is not None) else (load(root) if is_current(root) else None)
    if docs is None:
        docs = collect_documents(root, include or DEFAULT_INCLUDE)
        if include is None:
            save(root, docs)
    return HybridRetriever(
        documents=docs,
        embeddings=get_embeddings(settings.get("retrieval.embeddings")),
        root=root,
        k=int(settings.get("retrieval.top_k", 8)),
        rrf_k=int(settings.get("retrieval.rrf_k", 60)),
        reject_stale=reject_stale,
    )
