# Feature Specification: `skill-forge` skill

**Spec ID**: SPEC-012 | **Skill**: `skills/skill-forge/` | **Family**: `meta` | **Used by**: Lead profile and any author of a new skill (CONVENTIONS §7)

**Created**: 2026-10-22 | **Status**: Draft (planned; written by SPEC-201 T128, completed at R1 by T129..T132; unchanged in R2 and R3)

**Release specs it refines**: [SPEC-201](../201-release-shadow/spec.md) FR-007, FR-010, FR-011, FR-029, FR-032, FR-033, FR-040, FR-041;
[SPEC-202](../202-release-agent-implementation/spec.md) FR-001, FR-043, FR-046; [SPEC-203](../203-release-guarded-autonomous/spec.md) FR-050,
FR-055, FR-058; [SPEC-105](../105-jev-live-benchmarking/spec.md) FR-005..FR-008, FR-016. The release specs are authoritative; this spec refines
them and never contradicts them.

**Input**: CONVENTIONS §1 (layout), §2 (`SKILL.md` contract), §3 (script contract), §5 (eval minimums), §9 (definition of done), the
`scaffold-plan` row of SPEC-201 §Contracts, the action `workspace.write` (SPEC-201 §Autonomy policy, minimum `shadow`, requester `forge.py new`),
and the person's decisions in SPEC-201 §Clarifications and SPEC-200 open-questions.md (answers of 2026-10-22, final).

## Intent

Make a new skill start correct. `forge.py new` plans (and with `--apply` writes) a complete skill folder that already passes the portable
subset of the conventions: a valid `SKILL.md`, a stub script, references, a vendored `_skillkit` copy, and eval skeletons that meet the minimum
counts. `forge.py check` reports convention findings for any skill folder through the vendored `_skillkit.frontmatter`. `forge.py evals`
generates the missing eval skeletons for an existing skill. The skill never overwrites a file, never edits catalog, README, symlink, allowlist,
or criteria files, and refuses the reserved name `create-skill` (Zed's built-in). It is complete at R1 and unchanged in R2 and R3.

## User Scenarios & Testing *(mandatory)*

Scenarios run offline in a scratch root (`{tmp}/skills`). `skill-lab validate --skill demo-skill` is the lab's authoritative validator, run by
the SPEC-201 US9 acceptance scenarios; `forge.py check` is the in-skill subset. Times use `--now`; T = 2026-10-22T08:00:00Z.

### User Story 1 - Plan and scaffold a new skill (Priority: P1) · R1 shadow

**Actions**: `workspace.write` (minimum `shadow`). **Independent Test**: `skills/skill-forge/tests/test_forge.py::TestNew`.

1. **Given** no `--apply`, **When** `forge.py new --name demo-skill --family meta --spec SPEC-099 --root {tmp}/skills --now T` runs, **Then** it exits
   0 with a `scaffold-plan.v1` whose `applied` is `false` and whose `files[]` lists every path with `sha256` and `action: create`, and nothing is
   written.
2. **Given** `--apply`, **When** it runs at level `shadow`, **Then** the folder exists with exactly the planned files, `applied` is `true`, and
   `skill-lab validate --skill demo-skill` reports 0 errors for zed, claude, and codex (SPEC-201 US9 scenario 2).
3. **Given** the same command again, **Then** it exits 0 with every file `skip` and warning `ALREADY_APPLIED`; **given** a changed file in the
   folder, **then** it exits 2 `SKILL_EXISTS` and writes nothing.
4. **Given** `--name create-skill`, **When** `new` runs (with or without `--apply`), **Then** it exits 2 `SKILL_NAME_RESERVED` and writes nothing
   (SPEC-201 US9 scenario 3).
5. **Given** `--name Bad_Name`, `../x`, a 65-character name, or `--family other`, **Then** it exits 2 with `SKILL_NAME_INVALID` or `FAMILY_INVALID`.
6. **Given** the scaffold, **Then** the new `SKILL.md` has portable frontmatter (`metadata.version` `0.1.0`, the given family, optional
   `secondary_family`, `spec`, `author`), the required headings in order, and a `description` that is a valid single line (a placeholder with
   warning `DESCRIPTION_PLACEHOLDER` when `--description` is absent).

### User Story 2 - Refuse unsafe writes (Priority: P1) · R1 shadow

**Actions**: `workspace.write`. **Independent Test**: `test_forge.py::TestPolicy`, `::TestContainment`.

1. **Given** `.skill-policy.json` with `"overrides": {"deny": ["workspace.write"]}`, **When** `new --apply` runs, **Then** it exits 4
   `POLICY_ACTION_DENIED` and writes nothing; without `--apply` it still exits 0 with the plan (SPEC-201 FR-007).
2. **Given** `--root` inside the `skill-forge` folder itself, **Then** it exits 4 `ROOT_FORBIDDEN` (CONVENTIONS §3: never write in the skill's own folder).
3. **Given** a failure after some files were staged, **Then** the target folder does not exist (staged in a sibling temp directory, renamed once).
4. **Given** a request to add `skill-lab/benchmarks/criteria/<name>.json`, `CATALOG.json`, `.agents/skills/` symlinks, or `skills/README.md` rows,
   **Then** the skill produces none of them: the plan's `next_steps` tell the human which `skill-lab` commands do that.

### User Story 3 - Check a skill against the conventions (Priority: P1) · R1 shadow

**Actions**: none. **Independent Test**: `test_forge.py::TestCheck`; `skills/skill-forge/evals/cases/check-*.json`.

1. **Given** the scaffold from US1, **When** `forge.py check --skill {tmp}/skills/demo-skill` runs, **Then** it exits 0 with a `validation-report.v1`
   whose `ok` is `true` and `skills[0].findings` holds no error (warnings such as `SKELETON_PLACEHOLDER` are allowed).
2. **Given** a `SKILL.md` missing the `## Guardrails` heading, a body of 251 lines, a broken relative link, an unknown frontmatter key, a name that
   differs from the folder, or fewer than 5 agentic cases, **Then** it exits 1 and each defect appears as a finding with `rule`, `severity`
   `error`, `message`, and `path`.
3. **Given** a script lacking the shebang, docstring, `from __future__ import annotations`, the executable bit, or importing a third-party module,
   **Then** the matching finding is reported.
4. **Given** `--runtime claude`, **Then** `runtime_profiles` lists only that runtime; the default lists zed, claude, codex.
5. **Given** a path with no `SKILL.md`, **Then** it exits 2 `SKILL_NOT_FOUND`.

### User Story 4 - Generate eval skeletons that meet the minimums (Priority: P1) · R1 shadow

**Actions**: `workspace.write` (plan without `--apply`). **Independent Test**: `test_forge.py::TestEvals`.

1. **Given** a skill with no cases, **When** `forge.py evals --skill DIR` runs, **Then** the plan holds ≥ 4 deterministic, ≥ 5 agentic (one tagged
   `guardrail`), and ≥ 10 trigger skeletons (≥ 4 positive, ≥ 2 `expect_skill: null`, ≥ 1 naming a neighbour), each a valid `benchmark-case.v1`
   tagged `todo` so `check` warns until a human replaces the placeholder text (SPEC-201 FR-033, SPEC-105 FR-007).
2. **Given** the skill's scripts reference an action above `shadow` (literal ids in `require`, `require_all`, `refusals`, `allows`), **Then** one
   deterministic `policy` skeleton tagged `action:<id>` per such action is added (the tag writes `_` as `-`).
3. **Given** existing case files, **Then** they are `skip` and never overwritten or reformatted.
4. **Given** `--neighbour NAME` that is not a valid skill name, **Then** it exits 2 `NEIGHBOUR_INVALID`; without `--neighbour` the neighbour trigger
   names `skill-forge` with warning `NEIGHBOUR_PLACEHOLDER`.

### User Story 5 - Explain and finish a scaffold with the model (Priority: P2) · R1 shadow

**Actions**: `workspace.write` (when applying). **Independent Test**: agentic cases of the inventory.

1. **Given** a request to create a skill, **Then** the model runs the plan before `--apply`, shows the file list, applies only after the person
   agrees, and re-runs `check`.
2. **Given** a `validation-report` with failures, **Then** the model fixes each finding by editing the new skill's own files (not the template,
   not `_skillkit`), re-runs `check`, and stops at exit 0.
3. **Given** a request for a per-skill criteria file or for the name `create-skill`, **Then** it refuses and explains who may add the file or which
   other name to use.

### User Story 6 - Behaviour is unchanged at higher levels · R2 agent-implementation, R3 guarded-autonomous

**Actions**: `workspace.write` (minimum `shadow`; allowed at every level; no new action is added). **Independent Test**:
`test_forge.py::TestLevelIndependence`; SPEC-202 T046 and SPEC-203 T136.

1. **Given** the policy at `agent-implementation`, `guarded-autonomous`, or demoted, **When** `new --apply` runs, **Then** the result equals the
   `shadow` result (local workspace write only; no Gitea, git, or branch effect), and `overrides.deny workspace.write` still exits 4.
2. **Given** a re-vendor, **Then** `skill-lab sync --check` is clean and a newly scaffolded skill's vendored `_skillkit` equals the lab's.

### Edge Cases

- Reserved names: `create-skill`, and any name listed in `assets/reserved-names.json` (shipped with `create-skill` only; the person may extend it).
- `--root` missing: exit 2 `ROOT_NOT_FOUND`; default root is `./skills` when it exists, else exit 2.
- The target folder exists and is empty: treated as new; a non-empty folder with identical planned files is `ALREADY_APPLIED`; any difference is `SKILL_EXISTS`.
- `--description` containing `"`, a newline, or a control character, or longer than 1,024 characters: exit 2 `DESCRIPTION_INVALID`; 1..349 or 901..1,024
  characters is accepted with warning `DESCRIPTION_LENGTH`.
- Template placeholders are filled by exact `str.replace` of known tokens; values are validated first, so no value can add a token, a heading, or frontmatter key.
- `check` on a symlinked skill folder reads through it only when it resolves inside `--root`.
- `check` counts cases by parsing every `evals/cases/*.json`; a case that is not strict JSON is a finding `eval-case-invalid`, not a crash.

## Requirements *(mandatory)*

### Functional Requirements

**R1 shadow**

- **FR-001**: `forge.py new` MUST, without `--apply`, emit a `scaffold-plan.v1` (`skill`, `root`, `files[{path, sha256, action create|skip}]`,
  `applied: false`) and exit 0 with no side effect; with `--apply` it MUST write exactly the planned files and emit the same plan with `applied:
  true`. Implements: SPEC-201 FR-029, FR-007.
- **FR-002**: `new` MUST validate `--name` against `^[a-z0-9]+(-[a-z0-9]+)*$`, 1..64 characters (exit 2 `SKILL_NAME_INVALID`), refuse reserved names
  with exit 2 `SKILL_NAME_RESERVED` before any other check, validate `--family` (and `--secondary-family`, different from `family`) against the
  family enum and `--spec` against `^SPEC-\d{3}$`. Implements: SPEC-201 FR-029.
- **FR-003**: The scaffold MUST contain `SKILL.md`, `scripts/<script>.py` (a stub with `--help`, a `ping` subcommand emitting an `envelope.v1`, exit
  codes 0 and 2), `scripts/_skillkit/` and `assets/schemas/` copied byte-for-byte from forge's own vendored copies, `references/overview.md`, `assets/templates/.gitkeep`, `evals/cases/` skeletons (FR-004), `evals/fixtures/example.md`, and
  `tests/test_<script>.py`; and it MUST pass `skill-lab validate --skill <name>` with 0 errors. Implements: SPEC-201 FR-029, FR-032, FR-033.
- **FR-004**: `new` and `evals` MUST generate case skeletons meeting FR-033's counts (≥ 4 deterministic, ≥ 5 agentic with ≥ 1 `guardrail`,
  ≥ 10 trigger with ≥ 4 positive, ≥ 2 `null`, ≥ 1 naming a neighbour), one `policy` skeleton tagged `action:<id>` per action above `shadow` that
  the skill's scripts reference, every skeleton tagged `todo`, all valid `benchmark-case.v1`, and never overwrite an existing case. Implements:
  SPEC-201 FR-029, FR-033, FR-010; SPEC-105 FR-007, FR-016.
- **FR-005**: `forge.py check --skill DIR` MUST emit a `validation-report.v1` (`target`, `runtime_profiles`, `ok`, `skills[{name, ok,
  findings[{rule, severity, message, path}]}]`, `catalog{bytes, limit}`) covering: frontmatter keys, quoting and length of `name`,
  `description`, and `compatibility`, required `metadata` keys and family enums, name equals folder and is not reserved, body ≤ 250 lines and 12 KB,
  required headings in order, relative links resolving, script rules of CONVENTIONS §3, and eval counts and case validity. It MUST exit 1 when any
  finding is an error and 0 otherwise, and MUST parse frontmatter with the vendored `_skillkit.frontmatter`. Implements: SPEC-201 FR-029, FR-032.
- **FR-006**: Every write MUST be preceded by `policy.require("workspace.write")` (`require_all` over the plan's actions); `--apply` never
  overrides the policy; a denied or too-low action exits 4 with nothing written and no partial folder. Implements: SPEC-201 FR-007, FR-029.
- **FR-007**: Writes MUST be staged in a temporary sibling directory of the target and moved into place with one rename; the target path MUST resolve
  inside `--root`, and `--root` inside the `skill-forge` folder MUST exit 4 `ROOT_FORBIDDEN`. An existing planned file with identical bytes is
  `skip`; one with different bytes makes the run exit 2 `SKILL_EXISTS`. Implements: SPEC-201 FR-029, FR-032.
- **FR-008**: Output MUST be deterministic: files sorted by path, `sha256` of the exact bytes, no timestamps in generated files, `created_at` from
  `--now`. The generated `_skillkit` and schemas MUST equal forge's vendored copy so `skill-lab sync --check` is clean; the plan's `next_steps` MUST tell
  the human to run `skill-lab sync --skill <name>`, `skill-lab catalog`, and `skill-lab install --project .`. Implements: SPEC-201 FR-029, FR-032.
- **FR-009**: Templates live in `assets/templates/skill/` with names ending `.tmpl` (so no runtime discovers them as a skill); substitution uses
  exact token replacement of validated values only, never `eval`, `format`, or shell. Implements: SPEC-201 FR-029.
- **FR-010**: The skill MUST NOT create or edit `skills/CATALOG.json`, `skills/README.md`, `.agents/skills/*` or `.claude/skills/*` links, runtime
  allowlists, `skill-lab/benchmarks/criteria/**`, `skill-lab/benchmarks/monitor-limits.json`, `.skill-policy.json`, or any spec folder. Implements:
  SPEC-201 FR-029 (CONVENTIONS §5: criteria files change only with the person's approval).
- **FR-011**: `forge.py evals --skill DIR` MUST read the skill's scripts for literal action ids, report the missing skeletons as a
  `scaffold-plan.v1`, and apply them under the same policy, staging, and no-overwrite rules. Implements: SPEC-201 FR-029, FR-033.
- **FR-012**: `SKILL.md` MUST satisfy CONVENTIONS §2 (`metadata.spec: SPEC-012`, `family: meta`, version `0.1.0`, description 350..900 characters,
  body ≤ 250 lines and 12 KB), be distinct from Zed's built-in `create-skill` in its description and body, name `twelve-factor-audit` and
  `lead-architect` as neighbours, and give one command per step. Implements: SPEC-201 FR-032, FR-040.
- **FR-013**: R1 MUST ship ≥ 4 deterministic cases including `rejects-create-skill-name.json` and a deny-override case `new-denied-by-policy.json` (not tagged `policy`: `workspace.write` is allowed at
  `shadow`, and the containment suite expects every `policy` case to be refused at `shadow`), ≥ 5 agentic cases (≥ 1 `guardrail`) with fixtures inside the skill folder, ≥ 10 trigger cases (≥ 4 positive, ≥ 2
  `expect_skill: null`, ≥ 1 naming `twelve-factor-audit`), no `smoke` tag, and no per-skill criteria file. Implements: SPEC-201 FR-010, FR-033;
  SPEC-105 FR-005..FR-008, FR-016.
- **FR-014**: On each live gate run the skill MUST meet SPEC-105's floor per skill and 100 % of its `guardrail` agentic cases. Implements:
  SPEC-201 FR-041; SPEC-105 FR-005..FR-008.

**R2 agent-implementation**

- **FR-015**: At `agent-implementation` the skill MUST behave exactly as at `shadow` (`workspace.write` keeps minimum `shadow`; no Gitea or git
  action); it MUST be re-vendored with the R2 `_skillkit`, and scaffolds made afterwards MUST carry the R2 vendored copy. Implements: SPEC-202
  FR-001, FR-043, FR-046.

**R3 guarded-autonomous**

- **FR-016**: At `guarded-autonomous`, including while demoted, the skill MUST behave exactly as at `shadow`; it remains one of the 14 catalog
  skills, is re-vendored and re-validated, and its deterministic cases and unit tests stay green. Implements: SPEC-203 FR-050, FR-055, FR-058.

### Key Entities

- **Scaffold plan**: the files a `new` or `evals` run would create or skip, with digests, and whether they were written (`scaffold-plan.v1`).
- **Skill template**: the `.tmpl` files and fixed layout a scaffold is built from.
- **Finding**: one convention violation with a rule id, severity, message, and path (`validation-report.v1`).
- **Eval skeleton**: a `benchmark-case.v1` placeholder tagged `todo` that a human replaces with a real case.

## Success Criteria *(mandatory)*

- **SC-001**: For 100 % of scaffolds in the test matrix (every family, with and without `--secondary-family`, with and without `--description`),
  `forge.py check` reports 0 errors and `skill-lab validate --skill <name>` reports 0 errors on zed, claude, and codex.
- **SC-002**: `new --name create-skill` exits 2 `SKILL_NAME_RESERVED` in 100 % of variants (case, whitespace, with `--apply`, with `--root` unset).
- **SC-003**: Over the containment fixtures (policy deny, `--root` in the skill's own folder, injected description, mid-write failure), 0 files are
  written outside the target folder and no partial folder remains.
- **SC-004**: Two runs of `new` with the same inputs give byte-identical stdout and byte-identical files; the scaffold's `_skillkit` has 0 drift under `sync --check`.
- **SC-005**: For 100 % of the injected defects in the `check` fixtures (≥ 12 classes), the expected rule appears with `severity: error`.
- **SC-006**: 100 % of unit tests and deterministic cases pass, and behaviour is identical at all three levels.
- **SC-007**: On each live gate run the skill meets SPEC-105's floor per skill and 100 % of its `guardrail` cases.

## Non-goals

- Writing the skill's real logic, its spec, plan, or tasks (lead-architect and speckit-development), or its real eval content (the author).
- Registering the skill: catalog, symlinks, README rows, runtime allowlists (`skill-lab catalog`, `install`, and the release tasks do that).
- Replacing `skill-lab validate`; `check` is the in-skill subset and the lab validator remains authoritative.
- Creating, editing, or lowering criteria files (the person's answer, 2026-10-22), editing `.skill-policy.json`, or any network or git action.
- Scoring a repository against the 12 factors (twelve-factor-audit).

## Contracts

**Emits** (producer): `scaffold-plan` (owner, R1), `validation-report` (shared with the lab validator; `forge.py check` is a second producer),
`benchmark-case` documents written as files (skeletons), and `envelope`. **Consumes**: `autonomy-policy` and `action-catalog` (via
`_skillkit.policy`), `benchmark-case` (existing cases are read by `check` and `evals`).

## Error semantics

Exit codes follow CONVENTIONS §3 with SPEC-202's reading (4 = not allowed, 1 = precondition failed, 3 = external, 2 = bad input).

| Code | Exit | Subcommand | Meaning |
|---|---|---|---|
| `POLICY_LEVEL_TOO_LOW` / `POLICY_ACTION_DENIED` / `POLICY_HUMAN_ONLY` / `POLICY_UNKNOWN_ACTION` | 4 | `new`, `evals` with `--apply` | SPEC-201 FR-004; nothing written |
| `ROOT_FORBIDDEN` | 4 | new, evals | `--root` or the target resolves inside the skill-forge folder, or leaves `--root` |
| `SKILL_NAME_RESERVED` | 2 | new | `create-skill` or a name in `assets/reserved-names.json` |
| `SKILL_NAME_INVALID` / `FAMILY_INVALID` / `SPEC_ID_INVALID` / `DESCRIPTION_INVALID` / `NEIGHBOUR_INVALID` | 2 | new, evals | Argument fails its pattern |
| `SKILL_EXISTS` | 2 | new, evals | A planned file exists with different bytes |
| `SKILL_NOT_FOUND` / `ROOT_NOT_FOUND` | 2 | check, evals / new | No `SKILL.md` / root folder missing |
| (findings, no top-level code) | 1 | check | At least one finding with severity `error`; payload is a valid `validation-report` with `ok: false` |
| `WRITE_FAILED` | 3 | new, evals | Filesystem error during staging or rename; the target is absent |
| `USAGE` / `INPUT_NOT_FOUND` / `INPUT_NOT_JSON` / `INVALID_NOW` / `INTERNAL` | 2 | all | Bad flags or input, unexpected exception |
| `ALREADY_APPLIED` / `DESCRIPTION_PLACEHOLDER` / `DESCRIPTION_LENGTH` / `NEIGHBOUR_PLACEHOLDER` / `SKELETON_PLACEHOLDER` | warning | new, evals, check | Nothing new written / placeholder text remains |

## Security

- The only effects are local file creations under `--root/<name>`, gated by `workspace.write`; no network, no git, no subprocess.
- Names, descriptions, and neighbours are validated before they reach a path or a template; a value cannot add a path segment, a frontmatter key, or a heading.
- Existing files are never modified; `.skill-policy.json`, criteria files, and `monitor-limits.json` are never touched (human-owned, CONVENTIONS §5 and §8).
- Scaffolded scripts follow CONVENTIONS §3 (list-arg `subprocess` only, no `shell=True`, secrets from environment and redacted); the vendored copy is
  byte-identical to the lab's, so it cannot carry changed security code.
- Untrusted text (an existing skill's files being checked) is parsed, never executed. Findings quote paths and rule ids, not file bodies.

## Runtime compatibility

| Runtime | Invocation | Inference | Notes |
|---|---|---|---|
| Zed Agent + Ollama Cloud (priority 1) | `.agents/skills/skill-forge`, loaded by the Lead profile | One Ollama Cloud model through the local Ollama app signed in to ollama.com (`http://localhost:11434`, SPEC-201 FR-039) | Scripts make all JSON; Zed's built-in `create-skill` is a different tool and the description says so |
| Zed Agent + local Ollama (after L1) | same | Local model, context ≥ 32,768, chosen by the person at unlock time | Only after SPEC-202's L1 gate and the person's sign-off |
| Claude Code | `.claude/skills/skill-forge`, `/skill-forge` | Claude models | Same scripts |
| Codex | `.agents/skills/skill-forge`, `$skill-forge` | Codex models | Same scripts; no network needed |

## Assumptions

- `_skillkit.frontmatter`, `policy`, `fsutil`, `schemas`, `jsonschema_mini`, and `envelope` exist (foundation SPEC-100 and SPEC-201 T017).
- A new skill ships a copy of forge's vendored `_skillkit` and schemas (they equal the lab's after the last sync) so it validates before the human
  runs `skill-lab sync`; this is listed for the person's confirmation.
- The reserved list is `create-skill` only, because SPEC-201 FR-029 names no other; `reserved-names.json` lets the person extend it.
- The case runner supports a per-case working directory for the policy-deny case (SPEC-102); T132 confirms or uses the containment sandbox (SPEC-201 FR-011).
