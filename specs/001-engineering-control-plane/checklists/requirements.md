# Specification Quality Checklist: Engineering Control Plane

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
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
- [ ] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

- **Resolved markers**:
  - FR-007 reads "Events have no time limit." (project intake Q16), checked by SC-014.
  - FR-021 holds the person's peak capacity, "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20), enforced with the subagent cap in FR-034 (project intake Q18) and checked by SC-010.
  - FR-035 reads "One per role (Recommended)" — one session each for Lead, PSE and Review; at most one issue in build at a time (project intake R1). Everything that assumed two PSE sessions at once was changed: FR-003's example, US3 AS-1 (two claims instead of two PSE sessions), US3 AS-6 and AS-7, User Story 4 (narrative, Why, Independent Test, AS-2 and AS-3), the Edge Cases "Concurrent claims" and "Capacity full", FR-018 step 4, FR-037 step 3, TR-04, the WAIT reasons, FR-021, FR-023, SC-006, SC-010 and the Capacity Registry entity. This round also fixed three places that still leaned the old way. The US3 Independent Test now runs its sessions one after another. FR-035 now says when a PSE session ends (after its move to Review, which is not a stop), and US4 AS-2 and AS-3 now say in their Given that the session that built 184 has ended. "Write-set serialization then only orders queued work" follows from R1, but the person did not say it. Last round FR-035 presented it as the person's words; it now reads as an inference.
- **FR-038** (project intake R7, "Both"): the forge-side fence. Alongside the coordination-layer fence of FR-032, a `lease-epoch` commit status that branch protection requires keeps a commit from a stale epoch from merging. The wording that called the forge-side fence an open item of spec 008 is gone from US3, FR-032, the Edge Case "Hard stop with a write in flight", SC-012 and Assumptions. FR-038 is checked by US3 AS-9, SC-016 and the Edge Cases. This round:
  - Only the two fences are attributed to R7. The US3 narrative, the Edge Case "Hard stop with a write in flight", FR-030's Shadow bullet and the Dependencies entry for 002 now mark as "(inferred)" the control plane as poster, commits recording their epoch, the gateway's mode check refusing the post in Shadow mode, and the System-row-only tool.
  - FR-030 now lists posting the `lease-epoch` status among the consequential actions, so its gate covers the post by its own definition.
  - FR-038 no longer says that R7 is the human approval a new tool needs (spec 002 FR-003), and Assumptions no longer say the System's account "is given" code-write access. Both are now marked as inferred readings, and the access is a person's setup step (Art. VI).
  - FR-038 now says the fence holds only while no credential a session or subagent can reach can post a commit status (spec 002 Assumptions: Branches; spec 003 FR-039). The new Edge Case "A `lease-epoch` status from another account" covers this.
  - FR-038 bullet 1 now cites spec 003 FR-039. The Dependencies' implementation order notes that FR-038's success path needs spec 003 FR-039, so a person should not make `lease-epoch` required before it ships (inferred).
- **New requirement FR-039** (project intake R2, "Owner, per issue (Recommended)"): the control plane records an implementation-worker grant only on the owner's approval for that issue, and grants Lead a write lease only on an issue with such a grant, never on Lead's request alone (Art. VI). Last round filed this gap under "Outside this task's files". That was wrong, because the gap was in this spec's own lease service. FR-035 and US3 AS-7 counted on Lead holding a write lease. But TR-04 granted only "the PSE write lease", and TR-05 and TR-08 let only the PSE move an issue to Review. So US3 AS-7's Given could not be reached by any procedure here. Now:
  - TR-04, TR-05 and TR-08 name Lead under a grant (inferred).
  - FR-015 says a write lease goes to Lead only under FR-039.
  - The refusal list gains "no implementation-worker grant".
  - The Key Entities gain the Implementation-Worker Grant, and the Clarifications gain the R2 line.
  - FR-039 is checked by US3 AS-10 and SC-017. US3 AS-7, the US3 Independent Test and SC-012 cite it.
- **Two markers are open, both in FR-038**:
  - *People's pull requests*: how a pull request from a branch a person pushed meets a required `lease-epoch` check. The control plane judges only agent-branch heads, and in Shadow mode every System write is refused (spec 002 FR-024). So once a person makes the check required, such a pull request could never merge. Spec 002 FR-038 holds the same question, and one answer settles both specs. The person never said how, so it is marked rather than inferred.
  - *A stale commit beneath a current-epoch head* (new this round): last round this appeared only as a "known limit" in this checklist, while FR-038 said such commits "are covered" by the recovery assessment and the FR-037 branch-head check. They are not covered. Both checks read the branch before a re-dispatch, so a stale commit that lands after it, with the new session's commit on top, sits beneath a passing head and can merge. The "covered" sentence is gone. The gap is now the Edge Case "A stale commit beneath a current-epoch head" and a marker in FR-038. The marker offers three answers: judge every commit the branch adds after the lease's base commit, bar a session from building on a commit it did not make (spec 003), or another way the person names. FR-032, the US3 narrative, the Edge Case "Hard stop with a write in flight" and Assumptions now say the two checks find what a late push landed *before* a re-dispatch.
- **Unticked: "No [NEEDS CLARIFICATION] markers remain"**. Two FR-038 markers are open. Tick it once the person answers both.
- **Unticked: "Requirements are testable and unambiguous"**. Last round said it stayed unticked only because of the FR-038 marker. That was wrong: the R2 gap above was a second reason, since no procedure in this spec reached US3 AS-7's Given, and Lead under a grant could not move its issue to Review. FR-039 closes that gap this round, though its Lead-dispatch path is inferred. The item now stays unticked because of the two FR-038 markers. Until they are answered, nobody can say what a required `lease-epoch` check does to a person's own pull request, or whether a stale commit beneath a current-epoch head can merge. FR-035 is answered and testable (US3 AS-6, US4 AS-2 and AS-3, SC-006, SC-010). Earlier rounds fixed these: the transition table (TR-01 to TR-15) with its refusal and WAIT reasons; epochs compared per issue or per part (FR-015, FR-032); the fence's scope (FR-032, SC-012); `session_id` (FR-003); exits from Ready to Merge (TR-14, TR-15); and Blocked versus Done (FR-008).
- **Unticked: "All functional requirements have clear acceptance criteria"**. Last round ticked it although its own notes said the open part of FR-038 had no criterion. The R2 gap also left Lead's write-lease path with no requirement and no criterion. FR-039 now has US3 AS-10 and SC-017. The two open parts of FR-038 still have none. Tick it again once both FR-038 markers are answered and given criteria. Covered now:
  - FR-035: US3 AS-6, US4 AS-2 and AS-3, SC-006 and SC-010.
  - FR-038 (head judging): US3 AS-9, SC-016, and the Edge Cases "Hard stop with a write in flight" and "A head that records no epoch".
  - FR-039: US3 AS-7 and AS-10, SC-012 and SC-017.
  - Earlier requirements: FR-029 (US2 AS-6, SC-013); FR-030 (US2 AS-5, SC-009); FR-031 (US2 AS-7); FR-033 (SC-015); FR-016 (US3 AS-4, SC-011); FR-032 and per-part epochs (US3 AS-5, AS-7, SC-012); FR-021 and FR-034 (US3 AS-6, SC-010); FR-037 (US3 AS-8); FR-003 (US1 AS-5); FR-004's comment, label and board-move types (US1 AS-4 and two Edge Cases); FR-036 (Edge Case "A person moves a card"); TR-14 and TR-15 (Edge Case "A check fails or a review requests changes after Ready to Merge").
- **Unticked: "Feature meets measurable outcomes defined in Success Criteria"**. FR-038's aim is that a commit from a stale epoch can never merge. SC-016 measures that for heads only. The spec now says a stale commit beneath a current-epoch head can merge, and no criterion covers that path. Tick it once the second FR-038 marker is answered and a criterion covers that path.
- **Unticked: "No implementation details (languages, frameworks, APIs)" and "No implementation details leak into specification"**. Last round kept them ticked by calling the `lease-epoch` items "constraints, not design choices". Only the status context itself rests on R7. FR-038 also names inferred design details: the gateway tool `gitea.commit.set_lease_epoch_status` and its System-row placement, the event types that report a new head, and a commit trailer as an example of how a commit records its epoch. They are kept as cross-references to spec 002 FR-038 and spec 003 FR-039 so that the three specs stay aligned, and planning may change them. These two items do not block planning.
- **Unticked: "Written for non-technical stakeholders"**. The readers are the engineering owner and the role agents, and the requirements use engineering terms that the constitution or the design fixed: HMAC-SHA256, idempotency key, mutation envelope, lease epoch, commit status. The User Stories stay in plain language. This item does not block planning.
- **Provenance**: HMAC-SHA256 comes from the report (§Event-driven communication) and the constitution (Additional Constraints: Events), not from the person. These are named because the person fixed them: Gitea 28.x (Q1), the LangGraph service (Q2), SQLite (Q9), the OCaml/Rust/Python split (Q10, in Assumptions), Claude and Ollama (Q7, in Assumptions) and the MacBook Pro M4 Pro host (Q22; data-model intake Q14). The `lease-epoch` status context rests on R7. The tool name, the trailer and the System-row placement are inferred (see above).
- **Other answers checked against this spec**:
  - R2: now has its own requirement, FR-039, and a Clarifications line. FR-035 and FR-015, TR-04, TR-05 and TR-08, US3 AS-7 and AS-10, and SC-012 and SC-017 cite it.
  - R5 (spec 007 SC-004): the Assumption that said the owner had not confirmed a headline target now cites R5. This spec's own numbers are not covered by R5 and stay proposed defaults.
  - R8: the Edge Case "Jev's labels and comments" names the per-role and summary `jev/` labels, and the Jev Assumption says they all fall in the `jev/` scope that spec 008 FR-002 already grants. Jev gains no right from FR-038.
  - R6 (spec 008 FR-015) does not apply: this spec sets no Jev window.
  - R3 and R4 were applied last round to other specs and need no change here.
- **Inferred rules awaiting the person**: the person did not state these. They are marked "(inferred)" in the spec and should go back to the person through `/speckit-intake-refine`:
  - FR-002: manual redelivery under a new identifier counts as a duplicate.
  - FR-003: a person's account gets `actor_role` `person`. `session_id` is resolved from the lease records and the capacity registry, and left empty when not exactly one session of the role is active.
  - FR-004: the `issue.commented`, `issue.label_changed` and `issue.board_moved` types, and deriving `issue.board_moved` from a board re-read if Gitea 28.x sends no webhook for a column move.
  - FR-009: the from→to pairs TR-06, TR-07, TR-10, TR-12, TR-14 and TR-15; Lead under a grant as a requester in TR-04, TR-05 and TR-08; and the list of refusal and WAIT reasons, including "no implementation-worker grant".
  - FR-015 and FR-032: the epoch is scoped to the issue, or to the issue and part when Lead partitions it.
  - FR-017: Lead records the recovery outcome.
  - FR-021 and FR-035: a dispatch or session start beyond the capacity is held as WAIT "capacity" rather than refused. The ceiling of one session per role is the person's (R1); the holding is not.
  - FR-035: an issue is "in build" while any write lease on it is active, whichever role holds it (Lead under a grant included). A partitioned issue counts as one issue in build. A second session of a role is held "whether or not it holds a write lease". With one PSE session, a second concurrent part lease can only be Lead's (also US3 AS-7). A PSE session ends after its move to Review, and that is not a stop; Lead releases its lease the same way and stays active. "Write-set serialization then only orders queued work" follows from R1 but is not the person's words.
  - FR-023 and User Story 4: "orders queued work" means an issue waits while its write set overlaps that of an issue dispatched earlier and not yet Done, and a non-overlapping issue may take the build slot first.
  - FR-038: the whole design beyond the two fences. That covers several points:
    - commits record their epoch (for example a trailer), and the control plane posts the status on new agent-branch heads;
    - a grant that ended in recovery (expired, released at a stop, revoked) counts as older;
    - the check is fail-closed, and only the head is judged;
    - the tool's name and its System-row placement;
    - reading R7 as the human approval spec 002 FR-003 needs for that tool;
    - a person giving the System's bot account code-write access (Assumptions);
    - the fence holds only while no session credential can post a status, and keeping such credentials away is a planning item;
    - the gateway's mode check refuses the post in Shadow mode;
    - a person should not make the check required before spec 003 FR-039 ships (Dependencies).
  - FR-039: how the owner's approval reaches the control plane. On a granted issue, the claim or re-dispatch procedure gives the lease to Lead (role `lead`, branch `agent/lead/<issue>-<slug>`), and the next action keeps the name DISPATCH_PSE. The active Lead session takes the lease. A part's lease on an issue already In Progress is acquired with no board move. Lead moves the issue to Review and then releases the lease. The refusal reason in US3 AS-10 is inferred too.
  - FR-024: `expected_version` is a per-issue counter kept by the control plane.
  - FR-028: treating the capacity caps (FR-021, FR-034, FR-035) as Critical-risk rules. The caps themselves are the person's (Q18, Q20, R1).
  - FR-030: the mode gate fails closed to Shadow until spec 007 supplies the modes. Starting a read-only analysis session with no write lease is not consequential, so Shadow allows it.
  - FR-031: the System actor has its own Gitea bot account.
  - FR-034: subagents work under their parent session's lease.
  - FR-036: a person's out-of-table move is surfaced, never undone.
  - FR-037: the re-dispatch procedure, including the branch-head check and no board move.
  - Edge Case "Removed person or agent": raw deliveries are anonymized too, keep their receipt-time verification result and body hash, and are never re-verified.
  - Assumptions: the lease TTL and retry defaults, and the reading of Q10.
- **Success Criteria numbers are proposed defaults** (Assumptions). R5 set the project's headline target in spec 007 SC-004, not these. This covers the 24-hour soak (SC-010), the 4-hour heartbeat run (SC-011), the 50 late writes (SC-012) and the suite sizes of SC-016. SC-004 is a stress test above the stated capacity. SC-017 is a zero count, not a proposed number.
- **Dependencies** match the fixed dependency map. Upstream: 009. Downstream: 002, 003, 004, 005, 006, 007, 008. FR-038 and FR-039 add no edge. 002 carries the status write, as it carries every other write 001 requests, and FR-038 is implemented after 002 like the other Gitea-writing requirements. FR-038's success path also relies on spec 003 FR-039 (sessions record their epoch in commits). 003 is already downstream, so until 003 ships every agent-branch head fails closed, and a person should not make `lease-epoch` a required check before then (inferred; spec Dependencies, Implementation order).
- **Outside this task's files**:
  - The first FR-038 marker (people's pull requests) is shared with spec 002 FR-038, so one answer should settle both.
  - The second FR-038 marker (a stale commit beneath a current-epoch head) touches spec 003. One answer bars a session from building on a commit it did not make. The other would change spec 003's Edge Case "Head without its epoch", where a new commit on top repairs a head. Spec 002 FR-038 and spec 003 FR-039 describe head judging and need to follow the answer.
  - Spec 002 FR-003 and its tool list state that R7 is the human approval for `gitea.commit.set_lease_epoch_status`. This spec now marks that reading as inferred. The two should agree once the person confirms it.
  - Spec 002's actor board-move table (FR-005) still lists TR-01 to TR-13 only. It needs TR-14 for Review and TR-15 for System. Its PSE row (TR-05, TR-08) already reaches Lead on a granted issue through spec 002 FR-031, which matches TR-05 and TR-08 here.
- Items marked incomplete need the person's answer before `/speckit-plan`. The blocking ones are the two FR-038 markers. The "non-technical stakeholders" item and the two "implementation details" items are explained above and do not block.
