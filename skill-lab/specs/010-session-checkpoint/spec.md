# Feature Specification: `session-checkpoint` skill

**Spec ID**: SPEC-010 | **Skill**: `skills/session-checkpoint/` | **Family**: `control-plane` | **Used by**: Lead and PSE profiles (CONVENTIONS §7), R3 lease recovery

**Created**: 2026-10-28 | **Status**: Draft (planned; written by SPEC-201 T083, extended by SPEC-202 T051..T059 and SPEC-203 T094)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-007, FR-010, FR-011, FR-027, FR-032, FR-033;
[SPEC-202](../202-release-agent-implementation/spec.md) FR-009, FR-016, FR-042, FR-043, FR-044;
[SPEC-203](../203-release-guarded-autonomous/spec.md) FR-040, FR-048, FR-050, FR-053;
[SPEC-105](../105-jev-live-benchmarking/spec.md) FR-007, FR-008, FR-016. The release specs are authoritative; this spec refines them and never
contradicts them.

**Input**: the report's §Session checkpoint ("deliberately not chain-of-thought": decision, rationale summary, evidence, assumption, tool result,
changed state, unresolved question, next action), its recovery rule (§Claiming work safely: check branch, commits, PR, and last checkpoint), and the
person's decisions in SPEC-201 §Clarifications and SPEC-200 open-questions.md (answers of 2026-10-22, final).

## Intent

A checkpoint is the one compact, durable record that lets a replacement session continue without the old conversation. The skill writes it to a
local store, reads and renders it, and, before a successor trusts it, compares it with reality (branch, head commit, lease, issue state) in a
`resume-plan.v1`. The schema rejects every field outside the contract, so hidden reasoning has nowhere to live. R1 is entirely local
(`state.write.local`) and only plans the Gitea comment. R2 posts that comment once, marked and deduplicated. R3 adds recovery checks so lease
recovery can find the latest valid checkpoint and prove what happened since.

## User Scenarios & Testing *(mandatory)*

Scenarios run offline against the golden feature `skill-lab/fixtures/golden-feature/specs/042-session-refresh` and a scratch git repository built
from it: issue 184, branch `agent/pse/184-session-refresh`, session `pse-184-01`, head commit H1 (a later commit H2 exists in some fixtures).
Times use `--now`; T = 2026-10-22T08:00:00Z. R2 and R3 add the in-process Gitea double (`--gitea-fixture`).

### User Story 1 - Write, read, and render a checkpoint (Priority: P1) · R1 shadow

**Actions**: `state.write.local` (minimum `shadow`) for `write`; none for `read` and `render` (`render --out` writes only under `--out`).
**Independent Test**: `skills/session-checkpoint/tests/test_checkpoint.py`.

1. **Given** the report's example (role `pse`, issue 184, spec `SPEC-042`, three completed lines, decision `D-01`, evidence, empty blockers, a
   next action), **When** `checkpoint.py write --input cp.json --apply --now T` runs, **Then** it exits 0 with a `session-checkpoint.v1` stored under
   `<state-dir>/checkpoints/`, with a deterministic `checkpoint_id` (`ckp-` + 16 hex of its digest) in the envelope.
2. **Given** an input holding a `reasoning` field (or `thoughts`, `chain_of_thought`, any key outside the contract), **Then** it exits 1
   `CHECKPOINT_FIELD_NOT_ALLOWED` naming the key's JSON pointer, and writes nothing.
3. **Given** no `--apply`, **Then** it exits 0 with a `mutation-plan.v1` (one `state.write.local` request) and writes nothing.
4. **Given** level `shadow` and `"overrides": {"deny": ["state.write.local"]}`, **When** `write --apply` runs, **Then** it exits 4
   `POLICY_ACTION_DENIED` and writes nothing.
5. **Given** a stored checkpoint, **When** `read --issue 184 --session pse-184-01` runs, **Then** the same document is emitted; `read` of a missing
   one exits 1 `CHECKPOINT_NOT_FOUND`.
6. **Given** `render --checkpoint <file> --out out.md`, **Then** `out.md` follows `assets/templates/checkpoint.md` and a `rendered-document.v1`
   (`doc_kind: checkpoint`, `sha256`, `sources`) is emitted; the same input gives byte-identical output.
7. **Given** a line containing `GITEA_TOKEN=abc123...` or a bearer token, **Then** `write` redacts it with `_skillkit.redact` and adds warning
   `SECRET_REDACTED`; **given** a line longer than the schema limit, **Then** exit 2 `CHECKPOINT_INVALID`.

### User Story 2 - Resume plan that verifies the checkpoint against reality (Priority: P1) · R1 shadow

**Actions**: none (read-only). **Independent Test**: `skills/session-checkpoint/tests/test_checkpoint.py::TestResumePlan`.

1. **Given** a checkpoint with `head_commit` H1 and a scratch repo whose branch head is H1, **When** `resume-plan --checkpoint <file> --repo DIR` runs,
   **Then** `verified` holds `branch_exists`, `head_matches` as `pass`, `stale` is `false`, and `next_action` is the checkpoint's own.
2. **Given** the branch head is H2, **Then** `head_matches` is `fail`, `stale` is `true`, and `blockers` tells the successor to re-verify from H1
   before continuing; the checkpoint's `next_action` is still shown but not marked ready (SPEC-201 FR-027).
3. **Given** the branch is missing, **Then** `branch_exists` is `fail`; **given** the lease store (`--state-dir`) shows the checkpoint's lease
   expired or held by another session, **Then** `lease_valid` is `fail`; with no lease in the checkpoint it is `na`.
4. **Given** `--gitea-url` (read-only), **Then** `issue_open` is `pass` for an open issue and `fail` for a closed one; without it, `na`.
5. **Given** a successor that continues despite `stale: true`, **Then** nothing in the skill stops it; the SKILL.md rule and the PSE preflight do.

### User Story 3 - Plan and refuse publishing at shadow (Priority: P1) · R1 shadow

**Actions**: `gitea.comment.create` (minimum `agent-implementation`). **Independent Test**: `skills/session-checkpoint/tests/test_checkpoint.py::TestPublish`.

1. **Given** level `shadow`, **When** `publish --checkpoint <file> --repository acme/app` runs without `--apply`, **Then** it exits 0 with a
   `gitea-plan.v1` holding one operation (`action: gitea.comment.create`, `POST /repos/acme/app/issues/184/comments`, marker `skill-lab:session-checkpoint:v1`).
2. **Given** level `shadow`, **When** `publish --apply` runs, **Then** it exits 4 `POLICY_LEVEL_TOO_LOW` and the Gitea double logs no request (SPEC-201 FR-007).

### User Story 4 - Publish the handoff once (Priority: P2) · R2 agent-implementation

**Actions**: `gitea.comment.create` (minimum `agent-implementation`). **Independent Test**: `skills/session-checkpoint/tests/test_checkpoint_publish.py`;
integration `skill-lab/tests/integration/test_r2_us1_pse_delivery.py` (SPEC-202 T060).

1. **Given** level `agent-implementation` and a valid checkpoint, **When** `publish --apply` runs on the double, **Then** issue 184 has one comment starting
   `<!-- skill-lab:session-checkpoint:v1 key=<idempotency_key> digest=<sha256> -->` followed by one fenced `json` block holding the checkpoint.
2. **Given** the same command again, **Then** it is `already_applied` and the issue still has one such comment (deduplicated by digest).
3. **Given** role `pse` with no active lease for the issue in the local store, **Then** it exits 4 `LEASE_REQUIRED` and writes nothing remote.
4. **Given** a checkpoint line holding a token, **Then** the posted comment contains the redacted text and the canary token appears nowhere.
5. **Given** an identity other than the acting role's, **Then** exit 4 `IDENTITY_MISMATCH`; the comment is posted as the role's login only.

### User Story 5 - Resume from recovery evidence (Priority: P2) · R3 guarded-autonomous

**Actions**: none (read-only). **Independent Test**: `skills/session-checkpoint/tests/test_resume_recovery.py`; integration `test_r3_us5_recovery.py` (SPEC-203 T101).

1. **Given** `--recovery` with a PR, push receipts, and a remote head equal to the checkpoint's head, **Then** `verified` adds `pr_state`,
   `descendant_of_checkpoint`, `commit_attribution`, and `push_receipts_match` as `pass`, and `resume-plan.v1` carries `recovery_ref`.
2. **Given** later commits by the PSE login with the expired session's trailer and covered by receipts, **Then** `descendant_of_checkpoint`,
   `commit_attribution`, and `push_receipts_match` pass and `stale` is `true` with the re-verification point at the checkpoint head.
3. **Given** a foreign commit, a head that is not a descendant, or commits with no receipt, **Then** the matching check is `fail` and
   `blockers` names it; the skill never classifies or takes over (that is `work-lease recover`).
4. **Given** several checkpoints for one (issue, branch), local and as marked comments, **Then** the latest valid one is chosen; comments count only
   from configured identities with a matching digest, and an unconfigured user's checkpoint comment is ignored as data.
5. **Given** a stale checkpoint (older head than the chosen one), **Then** it is rejected for resume with `CHECKPOINT_STALE`.

### Edge Cases

- Two checkpoints written in the same second for one session: ids differ by digest; `read` without `--checkpoint` returns the newest by `created_at`, ties broken by id.
- A stored file is not strict JSON or fails `session-checkpoint.v1`: `read` and `resume-plan` exit 2 `CHECKPOINT_INVALID`; it is never repaired in place.
- The repo path is not a git repository or `git` is missing: checks needing it are `na` with detail; exit 0 unless `--require-repo` (exit 2 `REPO_REQUIRED`).
- `head_commit` null (a checkpoint taken before any commit): `head_matches` is `na`; the plan says no commit to verify.
- A `decisions[].source` path that does not exist in `--repo`: warning `DECISION_SOURCE_MISSING`, not an error (the source may be on another branch).
- `lease.expires_at` in the past at `--now`: `lease_valid` is `fail`; the checkpoint is still readable.
- A comment body edited after posting: digest mismatch, ignored; the next `publish` posts a new comment only when the local digest differs from every valid one.

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: `checkpoint.py write` MUST validate its input against `session-checkpoint.v1` (`additionalProperties: false` at every level, line
  and array limits from the schema), exit 1 `CHECKPOINT_FIELD_NOT_ALLOWED` with the JSON pointer of the first disallowed key, and with `--apply`
  (`state.write.local`) store `<state-dir>/checkpoints/<checkpoint_id>.json` atomically under a writer lock; without `--apply` it MUST emit a
  `mutation-plan.v1` and write nothing. Implements: SPEC-201 FR-027, FR-007.
- **FR-002**: `checkpoint_id` MUST be `ckp-` + 16 hex of the SHA-256 of the canonical JSON; `created_at` comes from `--now`; the same input and `--now`
  MUST give a byte-identical stored file and envelope; a stored file MUST NOT be overwritten or deleted. Implements: SPEC-201 FR-027, FR-032.
- **FR-003**: Every free-text value MUST pass `_skillkit.redact` before storage, with warning `SECRET_REDACTED` when anything changed; the skill MUST
  NOT accept narrative reasoning: only the contract's fields (goal, completed, decisions with a source, evidence lines, blockers, next action,
  unresolved questions) exist. Implements: SPEC-201 FR-027 (report §Session checkpoint).
- **FR-004**: `read` MUST emit the stored `session-checkpoint.v1` selected by `--checkpoint` (file or id) or by `--issue` plus `--session`, newest
  first, writing nothing (exit 1 `CHECKPOINT_NOT_FOUND`, exit 2 `CHECKPOINT_INVALID`). Implements: SPEC-201 FR-027.
- **FR-005**: `render` MUST produce a Markdown document from `assets/templates/checkpoint.md` and emit `rendered-document.v1` (`doc_kind:
  checkpoint`) with the `sha256` of the output and the source checkpoint; writing is only under `--out`. Implements: SPEC-201 FR-027.
- **FR-006**: `resume-plan` MUST emit `resume-plan.v1` with `verified[]` entries `branch_exists`, `head_matches`, `lease_valid`, and `issue_open`
  (`pass`, `fail`, or `na` with detail), `stale: true` when `head_matches` fails, the checkpoint's `next_action`, and `blockers[]`; it MUST be read-only
  (git by list-argument subprocess in read mode, the Gitea read-only client for `issue_open`) and MUST NOT run the next action. Implements: SPEC-201 FR-027.
- **FR-007**: `publish` without `--apply` MUST emit a `gitea-plan.v1` with one `gitea.comment.create` operation carrying the marker grammar of
  SPEC-202 FR-009; with `--apply` at `shadow` it MUST exit 4 `POLICY_LEVEL_TOO_LOW` with nothing sent (all-or-nothing). Implements: SPEC-201 FR-007, FR-027.
- **FR-008**: `checkpoint.py` MUST follow CONVENTIONS §3 (stdlib, one envelope, exit codes 0-4, `--now`, no write inside the skill folder); the
  deterministic-case seam `--seed-store DIR` MUST only read a fixture store or copy it into an empty store (else exit 2 `SEED_STORE_NOT_EMPTY`).
  Implements: SPEC-201 FR-032.
- **FR-009**: `SKILL.md` MUST satisfy CONVENTIONS §2 (`metadata.spec: SPEC-010`, `family: control-plane`, body ≤ 250 lines and 12 KB), name one command
  per step, state the behaviour per level, and tell the session to write a checkpoint on stop, handoff, or replacement and to run `resume-plan` first
  when it starts from one. Implements: SPEC-201 FR-032.
- **FR-010**: R1 MUST ship ≥ 4 deterministic cases including `rejects-chain-of-thought-fields.json` and a `policy` case tagged
  `action:gitea.comment.create`, ≥ 5 agentic cases (≥ 1 `guardrail`) with fixtures inside the skill folder, ≥ 10 trigger cases (≥ 4 positive, ≥ 2
  `expect_skill: null`, ≥ 1 naming `work-lease`), and no per-skill criteria file. Implements: SPEC-201 FR-010, FR-011, FR-033; SPEC-105 FR-007, FR-016.

**R2 agent-implementation**

- **FR-011**: `publish --apply` (`gitea.comment.create`) MUST post the checkpoint as one marked issue comment `<!-- skill-lab:session-checkpoint:v1
  key=<idempotency_key> digest=<sha256> -->` plus one fenced `json` block through the shared write path (policy, identity, dedupe by digest and marker,
  re-read, write, verify, receipt), deduplicate by digest, and emit `apply-report.v1`; a re-run MUST be `already_applied` with 0 new writes.
  Implements: SPEC-202 FR-016, FR-009.
- **FR-012**: For role `pse`, `publish --apply` MUST require an active lease for the issue in the local store (`LEASE_REQUIRED`, `LEASE_EXPIRED`,
  `LEASE_HELD_BY_OTHER`, exit 4) and MUST post with the role's own identity (`IDENTITY_MISMATCH`, exit 4); no token MAY appear in output, comments,
  or state. Implements: SPEC-202 FR-016, FR-010, FR-044.
- **FR-013**: R2 MUST add `publish-applied.json`, `publish-rerun.json`, the agentic case `agentic-r2-publish-handoff` with a Jev judgment, the
  trigger cases `trigger-r2-save-progress` (positive) and `trigger-r2-neg-claim-issue` (expects `work-lease`), and the publish step with its lease
  rule in `SKILL.md`. Implements: SPEC-202 FR-042, FR-043.

**R3 guarded-autonomous**

- **FR-014**: `resume-plan --recovery` MUST add the verified checks `pr_state`, `descendant_of_checkpoint`, `commit_attribution`, and
  `push_receipts_match` to `resume-plan.v1` and set `recovery_ref`, from the PR, commits since the checkpoint head (author, committer, session
  trailer), and push receipts; a failed check MUST appear in `blockers[]`, and the skill MUST NOT classify, release, or take over a lease. Implements:
  SPEC-203 FR-040.
- **FR-015**: The skill MUST find the latest valid checkpoint for an (issue, branch) pair among local records and marked issue comments, honouring
  a comment only when authored by a configured identity (`gitea-project.v1`) and its digest matches its block, and MUST reject a checkpoint whose
  head is older than the chosen one for resume (`CHECKPOINT_STALE`). Implements: SPEC-203 FR-040, FR-048 (grounding, prompt-injection).
- **FR-016**: R3 MUST add the agentic cases `agentic-r3-recovery-checkpoint-summary` and `agentic-r3-resume-from-recovery`, the AFV cases of SPEC-203
  T120, T121, and T126, one positive and one negative trigger case ("resume from my last checkpoint" positive; "the PSE session died, recover
  issue 301" negative, `work-lease`), and the recovery step in `SKILL.md`. Implements: SPEC-203 FR-048, FR-050, FR-053.

### Key Entities

- **Checkpoint**: the compact continuity record of a session (`session-checkpoint.v1`); the store keeps every checkpoint ever written.
- **Resume plan**: the checkpoint compared with branch, head, lease, issue, and (R3) PR and receipts, with `stale` and `blockers` (`resume-plan.v1`).
- **Checkpoint comment** (R2): the marked issue comment that carries a checkpoint to a successor on another host; the local store stays primary.
- **Rendered checkpoint**: the Markdown view for a human (`rendered-document.v1`, `doc_kind: checkpoint`).

## Success Criteria *(mandatory)*

- **SC-001**: 100 % of inputs holding any key outside the contract (including `reasoning`) are rejected and 0 are stored.
- **SC-002**: A head mismatch yields `stale: true` in 100 % of fixtures; a matching head yields `stale: false`.
- **SC-003**: 100 % of deterministic cases pass, and every subcommand run twice with the same `--now` and store gives byte-identical stdout.
- **SC-004**: At `shadow`, `publish --apply` causes 0 Gitea writes (SPEC-201 G-OFF-07). R2: re-running `publish` makes 0 extra comments (SPEC-202 SC-002).
- **SC-005**: R3: 100 % of the recovery fixtures report the expected failed checks, and 0 checkpoint comments from unconfigured identities are used.
- **SC-006**: On each live gate run the skill meets SPEC-105's floor per skill and 100 % of its `guardrail` cases.

## Non-goals

- Storing, summarizing, or reconstructing a model's chain of thought; any field beyond the contract.
- Claiming or renewing leases (work-lease); classifying an expired lease or taking it over (`work-lease recover|takeover`); choosing what to dispatch (lead-architect).
- Running the checkpoint's `next_action`; moving board states; editing issues other than posting the marked comment (R2).
- Conversation compaction or memory for a runtime; a per-skill criteria file (the person's answer, 2026-10-22).

## Contracts

**Emits** (producer): `session-checkpoint` (owner, every level), `resume-plan` (owner, R1; R3 adds checks and `recovery_ref`), `rendered-document`
(shared contract, `doc_kind: checkpoint`), `mutation-plan` (local-write plans, shared), `gitea-plan` (publish plan, shared), `apply-report` (R2
publish, shared), and `envelope`. **Consumes**: `lease` (read-only, from `work-lease`'s store), `autonomy-policy` and `action-catalog` (via
`_skillkit.policy`), `mutation-request`, `gitea-project`, `gitea-fixture`, `mutation-receipt` (R2 receipts; R3 push receipts), `lease-recovery`
(R3, referenced by `recovery_ref` only).

## Error semantics

Exit codes follow CONVENTIONS §3 with SPEC-202's reading (4 = not allowed, 1 = precondition failed, 3 = external, 2 = bad input); refusals carry no plan.

| Code | Exit | Subcommand | Meaning |
|---|---|---|---|
| `CHECKPOINT_FIELD_NOT_ALLOWED` (skill-local) | 1 | write | A key outside `session-checkpoint.v1`, with its JSON pointer |
| `CHECKPOINT_NOT_FOUND` (skill-local) | 1 | read, render, resume-plan, publish | No stored checkpoint matches |
| `CHECKPOINT_STALE` (skill-local) | 1 | resume-plan (R3) | A newer valid checkpoint exists for the pair |
| `CHECKPOINT_INVALID` / `REPO_REQUIRED` / `SEED_STORE_NOT_EMPTY` (skill-local) | 2 | all | Schema-invalid input or store file / no repo / seam misuse |
| `POLICY_LEVEL_TOO_LOW` / `POLICY_ACTION_DENIED` / `POLICY_HUMAN_ONLY` / `POLICY_UNKNOWN_ACTION` | 4 | write, publish | SPEC-201 FR-004 (also while demoted, R3) |
| `LEASE_REQUIRED` / `LEASE_EXPIRED` / `LEASE_HELD_BY_OTHER` | 4 | publish (R2, role `pse`) | No usable lease for the issue |
| `IDENTITY_MISMATCH` / `UNSUPPORTED_OP` / `LIVE_SMOKE_REQUIRED` | 4 | publish (R2) | Client guardrails |
| `LOCK_TIMEOUT` | 3 | write | Store lock busy 10 s; retry later |
| `GITEA_UNREACHABLE` / `GITEA_AUTH` / `GITEA_SCHEMA_DRIFT` / `VERIFY_AFTER_WRITE_FAILED` | 3 | publish (R2), resume-plan with `--gitea-url`, R3 | External failure; a re-run resumes |
| `SECRET_REDACTED` / `DECISION_SOURCE_MISSING` / `ALREADY_APPLIED` / `AUTONOMY_DEMOTED` | warning | as named | Informational |
| `USAGE` / `INPUT_NOT_FOUND` / `INPUT_NOT_JSON` / `INVALID_NOW` / `INTERNAL` | 2 | all | Bad input or unexpected exception |

## Security

- A checkpoint holds no secrets: free text is redacted on write and again on publish; tokens never appear in output, comments, or state.
- Hidden reasoning is out of scope by construction: the schema forbids unknown keys, so a checkpoint cannot smuggle chain of thought or instructions.
- Checkpoint comments and files are untrusted data: a marker counts only from a configured identity with a matching digest; nothing in a checkpoint is
  executed, and `next_action` is text for a successor to weigh against `resume-plan`, never a command the skill runs.
- `resume-plan` is read-only and runs git by list-argument subprocess only; paths with `..` or outside `--repo` are rejected.
- The boundary remains Gitea branch protection plus the human merge; SPEC-203 FR-052 does not list this skill as a critical policy path, so an ordinary change is classified by the merge gate's path rules.

## Runtime compatibility

| Runtime | Invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/session-checkpoint`, loaded by the Lead and PSE profiles | One Ollama Cloud model through the local Ollama app signed in to ollama.com (`http://localhost:11434`, SPEC-201 FR-039) | Scripts make all JSON (no structured outputs); the model only fills the input fields |
| Zed Agent + local Ollama (after L1) | same | Local model on the same provider, context ≥ 32,768, chosen by the person at unlock time | Only after SPEC-202's L1 gate and the person's sign-off; a checkpoint is what makes a short-context restart safe |
| Claude Code | `.claude/skills/session-checkpoint`, `/session-checkpoint` | Claude models | Same scripts and store |
| Codex | `.agents/skills/session-checkpoint`, `$session-checkpoint` | Codex models | Without network, `publish --apply` exits 3 at the first Gitea read; a re-run resumes |

## Assumptions

- `session-checkpoint.v1` (foundation contract) is canonical and unchanged by R1; `resume-plan.v1`, `rendered-document.v1`, `mutation-plan.v1`
  come from SPEC-201's contract tasks; `_skillkit.policy` from T017, `plan_apply` and the hardened Gitea client from SPEC-202 T030..T034, `recovery` from SPEC-203 T043..T044.
- The checkpoint store is per host, like the lease store; a successor on another host reads the marked comment (R2) rather than the local file.
- `decisions[].source` is a repo-relative path or null; its existence is a warning, because it can live on another branch.
- A checkpoint is written by the session itself (or the Lead for a dead session) from recorded facts; the skill cannot verify "completed" claims,
  which is why `resume-plan` checks branch, head, lease, and (R3) commits and receipts instead.
