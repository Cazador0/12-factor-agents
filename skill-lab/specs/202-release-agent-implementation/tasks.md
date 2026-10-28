---

description: "Task list for SPEC-202 R2 Agent implementation"
---

# Tasks: R2 Agent implementation

**Input**: Design documents from `/skill-lab/specs/202-release-agent-implementation/`

**Prerequisites**: plan.md (required), spec.md (required for user stories), synthesis.md, release-plan.md

**Tests**: Requested. The spec mandates tests-first. Every implementation task depends on a test task that must fail
first, for the right reason.

**Organization**: Tasks are grouped by user story, so each story can be implemented and tested independently. Paths
are relative to the repository root of `Cazador0/skill-factory` (`skills/`, `skill-lab/`, `AGENTS.md`). A path marked
† in plan.md is confirmed by the R1 alignment task before it is edited.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1..US6)
- Inline `(depends on T0NN, ...)` lists explicit prerequisites; phase order adds the rest
- `— FR-NNN` names the requirements a task implements or verifies
- **Verification** of a task = the test files and lab commands named in its description (SPEC-201 plan.md §Verification derivation). A "Write failing tests" task is a red-phase task: it is done when its tests run and fail with assertion failures, not import or syntax errors. R1's `dev_state.py mark` needs a passing check run, so the orchestrator works each red-phase task together with the implementation task that depends on it. It marks the red-phase task first and the implementation task second, both after the implementation's tests pass. This keeps the graph acyclic and the tests written first

## Path Conventions

- Shared library: `skill-lab/shared/_skillkit/` (canonical; vendored into `skills/*/scripts/_skillkit/` by `skill-lab sync`)
- Contracts: `skill-lab/contracts/schemas/`
- Lab: `skill-lab/lab/`; lab tests: `skill-lab/tests/`
- Skills: `skills/<name>/{scripts,assets,evals,tests}/`
- Evidence for this release: `skill-lab/specs/202-release-agent-implementation/evidence/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Verify entry criteria, verify external facts, and align with R1 as it was actually built

- [ ] T001 Record entry criteria E-1..E-5 (R1 APPROVE verdict URL, request ID and digest; `git ls-remote` proof that `release/r1-shadow` exists on `Cazador0/skill-factory` with the reviewed head; R1 `release check --stage merge` report digest with every offline and live gate `pass`; R1 and SPEC-105 interface inventory) in skill-lab/specs/202-release-agent-implementation/evidence/entry-check.json
- [ ] T002 Create branch `release/r2-agent-implementation` from the `release/r1-shadow` head in the skill-factory checkout (stacked PRs: R2 starts once R1 has its APPROVE and its live gates passed, E-1..E-3) and record the base commit in skill-lab/specs/202-release-agent-implementation/evidence/entry-check.json (depends on T001)
- [ ] T003 Verify Gitea facts V-1..V-3: vendor the Gitea v28.2.0 swagger into skill-lab/docs/research/vendor/gitea-28.2.0-swagger.v1.json, add a row in skill-lab/docs/research/vendor/README.md, and add the endpoint table, branch-protection field names, auto-close-on-merge behaviour and conditional-write support to skill-lab/docs/research/SOURCES.md; mark any fact without a reachable source as "unverified" — FR-004, FR-021 (depends on T001)
- [ ] T004 Verify runtime facts V-4..V-7 (`claude -p --json-schema` flags; that the local Ollama app signed in to ollama.com lists local model ids next to the `:cloud` ids under the one `ollama` provider at `http://localhost:11434` and that a Zed profile can pin either, verification only, because the person chose shape (a); Ollama over-length prompt behaviour and `/api/ps` fields; Codex sandbox network default for push) and record them in skill-lab/docs/research/SOURCES.md — FR-037, FR-038 (depends on T003)
- [ ] T005 Reconcile with SPEC-201 and SPEC-105 as built: module and CLI names of the lab files marked † in plan.md, plan op vocabulary of tasks_to_issues, comment_plan, labels_plan, review_verdict, checkpoint and lease plans, R1 seed fixture format, `check-run.v1` fields, marker grammar, `_skillkit.policy` API, and SPEC-105's `lab.streak`, `score --catalog`, `skill-lab report`, `release record-run` arguments, `run-monitor` `snapshot.py` options, `benchmark-run.v1` field and metric names, `prices.json` and `monitor-limits.json`; write skill-lab/specs/202-release-agent-implementation/evidence/r1-alignment.json — FR-001, FR-023, FR-036, FR-046 (depends on T001)
- [ ] T006 Dogfood readiness: run `python3 skills/lead-architect/scripts/spec_readiness.py --feature skill-lab/specs/202-release-agent-implementation` and `python3 skills/lead-architect/scripts/plan_dag.py --tasks skill-lab/specs/202-release-agent-implementation/tasks.md` and save skill-lab/specs/202-release-agent-implementation/evidence/readiness.json and skill-lab/specs/202-release-agent-implementation/evidence/task-graph.json (depends on T005)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Contracts, the raised clamp with base-branch verification, the single write path, the delivery executor, and the write-capable double

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Contracts (tests first)

- [ ] T007 Write failing contract tests with 1 valid and ≥ 2 invalid example documents per R2 contract in skill-lab/tests/test_contracts_r2.py and skill-lab/tests/fixtures/contracts/r2/ (depends on T005)
- [ ] T008 [P] Create skill-lab/contracts/schemas/mutation-receipt.v1.schema.json per spec.md §Contracts — FR-005 (depends on T007)
- [ ] T009 [P] Create skill-lab/contracts/schemas/apply-report.v1.schema.json — FR-023, FR-026 (depends on T007)
- [ ] T010 [P] Create skill-lab/contracts/schemas/gitea-project.v1.schema.json — FR-007 (depends on T007)
- [ ] T011 [P] Create skill-lab/contracts/schemas/gitea-fixture.v1.schema.json with the single declared `x_ext` object for raw branch-protection fields, mapping R1's seed format onto it — FR-008 (depends on T007)
- [ ] T012 [P] Create skill-lab/contracts/schemas/worktree-state.v1.schema.json — FR-011 (depends on T007)
- [ ] T013 [P] Create skill-lab/contracts/schemas/pr-request.v1.schema.json with body maxLength 60000 — FR-015, FR-033 (depends on T007)
- [ ] T014 [P] Create skill-lab/contracts/schemas/review-post.v1.schema.json — FR-017, FR-018 (depends on T007)
- [ ] T015 [P] Create skill-lab/contracts/schemas/branch-protection-audit.v1.schema.json — FR-021 (depends on T007)
- [ ] T016 [P] Create skill-lab/contracts/schemas/delivery-record.v1.schema.json with the 13 step ids — FR-030 (depends on T007)
- [ ] T017 [P] Create skill-lab/contracts/schemas/human-signoff.v1.schema.json with subject kinds `inference-enablement` and `autonomy-level-change` — FR-035 (depends on T007)
- [ ] T018 [P] Create skill-lab/contracts/schemas/inference-gate.v1.schema.json — FR-036 (depends on T007)
- [ ] T019 [P] Create skill-lab/contracts/schemas/smoke-report.v1.schema.json — FR-041 (depends on T007)
- [ ] T020 Apply the additive changes (optional `tree_clean`, `worktree` on check-run; `level` enum on containment-report) in skill-lab/contracts/schemas/check-run.v1.schema.json and skill-lab/contracts/schemas/containment-report.v1.schema.json — FR-008, FR-012 (depends on T007)
- [ ] T021 Add the 12 new contracts and 2 additive changes to the contract catalog in skill-lab/docs/CONVENTIONS.md §4 — FR-045 (depends on T008, T009, T010, T011, T012, T013, T014, T015, T016, T017, T018, T019, T020)

### Policy: raise the clamp safely (tests first)

- [ ] T022 Write failing tests for the generated 34-action × 3-level × 4-role matrix (19 allowed at agent-implementation, 7 refused, 5 human-only at every level) in skill-lab/tests/test_skillkit_policy_r2.py and the base-branch fixture set (wt above base, wt below base, missing base, invalid base, base under `agent/`, no origin) in skill-lab/tests/test_skillkit_policy_base.py — FR-001, FR-002, FR-003 (depends on T005)
- [ ] T023 Set `SUPPORTED_MAX_LEVEL = "agent-implementation"` and implement base-branch verification with warning `POLICY_NOT_ON_BASE` in skill-lab/shared/_skillkit/policy.py, without changing `ACTION_CATALOG`. Update SPEC-201's clamp expectations in skill-lab/tests/test_policy.py: a declared `guarded-autonomous` now clamps to `agent-implementation`. Record every changed R1 assertion in skill-lab/specs/202-release-agent-implementation/evidence/r1-test-updates.md for the reviewer — FR-001, FR-002, FR-003 (depends on T022, T010)

### Single write path (tests first)

- [ ] T024 Write failing tests for markers (render, parse, author trust, digest mismatch, two blocks) and the mutation ledger (atomic receipt, already_applied, crash between write and receipt, observed-state digest) in skill-lab/tests/test_skillkit_markers.py and skill-lab/tests/test_skillkit_mutations.py — FR-005, FR-009 (depends on T008)
- [ ] T025 Implement marker render and parse with configured-identity trust in skill-lab/shared/_skillkit/markers.py, keeping R1's verdict marker byte-identical — FR-009 (depends on T024)
- [ ] T026 Implement the idempotency ledger, `mutation-receipt.v1` writes under `fsutil.file_lock`, and `expected_version`/`expected_state_digest` helpers in skill-lab/shared/_skillkit/mutations.py — FR-005 (depends on T024, T025)
- [ ] T027 Write failing tests for the in-memory engine (every endpoint-table row, pagination, label replace, exclusive labels, dependencies, requested reviewers, reviews with self-approval refusal, combined status, fault injection, write log) in skill-lab/tests/test_skillkit_gitea_memory.py — FR-008 (depends on T011)
- [ ] T028 Implement the in-memory Gitea engine seeded from `gitea-fixture.v1` in skill-lab/shared/_skillkit/gitea_memory.py, following the verified endpoint table — FR-008 (depends on T027, T003)
- [ ] T029 Write failing tests for the hardened client (endpoint-table matching with allowed body keys, including the `lease.write.remote` comment row for op `mirror_lease`, `UNSUPPORTED_OP`, no merge row, no public generic request method, HTTPS-unless-loopback, identity check, host guard with sandbox exception, pagination, read retries with Retry-After, no blind write retry, error mapping, verify-after-write, `--gitea-fixture` transport) in skill-lab/tests/test_skillkit_gitea_r2.py — FR-004, FR-005, FR-006, FR-007, FR-041 (depends on T010, T028)
- [ ] T030 Extend `GiteaClient.send` and add the semantic write methods, identity check, host guard, and receipts in skill-lab/shared/_skillkit/gitea.py — FR-004, FR-005, FR-006, FR-007 (depends on T023, T026, T029)
- [ ] T031 Write failing tests for the shared plan applier (require-all-first, per-skill op allow-lists, `PLAN_STALE`, dedupe re-check before create, journaling, stop at first failure, `PROJECT_COLUMNS_DEFERRED` skip, `apply-report.v1`) in skill-lab/tests/test_skillkit_plan_apply.py — FR-023, FR-024 (depends on T009, T030)
- [ ] T032 Implement the shared `gitea-plan` applier in skill-lab/shared/_skillkit/plan_apply.py — FR-023, FR-024, FR-028 (depends on T031)

### Leases, git writes, checks, delivery (tests first)

- [ ] T033 Write failing tests for read-only lease verification (active, expired, other session, write-domain coverage) against R1's lease store format in skill-lab/tests/test_skillkit_leases.py — FR-010 (depends on T005)
- [ ] T034 Implement `verify(state_dir, issue, role, session_id, paths)` raising `LEASE_REQUIRED`, `LEASE_EXPIRED`, `LEASE_HELD_BY_OTHER` in skill-lab/shared/_skillkit/leases.py — FR-010 (depends on T033)
- [ ] T035 Write failing tests for git write helpers in temporary repositories (worktree_add, branch_create, commit with identity and trailers, push_branch exact refspec, force flags refused, credential URLs refused, non-fast-forward mapping, ls_remote verify, `show` for base-branch reads, allowlist still refusing every other subcommand) in skill-lab/tests/test_skillkit_gitrepo_r2.py — FR-011, FR-013, FR-014 (depends on T005)
- [ ] T036 Add the policy-guarded write helpers and read-only `show` to skill-lab/shared/_skillkit/gitrepo.py — FR-011, FR-013, FR-014 (depends on T035, T023)
- [ ] T037 Write failing tests for `tree_clean` and `worktree` in every check run in skill-lab/tests/test_skillkit_checks_r2.py — FR-012 (depends on T020)
- [ ] T038 Record `tree_clean` and `worktree` in check runs in skill-lab/shared/_skillkit/checks.py — FR-012 (depends on T037, T036)
- [ ] T039 Write failing tests for the delivery executor steps worktree (detached at the lease base), branch, commit, push, pr, review-request, review-session (lease, slug rule ≤ 40 chars, adopt or `WORKTREE_CONFLICT`, `SCOPE_VIOLATION`, `POLICY_PATH_TOUCHED`, `PROTECTED_BRANCH`, `NOTHING_TO_COMMIT`, `REMOTE_HOST_MISMATCH`, forge `github` writes `pr-request.v1` only, idempotent PR by head branch) in skill-lab/tests/test_skillkit_delivery.py — FR-010, FR-011, FR-013, FR-014, FR-015, FR-032, FR-033 (depends on T012, T013, T034, T036)
- [ ] T040 Implement the shared delivery executor with SPEC-201's step names in skill-lab/shared/_skillkit/delivery.py — FR-011, FR-013, FR-014, FR-015, FR-032, FR-033 (depends on T039, T030, T038)

### Test double, containment, fixtures

- [ ] T041 Write failing tests for the HTTP double (wraps the engine, write endpoints, JSONL write log, faults, bare remote creation, lab-only admin merge, 127.0.0.1 only) in skill-lab/tests/test_gitea_double_r2.py — FR-008 (depends on T028)
- [ ] T042 Refactor skill-lab/lab/gitea_double.py into an HTTP wrapper over the vendored engine with write endpoints and the admin merge, and register `gitea-double serve` in skill-lab/lab/cli.py. Update SPEC-201's skill-lab/tests/test_gitea_double.py so that 405 is expected only for requests outside the endpoint table, and record the change in skill-lab/specs/202-release-agent-implementation/evidence/r1-test-updates.md — FR-008 (depends on T041)
- [ ] T043 Extend the containment harness to `--level agent-implementation` (7 R3 and 5 human-only actions) with tests in skill-lab/tests/test_containment_r2.py and code in skill-lab/lab/containment.py — FR-003, FR-008 (depends on T042, T023)
- [ ] T044 Build the integration fixtures and harness (golden repo seed, committed `.skill-policy.json` at agent-implementation and `.skill-gitea.json` on main, per-role tokens, ephemeral double) in skill-lab/tests/integration/fixtures/r2-golden/gitea.json, skill-lab/tests/integration/fixtures/r2-golden/skill-gitea.json, skill-lab/tests/integration/fixtures/r2-golden/skill-policy.json and skill-lab/tests/integration/r2_harness.py (depends on T011, T010, T042)
- [ ] T045 [P] Create example configs skill-lab/config/gitea/skill-gitea.example.json and skill-lab/config/policy/skill-policy.agent-implementation.example.json (`set_by: "Cazador0"`, the person's GitHub username) — FR-007 (depends on T010, T023)
- [ ] T046 Vendor the new and extended `_skillkit` modules and schemas into every skill with `python3 skill-lab/bin/skill-lab sync`, confirm `sync --check` is clean, run SPEC-201's full suite (every R1 integration test must still pass at level `shadow`), and re-run the Constitution Check from plan.md into skill-lab/specs/202-release-agent-implementation/evidence/constitution-recheck.md (depends on T021, T023, T026, T030, T032, T034, T036, T038, T040)

**Checkpoint**: Foundation ready. User story phases can now proceed (US1 first as MVP; US2, US3 can follow in parallel on different skills)

---

## Phase 3: User Story 1 - PSE delivers a pull request from an isolated worktree under a lease (Priority: P1) 🎯 MVP

**Goal**: A leased PSE session creates its worktree and branch, commits within its write domains, pushes only its branch, and opens one PR whose evidence is backed by executed checks

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r2_us1_pse_delivery.py` on the double and bare remote: 1 PR from `agent/pse/<issue>-<slug>`, evidence bound to clean-tree check runs, no foreign ref changed

### Tests for User Story 1 ⚠️

> **NOTE: Write these tests FIRST, ensure they FAIL before implementation**

- [ ] T047 [P] [US1] Add deterministic cases tagged `applied` and `rerun` for the 6 pse-implementer actions (named per plan.md §Deterministic evals, including `worktree-applied.json` and `pr-create-rerun.json`), the `policy` refusal case `pr-update-refused-at-shadow.json` tagged `action:gitea.pr.update` (a pair R1 did not reference, FR-043), plus guardrail cases push-foreign-branch, push-force-flag, push-credential-url, push-remote-host-mismatch, commit-out-of-domain, commit-policy-path, with fixtures, in skills/pse-implementer/evals/cases/ and skills/pse-implementer/evals/fixtures/r2/ — FR-011, FR-013, FR-014, FR-015, FR-043 (depends on T046)
- [ ] T048 [P] [US1] Add 6 deterministic cases tagged `evidence` (`evidence-not-executed.json`, `evidence-log-digest-mismatch.json`, `evidence-different-commit.json`, `evidence-dirty-tree.json`, `evidence-status-mismatch.json`, `evidence-ac-without-evidence.json`) in skills/pse-implementer/evals/cases/ with fixtures in skills/pse-implementer/evals/fixtures/r2/evidence/ — FR-012 (depends on T046)
- [ ] T049 [P] [US1] Write failing tests for `delivery_plan.py --apply --step worktree|branch|commit|push|pr` (each step, `USAGE` without `--step`, `POLICY_LEVEL_TOO_LOW` at shadow, lease refusals) in skills/pse-implementer/tests/test_delivery_plan_apply.py — FR-010, FR-011 (depends on T046)
- [ ] T050 [P] [US1] Write failing tests for the 6 evidence integrity codes and the non-null head requirement in skills/pse-implementer/tests/test_evidence_integrity.py — FR-012 (depends on T046)
- [ ] T051 [P] [US1] Write failing tests and `applied`/`rerun`/`policy` cases for `checkpoint.py publish --apply` (marker, digest dedupe, redaction, PSE lease) in skills/session-checkpoint/tests/test_checkpoint_publish.py and skills/session-checkpoint/evals/cases/ (`publish-applied.json`, `publish-rerun.json`) — FR-016, FR-043 (depends on T046)

### Implementation for User Story 1

- [ ] T052 [US1] Implement `--apply --step worktree|branch|commit|push|pr` on top of `_skillkit.delivery` in skills/pse-implementer/scripts/delivery_plan.py — FR-010, FR-011, FR-013, FR-014, FR-015 (depends on T049, T040)
- [ ] T053 [US1] Implement the 6 integrity rules against `check-run.v1` in skills/pse-implementer/scripts/evidence_manifest.py — FR-012 (depends on T050, T038)
- [ ] T054 [US1] Create the PR body template (intent, acceptance criteria with statuses, checks table, marked evidence block, `Closes #<issue>`) and commit message template in skills/pse-implementer/assets/templates/pr-body.md and skills/pse-implementer/assets/templates/commit-message.txt — FR-013, FR-015 (depends on T052)
- [ ] T055 [US1] Implement `publish --apply` through the plan applier in skills/session-checkpoint/scripts/checkpoint.py — FR-016 (depends on T051, T032, T034)
- [ ] T056 [US1] Update skills/pse-implementer/SKILL.md with the R2 procedure (one command per step: worktree, branch, implement, commit, run_check, evidence validate, push, pr), behaviour per level, and runtime notes for Zed, Claude Code, and Codex within 250 lines and 12 KB — FR-042 (depends on T052, T053, T054)
- [ ] T057 [US1] Update skills/session-checkpoint/SKILL.md with the publish step and its lease rule — FR-042 (depends on T055)
- [ ] T058 [P] [US1] Add agentic cases agentic-r2-deliver-issue-pr and agentic-r2-injected-issue-body (tag `guardrail`) with Jev judgments, plus trigger cases trigger-r2-open-pr (positive) and trigger-r2-neg-deliver-feature (expects speckit-development) in skills/pse-implementer/evals/cases/ — FR-043 (depends on T056)
- [ ] T059 [P] [US1] Add agentic case agentic-r2-publish-handoff with a Jev judgment and trigger cases trigger-r2-save-progress (positive) and trigger-r2-neg-claim-issue (expects work-lease) in skills/session-checkpoint/evals/cases/ — FR-043 (depends on T057)
- [ ] T060 [US1] Write and pass integration test skill-lab/tests/integration/test_r2_us1_pse_delivery.py covering acceptance scenarios 1–9 of User Story 1, a re-run with 0 new writes, and `git for-each-ref` before and after on the bare remote — FR-009..FR-016 (depends on T044, T052, T053, T055)

**Checkpoint**: User Story 1 is fully functional and testable independently (MVP)

---

## Phase 4: User Story 2 - Review posts an independent verdict, and the merge stays human (Priority: P2)

**Goal**: Review posts verdicts to Gitea from its own identity after session, identity, and freshness checks; the merge gate audits branch protection and never auto-merges

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r2_us2_review_merge.py`: one APPROVED review with the verdict JSON, decision `HUMAN_APPROVAL_REQUIRED` with `uncapped_decision: AUTO_MERGE`, zero merge calls

### Tests for User Story 2 ⚠️

- [ ] T061 [P] [US2] Write failing tests for `review_verdict.py --comment-plan --post --apply` (event mapping, idempotency per PR, commit and verdict digest, identity rule, R1 session rule, `VERDICT_STALE`, `PR_NOT_OPEN`, `APPROVAL_WITHOUT_PASSING_GATE`, `review-post.v1`) in skills/review-verifier/tests/test_verdict_post.py — FR-017, FR-018, FR-019 (depends on T046)
- [ ] T062 [P] [US2] Add deterministic cases tagged `applied`/`rerun` for `gitea.pr.review.submit` and `gitea.comment.create` (`post-applied.json`, `post-rerun.json`, `comment-applied.json`, `comment-rerun.json`) and 5 cases tagged `independence` (`independence-author-login.json`, `independence-commit-author-login.json`, `independence-pse-login.json`, `independence-session-trailer.json`, `independence-reviewer-commits-outside-tests.json`) plus `post-stale-head.json` and `approval-without-gate.json` in skills/review-verifier/evals/cases/ with fixtures in skills/review-verifier/evals/fixtures/r2/ — FR-017, FR-018, FR-019, FR-043 (depends on T046)
- [ ] T063 [P] [US2] Write failing tests for the branch audit and its 12 fixtures (recommended policy, 10 single-field deviations, 1 unknown field) in skills/merge-policy-gate/tests/test_branch_audit.py and skills/merge-policy-gate/evals/fixtures/branch-protection/ — FR-021 (depends on T046)
- [ ] T064 [P] [US2] Write failing tests for the R2 merge decision (cap with `CAPPED_BY_AUTONOMY_LEVEL`, `BLOCKED` without review post or quality gate, a non-compliant audit adds reason `BRANCH_PROTECTION_NONCOMPLIANT`, is not listed in `gates[]`, and the decision stays `HUMAN_APPROVAL_REQUIRED`; every emitted decision validates against merge-decision.v1; `merge_plan.py --apply` still exit 4) in skills/merge-policy-gate/tests/test_merge_decision_r2.py — FR-020, FR-022 (depends on T046)
- [ ] T065 [P] [US2] Add deterministic cases tagged `branch-audit` (12, including `branch-audit-recommended.json`) and `cap-low-risk.json`, `blocked-missing-review.json`, `merge-plan-refused.json` in skills/merge-policy-gate/evals/cases/ — FR-020, FR-021, FR-022 (depends on T046)

### Implementation for User Story 2

- [ ] T066 [US2] Implement `--comment-plan --post --apply` with the identity rule, freshness check, and plan-applier execution in skills/review-verifier/scripts/review_verdict.py — FR-017, FR-018, FR-019 (depends on T061, T032)
- [ ] T067 [US2] Create skills/merge-policy-gate/assets/branch-policy-map.json mapping BP-01..BP-12 to the Gitea fields verified in SOURCES.md, with `map_version` and per-rule `required` — FR-021 (depends on T003, T063)
- [ ] T068 [US2] Implement skills/merge-policy-gate/scripts/branch_audit.py emitting `branch-protection-audit.v1` with `unknown` never passing and BP-10 as a self-audit of the vendored endpoint table — FR-021 (depends on T063, T067, T030)
- [ ] T069 [US2] Extend skills/merge-policy-gate/scripts/merge_decision.py to consume `review-post.v1`, `quality-gate.v1`, and `branch-protection-audit.v1` as gates under the R2 cap, and add `.skill-gitea.json` to the critical-path list — FR-020, FR-022 (depends on T064, T068, T066)
- [ ] T070 [US2] Update skills/review-verifier/SKILL.md (post step, independence rules, Review-identity requirement) and skills/merge-policy-gate/SKILL.md (audit step, cap) within budgets — FR-042 (depends on T066, T069)
- [ ] T071 [P] [US2] Add agentic cases agentic-r2-post-stale, agentic-r2-self-review-refusal (tag `guardrail`), agentic-r2-explain-cap with Jev judgments, and trigger cases trigger-r2-post-verdict, trigger-r2-neg-safe-to-merge, trigger-r2-audit-protection, trigger-r2-neg-review-pr in skills/review-verifier/evals/cases/ and skills/merge-policy-gate/evals/cases/ — FR-043 (depends on T070)
- [ ] T072 [US2] Write and pass integration test skill-lab/tests/integration/test_r2_us2_review_merge.py covering acceptance scenarios 1–7 of User Story 2 and asserting 0 merge calls in the double log — FR-017..FR-022 (depends on T060, T069)

**Checkpoint**: User Stories 1 and 2 both work independently

---

## Phase 5: User Story 3 - The Lead populates and drives the board idempotently (Priority: P2)

**Goal**: The Lead applies issues, dependencies, labels, milestones, assignment, leases, and transitions, with 0 duplicates on re-run or after a crash

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r2_us3_lead_board.py`, including the fault sweep k = 1..N

### Tests for User Story 3 ⚠️

- [ ] T073 [P] [US3] Write failing tests for `tasks_to_issues.py --apply` (create counts equal plan ops, re-run 0 writes, closed-issue dedupe, `PLAN_STALE`, `LABEL_NOT_EXCLUSIVE`, journaled map, fault at every op) in skills/speckit-gitea-taskstoissues/tests/test_tasks_to_issues_apply.py — FR-022, FR-023, FR-024 (depends on T046)
- [ ] T074 [P] [US3] Add deterministic cases tagged `applied`/`rerun` for the 6 taskstoissues actions, the `policy` refusal case `issue-update-refused-at-shadow.json` tagged `action:gitea.issue.update` (FR-043), plus `dedupe-closed.json`, `plan-stale.json`, `label-not-exclusive.json` in skills/speckit-gitea-taskstoissues/evals/cases/ with fixtures in skills/speckit-gitea-taskstoissues/evals/fixtures/r2/ — FR-023, FR-043 (depends on T046)
- [ ] T075 [P] [US3] Write failing tests and `applied`/`rerun`/`policy` cases for `comment_plan.py --apply` (create_comment only, marker dedupe, no spec or map edits) in skills/speckit-gitea-sync/tests/test_comment_plan_apply.py and skills/speckit-gitea-sync/evals/cases/ — FR-028, FR-043 (depends on T046)
- [ ] T076 [P] [US3] Write failing tests and cases for `labels_plan.py --apply` (recompute, `PLAN_STALE`, `ROLE_NOT_AUTHORIZED`, from-state check, CI precondition with `ci: none`, `PROJECT_COLUMNS_DEFERRED` skip) in skills/kanban-state-machine/tests/test_labels_plan_apply.py and skills/kanban-state-machine/evals/cases/ (including `role-not-authorized.json`) — FR-025, FR-043 (depends on T046)
- [ ] T077 [P] [US3] Write failing tests and cases for `lease.py --mirror --apply` (acquire, renew, release comments as op `mirror_lease`; foreign active mirror refusal) in skills/work-lease/tests/test_lease_mirror.py and skills/work-lease/evals/cases/ (`mirror-applied.json`, `mirror-rerun.json`) — FR-027, FR-043 (depends on T046)
- [ ] T078 [P] [US3] Write failing tests and cases for dispatch apply (claiming sequence, 4 precondition codes, idempotent resume), complete_issue (merged check, `state/done`, `CLOSE_PENDING`, unblocked list), and arbitrate publish in skills/lead-architect/tests/test_dispatch_apply.py, skills/lead-architect/tests/test_complete_issue.py, skills/lead-architect/tests/test_arbitrate_publish.py and skills/lead-architect/evals/cases/ (including `dispatch-applied.json`, `dispatch-rerun.json`, and the `policy` refusal case `labels-set-refused-at-shadow.json` tagged `action:gitea.labels.set`, a pair R1 did not reference, FR-043) — FR-026, FR-028, FR-029, FR-043 (depends on T046)

### Implementation for User Story 3

- [ ] T079 [US3] Implement `--apply` through the shared applier with the taskstoissues op allow-list and map journaling in skills/speckit-gitea-taskstoissues/scripts/tasks_to_issues.py — FR-022, FR-023, FR-024 (depends on T073, T074, T032)
- [ ] T080 [P] [US3] Implement `--apply` (op create_comment only) in skills/speckit-gitea-sync/scripts/comment_plan.py — FR-028 (depends on T075, T032)
- [ ] T081 [US3] Implement `--apply` with live recomputation via R1's transition engine in skills/kanban-state-machine/scripts/labels_plan.py — FR-025 (depends on T076, T032)
- [ ] T082 [US3] Implement `--mirror --apply` and foreign-mirror detection in skills/work-lease/scripts/lease.py — FR-027 (depends on T077, T032, T034)
- [ ] T083 [US3] Implement `--apply` following the claiming sequence (assign, local lease with base_commit and branch, IN_PROGRESS, mirror) in skills/lead-architect/scripts/dispatch_recommend.py — FR-026 (depends on T078, T081, T082)
- [ ] T084 [US3] Create skills/lead-architect/scripts/complete_issue.py (verify merged, set `state/done`, report `CLOSE_PENDING`, list unblocked issues) — FR-029 (depends on T078, T081)
- [ ] T085 [P] [US3] Implement `--publish --apply` through the applier in skills/lead-architect/scripts/arbitrate.py — FR-028 (depends on T078, T032)
- [ ] T086 [US3] Update skills/speckit-gitea-taskstoissues/SKILL.md and skills/speckit-gitea-sync/SKILL.md with the apply steps, resume rule, and behaviour per level — FR-042 (depends on T079, T080)
- [ ] T087 [US3] Update skills/kanban-state-machine/SKILL.md, skills/work-lease/SKILL.md, and skills/lead-architect/SKILL.md with the apply, mirror, dispatch, complete, and publish steps — FR-042 (depends on T081, T082, T083, T084, T085)
- [ ] T088 [P] [US3] Add agentic cases agentic-r2-resume-apply, agentic-r2-drift-comments, agentic-r2-stale-transition, agentic-r2-foreign-mirror (tag `guardrail`), agentic-r2-dispatch-choice with Jev judgments, and one positive plus one negative trigger case per skill in skills/speckit-gitea-taskstoissues/evals/cases/, skills/speckit-gitea-sync/evals/cases/, skills/kanban-state-machine/evals/cases/, skills/work-lease/evals/cases/ and skills/lead-architect/evals/cases/ — FR-043 (depends on T086, T087)
- [ ] T089 [US3] Write and pass integration test skill-lab/tests/integration/test_r2_us3_lead_board.py covering acceptance scenarios 1–9 of User Story 3, the fault sweep k = 1..N with 0 duplicates, and concurrent dispatch serialization — FR-022..FR-029 (depends on T044, T079, T080, T081, T082, T083, T084, T085)

**Checkpoint**: User Stories 1, 2, and 3 work independently

---

## Phase 6: User Story 4 - `/speckit-development` delivers a feature end to end (Priority: P3)

**Goal**: One command runs preflight through review request with each step a single tool call and resumable state

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r2_us4_golden_e2e.py skill-lab/tests/integration/test_r2_us4_resume.py`

### Tests for User Story 4 ⚠️

- [ ] T090 [P] [US4] Write failing tests for `delivery_record.py` (init, next, mark, the FR-030 step order with checks and evidence after commit, resume at first non-done step, `NOT_CONVERGED` after 3 passes, handoff) in skills/speckit-development/tests/test_delivery_record.py — FR-030, FR-031, FR-034 (depends on T046)
- [ ] T091 [P] [US4] Write failing tests for `delivery_plan.py --apply --step` worktree..pr (shared executor, forge `github` emits `pr-request.v1` with no network) and review-request, review-session (requests the Review login, writes the session dispatch from R1's rendered prompt, round limit) in skills/speckit-development/tests/test_delivery_plan_apply.py and skills/speckit-development/tests/test_delivery_review_steps.py — FR-030, FR-032, FR-033 (depends on T046)
- [ ] T092 [P] [US4] Add deterministic cases tagged `applied`/`rerun` for the 8 speckit-development actions (including `review-request-applied.json` and `review-request-rerun.json`), the `policy` refusal case `pr-update-refused-at-shadow.json` tagged `action:gitea.pr.update` (FR-043), plus `not-converged.json`, `forge-github-pr-request.json`, `rounds-exhausted.json`, `resume-after-push.json`, and `never-merges.json` in skills/speckit-development/evals/cases/ with fixtures in skills/speckit-development/evals/fixtures/r2/ — FR-030..FR-034, FR-043 (depends on T046)

### Implementation for User Story 4

- [ ] T093 [US4] Create skills/speckit-development/scripts/delivery_record.py (`init`, `status`, `next`, `mark`) emitting `delivery-record.v1` — FR-030, FR-031, FR-034 (depends on T090, T016)
- [ ] T094 [US4] Implement `--apply --step worktree|branch|commit|push|pr` on the shared executor, with forge `github` handling, and create skills/speckit-development/assets/templates/pr-body.md, in skills/speckit-development/scripts/delivery_plan.py — FR-030, FR-033 (depends on T091, T040)
- [ ] T095 [US4] Implement `--apply --step review-request` (`gitea.pr.review.request` for the Review login) and `--step review-session` (`review.session.request` dispatch file) and create skills/speckit-development/assets/templates/review-dispatch.md, in skills/speckit-development/scripts/delivery_plan.py — FR-032 (depends on T091, T094)
- [ ] T096 [US4] Update skills/speckit-development/SKILL.md with the 13-step R2 procedure (one command per step, resume rule, converge bound, no merge) and write the detail in skills/speckit-development/references/r2-delivery.md (≤ 300 lines, with TOC) — FR-030..FR-034, FR-042 (depends on T093, T094, T095)
- [ ] T097 [P] [US4] Add agentic cases agentic-r2-resume-delivery and agentic-r2-no-merge (tag `guardrail`) with Jev judgments, and trigger cases trigger-r2-deliver-feature (positive) and trigger-r2-neg-open-pr-only (expects pse-implementer) in skills/speckit-development/evals/cases/ — FR-043 (depends on T096)
- [ ] T098 [US4] Write and pass golden end-to-end test skill-lab/tests/integration/test_r2_us4_golden_e2e.py: tasks_to_issues apply, dispatch, delivery steps, review request, stub `claude` CLI through R1's review_local.py, verdict posted by the Review identity, merge decision `HUMAN_APPROVAL_REQUIRED`, admin-simulated human merge, complete_issue — FR-029..FR-034 (depends on T072, T089, T096)
- [ ] T099 [US4] Write and pass resume test skill-lab/tests/integration/test_r2_us4_resume.py interrupting after each of the 13 steps and resuming with 0 duplicate side effects — FR-030, FR-005 (depends on T098)

**Checkpoint**: The full R2 delivery loop works end to end on the double

---

## Phase 7: User Story 5 - Local inference is enabled only by a measured gate and the user's sign-off (Priority: P3)

**Goal**: The L1 mechanism (sign-off, gate evaluator, run metadata, local profiles, installer gate, doctor, fallback rule) exists and is correct offline

**Independent Test**: `python3 -m unittest skill-lab/tests/test_l1_gate.py skill-lab/tests/test_install_local_inference.py skill-lab/tests/test_bench_local_monitoring.py`, plus `skills/run-monitor/tests/test_snapshot_host_metrics_off.py` from the skill folder

### Tests for User Story 5 ⚠️

- [ ] T100 [P] [US5] Write failing tests for `signoff create|verify` (interactive confirmation required, non-TTY refusal, digest binding, tamper detection) in skill-lab/tests/test_signoff.py — FR-035 (depends on T017)
- [ ] T101 [P] [US5] Write failing tests and a ≥ 15-row fixture matrix of committed SPEC-105 run summaries (ENABLED; cloud streak shorter than 3; counting run failing a per-skill floor gate; counting run failing a catalog floor gate; unstable case; replay run neither extends nor breaks; partial run; outage run; degraded run; model change; suite digest change; SUITE_UNKNOWN; signoff missing; signoff reject; signoff digest mismatch; local failing; local num_ctx below 32768; local FORMAT_ENFORCED) in skill-lab/tests/test_l1_gate.py and skill-lab/tests/fixtures/l1/, asserting that the gate recomputes the streak with SPEC-105's `lab.streak` and ignores a stored streak file — FR-036 (depends on T018)
- [ ] T102 [P] [US5] Write failing tests for `install --runtime zed --inference local` (`LOCAL_INFERENCE_GATED` without a matching ENABLED record, cloud profiles kept, `--check` drift report) in skill-lab/tests/test_install_local_inference.py — FR-037, FR-039 (depends on T018)
- [ ] T103 [P] [US5] Write failing tests for `doctor --runtime ollama-local` against a fake server on 127.0.0.1 (unreachable, model missing, `NUM_CTX_TOO_SMALL`, GPU residency unknown) in skill-lab/tests/test_doctor_ollama_local.py — FR-038 (depends on T005)
- [ ] T104 [P] [US5] Write failing tests for the `ollama-local` cloud-parity mode (no `format` in requests, the same repair loop and `max_repairs` as `ollama-cloud`, `structured_output: "none"` recorded, `num_ctx` from config default 32768, no fallback to cloud on error, default `format` mode unchanged) in skill-lab/tests/test_runtime_ollama_local.py — FR-039, FR-040 (depends on T005)

### Implementation for User Story 5

- [ ] T105 [US5] Create skill-lab/lab/signoff.py and register `signoff create|verify` in skill-lab/lab/cli.py — FR-035 (depends on T100)
- [ ] T106 [US5] Create skill-lab/lab/l1_gate.py implementing the D-17 rules over SPEC-105's `lab.streak` (cloud entry `local_unlock_evidence`, sign-off by `Cazador0`, 3 counting local runs on the same suite digest passing the same floor gates) and register `gate l1` in skill-lab/lab/cli.py — FR-036 (depends on T101, T105)
- [ ] T107 [US5] Extend SPEC-201's `release record-run` so `ollama-local` runs are recorded with SPEC-105's `benchmark-run.v1` fields (`suite_digest`, `commit`, `counts_toward_streak`, `exclusion_reasons`, `degraded`) and per-result `num_ctx` exactly as cloud runs are, with no `notes[]` fallback, and reject a local run whose recorded num_ctx is below 32768 as L1-ineligible, in skill-lab/lab/record_run.py — FR-040 (depends on T104)
- [ ] T108 [US5] Add the cloud-parity mode to skill-lab/lab/runtimes/ollama_local.py (no `format`, reuse the `ollama-cloud` repair loop, `num_ctx` from config, an unreachable endpoint after retries gives an `errored` case with `OLLAMA_UNREACHABLE` and the run exclusion reason `outage`, no fallback) and make `skill-lab gate l1` treat `structured_output: "format"` runs as ineligible (`FORMAT_ENFORCED`) — FR-039, FR-040 (depends on T104, T004, T107)
- [ ] T109 [US5] Complete skill-lab/config/zed/local-ollama.disabled.jsonc with `Lead (local)`, `PSE (local)`, `Review (local)` profiles, `default_model {provider: "ollama", model}` placeholders for the user's model, and per-model `max_tokens: 32768`, using shape (a), the person's decision: every profile on provider `ollama` at `http://localhost:11434`, the cloud profiles keeping their `:cloud` model ids and the `(local)` profiles switching to local model ids on the same provider — FR-037 (depends on T004)
- [ ] T110 [US5] Gate `install --runtime zed --inference local` on a matching ENABLED `inference-gate.v1` (previewable with the existing `--dry-run`) and extend the existing `--check` to report inference drift in skill-lab/lab/install.py — FR-037, FR-039 (depends on T102, T106, T109)
- [ ] T111 [US5] Create skill-lab/lab/doctor.py with the `ollama-local` probes and register `doctor` in skill-lab/lab/cli.py — FR-038 (depends on T103, T108)
- [ ] T112 [P] [US5] Create skill-lab/benchmarks/signoff/README.md and skill-lab/benchmarks/gates/README.md (what lives there, who writes it, how to verify) — FR-035, FR-036 (depends on T105, T106)
- [ ] T113 [US5] Write the runbook skill-lab/docs/runbooks/local-inference-l1.md: gate steps (SPEC-105 `skill-lab streak` for the cloud entry, sign-off as `Cazador0`, 3 counting local runs), sample review, `num_ctx` 32768 guidance for GPUs under 24 GB (Zed default 4096, Ollama default 4k under 24 GiB, verify `ollama ps` shows 100 % GPU and context 32768), the runs inside the person's Rancher Desktop local container with `run-monitor` `snapshot.py --target local-container` reading only that container (no Docker or containerd socket), the local model decided at unlock time (list what fits the GPU at 32k context with tool support, verify it with `skill-lab doctor`, the person picks), fallback to the cloud profile, and demotion — FR-038, FR-039, FR-048 (depends on T106, T110, T111, T144)
- [ ] T114 [US5] Add the local-inference fallback rule (after 2 schema-invalid outputs or an unreachable endpoint: checkpoint, switch to the cloud profile) to AGENTS.md — FR-039 (depends on T113)
- [ ] T143 [P] [US5] Write failing tests in skill-lab/tests/test_bench_local_monitoring.py: on `--runtime ollama-local` bench runs `run-monitor` `snapshot.py --target local-container` after each skill as a child process (list arguments) in the same container, and `--target benchmark-container` on every other runtime; each local report has `target.kind: local-container`; with a fake cgroup v2 tree whose `memory.current` crosses the `monitor-limits.json` limit the run is `degraded` and does not count; no Docker or containerd socket and no path outside the container's own `/sys/fs/cgroup`, `/proc`, and working filesystem is opened; API and session figures still come from the run log, and the advisory assessment goes through the run's own runtime — FR-048 (depends on T005)
- [ ] T144 [US5] Pass `--target local-container` from skill-lab/lab/bench.py to `run-monitor` on `--runtime ollama-local` runs, and name the target and when bench uses it in one line of skills/run-monitor/SKILL.md; leave skills/run-monitor/scripts/snapshot.py (its `local-container` target ships with SPEC-105 in R1), skill-lab/benchmarks/monitor-limits.json, and the `run-health.v1` contract unchanged — FR-042, FR-048 (depends on T143)

**Checkpoint**: L1 can be evaluated honestly as soon as live runs exist, and local runs are monitored only from inside their own Rancher Desktop container

---

## Phase 8: User Story 6 - Live Gitea smoke test before the first live write (Priority: P4)

**Goal**: A staged smoke test on a sandbox repository proves the client against a real Gitea and unlocks live writes per host

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r2_us6_smoke_double.py`

### Tests for User Story 6 ⚠️

- [ ] T115 [P] [US6] Write failing tests for `smoke gitea` (`GITEA_NOT_CONFIGURED` with `not_run`, `SMOKE_REPO_NOT_SANDBOX`, missing swagger endpoint, stage identities, sandbox-only cleanup client, policy file required on the sandbox default branch) in skill-lab/tests/test_smoke_gitea.py — FR-041 (depends on T042, T019)

### Implementation for User Story 6

- [ ] T116 [US6] Create skill-lab/lab/smoke_gitea.py with the 4 stages and the sandbox-only cleanup client, register `smoke gitea` in skill-lab/lab/cli.py, and wire the client's host guard to read `.skill-state/smoke/<host>.json` — FR-041 (depends on T115, T030)
- [ ] T117 [US6] Write and pass integration test skill-lab/tests/integration/test_r2_us6_smoke_double.py with the double posing as a non-loopback host (writes refused before the smoke test, allowed after it) — FR-041 (depends on T116, T044)
- [ ] T118 [US6] Write the runbook skill-lab/docs/runbooks/live-gitea-smoke.md: bot accounts (Review separate), least-privilege token scopes to confirm, sandbox repository with committed `.skill-policy.json`, commands per stage with the per-role `GITEA_TOKEN`, reading the report, cleanup — FR-041 (depends on T116)

**Checkpoint**: All user stories are independently functional

---

## Phase 9: Polish & Cross-Cutting Concerns

**Purpose**: Decisions on record, conventions, configs, gates, release delivery steps 5–8

- [ ] T119 [P] Write skill-lab/docs/adr/0201-per-role-gitea-identities.md (D-3, D-11) in MADR form with a Compliance section naming the tests — FR-045
- [ ] T120 [P] Write skill-lab/docs/adr/0202-single-host-lease-authority-with-gitea-mirror.md (D-7) — FR-045
- [ ] T121 [P] Write skill-lab/docs/adr/0203-l1-local-inference-gate-and-human-signoff.md (D-16, D-17, D-18) — FR-045
- [ ] T122 [P] Write skill-lab/docs/adr/0204-skills-are-gitea-only-orchestrator-owns-github.md (D-4) — FR-045
- [ ] T123 [P] Write skill-lab/docs/adr/0205-optimistic-concurrency-and-idempotent-writes.md (D-5, D-6, D-14) — FR-045
- [ ] T124 [P] Write skill-lab/docs/adr/0206-live-gitea-smoke-before-first-live-write.md (D-19) — FR-045
- [ ] T125 [P] Write skill-lab/docs/adr/0207-base-branch-verification-of-autonomy-policy.md (D-21) — FR-045
- [ ] T126 Amend skill-lab/docs/CONVENTIONS.md §7 (R2 role permissions per profile) and §8 (base-branch verification, effective level = minimum) citing ADR-0201 and ADR-0207 — FR-045 (depends on T119, T120, T121, T122, T123, T124, T125)
- [ ] T127 Update runtime permission templates for R2 (allow the delivery scripts, confirm `--apply`, deny raw `git push`, `--force`, `--no-verify`, and edits to `.skill-policy.json`, `.skill-gitea.json`, `skill-lab/config/**`, `skill-lab/benchmarks/signoff/**`, `skill-lab/benchmarks/criteria/**`, and `skill-lab/benchmarks/monitor-limits.json`) in skill-lab/config/zed/settings.example.jsonc, skill-lab/config/claude/settings.example.json and skill-lab/config/codex/config.example.toml — FR-042, FR-044 (depends on T056, T070, T087, T096)
- [ ] T128 Add validator rule `eval-inventory-r2` in skill-lab/lab/validate_policy.py and the R2 config rules (deny patterns present, local file present and not installed, codex template) in skill-lab/lab/config_rules.py, with tests in skill-lab/tests/test_validate_r2.py — FR-043 (depends on T005)
- [ ] T129 Define every gate of spec.md §Release gates in skill-lab/specs/202-release-agent-implementation/gates.json (`release-gates.v1`): G-OFF-01..G-OFF-23 and G-LIVE-01..G-LIVE-07 at stage `merge` (the live gates with per-skill and catalog scopes and SPEC-105's floor, read from `evidence/live-runs.json`), G-POST-01..02 at stage `post-review`, and no gate at stage `complete`. Extend skill-lab/config/export/ci.yml with `policy containment --level agent-implementation`, the R2 integration tests, and the R2 export-manifest path (critical-risk path, named in the reviewer checklist), keeping the offline gates on every PR and the live tiers only in a manually started job — FR-045, FR-047, FR-049 (depends on T005)
- [ ] T130 Write and pass release-gate tests (AUTO_MERGE envelope scan, 0 merge calls, canary secret scan with one canary per `SECRET_ENV_VARS` name, coverage counts, ci.yml runs live tiers only on manual dispatch, the R2 review request carries the live run's summary digest and the no-keys instructions) in skill-lab/tests/release/test_r2_release_gates.py — FR-019, FR-043, FR-044, FR-049 (depends on T098, T099, T117, T129)
- [ ] T147 Write and pass live-gate evaluation tests in skill-lab/tests/release/test_r2_live_gates.py (a passing counting run; each floor gate failing per skill and catalog-wide; a guardrail miss; replay, partial, outage, and degraded runs; a stale suite digest gives `LIVE_RUN_STALE`; no run gives `NO_LIVE_RUN`; the newest matching run wins), and add `--spec SPEC-202` support to `release record-run` writing skill-lab/specs/202-release-agent-implementation/evidence/live-runs.json in skill-lab/lab/record_run.py — FR-046, FR-047 (depends on T107, T129)
- [ ] T131 Regenerate skill-lab/docs/autonomy.md from `policy.catalog_document()` so `supported_max_level` reads `agent-implementation` and the drift test passes — FR-045 (depends on T023)
- [ ] T132 Regenerate skills/CATALOG.json with `python3 skill-lab/bin/skill-lab catalog` and confirm the catalog of 14 skills is ≤ 51,200 bytes — FR-042 (depends on T056, T057, T070, T086, T087, T096, T127, T144)
- [ ] T133 Finalize skill-lab/specs/202-release-agent-implementation/traceability.json: replace planned paths with real ones, set `planned: false`, and pass `skill-lab validate --specs` — FR-045 (depends on T130, T132, T147)
- [ ] T134 Run `python3 skill-lab/bin/skill-lab release check --spec SPEC-202 --stage merge` and save skill-lab/specs/202-release-agent-implementation/evidence/release-gate-report-offline.json; every G-OFF gate must be `pass` (the live gates stay `not_run` until T135 records a run, and T145 checks the full stage) (depends on T128, T129, T131, T133)
- [ ] T135 Live gate run: if `OLLAMA_API_KEY` and `TYPESAFE_API_KEY` (or `JEV_API_KEY`) and network are present, run `skill-lab bench --tier agentic,trigger --runtime ollama-cloud --model <M1> --jev live` over every agentic and trigger case of all 14 skills, then `skill-lab score --strict` per skill and `--catalog`, and `skill-lab streak`; commit skill-lab/benchmarks/runs/<run_id>/ and record it by digest with `skill-lab release record-run --spec SPEC-202 --run <dir>` into skill-lab/specs/202-release-agent-implementation/evidence/live-runs.json. An outage or degraded run does not count and is re-run. Without keys or network, record `not_run` with the reason, never a pass, and the PR stays unmerged — FR-046 (depends on T134)
- [ ] T136 If `GITEA_URL` and per-role tokens are present, run the 4 smoke stages against the sandbox repository and save skill-lab/specs/202-release-agent-implementation/evidence/live-gitea-smoke.json; otherwise record `not_run` with the reason (depends on T134)
- [ ] T137 Run `python3 skills/speckit-development/scripts/converge.py --feature skill-lab/specs/202-release-agent-implementation --apply`; if findings remain, implement the appended Convergence tasks and re-run until 0 findings; save skill-lab/specs/202-release-agent-implementation/evidence/convergence-report.json (depends on T134)
- [ ] T145 Run `python3 skill-lab/bin/skill-lab release check --spec SPEC-202 --stage merge` with the recorded live run and save skill-lab/specs/202-release-agent-implementation/evidence/release-gate-report-merge.json; every G-OFF and G-LIVE gate must be `pass`, and a live gate that is `not_run` or `fail` keeps the release open — FR-047 (depends on T135, T137)
- [ ] T138 Self-check the release diff with merge-policy-gate (expect `risk_class: critical`, `HUMAN_APPROVAL_REQUIRED`) into skill-lab/specs/202-release-agent-implementation/evidence/merge-decision-self.json, render skill-lab/specs/202-release-agent-implementation/evidence/pr-body.md with pr_body.py, and write skill-lab/specs/202-release-agent-implementation/evidence/pr-request.json with `delivery_plan.py --step pr --forge github` (no `--apply`; the factory repository runs at `shadow`) (depends on T145)
- [ ] T139 Release PR: run `skill-lab/bin/export-repo --out <scratch>/skill-factory` and `--check` (manifest at skill-lab/specs/202-release-agent-implementation/evidence/export-manifest.json), commit on `release/r2-agent-implementation`, push, and have the orchestrator open the PR to base `release/r1-shadow` (stacked; retargeted to `main` when R1 merges, E-6) from skill-lab/specs/202-release-agent-implementation/evidence/pr-request.json (depends on T138)
- [ ] T146 Post the live scores on the R2 PR: render `skill-lab report --run skill-lab/benchmarks/runs/<run_id>` (per-skill and catalog results, unsure and flagged cases, unstable cases, tokens and cost basis, suite digest) and have the orchestrator post it as a PR comment — FR-046 (depends on T139)
- [ ] T140 Independent review: write `<scratch>/r2-post-review/review-request.json` with review_request.py (forge github, round 1, carrying the sha256 of the counting live run's summary; kept out of the release branch, because a commit after the reviewed head would make the verdict stale, SPEC-201 D-17); the orchestrator creates a separate Claude Code cloud session on the release branch whose environment holds none of `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, `JEV_API_KEY`; the session runs review-verifier against spec.md, re-runs `release check --stage merge` with the live gates read only from the committed run (it re-runs no live case and says so in its verdict), checks the critical-risk paths (policy.py clamp, permission templates, review gates, criteria and limits files) and posts a `review-verdict.v1` comment, then runs `run-monitor` `snapshot.py --target reviewer-session` and posts the `run-health.v1` report as a separate comment marked `<!-- skill-lab:run-health:v1 request_id=<id> -->`; fall back to review_local.py with `mode: cli-fallback` only if no cloud session can be created; collect the verdict and the health report with review_collect.py — FR-049 (depends on T146)
- [ ] T141 If the verdict is `CHANGES_REQUESTED`, fix through new Convergence tasks in skill-lab/specs/202-release-agent-implementation/tasks.md, push, and request the next round (at most 3 rounds; then the person decides). A fix that changes any SKILL.md or eval case changes the suite digest, so T135 and T145 run again before the next round — FR-049 (depends on T140)
- [ ] T142 Run `release check --stage post-review` into `<scratch>/r2-post-review/release-gate-report-post-review.json` (out of the branch, attached to the PR thread; SPEC-203 T001 copies it); once a human has merged R1, have the orchestrator retarget the R2 PR base to `main` (`gh pr edit --base main`, E-6); re-request review if the diff changed after the reviewed head, on retargeting or otherwise; hand the merge to the human, who merges R2 only after R1 (depends on T141)

---

## Milestone M-L1 (outside this task graph)

M-L1 (local inference enabled) is executed from skill-lab/docs/runbooks/local-inference-l1.md and release-plan.md §10
once live runs exist. It is deliberately **not** a phase of this tasks.md, for two reasons. Under SPEC-201's wave rule,
Polish depends on every user-story phase, so a user-story phase that waits on Polish would form a cycle. And its
artefacts (3 cloud runs, a human sign-off, 3 local runs) cannot exist at merge time, so converge would report them as
missing. Every FR it exercises (FR-035..FR-040, FR-048) is implemented and verified offline by Phase 7.

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: starts once R1 has its APPROVE verdict and its live gates passed (E-1..E-3), on a branch stacked on `release/r1-shadow`; R1's human merge gates only R2's merge (E-6, T142)
- **Foundational (Phase 2)**: depends on Setup; BLOCKS all user stories
- **US1 (Phase 3)**: after Foundational; the MVP
- **US2 (Phase 4)**: after Foundational for its unit work; its integration test needs US1's PR (T060)
- **US3 (Phase 5)**: after Foundational; independent of US1 and US2 except the shared fixtures
- **US4 (Phase 6)**: needs US1, US2 and US3 integration green (T072, T089)
- **US5 (Phase 7)**: after Foundational contracts; independent of US1–US4
- **US6 (Phase 8)**: after the double and client (T042, T030)
- **Polish (Phase 9)**: after all stories; from T134 on, the order is T134 → T135, T136, T137 → T145 → T138 → T139 → T146 → T140 → T141 → T142
- **M-L1**: outside this task graph (see above); starts after T135, whose run is the first of the R2-suite streak, and runs in parallel with R3, blocking neither the R2 merge nor R3 (synthesis Q-5, resolved)

### User Story Dependencies

- **US1 (P1)**: independent after Foundational
- **US2 (P2)**: unit tests independent; integration reuses the US1 PR fixture
- **US3 (P2)**: independent after Foundational
- **US4 (P3)**: integrates US1–US3
- **US5 (P3)**: independent (lab only)
- **US6 (P4)**: independent (lab plus client)

### Within Each User Story

- Tests and eval cases are written first and must fail
- Shared executor before skill scripts; scripts before SKILL.md; SKILL.md before agentic and trigger cases; integration test last

### Parallel Opportunities

- Contract schemas T008–T019 run in parallel after T007
- Test-writing tasks marked [P] inside each story run in parallel (different skill folders)
- US3, US5, and US6 can run in parallel with US1 and US2 once Foundational is done, on different files
- ADR tasks T119–T125 run in parallel

---

## Parallel Example: User Story 3

```bash
# Launch the US3 test tasks together (different skill folders):
Task: "Write failing tests for tasks_to_issues.py --apply in skills/speckit-gitea-taskstoissues/tests/test_tasks_to_issues_apply.py"
Task: "Write failing tests and cases for comment_plan.py --apply in skills/speckit-gitea-sync/tests/test_comment_plan_apply.py"
Task: "Write failing tests and cases for labels_plan.py --apply in skills/kanban-state-machine/tests/test_labels_plan_apply.py"
Task: "Write failing tests and cases for lease.py --mirror --apply in skills/work-lease/tests/test_lease_mirror.py"
```

---

## Implementation Strategy

### MVP First (User Story 1 Only)

1. Complete Phase 1: Setup (entry evidence, verification, R1 alignment)
2. Complete Phase 2: Foundational (critical; blocks all stories)
3. Complete Phase 3: User Story 1
4. **STOP and VALIDATE**: `test_r2_us1_pse_delivery.py` green on the double

### Incremental Delivery

1. Setup + Foundational → write path and delivery executor ready
2. US1 → PSE PR on the double (MVP)
3. US2 → independent review posted, merge stays human
4. US3 → Lead drives the board idempotently
5. US4 → `/speckit-development` end to end
6. US5 + US6 → L1 mechanism and live smoke test
7. Polish → gates, PR, independent review, human merge; M-L1 when live runs exist

---

## Notes

- [P] tasks = different files, no dependencies on incomplete tasks. This is Spec Kit's file-level definition. R1's `plan_dag.py` infers write domains per directory and may put [P] tasks that share a directory (for example the schemas, T008–T019) into separate waves; that is expected and safe
- Every task names the FRs it serves; traceability.json maps each FR to its implementing and verifying paths
- Live tasks (T135, T136, T145, T146) and the M-L1 procedure never fabricate results: without keys, network, or Gitea they record `not_run` with a reason, and a `not_run` live gate keeps the R2 PR unmerged
- No task in this release merges a PR, closes an issue, edits `.skill-policy.json` in a target project, edits a criteria file or `monitor-limits.json`, creates a Gitea webhook, or creates a sign-off on the person's behalf
