# Specification Quality Checklist: Independent Quality Assurance and Evidence Gates

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Updated**: 2026-10-22 (refinement: verified review findings, project and data-model intake answers, fixed dependency map; second pass: seven verified findings, listed under "Second-pass review findings")
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs). Deliberate exceptions are listed in Notes.
- [x] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous. Inferred rules and proposed defaults are listed in Notes.
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details). SC-004 names Claude and Ollama, which the person fixed.
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification. Deliberate exceptions are listed in Notes.

## Notes

### Why items changed

- **Unticked: "Written for non-technical stakeholders"**. The earlier version ticked this, but it is not true. The readers are the engineering owner and the role agents. The requirements use terms that the constitution and the report fix, such as head commit, status context, manifest and bot account. The User Stories stay in plain language. This item does not block planning.
- **"Requirements are testable and unambiguous" and "Success criteria are measurable" stay ticked, now with grounds.** The review was right that the earlier ticks were not earned: FR-020 was untestable, and the SC numbers were not labeled as defaults. This pass fixes both:
  - FR-020 defines "recurring" (3 distinct PRs, a proposed default). It replaces "where possible" with a recorded "not mechanizable" decision in a versioned mistake register. The invented "weekly review" is gone.
  - FR-018 names an artifact and a check. Every repository keeps a versioned security mapping: its SSDF practices always, each naming an artifact or check, and its ASVS level and requirements only where it serves web applications or services. The manifest cites evidence per mapped ASVS requirement, and SC-011 checks both parts.
  - FR-021 defines "CI" for Low and "complete CI" for Medium and above. FR-024 defines a human approval by account.
  - FR-022 says how skipped, cancelled, missing and fail-then-pass results count.
  - Every invented number is labeled a proposed default, in the SC itself and in Assumptions.
- **"No [NEEDS CLARIFICATION] markers remain" stays ticked.** The only open question the review raised, how approvals are told apart, was answered by the person ("Each role gets its own Gitea bot account.", project intake Q15) and now sits in FR-024. Every other gap was settled with an inferred rule or a proposed default, listed below for `/speckit-intake-refine`.
- **"All functional requirements have clear acceptance criteria" stays ticked.** Each FR now maps to an acceptance scenario, edge case or success criterion:

  | Requirement | Acceptance criteria |
  |---|---|
  | FR-001, FR-002 | US1 AS-4, SC-011 |
  | FR-003 | US4, SC-003 |
  | FR-004 | US4 AS-6 |
  | FR-005 | US4 Independent Test, SC-004 |
  | FR-006 | Edge Cases (missing evidence artifact) |
  | FR-007 | US2 AS-1, AS-2 |
  | FR-008 | US2 AS-3, AS-4, Edge Cases (Review's regression test), SC-009 |
  | FR-009, FR-010 | US1 AS-1, AS-2, SC-001 |
  | FR-011 | US1 AS-3, US4 AS-3, Edge Cases (late approval) |
  | FR-012 | US5 AS-1, SC-005 |
  | FR-013, FR-014 | SC-001, US3 AS-6 (Shadow mode), Edge Cases (administrator bypass) |
  | FR-015 | US3 AS-2, Edge Cases (docs with migration) |
  | FR-016 | US3 Independent Test, SC-002 |
  | FR-017 | US3 AS-1, AS-3, SC-008 |
  | FR-018 | US1 AS-6, SC-011 |
  | FR-019 | US1 AS-5 |
  | FR-020 | US5 AS-2, AS-3 |
  | FR-021 | US3 AS-4, US3 Independent Test |
  | FR-022 | Edge Cases (flaky CI; skipped, cancelled or missing checks) |
  | FR-023 | Edge Cases (model switch) |
  | FR-024 | US3 AS-5, AS-6, SC-010 |
  | FR-025 | US4 AS-4, SC-004 |
  | FR-026 | US4 AS-5 |

- **"Feature meets measurable outcomes" stays ticked** as the usual spec-time readiness item: every requirement maps to a success criterion or scenario. It does not claim that anything has been built.

### Review findings applied

- **Risk table versus autonomy modes (medium)**: US3 and the new FR-021 treat the risk table as a ceiling. The active mode may require more, never less, and the gateway enforces that (spec 002 FR-025). The US3 Independent Test is now run in Guarded autonomous mode and repeated in Agent implementation mode.
- **Article VI changes not Critical (medium)**: FR-017 now makes the rule-defining scope Critical, and that outranks the "agent tools" High example (spec 002 FR-003). US3 AS-1 reads Critical, and AS-3 covers a gateway tool change.
- **FR-017 list incomplete (medium)**: the list now matches constitution Art. VI, adding role contracts and the constitution. It also covers spec 007's mode policy, promotion criteria, demotion limits and metric definitions, spec 003's path policy, this spec's own risk, category and applicability rules, and the list itself. It is one versioned list.
- **Review commits on the PR under review (medium)**: FR-008 forbids Review from pushing to the PR's branch. Review's tests stay off it. If PSE adopts them, they arrive as a new head, which FR-011 treats like any other. US2 AS-3 and AS-4 and SC-009 test this. The second pass below changed how the tests reach PSE.
- **SC-006 invented 25% (medium)**: now a no-regression bound against the Shadow-mode baseline, matching the report and spec 007 SC-004.
- **SC-005 ramp contradicts FR-012 (medium)**: now 100% from the day the gate is enforced.
- **FR-020 untestable, invented "weekly review" (medium)**: fixed as described above.
- **SC-003 and SC-007 invented numbers (low)**: labeled proposed defaults. "Medium-sized" is renamed "a PR under 400 changed lines". SC-007 is measured on the MacBook host at the person's peak capacity.
- **FR-018 unverifiable (low)**: versioned security mapping with evidence per mapped requirement.
- **Circular schema ownership (low)**: spec 003 now owns the evidence-package and verdict field sets (003 FR-014, FR-019), as `specs/README.md` already says. FR-006 and FR-007 point to them and keep no second copy. The review suggested 006 as the owner, but 003 has already taken ownership in its own refinement. Pointing to 003 removes the circle without contradicting it.
- **Low and Medium rules only in prose; "human approval" undefined (low)**: FR-021 and FR-024.
- **Flaky fail-then-pass undefined (low)**: FR-022 and Edge Cases. SC-002 is unchanged, as the verdict advised.
- **Missed: approvals need separate accounts (medium)**: the person settled it (Q15). FR-024 requires the Review approval from Review's own bot account and human approvals from a person's account no credential of an agent can use. The 002 line in Dependencies names 002 FR-017 as what makes FR-013, FR-016 and FR-024 possible.

### Second-pass review findings applied

- **Review approval in Shadow mode (medium)**: FR-013 and FR-024 had made the constitution's "at least one Review approval" count only from Review's bot account, in every mode. In Shadow mode the gateway refuses every Review write (spec 002 FR-024) and a person approves and merges (spec 007 FR-002, US1), so no PR could have merged. FR-013 and FR-024 now apply the bot-account rule in Agent implementation mode and above. In Shadow mode a person's approving review on the current head satisfies FR-013, recorded next to Review's recommendation. Assumptions add that on a High or Critical PR the same review is also the human approval. US3 AS-6 tests it. All of this is marked "(inferred)" and listed below.
- **No tool for Review's test-only branch or PR (medium)**: "or its own test-only PR" is dropped; Review never opens a PR. FR-008 now says how the tests reach PSE. They go on a test-only branch the control plane created when it dispatched Review, where one exists. Otherwise, including in Shadow mode, they travel inside the verdict as the evidence of a finding. Both routes are marked "(inferred)". The first needs tools that specs 001 and 002 do not have yet (see "Outside this task's files"). US2, US2 AS-3 and the Edge Case now match.
- **Unmarked inferred rules (medium)**: "(inferred)" is added to FR-002 (per language or component), FR-013 and FR-024 (both approval definitions), FR-017 ("the list itself"), FR-020 (the mistake register), FR-021 (the definition of "Complete CI" for Medium) and FR-025 (the suite runs on every backend). Each is now in the list below.
- **SC-009 and adoption by merge (low)**: FR-008 now says that PSE adopts a test by committing it again under its own bot account. Review's commits are never merged, rebased or cherry-picked into the PR's branch. SC-009 now counts commits authored or pushed by Review's bot account, and US2 AS-4 says the test arrives as a commit PSE authored and pushed.
- **FR-018 versus SC-011 (low)**: every repository now keeps the security mapping. SSDF practices are always present, and the ASVS level and requirements only where the repository serves web applications or services. SC-011 checks the SSDF part for every repository, and the Key Entity matches.
- **FR-026 input from 008 not explained (low)**: a new Assumption says the Jev verdict is an optional input. It never blocks a verdict and is absent until 008 is built, so it is not a build edge, as spec 008 itself says. The Dependencies note below no longer says Jev's output is "not consumed".
- **Stale notes about other files (low)**: the notes under "Outside this task's files" are rewritten to match those files as they stand now.

### Review findings not applied

- **"The status context fixes the mechanism" (refuted)**: kept. FR-013 now also says the control plane's EVALUATE_MERGE_POLICY step (spec 001 TR-09) reads the same result, so the two layers line up.
- **"Article III listed but not cited inline" (refuted)**: not a defect. Inline citations of Art. I, III, VII and IX were added anyway, where requirements changed for other reasons.

### Inferred decisions awaiting the person

The person did not state these. Each is marked "(inferred)" in the spec and should go to `/speckit-intake-refine`:

- FR-002: the applicability record decides per language or component where a repository holds several.
- FR-003: the git-history.md and stuck-session cases in the suite.
- FR-006: each evidence-package test category maps to a verification layer.
- FR-008: how Review's tests reach PSE (a test-only branch the control plane creates at Review's dispatch, or inside the verdict), and adoption by PSE committing them again, never by merging Review's commits.
- FR-013 and FR-024, first bullet: the Review approval counts only from Review's bot account in Agent implementation mode and above. In Shadow mode a person's approving review satisfies it. This reads the constitution's "at least one Review approval" by mode, so the person should confirm the reading.
- FR-015: a head with no computed class is Critical, matching spec 002 FR-026.
- FR-017: this spec's own rules and applicability records, and the list itself, are in the rule-defining scope.
- FR-018: every repository keeps a security mapping, with SSDF practices always and ASVS only where it serves web applications or services, and the evidence rule.
- FR-020: "recurring" means 3 distinct PRs; the mistake register.
- FR-021: the meaning of "CI" for Low; the definition of "Complete CI" for Medium; complete CI for High and Critical.
- FR-022: how skipped, cancelled, missing and fail-then-pass results count.
- FR-024, second and third bullets: what counts as a human approval, and that bot-account approvals never do.
- FR-025: the agent-behavior suite runs on every model backend a role uses, with identical authority outcomes.
- FR-026: Jev's verdicts are evidence Review may cite, never a verdict on code.
- Edge Cases: BLOCKED_BY_ENV ends a Review session normally and is not, by itself, stuck.
- Assumptions: protected file patterns cover the rule-defining scope; the suite and CI run on the MacBook; one person gives every human approval; manifests are still built in Shadow mode, and there one review by the person is both the Review approval and the human approval; traceability does not need spec 004; Jev's cases read "not applicable" until spec 008 exists; FR-026's Jev input is not a build edge; a CI job as one option for publishing the gate in Shadow mode; the reading of Q10.

### Proposed defaults, not confirmed by the owner

- SC-003: 3 cases per area, within 2 months.
- SC-007: under 400 changed lines, 30 minutes, 90th percentile.
- FR-020: 3 distinct PRs make a mistake recurring.

The 0 and 100% targets in SC-001, SC-002, SC-004, SC-005 and SC-008 to SC-011 are not defaults. The constitution fixes them (Art. II, IV, VI, VIII).

### Deliberate exceptions to "no implementation details"

- **Gitea 28.x branch-protection features, status contexts and Gitea's combined-status behavior**: Gitea is fixed by the person (project intake Q1). The combined-status facts come from the Jev research report and are stated in Assumptions.
- **OWASP ASVS 5.0.0, NIST SSDF 1.1 and SLSA**: standards the report and the constitution require, not implementation choices.
- **Claude and Ollama** (Q7, Q14) in FR-025 and SC-004; **the MacBook Pro M4 Pro host** (Q22; data-model intake Q14) in SC-007 and Assumptions; **the OCaml, Rust and Python split** (Q10) in FR-002 and Assumptions. All of these are fixed by the person.
- **git-history.md** (data-model intake Q20) names a file the person fixed.

### Dependencies

The Dependencies section now matches the fixed dependency map: upstream 001, 002 and 003; downstream 007, with one line per edge saying what is consumed.

- The old "Related" line (004 and 005) is removed, because the map has no edge between 006 and either of them.
- What the review said 004 supplied (requirements traceability) now comes from spec 001's issue contract and spec 003's evidence package.
- What 005 and 009 define, and Jev's behavior from 008, are tested from outside by the agent-behavior suite and are not consumed (Assumptions).
- FR-026 does let Review cite a Jev verdict, which is an 008 output. It is an optional input: it never blocks a verdict and is absent until 008 is built. So it is not a build edge (Assumptions), which matches spec 008: "Review owns verdicts, and may cite Jev (spec 006 FR-026)".
- The 002 line names 002 FR-017 (one bot account per role) as what FR-013, FR-016 and FR-024 need, as the missed finding asked.

### Clarifications

The section was moved from just after the header to the last section, as this workflow requires. It carries answers from the project intake (Q1–Q4, Q6, Q7, Q10, Q13–Q22) and the data-model intake (Q8, Q14, Q17, Q20). Each line names its intake and question number. No `/speckit-clarify` session has run on this spec yet.

### Outside this task's files (for those specs' owners)

- **Specs 001 and 002 (missing tool for FR-008)**: Review has no way to get a test-only branch. Under spec 002 FR-005, `gitea.branch.create` belongs to the control plane, only at dispatch and under the dispatched session's write lease. Only PSE may call `gitea.pr.create`. Spec 002's Assumptions mention a push credential for PSE's account only, and spec 001 creates a branch only in the claim procedure for a PSE dispatch (001 FR-018). The owners of 001 and 002 are asked for two things: creating a test-only branch when the control plane dispatches Review, and a push path for Review's bot account limited to that branch. Until then, FR-008's other route applies: the tests travel inside the verdict.
- **Spec 003 US2 AS-3** lets Review add a regression test "on a test-only path". It should say the test is not pushed to the branch of the PR under review (this spec's FR-008).
- **Constitution Sync Impact Report**: it flags this checklist for a note saying the constitution "still reads v1.0.0". That note is now removed, so the warning can be cleared at the next amendment. This task does not edit the constitution.

All items above that are ticked are backed by the spec as written. The one unticked item ("Written for non-technical stakeholders") does not block `/speckit-clarify` or `/speckit-plan`.
