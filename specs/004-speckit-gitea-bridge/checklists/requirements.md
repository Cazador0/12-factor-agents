# Specification Quality Checklist: Spec Kit to Gitea Bridge

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Updated**: 2026-10-22 (refinement: verified review findings, project intake Q6–Q22 and R3–R4, data-model intake Q8, Q14, Q20 and Q26, fixed dependency map)
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
- [x] Success criteria are technology-agnostic (no implementation details). Deliberate exceptions are listed in Notes.
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

### Markers (1 open)

The marker is the person's to answer, because it changes a role's authority (Art. VI). Resolve it with `/speckit-clarify` or `/speckit-intake-refine` before `/speckit-plan`.

- **FR-027, how the Lead's mapping commit reaches a branch and a pull request.** The mapping goes to `main` through protected `main` with at least one Review approval. No spec says how a Lead commit gets there: in spec 002 FR-005 only the control plane creates branches (at dispatch) and only PSE opens pull requests, and the Lead gets a branch only as an implementation worker (spec 003 FR-010). The same gap applies to every specification change the Lead writes. The options are:
  - (a) the control plane creates a specification branch and the Lead may open a pull request, which widens the Lead's row in spec 002 FR-005 (Critical risk);
  - (b) the Lead commits on a branch the control plane creates, and a person opens the pull request;
  - (c) a PSE session opens the pull request under a specification-change issue.

### Markers resolved

- **FR-023**: the person answered "Both Create issues by hand and Approve; gateway writes it" (project intake R3). In Shadow mode a person either creates the planned issues by hand, which the Lead then confirms into the mapping, or approves the plan so that the gateway carries it out as human-approved writes (spec 002 FR-037). The question named Shadow mode only. Applying the same two ways in Agent implementation and Guarded autonomous modes is inferred, as spec 002 FR-037 also reads it.
- **FR-024**: the person answered "Approve read-only search (Recommended)" (project intake R4). FR-024 now asks for issue search, milestone issue listing and milestone lookup. The board is no longer listed as missing, because spec 002 FR-001 already reads it.

### Unticked items and why

- **"No [NEEDS CLARIFICATION] markers remain"**: one remains (FR-027).
- **"Requirements are testable and unambiguous"**: this was ticked before, but it was not true. FR-016 required traceability that `tasks.md` cannot carry, FR-017 relied on a "critical" tag the marker syntax does not have, and the risk class in FR-004 had no source. All three are now fixed:
  - FR-016 sets a traceability convention, which is inferred.
  - FR-017 treats every open marker as blocking and requires a committed analysis report.
  - FR-004 takes the risk class from the Lead's declaration, recorded in the feature folder, with any per-task override on the task line (inferred).

  The item stays unticked for three reasons:
  - FR-027's route to `main` is open.
  - FR-019's CI-only rule and its binding to the plan, tasks and analysis commits have no enforcing gate: spec 001 FR-029 checks only the spec commit.
  - FR-006's placement in Backlog has no row in spec 001's transition table, and spec 002 does not let the Lead make it, so the gateway may refuse it.
- **"All functional requirements have clear acceptance criteria"**: FR-027 cannot have a final acceptance criterion until it is answered. FR-019's CI-only rule has a criterion (US2 AS-5, SC-004) that cannot pass until spec 001 FR-029 checks the producer. Every other requirement has at least one scenario, edge case or success criterion:

  | Requirements | Covered by |
  |---|---|
  | FR-002 | Edge Cases 1–3 |
  | FR-004 | US4 AS-1 and AS-3 |
  | FR-008 | US1 AS-4 and AS-6, Edge Case on the key conflict, SC-002 |
  | FR-017 | US2 AS-2 |
  | FR-019 | US2 AS-3 and AS-5, SC-004 |
  | FR-022, FR-023 | US1 AS-5 and AS-8, SC-007 |
  | FR-024 | US1 AS-3 and AS-6 |
  | FR-025 | US1 AS-3, SC-009 |
  | FR-026 | Edge Case on the deleted issue |
  | FR-027 | US1 AS-7 (reading the branch head only) |
  | FR-028 | US2 AS-7 |
  | FR-029 | US2 AS-6 |
  | FR-030 | Edge Case on issue text, SC-009 |
  | FR-031 | SC-010 |
  | FR-032 | US1 AS-2 |
  | FR-033 | Edge Cases |
  | FR-034 | Edge Case on the unknown format version |
  | FR-035 | Edge Case on missing labels and milestones |
- **"Feature meets measurable outcomes defined in Success Criteria"**: SC-004 cannot be met until spec 001 FR-029 checks the result's producer and the plan, tasks and analysis commits. The issue search that SC-005 and SC-009 rely on is now approved (project intake R4).
- **"Written for non-technical stakeholders"**: this was ticked before, but it is not true. The readers are the engineering owner and the role agents. The requirements use terms that the constitution and report fix: idempotency key, mutation envelope, task DAG, autonomy mode. The user stories stay in plain language. This item does not block planning.

### Previous note corrected

The previous note said "the report settles every behavior". That was wrong: the ledger found 40 of 47 decisions unbacked. The following are now marked "(inferred)" in the spec and should go back to the person through `/speckit-intake-refine`:

- the hidden-marker identifier, now left to the plan (Assumptions);
- one issue per task (FR-003);
- the issue-body sources (FR-004);
- the risk-class source, and where the declaration and per-task overrides are recorded (FR-004);
- stopping the whole run on a dangling reference or cycle (FR-002);
- the idempotency key's parts, including the dependency target and the generation, and the generation counter (FR-009, FR-026);
- the map's route through protected `main` (FR-027);
- the traceability convention on task lines (FR-016);
- every open marker blocking (FR-017);
- the committed analysis report (FR-017);
- a CI-produced result being the only one that counts (FR-019);
- Review attribution (FR-029);
- adoption only of issues the Lead's bot account wrote, and the Lead's confirmation recorded in the mapping (FR-025);
- the plan fingerprint and the bridge's own check against the approved plan (FR-022, FR-023);
- applying R3's two ways in Agent implementation and Guarded autonomous modes (FR-023);
- Jev may run sync and the check (FR-021);
- the run report feeding the Lead's decision trace (FR-031);
- the four command outcomes (FR-033);
- format versions, and the completeness result's schema belonging to spec 009 (FR-034);
- human-owned milestones (FR-035);
- the Python reading of the stack answer (Assumptions).

The Backlog entry column is no longer the spec's own decision. It now comes from spec 001 (FR-006). Dry-run is kept, and in Shadow mode a person applies its plan by hand or approves it (FR-022, FR-023; project intake R3).

### Deliberate exceptions to "no implementation details"

- **Gitea 28.x and the LangGraph service**: fixed by the person (project intake Q1, Q2).
- **`tasks.md`, `task-issue-map.yaml` and the report's command concepts** (`speckit-gitea-taskstoissues`, `speckit-gitea-sync`): named by the report. They are interfaces the feature must honor.
- **Command invocation**: FR-001 and FR-011 no longer hard-code Claude Code's slash syntax. The owner chose the LangGraph service, and the report warns against "hard-coding `/speckit-*` into the architecture". Syntax for each integration is left to the plan. With this change, "No implementation details" and "No implementation details leak" were validated again and stay ticked.
- **Stack and host**: the OCaml, Rust and Python split (project intake Q6, Q10), the MacBook Pro M4 Pro with about 18 GB usable (data-model intake Q14; project intake Q22), and Claude and Ollama (project intake Q7) appear only in Assumptions or as constraints. The earlier "Python 3.12+ (unconfirmed)" assumption is replaced by the stack answer.
- **SC-003**: it names the MacBook host, Gitea, the LangGraph service, SQLite and local Ollama, because the person fixed all of them (project intake Q1, Q2, Q7, Q9, Q22). It names no technology choice of the spec's own. This is the exception the ticked "Success criteria are technology-agnostic" item points to.
- **FR-024**: names spec 002's existing board read (`gitea.project.get`) to show which capability is already there.

### Success criteria

- The numbers in SC-001 to SC-005 are proposed defaults, not confirmed (Assumptions; project intake row S9 is still open). SC-003 no longer cites an unmeasured "baseline of manual entry".
- SC-006 is withdrawn. "Requirements changed after implementation began" belongs to spec 007's scorecard, and 004 has no downstream edge to 007.
- SC-007 to SC-010 are new. They cover Shadow-mode behavior, gate failures, injection resistance and run reports. SC-007 now excludes runs with a plan a person approved (project intake R3).

### Dependencies

The Dependencies section now matches the fixed dependency map: upstream 001 and 002, downstream none.

- The earlier Downstream entries (003, 006, 007) are relabelled as Related. The map has no such edges, 003 states there is no 003–004 edge, and 006 and 007 list 004 only as Related.
- The obligation on spec 001 to read the completeness result is only partly backed. Spec 001 FR-029 and the TR-03 entry condition refuse a missing or failed result and one from an older spec commit. They do not check the producer (CI only) or the commits of the plan, tasks and analysis report, which FR-019 requires. See "Outside this task's files".
- The constitution citations add Articles III, VI and IX.

### Outside this task's files

- **Spec 001 FR-029 and TR-03** need to check the completeness result's producer (CI only) and the commits of the plan, tasks and analysis report, not only the spec commit (FR-019). Until then, a passing result a session produced locally at the current spec commit satisfies the gate.
- **Spec 001's transition table and spec 002 FR-005** need an initial placement of a new issue in Backlog, or a statement that adding a new issue to Backlog is not a move. Spec 002's matrix must then allow it for the Lead. Today spec 001 FR-009 refuses every move not in the table, and the Lead's `gitea.project.move_issue` covers only TR-01 to TR-03 and Blocked (FR-006).
- **Specs 002 and 003** do not say how a commit the Lead writes, the mapping or any other specification change, reaches a branch and a pull request (FR-027 marker).
- **Spec 009 FR-002** does not list the completeness result among the shared record schemas. Spec 004 writes it and spec 001 reads it, so its schema, at least the fields spec 001 reads, belongs there (FR-034).
- **Spec 007 FR-002** still says a human performs every consequential mutation in Shadow mode. The intake records that R3 changes it, and spec 002 FR-037 already carries the human-approved plan write.
