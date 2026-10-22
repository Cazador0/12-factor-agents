"""Shared, stdlib-only helpers for skill scripts (canonical copy).

This package is vendored verbatim into ``skills/<name>/scripts/_skillkit/`` by
``skill-lab sync``. Never edit a vendored copy; change this canonical copy and
re-sync. Scripts import it after putting their own directory on ``sys.path``::

    sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
    from _skillkit import cli, envelope

The package root deliberately imports no submodules, so importing one module
never drags in the rest. Modules:

- ``envelope``        envelope.v1 construction, compact errors, ``run_script``
- ``cli``             argparse base parser, strict JSON/text input, ``--now``
- ``jsonschema_mini`` validator for the contract keyword subset (CONVENTIONS §4)
- ``schemas``         locate and load vendored ``*.v1.schema.json`` contracts
- ``frontmatter``     strict SKILL.md frontmatter parser (CONVENTIONS §2)
- ``jsonpointer``     RFC 6901 JSON Pointer resolution
- ``redact``          secret masking for everything a script prints
- ``fsutil``          atomic writes, file locks, path containment
- ``ids``             canonical JSON, digests, idempotency keys
- ``stdlib_modules``  "is this import in the standard library?" (3.9 fallback)
- ``assertions``      benchmark assertion operators (CONVENTIONS §5)
- ``timeutil``        RFC 3339 parsing and formatting
"""

from __future__ import annotations

SKILLKIT_VERSION = "0.1.0"

EXIT_OK = 0
"""Completed; the checked thing is OK or the decision was computed."""

EXIT_FAIL = 1
"""Completed; the checked thing failed (the payload is still valid)."""

EXIT_USAGE = 2
"""Usage or input error, including unexpected internal errors."""

EXIT_EXTERNAL = 3
"""External dependency failure (network, Gitea, model API, lock timeout)."""

EXIT_REFUSED = 4
"""Refused by policy or guardrail."""

EXIT_CODES = (EXIT_OK, EXIT_FAIL, EXIT_USAGE, EXIT_EXTERNAL, EXIT_REFUSED)

__all__ = [
    "SKILLKIT_VERSION",
    "EXIT_OK",
    "EXIT_FAIL",
    "EXIT_USAGE",
    "EXIT_EXTERNAL",
    "EXIT_REFUSED",
    "EXIT_CODES",
]
