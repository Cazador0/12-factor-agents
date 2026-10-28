# Release plan: R1 Shadow mode

**Spec ID**: SPEC-201 | **Release**: R1 | **Autonomy level shipped**: `shadow`

**Created**: 2026-10-22 | **Status**: Draft (planning, delivery step 1; refined with the person 2026-10-22, see spec.md §Clarifications)

**Parent**: [SPEC-200 release roadmap](../200-release-roadmap/spec.md) | **Next**: [SPEC-202 R2 Agent implementation](../202-release-agent-implementation/release-plan.md)

**Delivers inside R1**: [SPEC-105 Jev live benchmarking](../105-jev-live-benchmarking/spec.md) and the 14th skill `run-monitor` (SPEC-014)

**Companion documents**: [synthesis.md](synthesis.md) (step 2), [spec.md](spec.md) and [tasks.md](tasks.md) (step 3),
[plan.md](plan.md) (step 4), [traceability.json](traceability.json)

## 1. Scope in one paragraph

R1 ships all 14 portable skills at their shadow-mode capability for Zed + Ollama Cloud first, then Claude
Code and Codex. "Shadow" is the report's first autonomy level: "Lead, PSE, and Review analyze real work and
produce plans/recommendations; humans perform consequential mutations" (report §Progressive autonomy). R1
also owns the machinery every later release builds on. That is the `autonomy-policy.v1` file
`.skill-policy.json`, the 34-entry action catalog, and `_skillkit.policy`, which loads fail-safe to `shadow`,
clamps to the release's maximum level, and refuses with exit 4. It also owns the read-only Gitea client and
test double, the four webhook defense layers (body-digest dedupe, freshness guard, events as hints, secret
hygiene), the cloud-first Zed configuration with a disabled local profile, the export of the working tree into
the standalone repository `Cazador0/skill-factory`, and the independent-review loop (`review-request.v1` →
separate Claude Code cloud session holding no live keys → `review-verdict.v1` PR comment plus the reviewer's own
`run-health.v1` comment → parse). R1 delivers SPEC-105 (Jev live benchmarking) and its `run-monitor` skill
(SPEC-014, family `control-plane`, secondary family `meta`), because the first live run is R1's release gate: R1
merges only after one fully passing, counting live run on Ollama Cloud with live Jev grading, measured against
the SPEC-104 defaults as a floor per skill and catalog-wide (intake Q1, Q15; spec.md §Clarifications rows 1, 5,
11). R1 is delivered with `/speckit-development` (SPEC-013), which takes over execution of this release's
`tasks.md` once it passes its own acceptance test (the self-hosting switch-over, task T054).

## 2. Release goals

Each goal is measurable. `spec.md` §Release goals maps every goal to FRs, SCs, and gates.

| ID | Goal | Measure (threshold) |
|---|---|---|
| RG-1 | Shadow containment is enforced by policy code, not by prompts | Containment suite: 0 consequential effects (non-GET requests to the double, git ref changes, working-tree writes outside `--out`/`--state-dir`) across 100 % of (skill, action) pairs above `shadow`; ≥ 40 hostile policy files all yield `shadow` |
| RG-2 | 14 skills ship at R1 capability on Zed, Claude Code, and Codex | `validate` 0 errors × 3 runtimes; unit tests 100 % on Python 3.9 and current; deterministic cases 100 % (≥ 56 plus refusal cases); eval inventory 0 violations (≥ 4 deterministic, ≥ 5 agentic with ≥ 1 `guardrail`, ≥ 10 trigger with ≥ 2 `expect_skill: null` per skill); no per-skill criteria file shipped (scoring uses `_defaults.json`, the floor) and 0 below the floor |
| RG-3 | Every requirement is traced | SPEC-001..014, SPEC-105, and SPEC-201: 0 FRs without an existing `verified_by`; 0 `planned: true` at merge |
| RG-4 | Inference is cloud-first, and R1 merges only after one fully passing, counting live run | Zed config rules 0 errors (3 of 3 profiles on one Ollama Cloud model through the local Ollama app signed in to ollama.com, no local model in the template, local file present but not installable); on the newest recorded live gate run matching the tree: agentic pass rate ≥ 0.80, trigger accuracy ≥ 0.90, agentic schema-valid rate ≥ 0.95, and Jev uncertain rate after one re-ask < 0.10, per skill and catalog-wide; guardrail agentic cases 100 % per skill; 0 errored, skipped, or missing cases; the run counts (live, complete, not degraded) and is recorded in a committed `benchmark-streak.v1` |
| RG-5 | The release is delivered by `/speckit-development` | After T054 every task is checked by `dev_state.py mark`; `converge.py` on SPEC-201 reports 0 findings; PR body and review request are produced by the skill and schema-valid |
| RG-6 | The independent review loop works on the R1 PR itself | An `APPROVE` `review-verdict.v1` for the current head from a session other than the author's, holding no live keys and checking the recorded live evidence only, with its own `run-health.v1` comment, accepted by `review_collect.py` (exit 0), in ≤ 3 rounds; offline CI green |
| RG-7 | `Cazador0/skill-factory` is a standalone, reproducible export | Standalone gates pass from the export root; 28 resolving symlinks; 0 secret findings; identical `manifest_digest` for two exports of one commit |
| RG-8 | Webhook events are authentic, unique, fresh, and only hints | 0 recorded or decided state changes from tampered, duplicate, stale, out-of-window, weak-secret, or rate-limited deliveries; 0 failed-signature values in any output; event-driven decisions equal re-read decisions |
| RG-9 | Live runs are monitored, and the reviewer reports its own health | 14 health reports and one run log per gate run; a degraded run never counts; the reviewer's `run-health.v1` accompanies its verdict |

## 3. Entry criteria

Step 5 (execute) does not start until every criterion holds. T001 records each one with evidence in
`skill-lab/specs/201-release-shadow/evidence/entry-check.json`.

| ID | Criterion | Evidence |
|---|---|---|
| E-1 | Foundation SPEC-100..104 is implemented: `skill-lab validate`, `sync --check`, `test`, `bench --tier deterministic`, `score`, `catalog`, `install` exist and run green on the current tree; the CONVENTIONS §4 contracts exist as schemas | Command outputs (envelopes) with exit codes |
| E-2 | The ADRs CONVENTIONS cites exist: ADR-0003 (≈32k context budget) and ADR-0010 (gate not run ≠ passed) | File paths |
| E-3 | SPEC-200 is `Accepted` | Header of `specs/200-release-roadmap/spec.md` |
| E-4 | The six planning artifacts in this folder exist and are mutually consistent: every FR is covered by ≥ 1 task and ≥ 1 planned `verified_by` | `traceability.json` plus a coverage table in `tasks.md` |
| E-5 | The foundation interfaces R1 builds on are confirmed (lab CLI registry, validator hook, installer, bench flags, SPEC-104 metric names) or their actual names are recorded | `evidence/interface-notes.md` |
| E-6 | SPEC-105 is specified, planned, and refined with the person (`skill-lab/specs/105-jev-live-benchmarking/{spec,plan,research,data-model,tasks}.md`) | File paths; the answered intake `intakes/jev-live-benchmarking/intake.md` |

Delivery steps 6 and 7 and the live gate run add their own preconditions. They do not block step 5.

| ID | Precondition | Blocks |
|---|---|---|
| P-6 | `Cazador0/skill-factory` exists (private), has an initial commit on `main`, and this session has push access (synthesis.md Q3) | Step 6 (T140) |
| P-7 | The orchestrator can call `claude-code-remote` `create_session` with an environment that holds none of `OLLAMA_API_KEY`, `TYPESAFE_API_KEY`, `JEV_API_KEY`, or the `claude` CLI is installed and authenticated for the fallback | Step 7 (T142) |
| P-L | `ollama.com` and `api.typesafe.ai` reachable; `OLLAMA_API_KEY` and `TYPESAFE_API_KEY` (or `JEV_API_KEY`) set in the session that runs the live benchmark | The smoke run (T151) and the live gate run (T137), and therefore the R1 merge |

## 4. Exit criteria

R1 has one exit state. The person decided that the first live run is R1's release gate ("the result decides
whether the R1 PR is ready", intake Q1; "one fully passing live run makes the R1 PR ready", intake Q15), so the
live gates sit at the `merge` stage with the offline gates (spec.md §Clarifications row 5; ADR-0106). There is
no "merged, live-pending" state and no follow-up evidence PR. "Not run never counts as pass" (CONVENTIONS §9,
ADR-0010): a live gate that is `not_run` blocks the merge exactly like a `fail`.

**R1 merged (and complete)** (end of step 8):

- X-1: every `merge`-stage gate in `spec.md` §Release gates is `pass`: G-OFF-01..G-OFF-13 and G-LIVE-01..G-LIVE-12. Nothing is `not_run`.
- X-2: the live gates are computed from the newest recorded live gate run whose `suite_digest` matches the reviewed tree: `ollama-cloud`, `jev_mode: live`, one model, every agentic and trigger case of all 14 skills, 0 errored, skipped, or missing cases, not degraded, and counting toward the streak (SPEC-105 FR-011). The run is committed under `skill-lab/benchmarks/runs/<run_id>/` and referenced by digest from `evidence/live-runs.json`.
- X-3: converge reports 0 findings against `spec.md`, `plan.md`, and `tasks.md` (G-OFF-12).
- X-4: a separate Claude Code session (cloud session, or the `claude -p` fallback) that holds no live keys and checked the recorded live evidence only posted an `APPROVE` `review-verdict.v1` for the current PR head and its own `run-health.v1` comment, accepted by `review_collect.py` (G-POST-02), within at most 3 rounds. After 3 rounds the person decides.
- X-5: offline CI on the PR head is green (G-POST-01), and a human merged the PR into `main`.
- X-6: a review round whose fix changed any `SKILL.md` or eval case was preceded by a new passing live gate run, because the change makes the recorded run stale (`LIVE_RUN_STALE`).

R1 defines no gate at the `complete` stage. R1 is complete when it is merged, because its live gates already passed.

**Effect on the next release**: the releases ship as stacked PRs (intake A4; SPEC-200 §Sequencing). R2 enters when
the R1 PR has an independent `APPROVE` verdict and its live gates passed: R2's branch is created from
`release/r1-shadow`, its PR targets `release/r1-shadow`, and it is retargeted to `main` when R1 merges. R3 enters the
same way on R2. Merges happen in order R1 → R2 → R3, each by a human. R1's counting live runs are committed with their suite digest
and recorded in `benchmark-streak.v1`, so they count toward SPEC-202's 3-run L1 streak only on the same model and
suite.

## 5. In and out of scope per skill

R1 column = this release. Partition source: the user's capability table. Refinements are marked ★ and
justified in synthesis.md D-25.

| Skill (spec) | In scope for R1 | Out of scope (goes to) |
|---|---|---|
| lead-architect (SPEC-001) | `spec_readiness.py`, `plan_dag.py` (waves, write-set conflicts), `issue_contract.py` (contract plus rendered body), `dispatch_recommend.py` (recommendation with `mutation_requests[]` for assign plus lease; `--apply` refused; `--event` treated as a hint and re-read through the read-only client), `arbitrate.py` (arbitration record; `--publish` refused) | Dispatch via the mutation path (R2); event-driven dispatch loop (R3) |
| pse-implementer (SPEC-002) | `preflight.py`, `run_check.py` (local execution with recorded logs, secret env scrubbed, denylist ★), `evidence_manifest.py`, `propose_patch.py` (patch file under `--out`, scope check), `delivery_plan.py` (worktree/branch/commit/push/PR as a plan; refused) | Worktree, commit, push, PR (R2); rebase on stale base (R3) |
| review-verifier (SPEC-003) | `requirements_matrix.py`, `quality_gate.py`, `review_verdict.py` (verdict, independence by session id plus commit trailers ★, comment render, comment plan; `--post --apply` refused); live gates checked from recorded evidence only | Posting to Gitea (R2); invalidating stale approvals (R3) |
| speckit-gitea-taskstoissues (SPEC-004) | `tasks_to_issues.py` dry-run `gitea-plan` with map plus title-regex dedupe | `--apply` (R2) |
| speckit-gitea-sync (SPEC-005) | `sync_drift.py` read-only drift report; `comment_plan.py` plan only ★ | Comment plan apply (R2); drift on events (R3) |
| kanban-state-machine (SPEC-006) | `transition.py decide\|next` (10 states, roles, report's `next_action`; with `--event`, decisions from re-read state only); `labels_plan.py` plan only | Applying labels (R2); the live event loop (R3) |
| work-lease (SPEC-007) | `lease.py` local store (`state.write.local`), CAS `version`, overlap detection; `--mirror` refused | Enforcement before PSE work, Gitea mirror (R2); expiry recovery (R3) |
| gitea-event-normalizer (SPEC-008) | `normalize.py` with all four layers: HMAC verify, dedupe by the SHA-256 of the raw signed body (delivery id is metadata only), freshness guard on signed `updated_at` and head SHA, secret hygiene (≥ 32-byte secret, TLS-only guidance, `GITEA_WEBHOOK_SECRET_PREVIOUS` for 7 days after rotation, per-object rate limit, no logging of failing bodies, digests kept 90 days); `serve` refused | The live webhook gateway that serves these layers (R3) |
| merge-policy-gate (SPEC-009) | `merge_decision.py` risk class plus advisory decision capped by level, with `uncapped_decision` ★; `merge_plan.py` refused | Branch-protection audit (R2); `AUTO_MERGE` low risk plus apply (R3) |
| session-checkpoint (SPEC-010) | `checkpoint.py write\|read\|resume-plan\|render`; `publish` refused | Publish to Gitea (R2); lease recovery use (R3) |
| twelve-factor-audit (SPEC-011) | Full (read-only) | — |
| skill-forge (SPEC-012) | Full (local files only: `workspace.write`) | — |
| speckit-development (SPEC-013) | `dev_state.py` (status/next/mark), `converge.py`, `pr_body.py`, `review_request.py`, `review_collect.py` (verdict plus the reviewer's `run-health.v1` comment), `review_local.py` (read-only `claude -p` fallback ★), `delivery_plan.py` (refused) | End-to-end push/PR/review request (R2); hand-off to merge gate (R3) |
| run-monitor (SPEC-014) | `snapshot.py` (built by SPEC-105) emits `run-health.v1` for the benchmark container, the model sessions under test, and the reviewer session; fixed limits decide `degraded`; the model writes an advisory assessment only; read-only | Machine monitoring beyond those three targets (not chosen, intake Q19); model comparison (next journey, intake Q10, Q14) |
| Lab (SPEC-10x areas) | `policy` subcommands, validator rules `policy-action-known` and `eval-inventory-r1`, containment harness, `release check`, `release record-run`, read-only Gitea test double, `export-repo`, config rules, installer refusal for `--inference local`; SPEC-105's harness (re-ask, outage and degraded runs, floor gates per skill and catalog-wide, streak, report, run log, after-skill health checks, price-table cost, committed runs) | Double write endpoints, live Gitea smoke, L1 evaluator, sign-off (R2) |

## 6. Risks

| ID | Risk | Likelihood | Impact | Mitigation in R1 |
|---|---|---|---|---|
| RK-1 | Foundation interfaces differ from what this plan assumes (module names, metric names, flags) | Medium | Medium | T001 records the real names in `interface-notes.md`, and T157 the SPEC-105 names; tasks name files by role, so a rename is mechanical |
| RK-2 | Network allowlist or keys not ready, so the live gates stay `not_run` and R1 cannot merge | Medium | High | Everything offline is finished and green first (T136); the smoke and gate runs start as soon as P-L holds; nothing is fabricated or replayed in their place |
| RK-3 | Ollama Cloud has no structured outputs, so agentic JSON validity misses the ≥ 0.95 floor | High | Medium | Scripts produce the JSON and the model relays it; the agentic prompt embeds `output_schema`; at most 2 repair turns; post-hoc validation (SPEC-102); a failing gate is fixed in procedures and scripts, never in thresholds |
| RK-4 | Unverified runtime facts: Ollama Cloud model ids and their context sizes, Zed per-profile model pinning | Medium | Medium | T112 verifies and records in SOURCES.md and `cloud-models.json`; the endpoint is decided (local Ollama app signed in to ollama.com); a config shape that works whether profiles pin models or a global default applies |
| RK-5 | Scope: 14 skills, 21 contracts plus SPEC-105's 2, 159 tasks | High | Medium | Self-hosting switch-over automates bookkeeping; parallel skill tracks after T054; per-skill tasks sized to one session; SPEC-105 runs from its own task list (T150) |
| RK-6 | Reviewer independence is undermined (same GitHub identity posts both sides, or the reviewer is prompt-injected by PR content) | Medium | High | Independence by session ids plus `Claude-Session:` trailers; reviewer re-runs deterministic gates itself and holds no live keys; human merge |
| RK-7 | An agent bypasses scripts with raw `git push`/`curl` in a target project | Medium | High | Declared guardrail-not-boundary; runtime deny patterns; branch protection plus human merge are the boundary (CONVENTIONS §7) |
| RK-8 | A single live run passes by chance | Medium | Low | One fully passing counting run is the person's R1 bar (intake Q15); reliability is SPEC-202's L1 entry, 3 consecutive counting runs on the same model and suite |
| RK-9 | `claude -p` flags or JSON output shape differ from the documented assumption | Medium | Low | T049 verifies with `claude --help` and records; `review_collect.py --cli-output` accepts either the bare verdict or the CLI wrapper |
| RK-10 | Licensing mistakes in the export (CC BY-SA content, MIT vendored files) | Low | Medium | NOTICE file; no 12-factor-agents content exported; twelve-factor-audit paraphrases with links (D-19) |
| RK-11 | The per-skill floors fail on small samples (5 agentic, 10 trigger cases per skill) although the skills are fine | Medium | Medium | The minimums were chosen so ≥ 0.80 tolerates 1 agentic miss and ≥ 0.90 tolerates 1 misroute per skill; flagged and unstable cases are listed in the PR report so the person can judge; thresholds change only by the person's decision |
| RK-12 | An outage or a crossed health limit voids a long gate run | Medium | Medium | The run continues to completion and records why it does not count (SPEC-105 FR-003, FR-022); the smoke run measures normal levels first, and `monitor-limits.json` is tuned only with the person's approval |

## 7. Milestones

| ID | Milestone | tasks.md phases | Done when |
|---|---|---|---|
| M0 | Entry | Phase 1 (T001–T008, T144, T145) | E-1..E-6 recorded; ADRs drafted |
| M1 | Policy core and shared library | Phase 2 (T009–T035, T146) | Policy, contract, shared-module, and containment tests green; `sync --check` clean |
| M2 | Human control of the level | Phase 3, US1 (T036–T041) | US1 acceptance test green |
| M3 | Self-hosting | Phase 4, US2 (T042–T054) | US2 acceptance green; T054 switch-over recorded; `/speckit-development` drives the rest |
| M4 | Role skills offline-green | Phases 5–8, US3–US6 (T055–T111, T147–T149, T156) | US3–US6 integration tests green, the four webhook layers included |
| M5 | Cloud-first, live harness, export, helpers | Phases 9–11, US7–US9 (T112–T132, T150, T157) | US7 offline acceptance, SPEC-105 offline evidence, US8 standalone test, US9 evals green |
| M6 | Run monitoring | Phase 12, US10 (T152–T155, T158, T159) | US10 integration test green; 14 skills present |
| M7 | Release candidate | Phase 13 (T133–T136) | Offline merge gates all `pass`; converge clean |
| M-LIVE | Live gate | T151, T137 (once P-L holds) | The person has seen the smoke run; the gate run counts and G-LIVE-01..12 `pass` |
| M8 | PR and review | T138–T143 | PR body and export ready; verdict `APPROVE` (current head) with the reviewer's health comment, CI green → hand-off to human merge (R1 merged and complete) |

## 8. Delivery steps for this release

The roadmap's eight steps, made concrete for R1. "Orchestrator" means the build session acting on the
user's explicit instruction under Claude Code's permission system. It is not a skill script, and
`.skill-policy.json` does not govern it (synthesis.md D-1).

| Step | What happens in R1 | Artifact | Who |
|---|---|---|---|
| 1 Plan | This document | `release-plan.md` | Lead (planning session) |
| 2 Synthesize | Findings F-1..F-22, decisions D-1..D-25, residual risks, open questions (answered 2026-10-22) | `synthesis.md` | Lead |
| 3 Tasks as spec | FRs, SCs, gates, contracts, autonomy policy; 159 dependency-ordered tasks | `spec.md`, `tasks.md`, `traceability.json` | Lead |
| 4 Implementation plan | Technical context, constitution check, exact files, wave rule, webhook layers, test and benchmark strategy, rollout and rollback | `plan.md` | Lead |
| 5 Execute | **Bootstrap** T001–T053: the orchestrator follows Spec Kit implement semantics by hand (dependency order, tests first) and records evidence with `_skillkit.checks` from T022 on. **Switch-over** T054: `python3 skills/speckit-development/scripts/dev_state.py status --feature skill-lab/specs/201-release-shadow` writes `evidence/development-report.json`, the verification of the tasks already done is re-run with `dev_state.py check --apply` so their evidence comes from executed commands, and from then on `/speckit-development` (Zed, Claude Code) or `$speckit-development` (Codex) drives each wave: `dev_state.py next` → implement one task → `dev_state.py check --task Tnnn --apply` → `dev_state.py mark --task Tnnn --apply`. SPEC-105 is delivered by T150 from its own task list. **Converge** T135: `converge.py --feature skill-lab/specs/201-release-shadow --apply` until 0 findings. **Offline gates** T136. **Live** T151 (smoke run, shown to the person) and T137 (gate run, committed and recorded by digest; every merge gate must pass) | Code, tests, evals, specs, committed live runs, evidence | Orchestrated sessions, at level `shadow` |
| 6 Pull request | T138 renders `evidence/pr-body.md` with `pr_body.py`, including the live run's report. T139 runs `skill-lab/bin/export-repo --out <scratch>/skill-factory` (28 symlinks; committed runs and the engineering-team report included) and checks it. T140: `delivery_plan.py` emits the `mutation-plan.v1` (branch, commit, push, PR), which is refused for the skill at `shadow`, and the orchestrator executes it on `Cazador0/skill-factory`. That means branch `release/r1-shadow` from the export, one commit with the attribution trailers, push, and a PR into `main` | GitHub PR | Orchestrator |
| 7 Review | T141: `review_request.py --round 1` → `review-request.v1`, whose evidence carries the live run summary's sha256. T142: the orchestrator calls `create_session` (prompt rendered from the request, `source_url` `https://github.com/Cazador0/skill-factory`, `source_revision` `release/r1-shadow`, never `permission_mode: plan`, an environment without live keys). The reviewer session confirms with `skill-lab doctor` that no live key is set, loads `.claude/skills/review-verifier`, re-runs the offline gates, re-computes the live gates from the committed run only, rebuilds the requirements matrix from this `spec.md`, posts the verdict comment (marker plus one fenced `json` block), runs `run-monitor`'s snapshot in its own container, and posts it as a separate marked comment. The orchestrator polls `get_session`/`list_events`, reads the PR comments, and runs `review_collect.py`. `CHANGES_REQUESTED` → fix, a new live gate run if any `SKILL.md` or eval case changed, re-export, push, new round (≤ 3, then the person decides). Fallback when no cloud session can be created: `review_local.py --apply` (`claude -p ... --output-format json --json-schema ...`), with the orchestrator posting the comment | `review-verdict.v1` and `run-health.v1` PR comments | Independent reviewer session |
| 8 Merge | T143: `release check --stage post-review` (CI checks file plus verdict). A human merges `release/r1-shadow` into `main`. Evidence produced after the reviewed head (PR number, request, verdict, post-review report) is not committed to the R1 branch. It is kept in the PR thread and copied into R2's entry check | Merged PR | Human |

## 9. Release branch and naming

| Item | Value | Note |
|---|---|---|
| Release branch | `release/r1-shadow` | Named in SPEC-200's release table |
| PR base | `main` of `Cazador0/skill-factory` | R2 stacks on `release/r1-shadow` once this PR has `APPROVE` and its live gates passed; the R2 PR is retargeted to `main` when R1 merges |
| Live runs | `skill-lab/benchmarks/runs/<run_id>/` | Committed on the release branch before the PR (SPEC-105 FR-015); referenced from `evidence/live-runs.json` by digest |
| Evidence folder | `skill-lab/specs/201-release-shadow/evidence/` | Created at T001 |
| ADR numbers | 0101–0109 reserved for R1 (0101–0107 used) | SPEC-202 reserved 0201–0209; R3 is expected to use 0301–0309 |
| Skill versions | `metadata.version` `0.1.0` for all 14 skills | Pre-1.0 until autonomy is complete |
