# Specification Quality Checklist: Independent Quality Assurance and Evidence Gates

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Updated**: 2026-10-22 (refinement: verified review findings, project and data-model intake answers, fixed dependency map; second pass: seven verified findings, listed under "Second-pass review findings"; answers pass: specify-phase decisions R1, R2, R3, R4, R5, R7 and R8, listed under "Phase Refinements answers applied"; R6 does not apply; third pass: eighteen verified findings on the answers pass, listed under "Third-pass review findings applied")
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs). Deliberate exceptions are listed in Notes.
- [x] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain. One marker is open in FR-013: how a pull request from a branch a person pushed, which is every pull request in Shadow mode, meets the required `lease-epoch` check. It is the same question as spec 001 FR-038 and spec 002 FR-038. See Notes.
- [x] Requirements are testable and unambiguous. Inferred rules and proposed defaults are listed in Notes. FR-013's `lease-epoch` rule is testable as written (required on `main` once a person adds it; posted only on agent-branch heads, per the Key Entity and FR-005, a posting design inferred in specs 001 and 002); the open marker may widen it to people's pull requests. FR-005's status case is limited to the gateway and to agent actors, so CI's own statuses do not fail it (third pass).
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details). SC-004 names Claude and Ollama, which the person fixed.
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded. This spec requires `lease-epoch` on `main` and tests both fences; who posts the status and how belongs to specs 001 and 002.
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
- **Unticked in the answers pass: "No [NEEDS CLARIFICATION] markers remain".** The earlier open question, how approvals are told apart, stays answered by the person ("Each role gets its own Gitea bot account.", project intake Q15) and sits in FR-024. The person's R7 answer ("Both") added a required `lease-epoch` status, and that raised a new question this spec cannot settle alone. The control plane posts the status only on agent-branch heads, and the gateway refuses every System write in Shadow mode. In Shadow mode no write lease is granted, so every pull request comes from a branch a person pushed (inferred), and once a person makes `lease-epoch` required, none could merge. That would block US3 AS-6 and the Shadow-mode merges behind SC-006's baseline. FR-013 now carries one marker, worded as the same question as spec 001 FR-038 and spec 002 FR-038, so one answer settles all three. Every other gap is settled with an inferred rule or a proposed default, listed below for `/speckit-intake-refine`.
- **"All functional requirements have clear acceptance criteria" stays ticked.** Each FR now maps to an acceptance scenario, edge case or success criterion:

  | Requirement | Acceptance criteria |
  |---|---|
  | FR-001, FR-002 | US1 AS-4, SC-011 |
  | FR-003 | US4, US4 AS-7 (late push and stale-epoch write, R7), AS-8 (one session per role, R1), AS-9 (racing claims, R1), SC-003 |
  | FR-004 | US4 AS-6 |
  | FR-005 | US4 Independent Test, US4 AS-10 (status and `jev/` label containment, R7, R8), SC-004 |
  | FR-006 | Edge Cases (missing evidence artifact) |
  | FR-007 | US2 AS-1, AS-2 |
  | FR-008 | US2 AS-3, AS-4, Edge Cases (Review's regression test), SC-009 |
  | FR-009, FR-010 | US1 AS-1, AS-2, SC-001 |
  | FR-011 | US1 AS-3, US4 AS-3, Edge Cases (late approval) |
  | FR-012 | US5 AS-1, SC-005 |
  | FR-013, FR-014 | SC-001, US3 AS-6 (Shadow mode), US4 AS-7 (`lease-epoch`), Edge Cases (administrator bypass, late push, a person's pull request) |
  | FR-015 | US3 AS-2, Edge Cases (docs with migration) |
  | FR-016 | US3 Independent Test, SC-002 |
  | FR-017 | US3 AS-1, AS-3, Edge Cases (a PR that builds an approved gateway tool), SC-008 |
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

### Phase Refinements answers applied (project intake R1–R8)

Source: the "## Phase Refinements" table of `.specify/intakes/agent-engineering-team/intake.md`. Each applied answer has a Clarifications line in the exact form of the intake row. Spec 006 had not been touched by the earlier round that applied R2–R4 to other specs, so this pass also checks those three against this file.

- **R1, one session per role ("One per role (Recommended)")**: the concurrency case "two PSEs claiming one issue" assumed two PSE sessions at once and is replaced. FR-003 now tests that a second session of a role, or a second issue's dispatch while one is in build, waits with the reason "capacity", and that two claims on one issue or part grant at most one lease (spec 001 FR-035). US4 and its new AS-8 and AS-9 match (the racing claims got their own AS-9 in the third pass). SC-007 and the Scale assumption name one session each for Lead, PSE and Review. Write-set serialization is not named in this spec, so nothing else changed.
- **R2, owner approves Lead as implementation worker, per issue**: this spec had assumed that only PSE implements and opens PRs, and that Lead always arbitrates. FR-006 now says Lead attaches the evidence package on a granted issue. FR-008 says Lead adopts Review's tests there and can open PRs (spec 002 FR-031). The arbitration Edge Case sends a dispute on a granted issue to a person (spec 003 FR-008, FR-010). R2 itself says only who approves the grant; routing the dispute to a person is inferred, as spec 003 FR-008 marks it, and the third pass marks it "(inferred)" here too. US2, US2 AS-4, the Review-test Edge Case and the evidence-package Key Entity now name Lead on a granted issue as well (third pass). The 003 dependency line names the grant.
- **R3, both ways to apply the bridge's plan in Shadow mode**: this spec's statement that the gateway refuses every Review write in Shadow mode stays true. FR-013 now says the human-approved plan write covers only the plan's entries (R3), never a review or a merge (spec 002 FR-037, inferred there). R3 says nothing about reviews or merges, so the third pass marks that limit inferred, as spec 007 FR-002 does. The 002 dependency line names it.
- **R4, read-only search approved**: FR-017 and a new Edge Case say that the PR that builds an approved gateway tool is still Critical. It merges only with a person's approving review on its head (inferred). The person's answer approves the design, not the PR.
- **R5, "+30% in 3 months (Recommended)"**: SC-006 now cites the guardrail that the R5 question fixed for whichever target was picked, and that spec 007 SC-004 keeps (no worse than the Shadow-mode baselines), and names the target as spec 007's. The person chose only the headline option; the guardrail wording is the question's, not the person's (third pass). The Assumption that said the owner had not confirmed a headline target is replaced. R5 confirms none of this spec's proposed defaults.
- **R7, "Both"**: FR-013 requires `lease-epoch` on `main`, which a person adds to the required status checks (Art. VI). It also says the status is not a manifest category and that the inferred design (who posts the status, fail closed, one narrow System-only tool) lives in specs 001 and 002. FR-003 adds the late-push failure-recovery case, and FR-005 adds the containment case that, through the gateway, only System posts a status and only `lease-epoch`. US4 AS-7 tests the first and AS-10 the second (third pass; before it, AS-7 was said to test both, but it tests only the first). FR-008 explains why tests adopted under a write lease pass the check (spec 003 FR-039), and that in Shadow mode a person's adopting commit falls under the open FR-013 marker. FR-017 names the required-check list as rule-defining, and a new Key Entity and two Edge Cases cover the status. The CI assumption now says the gateway posts no status but `lease-epoch` in any mode, so the manifest's status is published outside the gateway in every mode. This spec never said the forge-side fence was an open question, so there was nothing to remove. The answer raised the open question in FR-013 (see "Unticked in the answers pass").
- **R8, "Role labels + summary (Recommended)"**: FR-005's Jev containment case names the `jev/` scope, meaning the three summary and nine role labels (spec 002 FR-027), and adds that Jev creates no label and posts no status. FR-026 says labels only show verdicts and that Review cites Jev's comment, never a label alone (inferred). US4 matches.

### Answers that do not apply

- **R6, "60 min, per role later (Recommended)"**: this spec sets no Jev window. The only place where Review's session length meets Jev is the BLOCKED_BY_ENV Edge Case. There the session ends normally with a checkpoint, so it never sits waiting, and the 60-minute window does not change it. The Edge Case used to add a general claim, that waiting on the environment is not by itself a stuck session, which R6 does govern: under spec 008 FR-015 only waiting on a person pauses the spinning clock. The third pass limits the Edge Case to the session that ends ("the PR waits, not the session"), so this spec makes no claim about a Review session that keeps waiting; spec 008 FR-015 judges it. SC-007's 30-minute target is a Review turnaround target, not a stuck rule.

### Third-pass review findings applied

A review of the answers pass found eighteen issues, each confirmed in the files before any change. Some repeat one another (FR-005 twice, the plan-write limit twice, the stale CI-job note twice, and the Key Entity in two findings); each was fixed once.

- **FR-005 and US4 stronger than R7 (medium, two findings)**: they said only the control plane could post any commit status. The spec's own CI assumption has CI and the merge evidence gate post statuses from outside the gateway, so the containment case would have failed against legitimate CI. R7 limits only the new gateway tool. FR-005 and US4 now say that through the gateway only System posts a status, and only `lease-epoch`, and that no role session, subagent or Jev posts any. "Requirements are testable and unambiguous" stays ticked on that corrected wording.
- **Posting design read as the person's (medium)**: the Key Entity, US4 AS-7, the late-push and person's-pull-request Edge Cases and the US4 narrative now mark the posting design "(inferred)". The person's "Both" is attached only to the two fences and to "can never merge".
- **FR-008 in Shadow mode (medium)**: the adopting commit carries an epoch only in a mode that grants write leases. A new FR-008 bullet says that in Shadow mode the tests travel inside the verdict as a recommendation, the person adopts them on the branch they pushed, and that commit falls under the open FR-013 marker.
- **"Cannot merge" without its condition (medium)**: US4 AS-7, the late-push Edge Case and FR-003's late-push bullet now hold only with `lease-epoch` among `main`'s required status checks, as spec 001 SC-016 states it. The Edge Case says what fences that head until a person adds the check. Requirement Completeness above now reads "once a person adds it".
- **Dispute routing on a granted issue (low)**: marked "(inferred)" and added to the inferred list.
- **Plan-write limit (low, two findings)**: FR-013 now cites spec 002 FR-037 "inferred there" for "never a review or a merge", the 002 dependency line matches, and the item is in the inferred list.
- **BLOCKED_BY_ENV and R6 (low)**: the Edge Case is limited to the session that ends; see "Answers that do not apply". No R6 Clarifications line is added, because the spec still sets and restates no Jev window.
- **FR-017 and the Key Entity (low)**: FR-017 names R4's search tools as approved and the `lease-epoch` tool as approved by a reading of "Both" (inferred). The Key Entity marks the posting design inferred in specs 001 and 002.
- **SC-006 attribution (low)**: the guardrail is the R5 question's, not words the person chose. SC-006 and the R5 entry above now say so.
- **AS-7 and the R7 containment case (low)**: AS-7 tested only the late push. A new US4 AS-10 covers the status containment case and Jev's `jev/` scope, and the FR-005 mapping row lists it.
- **AS-7 and AS-8 outcomes not set up (low)**: AS-7's When now sends the stale-epoch write and lease check. The racing claims moved from AS-8 into a new AS-9 with their own Given and When. No id was renumbered.
- **Lead on a granted issue (low)**: US2, US2 AS-4, the Review-test Edge Case and the evidence-package Key Entity now name Lead on a granted issue, and US2 and the Edge Case name the person in Shadow mode.
- **"Required check" (low)**: FR-009, US1 and FR-022 now say "required category" or "required manifest check", and FR-022 defines the latter. FR-013, FR-017, US3 AS-6, the Edge Cases, Assumptions and Dependencies use "required status checks" for branch protection.
- **Stale checklist notes (low, three findings)**: the CI-job item now reads "in every mode"; the note on specs 007 and 008 now says they already carry R5 and R8.

### Review findings not applied

- **"The status context fixes the mechanism" (refuted)**: kept. FR-013 now also says the control plane's EVALUATE_MERGE_POLICY step (spec 001 TR-09) reads the same result, so the two layers line up.
- **"Article III listed but not cited inline" (refuted)**: not a defect. Inline citations of Art. I, III, VII and IX were added anyway, where requirements changed for other reasons.

### Inferred decisions awaiting the person

The person did not state these. Each is marked "(inferred)" in the spec and should go to `/speckit-intake-refine`:

- FR-002: the applicability record decides per language or component where a repository holds several.
- FR-003: the git-history.md and stuck-session cases in the suite; the late-push case that tests both lease-epoch fences (R7), with `lease-epoch` among the required status checks and the control plane judging the head (US4 AS-7); the concurrency cases built on one session per role (R1), including two claims on one part from PSE and Lead under a grant (US4 AS-9).
- FR-005: the containment case that, through the gateway, only System posts a commit status, and only `lease-epoch` on the current head of an agent branch, and that no role session, subagent or Jev posts any status (US4 AS-10; the tool's limits are inferred in spec 002). The CI contexts and the merge evidence gate reach Gitea from outside the gateway and are not covered by this case.
- FR-006: each evidence-package test category maps to a verification layer; Lead attaches the package on an issue it holds under an implementation-worker grant (R2).
- FR-008: how Review's tests reach PSE (a test-only branch the control plane creates at Review's dispatch, or inside the verdict), and adoption by PSE, or by Lead on a granted issue, committing them again, never by merging Review's commits. In modes that grant write leases, this route is also why adopted tests carry a lease epoch and Review's own commits never reach the protected branch. In Shadow mode no write lease is granted, so the tests travel inside the verdict as a recommendation and the person adopts them on the branch they pushed; that commit records no epoch, and how it meets a required `lease-epoch` is the open FR-013 question.
- FR-013: `lease-epoch` is not a manifest category, and neither it nor the manifest stands in for the other. In Shadow mode every pull request comes from a branch a person pushed (the premise of the open marker). The human-approved plan write that Shadow mode allows never covers a review or a merge (R3 allows the plan write; the limit is inferred in spec 002 FR-037).
- FR-017: the `lease-epoch` status tool counts as approved because R7's "Both" is read that way; the person did not name the tool.
- FR-022: "required manifest check" means a check behind a category FR-021 requires; branch protection's required status checks, such as `lease-epoch`, are not manifest checks.
- Key Entities and Edge Cases: the control plane posts `lease-epoch` on agent-branch heads, failure for a missing or older epoch and success otherwise. Only the two fences are the person's (R7); the posting design is inferred in specs 001 and 002.
- FR-026: Jev's labels only show verdicts, and Review cites Jev's comment, never a label alone (R8).
- Edge Cases: a PR that builds a gateway tool a person approved (R4, R7) is still Critical and needs a person's approving review on its head.
- Edge Cases: a PSE–Review dispute on an issue Lead holds under an implementation-worker grant goes to a person, because Lead is the implementer there (R2 says only who approves the grant; spec 003 FR-008 marks the routing inferred).
- Assumptions: the manifest's status is published outside the gateway in every mode, because the gateway posts no status but `lease-epoch`; one Review session reviews the pull requests (R1).
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
- Edge Cases: BLOCKED_BY_ENV is a completed verdict, so the Review session ends normally with a checkpoint, and the PR waits, not the session.
- Assumptions: protected file patterns cover the rule-defining scope; the suite and CI run on the MacBook; one person gives every human approval; manifests are still built in Shadow mode, and there one review by the person is both the Review approval and the human approval; traceability does not need spec 004; Jev's cases read "not applicable" until spec 008 exists; FR-026's Jev input is not a build edge; a CI job as one option for publishing the gate, in every mode; the reading of Q10.

### Proposed defaults, not confirmed by the owner

- SC-003: 3 cases per area, within 2 months.
- SC-007: under 400 changed lines, 30 minutes, 90th percentile.
- FR-020: 3 distinct PRs make a mistake recurring.

The person's headline target ("+30% in 3 months (Recommended)", project intake R5) belongs to spec 007 SC-004 and confirms none of these defaults. SC-006 uses only the guardrail that the R5 question fixed for whichever target was picked.

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
- The answers pass adds no edge. What R1, R2, R3, R7 and R8 bring comes through the existing upstream edges: 001 FR-032, FR-035 and FR-038; 002 FR-027, FR-037 and FR-038; 003 FR-008, FR-010 and FR-039. FR-026 cites spec 008 FR-036 for what the labels show, and US4 AS-7 cites the stop ladder, but both are references only, like the existing Jev input. They are not build edges.

### Clarifications

The section was moved from just after the header to the last section, as this workflow requires. It carries answers from the project intake (Q1–Q4, Q6, Q7, Q10, Q13–Q22), the project intake's Phase Refinements (R1, R2, R3, R4, R5, R7, R8) and the data-model intake (Q8, Q14, Q17, Q20). Each line names its intake and question or row number. The R lines copy the row's question and answer and use the form "(project intake, R<n>)". R6 has no line, because it does not apply here. No `/speckit-clarify` session has run on this spec yet.

### Outside this task's files (for those specs' owners)

- **Specs 001 and 002 (missing tool for FR-008)**: Review has no way to get a test-only branch. Under spec 002 FR-005, `gitea.branch.create` belongs to the control plane, only at dispatch and under the dispatched session's write lease. Only PSE may call `gitea.pr.create`, or Lead on an issue it holds under an implementation-worker grant (spec 002 FR-031). Spec 002's Assumptions mention a push credential for PSE's account only, and spec 001 creates a branch only in the claim procedure for a PSE dispatch (001 FR-018). The owners of 001 and 002 are asked for two things: creating a test-only branch when the control plane dispatches Review, and a push path for Review's bot account limited to that branch. Until then, FR-008's other route applies: the tests travel inside the verdict.
- **Spec 003 US2 AS-3** lets Review add a regression test "on a test-only path". It should say the test is not pushed to the branch of the PR under review (this spec's FR-008).
- **Spec 003 FR-020 marker** asks how Review's regression tests reach the protected branch now that `lease-epoch` is required. This spec's FR-008 already takes its first option in modes that grant write leases: PSE, or Lead on a granted issue, commits the test again under its own lease (inferred). In Shadow mode the person who pushed the branch adopts the test, and that commit falls under the lease-epoch marker below. The owner of 003 may settle the marker the same way, or the person may choose otherwise. If so, FR-008 changes with it.
- **Specs 007 and 008**: specs 007 SC-004 and 008 FR-036 already carry R5 and R8. If a later pass changes their wording or numbering, SC-006 and FR-026 should follow.
- **Lease-epoch marker**: FR-013 here, spec 001 FR-038 and spec 002 FR-038 carry the same question. Whoever records the person's answer should settle all three together.
- **Constitution Sync Impact Report**: it flags this checklist for a note saying the constitution "still reads v1.0.0". That note is now removed, so the warning can be cleared at the next amendment. This task does not edit the constitution.

All items above that are ticked are backed by the spec as written. Two items are unticked. "Written for non-technical stakeholders" does not block `/speckit-clarify` or `/speckit-plan`. "No [NEEDS CLARIFICATION] markers remain" does not block `/speckit-clarify`. Planning can start, but the `lease-epoch` marker in FR-013 should be answered before a person makes `lease-epoch` a required check, or Shadow-mode merges stop.
