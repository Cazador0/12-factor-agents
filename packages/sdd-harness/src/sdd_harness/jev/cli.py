"""``sdd-jev``: Jev, the read-mostly progress watchdog.

    sdd-jev scan --sessions sessions.json --gitea-url http://localhost:3000  # token from $JEV_GITEA_TOKEN
    sdd-jev scan --sessions sessions.json --dry-run      # decide and record, write nothing to Gitea
    sdd-jev history <session-id>
    sdd-jev schema [--check]                             # schemas/jev-message.v1.json

Run every 10 minutes from the LangGraph service's scheduler or cron: */10 * * * *
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter

from ..config import Settings
from . import schema
from .explain import make_explainer
from .gitea import HttpGiteaClient
from .models import SessionInfo, Thresholds
from .scan import run_scan
from .store import ScanStore

SESSIONS = TypeAdapter(list[SessionInfo])


def _db(settings: Settings) -> Path:
    return settings.root / ".specify" / "sessions" / "jev.sqlite"


def main(argv: list[str] | None = None) -> int:
    p = argparse.ArgumentParser(prog="sdd-jev", description=__doc__, formatter_class=argparse.RawTextHelpFormatter)
    p.add_argument("--root", type=Path, default=None)
    sub = p.add_subparsers(dest="cmd", required=True)
    sc = sub.add_parser("scan", help="Scan every supervised session once")
    sc.add_argument("--sessions", required=True, help="JSON list of sessions (the control plane's view, spec 001)")
    sc.add_argument("--gitea-url", default=os.environ.get("JEV_GITEA_URL", "http://localhost:3000"))
    sc.add_argument("--token-env", default="JEV_GITEA_TOKEN", help="Environment variable holding Jev's bot token")
    sc.add_argument("--dry-run", action="store_true", help="Decide and record locally; write nothing to Gitea")
    sc.add_argument("--explain", choices=["none", "claude", "ollama"], default="none")
    sc.add_argument("--now", help="ISO timestamp to scan as (tests and replays)")
    h = sub.add_parser("history", help="Show a session's scan history")
    h.add_argument("session_id")
    h.add_argument("-n", type=int, default=12)
    s = sub.add_parser("schema", help="Write or check schemas/jev-message.v1.json")
    s.add_argument("--check", action="store_true")
    args = p.parse_args(argv)
    settings = Settings.load(args.root)

    if args.cmd == "schema":
        if args.check:
            ok = schema.is_current(settings.root)
            print("schema is current" if ok else "schema is stale: run sdd-jev schema")
            return 0 if ok else 1
        print(schema.write(settings.root))
        return 0
    if args.cmd == "history":
        store = ScanStore(_db(settings))
        try:
            for r in store.history(args.session_id, limit=args.n):
                reasons = ",".join(x.value for x in r.reasons) or "-"
                episode = r.episode_id or "-"
                print(f"{r.scan_id}  {r.kind.value:<15} {r.next_action.value:<14} {reasons}  episode={episode}")
        finally:
            store.close()
        return 0

    sessions = SESSIONS.validate_json(Path(args.sessions).read_text("utf-8"))
    token = os.environ.get(args.token_env)
    if not token:
        print(f"sdd-jev: set {args.token_env} to Jev's Gitea bot token", file=sys.stderr)
        return 2
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    report = run_scan(
        settings.root,
        sessions,
        HttpGiteaClient(args.gitea_url, token),
        _db(settings),
        now,
        Thresholds(),
        dry_run=args.dry_run,
        explain=make_explainer(args.explain, settings),
    )
    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
