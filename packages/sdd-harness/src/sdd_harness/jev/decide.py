"""The pure verdict function. Plain code decides a session's health; a model never does (Art. III).

``decide(evidence, history, thresholds)`` has no I/O: it reads one scan's evidence and the session's earlier
scan records (newest first) and returns a verdict. Rules, from the Jev research report:

- **dead**: the lease heartbeat is older than its TTL. Lease expiry already frees the work; Jev tells the Lead.
- **hung**: no agent-loop event for ``hung_after_min``. The clock pauses while a tool call is still inside its own
  timeout, while the session waits on a person, and during start-up grace.
- **spinning**: the loop is alive but nothing durable (pushed commit, checkpoint, recorded state change) happened in
  ``progress_window_min``. Paused while the session waits on a person and during start-up grace.
- **loops**: identical action+error 3 times warns, 4 is stuck; identical action+observation 4 is stuck;
  A/B alternation of 6 is stuck; 3 consecutive command timeouts are stuck. Evidence counts these only when new
  calls completed since the last observed scan, so one streak is never counted twice.
- **CI**: 3 consecutive head commits with a completed, non-cancelled failure. A red push does not reset the chain.
- **failing commands**: supporting only — counts toward a bad scan when the scan shows no durable progress.
- **waiting on a person** pauses the stall clocks and the loop and CI rules.
- **debounce**: one bad scan warns (and nudges); two consecutive bad scans mean stuck. Only a scan with durable
  progress breaks the chain or closes an episode; an unobservable scan is ``unknown`` and changes nothing.
- **incarnation**: only scans since the session (re)started count; a restart begins a new episode history.
- **stopped**: once a stop was requested, a released lease with a checkpoint (or the Lead's acknowledgement) written
  after the request means the session stopped; that wins over whatever the current signals say.
"""

from __future__ import annotations

from datetime import UTC, datetime, timedelta

from .models import Evidence, JevKind, NextAction, Reason, ScanRecord, Thresholds, Verdict

BAD = frozenset({JevKind.WARN, JevKind.STUCK, JevKind.STOP})
STOP_ACTIONS = frozenset({NextAction.REQUEST_STOP, NextAction.HARD_STOP})


def _minutes(delta: timedelta) -> float:
    return delta.total_seconds() / 60


def consecutive_bad_scans(history: list[ScanRecord], lookback: int) -> int:
    """Consecutive non-healthy scans among the last ``lookback`` observed scans, newest first.

    ``unknown`` scans observed nothing: they are skipped and do not use up the lookback. An ``ok`` scan breaks the
    chain only if it saw durable progress; a chatty ``ok`` without durable progress neither counts nor resets, so a
    looping session cannot reset its own counter.
    """
    count = 0
    observed = [r for r in history if r.kind is not JevKind.UNKNOWN][:lookback]
    for rec in observed:
        if rec.kind in BAD:
            count += 1
        elif rec.durable_progress:
            break
    return count


def open_episode(history: list[ScanRecord], hold: int) -> str | None:
    """The episode a new bad scan should join: the latest one, unless more than ``hold`` recovered scans followed it.

    A recovered scan is an ``ok`` scan with durable progress — the same definition that breaks the debounce chain.
    """
    recovered = 0
    for rec in history:
        if rec.kind is JevKind.UNKNOWN:
            continue
        if rec.kind in BAD and rec.episode_id:
            return rec.episode_id
        if rec.kind is JevKind.OK and rec.durable_progress:
            recovered += 1
            if recovered > hold:
                return None
    return None


def _episode_records(history: list[ScanRecord], episode_id: str) -> list[ScanRecord]:
    return [r for r in history if r.episode_id == episode_id]


def _new_episode(ev: Evidence, t: Thresholds) -> str:
    """Named after the scan slot, so a retried scan in the same slot mints the same id."""
    return f"{ev.session.session_id}@{scan_slot(ev.now, t.scan_interval_min)}"


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
    if s.waiting_on_human:
        facts.append("waiting on a person: stall clocks and loop and CI rules paused")
    elif in_startup:
        facts.append("start-up grace: no agent-loop event yet")
    elif in_flight:
        facts.append("a tool call is still inside its own timeout: hung clock paused")

    last_loop = ev.last_loop_event_at or s.started_at
    hung = not (s.waiting_on_human or in_startup or in_flight) and _minutes(now - last_loop) >= t.hung_after_min
    if hung:
        reasons.append(Reason.HUNG)
        facts.append(f"no agent-loop event for {_minutes(now - last_loop):.0f} min")

    last_progress = ev.last_durable_progress_at or s.started_at
    spinning_paused = s.waiting_on_human or in_startup
    if not spinning_paused and not hung and _minutes(now - last_progress) >= t.progress_window_min:
        reasons.append(Reason.SPINNING)
        facts.append(f"no durable progress for {_minutes(now - last_progress):.0f} min")

    if s.waiting_on_human:
        return reasons, immediate, facts

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


def _stopped(ev: Evidence, prior: list[ScanRecord]) -> str | None:
    """Why the session counts as stopped after a stop request in this episode, or ``None``."""
    requests = [r.at for r in prior if r.next_action in STOP_ACTIONS]
    s = ev.session
    if not requests or not s.lease.released:
        return None
    requested_at = min(requests)
    if ev.checkpoint_at is not None and ev.checkpoint_at >= requested_at:
        return "stopped cleanly: checkpoint written after the stop request and lease released"
    if s.lead_ack_at is not None and s.lead_ack_at >= requested_at:
        return "stopped by the Lead after the stop request: lease released (no checkpoint)"
    return None


def _escalation(ev: Evidence, t: Thresholds, prior: list[ScanRecord]) -> NextAction | None:
    """Park on repeated restarts; page a person (L2) when the Lead stays silent or the episode stays unresolved."""
    s = ev.session
    if s.restarts >= t.restarts_to_park:
        return NextAction.PARK
    stuck = [r for r in prior if r.kind in (JevKind.STUCK, JevKind.STOP)]
    if stuck:
        first_stuck_at = min(r.at for r in stuck)
        lead_silent = s.lead_ack_at is None or s.lead_ack_at < first_stuck_at
        if (lead_silent and len(stuck) >= t.lead_ack_scans) or len(stuck) >= t.page_after_scans:
            return NextAction.PAGE_PERSON
    return None


def _ladder(ev: Evidence, t: Thresholds, prior: list[ScanRecord]) -> NextAction:
    """Where a stuck episode stands: request stop → (grace) hard stop → page a person; park on restarts."""
    escalated = _escalation(ev, t, prior)
    if escalated is not None:
        return escalated
    requests = [r.at for r in prior if r.next_action in STOP_ACTIONS]
    if requests:
        requested_at = min(requests)
        # Grace is counted in observed scans, not wall-clock minutes, so scheduler jitter cannot stretch it.
        scans_since = sum(1 for r in prior if r.at > requested_at and r.kind is not JevKind.UNKNOWN) + 1
        if scans_since >= t.stop_grace_scans:
            return NextAction.HARD_STOP  # the policy owner stops it; lease expiry is the backstop
    return NextAction.REQUEST_STOP  # checkpoint and release the lease; the Lead is told (L1)


def decide(ev: Evidence, history: list[ScanRecord], t: Thresholds | None = None) -> Verdict:
    t = t or Thresholds()
    # A restarted session is a new incarnation: earlier scans, episodes and stop requests are not its own.
    history = [r for r in history if r.at >= ev.session.started_at]
    current = open_episode(history, t.recovery_hold_scans)
    if not ev.observable:
        why = ev.unobservable_reason or "session could not be observed"
        return Verdict(JevKind.UNKNOWN, (Reason.UNOBSERVABLE,), NextAction.NONE, current, (why,))

    reasons, immediate, facts = _signals(ev, t)
    all_reasons = tuple(dict.fromkeys([*immediate, *reasons]))

    if current is not None and (why := _stopped(ev, _episode_records(history, current))):
        return Verdict(JevKind.STOP, all_reasons, NextAction.NOTIFY_LEAD, current, (*facts, why))

    if Reason.DEAD in immediate:
        episode = current or _new_episode(ev, t)
        action = _escalation(ev, t, _episode_records(history, episode)) or NextAction.NOTIFY_LEAD
        return Verdict(JevKind.STUCK, (Reason.DEAD,), action, episode, tuple(facts))

    if not all_reasons:
        return Verdict(JevKind.OK, (), NextAction.NONE, None, tuple(facts))

    # Durable progress starts a new chain, except a push whose CI is red: that is the CI rule's own evidence.
    resets = ev.durable_progress_since_last_scan and Reason.CI_NOT_CONVERGING not in reasons
    prior_bad = 0 if resets else consecutive_bad_scans(history, t.bad_scan_lookback)
    episode = current or _new_episode(ev, t)
    if immediate or prior_bad + 1 >= t.stuck_after_bad_scans:
        action = _ladder(ev, t, _episode_records(history, episode))
        return Verdict(JevKind.STUCK, all_reasons, action, episode, tuple(facts))
    return Verdict(JevKind.WARN, all_reasons, NextAction.NUDGE_SESSION, episode, tuple(facts))


def scan_slot(now: datetime, interval_min: int = 10) -> str:
    """Deterministic UTC scan id: the start of the scan interval, so a retried scan reuses its id."""
    now = now.replace(tzinfo=UTC) if now.tzinfo is None else now.astimezone(UTC)
    minute = (now.minute // interval_min) * interval_min
    return now.replace(minute=minute, second=0, microsecond=0).strftime("%Y-%m-%dT%H:%MZ")
