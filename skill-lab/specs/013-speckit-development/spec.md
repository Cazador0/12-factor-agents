# Feature Specification: `speckit-development` skill

**Spec ID**: SPEC-013 | **Skill**: `skills/speckit-development/` | **Family**: `speckit-gitea` | **Used by**: Lead and PSE profiles, the build orchestrator (CONVENTIONS §7)

**Created**: 2026-10-28 | **Status**: Draft (planned; written by SPEC-201 T042, extended by SPEC-202 T090–T097 and SPEC-203 T129–T131, T155)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-004, FR-007, FR-014..FR-016, FR-030, FR-031, FR-032, FR-033, FR-034, FR-035,
FR-036, FR-037, FR-038, FR-048; [SPEC-202](../202-release-agent-implementation/spec.md) FR-010..FR-015, FR-030..FR-034, FR-042, FR-043, FR-049;
[SPEC-203](../203-release-guarded-autonomous/spec.md) FR-050, FR-051, FR-053, FR-057;
[SPEC-105](../105-jev-live-benchmarking/spec.md) FR-007, FR-016, FR-018, FR-023. The release specs are authoritative; this spec refines them and never
contradicts them.

**Input**: the roadmap's step 5 ("Execute and deliver Implementation Plan as `/speckit-development`", SPEC-200), the report's PSE and Review contracts
(§Safe autonomous merge, §Review contract), Spec Kit's converge semantics (synthesis.md F-12), and the person's decisions in SPEC-201 §Clarifications
and SPEC-200 open-questions.md (answers of 2026-10-22, final): stacked release PRs, floor gates, no per-skill criteria files, 14 skills, a reviewer that
holds no live keys and posts its own `run-health.v1`.

## Intent

`/speckit-development` (Zed, Claude Code) or `$speckit-development` (Codex) executes one feature's `tasks.md`: it computes the dependency waves, presents one
task per step, runs only the verification the task declares, marks `[x]` only behind a passing `check-run.v1`, converges the finished work against spec,
plan, and tasks, drafts the PR body, and drives the independent review (request, collect, local fallback). The scripts compute every result; the model
chooses the next step and explains the result. R1 plans every delivery mutation and refuses it with `--apply`; R2 performs the 13-step delivery from a
resumable record; R3 adds the merge-gate handoff. It never merges, at any level.

## User Scenarios & Testing *(mandatory)*

Scenarios run offline on the golden feature `skill-lab/fixtures/golden-feature/specs/042-session-refresh` (copied to
`skills/speckit-development/evals/fixtures/golden/`; T001 and T002 checked, 14 tasks). R2 and R3 add the in-process Gitea double (`--gitea-fixture`) and
materialized repositories (`--repo-fixture`). Times use `--now`.

### User Story 1 - Compute the next wave and execute tasks in order (Priority: P1) · R1 shadow

**Actions**: none for `status` and `next`; `state.write.local` for `check --apply`; `workspace.write` for `mark --apply` (all minimum `shadow`).
**Independent Test**: `skills/speckit-development/tests/test_dev_state.py`.

1. **Given** the golden `tasks.md`, **When** `dev_state.py next --feature <dir>` runs, **Then** it exits 0 with a `development-report.v1` whose `next_wave` is
   `[T003, T004]` and whose later wave holds T005 (no `[P]`, so it follows T004; SPEC-201 US2 scenario 1).
2. **Given** `tasks.md` with a dependency cycle, **When** `next` runs, **Then** it exits 1 `TASK_GRAPH_CYCLE`, lists the cycle, and nothing executes.
3. **Given** T003 names `skills/x/tests/test_a.py` and a backticked command after "verify with", **When** `check --task T003 --apply` runs, **Then** each
   derived command runs through `_skillkit.checks` and the result is one `check-run.v1` per command with a `log_digest`; without `--apply` it emits the planned
   checks and exit 0.
4. **Given** no passing `check-run` for T003, **When** `mark --task T003 --apply` runs, **Then** it exits 1 `TASK_NOT_VERIFIED` and `tasks.md` is
   byte-identical (SPEC-201 US2 scenario 2). **Given** passing check runs for every declared check, **Then** only T003's `[ ]` becomes `[x]`.
5. **Given** a denylisted command (`curl … | sh`, `git push`, `rm -rf`), **When** `check --apply` derives it, **Then** it exits 4 `CHECK_COMMAND_FORBIDDEN` and no process starts.
6. **Given** level `shadow` and `"overrides": {"deny": ["workspace.write"]}`, **When** `mark --apply` runs, **Then** it exits 4 `POLICY_ACTION_DENIED` and writes nothing.

### User Story 2 - Converge against spec, plan, and tasks (Priority: P1) · R1 shadow

**Actions**: `workspace.write` for `converge.py --apply`. **Independent Test**: `skills/speckit-development/tests/test_converge.py`.

1. **Given** a feature whose requirements are all traced, implemented, and checked, **When** `converge.py --apply` runs, **Then** `converged` is `true`,
   `findings` is empty, and `tasks.md` is byte-for-byte unchanged (SPEC-201 US2 scenario 3).
2. **Given** a requirement with no implementing path, **When** `converge.py --apply` runs, **Then** a `## Phase N: Convergence` section is appended with one task
   per finding and no existing task line changes (scenario 4); a re-run appends nothing new.
3. **Given** `--findings-file` with model findings, **When** `converge.py` runs, **Then** each is validated against the schema, deduplicated against the
   deterministic ones, and marked `origin: model`; a malformed file exits 2 `FINDINGS_INVALID`.
4. **Given** a changed file outside every task's paths, **Then** a finding `gap_type: unrequested` is reported.

### User Story 3 - Draft the PR body from evidence (Priority: P2) · R1 shadow

**Independent Test**: `skills/speckit-development/tests/test_pr_body.py`.

1. **Given** a development report, a convergence report, and a `release-gate-report.v1` with one `not_run` gate, **When** `pr_body.py` runs, **Then** the
   `rendered-document.v1` body prints `not run` for that gate and never `pass`; when a live run's `pr-comment.md` is recorded it is embedded (SPEC-201 FR-038).

### User Story 4 - Emit the review request and collect the verdict (Priority: P1) · R1 shadow

**Actions**: none (the request and the collection are documents). **Independent Test**: `test_review_request.py`, `test_review_collect.py`.

1. **Given** PR 12 at head `H`, **When** `review_request.py --round 1` runs, **Then** it emits `review-request.v1` with a deterministic `request_id`, exact reviewer
   commands, the live-run summary digest in `evidence[]`, and instructions (a) recorded evidence only, no live keys, never re-run a live case, (b)
   `skill-lab doctor` check returning `BLOCKED_BY_ENV`, (c) the `run-monitor` self-report and its separate marked comment. `--round 4` exits 4 `REVIEW_ROUNDS_EXHAUSTED`.
2. **Given** a verdict comment with the request marker, `result: APPROVE`, `reviewed_commit` equal to `H`, a reviewer session absent from every `Claude-Session:`
   trailer in `base..head`, and the reviewer's `run-health.v1` comment with `target.kind: reviewer-session`, **When** `review_collect.py` runs, **Then** it exits 0.
3. **Given** the head moved, **Then** exit 1 `VERDICT_STALE`; reviewer equals author or appears in a trailer: exit 4 `REVIEW_NOT_INDEPENDENT`; two fenced `json`
   blocks: exit 2 `VERDICT_AMBIGUOUS`; schema failure: exit 2 `VERDICT_SCHEMA_INVALID`; no marker comment: exit 1 `VERDICT_NOT_FOUND`.
4. **Given** an `APPROVE` verdict and no reviewer health comment, **Then** exit 1 `RUN_HEALTH_NOT_FOUND`; a `degraded` health report never changes the verdict.

### User Story 5 - Local fallback reviewer (Priority: P2) · R1 shadow

**Actions**: `review.local.run` (minimum `shadow`). **Independent Test**: `skills/speckit-development/tests/test_review_local.py`.

1. **Given** no `--apply`, **When** `review_local.py` runs, **Then** it exits 0 with a plan holding the exact `claude -p … --output-format json --json-schema <vendored review-verdict.v1 schema>` argv, read-only tools, and the timeout.
2. **Given** `--apply` and no `claude` on `PATH`, **Then** it exits 3 `CLAUDE_CLI_NOT_FOUND`; the child environment never holds `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, `JEV_API_KEY`, or `GITEA_TOKEN`.

### User Story 6 - Delivery operations are planned and refused at shadow (Priority: P1) · R1 shadow

**Actions** (all minimum `agent-implementation`): `git.worktree.create`, `git.branch.create`, `git.commit`, `git.push.branch`, `gitea.pr.create`,
`gitea.pr.review.request`, `review.session.request`. **Independent Test**: `skills/speckit-development/tests/test_delivery_plan.py`.

1. **Given** level `shadow`, **When** `delivery_plan.py --step worktree` runs without `--apply`, **Then** it exits 0 with a `mutation-plan.v1` holding one request with that action.
2. **Given** level `shadow`, **When** any step runs with `--apply`, **Then** it exits 4 `POLICY_LEVEL_TOO_LOW`, nothing is written, and no network or git call is made (SPEC-201 FR-007, FR-030).

### User Story 7 - Deliver a feature end to end, resumably (Priority: P3) · R2 agent-implementation

**Actions**: the seven R1 delivery actions plus `gitea.pr.update` (all minimum `agent-implementation`), `state.write.local`, `workspace.write`.
**Independent Test**: `skill-lab/tests/integration/test_r2_us4_golden_e2e.py`, `test_r2_us4_resume.py` (SPEC-202 T098, T099); `skills/speckit-development/tests/test_delivery_record.py`.

1. **Given** the golden feature applied to the double and level `agent-implementation`, **When** the delivery runs for one issue, **Then** `delivery-record.v1` shows
   steps through `review_request` as `done`, one PR exists, the Review login is a requested reviewer, a review dispatch exists, and a `review-request.v1` with forge `gitea` is recorded (SPEC-202 US4 scenario 1).
2. **Given** an interruption after any step, **When** the same `--delivery-id` resumes, **Then** execution continues at the first step not `done` with no repeated side effect (scenario 2).
3. **Given** no held lease for the issue, role `pse`, and session, **When** preflight runs, **Then** it exits 4 `LEASE_REQUIRED`, `LEASE_EXPIRED`, or `LEASE_HELD_BY_OTHER` (SPEC-202 FR-010).
4. **Given** converge still reports findings after 3 passes, **Then** the record shows `NOT_CONVERGED`, exit 1, `next_action` escalates to Lead, nothing is committed or pushed (scenario 3).
5. **Given** forge `github` (the factory repository), **When** `--step pr` runs, **Then** only a `pr-request.v1` is written under `--out`, no network call is made, and `next_action` is `orchestrator.create_pr`; with `--apply` it exits 4 `UNSUPPORTED_OP` (scenario 4).
6. **Given** review mode `cli` and no `claude`, **Then** `review_local.py --apply` exits 3 and the record holds no verdict; a fourth round exits 4 `REVIEW_ROUNDS_EXHAUSTED` (scenarios 5, 6).
7. **Given** any outcome, **Then** no merge was requested and `next_action` is a human merge or a PSE fix after `CHANGES_REQUESTED` (scenario 7).

### User Story 8 - Hand off to the merge gate; the factory stays human-merged (Priority: P3) · R3 guarded-autonomous

**Actions**: none new (the handoff records a decision; it never merges). **Independent Test**: `skills/speckit-development/tests/test_handoff_r3.py`; `skill-lab/tests/integration/test_r3_us9_handoff_factory.py` (SPEC-203 T132).

1. **Given** a promoted project and a delivered low-risk issue with an `AUTO_MERGE` decision, **When** the handoff runs, **Then** `merge_handoff.mode` is `event_loop`, `next_action` is `merge_gate.event_loop`, and no merge request was made (SPEC-203 US9 scenario 1).
2. **Given** a medium-risk issue, **Then** `mode` is `human` and `next_action` is a human merge (scenario 2).
3. **Given** forge `github`, **Then** no merge path exists, the pr step writes `pr-request.v1` only, and the mode is `human` (scenario 3).
4. **Given** `review_request.py --live-runs evidence/live-runs.json`, **Then** `evidence[]` holds the summary sha256 of every run in the streak and the sha256 of the `benchmark-streak.v1` record; a file whose runs are not consecutive counting runs on one model and suite digest exits 1 (SPEC-203 FR-057).

### Edge Cases

- `tasks.md` has an unknown `(depends on T…)` id: warning `UNKNOWN_DEPENDENCY`, the edge is unsatisfiable, the task never enters a wave.
- A task description names no test path, no "verify with" command: `mark` requires at least one passing check attached with `--check-id` (plan.md §Verification derivation); none: `TASK_NOT_VERIFIED`.
- A check log digest changed on disk after the run: `mark` exits 1 `TASK_NOT_VERIFIED` (the record is stale).
- `tasks.md` is edited by hand between `check` and `mark`: `mark` re-parses, flips only the named line, and refuses when the line no longer matches (`TASK_LINE_CHANGED`, exit 1).
- A verdict comment from an unconfigured account or with a forged marker: ignored as untrusted data; only the newest well-formed marker comment for the request counts.
- Evidence committed after the reviewed head makes the verdict stale (SPEC-201 D-17); the next round needs a new `review-request.v1`.
- A round whose fix changed any `SKILL.md` or eval case changes the suite digest, so the live gate run repeats before the next request (SPEC-201 FR-037).

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: `dev_state.py status|next` MUST parse `tasks.md` through `_skillkit.speckit_tasks`, compute waves by the wave rule, and emit `development-report.v1` (`waves`, `next_wave`, `tasks_status`, `counts`, `graph_digest`); a non-empty `cycles[]` MUST exit 1 `TASK_GRAPH_CYCLE` and execute nothing. Implements: SPEC-201 FR-014, FR-030.
- **FR-002**: `dev_state.py check --task Tnnn [--apply]` MUST derive the task's verification per plan.md §Verification derivation (test paths, "verify with"/"pass" commands, `--check-id` attachments), run each through `_skillkit.checks` only with `--apply` (action `state.write.local`), and emit one `check-run.v1` per command; the denylist MUST refuse with 4 `CHECK_COMMAND_FORBIDDEN`. Implements: SPEC-201 FR-016, FR-030.
- **FR-003**: `dev_state.py mark --task Tnnn --apply` (action `workspace.write`) MUST flip only that task's `[ ]` to `[x]`, and only when every declared check has a passing `check-run.v1` with an intact log digest; otherwise exit 1 `TASK_NOT_VERIFIED` with `tasks.md` byte-identical. Implements: SPEC-201 FR-030.
- **FR-004**: `converge.py` MUST read spec, plan, and tasks as the sole source of intent and emit `convergence-report.v1`: deterministic findings (untraced FR, unchecked task, missing planned path, missing `verified_by`, failed or absent check, changed file outside every task's paths) plus validated model findings from `--findings-file`; `gap_type` ∈ `missing`, `partial`, `contradicts`, `unrequested`; severity CRITICAL..LOW; `converged` true iff `findings` is empty. Implements: SPEC-201 FR-031.
- **FR-005**: `converge.py --apply` (action `workspace.write`) MUST append at most one `## Phase N: Convergence` section with one task per finding, MUST never rewrite, renumber, or delete a task, and MUST leave `tasks.md` byte-identical when `findings` is empty or all are already appended. Implements: SPEC-201 FR-031.
- **FR-006**: `pr_body.py` MUST render `rendered-document.v1` (`doc_kind: pr-body`) from the development, convergence, and release-gate reports; a `not_run` gate prints `not run`, never `pass`; the live run's `pr-comment.md` from `skill-lab report --run` is embedded when recorded. Implements: SPEC-201 FR-038; SPEC-105 FR-018.
- **FR-007**: `review_request.py` MUST emit `review-request.v1` with a deterministic `request_id` (`rr-` + 16 hex of repository, PR, head SHA, round), round 1..3 (round 4 exits 4 `REVIEW_ROUNDS_EXHAUSTED`), exact reviewer commands, evidence digests including the counting live run's summary sha256, the required output contract, and instructions (a), (b), (c) of SPEC-201 FR-034; `--render-prompt` MUST render the reviewer prompt (`rendered-document.v1`, `doc_kind: review-prompt`). Implements: SPEC-201 FR-034, FR-037; SPEC-105 FR-018, FR-023.
- **FR-008**: `review_collect.py` MUST select the newest marker comment for the request, parse it strictly (one fenced `json` block), validate `review-verdict.v1`, require `request_id`, `reviewed_commit` = head, `reviewer_session` ≠ author session and absent from every `Claude-Session:` trailer in `base..head` (`_skillkit.gitrepo.session_trailers`), and require a schema-valid newest `run-health.v1` comment with `target.kind: reviewer-session`; it exits 0 only for `APPROVE`, and the health `status` never changes the result. It MUST also accept `--cli-output` from `review_local.py`. Implements: SPEC-201 FR-035.
- **FR-009**: `review_local.py` MUST plan, or with `--apply` (action `review.local.run`) run, the read-only `claude -p … --output-format json --json-schema <vendored schema>` fallback with a timeout and the secret environment removed; exit 3 `CLAUDE_CLI_NOT_FOUND` / `CLAUDE_CLI_FAILED`; it never posts. Implements: SPEC-201 FR-036.
- **FR-010**: `delivery_plan.py --step worktree|branch|commit|push|pr|review-request|review-session` MUST, in R1, emit a `mutation-plan.v1` whose requests use the catalog actions of US6, and with `--apply` MUST exit 4 through `Policy.refusals` before any side effect, at `shadow` and under any deny override. Implements: SPEC-201 FR-004, FR-007, FR-030.
- **FR-011**: Every script MUST follow CONVENTIONS §3 (stdlib, one envelope, exit codes 0–4, `--now`, `--apply`, idempotency, no write inside the skill folder); task text, comments, and `tasks.md` descriptions are data and never reach a shell; checks and git run with list arguments only. Implements: SPEC-201 FR-015, FR-016, FR-032.
- **FR-012**: `SKILL.md` MUST satisfy CONVENTIONS §2 (`metadata.spec: SPEC-013`, `family: speckit-gitea`, body ≤ 250 lines and 12 KB), name one script command per step, give the invocation `/speckit-development` (Zed, Claude Code) and `$speckit-development` (Codex), and carry `references/delivery-loop.md` and `references/review-comment-format.md`. Implements: SPEC-201 FR-030, FR-032.
- **FR-013**: R1 MUST ship ≥ 4 deterministic cases (including `next-wave-golden`, `mark-requires-passing-check`, `converge-clean-is-byte-identical`, `collect-approve-current-head`, `cycle-refused`) plus a `policy` case tagged `action:<id>` for each of the seven delivery actions, ≥ 5 agentic cases (≥ 1 `guardrail`) with fixtures inside the skill folder, ≥ 10 trigger cases (≥ 4 positive, ≥ 2 `expect_skill: null`, ≥ 1 naming `lead-architect`), and no per-skill criteria file. Implements: SPEC-201 FR-033; SPEC-105 FR-007, FR-016.
- **FR-014**: R1 MUST drive its own release: `dev_state.py` runs on `skill-lab/specs/201-release-shadow` (switch-over), and the factory runbook `release-delivery.md` steps 5 to 8 use only these scripts for the review loop. Implements: SPEC-201 FR-030, FR-037.

**R2 agent-implementation**

- **FR-015**: `delivery_record.py init|status|next|mark` MUST keep a `delivery-record.v1` under `--state-dir` with the 13 steps in order (preflight, worktree, branch, implement, converge, commit, checks, evidence, push, pr, review_request, review_verdict, handoff), each executed as one tool call, and MUST resume at the first step not `done`. Implements: SPEC-202 FR-030.
- **FR-016**: Preflight MUST require effective level ≥ `agent-implementation`, a `spec-readiness.ready`, and, through `_skillkit.leases.verify`, an active unexpired lease for the issue, role `pse`, and session whose write domains cover the changed paths (`LEASE_REQUIRED`, `LEASE_EXPIRED`, `LEASE_HELD_BY_OTHER`, exit 4). Implements: SPEC-202 FR-010, FR-030.
- **FR-017**: `delivery_plan.py --apply --step worktree|branch|commit|push|pr` MUST run on the shared `_skillkit.delivery` executor (worktree-state, branch `agent/pse/<issue>-<slug>`, commit, push of that branch only, PR through the hardened client), refuse `--apply` without `--step` with exit 2 `USAGE`, and run the checks step on the committed head with a clean tree. Implements: SPEC-202 FR-011, FR-012, FR-013, FR-014, FR-015, FR-030.
- **FR-018**: Converge MUST run at most 3 passes; if findings remain the step MUST record `NOT_CONVERGED`, exit 1, set `next_action` to escalate to Lead, and skip commit and push. Implements: SPEC-202 FR-031.
- **FR-019**: With forge `github`, `--step pr` MUST only write `pr-request.v1` under `--out` and set `next_action: orchestrator.create_pr`, with no network call and at every level; `--apply` MUST exit 4 `UNSUPPORTED_OP`. Implements: SPEC-202 FR-033.
- **FR-020**: On forge `gitea`, `--apply --step review-request` (`gitea.pr.review.request`) MUST request the Review login, and `--step review-session` (`review.session.request`) MUST write a dispatch file rendered from `review_request.py --render-prompt`; the fallback is `review_local.py` with `reviewer.mode: cli-fallback`; the 3-round limit holds. Implements: SPEC-202 FR-032.
- **FR-021**: The skill MUST NOT request a merge: the handoff step MUST record the merge decision (at most `HUMAN_APPROVAL_REQUIRED` at `agent-implementation`) and `next_action` MUST be a human merge or a PSE fix after `CHANGES_REQUESTED`. Implements: SPEC-202 FR-034.
- **FR-022**: `SKILL.md` MUST document the 13-step R2 procedure with `references/r2-delivery.md` (≤ 300 lines, TOC) and `assets/templates/pr-body.md`, `assets/templates/review-dispatch.md`; R2 MUST add, for each of the 8 (skill, action) pairs `git.worktree.create`, `git.branch.create`, `git.commit`, `git.push.branch`, `gitea.pr.create`, `gitea.pr.update`, `gitea.pr.review.request`, `review.session.request`, an `applied` and a `rerun` deterministic case, the `policy` case `pr-update-refused-at-shadow`, ≥ 1 agentic case, and a positive and a negative trigger case. Implements: SPEC-202 FR-042, FR-043.

**R3 guarded-autonomous**

- **FR-023**: At `guarded-autonomous`, the handoff MUST record `merge_handoff{decision, decision_digest, uncapped_decision, mode}` in `delivery-record.v1`, with `mode: event_loop` and `next_action: merge_gate.event_loop` only when the decision is `AUTO_MERGE`, else `mode: human`. Implements: SPEC-203 FR-051.
- **FR-024**: No script of this skill MAY invoke `merge_plan.py` or reference a merge endpoint (static test over the scripts); on forge `github` the mode is always `human`. Implements: SPEC-203 FR-051.
- **FR-025**: `review_request.py --live-runs <evidence/live-runs.json>` MUST put the summary sha256 of every streak run and the sha256 of the `benchmark-streak.v1` record into `evidence[]`, keep R1's reviewer instructions, exit 1 when the runs are fewer than three (R3 needs three consecutive live runs) or are not consecutive counting runs on one model and suite digest, and exit 4 `REVIEW_ROUNDS_EXHAUSTED` above round 3. Implements: SPEC-203 FR-057.
- **FR-026**: The handoff MUST carry the issue contract unchanged into the merge-gate record (intent preserved: issue, spec ids, acceptance criteria, risk). Implements: SPEC-203 FR-050.
- **FR-027**: R3 MUST update `SKILL.md` (handoff per level), add the cases `handoff-event-loop-low-risk`, `handoff-human-medium`, `afv-handoff-keeps-issue-contract`, the agentic `agentic-r3-handoff-not-merge` (`guardrail`) and `agentic-r3-handoff-human-for-medium`, a positive and a negative (`merge-policy-gate`) trigger case, and no per-skill criteria file. Implements: SPEC-203 FR-050, FR-053.

### Key Entities

- **Development report** (`development-report.v1`): the state of one `tasks.md` (waves, statuses, check ids).
- **Check run** (`check-run.v1`): one executed verification command with its log digest; the only basis for `[x]`.
- **Convergence report** (`convergence-report.v1`): findings that spec, plan, and tasks are not yet satisfied, and the appended Convergence tasks.
- **Review request / verdict comment / health comment**: the request document, the marked verdict (`review-verdict.v1`), and the reviewer's marked `run-health.v1`.
- **Delivery record** (R2, `delivery-record.v1`): the resumable state of one delivery, with `merge_handoff` from R3.
- **PR request** (R2, `pr-request.v1`): the PR the orchestrator creates when the forge is GitHub.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the golden feature, `next` reports wave `[T003, T004]` and `mark` without a passing check changes 0 bytes in 100 % of runs (SPEC-201 SC-008).
- **SC-002**: `converge.py` on a clean tree leaves `tasks.md` byte-identical, and on SPEC-201/202/203 reports 0 findings at merge (G-OFF-12, G-OFF-23, G-OFF-25).
- **SC-003**: At `shadow`, every delivery `--apply` exits 4 with 0 git, network, and file writes (SPEC-201 containment, G-OFF-07).
- **SC-004**: `review_collect.py` approves only a current-head, independent `APPROVE` with a reviewer health comment: 100 % of the stale, self-review, ambiguous, and missing-health fixtures are refused.
- **SC-005**: R2: interrupting after each of the 13 steps and resuming gives 0 duplicate side effects (SPEC-202 SC-001, SC-002).
- **SC-006**: R3: 0 scripts reference a merge path; `mode` is `event_loop` only for `AUTO_MERGE`.
- **SC-007**: On each live gate run the skill meets SPEC-105's floor per skill and 100 % of its `guardrail` cases.

## Non-goals

- Merging, scheduling a merge, or force-pushing (`merge-policy-gate` decides; the human merges the factory; the R3 rebase is `pse-implementer`).
- Computing the dependency graph for planning or writing issue contracts (`lead-architect`); implementing one issue under a lease (`pse-implementer`); judging a PR (`review-verifier`).
- Writing to GitHub: with forge `github` the skill only writes `pr-request.v1` (SPEC-202 D-4).
- Creating the reviewer session itself (the orchestrator with `create_session`); live benchmark re-runs by the reviewer.
- A per-skill criteria file (the person's answer, 2026-10-22).

## Contracts

**Emits** (producer): `development-report`, `convergence-report`, `review-request`, `check-run` (through `_skillkit.checks`), `rendered-document`
(`pr-body`, `review-prompt`), `mutation-plan` (shared), `envelope`; R2 `delivery-record`, `worktree-state`, `pr-request`, `apply-report` (shared,
through `_skillkit.plan_apply`); R3 `delivery-record` with `merge_handoff`. **Consumes**: `review-verdict` and `run-health` (from PR comments),
`release-gate-report`, `task-graph` (via `_skillkit.speckit_tasks`), `spec-readiness`, `issue-contract`, `lease`, `autonomy-policy`, `action-catalog`
(via `_skillkit.policy`), `merge-decision` (R3 handoff), `benchmark-streak` and `benchmark-run` digests (R3), `gitea-project`, `gitea-fixture`,
`mutation-receipt` (R2). Comment grammars: `<!-- skill-lab:review-verdict:v1 request_id=<id> head=<sha40> -->` and
`<!-- skill-lab:run-health:v1 request_id=<id> -->`, each followed by exactly one fenced `json` block.

## Error semantics

Exit codes follow CONVENTIONS §3 with SPEC-201's reading (4 = refused, 1 = checked and failed, 3 = external, 2 = bad input).

| Code | Exit | Script | Meaning |
|---|---|---|---|
| `POLICY_LEVEL_TOO_LOW` / `POLICY_ACTION_DENIED` / `POLICY_HUMAN_ONLY` / `POLICY_UNKNOWN_ACTION` | 4 | all mutating | SPEC-201 FR-004; delivery `--apply` at `shadow` |
| `TASK_NOT_VERIFIED` / `TASK_GRAPH_CYCLE` | 1 | `dev_state.py` | Declared checks missing or failing / cycle, nothing executes |
| `TASK_LINE_CHANGED` (skill-local) / `NOT_CONVERGED` | 1 | `dev_state.py mark` / `converge.py`, delivery (R2) | Line edited since `check` / `converged` is false, or findings remain after 3 passes |
| `CHECK_COMMAND_FORBIDDEN` | 4 | `dev_state.py check` | Denylisted command; no process started |
| `CHECK_TIMEOUT` | 1 | `dev_state.py check` | Payload `status: timeout` |
| `FINDINGS_INVALID` / `TASKS_NOT_FOUND` (skill-local) | 2 | `converge.py`, `dev_state.py` | Bad findings file / no `tasks.md` |
| `REVIEW_ROUNDS_EXHAUSTED` / `REVIEW_NOT_INDEPENDENT` | 4 | `review_request.py`, `review_collect.py` | Round > 3, the person decides / reviewer equals author or authored a commit in range |
| `VERDICT_NOT_FOUND` / `VERDICT_STALE` / `RUN_HEALTH_NOT_FOUND` | 1 | `review_collect.py` | No marker comment / head moved / no reviewer health comment |
| `VERDICT_AMBIGUOUS` / `VERDICT_SCHEMA_INVALID` | 2 | `review_collect.py` | More than one `json` block / schema failure |
| `CLAUDE_CLI_NOT_FOUND` / `CLAUDE_CLI_FAILED` | 3 | `review_local.py` | Fallback reviewer unavailable or failed |
| `LEASE_REQUIRED` / `LEASE_EXPIRED` / `LEASE_HELD_BY_OTHER` | 4 | delivery (R2) | Lease missing, expired, or held by another session |
| `UNSUPPORTED_OP` / `IDENTITY_MISMATCH` | 4 | delivery (R2) | `--apply` with forge `github` / wrong role identity |
| `GITEA_UNREACHABLE` / `GITEA_AUTH` / `VERIFY_AFTER_WRITE_FAILED` | 3 | delivery (R2) | External failure; re-run resumes |
| `NOTHING_TO_COMMIT` / `WORKTREE_CONFLICT` | 1 | delivery (R2) | Precondition failed |
| `GIT_COMMAND_FORBIDDEN` | 4 | `_skillkit.gitrepo` | Non-read-only git subcommand requested |
| `USAGE` / `INPUT_NOT_FOUND` / `INPUT_NOT_JSON` / `INVALID_NOW` / `INTERNAL` | 2 | all | Bad input or unexpected exception |

## Security

- The review loop is evidence-only: the reviewer holds none of `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, `JEV_API_KEY`; `review_local.py` removes secret variables from the child environment and restricts tools to read-only.
- Verification commands are untrusted input: list arguments only, the `_skillkit.checks` denylist, scrubbed environment, no network tools; logs land under `--state-dir` and pass `_skillkit.redact`.
- Comments, issue bodies, and `tasks.md` text are data: markers count only from configured identities, nothing is executed or interpolated into a shell.
- No script holds a merge path (static test in R3), and the policy file, criteria files, and `monitor-limits.json` are never edited by this skill.
- Independence is checked from `Claude-Session:` trailers and session ids, not from the reviewer's claim.

## Runtime compatibility

| Runtime | Invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/speckit-development`, `/speckit-development` | One Ollama Cloud model through the local Ollama app signed in to ollama.com (`http://localhost:11434`, SPEC-201 FR-039) | Scripts produce all JSON (no structured outputs); one tool call per step |
| Zed Agent + local Ollama (after L1) | same | Local model, context ≥ 32,768, enabled by the person after SPEC-202's L1 gate | Same procedure |
| Claude Code | `.claude/skills/speckit-development`, `/speckit-development` | Claude models | Hosts the reviewer (cloud session or `claude -p` fallback) |
| Codex | `.agents/skills/speckit-development`, `$speckit-development` | Codex models | Network sandboxing may block Gitea and push; scripts then exit 3 and nothing is skipped silently |

## Assumptions

- `_skillkit.speckit_tasks`, `checks`, `gitrepo`, `policy` exist from SPEC-201 T017–T022; `delivery`, `leases.verify`, `plan_apply` from SPEC-202 T030–T040.
- `review_local.py --apply` writes the CLI's raw output under `--out` and emits it as `review-verdict` for `review_collect.py --cli-output`; the exact flag spellings are recorded at SPEC-201 T049.
- `TASK_LINE_CHANGED` is a skill-local code proposed here; it becomes real at T044 or is renamed in `interface-notes.md`. `converge.py` exits 1 `NOT_CONVERGED` when `converged` is false (so the gate command G-OFF-12 fails on findings), still emitting a valid `convergence-report.v1`.
- The R2 `delivery_plan.py` keeps its R1 flags; only `--apply` changes behaviour (SPEC-202 plan).
