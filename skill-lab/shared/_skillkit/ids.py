"""Canonical JSON, content digests, and deterministic idempotency keys.

``canonical_json`` is the one serialisation used for hashing: sorted keys,
no whitespace, UTF-8 characters kept, NaN/Infinity refused. Two equal JSON
values therefore always hash the same, on every platform and Python version.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any

DIGEST_PREFIX = "sha256:"
IDEMPOTENCY_PREFIX = "idem-"


def canonical_json(obj: Any) -> str:
    """Serialise ``obj`` canonically (sorted keys, ``,``/``:`` separators)."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False, allow_nan=False)


def digest(obj: Any) -> str:
    """Return ``sha256:<64 hex>`` of the canonical JSON of ``obj``."""
    return digest_bytes(canonical_json(obj).encode("utf-8"))


def digest_bytes(data: bytes) -> str:
    """Return ``sha256:<64 hex>`` of raw bytes (for logs and artifacts)."""
    return DIGEST_PREFIX + hashlib.sha256(data).hexdigest()


def digest_file(path: str, chunk_size: int = 1 << 16) -> str:
    """Return ``sha256:<64 hex>`` of a file's bytes, read in chunks."""
    hasher = hashlib.sha256()
    with open(path, "rb") as handle:
        for chunk in iter(lambda: handle.read(chunk_size), b""):
            hasher.update(chunk)
    return DIGEST_PREFIX + hasher.hexdigest()


def idempotency_key(*parts: Any) -> str:
    """Derive ``idem-<32 hex>`` from the canonical JSON of ``parts``.

    The same inputs always give the same key, so a retried mutation is
    recognised as a duplicate: ``idempotency_key("create_issue", repo, "T001")``.
    """
    return IDEMPOTENCY_PREFIX + hashlib.sha256(canonical_json(list(parts)).encode("utf-8")).hexdigest()[:32]
