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

- [ ] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **One marker remains** (FR-010): who may grant Lead an implementation-worker grant. The person has not answered this. The marker now offers only options that the constitution allows: the owner per issue, or a human-approved standing policy rule that the control plane applies. Lead granting itself the mode is excluded, because it would widen Lead's own authority (Art. VI). How the grant is enforced is no longer open: the control plane records it per issue, the gateway honors it (spec 002 FR-031), Lead may not request review, schedule a merge or arbitrate on that issue, and disputes there go to a person. Resolve the grantor with `/speckit-clarify` or `/speckit-intake-refine` before `/speckit-plan`.
- **Unticked: "Requirements are testable and unambiguous"**. The previous version ticked this item although FR-010 was open. The item stays unticked only because of FR-010's grantor. FR-023, FR-024 and FR-027 were also ambiguous, and they now have definitions:
  - FR-023's execution phases are tied to spec 005's lifecycle hooks.
  - FR-024's consequential steps are tied to spec 005's traces and spec 001's list of consequential actions.
  - FR-027 says a jointly owned stage needs both roles' sign-off.
- **Unticked: "All functional requirements have clear acceptance criteria"**. FR-010's grantor has no acceptance criterion until the person answers. Every other new requirement has one:

  | Requirement | Acceptance criteria |
  |---|---|
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

  These are constraints, not design choices, so the "no implementation details" and "technology-agnostic" items stay ticked.
- **"Success criteria are measurable" stays ticked**. SC-008 sets no target on purpose, but the rate is measured and reported, so it is measurable. SC-006 was split: the completion rate stays in SC-006, and 0 repeated external writes is now SC-009, so repeated writes are never tolerated. SC-003 now says its 95% is an evaluation tolerance that does not relax FR-013.
- **"Feature meets measurable outcomes" stays ticked** as the standard spec-time readiness item: every requirement maps to a success criterion. It does not claim that anything has been built.
- **Success Criteria numbers are proposed defaults** (Assumptions; project intake row S9 is still open). This covers every sample size and rate, the one-business-day bound in SC-007, the 20 stuck-session drills in SC-012 and the "twice" deadlock threshold in Edge Cases.
- **Inferred rules awaiting the person**. The person did not state these. They are marked "(inferred)" in the spec and should go back through `/speckit-intake-refine`:
  - FR-028: no role may act as Smokey or any person.
  - FR-010: Lead's branch name, and disputes going to a person.
  - FR-031: an escalation about Lead's own session goes to a person.
  - FR-014 and FR-019: this spec owns the evidence-package and verdict field sets.
  - FR-025: "reasoning stops making progress" is judged from traces and events, never from visible reasoning chains.
  - FR-027: joint sign-off for jointly owned stages.
  - FR-033: the path policy, its fail-closed default and its Critical risk class.
  - FR-034: QA issues do not widen a pull request's scope.
  - FR-035: at the cap, a session works itself or waits.
  - FR-036: finishing or handing off is a normal end.
  - FR-038: Jev's nudges are advisory.
  - Assumptions: the reading of Q10, and that 10 agents equal 3 sessions, 6 subagents and Jev.
- **Dependencies** now match the fixed dependency map. Upstream: 001, 002, 005. Downstream: 006, 007, 008. 004 is neither, so the US3 Independent Test now seeds issues directly instead of running the bridge, and FR-007 cites spec 001's Issue Contract instead of restating its sections. A Constitution line (v1.1.0, Art. I–IX) was added.
- **Clarifications** carry over answers from the project and data-model intakes. Each line names its intake and question number. No `/speckit-clarify` session has run on this spec yet. The section stays last, as this workflow requires, rather than moving to just after the header as `/speckit-clarify` would place it.
- **Outside this task's files** (for the specs' owners):
  - spec 004 still lists 003 as Downstream, and `specs/README.md` still omits 008 and 009.
  - spec 007's Upstream line still describes 003 as supplying "which actions each role may take in each mode". It should read "role contracts whose permissions each mode restricts" (FR-029).
  - spec 006 FR-006 and FR-007 restate the evidence-package and verdict fields, which this spec now owns (FR-014, FR-019).
  - spec 004 maps one task to one issue, while the report and spec 001's Issue Contract allow several task IDs per issue. This spec now works either way.
- Items marked incomplete need spec updates or the person's answer before `/speckit-plan`. The only blocking one is FR-010's grantor. The "non-technical stakeholders" item is explained above and does not block.
