"""Mask secrets in anything a script is about to print or persist.

``redact(obj)`` returns a new object; the input is never modified. It masks:

- the values of ``SECRET_ENV_VARS`` currently set in the environment (only
  values of 8+ characters, so short values cannot mangle ordinary text);
- ``Bearer <token>`` and ``Authorization: <scheme> <credential>`` text;
- URL userinfo (``scheme://user:pass@host`` becomes ``scheme://***@host``);
- well-known token formats (GitHub ``ghp_``/``github_pat_``, ``sk-`` keys);
- string or container values under keys that name a credential, such as
  ``token``, ``api_key``, ``authorization``, ``password``, ``secret``.

Counts such as ``input_tokens`` are kept: plural ``tokens`` is not a credential
word, and numbers, booleans and nulls are never masked.
"""

from __future__ import annotations

import os
import re
from typing import Any, Iterable, List

MASK = "***"

SECRET_ENV_VARS = (
    "GITEA_TOKEN",
    "TYPESAFE_API_KEY",
    "JEV_API_KEY",
    "OLLAMA_API_KEY",
    "GITHUB_TOKEN",
    "GH_TOKEN",
    "ANTHROPIC_API_KEY",
    "OPENAI_API_KEY",
)

MIN_SECRET_LENGTH = 8

_SENSITIVE_WORDS = frozenset(
    {
        "token",
        "password",
        "passwd",
        "passphrase",
        "secret",
        "authorization",
        "auth",
        "apikey",
        "cookie",
        "credential",
        "credentials",
    }
)
_SENSITIVE_PAIRS = frozenset(
    {("api", "key"), ("private", "key"), ("access", "key"), ("secret", "key"), ("signing", "key")}
)
_KEY_WORD_RE = re.compile(r"[A-Z]+(?![a-z])|[A-Z]?[a-z0-9]+")

_KNOWN_TOKEN_RE = re.compile(
    r"\b(?:gh[pousr]_[A-Za-z0-9]{20,}|github_pat_[A-Za-z0-9_]{20,}|sk-(?:ant-)?[A-Za-z0-9_\-]{20,})"
)
_BEARER_RE = re.compile(r"(?i)\b(bearer)\s+[A-Za-z0-9\-._~+/]+=*")
_AUTH_HEADER_RE = re.compile(r"(?i)\b(authorization\s*[:=]\s*)((?:token|basic|bearer)\s+)?([^\s,;\"']+)")
_URL_USERINFO_RE = re.compile(r"(?i)\b([a-z][a-z0-9+.\-]*://)[^/\s@?#]+@")


def redact(obj: Any) -> Any:
    """Return a deep copy of ``obj`` (JSON-like data) with secrets masked."""
    return _redact(obj, _env_secrets())


def redact_text(text: str) -> str:
    """Mask secrets inside a single string (for stderr logs and messages)."""
    return _redact_text(text, _env_secrets())


def is_sensitive_key(key: str) -> bool:
    """Return True when a mapping key names a credential.

    The key is split into words on separators and camelCase, so ``apiKey``,
    ``GITEA_TOKEN`` and ``x-auth-token`` match while ``input_tokens``,
    ``idempotency_key`` and ``author`` do not.
    """
    words = [word.lower() for word in _KEY_WORD_RE.findall(key)]
    if any(word in _SENSITIVE_WORDS for word in words):
        return True
    return any(pair in _SENSITIVE_PAIRS for pair in zip(words, words[1:]))


def _env_secrets() -> List[str]:
    values = {os.environ.get(name, "") for name in SECRET_ENV_VARS}
    return sorted((v for v in values if len(v) >= MIN_SECRET_LENGTH), key=len, reverse=True)


def _redact(obj: Any, secrets: Iterable[str]) -> Any:
    if isinstance(obj, str):
        return _redact_text(obj, secrets)
    if isinstance(obj, dict):
        result = {}
        for key, value in obj.items():
            safe_key = _redact_text(key, secrets) if isinstance(key, str) else key
            if isinstance(key, str) and is_sensitive_key(key) and _maskable(value):
                result[safe_key] = MASK
            else:
                result[safe_key] = _redact(value, secrets)
        return result
    if isinstance(obj, (list, tuple)):
        return [_redact(item, secrets) for item in obj]
    return obj


def _maskable(value: Any) -> bool:
    """Credentials are strings or containers; numbers, booleans, nulls stay readable."""
    if isinstance(value, str):
        return value != ""
    return isinstance(value, (dict, list, tuple))


def _redact_text(text: str, secrets: Iterable[str]) -> str:
    for secret in secrets:
        text = text.replace(secret, MASK)
    text = _KNOWN_TOKEN_RE.sub(MASK, text)
    text = _BEARER_RE.sub(lambda m: m.group(1) + " " + MASK, text)
    text = _AUTH_HEADER_RE.sub(lambda m: m.group(1) + (m.group(2) or "") + MASK, text)
    return _URL_USERINFO_RE.sub(lambda m: m.group(1) + MASK + "@", text)
