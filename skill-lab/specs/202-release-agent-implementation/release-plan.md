# Release plan: R2 Agent implementation

**Spec ID**: SPEC-202 | **Release**: R2 | **Autonomy level shipped**: `agent-implementation`

**Created**: 2026-10-22 | **Status**: Draft (planning, delivery step 1)

**Parent**: [SPEC-200 release roadmap](../200-release-roadmap/spec.md) | **Previous**: [SPEC-201 R1 Shadow](../201-release-shadow/release-plan.md) | **Next**: SPEC-203 (R3 Guarded autonomous)

**Companion documents**: [synthesis.md](synthesis.md) (step 2), [spec.md](spec.md) and [tasks.md](tasks.md) (step 3),
[plan.md](plan.md) (step 4), [traceability.json](traceability.json).

## 1. Scope in one paragraph

R1 shipped every script, plan, and catalog action that R2 needs, with every consequential `--apply` refused at
`shadow`. R2 raises `policy.SUPPORTED_MAX_LEVEL` to `agent-implementation`. It first adds the base-branch verification
of `.skill-policy.json` that R1 made a precondition. It then makes the 19 actions at that level work, inside narrow,
mechanically checked boundaries:

- **PSE delivery.** A PSE session leases an issue and works in an isolated git worktree on branch
  `agent/pse/<issue>-<slug>`. It commits, pushes **only that branch**, and opens a PR through the hardened Gitea client.
  Every check it reports comes from a command it ran on the commit it reports, with a clean tree.
- **Lead control plane.** The Lead applies R1's dry-run plans idempotently: issues, dependencies, labels, assignment,
  lease, and scoped-label board transitions.
- **Review.** Review posts its verdict to the PR from its own Gitea identity, after an independence check by session
  and by identity.
- **Merge gate.** It stays capped at `HUMAN_APPROVAL_REQUIRED` and audits branch protection against the report's
  recommended `main` policy.
- **`/speckit-development`** (SPEC-013) delivers a feature end to end, from worktree to PR to an independent review
  request.
- **L1 local inference.** R2 ships the mechanism: local Ollama Zed profiles stay gated until a measured gate passes:
  3 consecutive live cloud runs, a recorded human sign-off, then the same suite on `ollama-local`.

Everything runs offline against the Gitea 28.x test double first. It goes live only when `GITEA_URL`, `GITEA_TOKEN`,
`OLLAMA_API_KEY`, and `TYPESAFE_API_KEY` (or `JEV_API_KEY`) are present, and no live result is ever fabricated.

## 2. Release goals

Each goal is measurable. `spec.md` §Release goals maps every goal to its FRs, SCs, and gates.

| ID | Goal | Measure (threshold) |
|---|---|---|
| RG-1 | PSE delivers a real PR from an isolated worktree under a lease | Golden end-to-end run on the double: exactly 1 PR per issue from `agent/pse/<issue>-<slug>`; 100 % of reported checks trace to a `check-run.v1` on the reported head with `tree_clean: true`; 0 pushes to any other ref |
| RG-2 | Control-plane writes are idempotent and crash-safe | Each of the 10 apply entry points re-run: 0 additional writes in the double's write log. Fault after every op index: 0 duplicate issues, dependencies, labels, comments, PRs, or reviews after resume |
| RG-3 | Review posts verdicts independently | 0 of 5 independence and freshness violation kinds accepted; every posted review carries a schema-valid `review-verdict.v1` whose `reviewed_commit` equals the PR head at post time |
| RG-4 | No agent merges; branch protection is audited | `AUTO_MERGE` emitted 0 times and merge endpoint called 0 times at `agent-implementation`; branch audit correct on 12 of 12 fixtures (recommended policy, 10 single-field deviations, 1 unknown field) |
| RG-5 | `/speckit-development` delivers end to end | Golden feature: tasks to PR to review request to posted verdict, every step in a schema-valid `delivery-record.v1`; resume after an interruption at each step completes with 0 duplicate side effects |
| RG-6 | Authority stays bounded by policy | At `shadow`, 19 of 19 R2 actions exit 4 (catalog 1.0.0); at `agent-implementation`, 7 of 7 R3 actions exit 4; 60 of 60 human-only refusals; 0 effective-level escalations from a working-tree-only policy raise; 0 secret canary leaks |
| RG-7 | Local inference L1 ships behind its measured gate | Gate evaluator 100 % correct on a fixture matrix of ≥ 12 rows; local profiles installed 0 times without an `ENABLED` `inference-gate.v1` matching the current suite digest and model |
| RG-8 | Live readiness without fabrication | With credentials: G-LIVE-01..05 pass on ≥ 1 complete run of the R2 suite, and the live Gitea smoke test passes all 4 stages with full cleanup. Without them: `not_run` with a reason, never a pass |
| RG-9 | Portable quality bar holds for all 13 skills | `skill-lab validate` 0 errors (zed, claude, codex); `sync --check` 0 drift; 100 % unit tests (Python 3.9 and current) and ≥ 112 deterministic cases passing; 0 inventory violations; catalog ≤ 51,200 bytes |
| RG-10 | The release itself follows the delivery process | The R2 PR has an `APPROVE` `review-verdict.v1` from a session other than every authoring session, in ≤ 3 rounds; merge-policy-gate classifies the R2 diff `critical` → `HUMAN_APPROVAL_REQUIRED` |

## 3. Entry criteria

R2 step 5 (execute) does not start until all of these hold. T001 records each one, with evidence, in
`skill-lab/specs/202-release-agent-implementation/evidence/entry-check.json`.

| ID | Criterion | Evidence |
|---|---|---|
| E-1 | The R1 PR (SPEC-201) has an `APPROVE` `review-verdict.v1` from the independent reviewer session, accepted by `review_collect.py` (roadmap: "R2 starts only after the R1 PR has an APPROVE verdict") | PR comment URL, request ID, verdict digest (copied from R1's post-review evidence) |
| E-2 | Branch `release/r1-shadow` exists on `Cazador0/skill-factory`, and its head is the reviewed commit | `git ls-remote` output |
| E-3 | R1's `release check --spec SPEC-201 --stage merge` reports every gate `pass` on that head | `release-gate-report.v1` |
| E-4 | R1 deliverables R2 builds on exist under the names SPEC-201 gives them: `_skillkit.policy` (catalog of 34 actions, `SUPPORTED_MAX_LEVEL`), `_skillkit.gitea` (`GiteaClient.send`), `_skillkit.gitrepo`, `_skillkit.checks` (`check-run.v1`), the read-only Gitea double, the containment harness, `release check`, `export-repo`, and the scripts listed in §5 | T005 writes `evidence/r1-alignment.json` |
| E-5 | This folder's six artifacts exist, and `lead-architect` readiness on this spec reports no failing check | `spec-readiness.v1` envelope (T006) |
| E-6 | Merge of R2 (step 8) additionally requires R1 merged to `main` by a human | GitHub PR state |

E-6 gates step 8 only. Steps 5–7 may proceed while R1 waits for its human merge, because the R2 PR is stacked on the
R1 branch (user decision), which matches R1's own plan (SPEC-201 release-plan §4).

## 4. Exit criteria

R2 uses the same two exit states as R1, so "not run never counts as pass" (CONVENTIONS §9, ADR-0010) holds without
blocking the merge on a network allowlist that the user has not finished yet.

**R2 merged** (end of step 8):

- X-1: `release check --spec SPEC-202 --stage merge` reports every gate G-OFF-01..G-OFF-23 `pass`.
- X-2: converge reports 0 findings against this spec, plan, and tasks (G-OFF-23).
- X-3: a separate Claude Code cloud session posted an `APPROVE` `review-verdict.v1` on the R2 PR, and `review_collect.py`
  accepted it (G-POST-02).
- X-4: CI on the PR head is green (G-POST-01), R1 is merged, and a human merged R2.

**R2 complete**:

- X-5: `release check --spec SPEC-202 --stage complete` reports G-LIVE-01..05 `pass` on ≥ 1 complete run of the R2
  suite, and R1 is complete. Until then R2 is "merged, live-pending". R3 step 5 may still start at R2's `APPROVE`
  (the same rule R1 applies to R2, D-20), but R3 cannot be complete and no project can be promoted while R2 is
  live-pending. A live gate that ran and failed stops R3 from starting.
- X-6: L1 is not an exit criterion. It is milestone M-L1 on the inference track, which runs in parallel with R3
  (roadmap sequencing diagram). Its gate record must be honest: `NOT_ENABLED` with reasons is a valid record.
- X-7: the live Gitea smoke test (RT-01) is not an exit criterion either, because the user decided "test double now,
  live later". It is enforced at runtime instead: the Gitea client refuses consequential writes to any non-loopback
  host until a passing `smoke-report.v1` for that host exists (FR-041).

## 5. In and out of scope per skill

Script names are SPEC-201's. R2 enables their `--apply` paths, or adds the few new scripts named here.

| Skill | In scope for R2 | Out of scope (where it goes) |
|---|---|---|
| lead-architect | `dispatch_recommend.py --apply`, following the report's "claiming work safely" sequence (assign the PSE identity, local lease with base SHA, `IN_PROGRESS`, lease mirror). `arbitrate.py --publish --apply`. New `complete_issue.py` (`state/done` after an observed human merge; reports `CLOSE_PENDING`) | Event-driven dispatch loop, auto-dispatch of unlocked work, closing issues (R3) |
| pse-implementer | `delivery_plan.py --apply --step worktree\|branch\|commit\|push\|pr` (SPEC-201 step names, through `_skillkit.delivery`); evidence integrity bound to `check-run.v1` with `tree_clean`; lease, scope, and policy-path enforcement | Rebase on a stale base (`git.push.force_own_branch`, R3); conflict resolution (always human) |
| review-verifier | `review_verdict.py --comment-plan --post --apply`: Gitea review plus R1's verdict comment; independence by session (R1) and identity (R2); freshness at post time | Invalidating stale approvals on new-head events (R3) |
| speckit-gitea-taskstoissues | `tasks_to_issues.py --apply`: idempotent, journaled, map plus title-regex dedupe across open and closed issues | Project-board columns (labels only) |
| speckit-gitea-sync | `comment_plan.py --apply` (`create_comment` ops only) | Drift check on events (R3); rewriting specs (never) |
| kanban-state-machine | `labels_plan.py --apply`: scoped `state/*` labels by required role, with the decision recomputed from live state | Event-driven transitions (R3); project columns |
| work-lease | `lease.py … --mirror --apply`; `_skillkit.leases.verify` enforced by every PSE mutation | Expiry recovery and takeover (R3); multi-host lease authority |
| gitea-event-normalizer | No change (R2 polls; it does not consume events) | Webhook gateway `serve` (R3) |
| merge-policy-gate | Cap stays at `HUMAN_APPROVAL_REQUIRED` with `uncapped_decision`; new `branch_audit.py` (BP-01..BP-12); `merge_decision.py` consumes `review-post.v1` and `branch-protection-audit.v1` | `AUTO_MERGE` for low risk; `merge_plan.py --apply` (R3) |
| session-checkpoint | `checkpoint.py publish --apply` (marked issue comment) | Lease-recovery consumption (R3) |
| twelve-factor-audit | No change | — |
| skill-forge | No change | — |
| speckit-development | End to end: new `delivery_record.py` (resumable step state); `delivery_plan.py --apply --step worktree\|branch\|commit\|push\|pr\|review-request\|review-session` (shared executor; review-request asks the Review login on Gitea, review-session writes the dispatch); R1's `dev_state.py`, `converge.py` (≤ 3 passes), `pr_body.py`, `review_local.py`, and `review_collect.py` unchanged | Hand-off to auto-merge (R3) |
| Policy machinery | `SUPPORTED_MAX_LEVEL` raised; base-branch verification; containment at `agent-implementation` | Promotion and demotion by metrics (R3) |
| Lab | Write endpoints in the test double (engine moved to `_skillkit.gitea_memory`); live Gitea smoke test; L1 gate evaluator; `signoff`; `doctor --runtime ollama-local`; installer `--inference local` gate; `ollama-local` parity; validator rule `eval-inventory-r2`; `gates.json` | Changing scoring semantics (SPEC-104 owns them) |

## 6. Risks (summary; synthesis.md §5 has detail and mitigations)

| ID | Risk | Likelihood | Impact | Mitigation in this release |
|---|---|---|---|---|
| RK-1 | Gitea 28.x endpoint or field drift from the double | Medium | High | Swagger verification (T003), endpoint table, live smoke test before the first live write |
| RK-2 | Lost update between read and write | Medium | Medium | Observed-state digest plus re-read after write; leases serialize writers |
| RK-3 | The lease store is single-host | High (by design) | Medium | Declared limit (ADR-0202); mirror conflict detection |
| RK-4 | An agent bypasses scripts with raw `git push` or HTTP | Medium | High | Runtime deny patterns (guardrail); branch protection plus least-privilege tokens are the boundary |
| RK-5 | The R2 PR itself changes the policy clamp, permission configs, and the review gates (critical risk) | Certain | High | Human merge is mandatory; the reviewer checklist names those paths; self-classification must say `critical` |
| RK-6 | A local model on a < 24 GB GPU cannot follow the procedures at 32k context | Medium | Medium | Measured L1 gate; cloud fallback stays installed |
| RK-7 | The network allowlist is not ready, so live gates stay `not_run` | Medium | Medium | "Merged, live-pending" exit state |
| RK-8 | CLI-fallback review gives weaker independence | Medium | Medium | Mode recorded in the verdict (R1 contract); posting needs the Review identity |
| RK-13 | A missing `origin/<base>` ref puts projects at `shadow` | Medium | Low | Intended fail-closed behaviour; runbook says `git fetch origin <base>` |

## 7. Milestones

| ID | Milestone | Contents (tasks.md phases) | Done when |
|---|---|---|---|
| M0 | Entry | Phase 1 (T001–T006) | E-1..E-5 recorded; R1 alignment recorded |
| M1 | Foundation for writes | Phase 2: contracts, clamp plus base-branch check, Gitea client, mutation ledger, plan applier, leases, git write helpers, delivery executor, double | Phase 2 tests green; `sync --check` clean |
| M2 | MVP: PSE PR on the double | Phase 3 (US1) | `test_r2_us1_pse_delivery.py` green |
| M3 | Review and merge gate | Phase 4 (US2) | `test_r2_us2_review_merge.py` green |
| M4 | Lead drives the board | Phase 5 (US3) | `test_r2_us3_lead_board.py` green |
| M5 | End-to-end delivery | Phase 6 (US4) | Golden end-to-end and resume tests green |
| M6 | L1 mechanism and live smoke test | Phases 7 and 8 (US5, US6) | Gate matrix, installer, and smoke-against-double tests green |
| M7 | Release candidate | Phase 9: ADRs, CONVENTIONS, configs, validator rule, gates, catalog, traceability, offline gates, converge | `release check --stage merge` passes; converge has 0 findings |
| M8 | PR, review, merge | Phase 9 tail (T138–T142) | X-1..X-4 |
| M-LIVE | Live completion | T135 when keys and network exist; T136 when Gitea is configured | X-5 (G-LIVE-01..05); RT-01 unlocks live writes |
| M-L1 | Local inference enabled | §10 procedure (live, human; outside tasks.md) | `inference-gate.v1` `ENABLED`, and the user applies the installer |

## 8. Delivery steps for this release

The roadmap's eight steps, made concrete for R2. Steps 5–8 follow SPEC-201's `skill-lab/docs/runbooks/release-delivery.md`.

| Step | What happens in R2 | Artifact | Who |
|---|---|---|---|
| 1 Plan | This document | `release-plan.md` | Lead (planning session) |
| 2 Synthesize | Findings F-1..F-38, decisions D-1..D-26, verifications V-1..V-7, risks, open questions Q-1..Q-9 | `synthesis.md` | Lead |
| 3 Tasks as spec | FRs, SCs, gates, contracts, autonomy policy; dependency-ordered tasks | `spec.md`, `tasks.md`, `traceability.json` | Lead |
| 4 Implementation plan | Technical context, constitution check, exact files, endpoint table, test and benchmark strategy, rollout and rollback | `plan.md` | Lead |
| 5 Execute | Work happens in a checkout of `Cazador0/skill-factory` on branch `release/r2-agent-implementation`, created from the `release/r1-shadow` head. `/speckit-development` drives `tasks.md` in dependency order. It is the R1 build, running at `shadow` against the factory repository: one task per step, marked `[x]` only with passing `check-run` evidence, and converge until 0 findings. Evidence goes to `skill-lab/specs/202-release-agent-implementation/evidence/`. The new R2 write capabilities are exercised only against the Gitea test double, plus a sandbox Gitea repository when one is configured, never against the factory repository | Code, tests, evals, evidence | PSE sessions, orchestrated |
| 6 Pull request | `pr_body.py` renders `evidence/pr-body.md`, and `export-repo` builds and checks the standalone tree. `delivery_plan.py --step pr --forge github` (no `--apply`; the factory repository runs at `shadow`) writes `evidence/pr-request.json`. The orchestrator, not a skill (D-4), pushes `release/r2-agent-implementation` and opens a PR with base `release/r1-shadow` (stacked) | GitHub PR | Orchestrator |
| 7 Review | `review_request.py` writes `review-request.v1` (forge `github`, round 1). The orchestrator creates a separate Claude Code cloud session with `create_session` on the release branch. That session loads `.claude/skills/review-verifier`, rebuilds the requirements matrix from this `spec.md`, re-runs `release check --stage merge`, runs merge-policy-gate on the diff (expects `critical`), and posts a `review-verdict.v1` comment with R1's marker. If no cloud session can be created, R1's `review_local.py` (`claude -p --json-schema`) is the fallback, and the verdict records `mode: cli-fallback`. `review_collect.py` accepts the verdict. At most 3 rounds | PR comment | Independent reviewer |
| 8 Merge | `release check --stage post-review` passes (CI green, verdict collected). Once R1 is merged and `release/r1-shadow` is gone, the orchestrator retargets the base to `main` (`gh pr edit --base main`); if the diff changed, step 7 runs again. A human merges | Merged PR | Human |

## 9. Release branch and naming

| Item | Value | Note |
|---|---|---|
| Release branch | `release/r2-agent-implementation` | Created from `release/r1-shadow` (SPEC-201 release-plan §9) |
| PR base | `release/r1-shadow` (stacked); `main` after R1 merges | User decision |
| PSE branches produced by the skills | `agent/pse/<issue>-<slug>` in the Gitea target repository | Report: "Recommended branch format" |
| Evidence folder | `skill-lab/specs/202-release-agent-implementation/evidence/` | Created during step 5. Evidence produced at or after the reviewed head (review request, verdict, post-review gate report) stays out of the branch and lives in the PR thread (SPEC-201 D-17) |
| Gate definitions | `skill-lab/specs/202-release-agent-implementation/gates.json` | `release-gates.v1` (SPEC-201) |
| ADR numbers | ADR-0201..ADR-0207 used; 0201–0209 reserved for R2 | R1 uses 0101–0109; R3 is expected to use 0301–0309 |

## 10. Milestone M-L1 procedure (local inference, outside the task graph)

M-L1 runs after R2's mechanism exists (Phase 7) and live cloud runs are possible (T135). It runs in parallel with R3 and
never blocks the R2 merge or R3 (X-6). It sits outside `tasks.md`: under SPEC-201's wave rule, a story phase that waits on
Polish would form a cycle, and its artefacts cannot exist at merge time. Every command records evidence, and none
fabricates a result.

| Step | Who | Command | Output | Passes when |
|---|---|---|---|---|
| L1-a | orchestrator | `skill-lab bench --runtime ollama-cloud --jev live --tier agentic` and `--tier trigger`, then `skill-lab release record-run`, repeated on one commit and suite digest with the model from `skill-lab/config/zed/cloud-models.json` | `evidence/bench/<run_id>.summary.json` (×3 or more) | 3 consecutive eligible runs each pass G-LIVE-01..05 (D-17) |
| L1-b | orchestrator | `skill-lab gate l1 --stage cloud --model <m>` | `skill-lab/benchmarks/gates/l1-cloud-<m>.json` | `cloud.passed: true` (gate L1-01) |
| L1-c | **user** | `skill-lab signoff create --subject inference-enablement --model <m>` (interactive; reviews the deterministic sample set) | `skill-lab/benchmarks/signoff/<date>-inference-enablement-<m>.json` | `decision: approve`, bound to the L1-a run digests (gate L1-02); agents never create this file |
| L1-d | user or orchestrator | `skill-lab doctor --runtime ollama-local --model <local-m>` | doctor envelope | reachable, model pulled, context ≥ 32768, GPU residency reported (Q-1 picks the model) |
| L1-e | orchestrator | `skill-lab bench --runtime ollama-local --jev live --tier agentic` and `--tier trigger`, then `release record-run`, ×3 on the same suite digest | `evidence/bench/<run_id>.summary.json` | 3 consecutive runs each pass the same gates (gate L1-03) |
| L1-f | orchestrator | `skill-lab gate l1 --model <local-m>` | `skill-lab/benchmarks/gates/l1-<local-m>.json` | `decision: ENABLED` |
| L1-g | **user** | `skill-lab install --runtime zed --inference local` | local profiles installed next to the cloud profiles | the installer finds the matching `ENABLED` record; `install --check` reports no drift |

Demotion: any later run that fails its gates, or a suite or model change, flips the next `gate l1` evaluation to
`NOT_ENABLED`. `install --check` then reports drift, and the runbook says to switch the threads back to the cloud profiles.

