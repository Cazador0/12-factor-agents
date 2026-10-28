"""RFC 3339 timestamps: strict checking, parsing, and canonical formatting.

Every timestamp a script emits uses the canonical form ``YYYY-MM-DDTHH:MM:SSZ``
(UTC, whole seconds). Parsing raises ``ValueError``; callers that need a compact
script error wrap it (see ``cli.parse_now``).
"""

from __future__ import annotations

import datetime as _dt
import re

_RFC3339_RE = re.compile(
    r"^(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    r"[Tt](?P<hour>[0-9]{2}):(?P<minute>[0-9]{2}):(?P<second>[0-9]{2})"
    r"(?P<fraction>\.[0-9]+)?"
    r"(?P<offset>[Zz]|[+-][0-9]{2}:[0-9]{2})$"
)

_LOOSE_RE = re.compile(
    r"^(?P<year>[0-9]{4})-(?P<month>[0-9]{2})-(?P<day>[0-9]{2})"
    r"(?:[Tt ](?P<hour>[0-9]{2}):(?P<minute>[0-9]{2})(?::(?P<second>[0-9]{2})(?P<fraction>\.[0-9]+)?)?"
    r"(?P<offset>[Zz]|[+-][0-9]{2}:?[0-9]{2})?)?$"
)


def utc_now() -> _dt.datetime:
    """Return the current time as an aware UTC datetime with whole seconds."""
    return _dt.datetime.now(_dt.timezone.utc).replace(microsecond=0)


def to_iso(value: _dt.datetime) -> str:
    """Format a datetime as ``YYYY-MM-DDTHH:MM:SSZ``.

    Aware datetimes are converted to UTC; naive ones are taken to be UTC.
    Sub-second precision is dropped so output stays byte-stable.
    """
    if value.tzinfo is None:
        value = value.replace(tzinfo=_dt.timezone.utc)
    value = value.astimezone(_dt.timezone.utc)
    return value.strftime("%Y-%m-%dT%H:%M:%SZ")


def is_rfc3339(value: object) -> bool:
    """Return True when ``value`` is an RFC 3339 ``date-time`` string.

    Follows RFC 3339 §5.6 as JSON Schema's ``format: date-time`` requires:
    ASCII digits only, case-insensitive ``T``/``Z``, a mandatory offset, real
    calendar dates, and a leap second (``:60``) only at 23:59 UTC.
    """
    if not isinstance(value, str):
        return False
    match = _RFC3339_RE.match(value)
    if match is None:
        return False
    year, month, day, hour, minute, second = (
        int(match.group(key)) for key in ("year", "month", "day", "hour", "minute", "second")
    )
    if not _valid_date(year, month, day):
        return False
    if hour > 23 or minute > 59 or second > 60:
        return False
    offset_minutes = _offset_minutes(match.group("offset"))
    if offset_minutes is None:
        return False
    if second == 60:
        utc_minutes = (hour * 60 + minute - offset_minutes) % (24 * 60)
        return utc_minutes == 23 * 60 + 59
    return True


def parse_rfc3339(value: str) -> _dt.datetime:
    """Parse a strict RFC 3339 date-time into an aware UTC datetime.

    Raises ``ValueError`` for anything ``is_rfc3339`` rejects and for leap
    seconds, which ``datetime`` cannot represent.
    """
    if not is_rfc3339(value):
        raise ValueError("not an RFC 3339 date-time: %r" % (value,))
    return _build(_RFC3339_RE.match(value), require_offset=True)


def parse_iso8601(value: str) -> _dt.datetime:
    """Parse the ISO 8601 forms accepted for ``--now`` into aware UTC.

    Accepts RFC 3339 plus the common relaxations: a date alone (midnight), a
    space instead of ``T``, minutes without seconds, ``+HHMM`` offsets, and no
    offset at all (taken to be UTC). Raises ``ValueError`` otherwise.
    """
    if not isinstance(value, str):
        raise ValueError("timestamp must be a string")
    match = _LOOSE_RE.match(value.strip())
    if match is None:
        raise ValueError("not an ISO 8601 timestamp: %r" % (value,))
    return _build(match, require_offset=False)


def _build(match: re.Match, *, require_offset: bool) -> _dt.datetime:
    year, month, day = int(match.group("year")), int(match.group("month")), int(match.group("day"))
    hour = int(match.group("hour") or 0)
    minute = int(match.group("minute") or 0)
    second = int(match.group("second") or 0)
    fraction = match.group("fraction") or ""
    microsecond = int((fraction[1:] + "000000")[:6]) if fraction else 0
    offset_text = match.group("offset")
    if offset_text is None and require_offset:
        raise ValueError("timestamp has no UTC offset")
    offset_minutes = _offset_minutes(offset_text) if offset_text else 0
    if offset_minutes is None:
        raise ValueError("invalid UTC offset: %r" % (offset_text,))
    tz = _dt.timezone(_dt.timedelta(minutes=offset_minutes))
    try:
        value = _dt.datetime(year, month, day, hour, minute, second, microsecond, tzinfo=tz)
    except ValueError as exc:
        raise ValueError("invalid timestamp: %s" % exc) from None
    return value.astimezone(_dt.timezone.utc)


def _offset_minutes(text: str) -> int | None:
    """Return the signed offset in minutes, or None when it is out of range."""
    if text in ("Z", "z"):
        return 0
    sign = -1 if text[0] == "-" else 1
    digits = text[1:].replace(":", "")
    hours, minutes = int(digits[:2]), int(digits[2:])
    if hours > 23 or minutes > 59:
        return None
    return sign * (hours * 60 + minutes)


def _valid_date(year: int, month: int, day: int) -> bool:
    if not 1 <= month <= 12 or day < 1:
        return False
    days_in_month = (31, 29 if _is_leap(year) else 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31)
    return day <= days_in_month[month - 1]


def _is_leap(year: int) -> bool:
    return year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)
