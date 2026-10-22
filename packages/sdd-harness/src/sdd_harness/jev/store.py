"""Jev's local memory: scan history keyed by (session_id, scan_id), and comment intents for idempotent posting."""

from __future__ import annotations

import json
import sqlite3
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path

from .decide import consecutive_bad_scans
from .models import JevKind, JevMessage, NextAction, Reason, ScanRecord

SCHEMA = """
CREATE TABLE IF NOT EXISTS scans (
    session_id TEXT NOT NULL,
    scan_id TEXT NOT NULL,
    at TEXT NOT NULL,
    kind TEXT NOT NULL,
    reasons TEXT NOT NULL,
    next_action TEXT NOT NULL,
    episode_id TEXT,
    durable_progress INTEGER NOT NULL,
    head_sha TEXT,                  -- branch head this scan saw; '' = nothing pushed; NULL = not read
    message TEXT NOT NULL,
    PRIMARY KEY (session_id, scan_id)
);
CREATE INDEX IF NOT EXISTS scans_by_time ON scans (session_id, at DESC);
CREATE TABLE IF NOT EXISTS intents (
    key TEXT PRIMARY KEY,           -- the episode's comment key (marker in the comment body)
    session_id TEXT NOT NULL,
    owner TEXT NOT NULL,
    repo TEXT NOT NULL,
    issue INTEGER NOT NULL,
    episode_id TEXT NOT NULL,
    recovery_point TEXT NOT NULL,   -- intended → posted → resolved
    comment_id INTEGER,
    updated_at TEXT NOT NULL
);
"""


def _iso(dt: datetime) -> str:
    return dt.astimezone(UTC).isoformat(timespec="seconds")


@dataclass(frozen=True)
class Intent:
    key: str
    owner: str
    repo: str
    issue: int
    episode_id: str
    recovery_point: str
    comment_id: int | None


class ScanStore:
    def __init__(self, path: Path):
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.db = sqlite3.connect(path)
        self.db.executescript(SCHEMA)

    def close(self) -> None:
        self.db.close()

    def record(self, msg: JevMessage, at: datetime, durable_progress: bool, head_sha: str | None = None) -> None:
        """Insert or replace the scan; a retried scan in the same slot overwrites itself, never duplicates."""
        self.db.execute(
            "INSERT OR REPLACE INTO scans VALUES (?,?,?,?,?,?,?,?,?,?)",
            (
                msg.session_id,
                msg.scan_id,
                _iso(at),
                msg.kind.value,
                json.dumps([r.value for r in msg.reasons]),
                msg.next_action.value,
                msg.episode_id,
                int(durable_progress),
                head_sha,
                msg.model_dump_json(),
            ),
        )
        self.db.commit()

    def history(self, session_id: str, before_scan: str | None = None, limit: int = 50) -> list[ScanRecord]:
        """Earlier scans, newest first (excluding ``before_scan`` itself when re-running a slot)."""
        rows = self.db.execute(
            "SELECT session_id, scan_id, at, kind, reasons, next_action, episode_id, durable_progress, head_sha "
            "FROM scans WHERE session_id = ? AND (? IS NULL OR scan_id < ?) ORDER BY scan_id DESC LIMIT ?",
            (session_id, before_scan, before_scan, limit),
        ).fetchall()
        return [
            ScanRecord(
                session_id=r[0],
                scan_id=r[1],
                at=datetime.fromisoformat(r[2]),
                kind=JevKind(r[3]),
                reasons=tuple(Reason(x) for x in json.loads(r[4])),
                next_action=NextAction(r[5]),
                episode_id=r[6],
                durable_progress=bool(r[7]),
                head_sha=r[8],
            )
            for r in rows
        ]

    def consecutive_non_healthy(self, session_id: str, lookback: int = 6) -> int:
        """Consecutive warn/stuck/stop scans, newest first. Unknown scans are skipped; a durable-progress ok ends it."""
        return consecutive_bad_scans(self.history(session_id), lookback)

    # ---------------------------------------------------------------- comment intents

    def intent(self, key: str) -> Intent | None:
        row = self.db.execute(
            "SELECT key, owner, repo, issue, episode_id, recovery_point, comment_id FROM intents WHERE key = ?", (key,)
        ).fetchone()
        return Intent(*row) if row else None

    def unresolved(self, session_id: str) -> list[Intent]:
        """This session's episode comments not yet marked resolved, oldest first."""
        rows = self.db.execute(
            "SELECT key, owner, repo, issue, episode_id, recovery_point, comment_id FROM intents "
            "WHERE session_id = ? AND recovery_point != 'resolved' ORDER BY updated_at",
            (session_id,),
        ).fetchall()
        return [Intent(*r) for r in rows]

    def mark_intent(
        self,
        key: str,
        session_id: str,
        where: tuple[str, str, int],
        episode_id: str,
        point: str,
        comment_id: int | None,
        now: datetime,
    ) -> None:
        owner, repo, issue = where
        self.db.execute(
            "INSERT INTO intents VALUES (?,?,?,?,?,?,?,?,?) ON CONFLICT(key) DO UPDATE SET "
            "recovery_point = excluded.recovery_point, comment_id = COALESCE(excluded.comment_id, intents.comment_id), "
            "updated_at = excluded.updated_at",
            (key, session_id, owner, repo, issue, episode_id, point, comment_id, _iso(now)),
        )
        self.db.commit()

    def others_unresolved_on(self, where: tuple[str, str, int], key: str) -> bool:
        """Whether another unresolved episode (any session) still shares this issue, so its labels must stay."""
        owner, repo, issue = where
        row = self.db.execute(
            "SELECT 1 FROM intents WHERE owner = ? AND repo = ? AND issue = ? AND key != ? "
            "AND recovery_point != 'resolved' LIMIT 1",
            (owner, repo, issue, key),
        ).fetchone()
        return row is not None

    def forget_comment(self, key: str) -> None:
        """The stored comment is gone (a person deleted it): the next write searches by marker or posts anew."""
        self.db.execute("UPDATE intents SET comment_id = NULL, recovery_point = 'intended' WHERE key = ?", (key,))
        self.db.commit()

    def prune_intents(self, now: datetime, keep_hours: int = 72) -> int:
        """Dedup records live at least 72 hours (research: survive a weekend before a person answers).

        An open episode refreshes its row on every scan, so only resolved rows and rows of sessions no longer
        scanned go stale; a pruned row's comment is still found by its marker.
        """
        cutoff = _iso(now - timedelta(hours=keep_hours))
        cur = self.db.execute("DELETE FROM intents WHERE updated_at < ?", (cutoff,))
        self.db.commit()
        return cur.rowcount
