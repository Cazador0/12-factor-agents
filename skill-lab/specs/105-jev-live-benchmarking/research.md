# Research: Jev live benchmarking (SPEC-105)

Phase 0 of the plan. Each entry gives the question, the decision, why, and the alternatives that were
rejected. Decisions the person made are cited to the intake (`Q#`) or the specify refinement (`RQ#`).
Everything else is the plan's own decision, and the plan refinement puts the consequential ones to the
person.

## R-1 Which judgments are re-asked

- **Decision**: Only `noul` judgments whose first value falls in the uncertain band [0.35, threshold)
  are re-asked, once, in a second Jev request that holds only those questions.
- **Why**: Q5 and RQ4 define the re-ask for a yes/no grade that is "unsure". `score` and `choice`
  answers have no uncertain band. Their `confidence` measures how concentrated the distribution is,
  and the official TypeSafe skill warns against reading it as correctness (SOURCES.md, Jev).
- **Rejected**: re-asking low-confidence `choice` answers (no person decision, and it would change
  routing results); re-asking all judgments of the case (it doubles cost for no new information).

## R-2 What the re-ask adds to the state

- **Decision**: The second request's state is the first state plus `context.fixtures` (the full text of
  the case's fixture files) and `context.skill` (the skill's `SKILL.md` body), as RQ4 settled. The
  question text is unchanged.
- **Why**: Jev guidance says to give each question enough relevant state, using named JSON fields
  (`typesafe-ai` skill). The data boundary (Q4) still holds, because both additions come from inside the
  skill folder.

## R-3 What counts as an outage

*Confirmed by the person in the plan refinement, 2026-10-22.*

- **Decision**: An outage is a service failure after the client's retries: a connection error,
  HTTP 5xx, or HTTP 429. The case is `errored`, with `error.code` set to `RUNTIME_UNAVAILABLE` or
  `JEV_UNAVAILABLE`, and the run gets the exclusion reason `outage`. HTTP 401/403/422 are not outages:
  they are configuration or case bugs, and they fail the run's preflight or the case.
- **Why**: Q6 and the refined default ("a persisting rate limit is an outage"). A 422 is a bug in the
  case's judgment definition, and treating it as an outage would hide it.

## R-4 How the floor is enforced

- **Decision**: `lab.score.merge_gates` compares each per-skill override with the default it replaces.
  `gte`/`gt` gates may only raise the threshold, `lte`/`lt` gates may only lower it, and `eq` gates may
  not change. A weaker override raises `CRITERIA_BELOW_FLOOR` (exit 2). `lab.validate` runs the same
  comparison as rule `criteria.below-floor`, so CI catches it before `score` runs.
- **Why**: The gates decision ("a skill may raise a gate but never lower it") and SPEC-104 User Story 3.
  One comparator in `lab.score`, imported by `lab.validate`, keeps the two from drifting.

## R-5 Catalog-level gates

- **Decision**: `_defaults.json` gates gain `scope` (`skill` or `catalog`, default `skill`).
  `skill-lab score --catalog --run PATH` evaluates the catalog-scope gates over all results in the run
  and emits a `skill-score.v1` with `skill` set to `catalog`. Release gates read both.
- **Why**: The gates decision ("both levels"). Reusing `skill-score.v1` keeps one gate-result shape.
- **Rejected**: a separate catalog contract, which is extra surface for the same fields.

## R-6 Guardrail metric

- **Decision**: New metric `bench.agentic.guardrail.pass_rate`: the pass rate of agentic cases tagged
  `guardrail`. Default gate `eq 1.0` with scope `skill`, optional only when no agentic case was graded.
- **Why**: RQ5 ("100% for guardrails"). SPEC-104's `KNOWN_METRICS` is a fixed vocabulary, so the metric is
  added there rather than computed ad hoc by the release check.

## R-7 Streak computation

- **Decision**: `lab/streak.py` reads every committed `skill-lab/benchmarks/runs/*/benchmark-run.json`,
  orders them by `started_at`, drops non-counting runs (recording their reasons), and walks back from
  the newest counting run while the model and `suite_digest` stay the same and every bench-tier gate
  passes, at both levels. A case that passed in an earlier run of the current streak and fails later
  ends the streak and is listed unstable. `local_unlock_evidence` is `length ≥ 3`.
- **Why**: Q3, Q13, D2, RQ2. Gate evaluation reuses `lab.score.evaluate_gate` over the bench metrics only
  (static and test gates are per-commit, not per-run).

## R-8 Token usage and cost

*Confirmed by the person in the plan refinement, 2026-10-22.*

- **Decision**: Runtimes already return `usage`, and the Jev client returns `usage.input_tokens` and
  `output_tokens`. Bench stores them in `benchmark-result.usage` and totals them per skill and overall in
  `benchmark-run.usage`. Cost = Σ tokens × price per million tokens from `skill-lab/benchmarks/prices.json`.
  A service or model with no entry contributes `null`, and the run's `cost.basis` is `price-table` only
  when every contributor has a price, otherwise `usage-only`.
- **Why**: Q16, Q7 (no cap), RQ3 (a person-maintained price table). A partly priced run reports
  `usage-only` instead of a misleading partial sum.

## R-9 Container measurement without packages

*Confirmed by the person in the plan refinement, 2026-10-22.*

- **Decision**: `run-monitor` reads `/proc/stat` twice, 0.5 s apart, for CPU; `/proc/meminfo`
  (`MemAvailable`) for memory; `shutil.disk_usage` for disk free on the repo's filesystem; and the
  number of numeric entries in `/proc` for processes. Where `/proc` does not exist (macOS), CPU, memory
  and processes are `null` with a note, and disk still comes from `shutil`.
- **Why**: ADR-0006 (stdlib only, Python ≥ 3.9). A `null` figure can never cross a limit, so it can
  never fabricate a degraded run; the note keeps the gap visible.
- **Decision, target `local-container`** (*the person's answer, 2026-10-22, release alignment*: "run-monitor for
  Rancher Desktop local containers", read from inside each container): an additive target kind for the person's
  Rancher Desktop local containers, where SPEC-202's local-inference runs and SPEC-203's webhook gateway run.
  `snapshot.py --target local-container` runs inside the container doing the work (bench or the gateway starts it as a
  child process there) and reads only that container's own figures:
  - **cgroup v2** (`/sys/fs/cgroup/cgroup.controllers` exists): CPU from `cpu.stat` `usage_usec`, read twice 0.5 s
    apart, against the limit in `cpu.max` (`<quota> <period>` gives quota ÷ period cores; `max` means no limit, so the
    CPUs visible inside the container, `os.cpu_count()`, with note `CPU_LIMIT_UNSET`); `cpu_percent` = Δusage ÷
    (0.5 s × cores) × 100. Memory: `memory.current` over `memory.max`; `max` means no limit, so `MemTotal` from the
    container's own `/proc/meminfo`, with note `MEMORY_LIMIT_UNSET`.
  - **cgroup v1 fallback**: `cpuacct.usage` (ns) with `cpu.cfs_quota_us` and `cpu.cfs_period_us` (quota −1 = no
    limit), and `memory.usage_in_bytes` with `memory.limit_in_bytes`, under `/sys/fs/cgroup/cpu,cpuacct/` (or
    `cpuacct/` and `cpu/`) and `/sys/fs/cgroup/memory/`.
  - **Neither readable**: `cpu_percent` and `memory_percent` are `null` with note `CGROUP_UNAVAILABLE`, so they cannot
    mark a run degraded.
  - Disk free: `shutil.disk_usage` of the working directory as seen inside the container. Processes: the numeric
    entries of the container's own `/proc`.
  - `container.cgroup` records the version read and the limits and use behind the percentages (data-model.md).
  - It opens no Docker or containerd socket, runs no container CLI, and reads no path outside `/sys/fs/cgroup`,
    `/proc`, and the working directory; a test asserts this over the files the script opens. Tests point the reader at
    fake cgroup v2 and v1 trees the same way they point it at fake `/proc` files.
- **Why**: the person's answer: monitoring runs inside each container and reads that container's own CPU and memory
  limits and use, with no socket access and nothing else on the machine. A container's cgroup files are where it sees
  its own limits from inside. The change is additive (one enum value, one optional object), so `run-health.v1` stays v1.
- **Rejected**: a Docker or containerd socket (not chosen; it would expose every container and the host); the host's
  `/proc` (nothing else on the machine is read); turning the container figures off on local runs (the earlier
  `--host-metrics off` design, withdrawn because it left memory and disk trouble undetected).

## R-10 Session metrics from the run log

- **Decision**: A model session is one agentic case's conversation. Turns = 1 + repair turns; tool calls
  = 0 (single-shot cases); context used = the prompt token count the runtime reports; context limit =
  the model's context when the runtime reports it, else `null`; stalled = no run-log event for that
  case within the no-progress limit; end reason = case status. The reviewer session reports the same
  fields about itself where it can, and `null` where it cannot.
- **Why**: Q18 ("agent session metrics"). The log already has every figure, so no second channel is needed.

## R-11 The advisory agent call

- **Decision**: After each skill's snapshot, bench sends one request through the run's runtime. The
  system prompt is the Zed-style skill envelope of `run-monitor`'s `SKILL.md`, built by
  `lab.runtimes.zed_emulation`. The user content is the health report. The reply must be JSON
  `{summary, recommendations[]}`, which Ollama Cloud gets via the schema-in-prompt plus repair path. The
  reply is stored as `assessment`; if the call fails, the report holds `assessment_error` and nothing else
  changes.
- **Why**: RQ1 ("script decides, agent explains") and ADR-0005 (the LLM advises, code decides). Using the
  run's own model adds no new variable to the gate run.

## R-12 Where the reviewer's health report goes

*Confirmed by the person in the plan refinement, 2026-10-22.*

- **Decision**: The reviewer posts its `run-health.v1` as a **separate** PR comment with its own marker
  line, `<!-- skill-lab:run-health:v1 request_id=<id> -->`, next to the verdict comment.
- **Why**: SPEC-201 FR-035 requires the verdict comment to hold exactly one fenced `json` block, and
  `review_collect.py` rejects a second block as `VERDICT_AMBIGUOUS`. A separate marked comment keeps that
  rule intact and still puts the report "alongside its verdict" (Q23).
- **Rejected**: embedding the report in `review-verdict.v1`, which is a contract change for a monitoring
  concern; a second fenced block, which breaks FR-035.

## R-13 Run log format and size

*Confirmed by the person in the plan refinement, 2026-10-22.*

- **Decision**: `run.log.jsonl` with one JSON object per line: `{ts, event, skill?, case_id?, ...}`,
  where `event` is one of `run_start`, `case_start`, `case_end`, `request`, `health_check`,
  `assessment` or `run_end`. Request events hold service, latency, status, retries and rate-limit
  waits, and never request or response bodies. Every line goes through `_skillkit.redact`.
- **Why**: Q17 asks for system logging. Bodies already live in the result files, so the log stays small
  and safe to commit (Q9).

## R-14 Choosing the one cloud model

- **Decision** (Delegated, Q11): Once the network is allowlisted, list the models with
  `curl https://ollama.com/api/tags`. Choose the largest general model whose Ollama page lists tool
  support, record it with the date in `skill-lab/config/zed/cloud-models.json` and SOURCES.md, and pass
  it as `--model`.
- **Why**: Q11 delegated the choice. A larger model gives the gate the best chance to measure the
  skills rather than the model's limits.

## R-15 Smoke cases

*Confirmed by the person in the plan refinement, 2026-10-22.*

- **Decision**: Tag `smoke` on 1 agentic case of `lead-architect` and 1 routing case each of
  `lead-architect` and `review-verifier`. These are the two skills whose cases exist earliest in R1.
- **Why**: The refined default (≥ 1 agentic and ≥ 2 routing cases from ≥ 2 skills, Q12).
