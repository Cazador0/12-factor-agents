# Specification Quality Checklist: Engineering Control Plane

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

- **Resolved markers**: FR-007 now reads "Events have no time limit." (project intake Q16), with SC-014 to check it. FR-021 now holds the person's peak capacity, "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20). It is enforced together with the subagent cap in FR-034 (project intake Q18) and checked by SC-010.
- **One marker remains** (FR-035): how the 3 agent sessions divide among Lead, PSE and Review. Either one session per role, or two PSE sessions may run at once on separable issues. This is the person's choice. It decides whether User Story 4's parallel dispatch (AS-3) can happen at all. Resolve it with `/speckit-clarify` or `/speckit-intake-refine` before `/speckit-plan`.
- **Unticked: "Requirements are testable and unambiguous"**. An earlier version ticked this item, but FR-009 then pointed to a transition table the spec never defined. The table now exists (TR-01 to TR-13). The item stays unticked only because FR-035 is open. Tick it once FR-035 is answered.
- **Unticked: "All functional requirements have clear acceptance criteria"**. FR-035 has no acceptance criterion until it is answered. Every other new requirement has one: FR-029 (US2 AS-6, SC-013), FR-030 (US2 AS-5, SC-009), FR-016 (US3 AS-4, SC-011), FR-032 (US3 AS-5, SC-012), FR-021 and FR-034 (US3 AS-6, SC-010), FR-031, FR-033 and FR-036 (Edge Cases, plus schema validation against spec 009).
- **Unticked: "Written for non-technical stakeholders"**. This item was ticked before, but it is not true. The readers are the engineering owner and the role agents, and the requirements use engineering terms that the constitution or the design fixed: HMAC-SHA256, idempotency key, mutation envelope, lease epoch. The User Stories stay in plain language. This item does not block planning.
- **Provenance correction**: the previous note said HMAC-SHA256 appears "because the owner fixed it (intake Q1, Q2)". That was wrong. Q1 is "Gitea only" and Q2 is "LangGraph service". HMAC-SHA256 comes from the report (§Event-driven communication) and from the constitution (Additional Constraints: Events). Technology named because the person fixed it: Gitea 28.x (Q1), the LangGraph service (Q2), SQLite (Q9), the OCaml/Rust/Python split (Q10, in Assumptions), Claude and Ollama (Q7, in Assumptions) and the MacBook Pro M4 Pro host (Q22; data-model intake Q14). These are constraints, not design choices, so the "no implementation details" items stay ticked.
- **Inferred rules awaiting the person**: the person did not state these. They are marked "(inferred)" in the spec and should go back to the person through `/speckit-intake-refine`:
  - FR-002: manual redelivery under a new identifier counts as a duplicate.
  - FR-003: a person's account gets `actor_role` `person`.
  - FR-009: the from→to pairs TR-06, TR-07, TR-10 and TR-12.
  - FR-017: Lead records the recovery outcome.
  - FR-023: the write set is split into a Lead declaration plus the scheduler's estimate.
  - FR-024: `expected_version` is a per-issue counter kept by the control plane.
  - FR-028: the capacity caps are Critical-risk rules.
  - FR-030: the mode gate fails closed to Shadow until spec 007 supplies the modes.
  - FR-031: the System actor has its own Gitea bot account.
  - FR-034: subagents work under their parent session's lease.
  - FR-036: a person's out-of-table move is surfaced, never undone.
  - Assumptions: the lease TTL and retry defaults, and the reading of Q10.
- **Success Criteria numbers are proposed defaults** (Assumptions; project intake row S9 is still open). This covers the 24-hour soak (SC-010), the 4-hour heartbeat run (SC-011) and the 50 late writes (SC-012). SC-004 now says it is a stress test above the stated capacity.
- **Dependencies** now match the fixed dependency map. Upstream: 009. Downstream: 002, 003, 004, 005, 006, 007, 008. Formats for traces and checkpoints come from 009, not from 005, which removes the hidden 001→005 back-edge. 004's completeness result and 007's modes plug into gate points that 001 owns (FR-029, FR-030), and both fail closed. The requirements that write to Gitea are implemented after 002 without making 002 upstream.
- **Outside this task's files**: `specs/README.md` still shows 001 with no upstream and omits 008 and 009, and spec 002 Assumptions still cite the retry defaults as "matching spec 001" without marking them proposed. Both need updating to match.
- Items marked incomplete need spec updates or the person's answer before `/speckit-plan`. The only blocking one is FR-035. The "non-technical stakeholders" item is explained above and does not block.
