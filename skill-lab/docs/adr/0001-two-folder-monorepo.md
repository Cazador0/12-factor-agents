# ADR-0001: Two-folder monorepo, splittable with git subtree

## Status

Accepted

## Date

2026-10-22

## Context

The system has two products with different consumers and different lifetimes.

- **Skills** are installed into other people's projects and home folders: Zed and Codex read
  `.agents/skills/<name>/`, Claude Code reads `.claude/skills/<name>/`
  ([SOURCES.md, Zed](../research/SOURCES.md#zed-agent-skills) and
  [Codex and Claude Code](../research/SOURCES.md#codex-and-claude-code-skills)). A skill must
  work as a single folder. Zed discovers only direct children of a skills root, global skills
  under `~/.agents/skills/` live outside any project, and a copy-mode install has no path back to
  this repository. A skill therefore cannot rely on anything outside its own folder at run time.
- **The lab** is the factory. It validates, vendors, installs, benchmarks and scores skills, and
  it holds the contracts, specs, research, fixtures and ADRs. Users never run it from inside a
  skill, and its code must never appear in a runtime's skill catalog.

The skills are being built inside the `12-factor-agents` working tree. They are exported to a
standalone repository (`Cazador0/skill-factory`, SPEC-201 User Story 8), and the two halves may
later become two repositories. Shared code (envelope, CLI helpers, strict JSON reading, the
schema validator, redaction, path guards) is needed by every skill script and by the lab.

The report asks for the repository to be the durable memory and for architecture rules to be
mechanical checks rather than prose (report
[§Lead contract](../research/engineering-team-report.md#lead-contract),
[§Authoritative repository knowledge](../research/engineering-team-report.md#authoritative-repository-knowledge)).

## Decision

1. **Two top-level folders.** `skills/` holds one flat folder per skill. `skill-lab/` holds
   everything else the factory needs. The repository root keeps only thin glue: `AGENTS.md`, the
   discovery symlinks `.agents/skills/<name>` and `.claude/skills/<name>`, license files and the
   README. The exact layout is [CONVENTIONS §1](../CONVENTIONS.md#1-layout).
2. **Splittable by construction.** `git subtree split --prefix skills` and
   `git subtree split --prefix skill-lab` must each produce a tree that works without the other
   half for its own purpose. Skills run without the lab. The lab needs a `skills/` folder to act
   on, but takes it as input (`--repo`) rather than through imports.
3. **One dependency direction.** The lab reads, runs and scores skills. No skill script imports,
   executes or reads files from `skill-lab/` at run time. One narrow exception applies to
   procedures, not scripts: `skill-forge` may tell the agent to run the lab's CLI
   (`python3 skill-lab/bin/skill-lab validate|bench|score ...`) as an optional step when the lab
   is present in the project. Its own scripts check skills through the vendored
   `_skillkit.frontmatter`, so the skill still works where the lab is absent.
4. **Vendoring, not linking.** The canonical shared library is
   [`skill-lab/shared/_skillkit/`](../../shared/_skillkit/__init__.py) and the canonical contracts
   are [`skill-lab/contracts/schemas/`](../../contracts/README.md). `skill-lab sync` copies them
   into `skills/<name>/scripts/_skillkit/` and `skills/<name>/assets/schemas/`. Vendored copies
   are never edited in place: a change goes to the canonical copy and is re-synced in the same
   commit. Scripts import the copy next to them (`sys.path.insert(0, <script dir>)`, then
   `from _skillkit import ...`), and `_skillkit.schemas.default_schema_dirs()` resolves schemas
   from the skill's own `assets/schemas/`.
5. **Generated files are never hand-edited.** `skills/CATALOG.json` comes from
   `skill-lab catalog`. Vendored files come from `skill-lab sync`. Lab output (benchmark runs,
   cassettes) never lands under `skills/`.
6. **Links stay inside their half.** Documents under `skill-lab/` use relative links only to
   files under `skill-lab/`, so they still resolve after a split. Paths in `skills/` and at the
   repository root are written as code (`skills/<name>/SKILL.md`), not as links.

## Consequences

### Positive

- A skill installs by symlink or copy with zero setup, and works from `~/.agents/skills/` on a
  machine that has never seen this repository.
- One canonical copy of every shared module and contract. Drift is a detectable error, not a
  silent fork.
- The export and any later split are mechanical. SPEC-201's export gates (G-OFF-10, G-OFF-11)
  prove the combined tree stands alone.
- Reviewers can reason about one direction of dependency. A diff that makes a skill reach into
  the lab is visibly wrong.

### Negative

- Duplication. `_skillkit` has 13 files today and SPEC-201 adds 5 modules, so 13 skills will
  carry about 18 vendored modules each. SPEC-201's plan estimates about 340 of roughly 800 files
  are vendored copies. Diffs get noisy, and reviewers must learn to skip `scripts/_skillkit/`
  and `assets/schemas/`.
- Every skill moves in lock-step with `_skillkit`. A skill cannot pin an older library, so a
  breaking library change touches every skill in one commit. `SKILLKIT_VERSION` (in
  `_skillkit/__init__.py`) records the version, but there is no per-skill pin.
- Contributors who forget `skill-lab sync` get a failing check rather than a working skill. That
  is intended, but it is friction.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| A skill reaches the lab dynamically, for example `importlib.import_module(name)` with a computed name after editing `sys.path` | The import rule is a static AST check | Code review. The skill isolation check below would catch it at run time |
| A skill's unit tests read `../../skill-lab/...`, so they pass here and fail in a split `skills/` repository | `skill-lab test` runs each skill's tests in place (cwd is the skill folder), so the lab is still reachable | Proposed skill isolation check (gap below) |
| Relative symlinks dangle after the repository moves | Symlinks are relative to the install root | `skill-lab install --check` reports `INSTALL_DRIFT`; a dangling managed link counts as stale and is replaced |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Two repositories from day one | SPEC-201 adds 21 contracts and changes 5 while it builds the skills that use them. Cross-repository changes cannot be atomic, and CI would need to coordinate two heads. The subtree-split design keeps this option open at no cost |
| `_skillkit` as a pip package | Breaks zero-install and stdlib-only use (ADR-0006). Zed users may have no pip or venv, and a global skill cannot declare dependencies |
| Symlink `scripts/_skillkit` to the canonical copy | Breaks copy installs, Windows without symlink rights, single-skill archives and a split `skills/` repository. `sync` replaces a symlinked `_skillkit` with a real copy |
| Git submodules | Adds a clone step and detached-HEAD states that agents handle poorly, and solves no problem vendoring leaves open |
| Group skills in family folders (`skills/roles/lead-architect`) | Zed does not discover nested folders ([SOURCES.md](../research/SOURCES.md#zed-agent-skills)). Family is `metadata.family` instead |
| One folder for skills and lab code | Lab code would ship into users' skill folders and could enter the runtime catalog |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Vendored `_skillkit` and schemas equal the canonical copies | `skill-lab sync --check` exits 1 with `VENDOR_DRIFT`; validator rules `vendor.skillkit-drift`, `vendor.skillkit-missing`, `vendor.schema-drift`, `vendor.schema-unknown`, `vendor.envelope-missing`; tests `test_lab_core_sync.py::TestSync::test_check_reports_every_kind_of_drift_without_writing`, `test_lab_core_sync.py::TestSync::test_replaces_a_symlinked_skillkit_with_a_real_copy`, `test_lab_core_validate.py::TestVendorRules::test_modified_vendored_skillkit` | enforced (SPEC-101 FR-008, FR-014, FR-015) |
| Merge gate on drift | G-OFF-02 `skill-lab sync --check` | planned (SPEC-201) |
| No static import of lab code from a skill | `import lab` is neither stdlib nor local, so `scripts.import-third-party` fires; `test_lab_core_validate.py::TestScriptRules::test_third_party_import` | enforced |
| A vendored copy works on its own | `test_skillkit_vendored_script.py::TestVendoredScript` runs a script against a vendored `_skillkit` in a temporary skill folder, including `test_nothing_is_written_inside_the_skill` | enforced |
| Lab output never lands in `skills/` | bench refuses `--out`, `--record` and `--cassettes` inside `skills/` with `PATH_FORBIDDEN`; `test_bench_runner.py::TestDeterministicTier::test_output_inside_skills_is_refused` | enforced |
| Flat layout | `zed.flat-layout`; `test_lab_core_validate.py::TestRuntimeProfiles::test_zed_flat_layout` | enforced |
| Catalog is generated | `skill-lab catalog --check` (`CATALOG_MISSING`, `CATALOG_STALE`); `test_lab_core_catalog.py::TestCatalog::test_check_detects_missing_and_stale_without_writing` | enforced |
| The exported tree stands alone | `skill-lab/bin/export-repo`, gates G-OFF-10 and G-OFF-11 (SPEC-201 FR-043, FR-044) | planned (SPEC-201) |
| A single skill copied alone passes its unit tests and deterministic cases | No check yet. Proposed: copy each skill to an empty temporary folder, run its tests and `bench --tier deterministic` there | gap |

**Revisit when** the factory is split into two repositories, or when a runtime gains a way to
declare shared dependencies between skills.

## References

- [CONVENTIONS §1 Layout](../CONVENTIONS.md#1-layout) and
  [§3 Script contract](../CONVENTIONS.md#3-script-contract-v)
- [SPEC-100 contracts and skillkit](../../specs/100-contracts-skillkit/spec.md),
  [SPEC-101 lab core](../../specs/101-lab-core/spec.md) (sync, validate, install, catalog)
- [SPEC-201 R1 Shadow](../../specs/201-release-shadow/spec.md) User Story 8 and gates G-OFF-02, G-OFF-10, G-OFF-11
- ADR-0006 (stdlib only), ADR-0002 (install layout)
