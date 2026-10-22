"""``sdd-refine``: build a phase's decision ledger and put its unbacked decisions to the person.

sdd-refine start specify                    # ledger → intake; prints round 1 for AskUserQuestion
sdd-refine answer specify --answers a.json  # records the round; prints the next one or the summary
sdd-refine ledger specify [--json]          # show the ledger without asking anything
"""

from __future__ import annotations

import argparse
import json
import sqlite3
import sys
from pathlib import Path

from langgraph.checkpoint.sqlite import SqliteSaver
from langgraph.types import Command

from ..config import Settings
from . import ledger as lg
from .extract import PHASES
from .graph import run


def _read_json(arg: str) -> dict:
    if arg == "-":
        raw = sys.stdin.read()
    elif arg.lstrip().startswith(("{", "[")):  # inline JSON; never stat it as a path (it may be too long)
        raw = arg
    else:
        raw = Path(arg).read_text("utf-8")
    return json.loads(raw)


def _feature_dir(settings: Settings, phase: str, given: str | None) -> Path | None:
    if phase == "constitution":
        return None
    if given:
        p = Path(given)
        return p if p.is_absolute() else settings.root / p
    fd = lg.feature_dir_from_scripts(settings.root)
    if fd is None:
        raise SystemExit("No FEATURE_DIR: pass --feature-dir specs/###-name")
    return fd


def _thread(phase: str, fd: Path | None) -> str:
    return f"refine-{phase}-{fd.name if fd else 'project'}"


def _db(settings: Settings) -> Path:
    p = settings.root / ".specify" / "sessions" / "refine.sqlite"
    p.parent.mkdir(parents=True, exist_ok=True)
    return p


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sdd-refine", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--root", type=Path, default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    for name in ("start", "ledger", "answer"):
        sp = sub.add_parser(name)
        sp.add_argument("phase", choices=PHASES)
        sp.add_argument("--feature-dir")
        if name in {"start", "ledger"}:
            sp.add_argument("--findings", help="analyze phase: the analysis report (Markdown or JSON)")
            sp.add_argument("--base", help="implement phase: git ref the tasks were written at")
            sp.add_argument(
                "--source",
                action="append",
                default=[],
                help="A document the person supplied (brief, report) to count as backing; repeatable",
            )
        if name == "ledger":
            sp.add_argument("--json", action="store_true")
        if name == "answer":
            sp.add_argument("--answers", required=True)
    args = p.parse_args(argv)
    settings = Settings.load(args.root)
    fd = _feature_dir(settings, args.phase, args.feature_dir)

    if args.cmd == "ledger":
        ledger, path = lg.build(
            settings,
            args.phase,
            fd,
            Path(args.findings) if args.findings else None,
            args.base,
            [Path(x) for x in args.source],
        )
        if args.json:
            print(json.dumps(lg.as_dict(ledger), indent=2, ensure_ascii=False))
        else:
            print(f"{path}\n{lg.summary(ledger)}")
            for r in ledger.rows:
                print(f"  {r.n:>3} {r.group:<11} {r.id:<8} {r.where:<40} {r.text[:70]}")
        return 0

    with sqlite3.connect(_db(settings), check_same_thread=False) as conn:
        saver = SqliteSaver(conn)
        thread = _thread(args.phase, fd)
        if args.cmd == "start":
            state = {
                "root": str(settings.root),
                "phase": args.phase,
                "feature_dir": str(fd) if fd else None,
                "findings": args.findings,
                "base": args.base,
                "sources": args.source,
            }
            # A new start rebuilds the ledger: drop any half-finished round for this phase.
            saver.delete_thread(thread)
            print(json.dumps(run(thread, state, saver), indent=2, ensure_ascii=False))
            return 0
        reply = _read_json(args.answers)
        notes = {k: v.get("notes") for k, v in (reply.get("annotations") or {}).items() if v.get("notes")}
        answers = reply.get("answers", reply)
        if saver.get_tuple({"configurable": {"thread_id": thread}}) is None:
            intake = lg.find_intake(settings, args.phase, fd)
            sidecar = lg.sidecar_path(settings, args.phase, intake, fd)
            if not sidecar.is_file():
                raise SystemExit("No ledger for this phase yet: run `sdd-refine start` first")
            run(thread, {"root": str(settings.root), "phase": args.phase, "sidecar": str(sidecar)}, saver)
        print(
            json.dumps(
                run(thread, Command(resume={"answers": answers, "notes": notes}), saver), indent=2, ensure_ascii=False
            )
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
