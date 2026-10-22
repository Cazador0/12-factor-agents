#!/usr/bin/env python3
"""Command log for Jev (spec 008): one JSON line per tool call start and end.

Registered for PreToolUse, PostToolUse and PostToolUseFailure. Writes
.specify/sessions/commands/<session_id>.jsonl (gitignored) with
{event, at, session_id, tool, command, tool_use_id, exit_code, ok, outcome, timed_out, timeout_s, duration_ms}.
Outputs are stored as short hashes, never as text. The hook always exits 0 so it can never block a tool call.
"""

import hashlib
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

MAX_COMMAND = 500


def _sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8", "replace")).hexdigest()[:16]


def _command(tool: str, tool_input: dict) -> str:
    if tool == "Bash":
        cmd = str(tool_input.get("command", ""))
    else:
        cmd = json.dumps(tool_input, sort_keys=True, default=str)
    return re.sub(r"\s+", " ", cmd).strip()[:MAX_COMMAND]


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except (json.JSONDecodeError, ValueError):
        return 0
    event = payload.get("hook_event_name", "")
    tool = str(payload.get("tool_name", ""))
    tool_input = payload.get("tool_input") or {}
    row = {
        "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "session_id": payload.get("session_id"),
        "tool": tool,
        "command": _command(tool, tool_input),
        "tool_use_id": payload.get("tool_use_id"),
    }
    if event == "PreToolUse":
        timeout_ms = tool_input.get("timeout") if tool == "Bash" else None
        row.update(event="start", timeout_s=int(timeout_ms) // 1000 if isinstance(timeout_ms, (int, float)) else None)
    elif event == "PostToolUse":
        resp = payload.get("tool_response")
        text = json.dumps(resp, sort_keys=True, default=str) if not isinstance(resp, str) else resp
        interrupted = bool(isinstance(resp, dict) and resp.get("interrupted"))
        row.update(event="end", exit_code=0, ok=not interrupted, outcome="ok:" + _sha(text),
                   timed_out=False, duration_ms=payload.get("duration_ms"))
    elif event == "PostToolUseFailure":
        error = str(payload.get("error", ""))
        first = error.splitlines()[0] if error else ""
        m = re.match(r"Exit code (\d+)", first)
        row.update(event="end", exit_code=int(m.group(1)) if m else None, ok=False, outcome="err:" + _sha(error),
                   timed_out=bool(re.search(r"timed out", error, re.I)), duration_ms=payload.get("duration_ms"),
                   interrupt=bool(payload.get("is_interrupt", False)))
    else:
        return 0
    root = Path(os.environ.get("CLAUDE_PROJECT_DIR") or payload.get("cwd") or ".")
    session = re.sub(r"[^A-Za-z0-9_.-]", "_", str(payload.get("session_id") or "unknown"))
    try:
        path = root / ".specify" / "sessions" / "commands" / f"{session}.jsonl"
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps(row) + "\n")
    except OSError:
        pass
    return 0


if __name__ == "__main__":
    sys.exit(main())
