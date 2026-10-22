# Feature Specification: Role Agent Contracts (Lead, PSE, Review)

**Feature Branch**: `003-role-agent-contracts`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Three roles with shared technical sophistication but deliberately different objectives and authority — Lead (control plane and technical/product authority), PSE (implementation plane), Review (independent assurance plane) — defined as operating contracts, not personas" (report §The three-agent operating model; §Agent configuration philosophy). Refined by the person's later answers on models (project intake Q7, Q14), Smokey (Q11–Q13), Gitea bot accounts (Q15), stopping and stuck sessions (Q17, Q19, Q21), subagents and capacity (Q18, Q20) and hosting (Q22).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - PSE delivers one assigned contract with evidence (Priority: P1)

A PSE session receives one Ready for Build issue, its lease and its base commit. It first reads — without editing — the governing intent, feature specification, architecture, task record, relevant decisions, the issue's acceptance criteria and the branch state. It writes an implementation plan scoped to the issue and confirms that no ambiguity would force it to invent product behavior. It then implements on its own branch with developer tests and opens a pull request carrying an evidence package that states what was built and what was actually run. It does this only where the active autonomy mode allows PSE writes. In Shadow mode, the mode every installation starts in, the same work becomes a recommendation, and a person performs the writes.

**Why this priority**: Implementation is the value the organization produces. Doing it under a contract, with evidence instead of assertion, is what makes the rest of the system trustworthy (Constitution Art. II, IV, V).

**Independent Test**: In Agent implementation mode, give a PSE session a fixture issue with three acceptance criteria and a seeded repository. Check that its first actions are reads, that it opens one pull request on `agent/pse/<issue>-<slug>`, and that the evidence package lists each criterion with a result backed by an executed command.

**Acceptance Scenarios**:

1. **Given** an assigned issue with acceptance criteria AC-01..AC-03, **When** the PSE finishes, **Then** the pull request's evidence package names the issue, the spec, the task ID or IDs, the base and head commits, the changed components, a result for each criterion, test results by category, migrations, known risks and unresolved questions, and the pull request carries a documentation delta.
2. **Given** a test category that was not run, **When** the evidence package is written, **Then** that category reads "not run" or "not applicable" with a reason, never "passed" (Constitution Art. IV).
3. **Given** the specification is silent on behavior the issue needs, **When** the PSE detects it, **Then** it stops, records the ambiguity on the issue and escalates to Lead instead of choosing the behavior itself (Constitution Art. V).
4. **Given** Shadow mode is active, **When** the PSE finishes its plan and proposed change, **Then** the gateway refuses its pull-request creation with "mode: shadow", the plan, proposed change and evidence are recorded as a recommendation, and a person performs the writes (FR-029).

---

### User Story 2 - Review independently proves or disproves the contract (Priority: P1)

A Review session takes a pull request in Review. It reconstructs expected behavior from the specification, not from the PSE's description. It examines the diff and exercises the running behavior. It checks architectural compatibility, security boundaries, regressions, failure modes and evidence completeness, and asks what evidence would prove the implementation fails. It returns a machine-readable verdict tied to the commit it reviewed.

**Why this priority**: Independent assurance is what keeps the team from being three copies of one agent agreeing with itself (Constitution Art. II). The verdict feeds the merge evidence gate (spec 006).

**Independent Test**: Give a Review session two pull requests. The first satisfies its criteria. The second silently violates a criterion that its own description claims to meet. Confirm APPROVE for the first, and CHANGES_REQUESTED citing the violated criterion for the second, with no Review commits to production paths in either.

**Acceptance Scenarios**:

1. **Given** a pull request whose PSE evidence claims AC-02 passed but whose running behavior violates AC-02, **When** Review completes, **Then** the verdict is CHANGES_REQUESTED, with AC-02 counted as failed and evidence attached.
2. **Given** CI or a required environment is unavailable, **When** Review cannot establish evidence, **Then** the verdict is BLOCKED_BY_ENV, not APPROVE.
3. **Given** Review finds a defect in production code, **When** it responds, **Then** it does not fix the production code. It returns CHANGES_REQUESTED and may add a failing regression test on a test-only path (FR-033).
4. **Given** Review finds a defect outside the scope of the pull request under review, **When** it reports it, **Then** it opens a QA issue and leaves the pull request's scope unchanged (FR-034).

---

### User Story 3 - Lead keeps intent, sequence and arbitration (Priority: P2)

Lead converts validated intent into specifications and an issue dependency graph. It verifies specification readiness before delegating, completes each issue's contract, and dispatches PSE work through the control plane. It watches pull-request, check and review events, resolves missing specification, arbitrates PSE–Review disagreements against the specification and evidence, and requests policy-mediated merge. Lead's scarce resource is global awareness, so it delegates exploration to at most 2 subagents at a time (FR-035) and keeps its own context on requirements, constraints and decisions.

**Why this priority**: Without a keeper of intent, the other two roles have no contract to satisfy or verify. This story can be tested on its own with seeded issues and a seeded disagreement, without stories 1 and 2 running.

**Independent Test**: Seed a feature whose issues already exist with incomplete contracts, plus one pull request carrying a PSE–Review disagreement. Confirm that Lead completes every section of the issue contract (spec 001) before any issue reaches Ready for Build. Confirm that it resolves the disagreement with a written ruling citing the specification, without editing either party's work.

**Acceptance Scenarios**:

1. **Given** a feature whose analysis report still has a critical finding, **When** Lead considers dispatch, **Then** no issue for that feature moves to Ready for Build (Constitution Art. V).
2. **Given** PSE disputes a CHANGES_REQUESTED verdict, **When** Lead arbitrates, **Then** it records a ruling citing the specification and evidence. The outcome is one of three: a specification change through the specification workflow, a remediation by PSE, or a re-review. Lead never overrides the verdict itself (Constitution Art. II).
3. **Given** a pull request ready for merge in a mode that allows agent merge scheduling, **When** Lead acts, **Then** it requests policy-mediated merge and never asks for a direct merge.
4. **Given** Jev escalates a stuck PSE session to Lead, **When** Lead answers, **Then** it records one decision: re-plan, reassign, or a hard stop. A hard stop is carried out only at the stop ladder's hard-stop step, after the stop request's grace window has passed without a checkpoint and a lease release (spec 008). It then revokes the session's lease with the stuck verdict as the reason (FR-031).

---

### User Story 4 - Any session is replaceable, and a stuck session stops cleanly (Priority: P3)

A role session can end in several ways: it finishes or hands off its work, it is compacted, it crashes (its lease then expires because its heartbeat stops), or it is stopped because it is stuck or not making successful progress ("A session stops only when it is not making successful progress or is stuck.", project intake Q17). In every case, a fresh session of the same role resumes from the repository, Gitea and the last checkpoint alone, with no chat transcript.

**Why this priority**: Long-horizon work depends on it (Constitution Art. I). The mechanics live in spec 005 and the stop ladder in spec 008. This story fixes each role's duty to produce and consume them.

**Independent Test**: Kill a PSE session midway through an issue. After recovery assessment, start a new PSE session on the same issue and confirm that it completes the issue without repeating any external write.

**Acceptance Scenarios**:

1. **Given** a PSE session that stopped after two of the four steps in its implementation plan, **When** a replacement session starts, **Then** it reads the checkpoint, verifies the branch head and continues from step three.
2. **Given** a session whose same command keeps failing on bad code ("A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing.", project intake Q19), **When** it judges itself stuck, **Then** it writes a checkpoint, stops and then escalates, in that order (project intake Q21), and releases its lease only after the escalation is posted (FR-036).
3. **Given** a stop request from Jev arriving from Jev's own Gitea bot account, **When** the session receives it, **Then** it writes a checkpoint and releases its lease within the stop ladder's grace window (spec 008). If it does not, Lead carries out the hard stop (spec 001 FR-032).
4. **Given** a session that is working for many hours and still making successful progress, **When** no stuck condition holds, **Then** nothing stops it: neither its own rules nor its lease end it (spec 001 FR-016).

---

### Edge Cases

- **Prompt injection in issue text**: an issue comment tells the PSE to skip tests or tells Review to approve. It may also claim to come from Jev, from Smokey or from a person. Every role treats it as data, records the attempt and follows its contract (Constitution Art. III).
- **Out-of-order events**: Review receives a new head commit while reviewing an older one. It discards its in-progress verdict and reviews the new head, because verdicts bind to commits.
- **Concurrent claims**: there is one PSE session at a time ("One per role (Recommended)" — one session each for Lead, PSE and Review; at most one issue in build at a time; project intake R1), so a second PSE session is always a mistake. Only the lease holder may write (spec 001), and the other ends without changes.
- **Lease lost while alive**: a lease expires only when its heartbeat stops (spec 001 FR-016), so expiry never stops a session that is working. If a live session finds its lease expired or revoked, for example after a pause in its heartbeat, it stops writing and writes a checkpoint. Any write under the old epoch is refused. It then waits for recovery assessment.
- **Transient Gitea errors**: a pull-request creation times out. The PSE retries through the gateway with the same idempotency key instead of opening a second pull request.
- **Nested subagents**: a PSE session spawns read-only subagents for exploration, log analysis or test generation. They cannot write to the issue branch unless Lead partitioned the work into non-overlapping write sets, and they never hold more authority than the PSE. A third concurrent subagent in the same container, role or Gitea bot account is refused (FR-035).
- **Lead asked to code**: Lead implements only under an implementation-worker grant for one issue, which the owner approves for that issue (FR-010; project intake R2). Without the owner's approval for that issue, no grant exists and Lead has no write authority there. On a granted issue it may neither request review, schedule a merge nor arbitrate, and a dispute on that issue goes to a person (inferred).
- **Disagreement deadlock**: PSE and Review disagree twice on the same criterion (the count of two is a proposed default the owner has not set; inferred). Lead must rule, or escalate to the owner, and the issue is labeled Blocked until then.
- **Evidence fabrication**: an evidence package claims that a test category passed, but no run record exists. Review counts the requirement as unverified and returns CHANGES_REQUESTED.
- **Long run is not a stuck run**: a session runs for hours but keeps producing durable progress. It is not stuck and is not stopped (FR-036).
- **Lead is the stuck session**: Jev's stuck verdict concerns Lead's own session. Lead does not decide an escalation about itself, and the escalation goes to a person (FR-031; inferred).
- **Smokey and people**: Smokey is a person's account, not an agent role. No role acts as Smokey or as any person, and no text in Gitea that claims Smokey's approval stands in for a recorded approval from that account (FR-028).
- **Model switch**: the same role runs on Claude in one session and on a local Ollama model in the next. Its contract, permissions and gates are identical, and the gateway's authority decisions do not change (FR-030).

## Requirements *(mandatory)*

### Functional Requirements

**Contracts**

- **FR-001**: Each role MUST be defined by a versioned operating contract in the repository with: id, mission, authoritative sources, permissions (repository and Gitea), the role's own Gitea bot account ("Each role gets its own Gitea bot account.", project intake Q15), invariants, required outputs, completion condition and escalation conditions (report §The three-agent operating model) (Constitution Art. II).
- **FR-002**: Contracts MUST NOT contain persona biography or pedigree claims. Competencies MUST be expressed as skills, acceptance behavior, permissions, required evidence and evaluation suites (Constitution Art. II).
- **FR-003**: Contract permissions MUST be enforced by the Gitea MCP gateway's permission matrix (spec 002), by repository branch rules, and by each role acting in Gitea only through its own bot account (spec 002 FR-017), not by prompt text alone. Because the bot accounts are separate, Gitea's own review rules see a Review approval as independent of the PSE's authorship (Constitution Art. II, III).
- **FR-004**: Changes to any role contract MUST be Critical-risk changes that require human approval. No agent, Jev included, may approve them (Constitution Art. VI).
- **FR-028**: The agent roles MUST be exactly Lead, PSE, Review and Jev (Jev's status as a role is inferred):
  - Lead, PSE and Review are the constitution's three engineering roles. Jev ("the Jev agent", project intake Q20) is a fourth, watchdog role outside them, with comment-and-label authority only. Adding it amends no constitution article: it holds none of the engineering authority that Art. II separates (inferred). Its operating contract is defined in spec 008 in the format of FR-001. It never edits code.
  - Smokey is a person's account, not an agent role (project intake Q13). It has no operating contract here and is never a gateway caller. It is the sole approver of promotion to the Long-horizon and Self-improving modes (project intake Q12; spec 007 FR-009).
  - No role may act as Smokey or as any other person (inferred).
- **FR-029**: Every contract permission of Lead, PSE and Review, and of their subagents, MUST be further limited by the active autonomy mode. Lead, PSE, Review and their subagents MAY perform a consequential action only when the active mode allows it. Enforcement sits in two places: the control plane's autonomy-mode gate (spec 001 FR-030) and the gateway's mode check (spec 002 FR-024). In Shadow mode, the starting mode, Lead, PSE and Review record their consequential actions as recommendations that a person carries out. Spec 007 sets which actions each mode allows, and a contract never grants more than its mode allows (Constitution Art. III; Development Workflow: Progressive autonomy). Jev's comment-and-label writes are not mode-gated, because they record observations rather than engineering work (spec 002 FR-024; inferred).
- **FR-030**: A role's contract, permissions, gates and evidence duties MUST be the same whichever allowed model the session runs: Claude, or Ollama cloud or local ("Ollama (cloud and local) alongside Claude Code models.", project intake Q7; constitution v1.1.0 per project intake Q14). Authority decisions stay in deterministic code, never in a model (Constitution Art. III).

**Lead**

- **FR-005**: Lead MUST own intent, constitution, architecture, specifications, the task DAG, issue contracts, assignment, repository structure and merge-policy selection (Constitution Art. II). Observably, Lead is the only role whose contract permits authoring changes to those artifacts. In the gateway's permission matrix (spec 002 FR-005), it is also the only role that may update and assign issues, set dependencies, and make the planning-board transitions from Backlog through Ready for Build. Review may create QA issues only (FR-034). Changes Lead authors are approved by another role or a person, never by Lead.
- **FR-006**: Lead MUST NOT move a feature's issues to Ready for Build until the feature meets the specification completeness contract, with a passing completeness result recorded (spec 001 FR-029), and its analysis report is clean (Constitution Art. V).
- **FR-007**: Lead MUST complete every section of the issue contract defined in spec 001 (Key Entities: Issue Contract) on every issue before the issue enters Ready for Build. This applies whether the issue was written by hand or generated by a tool. This spec keeps no second copy of the section list.
- **FR-008**: Lead MUST arbitrate PSE–Review disagreements by a recorded ruling that cites the specification, architecture and evidence. It MUST NOT override a verdict, or edit either party's work, to settle it (Constitution Art. II). On an issue where Lead holds an implementation-worker grant, the dispute goes to a person instead (FR-010; inferred).
- **FR-009**: Lead MUST request merges only by scheduling policy-mediated auto-merge through the gateway (spec 002), and only where the active mode allows it (FR-029). It MUST NOT approve its own work (Constitution Art. II, III).
- **FR-010**: Lead MAY implement only under an implementation-worker grant that the control plane records for one issue and the gateway honors (spec 002 FR-031):
  - On that issue only, Lead works as a PSE would: under a write lease and on its own branch, `agent/lead/<issue>-<slug>` (the branch name is inferred from the constitution's pattern).
  - On that issue it MUST NOT request review, schedule a merge or arbitrate. The gateway refuses the first two, and disputes on that issue go to a person (inferred).
  - The owner (a person) approves each grant, per issue ("Owner, per issue (Recommended)" — a person (the owner) approves each switch, per issue; project intake, Phase Refinements Specify R2). Lead never grants it to itself (Constitution Art. VI).
- **FR-031**: Lead MUST answer every stuck escalation it receives from Jev about another role's session with one recorded decision: re-plan, reassign, or a hard stop. Lead carries out a hard stop only at the stop ladder's hard-stop step, after the stop request's grace window has passed without a checkpoint and a lease release (spec 008). It then revokes the session's lease with the stuck verdict as the recorded reason (spec 001 FR-032). A session that writes its checkpoint and releases its lease within the window is not revoked. Spec 008 sets how fast Lead must answer and what happens when it does not. Lead MUST NOT decide an escalation about its own session; that escalation goes to a person (inferred; Constitution Art. II).

**PSE**

- **FR-011**: PSE MUST hold exactly one assigned issue on one isolated branch at a time (Constitution Art. II). It is the single write owner of that issue. The exception is an issue that Lead partitioned into non-overlapping write sets: each part then has one write owner (spec 001 FR-015).
- **FR-012**: PSE MUST begin with reads of the governing intent, specification, architecture, task record, relevant decisions, acceptance criteria and branch state before any edit. It MUST then write an issue-scoped implementation plan.
- **FR-013**: PSE MUST NOT invent missing product requirements. On ambiguity, it MUST escalate to Lead with the question and the options it sees (Constitution Art. V).
- **FR-014**: PSE MUST attach an evidence package to every pull request. The package holds: the issue, the spec ID, the task ID or IDs the issue carries, the base commit, the head commit, the changed components, per-criterion results, test results by category (unit, integration, typecheck, lint and any category the issue requires), migrations, known risks and unresolved questions. This spec owns this field set, and spec 006 consumes it (inferred, resolving a circular reference between the two specs).
- **FR-015**: PSE MUST NOT mark any evidence as passed unless the check was executed and its run record is attached (Constitution Art. IV).
- **FR-016**: PSE MUST NOT approve its own work, bypass failing checks, or modify policy, CI configuration or gates to make its work pass (Constitution Art. II, VI).
- **FR-017**: PSE MAY use bounded subagents for exploration, dependency analysis, unit-test generation, log analysis, benchmark design, migration analysis or documentation, within the cap of FR-035. Each subagent assignment MUST be recorded with its parent and scope.
- **FR-032**: For every issue, PSE MUST produce:
  - the implementation and developer tests;
  - a documentation delta covering the documentation affected by the implementation, or an explicit "none" with a reason;
  - the evidence package (FR-014);
  - a session checkpoint.

  (Report §Agent configuration philosophy: `required_outputs`; report §The three-agent operating model: PSE owns "documentation affected by implementation".)

**Review**

- **FR-018**: Review MUST reconstruct expected behavior from the specification and acceptance criteria independently of the PSE's description and evidence (Constitution Art. II).
- **FR-019**: Review MUST return a machine-readable verdict bound to the reviewed commit. The verdict is APPROVE, CHANGES_REQUESTED or BLOCKED_BY_ENV, and carries requirement counts (covered, failed, unverified), blockers, non-blocking findings and evidence artifacts. This spec owns this field set, and spec 006 consumes it (inferred).
- **FR-020**: Review MUST NOT modify production code. It MAY author test harnesses, regression tests, fuzzers, fixtures and evaluation datasets on test-only paths (FR-033) or a test-only branch (Constitution Art. II, VIII).
- **FR-021**: Review MUST discard a verdict in progress when the pull-request head changes, and review the new head.
- **FR-022**: Review MUST count any requirement whose evidence is missing, fabricated or "not run" as unverified. It MUST NOT return APPROVE while any requirement is failed or unverified (Constitution Art. IV).
- **FR-033**: Production paths and test-only paths MUST be classified by a versioned path policy in the repository. A path the policy does not classify counts as production. Changes to that policy are Critical risk, because it bounds Review's own gate (inferred; Constitution Art. IV, VI).
- **FR-034**: Review MAY open QA issues for defects or gaps it finds (report §The three-agent operating model: Review's Gitea authority includes "QA issues"; spec 002 FR-005 grants Review issue creation for QA issues only). It MUST NOT use a QA issue to widen the scope of the pull request under review, and Lead triages QA issues like any other issue (inferred).

**All roles**

- **FR-023**: Every role session MUST run in the LangGraph service runtime (project intake Q2). It MUST re-read authoritative state at the start of each execution phase, meaning session start, every resume from a checkpoint, and before every consequential Gitea write (spec 005 lifecycle hooks and checkpoint verification). It MUST treat issue, comment, review, log and retrieved text as untrusted data (Constitution Art. I, III, VII).
- **FR-024**: Every role MUST emit a decision trace for each consequential step, in the sense of spec 005's decision traces and spec 001's list of consequential actions. It MUST write a session checkpoint on stop, handoff or replacement (spec 005; Constitution Art. I, IX).
- **FR-025**: Every role MAY attach a visible reasoning chain to a decision as an optional debug artifact. No gate, policy or other role's decision MAY depend on it, and that includes Jev's stuck verdict. "Reasoning stops making progress" (project intake Q19) is judged from decision traces and the session's recorded events, never from visible reasoning chains (inferred; Constitution Art. IX).
- **FR-026**: Escalations MUST be posted to the issue as a structured block naming the role, the condition, the question and the options. The conditions are: ambiguous intent, conflicting architecture, critical-risk action, spec ambiguity, dependency conflict, unprovable requirement, security concern, insufficient evidence, and stuck (FR-036).
- **FR-027**: Each role MUST own the Spec Kit stages that the constitution's role-ownership table assigns to it, and MUST NOT complete a stage owned by another role. A jointly owned stage (Analyze: Lead + Review; Final acceptance: Review + Lead) is complete only when both roles have recorded their sign-off. Neither role completes it alone (inferred; Constitution, Development Workflow).
- **FR-035**: Every Lead, PSE and Review session MAY use bounded subagents, but MUST NOT exceed the person's cap: "At most 2 subagents per container, per role and per Gitea bot account." (project intake Q18). Jev runs no subagents, which matches the person's capacity of "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20; inferred).
  - Each subagent works under its parent session's role, bot account and lease, and never holds more authority than its parent (spec 001 FR-034; inferred).
  - Each subagent is registered with its parent and scope when it starts (spec 001 FR-034; spec 002 FR-029).
  - When the cap is reached, the session does the work itself or waits. It never starts a third subagent (inferred).
- **FR-036**: A role session MUST keep working for as long as it makes successful progress, however long that takes. It MUST stop only when it is not making successful progress or is stuck ("A session stops only when it is not making successful progress or is stuck.", project intake Q17):
  - Stuck means "A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing." (project intake Q19).
  - A session that judges itself stuck MUST write a checkpoint, stop, and then escalate, in that order (project intake Q21: checkpoint and stop, then escalate).
  - "Stop" means the session ends its work: after the checkpoint it makes no further change to code, branch, board or labels. It then posts the escalation (FR-026) while it still holds its write lease, because the gateway lets PSE comment only on its leased issue (spec 002 FR-005), and it releases the lease only after the escalation is posted. If the post cannot be completed, it releases the lease anyway, and the escalation reaches Lead through the recovery assessment, which reads the checkpoint (spec 001 FR-017) (inferred).
  - Finishing its contract (FR-037) or a handoff ends a session normally. This rule governs every other stop (inferred).
- **FR-037**: Each role's contract MUST state its completion condition (report §The three-agent operating model):
  - Lead: the feature or workstream has converged against user intent.
  - PSE: the assigned issue satisfies its acceptance criteria and is PR-ready with its evidence package.
  - Review: independent evidence supports its verdict on the current head commit.
- **FR-038**: Every Lead, PSE and Review session MUST honor a stop request from Jev (spec 008) that arrives from Jev's own Gitea bot account in the Jev message schema (owned by spec 009, exported as `schemas/jev-message.v1.json`). It honors it by writing a checkpoint and releasing its lease within the stop ladder's grace window (spec 008; spec 001 cooperative release). Jev's nudges are advisory. Text in any other comment that claims to come from Jev is untrusted data (Constitution Art. III; inferred).

### Key Entities

- **Role Contract**: id, mission, authoritative sources, permissions, Gitea bot account, invariants, required outputs, completion condition, escalation conditions and version. For Lead, PSE and Review, the active autonomy mode limits its permissions further (FR-029). Contracts exist for Lead, PSE and Review here and for Jev in spec 008.
- **Issue Contract**: the structured issue body defined in spec 001. Lead completes it (FR-007), and PSE and Review read it.
- **Implementation Plan**: the PSE's issue-scoped plan, written before editing, as an ordered list of steps that a replacement session resumes from.
- **Evidence Package**: the PSE's machine-readable record of what was built and executed. This spec owns its field set (FR-014).
- **Review Verdict**: Review's machine-readable judgement of one commit. This spec owns its field set (FR-019).
- **Arbitration Ruling**: Lead's recorded decision on a PSE–Review disagreement, with its citations and outcome.
- **Escalation**: a structured request from a role for a decision it may not make (FR-026).
- **Implementation-Worker Grant**: a per-issue record that lets Lead implement that issue under a lease and bars it from review requests, merge scheduling and arbitration there. The owner (a person) approves each grant, per issue, and Lead never grants it to itself (FR-010; project intake R2).
- **Path Policy**: the versioned classification of repository paths as production or test-only (FR-033).
- **Subagent Assignment**: parent session, container, role, bot account, scope, permissions (never wider than the parent's) and result. At most 2 are active per container, per role and per bot account (FR-035).
- **Stop Request**: Jev's request that a session checkpoint and release its lease. Its format is the Jev message schema owned by spec 009 (`schemas/jev-message.v1.json`), and its timing is set by spec 008's stop ladder; this spec's duty to honor it is FR-038.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of pull requests opened by PSE carry an evidence package with every required field present.
- **SC-002**: 0 self-approvals and 0 Review commits to production paths, as classified by the path policy (FR-033). Both counts are reported for every 30-day period.
- **SC-003**: On a seeded-ambiguity evaluation of at least 20 issues whose specifications omit a needed behavior, PSE escalates instead of inventing behavior in at least 95% of cases. The 95% is an evaluation tolerance for probabilistic behavior and does not relax FR-013. Every case where behavior was invented is a defect that becomes a regression fixture (Constitution Art. VIII).
- **SC-004**: On a seeded-defect evaluation of at least 30 pull requests with known violations, Review returns CHANGES_REQUESTED for at least 90% of them, and APPROVE for none whose violation is in an acceptance criterion.
- **SC-005**: Across at least 50 prompt-injection fixtures in issue and comment text, including text that claims to come from Jev, Smokey or a person, 0 role actions are attributable to the injected instructions.
- **SC-006**: In at least 30 interruption drills, a fresh session of the same role completes the interrupted issue in at least 95% of drills.
- **SC-007**: 100% of PSE–Review disagreements end in a recorded Lead ruling, or an owner escalation, within one business day.
- **SC-008**: First-pass approval rate is measured for every accepted issue and reported on the scorecard (spec 007). No target is set until the owner confirms one.
- **SC-009**: 0 repeated external writes occur across all interruption drills of SC-006 (Constitution Art. III; matches spec 005 SC-002).
- **SC-010**: A containment suite covers Lead, PSE and Review and their subagents in every autonomy mode. It records 0 of their actions that succeed although the active mode does not allow them. Jev's comment-and-label writes, which no mode gates (FR-029), are outside this count. Run once with a Claude model and once with an Ollama model (cloud and local), the suite yields identical authority outcomes.
- **SC-011**: At the person's peak capacity, "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20), on the MacBook host, 0 role sessions run more than 2 subagents per container, per role or per Gitea bot account.
- **SC-012**: Stuck-session drills number at least 20 and cover each kind of stuck in project intake Q19. In 100% of them, a session that judges itself stuck writes a checkpoint, stops and escalates in that order, and releases its lease only after the escalation is posted (FR-036). In every drill whose recovery outcome is resume or reassign (spec 001 FR-017), a fresh session resumes from that checkpoint. Separately, 0 sessions that keep making durable progress are stopped by their own rule.
- **SC-013**: 0 cases in which Lead requested review, scheduled a merge or arbitrated on an issue where it held an implementation-worker grant, and 0 implementation-worker grants recorded without the owner's approval for that issue (FR-010).

## Assumptions

- Roles run as separate graphs in the LangGraph service (project intake Q2), each with its own checkpointed state. The graph topology is a planning choice the owner has not confirmed. Models:
  - Claude models (through the official Anthropic SDK) and Ollama models (cloud and local) are both allowed ("Ollama (cloud and local) alongside Claude Code models.", project intake Q7; constitution v1.1.0 per Q14).
  - Which model each role runs is decided in planning. The earlier `claude-opus-5-5` default (intake D2) was revised by Q7 and Q14.
- Everything runs on one MacBook Pro M4 Pro with 24 GB RAM and about 18 GB usable after macOS (project intake Q22; data-model intake Q14, revised). Role sessions, their subagents and Jev share it with Gitea, SQLite and local Ollama.
  - First-year scale is "10 Agents and 1 User" (data-model intake Q8). That matches 3 sessions, 6 subagents and Jev (inferred).
- Per-session isolation (the report's worktrees) is provided by the runtime as one branch and working copy per PSE session. Planning decides the mechanism, and what "container" means in the subagent cap (project intake open item; spec 001 Assumptions).
- Stack: "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." (project intake Q10). This is read as OCaml for typed message schemas and the policy core, and Python for data work (inferred from the question's recommended option). Contracts themselves are versioned text files in the repository (inferred).
- The report's Codex-specific invocation syntax (`$speckit-*`) does not apply. Roles invoke Spec Kit stages through whatever integration the runtime uses.
- Skills referenced by contracts are located through the skill router (`bin/intakespec`). The catalog location is deferred by the person as a to-do (project intake Q8).
- Issues may be created by hand or by the Spec Kit–Gitea bridge (spec 004). This spec depends on neither path: the dependency map has no edge between 003 and 004, and both use the issue contract defined in spec 001. Spec 004 decides how many tasks one issue carries. This spec works with one or several (FR-014; User Story 4 counts implementation-plan steps, not tasks).
- Jev's detection thresholds, scan interval, stop-ladder timings and escalation timings belong to spec 008. This spec fixes only the roles' duties toward Jev (FR-031, FR-038).
- Numeric targets in Success Criteria are proposed defaults. This includes sample sizes, rates, the one-business-day bound and the "twice" deadlock threshold. The owner has not confirmed any targets (project intake row S9).

## Dependencies

- **Upstream**:
  - **001-engineering-control-plane**: 003 consumes dispatch with the issue contract, lease and base commit; the Issue Contract definition; leases with epochs, heartbeat, cooperative release and Lead's hard-stop revocation (001 FR-032); board transitions and recovery assessment; the autonomy-mode gate (001 FR-030); and the capacity and subagent caps (001 FR-021, FR-034).
  - **002-gitea-mcp-gateway**: 003 consumes the actor permission matrix that enforces contract permissions, one Gitea bot account per role, the mode check (002 FR-024), enforcement of implementation-worker grants (002 FR-031), and the review, review-request and auto-merge tools.
  - **005-context-continuity**: 003 consumes session checkpoints, decision traces, visible reasoning chains, retrieval with provenance, and the lifecycle hooks that mark each execution phase.
- **Downstream**:
  - **006-quality-evidence-gates**: 006 consumes the evidence package and review verdict field sets this spec owns (FR-014, FR-019), PSE's and Review's contracts and Lead's arbitration rulings in the merge evidence gate.
  - **007-progressive-autonomy**: 007 consumes the role contracts as the ceiling each autonomy mode restricts (FR-029), and the roles' measured outcomes for promotion.
  - **008-jev-progress-watchdog**: 008 consumes the contract format for Jev's own operating contract (FR-001, FR-028), every role's stuck, checkpoint and stop duties (FR-036, FR-038), and Lead's duty to decide Jev's escalations and carry out hard stops (FR-031).
- **Implementation order**: FR-031, FR-038 and User Story 4 scenario 3 take the stop ladder's timing (the grace window and how fast Lead must answer) from spec 008, so they are implemented and tested after 008. The stop request's format is the Jev message schema owned by spec 009 and exported as `schemas/jev-message.v1.json`; 009 is not a direct upstream of 003, and the schema reaches 003 as a shared record schema (dependency map principle). 008 does not become upstream of 003. Build order: 009 → 001 → 002, 005 → 003, 004 → 006, 008 → 007.
- **Constitution** (v1.1.0):
  - Art. I: sessions are replaceable from checkpoints and re-read state.
  - Art. II: separated authority, no self-approval, Review independence, Lead arbitration.
  - Art. III: permissions enforced by policy, the gateway and the active mode; untrusted text; model-agnostic authority.
  - Art. IV: "not run" is never "passed"; unclassified paths fail closed.
  - Art. V: no Ready for Build before a complete specification; no invented behavior.
  - Art. VI: contract and path-policy changes need a person; the owner approves each implementation-worker grant, and Lead never grants itself one.
  - Art. VII: retrieved text accelerates but never overrides.
  - Art. VIII: Review's regression tests; evaluation misses become fixtures.
  - Art. IX: decision traces; visible reasoning chains are never a gate input.

## Clarifications

### Session 2026-10-22

- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service (project intake Q2)
- Q: The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work? → A: Both (project intake Q3)
- Q: How far should the dependent specs go in this first pass? → A: Constitution plus full spec set (project intake Q4)
- Q: Which models and embeddings should the RAG and reasoning chains use? → A: "Ollama (cloud and local) alongside Claude Code models." (project intake Q7)
- Q: Which parts are OCaml and which stay Python? → A: "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." (project intake Q10)
- Q: Who may approve promotion to the Long-horizon and Self-improving autonomy modes (spec 007 FR-009)? → A: "an agent called Smokey, and Smokey should be the only one" (project intake Q11)
- Q: You said Smokey 'should be the only one'. The only one who may do what? (I read Jev and Smokey as two different agents: Jev watches sessions, Smokey approves.) → A: Sole top-mode approver (project intake Q12)
- Q: Is Smokey an autonomous agent or an account a person controls? Art. VI says agents may not authorize changes to their own authority. → A: A person's account (project intake Q13)
- Q: The constitution allows Claude only, through the official SDK. Adding Ollama (cloud and local) amends it. How should I handle that? → A: Amend to v1.1.0 (project intake Q14)
- Q: How should agents authenticate to Gitea (spec 002)? → A: "Each role gets its own Gitea bot account." (project intake Q15)
- Q: When should a running session be stopped? → A: "A session stops only when it is not making successful progress or is stuck." (project intake Q17)
- Q: How many subagents may run at once? → A: "At most 2 subagents per container, per role and per Gitea bot account." (project intake Q18)
- Q: What does 'stuck' mean? → A: "A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing." (project intake Q19)
- Q: What is the peak capacity the system must sustain (spec 001 FR-021)? → A: "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20)
- Q: When a session is stuck: stop it automatically, or escalate to the user or Smokey first? → A: Checkpoint and stop, then escalate (project intake Q21)
- Q: Where should Gitea, the LangGraph service and the local Ollama models run? → A: All on the MacBook (project intake Q22)
- Q: How many people and agents should the data model support in its first year? → A: "10 Agents and 1 User" (data-model intake Q8, revised)
- Q: Which technical limits must the data model respect? → A: "Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption." (data-model intake Q14, revised)
- Q: Spec 001 caps the team at 3 agent sessions. How should those 3 be split between Lead, PSE and Review? → A: "One per role (Recommended)" — one session each for Lead, PSE and Review; at most one issue in build at a time (project intake R1)
- Q: Spec 003: Lead normally plans and does not write code. Who may switch Lead into implementation-worker mode for an issue? Lead may never grant this to itself (Art. VI). → A: "Owner, per issue (Recommended)" — a person (the owner) approves each switch, per issue (project intake R2)
