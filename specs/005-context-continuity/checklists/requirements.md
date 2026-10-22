# Specification Quality Checklist: Context Engineering and Long-Horizon Continuity

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
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
- [x] No implementation details leak into specification

## Notes

- **"Requirements are testable and unambiguous" is ticked again only after these fixes.** The previous version ticked it while the spec held undefined terms and a self-contradicting FR-008. The fixes:
  - **FR-008 (stale)**: the old rule ("not an ancestor of its head") would have served the old ADR chunk that the spec's own US4 test expects to be rejected. Stale now means either (a) the indexed commit is unreachable from the head, or (b) the chunk's unit changed between the indexed commit and the head. US4 AS-2, AS-3 and SC-003 use the same definition.
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
- **Technology named because the person fixed it**:
  - SQLite with sqlite-vec plus the custom Python vector backend (project intake Q9; data-model intake Q7; FR-025);
  - Claude and Ollama (project intake Q7, Q14; FR-015 names their reasoning-output forms only to define what is never stored);
  - the MacBook Pro M4 Pro host (project intake Q22; data-model intake Q14; SC-007);
  - `git-history.md`, the person's own file name (data-model intake Q13, Q20, Q26).

  Two more names are interfaces shared with spec 008, fixed by the Jev design: `commands.jsonl` and its `{command, exit_code, at}` entry (Jev research report). The PostToolUse hook and the `.specify/traces/<run>/trace.jsonl` path appear only in Assumptions. On that basis, the "no implementation details" and "technology-agnostic" items stay ticked. The lexical method, the reranker, the embedding model and the language reading are all in Assumptions.
- **Every functional requirement has an acceptance criterion**:

  | Requirement | Acceptance criteria |
  |---|---|
  | FR-001 to FR-003 | US5, SC-006 |
  | FR-004 to FR-010 | US4 AS-1 to AS-4, SC-003, SC-007 |
  | FR-011, FR-012 | US1 AS-1, AS-2, AS-5, SC-001 |
  | FR-013 | US1 AS-3, Edge Cases (missing trace) |
  | FR-014 | US2 AS-1, AS-2, SC-004 |
  | FR-015 | US2 AS-3, SC-005 |
  | FR-016, FR-017 | US3 |
  | FR-018 | US2 AS-4, Edge Cases (secrets), SC-005 |
  | FR-019 | US1 AS-1, US6 AS-1 |
  | FR-020 | US2 AS-5, SC-002 |
  | FR-021 | US2 Independent Test |
  | FR-022 | Edge Cases (subagent checkpoints) |
  | FR-023 | US1 AS-4, AS-5, SC-011 |
  | FR-024 | SC-010 |
  | FR-025 | US4 AS-1, SC-007 |
  | FR-026 | US6, SC-008 |
  | FR-027 | US2 AS-4, SC-009 |
  | FR-028 | US1 AS-4, SC-011 |
  | FR-029 | US2 AS-4, SC-010 |
  | FR-030 | US4 AS-5 |

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
  - FR-023: the lease is renewed rather than released when the same session continues.
  - Edge Cases: entries for commits made by people, pushes by others, and death after a push.
  - Assumptions: the drill mode, the 150-line `AGENTS.md` limit, the chain step fields, the reading of Q10, and 10 agents = 3 sessions + 6 subagents + Jev.
- **Success Criteria numbers are proposed defaults** (Assumptions; project intake row S9 is still Partial): 30 drills, 95%, 3 months, 2 minutes, 9 of 10, and 2 seconds. Two targets come from the person: 200 ms p95 at 1 million chunks (data-model intake Q4), and 0 stale results (data-model intake Q17).
- **Dependencies** now match the fixed dependency map. Upstream: 001 and 009. Downstream: 003 and 008. Checkpoint and trace formats come from 009, so 001's recovery assessment reads them without a 001↔005 cycle.
- **Outside this task's files** (for the specs' owners):
  - `specs/README.md` still shows 005 as "Depends on: 001" and "Unblocks: 003", and still lists 005 as the definer of "Session checkpoint" and "Decision trace" in the shared vocabulary. 009 now owns those formats.
  - The README's open-items list still cites Python 3.12+, `claude-opus-5-5` and unresolved storage.
  - Spec 003 FR-023 cites "spec 005 lifecycle hooks". The section is now titled "Lifecycle points (the report's lifecycle hooks)", so the reference still resolves.
- `/speckit-plan` can proceed. The "non-technical stakeholders" item is explained above and does not block.
