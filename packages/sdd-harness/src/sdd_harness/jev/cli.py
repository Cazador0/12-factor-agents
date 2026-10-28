"""``sdd-jev``: Jev, the read-mostly progress watchdog.

    sdd-jev scan --sessions sessions.json --gitea-url http://localhost:3000  # token from $JEV_GITEA_TOKEN
    sdd-jev scan --sessions sessions.json --dry-run      # decide and record, write nothing to Gitea
    sdd-jev history <session-id>
    sdd-jev schema [--check]                             # schemas/jev-message.v1.json

Run every 10 minutes from the LangGraph service's scheduler or cron: */10 * * * *
Jev's token needs the scopes read:repository, write:issue and read:user (read:organization for organisation
labels), and its account must not have push, merge or admin rights.

The sessions file lists every supervised session: an open episode of a session missing from it is ended
(labels cleared, comment marked ended, never "recovered"). An entry that does not validate is reported and
skipped; the others are still scanned.

Exit codes: 0 scanned (or skipped: another scan holds the lock), 1 at least one session's scan failed or its
entry was invalid, 2 usage or configuration, 3 Gitea unreachable or refused the token at start-up,
4 refused: Jev's account has too many rights.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from datetime import UTC, datetime
from pathlib import Path

from pydantic import TypeAdapter, ValidationError

from ..config import Settings
from . import schema
from .explain import make_explainer
from .gitea import GiteaError, HttpGiteaClient
from .models import SessionInfo, Thresholds
from .scan import run_scan
from .store import ScanStore

SESSION = TypeAdapter(SessionInfo)


def _load_sessions(path: Path) -> tuple[list[SessionInfo], list[dict]]:
    """Validate each entry on its own: one malformed session must not stop Jev from scanning the rest.

    Raises ``OSError`` or ``ValueError`` when the file itself cannot be read as a JSON list.
    """
    raw = json.loads(path.read_text("utf-8"))
    if not isinstance(raw, list):
        raise ValueError("expected a JSON list of sessions")
    sessions: list[SessionInfo] = []
    invalid: list[dict] = []
    for i, item in enumerate(raw):
        try:
            sessions.append(SESSION.validate_python(item))
        except ValidationError as exc:
            sid = item.get("session_id") if isinstance(item, dict) else None
            problem = "; ".join(
                f"{'.'.join(map(str, e['loc'])) or 'entry'}: {e['msg']}"
                for e in exc.errors(include_url=False, include_input=False)
            )
            invalid.append({"session": str(sid) if sid else f"#{i}", "problem": problem})
    return sessions, invalid


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

    try:
        sessions, invalid = _load_sessions(Path(args.sessions))
    except (OSError, ValueError) as exc:
        print(f"sdd-jev: cannot read sessions from {args.sessions}: {exc}", file=sys.stderr)
        return 2
    token = os.environ.get(args.token_env)
    if not token:
        print(f"sdd-jev: set {args.token_env} to Jev's Gitea bot token", file=sys.stderr)
        return 2
    now = datetime.fromisoformat(args.now) if args.now else datetime.now(UTC)
    if now.tzinfo is None:
        now = now.replace(tzinfo=UTC)
    try:
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
    except PermissionError as exc:
        print(f"sdd-jev: refusing to run: {exc}", file=sys.stderr)
        return 4
    except GiteaError as exc:
        why = "refused Jev's token" if exc.status in (401, 403) else "unreachable"
        print(f"sdd-jev: Gitea {why} at start-up, nothing scanned: {exc}", file=sys.stderr)
        return 3
    report["invalid_sessions"] = invalid
    print(json.dumps(report, indent=2))
    return 1 if report.get("failed") or invalid else 0


if __name__ == "__main__":
    raise SystemExit(main())
