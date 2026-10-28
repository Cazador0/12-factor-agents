# Specification Quality Checklist: Gitea MCP Gateway

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Updated**: 2026-10-22 (refinement: review findings, project intake Q15 and Q16, Jev research report, alignment with the refined spec 001; fix pass: specify-phase decisions R3 and R4, second review findings; answers pass: specify-phase decisions R1, R2, R5, R7 and R8; third review pass: the R7 tool's approval marked inferred, FR-036 per-context output, FR-038's limits and wider marker, modes named in the new scenarios, cross-spec follow-ups re-checked)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs). Deliberate exceptions are listed in Notes.
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders. Stories and priorities are in plain language; the requirement tables use the contract vocabulary the constitution and report fix (see Notes).
- [x] All mandatory sections completed

## Requirement Completeness

- [ ] No [NEEDS CLARIFICATION] markers remain. One marker is open in FR-038: how a head commit a person pushed or made, on a branch a person pushed or at the head of an agent branch, meets the required `lease-epoch` check. See Notes.
- [x] Requirements are testable and unambiguous. FR-038 is testable as written (it posts only on agent-branch heads and fails a missing epoch); its open marker may add a success path. The third review found that US1 scenario 8 and US4 scenarios 9 and 10 named no mode, so under the default state (Shadow) they refused for the wrong reason, and that US2 scenario 14 could not hold as written. They are fixed; see Notes.
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details). They name Gitea, which the person fixed (project intake Q1), and SC-006 refers to the host only as "the single host fixed in Assumptions". SC-011 names the `lease-epoch` status and its tool, which are contract names. See Notes.
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded. The open FR-038 marker asks whether the status tool should also post success on heads people push or make; until it is answered, the tool covers agent-branch heads only and fails a head that records no epoch. FR-038 now also states what the status does not fence (commits beneath the head, heads judged before a revocation, a credential that can post a status).
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification. Deliberate exceptions are listed in Notes.

## Notes

### Markers

Both earlier `[NEEDS CLARIFICATION]` markers are resolved:

- **FR-017 (Gitea identity)**: settled by "Each role gets its own Gitea bot account." (project intake Q15). Jev also gets its own bot account, which may only comment and label. The control plane writes through its own account (spec 001 FR-031).
- **FR-013 (idempotency retention)**: idempotency records are kept as long as events. "Events have no time limit." (project intake Q16), so the records are never pruned. This is marked inferred in the spec.

One new marker is open, so the "No markers remain" item is unticked:

- **FR-038 (heads a person pushed or made)**: the person's R7 answer adds a lease-epoch commit status that branch protection requires. Gitea applies a required check to every pull request into the protected branch, and a missing status leaves it pending, so it cannot merge (Gitea v28.2.0 source, read for this pass). Two kinds of head record no lease epoch: the head of a branch a person pushed, and a commit a person adds to an agent branch, for example the merge commit of Gitea's update-branch action, which branch protection's "branch must be current" rule can make necessary and which no gateway tool replaces. The tool posts only on agent-branch heads and fails a missing epoch, and FR-024 refuses `system` writes in Shadow mode, so neither pull request could merge. The person has not said whether the control plane should post `lease-epoch` success on heads people push or make, in every mode, or how else those pull requests meet the check. This is the person's call, because it decides what the fence covers (Art. VI). The third review widened the marker from branches people push to this second case, so it stays one marker, and the marker now says that its first option adds a success path outside the missing-epoch failure rule, which SC-011 and the "Commit with no recorded epoch" edge case would then exclude. SC-011 no longer decides the question in advance: its merge criterion now covers agent-branch heads only.

### Why "testable and unambiguous" and "clear acceptance criteria" are ticked

The first review faulted FR-006, FR-008 and FR-010.

- **FR-006**: "acting for the author" is now four enumerated cases.
- **FR-008**: the subagent identity is defined in FR-029, from spec 001's capacity registry.
- **FR-010**: every envelope field now has a defined value for every mutating tool, including `new` and `absent` for `gitea.issue.create`.

The second review found scenarios and criteria that could not be tested as written. They are fixed:

- **US4 scenarios 1 and 7, US2 scenario 12**: each Given clause now names a mode, and for merges a risk class, under which the expected outcome holds. Before, the default state (no mode recorded, so Shadow) refused them.
- **SC-009, US3 scenario 3, FR-034**: Gitea's exclusive-scope rule removes the other labels of the added label's exclusive scope. That is now the expected outcome, checked against the returned set; the 0-removal target covers every label outside that scope. After R8 the scope is the part of the name before the last `/`, so `jev/stuck` (scope `jev`) and `jev/pse/stuck` (scope `jev/pse`) never replace each other, and US3 scenario 3 now checks both.
- **FR-012**: a mutation whose `expected_version` is `absent` (only `gitea.issue.create`) skips the version comparison, so US2 scenario 9 no longer conflicts with it.
- **FR-034**: a label name defined in both the repository and the organization is refused as ambiguous (US3 scenario 6).
- **FR-031**: for a pull request of an issue Lead implements, a person requests review and schedules the merge in Gitea directly (US2 scenario 12).

The third review found these, and they are fixed:

- **US1 scenario 8, US4 scenarios 9 and 10**: FR-038 applies the mode check to the status tool, and with no mode recorded the mode is Shadow, so a `system` post and Lead's auto-merge would both be refused for the mode. Each Given clause now names Guarded autonomous mode, and the refusals in US1 scenario 8 and US4 scenario 10 name the context, head or epoch check, not the mode. US4 scenario 9 now has the push land after the revocation; a commit pushed before it recorded the then-current epoch and would have been judged success.
- **US2 scenario 14**: after R1 the second call comes from a later session under a new lease, so an identical call would be refused as stale or as not holding the lease, or replayed by its idempotency key. It is now an equivalent call, each with its own session's current epoch, a fresh `expected_version` and its own idempotency key.
- **US1 Independent Test**: it no longer says the status tool "does not exist" for `system`. A non-`system` actor finds no status tool; a `system` call that carries a context field is refused (FR-038).
- **SC-011**: it now lists the refusals of a state other than success or failure and of an agent branch of another issue, and its merge criterion covers agent-branch heads only.
- **Edge case "Commit with no recorded epoch"**: it now covers agent-branch heads only, matching FR-038, the Lease-Epoch Status entity and the next edge case.
- **FR-036**: the check tools now also return each context's latest status (context, state, status id, description, commit), and the combined state counts `lease-epoch` as Gitea does, so spec 008 FR-020 can leave `lease-epoch` out of its CI state. US3 scenario 5 tests it.

Every FR from FR-001 to FR-038 now has at least one acceptance scenario, edge case or success criterion. FR-003, FR-013, FR-017 and FR-023 gained scenarios in the first pass. FR-037 is covered by US2 scenarios 16 to 18 and SC-008, the R4 tools by US1 scenario 7, and PSE's issue update by US2 scenario 19. FR-038 is covered by US1 scenario 8, US4 scenarios 9 and 10, SC-011 and four edge cases (late push, no recorded epoch, people's pull requests, status posted outside the gateway). The R8 label scopes are covered by US1 scenario 4 and US3 scenario 3.

### Decisions applied

Answers pass (R1 to R8; R3 and R4 were applied in the fix pass and re-checked here):

- **Project intake R7** ("Both"): the coordination-layer fence stays as it was (FR-007, US2 scenario 13). The new FR-038 adds `gitea.commit.set_lease_epoch_status`, which only `system` calls and which writes only the `lease-epoch` context, on agent-branch heads. FR-001 (tool list and the table of tools needing FR-003 approval, now nine added tools), FR-002 (no other commit status), the FR-005 matrix, FR-010 (envelope values), FR-027 (Jev posts no status), FR-036 (per-context check output), Key Entities (Lease, Lease-Epoch Status, Bot Account), Assumptions (Gitea facts, human-owned setup, Branches), Dependencies (001 and 008) and the Constitution list follow it. US1 scenario 8, US4 scenarios 9 and 10, SC-011 and four edge cases test it. The spec no longer treats the forge-side fence as an open question; the one open item is the marker above.
  - The third review found that FR-001 said a person approved the R7 tool as a Critical-risk change, without an "(inferred)" mark, although R7's question asked where the fence lives and named no tool, and spec 001 FR-038 lists the same reading under "The design below is inferred". FR-001 now counts two tools approved by a person (R4), reads R7's "Both" as the FR-003 approval for the third "(inferred)", and its table has an Approval column that says so. This is an Art. VI authority point, so it stays with the inferred decisions below for the person to confirm.
  - FR-038 now keeps R7's sentence as the person's goal and states what the mechanism guarantees: an agent-branch head that records a missing or older epoch when judged cannot merge. It names the limits (commits beneath the head, heads judged success before a revocation, a credential that can post a status) and leaves the first two to spec 001's recovery assessment (spec 001 FR-017, FR-037). FR-038, the table's Serves cell and the Dependencies (001) bullet now cite spec 001 FR-038, which gives the control plane the duty to judge and post.
  - The US1 tool-list bullet and the Lease-Epoch Status entity cite R7 only for the required status itself, and mark the poster, the agent-branch scope and the failure rule as inferred (FR-038).
- **Project intake R8** ("All three", confirmed as "Role labels + summary (Recommended)"): the human-owned setup lists the 12 labels; FR-027 defines Jev's `jev/` scope as every label whose name begins with `jev/`; FR-034 states how Gitea derives an exclusive scope; US1 scenario 4 and US3 scenario 3, the matrix's label row, the Label Map entity and Dependencies (008) follow it.
- **Project intake R1** ("One per role (Recommended)"): US2 scenario 14 no longer implies two PSE sessions at once; it now uses one PSE session after another, each making an equivalent call under its own lease epoch, version and idempotency key. The Success-criteria assumption records the split and that the 6 subagents are at most 2 per role. Nothing else in this spec assumed concurrent sessions of one role.
- **Project intake R2** ("Owner, per issue (Recommended)"): FR-031 already deferred to spec 003 FR-010, which records R2. FR-031 now names the owner's per-issue grant for traceability. Gateway behavior is unchanged.
- **Project intake R5** ("+30% in 3 months (Recommended)"): the Success-criteria assumption no longer says the headline target is unconfirmed. It records that R5 sets the project's headline target (spec 007 SC-004), and that this spec's own numbers are still proposed defaults.
- **Project intake R6** does not apply: this spec has no durable-progress window or other Jev threshold.
- **R3 and R4** are still reflected correctly: FR-024 and FR-037 (R3), FR-001 and the matrix's read row (R4). Their Clarifications lines now use the form "(project intake, R<n>)", like the new ones.

Every applied answer (R1, R2, R3, R4, R5, R7, R8) has a Clarifications line, with the question and answer copied from the Phase Refinements table. The Input line now names all seven: four that change the gateway's behavior (R3, R4, R7, R8) and three recorded for traceability (R1, R2, R5).

Fix pass:

- **Project intake R3** ("Both Create issues by hand and Approve; gateway writes it"): FR-024 now excepts a human-approved plan write, defined in the new FR-037 (actor, approval check, scope, audit fields). FR-010, FR-022, the FR-025 Shadow row, SC-008, the No-mode edge case, Key Entities and Dependencies (004) follow it, and US2 scenarios 16 to 18 test it.
- **Project intake R4** ("Approve read-only search (Recommended)"): FR-001 adds `gitea.issue.search` and `gitea.milestone.get` as reads approved by a person under FR-003. The matrix's read row, US1, the Gitea-operations assumption and Dependencies (004) follow it, and US1 scenario 7 tests it.

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
- The plan-approval record belongs with spec 009's shared types (Key Entities). Spec 009 FR-002 now lists it and owns its schema, and marks that placement inferred too.
- The check tools return each context's latest status (context, state, status id, description, commit), so a consumer such as spec 008 FR-020 can leave `lease-epoch` out of its own reading (FR-036; marked "(inferred, project intake R7)"). The combined state itself still counts `lease-epoch`, as Gitea does.
- The gateway runs its own check of the subagent cap, as a backstop (FR-030).
- At startup the gateway checks that no bot account has administrator rights (FR-028).
- Retry exhaustion is recorded as evidence Jev can read (FR-018). Spec 008 does not consume it yet.
- The gateway owns the audit records (Key Entities).
- The gateway runs on the MacBook, and its policy core is OCaml (Assumptions).
- **The lease-epoch status** (FR-038). The two fences are the person's answer (project intake R7); these details are not:
  - reading the person's "Both" as the human approval FR-003 requires for a new tool. R7's question asked where the fence lives and did not name a gateway tool, so the person may want to confirm this reading. Until the third review, FR-001 stated this reading as fact and counted the tool as "approved by a person"; it is now marked "(inferred)" in FR-001's text and its table's Approval column, as spec 001 FR-038 marks it;
  - the tool's name `gitea.commit.set_lease_epoch_status` and its placement in the System row only;
  - the control plane judges each new head and posts the status. R7's own record says which component posts it is inferred;
  - a commit records its lease epoch, for example in a commit trailer the session writes;
  - failure when the epoch is missing or older (fail closed), success otherwise, and no other state;
  - the tool posts only on the current head of an agent branch for the envelope's issue, and its input has no context field;
  - the gateway asks the lease service to confirm the epoch before it posts success, as a second check;
  - the gateway's mode check applies to the tool, so nothing is posted in Shadow mode;
  - the control plane's bot account gets write access to the code, which Gitea requires to post a status;
  - the push credential agents use must not be able to post a commit status, because Gitea counts the latest status of a context;
  - what the status does not fence: a stale commit beneath a head that records the current epoch, and a head judged success before its lease was revoked. This spec leaves both to spec 001's recovery assessment (spec 001 FR-017, FR-037); spec 001 FR-038 states the first.
- Jev's write scope `jev/` is read as the label-name prefix, which covers all 12 labels, not as Gitea's exclusive scope of each label (FR-027). The permission itself comes from the Jev report: "Jev's write set should stay at its own comments and its `jev/*` labels." (§Jev proposes the stop; the policy owner carries it out). R8 names the 12 labels but does not word the permission. The earlier note, and FR-027, put the phrase "labels in the jev/ scope" in quotation marks and attributed it to R8, which does not contain it; both are corrected.
- US1 scenario 4 cites R8 for Jev's `jev/pse/stuck` call and now marks the prefix reading of the scope as inferred (FR-027).

### Proposed defaults, not confirmed by the owner

These numbers are proposed defaults; the owner has not confirmed them (Assumptions). Project intake R5 set the project's headline target (spec 007 SC-004), which closed the S9 open item, but no answer sets these gateway targets:

- SC-002: the 500-call suite.
- SC-003: at least 20 dropped writes.
- SC-004: the 30-day window.
- SC-006: 5 seconds.
- SC-007: 95% within 2 s.
- The retry defaults.

The load these targets must hold at is the person's own capacity figure (project intake Q20).

### Deliberate exceptions to "no implementation details"

- **Tool names (FR-001, FR-005)**: these are the report's semantic tool surface, kept verbatim because other specs cite them as the contract. The two R4 tools and the R7 tool carry inferred names in the same style.
- **Envelope field names (FR-010)**: Constitution Art. III mandates them.
- **The `actor_role` values, the `jev/` label scope and its 12 label names, the agent branch pattern and the `lease-epoch` status context**: these are contract names that specs 001 and 008 share, and that the person's answers fix (project intake R7, R8).
- **Gitea 28.x and MCP**: Gitea is fixed by the person (project intake Q1), and the constitution names the MCP gateway.
- **Gitea 28.x API facts** (labels by ID, never mixed; additive `POST` versus replacing `PUT`; unknown names silently dropped; same-named repository and organization labels both added; exclusive scopes; no comment pagination; page-limited combined status; required status contexts; no rate limiter): these come from the Jev research report. Four facts were read from the Gitea v28.2.0 source for this pass and are marked so in Assumptions: how an exclusive scope is derived from a label's name, that a missing required status leaves a pull request pending, that posting a status needs write access to the code, and that only the latest status of a context counts. They are stated in Assumptions, and the FRs describe only the behavior that guards against them.
- **The commit trailer** (FR-038, Assumptions: Branches) is an example of how a commit can record its lease epoch, marked inferred; planning chooses the form.
- **Stack, host and models**: all fixed by the person. The stack (OCaml, Rust and Python split; SQLite) appears only in Assumptions. The host and models also appear outside Assumptions, deliberately:
  - the Overload edge case names "the shared MacBook host" (project intake Q22), because the pacing exists to protect it;
  - FR-033 and US2 scenario 14 name Claude and Ollama (project intake Q7), because the requirement is that decisions do not depend on the model;
  - SC-006 names the peak load (project intake Q20) and refers to the host only as "the single host fixed in Assumptions", and SC-007 reuses that load.

  The earlier note said the host and stack "appear only in Assumptions". That was not true and is corrected here.

### Dependencies

The Dependencies section matches the fixed dependency map: upstream 001 and 009; downstream 003, 004, 006 and 008. R7 adds no edge: the control plane (001, upstream) posts the `lease-epoch` status through this spec's tool at runtime, as the map's note says ("001 defines what, 002 defines how"), and Jev (008, already downstream) relies on the status as its forge-side fence.

- **Spec 007 is not listed as downstream.** The gateway enforces the mode that 007 defines (FR-024, FR-025) and reads it through a spec 009 record that defaults to Shadow. This is recorded in Assumptions, not as a dependency edge.
- **Spec 006 is treated the same way.** 006 computes the risk class that FR-026 reads, which defaults to Critical when absent. This is also recorded in Assumptions.
- **`specs/README.md` matches** (checked 2026-10-22): 009 is listed, and 002's row reads depends on 001 and 009, unblocks 003, 004, 006 and 008.

### Cross-spec follow-ups (outside this file)

This pass edited only this spec and this checklist. The answers pass listed follow-ups that specs 001, 008 and 009 have since taken up; the third review pass re-checked them against the current specs on 2026-10-22.

- **Resolved since the fix pass**:
  - Spec 004 FR-023 and FR-024 no longer carry the R3 and R4 markers, and spec 007 FR-002 records the human-approved plan write (R3).
  - Spec 009 FR-002 lists the plan-approval record and says the mutation envelope references it (FR-037).
  - Spec 001 FR-032 and its Assumptions describe both fences as the person's choice; spec 008 FR-029 step 5 and its US2 text carry no R7 marker and cite spec 001 FR-038 and this spec's FR-038. Spec 008 has no markers left.
  - Spec 001 FR-038 gives the control plane (System) the duty of judging agent-branch heads and posting `lease-epoch`. This spec now cites it (FR-001 table, FR-038, Dependencies).
  - Spec 001 FR-035 applies R1 and carries no marker.
  - Spec 008 FR-036 lists all 12 labels, and its FR-002 and human-owned setup refer to them.
  - Spec 008 FR-020 leaves `lease-epoch` out of a head's CI state and status count. This spec's FR-036 now returns each context's latest status, which that rule needs; before this pass FR-036 promised only a combined state.
- **Still open**:
  - The question of heads a person pushes or makes is open in three specs: spec 001 FR-038, this spec's FR-038 and spec 006 (its `lease-epoch` marker says one answer settles all three). This spec's marker now also covers a person's commit at the head of an agent branch, such as Gitea's update-branch merge commit; the markers in specs 001 and 006 ask only about branches people push, and spec 001's edge case "A head that records no epoch" fails a person's commit on an agent branch (inferred). Once the person answers, the three specs should be aligned.
  - Spec 003 FR-020 has a related marker: Review's test-only commits record no lease epoch, so a head made of them fails `lease-epoch`. Its options may add a test-only write lease and branch, which would change this spec's FR-005.
  - Spec 004 has a marker on how Lead's specification commits reach a branch and a pull request. Its option (a) would widen Lead's row in this spec's FR-005, a Critical-risk change (FR-003) that needs a person.
  - Spec 001 FR-038 judges each new head only and does not say whether a head judged success before its lease was revoked is judged again. This spec leaves that case to spec 001's recovery assessment (FR-038).

### Cross-references checked

- **Spec 009** now exists. Checked against its FR-002 shared types:
  - FR-010: the mutation envelope with the lease epoch is listed;
  - FR-022: audit records are listed;
  - FR-024: the active-mode record is listed;
  - FR-026: the computed-risk-class record is listed;
  - FR-029: actor, bot-account and subagent identities are listed;
  - FR-032: idempotency records are listed;
  - FR-037: the plan-approval record is listed, and the mutation envelope references it (re-checked in the third review pass).
- **Spec 008** now exists too. Its citations of FR-027, FR-034, FR-035, FR-036 and FR-038 match this spec; its FR-020 picks each check's latest status by status id, which FR-036 now returns. It does not name the `jev` actor value or consume FR-018's retry-exhaustion evidence, so both stay inferred here.
- **Spec 001** FR-038 and FR-031 match this spec's FR-038 and the System row of FR-005. Spec 001 marks the R7 tool's approval as inferred, as this spec now does.
- **Spec 003** FR-039 has each commit made under a write lease record its epoch, which FR-038 now cites.
- **Spec 003** FR-010 records R2, which FR-031 now cites.
- **Constitution**: `.specify/memory/constitution.md` reads v1.1.0, which allows Ollama cloud and local alongside Claude (project intake Q14). Its Sync Impact Report flagged this file's earlier "still reads v1.0.0" note as stale; the note is removed.
