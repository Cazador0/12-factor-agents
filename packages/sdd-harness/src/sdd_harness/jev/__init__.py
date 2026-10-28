"""Jev: a read-mostly, type-safe progress watchdog for agent sessions (spec 008).

Plain code decides health (``decide``); Jev comments and labels, and never edits code, pushes, approves or merges.
"""

from .decide import consecutive_bad_scans, decide, open_episode, scan_slot
from .models import (
    SCHEMA_VERSION,
    CommitCI,
    Evidence,
    JevKind,
    JevMessage,
    Lease,
    NextAction,
    Reason,
    ScanRecord,
    SessionInfo,
    Thresholds,
    Verdict,
    idempotency_key,
)
from .scan import run_scan, scan_session
from .store import ScanStore

__all__ = [
    "SCHEMA_VERSION",
    "CommitCI",
    "Evidence",
    "JevKind",
    "JevMessage",
    "Lease",
    "NextAction",
    "Reason",
    "ScanRecord",
    "ScanStore",
    "SessionInfo",
    "Thresholds",
    "Verdict",
    "consecutive_bad_scans",
    "decide",
    "idempotency_key",
    "open_episode",
    "run_scan",
    "scan_session",
    "scan_slot",
]
