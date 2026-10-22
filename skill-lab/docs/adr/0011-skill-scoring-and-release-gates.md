# ADR-0011: Skill scoring model and release gates

## Status

Accepted

## Date

2026-10-22

## Context

Every skill needs one reproducible answer to "may this ship?", built from evidence that differs in
kind: static conformance to CONVENTIONS, unit tests, and three benchmark tiers. Deterministic
cases test scripts and should never fail. Agentic cases test a nondeterministic model following the
skill. Trigger cases test routing across the whole catalog. The report says to measure accepted
outcomes against explicit gates, not activity
([§Core metrics](../research/engineering-team-report.md#core-metrics)). ADR-0010 fixes what pass,
fail, not run and skipped mean. This ADR fixes what is measured and the default values.

Sample sizes are small. CONVENTIONS §5 asks for at least 4 deterministic, 2 agentic, 3 positive
and 1 negative trigger case per skill, and SPEC-201 raises the live-tier counts. With *n* cases a
rate can only take the values *k/n*, so a threshold means something only relative to *n*.

## Decision

1. **One command, one contract.** `skill-lab score --skill NAME` emits `skill-score.v1` built from
   the validator report, the skill's unit tests, and the latest valid benchmark run with results
   for the skill (or `--run`). It exits 0 when `release_ready` and 1 otherwise.
2. **Static rubric**:
   `100 − 25 × errors − 5 × warnings − description heuristics`, clamped to 0..100. The heuristics
   cost 10 when the description has no "Use when" clause, 5 when it is outside 350–900 characters,
   and 5 when the "Use when" clause has fewer than 2 trigger phrases. The gate is
   `static.score ≥ 90`. The weights are chosen so that **one validator error fails the gate on
   its own** (an error means a runtime may not load the skill), while warnings and style issues
   only add up.
3. **Unit tests**: `tests.pass_rate == 1.0`. A skill without tests cannot pass, because the metric
   is unmeasured and the gate is mandatory.
4. **Default tier gates** ([`_defaults.json`](../../benchmarks/criteria/_defaults.json)):

   | Gate id | Metric | Threshold | Mandatory? | Why |
   |---|---|---|---|---|
   | `deterministic-all-pass` | `bench.deterministic.pass_rate` | = 1.0 | yes | Scripts are deterministic, so any failing case is a bug |
   | `deterministic-schema-valid` | `bench.deterministic.schema_valid_rate` | = 1.0 | yes | Every envelope and payload honours its contract |
   | `agentic-schema-valid` | `bench.agentic.schema_valid_rate` | ≥ 0.95 | optional when unavailable | Models must return contract JSON without structured outputs (ADR-0003) |
   | `agentic-quality` | `bench.agentic.pass_rate` | ≥ 0.8 | optional when unavailable | Models follow the procedure in most runs; failures count |
   | `trigger-routing` | `bench.trigger.accuracy` | ≥ 0.9 | optional when unavailable | Requests route to the skill, and neighbouring requests do not |
   | `jev-uncertain` | `bench.jev.uncertain_rate` | ≤ 0.1 | optional when unavailable | At most one judgment in ten needs a human |

5. **Per-skill criteria** (`skill-lab/benchmarks/criteria/<skill>.json`, `success-criteria.v1`) are
   merged over the defaults. A skill gate replaces the default with the same `id`, or else the
   not-yet-replaced default on the same `metric`, and keeps that default's optionality. Any other
   skill gate is appended and is mandatory. An unknown metric is `UNKNOWN_METRIC` (exit 2).
   Metrics come from the fixed vocabulary `lab.score.KNOWN_METRICS`.
6. **A per-skill gate may set a threshold below the default only with a sample-size rationale and
   an aggregate gate that bounds it.** SPEC-201 does this: at least 3 agentic cases per skill with
   `bench.agentic.pass_rate ≥ 0.67`, which tolerates exactly one miss; at least 6 trigger cases per
   skill with `bench.trigger.accuracy ≥ 0.83`, also one miss; and a catalog-wide trigger gate
   `≥ 0.90` over at least 78 cases, so per-skill tolerance cannot compound (13 skills × 1 miss each
   would give 0.83 and fail it). Invariants never get a tolerance: guardrail-tagged agentic cases
   must pass 100 % (G-LIVE-02). Criteria files are critical policy paths, so a lower threshold
   always needs a human-merged change.
7. **Skill score and release gates are separate.** `skill-score` covers one skill.
   Repository-level gates (zero validation errors on all runtimes, no vendor drift, standalone
   export, containment, traceability, Python 3.9) belong to `skill-lab release check` and
   `release-gates.v1` (SPEC-201 FR-042).
8. **Eval inventory has floors.** CONVENTIONS §5 minimums are validator errors
   (`evals.deterministic-count`, `evals.agentic-count`, `evals.positive-trigger-count`,
   `evals.negative-trigger-count`). R1 raises them with the rule `eval-inventory-r1`: at least 3
   agentic cases (at least 1 tagged `guardrail`), 4 positive and 2 negative trigger cases (at
   least 1 naming a neighbouring skill, at least 1 expecting no skill), and 1 policy-tagged
   deterministic case per action above `shadow`.
9. **One run is one sample.** Scoring reads a single benchmark run. Reliability across runs
   (SPEC-202's 3-run L1 streak) is computed by release tooling, not by `score`.

## Consequences

### Positive

- Ship decisions are mechanical and reproducible. The same inputs always give the same score.
- No compensation between dimensions: a perfect static score cannot offset a failing guardrail.
- Skills can tighten gates or add their own, and the defaults keep the vocabulary consistent.

### Negative

- Small samples make per-skill rates coarse (0, 0.33, 0.67, 1.0 at *n* = 3). There are no
  confidence intervals.
- The static heuristics are crude English-text checks, and they double-count one issue: a
  description outside 350–900 characters raises the validator warning
  `frontmatter.description-length` (−5) **and** fails the length heuristic (−5).
- Every validator warning counts, including `install.not-installed`. A skill scored before
  `skill-lab install` loses points it would not lose after. Score installed skills.
- Trigger accuracy routed through Jev is a proxy for what the user's model does in Zed (ADR-0007).

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| A per-skill override lowers a default without justification | `lab.score.merge_gates` replaces gates in both directions; SPEC-104's "the defaults stay the floor" is not enforced in code | Decision 6; criteria files are critical paths (human merge). Either enforce a floor or amend SPEC-104's wording (open) |
| Thresholds are tuned to pass rather than the skill improved | Human pressure near a release | ADR-0010 decision 11: fix the skill, not the threshold |
| A suite is changed to make a streak easier | Cases are files in the skill | Live runs record a suite digest, and a changed suite starts a new streak (SPEC-202 synthesis D-17) |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| A weighted composite score | Compensatory; hides which gate failed |
| Statistical acceptance tests (confidence intervals, sequential tests) | Sample sizes are too small to make them meaningful; the 3-run streak is the pragmatic substitute |
| Bespoke scoring code per skill | Defeats comparability; per-skill differences belong in criteria data |
| Release thresholds equal to the defaults (0.8 agentic, 0.9 trigger per skill) | At 3 to 7 cases these thresholds tolerate zero misses, so model nondeterminism alone would fail them |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Defaults file matches this ADR and SPEC-104 | `test_score_gates.py::TestDefaults::test_defaults_file_is_valid_and_matches_spec`, `test_score_gates.py::TestDefaults::test_every_default_metric_is_known`, `test_score_gates.py::TestDefaults::test_optional_gate_needs_a_reason` | enforced |
| Static rubric and heuristics | `test_score_static.py::TestStaticRubric`, `test_score_static.py::TestDescriptionHeuristics` | enforced |
| Merge by id, then metric; new gates mandatory; unknown metric refused | `test_score_gates.py::TestMergeGates::test_replace_by_id_then_metric_and_append_new`, `test_score_gates.py::TestScoreEndToEnd::test_skill_criteria_add_mandatory_gates`, `test_score_gates.py::TestScoreEndToEnd::test_explicit_run_and_unknown_metric` | enforced |
| Rates from results | `test_score_gates.py::TestMetrics::test_rates_from_results` | enforced |
| CONVENTIONS eval minimums | `evals.deterministic-count`, `evals.agentic-count`, `evals.positive-trigger-count`, `evals.negative-trigger-count`; `test_lab_core_validate.py::TestEvalRules::test_tier_minimums` | enforced |
| R1 inventory | rule `eval-inventory-r1` (SPEC-201 FR-010) | planned |
| Per-skill criteria files exist for all 13 skills | `skill-lab/benchmarks/criteria/<skill>.json` (SPEC-201 FR-033) | planned |
| Lowered thresholds carry a rationale and an aggregate bound | Review of the criteria diff (critical path) | human only; no mechanical check |

**Revisit when** per-skill case counts grow enough for statistical tests, when the first live runs
show the defaults are mis-set, or when SPEC-104's floor wording is resolved.

## References

- [SPEC-104 scoring and release gates](../../specs/104-scoring-gates/spec.md),
  [SPEC-201 R1](../../specs/201-release-shadow/spec.md) §Release gates (G-LIVE-01..05),
  [SPEC-201 synthesis](../../specs/201-release-shadow/synthesis.md) D-16, D-20
- [CONVENTIONS §5](../CONVENTIONS.md#5-evals-and-benchmarks), [§9](../CONVENTIONS.md#9-definition-of-done-for-a-skill-v)
- ADR-0007 (Jev metrics), ADR-0010 (gate semantics)
