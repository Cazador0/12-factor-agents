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
- **Unticked: "Requirements are testable and unambiguous"**. An earlier version ticked this item, but FR-009 then pointed to a transition table the spec never defined. The table now exists (TR-01 to TR-15) with a list of refusal reasons and WAIT reasons, so a refusal has expected text to test against. This review round also fixed five ambiguities: the epoch fence now compares epochs per issue or per part (FR-015, FR-032); the fence's scope is limited to writes through the control plane or the gateway (FR-032, SC-012); `session_id` is no longer taken from a role's bot account (FR-003); Ready to Merge has exits for a failed check or a changes-requested review (TR-14, TR-15); and Blocked no longer contradicts TR-12 on Done (FR-008). The item stays unticked only because FR-035 is open. Tick it once FR-035 is answered.
- **Unticked: "All functional requirements have clear acceptance criteria"**. FR-035 has no acceptance criterion until it is answered. The previous note claimed FR-031 and FR-033 were covered by Edge Cases; that was wrong, because no edge case, scenario or success criterion covered them. They now have one each. Every other requirement added or changed in review has one too:
  - FR-029 (US2 AS-6, SC-013); FR-030, including read-only analysis sessions in Shadow (US2 AS-5, SC-009); FR-031 (US2 AS-7); FR-033 (SC-015).
  - FR-016 (US3 AS-4, SC-011); FR-032 and per-part epochs (US3 AS-5, AS-7, SC-012); FR-021 and FR-034 (US3 AS-6, SC-010); FR-037 re-dispatch (US3 AS-8).
  - FR-003 `session_id` (US1 AS-5); FR-004's comment, label and board-move types (US1 AS-4, Edge Cases "Jev's labels and comments" and "A person moves a card"); FR-036 (Edge Case "A person moves a card"); TR-14 and TR-15 (Edge Case "A check fails or a review requests changes after Ready to Merge").
- **Unticked: "Written for non-technical stakeholders"**. This item was ticked before, but it is not true. The readers are the engineering owner and the role agents, and the requirements use engineering terms that the constitution or the design fixed: HMAC-SHA256, idempotency key, mutation envelope, lease epoch. The User Stories stay in plain language. This item does not block planning.
- **Provenance correction**: the previous note said HMAC-SHA256 appears "because the owner fixed it (intake Q1, Q2)". That was wrong. Q1 is "Gitea only" and Q2 is "LangGraph service". HMAC-SHA256 comes from the report (§Event-driven communication) and from the constitution (Additional Constraints: Events). Technology named because the person fixed it: Gitea 28.x (Q1), the LangGraph service (Q2), SQLite (Q9), the OCaml/Rust/Python split (Q10, in Assumptions), Claude and Ollama (Q7, in Assumptions) and the MacBook Pro M4 Pro host (Q22; data-model intake Q14). These are constraints, not design choices, so the "no implementation details" items stay ticked.
- **Inferred rules awaiting the person**: the person did not state these. They are marked "(inferred)" in the spec and should go back to the person through `/speckit-intake-refine`:
  - FR-002: manual redelivery under a new identifier counts as a duplicate.
  - FR-003: a person's account gets `actor_role` `person`; `session_id` is resolved from the lease records and capacity registry, and left empty when not exactly one session of the role is active on the account.
  - FR-004: the `issue.commented`, `issue.label_changed` and `issue.board_moved` types, and deriving `issue.board_moved` from a board re-read if Gitea 28.x sends no webhook for a column move.
  - FR-009: the from→to pairs TR-06, TR-07, TR-10, TR-12, TR-14 and TR-15, and the list of refusal and WAIT reasons.
  - FR-015 and FR-032: the epoch is scoped to the issue, or to the issue and part when Lead partitions it.
  - FR-017: Lead records the recovery outcome.
  - FR-021: holding a dispatch above the stated capacity as WAIT "capacity" (also US3 AS-6, Edge Case "Capacity full", SC-010). The person gave Q20 as the peak capacity the system "must sustain", not as a ceiling. The subagent cap in FR-034 is backed by the person's "At most" (Q18); the session ceiling is not.
  - FR-023: the write set is split into a Lead declaration plus the scheduler's estimate.
  - FR-024: `expected_version` is a per-issue counter kept by the control plane.
  - FR-028: the capacity caps are Critical-risk rules.
  - FR-030: the mode gate fails closed to Shadow until spec 007 supplies the modes; starting a read-only analysis session with no write lease is not consequential, so Shadow allows it.
  - FR-031: the System actor has its own Gitea bot account.
  - FR-034: subagents work under their parent session's lease.
  - FR-036: a person's out-of-table move is surfaced, never undone.
  - FR-037: the re-dispatch procedure for resume, reassign and RETURN_TO_PSE with no PSE lease held, including the branch-head check and no board move.
  - Edge Case "Removed person or agent": raw deliveries are anonymized too, keep their receipt-time verification result and body hash, and are never re-verified.
  - Assumptions: the lease TTL and retry defaults, and the reading of Q10.
- **Success Criteria numbers are proposed defaults** (Assumptions; project intake row S9 is still open). This covers the 24-hour soak (SC-010), the 4-hour heartbeat run (SC-011) and the 50 late writes (SC-012). SC-004 now says it is a stress test above the stated capacity.
- **Dependencies** now match the fixed dependency map. Upstream: 009. Downstream: 002, 003, 004, 005, 006, 007, 008. Formats for traces and checkpoints come from 009, not from 005, which removes the hidden 001→005 back-edge. 004's completeness result and 007's modes plug into gate points that 001 owns (FR-029, FR-030), and both fail closed. The requirements that write to Gitea are implemented after 002 without making 002 upstream.
- **Earlier cross-file note withdrawn**: the previous note said `specs/README.md` and spec 002 were out of date. Both had already been fixed: the README row for 001 shows upstream 009 and downstream 002 to 008 and lists 008 and 009, and spec 002's retry-defaults assumption now says "These are proposed defaults the owner has not confirmed."
- **Outside this task's files, raised by this round**:
  - Spec 002's actor board-move table (FR-005) lists TR-01 to TR-13 only. It needs TR-14 for review and TR-15 for system.
  - Spec 008's User Story 2 (its narrative, Independent Test and AS-3) and SC-004 say a push that presents a revoked epoch is refused or never lands. Spec 001 now refuses only writes through the control plane or the gateway (FR-032), so those statements hold only if spec 008's open item on a forge-side fence is answered with a required status check.
- Items marked incomplete need spec updates or the person's answer before `/speckit-plan`. The only blocking one is FR-035. The "non-technical stakeholders" item is explained above and does not block.
