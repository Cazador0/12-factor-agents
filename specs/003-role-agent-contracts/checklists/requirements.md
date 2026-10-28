# Specification Quality Checklist: Role Agent Contracts (Lead, PSE, Review)

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain
- [ ] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **This round applied the person's Phase Refinements** from the project intake. Each answer was checked against the whole spec:
  - **R1** ("One per role (Recommended)" — one session each for Lead, PSE and Review; at most one issue in build at a time). It was already in the "Concurrent claims" edge case and Clarifications. This round removed what still assumed more than one PSE session:
    - FR-011: with one PSE session, the PSE holds at most one part's lease of a partitioned issue, and another part can be written at the same time only by Lead under an implementation-worker grant (spec 001 FR-035; inferred). Write-set serialization only orders queued work.
    - The "Nested subagents" edge case: a subagent holds no lease (spec 001 FR-034), commits only to its parent's branch under its parent's lease, and writes only its parent's part of a partitioned issue (inferred).
    - FR-010: while Lead holds a granted issue's write lease, that issue takes the one build slot (spec 001 FR-035; inferred). Lead's part lease beside the PSE's part is also marked (inferred).
    - "Concurrent claims" now says a second session of a role is held as WAIT "capacity" (spec 001 FR-035). Holding rather than refusing, and the duplicate ending without changes, are marked (inferred).
    - The Assumptions isolation line now says one working copy per session that holds a write lease, plus a read-only working copy for Review (inferred).
  - **R7** ("Both", read by the intake as two fences). It is applied as new FR-039, which carries the part that spec 001 FR-038 leaves to the role contracts. FR-039 states the two fences first. Everything after them is marked inferred, including the duty that every commit made under a write lease records that lease's epoch. It is applied in these places:
    - US4 AS-5 (a late push from a revoked session leaves a head that cannot merge);
    - the "Lease lost while alive" and "Head without its epoch" edge cases;
    - the Commit Epoch entity and SC-014;
    - the 001 and 002 Upstream lines, and the Art. IV and Art. VI lines;
    - a Clarifications line.

    The two fences are the person's. Everything else is marked "(inferred)": that commits record an epoch, the commit trailer as the form, who judges and posts, the fail-closed rule (also in the Art. IV line), that an ended grant's epoch counts as older, that the status judges heads only, the System-only tool, and that no role touches the status. Spec 003 never said the forge-side fence was open, so there was no such wording to remove.
  - **R3** (checked because FR-029 touches Shadow mode). FR-029 said that in Shadow mode a person carries out every recommendation. R3 adds a second path for the bridge's dry-run plan only: a person approves it and the gateway writes it (spec 002 FR-037). FR-029 now names that one exception, US3 AS-5 tests it, the Assumptions line on the bridge names it, and Clarifications records R3.
  - **R2** is still reflected in FR-010, the Implementation-Worker Grant entity, the "Lead asked to code" edge case, SC-013 and the Art. VI line. The R1 and R2 Clarifications lines use the form "(project intake, R<n>)".
  - **R5** (checked because the Assumptions line on targets quotes it). Its headline target belongs to spec 007 SC-004. The Assumptions line says that it sets none of this spec's numbers. Because that line now rests on R5, R5 also gets a Clarifications line, copied from its row, and is named in the Input line, as R3 is.
  - **Not applicable**:
    - R4: this spec uses no issue search or milestone lookup.
    - R6: this spec defers every Jev threshold to spec 008 and names no window.
    - R8: this spec names no `jev/*` label, and no role here writes one. Jev's label rights stay in spec 002 FR-027 and spec 008.
- **Verification fixes this round** (no FR or SC was renumbered):
  - The subagent contradiction is resolved one way. "Nested subagents" had said subagents never write the issue branch, while FR-039 and SC-014 counted subagent commits. Subagents may now commit to their parent's branch under the parent's lease (new FR-035 sub-bullet; inferred from data-model intake Q19, where git history records "which ... subagent made it"). FR-039, SC-014, the edge case and this checklist agree.
  - FR-039 now judges heads as spec 001 FR-038 does: when a pull request is opened or updated, with an ended grant's epoch counting as older. It says that the status judges heads only, so stale commits beneath a fresh head are left to the recovery assessment and the re-dispatch branch-head check. US4 AS-5 and "Lease lost while alive" now say "its head cannot merge", not "the commit can never merge".
  - FR-039's status ban cites FR-016 for PSE only. Extending it to Lead and Review is marked inferred.
  - "Head without its epoch" now uses a squash or an amend as its example. A plain rebase keeps commit trailers.
- **Unticked: "No [NEEDS CLARIFICATION] markers remain"**. FR-020 has one marker, which R7 created:
  - Review holds no write lease (spec 001 FR-015) and no branch or pull-request tool (spec 002 FR-005). Its test-only commits therefore record no epoch.
  - Once `lease-epoch` is required, a head made of those commits can never merge.
  - The marker asks how Review's regression tests should reach the protected branch.
- **Unticked: "Requirements are testable and unambiguous"**. FR-020 leaves that one route open. Its MUST NOT and MAY parts stay testable (US2 AS-3, SC-002). The earlier claim that every other requirement was unambiguous was wrong: the spec contradicted itself on whether subagents commit. That contradiction is fixed above. No other ambiguity is known, but this item stays unticked for FR-020. The definitions noted in earlier rounds still hold:
  - FR-023's execution phases are spec 005's lifecycle hooks.
  - FR-024's consequential steps are spec 005's traces and spec 001's consequential actions.
  - FR-027's joint stages need both roles' sign-off.
  - FR-036 releases the lease only after the escalation is posted.
- **Ticked: "All functional requirements have clear acceptance criteria"**:

  | Requirement | Acceptance criteria |
  |---|---|
  | FR-010 (grantor; build slot) | Edge Cases (Lead asked to code), US3 AS-6, SC-013 |
  | FR-011 (one PSE session) | Edge Cases (Concurrent claims, Nested subagents) |
  | FR-020 | US2 AS-3, SC-002 (the route to the protected branch is open) |
  | FR-028 | Edge Cases (Smokey and people) |
  | FR-029 (including the R3 exception) | US1 AS-4, US3 AS-5, SC-010 |
  | FR-030 | Edge Cases (model switch), SC-010 |
  | FR-031 | US3 AS-4, Edge Cases (Lead is the stuck session) |
  | FR-032 | US1 AS-1 |
  | FR-033 | SC-002 |
  | FR-034 | US2 AS-4 |
  | FR-035 (cap; subagent commits) | Edge Cases (Nested subagents), SC-011, SC-014 |
  | FR-036 | US4 AS-2, AS-4, SC-012 |
  | FR-037 | US1 AS-1, US2, US3 |
  | FR-038 | US4 AS-3 |
  | FR-039 | US4 AS-5, Edge Cases (Lease lost while alive, Head without its epoch), SC-014 |
  | SC-013 | Edge Cases (Lead asked to code) |

  US3 AS-5 (a person-approved bridge plan written in Shadow mode, and the same writes refused without that approval) and US3 AS-6 (a dispatch held as WAIT "capacity" while Lead holds a granted issue's lease) are new this round. Before them, the table cited criteria that did not test the R3 exception or the build slot.
- **Unticked: "Written for non-technical stakeholders"**. The readers are the engineering owner and the role agents. Requirements use terms the constitution or the design fixes, such as lease epoch, idempotency key, bot account, evidence package and commit status. The User Stories stay in plain language. This item does not block planning.
- **Technology named because the person fixed it**:
  - the LangGraph service (project intake Q2);
  - Gitea bot accounts, one per role (Q15);
  - Claude and Ollama, cloud and local (Q7, Q14; FR-030 and SC-010);
  - the MacBook Pro M4 Pro host (Q22; data-model intake Q14, in Assumptions and SC-011);
  - the OCaml/Rust/Python split (Q10, in Assumptions only);
  - a `lease-epoch` commit status that branch protection requires (R7; FR-039, SC-014).

  The commit trailer is named only as an example and is marked inferred. `schemas/jev-message.v1.json` is the path of the shared schema that the dependency map assigns to spec 009, not a design choice. These are constraints, so the "no implementation details" and "technology-agnostic" items stay ticked.
- **"Success criteria are measurable" stays ticked**:
  - SC-008 sets no target on purpose, but the rate is measured and reported.
  - SC-014 counts commits and merged heads in the existing SC-001, SC-006 and SC-012 runs.
- **"Feature meets measurable outcomes" stays ticked** as the standard spec-time readiness item: every success criterion traces to requirements that, once built, can meet it. It does not claim that anything has been built. The earlier note said that every requirement maps to a success criterion. That was false. Every requirement maps to an acceptance scenario, an edge case, a success criterion or its own testable wording, but these have no success criterion of their own:
  - FR-001, FR-002, FR-004 and FR-005 (contract form, no personas, contract changes, Lead's ownership), checked by their own wording;
  - FR-006 and FR-007 (US3 AS-1 and US3's Independent Test);
  - FR-010's build-slot bullet (US3 AS-6);
  - FR-011 (Edge Cases: Concurrent claims, Nested subagents);
  - FR-012 (US1's Independent Test: its first actions are reads);
  - FR-015 (US1 AS-2);
  - FR-021 (Edge Cases: Out-of-order events);
  - FR-025 and FR-027, checked by their own wording;
  - FR-031 (US3 AS-4; Edge Cases: Lead is the stuck session);
  - FR-034 (US2 AS-4);
  - FR-037 (US1 AS-1, US2, US3);
  - FR-038 (US4 AS-3).
- **Success Criteria numbers are proposed defaults** (Assumptions: "The owner has confirmed none of this spec's targets."):
  - This covers every sample size and rate, the one-business-day bound in SC-007, the 20 stuck-session drills in SC-012 and the "twice" deadlock threshold in Edge Cases.
  - SC-014's 0 follows the intake's reading of R7 ("a commit from a stale epoch can never merge"). The person's own answer was only "Both", so the 0 is not a target the person set. SC-014's 100% rests on the inferred FR-039 recording duty and is a proposed default like every other number here.
  - Row S9's headline target is answered for spec 007 only (R5).
- **Inferred rules awaiting the person**. The person did not state these. They are marked "(inferred)" in the spec and should go back through `/speckit-intake-refine`:
  - FR-028: Jev's status as a fourth, watchdog role outside the constitution's three engineering roles, amending no article; and no role may act as Smokey or any person.
  - FR-029: Jev's comment-and-label writes are not mode-gated (taken from spec 002 FR-024, itself inferred).
  - FR-008, FR-010, US3 AS-6 and Edge Cases (Lead asked to code):
    - Lead's branch name;
    - disputes on a granted issue go to a person;
    - a granted issue takes the one build slot;
    - Lead may hold one part's lease beside the PSE's part.
  - FR-011 and Edge Cases (Nested subagents, Concurrent claims): with one PSE session, a second concurrent part owner can only be Lead under a grant; a second session of a role is held, not refused, and ends without changes if it runs anyway.
  - FR-035 and Edge Cases (Nested subagents): a subagent may commit to its parent's branch, and only there, under its parent's lease; the parent stays the single write owner.
  - FR-031: an escalation about Lead's own session goes to a person.
  - FR-014 and FR-019: this spec owns the evidence-package and verdict field sets.
  - FR-025: "reasoning stops making progress" is judged from traces and events, never from visible reasoning chains.
  - FR-027: joint sign-off for jointly owned stages.
  - FR-033: the path policy, its fail-closed default and its Critical risk class.
  - FR-034: QA issues do not widen a pull request's scope.
  - FR-035: subagents work under the parent's role, bot account and lease (as spec 001 FR-034); Jev runs no subagents; at the cap, a session works itself or waits.
  - FR-036: finishing or handing off is a normal end; "stop" means ending work; the escalation is posted before the lease is released; a failed post falls back to the recovery assessment.
  - FR-038: Jev's nudges are advisory.
  - FR-039, US4 AS-5, the Commit Epoch entity and Edge Cases (Head without its epoch, Lease lost while alive):
    - every commit under a write lease records its lease's epoch;
    - the commit trailer as the form;
    - a commit records only the epoch its session holds;
    - the control plane judges heads when a pull request is opened or updated, and posts through a System-only tool;
    - the fail-closed rule, with an expired, stopped or revoked grant's epoch counting as older (as spec 001 FR-038);
    - the status judges heads only, and stale commits beneath a fresh head are left to the recovery assessment and the re-dispatch branch-head check;
    - no role touches the status (FR-016 covers PSE; the extension to Lead and Review is new);
    - a failing head is cured by a new commit.
  - Assumptions: the reading of Q10; that 10 agents equal 3 sessions, 6 subagents and Jev; Review's read-only working copy.
- **Dependencies** match the fixed dependency map:
  - Upstream: 001, 002, 005. Downstream: 006, 007, 008. 004 is neither. The R3 exception reaches 003 through spec 002 FR-037, not from 004, and the Assumptions line on the bridge says so.
  - The 001 line names the `lease-epoch` status (001 FR-038) and the one-session-per-role division (001 FR-035).
  - The 002 line names the human-approved plan writes (002 FR-037) and the System-only status tool (002 FR-038).
  - The Implementation order bullet now also names User Story 4 scenario 5, whose revocation happens at the stop ladder's hard-stop step. FR-031, FR-038 and US4 AS-3 and AS-5 come after 008, and the stop request's format is 009's schema.
- **Clarifications** carry over answers from the project and data-model intakes, now including R1, R2, R3, R5 and R7, each copied from its Phase Refinements row. No `/speckit-clarify` session has run on this spec yet. The section stays last, as this workflow requires.
- **Outside this task's files** (for the specs' owners):
  - **spec 001, implementation-worker grant** (still open):
    - 001 has no grant record. Its only path to a write lease is TR-04, which dispatches a PSE.
    - TR-05 and TR-08 can be requested only by "PSE holding the write lease".
    - 003 FR-010 and 002 FR-031 need 001 to add: a per-issue grant record whose grantor is the owner (R2), a dispatch that grants Lead the write lease, and TR-05 and TR-08 requestable by that Lead.
    - 001 FR-035 now answers whether a Lead-built issue counts toward R1's one issue in build (yes, inferred), so that part of the earlier follow-up is closed.
  - **spec 001 FR-035** (closed): it now carries R1, so its earlier marker is resolved.
  - **specs 001 and 002, Review's commits** (see the FR-020 marker): Review holds no write lease (001 FR-015) and has no branch or pull-request tool (002 FR-005). Whichever way the person answers, one of these may need to change.
  - **specs 001 and 002, people's pull requests** (their FR-038 markers): in Shadow mode every commit and pull request is a person's, because no write lease is granted in Shadow mode (spec 001 FR-038; 003 FR-029, US1 AS-4). The R3 exception covers only the bridge plan's issue writes, never branches or pull requests (spec 002 FR-037). Until those markers are answered, a person's pull request cannot pass a required `lease-epoch` check.
  - **spec 008** (closed): 008 FR-029 step 5 now lists both fences and cites 003 FR-039 for the recording duty, FR-015 sets 60 minutes under R6, and FR-036 names the 12 labels under R8. 008 now agrees with 003 FR-039. 003 names no `jev/*` label.
  - **spec 001 FR-017 and spec 002**: 003 FR-036 has a stuck PSE post its escalation while it still holds its write lease, and release the lease afterwards (inferred).
    - 001 FR-017's "released by a session that stopped (checkpoint and stop, then escalate)" should say that the release follows the escalation.
    - 002's `gitea.issue.comment` row already allows the escalation. Its owner should confirm that the escalation is PSE's last write under the lease.
  - **spec 004**: it maps one task to one issue (SC-002), while the report and spec 001's Issue Contract allow several task IDs per issue. This spec works either way.
- **Blocking**:
  - Planning is blocked only by FR-020's marker, and only for Review's test authoring. Everything else can be planned.
  - The "non-technical stakeholders" item does not block.
  - The spec 001 implementation-worker follow-up must land before FR-010 is implemented.
