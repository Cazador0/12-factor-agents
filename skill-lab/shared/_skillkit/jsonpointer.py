"""RFC 6901 JSON Pointer resolution.

``""`` is the whole document, ``"/a/0"`` is key ``a`` then array index 0,
``~1`` encodes ``/`` and ``~0`` encodes ``~``. Array indices must be ``0`` or
have no leading zero; ``-`` (one past the end) never resolves to a value.
"""

from __future__ import annotations

import re
from typing import Any, List

_INDEX_RE = re.compile(r"^(0|[1-9][0-9]*)$")
_BAD_ESCAPE_RE = re.compile(r"~(?![01])")


class PointerError(LookupError):
    """The pointer does not resolve to a value in the document."""


class PointerSyntaxError(PointerError, ValueError):
    """The pointer is not a syntactically valid RFC 6901 pointer."""


def escape(token: str) -> str:
    """Escape one reference token (``~`` -> ``~0``, ``/`` -> ``~1``)."""
    return token.replace("~", "~0").replace("/", "~1")


def unescape(token: str) -> str:
    """Decode one reference token; raises ``PointerSyntaxError`` on bad ``~``."""
    if _BAD_ESCAPE_RE.search(token):
        raise PointerSyntaxError("invalid '~' escape in token %r" % (token,))
    return token.replace("~1", "/").replace("~0", "~")


def split(pointer: str) -> List[str]:
    """Split a pointer into decoded reference tokens."""
    if not isinstance(pointer, str):
        raise PointerSyntaxError("pointer must be a string")
    if pointer == "":
        return []
    if not pointer.startswith("/"):
        raise PointerSyntaxError("pointer must be empty or start with '/': %r" % (pointer,))
    return [unescape(token) for token in pointer[1:].split("/")]


def join(base: str, *tokens: Any) -> str:
    """Append raw tokens (escaped here) to ``base``: ``join("/a", "b/c", 0)`` -> ``/a/b~1c/0``."""
    return base + "".join("/" + escape(str(token)) for token in tokens)


def resolve(doc: Any, pointer: str) -> Any:
    """Return the value ``pointer`` refers to inside ``doc``.

    Raises ``PointerSyntaxError`` for malformed pointers and ``PointerError``
    when a step is missing, out of range, or descends into a scalar.
    """
    current = doc
    walked = ""
    for token in split(pointer):
        walked = join(walked, token)
        if isinstance(current, dict):
            if token not in current:
                raise PointerError("no member %r at %s" % (token, walked))
            current = current[token]
        elif isinstance(current, (list, tuple)):
            if not _INDEX_RE.match(token):
                raise PointerError("invalid array index %r at %s" % (token, walked))
            index = int(token)
            if index >= len(current):
                raise PointerError("index %d out of range at %s" % (index, walked))
            current = current[index]
        else:
            raise PointerError("cannot descend into a scalar at %s" % (walked,))
    return current


def exists(doc: Any, pointer: str) -> bool:
    """Return True when ``pointer`` resolves inside ``doc``.

    A malformed pointer is a caller bug, so ``PointerSyntaxError`` propagates
    instead of reading as "missing".
    """
    try:
        resolve(doc, pointer)
    except PointerSyntaxError:
        raise
    except PointerError:
        return False
    return True
