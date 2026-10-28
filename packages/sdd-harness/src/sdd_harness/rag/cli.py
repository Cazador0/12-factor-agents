"""``sdd-index``: build, query and check the derived retrieval index."""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import Settings
from .index import build_retriever, collect_documents, save
from .provenance import Provenance, head_sha, staleness
from .retriever import cite


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sdd-index", description=__doc__)
    p.add_argument("--root", type=Path, default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    sub.add_parser("build", help="Rebuild .specify/index from the repository")
    q = sub.add_parser("query", help="Hybrid search with provenance")
    q.add_argument("text")
    q.add_argument("-k", type=int, default=8)
    q.add_argument("--kind", action="append", help="Restrict to chunk kinds (repeatable)")
    q.add_argument("--spec", help="Restrict to a spec id such as SPEC-001")
    q.add_argument("--path-prefix")
    q.add_argument("--json", action="store_true")
    sub.add_parser("check", help="Report stale chunks in the persisted index")
    args = p.parse_args(argv)

    settings = Settings.load(args.root)
    if args.cmd == "build":
        docs = collect_documents(settings.root)
        path = save(settings.root, docs)
        print(f"Indexed {len(docs)} chunks at HEAD {(head_sha(settings.root) or 'n/a')[:12]} → {path}")
        return 0
    if args.cmd == "check":
        retriever = build_retriever(settings, reject_stale=False)
        head = head_sha(settings.root)
        stale = [
            (d.metadata["path"], why)
            for d in retriever.documents
            if (why := staleness(settings.root, Provenance.model_validate(d.metadata["provenance"]), head))
        ]
        print(json.dumps({"chunks": len(retriever.documents), "stale": len(stale), "examples": stale[:10]}, indent=2))
        return 0
    retriever = build_retriever(settings)
    filters: dict = {}
    if args.kind:
        filters["kind"] = args.kind
    if args.spec:
        filters["spec_id"] = args.spec
    if args.path_prefix:
        filters["path_prefix"] = args.path_prefix
    if filters:
        retriever = retriever.with_filters(**filters)
    docs = retriever.search(args.text, k=args.k)
    if args.json:
        print(
            json.dumps(
                [{"cite": cite(d), "score": d.metadata["score"], "text": d.page_content} for d in docs], indent=2
            )
        )
    else:
        for d in docs:
            print(f"[{d.metadata['score']:.4f}] {cite(d)}  ({d.metadata['kind']})")
            print("    " + d.page_content[:200].replace("\n", " ") + "\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
