# Feature Specification: Release roadmap for progressive autonomy

**Spec ID**: SPEC-200

**Created**: 2026-10-22

**Status**: Accepted

**Input**: User decisions in the build session, 2026-10-22:
"All three options. Phase out each option as separate specs and define all release goals for each
option, then sequence each option and complete all tasks: Plan → Synthesize → Create Tasks as Spec →
Create Implementation Plan → Execute and deliver Implementation Plan as `/speckit-development` →
Create Pull Request → another Claude Code session reviews the changes."
"Everything cloud first. Local enabled second after cloud is reliable and performing as expected and
aligned to user intent."

## Intent

The skills bring the report's Lead / PSE / Review engineering organization to the Zed Agent,
Claude Code, and Codex. Autonomy is earned in steps, not granted at once. Each autonomy level the
report defines is a separate release with its own spec, release goals, and gates. A release ships
only after the previous release's gates have passed.

## Releases

| Release | Spec | Autonomy level shipped | What agents may do on their own | What stays human |
|---|---|---|---|---|
| R1 Shadow | SPEC-201 | `shadow` | Read, analyse, plan, and emit JSON plans, verdicts, and decisions. Every Gitea and git mutation is a plan (`gitea-plan`, `mutation-request`) | Every consequential write and every merge |
| R2 Agent implementation | SPEC-202 | `agent-implementation` | PSE branches, codes, tests, pushes its own branch, and opens a PR. Lead creates issues and dependencies. Review posts reviews. Leases are enforced | Merge (the merge gate never returns `AUTO_MERGE`) |
| R3 Guarded autonomous | SPEC-203 | `guarded-autonomous` | Low-risk PRs auto-merge through Gitea "merge when checks succeed" once Review, CI, freshness, and dependency gates pass. Event-driven dispatch, lease recovery | High- and critical-risk merges, any change to policy, CI, agent permissions, or the gates themselves |

A release supports its own level and every lower level. The active level for a project is set in
`.skill-policy.json` (contract `autonomy-policy.v1`, defined in SPEC-201). Raising the level is a
**critical-risk** change: it always needs a human, and no agent may make it. That follows the
report's invariant that agents may not autonomously weaken the rules that define their authority.

## Inference track

| Step | When | Configuration |
|---|---|---|
| C1 Cloud first | R1 | Every Zed profile (Lead, PSE, Review) defaults to an Ollama Cloud model. Benchmarks run `--runtime ollama-cloud --jev live` |
| L1 Local second | R2, gated | Local Ollama profiles ship disabled. L1's entry is SPEC-105's `benchmark-streak.v1` with `local_unlock_evidence: true` for the cloud model (3 consecutive counting runs on the same model and suite digest) plus the person's recorded sign-off. Then the same floor gates must pass on `--runtime ollama-local`, and L1 switches the profile model ids to local models on the same provider (the local Ollama app) |

The gate for enabling local inference is measured. "Reliable" means every skill and the whole catalog meet the
floor on Ollama Cloud with Jev judgments live (agentic pass rate ≥ 0.80, trigger accuracy ≥ 0.90, agentic
schema-valid rate ≥ 0.95, Jev uncertain rate after one re-ask < 0.10, guardrail cases 100 %), on 3 consecutive
counting runs of the same model and suite (intake Q3; SPEC-105 FR-005..FR-012). A counting run is live (never
replay), complete, not degraded, and has no errored case. "Aligned to user intent" is the person's recorded
sign-off in `skill-lab/benchmarks/signoff/` (in SPEC-202). The endpoint is the local Ollama app signed in to
ollama.com (`http://localhost:11434`), which serves cloud models in R1 and local models after L1 (SPEC-201
§Clarifications).

## Delivery process (every release)

```text
1 Plan            release-plan.md   scope, release goals RG-n, entry and exit criteria
2 Synthesize      synthesis.md      research findings, decisions, risks, open questions
3 Tasks as spec   spec.md           FR-n, SC-n, acceptance scenarios, release gates
                  tasks.md          Spec Kit format, dependency-ordered, mapped to skills
4 Impl. plan      plan.md           technical context, architecture deltas, test strategy
5 Execute         /speckit-development drives tasks.md: implement → evidence → converge
6 Pull request    release branch → Cazador0/skill-factory
7 Review          a separate Claude Code cloud session, holding no live keys and checking the
                  recorded live evidence only, runs review-verifier on the PR, posts a
                  review-verdict.v1 JSON comment, and posts its own run-health.v1 report as a
                  separate marked comment; at most 3 rounds, then the person decides
8 Merge           human merge after the verdict is APPROVE, every merge-stage gate (the live
                  gates included) passes, and CI is green
```

Steps 1 to 4 live in `skill-lab/specs/20N-release-<name>/`. Step 5 is the `speckit-development`
skill (SPEC-013), one of the 14 skills. In R1 it runs plan-and-evidence only; from R2 it delivers the PR
end to end. Step 7 never runs in the session that wrote the change, so the reviewer and the author
are always independent.

## Release goals (summary; each release spec is authoritative)

- **R1 (SPEC-201)**: all 14 skills install and validate on Zed, Claude Code, and Codex; the 14th is
  `run-monitor` (SPEC-014, family `control-plane`, secondary family `meta`). The autonomy policy is
  enforced by `_skillkit.policy`, and at level `shadow` every mutation is refused with exit 4 or emitted
  as a plan. Deterministic gates pass 100 %. R1 delivers SPEC-105 (Jev live benchmarking) and merges only
  after one fully passing, counting live run on Ollama Cloud with live Jev grading, measured against the
  floor per skill and catalog-wide. Webhook events get all four defense layers (body-digest dedupe,
  freshness guard, events as hints, secret hygiene). Zed profiles are configured cloud-first. The
  automated review loop (step 7) works on the R1 PR itself.
- **R2 (SPEC-202)**: PSE delivers a real PR from an isolated worktree under a lease, with evidence
  produced only from executed commands. `speckit-gitea-taskstoissues --apply` is idempotent against
  the Gitea test double, and against a live Gitea when one is configured. Review posts verdicts. The
  merge gate never auto-merges. Local inference L1 is enabled behind its gate.
- **R3 (SPEC-203)**: `AUTO_MERGE` for low risk only. Event-driven loop: the live webhook gateway,
  built on R1's four webhook defense layers, then state machine, then dispatch. Lease-expiry recovery from checkpoints. Promotion and
  demotion between levels driven by the report's core metrics, with automatic demotion to
  `agent-implementation` after an escaped defect or a revert.

## Sequencing

```text
Foundation (SPEC-100..104) ──► R1 Shadow (+ SPEC-105) ──► R2 Agent implementation ──► R3 Guarded autonomous
                                  │                              │
                          C1 cloud gates ──3 counting runs + sign-off──► L1 local enablement
```

R2's entry is R1 merged, with an `APPROVE` verdict from the independent reviewer and R1's live gates
passed. R3's entry is R2 merged. R1 merges only after one fully passing, counting live run, so there is
no "merged, live-pending" state (the person's decisions, 2026-10-22). A release that misses a gate stays
open; the next one does not start.

## Success Criteria

- **SC-001**: Each release has release-plan.md, synthesis.md, spec.md, plan.md, and tasks.md, with every FR traced to tasks and verification.
- **SC-002**: Each release PR receives a review-verdict.v1 from a session other than the authoring session before merge.
- **SC-003**: At level `shadow`, 0 consequential mutations succeed across the full deterministic suite (every attempt exits 4 or emits a plan).
- **SC-004**: Local inference is enabled only with a passing L1 gate record.

## Non-goals

- Agents merging the skill-factory repository's own PRs. The factory's main branch is always merged by a human.
- Storing or reconstructing chain-of-thought.
- Persona pedigree prompts. Roles are defined by competencies, permissions, and evidence.

## Release index

Each release folder holds the five delivery documents of steps 1–4 plus its `traceability.json`. The release specs are
authoritative; this index only links them. Open questions for all three releases are consolidated in
[open-questions.md](open-questions.md), and this roadmap's own success criteria are traced in
[traceability.json](traceability.json).

| Release | Spec | Level | 1 Plan | 2 Synthesize | 3 Tasks as spec | 3 Task list | 4 Implementation plan | Traceability | Release branch → PR base |
|---|---|---|---|---|---|---|---|---|---|
| R1 Shadow | SPEC-201 | `shadow` | [release-plan.md](../201-release-shadow/release-plan.md) | [synthesis.md](../201-release-shadow/synthesis.md) | [spec.md](../201-release-shadow/spec.md) | [tasks.md](../201-release-shadow/tasks.md) (159 tasks; SPEC-105 delivered by T150) | [plan.md](../201-release-shadow/plan.md) | [traceability.json](../201-release-shadow/traceability.json) | `release/r1-shadow` → `main` |
| R2 Agent implementation | SPEC-202 | `agent-implementation` | [release-plan.md](../202-release-agent-implementation/release-plan.md) | [synthesis.md](../202-release-agent-implementation/synthesis.md) | [spec.md](../202-release-agent-implementation/spec.md) | [tasks.md](../202-release-agent-implementation/tasks.md) (147 tasks) | [plan.md](../202-release-agent-implementation/plan.md) | [traceability.json](../202-release-agent-implementation/traceability.json) | `release/r2-agent-implementation` (from `main` at the R1 merge commit) → `main` |
| R3 Guarded autonomous | SPEC-203 | `guarded-autonomous` | [release-plan.md](../203-release-guarded-autonomous/release-plan.md) | [synthesis.md](../203-release-guarded-autonomous/synthesis.md) | [spec.md](../203-release-guarded-autonomous/spec.md) | [tasks.md](../203-release-guarded-autonomous/tasks.md) (155 tasks) | [plan.md](../203-release-guarded-autonomous/plan.md) | [traceability.json](../203-release-guarded-autonomous/traceability.json) | `release/r3-guarded-autonomous` (from `main` at the R2 merge commit) → `main` |

### Cross-release anchors

These facts appear in more than one release spec. They were re-checked on 2026-10-22 against the person's final
decisions (SPEC-201 §Clarifications, the answered intake `intakes/jev-live-benchmarking/intake.md`, and SPEC-105),
and a change to any of them must be made in every release that states it.

| Anchor | Value | Defined in |
|---|---|---|
| Skills | 14 skills, SPEC-001..SPEC-014. The 14th, `run-monitor` (SPEC-014, `metadata.family: control-plane`, `metadata.secondary_family: meta`), ships in R1; SPEC-105 FR-019..FR-023 define its R1 capability. Deterministic minimum 14 × 4 = 56 cases (R2 raises the release floor to ≥ 116, R3 to ≥ 206); install symlinks 14 × 2 = 28. `run-monitor` changes: R2 adds one option, `snapshot.py --host-metrics off`, which bench passes on `--runtime ollama-local` runs so no figures from your machine are recorded (OQ-22); R3 makes no change | SPEC-201 FR-032, FR-048; SPEC-202 FR-048, D-27, G-OFF-05; SPEC-203 FR-058, D-29, G-OFF-05; CONVENTIONS §2, §6 |
| Eval minimums | Per skill: ≥ 4 deterministic; ≥ 5 agentic, ≥ 1 of them `guardrail`; ≥ 10 trigger, ≥ 2 of them `expect_skill: null` | CONVENTIONS §5; SPEC-105 FR-007; SPEC-201 FR-033 |
| Live gate floor | SPEC-104's defaults are the floor, per skill and catalog-wide: agentic pass rate ≥ 0.80, trigger accuracy ≥ 0.90, agentic schema-valid rate ≥ 0.95, Jev uncertain rate after one re-ask < 0.10; guardrail-tagged agentic cases 100 %; a per-skill criteria file may only raise a gate. No count-based gate and no lowered per-skill threshold. Later releases add gates on top of the floor in their own specs | SPEC-105 FR-005..FR-008; SPEC-201 §Release gates; SPEC-202, SPEC-203 §Release gates |
| Live run rules | An uncertain judgment is re-asked once, then failed and flagged; an outage (connection error, HTTP 5xx, 429 after retries) makes cases `errored` and the run not counting; 401, 403, and 422 are not outages; a degraded run does not count; replay never counts; results are committed under `skill-lab/benchmarks/runs/<run_id>/` and release evidence references them by digest; cost from the person's price table, usage only when any price is missing; `monitor-limits.json` changes need the person's approval | SPEC-105 FR-002..FR-022; SPEC-201 FR-041, FR-049 |
| Exit states and sequencing | R1 merges only after one fully passing, counting live run: every offline and live gate is at the `merge` stage, `not_run` blocks like `fail`, and there is no "merged, live-pending" state or follow-up evidence PR. R1 is complete when merged. R2 and R3 follow the same rule: their live gates are at the `merge` stage, and each is complete when merged (how many counting runs R3 needs is OQ-24). R2's entry is R1 merged with an independent `APPROVE` and its live gates passed; R3's entry is R2 merged. `not_run` never counts as `pass`. No project is promoted to `guarded-autonomous` before R3 is merged (SPEC-203 P-8) | SPEC-201 release-plan §4; SPEC-202 and SPEC-203 entry criteria |
| Action catalog | `catalog_version` 1.0.0 (SPEC-201): 34 actions, 3 `shadow` / 19 `agent-implementation` / 7 `guarded-autonomous` / 5 `human-only`. 1.1.0 (SPEC-203): adds `autonomy.demote` (`shadow`) and `gitea.pr.merge_schedule.cancel` (`agent-implementation`), 36 actions, 4 / 20 / 7 / 5. No release lowers a minimum level. Creating a Gitea webhook (`gitea.webhook.create`) is `human-only` at every level | SPEC-201 §Autonomy policy, SPEC-202 §Autonomy policy, SPEC-203 §Autonomy policy |
| Supported maximum level | `_skillkit.policy.SUPPORTED_MAX_LEVEL`: `shadow` (R1), `agent-implementation` (R2, only with base-branch verification of `.skill-policy.json`), `guarded-autonomous` (R3, only with a verified human promotion and no active demotion) | SPEC-201 FR-003, SPEC-202 FR-001/FR-002, SPEC-203 FR-001/FR-002 |
| Human-owned files | Agents may not edit `.skill-policy.json` (`set_by: Cazador0`), `skill-lab/benchmarks/criteria/**`, or `skill-lab/benchmarks/monitor-limits.json`; Zed and Claude Code settings deny those edits, and `merge-policy-gate` classifies them `critical` | SPEC-201 FR-012, §Security |
| Webhook defense | All four layers ship in R1: dedupe by the SHA-256 of the raw signed body (the delivery id is metadata only); a freshness guard on each issue's and PR's signed `updated_at` and head SHA, so older bodies are stale and never drive a state change; events are hints that decision scripts re-read through the read-only Gitea client before deciding; secret hygiene (≥ 32-byte random secret, TLS-only guidance, `GITEA_WEBHOOK_SECRET_PREVIOUS` accepted for 7 days after rotation and listed in `SECRET_ENV_VARS`, a per-object rate limit, no logging of bodies that fail the signature, digests kept 90 days). `normalized-event.v1` gains `body_sha256` and `stale` (additive). R3 builds the live gateway on these layers and introduces none of them | SPEC-201 FR-025, FR-047; SPEC-203 |
| Inference | C1: every Zed profile defaults to one Ollama Cloud model in R1, reached through the local Ollama app signed in to ollama.com (`http://localhost:11434`); T112 verifies the model ids only; the local profile file ships disabled. L1 (R2): SPEC-105's `benchmark-streak.v1` with `local_unlock_evidence: true` for the cloud model (3 consecutive counting runs, same model and suite digest) plus the person's recorded sign-off; then the same floor gates on `--runtime ollama-local`; L1 switches the profile model ids to local models on the same provider | SPEC-201 FR-039; SPEC-105 FR-010; SPEC-202 L1 |
| Independent review | `review-request.v1` (SPEC-201) → a fresh, separate Claude Code cloud session per round (`create_session`; `claude -p --json-schema` fallback records `reviewer.mode: cli-fallback`) that holds no Ollama or TypeSafe keys and checks recorded evidence only → one marked PR comment with one `review-verdict.v1`, plus the reviewer's own `run-health.v1` as a separate marked comment (`<!-- skill-lab:run-health:v1 request_id=<id> -->`) → `review_collect.py`; at most 3 rounds, then the person decides. CI runs offline on every PR; live tiers only when started manually. Evidence produced at or after the reviewed head stays out of the release branch | SPEC-201 D-12, D-13, D-17, FR-034..FR-037, FR-044 |
| Contract ownership | New contracts: SPEC-201 21, SPEC-105 2 (`benchmark-streak`, `run-health`, delivered in R1), SPEC-202 12, SPEC-203 11. Later releases change them only additively and stay on `v1` (`urn:skill-lab:schema:<name>:v1`) | each release spec §Contracts; SPEC-105 data-model.md |
| ADR blocks | R1 0101–0109 (0101–0107 used), R2 0201–0209, R3 0301–0309 | SPEC-201 D-22, SPEC-202 D-25, SPEC-203 D-26 |
