"""Optional, model-written explanations of a verdict. They describe; they never decide (Art. III).

``claude`` uses the official Anthropic SDK through ``sdd_harness.llm``; ``ollama`` calls an Ollama server (local by
default, or Ollama cloud with ``OLLAMA_HOST`` and ``OLLAMA_API_KEY``), as constitution v1.1.0 allows.
"""

from __future__ import annotations

import json
import os
import urllib.request

from pydantic import BaseModel, ConfigDict

from .models import JevMessage

PROMPT = (
    "Explain this watchdog verdict to the engineer on call in two or three plain sentences: what the session was "
    "doing, why the verdict follows from the evidence, and what happens next. Do not change or question the verdict; "
    "it was decided by code. Verdict JSON:\n"
)


class Explanation(BaseModel):
    model_config = ConfigDict(extra="forbid")
    text: str


def claude_explainer(settings=None):
    from ..llm import Claude

    claude = Claude.from_settings(settings)
    claude.effort = "low"  # a short explanation, not a hard problem

    def explain(msg: JevMessage) -> str:
        return claude.parse(Explanation, PROMPT + msg.model_dump_json()).text

    return explain


def ollama_explainer(model: str | None = None, host: str | None = None, timeout: float = 60.0):
    host = (host or os.environ.get("OLLAMA_HOST") or "http://localhost:11434").rstrip("/")
    model = model or os.environ.get("SDD_OLLAMA_MODEL") or "llama3.1:8b"
    key = os.environ.get("OLLAMA_API_KEY")

    def explain(msg: JevMessage) -> str:
        body = json.dumps({"model": model, "prompt": PROMPT + msg.model_dump_json(), "stream": False}).encode()
        req = urllib.request.Request(f"{host}/api/generate", data=body, method="POST")
        req.add_header("Content-Type", "application/json")
        if key:
            req.add_header("Authorization", f"Bearer {key}")
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return str(json.loads(resp.read()).get("response", "")).strip()

    return explain


def make_explainer(provider: str | None, settings=None):
    if not provider or provider == "none":
        return None
    if provider == "claude":
        return claude_explainer(settings)
    if provider == "ollama":
        return ollama_explainer()
    raise ValueError(f"unknown explainer {provider!r}: none | claude | ollama")
