"""Claude-backed nodes for the LangGraph service runtime.

Calls go through the official ``anthropic`` SDK (``client.beta.messages.parse``) and are wrapped as
LangChain runnables so they compose inside LCEL chains and LangGraph nodes.

Inside a Claude Code session the host model already does the reasoning, so the engines never
call out unless ``SDD_LLM=on`` or an API credential is present (``SDD_LLM=auto``, the default).
Every caller keeps a deterministic path for when :func:`llm_enabled` is false.
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any, TypeVar

from langchain_core.runnables import Runnable, RunnableLambda
from pydantic import BaseModel

DEFAULT_MODEL = "claude-opus-5-5"
# Server-side refusal fallback: the API re-runs a declined request on Anthropic's recommended
# fallback model, routed by refusal category, inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

T = TypeVar("T", bound=BaseModel)


class ClaudeRefusal(RuntimeError):
    """The whole fallback chain declined the request."""

    def __init__(self, category: str | None, explanation: str | None):
        super().__init__(f"Claude declined the request (category={category}): {explanation}")
        self.category = category
        self.explanation = explanation


class ClaudeTruncated(RuntimeError):
    """The response hit max_tokens before the structured output was complete."""


def llm_enabled() -> bool:
    """Whether Claude-backed nodes should run.

    ``SDD_LLM=on`` forces them on, ``off`` forces them off. ``auto`` (default) turns them on when a
    credential the SDK reads is present: an API key, an auth token, or an ``ant auth login`` profile.
    """
    mode = os.environ.get("SDD_LLM", "auto").strip().lower()
    if mode in {"on", "1", "true"}:
        return True
    if mode in {"off", "0", "false"}:
        return False
    if os.environ.get("ANTHROPIC_API_KEY") or os.environ.get("ANTHROPIC_AUTH_TOKEN"):
        return True
    return (Path.home() / ".config" / "anthropic").is_dir() and bool(os.environ.get("ANTHROPIC_PROFILE"))


@dataclass
class Claude:
    """Structured-output calls to Claude with adaptive thinking and refusal fallbacks."""

    model: str = DEFAULT_MODEL
    effort: str = "high"
    max_tokens: int = 16000
    client: Any = None

    @classmethod
    def from_settings(cls, settings: Any | None = None) -> Claude:
        if settings is None:
            return cls()
        return cls(
            model=str(settings.get("llm.model", DEFAULT_MODEL)),
            effort=str(settings.get("llm.effort", "high")),
        )

    def _client(self) -> Any:
        if self.client is None:
            import anthropic

            self.client = anthropic.Anthropic()
        return self.client

    def parse(self, schema: type[T], user: str, system: str | None = None) -> T:
        kwargs: dict[str, Any] = {
            "model": self.model,
            "max_tokens": self.max_tokens,
            "messages": [{"role": "user", "content": user}],
            "output_format": schema,
            "thinking": {"type": "adaptive"},
            "output_config": {"effort": self.effort},
            "betas": [FALLBACK_BETA],
            "fallbacks": "default",
        }
        if system:
            kwargs["system"] = system
        response = self._client().beta.messages.parse(**kwargs)
        if response.stop_reason == "refusal":
            details = getattr(response, "stop_details", None)
            raise ClaudeRefusal(getattr(details, "category", None), getattr(details, "explanation", None))
        if response.stop_reason == "max_tokens":
            raise ClaudeTruncated(f"{schema.__name__} output hit max_tokens={self.max_tokens}")
        parsed = response.parsed_output
        if parsed is None:
            raise ClaudeTruncated(f"No {schema.__name__} in the response (stop_reason={response.stop_reason})")
        return parsed

    def runnable(self, schema: type[T], system: str | None = None) -> Runnable[str, T]:
        """A LangChain runnable: prompt text in, validated ``schema`` instance out."""
        return RunnableLambda(lambda prompt: self.parse(schema, str(prompt), system=system)).with_config(
            run_name=f"claude:{schema.__name__}"
        )
