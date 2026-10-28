# Feature Specification: `work-lease` skill

**Spec ID**: SPEC-007 | **Skill**: `skills/work-lease/` | **Family**: `control-plane` | **Used by**: PSE and Lead profiles, R3 gateway (CONVENTIONS §7)

**Created**: 2026-10-22 | **Status**: Draft (planned; written by SPEC-201 T078, extended by SPEC-203 T094)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-007, FR-010, FR-011, FR-024, FR-032, FR-033;
[SPEC-202](../202-release-agent-implementation/spec.md) FR-004, FR-005, FR-007, FR-009, FR-010, FR-027, FR-042..FR-044;
[SPEC-203](../203-release-guarded-autonomous/spec.md) FR-021, FR-022, FR-036..FR-039, FR-048, FR-050, FR-052, FR-053;
[SPEC-105](../105-jev-live-benchmarking/spec.md) FR-007, FR-008, FR-016. The release specs are authoritative; this spec refines them and never
contradicts them.

**Input**: the report's claiming sequence ("Atomically obtain lease: issue, role, session, expires"; "A lease should have a TTL and heartbeat,
but expiry must not automatically imply that another PSE may blindly continue in the same branch. Recovery first checks the branch, current
commits, PR, and last checkpoint"; report §Claiming work safely), its write-set rule (§Protecting against cross-agent conflicts), the single write
owner rule (§PSE contract), and the person's decisions in SPEC-201 §Clarifications and SPEC-200 open-questions.md (answers of 2026-10-22, final).

## Intent

A lease is the one claim that makes a session the single writer of a set of paths for a bounded time. The skill keeps leases in a local store
under `--state-dir` (the authority on a single host, ADR-0202), detects write-domain overlap before granting, and renews by heartbeat. R1 does all
of this locally (`state.write.local`) and only plans the Gitea mirror; R2 mirrors leases as marked issue comments and lets PSE delivery steps
verify them; R3 recovers expired leases from evidence and permits a takeover only with a fresh recovery record.

## User Scenarios & Testing *(mandatory)*

Scenarios run offline against the golden feature `skill-lab/fixtures/golden-feature/specs/042-session-refresh`: issue 184 covers T006 and T007
(domain `src/auth/tokens/**`), issue 185 covers T011 (`src/auth/tokens/families.py`), which overlaps it. Times use `--now`; T = 2026-10-22T08:00:00Z.
R2 and R3 add the in-process Gitea double (`--gitea-fixture`) and materialized repositories (`--repo-fixture`).

### User Story 1 - Acquire a lease with write-domain overlap detection (Priority: P1) · R1 shadow

**Actions**: `state.write.local` (minimum `shadow`). **Independent Test**: `skills/work-lease/tests/test_lease.py`.

1. **Given** an empty store, **When** `lease.py acquire --resource issue:184 --role pse --session pse-184-01 --write-domain 'src/auth/tokens/**'
   --apply --now T` runs, **Then** it exits 0 with a `lease.v1` that is `active`, `version` 1, `ttl_seconds` 1800, `heartbeat_at` T, and
   `expires_at` T + 1,800 s (SPEC-201 FR-024).
2. **Given** that lease, **When** session `pse-185-01` acquires issue 185 with domain `src/auth/tokens/families.py`, **Then** it exits 1
   `WRITE_SET_CONFLICT` with a `lease-check.v1` whose `grantable` is `false` and whose conflict names the lease and the overlapping domains
   (SPEC-201 US4 scenario 6).
3. **Given** no `--apply`, **When** `acquire` runs, **Then** it exits 0 with a `mutation-plan.v1` (one `state.write.local` request) and writes nothing.
4. **Given** level `shadow` and `"overrides": {"deny": ["state.write.local"]}`, **When** `acquire --apply` runs, **Then** it exits 4
   `POLICY_ACTION_DENIED` and writes nothing under `--state-dir` (SPEC-201 US1 scenario 4).
5. **Given** two processes acquiring overlapping domains at the same instant, **Then** exactly one lease is granted and the other gets
   `grantable: false` (file lock plus compare-and-swap).
6. **Given** the same session re-acquires the same resource and domains while its lease is active, **Then** the existing lease is returned unchanged.
7. **Given** `--ttl 299` or `--ttl 7201`, **Then** it exits 2 `TTL_OUT_OF_RANGE` and writes nothing.

### User Story 2 - Renew, release, status, and check (Priority: P1) · R1 shadow

**Actions**: `state.write.local` for renew and release; none for status and check. **Independent Test**: `skills/work-lease/tests/test_lease.py`.

1. **Given** the US1 lease, **When** `renew --lease <id> --session pse-184-01 --apply --now T+600` runs, **Then** `heartbeat_at` is T+600,
   `expires_at` is T+2,400, and `version` is 2.
2. **Given** `--expected-version 1` after that renew, **Then** it exits 1 `VERSION_CONFLICT` and nothing changes.
3. **Given** another session, **When** it renews or releases the lease, **Then** it exits 4 `LEASE_HELD_BY_OTHER`.
4. **Given** `--now` after `expires_at`, **When** the holder renews, **Then** it exits 4 `LEASE_EXPIRED`: expiry is never extended silently.
5. **Given** `release --apply`, **Then** `status` is `released` with `released_at` and `release_reason`, and an overlapping acquire is grantable.
6. **Given** a lease past `expires_at` and never released, **When** `status` runs, **Then** it reports `status: expired` without writing; **when**
   `check` runs for an overlapping request, **then** the lease still conflicts until it is released or recovered.

### User Story 3 - Plan and refuse the Gitea mirror at shadow (Priority: P1) · R1 shadow

**Actions**: `lease.write.remote` (minimum `agent-implementation`). **Independent Test**: `skills/work-lease/tests/test_lease.py::TestMirror`.

1. **Given** level `shadow`, **When** `acquire --mirror --repository owner/app` runs without `--apply`, **Then** it exits 0 with a `gitea-plan.v1`
   holding one `mirror_lease` operation (`action: lease.write.remote`, `POST /repos/{owner}/{repo}/issues/184/comments`).
2. **Given** level `shadow`, **When** `acquire --mirror --apply` runs, **Then** it exits 4 `POLICY_LEVEL_TOO_LOW`, writes no local lease, and the
   Gitea double logs no request (all-or-nothing, SPEC-201 FR-007).

### User Story 4 - Mirror the lease on the issue (Priority: P2) · R2 agent-implementation

**Actions**: `lease.write.remote` (minimum `agent-implementation`) plus `state.write.local`. **Independent Test**:
`skills/work-lease/tests/test_lease_mirror.py`; integration `skill-lab/tests/integration/test_r2_us3_lead_board.py` (SPEC-202 T089).

1. **Given** level `agent-implementation`, **When** `acquire --mirror --apply` runs on the double, **Then** the local lease exists and issue 184
   has one comment starting `<!-- skill-lab:lease:v1 key=<idempotency_key> digest=<sha256> -->` followed by one fenced `json` block holding the lease.
2. **Given** the same command again, **Then** the result is `already_applied` and the issue still has one such comment.
3. **Given** issue 184 shows an unexpired active mirror of session `pse-184-02` from a configured identity, **When** `pse-184-01` acquires with
   `--mirror --apply`, **Then** it exits 1 `LEASE_MIRROR_CONFLICT` with `grantable: false`, and nothing is written locally or remotely (SPEC-202 FR-027).
4. **Given** a marker from an unconfigured user, or one whose digest does not match its block, **Then** it is ignored as untrusted data.
5. **Given** `release --mirror --apply`, **Then** the local lease is `released` and a marked release comment is posted once.

### User Story 5 - Delivery steps trust only this store (Priority: P1) · R2 agent-implementation

**Actions**: none in this skill (the store is read by `_skillkit.leases.verify`, SPEC-202 FR-010). **Independent Test**:
`skill-lab/tests/test_skillkit_leases.py` (SPEC-202 T033) on stores written by `lease.py`.

1. **Given** a lease written by `lease.py acquire`, **When** a PSE delivery step verifies paths inside its domains, **Then** it passes.
2. **Given** a path outside the domains, an expired lease, or another session, **Then** verification raises `LEASE_REQUIRED`, `LEASE_EXPIRED`, or
   `LEASE_HELD_BY_OTHER` (exit 4).

### User Story 6 - Recover an expired lease from evidence (Priority: P2) · R3 guarded-autonomous

**Actions**: none without `--apply`; with `--apply`, `state.write.local` and `lease.write.remote` (minimum `agent-implementation`).
**Independent Test**: `skills/work-lease/tests/test_recover.py`; integration `test_r3_us5_recovery.py` (SPEC-203 T101).

1. **Given** issue 301's lease expired less than 600 s ago, **When** `recover --lease <id>` runs, **Then** the classification is `not_eligible` and
   it exits 1 `LEASE_NOT_EXPIRED` (SPEC-203 US5 scenario 1).
2. **Given** expiry over 600 s ago, no branch, no PR, and no push receipt, **When** `recover --apply` runs, **Then** the classification is
   `release_no_work` and the lease is `released`.
3. **Given** a valid checkpoint whose `head_commit` equals the remote head and the last push receipt, **Then** the classification is
   `resume_from_checkpoint` with `takeover.permitted: true`; **given** later commits by the PSE login with the expired session's trailer covered by
   receipts, **then** it is `resume_with_reverification` with `reverify_from` at the checkpoint head.
4. **Given** a dirty worktree, a foreign commit, an unexplained remote head, or commits without a checkpoint, **When** `recover --apply` runs,
   **Then** the classification is `escalate_human`, uncommitted changes are preserved as a patch under `<state-dir>/recovery/` and not applied, a
   marked comment is mirrored, and no branch, worktree, or commit is deleted. `blind_continuation` is always `false`.

### User Story 7 - Take over only with a fresh permitting record (Priority: P2) · R3 guarded-autonomous

**Actions**: `lease.takeover` (minimum `guarded-autonomous`). **Independent Test**: `skills/work-lease/tests/test_takeover.py`.

1. **Given** a `resume_*` recovery record at most 300 s old and an unchanged lease version, **When** the successor runs `takeover --recovery <file>
   --session pse-301-02 --apply`, **Then** a successor lease exists with the same issue, branch, base, and write domains.
2. **Given** a record older than 300 s, or a lease version that changed, **Then** it exits 1 `RECOVERY_STALE` or `VERSION_CONFLICT`; **given** no
   record, **then** exit 4 `RECOVERY_RECORD_REQUIRED`; **given** an `escalate_human` record, **then** exit 4 `TAKEOVER_NOT_PERMITTED`.
3. **Given** two successors racing on one record, **Then** exactly one takeover succeeds and the other exits 1 `VERSION_CONFLICT`.
4. **Given** level `agent-implementation`, or an active demotion, **Then** `takeover --apply` exits 4 `POLICY_LEVEL_TOO_LOW`.

### User Story 8 - Gateway handlers keep leases consistent with Gitea (Priority: P3) · R3 guarded-autonomous

**Actions**: as US6 for recovery; `state.write.local` and `lease.write.remote` for release. **Independent Test**: `skills/work-lease/tests/test_recover.py::TestHandlers`.

1. **Given** a `reconcile.tick`, **When** the gateway runs `lease.py recover --all-expired --apply`, **Then** every expired, unrecovered lease gets
   one recovery record, and a re-run writes nothing new.
2. **Given** `pull_request.merged` or `pull_request.closed` for PR 311, **When** `release --if-pr-closed --pr 311 --apply` runs, **Then** the
   active lease on that PR's branch is `released` with reason `pr_merged` or `pr_closed`; an open PR leaves it unchanged (exit 0, no-op).

### Edge Cases

- A lease file is unreadable, not strict JSON, or fails `lease.v1`: `acquire` and `check` refuse with `LEASE_STORE_INVALID` (exit 2), because an
  overlap cannot be ruled out; nothing is granted.
- The store lock is held longer than 10 s: exit 3 `LOCK_TIMEOUT`; retry later. Readers never take the lock (writes are atomic renames).
- Domains with wildcards (`src/*/tokens/**`) are compared on their static prefix, so they conflict with anything under `src/`.
- Two resources, disjoint domains: both granted. One resource, another session's active lease: conflict even with disjoint domains.
- The clock jumps back: expiry uses the single host's clock and `--now` (SPEC-202 D-7); Gitea timestamps never decide expiry.
- An issue comment forges a `skill-lab:lease:v1` marker: honoured only from a configured identity with a matching digest (SPEC-202 FR-009).
- The gateway's orchestration lease (`resource.type: orchestration`, SPEC-203 FR-022) shares the store; `status` shows it, and a second holder
  conflicts on the same resource.

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: The store MUST hold one bare `lease.v1` document per lease at `<state-dir>/leases/<lease_id>.json`, written atomically
  (`fsutil.atomic_write_json`) under the writer lock `<state-dir>/leases/.lock` (`fsutil.file_lock`); readers MUST NOT lock; no lease file is ever
  deleted. Resource types are `issue`, `pull_request`, `branch`, and `orchestration`. Implements: SPEC-201 FR-024; SPEC-203 FR-022.
- **FR-002**: `acquire` MUST create an `active` lease with `lease_id` `lse-` + 16 hex of the digest of resource, role, session, and `acquired_at`;
  `version` 1; `ttl_seconds` from `--ttl` (default 1,800, allowed 300..7,200, else exit 2 `TTL_OUT_OF_RANGE`); `heartbeat_at` = `acquired_at` =
  `--now`; `expires_at` = now + TTL; optional `branch` and `base_commit`; and write domains from `--write-domain` or the issue contract.
  Implements: SPEC-201 FR-024.
- **FR-003**: Before granting, `acquire` and `check` MUST compare the request with every stored `active` lease, including one past `expires_at`
  that was neither released nor recovered, and report each overlap in `lease-check.v1 conflicts[]`; a conflict exists when another session holds
  the same resource or when two domains' static prefixes are equal or one contains the other on a path-segment boundary. A refusal exits 1
  `WRITE_SET_CONFLICT`. Implements: SPEC-201 FR-024 (report §Claiming work safely).
- **FR-004**: `renew` MUST, for the holding session only, set `heartbeat_at` to now and `expires_at` to now + TTL and increment `version`; it MUST
  exit 1 `VERSION_CONFLICT` on a stale `--expected-version`, 4 `LEASE_HELD_BY_OTHER` for another session, 4 `LEASE_EXPIRED` after `expires_at`,
  and 4 `LEASE_REQUIRED` for an unknown lease. Implements: SPEC-201 FR-024.
- **FR-005**: `release` MUST, for the holding session only, set `status: released`, `released_at`, and `release_reason`, and increment `version`;
  releasing a released lease returns it unchanged with warning `ALREADY_APPLIED`. Implements: SPEC-201 FR-024.
- **FR-006**: `status` (by lease id or resource) MUST emit the stored `lease.v1` with `status: expired` computed when now ≥ `expires_at`, writing
  nothing (exit 1 `LEASE_NOT_FOUND` when none matches); `check` MUST emit `lease-check.v1` (exit 0 grantable, exit 1 `WRITE_SET_CONFLICT`) and
  write nothing. Implements: SPEC-201 FR-024.
- **FR-007**: Without `--apply`, mutating subcommands MUST emit their plan and exit 0: a `mutation-plan.v1` for local writes, and with `--mirror`
  a `gitea-plan.v1` op `mirror_lease` (action `lease.write.remote`). With `--apply` they MUST call `require_all` for every action first; at
  `shadow`, `--mirror --apply` exits 4 `POLICY_LEVEL_TOO_LOW` with nothing written. Implements: SPEC-201 FR-007, FR-024.
- **FR-008**: `lease.py` MUST follow CONVENTIONS §3 (stdlib, one envelope, exit codes 0–4, `--now` determinism, no write inside the skill folder);
  the deterministic-case seam `--seed-store DIR` MUST only read a fixture store or copy it into an empty store (else exit 2 `SEED_STORE_NOT_EMPTY`).
  Implements: SPEC-201 FR-032.
- **FR-009**: `SKILL.md` MUST satisfy CONVENTIONS §2 (`metadata.spec: SPEC-007`, `family: control-plane`, body ≤ 250 lines and 12 KB), name one
  command per step, state the behaviour per level, and tell the holder to renew at least every 600 s (TTL/3). Implements: SPEC-201 FR-032;
  SPEC-202 FR-042; SPEC-203 FR-053.
- **FR-010**: R1 MUST ship ≥ 4 deterministic cases including `overlap-detected.json`, a `policy` case tagged `action:lease.write.remote`, ≥ 5 agentic
  cases (≥ 1 `guardrail`) with fixtures inside the skill folder, ≥ 10 trigger cases (≥ 4 positive, ≥ 2 `expect_skill: null`, ≥ 1 naming
  `session-checkpoint`), and no per-skill criteria file. Implements: SPEC-201 FR-010, FR-011, FR-033; SPEC-105 FR-007, FR-016.

**R2 agent-implementation**

- **FR-011**: The store format of FR-001 MUST stay readable by `_skillkit.leases.verify(state_dir, issue, role, session_id, paths)`, which PSE
  delivery steps call; a format change MUST update both in one change. Implements: SPEC-202 FR-010.
- **FR-012**: `acquire|renew|release --mirror --apply` MUST post the marked lease comment through the shared write path (policy, identity, dedupe by
  idempotency key and marker, re-read, write, verify, receipt) using only the `mirror_lease` endpoint row, and MUST refuse with exit 1
  `LEASE_MIRROR_CONFLICT` (`grantable: false`, nothing written) when the issue shows an unexpired active mirror of another session from a configured
  identity. The local store stays the authority. Implements: SPEC-202 FR-004, FR-005, FR-009, FR-027.
- **FR-013**: Mirror writes MUST use the acting role's identity (`IDENTITY_MISMATCH`, exit 4) and carry only lease fields; no token MAY appear in
  output, comments, or state. Implements: SPEC-202 FR-007, FR-044.
- **FR-014**: R2 MUST add `mirror-applied.json` and `mirror-rerun.json`, the guardrail agentic case `agentic-r2-foreign-mirror`, and one positive and
  one negative trigger case. Implements: SPEC-202 FR-042, FR-043.

**R3 guarded-autonomous**

- **FR-015**: From R3, `lease.py` MUST take `DEFAULT_TTL_SECONDS` (1,800), `HEARTBEAT_MAX_INTERVAL_SECONDS` (600), and `TAKEOVER_GRACE_SECONDS` (600)
  from `_skillkit.leases`, and finish every network step within 120 s with 30 s per HTTP request. Implements: SPEC-203 FR-036.
- **FR-016**: `recover --lease <id> [--apply]` MUST inspect branch heads, commits since `base_commit` (≤ 50, with author, committer, and session
  trailer), push receipts, PR state, the last checkpoint (through `checkpoint.py resume-plan --recovery`), worktree, and mirror; apply rules
  R-0..R-9 in order through `_skillkit.recovery`; and emit `lease-recovery.v1` with `blind_continuation: false`. With `--apply` it marks the lease
  `expired` or `released`, preserves uncommitted changes as a patch, mirrors the classification, records an unexplained remote head (rule R-4) as
  a `lease_violation` incident (`autonomy-incident.v1` source `lease_recovery`), and never deletes a branch, worktree, or commit. Implements:
  SPEC-203 FR-037, FR-039.
- **FR-017**: `takeover --recovery <file> --session <id> --apply` (`lease.takeover`) MUST require a record ≤ 300 s old classified
  `resume_from_checkpoint` or `resume_with_reverification`, the lease in this host's store at the recorded version (compare-and-swap), and then
  create the successor lease with the same issue, branch, base, and domains; otherwise exit 4 `RECOVERY_RECORD_REQUIRED` or
  `TAKEOVER_NOT_PERMITTED`, or exit 1 `RECOVERY_STALE` or `VERSION_CONFLICT`. Implements: SPEC-203 FR-038.
- **FR-018**: The gateway handlers MUST be `recover --all-expired --apply` (every reconcile tick) and `release --if-pr-closed --pr <n> --apply`
  (`pull_request.closed`, `pull_request.merged`); `expired` lists expired, unrecovered leases read-only; re-runs write nothing new.
  Implements: SPEC-203 FR-021 (plan §Routing table).
- **FR-019**: R3 MUST add the four pair-5 cases (`applied`, `rerun`, `policy` at `agent-implementation` tagged `action:lease.takeover`, `demoted`),
  the AFV cases of SPEC-203 T118, T119, T121, T122, T124, T125, the agentic case `agentic-r3-classify-recovery`, one positive and one negative trigger
  case, and the recovery and takeover steps in `SKILL.md` ("never continue an expired lease without a recovery record"). Implements: SPEC-203
  FR-048, FR-050, FR-053.

### Key Entities

- **Lease**: one session's exclusive, expiring claim on a resource's write domains (`lease.v1`); the store keeps every lease ever granted.
- **Lease check**: whether a requested lease is grantable, and which leases and domains conflict (`lease-check.v1`).
- **Lease mirror** (R2): the marked issue comment that shows the lease on Gitea; the local store remains the authority.
- **Recovery record** (R3): the evidence-based classification of an expired lease (`lease-recovery.v1`), the only key to a takeover.

## Success Criteria *(mandatory)*

- **SC-001**: In concurrent acquire tests (two processes per race), exactly one overlapping lease is granted in 100 % of runs.
- **SC-002**: At `shadow`, `--mirror --apply` causes 0 Gitea writes and 0 local writes (SPEC-201 G-OFF-07).
- **SC-003**: 100 % of deterministic cases pass, and every subcommand run twice with the same `--now` and store gives byte-identical stdout.
- **SC-004**: R2: re-running a mirror makes 0 extra comments; a foreign active mirror causes 0 local or remote writes (SPEC-202 SC-002).
- **SC-005**: R3: 100 % of ≥ 14 recovery fixtures classify correctly and 0 takeovers happen without a fresh permitting record (SPEC-203 SC-008, G-OFF-16).
- **SC-006**: On each live gate run the skill meets SPEC-105's floor per skill and 100 % of its `guardrail` cases.

## Non-goals

- Multi-host lease authority (SPEC-203 release-plan); Gitea as the lease authority; leases on paths without a resource.
- Choosing what to dispatch (lead-architect); saving session progress (session-checkpoint); moving board states (kanban-state-machine).
- Taking over a lease from a stale, missing, or non-resume record; resolving a dirty worktree (human); deleting branches, worktrees, or commits.
- A per-skill criteria file (the person's answer, 2026-10-22).

## Contracts

**Emits** (producer): `lease` (owner, every level), `lease-check` (owner, R1), `lease-recovery` (owner, R3), `mutation-plan` (local-write plans,
shared contract), `gitea-plan` (op `mirror_lease`, shared contract), `apply-report` (R2 mirror applies through `_skillkit.plan_apply`, shared), and
`envelope`. **Consumes**: `issue-contract` (write domains), `autonomy-policy` and `action-catalog` (via `_skillkit.policy`), `mutation-request`,
`gitea-project`, `gitea-fixture`, `mutation-receipt` (R2 receipts; R3 push receipts), `session-checkpoint` and `resume-plan` (R3 recovery).

## Error semantics

Exit codes follow CONVENTIONS §3 with SPEC-202's reading (4 = not allowed, 1 = precondition failed, 3 = external, 2 = bad input); refusals carry no plan.

| Code | Exit | Subcommand | Meaning |
|---|---|---|---|
| `POLICY_LEVEL_TOO_LOW` / `POLICY_ACTION_DENIED` / `POLICY_HUMAN_ONLY` / `POLICY_UNKNOWN_ACTION` | 4 | all mutating | SPEC-201 FR-004 (also while demoted, R3) |
| `WRITE_SET_CONFLICT` | 1 | acquire, check | Overlap or same resource held by another session |
| `VERSION_CONFLICT` | 1 | renew, release, takeover | Compare-and-swap lost |
| `LEASE_REQUIRED` / `LEASE_EXPIRED` / `LEASE_HELD_BY_OTHER` | 4 | renew, release (and `_skillkit.leases` in R2) | Unknown lease / past expiry / not the holder |
| `LEASE_NOT_FOUND` (skill-local) | 1 | status | No lease matches the id or resource |
| `TTL_OUT_OF_RANGE` / `LEASE_STORE_INVALID` / `SEED_STORE_NOT_EMPTY` (skill-local) | 2 | acquire, check, seam | Bad TTL / unreadable store / seam misuse |
| `LOCK_TIMEOUT` | 3 | writers | Store lock busy; retry later |
| `LEASE_MIRROR_CONFLICT` | 1 | `--mirror` (R2) | Foreign active mirror on the issue |
| `IDENTITY_MISMATCH` / `UNSUPPORTED_OP` / `LIVE_SMOKE_REQUIRED` | 4 | `--mirror` (R2) | Client guardrails |
| `GITEA_UNREACHABLE` / `GITEA_AUTH` / `GITEA_SCHEMA_DRIFT` / `VERIFY_AFTER_WRITE_FAILED` | 3 | `--mirror`, recover (R2, R3) | External failure; re-run resumes |
| `LEASE_NOT_EXPIRED` / `RECOVERY_STALE` | 1 | recover / takeover (R3) | Within TTL or grace / record older than 300 s |
| `RECOVERY_RECORD_REQUIRED` / `TAKEOVER_NOT_PERMITTED` | 4 | takeover (R3) | No record / non-resume classification |
| `AUTONOMY_DEMOTED` | warning | all (R3) | Effective level lowered by a demotion |
| `ALREADY_APPLIED` (skill-local) | warning | release, mirror re-runs | Nothing new written |
| `USAGE` / `INPUT_NOT_FOUND` / `INPUT_NOT_JSON` / `INVALID_NOW` / `INTERNAL` | 2 | all | Bad input or unexpected exception |

## Security

- The store is a guardrail on a single host (ADR-0202); the boundary is still Gitea branch protection and the human merge. A session can edit
  `.skill-state/` by hand, which is why R2 delivery steps also check scope, branch, and identity, and R3 recovery checks commits and push receipts.
- Leases hold no secrets; mirror comments carry only lease fields, and all output passes `_skillkit.redact`.
- Issue comments are untrusted: markers count only from configured identities with matching digests, and nothing in a comment is executed.
- From R3, `skills/work-lease/**` is a critical policy path, so any change to this skill is `critical` risk and merged by a human (SPEC-203 FR-052).
- Takeover needs `lease.takeover` (guarded-autonomous) plus a fresh evidence record; expiry alone never transfers the branch (report §Claiming
  work safely).

## Runtime compatibility

| Runtime | Invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/work-lease`, loaded by the PSE and Lead profiles | One Ollama Cloud model through the local Ollama app signed in to ollama.com (`http://localhost:11434`, SPEC-201 FR-039) | Scripts make all JSON (no structured outputs). R3: the gateway runs handlers as subprocesses outside Zed |
| Zed Agent + local Ollama (after L1) | same | Local model on the same provider, context ≥ 32,768, chosen by the person at unlock time | Only after SPEC-202's L1 gate and the person's sign-off |
| Claude Code | `.claude/skills/work-lease`, `/work-lease` | Claude models | Same scripts and store |
| Codex | `.agents/skills/work-lease`, `$work-lease` | Codex models | Without network, `--mirror --apply` exits 3 at the foreign-mirror read, before the local write; a re-run resumes |

## Assumptions

- `_skillkit.fsutil.file_lock` and `atomic_write_json` exist (foundation); `_skillkit.policy` comes from SPEC-201 T017; `_skillkit.leases.verify`,
  `plan_apply`, and the hardened Gitea client from SPEC-202 T030–T034; `_skillkit.leases` constants and `recovery` from SPEC-203 T043–T044.
- One control-plane host and clone per repository (SPEC-202 D-7, SPEC-203 Assumptions).
- An expired lease that was neither released nor recovered keeps blocking overlapping acquires (FR-003); this is the conservative reading of the
  report's "expiry must not automatically imply ... blindly continue" and is listed for the person's confirmation.
