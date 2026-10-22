# Feature Specification: Spec Kit to Gitea Bridge

**Feature Branch**: `004-speckit-gitea-bridge`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Gitea integration for Spec Kit, and the definition of a complete specification" (research report: *Spec Kit and specification-driven delivery* → *Definition of "complete specification"* and *Gitea integration for Spec Kit*)

## Clarifications

### Session 2026-10-22

- Q: The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target? → A: Gitea only
- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service
- Q: The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work? → A: Both
- Q: How far should the dependent specs go in this first pass? → A: Constitution plus full spec set

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn a feature's task list into a Gitea issue graph without duplicates (Priority: P1)

The Lead has a feature whose `tasks.md` is clean under analysis. It runs the bridge's tasks-to-issues command (`/speckit-gitea-taskstoissues` in Claude Code, `speckit.gitea.taskstoissues` elsewhere). The bridge reads every task ID and dependency marker, looks up each task in Gitea before doing anything, creates only the issues that are missing, links each issue to the tasks it is blocked by, places it on the project board, and writes the mapping back to a committed `task-issue-map.yaml` in the feature folder. Running it a second time changes nothing.

**Why this priority**: This is the deterministic bridge from specification to execution. Without it the Lead hand-copies tasks into Gitea, and every repeated agent run risks duplicate issues, which is the failure the report names first.

**Independent Test**: Run the command against a sample feature with 6 tasks and 3 dependency markers on a scratch Gitea repository, then run it again. The first run creates 6 issues and 3 dependency links and writes the mapping; the second run creates nothing and reports "0 created, 6 matched".

**Acceptance Scenarios**:

1. **Given** a feature whose `tasks.md` holds tasks T031, T032 and T034, where T032 and T034 depend on T031, and no matching Gitea issues exist, **When** the Lead runs the tasks-to-issues command, **Then** three issues are created, T032's and T034's issues are recorded as blocked by T031's issue, all three sit in the board's Backlog column, and `task-issue-map.yaml` lists each task ID with its issue number and `blocked_by` list.
2. **Given** the same feature after a successful run, **When** the command runs again, **Then** no issue is created, no dependency link is duplicated, and the mapping file is byte-for-byte unchanged.
3. **Given** a feature where T031 already has an issue that was created by hand and carries the task ID marker, **When** the command runs, **Then** the existing issue is adopted into the mapping instead of a second one being created.
4. **Given** a run that fails after creating two of five issues, **When** the command runs again, **Then** it creates only the three missing issues and the final mapping holds all five.

---

### User Story 2 - Gate "Ready for Build" on a complete, traceable specification (Priority: P1)

Before any issue of a feature may move to Ready for Build, the bridge checks the feature against the completeness contract: product intent, user stories, functional and non-functional requirements, acceptance criteria, explicit non-goals, contracts where relevant, error and failure semantics, authorization and security requirements, observability, performance targets where relevant, migration and compatibility where relevant, an architecture plan, a dependency map, the task DAG, a reviewer checklist, no unresolved critical clarification, a clean analysis report, and traceability from every requirement to at least one task and one expected verification. Each missing element is reported by name and location. A feature that fails stays out of Ready for Build.

**Why this priority**: The report replaces "complete 100 percent of the documentation" with a verifiable contract. Without the gate, PSE sessions start from guesses, which Article V (Specification Before Build) forbids.

**Independent Test**: Run the traceability check on a fixture feature with one requirement that no task covers and one task with no expected verification. It fails with exactly those two findings. Fix both, rerun, and it passes.

**Acceptance Scenarios**:

1. **Given** a feature where FR-007 is referenced by no task, **When** the check runs, **Then** it fails and names FR-007 as untraced, citing the spec file and line.
2. **Given** a feature whose spec still holds an open clarification marker tagged critical, **When** the check runs, **Then** it fails and names the marker, and no issue of that feature can be moved to Ready for Build.
3. **Given** a feature that satisfies every element of the contract, **When** the check runs, **Then** it passes and records a machine-readable result that the control plane (spec 001) reads before allowing the Ready for Build transition.
4. **Given** a feature where an element is not applicable (for example, no data migration), **When** the spec states that explicitly, **Then** the check accepts it; **When** the element is simply absent, **Then** the check fails. An absent element is never treated as N/A.

---

### User Story 3 - Detect drift between the spec and the issue board without rewriting either (Priority: P2)

Work moves on. Tasks get renamed, split or removed in `tasks.md`; issues get closed, edited or created by hand in Gitea. The Lead runs the sync command (`/speckit-gitea-sync`). It compares every mapped task with its issue and every open issue carrying a task marker with the task list, then writes a drift report: issues with no task, tasks with no issue, dependency links that no longer match, closed issues whose task is still open in the spec, and mapping entries pointing at deleted issues. It changes nothing on its own.

**Why this priority**: Drift is inevitable over a long horizon. The report is explicit that drift must be reported rather than silently fixed, because silently rewriting the spec would let execution state overrule the source of truth (Article I).

**Independent Test**: On a synced fixture, delete one task from `tasks.md`, close one issue by hand and add one dependency link in Gitea. Run sync. The report lists exactly those three drifts, and `git status` shows no change to `tasks.md`, `spec.md` or the mapping.

**Acceptance Scenarios**:

1. **Given** a mapped task that was removed from `tasks.md`, **When** sync runs, **Then** the report lists its issue as "orphaned issue" and the issue is neither closed nor edited.
2. **Given** an issue closed in Gitea while its task is still unchecked in `tasks.md`, **When** sync runs, **Then** the report lists the pair as "state mismatch" and leaves both untouched.
3. **Given** no drift, **When** sync runs, **Then** the report says "no drift" and the command exits successfully.

---

### User Story 4 - Carry labels, milestone and assignee class onto each issue (Priority: P3)

Each created issue carries labels derived from the task (user story, phase, parallelizable marker, risk class), the feature's milestone, and an assignee class (Lead, PSE or Review) rather than a named session. It also carries a body that lets any agent rebuild its contract without a transcript: intent, spec and story reference, task IDs, acceptance criteria, non-goals, dependencies, risk, required verification and ownership.

**Why this priority**: These fields let the scheduler (spec 001) and the role agents (spec 003) act on issues mechanically. They are valuable but not blocking: issues without them can still be scheduled by hand.

**Independent Test**: Create issues for a fixture feature and read one back through the API. The labels, milestone, assignee class and every section of the issue body template are present.

**Acceptance Scenarios**:

1. **Given** a task marked `[P]` under User Story 2 in a medium-risk feature, **When** its issue is created, **Then** it carries labels for the story, the parallelizable marker and `risk:medium`, plus the feature's milestone.
2. **Given** any created issue, **When** a fresh session reads only that issue, **Then** it finds the intent, the spec reference, the task IDs, the acceptance criteria, the dependencies and the required verification without opening a chat transcript.

---

### Edge Cases

- A task ID appears twice in `tasks.md`. The command stops before creating anything and reports both lines; it never guesses which one is real.
- A dependency marker names a task ID that does not exist. The command reports the dangling reference and creates no dependency link for it; the other issues are still created.
- The dependency markers form a cycle. The command reports the cycle with every task in it and creates no dependency links for the cycle members, because a cyclic DAG can never unblock.
- Gitea returns a transient error midway through a run. Already-created issues are recorded in the mapping before the command exits with an error, so the next run resumes without duplicates.
- Someone edits `task-issue-map.yaml` by hand so that two tasks point at the same issue. Sync reports the collision; tasks-to-issues refuses to run until it is resolved.
- The feature folder has no `tasks.md` yet. Both commands stop with a message naming the missing file and the phase that produces it (`/speckit.tasks`).
- A task is split into two tasks after its issue exists. Sync reports one mapped task as missing and one new task as unmapped; it does not move the old issue to either.
- The caller's role lacks issue-creation authority in the gateway (spec 002). The command stops before any write and names the missing permission.

## Requirements *(mandatory)*

### Functional Requirements

**Tasks to issues**

- **FR-001**: The bridge MUST provide a tasks-to-issues command invocable as `/speckit-gitea-taskstoissues` in Claude Code and as `speckit.gitea.taskstoissues` in other Spec Kit integrations, scoped to one feature folder at a time.
- **FR-002**: The command MUST parse every task ID, its user-story tag, its parallelizable marker and its dependency markers from `specs/<feature>/tasks.md`, and MUST validate the set (unique IDs, no dangling references, no cycles) before any write.
- **FR-003**: For each task, the command MUST look up an existing Gitea issue by its task ID marker before creating one, and MUST create an issue only when none exists.
- **FR-004**: The command MUST set labels (story, parallelizable, risk class), the feature milestone and an assignee class on each created issue, and MUST fill the issue body from the issue contract template (intent, spec, tasks, acceptance criteria, non-goals, dependencies, risk, required verification, ownership, current PR).
- **FR-005**: The command MUST create a Gitea dependency link for every dependency marker whose both ends are mapped, and MUST NOT create a link that already exists.
- **FR-006**: The command MUST place every created issue in the project board's Backlog column. It MUST NOT move an issue to any later column; later transitions belong to the control plane (spec 001).
- **FR-007**: The command MUST write the mapping to `specs/<feature>/task-issue-map.yaml` with, per task, the issue number and its `blocked_by` task IDs, in a stable sort order so that an unchanged run produces an identical file.
- **FR-008**: The command MUST record each issue in the mapping as soon as it is created, so an interrupted run never loses track of an issue it made.
- **FR-009**: Every Gitea write MUST go through the semantic gateway (spec 002) with an idempotency key derived from the feature, the task ID and the operation, so a retried write cannot create a second issue.
- **FR-010**: Re-running the command on an unchanged feature MUST perform zero Gitea writes and leave the mapping unchanged.

**Drift detection**

- **FR-011**: The bridge MUST provide a sync command invocable as `/speckit-gitea-sync` (or `speckit.gitea.sync`) that compares the mapping, `tasks.md` and the issues carrying the feature's task markers.
- **FR-012**: The sync command MUST report at least these drift kinds: orphaned issue, unmapped task, dangling mapping entry, dependency mismatch, state mismatch, and mapping collision.
- **FR-013**: The sync command MUST be read-only toward the spec, `tasks.md`, the mapping and Gitea. It MUST NOT rewrite any of them to resolve drift (Article I: The Repository Is the Memory).
- **FR-014**: The drift report MUST be machine-readable and human-readable, naming each drift with the task ID, issue number and file location involved.

**Completeness and traceability gate**

- **FR-015**: The bridge MUST provide a completeness check that evaluates a feature against every element of the completeness contract listed in User Story 2, and MUST report each missing element by name and file location.
- **FR-016**: The check MUST verify traceability: every functional and non-functional requirement maps to at least one task, and every task maps to at least one expected verification (a named test, check or review step).
- **FR-017**: The check MUST fail while the spec holds an unresolved critical clarification marker, or while the latest analysis report has a CRITICAL finding.
- **FR-018**: The check MUST accept an element marked explicitly not applicable with a reason, and MUST fail on an element that is merely absent ("not stated" is never "not applicable"; Article IV: Evidence Over Assertion).
- **FR-019**: The check MUST write a machine-readable result per feature that the control plane (spec 001) reads before it allows any of the feature's issues into Ready for Build (Article V: Specification Before Build).
- **FR-020**: The check MUST be runnable in CI as a linter with a non-zero exit on failure, so a pull request that breaks traceability is blocked mechanically (Article VIII: Mistakes Become Mechanisms).

**Authority**

- **FR-021**: Only the Lead role MAY run tasks-to-issues against a live Gitea repository; any role MAY run sync and the completeness check (Article II: Separated Authority).
- **FR-022**: Both commands MUST support a dry-run mode that prints the planned writes without performing any.

### Key Entities

- **Task**: one line of `tasks.md`; identified by its task ID (T###); carries a user-story tag, an optional parallelizable marker, a description and zero or more dependencies on other tasks.
- **Issue contract**: the structured body of a Gitea issue; sections for intent, spec reference, task IDs, acceptance criteria, non-goals, dependencies, risk, required verification, ownership and current PR. Lets a fresh session rebuild the work's contract.
- **Task-issue map**: the committed `task-issue-map.yaml` per feature; maps each task ID to one issue number and its `blocked_by` task IDs. The only link between the spec's IDs and Gitea's numbers.
- **Drift finding**: one mismatch between the map, `tasks.md` and Gitea; has a kind, the task ID and issue number involved, the evidence and a suggested owner.
- **Completeness result**: the per-feature outcome of the completeness check; lists each contract element with pass, fail or not-applicable-with-reason, plus the traceability matrix (requirement → tasks → verifications).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across 50 consecutive re-runs of tasks-to-issues on unchanged features, zero duplicate issues and zero duplicate dependency links are created.
- **SC-002**: A run interrupted at any point and then re-run ends with exactly one issue per task in 100% of fault-injection trials (at least 20 trials covering every write step).
- **SC-003**: The Lead turns a 40-task feature into a fully linked issue graph in under 5 minutes of wall-clock time, against a baseline of manual entry.
- **SC-004**: In the first 3 months of use, 100% of issues that reach Ready for Build belong to a feature whose completeness result passed at that commit.
- **SC-005**: Seeded drift fixtures (at least one per drift kind) are detected by sync with 100% recall and no false positives on a drift-free fixture.
- **SC-006**: The metric "requirements changed after implementation began" (spec 007 scorecard) falls by at least 30% within 3 months of the gate being enforced, compared with the first month of shadow mode.

## Assumptions

- Gitea 28.x is the forge, and its API exposes issue dependencies, project columns and milestones as the report describes (user decision: Gitea only).
- All Gitea writes travel through the semantic gateway of spec 002; the bridge never holds a raw administrator token.
- Task IDs and dependency markers follow Spec Kit's current `tasks.md` conventions; the bridge reads them, it does not define them.
- Each issue carries a hidden, machine-readable marker naming its feature and task ID, so lookup by task ID is exact rather than a title search.
- The completeness check's applicability rules ("where relevant") are decided per feature in the spec itself and are not inferred by the tool.
- Implementation language is assumed to be Python 3.12+ (unconfirmed; the language question went unanswered).
- The core `taskstoissues` command and the GitHub issues extension stay unused in this repository; they are GitHub-specific and the forge is Gitea.

## Dependencies

- **Upstream**: 001-engineering-control-plane (board columns, Ready for Build transition, reading the completeness result); 002-gitea-mcp-gateway (every Gitea read and write, idempotency keys, role authority).
- **Downstream**: 003-role-agent-contracts (Lead runs the bridge; PSE and Review read issue contracts); 006-quality-evidence-gates (requirements traceability is an input to the merge evidence gate); 007-progressive-autonomy (long-horizon mode depends on the Lead populating Gitea autonomously through this bridge).
- **Constitution**: Article I (The Repository Is the Memory), Article II (Separated Authority), Article IV (Evidence Over Assertion), Article V (Specification Before Build), Article VIII (Mistakes Become Mechanisms).
