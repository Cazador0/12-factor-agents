"""TypeSafe System One ("Jev") client and judgment builders (SPEC-103).

Wire format, from the official SDK's generated models (vendored at
``docs/research/vendor/typesafe-wire-models.py``)::

    POST {base}/v1/systemone   {"model", "state", "questions": {name: Question}}
      -> 200 {"model", "answers": {name: Answer}, "usage": {"input_tokens", "output_tokens"}}
      -> 422 {"detail": [{"loc", "msg", "type"}]}
    GET  {base}/v1/models      -> {"models": [{"name", "description", "release_date"}]}

Configuration comes from the environment: ``TYPESAFE_BASE_URL`` (default
``https://api.typesafe.ai``), ``TYPESAFE_API_KEY`` or, failing that,
``JEV_API_KEY``, and ``TYPESAFE_DEFAULT_MODEL`` (default ``jev-latest``).
Requests send ``Authorization: Bearer``, JSON ``Content-Type``/``Accept`` and
``User-Agent: skill-lab/<version>``; retries cover 429/500/502/503/504 and
connection errors, honouring ``retry-after-ms``/``retry-after``. The key is
never logged or put in an error message.

Answers are parsed into ``NoulAnswer``, ``ChoiceAnswer`` and ``ScoreAnswer``
and checked strictly: every question answered exactly once, with the
question's type, finite probabilities in [0, 1], and a choice that is one of
the question's labels. Anything else is a ``JevProtocolError``; typed output
guarantees the interface, never the truth of an answer.
"""

from __future__ import annotations

import dataclasses
import math
import os
import time
from typing import Any, Callable, Dict, List, Mapping, Optional, Sequence, Tuple

from _skillkit import cli
from _skillkit.envelope import compact
from _skillkit.redact import redact_text

from .runtimes.transport import (
    RetryPolicy,
    Transport,
    TransportError,
    json_request,
    send_with_retries,
    urllib_transport,
)

DEFAULT_BASE_URL = "https://api.typesafe.ai"
DEFAULT_MODEL = "jev-latest"
DEFAULT_TIMEOUT = 30.0
SYSTEM_ONE_PATH = "/v1/systemone"
MODELS_PATH = "/v1/models"
REQUEST_ID_HEADER = "x-typesafe-request-id"
RETRY_COUNT_HEADER = "X-TypeSafe-Retry-Count"
API_KEY_ENV_VARS = ("TYPESAFE_API_KEY", "JEV_API_KEY")
BASE_URL_ENV = "TYPESAFE_BASE_URL"
MODEL_ENV = "TYPESAFE_DEFAULT_MODEL"
QUESTION_TYPES = ("noul", "choice", "score")
NONE_LABEL = "none"
"""The routing choice meaning "no installed skill fits"."""
DEFAULT_RETRY = RetryPolicy()
"""Up to 3 retries on 429/500/502/503/504 and connection errors."""
_SCORE_TOLERANCE = 1e-6
"""Float slack when checking that an expected score lies within its levels."""


# ---------------------------------------------------------------------------
# Typed answers
# ---------------------------------------------------------------------------


@dataclasses.dataclass(frozen=True)
class NoulAnswer:
    noul: float
    """Probability of yes / true, 0..1; near 0.5 means uncertain."""
    type = "noul"


@dataclasses.dataclass(frozen=True)
class ChoiceAnswer:
    choice: str
    confidence: float
    probabilities: Dict[str, float]
    type = "choice"


@dataclasses.dataclass(frozen=True)
class ScoreAnswer:
    score: float
    """Probability-weighted average of the 0-based levels."""
    confidence: float
    legend: Dict[str, Any]
    probabilities: Dict[str, float]
    type = "score"


Answer = Any  # NoulAnswer | ChoiceAnswer | ScoreAnswer (runtime unions need Python 3.10)


@dataclasses.dataclass(frozen=True)
class Usage:
    input_tokens: int
    output_tokens: int


@dataclasses.dataclass(frozen=True)
class SystemOneResult:
    model: str
    answers: Dict[str, Answer]
    usage: Usage
    request_id: Optional[str]


@dataclasses.dataclass(frozen=True)
class ModelInfo:
    name: str
    description: str
    release_date: str


# ---------------------------------------------------------------------------
# Errors
# ---------------------------------------------------------------------------


class JevError(Exception):
    """Base class; ``code`` is the compact error code bench reports."""

    code = "JEV_ERROR"

    def __init__(self, message: str, *, status: Optional[int] = None, request_id: Optional[str] = None) -> None:
        self.message = compact(redact_text(message), 300)
        self.status = status
        self.request_id = request_id
        suffix = " (request_id=%s)" % request_id if request_id else ""
        super().__init__(self.message + suffix)


class JevConfigError(JevError):
    """No usable API key (or another configuration problem); nothing was sent."""

    code = "JEV_NOT_CONFIGURED"


class JevConnectionError(JevError):
    """No HTTP response after the retries (DNS, refused, timeout, reset)."""

    code = "JEV_UNREACHABLE"


class JevAuthError(JevError):
    """HTTP 401 or 403: the key is missing, wrong or not allowed."""

    code = "JEV_AUTH"


class JevValidationError(JevError):
    """HTTP 422: the API rejected the request; ``detail`` lists ``{loc, msg, type}``."""

    code = "JEV_REQUEST_INVALID"

    def __init__(self, message: str, detail: List[Dict[str, Any]], **kwargs: Any) -> None:
        super().__init__(message, **kwargs)
        self.detail = detail


class JevHTTPError(JevError):
    """Any other non-200 status, including retryable ones after the retries ran out."""

    code = "JEV_HTTP_ERROR"


class JevProtocolError(JevError):
    """A 200 response whose body does not match the wire models."""

    code = "JEV_PROTOCOL"


# ---------------------------------------------------------------------------
# Client
# ---------------------------------------------------------------------------


def resolve_api_key(environ: Optional[Mapping[str, str]] = None) -> Optional[str]:
    """``TYPESAFE_API_KEY``, else ``JEV_API_KEY`` ("the Jev API key"), stripped; None when neither is set."""
    environ = os.environ if environ is None else environ
    for name in API_KEY_ENV_VARS:
        value = environ.get(name, "").strip()
        if value:
            return value
    return None


def settings_from_env(environ: Optional[Mapping[str, str]] = None) -> Dict[str, str]:
    """``base_url`` from ``TYPESAFE_BASE_URL`` and ``model`` from ``TYPESAFE_DEFAULT_MODEL``, with defaults."""
    environ = os.environ if environ is None else environ
    return {
        "base_url": environ.get(BASE_URL_ENV, "").strip() or DEFAULT_BASE_URL,
        "model": environ.get(MODEL_ENV, "").strip() or DEFAULT_MODEL,
    }


class JevClient:
    """Synchronous System One client over an injectable transport."""

    def __init__(
        self,
        api_key: Optional[str],
        *,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout: float = DEFAULT_TIMEOUT,
        retry: RetryPolicy = DEFAULT_RETRY,
        transport: Optional[Transport] = None,
        sleep: Callable[[float], None] = time.sleep,
        log: Optional[Callable[[str], None]] = cli.log,
    ) -> None:
        """``api_key`` None sends no ``Authorization`` header (only for replay transports)."""
        if api_key is not None and (not api_key.isascii() or not api_key.isprintable() or " " in api_key):
            raise JevConfigError("the Jev API key must be printable ASCII without spaces")
        if not (math.isfinite(timeout) and timeout > 0):
            raise JevConfigError("timeout must be a positive number of seconds")
        self._api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._retry = retry
        self._transport = transport or urllib_transport
        self._sleep = sleep
        self._log = log

    @classmethod
    def from_env(cls, environ: Optional[Mapping[str, str]] = None, **kwargs: Any) -> "JevClient":
        """Configure from the environment; raises ``JevConfigError`` when no key is set."""
        key = resolve_api_key(environ)
        if key is None:
            raise JevConfigError("set TYPESAFE_API_KEY (or JEV_API_KEY) to use Jev")
        for name, value in settings_from_env(environ).items():
            kwargs.setdefault(name, value)
        return cls(key, **kwargs)

    def ask(
        self, state: Any, questions: Mapping[str, Mapping[str, Any]], *, model: Optional[str] = None
    ) -> SystemOneResult:
        """Ask every question about ``state`` in one request (the API answers them in parallel)."""
        check_questions(questions)
        body = {"model": model or self.model, "state": state, "questions": dict(questions)}
        data, request_id = self._call("POST", SYSTEM_ONE_PATH, body, policy=self._retry)
        return parse_system_one(data, questions, request_id)

    def list_models(self, *, timeout: Optional[float] = None, retry: Optional[RetryPolicy] = None) -> List[ModelInfo]:
        """``GET /v1/models``; also the cheap reachability probe bench uses."""
        data, request_id = self._call("GET", MODELS_PATH, None, policy=retry or self._retry, timeout=timeout)
        return parse_models(data, request_id)

    def _call(
        self, method: str, path: str, body: Any, *, policy: RetryPolicy, timeout: Optional[float] = None
    ) -> Tuple[Any, Optional[str]]:
        headers = {"Authorization": "Bearer " + self._api_key} if self._api_key else {}
        request = json_request(method, self.base_url + path, body, headers=headers, timeout=timeout or self.timeout)
        try:
            response = send_with_retries(
                self._transport,
                request,
                policy=policy,
                sleep=self._sleep,
                retry_header=RETRY_COUNT_HEADER,
                on_retry=self._on_retry(method, path, policy),
            )
        except TransportError as exc:
            raise JevConnectionError(self._scrub("%s %s failed: %s" % (method, path, exc))) from None
        request_id = response.header(REQUEST_ID_HEADER)
        decoded = _decode(response.body)
        if response.status == 200:
            if decoded is _UNDECODABLE:
                raise JevProtocolError("%s %s returned a body that is not JSON" % (method, path), request_id=request_id)
            return decoded, request_id
        message = self._scrub("%s %s returned HTTP %d: %s" % (method, path, response.status, _server_message(decoded)))
        if response.status in (401, 403):
            raise JevAuthError(message, status=response.status, request_id=request_id)
        if response.status == 422:
            raise JevValidationError(message, _detail(decoded), status=422, request_id=request_id)
        raise JevHTTPError(message, status=response.status, request_id=request_id)

    def _scrub(self, text: str) -> str:
        """Mask this client's own key, which ``redact`` only knows when it came from the environment."""
        return text.replace(self._api_key, "***") if self._api_key else text

    def _on_retry(self, method: str, path: str, policy: RetryPolicy) -> Optional[Callable[[int, float, str], None]]:
        if self._log is None:
            return None
        log = self._log
        return lambda attempt, delay, reason: log(
            "jev: %s %s %s; retry %d/%d in %.1fs" % (method, path, reason, attempt, policy.max_retries, delay)
        )


# ---------------------------------------------------------------------------
# Request and response checking
# ---------------------------------------------------------------------------


def check_questions(questions: Mapping[str, Mapping[str, Any]]) -> None:
    """Refuse requests the API would reject with 422, before spending a call."""
    if not isinstance(questions, Mapping) or not questions:
        raise JevConfigError("a System One request needs at least one question")
    for name, question in questions.items():
        kind = question.get("type") if isinstance(question, Mapping) else None
        if kind not in QUESTION_TYPES:
            raise JevConfigError("question %r has unsupported type %r" % (name, kind))
        criteria = question.get("criteria")
        if kind == "choice" and (not isinstance(criteria, Mapping) or not criteria):
            raise JevConfigError("choice question %r needs a non-empty criteria map" % name)
        if kind == "score" and (not isinstance(criteria, list) or not criteria):
            raise JevConfigError("score question %r needs a non-empty criteria list" % name)


def parse_system_one(
    data: Any, questions: Mapping[str, Mapping[str, Any]], request_id: Optional[str]
) -> SystemOneResult:
    """Strictly convert a 200 body into typed answers matching ``questions``."""
    fail = _protocol(request_id)
    if not isinstance(data, dict):
        raise fail("response body is not an object")
    model, answers, usage = data.get("model"), data.get("answers"), data.get("usage")
    if not isinstance(model, str):
        raise fail("response has no model string")
    if not isinstance(answers, dict) or not answers:
        raise fail("response has no answers object")
    if set(answers) != set(questions):
        missing, extra = sorted(set(questions) - set(answers)), sorted(set(answers) - set(questions))
        raise fail("answers do not match the questions (missing %s, unexpected %s)" % (missing, extra))
    parsed = {name: _parse_answer(name, answers[name], questions[name], fail) for name in sorted(answers)}
    if not isinstance(usage, dict) or not all(_is_count(usage.get(key)) for key in ("input_tokens", "output_tokens")):
        raise fail("response has no usage {input_tokens, output_tokens}")
    return SystemOneResult(model, parsed, Usage(usage["input_tokens"], usage["output_tokens"]), request_id)


def parse_models(data: Any, request_id: Optional[str] = None) -> List[ModelInfo]:
    fail = _protocol(request_id)
    models = data.get("models") if isinstance(data, dict) else None
    if not isinstance(models, list):
        raise fail("models response has no models list")
    result = []
    for entry in models:
        fields = [
            entry.get(key) if isinstance(entry, dict) else None for key in ("name", "description", "release_date")
        ]
        if not all(isinstance(value, str) for value in fields):
            raise fail("model entry needs name, description and release_date strings")
        result.append(ModelInfo(*fields))
    return result


def _parse_answer(
    name: str, answer: Any, question: Mapping[str, Any], fail: Callable[[str], JevProtocolError]
) -> Answer:
    if not isinstance(answer, dict):
        raise fail("answer %r is not an object" % name)
    kind = answer.get("type")
    if kind not in QUESTION_TYPES:
        raise fail("answer %r has unknown type %r" % (name, kind))
    if kind != question.get("type"):
        raise fail("answer %r has type %r but the question is %r" % (name, kind, question.get("type")))
    if kind == "noul":
        return NoulAnswer(_probability(answer.get("noul"), "%s.noul" % name, fail))
    confidence = _probability(answer.get("confidence"), "%s.confidence" % name, fail)
    probabilities = _probability_map(answer.get("probabilities"), "%s.probabilities" % name, fail)
    if kind == "choice":
        choice = answer.get("choice")
        labels = set(question.get("criteria") or {})
        if not isinstance(choice, str) or choice not in labels:
            raise fail("answer %r chose %r, which is not one of the question's labels" % (name, choice))
        return ChoiceAnswer(choice, confidence, probabilities)
    score, legend = answer.get("score"), answer.get("legend")
    top = max(len(question.get("criteria") or []) - 1, 0)
    if not _is_number(score) or not -_SCORE_TOLERANCE <= score <= top + _SCORE_TOLERANCE:
        raise fail("answer %r has score %r outside 0..%d" % (name, score, top))
    if not isinstance(legend, dict):
        raise fail("answer %r has no legend object" % name)
    return ScoreAnswer(float(score), confidence, legend, probabilities)


def _probability(value: Any, where: str, fail: Callable[[str], JevProtocolError]) -> float:
    if not _is_number(value) or not 0.0 <= value <= 1.0:
        raise fail("%s must be a number in [0, 1], got %r" % (where, value))
    return float(value)


def _probability_map(value: Any, where: str, fail: Callable[[str], JevProtocolError]) -> Dict[str, float]:
    if not isinstance(value, dict):
        raise fail("%s must be an object" % where)
    return {str(key): _probability(item, "%s.%s" % (where, key), fail) for key, item in value.items()}


def _is_number(value: Any) -> bool:
    return isinstance(value, (int, float)) and not isinstance(value, bool) and math.isfinite(value)


def _is_count(value: Any) -> bool:
    return isinstance(value, int) and not isinstance(value, bool) and value >= 0


def _protocol(request_id: Optional[str]) -> Callable[[str], JevProtocolError]:
    return lambda message: JevProtocolError(message, request_id=request_id)


_UNDECODABLE = object()


def _decode(body: bytes) -> Any:
    if not body:
        return None
    try:
        return cli.loads_strict(body.decode("utf-8"))
    except (UnicodeDecodeError, ValueError):
        return _UNDECODABLE


def _server_message(body: Any) -> str:
    """The server's error text, the way the SDK's ``extract_message`` finds it."""
    if body is None:
        return "(no body)"
    if body is _UNDECODABLE:
        return "(non-JSON body)"
    if isinstance(body, dict):
        for key in ("error", "message", "detail"):
            value = body.get(key)
            if isinstance(value, str):
                return value
            if isinstance(value, dict) and isinstance(value.get("message"), str):
                return value["message"]
        if isinstance(body.get("detail"), list):
            return "; ".join(_format_detail(entry) for entry in _detail(body)) or "(no detail)"
    return compact(str(body), 200)


def _detail(body: Any) -> List[Dict[str, Any]]:
    entries = body.get("detail") if isinstance(body, dict) else None
    if not isinstance(entries, list):
        return []
    return [
        {"loc": entry.get("loc"), "msg": entry.get("msg"), "type": entry.get("type")}
        for entry in entries
        if isinstance(entry, dict)
    ]


def _format_detail(entry: Dict[str, Any]) -> str:
    loc = entry.get("loc")
    path = ".".join(str(part) for part in loc if part != "body") if isinstance(loc, list) else ""
    return "%s: %s" % (path, entry.get("msg")) if path else str(entry.get("msg"))


# ---------------------------------------------------------------------------
# Building questions and state from benchmark cases
# ---------------------------------------------------------------------------


def question_for(judgment: Mapping[str, Any]) -> Dict[str, Any]:
    """The System One question for one benchmark-case judgment (its ``id`` is the question name)."""
    return {"type": judgment["type"], "instructions": judgment["instructions"], "criteria": judgment["criteria"]}


def judgment_batches(judgments: Sequence[Mapping[str, Any]]) -> List[Tuple[Tuple[str, ...], List[Mapping[str, Any]]]]:
    """Group judgments by their ``state_from`` set, in first-seen order.

    Each group becomes one request, so every judgment sees exactly the state
    it declared; cases whose judgments share ``state_from`` (the usual case)
    make a single request.
    """
    groups: Dict[Tuple[str, ...], List[Mapping[str, Any]]] = {}
    for judgment in judgments:
        groups.setdefault(tuple(sorted(judgment["state_from"])), []).append(judgment)
    return list(groups.items())


def build_state(
    state_from: Sequence[str],
    *,
    skill: Mapping[str, Any],
    prompt: Optional[str],
    fixtures: Mapping[str, Any],
    output: Any,
) -> Dict[str, Any]:
    """``{"skill", "prompt", "fixtures", "output"}`` restricted to ``state_from``, in that key order."""
    available = {"skill": dict(skill), "prompt": prompt, "fixtures": dict(fixtures), "output": output}
    return {key: available[key] for key in ("skill", "prompt", "fixtures", "output") if key in state_from}


def routing_question(catalog: Sequence[Tuple[str, str]]) -> Dict[str, Any]:
    """A choice question over every catalog skill plus ``none`` (question IDs are not sent, so this says it all)."""
    names = [name for name, _ in catalog]
    if NONE_LABEL in names:
        raise JevConfigError("a skill named %r collides with the routing label for no skill" % NONE_LABEL)
    criteria: Dict[str, Any] = {name: description for name, description in catalog}
    criteria[NONE_LABEL] = "No installed skill fits this request"
    return {
        "type": "choice",
        "instructions": (
            "The state is a request a user typed to an AI coding agent. The agent has the installed skills "
            "listed as choices, each with its description. Choose the one skill the agent should load to handle "
            "this request, judging only by the descriptions. Choose 'none' when no installed skill fits."
        ),
        "criteria": criteria,
    }
