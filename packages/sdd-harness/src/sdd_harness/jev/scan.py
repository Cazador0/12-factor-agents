"""One Jev scan over the supervised sessions: collect → decide → record → (for warn, stuck, stop) comment and label.

Jev's write set is its own issue comments and its ``jev/*`` labels. It never edits code, pushes, approves or
merges; a stop is a request the session and the Lead carry out (Art. III). Healthy and unknown scans are recorded
locally only.
"""

from __future__ import annotations

import json
from collections.abc import Callable
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from .decide import decide, open_episode, scan_slot
from .gitea import GiteaClient, GiteaError, find_comment, label_ids, marker, self_check
from .models import (
    Evidence,
    JevKind,
    JevMessage,
    NextAction,
    ScanRecord,
    SessionInfo,
    Thresholds,
    idempotency_key,
)
from .signals import collect
from .store import ScanStore

LABEL_WARN, LABEL_STUCK, LABEL_PARKED = "jev/warning", "jev/stuck", "jev/parked"
JEV_LABELS = [LABEL_WARN, LABEL_STUCK, LABEL_PARKED]

Explainer = Callable[[JevMessage], str | None]

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


def _upsert_comment(
    gitea: GiteaClient,
    store: ScanStore,
    s: SessionInfo,
    msg: JevMessage,
    key: str,
    login: str,
    body: str,
    now: datetime,
) -> str:
    """One living comment per episode: find it by the stored id or the marker, then edit; post only if absent."""
    known = store.intent(key)
    comment_id = known[1] if known else None
    if comment_id is None:
        comment_id = find_comment(gitea, s.owner, s.repo, s.issue, key, login)  # crashed after POST last time
    store.mark_intent(key, s.session_id, s.issue, msg.episode_id or "-", "intended", comment_id, now)
    if comment_id is not None:
        gitea.edit_comment(s.owner, s.repo, comment_id, body)
        action = f"edited comment {comment_id}"
    else:
        comment_id = gitea.create_comment(s.owner, s.repo, s.issue, body)
        action = f"posted comment {comment_id}"
    store.mark_intent(key, s.session_id, s.issue, msg.episode_id or "-", "posted", comment_id, now)
    return action


def scan_session(
    root: Path,
    s: SessionInfo,
    gitea: GiteaClient,
    store: ScanStore,
    now: datetime,
    login: str,
    labels: dict[str, int],
    t: Thresholds,
    dry_run: bool = False,
    explain: Explainer | None = None,
) -> tuple[ScanResult, Evidence]:
    scan_id = scan_slot(now, t.scan_interval_min)
    history = store.history(s.session_id, before_scan=scan_id)
    ev = collect(root, s, gitea, now, history[0].at if history else None, t)
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
    store.record(msg, now, ev.durable_progress_since_last_scan)
    result = ScanResult(msg)

    if v.kind is JevKind.OK:
        _resolve_if_recovered(gitea, store, s, msg, history, login, labels, now, t, dry_run, result)
        return result, ev
    if v.kind is JevKind.UNKNOWN:
        return result, ev
    if s.issue is None:
        result.problems.append("no issue to comment on; verdict recorded locally only")
        return result, ev
    key = idempotency_key(s.session_id, v.episode_id, "episode")
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
            _upsert_comment(gitea, store, s, msg, key, login, render_comment(msg, key, explanation), now)
        )
        if label in labels:
            applied = gitea.add_labels(s.owner, s.repo, s.issue, [labels[label]])
            if labels[label] in applied:
                result.actions.append(f"label {label}")
            else:
                result.problems.append(f"label {label} not present after POST")
        else:
            result.problems.append(f"label {label} missing in {s.owner}/{s.repo}: a person creates it once (exclusive)")
    except GiteaError as exc:
        result.problems.append(f"Gitea write failed, will retry next scan: {exc}")
    return result, ev


def _resolve_if_recovered(gitea, store, s, msg, history, login, labels, now, t, dry_run, result) -> None:
    """When an ok scan closes an episode (past the recovery hold), clear Jev's labels and mark the comment resolved."""
    episode = open_episode(history, t.recovery_hold_scans)
    if episode is None or s.issue is None:
        return
    current = ScanRecord(s.session_id, msg.scan_id, now, JevKind.OK, (), NextAction.NONE, None, False)
    if open_episode([current, *history], t.recovery_hold_scans) is not None:
        return  # still inside the hold: a relapse would reuse the episode
    if dry_run:
        result.actions.append(f"would resolve episode {episode}")
        return
    try:
        for name in (LABEL_WARN, LABEL_STUCK):  # parked needs a person's reset
            if name in labels:
                gitea.remove_label(s.owner, s.repo, s.issue, labels[name])
        key = idempotency_key(s.session_id, episode, "episode")
        known = store.intent(key)
        if known and known[1]:
            gitea.edit_comment(s.owner, s.repo, known[1], render_comment(msg, key, resolved=True))
        result.actions.append(f"resolved episode {episode}")
    except GiteaError as exc:
        result.problems.append(f"could not clear labels for the resolved episode: {exc}")


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
    t = t or Thresholds()
    store = ScanStore(db_path)
    try:
        repos = {(s.owner, s.repo) for s in sessions}
        login = self_check(gitea, repos)  # raises PermissionError if Jev could push or merge
        maps = {r: label_ids(gitea, r[0], r[1], JEV_LABELS) for r in repos}
        out: list[ScanResult] = []
        evidence: list[Evidence] = []
        for s in sessions:
            res, ev = scan_session(root, s, gitea, store, now, login, maps[(s.owner, s.repo)], t, dry_run, explain)
            out.append(res)
            evidence.append(ev)
        notes = []
        observed = [e for e in evidence if e.observable]
        if len(observed) > 1 and all(e.ci_never_reported for e in observed):
            notes.append("no session's CI has reported: the runner pool is likely down (one dependency alert, not N)")
        pruned = store.prune_intents(now)
        return {
            "scan_id": scan_slot(now, t.scan_interval_min),
            "bot": login,
            "results": [
                {"message": json.loads(r.message.model_dump_json()), "actions": r.actions, "problems": r.problems}
                for r in out
            ],
            "notes": notes,
            "pruned_intents": pruned,
        }
    finally:
        store.close()
