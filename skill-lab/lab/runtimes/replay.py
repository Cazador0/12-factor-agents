"""Record model-runtime turns during a live run, and replay them later (``--runtime replay``).

The cassette key is the turn's input (system prompt, user prompt, output
schema, model), not the wire format, so a turn recorded on any runtime
(Ollama local or cloud, Claude Code, Codex) replays without that runtime. A
replayed result keeps the recorded runtime name and model in ``raw_meta``.
Replay never fabricates: an unrecorded turn raises ``CassetteMiss``.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

from . import LIVE_PREREQ_MISSING, Runtime, RuntimeCallError, RuntimeResult
from ..cassette import RUNTIME_KIND, Cassette


def turn_request(
    system_prompt: str, user_prompt: str, output_schema: Optional[dict], model: Optional[str]
) -> Dict[str, Any]:
    return {"system": system_prompt, "user": user_prompt, "output_schema": output_schema, "model": model}


class RecordingRuntime(Runtime):
    """Wraps a live runtime and saves every successful turn in ``cassette``."""

    def __init__(self, inner: Runtime, cassette: Cassette, *, recorded_at: str) -> None:
        self.inner = inner
        self.cassette = cassette
        self.recorded_at = recorded_at
        self.name = inner.name
        self.model = inner.model

    def available(self) -> Tuple[bool, str]:
        return self.inner.available()

    def run(
        self, system_prompt: str, user_prompt: str, output_schema: Optional[dict], *, timeout: float
    ) -> RuntimeResult:
        result = self.inner.run(system_prompt, user_prompt, output_schema, timeout=timeout)
        response = {
            "text": result.text,
            "json": result.json_or_none,
            "usage": result.usage,
            "raw_meta": result.raw_meta,
        }
        self.cassette.save(
            RUNTIME_KIND,
            turn_request(system_prompt, user_prompt, output_schema, self.model),
            response,
            recorded_at=self.recorded_at,
            meta={"runtime": self.inner.name, "model": self.model},
        )
        return result


class ReplayRuntime(Runtime):
    name = "replay"

    def __init__(self, cassette: Cassette, *, model: Optional[str] = None) -> None:
        self.cassette = cassette
        self.model = model

    def available(self) -> Tuple[bool, str]:
        if self.cassette.count(RUNTIME_KIND) == 0:
            return False, "%s: no recorded runtime turns in %s" % (LIVE_PREREQ_MISSING, self.cassette.root)
        return True, "ok"

    def run(
        self, system_prompt: str, user_prompt: str, output_schema: Optional[dict], *, timeout: float
    ) -> RuntimeResult:
        """The recorded result; raises ``CassetteMiss`` when this turn was never recorded."""
        entry = self.cassette.load(RUNTIME_KIND, turn_request(system_prompt, user_prompt, output_schema, self.model))
        response, meta = entry["response"], entry.get("meta") or {}
        if not isinstance(response.get("text"), str):
            raise RuntimeCallError("RUNTIME_PROTOCOL", "recorded turn has no text")
        raw_meta = dict(response.get("raw_meta") or {})
        raw_meta.update(
            {"replayed": True, "recorded_runtime": meta.get("runtime"), "recorded_at": entry.get("recorded_at")}
        )
        usage = response.get("usage") if isinstance(response.get("usage"), dict) else {}
        return RuntimeResult(response["text"], response.get("json"), usage, raw_meta)


__all__ = ["RecordingRuntime", "ReplayRuntime", "turn_request"]
