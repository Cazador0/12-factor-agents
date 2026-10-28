"""``ollama-local``: a local Ollama server with JSON-Schema structured outputs.

Request (Ollama ``/api/chat``, ``capabilities/structured-outputs.mdx``)::

    POST $OLLAMA_HOST/api/chat
    {"model": M, "messages": [system, user], "stream": false,
     "options": {"num_ctx": 32768, "temperature": 0}, "format": <schema>}

``num_ctx`` defaults to 32768 because GPUs under 24 GB give Ollama a 4k
default (``context-length.mdx``), far too small for a skill plus its fixtures.
The schema is also appended to the prompt, as the Ollama docs recommend.
``OllamaClient`` is shared with ``ollama-cloud``.
"""

from __future__ import annotations

import os
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Tuple

from _skillkit import cli
from _skillkit.envelope import compact
from _skillkit.redact import redact_text

from . import LIVE_PREREQ_MISSING, Runtime, RuntimeCallError, RuntimeResult, parse_reply, schema_instruction, usage_from
from .transport import (
    NO_RETRY,
    RetryPolicy,
    Transport,
    TransportError,
    json_request,
    send_with_retries,
    urllib_transport,
)

DEFAULT_HOST = "http://localhost:11434"
DEFAULT_PORT = 11434
DEFAULT_NUM_CTX = 32768
PROBE_TIMEOUT = 3.0
CHAT_RETRY = RetryPolicy(max_retries=2)
_STATUS_CODES = {401: "RUNTIME_AUTH", 403: "RUNTIME_AUTH", 404: "MODEL_NOT_FOUND"}


def normalize_host(value: Optional[str]) -> str:
    """Turn an ``OLLAMA_HOST`` value (``host``, ``host:port`` or a URL) into a base URL."""
    value = (value or "").strip().rstrip("/")
    if not value:
        return DEFAULT_HOST
    if "://" not in value:
        value = "http://" + value
    scheme, rest = value.split("://", 1)
    authority, _, path = rest.partition("/")
    if authority.startswith("["):
        has_port = "]:" in authority
    else:
        has_port = ":" in authority
    if not has_port:
        authority = "%s:%d" % (authority, DEFAULT_PORT)
    return "%s://%s%s" % (scheme, authority, "/" + path if path else "")


class OllamaClient:
    """Minimal Ollama REST client: ``/api/chat`` and ``/api/tags``."""

    def __init__(
        self,
        base_url: str,
        *,
        api_key: Optional[str] = None,
        transport: Optional[Transport] = None,
        sleep: Callable[[float], None] = time.sleep,
        retry: RetryPolicy = CHAT_RETRY,
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self._api_key = api_key
        self._transport = transport or urllib_transport
        self._sleep = sleep
        self._retry = retry

    def chat(self, body: Dict[str, Any], *, timeout: float) -> Dict[str, Any]:
        """POST ``/api/chat`` (non-streaming) and return the decoded reply object."""
        reply = self._call("POST", "/api/chat", body, timeout=timeout, policy=self._retry)
        message = reply.get("message")
        if not isinstance(message, dict) or not isinstance(message.get("content"), str):
            raise RuntimeCallError("RUNTIME_PROTOCOL", "Ollama reply has no message.content string")
        return reply

    def model_names(self, *, timeout: float = PROBE_TIMEOUT) -> List[str]:
        """Names from ``GET /api/tags`` (one attempt; used as a cheap availability probe)."""
        reply = self._call("GET", "/api/tags", None, timeout=timeout, policy=NO_RETRY)
        models = reply.get("models")
        if not isinstance(models, list):
            raise RuntimeCallError("RUNTIME_PROTOCOL", "Ollama /api/tags reply has no models list")
        names = []
        for entry in models:
            if isinstance(entry, dict):
                names.extend(entry[key] for key in ("name", "model") if isinstance(entry.get(key), str))
        return sorted(set(names))

    def _call(self, method: str, path: str, body: Any, *, timeout: float, policy: RetryPolicy) -> Dict[str, Any]:
        headers = {"Authorization": "Bearer " + self._api_key} if self._api_key else {}
        request = json_request(method, self.base_url + path, body, headers=headers, timeout=timeout)
        try:
            response = send_with_retries(self._transport, request, policy=policy, sleep=self._sleep)
        except TransportError as exc:
            code = "RUNTIME_TIMEOUT" if exc.timeout else "RUNTIME_UNREACHABLE"
            raise RuntimeCallError(code, "%s %s: %s" % (method, path, exc)) from None
        if response.status != 200:
            code = _STATUS_CODES.get(response.status, "RUNTIME_HTTP_ERROR")
            detail = _error_text(response.body)
            raise RuntimeCallError(code, "%s %s returned HTTP %d%s" % (method, path, response.status, detail))
        try:
            decoded = cli.loads_strict(response.body.decode("utf-8"))
        except (UnicodeDecodeError, ValueError) as exc:
            raise RuntimeCallError("RUNTIME_PROTOCOL", "%s %s reply is not JSON: %s" % (method, path, exc)) from None
        if not isinstance(decoded, dict):
            raise RuntimeCallError("RUNTIME_PROTOCOL", "%s %s reply is not a JSON object" % (method, path))
        return decoded


def model_listed(model: str, names: List[str]) -> bool:
    """True when ``model`` (``qwen3`` means ``qwen3:latest``) is among ``names``."""
    wanted = {model, model if ":" in model else model + ":latest"}
    return bool(wanted & set(names))


def chat_messages(system_prompt: str, user_prompt: str, output_schema: Optional[dict]) -> List[Dict[str, str]]:
    """System + user messages; the user turn ends with the output contract when a schema is given."""
    user = user_prompt if output_schema is None else user_prompt + "\n\n" + schema_instruction(output_schema)
    return [{"role": "system", "content": system_prompt}, {"role": "user", "content": user}]


def reply_usage(reply: Mapping[str, Any]) -> Dict[str, int]:
    return usage_from(reply.get("prompt_eval_count"), reply.get("eval_count"))


class OllamaLocalRuntime(Runtime):
    name = "ollama-local"

    def __init__(
        self,
        model: Optional[str],
        *,
        num_ctx: int = DEFAULT_NUM_CTX,
        host: Optional[str] = None,
        temperature: float = 0.0,
        transport: Optional[Transport] = None,
        sleep: Callable[[float], None] = time.sleep,
        environ: Optional[Mapping[str, str]] = None,
    ) -> None:
        environ = os.environ if environ is None else environ
        self.model = model
        self.num_ctx = num_ctx
        self.temperature = temperature
        self.base_url = normalize_host(host if host is not None else environ.get("OLLAMA_HOST"))
        self.client = OllamaClient(self.base_url, transport=transport, sleep=sleep)

    def available(self) -> Tuple[bool, str]:
        if not self.model:
            return False, "%s: --model is required for %s" % (LIVE_PREREQ_MISSING, self.name)
        try:
            names = self.client.model_names()
        except RuntimeCallError as exc:
            return False, "%s: Ollama at %s is not reachable (%s)" % (LIVE_PREREQ_MISSING, self.base_url, exc.message)
        if not model_listed(self.model, names):
            return False, "%s: model %s is not pulled on %s (run: ollama pull %s)" % (
                LIVE_PREREQ_MISSING,
                self.model,
                self.base_url,
                self.model,
            )
        return True, "ok"

    def run(
        self, system_prompt: str, user_prompt: str, output_schema: Optional[dict], *, timeout: float
    ) -> RuntimeResult:
        body: Dict[str, Any] = {
            "model": self.model,
            "messages": chat_messages(system_prompt, user_prompt, output_schema),
            "stream": False,
            "options": {"num_ctx": self.num_ctx, "temperature": self.temperature},
        }
        if output_schema is not None:
            body["format"] = output_schema
        reply = self.client.chat(body, timeout=timeout)
        text = reply["message"]["content"]
        data, mode = parse_reply(text)
        meta = {
            "num_ctx": self.num_ctx,
            "structured_output": "format" if output_schema is not None else "none",
            "json_extraction": mode,
            "done_reason": reply.get("done_reason"),
        }
        return RuntimeResult(text, data, reply_usage(reply), meta)


def _error_text(body: bytes) -> str:
    """A short, redacted excerpt of an error body (Ollama sends ``{"error": "..."}``)."""
    try:
        decoded = cli.loads_strict(body.decode("utf-8"))
        text = decoded.get("error") if isinstance(decoded, dict) else None
    except (UnicodeDecodeError, ValueError):
        text = body.decode("utf-8", "replace")
    if not text:
        return ""
    return ": " + compact(redact_text(str(text)), 200)
