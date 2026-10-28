# Implementation Plan: Jev live benchmarking

**Branch**: `105-jev-live-benchmarking` (delivered inside `release/r1-shadow`) | **Date**: 2026-10-22 |
**Spec**: [spec.md](spec.md) | **Research**: [research.md](research.md) | **Data model**: [data-model.md](data-model.md) |
**Tasks**: [tasks.md](tasks.md)

**Input**: SPEC-105, specified and refined with the person (intake `intakes/jev-live-benchmarking/intake.md`).

## Clarifications

### Session 2026-10-22 (plan refinement)

- Q: Which of these plan defaults should stay as written (set 1)? → A: All four: 401/403/422 are not outages; a partly priced run reports usage only; missing /proc metrics never mark a run degraded; the reviewer's health report is a separate marked PR comment.
- Q: Which of these plan defaults should stay as written (set 2)? → A: All three: smoke cases from lead-architect and review-verifier; no request or response bodies in the run log; monitor-limits.json changes need the person's approval.

## Summary

Turn the existing offline-tested benchmark harness (SPEC-102/103/104) into the R1 live release gate.
The plan has six parts:

1. **Grading**: re-ask unsure Jev grades once, and classify outages as errored without stopping the run.
2. **Gates**: enforce the defaults as a floor at skill and catalog level, add the guardrail gate, and raise the eval-case minimums.
3. **Streak**: record whether each run counts and compute the 3-in-a-row streak.
4. **Usage, cost and storage**: structured token usage, cost from the person's price table, every result committed with no secrets, and the data boundary enforced.
5. **Monitoring**: a structured run log; `run-monitor` snapshots after each skill, whose fixed limits decide degradation; then one advisory agent call explains the snapshot.
6. **Reporting**: a PR comment for the person and the reviewer, plus the reviewer's own health report.

All of it is stdlib Python ≥ 3.9 inside `skill-lab/lab/` and one new skill, `skills/run-monitor/`.

## Technical Context

**Language/Version**: Python ≥ 3.9, standard library only (ADR-0006; intake D4 confirmed)
**Primary Dependencies**: none; `skill-lab/shared/_skillkit` (vendored into `run-monitor`)
**Storage**: files committed in git: `skill-lab/benchmarks/runs/<run_id>/` (results, run summary, run log, health reports, PR comment), `skill-lab/benchmarks/cassettes/`, and `prices.json` and `monitor-limits.json` (intake Q9)
**Testing**: unittest with the existing fake TypeSafe and Ollama servers (`skill-lab/tests/test_bench_fakes.py`), plus one live smoke run the person reviews (intake Q12)
**Target Platform**: Claude Code cloud containers (live runs after allowlisting) and the person's machine, including the person's Rancher Desktop local containers, which `run-monitor` reads only from inside each container (target `local-container`, research R-9); CI runs only the offline tiers (SPEC-201 refinement)
**Project Type**: CLI lab plus one portable agent skill
**Performance Goals**: no time limit; runs go to completion (Q17). One extra advisory model call per skill. A health check costs about 0.5 s of CPU sampling per skill
**Constraints**: never fabricate results; only skill-factory fixtures are sent (Q4); keys only from environment variables; Ollama Cloud has no structured outputs
**Scale/Scope**: 14 skills × (≥ 5 agentic + ≥ 10 trigger) ≥ 210 live cases per full run, plus up to 2 repair turns per agentic case, ≤ 1 re-ask per unsure judgment, and 14 advisory calls

## Constitution Check

There is no ratified constitution yet; the whole-product intake comes later. The interim
constitution-equivalent is CONVENTIONS plus the ADRs.

| Rule | Source | This plan |
|---|---|---|
| Stdlib only, Python ≥ 3.9 | ADR-0006, CONVENTIONS §3 | Yes. `/proc` reads have fallbacks (research R-9) |
| One envelope per script, exit codes 0–4 | CONVENTIONS §3 | `streak`, `report` and `run-monitor snapshot` emit envelopes. New codes are listed in the spec's error table |
| JSON contracts, subset, `additionalProperties: false` | ADR-0004 | 2 new contracts and 3 additive changes (data-model.md) |
| LLM proposes, code decides | ADR-0005 | Degraded is decided by limits; the agent only explains (RQ1) |
| Not run never counts as pass | ADR-0010 | Unmeasured gates stay `not_run`; replay and partial runs never count |
| Jev is never the only gate for deterministic properties | ADR-0007 | Unchanged; the re-ask applies to agentic judgments only |
| Defaults as floor | SPEC-104 US3, gates decision | Enforced in `merge_gates` and `validate` (R-4) |
| Skills never write inside their own folder | ADR-0012, Zed facts | `run-monitor` writes only to `--out` |
| Secrets only via env, redacted | ADR-0012 | Every written file passes through `_skillkit.redact`, and a test scans the outputs |

No violations. Complexity tracking: none needed.

## Project Structure

### Documentation (this feature)

```text
skill-lab/specs/105-jev-live-benchmarking/
├── spec.md            # specified and refined
├── research.md        # Phase 0 decisions R-1..R-15
├── data-model.md      # contract and configuration fields
├── plan.md            # this file
├── tasks.md           # engineering tasks (Spec Kit format)
└── traceability.json  # FR → code and tests
```

### Source code

```text
skill-lab/
├── lab/
│   ├── bench.py          # re-ask, outage, usage, boundary, run log, health checks, counting fields
│   ├── graders.py        # re-ask banding helpers, guardrail summary
│   ├── score.py          # floor comparator, scope, --catalog, guardrail metric
│   ├── validate.py       # criteria.below-floor, new eval minimums
│   ├── streak.py         # NEW: skill-lab streak → benchmark-streak.v1
│   ├── report.py         # NEW: skill-lab report → rendered-document.v1 + pr-comment.md
│   ├── runlog.py         # NEW: JSONL event sink with redaction
│   ├── cli.py            # register streak and report
│   └── runtimes/transport.py, jev.py   # request hooks for the run log
├── benchmarks/
│   ├── criteria/_defaults.json   # floor gates, scope, guardrail, catalog copies
│   ├── prices.json               # NEW, empty services
│   ├── monitor-limits.json       # NEW, starting limits
│   ├── runs/                     # now committed
│   └── cassettes/                # committed
├── contracts/schemas/            # benchmark-streak.v1, run-health.v1 (new); result/run/criteria (additive)
└── tests/                        # test_live_*.py, test_streak.py, test_score_floor.py, schema tests
skills/run-monitor/
├── SKILL.md                      # procedure: snapshot, read, assess; never change the decision
├── scripts/snapshot.py           # run-health.v1 for container, APIs, sessions; limits → status
├── scripts/_skillkit/            # vendored
├── assets/schemas/               # run-health, envelope (vendored)
├── evals/                        # ≥ 4 deterministic, ≥ 5 agentic, ≥ 10 trigger (SPEC-201 tasks)
└── tests/test_snapshot.py
.gitignore                        # stop ignoring skill-lab/benchmarks/runs/
```

**Structure decision**: the feature extends the existing lab modules where it changes their behaviour,
and adds three modules where it adds a command or an event sink. `run-monitor` is a full skill because the
person asked for agent skill calls (Q22, RQ1), and so that the reviewer session can run the same code in
its own container (Q23).

**Ownership with SPEC-201**: this feature's tasks build `snapshot.py`, its tests and its schema. SPEC-201's
`run-monitor` tasks own SPEC-014 (the skill spec), the `SKILL.md` body and the skill's eval cases. Both
release through the R1 PR.

## Phase plan

### Phase A: contracts first

Write `benchmark-streak.v1` and `run-health.v1`, and the additive changes to `benchmark-result`,
`benchmark-run` and `success-criteria`, with examples, invalid fixtures and a CONVENTIONS §4 catalog
update. Contract tests must pass before any producer code exists.

### Phase B: grading and outage (FR-001..FR-004)

- `bench._ask_judgments` keeps the first reply. For noul judgments in the uncertain band, it builds the
  expanded state (R-2) and sends one second request with only those questions. Then
  `graders.grade_judgment` grades the second value, and both values and `reasked` are recorded. Usage
  from both calls is summed.
- Service failures after retries map to `errored` with `RUNTIME_UNAVAILABLE` or `JEV_UNAVAILABLE` (R-3),
  and the case loop continues. `run_end` sets `exclusion_reasons += ["outage"]`.
- Tests: an uncertain value then a pass; uncertain twice gives fail and `needs_human`; 429 storms; a 5xx
  mid-run leaves the remaining cases graded; 422 is not an outage.

### Phase C: gates and minimums (FR-005..FR-009)

- `_defaults.json` per data-model.md. `merge_gates` uses the floor comparator (R-4), and `validate` reuses
  it.
- Add the `scope` field and `score --catalog`. Add the guardrail metric (R-6).
- `validate` minimums: ≥ 4 deterministic, ≥ 5 agentic with ≥ 1 tagged `guardrail`, ≥ 10 trigger with ≥ 2
  `expect_skill: null`.
- The R1 gate run passes on one counting run where every skill gate and every catalog gate passes.
  Otherwise the gate is `not_run`, never passed.

### Phase D: usage, cost, storage, boundary (FR-013..FR-017)

- Structured `usage` on results and totals on runs. Cost from `prices.json` (R-8).
- `.gitignore` stops ignoring `skill-lab/benchmarks/runs/`; cassettes default to `skill-lab/benchmarks/cassettes/`.
- `load_fixtures` resolves every fixture with `_skillkit.fsutil.safe_join(skill_dir, ...)`; escaping
  raises `DATA_BOUNDARY` (exit 4) before any request.
- Every write goes through `_skillkit.redact`. A test sets fake secrets in the environment, runs a full
  fake-server bench, and greps every written file for them.

### Phase E: monitoring (FR-019..FR-023)

- `lab/runlog.py` is an append-only JSONL sink. Runtimes and the Jev client report request events
  through a hook, so bodies are never logged (R-13).
- `skills/run-monitor/scripts/snapshot.py`: `--target`, `--run-log`, `--limits`, `--skill`, `--out` →
  `run-health.v1`. Container metrics per R-9, API and session metrics per R-10, and limits decide
  `status`. `--target local-container` (additive, the person's answer, 2026-10-22) reads the container's own cgroup v2
  files (`cpu.stat`, `cpu.max`, `memory.current`, `memory.max`), falls back to cgroup v1, records `null` plus a note
  when neither is readable, and adds `container.cgroup`; disk free and process count are those seen inside the
  container. It opens no Docker or containerd socket and reads nothing else on the machine. Callers run it inside the
  container doing the work: SPEC-202's bench on `--runtime ollama-local` runs, and SPEC-203's webhook gateway on every
  reconcile tick.
- Bench, after each skill: run the snapshot, set `degraded` and `exclusion_reasons += ["degraded"]` on
  a problem, then make the advisory call (R-11) and store `assessment` or `assessment_error`.
- Reviewer instructions: the `speckit-development` review request adds the snapshot command for
  `--target reviewer-session` and the separate marked health comment (R-12).

### Phase F: streak and report (FR-010..FR-012, FR-018)

- `skill-lab streak` per R-7. `skill-lab report --run PATH` renders `pr-comment.md` and a
  `rendered-document.v1` that holds per-skill and catalog gates, unsure and flagged cases, unstable cases,
  usage and cost basis, degraded or outage status, the streak, and `suite_digest`.

### Phase G: smoke, docs, live

- Smoke cases tagged `smoke` (R-15). `bench --tag smoke` exists already.
- Update `setup-jev.md` and `live-benchmarks.md`: re-ask, outage and degraded rules, `--strict`, `streak`,
  `report`, `prices.json`, `monitor-limits.json`.
- Live (network and keys needed): smoke run → the person looks at it → tune `monitor-limits.json` if the
  smoke run's normal levels require it → R1 gate run → `report` → post on the R1 PR.

## Test strategy

| Layer | What | Where |
|---|---|---|
| Contract | schemas parse, use only the subset, examples valid, invalid fixtures rejected | `test_contracts.py` (extended) |
| Unit | floor comparator, re-ask selection, outage mapping, cost math, streak walk, limits evaluation, `/proc` fallbacks, `local-container` cgroup v2 and v1 readers and their `null` fallback, no socket or host path opened | `test_score_floor.py`, `test_live_reask.py`, `test_live_usage.py`, `test_streak.py`, `skills/run-monitor/tests/test_snapshot.py` |
| Integration | full fake-server bench: re-ask, outage, degraded, usage totals, committed files without secrets, PR report | `test_live_gate.py`, `test_live_storage.py`, `test_live_monitor.py`, `test_live_report.py` |
| Live smoke | 1 agentic + 2 routing cases on Ollama Cloud with Jev live | manual, recorded under `benchmarks/runs/` |
| Live gate | full run, both levels | R1 gate |

Every FR has at least one verifying test in `traceability.json`. The suite runs on Python 3.9 and the
current Python.

## Rollout and rollback

- Ships in the R1 PR. Offline CI runs every new test, and live tiers run only when started manually.
- Rollback: the changes are additive to v1 contracts. Reverting the feature's commits restores the
  previous harness. Committed runs stay readable because the new fields are optional.
- Risks: Jev waitlist or access delays block every live gate (they stay `not_run`, and R1 cannot merge);
  Ollama Cloud plan limits may rate-limit a 210-case run (outage, which does not count; the person can
  re-run); `/proc` gaps on macOS give `null` metrics (they cannot trigger degraded, by design).
