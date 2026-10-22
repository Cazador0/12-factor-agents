"""The pure verdict function. Plain code decides a session's health; a model never does (Art. III).

``decide(evidence, history, thresholds)`` has no I/O: it reads one scan's evidence and the session's earlier
scan records (newest first) and returns a verdict. Rules, from the Jev research report:

- **dead**: the lease heartbeat is older than its TTL. Lease expiry already frees the work; Jev tells the Lead.
- **hung**: no agent-loop event for ``hung_after_min``. The clock pauses while a tool call is still inside its own
  timeout, while the session waits on a person, and during start-up grace.
- **spinning**: the loop is alive but nothing durable (pushed commit, checkpoint, recorded state change) happened in
  ``progress_window_min``.
- **loops**: identical action+error 3 times warns, 4 is stuck; identical action+observation 4 is stuck;
  A/B alternation of 6 is stuck; 3 consecutive command timeouts are stuck.
- **CI**: 3 consecutive head commits with a completed, non-cancelled failure.
- **failing commands**: supporting only — counts toward a bad scan when the scan shows no durable progress.
- **debounce**: one bad scan warns (and nudges); two consecutive bad scans mean stuck. Only a scan with durable
  progress breaks the chain; an unobservable scan is ``unknown`` and changes nothing.
"""

from __future__ import annotations

from datetime import datetime, timedelta

from .models import Evidence, JevKind, NextAction, Reason, ScanRecord, Thresholds, Verdict

BAD = frozenset({JevKind.WARN, JevKind.STUCK, JevKind.STOP})
IMMEDIATE = frozenset(
    {
        Reason.DEAD,
        Reason.LOOP_ACTION_ERROR,
        Reason.LOOP_ACTION_OBSERVATION,
        Reason.LOOP_ALTERNATION,
        Reason.COMMAND_TIMEOUTS,
    }
)


def _minutes(delta: timedelta) -> float:
    return delta.total_seconds() / 60


def consecutive_bad_scans(history: list[ScanRecord], lookback: int) -> int:
    """Consecutive non-healthy scans, newest first.

    ``unknown`` scans are skipped (they observed nothing). An ``ok`` scan breaks the chain only if it saw durable
    progress; a chatty ``ok`` without durable progress neither counts nor resets, so a looping session cannot reset
    its own counter.
    """
    count = 0
    for rec in history[:lookback]:
        if rec.kind is JevKind.UNKNOWN:
            continue
        if rec.kind in BAD:
            count += 1
        elif rec.durable_progress:
            break
    return count


def open_episode(history: list[ScanRecord], hold: int) -> str | None:
    """The episode a new bad scan should join: the latest one, if no more than ``hold`` ok scans followed it."""
    oks = 0
    for rec in history:
        if rec.kind is JevKind.UNKNOWN:
            continue
        if rec.kind in BAD and rec.episode_id:
            return rec.episode_id if oks <= hold else None
        if rec.kind is JevKind.OK:
            oks += 1
            if oks > hold:
                return None
    return None


def _episode_records(history: list[ScanRecord], episode_id: str) -> list[ScanRecord]:
    return [r for r in history if r.episode_id == episode_id]


def _signals(ev: Evidence, t: Thresholds) -> tuple[list[Reason], list[Reason], list[str]]:
    """(bad-scan reasons, immediately-stuck reasons, facts)."""
    reasons: list[Reason] = []
    immediate: list[Reason] = []
    facts: list[str] = list(ev.facts)
    s, now = ev.session, ev.now

    hb = s.lease.heartbeat_at
    if hb is not None and not s.lease.released and (now - hb).total_seconds() > s.lease.ttl_s:
        immediate.append(Reason.DEAD)
        facts.append(f"lease heartbeat {_minutes(now - hb):.0f} min old (TTL {s.lease.ttl_s // 60} min)")

    in_startup = (
        ev.last_loop_event_at is None and _minutes(now - s.started_at) < t.startup_grace_scans * t.scan_interval_min
    )
    in_flight = ev.in_flight_started_at is not None and (now - ev.in_flight_started_at).total_seconds() < (
        ev.in_flight_timeout_s or t.default_tool_timeout_s
    )
    paused = s.waiting_on_human or in_startup or in_flight
    if s.waiting_on_human:
        facts.append("waiting on a person: stall clocks paused")
    elif in_startup:
        facts.append("start-up grace: no agent-loop event yet")
    elif in_flight:
        facts.append("a tool call is still inside its own timeout: hung clock paused")

    last_loop = ev.last_loop_event_at or s.started_at
    hung = not paused and _minutes(now - last_loop) >= t.hung_after_min
    if hung:
        reasons.append(Reason.HUNG)
        facts.append(f"no agent-loop event for {_minutes(now - last_loop):.0f} min")

    last_progress = ev.last_durable_progress_at or s.started_at
    if not paused and not hung and _minutes(now - last_progress) >= t.progress_window_min:
        reasons.append(Reason.SPINNING)
        facts.append(f"no durable progress for {_minutes(now - last_progress):.0f} min")

    if ev.action_error_streak >= t.action_error_stuck:
        immediate.append(Reason.LOOP_ACTION_ERROR)
    elif ev.action_error_streak >= t.action_error_warn:
        reasons.append(Reason.LOOP_ACTION_ERROR)
    if ev.action_error_streak >= t.action_error_warn:
        facts.append(f"same call failed the same way {ev.action_error_streak} times in a row")
    if ev.action_observation_streak >= t.action_observation_stuck:
        immediate.append(Reason.LOOP_ACTION_OBSERVATION)
        facts.append(f"same call returned the same result {ev.action_observation_streak} times in a row")
    if ev.alternation_len >= t.alternation_stuck:
        immediate.append(Reason.LOOP_ALTERNATION)
        facts.append(f"two calls alternating for {ev.alternation_len} events")
    if ev.consecutive_timeouts >= t.command_timeouts_stuck:
        immediate.append(Reason.COMMAND_TIMEOUTS)
        facts.append(f"{ev.consecutive_timeouts} consecutive command timeouts")

    if ev.ci_failing_streak >= t.ci_failing_commits:
        reasons.append(Reason.CI_NOT_CONVERGING)
        facts.append(f"CI failed (not cancelled) on {ev.ci_failing_streak} consecutive head commits")

    if ev.failing_commands_in_scan >= t.failing_commands_supporting and not ev.durable_progress_since_last_scan:
        reasons.append(Reason.FAILING_COMMANDS)
        facts.append(f"{ev.failing_commands_in_scan} failing commands this scan and no durable progress")

    return reasons, immediate, facts


def _ladder(ev: Evidence, t: Thresholds, history: list[ScanRecord], episode_id: str) -> tuple[JevKind, NextAction]:
    """Where a stuck episode stands: request stop → (grace) hard stop or stopped → page a person; park on restarts."""
    s, now = ev.session, ev.now
    if s.restarts >= t.restarts_to_park:
        return JevKind.STUCK, NextAction.PARK
    prior = _episode_records(history, episode_id)  # newest first
    stuck_scans = [r for r in prior if r.kind in (JevKind.STUCK, JevKind.STOP)]
    stop_requests = [r for r in prior if r.next_action in (NextAction.REQUEST_STOP, NextAction.HARD_STOP)]
    requested_at = stop_requests[-1].at if stop_requests else None  # the first request in this episode
    # 1. Stopped cleanly: checkpoint written after the request and lease released → the Lead takes over.
    if (
        requested_at is not None
        and ev.checkpoint_at is not None
        and ev.checkpoint_at >= requested_at
        and s.lease.released
    ):
        return JevKind.STOP, NextAction.NOTIFY_LEAD
    # 2. L2: the Lead did not acknowledge within its window, or the episode stayed unresolved too long.
    if stuck_scans:
        first_stuck_at = stuck_scans[-1].at
        lead_silent = s.lead_ack_at is None or s.lead_ack_at < first_stuck_at
        if (lead_silent and len(stuck_scans) >= t.lead_ack_scans) or len(stuck_scans) >= t.page_after_scans:
            return JevKind.STUCK, NextAction.PAGE_PERSON
    # 3. Grace window over without a checkpoint: the policy owner stops it (lease expiry is the backstop).
    if requested_at is not None and _minutes(now - requested_at) >= t.stop_grace_scans * t.scan_interval_min:
        return JevKind.STUCK, NextAction.HARD_STOP
    # 4. First stuck verdict: ask the session to checkpoint and release its lease; the Lead is told (L1).
    return JevKind.STUCK, NextAction.REQUEST_STOP


def decide(ev: Evidence, history: list[ScanRecord], t: Thresholds | None = None) -> Verdict:
    t = t or Thresholds()
    if not ev.observable:
        why = ev.unobservable_reason or "session could not be observed"
        return Verdict(
            JevKind.UNKNOWN,
            (Reason.UNOBSERVABLE,),
            NextAction.NONE,
            open_episode(history, t.recovery_hold_scans),
            (why,),
        )

    reasons, immediate, facts = _signals(ev, t)
    if Reason.DEAD in immediate:
        episode = open_episode(history, t.recovery_hold_scans) or f"{ev.session.session_id}@{ev.now:%Y%m%dT%H%M}"
        return Verdict(JevKind.STUCK, (Reason.DEAD,), NextAction.NOTIFY_LEAD, episode, tuple(facts))

    all_reasons = tuple(dict.fromkeys([*immediate, *reasons]))
    if not all_reasons:
        return Verdict(JevKind.OK, (), NextAction.NONE, None, tuple(facts))

    prior_bad = 0 if ev.durable_progress_since_last_scan else consecutive_bad_scans(history, t.bad_scan_lookback)
    episode = open_episode(history, t.recovery_hold_scans) or f"{ev.session.session_id}@{ev.now:%Y%m%dT%H%M}"
    if immediate or prior_bad + 1 >= t.stuck_after_bad_scans:
        kind, action = _ladder(ev, t, history, episode)
        return Verdict(kind, all_reasons, action, episode, tuple(facts))
    return Verdict(JevKind.WARN, all_reasons, NextAction.NUDGE_SESSION, episode, tuple(facts))


def scan_slot(now: datetime, interval_min: int = 10) -> str:
    """Deterministic scan id: the start of the scan interval, so a retried scan reuses its id."""
    minute = (now.minute // interval_min) * interval_min
    return now.replace(minute=minute, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%MZ")
