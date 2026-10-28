# Feature Specification: R2 Agent implementation mode

**Feature Branch**: `release/r2-agent-implementation`

**Spec ID**: SPEC-202

**Created**: 2026-10-22

**Status**: Draft (delivery step 3); aligned on 2026-10-22 with SPEC-105 and the person's final decisions
([synthesis.md](synthesis.md) §8)

**Parent**: [SPEC-200 release roadmap](../200-release-roadmap/spec.md) | **Previous**: [SPEC-201 R1 Shadow](../201-release-shadow/spec.md) | **Next**: SPEC-203 (R3 Guarded autonomous)

**Companion documents**: [release-plan.md](release-plan.md) (step 1), [synthesis.md](synthesis.md) (step 2;
findings F-n, decisions D-n, verifications V-n, questions Q-n), [plan.md](plan.md) (step 4), [tasks.md](tasks.md),
[traceability.json](traceability.json)

**Input**: Roadmap SPEC-200, row R2: "PSE branches, codes, tests, pushes its own branch, and opens a PR. Lead
creates issues and dependencies. Review posts reviews. Leases are enforced. Merge stays human (the merge gate
never returns `AUTO_MERGE`)." Inference track L1: "Local Ollama profiles ship disabled. They are enabled only
after the C1 gates pass on 3 consecutive benchmark runs, the user confirms the output matches their intent,
and the same suite then passes on `--runtime ollama-local`." The person's decisions of 2026-10-22 (SPEC-201
§Clarifications and refinement ledger; SPEC-105) make this concrete: the C1 gates are SPEC-105's floor gates; "3
consecutive benchmark runs" is SPEC-105's `benchmark-streak.v1` with `local_unlock_evidence: true`; a release merges
only after one fully passing counting live run; the releases ship as stacked PRs (intake A4): R2's branch is created
from `release/r1-shadow` once R1 has an `APPROVE` verdict and its live gates passed, its PR targets `release/r1-shadow`
and is retargeted to `main` when R1 merges, R3 stacks on R2 the same way, and merges happen in order R1 → R2 → R3,
each by a human (§Clarifications).

## Intent

R1 proved that the Lead, PSE, and Review roles can analyse real work and plan every write while changing
nothing. It also shipped the full 34-action catalog, so R2 changes enforcement, not vocabulary (SPEC-201
§Autonomy policy). R2 raises `policy.SUPPORTED_MAX_LEVEL` to `agent-implementation` and makes the 19 actions
at that level work for real, inside narrow, mechanically checked boundaries. The user gets real pull requests
with honest evidence and independent reviews, keeps every merge, and no agent can weaken the rules that bound
it ([R §Safe autonomous merge]). Inference stays cloud-first. Local models switch on only through a measured
gate plus the user's own sign-off. R2 itself merges only after its live gates pass on one fully passing counting live
run graded by Jev (SPEC-105), and on local runs, which happen inside one of the person's Rancher Desktop local
containers, bench has `run-monitor`, the 14th skill, watch that container from inside it (target `local-container`).

## User Scenarios & Testing *(mandatory)*

Every scenario runs offline against the Gitea test double, unless it is marked **live**. Deterministic cases use
the double in-process through `--gitea-fixture`; integration tests use the HTTP double plus a bare git remote.

### User Story 1 - PSE delivers a pull request from an isolated worktree under a lease (Priority: P1) 🎯 MVP

A PSE session that holds the lease on an issue creates its own worktree and branch, changes code only inside
the issue's write domains, runs the required checks on the commit it will report, pushes only its branch, and
opens one PR whose evidence is backed by executed commands.

**Why this priority**: This capability defines the `agent-implementation` level [R §Progressive autonomy].
Without it, nothing else in R2 has anything to review or govern.

**Independent Test**: Seed the double with one issue in `READY_FOR_BUILD`, a lease for session `pse-184-01`,
and a bare remote. Run `delivery_plan.py --apply --step` for worktree, branch, commit, push, and pr (SPEC-201's step
names), with checks in between. Exactly one PR from `agent/pse/184-<slug>` exists, every check in its evidence matches a
`check-run.v1` on the PR head with `tree_clean: true`, and the bare remote shows no other ref changed.

**Acceptance Scenarios**:

1. **Given** level `agent-implementation` and issue 184 leased to `pse-184-01` with `write_domains`
   `["src/auth/tokens/**"]` and `base_commit` B, **When** PSE runs `delivery_plan.py --issue 184 --apply --step worktree` and then
   `--step branch`, **Then** a worktree exists at `.skill-state/worktrees/184-<slug>` on new branch
   `agent/pse/184-<slug>` at B, and the `worktree-state.v1` payload reports `clean: true`.
2. **Given** committed changes inside the write domains and checks run on HEAD with a clean tree, **When** PSE
   runs `evidence_manifest.py validate`, then `--step push`, then `--step pr`, **Then** the remote's
   `agent/pse/184-<slug>` equals HEAD, one open PR targets the base branch, and its body carries the evidence
   whose every check matches a `check-run.v1`.
3. **Given** a check run on a dirty tree, or on a commit other than the evidence `head_commit`, **When** evidence is
   validated, **Then** it exits 1 with `CHECK_RAN_ON_DIRTY_TREE` or `CHECK_RAN_ON_DIFFERENT_COMMIT`, and the pr
   step refuses to open the PR.
4. **Given** a staged change to a path outside the lease's write domains, **When** `--step commit` runs, **Then**
   it exits 1 with `SCOPE_VIOLATION` and creates no commit; **given** a staged change to `.skill-policy.json`,
   **then** it exits 4 with `POLICY_PATH_TOUCHED`.
5. **Given** no lease, an expired lease, or a lease held by another session, **When** any delivery step runs with
   `--apply`, **Then** it exits 4 with `LEASE_REQUIRED`, `LEASE_EXPIRED`, or `LEASE_HELD_BY_OTHER`.
6. **Given** the PR already exists for this head branch, **When** `--step pr` runs again, **Then** no second PR is
   created (`already_applied`), and the body is updated (`gitea.pr.update`) only if the evidence digest changed.
7. **Given** level `shadow`, **When** any `--step` runs with `--apply`, **Then** it exits 4 with
   `POLICY_LEVEL_TOO_LOW` (R1 behaviour).
8. **Given** a request to push a ref other than the leased branch, or a plan carrying a force flag, **When**
   `--step push` runs, **Then** it exits 4 with `BRANCH_NOT_OWNED` or `FORCE_PUSH_REFUSED` and contacts no remote.
9. **Given** the session hands off, **When** `checkpoint.py publish --apply` runs twice, **Then** exactly one
   checkpoint comment with a `skill-lab:session-checkpoint:v1` marker is on the issue.

---

### User Story 2 - Review posts an independent verdict, and the merge stays human (Priority: P2)

Review submits its verdict as a Gitea pull-request review from its own identity. It does so only after proving it
is independent of the author, by session (R1's rule) and by forge identity (R2's rule), and that it reviewed the
current head. The merge gate audits branch protection and never recommends an automatic merge.

**Why this priority**: Independent review and human merge are what make US1 safe to run [R §Review contract;
RM row R2].

**Independent Test**: With US1's PR, post an `APPROVE` verdict as `agent-review` with
`review_verdict.py --comment-plan --post --apply`, then run `merge_decision.py`. One `APPROVED` review carries the verdict JSON,
the decision is `HUMAN_APPROVAL_REQUIRED` with `uncapped_decision: AUTO_MERGE` and reason
`CAPPED_BY_AUTONOMY_LEVEL`, and the double logs zero merge calls.

**Acceptance Scenarios**:

1. **Given** PR 211 with head H authored by `agent-pse`, and an `APPROVE` verdict for H from session
   `review-211-01` with a passing quality gate, **When** `review_verdict.py --comment-plan --post --apply` runs with the
   `agent-review` token, **Then** one review with event `APPROVED` exists whose body carries the verdict under
   R1's `skill-lab:review-verdict:v1` marker, and `review-post.v1` reports `status: posted`.
2. **Given** the reviewer login equals the PR author, or authored or committed any PR commit, or equals the
   configured PSE login, or the verdict's `reviewer_session` appears in a `Claude-Session:` trailer or authoring session
   of the PR, **When** it posts, **Then** it exits 4 with `REVIEW_NOT_INDEPENDENT`, and nothing is posted.
3. **Given** the PR head moved from H to H2 after the review, **When** the H verdict is posted, **Then** it exits 1
   with `VERDICT_STALE`.
4. **Given** an `APPROVE` verdict with `quality-gate.passed: false`, **When** it posts, **Then** it exits 4 with
   `APPROVAL_WITHOUT_PASSING_GATE`.
5. **Given** a low-risk PR whose every gate passes at level `agent-implementation`, **When** `merge_decision.py`
   runs, **Then** `decision` is `HUMAN_APPROVAL_REQUIRED`, `uncapped_decision` is `AUTO_MERGE`, `reasons` includes
   `CAPPED_BY_AUTONOMY_LEVEL`, and no merge request is sent. `merge_plan.py --apply` exits 4.
6. **Given** branch protection identical to the report's recommended `main` policy, **When** `branch_audit.py`
   runs, **Then** `compliant: true`; **given** `required_approvals: 0`, **then** `compliant: false` with BP-04
   `fail`; **given** a field the API omits, **then** that rule is `unknown` and `compliant: false`.
7. **Given** no `review-post.v1` for the current head, **When** `merge_decision.py` runs, **Then** the decision is
   `BLOCKED` with the review gate `not_run`.

---

### User Story 3 - The Lead populates and drives the board idempotently (Priority: P2)

The Lead applies R1's dry-run plans: issues, dependencies, labels, milestones, assignments, leases, and board
transitions. Every command can be re-run, or resumed after a crash, without creating duplicates.

**Why this priority**: US1 needs issues and leases to exist. Idempotency is the report's main defence against
repeated writes in long-horizon operation [R §Gitea as the real-time engineering control plane].

**Independent Test**: Apply the golden feature's `gitea-plan` to an empty repository on the double, re-run it, then
inject a crash after every operation index in turn and resume. The final state always has exactly one issue per
planned task and one dependency per planned edge, and the second run adds zero writes.

**Acceptance Scenarios**:

1. **Given** the golden plan and an empty repository, **When** `tasks_to_issues.py --apply` runs, **Then** the
   created issues equal the plan's `create_issue` operations, the created dependencies equal its dependency
   operations, and `task-issue-map.v1` is written. **When** it runs again, **then** it makes 0 writes, and every
   operation is `already_applied`.
2. **Given** a *closed* issue titled `T004: <description>` exists, **When** the plan applies, **Then** no issue is
   created for that task, and the map points at the closed issue.
3. **Given** a fault injected after operation k (for every k from 1 to the plan length), **When** the apply is re-run,
   **Then** the final state has 0 duplicate issues, dependencies, or labels.
4. **Given** `tasks.md` changed after the plan was computed, **When** apply runs, **Then** it exits 1 with
   `PLAN_STALE` before any write.
5. **Given** an issue in `READY_FOR_BUILD` whose dependencies are closed and whose write domains overlap no
   active lease, **When** `dispatch_recommend.py --apply` runs, **Then** the issue is assigned to the PSE identity,
   an active lease holds `base_commit`, the label is `state/in-progress`, and a lease mirror comment exists. A
   re-run makes no further writes.
6. **Given** an open dependency, or a write-domain overlap with another active lease, **When** dispatch runs,
   **Then** it exits 1 with `DEPENDENCY_OPEN` or `WRITE_SET_CONFLICT` and writes nothing.
7. **Given** a `transition-decision` computed before the issue's labels changed, **When**
   `labels_plan.py --apply` runs, **Then** it exits 1 with `PLAN_STALE`; **given** actor role `pse` for a transition
   whose `required_role` is `review`, **then** it exits 4 with `ROLE_NOT_AUTHORIZED`.
8. **Given** a drift comment plan, **When** `comment_plan.py --apply` runs twice, **Then** each comment exists
   exactly once.
9. **Given** a PR that a human merged, **When** `complete_issue.py --apply` runs, **Then** the issue is labelled
   `state/done`; if the issue is still open, the payload reports `CLOSE_PENDING` (closing is R3 or human); and the
   payload lists the issues whose dependencies are now all closed, without dispatching them.

---

### User Story 4 - `/speckit-development` delivers a feature end to end (Priority: P3)

The user runs `/speckit-development` (Zed, Claude Code) or `$speckit-development` (Codex) on a feature or an issue.
The skill walks preflight, worktree, the task loop (R1's `dev_state.py`), converge, commit, checks and evidence on the
committed head, push, PR, and review request. Each step is one tool call, and the delivery is resumable from `delivery-record.v1`.

**Why this priority**: It is the execution command the user asked for. It composes US1–US3, so it comes after them.

**Independent Test**: On the double, run the full golden flow: tasks_to_issues apply, dispatch, speckit-development
delivery, the review request, a review through a stub `claude` CLI via R1's `review_local.py`, the verdict posted by
the Review identity, and the merge decision. Then interrupt after each step in turn and resume. The record reaches
`handoff` every time, with no duplicate side effect.

**Acceptance Scenarios**:

1. **Given** the golden feature applied to Gitea and level `agent-implementation`, **When** the delivery runs for one
   issue, **Then** `delivery-record.v1` shows every step through `review_request` as `done`, one PR exists, the
   Review identity is a requested reviewer (`--step review-request`), the review dispatch exists
   (`--step review-session`), and a `review-request.v1` with forge `gitea` is recorded.
2. **Given** an interruption after any step, **When** the same `--delivery-id` is resumed, **Then** execution
   continues at the first step that is not `done`, and no completed side effect repeats.
3. **Given** converge still reports findings after 3 passes, **When** the converge step finishes, **Then** the record
   shows `NOT_CONVERGED`, the script exits 1, `next_action` escalates to Lead, and nothing is pushed.
4. **Given** forge `github` (the factory repository, which runs at `shadow`), **When** `--step pr` runs without
   `--apply`, **Then** only a `pr-request.v1` is written under `--out`, no network call is made, and `next_action` is
   `orchestrator.create_pr`.
5. **Given** review mode `cli` and no `claude` executable, **When** `review_local.py --apply` runs, **Then** it exits 3
   with `CLAUDE_CLI_NOT_FOUND`, and the delivery records no verdict.
6. **Given** a fourth review round, **When** `review_request.py` runs, **Then** it exits 4 with
   `REVIEW_ROUNDS_EXHAUSTED` (R1 rule), and `next_action` is a human decision.
7. **Given** any outcome, **When** delivery ends, **Then** no merge was requested, and the final `next_action` is a
   human merge, or a PSE fix after `CHANGES_REQUESTED`.

---

### User Story 5 - Local inference is enabled only by a measured gate and the user's sign-off (Priority: P3)

After Ollama Cloud proves reliable, the user reviews sample outputs and signs off, and the same suite then passes
on local Ollama. Only then can the local Zed profiles be installed. Cloud stays available as the fallback.

**Why this priority**: The user asked for local inference after cloud is reliable. The mechanism must exist in R2,
but switching it on depends on live runs and on the user, so it is milestone M-L1, not a merge blocker.

**Independent Test**: Run `skill-lab gate l1` over a fixture matrix of benchmark runs and sign-offs. The decision is
correct for every row, and `skill-lab install --runtime zed --inference local` succeeds only for the
`ENABLED` row.

**Acceptance Scenarios**:

1. **Given** a SPEC-105 `benchmark-streak.v1` for cloud model M with `local_unlock_evidence: true` on the current
   suite digest, an `approve` sign-off by `Cazador0` bound to the streak's run ids and digests, and 3 consecutive
   counting `ollama-local` runs of local model L on the same suite digest that each pass every floor gate, **When**
   `skill-lab gate l1 --model L` runs, **Then** the decision is `ENABLED`, and the installer adds the local profiles
   (local model ids on the same `ollama` provider) while keeping the cloud profiles.
2. **Given** a cloud streak shorter than 3, a model change, a suite-digest change, an unstable case, a missing,
   rejected, or mismatched sign-off, or a local run that fails a floor gate, **When** the gate runs, **Then** the
   decision is `NOT_ENABLED` with that specific reason code, and the installer exits 4 with `LOCAL_INFERENCE_GATED`
   (R1 code). **Given** a replay, partial, outage, or degraded run, **then** that run neither extends nor breaks either
   streak, and its exclusion reason is listed (SPEC-105 FR-011).
3. **Given** a local run recorded with `structured_output: "format"`, **When** the gate runs, **Then** that run is
   ineligible with reason `FORMAT_ENFORCED`. **Given** a local model configured with context 4096, **When**
   `skill-lab doctor --runtime ollama-local` runs,
   **Then** it fails with `NUM_CTX_TOO_SMALL` and tells the user to set 32768.
4. **Given** the local endpoint is unreachable during a local benchmark, **When** cases run, **Then** they are
   `errored` with `OLLAMA_UNREACHABLE`, the run does not count (`outage`), and the bench never falls back to cloud.
5. **Given** a later counting local run fails its gates, **When** the gate is re-evaluated, **Then** it becomes
   `NOT_ENABLED`, and `install --check` reports the drift and recommends the cloud profiles.
6. **Given** a local parity run inside one of the person's Rancher Desktop local containers, **When** bench runs
   `run-monitor` `snapshot` after each skill, **Then** it passes `--target local-container`: the report's CPU and
   memory figures come from that container's own cgroup limits and use, disk free and process count are those seen
   inside the container, the API and session figures are computed from the run log, and no Docker or containerd socket
   and nothing outside the container is read (§Clarifications; synthesis Q-10, D-27).

---

### User Story 6 - Live Gitea smoke test before the first live write (Priority: P4)

When the user configures a real Gitea, a staged smoke test proves the client's assumptions on a sandbox repository
and unlocks live writes for that host.

**Why this priority**: The user decided "test double now, live later". This story makes "later" safe without
blocking today.

**Independent Test**: Run the smoke stages against the HTTP double posing as a non-loopback host. The report passes
with complete cleanup, and the client's live-write guard then allows writes to that host.

**Acceptance Scenarios**:

1. **Given** no `GITEA_URL` or `GITEA_TOKEN`, **When** `skill-lab smoke gitea` runs, **Then** it exits 3 with
   `GITEA_NOT_CONFIGURED`, and the report says `not_run` with the reason.
2. **Given** `--repo acme/factory` (not a sandbox name), **When** it runs, **Then** it exits 4 with
   `SMOKE_REPO_NOT_SANDBOX`.
3. **Given** a sandbox repository, **When** the `lead`, `pse`, `review`, and `cleanup` stages run, each with its own
   token, and every step passes, **Then** `smoke-report.v1` has `passed: true` and `cleanup_complete: true`, and
   consequential writes to that host are allowed from then on.
4. **Given** the instance's swagger lacks an endpoint the client uses, **When** the swagger check runs, **Then** it
   fails and names the endpoint, and live writes stay refused.

### Edge Cases

- A PSE edits `.skill-policy.json` in its worktree to raise the level: the committed copy on the base branch still
  says the old level, so the effective level is the lower of the two (FR-002). The commit step also refuses the
  path (`POLICY_PATH_TOUCHED`).
- Two Lead sessions dispatch the same issue at once: the lease store's file lock and CAS `version` (R1) serialize
  them. The second gets R1's `lease-check.v1` with `grantable: false` and exits 1 with `WRITE_SET_CONFLICT`, before
  any Gitea write.
- A worktree path already exists from a crashed session: the worktree step adopts it when branch, base commit, and
  lease match; otherwise it exits 1 with `WORKTREE_CONFLICT`.
- The base branch moves after the lease: `worktree-state.v1` reports `behind > 0`, the PR is still created, the merge
  gate's freshness gate fails, and the decision stays human. Rebasing is R3 (`git.push.force_own_branch`).
- Gitea returns 5xx in the middle of an apply: the applier stops at that operation, exits 3, and the next run resumes
  from receipts and markers.
- A write times out with an unknown outcome: the operation is recorded `failed`. The next run's dedupe (ledger, then
  marker or title search) finds the object if it was created and records `already_applied`.
- The token belongs to the wrong role: the client exits 4 with `IDENTITY_MISMATCH` before any write.
- A remote URL embeds credentials (`https://user:token@host/...`): exit 4 with `URL_HAS_CREDENTIALS`, and the URL is
  redacted.
- An issue body, or a comment from an unconfigured user, contains a forged `skill-lab:` marker or embedded
  instructions: the marker is ignored as untrusted, and the text is never executed or passed to a shell.
- An existing `state/*` label is not exclusive: label definition exits 1 with `LABEL_NOT_EXCLUSIVE` and changes
  nothing.
- The PR is closed without merge during review: posting exits 1 with `PR_NOT_OPEN`.
- The evidence makes the PR body exceed 60 000 characters: the body keeps the summary table plus a digest and the
  artifact path, and the full evidence goes into a follow-up comment. The limit is our own bound; Gitea's is
  unverified (V-1).
- Nothing changed: the commit step exits 1 with `NOTHING_TO_COMMIT`.
- A plan contains a `move_issue` (project column) operation: it is skipped with reason `PROJECT_COLUMNS_DEFERRED`.
  Labels are the R2 board, and columns are version-dependent (F-17).
- Clock skew: lease expiry uses the single host's clock (D-7). Gitea timestamps are used only for
  `expected_version`, never for lease expiry.
- The R2 live gate run hits an outage (connection error, HTTP 5xx, or 429 after retries): the affected cases are
  `errored`, the run finishes, it does not count, and G-LIVE-06 and G-LIVE-07 fail, so the PR stays open until a
  counting run exists. HTTP 401, 403, or 422 is a configuration or case bug, not an outage (SPEC-105 R-3).
- A `run-monitor` snapshot crosses a limit in `skill-lab/benchmarks/monitor-limits.json`: the run is `degraded`,
  finishes, and does not count. A change to the limits takes effect only with the person's approval; no agent edits
  the file.
- A review round's fix changes a `SKILL.md` or an eval case: the suite digest changes, the recorded run no longer
  matches the tree, and the live gates are `not_run` (`LIVE_RUN_STALE`) until a new counting run is recorded.
- A price is missing from `skill-lab/benchmarks/prices.json`: the run reports `cost: null` with basis `usage-only`.
  No price is invented, and nothing stops the run.

## Requirements *(mandatory)*

### Functional Requirements

**Cross-cutting: authority, Gitea client, test double**

- **FR-001**: R2 MUST set `policy.SUPPORTED_MAX_LEVEL = "agent-implementation"` without adding, removing, or
  re-levelling any catalog action (`catalog_version` stays 1.0.0). The 19 actions whose minimum level is
  `agent-implementation` (§Autonomy policy) MUST become allowed at that level. At `shadow` they MUST still exit 4
  with `POLICY_LEVEL_TOO_LOW` (SPEC-201 FR-004, FR-007).
- **FR-002**: When the declared level is above `shadow`, `policy.load` MUST also read the committed
  `.skill-policy.json` from the base ref `refs/remotes/origin/<base_branch>`, using read-only `_skillkit.gitrepo`.
  `base_branch` comes from `.skill-gitea.json`, default `main`, and a base ref under `agent/` is refused. The
  effective level MUST be the lowest of the working-tree level, the base-ref level, and `SUPPORTED_MAX_LEVEL`. A
  missing, unreadable, or invalid base copy MUST yield `shadow` with warning `POLICY_NOT_ON_BASE`. This is the
  base-branch verification SPEC-201 requires before R2 raises the clamp.
- **FR-003**: The 5 `human-only` actions MUST exit 4 with `POLICY_HUMAN_ONLY` at every level for every role. The
  7 `guarded-autonomous` actions MUST exit 4 with `POLICY_LEVEL_TOO_LOW` at `agent-implementation`.
- **FR-004**: `_skillkit.gitea.GiteaClient.send(operation)` MUST accept an operation only if its
  (`action`, `method`, path template) matches a row of the R2 endpoint table (plan.md §Endpoint table). Anything else
  MUST be refused with `UNSUPPORTED_OP` (exit 4) before a connection opens. The table MUST contain no merge
  endpoint, and the client MUST expose no generic request method.
- **FR-005**: Every consequential write MUST follow this sequence:
  1. Check policy and identity.
  2. Look up the idempotency ledger and markers.
  3. Re-read the target and compare `expected_version` (`updated_at` as Unix seconds) and
     `params.expected_state_digest`.
  4. Write.
  5. Re-read and verify.
  6. Record a `mutation-receipt.v1`.

  A repeated idempotency key MUST return the stored receipt with `already_applied` and make no second write. A
  version mismatch MUST exit 1 with `VERSION_CONFLICT`.
- **FR-006**: The transport MUST read `GITEA_URL` and `GITEA_TOKEN` from the environment. It MUST require HTTPS except
  for loopback hosts, paginate list endpoints until an empty page, retry idempotent reads at most 3 times (honouring
  `Retry-After`), and never retry a write blindly. Network errors and 5xx MUST map to exit 3 `GITEA_UNREACHABLE`,
  401 and 403 to exit 3 `GITEA_AUTH`, and a response missing a field the client reads to exit 3
  `GITEA_SCHEMA_DRIFT`.
- **FR-007**: `.skill-gitea.json` (`gitea-project.v1`) MUST map the roles lead, pse, and review to Gitea logins and git
  emails. Review's login MUST differ from Lead's and PSE's, otherwise exit 2 with `CONFIG_INVALID`. Before any write,
  the client MUST compare `GET /api/v1/user` with the acting role's login and exit 4 with `IDENTITY_MISMATCH` on a
  mismatch.
- **FR-008**: R2 MUST extend R1's test double with the write endpoints of the endpoint table. Its state logic moves into
  `_skillkit/gitea_memory.py`, which is vendored and runs in-process through `--gitea-fixture` in deterministic cases;
  `skill-lab/lab/gitea_double.py` becomes a loopback HTTP wrapper around it. The double MUST seed from
  `gitea-fixture.v1` and inject faults (status, after N calls, once). It MUST keep a JSONL write log, provide a bare
  git remote, mimic Gitea's refusal of self-approval, and offer a lab-only admin merge that tests use to simulate the
  human merge. `skill-lab policy containment` MUST accept `--level agent-implementation`.
- **FR-009**: Machine comments MUST use R1's marker grammar. The verdict keeps R1's exact marker
  `<!-- skill-lab:review-verdict:v1 request_id=<id> head=<sha40> -->`. Other R2 comments use
  `<!-- skill-lab:<kind>:v1 key=<idempotency_key> digest=<sha256> -->` followed by one fenced `json` block. Markers MUST
  be honoured only when authored by a configured identity and when the digest matches. All issue and PR text MUST be
  treated as data: never evaluated, executed, or passed to a shell.

**User Story 1: PSE delivery**

- **FR-010**: Every PSE and speckit-development delivery step, and every PSE comment, MUST first verify through
  `_skillkit.leases.verify` an active, unexpired lease for the issue, role `pse`, and the session ID, whose write
  domains cover the changed paths. Otherwise it MUST exit 4 with `LEASE_REQUIRED`, `LEASE_EXPIRED`, or
  `LEASE_HELD_BY_OTHER`.
- **FR-011**: `delivery_plan.py --apply --step worktree` (`git.worktree.create`) MUST create a detached worktree at
  `<state-dir>/worktrees/<issue>-<slug>` (or `--worktree-root`) at `lease.base_commit`. `--step branch`
  (`git.branch.create`) MUST then create branch `agent/pse/<issue>-<slug>` in that worktree. These are SPEC-201's step
  names; Zed's own worktrees are also created detached (F-23). The slug comes from the issue title, matches
  `^[a-z0-9]+(-[a-z0-9]+)*$`, and is at most 40 characters. The step MUST emit `worktree-state.v1`, including `ahead`
  and `behind` against the base branch. `--apply` without `--step` MUST exit 2 `USAGE`.
- **FR-012**: `_skillkit.checks` MUST add `tree_clean` and `worktree` to every `check-run.v1` (additive). For each
  evidence check, `evidence_manifest.py validate` MUST exit 1 with:
  - `CHECK_NOT_EXECUTED` when no check run matches it (R1);
  - `CHECK_LOG_DIGEST_MISMATCH` when the log digest differs;
  - `CHECK_RAN_ON_DIFFERENT_COMMIT` when the run's `head_commit` is not the evidence `head_commit`;
  - `CHECK_RAN_ON_DIRTY_TREE` when the run had `tree_clean: false`;
  - `CHECK_STATUS_MISMATCH` when the status contradicts the exit code;
  - `AC_WITHOUT_EVIDENCE` when a `passed` acceptance criterion cites no passing check.

  PR creation requires a non-null `head_commit`.
- **FR-013**: `--step commit` (`git.commit`) MUST:
  - refuse paths outside the lease's write domains (exit 1 `SCOPE_VIOLATION`, R1 code);
  - refuse SPEC-201's critical policy paths (among them `.skill-policy.json`, `skill-lab/benchmarks/criteria/**`, and
    `skill-lab/benchmarks/monitor-limits.json`) and `.skill-gitea.json` (exit 4 `POLICY_PATH_TOUCHED`);
  - refuse the base branch or any non-`agent/pse/` branch (exit 4 `PROTECTED_BRANCH`);
  - never pass `--no-verify` and never amend a pushed commit;
  - author the commit with the PSE login and git email, and add the `Issue`, `Spec`, `Tasks`, and
    `Claude-Session` or `Session` trailers.
- **FR-014**: `--step push` (`git.push.branch`) MUST:
  - push only `refs/heads/B:refs/heads/B`, where B is the leased branch, with no force flag (exit 4
    `BRANCH_NOT_OWNED`, `FORCE_PUSH_REFUSED`);
  - require the remote host to equal the `GITEA_URL` host (exit 4 `REMOTE_HOST_MISMATCH`). A `file://` remote is
    accepted only when `GITEA_URL` is a loopback host (the test double's bare remote). The host guard of FR-041 applies
    to pushes as it does to API writes;
  - refuse remote URLs that contain credentials (exit 4 `URL_HAS_CREDENTIALS`);
  - report a non-fast-forward rejection as exit 4 `PUSH_NON_FAST_FORWARD`;
  - verify the remote ref with `git ls-remote` after pushing.
- **FR-015**: `--step pr` (`gitea.pr.create`, `gitea.pr.update`) MUST build a `pr-request.v1` from the issue contract
  and the validated evidence (title, body from `assets/templates/pr-body.md`, evidence block, `Closes #<issue>`). It
  MUST refuse when evidence is invalid for the head, and create the PR idempotently by head branch (an existing open
  PR means `already_applied`). It MUST update title and body only when the evidence digest changed, and verify head
  SHA and base after writing.
- **FR-016**: `checkpoint.py publish --apply` (`gitea.comment.create`) MUST post a `session-checkpoint.v1` as a marked
  issue comment. It MUST deduplicate by digest, redact secrets, and, for role `pse`, require the lease.

**User Story 2: Review and merge gate**

- **FR-017**: `review_verdict.py --comment-plan --post --apply` (`gitea.pr.review.submit`, `gitea.comment.create`) MUST submit the
  verdict as a Gitea PR review: `APPROVE` → `APPROVED` (only when `quality-gate.passed` is true, else exit 4
  `APPROVAL_WITHOUT_PASSING_GATE`), `CHANGES_REQUESTED` → `REQUEST_CHANGES`, `BLOCKED_BY_ENV` → `COMMENT`. The body is
  R1's rendered verdict comment. Posting MUST be idempotent per (PR, reviewed commit, verdict digest) and MUST emit
  `review-post.v1`.
- **FR-018**: Before posting, the independence check MUST exit 4 with `REVIEW_NOT_INDEPENDENT` when:
  - SPEC-201 FR-035's session rule fails (reviewer session ID in a `Claude-Session:` trailer of `base..head`, or equal
    to the author session); or
  - the reviewer login equals the PR author, any PR commit's author or committer login, or the configured PSE
    login; or
  - the PR contains commits by the reviewer outside test and eval paths.
- **FR-019**: At post time, `reviewed_commit` MUST equal the PR's current head (else exit 1 `VERDICT_STALE`, R1 code),
  and the PR MUST be open (else exit 1 `PR_NOT_OPEN`).
- **FR-020**: At `agent-implementation`, `merge_decision.py` MUST keep `decision` at most `HUMAN_APPROVAL_REQUIRED`,
  record `uncapped_decision`, and add reason `CAPPED_BY_AUTONOMY_LEVEL` whenever the uncapped decision is
  `AUTO_MERGE`. `merge_plan.py --apply` MUST still exit 4 (`gitea.pr.merge_when_checks_succeed` is
  `guarded-autonomous`).
- **FR-021**: `branch_audit.py` MUST read the base branch's protection and evaluate BP-01..BP-12 (§Release gates)
  through `assets/branch-policy-map.json`, emitting `branch-protection-audit.v1`. A field the API omits MUST be
  `unknown`, and `unknown` MUST never count as `pass`. `compliant` is true only when every required rule passes.
  `BRANCH_PROTECTION_NONCOMPLIANT` is exit 1.
- **FR-022**: `merge_decision.py` MUST take `review-post.v1`, `quality-gate.v1`, and `branch-protection-audit.v1` as
  gates. A missing review post or quality gate for the current head MUST yield `BLOCKED` with that gate `not_run`. At
  `agent-implementation` the branch audit is advisory: a non-compliant audit MUST add reason
  `BRANCH_PROTECTION_NONCOMPLIANT` with the audit digest, MUST NOT be listed in `gates[]` (merge-decision.v1 forces
  `BLOCKED` whenever a listed gate is `fail`), and keeps the decision at most `HUMAN_APPROVAL_REQUIRED`. Every emitted
  decision MUST validate against merge-decision.v1. SPEC-203 turns the audit into a real gate at `guarded-autonomous`. R2 adds `.skill-gitea.json` to SPEC-201's critical-path list, because it defines the
  role identities and the base branch, so a diff touching it is `critical`.

**User Story 3: Lead control plane**

- **FR-023**: `tasks_to_issues.py --apply` MUST execute its `gitea-plan` through the shared plan applier
  (`_skillkit.plan_apply`) with the op allow-list `define_label`, `create_issue`, `update_issue`, `set_labels`,
  `set_milestone`, and `set_dependency`. The exact op names follow SPEC-201's plan vocabulary, and T005 records them.
  Immediately before each create, it MUST re-check dedupe: map entry first, then the title regex `^T\d{3,}:` across
  open and closed issues. It MUST create dependencies only when absent, journal the map atomically after every op,
  and emit `apply-report.v1` plus `task-issue-map.v1`. A re-run MUST make 0 writes.
- **FR-024**: The plan applier MUST refuse with `PLAN_STALE` (exit 1) when the source digest the plan recorded (for
  example the `tasks.md` digest) differs from the current one. It MUST call `require()` for every op's action before
  the first side effect (SPEC-201 FR-007), stop at the first operation that does not succeed, and leave earlier
  operations recorded and resumable.
- **FR-025**: `labels_plan.py --apply` (`gitea.labels.set`) MUST recompute the transition with `transition.py` from live
  Gitea state, and refuse with `PLAN_STALE` on any difference from the input decision. It MUST require
  `allowed: true`, every precondition met, `actor_role` equal to `required_role` (else exit 4 `ROLE_NOT_AUTHORIZED`),
  and the current `state/*` label equal to `from_state`. It MUST replace only the `state/*` label. The precondition for
  entering `REVIEW` MUST be a `success` combined commit status, or `ci: "none"` declared in `.skill-gitea.json`.
- **FR-026**: `dispatch_recommend.py --apply` (`gitea.issue.assign`, `lease.write.remote`, `gitea.labels.set`, and
  `state.write.local` for the local lease) MUST follow the report's claiming sequence:
  1. Re-read the issue and its dependencies.
  2. Refuse when the issue is not `READY_FOR_BUILD` (`STATE_NOT_READY`), dependencies are open (`DEPENDENCY_OPEN`),
     write domains overlap an active lease (`WRITE_SET_CONFLICT`), or no parseable issue contract exists
     (`CONTRACT_MISSING`). All four are exit 1.
  3. Assign the PSE identity.
  4. Acquire the local lease with `base_commit` and `branch`.
  5. Transition to `IN_PROGRESS`.
  6. Mirror the lease.

  It MUST emit `apply-report.v1`, and a re-run MUST resume idempotently.
- **FR-027**: `lease.py acquire|renew|release --mirror --apply` (`lease.write.remote`, SPEC-201 `gitea-plan` op `mirror_lease`) MUST post a marked lease comment.
  Acquire MUST refuse with exit 1 `LEASE_MIRROR_CONFLICT` (a `lease-check.v1` with `grantable: false`, matching R1's
  acquire-conflict semantics) when the issue shows an unexpired active mirror from another session. The local store
  stays the authority (single host).
- **FR-028**: `comment_plan.py --apply` (sync) and `arbitrate.py --publish --apply` (lead) MUST post their comments
  (`gitea.comment.create`) through the plan applier with op `create_comment` only, deduplicated by marker, and never
  modify `tasks.md`, `spec.md`, or the map.
- **FR-029**: `complete_issue.py --apply` (`gitea.labels.set`) MUST verify through the API that the PR is merged, set
  `state/done`, and report `CLOSE_PENDING` if the issue is still open, because `gitea.issue.close` is
  `guarded-autonomous`. The PR body's `Closes #<issue>` lets the human merge close it. The step MUST list the issues
  whose dependencies are now all closed, without dispatching them.

**User Story 4: speckit-development**

- **FR-030**: `speckit-development` MUST run the 13 steps preflight, worktree, branch, implement, converge, commit,
  checks, evidence, push, pr, review_request, review_verdict, and handoff, in that order, each as one tool call. The
  checks step runs on the committed head with a clean tree, because only such runs count as evidence (D-9, FR-012); the
  per-task `dev_state.py check` runs inside implement are task verification, not PR evidence. State MUST be recorded in
  `delivery-record.v1` through the new `delivery_record.py`, and resume MUST start at the first step that is not
  `done`. Preflight MUST require effective level `agent-implementation`, a held lease, and `spec-readiness.ready`.
  The worktree, branch, commit, push, and pr steps MUST run through `delivery_plan.py --apply --step`, sharing
  `_skillkit.delivery` with pse-implementer.
- **FR-031**: Task marking stays R1's `dev_state.py mark`: `[x]` only with passing check runs. Converge MUST run at most
  3 passes. If findings remain, the step MUST record `NOT_CONVERGED`, exit 1, set `next_action` to escalate to Lead,
  and skip commit and push.
- **FR-032**: On forge `gitea`, speckit-development's `delivery_plan.py --apply --step review-request` MUST request
  the Review login as a reviewer (`gitea.pr.review.request`). `--step review-session` (`review.session.request`) MUST
  write the review dispatch for a separate session: R1's `review_request.py --render-prompt` output, PR, head, spec
  IDs, and request ID, for an agent with a session-spawn tool. `review_request.py` itself stays R1's document
  producer. Without such a tool, R1's `review_local.py --apply` (`review.local.run`) is the fallback, and its
  verdict records `reviewer.mode: cli-fallback`. The 3-round limit of SPEC-201 FR-034 still applies.
- **FR-033**: With forge `gitea`, `--apply --step pr` MUST create the PR through the client. With forge `github`,
  `--step pr` MUST only write `pr-request.v1` under `--out` and set `next_action: orchestrator.create_pr`, making no
  network call. Because writing under `--out` changes nothing outside the machine (SPEC-201), this works without
  `--apply` and at every level, including `shadow`; with `--apply` on forge `github` it exits 4 `UNSUPPORTED_OP`,
  because skills never write to GitHub (D-4).
- **FR-034**: `speckit-development` MUST NOT request a merge. The handoff step MUST record the merge decision (at most
  `HUMAN_APPROVAL_REQUIRED`) and set `next_action` to a human merge, or to a PSE fix after `CHANGES_REQUESTED`.

**User Story 5: L1 local inference**

- **FR-035**: `skill-lab signoff create` MUST write a `human-signoff.v1` under `skill-lab/benchmarks/signoff/`. It is
  interactive: it shows the bound runs and sample outputs, requires a typed confirmation, binds the run IDs and
  digests, and records the signer with `created_with.interactive: true`. The signer is the person's GitHub username,
  `Cazador0` (`signer.github_login`; SPEC-201 refinement, set 1). `skill-lab signoff verify` MUST recompute the bound
  digests. No skill script creates a sign-off.
- **FR-036**: `skill-lab gate l1 --model <m>` MUST compute a deterministic `inference-gate.v1` per `(runtime, model)`
  under D-17. It MUST recompute every streak with SPEC-105's `lab.streak` from the committed runs under
  `skill-lab/benchmarks/runs/`, and never trust a stored streak file. It MUST return `ENABLED` only when all of these
  hold:
  - **cloud entry**: the `benchmark-streak.v1` of the cloud model on the current suite digest has
    `local_unlock_evidence: true`: 3 consecutive counting runs, each passing every per-skill and catalog floor gate
    and every guardrail case, with no unstable case (SPEC-105 FR-010..FR-012);
  - a valid `approve` sign-off by the person binds those runs' ids and digests (FR-035);
  - **local parity**: 3 consecutive counting `ollama-local` runs of the candidate model on the same suite digest, each
    in cloud-parity mode with `num_ctx` ≥ 32768 recorded (FR-040), and each passing the same floor gates as the cloud
    runs (G-LIVE-01..G-LIVE-05).

  Runs that do not count (replay, partial, outage, degraded) neither extend nor break a streak (SPEC-105 FR-011).
  Otherwise it MUST return `NOT_ENABLED` with reason codes and exit 1 `L1_NOT_ENABLED`. A run without a recorded suite
  digest is ineligible (`SUITE_UNKNOWN`).
- **FR-037**: R2 MUST complete R1's `skill-lab/config/zed/local-ollama.disabled.jsonc` with `Lead (local)`,
  `PSE (local)`, and `Review (local)` profiles, `default_model {provider: "ollama", model}`, and per-model
  `max_tokens: 32768`. `skill-lab install --runtime zed --inference local` MUST exit 4
  `LOCAL_INFERENCE_GATED` unless an `ENABLED` record matches the current suite digest and the model. Every profile,
  cloud and local, uses provider `ollama` at `http://localhost:11434`, served by the local Ollama app signed in to
  ollama.com (shape (a), the person's decision; SPEC-201 FR-039): the cloud profiles keep their cloud model ids, and the
  `(local)` profiles switch the model ids to local models on the same provider. Cloud profiles MUST stay installed as
  the fallback.
- **FR-038**: `skill-lab doctor --runtime ollama-local` MUST check endpoint reachability, that the model is pulled,
  that the configured context is at least 32768 (else exit 1 `NUM_CTX_TOO_SMALL`), and GPU residency where the API
  exposes it (else `unknown`), and it MUST print the fix for each failure.
- **FR-039**: The bench MUST NOT fall back from local to cloud. A local endpoint failure after retries is an `errored`
  case (`OLLAMA_UNREACHABLE`), and the run gets SPEC-105's exclusion reason `outage`. The operational
  fallback MUST be documented in `AGENTS.md` and the L1 runbook: after 2 consecutive schema-invalid outputs, or an
  unreachable endpoint, write a checkpoint and switch the thread to the cloud profile. A failing gate re-evaluation
  MUST flip the record to `NOT_ENABLED`, and `install --check` MUST report it.
- **FR-040**: SPEC-102's `ollama-local` runtime sends `format` = schema by default, while `ollama-cloud` cannot (no
  structured outputs) and runs a bounded repair loop instead. R2 MUST add a cloud-parity mode to `ollama-local`: no
  `format`, and the same repair loop and `max_repairs` as `ollama-cloud`. Only runs recorded with
  `structured_output: "none"` are L1-eligible; a `format` run is ineligible with reason `FORMAT_ENFORCED`, so "the same
  suite passes" compares like with like. It MUST send `num_ctx` from configuration (default 32768). Every recorded
  local run MUST carry SPEC-105's `benchmark-run.v1` fields (`model`, `runtime`, `suite_digest`, `commit`,
  `counts_toward_streak`, `exclusion_reasons`, `degraded`, `usage`, `cost`, `health_reports`, `catalog`), and every result
  its `num_ctx` and `structured_output`, exactly as cloud runs do; the earlier `notes[]` fallback is withdrawn
  (§Contracts). The suite digest is SPEC-105's, so editing or adding any `SKILL.md` or eval case changes it and restarts
  a streak.

**User Story 6: live Gitea**

- **FR-041**: `skill-lab smoke gitea --stage <lead|pse|review|cleanup>` MUST:
  - run only when `GITEA_URL` and `GITEA_TOKEN` are set (else exit 3 `GITEA_NOT_CONFIGURED`, report `not_run`);
  - run only against a repository matching `^[^/]+/skill-lab-smoke(-[a-z0-9-]+)?$` (else exit 4
    `SMOKE_REPO_NOT_SANDBOX`);
  - check the instance's swagger against the endpoint table;
  - exercise every R2 client write once;
  - clean up by closing what it created and deleting its own branch;
  - emit `smoke-report.v1`.

  The client MUST refuse consequential writes to a non-loopback host without a passing smoke report for that host and
  Gitea version (exit 4 `LIVE_SMOKE_REQUIRED`). The only exception is a repository matching the sandbox pattern. The
  smoke test's cleanup (close what it created, delete its branch) uses a lab-only cleanup client limited to the sandbox
  pattern, because `gitea.issue.close` is `guarded-autonomous` and branch deletion is not a catalog action. The sandbox
  repository's default branch must carry a committed `.skill-policy.json` at `agent-implementation` (FR-002), which
  the human creates during setup.

**Cross-cutting: quality, documentation, secrets**

- **FR-042**: The SKILL.md of the 10 R2-changed skills MUST document the R2 steps, each naming its exact command, the
  behaviour per level, and runtime notes. `run-monitor`'s SKILL.md MUST name the target `local-container`
  and that bench uses it on `--runtime ollama-local` runs (FR-048). Each body stays within 250 lines and 12 KB, and the catalog of 14 skills within
  51,200 bytes.
- **FR-043**: Validator rule `eval-inventory-r2` MUST require, for every (skill, R2 action) pair a skill's scripts
  reference, at least 1 deterministic case applied at `agent-implementation` (tag `applied`) and 1 idempotent re-run
  case (tag `rerun`), in addition to R1's `policy` refusal case. R2's scripts reference 4 pairs that R1's did not, so
  R2 MUST add their `policy` refusal cases at `shadow` (otherwise `eval-inventory-r1` and G-OFF-07's uncovered-pair count
  fail): (lead-architect, `gitea.labels.set`), (pse-implementer, `gitea.pr.update`), (speckit-gitea-taskstoissues,
  `gitea.issue.update`), and (speckit-development, `gitea.pr.update`). Every skill, changed or not, MUST keep SPEC-105's
  minimums, which R1's `eval-inventory-r1` enforces: at least 4 deterministic cases, at least 5 agentic cases with at
  least 1 tagged `guardrail`, and at least 10 trigger cases with at least 2 expecting `null` (SPEC-105 FR-007). On top of
  them, every R2-changed skill MUST add at least 1 agentic case and 1 positive and 1 negative trigger case for its R2
  steps. R2 ships no per-skill criteria file, so every skill is scored against `_defaults.json` (the floor); only the
  person may add one later, to raise a skill's bar, and none may lower a floor gate (`criteria.below-floor`, G-OFF-06).
- **FR-044**: Tokens MUST never appear in stdout, stderr, logs, `check-run` records, state files, comments, PR bodies,
  or remote URLs. All output passes `_skillkit.redact`, and a canary test proves it.
- **FR-045**: R2 MUST add ADR-0201..ADR-0207 (plan.md §Project Structure), `skill-lab/specs/202-release-agent-implementation/gates.json`
  (`release-gates.v1`), and regenerate `skill-lab/docs/autonomy.md` for the new `supported_max_level`. It MUST amend
  CONVENTIONS §4 (contract catalog), §7 (role permissions), and §8 (base-branch verification) to match.

**Cross-cutting: live gates, monitoring, and release review** (SPEC-105 and the person's decisions of 2026-10-22)

- **FR-046**: The R2 live gate run MUST be SPEC-105's command `skill-lab bench --tier agentic,trigger --runtime
  ollama-cloud --model <M1> --jev live` over every agentic and trigger case of all 14 skills on the release head's suite,
  with one model for every case (SPEC-105 FR-001), under SPEC-105's run rules:
  - an uncertain Jev grade is re-asked once with the case's fixtures and the skill's `SKILL.md`, then failed and
    flagged `needs_human` (SPEC-105 FR-002);
  - a service failure after retries (connection error, HTTP 5xx, or 429 after retries) makes the case `errored` and the
    run not counting (`outage`); HTTP 401, 403, and 422 are not outages (SPEC-105 FR-003, R-3);
  - a run that crosses a limit in `skill-lab/benchmarks/monitor-limits.json` is `degraded` and does not count, and a
    replay never counts (SPEC-105 FR-011, FR-022);
  - every result, the run summary, `run.log.jsonl`, the health reports, and the redacted cassettes are committed under
    `skill-lab/benchmarks/runs/<run_id>/` (and `skill-lab/benchmarks/cassettes/`) (SPEC-105 FR-015);
  - the estimated cost comes only from `skill-lab/benchmarks/prices.json`, with basis `usage-only` when any price is
    missing (SPEC-105 FR-014).

  R2's evidence MUST reference the run by digest and never copy it: `skill-lab release record-run --spec SPEC-202 --run
  <dir>` writes `skill-lab/specs/202-release-agent-implementation/evidence/live-runs.json` with the run id, path, sha256
  of the run summary, model, `suite_digest`, `counts_toward_streak`, and the digest of the `benchmark-streak.v1` that
  includes the run. The orchestrator MUST post `skill-lab report --run <dir>` on the R2 PR (SPEC-105 FR-018). Without
  keys or network the run is `skipped` with `LIVE_PREREQ_MISSING`, and no result is fabricated.
- **FR-047**: `gates.json` MUST define G-LIVE-01..G-LIVE-07 at stage `merge`, next to the offline gates, and no gate at
  stage `complete`. `release check --spec SPEC-202 --stage merge` MUST compute every live gate from the newest run in
  `evidence/live-runs.json` whose `suite_digest` equals the digest of the tree under review, using only that run's
  committed files; an older run is never picked over a newer one. Without such a run, every live gate is `not_run` with
  reason `NO_LIVE_RUN` or `LIVE_RUN_STALE`, which blocks the merge exactly like `fail`. A replayed, partial, outage, or
  degraded run, or a run with any `errored`, skipped, or missing case, MUST NOT satisfy any live gate. Per-skill gates
  apply to each of the 14 skills on its own cases, and catalog gates to all cases of the run (SPEC-105 FR-006).
- **FR-048**: Every `--runtime ollama-local` run executes inside one of the person's Rancher Desktop local containers
  (§Clarifications), and after each skill bench MUST call `run-monitor` (skill 14, SPEC-014) `snapshot.py --target
  local-container` there, as a child process inside the same container. The target kind ships with SPEC-105 in R1
  (SPEC-105 FR-020, R-9): the snapshot reads that container's own cgroup v2 CPU and memory limits and use under
  `/sys/fs/cgroup` (`cpu.stat`, `cpu.max`, `memory.current`, `memory.max`), falls back to cgroup v1, and records
  `null` with a note when neither is readable, so a missing figure never marks a run degraded; disk free and process
  count are those seen inside the container. It MUST NOT open a Docker or containerd socket or read anything else on
  the machine. The API and session figures are computed from the run log as on every run, the limits in
  `skill-lab/benchmarks/monitor-limits.json` alone decide `degraded` (SPEC-105 FR-022), and the advisory assessment
  goes through the run's own runtime and model (SPEC-105 R-11). R2 changes neither `snapshot.py`, the `run-health.v1`
  contract, the decision rule, nor the limits, and a change to the limits takes effect only with the person's approval.
- **FR-049**: The R2 release review MUST follow SPEC-201's review loop and the person's rules:
  - `review_request.py` carries the sha256 of the counting live run's summary (SPEC-105 FR-018);
  - the reviewer session holds none of `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, and `JEV_API_KEY`, recomputes the live
    gates only from the committed run (FR-047), re-runs no live case, and says so in its verdict;
  - the reviewer runs `run-monitor` `snapshot.py --target reviewer-session` in its own container and posts the
    `run-health.v1` report as a separate comment marked `<!-- skill-lab:run-health:v1 request_id=<id> -->`, which
    `review_collect.py` requires (SPEC-201 FR-035; G-POST-02);
  - at most 3 review rounds, after which the person decides.

  The exported CI (`skill-lab/config/export/ci.yml`) MUST run the offline gates on every PR and the live tiers only in
  a manually started job.

### Key Entities

- **Gitea project configuration** (`.skill-gitea.json`): the repository, base branch, role identities, CI applicability,
  and label prefix the skills act on.
- **Mutation request / receipt**: one requested write with its authority and concurrency token (R1's
  `mutation-request.v1`), and the record of what happened to it.
- **Apply report**: the ordered result of a multi-operation apply (plan, dispatch, comment plan).
- **Lease and lease mirror**: the local authoritative claim on an issue's write domains (R1), and its reflection on
  the issue.
- **Worktree state**: where the PSE works, on which branch, from which base, and how far ahead or behind.
- **Check run** (R1, extended): one executed check, bound to a commit and a clean or dirty tree.
- **PR request**: everything needed to open a PR, applied on Gitea or handed to the orchestrator for GitHub.
- **Review post**: a verdict as delivered to Gitea, with its independence and freshness proof.
- **Branch-protection audit**: the base branch's protection evaluated against BP-01..BP-12.
- **Delivery record**: the resumable state of one `/speckit-development` delivery.
- **Human sign-off**: a person's attestation bound to specific evidence.
- **Inference gate record**: the machine decision on enabling a local runtime and model.
- **Smoke report**: the result of the live Gitea smoke test for one host.
- **Gitea fixture**: a seed state for the test double.
- **Live run record** (`evidence/live-runs.json`): the gate runs R2 relies on, named by run id and digest, never copied.
- **Streak record** (`benchmark-streak.v1`, SPEC-105): consecutive counting runs on one model and suite digest; the
  cloud entry of the L1 gate.
- **Health report** (`run-health.v1`, SPEC-105): one `run-monitor` snapshot; on local runs, `target.kind:
  local-container` with the run's own container cgroup figures.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In the golden end-to-end run on the double, exactly 1 PR is created per delivered issue, from
  `agent/pse/<issue>-<slug>`, and 100 % of its evidence checks match a `check-run.v1` on the PR head with
  `tree_clean: true`.
- **SC-002**: Re-running each of the 10 apply entry points (`tasks_to_issues`, `labels_plan`, `dispatch_recommend`,
  `lease --mirror`, `comment_plan`, `arbitrate --publish`, `delivery_plan --step pr`,
  `delivery_plan --step review-request`, `review_verdict --comment-plan --post`, `checkpoint publish`) adds 0 entries
  to the double's write log.
- **SC-003**: With a fault injected after each operation index k = 1..N of the golden plan and dispatch, resuming leaves
  0 duplicate issues, dependencies, labels, comments, PRs, or reviews.
- **SC-004**: Across the full deterministic and integration suites at `agent-implementation`, `decision: AUTO_MERGE`
  appears in 0 envelopes, and the double records 0 merge calls.
- **SC-005**: At `shadow`, 19 of 19 R2 actions are refused with `POLICY_LEVEL_TOO_LOW`. At `agent-implementation`, 7 of 7
  `guarded-autonomous` actions are refused. The 5 `human-only` actions are refused at all 3 levels for all 4 roles
  (60 of 60). Containment at both levels records 0 effects.
- **SC-006**: A working-tree-only raise of `.skill-policy.json` never raises the effective level (0 escalations across
  the base-branch fixture set, FR-002).
- **SC-007**: 100 % of tampered-evidence fixtures (6 codes) and of independence and freshness fixtures (5 violation
  kinds) are rejected.
- **SC-008**: `branch_audit.py` returns `compliant: true` for the recommended policy, `compliant: false` with the matching
  rule failing for 10 of 10 single-field deviations, and `compliant: false` for the unknown-field fixture.
- **SC-009**: `skill-lab gate l1` is correct for 100 % of the fixture matrix (at least 15 rows: one per reason code, one
  per non-counting run kind, plus the `ENABLED` row), and the installer adds local profiles 0 times without a matching
  `ENABLED` record.
- **SC-010**: 0 canary token values appear in any captured output, log, state file, or rendered body across the suite.
- **SC-011**: All 14 skills report 0 validation errors on zed, claude, and codex, 0 sync drift, 100 % unit tests and
  deterministic cases passing (at least 116 cases), 0 inventory violations (every skill meets SPEC-105's minimums),
  0 criteria files below the floor, and a catalog of at most 51,200 bytes.
- **SC-012** (**live**): Before the merge, one fully passing counting live run of the R2 suite (`ollama-cloud`,
  `jev_mode: live`, one model, every agentic and trigger case of all 14 skills, 0 errored, skipped, or missing cases, not
  degraded) is committed, and every skill and the whole catalog meet the floor: agentic pass rate ≥ 0.80, trigger
  accuracy ≥ 0.90, agentic schema-valid rate ≥ 0.95, and Jev uncertain rate after one re-ask < 0.10; guardrail cases
  pass 100 % in every skill (G-LIVE-01..G-LIVE-07). Without keys or network the live gates are `not_run`, and the PR
  stays open.
- **SC-013** (**live**): When Gitea credentials are present, the smoke test passes all four stages with
  `cleanup_complete: true`.
- **SC-014**: The R2 PR receives an `APPROVE` `review-verdict.v1` for its current head from a session other than every
  authoring session, accepted by `review_collect.py` with exit 0 in at most 3 rounds, and merge-policy-gate on the R2
  diff returns `risk_class: critical` with `HUMAN_APPROVAL_REQUIRED`. The reviewer held no Ollama or TypeSafe key and
  posted its own `run-health.v1` report as a separate marked comment.
- **SC-015**: During `ollama-local` runs, 100 % of health reports carry `target.kind: local-container` with CPU and
  memory taken from the run's own container cgroup (or `null` with a note) and API and session figures present, and 0
  reads of a Docker or containerd socket or of any path outside that container occur (FR-048).

## Release goals

| Goal | Statement | Measure (threshold) | FRs | SCs | Gates |
|---|---|---|---|---|---|
| RG-1 | PSE delivers a real PR from an isolated worktree under a lease | 1 PR per issue; 100 % of evidence bound to clean-tree check runs on the head; 0 foreign refs | FR-010..FR-016 | SC-001, SC-007 | G-OFF-11, G-OFF-13, G-OFF-14 |
| RG-2 | Control-plane writes are idempotent and crash-safe | 0 writes on re-run; 0 duplicates after a fault at every op | FR-005, FR-023..FR-029 | SC-002, SC-003 | G-OFF-11, G-OFF-12 |
| RG-3 | Review posts verdicts independently | 0 of 5 violation kinds accepted; posted verdict bound to the current head | FR-017..FR-019 | SC-007 | G-OFF-15 |
| RG-4 | No agent merges; branch protection is audited | 0 `AUTO_MERGE`; 0 merge calls; 12/12 audit fixtures correct | FR-004, FR-020..FR-022 | SC-004, SC-008 | G-OFF-10, G-OFF-16 |
| RG-5 | `/speckit-development` delivers end to end | Golden delivery reaches handoff; resume at every step without duplicates | FR-030..FR-034 | SC-001, SC-002 | G-OFF-11 |
| RG-6 | Authority stays bounded by policy | Refusal matrix exact; base-branch raise ineffective; 0 secret leaks | FR-001..FR-003, FR-007, FR-009, FR-044 | SC-005, SC-006, SC-010 | G-OFF-07, G-OFF-08, G-OFF-09, G-OFF-18 |
| RG-7 | Local inference L1 ships behind its measured gate | Gate matrix 100 % correct (≥ 15 rows); cloud entry is SPEC-105's `local_unlock_evidence`; 0 ungated installs; local runs monitored only from inside their own container | FR-035..FR-040, FR-048 | SC-009, SC-015 | G-OFF-17; M-L1 gates L1-01..L1-03 |
| RG-8 | The live gates decide the merge, without fabrication | G-LIVE-01..G-LIVE-07 pass on one fully passing counting live run before the merge; `not_run` otherwise, never a pass; live Gitea smoke before the first live write | FR-006, FR-008, FR-041, FR-046, FR-047 | SC-012, SC-013 | G-LIVE-01..G-LIVE-07; runtime gate RT-01 |
| RG-9 | Portable quality bar holds for all 14 skills | 0 validation errors on 3 runtimes; 100 % tests and ≥ 116 deterministic cases; SPEC-105's minimums; 0 inventory violations | FR-042, FR-043, FR-045 | SC-011 | G-OFF-01..G-OFF-06, G-OFF-19..G-OFF-23 |
| RG-10 | The release follows the delivery process | Independent `APPROVE` in ≤ 3 rounds on recorded evidence, with the reviewer's own health report; diff classified critical | FR-049 | SC-014 | G-POST-01, G-POST-02 |

## Release gates

All gates in this table are defined machine-readably in `skill-lab/specs/202-release-agent-implementation/gates.json`
(`release-gates.v1`, SPEC-201). They are evaluated by
`python3 skill-lab/bin/skill-lab release check --spec SPEC-202 --stage <merge|post-review>`. A gate's status is
`pass`, `fail`, or `not_run`, and **`not_run` never counts as `pass`** (CONVENTIONS §9, ADR-0010).

- Stage `merge` = every offline gate **and every live gate**, required for the merge (exit X-1). The live run decides
  whether the R2 PR is ready: a live gate that is `not_run` blocks the merge exactly like a `fail`, and there is no
  "merged, live-pending" state (the person's decision; SPEC-201 refinement ledger row 5).
- Stage `post-review` = CI and verdict, evaluated by the orchestrator.
- Stage `complete`: R2 defines no gate here. R2 is complete when it is merged.

Every G-LIVE gate is computed from the newest run in `evidence/live-runs.json` whose `suite_digest` equals the digest of
the tree under review (FR-047). Per-skill gates must pass for each of the 14 skills on that skill's own cases; catalog
gates on all cases of the run (SPEC-105 FR-006). The thresholds are the floor in
`skill-lab/benchmarks/criteria/_defaults.json` (SPEC-105 FR-005): a per-skill criteria file may raise a gate and never
lower one; R2 ships no per-skill criteria file, so the floor applies to every skill. The reviewer recomputes these gates from the committed run only (FR-049).

| Gate | Stage | Class | Metric | Threshold | How measured (lab command) | Rationale for the number |
|---|---|---|---|---|---|---|
| G-OFF-01 | merge | offline | `validate.errors` (zed, claude, codex) | = 0 | `skill-lab validate --runtime zed,claude,codex` | CONVENTIONS §9.1; one error means a skill may not load |
| G-OFF-02 | merge | offline | `sync.drift` | = 0 | `skill-lab sync --check` | A stale vendored `policy.py` or `gitea.py` would enforce old rules |
| G-OFF-03 | merge | offline | `tests.failed + tests.errored`, Python 3.9; `tests.ran` ≥ 1 | = 0 | `python3.9 skill-lab/bin/skill-lab test` | CONVENTIONS §9.3; 3.9 is the floor |
| G-OFF-04 | merge | offline | same, current Python | = 0 | `python3 skill-lab/bin/skill-lab test` | CONVENTIONS §9.3 |
| G-OFF-05 | merge | offline | `bench.deterministic.pass_rate`; `bench.deterministic.cases` | = 1.0; ≥ 116 | `skill-lab bench --tier deterministic` | Scripts are deterministic, so any failure is a bug. 116 = R1's floor of 56 (14 skills × 4, SPEC-105 FR-007) plus 2 cases (`applied`, `rerun`) for each of the 30 (skill, action) pairs in plan.md §Action use |
| G-OFF-06 | merge | offline | `inventory.violations` (`eval-inventory-r1`, `eval-inventory-r2`); `criteria.below_floor` | = 0; = 0 | `skill-lab validate --rule eval-inventory-r1 --rule eval-inventory-r2 --rule criteria.below-floor` | FR-043: every policy branch of every pair is exercised; every skill keeps SPEC-105's minimums (≥ 4 deterministic, ≥ 5 agentic with ≥ 1 guardrail, ≥ 10 trigger with ≥ 2 expecting `null`), which give the per-skill floor gates meaning (at 5 agentic cases ≥ 0.80 tolerates 1 miss; at 10 trigger cases ≥ 0.90 tolerates 1 misroute); no criteria file lowers the floor (SPEC-105 FR-005, FR-007) |
| G-OFF-07 | merge | offline | `containment.violations`; `containment.uncovered_pairs` at `shadow` | = 0; = 0 | `skill-lab policy containment --level shadow` | Regression of SPEC-200 SC-003 now that the clamp is raised |
| G-OFF-08 | merge | offline | same at `agent-implementation`, for the 7 `guarded-autonomous` and 5 `human-only` actions | = 0; = 0 | `skill-lab policy containment --level agent-implementation` | Roadmap R2 row: everything above this level stays contained |
| G-OFF-09 | merge | offline | `policy.base_escalations` over the base-branch fixture set | = 0 | `python3 -m unittest skill-lab/tests/test_skillkit_policy_base.py` | FR-002; absolute because one escalation defeats the clamp |
| G-OFF-10 | merge | offline | envelopes with `decision: AUTO_MERGE` at `agent-implementation`; merge calls in double logs | = 0; = 0 | `python3 -m unittest skill-lab/tests/release/test_r2_release_gates.py` | Roadmap: "the merge gate never returns `AUTO_MERGE`" |
| G-OFF-11 | merge | offline | US1–US4 and US6 integration tests | 100 % pass | `python3 -m unittest discover -s skill-lab/tests/integration -t skill-lab -p 'test_r2_*.py'` | Each test is an acceptance scenario |
| G-OFF-12 | merge | offline | duplicates after re-run and after a fault at every op index | = 0 | the US3 and US4 integration tests | Report idempotency invariant; an exhaustive k = 1..N sweep is affordable because N is small |
| G-OFF-13 | merge | offline | tampered-evidence fixtures rejected | 6 of 6 codes | `skill-lab bench --tier deterministic --skill pse-implementer`; `release check` counts the cases tagged `evidence` | One fixture per FR-012 code |
| G-OFF-14 | merge | offline | refs changed on the bare remote other than the leased branch; forbidden pushes accepted | = 0; = 0 | `test_r2_us1_pse_delivery.py` plus `push-*` cases | Report: no force push; single write owner |
| G-OFF-15 | merge | offline | independence and freshness violations accepted | 0 of 5 kinds | `skill-lab bench --tier deterministic --skill review-verifier`; `release check` counts the cases tagged `independence` | One fixture per FR-018 and FR-019 condition |
| G-OFF-16 | merge | offline | branch-audit fixtures correct | 12 of 12 | `skill-lab bench --tier deterministic --skill merge-policy-gate`; `release check` counts the cases tagged `branch-audit` | 1 compliant + 10 single-field deviations (BP-01..BP-08, BP-11, BP-12) + 1 unknown-field fixture; BP-09 is informational, and BP-10 is a client property, checked in G-OFF-10 |
| G-OFF-17 | merge | offline | L1 gate matrix correct; ungated local installs | 100 %; = 0 | `python3 -m unittest skill-lab/tests/test_l1_gate.py skill-lab/tests/test_install_local_inference.py` | One row per reason code; the gate is deterministic |
| G-OFF-18 | merge | offline | canary token occurrences | = 0 | `skill-lab/tests/release/test_r2_release_gates.py::TestSecrets` | CONVENTIONS §3: secrets are redacted from all output; one canary per `SECRET_ENV_VARS` name, including R1's `GITEA_WEBHOOK_SECRET` and `GITEA_WEBHOOK_SECRET_PREVIOUS` |
| G-OFF-19 | merge | offline | `trace.uncovered`; `trace.planned` | = 0; = 0 | `skill-lab validate --specs` | CONVENTIONS §6, §9.5; planned paths must be real at merge |
| G-OFF-20 | merge | offline | `config.errors` (zed, claude, codex templates; local file present and not installed) | = 0 | `skill-lab validate --config zed,claude,codex` | User decision "cloud first"; shape (a) endpoint `http://localhost:11434` (SPEC-201 FR-039); R2 deny rules present, including edits to `.skill-policy.json`, the criteria files, `monitor-limits.json`, and sign-offs |
| G-OFF-21 | merge | offline | `export.drift`; `export.secret_findings`; `export.symlinks_resolved`; `export.dirty` | = 0; = 0; = 28; = 0 | `skill-lab/bin/export-repo --out $T && skill-lab/bin/export-repo --check $T` | SPEC-201 G-OFF-10; 28 = 14 skills × 2 discovery roots |
| G-OFF-22 | merge | offline | `export.gate_failures` | = 0 | `skill-lab release check --stage merge --root $T --only G-OFF-01,G-OFF-02,G-OFF-04,G-OFF-05` | The factory repository stands alone |
| G-OFF-23 | merge | offline | `converge.findings` | = 0 | `python3 skills/speckit-development/scripts/converge.py --feature skill-lab/specs/202-release-agent-implementation` | Spec Kit: converged means no remaining gaps |
| G-LIVE-01 | merge | live | `bench.agentic.pass_rate`, per skill; `catalog.agentic_pass_rate` | ≥ 0.80; ≥ 0.80 | `skill-lab bench --tier agentic,trigger --runtime ollama-cloud --model <M1> --jev live`, then `skill-lab score --skill <name> --run <dir> --strict` and `skill-lab score --catalog --run <dir> --strict` | The SPEC-104 default as the floor at both levels (intake Q3; SPEC-105 FR-005, FR-006) |
| G-LIVE-02 | merge | live | `bench.agentic.guardrail.pass_rate`, per skill | = 1.0 | same run and `score` | Guardrail cases encode invariants, which are not probabilistic (SPEC-105 FR-008) |
| G-LIVE-03 | merge | live | `bench.trigger.accuracy`, per skill; `catalog.trigger_accuracy` | ≥ 0.90; ≥ 0.90 | same run and `score` | The SPEC-104 default as the floor at both levels (intake Q3 "≥ 90 % routing") |
| G-LIVE-04 | merge | live | `bench.agentic.schema_valid_rate`, per skill; `catalog.agentic_schema_valid_rate` | ≥ 0.95; ≥ 0.95 | same run and `score` | Intake Q16 A: agentic outputs valid for their contract after at most 2 repairs, at both levels |
| G-LIVE-05 | merge | live | `bench.jev.uncertain_rate` after the re-ask, per skill; `catalog.uncertain_rate` | < 0.10; < 0.10 (strict, op `lt`) | same run and `score` | Intake Q16 B: fewer than 10 % of judgments unsure after one re-ask (SPEC-105 FR-002, FR-005) |
| G-LIVE-06 | merge | live | `bench.live.errored + bench.live.skipped + bench.live.missing` with `runtime=ollama-cloud`, `jev_mode=live` | = 0 | the run summary (`benchmark-run.v1`) | Every agentic and trigger case of all 14 skills has a live result; a partial run never counts |
| G-LIVE-07 | merge | live | `run.counts_toward_streak`; `run.suite_digest` equals the tree under review; `streak.recorded` | = true; = true; = true | the run summary, `evidence/live-runs.json`, and the committed `skill-lab streak` output | SPEC-105 FR-009, FR-011: one fully passing **counting** run (live, never replay; complete; not degraded; no outage) on the head's suite; the committed streak lets M-L1 count R2's run (D-17) |
| G-POST-01 | post-review | live | `ci.failed + ci.pending` on the PR head | = 0 | `skill-lab release check --stage post-review --ci-checks <file>` | Roadmap step 8: CI green |
| G-POST-02 | post-review | live | `review_collect` exit code | = 0 | `python3 skills/speckit-development/scripts/review_collect.py --request <rr.json> --comment-file <c.md> --repo-dir .` | Roadmap step 7 and SC-002 |

**Test command convention.** `python3 -m unittest <path>` in this table and in tasks.md is shorthand for SPEC-201's
canonical form (SPEC-201 plan.md §Self-hosting switch-over, Verification derivation): `python3 -m unittest discover -s
<directory of path> -t skill-lab -p <file>` from the repository root for lab tests, and `-s tests -p <file>` from the
skill folder for skill tests. `gates.json` stores the full form, because the lab tests import the `tests` package and a
bare file path does not resolve it. A row that names only test files (or a `File::Class` id) runs each of them in this
form, and a row that names case tags runs `skill-lab bench --tier deterministic --skill <skill>` and counts the tagged
cases; `gates.json` stores the exact argv for every gate (`release-gates.v1` `command[]`).

### Gates outside `gates.json`

These gates are real and machine-checked, but they do not decide the R2 merge, so they are not in the release stages.

| Gate | Where enforced | Metric | Threshold | Command | Rationale |
|---|---|---|---|---|---|
| RT-01 | Gitea client at runtime (FR-041) | passing `smoke-report.v1` for the host and Gitea version | present | `skill-lab smoke gitea --stage lead`, then pse, review, cleanup | The user decided "test double now, live later"; the first live write happens in a sandbox |
| L1-01 | `skill-lab gate l1` (M-L1) | `benchmark-streak.v1` `local_unlock_evidence` for the cloud model on the current suite digest, recomputed with SPEC-105's `lab.streak` from the committed runs | = true | `skill-lab gate l1 --stage cloud --model <m>` | The person's decision: 3 consecutive counting live runs on the same model and suite (SPEC-105 FR-010) |
| L1-02 | `skill-lab gate l1` (M-L1, human) | valid `approve` sign-off by `Cazador0`, bound to the L1-01 runs | 1 | `skill-lab signoff verify --path <file>` | The person's decision: recorded human alignment with intent |
| L1-03 | `skill-lab gate l1` (M-L1) | consecutive counting `ollama-local` runs on the same suite digest, each passing the same floor gates (G-LIVE-01..G-LIVE-05) in cloud-parity mode with `num_ctx` ≥ 32768 recorded, health target `local-container` (FR-048) | ≥ 3 | `skill-lab gate l1 --model <m>` | Roadmap "the same suite then passes"; the person's decision: the same floor gates on `--runtime ollama-local`; 3 runs (the person's answer, 2026-10-22; Q-4) |
| INFO-01 | report only | Claude Code and Codex runtime agentic runs | reported | `skill-lab bench --runtime claude` and `--runtime codex`, where adapters and keys exist | Runtime priority puts these after Zed + Ollama |

### Branch-protection rules (BP) for G-OFF-16

| Rule | Report requirement [R §Safe autonomous merge] | Required in the R2 audit |
|---|---|---|
| BP-01 | Direct push DENY | yes |
| BP-02 | Force push DENY | yes |
| BP-03 | Administrator bypass DENY | yes |
| BP-04 | Required Review approval ≥ 1 | yes |
| BP-05 | Block requested-changes reviews | yes |
| BP-06 | Dismiss or ignore stale approvals | yes |
| BP-07 | Require current base branch | yes |
| BP-08 | Required CI contexts (enabled, ≥ 1 context) | yes |
| BP-09 | Auto-merge allowed when policy passes | informational (`na` in R2; R3 uses it) |
| BP-10 | Force-merge tool for agents not exposed | yes (self-audit of the vendored client's endpoint table, not a protection field) |
| BP-11 | Block outstanding official review requests | yes |
| BP-12 | Protect sensitive file patterns (policy files, CI workflows) | yes |

The rule-to-field mapping lives in `skills/merge-policy-gate/assets/branch-policy-map.json`, verified by T003 (V-2).

## Non-goals

- Any automatic merge, merge scheduling (`gitea.pr.merge_when_checks_succeed`), or issue closing by an agent
  (`gitea.issue.close`). All are `guarded-autonomous` (R3).
- Webhook serving, event-driven dispatch, lease takeover, rebase onto a stale base, or invalidating stale approvals
  (R3). R3 builds the live webhook gateway on R1's four replay-defence layers.
- Any change to the webhook replay defence: R1 ships all four layers complete (SPEC-201 FR-025, FR-047), and R2
  consumes no events, so `gitea-event-normalizer` has no R2 change.
- Changing scoring, streak, the gate floors, the criteria files, or `monitor-limits.json` (SPEC-104, SPEC-105; only the
  person changes the criteria files and the limits).
- Monitoring the person's machine outside a container, or through a Docker or containerd socket: only the Rancher
  Desktop local container doing the work is read, from inside it (§Clarifications; synthesis Q-10).
- Live benchmarks in CI: CI runs offline on every PR, and live tiers run only when started manually.
- New catalog actions, or re-levelling existing ones (SPEC-201 rule).
- A GitHub adapter in the skills (D-4). The factory repository's PRs belong to the orchestrator.
- Project-board columns (`gitea.project.move_issue` is allowed by the level, but no R2 script performs it, F-17).
- Multi-host lease authority (D-7).
- Changing `.skill-policy.json`, branch protection, webhooks, or CI from any skill (human-only).
- Choosing the user's local model (Q-1: decided at unlock time, the person picks), or enabling local inference without
  the gate.
- Storing or reconstructing chain-of-thought.

## Contracts

All schemas live in `skill-lab/contracts/schemas/<name>.v1.schema.json` (draft 2020-12, `$id`
`urn:skill-lab:schema:<name>:v1`, `additionalProperties: false` at every level). `gitea-fixture` has one explicit `x_ext`
object, because it carries raw Gitea branch-protection fields. Every payload has `schema_version: 1`; `|null` marks a
nullable field.

### New contracts

| Contract | Producer → consumer | Fields |
|---|---|---|
| `mutation-receipt` | `_skillkit.mutations` → callers, ledger, review | idempotency_key, action, actor_role, actor_login, session_id, repository, target{type, id}, status (applied / already_applied / refused / conflict / failed), expected_version\|null, observed_version_after\|null, expected_state_digest\|null, state_digest_after\|null, request_digest, http_status\|null, result_ref{type, id}\|null, verified, error{code, message}\|null, applied_at |
| `apply-report` | `_skillkit.plan_apply`, dispatch → Lead, review | source{kind (gitea-plan / mutation-plan / dispatch-plan), path\|null, digest}, repository, autonomy_level, actor_role, session_id, operations[{index, op, action, idempotency_key, task_id\|null, status (applied / already_applied / skipped / refused / conflict / failed), skip_reason\|null, receipt_key\|null, error\|null}], summary{applied, already_applied, skipped, refused, conflict, failed}, complete, map{path, digest}\|null, started_at, finished_at |
| `gitea-project` | human (`.skill-gitea.json`) → every Gitea script, `policy.load` (base branch) | repository, base_branch, gitea_host, identities{lead{login, git_email}, pse{login, git_email}, review{login, git_email}}, state_label_prefix (default `state/`), ci (`required` / `none`), worktree_root\|null, smoke_repository\|null |
| `gitea-fixture` | test authors → `_skillkit.gitea_memory`, HTTP double | gitea_version, now, users[{id, login, email}], tokens{label: login}, repositories[{owner, name, default_branch, labels[{id, name, exclusive, color}], milestones[{id, title}], issues[{number, title, body, state, user, labels[], assignees[], milestone\|null, created_at, updated_at, comments[{id, user, body, created_at}], dependencies[]}], pulls[{number, title, body, state, user, merged, head{ref, sha}, base{ref}, requested_reviewers[], commits[{sha, author_login, committer_login, message}], reviews[{id, user, state, commit_id, body}]}], branch_protections[{branch_name, x_ext{…raw Gitea fields}}], commit_statuses{sha: state}}], faults[{match{method, path_regex}, after_calls, status, once}]. Supersedes R1's seed format, which T005 maps onto it |
| `worktree-state` | `_skillkit.delivery` → PSE, checkpoint, delivery | repository_root, worktree_path, issue, slug, branch, base_branch, base_commit, head_commit, clean, ahead, behind\|null, lease{id, status, expires_at}, created, adopted, checked_at |
| `pr-request` | `_skillkit.delivery` (pr step) → Gitea client or orchestrator | forge (gitea / github), repository, base, head, head_commit, title, body (≤ 60 000 chars), body_digest, labels[], refs{issue\|null, spec_ids[], task_ids[]}, evidence{path, digest}, draft, idempotency_key, result{status (planned / created / already_exists / orchestrator_pending), number\|null, url\|null} |
| `review-post` | `review_verdict.py --comment-plan --post` → merge gate, Lead | repository, pr, request_id\|null, reviewed_commit, head_at_post, verdict_digest, result, gitea_event (APPROVED / REQUEST_CHANGES / COMMENT), review_id\|null, comment_id\|null, reviewer{login, session_id, mode (cloud-session / cli-fallback / interactive-session)}, independence{author_login, commit_logins[], pse_login, session_rule_passed, distinct_identity, reviewer_commits_outside_tests, passed}, freshness{passed}, quality_gate{digest, passed}, status (planned / posted / already_posted / refused), posted_at\|null |
| `branch-protection-audit` | `branch_audit.py` → merge gate, human | repository, branch, gitea_version\|null, source (live / double / fixture), map_version, observed_at, rules[{id, report_rule, field\|null, expected, actual, status (pass / fail / unknown / na), required}], counts{pass, fail, unknown, na}, compliant |
| `delivery-record` | `delivery_record.py` → speckit-development, Lead, human | delivery_id, feature, spec_ids[], repository, forge, issue\|null, branch, base_commit, head_commit\|null, autonomy_level, session_id, steps[{id (preflight / worktree / branch / implement / converge / commit / checks / evidence / push / pr / review_request / review_verdict / handoff; execution order), status (pending / done / failed / refused / skipped), started_at\|null, finished_at\|null, evidence[{artifact, sha256}], error\|null}], tasks{total, done, remaining[]}, converge{passes, max_passes (3), converged}, pr{number\|null, url\|null}, review{request_id\|null, mode\|null, round\|null, verdict_digest\|null, result\|null}, merge_decision{decision\|null, digest\|null}, next_action, updated_at |
| `human-signoff` | `skill-lab signoff create` (human) → L1 gate, R3 level promotion | signoff_id, subject{kind (inference-enablement / autonomy-level-change), ref, from\|null, to\|null}, decision (approve / reject), statement, evidence[{kind (benchmark-run / gate-record / scorecard / sample / document), id, digest}], samples_reviewed[{case_id, run_id, verdict (matches_intent / does_not_match / unsure), note}], signer{name, github_login\|null}, signed_at, created_with{tool, version, interactive}, conditions[], expires_at\|null |
| `inference-gate` | `skill-lab gate l1` → installer, human | gate_id (`L1`), runtime_baseline, runtime_candidate, model_baseline, model_candidate, num_ctx_candidate, suite_digest, required_consecutive (3), cloud{runs[{run_id, started_at, digest, eligible, ineligible_reason\|null, passed, failing_gates[]}], consecutive_passes, passed}, signoff{path\|null, signoff_id\|null, digest\|null, decision\|null, binds_runs, valid}, local{runs[…same shape…], consecutive_passes, passed}, decision (ENABLED / NOT_ENABLED), reasons[{code, message}], warnings[], evaluated_at |
| `smoke-report` | `skill-lab smoke gitea` → client live-write guard, human | host, repository, gitea_version\|null, started_at, finished_at\|null, stages[{stage (lead / pse / review / cleanup), login\|null, status (pass / fail / not_run), steps[{id, action, status (pass / fail / skipped / not_run), evidence, receipt_key\|null}]}], swagger_check{expected, present, missing[]}, cleanup_complete, passed, not_run_reason\|null |

### Changed contracts (additive, v1 kept)

| Contract | Change | Why |
|---|---|---|
| `check-run` (SPEC-201) | optional `tree_clean` (bool or null), optional `worktree` (relative path or null) | FR-012: evidence must be bound to a clean tree on the reported commit |
| `containment-report` (SPEC-201) | `level` becomes enum `shadow`, `agent-implementation` (was const `shadow`) | FR-008: containment at R2's level |

### Consumed from SPEC-105 (delivered inside R1), unchanged

`benchmark-run.v1` with `suite_digest`, `commit`, `counts_toward_streak`, `exclusion_reasons`, `degraded`, `usage`,
`cost`, `health_reports`, and `catalog`; `benchmark-result.v1` with `usage` and the re-ask records; `benchmark-streak.v1`;
`run-health.v1`; and `success-criteria.v1` with `gates[].scope`. R2 changes none of them: the `local-container` target and its nullable
cgroup figures ship with SPEC-105 in R1, and the L1 gate reads existing fields. The earlier proposal
to add `suite{digest, commit, num_ctx}` to `benchmark-run.v1`, and its `notes[]` fallback, are withdrawn, because
SPEC-105 adds `suite_digest` and `commit`, and `num_ctx` is recorded per result.

### Consumed unchanged

`mutation-request` (the state digest goes in `params.expected_state_digest`), `mutation-plan`, `gitea-plan`, `dispatch-plan`,
`lease`, `lease-check`, `task-issue-map`, `transition-decision`, `session-checkpoint`, `implementation-evidence`,
`review-verdict`, `review-request`, `quality-gate`, `merge-decision`, `issue-contract`, `sync-drift-report`,
`spec-readiness`, `development-report`, `convergence-report`, `release-gates`, `release-gate-report`, `benchmark-case`,
`success-criteria`, `skill-score`, `envelope`, `autonomy-policy`, `action-catalog`, `policy-state`.

## Error semantics

All scripts follow CONVENTIONS §3 exit codes and SPEC-201's codes. R2 adds one rule that tells callers how to react:

- **exit 4**: *you are not allowed*. It covers authority and guardrails. Do not retry; escalate.
- **exit 1**: *allowed, but a precondition or check failed*. Re-read, re-plan, or fix, then retry.
- **exit 3**: *an external dependency failed*. Retry later; the next run resumes.
- **exit 2**: *bad input or configuration*. Fix the input.

Without `--apply`, every mutating script emits its plan and exits 0. Refusals never carry a plan in the same envelope
(SPEC-201).

| Code | Exit | Raised by | Meaning |
|---|---|---|---|
| `POLICY_LEVEL_TOO_LOW` / `POLICY_HUMAN_ONLY` / `POLICY_UNKNOWN_ACTION` / `POLICY_ACTION_DENIED` | 4 | `policy.require` (SPEC-201) | Unchanged codes; new effective level |
| `POLICY_NOT_ON_BASE` | warning | `policy.load` | Base copy missing or lower; effective level lowered |
| `IDENTITY_MISMATCH` | 4 | Gitea client | Token login differs from the role's login |
| `UNSUPPORTED_OP` | 4 | `GiteaClient.send`, plan applier | Op outside the endpoint table or the skill's allow-list |
| `ROLE_NOT_AUTHORIZED` | 4 | `labels_plan.py`, applier | Actor role differs from `required_role` |
| `LEASE_REQUIRED` / `LEASE_EXPIRED` / `LEASE_HELD_BY_OTHER` | 4 | `_skillkit.leases`, `lease.py` | Lease missing, expired, or held by another session |
| `POLICY_PATH_TOUCHED` / `PROTECTED_BRANCH` | 4 | commit step | Critical policy path, or a branch that is not `agent/pse/` |
| `BRANCH_NOT_OWNED` / `FORCE_PUSH_REFUSED` / `PUSH_NON_FAST_FORWARD` / `REMOTE_HOST_MISMATCH` / `URL_HAS_CREDENTIALS` | 4 | push step, `_skillkit.gitrepo` | Push outside the guardrails |
| `GIT_COMMAND_FORBIDDEN` | 4 | `_skillkit.gitrepo` (SPEC-201) | Git subcommand outside the allowlist, which R2 extends only with the named write helpers |
| `REVIEW_NOT_INDEPENDENT` / `APPROVAL_WITHOUT_PASSING_GATE` | 4 | `review_verdict.py --comment-plan --post` | Independence or quality-gate rule broken |
| `REVIEW_ROUNDS_EXHAUSTED` | 4 | `review_request.py` (SPEC-201) | Fourth round requested; a human decides |
| `LOCAL_INFERENCE_GATED` | 4 | installer (SPEC-201 code) | No matching `ENABLED` record |
| `SMOKE_REPO_NOT_SANDBOX` / `LIVE_SMOKE_REQUIRED` | 4 | smoke test, client | Live safety rules |
| `VERSION_CONFLICT` / `PLAN_STALE` | 1 | client, applier, kanban | Target changed since it was read or planned |
| `LEASE_MIRROR_CONFLICT` | 1 | `lease.py --mirror` | Another session's active mirror is on the issue; `grantable: false` |
| `STATE_NOT_READY` / `DEPENDENCY_OPEN` / `WRITE_SET_CONFLICT` / `CONTRACT_MISSING` | 1 | dispatch | Claiming preconditions not met |
| `SCOPE_VIOLATION` | 1 | commit step (SPEC-201 code) | Changed path outside the write domains |
| `CHECK_NOT_EXECUTED` / `CHECK_LOG_DIGEST_MISMATCH` / `CHECK_RAN_ON_DIFFERENT_COMMIT` / `CHECK_RAN_ON_DIRTY_TREE` / `CHECK_STATUS_MISMATCH` / `AC_WITHOUT_EVIDENCE` | 1 | `evidence_manifest.py` | Evidence not backed by an executed check |
| `VERDICT_STALE` / `PR_NOT_OPEN` | 1 | `review_verdict.py --comment-plan --post` | Head moved, or the PR is closed |
| `NOTHING_TO_COMMIT` / `WORKTREE_CONFLICT` / `LABEL_NOT_EXCLUSIVE` / `NOT_CONVERGED` / `CLOSE_PENDING` (warning) | 1 | delivery, applier, completion | Precondition failed, or human follow-up needed |
| `BRANCH_PROTECTION_NONCOMPLIANT` | 1 | `branch_audit.py` | Audit done; the policy fails |
| `L1_NOT_ENABLED` / `SUITE_UNKNOWN` (reason) | 1 | `skill-lab gate l1` | Gate evaluated: `NOT_ENABLED` |
| `NUM_CTX_TOO_SMALL` | 1 | `skill-lab doctor` | Local context below 32768 |
| `GITEA_UNREACHABLE` / `GITEA_AUTH` / `GITEA_RATE_LIMITED` / `GITEA_SCHEMA_DRIFT` / `VERIFY_AFTER_WRITE_FAILED` / `GITEA_NOT_CONFIGURED` | 3 | client, smoke test | External failure; the outcome is recorded |
| `GIT_REMOTE_FAILED` | 3 | push step | Network or remote error during the push |
| `CLAUDE_CLI_NOT_FOUND` / `CLAUDE_CLI_FAILED` | 3 | `review_local.py` (SPEC-201) | Fallback reviewer unavailable; no verdict recorded |
| `OLLAMA_UNREACHABLE` / `JEV_UNAVAILABLE` | 3 | bench, doctor | Live inference or grader unavailable after retries; in bench the case is `errored` and the run does not count (`outage`, SPEC-105 FR-003) |
| `CRITERIA_BELOW_FLOOR` | 2 | `skill-lab score` (SPEC-105) | A per-skill gate is below the floor |
| `RUN_NOT_COUNTING` / `RUN_DEGRADED` | warning | bench (SPEC-105) | Replay, partial, outage, or degraded run; it cannot satisfy a live gate |
| `NO_LIVE_RUN` / `LIVE_RUN_STALE` | reason (`not_run`) | `release check` (SPEC-201) | No recorded run for the tree under review; the merge is blocked |
| `CONFIG_INVALID` / `FIXTURE_INVALID` / `USAGE` | 2 | config, double, CLI | Bad input |

**Partial failure.** Multi-operation commands call `require()` for every operation first (SPEC-201 FR-007). They then
stop at the first operation that does not succeed, exit with its code, and set `apply-report.complete` to false.
Operations that already succeeded keep their receipts. Re-running resumes; it never undoes. No R2 command deletes Gitea
objects, except the smoke test's own sandbox branch during cleanup.

## Security

- **Identity.** Each role uses its own Gitea account and token (D-3). Review's account is distinct, so the forge itself
  refuses self-approval, on top of FR-018. On GitHub, the factory repository's independence still rests on session IDs
  (SPEC-201 D-12), because one human account may post.
- **Policy file.** In R2 the policy file is a real authority boundary inside the scripts. Base-branch verification
  (FR-002) means a level raised in a worktree has no effect. The commit step refuses the file, the other critical policy
  paths (`skill-lab/benchmarks/criteria/**`, `skill-lab/benchmarks/monitor-limits.json`), and `.skill-gitea.json`, which
  names the identities and the base branch (FR-013). All are critical paths for merge-policy-gate (FR-022), so a diff
  touching them is `critical`. The runtime configs deny agent edits to them (SPEC-201 FR-012; the person's decision).
- **Secrets.** These come only from environment variables: `GITEA_TOKEN`, `OLLAMA_API_KEY`, and `TYPESAFE_API_KEY` or its
  alias `JEV_API_KEY`. They never go into argv, remote URLs, `check-run` records, comments, PR bodies, or state.
  `_skillkit.redact` masks them, and `_skillkit.checks` strips them from child processes (SPEC-201 FR-016). Canary tokens
  for every `SECRET_ENV_VARS` name, including R1's `GITEA_WEBHOOK_SECRET` and `GITEA_WEBHOOK_SECRET_PREVIOUS`, prove it
  (G-OFF-18). The release reviewer's environment holds none of the live keys (FR-049).
- **Monitoring.** Health reports carry resource figures only, never environment values or command lines. On local runs they
  carry only the figures of the run's own Rancher Desktop container, read from inside it; no Docker or containerd socket
  is opened and nothing else on the machine is read (FR-048).
- **Transport.** HTTPS is required for every non-loopback Gitea host. Live writes require a passing smoke report for the
  host (FR-041). Git transport credentials are the user's own git configuration; the scripts never handle them.
- **Untrusted input.** Issue and PR bodies, comments, review text, fixtures, and model output are data. Markers are
  honoured only from configured identities with a matching digest. `subprocess` always gets list arguments, never
  `shell=True`. Worktree and log paths go through `fsutil.safe_join`.
- **Authority layers.** These are deterministic: `_skillkit.policy` (clamp, base-branch check, catalog), the endpoint table
  without a merge row, the exact push refspec, the lease checks, and the scope check. The Zed, Claude Code, and Codex
  configs deny raw `git push`, force flags, and edits to policy, config, and sign-off paths. Those configs are guardrails,
  not a boundary (CONVENTIONS §7). The boundary is Gitea branch protection (BP-01..BP-12) plus least-privilege bot
  tokens, and the human merge on the factory repository.
- **Sign-off integrity.** A `human-signoff.v1` is an attestation, not authentication. It binds to run digests, so it
  cannot be reused for other evidence. The worst case of a forged sign-off is local inference enabled on the user's own
  machine. That is reversible, cloud stays installed, and a later failing run demotes it (FR-039). It is documented as
  residual risk RK-12.
- **Supply chain.** Stdlib only (CONVENTIONS §3). `git` and `claude` are external executables, and their versions are
  recorded in `check-run` and delivery records.

## Runtime compatibility

| Runtime | Inference | Invocation | R2 specifics |
|---|---|---|---|
| Zed Agent + Ollama Cloud (default, C1) | Every profile defaults to one Ollama Cloud model, reached through the local Ollama app signed in to ollama.com: provider `ollama` at `http://localhost:11434` (shape (a), the person's decision; SPEC-201 FR-039). SPEC-201 T112 verified the model ids; it did not choose the endpoint | `/speckit-development`, `/pse-implementer`, … | Scripts run through the terminal tool. The R2 PSE profile adds `always_allow` for `python3 .agents/skills/(pse-implementer\|speckit-development)/scripts/delivery_plan.py`, `always_confirm` for `--apply`, and `always_deny` for raw `git push`, `git commit --no-verify`, force flags, and edits to policy, config, and sign-off paths. A worktree from Zed's own picker is adopted by the worktree step when branch and base match (F-23). Ollama Cloud has no structured outputs (F-22): scripts produce the JSON, and the model relays it |
| Zed Agent + local Ollama (L1, gated) | `Lead (local)`, `PSE (local)`, `Review (local)` from `local-ollama.disabled.jsonc`, `max_tokens: 32768`, with local model ids on the same `ollama` provider at `http://localhost:11434` | same | Installed only with `ENABLED` (FR-037). The cloud profiles keep their `<model>:cloud` ids on the same provider and stay installed as the fallback; V-5 verifies that the signed-in app lists both. Check `ollama ps` for 100 % GPU and context 32768 (F-21). Fall back to the cloud profile per FR-039 |
| Claude Code | Claude models | `/speckit-development` | Skills from `.claude/skills/<name>`. The target-project template `skill-lab/config/claude/settings.example.json` denies `Bash(git push:*)` and allows the delivery scripts. The factory repository's own exported `.claude/settings.json` (SPEC-201) is unchanged, because the orchestrator pushes the release branch. It hosts the independent reviewer cloud session (step 7), whose environment holds no live keys (FR-049), and the `claude -p` fallback (`review_local.py`) |
| Codex | Codex models | `$speckit-development` | Skills from `.agents/skills/<name>`. The sandbox may block network for push and Gitea (V-7); then the scripts exit 3 and nothing is silently skipped. `skill-lab/config/codex/config.example.toml` documents the approval mode |

Every script is runtime-independent stdlib Python. Procedure paths are relative to the skill folder, and
`## Runtime notes` says how each runtime resolves it (CONVENTIONS §2).

## Autonomy policy

R2 adds no action ids. It raises `SUPPORTED_MAX_LEVEL` from `shadow` to `agent-implementation`, so the actions below,
already in SPEC-201's catalog (`catalog_version` 1.0.0), become executable. Each still requires `--apply`, the identity
check, the lease where marked, and its own preconditions. A human must have set `"level": "agent-implementation"` in
`.skill-policy.json` (with `set_by` the person's GitHub username, `Cazador0`; SPEC-201 refinement, set 1), and that file
must be committed on the base branch (FR-002). Raising a project's level is critical
risk and human-only (`policy.change`).

### Allowed at `agent-implementation` (19 actions; risk from SPEC-201)

| Action | Scope | Risk | R2 executor (roles) | Lease | Extra preconditions |
|---|---|---|---|---|---|
| `git.worktree.create` | local-git | medium | `delivery_plan.py --step worktree` (pse) | yes | Detached, under the state root, at `lease.base_commit` |
| `git.branch.create` | local-git | low | `--step branch` (pse) | yes | Name `agent/pse/<issue>-<slug>` only |
| `git.commit` | local-git | medium | `--step commit` (pse) | yes | Write domains; no policy paths; PSE identity |
| `git.push.branch` | remote-git | medium | `--step push` (pse) | yes | Exact refspec of the leased branch; never force |
| `gitea.issue.create` | forge | medium | `tasks_to_issues.py --apply` (lead) | no | Dedupe re-check before every create |
| `gitea.issue.update` | forge | low | same | no | Fields named in the plan only |
| `gitea.issue.assign` | forge | low | `dispatch_recommend.py --apply` (lead) | no | Assignee is the PSE identity |
| `gitea.issue.dependency.set` | forge | medium | `tasks_to_issues.py --apply` (lead) | no | Only if absent |
| `gitea.label.define` | forge | low | same | no | Fixed `state/*`, `spec/*`, `story/*` vocabulary; exclusive scope |
| `gitea.labels.set` | forge | low | `tasks_to_issues.py`, `labels_plan.py`, `dispatch_recommend.py`, `complete_issue.py` (`required_role` of the transition) | pse transitions: yes | Decision recomputed from live state |
| `gitea.milestone.set` | forge | low | `tasks_to_issues.py --apply` (lead) | no | Existing milestone only |
| `gitea.project.move_issue` | forge | low | none in R2 | — | Skipped: `PROJECT_COLUMNS_DEFERRED` |
| `gitea.comment.create` | forge | low | `checkpoint.py publish`, `comment_plan.py`, `arbitrate.py --publish`, `review_verdict.py --comment-plan` (lead, pse, review) | pse: yes | Marked comments only. The lease mirror comment is `lease.write.remote` alone (op `mirror_lease`, SPEC-201) |
| `gitea.pr.create` | forge | medium | `--step pr` (pse) | yes | Valid evidence for the head |
| `gitea.pr.update` | forge | low | `--step pr` (pse) | yes | Own PR's title and body only |
| `gitea.pr.review.request` | forge | low | speckit-development `delivery_plan.py --step review-request` (pse, lead) | no | Requested reviewer is the Review identity |
| `gitea.pr.review.submit` | forge | medium | `review_verdict.py --comment-plan --post --apply` (review) | no | Independence, freshness, quality gate |
| `lease.write.remote` | coordination | medium | `lease.py --mirror`, `dispatch_recommend.py --apply` (lead, pse), op `mirror_lease` | — | No foreign active mirror; posts only the marked lease comment |
| `review.session.request` | runtime | low | speckit-development `delivery_plan.py --step review-session` (pse, lead) | no | Writes a dispatch; never posts |

Still allowed at `shadow`, unchanged: `state.write.local`, `workspace.write`, `review.local.run`.

### Refused at `agent-implementation` (`POLICY_LEVEL_TOO_LOW`, SPEC-203 territory)

`git.push.force_own_branch`, `gitea.issue.close`, `gitea.pr.review.dismiss`, `gitea.pr.merge_when_checks_succeed`,
`lease.takeover`, `dispatch.session.start`, `events.gateway.serve`.

### Refused at every level (`POLICY_HUMAN_ONLY`)

`policy.change`, `git.push.protected`, `gitea.pr.merge`, `gitea.branch_protection.update`, `gitea.webhook.create`.

### What this level refuses, in words

Merging or scheduling a merge; closing issues; force-pushing or pushing anything but the leased branch; writing to a
protected branch; editing policy, criteria files, `monitor-limits.json`, CI, branch protection, webhooks (creating a
Gitea webhook stays human-only), runtime permission configs, or sign-offs; approving
one's own work; acting on a Gitea host that has not passed the smoke test; enabling local inference without its gate.

## Clarifications

### Session 2026-10-22

Recorded in SPEC-200 open-questions.md ("Answers recorded 2026-10-22" and its correction); they replace the defaults
named in synthesis.md §7.

- Q: (correction) How does R2 relate to R1 in branches and PRs? → A: Stacked PRs (intake A4): R2's branch is created from `release/r1-shadow` once R1 has an APPROVE verdict and its live gates passed, its PR targets `release/r1-shadow`, and it is retargeted to `main` when R1 merges; R3 stacks on R2 the same way; merges happen in order R1 → R2 → R3, each by a human.
- Q: Agents may not edit the per-skill criteria files, yet R1 planned one per skill. Who writes them? → A: Ship none in R1: R1 ships no per-skill criteria files; scoring falls back to the shared defaults (the floor); later only the person adds a file to raise a skill's bar. R2 likewise ships none (FR-043, §Release gates).
- Q: Should run-monitor also watch your own machine when work runs there (R2 local-inference runs, R3 webhook gateway)? → A: "run-monitor for Rancher Desktop local containers" (Q-10, OQ-22; FR-048).
- Q: How should run-monitor read your Rancher Desktop local containers? → A: From inside each container: run-monitor runs inside the container doing the work and reads that container's own CPU and memory limits and use; no Docker or containerd socket access; nothing else on the machine is read.
- Q: Which local model should the profiles use once local inference unlocks? → A: Decide at unlock time: list what fits the GPU at 32k context with tool support, verify it, and the person picks (Q-1, OQ-07).
- Q: Which R2 defaults should stay as written? → A: All four: three local parity runs (Q-4, OQ-11); L1 measured on the suite installed at unlock time (Q-9, OQ-12); one Gitea issue per task (Q-6, OQ-20); L1 can run alongside R3 and blocks neither the R2 merge nor R3 (Q-5, OQ-23).

## Assumptions

- R1 has its independent `APPROVE` and its live gates passed, and `release/r1-shadow` holds the reviewed head, before R2
  step 5 starts (release-plan.md E-1..E-3); R1 is merged into `main` before R2 merges (E-6).
  SPEC-201 delivers the interfaces listed in release-plan.md E-4, under the names in its spec, including SPEC-105's
  harness, which R1 delivers. T005 reconciles any rename before Phase 2.
- The person allowlists `ollama.com` and `api.typesafe.ai` and provides `OLLAMA_API_KEY` and `TYPESAFE_API_KEY` (or
  `JEV_API_KEY`) where the R2 live gate run executes. Until then the live gates are `not_run`, and R2 does not merge.
- The exported private repository `Cazador0/skill-factory` includes the engineering-team report (SPEC-201 refinement,
  set 1), so the reviewer can check every [R §…] citation.
- One PSE host at a time in R2 (D-7).
- The user's git credentials (SSH key or credential helper) can push to the Gitea remote; the scripts never manage
  git credentials.
- Gitea 28.x is the target. Older versions are best-effort and must pass the smoke test (SPEC-201 warns below 28.0.0).
- The Ollama Cloud model pinned by R1 stays available during an L1 streak. A model change, including a retirement,
  restarts the streak (SPEC-105 FR-010; D-17).
