# Vendored reference material

These files are copied verbatim from upstream projects so the lab can be
built and verified offline. They are reference inputs, not code the lab runs.

| File | Upstream | License |
|---|---|---|
| `typesafe-wire-models.py` | `typesafe-sdk` 0.7.5 (`typesafe_sdk/_schemas/models.py`), generated from `https://api.typesafe.ai/openapi.json` | MIT, TypeSafe AI |
| `speckit-tasks-template.md` | `github/spec-kit` `templates/tasks-template.md` @ `dc2cec4` (2026-10-21) | MIT, Copyright GitHub, Inc. |
| `speckit-spec-template.md` | `github/spec-kit` `templates/spec-template.md` @ `dc2cec4` (2026-10-21) | MIT, Copyright GitHub, Inc. |

When upstream changes, re-copy the file, update the version column, and run
`python3 skill-lab/bin/skill-lab test` so contract drift shows up as a failing test.
