# Feature Specification: `speckit-gitea-taskstoissues` skill

**Spec ID**: SPEC-004 | **Skill**: `skills/speckit-gitea-taskstoissues/` | **Family**: `speckit-gitea` | **Used by**: Lead profile (CONVENTIONS §7)

**Created**: 2026-10-22 | **Status**: Draft (planned; written by SPEC-201 T061, extended by SPEC-202 T073..T088)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-007, FR-010, FR-011, FR-014, FR-021, FR-032, FR-033;
[SPEC-202](../202-release-agent-implementation/spec.md) FR-005, FR-007, FR-009, FR-023, FR-024, FR-042..FR-044;
[SPEC-203](../203-release-guarded-autonomous/spec.md) FR-053 (re-validated, no behaviour change, T136);
[SPEC-105](../105-jev-live-benchmarking/spec.md) FR-007, FR-008, FR-016. The release specs are authoritative; this spec refines them and never
contradicts them.

**Input**: the report's §Gitea integration for Spec Kit ("Read tasks.md, parse task IDs and dependency markers, look up existing Gitea issues by
task ID, create only missing issues, set labels / milestone, create dependency relationships, write issue IDs back to a machine-readable
mapping"), SOURCES.md (Spec Kit `tasks.md` line grammar; the deprecated GitHub-only `taskstoissues`; Gitea dependency endpoint), and the person's
decisions in SPEC-201 §Clarifications and SPEC-200 open-questions.md (answers of 2026-10-22, final).

## Intent

Spec Kit's own task-to-issue command is GitHub-only. This skill gives the Lead a Gitea-native, duplicate-proof way to turn `tasks.md` into issues.
R1 computes the whole job as a dry-run `gitea-plan` and refuses to apply it; R2 applies the same plan idempotently, resumably, and with a
journaled task-to-issue map; R3 changes nothing here and only re-validates the skill. The script decides every operation; the model runs the
steps in order and explains the result.

## User Scenarios & Testing *(mandatory)*

Scenarios run offline against the golden feature `skill-lab/fixtures/golden-feature/specs/042-session-refresh` (14 tasks, copied to
`skills/speckit-gitea-taskstoissues/evals/fixtures/golden/`) and the Gitea double's seed (issues `T001: …` to `T003: …` open, `T013: …` closed,
orphan `T099: stray`; exported as `evals/fixtures/issues-seed.json`). R1 reads Gitea only through `--issues-file` or the read-only client
(`--gitea-url`); R2 adds `--gitea-fixture` and the HTTP double. Times use `--now`.

### User Story 1 - Plan the missing issues for a feature (Priority: P1) · R1 shadow

**Actions**: none to run (the plan only names `gitea.issue.create`, `gitea.label.define`, `gitea.labels.set`, `gitea.milestone.set`,
`gitea.issue.dependency.set`, minimum `agent-implementation`). **Independent Test**:
`skills/speckit-gitea-taskstoissues/tests/test_tasks_to_issues.py`; integration `skill-lab/tests/integration/test_us3_lead_flow.py` (SPEC-201 T071).

1. **Given** the golden `tasks.md` and the double's seed, **When** `python3 scripts/tasks_to_issues.py --tasks evals/fixtures/golden/tasks.md
   --issues-file evals/fixtures/issues-seed.json --repository owner/app` runs, **Then** it exits 0 with a `gitea-plan.v1` that has exactly 10
   `create_issue` operations (T004..T012 and T014), titled `T004: <description>` and so on, and 4 `set_dependency` operations (T008→T006,
   T008→T007, T009→T008, T012→T011); `skipped[]` lists T001, T002, T003 (open) and T013 (closed) with their issue numbers; the orphan `T099` is
   ignored (SPEC-201 US3 scenario 3).
2. **Given** the same inputs and `--now`, **When** the command runs twice, **Then** both stdout documents are byte-identical, and every
   `idempotency_key` equals `_skillkit.ids.idempotency_key(repository, feature, task_id, op)`.
3. **Given** a map `task-issue-map.v1` that lists T005 as issue 190, **When** the plan is computed, **Then** T005 is in `skipped[]` with reason
   `mapped` even if no issue titled `T005:` is in the issue list (the map is consulted first, the title regex second).
4. **Given** tasks with `[US1]`, `[US2]`, and no story marker, **When** the plan is computed, **Then** each created issue carries the labels
   `state/backlog`, `spec/042-session-refresh`, and `story/US1` or `story/US2` (none for no marker), and labels missing from the repository are
   planned first as `define_label` operations from the fixed vocabulary only.
5. **Given** `--milestone "Session refresh"`, **Then** a `set_milestone` operation follows each create; without the flag no milestone operation
   exists.
6. **Given** a task `(depends on T099)` with no T099 in `tasks.md`, **Then** the warning `UNKNOWN_DEPENDENCY` names it and no link is planned;
   **given** a dependency cycle, **then** it exits 1 `TASK_GRAPH_CYCLE` and plans nothing.

### User Story 2 - Refuse to apply at shadow (Priority: P1) · R1 shadow

**Actions**: the five above, each minimum `agent-implementation`. **Independent Test**: `test_tasks_to_issues.py::TestPolicy`.

1. **Given** level `shadow` (or no policy file), **When** the US1 command runs with `--apply`, **Then** it exits 4 `POLICY_LEVEL_TOO_LOW`, prints
   no plan, and the Gitea double logs 0 non-GET requests (SPEC-201 US3 scenario 4, FR-007 all-or-nothing).
2. **Given** `"overrides": {"deny": ["gitea.issue.create"]}` at any level, **Then** `--apply` exits 4 `POLICY_ACTION_DENIED` before any request.
3. **Given** `--gitea-url https://user:token@host`, **Then** it exits 4 `URL_HAS_CREDENTIALS` with the URL redacted.

### User Story 3 - Read Gitea read-only (Priority: P2) · R1 shadow

**Independent Test**: `test_tasks_to_issues.py::TestReadOnlyClient`, against `skill-lab/lab/gitea_double.py`.

1. **Given** `--gitea-url` pointing at the double, **When** the plan is computed, **Then** only `GET /api/v1/repos/{owner}/{repo}/issues?state=all`
   (paged), `/labels`, and `/milestones` are requested, and the plan equals the one built from `--issues-file`.
2. **Given** the server is unreachable or answers 401, **Then** it exits 3 `GITEA_UNREACHABLE` or `GITEA_AUTH`, and a token never appears in output.

### User Story 4 - Apply the plan idempotently and resume it (Priority: P1) · R2 agent-implementation

**Actions**: `gitea.label.define`, `gitea.issue.create`, `gitea.labels.set`, `gitea.milestone.set`, `gitea.issue.dependency.set` (and
`gitea.issue.update` for `--refresh-titles`), all minimum `agent-implementation`; the map journal is `state.write.local`. **Independent Test**:
`skills/speckit-gitea-taskstoissues/tests/test_tasks_to_issues_apply.py`; integration `test_r2_us3_lead_board.py` (SPEC-202 T089).

1. **Given** level `agent-implementation`, the Lead's token, and an empty repository on the double, **When** `tasks_to_issues.py --apply` runs,
   **Then** the created issues equal the plan's `create_issue` operations, the created dependencies equal its `set_dependency` operations,
   `apply-report.v1` and `task-issue-map.v1` are emitted, and the map file is written (SPEC-202 US3 scenario 1).
2. **Given** the same command again, **Then** 0 writes occur and every operation is `already_applied`.
3. **Given** a closed issue titled `T004: …`, **When** the plan applies, **Then** no issue is created for T004 and the map points at the closed
   issue (scenario 2). Immediately before each create the script re-reads, so an issue made by another session in between is not duplicated.
4. **Given** a fault after operation k for every k, **When** the same command is re-run, **Then** the final state has 0 duplicate issues,
   dependencies, or labels (scenario 3).
5. **Given** `tasks.md` changed after the plan was computed, **When** `--apply --plan FILE` runs, **Then** it exits 1 `PLAN_STALE` before any write.
6. **Given** a repository whose `state/backlog` label exists but is not exclusive, **Then** label definition exits 1 `LABEL_NOT_EXCLUSIVE` and
   changes nothing (SPEC-202 Edge Cases).
7. **Given** `--apply` and a PSE token, **Then** it exits 4 `IDENTITY_MISMATCH`: only the Lead identity writes (SPEC-202 FR-007).

### User Story 5 - Refresh drifted titles of mapped open issues (Priority: P3) · R2 agent-implementation

**Actions**: `gitea.issue.update` (minimum `agent-implementation`). **Independent Test**: `test_tasks_to_issues_apply.py::TestRefreshTitles`.

1. **Given** a mapped, open issue whose title differs from `T008: <current description>`, **When** `--refresh-titles` runs without `--apply`,
   **Then** the plan holds one `update_issue` operation changing only `title` (and the generated body); without the flag no `update_issue`
   operation is ever planned.
2. **Given** level `shadow`, **When** `--refresh-titles --apply` runs, **Then** it exits 4 `POLICY_LEVEL_TOO_LOW`; **given** a closed issue,
   **then** it is skipped with reason `closed` (the skill never reopens, closes, or deletes an issue).

### User Story 6 - The skill stays correct in R3 (Priority: P3) · R3 guarded-autonomous

**Actions**: none new. **Independent Test**: `skill-lab validate --skill speckit-gitea-taskstoissues` and
`skill-lab bench --skill speckit-gitea-taskstoissues --tier deterministic` after `skill-lab sync` (SPEC-203 T136).

1. **Given** R3's re-vendored `_skillkit` (policy, demotion state), **When** the deterministic cases run, **Then** all pass with unchanged output;
   **given** an active demotion, **then** `--apply` exits 4 `POLICY_LEVEL_TOO_LOW` with warning `AUTONOMY_DEMOTED`.
2. **Given** the R3 gateway, **Then** no handler runs this skill: issue creation stays a Lead command.

### Edge Cases

- `tasks.md` lacks task ids, or is empty: exit 2 `NO_TASKS`; missing file: exit 2 `INPUT_NOT_FOUND`.
- Duplicate task id in `tasks.md`: exit 2 `DUPLICATE_TASK_ID` naming both lines; nothing is planned.
- A description over 240 characters: the title is cut at a word boundary with warning `TITLE_TRUNCATED` (the full text stays in the body).
- A checked task `[x]` with no issue: created like any other task with `state/backlog` and warning `CHECKED_TASK_WITHOUT_ISSUE`; closing it
  is a human or R3 action (`gitea.issue.close`, which this skill never references).
- An issue with title `T004: other text` exists: it counts as present (the regex dedupes by task id, not title); `sync` reports the mismatch.
- A task description contains a `skill-lab:` marker, a URL, or instructions (hostile text): it is quoted data in the body, never executed.
- The issue list is paged: the client follows `Link` pages up to a bound of 50 pages, else exit 3 `GITEA_SCHEMA_DRIFT` with `PAGINATION_LIMIT`.
- An operation fails mid-apply (R2): exit with its code, `apply-report.complete` false, earlier operations recorded; the re-run resumes.

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: `tasks_to_issues.py` MUST parse `tasks.md` through `_skillkit.speckit_tasks` (id regex `\bT\d{3,}\b`, `[P]`, `[USn]`, `[x]`, inline
  `(depends on …)`) and emit a `gitea-plan.v1` whose `create_issue` operations (action `gitea.issue.create`) cover exactly the tasks that have no
  issue, each titled `T001: <description>`. Implements: SPEC-201 FR-014, FR-021.
- **FR-002**: Dedupe MUST consult the `task-issue-map.v1` file first (`--map`), then the task-id regex `^T\d{3,}:` over the titles of open and
  closed issues; every task found is listed in `skipped[]` with `task_id`, `issue`, and reason (`mapped`, `open`, `closed`); issues whose id is not
  in `tasks.md` are ignored (reported by speckit-gitea-sync). Implements: SPEC-201 FR-021; SOURCES.md Spec Kit.
- **FR-003**: Dependency links MUST come only from inline `(depends on …)` markers and be planned as `set_dependency` operations (action
  `gitea.issue.dependency.set`, one per edge, skipping links already present on the issue list); an unknown dependency is a warning
  `UNKNOWN_DEPENDENCY` with no link; a cycle exits 1 `TASK_GRAPH_CYCLE` with no plan. Phase-order edges are never turned into links. Implements:
  SPEC-201 FR-014, FR-021.
- **FR-004**: Labels MUST come from the fixed vocabulary `state/*`, `spec/<feature-slug>`, `story/US<n>`: new issues get `state/backlog`
  (the Lead moves them later), `spec/<slug>`, and `story/US<n>` when the task has one. Missing labels MUST be planned first as `define_label`
  operations (action `gitea.label.define`, `state/*` created exclusive) and applied to each issue with `set_labels` (action `gitea.labels.set`,
  full set, only `state/*` and the two scoped prefixes changing). `--milestone TITLE` MUST add one `set_milestone` operation (action
  `gitea.milestone.set`) per created issue; without it none is planned. Implements: SPEC-201 FR-021.
- **FR-005**: Every operation MUST carry `idempotency_key` = `_skillkit.ids.idempotency_key(repository, feature, task_id, op)` (dependency
  operations use the dependent task id and the op string `set_dependency:<blocker>`), carry `action`, and name its request (`method`, `path`,
  `body`) and `reason`; the plan MUST record the SHA-256 of `tasks.md` as its source digest (the value SPEC-202 FR-024 compares). The same inputs
  and `--now` MUST give a byte-identical document. Implements: SPEC-201 FR-021; SPEC-202 FR-024.
- **FR-006**: Gitea MUST be read only through `--issues-file` (an issue export, a `gitea-fixture` issue list, or the double's seed) or the
  read-only client `--gitea-url` (GET only, paged, token from `GITEA_TOKEN`); a URL with credentials MUST exit 4 `URL_HAS_CREDENTIALS`; any
  non-GET request is a bug the lab test asserts never happens in R1. Implements: SPEC-201 FR-017, FR-021.
- **FR-007**: With `--apply` the script MUST call `require_all` for the five plan actions first; at `shadow` it MUST exit 4
  `POLICY_LEVEL_TOO_LOW`, print no plan, make no request, and write nothing; `overrides.deny` gives `POLICY_ACTION_DENIED`. `--apply` never
  overrides policy. Implements: SPEC-201 FR-004, FR-007, FR-021.
- **FR-008**: The issue body MUST be rendered from `assets/templates/issue-body.md`: task id and description (quoted), the feature and the spec
  path, the story, `Depends on` task ids, write-domain paths found in the description, and one informational marker line
  `<!-- skill-lab:task-issue:v1 feature=<slug> task=<id> -->` that is never trusted for dedupe. Implements: SPEC-201 FR-021.
- **FR-009**: The script MUST follow CONVENTIONS §3 (stdlib, one envelope, exit codes 0–4, `--now`, no write inside the skill folder) and
  `SKILL.md` MUST satisfy CONVENTIONS §2 (`metadata.spec: SPEC-004`, `family: speckit-gitea`, body ≤ 250 lines and 12 KB), naming one command
  per step and the behaviour per level. Implements: SPEC-201 FR-032.
- **FR-010**: R1 MUST ship ≥ 4 deterministic cases including `plan-creates-missing-only.json` and the `policy` case `apply-refused-at-shadow.json`
  tagged with the five actions, ≥ 5 agentic cases (≥ 1 `guardrail`) with fixtures inside the skill folder, ≥ 10 trigger cases (≥ 4 positive,
  ≥ 2 `expect_skill: null`, ≥ 1 naming `speckit-gitea-sync`), and no per-skill criteria file. Implements: SPEC-201 FR-010, FR-011, FR-033;
  SPEC-105 FR-007, FR-016.

**R2 agent-implementation**

- **FR-011**: `--apply` MUST execute the plan through `_skillkit.plan_apply` with the op allow-list `define_label`, `create_issue`,
  `update_issue`, `set_labels`, `set_milestone`, and `set_dependency`; immediately before each create it MUST re-check dedupe (map, then
  `^T\d{3,}:` over open and closed issues), create each dependency only when absent, journal the map atomically after every operation, and emit
  `apply-report.v1` plus `task-issue-map.v1`; a re-run MUST make 0 writes. Implements: SPEC-202 FR-023, FR-005.
- **FR-012**: The apply MUST refuse with exit 1 `PLAN_STALE` when the plan's recorded `tasks.md` digest differs from the current one, call
  `require_all` for every operation's action before the first side effect, stop at the first operation that does not succeed, and leave earlier
  operations recorded so the same command resumes. Implements: SPEC-202 FR-024.
- **FR-013**: An existing `state/*` label that is not exclusive MUST exit 1 `LABEL_NOT_EXCLUSIVE` with no change. `--refresh-titles` MUST plan
  `update_issue` (action `gitea.issue.update`) only for mapped, open issues, change only `title` and the generated body, and never close, reopen,
  delete, relabel, or touch a closed issue. Implements: SPEC-202 FR-023, FR-043.
- **FR-014**: Writes MUST use the Lead identity from `.skill-gitea.json` (`IDENTITY_MISMATCH`, exit 4, for another role), fail closed on
  `UNSUPPORTED_OP`, and keep every token out of output, plan, report, map, and state. Implements: SPEC-202 FR-007, FR-009, FR-044.
- **FR-015**: `SKILL.md` MUST document the apply steps, the resume rule ("re-run the same command"), and the behaviour per level; R2 MUST add the
  `applied`/`rerun` cases for the six actions, `issue-update-refused-at-shadow.json` (`policy`, `action:gitea.issue.update`),
  `dedupe-closed.json`, `plan-stale.json`, `label-not-exclusive.json`, the agentic case `agentic-r2-resume-apply`, and one positive and one
  negative trigger case. Implements: SPEC-202 FR-042, FR-043.

**R3 guarded-autonomous**

- **FR-016**: R3 MUST leave the script and `SKILL.md` unchanged in behaviour: the skill is re-vendored (`skill-lab sync --skill
  speckit-gitea-taskstoissues`), re-validated, and its deterministic tier re-run; with an active demotion `--apply` MUST exit 4
  `POLICY_LEVEL_TOO_LOW` and emit warning `AUTONOMY_DEMOTED`. No gateway handler runs this skill. Implements: SPEC-203 FR-053 (T136).

### Key Entities

- **Task**: one `tasks.md` line with id, phase, story, parallel flag, checked state, dependencies, and write paths (`task-graph.v1` task).
- **Issue plan** (`gitea-plan.v1`): the operations that would create missing issues, labels, milestone links, and dependencies, plus `skipped[]`.
- **Task-issue map** (`task-issue-map.v1`): the committed, machine-readable `T001 → issue` record; journaled by R2's apply, read by R1 and sync.
- **Apply report** (`apply-report.v1`, R2): per-operation status with receipts; `complete` false means resume.

## Success Criteria *(mandatory)*

- **SC-001**: On the golden feature and seed, the plan has 10 creates and 4 links in 100 % of runs, and a re-run is byte-identical.
- **SC-002**: At `shadow`, `--apply` causes 0 non-GET requests and 0 local writes (SPEC-201 G-OFF-07).
- **SC-003**: R2: the fault sweep k = 1..N ends with 0 duplicate issues, labels, or dependencies, and an unfaulted re-run makes 0 writes (SPEC-202 SC-002, SC-003).
- **SC-004**: 100 % of deterministic cases pass, and every case run twice with the same `--now` gives byte-identical stdout.
- **SC-005**: On each live gate run the skill meets SPEC-105's floor per skill (agentic ≥ 0.80, trigger ≥ 0.90) and 100 % of its `guardrail` cases.

## Non-goals

- Writing issue contracts, acceptance criteria, or dispatching issues (lead-architect); detecting drift (speckit-gitea-sync); moving board
  states beyond the initial `state/backlog` label (kanban-state-machine).
- Closing, reopening, deleting, or assigning issues; project-board columns (labels only); creating GitHub issues (speckit-development's github forge).
- Rewriting `tasks.md` or `spec.md`, or committing the map (the human or Lead commits it).
- A per-skill criteria file (the person's answer, 2026-10-22).

## Contracts

**Emits** (producer): `gitea-plan` (R1, shared contract, ops `define_label`, `create_issue`, `set_labels`, `set_milestone`, `set_dependency`,
and from R2 `update_issue`), `apply-report` (R2, shared, from `_skillkit.plan_apply`), `task-issue-map` (R2, owner of the write; R1 only reads
it), `rendered-document` (`doc_kind: issue-body`, via `--render`), and `envelope`. **Consumes**: `task-issue-map` (dedupe), `task-graph` (through
`_skillkit.speckit_tasks`), `gitea-project` (R2 identities), `gitea-fixture` (R2 deterministic cases), `mutation-receipt` (R2), `autonomy-policy`
and `action-catalog` (via `_skillkit.policy`).

## Error semantics

Exit codes follow CONVENTIONS §3 with SPEC-202's reading (4 = not allowed, 1 = precondition failed, 3 = external, 2 = bad input); refusals print no plan.

| Code | Exit | Where | Meaning |
|---|---|---|---|
| `POLICY_LEVEL_TOO_LOW` / `POLICY_ACTION_DENIED` / `POLICY_HUMAN_ONLY` / `POLICY_UNKNOWN_ACTION` | 4 | `--apply`, `--refresh-titles --apply` | SPEC-201 FR-004; also while demoted (R3) |
| `URL_HAS_CREDENTIALS` / `IDENTITY_MISMATCH` / `UNSUPPORTED_OP` / `LIVE_SMOKE_REQUIRED` | 4 | client, apply | Client guardrails (SPEC-202 FR-007) |
| `TASK_GRAPH_CYCLE` | 1 | plan | Dependency cycle; no plan |
| `PLAN_STALE` | 1 | apply (R2) | `tasks.md` or live state changed since the plan |
| `LABEL_NOT_EXCLUSIVE` | 1 | apply (R2) | Existing `state/*` label is not exclusive |
| `NO_TASKS` / `DUPLICATE_TASK_ID` / `MAP_INVALID` / `ISSUES_FILE_INVALID` (skill-local) | 2 | plan | Unusable input |
| `GITEA_UNREACHABLE` / `GITEA_AUTH` / `GITEA_SCHEMA_DRIFT` / `VERIFY_AFTER_WRITE_FAILED` | 3 | read, apply | External failure; the re-run resumes |
| `UNKNOWN_DEPENDENCY` / `TITLE_TRUNCATED` / `CHECKED_TASK_WITHOUT_ISSUE` / `AUTONOMY_DEMOTED` / `ALREADY_APPLIED` | warning | plan, apply | Information only |
| `USAGE` / `INPUT_NOT_FOUND` / `INPUT_NOT_JSON` / `INVALID_NOW` / `INTERNAL` | 2 | all | Bad input or unexpected exception |

## Security

- Task text, issue titles, and bodies are untrusted data: quoted into the body, never evaluated, executed, or passed to a shell; a `skill-lab:`
  marker found in them is ignored (SPEC-202 FR-009). Labels outside the fixed vocabulary are never created, so text cannot mint a label.
- Reads are GET-only; a token comes only from `GITEA_TOKEN`, is redacted by `_skillkit.redact`, and never reaches output, plan, map, or logs.
- The plan names every request, so a human can read what `--apply` would hit; `--apply` runs only after `require_all` for all actions.
- The map and `tasks.md` are never written by anything but the applier's map journal; the skill cannot reach issues of another repository.

## Runtime compatibility

| Runtime | Invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/speckit-gitea-taskstoissues`, loaded by the Lead profile | One Ollama Cloud model through the local Ollama app signed in to ollama.com (`http://localhost:11434`, SPEC-201 FR-039) | Scripts make all JSON (no structured outputs); one tool call per step |
| Zed Agent + local Ollama (after L1) | same | Local model, context ≥ 32,768, chosen by the person at unlock time | Only after SPEC-202's L1 gate and the person's sign-off |
| Claude Code | `.claude/skills/speckit-gitea-taskstoissues`, `/speckit-gitea-taskstoissues` | Claude models | Same scripts |
| Codex | `.agents/skills/speckit-gitea-taskstoissues`, `$speckit-gitea-taskstoissues` | Codex models | Without network the read-only client exits 3; use `--issues-file` |

## Assumptions

- `_skillkit.speckit_tasks`, `ids`, `policy`, and `gitea` come from SPEC-201 T019..T025; `plan_apply` and the hardened client from SPEC-202 T030..T034.
- The plan's source-digest field name and the exact `define_label` body (`exclusive: true`) are recorded by SPEC-201 T025 and SPEC-202 T005; this
  spec follows them.
- The map defaults to `specs/<feature>/task-issue-map.json` (committed by a human); the applier's journal write is covered by
  `state.write.local` and needs no extra catalog action.
- `state/backlog` as the initial label is the conservative choice (nothing is ready for build until the Lead moves it); listed for the person's confirmation.
