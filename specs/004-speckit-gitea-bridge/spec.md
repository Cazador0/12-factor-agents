# Feature Specification: Spec Kit to Gitea Bridge

**Feature Branch**: `004-speckit-gitea-bridge`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Gitea integration for Spec Kit, and the definition of a complete specification" (research report: *Spec Kit and specification-driven delivery* → *Definition of "complete specification"* and *Gitea integration for Spec Kit*)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Turn a feature's task list into a Gitea issue graph without duplicates (Priority: P1)

The Lead has a feature whose `tasks.md` is clean under analysis. From the LangGraph service it invokes the bridge's tasks-to-issues command (the report's `speckit-gitea-taskstoissues`). The bridge reads every task ID and dependency marker, validates them and looks up each task in Gitea before it acts. When the active autonomy mode lets the Lead populate Gitea, the bridge then:

- creates only the issues that are missing, as the Lead's own Gitea bot account through the gateway;
- links each issue to the tasks that block it;
- places each new issue on the project board;
- writes the mapping to `task-issue-map.yaml` in the feature folder, which is then committed.

In every earlier mode the bridge prints the same plan and writes nothing on its own. A person applies the plan, either by creating the issues by hand or by approving the plan for the gateway to carry out (project intake R3, for Shadow mode; in the other modes before Long-horizon this is inferred, FR-023). A second run on an unchanged feature changes nothing.

**Why this priority**: This is the deterministic bridge from specification to execution. Without it the Lead copies tasks into Gitea by hand, and every repeated agent run risks duplicate issues, which is the first failure the report names. The first release runs in Shadow mode, where "humans perform consequential mutations" (report §Progressive autonomy; project intake D9). On day one the bridge therefore produces the plan, and a person either applies it by hand or approves it for the gateway to carry out (project intake R3).

**Independent Test**: Use a scratch Gitea repository whose fixture mode lets the Lead populate Gitea. Run the command against a sample feature with 6 tasks and 3 dependency markers, then run it again.

- The first run creates 6 issues and 3 dependency links and writes the mapping.
- The second run creates nothing and reports "0 created, 6 matched".
- With the fixture mode set to Shadow and no approved plan, a run on a fresh feature prints the full plan, names the mode and makes no Gitea write.

**Acceptance Scenarios**:

1. **Given** a feature whose `tasks.md` holds tasks T031, T032 and T034, where T032 and T034 depend on T031, no matching Gitea issues, and a mode that lets the Lead populate Gitea, **When** the Lead runs the tasks-to-issues command, **Then**:
   - three issues are created;
   - T032's and T034's issues are recorded as blocked by T031's issue;
   - all three sit in the board's entry column, Backlog (spec 001);
   - `task-issue-map.yaml` lists each task ID with its issue number and `blocked_by` list.
2. **Given** the same feature after a successful run, **When** the command runs again, **Then** no issue is created, no dependency link is duplicated, and the mapping file is byte-for-byte unchanged.
3. **Given** T031 already has an issue that carries T031's task identifier but was written by an account other than the Lead's bot account (for example, by hand), **When** the command runs, **Then**:
   - it creates no second issue for T031;
   - it reports the issue as an "unconfirmed issue";
   - it adds the issue to the mapping only after the Lead's confirmation is recorded (FR-025);
   - on adoption it reports every issue-contract section the body lacks (FR-025).
4. **Given** a run that fails after creating two of five issues, **When** the command runs again, **Then** it creates only the three missing issues and the final mapping holds all five.
5. **Given** Shadow mode, or no mode recorded, and no plan that a person approved, **When** the Lead runs the command, **Then** it performs no Gitea write. It prints the full plan of creations, links, labels and board placements, and names the mode that kept it from writing (FR-023).
6. **Given** an issue that the Lead's bot account created in an earlier run, that carries T032's identifier, and whose mapping entry was lost before it was committed, **When** the command runs again, **Then** the issue is adopted into the mapping without a second issue being created (FR-008, FR-025).
7. **Given** a run whose mapping is committed on a branch that has not yet merged into `main`, **When** tasks-to-issues or sync runs again for that feature, **Then** it reads the mapping from that branch's head, and its run report names the branch and commit (FR-027, FR-031).
8. **Given** Shadow mode and a plan that a person's Gitea account approved, **When** the Lead runs the command, **Then** it sends exactly the approved plan's writes, each citing the approval, and the gateway carries them out as human-approved writes (spec 002 FR-037). **Given** the same approval after the feature changed, so that the run's plan no longer matches it, **When** the Lead runs the command, **Then** it writes nothing and reports the mismatch (FR-023).

---

### User Story 2 - Gate "Ready for Build" on a complete, traceable specification (Priority: P1)

Before any issue of a feature may move to Ready for Build, the bridge checks the feature against the completeness contract (Constitution Art. V). The contract holds:

- product intent and user stories;
- functional and non-functional requirements, and acceptance criteria;
- explicit non-goals;
- contracts where relevant;
- error and failure semantics, and authorization and security requirements;
- observability requirements, and performance targets where relevant;
- migration and compatibility requirements where relevant;
- an architecture plan, a dependency map and an acyclic task DAG;
- a reviewer checklist that Review owns;
- no unresolved clarification;
- a clean analysis report that Lead and Review both stand behind;
- traceability from every requirement to at least one task and one expected verification.

Each missing element is reported by name and location. A feature that fails stays out of Ready for Build. The result is tied to the commits it checked, and only a result produced by CI at the current commit counts. Spec 001's gate enforces the spec commit today; the producer and the commits of the plan, tasks and analysis report still need its support (FR-019).

**Why this priority**: The report replaces "complete 100 percent of the documentation" with a verifiable contract. Without the gate, the PSE session starts building from guesses, which Article V (Specification Before Build) forbids.

**Independent Test**: Run the traceability check on a fixture feature with one requirement that no task covers and one task with no expected verification. It fails with exactly those two findings. Fix both, rerun, and it passes.

**Acceptance Scenarios**:

1. **Given** a feature where FR-007 is referenced by no task, **When** the check runs, **Then** it fails and names FR-007 as untraced, citing the spec file and line.
2. **Given** a feature whose spec, plan or tasks still hold an open clarification marker, **When** the check runs, **Then** it fails and names the marker, and no issue of that feature can be moved to Ready for Build. Every open marker blocks, because the marker syntax carries no criticality tag (FR-017).
3. **Given** a feature that satisfies every element of the contract, **When** CI runs the check, **Then** it passes. It records a machine-readable result, tied to the commits it checked, that the control plane reads before it allows Lead's Ready for Build move (spec 001 FR-029, TR-03).
4. **Given** a feature where an element is not applicable (for example, no data migration), **When** the spec states that explicitly, **Then** the check accepts it; **When** the element is simply absent, **Then** the check fails. An absent element is never treated as N/A.
5. **Given** a passing result recorded at an earlier commit of the feature's spec, **When** Lead asks to move an issue to Ready for Build, **Then** the result does not count and the move is refused (spec 001 FR-029; FR-019). A result at an earlier commit of the plan or tasks, or one produced outside CI, does not count either (FR-019), but the control plane refuses the move on those grounds only once spec 001 FR-029 checks them.
6. **Given** a feature whose reviewer checklist was written and signed off only by the Lead, **When** the check runs, **Then** it fails and names the reviewer checklist as lacking Review's attribution (FR-029).
7. **Given** a `tasks.md` with a dependency cycle or a dependency on a task that does not exist, **When** the check runs, **Then** it fails and names the cycle or the dangling reference (FR-028).

---

### User Story 3 - Detect drift between the spec and the issue board without rewriting either (Priority: P2)

Work moves on. Tasks get renamed, split or removed in `tasks.md`; issues get closed, edited or created by hand in Gitea. The Lead runs the sync command (the report's `speckit-gitea-sync`). It compares every mapped task with its issue, and every issue that carries one of the feature's task identifiers with the task list. It then writes a drift report covering:

- issues with no task;
- tasks with no issue;
- dependency links that no longer match;
- closed issues whose task is still open in the spec;
- mapping entries that point at deleted issues;
- identifier-bearing issues that the Lead has not confirmed.

It changes nothing on its own.

**Why this priority**: Drift is inevitable over a long horizon. The report is explicit that drift must be reported rather than silently fixed, because silently rewriting the spec would let execution state overrule the source of truth (Article I).

**Independent Test**: On a synced fixture, delete one task from `tasks.md`, close one issue by hand and add one dependency link in Gitea. Run sync. The report lists exactly those three drifts, and `git status` shows no change to `tasks.md`, `spec.md` or the mapping.

**Acceptance Scenarios**:

1. **Given** a mapped task that was removed from `tasks.md`, **When** sync runs, **Then** the report lists its issue as "orphaned issue" and the issue is neither closed nor edited.
2. **Given** an issue closed in Gitea while its task is still unchecked in `tasks.md`, **When** sync runs, **Then** the report lists the pair as "state mismatch" and leaves both untouched.
3. **Given** no drift, **When** sync runs, **Then** the report says "no drift" and the command exits successfully.

---

### User Story 4 - Carry labels, milestone and assignee class onto each issue (Priority: P3)

Each created issue carries:

- labels derived from the task: user story, phase and parallelizable marker;
- a risk-class label on the constitution's Low/Medium/High/Critical scale, taken from the Lead's declaration;
- the feature's milestone;
- an assignee class (Lead, PSE or Review) rather than a named session.

It also carries a body in the issue contract that spec 001 defines, so any agent can rebuild its contract without a transcript. The bridge fills the sections it can derive from the repository: intent, spec and story reference, task IDs, acceptance criteria, non-goals, dependencies, risk, required verification and ownership. Current PR is empty at creation and filled later. Any section the bridge cannot derive is marked as waiting for the Lead and never invented.

**Why this priority**: These fields let the scheduler (spec 001) and the role agents act on issues mechanically. They are valuable but not blocking: issues without them can still be scheduled by hand.

**Independent Test**: Create issues for a fixture feature and read one back through the gateway. The labels, milestone, assignee class and every section of the issue contract are present, either filled or marked as waiting for the Lead.

**Acceptance Scenarios**:

1. **Given** a task marked `[P]` under User Story 2 in a feature whose Lead-declared risk class is Medium, **When** its issue is created, **Then** it carries labels for the story, the parallelizable marker and `risk:medium`, plus the feature's milestone.
2. **Given** any created issue, **When** a fresh session reads only that issue, **Then** it finds the intent, the spec reference, the task IDs, the acceptance criteria, the dependencies and the required verification without opening a chat transcript.
3. **Given** a feature with no declared risk class, **When** the command runs, **Then** it stops before any write and names the missing declaration. It never guesses a class (FR-004).

---

### Edge Cases

- A task ID appears twice in `tasks.md`. The command stops before any write and reports both lines. It never guesses which one is real.
- A dependency marker names a task ID that does not exist. The command stops before any write and reports the dangling reference. An issue created without its blocker link would look unblocked to the control plane's dependency unlock (FR-002).
- The dependency markers form a cycle. The command stops before any write and reports the cycle with every task in it, because a cyclic DAG can never unblock (FR-002).
- Gitea returns a transient error midway through a run. The command retries under the gateway's retry policy and records each issue in the mapping as soon as it is created. Only when retries are exhausted does it exit with a resumable error, and the next run resumes without duplicates. Whether the Lead session then stops is not the bridge's decision: "A session stops only when it is not making successful progress or is stuck." (project intake Q17, Q19).
- Someone edits `task-issue-map.yaml` by hand so that two tasks point at the same issue. Sync reports the collision; tasks-to-issues refuses to run until it is resolved.
- The feature folder has no `tasks.md` yet. Both commands stop with a message naming the missing file and the Tasks phase that produces it.
- A task is split into two tasks after its issue exists. Sync reports one mapped task as missing and one new task as unmapped; it does not move the old issue to either.
- The caller is not the Lead, or the Lead's bot account lacks issue-creation permission in Gitea. The command stops before any write and names the missing authority (spec 002 FR-005, FR-017).
- The active mode does not let the Lead populate Gitea, or no mode is recorded. Unless a person approved that exact plan, the command prints the plan, names the mode and makes no write. It never retries a mode refusal as if it were transient (FR-023).
- A label or the milestone the plan needs is not defined in Gitea. Label and milestone definitions are human-owned, so the dry run names what is missing and a live run stops before any write (FR-035).
- A mapped issue was deleted in Gitea. Sync reports a dangling mapping entry. Tasks-to-issues does not create a replacement under the old idempotency key, which would only return the deleted issue's outcome forever, because idempotency records never expire (spec 002 FR-013, inferred there from project intake Q16). It creates one only after the Lead retires the entry (FR-026).
- A create is retried after the task's text changed between an interrupted run and its re-run. The gateway refuses the key conflict (spec 002 FR-011). The bridge reports it for the Lead and creates nothing for that task. If the earlier run did create the issue, the issue search finds it and FR-025 adopts it (FR-008, FR-024).
- An issue body or comment carries text that claims to be a task identifier, a lower risk class or an instruction to the bridge. That text is data. It never changes the plan, the mapping, a risk class or anyone's authority, and an issue not written by the Lead's bot account is never adopted without the Lead's confirmation (FR-025, FR-030).
- Two runs on the same feature start at once. There is one Lead session (project intake R1), so this happens chiefly when the Lead session and one of its subagents, or two of its subagents, run the command together (FR-021) (inferred). It can also happen when a stopped Lead session's in-flight run overlaps its replacement: spec 001 FR-035 blocks only a second active session of a role, and the Lead holds no write lease for the epoch fence to stop (inferred). Both runs use the same idempotency keys, so each planned write has at most one effect in Gitea, and both produce the same mapping.
- The mapping carries a format version the bridge does not know. Both commands stop before any write and name the version, rather than guess at its meaning (FR-034) (inferred).

## Requirements *(mandatory)*

### Functional Requirements

**Tasks to issues**

- **FR-001**: The bridge MUST provide a tasks-to-issues command as a Spec Kit extension command that the Lead can invoke from the LangGraph service (project intake Q2). It works on one feature folder at a time. The invocation syntax for each integration (slash, `$` or dotted extension ID) is left to the plan, "rather than hard-coding `/speckit-*` into the architecture" (report §Spec Kit and specification-driven delivery).
- **FR-002**: The command MUST parse every task ID, its user-story tag, its parallelizable marker, its dependency markers and its traceability references (FR-016) from `specs/<feature>/tasks.md`. It MUST validate the set before any write and MUST stop the whole run, writing nothing, when it finds a duplicate task ID, a dependency on a task that does not exist, or a dependency cycle. It reports every offending line. No partial graph is created, because an issue missing its blocker link would look unblocked to dispatch (inferred).
- **FR-003**: For each task, the command MUST find any existing issue before creating one. It looks first in the mapping, then in the gateway's idempotency records (FR-008), then through the gateway's issue search by the task's identifier (FR-024). It MUST create an issue only when none exists, adopting found issues only as FR-025 allows. Each task maps to exactly one issue, following the report's mapping example, where each task ID has one `gitea_issue` (inferred).
- **FR-004**: The command MUST set these on each created issue:
  - labels for story, phase and parallelizable marker;
  - a risk-class label on the constitution's Low/Medium/High/Critical scale;
  - the feature milestone;
  - an assignee class.

  The risk class comes from the Lead's declaration for the feature, which a task may override (inferred from the report's issue template, where "Risk" is set per issue). The Lead records the feature's declaration in the feature folder, and a task's override on its task line under the convention of FR-016, so both are committed and readable without a transcript (Art. I). Their exact place and syntax are left to the plan (inferred). A missing feature declaration stops the run before any write. The label does not set the merge risk class: spec 006's classifier computes that, and the gateway uses the higher of the computed class and the label and ignores a lower label (spec 002 FR-026).

  The command MUST fill the issue body in the issue contract that spec 001 defines (Key Entities: Issue Contract), from these sources (inferred):
  - spec and story reference, task IDs and dependencies come from `tasks.md` and the mapping;
  - acceptance criteria come from the acceptance scenarios of the task's user story, and non-goals from the spec's non-goals;
  - intent comes from the story's summary;
  - required verification comes from the task's verification reference (FR-016);
  - ownership comes from the assignee class.

  Expected write domains are left for the Lead to declare (spec 001 FR-023), and current PR stays empty at creation. The bridge MUST NOT invent content for any section it cannot derive. It marks such a section as waiting for the Lead, who completes the contract before Ready for Build (Art. V; spec 003 FR-007).
- **FR-005**: The command MUST create a Gitea dependency link for every dependency marker whose both ends are mapped, and MUST NOT create a link that already exists.
- **FR-006**: The command MUST place every created issue in the board's entry column, which spec 001 sets as Backlog (spec 001 Dependencies). The report says only "Add to project board", so the column comes from spec 001, not from the report. Spec 001's transition table has no row for placing a new issue in Backlog, and spec 002 lets the Lead move issues only for TR-01 to TR-03 and Blocked, so the gateway may refuse this placement until those specs allow it. The command MUST NOT move an issue to any later column. Later moves follow spec 001's transition table: Backlog → Ready for Spec → Specifying → Ready for Build (TR-01 to TR-03), each requested by the Lead.
- **FR-007**: The command MUST write the mapping to `specs/<feature>/task-issue-map.yaml`. For each task, the mapping holds the issue number, its `blocked_by` task IDs and its generation (FR-026). Entries are kept in a stable sort order, so that an unchanged run produces an identical file.
- **FR-008**: The command MUST record each issue in the mapping as soon as it is created, so an interrupted run never loses track of an issue it made. If the uncommitted mapping is lost, a re-run MUST recover every issue the earlier run created for a task whose planned write is unchanged, by replaying its idempotency keys, because a replayed key with the same payload returns its first recorded outcome and those records never expire (spec 002 FR-011, FR-013, inferred there from project intake Q16). When a task's text changed in between, the gateway refuses the replay as a key conflict (spec 002 FR-011). The bridge then reports the conflict for the Lead and creates nothing for that task. If the earlier run did create the issue, the bridge recovers it through the issue search and adoption (FR-024, FR-025).
- **FR-009**: Every Gitea read and write MUST go through the semantic gateway (spec 002). Writes are made as the Lead's own Gitea bot account: "Each role gets its own Gitea bot account." (project intake Q15). The bridge holds no Gitea credential (spec 002 FR-016). Each write carries the mutation envelope and an idempotency key, so that a retried write has one effect and distinct writes never share a key (Art. III). The key is built from these parts (inferred; the report names none):
  - the feature;
  - the task ID;
  - the operation;
  - for a dependency link, the blocking task's ID (inferred);
  - the task's generation (FR-026) (inferred).

  The key's exact encoding is left to the plan.
- **FR-010**: Re-running the command on an unchanged feature MUST perform zero Gitea writes and leave the mapping unchanged.

**Drift detection**

- **FR-011**: The bridge MUST provide a sync command, as a Spec Kit extension command invocable in the same way as FR-001. It compares the mapping, `tasks.md` and the issues that carry the feature's task identifiers, which it finds through the gateway's issue search (FR-024).
- **FR-012**: The sync command MUST report at least these drift kinds:
  - orphaned issue;
  - unmapped task;
  - dangling mapping entry;
  - dependency mismatch;
  - state mismatch;
  - mapping collision;
  - unconfirmed issue, meaning an identifier-bearing issue that the Lead's bot account did not write and the Lead has not confirmed.
- **FR-013**: The sync command MUST be read-only toward the spec, `tasks.md`, the mapping and Gitea. It MUST NOT rewrite any of them to resolve drift (Article I: The Repository Is the Memory).
- **FR-014**: The drift report MUST be machine-readable and human-readable, naming each drift with the task ID, issue number and file location involved.

**Completeness and traceability gate**

- **FR-015**: The bridge MUST provide a completeness check that evaluates a feature against every element of the completeness contract in User Story 2 (Constitution Art. V), and MUST report each missing element by name and file location.
- **FR-016**: The check MUST verify traceability: every functional and non-functional requirement maps to at least one task, and every task maps to at least one expected verification, such as a named test, check or review step. Spec Kit's task format carries neither link, so each task line names the requirement IDs it serves and its expected verification. The Lead adds them at the Tasks stage, which the Lead owns (Constitution, Development Workflow). This traceability convention is inferred from Art. V and from the report's CI linter that "validates required headings, IDs, cross-references, and traceability". Its exact syntax is left to the plan.
- **FR-017**: The check MUST fail in either of these cases:
  - any clarification marker is still open in the feature's spec, plan or tasks. The marker syntax has no criticality tag, so every open marker counts as an unresolved critical clarification (inferred, failing closed under Art. IV).
  - the feature's analysis report is missing, older than the current commit of its spec, plan and tasks, or holds a CRITICAL finding.

  Spec Kit's analyze step writes no file (report: "analyze step is explicitly read-only"), and chat-only output is unavailable (Art. I). The analysis report MUST therefore be committed at a fixed path in the feature folder. It records the commits it analyzed (inferred). The path is left to the plan.
- **FR-018**: The check MUST accept an element marked explicitly not applicable with a reason, and MUST fail on an element that is merely absent ("not stated" is never "not applicable"; Article IV: Evidence Over Assertion).
- **FR-019**: The check MUST write a machine-readable completeness result per feature, which records:
  - the commits of the spec, plan, tasks and analysis report it evaluated;
  - the producer that ran the check;
  - each contract element's outcome;
  - the traceability matrix.

  The control plane reads it before it allows Lead's move into Ready for Build (spec 001 FR-029, TR-03; Article V: Specification Before Build). Only a result produced by CI (FR-020) at the feature's current commit counts. A result produced locally by any session is advice only (inferred), and a result from an older commit never counts.

  Spec 001 FR-029 enforces only part of this. It refuses a missing or failed result and one produced at an older spec commit. It does not check the producer, or the commits of the plan, tasks and analysis report. Because any actor may run the check (FR-021), a passing result a session produced locally at the current spec commit would satisfy that gate today. The CI-only rule and the binding to the plan, tasks and analysis commits are therefore this spec's own obligations, and no gate enforces them until spec 001 FR-029 adopts them (inferred).
- **FR-020**: The check MUST be runnable in CI as a linter with a non-zero exit on failure, so that a pull request that breaks traceability fails a check (Article VIII: Mistakes Become Mechanisms). Making that check a required status check changes CI policy and branch protection. That change is Critical risk and needs human approval, and the bridge never configures it (Art. VI).
- **FR-028**: The check MUST fail when the task DAG has a dependency cycle or a dependency on a task that does not exist (Art. V: "a task DAG").
- **FR-029**: The check MUST verify that the reviewer checklist is attributed to the Review role and that the analysis report is attributed to both Lead and Review. Attribution means written or signed off from that role's own account. The check MUST fail when either element was produced by the Lead alone (Art. II; Constitution, Development Workflow: "Checklist | Review", "Analyze | Lead + Review"). Reading the constitution's stage owners as an attribution rule the check verifies is this spec's own (inferred). The attribution mechanism is left to the plan.

**Authority and autonomy**

- **FR-021**: Only the Lead MAY run tasks-to-issues against a live Gitea repository, and it does so through its own bot account (FR-009). A subagent of the Lead session MAY run it only within the Lead session's authority, and is counted against "At most 2 subagents per container, per role and per Gitea bot account." (project intake Q18; spec 002 FR-008, FR-030). Any actor the gateway admits MAY run sync and the completeness check, because both are read-only toward Gitea (Article II: Separated Authority). Jev is included (inferred). Only the CI result of the check counts for Ready for Build (FR-019).
- **FR-022**: Both commands MUST support a dry-run mode that prints the planned writes without performing any. The plan lists every issue to create, link to add, label and milestone to set, and board placement, each with its idempotency key. It also carries a fingerprint over every planned write and its key, by which a person's approval names the plan (spec 002 FR-037) (inferred).
- **FR-023**: Tasks-to-issues MUST obey the active autonomy mode, which the gateway enforces (spec 002 FR-024; spec 001 FR-030). The bridge makes live writes on its own only in a mode that lets the Lead populate Gitea. Spec 007 grants that first in Long-horizon mode ("the Lead MAY … populate Gitea", spec 007 FR-005). Promotion to Long-horizon is approved only by Smokey, who is a person's account (project intake Q11 to Q13).
  - In Shadow mode, and when no mode is recorded, the command MUST produce the dry-run plan (FR-022) and name the mode. A person then applies the plan in either of two ways: "Both Create issues by hand and Approve; gateway writes it" (project intake R3).
    - (a) The person creates the planned issues by hand in Gitea. The bridge reports them as unconfirmed issues, which enter the mapping only after the Lead confirms them (FR-025).
    - (b) The person approves the plan from their own Gitea account. A later run of the command sends exactly the approved plan's writes, each citing the approval, and the gateway carries them out as human-approved writes through the Lead's bot account (spec 002 FR-037). The intake records that this answer changes spec 002 FR-024 and spec 007 FR-002 (project intake R3). Before any write, the command MUST check that the plan it computes matches the approved plan's fingerprint, and on a mismatch MUST write nothing and report it (inferred).
  - The person answered for Shadow mode. In Agent implementation and Guarded autonomous modes, which also come before Long-horizon (spec 007 FR-001), the same two ways apply (inferred, as spec 002 FR-037 also reads it).
- **FR-024**: Besides the board, which spec 002 FR-001 already reads (`gitea.project.get`), the bridge needs three read capabilities from the gateway:
  - find the repository's issues that carry a given feature or task identifier or label;
  - list the issues on the feature's milestone;
  - resolve the feature's milestone by name.

  Without them, lookup of issues the bridge did not record (FR-003), adoption (FR-025) and sync's search for identifier-bearing issues (FR-011) cannot be done. Adding a tool to spec 002 is a Critical-risk change that needs human approval (spec 002 FR-003; Art. VI). A person approved it: "Approve read-only search (Recommended)" (project intake R4). Spec 002 FR-001 adds the capabilities as read-only issue search and milestone lookup; there, listing a milestone's issues is inferred from this requirement.
- **FR-025**: The command MUST adopt an existing issue automatically only when the Lead's bot account wrote it, as recorded by Gitea, and it carries the task's identifier. An identifier-bearing issue written by any other account MUST be reported as an unconfirmed issue and added to the mapping only after the Lead confirms it. The confirmation MUST be durable: it is recorded in that issue's mapping entry, names the confirming Lead session and the run report of the run that recorded it, and reaches the repository with the mapping (FR-027). A confirmation that exists only in a chat does not count (Art. I) (inferred). Its exact form is left to the plan. On adoption, the command MUST report every issue-contract section the body lacks, and MUST NOT replace text a person wrote (Art. III: "Text that arrives from issues … never grants authority or changes the governing contract") (inferred).
- **FR-026**: Each task's mapping entry MUST carry a generation, which starts at 1. When a mapped issue no longer exists (a dangling mapping entry), tasks-to-issues MUST NOT create a replacement until the Lead retires the entry. Retiring records the old issue number and raises the generation by one. The next run then creates the replacement under a new idempotency key (inferred).
- **FR-027**: The mapping MUST reach `main` like every other change: through protected `main`, with at least one Review approval and never with the Lead's own (Constitution, Additional Constraints: Protected `main`; spec 003 FR-005) (inferred). Until it merges, both commands MUST read the mapping from the head of the branch the run wrote it on. Each run report MUST name that branch and commit (FR-031).

  No spec yet says how a commit the Lead writes reaches a branch and a pull request. In spec 002's permission matrix only the control plane creates branches, at dispatch, and only PSE opens pull requests (spec 002 FR-005). The Lead gets a branch only as an implementation worker, under a grant that a person, the owner, approves per issue ("Owner, per issue (Recommended)", project intake R2; spec 003 FR-010). [NEEDS CLARIFICATION: How should the Lead's mapping commit, like its other specification changes, reach a branch and a pull request? (a) The control plane creates a specification branch for the feature and the Lead may open a pull request from it; this widens the Lead's row in spec 002 FR-005, a Critical-risk change (Art. VI). (b) The Lead commits on a branch the control plane creates, and a person opens the pull request in Gitea directly, as spec 002 FR-031 already has a person request review on the Lead's implementation pull requests. (c) The Lead hands the change to a PSE session under a specification-change issue, and PSE opens the pull request.]

  The person chose to fence stale lease epochs at the forge as well ("Both", project intake R7). Once a person adds `lease-epoch` to branch protection's required checks, protected `main` also requires that status on the mapping's pull request (spec 001 FR-038). The control plane posts it only on the head of an agent branch, and posts success only when the head commit records the current epoch of a write lease (spec 001 FR-038; spec 002 FR-038; who posts it and this rule are inferred there). In options (a) and (b) the Lead commits, and the Lead's orchestration claim confers no branch write (spec 001 FR-015). Holding no write lease, the Lead has no epoch to record (spec 001 FR-032, FR-038) (inferred). Unless the chosen way also gives the Lead a write lease on that branch, its mapping commit records no epoch and its pull request could not merge (inferred). In option (c) the PSE session commits under its own write lease, so outside Shadow mode its commit can record the epoch (inferred). With one session per role and at most one issue in build at a time (project intake R1; spec 001 FR-035), any write lease used for the mapping commit, whether Lead's or PSE's under (c), makes its issue the one issue in build. The mapping change then waits for, and holds, the single build slot (inferred). In Shadow mode, where the first release runs (User Story 1), no write lease is granted and no `lease-epoch` status is posted at all (spec 001 FR-030, FR-038). A person's plan approval never covers branch creation or lease grants (spec 007 FR-002), and only PSE, under a write lease, opens a pull request (spec 002 FR-005). So in Shadow mode, under every option, the mapping's pull request cannot merge once the check is required (inferred). The answer to the marker above must therefore also say how the mapping's pull request meets this check, in Shadow mode as well as later modes. Specs 001 and 002 ask the same question only for branches a person pushed (spec 001 FR-038, spec 002 FR-038) (inferred).
- **FR-030**: The bridge MUST treat all text it reads from Gitea as untrusted data (spec 002 FR-015). This covers issue bodies, comments, labels set by others and titles. Such text MUST NOT change the plan, the mapping, a risk class or any authority. Issues are identified only by the gateway's structured fields and the bridge's own identifier (Art. III).

**Non-functional, observability and compatibility**

- **FR-031**: Every run of either command, dry or live, MUST leave a machine-readable run report. It records:
  - the actor, its bot account and session, and the mode in effect;
  - the feature and the commits it read;
  - every planned write, with its idempotency key and its outcome (performed, matched, skipped or refused, with the gateway's reason);
  - the mapping's branch and commit.

  The Lead's decision trace for the run cites this report. Optional visible reasoning may sit beside the trace, but it is never the record (project intake Q3: "Both"; Art. IX) (inferred).
- **FR-032**: Every bridge decision MUST be made in deterministic code, and the same inputs MUST yield the same plan, drift report and completeness result. Bridge decisions are what to create, what to adopt, which drift exists and whether the check passes. No model, Claude or Ollama, makes these decisions (project intake Q7; Art. III).
- **FR-033**: Each command MUST end with one of these distinct, machine-readable outcomes, each with its reason (inferred: the four outcomes are this spec's own design):
  - success;
  - validation failure (nothing written);
  - refused by mode or authority (nothing written);
  - partial and resumable (what was written is recorded).
- **FR-034**: The mapping, drift report, completeness result and run report MUST each carry a format version, so that later format changes can be migrated. Migration of existing data is not applicable to the first release, because no earlier mapping exists (inferred). The mapping, drift report and run report are this spec's own formats. The completeness result is different: this spec writes it and spec 001's TR-03 reads it, so it is a shared record. Its schema, at least the fields spec 001 reads, belongs among spec 009's shared record schemas, and this spec will write it in that schema rather than define a second copy (fixed dependency map) (inferred). The map gives 004 no direct edge to 009, so 004 reaches that schema through spec 001, which 009 precedes in the build order. Spec 009 does not list it yet.
- **FR-035**: The bridge MUST NOT create label or milestone definitions. Both are human-owned setup, like the label definitions in spec 002 (Assumptions: Human-owned setup); for milestones this is inferred. A label or milestone the plan needs that does not exist MUST be named in the dry run, and a live run MUST stop before any write.

### Key Entities

- **Task**: one line of `tasks.md`. It is identified by its task ID (T###) and carries:
  - a user-story tag and an optional parallelizable marker;
  - a description;
  - zero or more dependencies on other tasks;
  - the requirement IDs it serves and its expected verification (FR-016);
  - an optional risk-class override of the feature's declared class (FR-004).
- **Issue contract**: the structured issue body defined in spec 001 (Key Entities: Issue Contract). This spec keeps no second copy of its section list. FR-004 states which sections the bridge fills and from where.
- **Task-issue map**: the committed `task-issue-map.yaml` per feature, with a format version. It maps each task ID to one issue number, its `blocked_by` task IDs and its generation, and records retired issue numbers and the Lead's confirmation of every adopted issue that the Lead's bot account did not write (FR-025). It is the only link between the spec's IDs and Gitea's numbers.
- **Plan**: the ordered list of writes a run would perform: issues, links, labels, milestone and board placement, each with its idempotency key, plus the plan's fingerprint (FR-022). In a dry run the plan is printed and nothing is written. A person may approve it for the gateway to carry out (FR-023).
- **Drift finding**: one mismatch between the map, `tasks.md` and Gitea. It has a kind, the task ID and issue number involved, the evidence and a suggested owner.
- **Completeness result**: the per-feature outcome of the completeness check. It records:
  - each contract element with pass, fail or not-applicable-with-reason;
  - the traceability matrix (requirement → tasks → verifications);
  - the commits evaluated, the producer and the Review attributions found.

  It is a shared record that spec 001 reads, so its schema belongs among spec 009's shared record schemas (FR-034).
- **Run report**: the per-run record of FR-031. It holds the actor, mode, commits read, every planned write with its key and outcome, and the mapping's branch and commit.

### Non-goals

The constitution's Art. V lists explicit non-goals as part of a complete specification, so this subsection is added to the template. The bridge deliberately does not:

- Resolve drift automatically. Sync only reports it (FR-013).
- Move issues past the board's entry column. Spec 001's transition table owns every later move.
- Support GitHub. The forge is "Gitea only" (project intake Q1), so Spec Kit's core `taskstoissues` command and its GitHub issues extension stay unused.
- Create label or milestone definitions, or configure branch protection or required checks (FR-020, FR-035; Art. VI).
- Hold a Gitea credential or call Gitea except through spec 002.
- Define the issue contract's sections (spec 001), the role contracts (spec 003) or the autonomy modes (spec 007).
- Let a model decide what to create, adopt or report (FR-032).
- Define Spec Kit's `tasks.md` conventions beyond the traceability references of FR-016.
- Write or index `git-history.md`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Across 50 consecutive re-runs of tasks-to-issues on unchanged features, zero duplicate issues and zero duplicate dependency links are created.
- **SC-002**: A run interrupted at any point and then re-run ends with exactly one issue per task in 100% of fault-injection trials (at least 20 trials covering every write step).
- **SC-003**: A live tasks-to-issues run turns a 40-task feature into a fully linked issue graph in under 5 minutes of wall-clock time. This is measured on the MacBook host with Gitea, the LangGraph service, SQLite and local Ollama all running on it (project intake Q22).
- **SC-004**: In the first 3 months of use, 100% of issues that reach Ready for Build belong to a feature whose completeness result, produced by CI, passed at that commit. Spec 001's gate can hold this only once it checks the result's producer and the plan, tasks and analysis commits (FR-019).
- **SC-005**: Seeded drift fixtures, with at least one per drift kind in FR-012, are detected by sync with 100% recall and no false positives on a drift-free fixture.
- **SC-006**: (withdrawn: "requirements changed after implementation began" is a spec 007 scorecard metric that this gate alone can neither move nor be credited with, and 004 has no downstream edge to 007 in the dependency map)
- **SC-007**: With Shadow mode active, or no mode recorded, and no plan a person approved, tasks-to-issues performs 0 Gitea writes across the SC-001 fixture features. In 100% of those runs it prints a plan that lists every write a live run would make.
- **SC-008**: On seeded fixtures, the completeness check fails in 100% of cases and names the cause. The fixtures include one per missing contract element, an untraced requirement, a task with no verification, a cyclic or dangling task DAG, a Lead-only reviewer checklist and a result from an older commit. It passes on a complete fixture.
- **SC-009**: In seeded prompt-injection fixtures, 0 identifier-bearing issues written by an account other than the Lead's bot account enter the mapping without the Lead's confirmation recorded in their mapping entry (FR-025).
- **SC-010**: 100% of runs, dry or live, leave a run report that accounts for every planned write as performed, matched, skipped or refused.

## Assumptions

- **Forge**: Gitea 28.x is the forge (project intake Q1). Its API exposes issue dependencies, project columns, milestones and labels as the report describes.
- **Gitea instance**: Gitea runs on the MacBook with everything else (project intake Q22). The independent tests and SC-001, SC-002 and SC-007 need a scratch repository on that instance whose fixture mode can be set to Shadow or to a mode that lets the Lead populate Gitea (inferred). Two items are still open in the project intake: whether this GitHub-hosted repository is mirrored into that instance, and who operates it.
- **Host and scale**: the host is a MacBook Pro M4 Pro: "Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption." (data-model intake Q14). The bridge shares it with Gitea, the LangGraph service, SQLite and local Ollama. First-year scale is "10 Agents and 1 User" (data-model intake Q8), which matches the peak capacity "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20). The person split the 3 agent sessions "One per role (Recommended)": one session each for Lead, PSE and Review, with at most one issue in build at a time (project intake R1). A single Lead session therefore runs the bridge, itself or through at most 2 of its subagents (FR-021). The one-issue-in-build limit governs dispatch (spec 001 FR-035), not how many issues the bridge creates in Backlog (inferred).
- **Gateway**: every Gitea read and write travels through spec 002 as the calling role's own bot account (project intake Q15). Retries follow the gateway's and control plane's defaults: 5 attempts with exponential backoff capped at 2 minutes, which are proposed defaults in specs 001 and 002.
- **Task conventions**: task IDs and dependency markers follow Spec Kit's current `tasks.md` conventions. The bridge reads them and does not define them, except for the traceability references of FR-016.
- **Task identifier**: each issue carries a machine-readable identifier of its feature and task ID, so that lookup by task ID is exact rather than a title search. The report says only "Lookup existing Gitea issues by task ID". The identifier mechanism is left to the plan (inferred).
- **Applicability**: the completeness check's applicability rules ("where relevant") are decided per feature in the spec itself and are not inferred by the tool.
- **Stack**: "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." (project intake Q10; Q6: "OCaml and Python; Markdown; a vector DB; SQLite; knowledge graphs."). This replaces the earlier unconfirmed Python 3.12+ assumption. Read with the question's recommended option, the bridge is a Python engine like the repository's other Spec Kit engines, and any typed record it hands to the OCaml policy core uses the shared record formats that specs 001 and 002 consume. Planning decides the rest (inferred).
- **Autonomy modes**: the bridge reads the active mode only through spec 002 and spec 001. Until spec 007 supplies the modes, Shadow applies, so the dry-run path is the bridge's default and this spec can be built and tested first (inferred, as in spec 002's Assumptions).
- **Session stopping**: stopping a stuck Lead session is decided outside the bridge: "Checkpoint and stop, then escalate" (project intake Q21), using the stop rules of spec 008.
- **git-history.md**: commits that carry the mapping are pushed like any other commit. `git-history.md` is written "At the start of every Coding Agent Session and after every git push." (data-model intake Q20), is generated and gitignored (data-model intake Q26) and belongs to spec 009. The bridge never writes it (inferred).
- **Success-criteria numbers**: the numeric targets in Success Criteria are proposed defaults that the person has not confirmed. The person set the project's headline target in spec 007 SC-004: "+30% in 3 months (Recommended)", accepted issues per week (project intake R5). It does not cover this spec's numbers, so they remain proposed defaults, as in specs 001 and 002 (inferred).

## Dependencies

- **Upstream**:
  - **001-engineering-control-plane**: 004 consumes the board's entry column (Backlog) and transition table (TR-01 to TR-03), the issue-contract definition (Key Entities: Issue Contract), the autonomy-mode gate (FR-030), and the Ready for Build entry condition (FR-029, TR-03) that reads the completeness result 004 produces. FR-029 checks only the spec commit so far (this spec's FR-019), and the result's schema reaches 004 through 001 from spec 009 (this spec's FR-034). The mapping's pull request must also meet 001's `lease-epoch` required check once a person adds it to branch protection (FR-038; project intake R7; this spec's FR-027).
  - **002-gitea-mcp-gateway**: 004 consumes every Gitea read and write it makes: issue creation, labels resolved to IDs (FR-034), dependency links, board placement, the Lead's own bot account and authority (FR-005, FR-017), the mode check (FR-024), human-approved plan writes in Shadow mode (FR-037; project intake R3), idempotency with never-expiring records (FR-011, FR-013), untrusted-text labelling (FR-015), and the read-only issue search and milestone lookup approved for this spec's FR-024 (FR-001; project intake R4).
- **Downstream**: none. In the dependency map no spec depends on 004.
- **Related (not build edges)**: 003-role-agent-contracts (the Lead completes the issue contract on bridge-made issues, spec 003 FR-007); 006-quality-evidence-gates (requirements traceability feeds the merge evidence manifest); 007-progressive-autonomy (Long-horizon mode is where live Lead population begins).
- **Build order**: 009 → 001 → 002, 005 → 003, 004 → 006, 008 → 007. 004 is built after 001 and 002, in parallel with 003.
- **Constitution**: Article I (The Repository Is the Memory), Article II (Separated Authority), Article III (Agents Propose, Policy Decides), Article IV (Evidence Over Assertion), Article V (Specification Before Build), Article VI (Rules Are Not Self-Amendable), Article VIII (Mistakes Become Mechanisms), Article IX (Traces, Not Hidden Thoughts).

## Clarifications

### Session 2026-10-22

- Q: The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target? → A: Gitea only (project intake Q1)
- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service (project intake Q2)
- Q: The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work? → A: Both (project intake Q3)
- Q: How far should the dependent specs go in this first pass? → A: Constitution plus full spec set (project intake Q4)
- Q: Which language should the skills' source code (LangChain/LangGraph/RAG) be written in? → A: "OCaml and Python; Markdown; a vector DB; SQLite; knowledge graphs." (project intake Q6)
- Q: Which models and embeddings should the RAG and reasoning chains use? → A: "Ollama (cloud and local) alongside Claude Code models." (project intake Q7)
- Q: Which parts are OCaml and which stay Python? → A: "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." (project intake Q10)
- Q: Who may approve promotion to the Long-horizon and Self-improving autonomy modes (spec 007 FR-009)? → A: "an agent called Smokey, and Smokey should be the only one" (project intake Q11)
- Q: You said Smokey 'should be the only one'. The only one who may do what? (I read Jev and Smokey as two different agents: Jev watches sessions, Smokey approves.) → A: Sole top-mode approver (project intake Q12)
- Q: Is Smokey an autonomous agent or an account a person controls? Art. VI says agents may not authorize changes to their own authority. → A: A person's account (project intake Q13)
- Q: How should agents authenticate to Gitea (spec 002)? → A: "Each role gets its own Gitea bot account." (project intake Q15)
- Q: How long are raw deliveries and normalized events kept (spec 001 FR-007)? → A: "Events have no time limit." (project intake Q16)
- Q: When should a running session be stopped? → A: "A session stops only when it is not making successful progress or is stuck." (project intake Q17)
- Q: How many subagents may run at once? → A: "At most 2 subagents per container, per role and per Gitea bot account." (project intake Q18)
- Q: What does 'stuck' mean? → A: "A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing." (project intake Q19)
- Q: What is the peak capacity the system must sustain (spec 001 FR-021)? → A: "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20)
- Q: When a session is stuck: stop it automatically, or escalate to the user or Smokey first? → A: Checkpoint and stop, then escalate (project intake Q21)
- Q: Where should Gitea, the LangGraph service and the local Ollama models run? → A: All on the MacBook (project intake Q22)
- Q: How many people and agents should the data model support in its first year? → A: "10 Agents and 1 User" (data-model intake Q8, revised)
- Q: Which technical limits must the data model respect? → A: "Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption." (data-model intake Q14, revised)
- Q: When should git-history.md be written and fed to the vector store? → A: "At the start of every Coding Agent Session and after every git push." (data-model intake Q20, revised)
- Q: A git-history.md entry written after a push can't be inside that push. How should the file be kept? → A: Generated and gitignored (data-model intake Q26)
- Q: Spec 001 caps the team at 3 agent sessions. How should those 3 be split between Lead, PSE and Review? → A: "One per role (Recommended)" — one session each for Lead, PSE and Review; at most one issue in build at a time (project intake, R1)
- Q: Spec 003: Lead normally plans and does not write code. Who may switch Lead into implementation-worker mode for an issue? Lead may never grant this to itself (Art. VI). → A: "Owner, per issue (Recommended)" — a person (the owner) approves each switch, per issue (project intake, R2)
- Q: Spec 004: in Shadow mode, the Spec Kit→Gitea bridge only produces a dry-run plan. How should a person apply that plan? → A: "Both Create issues by hand and Approve; gateway writes it" — both paths: a person creates the issues by hand (the bridge reports them unconfirmed for Lead to confirm), or a person approves the plan and the gateway carries it out as a human-approved write (changes spec 002 FR-024 and spec 007 FR-002) (project intake, R3)
- Q: Spec 004: do you approve adding read-only issue search (by feature/task ID or label) and milestone lookup to the Gitea gateway? → A: "Approve read-only search (Recommended)" — a person approved it (Art. VI; spec 002 FR-003) (project intake, R4)
- Q: Spec 007's headline goal: what should autonomy deliver? The guardrails (escaped defects, reverts, security incidents, human recovery cost no worse than the Shadow-mode baseline) apply whichever is picked. → A: "+30% in 3 months (Recommended)" — accepted issues per week rise by at least 30% within 3 months of reaching Guarded autonomous mode, compared with Shadow mode, at the fixed capacity of 3 sessions, 6 subagents and Jev (project intake, R5)
- Q: Spec 008: when a stale session's lease is revoked, where should the epoch fence live? (Coordination layer only, or also a required commit status.) → A: "Both" (the person's own answer) — read as: the coordination-layer fence (spec 001 FR-032) and also a lease-epoch commit status that branch protection requires, so a commit from a stale epoch can never merge; which component posts the status is (inferred) (project intake, R7)
