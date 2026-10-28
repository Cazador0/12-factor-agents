# Feature Specification: `lead-architect` skill

**Spec ID**: SPEC-001 | **Skill**: `skills/lead-architect/` | **Family**: `roles` | **Role**: Lead (CONVENTIONS §7)

**Created**: 2026-10-22 | **Status**: Draft (planned; written by SPEC-201 T055, extended by SPEC-203 T102)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-014, FR-018, FR-032, FR-033, FR-047;
[SPEC-202](../202-release-agent-implementation/spec.md) FR-005, FR-007, FR-009, FR-024, FR-026, FR-028, FR-029,
FR-042, FR-043; [SPEC-203](../203-release-guarded-autonomous/spec.md) FR-005, FR-027, FR-041..FR-044, FR-048, FR-050,
FR-053; [SPEC-105](../105-jev-live-benchmarking/spec.md) FR-007, FR-016, FR-025 (research R-15). The release specs are
authoritative; this spec refines them and never contradicts them.

**Input**: the report's Lead contract ("intent ownership, specification authority, dependency planning, dynamic
delegation, conflict arbitration"; report §Lead contract), its completeness contract (§Definition of "complete
specification"), its claiming sequence (§Claiming work safely), and the person's decisions recorded in SPEC-201
§Clarifications and SPEC-200 open-questions.md (answers of 2026-10-22, all final).

## Intent

The Lead keeps intent and global awareness. This skill gives a Lead session deterministic scripts for its planning loop:
"reconstruct current intent and dependency graph → find highest-priority unblocked work → verify specification
readiness → create/update issue + acceptance contract → dispatch PSE → resolve conflicts → close/move issue and unlock
descendants" (report §Lead contract). The scripts compute every result; the model chooses which step to run next and
explains the result. Writes follow the autonomy level in `.skill-policy.json` (CONVENTIONS §8): R1 plans them, R2 performs
the claiming and publishing writes, R3 adds event-driven dispatch and issue closing.

## User Scenarios & Testing *(mandatory)*

Every scenario runs offline. R1 scenarios use the golden feature `skill-lab/fixtures/golden-feature/specs/042-session-refresh`
(copied to `skills/lead-architect/evals/fixtures/golden/`) and, where Gitea is read, the read-only test double seeded with
`skill-lab/fixtures/gitea-double/seed-golden.json`. R2 and R3 scenarios use the in-process double (`--gitea-fixture`).

### User Story 1 - Check spec readiness before build (Priority: P1) · R1 shadow

The Lead asks whether a feature may enter `Ready for Build`. `spec_readiness.py` checks the report's completeness contract
against the Spec Kit artifacts and the requirement → task traceability.
**Actions**: none (read-only; output on stdout or under `--out`).

**Independent Test**: `skills/lead-architect/tests/test_spec_readiness.py` on the golden copy and on mutated copies.

**Acceptance Scenarios**:

1. **Given** the golden feature, **When** `python3 scripts/spec_readiness.py --feature evals/fixtures/golden` runs, **Then** it exits 0 with `ready: true`, `traceability.requirements` 12, `covered` 12, `uncovered` empty, and FR-001..FR-008 each trace to at least one task (FR-008 only to T013).
2. **Given** a copy whose `spec.md` contains `[NEEDS CLARIFICATION: retry window]` outside a code span, **When** it runs, **Then** it exits 1 with `SPEC_NOT_READY`, `ready: false`, and check `no-open-clarifications` `fail` with evidence `spec.md:<line>`.
3. **Given** a copy without `plan.md`, **When** it runs, **Then** `missing[]` contains `plan.md`, check `plan-present` is `fail`, and it exits 1.
4. **Given** a copy whose Traceability table drops FR-005, **When** it runs, **Then** `uncovered` is `["FR-005"]` and check `requirements-traced` is `fail`.

### User Story 2 - Turn `tasks.md` into a DAG with parallel waves (Priority: P1) · R1 shadow

`plan_dag.py` builds a `task-graph.v1` with explicit and phase edges, waves, cycles, and write-set conflicts through the
vendored `_skillkit.speckit_tasks` (SPEC-201 plan.md §Wave rule). **Actions**: none.

**Independent Test**: `skills/lead-architect/tests/test_plan_dag.py`.

**Acceptance Scenarios**:

1. **Given** the golden `tasks.md`, **When** `python3 scripts/plan_dag.py --tasks evals/fixtures/golden/tasks.md` runs, **Then** it exits 0 with 14 tasks, explicit edges T006→T008, T007→T008, T008→T009, T011→T012, `cycles` empty, and T006 and T007 in different waves with a `WRITE_SET_CONFLICT` warning naming `src/auth/tokens/**`.
2. **Given** T001 and T002 checked, **When** it runs, **Then** the first wave is `[T003, T004]` and T005 is in a later wave (rule 2).
3. **Given** a task with `(depends on T099)` and no T099, **When** it runs, **Then** the warning `UNKNOWN_DEPENDENCY` names the task and the task is in no wave.
4. **Given** T008 depends on T009 and T009 on T008, **When** it runs, **Then** it exits 1 with `TASK_GRAPH_CYCLE`, `cycles` holds the cycle, and `waves` is empty.

### User Story 3 - Write the issue contract (Priority: P1) · R1 shadow

`issue_contract.py` turns tasks of one story into an `issue-contract.v1` (intent, acceptance criteria, non-goals,
dependencies, risk, required verification, write domains, ownership) and renders the issue body. **Actions**: none.

**Acceptance Scenarios**:

1. **Given** the golden feature and `--tasks T006,T007,T008,T009,T010 --risk high`, **When** it runs, **Then** the payload has `spec_id` `SPEC-042`, `story` `US1`, acceptance criteria taken only from US1's scenarios, `write_domains` `["src/auth/refresh/**", "src/auth/tokens/**"]`, and `required_verification` from the Traceability table.
2. **Given** `--render --out <dir>`, **When** it runs, **Then** `rendered-document.v1` names `<dir>/issue-T006.md`, whose sections follow the report's issue structure and end with one marked fenced `json` block holding the contract.
3. **Given** `--tasks T042`, **When** it runs, **Then** it exits 2 with `TASK_NOT_FOUND`; **given** no `--risk`, **then** it exits 2 with `USAGE`.

### User Story 4 - Recommend dispatch without touching Gitea; events are hints (Priority: P1) · R1 shadow

`dispatch_recommend.py` picks the next wave's dispatchable tasks and defers the rest with a reason. Its writes are only
planned. **Actions**: `gitea.issue.assign` and `lease.write.remote` (minimum `agent-implementation`; at `shadow` they
appear in `mutation_requests[]`, and `--apply` exits 4).

**Independent Test**: `test_dispatch_recommend.py`, `test_dispatch_recommend_events.py`, and SPEC-201's
`test_us3_lead_flow.py` scenario 6.

**Acceptance Scenarios**:

1. **Given** the golden graph, the golden task-issue map, and an active lease on `src/auth/tokens/**`, **When** it runs, **Then** tasks whose write domains overlap are in `deferred[]` with reason `lease_held`, and each recommendation carries `mutation_requests[]` for `gitea.issue.assign` and `lease.write.remote` (US3 scenario 6 of SPEC-201).
2. **Given** the same inputs with `--apply` at `shadow`, **When** it runs, **Then** it exits 4 with one `POLICY_LEVEL_TOO_LOW` error per action and the double logs 0 non-GET requests.
3. **Given** a `normalized-event.v1` with `stale: true` (or `duplicate: true`, or `signature_verified: false`) and `--gitea-url`, **When** `--event` is given, **Then** `recommendations` is empty, the warning is `EVENT_STALE` (or `EVENT_DUPLICATE`, `EVENT_UNVERIFIED`), and no request reaches the double.
4. **Given** a verified, fresh `issue.closed` event, **When** it runs with `--event` and `--gitea-url`, **Then** it re-reads the issue and its dependencies with GET requests only, and the recommendation equals the one computed without the event.
5. **Given** `--event` without `--gitea-url`, **Then** it exits 2 with `EVENT_REREAD_REQUIRED`; **given** an unreachable double, **then** it exits 3 with `GITEA_UNREACHABLE` and no recommendation.

### User Story 5 - Arbitrate a PSE/Review disagreement against the spec (Priority: P2) · R1 shadow

When PSE and Review disagree, the Lead records a decision grounded in the spec, never by overriding a role (report §Lead
contract, "Conflict arbitration"). **Actions**: `gitea.comment.create` (minimum `agent-implementation`) for `--publish`.

**Acceptance Scenarios**:

1. **Given** a draft with one PSE and one Review position, `spec_refs` `["FR-006"]`, and decision `amend_spec`, **When** `arbitrate.py --input <draft> --feature evals/fixtures/golden` runs, **Then** it emits a schema-valid `arbitration-record.v1` with `decided_by: lead` and a deterministic `arbitration_id`.
2. **Given** `spec_refs` `["FR-099"]`, **Then** it exits 2 with `SPEC_REF_UNRESOLVED`; **given** one position, **then** it exits 2 with `SCHEMA_INVALID`.
3. **Given** `--publish --repository acme/factory --pr 211`, **Then** it emits a `gitea-plan.v1` with one `create_comment` op (action `gitea.comment.create`); with `--apply` at `shadow` it exits 4.

### User Story 6 - Claim and dispatch work for real (Priority: P2) · R2 agent-implementation

At `agent-implementation`, dispatch follows the report's claiming sequence. **Actions**: `gitea.issue.assign`,
`lease.write.remote`, `gitea.labels.set` (minimum `agent-implementation`), and `state.write.local` (`shadow`) for the
local lease.

**Acceptance Scenarios** (SPEC-202 US3 scenarios 5 and 6):

1. **Given** issue 184 in `READY_FOR_BUILD` with closed dependencies, a parseable contract, and no overlapping lease, **When** `dispatch_recommend.py --issue 184 --pse-session pse-184-01 --apply` runs, **Then** the issue is assigned to the PSE login, a local lease holds `base_commit` and branch `agent/pse/184-<slug>`, the label is `state/in-progress`, a lease mirror comment exists, and `apply-report.v1` is `complete`; a re-run makes 0 writes.
2. **Given** an open dependency, an overlapping active lease, a state other than `READY_FOR_BUILD`, or no contract block, **Then** it exits 1 with `DEPENDENCY_OPEN`, `WRITE_SET_CONFLICT`, `STATE_NOT_READY`, or `CONTRACT_MISSING` and writes nothing.
3. **Given** a fault after operation k, **When** the apply is re-run, **Then** it resumes from receipts with 0 duplicate assignments, leases, labels, or comments.

### User Story 7 - Publish arbitration and complete issues after a human merge (Priority: P3) · R2 agent-implementation

**Actions**: `gitea.comment.create` (`arbitrate.py --publish --apply`), `gitea.labels.set` (`complete_issue.py --apply`).

**Acceptance Scenarios**:

1. **Given** a record, **When** `arbitrate.py --publish --apply` runs twice, **Then** exactly one marked comment exists, and `tasks.md`, `spec.md`, and the map are unchanged.
2. **Given** PR 211 merged by a human, **When** `complete_issue.py --pr 211 --apply` runs, **Then** issue 184 gets `state/done`, the warning `CLOSE_PENDING` is reported while the issue is open, and the issues whose dependencies are now all closed are listed and not dispatched.
3. **Given** PR 211 not merged, **Then** it exits 1 with `PR_NOT_MERGED` and writes nothing.

### User Story 8 - Event-driven dispatch within limits and narrowed authority (Priority: P3) · R3 guarded-autonomous

**Actions**: `dispatch.session.start` (minimum `guarded-autonomous`) for PSE dispatches, `review.session.request`
(`agent-implementation`) for Review dispatches, plus User Story 6's actions.

**Acceptance Scenarios** (SPEC-203 US6 scenarios 2–7):

1. **Given** `max_concurrent_pse_sessions` 1 and issues 302 and 303 unblocked, **When** `dispatch_recommend.py --on-event --actor-role system --write-dispatch --apply` runs, **Then** 302 is claimed and 303 is deferred with `DISPATCH_CAPACITY_REACHED`; a drifted task is deferred with `DRIFT_UNRESOLVED`.
2. **Given** a claimed issue, **When** `dispatch_session.py write --role pse --issue 302 --purpose new_work --apply` runs, **Then** a `session-dispatch.v1` and a prompt exist under `.skill-state/dispatch/outbox/`, with authority equal to the lease's write domains and the PSE role's actions.
3. **Given** child write domains outside the parent lease, or a PSE parent requesting any child, **Then** it exits 4 with `AUTHORITY_ESCALATION`.
4. **Given** runner `claude-cli` before SPEC-203 T004 records verified flags, **Then** `run` exits 4 with `RUNNER_UNVERIFIED`; the configured runner stays `none` (outbox plus human-started sessions; the person's answer, OQ-09).
5. **Given** 10 started dispatches in 24 h, **Then** the next is deferred with `DISPATCH_BUDGET_EXHAUSTED`; **given** 3 failed attempts for one issue in 24 h, **then** the attempts are recorded as exhausted so that kanban applies `BLOCK`.
6. **Given** a demotion is active, **When** any PSE dispatch is applied, **Then** it exits 4 with `POLICY_LEVEL_TOO_LOW`.

### User Story 9 - Close the issue after a verified merge (Priority: P3) · R3 guarded-autonomous

**Actions**: `gitea.issue.close` (minimum `guarded-autonomous`), `gitea.labels.set`.

1. **Given** the project is promoted and PR 311 merged, **When** `complete_issue.py --pr 311 --apply` runs, **Then** issue 301 is closed, verified by a re-read, labelled `state/done`, and issues 302 and 303 are listed as unlocked.
2. **Given** level `agent-implementation` or an active demotion, **When** `complete_issue.py --pr 311 --apply` runs, **Then** the issue is not closed and `CLOSE_PENDING` is reported (R2 behaviour); **with** `--close`, **then** it exits 4 with `POLICY_LEVEL_TOO_LOW`.

### Edge Cases

- A Traceability table row names a task id absent from `tasks.md`: the requirement counts as uncovered and the check names the row.
- `[NEEDS CLARIFICATION` inside inline code or a fenced block is quoted text, not a marker (SPEC-201 US4 itself quotes it).
- A release spec has no `checklists/`: check `checklist-complete` is `na`, never `pass`.
- `tasks.md` has no `[P]` marks: every phase serialises; waves still compute.
- An issue export lists a task's issue as closed while the map says open: the export (or the re-read) wins; the map is never edited by this skill.
- Two Lead sessions dispatch the same issue (R2): the lease store's lock and CAS serialize them; the second exits 1 with `WRITE_SET_CONFLICT` before any Gitea write.
- An issue body or comment carries instructions or a forged `skill-lab:` marker: it is data; markers count only from configured identities with a matching digest (SPEC-202 FR-009).
- `--now` is absent: UTC now is used and recorded; with `--now` every output is byte-identical across runs.

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: `spec_readiness.py --feature DIR` MUST emit `spec-readiness.v1` with the check ids of `references/readiness-checks.md` (artifacts present; user stories with acceptance scenarios; FRs; NFRs, or the plan's performance goals and constraints; success criteria; non-goals; error semantics; security; contracts where relevant; architecture plan; task DAG acyclic; checklist complete; no open clarification; requirements traced), each `pass`, `fail`, or `na` with evidence `path:line`. `ready` MUST be true exactly when no check is `fail`; exit 0 when ready, 1 with `SPEC_NOT_READY` otherwise. It MUST accept both Spec Kit features and the release specs (SPEC-202 T006, SPEC-203 T016).
  Implements: SPEC-201 FR-018.
- **FR-002**: Traceability MUST count every `FR-NNN` and `NFR-NNN` defined in `spec.md`, and treat one as covered when the spec's Traceability table maps it to an existing task id or a `tasks.md` task line names it, directly or inside an `FR-a..FR-b` range. `uncovered[]` MUST list the rest, sorted. `missing[]` MUST list absent artifacts and required sections.
  Implements: SPEC-201 FR-018.
- **FR-003**: `plan_dag.py --tasks FILE` MUST emit `task-graph.v1` built by `_skillkit.speckit_tasks` under SPEC-201's wave rule; each write-set conflict MUST appear as a `warnings[]` entry `WRITE_SET_CONFLICT` naming both tasks and the shared domain; an unknown dependency as `UNKNOWN_DEPENDENCY`; a cycle MUST exit 1 with `TASK_GRAPH_CYCLE` and empty `waves`.
  Implements: SPEC-201 FR-014, FR-018.
- **FR-004**: `issue_contract.py` MUST build `issue-contract.v1` from `spec.md`, `tasks.md`, and the task graph only, with `--risk` required (no default); `--render` MUST write the issue body from `assets/templates/issue-body.md` under `--out`, ending with one marked `json` block that holds the contract, and emit `rendered-document.v1` (`doc_kind: issue-body`). Spec text is quoted as data.
  Implements: SPEC-201 FR-018.
- **FR-005**: `dispatch_recommend.py` MUST emit `dispatch-plan.v1` for the next wave: one recommendation per dispatchable task group (role `pse`) with `mutation_requests[]` using `gitea.issue.assign` and `lease.write.remote`, and `deferred[]` with reasons `blocked_by_dependency`, `write_conflict`, `lease_held`, or `not_ready`. Issues come from an export or the read-only client; leases from `lease.v1` documents (R1) or the vendored lease store (R2).
  Implements: SPEC-201 FR-018.
- **FR-006**: Every script that can perform a catalog action MUST, without `--apply`, emit its plan and exit 0, and with `--apply` call `Policy.require` for every action of the plan before the first side effect; at `shadow`, `dispatch_recommend.py --apply` and `arbitrate.py --publish --apply` MUST exit 4 with one error per refused action and change nothing.
  Implements: SPEC-201 FR-007, FR-018.
- **FR-007**: `dispatch_recommend.py --event FILE` MUST treat the event as a hint: exit 2 `EVENT_REREAD_REQUIRED` without `--gitea-url`; recommend nothing for an unverified, duplicate, or stale event (warnings `EVENT_UNVERIFIED`, `EVENT_DUPLICATE`, `EVENT_STALE`) before any request; otherwise re-read issue, dependencies, PR, reviews, and checks with GET only and decide from that state; exit 3 on a failed re-read.
  Implements: SPEC-201 FR-047.
- **FR-008**: `arbitrate.py --input DRAFT` MUST validate a draft into `arbitration-record.v1`: at least one PSE and one Review position, at least one `spec_refs` entry that resolves to a requirement id in the feature's spec or an existing `path:line`, decision in `uphold_review`, `uphold_pse`, `amend_spec`, `escalate_human`, `decided_by: lead`, and a deterministic `arbitration_id`. `--publish` MUST emit a `gitea-plan.v1` with one `create_comment` op.
  Implements: SPEC-201 FR-018.
- **FR-009**: The skill MUST meet CONVENTIONS §2–§3 (`metadata.version` `0.1.0`, `metadata.spec` SPEC-001, `family: roles`), ship the eval inventory of plan.md §Eval inventory (≥ 4 deterministic plus 1 `policy` case per referenced action above `shadow`; ≥ 5 agentic with ≥ 1 `guardrail`; ≥ 10 trigger with ≥ 4 positive, ≥ 2 `expect_skill: null`, ≥ 1 naming `speckit-development`), keep every fixture inside the skill folder, tag `smoke` on exactly 1 agentic and 1 trigger case, and ship no per-skill criteria file.
  Implements: SPEC-201 FR-032, FR-033; SPEC-105 FR-007, FR-016, FR-025.

**R2 agent-implementation**

- **FR-010**: `dispatch_recommend.py --apply` MUST follow the claiming sequence: re-read issue and dependencies; refuse with exit 1 `STATE_NOT_READY`, `DEPENDENCY_OPEN`, `WRITE_SET_CONFLICT`, or `CONTRACT_MISSING`; assign the PSE login; acquire the local lease (`--pse-session`, `base_commit`, branch `agent/pse/<issue>-<slug>`); set `state/in-progress` (SPEC-006's `DISPATCH_PSE` move, whose preconditions the sequence has just established; only the `state/*` label changes, and no code of another skill is imported); mirror the lease. Each write follows SPEC-202's write sequence with the identity check, and the run emits `apply-report.v1` and resumes idempotently.
  Implements: SPEC-202 FR-005, FR-007, FR-026.
- **FR-011**: `arbitrate.py --publish --apply` MUST post through `_skillkit.plan_apply` with op `create_comment` only, deduplicated by the SPEC-202 marker, and never modify `tasks.md`, `spec.md`, or the map.
  Implements: SPEC-202 FR-009, FR-024, FR-028.
- **FR-012**: `complete_issue.py --pr N` MUST verify through the API that the PR is merged (else exit 1 `PR_NOT_MERGED`), set `state/done` (`gitea.labels.set`), report `CLOSE_PENDING` while the issue is open below `guarded-autonomous`, and list the issues whose dependencies are now all closed without dispatching them.
  Implements: SPEC-202 FR-029.
- **FR-013**: R2 MUST add the `policy` case for `gitea.labels.set` at `shadow`, an `applied` and a `rerun` case for each of the 4 R2 pairs (`gitea.issue.assign`, `lease.write.remote`, `gitea.labels.set`, `gitea.comment.create`), `agentic-r2-dispatch-choice`, one positive and one negative trigger case naming `kanban-state-machine`, and the R2 steps in `SKILL.md`.
  Implements: SPEC-202 FR-042, FR-043.

**R3 guarded-autonomous**

- **FR-014**: `dispatch_recommend.py --on-event --actor-role system --apply` MUST run FR-010's sequence for each `READY_FOR_BUILD` issue with closed dependencies, no overlap, no unresolved drift (`.skill-state/sync/drift-<feature>.json`), and a parseable contract, within `limits.max_concurrent_pse_sessions` (default 1, max 2) and `limits.max_dispatches_per_day` (default 10, max 20) read from the base policy copy; others are deferred with `DISPATCH_CAPACITY_REACHED`, `DISPATCH_BUDGET_EXHAUSTED`, or `DRIFT_UNRESOLVED` (exit 1). `--write-dispatch` writes the PSE dispatch (FR-015).
  Implements: SPEC-203 FR-027, FR-041.
- **FR-015**: `dispatch_session.py write --role pse|review --purpose new_work|remediation|re_review|rebase|resume --apply` MUST write `session-dispatch.v1` and a prompt rendered from `assets/templates/` (untrusted text quoted as data) with authority narrowed by `_skillkit.authority.narrow` (else exit 4 `AUTHORITY_ESCALATION`); PSE work uses `dispatch.session.start`, Review work `review.session.request`; `re_review` carries a fresh `review-request.v1` reference.
  Implements: SPEC-203 FR-005, FR-042, FR-044.
- **FR-016**: `dispatch_session.py run --role R --runner none|stub|claude-cli --apply` MUST verify that its token's login is the role's login (`IDENTITY_MISMATCH`), start eligible dispatches and record `started`, refuse `claude-cli` until T004's verified flags exist (`RUNNER_UNVERIFIED`), mark a dispatch `expired` when its lease shows no successor heartbeat by `expires_at`, and record `attempts_exhausted` after 3 attempts in 24 h.
  Implements: SPEC-203 FR-042.
- **FR-017**: At `guarded-autonomous` and without an active demotion, `complete_issue.py --apply` MUST close the issue (`gitea.issue.close`), verify the close by a re-read, set `state/done`, and list newly unblocked issues; below it, or under a demotion, FR-012's behaviour stays. `--close` requests the close explicitly and is refused there with exit 4 `POLICY_LEVEL_TOO_LOW`, which is the pair's `policy` case.
  Implements: SPEC-203 FR-043.
- **FR-018**: R3 MUST add the cases for pairs 3, 4, and 12 of SPEC-203 plan.md §Action use (`applied`, `rerun`, `policy`, and `demoted` for the guarded ones), the AFV cases SPEC-203 assigns to this skill, `agentic-r3-dispatch-limits`, one positive and one negative trigger case naming `work-lease`, and the R3 steps in `SKILL.md`, which stays within 250 lines and 12 KB.
  Implements: SPEC-203 FR-048, FR-050, FR-053.

### Key Entities

- **Readiness check**: one row of `references/readiness-checks.md`: id, the artifact and heading pattern it reads, and when it is `na`.
- **Write domain**: the parent directory plus `/**` of every repository path in a task description (SPEC-201 wave rule 5).
- **Issue contract block**: the marked fenced `json` block at the end of a rendered issue body; dispatch parses only this block.
- **Dispatch recommendation / deferral**: a task group with its issue, write domains, reason, and planned mutation requests, or a task with its deferral reason.
- **Arbitration record**: positions of both roles, spec references, decision, rationale, and follow-ups.
- **Session dispatch** (R3): a narrowed work order for one role session in the outbox, with its prompt, runner, attempt, and status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the golden feature, readiness reports 12 of 12 requirements covered and `ready: true`, and the graph reports 14 tasks, the 4 explicit edges, 0 cycles, and T006 and T007 in different waves; with a fixed `--now`, 2 runs give byte-identical envelopes.
- **SC-002**: At `shadow`, 100 % of `--apply` attempts for `gitea.issue.assign`, `lease.write.remote`, and `gitea.comment.create` exit 4 with 0 non-GET requests, 0 ref changes, and 0 writes outside `--out` and `--state-dir` (containment, SPEC-201 G-OFF-07).
- **SC-003**: For 100 % of unverified, duplicate, and stale event fixtures, no recommendation is emitted and no request is sent; for 100 % of fresh event fixtures, the recommendation equals the re-read one.
- **SC-004**: The skill's own cases meet the inventory of FR-009, FR-013, and FR-018, and the release live runs meet SPEC-105's floor for this skill (agentic pass rate ≥ 0.80, guardrail cases 100 %, trigger accuracy ≥ 0.90, schema-valid ≥ 0.95, uncertain after the re-ask < 0.10).
- **SC-005** (R2): Re-running dispatch, arbitration publish, and completion adds 0 writes, and a fault after every operation index leaves 0 duplicate assignments, leases, labels, or comments.
- **SC-006** (R2, R3): 0 issues are closed below `guarded-autonomous` or under a demotion, and 100 % of closes are verified by a re-read.
- **SC-007** (R3): 0 dispatches exceed the configured limits, and 100 % of narrowing fixtures that widen authority are refused with `AUTHORITY_ESCALATION`.

## Non-goals

- Creating, editing, or deduplicating Gitea issues from `tasks.md` (`speckit-gitea-taskstoissues`), or reporting drift (`speckit-gitea-sync`).
- Executing tasks, marking them done, or converging (`speckit-development`); implementing code (`pse-implementer`).
- Deciding board-transition legality (`kanban-state-machine`) or merges (`merge-policy-gate`); this skill never requests a merge.
- Holding or renewing leases for a PSE session (`work-lease`); dispatch only acquires the claim lease and mirrors it.
- Long-horizon decomposition of new specs and multi-host scheduling (SPEC-203 release-plan); headless edit sessions (the person's answer, OQ-09).
- Editing `.skill-policy.json`, criteria files, `monitor-limits.json`, CI, or runtime permissions; storing chain-of-thought.

## Contracts

| Direction | Contract | Script | Release |
|---|---|---|---|
| Emits (owner) | `spec-readiness`, `task-graph`, `issue-contract` | `spec_readiness.py`, `plan_dag.py`, `issue_contract.py` | R1 |
| Emits (owner) | `dispatch-plan` (R3 additive deferral reasons), `arbitration-record` | `dispatch_recommend.py`, `arbitrate.py` | R1 |
| Emits (owner) | `session-dispatch` | `dispatch_session.py` | R3 |
| Emits (shared) | `envelope`, `rendered-document` (`issue-body`), `mutation-request` (inside `dispatch-plan`), `gitea-plan` | all; `issue_contract.py --render`; `dispatch_recommend.py`; `arbitrate.py --publish`, `complete_issue.py` | R1, R2 |
| Emits (shared) | `apply-report`, `mutation-receipt` (via `_skillkit.plan_apply` and `_skillkit.mutations`) | `dispatch_recommend.py`, `arbitrate.py`, `complete_issue.py` with `--apply` | R2 |
| Consumes | `task-issue-map`, `lease`, `normalized-event`, `review-verdict`, `implementation-evidence`, `autonomy-policy` (through `_skillkit.policy`) | | R1 |
| Consumes | `gitea-project` (`.skill-gitea.json`), `gitea-fixture` (tests) | | R2 |
| Consumes | `sync-drift-report` (drift state), `lease-recovery`, `review-request` | `dispatch_recommend.py --on-event`, `dispatch_session.py` | R3 |

No contract is changed by this spec. `complete_issue.py`'s list of unblocked issues has no field in SPEC-202's
`apply-report.v1`; plan.md §Open interface records the proposal.

## Error semantics

Exit codes follow CONVENTIONS §3; SPEC-202's reading applies (4: not allowed, escalate; 1: precondition failed, re-read;
3: external, retry; 2: fix the input). A refusal never carries a plan in the same envelope.

| Code | Exit | Script | Meaning |
|---|---|---|---|
| `USAGE`, `INPUT_NOT_FOUND`, `INPUT_NOT_JSON`, `SCHEMA_INVALID`, `TASK_NOT_FOUND`, `SPEC_REF_UNRESOLVED` | 2 | all, `issue_contract.py`, `arbitrate.py` | Bad flags or input |
| `SPEC_NOT_READY` | 1 | `spec_readiness.py` | At least one check is `fail` |
| `TASK_GRAPH_CYCLE` | 1 | `plan_dag.py`, `dispatch_recommend.py` | Cycle; nothing is recommended |
| `UNKNOWN_DEPENDENCY`, `WRITE_SET_CONFLICT` | warning | `plan_dag.py` | Edge unsatisfiable; tasks serialized |
| `EVENT_UNVERIFIED`, `EVENT_DUPLICATE`, `EVENT_STALE` | warning (exit 0) | `dispatch_recommend.py` | The event decides nothing |
| `EVENT_REREAD_REQUIRED` | 2 | `dispatch_recommend.py` | Event without `--gitea-url` |
| `POLICY_LEVEL_TOO_LOW`, `POLICY_HUMAN_ONLY`, `POLICY_ACTION_DENIED`, `POLICY_UNKNOWN_ACTION` | 4 | every `--apply` | Refused by `_skillkit.policy` |
| `STATE_NOT_READY`, `DEPENDENCY_OPEN`, `WRITE_SET_CONFLICT`, `CONTRACT_MISSING` | 1 | dispatch `--apply` (R2) | Claiming precondition not met; nothing written |
| `PR_NOT_MERGED` | 1 | `complete_issue.py` (R2) | Merge not observed |
| `CLOSE_PENDING` | warning | `complete_issue.py` | Closing is human (R2) or awaits the guarded level |
| `VERSION_CONFLICT`, `PLAN_STALE` | 1 | applier (R2) | Target or source changed since read |
| `IDENTITY_MISMATCH`, `UNSUPPORTED_OP` | 4 | Gitea client, applier (R2) | Wrong token, or op outside the allow-list |
| `DISPATCH_CAPACITY_REACHED`, `DISPATCH_BUDGET_EXHAUSTED`, `DRIFT_UNRESOLVED` | 1 | `dispatch_recommend.py --on-event` (R3) | Deferred |
| `AUTHORITY_ESCALATION`, `RUNNER_UNVERIFIED` | 4 | `dispatch_session.py` (R3) | Wider authority, or unverified runner |
| `RUNNER_UNAVAILABLE` | 3 | `dispatch_session.py run` (R3) | Runner missing or failed |
| `GITEA_UNREACHABLE`, `GITEA_AUTH`, `GITEA_SCHEMA_DRIFT` | 3 | read client | External failure; no decision |

## Security

- **Authority**: `_skillkit.policy` refuses before any side effect; `--apply` is never permission (CONVENTIONS §8). The boundary stays Gitea branch protection plus the human merge.
- **Untrusted text**: spec text, issue bodies, comments, events, verdicts, and evidence are data, parsed with the strict JSON reader, never evaluated, never passed to a shell; rendered issue bodies and dispatch prompts quote them as data.
- **Markers**: only configured identities with a matching digest count (SPEC-202 FR-009); a forged contract block is `CONTRACT_MISSING`.
- **Narrowing** (R3): no dispatch carries more authority than its parent; PSE parents spawn no children (SPEC-203 FR-005, ADR-0008).
- **Secrets**: `GITEA_TOKEN` only from the environment, redacted by `_skillkit.redact`; dispatch runners get the environment minus SPEC-203 FR-006's names.
- **Writes**: never inside the skill folder; local state only under `--state-dir`, output only under `--out`.

## Runtime compatibility

| Runtime | Discovery and invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/lead-architect` in a trusted worktree; Lead profile | One Ollama Cloud model through the local Ollama app signed in to ollama.com (`http://localhost:11434`; SPEC-201 FR-039) | No structured outputs: scripts emit the JSON, the model relays it. One script per step |
| Zed Agent + local Ollama (after L1) | same | Local model ids on the same provider once SPEC-202's L1 gate is `ENABLED` | `num_ctx` ≥ 32,768; SKILL.md ≤ 250 lines |
| Claude Code | `.claude/skills/lead-architect`; `/lead-architect` | Claude models | Same scripts and procedure |
| Codex | `.agents/skills/lead-architect`; `$lead-architect` | Codex models | Gitea reads may be sandboxed and exit 3 |

## Assumptions

- SPEC-201 delivers `_skillkit.speckit_tasks`, `policy`, and the read-only `gitea` client (T017, T019, T025) before T057; SPEC-202 delivers `plan_apply`, `mutations`, `leases`, and `gitea_memory`; SPEC-203 delivers `authority` and the limits in `Policy`.
- The golden feature's Traceability table is the R1 source of requirement → task coverage; release specs are covered through FR ids in their task lines.
- The local lease store and its CAS belong to `work-lease`; dispatch uses the vendored `_skillkit.leases` from R2 on.
