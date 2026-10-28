# Specification Quality Checklist: Spec Kit to Gitea Bridge

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Updated**: 2026-10-22 (refinement: verified review findings, project intake Q6–Q22 and R1–R5 and R7, data-model intake Q8, Q14, Q20 and Q26, fixed dependency map)
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

  The person's R7 answer adds a second thing the answer must settle. Once a person makes `lease-epoch` a required check, the mapping's pull request needs a passing `lease-epoch` status. The control plane posts success only on an agent-branch head that records the current epoch of a write lease (spec 001 FR-038; spec 002 FR-038; who posts it and this rule are inferred there). In (a) and (b) the Lead commits under no write lease, so its commit records no epoch and could not merge unless the answer also gives the Lead a lease on that branch. In (c) the PSE session commits under its own lease, but only outside Shadow mode. With one session per role and at most one issue in build at a time (project intake R1; spec 001 FR-035), any write lease used for the mapping commit, whether Lead's or PSE's under (c), makes its issue the one issue in build. The mapping change then waits for, and holds, the single build slot (inferred). In Shadow mode, where the first release runs, no write lease is granted and no `lease-epoch` status is posted (spec 001 FR-030, FR-038). A person's plan approval never covers branch creation or lease grants (spec 007 FR-002), and PSE cannot open the pull request without a write lease (spec 002 FR-005). So in Shadow mode, under every option, the mapping's pull request cannot merge once the check is required, and the answer must cover Shadow mode too. This reading is inferred (FR-027). The Lead's implementation-worker mode is no shortcut: the owner approves it per issue (project intake R2). The marker's question is unchanged and still the person's.

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
  - FR-027's route to `main` is open, and so is how the mapping's pull request meets the required `lease-epoch` check, in Shadow mode as well as later modes (project intake R7).
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
- the Python reading of the stack answer (Assumptions);
- the Lead's mapping commit recording no lease epoch under FR-027 options (a) and (b), and so failing a required `lease-epoch` check (FR-027; project intake R7);
- the mapping's pull request failing a required `lease-epoch` check under every FR-027 option in Shadow mode, and any write lease used for the mapping commit taking the single build slot (FR-027; project intake R1, R7);
- concurrent runs coming chiefly from the one Lead session and its subagents, or from a stopped Lead session's in-flight run overlapping its replacement, and the one-issue-in-build limit not limiting Backlog creation (Edge Cases; Assumptions: Host and scale; project intake R1);
- the headline target of R5 not covering this spec's numbers (Assumptions: Success-criteria numbers).

The Backlog entry column is no longer the spec's own decision. It now comes from spec 001 (FR-006). Dry-run is kept, and in Shadow mode a person applies its plan by hand or approves it (FR-022, FR-023; project intake R3).

### Deliberate exceptions to "no implementation details"

- **Gitea 28.x and the LangGraph service**: fixed by the person (project intake Q1, Q2).
- **`tasks.md`, `task-issue-map.yaml` and the report's command concepts** (`speckit-gitea-taskstoissues`, `speckit-gitea-sync`): named by the report. They are interfaces the feature must honor.
- **Command invocation**: FR-001 and FR-011 no longer hard-code Claude Code's slash syntax. The owner chose the LangGraph service, and the report warns against "hard-coding `/speckit-*` into the architecture". Syntax for each integration is left to the plan. With this change, "No implementation details" and "No implementation details leak" were validated again and stay ticked.
- **Stack and host**: the OCaml, Rust and Python split (project intake Q6, Q10), the MacBook Pro M4 Pro with about 18 GB usable (data-model intake Q14; project intake Q22), and Claude and Ollama (project intake Q7) appear only in Assumptions or as constraints. The earlier "Python 3.12+ (unconfirmed)" assumption is replaced by the stack answer.
- **SC-003**: it names the MacBook host, Gitea, the LangGraph service, SQLite and local Ollama, because the person fixed all of them (project intake Q1, Q2, Q7, Q9, Q22). It names no technology choice of the spec's own. This is the exception the ticked "Success criteria are technology-agnostic" item points to.
- **FR-024**: names spec 002's existing board read (`gitea.project.get`) to show which capability is already there.

### Success criteria

- The numbers in SC-001 to SC-010 (SC-006 withdrawn) are proposed defaults, not confirmed (Assumptions). The intake's open item on a headline target is now resolved by R5, "+30% in 3 months (Recommended)", but that target is spec 007 SC-004's and sets none of this spec's numbers (inferred, as specs 001 and 002 read it). SC-003 no longer cites an unmeasured "baseline of manual entry".
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
- **Spec 001 FR-038 and spec 002 FR-038** post `lease-epoch` success only on an agent-branch head whose commit records the current epoch of a write lease, and failure on any other agent-branch head (fail closed). Their open marker asks only about pull requests from branches a person pushed. A Lead commit made under no write lease, such as the mapping commit under FR-027 options (a) and (b), is not covered, so once a person makes `lease-epoch` required such a pull request could not merge. In Shadow mode, where the first release runs, no write lease is granted and no `lease-epoch` status is posted, so the mapping's pull request could not merge under any option, (c) included (project intake R7; inferred).
- **Spec 007 FR-002**: corrected. The earlier note said it still had a human perform every consequential mutation in Shadow mode. It now names the human-approved bridge plan as the one exception (project intake R3; spec 002 FR-037), so nothing is outstanding there.

### Answers applied this round (project intake R1–R8)

- **R1** ("One per role (Recommended)"): applied. There is one Lead session, so the bridge runs in that session or in at most 2 of its subagents. The one-issue-in-build limit governs dispatch, not how many Backlog issues the bridge creates (inferred). Two concurrent runs are now explained chiefly as the Lead session and one of its subagents, or two of its subagents, and also as a stopped Lead session's in-flight run overlapping its replacement (inferred). FR-027 now says that any write lease used for the mapping commit takes the single build slot (inferred). US2's "PSE sessions" now reads "the PSE session" (Assumptions: Host and scale; Edge Cases).
- **R2** ("Owner, per issue (Recommended)"): this was applied in specs 003 and 001 in the last round, but this file's FR-027 still named the implementation-worker branch without the owner's per-issue approval. It now has it.
- **R3, R4**: still reflected correctly (FR-023, FR-024, US1 AS-8, Dependencies). Their Clarifications lines now use the exact "(project intake, R<n>)" form.
- **R5** ("+30% in 3 months (Recommended)"): applied to Assumptions (Success-criteria numbers). It sets spec 007's headline target, not this spec's numbers.
- **R6** (Jev's 60-minute window): not applicable. This spec names no window; session stopping is left to spec 008 (Assumptions: Session stopping).
- **R7** ("Both"): applied to FR-027 and Dependencies, where the mapping's pull request must also meet the required `lease-epoch` check. FR-027 now marks the status design as inferred, as specs 001 and 002 do, and says that in Shadow mode no option lets the mapping's pull request meet the check. The bridge posts no status and configures no branch protection (FR-020; Non-goals). This spec never said the forge-side fence was an open question, so there was no such wording to remove.
- **R8** (per-role `jev/` labels plus a summary label): not applicable. This spec names no `jev/` label, never creates label definitions (FR-035) and sets labels only on issues it creates (FR-004). It treats labels that others set as untrusted data (FR-030).
