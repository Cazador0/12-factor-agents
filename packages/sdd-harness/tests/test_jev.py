"""Jev: pure rules, CI semantics, the strict message contract, the store, the hook, and full scans on a fake Gitea."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta
from pathlib import Path

import pytest
from pydantic import ValidationError

from sdd_harness.jev import (
    CommitCI,
    Evidence,
    JevKind,
    JevMessage,
    Lease,
    NextAction,
    Reason,
    ScanRecord,
    ScanStore,
    SessionInfo,
    decide,
    idempotency_key,
    run_scan,
    scan_slot,
)
from sdd_harness.jev import schema as jev_schema
from sdd_harness.jev.gitea import GiteaError, combine, failing_contexts, marker
from sdd_harness.jev.signals import ci_failing_streak, in_flight, read_commands, trailing_alternation

T0 = datetime(2026, 10, 22, 10, 0, tzinfo=UTC)
REPO_ROOT = Path(__file__).resolve().parents[3]
HOOK = REPO_ROOT / ".claude" / "hooks" / "command_log.py"


def session(**kw) -> SessionInfo:
    base = dict(
        session_id="pse-184",
        role="pse",
        issue=184,
        owner="acme",
        repo="factory",
        branch="agent/pse/184-x",
        run_id="run-184",
        commands_log=".specify/sessions/commands/pse-184.jsonl",
        started_at=T0 - timedelta(hours=2),
    )
    return SessionInfo(**{**base, **kw})


def ev(minutes: int = 0, **kw) -> Evidence:
    now = T0 + timedelta(minutes=minutes)
    base = dict(
        session=session(),
        now=now,
        last_loop_event_at=now - timedelta(minutes=1),
        last_durable_progress_at=now - timedelta(minutes=5),
        durable_progress_since_last_scan=True,
    )
    return Evidence(**{**base, **kw})


def rec(minutes: int, kind: JevKind, action=NextAction.NONE, episode=None, durable=False, reasons=()) -> ScanRecord:
    at = T0 + timedelta(minutes=minutes)
    return ScanRecord("pse-184", scan_slot(at), at, kind, tuple(reasons), action, episode, durable)


# ---------------------------------------------------------------- decide(): the pure rules


def test_healthy_session_is_ok():
    assert decide(ev(), []).kind is JevKind.OK


def test_hung_after_twenty_minutes_of_silence():
    v = decide(ev(last_loop_event_at=T0 - timedelta(minutes=21), durable_progress_since_last_scan=False), [])
    assert v.kind is JevKind.WARN and Reason.HUNG in v.reasons and v.next_action is NextAction.NUDGE_SESSION


@pytest.mark.parametrize(
    "pause",
    [
        {"in_flight_started_at": T0 - timedelta(minutes=5), "in_flight_timeout_s": 3600},
        {"session": session(waiting_on_human=True)},
        {"session": session(started_at=T0 - timedelta(minutes=10)), "last_loop_event_at": None},
    ],
    ids=["tool-call-inside-its-timeout", "waiting-on-a-person", "start-up-grace"],
)
def test_hung_clock_pauses(pause):
    silent = {"last_loop_event_at": T0 - timedelta(minutes=40), "durable_progress_since_last_scan": False}
    v = decide(ev(**{**silent, **pause}), [])
    assert Reason.HUNG not in v.reasons


def test_in_flight_call_past_its_own_timeout_does_not_pause():
    v = decide(
        ev(
            last_loop_event_at=T0 - timedelta(minutes=40),
            in_flight_started_at=T0 - timedelta(minutes=30),
            in_flight_timeout_s=120,
            durable_progress_since_last_scan=False,
        ),
        [],
    )
    assert Reason.HUNG in v.reasons


def test_spinning_without_durable_progress_for_an_hour():
    v = decide(ev(last_durable_progress_at=T0 - timedelta(minutes=61), durable_progress_since_last_scan=False), [])
    assert Reason.SPINNING in v.reasons and v.kind is JevKind.WARN


def test_action_error_three_warns_four_is_stuck():
    assert decide(ev(action_error_streak=3), []).kind is JevKind.WARN
    v = decide(ev(action_error_streak=4), [])
    assert v.kind is JevKind.STUCK and v.next_action is NextAction.REQUEST_STOP


@pytest.mark.parametrize(
    "field,value", [("action_observation_streak", 4), ("alternation_len", 6), ("consecutive_timeouts", 3)]
)
def test_immediate_loop_rules(field, value):
    assert decide(ev(**{field: value}), []).kind is JevKind.STUCK


def test_failing_commands_only_support_a_bad_scan():
    assert decide(ev(failing_commands_in_scan=9), []).kind is JevKind.OK  # durable progress this scan
    v = decide(ev(failing_commands_in_scan=9, durable_progress_since_last_scan=False), [])
    assert Reason.FAILING_COMMANDS in v.reasons


def test_two_consecutive_bad_scans_mean_stuck():
    hung = dict(last_loop_event_at=T0 - timedelta(minutes=30), durable_progress_since_last_scan=False)
    first = decide(ev(**hung), [])
    assert first.kind is JevKind.WARN
    history = [rec(0, JevKind.WARN, NextAction.NUDGE_SESSION, first.episode_id)]
    second = decide(ev(10, **{**hung, "last_loop_event_at": T0 - timedelta(minutes=30)}), history)
    assert second.kind is JevKind.STUCK and second.episode_id == first.episode_id


def test_unknown_and_chatty_ok_scans_do_not_reset_the_chain():
    hung = dict(last_loop_event_at=T0 - timedelta(minutes=30), durable_progress_since_last_scan=False)
    history = [
        rec(20, JevKind.UNKNOWN),
        rec(10, JevKind.OK, durable=False),
        rec(0, JevKind.WARN, NextAction.NUDGE_SESSION, "e1"),
    ]
    assert decide(ev(30, **hung), history).kind is JevKind.STUCK
    history = [rec(10, JevKind.OK, durable=True), rec(0, JevKind.WARN, NextAction.NUDGE_SESSION, "e1")]
    assert decide(ev(20, **hung), history).kind is JevKind.WARN  # durable progress broke the chain


def test_unobservable_scan_is_unknown():
    v = decide(ev(observable=False, unobservable_reason="Gitea unavailable"), [])
    assert v.kind is JevKind.UNKNOWN and v.reasons == (Reason.UNOBSERVABLE,)


def test_dead_lease_tells_the_lead():
    s = session(lease=Lease(heartbeat_at=T0 - timedelta(minutes=45), ttl_s=1800))
    v = decide(ev(session=s), [])
    assert v.kind is JevKind.STUCK and v.reasons == (Reason.DEAD,) and v.next_action is NextAction.NOTIFY_LEAD


def test_stop_ladder_request_then_hard_stop_then_stopped():
    stuck = dict(action_error_streak=4)
    h1 = [rec(0, JevKind.STUCK, NextAction.REQUEST_STOP, "e1")]
    lead_acked = session(lead_ack_at=T0 + timedelta(minutes=1))
    v = decide(ev(10, session=lead_acked, **stuck), h1)
    assert v.next_action is NextAction.HARD_STOP  # grace (one scan) passed without a checkpoint
    done = session(lead_ack_at=T0 + timedelta(minutes=1), lease=Lease(released=True))
    v = decide(ev(10, session=done, checkpoint_at=T0 + timedelta(minutes=8), **stuck), h1)
    assert v.kind is JevKind.STOP and v.next_action is NextAction.NOTIFY_LEAD


def test_silent_lead_pages_a_person_and_restarts_park():
    h1 = [rec(0, JevKind.STUCK, NextAction.REQUEST_STOP, "e1")]
    assert decide(ev(10, action_error_streak=4), h1).next_action is NextAction.PAGE_PERSON
    assert decide(ev(action_error_streak=4, session=session(restarts=2)), []).next_action is NextAction.PARK


def test_relapse_inside_recovery_hold_reuses_the_episode():
    history = [rec(10, JevKind.OK, durable=True), rec(0, JevKind.WARN, NextAction.NUDGE_SESSION, "e1")]
    assert decide(ev(20, action_error_streak=3), history).episode_id == "e1"
    history = [rec(20, JevKind.OK, durable=True), *history]
    assert decide(ev(30, action_error_streak=3), history).episode_id != "e1"


def test_scan_slot_is_deterministic():
    assert scan_slot(T0 + timedelta(minutes=17, seconds=40)) == "2026-10-22T10:10Z"


# ---------------------------------------------------------------- CI and Gitea semantics


def test_ci_streak_ignores_cancelled_none_and_shrinking_failures():
    f = lambda sha, *ctx: CommitCI(sha, "failure", frozenset(ctx))  # noqa: E731
    assert ci_failing_streak([f("c", "a"), f("b", "a"), f("a", "a")]) == 3
    assert (
        ci_failing_streak([f("c", "a"), CommitCI("x", "cancelled"), CommitCI("y", "none"), f("b", "a"), f("a", "a")])
        == 3
    )
    assert ci_failing_streak([f("c", "a"), CommitCI("s", "success"), f("b", "a")]) == 1
    assert ci_failing_streak([f("c", "a"), f("b", "a", "b"), f("a", "a", "b")]) == 2  # c is converging


def test_combine_uses_latest_status_per_context_and_both_keys():
    statuses = [
        {"context": "ci", "status": "success"},
        {"context": "ci", "status": "failure"},
        {"context": "lint", "state": "skipped"},
    ]
    assert combine(statuses) == "success"
    assert combine([{"context": "ci", "status": "warning"}]) == "failure"
    assert combine([]) == "none"
    assert failing_contexts([{"context": "ci", "status": "error"}, {"context": "x", "status": "success"}]) == {"ci"}


# ---------------------------------------------------------------- the message contract


def test_message_is_strict_frozen_and_closed():
    key = idempotency_key("s", "e", "health.warn:nudge_session")
    msg = JevMessage(kind=JevKind.WARN, scan_id="2026-10-22T10:00Z", session_id="s", issue=3, idempotency_key=key)
    with pytest.raises(ValidationError):
        msg.model_copy(update={}).__class__(**{**msg.model_dump(), "extra": 1})
    with pytest.raises(ValidationError):
        JevMessage(
            kind=JevKind.WARN, scan_id="x", session_id="s", issue="3", idempotency_key=key
        )  # strict: no coercion
    with pytest.raises(ValidationError):
        JevMessage(kind=JevKind.WARN, scan_id="x", session_id="s", idempotency_key="nope")
    with pytest.raises(ValidationError):
        msg.kind = JevKind.OK  # type: ignore[misc]
    assert JevMessage.model_validate_json(msg.model_dump_json()) == msg
    assert idempotency_key("s", "e", "x") == idempotency_key("s", "e", "x")


def test_exported_schema_is_current():
    assert jev_schema.is_current(REPO_ROOT), "run: bin/sdd-jev schema (or uv run sdd-jev --root . schema)"
    props = json.loads((REPO_ROOT / jev_schema.SCHEMA_REL).read_text())["properties"]
    assert set(props) >= {
        "schema_version",
        "kind",
        "scan_id",
        "session_id",
        "issue",
        "reasons",
        "next_action",
        "idempotency_key",
    }


# ---------------------------------------------------------------- store


def test_store_counts_consecutive_non_healthy_scans(tmp_path):
    store = ScanStore(tmp_path / "jev.sqlite")
    key = idempotency_key("pse-184", "e", "x")
    for minutes, kind, durable in [
        (0, JevKind.OK, True),
        (10, JevKind.WARN, False),
        (20, JevKind.UNKNOWN, False),
        (30, JevKind.STUCK, False),
    ]:
        at = T0 + timedelta(minutes=minutes)
        store.record(
            JevMessage(kind=kind, scan_id=scan_slot(at), session_id="pse-184", idempotency_key=key), at, durable
        )
    assert store.consecutive_non_healthy("pse-184") == 2
    store.record(
        JevMessage(
            kind=JevKind.STUCK, scan_id=scan_slot(T0 + timedelta(minutes=30)), session_id="pse-184", idempotency_key=key
        ),
        T0 + timedelta(minutes=30),
        False,
    )
    assert len(store.history("pse-184")) == 4  # same slot overwrote itself
    store.close()


# ---------------------------------------------------------------- the command-log hook


def run_hook(root: Path, payload: dict) -> None:
    subprocess.run(
        [sys.executable, str(HOOK)],
        input=json.dumps(payload),
        text=True,
        check=True,
        env={"CLAUDE_PROJECT_DIR": str(root), "PATH": "/usr/bin:/bin"},
    )


def test_hook_logs_start_end_and_failures(tmp_path):
    base = {"session_id": "cc-1", "tool_name": "Bash", "tool_input": {"command": "pytest -q", "timeout": 300000}}
    run_hook(tmp_path, {**base, "hook_event_name": "PreToolUse", "tool_use_id": "t1"})
    run_hook(
        tmp_path,
        {
            **base,
            "hook_event_name": "PostToolUseFailure",
            "tool_use_id": "t1",
            "error": "Exit code 2\nFAILED\nCommand timed out after 2m 0s",
        },
    )
    run_hook(tmp_path, {**base, "hook_event_name": "PreToolUse", "tool_use_id": "t2"})
    events = read_commands(tmp_path / ".specify/sessions/commands/cc-1.jsonl")
    assert [e.event for e in events] == ["start", "end", "start"]
    end = events[1]
    assert end.exit_code == 2 and not end.ok and end.timed_out and end.outcome.startswith("err:")
    assert events[0].timeout_s == 300
    flying = in_flight(events)
    assert flying is not None and flying.tool_use_id == "t2"


def test_hook_stores_hashes_never_command_or_file_text(tmp_path):
    secret = "ghp_s3cretTOKENvalue"
    run_hook(
        tmp_path,
        {
            "session_id": "cc-2",
            "hook_event_name": "PreToolUse",
            "tool_name": "Bash",
            "tool_input": {"command": f"GITEA_TOKEN={secret} curl -H 'Authorization: token {secret}' x"},
        },
    )
    run_hook(
        tmp_path,
        {
            "session_id": "cc-2",
            "hook_event_name": "PreToolUse",
            "tool_name": "Edit",
            "tool_input": {"file_path": "a.py", "old_string": "x", "new_string": f"KEY = '{secret}'"},
        },
    )
    path = tmp_path / ".specify/sessions/commands/cc-2.jsonl"
    assert secret not in path.read_text()
    assert path.stat().st_mode & 0o777 == 0o600
    first, second = read_commands(path)
    assert first.action.startswith("sha:") and first.action != second.action


def test_alternation_detects_two_state_cycles(tmp_path):
    log = tmp_path / "c.jsonl"
    rows = [
        {
            "event": "end",
            "at": (T0 + timedelta(seconds=i)).isoformat(),
            "tool": "Bash",
            "action": "a" if i % 2 else "b",
            "exit_code": 1,
            "ok": False,
            "outcome": "err:x",
        }
        for i in range(6)
    ]
    log.write_text("\n".join(json.dumps(r) for r in rows))
    assert trailing_alternation([e for e in read_commands(log) if e.event == "end"]) == 6


# ---------------------------------------------------------------- full scans on a fake Gitea


class FakeGitea:
    def __init__(self, can_push=False):
        self.login = "jev-bot"
        self.can_push = can_push
        self.commits: dict[str, list[dict]] = {}
        self.statuses: dict[str, list[dict]] = {}
        self.runs: dict[str, list[dict]] = {}
        self.comments: dict[int, list[dict]] = {}
        self.labels = [
            {"id": 41, "name": "jev/warning"},
            {"id": 42, "name": "jev/stuck"},
            {"id": 43, "name": "jev/parked"},
        ]
        self.issue_labels: dict[int, set[int]] = {}
        self.fail_reads = False
        self.posts = 0

    def me(self):
        return self.login

    def version(self):
        return "28.2.0"

    def default_branch(self, owner, repo):
        return "main"

    def branch_rights(self, owner, repo, branch):
        return (self.can_push, False)

    def branch_commits(self, owner, repo, branch, limit):
        if self.fail_reads:
            raise GiteaError("HTTP 503")
        return self.commits.get(branch, [])[:limit]

    def commit_statuses(self, owner, repo, sha):
        return self.statuses.get(sha, [])

    def runs_for_commit(self, owner, repo, sha):
        return self.runs.get(sha, [])

    def list_comments(self, owner, repo, issue):
        return list(self.comments.get(issue, []))

    def create_comment(self, owner, repo, issue, body):
        self.posts += 1
        cid = 1000 + self.posts
        self.comments.setdefault(issue, []).append({"id": cid, "body": body, "user": {"login": self.login}})
        return cid

    def edit_comment(self, owner, repo, comment_id, body):
        for cs in self.comments.values():
            for c in cs:
                if c["id"] == comment_id:
                    c["body"] = body

    def repo_labels(self, owner, repo):
        return self.labels

    def add_labels(self, owner, repo, issue, label_ids):
        have = self.issue_labels.setdefault(issue, set())
        for lid in label_ids:  # jev/* labels are exclusive within their scope
            have -= {41, 42, 43}
            have.add(lid)
        return sorted(have)

    def remove_label(self, owner, repo, issue, label_id):
        self.issue_labels.get(issue, set()).discard(label_id)


def write_log(root: Path, rows: list[dict]) -> None:
    path = root / ".specify/sessions/commands/pse-184.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(r) + "\n" for r in rows))


def failing_loop(at: datetime, n: int = 4) -> list[dict]:
    return [
        {
            "event": "end",
            "at": (at - timedelta(seconds=n - i)).isoformat(),
            "tool": "Bash",
            "action": "pytest -q",
            "exit_code": 1,
            "ok": False,
            "outcome": "err:same",
        }
        for i in range(n)
    ]


def test_scan_posts_one_living_comment_per_episode(tmp_path):
    g = FakeGitea()
    db = tmp_path / "jev.sqlite"
    s = session(started_at=T0 - timedelta(hours=3))
    quiet = T0 - timedelta(minutes=30)
    write_log(
        tmp_path,
        [
            {
                "event": "end",
                "at": quiet.isoformat(),
                "tool": "Bash",
                "action": "ls",
                "exit_code": 0,
                "ok": True,
                "outcome": "ok:a",
            }
        ],
    )
    r1 = run_scan(tmp_path, [s], g, db, T0)
    m1 = r1["results"][0]["message"]
    assert m1["kind"] == "health.warn" and Reason.HUNG.value in m1["reasons"]
    assert g.posts == 1 and g.issue_labels[184] == {41}
    r2 = run_scan(tmp_path, [s], g, db, T0 + timedelta(minutes=10))
    m2 = r2["results"][0]["message"]
    assert m2["kind"] == "health.stuck" and m2["next_action"] == "request_stop" and m2["episode_id"] == m1["episode_id"]
    assert g.posts == 1 and len(g.comments[184]) == 1, "the episode comment is edited in place, not re-posted"
    assert g.issue_labels[184] == {42}
    body = g.comments[184][0]["body"]
    assert marker(idempotency_key("pse-184", m1["episode_id"], "episode")) in body and "```json" in body


def test_crash_after_post_does_not_duplicate_the_comment(tmp_path):
    g = FakeGitea()
    s = session()
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [s], g, tmp_path / "a.sqlite", T0)
    assert g.posts == 1
    run_scan(tmp_path, [s], g, tmp_path / "fresh.sqlite", T0)  # lost local state: finds its comment by marker
    assert g.posts == 1 and len(g.comments[184]) == 1


def test_healthy_and_unknown_scans_stay_local(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(minutes=30))
    write_log(
        tmp_path,
        [
            {
                "event": "end",
                "at": (T0 - timedelta(minutes=1)).isoformat(),
                "tool": "Bash",
                "action": "pytest",
                "exit_code": 0,
                "ok": True,
                "outcome": "ok:1",
            }
        ],
    )
    assert run_scan(tmp_path, [s], g, tmp_path / "j.sqlite", T0)["results"][0]["message"]["kind"] == "health.ok"
    g.fail_reads = True
    r = run_scan(tmp_path, [s], g, tmp_path / "j.sqlite", T0 + timedelta(minutes=10))
    assert r["results"][0]["message"]["kind"] == "health.unknown"
    assert g.posts == 0 and not g.issue_labels


def test_refuses_to_run_with_push_rights(tmp_path):
    with pytest.raises(PermissionError):
        run_scan(tmp_path, [session()], FakeGitea(can_push=True), tmp_path / "j.sqlite", T0)


def test_dry_run_and_missing_labels(tmp_path):
    g = FakeGitea()
    write_log(tmp_path, failing_loop(T0, 4))
    r = run_scan(tmp_path, [session()], g, tmp_path / "j.sqlite", T0, dry_run=True)
    assert r["results"][0]["actions"] and g.posts == 0
    g.labels = []
    r = run_scan(tmp_path, [session()], g, tmp_path / "k.sqlite", T0)
    assert any("missing" in p for p in r["results"][0]["problems"]) and g.posts == 1


def test_episode_resolution_clears_labels(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [s], g, db, T0)
    assert g.issue_labels[184] == {41}
    for i, minutes in enumerate((10, 20)):
        at = T0 + timedelta(minutes=minutes)
        g.commits[s.branch] = [{"sha": f"s{i}", "created": (at - timedelta(minutes=1)).isoformat()}]
        write_log(
            tmp_path,
            [
                {
                    "event": "end",
                    "at": (at - timedelta(minutes=1)).isoformat(),
                    "tool": "Bash",
                    "action": f"step {i}",
                    "exit_code": 0,
                    "ok": True,
                    "outcome": f"ok:{i}",
                }
            ],
        )
        run_scan(tmp_path, [s], g, db, at)
    assert g.issue_labels[184] == set()
    assert "resolved" in g.comments[184][0]["body"]


def test_shared_runner_outage_is_one_note(tmp_path):
    g = FakeGitea()
    a, b = session(), session(session_id="pse-185", issue=185, branch="agent/pse/185-y", commands_log=None)
    for br in (a.branch, b.branch):
        g.commits[br] = [{"sha": br + "1", "created": T0.isoformat()}]
    write_log(
        tmp_path,
        [
            {
                "event": "end",
                "at": T0.isoformat(),
                "tool": "Bash",
                "action": "x",
                "exit_code": 0,
                "ok": True,
                "outcome": "ok:x",
            }
        ],
    )
    r = run_scan(tmp_path, [a, b], g, tmp_path / "j.sqlite", T0)
    assert any("runner pool" in n for n in r["notes"])
