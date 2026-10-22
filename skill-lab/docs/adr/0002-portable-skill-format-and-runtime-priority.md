# ADR-0002: Portable Agent Skills format, Zed-first runtime priority, symlink install

## Status

Accepted

## Date

2026-10-22

## Context

The same skill folder must load in three runtimes. The user ranks them: the **Zed Agent** (on
Ollama) first, then **Claude Code** and **Codex** as equals. The facts that constrain the format
come from [SOURCES.md](../research/SOURCES.md#zed-agent-skills), Zed's `skills.md` and the parser
`crates/agent_skills/agent_skills.rs`:

| Constraint | Zed | Claude Code | Codex |
|---|---|---|---|
| Discovery | `~/.agents/skills/` and `<worktree>/.agents/skills/`, **flat only**, symlinks supported | `.claude/skills/<name>/SKILL.md` | `.agents/skills` from cwd up to the repository root, symlinks followed |
| Invocation | catalog plus `skill` tool; `/name` | `/name` | `$name` |
| Frontmatter read | `name`, `description`, `disable-model-invocation` (serde_yaml, unknown keys ignored) | its own parser | its own parser |
| `name` | 1–64 chars, `^[a-z0-9]+(-[a-z0-9]+)*$`, equals the folder | — | — |
| `description` | ≤ 1024 chars; longer still loads, with a warning | — | — |
| Size | `SKILL.md` ≤ 100 KB (`MAX_SKILL_FILE_SIZE`); body guidance ≤ 500 lines | — | — |
| Catalog | names plus descriptions of all skills ≤ 50 KB (`MAX_SKILL_DESCRIPTIONS_SIZE`); overflow is dropped with a UI warning | — | — |
| Trust | project-local skills load only from trusted worktrees | — | — |
| Self-modification | the agent cannot edit `SKILL.md` or bundled resources without explicit authorization | — | — |
| Built-ins | `create-skill` ships with Zed. Same-named skills shadow by precedence ProjectLocal > Global > BuiltIn (`SkillSource::precedence`) | — | — |

Spec Kit installs its own Zed and Codex skills into the same `.agents/skills/` folder
([SOURCES.md, Codex and Claude Code](../research/SOURCES.md#codex-and-claude-code-skills)), so
our skills share that folder and Zed's catalog budget with `speckit-*` skills and with whatever
global skills the user has.

## Decision

1. **One folder per skill in the Agent Skills format**: `SKILL.md` plus optional `references/`,
   `scripts/`, `assets/`, `evals/` and `tests/` (CONVENTIONS §1).
2. **A strict frontmatter subset** that parses the same way in serde_yaml, Claude Code, Codex and
   the lab's own parser (`_skillkit.frontmatter`): only the keys `name`, `description`,
   `license`, `compatibility`, `metadata` (a one-level map of string scalars) and
   `disable-model-invocation`. `description` and `compatibility` are single-line double-quoted
   strings. No block scalars, anchors, tags, lists, flow collections or comments
   ([CONVENTIONS §2](../CONVENTIONS.md#2-skillmd-contract)).
3. **Runtime priority decides conflicts.** Every limit is Zed's or stricter. Where runtimes
   differ, the skill uses the intersection all three accept. Behaviour that only one runtime has
   goes in the optional `## Runtime notes` section, which also says how each runtime resolves the
   skill folder (Zed's skill envelope gives the directory, Claude Code uses
   `.claude/skills/<name>`, Codex uses `.agents/skills/<name>`).
4. **The lab turns Zed's limits into rules**, some stricter than Zed:
   - flat layout, `name` equals the folder, name pattern and length;
   - `description` over 1024 chars is an **error** (Zed only warns), 350–900 chars is the target
     (warning outside it);
   - `SKILL.md` over 100 KB is an error under the zed profile;
   - the body is at most 250 lines and 12 KB (ADR-0003 explains why);
   - a UTF-8 BOM is an error under the zed profile, because Zed's `trim_start()` does not strip
     U+FEFF;
   - the catalog over 50 KB is an error and over 40 KB a warning.
5. **Install by relative symlink.** `skill-lab install` creates
   `.agents/skills/<name> -> ../../skills/<name>` (Zed and Codex share it) and
   `.claude/skills/<name> -> ../../skills/<name>`. `--mode copy` writes a marked copy
   (`.skill-lab-managed`) where symlinks are unavailable. `--global` writes absolute symlinks
   under `$HOME`. Install never replaces a path it does not manage (`INSTALL_CONFLICT`, exit 4)
   unless `--force` is given.
6. **No writes inside a skill folder.** The agent may not edit skill files, so scripts keep state
   in `./.skill-state/` (or `--state-dir`) and write output only to `--out`
   (`_skillkit.fsutil.ensure_not_inside`).
7. **`create-skill` is reserved.** A project or global skill with that name would shadow Zed's
   built-in skill-authoring flow. Our authoring skill is `skill-forge`. Reserved names live in
   `_skillkit.frontmatter.RESERVED_NAMES`.
8. **Model invocation stays on.** No skill sets `disable-model-invocation: true` in R1, and the
   validator warns if one does. Zed hides such skills from the model's catalog, so they could not
   route, and the authority boundary is deterministic code, not whether a model may load
   instructions (SPEC-202 synthesis D-26).
9. **Trusted worktree is a documented prerequisite.** Project-local skills do not load from an
   untrusted Zed worktree. The skills' `## Runtime notes` and the install output say so, because
   the lab cannot observe Zed's trust state.

## Consequences

### Positive

- One source folder serves three runtimes. Nothing is generated per runtime.
- The lab's parser is a single stdlib file whose accept/reject matrix is tested, so "parses in
  Zed" is a checkable claim rather than a hope.
- Sharing `.agents/skills/` with Spec Kit means a target project already set up for Spec Kit on
  Zed or Codex needs no new discovery folder.

### Negative

- Runtime-specific frontmatter extensions that need lists or nested maps are unavailable. Any
  per-runtime authority (tool restrictions and similar) has to live in runtime configuration
  (ADR-0008), not in `SKILL.md`.
- The 1024-character error and the 250-line budget can reject a skill Zed itself would load.
- Symlinks need care on Windows. Copy mode works there, but copies go stale: `install --check`
  and the validator's `install.parity` rule catch stale copies, they do not prevent them.
- The 50 KB catalog budget is shared with every other skill the user has installed. The lab
  measures only our skills' share.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| Overflow of the user's total catalog silently drops some skills (Zed shows only a UI warning) | The lab cannot see the user's global skills | Descriptions aim at 350–900 chars; the lab's own catalog warning fires at 40 KB, well below Zed's limit |
| Claude Code or Codex parse an edge case differently from the lab | Differential tests exist only against the Zed source and the lab parser; the Codex CLI is not installed in the build container | Keep to the subset; the trigger tier on each runtime shows whether the skill is seen at all |
| Two trusted worktrees ship the same project skill name; Zed keeps the first in iteration order | Zed's documented tie rule | Names are unique within this catalog; the trigger tier detects misrouting |
| A future Zed built-in takes one of our names and is shadowed by our skill | Upstream may add built-ins | Re-check `crates/agent_skills/builtin/` when SOURCES.md is refreshed |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Per-runtime variants of each skill | Three copies to keep in step. The intersection format loses nothing the skills need |
| Full YAML frontmatter | YAML parsers disagree on edge cases (block-scalar chomping, implicit types, duplicate keys), and the standard library has no YAML parser (ADR-0006) |
| Copy installs by default | Copies go stale. Symlinks are the documented Zed mechanism and always show the current content |
| Global install by default (`~/.agents/skills`) | Puts 13 descriptions in every project's catalog budget and bypasses per-project trust. Offered as `--global` |
| Name the authoring skill `create-skill` to replace Zed's | Shadows a built-in the user may rely on, and the built-in does not know our conventions |
| Set `disable-model-invocation` on skills that write | They would vanish from the catalog, routing gates would fail by construction, and authority would still not rest on the flag |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Frontmatter subset and field rules | `frontmatter.*` rules (SPEC-101 rule catalog), for example `frontmatter.block-scalar`, `frontmatter.unknown-key`, `frontmatter.name-folder-mismatch`, `frontmatter.name-reserved`, `frontmatter.not-double-quoted`; tests in `test_lab_core_validate.py::TestFrontmatterRules` and `test_skillkit_frontmatter.py::TestReject` | enforced |
| `description` limits | `frontmatter.too-long` (error over 1024), `frontmatter.description-length` (warning outside 350–900); `test_lab_core_validate.py::TestFrontmatterRules::test_description_over_1024_chars` | enforced |
| BOM | `frontmatter.bom` (error for zed, warning otherwise); `test_lab_core_validate.py::TestFrontmatterRules::test_bom_is_an_error_for_zed_and_a_warning_otherwise` | enforced |
| Zed loader limits | `zed.skill-file-too-large`, `zed.flat-layout`; `test_lab_core_validate.py::TestRuntimeProfiles` | enforced |
| Catalog budget | `CATALOG_BUDGET_EXCEEDED` (error over 50 KB), `CATALOG_BUDGET_NEAR` (over 40 KB); `test_lab_core_validate.py::TestCatalogBudget::test_budget_counts_utf8_bytes_of_name_and_description` | enforced |
| Install layout and parity | `skill-lab install`, `install --check` (`INSTALL_DRIFT`), `INSTALL_CONFLICT`; rule `install.parity`; `test_lab_core_install.py::TestProjectSymlinks::test_default_creates_relative_symlinks_for_all_runtimes`, `test_lab_core_install.py::TestRefusal::test_unmanaged_path_is_refused_without_changes` | enforced |
| `create-skill` refused | `frontmatter.name-reserved`; `skill-lab new create-skill` exits 4 `SKILL_NAME_RESERVED` (`test_lab_core_scaffold.py::TestScaffoldRefusals::test_reserved_name_exits_4`); `skill-forge` refuses it too (SPEC-201 FR-029) | enforced (lab); planned (skill-forge) |
| What the model sees in Zed | Bench renders the catalog and `<skill_content>` envelope exactly as Zed does; `test_runtimes_zed_emulation.py::TestCatalog::test_exact_catalog_section`, `test_runtimes_zed_emulation.py::TestCatalog::test_hidden_skills_are_left_out` | enforced |
| All 13 skills load on all three runtimes | G-OFF-01 `skill-lab validate --runtime zed,claude,codex` = 0 errors | planned (SPEC-201) |

**Revisit when** Zed supports nested skill folders or new frontmatter keys, or when Claude Code or
Codex change their discovery paths. Update SOURCES.md and this ADR in the same commit.

## References

- [SOURCES.md: Zed Agent skills](../research/SOURCES.md#zed-agent-skills),
  [Codex and Claude Code skills](../research/SOURCES.md#codex-and-claude-code-skills)
- [CONVENTIONS §1](../CONVENTIONS.md#1-layout), [§2](../CONVENTIONS.md#2-skillmd-contract),
  [§7](../CONVENTIONS.md#7-roles-and-authority-zed-profiles)
- [SPEC-101 lab core](../../specs/101-lab-core/spec.md) (rule catalog, install),
  [SPEC-102](../../specs/102-bench-runtimes-graders/spec.md) FR-013 (Zed emulation)
- ADR-0003 (body budget), ADR-0008 (runtime permissions)
