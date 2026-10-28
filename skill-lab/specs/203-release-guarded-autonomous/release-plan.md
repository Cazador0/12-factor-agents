# Release plan: R3 Guarded autonomous

**Spec ID**: SPEC-203 | **Release**: R3 | **Autonomy level shipped**: `guarded-autonomous`

**Created**: 2026-10-22 | **Status**: Draft (planning, delivery step 1); aligned on 2026-10-22 with SPEC-105 and the
person's final decisions recorded in SPEC-201 §Clarifications (see spec.md §Clarifications)

**Parent**: [SPEC-200 release roadmap](../200-release-roadmap/spec.md) | **Previous**: [SPEC-202 R2 Agent implementation](../202-release-agent-implementation/release-plan.md) | **Next**: none (the report's long-horizon and self-improving modes are out of this roadmap)

**Companion documents**: [synthesis.md](synthesis.md) (step 2), [spec.md](spec.md) and [tasks.md](tasks.md) (step 3),
[plan.md](plan.md) (step 4), [traceability.json](traceability.json).

## 1. Scope in one paragraph

R2 made every `agent-implementation` action real and kept the merge human. R3 raises `policy.SUPPORTED_MAX_LEVEL` to
`guarded-autonomous` and makes the 7 actions at that level executable, inside the report's "guarded autonomous mode":
"low-risk PRs automatically merge when protected-branch, CI, Review, freshness, and dependency gates all pass.
Medium/high-risk work still requires human approval" (report §Progressive autonomy). Concretely:

- **Auto-merge, low risk only.** `merge-policy-gate` returns `AUTO_MERGE` only for low-risk agent PRs with **every**
  gate passing: Review `APPROVE` on the current head, quality gate passed, required CI success, up to date with the
  base, no requested changes, no outstanding review requests, dependency issues closed, plus compliant branch
  protection and a non-admin merge identity. It applies the decision only through Gitea's merge-when-checks-succeed
  (`POST /repos/{owner}/{repo}/pulls/{index}/merge` with `merge_when_checks_succeed: true` and `head_commit_id`).
  There is no force-merge path. Medium, high, and critical risk always go to a human. The factory repository
  (`Cazador0/skill-factory`) is always human-merged.
- **Event-driven control plane.** `gitea-event-normalizer serve` is the live webhook gateway, built on the four
  replay-defence layers R1 already ships (SPEC-201 FR-025, refinement ledger row 2): body-SHA-256 dedupe, a freshness
  guard on the signed `updated_at` and head SHA (an older body is `stale` and never drives a state change), events
  treated as hints that are re-read before any decision, and secret hygiene (a random secret of at least 32 bytes,
  TLS-only endpoint guidance, `GITEA_WEBHOOK_SECRET_PREVIOUS` accepted for 7 days after a rotation, a per-object rate
  limit, no logging of a body that fails its signature; digests kept 90 days; the delivery ID is metadata only). R3 adds the HTTP
  transport and its bounds, acknowledgement only after a durable write, a bounded inbox, and a deterministic processor
  that routes each event to the kanban state machine, Lead dispatch, the merge gate, review invalidation, lease
  recovery, and the drift check. R3's route policy over R1's freshness verdicts makes out-of-order events (a
  `PR_UPDATED` before a delayed `REVIEW_APPROVED`) harmless, and a reconcile sweep repairs lost deliveries.
- **Lease expiry recovery.** Expiry never means blind continuation. `work-lease recover` inspects the branch, its
  commits, the push receipts, the PR, and the last checkpoint, then classifies the case. Only a successor holding a
  fresh recovery record may take over.
- **Promotion and demotion by metrics.** A scorecard computes the report's core metrics and, for model reliability,
  reuses SPEC-105's run data (`benchmark-run.v1`, `benchmark-streak.v1`, `run-health.v1`). An escaped defect, a revert,
  a containment breach, a gate-integrity violation, or a lease violation **demotes the project automatically** to
  `agent-implementation` within the processing of the triggering event. Only a human promotes: through a
  human-merged change to `.skill-policy.json` on the base branch, bound to a human sign-off and an eligible scorecard.
- **Agentic-framework verification.** Ten eval suites (intent preservation, tool correctness, permission containment
  including nested subagent authority, prompt-injection resilience, long-horizon recovery, idempotency, ordering,
  concurrency, failure recovery, grounding) become release gates, plus an offline long-horizon soak test.

Everything runs offline against the R2 Gitea test double first, extended with merge-when-checks-succeed semantics and
signed webhook emission. Live Gitea merges are refused per host until a sandbox merge smoke stage has passed. Live
model and Jev runs use SPEC-105's harness (delivered inside R1) when `ollama.com` and `api.typesafe.ai` are reachable,
and no result is ever fabricated. R3 merges only when its live gates pass: there is no "merged, live-pending" state
(the person's decision, intake `jev-live-benchmarking` Q1 and Q15, SPEC-201 refinement ledger row 5).

The catalog has **14 skills**: R1 adds `run-monitor` (skill 14, SPEC-014, family `control-plane`, secondary family
`meta`; intake Q22). R3 does not change its scripts; the webhook gateway runs its `local-container` snapshot inside the
gateway's Rancher Desktop container (§5).

## 2. Release goals

Each goal is measurable. `spec.md` §Release goals maps every goal to its FRs, SCs, and gates.

| ID | Goal | Measure (threshold) |
|---|---|---|
| RG-1 | Low-risk PRs auto-merge only when every gate passes; everything else stays human | Golden loop on the double: 100 % of eligible low-risk PRs merged through merge-when-checks-succeed bound to the decided head; 0 system merges of medium, high, or critical PRs; 0 mismatches over the exhaustive decision matrix (32,768 gate × risk combinations, 13 single-`not_run` cases, 192 cap combinations); 0 merge requests carrying `force_merge`, lacking `head_commit_id`, or with `merge_when_checks_succeed` other than `true` |
| RG-2 | A verified, deduplicated, crash-safe event-driven control plane | 0 unverified or duplicate deliveries processed over ≥ 20 fixtures; a crash injected at each of the 6 pipeline steps loses 0 acknowledged events and processes each event's side effects once |
| RG-3 | Safety does not depend on event order | 0 unsafe merges and 0 final-state mismatches over 6 canonical scenarios (≤ 5 events each): every delivery order after the world has fully advanced plus every single-delay interleaving (≤ 756 runs), each followed by one reconcile tick |
| RG-4 | The system demotes itself; only a human promotes | 5 of 5 trigger kinds demote within the triggering event, with 0 system-scheduled merges outstanding afterwards; 0 guarded actions succeed after a demotion; 0 effective `guarded-autonomous` levels without a valid base-branch promotion over ≥ 40 hostile fixtures |
| RG-5 | Lease expiry is recovered from evidence, never blindly | 100 % correct classification on ≥ 14 recovery fixtures covering rules R-0..R-9; 0 takeovers without a fresh recovery record; 0 automatic adoptions of a dirty worktree |
| RG-6 | Event-driven dispatch stays inside limits and narrowed authority | 0 dispatches above `max_concurrent_pse_sessions` or `max_dispatches_per_day`; 0 accepted escalations over the authority-narrowing fixture matrix |
| RG-7 | Stale heads are handled; conflicts go to a human | 0 merges on an approval of a non-head commit; 100 % of rebase conflicts end with `rebase --abort` and a human escalation; 0 pushes other than `--force-with-lease` with the recorded expected SHA on the leased branch |
| RG-8 | Agentic-framework verification proves the safety properties | 10 of 10 AFV suites meet their minimum case counts (45 deterministic, 14 agentic in total) and pass 100 % deterministically; the soak test reports 0 invariant violations |
| RG-9 | Portable quality bar and cloud reliability | `skill-lab validate` 0 errors (zed, claude, codex) for all 14 skills; `sync --check` 0 drift; 100 % unit tests on Python 3.9 and current; ≥ 206 deterministic cases passing; SPEC-105 eval minimums for every skill (≥ 4 deterministic, ≥ 5 agentic with ≥ 1 `guardrail`, ≥ 10 trigger with ≥ 2 expecting no skill); 0 inventory violations; catalog ≤ 51,200 bytes; 0 canary secret leaks. Live (merge stage): SPEC-105's floor gates per skill **and** catalog-wide (agentic ≥ 0.80, trigger ≥ 0.90, agentic schema-valid ≥ 0.95, uncertain after re-ask < 0.10, guardrail cases 100 %) plus AFV agentic ≥ 0.90, on each of 3 consecutive counting `ollama-cloud` runs with Jev live on one model and the R3 suite digest (`benchmark-streak.v1` length ≥ 3, 0 unstable cases): G-LIVE-01..08 |
| RG-10 | The release follows the delivery process; the factory stays human-merged | Independent `APPROVE` `review-verdict.v1` for the current head in ≤ 3 rounds (after round 3 the person decides), from a reviewer that reads recorded evidence only and holds no Ollama or TypeSafe keys, plus its own `run-health.v1` comment; merge-policy-gate classifies the R3 diff `critical`, decision `HUMAN_APPROVAL_REQUIRED`, reasons including `FACTORY_REPOSITORY`; a human merges |

## 3. Entry criteria

R3 step 5 (execute) does not start until all of these hold. T001 records each one, with evidence, in
`skill-lab/specs/203-release-guarded-autonomous/evidence/entry-check.json`.

| ID | Criterion | Evidence |
|---|---|---|
| E-1 | The R2 PR (SPEC-202) has an `APPROVE` `review-verdict.v1` from the independent reviewer session, accepted by `review_collect.py` (roadmap: R3's branch is created from `release/r2-agent-implementation` once R2 has an `APPROVE` verdict and its live gates passed) | PR comment URL, request ID, verdict digest from R2's post-review evidence |
| E-2 | Branch `release/r2-agent-implementation` exists on `Cazador0/skill-factory`, and its head is the commit E-1's verdict reviewed (stacked PRs, intake A4; correction recorded 2026-10-22; synthesis D-32) | `git ls-remote` output |
| E-3 | `release check --spec SPEC-202 --stage merge` reports every gate `pass` on the reviewed head. A release merges only when its live gates pass (intake Q1, Q15; SPEC-201 refinement ledger row 5), so SPEC-202's live gates are merge-stage gates and E-3 includes them | `release-gate-report.v1` |
| E-4 | SPEC-202's live gates passed on recorded SPEC-105 runs: the run ids and `benchmark-run.v1` digests under `skill-lab/benchmarks/runs/` that SPEC-202's `evidence/live-runs.json` names and the R2 reviewer read are recorded, and none of R2's live gates is `fail` or `not_run`. If SPEC-202 as built still separates a `complete` stage, T001 records it and requires that stage to pass too | `release-gate-report.v1`; run digests |
| E-5 | R2 deliverables R3 builds on exist under SPEC-202's names: `_skillkit.policy` (base-branch verification), `_skillkit.gitea` (endpoint table, `GiteaClient.send`), `_skillkit.gitea_memory`, `_skillkit.mutations`, `_skillkit.markers`, `_skillkit.plan_apply`, `_skillkit.leases`, `_skillkit.delivery`, `gitea-project.v1`, `review-post.v1`, `branch-protection-audit.v1`, `delivery-record.v1`, `human-signoff.v1`, `skill-lab smoke gitea`, `skill-lab signoff`, `skill-lab gate l1`, `skill-lab policy containment --level`, `skill-lab release record-run`; and the R1 deliverables R3 relies on: R1's four webhook layers (SPEC-201 FR-025) and SPEC-105's harness delivered inside R1 (`score --catalog`, `skill-lab streak`, `skill-lab report`, `run-monitor` `snapshot.py`, `prices.json`, `monitor-limits.json`) | T002 and T151 write `evidence/r2-alignment.json` |
| E-6 | This folder's six artifacts exist, and `lead-architect` readiness on this spec reports no failing check | `spec-readiness.v1` envelope (T016) |
| E-7 | Merge of R3 (step 8) additionally requires R2 merged into `main` by a human and the R3 PR retargeted to `main` | GitHub PR state of both PRs |

E-1..E-6 hold before step 5 starts; E-7 gates step 8 only. Steps 5–7 may proceed while R2 waits for its human merge,
because the R3 PR is stacked on the R2 branch: `release/r3-guarded-autonomous` is created from the
`release/r2-agent-implementation` head, and the R3 PR targets that branch until R2 merges (synthesis.md D-32, Q-4
resolved). If the R2 head changes before its merge (a new R2 review round), R3 rebases onto the new head and T001
re-records E-1..E-4.

## 4. Exit criteria

R3 has **one** exit state, "merged". A release merges only when its live gates pass; there is no "merged,
live-pending" state (the person's decision: intake `jev-live-benchmarking` Q1 "the result decides whether the R1 PR is
ready" and Q15, applied to every release by SPEC-201 refinement ledger row 5). "Not run never counts as pass"
(CONVENTIONS §9, ADR-0010) therefore blocks the merge while the network allowlist or the keys are missing.

**R3 merged** (end of step 8):

- X-1: `release check --spec SPEC-203 --stage merge` reports every gate G-OFF-01..G-OFF-28 **and** G-LIVE-01..G-LIVE-08
  `pass`. The live gates use SPEC-105's floor model per skill and catalog-wide, read only from counting runs committed
  under `skill-lab/benchmarks/runs/<run_id>/`, and need 3 consecutive counting runs on one model and the R3 suite digest
  (`benchmark-streak.v1` length ≥ 3, D-24).
- X-2: converge reports 0 findings against this spec, plan, and tasks (G-OFF-25).
- X-3: a separate Claude Code cloud session posted an `APPROVE` `review-verdict.v1` on the R3 PR for its current head,
  and `review_collect.py` accepted it (G-POST-02). The reviewer used recorded evidence only, held no Ollama or TypeSafe
  keys, said so in its verdict, and posted its own `run-health.v1` report as a separate marked comment (SPEC-105
  FR-023, research R-12). At most 3 review rounds; after round 3 the person decides.
- X-4: offline CI on the PR head is green (G-POST-01; live tiers run only when started manually), R2 is merged and the
  R3 PR is retargeted to `main` (E-7), and a human merged R3.
- X-5: the live Gitea merge smoke stage (RT-02) is **not** an exit criterion, because the user decided "test double
  now, live later". It is enforced at runtime: the client refuses `gitea.pr.merge_when_checks_succeed` against any
  non-loopback host until a passing `smoke-report.v1` with stage `merge` exists for that host and Gitea version.
- X-6: no project is promoted by the release. Promotion of a target project to `guarded-autonomous` is milestone
  M-PROMO, a human act that requires R3 merged (promotion criterion P-8, which also reads SPEC-105's streak).

R3 adds no gate to a `complete` stage; `release check --spec SPEC-203 --stage complete` has nothing to evaluate.

## 5. In and out of scope per skill

Script names are SPEC-201's and SPEC-202's. R3 enables their guarded paths or adds the few new scripts named here.

| Skill | In scope for R3 | Out of scope |
|---|---|---|
| lead-architect | `dispatch_recommend.py --on-event --apply` (unlock-driven dispatch within capacity, daily budget, and drift state); new `dispatch_session.py write\|run` (`session-dispatch.v1`, role runners, authority narrowing); `complete_issue.py --apply` closes the issue at `guarded-autonomous` (`gitea.issue.close`) | Long-horizon decomposition of new specs; multi-host scheduling |
| pse-implementer | `delivery_plan.py --apply --step rebase` (local rebase onto the moved base) and `--step push --force-with-lease` (`git.push.force_own_branch`, own leased branch only, exact expected SHA) | Resolving rebase conflicts (always human) |
| review-verifier | New `invalidate.py`: marks verdicts for non-head commits stale (local) and, run by the Review identity, dismisses stale Review approvals (`gitea.pr.review.dismiss`) | Approving anything automatically; repairing PSE code |
| speckit-gitea-taskstoissues | No change (re-validated) | — |
| speckit-gitea-sync | `sync_drift.py --on-event --apply`: drift check on issue and base-branch events, R2 comment plan once, drift state that dispatch honours | Rewriting specs or the map (never) |
| kanban-state-machine | `labels_plan.py --on-event\|--reconcile --apply` as `system`: observed-fact transitions recomputed from live state | Role-owned work transitions by `system`; project columns |
| work-lease | `lease.py recover\|takeover\|expired`: recovery protocol R-0..R-9, takeover gated by a fresh `lease-recovery.v1`, orchestration lease for the gateway; TTL and grace constants | Multi-host lease authority |
| gitea-event-normalizer | `normalize.py serve\|ingest\|process\|reconcile\|status`: the webhook gateway on R1's four replay-defence layers (called, not re-implemented), the event processor with the fixed routing table, the route policy over R1's `stale` flag and R3's `stale_commit` verdict, and a `run-monitor` `local-container` snapshot of the gateway's own container on every reconcile tick (FR-058) | Creating webhooks in Gitea (`gitea.webhook.create` stays `human-only`); re-implementing R1's layers |
| merge-policy-gate | `merge_decision.py` at `guarded-autonomous` (13 evidence gates, 6 caps, `AUTO_MERGE` for low risk only, decision records at every level); `merge_plan.py --apply\|--evaluate\|--evaluate-open\|--cancel\|--cancel-if-head-differs\|--cancel-all\|--sweep-expired\|--reevaluate-open`; `branch_audit.py` requires BP-09 at this level; new `autonomy_scorecard.py` and `autonomy_guard.py detect\|evaluate\|demote\|audit-merge` | Auto-merge of medium, high, or critical risk; auto-promotion; any merge of the factory repository |
| session-checkpoint | `checkpoint.py resume-plan --recovery` (checks `pr_state`, `descendant_of_checkpoint`, `commit_attribution`, `push_receipts_match`), consumed by lease recovery | — |
| twelve-factor-audit | No change (re-validated) | — |
| skill-forge | No change (re-validated) | — |
| speckit-development | Handoff at `guarded-autonomous`: records the merge handoff in `delivery-record.v1` and sets `next_action: merge_gate.event_loop` only when the (capped) decision is `AUTO_MERGE`, otherwise a human merge (FR-051); it never calls the merge endpoint. `review_request.py` carries the digests of every run in the live streak and keeps SPEC-105's reviewer self-report instruction (FR-057) | Merging its own PR |
| run-monitor (skill 14, SPEC-014) | **No script change** (re-vendored and re-validated). Each R3 live run takes one `run-health.v1` snapshot after each skill (14 per run) with SPEC-105's limits deciding degraded and one advisory assessment, and the R3 reviewer runs it in its own container (FR-057). The webhook gateway runs inside one of the person's Rancher Desktop local containers; on every reconcile tick `normalize.py serve` runs `snapshot.py --target local-container` there (SPEC-105's target kind, delivered in R1), which reads only that container's own cgroup figures, disk free, and process count (FR-058; answers recorded 2026-10-22, Q-13 resolved) | Reading anything outside the gateway's container or a Docker or containerd socket; letting a health report change a gateway decision; changing `monitor-limits.json` (the person approves any change) |
| Policy machinery | `SUPPORTED_MAX_LEVEL = "guarded-autonomous"`; catalog 1.1.0 (36 actions: `autonomy.demote`, `gitea.pr.merge_schedule.cancel` added); promotion verification; demotion latch; `_skillkit.authority` | Lowering any existing minimum level |
| Lab | Double: merge-when-checks-succeed semantics, dismissal, close, signed webhook emission with faults; `smoke gitea --stage merge`; `afv run`; `autonomy scorecard\|promote-check\|status`; `signoff create --subject autonomy-level-change`; containment `--level guarded-autonomous [--demoted]`; validator rules `eval-inventory-r3` and `afv-inventory`; `release check` live gates read from SPEC-105 outputs (`score --strict` per skill, `score --catalog`, `benchmark-run.v1`, `benchmark-streak.v1`); `gates.json` | Changing scoring semantics (SPEC-104 and SPEC-105 own them); count-based live metrics; lowering any SPEC-105 floor gate; editing criteria files, `monitor-limits.json`, or `prices.json` |

## 6. Risks (summary; synthesis.md §5 has detail and mitigations)

| ID | Risk | Likelihood | Impact | Mitigation in this release |
|---|---|---|---|---|
| RK-1 | Gitea 28.x merge-when-checks-succeed semantics differ from the double (field names, head binding, behaviour on a new push) | Medium | High | Swagger verification (T003); head-binding cancel on every new head; live merge smoke stage before the first live auto-merge (RT-02) |
| RK-2 | A scheduled merge outlives the evidence it was decided on | Medium | High | Cancel on regress events, 30-minute schedule TTL, `head_commit_id`, BP-06 and BP-07 required |
| RK-3 | An agent deletes the local demotion latch | Medium | High | The merge gate re-checks the Gitea mirror on every decision; the guard re-derives demotion from durable incidents |
| RK-4 | A human promotes without real evidence | Low | High | Policy code verifies the signed scorecard's criteria against code constants; P-1 needs ≥ 30 calibration PRs |
| RK-5 | Escaped defects are only detected when someone labels them | High | Medium | Revert detection is automatic; labelling convention documented (Q-10); unattributed defects also demote |
| RK-10 | The network allowlist or the keys are not ready, so R3's live gates stay `not_run` and R3 cannot merge; no project can be promoted | Medium | High | Offline work, convergence, and review preparation continue; the PR waits for the live gates; nothing is replayed or fabricated in place of a live run (intake D2, A8) |
| RK-11 | The R3 PR changes the gates, the policy clamp, and the gateway (critical risk) | Certain | High | Human merge mandatory; self-classification gate G-OFF-26; reviewer checklist |
| RK-16 | Ollama Cloud or TypeSafe outages, persistent rate limits, or a degraded run during the 3-run streak | Medium | Medium | SPEC-105: an outage marks cases `errored` and a crossed `monitor-limits.json` limit marks the run degraded; neither run counts, the next counting run continues the streak; a pass-then-fail case or a case edit restarts it; cost is reported from `prices.json`, never capped |

## 7. Milestones

| ID | Milestone | Contents (tasks.md phases) | Done when |
|---|---|---|---|
| M0 | Entry | Phase 1 (T001–T016, T151) | E-1..E-6 recorded (R2 `APPROVE` with its live gates passed; branch stacked on `release/r2-agent-implementation`); R2, R1, and SPEC-105 alignment (X-1..X-15) and Gitea facts recorded |
| M1 | Foundation | Phase 2 (T017–T059, T154): contracts, policy clamp, promotion, latch, authority, autonomy and merge-policy modules, client rows, double semantics and webhooks, leases and recovery, gateway and event loop, git helpers, lab commands including the SPEC-105 live-gate evaluation, fixtures | Phase 2 tests green; `sync --check` clean |
| M2 | MVP: guarded auto-merge on the double | Phase 3 (US1) | `test_r3_us1_auto_merge.py` green |
| M3 | Gateway | Phase 4 (US2) | `test_r3_us2_gateway.py` green |
| M4 | Ordering and event-driven board | Phase 5 (US3) | `test_r3_us3_ordering.py` green (all permutations) |
| M5 | Demotion and promotion | Phase 6 (US4) | `test_r3_us4_demotion.py` green |
| M6 | Recovery, dispatch, stale heads | Phases 7–9 (US5–US7) | US5–US7 integration tests green |
| M7 | Verification suites | Phase 10 (US8) | `afv-report.v1` meets minimums; soak 0 violations |
| M8 | Release candidate | Phase 11 (T129–T132, T155) and Phase 12 up to T141 | every offline merge-stage gate passes; converge 0 findings |
| M-LIVE | Live gates | T142 (3 consecutive counting SPEC-105 runs) when keys and network exist; T143 when a Gitea sandbox is configured | G-LIVE-01..08 pass; required before the PR body and the review (T144), because R3 merges only when its live gates pass. RT-02 unlocks live auto-merge per host |
| M9 | PR, review, merge | T144–T150, T152, T153 | X-1..X-4 |
| M-PROMO | First project promotion (human; outside tasks.md) | runbook `skill-lab/docs/runbooks/autonomy-promotion.md` | P-1..P-8 eligible, signed, human-merged; `skill-lab autonomy status` shows `guarded-autonomous` |

## 8. Delivery steps for this release

The roadmap's eight steps, made concrete for R3. Steps 5–8 follow SPEC-201's `skill-lab/docs/runbooks/release-delivery.md`.

| Step | What happens in R3 | Artifact | Who |
|---|---|---|---|
| 1 Plan | This document | `release-plan.md` | Lead (planning session) |
| 2 Synthesize | Findings F-1..F-45, decisions D-1..D-32, cross-release findings X-1..X-15, verifications V-1..V-11, risks, questions Q-1..Q-14 (all resolved by the person's answers and the answers recorded 2026-10-22, except Q-2 (a), (c), (d), (e)) | `synthesis.md` | Lead |
| 3 Tasks as spec | FRs, SCs, gates, contracts, autonomy policy; dependency-ordered tasks | `spec.md`, `tasks.md`, `traceability.json` | Lead |
| 4 Implementation plan | Technical context, constitution check, exact files, decision function, routing table, recovery rules, test and benchmark strategy, rollout and rollback | `plan.md` | Lead |
| 5 Execute | Work happens in a checkout of `Cazador0/skill-factory` on branch `release/r3-guarded-autonomous`, created from the `release/r2-agent-implementation` head (E-2; stacked PRs). `/speckit-development` (the R2 build, running at `shadow` against the factory repository) drives `tasks.md` in dependency order: one task per step, marked `[x]` only with passing `check-run` evidence, then converge until 0 findings. Evidence goes to `skill-lab/specs/203-release-guarded-autonomous/evidence/`. The new guarded capabilities are exercised only against the Gitea test double, plus a sandbox Gitea repository when one is configured, **never** against the factory repository | Code, tests, evals, evidence | PSE sessions, orchestrated |
| 6 Pull request | `pr_body.py` renders `evidence/pr-body.md`; `export-repo` builds and checks the standalone tree; `delivery_plan.py` with forge `github` writes `evidence/pr-request.json`. The orchestrator, not a skill (SPEC-202 D-4), pushes `release/r3-guarded-autonomous` and opens a PR with base `release/r2-agent-implementation` (stacked), then posts the `skill-lab report` comment of each streak run and the streak record on the PR (SPEC-105 FR-018; T153). CI on the factory runs only the offline tiers on every PR; live tiers run only when started manually | GitHub PR | Orchestrator |
| 7 Review | `review_request.py` writes `review-request.v1` (forge `github`, round 1) carrying the digests of the 3 streak runs and of the `benchmark-streak.v1` record. The orchestrator creates a separate Claude Code cloud session with `create_session` on the release branch; its environment holds no Ollama or TypeSafe keys. That session loads `.claude/skills/review-verifier`, rebuilds the requirements matrix from this `spec.md`, re-runs the offline merge-stage gates, re-computes the live gates offline from the committed runs (recorded evidence only; it never re-runs a live case and says so in its verdict), runs merge-policy-gate on the diff (expects `critical`, `HUMAN_APPROVAL_REQUIRED`, `FACTORY_REPOSITORY`), posts a `review-verdict.v1` comment with R1's marker, and posts its own `run-health.v1` snapshot as a separate comment marked `<!-- skill-lab:run-health:v1 request_id=<id> -->` (SPEC-105 FR-023). If no cloud session can be created, R1's `review_local.py` (`claude -p --json-schema`) is the fallback, and the verdict records `mode: cli-fallback`. `review_collect.py` accepts the verdict. At most 3 rounds; after round 3 the person decides | PR comments | Independent reviewer |
| 8 Merge | `release check --stage post-review` passes (CI green, verdict collected), and the merge-stage report passes every offline and live gate on the reviewed head. Once a human has merged R2 (E-7), the orchestrator retargets the base to `main` (`gh pr edit --base main`); if the diff changed after the reviewed head, on retargeting or otherwise, step 7 runs again (a change to any `SKILL.md` or eval case also restarts the live streak, T142). A human merges. No agent and no R3 code path merges the factory repository | Merged PR | Human |

## 9. Release branch and naming

| Item | Value | Note |
|---|---|---|
| Release branch | `release/r3-guarded-autonomous` | Created from the `release/r2-agent-implementation` head once R2 has `APPROVE` and its live gates passed (E-1..E-4) |
| PR base | `release/r2-agent-implementation` (stacked); `main` after R2 merges | Intake A4; the correction recorded 2026-10-22 (SPEC-200 open-questions.md; synthesis D-32). Merges in order R1 → R2 → R3, each by a human |
| Agent branches produced by the skills | `agent/pse/<issue>-<slug>` in the Gitea target repository; rebased in place by the leased PSE | Report: "Recommended branch format" |
| Evidence folder | `skill-lab/specs/203-release-guarded-autonomous/evidence/` | Created during step 5; evidence produced at or after the reviewed head stays out of the branch (SPEC-201 D-17) |
| Live run results | `skill-lab/benchmarks/runs/<run_id>/` (committed: results, run summary, run log, 14 health reports, PR comment) | SPEC-105 FR-015 and SPEC-201 refinement set 2: R3 evidence points at each run by digest (`evidence/live-runs.json`) instead of copying it |
| Gate definitions | `skill-lab/specs/203-release-guarded-autonomous/gates.json` | `release-gates.v1` (SPEC-201) |
| ADR numbers | ADR-0301..ADR-0309 | R1 uses 0101–0109, R2 0201–0207 |
| Catalog version | `1.1.0` (36 actions) | Adds 2 restrictive or clean-up actions; lowers nothing |
