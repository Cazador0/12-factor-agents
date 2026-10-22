"""HTTP plumbing shared by the Jev client and the Ollama runtimes (stdlib ``urllib``).

A *transport* is any callable ``(HttpRequest) -> HttpResponse``.
``urllib_transport`` is the real one; tests inject fakes or point it at a local
``http.server``, and ``lab.cassette.CassetteTransport`` records or replays it.
Every HTTP status, including 4xx and 5xx, comes back as an ``HttpResponse``;
only a failure to get any response at all (refused connection, DNS failure,
timeout, reset) raises ``TransportError``.

``send_with_retries`` adds bounded, deterministic retries: exponential backoff
without jitter (CONVENTIONS §3 forbids randomness), honouring ``retry-after-ms``
and ``retry-after`` hints the way the official TypeSafe SDK does
(``typesafe_sdk/_core/errors.py::parse_retry_after``).
"""

from __future__ import annotations

import datetime as _dt
import email.utils
import http.client
import json
import math
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Any, Callable, Dict, Iterable, Mapping, NamedTuple, Optional, Tuple

from lab import LAB_VERSION

USER_AGENT = "skill-lab/" + LAB_VERSION
JSON_CONTENT_TYPE = "application/json"
RETRY_STATUSES = frozenset({429, 500, 502, 503, 504})
MAX_RESPONSE_BYTES = 16 * 1024 * 1024
_LOOPBACK_HOSTS = frozenset({"localhost", "127.0.0.1", "::1"})
_TIMEOUTS = (socket.timeout, TimeoutError)  # distinct classes on Python 3.9, aliases from 3.10


class HttpRequest(NamedTuple):
    method: str
    url: str
    headers: Mapping[str, str]
    body: Optional[bytes] = None
    timeout: float = 30.0


class HttpResponse(NamedTuple):
    status: int
    headers: Mapping[str, str]
    """Header names are lower-case."""
    body: bytes

    def header(self, name: str) -> Optional[str]:
        return self.headers.get(name.lower())


class TransportError(Exception):
    """No HTTP response was received (connection refused, DNS, timeout, reset)."""

    def __init__(self, message: str, *, timeout: bool = False) -> None:
        super().__init__(message)
        self.timeout = timeout


Transport = Callable[[HttpRequest], HttpResponse]


class RetryPolicy(NamedTuple):
    """Bounded retries: ``max_retries`` after the first attempt."""

    max_retries: int = 3
    backoff_initial: float = 0.5
    backoff_max: float = 8.0
    max_retry_after: float = 60.0
    """A server hint longer than this ends the retries instead of stalling the run."""
    statuses: frozenset = RETRY_STATUSES


NO_RETRY = RetryPolicy(max_retries=0)


def urllib_transport(request: HttpRequest) -> HttpResponse:
    """Send ``request`` with ``urllib``; proxies from the environment apply except for loopback hosts."""
    prepared = urllib.request.Request(
        request.url, data=request.body, method=request.method, headers=dict(request.headers)
    )
    try:
        with _opener_for(request.url).open(prepared, timeout=request.timeout) as response:
            return HttpResponse(response.status, _lower_headers(response.headers.items()), _read_capped(response))
    except urllib.error.HTTPError as exc:
        headers = _lower_headers(exc.headers.items()) if exc.headers is not None else {}
        try:
            body = _read_capped(exc)
        except (OSError, http.client.HTTPException, TransportError):
            body = b""
        return HttpResponse(exc.code, headers, body)
    except urllib.error.URLError as exc:
        raise TransportError(_describe(exc.reason), timeout=isinstance(exc.reason, _TIMEOUTS)) from None
    except (OSError, http.client.HTTPException) as exc:
        raise TransportError(_describe(exc), timeout=isinstance(exc, _TIMEOUTS)) from None


def send_with_retries(
    transport: Transport,
    request: HttpRequest,
    *,
    policy: RetryPolicy,
    sleep: Callable[[float], None],
    retry_header: Optional[str] = None,
    on_retry: Optional[Callable[[int, float, str], None]] = None,
) -> HttpResponse:
    """Send ``request``, retrying retryable statuses and transport errors.

    Returns the first non-retryable response, or the last response once the
    retries are spent. Re-raises the last ``TransportError`` when no attempt
    got a response. ``retry_header`` names a header that carries the retry
    count on retried attempts (the TypeSafe SDK sends ``X-TypeSafe-Retry-Count``).
    ``on_retry(attempt, delay, reason)`` is called before each wait.
    """
    attempt = 0
    while True:
        headers = dict(request.headers)
        if attempt and retry_header:
            headers[retry_header] = str(attempt)
        try:
            response = transport(request._replace(headers=headers))
        except TransportError as exc:
            if attempt >= policy.max_retries:
                raise
            delay, reason = backoff_delay(attempt + 1, policy), str(exc)
        else:
            if response.status not in policy.statuses or attempt >= policy.max_retries:
                return response
            hinted = parse_retry_after(response.headers)
            if hinted is not None and hinted > policy.max_retry_after:
                return response
            delay = backoff_delay(attempt + 1, policy) if hinted is None else hinted
            reason = "HTTP %d" % response.status
        attempt += 1
        if on_retry is not None:
            on_retry(attempt, delay, reason)
        sleep(delay)


def backoff_delay(attempt: int, policy: RetryPolicy) -> float:
    """Delay before retry number ``attempt`` (1-based): initial * 2^(attempt-1), capped."""
    return min(policy.backoff_max, policy.backoff_initial * (2 ** (attempt - 1)))


def parse_retry_after(headers: Mapping[str, str], now: Optional[_dt.datetime] = None) -> Optional[float]:
    """Seconds the server asks us to wait, from ``retry-after-ms`` or ``retry-after``; None without a usable hint."""
    raw_ms = headers.get("retry-after-ms")
    if raw_ms is not None:
        value = _finite_float(raw_ms)
        if value is not None and value >= 0:
            return value / 1000.0
    raw = headers.get("retry-after")
    if raw is None:
        return None
    seconds = _finite_float(raw)
    if seconds is not None:
        return seconds if seconds >= 0 else None
    try:
        when = email.utils.parsedate_to_datetime(raw)
    except (TypeError, ValueError, IndexError):
        return None
    if when is None:
        return None
    if when.tzinfo is None:
        when = when.replace(tzinfo=_dt.timezone.utc)
    current = now or _dt.datetime.now(_dt.timezone.utc)
    return max(0.0, (when - current).total_seconds())


def json_request(method: str, url: str, payload: Any, *, headers: Mapping[str, str], timeout: float) -> HttpRequest:
    """Build a request with a compact UTF-8 JSON body (``payload`` None sends no body)."""
    merged = {"Accept": JSON_CONTENT_TYPE, "User-Agent": USER_AGENT}
    merged.update(headers)
    body = None
    if payload is not None:
        body = json.dumps(payload, ensure_ascii=False, allow_nan=False, separators=(",", ":")).encode("utf-8")
        merged["Content-Type"] = JSON_CONTENT_TYPE
    return HttpRequest(method, url, merged, body, timeout)


def is_loopback(url: str) -> bool:
    """True for http(s) URLs whose host is localhost, 127.0.0.1 or ::1."""
    host = urllib.parse.urlsplit(url).hostname or ""
    return host.lower() in _LOOPBACK_HOSTS


def url_path(url: str) -> str:
    """The path of ``url`` (no scheme, host, query or credentials), for logs and cassette keys."""
    return urllib.parse.urlsplit(url).path or "/"


_OPENERS: Dict[bool, urllib.request.OpenerDirector] = {}


def _opener_for(url: str) -> urllib.request.OpenerDirector:
    """A direct opener for loopback hosts (a stray HTTP_PROXY must not capture localhost), else the default."""
    loopback = is_loopback(url)
    if loopback not in _OPENERS:
        handlers = (urllib.request.ProxyHandler({}),) if loopback else ()
        _OPENERS[loopback] = urllib.request.build_opener(*handlers)
    return _OPENERS[loopback]


def _read_capped(response: Any) -> bytes:
    data = response.read(MAX_RESPONSE_BYTES + 1)
    if len(data) > MAX_RESPONSE_BYTES:
        raise TransportError("response body exceeds %d bytes" % MAX_RESPONSE_BYTES)
    return data


def _lower_headers(items: Iterable[Tuple[str, str]]) -> Dict[str, str]:
    return {name.lower(): value for name, value in items}


def _finite_float(text: str) -> Optional[float]:
    try:
        value = float(text.strip() or "0")
    except ValueError:
        return None
    return value if math.isfinite(value) else None


def _describe(error: Any) -> str:
    if isinstance(error, str):
        return error
    return "%s: %s" % (type(error).__name__, error) if str(error) else type(error).__name__
