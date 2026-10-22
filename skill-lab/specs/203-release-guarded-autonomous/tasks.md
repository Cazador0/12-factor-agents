---

description: "Task list for SPEC-203 R3 Guarded autonomous mode"
---

# Tasks: R3 Guarded autonomous mode

**Input**: Design documents from `skill-lab/specs/203-release-guarded-autonomous/` (spec.md, plan.md, synthesis.md, release-plan.md)

**Prerequisites**: plan.md (required), spec.md (required for user stories), entry criteria E-1..E-6 (release-plan.md §3): R2 approved, merged to `main` by a human with every merge-stage gate passing (its live gates included), R2 and SPEC-105 interfaces present

**Tests**: Requested. Every implementation task follows a task that writes its tests first, and those tests are seen to fail on assertions before implementation.

**Organization**: Tasks are grouped by user story (spec.md US1–US9) so each story can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependency on an incomplete task)
- **[Story]**: Which user story this task belongs to (US1–US9)
- Paths are relative to the repository root (`Cazador0/skill-factory` checkout on branch `release/r3-guarded-autonomous`, created from `main` at the R2 merge commit)
- Dependency semantics follow SPEC-201 plan.md §Wave rule: a task without `[P]` depends on the nearest preceding task in its phase; `(depends on …)` adds explicit edges
- **Verification** of a task = the test files and lab commands named in its description. `/speckit-development` closes a task only through `dev_state.py mark --task Tnnn --apply`, which requires a passing `check-run.v1` for each

## Path Conventions

- Shared code: `skill-lab/shared/_skillkit/` (canonical), vendored into `skills/<name>/scripts/_skillkit/` by `skill-lab sync`
- Contracts: `skill-lab/contracts/schemas/`, vendored into `skills/<name>/assets/schemas/`
- Lab: `skill-lab/lab/`, tests in `skill-lab/tests/`, integration tests in `skill-lab/tests/integration/`
- Skills: `skills/<name>/{SKILL.md,scripts,references,assets,evals,tests}`
- Release evidence: `skill-lab/specs/203-release-guarded-autonomous/evidence/`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Entry check, alignment with R1 and R2, verification of the facts R3 must not assume, and the decisions on record

- [ ] T001 Run the R3 entry check: E-1 (R2 verdict accepted by `review_collect.py`), E-2 (a human merged the R2 PR into `main`; merge commit SHA and `git merge-base --is-ancestor <reviewed head> <merge commit>`), E-3 (`skill-lab release check --spec SPEC-202 --stage merge` on the reviewed head: every gate `pass`, live gates included), E-4 (the run ids and `benchmark-run.v1` digests in SPEC-202's `evidence/live-runs.json`, each under `skill-lab/benchmarks/runs/`; no R2 live gate `fail` or `not_run`; if SPEC-202 as built still has a `complete` stage, it passes too), E-6 (this folder's six artifacts); record exit codes and digests in `skill-lab/specs/203-release-guarded-autonomous/evidence/entry-check.json`. R3 step 5 does not start before E-2 holds (the person's decision: R3 entry = R2 merged)
- [ ] T002 Record the real names of every SPEC-202 and SPEC-201 interface in plan.md §Interface alignment (modules, lab commands, contract names, R1's normalized event-type vocabulary and seen-set format, R2 merge-decision gate ids, the installer's source-commit record used by promotion criterion P-8) and the status of cross-release items X-1..X-10 in `skill-lab/specs/203-release-guarded-autonomous/evidence/r2-alignment.json` (T151 adds X-11..X-15); list every mapped rename for later tasks
- [ ] T151 [P] Check cross-release items X-11..X-15 against R1 and R2 as delivered and record the result in `skill-lab/specs/203-release-guarded-autonomous/evidence/r2-alignment.json`: X-11 (14 skills; `run-monitor` is SPEC-014 with `metadata.family: control-plane`, `metadata.secondary_family: meta`, and SPEC-202's `--host-metrics off`), X-12 (SPEC-105 delivered: `_defaults.json` floor, `score --strict` and `--catalog`, `criteria.below-floor`, the eval minimums in `eval-inventory-r1`, `skill-lab streak`, `skill-lab report`, `release record-run`, `benchmark-run.v1` fields `counts_toward_streak`, `exclusion_reasons`, `suite_digest`, `health_reports`, `catalog{…}`, `run-health.v1`, `prices.json`, `monitor-limits.json`), X-13 (R1's four webhook layers: `body_sha256` and `stale` in `normalized-event.v1`, the body-digest seen set with 90-day retention, the freshness record path, `GITEA_WEBHOOK_SECRET_PREVIOUS` with `GITEA_WEBHOOK_SECRET_ROTATED_AT`, `WEBHOOK_SECRET_TOO_SHORT`, `EVENT_RATE_LIMITED`, `references/webhook-hygiene.md`), X-14 (SPEC-202's L1 gate reads `benchmark-streak.v1`), X-15 (SPEC-201 and SPEC-202 have their live gates in the `merge` stage); also record where the installed Zed profiles name their model (input of P-8, FR-056). Record every rename in plan.md §Interface alignment; never assume a name (depends on T002)
- [ ] T003 [P] Verify Gitea facts V-1..V-9 and V-11 against `skill-lab/docs/research/vendor/gitea-28.2.0-swagger.v1.json` (SPEC-202 T003) and the Gitea 28.x docs; append the merge body fields, cancel endpoint, dismissal endpoint, review and pull fields, permissions, commit-to-PR lookup, BP-09 field, webhook delivery behaviour, and issue filters to `skill-lab/docs/research/SOURCES.md` §Gitea with source and date; write `skill-lab/specs/203-release-guarded-autonomous/evidence/gitea-facts.json`, marking anything not found `unverified` (depends on T002)
- [ ] T004 [P] Verify runner facts V-10 with `claude --help` and `codex --help` (headless permission mode, allowed tools, turn limit, JSON usage and cost fields; existence of `codex exec`) and record them in `skill-lab/specs/203-release-guarded-autonomous/evidence/interface-notes.md` and `skill-lab/docs/research/SOURCES.md` §Codex and Claude Code skills; an absent executable is recorded as `unverified`, never guessed (depends on T002)
- [ ] T005 [P] Create the reviewer-owned checklist `skill-lab/specs/203-release-guarded-autonomous/checklists/requirements.md` from the Spec Kit checklist template, covering FR completeness and testability, gate rationales, contract field lists and invariants, the autonomy invariants (no force-merge, low risk only, human-only promotion, factory human-merged), X-1..X-15, the live-gate floor model of FR-055, and the recorded-evidence review of FR-057 (depends on T002)
- [ ] T006 [P] Write ADR-0301 "Guarded auto-merge: low risk only, merge-when-checks-succeed bound to the head, never force-merge" in `skill-lab/docs/adr/0301-guarded-auto-merge-low-risk-only.md` (D-2..D-7; amends ADR-0009 §2 to add the restrictive cancel row; Compliance: G-OFF-11, G-OFF-12, G-OFF-26) (depends on T002)
- [ ] T007 [P] Write ADR-0302 "Restrict-only demotion latch and human promotion through the base branch" in `skill-lab/docs/adr/0302-restrict-only-demotion-latch-and-human-promotion.md` (D-14, D-15; amends SPEC-201 FR-001/FR-005 and the `--state-dir` convention for the latch; Compliance: G-OFF-09, G-OFF-10, G-OFF-17) (depends on T002)
- [ ] T008 [P] Write ADR-0303 "Autonomy scorecard, demotion triggers, and promotion criteria" in `skill-lab/docs/adr/0303-autonomy-scorecard-and-thresholds.md` (D-16; thresholds as code constants; Compliance: `test_skillkit_autonomy.py`) (depends on T002)
- [ ] T009 [P] Write ADR-0304 "Webhook gateway on R1's replay defence: verify before parse, body-digest dedupe, acknowledge after persist" in `skill-lab/docs/adr/0304-webhook-gateway-verify-dedupe-ack-after-persist.md` (D-9, D-27; the gateway calls R1's four layers of SPEC-201 FR-025 and ADR-0107 and adds only transport, bounds, durability, and the inbox; Compliance: G-OFF-15) (depends on T002)
- [ ] T010 [P] Write ADR-0305 "Level-triggered processing, a route policy over R1's freshness verdicts, and a fixed routing table to sibling skills" in `skill-lab/docs/adr/0305-event-routing-table-to-sibling-skills.md` (D-10, D-11, D-13; `stale` bodies route nowhere, `stale_commit` skips progress routes; Compliance: G-OFF-14, `test_event_routing_docs.py`) (depends on T002)
- [ ] T011 [P] Write ADR-0306 "Lease expiry recovery protocol" in `skill-lab/docs/adr/0306-lease-expiry-recovery-protocol.md` (D-17; rules R-0..R-9; TTL 1800 s, grace 600 s; Compliance: G-OFF-16) (depends on T002)
- [ ] T012 [P] Write ADR-0307 "Event-driven dispatch, role runners, one token per process, and authority narrowing" in `skill-lab/docs/adr/0307-event-driven-dispatch-runners-and-authority-narrowing.md` (D-12, D-18, D-19; defines the `system` role; Compliance: G-OFF-27) (depends on T002)
- [ ] T013 [P] Write ADR-0308 "Rebase on base with force-with-lease on the leased branch" in `skill-lab/docs/adr/0308-rebase-on-base-with-force-with-lease.md` (D-20, D-21; Compliance: G-OFF-28) (depends on T002)
- [ ] T014 [P] Write ADR-0309 "Agentic-framework verification suites as release gates" in `skill-lab/docs/adr/0309-agentic-framework-verification-suites-as-gates.md` (D-23, D-24; the live gates are SPEC-105's floor per skill and catalog-wide in the `merge` stage, on 3 consecutive counting runs; Compliance: G-OFF-18, G-OFF-19, G-LIVE-07, G-LIVE-08) (depends on T002)
- [ ] T015 Amend `skill-lab/docs/CONVENTIONS.md` §4 (11 contract rows, 9 additive changes), §7 (the `system` role and its identity), and §8 (`SUPPORTED_MAX_LEVEL` guarded-autonomous, promotion verification, demotion latch location), citing ADR-0301..0309; write `skill-lab/tests/test_adrs_r3.py` (MADR sections present; CONVENTIONS cites each) and verify with `skill-lab validate` (depends on T006, T007, T008, T009, T010, T011, T012, T013, T014)
- [ ] T016 Run `python3 skills/lead-architect/scripts/spec_readiness.py --feature skill-lab/specs/203-release-guarded-autonomous` into `skill-lab/specs/203-release-guarded-autonomous/evidence/spec-readiness.json` and `python3 skills/lead-architect/scripts/plan_dag.py --tasks skill-lab/specs/203-release-guarded-autonomous/tasks.md` into `skill-lab/specs/203-release-guarded-autonomous/evidence/task-graph.json`; `ready` must be `true` and `cycles` empty (depends on T005, T015, T151)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Contracts, fixtures, the policy clamp with promotion and latch, authority, the autonomy and merge-policy modules, the client rows, the double's merge semantics and webhooks, leases and recovery, the gateway and event loop, git helpers, and the lab commands every story uses

**⚠️ CRITICAL**: No user story work can begin until this phase is complete

### Contracts (tests first)

- [ ] T017 Write failing contract tests `skill-lab/tests/test_contracts_r3.py` with one valid and ≥ 2 invalid documents per new or changed contract under `skill-lab/tests/fixtures/contracts/r3/`, covering every invariant in spec.md §Contracts (for example a `merge-execution` body with `force_merge`, a `lease-recovery` permitting takeover on `escalate_human`, an eligible `autonomy-scorecard` with a failing criterion), plus the subset-keyword check (depends on T016)
- [ ] T018 [P] Create `skill-lab/contracts/schemas/autonomy-scorecard.v1.schema.json`, `autonomy-incident.v1.schema.json`, and `autonomy-demotion.v1.schema.json` — FR-028..FR-031 (depends on T017)
- [ ] T019 [P] Create `skill-lab/contracts/schemas/event-record.v1.schema.json`, `gateway-run.v1.schema.json`, and `session-dispatch.v1.schema.json` — FR-017..FR-024, FR-042 (depends on T017)
- [ ] T020 [P] Create `skill-lab/contracts/schemas/lease-recovery.v1.schema.json`, `rebase-report.v1.schema.json`, `approval-invalidation.v1.schema.json`, `merge-execution.v1.schema.json` (merge style key exactly as T003 recorded), and `afv-report.v1.schema.json` — FR-014, FR-037, FR-045, FR-046, FR-048 (depends on T017, T003)
- [ ] T021 [P] Apply the additive changes to `skill-lab/contracts/schemas/autonomy-policy.v1.schema.json`, `policy-state.v1.schema.json`, `merge-decision.v1.schema.json`, `containment-report.v1.schema.json`, `resume-plan.v1.schema.json`, `gitea-project.v1.schema.json`, `delivery-record.v1.schema.json`, `smoke-report.v1.schema.json`, and `dispatch-plan.v1.schema.json` (spec.md §Changed contracts) — FR-002, FR-004, FR-008, FR-009, FR-011, FR-040, FR-041, FR-051 (depends on T017)
- [ ] T022 Write `skill-lab/contracts/examples/<name>.v1.example.json` for the 11 new contracts, add their rows to `skill-lab/contracts/README.md`, and make `skill-lab/tests/test_contracts_r3.py` pass (depends on T018, T019, T020, T021)
- [ ] T023 [P] Write `skill-lab/specs/203-release-guarded-autonomous/gates.json` (`release-gates.v1`) with G-OFF-01..28 and G-LIVE-01..08 at stage `merge`, G-POST-01..02 at stage `post-review`, and no gate at stage `complete`, exactly as spec.md §Release gates, including each rationale; no gate uses a count metric and no threshold is below SPEC-105's floor; validate it in `skill-lab/tests/test_contracts_r3.py` — FR-054, FR-055 (depends on T022)

### Fixtures

- [ ] T024 [P] Create the R3 feature fixture `skill-lab/fixtures/r3/specs/043-onboarding-docs/` (`spec.md`, `plan.md`, `tasks.md`, `checklists/requirements.md`) with two docs tasks (low), one `src/api/` task (medium), and one `src/auth/` task (high), a dependency on issue 299, and a write-domain overlap; readiness must pass with `skills/lead-architect/scripts/spec_readiness.py` (depends on T016)
- [ ] T025 [P] Create the double seed `skill-lab/fixtures/gitea-double/seed-r3-autonomy.json` (`gitea-fixture.v1`): repository `acme/factory`, identities `agent-lead`, `agent-pse`, `agent-review`, `agent-system` (not admin), branch protection meeting BP-01..BP-12 with required context `ci/test`, tracking issue 300, issues 299 and 301–304 for feature 043, labels `state/*`, `risk/*`, `incident/*`, `autonomy/demoted` (depends on T024)
- [ ] T026 [P] Create the policy fixtures `skill-lab/fixtures/r3/policy/promotion/` (12 failure modes × 2 plus 2 valid promotions) and `skill-lab/fixtures/r3/policy/latch/` (9 failure modes × 2 plus positive controls) as committed-repository descriptions per plan.md §Policy fixtures (depends on T021)
- [ ] T027 [P] Write the deterministic scenario generator `skill-lab/tests/fixtures/r3/make_events.py` and generate `skill-lab/fixtures/r3/events/S1..S6/{world.json,deliveries.json,expected.json}` per plan.md §Ordering scenarios, signing deliveries with the fixed test secret (depends on T025)
- [ ] T028 [P] Write the soak DAG generator `skill-lab/tests/fixtures/r3/soak_dag.py` (40 issues: 24 low, 10 medium, 6 high; 15 dependency edges; 5 write-domain overlaps; fixed fault schedule; one revert at issue 30) per plan.md §Long-horizon soak (depends on T025)

### Policy, authority (tests first)

- [ ] T029 Write failing tests `skill-lab/tests/test_skillkit_policy_r3.py` (TestCatalogR3: 36 actions, the 2 new rows, 0 changed rows against SPEC-201's table; TestClampGuarded; TestPromotionVerification over `skill-lab/fixtures/r3/policy/promotion/`; TestDemotionLatch over `skill-lab/fixtures/r3/policy/latch/` including a run from a linked worktree; TestPolicyState for `demotion`, `promotion`, `limits`; TestNoEscapeHatchesR3: `--state-dir`, environment, and flags change nothing; static check that `policy.py` reads no `os.environ`) — FR-001..FR-004 (depends on T026)
- [ ] T030 Extend `skill-lab/shared/_skillkit/policy.py` (plan.md §Policy load at R3: `SUPPORTED_MAX_LEVEL`, `CATALOG_VERSION = "1.1.0"`, the 2 actions, `promotion_verified`, latch through `gitrepo.common_dir`, base-only `limits` and `auto_merge`, `state_document` fields) until `skill-lab/tests/test_skillkit_policy_r3.py` passes; update only the release-specific assertions of SPEC-201's `skill-lab/tests/test_policy.py` (catalog table of 34 → SPEC-203's 36 with R1's rows unchanged) and SPEC-202's `skill-lab/tests/test_skillkit_policy_r2.py` (`SUPPORTED_MAX_LEVEL`) so that every behavioral assertion still runs and passes — FR-001..FR-004 (depends on T029)
- [ ] T031 [P] Write failing tests `skill-lab/tests/test_skillkit_authority.py` (the 24-row narrowing matrix of plan.md §Authority narrowing; level, role lattice, actions, and write-domain containment; `AUTHORITY_ESCALATION` exit 4) — FR-005 (depends on T030)
- [ ] T032 Create `skill-lab/shared/_skillkit/authority.py` (`ROLE_ACTIONS`, `Authority`, `narrow`) until `skill-lab/tests/test_skillkit_authority.py` passes — FR-005 (depends on T031)

### Autonomy and merge policy (tests first)

- [ ] T033 [P] Write failing tests `skill-lab/tests/test_skillkit_autonomy.py` (every metric of plan.md §Scorecard metrics on fixture ledgers, including the `model.*` metrics over committed SPEC-105 run, streak, and health-report fixtures under `skill-lab/tests/fixtures/r3/spec105/`; `applicable`/`status` rules; D-T1..D-T5; P-1..P-8 including `not_run` without data, and P-8 failing for a streak of 2, an unstable case, a non-counting run, a degraded health report, another model or suite digest, or a failing merge-stage report; a spy proving 0 model or Jev calls; revert-message and `Caused-by:` parsing with configured and unconfigured authors; latch write and read helpers; `THRESHOLDS_VERSION`; no environment reads) — FR-028, FR-029, FR-032, FR-056 (depends on T018)
- [ ] T034 Create `skill-lab/shared/_skillkit/autonomy.py` (reading SPEC-105's `benchmark-streak.v1`, `benchmark-run.v1`, and `run-health.v1` for the model metrics and P-8, never calling a model) until `skill-lab/tests/test_skillkit_autonomy.py` passes — FR-028, FR-029, FR-032, FR-056 (depends on T033)
- [ ] T035 [P] Write failing tests `skill-lab/tests/test_skillkit_merge_policy.py` (each gate and cap of plan.md §Merge decision; the risk classifier table, renames, the 400-line cap, contract and label maxima, injected PR text; factory detection; merge body builder with exactly four keys) and `skill-lab/tests/test_skillkit_merge_policy_matrix.py` (independent oracle over 32,768 gate × risk rows, 13 single-`not_run` rows, 192 cap rows) — FR-011..FR-013 (depends on T021)
- [ ] T036 Create `skill-lab/shared/_skillkit/merge_policy.py` (`decide`, `GATES`, `CAPS`, risk tables, `merge_body`) until both test files pass; medium risk never yields `AUTO_MERGE` (X-9) — FR-011..FR-013 (depends on T035)

### Gitea client and double (tests first)

- [ ] T037 [P] Write failing tests `skill-lab/tests/test_skillkit_gitea_r3.py` (every row of plan.md §Endpoint rows; no immediate-merge row; bodies with `force_merge`, a missing key, `merge_when_checks_succeed: false`, or a short `head_commit_id` → `UNSUPPORTED_OP` with a socket-factory spy showing 0 connections; `MERGE_IDENTITY_IS_ADMIN`, `MERGE_IDENTITY_UNVERIFIED`, `MERGE_ACTOR_IS_AUTHOR`; `LIVE_MERGE_SMOKE_REQUIRED` for a non-loopback host without a `merge` stage) — FR-007..FR-009 (depends on T003, T030)
- [ ] T038 Extend `skill-lab/shared/_skillkit/gitea.py` with the R3 rows, the merge body validator, the system identity and permission checks, and the live-merge guard until `skill-lab/tests/test_skillkit_gitea_r3.py` passes; change SPEC-202's "absent merge row" assertion in `skill-lab/tests/test_skillkit_gitea_r2.py` to R3's rule (no immediate-merge row; the schedule row refused below `guarded-autonomous`), keeping every other SPEC-202 client test unchanged and passing — FR-007..FR-009 (depends on T037)
- [ ] T039 [P] Write failing tests `skill-lab/tests/test_skillkit_gitea_memory_r3.py` (immediate merge versus schedule; `409` on head mismatch; a schedule never executes for another head; cancel; each protection rule at merge time; dismissal; close; webhook outbox entries signed with the test secret) — FR-010 (depends on T025)
- [ ] T040 Extend `skill-lab/shared/_skillkit/gitea_memory.py` with plan.md §Test double R3 semantics until `skill-lab/tests/test_skillkit_gitea_memory_r3.py` passes — FR-010 (depends on T039)
- [ ] T041 Write failing tests `skill-lab/tests/test_gitea_double_webhooks.py` (HTTP delivery of the outbox to `--webhook-url`; deterministic delivery IDs; faults `delay`, `reorder`, `duplicate`, `drop`, `tamper`) — FR-010 (depends on T040)
- [ ] T042 Extend `skill-lab/lab/gitea_double.py` with webhook delivery and fault flags until `skill-lab/tests/test_gitea_double_webhooks.py` passes — FR-010 (depends on T041)

### Leases and recovery (tests first)

- [ ] T043 [P] Write failing tests `skill-lab/tests/test_skillkit_leases_r3.py` (TTL, heartbeat, and grace constants; expired listing; takeover CAS; orchestration lease acquire, renew, and loss) and `skill-lab/tests/test_skillkit_recovery.py` (the ≥ 16 rule fixtures of plan.md §Recovery rules built in temporary git repositories with push receipts and checkpoints) — FR-036..FR-039 (depends on T019, T020)
- [ ] T044 Extend `skill-lab/shared/_skillkit/leases.py` and create `skill-lab/shared/_skillkit/recovery.py` until both test files pass (X-6) — FR-036..FR-039 (depends on T043)

### Webhook gateway and event loop (tests first)

- [ ] T045 [P] Write failing tests `skill-lab/tests/test_skillkit_webhook.py` (every rejection class of FR-017 with ≥ 2 fixtures each; a parser spy never called on a bad signature, and no value parsed from a failing body in any log, record, or envelope; the previous secret accepted at 6 days with `WEBHOOK_SECRET_PREVIOUS_USED` and refused at 7 days or without `GITEA_WEBHOOK_SECRET_ROTATED_AT`; `WEBHOOK_SECRET_TOO_SHORT` for a secret under 32 bytes; dedupe by body SHA-256 under 2 concurrent requests, with the same body under a new delivery ID a duplicate and a new body under a reused delivery ID not; R1's per-object rate limit → `429` with nothing persisted; a stale body persisted with `stale: true` and R1's freshness record unchanged; ack only after the record is written; crash points C1..C6; inbox bound → `503`; TLS requirement off loopback; missing secret; the gateway calls R1's layer code and re-implements none of it) — FR-017..FR-019, FR-023 (depends on T019)
- [ ] T046 Create `skill-lab/shared/_skillkit/webhook.py` (plan.md §Gateway pipeline) until `skill-lab/tests/test_skillkit_webhook.py` passes — FR-017..FR-019, FR-023 (depends on T045)
- [ ] T047 [P] Write failing tests `skill-lab/tests/test_skillkit_eventloop.py` (`ROUTES` covers R1's event vocabulary from T002 or records types as routed nowhere; ordering verdicts; `unverified`, `duplicate`, and `stale` records run no route (not even a cancel route) and never touch R1's freshness record; progress routes skipped for `stale_commit`; no second high-water record; argv built only from typed fields; handler environment minus FR-006's names; exit-code mapping; 3 attempts then `dead_letter`; per-record policy reload; reconcile tick generation; `ROUTE_TARGET_MISSING` and `ROUTE_TARGET_DRIFT`; in-process test mode) — FR-006, FR-020..FR-022, FR-024 (depends on T019, T032)
- [ ] T048 Create `skill-lab/shared/_skillkit/eventloop.py` (plan.md §Routing table and §Ordering guard) until `skill-lab/tests/test_skillkit_eventloop.py` passes (X-10) — FR-006, FR-020..FR-022, FR-024 (depends on T047)

### Git, delivery, redaction (tests first)

- [ ] T049 [P] Write failing tests `skill-lab/tests/test_skillkit_gitrepo_r3.py` (`fetch_base` fixed refspec; `rebase` and `rebase_abort`; `push_force_with_lease` exact lease string and refspec; `common_dir` from a linked worktree; `is_ancestor`; every other subcommand still `GIT_COMMAND_FORBIDDEN`), `skill-lab/tests/test_skillkit_delivery_r3.py` (rebase step and force-with-lease push preconditions), and `skill-lab/tests/test_skillkit_redact_r3.py` (`GITEA_WEBHOOK_SECRET` and `GITEA_WEBHOOK_SECRET_PREVIOUS` masked and stripped from child environments) — FR-006, FR-046, FR-047 (depends on T016)
- [ ] T050 Extend `skill-lab/shared/_skillkit/gitrepo.py`, `skill-lab/shared/_skillkit/delivery.py`, and (if X-3 is still open) `skill-lab/shared/_skillkit/redact.py` until the three test files pass (X-3, X-5) — FR-006, FR-046, FR-047 (depends on T049)
- [ ] T051 Update `skill-lab/shared/_skillkit/__init__.py` with the 6 new modules, run `skill-lab sync` to vendor modules and schemas into all 14 skills (including `run-monitor`), pass `skill-lab sync --check`, and record the constitution re-check (no import from `skill-lab/`, vendored size within limits, every new script's `--help` exits 0) in `skill-lab/specs/203-release-guarded-autonomous/evidence/constitution-recheck.md` (depends on T022, T030, T032, T034, T036, T038, T040, T044, T046, T048, T050)

### Lab commands (tests first within each task)

- [ ] T052 [P] Write failing tests `skill-lab/tests/test_containment_r3.py`, then extend `skill-lab/lab/containment.py` with `--level guarded-autonomous` and `--demoted` (the harness seeds a demotion record in the sandbox's main worktree) until they pass — G-OFF-09 (depends on T051)
- [ ] T053 [P] Write failing tests `skill-lab/tests/test_release_r3.py`, then extend `skill-lab/lab/release.py` with the SPEC-203 gate set: G-LIVE-01..05 read from SPEC-105's `score --strict` per skill and `score --catalog` (floor per skill and catalog-wide; guardrail 100 %), G-LIVE-06 from `benchmark-run.v1` (`counts_toward_streak`, `suite_digest`, 14 `health_reports`, 0 errored, skipped, or missing cases), `afv.agentic.pass_rate` and its guardrail rate (G-LIVE-07), and G-LIVE-08 from the committed `benchmark-streak.v1` (length ≥ 3, 0 unstable cases, one model and the tree's suite digest), every live gate at stage `merge` and none at `complete`; no count metric (X-2, X-12) — FR-054, FR-055 (depends on T023)
- [ ] T154 [P] Write failing tests `skill-lab/tests/release/test_r3_live_gates.py` over committed fixtures in `skill-lab/tests/fixtures/r3/spec105/` (a passing streak of 3 counting runs; each floor gate failing per skill and catalog-wide; a guardrail miss; AFV agentic 12/14; a streak of 2; an unstable case; replay, partial, outage, and degraded runs; a stale suite digest → `LIVE_RUN_STALE`; no run → `NO_LIVE_RUN`; a criteria file below the floor → `CRITERIA_BELOW_FLOOR`), then add `--spec SPEC-203` to `skill-lab release record-run` in `skill-lab/lab/record_run.py`, writing `skill-lab/specs/203-release-guarded-autonomous/evidence/live-runs.json` with each run's id, path, summary sha256, model, and `suite_digest` plus the sha256 of the `benchmark-streak.v1` record, until they pass — FR-055 (depends on T053)
- [ ] T054 [P] Write failing tests `skill-lab/tests/test_validate_r3.py`, then extend `skill-lab/lab/validate_policy.py` with rules `eval-inventory-r3` (plan.md §Action use), `afv-inventory` (plan.md §AFV suites), and the autonomy write ban (FR-035) until they pass — FR-035, FR-050 (depends on T051)
- [ ] T055 [P] Write failing tests `skill-lab/tests/test_afv.py`, then create `skill-lab/lab/afv.py` (`skill-lab afv run --tier deterministic|agentic [--from-run <run>]`, aggregation by `afv:<suite>` tag, minimums; the agentic tier only aggregates a recorded live run and is `not_run` without one) until they pass — FR-048 (depends on T020)
- [ ] T056 [P] Write failing tests `skill-lab/tests/test_autonomy_cmd.py`, then create `skill-lab/lab/autonomy_cmd.py` (`skill-lab autonomy scorecard|promote-check|status --project DIR`, read-only, `PROMOTION_NOT_ELIGIBLE` exit 1) and register `afv` and `autonomy` in `skill-lab/lab/cli.py` until they pass — FR-004, FR-033 (depends on T051, T055)
- [ ] T057 [P] Write failing tests `skill-lab/tests/test_signoff_r3.py`, then extend `skill-lab/lab/signoff.py` with `--subject autonomy-level-change` (interactive only; binds the scorecard digest; refuses a non-eligible scorecard; writes `.skill-autonomy/signoffs/<id>.json` in `--project`) until they pass — FR-033 (depends on T034)
- [ ] T058 [P] Write failing tests `skill-lab/tests/test_smoke_merge.py` (against the HTTP double posing as a non-loopback host), then extend `skill-lab/lab/smoke_gitea.py` with `--stage merge` steps M-1..M-6 (plan.md §Merge smoke stage; sandbox pattern only) until they pass — FR-009 (depends on T042, T038)
- [ ] T059 Create `skill-lab/tests/integration/r3_harness.py` on top of SPEC-202's `r2_harness.py` (HTTP double with webhook delivery, bare remote, clone with committed promotion fixture and four identities, `serve` on 127.0.0.1 port 0 with a ready file, per-role tokens, stub runner, in-process handler mode for the ordering suite) and `skill-lab/tests/integration/crashing_serve.py` (test-only crash hooks) (depends on T042, T051)

**Checkpoint**: Foundation ready; every user story can now start.

---

## Phase 3: User Story 1 - A low-risk PR merges itself only when every gate passes; everything else stays human (Priority: P1) 🎯 MVP

**Goal**: `merge-policy-gate` decides from live state with 13 gates and 6 caps, and schedules low-risk merges through merge-when-checks-succeed bound to the head

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r3_us1_auto_merge.py`

### Tests for User Story 1 ⚠️

- [ ] T060 [US1] Update SPEC-009 in `skill-lab/specs/009-merge-policy-gate/spec.md` (R3 FRs: FR-011..FR-016, FR-028..FR-035, FR-052) and its planned `skill-lab/specs/009-merge-policy-gate/traceability.json` (depends on T051)
- [ ] T061 [P] [US1] Write failing tests `skills/merge-policy-gate/tests/test_merge_decision_r3.py` (spec.md US1 scenarios 1, 4, 5, 8, 12; `--live` against the in-process engine; `--record --apply` writes `.skill-state/merge/decisions/<pr>-<head>.json`; `--diff-fixture`; R2's below-guarded representation kept, X-1) (depends on T060)
- [ ] T062 [P] [US1] Write failing tests `skills/merge-policy-gate/tests/test_merge_plan_apply.py` (US1 scenarios 2, 3, 6, 7, 9, 10, 11; `MERGE_CAPPED`, `MERGE_GATES_FAILED`, `HEAD_MOVED`; `--evaluate` → `not_eligible` exit 0; every cancel trigger; `--sweep-expired` with TTL 30; `--reevaluate-open`; `--cancel-all`; receipts and `merge-execution.v1`) (depends on T060)
- [ ] T063 [P] [US1] Write failing tests `skills/merge-policy-gate/tests/test_branch_audit_r3.py` (BP-09 required at guarded; `unknown` → `fail`; non-compliance → gate `branch-protection-compliant` `fail` → `BLOCKED`) (depends on T060)

### Implementation for User Story 1

- [ ] T064 [US1] Extend `skills/merge-policy-gate/scripts/merge_decision.py` (live snapshot builder, `_skillkit.merge_policy.decide`, Gitea-side demotion cap, `--record`, `--diff-fixture`) until `skills/merge-policy-gate/tests/test_merge_decision_r3.py` passes (X-1, X-9) — FR-011..FR-013, FR-034, FR-052 (depends on T061, T036, T038)
- [ ] T065 [US1] Extend `skills/merge-policy-gate/scripts/merge_plan.py` (`--apply`, `--evaluate`, `--evaluate-open`, `--cancel`, `--cancel-if-head-differs`, `--cancel-all`, `--sweep-expired`, `--reevaluate-open`; plan.md §Merge execution) until `skills/merge-policy-gate/tests/test_merge_plan_apply.py` passes — FR-014, FR-015 (depends on T062, T064, T040)
- [ ] T066 [US1] Extend `skills/merge-policy-gate/scripts/branch_audit.py` and `skills/merge-policy-gate/assets/branch-policy-map.json` (BP-09 field from T003) until `skills/merge-policy-gate/tests/test_branch_audit_r3.py` passes — FR-016 (depends on T063, T003)
- [ ] T067 [US1] Write `skills/merge-policy-gate/references/auto-merge-gates.md` (gates, caps, lifecycle), update `skills/merge-policy-gate/references/risk-classes.md` (R3 tables), and update `skills/merge-policy-gate/SKILL.md` (decide, evaluate, schedule, cancel steps, each one command; behaviour per level; "never merge medium or above; never force-merge; never the factory"); verify with `skill-lab validate --skill merge-policy-gate` — FR-053 (depends on T064, T065, T066)
- [ ] T068 [US1] Add eval cases in `skills/merge-policy-gate/evals/cases/` for pair 1 (`merge-when-checks-succeed-applied.json`, `merge-when-checks-succeed-rerun.json`, `merge-when-checks-succeed-refused-agent-implementation.json` tagged `policy` and `action:gitea.pr.merge-when-checks-succeed`, `merge-when-checks-succeed-refused-demoted.json` tagged `demoted`) and pair 8 (`merge-schedule-cancel-applied.json`, `merge-schedule-cancel-rerun.json`, `merge-schedule-cancel-refused-shadow.json` tagged `policy` and `action:gitea.pr.merge-schedule.cancel`); agentic `agentic-r3-explain-human-merge.json`; trigger cases "auto-merge PR 311 when CI passes" (positive) and "move PR 311 to review" (negative, `kanban-state-machine`); leave `skill-lab/benchmarks/criteria/merge-policy-gate.json` unchanged (agents never edit criteria files; it stays at or above SPEC-105's floor) and keep the skill at SPEC-105's minimums (≥ 5 agentic with ≥ 1 `guardrail`, ≥ 10 trigger with ≥ 2 `expect_skill: null`); verify with `skill-lab bench --skill merge-policy-gate --tier deterministic` — FR-050 (depends on T067)
- [ ] T069 [US1] Write and pass `skill-lab/tests/integration/test_r3_us1_auto_merge.py` (golden: PR 311 auto-merges through one schedule bound to H; 303 and 304 end `READY_TO_MERGE` with a cap comment; schedule cancelled on a new head; TTL sweep; factory cap; double logs show 0 other merge calls) (depends on T068, T059)

**Checkpoint**: Guarded auto-merge works on the double; everything else stays human.

---

## Phase 4: User Story 2 - Verified, deduplicated webhook events drive the board (Priority: P1)

**Goal**: `gitea-event-normalizer` serves the webhook gateway and processes events through the routing table

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r3_us2_gateway.py`

### Tests for User Story 2 ⚠️

- [ ] T070 [US2] Update SPEC-008 in `skill-lab/specs/008-gitea-event-normalizer/spec.md` (FR-017..FR-024) and its planned `skill-lab/specs/008-gitea-event-normalizer/traceability.json` (depends on T051)
- [ ] T071 [P] [US2] Write failing tests `skills/gitea-event-normalizer/tests/test_serve.py` (US2 scenarios 1–12 over loopback with a ready file, including the body-digest duplicate under a new delivery ID, the 7-day previous-secret window, `WEBHOOK_SECRET_TOO_SHORT`, and the per-object `429`; SIGTERM; one `gateway-run.v1` envelope; orchestration lease; demotion stop) and `skills/gitea-event-normalizer/tests/test_ingest_process.py` (`ingest` at every level, `process --apply` refused below guarded, reconcile ticks, dead-letter) (depends on T070)

### Implementation for User Story 2

- [ ] T072 [US2] Extend `skills/gitea-event-normalizer/scripts/normalize.py` with `serve`, `ingest`, `process`, `reconcile`, and `status` over `_skillkit.webhook` and `_skillkit.eventloop` until both test files pass — FR-017..FR-024 (depends on T071, T046, T048)
- [ ] T073 [US2] Write `skills/gitea-event-normalizer/references/gateway.md` (operator setup, response codes, crash safety) and generate `skills/gitea-event-normalizer/references/event-routing.md` from `ROUTES`; write `skill-lab/tests/test_event_routing_docs.py` (the generated file matches `ROUTES`) (depends on T072)
- [ ] T074 [US2] Update `skills/gitea-event-normalizer/SKILL.md` (agents use `status` and `ingest`; the operator starts `serve` outside the agent; one command per step); verify with `skill-lab validate --skill gitea-event-normalizer` — FR-053 (depends on T073)
- [ ] T075 [US2] Add eval cases in `skills/gitea-event-normalizer/evals/cases/` for pair 2 (`gateway-process-applied.json`, `gateway-process-rerun.json`, `gateway-process-refused-agent-implementation.json` tagged `policy` and `action:events.gateway.serve`, `gateway-process-refused-demoted.json` tagged `demoted`); agentic `agentic-r3-operator-start.json` (`guardrail`); trigger cases "start the webhook gateway" (positive) and "which issues drifted" (negative, `speckit-gitea-sync`); leave `skill-lab/benchmarks/criteria/gitea-event-normalizer.json` unchanged (agents never edit criteria files) and keep the skill at SPEC-105's minimums; verify with `skill-lab bench --skill gitea-event-normalizer --tier deterministic` — FR-050 (depends on T074)
- [ ] T076 [US2] Write and pass `skill-lab/tests/integration/test_r3_us2_gateway.py` (the double delivers signed webhooks to `serve`; tampered, oversized, and duplicate deliveries (the same body under a new delivery ID) change nothing; a tampered body leaves no parsed value in any log or record; crashes C1..C6 through `crashing_serve.py`; inbox full; second gateway refused; hostile payload text has no effect) (depends on T075, T059)

**Checkpoint**: Events drive the control plane; acknowledged events are never lost or applied twice.

---

## Phase 5: User Story 3 - Out-of-order and duplicate events never cause an unsafe action (Priority: P1)

**Goal**: The board moves only on observed facts recomputed from live state; stale facts never produce progress; drift is caught on events

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r3_us3_ordering.py`

### Tests for User Story 3 ⚠️

- [ ] T077 [US3] Update SPEC-006 in `skill-lab/specs/006-kanban-state-machine/spec.md` (FR-024, FR-025) and SPEC-005 in `skill-lab/specs/005-speckit-gitea-sync/spec.md` (FR-027), with their planned `traceability.json` files (depends on T051)
- [ ] T078 [P] [US3] Write failing tests `skills/kanban-state-machine/tests/test_on_event.py` (each observed-fact transition as `system`, including `BLOCK` from a reopened dependency, an `escalate_human` recovery, a recorded rebase conflict, or exhausted dispatch attempts, `UNBLOCK`, and `REQUEUE` after `release_no_work`; role-owned transitions refused with `ROLE_NOT_AUTHORIZED`; recompute and `PLAN_STALE`; cap comment on `READY_TO_MERGE`) (depends on T077)

### Implementation for User Story 3

- [ ] T079 [US3] Extend `skills/kanban-state-machine/scripts/transition.py` and `skills/kanban-state-machine/scripts/labels_plan.py` with `--on-event`, `--reconcile`, and the observed-fact rule until `skills/kanban-state-machine/tests/test_on_event.py` passes (X-8) — FR-025 (depends on T078)
- [ ] T080 [US3] Update `skills/kanban-state-machine/SKILL.md` and add eval cases in `skills/kanban-state-machine/evals/cases/` (deterministic `on-event-move-to-review.json`, `on-event-role-owned-refused.json`; agentic `agentic-r3-observed-fact-transition.json`; trigger "mark PR 311 ready to merge after CI" (positive) and "auto-merge PR 311" (negative, `merge-policy-gate`)); leave `skill-lab/benchmarks/criteria/kanban-state-machine.json` unchanged (agents never edit criteria files) and keep the skill at SPEC-105's minimums; verify with `skill-lab validate --skill kanban-state-machine` and `skill-lab bench --skill kanban-state-machine --tier deterministic` — FR-050, FR-053 (depends on T079)
- [ ] T081 [P] [US3] Write failing tests `skills/speckit-gitea-sync/tests/test_sync_on_event.py` (events that trigger a drift check; one comment per drift through R2's applier; `.skill-state/sync/drift-<feature>.json` written and cleared) (depends on T077)
- [ ] T082 [US3] Extend `skills/speckit-gitea-sync/scripts/sync_drift.py` with `--on-event` and the drift state file until `skills/speckit-gitea-sync/tests/test_sync_on_event.py` passes — FR-027 (depends on T081)
- [ ] T083 [US3] Update `skills/speckit-gitea-sync/SKILL.md` and add eval cases in `skills/speckit-gitea-sync/evals/cases/` (deterministic `drift-on-issue-edit.json`; agentic `agentic-r3-drift-on-event.json`; trigger "check drift after this issue was edited" (positive) and "create the Gitea issues for these tasks" (negative, `speckit-gitea-taskstoissues`)); leave `skill-lab/benchmarks/criteria/speckit-gitea-sync.json` unchanged (agents never edit criteria files) and keep the skill at SPEC-105's minimums; verify with `skill-lab validate --skill speckit-gitea-sync` — FR-050, FR-053 (depends on T082)
- [ ] T084 [US3] Write and pass `skill-lab/tests/integration/test_r3_us3_ordering.py` (S1..S6: every fully-advanced delivery order plus the n + 1 interleaved schedules, each followed by one reconcile tick; 0 unsafe merges checked against the double's state at each merge request; 0 final-state mismatches; the dropped-delivery repair of US3 scenario 5; a body R1 marks `stale` runs no route and changes no state, US3 scenario 8) — FR-024, FR-026 (depends on T079, T082, T072, T065, T027)

**Checkpoint**: Safety is independent of event order.

---

## Phase 6: User Story 4 - The system demotes itself on an escaped defect or a revert; only a human promotes (Priority: P1)

**Goal**: Scorecard, incident detection, demotion within the triggering event, and human-only promotion

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r3_us4_demotion.py skill-lab/tests/integration/test_r3_us4_promotion.py`

### Tests for User Story 4 ⚠️

- [ ] T085 [P] [US4] Write failing tests `skills/merge-policy-gate/tests/test_autonomy_scorecard.py` (window selection; source coverage; every metric present with applicability; P-1..P-8 on fixture histories including 29 versus 30 candidates; deterministic output with `--now`) (depends on T060, T034)
- [ ] T086 [P] [US4] Write failing tests `skills/merge-policy-gate/tests/test_autonomy_guard.py` (detect from labels, revert commits, audits, containment reports, recoveries; `--apply` order: latch, then cancels, then mirror; mirror failure → exit 3 with the latch kept; re-run writes nothing; `audit-merge` mismatch → `gate_integrity`) (depends on T060, T034)

### Implementation for User Story 4

- [ ] T087 [US4] Create `skills/merge-policy-gate/scripts/autonomy_scorecard.py` until `skills/merge-policy-gate/tests/test_autonomy_scorecard.py` passes — FR-028, FR-032 (depends on T085)
- [ ] T088 [US4] Create `skills/merge-policy-gate/scripts/autonomy_guard.py` (`detect`, `evaluate`, `demote`, `audit-merge`; plan.md §Demotion procedure) until `skills/merge-policy-gate/tests/test_autonomy_guard.py` passes — FR-029..FR-031 (depends on T086, T065)
- [ ] T089 [US4] Write `skills/merge-policy-gate/references/autonomy-promotion.md` (metrics, triggers, criteria, labelling convention for incidents) and the runbook `skill-lab/docs/runbooks/autonomy-promotion.md` (promote-check, sign-off, the human-merged promotion PR, removing `autonomy/demoted` after re-promotion, re-promotion after a demotion) — FR-033 (depends on T088, T057)
- [ ] T090 [US4] Update `skills/merge-policy-gate/SKILL.md` with the scorecard and guard steps, keeping the body ≤ 250 lines and ≤ 12 KB by moving detail to `references/`; verify with `skill-lab validate --skill merge-policy-gate` — FR-053 (depends on T089, T067)
- [ ] T091 [US4] Add eval cases in `skills/merge-policy-gate/evals/cases/` for pairs 9, 10, 11 (`guard-mirror-comment-applied.json`, `guard-mirror-comment-rerun.json`, `guard-mirror-comment-refused-shadow.json`, `guard-mirror-label-applied.json`, `guard-mirror-label-rerun.json`, `guard-mirror-label-refused-shadow.json`, `guard-define-label-applied.json`, `guard-define-label-rerun.json`, `guard-define-label-refused-shadow.json`, the refusals tagged `policy` with their `action:` tags) and pair 13 (`autonomy-demote-applied.json`, `autonomy-demote-rerun.json`); trigger cases "why did autonomy get demoted" (positive) and "save my progress for the next session" (negative, `session-checkpoint`); verify with `skill-lab bench --skill merge-policy-gate --tier deterministic` — FR-050 (depends on T090)
- [ ] T092 [US4] Write and pass `skill-lab/tests/integration/test_r3_us4_demotion.py` (US4 scenarios 1–4 and 9 through the gateway: revert on `main`, escaped-defect label, gate-integrity audit, containment breach, lease violation, 2 fixtures each; schedules cancelled; guarded actions refused; latch deletion still capped by the forge mirror) (depends on T091, T072, T059)
- [ ] T093 [US4] Write and pass `skill-lab/tests/integration/test_r3_us4_promotion.py` (US4 scenarios 5–8: promotion only via a human-merged base commit with a valid sign-off and eligible scorecard; every hostile promotion fixture stays `agent-implementation`; `promote-check` exit codes) (depends on T092, T056, T057)

**Checkpoint**: Autonomy is measured and reversible; promotion is human-only.

---

## Phase 7: User Story 5 - Lease expiry is recovered from evidence, never by blind continuation (Priority: P2)

**Goal**: `work-lease recover|takeover` and `session-checkpoint resume-plan --recovery`

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r3_us5_recovery.py`

### Tests for User Story 5 ⚠️

- [ ] T094 [US5] Update SPEC-007 in `skill-lab/specs/007-work-lease/spec.md` (FR-036..FR-039) and SPEC-010 in `skill-lab/specs/010-session-checkpoint/spec.md` (FR-040), with their planned `traceability.json` files (depends on T051)
- [ ] T095 [P] [US5] Write failing tests `skills/work-lease/tests/test_recover.py` (US5 scenarios 1–5 over the rule fixtures; `--apply` marks, preserves, mirrors) and `skills/work-lease/tests/test_takeover.py` (scenario 6: fresh record, CAS, `RECOVERY_RECORD_REQUIRED`, `TAKEOVER_NOT_PERMITTED`, `RECOVERY_STALE`, `VERSION_CONFLICT`; successor lease fields) (depends on T094)
- [ ] T096 [P] [US5] Write failing tests `skills/session-checkpoint/tests/test_resume_recovery.py` (the 4 new verified checks; latest valid checkpoint among local records and marked comments from configured identities only) (depends on T094)

### Implementation for User Story 5

- [ ] T097 [US5] Extend `skills/session-checkpoint/scripts/checkpoint.py` with `resume-plan --recovery` until `skills/session-checkpoint/tests/test_resume_recovery.py` passes — FR-040 (depends on T096)
- [ ] T098 [US5] Extend `skills/work-lease/scripts/lease.py` with `recover`, `takeover`, `expired`, and `release --if-pr-closed` over `_skillkit.recovery` until both work-lease test files pass — FR-036..FR-039 (depends on T095, T097, T044)
- [ ] T099 [US5] Update `skills/work-lease/SKILL.md` and `skills/session-checkpoint/SKILL.md` (recovery and takeover steps; "never continue an expired lease without a recovery record"); verify with `skill-lab validate --skill work-lease` and `--skill session-checkpoint` — FR-053 (depends on T098)
- [ ] T100 [US5] Add eval cases for pair 5 in `skills/work-lease/evals/cases/` (`lease-takeover-applied.json`, `lease-takeover-rerun.json`, `lease-takeover-refused-agent-implementation.json` tagged `policy` and `action:lease.takeover`, `lease-takeover-refused-demoted.json` tagged `demoted`); agentic `skills/work-lease/evals/cases/agentic-r3-classify-recovery.json` and `skills/session-checkpoint/evals/cases/agentic-r3-recovery-checkpoint-summary.json`; trigger cases "the PSE session died, recover issue 301" (positive, `work-lease`), "resume from my last checkpoint" (positive, `session-checkpoint`), and one negative each; leave `skill-lab/benchmarks/criteria/work-lease.json` and `session-checkpoint.json` unchanged (agents never edit criteria files) and keep both skills at SPEC-105's minimums; verify with `skill-lab bench --skill work-lease --tier deterministic` — FR-050 (depends on T099)
- [ ] T101 [US5] Write and pass `skill-lab/tests/integration/test_r3_us5_recovery.py` (a scripted PSE stub killed after each delivery step in turn; classification, takeover by a successor, the successor's first step; dirty worktree escalated with the patch preserved; unexplained head → `lease_violation`) (depends on T100, T059)

**Checkpoint**: Expired leases are recovered from evidence or escalated.

---

## Phase 8: User Story 6 - Event-driven dispatch unlocks the next work within limits and narrowed authority (Priority: P2)

**Goal**: Close and unlock on merge, dispatch within limits, write session dispatches, start them through role runners

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r3_us6_dispatch_loop.py`

### Tests for User Story 6 ⚠️

- [ ] T102 [US6] Update SPEC-001 in `skill-lab/specs/001-lead-architect/spec.md` (FR-041..FR-044) and its planned `skill-lab/specs/001-lead-architect/traceability.json` (depends on T051)
- [ ] T103 [P] [US6] Write failing tests `skills/lead-architect/tests/test_dispatch_on_event.py` (capacity, daily budget, attempts, drift deferral, claiming sequence reuse), `skills/lead-architect/tests/test_dispatch_session.py` (`write` for each purpose; prompt quoting untrusted text; narrowing refusals; `run` identity check; runners `none`, `stub`, and `claude-cli` → `RUNNER_UNVERIFIED` until T004 verified flags; expiry), and `skills/lead-architect/tests/test_complete_issue_r3.py` (close at guarded; `CLOSE_PENDING` below) (depends on T102)

### Implementation for User Story 6

- [ ] T104 [US6] Extend `skills/lead-architect/scripts/dispatch_recommend.py` (`--on-event`, `--write-dispatch`, limits, drift deferral) and `skills/lead-architect/scripts/complete_issue.py` (`gitea.issue.close` at guarded) until `test_dispatch_on_event.py` and `test_complete_issue_r3.py` pass — FR-041, FR-043 (depends on T103, T032, T082)
- [ ] T105 [US6] Create `skills/lead-architect/scripts/dispatch_session.py` (`write`, `run`) and the templates `skills/lead-architect/assets/templates/pse-dispatch-prompt.md` and `skills/lead-architect/assets/templates/review-dispatch-prompt.md` until `skills/lead-architect/tests/test_dispatch_session.py` passes — FR-042, FR-044 (depends on T104, T004)
- [ ] T106 [US6] Update `skills/lead-architect/SKILL.md` (dispatch on events, session dispatch, close; runner behaviour per runtime); verify with `skill-lab validate --skill lead-architect` — FR-053 (depends on T105)
- [ ] T107 [US6] Add eval cases in `skills/lead-architect/evals/cases/` for pairs 3 and 4 (`dispatch-session-start-applied.json`, `dispatch-session-start-rerun.json`, `dispatch-session-start-refused-agent-implementation.json`, `dispatch-session-start-refused-demoted.json`, `issue-close-applied.json`, `issue-close-rerun.json`, `issue-close-refused-agent-implementation.json`, `issue-close-refused-demoted.json`; refusals tagged `policy` or `demoted` with their `action:` tags) and pair 12 (`review-dispatch-applied.json`, `review-dispatch-rerun.json`, `review-dispatch-refused-shadow.json`); agentic `agentic-r3-dispatch-limits.json`; trigger "dispatch the next unblocked issue" (positive) and "claim issue 302" (negative, `work-lease`); leave `skill-lab/benchmarks/criteria/lead-architect.json` unchanged (agents never edit criteria files) and keep the skill at SPEC-105's minimums; verify with `skill-lab bench --skill lead-architect --tier deterministic` — FR-050 (depends on T106)
- [ ] T108 [US6] Write and pass `skill-lab/tests/integration/test_r3_us6_dispatch_loop.py` (US6 scenarios 1–7 through the gateway: merge closes 301, 302 dispatched to the stub runner, 303 deferred by capacity, budget exhaustion, attempts escalation, narrowing refusals, remediation and re-review dispatches) (depends on T107, T072, T059)

**Checkpoint**: The loop closes, unlocks, and dispatches within bounds.

---

## Phase 9: User Story 7 - Stale heads: approvals are invalidated, the PSE rebases its own branch, conflicts go to a human (Priority: P2)

**Goal**: `review-verifier invalidate.py` and pse-implementer's rebase and force-with-lease steps

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r3_us7_stale_heads.py`

### Tests for User Story 7 ⚠️

- [ ] T109 [US7] Update SPEC-003 in `skill-lab/specs/003-review-verifier/spec.md` (FR-045) and SPEC-002 in `skill-lab/specs/002-pse-implementer/spec.md` (FR-046, FR-047), with their planned `traceability.json` files (depends on T051)
- [ ] T110 [P] [US7] Write failing tests `skills/review-verifier/tests/test_invalidate.py` (US7 scenarios 1–2; local stale marking by any role; `--dismiss` only by the Review identity; only Review-login approvals of non-head commits; `already_dismissed`; `403` → exit 3 `GITEA_AUTH`) (depends on T109)

### Implementation for User Story 7

- [ ] T111 [US7] Create `skills/review-verifier/scripts/invalidate.py` until `skills/review-verifier/tests/test_invalidate.py` passes — FR-045 (depends on T110)
- [ ] T112 [US7] Update `skills/review-verifier/SKILL.md` and add eval cases in `skills/review-verifier/evals/cases/` for pair 7 (`review-dismiss-applied.json`, `review-dismiss-rerun.json`, `review-dismiss-refused-agent-implementation.json` tagged `policy` and `action:gitea.pr.review.dismiss`, `review-dismiss-refused-demoted.json` tagged `demoted`); agentic `agentic-r3-rereview-request.json`; trigger "my approval is stale after the new push" (positive) and "is PR 311 safe to merge" (negative, `merge-policy-gate`); leave `skill-lab/benchmarks/criteria/review-verifier.json` unchanged (agents never edit criteria files) and keep the skill at SPEC-105's minimums; verify with `skill-lab validate --skill review-verifier` and `skill-lab bench --skill review-verifier --tier deterministic` — FR-050, FR-053 (depends on T111)
- [ ] T113 [P] [US7] Write failing tests `skills/pse-implementer/tests/test_rebase.py` (US7 scenarios 3–6 in temporary repositories with a bare remote: rebase success, conflict and abort, `PUSH_LEASE_MISMATCH`, `EVIDENCE_STALE_AFTER_REBASE`, only the leased refspec) (depends on T109)
- [ ] T114 [US7] Extend `skills/pse-implementer/scripts/delivery_plan.py` with `--step rebase` and `--step push --force-with-lease` over `_skillkit.delivery` until `skills/pse-implementer/tests/test_rebase.py` passes — FR-046, FR-047 (depends on T113, T050)
- [ ] T115 [US7] Update `skills/pse-implementer/SKILL.md` and add eval cases in `skills/pse-implementer/evals/cases/` for pair 6 (`force-own-branch-applied.json`, `force-own-branch-rerun.json`, `force-own-branch-refused-agent-implementation.json` tagged `policy` and `action:git.push.force-own-branch`, `force-own-branch-refused-demoted.json` tagged `demoted`); agentic `agentic-r3-rebase-clean.json`; trigger "rebase my PR on the new main" (positive) and "deliver feature 043 end to end" (negative, `speckit-development`); leave `skill-lab/benchmarks/criteria/pse-implementer.json` unchanged (agents never edit criteria files) and keep the skill at SPEC-105's minimums; verify with `skill-lab validate --skill pse-implementer` and `skill-lab bench --skill pse-implementer --tier deterministic` — FR-050, FR-053 (depends on T114)
- [ ] T116 [US7] Write and pass `skill-lab/tests/integration/test_r3_us7_stale_heads.py` (base moves → rebase dispatch → rebase → checks → force-with-lease push → re-review → auto-merge; conflict → abort, `state/blocked`, human; a stale approval never merges; a schedule is cancelled on the rebased head) (depends on T111, T115, T072, T059)

**Checkpoint**: Freshness is enforced without automatic conflict resolution.

---

## Phase 10: User Story 8 - Agentic-framework verification suites prove the safety properties (Priority: P2)

**Goal**: Ten AFV suites at their minimum counts, concurrency and failure-recovery integration tests, and the soak test

**Independent Test**: `python3 skill-lab/bin/skill-lab afv run --tier deterministic` (10 of 10 `pass`) and `python3 -m unittest skill-lab/tests/integration/test_r3_soak.py`

- [ ] T117 [P] [US8] Add the `afv:intent-preservation` cases: deterministic `skills/merge-policy-gate/evals/cases/afv-intent-chain-spec-mismatch.json`, `skills/merge-policy-gate/evals/cases/afv-intent-chain-ac-not-passed.json`, `skills/speckit-development/evals/cases/afv-handoff-keeps-issue-contract.json`, `skills/lead-architect/evals/cases/afv-dispatch-prompt-carries-contract.json`; agentic `skills/speckit-development/evals/cases/agentic-r3-handoff-not-merge.json` (`guardrail`) and `skills/lead-architect/evals/cases/agentic-afv-intent-after-remediation.json` (depends on T069, T107, T130)
- [ ] T118 [P] [US8] Add the `afv:tool-correctness` cases: deterministic `skills/merge-policy-gate/evals/cases/afv-scheduled-is-not-merged.json`, `skills/merge-policy-gate/evals/cases/afv-cancel-verified-by-reread.json`, `skills/review-verifier/evals/cases/afv-dismissal-verified.json`, `skills/lead-architect/evals/cases/afv-close-verified.json`; agentic `skills/merge-policy-gate/evals/cases/agentic-r3-scheduled-not-merged.json` (`guardrail`) and `skills/work-lease/evals/cases/agentic-afv-verify-takeover-state.json` (depends on T069, T107, T112, T100)
- [ ] T119 [P] [US8] Add the `afv:permission-containment` cases: deterministic `skills/gitea-event-normalizer/evals/cases/afv-handler-authority-bounded.json`, `skills/lead-architect/evals/cases/afv-narrowing-domains-outside-lease.json`, `skills/lead-architect/evals/cases/afv-narrowing-pse-spawns-lead.json`, `skills/merge-policy-gate/evals/cases/afv-admin-identity-refused.json`, `skills/merge-policy-gate/evals/cases/afv-force-merge-body-refused.json`, `skills/work-lease/evals/cases/afv-takeover-without-record.json`; agentic `skills/pse-implementer/evals/cases/agentic-afv-refuse-push-main.json` and `skills/review-verifier/evals/cases/agentic-r3-no-foreign-dismissal.json` (both `guardrail`) (depends on T075, T107, T069, T100, T115, T112)
- [ ] T120 [P] [US8] Add the `afv:prompt-injection` cases with hostile fixtures under each skill's `evals/fixtures/r3/injection/`: deterministic `skills/gitea-event-normalizer/evals/cases/afv-payload-instructions-ignored.json`, `skills/merge-policy-gate/evals/cases/afv-pr-body-risk-low-ignored.json`, `skills/kanban-state-machine/evals/cases/afv-forged-marker-ignored.json`, `skills/session-checkpoint/evals/cases/afv-unconfigured-checkpoint-ignored.json`, `skills/speckit-gitea-sync/evals/cases/afv-issue-edit-instructions-ignored.json`; agentic `skills/merge-policy-gate/evals/cases/agentic-r3-injected-risk-low.json`, `skills/lead-architect/evals/cases/agentic-r3-injected-dispatch.json`, `skills/review-verifier/evals/cases/agentic-afv-injected-approve.json` (all `guardrail`) (depends on T075, T069, T080, T100, T083, T107, T112)
- [ ] T121 [P] [US8] Add the `afv:long-horizon-recovery` cases: deterministic `skills/work-lease/evals/cases/afv-resume-from-checkpoint.json`, `skills/work-lease/evals/cases/afv-reverify-after-checkpoint.json`, `skills/session-checkpoint/evals/cases/afv-latest-valid-checkpoint.json`, `skills/gitea-event-normalizer/evals/cases/afv-inbox-replay-after-restart.json`; agentic `skills/work-lease/evals/cases/agentic-r3-no-blind-takeover.json` (`guardrail`) and `skills/session-checkpoint/evals/cases/agentic-r3-resume-from-recovery.json` (depends on T100, T075)
- [ ] T122 [P] [US8] Add the `afv:idempotency` cases: deterministic `skills/gitea-event-normalizer/evals/cases/afv-duplicate-delivery-once.json`, `skills/merge-policy-gate/evals/cases/afv-rerun-schedule-no-write.json`, `skills/merge-policy-gate/evals/cases/afv-rerun-guard-no-write.json`, `skills/work-lease/evals/cases/afv-rerun-takeover-no-write.json`, `skills/lead-architect/evals/cases/afv-rerun-dispatch-no-write.json` (depends on T075, T091, T100, T107)
- [ ] T123 [P] [US8] Add the `afv:ordering` cases: deterministic `skills/gitea-event-normalizer/evals/cases/afv-stale-commit-approval.json`, `skills/gitea-event-normalizer/evals/cases/afv-stale-commit-check.json`, `skills/gitea-event-normalizer/evals/cases/afv-stale-body-no-route.json` (R1's freshness guard marks an older body `stale`; no route runs), `skills/kanban-state-machine/evals/cases/afv-merged-before-review.json`; agentic `skills/kanban-state-machine/evals/cases/agentic-r3-stale-approval.json` (depends on T075, T080)
- [ ] T124 [P] [US8] Add the `afv:concurrency` cases `skills/work-lease/evals/cases/afv-two-takeovers-one-wins.json`, `skills/gitea-event-normalizer/evals/cases/afv-second-gateway-refused.json`, `skills/lead-architect/evals/cases/afv-two-dispatches-one-issue.json`, `skills/merge-policy-gate/evals/cases/afv-schedule-versus-push-race.json`, and write and pass `skill-lab/tests/integration/test_r3_concurrency.py` (two processes per race, file locks and CAS, double schedule-versus-push race) (depends on T100, T076, T107, T069)
- [ ] T125 [P] [US8] Add the `afv:failure-recovery` cases `skills/merge-policy-gate/evals/cases/afv-ci-pending-ttl-cancel.json`, `skills/merge-policy-gate/evals/cases/afv-gitea-503-during-schedule.json`, `skills/gitea-event-normalizer/evals/cases/afv-dead-letter-after-three.json`, `skills/work-lease/evals/cases/afv-sandbox-died.json`, `skills/kanban-state-machine/evals/cases/afv-dependency-reopened.json`, `skills/pse-implementer/evals/cases/afv-rebase-conflict-aborts.json`, agentic `skills/pse-implementer/evals/cases/agentic-r3-conflict-escalation.json` (`guardrail`), and write and pass `skill-lab/tests/integration/test_r3_failure_recovery.py` (a fault after every operation of the golden loop, resume, and a re-run sweep with 0 extra writes) (depends on T069, T076, T100, T080, T115)
- [ ] T126 [P] [US8] Add the `afv:grounding` cases: deterministic `skills/review-verifier/evals/cases/afv-stale-verdict-rejected.json`, `skills/session-checkpoint/evals/cases/afv-stale-checkpoint-rejected.json`, `skills/merge-policy-gate/evals/cases/afv-evidence-other-head.json`; agentic `skills/review-verifier/evals/cases/agentic-r3-current-head-only.json` (depends on T112, T100, T069)
- [ ] T127 [US8] Write and pass `skill-lab/tests/integration/test_r3_soak.py` over the DAG from `skill-lab/tests/fixtures/r3/soak_dag.py` with every invariant of spec.md US8 scenario 4 — FR-049 (depends on T076, T084, T092, T101, T108, T116, T028)
- [ ] T128 [US8] Run `python3 skill-lab/bin/skill-lab afv run --tier deterministic` into `skill-lab/specs/203-release-guarded-autonomous/evidence/afv-report-deterministic.json` and `skill-lab validate --rule afv-inventory`; every suite `pass` with its minimums (G-OFF-18) — FR-048 (depends on T117, T118, T119, T120, T121, T122, T123, T124, T125, T126, T127, T055)

**Checkpoint**: Every property the report lists for agent systems is tested and gated.

---

## Phase 11: User Story 9 - `/speckit-development` hands off to the merge gate; the factory stays human-merged (Priority: P3)

**Goal**: The delivery command records a merge handoff and never merges; the factory cap holds

**Independent Test**: `python3 -m unittest skill-lab/tests/integration/test_r3_us9_handoff_factory.py`

- [ ] T129 [US9] Update SPEC-013 in `skill-lab/specs/013-speckit-development/spec.md` (FR-051) with its planned `traceability.json`, and write failing tests `skills/speckit-development/tests/test_handoff_r3.py` (US9 scenarios 1–3; a static check that no speckit-development script references `merge_plan.py` or the merge endpoint) (depends on T051)
- [ ] T130 [US9] Extend `skills/speckit-development/scripts/delivery_record.py` with the `merge_handoff` record and `next_action` rule until `skills/speckit-development/tests/test_handoff_r3.py` passes — FR-051 (depends on T129, T064)
- [ ] T131 [US9] Update `skills/speckit-development/SKILL.md` (handoff per level) and add eval cases in `skills/speckit-development/evals/cases/` (deterministic `handoff-event-loop-low-risk.json`, `handoff-human-medium.json`; agentic `agentic-r3-handoff-human-for-medium.json`; trigger "finish delivering feature 043 and hand it off" (positive) and "auto-merge PR 311" (negative, `merge-policy-gate`)); leave `skill-lab/benchmarks/criteria/speckit-development.json` unchanged (agents never edit criteria files) and keep the skill at SPEC-105's minimums; verify with `skill-lab validate --skill speckit-development` — FR-050, FR-053 (depends on T130)
- [ ] T132 [US9] Write and pass `skill-lab/tests/integration/test_r3_us9_handoff_factory.py` (golden delivery hands off and the gateway auto-merges the low-risk PR; forge `github` has no merge path; the factory cap on `Cazador0/skill-factory` and on a tree containing `skill-lab/shared/_skillkit/policy.py`; a synthetic diff of R3's own paths classifies `critical` with `FACTORY_REPOSITORY` and `POLICY_PATHS_TOUCHED`) — FR-052 (depends on T131, T069)
- [ ] T155 [P] [US9] Write failing tests `skills/speckit-development/tests/test_review_request_r3.py` (`--live-runs <evidence/live-runs.json>` puts the summary sha256 of every run in the streak and the sha256 of the `benchmark-streak.v1` record into `evidence[]`; R1's reviewer instructions stay: recorded evidence only, no `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, or `JEV_API_KEY` with `BLOCKED_BY_ENV`, no live re-run stated in the verdict, the separate `<!-- skill-lab:run-health:v1 request_id=<id> -->` comment; round 4 exits 4 `REVIEW_ROUNDS_EXHAUSTED`; a `live-runs.json` whose runs are not consecutive counting runs on one model and suite digest exits 1), then extend `skills/speckit-development/scripts/review_request.py` until they pass — FR-057 (depends on T129, T154)

**Checkpoint**: All user stories are independently functional.

---

## Phase 12: Polish, Gates & Delivery

**Purpose**: Documentation, configuration, catalog, traceability, convergence, release gates, live runs, PR, independent review, human merge

- [ ] T133 [P] Regenerate `skill-lab/docs/autonomy.md` from `policy.catalog_document()` (36 actions; promotion and demotion sections) with drift test `skill-lab/tests/test_autonomy_docs_sync.py`, and write the runbook `skill-lab/docs/runbooks/webhook-gateway.md` (a human creates the Gitea webhook, human-only at every level; a random secret of at least 32 bytes; a TLS-only `https://` endpoint, or loopback; rotation with `GITEA_WEBHOOK_SECRET_PREVIOUS` and `GITEA_WEBHOOK_SECRET_ROTATED_AT`, accepted for 7 days; the per-object rate limit; digests kept 90 days; a link to R1's `skills/gitea-event-normalizer/references/webhook-hygiene.md` instead of repeating it; `ALLOWED_HOST_LIST`; service setup; health via `normalize.py status`; stop and rollback; the gateway host is not monitored by `run-monitor`) — FR-053 (depends on T030, T072)
- [ ] T134 [P] Add the R3 deny rules to `skill-lab/config/zed/settings.example.jsonc` and `skill-lab/config/claude/settings.example.json` (agent edits of `.skill-autonomy/**` and `.skill-state/autonomy/**`; `normalize.py serve` in agent terminals) while keeping R1's deny rules for `.skill-policy.json`, `skill-lab/benchmarks/criteria/**`, and `skill-lab/benchmarks/monitor-limits.json` (SPEC-201 FR-012), keep the Zed provider at the local Ollama app signed in to ollama.com (`http://localhost:11434`) with the cloud model R1 chose, add notes to `skill-lab/config/codex/config.example.toml`, update `skill-lab/config/gitea/skill-gitea.example.json`, create `skill-lab/config/policy/skill-policy.guarded-autonomous.example.json`, extend `skill-lab/lab/config_rules.py`, and write `skill-lab/tests/test_config_rules_r3.py`; verify with `skill-lab validate --config zed,claude,codex` (G-OFF-22) — FR-053 (depends on T072)
- [ ] T135 [P] Update `skill-lab/config/export/AGENTS.md` (what agents may never do at R3: merge medium or above, force-merge, edit promotion files, remove `autonomy/demoted`, continue an expired lease without a recovery record) and `skill-lab/config/export/ci.yml` (offline on every PR and push on Python 3.9 and the current Python: containment at all levels and `--demoted`, R3 integration tests, AFV deterministic run; live tiers only in the manually started `workflow_dispatch` job, SPEC-201 FR-044; still no merge step) (depends on T052, T055)
- [ ] T136 [P] Re-vendor and re-validate the unchanged skills: `skill-lab sync --skill speckit-gitea-taskstoissues`, `--skill twelve-factor-audit`, `--skill skill-forge`, `--skill run-monitor`, then `skill-lab validate` and `skill-lab bench --tier deterministic` for each; `run-monitor` gets no R3 change (FR-058, D-29): `scripts/snapshot.py`, `run-health.v1`, and `skill-lab/benchmarks/monitor-limits.json` stay byte-identical (checked with `git diff --exit-code`) (depends on T051)
- [ ] T137 Generate `skills/CATALOG.json` with `skill-lab catalog` and the 28 discovery symlinks with `skill-lab install --project .`; write `skill-lab/tests/test_skills_r3.py` (14 skills, `run-monitor` listed under `control-plane` and `meta`; `metadata.version` bumped for the 10 changed skills and unchanged for the 4 others; every skill at SPEC-105's minimums; body limits; catalog ≤ 51,200 bytes; 28 symlinks resolve) and `skill-lab/tests/release/test_r3_release_gates.py` (TestMergeRequests over every double log the suites wrote: 0 bodies with `force_merge`, `merge_when_checks_succeed` always `true`, `head_commit_id` always the decided head, 0 system merges of ineligible PRs; TestSecrets: 0 canary values of `GITEA_TOKEN`, `GITEA_WEBHOOK_SECRET`, `GITEA_WEBHOOK_SECRET_PREVIOUS`, `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`); verify with `skill-lab validate --runtime zed,claude,codex` and `python3 -m unittest skill-lab/tests/release/test_r3_release_gates.py` (G-OFF-12, G-OFF-20) (depends on T068, T075, T080, T083, T091, T100, T107, T112, T115, T127, T131, T132, T136)
- [ ] T138 Set `planned: false` for every requirement in `skill-lab/specs/203-release-guarded-autonomous/traceability.json` and in the 10 updated per-skill traceability files whose paths now exist, fix any gap, and pass `skill-lab validate --specs` (G-OFF-21) (depends on T137, T128, T132, T133, T134, T135, T093, T154, T155)
- [ ] T139 Run `python3 skills/speckit-development/scripts/converge.py --feature skill-lab/specs/203-release-guarded-autonomous --apply` into `skill-lab/specs/203-release-guarded-autonomous/evidence/convergence-report.json`; execute any appended Convergence-phase tasks; repeat until `converged: true` (G-OFF-25)
- [ ] T140 Write `skill-lab/specs/203-release-guarded-autonomous/evidence/release-diff.json` from `git diff --name-status --numstat main...HEAD` (the branch starts at the R2 merge commit on `main`) and run `python3 skills/merge-policy-gate/scripts/merge_decision.py --diff-fixture skill-lab/specs/203-release-guarded-autonomous/evidence/release-diff.json` into `skill-lab/specs/203-release-guarded-autonomous/evidence/self-classification.json`; it must report `critical`, `HUMAN_APPROVAL_REQUIRED`, and reasons including `FACTORY_REPOSITORY` and `POLICY_PATHS_TOUCHED` (G-OFF-26)
- [ ] T141 Run `skill-lab policy containment --level shadow`, `--level agent-implementation`, `--level guarded-autonomous`, and `--level guarded-autonomous --demoted` into `skill-lab/specs/203-release-guarded-autonomous/evidence/containment-<level>.json`, then `skill-lab release check --spec SPEC-203 --stage merge --only G-OFF-01,…,G-OFF-28` into `skill-lab/specs/203-release-guarded-autonomous/evidence/gate-report-offline.json`; every offline merge-stage gate G-OFF-01..28 must be `pass` (the live merge-stage gates are T142's)
- [ ] T142 [P] Live gates (merge stage; FR-055): if `OLLAMA_API_KEY`, `TYPESAFE_API_KEY` (or `JEV_API_KEY`), and network to `ollama.com` and `api.typesafe.ai` exist in the benchmark environment, run `skill-lab bench --tier agentic,trigger --runtime ollama-cloud --model <M> --jev live` over all 14 skills on the final R3 suite with the one model R1 chose (14 `run-monitor` health reports per run; a crossed `monitor-limits.json` limit marks the run degraded and it does not count), then `skill-lab score --skill <name> --run <dir> --strict` per skill, `skill-lab score --catalog --run <dir> --strict`, and `skill-lab afv run --tier agentic --from-run <dir>`; commit the run under `skill-lab/benchmarks/runs/<run_id>/`, name it by digest with `skill-lab release record-run --spec SPEC-203` (`evidence/live-runs.json`; nothing copied), and run `skill-lab streak`; repeat until `benchmark-streak.v1` has length ≥ 3 and 0 unstable cases on one model and the tree's suite digest (replay never counts; outage, partial, and degraded runs do not count; fix a 401, 403, or 422 before re-running; cost from `prices.json` or `usage-only`; no cap). Then run `skill-lab release check --spec SPEC-203 --stage merge` into `skill-lab/specs/203-release-guarded-autonomous/evidence/gate-report-merge.json`; every gate G-OFF-01..28 and G-LIVE-01..08 must be `pass`. Without keys or network, record G-LIVE-01..08 as `not_run` with date and reason in `gate-report-merge.json`; the PR then waits, because R3 merges only when its live gates pass. Never fabricate, and never edit a criteria file, `monitor-limits.json`, or `prices.json` (depends on T141, T154)
- [ ] T143 [P] Live Gitea: if `GITEA_URL`, the four role tokens, and a sandbox repository matching SPEC-202's pattern are configured, run `skill-lab smoke gitea --stage merge` (after SPEC-202's lead, pse, review stages) into `skill-lab/specs/203-release-guarded-autonomous/evidence/smoke-merge.json`; otherwise record `not_run` with the reason. RT-02 stays enforced by the client either way (depends on T141, T058)
- [ ] T144 Render the PR body with `python3 skills/speckit-development/scripts/pr_body.py --feature skill-lab/specs/203-release-guarded-autonomous --out skill-lab/specs/203-release-guarded-autonomous/evidence/pr-body.md` from the development, convergence, self-classification, and merge-stage gate reports and `evidence/live-runs.json` (`not run` printed for `not_run` gates); start only when T142 reports every live gate `pass` (depends on T142, T143)
- [ ] T145 Export with `skill-lab/bin/export-repo --out <scratchpad>/skill-factory`, write `skill-lab/specs/203-release-guarded-autonomous/evidence/export-manifest.json`, and pass `skill-lab/bin/export-repo --check <scratchpad>/skill-factory` (G-OFF-23, G-OFF-24; requires `dirty: false`)
- [ ] T146 Release PR (factory delivery, SPEC-202 D-4): run `python3 skills/speckit-development/scripts/delivery_plan.py --step pr` with forge `github` to write `skill-lab/specs/203-release-guarded-autonomous/evidence/pr-request.json`; the orchestrator pushes `release/r3-guarded-autonomous` (created from `main` at the R2 merge commit) to `Cazador0/skill-factory` and opens a PR with base `main` and body `evidence/pr-body.md`. Keep the PR record out of the branch (SPEC-201 D-17)
- [ ] T153 Post the live scores on the R3 PR (SPEC-105 FR-018; intake jev-live-benchmarking Q2): render `skill-lab report --run skill-lab/benchmarks/runs/<run_id>` for each run in the streak (per-skill and catalog results, unsure and flagged cases, unstable cases, tokens and cost basis, degraded or outage status, suite digest) and have the orchestrator post each as a PR comment, followed by one comment with the `benchmark-streak.v1` digest and length
- [ ] T147 Emit the round-1 review request with `python3 skills/speckit-development/scripts/review_request.py --pr-number <N> --pr-url <URL> --head <sha> --base main --live-runs skill-lab/specs/203-release-guarded-autonomous/evidence/live-runs.json --spec SPEC-203 --spec SPEC-001 --spec SPEC-002 --spec SPEC-003 --spec SPEC-005 --spec SPEC-006 --spec SPEC-007 --spec SPEC-008 --spec SPEC-009 --spec SPEC-010 --spec SPEC-013 --round 1 --author-session <this session id>` into `<scratchpad>/r3-post-review/review-request.json` (kept out of the branch, SPEC-201 D-17) and render the reviewer prompt with `--render-prompt` (its `evidence[]` carries the summary sha256 of each of the 3 streak runs and of the `benchmark-streak.v1` record; its instructions are R1's: re-compute the live gates from those committed runs only, hold no `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, or `JEV_API_KEY` (`skill-lab doctor`; `BLOCKED_BY_ENV` when set), never re-run a live case and say so in the verdict, and post the reviewer's own `run-health.v1` as a separate marked comment; the prompt names the R3 checklist: no force-merge path, low-only cap, promotion human-only, latch fail-closed, factory cap, R1's webhook layers reused and not re-implemented, SPEC-105 floor gates, X-1..X-15) — FR-057 (depends on T155, T153)
- [ ] T148 Independent review (runbook `skill-lab/docs/runbooks/release-delivery.md`): the orchestrator calls `create_session` (rendered prompt, `source_url` `https://github.com/Cazador0/skill-factory`, `source_revision` `release/r3-guarded-autonomous`, never `permission_mode: plan`, an `environment_id` whose environment holds no Ollama or TypeSafe key); the reviewer session runs review-verifier, re-runs the offline merge-stage gates and the self-classification, re-computes G-LIVE-01..08 offline from the committed runs whose digests the request carries (recorded evidence only; it re-runs no live case and says so in its verdict), posts the `review-verdict.v1` comment, runs `run-monitor`'s `snapshot.py --target reviewer-session` in its own container, and posts the `run-health.v1` report as a separate comment marked `<!-- skill-lab:run-health:v1 request_id=<id> -->`; the orchestrator polls and runs `python3 skills/speckit-development/scripts/review_collect.py --request <rr.json> --comment-file <comment.md> --repo-dir <export>`, which also requires the reviewer's health comment. If `create_session` is unavailable, use `review_local.py --apply` and post its comment (`reviewer.mode: cli-fallback`) — FR-057
- [ ] T152 Review rounds (FR-057): if the verdict is `CHANGES_REQUESTED`, fix through new Convergence tasks in `skill-lab/specs/203-release-guarded-autonomous/tasks.md` in the authoring session, re-run T138–T141; a fix that changes any `SKILL.md` or eval case changes the suite digest and restarts the streak, so T142 runs again until 3 new consecutive counting runs pass before T153 and T147 for the next round; push and request the next round. At most 3 automated rounds (`REVIEW_ROUNDS_EXHAUSTED` above 3); after round 3 the person decides. With `APPROVE` this task is done with no change
- [ ] T149 Run `skill-lab release check --spec SPEC-203 --stage post-review --ci-checks <checks.json> --verdict <verdict.json>` (G-POST-01, G-POST-02; offline CI green on the PR head) into `<scratchpad>/r3-post-review/gate-report-post-review.json` (out of the branch, attached to the PR thread) (depends on T152)
- [ ] T150 Hand the PR to the human for merge: the merge-stage gate report (T142) passes every offline and live gate on the reviewed head, the verdict is `APPROVE` for that head, and CI is green; if the diff changed after the reviewed head, request a new round first (T152). A human merges; no agent and no R3 code path merges the factory repository. R3 has one exit state, "merged", reached at the human merge, because its live gates already passed at the merge stage; there is no "merged, live-pending" state and no `complete`-stage gate (release-plan.md §4)

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: T001 (R2 merged, E-2) → T002; T151 and T003–T014 in parallel after T002; T015 after the ADRs; T016 after T005, T015, and T151
- **Foundational (Phase 2)**: depends on Setup and BLOCKS all user stories. Contracts first (T017–T023); fixtures (T024–T028) in parallel; then the module pairs (tests → implementation); T051 joins every module; lab commands (T052–T058) in parallel after T051, with T154 (SPEC-105 live-gate evaluation and `record-run --spec SPEC-203`) after T053; T059 last
- **US1 (Phase 3)**, **US2 (Phase 4)**, **US3 (Phase 5)**: start after Foundational; US3's integration test also needs US1's `merge_plan.py` (T065) and US2's processor (T072)
- **US4 (Phase 6)**: needs US1's merge plan (T065) for cancellation and US2's processor (T072) for its integration test
- **US5, US6, US7 (Phases 7–9)**: start after Foundational; their integration tests run through US2's gateway (T072); US6 reads US3's drift state (T082)
- **US8 (Phase 10)**: needs the skill evals of US1–US7 and US9's handoff (T130)
- **US9 (Phase 11)**: needs US1's decision (T064); T155 (review request with streak digests) needs T154
- **Polish (Phase 12)**: depends on every user-story phase. T142 (live gates, 3 consecutive counting runs) and T143 run in parallel after T141. The PR waits for T142: R3 merges only when its live gates pass. Then T144 → T145 → T146 → T153 → T147 → T148 → T152 → T149 → T150, strictly sequential; a review fix that changes a `SKILL.md` or eval case sends the flow back to T142

### User Story Dependencies

- **US1 (P1)**: Foundational only
- **US2 (P1)**: Foundational only
- **US3 (P1)**: Foundational; integration needs US1 and US2
- **US4 (P1)**: Foundational plus US1 (T065); integration needs US2
- **US5, US6, US7 (P2)**: Foundational; integration needs US2
- **US8 (P2)**: US1–US7 and US9's handoff
- **US9 (P3)**: Foundational plus US1 (T064)

### Within Each User Story

- Spec update → failing tests → implementation → references and SKILL.md → evals and criteria → integration test
- Tests MUST fail on assertions before implementation
- `SKILL.md` is written after its scripts exist, so every procedure step names a real command

### Parallel Opportunities

- T003–T014 (verifications, checklist, ADRs)
- T018–T021 (schema groups), T024–T028 (fixtures), and every `[P]` test task of Phase 2
- T052–T058 (lab commands)
- After Phase 2: the opening tasks of US1, US2, US3, US5, US6, US7, and US9 (T060, T070, T077, T094, T102, T109, T129)
- T117–T126 (AFV suites) once their skills' evals exist
- T133–T136 (documentation, configuration, re-validation)

---

## Parallel Example: after the foundation (T059)

```bash
# Seven story tracks can start together:
Task: "Update SPEC-009 in skill-lab/specs/009-merge-policy-gate/spec.md"
Task: "Update SPEC-008 in skill-lab/specs/008-gitea-event-normalizer/spec.md"
Task: "Update SPEC-006 and SPEC-005 (kanban, sync)"
Task: "Update SPEC-007 and SPEC-010 (lease, checkpoint)"
Task: "Update SPEC-001 in skill-lab/specs/001-lead-architect/spec.md"
Task: "Update SPEC-003 and SPEC-002 (review, pse)"
Task: "Update SPEC-013 and write skills/speckit-development/tests/test_handoff_r3.py"
```

---

## Implementation Strategy

### MVP first (US1)

1. Phase 1 Setup, then Phase 2 Foundational
2. Phase 3 US1 → **STOP and VALIDATE**: on the double, the low-risk PR merges through one bound schedule, and nothing else merges

### Control plane next (US2, US3)

3. Phase 4 US2 and Phase 5 US3 → events drive the board; the ordering suite is green

### Safety valve (US4)

4. Phase 6 US4 → demotion within the event; promotion only through a human-merged base commit

### Incremental delivery

5. US5 → US6 → US7 (P2), then US8 verification, then US9 (P3). Each phase ends with its integration test
6. Phase 12: offline gates, then the live gates (3 consecutive counting SPEC-105 runs), then the PR with the live scores, the independent review from recorded evidence, and the human merge

## Notes

- `[P]` tasks touch different files and have no dependency on an incomplete task
- Commit after each task with the attribution trailers; `/speckit-development` marks a task `[x]` only with a passing `check-run.v1`
- Live tasks (T142, T143) record `not_run` with a reason when prerequisites are missing; they never fabricate results. A `not_run` live gate keeps the PR open
- No task edits `.skill-policy.json`, a criteria file, `skill-lab/benchmarks/monitor-limits.json`, or `prices.json`; no task creates a Gitea webhook (human-only)
- Nothing in this task list merges the factory repository; T150 ends with a human merge
