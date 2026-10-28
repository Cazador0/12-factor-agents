# ADR-0005: Deterministic scripts own state transitions; the model proposes, policy decides, Gitea enforces

## Status

Accepted

## Date

2026-10-22

## Context

The report's central doctrine (report
[§Orchestrator state model](../research/engineering-team-report.md#orchestrator-state-model)):

> LLM decides what it believes should happen.
> Policy code decides what it is allowed to make happen.
> Gitea enforces the final repository rules.

It also gives a deterministic `next_action(issue, project, pull_request, checks, review)` function
and an explicit 10-state board with an owner per state
([§Kanban state machine](../research/engineering-team-report.md#kanban-state-machine)), and says
autonomy "should be implemented as a state machine with evidence and permissions, not as a powerful
prompt" ([§Final recommended operating doctrine](../research/engineering-team-report.md#final-recommended-operating-doctrine)).

The 12-factor principles point the same way. Factor 8 says to own the control flow instead of
letting the model loop freely. Factor 12 says to make the agent a stateless reducer: the next state
is a pure function of the current state and the incoming event. Factor 5 says to keep execution
state and business state in one place, and Factor 6 to make work pausable and resumable.

The models that run these skills are small or remote, nondeterministic, and replaceable
mid-task. Every session must be replaceable because its durable state lives outside the
conversation (report doctrine).

## Decision

1. **Every decision that changes state, or that a later step relies on, is computed by a
   deterministic script from explicit inputs.** The scripts planned in SPEC-201:

   | Decision | Script (skill) | Output contract |
   |---|---|---|
   | Is the feature ready to build? | `spec_readiness.py` (lead-architect) | `spec-readiness.v1` |
   | Task order, waves, write-set conflicts | `plan_dag.py` (lead-architect) | `task-graph.v1` |
   | What to dispatch next, and what to defer | `dispatch_recommend.py` (lead-architect) | `dispatch-plan.v1` |
   | Is a board transition legal, and what is the next action? | `transition.py` (kanban-state-machine) | `transition-decision.v1` |
   | May this lease be granted? | `lease.py` (work-lease) | `lease.v1`, `lease-check.v1` |
   | Is this webhook authentic and new? | `normalize.py` (gitea-event-normalizer) | `normalized-event.v1` |
   | Did the evidence come from executed checks? | `evidence_manifest.py` (pse-implementer) | `implementation-evidence.v1` |
   | Did the quality gate pass? | `quality_gate.py` (review-verifier) | `quality-gate.v1` |
   | What is the verdict? | `review_verdict.py` (review-verifier) | `review-verdict.v1` |
   | May this PR merge, and how? | `merge_decision.py` (merge-policy-gate) | `merge-decision.v1` |
   | May this task be marked done? | `dev_state.py mark` (speckit-development) | `development-report.v1` |

2. **The model orchestrates and supplies judgement, never state.** It picks the next procedure
   step, provides inputs that code cannot compute (draft acceptance criteria, review findings
   with evidence), and relays envelopes. It never asserts a state. It requests one with a
   `mutation-request.v1`, and a script rules on it. A verdict of `APPROVE` exists only if
   `review_verdict.py` computed it from a passing quality gate, zero blockers and zero
   unverified requirements.
3. **Scripts are stateless reducers.** Output is a function of the input files, the flags and the
   clock (`--now`). There is no hidden state: durable state lives in Gitea (ADR-0009), in committed
   files (specs, the task-issue map), or under `--state-dir` (leases, seen sets, checkpoints).
   The same inputs give a byte-identical payload.
4. **Four layers, each able to refuse, none able to override a refusal below it:**
   1. the script's own preconditions (`transition-decision.preconditions[]`, `required_role`,
      lease conflicts, schema validity of inputs);
   2. the autonomy policy, `_skillkit.policy.require(action)`, which exits 4 when the level does
      not allow the action (CONVENTIONS §8; planned for ADR-0101 and ADR-0102);
   3. the explicit `--apply` flag: without it a script only emits a plan (`gitea-plan.v1` or
      `mutation-plan.v1`) and exits 0;
   4. Gitea itself: branch protection, required checks, required reviews, and a human merge where
      the level requires it (ADR-0008, ADR-0009).
5. **"Planned" and "refused" never mix.** A script checks every action in its plan before the
   first side effect (all-or-nothing preflight). A refusal (exit 4) carries no plan. A caller
   re-runs without `--apply` to see the plan (SPEC-201 synthesis D-7).
6. **The board is the report's board.** kanban-state-machine encodes the 10 states (Backlog,
   Ready for Spec, Specifying, Ready for Build, In Progress, Review, Changes Requested, Ready to
   Merge, Done, Blocked) with their owners, and implements `next_action` branch for branch.
7. **Recommendations are recorded, not acted on.** Where a decision is capped by the autonomy
   level, the uncapped result is recorded for calibration (`merge-decision.uncapped_decision`) and
   no consumer acts on it (SPEC-201 synthesis D-24).
8. **Time is an input, and its source matters.** `--now` exists so tests and re-runs are
   reproducible. A decision that grants authority from elapsed time (lease expiry and takeover,
   merge-schedule expiry, freshness) must not trust a caller-supplied `--now` once it acts with
   `--apply` above `shadow`.

## Consequences

### Positive

- Every decision is reproducible and testable offline. The deterministic benchmark tier covers it
  with no model in the loop.
- A small model only has to follow numbered steps and read error codes. The hard reasoning about
  legality lives in tested code.
- A replacement session can continue from repository, Gitea and checkpoint state. Nothing lives
  only in a transcript.
- The decision record is auditable: every refusal has a code, and every plan has idempotency keys
  and reasons.

### Negative

- More code. SPEC-201 plans about 32 scripts across 13 skills, each with tests and eval cases.
- Rigidity. A situation the scripts do not model ends in a refusal or escalation, not in an
  improvised fix. That is intended, but it costs human attention.
- Latency. One tool call per step, and plans before applies, mean more round trips than a
  free-running agent.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| An agent in an IDE runtime bypasses the scripts with its shell or editor | Scripts are guardrails; the runtime has a terminal | Gitea branch protection and human merge are the boundary (ADR-0008) |
| A deterministic function of wrong inputs gives a wrong answer, for example hand-typed evidence | Garbage in, garbage out | Evidence binds to `check-run` log digests; Review rebuilds the requirements matrix from `spec.md`, not from PSE's claims; R2 re-reads Gitea before every write (SPEC-202 synthesis D-5) |
| A caller passes a fabricated `--now` to make a lease look expired | `--now` is a common flag on every script | Decision 8; enforcement is not built yet (gap below) |
| The state machine and Gitea disagree after a partial failure | Networks fail mid-sequence | Plans are idempotent; R2 journals each operation; R3 treats events as hints and reconciles from live state (SPEC-203) |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Let the model drive state directly (set labels, merge, write leases) | Nondeterministic, untestable, and the report rules it out |
| Rules written only in prompts | Prompts are not enforced. The report asks for mechanical constraints over prose |
| A workflow engine or database service as orchestrator | Needs infrastructure and network; scripts must run offline on the standard library (ADR-0006). Gitea already stores the state |
| An MCP server as the policy point in R1 | The report recommends a semantic Gitea tool surface, and R2/R3 grow towards it, but R1 must run as offline stdlib scripts (SPEC-201 non-goals) |
| Trust `--now` everywhere | Lets a caller forge elapsed time for authority decisions |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Every skill has deterministic cases, and all of them pass | `evals.deterministic-count` (at least 4 per skill); default gate `deterministic-all-pass` (`bench.deterministic.pass_rate == 1.0`) in [`_defaults.json`](../../benchmarks/criteria/_defaults.json) | enforced (lab); per skill once skills exist |
| Same inputs and `--now` give the same output | Per-script `test_*_is_deterministic` tests (SPEC-201 plan §Test strategy); bench run ids: `test_bench_runner.py::TestDeterministicTier::test_run_id_is_deterministic_with_now` | planned (skills); enforced (bench) |
| The board and `next_action` match the report | `skills/kanban-state-machine/tests/test_transition.py` (SPEC-201 T107) | planned |
| Plans without `--apply`; refusals exit 4 with no effect | `skill-lab policy containment` (G-OFF-07): every policy-tagged case run with `--apply` at `shadow` must exit 4 with no request, ref change or file write | planned (SPEC-201 FR-011) |
| Illegal decisions cannot be represented | Schema invariants: `review-verdict` APPROVE, `merge-decision` AUTO_MERGE, `quality-gate` passed (`test_contracts.py::TestExamples::test_every_example_validates` and the crafted invalid cases) | enforced |
| Time-based authority ignores a caller-supplied clock under `--apply` | No check yet | gap |

**Revisit when** a decision the report requires cannot be expressed as a function of recorded
inputs, or when an MCP gateway takes over the policy point from the scripts.

## References

- Report [§Orchestrator state model](../research/engineering-team-report.md#orchestrator-state-model),
  [§Kanban state machine](../research/engineering-team-report.md#kanban-state-machine),
  [§Claiming work safely](../research/engineering-team-report.md#claiming-work-safely)
- 12-factor [Factor 5](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-05-unify-execution-state.md),
  [Factor 6](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-06-launch-pause-resume.md),
  [Factor 8](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-08-own-your-control-flow.md),
  [Factor 12](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-12-stateless-reducer.md)
- [CONVENTIONS §3](../CONVENTIONS.md#3-script-contract-v), [§8](../CONVENTIONS.md#8-autonomy-levels)
- [SPEC-201 R1](../../specs/201-release-shadow/spec.md) FR-007, FR-011, FR-018..FR-031;
  [SPEC-201 synthesis](../../specs/201-release-shadow/synthesis.md) D-7, D-24
