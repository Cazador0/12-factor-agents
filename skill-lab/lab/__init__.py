"""skill-lab: validate, vendor, install, catalog, scaffold and test portable agent skills.

Every subcommand module exposes ``main(argv: list[str]) -> int`` and prints
exactly one ``envelope.v1`` JSON document on stdout (CONVENTIONS §3). The
dispatcher table lives in ``lab.cli``; ``skill-lab/bin/skill-lab`` is the
executable entry point.

Importing this package puts ``skill-lab/shared`` on ``sys.path`` so lab
modules use the canonical ``_skillkit`` exactly as a vendored skill script
uses its own copy. The path is derived from this file, never hard-coded.
"""

from __future__ import annotations

import os
import sys

LAB_VERSION = "0.1.0"

SHARED_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "shared")

if SHARED_DIR not in sys.path:
    sys.path.insert(0, SHARED_DIR)

__all__ = ["LAB_VERSION", "SHARED_DIR"]
