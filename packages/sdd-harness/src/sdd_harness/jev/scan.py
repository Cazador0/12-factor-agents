"""One Jev scan over the supervised sessions: collect → decide → record → (for warn, stuck, stop) comment and label.

Jev's write set is its own issue comments and its ``jev/*`` labels. It never edits code, pushes, approves or
merges; a stop is a request the session and the Lead carry out (Art. III). Healthy and unknown scans are recorded
locally only, except that a healthy scan finishes resolving episodes that have closed, and every run ends the open
episodes of sessions that are no longer supervised.
"""

from __future__ import annotations

import fcntl
import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import IO

from .decide import decide, open_episode, scan_slot
from .gitea import GiteaClient, GiteaError, find_comment, label_ids, marker, self_check
from .models import (
    Evidence,
    JevKind,
    JevMessage,
    NextAction,
    Reason,
    ScanRecord,
    SessionInfo,
    Thresholds,
    as_utc,
    idempotency_key,
)
from .signals import collect
from .store import Intent, ScanStore

LABEL_WARN, LABEL_STUCK, LABEL_PARKED = "jev/warning", "jev/stuck", "jev/parked"
JEV_LABELS = [LABEL_WARN, LABEL_STUCK, LABEL_PARKED]

Explainer = Callable[[JevMessage], str | None]
LabelMaps = dict[tuple[str, str], dict[str, int]]

SUMMARY = {
    NextAction.NUDGE_SESSION: "First bad scan: the session is nudged. A second consecutive bad scan means stuck.",
    NextAction.REQUEST_STOP: (
        "Stuck: the session is asked to write its checkpoint and release its lease; the Lead is notified."
    ),
    NextAction.HARD_STOP: (
        "The stop grace window passed without a checkpoint: the Lead stops the session; lease expiry is the backstop."
    ),
    NextAction.NOTIFY_LEAD: (
        "The session has stopped (or its lease went stale): the Lead re-plans, reassigns or recovers."
    ),
    NextAction.PAGE_PERSON: "Escalated to a person: the Lead did not act in time, or the episode is still unresolved.",
    NextAction.PARK: "Parked after repeated restarts: a person must reset it.",
}


@dataclass
class ScanResult:
    message: JevMessage
    actions: list[str] = field(default_factory=list)
    problems: list[str] = field(default_factory=list)


def episode_key(session_id: str, episode_id: str | None, owner: str, repo: str, issue: int | None) -> str:
    """One living comment per episode per work item."""
    return idempotency_key(session_id, episode_id, f"episode:{owner}/{repo}#{issue}")


def render_comment(msg: JevMessage, key: str, explanation: str | None = None, resolved: bool = False) -> str:
    title = "resolved" if resolved else msg.kind.value
    lines = [marker(key), f"**Jev** · {title} · `{msg.session_id}` · scan {msg.scan_id}", ""]
    lines.append("This stall episode has recovered." if resolved else SUMMARY.get(msg.next_action, ""))
    if msg.evidence:
        lines += ["", *[f"- {fact}" for fact in msg.evidence]]
    lines += ["", "```json", json.dumps(json.loads(msg.model_dump_json()), indent=2), "```"]
    if explanation:
        lines += ["", "_Explanation (model-written; the verdict above was decided by code):_", "", explanation.strip()]
    return "\n".join(lines) + "\n"


def render_ended(key: str, session_id: str, episode_id: str, scan_id: str) -> str:
    """An episode whose session is no longer supervised ended; it did not recover (spec 008: never report a stopped
    session as recovered)."""
    return (
        f"{marker(key)}\n**Jev** · ended · `{session_id}` · scan {scan_id}\n\n"
        f"Stall episode `{episode_id}` ended without recovering: the session is no longer supervised (stopped, "
        "reassigned or removed). The Lead's re-plan decides what happens to the work.\n"
    )


def _labels_for(gitea: GiteaClient, maps: LabelMaps, owner: str, repo: str) -> dict[str, int]:
    if (owner, repo) not in maps:
        maps[(owner, repo)] = label_ids(gitea, owner, repo, JEV_LABELS)
    return maps[(owner, repo)]


def _upsert_comment(
    gitea: GiteaClient,
    store: ScanStore,
    s: SessionInfo,
    issue: int,
    msg: JevMessage,
    key: str,
    login: str,
    body: str,
    now: datetime,
) -> str:
    """One living comment per episode: find it by the stored id or the marker, then edit; post only if absent."""
    where = (s.owner, s.repo, issue)
    episode = msg.episode_id or "-"
    known = store.intent(key)
    comment_id = known.comment_id if known else None
    # Recorded before any Gitea call, so the episode is resolved (and its label cleared) even if every write fails.
    store.mark_intent(key, s.session_id, where, episode, "intended", comment_id, now)
    if comment_id is None:
        comment_id = find_comment(gitea, s.owner, s.repo, issue, key, login)  # crashed after POST last time
    action = ""
    if comment_id is not None:
        try:
            gitea.edit_comment(s.owner, s.repo, comment_id, body)
            action = f"edited comment {comment_id}"
        except GiteaError as exc:
            if exc.status != 404:
                raise
            store.forget_comment(key)  # a person deleted it: post the episode's comment again
            comment_id = None
    if comment_id is None:
        comment_id = gitea.create_comment(s.owner, s.repo, issue, body)
        action = f"posted comment {comment_id}"
    store.mark_intent(key, s.session_id, where, episode, "posted", comment_id, now)
    return action


def _resolve_closed(
    gitea: GiteaClient,
    store: ScanStore,
    s: SessionInfo,
    msg: JevMessage,
    still_open: str | None,
    login: str,
    maps: LabelMaps,
    now: datetime,
    dry_run: bool,
    result: ScanResult,
    live: frozenset[str] | None,
) -> None:
    """Finish every closed episode of this session: clear its labels and mark its comment resolved.

    Runs on every ok scan until each one succeeds, so a failed Gitea write is retried rather than forgotten. Labels
    stay while another supervised session's unresolved episode still shares the issue.
    """
    for intent in store.unresolved(s.session_id):
        if intent.episode_id == still_open:
            continue
        if dry_run:
            result.actions.append(f"would resolve episode {intent.episode_id}")
            continue
        try:
            body = render_comment(msg, intent.key, resolved=True)
            _close(gitea, store, s.session_id, intent, login, maps, now, body, live)
            result.actions.append(f"resolved episode {intent.episode_id}")
        except GiteaError as exc:
            result.problems.append(f"episode {intent.episode_id} not resolved yet, will retry next ok scan: {exc}")


def _close(
    gitea: GiteaClient,
    store: ScanStore,
    session_id: str,
    intent: Intent,
    login: str,
    maps: LabelMaps,
    now: datetime,
    body: str,
    live: frozenset[str] | None,
) -> None:
    """Clear the episode's labels (unless another episode still shares the issue), rewrite its comment, mark it."""
    where = (intent.owner, intent.repo, intent.issue)
    if not store.others_unresolved_on(where, intent.key, live):
        labels = _labels_for(gitea, maps, intent.owner, intent.repo)
        for name in (LABEL_WARN, LABEL_STUCK):  # parked needs a person's reset
            if name in labels:
                gitea.remove_label(intent.owner, intent.repo, intent.issue, labels[name])  # absent label: no-op
    cid = intent.comment_id or find_comment(gitea, intent.owner, intent.repo, intent.issue, intent.key, login)
    if cid is not None:
        try:
            gitea.edit_comment(intent.owner, intent.repo, cid, body)
        except GiteaError as exc:
            if exc.status != 404:  # a deleted comment has nothing left to resolve
                raise
    store.mark_intent(intent.key, session_id, where, intent.episode_id, "resolved", cid, now)


def _end_unsupervised(
    gitea: GiteaClient,
    store: ScanStore,
    live: frozenset[str],
    login: str,
    maps: LabelMaps,
    now: datetime,
    scan_id: str,
    dry_run: bool,
) -> tuple[list[str], list[str]]:
    """End the open episodes of sessions no longer scanned, so their labels never outlive them. (actions, problems)"""
    actions: list[str] = []
    problems: list[str] = []
    for session_id, intent in store.unresolved_elsewhere(live):
        if dry_run:
            actions.append(f"would end episode {intent.episode_id} of {session_id}: no longer supervised")
            continue
        try:
            body = render_ended(intent.key, session_id, intent.episode_id, scan_id)
            _close(gitea, store, session_id, intent, login, maps, now, body, live)
            actions.append(f"ended episode {intent.episode_id} of {session_id}: no longer supervised")
        except GiteaError as exc:
            problems.append(f"episode {intent.episode_id} of {session_id} not ended yet, will retry next run: {exc}")
    return actions, problems


def scan_session(
    root: Path,
    s: SessionInfo,
    gitea: GiteaClient,
    store: ScanStore,
    now: datetime,
    login: str,
    maps: LabelMaps,
    t: Thresholds,
    dry_run: bool = False,
    explain: Explainer | None = None,
    live: frozenset[str] | None = None,
) -> tuple[ScanResult, Evidence]:
    scan_id = scan_slot(now, t.scan_interval_min)
    # This incarnation's *observed* scans, uncapped: an unknown scan saw nothing and moves nothing, and no run of
    # unknown scans can push the episode's own records out of view.
    history = store.history(s.session_id, before_scan=scan_id, limit=None, observed_only=True, since=s.started_at)
    seen_heads: dict[str, datetime] = {}
    for r in reversed(history):  # oldest first: keep when each head was first seen
        if r.head_sha is not None:
            seen_heads.setdefault(r.head_sha, r.at)
    first = next((r for r in reversed(history) if r.head_sha is not None), None)
    baseline = (first.head_sha, first.at) if first is not None and first.head_sha is not None else None
    last_at = history[0].at if history else None
    ev = collect(root, s, gitea, now, last_at, t, seen_heads=seen_heads, baseline=baseline)
    v = decide(ev, history, t)
    level = f"{v.kind.value}:{v.next_action.value}"
    msg = JevMessage(
        kind=v.kind,
        scan_id=scan_id,
        session_id=s.session_id,
        issue=s.issue,
        reasons=v.reasons,
        next_action=v.next_action,
        episode_id=v.episode_id,
        evidence=v.facts,
        idempotency_key=idempotency_key(s.session_id, v.episode_id, level),
    )
    ci_streak = ev.ci_failing_streak if ev.head_sha is not None else None
    store.record(msg, now, ev.durable_progress_since_last_scan, ev.head_sha, ci_streak)
    result = ScanResult(msg)

    if v.kind is JevKind.OK:
        current = ScanRecord(
            s.session_id, scan_id, now, JevKind.OK, (), NextAction.NONE, None, ev.durable_progress_since_last_scan
        )
        still_open = open_episode([current, *history], t.recovery_hold_scans)
        _resolve_closed(gitea, store, s, msg, still_open, login, maps, now, dry_run, result, live)
        return result, ev
    if v.kind is JevKind.UNKNOWN:
        return result, ev
    if s.issue is None:
        result.problems.append("no issue to comment on; verdict recorded locally only")
        return result, ev
    key = episode_key(s.session_id, v.episode_id, s.owner, s.repo, s.issue)
    label = (
        LABEL_PARKED if v.next_action is NextAction.PARK else (LABEL_WARN if v.kind is JevKind.WARN else LABEL_STUCK)
    )
    if dry_run:
        result.actions += [f"would upsert episode comment {key}", f"would add label {label}"]
        return result, ev
    explanation = None
    if explain is not None:
        try:
            explanation = explain(msg)
        except Exception as exc:  # an explanation is optional and never changes the verdict
            result.problems.append(f"explanation skipped: {exc}")
    try:
        result.actions.append(
            _upsert_comment(gitea, store, s, s.issue, msg, key, login, render_comment(msg, key, explanation), now)
        )
    except GiteaError as exc:
        result.problems.append(f"comment write failed, will retry next scan: {exc}")
    try:  # independent of the comment: a failed comment never holds back the label, nor the reverse
        labels = _labels_for(gitea, maps, s.owner, s.repo)
        if label in labels:
            applied = gitea.add_labels(s.owner, s.repo, s.issue, [labels[label]])
            if labels[label] in applied:
                result.actions.append(f"label {label}")
            else:
                result.problems.append(f"label {label} not present after POST")
        else:
            result.problems.append(
                f"label {label} not found in {s.owner}/{s.repo} or its organisation: a person creates it once "
                "(exclusive); organisation labels also need the token scope read:organization"
            )
    except GiteaError as exc:
        result.problems.append(f"label write failed, will retry next scan: {exc}")
    return result, ev


def _failed(s: SessionInfo, now: datetime, t: Thresholds, exc: Exception) -> ScanResult:
    """A session whose scan raised: reported as unknown (not recorded), so the other sessions are still scanned."""
    msg = JevMessage(
        kind=JevKind.UNKNOWN,
        scan_id=scan_slot(now, t.scan_interval_min),
        session_id=s.session_id,
        issue=s.issue,
        reasons=(Reason.UNOBSERVABLE,),
        idempotency_key=idempotency_key(s.session_id, None, "health.unknown:none"),
    )
    return ScanResult(msg, problems=[f"scan failed: {exc!r}"])


def _lock(db_path: Path) -> IO[str] | None:
    """One Jev scan at a time: overlapping runs would race on the same episode's comment."""
    path = db_path.with_suffix(".lock")
    path.parent.mkdir(parents=True, exist_ok=True)
    fh = path.open("a")
    try:
        fcntl.flock(fh, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except BlockingIOError:
        fh.close()
        return None
    return fh


def run_scan(
    root: Path,
    sessions: list[SessionInfo],
    gitea: GiteaClient,
    db_path: Path,
    now: datetime,
    t: Thresholds | None = None,
    dry_run: bool = False,
    explain: Explainer | None = None,
) -> dict:
    """Scan every session once. Raises ``PermissionError`` (Jev has too many rights) or ``GiteaError`` (start-up)."""
    t = t or Thresholds()
    now = as_utc(now)
    scan_id = scan_slot(now, t.scan_interval_min)
    lock = _lock(db_path)
    if lock is None:
        return {"scan_id": scan_id, "skipped": "another Jev scan holds the lock", "results": [], "failed": []}
    store = ScanStore(db_path)
    try:
        repos = {(s.owner, s.repo) for s in sessions}
        login = self_check(gitea, repos)  # raises PermissionError if Jev could push, merge or administer
        maps: LabelMaps = {}  # read on first use, inside each session's own error handling
        live = frozenset(s.session_id for s in sessions)
        out: list[ScanResult] = []
        evidence: list[Evidence] = []
        failed: list[str] = []
        for s in sessions:
            try:
                res, ev = scan_session(root, s, gitea, store, now, login, maps, t, dry_run, explain, live)
                evidence.append(ev)
            except Exception as exc:  # one session's failure must not blind Jev to the others
                res = _failed(s, now, t, exc)
                failed.append(s.session_id)
            out.append(res)
        ended, end_problems = _end_unsupervised(gitea, store, live, login, maps, now, scan_id, dry_run)
        notes = list(end_problems)
        observed = [e for e in evidence if e.observable and e.session.role == "pse" and e.session.branch is not None]
        if len(observed) > 1 and all(e.ci_never_reported for e in observed):
            notes.append("no session's CI has reported: the runner pool is likely down (one dependency alert, not N)")
        pruned = store.prune_intents(now)
        return {
            "scan_id": scan_id,
            "bot": login,
            "results": [
                {"message": json.loads(r.message.model_dump_json()), "actions": r.actions, "problems": r.problems}
                for r in out
            ],
            "failed": failed,
            "ended": ended,
            "notes": notes,
            "pruned_intents": pruned,
        }
    finally:
        store.close()
        lock.close()
