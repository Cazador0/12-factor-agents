# ADR-0007: Jev (TypeSafe System One) grades what code cannot, and only that

## Status

Accepted

## Date

2026-10-22

## Context

Two benchmark tiers need a grader beyond exit codes and JSON assertions:

- **Agentic cases**: a model runs with the skill loaded and returns JSON for a contract. Schema
  validity and assertions check the shape and the hard facts. Some qualities are semantic: "the
  blocker summary explains the defect in terms the PSE can act on", "each acceptance criterion is
  testable".
- **Trigger cases**: does a user query route to the right skill, or to none, across the whole
  catalog?

A second generative model as judge would add another nondeterministic model, produce prose that
must be parsed, and give no calibrated measure of uncertainty. TypeSafe's **Jev** (System One)
answers typed questions about a `state` with calibrated outputs
([SOURCES.md, TypeSafe AI "Jev"](../research/SOURCES.md#typesafe-ai-jev-system-one-model);
`typesafe-sdk` 0.7.5 wire models vendored at `docs/research/vendor/typesafe-wire-models.py`):

- `noul`: probability that a statement holds; `choice`: one label plus confidence and the full
  distribution; `score`: a probability-weighted position on ordered levels.
- One narrow judgment per question. Independent questions over the same state go in one request
  and run in parallel. Question ids are not sent to the model, so the instructions must carry the
  full meaning.
- A noul near 0.5 means similar probability for yes and no, not "medium". Typed output guarantees
  the interface, not the truth. TypeSafe's own skill says to validate the model's performance in
  the target domain and to treat published thresholds as examples, not rules.

Network access to `api.typesafe.ai` is blocked in the build container, and no key is set. The user
will allowlist the host and provide the key later
([runbook](../runbooks/setup-jev.md)).

## Decision

1. **Deterministic grading first, always.** For every case: exit code (deterministic tier), schema
   validity, then JSON-Pointer assertions. Judgments are asked only after those pass (SPEC-102
   FR-005). Jev is never the only gate for a property code can check. "The verdict's `result` is
   `CHANGES_REQUESTED`" is an `eq` assertion. "The blocker summary names the failing retry path"
   is a noul.
2. **Three question types, each with a fixed pass rule** in the case's `pass_if`:
   `noul` passes at `{"gte": t}`; `score` passes at `{"gte": level}`; `choice` passes at
   `{"eq": label}`. Image (`box`) questions are not supported.
3. **Uncertainty is a fail that needs a human.** For noul: `pass` at or above `t`, `uncertain` in
   `[0.35, t)`, `fail` below 0.35 (`lab.graders.UNCERTAIN_FLOOR`). An uncertain result fails the
   case and sets `needs_human: true`. The default gate `jev-uncertain` caps
   `bench.jev.uncertain_rate` at 0.1.
4. **One request per case and `state_from` set.** Judgments sharing their declared state parts
   (`skill`, `prompt`, `fixtures`, `output`) go in one request (`lab.jev.judgment_batches`), and
   the state contains exactly those parts (`build_state`).
5. **Routing is one `choice` question** over every model-invocable catalog skill, each described
   by its own description, plus `none` (`lab.jev.routing_question`). `--router runtime` asks the
   model under test instead, through Zed's emulated catalog. Results record `routed_skill`, the
   method, and for Jev the confidence and top probabilities.
6. **Never fabricate.** With no key or no reachable API, Jev is `off` for the run and every judged
   case is `skipped` with a reason starting `LIVE_PREREQ_MISSING`, even when its other checks
   passed. A response that breaks the interface (wrong type, missing answer, a label that is not
   offered, a probability outside [0, 1]) raises `JevProtocolError` and the case is `error`, never
   graded. Replay (`--jev replay --cassettes DIR`) is allowed only from cassettes recorded by a real
   live run (`--record`). Replayed results carry `jev_mode: "replay"`, an unrecorded request is
   `skipped` with `CASSETTE_MISS`, and a replayed run never satisfies a live gate (SPEC-201 FR-041).
7. **Credentials.** The key comes from `TYPESAFE_API_KEY`, with `JEV_API_KEY` as the user's alias:
   `TYPESAFE_API_KEY` wins when both are set, and a blank one falls through to the alias.
   `TYPESAFE_BASE_URL` (default `https://api.typesafe.ai`) and `TYPESAFE_DEFAULT_MODEL` (default
   `jev-latest`) are optional. The key is sent only in the `Authorization` header. It is masked in
   every message, and cassettes never store headers. Judgment ids must not contain credential
   words, because redaction masks values under such keys in recorded responses.
8. **Thresholds are provisional until calibrated on our data.** Before a threshold is relied on
   beyond the R1 baseline (for SPEC-202's L1 local enablement, or for SPEC-203's promotion
   metrics), each judgment family is checked on a labelled set of fixed states with known truth.
   Each set has at least 10 states, at least 5 positive and 5 negative, built by construction
   from fixtures (for example the same verdict with and without the failing requirement id). The
   threshold is accepted when, on that set, **no negative passes**, at least 80 % of positives pass,
   and at most 10 % land in the uncertain band. Until then, live results are recorded with the note
   that their judgment thresholds are uncalibrated. The protocol needs a fixed-output judging mode
   that bench does not have yet.

## Consequences

### Positive

- Semantic qualities and routing get a typed, machine-gradable signal with an explicit "not sure"
  outcome that goes to a human instead of a guess.
- The grader is independent of the models under test (Ollama, Claude, Codex), which avoids a
  model grading its own family's output.
- Narrow, batched questions keep cost and latency predictable: one request per case in the usual
  case.
- Offline runs stay honest: no key means `skipped`, never a pass.

### Negative

- An external, paid dependency with access that may be waitlisted, and network access the build
  container does not have yet. Until the user allowlists the host, every judged case is `skipped`.
- Benchmark state (skill text, prompts, fixtures, model output) is sent to a third party.
  Fixtures must never contain secrets.
- Calibration is unproven for our questions. A badly worded question drifts towards 0.5 and lands
  in the uncertain band (SPEC-201 risk R-9).
- Vendor coupling: the client follows the vendored 0.7.5 wire models. An API change surfaces as
  `JevProtocolError`, which is safe but stops grading.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| Jev routing measures whether descriptions are distinguishable to a calibrated judge, not whether the user's model actually picks the skill in Zed | Release trigger gates route through Jev when it is available (`--router auto`) | Record a `--router runtime` run on the same suite as a diagnostic; a large gap between the two means the descriptions need work |
| A `choice` or `score` answer passes on the right label with low confidence | Only noul has an uncertain band; confidence is recorded but not gated | Inspect confidence in run notes; add a confidence floor after calibration if needed |
| Thresholds such as 0.8 are copied from examples, not derived | No live run has happened yet | Decision 8 |
| A judgment is answered from the wrong state | Mis-declared `state_from` | `build_state` includes only the declared parts; tests pin this |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| A generative LLM as judge (the same Ollama model, or another chat model) | Self-grading, prose output to parse, no calibrated uncertainty, and a second nondeterministic model in the gate |
| Human grading only | Does not scale to regression runs on every change. Humans stay the escalation path for `needs_human` |
| Assertions only | Cannot measure semantic quality or routing |
| Embedding similarity for routing | Needs its own calibrated threshold and has no principled "none" answer |
| Treat an uncertain noul as a pass, or average it in | Converts "not sure" into "yes", which is exactly what "not run is not passed" forbids (ADR-0010) |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Bands, uncertain = fail with `needs_human`, score and choice rules | `test_bench_graders.py::TestJudgments::test_noul_bands`, `test_bench_graders.py::TestJudgments::test_uncertain_noul_fails_and_needs_a_human`, `test_bench_graders.py::TestJudgments::test_score_and_choice_rules`, `test_bench_runner.py::TestModelTiers::test_uncertain_judgment_fails_and_flags_a_human` | enforced |
| No key or no network means skipped, never passed | `test_bench_runner.py::TestModelTiers::test_missing_jev_key_means_off_without_network`, `test_bench_runner.py::TestModelTiers::test_jev_off_leaves_judged_cases_ungraded`, `test_bench_runner.py::TestModelTiers::test_unavailable_services_are_skipped_never_passed` | enforced |
| Judgments only with Jev on | `benchmark-result.v1` cannot carry judgments with `jev_mode: "off"` (schema invariant, `test_contracts.py`) | enforced |
| Interface violations are errors, not grades | `test_jev_client.py::TestStrictResponses::test_protocol_violations`, `test_jev_client.py::TestStrictResponses::test_non_json_200_is_a_protocol_error` | enforced |
| Batching and declared state | `test_jev_client.py::TestBuilders::test_batches_group_by_state_from_set`, `test_jev_client.py::TestBuilders::test_build_state_only_includes_declared_parts`, `test_jev_client.py::TestBuilders::test_routing_question` | enforced |
| Key precedence and secrecy | `test_jev_client.py::TestConfiguration::test_key_precedence_and_defaults`, `test_jev_client.py::TestSystemOne::test_401_and_403_are_auth_errors_without_the_key`, `test_jev_cassette.py::TestCassette::test_secret_values_and_credential_keys_are_redacted` | enforced |
| Replay only from recordings; misses never answered | `test_jev_cassette.py::TestCassette::test_replay_miss_is_never_answered`, `test_bench_runner.py::TestModelTiers::test_record_then_replay_without_services`, `test_bench_runner.py::TestModelTiers::test_replay_miss_is_skipped` | enforced |
| Replayed or partial runs never satisfy a live gate | `skill-lab release check` (G-LIVE-05) | planned (SPEC-201 FR-041, FR-042) |
| The client matches the live API | Only a fake server on 127.0.0.1 has been used. No request has reached `api.typesafe.ai` from this repository | not run |
| Thresholds calibrated on labelled data (decision 8) | Fixed-output judging mode and calibration sets; no location is defined in CONVENTIONS §1 yet | gap |

**Revisit when** the first live run is recorded (re-check every threshold against decision 8), when
TypeSafe changes its wire models, or if the uncertain rate stays above 0.1.

## References

- [SOURCES.md: TypeSafe AI "Jev"](../research/SOURCES.md#typesafe-ai-jev-system-one-model),
  [runbook: set up Jev](../runbooks/setup-jev.md)
- [SPEC-103 Jev grader client](../../specs/103-jev-grader/spec.md),
  [SPEC-102 bench](../../specs/102-bench-runtimes-graders/spec.md) FR-005..FR-008, FR-014
- [CONVENTIONS §5](../CONVENTIONS.md#5-evals-and-benchmarks)
- ADR-0010 (not run is not passed), ADR-0011 (gates that use Jev metrics)
