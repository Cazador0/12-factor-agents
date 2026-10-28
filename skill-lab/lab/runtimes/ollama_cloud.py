"""``ollama-cloud``: Ollama's hosted API, which has no structured outputs.

``POST https://ollama.com/api/chat`` with ``Authorization: Bearer
$OLLAMA_API_KEY`` (``cloud.mdx``, ``api/authentication.mdx``). The request
never carries ``format``: "Ollama's cloud currently does not support
structured outputs" (``capabilities/structured-outputs.mdx``), and cloud
models run at their maximum context, so ``num_ctx`` is not sent either.

Instead the schema goes into the prompt, the reply is parsed and validated
here, and an invalid reply gets up to ``max_repairs`` follow-up turns that feed
back the compact validation errors (12-factor agents, Factor 9: compact errors
into the context window). The last reply is returned either way; graders
decide whether it passes.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from _skillkit.envelope import compact
from _skillkit.jsonschema_mini import validate

from . import LIVE_PREREQ_MISSING, Runtime, RuntimeCallError, RuntimeResult, extract_json, parse_reply
from .ollama_local import OllamaClient, chat_messages, model_listed, reply_usage
from .transport import Transport

CLOUD_URL = "https://ollama.com"
DEFAULT_MAX_REPAIRS = 2
MAX_REPAIR_ERRORS = 8
PROBE_TIMEOUT = 5.0


class OllamaCloudRuntime(Runtime):
    name = "ollama-cloud"

    def __init__(
        self,
        model: Optional[str],
        *,
        max_repairs: int = DEFAULT_MAX_REPAIRS,
        api_key: Optional[str] = None,
        base_url: str = CLOUD_URL,
        temperature: float = 0.0,
        transport: Optional[Transport] = None,
        sleep: Callable[[float], None] = time.sleep,
        environ: Optional[Mapping[str, str]] = None,
    ) -> None:
        environ = os.environ if environ is None else environ
        if max_repairs < 0:
            raise ValueError("max_repairs must be >= 0")
        self.model = model
        self.max_repairs = max_repairs
        self.temperature = temperature
        self.base_url = base_url.rstrip("/")
        key = api_key if api_key is not None else environ.get("OLLAMA_API_KEY", "").strip()
        self._has_key = bool(key)
        self.client = OllamaClient(self.base_url, api_key=key or None, transport=transport, sleep=sleep)

    def available(self) -> Tuple[bool, str]:
        if not self.model:
            return False, "%s: --model is required for %s" % (LIVE_PREREQ_MISSING, self.name)
        if not self._has_key:
            return False, "%s: OLLAMA_API_KEY is not set" % LIVE_PREREQ_MISSING
        try:
            names = self.client.model_names(timeout=PROBE_TIMEOUT)
        except RuntimeCallError as exc:
            return False, "%s: %s is not reachable (%s)" % (LIVE_PREREQ_MISSING, self.base_url, exc.message)
        if not model_listed(self.model, names):
            return False, "%s: model %s is not offered by %s/api/tags" % (
                LIVE_PREREQ_MISSING,
                self.model,
                self.base_url,
            )
        return True, "ok"

    def run(
        self, system_prompt: str, user_prompt: str, output_schema: Optional[dict], *, timeout: float
    ) -> RuntimeResult:
        messages = chat_messages(system_prompt, user_prompt, output_schema)
        usage = {"input_tokens": 0, "output_tokens": 0}
        repairs = 0
        while True:
            reply = self.client.chat(self._body(messages), timeout=timeout)
            for key, value in reply_usage(reply).items():
                usage[key] += value
            text = reply["message"]["content"]
            data, mode, problems = _check(text, output_schema)
            if not problems or repairs >= self.max_repairs:
                meta = {
                    "structured_output": "prompt+validate" if output_schema is not None else "none",
                    "json_extraction": mode,
                    "repairs": repairs,
                    "validation_errors": problems,
                }
                return RuntimeResult(text, data, usage, meta)
            messages = messages + [
                {"role": "assistant", "content": text},
                {"role": "user", "content": repair_prompt(problems)},
            ]
            repairs += 1

    def _body(self, messages: List[Dict[str, str]]) -> Dict[str, Any]:
        return {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": self.temperature},
        }


def repair_prompt(problems: List[str]) -> str:
    """The follow-up turn after an invalid reply: compact errors, then the instruction."""
    lines = ["Your previous reply is not valid. Problems:"]
    lines.extend("- " + problem for problem in problems)
    lines.append("Reply again with only the corrected JSON document, nothing else.")
    return "\n".join(lines)


def _check(text: str, schema: Optional[dict]) -> Tuple[Any, str, List[str]]:
    """Parse and validate one reply into ``(data, extraction_mode, problems)``."""
    if schema is None:
        data, mode = parse_reply(text)
        return data, mode, []
    try:
        data, mode = extract_json(text)
    except ValueError as exc:
        return None, "failed", ["the reply is not a JSON document (%s)" % exc]
    issues = validate(data, schema)
    problems = [compact("%s: %s: %s" % (issue.path or "/", issue.keyword, issue.message), 200) for issue in issues]
    if len(problems) > MAX_REPAIR_ERRORS:
        problems = problems[:MAX_REPAIR_ERRORS] + ["... and %d more" % (len(problems) - MAX_REPAIR_ERRORS)]
    return data, mode, problems
