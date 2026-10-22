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
- [ ] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

- Items marked incomplete require spec updates before `/speckit-clarify` or `/speckit-plan`. None of the six unticked items blocks `/speckit-clarify`. The two markers should be settled before `/speckit-plan` fixes the progress window and the fence.
- **Unticked: "No implementation details (languages, frameworks, APIs)".** This is not true. The requirements name Gitea 28.x API facts, because the person fixed Gitea as the forge (project intake Q1), and the confirmed review corrections are stated in those terms. Examples:
  - token scopes (`read:repository`, `write:issue`, `read:user`, `read:organization`);
  - the `X-Total-Count` total;
  - status ids;
  - the "Canceled after …" status description;
  - exclusive scoped labels;
  - Bot-type accounts and organisation teams.

  Other named technology was also fixed by the person: SQLite (Q9), OCaml and Python (Q6, Q10), versioned JSON Schemas in `schemas/` (data-model intake Q10, D2), the LangGraph service (Q2), Claude and Ollama (Q7, Q14) and the MacBook host (Q22). This does not block planning.
- **Unticked: "No implementation details leak into specification".** It is the same claim as the first Content Quality item, and it is not true for the same reasons: the requirements name `X-Total-Count`, token scopes, status ids and SQLite. An earlier pass ticked it by reading it as "no technology the person did not fix appears outside Assumptions", as spec 009's checklist reads it. That narrower check still holds and is kept here as a note only. A script checked the text before Assumptions. Pydantic, `ppx_deriving_yojson`, cron, the PostToolUse/PreToolUse hook names, `decide()`, `sdd-jev`, `command_log.py` and the `.jsonl` paths appear only in Assumptions. Endpoint paths and HTTP verbs (`POST` rather than `PUT`, `DELETE …/labels/{id}`) are also kept in Assumptions. The requirements say "add, never replace".
- **Unticked: "Written for non-technical stakeholders".** The readers are the engineering owner, the Lead and Review. The requirements use terms the constitution, the person or the review corrections fixed: lease epoch, debounce, idempotency key, fingerprint, incarnation. The User Stories and Edge Cases stay in plain language. This does not block planning.
- **Unticked: "No [NEEDS CLARIFICATION] markers remain".** Two markers remain. Both are the person's choices, and both were named as open items by the Jev report's conclusion.
  - **FR-015, the durable-progress window**: the default is 60 minutes, and the report says "no source publishes a … threshold". The choices are:
    - (A) keep 60 minutes for every role;
    - (B) set it per role (Lead, PSE, Review), starting at 60 minutes;
    - (C) as B, then recalibrate from the first 4 weeks of scan history, with a person approving each change (FR-048).
  - **FR-029, where the epoch fence lives**: the choices are:
    - (A) only in the coordination layer, where spec 001 FR-032 already rejects older epochs on every write and lease check it handles;
    - (B) also a required lease-epoch commit status in branch protection, so stale-epoch commits can never merge. A person must change branch protection (Art. VI);
    - (C) decide in planning after a Gitea test.

    Spec 001's Assumptions already defer this question to spec 008.

  Resolve them with `/speckit-clarify` or `/speckit-intake-refine specify`.
- **Unticked: "Feature meets measurable outcomes defined in Success Criteria".** The requirements cover every SC, but three outcomes cannot be claimed yet:
  - SC-001 and SC-002 depend on the spinning window, which is still open (FR-015).
  - SC-004's "0 writes presenting an old epoch land" depends on where the fence lives (FR-029). A `git push` goes through git under branch protection, not through the gateway (spec 002 Assumptions). The coordination-layer fence alone may therefore not stop a late push from reaching the branch. User Story 2's narrative, Independent Test and AS-3 now promise only what spec 001 FR-032 gives, the refusal of control-plane and gateway writes, and leave the late push to the FR-029 marker.
  - SC-003's 5% false-stuck target and the suite sizes in SC-001, SC-004 and SC-005 are proposed defaults the owner has not confirmed (Assumptions).
- **Unticked: "Requirements are testable and unambiguous".** A review on 2026-10-22 found these contradictions and gaps. They are fixed in this pass, but no second reader has re-checked the fixes:
  - FR-028 forbade a stop for any session making durable progress, while the CI rule (FR-019, FR-025) and the loop rules (FR-016) stop such sessions through FR-029. FR-028 now follows Q17's terms: a stop only on a stuck verdict, and run time, cost and iteration count are never stop reasons on their own. US2 AS-7 now states the CI and rule conditions.
  - Episodes of stopped or dead sessions had no resolution rule, so L2 and FR-034's re-notification never ended. FR-052 now resolves them once the recovery outcome is recorded, and FR-032, FR-034 and SC-010 use it.
  - The monologue rule and the "since the last human input" window had no evidence source. FR-005 now names lifecycle events.
  - FR-021 now says failing commands never make a scan bad on their own; US1 AS-13 matches.
  - FR-010 no longer asks for the command as text and as a fingerprint at once.

  The item also stays unticked because the waiting pause (FR-014, FR-015, FR-018), the monologue rule (FR-016), the Lead's acknowledgement (FR-032) and the restart count (FR-033) rest on inputs that no upstream spec records yet (FR-005; listed under "Outside this task's files"). They can be tested with fixtures through the decision function, but not end to end. Re-tick after a re-check and once specs 001, 003, 005 and 009 adopt those inputs. FR-015 is testable at its 60-minute default. Two earlier fixes stand: "false-stuck rate" counts once per episode, not per stuck scan (FR-049, SC-003); FR-017's immediacy and FR-045's retry rule are marked inferred.
- **Ticked: "Success criteria are technology-agnostic".** The SCs name no product, language or API. SC-009 mentions "the single host" and the person's capacity, which are outcomes, not technology.
- **Ticked: "Scope is clearly bounded".** A Non-goals list follows Key Entities, as in specs 001 and 005. It covers no code edits, no hard stop by Jev, no in-session loop detector, no promotions, no label or account setup, no wall-clock caps, and no schema definitions.
- **Every functional requirement has an acceptance criterion.** A script mapped the references, and the table below corrects it by hand: cross-spec references such as "spec 001 FR-017" are not this spec's FRs.

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
  | FR-020 | US1 AS-11, Edge Cases (CI cancelled runs) |
  | FR-021 | US1 AS-13 |
  | FR-022 | Edge Cases (shared runner outage), SC-014 |
  | FR-023 | US1 AS-1, AS-6 |
  | FR-024 | US1 AS-14, SC-006 |
  | FR-025 | US1 AS-12 |
  | FR-026 | US3 AS-5, AS-7, Edge Cases (relapse within the hold) |
  | FR-027 | US3 AS-7 |
  | FR-028 | US2 AS-7 |
  | FR-029 | US2 AS-1, AS-3, SC-004 |
  | FR-030 | US2 AS-2, AS-3, Edge Cases (stopped session still silent) |
  | FR-031 | US2 AS-6 |
  | FR-032 | US1 AS-1, US2 AS-1, AS-4, SC-010 |
  | FR-033 | US2 AS-5, SC-011 |
  | FR-034 | US2 AS-4, AS-9 |
  | FR-035 | US3 AS-1, AS-6, Edge Cases (session without a work item) |
  | FR-036 | US1 AS-1, US3 AS-1, AS-11, Edge Cases (a `jev/*` label is missing) |
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
  | 7. Only PSE sessions need a branch | FR-008 |
  | 8. A push is detected by a head change | FR-009 |
  | 9. Self-check and token scopes | FR-040, FR-041 |
  | 10. Labels from repository and organisation, by ID; total-count paging; latest status by id; "Canceled after …" | FR-020, FR-036, FR-038 |
  | 11. One living comment per episode per work item; recreate when deleted; independent label write | FR-037 |
  | 12. Run lock; per-session errors; UTC; episode ids from the slot | FR-026, FR-045, FR-046 |

- **Threshold sourcing**: every threshold cites the Jev report (linked by path) and the upstream source the report gives for it. They are inline in FR-013 to FR-039, and collected in FR-048's table. None of the numbers are the person's words. The report itself labels these as local policy: the 60-minute window, the start-up grace, the L1 and L2 timings, and the circuit-breaker count.
- **The person's words the spec rests on**:
  - Q17, "A session stops only when it is not making successful progress or is stuck.": FR-001, FR-028, and the reason no wall-clock, cost or iteration caps are adopted.
  - Q19: FR-012's mapping table.
  - Q20: FR-047 and SC-009.
  - Q21, "Checkpoint and stop, then escalate": FR-029. The reading that the stop never waits for the person's or Smokey's approval, and that L2 follows, is marked inferred in Assumptions.
- **Inferred rules awaiting the person**. These are marked "(inferred)" in the spec and should go back through `/speckit-intake-refine`:
  - FR-004: the model's inputs, the labelling and the template fallback.
  - FR-005: the inputs no upstream spec records yet (agent messages and human input, waiting on a person, the Lead's acknowledgement, the restart count) and where they would come from.
  - FR-010: the fields added to the command-log entry.
  - FR-013: dead is reported under the stuck kind.
  - FR-016 and FR-017: loop and timeout verdicts skip the two-scan debounce.
  - FR-021: the reading of "supporting": failing commands never make a scan bad on their own.
  - FR-022: at least two sessions, and the scope of the suppression.
  - FR-031: the person carries out the hard stop on the Lead's own session.
  - FR-032: what counts as an acknowledgement.
  - FR-033: an automatic restart is a re-dispatch on a resume or reassign outcome the Lead recorded.
  - FR-035: notices for a session without a work item.
  - FR-041: the version check.
  - FR-043: the reason and next-action names.
  - FR-045: the record's fields and no age-based deletion.
  - FR-047: subagents.
  - FR-048: a person approves threshold changes.
  - FR-049: the metric definitions.
  - FR-050 and FR-051.
  - FR-052: a stopped or dead session's episode resolves once the recovery outcome is recorded, and `jev/parked` stays.
  - The edge cases "waiting is never escalated" and "session ends normally".
  - The Assumptions on paging (including that Smokey is not part of Jev's escalations), the 2-minute default tool timeout and the gateway read tools Jev still lacks.
- **Dependencies** match the fixed dependency map exactly: upstream 001, 002, 003, 005 and 009; downstream 007, one line per edge saying what is consumed. Each upstream line mirrors that spec's own downstream line for 008, except that the 005 and 009 lines now also name lifecycle events (FR-005), which those specs' downstream lines for 008 do not list yet. The build order is copied verbatim.
- **Clarifications**: a script compared all 22 "- Q: … → A: …" lines with the two intakes. The required project-intake lines Q17, Q19, Q20 and Q21 are present. Thirteen other project-intake lines are included: Q1, Q2, Q3, Q7, Q9, Q10, Q12, Q13, Q14, Q15, Q16, Q18 and Q22. So are five data-model lines: Q8 revised, Q9, Q10, Q14 revised and Q25.
- **Outside this task's files** (for the specs' owners):
  - Spec 009 FR-002 lists the Jev message fields without `episode_id` and `evidence`, which the existing schema and FR-042 include. Planning reconciles them, as spec 009's checklist already notes.
  - Spec 005 FR-027, as read on 2026-10-22, now carries FR-010's fields: a start line with the call's own timeout, fingerprints of the call and of its result or error, a timed-out flag, and the command stored as a fingerprint, never as text. Spec 009's command-log schema should adopt them (inferred).
  - Spec 001 records none of three inputs FR-005 needs (inferred): whether a session waits on a person, the Lead's acknowledgement of an episode, and a restart count per work item. It also has no automatic restart: a re-dispatch (001 FR-037) follows a recorded recovery outcome (001 FR-017). FR-033 counts a re-dispatch on a Lead-recorded outcome as an automatic restart. Spec 001 should record re-dispatches per work item, and refuse a re-dispatch on a Lead-recorded outcome for a work item carrying `jev/parked` until a person resets the breaker.
  - Spec 003 FR-031's recorded decision should name the episode id, so that Jev can read it as the Lead's acknowledgement (FR-032) (inferred).
  - Spec 005's lifecycle points (005 FR-019 to FR-023) record no agent message without a tool call, no human input, and no start or end of a wait on a person. FR-016's monologue rule and loop window, and the waiting pause (FR-014, FR-015, FR-018), need them (inferred). Spec 005's downstream line for 008 should also name lifecycle events.
  - Spec 009's lifecycle-event schema should carry those event types, and its downstream line for 008 should name lifecycle events (inferred).
  - Spec 002 FR-001's read tools do not cover every read Jev needs through the gateway (FR-002): a branch's head and commits, Jev's own repository permissions and default-branch push and merge rights, and the Gitea version. Adding them is a Critical-risk change a person approves (002 FR-003).
  - Spec 007 FR-022's working definitions differ from FR-049 in three ways: false-stuck counts per episode; dead sessions are excluded from the stuck rate; recovery may resume in the next session on the same work item. Spec 007 says spec 008 wins, but its checklist asks for a re-check now that 008 exists.
  - Spec 002 FR-027's start-up check covers push and merge on the default branch. FR-041 also refuses repository push or admin permission, unreadable rights and a Gitea version other than 28.x. Spec 002 may want to match.
  - Spec 003 FR-031 gives Lead three decisions: re-plan, reassign or hard stop. FR-049 also needs the Lead or the person to be able to record a verdict as wrong.
  - `specs/README.md` has no rows for 008 or 009, and its map and build order predate the fixed dependency map.
- **Existing code**: `packages/sdd-harness/src/sdd_harness/jev/` was read on 2026-10-22 only to align terminology. This spec does not certify which corrections the code implements. In the code as read:
  - `signals.py` detects a push as a branch-head change between observed scans (`seen_heads`). It still falls back to committer dates when there is no observed history yet, and caps them at Jev's first look for a head that was already there. Both conflict with FR-009's "never by commit dates".
  - There is no monologue rule (FR-016 applies).
  - `decide.py` makes 5 or more failing commands a reason on its own when a scan shows no durable progress, which FR-021 now forbids.
  - Gitea is read directly with Jev's token, not through the gateway (FR-002; Assumptions, gateway path).
- `/speckit-clarify` can proceed. Two markers remain.
