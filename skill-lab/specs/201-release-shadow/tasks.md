---

description: "Task list for SPEC-201 R1 Shadow mode"
---

# Tasks: R1 Shadow mode

**Input**: Design documents from `skill-lab/specs/201-release-shadow/` (spec.md, plan.md, synthesis.md, release-plan.md)

**Prerequisites**: plan.md (required), spec.md (required for user stories), foundation SPEC-100..104 (entry criterion E-1)

**Tests**: Requested. Every implementation task follows a task that writes its tests first, and those tests are seen to fail before implementation.

**Organization**: Tasks are grouped by user story (spec.md US1–US9) so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1–US9)
- Paths are relative to the repository root `/home/user/12-factor-agents`
- Dependency semantics follow plan.md §Wave rule: a task without `[P]` depends on the nearest preceding task in its phase; `(depends on …)` adds explicit edges
- **Verification** of a task = the test files and lab commands named in its description. From T054 on, `dev_state.py mark --task Tnnn --apply` requires a passing `check-run.v1` for each

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Entry check, release scaffolding, and the decisions on record

- [ ] T001 Run the foundation entry check (`skill-lab validate`, `sync --check`, `test`, `bench --tier deterministic`, `score`, `catalog`, `install --help`) and record exit codes in `skill-lab/specs/201-release-shadow/evidence/entry-check.json`; record the real names of the lab CLI registry, validator hook, installer, bench flags, and SPEC-104 metric names in `skill-lab/specs/201-release-shadow/evidence/interface-notes.md` (plan.md §Interface alignment)
- [ ] T002 [P] Create the reviewer-owned requirements checklist `skill-lab/specs/201-release-shadow/checklists/requirements.md` from the Spec Kit checklist template, covering completeness, testability, gate rationale, and contract field lists of `spec.md` (depends on T001)
- [ ] T003 [P] Write ADR-0101 "Autonomy policy file and fail-safe loading" in `skill-lab/docs/adr/0101-autonomy-policy-file.md` (MADR; Compliance: `test_policy.py`, G-OFF-07) (depends on T001)
- [ ] T004 [P] Write ADR-0102 "Action catalog and minimum levels" in `skill-lab/docs/adr/0102-action-catalog.md` (34 ids, `human-only`, catalog is a critical path) (depends on T001)
- [ ] T005 [P] Write ADR-0103 "Cloud-first inference with gated local enablement" in `skill-lab/docs/adr/0103-cloud-first-inference.md` (D-14, D-15; Compliance: G-OFF-09, `LOCAL_INFERENCE_GATED`) (depends on T001)
- [ ] T006 [P] Write ADR-0104 "Independent review loop" in `skill-lab/docs/adr/0104-independent-review-loop.md` (review-request.v1, comment marker, session-id and trailer independence, ≤ 3 rounds, `claude -p` fallback) (depends on T001)
- [ ] T007 [P] Write ADR-0105 "Standalone export to Cazador0/skill-factory" in `skill-lab/docs/adr/0105-standalone-export.md` (layout, LICENSE, NOTICE, manifest, no git operations) (depends on T001)
- [ ] T008 Amend `skill-lab/docs/CONVENTIONS.md` §4 (add the 21 new contract rows and the 5 additive changes) and §8 (clamp, `refusals`, catalog, `human-only`), citing ADR-0101..0105; write `skill-lab/tests/test_adrs_r1.py` (MADR sections present in ADR-0101..0105; CONVENTIONS cites each) and verify with `skill-lab validate` (ADR references hold) (depends on T003, T004, T005, T006, T007)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Contracts, the policy core, shared modules, the read-only Gitea double, and the lab commands every story uses

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Contracts (tests first)

- [ ] T009 Write failing contract tests `skill-lab/tests/test_contracts_r1.py` with one valid and ≥ 2 invalid example per new or changed contract under `skill-lab/tests/fixtures/contracts/r1/` (spec.md §Contracts), including a subset-keyword check against `jsonschema_mini`
- [ ] T010 [P] Write schemas `skill-lab/contracts/schemas/autonomy-policy.v1.schema.json`, `action-catalog.v1.schema.json`, `policy-state.v1.schema.json`, `mutation-plan.v1.schema.json` (depends on T009)
- [ ] T011 [P] Write schemas `skill-lab/contracts/schemas/check-run.v1.schema.json`, `rendered-document.v1.schema.json`, `requirements-matrix.v1.schema.json`, `development-report.v1.schema.json`, `convergence-report.v1.schema.json`, `review-request.v1.schema.json` (depends on T009)
- [ ] T012 [P] Write schemas `skill-lab/contracts/schemas/preflight-report.v1.schema.json`, `patch-proposal.v1.schema.json`, `lease-check.v1.schema.json`, `resume-plan.v1.schema.json`, `dispatch-plan.v1.schema.json`, `arbitration-record.v1.schema.json`, `scaffold-plan.v1.schema.json` (depends on T009)
- [ ] T013 [P] Write schemas `skill-lab/contracts/schemas/containment-report.v1.schema.json`, `export-manifest.v1.schema.json`, `release-gates.v1.schema.json`, `release-gate-report.v1.schema.json` (depends on T009)
- [ ] T014 [P] Apply the additive changes to `skill-lab/contracts/schemas/review-verdict.v1.schema.json`, `mutation-request.v1.schema.json`, `gitea-plan.v1.schema.json`, `implementation-evidence.v1.schema.json`, `merge-decision.v1.schema.json` and make `skill-lab/tests/test_contracts_r1.py` pass (depends on T009)
- [ ] T015 [P] Write `skill-lab/specs/201-release-shadow/gates.json` (`release-gates.v1`) with G-OFF-01..12, G-LIVE-01..05, G-POST-01..02 exactly as spec.md §Release gates, including each rationale; validate against `release-gates.v1` in `skill-lab/tests/test_contracts_r1.py` (depends on T013)

### Policy core (tests first)

- [ ] T016 [P] Write failing tests `skill-lab/tests/test_policy.py` (classes TestLoad, TestHostileFiles with 10 classes × ≥ 4 variants, TestClamp, TestAllows, TestRequire, TestRefusals, TestNoEscapeHatches incl. a static check that `policy.py` never reads `os.environ`, TestCatalog against the spec.md §Autonomy policy table) (depends on T010)
- [ ] T017 Implement `skill-lab/shared/_skillkit/policy.py` (plan.md §Policy module: `load`, `Policy.allows/require/refusals/require_all`, `ACTION_CATALOG` with 34 actions, `SUPPORTED_MAX_LEVEL = "shadow"`, `find_project_root`, `catalog_document`, `state_document`) until `skill-lab/tests/test_policy.py` passes

### Shared modules (tests first)

- [ ] T018 [P] Write failing tests `skill-lab/tests/test_speckit_tasks.py` asserting the golden facts (14 tasks, `[P]` set, explicit edges, T006/T007 write conflict, wave 0 = `[T003, T004]`), the wave rule of plan.md including the Convergence-phase rule, cycle detection, and `UNKNOWN_DEPENDENCY` (depends on T009)
- [ ] T019 Implement `skill-lab/shared/_skillkit/speckit_tasks.py` (parser plus `task-graph.v1` builder) until `skill-lab/tests/test_speckit_tasks.py` passes
- [ ] T020 [P] Write `skill-lab/tests/test_gitrepo.py` first (read-only allowlist, `GIT_COMMAND_FORBIDDEN`, `session_trailers` parsing `Claude-Session:` URLs, `refs_digest` stability), then implement `skill-lab/shared/_skillkit/gitrepo.py` until it passes (depends on T009)
- [ ] T021 [P] Write failing tests `skill-lab/tests/test_checks.py` (env scrub of every `redact.SECRET_ENV_VARS` name, including `GITEA_WEBHOOK_SECRET`, denylist of plan.md §Check denylist with no process started, timeout → `status: timeout`, log digest equals sha256 of log bytes, `check-run.v1` validity, no execution without `--apply`) (depends on T011)
- [ ] T022 Add `GITEA_WEBHOOK_SECRET` to `SECRET_ENV_VARS` in `skill-lab/shared/_skillkit/redact.py` (read by the normalizer, FR-025) and implement `skill-lab/shared/_skillkit/checks.py` until `skill-lab/tests/test_checks.py` passes
- [ ] T023 [P] Write the seed `skill-lab/fixtures/gitea-double/seed-golden.json` (plan.md §Gitea test double) and failing tests `skill-lab/tests/test_gitea_double.py` (every listed GET endpoint, pagination, version `28.2.0`, non-GET → 405 and logged); check field names against Gitea's `/swagger.v1.json` when a 28.x instance or the published swagger is reachable, otherwise record "unverified" in `skill-lab/specs/201-release-shadow/evidence/interface-notes.md` (depends on T001)
- [ ] T024 Implement `skill-lab/lab/gitea_double.py` (loopback, ephemeral port, JSONL request log) until `skill-lab/tests/test_gitea_double.py` passes
- [ ] T025 Write `skill-lab/tests/test_gitea_client.py` first (read methods are GET-only, pagination, `GITEA_VERSION_UNTESTED`, `send()` calls `policy.require` before any socket opens and refuses at `shadow`, exit 3 on unreachable/401), then implement `skill-lab/shared/_skillkit/gitea.py`; record the Gitea 28.x read-scope token names in `skill-lab/specs/201-release-shadow/evidence/interface-notes.md` (depends on T017)
- [ ] T026 Update the module list in `skill-lab/shared/_skillkit/__init__.py` docstring for `policy`, `speckit_tasks`, `gitrepo`, `checks`, `gitea` (depends on T017, T019, T020, T022, T025)
- [ ] T027 Write and pass `skill-lab/tests/test_sync_r1.py`: `skill-lab sync` vendors the five new modules and the new schemas into a scratch skill, and `skill-lab sync --check` reports 0 drift (depends on T010, T011, T012, T013, T014)

### Lab commands

- [ ] T028 [P] Register subcommands `policy`, `release`, `export` in `skill-lab/lab/cli.py` and the rule hooks `policy-action-known`, `eval-inventory-r1`, `--config`, `--specs` in `skill-lab/lab/validate.py` (lazy imports); test `--help` exits 0 for each in `skill-lab/tests/test_cli_r1.py` (depends on T001)
- [ ] T029 [P] Write `skill-lab/tests/test_policy_cmd.py` first (show clamped, explain each refusal code, catalog schema-valid, `--format markdown` table), then implement `skill-lab/lab/policy_cmd.py` (depends on T017, T028)
- [ ] T030 [P] Write `skill-lab/tests/test_validate_policy.py` first (unknown literal action id → error; unknown `action:` tag → error; missing refusal coverage → error; inventory counts per FR-033), then implement `skill-lab/lab/validate_policy.py` (depends on T017, T028)
- [ ] T031 [P] Build the fixture skill `skill-lab/tests/fixtures/containment/fake-skill/` (one script with a plan of `gitea.issue.create`, `git.commit`, `state.write.local`) and write failing tests `skill-lab/tests/test_containment.py` (effects counted: non-GET, refs digest, workspace files; uncovered pairs reported; exit 0 only when contained) (depends on T025, T029)
- [ ] T032 Implement `skill-lab/lab/containment.py` (sandbox: temp git repo copy, Gitea double, fresh `--state-dir`; emits `containment-report.v1`) until `skill-lab/tests/test_containment.py` passes
- [ ] T033 [P] Write failing tests `skill-lab/tests/test_release_check.py`: `not_run` never counts as pass; stage filtering; `--only`; `--root` for export mode; live metrics computed from `benchmark-run.v1` documents and case tags (per-skill agentic pass rate, `tag:guardrail` pass rate, per-skill and catalog trigger accuracy, errored+skipped count); exit 1 `RELEASE_GATES_FAILED` (depends on T013, T015, T028)
- [ ] T034 Implement `skill-lab/lab/release.py` (`release check --spec --stage --only --root --ci-checks --verdict`) emitting `release-gate-report.v1` until `skill-lab/tests/test_release_check.py` passes
- [ ] T035 [P] Write `skill-lab/tests/test_record_run.py` first (redaction, `benchmark-run.v1` validation, gate-eligibility only for `ollama-cloud` + `jev_mode: live` + 0 error/skipped, and, when `benchmark-run.v1` has no `suite` field, the strict `notes[]` lines `suite_digest=sha256:<64 hex>` (over every SKILL.md and eval case file), `commit=<sha>`, and `num_ctx=<int>` in the recorded copy, the exact fallback form SPEC-202 parses), then implement `skill-lab/lab/record_run.py` (`release record-run --run --dest`) (depends on T013, T028)

**Checkpoint**: Policy core, shared modules, double, and lab commands are green. User story work can begin.

---

## Phase 3: User Story 1 - The human controls the autonomy level and nothing can raise it (Priority: P1) 🎯 MVP

**Goal**: The owner sets the level in `.skill-policy.json`; no agent, flag, environment, or malformed file can raise it; R1 clamps to `shadow`

**Independent Test**: `skill-lab/tests/integration/test_us1_policy.py` runs the containment harness on the fake skill with every hostile policy fixture

- [ ] T036 [P] [US1] Write the example policy `skill-lab/config/policy/skill-policy.example.json` (`level: shadow`, `set_by: Cazador0`) and `skill-lab/tests/test_policy_examples.py` (validates against `autonomy-policy.v1`; loads to `shadow`) (depends on T017)
- [ ] T037 [P] [US1] Add `agent.tool_permissions` always-deny rules for `edit_file` on `.skill-policy.json` and for terminal commands mentioning it to `skill-lab/config/zed/settings.example.jsonc` (depends on T001)
- [ ] T038 [P] [US1] Add `permissions.deny` Edit and Write rules for `.skill-policy.json` to `skill-lab/config/claude/settings.example.json`, verifying the rule syntax against the Claude Code settings documentation and recording it in `skill-lab/specs/201-release-shadow/evidence/interface-notes.md` (depends on T001)
- [ ] T039 [P] [US1] Write `skill-lab/tests/test_config_rules.py` first (policy-file deny rules present in the Zed and Claude templates), then implement `skill-lab/lab/config_rules.py` behind `skill-lab validate --config zed,claude` (depends on T028)
- [ ] T040 [P] [US1] Write the operator guide `skill-lab/docs/autonomy.md` (levels, clamp, how a human changes the level, restrict-only overrides, catalog table generated by `skill-lab policy catalog --format markdown`) and the drift test `skill-lab/tests/test_policy_docs_sync.py` comparing the catalog with `skill-lab/docs/autonomy.md` and the spec.md §Autonomy policy table (depends on T029)
- [ ] T041 [US1] Write and pass the US1 acceptance test `skill-lab/tests/integration/test_us1_policy.py` covering spec.md US1 scenarios 1–6 (depends on T032, T036, T037, T038, T039)

**Checkpoint**: US1 is independently verifiable. Policy enforcement is the MVP.

---

## Phase 4: User Story 2 - Deliver this release with `/speckit-development` and an independent review (Priority: P1)

**Goal**: `speckit-development` (SPEC-013) executes tasks.md in dependency order with executed evidence, converges, drafts the PR body, emits the review request, collects the verdict, and refuses every delivery mutation at `shadow`

**Independent Test**: `skill-lab/tests/integration/test_us2_speckit_development.py` on a scratch copy of the golden feature

### Tests for User Story 2

- [ ] T042 [US2] Write SPEC-013 in `skill-lab/specs/013-speckit-development/spec.md` and planned `skill-lab/specs/013-speckit-development/traceability.json` (FR-030, FR-031, FR-034–FR-038 capabilities; contracts development-report, convergence-report, rendered-document, review-request, review-verdict, mutation-plan)
- [ ] T043 [US2] Vendor with `skill-lab sync --skill speckit-development`, copy the golden feature to `skills/speckit-development/evals/fixtures/golden/`, and write failing tests `skills/speckit-development/tests/test_dev_state.py`, `skills/speckit-development/tests/test_converge.py`, `skills/speckit-development/tests/test_pr_body.py` (depends on T027)

### Implementation for User Story 2

- [ ] T044 [US2] Implement `skills/speckit-development/scripts/dev_state.py` (`status`, `next`, `check --task --apply` running the declared verification through `_skillkit.checks` per plan.md §Verification derivation (action `state.write.local`), `mark --task --apply` with `workspace.write`; `TASK_NOT_VERIFIED`, `TASK_GRAPH_CYCLE`) until `test_dev_state.py` passes (depends on T019, T022)
- [ ] T045 [P] [US2] Implement `skills/speckit-development/scripts/converge.py` (deterministic findings: untraced FR, unchecked task, missing planned path, missing `verified_by`, failed or absent check, changed file outside every task's paths; model findings via `--findings-file`; append-only `--apply`; byte-identical when clean) until `test_converge.py` passes (depends on T043, T019)
- [ ] T046 [P] [US2] Implement `skills/speckit-development/scripts/pr_body.py` (gate table prints `not run` for `not_run`) until `test_pr_body.py` passes (depends on T043)
- [ ] T047 [P] [US2] Write failing tests `skills/speckit-development/tests/test_review_request.py`, `test_review_collect.py`, `test_review_local.py`, `test_delivery_plan.py` with fixtures under `skills/speckit-development/evals/fixtures/review/` (verdict comments: approve, stale head, two json blocks, reviewer = author, reviewer in trailer; a `claude -p` output sample marked "synthetic shape, to be replaced at T049 by a recorded sample") (depends on T043)
- [ ] T048 [US2] Implement `skills/speckit-development/scripts/review_request.py` (deterministic `request_id`, round ≤ 3, `--render-prompt`) and `skills/speckit-development/scripts/review_collect.py` (FR-035 checks via `_skillkit.gitrepo.session_trailers`) until their tests pass (depends on T020)
- [ ] T049 [US2] Implement `skills/speckit-development/scripts/review_local.py` (`claude -p … --output-format json --json-schema …`, read-only tools, env scrub, `CLAUDE_CLI_NOT_FOUND`) and `skills/speckit-development/scripts/delivery_plan.py` (`--step worktree|branch|commit|push|pr|review-request|review-session`, `Policy.refusals`) until their tests pass; when `claude` is installed, record `claude --help` flag spellings and a real output sample in `skill-lab/specs/201-release-shadow/evidence/interface-notes.md` and replace the synthetic sample (depends on T017)
- [ ] T050 [US2] Write `skills/speckit-development/SKILL.md` (invocation `/speckit-development` in Zed and Claude Code, `$speckit-development` in Codex; one script per step; Runtime notes) with `skills/speckit-development/references/delivery-loop.md` and `skills/speckit-development/references/review-comment-format.md`; verify with `skill-lab validate --skill speckit-development` (depends on T044, T045, T046, T048)
- [ ] T051 [US2] Add eval cases in `skills/speckit-development/evals/cases/` (≥ 4 deterministic incl. `next-wave-golden.json`, `mark-requires-passing-check.json`, `converge-clean-is-byte-identical.json`, `collect-approve-current-head.json`, `cycle-refused.json`; policy refusals tagged `action:git.worktree.create`, `action:git.branch.create`, `action:git.commit`, `action:git.push.branch`, `action:gitea.pr.create`, `action:gitea.pr.review.request`, `action:review.session.request`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `lead-architect`), `skill-lab/benchmarks/criteria/speckit-development.json`, and set `planned: false` in `skill-lab/specs/013-speckit-development/traceability.json`; verify with `skill-lab bench --skill speckit-development --tier deterministic`
- [ ] T052 [P] [US2] Write the factory runbook `skill-lab/docs/runbooks/release-delivery.md` (steps 5–8: export, branch, push, PR; `create_session` parameters; 10-minute `send_later` polling, 60-minute limit; `review_collect.py`; ≤ 3 rounds; `BLOCKED_BY_ENV`; human merge; evidence after the reviewed head stays out of the branch) and its structural test `skill-lab/tests/test_runbook.py` (depends on T048, T049)
- [ ] T053 [US2] Write and pass the US2 acceptance test `skill-lab/tests/integration/test_us2_speckit_development.py` covering spec.md US2 scenarios 1–9 (depends on T051)
- [ ] T054 [US2] Self-hosting switch-over (plan.md §Self-hosting switch-over): run `python3 skills/speckit-development/scripts/dev_state.py status --feature skill-lab/specs/201-release-shadow` into `skill-lab/specs/201-release-shadow/evidence/development-report.json`, re-run the verification of T001–T053 with `dev_state.py check --task Tnnn --apply` (records copied to `skill-lab/specs/201-release-shadow/evidence/checks/`), and uncheck any task without a passing record (depends on T052)

**Checkpoint**: From here on `/speckit-development` drives every remaining task.

---

## Phase 5: User Story 3 - Lead plans a feature without touching Gitea (Priority: P1)

**Goal**: lead-architect, speckit-gitea-taskstoissues, and speckit-gitea-sync produce readiness, DAG, contracts, dispatch recommendation, dry-run gitea-plan, and drift report

**Independent Test**: `skill-lab/tests/integration/test_us3_lead_flow.py` on the golden feature against the read-only double

### lead-architect (SPEC-001)

- [ ] T055 [P] [US3] Write SPEC-001 in `skill-lab/specs/001-lead-architect/spec.md` and planned `skill-lab/specs/001-lead-architect/traceability.json` (FR-018) (depends on T054)
- [ ] T056 [US3] Vendor with `skill-lab sync --skill lead-architect`, copy the golden feature to `skills/lead-architect/evals/fixtures/golden/`, and write failing tests `skills/lead-architect/tests/test_spec_readiness.py`, `test_plan_dag.py`, `test_issue_contract.py`, `test_dispatch_recommend.py`, `test_arbitrate.py`
- [ ] T057 [US3] Implement `skills/lead-architect/scripts/spec_readiness.py` and `skills/lead-architect/scripts/plan_dag.py` on `_skillkit.speckit_tasks` until their tests pass (depends on T019)
- [ ] T058 [US3] Implement `skills/lead-architect/scripts/issue_contract.py` with `skills/lead-architect/assets/templates/issue-body.md`, `skills/lead-architect/scripts/dispatch_recommend.py` (refusals for `gitea.issue.assign`, `lease.write.remote`), and `skills/lead-architect/scripts/arbitrate.py` (`--publish` refusal for `gitea.comment.create`) until their tests pass
- [ ] T059 [US3] Write `skills/lead-architect/SKILL.md` and `skills/lead-architect/references/dag-and-waves.md`; verify with `skill-lab validate --skill lead-architect`
- [ ] T060 [US3] Add eval cases in `skills/lead-architect/evals/cases/` (≥ 4 deterministic incl. `dag-flags-write-conflict.json`; refusals tagged `action:gitea.issue.assign`, `action:lease.write.remote`, `action:gitea.comment.create`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `speckit-development`), `skill-lab/benchmarks/criteria/lead-architect.json`, and set `planned: false` in `skill-lab/specs/001-lead-architect/traceability.json`; verify with `skill-lab bench --skill lead-architect --tier deterministic`

### speckit-gitea-taskstoissues (SPEC-004)

- [ ] T061 [P] [US3] Write SPEC-004 in `skill-lab/specs/004-speckit-gitea-taskstoissues/spec.md` and planned `skill-lab/specs/004-speckit-gitea-taskstoissues/traceability.json` (FR-021) (depends on T054)
- [ ] T062 [US3] Vendor with `skill-lab sync --skill speckit-gitea-taskstoissues`, add fixtures `skills/speckit-gitea-taskstoissues/evals/fixtures/` (golden tasks.md, an issues export equal to the double's seed: open T001–T003, closed T013, orphan T099; a map file), and write failing tests `skills/speckit-gitea-taskstoissues/tests/test_tasks_to_issues.py` (with the seed's issues: 10 creates, 4 dependency links, `skipped[]` T001–T003 plus closed T013, orphan T099 ignored, byte-identical rerun)
- [ ] T063 [US3] Implement `skills/speckit-gitea-taskstoissues/scripts/tasks_to_issues.py` with `skills/speckit-gitea-taskstoissues/assets/templates/issue-body.md` (`--issues-file` or read-only `--gitea-url`; refusals for `gitea.issue.create`, `gitea.issue.dependency.set`, `gitea.label.define`, `gitea.labels.set`, `gitea.milestone.set`) until its tests pass (depends on T019, T025)
- [ ] T064 [US3] Write `skills/speckit-gitea-taskstoissues/SKILL.md`; verify with `skill-lab validate --skill speckit-gitea-taskstoissues`
- [ ] T065 [US3] Add eval cases in `skills/speckit-gitea-taskstoissues/evals/cases/` (≥ 4 deterministic incl. `plan-creates-missing-only.json`; refusal `apply-refused-at-shadow.json` tagged with the 5 actions above; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `speckit-gitea-sync`), `skill-lab/benchmarks/criteria/speckit-gitea-taskstoissues.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill speckit-gitea-taskstoissues --tier deterministic`

### speckit-gitea-sync (SPEC-005)

- [ ] T066 [P] [US3] Write SPEC-005 in `skill-lab/specs/005-speckit-gitea-sync/spec.md` and planned `skill-lab/specs/005-speckit-gitea-sync/traceability.json` (FR-022) (depends on T054)
- [ ] T067 [US3] Vendor with `skill-lab sync --skill speckit-gitea-sync`, add drift fixtures to `skills/speckit-gitea-sync/evals/fixtures/` (T013 closed but unchecked, orphan `T099: stray`, stale map), and write failing tests `skills/speckit-gitea-sync/tests/test_sync_drift.py`, `skills/speckit-gitea-sync/tests/test_comment_plan.py`
- [ ] T068 [US3] Implement `skills/speckit-gitea-sync/scripts/sync_drift.py` and `skills/speckit-gitea-sync/scripts/comment_plan.py` (refusal for `gitea.comment.create`) until their tests pass (depends on T019, T025)
- [ ] T069 [US3] Write `skills/speckit-gitea-sync/SKILL.md`; verify with `skill-lab validate --skill speckit-gitea-sync`
- [ ] T070 [US3] Add eval cases in `skills/speckit-gitea-sync/evals/cases/` (≥ 4 deterministic incl. `drift-orphan-and-state-mismatch.json`; refusal `comment-plan-apply-refused.json` tagged `action:gitea.comment.create`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `speckit-gitea-taskstoissues`), `skill-lab/benchmarks/criteria/speckit-gitea-sync.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill speckit-gitea-sync --tier deterministic`
- [ ] T071 [US3] Write and pass `skill-lab/tests/integration/test_us3_lead_flow.py` covering spec.md US3 scenarios 1–6 against `skill-lab/lab/gitea_double.py` (depends on T060, T065, T024)

**Checkpoint**: The Lead's shadow workflow is independently verifiable.

---

## Phase 6: User Story 4 - PSE produces a proposed patch with executed evidence (Priority: P1)

**Goal**: pse-implementer, work-lease, and session-checkpoint at R1 capability

**Independent Test**: `skill-lab/tests/integration/test_us4_pse_flow.py` in a scratch git repository built from the golden fixture

### pse-implementer (SPEC-002)

- [ ] T072 [P] [US4] Write SPEC-002 in `skill-lab/specs/002-pse-implementer/spec.md` and planned `skill-lab/specs/002-pse-implementer/traceability.json` (FR-019) (depends on T054)
- [ ] T073 [US4] Vendor with `skill-lab sync --skill pse-implementer`, add fixtures to `skills/pse-implementer/evals/fixtures/` (issue contract, spec with `[NEEDS CLARIFICATION`, unexecuted evidence draft, scratch repo recipe), and write failing tests `skills/pse-implementer/tests/test_preflight.py`, `test_run_check.py`, `test_evidence_manifest.py`, `test_propose_patch.py`, `test_delivery_plan.py`
- [ ] T074 [US4] Implement `skills/pse-implementer/scripts/preflight.py`, `skills/pse-implementer/scripts/run_check.py` (on `_skillkit.checks`), and `skills/pse-implementer/scripts/evidence_manifest.py` (`CHECK_NOT_EXECUTED`; `head_commit: null` plus `patch_ref` in R1) until their tests pass (depends on T022, T020)
- [ ] T075 [US4] Implement `skills/pse-implementer/scripts/propose_patch.py` (patch under `--out`, `SCOPE_VIOLATION`) and `skills/pse-implementer/scripts/delivery_plan.py` (`--step worktree|branch|commit|push|pr`, `Policy.refusals`) until their tests pass
- [ ] T076 [US4] Write `skills/pse-implementer/SKILL.md`; verify with `skill-lab validate --skill pse-implementer`
- [ ] T077 [US4] Add eval cases in `skills/pse-implementer/evals/cases/` (≥ 4 deterministic incl. `rejects-unexecuted-evidence.json` from CONVENTIONS §5 and `run-check-forbidden-push.json`; refusals incl. `delivery-commit-refused-at-shadow.json`, together tagged `action:git.worktree.create`, `action:git.branch.create`, `action:git.commit`, `action:git.push.branch`, `action:gitea.pr.create`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `review-verifier`), `skill-lab/benchmarks/criteria/pse-implementer.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill pse-implementer --tier deterministic`

### work-lease (SPEC-007)

- [ ] T078 [P] [US4] Write SPEC-007 in `skill-lab/specs/007-work-lease/spec.md` and planned `skill-lab/specs/007-work-lease/traceability.json` (FR-024) (depends on T054)
- [ ] T079 [US4] Vendor with `skill-lab sync --skill work-lease` and write failing tests `skills/work-lease/tests/test_lease.py` (acquire/renew/release/status/check, default TTL 1,800 s and the 300..7,200 s bound, renew extends `expires_at` from `--now`, CAS version conflict, write-domain overlap, `--mirror` refusal with a `gitea-plan` op `mirror_lease` in the plan, `overrides.deny state.write.local` refusal, concurrent acquire under `fsutil.file_lock`)
- [ ] T080 [US4] Implement `skills/work-lease/scripts/lease.py` until `skills/work-lease/tests/test_lease.py` passes
- [ ] T081 [US4] Write `skills/work-lease/SKILL.md`; verify with `skill-lab validate --skill work-lease`
- [ ] T082 [US4] Add eval cases in `skills/work-lease/evals/cases/` (≥ 4 deterministic incl. `overlap-detected.json`; refusal tagged `action:lease.write.remote`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `session-checkpoint`), `skill-lab/benchmarks/criteria/work-lease.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill work-lease --tier deterministic`

### session-checkpoint (SPEC-010)

- [ ] T083 [P] [US4] Write SPEC-010 in `skill-lab/specs/010-session-checkpoint/spec.md` and planned `skill-lab/specs/010-session-checkpoint/traceability.json` (FR-027) (depends on T054)
- [ ] T084 [US4] Vendor with `skill-lab sync --skill session-checkpoint` and write failing tests `skills/session-checkpoint/tests/test_checkpoint.py` (write/read/render, resume-plan `stale` on head mismatch, rejection of a `reasoning` field, `publish` refusal)
- [ ] T085 [US4] Implement `skills/session-checkpoint/scripts/checkpoint.py` until `skills/session-checkpoint/tests/test_checkpoint.py` passes (depends on T020)
- [ ] T086 [US4] Write `skills/session-checkpoint/SKILL.md`; verify with `skill-lab validate --skill session-checkpoint`
- [ ] T087 [US4] Add eval cases in `skills/session-checkpoint/evals/cases/` (≥ 4 deterministic incl. `rejects-chain-of-thought-fields.json`; refusal tagged `action:gitea.comment.create`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `work-lease`), `skill-lab/benchmarks/criteria/session-checkpoint.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill session-checkpoint --tier deterministic`
- [ ] T088 [US4] Write and pass `skill-lab/tests/integration/test_us4_pse_flow.py` covering spec.md US4 scenarios 1–7 (`git apply --check` on the proposed patch; every reported check matches a `check-run.v1` digest) (depends on T077, T082)

**Checkpoint**: PSE shadow workflow is independently verifiable.

---

## Phase 7: User Story 5 - Review returns an independent verdict and merge advice (Priority: P1)

**Goal**: review-verifier and merge-policy-gate at R1 capability; the verdict comment round-trips through speckit-development's collector

**Independent Test**: `skill-lab/tests/integration/test_us5_review_flow.py`

### review-verifier (SPEC-003)

- [ ] T089 [P] [US5] Write SPEC-003 in `skill-lab/specs/003-review-verifier/spec.md` and planned `skill-lab/specs/003-review-verifier/traceability.json` (FR-020) (depends on T054)
- [ ] T090 [US5] Vendor with `skill-lab sync --skill review-verifier`, copy the golden feature to `skills/review-verifier/evals/fixtures/golden/`, and write failing tests `skills/review-verifier/tests/test_requirements_matrix.py`, `test_quality_gate.py`, `test_review_verdict.py`
- [ ] T091 [US5] Implement `skills/review-verifier/scripts/requirements_matrix.py` (12 golden requirements plus SC-001..004, built from spec.md and traceability) and `skills/review-verifier/scripts/quality_gate.py` (`not_run` on applicable category fails) until their tests pass
- [ ] T092 [US5] Implement `skills/review-verifier/scripts/review_verdict.py` (`APPROVE` rule, `REVIEW_NOT_INDEPENDENT` via `_skillkit.gitrepo.session_trailers`, `--render-comment` marker plus one fenced json block, `--comment-plan [--post]` refusals for `gitea.comment.create` and `gitea.pr.review.submit`) until its tests pass (depends on T020)
- [ ] T093 [US5] Write `skills/review-verifier/SKILL.md` (opposing objective: "What evidence would prove that this implementation fails?"; never repair-and-approve); verify with `skill-lab validate --skill review-verifier`
- [ ] T094 [US5] Add eval cases in `skills/review-verifier/evals/cases/` (≥ 4 deterministic incl. `quality-gate-not-run-is-not-pass.json`, `verdict-self-review-refused.json`; refusals tagged `action:gitea.comment.create`, `action:gitea.pr.review.submit`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `pse-implementer`), `skill-lab/benchmarks/criteria/review-verifier.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill review-verifier --tier deterministic`

### merge-policy-gate (SPEC-009)

- [ ] T095 [P] [US5] Write SPEC-009 in `skill-lab/specs/009-merge-policy-gate/spec.md` and planned `skill-lab/specs/009-merge-policy-gate/traceability.json` (FR-026, FR-012 policy paths) (depends on T054)
- [ ] T096 [US5] Vendor with `skill-lab sync --skill merge-policy-gate` and write failing tests `skills/merge-policy-gate/tests/test_merge_decision.py` (every spec.md §Security policy path → `critical`; docs-only at `shadow` → `HUMAN_APPROVAL_REQUIRED` with `uncapped_decision: AUTO_MERGE`; missing verdict → `BLOCKED`; stale branch → `BLOCKED`), `skills/merge-policy-gate/tests/test_merge_plan.py`
- [ ] T097 [US5] Implement `skills/merge-policy-gate/scripts/merge_decision.py`, `skills/merge-policy-gate/scripts/merge_plan.py` (refusal for `gitea.pr.merge_when_checks_succeed`), and `skills/merge-policy-gate/references/risk-classes.md` until their tests pass
- [ ] T098 [US5] Write `skills/merge-policy-gate/SKILL.md` (decision is advisory at `shadow`; never act on `uncapped_decision`); verify with `skill-lab validate --skill merge-policy-gate`
- [ ] T099 [US5] Add eval cases in `skills/merge-policy-gate/evals/cases/` (≥ 4 deterministic incl. `policy-file-change-is-critical.json`, `docs-change-low-capped-at-shadow.json`; refusal tagged `action:gitea.pr.merge-when-checks-succeed`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `kanban-state-machine`), `skill-lab/benchmarks/criteria/merge-policy-gate.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill merge-policy-gate --tier deterministic`
- [ ] T100 [US5] Write and pass `skill-lab/tests/integration/test_us5_review_flow.py` covering spec.md US5 scenarios 1–7, including the comment round trip through `skills/speckit-development/scripts/review_collect.py` (depends on T094, T048)

**Checkpoint**: Review and merge advice are independently verifiable.

---

## Phase 8: User Story 6 - Control-plane decisions from offline events (Priority: P2)

**Goal**: gitea-event-normalizer and kanban-state-machine at R1 capability

**Independent Test**: `skill-lab/tests/integration/test_us6_events_flow.py`

### gitea-event-normalizer (SPEC-008)

- [ ] T101 [P] [US6] Write SPEC-008 in `skill-lab/specs/008-gitea-event-normalizer/spec.md` and planned `skill-lab/specs/008-gitea-event-normalizer/traceability.json` (FR-025) (depends on T054)
- [ ] T102 [US6] Vendor with `skill-lab sync --skill gitea-event-normalizer`, add payload and header fixtures to `skills/gitea-event-normalizer/evals/fixtures/` (valid, tampered, duplicate delivery, unknown event type, one fixture per vocabulary entry of FR-025; signatures computed with a fixture secret by the test, not by hand), and write failing tests `skills/gitea-event-normalizer/tests/test_normalize.py` (every vocabulary entry, `unmapped.<header>` with `blocking: false`)
- [ ] T103 [US6] Implement `skills/gitea-event-normalizer/scripts/normalize.py` (`normalize` with `hmac.compare_digest` over raw bytes; seen set via `state.write.local`; `serve` refusal for `events.gateway.serve`) and write the event-type vocabulary `skills/gitea-event-normalizer/references/event-types.md` (FR-025; the `X-Gitea-Event` and `action` values checked against the Gitea 28.x webhook docs, or marked unverified) until its tests pass
- [ ] T104 [US6] Write `skills/gitea-event-normalizer/SKILL.md`; verify with `skill-lab validate --skill gitea-event-normalizer`
- [ ] T105 [US6] Add eval cases in `skills/gitea-event-normalizer/evals/cases/` (≥ 4 deterministic incl. `tampered-body.json`, `duplicate-delivery.json`; refusal tagged `action:events.gateway.serve`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `kanban-state-machine`), `skill-lab/benchmarks/criteria/gitea-event-normalizer.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill gitea-event-normalizer --tier deterministic`

### kanban-state-machine (SPEC-006)

- [ ] T106 [P] [US6] Write SPEC-006 in `skill-lab/specs/006-kanban-state-machine/spec.md` and planned `skill-lab/specs/006-kanban-state-machine/traceability.json` (FR-023) (depends on T054)
- [ ] T107 [US6] Vendor with `skill-lab sync --skill kanban-state-machine` and write failing tests `skills/kanban-state-machine/tests/test_transition.py` (10 states × owning roles; the report's `next_action` branches WAIT, DISPATCH_PSE, MOVE_TO_REVIEW, RETURN_TO_PSE, EVALUATE_MERGE_POLICY, COMPLETE_AND_UNLOCK_DEPENDENCIES, NOOP), `skills/kanban-state-machine/tests/test_labels_plan.py` (with a swagger fixture that exposes project-column paths, so `move_issue` is planned, and one that does not, so only `set_labels` is)
- [ ] T108 [US6] Implement `skills/kanban-state-machine/scripts/transition.py`, `skills/kanban-state-machine/scripts/labels_plan.py` (refusals for `gitea.labels.set`, `gitea.project.move_issue`), and `skills/kanban-state-machine/references/states.md` until their tests pass
- [ ] T109 [US6] Write `skills/kanban-state-machine/SKILL.md`; verify with `skill-lab validate --skill kanban-state-machine`
- [ ] T110 [US6] Add eval cases in `skills/kanban-state-machine/evals/cases/` (≥ 4 deterministic incl. `review-changes-requested-returns-to-pse.json`, `illegal-transition-by-role.json`; refusals tagged `action:gitea.labels.set`, `action:gitea.project.move-issue`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `merge-policy-gate`), `skill-lab/benchmarks/criteria/kanban-state-machine.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill kanban-state-machine --tier deterministic`
- [ ] T111 [US6] Write and pass `skill-lab/tests/integration/test_us6_events_flow.py` covering spec.md US6 scenarios 1–6 (normalized events fed into `transition.py next`) (depends on T105)

**Checkpoint**: Offline control-plane decisions are independently verifiable.

---

## Phase 9: User Story 7 - Cloud-first runtime configuration and live benchmarks (Priority: P2)

**Goal**: All Zed profiles default to Ollama Cloud; local profile present but disabled; live benchmarks run when allowed and never fabricate

**Independent Test**: `skill-lab/tests/integration/test_us7_cloud_first.py` (offline)

- [ ] T112 [P] [US7] Verify the runtime facts in synthesis.md R-5 when the network allows: list Ollama Cloud models via the documented API with `OLLAMA_API_KEY`, and check Zed's `agent-profiles.md` (per-profile model) and `integrations/zed.mdx` (auth to `https://ollama.com`). Record results with date and source in a new "Runtime facts verified for SPEC-201" section of `skill-lab/docs/research/SOURCES.md` and in `skill-lab/config/zed/cloud-models.json` (M1 and context size). Without network, write `cloud-models.json` with `"verified": false` and the reason (depends on T054)
- [ ] T113 [US7] Make `skill-lab/config/zed/settings.example.jsonc` cloud-first (plan.md §Zed configuration shape: the endpoint shape T112 verified, `https://ollama.com` or a signed-in local daemon serving cloud model ids; `available_models` from `cloud-models.json` with no local model, the foundation template's local entries moved to T114's file; `agent.default_model` M1, and per-profile models for Lead, PSE, Review if T112 confirmed support), keeping T037's deny rules (depends on T037)
- [ ] T114 [P] [US7] Write `skill-lab/config/zed/local-ollama.disabled.jsonc` (`http://localhost:11434`, local models with `max_tokens` ≥ 32768 per ADR-0003, header "DISABLED until SPEC-202 L1 gate") (depends on T112)
- [ ] T115 [US7] Extend `skill-lab/tests/test_config_rules.py` first, then `skill-lab/lab/config_rules.py`, with the cloud-first rules of plan.md §Zed configuration shape (3 of 3 profiles cloud; local file not merged; unverified model ids → warning, not error) (depends on T113, T039)
- [ ] T116 [P] [US7] Write `skill-lab/tests/test_install_inference.py` first, then make `skill-lab install --inference local` exit 4 `LOCAL_INFERENCE_GATED` in `skill-lab/lab/install.py` (depends on T054)
- [ ] T117 [US7] Write and pass `skill-lab/tests/integration/test_us7_cloud_first.py` covering spec.md US7 scenarios 1–3 offline (live scenario 4 is exercised by T137) (depends on T115, T034, T035)

**Checkpoint**: Cloud-first configuration is verifiable offline. The live run happens in Phase 12.

---

## Phase 10: User Story 8 - Standalone export to `Cazador0/skill-factory` (Priority: P2)

**Goal**: `skill-lab/bin/export-repo` assembles a reproducible, standalone repository root

**Independent Test**: `skill-lab/tests/integration/test_us8_export_standalone.py`

- [ ] T118 [P] [US8] Write the export templates `skill-lab/config/export/README.md`, `skill-lab/config/export/AGENTS.md` (report §Authoritative repository knowledge: 8 questions only), `skill-lab/config/export/NOTICE` (MIT-vendored files, upstream concept attribution), `skill-lab/config/export/gitignore`, `skill-lab/config/export/claude-settings.json` (from T038's rules), and `skill-lab/config/export/ci.yml` (plan.md §CI workflow; pin action tags after checking their release pages) (depends on T054, T038)
- [ ] T119 [P] [US8] Write failing tests `skill-lab/tests/test_export_repo.py` covering spec.md US8 scenarios 1–5, determinism (two exports → equal `manifest_digest`), `EXPORT_OUT_INSIDE_SOURCE`, `EXPORT_SYMLINK_ESCAPE`, executable bits, and `--verify-manifest` (depends on T054, T013)
- [ ] T120 [US8] Implement `skill-lab/lab/export_repo.py` (plan.md §Export layout) and the wrapper `skill-lab/bin/export-repo` until `skill-lab/tests/test_export_repo.py` passes (depends on T118)
- [ ] T121 [US8] Write and pass `skill-lab/tests/integration/test_us8_export_standalone.py`: export to a temp dir, then run `validate`, `sync --check`, `test`, `bench --tier deterministic`, `policy containment`, and `export-repo --verify-manifest` from the export root with no access to the source tree
- [ ] T122 [P] [US8] Write `skills/README.md` (what each of the 13 skills does, family, spec id, R1 capability, invocation per runtime) (depends on T054)

**Checkpoint**: Export is independently verifiable.

---

## Phase 11: User Story 9 - Audit and authoring helpers (Priority: P3)

**Goal**: twelve-factor-audit and skill-forge at full capability

**Independent Test**: their deterministic eval suites

### twelve-factor-audit (SPEC-011)

- [ ] T123 [P] [US9] Write SPEC-011 in `skill-lab/specs/011-twelve-factor-audit/spec.md` and planned `skill-lab/specs/011-twelve-factor-audit/traceability.json` (FR-028) (depends on T054)
- [ ] T124 [US9] Vendor with `skill-lab sync --skill twelve-factor-audit`, add a small sample repository under `skills/twelve-factor-audit/evals/fixtures/sample-repo/`, and write failing tests `skills/twelve-factor-audit/tests/test_audit.py` (12 factor ids, scores 0..3, `max_total` 36, every evidence path exists, deterministic output)
- [ ] T125 [US9] Implement `skills/twelve-factor-audit/scripts/audit.py`, `skills/twelve-factor-audit/assets/signals.json`, and `skills/twelve-factor-audit/references/factors.md` (paraphrase plus links to upstream, no verbatim text, synthesis.md D-19) until its tests pass
- [ ] T126 [US9] Write `skills/twelve-factor-audit/SKILL.md`; verify with `skill-lab validate --skill twelve-factor-audit`
- [ ] T127 [US9] Add eval cases in `skills/twelve-factor-audit/evals/cases/` (≥ 4 deterministic incl. `audit-sample-repo-scorecard.json`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `skill-forge`), `skill-lab/benchmarks/criteria/twelve-factor-audit.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill twelve-factor-audit --tier deterministic`

### skill-forge (SPEC-012)

- [ ] T128 [P] [US9] Write SPEC-012 in `skill-lab/specs/012-skill-forge/spec.md` and planned `skill-lab/specs/012-skill-forge/traceability.json` (FR-029) (depends on T054)
- [ ] T129 [US9] Vendor with `skill-lab sync --skill skill-forge` and write failing tests `skills/skill-forge/tests/test_forge.py` (`new` scaffold validates with 0 errors; `SKILL_NAME_RESERVED` for `create-skill`; `check` finds a missing heading; `evals` skeleton meets FR-033 counts; `overrides.deny workspace.write` → exit 4)
- [ ] T130 [US9] Implement `skills/skill-forge/scripts/forge.py` and the template folder `skills/skill-forge/assets/templates/skill/` (incl. `SKILL.md.tmpl`, named so no runtime discovers it as a skill) until its tests pass
- [ ] T131 [US9] Write `skills/skill-forge/SKILL.md` (distinct from Zed's built-in `create-skill`); verify with `skill-lab validate --skill skill-forge`
- [ ] T132 [US9] Add eval cases in `skills/skill-forge/evals/cases/` (≥ 4 deterministic incl. `rejects-create-skill-name.json`; ≥ 3 agentic incl. 1 `guardrail`; 4 positive + 2 negative trigger, one naming `twelve-factor-audit`), `skill-lab/benchmarks/criteria/skill-forge.json`, and set `planned: false` in its traceability; verify with `skill-lab bench --skill skill-forge --tier deterministic`

**Checkpoint**: All 13 skills exist at R1 capability.

---

## Phase 12: Polish, Gates & Delivery

**Purpose**: Catalog and install, traceability, convergence, release gates, live baseline, PR, independent review

- [ ] T133 Generate `skills/CATALOG.json` with `skill-lab catalog` and the 26 discovery symlinks `.agents/skills/<name>` and `.claude/skills/<name>` with `skill-lab install --project .`; write `skill-lab/tests/test_skills_r1.py` (13 skills present, `metadata.spec` SPEC-001..013 and version `0.1.0`, inventory and criteria files present, every criteria file replaces the SPEC-104 defaults `agentic-quality`, `trigger-routing`, `agentic-schema-valid`, and `jev-uncertain` by id as spec.md §Release gates lists, 26 symlinks resolve) and verify with `skill-lab validate --runtime zed,claude,codex` (catalog ≤ 51,200 bytes) (depends on T051, T060, T065, T070, T077, T082, T087, T094, T099, T105, T110, T127, T132)
- [ ] T134 Set `planned: false` for every requirement in `skill-lab/specs/201-release-shadow/traceability.json` whose paths now exist, fix any remaining gap, and pass `skill-lab validate --specs` (G-OFF-08) (depends on T041, T053, T071, T088, T100, T111, T117, T121, T122)
- [ ] T135 Run `python3 skills/speckit-development/scripts/converge.py --feature skill-lab/specs/201-release-shadow --apply` into `skill-lab/specs/201-release-shadow/evidence/convergence-report.json`; execute any appended Convergence-phase tasks; repeat until `converged: true` (G-OFF-12)
- [ ] T136 Run `skill-lab policy containment` into `skill-lab/specs/201-release-shadow/evidence/containment-report.json` and `skill-lab release check --spec SPEC-201 --stage merge` into `skill-lab/specs/201-release-shadow/evidence/gate-report-merge.json`; every merge-stage gate must be `pass` (G-OFF-01..12)
- [ ] T137 [P] Live baseline (synthesis.md Q1). If P-L holds, run `skill-lab bench --tier agentic,trigger --runtime ollama-cloud --model <M1> --jev live`, record it with `skill-lab release record-run --dest skill-lab/specs/201-release-shadow/evidence/bench/`, and run `skill-lab release check --spec SPEC-201 --stage complete` into `skill-lab/specs/201-release-shadow/evidence/gate-report-complete.json`. Otherwise write `skill-lab/specs/201-release-shadow/evidence/bench/README.md` with date and reason and record G-LIVE-01..05 as `not_run`. Never fabricate (depends on T133, T115, T035)
- [ ] T138 Render the PR body with `python3 skills/speckit-development/scripts/pr_body.py --feature skill-lab/specs/201-release-shadow --out skill-lab/specs/201-release-shadow/evidence/pr-body.md` from the development, convergence, and gate reports (depends on T136, T137)
- [ ] T139 Export with `skill-lab/bin/export-repo --out <scratchpad>/skill-factory`, write `skill-lab/specs/201-release-shadow/evidence/export-manifest.json`, and pass `skill-lab/bin/export-repo --check <scratchpad>/skill-factory` (G-OFF-10, G-OFF-11; requires `dirty: false`)
- [ ] T140 Release PR (factory delivery, synthesis.md D-1): run `python3 skills/speckit-development/scripts/delivery_plan.py --step branch|commit|push|pr` to emit the refused-at-shadow `mutation-plan.v1`, then the orchestrator executes it on `Cazador0/skill-factory`: branch `release/r1-shadow` from the export, one commit with the attribution trailers, push, PR into `main` with body `evidence/pr-body.md`. Keep the PR record (number, URL, head SHA) out of the branch (D-17) (requires P-6, synthesis.md Q3)
- [ ] T141 Emit the round-1 review request with `python3 skills/speckit-development/scripts/review_request.py --pr-number <N> --pr-url <URL> --head <sha> --base main --spec SPEC-201 --spec SPEC-001 … --spec SPEC-013 --round 1 --author-session <this session id>` into `<scratchpad>/r1-post-review/review-request.json` (kept out of the branch, D-17) and render the reviewer prompt with `--render-prompt`
- [ ] T142 Independent review (runbook `skill-lab/docs/runbooks/release-delivery.md`): the orchestrator calls `create_session` (rendered prompt, `source_url` `https://github.com/Cazador0/skill-factory`, `source_revision` `release/r1-shadow`, no `permission_mode: plan`); the reviewer session runs review-verifier and the offline gates and posts the verdict comment; the orchestrator polls and runs `python3 skills/speckit-development/scripts/review_collect.py --request <rr.json> --comment-file <comment.md> --repo-dir <export>`. On `CHANGES_REQUESTED`: fix in the authoring session, re-run T134–T139, push, next round (≤ 3). If `create_session` is unavailable, use `review_local.py --apply` and post its comment (requires P-7)
- [ ] T143 Run `skill-lab release check --spec SPEC-201 --stage post-review --ci-checks <checks.json> --verdict <verdict.json>` (G-POST-01, G-POST-02) into `<scratchpad>/r1-post-review/gate-report-post-review.json`, which stays out of the R1 branch (D-17) and is attached to the PR thread and hand the PR to the human for merge; R1 is "merged" after the human merge and "complete" once G-LIVE-01..05 pass (release-plan.md §4)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 first; T002–T007 in parallel after it; T008 after the ADRs it cites
- **Foundational (Phase 2)**: depends on Setup and BLOCKS all user stories. Inside it: schemas (T010–T014) after T009; policy (T016–T017) after T010; shared modules in parallel; lab commands after T028
- **US1 (Phase 3)** and **US2 (Phase 4)**: start after Foundational, independently
- **US3–US9 (Phases 5–11)**: start after Foundational. Each phase's opening tasks additionally depend on **T054** (self-hosting switch-over), so `/speckit-development` drives them (synthesis.md D-11)
- **Polish & Delivery (Phase 12)**: depends on every user-story phase. T137 can run in parallel with T134–T136. T140–T143 are strictly sequential

### User Story Dependencies

- **US1 (P1)**: Foundational only
- **US2 (P1)**: Foundational only (its review collector is later reused by the US5 integration test)
- **US3, US4, US6, US9**: Foundational plus T054
- **US5 (P1)**: Foundational plus T054. Its integration test T100 also uses US2's `review_collect.py` (T048)
- **US7 (P2)**: Foundational plus T054. Its live scenario runs in T137
- **US8 (P2)**: Foundational plus T054. It uses US1's Claude deny rules (T038)

### Within Each Skill Track

- Spec → vendor plus failing tests → scripts → SKILL.md → evals plus criteria plus traceability
- Tests MUST fail before implementation
- `SKILL.md` is written after its scripts exist, so every procedure step names a real command

### Parallel Opportunities

- T002–T007 (ADRs and checklist)
- T010–T015 (schema groups), T018/T020/T021/T023 (shared-module tests), T028–T031/T033/T035 (lab commands)
- After T054: the opening spec tasks of all 12 remaining skills (T055, T061, T066, T072, T078, T083, T089, T095, T101, T106, T123, T128) plus T112, T116, T118, T119, T122

---

## Parallel Example: after the switch-over (T054)

```bash
# Twelve independent skill tracks can start together:
Task: "Write SPEC-001 in skill-lab/specs/001-lead-architect/spec.md"
Task: "Write SPEC-002 in skill-lab/specs/002-pse-implementer/spec.md"
Task: "Write SPEC-003 in skill-lab/specs/003-review-verifier/spec.md"
Task: "Write SPEC-008 in skill-lab/specs/008-gitea-event-normalizer/spec.md"
# Runtime and export work in parallel with them:
Task: "Verify runtime facts → skill-lab/config/zed/cloud-models.json"
Task: "Write failing tests skill-lab/tests/test_export_repo.py"
```

---

## Implementation Strategy

### MVP first (US1)

1. Phase 1 Setup, then Phase 2 Foundational
2. Phase 3 US1 → **STOP and VALIDATE**: the containment harness proves no `--apply` above `shadow` has an effect

### Self-hosting next (US2)

3. Phase 4 US2 → T054 switch-over. Every later task is opened by `dev_state.py next` and closed by `dev_state.py mark --apply`

### Incremental delivery

4. US3 → US4 → US5 (P1 role skills), then US6, US7, US8 (P2), then US9 (P3). Each phase ends with its integration test
5. Phase 12: gates, live baseline, PR, independent review, human merge

---

## Coverage: requirements → tasks

| FR | Tasks | FR | Tasks |
|---|---|---|---|
| FR-001..FR-005 | T016, T017 | FR-026 | T095–T099 |
| FR-006 | T004, T017, T040 | FR-027 | T083–T087 |
| FR-007 | T017, T031, T032, every skill script task | FR-028 | T123–T127 |
| FR-008 | T025 | FR-029 | T128–T132 |
| FR-009 | T029 | FR-030 | T042–T044, T049, T054 |
| FR-010 | T028, T030 | FR-031 | T045, T135 |
| FR-011 | T031, T032, T136 | FR-032 | every SPEC and SKILL.md task, T133 |
| FR-012 | T037, T038, T039, T097, T118 | FR-033 | every eval task, T030 |
| FR-013 | T009–T014 | FR-034 | T047, T048, T141 |
| FR-014 | T018, T019 | FR-035 | T048, T092, T100, T142 |
| FR-015 | T020 | FR-036 | T047, T049 |
| FR-016 | T021, T022 | FR-037 | T052, T142 |
| FR-017 | T023, T024 | FR-038 | T046, T138 |
| FR-018 | T055–T060 | FR-039 | T005, T112–T117 |
| FR-019 | T072–T077 | FR-040 | T133 |
| FR-020 | T089–T094 | FR-041 | T035, T137 |
| FR-021 | T061–T065 | FR-042 | T015, T033, T034, T136, T143 |
| FR-022 | T066–T070 | FR-043 | T119, T120, T139 |
| FR-023 | T106–T110 | FR-044 | T118, T121 |
| FR-024 | T078–T082 | FR-045 | T040, T118, T122, T133 |
| FR-025 | T101–T105 | FR-046 | T003–T008 |

---

## Notes

- [P] tasks = different files, no dependency on an incomplete task
- Every task is sized for one agent session; a skill track is 5–6 tasks
- Verify tests fail before implementing
- At `shadow`, `/speckit-development` never commits or pushes. Commits on `release/r1-shadow` are made by the orchestrator at T140 (synthesis.md D-1)
- Evidence produced at or after T140 is not committed to the R1 branch (D-17)
- Avoid: vague tasks, same-file conflicts between [P] tasks, cross-story dependencies other than those listed
