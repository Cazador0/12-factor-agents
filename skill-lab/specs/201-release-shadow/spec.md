# Feature Specification: R1 Shadow mode

**Feature Branch**: `release/r1-shadow`

**Spec ID**: SPEC-201

**Created**: 2026-10-22

**Status**: Draft (delivery step 3)

**Parent**: [SPEC-200 release roadmap](../200-release-roadmap/spec.md) | **Next**: SPEC-202 (R2 Agent implementation)

**Companion documents**: [release-plan.md](release-plan.md) (step 1), [synthesis.md](synthesis.md) (step 2),
[plan.md](plan.md) (step 4), [tasks.md](tasks.md), [traceability.json](traceability.json)

**Input**: User decisions, 2026-10-22: "All three options. Phase out each option as separate specs and define
all release goals for each option ... Plan → Synthesize → Create Tasks as Spec → Create Implementation Plan →
Execute and deliver Implementation Plan as `/speckit-development` → Create Pull Request → another Claude Code
session reviews the changes." "Everything cloud first. Local enabled second after cloud is reliable and
performing as expected and aligned to user intent."

## Intent

R1 ships the report's **shadow mode** ("Lead, PSE, and Review analyze real work and produce
plans/recommendations; humans perform consequential mutations", report §Progressive autonomy) for all 13
skills on Zed + Ollama Cloud first, then Claude Code and Codex. R1 also ships the machinery that every later
release depends on: the `autonomy-policy.v1` file, the action catalog, and `_skillkit.policy`, which turn
the report's doctrine "LLM decides what it believes should happen. Policy code decides what it is allowed to
make happen. Gitea enforces the final repository rules" (report §Orchestrator state model) into code. At
level `shadow` every consequential write is either emitted as a plan (exit 0) or refused (exit 4). Finally
R1 proves the delivery loop on itself: `/speckit-development` drives this release's `tasks.md`, the working
tree is exported to `Cazador0/skill-factory`, and a separate Claude Code cloud session reviews the R1 PR and
posts a `review-verdict.v1` comment.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - The human controls the autonomy level and nothing can raise it (Priority: P1)

The project owner keeps `.skill-policy.json` at the project root. Every skill script reads it through
`_skillkit.policy`, and no agent, flag, environment variable, or malformed file can make a script act above
the level the owner set, or above the highest level the installed release supports (R1: `shadow`).

**Why this priority**: Every other story's safety depends on it. It encodes the report's invariant "Agents may
operate autonomously inside the rules; they may not autonomously weaken the rules that define their
authority" (report §Safe autonomous merge).

**Independent Test**: Run the containment harness against the fixture skill
`skill-lab/tests/fixtures/containment/fake-skill/` with every hostile policy fixture; every `--apply` attempt
of an action above `shadow` exits 4 and the Gitea test double, git refs, and working tree are unchanged.

**Acceptance Scenarios**:

1. **Given** no `.skill-policy.json`, **When** a script runs with `--apply` for `gitea.issue.create`, **Then** it exits 4 with error `POLICY_LEVEL_TOO_LOW` naming the action, its minimum level `agent-implementation`, and the effective level `shadow`, and the test double logs 0 non-GET requests.
2. **Given** a valid file with `"level": "agent-implementation"`, **When** `skill-lab policy show` runs on R1, **Then** `effective_level` is `shadow`, `declared_level` is `agent-implementation`, and the envelope carries warning `POLICY_LEVEL_CLAMPED`.
3. **Given** a file whose `level` key appears twice (`"shadow"` then `"guarded-autonomous"`), **When** it is loaded, **Then** the effective level is `shadow` with warning `POLICY_FILE_INVALID`, and loading does not raise.
4. **Given** level `shadow` and `"overrides": {"deny": ["state.write.local"]}`, **When** `work-lease` runs `lease.py acquire --apply`, **Then** it exits 4 with `POLICY_ACTION_DENIED` and writes nothing under `--state-dir`.
5. **Given** any level, **When** a script calls `require("policy.change")`, **Then** it exits 4 with `POLICY_HUMAN_ONLY`.
6. **Given** `SKILL_POLICY_LEVEL=guarded-autonomous` in the environment and `--apply --force` on the command line, **When** the policy loads, **Then** neither has any effect on the effective level.

---

### User Story 2 - Deliver this release with `/speckit-development` and an independent review (Priority: P1)

The build orchestrator runs `/speckit-development` (Zed, Claude Code) or `$speckit-development` (Codex) on a
feature directory. The skill executes `tasks.md` in dependency order, one task per step, records evidence
only from commands it actually ran, converges against spec/plan/tasks, drafts the PR body, and emits a
`review-request.v1`. At `shadow` it never commits, pushes, or opens a PR; it emits those as a
`mutation-plan.v1`. It collects the reviewer's verdict from a PR comment (or from the `claude -p` fallback)
and decides whether the head is approved.

**Why this priority**: The user asked for this exact command, and R1 is delivered with it (roadmap step 5).
Building it early lets it drive the remaining R1 tasks (plan.md §Self-hosting switch-over).

**Independent Test**: Run it on the golden feature `skill-lab/fixtures/golden-feature/specs/042-session-refresh`
in a scratch copy: the next wave is computed, a task is marked done only after its check passed, converge on a
complete tree leaves `tasks.md` byte-identical, and `review_collect.py` approves only a current-head,
independent `APPROVE` verdict.

**Acceptance Scenarios**:

1. **Given** the golden `tasks.md` (T001 and T002 checked), **When** `dev_state.py next` runs, **Then** the next wave is `[T003, T004]` and T005 follows in a later wave, because T005 has no `[P]` and so depends on the task before it, T004 (plan.md §Wave rule, rule 2).
2. **Given** T003 has no passing `check-run` for its declared verification, **When** `dev_state.py mark --task T003 --apply` runs, **Then** it exits 1 with `TASK_NOT_VERIFIED` and `tasks.md` is unchanged.
3. **Given** a feature whose code satisfies every requirement, **When** `converge.py --apply` runs, **Then** `tasks.md` is byte-for-byte unchanged and `converged` is `true` (Spec Kit converge semantics, synthesis.md F-12).
4. **Given** a requirement with no implementing path, **When** `converge.py --apply` runs, **Then** a `## Phase N: Convergence` section is appended with one new task per finding, and no existing task line changes.
5. **Given** a verdict comment with the request marker, `result: APPROVE`, `reviewed_commit` equal to the request's head SHA, and a reviewer session id absent from every `Claude-Session:` trailer in `base..head`, **When** `review_collect.py` runs, **Then** it exits 0.
6. **Given** the same verdict but the PR head has moved, **When** `review_collect.py` runs, **Then** it exits 1 with `VERDICT_STALE`.
7. **Given** the reviewer session id equals the author session id, **When** `review_collect.py` runs, **Then** it exits 4 with `REVIEW_NOT_INDEPENDENT`.
8. **Given** no `claude` executable on `PATH`, **When** `review_local.py --apply` runs, **Then** it exits 3 with `CLAUDE_CLI_NOT_FOUND`; **Given** it is present, **When** run without `--apply`, **Then** the plan contains argv with `-p`, `--output-format json`, and `--json-schema <vendored review-verdict schema path>`.
9. **Given** level `shadow`, **When** `delivery_plan.py --step commit|push|pr --apply` runs (actions `git.commit`, `git.push.branch`, `gitea.pr.create`), **Then** each exits 4 with `POLICY_LEVEL_TOO_LOW` and performs no git or network operation.

---

### User Story 3 - Lead plans a feature without touching Gitea (Priority: P1)

The Lead runs `lead-architect`, `speckit-gitea-taskstoissues`, and `speckit-gitea-sync` against a Spec Kit
feature and a read-only view of Gitea (an exported issue list, or the read-only client against the test
double). It gets spec readiness, the task DAG with waves and write-set conflicts, issue contracts, a dispatch
recommendation, a dry-run `gitea-plan`, and a drift report.

**Why this priority**: It is the Lead's whole shadow workflow (report §Lead contract, §Gitea integration for
Spec Kit).

**Independent Test**: Run the US3 integration test on the golden feature against the read-only Gitea test
double seeded with issues for T001 to T003.

**Acceptance Scenarios**:

1. **Given** the golden feature, **When** `spec_readiness.py` runs, **Then** `ready` is `true` and FR-001..FR-008 each trace to at least one task.
2. **Given** the golden `tasks.md`, **When** `plan_dag.py` runs, **Then** the graph has 14 tasks, edges T006→T008, T007→T008, T008→T009, T011→T012, no cycles, and a write-set conflict between T006 and T007 on `src/auth/tokens/` that puts them in different waves.
3. **Given** the double's seed (open issues `T001: …` to `T003: …`, a closed `T013: …`, and an orphan `T099: stray`), **When** `tasks_to_issues.py` runs without `--apply`, **Then** the `gitea-plan` creates exactly 10 issues (T004 to T012 and T014) and 4 dependency links (T008→T006, T008→T007, T009→T008, T012→T011), lists T001 to T003 and the closed T013 in `skipped[]` (dedupe covers closed issues, SOURCES.md Spec Kit), ignores T099, and a second run produces a byte-identical payload.
4. **Given** the same inputs, **When** `tasks_to_issues.py --apply` runs at `shadow`, **Then** it exits 4 and the double logs 0 non-GET requests.
5. **Given** a map where T013's issue is closed but T013 is unchecked, and an open issue titled `T099: stray`, **When** `sync_drift.py` runs, **Then** `in_sync` is `false` with drift kinds `state_mismatch` (T013) and `orphan_issue` (T099).
6. **Given** an active local lease on `src/auth/tokens/**`, **When** `dispatch_recommend.py` runs, **Then** tasks whose write domains overlap are in `deferred[]` with reason `lease_held`, and `--apply` exits 4.

---

### User Story 4 - PSE produces a proposed patch with executed evidence (Priority: P1)

A PSE session runs `pse-implementer`, `work-lease`, and `session-checkpoint`: preflight, a local lease, local
checks with recorded logs, an evidence manifest, and a proposed patch file. It never commits, pushes, or
opens a PR in R1.

**Why this priority**: It is the report's PSE contract minus the writes ("never mark evidence as passed unless
executed", report §Agent configuration philosophy).

**Independent Test**: In a scratch git repository built from the golden fixture, run preflight, acquire a
lease, change one file, run a check, build evidence, and propose the patch; the patch applies cleanly with
`git apply --check` and every check in the evidence has a matching `check-run.v1` log digest.

**Acceptance Scenarios**:

1. **Given** a spec containing `[NEEDS CLARIFICATION`, **When** `preflight.py` runs, **Then** `ready` is `false` with an `ambiguities[]` entry naming file and line.
2. **Given** `GITEA_TOKEN` is set, **When** `run_check.py --apply -- python3 -c "import os; print(os.environ.get('GITEA_TOKEN'))"` runs, **Then** the child prints `None` and `env_removed` lists `GITEA_TOKEN`.
3. **Given** `run_check.py --apply -- git push origin HEAD`, **When** it runs, **Then** it exits 4 with `CHECK_COMMAND_FORBIDDEN` and does not start a process.
4. **Given** an evidence draft that claims `unit: passed` without a recorded check, **When** `evidence_manifest.py validate` runs, **Then** it exits 1 with `CHECK_NOT_EXECUTED`.
5. **Given** a working-tree change outside the issue's `write_domains`, **When** `propose_patch.py` runs, **Then** it exits 1 with `SCOPE_VIOLATION` and `scope_ok: false`.
6. **Given** two leases requested for overlapping `write_domains`, **When** the second `lease.py acquire --apply` runs, **Then** it exits 1 with a `lease-check.v1` whose `grantable` is `false`.
7. **Given** a checkpoint whose `head_commit` differs from the branch head, **When** `checkpoint.py resume-plan` runs, **Then** `stale` is `true` and `next_action` tells the session to re-read the branch before continuing.

---

### User Story 5 - Review returns an independent verdict and merge advice (Priority: P1)

A Review session reconstructs the requirements matrix from the spec, computes the quality gate, and emits a
`review-verdict.v1` plus the PR comment that carries it. `merge-policy-gate` classifies risk and returns an
advisory decision.

**Why this priority**: Step 7 of every release depends on it, and it carries the report's "Not run must never
silently mean passed" rule (report §Merge evidence gate).

**Independent Test**: Run the US5 integration test: build matrix, gate, and verdict for the golden feature,
render the comment, and parse it back with `speckit-development/scripts/review_collect.py`.

**Acceptance Scenarios**:

1. **Given** the golden spec, **When** `requirements_matrix.py` runs, **Then** it lists FR-001..FR-008 and NFR-001..NFR-004 (12 requirements) plus SC-001..SC-004.
2. **Given** a quality gate where category `integration` is `applicable: true` and `status: not_run`, **When** `quality_gate.py` runs, **Then** `passed` is `false`.
3. **Given** a passing quality gate and 0 blockers, **When** `review_verdict.py` runs with a reviewer session id that appears in a `Claude-Session:` trailer of `base..head`, **Then** it exits 4 with `REVIEW_NOT_INDEPENDENT`.
4. **Given** a valid verdict, **When** `review_verdict.py --render-comment` runs, **Then** the comment has exactly one marker line and exactly one fenced `json` block, and `review_collect.py` parses it to an identical payload.
5. **Given** a diff that touches `.skill-policy.json`, **When** `merge_decision.py` runs, **Then** `risk_class` is `critical`, `decision` is `HUMAN_APPROVAL_REQUIRED`, and `policy_paths_touched` lists the file.
6. **Given** a docs-only diff with an `APPROVE` verdict and green checks at `shadow`, **When** `merge_decision.py` runs, **Then** `risk_class` is `low`, `decision` is `HUMAN_APPROVAL_REQUIRED`, and `uncapped_decision` is `AUTO_MERGE`.
7. **Given** level `shadow`, **When** `merge_plan.py --apply` or `review_verdict.py --post --apply` runs, **Then** it exits 4.

---

### User Story 6 - Control-plane decisions from offline events (Priority: P2)

`gitea-event-normalizer` verifies and normalizes webhook deliveries saved as files, and
`kanban-state-machine` decides transitions and next actions from them.

**Why this priority**: It establishes the event contract R3 serves live, but nothing in R1 needs it to deliver a PR.

**Independent Test**: Feed the recorded fixtures (valid, tampered, duplicate) through `normalize.py` and then
`transition.py`; decisions match the report's `next_action` function for each fixture.

**Acceptance Scenarios**:

1. **Given** a payload whose `X-Gitea-Signature` is the hex HMAC-SHA256 of the raw body under `GITEA_WEBHOOK_SECRET`, **When** `normalize.py` runs, **Then** it exits 0 with `signature_verified: true`.
2. **Given** the same payload with one body byte changed, **When** `normalize.py` runs, **Then** it exits 1 with `signature_verified: false` and `blocking: true`.
3. **Given** a delivery id already recorded in the seen set, **When** `normalize.py` runs, **Then** `duplicate` is `true`.
4. **Given** an issue in `REVIEW` with a `review.changes_requested` event, **When** `transition.py next` runs, **Then** the action is `RETURN_TO_PSE` and `to_state` is `CHANGES_REQUESTED`.
5. **Given** role `pse` requests a transition owned by `review`, **When** `transition.py decide` runs, **Then** `allowed` is `false` with `required_role: review`.
6. **Given** level `shadow`, **When** `labels_plan.py --apply` or `normalize.py serve` runs, **Then** it exits 4.

---

### User Story 7 - Cloud-first runtime configuration and live benchmarks (Priority: P2)

Every Zed profile (Lead, PSE, Review) defaults to an Ollama Cloud model. A local Ollama profile file is
present but disabled. Benchmarks run `--runtime ollama-cloud --jev live` as soon as the network is
allowlisted; without network or keys they report `skipped`/`not_run`, never a pass.

**Why this priority**: The user decided "everything cloud first", and R2's local enablement (L1) needs R1's
live runs as its baseline (roadmap §Inference track).

**Independent Test**: `skill-lab validate --config zed` passes on the shipped template; `skill-lab bench
--runtime ollama-cloud --jev live` without `OLLAMA_API_KEY` reports every agentic and trigger case `skipped`
with reason, and `skill-lab release check --spec SPEC-201` reports G-LIVE-01..05 `not_run`.

**Acceptance Scenarios**:

1. **Given** `skill-lab/config/zed/settings.example.jsonc`, **When** `skill-lab validate --config zed` runs, **Then** all 3 profiles resolve to provider `ollama` and a model id that `skill-lab/config/zed/cloud-models.json` lists as cloud, the provider endpoint is one of the two cloud shapes of FR-039, `available_models` lists no local model, and 0 errors are reported.
2. **Given** `skill-lab/config/zed/local-ollama.disabled.jsonc`, **When** `skill-lab install --inference local` runs on R1, **Then** it exits 4 with `LOCAL_INFERENCE_GATED`.
3. **Given** no `OLLAMA_API_KEY` or `TYPESAFE_API_KEY`/`JEV_API_KEY`, **When** the live benchmark runs, **Then** agentic and trigger cases are `skipped` with reason `LIVE_PREREQ_MISSING`, and no result has `jev_mode: live`.
4. **Given** keys and network, **When** the live benchmark completes, **Then** the run summary and Jev cassettes are written under `skill-lab/specs/201-release-shadow/evidence/bench/` with secrets redacted, and `release check` computes G-LIVE-01..05 from them.

---

### User Story 8 - Standalone export to `Cazador0/skill-factory` (Priority: P2)

`skill-lab/bin/export-repo` assembles a standalone repository root from the working tree, so the factory repo
contains `skills/` and `skill-lab/` and nothing from 12-factor-agents' own content.

**Why this priority**: Step 6 cannot happen without it.

**Independent Test**: Export to an empty temp directory and run validate, sync `--check`, unit tests, and the
deterministic benchmark from inside it.

**Acceptance Scenarios**:

1. **Given** an empty `--out`, **When** `export-repo` runs, **Then** it writes README.md, LICENSE (byte-identical to the working tree's Apache-2.0 `LICENSE`), NOTICE, AGENTS.md, .gitignore, `.github/workflows/ci.yml`, `.claude/settings.json`, `skills/`, `skill-lab/`, and 26 relative symlinks (13 under `.agents/skills/`, 13 under `.claude/skills/`) that resolve inside `--out`.
2. **Given** a non-empty `--out`, **When** `export-repo` runs, **Then** it exits 2 with `EXPORT_OUT_NOT_EMPTY`.
3. **Given** a file under `skills/` containing a value of `GITEA_TOKEN` from the environment, **When** `export-repo` runs, **Then** it exits 4 with `EXPORT_SECRET_DETECTED` and writes nothing.
4. **Given** two exports of the same commit, **When** their manifests are compared, **Then** `manifest_digest` is identical.
5. **Given** an export, **When** `export-repo --check <dir>` runs after one byte changes in an exported file, **Then** it exits 1 with `EXPORT_DRIFT` naming the path.

---

### User Story 9 - Audit and authoring helpers (Priority: P3)

`twelve-factor-audit` scores a repository against the 12 factors read-only, and `skill-forge` scaffolds and
checks new skills locally.

**Why this priority**: Both are complete at R1 (no later capability), and neither blocks delivery.

**Independent Test**: Audit the exported tree; scaffold a skill named `demo-skill` into a scratch `skills/`
and validate it.

**Acceptance Scenarios**:

1. **Given** a repository, **When** `audit.py` runs, **Then** the scorecard has 12 factors with ids 1..12, each score in 0..3, `max_total` 36, and every evidence path exists in the target.
2. **Given** `forge.py new --name demo-skill --apply`, **When** it runs, **Then** the scaffold passes `skill-lab validate --skill demo-skill` with 0 errors.
3. **Given** `forge.py new --name create-skill`, **When** it runs, **Then** it exits 2 with `SKILL_NAME_RESERVED`.

---

### Edge Cases

- `.skill-policy.json` is a symlink, a directory, a FIFO, larger than 64 KiB, not UTF-8, or has a UTF-8 BOM: symlink, non-regular file, oversize, and non-UTF-8 → `shadow` + `POLICY_FILE_INVALID`. A BOM is accepted, because `_skillkit.cli.read_text` reads `utf-8-sig`.
- The policy file changes while a script runs: the policy is loaded once per process and every check in that process uses the loaded value. A plan therefore never applies half its operations under one level and half under another.
- An `--apply` plan mixes allowed local actions and refused actions: the script calls `require()` for every action in the plan before the first side effect and exits 4 without doing any of them (FR-007).
- The project root cannot be determined (no `.git` above cwd): `find_project_root` returns cwd. In R1 the clamp makes the file's content irrelevant to the effective level anyway (synthesis.md D-3).
- `tasks.md` has a dependency cycle: `task-graph.cycles[]` is non-empty, `dev_state.py next` exits 1 with `TASK_GRAPH_CYCLE`, and nothing executes.
- A task references a dependency ID that does not exist: `plan_dag.py` emits a warning `UNKNOWN_DEPENDENCY` and treats the edge as unsatisfiable, so the task never becomes ready.
- Two verdict comments carry the same request marker: `review_collect.py` uses the newest by `created_at`; if it holds more than one fenced `json` block, it exits 2 with `VERDICT_AMBIGUOUS`.
- The reviewer posts no verdict: `review_collect.py` exits 1 with `VERDICT_NOT_FOUND`; the orchestrator keeps polling until its timeout (release-delivery runbook) and then escalates to the human.
- The PR head moves during review: the verdict is stale (`VERDICT_STALE`) and a new review round with a new `review-request.v1` is required.
- A fourth review round is requested: `review_request.py` exits 4 with `REVIEW_ROUNDS_EXHAUSTED`; the human decides.
- Ollama Cloud returns prose or malformed JSON: the agentic case is `schema_valid: false` → `fail` (Ollama Cloud has no structured outputs, SOURCES.md). A network failure mid-case is `error`. Neither counts as pass, and a run with any `error` or `skipped` case cannot satisfy G-LIVE-05.
- Jev returns HTTP 422 or times out: the judgment is `error`, the case is `error`, and nothing is synthesised.
- Python 3.9 lacks a stdlib feature the current Python has: G-OFF-03 catches it, because the suite runs on both.
- `--out` for the export is inside the working tree: refused with `EXPORT_OUT_INSIDE_SOURCE` (exit 2), because the export would include itself.
- The working tree is dirty at export time: the manifest records `dirty: true` and `commit` is the HEAD SHA. The release PR export requires `dirty: false` (G-OFF-10 metric `export.dirty == 0`).

## Requirements *(mandatory)*

### Functional Requirements

**Autonomy policy machinery**

- **FR-001**: `_skillkit.policy.load(project_root, now=None)` MUST read only `<project_root>/.skill-policy.json` and return a `Policy` with `level` (effective), `declared_level`, `source`, `denied`, and `warnings`. A missing file MUST yield `shadow` with no warning. `load` MUST NOT raise for any file content or file type.
- **FR-002**: A policy file that is not a regular file (a symlink, directory, or device), is larger than 65,536 bytes, is not UTF-8, is not strict JSON (duplicate keys, NaN, trailing data), fails `autonomy-policy.v1`, or lists an action id in `overrides.deny` that is not in the catalog MUST yield effective level `shadow` and exactly one warning `POLICY_FILE_INVALID` with the path and a compact reason. It MUST never yield a higher level.
- **FR-003**: The effective level MUST be the lower of the declared level and `policy.SUPPORTED_MAX_LEVEL`. R1 sets `SUPPORTED_MAX_LEVEL = "shadow"`. When the declared level is higher, a warning `POLICY_LEVEL_CLAMPED` MUST be added.
- **FR-004**: `Policy.allows(action)` MUST return `true` only if the action is in the catalog, its minimum level is not `human-only`, it is not in `overrides.deny`, and rank(effective level) ≥ rank(minimum level). Ranks: `shadow`=0 < `agent-implementation`=1 < `guarded-autonomous`=2. `Policy.require(action)` MUST raise `_skillkit.envelope.ScriptError` with `exit_code=4` and the first matching code in this order: `POLICY_UNKNOWN_ACTION`, `POLICY_HUMAN_ONLY`, `POLICY_ACTION_DENIED`, `POLICY_LEVEL_TOO_LOW`. The message MUST name the action, its minimum level, and the effective level, and `path` MUST be `.skill-policy.json`.
- **FR-005**: No environment variable, command-line flag (including `--apply` and `--force`), `--state-dir` content, or file inside a skill folder MAY influence the effective level or remove a deny entry. `policy.py` MUST NOT read `os.environ`.
- **FR-006**: `policy.ACTION_CATALOG` MUST contain exactly the entries in §Autonomy policy (34 actions), each with `id`, `min_level`, `scope`, `risk`, and `summary`. `policy.catalog_document()` MUST return a payload valid against `action-catalog.v1`, with actions sorted by id. Actions whose `min_level` is `human-only` MUST be refused at every level.
- **FR-007**: Every skill script that can perform a catalog action MUST: without `--apply`, emit the plan and exit 0 with no side effect; with `--apply`, call `require()` for every action in the plan before the first side effect (all-or-nothing preflight), and on refusal exit 4 having changed nothing.
- **FR-008**: `_skillkit.gitea` MUST issue only `GET` requests from its read methods. Every non-GET request MUST go through `GiteaClient.send(operation)`, which MUST call `policy.require(operation.action)` before opening a connection. In R1 every non-GET action is refused by the clamp.
- **FR-009**: `skill-lab policy show`, `skill-lab policy explain --action <id>`, and `skill-lab policy catalog` MUST emit `policy-state.v1`, `policy-state.v1` with `query`, and `action-catalog.v1` envelopes respectively.
- **FR-010**: `skill-lab validate` MUST add rule `policy-action-known` (error: a literal action id passed to `require`, `require_all`, `refusals`, or `allows` in a skill script, or named in an `action:<id>` eval tag, is not in the catalog; because the `benchmark-case.v1` tag pattern has no `_`, a tag writes each `_` of the id as `-`, which is reversible since catalog ids never contain `-`) and rule `eval-inventory-r1` (error: a skill has fewer than 4 deterministic, 3 agentic with at least 1 tagged `guardrail`, 4 positive trigger, or 2 negative trigger cases; or an action above `shadow` that its scripts reference is not covered by an `action:<id>` tag on a deterministic case tagged `policy`). `Policy.refusals(actions)` MUST return one compact error per refused action, with the action id first in the message, so a multi-action refusal reports every refused action.
- **FR-011**: `skill-lab policy containment` MUST run every deterministic case tagged `policy` with its `--apply` arguments, at effective level `shadow`, in a sandbox: a temporary copy of the fixture git repository, the Gitea test double with request logging, and a fresh `--state-dir`. It MUST emit `containment-report.v1` counting per attempt the non-GET requests seen by the double, changed git refs, and changed working-tree files outside `--out`/`--state-dir`, and it MUST exit 0 only when every attempt exits 4 with no effect and every (skill, action) pair is covered.
- **FR-012**: The policy file MUST be protected by layered guardrails: the Zed settings template MUST deny agent edits to `.skill-policy.json` (`tool_permissions` always-deny on `edit_file` and on terminal commands that mention it); the exported `.claude/settings.json` MUST deny Edit and Write on it; and `merge-policy-gate` MUST classify any diff touching the policy paths in §Security as `critical`.

**Contracts**

- **FR-013**: The 21 new contracts and 5 additive contract changes in §Contracts MUST exist as `skill-lab/contracts/schemas/<name>.v1.schema.json`, use only the `jsonschema_mini` keyword subset with `additionalProperties: false`, have one valid and at least two invalid example documents each under `skill-lab/tests/fixtures/contracts/r1/`, and be vendored into every skill that emits or consumes them.

**Shared library and test double**

- **FR-014**: `_skillkit.speckit_tasks` MUST parse Spec Kit `tasks.md` (`- [ ] T001 [P] [US1] Description`, checked `[x]`, task id regex `\bT\d{3,}\b`, inline `(depends on T012, T013)`, phase headings Setup → Foundational → user stories → Polish → Convergence) and build a `task-graph.v1` with explicit edges, phase-order edges, waves, cycles, and write-set conflicts from file paths in descriptions.
- **FR-015**: `_skillkit.gitrepo` MUST provide read-only git helpers (`head_sha`, `is_clean`, `diff_names`, `diff_patch`, `refs_digest`, `session_trailers(base, head)`), run git with list arguments only, and refuse any subcommand outside its read-only allowlist with `GIT_COMMAND_FORBIDDEN` (exit 4).
- **FR-016**: `_skillkit.checks.run_check(argv, ...)` MUST execute only when the calling script got `--apply` (action `state.write.local`, because the log lands under `--state-dir`; without it the script returns the planned check), run the command with list arguments, remove every variable in `_skillkit.redact.SECRET_ENV_VARS` from the child's environment (R1 adds `GITEA_WEBHOOK_SECRET`, which FR-025 reads, to that list), refuse the denylisted commands in plan.md §Check denylist with `CHECK_COMMAND_FORBIDDEN` (exit 4) before starting a process, enforce a timeout, write the combined log under `--state-dir`, and return a `check-run.v1` whose `log_digest` is the SHA-256 of the log bytes.
- **FR-017**: `skill-lab/lab/gitea_double.py` MUST serve the read endpoints in plan.md §Gitea test double from a seed fixture over loopback, report version `28.2.0` from `GET /api/v1/version`, append every request to a JSONL log, and answer every non-GET request with HTTP 405 in R1.

**The 13 skills at R1 capability**

- **FR-018**: `lead-architect` MUST provide spec readiness (`spec-readiness.v1`), task DAG with waves and write-set conflicts (`task-graph.v1`), issue-contract render (`issue-contract.v1` plus `rendered-document.v1`), dispatch recommendation (`dispatch-plan.v1` whose `mutation_requests[]` use catalog actions `gitea.issue.assign` and `lease.write.remote`), and arbitration records (`arbitration-record.v1`). `dispatch_recommend.py --apply` and `arbitrate.py --publish --apply` (`gitea.comment.create`) MUST exit 4 at `shadow`.
- **FR-019**: `pse-implementer` MUST provide preflight (`preflight-report.v1`), local checks (`check-run.v1` via `_skillkit.checks`), evidence manifest build and validate (`implementation-evidence.v1` with `head_commit: null` and `patch_ref` in R1), proposed patch (`patch-proposal.v1`, patch file under `--out`), and a delivery plan (`mutation-plan.v1` for `git.worktree.create`, `git.branch.create`, `git.commit`, `git.push.branch`, `gitea.pr.create`) that exits 4 with `--apply` at `shadow`.
- **FR-020**: `review-verifier` MUST provide the requirements matrix (`requirements-matrix.v1`) reconstructed from `spec.md` and traceability, never from the PSE's evidence alone; the quality gate (`quality-gate.v1`, where `not_run` on an applicable category fails); the verdict (`review-verdict.v1`, `APPROVE` only when the quality gate passed, `blockers` is empty, and `requirements.unverified` is 0); the independence check (FR-035); the verdict comment render (`rendered-document.v1`); and a comment plan (`gitea-plan.v1` op with action `gitea.comment.create`, and with `gitea.pr.review.submit` when `--post` is given) that exits 4 with `--apply` at `shadow`.
- **FR-021**: `speckit-gitea-taskstoissues` MUST emit a dry-run `gitea-plan.v1` that creates only missing issues titled `T001: <description>`, deduplicates by the `task-issue-map.v1` file first and then by the task-id regex over open and closed issue titles, adds labels, milestone, and dependency links from inline markers, derives every `idempotency_key` with `_skillkit.ids.idempotency_key(repository, feature, task_id, op)`, and exits 4 with `--apply` at `shadow`.
- **FR-022**: `speckit-gitea-sync` MUST emit a read-only `sync-drift-report.v1` (kinds `missing_issue`, `orphan_issue`, `title_mismatch`, `state_mismatch`, `dependency_mismatch`, `stale_map`) from tasks.md, the map, and an issue list (file or read-only client), plus a comment plan (`gitea-plan.v1`) that exits 4 with `--apply` at `shadow`.
- **FR-023**: `kanban-state-machine` MUST decide transitions for the report's 10 states and their owning roles (`transition-decision.v1`), implement the report's `next_action` function deterministically, and emit scoped-label plans (`state/<name>`, `gitea-plan.v1` op `set_labels`, action `gitea.labels.set`, plus op `move_issue`, action `gitea.project.move_issue`, only when the server's `/swagger.v1.json` exposes project columns) that exit 4 with `--apply` at `shadow`.
- **FR-024**: `work-lease` MUST keep a local lease store under `--state-dir` with file locking and a monotonically increasing `version` for compare-and-swap, detect `write_domains` overlap (`lease-check.v1`), and support `acquire`, `renew`, `release`, `status`, and `check`. The default TTL MUST be 1,800 s (`--ttl`, allowed 300..7,200 s), and `renew` MUST extend `expires_at` by the TTL from `--now` and set `heartbeat_at`. 1,800 s is 3 × the 600 s check timeout (plan.md §Check denylist), so a session that renews every TTL/3 survives one hung check; SPEC-202 inherits this constant and SPEC-203 D-17 adds the heartbeat cadence and the takeover grace on top of it. Local writes require `--apply` (action `state.write.local`); `--mirror` (action `lease.write.remote`, `gitea-plan` op `mirror_lease`) exits 4 at `shadow`.
- **FR-025**: `gitea-event-normalizer` MUST verify `X-Gitea-Signature` (hex HMAC-SHA256 of the raw body) with a constant-time compare, deduplicate by `X-Gitea-Delivery` against a seen set under `--state-dir` (recording requires `--apply`, action `state.write.local`), and emit `normalized-event.v1`. `event_type` MUST come from the fixed vocabulary in `skills/gitea-event-normalizer/references/event-types.md`, which maps `X-Gitea-Event` plus the payload `action` to: `issue.created`, `issue.edited`, `issue.assigned`, `issue.labeled`, `issue.closed`, `issue.reopened`, `pull_request.opened`, `pull_request.synchronized`, `pull_request.closed`, `pull_request.merged`, `review.approved`, `review.changes_requested`, `review.dismissed`, `check.success`, `check.failure`, `push.base` (push to the configured base branch), and `push.branch` (any other push). The raw header and action values are checked against the Gitea 28.x webhook docs at T102 and recorded there, not assumed. A delivery outside the table becomes `unmapped.<header value>` with `blocking: false`. `issue.dependency_resolved` and `reconcile.tick` are derived types that no delivery produces; SPEC-203 emits them. `serve` (action `events.gateway.serve`) MUST exit 4 at `shadow`.
- **FR-026**: `merge-policy-gate` MUST classify risk with the report's 4 classes from changed paths and labels, list `policy_paths_touched`, and emit an advisory `merge-decision.v1` whose `decision` is never `AUTO_MERGE` below `guarded-autonomous` and whose `uncapped_decision` records the risk-only result. `merge_plan.py --apply` (action `gitea.pr.merge_when_checks_succeed`) MUST exit 4 at `shadow`.
- **FR-027**: `session-checkpoint` MUST write (action `state.write.local`), read, render (`rendered-document.v1`), and resume-plan (`resume-plan.v1`) checkpoints that validate against `session-checkpoint.v1`, which rejects any field outside the contract (no chain-of-thought, report §Session checkpoint). `publish` (action `gitea.comment.create`) MUST exit 4 at `shadow`.
- **FR-028**: `twelve-factor-audit` MUST emit a read-only `twelve-factor-scorecard.v1` with factors 1..12, scores 0..3, evidence paths that exist in the target, `max_total` 36, and a grade. Its references paraphrase the factors and link to the upstream text; they quote nothing verbatim (synthesis.md D-19).
- **FR-029**: `skill-forge` MUST scaffold a new skill (`scaffold-plan.v1`; writing requires `--apply`, action `workspace.write`), check an existing skill against CONVENTIONS through the vendored `_skillkit.frontmatter`, and generate eval-case skeletons that meet FR-033's counts. It MUST refuse the name `create-skill` with `SKILL_NAME_RESERVED`.
- **FR-030**: `speckit-development` MUST execute a feature's `tasks.md` in dependency order: compute waves through `_skillkit.speckit_tasks`, present one task per step, run a task's declared verification through `_skillkit.checks` (`dev_state.py check`), mark a task `[x]` (action `workspace.write`) only when every check declared for it has a passing `check-run.v1`, record a `development-report.v1`, refuse to run on a graph with cycles, and emit delivery operations (`git.worktree.create`, `git.branch.create`, `git.commit`, `git.push.branch`, `gitea.pr.create`, `gitea.pr.review.request`, `review.session.request`) as a `mutation-plan.v1` that exits 4 with `--apply` at `shadow`.
- **FR-031**: `speckit-development/scripts/converge.py` MUST follow Spec Kit converge semantics: read spec, plan, and tasks as the sole source of intent; classify findings as `missing`, `partial`, `contradicts`, or `unrequested` with severity CRITICAL/HIGH/MEDIUM/LOW; and with `--apply` only append one `## Phase N: Convergence` section, never rewriting, renumbering, or deleting a task. With zero findings, `tasks.md` stays byte-for-byte unchanged. It MUST emit `convergence-report.v1` with `converged` true exactly when `findings` is empty.
- **FR-032**: Each of the 13 skills MUST satisfy CONVENTIONS §2 and §3 (frontmatter subset, body ≤ 250 lines and ≤ 12 KB, required headings, stdlib-only scripts, envelope output, exit codes), carry `metadata.version` `0.1.0` and `metadata.spec` SPEC-001..SPEC-013, and have `skill-lab/specs/0NN-<name>/spec.md` plus a complete `traceability.json`.
- **FR-033**: Each skill MUST have at least 4 deterministic cases plus 1 `policy`-tagged deterministic case per referenced action above `shadow`; at least 3 agentic cases, at least 1 of them tagged `guardrail`; at least 4 positive and 2 negative trigger cases (at least 1 negative names a neighbouring skill, at least 1 expects `null`); and a `skill-lab/benchmarks/criteria/<name>.json` with the per-skill gates in §Release gates.

**Independent review loop**

- **FR-034**: `speckit-development/scripts/review_request.py` MUST emit `review-request.v1` with a deterministic `request_id`, PR number and URL, repository, head and base ref and SHA, spec ids, round (1..3), author session, reviewer instructions with exact commands, evidence digests, and the required output contract `review-verdict.v1` delivered as a PR comment with the request's marker. A round above 3 MUST exit 4 with `REVIEW_ROUNDS_EXHAUSTED`.
- **FR-035**: The verdict comment MUST be one marker line `<!-- skill-lab:review-verdict:v1 request_id=<id> head=<sha40> -->`, a human summary, and exactly one fenced `json` block holding a `review-verdict.v1` payload. `review_collect.py` MUST select the newest marker comment for the request, parse it strictly, validate the schema, and require `request_id` equal to the request's, `reviewed_commit` equal to the request's head, `reviewer_session` different from the request's `author.session_id`, and the reviewer session id absent from every `Claude-Session:` trailer in `base..head`. It exits 0 only for `APPROVE`.
- **FR-036**: `speckit-development/scripts/review_local.py` MUST plan (without `--apply`) or run (with `--apply`, action `review.local.run`) the read-only fallback reviewer `claude -p <prompt> --output-format json --json-schema <path to vendored review-verdict.v1 schema>` with tools restricted to read-only, a timeout, and the secret environment removed except the CLI's own credentials. It MUST exit 3 `CLAUDE_CLI_NOT_FOUND` when `claude` is not on `PATH`, and hand the output to `review_collect.py --cli-output`. It never posts anything.
- **FR-037**: `skill-lab/docs/runbooks/release-delivery.md` MUST give the exact factory steps 5 to 8: export, branch, push, and PR creation by the orchestrator; reviewer creation with `claude-code-remote` `create_session` (prompt rendered from `review-request.v1`, `source_url`, `source_revision` set to the release branch, never `permission_mode: plan`); polling with `get_session` and `list_events`; verdict collection; at most 3 rounds; `BLOCKED_BY_ENV` handling; and human merge.
- **FR-038**: `speckit-development/scripts/pr_body.py` MUST render the PR body (`rendered-document.v1`) from the development report, convergence report, and release gate report, with a gate table that prints `not run` for `not_run` gates and never `pass`.

**Cloud-first runtime and gates**

- **FR-039**: `skill-lab/config/zed/settings.example.jsonc` MUST default every profile (Lead, PSE, Review) and `agent.default_model` to an Ollama Cloud model, in one of two endpoint shapes, whichever T112 verifies: (b) `language_models.ollama.api_url` `https://ollama.com` with `OLLAMA_API_KEY`; or (a) `http://localhost:11434` served by a local Ollama daemon signed in to ollama.com, with every default model id listed as cloud in `skill-lab/config/zed/cloud-models.json`. Shape (a) is what the foundation template ships today, citing Ollama's authentication docs. In both shapes the inference runs on Ollama Cloud, and `available_models` in the template lists cloud models only. `skill-lab/config/zed/local-ollama.disabled.jsonc` MUST exist and hold every local model (`http://localhost:11434`, context ≥ 32,768 per ADR-0003); T113 moves the local entries the foundation template lists into it. `skill-lab install --inference local` MUST exit 4 `LOCAL_INFERENCE_GATED` in R1. `skill-lab validate --config zed` MUST check these rules.
- **FR-040**: Skills MUST install for Claude Code (`.claude/skills/<name>` symlinks, invoked `/name`) and Codex (`.agents/skills/<name>`, invoked `$name`) through `skill-lab install`, and `skill-lab validate --runtime claude,codex` MUST report 0 errors.
- **FR-041**: Live benchmarks MUST run as `skill-lab bench --runtime ollama-cloud --jev live` over all 13 skills, never rely on Ollama structured outputs, report `skipped` with reason `LIVE_PREREQ_MISSING` when keys or network are absent, write redacted run summaries and Jev cassettes to `skill-lab/specs/201-release-shadow/evidence/bench/`, and label replayed judgments `jev_mode: replay`. A replayed or partial run MUST NOT satisfy any live gate.
- **FR-042**: `skill-lab/specs/201-release-shadow/gates.json` (`release-gates.v1`) MUST define every gate in §Release gates, and `skill-lab release check --spec SPEC-201 [--stage merge|complete|post-review]` MUST emit `release-gate-report.v1` with each gate `pass`, `fail`, or `not_run` (with reason). It MUST exit 0 only when every gate of the requested stage passes.

**Export to `Cazador0/skill-factory`**

- **FR-043**: `skill-lab/bin/export-repo --out DIR` MUST assemble the standalone root (§Contracts `export-manifest.v1`, User Story 8), copy LICENSE byte-identical from the working tree root, use relative symlinks, preserve executable bits, exclude git-ignored and out-of-scope paths, refuse a non-empty or in-source `--out`, refuse secrets and symlinks that escape `--out` (exit 4), emit `export-manifest.v1` with a reproducible `manifest_digest`, and support `--check DIR` (exit 1 `EXPORT_DRIFT`).
- **FR-044**: The exported tree MUST pass `python3 skill-lab/bin/skill-lab validate`, `sync --check`, `test`, and `bench --tier deterministic` from its own root without reading any path outside it. `.github/workflows/ci.yml` MUST run those offline gates on Python 3.9 and the current Python for every push and PR, MUST NOT run live tiers unless started manually with secrets, and MUST NOT merge anything.
- **FR-045**: The repository MUST have a short root `AGENTS.md` (report §Authoritative repository knowledge: what the repo is, principles, where specs and architecture live, how to build and test, what agents may never do, handoff protocol), `skills/README.md`, a generated `skills/CATALOG.json`, and `skill-lab/docs/autonomy.md`, whose action table is generated from `policy.catalog_document()` and tested for drift.

**Decisions on record**

- **FR-046**: ADR-0101..ADR-0105 (§Contracts and plan.md §Constitution check) MUST exist in MADR form, and CONVENTIONS §4 (contract catalog) and §8 (autonomy) MUST be amended to reference them.

### Key Entities

- **Autonomy policy**: the human-owned file `.skill-policy.json` (`autonomy-policy.v1`). Holds the declared level, who set it, when, why, and optional restrict-only overrides.
- **Policy (runtime)**: the immutable object `load()` returns. The effective level is min(declared, release maximum), plus deny set, source, and warnings. It is loaded once per process.
- **Action**: a catalog entry with an id (`gitea.issue.create`), minimum level (`shadow`, `agent-implementation`, `guarded-autonomous`, or the pseudo-level `human-only`), scope, informative risk, and summary.
- **Plan**: a `gitea-plan.v1` (HTTP operations) or `mutation-plan.v1` (git, session, lease operations) that names the catalog action of every operation and what `--apply` would hit.
- **Release gate**: a machine-checkable threshold in `gates.json` with class (offline or live), stage (merge, complete, post-review), metric, operator, threshold, command, and rationale.
- **Review request / verdict comment**: the request the author side emits, and the PR comment the independent reviewer posts, bound together by `request_id` and head SHA.
- **Export manifest**: the reproducible description of the standalone repository the export produced.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: At `shadow`, the containment suite records 0 consequential effects (non-GET requests, ref changes, or working-tree writes outside `--out`/`--state-dir`) across every (skill, action) pair above `shadow`, with at least 1 attempt per pair (roadmap SC-003).
- **SC-002**: For 100 % of the at least 40 enumerated hostile or malformed policy files (10 failure classes × at least 4 variants), the effective level is `shadow` and `load` does not raise.
- **SC-003**: 13 of 13 skills report 0 validation errors on zed, claude, and codex, and the catalog stays at or below 51,200 bytes (Zed `MAX_SKILL_DESCRIPTIONS_SIZE`).
- **SC-004**: 100 % of unit tests pass on Python 3.9 and on the current Python, and 100 % of at least 52 deterministic cases pass.
- **SC-005**: 100 % of FRs in SPEC-001..SPEC-013 and SPEC-201 have at least 1 existing `verified_by` path, and 0 requirements remain `planned: true` at merge.
- **SC-006**: On at least 1 complete live run (`ollama-cloud`, `jev_mode: live`, 0 errored or skipped cases), every skill has at most 1 failed agentic case, guardrail-tagged agentic cases pass 100 %, every skill has at most 1 failed (misrouted) trigger case, and catalog-wide trigger accuracy is ≥ 0.90.
- **SC-007**: 3 of 3 Zed profiles default to an Ollama Cloud model, and the local profile is present and not installed.
- **SC-008**: `converge.py` on SPEC-201 reports 0 findings at merge, and `speckit-development` produced the release's development report, PR body, and review request, all schema-valid.
- **SC-009**: The R1 PR receives an `APPROVE` `review-verdict.v1` for its current head from a session other than the authoring session, accepted by `review_collect.py` with exit 0, within at most 3 review rounds (roadmap SC-002).
- **SC-010**: The export passes every standalone gate from its own root, has 26 resolving symlinks and 0 secret findings, and two exports of the same commit have identical `manifest_digest`.
- **SC-011**: CI is green on the R1 PR head on Python 3.9 and the current Python.

## Release goals

| ID | Goal | Measure | FR | SC | Gates |
|---|---|---|---|---|---|
| RG-1 | Shadow containment is enforced by policy code, not by prompts | 0 consequential effects; 100 % of pairs covered; 0 escalations from hostile files | FR-001..FR-012, FR-017 | SC-001, SC-002 | G-OFF-06, G-OFF-07, G-OFF-03/04 |
| RG-2 | 13 skills ship at R1 capability on Zed, Claude Code, and Codex | 0 validation errors; tests and deterministic cases 100 %; inventory met | FR-013..FR-033, FR-040 | SC-003, SC-004 | G-OFF-01..G-OFF-06 |
| RG-3 | Every requirement is traced to code and verification | 0 uncovered FRs, 0 `planned: true` | FR-032, FR-046 | SC-005 | G-OFF-08 |
| RG-4 | Inference is cloud-first, measured live as soon as the network allows | Config rules 0 errors; live gates per SC-006 on ≥ 1 complete run | FR-039, FR-041, FR-042 | SC-006, SC-007 | G-OFF-09, G-LIVE-01..05 |
| RG-5 | The release is delivered by `/speckit-development` | Development report, 0 convergence findings, schema-valid PR body and review request | FR-030, FR-031, FR-034, FR-038 | SC-008 | G-OFF-12 |
| RG-6 | Independent review works on the R1 PR itself | Independent, head-bound `APPROVE` in ≤ 3 rounds; CI green | FR-020, FR-035..FR-037 | SC-009, SC-011 | G-POST-01, G-POST-02 |
| RG-7 | `Cazador0/skill-factory` is a standalone, reproducible export | Standalone gates pass; 26 symlinks; 0 secrets; reproducible digest | FR-043..FR-045 | SC-010 | G-OFF-10, G-OFF-11 |

## Release gates

All gates are defined machine-readably in `skill-lab/specs/201-release-shadow/gates.json` and evaluated by
`python3 skill-lab/bin/skill-lab release check --spec SPEC-201 --stage <stage>`. A gate's status is
`pass`, `fail`, or `not_run`. **`not_run` never counts as `pass`** (CONVENTIONS §9, ADR-0010, report
§Merge evidence gate). "Offline" gates need no network. "Live" gates need `ollama.com` and
`api.typesafe.ai` (allowlisted by the user), plus `OLLAMA_API_KEY` and `TYPESAFE_API_KEY` (alias `JEV_API_KEY`).

**Stages** (aligned with SPEC-202's two exit states):

- `merge`: all offline gates. The independent reviewer may return `APPROVE` only when every `merge` gate passes.
- `complete`: the live gates. If they ran before review, a `fail` blocks the merge: the reviewer returns `CHANGES_REQUESTED`, because a failed capability gate is a defect. If they are `not_run`, the reviewer records them as explicitly not applicable to the merge decision (report: "the applicability decision itself must be explicit"), and R1 is **merged, live-pending** until they pass.
- `post-review`: evaluated by the orchestrator after the verdict.

| Gate | Stage | Class | Metric | Threshold | How measured (lab command) | Rationale |
|---|---|---|---|---|---|---|
| G-OFF-01 | merge | offline | `validate.errors` | = 0 | `skill-lab validate --runtime zed,claude,codex` | Zed, Claude Code, and Codex limits are hard limits; a single error means a skill may not load (SOURCES.md Zed) |
| G-OFF-02 | merge | offline | `sync.drift` | = 0 | `skill-lab sync --check` | A stale vendored `policy.py` would enforce an old catalog |
| G-OFF-03 | merge | offline | `tests.failed + tests.errored` on Python 3.9; `tests.ran` ≥ 1 | = 0 | `python3.9 skill-lab/bin/skill-lab test` (CI matrix) | CONVENTIONS §9.3; 3.9 is the floor. Missing interpreter ⇒ `not_run` ⇒ blocks |
| G-OFF-04 | merge | offline | same, current Python | = 0 | `python3 skill-lab/bin/skill-lab test` | CONVENTIONS §9.3 |
| G-OFF-05 | merge | offline | `bench.deterministic.pass_rate`; `bench.deterministic.cases` | = 1.0; ≥ 52 | `skill-lab bench --tier deterministic` | Scripts are deterministic, so any failure is a bug; 52 = 13 skills × CONVENTIONS minimum 4 |
| G-OFF-06 | merge | offline | `inventory.violations` | = 0 | `skill-lab validate --rule eval-inventory-r1` | Counts above CONVENTIONS minimums give the live thresholds statistical meaning (synthesis.md D-20) |
| G-OFF-07 | merge | offline | `containment.violations`; `containment.uncovered_pairs` | = 0; = 0 | `skill-lab policy containment` | Roadmap SC-003: 0 consequential mutations at `shadow` |
| G-OFF-08 | merge | offline | `trace.uncovered`; `trace.planned` | = 0; = 0 | `skill-lab validate --specs` | CONVENTIONS §6 and §9.5; planned paths must have become real |
| G-OFF-09 | merge | offline | `config.errors` | = 0 | `skill-lab validate --config zed,claude` | User decision "everything cloud first"; policy-file deny rules present |
| G-OFF-10 | merge | offline | `export.drift`; `export.secret_findings`; `export.symlinks_resolved`; `export.dirty` | = 0; = 0; = 26; = 0 | `skill-lab/bin/export-repo --out $T && skill-lab/bin/export-repo --check $T` | 26 = 13 skills × 2 discovery roots (`.agents/skills`, `.claude/skills`) |
| G-OFF-11 | merge | offline | `export.gate_failures` | = 0 | `skill-lab release check --stage merge --root $T --only G-OFF-01,G-OFF-02,G-OFF-04,G-OFF-05` | Proves the factory repo stands alone (`git subtree split` design, CONVENTIONS §1) |
| G-OFF-12 | merge | offline | `converge.findings` | = 0 | `python3 skills/speckit-development/scripts/converge.py --feature skill-lab/specs/201-release-shadow` | Spec Kit: converged means no remaining gaps |
| G-LIVE-01 | complete | live | max over skills of `bench.agentic.failed` (SPEC-104 vocabulary) | ≤ 1 | `skill-lab bench --runtime ollama-cloud --jev live --tier agentic` | ≥ 3 cases per skill (FR-033). A count tolerates exactly 1 capability miss per skill under model nondeterminism at any case count; a rate cannot (0.67 would reject 2/3 = 0.667, which is why the count is used; SPEC-202 and SPEC-203 use the same metric) |
| G-LIVE-02 | complete | live | `bench.agentic.tag:guardrail.pass_rate` | = 1.0 | same run, computed by `release check` from case tags | Guardrail cases encode invariants (no mutation claims, no fabricated evidence); an invariant is not probabilistic |
| G-LIVE-03 | complete | live | max over skills of `bench.trigger.failed` (misroutes; SPEC-104 vocabulary) | ≤ 1 | `skill-lab bench --runtime ollama-cloud --jev live --tier trigger` | ≥ 6 cases per skill (FR-033); exactly 1 misroute per skill is tolerated at any case count, the same rule as G-LIVE-01 |
| G-LIVE-04 | complete | live | `bench.trigger.catalog_accuracy` | ≥ 0.90 | same run | ≥ 78 cases; caps total misroutes at 7, so per-skill tolerance cannot compound (13 × 1 miss = 0.83 < 0.90 fails) |
| G-LIVE-05 | complete | live | `bench.live.errored + bench.live.skipped` with `runtime=ollama-cloud`, `jev_mode=live` | = 0 | same run(s) | A run with errors or skips is incomplete; partial runs never count |
| G-POST-01 | post-review | live | `ci.failed + ci.pending` on the PR head | = 0 | `skill-lab release check --stage post-review --ci-checks <file>` (file from the GitHub checks list) | Roadmap step 8: CI green |
| G-POST-02 | post-review | live | `review_collect` exit code | = 0 | `python3 skills/speckit-development/scripts/review_collect.py --request <rr.json> --comment-file <c.md> --repo-dir .` | Roadmap step 7 and SC-002 |

Per-skill criteria files (`skill-lab/benchmarks/criteria/<skill>.json`, `success-criteria.v1`) carry the
per-skill share of these gates, so that `skill-lab score` never rejects a run the release gates accept. Each file
keeps the SPEC-104 defaults `static-score`, `unit-tests`, `deterministic-all-pass`, and `deterministic-schema-valid`,
adds `tests.failed = 0`, and replaces four optional defaults **by id** (SPEC-104 FR-007 keeps their optionality, so
offline scoring skips them with a reason):

| Default id (SPEC-104) | Default | Per-skill replacement | Why |
|---|---|---|---|
| `agentic-quality` | `bench.agentic.pass_rate ≥ 0.8` | `bench.agentic.failed ≤ 1` | G-LIVE-01; at the 3 or 4 agentic cases most skills have, 0.8 admits no miss (2/3 = 0.67, 3/4 = 0.75) |
| `trigger-routing` | `bench.trigger.accuracy ≥ 0.9` | `bench.trigger.failed ≤ 1` | G-LIVE-03; at 6–8 cases, 0.9 admits no misroute |
| `agentic-schema-valid` | `bench.agentic.schema_valid_rate ≥ 0.95` | `bench.agentic.schema_valid_rate ≥ 0.66` | A schema-invalid output is already a failed case, so G-LIVE-01 bounds it; 0.66 never rejects what `failed ≤ 1` accepts at 3–6 cases (2/3 passes) |
| `jev-uncertain` | `bench.jev.uncertain_rate ≤ 0.1` | `bench.jev.uncertain_rate ≤ 0.34` | An uncertain judgment already fails its case (CONVENTIONS §5); 0.34 admits the one tolerated miss at 3 judgments (1/3) |

The metric names follow SPEC-104's vocabulary (`bench.<tier>.failed` is in its `KNOWN_METRICS`). T001 confirms them,
and plan.md §Interface alignment records any rename. The criteria files are critical policy paths.

The live run needs to pass once in R1. That single run is the baseline. SPEC-202's L1 local enablement
requires the same gates on 3 consecutive cloud runs. R1 records every complete live run with its suite digest, date, and model, so that SPEC-202 can count R1's runs toward a streak for the same suite. SPEC-202 D-17 decides that a different suite starts a new streak.

## Non-goals

- Any consequential write by a skill script: no Gitea write, commit, push, PR, review post, label change, remote lease, or merge (all R2/R3).
- Raising `SUPPORTED_MAX_LEVEL` above `shadow` (R2 raises it, after adding base-branch verification of the policy file, synthesis.md D-3).
- Enabling local Ollama inference (SPEC-202 L1).
- Webhook serving, event-driven loops, lease takeover, auto-merge (R3).
- A Gitea MCP server. R1 has a narrow stdlib client; report §Gitea as control plane recommends a semantic tool surface, and R2/R3 grow it.
- Write endpoints in the Gitea test double (SPEC-202 extends the R1 double).
- A GitHub Actions job that enforces the review verdict as a required status check. The human merge is the enforcement point in R1 (synthesis.md D-12).
- Agents merging the factory repository (roadmap non-goal), storing chain-of-thought, persona pedigree prompts.

## Contracts

Canonical schemas go in `skill-lab/contracts/schemas/<name>.v1.schema.json` (JSON Schema draft 2020-12, `$id`
`urn:skill-lab:schema:<name>:v1`, CONVENTIONS §4). All of them use `schema_version: 1` and
`additionalProperties: false` at every level, with no `x_ext` extension point. **New contracts in R1** (core
fields; the schemas are authoritative once written):

| Contract | Producer → consumer | Fields |
|---|---|---|
| `autonomy-policy` | human → `_skillkit.policy` (file `.skill-policy.json`, not wrapped in an envelope) | `schema_version` (const 1); `level` (enum `shadow`, `agent-implementation`, `guarded-autonomous`); `set_by` (1–128 chars, no control chars; forge username of the human); `set_at` (date-time); `reason` (1–500 chars); `overrides?` {`deny`: [action id, unique, ≤ 64 items, pattern `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$` (the `mutation-request.action` pattern)]} |
| `action-catalog` | `skill-lab policy catalog` → docs, review, tests | `catalog_version` (semver); `levels` (prefixItems const `shadow`, `agent-implementation`, `guarded-autonomous`); `supported_max_level`; `actions[{id, min_level (levels ∪ `human-only`), scope (`local-state`, `local-workspace`, `local-git`, `remote-git`, `forge`, `coordination`, `runtime`, `policy`), risk (`low`…`critical`), summary ≤ 200, introduced_in}]` sorted by id |
| `policy-state` | `skill-lab policy show/explain` → human | `effective_level`, `declared_level` (string or null), `supported_max_level`, `source` (string or null), `set_by` (or null), `set_at` (or null), `denied[]` (sorted), `catalog_version`, `query?` {`action`, `allowed`, `code` (or null), `min_level`} |
| `mutation-plan` | pse, speckit-development, review_local → human/orchestrator | `autonomy_level`; `requests[]` (`mutation-request.v1` items, copied into `$defs`); `required_actions[]` (sorted, unique); `allowed_now` (bool); `refusals[{action, code}]` |
| `check-run` | `_skillkit.checks` (pse `run_check.py`, speckit-development `dev_state.py check`, review re-runs) → evidence | `check_id` (`chk-` + 16 hex); `name`; `argv[]`; `cwd` (relative); `started_at`; `duration_ms`; `exit_code` (int or null on timeout); `status` (`passed`, `failed`, `timeout`); `log_path` (relative to `--state-dir`); `log_digest` (`sha256:`…); `env_removed[]` (names only, sorted); `head_commit` (string or null) |
| `preflight-report` | pse `preflight.py` → pse, lead | `issue` (int or null); `spec_id`; `task_ids[]`; `base_commit`; `working_tree_clean`; `contract_complete`; `ambiguities[{path, line, text}]`; `lease{required, held (bool or null)}`; `checks[{id, status pass/fail/na, message}]`; `ready` |
| `patch-proposal` | pse `propose_patch.py` → review, human | `spec_id`; `issue` (or null); `task_ids[]`; `base_commit`; `patch{path, sha256, bytes}`; `files[{path, change added/modified/deleted/renamed, in_scope, write_domain (or null)}]`; `scope_ok`; `out_of_scope[]` |
| `lease-check` | work-lease → lead, pse | `requested{resource{type, id}, role, session_id, write_domains[]}`; `conflicts[{lease_id, resource, overlapping_domains[]}]`; `grantable`; `autonomy_level` |
| `resume-plan` | session-checkpoint → successor session | `checkpoint{path, sha256}`; `role`; `session_id`; `verified[{id branch_exists/head_matches/lease_valid/issue_open, status pass/fail/na, detail}]`; `stale`; `next_action`; `blockers[]` |
| `dispatch-plan` | lead `dispatch_recommend.py` → human/orchestrator | `feature`; `wave` (int ≥ 0); `recommendations[{task_ids[], issue (or null), role (const `pse`), write_domains[], reason, mutation_requests[]}]`; `deferred[{task_id, reason (blocked_by_dependency, write_conflict, lease_held, not_ready), detail}]`; `autonomy_level` |
| `arbitration-record` | lead `arbitrate.py` → pse, review, human | `arbitration_id`; `pr`; `issue`; `positions[{role pse/review, summary, evidence[]}]` (≥ 2); `spec_refs[]` (requirement ids or `path:line`, ≥ 1); `decision` (`uphold_review`, `uphold_pse`, `amend_spec`, `escalate_human`); `rationale` (≤ 1000); `follow_ups[{owner, action}]`; `decided_by` (const `lead`); `decided_at` |
| `requirements-matrix` | review `requirements_matrix.py` → review | `spec_id`; `source{path, sha256}`; `requirements[{id (FR/NFR/SC-NNN), kind, text, verification[{kind test/eval/check/manual, ref, status passed/failed/not_run}], status covered/failed/unverified}]`; `summary{covered, failed, unverified}` |
| `rendered-document` | any render step → human, PR | `doc_kind` (`pr-body`, `verdict-comment`, `review-prompt`, `checkpoint`, `issue-body`); `path`; `sha256`; `bytes`; `sources[{artifact, sha256}]` |
| `development-report` | speckit-development `dev_state.py` → review, PR body | `spec_id`; `feature_dir`; `tasks{path, sha256}`; `autonomy_level`; `graph_digest`; `waves[[ids]]`; `next_wave[]`; `tasks_status[{id, status done/pending/blocked/failed, check_ids[]}]`; `counts{total, done, pending, blocked, failed}` |
| `convergence-report` | speckit-development `converge.py` → review (quality gate `spec.converged`) | `spec_id`; `inputs{spec, plan, tasks: {path, sha256}}`; `checked{requirements, acceptance_scenarios, plan_decisions, tasks}`; `findings[{id F\d+, gap_type missing/partial/contradicts/unrequested, severity CRITICAL/HIGH/MEDIUM/LOW, source_ref, evidence, remaining_work, origin deterministic/model}]`; `converged` (true iff findings empty); `appended` ({phase, task_ids[]} or null) |
| `review-request` | speckit-development `review_request.py` → reviewer session | `request_id` (`rr-` + 16 hex, digest of repository, PR, head SHA, round); `created_at`; `round` (1..3); `release?` (`R1`/`R2`/`R3`); `repository{forge github/gitea, host, full_name}`; `pr{number, url}`; `head{ref, sha}`; `base{ref, sha}`; `spec_ids[]` (pattern `^SPEC-\d{3}$`, ≥ 1); `author{session_id, runtime}`; `instructions{summary ≤ 2000, commands[{id, argv[], expect_exit}] ≤ 20, must_not[]}`; `evidence[{artifact, sha256}]`; `required_output{contract (const review-verdict URN), schema_path, delivery pr-comment/stdout, comment_marker}` |
| `scaffold-plan` | skill-forge → human | `skill`; `root`; `files[{path, sha256, action create/skip}]`; `applied` |
| `containment-report` | `skill-lab policy containment` → release check | `level` (const `shadow`); `pairs[{skill, action}]`; `attempts[{skill, case_id, action, exit_code, code, effects{http_non_get, refs_changed, files_changed[]}, contained}]`; `summary{pairs, attempts, contained, violations, uncovered_pairs[]}` |
| `export-manifest` | `export-repo` → reviewer, CI | `source{commit, dirty}`; `target{repository, layout_version}`; `files[{path, sha256, size, mode 100644/100755}]` (sorted); `symlinks[{path, target}]` (sorted); `excluded[{pattern, reason}]`; `counts{files, symlinks, skills}`; `manifest_digest` (sha256 of canonical files and symlinks only, so the timestamp does not change it) |
| `release-gates` | release spec (`gates.json`) → release check | `release`; `spec_id`; `gates[{id (^G-(OFF\|LIVE\|POST)-\d{2}$), title, class offline/live, stage merge/complete/post-review, metric, op eq/gte/lte, threshold, scope release/per-skill, command[], rationale}]` |
| `release-gate-report` | `skill-lab release check` → reviewer, PR body | `release`; `spec_id`; `commit`; `autonomy_level`; `gates[{id, stage, class, metric, op, threshold, actual (number or null), status pass/fail/not_run, reason (required unless pass), evidence[{artifact, sha256}], per_skill?[{skill, actual, status}]}]`; `summary{merge, complete, post_review: {total, passed, failed, not_run}}`; `merge_ready`; `complete` |

**Changed contracts (additive, v1 kept)**, synthesis.md D-21:

| Contract | Change | Why |
|---|---|---|
| `review-verdict` | optional `request_id`; optional `reviewer{mode (cloud-session/cli-fallback/interactive-session), runtime (claude-code/zed/codex/other), model?}`. The reviewer's session id stays in the existing `reviewer_session` field; there is no `reviewer.session_id`. `interactive-session` is a human-started Review thread (for example a Zed Review profile), first used by SPEC-202's `review-post.v1` | Binds a verdict to its request and makes independence checkable; `reviewer.mode` is the field SPEC-202 and SPEC-203 read, with the same three values |
| `mutation-request` | `action` keeps its schema pattern and must also be a catalog id (semantic check in `policy`, `POLICY_UNKNOWN_ACTION`); optional `required_level` | Plans name catalog actions |
| `gitea-plan` | optional `operations[].action` (catalog id); every R1 producer sets it, and a lab test asserts that | `require()` needs the action per operation |
| `implementation-evidence` | `head_commit` becomes string or null (null = uncommitted R1 proposal); optional `patch_ref{path, sha256}` | R1 has no commit; evidence never invents one |
| `merge-decision` | optional `autonomy_level`; optional `uncapped_decision` | Shadow-mode calibration data for R3 promotion (report §Core metrics) |

**`gitea-plan` op vocabulary** (every R1 producer uses exactly these `op` names and sets `action`; SPEC-202's
plan applier allow-lists them). The paths are Gitea 28.x REST under `/api/v1`. Only the dependency endpoint is
in SOURCES.md; T023 checks the others against `/swagger.v1.json`, and T025 records any correction.

| `op` | `action` | Request | Producer (R1, plan only) |
|---|---|---|---|
| `define_label` | `gitea.label.define` | `POST /repos/{owner}/{repo}/labels` | tasks_to_issues |
| `create_issue` | `gitea.issue.create` | `POST /repos/{owner}/{repo}/issues` | tasks_to_issues |
| `update_issue` | `gitea.issue.update` | `PATCH /repos/{owner}/{repo}/issues/{index}` | none in R1 (SPEC-202) |
| `set_labels` | `gitea.labels.set` | `PUT /repos/{owner}/{repo}/issues/{index}/labels` (full set; only `state/*` changes) | tasks_to_issues, labels_plan |
| `set_milestone` | `gitea.milestone.set` | `PATCH /repos/{owner}/{repo}/issues/{index}` (`milestone`) | tasks_to_issues |
| `set_dependency` | `gitea.issue.dependency.set` | `POST /repos/{owner}/{repo}/issues/{index}/dependencies` (`IssueMeta`) | tasks_to_issues |
| `move_issue` | `gitea.project.move_issue` | project-column endpoint when `/swagger.v1.json` exposes it; otherwise not planned (labels fallback) | labels_plan |
| `create_comment` | `gitea.comment.create` | `POST /repos/{owner}/{repo}/issues/{index}/comments` | comment_plan, review_verdict, checkpoint publish, arbitrate `--publish` |
| `mirror_lease` | `lease.write.remote` | `POST /repos/{owner}/{repo}/issues/{index}/comments` (marked lease comment only) | work-lease `lease.py --mirror`; lead `dispatch_recommend.py` (inside its `mutation_requests[]`) |
| `submit_review` | `gitea.pr.review.submit` | `POST /repos/{owner}/{repo}/pulls/{index}/reviews` | review_verdict `--post` |
| `merge_when_checks_succeed` | `gitea.pr.merge_when_checks_succeed` | `POST /repos/{owner}/{repo}/pulls/{index}/merge` with `merge_when_checks_succeed: true` | merge_plan |

**Consumed unchanged**: `envelope`, `task-graph`, `spec-readiness`, `issue-contract`, `quality-gate`,
`session-checkpoint`, `normalized-event`, `lease`, `transition-decision`, `task-issue-map`,
`sync-drift-report`, `twelve-factor-scorecard`, `validation-report`, `benchmark-case`, `benchmark-result`,
`benchmark-run`, `success-criteria`, `skill-score`.

## Error semantics

Exit codes follow CONVENTIONS §3 (0 ok, 1 checked-and-failed, 2 usage/input, 3 external, 4 refused). Errors are
compact `{code, message, path}` objects. New codes:

| Code | Exit | Raised by | Meaning |
|---|---|---|---|
| `POLICY_UNKNOWN_ACTION` | 4 | `policy.require` | Action id not in the catalog (fail closed) |
| `POLICY_HUMAN_ONLY` | 4 | `policy.require` | Action is never available to agents |
| `POLICY_ACTION_DENIED` | 4 | `policy.require` | Action is in `overrides.deny` |
| `POLICY_LEVEL_TOO_LOW` | 4 | `policy.require` | Effective level below the action's minimum |
| `POLICY_FILE_INVALID` | warning | `policy.load` | File unusable; effective level forced to `shadow` |
| `POLICY_LEVEL_CLAMPED` | warning | `policy.load` | Declared level above the release maximum |
| `GIT_COMMAND_FORBIDDEN` | 4 | `_skillkit.gitrepo` | Non-read-only git subcommand requested |
| `CHECK_COMMAND_FORBIDDEN` | 4 | `_skillkit.checks` | Denylisted command; no process started |
| `CHECK_TIMEOUT` | 1 | `_skillkit.checks` | Payload `status: timeout`, `exit_code: null` |
| `CHECK_NOT_EXECUTED` | 1 | `evidence_manifest.py` | Evidence claims a check with no matching `check-run` |
| `SCOPE_VIOLATION` | 1 | `propose_patch.py` | Changed path outside `write_domains` |
| `TASK_NOT_VERIFIED` | 1 | `dev_state.py mark` | Declared checks missing or failing |
| `TASK_GRAPH_CYCLE` | 1 | `dev_state.py` | Cycle in tasks; nothing executes |
| `REVIEW_NOT_INDEPENDENT` | 4 | `review_verdict.py`, `review_collect.py` | Reviewer equals the author or authored a commit in range |
| `REVIEW_ROUNDS_EXHAUSTED` | 4 | `review_request.py` | Round > 3; human decides |
| `VERDICT_NOT_FOUND` | 1 | `review_collect.py` | No marker comment for the request yet |
| `VERDICT_STALE` | 1 | `review_collect.py` | `reviewed_commit` ≠ current head |
| `VERDICT_AMBIGUOUS` | 2 | `review_collect.py` | More than one fenced `json` block |
| `VERDICT_SCHEMA_INVALID` | 2 | `review_collect.py` | Block fails `review-verdict.v1` |
| `CLAUDE_CLI_NOT_FOUND` / `CLAUDE_CLI_FAILED` | 3 | `review_local.py` | Fallback reviewer unavailable or failed |
| `SIGNATURE_INVALID` | 1 | `normalize.py` | HMAC mismatch; payload `signature_verified: false` |
| `GITEA_UNREACHABLE` / `GITEA_AUTH` | 3 | `_skillkit.gitea` | Network or 401/403 on a read |
| `GITEA_VERSION_UNTESTED` | warning | `_skillkit.gitea` | Server version below 28.0.0 |
| `LIVE_PREREQ_MISSING` | case `skipped` | bench | Keys or network absent |
| `LOCAL_INFERENCE_GATED` | 4 | `skill-lab install --inference local` | L1 gate not passed (SPEC-202) |
| `SKILL_NAME_RESERVED` | 2 | `forge.py` | `create-skill` and other reserved names |
| `EXPORT_OUT_NOT_EMPTY` / `EXPORT_OUT_INSIDE_SOURCE` | 2 | `export-repo` | Unsafe output location |
| `EXPORT_SECRET_DETECTED` / `EXPORT_SYMLINK_ESCAPE` | 4 | `export-repo` | Nothing is written |
| `EXPORT_DRIFT` | 1 | `export-repo --check` | First differing path reported |
| `RELEASE_GATES_FAILED` | 1 | `release check` | At least one gate of the stage is `fail` or `not_run` |

Policy refusals never print a plan on stdout in the same envelope. To see the plan, the caller re-runs
without `--apply`. That keeps "refused" (exit 4) and "planned" (exit 0) distinguishable to any consumer.

## Security

- **Authority boundary**: `_skillkit.policy` is a guardrail inside the scripts. The security boundary is still the forge's branch protection plus human merge (CONVENTIONS §7, report §Safe autonomous merge). In R1 nothing a skill does can mutate a remote, because `SUPPORTED_MAX_LEVEL` is `shadow` and the Gitea client cannot send a non-GET without `require()`.
- **Policy paths classified `critical`** by `merge-policy-gate`: `.skill-policy.json`; `skill-lab/shared/_skillkit/policy.py` and every vendored `skills/*/scripts/_skillkit/policy.py`; `skill-lab/contracts/schemas/autonomy-policy.v1.schema.json` and `action-catalog.v1.schema.json`; `skill-lab/benchmarks/criteria/**`; `skill-lab/specs/*/gates.json`; `.github/workflows/**`, `.gitea/workflows/**`; `skill-lab/config/**`; `.claude/settings.json`; `CODEOWNERS`; `skills/review-verifier/**` (the reviewer's own gates, report §Safe autonomous merge).
- **No escape hatches**: no environment variable, flag, state file, or skill-local file affects the level (FR-005). `overrides` can only deny. An invalid file falls to `shadow`.
- **Secrets** come only from environment variables. `_skillkit.redact` masks them in all output. `run_check` and `review_local` strip `SECRET_ENV_VARS` from child processes (except the Claude CLI's own credential, which the fallback needs). The export scans every file for the live values of `SECRET_ENV_VARS` and the redact token patterns, and refuses on a match.
- **Untrusted text**: issue bodies, PR comments (including verdict comments), webhook payloads, fixtures, and model output are data. They are parsed with the strict JSON reader (no duplicate keys) and never evaluated, and never reach a shell. The reviewer prompt quotes the review request as data and tells the reviewer to treat repository text as untrusted (report §Agentic-framework verification, prompt-injection resilience).
- **Independence**: author and reviewer are different sessions, proven by session ids and `Claude-Session:` commit trailers (FR-035). The posting identity on GitHub may be the same human account, which is why identity alone is never used as proof (synthesis.md D-12).
- **Webhook verification**: HMAC-SHA256 over the raw bytes, `hmac.compare_digest`, secret from `GITEA_WEBHOOK_SECRET`, which R1 adds to `_skillkit.redact.SECRET_ENV_VARS` (T022) so it is masked and stripped from child processes; an unverified event is `blocking: true` and must not drive a transition.
- **Gitea token**: R1 needs none. If one is supplied for live reads, use a read-scoped token (scope names to be verified against the Gitea 28.x docs at T025).
- **Git**: the git helpers allow read-only subcommands only. `run_check` denies git write subcommands and forge CLIs. Both are guardrails; in IDE runtimes, the terminal tool's confirm/deny settings remain the operator's control.

## Runtime compatibility

| Runtime | Discovery and invocation | Inference (R1) | Notes |
|---|---|---|---|
| **Zed Agent + Ollama Cloud** (priority 1) | `.agents/skills/<name>` symlinks in a trusted worktree; flat folders; the `skill` tool loads SKILL.md; `/speckit-development` | Default for Lead, PSE, and Review profiles: an Ollama Cloud model, reached through `api_url` `https://ollama.com` with `OLLAMA_API_KEY`, or through a local daemon signed in to ollama.com (FR-039; T112 decides) | Ollama Cloud has **no structured outputs**: skills never depend on `format`; scripts produce the JSON and the model relays it. Cloud models run at max context. Zed cannot edit skill folders, so scripts never write inside them |
| Zed Agent + local Ollama (priority 2, **disabled**) | same | `local-ollama.disabled.jsonc`; not installable in R1 | Enabled only by SPEC-202 L1. Zed's default `num_ctx` is 4096, so the file sets ≥ 32,768 (ADR-0003). SKILL.md ≤ 250 lines keeps headroom |
| Claude Code | `.claude/skills/<name>` symlinks; `/name`, `/speckit-development` | Claude models | Hosts the independent reviewer (cloud session or `claude -p` fallback) |
| Codex | `.agents/skills` from cwd up to the repo root, symlinks followed; `$name`, `$speckit-development` | Codex models | Spec Kit commands use `$speckit-*` in Codex skills mode (report §Spec Kit) |

Every procedure step is one tool call that names one script, with no parallel tool calls and no long
intermediate state (CONVENTIONS §2), so a small cloud or local model can follow it.

## Autonomy policy

**Scope**: `.skill-policy.json` governs what **skill scripts** do to a **target project** (its git
repository, its Gitea, its leases). The factory's own delivery to `Cazador0/skill-factory` (export, push,
PR, reviewer session, verdict comment) is done by the build orchestrator under the user's explicit
instruction and Claude Code's permission system, and the merge stays human (synthesis.md D-1). Inside a
target project, R1 means:

- **Allowed at `shadow`** (with `--apply` where noted): reading anything; writing under `--out`; and the
  three local catalog actions `state.write.local` (leases, seen sets, checkpoints, and the logs of local
  checks run through `_skillkit.checks`, which also scrubs the credentials that could reach outside the
  machine), `workspace.write`, and `review.local.run`.
- **Refused at `shadow`** (exit 4 with `--apply`, plan without it): every action with a minimum level
  above `shadow`.
- **Refused at every level**: `human-only` actions.

**Action catalog** (`_skillkit.policy.ACTION_CATALOG`, `catalog_version` 1.0.0, 34 actions). "R1 requester"
names the scripts whose plans include the action.

| Action id | Min level | Scope | Risk | R1 requester (planned or refused) |
|---|---|---|---|---|
| `state.write.local` | shadow | local-state | low | work-lease `lease.py`, session-checkpoint `checkpoint.py write`, gitea-event-normalizer `normalize.py --apply` (seen set), pse-implementer `run_check.py`, speckit-development `dev_state.py check` |
| `workspace.write` | shadow | local-workspace | low | speckit-development `dev_state.py mark`, `converge.py --apply`; skill-forge `forge.py new` |
| `review.local.run` | shadow | runtime | low | speckit-development `review_local.py` |
| `git.worktree.create` | agent-implementation | local-git | medium | pse `delivery_plan.py`, speckit-development `delivery_plan.py` |
| `git.branch.create` | agent-implementation | local-git | low | same |
| `git.commit` | agent-implementation | local-git | medium | same |
| `git.push.branch` | agent-implementation | remote-git | medium | same (own `agent/<role>/<issue>-<slug>` branch only, enforced in R2) |
| `git.push.force_own_branch` | guarded-autonomous | remote-git | high | (R3 rebase-on-base) |
| `git.push.protected` | human-only | remote-git | critical | none |
| `gitea.issue.create` | agent-implementation | forge | medium | taskstoissues `tasks_to_issues.py` |
| `gitea.issue.update` | agent-implementation | forge | low | none in R1 (R2 drift remediation) |
| `gitea.issue.assign` | agent-implementation | forge | low | lead `dispatch_recommend.py` |
| `gitea.issue.close` | guarded-autonomous | forge | medium | (R3 complete-and-unlock) |
| `gitea.issue.dependency.set` | agent-implementation | forge | medium | taskstoissues |
| `gitea.label.define` | agent-implementation | forge | low | taskstoissues (fixed `state/*`, `spec/*`, `story/*` vocabulary only) |
| `gitea.labels.set` | agent-implementation | forge | low | taskstoissues; kanban `labels_plan.py` |
| `gitea.milestone.set` | agent-implementation | forge | low | taskstoissues |
| `gitea.project.move_issue` | agent-implementation | forge | low | kanban `labels_plan.py` (when the server exposes project columns) |
| `gitea.comment.create` | agent-implementation | forge | low | sync `comment_plan.py`; review `review_verdict.py`; checkpoint `checkpoint.py publish`; lead `arbitrate.py --publish` |
| `gitea.pr.create` | agent-implementation | forge | medium | pse and speckit-development `delivery_plan.py` |
| `gitea.pr.update` | agent-implementation | forge | low | none in R1 (R2 PR body updates) |
| `gitea.pr.review.request` | agent-implementation | forge | low | speckit-development `delivery_plan.py` |
| `gitea.pr.review.submit` | agent-implementation | forge | medium | review `review_verdict.py --post` |
| `gitea.pr.review.dismiss` | guarded-autonomous | forge | high | (R3 stale-approval invalidation) |
| `gitea.pr.merge_when_checks_succeed` | guarded-autonomous | forge | high | merge-policy-gate `merge_plan.py` |
| `gitea.pr.merge` | human-only | forge | critical | none ("Force-merge tool for agents: NOT EXPOSED", report §Safe autonomous merge) |
| `gitea.branch_protection.update` | human-only | forge | critical | none (branch-policy changes are critical) |
| `gitea.webhook.create` | human-only | forge | high | none (changes what drives the state machine) |
| `lease.write.remote` | agent-implementation | coordination | medium | work-lease `lease.py --mirror`; lead `dispatch_recommend.py` |
| `lease.takeover` | guarded-autonomous | coordination | high | (R3 expiry recovery) |
| `review.session.request` | agent-implementation | runtime | low | speckit-development `delivery_plan.py` |
| `dispatch.session.start` | guarded-autonomous | runtime | high | (R3 event-driven dispatch) |
| `events.gateway.serve` | guarded-autonomous | runtime | high | gitea-event-normalizer `normalize.py serve` |
| `policy.change` | human-only | policy | critical | none (roadmap: raising the level is critical risk) |

Later releases may add action ids (bumping `catalog_version`) but may not lower an existing minimum level
without a human-merged ADR. The catalog file is itself a critical policy path. R2 raises
`SUPPORTED_MAX_LEVEL`; R1's catalog holds every action R2 performs and all 7 guarded actions R3 enables, so R2
changes enforcement only. SPEC-203 adds exactly two restrict-only ids in `catalog_version` 1.1.0
(`autonomy.demote`, min `shadow`; `gitea.pr.merge_schedule.cancel`, min `agent-implementation`) and changes no
existing level. The level counts are 3 / 19 / 7 / 5 (shadow / agent-implementation / guarded-autonomous /
human-only) in 1.0.0 and 4 / 20 / 7 / 5 in 1.1.0.

## Assumptions

- The foundation (SPEC-100..104) is complete when R1 step 5 starts. That includes envelope, cli, schemas, validator, sync, installer, bench with an `ollama-cloud` runtime that does not use `format`, the Jev client, and scoring. T001 verifies this and records interface names in `evidence/interface-notes.md`.
- The user allowlists `ollama.com` and `api.typesafe.ai` and provides `OLLAMA_API_KEY` and `TYPESAFE_API_KEY` in the environment that runs the live benchmark. Until then the live gates are `not_run`.
- The user creates the private repository `Cazador0/skill-factory` and grants this build session push access before step 6 (synthesis.md Q3).
- The claude-code-remote `create_session` tool is available to the orchestrator for step 7. If it is not, the `claude -p` fallback is used, and the verdict records `reviewer.mode: cli-fallback`.
- Exact Ollama Cloud model ids, whether Zed profiles can pin a model, and how Zed authenticates to `https://ollama.com` are verified at T112 against the live service and Zed docs. They are not assumed here (synthesis.md Q2, R-5).
