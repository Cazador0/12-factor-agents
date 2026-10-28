# Feature Specification: JSON contracts and the shared skillkit

**Spec**: SPEC-100

**Component**: `skill-lab/contracts/` and `skill-lab/shared/_skillkit/` (family: lab)

**Created**: 2026-10-22

**Status**: Implemented

**Input**: CONVENTIONS §3–§5 and the engineering-team report: every role and
the control plane exchange typed JSON evidence, and every skill script shares
one small, stdlib-only library vendored into its folder.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A small local model can act on any script's output (Priority: P1)

An agent running Zed with a ~32k-context Ollama model calls a skill script.
Whatever happens (success, a failed check, bad input, a crash), it receives
exactly one compact JSON envelope whose `ok`, `errors[].code` and payload it can
branch on without reading prose or a stack trace.

**Why this priority**: every skill depends on it; without it nothing else is
machine-checkable.

**Independent Test**: run `run_script` with mains that succeed, fail, raise
`ScriptError`, raise an unexpected exception, and get bad flags; each run
prints one envelope that validates against `envelope.v1`.

**Acceptance Scenarios**:

1. **Given** a script whose check passes, **When** it exits, **Then** stdout is one envelope with `ok: true`, exit code 0, no errors, and a payload valid against `kind_schema`.
2. **Given** a script that raises an unexpected exception, **When** it exits, **Then** the envelope carries one `INTERNAL` error, exit code is 2, and no traceback appears on stdout.
3. **Given** `GITEA_TOKEN` is set, **When** any output mentions its value, **Then** the value appears only as `***`.

---

### User Story 2 - Roles exchange evidence that cannot claim more than it proves (Priority: P1)

Lead, PSE and Review hand each other issue contracts, evidence packages,
verdicts, gates and merge decisions as JSON. A document that asserts an
impossible state (APPROVE with blockers, a passed gate with an applicable
`not_run` category, AUTO_MERGE of high-risk work) is rejected by schema.

**Why this priority**: the report's safety argument rests on evidence that
"not run" never silently means "passed".

**Independent Test**: validate each example and each crafted violation in
`tests/test_contracts.py`; every example passes, every violation fails.

**Acceptance Scenarios**:

1. **Given** a `review-verdict` with `result: APPROVE` and one blocker, **When** it is validated, **Then** it is invalid.
2. **Given** a `quality-gate` with `passed: true` and an applicable category whose status is `not_run`, **When** it is validated, **Then** it is invalid.
3. **Given** a `merge-decision` of `AUTO_MERGE` that touches a policy path, **When** it is validated, **Then** it is invalid.

---

### User Story 3 - The lab validates skills and benchmarks deterministically (Priority: P2)

The lab parses every `SKILL.md` with the same strict subset Zed, Claude Code and
Codex agree on, checks script imports against the Python 3.9 standard library,
evaluates benchmark assertions, and scores skills, all offline and with the
same result on every run.

**Why this priority**: release gates are only meaningful when their inputs are
parsed and graded identically everywhere.

**Independent Test**: the frontmatter accept/reject matrix, the assertion
operator tests, and the stdlib list tests pass on Python 3.11–3.13.

**Acceptance Scenarios**:

1. **Given** a SKILL.md whose description is a YAML block scalar, **When** it is parsed, **Then** a `block_scalar` issue names the file and line.
2. **Given** an assertion on a path that does not exist, **When** it is evaluated with any op except `not_exists`, **Then** it fails.
3. **Given** a script that imports `tomllib`, **When** imports are checked with `is_portable_stdlib`, **Then** it is rejected (absent from 3.9).

### Edge Cases

- A UTF-8 BOM, leading blank lines and CRLF line endings in SKILL.md parse like Zed's `trim_start()` reader; the BOM is reported in `bom`.
- `1.0` is an integer and `true` is never a number, as JSON Schema requires.
- A leap second (`23:59:60Z`) is a valid RFC 3339 date-time; `23:58:60Z` is not.
- Two writers replacing the same state file never leave a torn file; a second lock holder times out with `LOCK_TIMEOUT`.
- A symlink inside an allowed root that points outside it is a traversal.
- An instance nested too deeply to validate yields one `depth` issue instead of a crash.

## Requirements *(mandatory)*

### Functional Requirements

Contract families:

- **FR-001**: The catalog MUST provide `envelope.v1`, the single stdout document, with `ok` true exactly when the exit code is 0, a payload object and no errors when `ok` is true, and compact `{code, message, path}` errors.
- **FR-002**: The catalog MUST provide the coordination contracts `mutation-request`, `lease`, `normalized-event`, `transition-decision`, `merge-decision` and `session-checkpoint`, each carrying the authority, concurrency and idempotency fields the report requires.
- **FR-003**: The catalog MUST provide the planning contracts `task-graph`, `spec-readiness`, `issue-contract`, `task-issue-map`, `sync-drift-report` and `gitea-plan`, using Spec Kit task IDs (`T001`), spec IDs (`SPEC-042`), FR/NFR IDs and Gitea REST paths under `/api/v1`.
- **FR-004**: The catalog MUST provide the evidence contracts `implementation-evidence`, `review-verdict` and `quality-gate`, where every check records its command, exit code and log digest and every quality category states its applicability explicitly.
- **FR-005**: The catalog MUST provide the audit and validation contracts `twelve-factor-scorecard` (exactly factors 1–12 in order, scores 0–3, max 36) and `validation-report`.
- **FR-006**: The catalog MUST provide the benchmark contracts `benchmark-case` (deterministic, agentic and trigger tiers; Jev noul/score/choice judgments), `benchmark-result`, `benchmark-run`, `success-criteria` and `skill-score`.
- **FR-007**: Every schema MUST use draft 2020-12 with `$id` `urn:skill-lab:schema:<name>:v1`, stay within the CONVENTIONS §4 keyword subset, declare `additionalProperties` on every object (open only at four documented slots), require `schema_version: 1` in payloads, and ship one example that validates.
- **FR-008**: Schemas MUST make the report's forbidden states unrepresentable: APPROVE with blockers or unverified requirements, a passed gate with an applicable `not_run` category, AUTO_MERGE of high/critical risk or policy paths, Jev judgments with `jev_mode: off`, an uncertain judgment counted as pass, a gate passed without a measured value, `release_ready` with failed tests.
- **FR-009**: Every CONVENTIONS §4 catalog contract MUST have a schema, every schema file MUST be listed in the contracts README table and have an example, and shared `$defs` MUST be identical in every file that copies them.

Skillkit modules:

- **FR-010**: `envelope` MUST build envelopes (`make_envelope`), compact errors (`error`, `ScriptError` with exit codes 1–4), emit exactly one sorted UTF-8 JSON document (`emit`), and `run_script` MUST turn every outcome, including argparse errors and unexpected exceptions (`INTERNAL`, exit 2, traceback only on stderr with `SKILLKIT_DEBUG=1`), into one redacted envelope.
- **FR-011**: `cli` MUST provide `base_parser` with `--pretty`, `--now` and `--state-dir` (default `./.skill-state`) whose usage errors raise `ScriptError("USAGE")`, strict `read_json`/`read_text` (`INPUT_NOT_FOUND`, `INPUT_UNREADABLE`, `INPUT_NOT_JSON` with `file:line:col`; no NaN, no numbers that overflow to infinity, no duplicate keys, no pathological nesting), the same rules for in-memory text as `loads_strict`, `parse_now` and `to_iso`.
- **FR-012**: `jsonschema_mini.validate` MUST implement exactly the keyword subset with JSON Schema semantics (integral floats are integers, booleans are not numbers, `oneOf` exactly one, local `$ref`, RFC 3339 `date-time`) and return issues in a deterministic order, where a failed `anyOf`/`oneOf` quotes the rule's short description and the closest alternative so a model can correct its output; `unsupported_keywords` MUST list every keyword outside the subset.
- **FR-013**: `schemas` MUST locate the skill root of a vendored copy, load `<name>.v1.schema.json` from `assets/schemas/` or given directories (refusing names that could traverse), and validate payloads and envelopes.
- **FR-014**: `frontmatter.parse` MUST accept exactly the CONVENTIONS §2 subset and report every other construct with its line; `frontmatter.lint` MUST apply the §2 field rules.
- **FR-015**: `jsonpointer` MUST implement RFC 6901 resolution, distinguishing malformed pointers from missing values.
- **FR-016**: `redact` MUST mask values of the listed secret environment variables, bearer and Authorization credentials, URL userinfo, known token formats and values under credential-named keys, without modifying its input.
- **FR-017**: `fsutil` MUST provide atomic JSON/text writes, an exclusive file lock with `LOCK_TIMEOUT` (exit 3), `safe_join` refusing traversal (`PATH_TRAVERSAL`, exit 4) and `ensure_not_inside` refusing writes into a protected folder (`PATH_FORBIDDEN`, exit 4).
- **FR-018**: `ids` MUST provide canonical JSON, `sha256:` digests and deterministic `idem-<32 hex>` idempotency keys.
- **FR-019**: `stdlib_modules` MUST answer "is this a standard-library module" on Python 3.10+ from `sys.stdlib_module_names` and on 3.9 from an embedded complete list, and `is_portable_stdlib` MUST require presence in 3.9 and in the running Python. `is_known_stdlib` MUST recognise any module of Python 3.9 through 3.14 (`POST_PY39_STDLIB_MODULES`, measured from real interpreters) on every interpreter, so a validator on 3.9 reports `tomllib` as not portable rather than third-party.
- **FR-020**: `assertions.evaluate` MUST implement the 17 CONVENTIONS §5 operators without type coercion, fail every op except `not_exists` on a missing path, and raise `InvalidAssertion` for malformed assertions.
- **FR-021**: `timeutil` MUST check and parse RFC 3339 strictly, accept the documented ISO 8601 relaxations for `--now`, and format timestamps as `YYYY-MM-DDTHH:MM:SSZ`.
- **FR-022**: The `_skillkit` package MUST be standard-library only, parse as Python 3.9, avoid runtime PEP 604 unions and 3.10-only APIs, never `eval`/`exec` or use `shell=True`, and import no submodule from its root.
- **FR-023**: `jsonschema_mini` MUST agree with a reference draft 2020-12 implementation on the validity of every example and crafted instance whenever that implementation is installed.

### Key Entities

- **Contract**: a versioned JSON Schema (`<name>.v<N>.schema.json`) plus one example; identified by its URN.
- **Envelope**: the stdout wrapper that names a contract (`kind`, `kind_schema`) and carries its payload.
- **Issue**: `(path, keyword, message)`, one validation or parse problem.
- **ScriptError**: a compact error (`code`, `message`, `path`) with an exit code.
- **Assertion**: `{path, op, value?}` evaluated against an envelope or model output.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 23 of 23 catalog contracts have a schema and an example; 100% of examples and crafted valid variants validate, and 100% of crafted violations are rejected.
- **SC-002**: `unsupported_keywords` returns `[]` for every schema.
- **SC-003**: Where the reference `jsonschema` package is installed, `jsonschema_mini` agrees with it on 100% of compared instances (more than 150).
- **SC-004**: The full suite passes on Python 3.11, 3.12 and 3.13 with no third-party packages; the package parses with Python 3.9 grammar.
- **SC-005**: No test output, envelope or state file contains a configured secret value.

## Assumptions

- Python 3.9 is the oldest supported runtime; it is not installed in the build container, so 3.9 compatibility is enforced statically (grammar, API and import checks) and by the embedded module list.
- Producers enforce map key formats (`AC-01`, `T001`) because the keyword subset has no `propertyNames`.
- The reference `jsonschema` package is a test-time cross-check only; nothing under `skills/` or `skill-lab/` imports it at runtime.

## Non-goals

- A general JSON Schema implementation: keywords outside the subset are ignored by `validate` and reported by `unsupported_keywords`.
- A YAML parser: `frontmatter` accepts only the portable subset and rejects the rest.
- Network access, Gitea calls or model calls; those belong to the skills and to SPEC-102/103.

## Contracts

Emits: all 23 schemas in `skill-lab/contracts/schemas/` (`envelope`,
`mutation-request`, `task-graph`, `spec-readiness`, `issue-contract`,
`implementation-evidence`, `review-verdict`, `quality-gate`,
`session-checkpoint`, `normalized-event`, `lease`, `transition-decision`,
`merge-decision`, `task-issue-map`, `sync-drift-report`, `gitea-plan`,
`twelve-factor-scorecard`, `validation-report`, `benchmark-case`,
`benchmark-result`, `benchmark-run`, `success-criteria`, `skill-score`).
`run_script` emits `envelope.v1`. Consumes: none.

## Error semantics

All skillkit errors are compact `{code, message, path}` objects; messages are
one line of at most 300 characters.

| Code | Exit | Raised by | Meaning |
|---|---|---|---|
| `USAGE` | 2 | `cli` parser, `run_script` | Bad flags or arguments |
| `INTERNAL` | 2 | `run_script` | Unexpected exception or a `main()` contract violation |
| `INPUT_NOT_FOUND` | 2 | `read_json`, `read_text` | Missing file |
| `INPUT_UNREADABLE` | 2 | `read_json`, `read_text` | Directory or permission problem |
| `INPUT_NOT_JSON` | 2 | `read_json` | Invalid JSON, not UTF-8, NaN/Infinity, overflowing numbers, duplicate keys, nesting too deep |
| `INPUT_NOT_TEXT` | 2 | `read_text` | Not valid UTF-8 text |
| `INVALID_NOW` | 2 | `parse_now` | `--now` is not ISO 8601 |
| `SCHEMA_NOT_FOUND`, `SCHEMA_UNREADABLE`, `SCHEMA_NAME_INVALID`, `SCHEMA_URN_INVALID` | 2 | `schemas` | Missing or broken vendored schema |
| `SCHEMA_INVALID`, `ISSUES_TRUNCATED` | caller | `Issue.to_error`, `issues_to_errors` | Validation issues rendered as errors |
| `LOCK_TIMEOUT` | 3 | `file_lock` | Lock not acquired in time |
| `PATH_TRAVERSAL` | 4 | `safe_join` | Path escapes its root |
| `PATH_FORBIDDEN` | 4 | `ensure_not_inside` | Write inside a protected folder |

Programming errors (an invalid error code, an invalid `kind`, an unusable
schema) raise `ValueError`/`SchemaError` at the call site instead of being
reported as user errors.

## Security

- Secrets come only from environment variables and are masked from every
  envelope (`run_script` and `emit` redact) and from stderr logs (`cli.log`).
- Untrusted JSON is parsed strictly; duplicate keys are refused so two parsers
  cannot disagree about a value.
- Paths from untrusted input go through `safe_join`; scripts call
  `ensure_not_inside(path, skill_root())` before writing.
- The package never evaluates input, never spawns a shell, and imports nothing
  outside the standard library (tested).
- Schemas forbid absolute and `..` paths in write domains, evidence paths and
  Gitea REST paths, and forbid credentials in Gitea plans by allowing only
  `/api/v1/...` paths.

## Runtime compatibility

- Python ≥ 3.9, standard library only, POSIX and Windows (`fcntl` or `msvcrt`
  locks, with an `O_EXCL` fallback elsewhere).
- Zed (Ollama local or cloud), Claude Code and Codex all run skill scripts the
  same way; nothing here depends on the agent runtime. Output is compact JSON
  by default to save context for ~32k-token local models.
- The frontmatter subset matches Zed's `extract_frontmatter` (leading
  whitespace trimmed, closing line exactly `---`) and parses identically in
  serde_yaml and JavaScript YAML loaders.
