"""Model runtimes that run agentic and trigger benchmark cases (SPEC-102).

A ``Runtime`` has a ``name``, an optional ``model``, ``available()`` returning
``(bool, reason)``, and ``run(system_prompt, user_prompt, output_schema, *,
timeout)`` returning a ``RuntimeResult(text, json_or_none, usage, raw_meta)``.
``output_schema`` is a JSON Schema dict (or None for free text). Only
``ollama-cloud`` validates the reply itself: it has no structured outputs, so
it runs a bounded repair loop. Graders always re-validate every reply.

Runtimes are created by name with ``create_runtime``:

=================  ==========================================================
``ollama-local``   ``POST $OLLAMA_HOST/api/chat`` with ``format`` = schema
``ollama-cloud``   ``POST https://ollama.com/api/chat``, Bearer ``OLLAMA_API_KEY``
``claude-cli``     ``claude -p --output-format json`` (when on PATH)
``codex-cli``      ``codex exec --json`` (when on PATH)
``replay``         results recorded earlier by a live run (``lab.cassette``)
=================  ==========================================================

Prompts come from ``zed_emulation``; results are labelled
``<runtime>-zed-emulation`` because they emulate Zed's skill loading, not Zed.
"""

from __future__ import annotations

import json
import re
from typing import Any, Dict, Mapping, NamedTuple, Optional, Tuple

from _skillkit import cli

RUNTIME_NAMES = ("ollama-local", "ollama-cloud", "claude-cli", "codex-cli", "replay")
RUNTIME_ALIASES = {"claude": "claude-cli", "codex": "codex-cli"}
"""Short names used in SPEC-202 (``--runtime claude``)."""

LIVE_PREREQ_MISSING = "LIVE_PREREQ_MISSING"
"""Reason prefix for a runtime or service that cannot be used here (SPEC-201 FR-041)."""

_FENCE_RE = re.compile(r"```(?:json|JSON)?[ \t]*\r?\n(.*?)\r?\n?```", re.DOTALL)
_THINK_RE = re.compile(r"^\s*<think>.*?</think>", re.DOTALL)


class RuntimeResult(NamedTuple):
    text: str
    """The model's final reply text."""
    json_or_none: Any
    """The reply parsed as JSON, or None when no JSON document could be extracted."""
    usage: Dict[str, int]
    """``input_tokens`` and ``output_tokens`` when the runtime reports them."""
    raw_meta: Dict[str, Any]
    """Runtime-specific facts worth recording (repairs, extraction mode, num_ctx...)."""


class RuntimeCallError(Exception):
    """The runtime was available but the call failed (HTTP error, timeout, unusable reply)."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__("%s: %s" % (code, message))
        self.code = code
        self.message = message


class Runtime:
    """Interface every runtime implements."""

    name = ""
    model: Optional[str] = None

    def available(self) -> Tuple[bool, str]:
        """``(True, "ok")`` or ``(False, reason)``; never raises and never spends tokens."""
        raise NotImplementedError

    def run(
        self, system_prompt: str, user_prompt: str, output_schema: Optional[dict], *, timeout: float
    ) -> RuntimeResult:
        """One model turn. Raises ``RuntimeCallError`` when the call fails."""
        raise NotImplementedError


def canonical_name(name: str) -> str:
    """Map an alias (``claude``) to its runtime name (``claude-cli``)."""
    return RUNTIME_ALIASES.get(name, name)


def create_runtime(
    name: str,
    *,
    model: Optional[str] = None,
    num_ctx: Optional[int] = None,
    max_repairs: Optional[int] = None,
    cassette: Any = None,
    environ: Optional[Mapping[str, str]] = None,
) -> Runtime:
    """Build a runtime by name. ``cassette`` (a ``lab.cassette.Cassette``) is required for ``replay``."""
    name = canonical_name(name)
    if name == "ollama-local":
        from .ollama_local import DEFAULT_NUM_CTX, OllamaLocalRuntime

        return OllamaLocalRuntime(model, num_ctx=num_ctx or DEFAULT_NUM_CTX, environ=environ)
    if name == "ollama-cloud":
        from .ollama_cloud import DEFAULT_MAX_REPAIRS, OllamaCloudRuntime

        repairs = DEFAULT_MAX_REPAIRS if max_repairs is None else max_repairs
        return OllamaCloudRuntime(model, max_repairs=repairs, environ=environ)
    if name == "claude-cli":
        from .claude_cli import ClaudeCliRuntime

        return ClaudeCliRuntime(model, environ=environ)
    if name == "codex-cli":
        from .codex_cli import CodexCliRuntime

        return CodexCliRuntime(model, environ=environ)
    if name == "replay":
        from .replay import ReplayRuntime

        if cassette is None:
            raise ValueError("the replay runtime needs a cassette directory")
        return ReplayRuntime(cassette, model=model)
    raise ValueError("unknown runtime %r (known: %s)" % (name, ", ".join(RUNTIME_NAMES)))


def extract_json(text: str) -> Tuple[Any, str]:
    """Parse the JSON document in a model reply; return ``(data, mode)``.

    ``mode`` records how lenient the extraction had to be: ``strict`` (the
    whole reply), ``fenced`` (a Markdown code block) or ``embedded`` (the
    outermost ``{...}`` or ``[...]`` span). A leading ``<think>`` block is
    dropped first. Raises ``ValueError`` when no JSON document is found.
    """
    stripped = _THINK_RE.sub("", text, count=1).strip()
    candidates = [("strict", stripped)]
    candidates.extend(("fenced", match.group(1)) for match in _FENCE_RE.finditer(stripped))
    for opener, closer in (("{", "}"), ("[", "]")):
        start, end = stripped.find(opener), stripped.rfind(closer)
        if 0 <= start < end:
            candidates.append(("embedded", stripped[start : end + 1]))
    for mode, candidate in candidates:
        try:
            return cli.loads_strict(candidate), mode
        except ValueError:
            continue
    raise ValueError("no JSON document found in the reply")


def parse_reply(text: str) -> Tuple[Any, str]:
    """``extract_json`` that returns ``(None, "failed")`` instead of raising."""
    try:
        return extract_json(text)
    except ValueError:
        return None, "failed"


def schema_instruction(schema: dict) -> str:
    """The output contract appended to the user prompt (Ollama recommends it even with ``format``)."""
    return (
        "Reply with exactly one JSON document and nothing else (no prose, no Markdown fences). "
        "It must validate against this JSON Schema (draft 2020-12):\n"
        + json.dumps(schema, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    )


def usage_from(input_tokens: Any, output_tokens: Any) -> Dict[str, int]:
    """Token usage with non-integer or missing counts left out."""
    usage = {}
    for key, value in (("input_tokens", input_tokens), ("output_tokens", output_tokens)):
        if isinstance(value, int) and not isinstance(value, bool) and value >= 0:
            usage[key] = value
    return usage


__all__ = [
    "LIVE_PREREQ_MISSING",
    "RUNTIME_ALIASES",
    "RUNTIME_NAMES",
    "Runtime",
    "RuntimeCallError",
    "RuntimeResult",
    "canonical_name",
    "create_runtime",
    "extract_json",
    "parse_reply",
    "schema_instruction",
    "usage_from",
]
