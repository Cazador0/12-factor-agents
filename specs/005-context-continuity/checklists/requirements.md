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

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [ ] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

- **"Requirements are testable and unambiguous" is ticked again only after these fixes.** The previous version ticked it while the spec held undefined terms and a self-contradicting FR-008. The fixes:
  - **FR-008 (stale)**: the old rule ("not an ancestor of its head") would have served the old ADR chunk that the spec's own US4 test expects to be rejected. Stale now means (a) the indexed commit is unreachable from the head, (b) the chunk's unit changed between the indexed commit and the head, or (c), added in the second review pass, a Gitea text's version changed or the text was deleted. US4 AS-2, AS-3, AS-6 and SC-003 use the same definition.
  - **FR-011 ("long-running session")**: now "every role session", matching Art. I, spec 003 FR-024 and this spec's own FR-023.
  - **FR-014 ("consequential step")**: now an enumerated list. SC-004, US2 AS-1 and the US2 Independent Test all use that term.
  - **FR-015 ("hidden model reasoning")**: now defined by provider-marked reasoning output plus the schema allowlist, with fixtures (SC-005).
  - **FR-016 ("production run")**: dropped. Chains are now off for every run.
  - **SC-001 ("same final state")**: replaced by outcome equivalence, since model-driven runs are nondeterministic.
  - **FR-003**: now has a proposed length default.
- **No markers.** The open items carried from the intakes are planning items, not choices still waiting on the person, so they appear as Assumptions:
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
  | FR-011, FR-012 | US1 AS-1, AS-2, AS-5, AS-7, SC-001 |
  | FR-013 | US1 AS-3, Edge Cases (missing trace) |
  | FR-014 | US2 AS-1, AS-2, SC-004 |
  | FR-015 | US2 AS-3, SC-005 |
  | FR-016, FR-017 | US3 |
  | FR-018 | US2 AS-4, Edge Cases (secrets), SC-005, SC-009 |
  | FR-019 | US1 AS-1, US6 AS-1 |
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
  - Edge Cases: entries for commits made by people, pushes by others, and death after a push.
  - Assumptions: the drill mode, the 150-line `AGENTS.md` limit, the chain step fields, the reading of Q10, and 10 agents = 3 sessions + 6 subagents + Jev.
- **Second review pass (fixes applied)**:
  - Command log (FR-027, SC-009, US2 AS-4, Key Entities, Assumptions, Dependencies): 005 said one entry per command, holding the command text, in `commands.jsonl`. Spec 008 FR-010 and the hook as built keep a start and an end line per tool call, with fingerprints only, in `.specify/sessions/commands/<session_id>.jsonl`. FR-027 now follows 008 and the hook, keeps the decision record's `{command, exit_code, at}` as the core of each end line, and marks every other field (inferred).
  - Non-git provenance (FR-006, FR-008 (c), SC-003, US4 AS-6, Edge Cases): Gitea text has no commit, and FR-008 (a) and (b) could not see an edit made in Gitea, so SC-003 could not be verified for those sources.
  - Checkpoints for Review and planning Lead sessions (FR-011, FR-012, FR-019, Key Entities, US1 AS-7, Edge Cases): branch, head commit and lease epoch are now required only where the session holds them, matching FR-020.
  - Compaction (US1, US1 AS-6, FR-023, FR-031, SC-001): compaction is now a self-resume by the same session, with no recovery assessment, matching project intake Q17 and spec 001 FR-017. It was counted as a disappearance before.
  - FR-024 now states data-model intake Q9 as given: the owning role changes a record and everyone in the tenant reads it.
  - Evidence (FR-011, Dependencies Art. IV): "not applicable" with its reason is now a third evidence state, as Art. IV requires.
  - FR-023: step 3 escalates only after a self-judged stuck stop (spec 003 FR-036), names the recipient, and leaves the escalation after a Jev-requested stop to Jev (spec 008 FR-029, FR-032). The lease release moved to the last step, because spec 003 FR-036 posts the escalation while the session still holds its lease and spec 002 FR-007 requires the lease for a PSE's status write.
- **Success Criteria numbers are proposed defaults** (Assumptions; project intake row S9 is still Partial): 30 drills, 95%, 3 months, 2 minutes, 9 of 10, and 2 seconds. Two targets come from the person: 200 ms p95 at 1 million chunks (data-model intake Q4), and 0 stale results (data-model intake Q17).
- **Dependencies** now match the fixed dependency map. Upstream: 001 and 009. Downstream: 003 and 008. Checkpoint and trace formats come from 009, so 001's recovery assessment reads them without a 001↔005 cycle.
- **Outside this task's files** (for the specs' owners):
  - Spec 003 FR-023 cites "spec 005 lifecycle hooks". The section is now titled "Lifecycle points (the report's lifecycle hooks)", so the reference still resolves.
  - The earlier bullets saying `specs/README.md` was stale were removed: the README now shows 005 as depending on 001 and 009 and unblocking 003 and 008, attributes the checkpoint and trace schemas to 009, and no longer cites Python 3.12+ or `claude-opus-5-5`.
- `/speckit-plan` can proceed. The unticked "non-technical stakeholders" and implementation-detail items are explained above and do not block.
