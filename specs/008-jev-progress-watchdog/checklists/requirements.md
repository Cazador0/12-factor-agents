# Specification Quality Checklist: Jev, the Progress Watchdog for Agent Sessions

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
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
- [ ] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`. None of the five unticked items blocks `/speckit-clarify`. No markers remain: the person settled both on 2026-10-22 (project intake R6, R7).
- **Pass of 2026-10-22: the person's specify-phase answers (project intake, Phase Refinements R1 to R8)**. This pass applied R1, R6, R7 and R8, and brought the spec in line with R2. R3, R4 and R5 change nothing here. The changes are:
  - **R6, the durable-progress window (FR-015)**: the marker is gone. The window is 60 minutes for every role: "60 min, per role later (Recommended)". After the first weeks of scan history, per-role values are proposed and take effect only when a person approves them (FR-015, FR-048; Art. VI). FR-048's table, Assumptions and the Constitution notes follow.
  - **R7, where the epoch fence lives (FR-029 step 5)**: the marker is gone. The person answered "Both": the coordination-layer fence (spec 001 FR-032) and a `lease-epoch` commit status that branch protection requires (spec 001 FR-038; spec 002 FR-038). The design beyond the two fences is marked inferred and owned by specs 001, 002 and 003. User Story 2's narrative, its Independent Test and AS-3 no longer call the late push an open question: a late push can land but cannot merge once a person makes `lease-epoch` a required check. FR-002 and the Non-goals now say Jev never posts a commit status. SC-004 now measures both fences. A new edge case covers the late push. Two inferred consequences were added: FR-020 leaves the `lease-epoch` status out of the CI rule and its status count, and a new edge case says so.
  - **R8, labels when several sessions share an issue (FR-036)**: Jev now uses 12 labels, nine role labels (`jev/lead/…`, `jev/pse/…`, `jev/review/…`) and three summary labels (`jev/warning`, `jev/stuck`, `jev/parked`). The scope rule was checked against the Gitea v28.2.0 source on 2026-10-22: `Label.ExclusiveScope` in `models/issues/label.go` (line 185) cuts the name at the last `/`, and `RemoveDuplicateExclusiveIssueLabels` in `models/issues/issue_label.go` (line 63) removes only labels of the same scope. So a role label and the summary label never replace each other. The changed text is US1 AS-1, US2 AS-1, AS-5 and AS-9, User Story 3's narrative and Independent Test, US3 AS-1, AS-7 and AS-11, FR-002, FR-027, FR-033, FR-036, FR-037, FR-052, the edge case "A `jev/*` label is missing", Key Entities and Assumptions (human-owned setup). New text is US3 AS-17, the edge case "Several sessions on one work item" and SC-015.
  - **R1, one session per role (FR-022, FR-047)**: FR-022's dependency alert assumed two or more PSE sessions at once. With one session per role, it now covers every session with a branch, and it can fire only when Lead implements a second part of a partitioned issue under an implementation-worker grant (inferred). A lone zero-status head raises no alert. The shared-runner edge case and SC-014 follow. FR-047, Key Entities, SC-009 and the opening of User Scenarios name the one-per-role division.
  - **R2, Lead under an implementation-worker grant (FR-008)**: R2 itself was applied to spec 003 in the last pass. This spec still said Lead never has a branch, while spec 003 FR-010 gives Lead its own branch under a grant that the owner approves per issue. FR-008 now requires a branch of every session that holds a write lease. FR-005, FR-019, US1 AS-16, the edge case "Sessions without a branch" and Key Entities follow (inferred from spec 003 FR-010).
  - **R3, R4, R5**: none touches this spec's requirements. R4's issue search and milestone lookup do not cover the reads Jev still lacks (Assumptions, gateway path). R5 sets spec 007's headline target. A short note in Assumptions says it sets none of this spec's numbers.
- **Review fixes of 2026-10-22 (second pass over the R1 to R8 changes)**. A review found these, each confirmed in the file before it was changed:
  - R7 citations sat on inferred design. FR-002, US2 AS-3, the late-push edge case, FR-020 and the Non-goals now mark who posts `lease-epoch` as inferred, and keep the R7 citation on the two fences only. FR-002 marks "Jev gains no new right" as inferred from R7's design. FR-029 step 5 now marks reading R7 as the spec 002 FR-003 approval of the new tool as inferred, as spec 001 FR-038 does. The Dependencies line for 002 says the poster is inferred.
  - The breaker reset had no input. FR-005 now lists it, FR-033 says what counts as a reset and that Jev's next observed scan removes the parked labels and zeroes the restart count, and FR-036, US2 AS-9 and Key Entities follow (all inferred).
  - FR-020 contradicted itself: its CI-state bullet now reads "every reported check except `lease-epoch`", and Jev combines the per-context statuses spec 002 FR-036 returns, not its combined state. The justification now covers a head that records no epoch, and names the heads spec 001 judges (pull request heads, outside Shadow mode); the edge case follows.
  - FR-022 treated the spinning clock two ways without a reason. It now gives one: in an outage the alert stands in for the verdicts, and for a lone head nothing does. The outage flag reaches the decision function inside each session's evidence snapshot (FR-003, US1 AS-17, Key Entities), and, because one of the two sessions is always the Lead's own under R1, the alert also goes to the person (FR-031; SC-014 and the edge case follow). FR-022 was not withdrawn: that is the owner's call (see the inferred list).
  - US1 AS-16 now follows FR-008 (any session that holds a write lease and names no branch). FR-027 keeps parked labels. Key Entities no longer says a role label always shows the latest verdict. SC-015 has a suite size, leaves out scans with a failed label write or a person's label edit, and allows the labels Jev removes on purpose. The Input line names R2 and counts five decisions.
- **Unticked: "No implementation details (languages, frameworks, APIs)".** This is not true. The requirements name Gitea 28.x API facts, because the person fixed Gitea as the forge (project intake Q1), and the confirmed review corrections are stated in those terms. Examples:
  - token scopes (`read:repository`, `write:issue`, `read:user`, `read:organization`);
  - the `X-Total-Count` total;
  - status ids;
  - the "Canceled after …" status description;
  - exclusive scoped labels, and Gitea's `ExclusiveScope` rule, cited from its source (FR-036);
  - Bot-type accounts and organisation teams;
  - spec 002's tool `gitea.commit.set_lease_epoch_status`, named in FR-029 step 5 as the R7 design relays it.

  Other named technology was also fixed by the person: SQLite (Q9), OCaml and Python (Q6, Q10), versioned JSON Schemas in `schemas/` (data-model intake Q10, D2), the LangGraph service (Q2), Claude and Ollama (Q7, Q14) and the MacBook host (Q22). This does not block planning.
- **Unticked: "No implementation details leak into specification".** It is the same claim as the first Content Quality item, and it is not true for the same reasons. An earlier pass ticked it by reading it as "no technology the person did not fix appears outside Assumptions", as spec 009's checklist reads it. A script re-checked the text before Assumptions on 2026-10-22. Pydantic, `ppx_deriving_yojson`, cron, the PostToolUse/PreToolUse hook names, `decide()`, `sdd-jev`, `command_log.py`, the `.jsonl` paths, and the HTTP verbs `POST`, `PUT` and `DELETE` appear only in Assumptions. Before Assumptions it found `X-Total-Count`, SQLite, `ExclusiveScope` and `gitea.commit.set_lease_epoch_status`, once each. The first two were already there; the last two come with R8 and R7. The requirements say "add, never replace".
- **Unticked: "Written for non-technical stakeholders".** The readers are the engineering owner, the Lead and Review. The requirements use terms the constitution, the person or the review corrections fixed: lease epoch, debounce, idempotency key, fingerprint, incarnation, exclusive scope. The User Stories and Edge Cases stay in plain language. This does not block planning.
- **Ticked: "No [NEEDS CLARIFICATION] markers remain".** The spec holds no markers. The two it held were the person's choices, and both are now answered:
  - FR-015, the durable-progress window: "60 min, per role later (Recommended)" (project intake R6);
  - FR-029, where the epoch fence lives: "Both" (project intake R7).

  Spec 001 FR-038 and spec 002 FR-038 hold a related marker about pull requests from branches a person pushed. It belongs to those specs, and this spec does not repeat it (see "Outside this task's files").
- **Unticked: "Feature meets measurable outcomes defined in Success Criteria".** The requirements cover every SC, and SC-001 and SC-002 no longer wait on the window (R6). Three outcomes still cannot be claimed:
  - SC-004's merge half holds only once specs 001, 002 and 003 build the forge-side fence and a person adds `lease-epoch` to branch protection's required checks. That person may wait for the open marker in spec 001 FR-038 and spec 002 FR-038, because a required `lease-epoch` would block pull requests from branches a person pushed.
  - SC-014 now needs a Lead session working a second part of an issue to produce two heads (FR-022). It cannot be observed in normal operation with one PSE session, only in replay.
  - SC-003's 5% false-stuck target and the suite sizes in SC-001, SC-004, SC-005 and SC-015 are proposed defaults the owner has not confirmed (Assumptions).
- **Unticked: "Requirements are testable and unambiguous".** An earlier review on 2026-10-22 found contradictions and gaps, which were fixed but never re-checked by a second reader:
  - FR-028 now follows Q17's terms, and US2 AS-7 states the CI and rule conditions.
  - FR-052 resolves the episodes of stopped or dead sessions; FR-032, FR-034 and SC-010 use it.
  - FR-005 names lifecycle events for the monologue rule and the "since the last human input" window.
  - FR-021 says failing commands never make a scan bad on their own; US1 AS-13 matches.
  - FR-010 no longer asks for the command as text and as a fingerprint at once.

  The R1 to R8 pass added text that no second reader had checked: FR-008 (Lead under a grant), FR-020 (the `lease-epoch` exclusion), FR-022 (R1), FR-029 step 5, FR-036 and SC-015. A review then found the defects listed under "Review fixes", and the fixes, including the breaker reset in FR-005 and FR-033 and FR-022's new reason, have not been re-read by a second reader either. Two gaps are known and left to planning (inferred):
  - A stopped session's late push that lands after its work item was re-dispatched changes the branch head, and FR-009 would count it as the new incarnation's push. FR-007's incarnation scoping does not say how to tell them apart. The head's `lease-epoch` failure could do it, but this spec does not say so.
  - A live session whose commits record no epoch keeps pushing heads that fail `lease-epoch` and can never merge. Each push counts as durable progress and the CI rule leaves `lease-epoch` out, so no Jev rule sees it (FR-020).

  The item also stays unticked because the waiting pause (FR-014, FR-015, FR-018), the monologue rule (FR-016), the Lead's acknowledgement (FR-032), the restart count and the breaker reset (FR-033) rest on inputs that no upstream spec records yet (FR-005; listed under "Outside this task's files"). They can be tested with fixtures through the decision function, but not end to end. Re-tick after a re-check and once specs 001, 003, 005 and 009 adopt those inputs. Two earlier fixes stand: "false-stuck rate" counts once per episode, not per stuck scan (FR-049, SC-003); FR-017's immediacy and FR-045's retry rule are marked inferred.
- **Ticked: "Success criteria are technology-agnostic".** The SCs name no product, language or API. SC-004 names the `lease-epoch` status and branch protection, and SC-015 names the `jev/` labels. All three are the person's choices (R7, R8), not technology. SC-009 mentions "the single host" and the person's capacity, which are outcomes, not technology.
- **Ticked: "Scope is clearly bounded".** A Non-goals list follows Key Entities, as in specs 001 and 005. It covers no code edits, no hard stop by Jev, no in-session loop detector, no promotions, no label or account setup, no branch-protection writes, no commit statuses, no wall-clock caps, and no schema definitions.
- **Every functional requirement has an acceptance criterion.** A script mapped the references, and the table below corrects it by hand: cross-spec references such as "spec 001 FR-017" are not this spec's FRs. Rows changed in the R1 to R8 pass: FR-020, FR-027, FR-029, FR-033 and FR-036. FR-008, FR-022 and FR-047 changed in the spec but kept their rows. The review fixes changed no row.

  | Requirement | Acceptance criteria |
  |---|---|
  | FR-001 | US3 AS-14 |
  | FR-002 | US2 AS-1, US3 AS-14, SC-007 |
  | FR-003 | US1 AS-17, US1 Independent Test |
  | FR-004 | US3 AS-12 |
  | FR-005 | US1 AS-4, AS-8, AS-16 |
  | FR-006 | US1 AS-2, Edge Cases (forged Jev text) |
  | FR-007 | Edge Cases (session restarted) |
  | FR-008 | US1 AS-16, Edge Cases (sessions without a branch) |
  | FR-009 | US1 AS-6, Edge Cases (push of an old commit) |
  | FR-010 | US1 AS-3, AS-8 |
  | FR-011 | US1 AS-14, Edge Cases (Gitea unreachable), SC-006 |
  | FR-012 | US1 AS-2, SC-001 |
  | FR-013 | US1 AS-15 |
  | FR-014 | US1 AS-1, AS-3, AS-4, AS-5, Edge Cases (in-flight call, start-up), SC-001, SC-002 |
  | FR-015 | US1 AS-3, AS-4, AS-6 |
  | FR-016 | US1 AS-7, AS-8 |
  | FR-017 | US1 AS-9 |
  | FR-018 | US1 AS-3, AS-4, AS-10, Edge Cases (waiting on a human, nothing new since the last observed scan) |
  | FR-019 | US1 AS-11, US2 AS-8, Edge Cases (zero-status pending) |
  | FR-020 | US1 AS-11, Edge Cases (CI cancelled runs, the `lease-epoch` status on a head) |
  | FR-021 | US1 AS-13 |
  | FR-022 | Edge Cases (shared runner outage), SC-014 |
  | FR-023 | US1 AS-1, AS-6 |
  | FR-024 | US1 AS-14, SC-006 |
  | FR-025 | US1 AS-12 |
  | FR-026 | US3 AS-5, AS-7, Edge Cases (relapse within the hold) |
  | FR-027 | US3 AS-7, SC-010 |
  | FR-028 | US2 AS-7 |
  | FR-029 | US2 AS-1, AS-3, Edge Cases (late push from a stopped session), SC-004 |
  | FR-030 | US2 AS-2, AS-3, Edge Cases (stopped session still silent) |
  | FR-031 | US2 AS-6 |
  | FR-032 | US1 AS-1, US2 AS-1, AS-4, SC-010 |
  | FR-033 | US2 AS-5, AS-9, SC-011 |
  | FR-034 | US2 AS-4, AS-9 |
  | FR-035 | US3 AS-1, AS-6, Edge Cases (session without a work item) |
  | FR-036 | US1 AS-1, US2 AS-5, AS-9, US3 AS-1, AS-7, AS-11, AS-17, Edge Cases (several sessions on one work item, a `jev/*` label is missing), SC-015 |
  | FR-037 | US3 AS-1 to AS-4, SC-005 |
  | FR-038 | US3 AS-11 |
  | FR-039 | US3 AS-2, AS-5, SC-005 |
  | FR-040 | US3 AS-10, SC-007 |
  | FR-041 | US3 AS-10, Edge Cases (token gains push rights, Gitea is not 28.x), SC-007 |
  | FR-042 | US3 AS-8, AS-9, SC-008 |
  | FR-043 | US3 AS-9 |
  | FR-044 | US3 AS-8, SC-008 |
  | FR-045 | US3 AS-5 |
  | FR-046 | US1 AS-16, US3 AS-5, AS-13, Edge Cases (one session's scan fails, overlapping runs, timestamps without a zone), SC-009, SC-013 |
  | FR-047 | Edge Cases (a subagent hangs), SC-009 |
  | FR-048 | Edge Cases (an agent edits the thresholds) |
  | FR-049 | US3 AS-16, SC-003, SC-012 |
  | FR-050 | US3 AS-16 |
  | FR-051 | US3 AS-15 |
  | FR-052 | US2 AS-9, SC-010 |

- **The twelve review corrections**: each is stated as a requirement marked "(inferred; review correction N)".

  | Correction | Requirements |
  |---|---|
  | 1. An unknown scan changes nothing | FR-011, FR-024 |
  | 2. An obeyed or revoked stop is recognized as stopped | FR-030 |
  | 3. A red push does not reset the CI debounce | FR-025 |
  | 4. Loop and timeout rules re-apply only on new calls; waiting pauses the loop and CI rules; an in-flight call pauses only the hung clock | FR-018 |
  | 5. Recovery requires durable progress; resolution is retried | FR-027 |
  | 6. Evidence is scoped to the incarnation | FR-007 |
  | 7. Only sessions that hold a write lease need a branch: PSE, and Lead under an implementation-worker grant (the Lead part follows spec 003 FR-010 and R2) | FR-008 |
  | 8. A push is detected by a head change | FR-009 |
  | 9. Self-check and token scopes | FR-040, FR-041 |
  | 10. Labels from repository and organisation, by ID; total-count paging; latest status by id; "Canceled after …" | FR-020, FR-036, FR-038 |
  | 11. One living comment per episode per work item; recreate when deleted; independent label write | FR-037 |
  | 12. Run lock; per-session errors; UTC; episode ids from the slot | FR-026, FR-045, FR-046 |

- **Threshold sourcing**: every threshold cites the Jev report (linked by path) and the upstream source the report gives for it. They are inline in FR-013 to FR-039, and collected in FR-048's table. The person confirmed one of them: the 60-minute durable-progress window for every role, with per-role values later that a person approves (project intake R6). None of the other numbers are the person's words. The report itself labels these as local policy: the 60-minute window, the start-up grace, the L1 and L2 timings, and the circuit-breaker count.
- **The person's words the spec rests on**:
  - Q17, "A session stops only when it is not making successful progress or is stuck.": FR-001, FR-028, and the reason no wall-clock, cost or iteration caps are adopted.
  - Q19: FR-012's mapping table.
  - Q20: FR-047 and SC-009.
  - Q21, "Checkpoint and stop, then escalate": FR-029. The reading that the stop never waits for the person's or Smokey's approval, and that L2 follows, is marked inferred in Assumptions.
  - R1, "One per role (Recommended)": FR-022, FR-047, SC-009, SC-014 and the opening of User Scenarios.
  - R2, "Owner, per issue (Recommended)": FR-008, through spec 003 FR-010.
  - R6, "60 min, per role later (Recommended)": FR-015 and FR-048.
  - R7, "Both": the two fences in FR-029 step 5, User Story 2 and SC-004. FR-002's rule that Jev never posts a commit status, the `lease-epoch` one included, and gains no new right is inferred from R7's design; it is not the person's words. So is who posts the status.
  - R8, "All three", confirmed as "Role labels + summary (Recommended)": FR-036, and every scenario and requirement that names a `jev/` label.
- **Inferred rules awaiting the person**. These are marked "(inferred)" in the spec and should go back through `/speckit-intake-refine`:
  - FR-002: Jev never posts a commit status, the `lease-epoch` one included; the control plane posts it; Jev gains no new right from the fence.
  - FR-003: the runner-outage flag reaches the decision function inside each session's evidence snapshot.
  - FR-004: the model's inputs, the labelling and the template fallback.
  - FR-005: the inputs no upstream spec records yet (agent messages and human input, waiting on a person, the Lead's acknowledgement, the restart count, a person's breaker reset) and where they would come from.
  - FR-008: Lead under an implementation-worker grant names a branch and is judged on its branch and CI.
  - FR-010: the fields added to the command-log entry.
  - FR-013: dead is reported under the stuck kind.
  - FR-015: how many weeks of scan history a per-role proposal needs, and that an agent may draft it.
  - FR-016 and FR-017: loop and timeout verdicts skip the two-scan debounce.
  - FR-020: the `lease-epoch` status is left out of the CI state and its status count; Jev combines the per-context statuses itself; the heads it is posted on; and that a live session whose heads record no epoch is not detected.
  - FR-021: the reading of "supporting": failing commands never make a scan bad on their own.
  - FR-022: at least two sessions; the scope of the suppression and its reason (the alert stands in for the verdicts, so a lone head's spinning clock keeps running); the outage flag in the evidence snapshot; under R1, that the alert fires only when Lead works a second part, goes to the person as well as the Lead, and that a lone zero-status head raises none. The owner may prefer to withdraw FR-022, or to detect a runner outage another way, since under R1 an outage that one branch sees raises no alert.
  - FR-029 step 5: everything beyond the two fences, as R7 is read: the commit trailer, the System actor judging and posting, fail closed on a missing epoch, the tool's name and row, and R7 read as the spec 002 FR-003 approval of `gitea.commit.set_lease_epoch_status`. Specs 001, 002 and 003 carry the same inference.
  - FR-031: the person carries out the hard stop on the Lead's own session.
  - FR-032: what counts as an acknowledgement.
  - FR-033: an automatic restart is a re-dispatch on a resume or reassign outcome the Lead recorded; a reset is a person's recorded act, either a reset recorded from their account or their removal of a parked label, observed by spec 001 FR-036; after a reset, Jev's next observed scan removes the parked labels, zeroes the restart count and recomputes the summary.
  - FR-035: notices for a session without a work item.
  - FR-036: the severity order (parked, then stuck, then warning); a label stays through the stop ladder and the recovery hold; the summary is computed from Jev's own records, not from the issue's labels; a role label is removed when its episode closes, and a standing parked label blocks that role's warning and stuck labels. Together these mean a role label shows its open episode's latest bad verdict, or parked, which can lag R8's "latest verdict" during the recovery hold or under a parked label; the person should confirm that gap.
  - FR-041: the version check.
  - FR-043: the reason and next-action names.
  - FR-045: the record's fields and no age-based deletion.
  - FR-047: subagents; one live session per role means one session per role label at a time.
  - FR-048: a person approves threshold changes. R6 now backs this for the durable-progress window.
  - FR-049: the metric definitions.
  - FR-050 and FR-051.
  - FR-052: a stopped or dead session's episode resolves once the recovery outcome is recorded, and parked labels stay.
  - The edge cases "waiting is never escalated", "session ends normally", "a lone zero-status head", "the `lease-epoch` status on a head", and who posts the failure in "late push from a stopped session" (also US2 AS-3).
  - SC-015's suite size and its exclusion of scans with a failed label write or a person's label edit.
  - The Assumptions on paging (including that Smokey is not part of Jev's escalations), the 2-minute default tool timeout and the gateway read tools Jev still lacks.
- **Dependencies** match the fixed dependency map exactly: upstream 001, 002, 003, 005 and 009; downstream 007, one line per edge saying what is consumed. Each upstream line mirrors that spec's own downstream line for 008, as read on 2026-10-22. The 001 line now names both epoch fences (001 FR-032, FR-038), and the 002 line names the 12 `jev/` labels and the `lease-epoch` status (002 FR-027, FR-034, FR-038). One exception remains: the 005 and 009 lines also name lifecycle events (FR-005), which those specs' downstream lines for 008 do not list yet. The build order is copied verbatim.
- **Clarifications**: a script compared all 27 "- Q: … → A: …" lines with the two intakes on 2026-10-22. The required project-intake lines Q17, Q19, Q20 and Q21 are present. Thirteen other project-intake lines are included: Q1, Q2, Q3, Q7, Q9, Q10, Q12, Q13, Q14, Q15, Q16, Q18 and Q22. So are five data-model lines: Q8 revised, Q9, Q10, Q14 revised and Q25. Five Phase Refinements lines were added in this pass, R1, R2, R6, R7 and R8, each copied exactly from its row in the form "(project intake, R<n>)". R3, R4 and R5 have no line, because they change nothing here.
- **Outside this task's files** (for the specs' owners):
  - Spec 009 FR-002 lists the Jev message fields without `episode_id` and `evidence`, which the existing schema and FR-042 include. Planning reconciles them, as spec 009's checklist already notes.
  - Spec 005 FR-027, as read on 2026-10-22, now carries FR-010's fields: a start line with the call's own timeout, fingerprints of the call and of its result or error, a timed-out flag, and the command stored as a fingerprint, never as text. Spec 009's command-log schema should adopt them (inferred).
  - Spec 001 records none of four inputs FR-005 needs (inferred): whether a session waits on a person, the Lead's acknowledgement of an episode, a restart count per work item, and a breaker reset recorded from a person's account. Spec 001 FR-036 already records a person's label change as an observed event, which FR-033 reads as the other form of reset. Spec 001 also has no automatic restart: a re-dispatch (001 FR-037) follows a recorded recovery outcome (001 FR-017). FR-033 counts a re-dispatch on a Lead-recorded outcome as an automatic restart. Spec 001 should record re-dispatches per work item, and refuse a re-dispatch on a Lead-recorded outcome for a work item whose breaker Jev records as parked until a person's reset is recorded. It should key that refusal on the same breaker record and reset that FR-033 reads, not on the `jev/parked` label, so that the two never disagree (inferred).
  - Spec 001 FR-038 and spec 002 FR-038 hold an open marker: once `lease-epoch` is required, a pull request from a branch a person pushed records no epoch and could never merge. SC-004's merge half waits on it (see above). Spec 003 FR-020 holds a related marker on Review's test-only commits.
  - Spec 003 FR-020's marker also decides whether Review has a branch. If the person gives Review a test-only write lease and branch, FR-008's general rule ("only a session that holds a write lease must name a branch") already covers it, and Jev watches that branch's CI. But US1 AS-16 ("a Review session, which has no branch"), the edge case "Sessions without a branch" and FR-008's "(Review, and Lead without a write lease)" would have to change. Until the marker is settled, those three places assume Review holds no write lease.
  - Spec 002 FR-036, as read on 2026-10-22, counts `lease-epoch` in the combined state that `gitea.commit.checks` and `gitea.pr.checks` return, and also returns each context's latest status. FR-020 therefore combines those per-context statuses itself, leaving `lease-epoch` out, and never takes the tools' combined state as the CI state. Spec 002 needs no change for this (inferred).
  - Spec 003 FR-031's recorded decision should name the episode id, so that Jev can read it as the Lead's acknowledgement (FR-032) (inferred).
  - Spec 005's lifecycle points (005 FR-019 to FR-023) record no agent message without a tool call, no human input, and no start or end of a wait on a person. FR-016's monologue rule and loop window, and the waiting pause (FR-014, FR-015, FR-018), need them (inferred). Spec 005's downstream line for 008 should also name lifecycle events.
  - Spec 009's lifecycle-event schema should carry those event types, and its downstream line for 008 should name lifecycle events (inferred).
  - Spec 002 FR-001's read tools do not cover every read Jev needs through the gateway (FR-002): a branch's head and commits, Jev's own repository permissions and default-branch push and merge rights, and the Gitea version. R4 added issue search and milestone lookup only. Adding the others is a Critical-risk change a person approves (002 FR-003).
  - Spec 007 FR-022's working definitions differ from FR-049 in three ways: false-stuck counts per episode; dead sessions are excluded from the stuck rate; recovery may resume in the next session on the same work item. Spec 007 says spec 008 wins, but its checklist asks for a re-check now that 008 exists.
  - Spec 002 FR-027's start-up check covers push and merge on the default branch. FR-041 also refuses repository push or admin permission, unreadable rights and a Gitea version other than 28.x. Spec 002 may want to match.
  - Spec 003 FR-031 gives Lead three decisions: re-plan, reassign or hard stop. FR-049 also needs the Lead or the person to be able to record a verdict as wrong.
  - `specs/README.md` now has rows for 008 and 009 that match the fixed dependency map. Its 008 row, as read on 2026-10-22, names the R6 window, both epoch fences (R7) and the role and summary labels (R8). An earlier version of this note said it did not; that was wrong. What README still lacks is in its glossary: the entry for Jev says branch commits and head CI are read "for a PSE session", which leaves out Lead under an implementation-worker grant (R2; FR-008).
- **Existing code**: `packages/sdd-harness/src/sdd_harness/jev/` was read on 2026-10-22 only to align terminology. This spec does not certify which corrections the code implements. In the code as read:
  - `signals.py` detects a push as a branch-head change between observed scans (`seen_heads`). It still falls back to committer dates when there is no observed history yet, and caps them at Jev's first look for a head that was already there. Both conflict with FR-009's "never by commit dates".
  - There is no monologue rule (FR-016 applies).
  - `decide.py` makes 5 or more failing commands a reason on its own when a scan shows no durable progress, which FR-021 now forbids.
  - Gitea is read directly with Jev's token, not through the gateway (FR-002; Assumptions, gateway path).
  - `scan.py` knows only the three summary labels (`jev/warning`, `jev/stuck`, `jev/parked`). It has no role labels and no summary recomputation (FR-036).
  - `gitea.py` combines every non-cancelled status of a head, so a `lease-epoch` status would count as CI (FR-020).
- `/speckit-clarify` can proceed. No markers remain.
