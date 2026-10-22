# Release plan: R1 Shadow mode

**Spec ID**: SPEC-201 | **Release**: R1 | **Autonomy level shipped**: `shadow`

**Created**: 2026-10-22 | **Status**: Draft (planning, delivery step 1)

**Parent**: [SPEC-200 release roadmap](../200-release-roadmap/spec.md) | **Next**: [SPEC-202 R2 Agent implementation](../202-release-agent-implementation/release-plan.md)

**Companion documents**: [synthesis.md](synthesis.md) (step 2), [spec.md](spec.md) and [tasks.md](tasks.md) (step 3),
[plan.md](plan.md) (step 4), [traceability.json](traceability.json)

## 1. Scope in one paragraph

R1 ships all 13 portable skills at their shadow-mode capability for Zed + Ollama Cloud first, then Claude
Code and Codex. "Shadow" is the report's first autonomy level: "Lead, PSE, and Review analyze real work and
produce plans/recommendations; humans perform consequential mutations" (report §Progressive autonomy). R1
also owns the machinery every later release builds on. That is the `autonomy-policy.v1` file
`.skill-policy.json`, the 34-entry action catalog, and `_skillkit.policy`, which loads fail-safe to `shadow`,
clamps to the release's maximum level, and refuses with exit 4. It also owns the read-only Gitea client and
test double, the cloud-first Zed configuration with a disabled local profile, the cloud benchmark gates, the
export of the working tree into the standalone repository `Cazador0/skill-factory`, and the independent-review
loop (`review-request.v1` → separate Claude Code cloud session → `review-verdict.v1` PR comment → parse). R1
is delivered with its own 13th skill, `/speckit-development`, which takes over execution of this release's
`tasks.md` once it passes its own acceptance test (the self-hosting switch-over, task T054).

## 2. Release goals

Each goal is measurable. `spec.md` §Release goals maps every goal to FRs, SCs, and gates.

| ID | Goal | Measure (threshold) |
|---|---|---|
| RG-1 | Shadow containment is enforced by policy code, not by prompts | Containment suite: 0 consequential effects (non-GET requests to the double, git ref changes, working-tree writes outside `--out`/`--state-dir`) across 100 % of (skill, action) pairs above `shadow`; ≥ 40 hostile policy files all yield `shadow` |
| RG-2 | 13 skills ship at R1 capability on Zed, Claude Code, and Codex | `validate` 0 errors × 3 runtimes; unit tests 100 % on Python 3.9 and current; deterministic cases 100 % (≥ 52 plus refusal cases); eval inventory 0 violations |
| RG-3 | Every requirement is traced | SPEC-001..013 and SPEC-201: 0 FRs without an existing `verified_by`; 0 `planned: true` at merge |
| RG-4 | Inference is cloud-first and measured live as soon as the network allows | Zed config rules 0 errors (3 of 3 profiles on an Ollama Cloud model, no local model in the template, local file present but not installable); on ≥ 1 complete live run: ≤ 1 failed agentic case per skill, guardrail agentic 1.0, ≤ 1 misrouted trigger case per skill, catalog trigger ≥ 0.90 |
| RG-5 | The release is delivered by `/speckit-development` | After T054 every task is checked by `dev_state.py mark`; `converge.py` on SPEC-201 reports 0 findings; PR body and review request are produced by the skill and schema-valid |
| RG-6 | The independent review loop works on the R1 PR itself | An `APPROVE` `review-verdict.v1` for the current head from a session other than the author's, accepted by `review_collect.py` (exit 0), in ≤ 3 rounds; CI green |
| RG-7 | `Cazador0/skill-factory` is a standalone, reproducible export | Standalone gates pass from the export root; 26 resolving symlinks; 0 secret findings; identical `manifest_digest` for two exports of one commit |

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

Delivery steps 6 and 7 add their own preconditions. They do not block step 5.

| ID | Precondition | Blocks |
|---|---|---|
| P-6 | `Cazador0/skill-factory` exists (private), has an initial commit on `main`, and this session has push access (synthesis.md Q3) | Step 6 (T140) |
| P-7 | The orchestrator can call `claude-code-remote` `create_session`, or the `claude` CLI is installed and authenticated for the fallback | Step 7 (T142) |
| P-L | `ollama.com` and `api.typesafe.ai` reachable; `OLLAMA_API_KEY` and `TYPESAFE_API_KEY` (or `JEV_API_KEY`) set | Live gates only (T137) |

## 4. Exit criteria

R1 uses the two exit states SPEC-202 defines, so "not run never counts as pass" (CONVENTIONS §9, ADR-0010)
holds without making the merge depend on when the network allowlist lands (synthesis.md D-16).

**R1 merged** (end of step 8):

- X-1: every `merge`-stage gate (G-OFF-01..G-OFF-12) in `spec.md` §Release gates is `pass`. Nothing is `not_run`.
- X-2: converge reports 0 findings against `spec.md`, `plan.md`, and `tasks.md` (G-OFF-12).
- X-3: a separate Claude Code session (cloud session, or the `claude -p` fallback) posted an `APPROVE` `review-verdict.v1` for the current PR head, accepted by `review_collect.py` (G-POST-02).
- X-4: CI on the PR head is green (G-POST-01), and a human merged the PR into `main`.
- X-5: no live gate is `fail`. A live gate that ran and failed is a defect, so the reviewer returns `CHANGES_REQUESTED`. Live gates that are `not_run` leave R1 **merged, live-pending**.

**R1 complete**:

- X-6: G-LIVE-01..G-LIVE-05 `pass` on ≥ 1 complete live run (`ollama-cloud`, `jev_mode: live`, 0 errored or skipped cases), recorded under `evidence/bench/`. If the run happens after the merge, its evidence lands through a follow-up evidence-only PR `release/r1-live-evidence` → `main`, reviewed the same way. R1 never pushes evidence onto a reviewed head (synthesis.md D-17).

**Effect on the next release**: R2 steps 5 to 7 may start once X-3 holds (roadmap: "R2 starts only after the
R1 PR has an APPROVE verdict"). R2 cannot reach its own "complete" state while R1 is live-pending. R1's live runs are recorded with their
suite digest, and they count toward SPEC-202's 3-run L1 streak only for the same suite (SPEC-202 D-17).

The same sequencing rule holds between every pair of releases (SPEC-200 §Release index): the next release's step 5
starts at this release's independent `APPROVE` with every `merge`-stage gate `pass`; its step 8 needs this release
merged; its "complete" needs this release complete. A live gate that ran and **failed** is a missed gate in the
roadmap's sense ("the next one does not start"); a live gate that is `not_run` is pending, not missed.

## 5. In and out of scope per skill

R1 column = this release. Partition source: the user's capability table. Refinements are marked ★ and
justified in synthesis.md D-25.

| Skill (spec) | In scope for R1 | Out of scope (goes to) |
|---|---|---|
| lead-architect (SPEC-001) | `spec_readiness.py`, `plan_dag.py` (waves, write-set conflicts), `issue_contract.py` (contract plus rendered body), `dispatch_recommend.py` (recommendation with `mutation_requests[]` for assign plus lease; `--apply` refused), `arbitrate.py` (arbitration record; `--publish` refused) | Dispatch via the mutation path (R2); event-driven dispatch loop (R3) |
| pse-implementer (SPEC-002) | `preflight.py`, `run_check.py` (local execution with recorded logs, secret env scrubbed, denylist ★), `evidence_manifest.py`, `propose_patch.py` (patch file under `--out`, scope check), `delivery_plan.py` (worktree/branch/commit/push/PR as a plan; refused) | Worktree, commit, push, PR (R2); rebase on stale base (R3) |
| review-verifier (SPEC-003) | `requirements_matrix.py`, `quality_gate.py`, `review_verdict.py` (verdict, independence by session id plus commit trailers ★, comment render, comment plan; `--post --apply` refused) | Posting to Gitea (R2); invalidating stale approvals (R3) |
| speckit-gitea-taskstoissues (SPEC-004) | `tasks_to_issues.py` dry-run `gitea-plan` with map plus title-regex dedupe | `--apply` (R2) |
| speckit-gitea-sync (SPEC-005) | `sync_drift.py` read-only drift report; `comment_plan.py` plan only ★ | Comment plan apply (R2); drift on events (R3) |
| kanban-state-machine (SPEC-006) | `transition.py decide\|next` (10 states, roles, report's `next_action`); `labels_plan.py` plan only | Applying labels (R2); event-driven transitions (R3) |
| work-lease (SPEC-007) | `lease.py` local store (`state.write.local`), CAS `version`, overlap detection; `--mirror` refused | Enforcement before PSE work, Gitea mirror (R2); expiry recovery (R3) |
| gitea-event-normalizer (SPEC-008) | `normalize.py` HMAC verify, dedupe (seen set under `--state-dir`), normalize offline files; `serve` refused | Webhook gateway serve (R3) |
| merge-policy-gate (SPEC-009) | `merge_decision.py` risk class plus advisory decision capped by level, with `uncapped_decision` ★; `merge_plan.py` refused | Branch-protection audit (R2); `AUTO_MERGE` low risk plus apply (R3) |
| session-checkpoint (SPEC-010) | `checkpoint.py write\|read\|resume-plan\|render`; `publish` refused | Publish to Gitea (R2); lease recovery use (R3) |
| twelve-factor-audit (SPEC-011) | Full (read-only) | — |
| skill-forge (SPEC-012) | Full (local files only: `workspace.write`) | — |
| speckit-development (SPEC-013) | `dev_state.py` (status/next/mark), `converge.py`, `pr_body.py`, `review_request.py`, `review_collect.py`, `review_local.py` (read-only `claude -p` fallback ★), `delivery_plan.py` (refused) | End-to-end push/PR/review request (R2); hand-off to merge gate (R3) |
| Lab (SPEC-10x areas) | `policy` subcommands, validator rules `policy-action-known` and `eval-inventory-r1`, containment harness, `release check`, `release record-run`, read-only Gitea test double, `export-repo`, config rules, installer refusal for `--inference local` | Double write endpoints, live Gitea smoke, L1 evaluator, sign-off (R2) |

## 6. Risks

| ID | Risk | Likelihood | Impact | Mitigation in R1 |
|---|---|---|---|---|
| RK-1 | Foundation interfaces differ from what this plan assumes (module names, metric names, flags) | Medium | Medium | T001 records the real names in `interface-notes.md`; tasks name files by role, so a rename is mechanical |
| RK-2 | Network allowlist or keys not ready, so live gates stay `not_run` | Medium | Medium | Offline-first exit (R1 merged, live-pending); live run recorded whenever available; never fabricated |
| RK-3 | Ollama Cloud has no structured outputs, so agentic JSON validity fails | High | Medium | Scripts produce the JSON and the model relays it; the agentic prompt embeds `output_schema`; post-hoc validation (SPEC-102); thresholds tolerate 1 capability miss but no guardrail miss |
| RK-4 | Unverified runtime facts: Ollama Cloud model ids, Zed per-profile model pinning, Zed auth to `ollama.com` | Medium | Medium | T112 verifies and records in SOURCES.md; a config shape that works whether profiles pin models or a global default applies |
| RK-5 | Scope: 13 skills, 21 contracts, 143 tasks | High | Medium | Self-hosting switch-over automates bookkeeping; parallel skill tracks after T054; per-skill tasks sized to one session |
| RK-6 | Reviewer independence is undermined (same GitHub identity posts both sides, or the reviewer is prompt-injected by PR content) | Medium | High | Independence by session ids plus `Claude-Session:` trailers; reviewer re-runs deterministic gates itself; human merge |
| RK-7 | An agent bypasses scripts with raw `git push`/`curl` in a target project | Medium | High | Declared guardrail-not-boundary; runtime deny patterns; branch protection plus human merge are the boundary (CONVENTIONS §7) |
| RK-8 | Single live run passes by chance | Medium | Low | R1's live run is a baseline only; R2's L1 needs 3 consecutive runs |
| RK-9 | `claude -p` flags or JSON output shape differ from the documented assumption | Medium | Low | T049 verifies with `claude --help` and records; `review_collect.py --cli-output` accepts either the bare verdict or the CLI wrapper |
| RK-10 | Licensing mistakes in the export (CC BY-SA content, MIT vendored files) | Low | Medium | NOTICE file; no 12-factor-agents content exported; twelve-factor-audit paraphrases with links (D-19) |

## 7. Milestones

| ID | Milestone | tasks.md phases | Done when |
|---|---|---|---|
| M0 | Entry | Phase 1 (T001–T008) | E-1..E-5 recorded; ADRs drafted |
| M1 | Policy core and shared library | Phase 2 (T009–T035) | Policy, contract, shared-module, and containment tests green; `sync --check` clean |
| M2 | Human control of the level | Phase 3, US1 (T036–T041) | US1 acceptance test green |
| M3 | Self-hosting | Phase 4, US2 (T042–T054) | US2 acceptance green; T054 switch-over recorded; `/speckit-development` drives the rest |
| M4 | Role skills offline-green | Phases 5–8, US3–US6 (T055–T111) | US3–US6 integration tests green |
| M5 | Cloud-first, export, helpers | Phases 9–11, US7–US9 (T112–T132) | US7 offline acceptance, US8 standalone test, US9 evals green |
| M6 | Release candidate | Phase 12 (T133–T139) | Merge-stage gate report all `pass`; converge clean; PR body and export ready |
| M7 | PR and review | T140–T143 | Verdict `APPROVE` (current head), CI green → hand-off to human merge (R1 merged) |
| M-LIVE | Live baseline | T137 (whenever P-L holds) | G-LIVE-01..05 `pass` (R1 complete) |

## 8. Delivery steps for this release

The roadmap's eight steps, made concrete for R1. "Orchestrator" means the build session acting on the
user's explicit instruction under Claude Code's permission system. It is not a skill script, and
`.skill-policy.json` does not govern it (synthesis.md D-1).

| Step | What happens in R1 | Artifact | Who |
|---|---|---|---|
| 1 Plan | This document | `release-plan.md` | Lead (planning session) |
| 2 Synthesize | Findings F-1..F-22, decisions D-1..D-25, residual risks, open questions | `synthesis.md` | Lead |
| 3 Tasks as spec | FRs, SCs, gates, contracts, autonomy policy; 143 dependency-ordered tasks | `spec.md`, `tasks.md`, `traceability.json` | Lead |
| 4 Implementation plan | Technical context, constitution check, exact files, wave rule, test and benchmark strategy, rollout and rollback | `plan.md` | Lead |
| 5 Execute | **Bootstrap** T001–T053: the orchestrator follows Spec Kit implement semantics by hand (dependency order, tests first) and records evidence with `_skillkit.checks` from T022 on. **Switch-over** T054: `python3 skills/speckit-development/scripts/dev_state.py status --feature skill-lab/specs/201-release-shadow` writes `evidence/development-report.json`, the verification of T001–T053 is re-run with `dev_state.py check --apply` so their evidence comes from executed commands, and from then on `/speckit-development` (Zed, Claude Code) or `$speckit-development` (Codex) drives each wave: `dev_state.py next` → implement one task → `dev_state.py check --task Tnnn --apply` → `dev_state.py mark --task Tnnn --apply`. **Converge** T135: `converge.py --feature skill-lab/specs/201-release-shadow --apply` until 0 findings | Code, tests, evals, specs, evidence | Orchestrated sessions, at level `shadow` |
| 6 Pull request | T138 renders `evidence/pr-body.md` with `pr_body.py`. T139 runs `skill-lab/bin/export-repo --out <scratch>/skill-factory` and checks it. T140: `delivery_plan.py` emits the `mutation-plan.v1` (branch, commit, push, PR), which is refused for the skill at `shadow`, and the orchestrator executes it on `Cazador0/skill-factory`. That means branch `release/r1-shadow` from the export, one commit with the attribution trailers, push, and a PR into `main` | GitHub PR | Orchestrator |
| 7 Review | T141: `review_request.py --round 1` → `review-request.v1`. T142: the orchestrator calls `create_session` (prompt rendered from the request, `source_url` `https://github.com/Cazador0/skill-factory`, `source_revision` `release/r1-shadow`, never `permission_mode: plan`). The reviewer session loads `.claude/skills/review-verifier`, re-runs the offline gates, rebuilds the requirements matrix from this `spec.md`, and posts the verdict comment (marker plus one fenced `json` block). The orchestrator polls `get_session`/`list_events`, reads the PR comments, and runs `review_collect.py`. `CHANGES_REQUESTED` → fix, re-export, push, new round (≤ 3). Fallback when no cloud session can be created: `review_local.py --apply` (`claude -p ... --output-format json --json-schema ...`), with the orchestrator posting the comment | `review-verdict.v1` PR comment | Independent reviewer session |
| 8 Merge | T143: `release check --stage post-review` (CI checks file plus verdict). A human merges `release/r1-shadow` into `main`. Evidence produced after the reviewed head (PR number, request, verdict, post-review report) is not committed to the R1 branch. It is kept in the PR thread and copied into R2's entry check | Merged PR | Human |

## 9. Release branch and naming

| Item | Value | Note |
|---|---|---|
| Release branch | `release/r1-shadow` | Matches SPEC-202's assumption |
| PR base | `main` of `Cazador0/skill-factory` | R2 stacks on `release/r1-shadow` |
| Follow-up evidence branch | `release/r1-live-evidence` | Only if the live baseline lands after the merge |
| Evidence folder | `skill-lab/specs/201-release-shadow/evidence/` | Created at T001 |
| ADR numbers | 0101–0109 reserved for R1 | SPEC-202 reserved 0201–0209; R3 is expected to use 0301–0309 |
| Skill versions | `metadata.version` `0.1.0` for all 13 skills | Pre-1.0 until autonomy is complete |
