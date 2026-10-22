# ADR-0010: "100 % success" means 100 % of explicit gates pass, and a gate that did not run never passes

## Status

Accepted

## Date

2026-10-22

## Context

The user asked for skills that work "100 %". The report answers what that can honestly mean
(report [§Executive architecture](../research/engineering-team-report.md#executive-architecture)):

> "100 percent accurate" should mean **100 percent of explicitly defined acceptance gates are
> satisfied**, not an impossible guarantee that software is defect-free.

and in [§Merge evidence gate](../research/engineering-team-report.md#merge-evidence-gate): "the
applicability decision itself must be explicit. 'Not run' must never silently mean 'passed.'"

The environment makes this concrete. Today the build container cannot reach `ollama.com` or
`api.typesafe.ai`, has no keys, and has no Python 3.9 interpreter. A large share of the gates
cannot run here, and every one of them is a temptation to report green.

## Decision

1. **Success is defined only by gates.** "100 %" means every explicitly defined gate passes. It
   never means "defect-free" or "the model is always right".
2. **A gate is data.** Each gate has an `id`, a `metric` from a fixed vocabulary, an operator
   (`eq` with 1e-9 tolerance, `gte`, `lte`, `gt`, `lt`), a `threshold`, a `rationale`, and the
   command that measures it. Per skill: `success-criteria.v1` merged over the lab defaults
   ([`_defaults.json`](../../benchmarks/criteria/_defaults.json)). Per release: `release-gates.v1`
   in `gates.json` (SPEC-201 FR-042).
3. **Only `pass` passes.** Gate outcomes are `pass`, `fail`, `not_run` and, in skill scoring only,
   `skipped`. A gate whose metric was not measured can never be `pass`. The `skill-score.v1`
   schema makes a passed gate with `actual: null` invalid.
4. **`skipped` is narrow and loud.** A skill-score gate may be `skipped` only when all of these
   hold:
   - the lab defaults mark it `optional_when_unavailable`, with an `optional_reason`;
   - its metric could not be measured in this environment;
   - `--strict` was not given.

   Every skip carries a reason and a `GATE_SKIPPED` warning. A skill that is ready only because
   gates were skipped also gets `RELEASE_READY_OFFLINE`. With `--strict`, every skip becomes
   `not_run`, which blocks.
5. **Two readiness levels, never confused.** `release_ready: true` is CONVENTIONS §9.6 readiness:
   every gate that could run here passed, and the skipped ones are listed. **Full readiness** is
   `release_ready` without `RELEASE_READY_OFFLINE`, or equivalently `skill-lab score --strict`
   exiting 0. Live release stages use `--strict` on runs recorded against the live services
   (SPEC-104 §Readiness levels).
6. **Releases have two exit states** (SPEC-201, SPEC-202):
   - **merged**: every `merge`-stage gate passes, an independent reviewer approved the current
     head, and a human merged;
   - **complete**: the `complete`-stage live gates also pass.

   A live gate that is `not_run` leaves a release "merged, live-pending", never "complete". A live
   gate that ran and **failed** blocks the merge, because a failed capability gate is a defect.
   A release that misses a gate stays open, and the next one does not start (SPEC-200). SPEC-202
   also makes R3 wait until R2 is complete (SPEC-202 synthesis D-20).
7. **Rates never hide what did not run.** `pass_rate = passed / (passed + failed + errored)`.
   Skipped cases are excluded, and a tier where nothing was graded has `pass_rate: null`
   (unmeasured), not 1.0. Errored cases count against the rate.
8. **Evidence must come from execution.** A check counts only with a recorded `check-run` (command,
   exit code, log digest). An evidence manifest that claims an unexecuted check fails with
   `CHECK_NOT_EXECUTED`. A replayed run never satisfies a live gate, and a live run with any
   errored or skipped case is incomplete (G-LIVE-05).
9. **Applicability is explicit.** Every `quality-gate.v1` category states `applicable`. An
   applicable category with status `not_run` fails the gate. "Not applicable" is a recorded
   decision, not a default.
10. **Every surface prints the truth.** Score envelopes, release reports and PR bodies print
    `not run` for a gate that did not run, and never `pass` (SPEC-201 FR-038).
11. **Fix the skill, not the threshold.** On a failing gate, change descriptions, procedures or
    scripts. Thresholds sit in critical policy paths (`skill-lab/benchmarks/criteria/**`,
    `skill-lab/specs/*/gates.json`) and change only through an ADR and a human merge (SPEC-201
    plan §Benchmark plan).

## Consequences

### Positive

- A green result means what it says. Reviewers and the user can trust it without re-deriving it.
- Missing infrastructure shows up as explicit `not_run` or `skipped` lines with reasons, which is
  also the to-do list for enabling it.
- Gate definitions are reviewable data, so "what does done mean" is answered in one file.

### Negative

- More red and amber. While the network is blocked, every release is at best "merged,
  live-pending".
- Four outcome states are more to learn than pass/fail. Offline `release_ready` can be misread as
  full readiness. The `RELEASE_READY_OFFLINE` warning exists for exactly that reason, but people
  skim warnings.
- Small samples make rates coarse. With 3 agentic cases a skill can score only 0, 0.33, 0.67 or 1.0
  (ADR-0011).

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| Every gate passes and the product is still wrong (Goodhart) | Gates measure what was specified, not everything that matters | Independent review rebuilt from the spec; human merge; every recurring mistake becomes a fixture, then an eval, then a mechanical check (report [§Agentic-framework verification](../research/engineering-team-report.md#agentic-framework-verification)) |
| A gate is defined too weakly | Thresholds are human choices | Thresholds carry rationales and sit in critical paths; changes need an ADR |
| An optional gate stays skipped forever | Live services may never be configured | `GATE_SKIPPED` on every run; live stages require `--strict` |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Treat skipped as passed when offline | Exactly the "not run means passed" failure the report forbids |
| Block every merge until live gates can run | Ties the merge to a network allowlist and adds no safety; offline gates already protect the merge (SPEC-201 synthesis, rejected alternatives) |
| One composite quality score | Compensatory: a high static score could hide a failing guardrail. It also hides which gate failed |
| "Confidence" estimates instead of gates | Not checkable; restates the problem |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Unmeasured mandatory gate is `not_run`; optional one is `skipped` unless `--strict` | `test_score_gates.py::TestEvaluateGate::test_unmeasured_mandatory_gate_is_not_run`, `test_score_gates.py::TestEvaluateGate::test_unmeasured_optional_gate_is_skipped_unless_strict` | enforced |
| Offline readiness lists skipped gates; `--strict` blocks | `test_score_gates.py::TestScoreEndToEnd::test_offline_release_ready_lists_skipped_gates`, `test_score_gates.py::TestScoreEndToEnd::test_strict_mode_turns_skips_into_not_run` | enforced |
| No tests or failing tests block release | `test_score_gates.py::TestScoreEndToEnd::test_no_tests_flag_means_not_run`, `test_score_gates.py::TestScoreEndToEnd::test_failing_unit_tests_block_release` | enforced |
| Skipped never counts as passed in rates | `test_bench_graders.py::TestSummaries::test_skipped_never_counts_as_passed`, `test_score_gates.py::TestMetrics::test_skipped_tiers_and_missing_inputs_are_unmeasured_with_reasons` | enforced |
| Unavailable services are skipped with a reason | `test_bench_runner.py::TestModelTiers::test_unavailable_services_are_skipped_never_passed`, `test_bench_runner.py::TestModelTiers::test_unreachable_runtime_is_skipped_with_reason` | enforced |
| Contracts forbid passing what did not run | `skill-score.v1` (no pass without a value) and `quality-gate.v1` (no pass with an applicable `not_run` category); crafted invalid cases in `test_contracts.py` | enforced |
| Release check: `not_run` blocks the stage; exits 1 `RELEASE_GATES_FAILED` | `skill-lab/tests/test_release_check.py` (SPEC-201 FR-042) | planned |
| Unexecuted evidence fails | `evidence_manifest.py validate` exits 1 `CHECK_NOT_EXECUTED` (SPEC-201 User Story 4, scenario 4) | planned |
| PR body prints `not run` | `pr_body.py` (SPEC-201 FR-038) | planned |

**Revisit when** a gate class appears whose outcome cannot be expressed as pass, fail or not run,
or when sample sizes allow statistical acceptance criteria instead of fixed thresholds.

## References

- Report [§Executive architecture](../research/engineering-team-report.md#executive-architecture),
  [§Merge evidence gate](../research/engineering-team-report.md#merge-evidence-gate),
  [§Core metrics](../research/engineering-team-report.md#core-metrics)
- [CONVENTIONS §5](../CONVENTIONS.md#5-evals-and-benchmarks), [§9](../CONVENTIONS.md#9-definition-of-done-for-a-skill-v)
- [SPEC-104 scoring](../../specs/104-scoring-gates/spec.md), [SPEC-102 bench](../../specs/102-bench-runtimes-graders/spec.md) FR-008,
  [SPEC-201 R1](../../specs/201-release-shadow/spec.md) §Release gates
- ADR-0007 (uncertain judgments fail), ADR-0011 (gate values)
