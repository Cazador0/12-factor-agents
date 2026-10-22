"""Export the JevMessage JSON Schema to ``schemas/jev-message.v1.json``, the cross-language contract.

OCaml and Rust generate their bindings from this file (spec 009 FR-003). Enums are plain JSON strings, which
``ppx_deriving_yojson``'s default variant encoding does not match (see ``models.py``).
"""

from __future__ import annotations

import json
from pathlib import Path

from .models import JevMessage

SCHEMA_REL = Path("schemas/jev-message.v1.json")
SCHEMA_ID = "https://github.com/Cazador0/12-factor-agents/schemas/jev-message.v1.json"


def message_schema() -> dict:
    schema = JevMessage.model_json_schema(mode="serialization")
    return {"$schema": "https://json-schema.org/draft/2020-12/schema", "$id": SCHEMA_ID, **schema}


def render() -> str:
    return json.dumps(message_schema(), indent=2, sort_keys=True) + "\n"


def write(root: Path) -> Path:
    path = root / SCHEMA_REL
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(render(), encoding="utf-8")
    return path


def is_current(root: Path) -> bool:
    path = root / SCHEMA_REL
    return path.is_file() and path.read_text(encoding="utf-8") == render()
