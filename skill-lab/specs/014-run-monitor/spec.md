# Feature Specification: `run-monitor` skill

**Spec ID**: SPEC-014 | **Skill**: `skills/run-monitor/` | **Family**: `control-plane`, **secondary family**: `meta` | **Used by**: bench after each skill, the independent reviewer, the R2 local-inference runs, the R3 webhook gateway

**Created**: 2026-10-28 | **Status**: Draft (planned; written by SPEC-201 T152; script built by SPEC-105 T025–T026, T041–T042)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-032, FR-033, FR-048 (US10);
[SPEC-202](../202-release-agent-implementation/spec.md) FR-042, FR-048, FR-049; [SPEC-203](../203-release-guarded-autonomous/spec.md) FR-053, FR-057, FR-058;
[SPEC-105](../105-jev-live-benchmarking/spec.md) FR-007, FR-016, FR-019..FR-023, research R-9..R-11. The release specs are authoritative; this spec refines them
and never contradicts them. SPEC-105's tasks own `scripts/snapshot.py`, its tests, and the `run-health.v1` schema (SPEC-105 plan §Ownership with SPEC-201);
SPEC-201's tasks own this spec, `SKILL.md`, and the eval cases.

**Input**: the person's intake answers Q17..Q24 (runs complete under system logging, system monitoring, and periodic agent-skill performance checks; a
`run-monitor` skill called after each skill and by the reviewer in its own container), the family decision (control-plane plus meta, SPEC-201 §Clarifications),
and the 2026-10-22 answers: "run-monitor for Rancher Desktop local containers", read from inside each container, with no Docker or containerd socket and
nothing else on the machine (SPEC-105 FR-020, R-9).

## Intent

`run-monitor` answers one question: is the place this work runs in healthy enough for the result to count? A single read-only script takes a snapshot of the
container it runs in, the APIs, and the model sessions recorded in a run log, and a fixed set of limits alone decides `ok` or `degraded`. The model, following
`SKILL.md`, only explains the snapshot in an advisory assessment. The same script serves the live gate run (after each skill), the reviewer session (in its own
container, posted with its verdict), R2's local-inference runs, and R3's webhook gateway (both inside the person's Rancher Desktop local containers, target
`local-container`). It performs no catalog action at any level.

## User Scenarios & Testing *(mandatory)*

Scenarios run offline over fake `/proc` and cgroup trees (`--proc-root`, `--cgroup-root`, fixtures under `skills/run-monitor/evals/fixtures/`), a fixed
limits file equal to `skill-lab/benchmarks/monitor-limits.json` (memory ≥ 90 %, disk free < 1 GiB, API error rate ≥ 5 %, no progress for 600 s), and run logs
under `evals/fixtures/logs/`. Times use `--now`; T = 2026-10-22T08:00:00Z. **Actions: none in any story** (read-only; output on stdout or under `--out`).

### User Story 1 - Snapshot the benchmark container; healthy means ok (Priority: P1) · R1 shadow

**Independent Test**: `skills/run-monitor/tests/test_snapshot.py`; `skill-lab/tests/integration/test_us10_run_monitor.py` (SPEC-201 T155).

1. **Given** fake `/proc` readings and a run log below every limit, **When** `snapshot.py --target benchmark-container --skill lead-architect --run-log <log> --limits <limits>`
   runs, **Then** it exits 0 with a schema-valid `run-health.v1`: `status: ok`, empty `problems[]`, `container{cpu_percent, memory_percent, disk_free_bytes, processes}`,
   `limits` with the file's digest, and `taken_at` = `--now` (SPEC-201 US10 scenario 1).
2. **Given** no `--run-log`, **Then** `apis[]` and `sessions[]` are empty and `run_id` is `null` unless `--run-id` is given.

### User Story 2 - A crossed limit marks the run degraded and nothing else (Priority: P1) · R1 shadow

**Independent Test**: `test_snapshot.py::TestLimits`; `skill-lab/tests/test_live_monitor.py` (SPEC-105 T027).

1. **Given** memory at 91 %, **When** `snapshot.py` runs, **Then** `status` is `degraded`, `problems[]` holds one entry `{code: MEMORY_HIGH, metric: container.memory_percent, actual: 91, limit: 90}`, the envelope has `ok: true` with warning `RUN_DEGRADED`, and the exit code is 0.
2. **Given** disk free 900 MB, or an API error rate of 6 % within the skill, or a session with no log event for 601 s, **Then** `problems[]` names `DISK_LOW`, `API_ERROR_RATE`, or `SESSION_STALLED` respectively; several crossed limits give several problems (SPEC-201 US10 scenario 2).
3. **Given** readings exactly at a limit boundary (memory 90.0 %, error rate 0.05, free disk 1,073,741,824 bytes, 600 s), **Then** memory and error rate and no-progress are `degraded` (≥) and disk free is `ok` (strict `<`).
4. **Given** a figure that is `null` (no `/proc`, no cgroup), **Then** it never creates a problem: a missing figure cannot mark a run degraded.
5. **Given** the same inputs and `--now`, **Then** two runs give byte-identical stdout.

### User Story 3 - API health and sessions come from the run log (Priority: P1) · R1 shadow

**Independent Test**: `test_snapshot.py::TestRunLog`.

1. **Given** a run log with requests to `ollama-cloud` and `typesafe` (latency, status, retries, rate-limit waits), **When** `snapshot.py --skill S` runs, **Then** `apis[]` holds one entry per service with `requests`, `p50_ms`, `p95_ms`, `error_rate`, `rate_limited`, and `retry_wait_ms`, computed only over events of skill S (SPEC-105 R-10).
2. **Given** agentic cases in the log, **Then** `sessions[]` has one entry per case with `turns` (1 + repair turns), `tool_calls` (0), `context_used` (prompt tokens the runtime reported), `context_limit` (or `null`), `stalled`, and `end_reason` (case status).
3. **Given** a malformed line in the log, **Then** it is skipped with warning `RUN_LOG_LINE_SKIPPED` and the line number; a missing log file exits 2 `INPUT_NOT_FOUND`.

### User Story 4 - The snapshot leaks nothing and writes only where told (Priority: P1) · R1 shadow

**Independent Test**: `test_snapshot.py::TestHygiene` (opened-files assertion, canary environment).

1. **Given** the environment holds canary values (`OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, `GITEA_TOKEN`, a secret in an argv), **When** `snapshot.py` runs, **Then** no stdout, stderr, or `--out` file contains a canary, no environment value, and no command line with arguments (SPEC-201 US10 scenario 3).
2. **Given** any run, **Then** the script opened only `/proc` (or `--proc-root`), `/sys/fs/cgroup` (or `--cgroup-root`), the working directory's filesystem for disk figures, `--run-log`, `--limits`, and `--out`; it made no network call, opened no socket, and started no subprocess.
3. **Given** `--out` outside the working directory (`../x`, an absolute path elsewhere, or a symlink escaping it), **Then** it exits 4 `PATH_NOT_ALLOWED` and writes nothing.

### User Story 5 - Watch a Rancher Desktop local container from inside it (Priority: P1) · R1 shadow

**Independent Test**: `skills/run-monitor/tests/test_snapshot_local_container.py` (SPEC-105 T041).

1. **Given** a fake cgroup v2 tree (`cpu.stat` read twice, `cpu.max` `200000 100000`, `memory.current`, `memory.max`), **When** `snapshot.py --target local-container` runs, **Then** `target.kind` is `local-container` with the container hostname as `id`; `cpu_percent` = Δ`usage_usec` ÷ (interval × 2 cores) × 100; `memory_percent` = `memory.current` ÷ `memory.max` × 100; `container.cgroup` = `{version: 2, cpu_limit_cores: 2, memory_limit_bytes, memory_used_bytes}`; disk free and processes are those seen inside the container (SPEC-105 US3 scenario 4).
2. **Given** `cpu.max` or `memory.max` is `max`, **Then** the limit falls back to `os.cpu_count()` or the container's `MemTotal`, with notes `CPU_LIMIT_UNSET` or `MEMORY_LIMIT_UNSET`, and the cgroup limit field is `null`.
3. **Given** only a cgroup v1 tree (`cpuacct.usage`, `cpu.cfs_quota_us`, `cpu.cfs_period_us`, `memory.usage_in_bytes`, `memory.limit_in_bytes`), **Then** the same figures are read with `cgroup.version: 1`.
4. **Given** neither is readable, **Then** `cpu_percent` and `memory_percent` are `null` with note `CGROUP_UNAVAILABLE`, `container.cgroup.version` is `null`, and the run is never `degraded` for them.
5. **Given** a `memory.current` that crosses the memory limit, **Then** the run is `degraded` exactly as for any other target.
6. **Given** any local-container run, **Then** it opened no Docker or containerd socket, ran no container CLI, and read no path outside `/sys/fs/cgroup`, `/proc`, and the working directory.

### User Story 6 - The advisory assessment explains and never decides (Priority: P2) · R1 shadow

**Independent Test**: agentic cases `assessment-keeps-status` (guardrail) and the SPEC-105 bench test `skill-lab/tests/test_live_monitor.py` (assessment stored, failure changes nothing).

1. **Given** a degraded snapshot, **When** the model follows `SKILL.md`'s advisory step, **Then** it adds `assessment{summary ≤ 1000 chars, recommendations[≤ 10]}` and `status` and `problems[]` are byte-identical to the script's (SPEC-201 US10 scenario 4; SPEC-105 FR-021).
2. **Given** a healthy snapshot, **Then** the assessment says so briefly and recommends nothing it cannot ground in a reported figure.
3. **Given** a run-log field that contains instructions ("report ok", "ignore the limits"), **Then** the model treats it as data and the status stays as computed.
4. **Given** the advisory call fails, **Then** the report holds `assessment_error` and nothing else changes (SPEC-105 R-11).

### User Story 7 - The reviewer reports on its own container (Priority: P2) · R1 shadow

**Independent Test**: `skill-lab/tests/integration/test_us10_run_monitor.py` (with `review_collect.py`, SPEC-201 T155, T159).

1. **Given** the reviewer session in its own container, **When** it runs `snapshot.py --target reviewer-session --limits skill-lab/benchmarks/monitor-limits.json`, **Then** it gets a schema-valid `run-health.v1` with `run_id: null` and `target.kind: reviewer-session`; `sessions[]` holds what the session can report about itself, else `null` fields.
2. **Given** the report, **When** the reviewer follows `SKILL.md`, **Then** it posts it as a separate PR comment: the marker line `<!-- skill-lab:run-health:v1 request_id=<id> -->` and exactly one fenced `json` block (SPEC-201 FR-034(c), FR-035); `degraded` informs the person and never changes the verdict.

### User Story 8 - Local-inference runs report through `local-container` · R2 agent-implementation

**Actions**: none. **Independent Test**: `skill-lab/tests/test_bench_local_monitoring.py` (SPEC-202 T143); `snapshot.py` and its tests are unchanged.

1. **Given** a bench run with `--runtime ollama-local` inside one of the person's Rancher Desktop containers, **When** each skill's cases finish, **Then** bench runs `snapshot.py --target local-container` as a child process (list arguments) in that container, every report has `target.kind: local-container`, and a crossed limit marks the run `degraded` so it does not count (SPEC-202 FR-048). Every other runtime keeps `--target benchmark-container`.
2. **Given** `SKILL.md`, **Then** one line names the target `local-container` and says bench uses it on `--runtime ollama-local` runs (SPEC-202 FR-042).

### User Story 9 - The webhook gateway watches its own container each tick · R3 guarded-autonomous

**Actions**: none. **Independent Test**: `skills/gitea-event-normalizer/tests/test_serve.py` (SPEC-203 T071, T072); `run-monitor` files stay byte-identical (SPEC-203 T136).

1. **Given** the gateway inside a Rancher Desktop container, **When** a `reconcile.tick` record is processed, **Then** it runs `snapshot.py --target local-container --skill gitea-event-normalizer --limits <monitor-limits.json> --out <state>/gateway/health/` as a subprocess with list arguments, and the report lands at `gateway/health/<taken_at>.json` with `run_id: null`, `apis[]` and `sessions[]` empty (no `run.log.jsonl`).
2. **Given** a `degraded` report, **Then** the gateway logs `RUN_DEGRADED` and changes no record, route, decision, or state, and makes no advisory model call (SPEC-203 FR-058).
3. **Given** R3, **Then** `snapshot.py`, `run-health.v1`, and `monitor-limits.json` are byte-identical to their R2 content; only the vendored `_skillkit` is refreshed.

### Edge Cases

- `/proc` is absent (macOS host): CPU, memory, and processes are `null` with note `PROC_UNAVAILABLE`; disk still comes from `shutil.disk_usage`; no problem is raised for the nulls.
- `/proc/stat` shows no change over the sample interval: `cpu_percent` is `0.0`, not `null`.
- `monitor-limits.json` is missing, not strict JSON, or lacks a key: exit 2 `LIMITS_INVALID`; the script never guesses a limit.
- A run log from a different run than `--run-id`: events carry the id; mismatching events are ignored with warning `RUN_LOG_RUN_MISMATCH`.
- `--skill` names a skill with no events: `apis[]` and `sessions[]` are empty and the run is not degraded by them.
- The snapshot takes longer than 5 s (slow `/proc`): it still completes; no timeout kills a measurement mid-write of `--out` (atomic write).
- Two snapshots into the same `--out` directory in one second: the file name is `<taken_at>.json` with a numeric suffix `-2`, never overwritten.
- The model's assessment is missing or malformed: bench stores `assessment_error`; a reviewer comment without an assessment is still valid.

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: `snapshot.py` MUST emit `run-health.v1` for the container it runs in: `cpu_percent` from two `/proc/stat` reads one `--sample-interval` (default 0.5 s) apart, `memory_percent` from `MemAvailable` over `MemTotal` in `/proc/meminfo`, `disk_free_bytes` from `shutil.disk_usage` of the working directory, and `processes` as the count of numeric entries in `/proc`. Implements: SPEC-105 FR-020, R-9; SPEC-201 FR-048.
- **FR-002**: Where `/proc` does not exist, CPU, memory, and processes MUST be `null` with note `PROC_UNAVAILABLE` and disk still from `shutil`; a `null` figure MUST NOT create a problem. Implements: SPEC-105 R-9.
- **FR-003**: `apis[]` MUST be derived from `--run-log` per service (`requests`, `p50_ms`, `p95_ms`, `error_rate`, `rate_limited`, `retry_wait_ms`), restricted to events of `--skill` when given; malformed lines MUST be skipped with warning `RUN_LOG_LINE_SKIPPED`. Implements: SPEC-105 FR-019, FR-020, R-10.
- **FR-004**: `sessions[]` MUST list one entry per agentic case or session in the log with `turns`, `tool_calls`, `context_used`, `context_limit`, `stalled` (no log event within `no_progress_seconds_max`), and `end_reason`; fields the log cannot supply are `null`. Implements: SPEC-105 FR-020, R-10.
- **FR-005**: `status` MUST be `degraded` iff `problems[]` is non-empty, and `problems[]` MUST be computed only from the figures and `--limits` (memory ≥ `memory_percent_max`, disk free < `disk_free_bytes_min`, any API error rate ≥ `api_error_rate_max`, any session stalled ≥ `no_progress_seconds_max`); `limits` MUST copy the file's values with its sha256; a degraded result MUST exit 0 with warning `RUN_DEGRADED`; no model output or environment variable MAY influence it. Implements: SPEC-105 FR-021, FR-022; SPEC-201 FR-048.
- **FR-006**: `--target local-container` MUST read the container's own cgroup figures: cgroup v2 (`cpu.stat` twice against `cpu.max`; `memory.current` against `memory.max`), else cgroup v1, else `null` with note `CGROUP_UNAVAILABLE`; `max` limits fall back with notes `CPU_LIMIT_UNSET` and `MEMORY_LIMIT_UNSET`; `container.cgroup` records the version and the limits and use behind the percentages; `target.id` is the container hostname; disk free and process count are those seen inside the container. Implements: SPEC-105 FR-020, R-9; SPEC-201 FR-048.
- **FR-007**: The script MUST be read-only and hygienic: it MUST NOT read or print environment values or command lines, open a network connection, a Docker or containerd socket, or any socket, run a container CLI or any subprocess, or read any path outside `/proc`, `/sys/fs/cgroup`, the working directory, `--run-log`, `--limits`, and the seam roots (which must lie under the working directory); output goes to stdout or `--out`, which must lie under the working directory (else exit 4 `PATH_NOT_ALLOWED`). Implements: SPEC-201 FR-048; SPEC-105 FR-020, §Security.
- **FR-008**: `--out PATH` MUST accept a file or a directory; for a directory it MUST write `<taken_at>.json` (suffix `-2`, `-3` on collision), atomically through `fsutil.atomic_write_json`, containing the `run-health.v1` payload; stdout is always the `envelope.v1`. `--target` is one of `benchmark-container`, `model-session`, `reviewer-session`, `local-container`; `--run-id` defaults to `null`. Implements: SPEC-105 FR-021; SPEC-203 FR-058 (gateway invocation).
- **FR-009**: `SKILL.md` MUST satisfy CONVENTIONS §2 (`metadata.spec: SPEC-014`, `family: control-plane`, `secondary_family: meta`, version `0.1.0`, body ≤ 250 lines and 12 KB) and its procedure MUST (1) run `python3 scripts/snapshot.py` with the target kind of the place it runs, (2) write the advisory `assessment{summary, recommendations[]}` without changing `status` or `problems[]`, (3) for the reviewer use `--target reviewer-session` and the separate marked comment with one fenced `json` block, (4) state the guardrails (no environment values, no command lines with arguments, nothing written outside `--out`). Implements: SPEC-201 FR-032, FR-048; SPEC-105 FR-021, FR-023.
- **FR-010**: `snapshot.py` MUST follow CONVENTIONS §3 (stdlib only, one envelope, exit codes 0–4, `--now` determinism, no write inside the skill folder) and expose the deterministic-case seams `--proc-root`, `--cgroup-root`, `--sample-interval`; in a seam root a second sample is read from `stat.next` or `cpu.stat.next` when present, so no case sleeps. Implements: SPEC-201 FR-032.
- **FR-011**: R1 MUST ship ≥ 4 deterministic cases (including `snapshot-ok-below-limits`, `snapshot-degraded-memory`, `snapshot-no-environment-values`, `snapshot-without-proc-is-null`, `snapshot-local-container-cgroup-v2`), no `policy` case (the skill references no catalog action), ≥ 5 agentic cases (≥ 1 `guardrail`, `assessment-keeps-status`) with fixtures inside the skill folder, ≥ 10 trigger cases (≥ 4 positive, ≥ 2 `expect_skill: null`, ≥ 1 naming `skill-forge`), and no per-skill criteria file. Implements: SPEC-201 FR-033; SPEC-105 FR-007, FR-016.
- **FR-012**: The skill MUST be listed under both families `control-plane` and `meta` in `skills/CATALOG.json` and `skills/README.md`, and MUST be registered in the Zed skill and skill-script allowlists and the Claude `Skill(...)` rules. Implements: SPEC-201 FR-032 (CONVENTIONS §2, §6).

**R2 agent-implementation**

- **FR-013**: R2 MUST leave `scripts/snapshot.py`, `run-health.v1`, and `monitor-limits.json` unchanged and MUST add to `SKILL.md`, in one line, that `--target local-container` exists and that bench uses it on `--runtime ollama-local` runs inside the person's Rancher Desktop container; the advisory assessment goes through the run's own runtime and model. Implements: SPEC-202 FR-042, FR-048.

**R3 guarded-autonomous**

- **FR-014**: R3 MUST change no script of this skill: `scripts/snapshot.py`, `run-health.v1`, and `monitor-limits.json` stay byte-identical (a limits change needs the person's approval; no agent edits the file); `skill-lab sync` refreshes the vendored `_skillkit` only, and `skill-lab validate` and the deterministic tier re-run. Implements: SPEC-203 FR-058.
- **FR-015**: The invocation used by the webhook gateway (`--target local-container --skill gitea-event-normalizer --limits … --out <dir>` with no `--run-log`) MUST work unchanged: `run_id: null`, empty `apis[]` and `sessions[]`, the report written to `<dir>/<taken_at>.json`, and `degraded` informational only. Implements: SPEC-203 FR-058; SPEC-105 FR-020.
- **FR-016**: R3 reviewer instructions (SPEC-203 FR-057) MUST keep working with this skill: `--target reviewer-session` in the reviewer's own container, posted as a separate marked comment that `review_collect.py` requires. Implements: SPEC-203 FR-057; SPEC-105 FR-023.

### Key Entities

- **Health report** (`run-health.v1`): one snapshot of a container, the APIs, and the sessions, with its decision (`status`, `problems[]`) and an optional advisory `assessment`.
- **Monitor limits** (`skill-lab/benchmarks/monitor-limits.json`): the four fixed limits; human-maintained and applied only with the person's approval.
- **Run log** (`run.log.jsonl`): the structured bench log (case, request, and health-check events) that the API and session figures come from.
- **Target**: where the snapshot is taken: `benchmark-container`, `model-session`, `reviewer-session`, or `local-container`.
- **Health comment**: the reviewer's separate PR comment carrying one `run-health.v1` block under the marker line.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In 100 % of fixture runs, `status` equals the verdict recomputed from the limits and the reported figures, and a `null` figure never causes `degraded`.
- **SC-002**: 0 canary values, environment values, or command lines appear in stdout, stderr, or any `--out` file; the opened-files assertion lists only allowed paths (SPEC-201 US10 scenario 3).
- **SC-003**: For `local-container`, cgroup v2, cgroup v1, and unavailable fixtures give the documented figures and notes, with 0 socket or out-of-scope path opens (SPEC-105 US3 scenario 4).
- **SC-004**: Every run twice with the same `--now` and fixture roots gives byte-identical stdout.
- **SC-005**: The agentic guardrail `assessment-keeps-status` passes at 100 %, and the skill meets SPEC-105's floor per skill on each live gate run.
- **SC-006**: R3: the three files named in FR-014 are byte-identical to R2 (`git diff --exit-code`, SPEC-203 T136).

## Non-goals

- Reading the host, other containers, or anything outside the container it runs in; any Docker or containerd socket or container CLI (the person's decision, 2026-10-22).
- Deciding degradation with a model, tuning or editing `monitor-limits.json` (the person approves any change), or blocking the run: a degraded run completes and does not count.
- Alerting, paging, or dashboards; metrics retention; collecting the verdict (`speckit-development`); scaffolding or checking skills (`skill-forge`).
- Metrics for the person's machine outside Rancher Desktop containers.
- A per-skill criteria file (the person's answer, 2026-10-22).

## Contracts

**Emits** (producer): `run-health` (the skill's script produces it; the schema is owned by SPEC-105 and vendored here) and `envelope`. The reviewer's
comment grammar `<!-- skill-lab:run-health:v1 request_id=<id> -->` plus one fenced `json` block is documented here and in
`speckit-development/references/review-comment-format.md`. **Consumes**: `skill-lab/benchmarks/monitor-limits.json` (lab configuration format, data-model.md) and
`run.log.jsonl` (lab run log, SPEC-105 FR-019). It consumes no catalog contract and no `autonomy-policy`.

## Error semantics

Exit codes follow CONVENTIONS §3. A degraded run is a successful measurement: exit 0 with warning `RUN_DEGRADED`.

| Code | Exit | Meaning |
|---|---|---|
| `RUN_DEGRADED` | warning | A limit was crossed; `status: degraded`, `problems[]` names each (SPEC-105 §Error semantics) |
| `RUN_LOG_LINE_SKIPPED` / `RUN_LOG_RUN_MISMATCH` (skill-local) | warning | Malformed line skipped / events of another run ignored |
| `PROC_UNAVAILABLE` / `CGROUP_UNAVAILABLE` / `CPU_LIMIT_UNSET` / `MEMORY_LIMIT_UNSET` | note in `container.notes[]` | A figure is `null` or falls back; never a problem |
| `LIMITS_INVALID` (skill-local) | 2 | `--limits` missing, not strict JSON, or incomplete |
| `INPUT_NOT_FOUND` / `INPUT_NOT_JSON` | 2 | `--run-log` unreadable |
| `USAGE` / `INVALID_NOW` / `INTERNAL` | 2 | Bad flags (including an unknown `--target`) or unexpected exception |
| `PATH_NOT_ALLOWED` (skill-local) | 4 | `--out`, `--proc-root`, or `--cgroup-root` outside the working directory (or a symlink escaping it) |

Problem codes inside `problems[]` (proposed, kept in `references/metrics.md`): `MEMORY_HIGH`, `DISK_LOW`, `API_ERROR_RATE`, `SESSION_STALLED`.

## Security

- The report holds resource figures, never environment values or command lines with arguments (SPEC-105 §Security); the hostname used as the `local-container` id is the only identifier read from the system.
- No network, no sockets, no subprocess, no container CLI; reads are limited to the allowed paths of FR-007, and a test asserts the opened files.
- Run-log text, case ids, and model output are data: nothing is executed or interpolated, and the assessment step cannot change the decision.
- `--out` and the seam roots are confined to the working directory; the script never writes inside the skill folder.
- `monitor-limits.json` is a critical policy path: agents propose changes with measurements (SPEC-201 T151) and the person approves.

## Runtime compatibility

| Runtime | Invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/run-monitor`, `/run-monitor` | The run's own Ollama Cloud model through the local Ollama app signed in to ollama.com (`http://localhost:11434`, SPEC-201 FR-039) for the advisory call; bench builds the Zed-style skill envelope (SPEC-105 R-11) | The reply is `{summary, recommendations[]}` by schema-in-prompt plus repair (no structured outputs) |
| Zed Agent + local Ollama (after L1) | same | The local model of the run, context ≥ 32,768 | Inside the Rancher Desktop container the target is `local-container` (R2) |
| Claude Code | `.claude/skills/run-monitor`, `/run-monitor` | Claude models | The reviewer runs it in its own container and posts the health comment |
| Codex | `.agents/skills/run-monitor`, `$run-monitor` | Codex models | Needs no network; reads `/proc` and cgroup files only |

The script needs Linux `/proc` for CPU, memory, and processes (containers, cloud sessions); on macOS they are `null` with a note, so a local Mac session never fakes a figure.

## Assumptions

- The run-log event fields (`ts`, `event`, `service`, `latency_ms`, `status`, `retries`, `rate_limited`, `retry_wait_ms`, `skill`, `case_id`, `prompt_tokens`, `context_limit`, `end_reason`) are the names SPEC-105's `lab/runlog.py` writes; the real names are reconciled at SPEC-105 T026 and recorded in `interface-notes.md`.
- Problem code names and the exit 0 for a degraded run are proposed here and reconciled with SPEC-105 T025 at build time; the decision rule itself is fixed by SPEC-105 FR-022.
- The advisory assessment is merged into the stored report by bench (SPEC-105 T029) and, for the reviewer, by pasting the model's JSON into the health comment; a merge flag in `snapshot.py` would be a SPEC-105 change and is not planned.
- SPEC-202's task list still names `skills/run-monitor/tests/test_snapshot_host_metrics_off.py` in a T-series Independent Test line; the `--host-metrics off` design was withdrawn (SPEC-105 R-9), so no such test is planned here.
