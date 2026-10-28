# Specification Quality Checklist: Context Engineering and Long-Horizon Continuity

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
- [ ] Success criteria are technology-agnostic (no implementation details)
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

- **Unticked in the review of the R1-R8 round: "No [NEEDS CLARIFICATION] markers remain", "Requirements are testable and unambiguous" and "Feature meets measurable outcomes defined in Success Criteria".** The R7 round ticked all three while FR-012 stated the late-push rule more weakly than the person's "a commit from a stale epoch can never merge" (the intake's reading of "Both", project intake R7). FR-012 only barred the replacement from building on a late-push commit "until it has reported the divergence and reconciled", and reconciling from the branch adopts the branch head, stale commit included. Its next commit would then pass `lease-epoch`, which judges only the head (spec 001 FR-038), and carry the stale commit to merge. The Edge Case stated the rule without that condition, and nothing ensured SC-012's "0 ... merge". The fix:
  - FR-012 now bars the replacement, without condition, from committing on top of such a commit, pushing a head that contains it, or adopting it when it reconciles (inferred). The new FR-032 runs the check again before each push and after a push rejected as non-fast-forward, because a late push can land after the replacement has started. US1 AS-8, the Edge Case and SC-012 use the same rule.
  - How the stale commit leaves the branch (dropped, kept after a person reviews it, or left to a recovery assessment), and whether a reverted or squashed stale commit counts as "merged", is the person's choice. FR-012 now holds one [NEEDS CLARIFICATION] marker for it (1 of 3). Spec 001 FR-038's second marker asks the same question, so one answer settles both.
  - The three items stay unticked until that marker is answered: the marker remains, FR-012's next step after the ban is open, and SC-012's "0 merge" target cannot be shown met while it is.
- **"Requirements are testable and unambiguous" was ticked again after these fixes, before the R7 round.** The previous version ticked it while the spec held undefined terms and a self-contradicting FR-008. The fixes:
  - **FR-008 (stale)**: the old rule ("not an ancestor of its head") would have served the old ADR chunk that the spec's own US4 test expects to be rejected. Stale now means (a) the indexed commit is unreachable from the head, (b) the chunk's unit changed between the indexed commit and the head, or (c), added in the second review pass, a Gitea text's version changed or the text was deleted. US4 AS-2, AS-3, AS-6 and SC-003 use the same definition.
  - **FR-011 ("long-running session")**: now "every role session", matching Art. I, spec 003 FR-024 and this spec's own FR-023.
  - **FR-014 ("consequential step")**: now an enumerated list. SC-004, US2 AS-1 and the US2 Independent Test all use that term.
  - **FR-015 ("hidden model reasoning")**: now defined by provider-marked reasoning output plus the schema allowlist, with fixtures (SC-005).
  - **FR-016 ("production run")**: dropped. Chains are now off for every run.
  - **SC-001 ("same final state")**: replaced by outcome equivalence, since model-driven runs are nondeterministic.
  - **FR-003**: now has a proposed length default.
- **One marker (FR-012), and no others.** The FR-012 marker is above. The open items carried from the intakes are planning items, not choices still waiting on the person, so they appear as Assumptions:
  - how lifecycle points bind to the LangGraph service (project intake open item, cites Q2);
  - whether sqlite-vec meets p95 under 200 ms at 1 million chunks (data-model intake open item);
  - whether this repository is mirrored into Gitea (project intake open item).

  The earlier open item on storage was resolved by project intake Q9, and the earlier scale item by Q18, Q20 and data-model intake Q8.
- **Unticked: "Written for non-technical stakeholders"**. This item was ticked before, but it is not true. The readers are the engineering owner and the role agents. The requirements use terms that the constitution or the design fixed: commit reachability, lease epoch, schema allowlist, provenance. The User Stories stay in plain language. This item does not block planning.
- **Unticked: "No implementation details" (Content Quality), "Success criteria are technology-agnostic" and "No implementation details leak into specification" (Feature Readiness).** These were ticked before on the grounds that the person chose the technology. Who chose a technology does not make these items true. The spec names:
  - SQLite with sqlite-vec plus the custom Python vector backend (project intake Q9; data-model intake Q7; FR-025);
  - Claude thinking and redacted-thinking blocks and Ollama `<think>` segments (project intake Q7, Q14; FR-015 names them only to define what is never stored);
  - the MacBook Pro M4 Pro host, inside a success criterion (project intake Q22; data-model intake Q14; SC-007);
  - `git-history.md`, the person's own file name (data-model intake Q13, Q20, Q26);
  - the `{command, exit_code, at}` command-log entry of the decision record for spec 008 (FR-027, Key Entities).

  These are person-fixed constraints or interfaces shared with spec 008, so they do not block planning, in the same way as the "non-technical stakeholders" item. The hook, its log path `.specify/sessions/commands/<session_id>.jsonl` and the trace path `.specify/traces/<run>/trace.jsonl` appear only in Assumptions, cited to spec 008's Assumptions (Command log), not to the Jev research report, which names none of them. The lexical method, the reranker, the embedding model and the language reading are all in Assumptions.
- **Every functional requirement has an acceptance criterion.** This was ticked before while FR-005, FR-009, FR-010 and FR-022 had none (FR-010 and FR-022 appeared only in Edge Cases). It is ticked again after US4 AS-7 (chunk boundaries), US4 AS-8 (retrieved instructions are data), US2 AS-6 (subagent start record and cap refusal), US4 AS-6 (edited Gitea text), US1 AS-6 (compaction) and US1 AS-7 (Review checkpoint) were added:

  | Requirement | Acceptance criteria |
  |---|---|
  | FR-001 to FR-003 | US5, SC-006 |
  | FR-004, FR-005 | US4 AS-6, AS-7 |
  | FR-006 | US4 AS-1, AS-6 |
  | FR-007 | US4 AS-1, AS-4, SC-007 |
  | FR-008 | US4 AS-2, AS-3, AS-6, SC-003 |
  | FR-009, FR-010 | US4 AS-8 |
  | FR-011, FR-012 | US1 AS-1, AS-2, AS-5, AS-7, AS-8, SC-001, SC-012 |
  | FR-013 | US1 AS-3, Edge Cases (missing trace) |
  | FR-014 | US2 AS-1, AS-2, SC-004 |
  | FR-015 | US2 AS-3, SC-005 |
  | FR-016, FR-017 | US3 |
  | FR-018 | US2 AS-4, Edge Cases (secrets), SC-005, SC-009 |
  | FR-019 | US1 AS-1, AS-8, US6 AS-1 |
  | FR-020 | US2 AS-5, SC-002 |
  | FR-021 | US2 Independent Test |
  | FR-022 | US2 AS-6 |
  | FR-023 | US1 AS-4, AS-5, SC-011 |
  | FR-024 | SC-010 |
  | FR-025 | US4 AS-1, SC-007 |
  | FR-026 | US6, SC-008 |
  | FR-027 | US2 AS-4, SC-009 |
  | FR-028 | US1 AS-4, SC-011 |
  | FR-029 | US2 AS-4, SC-010 |
  | FR-030 | US4 AS-5 |
  | FR-031 | US1 AS-6, SC-001 |
  | FR-032 | US1 AS-8, SC-012 |

- **Review findings applied**:
  - all confirmed high and medium findings;
  - the low-severity ones: production run, length default, the storage Assumption, the Art. III citations, the spec ID format, and this checklist;
  - both missed findings: Shadow mode (FR-028, US1 AS-4, SC-011), and the downstream mismatch, where 006 and 007 are now Related per the fixed map.

  One part was applied differently. The confirmed finding asked to add 002 as an upstream of 005. The fixed dependency map does not allow that edge. Instead:
  - FR-020 records the outcome of 001's and 002's checks rather than re-deciding them;
  - FR-028 routes every write through 001, which carries it through 002 at runtime;
  - 002 is listed as Related, not upstream.
- **New in this pass**:
  - spec 009 owns the record schemas, and this spec owns when and how the records are written and read (FR-024, SC-010);
  - the retrieval index lives in spec 009's store (FR-025);
  - provenance includes the tenant, and results without source and commit are refused (FR-006);
  - "stale results never appear", so SC-003 now targets 0 stale chunks served, where it previously allowed under 1%;
  - store now, embed later (FR-030);
  - the `git-history.md` feed to spec 009's knowledge graph (FR-026, US6, SC-008);
  - the command log that Jev reads (FR-027, SC-009);
  - agent-loop timestamps for Jev (FR-029);
  - the stop reason and lease epoch in checkpoints (FR-011);
  - a Non-goals subsection, added as spec 001 did.

  Clarifications moved to the last section and now carry each intake and Q number.
- **Inferred rules awaiting the person**. The person did not state these. They are marked "(inferred)" in the spec and should go back through `/speckit-intake-refine`:
  - FR-001: the governed repositories are the product repositories in Gitea.
  - FR-005: `git-history.md` is chunked by commit.
  - FR-007: knowledge-graph results follow the same provenance and staleness rules.
  - FR-008 (b): changes are compared per structural unit.
  - FR-014: a plan change is a consequential step.
  - FR-015: the definition of hidden model reasoning.
  - FR-016: a person or Lead switches chains on.
  - FR-006, FR-008 (c): for Gitea issues, comments and PR summaries, the Gitea ID and the text's version stand in for source and commit, and a chunk is stale when the live version differs or the text was deleted.
  - FR-011, FR-012, FR-019: a planning Lead's checkpoint covers each issue it plans; a Review checkpoint records the reviewed pull request and head commit; a Lead without a write lease records and verifies issue state and board column.
  - FR-023: the escalation after a self-judged stuck stop goes to the Lead, or to a person when the Lead is stuck.
  - FR-024: a session adds its own checkpoints and traces and does not rewrite an earlier session's. This is narrower than data-model intake Q9 ("Its owning role only ... everyone in the tenant reads"), which FR-024 now states as the person gave it.
  - FR-027: every command-log field beyond `{command, exit_code, at}` (start lines, the call's own timeout, the result fingerprint, the timed-out flag), storing the command as a fingerprint rather than text, and never blocking a tool call. These follow spec 008 FR-010 and the hook as built.
  - FR-031: compaction alone neither stops nor replaces a session; it checkpoints before compaction where the runtime allows, then reloads its checkpoint and renews its lease.
  - FR-012 (R7 round, tightened in its review): how a resuming session works within the two fences the person chose. Outside Shadow mode, a replacement for a session that held a write lease holds a new lease with a higher epoch, and its commits record that epoch, never its checkpoint's. A commit after the replacement's base commit that records an older epoch is a late push from the replaced session: the replacement never commits on top of it, never pushes a head that contains it, and does not adopt it when it reconciles. The epoch is compared with the current epoch of the same issue or part (spec 001 FR-032). US1 AS-8 and SC-012 test this.
  - FR-032: the late-push check runs again before each push and after a push rejected as non-fast-forward.
  - FR-011, FR-019, Key Entities: for a partitioned issue, the checkpoint and the session-start fetch record the part the lease covers.
  - FR-019, US1 AS-8, the "Two checkpoints for one lease" edge case: that a commit records its lease's epoch, and that the control plane judges the head and posts `lease-epoch`. Only the two fences are the person's (R7); these clauses are now marked (inferred) and cite spec 001 FR-038 and spec 003 FR-039, not R7.
  - The "Two checkpoints for one lease" edge case: a Review checkpoint and a Lead checkpoint for another part under an R2 grant are expected, not a conflict.
  - SC-012: the 0-heads-pushed and 100%-own-epoch targets, and the drill conditions (Agent implementation mode, an open pull request, `lease-epoch` required by a person).
  - Edge Cases: entries for commits made by people, pushes by others, and death after a push.
  - Assumptions: the drill mode, the 150-line `AGENTS.md` limit, the chain step fields, the reading of Q10, and 10 agents = 3 sessions + 6 subagents + Jev.
- **Second review pass (fixes applied)**:
  - Command log (FR-027, SC-009, US2 AS-4, Key Entities, Assumptions, Dependencies): 005 said one entry per command, holding the command text, in `commands.jsonl`. The hook as built keeps a start and an end line per tool call, with fingerprints only, and spec 008 FR-010's last bullet needs the start line (its first sentence still says one line per call; see "Outside this task's files"), in `.specify/sessions/commands/<session_id>.jsonl`. FR-027 now follows 008 and the hook, keeps the decision record's `{command, exit_code, at}` as the core of each end line, and marks every other field (inferred).
  - Non-git provenance (FR-006, FR-008 (c), SC-003, US4 AS-6, Edge Cases): Gitea text has no commit, and FR-008 (a) and (b) could not see an edit made in Gitea, so SC-003 could not be verified for those sources.
  - Checkpoints for Review and planning Lead sessions (FR-011, FR-012, FR-019, Key Entities, US1 AS-7, Edge Cases): branch, head commit and lease epoch are now required only where the session holds them, matching FR-020.
  - Compaction (US1, US1 AS-6, FR-023, FR-031, SC-001): compaction is now a self-resume by the same session, with no recovery assessment, matching project intake Q17 and spec 001 FR-017. It was counted as a disappearance before.
  - FR-024 now states data-model intake Q9 as given: the owning role changes a record and everyone in the tenant reads it.
  - Evidence (FR-011, Dependencies Art. IV): "not applicable" with its reason is now a third evidence state, as Art. IV requires.
  - FR-023: step 3 escalates only after a self-judged stuck stop (spec 003 FR-036), names the recipient, and leaves the escalation after a Jev-requested stop to Jev (spec 008 FR-029, FR-032). The lease release moved to the last step, because spec 003 FR-036 posts the escalation while the session still holds its lease and spec 002 FR-007 requires the lease for a PSE's status write.
- **Success Criteria numbers are proposed defaults** (Assumptions): 30 drills, 95%, 3 months, 2 minutes, 9 of 10, 2 seconds, and SC-012's at least one late-push drill. R5 set only spec 007's headline autonomy target (SC-004 there), and no answer covers this spec's numbers. Two targets come from the person: 200 ms p95 at 1 million chunks (data-model intake Q4), and 0 stale results (data-model intake Q17). Of SC-012's targets, only "0 ... merge" restates the person, and it rests on the intake's recorded reading of their answer "Both" ("so a commit from a stale epoch can never merge", project intake R7). The "100% ... record its own lease's epoch" target measures inferred design (spec 003 FR-039), and the "0 heads pushed" target measures FR-012's inferred rule.
- **Phase refinements R1-R8 (this round)**. Each answer was checked against the whole spec.
  - **R1 applied** ("One per role (Recommended)"): US1 now says the replacement is the PSE's one session and holds a new lease with a higher epoch (spec 001 FR-035, FR-037). The edge case, retitled "Two checkpoints for one lease" in this round's review, no longer reads as two dispatched PSE sessions: the second checkpoint comes from a stale session still running beside its replacement. The review narrowed it to two checkpoints from the same role for the same lease identity (the issue, or the issue and part). Under R2 with R1, Lead may hold another part's lease beside the PSE (spec 001 FR-035), and Review checkpoints the same issue; both are expected, not a conflict. The R1 round's US1 and FR-012 text also said, without condition, that a replacement holds a new, higher-epoch lease. It now holds one only outside Shadow mode, and only when it replaces a session that held a write lease, so the Shadow-mode repeat of US1's test and the Review replacement of US1 AS-7 no longer conflict with it. The Assumptions scale line now reads the 3 sessions as one per role; reading 10 agents as 3 + 6 + Jev stays inferred. Its sentence "No requirement here assumes two sessions of one role at once" contradicted the stale session the edge case describes. It now says "two dispatched sessions" and points to the edge case and FR-012. Dependencies list 001 FR-035 and FR-037. No other text assumed two sessions of one role at once: US2 AS-6 is about subagents (2 per role, 6 in all), US6's "two agent sessions" are sequential, and a planning Lead covering several issues is not building them.
  - **R2 applied** (touched FR-011 only): the Lead write lease FR-011 mentions is now held under a grant the owner approves for each issue (spec 003 FR-010). Spec 005 decides nothing about the grant. Its review found that the grant clause followed both lease holders, so it could be read as requiring a grant for PSE work too. FR-011 now attaches the grant to Lead only, as R2 and spec 003 FR-010 do.
  - **R3 checked, no change**: FR-028, US1 AS-4 and SC-011 still hold. Spec 007 FR-002's one Shadow-mode exception is a bridge plan a person approves, which the gateway then writes. A session's stop recommendation is not part of a bridge plan, and the session itself still never writes in Shadow mode.
  - **R4 not applicable**: this spec requires no issue search or milestone lookup. It does read more than the session's own issue: FR-004 indexes "relevant Gitea issues and comments", and FR-019 has a planning Lead fetch each issue it covers. How the index finds the issues it ingests is left to spec 009 and planning.
  - **R5 not applicable**: see the bullet above.
  - **R6 not applicable**: this spec supplies the durable-progress signals (FR-029) but names no spinning window. Spec 008 owns the 60-minute window.
  - **R7 applied**: FR-012 (new paragraph and three inferred bullets), FR-019 (commits record the lease's epoch), US1 AS-8, the "Two checkpoints" edge case, a new Non-goal (this spec neither judges nor posts `lease-epoch`), SC-012, Dependencies (001 FR-038) and Art. VI in the constitution list. The two fences are the person's; the rest is marked inferred or cited to spec 001 FR-038, spec 002 FR-038 and spec 003 FR-039, where the design lives. No text here called the forge-side fence an open question, and none does now: the FR-012 marker added in the review asks only how a late-push commit leaves the branch, not where the fence lives. The review found three more gaps in this round's R7 text and fixed them (see the first note, the inferred list and "Review of the R1-R8 round" below): FR-012's late-push rule was conditional; FR-019, AS-8 and the edge case cited R7 for inferred design; and AS-8 assumed an open pull request and a mode that grants leases.
  - **R8 not applicable**: this spec names no `jev/*` label and gives Jev no write. "Labelled" in FR-017 and US3 means debug artifacts, not Gitea labels.
  - Clarifications gained the R1, R2 and R7 rows, copied from the Phase Refinements table.
- **Review of the R1-R8 round (fixes applied)**:
  - FR-012, FR-032, US1 AS-8, the edge case, SC-012: the late-push rule is now absolute, the check runs again before each push and after a rejected push, and one marker holds the person's choice of how the stale commit leaves the branch (first note).
  - FR-019, US1 AS-8, the edge case, Assumptions, SC-012: the commit-records-epoch and control-plane-posts clauses are marked (inferred). R7 is cited for the two fences only.
  - FR-011, FR-012, FR-019, Key Entities, Dependencies: a partitioned issue's checkpoint records the part, and FR-012 compares the epoch with that issue's or part's current epoch (spec 001 FR-032).
  - FR-011: the owner's per-issue grant now attaches to Lead only (R2).
  - US1, FR-012, US1 AS-8, SC-012: the higher-epoch lease and the `lease-epoch` status are scoped to modes that grant leases, to replacements of a session that held one, and, in AS-8 and SC-012, to an open pull request. SC-012's drills run in Agent implementation mode with `lease-epoch` made a required check by a person (Art. VI).
  - Key Entities, Assumptions: the new lifecycle point (FR-032) is listed.
  - Dependencies: the commit-epoch duty is spec 003's (003 FR-039), so AS-8's commit half and SC-012's own-epoch target are checked only once 003 is built. That is not a build edge, and 003 stays downstream as the fixed map requires.
  - Assumptions: the proposed-defaults bullet no longer cites row S9 as the reason (its open item is resolved by R5, which covers only spec 007), lists the late-push drill as a proposed default, and says which SC-012 target rests on the intake's reading of R7.
  - The `lease-epoch` status context name is a new interface detail shared with specs 001, 002 and 003. Like the other named interfaces above, it keeps "No implementation details" unticked and does not block planning.
- **Dependencies** now match the fixed dependency map. Upstream: 001 and 009. Downstream: 003 and 008. Checkpoint and trace formats come from 009, so 001's recovery assessment reads them without a 001↔005 cycle.
- **Outside this task's files** (for the specs' owners):
  - Spec 003 FR-023 cites "spec 005 lifecycle hooks". The section is now titled "Lifecycle points (the report's lifecycle hooks)", so the reference still resolves.
  - Spec 001 FR-038 judges only the head, and its second marker asks what happens to a stale-epoch commit that lands after a re-dispatch. Spec 005 FR-012 now bars the replacement, without condition, from building on such a commit or pushing a head that contains it (inferred). FR-012's marker asks the person the same question as spec 001 FR-038's second marker: how the stale commit leaves the branch. One answer settles both. Until then, SC-012's "0 ... merge" depends on that answer as well as on this spec. A recovery assessment that resumes the issue after the stale commit has landed would record a base commit beneath it. That case belongs to spec 001's recovery assessment, which lists the commit (spec 001 FR-017, FR-038).
  - Resolved: spec 008 FR-029 step 5 and its overview now state both fences (R7).
  - Spec 008 FR-010 says the command log "holds one line per tool call, written after each tool use (spec 005 FR-027)". Spec 005 FR-027 and the hook as built (`.claude/hooks/command_log.py`, PreToolUse and PostToolUse/PostToolUseFailure) write a start line and an end line per call, and FR-010's own last bullet needs the start line. The second-review note above said spec 008 FR-010 already keeps both lines; only its last bullet does.
  - The earlier bullets saying `specs/README.md` was stale were removed: the README now shows 005 as depending on 001 and 009 and unblocking 003 and 008, attributes the checkpoint and trace schemas to 009, and no longer cites Python 3.12+ or `claude-opus-5-5`.
- Before `/speckit-plan`, the FR-012 marker should go to the person (`/speckit-clarify` or `/speckit-intake-refine`), together with spec 001 FR-038's second marker, which asks the same question. The unticked "non-technical stakeholders" and implementation-detail items are explained above and do not block.
