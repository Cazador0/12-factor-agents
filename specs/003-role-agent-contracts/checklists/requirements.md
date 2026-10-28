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

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
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

- **Ticked: "No [NEEDS CLARIFICATION] markers remain"**. The last marker, FR-010's grantor, is answered. The person chose "Owner, per issue (Recommended)" — a person (the owner) approves each switch, per issue (project intake, Phase Refinements Specify R2). That answer was recorded after this spec was first written, so the marker had gone stale. FR-010, the Implementation-Worker Grant entity, the "Lead asked to code" edge case, SC-013 and the Art. VI line now name the owner as grantor, and a Clarifications line records R2. Lead never grants the mode to itself (Art. VI).
- **Ticked: "Requirements are testable and unambiguous"**. It was unticked only because of FR-010's grantor, which R2 now answers. FR-023, FR-024 and FR-027 already had definitions:
  - FR-023's execution phases are tied to spec 005's lifecycle hooks.
  - FR-024's consequential steps are tied to spec 005's traces and spec 001's list of consequential actions.
  - FR-027 says a jointly owned stage needs both roles' sign-off.

  This round also removed four contradictions:
  - FR-036: a stuck PSE could not post its escalation after stopping, because the gateway lets PSE comment only on its leased issue (spec 002 FR-005). "Stop" now means ending work, and the lease is released only after the escalation is posted (inferred).
  - FR-029, SC-010 and FR-035 now apply to Lead, PSE and Review and their subagents. Jev's comment-and-label writes are not mode-gated (spec 002 FR-024), and Jev runs no subagents (project intake Q20).
  - FR-031 and US3 AS-4: a hard stop is carried out only at the stop ladder's hard-stop step, after the grace window (spec 001 FR-032; spec 008).
  - SC-012: the resume part applies only to drills whose recovery outcome is resume or reassign.

  FR-010 is unambiguous, but it cannot be built or tested end to end until spec 001 defines the grant record and Lead's write-lease path (see the follow-ups below).
- **Ticked: "All functional requirements have clear acceptance criteria"**. It was unticked only because FR-010's grantor had no criterion. It now has one, and every other requirement listed here has one:

  | Requirement | Acceptance criteria |
  |---|---|
  | FR-010 (grantor) | Edge Cases (Lead asked to code), SC-013 |
  | FR-028 | Edge Cases (Smokey and people) |
  | FR-029 | US1 AS-4, SC-010 |
  | FR-030 | Edge Cases (model switch), SC-010 |
  | FR-031 | US3 AS-4, Edge Cases (Lead is the stuck session) |
  | FR-032 | US1 AS-1 |
  | FR-033 | SC-002 |
  | FR-034 | US2 AS-4 |
  | FR-035 | Edge Cases (nested subagents), SC-011 |
  | FR-036 | US4 AS-2, AS-4, SC-012 |
  | FR-037 | US1 AS-1, US2, US3 |
  | FR-038 | US4 AS-3 |
  | SC-013 | Edge Cases (Lead asked to code) |

- **Unticked: "Written for non-technical stakeholders"**. This item was ticked before, but it is not true. The readers are the engineering owner and the role agents. Requirements use terms fixed by the constitution or the design, such as lease epoch, idempotency key, bot account and evidence package. The User Stories stay in plain language. This item does not block planning.
- **Technology named because the person fixed it**:
  - the LangGraph service (project intake Q2);
  - Gitea bot accounts, one per role (Q15);
  - Claude and Ollama, cloud and local (Q7, Q14; FR-030 and SC-010);
  - the MacBook Pro M4 Pro host (Q22; data-model intake Q14, in Assumptions and SC-011);
  - the OCaml/Rust/Python split (Q10, in Assumptions only).

  `schemas/jev-message.v1.json` (FR-038, Stop Request, Dependencies) is the repository path of the shared schema that the dependency map assigns to spec 009, not a design choice. These are constraints, so the "no implementation details" and "technology-agnostic" items stay ticked.
- **"Success criteria are measurable" stays ticked**. SC-008 sets no target on purpose, but the rate is measured and reported, so it is measurable. SC-006 was split: the completion rate stays in SC-006, and 0 repeated external writes is now SC-009, so repeated writes are never tolerated. SC-003 now says its 95% is an evaluation tolerance that does not relax FR-013.
- **"Feature meets measurable outcomes" stays ticked** as the standard spec-time readiness item: every requirement maps to a success criterion. It does not claim that anything has been built.
- **Success Criteria numbers are proposed defaults** (Assumptions; project intake row S9 is still open). This covers every sample size and rate, the one-business-day bound in SC-007, the 20 stuck-session drills in SC-012 and the "twice" deadlock threshold in Edge Cases.
- **Inferred rules awaiting the person**. The person did not state these. They are marked "(inferred)" in the spec and should go back through `/speckit-intake-refine`:
  - FR-028: Jev's status as a fourth, watchdog role outside the constitution's three engineering roles, amending no article; and no role may act as Smokey or any person.
  - FR-029: Jev's comment-and-label writes are not mode-gated (taken from spec 002 FR-024, itself inferred).
  - FR-008, FR-010 and Edge Cases (Lead asked to code): Lead's branch name, and disputes on a granted issue going to a person.
  - FR-031: an escalation about Lead's own session goes to a person.
  - FR-014 and FR-019: this spec owns the evidence-package and verdict field sets.
  - FR-025: "reasoning stops making progress" is judged from traces and events, never from visible reasoning chains.
  - FR-027: joint sign-off for jointly owned stages.
  - FR-033: the path policy, its fail-closed default and its Critical risk class.
  - FR-034: QA issues do not widen a pull request's scope.
  - FR-035: subagents work under the parent's role, bot account and lease (as spec 001 FR-034); Jev runs no subagents; at the cap, a session works itself or waits.
  - FR-036: finishing or handing off is a normal end; "stop" means ending work, the escalation is posted before the lease is released, and a failed post falls back to the recovery assessment.
  - FR-038: Jev's nudges are advisory.
  - Assumptions: the reading of Q10, and that 10 agents equal 3 sessions, 6 subagents and Jev.
- **Dependencies** match the fixed dependency map. Upstream: 001, 002, 005. Downstream: 006, 007, 008. 004 is neither, so the US3 Independent Test seeds issues directly instead of running the bridge, and FR-007 cites spec 001's Issue Contract instead of restating its sections. An **Implementation order** bullet now says that FR-031, FR-038 and US4 AS-3 are implemented and tested after 008, whose stop-ladder timing they use, and that the stop request's format is the Jev message schema owned by 009. Neither 008 nor 009 becomes upstream of 003. A Constitution line (v1.1.0, Art. I–IX) lists the articles.
- **Clarifications** carry over answers from the project and data-model intakes, now including the Specify-phase refinements R1 (one session per role) and R2 (owner grants Lead's implementation-worker mode, per issue). Each line names its intake and question or row number. No `/speckit-clarify` session has run on this spec yet. The section stays last, as this workflow requires, rather than moving to just after the header as `/speckit-clarify` would place it.
- **Outside this task's files** (for the specs' owners):
  - **spec 001, implementation-worker grant**: 001 has no implementation-worker grant or record. Its only path to a write lease is TR-04, which dispatches a PSE, and the moves to Review (TR-05, TR-08) can be requested only by "PSE holding the write lease". 003 FR-010 and 002 FR-031 need 001 to add: a per-issue implementation-worker grant record whose grantor is the owner (project intake R2); a dispatch that grants Lead the write lease on that issue; and TR-05 and TR-08 requestable by the Lead holding that lease. 001 should also say whether a Lead-built issue counts toward R1's "at most one issue in build at a time". Once 001 defines the grant, 003's Upstream 001 line should name it.
  - **spec 001 FR-035**: its marker asks the question that project intake R1 answers ("One per role (Recommended)").
  - **spec 001 FR-017 and spec 002**: 003 FR-036 now has a stuck PSE post its escalation while it still holds its write lease and release the lease afterwards (inferred). 001 FR-017's "released by a session that stopped (checkpoint and stop, then escalate)" should say that the release follows the escalation. 002 needs no matrix change, because its `gitea.issue.comment` row already lets PSE comment on its leased issue, but its owner should confirm that the escalation is PSE's last write under the lease.
  - **spec 004**: it maps one task to one issue (SC-002), while the report and spec 001's Issue Contract allow several task IDs per issue. This spec works either way.
- No item blocks `/speckit-plan`. The "non-technical stakeholders" item is explained above and does not block. The spec 001 implementation-worker follow-up must land before FR-010 is implemented.
