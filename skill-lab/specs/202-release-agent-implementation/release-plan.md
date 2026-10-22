# Release plan: R2 Agent implementation

**Spec ID**: SPEC-202 | **Release**: R2 | **Autonomy level shipped**: `agent-implementation`

**Created**: 2026-10-22 | **Status**: Draft (planning, delivery step 1); aligned on 2026-10-22 with SPEC-105 and the person's
SPEC-201 refinement decisions ([synthesis.md](synthesis.md) §8)

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
- **L1 local inference.** R2 ships the mechanism: local Ollama Zed profiles stay gated until a measured gate passes.
  The entry is SPEC-105's `benchmark-streak.v1` with `local_unlock_evidence: true` for the cloud model (3 consecutive
  counting runs on the same model and suite digest), plus the person's recorded sign-off. Then the same floor gates
  must pass on `--runtime ollama-local`. Every Zed profile keeps provider `ollama` at `http://localhost:11434`: the local
  Ollama app, signed in to ollama.com, serves the cloud models in R1. L1 switches the profile model ids to local models
  on that same provider.
- **Run monitoring on local runs.** `run-monitor` (skill 14, SPEC-014) gets one option, `snapshot.py --host-metrics off`,
  which bench passes on `--runtime ollama-local` runs. Those run on the person's machine, and the person did not choose
  to monitor it (intake Q19); whether to monitor it stays the person's decision (Q-10).

Everything runs offline against the Gitea 28.x test double first. Live Gitea writes start only when `GITEA_URL` and
`GITEA_TOKEN` are present and the smoke test has passed. The live benchmark gates need `OLLAMA_API_KEY` and
`TYPESAFE_API_KEY` (or `JEV_API_KEY`), and no live result is ever fabricated. The R2 PR merges only after its live gates
pass on one fully passing counting live run of the R2 suite. There is no "merged, live-pending" state (the person's
decision: intake Q1 and Q15, SPEC-201 refinement ledger row 5). R2 starts only after R1 is merged, with R1's independent
`APPROVE` and its live gates passed, and R3 starts only after R2 is merged (the person's decision, 2026-10-22).

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
| RG-7 | Local inference L1 ships behind its measured gate | Gate evaluator 100 % correct on a fixture matrix of ≥ 15 rows; its cloud entry is SPEC-105's `local_unlock_evidence`; local profiles installed 0 times without an `ENABLED` `inference-gate.v1` matching the current suite digest and model; 0 host figures recorded on the person's machine during local runs (unless the person decides otherwise, Q-10) |
| RG-8 | The live gates decide the merge, without fabrication | G-LIVE-01..G-LIVE-07 (the floor gates per skill and catalog-wide, guardrail cases at 100 %, a counting run on the head's suite) pass on one fully passing counting live run of the R2 suite before the merge. Without keys or network they are `not_run`, which never passes and keeps the PR open. When Gitea is configured, the live Gitea smoke test passes all 4 stages with full cleanup |
| RG-9 | Portable quality bar holds for all 14 skills | `skill-lab validate` 0 errors (zed, claude, codex); `sync --check` 0 drift; 100 % unit tests (Python 3.9 and current) and ≥ 116 deterministic cases passing; every skill meets SPEC-105's eval minimums (≥ 4 deterministic, ≥ 5 agentic with ≥ 1 guardrail, ≥ 10 trigger with ≥ 2 expecting no skill); 0 inventory violations; catalog ≤ 51,200 bytes |
| RG-10 | The release itself follows the delivery process | The R2 PR has an `APPROVE` `review-verdict.v1` from a session other than every authoring session, in ≤ 3 rounds (after that, the person decides), from a reviewer that used recorded evidence only and posted its own `run-health.v1` report; merge-policy-gate classifies the R2 diff `critical` → `HUMAN_APPROVAL_REQUIRED` |

## 3. Entry criteria

R2 step 5 (execute) does not start until all of these hold. T001 records each one, with evidence, in
`skill-lab/specs/202-release-agent-implementation/evidence/entry-check.json`.

| ID | Criterion | Evidence |
|---|---|---|
| E-1 | The R1 PR (SPEC-201) has an `APPROVE` `review-verdict.v1` from the independent reviewer session, accepted by `review_collect.py` (roadmap: "R2's entry is R1 merged, with an `APPROVE` verdict from the independent reviewer and R1's live gates passed") | PR comment URL, request ID, verdict digest (copied from R1's post-review evidence) |
| E-2 | A human merged the R1 PR into `main` of `Cazador0/skill-factory`, and the merge contains the reviewed head (the person's decision, 2026-10-22: "R2 entry = R1 merged with APPROVE and live gates passed") | GitHub PR state, merge commit SHA, `git merge-base --is-ancestor <reviewed head> <merge commit>` |
| E-3 | R1's `release check --spec SPEC-201 --stage merge` reports every gate `pass` on that head. R1's merge stage includes its live gate: one fully passing counting live run (SPEC-105 FR-009) | `release-gate-report.v1` |
| E-4 | R1 deliverables R2 builds on exist under the names SPEC-201 gives them: `_skillkit.policy` (catalog of 34 actions, `SUPPORTED_MAX_LEVEL`), `_skillkit.gitea` (`GiteaClient.send`), `_skillkit.gitrepo`, `_skillkit.checks` (`check-run.v1`), the read-only Gitea double, the containment harness, `release check`, `export-repo`, and the scripts listed in §5. Also SPEC-105's harness, delivered inside R1: the floor gates in `skill-lab/benchmarks/criteria/_defaults.json` with `score --catalog`, the Jev re-ask, outage classification, `skill-lab streak` (`benchmark-streak.v1`), `skill-lab report`, the run log, `run-monitor` `snapshot` (`run-health.v1`, skill 14), runs committed under `skill-lab/benchmarks/runs/`, `prices.json`, and `monitor-limits.json` | T005 writes `evidence/r1-alignment.json` |
| E-5 | This folder's six artifacts exist, and `lead-architect` readiness on this spec reports no failing check | `spec-readiness.v1` envelope (T006) |

All five hold before step 5 starts. R2 no longer overlaps R1's human merge, so the R2 branch starts from `main` at the R1
merge commit, and the R2 PR targets `main` from the start. The earlier stacked base (`release/r1-shadow`) is no longer
needed (synthesis.md §8, row 4).

## 4. Exit criteria

R2 has one exit state, as R1 now has. The live benchmark gates are merge-stage gates, so the PR merges only when they
pass, and "not run never counts as pass" (CONVENTIONS §9, ADR-0010) keeps the PR open until a counting live run exists.
This is the person's decision for R1 (intake Q1 and Q15; SPEC-201 refinement ledger row 5), applied to every release
on 2026-10-22. Wherever SPEC-200 or SPEC-203 says "R2 complete", it means R2 merged.

**R2 merged** (end of step 8):

- X-1: `release check --spec SPEC-202 --stage merge` reports every gate G-OFF-01..G-OFF-23 and G-LIVE-01..G-LIVE-07
  `pass`. The live gates are computed from one fully passing counting live run of the R2 suite, committed under
  `skill-lab/benchmarks/runs/<run_id>/` and named by run id and digest in `evidence/live-runs.json`, which
  `skill-lab release record-run` writes (FR-046, FR-047).
- X-2: converge reports 0 findings against this spec, plan, and tasks (G-OFF-23).
- X-3: a separate Claude Code cloud session posted an `APPROVE` `review-verdict.v1` on the R2 PR, and `review_collect.py`
  accepted it (G-POST-02). The reviewer used recorded evidence only and held no Ollama or TypeSafe keys, and it posted
  its own `run-health.v1` report as a separate marked PR comment (SPEC-105 FR-023, R-12).
- X-4: CI on the PR head is green (G-POST-01; offline CI on every PR, live tiers only when started manually), and a
  human merged R2.
- X-5: there is no "merged, live-pending" state. A live gate that is `not_run` or `fail` keeps the PR open. R3 starts
  only after R2 is merged (the person's decision, 2026-10-22; D-20).

**Outside the exit criteria**:

- X-6: L1 is not an exit criterion. It is milestone M-L1 on the inference track, which by default runs in parallel
  with R3 (roadmap sequencing diagram; Q-5 is still open). Its gate record must be honest: `NOT_ENABLED` with reasons is a valid record.
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
| gitea-event-normalizer | No change. R2 polls; it does not consume events. R1 already ships all four replay-defence layers: body-SHA-256 dedupe, a freshness guard on the signed `updated_at` and head SHA, events treated as hints that are re-read before any decision, and secret hygiene (`GITEA_WEBHOOK_SECRET_PREVIOUS` accepted for 7 days; body digests kept 90 days). R2 leaves them unchanged | Webhook gateway `serve` (R3, built on R1's four layers) |
| merge-policy-gate | Cap stays at `HUMAN_APPROVAL_REQUIRED` with `uncapped_decision`; new `branch_audit.py` (BP-01..BP-12); `merge_decision.py` consumes `review-post.v1` and `branch-protection-audit.v1` | `AUTO_MERGE` for low risk; `merge_plan.py --apply` (R3) |
| session-checkpoint | `checkpoint.py publish --apply` (marked issue comment) | Lease-recovery consumption (R3) |
| twelve-factor-audit | No change | — |
| skill-forge | No change | — |
| run-monitor (skill 14, SPEC-014) | One option: `snapshot.py --host-metrics off` leaves the container figures `null` with note `HOST_METRICS_OFF` and still computes the API and session figures. Bench passes it on `--runtime ollama-local` runs, which run on the person's machine, because the person did not choose to monitor that machine (intake Q19; open question Q-10). The advisory assessment on a local run uses the run's own runtime and model. Limits and `monitor-limits.json` unchanged (D-27) | Monitoring the person's machine (only if the person chooses it, Q-10); changing the limits (the person's approval only, SPEC-105) |
| speckit-development | End to end: new `delivery_record.py` (resumable step state); `delivery_plan.py --apply --step worktree\|branch\|commit\|push\|pr\|review-request\|review-session` (shared executor; review-request asks the Review login on Gitea, review-session writes the dispatch); R1's `dev_state.py`, `converge.py` (≤ 3 passes), `pr_body.py`, `review_local.py`, and `review_collect.py` unchanged | Hand-off to auto-merge (R3) |
| Policy machinery | `SUPPORTED_MAX_LEVEL` raised; base-branch verification; containment at `agent-implementation` | Promotion and demotion by metrics (R3) |
| Lab | Write endpoints in the test double (engine moved to `_skillkit.gitea_memory`); live Gitea smoke test; L1 gate evaluator over SPEC-105's `lab.streak`; `signoff`; `doctor --runtime ollama-local`; installer `--inference local` gate; `ollama-local` parity with SPEC-105's run fields and `--host-metrics off`; live gates read from the committed run (FR-047); validator rule `eval-inventory-r2`; `gates.json` | Changing scoring, streak, or monitoring semantics (SPEC-104 and SPEC-105 own them) |

## 6. Risks (summary; synthesis.md §5 has detail and mitigations)

| ID | Risk | Likelihood | Impact | Mitigation in this release |
|---|---|---|---|---|
| RK-1 | Gitea 28.x endpoint or field drift from the double | Medium | High | Swagger verification (T003), endpoint table, live smoke test before the first live write |
| RK-2 | Lost update between read and write | Medium | Medium | Observed-state digest plus re-read after write; leases serialize writers |
| RK-3 | The lease store is single-host | High (by design) | Medium | Declared limit (ADR-0202); mirror conflict detection |
| RK-4 | An agent bypasses scripts with raw `git push` or HTTP | Medium | High | Runtime deny patterns (guardrail); branch protection plus least-privilege tokens are the boundary |
| RK-5 | The R2 PR itself changes the policy clamp, permission configs, and the review gates (critical risk) | Certain | High | Human merge is mandatory; the reviewer checklist names those paths; self-classification must say `critical` |
| RK-6 | A local model on a < 24 GB GPU cannot follow the procedures at 32k context | Medium | Medium | Measured L1 gate; cloud fallback stays installed |
| RK-7 | The network allowlist or the keys are not ready, so the live gates stay `not_run` and the R2 PR cannot merge | Medium | Medium | Execution, offline gates, and the PR proceed; only the merge waits (the person's decision). An outage or degraded run does not count and is re-run |
| RK-8 | CLI-fallback review gives weaker independence | Medium | Medium | Mode recorded in the verdict (R1 contract); posting needs the Review identity |
| RK-13 | A missing `origin/<base>` ref puts projects at `shadow` | Medium | Low | Intended fail-closed behaviour; runbook says `git fetch origin <base>` |
| RK-14 | R2's added eval cases change the suite digest, so R1's streak does not carry over to the R2 suite | Certain | Low | Expected (SPEC-105 FR-010): the R2 gate run is the first run of the R2-suite streak |
| RK-15 | With host metrics off, memory or disk trouble on the person's machine during local runs goes undetected | Medium | Low | API error-rate and no-progress limits still mark the run degraded; Q-10 lets the person choose host monitoring |

## 7. Milestones

| ID | Milestone | Contents (tasks.md phases) | Done when |
|---|---|---|---|
| M0 | Entry | Phase 1 (T001–T006) | E-1..E-5 recorded; R1 alignment recorded |
| M1 | Foundation for writes | Phase 2: contracts, clamp plus base-branch check, Gitea client, mutation ledger, plan applier, leases, git write helpers, delivery executor, double | Phase 2 tests green; `sync --check` clean |
| M2 | MVP: PSE PR on the double | Phase 3 (US1) | `test_r2_us1_pse_delivery.py` green |
| M3 | Review and merge gate | Phase 4 (US2) | `test_r2_us2_review_merge.py` green |
| M4 | Lead drives the board | Phase 5 (US3) | `test_r2_us3_lead_board.py` green |
| M5 | End-to-end delivery | Phase 6 (US4) | Golden end-to-end and resume tests green |
| M6 | L1 mechanism, local monitoring, and live smoke test | Phases 7 and 8 (US5, US6), including T143–T144 | Gate matrix, installer, host-metrics-off, and smoke-against-double tests green |
| M7 | Release candidate | Phase 9: ADRs, CONVENTIONS, configs, validator rule, gates, live-gate evaluation, catalog, traceability, offline gates, converge | Every G-OFF gate passes (T134); converge has 0 findings |
| M-LIVE | Live gates | T135 and T145 (required for the merge; they need keys and network); T136 when Gitea is configured | G-LIVE-01..G-LIVE-07 `pass` (part of X-1); RT-01 unlocks live writes |
| M8 | PR, review, merge | Phase 9 tail (T138, T139, T146, T140–T142) | X-1..X-5 |
| M-L1 | Local inference enabled | §10 procedure (live, human; outside tasks.md) | `inference-gate.v1` `ENABLED`, and the person applies the installer |

## 8. Delivery steps for this release

The roadmap's eight steps, made concrete for R2. Steps 5–8 follow SPEC-201's `skill-lab/docs/runbooks/release-delivery.md`.

| Step | What happens in R2 | Artifact | Who |
|---|---|---|---|
| 1 Plan | This document | `release-plan.md` | Lead (planning session) |
| 2 Synthesize | Findings F-1..F-45, decisions D-1..D-29, verifications V-1..V-7, risks, open questions Q-1..Q-10 (Q-3, Q-7, Q-8 resolved), alignment ledger | `synthesis.md` | Lead |
| 3 Tasks as spec | FRs, SCs, gates, contracts, autonomy policy; dependency-ordered tasks | `spec.md`, `tasks.md`, `traceability.json` | Lead |
| 4 Implementation plan | Technical context, constitution check, exact files, endpoint table, test and benchmark strategy, rollout and rollback | `plan.md` | Lead |
| 5 Execute | Work happens in a checkout of `Cazador0/skill-factory` on branch `release/r2-agent-implementation`, created from `main` at the R1 merge commit (E-2). `/speckit-development` drives `tasks.md` in dependency order. It is the R1 build, running at `shadow` against the factory repository: one task per step, marked `[x]` only with passing `check-run` evidence, and converge until 0 findings. Evidence goes to `skill-lab/specs/202-release-agent-implementation/evidence/`. The live gate run (T135) is committed under `skill-lab/benchmarks/runs/<run_id>/` and named by digest in `evidence/live-runs.json` (`skill-lab release record-run`); T145 then evaluates every merge-stage gate, live ones included. CI runs only the offline gates on every PR; live benchmarks run only when started manually. The new R2 write capabilities are exercised only against the Gitea test double, plus a sandbox Gitea repository when one is configured, never against the factory repository | Code, tests, evals, evidence | PSE sessions, orchestrated |
| 6 Pull request | `pr_body.py` renders `evidence/pr-body.md`, and `export-repo` builds and checks the standalone tree. `delivery_plan.py --step pr --forge github` (no `--apply`; the factory repository runs at `shadow`) writes `evidence/pr-request.json`. The orchestrator, not a skill (D-4), pushes `release/r2-agent-implementation` and opens a PR with base `main`. It then posts the live scores rendered by `skill-lab report --run <run>` as a PR comment (SPEC-105 FR-018; T146) | GitHub PR | Orchestrator |
| 7 Review | `review_request.py` writes `review-request.v1` (forge `github`, round 1). The orchestrator creates a separate Claude Code cloud session with `create_session` on the release branch. The review request carries the live run's digest. That session holds no Ollama or TypeSafe keys. It loads `.claude/skills/review-verifier`, rebuilds the requirements matrix from this `spec.md`, re-runs `release check --stage merge` (whose live gates read only the committed run, FR-047, so it re-runs no live case and says so in its verdict), runs merge-policy-gate on the diff (expects `critical`), and posts a `review-verdict.v1` comment with R1's marker. It also runs `run-monitor` `snapshot --target reviewer-session` in its own container and posts the `run-health.v1` report as a separate comment marked `<!-- skill-lab:run-health:v1 request_id=<id> -->` (SPEC-105 FR-023, R-12). If no cloud session can be created, R1's `review_local.py` (`claude -p --json-schema`) is the fallback, and the verdict records `mode: cli-fallback`. `review_collect.py` accepts the verdict. At most 3 rounds; after that the person decides | PR comments | Independent reviewer |
| 8 Merge | `release check --stage post-review` passes (CI green, verdict collected). If the diff changed after the reviewed head, step 7 runs again. A fix that changes any SKILL.md or eval case changes the suite digest, so a new counting live run of the changed suite is needed before the next review round. A human merges | Merged PR | Human |

## 9. Release branch and naming

| Item | Value | Note |
|---|---|---|
| Release branch | `release/r2-agent-implementation` | Created from `main` at the R1 merge commit (E-2) |
| PR base | `main` | R2 starts only after R1 is merged (the person's decision, 2026-10-22), so the earlier stacked base `release/r1-shadow` is not used |
| PSE branches produced by the skills | `agent/pse/<issue>-<slug>` in the Gitea target repository | Report: "Recommended branch format" |
| Evidence folder | `skill-lab/specs/202-release-agent-implementation/evidence/` | Created during step 5. Evidence produced at or after the reviewed head (review request, verdict, post-review gate report) stays out of the branch and lives in the PR thread (SPEC-201 D-17) |
| Gate definitions | `skill-lab/specs/202-release-agent-implementation/gates.json` | `release-gates.v1` (SPEC-201) |
| Live run results | `skill-lab/benchmarks/runs/<run_id>/` (committed, SPEC-105 FR-015) | `evidence/live-runs.json` names each gate run by run id and digest, never a copy (SPEC-201 refinement, set 2; FR-046) |
| ADR numbers | ADR-0201..ADR-0207 used; 0201–0209 reserved for R2 | R1 uses 0101–0109; R3 is expected to use 0301–0309 |

## 10. Milestone M-L1 procedure (local inference, outside the task graph)

M-L1 runs after R2's mechanism exists (Phase 7) and live cloud runs are possible (T135). By default it runs in parallel
with R3 and never blocks the R2 merge or R3 (X-6; Q-5 is still open). It sits outside `tasks.md`: under SPEC-201's wave rule, a story phase that waits on
Polish would form a cycle, and its artefacts cannot exist at merge time. Every command records evidence, and none
fabricates a result. The streak rules are SPEC-105's (FR-010..FR-012), so this procedure adds no second definition of
"reliable".

| Step | Who | Command | Output | Passes when |
|---|---|---|---|---|
| L1-a | orchestrator | `skill-lab bench --tier agentic,trigger --runtime ollama-cloud --model <m> --jev live` (SPEC-105 FR-001), then `skill-lab score --strict` per skill and `--catalog`, `skill-lab streak`, and a commit of the run, repeated on the same suite digest with the model from `skill-lab/config/zed/cloud-models.json`. R2's gate run (T135) is the first of them | `skill-lab/benchmarks/runs/<run_id>/` (×3 or more) and `benchmark-streak.v1` | `local_unlock_evidence: true`: 3 consecutive counting runs (live, complete, not degraded, no `errored` case) on the same model and suite digest, each passing every per-skill and catalog floor gate and every guardrail case, with no case that passed and then failed (D-17) |
| L1-b | orchestrator | `skill-lab gate l1 --stage cloud --model <m>` | `skill-lab/benchmarks/gates/l1-cloud-<m>.json` | the streak, recomputed with SPEC-105's `lab.streak` from the committed runs, has `local_unlock_evidence: true` for `<m>` on the current suite digest (gate L1-01) |
| L1-c | **person** | `skill-lab signoff create --subject inference-enablement --model <m>` (interactive; reviews the deterministic sample set) | `skill-lab/benchmarks/signoff/<date>-inference-enablement-<m>.json` | `decision: approve`, signer `Cazador0` (Q-7), bound to the streak's run ids and digests (gate L1-02); agents never create this file |
| L1-d | person, or the orchestrator on the person's machine | `skill-lab doctor --runtime ollama-local --model <local-m>` | doctor envelope | reachable, model pulled, context ≥ 32768, GPU residency reported (Q-1 picks the model) |
| L1-e | orchestrator on the person's machine | `skill-lab bench --tier agentic,trigger --runtime ollama-local --model <local-m> --jev live` in cloud-parity mode, then `score`, `streak`, and a commit of the run, ×3 on the same suite digest. Bench passes `--host-metrics off` to `run-monitor`, so the person's machine is not monitored (intake Q19; Q-10) | `skill-lab/benchmarks/runs/<run_id>/` | 3 consecutive counting local runs, each passing the same floor gates (gate L1-03; 3 is D-17's default, Q-4) |
| L1-f | orchestrator | `skill-lab gate l1 --model <local-m>` | `skill-lab/benchmarks/gates/l1-<local-m>.json` | `decision: ENABLED` |
| L1-g | **person** | `skill-lab install --runtime zed --inference local` | the `(local)` profiles, with local model ids on the same `ollama` provider at `http://localhost:11434`, installed next to the cloud profiles | the installer finds the matching `ENABLED` record; `install --check` reports no drift |

Demotion: a later counting run that fails a gate, a case that passed and then failed, or a suite or model change flips
the next `gate l1` evaluation to `NOT_ENABLED`. A run that does not count (replay, partial, outage, degraded) neither
extends nor breaks a streak, so it never demotes. `install --check` then reports drift, and the runbook says to switch
the threads back to the cloud profiles.

