# Specification Quality Checklist: Gitea MCP Gateway

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Updated**: 2026-10-22 (refinement: review findings, project intake Q15 and Q16, Jev research report, alignment with the refined spec 001; fix pass: specify-phase decisions R3 and R4, second review findings)
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
- [x] Success criteria are technology-agnostic (no implementation details). They name Gitea, which the person fixed (project intake Q1), and SC-006 refers to the host only as "the single host fixed in Assumptions". See Notes.
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

The first review faulted FR-006, FR-008 and FR-010.

- **FR-006**: "acting for the author" is now four enumerated cases.
- **FR-008**: the subagent identity is defined in FR-029, from spec 001's capacity registry.
- **FR-010**: every envelope field now has a defined value for every mutating tool, including `new` and `absent` for `gitea.issue.create`.

The second review found scenarios and criteria that could not be tested as written. They are fixed:

- **US4 scenarios 1 and 7, US2 scenario 12**: each Given clause now names a mode, and for merges a risk class, under which the expected outcome holds. Before, the default state (no mode recorded, so Shadow) refused them.
- **SC-009, US3 scenario 3, FR-034**: Gitea's exclusive-scope rule removes the other `jev/` label when one is added. That is now the expected outcome, checked against the returned set; the 0-removal target covers every label outside the added label's exclusive scope.
- **FR-012**: a mutation whose `expected_version` is `absent` (only `gitea.issue.create`) skips the version comparison, so US2 scenario 9 no longer conflicts with it.
- **FR-034**: a label name defined in both the repository and the organization is refused as ambiguous (US3 scenario 6).
- **FR-031**: for a pull request of an issue Lead implements, a person requests review and schedules the merge in Gitea directly (US2 scenario 12).

Every FR from FR-001 to FR-037 now has at least one acceptance scenario, edge case or success criterion. FR-003, FR-013, FR-017 and FR-023 gained scenarios in the first pass. FR-037 is covered by US2 scenarios 16 to 18 and SC-008, the R4 tools by US1 scenario 7, and PSE's issue update by US2 scenario 19.

### Decisions applied in this pass

- **Project intake R3** ("Both Create issues by hand and Approve; gateway writes it"): FR-024 now excepts a human-approved plan write, defined in the new FR-037 (actor, approval check, scope, audit fields). FR-010, FR-022, the FR-025 Shadow row, SC-008, the No-mode edge case, Key Entities and Dependencies (004) follow it, and US2 scenarios 16 to 18 test it.
- **Project intake R4** ("Approve read-only search (Recommended)"): FR-001 adds `gitea.issue.search` and `gitea.milestone.get` as reads approved by a person under FR-003. The matrix's read row, US1, the Gitea-operations assumption and Dependencies (004) follow it, and US1 scenario 7 tests it.

Both answers have a Clarifications line.

### Inferred decisions

The person did not state these. Each is marked "(inferred)" in the spec, and `/speckit-intake-refine` should put them back to the person:

- The actor name `jev` (FR-005). Spec 008 does not name the `actor_role` value either.
- Jev's comment and label writes are allowed in every autonomy mode (FR-024).
- The gateway's own mode check does not refuse lease tools. The lease service still applies spec 001 FR-030's mode gate to write-lease grants, so a write-lease claim in Shadow mode is refused there (FR-024). The earlier wording, "lease tools stay available in every mode", contradicted spec 001 FR-030 and is corrected.
- Long-horizon and Self-improving modes are read as needing a human approval for High and Critical only (FR-025).
- A "human approval" means an approval from a person's account (FR-009).
- A head with no computed risk class is treated as Critical (FR-026).
- A lowering risk label counts as an unauthorized-action attempt only when the audit trail shows an agent actor set it. Lowering text, and labels people set, are ignored but not counted (FR-026). Spec 006 FR-015 says only that the computed class wins.
- `gitea.pr.review` and `gitea.pr.enable_auto_merge` must name the head commit they decided on (FR-010).
- Lead's report authority "reviews" is narrowed to requesting reviews (FR-005).
- **PSE's issue authority** (FR-005). The matrix had narrowed it to nothing without saying so; the report ("Assigned issues", `issues: assigned_scope`) and spec 007 FR-003 ("update its assigned issues") grant it. PSE now has `gitea.issue.update` on the issue it holds the write lease for. Two limits remain this spec's reading: PSE may not open or close the issue, and it gets no label tool, because labels carry the risk class and the Blocked state that others own.
- For a pull request of an issue Lead implements, a person requests the review and schedules the merge in Gitea directly (FR-031). No other actor holds those tools.
- Six tools are added to the report's list (FR-001): `gitea.commit.checks`, `gitea.issue.labels.add`, `gitea.issue.labels.remove`, `gitea.pr.update`, `gitea.branch.create` and `coordination.lease.revoke`.
- The names `gitea.issue.search` and `gitea.milestone.get`, and that the milestone lookup also lists the milestone's issues, to cover spec 004 FR-024's second capability (FR-001). The tools themselves are the person's decision (project intake R4).
- **Human-approved plan writes** (FR-037). The two paths are the person's choice (project intake R3); these details are not:
  - the write runs as `lead` through Lead's bot account;
  - how the person records the approval is left to planning;
  - the approval never covers auto-merge, reviews, review requests, branch creation or lease grants;
  - the audit record marks the write as human-approved, so spec 007's scorecard counts it as a human action;
  - the same rule applies in Agent implementation and Guarded autonomous modes, where spec 004 FR-023 also has a person apply the plan. R3's question named Shadow mode only.
- A label name defined in both the repository and the organization is refused as ambiguous rather than resolved to one of them (FR-034).
- Gitea 28.x supports issue search and milestone lookup by name (Assumptions).
- The plan-approval record belongs with spec 009's shared types (Key Entities).
- The gateway runs its own check of the subagent cap, as a backstop (FR-030).
- At startup the gateway checks that no bot account has administrator rights (FR-028).
- Retry exhaustion is recorded as evidence Jev can read (FR-018). Spec 008 does not consume it yet.
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

- **Tool names (FR-001, FR-005)**: these are the report's semantic tool surface, kept verbatim because other specs cite them as the contract. The two R4 tools carry inferred names in the same style.
- **Envelope field names (FR-010)**: Constitution Art. III mandates them.
- **The `actor_role` values, the `jev/` label scope and the agent branch pattern**: these are contract names that specs 001 and 008 share.
- **Gitea 28.x and MCP**: Gitea is fixed by the person (project intake Q1), and the constitution names the MCP gateway.
- **Gitea 28.x API facts** (labels by ID, never mixed; additive `POST` versus replacing `PUT`; unknown names silently dropped; same-named repository and organization labels both added; exclusive scopes; no comment pagination; page-limited combined status; no rate limiter): these come from the Jev research report. They are stated in Assumptions, and the FRs describe only the behavior that guards against them.
- **Stack, host and models**: all fixed by the person. The stack (OCaml, Rust and Python split; SQLite) appears only in Assumptions. The host and models also appear outside Assumptions, deliberately:
  - the Overload edge case names "the shared MacBook host" (project intake Q22), because the pacing exists to protect it;
  - FR-033 and US2 scenario 14 name Claude and Ollama (project intake Q7), because the requirement is that decisions do not depend on the model;
  - SC-006 names the peak load (project intake Q20) and refers to the host only as "the single host fixed in Assumptions", and SC-007 reuses that load.

  The earlier note said the host and stack "appear only in Assumptions". That was not true and is corrected here.

### Dependencies

The Dependencies section matches the fixed dependency map: upstream 001 and 009; downstream 003, 004, 006 and 008.

- **Spec 007 is not listed as downstream.** The gateway enforces the mode that 007 defines (FR-024, FR-025) and reads it through a spec 009 record that defaults to Shadow. This is recorded in Assumptions, not as a dependency edge.
- **Spec 006 is treated the same way.** 006 computes the risk class that FR-026 reads, which defaults to Critical when absent. This is also recorded in Assumptions.
- **`specs/README.md` matches** (checked 2026-10-22): 009 is listed, and 002's row reads depends on 001 and 009, unblocks 003, 004, 006 and 008.

### Cross-spec follow-ups (outside this file)

R3 and R4 also touch other specs, which this pass did not edit:

- Spec 004 FR-023 and FR-024 still carry the `[NEEDS CLARIFICATION]` markers that R3 and R4 answered.
- Spec 007 FR-002 still says a human performs every consequential mutation in Shadow mode. Project intake R3 records that it changes too.
- Spec 009 FR-002 does not list the plan-approval record (FR-037), nor the approval-reference field of the mutation envelope.

### Cross-references checked

- **Spec 009** now exists. Checked against its FR-002 shared types:
  - FR-010: the mutation envelope with the lease epoch is listed;
  - FR-022: audit records are listed;
  - FR-024: the active-mode record is listed;
  - FR-026: the computed-risk-class record is listed;
  - FR-029: actor, bot-account and subagent identities are listed;
  - FR-032: idempotency records are listed;
  - FR-037: the plan-approval record is not listed yet (see the follow-ups above).
- **Spec 008** now exists too. Its citations of FR-027, FR-034, FR-035 and FR-036 match this spec. It does not name the `jev` actor value or consume FR-018's retry-exhaustion evidence, so both stay inferred here.
- **Constitution**: `.specify/memory/constitution.md` reads v1.1.0, which allows Ollama cloud and local alongside Claude (project intake Q14). Its Sync Impact Report flagged this file's earlier "still reads v1.0.0" note as stale; the note is removed.
