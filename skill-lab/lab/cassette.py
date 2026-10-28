"""Record and replay Jev and model-runtime exchanges as JSON files (SPEC-102, SPEC-103).

A cassette is a directory. Each exchange is one file
``<root>/<kind>/<64 hex>.json`` whose name is the SHA-256 of the canonical
request: for HTTP (``kind = "jev-http"``) the method, URL path and JSON body,
never the headers, so credentials are not part of the key; for model runtimes
(``kind = "runtime"``) the system prompt, user prompt, output schema and model.

Replay never invents an answer: a request that was not recorded raises
``CassetteMiss``, and the caller reports the case as skipped. Everything
written is passed through ``_skillkit.redact`` first, and ``aliases`` replace
machine-specific path prefixes (the repository root) with a placeholder, so a
cassette recorded on one machine replays on another and leaks no local paths.
Credential-named keys are masked by redaction, so judgment IDs must not
contain words such as ``token``, ``auth`` or ``secret``.
"""

from __future__ import annotations

import os
from typing import Any, Dict, Mapping, Optional

from _skillkit import cli, fsutil, ids
from _skillkit.redact import redact

from .runtimes.transport import HttpRequest, HttpResponse, Transport, url_path

CASSETTE_FORMAT = 1
HTTP_KIND = "jev-http"
RUNTIME_KIND = "runtime"
_RECORDED_HEADERS = ("content-type", "x-typesafe-request-id", "retry-after", "retry-after-ms")


class CassetteMiss(LookupError):
    """The request was never recorded; replay refuses to make up a response."""

    def __init__(self, kind: str, key: str) -> None:
        super().__init__("no recorded %s exchange for %s" % (kind, key))
        self.kind = kind
        self.key = key


class CassetteError(ValueError):
    """A cassette file exists but is not a usable recording."""


class Cassette:
    """One cassette directory; ``aliases`` maps local path prefixes to placeholders."""

    def __init__(self, root: str, *, aliases: Optional[Mapping[str, str]] = None) -> None:
        self.root = os.path.abspath(root)
        self.aliases = dict(sorted((aliases or {}).items(), key=lambda item: -len(item[0])))

    def normalize(self, obj: Any) -> Any:
        """``obj`` with aliases applied to every string and secrets redacted."""
        return redact(self._alias(obj))

    def key(self, kind: str, request: Any) -> str:
        return ids.digest({"kind": kind, "request": self.normalize(request)})

    def path_for(self, kind: str, key: str) -> str:
        return os.path.join(self.root, kind, key.split(":", 1)[1] + ".json")

    def load(self, kind: str, request: Any) -> Dict[str, Any]:
        """The recorded entry for ``request``; raises ``CassetteMiss`` or ``CassetteError``."""
        key = self.key(kind, request)
        path = self.path_for(kind, key)
        if not os.path.isfile(path):
            raise CassetteMiss(kind, key)
        try:
            with open(path, "r", encoding="utf-8") as handle:
                entry = cli.loads_strict(handle.read())
        except (OSError, ValueError) as exc:
            raise CassetteError("unreadable cassette entry %s: %s" % (path, exc)) from None
        if not isinstance(entry, dict) or entry.get("cassette_format") != CASSETTE_FORMAT or entry.get("key") != key:
            raise CassetteError("cassette entry %s has the wrong format or key" % path)
        if not isinstance(entry.get("response"), dict):
            raise CassetteError("cassette entry %s has no response object" % path)
        return entry

    def save(
        self, kind: str, request: Any, response: Dict[str, Any], *, recorded_at: str, meta: Optional[dict] = None
    ) -> str:
        """Write one redacted entry atomically and return its path (a later save of the same request wins)."""
        key = self.key(kind, request)
        entry = {
            "cassette_format": CASSETTE_FORMAT,
            "kind": kind,
            "key": key,
            "recorded_at": recorded_at,
            "request": self.normalize(request),
            "response": self.normalize(response),
            "meta": self.normalize(meta or {}),
        }
        path = self.path_for(kind, key)
        fsutil.atomic_write_json(path, entry)
        return path

    def count(self, kind: str) -> int:
        directory = os.path.join(self.root, kind)
        if not os.path.isdir(directory):
            return 0
        return sum(1 for name in os.listdir(directory) if name.endswith(".json"))

    def _alias(self, obj: Any) -> Any:
        if isinstance(obj, str):
            for prefix, placeholder in self.aliases.items():
                obj = obj.replace(prefix, placeholder)
            return obj
        if isinstance(obj, dict):
            return {self._alias(key): self._alias(value) for key, value in obj.items()}
        if isinstance(obj, (list, tuple)):
            return [self._alias(item) for item in obj]
        return obj


class CassetteTransport:
    """An HTTP transport that records through ``inner`` (``mode="record"``) or replays (``mode="replay"``)."""

    def __init__(
        self, cassette: Cassette, *, mode: str, inner: Optional[Transport] = None, recorded_at: str = ""
    ) -> None:
        if mode not in ("record", "replay"):
            raise ValueError("mode must be 'record' or 'replay'")
        if mode == "record" and inner is None:
            raise ValueError("record mode needs the real transport")
        self.cassette = cassette
        self.mode = mode
        self.inner = inner
        self.recorded_at = recorded_at

    def __call__(self, request: HttpRequest) -> HttpResponse:
        key_request = http_key_request(request)
        if self.mode == "replay":
            stored = self.cassette.load(HTTP_KIND, key_request)["response"]
            return _response_from_entry(stored)
        response = self.inner(request)
        self.cassette.save(HTTP_KIND, key_request, _response_to_entry(response), recorded_at=self.recorded_at)
        return response


def http_key_request(request: HttpRequest) -> Dict[str, Any]:
    """What identifies an HTTP exchange: method, path and body (headers and host excluded)."""
    return {"method": request.method.upper(), "path": url_path(request.url), "body": _decode_body(request.body)}


def _decode_body(body: Optional[bytes]) -> Any:
    if body is None:
        return None
    text = body.decode("utf-8", "replace")
    try:
        return {"json": cli.loads_strict(text)}
    except ValueError:
        return {"text": text}


def _response_to_entry(response: HttpResponse) -> Dict[str, Any]:
    headers = {name: response.headers[name] for name in _RECORDED_HEADERS if name in response.headers}
    return {"status": response.status, "headers": headers, "body": _decode_body(response.body)}


def _response_from_entry(stored: Dict[str, Any]) -> HttpResponse:
    status, headers, body = stored.get("status"), stored.get("headers"), stored.get("body")
    if not isinstance(status, int) or not isinstance(headers, dict):
        raise CassetteError("recorded HTTP response has no status or headers")
    if body is None:
        raw = b""
    elif isinstance(body, dict) and "json" in body:
        raw = ids.canonical_json(body["json"]).encode("utf-8")
    elif isinstance(body, dict) and isinstance(body.get("text"), str):
        raw = body["text"].encode("utf-8")
    else:
        raise CassetteError("recorded HTTP body has an unknown shape")
    return HttpResponse(status, {str(k).lower(): str(v) for k, v in headers.items()}, raw)
