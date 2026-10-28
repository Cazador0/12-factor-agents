"""``claude-cli``: Claude Code in print mode as a single-turn runtime.

``claude -p --output-format json --no-session-persistence --tools ""
--system-prompt <emulated Zed prompt> [--model M]`` with the user prompt on
stdin. ``--tools ""`` disables every tool so the turn is comparable with the
Ollama runtimes (one reply, no tool calls). The JSON result object carries the
reply in ``result`` and token counts in ``usage``. The output contract is
embedded in the prompt and validated by the graders.
"""

from __future__ import annotations

from typing import List, Optional, Tuple

from _skillkit import cli
from _skillkit.envelope import compact

from . import RuntimeCallError, RuntimeResult, parse_reply, schema_instruction, usage_from
from .cli_base import CliAgentRuntime


class ClaudeCliRuntime(CliAgentRuntime):
    name = "claude-cli"
    executable = "claude"

    def command(
        self, executable: str, system_prompt: str, user_prompt: str, output_schema: Optional[dict]
    ) -> Tuple[List[str], str]:
        argv = [
            executable,
            "-p",
            "--output-format",
            "json",
            "--no-session-persistence",
            "--tools",
            "",
            "--system-prompt",
            system_prompt,
        ]
        if self.model:
            argv.extend(["--model", self.model])
        stdin_text = user_prompt if output_schema is None else user_prompt + "\n\n" + schema_instruction(output_schema)
        return argv, stdin_text

    def parse(self, stdout: str) -> RuntimeResult:
        try:
            result = cli.loads_strict(stdout.strip())
        except ValueError as exc:
            raise RuntimeCallError("RUNTIME_PROTOCOL", "claude output is not JSON: %s" % exc) from None
        if not isinstance(result, dict) or not isinstance(result.get("result"), str):
            raise RuntimeCallError("RUNTIME_PROTOCOL", "claude output has no 'result' string")
        if result.get("is_error") is True or result.get("subtype", "success") != "success":
            raise RuntimeCallError("RUNTIME_FAILED", "claude reported an error: %s" % compact(result["result"], 200))
        text = result["result"]
        data, mode = parse_reply(text)
        usage = result.get("usage") if isinstance(result.get("usage"), dict) else {}
        meta = {
            "structured_output": "prompt",
            "json_extraction": mode,
            "num_turns": result.get("num_turns"),
            "total_cost_usd": result.get("total_cost_usd"),
        }
        return RuntimeResult(text, data, usage_from(usage.get("input_tokens"), usage.get("output_tokens")), meta)
