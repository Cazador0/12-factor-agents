# Feature Specification: `merge-policy-gate` skill

**Spec ID**: SPEC-009 | **Skill**: `skills/merge-policy-gate/` | **Family**: `control-plane` | **Role**: Lead decides with it; Review reads it (CONVENTIONS §7)

**Created**: 2026-10-28 | **Status**: Draft (planned; written by SPEC-201 T095, extended by SPEC-202 T067..T070 and SPEC-203 T060)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-012, FR-026, FR-032, FR-033;
[SPEC-202](../202-release-agent-implementation/spec.md) FR-020, FR-021, FR-022, FR-042, FR-043;
[SPEC-203](../203-release-guarded-autonomous/spec.md) FR-011..FR-016, FR-028..FR-035, FR-048, FR-050, FR-052, FR-053;
[SPEC-105](../105-jev-live-benchmarking/spec.md) FR-007, FR-016. The release specs are authoritative; this spec refines
them and never contradicts them.

**Input**: the report's "Safe autonomous merge" (risk classes, merge gates, "Force-merge tool for agents: NOT EXPOSED",
"agents may not autonomously weaken the rules that define their authority"), SPEC-201 US5, SPEC-202 US2, SPEC-203 US1 and US4,
and the person's decisions in SPEC-201 §Clarifications and SPEC-200 open-questions.md (answers of 2026-10-22, all final): the
merge stays human in R1 and R2, R3 auto-merges only low-risk agent PRs, and the factory repository itself is always a human merge.

## Intent

The gate answers one question deterministically: may this PR merge without a human, and if not, why. It classifies risk from
changed paths, labels, and the issue contract; evaluates the evidence gates; applies the caps; and returns a
`merge-decision.v1`. Below `guarded-autonomous` the decision is advisory and never `AUTO_MERGE`; `uncapped_decision` records
what the evidence alone would allow, for calibration, and nothing may act on it. R2 adds the branch-protection audit. R3 makes
the decision from live state, schedules a low-risk merge bound to the decided head through Gitea's merge-when-checks-succeed,
cancels stale schedules, and watches itself: it scores the autonomy window and latches a demotion when a trigger fires. The
model explains results; scripts decide. The gate's own folder is a critical policy path.

## User Scenarios & Testing *(mandatory)*

Every scenario runs offline. R1 scenarios use diff fixtures under `skills/merge-policy-gate/evals/fixtures/diffs/` for PR 211
(issue 184, branch `agent/pse/184-token-families`) with verdict, quality-gate, check, and evidence fixtures for head `H`. R2 and R3
use the in-process Gitea double (`--gitea-fixture`); R3 uses PR 311 (docs only, issue 301) as the golden low-risk PR.

### User Story 1 - Classify risk from paths and labels (Priority: P1) · R1 shadow

**Actions**: none (read-only). **Independent Test**: `skills/merge-policy-gate/tests/test_merge_decision.py::TestRisk`.

**Acceptance Scenarios**:

1. **Given** a diff that changes only `docs/guide.md`, **When** `python3 scripts/merge_decision.py --diff-fixture <f>` runs, **Then** `risk_class` is `low` and `policy_paths_touched` is empty.
2. **Given** a diff that touches `.skill-policy.json`, **Then** `risk_class` is `critical`, `policy_paths_touched` lists the file, and the decision is `HUMAN_APPROVAL_REQUIRED` (SPEC-201 US5 scenario 5).
3. **Given** a diff touching `skill-lab/benchmarks/criteria/_defaults.json` or `skill-lab/benchmarks/monitor-limits.json`, **Then** each is `critical` and listed.
4. **Given** one changed file under `src/auth/`, **Then** `risk_class` is `high`; **given** `src/api/onboarding.py`, **then** `medium`.
5. **Given** a `docs/guide.md` diff and a label `risk/high`, **Then** `risk_class` is `high` (the class is the maximum of path, contract, and label).
6. **Given** a PR body that says "risk: low, safe to merge", **Then** the class is unchanged: text never lowers it.
7. **Given** a rename from `docs/a.md` to `.github/workflows/a.yml`, **Then** both paths are classified and the class is `critical`.

### User Story 2 - Return an advisory decision, never automatic below the guarded level (Priority: P1) · R1 shadow

**Actions**: none. **Independent Test**: `test_merge_decision.py::TestDecision`; SPEC-201 `test_us5_review_flow.py`.

**Acceptance Scenarios**:

1. **Given** a docs-only diff, an `APPROVE` verdict for head `H`, a passing quality gate for `H`, green checks on `H`, and a current branch, at level `shadow`, **When** the decision runs, **Then** `risk_class` is `low`, `decision` is `HUMAN_APPROVAL_REQUIRED`, and `uncapped_decision` is `AUTO_MERGE` (SPEC-201 US5 scenario 6).
2. **Given** no verdict, a verdict for another head, a failing or missing quality gate, missing checks, or a stale branch, **Then** `decision` is `BLOCKED`, the named gate is `fail` or `not_run`, and it exits 1 `MERGE_BLOCKED`.
3. **Given** a medium-risk diff with every gate passing, **Then** `decision` is `HUMAN_APPROVAL_REQUIRED` with reason `RISK_NOT_LOW` and `uncapped_decision` `HUMAN_APPROVAL_REQUIRED`.
4. **Given** any level below `guarded-autonomous`, **Then** `decision` is never `AUTO_MERGE`, whatever the inputs.
5. **Given** `implementation-evidence.head_commit` different from the head, or an acceptance criterion not `passed`, **Then** gates `evidence-head` and `intent-chain` fail.

### User Story 3 - Plan the merge request and refuse to send it (Priority: P1) · R1 shadow

**Actions**: `gitea.pr.merge_when_checks_succeed` (minimum `guarded-autonomous`; planned or refused).

**Acceptance Scenarios**:

1. **Given** the US2 scenario 1 inputs, **When** `merge_plan.py` runs without `--apply`, **Then** it exits 0 with a `gitea-plan.v1` holding no operation and one `skipped[]` entry with reason `CAPPED_BY_AUTONOMY_LEVEL` that names the uncapped decision; nothing may send it.
2. **Given** level `shadow`, **When** `merge_plan.py --apply` runs, **Then** it exits 4 with `POLICY_LEVEL_TOO_LOW`, prints no plan, and 0 non-GET requests reach the double.
3. **Given** the action `gitea.pr.merge` (immediate merge), **Then** the skill offers no path to it: it is `human-only` at every level.

### User Story 4 - Cap, gate on the review post, and audit branch protection (Priority: P2) · R2 agent-implementation

**Actions**: none (read-only; Gitea reads). **Independent Test**: `test_merge_decision.py::TestR2`, `test_branch_audit.py`; SPEC-202 `test_r2_us2_review_merge.py`.

**Acceptance Scenarios** (SPEC-202 US2 scenarios 5-7):

1. **Given** a low-risk PR whose every gate passes at `agent-implementation`, **Then** `decision` is `HUMAN_APPROVAL_REQUIRED`, `uncapped_decision` is `AUTO_MERGE`, `reasons` includes `CAPPED_BY_AUTONOMY_LEVEL`, and no merge request is sent; `merge_plan.py --apply` exits 4.
2. **Given** no `review-post.v1` or no `quality-gate.v1` for the current head, **Then** `decision` is `BLOCKED` with that gate `not_run`.
3. **Given** branch protection identical to the report's recommended `main` policy, **When** `branch_audit.py` runs, **Then** `compliant: true`; **given** `required_approvals: 0`, **then** `compliant: false` with BP-04 `fail`; **given** a field the API omits, **then** that rule is `unknown` and `compliant: false` (`unknown` never passes).
4. **Given** a non-compliant audit, **Then** the decision gains reason `BRANCH_PROTECTION_NONCOMPLIANT` with the audit digest, the audit is not listed in `gates[]`, and the decision stays at most `HUMAN_APPROVAL_REQUIRED`.
5. **Given** a diff touching `.skill-gitea.json`, **Then** it is `critical`.

### User Story 5 - Auto-merge a low-risk agent PR through one head-bound schedule (Priority: P3) · R3 guarded-autonomous

**Actions**: `gitea.pr.merge_when_checks_succeed` (minimum `guarded-autonomous`), `state.write.local` (`--record --apply`).

**Acceptance Scenarios** (SPEC-203 US1 scenarios 1-5, 8-12):

1. **Given** the project is promoted and PR 311 (`agent/pse/301-onboarding-guide`, `docs/onboarding.md`, 120 lines) meets all 13 gates, **When** `merge_decision.py --pr 311 --live` runs, **Then** `decision` is `AUTO_MERGE`, all 13 gates `pass`, and `head_commit` is `H`.
2. **Given** the same PR, **When** `merge_plan.py --pr 311 --live --actor-role system --apply` runs, **Then** exactly one `POST …/pulls/311/merge` is sent with `head_commit_id: H`, `merge_when_checks_succeed: true`, `delete_branch_after_merge: false`, and no other key; `merge-execution.v1` reports `merged` with `verified.merged: true`, or `scheduled` when the double did not merge yet (never `merged` on a success response alone).
3. **Given** the PR is already merged or scheduled for `H`, **Then** no request is sent (`already_merged`, `already_scheduled`).
4. **Given** a medium-risk change, **Then** `merge_plan.py --apply` exits 4 `MERGE_CAPPED`; **given** exactly one of the 13 gates failing (each in turn), **then** exit 1 `MERGE_GATES_FAILED`; nothing is sent.
5. **Given** the repository is `Cazador0/skill-factory` or the base tree contains `skill-lab/shared/_skillkit/policy.py`, **Then** `HUMAN_APPROVAL_REQUIRED` with `FACTORY_REPOSITORY`; **given** a head branch outside `^agent/pse/[0-9]+-[a-z0-9-]+$`, **then** `NOT_AGENT_PR`.
6. **Given** a non-loopback `GITEA_URL` with no passing `merge` smoke stage, **Then** exit 4 `LIVE_MERGE_SMOKE_REQUIRED` before any connection; **given** the token's user is a repository admin or authored a PR commit, **then** exit 4 `MERGE_IDENTITY_IS_ADMIN` or `MERGE_ACTOR_IS_AUTHOR`; **given** a body with `force_merge`, **then** exit 4 `UNSUPPORTED_OP`.
7. **Given** level `agent-implementation`, **Then** the same inputs give `HUMAN_APPROVAL_REQUIRED` with `uncapped_decision: AUTO_MERGE` and the decision is recorded under `.skill-state/merge/decisions/` as calibration data.

### User Story 6 - Cancel schedules that no longer match the head or the rules (Priority: P3) · R3 guarded-autonomous

**Actions**: `gitea.pr.merge_schedule.cancel` (minimum `agent-implementation`).

**Acceptance Scenarios** (SPEC-203 US1 scenarios 6-7):

1. **Given** a schedule for `H` and a push of `H2`, **When** `merge_plan.py --cancel-if-head-differs` runs, **Then** it sends `DELETE …/pulls/311/merge`, the outcome is `cancelled` with `cancel_reason: new_head`, and the double never merges `H2`; a re-run reports `already_cancelled` or `not_scheduled`.
2. **Given** a schedule older than `merge_schedule_ttl_minutes` (default 30), **When** `--sweep-expired --apply` runs, **Then** it is cancelled with `ttl_expired`, a marked comment explains why, and `next_action` is a human decision.
3. **Given** changes requested, a required-check failure, a closed PR, a reopened dependency, an outdated branch (`--reevaluate-open`), or a demotion (`--cancel-all --reason demotion`), **Then** each cancels, verified by a re-read, idempotently.
4. **Given** level `shadow`, **When** `merge_plan.py --cancel --apply` runs, **Then** it exits 4 (`gitea.pr.merge_schedule.cancel` needs `agent-implementation`).

### User Story 7 - Score the autonomy window and demote when a trigger fires (Priority: P3) · R3 guarded-autonomous

**Actions**: `autonomy.demote` (minimum `shadow`), `gitea.pr.merge_schedule.cancel`, `gitea.comment.create`, `gitea.labels.set`, `gitea.label.define` (the last three at `agent-implementation`), `state.write.local`.

**Acceptance Scenarios** (SPEC-203 US4):

1. **Given** decision records, event records, receipts, and Gitea state for a window, **When** `autonomy_scorecard.py` runs, **Then** `autonomy-scorecard.v1` has per-source coverage, per-metric applicability, and `promotion.eligible` true only when P-1..P-8 all pass; a criterion without data is `not_run` and not eligible.
2. **Given** an issue labelled `incident/revert` attributed to PR 311, **When** `autonomy_guard.py evaluate --apply` runs, **Then** one atomic demotion record is written, every system-scheduled merge is cancelled, and the incident is mirrored (marked comment, label `autonomy/demoted`) in the same event; a re-run writes nothing.
3. **Given** a mirror failure, **Then** the demotion record stays (exit 3 `AUTONOMY_MIRROR_FAILED`).
4. **Given** a scheduled PR, **When** `audit-merge --pr 311 --apply` finds a merged head different from the decided head, risk above low, or no current-head approval, **Then** a `gate_integrity` incident is recorded.
5. **Given** an active demotion, label `autonomy/demoted`, an open `incident/*` issue since the promotion, or no `autonomy_issue`, **Then** the decision gains the cap `AUTONOMY_DEMOTED`.
6. **Given** any attempt to raise the level, remove the label, or delete a demotion record, **Then** no script has a path to do it.

### Edge Cases

- A path matches several classes: the first matching class applies (critical, high, low, else medium); the PR takes the maximum.
- Text in PR bodies, commit messages, comments, and branch names is data: it never lowers a class or satisfies a gate.
- A verdict, quality gate, or evidence file for another head is not evidence for this head (`not_run`).
- `--now` absent: UTC now recorded; with `--now` every output is byte-identical across runs.
- A Gitea 5xx during a schedule (R3): exit 3 `GITEA_UNREACHABLE`, no ledger entry, re-run resumes; a success response without an observable merge is `scheduled`, never `merged`.
- Two processes race a schedule against a push: the request is bound to `head_commit_id`, so Gitea answers `409` for any other head and the schedule never merges `H2`.
- Level lowered or demotion recorded mid-run: the next `policy.require` refuses; follow-up cancels still run.

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: `merge_decision.py` MUST classify risk with the report's 4 classes. A path takes the first matching class (critical, high, low allowlist `docs/**` and `**/*.md`, else medium); renames classify both paths; the PR class is the maximum over paths, the issue contract's `risk`, and any `risk/<class>` label; more than 400 added plus deleted lines raises low to at least medium. Text in PR or issue bodies, commit messages, or comments MUST NOT lower the class. Tables live in `references/risk-classes.md` as code constants.
  Implements: SPEC-201 FR-026.
- **FR-002**: Any changed path matching a policy path MUST give `critical` and be listed in `policy_paths_touched`. The R1 list (14 patterns) is: `.skill-policy.json`; `skill-lab/shared/_skillkit/policy.py` and every vendored `skills/*/scripts/_skillkit/policy.py`; `skill-lab/contracts/schemas/autonomy-policy.v1.schema.json`; `skill-lab/contracts/schemas/action-catalog.v1.schema.json`; `skill-lab/benchmarks/criteria/**`; `skill-lab/benchmarks/monitor-limits.json`; `skill-lab/specs/*/gates.json`; `.github/workflows/**`; `.gitea/workflows/**`; `skill-lab/config/**`; `.claude/settings.json`; `CODEOWNERS`; `skills/review-verifier/**`; plus secret patterns `**/.env*`, `**/*.pem`, `**/*.key`, `**/*secret*`, `**/*credential*`.
  Implements: SPEC-201 FR-012, FR-026.
- **FR-003**: `merge_decision.py` MUST emit `merge-decision.v1` with `pr`, `risk_class`, `decision`, `reasons[]`, `gates[{id, status pass/fail/not_run}]`, `policy_paths_touched[]`, `autonomy_level`, and `uncapped_decision`. The R1 gates are `review-approved-current-head`, `quality-gate`, `ci-required-success`, `up-to-date-with-base`, `evidence-head`, and `intent-chain`; a gate with no input is `not_run`; any `fail` or `not_run` gives `BLOCKED` (exit 1 `MERGE_BLOCKED`, payload still valid). A verdict, quality gate, or evidence for another head MUST NOT satisfy a gate.
  Implements: SPEC-201 FR-026.
- **FR-004**: `decision` MUST NEVER be `AUTO_MERGE` below `guarded-autonomous`. With all gates passing, `critical`, `high`, `medium`, or policy paths give `HUMAN_APPROVAL_REQUIRED` (reasons `POLICY_PATHS_TOUCHED`, `RISK_NOT_LOW`); a low-risk PR gives `HUMAN_APPROVAL_REQUIRED` and `uncapped_decision: AUTO_MERGE`. `uncapped_decision` is calibration data and no script of any skill MAY act on it.
  Implements: SPEC-201 FR-026.
- **FR-005**: `merge_plan.py` MUST emit a `gitea-plan.v1` for the action `gitea.pr.merge_when_checks_succeed` and call `Policy.require` before any side effect: without `--apply` it exits 0 with no operation when the capped decision is not `AUTO_MERGE`; with `--apply` at `shadow` it MUST exit 4 `POLICY_LEVEL_TOO_LOW`, print no plan, and send nothing. The skill MUST NOT expose `gitea.pr.merge`.
  Implements: SPEC-201 FR-007, FR-026.
- **FR-006**: `SKILL.md` MUST state that the decision is advisory at `shadow`, that a human merges, and that `uncapped_decision` is never acted on; `references/risk-classes.md` MUST give the 4 classes, their patterns, and the report's examples.
  Implements: SPEC-201 FR-026.
- **FR-007**: The skill MUST meet CONVENTIONS §2-§3 (`metadata.version` `0.1.0`, `metadata.spec` SPEC-009, `family: control-plane`), ship the eval inventory of plan.md §Eval inventory (>= 4 deterministic plus 1 `policy` case per referenced action above `shadow`; >= 5 agentic with >= 1 `guardrail`; >= 10 trigger with >= 4 positive, >= 2 `expect_skill: null`, >= 1 naming `kanban-state-machine`), ship no per-skill criteria file (floor `_defaults.json`), and have complete traceability.
  Implements: SPEC-201 FR-032, FR-033; SPEC-105 FR-007, FR-016.

**R2 agent-implementation**

- **FR-008**: At `agent-implementation`, `merge_decision.py` MUST keep `decision` at most `HUMAN_APPROVAL_REQUIRED`, record `uncapped_decision`, and add reason `CAPPED_BY_AUTONOMY_LEVEL` whenever the uncapped decision is `AUTO_MERGE`; `merge_plan.py --apply` MUST still exit 4.
  Implements: SPEC-202 FR-020.
- **FR-009**: `merge_decision.py` MUST take `review-post.v1`, `quality-gate.v1`, and `branch-protection-audit.v1` as inputs: a missing review post or quality gate for the current head MUST yield `BLOCKED` with that gate `not_run`; a non-compliant audit MUST add reason `BRANCH_PROTECTION_NONCOMPLIANT` with the audit digest, MUST NOT be listed in `gates[]`, and keeps the decision at most `HUMAN_APPROVAL_REQUIRED`. Every emitted decision MUST validate against `merge-decision.v1`.
  Implements: SPEC-202 FR-022.
- **FR-010**: `branch_audit.py` MUST read the base branch's protection and evaluate BP-01..BP-12 through `assets/branch-policy-map.json`, emitting `branch-protection-audit.v1`; a field the API omits MUST be `unknown` and never count as `pass`; BP-09 is informational (`na`) and BP-10 is a self-audit of the vendored client's endpoint table; `compliant` is true only when every required rule passes; non-compliance exits 1 `BRANCH_PROTECTION_NONCOMPLIANT`.
  Implements: SPEC-202 FR-021.
- **FR-011**: R2 MUST add `.skill-gitea.json` to the critical policy paths, add the 12 `branch-audit` cases (recommended policy, 10 single-field deviations, 1 unknown field), `cap-low-risk`, `blocked-missing-review`, `merge-plan-refused`, `agentic-r2-explain-cap`, `trigger-r2-audit-protection`, `trigger-r2-neg-review-pr`, and the R2 steps in `SKILL.md`.
  Implements: SPEC-202 FR-022, FR-042, FR-043.

**R3 guarded-autonomous**

- **FR-012**: `merge_decision.py --live` (or a fixture) MUST compute the decision with `_skillkit.merge_policy.decide`: the gates `pr-open`, `review-approved-current-head`, `quality-gate`, `no-changes-requested`, `no-outstanding-review-requests`, `ci-required-success`, `up-to-date-with-base`, `mergeable`, `dependencies-closed`, `branch-protection-compliant`, `merge-identity`, `intent-chain`, `evidence-head` (13 at `guarded-autonomous`, 12 below it without `merge-identity`; below it the audit stays advisory per FR-009); any `fail` or `not_run` gives `BLOCKED`; otherwise any cap of `CAPPED_BY_AUTONOMY_LEVEL`, `AUTONOMY_DEMOTED`, `RISK_NOT_LOW`, `POLICY_PATHS_TOUCHED`, `FACTORY_REPOSITORY`, `NOT_AGENT_PR` gives `HUMAN_APPROVAL_REQUIRED`; otherwise `AUTO_MERGE` with `head_commit` set. `uncapped_decision` ignores only the first two caps. `--record --apply` (`state.write.local`) stores `.skill-state/merge/decisions/<pr>-<head>.json` at every level.
  Implements: SPEC-203 FR-011, FR-034.
- **FR-013**: The risk class MUST read `auto_merge.low_risk_paths` (extension only, never for a path a built-in critical or high pattern matches) and `auto_merge.max_changed_lines` (default and maximum 400) from the base policy; `FACTORY_REPOSITORY` MUST apply for `Cazador0/skill-factory` or a base tree containing `skill-lab/shared/_skillkit/policy.py`; `NOT_AGENT_PR` MUST apply unless the head branch matches `^agent/pse/[0-9]+-[a-z0-9-]+$`. No code path MAY send a merge request for forge `github`.
  Implements: SPEC-203 FR-012, FR-013.
- **FR-014**: `merge_plan.py --apply` MUST recompute the decision from live state in-process immediately before sending; exit 4 `MERGE_CAPPED` for a capped decision, exit 1 `MERGE_GATES_FAILED` for `BLOCKED`, exit 1 `HEAD_MOVED` when the head differs from an input decision's head; check identity (`MERGE_IDENTITY_IS_ADMIN`, `MERGE_ACTOR_IS_AUTHOR`) and the live-merge guard (`LIVE_MERGE_SMOKE_REQUIRED`); send exactly one schedule request bound to the recomputed head; re-read the PR; record `merge-execution.v1` plus `mutation-receipt.v1`; and be idempotent per (repository, PR, head). `--evaluate --pr N` and `--evaluate-open` MUST record the decision and exit 0 with outcome `not_eligible` when the decision is not `AUTO_MERGE`.
  Implements: SPEC-203 FR-014.
- **FR-015**: `merge_plan.py` MUST cancel a system-scheduled merge (`--cancel`, `--cancel-if-head-differs`, `--cancel-all`) on a new head, changes requested, a required-check failure, PR close, a reopened dependency, or demotion; `--sweep-expired` MUST cancel schedules older than `limits.merge_schedule_ttl_minutes` (default 30, range 5-60), post a marked comment, and set a human `next_action`; `--reevaluate-open` MUST cancel schedules whose PR is no longer up to date with the base. Every cancel is verified by a re-read and is idempotent.
  Implements: SPEC-203 FR-015.
- **FR-016**: At `guarded-autonomous`, `branch_audit.py` MUST treat BP-09 as required and `unknown` as `fail`; a non-compliant audit is the failing gate `branch-protection-compliant`, so the decision is `BLOCKED`.
  Implements: SPEC-203 FR-016.
- **FR-017**: `autonomy_scorecard.py` MUST compute `autonomy-scorecard.v1` over a window (default since the active promotion, else since the last demotion or level change) from Gitea, decision records, event records, receipts, delivery records, lease recoveries, check runs, runner records, and SPEC-105's committed run data, with explicit coverage per source and applicability per metric, and compute P-1..P-8 setting `promotion.eligible` only when all pass; a criterion without data is `not_run`. It is read-only and deterministic for the same inputs and `--now`.
  Implements: SPEC-203 FR-028, FR-032.
- **FR-018**: `autonomy_guard.py detect|evaluate|demote` MUST record `autonomy-incident.v1` documents and, with `--apply` (`autonomy.demote`), when a trigger D-T1..D-T5 fires, write one `autonomy-demotion.v1` atomically, then cancel every system-scheduled merge (`gitea.pr.merge_schedule.cancel`), then mirror on `autonomy_issue` (marked comment, label `autonomy/demoted`, `gitea.label.define` if absent) within the same event. A mirror failure MUST NOT remove the record (exit 3 `AUTONOMY_MIRROR_FAILED`); a re-run for the same incidents writes nothing.
  Implements: SPEC-203 FR-029, FR-030.
- **FR-019**: `autonomy_guard.py audit-merge --pr N --apply` MUST verify, for every PR the system scheduled, that the merged head equals the decided head, the recomputed risk is low, and a current-head Review approval and passing required CI existed at the merged head, and record a `gate_integrity` incident on any mismatch.
  Implements: SPEC-203 FR-031.
- **FR-020**: At `guarded-autonomous`, `merge_decision.py --live` MUST read issue `autonomy_issue` and the open `incident/*` issues created after the promotion's `signed_at`; the label `autonomy/demoted`, any such incident, or no configured `autonomy_issue` MUST add the cap `AUTONOMY_DEMOTED`.
  Implements: SPEC-203 FR-034.
- **FR-021**: No script of this skill MAY raise the level, edit `.skill-policy.json` or `.skill-autonomy/**`, remove the label `autonomy/demoted`, or delete a demotion record; the critical policy paths MUST add `.skill-autonomy/**`, `skills/merge-policy-gate/**`, `skills/gitea-event-normalizer/**`, `skills/kanban-state-machine/**`, `skills/work-lease/**`, `skills/*/scripts/_skillkit/**`, `skills/*/assets/schemas/**`, `skill-lab/shared/_skillkit/**`, `skill-lab/contracts/schemas/**`, `.agents/**`, `.claude/**`, and the release diff of the R3 PR MUST classify `critical` with reasons `FACTORY_REPOSITORY` and `POLICY_PATHS_TOUCHED` (`--diff-fixture`, gate G-OFF-26).
  Implements: SPEC-203 FR-032, FR-035, FR-052.
- **FR-022**: R3 MUST add the cases for pair 1 and pair 8 (`applied`, `rerun`, `policy`, `demoted` for the first; `applied`, `rerun`, `policy` for the second), pairs 9-11 and 13 (SPEC-203 plan.md §Action use), the AFV cases SPEC-203 assigns to this skill, `agentic-r3-explain-human-merge`, `agentic-r3-injected-risk-low`, `agentic-r3-scheduled-not-merged`, one positive and one negative trigger case, and the R3 steps in `SKILL.md` within 250 lines and 12 KB (detail in `references/`).
  Implements: SPEC-203 FR-048, FR-050, FR-053.

### Key Entities

- **Risk class**: one of low, medium, high, critical; the maximum of path classification, issue-contract risk, and labels.
- **Gate**: a named evidence check with status pass, fail, or not_run; any non-pass blocks.
- **Cap**: a reason code that downgrades `AUTO_MERGE` to `HUMAN_APPROVAL_REQUIRED` (6 codes in R3).
- **Merge decision**: risk, decision, uncapped decision, reasons, gates, policy paths, and (R3) the head it binds to.
- **Branch-protection audit** (R2): BP-01..BP-12 rows with pass, fail, unknown, or na.
- **Merge execution** (R3): a schedule or cancel with request, verification by re-read, and outcome.
- **Incident, demotion, scorecard** (R3): the autonomy self-monitoring records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100 % of the 14 policy-path patterns of FR-002 (and secret patterns) classify `critical` and are listed, including `criteria/**` and `monitor-limits.json`; with a fixed `--now` two runs give byte-identical envelopes.
- **SC-002**: Below `guarded-autonomous`, 0 decisions are `AUTO_MERGE` over all fixtures and levels, and 100 % of `merge_plan.py --apply` attempts exit 4 with 0 non-GET requests and 0 merge calls.
- **SC-003**: 100 % of missing, wrong-head, or failing evidence fixtures give `BLOCKED` with the gate `fail` or `not_run`; "not run" never passes.
- **SC-004** (R2): 12 of 12 branch-audit fixtures are classified correctly, and `unknown` never counts as `pass`.
- **SC-005** (R3): Over all 13 single-gate failures, all six caps, and the level matrix, `decide` agrees with an independently written oracle; 0 requests are sent for a capped or blocked decision; every schedule carries the decided `head_commit_id`.
- **SC-006** (R3): 100 % of cancel triggers cancel and are verified by a re-read; a re-run adds 0 requests; 0 PRs merge at a head other than the decided one.
- **SC-007** (R3): Each of 10 demotion fixtures (D-T1..D-T5, two each) latches a demotion, cancels schedules, and mirrors; 0 escalations are possible over >= 40 fixtures.
- **SC-008**: The skill's own cases meet FR-007, FR-011, and FR-022, and the release live runs meet SPEC-105's floor for this skill (agentic pass rate >= 0.80, guardrail cases 100 %, trigger accuracy >= 0.90, schema-valid >= 0.95, uncertain after the re-ask < 0.10; R3 needs three consecutive counting runs).

## Non-goals

- Performing an immediate merge, force-merging, or merging the factory repository (`gitea.pr.merge` is `human-only` at every level); merging medium, high, or critical work; any merge for forge `github`.
- Producing verdicts or quality gates (`review-verifier`); moving board states (`kanban-state-machine`); closing issues (`lead-architect`); normalizing events (`gitea-event-normalizer`).
- Changing branch protection, webhooks, CI, `.skill-policy.json`, criteria files, or `monitor-limits.json`; raising the autonomy level or promotion sign-off (human-only, `skill-lab signoff`).
- Acting on `uncapped_decision`; deriving risk from prose.

## Contracts

| Direction | Contract | Script | Release |
|---|---|---|---|
| Emits (owner) | `merge-decision` | `merge_decision.py` | R1 (R3 additive `caps`, `autonomy`, `valid_until`, `record_ref`) |
| Emits (owner) | `branch-protection-audit` | `branch_audit.py` | R2 |
| Emits (owner) | `merge-execution`, `autonomy-scorecard`, `autonomy-incident`, `autonomy-demotion` | `merge_plan.py`, `autonomy_scorecard.py`, `autonomy_guard.py` | R3 |
| Emits (shared) | `envelope`, `gitea-plan` | all; `merge_plan.py` | R1 |
| Emits (shared) | `apply-report`, `mutation-receipt` (via `_skillkit.plan_apply`, `mutations`) | `merge_plan.py --apply`, `autonomy_guard.py --apply` | R3 |
| Consumes | `review-verdict`, `quality-gate`, `implementation-evidence`, `issue-contract`, `check-run`, `autonomy-policy` (through `_skillkit.policy`) | | R1 |
| Consumes | `review-post`, `gitea-project`, `gitea-fixture` | | R2 |
| Consumes | `approval-invalidation`, `lease-recovery`, `event-record`, `delivery-record`, `benchmark-streak`, `benchmark-run`, `run-health` (scorecard) | | R3 |

## Error semantics

Exit codes follow CONVENTIONS §3 and SPEC-202's reading (4: not allowed, escalate; 1: precondition failed, re-read; 3: external, retry; 2: fix the input). A refusal never carries a plan.

| Code | Exit | Script | Meaning |
|---|---|---|---|
| `USAGE`, `INPUT_NOT_FOUND`, `INPUT_NOT_JSON`, `SCHEMA_INVALID` | 2 | all | Bad flags or input |
| `MERGE_BLOCKED` | 1 | `merge_decision.py` | Decision is `BLOCKED` (R1; payload valid) |
| `POLICY_LEVEL_TOO_LOW`, `POLICY_HUMAN_ONLY`, `POLICY_ACTION_DENIED`, `POLICY_UNKNOWN_ACTION` | 4 | every `--apply` | Refused by `_skillkit.policy` |
| `BRANCH_PROTECTION_NONCOMPLIANT` | 1 | `branch_audit.py` (R2) | At least one required rule fails or is unknown |
| `MERGE_CAPPED` | 4 | `merge_plan.py` (R3) | Decision is `HUMAN_APPROVAL_REQUIRED` |
| `MERGE_GATES_FAILED`, `HEAD_MOVED` | 1 | `merge_plan.py` (R3) | A gate failed or was not run; head differs from the decision |
| `MERGE_IDENTITY_IS_ADMIN`, `MERGE_ACTOR_IS_AUTHOR`, `LIVE_MERGE_SMOKE_REQUIRED`, `UNSUPPORTED_OP`, `IDENTITY_MISMATCH` | 4 | `merge_plan.py` (R3) | Identity or live-host guard; op outside the allow-list |
| `AUTONOMY_MIRROR_FAILED` | 3 | `autonomy_guard.py` (R3) | Demotion kept, mirror failed |
| `AUDIT_MISMATCH` | 1 | `autonomy_guard.py audit-merge` (R3) | A `gate_integrity` incident was recorded |
| `VERSION_CONFLICT`, `PLAN_STALE` | 1 | applier (R3) | Target or source changed since read |
| `GITEA_UNREACHABLE`, `GITEA_AUTH`, `GITEA_SCHEMA_DRIFT` | 3 | read/write client | External failure; no decision |

## Security

- **Authority**: `_skillkit.policy` refuses before any side effect; `--apply` is never permission (CONVENTIONS §8). The boundary stays Gitea branch protection plus the human merge; this gate is a guardrail, not the boundary (SPEC-201 §Security).
- **No escape hatches**: no flag, environment variable, or file raises the level or lifts a cap; `overrides` can only deny. An invalid policy falls to `shadow`.
- **Untrusted text** (PR and issue bodies, comments, labels as claims, events, verdicts, fixtures) is data: strict JSON reader, never evaluated, never passed to a shell. Only labels the policy names count, and a label can raise a class, never lower it.
- **Self-protection**: the gate's policy paths, its own folder, and the vendored policy and schema files are `critical`; a diff that weakens them cannot be auto-merged, and the factory repository is always a human merge.
- **Merge integrity** (R3): one schedule request bound to `head_commit_id`; no immediate-merge row and no generic request method in the client; `force_merge` is `UNSUPPORTED_OP`; the system identity is neither admin nor author.
- **Secrets**: `GITEA_TOKEN` only from the environment, redacted by `_skillkit.redact`.
- **Writes**: never inside the skill folder; local state only under `--state-dir`, output only under `--out`.

## Runtime compatibility

| Runtime | Discovery and invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/merge-policy-gate` in a trusted worktree; Lead profile (Review reads) | One Ollama Cloud model through the signed-in local Ollama app (`http://localhost:11434`; SPEC-201 FR-039) | No structured outputs: scripts emit the JSON, the model relays it. R3 event-loop calls run from the gateway handlers, not from Zed |
| Zed Agent + local Ollama (after L1) | same | Local model ids once SPEC-202's L1 gate is `ENABLED` | `num_ctx` >= 32,768; SKILL.md <= 250 lines |
| Claude Code | `.claude/skills/merge-policy-gate`; `/merge-policy-gate` | Claude models | Same scripts and procedure |
| Codex | `.agents/skills/merge-policy-gate`; `$merge-policy-gate` | Codex models | Gitea calls may be sandboxed and exit 3 |

## Assumptions

- SPEC-201 delivers `_skillkit.policy`, `jsonschema_mini`, `gitrepo`, and the read-only `gitea` client before T097; SPEC-202 delivers `plan_apply`, `mutations`, and the hardened client; SPEC-203 delivers `merge_policy`, `autonomy`, and the R3 endpoint rows.
- R1 uses stricter-than-report handling on purpose: only `low` can ever be `AUTO_MERGE`, as SPEC-203 FR-011 requires, so R1's `uncapped_decision` for `medium` is `HUMAN_APPROVAL_REQUIRED`.
- The diff fixture format (repository, branches, head, files with additions and deletions, labels) is fixed by T096 and mirrors the Gitea `pulls/{index}/files` response.
