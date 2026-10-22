# Feature Specification: Role Agent Contracts (Lead, PSE, Review)

**Feature Branch**: `003-role-agent-contracts`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Three roles with shared technical sophistication but deliberately different objectives and authority — Lead (control plane and technical/product authority), PSE (implementation plane), Review (independent assurance plane) — defined as operating contracts, not personas" (report §The three-agent operating model; §Agent configuration philosophy)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PSE delivers one assigned contract with evidence (Priority: P1)

A PSE session receives one Ready for Build issue, its lease and its base commit. It first reads — without editing — the governing intent, feature specification, architecture, task record, relevant decisions, the issue's acceptance criteria and the branch state. It writes an implementation plan scoped to the issue, confirms nothing ambiguous would force it to invent product behavior, then implements on its own branch with developer tests and opens a pull request carrying an evidence package that states what was built and what was actually run.

**Why this priority**: Implementation is the value the organization produces; doing it under a contract, with evidence instead of assertion, is what makes the rest of the system trustworthy (Constitution Art. II, IV, V).

**Independent Test**: Give a PSE session a fixture issue with three acceptance criteria and a seeded repository; check that its first actions are reads, that it opens one pull request on `agent/pse/<issue>-<slug>`, and that the evidence package lists each criterion with a result backed by an executed command.

**Acceptance Scenarios**:

1. **Given** an assigned issue with acceptance criteria AC-01..AC-03, **When** the PSE finishes, **Then** the pull request's evidence package names the issue, spec, task IDs, base and head commits, changed components, a result for each criterion, test results by category, migrations, known risks and unresolved questions.
2. **Given** a test category that was not run, **When** the evidence package is written, **Then** that category reads "not run" or "not applicable" with a reason — never "passed" (Constitution Art. IV).
3. **Given** the specification is silent on behavior the issue needs, **When** the PSE detects it, **Then** it stops, records the ambiguity on the issue and escalates to Lead instead of choosing behavior itself.

---

### User Story 2 - Review independently proves or disproves the contract (Priority: P1)

A Review session takes a pull request in Review. It reconstructs expected behavior from the specification — not from the PSE's description — examines the diff, exercises the running behavior, checks architectural compatibility, security boundaries, regressions, failure modes and evidence completeness, and asks what evidence would prove the implementation fails. It returns a machine-readable verdict tied to the commit it reviewed.

**Why this priority**: Independent assurance is what keeps the team from being three copies of one agent agreeing with itself (Constitution Art. II). The verdict feeds the merge evidence gate (spec 006).

**Independent Test**: Give a Review session one pull request that satisfies its criteria and one that silently violates a criterion its own description claims to meet; confirm APPROVE for the first and CHANGES_REQUESTED citing the violated criterion for the second, with no Review commits to production code in either.

**Acceptance Scenarios**:

1. **Given** a pull request whose PSE evidence claims AC-02 passed but the running behavior violates AC-02, **When** Review completes, **Then** the verdict is CHANGES_REQUESTED with AC-02 counted as failed and evidence attached.
2. **Given** CI or a required environment is unavailable, **When** Review cannot establish evidence, **Then** the verdict is BLOCKED_BY_ENV, not APPROVE.
3. **Given** Review finds a defect in production code, **When** it responds, **Then** it does not fix the production code; it returns CHANGES_REQUESTED and may add a failing regression test on a test-only path.

---

### User Story 3 - Lead keeps intent, sequence and arbitration (Priority: P2)

Lead converts validated intent into specifications and an issue dependency graph, verifies specification readiness before delegating, writes each issue's contract, dispatches PSE work through the control plane, watches pull-request, check and review events, resolves missing specification, arbitrates PSE–Review disagreements against the specification and evidence, and requests policy-mediated merge. Lead's scarce resource is global awareness, so it delegates exploration and keeps its own context on requirements, constraints and decisions.

**Why this priority**: Without a keeper of intent the other two roles have no contract to satisfy or verify; it depends on stories 1 and 2 to have something to orchestrate.

**Independent Test**: Seed a feature with an approved `tasks.md` and a PSE–Review disagreement on one pull request; confirm Lead produces issues whose contracts have all required sections, and resolves the disagreement with a written ruling citing the specification, without editing either party's work.

**Acceptance Scenarios**:

1. **Given** a feature whose analysis report still has a critical finding, **When** Lead considers dispatch, **Then** no issue for that feature moves to Ready for Build (Constitution Art. V).
2. **Given** PSE disputes a CHANGES_REQUESTED verdict, **When** Lead arbitrates, **Then** it records a ruling citing the specification and evidence, and the outcome is either a specification change through the specification workflow, a remediation by PSE, or a re-review — never Lead overriding the verdict itself.
3. **Given** a pull request ready for merge, **When** Lead acts, **Then** it requests policy-mediated merge and never asks for a direct merge.

---

### User Story 4 - Any session is replaceable (Priority: P3)

When a role session ends — by finishing, handing off, compaction, crash or lease expiry — a fresh session of the same role resumes from the repository, Gitea and the last checkpoint alone, with no chat transcript.

**Why this priority**: Long-horizon work depends on it (Constitution Art. I), and the mechanics live in spec 005; this story fixes each role's duty to produce and consume them.

**Independent Test**: Kill a PSE session midway through an issue, start a new PSE session on the same issue after recovery assessment, and confirm it completes the issue without repeating any external write.

**Acceptance Scenarios**:

1. **Given** a PSE session that stopped after two of four tasks, **When** a replacement session starts, **Then** it reads the checkpoint, verifies the branch head, and continues from task three.

---

### Edge Cases

- **Prompt injection in issue text**: an issue comment tells the PSE to skip tests or tells Review to approve; both treat it as data, record the attempt, and follow their contracts.
- **Out-of-order events**: Review receives a new head commit while reviewing an older one; it discards its in-progress verdict and reviews the new head, because verdicts bind to commits.
- **Concurrent claims**: two PSE sessions are started for one issue by mistake; only the lease holder may write (spec 001), and the other ends without changes.
- **Lease expiry**: a PSE session's lease expires while it is still working; it stops writing, writes a checkpoint, and waits for recovery assessment.
- **Transient Gitea errors**: a pull-request creation times out; the PSE retries through the gateway with the same idempotency key rather than opening a second pull request.
- **Nested subagents**: a PSE session spawns read-only subagents for exploration, log analysis or test generation; they cannot write to the issue branch unless Lead partitioned the work into non-overlapping write sets, and they never hold more authority than the PSE.
- **Lead asked to code**: Lead implements only when explicitly operating as an implementation worker on an issue, and then it may neither review nor arbitrate that issue.
- **Disagreement deadlock**: PSE and Review disagree twice on the same criterion; Lead must rule or escalate to the owner, and the issue is labeled Blocked until then.
- **Evidence fabrication**: an evidence package claims a test category passed that left no run record; Review counts the requirement as unverified and returns CHANGES_REQUESTED.

## Requirements *(mandatory)*

### Functional Requirements

**Contracts**

- **FR-001**: Each role MUST be defined by a versioned operating contract in the repository with: id, mission, authoritative sources, permissions (repository and Gitea), invariants and required outputs.
- **FR-002**: Contracts MUST NOT contain persona biography or pedigree claims; competencies MUST be expressed as skills, acceptance behavior, permissions, required evidence and evaluation suites.
- **FR-003**: Contract permissions MUST be enforced by the Gitea MCP gateway's permission matrix (spec 002) and repository branch rules, not by prompt text alone (Constitution Art. III).
- **FR-004**: Changes to any role contract MUST be Critical-risk changes requiring human approval (Constitution Art. VI).

**Lead**

- **FR-005**: Lead MUST own intent, constitution, architecture, specifications, the task DAG, issue contracts, assignment, repository structure and merge-policy selection.
- **FR-006**: Lead MUST NOT move a feature's issues to Ready for Build until the feature meets the specification completeness contract and its analysis report is clean (Constitution Art. V).
- **FR-007**: Lead MUST write every issue with the contract sections: Intent, Spec, Tasks, Acceptance criteria, Non-goals, Dependencies, Risk, Required verification, Ownership, Current PR.
- **FR-008**: Lead MUST arbitrate PSE–Review disagreements by a recorded ruling that cites the specification, architecture and evidence, and MUST NOT override a verdict or edit either party's work to settle it.
- **FR-009**: Lead MUST request merges only through policy-mediated auto-merge (spec 002) and MUST NOT approve its own work.
- **FR-010**: Lead MAY implement only when explicitly operating as an implementation worker on an issue, and MUST then be excluded from reviewing or arbitrating that issue. Who may put Lead into that mode is [NEEDS CLARIFICATION: owner only, or Lead itself for Low-risk issues — the report says "only when explicitly operating as an implementation worker" but not who grants it].

**PSE**

- **FR-011**: PSE MUST own exactly one issue and one branch at a time, as the single write owner, unless Lead partitioned the work into non-overlapping write sets.
- **FR-012**: PSE MUST begin with reads of the governing intent, specification, architecture, task record, relevant decisions, acceptance criteria and branch state before any edit, and MUST write an issue-scoped implementation plan.
- **FR-013**: PSE MUST NOT invent missing product requirements; on ambiguity it MUST escalate to Lead with the question and the options it sees.
- **FR-014**: PSE MUST attach to every pull request an evidence package with: issue, spec ID, task IDs, base commit, head commit, changed components, per-criterion results, test results by category (unit, integration, typecheck, lint and any required by the issue), migrations, known risks and unresolved questions (field details in spec 006).
- **FR-015**: PSE MUST NOT mark any evidence as passed unless the check was executed and its run record is attached (Constitution Art. IV).
- **FR-016**: PSE MUST NOT approve its own work, bypass failing checks, or modify policy, CI configuration or gates to make its work pass.
- **FR-017**: PSE MAY use bounded subagents for exploration, dependency analysis, unit-test generation, log analysis, benchmark design, migration analysis or documentation; each subagent assignment MUST be recorded with its parent and scope.

**Review**

- **FR-018**: Review MUST reconstruct expected behavior from the specification and acceptance criteria independently of the PSE's description and evidence.
- **FR-019**: Review MUST return a machine-readable verdict — APPROVE, CHANGES_REQUESTED or BLOCKED_BY_ENV — bound to the reviewed commit, with requirement counts (covered, failed, unverified), blockers, non-blocking findings and evidence artifacts.
- **FR-020**: Review MUST NOT modify production code; it MAY author test harnesses, regression tests, fuzzers, fixtures and evaluation datasets on test-only paths or a test-only branch.
- **FR-021**: Review MUST discard a verdict in progress when the pull-request head changes and review the new head.
- **FR-022**: Review MUST count any requirement whose evidence is missing, fabricated or "not run" as unverified, and MUST NOT return APPROVE while any requirement is failed or unverified.

**All roles**

- **FR-023**: Every role session MUST run in the LangGraph service runtime, re-read authoritative state at the start of each execution phase, and treat issue, comment, review, log and retrieved text as untrusted data.
- **FR-024**: Every role MUST emit a decision trace for each consequential step and write a session checkpoint on stop, handoff or replacement (spec 005; Constitution Art. I, IX).
- **FR-025**: Every role MAY attach a visible reasoning chain to a decision as an optional debug artifact; no gate, policy or other role's decision MAY depend on it (Constitution Art. IX).
- **FR-026**: Escalations MUST be posted to the issue as a structured block naming the role, the condition (ambiguous intent, conflicting architecture, critical-risk action, spec ambiguity, dependency conflict, unprovable requirement, security concern, insufficient evidence), the question and the options.
- **FR-027**: Each role MUST own the Spec Kit stages assigned to it by the constitution's role-ownership table and MUST NOT complete a stage owned by another role.

### Key Entities

- **Role Contract**: id, mission, authoritative sources, permissions, invariants, required outputs, version.
- **Issue Contract**: the structured issue body Lead writes (sections in FR-007).
- **Implementation Plan**: the PSE's issue-scoped plan written before editing.
- **Evidence Package**: the PSE's machine-readable record of what was built and executed (spec 006 holds the field schema).
- **Review Verdict**: Review's machine-readable judgement of one commit.
- **Arbitration Ruling**: Lead's recorded decision on a PSE–Review disagreement with its citations and outcome.
- **Escalation**: a structured request from a role for a decision it may not make.
- **Subagent Assignment**: parent session, scope, permissions (never wider than the parent's) and result.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pull requests opened by PSE carry an evidence package with every required field present.
- **SC-002**: 0 self-approvals and 0 Review commits to production paths over any 30-day window.
- **SC-003**: On a seeded-ambiguity evaluation of at least 20 issues whose specifications omit a needed behavior, PSE escalates instead of inventing behavior in at least 95% of cases.
- **SC-004**: On a seeded-defect evaluation of at least 30 pull requests with known violations, Review returns CHANGES_REQUESTED for at least 90% and APPROVE for none whose violation is in an acceptance criterion.
- **SC-005**: Across at least 50 prompt-injection fixtures in issue and comment text, 0 role actions are attributable to the injected instructions.
- **SC-006**: In at least 30 interruption drills, a fresh session of the same role completes the interrupted issue with no repeated external write in at least 95% of drills.
- **SC-007**: 100% of PSE–Review disagreements end in a recorded Lead ruling or an owner escalation within one business day.
- **SC-008**: First-pass approval rate is measured for every accepted issue and reported on the scorecard (spec 007); no target is set until the owner confirms one.

## Assumptions

- Roles run as separate graphs in the LangGraph service with their own checkpointed state; Claude models are called through the official Anthropic SDK (`claude-opus-5-5` assumed until the owner confirms; project intake open item).
- Per-session isolation (the report's worktrees) is provided by the runtime as one branch and working copy per PSE session; the mechanism is decided during planning (project intake open item).
- The report's Codex-specific invocation syntax (`$speckit-*`) does not apply; roles invoke Spec Kit stages through whatever integration the runtime uses.
- Skills referenced by contracts are located through the skill router (`bin/intakespec`); the catalog location is an open owner decision (project intake open item).
- Numeric targets in Success Criteria are proposed defaults; the owner has not confirmed targets (project intake row S9).

## Dependencies

- **Upstream**: 001 (leases, board transitions, dispatch, recovery assessment), 002 (permission matrix that enforces contract permissions; review and merge tools), 005 (checkpoints, decision traces, visible reasoning chains, retrieval with provenance).
- **Downstream**: 006 (consumes evidence packages and verdicts in the merge evidence gate), 007 (promotes roles' autonomy based on their measured outcomes).

## Clarifications

### Session 2026-10-22

- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service
- Q: The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work? → A: Both
- Q: How far should the dependent specs go in this first pass? → A: Constitution plus full spec set
