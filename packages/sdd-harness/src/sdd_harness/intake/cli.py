"""``sdd-intake``: run an intake session round by round from the command line.

Typical loop inside Claude Code::

    sdd-intake start "an app that reminds me to water my plants" --draft draft.json
    # → prints {"status": "awaiting_answers", "card": {"questions": [...]}, ...}
    #   pass card.questions to AskUserQuestion, then:
    sdd-intake answer plant-watering-reminders --answers answers.json
    # → the next round, or {"status": "finished", ...}
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
from . import session
from .cards import lint_card
from .document import parse
from .graph import has_checkpoint, run, sessions_db


def _read_json(arg: str | None) -> dict | list | None:
    if not arg:
        return None
    if arg == "-":
        raw = sys.stdin.read()
    elif arg.lstrip().startswith(("{", "[")):  # inline JSON; never stat it as a path (it may be too long)
        raw = arg
    else:
        raw = Path(arg).read_text("utf-8")
    return json.loads(raw)


def _intake_path(settings: Settings, slug: str) -> Path:
    path = settings.intakes_dir / slug / "intake.md"
    if not path.is_file():
        raise SystemExit(f"No intake at {path}")
    return path


def _emit(obj: dict) -> None:
    print(json.dumps(obj, indent=2, ensure_ascii=False))


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sdd-intake", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--root", type=Path, default=None, help="Project root (default: nearest folder with .specify/)")
    sub = p.add_subparsers(dest="cmd", required=True)

    s = sub.add_parser("start", help="Write the Draft intake and return round 1")
    s.add_argument("idea")
    s.add_argument("--slug")
    s.add_argument("--scope", choices=["auto", "project", "feature"], default="auto")
    s.add_argument(
        "--draft", help="JSON (file, '-' or inline): title, interpretation, idea_type, rows, assumptions, questions"
    )
    s.add_argument("--no-ask", action="store_true", help="Write the Draft only (non-interactive hook runs)")

    a = sub.add_parser("answer", help="Record a round's answers and return the next round")
    a.add_argument("slug")
    a.add_argument(
        "--answers", required=True, help="AskUserQuestion result JSON: {answers: {...}, annotations?: {...}}"
    )

    n = sub.add_parser("next", help="Show the round waiting for answers (recomputed from the file if needed)")
    n.add_argument("slug")

    st = sub.add_parser("status", help="Rows, questions and open items")
    st.add_argument("slug")
    st.add_argument("--json", action="store_true")

    f = sub.add_parser("finish", help="Stop asking and close the intake")
    f.add_argument("slug")

    q = sub.add_parser("questions", help="Add questions, or rewrite a pending one with --replace Q#")
    q.add_argument("slug")
    q.add_argument("--json", required=True, help="A question object or a list of them")
    q.add_argument("--replace")

    r = sub.add_parser("rate", help="Set a row's status with evidence (host judgment)")
    r.add_argument("slug")
    r.add_argument("row")
    r.add_argument("status", choices=["Missing", "Partial", "Sufficient", "Delegated", "N/A", "Open"])
    r.add_argument("--evidence", required=True)
    r.add_argument("--still-needed", default="—")

    rs = sub.add_parser("resolve", help="Mark a question 'Not asked — resolved by Q#'")
    rs.add_argument("slug")
    rs.add_argument("qid")
    rs.add_argument("--by", required=True)
    rs.add_argument("--reason", required=True)

    rv = sub.add_parser("revise", help="Record a changed answer; the earlier one stays visible as superseded")
    rv.add_argument("slug")
    rv.add_argument("qid")
    rv.add_argument("--answer", required=True, help="The person's new answer, verbatim (option label or own words)")

    asm = sub.add_parser("assume", help="Add an assumption (unconfirmed unless cited)")
    asm.add_argument("slug")
    asm.add_argument("text")
    asm.add_argument("--citation", help="e.g. 'constitution Art. III' or 'prior decision (memory 2026-09-25)'")

    lint = sub.add_parser("lint", help="Check an AskUserQuestion payload against the card rules")
    lint.add_argument("json")

    args = p.parse_args(argv)
    settings = Settings.load(args.root)

    if args.cmd == "lint":
        data = _read_json(args.json)
        cards = data.get("questions", [data]) if isinstance(data, dict) else data
        report = {c.get("question", f"#{i}"): lint_card(c) for i, c in enumerate(cards)}
        _emit({"ok": not any(report.values()), "problems": report})
        return 0 if not any(report.values()) else 1

    with sqlite3.connect(sessions_db(settings), check_same_thread=False) as conn:
        saver = SqliteSaver(conn)
        if args.cmd == "start":
            draft = _read_json(args.draft)
            slug = (
                session.normalize_slug(args.slug)
                if args.slug
                else session.slugify((draft or {}).get("title") or args.idea)
            )
            slug = session.unique_dir(settings.intakes_dir, slug).name
            state = {"root": str(settings.root), "idea": args.idea, "slug": slug, "scope": args.scope, "draft": draft}
            if args.no_ask:
                path, problems = session.create(
                    settings,
                    args.idea,
                    slug=slug,
                    scope=args.scope,
                    draft=session.DraftInput.from_host(draft) if draft else None,
                )
                path.write_text(
                    path.read_text("utf-8").replace("**Status**: Draft", "**Status**: Draft — needs a session", 1),
                    "utf-8",
                )
                _emit({"status": "draft_only", "intake": str(path), "lint": problems})
                return 0
            _emit(run(settings, slug, state, saver))
            return 0

        path = _intake_path(settings, args.slug)
        if args.cmd == "answer":
            reply = _read_json(args.answers) or {}
            notes = {k: v.get("notes") for k, v in (reply.get("annotations") or {}).items() if v.get("notes")}
            answers = reply.get("answers", reply)
            if not has_checkpoint(saver, args.slug):
                # Fresh session: replay to the same interrupt from the file, then answer it.
                run(settings, args.slug, {"root": str(settings.root), "path": str(path)}, saver)
            _emit(run(settings, args.slug, Command(resume={"answers": answers, "notes": notes}), saver))
            return 0
        if args.cmd == "next":
            snapshot = saver.get_tuple({"configurable": {"thread_id": args.slug}})
            if snapshot is None:
                _emit(run(settings, args.slug, {"root": str(settings.root), "path": str(path)}, saver))
            else:
                from .graph import build_graph

                st_ = build_graph(saver).get_state({"configurable": {"thread_id": args.slug}})
                pending = [i.value for t in st_.tasks for i in t.interrupts]
                _emit({"status": "awaiting_answers", **pending[0]} if pending else {"status": "idle"})
            return 0
        if args.cmd == "finish":
            _emit(session.finish(settings, path, stopped=True))
            return 0
        if args.cmd == "status":
            intake = parse(path.read_text("utf-8"))
            data = {
                "intake": str(path),
                "status": intake.status,
                "round": intake.round,
                "rows": {r.id: r.status for r in intake.rows},
                "questions": {q.id: q.state for q in intake.questions},
                "open_items": intake.open_items,
            }
            if args.json:
                _emit(data)
            else:
                ok, total = intake.counts()
                print(f"{path}\nStatus: {intake.status} · round {intake.round} · {ok} of {total} rows settled")
                for row in intake.rows:
                    print(f"  {row.id:<4} {row.status:<10} {row.name}")
            return 0
        if args.cmd == "questions":
            data = _read_json(args.json)
            items = data if isinstance(data, list) else [data]
            dqs = [session.DraftQuestion.model_validate(x) for x in items]
            if args.replace:
                problems = session.replace_question(settings, path, args.replace, dqs[0])
            else:
                problems = session.add_questions(settings, path, dqs)
            _emit({"ok": not problems, "lint": problems})
            return 0
        if args.cmd == "rate":
            session.set_row(settings, path, args.row, args.status, args.evidence, args.still_needed)
            _emit({"ok": True})
            return 0
        if args.cmd == "resolve":
            session.resolve(settings, path, args.qid, args.by, args.reason)
            _emit({"ok": True})
            return 0
        if args.cmd == "revise":
            _emit(session.revise(settings, path, args.qid, args.answer))
            return 0
        if args.cmd == "assume":
            _emit({"ok": True, "id": session.add_assumption(settings, path, args.text, args.citation)})
            return 0
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
