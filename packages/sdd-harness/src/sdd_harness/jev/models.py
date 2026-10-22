"""Jev's types: the strict message contract shared with OCaml, and the evidence a scan collects.

``JevMessage`` is the only thing Jev publishes. It is strict (no coercion), frozen and closed
(``extra="forbid"``); its JSON Schema is exported to ``schemas/jev-message.v1.json`` as the cross-language
contract. Enums travel as plain JSON strings (``"health.ok"``), so an OCaml consumer writes its enum
``of_yojson``/``to_yojson`` by hand (or uses atdgen ``<json name=...>``): ``ppx_deriving_yojson`` would encode
variants as ``["health.ok"]``. All timestamps are UTC; a naive input is read as UTC.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import StrEnum
from typing import Annotated, Literal

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, model_validator

SCHEMA_VERSION = 1
SCAN_ID_PATTERN = r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}Z$"


def as_utc(dt: datetime) -> datetime:
    """Aware and in UTC; a naive value is read as UTC (as ``parse_ts`` and ``--now`` do)."""
    return dt.replace(tzinfo=UTC) if dt.tzinfo is None else dt.astimezone(UTC)


UtcDatetime = Annotated[datetime, AfterValidator(as_utc)]


class JevKind(StrEnum):
    OK = "health.ok"
    UNKNOWN = "health.unknown"
    WARN = "health.warn"
    STUCK = "health.stuck"
    STOP = "session.stop"


class Reason(StrEnum):
    DEAD = "dead"  # lease heartbeat stale: the process is gone
    HUNG = "hung"  # agent loop silent past the hung window
    SPINNING = "spinning"  # loop active but no durable progress in the progress window
    LOOP_ACTION_ERROR = "loop.action_error"  # the same call failing the same way again and again
    LOOP_ACTION_OBSERVATION = "loop.action_observation"  # the same call returning the same result again and again
    LOOP_ALTERNATION = "loop.alternation"  # A, B, A, B … with nothing changing
    COMMAND_TIMEOUTS = "command.timeouts"  # consecutive command timeouts
    CI_NOT_CONVERGING = "ci.not_converging"  # consecutive head commits with a real (non-cancelled) CI failure
    FAILING_COMMANDS = "commands.failing"  # supporting only: many failures and no durable progress
    UNOBSERVABLE = "unobservable"  # the scan could not see the session; changes nothing


class NextAction(StrEnum):
    NONE = "none"
    NUDGE_SESSION = "nudge_session"  # L0: in-band nudge on the first bad scan
    REQUEST_STOP = "request_stop"  # L1: Lead notified; the session checkpoints and releases its lease
    HARD_STOP = "hard_stop"  # grace window passed without a checkpoint: the policy owner stops it
    NOTIFY_LEAD = "notify_lead"  # stopped or dead: Lead re-plans, reassigns or recovers
    PAGE_PERSON = "page_person"  # L2: the Lead did not act in time, or the episode stayed unresolved
    PARK = "park"  # circuit breaker: too many restarts; manual reset only


class JevMessage(BaseModel):
    """What Jev says about one session in one scan."""

    model_config = ConfigDict(extra="forbid", strict=True, frozen=True)

    schema_version: Literal[1] = SCHEMA_VERSION
    kind: JevKind
    scan_id: str = Field(pattern=SCAN_ID_PATTERN, description="The UTC scan slot, e.g. 2026-10-22T10:20Z")
    session_id: str = Field(min_length=1)
    issue: int | None = Field(default=None, ge=1, description="Gitea issue index the session works on")
    reasons: tuple[Reason, ...] = ()
    next_action: NextAction = NextAction.NONE
    episode_id: str | None = Field(default=None, description="Stall episode this message belongs to")
    evidence: tuple[str, ...] = Field(default=(), description="Short, human-readable facts the verdict rests on")
    idempotency_key: str = Field(pattern=r"^jev-[0-9a-f]{24}$")


def idempotency_key(session_id: str, episode_id: str | None, level: str) -> str:
    """Deterministic, so a restarted Jev regenerates the same key for the same episode and level."""
    raw = f"{session_id}|{episode_id or '-'}|{level}".encode()
    return "jev-" + hashlib.sha256(raw).hexdigest()[:24]


class Lease(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    heartbeat_at: UtcDatetime | None = None
    ttl_s: int = Field(default=1800, ge=1)
    released: bool = False
    epoch: int | None = None


class SessionInfo(BaseModel):
    """One supervised session, as the control plane (spec 001) describes it to Jev.

    Only PSE sessions own a branch; Lead and Review sessions have none, so no branch or CI signal is read for them.
    """

    model_config = ConfigDict(extra="forbid", frozen=True)

    session_id: str = Field(min_length=1)
    role: Literal["lead", "pse", "review"]
    issue: int | None = Field(default=None, ge=1)
    owner: str
    repo: str
    branch: str | None = Field(default=None, min_length=1)
    run_id: str | None = Field(default=None, description="Folder under .specify/traces/ holding trace.jsonl")
    commands_log: str | None = Field(default=None, description="commands.jsonl written by the command-log hook")
    started_at: UtcDatetime
    lease: Lease = Lease()
    waiting_on_human: bool = False
    lead_ack_at: UtcDatetime | None = None
    restarts: int = Field(default=0, ge=0)

    @model_validator(mode="after")
    def _pse_has_a_branch(self) -> SessionInfo:
        if self.role == "pse" and self.branch is None:
            raise ValueError("a PSE session names its branch")
        return self


@dataclass(frozen=True)
class Thresholds:
    """Defaults from the Jev research report (docs/research/reports/Jev watchdog for coding agents.md)."""

    scan_interval_min: int = 10
    hung_after_min: int = 20  # agent-loop silence
    progress_window_min: int = 60  # durable progress (calibrate per role from scan history)
    startup_grace_scans: int = 2
    default_tool_timeout_s: int = 120  # Bash default when a call names none
    loop_window_events: int = 20
    action_error_warn: int = 3
    action_error_stuck: int = 4
    action_observation_stuck: int = 4
    alternation_stuck: int = 6
    command_timeouts_stuck: int = 3
    ci_failing_commits: int = 3
    failing_commands_supporting: int = 5
    stuck_after_bad_scans: int = 2
    bad_scan_lookback: int = 6  # scans examined when counting consecutive bad scans
    recovery_hold_scans: int = 1
    stop_grace_scans: int = 1
    lead_ack_scans: int = 1
    page_after_scans: int = 3
    restarts_to_park: int = 2


@dataclass(frozen=True)
class CommitCI:
    sha: str
    outcome: Literal["success", "failure", "cancelled", "pending", "none"]
    failing_contexts: frozenset[str] = frozenset()


@dataclass(frozen=True)
class Evidence:
    """Everything one scan observed about one session. ``decide`` reads only this."""

    session: SessionInfo
    now: datetime
    observable: bool = True
    unobservable_reason: str | None = None
    last_loop_event_at: datetime | None = None
    in_flight_started_at: datetime | None = None
    in_flight_timeout_s: int | None = None
    last_durable_progress_at: datetime | None = None
    durable_progress_since_last_scan: bool = False
    action_error_streak: int = 0
    action_observation_streak: int = 0
    alternation_len: int = 0
    consecutive_timeouts: int = 0
    failing_commands_in_scan: int = 0
    ci_failing_streak: int = 0
    ci_never_reported: bool = False
    checkpoint_at: datetime | None = None
    head_sha: str | None = None  # branch head seen by this scan; "" = read, nothing pushed; None = not read
    facts: tuple[str, ...] = ()


@dataclass(frozen=True)
class ScanRecord:
    session_id: str
    scan_id: str
    at: datetime
    kind: JevKind
    reasons: tuple[Reason, ...]
    next_action: NextAction
    episode_id: str | None
    durable_progress: bool
    head_sha: str | None = None


@dataclass(frozen=True)
class Verdict:
    kind: JevKind
    reasons: tuple[Reason, ...] = ()
    next_action: NextAction = NextAction.NONE
    episode_id: str | None = None
    facts: tuple[str, ...] = field(default=())
