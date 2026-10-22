# Specification Quality Checklist: Gitea MCP Gateway

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Updated**: 2026-10-22 (refinement: review findings, project intake Q15 and Q16, Jev research report, alignment with the refined spec 001)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs). Deliberate exceptions are listed in Notes.
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders. Stories and priorities are in plain language; the requirement tables use the contract vocabulary the constitution and report fix (see Notes).
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
- [x] No implementation details leak into specification. Deliberate exceptions are listed in Notes.

## Notes

### Markers

Both earlier `[NEEDS CLARIFICATION]` markers are resolved, and none remain.

- **FR-017 (Gitea identity)**: settled by "Each role gets its own Gitea bot account." (project intake Q15). Jev also gets its own bot account, which may only comment and label. The control plane writes through its own account (spec 001 FR-031).
- **FR-013 (idempotency retention)**: idempotency records are kept as long as events. "Events have no time limit." (project intake Q16), so the records are never pruned. This is marked inferred in the spec.

### Why "testable and unambiguous" and "clear acceptance criteria" are ticked

The review faulted FR-006, FR-008 and FR-010.

- **FR-006**: "acting for the author" is now four enumerated cases.
- **FR-008**: the subagent identity is defined in FR-029, from spec 001's capacity registry.
- **FR-010**: every envelope field now has a defined value for every mutating tool, including `new` and `absent` for `gitea.issue.create`.

Every FR from FR-001 to FR-036 now has at least one acceptance scenario, edge case or success criterion. FR-003, FR-013, FR-017 and FR-023 gained scenarios in this pass.

### Inferred decisions

The person did not state these. Each is marked "(inferred)" in the spec, and `/speckit-intake-refine` should put them back to the person:

- The actor name `jev` (FR-005).
- Jev's comment and label writes are allowed in every autonomy mode, and lease tools stay available in Shadow mode (FR-024).
- Long-horizon and Self-improving modes are read as needing a human approval for High and Critical only (FR-025).
- A "human approval" means an approval from a person's account (FR-009).
- A head with no computed risk class is treated as Critical (FR-026).
- `gitea.pr.review` and `gitea.pr.enable_auto_merge` must name the head commit they decided on (FR-010).
- Lead's report authority "reviews" is narrowed to requesting reviews (FR-005).
- Six tools are added to the report's list (FR-001): `gitea.commit.checks`, `gitea.issue.labels.add`, `gitea.issue.labels.remove`, `gitea.pr.update`, `gitea.branch.create` and `coordination.lease.revoke`.
- The gateway runs its own check of the subagent cap, as a backstop (FR-030).
- At startup the gateway checks that no bot account has administrator rights (FR-028).
- Retry exhaustion is recorded as evidence Jev can read (FR-018).
- The gateway owns the audit records (Key Entities).
- The gateway runs on the MacBook, and its policy core is OCaml (Assumptions).

### Proposed defaults, not confirmed by the owner

These numbers are proposed defaults; the owner has not confirmed them (Assumptions, project intake row S9):

- SC-002: the 500-call suite.
- SC-003: at least 20 dropped writes.
- SC-004: the 30-day window.
- SC-006: 5 seconds.
- SC-007: 95% within 2 s.
- The retry defaults.

The load these targets must hold at is the person's own capacity figure (project intake Q20).

### Deliberate exceptions to "no implementation details"

- **Tool names (FR-001, FR-005)**: these are the report's semantic tool surface, kept verbatim because other specs cite them as the contract.
- **Envelope field names (FR-010)**: Constitution Art. III mandates them.
- **The `actor_role` values, the `jev/` label scope and the agent branch pattern**: these are contract names that specs 001 and 008 share.
- **Gitea 28.x and MCP**: Gitea is fixed by the person (project intake Q1), and the constitution names the MCP gateway.
- **Gitea 28.x API facts** (labels by ID, never mixed; additive `POST` versus replacing `PUT`; unknown names silently dropped; no comment pagination; page-limited combined status; no rate limiter): these come from the Jev research report. They are stated in Assumptions, and the FRs describe only the behavior that guards against them.
- **Stack and host** (OCaml, Rust and Python split; SQLite; MacBook Pro M4 Pro): these are fixed by the person and appear only in Assumptions.

### Dependencies

The Dependencies section matches the fixed dependency map: upstream 001 and 009; downstream 003, 004, 006 and 008.

- **Spec 007 is no longer listed as downstream.** The gateway enforces the mode that 007 defines (FR-024, FR-025) and reads it through a spec 009 record that defaults to Shadow. This is recorded in Assumptions, not as a dependency edge.
- **Spec 006 is treated the same way.** 006 computes the risk class that FR-026 reads, which defaults to Critical when absent. This is also recorded in Assumptions.
- **`specs/README.md` does not match yet.** Its index and mermaid map still show the old edges: no 009, no 008, and 002 not unblocking 008. The person who owns the README must update them; this task did not edit that file.

### Forward references

- **Specs 008 and 009**: neither file existed in `specs/` when this refinement was written. The schemas this spec cites from 009 (envelope, idempotency record, audit record, identities, mode record, computed-risk record) and the Jev behaviors cited from 008 are therefore forward references. Check them once those specs land.
- **Constitution version**: `.specify/memory/constitution.md` still reads v1.0.0. The spec cites v1.1.0 for Ollama, as decided in project intake Q14. The amendment itself has not been written to the file yet.
