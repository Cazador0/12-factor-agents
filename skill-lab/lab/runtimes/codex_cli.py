"""``codex-cli``: ``codex exec --json`` as a single-turn runtime.

``codex exec --json --sandbox read-only --skip-git-repo-check [--model M] -``
reads the prompt from stdin (``-``). Codex has no system-prompt flag, so the
emulated Zed system prompt is sent first in the same text. ``--json`` prints
one JSON event per line; the reply is the last agent message and the usage
comes from ``turn.completed``. Both the current event shape
(``{"type": "item.completed", "item": {"type": "agent_message", "text"}}``)
and the older one (``{"msg": {"type": "agent_message", "message"}}``) are read.
The Codex CLI is not installed in the build container, so this parser is
verified only against those documented shapes.
"""

from __future__ import annotations

from typing import Any, Dict, List, Optional, Tuple

from _skillkit import cli
from _skillkit.envelope import compact

from . import RuntimeCallError, RuntimeResult, parse_reply, schema_instruction, usage_from
from .cli_base import CliAgentRuntime


class CodexCliRuntime(CliAgentRuntime):
    name = "codex-cli"
    executable = "codex"

    def command(
        self, executable: str, system_prompt: str, user_prompt: str, output_schema: Optional[dict]
    ) -> Tuple[List[str], str]:
        argv = [executable, "exec", "--json", "--sandbox", "read-only", "--skip-git-repo-check"]
        if self.model:
            argv.extend(["--model", self.model])
        argv.append("-")
        parts = [system_prompt, user_prompt]
        if output_schema is not None:
            parts.append(schema_instruction(output_schema))
        return argv, "\n\n".join(parts)

    def parse(self, stdout: str) -> RuntimeResult:
        messages: List[str] = []
        usage: Dict[str, Any] = {}
        for event in _events(stdout):
            failure = _failure(event)
            if failure is not None:
                raise RuntimeCallError("RUNTIME_FAILED", "codex reported an error: %s" % compact(failure, 200))
            text = _agent_message(event)
            if text is not None:
                messages.append(text)
            if event.get("type") == "turn.completed" and isinstance(event.get("usage"), dict):
                usage = event["usage"]
        if not messages:
            raise RuntimeCallError("RUNTIME_PROTOCOL", "codex output has no agent message")
        text = messages[-1]
        data, mode = parse_reply(text)
        meta = {"structured_output": "prompt", "json_extraction": mode, "agent_messages": len(messages)}
        return RuntimeResult(text, data, usage_from(usage.get("input_tokens"), usage.get("output_tokens")), meta)


def _events(stdout: str) -> List[Dict[str, Any]]:
    events = []
    for line in stdout.splitlines():
        line = line.strip()
        if not line.startswith("{"):
            continue
        try:
            event = cli.loads_strict(line)
        except ValueError:
            continue
        if isinstance(event, dict):
            events.append(event)
    return events


def _agent_message(event: Dict[str, Any]) -> Optional[str]:
    item = event.get("item")
    if event.get("type") == "item.completed" and isinstance(item, dict) and item.get("type") == "agent_message":
        return item.get("text") if isinstance(item.get("text"), str) else None
    msg = event.get("msg")
    if isinstance(msg, dict) and msg.get("type") == "agent_message" and isinstance(msg.get("message"), str):
        return msg["message"]
    return None


def _failure(event: Dict[str, Any]) -> Optional[str]:
    if event.get("type") == "error":
        return str(event.get("message", "error event"))
    if event.get("type") == "turn.failed":
        error = event.get("error")
        return str(error.get("message", "turn failed")) if isinstance(error, dict) else "turn failed"
    return None
