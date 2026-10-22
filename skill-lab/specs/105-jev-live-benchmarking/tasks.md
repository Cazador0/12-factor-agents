# Tasks: Jev live benchmarking

**Input**: Design documents from `/skill-lab/specs/105-jev-live-benchmarking/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md

**Delivered inside**: R1 (`release/r1-shadow`). SPEC-201's live gate run depends on T040.

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [ ] T001 Stop ignoring run output: remove `skill-lab/benchmarks/runs/` from .gitignore and add skill-lab/benchmarks/runs/README.md explaining committed runs
- [ ] T002 [P] Add skill-lab/benchmarks/prices.json with empty `services` and skill-lab/benchmarks/monitor-limits.json with the starting limits from data-model.md

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T003 Write contract tests first for benchmark-streak.v1, run-health.v1 and the additive fields in skill-lab/tests/test_contracts_live.py (they fail until T004–T006 land)
- [ ] T004 Add skill-lab/contracts/schemas/benchmark-streak.v1.schema.json and run-health.v1.schema.json with examples in skill-lab/contracts/examples/ (depends on T003)
- [ ] T005 Extend skill-lab/contracts/schemas/benchmark-result.v1.schema.json, benchmark-run.v1.schema.json and success-criteria.v1.schema.json additively per data-model.md, and update their examples (depends on T003)
- [ ] T006 Add the two new contracts to the CONVENTIONS §4 catalog in skill-lab/docs/CONVENTIONS.md and to skill-lab/contracts/README.md (depends on T004)
- [ ] T007 Add `lab/runlog.py` (redacting JSONL event sink) with tests in skill-lab/tests/test_runlog.py

**Checkpoint**: contracts and the run log exist; producers can be built.

---

## Phase 3: User Story 1 - Live-graded R1 gate run (Priority: P1) 🎯 MVP

### Tests for User Story 1

- [ ] T008 [P] [US1] Write re-ask tests (first uncertain then pass; twice uncertain gives fail with needs_human; only uncertain noul judgments re-asked; expanded state carries fixtures and SKILL.md) in skill-lab/tests/test_live_reask.py
- [ ] T009 [P] [US1] Write outage tests (5xx and 429-after-retries mark errored, remaining cases graded, run gets `outage`; 401/422 are not outages) in skill-lab/tests/test_live_gate.py
- [ ] T010 [P] [US1] Write floor tests (lowered override refused with CRITERIA_BELOW_FLOOR; raise allowed; eq unchanged; skill and catalog scopes; guardrail gate; R1 gate passes on one counting run and is not_run otherwise) in skill-lab/tests/test_score_floor.py
- [ ] T011 [P] [US1] Write usage and cost tests (structured usage per case, skill, total; cost null with usage-only when a price is missing; price-table basis when complete) in skill-lab/tests/test_live_usage.py
- [ ] T012 [P] [US1] Write storage and boundary tests (runs not ignored; no SECRET_ENV_VARS value in any written file; fixture outside the skill folder refused with DATA_BOUNDARY before any request) in skill-lab/tests/test_live_storage.py
- [ ] T013 [P] [US1] Write report tests (PR comment holds per-skill and catalog gates, unsure and flagged cases, usage and cost basis, degraded or outage status, suite digest) in skill-lab/tests/test_live_report.py

### Implementation for User Story 1

- [ ] T014 [US1] Implement the re-ask in skill-lab/lab/bench.py `_ask_judgments` and grading of the second value in skill-lab/lab/graders.py (depends on T008, T005)
- [ ] T015 [US1] Implement outage classification and continue-on-error in skill-lab/lab/bench.py, setting `exclusion_reasons` and `counts_toward_streak` (depends on T009, T005)
- [ ] T016 [US1] Implement the floor comparator, `scope`, `--catalog` and the guardrail metric in skill-lab/lab/score.py, and update skill-lab/benchmarks/criteria/_defaults.json per data-model.md (depends on T010, T005)
- [ ] T017 [US1] Add rule `criteria.below-floor` and the new eval minimums (≥ 5 agentic incl. ≥ 1 guardrail, ≥ 10 trigger incl. ≥ 2 expect_skill null) to skill-lab/lab/validate.py, reusing the comparator from T016, with tests in skill-lab/tests/test_lab_core_validate.py (depends on T016)
- [ ] T018 [US1] Record structured usage and compute cost from skill-lab/benchmarks/prices.json in skill-lab/lab/bench.py (depends on T011, T002, T005)
- [ ] T019 [US1] Enforce the data boundary in skill-lab/lab/bench.py `load_fixtures` with `_skillkit.fsutil.safe_join`, and redact every written file (depends on T012)
- [ ] T020 [US1] Write `suite_digest`, `commit`, `catalog` and `log` as fields of benchmark-run.v1 in skill-lab/lab/bench.py (depends on T005, T007)
- [ ] T021 [US1] Implement `skill-lab report` in skill-lab/lab/report.py and register it in skill-lab/lab/cli.py (depends on T013, T016, T020)

**Checkpoint**: an offline fake-server run produces a gate-ready run summary and PR comment.

---

## Phase 4: User Story 2 - Reliability streak (Priority: P1)

- [ ] T022 [P] [US2] Write streak tests (3 counting passing runs unlock; replay, partial, outage, degraded excluded with reasons; model or suite change restarts; a pass-then-fail case breaks the streak and is listed unstable) in skill-lab/tests/test_streak.py
- [ ] T023 [US2] Implement `skill-lab streak` in skill-lab/lab/streak.py and register it in skill-lab/lab/cli.py (depends on T022, T015, T016, T020)
- [ ] T024 [US2] Include the current streak in the PR report in skill-lab/lab/report.py (depends on T021, T023)

---

## Phase 5: User Story 3 - Run monitoring with run-monitor (Priority: P2)

- [ ] T025 [P] [US3] Write snapshot tests (container metrics from fake /proc files; null with notes without /proc; API p50/p95/error rate from a run log; session turns, context and stalls; limits produce problems and degraded) in skills/run-monitor/tests/test_snapshot.py
- [ ] T026 [US3] Implement skills/run-monitor/scripts/snapshot.py per research R-9 and R-10, vendor `_skillkit` and the run-health schema with `skill-lab sync` (depends on T025, T004)
- [ ] T027 [P] [US3] Write run-log and periodic-check tests (events logged without bodies; a snapshot after each skill; a crossed limit marks the run degraded and the run completes; the advisory assessment is stored, and its failure changes nothing) in skill-lab/tests/test_live_monitor.py
- [ ] T028 [US3] Add request hooks to skill-lab/lab/runtimes/transport.py and skill-lab/lab/jev.py that emit run-log events (depends on T007)
- [ ] T029 [US3] Run the snapshot after each skill and make the advisory agent call in skill-lab/lab/bench.py, storing health reports under the run folder (depends on T026, T027, T028)
- [ ] T030 [US3] Add the reviewer self-report command and the separate marked health comment (`<!-- skill-lab:run-health:v1 request_id=<id> -->`) to the speckit-development review request instructions in skills/speckit-development/scripts/review_request.py (depends on T026)

---

## Phase 6: User Story 4 - Live smoke run (Priority: P2)

- [ ] T031 [US4] Tag smoke cases: 1 agentic in skills/lead-architect/evals/cases/ and 1 routing each in skills/lead-architect/evals/cases/ and skills/review-verifier/evals/cases/ (research R-15)
- [ ] T032 [US4] Add a test that `bench --tag smoke` selects exactly the smoke cases in skill-lab/tests/test_live_gate.py (depends on T031)

---

## Phase 7: Polish & Cross-Cutting Concerns

- [ ] T033 [P] Update skill-lab/docs/runbooks/setup-jev.md and skill-lab/docs/runbooks/live-benchmarks.md for the re-ask, outage and degraded rules, `--strict`, `streak`, `report`, prices.json and monitor-limits.json
- [ ] T034 [P] Update SPEC-102, SPEC-103 and SPEC-104 specs and traceability for the changed behaviour in skill-lab/specs/102-bench-runtimes-graders/, 103-jev-grader/ and 104-scoring-gates/
- [ ] T035 Run the full lab suite on Python 3.9 and the current Python and record the results in skill-lab/specs/105-jev-live-benchmarking/evidence/offline.md (depends on T017, T019, T021, T024, T030, T032)
- [ ] T036 Mark every FR in skill-lab/specs/105-jev-live-benchmarking/traceability.json as implemented, removing `planned`, and run `skill-lab validate --specs` (depends on T035)
- [ ] T037 Live (network and keys): choose the one cloud model per research R-14 and record it in skill-lab/config/zed/cloud-models.json and skill-lab/docs/research/SOURCES.md
- [ ] T038 Live: run `skill-lab bench --tag smoke --runtime ollama-cloud --model <model> --jev live --record skill-lab/benchmarks/cassettes` and render its report for the person (depends on T037, T032, T029)
- [ ] T039 Propose a change to skill-lab/benchmarks/monitor-limits.json only if the smoke run's measured normal levels require it, with the measurements, and apply it only after the person approves (depends on T038)
- [ ] T040 Live: run the R1 gate run `skill-lab bench --tier agentic,trigger --runtime ollama-cloud --model <model> --jev live`, then `score --strict` per skill and `--catalog`, `streak` and `report`, and commit the run under skill-lab/benchmarks/runs/<run_id>/ (depends on T039, T036)

---

## Dependencies & Execution Order

- Setup (T001–T002) → Foundational (T003–T007) → US1 (T008–T021) → US2 (T022–T024) and US3 (T025–T030) → US4 (T031–T032) → Polish (T033–T040).
- US2 and US3 can proceed in parallel after US1's implementation tasks they depend on.
- T037–T040 need `api.typesafe.ai` and `ollama.com` allowlisted and `TYPESAFE_API_KEY` and `OLLAMA_API_KEY` set. Until then they stay open, and SPEC-201's live gates stay `not_run`.
