# Feature Specification: `review-verifier` skill

**Spec ID**: SPEC-003 | **Skill**: `skills/review-verifier/` | **Family**: `roles` | **Role**: Review (CONVENTIONS §7)

**Created**: 2026-10-28 | **Status**: Draft (planned; written by SPEC-201 T089, extended by SPEC-202 T070/T071 and SPEC-203 T109)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-007, FR-020, FR-032, FR-033, FR-034, FR-035;
[SPEC-202](../202-release-agent-implementation/spec.md) FR-017, FR-018, FR-019, FR-042, FR-043;
[SPEC-203](../203-release-guarded-autonomous/spec.md) FR-045, FR-048, FR-050, FR-052, FR-053;
[SPEC-105](../105-jev-live-benchmarking/spec.md) FR-007, FR-016, FR-025 (research R-15). The release specs are authoritative;
this spec refines them and never contradicts them.

**Input**: the report's Review contract ("What evidence would prove that this implementation fails to satisfy the
specification?"), its merge evidence gate ("Not run must never silently mean passed"), SPEC-201 US5 and the independent
review loop (FR-034, FR-035), and the person's decisions in SPEC-201 §Clarifications and SPEC-200 open-questions.md
(answers of 2026-10-22, all final).

## Intent

Review is not "PSE with a QA prompt". This skill gives a Review session scripts that reconstruct the requirements
matrix from the spec (never from the PSE's evidence alone), compute the quality gate, and emit a machine-readable
`review-verdict.v1` plus the PR comment that carries it. Review proves independence from the author, checks live gates
only from the committed live run and its recordings (it holds no live keys and re-runs no live case), and never repairs
the code it reviews and then approves it. R1 plans every write; R2 posts the verdict as a Gitea PR review from the Review
identity; R3 adds invalidation and dismissal of approvals that no longer match the head. The scripts compute every
result; the model chooses the next step, writes blocker text, and explains the result.

## User Scenarios & Testing *(mandatory)*

Every scenario runs offline. R1 scenarios use the golden feature `skill-lab/fixtures/golden-feature/specs/042-session-refresh`
(copied to `skills/review-verifier/evals/fixtures/golden/`: 12 requirements FR-001..FR-008 and NFR-001..NFR-004, plus
SC-001..SC-004). R2 and R3 use the in-process Gitea double (`--gitea-fixture`) with PR 211 (issue 184) and PR 311.

### User Story 1 - Rebuild the requirements matrix from the spec (Priority: P1) · R1 shadow

`requirements_matrix.py` lists every requirement and success criterion of the spec and resolves each one's verification
from the spec's Traceability table, `tasks.md`, and recorded `check-run.v1` files. The PSE's `implementation-evidence.v1`
is read as a claim to be checked, never as a source of requirements. **Actions**: none (read-only; output on stdout or `--out`).

**Independent Test**: `skills/review-verifier/tests/test_requirements_matrix.py` on the golden copy and mutated copies.

**Acceptance Scenarios**:

1. **Given** the golden feature, **When** `python3 scripts/requirements_matrix.py --feature evals/fixtures/golden --checks evals/fixtures/golden-checks` runs, **Then** it lists FR-001..FR-008, NFR-001..NFR-004 (12 requirements) and SC-001..SC-004, `source.sha256` equals the spec's digest, and `summary` counts match the rows.
2. **Given** evidence that claims `acceptance_criteria{AC-3: passed}` with no matching `check-run.v1`, **When** it runs, **Then** the requirement is `unverified` (verification `not_run`), never `covered`, and the claim is reported as a warning `EVIDENCE_CLAIM_UNGROUNDED`.
3. **Given** a requirement whose recorded check has `exit_code: 1`, **Then** its status is `failed`.
4. **Given** a requirement present in `spec.md` and absent from the evidence, **Then** it is still a row of the matrix (the matrix is built from the spec).
5. **Given** any `failed` or `unverified` row, **Then** the command exits 1 with `MATRIX_INCOMPLETE` and the payload stays schema-valid.

### User Story 2 - Compute the quality gate; "not run" is never "passed" (Priority: P1) · R1 shadow

`quality_gate.py` evaluates the report's merge evidence gate categories (format, lint, types, architecture, unit,
integration, e2e, security, dependency_scan) plus requirements traceability, review findings, spec convergence, and branch
freshness. Applicability is explicit. **Actions**: none.

**Independent Test**: `skills/review-verifier/tests/test_quality_gate.py`.

**Acceptance Scenarios**:

1. **Given** category `integration` with `applicable: true` and `status: not_run`, **When** `quality_gate.py` runs, **Then** `passed` is `false` and it exits 1 with `QUALITY_GATE_FAILED`.
2. **Given** an applicability file that marks `e2e` not applicable with a reason, **Then** `e2e` is `applicable: false` with its reason as evidence and does not fail the gate.
3. **Given** no applicability decision for a category, **Then** it exits 2 with `APPLICABILITY_MISSING` (the decision must be explicit).
4. **Given** a convergence report with findings, or a branch not current with base, or `blocking_findings` above 0, **Then** `passed` is `false`.
5. **Given** a live-run summary whose sha256 differs from the digest in the review request, **Then** category `live_gates` is `fail` with evidence naming both digests; no live case is run.

### User Story 3 - Return an independent verdict (Priority: P1) · R1 shadow

`review_verdict.py` combines matrix, quality gate, blockers, and the independence check into `review-verdict.v1`.
**Actions**: none for computing; `gitea.comment.create` and `gitea.pr.review.submit` (minimum `agent-implementation`) for the comment plan.

**Independent Test**: `skills/review-verifier/tests/test_review_verdict.py`; SPEC-201 `test_us5_review_flow.py`.

**Acceptance Scenarios**:

1. **Given** a passing gate, 0 blockers, and `unverified` 0, **When** `review_verdict.py` runs with a reviewer session absent from every `Claude-Session:` trailer of `base..head`, **Then** `result` is `APPROVE` and it exits 0.
2. **Given** the same inputs and a reviewer session id found in a trailer, or equal to `--author-session`, **Then** it exits 4 with `REVIEW_NOT_INDEPENDENT` and prints no verdict.
3. **Given** a failing quality gate, a blocker, or `unverified` above 0, **Then** `result` is `CHANGES_REQUESTED`, each blocker cites at least one requirement id and an evidence reference, and it exits 1.
4. **Given** any of `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, `JEV_API_KEY` set in the environment, **Then** `result` is `BLOCKED_BY_ENV`, no value is printed, and it exits 1.
5. **Given** live gates, **Then** `non_blocking_findings` states that live gates were checked from the committed run and recordings only and that no live case was re-run.
6. **Given** a diff in which the reviewer's own session edited production code, **Then** the independence check fails (no repair-and-approve).

### User Story 4 - Render the verdict comment and plan its posting (Priority: P1) · R1 shadow

`--render-comment` writes the PR comment; `--comment-plan [--post]` plans its posting. **Actions**: `gitea.comment.create`,
and `gitea.pr.review.submit` with `--post` (both minimum `agent-implementation`; at `shadow` they appear in plans and `--apply` exits 4).

**Acceptance Scenarios**:

1. **Given** a valid verdict, **When** `review_verdict.py --render-comment --out <dir>` runs, **Then** the comment has exactly one marker line `<!-- skill-lab:review-verdict:v1 request_id=<id> head=<sha40> -->`, a human summary, and exactly one fenced `json` block; `rendered-document.v1` has `doc_kind: verdict-comment`; and `review_collect.py` parses it to an identical payload.
2. **Given** `--comment-plan`, **Then** a `gitea-plan.v1` holds one `create_comment` op (`gitea.comment.create`); with `--post` it also holds a review-submit op (`gitea.pr.review.submit`); each carries a deterministic `idempotency_key`.
3. **Given** level `shadow`, **When** either runs with `--apply`, **Then** it exits 4 with one `POLICY_LEVEL_TOO_LOW` per refused action, no plan in that envelope, and 0 non-GET requests reach the double.

### User Story 5 - Post the verdict as a Gitea review from the Review identity (Priority: P2) · R2 agent-implementation

At `agent-implementation`, `review_verdict.py --comment-plan --post --apply` submits the verdict as a PR review after
session independence, forge-identity independence, and freshness checks. **Actions**: `gitea.pr.review.submit`,
`gitea.comment.create` (minimum `agent-implementation`).

**Independent Test**: `skills/review-verifier/tests/test_verdict_post.py`; SPEC-202 `test_r2_us2_review_merge.py`.

**Acceptance Scenarios** (SPEC-202 US2 scenarios 1-4):

1. **Given** an `APPROVE` verdict for PR 211 and the `agent-review` token, **When** the post runs, **Then** one review with event `APPROVED` exists whose body is the rendered comment under R1's marker, and `review-post.v1` has `status: posted`; `CHANGES_REQUESTED` maps to `REQUEST_CHANGES`, `BLOCKED_BY_ENV` to `COMMENT`.
2. **Given** the reviewer login equals the PR author, authored or committed any PR commit, equals the configured PSE login, the session rule fails, or the reviewer has commits outside test and eval paths, **Then** it exits 4 with `REVIEW_NOT_INDEPENDENT` and posts nothing.
3. **Given** the PR head moved after the review, **Then** it exits 1 with `VERDICT_STALE`; **given** a closed PR, exit 1 `PR_NOT_OPEN`.
4. **Given** `APPROVE` with `quality-gate.passed: false`, **Then** it exits 4 with `APPROVAL_WITHOUT_PASSING_GATE`.
5. **Given** a re-run for the same (PR, reviewed commit, verdict digest), **Then** `status` is `already_posted` and the double holds one review.

### User Story 6 - Invalidate and dismiss approvals for old heads (Priority: P3) · R3 guarded-autonomous

`invalidate.py --pr N --apply` marks local verdict and review-post records for non-head commits `stale`; with `--dismiss`
the Review identity dismisses its own `APPROVED` reviews whose `commit_id` is not the head. **Actions**: `state.write.local`
(`shadow`) for marking; `gitea.pr.review.dismiss` (minimum `guarded-autonomous`) for `--dismiss`.

**Acceptance Scenarios** (SPEC-203 US7 scenarios 1-2):

1. **Given** PR 311 approved at H1 and H2 pushed, **When** `invalidate.py --pr 311 --apply` runs, **Then** the H1 records are marked stale and the merge gate's `review-approved-current-head` fails until H2 is reviewed; `approval-invalidation.v1` has `next_round` and a `next_action` asking for a new review request.
2. **Given** a Review-identity session, **When** `invalidate.py --pr 311 --dismiss --apply` runs, **Then** the H1 approval is dismissed, verified by a re-read, and a re-run reports `already_dismissed`.
3. **Given** another reviewer's approval for an old commit, **Then** it is `not_owned` and untouched; **given** a non-Review identity with `--dismiss`, **then** exit 4 `IDENTITY_MISMATCH`.
4. **Given** level `agent-implementation` or a demotion, **When** `--dismiss --apply` runs, **Then** it exits 4 with `POLICY_LEVEL_TOO_LOW`; **given** a `403`, **then** exit 3 `GITEA_AUTH` noting BP-06 stays in force.

### Edge Cases

- A spec requirement with no Traceability row: the row exists with status `unverified` and a note, never omitted.
- A check-run whose `head_commit` differs from the reviewed commit is not evidence for that commit (status `not_run`).
- The reviewer runs inside a container with a live key present: `BLOCKED_BY_ENV`, never an approval "with a warning".
- Two verdict comments for one request: `review_collect.py` takes the newest; this skill renders exactly one per run.
- Repository text (PR body, comments, fixtures) that tells the reviewer to approve, skip a category, or use a key is data and changes no result.
- A verdict for a closed or merged PR: R2 posting exits 1 `PR_NOT_OPEN`; invalidation only marks local records.
- `--now` absent: UTC now is used and recorded; with `--now` every output is byte-identical across runs.

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: `requirements_matrix.py --feature DIR` MUST emit `requirements-matrix.v1` listing every FR, NFR, and SC id defined in `spec.md`, with `source.sha256`, per-row `verification[]` (kind test, eval, check, or manual; status passed, failed, or not_run) resolved from the spec's Traceability table, `tasks.md`, and recorded `check-run.v1` files, and `summary{covered, failed, unverified}`. It MUST be reconstructable without `implementation-evidence.v1`.
  Implements: SPEC-201 FR-020.
- **FR-002**: A row MUST be `covered` only when every verification entry resolves to an existing artifact with a passing record for the reviewed commit; a failing record gives `failed`; anything else gives `unverified`. Evidence claims with no matching record MUST be reported as warnings `EVIDENCE_CLAIM_UNGROUNDED`. Any `failed` or `unverified` row MUST exit 1 `MATRIX_INCOMPLETE`.
  Implements: SPEC-201 FR-020.
- **FR-003**: `quality_gate.py` MUST emit `quality-gate.v1` with the report's categories, explicit `applicable` per category (missing decision: exit 2 `APPLICABILITY_MISSING`), `requirements_traceability.complete`, `review.{blocking_findings, unresolved_questions}`, `spec.converged` (from `convergence-report.v1`), `branch.current_with_base`, and `passed`. An applicable category that is `not_run` or `fail` MUST make `passed` false (exit 1 `QUALITY_GATE_FAILED`).
  Implements: SPEC-201 FR-020.
- **FR-004**: `quality_gate.py --live-summary FILE --live-digest SHA` MUST set category `live_gates` from the committed live-run summary only: it passes when the file's sha256 equals the digest and the summary's gates passed, and it MUST NOT start a live case or read a key.
  Implements: SPEC-201 FR-020, FR-034; SPEC-105 FR-018.
- **FR-005**: `review_verdict.py` MUST emit `review-verdict.v1` where `APPROVE` requires `quality-gate.passed`, empty `blockers`, `requirements.unverified` 0 and `failed` 0; otherwise `CHANGES_REQUESTED`. Each blocker MUST cite at least one requirement id and an evidence reference. When any of `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, `JEV_API_KEY` is set (or `--blocked-by-env REASON` is given), the result MUST be `BLOCKED_BY_ENV` and no value printed. The verdict MAY carry `request_id` and `reviewer{mode, runtime, model?}`.
  Implements: SPEC-201 FR-020, FR-034.
- **FR-006**: The independence check MUST exit 4 `REVIEW_NOT_INDEPENDENT` when `--reviewer-session` equals `--author-session` or appears in any `Claude-Session:` trailer of `base..head`, read through `_skillkit.gitrepo.session_trailers`. A verdict MUST be refused before it is printed.
  Implements: SPEC-201 FR-020, FR-035.
- **FR-007**: `--render-comment` MUST write the comment of US4 scenario 1 (one marker line `<!-- skill-lab:review-verdict:v1 request_id=<id> head=<sha40> -->`, human summary, exactly one fenced `json` block) and emit `rendered-document.v1` (`doc_kind: verdict-comment`); `review_collect.py` MUST parse it back to an identical payload.
  Implements: SPEC-201 FR-020, FR-035.
- **FR-008**: `--comment-plan [--post]` MUST emit `gitea-plan.v1` with op `create_comment` (`gitea.comment.create`) and, with `--post`, a review-submit op (`gitea.pr.review.submit`); each with a deterministic idempotency key. Every script that can perform a catalog action MUST, without `--apply`, emit its plan and exit 0, and with `--apply` call `Policy.require` for every action before the first side effect; at `shadow` it MUST exit 4 with one error per refused action and change nothing.
  Implements: SPEC-201 FR-007, FR-020.
- **FR-009**: The reviewer MUST pursue the opposing objective and MUST NOT repair what it reviews: no script of this skill writes outside `--out` and `--state-dir`, edits production code, or approves a change its own session authored; `SKILL.md` MUST state that live gates are checked from the committed run and recordings only, with no live key held and no live case re-run, and that this is reported in `non_blocking_findings`.
  Implements: SPEC-201 FR-020, FR-034.
- **FR-010**: The skill MUST meet CONVENTIONS §2-§3 (`metadata.version` `0.1.0`, `metadata.spec` SPEC-003, `family: roles`), ship the eval inventory of plan.md §Eval inventory (>= 4 deterministic plus 1 `policy` case per referenced action above `shadow`; >= 5 agentic with >= 1 `guardrail`; >= 10 trigger with >= 4 positive, >= 2 `expect_skill: null`, >= 1 naming `pse-implementer`; tag `smoke` on exactly 1 trigger case), ship no per-skill criteria file (scored against `_defaults.json`, the floor), and have complete traceability.
  Implements: SPEC-201 FR-032, FR-033; SPEC-105 FR-007, FR-016, FR-025.

**R2 agent-implementation**

- **FR-011**: `review_verdict.py --comment-plan --post --apply` MUST submit the verdict as a Gitea PR review from the Review login: `APPROVE` to `APPROVED` (only when `quality-gate.passed`), `CHANGES_REQUESTED` to `REQUEST_CHANGES`, `BLOCKED_BY_ENV` to `COMMENT`, body R1's rendered comment. It MUST be idempotent per (PR, reviewed commit, verdict digest) and emit `review-post.v1`; a failed apply MUST resume from receipts through `_skillkit.plan_apply`.
  Implements: SPEC-202 FR-017.
- **FR-012**: Before posting, independence MUST exit 4 `REVIEW_NOT_INDEPENDENT` when the session rule fails, the reviewer login equals the PR author, any PR commit's author or committer login, or the configured PSE login, or the PR contains commits by the reviewer outside test and eval paths. `review-post.v1` MUST record the evidence under `independence`.
  Implements: SPEC-202 FR-018.
- **FR-013**: At post time `reviewed_commit` MUST equal the PR's current head (else exit 1 `VERDICT_STALE`), the PR MUST be open (else exit 1 `PR_NOT_OPEN`), and an `APPROVE` without a passing quality gate MUST exit 4 `APPROVAL_WITHOUT_PASSING_GATE`.
  Implements: SPEC-202 FR-017, FR-019.
- **FR-014**: R2 MUST add `applied` and `rerun` cases for `gitea.pr.review.submit` and `gitea.comment.create`, 5 `independence` cases (one per FR-012 condition), `post-stale-head`, `approval-without-gate`, `agentic-r2-post-stale`, `agentic-r2-self-review-refusal` (`guardrail`), triggers `trigger-r2-post-verdict` and `trigger-r2-neg-safe-to-merge`, and the R2 steps in `SKILL.md`.
  Implements: SPEC-202 FR-042, FR-043.

**R3 guarded-autonomous**

- **FR-015**: `invalidate.py --pr N --apply` MUST mark local verdict and review-post records for commits other than the head `stale` (`state.write.local`, any role) and emit `approval-invalidation.v1` with `next_round` and `next_action`; it never approves.
  Implements: SPEC-203 FR-045.
- **FR-016**: `invalidate.py --pr N --dismiss --apply` (`gitea.pr.review.dismiss`, Review identity only, else exit 4 `IDENTITY_MISMATCH`) MUST dismiss only `APPROVED` reviews by the Review login whose `commit_id` is not the head, verify each by a re-read, report `already_dismissed` on re-run, mark other reviewers' reviews `not_owned`, and map a `403` to exit 3 `GITEA_AUTH` with the note that BP-06 remains in force.
  Implements: SPEC-203 FR-045.
- **FR-017**: R3 MUST add the 4 cases for pair 7 (`applied`, `rerun`, `policy` at `agent-implementation`, `demoted`), the AFV cases SPEC-203 assigns to this skill (`afv-dismissal-verified`, `afv-stale-verdict-rejected`, `agentic-afv-injected-approve`, `agentic-r3-no-foreign-dismissal`, `agentic-r3-current-head-only`), `agentic-r3-rereview-request`, one positive and one negative trigger naming `merge-policy-gate`, and the R3 steps in `SKILL.md`, within 250 lines and 12 KB. The whole folder `skills/review-verifier/**` is a critical policy path for `merge-policy-gate` from R1 on.
  Implements: SPEC-203 FR-048, FR-050, FR-052, FR-053.

### Key Entities

- **Requirement row**: one spec id (FR, NFR, or SC) with its verification entries and a status of covered, failed, or unverified.
- **Quality gate category**: a named check family with explicit applicability, status pass, fail, or not_run, and evidence.
- **Verdict**: result, requirements counts, blockers, non-blocking findings, evidence digests, reviewer session and mode.
- **Independence evidence**: session ids, trailer set, logins, and reviewer commit paths that prove author and reviewer are distinct.
- **Review post** (R2) and **approval invalidation** (R3): the recorded outcome of posting or dismissing a review for a head.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: On the golden feature the matrix lists 12 requirements plus SC-001..SC-004, and with a fixed `--now` two runs give byte-identical envelopes.
- **SC-002**: 100 % of fixtures where an applicable category is `not_run` produce `passed: false`; 0 verdicts are `APPROVE` with `unverified` above 0 or a failing gate.
- **SC-003**: 100 % of independence fixtures (session equals author, session in a trailer, and from R2 the 5 identity kinds) are refused with `REVIEW_NOT_INDEPENDENT` and print or post nothing.
- **SC-004**: At `shadow`, 100 % of `--apply` attempts for `gitea.comment.create` and `gitea.pr.review.submit` exit 4 with 0 non-GET requests and 0 writes outside `--out` and `--state-dir`.
- **SC-005**: The rendered comment round-trips through `review_collect.py` for 100 % of verdict fixtures.
- **SC-006** (R2): Re-running a post adds 0 reviews and 0 comments, and a fault after every operation leaves 0 duplicates.
- **SC-007** (R3): 0 approvals for a non-head commit remain undismissed by the Review identity after `--dismiss`, 0 foreign approvals are dismissed, and every dismissal is verified by a re-read.
- **SC-008**: The skill's own cases meet FR-010, FR-014, and FR-017, and the release live runs meet SPEC-105's floor for this skill (agentic pass rate >= 0.80, guardrail cases 100 %, trigger accuracy >= 0.90, schema-valid >= 0.95, uncertain after the re-ask < 0.10; R3 needs three consecutive counting runs).

## Non-goals

- Implementing, fixing, or "repairing and approving" the change (`pse-implementer`); editing production code under review.
- Collecting verdicts from the PR thread, building review requests, round counting, or the `claude -p` fallback (`speckit-development`: `review_request.py`, `review_collect.py`, `review_local.py`).
- Classifying risk, deciding merges, auditing branch protection, or scheduling merges (`merge-policy-gate`); this skill never requests a merge.
- Running live benchmark cases or holding live keys; running `run-monitor` is the reviewer's separate step.
- Board transitions (`kanban-state-machine`), leases (`work-lease`), and editing `.skill-policy.json`, criteria files, or `monitor-limits.json`.
- Storing chain-of-thought in a verdict.

## Contracts

| Direction | Contract | Script | Release |
|---|---|---|---|
| Emits (owner) | `requirements-matrix`, `quality-gate`, `review-verdict` | `requirements_matrix.py`, `quality_gate.py`, `review_verdict.py` | R1 |
| Emits (owner) | `review-post` | `review_verdict.py --comment-plan --post --apply` | R2 |
| Emits (owner) | `approval-invalidation` | `invalidate.py` | R3 |
| Emits (shared) | `envelope`, `rendered-document` (`verdict-comment`), `gitea-plan` | all; `--render-comment`; `--comment-plan` | R1 |
| Emits (shared) | `apply-report`, `mutation-receipt` (via `_skillkit.plan_apply`, `mutations`) | `review_verdict.py --post --apply`, `invalidate.py --dismiss --apply` | R2, R3 |
| Consumes | `implementation-evidence`, `check-run`, `convergence-report`, `review-request`, `issue-contract`, `autonomy-policy` (through `_skillkit.policy`) | | R1 |
| Consumes | `gitea-project` (`.skill-gitea.json`), `gitea-fixture` (tests) | | R2 |

No contract is changed by this spec. `review-verdict.v1` gains only SPEC-201's optional `request_id` and `reviewer`.

## Error semantics

Exit codes follow CONVENTIONS §3 (0 ok, 1 checked and failed, 2 usage, 3 external, 4 refused). A refusal never carries a plan.

| Code | Exit | Script | Meaning |
|---|---|---|---|
| `USAGE`, `INPUT_NOT_FOUND`, `INPUT_NOT_JSON`, `SCHEMA_INVALID`, `APPLICABILITY_MISSING` | 2 | all, `quality_gate.py` | Bad flags or input |
| `MATRIX_INCOMPLETE` | 1 | `requirements_matrix.py` | A row is `failed` or `unverified` |
| `QUALITY_GATE_FAILED` | 1 | `quality_gate.py` | `passed` is false |
| result `CHANGES_REQUESTED` or `BLOCKED_BY_ENV` | 1 | `review_verdict.py` | Verdict computed, not approvable |
| `REVIEW_NOT_INDEPENDENT`, `APPROVAL_WITHOUT_PASSING_GATE` | 4 | `review_verdict.py` | Independence or gate rule broken |
| `VERDICT_STALE`, `PR_NOT_OPEN` | 1 | `review_verdict.py --post` (R2) | Head moved, or PR closed |
| `POLICY_LEVEL_TOO_LOW`, `POLICY_HUMAN_ONLY`, `POLICY_ACTION_DENIED`, `POLICY_UNKNOWN_ACTION` | 4 | every `--apply` | Refused by `_skillkit.policy` |
| `IDENTITY_MISMATCH`, `UNSUPPORTED_OP` | 4 | post, dismiss (R2, R3) | Wrong token for the Review role, or op outside the allow-list |
| `GITEA_UNREACHABLE`, `GITEA_AUTH`, `GITEA_SCHEMA_DRIFT` | 3 | read/write client | External failure; no decision |
| `VERSION_CONFLICT`, `PLAN_STALE` | 1 | applier (R2) | Target or source changed since read |

## Security

- **Authority**: `_skillkit.policy` refuses before any side effect; `--apply` is never permission (CONVENTIONS §8). Review may edit test and eval code only (CONVENTIONS §7); it cannot merge.
- **Independence**: proven by session ids and `Claude-Session:` trailers (R1), plus forge logins and commit paths (R2). Identity alone is never proof (SPEC-201 synthesis D-12).
- **Untrusted text**: PR bodies, comments, verdict comments, evidence, and fixtures are data, parsed with the strict JSON reader, never evaluated, never passed to a shell; the rendered comment quotes them as data.
- **Live keys**: the reviewer holds none; the three names are checked by name and never printed or read for value.
- **Secrets**: `GITEA_TOKEN` only from the environment, redacted by `_skillkit.redact`.
- **Own gates**: `skills/review-verifier/**` is a critical policy path, so a diff touching it is `critical` and needs a human merge.
- **Writes**: never inside the skill folder; local state only under `--state-dir`, output only under `--out`.

## Runtime compatibility

| Runtime | Discovery and invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/review-verifier` in a trusted worktree; Review profile | One Ollama Cloud model through the signed-in local Ollama app (`http://localhost:11434`; SPEC-201 FR-039) | No structured outputs: scripts emit the JSON, the model relays it. One script per step |
| Zed Agent + local Ollama (after L1) | same | Local model ids once SPEC-202's L1 gate is `ENABLED` | `num_ctx` >= 32,768; SKILL.md <= 250 lines |
| Claude Code | `.claude/skills/review-verifier`; `/review-verifier` | Claude models | Hosts the independent reviewer session (no live keys) |
| Codex | `.agents/skills/review-verifier`; `$review-verifier` | Codex models | Gitea calls may be sandboxed and exit 3 |

## Assumptions

- SPEC-201 delivers `_skillkit.gitrepo.session_trailers`, `checks`, `policy`, and `jsonschema_mini` (T017, T020) before T091; SPEC-202 delivers `plan_apply`, `mutations`, and the hardened `gitea` client.
- The golden feature's Traceability table is the R1 source of requirement-to-verification mapping.
- `review_collect.py` (speckit-development) is the consumer that proves the comment format; the format is owned here.
