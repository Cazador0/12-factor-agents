"""envelope.v1: the single JSON document every skill script prints on stdout.

A script's entry point is usually just::

    def main():
        args = build_parser().parse_args()
        ...
        return EXIT_OK, payload, [], []

    if __name__ == "__main__":
        sys.exit(envelope.run_script(main, skill="review-verifier",
                                     script="review_verdict.py", version="0.1.0",
                                     kind="review-verdict"))

``run_script`` guarantees exactly one envelope on stdout whatever happens:
``ScriptError`` becomes a compact error with its own exit code, argparse
usage errors become ``USAGE`` (exit 2), and any other exception becomes
``INTERNAL`` (exit 2) without a traceback on stdout. Secrets are redacted
before anything is written.
"""

from __future__ import annotations

import datetime as _dt
import json
import os
import re
import sys
import traceback
from typing import Any, Callable, Dict, List, NamedTuple, Optional, Sequence, TextIO, Tuple, Union

from . import EXIT_CODES, EXIT_FAIL, EXIT_OK, EXIT_USAGE
from .redact import redact
from .timeutil import parse_iso8601, to_iso, utc_now

URN_PREFIX = "urn:skill-lab:schema:"
ENVELOPE_SCHEMA = URN_PREFIX + "envelope:v1"
MAX_MESSAGE_LENGTH = 300

_CODE_RE = re.compile(r"^[A-Z][A-Z0-9_]*$")
_KIND_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")

Message = Dict[str, Optional[str]]
Now = Union[_dt.datetime, str, None]


def schema_urn(kind: str, version: int = 1) -> str:
    """Return ``urn:skill-lab:schema:<kind>:v<version>``."""
    return "%s%s:v%d" % (URN_PREFIX, kind, version)


def compact(message: Any, limit: int = MAX_MESSAGE_LENGTH) -> str:
    """Collapse whitespace to one line and cap the length (Factor 9)."""
    text = " ".join(str(message).split())
    return text if len(text) <= limit else text[: limit - 3] + "..."


def error(code: str, message: Any, path: Optional[str] = None) -> Message:
    """Build a compact error object ``{"code", "message", "path"}``.

    ``code`` must be UPPER_SNAKE; ``path`` is a JSON Pointer or ``file:line``.
    """
    if not isinstance(code, str) or not _CODE_RE.match(code):
        raise ValueError("error code must be UPPER_SNAKE, got %r" % (code,))
    return {"code": code, "message": compact(message), "path": None if path is None else str(path)}


class ScriptError(Exception):
    """A failure the script reports as one compact error and an exit code.

    ``exit_code`` defaults to 2 (usage or input error). Use 3 for external
    failures, 4 for policy refusals, and 1 only for "checked and failed"
    outcomes that have no payload.
    """

    def __init__(self, code: str, message: Any, path: Optional[str] = None, exit_code: int = EXIT_USAGE) -> None:
        if exit_code not in EXIT_CODES or exit_code == EXIT_OK:
            raise ValueError("ScriptError exit_code must be 1-4, got %r" % (exit_code,))
        self.error = error(code, message, path)
        self.code = code
        self.message = self.error["message"]
        self.path = self.error["path"]
        self.exit_code = exit_code
        super().__init__("%s: %s" % (code, self.message))

    def to_dict(self) -> Message:
        """Return the compact error object."""
        return dict(self.error)


class ScriptResult(NamedTuple):
    """What ``main()`` may return instead of a plain 4-tuple.

    Use it to attach an idempotency key or to override the envelope ``kind``
    (for scripts whose subcommands emit different contracts).
    """

    exit_code: int
    payload: Optional[dict]
    errors: Sequence[Any] = ()
    warnings: Sequence[Any] = ()
    idempotency_key: Optional[str] = None
    kind: Optional[str] = None


def make_envelope(
    kind: str,
    payload: Optional[dict],
    *,
    skill: str,
    script: str,
    version: str,
    ok: bool,
    errors: Optional[Sequence[Any]] = None,
    warnings: Optional[Sequence[Any]] = None,
    idempotency_key: Optional[str] = None,
    now: Now = None,
) -> dict:
    """Build an envelope.v1 document.

    ``errors`` and ``warnings`` accept error objects or bare strings (wrapped
    as ``ERROR`` / ``WARNING``). ``now`` is a datetime, an ISO 8601 string,
    or None for the current UTC time.
    """
    _check_kind(kind)
    return {
        "schema": ENVELOPE_SCHEMA,
        "kind": kind,
        "kind_schema": schema_urn(kind),
        "ok": bool(ok),
        "producer": {"skill": skill, "script": script, "version": version},
        "created_at": _timestamp(now),
        "idempotency_key": idempotency_key,
        "payload": payload,
        "errors": [_message(item, "ERROR") for item in errors or ()],
        "warnings": [_message(item, "WARNING") for item in warnings or ()],
    }


def dumps(envelope: dict, pretty: bool = False) -> str:
    """Serialise deterministically: sorted keys, UTF-8 text, trailing newline.

    Raises ``ValueError``/``TypeError`` for NaN, infinities or objects that
    are not JSON data.
    """
    if pretty:
        text = json.dumps(envelope, sort_keys=True, ensure_ascii=False, allow_nan=False, indent=2)
    else:
        text = json.dumps(envelope, sort_keys=True, ensure_ascii=False, allow_nan=False, separators=(",", ":"))
    return text + "\n"


def emit(envelope: dict, pretty: bool = False, stream: Optional[TextIO] = None) -> None:
    """Write exactly one redacted JSON document to ``stream`` (stdout by default)."""
    _write(dumps(redact(envelope), pretty), stream)


def run_script(
    main: Callable[[], Any],
    *,
    skill: str,
    script: str,
    version: str,
    kind: str,
    argv: Optional[Sequence[str]] = None,
    stream: Optional[TextIO] = None,
) -> int:
    """Run ``main()``, emit one envelope, and return the process exit code.

    ``main()`` returns ``(exit_code, payload, errors, warnings)`` or a
    ``ScriptResult``, or raises ``ScriptError``. ``argv`` (default
    ``sys.argv[1:]``) is only scanned for ``--pretty`` and ``--now`` so the
    envelope honours them even when argument parsing fails. ``ok`` is always
    ``exit_code == 0``; exit 0 must carry a payload object and no errors, and
    exit 1 must carry a payload object.
    """
    _check_kind(kind)
    pretty, now = _scan_output_flags(sys.argv[1:] if argv is None else list(argv))
    common = {"skill": skill, "script": script, "version": version, "now": now}
    try:
        exit_code, envelope = _run_main(main, kind, common)
    except SystemExit as exc:
        if exc.code in (0, None):
            return EXIT_OK  # --help or --version already printed
        exit_code = EXIT_USAGE
        if exc.code == EXIT_USAGE:
            detail = "invalid command-line arguments (see stderr)"
        else:
            detail = "script exited early with status %r" % (exc.code,)
        envelope = make_envelope(kind, None, ok=False, errors=[error("USAGE", detail)], **common)
    try:
        text = dumps(redact(envelope), pretty)
    except (TypeError, ValueError) as exc:
        exit_code = EXIT_USAGE
        failure = error("INTERNAL", "output is not JSON data: %s" % exc)
        text = dumps(redact(make_envelope(kind, None, ok=False, errors=[failure], **common)), pretty)
    _write(text, stream)
    return exit_code


def _run_main(main: Callable[[], Any], kind: str, common: dict) -> Tuple[int, dict]:
    """Call ``main`` and turn its outcome (or failure) into an envelope."""
    try:
        result = _unpack(main())
        envelope = make_envelope(
            result.kind or kind,
            result.payload,
            ok=result.exit_code == EXIT_OK,
            errors=result.errors,
            warnings=result.warnings,
            idempotency_key=result.idempotency_key,
            **common,
        )
        return result.exit_code, envelope
    except ScriptError as exc:
        return exc.exit_code, make_envelope(kind, None, ok=False, errors=[exc.to_dict()], **common)
    except Exception as exc:  # noqa: BLE001 - the INTERNAL contract
        if os.environ.get("SKILLKIT_DEBUG") == "1":
            traceback.print_exc(file=sys.stderr)
        failure = error("INTERNAL", "%s: %s" % (type(exc).__name__, exc))
        return EXIT_USAGE, make_envelope(kind, None, ok=False, errors=[failure], **common)


def _unpack(result: Any) -> ScriptResult:
    if not isinstance(result, ScriptResult):
        if not isinstance(result, (tuple, list)) or len(result) != 4:
            raise TypeError("main() must return (exit_code, payload, errors, warnings) or ScriptResult")
        result = ScriptResult(*result)
    if isinstance(result.exit_code, bool) or result.exit_code not in EXIT_CODES:
        raise TypeError("main() returned invalid exit code %r" % (result.exit_code,))
    if result.payload is not None and not isinstance(result.payload, dict):
        raise TypeError("payload must be a dict or None")
    if result.exit_code in (EXIT_OK, EXIT_FAIL) and result.payload is None:
        raise TypeError("exit code %d requires a payload" % result.exit_code)
    if result.exit_code == EXIT_OK and result.errors:
        raise TypeError("exit code 0 must not carry errors")
    if result.kind is not None:
        _check_kind(result.kind)
    return result


def _scan_output_flags(argv: List[str]) -> Tuple[bool, Now]:
    """Find ``--pretty`` and ``--now`` without full parsing; a bad ``--now`` is ignored here."""
    pretty = False
    now_text = None
    for index, arg in enumerate(argv):
        if arg == "--pretty":
            pretty = True
        elif arg == "--now" and index + 1 < len(argv):
            now_text = argv[index + 1]
        elif arg.startswith("--now="):
            now_text = arg[len("--now=") :]
    try:
        return pretty, parse_iso8601(now_text) if now_text else None
    except ValueError:
        return pretty, None


def _timestamp(now: Now) -> str:
    if now is None:
        return to_iso(utc_now())
    if isinstance(now, str):
        return to_iso(parse_iso8601(now))
    return to_iso(now)


def _message(item: Any, default_code: str) -> Message:
    if isinstance(item, dict):
        return error(item.get("code") or default_code, item.get("message", ""), item.get("path"))
    return error(default_code, item)


def _check_kind(kind: Any) -> None:
    if not isinstance(kind, str) or not _KIND_RE.match(kind):
        raise ValueError("envelope kind must be a contract name like 'review-verdict', got %r" % (kind,))


def _write(text: str, stream: Optional[TextIO]) -> None:
    """Write UTF-8 regardless of the platform's console encoding."""
    stream = sys.stdout if stream is None else stream
    buffer = getattr(stream, "buffer", None)
    if buffer is None:
        stream.write(text)
        stream.flush()
        return
    stream.flush()
    buffer.write(text.encode("utf-8"))
    buffer.flush()
