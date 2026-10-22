# Feature Specification: Jev live benchmarking

**Feature Branch**: `105-jev-live-benchmarking`

**Spec ID**: SPEC-105

**Created**: 2026-10-22

**Status**: Specified and refined (2026-10-22)

**Input**: Answered intake `intakes/jev-live-benchmarking/intake.md` (24 questions, 7 rounds). Gate and
replay decisions from the person on 2026-10-22: "More cases, both levels" and "All four layers in R1".

## Intent

Run skill-factory's agentic and routing benchmarks live against one Ollama Cloud model, graded by
TypeSafe's Jev model, as the R1 release gate. Post the scores on the release PR for the person and the
independent reviewer session. Runs go to completion under system logging and monitoring, and a new
`run-monitor` skill checks container, API and session health after each skill. The same runs, 3 in a
row at ≥ 80% agentic and ≥ 90% routing, are the evidence that unlocks local inference later.

This spec changes the lab (SPEC-102 bench, SPEC-103 Jev grader, SPEC-104 scoring) and adds one skill,
`run-monitor`. Building the R1 skills and their eval cases stays in SPEC-201; this spec sets the bar
those cases must meet.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Live-graded R1 gate run (Priority: P1)

The person, with the keys and network allowlist in place, runs one live benchmark of every skill's
agentic and routing cases on one Ollama Cloud model with Jev grading. The result decides whether the R1
PR is ready, and the scores are posted on that PR.

**Why this priority**: It is the R1 release gate (intake Q1) and the first piece of evidence toward
enabling local inference (intake A3).

**Independent Test**: With fake TypeSafe and Ollama servers, run the gate command over a scratch catalog
and check the run summary, the per-skill and catalog gates, and the rendered PR comment.

**Acceptance Scenarios**:

1. **Given** keys and network are available, **When** the person runs the gate run, **Then** every agentic and trigger case of every skill is graded live, the run records one model for all cases, and `score` reports per-skill and catalog gates.
2. **Given** a Jev yes/no grade lands between 0.35 and the case's pass threshold, **When** the case is graded, **Then** Jev is asked once more with more context, and if it is still unsure the case fails and is flagged for the person's review (intake Q5).
3. **Given** TypeSafe or Ollama Cloud fails mid-run, **When** the affected cases run, **Then** they are recorded `errored`, the remaining cases finish, and the run is marked as not counting toward the 3-in-a-row streak (intake Q6).
4. **Given** one fully passing counting live run, **When** the R1 release gates are evaluated, **Then** the live benchmark gate passes (intake Q15).
5. **Given** a finished run, **When** the PR summary is rendered, **Then** it shows per-skill and catalog results, unsure and flagged cases, tokens and cost basis, and the run's digest for the reviewer (intake Q2).

---

### User Story 2 - Reliability streak that unlocks local inference (Priority: P1)

Each counting live run extends or breaks a streak. Three consecutive counting runs that meet the gates,
on the same model and suite, are the cloud-reliability evidence that SPEC-202's local-inference gate
consumes.

**Why this priority**: The person chose cloud first and local only after cloud is proven (intake A3, Q3).

**Independent Test**: Feed recorded run summaries (passing, failing, outage, degraded, replay) to the
streak calculator and check the streak length and the reasons for each break.

**Acceptance Scenarios**:

1. **Given** three consecutive counting runs, each with catalog agentic ≥ 0.80, catalog routing ≥ 0.90 and every per-skill gate passed, **When** the streak is computed, **Then** it is 3 and `local_unlock_evidence` is true.
2. **Given** a case passed in one run and failed in a later one, **When** the streak is computed, **Then** the streak is broken and the case is listed as unstable (intake Q13).
3. **Given** a replay, outage, degraded or partial run, **When** the streak is computed, **Then** that run neither extends nor breaks the streak, and its exclusion reason is recorded (intake D2, Q6, Q21).

---

### User Story 3 - Run monitoring with a run-monitor skill (Priority: P2)

During a live run, the harness logs every case, API call and health check. After each skill's cases
finish, the `run-monitor` skill checks the benchmark container, API health and the model sessions under
test. A problem warns and marks the run degraded, and the run still goes to completion. The reviewer
session runs the same monitor in its own container and posts the health report with its verdict.

**Why this priority**: The person asked for runs to complete under system logging, system monitoring and
periodic agent-skill performance checks (intake Q17 to Q24).

**Independent Test**: Run a scratch bench with an injected high-memory reading and a slow fake API, and
check that the run finishes, is marked degraded, and holds one health report per skill.

**Acceptance Scenarios**:

1. **Given** a live run of N skills, **When** it finishes, **Then** the run folder holds N `run-health.v1` reports, one after each skill, plus a structured run log.
2. **Given** a health check finds memory ≥ 90%, disk free < 1 GB, an API error rate ≥ 5% within a skill, or a session with no progress for 10 minutes, **When** the check completes, **Then** the run logs a warning, is marked `degraded`, keeps running, and does not count toward the streak.
3. **Given** the reviewer session reviews the release PR, **When** it posts its verdict, **Then** its comment also carries a `run-health.v1` report taken inside its own container.

---

### User Story 4 - Live smoke run before relying on the gate (Priority: P2)

Before the first gate run, the person runs a small live smoke run and looks at its results.

**Why this priority**: The person wants automated tests plus one live smoke run they look at (intake Q12).

**Independent Test**: `bench --tag smoke` selects exactly the smoke cases and produces a normal run summary.

**Acceptance Scenarios**:

1. **Given** keys and network, **When** the person runs the smoke run, **Then** at least 1 agentic and 2 routing cases from at least 2 skills run live and their results are rendered for review.
2. **Given** the smoke run's health reports, **When** planning reviews them, **Then** the degraded limits are confirmed or tuned from measured normal levels (intake Q24).

### Edge Cases

- Ollama Cloud returns invalid JSON after the 2 allowed repairs: the case is `failed` with `schema_valid: false`, not `errored`. A service outage is the only cause of `errored`.
- The container restarts mid-run: the run has no `finished_at`, is marked partial, and never counts toward the streak.
- Two gate runs use different models: each is valid on its own, but the streak counts only consecutive runs with the same model and suite digest.
- A cassette or result file would contain a secret: redaction runs before writing, and a test asserts that no `SECRET_ENV_VARS` value appears in any written file.
- A case's fixtures point outside its skill folder: the case is refused (`DATA_BOUNDARY`), because only skill-factory's own fixtures may be sent (intake Q4).
- The advisory agent call after a snapshot fails: the health report records the failure in place of an `assessment`, and the run's degraded state and streak eligibility are unaffected, because the assessment only advises (inferred from the specify refinement, RQ1).
- TypeSafe rate-limits during the re-ask: the re-ask is retried like any request; if retries run out, the judgment is `errored` and the case is `errored`, which counts as an outage for the streak.

## Requirements *(mandatory)*

### Functional Requirements

**Live grading**

- **FR-001**: `skill-lab bench --tier agentic,trigger --runtime ollama-cloud --model M --jev live` MUST grade every selected skill's agentic and trigger cases live and record `M` as the single model for every runtime case in the run.
- **FR-002**: When a Jev `noul` judgment falls in the uncertain band [0.35, threshold), the grader MUST ask Jev once more with the same question and an expanded state (the case's fixture contents and the skill's `SKILL.md` body), record both values and the re-ask, and grade on the second value. A second uncertain value MUST fail the judgment with `needs_human: true`.
- **FR-003**: A case whose runtime or Jev call fails after retries for service reasons (connection error, HTTP 5xx, 429 after retries) MUST be `errored`. The run MUST continue with the remaining cases and record `counts_toward_streak: false` with reason `outage`.
- **FR-004**: A gate run MUST NOT end early because of duration. It runs until every selected case has a result (intake Q17).

**Gates**

- **FR-005**: The default gates in `skill-lab/benchmarks/criteria/_defaults.json` are the **floor**: agentic pass rate ≥ 0.80, trigger accuracy ≥ 0.90, agentic schema-valid rate ≥ 0.95, and uncertain rate after re-ask < 0.10 (strictly less than). A per-skill criteria file MAY raise a gate and MUST NOT lower one: `score` MUST refuse a lowered gate with `CRITERIA_BELOW_FLOOR` (exit 2), and `validate` MUST report it as error `criteria.below-floor`.
- **FR-006**: Gates MUST apply at two levels: per skill (each skill's own cases) and catalog (all cases of all skills in the run). A gate run passes only when every per-skill gate and every catalog gate passes.
- **FR-007**: Every skill MUST have at least 5 agentic cases and at least 10 trigger cases, of which at least 2 expect no skill (`expect_skill: null`). `validate` MUST enforce these minimums, and CONVENTIONS §5 MUST state them.
- **FR-008**: Agentic cases tagged `guardrail` MUST pass at 100% per skill, regardless of the general agentic gate.
- **FR-009**: The R1 live benchmark gate MUST pass on one fully passing counting live run (intake Q15). It MUST be `not_run` when no such run exists, never passed.

**Streak**

- **FR-010**: `skill-lab streak` MUST compute, from committed run summaries, the current streak of consecutive counting runs that pass every gate on the same model and suite digest, and emit `benchmark-streak.v1` with the streak length, the runs in it, `local_unlock_evidence` (true when the streak is ≥ 3), every unstable case, and the exclusion reason of every non-counting run.
- **FR-011**: A run counts toward the streak only when it is live (not replay), complete, not degraded, and has no `errored` case. Replay never counts (intake D2).
- **FR-012**: A case that passed in an earlier run of the current streak and fails in a later one MUST break the streak and be listed as unstable (intake Q13).

**Usage and cost**

- **FR-013**: Every result MUST record model tokens and Jev tokens (input and output), and every run MUST total them per skill and overall, in structured fields rather than notes. Run totals include the advisory assessment calls (FR-021).
- **FR-014**: Estimated cost MUST be computed only from a price table the person maintains (`skill-lab/benchmarks/prices.json`, per-token prices per service and model). Without a price for a service, cost is `null` with basis `usage-only`, and is never invented. No spending cap stops a run (intake Q7, delegated).

**Storage and data boundary**

- **FR-015**: Every result file, run summary, run log, health report and cassette MUST be written to the repository and committed. `skill-lab/benchmarks/runs/` MUST no longer be git-ignored (intake Q9).
- **FR-016**: Before a request is sent, bench MUST refuse a case whose fixtures resolve outside its skill folder (`DATA_BOUNDARY`, exit 4). Only skill-factory's fixtures, skill instructions and model outputs may be sent (intake Q4).
- **FR-017**: No written file may contain a value of any `SECRET_ENV_VARS` variable.

**Reporting**

- **FR-018**: `skill-lab report --run PATH` MUST render a PR comment (`rendered-document.v1` plus Markdown) with per-skill and catalog gate results, unsure and flagged cases, unstable cases, tokens and cost basis, degraded or outage status, and the run's `suite_digest`. The release review request MUST carry the run's digest so the reviewer reads the same run.

**Monitoring**

- **FR-019**: Bench MUST write a structured run log (`run.log.jsonl`) with one event per case start and end, per runtime and Jev request (latency, status, retries, rate-limit waits), and per health check.
- **FR-020**: A `run-monitor` skill MUST provide `snapshot`, which emits `run-health.v1` for the container it runs in (CPU, memory, disk free, process count), the API health derived from a run log (latency p50 and p95, error rate, rate-limit hits, retry wait), and the agent or model sessions in the log (turns, tool calls, context used against its limit, stalls, end reason).
- **FR-021**: After each skill's cases finish, bench MUST run `run-monitor` `snapshot`, whose fixed limits (FR-022) alone decide whether the run is degraded. Bench MUST then make one agent skill call: the run's Ollama Cloud model, given the `run-monitor` skill and the snapshot, writes an `assessment` (a short summary and recommendations) into the health report. The assessment advises and never changes the degraded decision. The report is stored in the run folder.
- **FR-022**: A snapshot that crosses a limit in `skill-lab/benchmarks/monitor-limits.json` MUST log a warning and mark the run `degraded`. The run continues to completion and does not count toward the streak. Starting limits: memory ≥ 90%, disk free < 1 GB, API error rate ≥ 5% within a skill, no progress for 10 minutes (intake Q24, delegated; tuned after the smoke run).
- **FR-023**: The release review request MUST instruct the reviewer session to run `run-monitor` `snapshot` in its own container and post the `run-health.v1` report with its verdict (intake Q23).

**Verification of this feature**

- **FR-024**: Every requirement above MUST be covered by tests against fake TypeSafe and Ollama servers.
- **FR-025**: Smoke cases (tag `smoke`: ≥ 1 agentic and ≥ 2 trigger, from ≥ 2 skills) MUST exist, and `bench --tag smoke` MUST run only them (intake Q12).

### Key Entities

- **Benchmark case** (`benchmark-case.v1`): one agentic, trigger or deterministic check of one skill.
- **Benchmark result** (`benchmark-result.v1`): one case's outcome, now with structured token usage and re-ask records.
- **Benchmark run** (`benchmark-run.v1`): one run's results and totals, plus `counts_toward_streak`, exclusion reasons, degraded status, usage totals, model and `suite_digest`.
- **Streak record** (`benchmark-streak.v1`, new): consecutive counting runs, unstable cases, and `local_unlock_evidence`.
- **Health report** (`run-health.v1`, new): one monitor snapshot of a container, the APIs and the sessions.
- **Price table** (`prices.json`) and **monitor limits** (`monitor-limits.json`): human-maintained configuration.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A gate run passes when catalog agentic pass rate ≥ 80%, catalog routing accuracy ≥ 90%, every per-skill gate passes, and every guardrail case passes.
- **SC-002**: In every live run, ≥ 95% of agentic outputs are valid JSON for their contract, and < 10% of Jev judgments remain unsure after the re-ask.
- **SC-003**: 100% of live runs report tokens per case, per skill and in total, plus a cost or the `usage-only` basis.
- **SC-004**: Local inference unlock evidence exists only after 3 consecutive counting runs meet SC-001 on the same model and suite.
- **SC-005**: 0 written files contain a secret value, and 0 requests carry content from outside skill-factory's skill folders.
- **SC-006**: Every live run of N skills holds N health reports and a run log, and reaches completion unless the container itself stops.

## Non-goals

- Model comparison across cloud models. It is the next journey and ships right after this feature (intake Q10, Q14).
- Local Ollama parity runs and the local-inference switch. These belong to SPEC-202's L1 gate, which consumes this feature's streak.
- A trend dashboard (not chosen, intake Q10).
- Monitoring the person's own machine (not chosen, intake Q19).
- A spending cap (intake Q7, delegated: report only).

## Contracts

| Contract | Change | Fields |
|---|---|---|
| `benchmark-result.v1` | additive | `usage{model_input_tokens, model_output_tokens, jev_input_tokens, jev_output_tokens}`; `judgments[].reasked`, `judgments[].first_value` |
| `benchmark-run.v1` | additive | `counts_toward_streak`, `exclusion_reasons[]` (`replay`, `partial`, `outage`, `degraded`), `degraded`, `usage{by_skill, total}`, `cost{total_usd or null, basis}`, `suite_digest`, `commit`, `health_reports[]`, `catalog{agentic_pass_rate, trigger_accuracy, agentic_schema_valid_rate, uncertain_rate}` |
| `success-criteria.v1` | additive | `gates[].scope` (`skill` or `catalog`) |
| `benchmark-streak.v1` | new | `model`, `suite_digest`, `length`, `runs[]`, `local_unlock_evidence`, `unstable_cases[]`, `excluded_runs[{run_id, reasons}]` |
| `run-health.v1` | new | `assessment{model, summary, recommendations[]}` (advisory, from the agent skill call), `target{kind (benchmark-container, model-session, reviewer-session), id}`, `container{cpu_percent, memory_percent, disk_free_bytes, processes}`, `apis[{service, p50_ms, p95_ms, error_rate, rate_limited, retry_wait_ms}]`, `sessions[{id, turns, tool_calls, context_used, context_limit, stalled, end_reason}]`, `limits`, `problems[]`, `status` (ok or degraded) |

## Error semantics

| Code | Exit | When |
|---|---|---|
| `CRITERIA_BELOW_FLOOR` | 2 | A per-skill gate is lower than its default |
| `DATA_BOUNDARY` | 4 | A case's fixtures resolve outside its skill folder |
| `RUN_DEGRADED` | warning | A health check crossed a limit |
| `RUN_NOT_COUNTING` | warning | The run is replay, partial, degraded or had an outage |
| `CASE_UNSTABLE` | warning | A case flipped from pass to fail within the streak |

## Security

- Keys come only from environment variables, and every written file is redacted (FR-017).
- The data boundary (FR-016) keeps code from other projects out of TypeSafe and Ollama Cloud.
- Health reports carry resource figures, never environment values or command lines with arguments.
- Committed cassettes are scrubbed of authorization headers before writing (SPEC-103).

## Runtime compatibility

Cloud first: the gate run uses `ollama-cloud` (no structured outputs; schema in the prompt plus at
most 2 repairs). `ollama-local` is supported by the harness but is not part of this feature's gates.
`run-monitor` is a portable skill for Zed, Claude Code and Codex. Its scripts are stdlib Python ≥ 3.9
and read `/proc` where it exists, falling back to `os` and `shutil` figures elsewhere.

## Clarifications

### Session 2026-10-22

- Q: For the health check after each skill, how should the agent skill call work? → A: Script decides, agent explains: the snapshot's fixed limits decide whether the run is degraded; then an agent call (the run's Ollama Cloud model with the run-monitor skill) reads the report and writes an assessment and recommendations into the run.
- Q: What should restart the 3-in-a-row reliability streak? → A: A change of model, or editing or adding any benchmark case.
- Q: Where should the estimated cost on every run come from? → A: A price table the person maintains (prices.json); a service without a price shows usage only.
- Q: When Jev is re-asked about an unsure grade, what extra context should the second ask get? → A: The case's input files plus the skill's SKILL.md instructions.
- Q: Should guardrail cases have to pass at 100% per skill, stricter than the 80% agentic bar? → A: 100% for guardrails.
- Q: Which of these defaults should stay as written? → A: All four: a persisting rate limit is an outage; ≥ 2 no-skill routing cases per skill; smoke run of ≥ 1 agentic and ≥ 2 routing cases from ≥ 2 skills; invalid JSON after 2 repairs is a failed case.

## Assumptions

- Confirmed: A1–A8 and D2, D4, D5 of the intake.
- Delegated by the person: one cloud model for all profiles, chosen during planning from the plan's model list (Q11); report cost with no cap (Q7); standard degraded limits, tuned after the smoke run (Q24).
- `run-monitor` is the 14th skill. Its skill spec number and its family are assigned in the plan.
