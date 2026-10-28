# Feature Specification: Benchmark runner, model runtimes and graders

**Spec**: SPEC-102

**Component**: `skill-lab/lab/bench.py`, `skill-lab/lab/graders.py`, `skill-lab/lab/cassette.py`, `skill-lab/lab/runtimes/` (family: lab)

**Created**: 2026-10-22

**Status**: Implemented

**Input**: CONVENTIONS §5 (deterministic, agentic and trigger tiers; "never fabricate model or Jev
results"), the engineering-team report ("every recurring agent mistake becomes a regression fixture,
then an evaluation"), and the user's runtime priority: the Zed Agent on Ollama (a local GPU under
24 GB, so about 32k context, plus Ollama Cloud, which has no structured outputs), then Claude Code and
Codex.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Deterministic cases gate every change offline (Priority: P1)

A skill author runs `skill-lab bench --tier deterministic` in CI with no network. Every case's script
runs in isolation and is graded by exit code, envelope and payload validity, and JSON-Pointer
assertions. A failing case fails the run.

**Why this priority**: deterministic cases are the only tier that runs everywhere, and they encode the
guardrails (refusals, schema invariants) that must never regress.

**Independent Test**: a scratch repository with one skill and a tiny echo script; `bench.run` grades a
passing and a failing case, writes the results and validates them against the contracts.

**Acceptance Scenarios**:

1. **Given** a case whose script exits 0 with a valid envelope and matching assertions, **When** bench runs, **Then** the result is `pass` with `schema_valid: true`.
2. **Given** a case that expects exit 1 while the script exits 0, **When** bench runs, **Then** the result is `fail`, the note says why, and the run exits 1.
3. **Given** a case that passes `--touch {tmp}/marker`, **When** bench runs, **Then** the file is written in a per-case temporary folder and never inside the skill folder.

---

### User Story 2 - A local or cloud model is benchmarked the way Zed presents the skill (Priority: P1)

The user runs `skill-lab bench --tier agentic --runtime ollama-cloud --model gpt-oss:120b --jev live`.
The model sees Zed's skill catalog and the `<skill_content>` envelope of the skill under test, plus
the fixture files, and must answer with JSON for the case's `output_schema`. Ollama Cloud gets the
schema in the prompt and up to two repair turns; Ollama local also gets `format` and `num_ctx` 32768.

**Why this priority**: the priority runtime is Zed on Ollama with about 32k context; a skill that only
works with structured outputs or a large context fails there.

**Independent Test**: fake Ollama and fake Jev servers on 127.0.0.1; the agentic case passes, and the
recorded requests show the emulated prompts, `num_ctx`, `format`, and one Jev request per case.

**Acceptance Scenarios**:

1. **Given** `--runtime ollama-local`, **When** an agentic case runs, **Then** the request carries `format` = the output schema, `stream: false` and `options.num_ctx: 32768`, and the result is labelled `ollama-local-zed-emulation`.
2. **Given** `--runtime ollama-cloud` and a first reply that is not JSON, **When** the case runs, **Then** no `format` is sent, a repair turn quotes the compact error, and the second reply is graded.
3. **Given** a case with two judgments that share `state_from`, **When** Jev is live, **Then** both go in one System One request whose state holds exactly the declared parts.

---

### User Story 3 - Unavailable services are skipped, never passed (Priority: P1)

In this container, network access to `api.typesafe.ai` and `ollama.com` is blocked and no keys are set.
`skill-lab bench --tier all` still runs: deterministic cases are graded, and agentic and trigger
cases are `skipped` with a reason that starts with `LIVE_PREREQ_MISSING`.

**Why this priority**: "a gate that did not run never counts as passed" (CONVENTIONS §9, ADR-0010).

**Independent Test**: run the agentic and trigger tiers with an empty environment; every result is
`skipped` with a reason and every skipped tier has `pass_rate: null`.

**Acceptance Scenarios**:

1. **Given** no `--runtime`, **When** agentic cases are selected, **Then** they are skipped with `LIVE_PREREQ_MISSING: no --runtime given`.
2. **Given** a runtime but no Jev key, **When** a case has judgments, **Then** its schema validity and assertions are recorded and the case is skipped because its judgments could not be graded.
3. **Given** `--jev replay` and a request that was never recorded, **When** the case runs, **Then** it is skipped with `CASSETTE_MISS` and no answer is invented.

---

### User Story 4 - Routing accuracy across the whole catalog (Priority: P2)

Trigger cases ask which installed skill a user query should load. With Jev available, a choice
question lists every catalog skill with its description plus `none`; otherwise the model runtime
names a skill from Zed's catalog.

**Why this priority**: a skill that never triggers, or triggers for its neighbour's requests, is
broken even when its scripts are perfect.

**Independent Test**: one positive and one negative trigger case, routed by fake Jev and then by the
fake Ollama runtime (`--router runtime`).

**Acceptance Scenarios**:

1. **Given** a query for the skill, **When** Jev chooses it, **Then** the result passes with `routed_skill` set and the top probabilities in the notes.
2. **Given** `expect_skill: null`, **When** the router answers `none`, **Then** the result passes with `routed_skill: null`.

---

### User Story 5 - A live run can be replayed later without the network (Priority: P3)

The user records one live run with `--record DIR` once the network is allowlisted, commits the
cassette, and anyone can replay it with `--runtime replay --jev replay --cassettes DIR`.

**Why this priority**: reproducible evidence for reviews without paying for or reaching live services.

**Independent Test**: record against fake servers, stop them, replay, and compare the statuses and
judgments; the cassette contains neither the API key nor the local repository path.

**Acceptance Scenarios**:

1. **Given** a recorded run, **When** it is replayed with the services stopped, **Then** every case has the same status and results carry `jev_mode: replay`.

### Edge Cases

- A case file that is not JSON, or whose `id` differs from its file name, is reported as `CASE_INVALID` (exit 1) and not run.
- A deterministic case that does not require schema validity records `schema_valid: null`, because a passing result may only carry `true` or `null`.
- A malformed assertion (bad regex, wrong value type) makes the result `error` (`ASSERTION_INVALID`), not `fail`.
- An envelope whose `kind_schema` names an unknown contract is schema-invalid, not a crash.
- `--out` inside `skills/` is refused with exit 4 (`PATH_FORBIDDEN`).
- A model reply wrapped in a Markdown fence or prose is still parsed, and `json_extraction` records how (`strict`, `fenced`, `embedded`).

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `skill-lab bench` MUST read `skills/<name>/evals/cases/*.json`, validate each against `benchmark-case.v1`, require `id` to equal the file name and `skill` the folder name, require choice judgments to pass on one of their own labels, and report every invalid file as a `CASE_INVALID` error (exit 1) without running it.
- **FR-002**: Bench MUST select cases with `--skill` (repeatable or comma-separated; default all), `--tier` (`deterministic`, `agentic`, `trigger` or `all`, repeatable or comma-separated; default `deterministic`) and `--tag` (a case must carry every given tag).
- **FR-003**: A deterministic case MUST run `sys.executable <script> <args>` with the skill folder as cwd, stdin from `stdin_file` (or empty), the case timeout (default 60 s), and a minimal environment without secrets in which `HOME`, `TMPDIR`, `TEMP` and `TMP` point to a fresh per-case temporary folder that `{tmp}` in args and env also names; script and stdin paths MUST stay inside the skill folder.
- **FR-004**: The deterministic grader MUST pass a case only when the exit code matches, the stdout is one envelope that validates (with its payload against `kind_schema`, using the lab's canonical contracts, and `ok` equal to `exit_code == 0`) whenever the case requires it, and every assertion passes via `_skillkit.assertions`; it MUST record `schema_valid: null` when validity is not required and `error` with `ASSERTION_INVALID` for malformed assertions.
- **FR-005**: An agentic case MUST run one model turn with the Zed-emulated system prompt (catalog) and user prompt (skill envelope, fixture files, task) against the contract named by `output_schema`, and pass only when the reply's JSON validates (when required), every assertion holds, and every judgment passes; judgments are asked only after the deterministic checks pass.
- **FR-006**: Judgments MUST be sent to Jev as one System One request per distinct `state_from` set (one per case when the judgments share it) with the state built from exactly the declared parts, and graded by CONVENTIONS §5: noul `pass` >= threshold, `uncertain` in [0.35, threshold) which fails with `needs_human: true`, `fail` below 0.35; score passes at `score >= gte`; choice passes when the label equals `eq`.
- **FR-007**: A trigger case MUST be routed across the whole model-invocable catalog, by a Jev choice question (criteria: each skill's description plus `none`) when `--router` is `jev`, or `auto` and Jev is available, and otherwise by the model runtime answering `{"skill": <name or none>}`; the result MUST record `routed_skill`, the routing method and, for Jev, the confidence and top probabilities.
- **FR-008**: Bench MUST NOT fabricate model or Jev results: an unavailable runtime or Jev makes the affected cases `skipped` with a reason starting `LIVE_PREREQ_MISSING`; a case whose judgments cannot be graded is `skipped` even when its other checks passed; skipped cases never count as passed (`pass_rate` = passed / (passed + failed + errored), null when nothing ran).
- **FR-009**: Runtimes MUST implement `name`, `model`, `available() -> (bool, reason)` (no tokens spent) and `run(system_prompt, user_prompt, output_schema, *, timeout) -> RuntimeResult(text, json_or_none, usage, raw_meta)`, and be created by name (`ollama-local`, `ollama-cloud`, `claude-cli`, `codex-cli`, `replay`; aliases `claude`, `codex`).
- **FR-010**: `ollama-local` MUST `POST $OLLAMA_HOST/api/chat` (default `http://localhost:11434`) with `stream: false`, `options.num_ctx` (default 32768, `--num-ctx`), `temperature: 0`, `format` = the output schema, and the schema also in the prompt; `available()` MUST check `/api/tags` and that the model is pulled.
- **FR-011**: `ollama-cloud` MUST `POST https://ollama.com/api/chat` with `Authorization: Bearer $OLLAMA_API_KEY`, never send `format` or `num_ctx`, put the schema in the prompt, parse and validate the reply, and on an invalid reply run at most `--max-repairs` (default 2) repair turns that feed back at most eight compact validation errors (Factor 9).
- **FR-012**: `claude-cli` MUST run `claude -p --output-format json --no-session-persistence --tools "" --system-prompt <prompt> [--model M]` and `codex-cli` MUST run `codex exec --json --sandbox read-only --skip-git-repo-check [--model M] -`, each with the prompt on stdin, in a fresh empty temporary folder, without a shell; reported errors, non-zero exits and unusable output MUST become `RuntimeCallError`.
- **FR-013**: The Zed emulation MUST render the catalog exactly as `crates/agent/src/templates/system_prompt.hbs` does (Handlebars-escaped name and description, unescaped location, `disable-model-invocation` skills hidden) and the envelope exactly as `render_skill_envelope` in `crates/agent/src/tools/skill_tool.rs` does (XML-escaped attributes, trimmed body, only `<skill_content` tags neutralised), discover skills by a flat scan, and label results `<runtime>-zed-emulation`.
- **FR-014**: With `--record DIR`, live Jev HTTP exchanges and runtime turns MUST be saved as cassette entries keyed by the SHA-256 of the canonical request content (never headers), with secrets redacted and the repository root replaced by `<repo>`; `--runtime replay` and `--jev replay` read `--cassettes DIR`, and an unrecorded request MUST raise `CassetteMiss`, reported as `skipped` (`CASSETTE_MISS`).
- **FR-015**: Bench MUST write one redacted `benchmark-result.v1` per case to `<out>/results/<skill>/<case_id>.json` and the `benchmark-run.v1` to `<out>/benchmark-run.json` (default `<out>` = `skill-lab/benchmarks/runs/<run_id>`), validate both before writing (`RESULT_INVALID` otherwise), refuse an output or cassette folder inside `skills/`, record `suite_digest=`, `commit=` and (for `ollama-local`) `num_ctx=` note lines, and print the run as an `envelope.v1` of kind `benchmark-run`.
- **FR-016**: The `run_id` MUST be `run-<UTC stamp>-<8 hex digest of the arguments>`, so the same `--now` and arguments give the same ID; the exit code MUST be 0 when every graded case passed, 1 when a case failed or errored or a case file is invalid, 2 for usage errors and 4 for refused output paths.
- **FR-017**: The HTTP transport MUST use stdlib `urllib`, return every HTTP status as a response, raise `TransportError` only when no response arrived, bypass environment proxies for loopback hosts, cap bodies at 16 MiB, and retry 429/500/502/503/504 and connection errors with deterministic exponential backoff (0.5 s doubling, capped at 8 s, no jitter) that honours `retry-after-ms` and `retry-after` and stops when a hint exceeds 60 s.

### Key Entities

- **Benchmark case**: `benchmark-case.v1`; tier, how to run it, what to expect, and judgments.
- **Benchmark result**: `benchmark-result.v1`; status (`pass`, `fail`, `error`, `skipped`), schema validity, assertions, judgments, notes.
- **Benchmark run**: `benchmark-run.v1`; all results plus per-tier summaries and run notes.
- **Runtime**: a model endpoint behind the `Runtime` interface; its results are labelled `<runtime>-zed-emulation`.
- **Cassette**: a folder of recorded exchanges (`jev-http/`, `runtime/`), one JSON file per request digest.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of results and runs written by bench validate against `benchmark-result.v1` and `benchmark-run.v1` (they are checked before writing).
- **SC-002**: With no network and no keys, 0 agentic or trigger cases are reported `pass`; 100% are `skipped` with a reason.
- **SC-003**: The emulated catalog section is byte-identical to a render of Zed's `system_prompt.hbs` skills block for the same skills.
- **SC-004**: A recorded run replays with the services stopped with 100% identical case statuses, and its cassette contains 0 occurrences of the API key or the local repository path.
- **SC-005**: Every test in `test_bench_*.py` and `test_runtimes_*.py` passes on Python 3.11, 3.12 and 3.13 without network access.

## Assumptions

- Ollama's `/api/chat` reply carries `message.content`, `prompt_eval_count` and `eval_count`; `/api/tags` lists `models[].name`.
- Claude Code's `--output-format json` result object carries `result`, `is_error`, `subtype` and `usage`. Codex's `exec --json` event shapes come from its documentation; the Codex CLI is not installed in the build container, so they are not verified against a real binary.
- Zed's Handlebars renderer uses handlebars-rust's default HTML escaping (`templates.rs` registers no other escape function) and drops standalone block and comment lines.
- Model sampling uses `temperature: 0` to reduce run-to-run variance; it does not make models deterministic.
- An agentic case is a single model turn with no tool calls: the fixtures are given to the model, and scripts are not executed by it.

## Non-goals

- Running Zed itself. The emulation reproduces Zed's skill catalog and envelope, not its tool loop, other system-prompt sections or permission prompts.
- Scoring and release gates (SPEC-104) and the Jev client's wire protocol (SPEC-103).
- Image (`box`) questions and multipart assets.
- Statistical aggregation across repeated runs; one run is one sample.

## Contracts

Consumes: `benchmark-case.v1`, `envelope.v1` and every contract a case's `kind_schema` or
`output_schema` names (canonical copies in `skill-lab/contracts/schemas/`). Emits:
`benchmark-result.v1`, `benchmark-run.v1`, and an `envelope.v1` of kind `benchmark-run`.

## Error semantics

| Code | Where | Exit / status | Meaning |
|---|---|---|---|
| `CASE_INVALID` | envelope error or result `error` | exit 1 / `error` | Case file invalid, or a path or `expect_skill` it names is unusable |
| `SCRIPT_NOT_FOUND`, `SCRIPT_NOT_RUNNABLE`, `TIMEOUT` | result `error` | `error` | The deterministic script could not be run to completion |
| `ASSERTION_INVALID` | result `error` | `error` | A malformed assertion (case-authoring error) |
| `FIXTURE_NOT_FOUND`, `FIXTURE_TOO_LARGE` | result `error` | `error` | An agentic fixture is missing or over 64 KiB |
| `SKILL_NOT_LOADABLE` | result `error` | `error` | The skill's SKILL.md has no usable name and description |
| `RUNTIME_*` (`AUTH`, `TIMEOUT`, `UNREACHABLE`, `HTTP_ERROR`, `PROTOCOL`, `FAILED`), `MODEL_NOT_FOUND` | result `error` | `error` | The runtime was available but the turn failed |
| `JEV_*` | result `error` | `error` | See SPEC-103 |
| `CASSETTE_INVALID` | result `error` | `error` | A cassette entry exists but is corrupt |
| `LIVE_PREREQ_MISSING: ...` | `skip_reason` | `skipped` | A runtime, key or endpoint is not available here |
| `CASSETTE_MISS: ...` | `skip_reason` | `skipped` | Replay has no recording of this request |
| `CASES_SKIPPED`, `NO_CASES` | envelope warning | - | Skips grouped by reason; nothing matched the filters |
| `SKILL_NOT_FOUND`, `USAGE` | envelope error | exit 2 | Unknown skill, bad flags, replay without `--cassettes` |
| `RESULT_INVALID` | envelope error | exit 2 | Bench produced a document that breaks its contract (a lab bug) |
| `PATH_FORBIDDEN` | envelope error | exit 4 | `--out`, `--record` or `--cassettes` inside `skills/` |

A result `fail` means the skill (or the model guided by it) did not meet the case; `error` means the
case could not be graded; `skipped` means it was not attempted or not fully graded.

## Security

- Deterministic scripts run without a shell, with list arguments, a minimal environment that carries no
  secrets, and a temporary `HOME`; their paths are confined to the skill folder (`safe_join`).
- Secrets come only from the environment (`OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, `JEV_API_KEY`); results,
  runs and cassettes pass through `_skillkit.redact`, and cassettes never store request headers.
- Model and Jev replies, fixtures and case text are data: they are parsed as JSON, never evaluated.
- CLI runtimes run in an empty temporary folder (`claude` with every tool disabled, `codex` in a
  read-only sandbox) so a model cannot read or edit the repository during a benchmark turn.
- Loopback requests bypass HTTP proxies; everything else honours the environment's proxy and CA settings.

## Runtime compatibility

- Python >= 3.9 standard library only; tested on 3.11, 3.12 and 3.13, checked statically for 3.9 grammar.
- Zed + Ollama local: `num_ctx` 32768 by default, matching GPUs under 24 GB; raise it with `--num-ctx`.
- Zed + Ollama Cloud: no structured outputs; schema in the prompt plus at most two repair turns.
- Claude Code and Codex: their CLIs run single-turn with tools disabled or read-only; results are labelled
  `claude-cli-zed-emulation` and `codex-cli-zed-emulation`.
- `benchmark-result.runtime` must match `^[a-z0-9]+(-[a-z0-9]+)*$`, so the emulation label uses `-zed-emulation`
  rather than `+zed-emulation`; Jev-routed trigger results are labelled `jev-choice`.
