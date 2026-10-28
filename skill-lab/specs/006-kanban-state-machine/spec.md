# Feature Specification: `kanban-state-machine` skill

**Spec ID**: SPEC-006 | **Skill**: `skills/kanban-state-machine/` | **Family**: `control-plane` | **Role**: Lead profile
(CONVENTIONS §7); `system` in R3's event loop

**Created**: 2026-10-22 | **Status**: Draft (planned; written by SPEC-201 T106, extended by SPEC-203 T077)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-023, FR-032, FR-033, FR-047;
[SPEC-202](../202-release-agent-implementation/spec.md) FR-005, FR-024, FR-025, FR-042, FR-043;
[SPEC-203](../203-release-guarded-autonomous/spec.md) FR-024, FR-025, FR-026, FR-039, FR-042, FR-046, FR-048, FR-050,
FR-053; [SPEC-105](../105-jev-live-benchmarking/spec.md) FR-007, FR-016. The release specs are authoritative; this spec
refines them and never contradicts them.

**Input**: the report's board (§Kanban state machine: 10 states, owners, entry and exit conditions), its deterministic
`next_action` function and doctrine "LLM decides what it believes should happen. Policy code decides what it is allowed to
make happen. Gitea enforces the final repository rules" (§Orchestrator state model), and the person's decisions recorded in
SPEC-201 §Clarifications ("All four layers in R1") and SPEC-200 open-questions.md (answers of 2026-10-22, all final).

## Intent

The board is the shared, durable state of the engineering team. This skill decides, deterministically, whether a move on
the board is legal for a role and what the next move should be, from authoritative Gitea state, never from a model's
belief or an event's claim. Board state is one exclusive scoped label `state/<kebab-name>` per issue, because Gitea's
project-column API differs between versions (SOURCES.md Gitea). R1 decides and plans labels; R2 applies a label change
for the role that owns it; R3 lets the `system` role apply observed-fact transitions from the webhook event loop.

## User Scenarios & Testing *(mandatory)*

Every scenario runs offline. R1 reads board facts from a facts file or from the read-only test double
(`skill-lab/fixtures/gitea-double/seed-golden.json`, repository `acme/factory`); R2 and R3 use the in-process double
(`--gitea-fixture`). Issue 184 / PR 211 follow the report's running example; the golden feature's tasks are the issues.

### User Story 1 - Decide whether a transition is legal for a role (Priority: P1) · R1 shadow

A Lead, PSE, or Review session asks whether it may make a board move. `transition.py decide` checks the transition table
(§Key Entities), the owning role, and the preconditions, and returns a `transition-decision.v1`.
**Actions**: none (read-only).

**Independent Test**: `skills/kanban-state-machine/tests/test_transition.py` over every (state, action, role) triple.

**Acceptance Scenarios**:

1. **Given** issue 184 labelled `state/in-progress` with open PR 211 and a `success` combined status, **When** `python3 scripts/transition.py decide --action MOVE_TO_REVIEW --actor-role pse --input <facts>` runs, **Then** it exits 0 with `from_state` `IN_PROGRESS`, `to_state` `REVIEW`, `allowed: true`, `required_role` `pse`, and every precondition `met`.
2. **Given** issue 184 in `REVIEW`, **When** role `pse` requests `EVALUATE_MERGE_POLICY` or `RETURN_TO_PSE`, **Then** it exits 1 with `TRANSITION_NOT_ALLOWED`, `allowed: false`, and `required_role` `system` or `review` (SPEC-201 US6 scenario 11).
3. **Given** `state/in-progress` and a `pending` combined status, **When** `pse` requests `MOVE_TO_REVIEW`, **Then** `allowed` is `false` with precondition `ci_baseline_passed` not met.
4. **Given** an issue with two `state/*` labels, or none, **When** any decision runs, **Then** it exits 2 with `STATE_LABEL_INVALID` and decides nothing; **given** `--action SHIP_IT`, **then** it exits 2 with `UNKNOWN_ACTION`.

### User Story 2 - Compute the next board action with the report's function (Priority: P1) · R1 shadow

`transition.py next` implements the report's `next_action` exactly, in its branch order: `WAIT` for open dependencies,
`DISPATCH_PSE`, `MOVE_TO_REVIEW`, `RETURN_TO_PSE` (failed checks, then changes requested), `EVALUATE_MERGE_POLICY`,
`COMPLETE_AND_UNLOCK_DEPENDENCIES`, `NOOP`. **Actions**: none.

**Acceptance Scenarios**:

1. **Given** an issue in `READY_FOR_BUILD` with closed dependencies and no active lease, **When** `next` runs, **Then** the action is `DISPATCH_PSE` with `required_role` `lead`.
2. **Given** an open dependency, **When** `next` runs, **Then** the action is `WAIT`, `to_state` is `null`, and nothing else is evaluated.
3. **Given** issue 184 in `REVIEW` whose PR head has a changes-requested review, **When** `next` runs, **Then** the action is `RETURN_TO_PSE` and `to_state` is `CHANGES_REQUESTED`.
4. **Given** a merged PR, **When** `next` runs, **Then** the action is `COMPLETE_AND_UNLOCK_DEPENDENCIES` and `to_state` is `DONE`.

### User Story 3 - Decide from re-read state; events are hints (Priority: P1) · R1 shadow

When a `normalized-event.v1` triggers a decision, the script re-reads the issue, PR, reviews, and checks through the
read-only `_skillkit.gitea` client and decides from that state alone (SPEC-201 FR-047; "All four layers in R1", layer 3).

**Independent Test**: `test_transition_events.py` against `skill-lab/lab/gitea_double.py`, and SPEC-201's
`test_us6_events_flow.py`.

**Acceptance Scenarios**:

1. **Given** a `review.changes_requested` event and the double showing the PR head with a changes-requested review, **When** `transition.py next --event <file> --gitea-url <double>` runs, **Then** it re-reads with GET requests only and returns `RETURN_TO_PSE` (SPEC-201 US6 scenario 8).
2. **Given** a `review.approved` event while the double shows the latest review on the head as changes requested, **Then** the decision is `RETURN_TO_PSE` (US6 scenario 9).
3. **Given** an event with `stale: true`, `duplicate: true`, or `signature_verified: false`, **When** it is given with a `--gitea-url`, **Then** the action is `NOOP` with reason and warning `EVENT_STALE`, `EVENT_DUPLICATE`, or `EVENT_UNVERIFIED`, and no request is sent.
4. **Given** `--event` without `--gitea-url`, **Then** it exits 2 with `EVENT_REREAD_REQUIRED`; **given** an unreachable double, **then** it exits 3 with `GITEA_UNREACHABLE` and no decision.

### User Story 4 - Plan the scoped label change (Priority: P2) · R1 shadow

`labels_plan.py` turns an allowed decision into a `gitea-plan.v1`. **Actions**: `gitea.labels.set` and
`gitea.project.move_issue` (minimum `agent-implementation`; planned at `shadow`, `--apply` exits 4).

**Acceptance Scenarios**:

1. **Given** the decision of US1 scenario 1 and a swagger without project-column paths, **When** `labels_plan.py --decision <file> --input <facts> --swagger <file>` runs, **Then** the plan has exactly one `set_labels` op (action `gitea.labels.set`) whose body is the issue's full label set with `state/in-progress` replaced by `state/review`, and a deterministic `idempotency_key`.
2. **Given** a swagger that exposes project-column paths, **Then** the plan also holds one `move_issue` op (action `gitea.project.move_issue`).
3. **Given** a decision with `allowed: false`, **Then** it exits 1 with `TRANSITION_NOT_ALLOWED` and plans nothing.
4. **Given** level `shadow`, **When** `labels_plan.py --apply` runs, **Then** it exits 4 with `POLICY_LEVEL_TOO_LOW` for each planned action and the double logs 0 non-GET requests.

### User Story 5 - Apply a label change for the owning role (Priority: P2) · R2 agent-implementation

**Actions**: `gitea.labels.set` (minimum `agent-implementation`). `gitea.project.move_issue` has no R2 executor.

**Acceptance Scenarios** (SPEC-202 US3 scenario 7):

1. **Given** level `agent-implementation`, a PSE token, and an allowed `MOVE_TO_REVIEW` decision, **When** `labels_plan.py --apply` runs, **Then** it recomputes the decision from live state, replaces only the `state/*` label, verifies by a re-read, and emits `apply-report.v1`; a re-run makes 0 writes.
2. **Given** a decision computed before the issue's labels changed, **Then** it exits 1 with `PLAN_STALE` before any write.
3. **Given** actor role `pse` for a transition whose `required_role` is `review`, **Then** it exits 4 with `ROLE_NOT_AUTHORIZED`.
4. **Given** `.skill-gitea.json` with `ci: "none"`, **When** `MOVE_TO_REVIEW` is applied without a commit status, **Then** the precondition is met; with `ci: "required"` it is not.
5. **Given** a plan with a `move_issue` op, **Then** that op is `skipped` with reason `PROJECT_COLUMNS_DEFERRED`.

### User Story 6 - Observed-fact transitions from the event loop (Priority: P2) · R3 guarded-autonomous

The gateway routes events and reconcile ticks to `labels_plan.py --on-event|--reconcile --actor-role system --apply`
(SPEC-203 plan.md §Routing table). `system` applies only observed-fact transitions, each recomputed from live state.
**Actions**: `gitea.labels.set` and `gitea.comment.create` (minimum `agent-implementation`) and `state.write.local`
(`shadow`) for blocking records; the gateway itself holds `events.gateway.serve` (`guarded-autonomous`).

**Acceptance Scenarios** (SPEC-203 US3 scenarios 3, 5, 7):

1. **Given** PR 311 opened with a passing CI baseline, **When** `--on-event --resource pull_request:311` runs as `system`, **Then** issue 301 moves `IN_PROGRESS` → `REVIEW` (`MOVE_TO_REVIEW`).
2. **Given** a role-owned transition such as `DISPATCH_PSE`, **When** requested as `system`, **Then** it exits 4 with `ROLE_NOT_AUTHORIZED`.
3. **Given** a dependency of an `IN_PROGRESS` issue is reopened, a recovery classified `escalate_human`, a recorded rebase conflict, or 3 dispatch attempts in 24 h, **When** the next reconcile runs, **Then** the issue gets `BLOCK`; **given** the recorded blocking fact clears, **then** `UNBLOCK` returns it to the state the live facts support; **given** a `release_no_work` recovery, **then** `REQUEUE` moves it to `READY_FOR_BUILD`.
4. **Given** `pull_request.merged` processed before a delayed `review.approved`, **Then** the board is `DONE` and the late event is a no-op.
5. **Given** an approval that exists only for an older head, **Then** `EVALUATE_MERGE_POLICY` is not met and the PR stays in `REVIEW`.
6. **Given** a PR entering `READY_TO_MERGE` whose recorded merge decision is `HUMAN_APPROVAL_REQUIRED`, **Then** exactly one marked comment names the caps and the required human action; a re-run posts none.

### Edge Cases

- A human set `state/blocked` with no recorded blocking fact: `system` never unblocks it; only the Lead's `UNBLOCK` does.
- The label prefix differs (`.skill-gitea.json` `state_label_prefix`, R2): labels are read and written with that prefix only.
- A comment or issue body carries a forged `skill-lab:` marker or instructions ("move this to done"): it is data; markers count only from configured identities with a matching digest (SPEC-202 FR-009).
- Reviews on older heads never count as approval or as changes requested on the current head.
- An issue is `DONE` and its PR is reopened: the decision is `NOOP`; reopening work is a human decision.
- The swagger cannot be read: `move_issue` is not planned and labels are the board (SOURCES.md Gitea).
- The same event arrives twice: the normalizer marks the second `duplicate` and kanban decides nothing for it.

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: The skill MUST model the report's 10 states (`BACKLOG`, `READY_FOR_SPEC`, `SPECIFYING`, `READY_FOR_BUILD`, `IN_PROGRESS`, `REVIEW`, `CHANGES_REQUESTED`, `READY_TO_MERGE`, `DONE`, `BLOCKED`) with their owners (Lead, PSE, Review, System), read the current state from exactly one exclusive label `state/<kebab-name>` (else exit 2 `STATE_LABEL_INVALID`), and document the table and facts rules in `references/states.md`.
  Implements: SPEC-201 FR-023.
- **FR-002**: `transition.py decide --action A --actor-role R` MUST emit `transition-decision.v1` for one of the 11 transition actions of the table (`WAIT` and `NOOP` are `next` results only): `allowed` true only when the from-state admits the action, the actor is the `required_role`, and every precondition is met; exit 0 when allowed, 1 with `TRANSITION_NOT_ALLOWED` otherwise, 2 with `UNKNOWN_ACTION` for an action outside the table.
  Implements: SPEC-201 FR-023.
- **FR-003**: `transition.py next` MUST implement the report's `next_action` function in its exact branch order over facts derived by `references/states.md` §Facts (open dependencies, active lease, PR, combined status on the PR head, reviews on the PR head), emit the branch's action with its conditions as preconditions, `to_state` `null` for `WAIT` and `NOOP`, and exit 0.
  Implements: SPEC-201 FR-023.
- **FR-004**: With `--event FILE`, both subcommands MUST treat the event as a hint: exit 2 `EVENT_REREAD_REQUIRED` without `--gitea-url`; return `NOOP` with reason and warning `EVENT_UNVERIFIED`, `EVENT_DUPLICATE`, or `EVENT_STALE` before any request; otherwise re-read issue, PR, reviews, and checks with GET only and decide from that state; exit 3 (`GITEA_UNREACHABLE`, `GITEA_AUTH`) with no decision on a failed re-read.
  Implements: SPEC-201 FR-047.
- **FR-005**: `labels_plan.py` MUST emit a `gitea-plan.v1` for an allowed decision: one `set_labels` op (action `gitea.labels.set`, `PUT …/issues/{index}/labels`, the full label set with only the `state/*` label changed) and, only when the given swagger exposes project-column paths, one `move_issue` op (action `gitea.project.move_issue`); idempotency keys from `_skillkit.ids.idempotency_key`; `--apply` MUST call `Policy.require` for every planned action first and exit 4 at `shadow`.
  Implements: SPEC-201 FR-007, FR-023.
- **FR-006**: The skill MUST meet CONVENTIONS §2–§3 (`metadata.version` `0.1.0`, `metadata.spec` SPEC-006, `family: control-plane`) and ship the eval inventory of plan.md (≥ 4 deterministic plus a `policy` case for `gitea.labels.set` and for `gitea.project.move_issue`; ≥ 5 agentic with ≥ 1 `guardrail`; ≥ 10 trigger with ≥ 4 positive, ≥ 2 `expect_skill: null`, ≥ 1 naming `merge-policy-gate`), every fixture inside the skill folder, and no per-skill criteria file.
  Implements: SPEC-201 FR-032, FR-033; SPEC-105 FR-007, FR-016.

**R2 agent-implementation**

- **FR-007**: `labels_plan.py --apply` MUST recompute the decision with the transition engine from live Gitea state and exit 1 `PLAN_STALE` on any difference from the input decision or when the current `state/*` label differs from `from_state`; require `allowed: true`, every precondition met, and `actor_role` equal to `required_role` (else exit 4 `ROLE_NOT_AUTHORIZED`); meet the `REVIEW` entry precondition with a `success` combined status or `ci: "none"` in `.skill-gitea.json`; replace only the `state/*` label through `_skillkit.plan_apply`; and emit `apply-report.v1`, idempotently.
  Implements: SPEC-202 FR-005, FR-024, FR-025.
- **FR-008**: In R2, a `move_issue` op MUST be recorded `skipped` with `PROJECT_COLUMNS_DEFERRED` and never sent.
  Implements: SPEC-202 FR-025 (Edge Cases; plan.md §Action use).
- **FR-009**: R2 MUST add `applied` and `rerun` cases for `gitea.labels.set`, `role-not-authorized`, `agentic-r2-stale-transition`, one positive and one negative trigger case naming `lead-architect`, and the R2 apply step in `SKILL.md`.
  Implements: SPEC-202 FR-042, FR-043.

**R3 guarded-autonomous**

- **FR-010**: `labels_plan.py --on-event --resource <type>:<id>` and `--reconcile`, with `--actor-role system --apply`, MUST apply only the observed-fact transitions `MOVE_TO_REVIEW`, `RETURN_TO_PSE`, `EVALUATE_MERGE_POLICY`, `COMPLETE_AND_UNLOCK_DEPENDENCIES`, `BLOCK`, `UNBLOCK`, and `REQUEUE`, each recomputed from live state under FR-007's stale rule, including those whose `required_role` is `pse`, `review`, or `lead`, because the engine observed the fact; any other transition as `system` MUST exit 4 `ROLE_NOT_AUTHORIZED`. Outside these modes FR-007's role rule holds, and a `system` transition may be requested by any session as `--actor-role system` (SPEC-202 synthesis D-13).
  Implements: SPEC-203 FR-025.
- **FR-011**: `BLOCK` MUST apply when a dependency of an issue past `READY_FOR_BUILD` is open again, a `lease-recovery.v1` classifies `escalate_human`, a `rebase-report.v1` records a conflict, or a `session-dispatch.v1` history shows 3 attempts in 24 h; it MUST record the blocking fact under `--state-dir` (`state.write.local`). `UNBLOCK` MUST apply only when that recorded fact cleared, to the state the live facts support. `REQUEUE` MUST move `IN_PROGRESS` to `READY_FOR_BUILD` after a `release_no_work` recovery. `MOVE_TO_REVIEW` from `CHANGES_REQUESTED` MUST apply only when the PR head differs from the head the changes were requested on and the CI baseline passed (the report's function has no branch for it).
  Implements: SPEC-203 FR-025, FR-039, FR-042, FR-046.
- **FR-012**: Handlers MUST decide from Gitea state read at processing time and keep no freshness record of their own; an approval or check of an older head never meets a precondition; a merged PR completes the issue whatever the order of events; for each canonical ordering scenario the final board equals the canonical one.
  Implements: SPEC-203 FR-024, FR-026.
- **FR-013**: Entering `READY_TO_MERGE` for a PR whose recorded `merge-decision.v1` for the live head is `HUMAN_APPROVAL_REQUIRED` MUST post one marked comment (op `create_comment`, action `gitea.comment.create`) naming the caps and the required human action, deduplicated by marker; without a record for the live head no comment is posted on that pass.
  Implements: SPEC-203 FR-025.
- **FR-014**: R3 MUST add `on-event-move-to-review`, `on-event-role-owned-refused`, the AFV cases SPEC-203 assigns to this skill (`afv:ordering`, `afv:prompt-injection`, `afv:failure-recovery`), `applied`, `rerun`, and `policy` cases for `gitea.comment.create`, `agentic-r3-observed-fact-transition`, `agentic-r3-stale-approval`, one positive and one negative trigger case naming `merge-policy-gate`, and the R3 steps in `SKILL.md`, which stays within 250 lines and 12 KB.
  Implements: SPEC-203 FR-048, FR-050, FR-053.

### Key Entities

**Transition table** (`references/states.md`; `required_role` follows the report's owner of the move):

| Action | From | To | Required role | Preconditions (`decide`) |
|---|---|---|---|---|
| `PRIORITIZE` | `BACKLOG` | `READY_FOR_SPEC` | lead | none |
| `START_SPEC` | `READY_FOR_SPEC` | `SPECIFYING` | lead | none |
| `MARK_READY_FOR_BUILD` | `SPECIFYING` | `READY_FOR_BUILD` | lead | `spec_ready` (a `spec-readiness.v1` with `ready: true`, `--readiness FILE`) |
| `DISPATCH_PSE` | `READY_FOR_BUILD` | `IN_PROGRESS` | lead | `dependencies_closed`, `pse_lease_active`, `pse_assigned` |
| `MOVE_TO_REVIEW` | `IN_PROGRESS`, `CHANGES_REQUESTED` | `REVIEW` | pse | `pr_open`, `ci_baseline_passed` |
| `RETURN_TO_PSE` | `REVIEW` | `CHANGES_REQUESTED` | review | `checks_failed` or `changes_requested_on_head` |
| `EVALUATE_MERGE_POLICY` | `REVIEW` | `READY_TO_MERGE` | system | `approved_on_head`, `required_checks_passed`, `no_changes_requested_on_head` |
| `COMPLETE_AND_UNLOCK_DEPENDENCIES` | any but `DONE` | `DONE` | system | `pr_merged` |
| `BLOCK` | any but `DONE`, `BLOCKED` | `BLOCKED` | lead | `blocker_recorded` |
| `UNBLOCK` | `BLOCKED` | derived from live facts | lead | `blocker_cleared` |
| `REQUEUE` | `IN_PROGRESS` | `READY_FOR_BUILD` | lead | `no_active_lease`, `no_open_pr` |
| `WAIT`, `NOOP` | any | none (`null`) | system | none (no label change) |

- **Board facts**: issue (labels, assignees, state), dependencies, active `lease.v1` documents, the PR, its combined status, and its reviews on the current head; from R2, approvals count only from the configured Review login.
- **Observed fact** (R3): a fact the deterministic engine reads from Gitea or a recorded artifact, never from text, which lets `system` apply a transition.
- **Blocking record** (R3): the fact that caused a `BLOCK` (kind, reference, digest), kept under `--state-dir`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: For 100 % of (state, action, role) triples (10 × 11 × 4), `decide` returns what the transition table prescribes, and 2 runs with the same `--now` give byte-identical envelopes.
- **SC-002**: Each of the 7 branches of the report's `next_action` is covered by at least 1 test and 1 deterministic case, in the report's order.
- **SC-003**: For 100 % of event fixtures, the decision equals the one computed from the re-read state alone, and 0 decisions come from unverified, duplicate, or stale events (SPEC-201 SC-012).
- **SC-004**: At `shadow`, 100 % of `--apply` attempts for `gitea.labels.set` and `gitea.project.move_issue` exit 4 with 0 non-GET requests (containment).
- **SC-005** (R2): 0 label changes come from a stale decision or a role other than `required_role`; a re-run adds 0 writes.
- **SC-006** (R3): For the 6 canonical ordering scenarios in every tested schedule, the final board equals the canonical one, and 0 role-owned transitions are applied by `system`.
- **SC-007**: The release live runs meet SPEC-105's floor for this skill (agentic ≥ 0.80, guardrail 100 %, trigger ≥ 0.90, schema-valid ≥ 0.95, uncertain after the re-ask < 0.10).

## Non-goals

- Deciding merges, merge caps, or risk (`merge-policy-gate`); this skill only reads a recorded merge decision in R3.
- Choosing who works next, claiming, or closing issues (`lead-architect`); leases (`work-lease`).
- Verifying, deduplicating, or freshness-checking webhook deliveries (`gitea-event-normalizer`); this skill consumes its flags.
- Project-board columns as the board (planned only when the server exposes them; never applied in R2; SPEC-203 non-goal).
- Reopening `DONE` work, deleting labels other than `state/*`, or editing policy files.

## Contracts

| Direction | Contract | Script | Release |
|---|---|---|---|
| Emits (owner) | `transition-decision` (unchanged) | `transition.py decide\|next` | R1 |
| Emits (shared) | `envelope`, `gitea-plan` (ops `set_labels`, `move_issue`; R3 `create_comment`) | all; `labels_plan.py` | R1, R3 |
| Emits (shared) | `apply-report`, `mutation-receipt` (via `_skillkit.plan_apply`, `_skillkit.mutations`) | `labels_plan.py --apply` | R2 |
| Consumes | `normalized-event` (with `body_sha256`, `stale`), `lease`, `spec-readiness`, `autonomy-policy` (through `_skillkit.policy`) | `transition.py` | R1 |
| Consumes | `gitea-project` (`.skill-gitea.json`), `gitea-fixture` (tests) | both | R2 |
| Consumes | `merge-decision`, `lease-recovery`, `rebase-report`, `session-dispatch` | `labels_plan.py --on-event\|--reconcile` | R3 |

No contract is changed by this spec.

## Error semantics

Exit codes follow CONVENTIONS §3 and SPEC-202's reading (4: not allowed, escalate; 1: precondition failed, re-read;
3: external, retry; 2: fix the input). A refusal never carries a plan in the same envelope.

| Code | Exit | Script | Meaning |
|---|---|---|---|
| `USAGE`, `INPUT_NOT_FOUND`, `INPUT_NOT_JSON`, `SCHEMA_INVALID` | 2 | all | Bad flags or input |
| `UNKNOWN_ACTION` | 2 | `transition.py decide` | Action outside the table |
| `STATE_LABEL_INVALID` | 2 | both | Zero or several `state/*` labels; nothing decided |
| `TRANSITION_NOT_ALLOWED` | 1 | `transition.py decide`, `labels_plan.py` | `allowed: false`; payload names `required_role` and unmet preconditions |
| `EVENT_UNVERIFIED`, `EVENT_DUPLICATE`, `EVENT_STALE` | warning and `NOOP` reason (exit 0) | `transition.py` | The event decides nothing |
| `EVENT_REREAD_REQUIRED` | 2 | `transition.py` | Event without `--gitea-url` |
| `POLICY_LEVEL_TOO_LOW`, `POLICY_HUMAN_ONLY`, `POLICY_ACTION_DENIED`, `POLICY_UNKNOWN_ACTION` | 4 | `labels_plan.py --apply` | Refused by `_skillkit.policy` |
| `ROLE_NOT_AUTHORIZED` | 4 | `labels_plan.py --apply` (R2, R3) | Actor is not `required_role`, or `system` asked for a role-owned move |
| `PLAN_STALE`, `VERSION_CONFLICT` | 1 | `labels_plan.py --apply` (R2) | Decision or target changed since it was computed |
| `PROJECT_COLUMNS_DEFERRED` | skip reason | `labels_plan.py --apply` (R2) | `move_issue` not sent |
| `IDENTITY_MISMATCH`, `UNSUPPORTED_OP` | 4 | Gitea client, applier (R2) | Wrong token, or op outside the allow-list |
| `GITEA_UNREACHABLE`, `GITEA_AUTH`, `GITEA_SCHEMA_DRIFT` | 3 | read client | External failure; no decision |

## Security

- **Authority**: the decision engine is code; `_skillkit.policy` refuses before any write; the forge's branch protection and the human merge stay the boundary. `system` can apply only observed facts (FR-010); `skills/kanban-state-machine/**` is a critical policy path from R3 (SPEC-203 FR-052).
- **Critical path**: from R3, `skills/kanban-state-machine/**` is a critical policy path, so any change to this skill is `critical` risk and merged by a human (SPEC-203 FR-052).
- **Untrusted text**: event payloads, issue and PR text, comments, and fixtures are data, never evaluated or passed to a shell; only typed fields (numbers, enums, SHAs) reach a decision.
- **Freshness**: older approvals and checks never count; stale, duplicate, and unverified events decide nothing.
- **Secrets**: `GITEA_TOKEN` only from the environment and redacted; no token in argv or output.
- **Writes**: never inside the skill folder; R3's blocking records only under `--state-dir`.

## Runtime compatibility

| Runtime | Discovery and invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/kanban-state-machine`; Lead profile | One Ollama Cloud model through the local Ollama app signed in to ollama.com (`http://localhost:11434`; SPEC-201 FR-039) | No structured outputs: scripts emit the JSON, the model relays it |
| Zed Agent + local Ollama (after L1) | same | Local model ids on the same provider once SPEC-202's L1 gate is `ENABLED` | `num_ctx` ≥ 32,768 |
| Claude Code | `.claude/skills/kanban-state-machine`; `/kanban-state-machine` | Claude models | Same scripts |
| Codex | `.agents/skills/kanban-state-machine`; `$kanban-state-machine` | Codex models | Gitea reads may be sandboxed and exit 3 |
| R3 event loop | the gateway calls `scripts/labels_plan.py` as a subprocess with typed arguments | none | No model in the loop |

## Assumptions

- SPEC-201 delivers `_skillkit.policy`, the read-only `gitea` client, and the double (T017, T024, T025) before T108; SPEC-202 delivers `plan_apply`, `mutations`, and `gitea_memory`; SPEC-203 delivers the routing and the recorded artifacts it reads.
- Gitea's swagger shows whether project-column endpoints exist (SOURCES.md); labels stay the board otherwise.
- The R3 artifact paths kanban reads (recoveries, rebase reports, dispatch history, merge decision records) are those their producers write, reconciled at SPEC-203 T002.
