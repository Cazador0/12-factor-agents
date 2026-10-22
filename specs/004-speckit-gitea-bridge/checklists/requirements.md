# Specification Quality Checklist: Spec Kit to Gitea Bridge

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Updated**: 2026-10-22 (refinement: verified review findings, project intake Q6–Q22, data-model intake Q8, Q14, Q20 and Q26, fixed dependency map)
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs). Deliberate exceptions are listed in Notes.
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
- [x] No implementation details leak into specification. Deliberate exceptions are listed in Notes.

## Notes

### Markers (2 open)

Both markers are the person's to answer. Resolve them with `/speckit-clarify` or `/speckit-intake-refine` before `/speckit-plan`.

- **FR-023, how a person applies the plan in Shadow mode.** The bridge writes live only when the mode lets the Lead populate Gitea, which spec 007 grants first in Long-horizon mode (FR-005). Until then a person applies the plan. The options are:
  - (a) the person creates the issues by hand and the Lead then confirms them into the mapping;
  - (b) the gateway carries out a plan the person approved, which changes spec 002 FR-024 and spec 007 FR-002;
  - (c) the person runs the plan under their own Gitea account, outside the gateway.
- **FR-024, widening the gateway with read-only issue search and milestone lookup.** Spec 002 FR-001 is a closed tool list with no search. Adding a tool is a Critical-risk change that needs human approval (spec 002 FR-003; Art. VI). Without it, the bridge cannot find issues it did not record. That rules out adoption of hand-made issues (FR-025) and stops sync from seeing identifier-bearing issues that are off the board (FR-011).

### Unticked items and why

- **"No [NEEDS CLARIFICATION] markers remain"**: two remain (FR-023, FR-024).
- **"Requirements are testable and unambiguous"**: this was ticked before, but it was not true. FR-016 required traceability that `tasks.md` cannot carry, FR-017 relied on a "critical" tag the marker syntax does not have, and the risk class in FR-004 had no source. All three are now fixed:
  - FR-016 sets a traceability convention, which is inferred.
  - FR-017 treats every open marker as blocking and requires a committed analysis report.
  - FR-004 takes the risk class from the Lead's declaration.

  The item stays unticked only because FR-003, FR-011, FR-023 and FR-025 depend on the two open answers.
- **"All functional requirements have clear acceptance criteria"**: FR-023 and FR-024 cannot have a final acceptance criterion until they are answered. Every other requirement has at least one scenario, edge case or success criterion:

  | Requirements | Covered by |
  |---|---|
  | FR-002 | Edge Cases 1–3 |
  | FR-004 | US4 AS-1 and AS-3 |
  | FR-008 | US1 AS-4 and AS-6, SC-002 |
  | FR-017 | US2 AS-2 |
  | FR-019 | US2 AS-3 and AS-5, SC-004 |
  | FR-025 | US1 AS-3, SC-009 |
  | FR-026 | Edge Case on the deleted issue |
  | FR-027 | US1 AS-7 |
  | FR-028 | US2 AS-7 |
  | FR-029 | US2 AS-6 |
  | FR-030 | Edge Case on issue text, SC-009 |
  | FR-031 | SC-010 |
  | FR-032 | US1 AS-2 |
  | FR-033 | Edge Cases |
  | FR-034 | Edge Case on the unknown format version |
  | FR-035 | Edge Case on missing labels and milestones |
- **"Feature meets measurable outcomes defined in Success Criteria"**: SC-005 includes the "unconfirmed issue" drift kind, and SC-009 covers adoption. Both depend on the issue search that FR-024 asks the person to approve. This item cannot be confirmed until that answer is in.
- **"Written for non-technical stakeholders"**: this was ticked before, but it is not true. The readers are the engineering owner and the role agents. The requirements use terms that the constitution and report fix: idempotency key, mutation envelope, task DAG, autonomy mode. The user stories stay in plain language. This item does not block planning.

### Previous note corrected

The previous note said "the report settles every behavior". That was wrong: the ledger found 40 of 47 decisions unbacked. The following are now marked "(inferred)" in the spec and should go back to the person through `/speckit-intake-refine`:

- the hidden-marker identifier, now left to the plan (Assumptions);
- one issue per task (FR-003);
- the issue-body sources (FR-004);
- the risk-class source (FR-004);
- stopping the whole run on a dangling reference or cycle (FR-002);
- the idempotency key's parts and the generation counter (FR-009, FR-026);
- the map's route through protected `main` (FR-027);
- the traceability convention on task lines (FR-016);
- every open marker blocking (FR-017);
- the committed analysis report (FR-017);
- a CI-produced result being the only one that counts (FR-019);
- Review attribution (FR-029);
- adoption only of issues the Lead's bot account wrote (FR-025);
- Jev may run sync and the check (FR-021);
- the run report feeding the Lead's decision trace (FR-031);
- format versions (FR-034);
- human-owned milestones (FR-035);
- the Python reading of the stack answer (Assumptions).

The Backlog entry column is no longer the spec's own decision. It now comes from spec 001 (FR-006). Dry-run is kept, and in Shadow mode it is the bridge's only path (FR-022, FR-023).

### Deliberate exceptions to "no implementation details"

- **Gitea 28.x and the LangGraph service**: fixed by the person (project intake Q1, Q2).
- **`tasks.md`, `task-issue-map.yaml` and the report's command concepts** (`speckit-gitea-taskstoissues`, `speckit-gitea-sync`): named by the report. They are interfaces the feature must honor.
- **Command invocation**: FR-001 and FR-011 no longer hard-code Claude Code's slash syntax. The owner chose the LangGraph service, and the report warns against "hard-coding `/speckit-*` into the architecture". Syntax for each integration is left to the plan. With this change, "No implementation details" and "No implementation details leak" were validated again and stay ticked.
- **Stack and host**: the OCaml, Rust and Python split (project intake Q6, Q10), the MacBook Pro M4 Pro with about 18 GB usable (data-model intake Q14; project intake Q22), and Claude and Ollama (project intake Q7) appear only in Assumptions or as constraints. The earlier "Python 3.12+ (unconfirmed)" assumption is replaced by the stack answer.
- **SC-003**: it names the MacBook host because the person fixed the host. It does not name a technology choice of the spec's own.

### Success criteria

- The numbers in SC-001 to SC-005 are proposed defaults, not confirmed (Assumptions; project intake row S9 is still open). SC-003 no longer cites an unmeasured "baseline of manual entry".
- SC-006 is withdrawn. "Requirements changed after implementation began" belongs to spec 007's scorecard, and 004 has no downstream edge to 007.
- SC-007 to SC-010 are new. They cover Shadow-mode behavior, gate failures, injection resistance and run reports.

### Dependencies

The Dependencies section now matches the fixed dependency map: upstream 001 and 002, downstream none.

- The earlier Downstream entries (003, 006, 007) are relabelled as Related. The map has no such edges, 003 states there is no 003–004 edge, and 006 and 007 list 004 only as Related.
- The obligation on spec 001 to read the completeness result is now backed by spec 001: FR-029 and the TR-03 entry condition.
- The constitution citations add Articles III, VI and IX.

### Outside this task's files

- **Spec 002 FR-001** would need the read tools in FR-024 if the person approves them. That is a Critical-risk change under Art. VI.
- **`specs/README.md`** still shows the old index: no 008 or 009, and 001 with no upstream.
- **Specs 008 and 009** did not exist in `specs/` when this was written. References to them (stop rules, `git-history.md`) are forward references.
- **Constitution version**: `.specify/memory/constitution.md` still reads v1.0.0. The v1.1.0 amendment for Ollama (project intake Q14) has not been written to the file yet.
