"""Collect a session's evidence: the command log, decision traces, checkpoints, pushed commits and CI.

Everything here reads; nothing writes. A source that cannot be read makes the scan ``unknown`` rather than
healthy or unhealthy, so "not observed" never reads as "passed" (Art. IV).
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

import yaml

from .gitea import GiteaClient, GiteaError, commit_outcome
from .models import CommitCI, Evidence, SessionInfo, Thresholds


def parse_ts(value: object) -> datetime | None:
    """An aware UTC datetime from an ISO string; anything else (missing, a number, garbage) is ``None``."""
    if not isinstance(value, str) or not value:
        return None
    try:
        dt = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    return dt.astimezone(UTC) if dt.tzinfo else dt.replace(tzinfo=UTC)


# ---------------------------------------------------------------- command log


@dataclass(frozen=True)
class CommandEvent:
    event: str  # start | end
    at: datetime
    tool: str
    action: str  # hash of the call (never its text), so equal calls compare equal
    tool_use_id: str | None = None
    exit_code: int | None = None
    ok: bool = True
    outcome: str = ""  # hash of the observation or error, never the text
    timed_out: bool = False
    timeout_s: int | None = None

    @property
    def fingerprint(self) -> tuple[str, str, str]:
        return (self.tool, self.action, self.outcome)


def read_commands(path: Path) -> list[CommandEvent]:
    """Lines written by .claude/hooks/command_log.py; malformed lines are skipped."""
    if not path.is_file():
        return []
    out: list[CommandEvent] = []
    for line in path.read_text("utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
            at = parse_ts(row.get("at"))
            if at is None:
                continue
            out.append(
                CommandEvent(
                    event=row.get("event", "end"),
                    at=at,
                    tool=str(row.get("tool", "Bash")),
                    action=str(row.get("action", "")),
                    tool_use_id=row.get("tool_use_id"),
                    exit_code=row.get("exit_code"),
                    ok=bool(row.get("ok", row.get("exit_code") in (0, None))),
                    outcome=str(row.get("outcome", "")),
                    timed_out=bool(row.get("timed_out", False)),
                    timeout_s=row.get("timeout_s"),
                )
            )
        except (json.JSONDecodeError, AttributeError, TypeError):
            continue
    out.sort(key=lambda e: e.at)
    return out


def trailing_identical(ends: list[CommandEvent]) -> int:
    """How many of the most recent completed calls share one fingerprint."""
    if not ends:
        return 0
    last = ends[-1].fingerprint
    n = 0
    for e in reversed(ends):
        if e.fingerprint != last:
            break
        n += 1
    return n


def trailing_alternation(ends: list[CommandEvent]) -> int:
    """Length of the A, B, A, B … tail made of exactly two distinct fingerprints."""
    if len(ends) < 4:
        return 0
    a, b = ends[-1].fingerprint, ends[-2].fingerprint
    if a == b:
        return 0
    n = 0
    for i, e in enumerate(reversed(ends)):
        if e.fingerprint != (a if i % 2 == 0 else b):
            break
        n += 1
    return n


def in_flight(events: list[CommandEvent]) -> CommandEvent | None:
    """The latest started call with no matching end."""
    ended = {e.tool_use_id for e in events if e.event == "end" and e.tool_use_id}
    starts = [e for e in events if e.event == "start" and e.tool_use_id and e.tool_use_id not in ended]
    return starts[-1] if starts else None


# ---------------------------------------------------------------- traces and checkpoints


def read_trace(path: Path) -> list[dict]:
    if not path.is_file():
        return []
    rows = []
    for line in path.read_text("utf-8", errors="replace").splitlines():
        try:
            row = json.loads(line)
        except json.JSONDecodeError:
            continue
        if isinstance(row, dict):
            rows.append(row)
    return rows


def read_checkpoint_at(path: Path) -> datetime | None:
    if not path.is_file():
        return None
    try:
        data = yaml.safe_load(path.read_text("utf-8")) or {}
    except yaml.YAMLError:
        return None
    cp = data.get("session_checkpoint", data) if isinstance(data, dict) else {}
    return parse_ts(str(cp.get("written_at"))) if isinstance(cp, dict) and cp.get("written_at") else None


def _tail(items: list, keep: int) -> list:
    return items[-keep:] if keep > 0 else []


# ---------------------------------------------------------------- CI


def ci_failing_streak(results: list[CommitCI]) -> int:
    """Consecutive head commits (newest first) whose CI completed with a real failure.

    Cancelled runs (Gitea maps them to ``failure``), commits with no statuses, and still-running CI neither count
    nor break the streak; a success breaks it. A failing commit whose failing contexts are a strict subset of the
    previous (older) failing commit's is converging, so it is skipped.
    """
    completed = [r for r in results if r.outcome in ("success", "failure")]
    streak = 0
    for i, r in enumerate(completed):
        if r.outcome == "success":
            break
        older = completed[i + 1] if i + 1 < len(completed) else None
        if older is not None and older.outcome == "failure" and r.failing_contexts < older.failing_contexts:
            continue
        streak += 1
    return streak


# ---------------------------------------------------------------- collect


def collect(
    root: Path,
    session: SessionInfo,
    gitea: GiteaClient,
    now: datetime,
    last_scan_at: datetime | None,
    t: Thresholds | None = None,
    commits_limit: int = 10,
    seen_heads: dict[str, datetime] | None = None,
) -> Evidence:
    """One scan's evidence.

    ``last_scan_at`` is the last *observed* scan (never an unknown one). ``seen_heads`` maps each branch head that
    earlier observed scans saw to when it was first seen: commit dates are committer dates, not push times, so once
    there is such history a push is dated by the scan that first saw it. Only evidence from this incarnation of the
    session (since ``started_at``) counts: a restarted session does not inherit the old command log, traces,
    checkpoint, commits or CI.
    """
    t = t or Thresholds()
    facts: list[str] = []
    started = session.started_at
    since = max(last_scan_at, started) if last_scan_at else started

    log_path = root / session.commands_log if session.commands_log else None
    events = [e for e in read_commands(log_path) if e.at >= started] if log_path else []
    ends = _tail([e for e in events if e.event == "end"], t.loop_window_events)
    trace_dir = root / ".specify" / "traces" / session.run_id if session.run_id else None
    rows = read_trace(trace_dir / "trace.jsonl") if trace_dir else []
    trace = [(r, ts) for r in rows if (ts := parse_ts(r.get("timestamp"))) and ts >= started]
    checkpoint_at = read_checkpoint_at(trace_dir / "checkpoint.yaml") if trace_dir else None
    if checkpoint_at is not None and checkpoint_at < started:
        checkpoint_at = None

    if log_path is None and trace_dir is None:
        return Evidence(session, now, observable=False, unobservable_reason="no command log or trace configured")

    loop_times = [e.at for e in events] + [ts for _, ts in trace]
    last_loop = max(loop_times) if loop_times else None
    flying = in_flight(events)

    durable_times = [ts for r, ts in trace if r.get("changed_state")]
    if checkpoint_at:
        durable_times.append(checkpoint_at)
    durable_since = any(ts > since for ts in durable_times)

    head: str | None = None
    results: list[CommitCI] = []
    if session.branch is not None:  # Lead and Review sessions own no branch: no push or CI signal
        try:
            commits = gitea.branch_commits(session.owner, session.repo, session.branch, commits_limit)
            mine = [c for c in commits if (ts := parse_ts(c.get("created"))) is None or ts >= started]
            results = [commit_outcome(gitea, session.owner, session.repo, c["sha"]) for c in mine]
        except GiteaError as exc:
            return Evidence(session, now, observable=False, unobservable_reason=f"Gitea unavailable: {exc}")
        head = str(commits[0]["sha"]) if commits else ""
        if seen_heads:  # a head not seen before was pushed since the last observed scan
            pushed = [seen_heads.get(head, now)] if head else []
        else:  # no observed history yet: committer dates are the best evidence (never later than now)
            pushed = [min(ts, now) for c in mine if (ts := parse_ts(c.get("created")))]
        durable_times += pushed
        durable_since = durable_since or any(ts > since for ts in pushed)
    last_durable = max(durable_times) if durable_times else None

    # Loop rules look at the tail of completed calls, but only when that tail grew since the last observed scan.
    fresh = bool(ends) and ends[-1].at > since
    trailing = trailing_identical(ends) if fresh else 0
    last_ok = ends[-1].ok if ends else True
    failing = sum(1 for e in ends if not e.ok and e.at > since)
    timeouts = 0
    for e in reversed(ends if fresh else []):
        if not e.timed_out:
            break
        timeouts += 1

    streak = ci_failing_streak(results)
    never = bool(results) and all(r.outcome == "none" for r in results)
    if never:
        facts.append("no CI status reported on recent head commits")
    return Evidence(
        session=session,
        now=now,
        last_loop_event_at=last_loop,
        in_flight_started_at=flying.at if flying else None,
        in_flight_timeout_s=flying.timeout_s if flying else None,
        last_durable_progress_at=last_durable,
        durable_progress_since_last_scan=durable_since,
        action_error_streak=trailing if not last_ok else 0,
        action_observation_streak=trailing if last_ok else 0,
        alternation_len=trailing_alternation(ends) if fresh else 0,
        consecutive_timeouts=timeouts,
        failing_commands_in_scan=failing,
        ci_failing_streak=streak,
        ci_never_reported=never,
        checkpoint_at=checkpoint_at,
        head_sha=head,
        facts=tuple(facts),
    )
