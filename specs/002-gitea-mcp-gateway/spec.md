# Feature Specification: Gitea MCP Gateway

**Feature Branch**: `002-gitea-mcp-gateway`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "An MCP server that wraps the Gitea REST API with a narrow semantic tool surface and authority boundaries; every mutation carries actor role, session, issue, expected version, idempotency key and reason" (report §Gitea as the real-time engineering control plane)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A narrow, semantic tool surface (Priority: P1)

Lead, PSE and Review touch Gitea only through a fixed set of meaningful tools — get, create, update, comment on and assign issues; read and set dependencies; read the project board and move issues across it; read, create, inspect, request review of, review, check and schedule auto-merge for pull requests; read branch protection; claim, renew and release leases. There is no tool that sends an arbitrary request, writes branch protection, or force-merges.

**Why this priority**: The gateway is where authority boundaries become real (Constitution Art. III). A generic request tool would let any prompt reach any endpoint, and every other control in this design would be advisory.

**Independent Test**: List the tools the gateway exposes and compare against the approved list; attempt to call an unlisted operation (raw request, branch-protection write, force merge) and confirm it does not exist.

**Acceptance Scenarios**:

1. **Given** a connected role session, **When** it lists available tools, **Then** it sees exactly the approved tools permitted for its role and no generic request tool.
2. **Given** any role, **When** it asks to change branch protection or force a merge, **Then** no tool exists for it and the attempt is recorded as an unauthorized-action attempt.
3. **Given** a session reads an issue, **When** the gateway returns it, **Then** the issue body and comments are marked as untrusted content.

---

### User Story 2 - Every mutation is authorized, idempotent and attributable (Priority: P1)

Each write names who is acting (role and session), on what issue, against which version of the record, under which idempotency key, and why. The gateway checks the role's authority for that tool, checks that the session holds the lease for the issue where a lease is required, and checks the expected version. A retried call with the same idempotency key returns the original result instead of acting twice.

**Why this priority**: Repeated writes after a success, stale writes and writes by the wrong role are the long-horizon failure modes the report singles out; this story prevents all three at the boundary.

**Independent Test**: Run a permission-containment suite that calls every tool as every role, with and without a lease, with fresh and stale versions, and with repeated idempotency keys; compare outcomes with the permission matrix.

**Acceptance Scenarios**:

1. **Given** a PSE session holding the lease for issue 184, **When** it moves 184 from In Progress to Review with a fresh `expected_version`, **Then** the move succeeds and is recorded with its envelope.
2. **Given** the same call is retried with the same idempotency key, **When** the gateway receives it, **Then** it returns the original result and Gitea is not called again.
3. **Given** the same idempotency key with a different payload, **When** the gateway receives it, **Then** the call is refused as a key conflict.
4. **Given** a PSE session, **When** it calls the pull-request review tool on a pull request it authored, **Then** the call is refused: no role approves its own work (Constitution Art. II).
5. **Given** a stale `expected_version`, **When** a mutation arrives, **Then** it is refused with the current version so the caller can re-read and re-decide.

---

### User Story 3 - Verified external state (Priority: P2)

After every mutation the gateway re-reads the affected Gitea object and returns what is actually there. If the observed state does not match what the mutation should have produced, the call reports a verification failure instead of success.

**Why this priority**: A successful tool response does not prove the objective succeeded (report §Agentic-framework verification, tool correctness). Agents must be able to rely on returned state.

**Independent Test**: Use a Gitea test double that accepts a write but silently leaves the object unchanged; confirm the gateway reports a verification failure and the control plane does not record the transition.

**Acceptance Scenarios**:

1. **Given** an issue move that Gitea accepts, **When** the gateway re-reads the board, **Then** the response includes the observed column and version.
2. **Given** Gitea reports success but the issue is still in its old column, **When** the gateway verifies, **Then** it returns a verification failure and records it.

---

### User Story 4 - Merge through policy, never around it (Priority: P3)

Lead asks for a pull request to merge only by scheduling auto-merge when checks succeed. Gitea's protected-branch rules — required approvals, blocking requested changes, dismissing stale approvals, requiring the branch to be current, required status checks, no administrator bypass — decide whether and when the merge happens. The gateway exposes branch protection only for reading, so agents can explain why a merge is waiting.

**Why this priority**: Autonomous merge is safe only when it is policy-mediated (report §Safe autonomous merge). It depends on stories 1 and 2.

**Independent Test**: Schedule auto-merge on a pull request with a failing required check and confirm it does not merge; let the check pass and confirm Gitea merges it without any further agent call.

**Acceptance Scenarios**:

1. **Given** a pull request with a passing review and a pending required check, **When** Lead schedules auto-merge, **Then** the merge is scheduled and happens only after the check succeeds.
2. **Given** a pull request whose risk class is High, **When** Lead schedules auto-merge without a recorded human approval, **Then** the gateway refuses the call with reason "human approval required".

---

### User Story 5 - A complete audit trail (Priority: P3)

Every tool call — allowed, refused or failed — is recorded with its envelope, the role's authority decision, the Gitea operations performed and the verified result, so that any write can be traced to the session and reason that caused it.

**Why this priority**: Unauthorized-action attempts blocked is a scorecard metric (report §Core metrics), and incident review needs attribution.

**Independent Test**: Run the containment suite, then query the audit trail for each call and confirm it is present with its outcome.

**Acceptance Scenarios**:

1. **Given** a refused call, **When** the audit trail is queried by session, **Then** the call appears with the refusal reason.

---

### Edge Cases

- **Duplicate mutation**: a session or a retried event repeats a write after it already succeeded; the idempotency key returns the first result and Gitea is not called again.
- **Transient Gitea errors**: Gitea times out or returns a server error; the gateway retries idempotent reads and envelope-keyed writes with bounded backoff and reports a retryable error after the limit — never a false success.
- **Lease expired mid-call**: a mutation arrives after its lease expired; it is refused and the caller is told the lease state.
- **Nested authority**: a subagent started by a PSE session asks for a Review-only tool; subagents never hold more authority than their parent.
- **Prompt injection in issue text**: an issue body returned by the issue tool contains instructions to approve or merge; the content is labeled untrusted and the gateway's authority checks are unaffected by it.
- **Self-review**: the session or role that authored a pull request tries to approve it; refused.
- **Rate limiting**: Gitea throttles requests; the gateway backs off and surfaces a retryable error with a retry-after hint.
- **Version skew**: the Gitea instance is older than the supported 28.x release; the gateway refuses to start and reports the version.
- **Stale approvals**: Gitea dismisses an approval after a new push; the pull-request tools report the approval as stale rather than current.

## Requirements *(mandatory)*

### Functional Requirements

**Tool surface**

- **FR-001**: Gateway MUST expose exactly these tools: `gitea.issue.get`, `gitea.issue.create`, `gitea.issue.update`, `gitea.issue.comment`, `gitea.issue.assign`, `gitea.issue.dependencies.get`, `gitea.issue.dependencies.set`, `gitea.project.get`, `gitea.project.move_issue`, `gitea.pr.get`, `gitea.pr.create`, `gitea.pr.changed_files`, `gitea.pr.request_review`, `gitea.pr.review`, `gitea.pr.checks`, `gitea.pr.enable_auto_merge`, `gitea.branch.protection.get`, `coordination.lease.claim`, `coordination.lease.renew`, `coordination.lease.release`.
- **FR-002**: Gateway MUST NOT expose any tool that sends an arbitrary method, path and body to Gitea, writes branch protection, merges immediately or bypasses required checks (Constitution Art. III, VI).
- **FR-003**: Adding, removing or widening a tool MUST be treated as a Critical-risk change requiring human approval (Constitution Art. VI).
- **FR-004**: Lease tools MUST delegate to the control plane's lease service (spec 001) rather than keep a separate lease record.

**Authority**

- **FR-005**: Gateway MUST enforce a role permission matrix: Lead — issues, dependencies, project state, assignment, review requests and policy-mediated merge scheduling; PSE — its assigned issues, branches and pull requests, issue comments and implementation-state transitions (In Progress → Review, Changes Requested → Review); Review — pull-request reviews, QA comments, QA issues and review-state transitions (Review → Changes Requested, Review → Ready to Merge request).
- **FR-006**: Gateway MUST refuse a review approval from the role or session that authored the pull request, and from any session acting for that author (Constitution Art. II).
- **FR-007**: Gateway MUST require a valid lease for PSE mutations on an issue and MUST refuse them when the session does not hold the lease.
- **FR-008**: Gateway MUST bound a subagent's authority by its parent session's authority and MUST record the parent on every subagent call.
- **FR-009**: Gateway MUST refuse to schedule auto-merge for a High or Critical risk pull request unless a human approval is recorded on it.

**Mutation envelope**

- **FR-010**: Gateway MUST reject any mutation missing `actor_role`, `session_id`, `issue_id`, `expected_version`, `idempotency_key` or `reason`.
- **FR-011**: Gateway MUST return the first recorded outcome for a repeated idempotency key with an identical payload and MUST refuse a repeated key with a different payload.
- **FR-012**: Gateway MUST refuse a mutation whose `expected_version` does not match the current record and MUST include the current version in the refusal.
- **FR-013**: Gateway MUST keep idempotency records for at least [NEEDS CLARIFICATION: how long idempotency keys stay valid — must outlast the longest retry and webhook redelivery window, which the report does not state].

**Verification and safety**

- **FR-014**: Gateway MUST re-read the affected object after every mutation and return the observed state; a mismatch MUST be reported as a verification failure, not success.
- **FR-015**: Gateway MUST label free text it returns from Gitea (issue bodies, comments, review text, commit messages, file names) as untrusted content.
- **FR-016**: Gateway MUST hold the Gitea credentials itself; tokens MUST never appear in tool inputs, outputs, logs or errors visible to agents.
- **FR-017**: Gateway MUST act in Gitea as [NEEDS CLARIFICATION: one bot account per role, or one gateway account with the role recorded only in the audit trail — affects how Gitea's own review rules see "independent" approval].
- **FR-018**: Gateway MUST classify errors as retryable (timeouts, server errors, rate limits) or final (authorization, validation, version conflict), retry retryable ones with bounded backoff, and never report success for an unverified write.
- **FR-019**: Gateway MUST verify on startup that the Gitea instance runs a supported 28.x release (28.2.0 or later) and refuse to start otherwise.
- **FR-020**: Pull-request tools MUST report each approval with the commit it applies to and whether Gitea considers it stale.
- **FR-021**: `gitea.pr.enable_auto_merge` MUST only schedule a merge to occur when Gitea's required checks succeed; it MUST never merge immediately.

**Audit**

- **FR-022**: Gateway MUST append an audit record for every call — allowed, refused or failed — holding the envelope, the authority decision, the Gitea operations performed and the verified result.
- **FR-023**: Gateway MUST count refused calls by role, tool and reason so the scorecard can report unauthorized-action attempts blocked (spec 007).

### Key Entities

- **Tool**: a named semantic operation, its input schema, the roles allowed to call it, whether it needs a lease, and whether it mutates.
- **Role Permission Matrix**: for each role, the tools and board transitions it may use.
- **Mutation Envelope**: `actor_role`, `session_id`, `issue_id`, `expected_version`, `idempotency_key`, `reason` (shared with spec 001).
- **Idempotency Record**: key, payload hash, first outcome, time recorded.
- **Authority Decision**: allow or refuse, with the rule and reason.
- **Verified Result**: the observed Gitea state after a mutation and whether it matched the intended change.
- **Audit Record**: one tool call with envelope, authority decision, Gitea operations and verified result.
- **Untrusted Content**: any Gitea free text returned to an agent, wrapped and labeled.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A permission-containment suite covering every role × tool pair, with and without leases, records 0 successful unauthorized mutations.
- **SC-002**: Replaying each mutation in a 500-call suite between two and five times produces exactly one external Gitea effect per idempotency key (100%).
- **SC-003**: 100% of mutations return an observed post-state; in a fault-injection suite where Gitea silently drops at least 20 writes, 100% are reported as verification failures.
- **SC-004**: A scan of all agent-visible tool outputs, logs and errors over a 30-day window finds 0 Gitea credentials.
- **SC-005**: 0 pull requests merge without their required checks passing, and 0 High or Critical risk pull requests merge without a recorded human approval.
- **SC-006**: 100% of tool calls, including refused ones, appear in the audit trail within 5 seconds.
- **SC-007**: 95% of read tools return within 2 seconds when Gitea itself responds within 1 second.

## Assumptions

- The gateway speaks the Model Context Protocol to the LangGraph service's role agents and the Gitea REST API to Gitea; agents never call Gitea directly.
- Gitea 28.x supports the issue, dependency, project-column, pull-request, review, changed-files, merge-status and scheduled-merge operations the tools need (report §Gitea as the real-time engineering control plane).
- Branch protection is configured by humans outside the agent system and read-only to it.
- Retry defaults: 5 attempts with exponential backoff capped at 2 minutes, matching spec 001.
- Risk class is read from the issue contract set by Lead (spec 001) and confirmed by the evidence gate (spec 006).
- Implementation language and hosting are decided during planning (project intake open items).

## Dependencies

- **Upstream**: 001 (lease service, mutation envelope, idempotency semantics, board transitions).
- **Downstream**: 003 (role contracts are enforced here), 004 (the bridge creates and links issues through these tools), 006 (merge evidence gate reads checks, reviews and merge status here), 007 (unauthorized-action attempts blocked).

## Clarifications

### Session 2026-10-22

- Q: The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target? → A: Gitea only
- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service
