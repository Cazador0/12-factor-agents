"""``sdd-route`` (also behind ``bin/intakespec``): find a skill for a spec-driven task.

sdd-route find 'plan the storage layer'     # JSON: name, classification, absolute_path, …
sdd-route check                             # is the stored skills graph current?
sdd-route build                             # rebuild .specify/index/skills-graph.json
sdd-route show speckit-plan                 # one node with its edges and screen findings
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

from ..config import Settings
from .catalog import build_nodes, check, edges, save_graph
from .graph import route


def main(argv: list[str] | None = None, prog: str = "sdd-route") -> int:
    p = argparse.ArgumentParser(prog=prog, description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--root", type=Path, default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    f = sub.add_parser("find", help="Route a task to skills (or to intake)")
    f.add_argument("terms", nargs="+")
    f.add_argument("-k", type=int, default=8)
    f.add_argument("--reasoning", action="store_true", help="Also print the visible reasoning chain")
    sub.add_parser("check", help="Report whether the skills graph is current")
    sub.add_parser("build", help="Rebuild the skills graph")
    s = sub.add_parser("show", help="Show one skill node")
    s.add_argument("name")
    args = p.parse_args(argv)
    settings = Settings.load(args.root)

    if args.cmd == "find":
        state = route(settings, " ".join(args.terms), args.k)
        if state.get("route") == "intake":
            out = {"route": "intake", "message": state["message"], "results": []}
        else:
            keep = (
                "name",
                "classification",
                "absolute_path",
                "stage",
                "tier",
                "findings",
                "source",
                "score",
                "why",
                "description",
            )
            out = {
                "route": "skill",
                "stage": state.get("stage"),
                "results": [
                    {k: (r[k][:300] if k == "description" else r[k]) for k in keep} for r in state.get("results", [])
                ],
            }
            if args.reasoning:
                out["reasoning"] = state.get("reasoning")
        print(json.dumps(out, indent=2, ensure_ascii=False))
        return 0
    if args.cmd == "check":
        report = check(settings)
        print(json.dumps(report, indent=2))
        print("graph is current" if report["current"] else "graph is NOT current — run: build")
        return 0 if report["current"] else 1
    if args.cmd == "build":
        nodes = build_nodes(settings)
        path = save_graph(settings, nodes)
        tiers = {t: sum(n.tier == t for n in nodes) for t in (1, 2, 3)}
        print(json.dumps({"skills": len(nodes), "edges": len(edges(nodes)), "tiers": tiers, "graph": str(path)}))
        return 0
    if args.cmd == "show":
        nodes = build_nodes(settings)
        matches = [n for n in nodes if n.name == args.name]
        es = [e for e in edges(nodes) if args.name in (e["from"], e["to"])]
        print(json.dumps({"nodes": [n.__dict__ for n in matches], "edges": es}, indent=2))
        return 0 if matches else 1
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
