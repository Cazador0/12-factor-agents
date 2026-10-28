# Feature Specification: Lab core (validator, sync, installer, catalog, scaffold, doctor, test runner)

**Spec**: SPEC-101

**Component**: `skill-lab/bin/skill-lab`, `skill-lab/lab/` (`cli`, `paths`, `validate`, `sync`,
`install`, `catalog`, `scaffold`, `doctor`, `testrun`) and `skill-lab/templates/skill/` (family: lab)

**Created**: 2026-10-22

**Status**: Implemented

**Input**: CONVENTIONS §1–§9. Every rule marked **[V]** must be machine-checked, skills must be
installable for Zed (priority runtime, Ollama local or cloud), Claude Code and Codex from one
folder, and vendored shared code must never drift from its canonical copy.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A skill author learns exactly what breaks a skill before review (Priority: P1)

An author (human or agent) runs `skill-lab validate --skill <name>` and gets one JSON report: each
finding names a rule, a severity, a one-line message and a `file:line` path. A small local model can
fix the skill by reading the findings alone.

**Why this priority**: CONVENTIONS §9 makes zero validate errors the first condition of done; every
later gate assumes it.

**Independent Test**: start from a skill that passes every rule, break one thing, and check that the
matching rule fires (`tests/test_lab_core_validate.py`, one test per rule).

**Acceptance Scenarios**:

1. **Given** a SKILL.md whose description is a YAML block scalar, **When** validate runs, **Then** it exits 1 with `frontmatter.block-scalar` at `skills/<name>/SKILL.md:3`.
2. **Given** a script that imports `requests`, **When** validate runs, **Then** it exits 1 with `scripts.import-third-party` at the import's line.
3. **Given** an empty `skills/` folder, **When** validate runs, **Then** it exits 0 with the warning `NO_SKILLS`.
4. **Given** a SKILL.md over 100 KB, **When** validate runs with `--runtime zed`, **Then** `zed.skill-file-too-large` is an error; with `--runtime claude` it is not reported.

---

### User Story 2 - One install makes a skill visible in Zed, Codex and Claude Code (Priority: P1)

A maintainer runs `skill-lab install` once; `.agents/skills/<name>` (Zed and Codex) and
`.claude/skills/<name>` (Claude Code) become relative symlinks to `skills/<name>`. A user without
symlink support uses `--mode copy`. Nothing the lab does not own is ever overwritten.

**Why this priority**: an uninstalled skill does not exist for the runtime.

**Independent Test**: install into a scratch repository, then check links, copies, refusals and
`--check` (`tests/test_lab_core_install.py`).

**Acceptance Scenarios**:

1. **Given** a fresh repository, **When** `skill-lab install` runs, **Then** both discovery folders hold `../../skills/<name>` symlinks and `install --check` exits 0.
2. **Given** a hand-made folder at `.agents/skills/<name>`, **When** install runs without `--force`, **Then** it exits 4 with `INSTALL_CONFLICT` and changes nothing.
3. **Given** `--global` with `HOME=/h`, **When** install runs, **Then** `/h/.agents/skills/<name>` and `/h/.claude/skills/<name>` are absolute symlinks.

---

### User Story 3 - A new skill starts from a template that already passes (Priority: P2)

`skill-lab new my-skill` creates `skills/my-skill/` and `skill-lab/specs/NNN-my-skill/` with every
required heading, an example script that follows the script contract, the minimum eval inventory,
a unit test and complete traceability. Every place to fill in says `TODO(scaffold)`.

**Why this priority**: thirteen skills are built next; each should start valid.

**Independent Test**: scaffold, then validate (0 errors), run its unit tests, and run its four
deterministic cases (`tests/test_lab_core_scaffold.py`).

**Acceptance Scenarios**:

1. **Given** no skill named `demo-skill`, **When** `skill-lab new demo-skill` runs, **Then** validate reports 0 errors and only `scaffold.todo` and `install.not-installed` warnings.
2. **Given** an existing `skills/demo-skill`, **When** `new demo-skill` runs, **Then** it exits 4 with `SKILL_EXISTS` and the folder is untouched.
3. **Given** the name `create-skill`, **When** `new` runs, **Then** it exits 4 with `SKILL_NAME_RESERVED`.

---

### User Story 4 - Vendored code never silently drifts (Priority: P2)

`skill-lab sync` mirrors `skill-lab/shared/_skillkit` into every skill with `scripts/` and refreshes
its vendored schemas; `sync --check` in CI exits 1 on any difference.

**Why this priority**: a stale vendored copy would enforce old rules in one skill only.

**Independent Test**: edit, delete and add files in a vendored copy; `--check` lists each as an
update, create or delete without writing; `sync` repairs all (`tests/test_lab_core_sync.py`).

**Acceptance Scenarios**:

1. **Given** a vendored `ids.py` edited by hand, **When** `sync --check` runs, **Then** it exits 1 with `VENDOR_DRIFT` and an `update` action for that file.
2. **Given** `--add-schema lease --skill x`, **When** sync runs, **Then** `assets/schemas/lease.v1.schema.json` is byte-identical to the canonical contract.

---

### User Story 5 - The environment explains itself (Priority: P3)

`skill-lab doctor` reports the Python version, git, layout, install parity, which credentials are
set (never their values) and whether the Jev API, Ollama Cloud, local Ollama and Gitea answer.
`skill-lab test` runs the lab's and each skill's unit tests and returns one set of counts.

**Why this priority**: the network to `api.typesafe.ai` and `ollama.com` is blocked today; the
report must say so as a warning, not crash.

**Independent Test**: doctor with injected probes and a local HTTP server; test runner on synthetic
suites that pass, fail, crash, time out or are missing (`tests/test_lab_core_doctor.py`,
`tests/test_lab_core_testrun.py`).

**Acceptance Scenarios**:

1. **Given** no network, **When** doctor runs, **Then** every `probe.*` check is `warn` and the exit code is 0.
2. **Given** `GITEA_TOKEN` is set, **When** doctor runs, **Then** the report says it is set and its value appears nowhere in stdout.
3. **Given** a skill whose tests fail, **When** `skill-lab test` runs, **Then** it exits 1 and that suite reports its failed and errored counts with a redacted log tail.

### Edge Cases

- `skills/` missing or empty: validate and sync exit 0 with `NO_SKILLS`; catalog refuses a missing folder (`SKILLS_DIR_NOT_FOUND`, exit 2) and writes an empty catalog for an empty one.
- Folders under `skills/` starting with `_` or `.` and folders without `SKILL.md` are not skills. With the zed profile, a folder that hides a nested `SKILL.md` is reported as its own entry with `zed.flat-layout`.
- A UTF-8 BOM before the frontmatter: Zed's `trim_start()` does not skip U+FEFF, so it is an error under the zed profile and a warning otherwise.
- A dangling symlink into `skills/` (a renamed skill) is managed and stale: install replaces it. A symlink anywhere else is foreign.
- Traceability entries with `"planned": true` (SPEC-201 style) report missing paths as warnings until the work lands.
- `scripts/_skillkit` that is a symlink or a file is drift; sync replaces it with a real copy.
- A script whose `--help` hangs is stopped after 20 s; a probe that hangs is stopped after 5 s.
- A case argument such as `--input no-such-file.json` is allowed (cases may test missing files); only skill paths under `evals/`, `assets/`, `references/` or `scripts/` that do not exist are warned about.

## Requirements *(mandatory)*

### Functional Requirements

Dispatcher:

- **FR-001**: `bin/skill-lab` MUST dispatch `validate`, `sync`, `install`, `catalog`, `new`, `doctor`, `test`, `bench` and `score` through the `lab.cli.COMMANDS` table, importing each module lazily; a missing module MUST yield `COMMAND_UNAVAILABLE` and a broken one `INTERNAL` (exit 2), and every command MUST print exactly one `envelope.v1` (honouring `--pretty`, `--now` and `--repo`) except for `--help`, which prints text and exits 0.

Validate:

- **FR-002**: `skill-lab validate` MUST emit a `validation-report.v1` payload, exit 0 when no error finding exists and 1 otherwise, accept `--skill NAME` (repeatable; unknown names exit 2) and default to every folder under `skills/` with a `SKILL.md`; an empty or missing `skills/` MUST succeed with the warning `NO_SKILLS`.
- **FR-003**: Validate MUST enforce the CONVENTIONS §2 frontmatter subset and field rules (allowed keys, name pattern and length, name equals folder, not `create-skill`, double-quoted one-line description of 1–1024 chars, compatibility, metadata keys and values) and warn when the description is outside 350–900 chars, lacks "Use when", or sets `disable-model-invocation: true`.
- **FR-004**: Validate MUST limit the SKILL.md body to 250 lines and 12 KB, require one `# Title` first and the headings When to use, Inputs, Procedure, Outputs, Guardrails and Resources in that order (optional When not to use after When to use, optional Runtime notes last), and require numbered Procedure steps.
- **FR-005**: Validate MUST resolve every relative Markdown link and every `references/`, `scripts/`, `assets/` or `evals/` path in inline code to an existing file inside the skill folder, ignoring URLs, anchors and fenced code, and reject absolute paths and links that leave the folder.
- **FR-006**: Validate MUST check every entry script for the shebang `#!/usr/bin/env python3`, a module docstring, `from __future__ import annotations`, the executable bit, Python 3.9 grammar, standard-library-only imports present in 3.9 and the running Python (relative imports, `_skillkit` and local modules allowed), and the absence of `shell=True`, `eval` and `exec`; helper modules (`scripts/_*.py`, sub-packages) get the same checks except shebang and executable bit.
- **FR-007**: Validate MUST run each entry script with `--help` (list arguments, cwd = skill folder, 20 s timeout, secrets removed from the environment, no bytecode written) and report any non-zero exit or timeout; `--no-run` skips this and adds the warning `SCRIPTS_NOT_RUN`.
- **FR-008**: Validate MUST report a vendored `_skillkit` that differs from canonical (changed, missing or extra files, `__pycache__` ignored), a missing one when scripts import `_skillkit`, schema files that are not canonical contracts or differ from them, and a missing `envelope.v1.schema.json` in a skill with `scripts/`.
- **FR-009**: Validate MUST check that every `evals/cases/*.json` is strict JSON valid against `benchmark-case.v1`, names this skill, has an `id` equal to its file name and unique, references existing scripts, fixtures and canonical output schemas, and that the skill has at least 4 deterministic, 2 agentic, 3 positive and 1 negative trigger cases.
- **FR-010**: Validate MUST require at least one `tests/test_*.py`, and a single `skill-lab/specs/NNN-*` folder for `metadata.spec` with `spec.md` and a `traceability.json` whose `spec` matches, whose paths and `file::Class::method` test ids exist inside the repository, where every FR has a `verified_by` entry and every `**FR-NNN**` in spec.md is traced.
- **FR-011**: Validate MUST check install parity of `.agents/skills/<name>` (zed, codex) and `.claude/skills/<name>` (claude): not installed is a warning; a link or copy that does not show the skill's current content is an error.
- **FR-012**: `--runtime zed|claude|codex|all` (comma-separated or repeated, default all) MUST select profiles: zed adds the 100 KB SKILL.md limit, the flat-layout check and the BOM error; each profile selects its discovery folder for install parity.
- **FR-013**: Validate MUST compute the catalog budget over all skills (UTF-8 bytes of name plus description) and report more than 50 KB as the envelope error `CATALOG_BUDGET_EXCEEDED` (payload `ok: false`) and more than 40 KB as the warning `CATALOG_BUDGET_NEAR`, plus `CATALOG_MISSING`/`CATALOG_STALE` warnings for `skills/CATALOG.json`.

Sync:

- **FR-014**: `skill-lab sync` MUST mirror `skill-lab/shared/_skillkit` into `scripts/_skillkit` of every skill that has `scripts/` (create, update and delete; `__pycache__` ignored), refresh every vendored canonical schema by file name, always vendor `envelope.v1.schema.json`, leave non-canonical schema files in place with an `UNKNOWN_SCHEMA` warning, and never touch skills without `scripts/`.
- **FR-015**: `sync --check` MUST compute the same actions without writing and exit 1 with `VENDOR_DRIFT` when any is needed; `--add-schema NAME` MUST require exactly one `--skill`, accept `lease`, `lease.v1` or the file name, and refuse unknown contracts (`SCHEMA_NOT_FOUND`) and skills without `scripts/`.

Install:

- **FR-016**: `skill-lab install` MUST install into the repository (default, relative symlinks), another project (`--project DIR`) or the home folder (`--global`, absolute symlinks), for `--runtime zed,codex,claude` (zed and codex share `.agents/skills`), in `--mode symlink` (default) or `copy` (with a `.skill-lab-managed` marker), and `--dry-run` MUST print the plan without changes.
- **FR-017**: Install MUST refuse (exit 4, `INSTALL_CONFLICT`, nothing changed) when a destination exists that is neither a symlink into `skills/` nor a marked copy, unless `--force`; MUST remove managed entries whose skill no longer exists (never with `--skill`); and `install --check` MUST exit 1 with `INSTALL_DRIFT` unless every entry shows the skill's current content.

Catalog:

- **FR-018**: `skill-lab catalog` MUST write `skills/CATALOG.json` as `{schema_version: 1, generated_by, skills: [{name, description, version, family, spec, path, scripts[], schemas[], eval_counts{deterministic, agentic, trigger}}], catalog_bytes}`, sorted by name, byte-stable (sorted keys, no timestamps), skipping unparseable skills with `SKILL_SKIPPED`.
- **FR-019**: `catalog --check` MUST compare without writing and exit 1 with `CATALOG_MISSING` or `CATALOG_STALE`.

Scaffold:

- **FR-020**: `skill-lab new NAME` MUST render `skill-lab/templates/skill` into `skills/NAME/` and `_spec/` into `skill-lab/specs/NNN-NAME/` (the number and family CONVENTIONS §6 assigns to NAME; for any other name `--spec` or the lowest SPEC-001..099 number that is neither used nor reserved by that table; an existing `skill-lab/specs/NNN-NAME/` written first is kept unchanged and reported as `spec_created: false`), vendor `_skillkit` and the envelope schema, and produce a skill that validates with zero errors whose unit tests and deterministic cases pass.
- **FR-021**: `new` MUST exit 2 for an invalid name, text option or template (`INVALID_NAME`, `INVALID_TEXT`, `INVALID_SPEC`, `TEMPLATE_INVALID`) and for `--spec` or `--family` values that contradict CONVENTIONS §6 (`SPEC_ASSIGNED`, `FAMILY_ASSIGNED`), and 4 for a reserved name, an existing skill, a used spec number or one §6 reserves for another skill (`SKILL_NAME_RESERVED`, `SKILL_EXISTS`, `SPEC_EXISTS`, `SPEC_RESERVED`), render through hidden staging folders so a failure leaves nothing behind, and support `--dry-run`.
- **FR-022**: Every place in the template an author must fill in MUST carry `TODO(scaffold)`, and validate MUST report each file under the skill (except `assets/` and vendored code) or its spec that still contains the marker as a `scaffold.todo` warning.

Doctor:

- **FR-023**: `skill-lab doctor` MUST report `python` (fail below 3.9), `git`, `layout.*` (fail when the skills folder, canonical `_skillkit`, contracts or template is missing), `skills`, `install.*` parity and `env.*` presence of `TYPESAFE_API_KEY`/`JEV_API_KEY`, `OLLAMA_API_KEY`, `GITEA_URL` and `GITEA_TOKEN` without ever reading their values into the report; it MUST exit 1 only when a check fails.
- **FR-024**: Doctor MUST probe `https://api.typesafe.ai/v1/models` (200 or 401 is reachable), `https://ollama.com/api/tags`, `http://localhost:11434/api/tags` and `$GITEA_URL/api/v1/version` (when set, credentials stripped) with a 5 s timeout and no credentials, turn every probe outcome including exceptions into `ok` or `warn`, and skip probes with `--offline`.

Test runner:

- **FR-025**: `skill-lab test` MUST run `python -m unittest discover -s skill-lab/tests -t skill-lab` from the repository root and, for each skill, `discover -s tests` with cwd = the skill folder, using the running interpreter, and aggregate ran, passed, failed, errored and skipped counts parsed from unittest's summary.
- **FR-026**: The test runner MUST mark suites `passed`, `failed`, `error` (no summary, crash or timeout), `no_tests` or `missing`, include a redacted log tail of at most 30 lines for failed and errored suites, support `--skill` (repeatable) and `--lab-only`, and exit 1 when any suite failed or errored.

Lab hygiene:

- **FR-027**: All lab code and `bin/skill-lab` MUST parse with Python 3.9 grammar, start with a docstring and `from __future__ import annotations`, import only portable standard-library modules, `lab` and `_skillkit`, avoid `shell=True`, `eval`, `exec` and runtime `X | Y` unions, and the template MUST use only the documented placeholders.

### Key Entities

- **Layout**: every path the lab uses, derived from one repository root (`--repo`).
- **Finding**: `{rule, severity error|warning, message, path}`, one validation result.
- **Install entry**: a skill in one discovery folder with a state (`missing`, `linked`, `copied`, `stale`, `foreign`, `orphan`) and an action (`create`, `replace`, `remove`, `none`, `refuse`).
- **Sync action**: `create`, `update` or `delete` of one vendored file.
- **Catalog**: the generated `skills/CATALOG.json` index.
- **Check**: one doctor result `{id, status ok|warn|fail, message}`.
- **Suite**: one unittest run with its counts and status.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every rule in the rule catalog below has a test that breaks a clean skill in exactly that way and observes the rule (100 % of rules).
- **SC-002**: A freshly scaffolded skill validates with 0 errors under zed, claude and codex, and 4 of 4 of its unit tests and 4 of 4 of its deterministic cases pass.
- **SC-003**: `skill-lab validate` on an empty `skills/` folder exits 0; on the real repository it never crashes (exit 0 or 1).
- **SC-004**: No envelope, log tail or doctor report contains the value of a configured secret.
- **SC-005**: The lab suite passes on Python 3.11, 3.12 and 3.13 with no third-party packages.

## Rule catalog

Frontmatter rules are named after the strict parser's issue keyword (`frontmatter.<keyword>`, with
`_` written as `-`): `missing-open-delimiter`, `missing-close-delimiter`, `tab`, `control-character`,
`comment`, `list`, `bad-indent`, `bad-line`, `duplicate-key`, `empty-value`, `empty-map`,
`nested-map`, `bad-metadata`, `block-scalar`, `flow-collection`, `anchor`, `tag`, `single-quoted`,
`ambiguous-scalar`, `bad-plain-scalar`, `bad-escape`, `trailing-content`, `unterminated-string`,
`unknown-key`, `missing-key`, `name-pattern`, `name-reserved`, `name-folder-mismatch`,
`not-double-quoted`, `too-long`, `not-string`, `missing-metadata-key`, `bad-metadata-value`,
`not-boolean`. All are errors. The other rules:

| Rule | Severity | Checks |
|---|---|---|
| `frontmatter.unreadable` | error | SKILL.md is readable UTF-8 |
| `frontmatter.bom` | error (zed) / warning | no UTF-8 BOM |
| `frontmatter.description-length` | warning | description is 350–900 chars |
| `frontmatter.description-use-when` | warning | description says "Use when" |
| `frontmatter.disable-model-invocation` | warning | not set to true in this release |
| `body.too-many-lines` / `body.too-large` | error | body ≤ 250 lines, ≤ 12 KB |
| `body.title` | error | one `# Title`, first |
| `body.heading-missing` / `body.heading-order` / `body.heading-duplicate` | error | required headings, in order, once |
| `body.procedure-not-numbered` | error | Procedure has numbered steps |
| `body.link-broken` / `body.link-escapes` | error | links and inline skill paths resolve inside the folder |
| `references.too-long` / `references.no-toc` | warning | ≤ 300 lines; contents above 100 |
| `references.unreadable` | error | references are UTF-8 |
| `scripts.unreadable` / `scripts.syntax` | error | UTF-8 source, Python 3.9 grammar |
| `scripts.shebang` / `scripts.docstring` / `scripts.future-import` / `scripts.executable` | error | script header and mode |
| `scripts.import-third-party` / `scripts.import-not-portable` | error | stdlib present in 3.9 and the running Python |
| `scripts.shell-true` / `scripts.eval-exec` | error | no shell, no eval/exec |
| `scripts.help` | error | `--help` exits 0 within 20 s |
| `vendor.skillkit-drift` / `vendor.skillkit-missing` | error | vendored `_skillkit` mirrors canonical |
| `vendor.schema-unknown` / `vendor.schema-drift` / `vendor.envelope-missing` | error | vendored schemas are canonical and current |
| `evals.case-unreadable` / `evals.case-schema` | error | strict JSON, `benchmark-case.v1` |
| `evals.case-id-mismatch` / `evals.case-id-duplicate` / `evals.case-skill-mismatch` | error | identity |
| `evals.case-script-missing` / `evals.fixture-missing` / `evals.output-schema-unknown` | error | references resolve |
| `evals.arg-path-missing` / `evals.trigger-unknown-skill` | warning | argument paths, neighbour names |
| `evals.deterministic-count` / `evals.agentic-count` / `evals.positive-trigger-count` / `evals.negative-trigger-count` | error | tier minimums 4 / 2 / 3 / 1 |
| `tests.missing` | error | at least one `tests/test_*.py` |
| `spec.missing` / `spec.ambiguous` / `spec.md-missing` | error | one spec folder with spec.md |
| `spec.folder-name` | warning | folder is `NNN-<name>` |
| `spec.traceability-missing` / `spec.traceability-invalid` / `spec.traceability-mismatch` | error | traceability file shape and id |
| `spec.trace-path-missing` / `spec.trace-test-missing` | error (warning when planned) | paths and test ids exist |
| `spec.fr-unverified` / `spec.fr-untraced` | error | every FR verified and traced |
| `install.not-installed` | warning | discovery folder has the skill |
| `install.parity` | error | it shows the skill's current content |
| `zed.skill-file-too-large` / `zed.flat-layout` | error | Zed loader limits |
| `scaffold.todo` | warning | no `TODO(scaffold)` left |

New rules hook in by appending a check function to `lab.validate.SKILL_CHECKS`.

## Assumptions

- The repository root holds `skills/` and `skill-lab/` side by side (CONVENTIONS §1); `--repo` points elsewhere, which is how the tests use scratch copies.
- Zed counts the catalog budget in bytes of name plus description and description length in characters (`agent_skills.rs`); Codex and Claude Code accept the same frontmatter subset.
- Skill specs use SPEC-001..099; SPEC-1xx and 2xx belong to the lab and to releases.
- Python 3.9 is not installed in this container; 3.9 compatibility of the lab is checked statically (FR-027) and at runtime on 3.11–3.13.

## Non-goals

- Running benchmark cases or scoring (SPEC-102, SPEC-104; `bench` and `score` are only dispatched here).
- Validating lab specs that no skill references (SPEC-201 adds `validate --specs`), runtime configuration templates (`--config`), ADR references, and policy rules (`_skillkit.policy`); `SKILL_CHECKS` is the hook for them.
- Fixing findings automatically: validate reports, sync and install repair only what they own.
- Calling any model or Gitea API; doctor only checks reachability.

## Contracts

Emits `envelope.v1` from every command. `validate` emits `validation-report.v1`. Consumes
`benchmark-case.v1` (eval cases) and the canonical schemas in `skill-lab/contracts/schemas/`.

The other commands emit lab-internal payloads that have no contract file yet; each is defined as a
`PAYLOAD_SCHEMA` constant (within the keyword subset) next to the code that builds it, and every test
validates the payload against it: `lab-sync` (`lab/sync.py`), `lab-install` (`lab/install.py`),
`lab-catalog` (`lab/catalog.py`; the file itself follows `CATALOG_SCHEMA`), `lab-scaffold`
(`lab/scaffold.py`), `lab-doctor` (`lab/doctor.py`) and `lab-test` (`lab/testrun.py`). Dispatcher
errors use kind `lab-cli` with a null payload. Promoting these to `contracts/schemas/*.v1.schema.json`
is a compatible follow-up.

## Error semantics

Envelope errors are compact `{code, message, path}`; validate turns each error finding into one with
the rule as code (`frontmatter.name-pattern` → `FRONTMATTER_NAME_PATTERN`), at most 20 plus `TRUNCATED`.

| Code | Exit | Raised by | Meaning |
|---|---|---|---|
| `USAGE` | 2 | every command | bad flags, unknown command or runtime |
| `COMMAND_UNAVAILABLE` | 2 | dispatcher | the command's module is not installed |
| `INTERNAL` | 2 | dispatcher, `run_script` | a command module failed to import or crashed |
| `REPO_NOT_FOUND`, `PROJECT_NOT_FOUND` | 2 | all, install | `--repo` / `--project` is not a directory |
| `SKILL_NOT_FOUND` | 2 | validate, sync, install, test | `--skill` names no skill |
| `SCHEMA_NOT_FOUND`, `SKILL_HAS_NO_SCRIPTS`, `CANONICAL_NOT_FOUND` | 2 | sync | bad `--add-schema` target or broken lab |
| `SKILLS_DIR_NOT_FOUND` | 2 | catalog | no `skills/` folder |
| `INVALID_NAME`, `INVALID_TEXT`, `INVALID_SPEC`, `TEMPLATE_INVALID` | 2 | new | bad input or template |
| `SYMLINK_FAILED` | 2 | install | the file system refuses symlinks; use `--mode copy` |
| `<RULE_CODE>`, `CATALOG_BUDGET_EXCEEDED` | 1 | validate | an error finding or the budget |
| `VENDOR_DRIFT` | 1 | sync --check | vendored files differ |
| `INSTALL_DRIFT` | 1 | install --check | a discovery folder is missing or stale |
| `CATALOG_MISSING`, `CATALOG_STALE` | 1 | catalog --check | generated file differs |
| `CHECK_FAILED` | 1 | doctor | a `fail` check |
| `TESTS_FAILED`, `TESTS_ERRORED` | 1 | test | a suite failed or errored |
| `INSTALL_CONFLICT` | 4 | install | an unmanaged path is in the way |
| `SKILL_NAME_RESERVED`, `SKILL_EXISTS`, `SPEC_EXISTS`, `NO_SPEC_NUMBER` | 4 | new | refused to overwrite or reuse |

Warnings: `NO_SKILLS`, `SCRIPTS_NOT_RUN`, `CATALOG_BUDGET_NEAR`, `CATALOG_MISSING`, `CATALOG_STALE`,
`SKILL_SKIPPED`, `UNKNOWN_SCHEMA`, `SUITE_MISSING`, `SUITE_NO_TESTS`.

## Security

- Skill scripts are run only by validate (`--help`) and test, always with list arguments, never a
  shell, with secret environment variables removed for `--help`, and with a timeout.
- Install and sync never delete or overwrite a path they do not manage; `--force` is explicit.
  Removing a symlink never touches its target.
- Doctor reads only whether credentials are set; probes send no credentials and strip userinfo from
  `GITEA_URL`. Every envelope and log tail is redacted by `_skillkit.redact`.
- Traceability paths and links are resolved lexically and must stay inside the repository or the skill
  folder; nothing from a skill or a case is evaluated.
- The scaffold writes only into a new skill folder and a new spec folder, through staging folders.

## Runtime compatibility

- Python ≥ 3.9 standard library only; POSIX and Windows (the executable-bit check is skipped on
  Windows; use `install --mode copy` where symlinks are unavailable).
- Zed: discovery in `.agents/skills` (flat), 100 KB SKILL.md and 50 KB catalog limits, BOM-sensitive
  reader. Codex shares `.agents/skills`. Claude Code reads `.claude/skills`.
- Output is compact JSON by default so a ~32k-context local model can read it; `--pretty` for humans.
