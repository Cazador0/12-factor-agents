# Feature Specification: Scoring and release gates

**Spec**: SPEC-104

**Component**: `skill-lab/lab/score.py`, `skill-lab/benchmarks/criteria/_defaults.json` (family: lab)

**Created**: 2026-10-22

**Status**: Implemented

**Input**: CONVENTIONS §9 ("100 % success means 100 % of the explicitly defined gates pass ... a gate
that did not run never counts as passed", ADR-0010) and §9.6 (`release_ready: true` for the gates that
can run in the current environment, listing which were skipped and why), and the engineering-team
report: measure accepted outcomes against explicit gates, not activity.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One command says whether a skill may ship, and why (Priority: P1)

`skill-lab score --skill review-verifier` combines the validator report, the skill's unit tests and
the latest benchmark run into a `skill-score` with every gate's measured value, threshold and outcome.

**Why this priority**: release decisions must be mechanical and reproducible, not a reading of logs.

**Independent Test**: a scratch skill with passing unit tests, a clean validation report and a
deterministic benchmark run scores `release_ready: true`; the payload validates against `skill-score.v1`.

**Acceptance Scenarios**:

1. **Given** a clean validator report, passing tests and an all-pass deterministic run, **When** the skill is scored offline, **Then** the static, test and deterministic gates pass and the exit code is 0.
2. **Given** one failing unit test, **When** the skill is scored, **Then** `release_ready` is false, `tests.failed` is 1 and the exit code is 1.

---

### User Story 2 - Live gates that could not run are explicit, never silently passed (Priority: P1)

Without a model runtime or Jev, the agentic, trigger and Jev gates cannot be measured. They are
`skipped` with their reason (because the defaults mark them `optional_when_unavailable`), listed in the
envelope warnings, and `release_ready` is qualified by a `RELEASE_READY_OFFLINE` warning. `--strict`
turns them into `not_run`, which blocks release.

**Why this priority**: the user's environment cannot reach Ollama Cloud or TypeSafe yet; scoring must
still work and must say exactly what it did not check.

**Independent Test**: the same scratch skill scores ready offline with four skipped gates, and not ready
with `--strict`.

**Acceptance Scenarios**:

1. **Given** no agentic results, **When** the skill is scored, **Then** `agentic-quality` has `actual: null`, `passed: false`, `skipped: true` and a reason, and a `GATE_SKIPPED` warning names it.
2. **Given** `--strict`, **When** the same skill is scored, **Then** those gates are `not_run`, `release_ready` is false and the `NOT_RELEASE_READY` error lists them.
3. **Given** a mandatory gate whose metric was not measured, **When** the skill is scored, **Then** the gate is `not_run` and blocks release.

---

### User Story 3 - Skills replace or extend the default gates (Priority: P2)

A skill's `benchmarks/criteria/<skill>.json` (`success-criteria.v1`) replaces a default gate or adds a
gate. A replacement may raise a threshold, or lower one only with the sample-size rationale and the
bounding aggregate gate that ADR-0011 §6 requires; criteria files change only through a human-merged PR.

**Why this priority**: SPEC-201 and SPEC-202 set per-skill thresholds (for example agentic >= 0.67 and
trigger >= 0.83) on top of the lab defaults.

**Independent Test**: merge a skill file that overrides one default by id, one by metric, and adds a new
gate; the overrides keep the defaults' optionality and the new gate is mandatory.

**Acceptance Scenarios**:

1. **Given** a skill gate on `bench.trigger.accuracy` with a new id, **When** criteria merge, **Then** it replaces the default trigger gate and stays optional when unavailable.
2. **Given** a skill gate on a metric not in the vocabulary, **When** the skill is scored, **Then** the command fails with `UNKNOWN_METRIC` (exit 2).

### Edge Cases

- No benchmark run with results for the skill: every bench gate is `not_run` (or skipped when optional) with "no benchmark run ... has results".
- A tier whose cases were all skipped: its pass rate is unmeasured, with the first skip reason.
- No `tests/test_*.py`, or `--no-tests`: `tests.*` metrics are unmeasured, so the default unit-test gate is `not_run`.
- No validator report: the static score falls back to the frontmatter lint and is reported, but the static gates are `not_run` because the full validator did not run.
- `eq` gates compare with a 1e-9 tolerance so `0.1 * 10 == 1.0` holds.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: `skill-lab score --skill NAME` MUST accept `--repo`, `--run PATH` (a `benchmark-run.json` or its folder), `--criteria FILE`, `--defaults FILE`, `--validation FILE`, `--no-tests`, `--strict`, `--now` and `--pretty` (a `--skill` that is not a skill name is a `USAGE` error), and print one `envelope.v1` of kind `skill-score` whose payload validates against `skill-score.v1` (`RESULT_INVALID` otherwise).
- **FR-002**: The validator report MUST come from `--validation FILE` (an envelope or a bare `validation-report` payload, validated), else from `lab.validate.main(["--skill", NAME, "--repo", ROOT])` called in-process, else from `bin/skill-lab validate` as a subprocess; when none yields a report for the skill, the static metrics are unmeasured with the reason.
- **FR-003**: The static score MUST be `100 - 25 x errors - 5 x warnings - heuristics`, clamped to 0..100, counting validator findings except those in `ENVIRONMENT_RULES` (`install.not-installed`: this machine's install state, not the skill's quality), where the description heuristics cost 10 (no "Use when"), 5 (outside 350-900 characters) and 5 (fewer than 2 trigger phrases in the "Use when" clause: quoted phrases, or else comma, semicolon or "or" separated parts of its first sentence); failed heuristics are listed as `STATIC_HEURISTIC` warnings; without a validator report the frontmatter lint's issue count stands in as errors and the result is partial.
- **FR-004**: Unit tests MUST run as `python -m unittest discover -s tests -p test_*.py` in the skill folder with a clean environment and a 600 s timeout, and be counted from unittest's summary (ran, passed, failures plus unexpected successes, errors, skipped); the payload's `tests.failed` counts failures and errors.
- **FR-005**: The benchmark run MUST be `--run`, else the run in `skill-lab/benchmarks/runs/*/benchmark-run.json` with the latest `started_at` (then `run_id`) among valid runs that have results for the skill; unreadable or invalid runs are ignored with a `RUN_IGNORED` warning; only the skill's own results are scored.
- **FR-006**: Metrics MUST come from the fixed vocabulary `KNOWN_METRICS`: `static.{score,errors,warnings}`, `tests.{ran,passed,failed,errored,skipped,pass_rate}`, `bench.<tier>.{cases,passed,failed,errored,skipped,pass_rate}`, `bench.{deterministic,agentic}.schema_valid_rate`, `bench.trigger.accuracy` (the trigger pass rate), `bench.jev.judgments` and `bench.jev.uncertain_rate` (uncertain bands over all agentic judgments). An unmeasured metric is null with a recorded reason; rates exclude skipped cases and are null when nothing was graded.
- **FR-007**: Criteria MUST be the lab defaults (`_defaults.json`: success-criteria gates plus `optional_when_unavailable` and a required `optional_reason`) merged with the skill's `success-criteria.v1` file: a skill gate replaces the default with the same `id`, or else the not yet replaced default with the same `metric`, and keeps its optionality; other skill gates are appended as mandatory; duplicate ids and invalid files are `CRITERIA_INVALID`, and unknown metrics are `UNKNOWN_METRIC` (exit 2).
- **FR-008**: Each gate MUST be evaluated with `gte`, `lte`, `gt`, `lt` or `eq` (tolerance 1e-9) into a `gate_result` whose status is `pass`, `fail` (reason "fail: actual op threshold does not hold"), `not_run` (metric unmeasured; reason "not_run: ...") or `skipped` (metric unmeasured, gate `optional_when_unavailable`, no `--strict`; reason "skipped: ... (optional when unavailable: ...)"); an unmeasured gate never passes.
- **FR-009**: `release_ready` MUST be true exactly when no unit test failed or errored and every gate passed or was skipped; the envelope MUST carry a `GATE_SKIPPED` or `GATE_NOT_RUN` warning per such gate, a `RELEASE_READY_OFFLINE` warning when readiness relies on skipped gates, and a `NOT_RELEASE_READY` error listing the failed and not-run gates otherwise; the exit code is 0 when ready and 1 when not.
- **FR-010**: `_defaults.json` MUST define exactly these gates: `static.score >= 90`; `tests.pass_rate == 1.0`; `bench.deterministic.pass_rate == 1.0`; `bench.deterministic.schema_valid_rate == 1.0`; and, optional when unavailable, `bench.agentic.schema_valid_rate >= 0.95`, `bench.agentic.pass_rate >= 0.8`, `bench.trigger.accuracy >= 0.9`, `bench.jev.uncertain_rate <= 0.1`.

### Key Entities

- **Success criteria**: `success-criteria.v1` per skill; the defaults file adds optionality.
- **Gate result**: `{id, metric, op, actual, threshold, passed, skipped, reason}` in `skill-score.v1`.
- **Skill score**: `skill-score.v1`; static, tests, per-tier bench summaries, gates, `release_ready`, `run_id`.

### Readiness levels

`release_ready` in the payload is CONVENTIONS §9.6 readiness: every gate that could run here passed.
Full readiness, every gate measured and passed, is `release_ready` with no `RELEASE_READY_OFFLINE`
warning, or equivalently `skill-lab score --strict` exiting 0. Release checks for live stages (SPEC-201
`complete`) use `--strict` on a run recorded with the live services.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 0 gates with `actual: null` are reported as passed (also enforced by `skill-score.v1`).
- **SC-002**: Offline, a skill whose deterministic, test and static gates pass is release-ready with exactly the four optional gates skipped and named in warnings; with `--strict` it is not.
- **SC-003**: The static score of a description that meets all three heuristics with no validator findings is 100.
- **SC-004**: Every test in `test_score_*.py` passes on Python 3.11, 3.12 and 3.13.

## Assumptions

- `lab.validate.main(argv)` (lab-core) prints one `validation-report` envelope and accepts `--skill` and `--repo`.
- Benchmark runs are written by SPEC-102 bench and are trusted only after schema validation.
- The defaults file lives with the lab (`skill-lab/benchmarks/criteria/_defaults.json`); skill criteria live in the scored repository's `skill-lab/benchmarks/criteria/<skill>.json`.
- `success-criteria.v1` has no optionality field, so optionality is a property of the lab defaults only; making it per-skill would be an additive v1 change.

## Non-goals

- Scoring the whole catalog in one call (`skill-lab score` scores one skill).
- Aggregating several runs or computing streaks (SPEC-202 L1 gates).
- Release-stage gates such as `validate.errors` or `export.drift` (SPEC-201 `release check`).

## Contracts

Consumes: `validation-report.v1`, `benchmark-run.v1` (with `benchmark-result.v1` items),
`success-criteria.v1`. Emits: `skill-score.v1` inside an `envelope.v1` of kind `skill-score`.

## Error semantics

| Code | Where | Exit | Meaning |
|---|---|---|---|
| `NOT_RELEASE_READY` | error | 1 | A gate failed or did not run, or a unit test failed |
| `GATE_SKIPPED`, `GATE_NOT_RUN` | warning | - | One per gate that could not be measured (path `/gates/<i>`) |
| `RELEASE_READY_OFFLINE` | warning | - | Ready only for the gates that could run here |
| `STATIC_HEURISTIC` | warning | - | A description heuristic failed (with its penalty) |
| `RUN_IGNORED`, `VERSION_UNKNOWN` | warning | - | An unusable run file; SKILL.md without semver version (reported as 0.0.0) |
| `SKILL_NOT_FOUND`, `REPO_NOT_FOUND`, `USAGE` | error | 2 | Bad target or flags |
| `CRITERIA_INVALID`, `UNKNOWN_METRIC` | error | 2 | Broken defaults or skill criteria |
| `VALIDATION_INVALID`, `RUN_INVALID`, `INPUT_NOT_FOUND`, `INPUT_NOT_JSON` | error | 2 | Unusable `--validation` or `--run` input |
| `RESULT_INVALID` | error | 2 | The computed score breaks `skill-score.v1` (a lab bug) |

## Security

- Unit tests run as a subprocess with list arguments and a minimal environment (no secrets passed).
- Input files are parsed with the strict JSON reader (no duplicate keys, no NaN) and validated before use.
- The command is read-only: it writes nothing but its envelope on stdout.

## Runtime compatibility

- Python >= 3.9 standard library only; tested on 3.11, 3.12 and 3.13.
- Runtime-independent: the score reads recorded results, so a run from Zed + Ollama, Claude Code or Codex scores the same way.
