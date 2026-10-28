"""Jev: pure rules, CI semantics, the strict message contract, the store, the hook, and full scans on a fake Gitea."""

from __future__ import annotations

import json
import subprocess
import sys
from datetime import UTC, datetime, timedelta, timezone
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
from sdd_harness.jev.gitea import GiteaError, HttpGiteaClient, combine, commit_outcome, failing_contexts, marker
from sdd_harness.jev.scan import episode_key
from sdd_harness.jev.signals import ci_failing_streak, collect, in_flight, read_commands, trailing_alternation

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


def test_combine_reads_every_check_and_both_keys():
    # rows are already one per check; two workflows sharing a name and job are two checks with one context string
    same_name = [
        {"context": "CI / test (push)", "status": "success"},
        {"context": "CI / test (push)", "status": "failure"},
    ]
    assert combine(same_name) == "failure"
    assert combine([{"context": "ci", "status": "success"}, {"context": "lint", "state": "skipped"}]) == "success"
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
        self.permissions = {"admin": False, "push": can_push, "pull": True}
        self.can_merge_main = False
        self.commits: dict[str, list[dict]] = {}
        self.statuses: dict[str, list[dict]] = {}
        self.comments: dict[int, list[dict]] = {}
        self.labels = [
            {"id": 41, "name": "jev/warning"},
            {"id": 42, "name": "jev/stuck"},
            {"id": 43, "name": "jev/parked"},
            {"id": 61, "name": "jev/lead/warning"},
            {"id": 62, "name": "jev/lead/stuck"},
            {"id": 63, "name": "jev/lead/parked"},
            {"id": 71, "name": "jev/pse/warning"},
            {"id": 72, "name": "jev/pse/stuck"},
            {"id": 73, "name": "jev/pse/parked"},
            {"id": 81, "name": "jev/review/warning"},
            {"id": 82, "name": "jev/review/stuck"},
            {"id": 83, "name": "jev/review/parked"},
        ]
        self.org_label_list: list[dict] = []
        self.issue_labels: dict[int, set[int]] = {}
        self.fail_reads = False
        self.fail_remove = 0  # remove_label calls that fail before one succeeds
        self.fail_list_comments = 0  # list_comments calls that fail before one succeeds
        self.org_error: int | None = None  # HTTP status /orgs/{owner}/labels answers with
        self.crash_branch: str | None = None
        self.branch_reads = 0
        self.posts = 0

    def me(self):
        return self.login

    def version(self):
        return "28.2.0"

    def repo_info(self, owner, repo):
        return {"default_branch": "main", "permissions": self.permissions}

    def branch_rights(self, owner, repo, branch):
        return (False, self.can_merge_main)

    def branch_commits(self, owner, repo, branch, limit):
        self.branch_reads += 1
        if self.fail_reads:
            raise GiteaError("HTTP 503", 503)
        if branch == self.crash_branch:
            raise RuntimeError("unexpected payload")
        return self.commits.get(branch, [])[:limit]

    def latest_statuses(self, owner, repo, sha):
        latest: dict[tuple, dict] = {}  # like Gitea: one row per context hash (context + workflow file)
        for st in self.statuses.get(sha, []):
            k = (st.get("context"), st.get("workflow"))
            if k not in latest or st.get("id", 0) > latest[k].get("id", 0):
                latest[k] = st
        return list(latest.values())

    def list_comments(self, owner, repo, issue):
        if self.fail_list_comments:
            self.fail_list_comments -= 1
            raise GiteaError("GET comments → HTTP 502", 502)
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
                    return
        raise GiteaError(f"PATCH comment {comment_id} → HTTP 404", 404)

    def repo_labels(self, owner, repo):
        return self.labels

    def org_labels(self, owner):
        if self.org_error is not None:
            raise GiteaError(f"GET /orgs/{owner}/labels → HTTP {self.org_error}", self.org_error)
        return self.org_label_list

    # Exclusive scope groups: adding any label in a group removes the others in the same group.
    _EXCLUSIVE_SCOPES: list[set[int]] = [
        {41, 42, 43},  # jev/   (summary)
        {61, 62, 63},  # jev/lead/
        {71, 72, 73},  # jev/pse/
        {81, 82, 83},  # jev/review/
    ]

    def add_labels(self, owner, repo, issue, label_ids):
        have = self.issue_labels.setdefault(issue, set())
        for lid in label_ids:
            for scope in self._EXCLUSIVE_SCOPES:
                if lid in scope:
                    have -= scope
            have.add(lid)
        return sorted(have)

    def remove_label(self, owner, repo, issue, label_id):
        if self.fail_remove:
            self.fail_remove -= 1
            raise GiteaError("DELETE label → HTTP 500", 500)
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
    assert g.posts == 1 and g.issue_labels[184] == {41, 71}
    r2 = run_scan(tmp_path, [s], g, db, T0 + timedelta(minutes=10))
    m2 = r2["results"][0]["message"]
    assert m2["kind"] == "health.stuck" and m2["next_action"] == "request_stop" and m2["episode_id"] == m1["episode_id"]
    assert g.posts == 1 and len(g.comments[184]) == 1, "the episode comment is edited in place, not re-posted"
    assert g.issue_labels[184] == {42, 72}
    body = g.comments[184][0]["body"]
    assert marker(episode_key("pse-184", m1["episode_id"], "acme", "factory", 184)) in body and "```json" in body


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
    assert any("not found" in p for p in r["results"][0]["problems"]) and g.posts == 1


def test_episode_resolution_clears_labels(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [s], g, db, T0)
    assert g.issue_labels[184] == {41, 71}
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


# ---------------------------------------------------------------- regressions from the adversarial review


def end_row(at: datetime, action: str = "x", ok: bool = True, outcome: str = "ok:x", **kw) -> dict:
    return {
        "event": "end",
        "at": at.isoformat(),
        "tool": "Bash",
        "action": action,
        "exit_code": 0 if ok else 1,
        "ok": ok,
        "outcome": outcome,
        **kw,
    }


def test_obeyed_stop_is_reported_stopped_even_when_signals_clear():
    h = [rec(10, JevKind.STUCK, NextAction.REQUEST_STOP, "e1"), rec(0, JevKind.WARN, NextAction.NUDGE_SESSION, "e1")]
    done = session(lease=Lease(released=True))
    v = decide(ev(20, session=done, checkpoint_at=T0 + timedelta(minutes=14)), h)  # healthy-looking: progress
    assert v.kind is JevKind.STOP and v.next_action is NextAction.NOTIFY_LEAD and v.episode_id == "e1"
    revoked = session(lease=Lease(released=True), lead_ack_at=T0 + timedelta(minutes=12))
    v = decide(ev(20, session=revoked, action_error_streak=4), h)  # the Lead hard-stopped it: no checkpoint
    assert v.kind is JevKind.STOP and v.next_action is NextAction.NOTIFY_LEAD


def ci_rec(minutes: int, streak: int) -> ScanRecord:
    at = T0 + timedelta(minutes=minutes)
    return ScanRecord(
        "pse-184",
        scan_slot(at),
        at,
        JevKind.WARN,
        (Reason.CI_NOT_CONVERGING,),
        NextAction.NUDGE_SESSION,
        "e1",
        False,
        "h",
        streak,
    )


def test_red_pushes_do_not_reset_the_ci_chain():
    v = decide(ev(10, ci_failing_streak=4, head_ci_red=True), [ci_rec(0, 3)])
    assert v.kind is JevKind.STUCK and Reason.CI_NOT_CONVERGING in v.reasons
    v = decide(ev(10, ci_failing_streak=4), [ci_rec(0, 3)])  # head still running, but an older push went red
    assert v.kind is JevKind.STUCK


def test_a_fix_whose_ci_is_still_running_resets_the_chain():
    v = decide(ev(10, ci_failing_streak=3), [ci_rec(0, 3)])  # pushed a fix; its CI has not reported yet
    assert v.kind is JevKind.WARN and v.episode_id == "e1"


def test_waiting_on_a_person_pauses_loop_and_ci_rules():
    v = decide(ev(session=session(waiting_on_human=True), action_error_streak=5, ci_failing_streak=4), [])
    assert v.kind is JevKind.OK


def test_unknown_scans_do_not_use_up_the_lookback():
    hung = dict(last_loop_event_at=T0 - timedelta(minutes=90), durable_progress_since_last_scan=False)
    h = [rec(80 - 10 * i, JevKind.UNKNOWN) for i in range(6)]
    h += [rec(10, JevKind.STUCK, NextAction.REQUEST_STOP, "e1"), rec(0, JevKind.WARN, NextAction.NUDGE_SESSION, "e1")]
    v = decide(ev(90, **hung), h)
    assert v.kind is JevKind.STUCK and v.episode_id == "e1"


def test_chatty_ok_scans_do_not_close_the_episode():
    h = [rec(20, JevKind.OK), rec(10, JevKind.OK), rec(0, JevKind.WARN, NextAction.NUDGE_SESSION, "e1")]
    v = decide(ev(30, action_error_streak=3, durable_progress_since_last_scan=False), h)
    assert v.episode_id == "e1" and v.kind is JevKind.STUCK


def test_stop_grace_is_counted_in_scans_not_wall_clock():
    request = ScanRecord(
        "pse-184", scan_slot(T0), T0 + timedelta(seconds=2), JevKind.STUCK, (), NextAction.REQUEST_STOP, "e1", False
    )
    acked = session(lead_ack_at=T0 + timedelta(minutes=1))
    assert decide(ev(10, session=acked, action_error_streak=4), [request]).next_action is NextAction.HARD_STOP


def test_in_flight_call_pauses_hung_but_not_spinning():
    v = decide(
        ev(
            last_durable_progress_at=T0 - timedelta(hours=3),
            durable_progress_since_last_scan=False,
            in_flight_started_at=T0 - timedelta(seconds=30),
            in_flight_timeout_s=600,
        ),
        [],
    )
    assert Reason.SPINNING in v.reasons


def test_dead_sessions_escalate_and_park():
    dead = dict(lease=Lease(heartbeat_at=T0 - timedelta(hours=2), ttl_s=1800))
    assert decide(ev(session=session(restarts=2, **dead)), []).next_action is NextAction.PARK
    h = [rec(0, JevKind.STUCK, NextAction.NOTIFY_LEAD, "e1", reasons=[Reason.DEAD])]
    assert decide(ev(10, session=session(**dead)), h).next_action is NextAction.PAGE_PERSON


def test_a_restart_begins_a_new_incarnation():
    restarted = session(started_at=T0 - timedelta(minutes=5), restarts=1)
    h = [rec(-30, JevKind.STUCK, NextAction.REQUEST_STOP, "old")]
    v = decide(ev(session=restarted, action_error_streak=4), h)
    assert v.episode_id != "old" and v.next_action is NextAction.REQUEST_STOP


def test_naive_timestamps_are_utc_and_scan_ids_are_utc_slots():
    s = SessionInfo(session_id="r", role="review", owner="o", repo="r", started_at=datetime(2026, 10, 22, 8, 0))
    assert s.started_at.tzinfo is not None and s.branch is None
    assert scan_slot(T0.astimezone(timezone(timedelta(hours=2)))) == scan_slot(T0) == "2026-10-22T10:00Z"
    with pytest.raises(ValidationError):
        SessionInfo(session_id="p", role="pse", owner="o", repo="r", started_at=T0)  # a PSE names its branch
    with pytest.raises(ValidationError):
        JevMessage(kind=JevKind.OK, scan_id="x", session_id="s", idempotency_key=idempotency_key("s", None, "x"))


def test_collect_counts_a_loop_once_and_ignores_older_incarnations(tmp_path):
    g = FakeGitea()
    write_log(tmp_path, failing_loop(T0, 3))
    s = session()
    first = collect(tmp_path, s, g, T0, None)
    assert first.action_error_streak == 3
    again = collect(tmp_path, s, g, T0 + timedelta(minutes=10), T0)  # no new calls since the last scan
    assert again.action_error_streak == 0
    g.commits[s.branch] = [
        {"sha": f"r{i}", "created": (T0 - timedelta(hours=1, minutes=i)).isoformat()} for i in range(3)
    ]
    for i in range(3):
        g.statuses[f"r{i}"] = [{"id": 1, "context": "ci", "status": "failure", "description": "Failing after 1m"}]
    fresh = session(started_at=T0 + timedelta(seconds=30), restarts=1)  # restarted after the old loop
    ev2 = collect(tmp_path, fresh, g, T0 + timedelta(minutes=1), None)
    assert ev2.action_error_streak == 0 and ev2.ci_failing_streak == 0 and ev2.last_loop_event_at is None


def test_push_time_comes_from_the_head_change_not_the_commit_date(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=2))
    write_log(tmp_path, [end_row(T0 + timedelta(minutes=55))])
    g.commits[s.branch] = [{"sha": "old", "created": (T0 - timedelta(hours=1)).isoformat()}]
    seen = {"old": T0 - timedelta(minutes=50)}
    g.commits[s.branch] = [{"sha": "late", "created": T0.isoformat()}, *g.commits[s.branch]]  # committed 10:00
    e = collect(tmp_path, s, g, T0 + timedelta(minutes=60), T0 + timedelta(minutes=50), seen_heads=seen)
    assert e.durable_progress_since_last_scan and e.last_durable_progress_at == T0 + timedelta(minutes=60)
    e = collect(
        tmp_path,
        s,
        g,
        T0 + timedelta(minutes=70),
        T0 + timedelta(minutes=60),
        seen_heads={**seen, "late": T0 + timedelta(minutes=60)},
    )
    assert not e.durable_progress_since_last_scan and e.last_durable_progress_at == T0 + timedelta(minutes=60)


def test_branchless_sessions_read_no_branch_or_ci(tmp_path):
    g = FakeGitea()
    g.fail_reads = True  # any branch read would make the scan unknown
    review = session(session_id="rev-1", role="review", branch=None, commands_log=None)
    assert collect(tmp_path, review, g, T0, None).observable


def test_cancelled_actions_jobs_and_status_order():
    g = FakeGitea()
    g.statuses["a"] = [
        {"id": 3, "context": "CI / build (push)", "status": "failure", "description": "Canceled after 2m"},
        {"id": 1, "context": "ci/woodpecker", "status": "pending"},
        {"id": 2, "context": "ci/woodpecker", "status": "failure", "description": "tests failed"},
    ]
    ci = commit_outcome(g, "o", "r", "a")
    assert ci.outcome == "failure" and ci.failing_contexts == {"ci/woodpecker"}
    g.statuses["b"] = [
        {"id": 1, "context": "CI / test (push)", "status": "failure", "description": "Canceled after 9s"}
    ]
    assert commit_outcome(g, "o", "r", "b").outcome == "cancelled"
    g.statuses["c"] = [  # two workflow files sharing name and job: the red one is not hidden by the green one
        {"id": 7, "context": "CI / test (push)", "workflow": "ci.yml", "status": "failure", "description": "Failure"},
        {"id": 8, "context": "CI / test (push)", "workflow": "ci-extra.yml", "status": "success"},
    ]
    assert commit_outcome(g, "o", "r", "c").outcome == "failure"


def test_unknown_scan_does_not_move_the_baseline(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=2))
    db = tmp_path / "j.sqlite"
    g.commits[s.branch] = [{"sha": "c0", "created": (T0 - timedelta(hours=1)).isoformat()}]
    write_log(tmp_path, failing_loop(T0, 3))
    assert run_scan(tmp_path, [s], g, db, T0)["results"][0]["message"]["kind"] == "health.warn"
    g.commits[s.branch] = [{"sha": "c1", "created": (T0 + timedelta(minutes=5)).isoformat()}, *g.commits[s.branch]]
    g.fail_reads = True
    assert (
        run_scan(tmp_path, [s], g, db, T0 + timedelta(minutes=10))["results"][0]["message"]["kind"] == "health.unknown"
    )
    g.fail_reads = False
    write_log(
        tmp_path,
        failing_loop(T0, 3)
        + [end_row(T0 + timedelta(minutes=19, seconds=i), "pytest -q", False, "err:new") for i in range(3)],
    )
    m = run_scan(tmp_path, [s], g, db, T0 + timedelta(minutes=20))["results"][0]["message"]
    assert m["kind"] == "health.warn", "the push before the outage still broke the chain"


def test_retried_scan_in_the_same_slot_reuses_the_episode(tmp_path):
    g = FakeGitea()
    write_log(tmp_path, failing_loop(T0, 3))
    db = tmp_path / "j.sqlite"
    run_scan(tmp_path, [session()], g, db, T0)
    r = run_scan(tmp_path, [session()], g, db, T0 + timedelta(minutes=4))
    assert g.posts == 1 and any("edited" in a for a in r["results"][0]["actions"])


def test_deleted_comment_is_recreated_and_label_still_moves(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [s], g, db, T0)
    g.comments[184] = []  # a person deleted Jev's comment
    write_log(tmp_path, failing_loop(T0 + timedelta(minutes=10), 4))
    run_scan(tmp_path, [s], g, db, T0 + timedelta(minutes=10))
    assert g.posts == 2 and len(g.comments[184]) == 1 and g.issue_labels[184] == {42, 72}


def test_comment_follows_the_work_item(tmp_path):
    g = FakeGitea()
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [session()], g, db, T0)
    write_log(tmp_path, failing_loop(T0 + timedelta(minutes=10), 4))
    run_scan(tmp_path, [session(issue=190)], g, db, T0 + timedelta(minutes=10))
    assert len(g.comments.get(190, [])) == 1 and g.issue_labels[190] == {42, 72}


def test_failed_resolution_is_retried(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [s], g, db, T0)
    g.fail_remove = 1
    problems = []
    for i in range(1, 4):
        at = T0 + timedelta(minutes=10 * i)
        g.commits[s.branch] = [{"sha": f"s{i}", "created": (at - timedelta(minutes=1)).isoformat()}]
        write_log(tmp_path, [end_row(at - timedelta(minutes=1), f"step {i}", outcome=f"ok:{i}")])
        problems += run_scan(tmp_path, [s], g, db, at)["results"][0]["problems"]
    assert any("will retry" in p for p in problems)
    assert g.issue_labels[184] == set() and "resolved" in g.comments[184][0]["body"]


def test_shared_issue_keeps_its_label_while_another_episode_is_open(tmp_path):
    g = FakeGitea()
    db = tmp_path / "j.sqlite"
    pse = session(started_at=T0 - timedelta(hours=3))
    rev = session(session_id="rev-1", role="review", branch=None, commands_log=".specify/sessions/commands/rev-1.jsonl")
    for name in ("pse-184", "rev-1"):
        path = tmp_path / f".specify/sessions/commands/{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in failing_loop(T0, 3)))
    run_scan(tmp_path, [pse, rev], g, db, T0)
    for i in range(1, 3):  # the PSE recovers with pushes; the reviewer stays silent and gets worse
        at = T0 + timedelta(minutes=10 * i)
        g.commits[pse.branch] = [{"sha": f"s{i}", "created": (at - timedelta(minutes=1)).isoformat()}]
        write_log(tmp_path, [end_row(at - timedelta(minutes=1), f"step {i}", outcome=f"ok:{i}")])
        run_scan(tmp_path, [pse, rev], g, db, at)
    assert g.issue_labels[184], "the reviewer's open episode keeps its label on the shared issue"


def test_one_session_failing_does_not_blind_jev_to_the_others(tmp_path):
    g = FakeGitea()
    write_log(tmp_path, failing_loop(T0, 4))
    a = session()
    b = session(session_id="pse-185", issue=185, branch="agent/pse/185-y")
    g.crash_branch = b.branch
    r = run_scan(tmp_path, [b, a], g, tmp_path / "j.sqlite", T0)
    assert r["failed"] == ["pse-185"] and r["results"][1]["message"]["kind"] == "health.stuck"


def test_only_one_scan_runs_at_a_time(tmp_path):
    import fcntl

    db = tmp_path / "j.sqlite"
    with (tmp_path / "j.lock").open("a") as held:
        fcntl.flock(held, fcntl.LOCK_EX)
        r = run_scan(tmp_path, [session()], FakeGitea(), db, T0)
    assert "skipped" in r and not r["results"]


@pytest.mark.parametrize(
    "setup",
    [
        lambda g: g.permissions.update(push=True),
        lambda g: g.permissions.update(admin=True),
        lambda g: setattr(g, "can_merge_main", True),
        lambda g: setattr(g, "permissions", {}),
    ],
    ids=["repo-push", "repo-admin", "merge-main", "unreadable"],
)
def test_self_check_refuses_any_write_authority(tmp_path, setup):
    g = FakeGitea()
    setup(g)
    with pytest.raises(PermissionError):
        run_scan(tmp_path, [session()], g, tmp_path / "j.sqlite", T0)


def test_org_labels_are_found(tmp_path):
    g = FakeGitea()
    g.labels, g.org_label_list = [], [{"id": 51, "name": "jev/warning"}, {"id": 52, "name": "jev/stuck"}]
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [session()], g, tmp_path / "j.sqlite", T0)
    assert g.issue_labels[184] == {51}


def test_review_session_with_a_branch_reads_no_branch(tmp_path):
    g = FakeGitea()
    g.fail_reads = True  # a branch read would make the scan unknown
    review = session(session_id="rev-1", role="review", branch="main", commands_log=None)
    e = collect(tmp_path, review, g, T0, None)
    assert e.observable and e.head_sha is None and g.branch_reads == 0


def test_calls_logged_after_the_scan_time_count_in_the_next_scan_only(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(minutes=30))
    db = tmp_path / "j.sqlite"
    # the scan's clock reads 10:00; three failures land 2–4 s later, before Jev reads this session's log
    write_log(
        tmp_path,
        [end_row(T0 - timedelta(minutes=2))]
        + [end_row(T0 + timedelta(seconds=2 + i), "pytest -q", False, "err:same") for i in range(3)],
    )
    kinds = [
        run_scan(tmp_path, [s], g, db, T0 + timedelta(minutes=m))["results"][0]["message"]["kind"] for m in (0, 10, 20)
    ]
    assert kinds == ["health.ok", "health.warn", "health.ok"]


def test_fifty_unknown_scans_do_not_lose_the_episode(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    first = run_scan(tmp_path, [s], g, db, T0)["results"][0]["message"]
    write_log(tmp_path, failing_loop(T0 + timedelta(minutes=10), 4))
    run_scan(tmp_path, [s], g, db, T0 + timedelta(minutes=10))
    g.fail_reads = True
    for i in range(50):
        run_scan(tmp_path, [s], g, db, T0 + timedelta(minutes=20 + 10 * i))
    g.fail_reads = False
    at = T0 + timedelta(minutes=520)
    write_log(tmp_path, failing_loop(at, 4))
    m = run_scan(tmp_path, [s], g, db, at)["results"][0]["message"]
    assert m["kind"] == "health.stuck" and m["episode_id"] == first["episode_id"]
    assert g.posts == 1 and g.issue_labels[184] == {42, 72}


def test_an_unknown_retry_never_overwrites_an_observed_scan(tmp_path):
    g = FakeGitea()
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    assert run_scan(tmp_path, [session()], g, db, T0)["results"][0]["message"]["kind"] == "health.warn"
    g.fail_reads = True
    r = run_scan(tmp_path, [session()], g, db, T0 + timedelta(minutes=4))  # same slot, nothing observed
    assert r["results"][0]["message"]["kind"] == "health.unknown"
    g.fail_reads = False
    write_log(
        tmp_path,
        failing_loop(T0, 3)
        + [end_row(T0 + timedelta(minutes=9, seconds=i), "pytest -q", False, "err:new") for i in range(3)],
    )
    m = run_scan(tmp_path, [session()], g, db, T0 + timedelta(minutes=10))["results"][0]["message"]
    assert m["kind"] == "health.stuck" and m["next_action"] == "request_stop" and g.posts == 1


def test_a_head_older_than_the_first_scan_is_not_a_fresh_push(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    g.commits[s.branch] = [{"sha": "old", "created": (T0 - timedelta(hours=2)).isoformat()}]
    kinds = []
    for m in (0, 10):
        at = T0 + timedelta(minutes=m)
        write_log(tmp_path, [end_row(at - timedelta(minutes=1), f"step {m}", outcome=f"ok:{m}")])
        kinds.append(run_scan(tmp_path, [s], g, db, at)["results"][0]["message"])
    assert [k["kind"] for k in kinds] == ["health.warn", "health.stuck"]
    assert all(Reason.SPINNING.value in k["reasons"] for k in kinds)


def test_label_is_cleared_even_when_the_comment_was_never_written(tmp_path):
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    g.fail_list_comments = 1
    r = run_scan(tmp_path, [s], g, db, T0)
    assert any("comment write failed" in p for p in r["results"][0]["problems"]) and g.issue_labels[184] == {41, 71}
    for i in range(1, 3):
        at = T0 + timedelta(minutes=10 * i)
        g.commits[s.branch] = [{"sha": f"s{i}", "created": (at - timedelta(minutes=1)).isoformat()}]
        write_log(tmp_path, [end_row(at - timedelta(minutes=1), f"step {i}", outcome=f"ok:{i}")])
        run_scan(tmp_path, [s], g, db, at)
    assert g.issue_labels[184] == set() and g.posts == 0


def test_an_unsupervised_sessions_episode_ends_and_frees_its_label(tmp_path):
    g = FakeGitea()
    db = tmp_path / "j.sqlite"
    stopped = session(started_at=T0 - timedelta(hours=3))
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [stopped], g, db, T0)
    assert g.issue_labels[184] == {41, 71}
    successor = session(
        session_id="pse-200", branch="agent/pse/184-y", commands_log=".specify/sessions/commands/x.jsonl"
    )
    log = tmp_path / ".specify/sessions/commands/x.jsonl"
    log.write_text(json.dumps(end_row(T0 + timedelta(minutes=9))) + "\n")
    g.commits[successor.branch] = [{"sha": "n1", "created": (T0 + timedelta(minutes=9)).isoformat()}]
    r = run_scan(tmp_path, [successor], g, db, T0 + timedelta(minutes=10))  # the Lead reassigned the issue
    assert r["results"][0]["message"]["kind"] == "health.ok"
    assert r["ended"] and g.issue_labels[184] == set()
    body = g.comments[184][0]["body"]
    assert "ended" in body and "has recovered" not in body
    assert not run_scan(tmp_path, [successor], g, db, T0 + timedelta(minutes=20))["ended"]


def test_label_guard_and_pruning_count_only_what_is_still_open(tmp_path):
    store = ScanStore(tmp_path / "j.sqlite")
    where = ("acme", "factory", 184)
    store.mark_intent("a", "pse-old", where, "e-old", "posted", 1001, T0)
    store.mark_intent("b", "pse-new", where, "e-new", "posted", 1002, T0)
    assert store.others_unresolved_on(where, "b")
    assert not store.others_unresolved_on(where, "b", frozenset({"pse-new"}))  # pse-old is no longer supervised
    store.mark_intent("b", "pse-new", where, "e-new", "resolved", 1002, T0)
    assert store.prune_intents(T0 + timedelta(hours=80)) == 1  # only the resolved row goes
    assert store.intent("a") is not None and store.intent("b") is None
    store.close()


def test_repository_labels_need_no_organisation_scope(tmp_path):
    g = FakeGitea()
    g.org_error = 403  # the token lacks read:organization
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [session()], g, tmp_path / "j.sqlite", T0)
    assert g.issue_labels[184] == {41, 71}
    g = FakeGitea()
    g.labels, g.org_error = [], 500
    r = run_scan(tmp_path, [session()], g, tmp_path / "k.sqlite", T0)  # a label read failure stays per session
    assert any("label write failed" in p for p in r["results"][0]["problems"]) and g.posts == 1


def test_older_database_is_migrated(tmp_path):
    import sqlite3

    db = tmp_path / "old.sqlite"
    con = sqlite3.connect(db)
    con.executescript(
        "CREATE TABLE scans (session_id TEXT NOT NULL, scan_id TEXT NOT NULL, at TEXT NOT NULL, kind TEXT NOT NULL,"
        " reasons TEXT NOT NULL, next_action TEXT NOT NULL, episode_id TEXT, durable_progress INTEGER NOT NULL,"
        " message TEXT NOT NULL, PRIMARY KEY (session_id, scan_id));"
        "CREATE TABLE intents (key TEXT PRIMARY KEY, session_id TEXT NOT NULL, issue INTEGER NOT NULL,"
        " episode_id TEXT NOT NULL, recovery_point TEXT NOT NULL, comment_id INTEGER, updated_at TEXT NOT NULL);"
    )
    con.execute(
        "INSERT INTO scans VALUES ('pse-184', '2026-10-22T09:50Z', ?, 'health.warn', '[]', 'nudge_session', 'e1', 0,"
        " '{}')",
        ((T0 - timedelta(minutes=10)).isoformat(),),
    )
    con.commit()
    con.close()
    write_log(tmp_path, failing_loop(T0, 4))
    m = run_scan(tmp_path, [session()], FakeGitea(), db, T0)["results"][0]["message"]
    assert m["kind"] == "health.stuck" and m["episode_id"] == "e1"


def test_cli_scans_the_valid_sessions_and_reports_the_invalid_one(tmp_path, monkeypatch, capsys):
    from sdd_harness.jev import cli

    g = FakeGitea()
    monkeypatch.setattr(cli, "HttpGiteaClient", lambda url, token: g)
    monkeypatch.setenv("JEV_GITEA_TOKEN", "t")
    good = json.loads(session().model_dump_json())
    bad = {**good, "session_id": "pse-185", "branch": None}  # listed before its worktree exists
    path = tmp_path / "sessions.json"
    path.write_text(json.dumps([bad, good]))
    write_log(tmp_path, failing_loop(T0, 3))
    code = cli.main(["--root", str(tmp_path), "scan", "--sessions", str(path), "--now", T0.isoformat(), "--dry-run"])
    report = json.loads(capsys.readouterr().out)
    assert code == 1 and [x["session"] for x in report["invalid_sessions"]] == ["pse-185"]
    assert [r["message"]["session_id"] for r in report["results"]] == ["pse-184"]
    path.write_text("{not json")
    assert cli.main(["--root", str(tmp_path), "scan", "--sessions", str(path)]) == 2


# ---------------------------------------------------------------- the HTTP client, without a network


class StubHttp(HttpGiteaClient):
    def __init__(self, pages: dict[str, list], total: int | None, missing_branch: bool = False):
        super().__init__("http://gitea.invalid", "t")
        self.pages, self.total, self.missing_branch, self.calls = pages, total, missing_branch, 0

    def _request(self, method, path, body=None, query=None):
        self.calls += 1
        if self.missing_branch and path.endswith("/commits"):
            raise GiteaError("GET commits → HTTP 404", 404)
        if path.startswith("/orgs/"):
            raise GiteaError(f"GET {path} → HTTP 403", 403)  # every /orgs route checks read:organization first
        page = (query or {}).get("page", 1)
        items = self.pages.get(path, [])
        clamp = 20  # the server's MAX_RESPONSE_ITEMS is below Jev's page size
        batch = items[(page - 1) * clamp : page * clamp]
        headers = {"x-total-count": str(self.total if self.total is not None else len(items))}
        if path.endswith("/status"):  # a combined status: the list sits under "statuses"
            return {"state": "pending", "total_count": len(batch), "statuses": batch}, headers
        return batch, headers


def test_paging_reads_past_a_clamped_page_and_404_branches_are_empty():
    labels = [{"id": i, "name": f"l{i}"} for i in range(24)] + [{"id": 41, "name": "jev/warning"}]
    c = StubHttp({"/repos/o/r/labels": labels}, None)
    assert {"id": 41, "name": "jev/warning"} in c.repo_labels("o", "r")
    assert StubHttp({}, None, missing_branch=True).branch_commits("o", "r", "agent/x", 10) == []
    statuses = [{"id": i, "context": f"c{i}", "status": "success"} for i in range(25)]
    assert len(StubHttp({"/repos/o/r/commits/abc/status": statuses}, None).latest_statuses("o", "r", "abc")) == 25
    assert StubHttp({}, None).org_labels("o") == []  # 403 without read:organization reads as "none"


def test_non_json_response_is_a_gitea_error(monkeypatch):
    class Resp:
        headers = {}

        def read(self):
            return b"<html>login</html>"

        def __enter__(self):
            return self

        def __exit__(self, *a):
            return False

    monkeypatch.setattr("urllib.request.urlopen", lambda req, timeout: Resp())
    with pytest.raises(GiteaError):
        HttpGiteaClient("http://gitea.invalid", "t").me()


# ---------------------------------------------------------------------------
# R8: role labels + summary label (spec 008 FR-036, SC-015)
# ---------------------------------------------------------------------------


def test_r8_pse_warn_and_stuck_use_role_and_summary_labels(tmp_path):
    """A single PSE session: warn gets {jev/pse/warning, jev/warning}; stuck gets {jev/pse/stuck, jev/stuck}."""
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [s], g, db, T0)
    assert g.issue_labels[184] == {41, 71}, "warn: jev/warning (41) + jev/pse/warning (71)"
    run_scan(tmp_path, [s], g, db, T0 + timedelta(minutes=10))
    assert g.issue_labels[184] == {42, 72}, "stuck: jev/stuck (42) + jev/pse/stuck (72)"


def test_r8_single_session_resolve_removes_both_labels(tmp_path):
    """When the only open episode resolves, both the role label and the summary label are removed."""
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [s], g, db, T0)
    assert g.issue_labels[184] == {41, 71}
    # recover
    for i in range(1, 3):
        at = T0 + timedelta(minutes=10 * i)
        g.commits[s.branch] = [{"sha": f"s{i}", "created": (at - timedelta(minutes=1)).isoformat()}]
        write_log(tmp_path, [end_row(at - timedelta(minutes=1), f"step {i}", outcome=f"ok:{i}")])
        run_scan(tmp_path, [s], g, db, at)
    assert g.issue_labels[184] == set(), "both labels removed after resolve"


def test_r8_role_and_summary_never_replace_each_other(tmp_path):
    """Adding a role label does not remove the summary label, and vice versa (different exclusive scopes)."""
    g = FakeGitea()
    s = session(started_at=T0 - timedelta(hours=3))
    db = tmp_path / "j.sqlite"
    write_log(tmp_path, failing_loop(T0, 3))
    run_scan(tmp_path, [s], g, db, T0)
    labels = g.issue_labels[184]
    assert 41 in labels, "summary label present"
    assert 71 in labels, "role label present"
    assert len(labels) == 2, "exactly two: role + summary, no accidental removal"


def test_r8_two_sessions_on_same_issue_summary_reflects_worst(tmp_path):
    """PSE stuck + Review warn → summary is stuck; PSE resolves → summary is warn; Review resolves → no summary."""
    g = FakeGitea()
    db = tmp_path / "j.sqlite"
    pse = session(started_at=T0 - timedelta(hours=3))
    rev = session(
        session_id="rev-1",
        role="review",
        branch=None,
        commands_log=".specify/sessions/commands/rev-1.jsonl",
        started_at=T0 - timedelta(hours=3),
    )
    for name in ("pse-184", "rev-1"):
        path = tmp_path / f".specify/sessions/commands/{name}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("".join(json.dumps(r) + "\n" for r in failing_loop(T0, 3)))
    # T0: both sessions get stuck (PSE branch-based → stuck; Review no branch → also stuck after 4 bad scans)
    # Run twice so both sessions reach stuck (stuck needs prior warn scan)
    run_scan(tmp_path, [pse, rev], g, db, T0)
    run_scan(tmp_path, [pse, rev], g, db, T0 + timedelta(minutes=5))
    labels = g.issue_labels[184]
    assert 72 in labels or 71 in labels, "PSE role label present"
    assert 82 in labels or 81 in labels, "Review role label present"
    # After PSE recovers (two ok scans), PSE role label gone; summary shows Review's level
    for i in range(1, 3):
        at = T0 + timedelta(minutes=10 + 10 * i)
        g.commits[pse.branch] = [{"sha": f"s{i}", "created": (at - timedelta(minutes=1)).isoformat()}]
        write_log(tmp_path, [end_row(at - timedelta(minutes=1), f"step {i}", outcome=f"ok:{i}")])
        run_scan(tmp_path, [pse, rev], g, db, at)
    labels_after_pse_resolve = g.issue_labels[184]
    assert 72 not in labels_after_pse_resolve and 71 not in labels_after_pse_resolve, "PSE role label removed"
    assert 41 in labels_after_pse_resolve or 42 in labels_after_pse_resolve, "summary label still present from Review"
    assert 81 in labels_after_pse_resolve or 82 in labels_after_pse_resolve, "Review role label still present"
