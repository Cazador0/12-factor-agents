# ADR-0013: Spec-first delivery for the skills themselves, Spec Kit-shaped, without a `.specify/` folder

## Status

Accepted

## Date

2026-10-22

## Context

The skills teach agents to deliver software from specifications. They should be built the same
way. The report asks for a verifiable completeness contract instead of "complete the docs":
requirements with ids, acceptance criteria, non-goals, error and security semantics, and
"traceability from requirement → task → expected verification", enforced "by a CI linter that
validates required headings, IDs, cross-references, and traceability" (report
[§Definition of "complete specification"](../research/engineering-team-report.md#definition-of-complete-specification),
[§Spec Kit and specification-driven delivery](../research/engineering-team-report.md#spec-kit-and-specification-driven-delivery)).

Spec Kit ([SOURCES.md, Spec Kit](../research/SOURCES.md#spec-kit)) gives the shape: a spec
template (User Scenarios & Testing with Given/When/Then, Functional Requirements `FR-NNN`, Key
Entities, Success Criteria `SC-NNN`, Assumptions), a `tasks.md` format, and the commands from
constitution to converge. Its templates are vendored as reference under
`docs/research/vendor/`. A Spec Kit project keeps its machinery in a `.specify/` folder (memory,
templates, scripts) and its features under a root `specs/` folder (report
[§Authoritative repository knowledge](../research/engineering-team-report.md#authoritative-repository-knowledge)).

**The user's intake tooling treats the presence of `.specify/` as "this project is initialized".**
Creating that folder here would change how that tooling behaves on this repository.

## Decision

1. **Spec before code, for every skill, lab component and release.** Each has
   `skill-lab/specs/NNN-<name>/spec.md` before its implementation starts. Numbers: `001`–`099` for
   skills (SPEC-001..SPEC-013 today), `1xx` for lab components (SPEC-100..SPEC-104), `2xx` for
   releases (SPEC-200..SPEC-203). A skill's `metadata.spec` names its spec.
2. **Spec Kit's spec template, plus five sections.** User Scenarios & Testing (prioritised stories,
   Given/When/Then acceptance scenarios, edge cases), Requirements (`FR-NNN`), Key Entities,
   Success Criteria (`SC-NNN`) and Assumptions, plus `## Non-goals`, `## Contracts` (what the
   component emits and consumes), `## Error semantics`, `## Security` and
   `## Runtime compatibility` ([CONVENTIONS §6](../CONVENTIONS.md#6-specs-adrs-traceability)).
3. **Machine-readable traceability.** `traceability.json` next to each spec maps every `FR` to
   `implemented_by` paths and `verified_by` entries (`file::Class::method` test ids or eval case
   paths). Every `**FR-NNN**` in `spec.md` must be traced, and every one needs at least one
   `verified_by`. During delivery an entry may be `"planned": true`, which turns missing paths into
   warnings. At merge no entry may still be planned (G-OFF-08).
4. **Releases add the delivery documents.** `release-plan.md`, `synthesis.md`, `plan.md`,
   `tasks.md` (Spec Kit task format) and `gates.json`, following SPEC-200's delivery process: plan,
   synthesise, tasks as spec, implementation plan, execute with `/speckit-development`, pull
   request, independent review, human merge.
5. **Converge semantics.** Delivery uses Spec Kit's converge rules: findings are appended as one
   `## Phase N: Convergence` section and never rewrite existing tasks, and a converged feature
   leaves `tasks.md` byte-identical (SPEC-201 FR-031).
6. **The constitution is CONVENTIONS plus the ADRs.** A change to a CONVENTIONS rule needs an ADR,
   and plans check themselves against both (SPEC-201 plan §Constitution Check).
7. **No `.specify/` folder in this repository.** There is no `.specify/memory/constitution.md`, no
   copied Spec Kit templates or scripts, and our tooling never runs `specify init` here. Specs live
   in `skill-lab/specs/`, not in a root `specs/` folder, so they move with the lab in a subtree
   split (ADR-0001). An agent must not "fix" the missing folder by creating it. Intake documents
   that the user's tooling produces are kept outside `.specify/` (this working tree uses
   `intakes/<slug>/intake.md`).
8. **Target projects stay real Spec Kit projects.** The skills read a target project's
   `.specify/` and `specs/<feature>/` layout. The golden fixture
   (`skill-lab/fixtures/golden-feature/specs/042-session-refresh/`) mirrors that layout, so
   nothing in the skills depends on how this repository stores its own specs.

## Consequences

### Positive

- Every requirement has a recorded implementation and verification, checked by machine. Review
  works from the spec, not from a transcript.
- A replacement session or a new contributor can rebuild intent from the repository alone.
- The skills are developed with the same discipline they enforce, which exposes their gaps early.

### Negative

- It is heavy. The release specs alone run to thousands of lines, and every FR needs a test id.
- Traceability proves a path exists and a test is named, not that the code implements the
  requirement. That still needs Review's requirements matrix and convergence.
- Without `.specify/`, Spec Kit's own commands cannot operate on this repository. Spec Kit's
  `analyze` and `checklist` are not available as-is; the validator and `converge.py` stand in.
- Two spec layouts to explain: `skill-lab/specs/` here, `specs/` in target projects.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| Spec and code drift beyond what traceability detects | Path existence is a weak proxy | Review rebuilds the requirements matrix from `spec.md`; `converge.py` gate G-OFF-12 |
| An agent or tool creates `.specify/` anyway | The folder is a common Spec Kit default | Decision 7; a lab test that fails when `.specify/` exists is proposed (gap below) |
| Lab and release specs are not covered by the per-skill validator | `skill-lab validate` checks specs reached through `metadata.spec` | Dedicated spec tests today; `validate --specs` in SPEC-201 |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Run Spec Kit itself here (`specify init`, `.specify/`, root `specs/`) | Creates `.specify/`, which the user's intake tooling would read as "initialized"; a root `specs/` would not move with the lab in a split; Spec Kit's generated scripts are not held to the stdlib rules |
| Only ADRs and tests, no specs | No requirement-to-verification traceability, which the report requires |
| Issues as specifications | Gitea holds execution state, not intent (ADR-0009); issues are not versioned with the code |
| Free-form design documents | Not machine-checkable |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Each skill names exactly one spec folder with `spec.md` | `spec.missing`, `spec.ambiguous`, `spec.md-missing`, `spec.folder-name`; `test_lab_core_validate.py::TestTestsAndSpecRules::test_spec_folder_required`, `test_lab_core_validate.py::TestTestsAndSpecRules::test_spec_folder_must_be_unique` | enforced (no skills exist yet, so nothing is checked in practice) |
| Traceability shape, ids, existing paths and test ids | `spec.traceability-missing`, `spec.traceability-invalid`, `spec.traceability-mismatch`, `spec.trace-path-missing`, `spec.trace-test-missing`; `test_lab_core_validate.py::TestTestsAndSpecRules::test_test_ids_must_name_real_methods` | enforced |
| Every FR traced and verified; planned entries only warn | `spec.fr-untraced`, `spec.fr-unverified`; `test_lab_core_validate.py::TestTestsAndSpecRules::test_every_fr_in_spec_md_is_traced`, `test_lab_core_validate.py::TestTestsAndSpecRules::test_every_fr_needs_verified_by`, `test_lab_core_validate.py::TestTestsAndSpecRules::test_planned_requirements_only_warn_about_missing_paths` | enforced |
| Lab specs follow the same shape | `test_lab_core_spec.py::TestSpec101`, `test_spec100_traceability.py::TestSpec100` | enforced for SPEC-100 and SPEC-101 |
| A scaffolded skill starts with a complete spec | `test_lab_core_scaffold.py::TestScaffoldOutput::test_spec_stub_has_the_required_sections_and_complete_traceability` | enforced |
| No planned entries at merge; lab and release specs validated | G-OFF-08 `skill-lab validate --specs` | planned (SPEC-201) |
| Converged at merge | G-OFF-12 `converge.py` reports 0 findings | planned (SPEC-201) |
| ADRs keep the MADR sections, and CONVENTIONS cites the ones it depends on | `skill-lab/tests/test_adrs_r1.py` covers ADR-0101..0105 (SPEC-201 T008); nothing checks ADR-0001..0013 yet | planned for R1 ADRs; gap for these |
| No `.specify/` folder in this repository | No check yet | gap |

**Revisit when** the user's intake tooling stops keying on `.specify/`, or when Spec Kit supports a
configurable specs folder that survives a subtree split.

## References

- Report [§Spec Kit and specification-driven delivery](../research/engineering-team-report.md#spec-kit-and-specification-driven-delivery),
  [§Definition of "complete specification"](../research/engineering-team-report.md#definition-of-complete-specification)
- [SOURCES.md: Spec Kit](../research/SOURCES.md#spec-kit); vendored
  [spec template](../research/vendor/speckit-spec-template.md) and
  [tasks template](../research/vendor/speckit-tasks-template.md)
- [CONVENTIONS §6](../CONVENTIONS.md#6-specs-adrs-traceability), [§9](../CONVENTIONS.md#9-definition-of-done-for-a-skill-v)
- [SPEC-200 roadmap](../../specs/200-release-roadmap/spec.md) (delivery process),
  [SPEC-101](../../specs/101-lab-core/spec.md) FR-010, [SPEC-201](../../specs/201-release-shadow/spec.md) FR-031, FR-046
- ADR-0001 (subtree split), ADR-0010 (gates)
