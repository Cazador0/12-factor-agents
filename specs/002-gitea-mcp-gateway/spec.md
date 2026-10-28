# Feature Specification: Gitea MCP Gateway

**Feature Branch**: `002-gitea-mcp-gateway`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Write related and dependent new "spec" using the file I attached here." (project intake, Idea). This spec covers the attached report's §Gitea as the real-time engineering control plane: "The MCP server should wrap the Gitea REST API", a narrow semantic tool surface, and a mutation envelope on every write. The person's later answers on Gitea bot accounts (project intake Q15) and event retention (project intake Q16) refine it, and so do the specify-phase decisions. Four of them change the gateway's behavior: human-approved plan writes in Shadow mode (project intake, R3), read-only issue search and milestone lookup (project intake, R4), a lease-epoch commit status that branch protection requires (project intake, R7) and per-role `jev/` labels beside the summary label (project intake, R8). Three more are recorded for traceability: one session per role (project intake, R1; US2 scenario 14), the owner's per-issue grant of implementation-worker mode (project intake, R2; FR-031) and the project's headline autonomy target (project intake, R5; Assumptions).

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A narrow, semantic tool surface (Priority: P1)

Lead, PSE, Review, the control plane (`system`, spec 001 FR-031) and Jev (the progress watchdog, spec 008) touch Gitea only through a fixed set of meaningful tools. With those tools they can:

- get, search, create, update, comment on, assign and label issues;
- look up milestones;
- read and set dependencies;
- read the project board and move issues across it;
- read, create, update, inspect, request review of, review, check and schedule auto-merge for pull requests;
- read the checks of a commit;
- post the `lease-epoch` status that branch protection requires (project intake, R7), which only the control plane posts, and only on the head of an agent branch (inferred, FR-038);
- read branch protection and create agent branches;
- claim, renew, release and revoke leases.

No tool sends an arbitrary request, writes branch protection, pushes to or deletes a branch, creates labels, posts any other commit status or force-merges. Each actor sees only the tools its row of the permission matrix allows. Jev sees read tools plus the comment and label tools, and nothing that can push, approve, merge or post a status.

**Why this priority**: The gateway is where authority boundaries become real (Constitution Art. III). A generic request tool would let any prompt reach any endpoint, and every other control in this design would then be advisory.

**Independent Test**: List the tools the gateway exposes to each actor and compare them with the permission matrix (FR-005). Then try to call each unlisted operation and confirm it does not exist: a raw request, a branch-protection write, a push or branch deletion, label creation, a force merge and, for every actor other than the control plane, any commit status. The control plane's status tool does exist, so test it separately: a `system` call that carries any status context field is refused before any Gitea write and audited (FR-038).

**Acceptance Scenarios**:

1. **Given** a connected session of any actor, **When** it lists the available tools, **Then** it sees exactly the approved tools its `actor_role` may call and no generic request tool.
2. **Given** any actor, **When** it asks to change branch protection or force a merge, **Then** no tool exists for it and the attempt is recorded as an unauthorized-action attempt.
3. **Given** a session reads an issue, **When** the gateway returns it, **Then** the issue body and comments are marked as untrusted content.
4. **Given** the Jev session, **When** it lists tools and then tries to add the label `risk:low`, **Then** it sees only read tools, `gitea.issue.comment` and the two label tools, and the label call is refused because Jev may touch only labels in the `jev/` scope (FR-027). **When** it adds the role label `jev/pse/stuck`, **Then** the call is allowed, because every label whose name begins with `jev/` is in Jev's scope (project intake, R8; reading the scope as the name prefix is inferred, FR-027).
5. **Given** the Jev bot account has been given push or merge permission in Gitea, **When** the gateway starts, **Then** it refuses every call made as Jev and reports which permission must be removed.
6. **Given** a Review session approves a pull request that a PSE session authored, **When** Gitea records the review, **Then** the approval comes from the Review bot account, which Gitea counts as independent of the PSE bot account that authored the pull request (FR-017).
7. **Given** the Lead session, **When** it searches issues by a task identifier and looks up the feature's milestone by name, **Then** it receives the matching issues and the milestone, their free text is marked untrusted, and nothing is written to Gitea (FR-001, FR-015; project intake R4).
8. **Given** Guarded autonomous mode, which allows `system` writes, and the control plane (`system`) and every other actor, **When** each lists its tools, **Then** only `system` sees `gitea.commit.set_lease_epoch_status`. **When** `system` calls it with any status context field, or on a commit that is not the current head of an agent branch, **Then** the call is refused before any Gitea write and audited, and the refusal names the context or head check, not the mode (FR-038; project intake, R7; the tool's design is inferred).

---

### User Story 2 - Every mutation is authorized, idempotent and attributable (Priority: P1)

Each write names five things:

- who is acting: the role and session, plus the parent session when the caller is a subagent;
- the issue it acts on;
- the issue version it was decided against, and the lease epoch when it writes under a lease;
- its idempotency key;
- why it is made.

The gateway checks the active autonomy mode and the actor's authority for that tool. Where a lease is required, it checks that the session holds the current lease. It also checks the expected version. A retried call with the same idempotency key returns the original result instead of acting twice, whether the first write came through the gateway or through the control plane.

**Why this priority**: The report singles out one long-horizon failure mode here: "an agent or retried event repeating a write after it has already succeeded" (report §Gitea as the real-time engineering control plane). This spec adds two more that the report's verification questions raise: stale writes (report §Agentic-framework verification, Concurrency) and writes by the wrong role (same section, Permission containment). This story stops all three at the boundary. The first release runs in Shadow mode, where humans perform the consequential mutations (project intake D9; spec 007 FR-002), or approve the bridge's plan for the gateway to carry out (project intake R3; FR-037). The mode check is what keeps agents read-only on day one.

**Independent Test**: Run a permission-containment suite that calls every tool as every actor and as each actor's subagents. Cover every autonomy mode, calls with and without a lease, current and older lease epochs, fresh and stale versions, repeated idempotency keys, and plan writes with and without a person's approval. Compare the outcomes with the permission matrix (FR-005) and the mode rules (FR-024, FR-025, FR-037).

**Acceptance Scenarios**:

1. **Given** a PSE session holding the write lease for issue 184 in a mode that allows PSE writes, **When** it moves 184 from In Progress to Review with a fresh `expected_version`, **Then** the move succeeds and is recorded with its envelope.
2. **Given** the same call is retried with the same idempotency key, **When** the gateway receives it, **Then** it returns the original result and Gitea is not called again.
3. **Given** the same idempotency key with a different payload, **When** the gateway receives it, **Then** the call is refused as a key conflict.
4. **Given** a PSE session, **When** it calls the pull-request review tool on a pull request it authored, **Then** the call is refused: no role approves its own work (Constitution Art. II).
5. **Given** a stale `expected_version`, **When** a mutation arrives, **Then** it is refused with the current version so the caller can re-read and re-decide.
6. **Given** Shadow mode is active, or no mode is recorded at all, **When** a PSE session that holds a lease tries to move its issue, **Then** the call is refused with "mode: shadow" and the refusal is audited.
7. **Given** a subagent of PSE session S, **When** it calls `gitea.pr.review`, **Then** the call is refused because the parent's authority does not include reviews, and the audit record names S as the parent.
8. **Given** the capacity registry already shows two active subagents under the PSE bot account, **When** a third subagent of a PSE session calls any tool, **Then** the call is refused and the refusal names the cap of 2 (project intake Q18).
9. **Given** Lead creates an issue for a new task with `issue_id` set to the feature's tracking issue (or `new` when there is none) and `expected_version` set to `absent`, **When** the gateway receives it, **Then** the envelope is complete and the call is decided on authority and mode alone.
10. **Given** the control plane already wrote under idempotency key K, **When** a gateway call arrives with key K and the same payload, **Then** the original outcome is returned and Gitea is not called again (one shared store, FR-032).
11. **Given** Jev posted an escalation comment carrying episode marker M, and Jev has since restarted, **When** it posts again with marker M, **Then** the gateway edits that comment in place and no second comment appears.
12. **Given** Lead holds the write lease for issue 190 as an implementation worker (spec 003 FR-010), in a mode that allows PSE writes (for example Agent implementation), **When** it creates a pull request for 190, **Then** the pull request is created. **When** it then requests review of that pull request or schedules its auto-merge, **Then** both calls are refused, and the refusal says that a person takes those steps in Gitea directly (FR-031).
13. **Given** Lead revoked a stuck PSE session's lease as the hard-stop step (spec 001 FR-032), **When** that session's late write arrives with the older lease epoch, **Then** the gateway refuses it as not holding the lease.
14. **Given** an equivalent call made first by a PSE session running a Claude model and, after that session stops, by the next PSE session running a local Ollama model (one PSE session at a time, project intake, R1), each call presenting its own session's current lease epoch, a fresh `expected_version` and its own idempotency key, **When** the gateway decides, **Then** both receive the same authority decision.
15. **Given** an idempotency key first used long before, older than any retry or webhook redelivery window, **When** the same call is replayed, **Then** the original outcome is still returned, because idempotency records never expire (FR-013).
16. **Given** Shadow mode and a bridge plan that a person's Gitea account approved (spec 004 FR-022), **When** Lead's bridge run sends one of the plan's issue creations with the approval reference, **Then** the issue is created through Lead's bot account, and the audit record names the approving account, the plan fingerprint and the mode (FR-037; project intake R3).
17. **Given** the same approved plan, **When** Lead sends a write whose tool, payload or idempotency key matches no entry of the plan, or schedules an auto-merge, **Then** the call is refused with "mode: shadow" (FR-037).
18. **Given** Shadow mode and a plan approval recorded by a bot account rather than a person's account, **When** Lead sends a plan write that cites it, **Then** the call is refused with "mode: shadow", and the refusal says the approval is not a person's (FR-037).
19. **Given** a PSE session holding the write lease for issue 184 in Agent implementation mode, **When** it updates the body of 184, **Then** the update succeeds. **When** it updates issue 185, which it does not lease, or tries to close 184, **Then** both calls are refused (FR-005).

---

### User Story 3 - Verified external state (Priority: P2)

After every mutation the gateway re-reads the affected Gitea object and returns what is actually there. If the observed state does not match what the mutation should have produced, the call reports a verification failure instead of success.

Labels and checks get the same care. Labels are added by ID, so a misspelled name can never vanish silently. A commit's check state covers every reported check, not just the first page of them.

**Why this priority**: A successful tool response does not prove the objective succeeded (report §Agentic-framework verification, tool correctness). Agents must be able to rely on returned state.

**Independent Test**: Use a Gitea test double that accepts a write but silently leaves the object unchanged. Confirm that the gateway reports a verification failure and that the control plane does not record the transition. Then add labels by name, including one unknown name, and read the checks for a commit that has more checks than fit on one page.

**Acceptance Scenarios**:

1. **Given** an issue move that Gitea accepts, **When** the gateway re-reads the board, **Then** the response includes the observed column and version.
2. **Given** Gitea reports success but the issue is still in its old column, **When** the gateway verifies, **Then** it returns a verification failure and records it.
3. **Given** an issue that carries `jev/warning`, `jev/pse/warning`, `jev/review/warning` and labels set by people, **When** Jev adds `jev/pse/stuck` by name and then `jev/stuck` by name, **Then** for each call the gateway:
   - sends the label's ID with the additive operation;
   - confirms that the returned label set contains that ID;
   - confirms that the one label Gitea's exclusive-scope rule replaces is gone, and treats that as the expected outcome: `jev/pse/warning` after the first call (scope `jev/pse`) and `jev/warning` after the second (scope `jev`);
   - confirms that every other label is still in place, including `jev/review/warning`, the labels people set and, after the second call, `jev/pse/stuck`, because a role label and the summary label never share an exclusive scope (FR-034; project intake, R8).
4. **Given** a label call that names a label which does not exist, **When** the gateway receives it, **Then** it refuses the call before any Gitea write and names the unknown label. Gitea never gets the chance to drop the name silently.
5. **Given** a commit with more reported checks than Gitea returns in one page, one of them `lease-epoch`, **When** `gitea.pr.checks` or `gitea.commit.checks` runs, **Then** the combined state covers every reported check, `lease-epoch` included, and the response also lists each context's latest status with its context, state, status id, description and commit (FR-036).
6. **Given** a label name defined both in the repository and in the organization, **When** a label call names it, **Then** the gateway refuses the call as ambiguous before any Gitea write and names both labels. Gitea would otherwise add both (FR-034).

---

### User Story 4 - Merge through policy, never around it (Priority: P3)

Lead asks for a pull request to merge only by scheduling auto-merge for when checks succeed. Gitea's protected-branch rules then decide whether and when the merge happens:

- required approvals;
- requested changes block the merge;
- stale approvals are dismissed;
- the branch must be current;
- required status checks must pass, including the `lease-epoch` status, once a person adds it to them (project intake, R7);
- no administrator bypass.

The gateway adds two checks of its own before it schedules a merge. First, the human approval required by the active mode and the pull request's risk class must be recorded. Second, that risk class must come from the classifier, never from issue text or a lowered label. The gateway exposes branch protection only for reading, so agents can explain why a merge is waiting.

**Why this priority**: Autonomous merge is safe only when it is policy-mediated (report §Safe autonomous merge). It depends on stories 1 and 2.

**Independent Test**: Schedule auto-merge on a pull request with a failing required check and confirm that it does not merge. Let the check pass and confirm that Gitea merges it without any further agent call. Repeat in each autonomy mode with Low-, Medium- and High-risk pull requests, with and without a recorded human approval. Then, in Guarded autonomous mode with `lease-epoch` required by branch protection, repeat with an agent-branch head whose `lease-epoch` status is failure or missing.

**Acceptance Scenarios**:

1. **Given** Guarded autonomous mode and a pull request whose computed risk class is Low, with a passing review and a pending required check, **When** Lead schedules auto-merge, **Then** the merge is scheduled and happens only after the check succeeds. (In Agent implementation mode the same outcome needs a recorded human approval on the head, FR-025.)
2. **Given** a pull request whose computed risk class is High, **When** Lead schedules auto-merge without a recorded human approval, **Then** the gateway refuses the call with reason "human approval required".
3. **Given** Guarded autonomous mode and a Medium-risk pull request with no human approval, **When** Lead schedules auto-merge, **Then** the call is refused with reason "human approval required" (spec 007 FR-004).
4. **Given** Agent implementation mode and a Low-risk pull request with no human approval, **When** Lead schedules auto-merge, **Then** the call is refused, because a human remains the merge authority in that mode (spec 007 FR-003).
5. **Given** an issue body or a label says the risk is Low while the computed class for the pull request's head is High, **When** Lead schedules auto-merge, **Then** the gateway uses High and refuses the call without a human approval. When the audit trail shows that an agent actor set the lowering label, the gateway counts it as an unauthorized-action attempt by that actor (FR-026).
6. **Given** no computed risk class is recorded for the pull request's current head, **When** Lead schedules auto-merge, **Then** the gateway treats the pull request as Critical and refuses the call without a human approval.
7. **Given** Guarded autonomous mode and a Low-risk pull request whose required checks already passed, **When** Lead schedules auto-merge, **Then** Gitea may merge at once under its own rules, and the gateway never sends a request that could merge before checks and branch protection pass.
8. **Given** a pull request that adds, removes or widens a gateway tool, so that its computed class is Critical, **When** Lead schedules auto-merge without a human approval, **Then** the call is refused (FR-003, FR-026).
9. **Given** Guarded autonomous mode, which allows `system` writes and merges, branch protection requires `lease-epoch`, and Lead has revoked a PSE session's lease (spec 001 FR-032), **When** that session's `git push`, still in flight, lands after the revocation a commit that records the revoked epoch, or no epoch, as the new head of its agent branch, and the control plane judges that head and posts `lease-epoch` failure, and Lead then schedules auto-merge with every human approval the mode and risk class need, **Then** Gitea never merges that head (FR-038; project intake, R7).
10. **Given** Guarded autonomous mode and the current head of an agent branch whose recorded epoch the lease service reports as older than the current epoch of its issue or part, **When** `system` asks the gateway to post `lease-epoch` success on it, **Then** the call is refused because the lease service does not confirm the epoch, not because of the mode; no status is written and the refusal is audited (FR-038).

---

### User Story 5 - A complete audit trail (Priority: P3)

Every tool call is recorded, whether it was allowed, refused or failed. Each record holds:

- the envelope;
- the caller's identity;
- the active mode;
- the authority decision;
- the Gitea operations performed;
- the verified result.

Any write can therefore be traced to the session and reason that caused it.

**Why this priority**: Unauthorized-action attempts blocked is a scorecard metric (report §Core metrics), and incident review needs attribution.

**Independent Test**: Run the containment suite, then query the audit trail for each call and confirm it is present with its outcome.

**Acceptance Scenarios**:

1. **Given** a refused call, **When** the audit trail is queried by session, **Then** the call appears with the refusal reason.
2. **Given** a call made by a subagent, **When** its audit record is read, **Then** it names the subagent, its parent session, the Gitea bot account used and the mode in effect.
3. **Given** the containment suite has run, **When** the scorecard asks for unauthorized-action attempts blocked, **Then** the gateway returns refusal counts by actor, tool and reason, and those counts match the audit trail (FR-023).

---

### Edge Cases

- **Duplicate mutation**: a session or a retried event repeats a write after it already succeeded. The idempotency key returns the first result, and Gitea is not called again.
- **Crash between write and record**: the gateway posts a comment, then stops before it records the outcome. On retry it finds its own comment by account and marker and edits it in place, instead of posting a second comment (FR-035).
- **Transient Gitea errors**: Gitea times out or returns a server error. The gateway retries idempotent reads and envelope-keyed writes with bounded backoff, and after the limit reports a retryable error. It never reports a false success.
- **Overload**: Gitea 28.2 has no built-in API rate limiter, so the gateway paces its own requests to protect the shared MacBook host (research report §Least privilege; project intake Q22). If Gitea still answers slowly or with errors, the caller gets a retryable error with a retry-after hint.
- **Lease expired or revoked mid-call**: a mutation arrives after its lease expired or was revoked, or with an older lease epoch. It is refused, and the caller is told the lease state (spec 001 FR-032).
- **Late push from a stopped session**: a revoked session's `git push` was still in flight and lands a commit on its agent branch. Pushes do not pass through the gateway, so the gateway cannot refuse it. The control plane judges the new head, posts `lease-epoch` failure through `gitea.commit.set_lease_epoch_status`, and branch protection keeps the head from merging (FR-038; project intake, R7).
- **Commit with no recorded epoch**: the head of an agent branch whose commit records no lease epoch gets `lease-epoch` failure, never success (fail closed, Constitution Art. IV) (FR-038; spec 001 FR-038). Until the FR-038 marker is answered, that includes a commit a person adds to an agent branch, such as the merge commit of Gitea's update-branch action, so such a pull request cannot merge on that head.
- **Pull request from a branch a person pushed**: its head is not an agent branch's head, so the gateway posts no `lease-epoch` status on it, and a required check that never reports would keep it from merging. How such pull requests meet the check is open (FR-038).
- **Status posted outside the gateway**: Gitea lets any account with write access to the repository's code post a commit status, and it counts the latest status of a context. The gateway exposes the status write to `system` only, for `lease-epoch` only (FR-002, FR-038). Keeping every other credential that could post one away from agents is a planning matter (Assumptions: Branches).
- **Nested authority**: a subagent started by a PSE session asks for a Review-only tool. Subagents never hold more authority than their parent. A subagent missing from the capacity registry, or a third concurrent subagent under one bot account, is refused (FR-029, FR-030).
- **Prompt injection in issue text**: an issue body returned by the issue tool contains instructions to approve or merge, or claims a lower risk class. The content is labeled untrusted, and the gateway's authority and risk checks are unaffected by it (FR-015, FR-026).
- **Self-review**: a session acting for a pull request's author tries to approve it. The approval is refused (FR-006).
- **No mode recorded**: the mode record is missing or unreadable. The gateway treats the mode as Shadow and refuses agent mutations, except writes in a bridge plan a person approved (FR-024, FR-037).
- **No computed risk class**: the classifier has not yet scored the current head. The gateway treats the pull request as Critical (FR-026).
- **Mixed, unknown or ambiguous labels**: a label call mixes IDs and names, names a label that does not exist, or names a label defined in both the repository and the organization. Gitea would reject the mix, silently drop the unknown name or add both same-named labels, so the gateway resolves every name to exactly one ID first and refuses unknown and ambiguous names (FR-034).
- **Jev account over-privileged**: at startup, Gitea reports that the Jev account can push or merge. The gateway refuses to act as Jev until a person removes the permission (FR-027).
- **Version skew**: the Gitea instance is older than the supported 28.x release. The gateway refuses to start and reports the version.
- **Stale approvals**: Gitea dismisses an approval after a new push. The pull-request tools report the approval as stale rather than current.

## Requirements *(mandatory)*

### Functional Requirements

**Tool surface**

- **FR-001**: Gateway MUST expose exactly these tools.
  - Reads: `gitea.issue.get`, `gitea.issue.search`, `gitea.milestone.get`, `gitea.issue.dependencies.get`, `gitea.project.get`, `gitea.pr.get`, `gitea.pr.changed_files`, `gitea.pr.checks`, `gitea.commit.checks`, `gitea.branch.protection.get`.
  - Writes: `gitea.issue.create`, `gitea.issue.update`, `gitea.issue.comment`, `gitea.issue.assign`, `gitea.issue.labels.add`, `gitea.issue.labels.remove`, `gitea.issue.dependencies.set`, `gitea.project.move_issue`, `gitea.pr.create`, `gitea.pr.update`, `gitea.pr.request_review`, `gitea.pr.review`, `gitea.pr.enable_auto_merge`, `gitea.commit.set_lease_epoch_status`, `gitea.branch.create`, `coordination.lease.claim`, `coordination.lease.renew`, `coordination.lease.release`, `coordination.lease.revoke`.

  Nine of these tools are not in the report's list. Two were approved by a person as Critical-risk changes (FR-003): they rest on "Approve read-only search (Recommended)" (project intake, R4). A third, `gitea.commit.set_lease_epoch_status`, is read as approved by the person's answer "Both" (project intake, R7), which the intake records as asking for a lease-epoch commit status that branch protection requires. That answer serves as the human approval FR-003 requires for the one tool that posts it (inferred). R7's question asked where the fence lives and named no gateway tool, so this spec does not count the third tool as approved by a person. The tool names, and the third tool's placement in the System row only, are inferred.

  | Tool needing FR-003 approval | What it does | Serves | Approval |
  |---|---|---|---|
  | `gitea.issue.search` | Finds the repository's issues by feature or task identifier, or by label. Read-only. | Spec 004 FR-003, FR-011 and FR-024 | Approved by a person (project intake R4) |
  | `gitea.milestone.get` | Resolves a milestone by name and lists the issues on it (listing them is inferred from spec 004 FR-024). Read-only. | Spec 004 FR-024 | Approved by a person (project intake R4) |
  | `gitea.commit.set_lease_epoch_status` | Posts the commit status `lease-epoch`, success or failure, on the head of an agent branch. It writes that one status context and no other (FR-038). | Spec 001 FR-038 and FR-032, and spec 008 FR-029 step 5 (project intake, R7) | Approval inferred from "Both" (project intake, R7); the person has not named this tool |

  The other six are inferred additions that serve requirements of other specs or the report:

  | Added tool | Serves |
  |---|---|
  | `gitea.commit.checks`, `gitea.issue.labels.add`, `gitea.issue.labels.remove` | Jev (spec 008; research report) |
  | `gitea.pr.update` | The report's PSE permission `pull_requests: create_update` (report §Agent configuration philosophy) |
  | `gitea.branch.create` | The claim procedure's "Create the isolated branch" step (spec 001 FR-018) |
  | `coordination.lease.revoke` | Lead's hard-stop revocation (spec 001 FR-032) |
- **FR-002**: Gateway MUST NOT expose any tool that does any of the following (Constitution Art. III, VI):
  - sends an arbitrary method, path and body to Gitea;
  - writes branch protection;
  - pushes to or deletes a branch;
  - creates any branch other than an agent branch named `agent/<role>/<issue>-<slug>` (spec 001 FR-019);
  - creates or edits label definitions;
  - posts a commit status, other than the `lease-epoch` status that only `system` posts through `gitea.commit.set_lease_epoch_status` (FR-038);
  - merges immediately or bypasses required checks.
- **FR-003**: Adding, removing or widening a tool MUST be treated as a Critical-risk change requiring human approval (Constitution Art. VI).
- **FR-004**: Lease tools MUST delegate to the control plane's lease service (spec 001) for claims, renewals, releases, revocations and epoch checks, rather than keep a separate lease record.

**Authority**

- **FR-005**: Gateway MUST accept only these `actor_role` values and MUST refuse any other: `lead`, `pse`, `review`, `system` and `jev`. `system` is the control plane's own actor (spec 001 FR-031). `jev` is an inferred name for the watchdog (spec 008). Gateway MUST enforce this permission matrix. In the matrix, "all" means every listed actor, and "write lease" means the session's current write lease on the issue (spec 001 FR-015).

  | Tool | Kind | May call | Lease |
  |---|---|---|---|
  | Read tools (FR-001), including `gitea.issue.search` and `gitea.milestone.get` (project intake R4) | read | all | — |
  | `gitea.issue.create` | write | lead; review (QA issues only) | — |
  | `gitea.issue.update` | write | lead; pse (its leased issue only, never its open or closed state) | pse: write lease |
  | `gitea.issue.assign` | write | lead | — |
  | `gitea.issue.comment` | write | lead; pse (on its leased issue); review; system; jev (its own comments only) | pse: write lease |
  | `gitea.issue.labels.add` / `.remove` | write | lead (any label outside `jev/`); system (`Blocked` only); jev (`jev/` labels only: the summary and role labels, FR-027) | — |
  | `gitea.issue.dependencies.set` | write | lead | — |
  | `gitea.project.move_issue` | write | lead, pse, review and system, each only for the transitions it owns (below) | pse: write lease |
  | `gitea.branch.create` | write | system, at dispatch, from the recorded base commit (spec 001 FR-018) | write lease of the dispatched session |
  | `gitea.pr.create` | write | pse (for its leased issue) | write lease |
  | `gitea.pr.update` | write | pse (its own pull request on its leased issue) | write lease |
  | `gitea.pr.request_review` | write | lead | — |
  | `gitea.pr.review` | write | review (never when acting for the author, FR-006) | — |
  | `gitea.pr.enable_auto_merge` | write | lead | — |
  | `gitea.commit.set_lease_epoch_status` | write | system only, and only the `lease-epoch` context (FR-038; project intake, R7; the System row is inferred) | — |
  | `coordination.lease.claim` | write | system (write leases at dispatch); lead and review (their own non-write claims, spec 001 FR-015) | — |
  | `coordination.lease.renew` / `.release` | write | the holding session; system releases at recovery | holder |
  | `coordination.lease.revoke` | write | lead, only as the hard-stop step, with a reason and the stuck-verdict reference (spec 001 FR-032) | — |

  Each actor may make only the board moves that spec 001's transition table assigns to it:

  | Actor | Board moves it owns (spec 001 transition table) |
  |---|---|
  | lead | TR-01, TR-02 and TR-03; adding Blocked (TR-12) and removing it (TR-13) |
  | pse holding the write lease | TR-05 and TR-08 |
  | review | TR-06 |
  | system | TR-04, TR-07, TR-09, TR-10 and TR-11; adding Blocked after the retry limit or a "block" recovery outcome (TR-12) |
  | jev | none |

  The report gives Lead "reviews". This spec reads that as requesting reviews and scheduling policy-mediated merges, not submitting verdicts, because Review alone proves correctness and Lead never overrides a verdict (Constitution Art. II; spec 003 FR-008) (inferred).

  The report gives PSE "Assigned issues" and `issues: assigned_scope`, and spec 007 FR-003 lets PSE "update its assigned issues". Here an assigned issue is the issue PSE holds the write lease for. Two limits are this spec's own reading (inferred):
  - PSE's `gitea.issue.update` may not open or close the issue, because closing it would bypass Done, which only System reaches, on an observed merge (spec 001 TR-11). Text PSE writes into the issue never changes a risk class (FR-026).
  - PSE gets no label tool. Labels carry the risk class and the Blocked state, which Lead and the control plane own (FR-026; spec 001 TR-12, TR-13).
- **FR-006**: Gateway MUST refuse a review approval when the caller is acting for the pull request's author. Acting for the author means any of the following (Constitution Art. II):
  - (a) the session that authored the pull request;
  - (b) any subagent of that session;
  - (c) any session of the authoring role, which shares the authoring Gitea bot account (FR-017);
  - (d) a Lead session that held the write lease on the pull request's issue as an implementation worker (FR-031).
- **FR-007**: Gateway MUST require the current write lease for every PSE mutation on an issue, and for every Lead mutation on an issue where Lead holds the write lease as an implementation worker. A call under a lease MUST present the lease epoch. Gateway MUST refuse the mutation in any of these cases (spec 001 FR-024, FR-032):
  - the session does not hold the lease;
  - the lease expired or was revoked;
  - the presented epoch is older than the current one.

  Because "A session stops only when it is not making successful progress or is stuck." (project intake Q17), a lease has no maximum total duration. It stays valid for as long as heartbeats renew it (spec 001 FR-016).
- **FR-008**: Gateway MUST bound a subagent's authority by its parent session's authority and MUST record the parent on every subagent call. The gateway recognizes a subagent caller by the identity described in FR-029.
- **FR-009**: Gateway MUST refuse to schedule auto-merge unless the pull request's current head carries the human approval that the active mode and the pull request's computed risk class require (FR-025, FR-026). A human approval is an approving review by a person's Gitea account, not a bot account (inferred).

**Mutation envelope**

- **FR-010**: Gateway MUST reject any mutation missing `actor_role`, `session_id`, `issue_id`, `expected_version`, `idempotency_key` or `reason` (Constitution Art. III). The envelope schema is owned by spec 009. Every field has a defined value for every mutating tool:
  - `issue_id` is the work issue the call serves. For a pull-request, branch or lease tool, it is the issue the pull request, branch or lease belongs to. For `gitea.commit.set_lease_epoch_status`, it is the issue of the agent branch whose head is judged. For `gitea.issue.create`, it is the parent or tracking issue, or `new` when there is none.
  - `expected_version` is the issue's version, which the control plane keeps (spec 001 FR-024). For `gitea.issue.create` it is `absent`.
  - A call made under a lease also carries the lease epoch.
  - A human-approved plan write also carries the reference of the plan approval it relies on (FR-037).
  - `gitea.pr.review` and `gitea.pr.enable_auto_merge` also name the head commit they decided on. A different current head is refused as stale (inferred). `gitea.commit.set_lease_epoch_status` names the commit it judges and the lease epoch that commit records (FR-038).
- **FR-011**: Gateway MUST return the first recorded outcome for a repeated idempotency key with an identical payload, and MUST refuse a repeated key with a different payload.
- **FR-012**: Gateway MUST refuse a mutation whose `expected_version` does not match the issue's current version (Key Entities), and MUST include the current version in the refusal. A mutation whose `expected_version` is `absent` skips this comparison. Only `gitea.issue.create` may send `absent` (FR-010); any other tool that sends it is refused as an incomplete envelope.
- **FR-013**: Gateway MUST keep idempotency records for as long as events are kept. "Events have no time limit." (project intake Q16), so idempotency records are never expired or pruned (inferred from Q16).

**Verification and safety**

- **FR-014**: Gateway MUST re-read the affected object after every mutation and return the observed state. A mismatch MUST be reported as a verification failure, not success.
- **FR-015**: Gateway MUST label free text it returns from Gitea (issue bodies, comments, review text, commit messages, file names) as untrusted content.
- **FR-016**: Gateway MUST itself hold the Gitea credential of every bot account: one per role, plus Jev's and the control plane's (FR-017). Each call MUST use only the calling actor's own account. No token may ever appear in tool inputs, outputs, logs or errors visible to agents.
- **FR-017**: Gateway MUST act in Gitea as the calling actor's own bot account:
  - **Roles**: "Each role gets its own Gitea bot account." (project intake Q15). Lead, PSE and Review therefore each have one, and Gitea's own review rules see a Review approval as independent of the PSE's authorship.
  - **Jev**: Jev has its own bot account, which may only comment and label. It may not push, approve or merge (recorded with project intake Q15; research report §Least privilege).
  - **Control plane**: the control plane writes through its own bot account (spec 001 FR-031).
  - **Subagents**: a subagent acts through its parent's role account (spec 001 FR-034).
- **FR-018**: Gateway MUST classify errors as retryable (timeouts, server errors, overload) or final (authorization, validation, version conflict, lease, mode). It MUST retry retryable errors with bounded backoff, and MUST never report success for an unverified write. A retryable error that outlasts the retry limit MUST be recorded in the audit trail. Jev can then read repeated exhaustion as evidence that work "keeps failing" (project intake Q19; spec 008) (inferred).
- **FR-019**: Gateway MUST verify on startup that the Gitea instance runs a supported 28.x release (28.2.0 or later) and refuse to start otherwise.
- **FR-020**: Pull-request tools MUST report each approval with the commit it applies to and whether Gitea considers it stale.
- **FR-021**: `gitea.pr.enable_auto_merge` MUST only request Gitea's policy-gated merge-when-checks-succeed operation. It MUST NOT cause a merge before required checks and branch-protection rules pass.

**Audit**

- **FR-022**: Gateway MUST append an audit record for every call, whether allowed, refused or failed. The record schema is owned by spec 009. Each record holds:
  - the envelope;
  - the caller's identity: the bot account, plus the subagent and its parent session for a subagent;
  - the mode in effect;
  - the authority decision;
  - the Gitea operations performed;
  - the verified result;
  - for a human-approved plan write, the approval reference, the approving person's account and the plan fingerprint (FR-037).
- **FR-023**: Gateway MUST count refused calls by actor, tool and reason so the scorecard can report unauthorized-action attempts blocked (spec 007).

**Autonomy mode and risk**

- **FR-024**: On every mutation by `lead`, `pse`, `review` or `system`, or by a subagent of one of them, the gateway MUST read the active autonomy mode from the mode record. The modes and their per-action rules come from spec 007, and the record schema is owned by spec 009. The gateway MUST:
  - refuse any mutation the mode does not allow;
  - name the mode in the refusal;
  - audit the refusal.

  In Shadow mode, the gateway MUST refuse every Gitea mutation by these actors (spec 007 FR-002; spec 001 FR-030), except a human-approved plan write (FR-037; project intake R3). When no mode is recorded, or the record cannot be read, the gateway MUST treat the mode as Shadow (spec 007 US1 scenario 3; Constitution Art. IV).

  The gateway's own mode check does not refuse these calls:
  - Read tools, in every mode.
  - Lease tools, because leases are control-plane coordination records, not Gitea writes (inferred). The lease service those tools delegate to (FR-004) still applies spec 001 FR-030's autonomy-mode gate to write-lease grants. A write-lease claim in Shadow mode is therefore refused by the lease service, and the gateway returns that refusal with the mode named.
  - Jev's comment-and-label writes, in every mode, because they record observations rather than engineering work (inferred).
- **FR-025**: Gateway MUST require the following human approval before scheduling auto-merge:

  | Active mode | Human approval required on |
  |---|---|
  | Shadow, or no mode recorded | Not applicable: FR-024 refuses the request. A human-approved plan write never covers auto-merge (FR-037). |
  | Agent implementation | Every pull request ("a human MUST remain the merge authority", spec 007 FR-003) |
  | Guarded autonomous | Medium, High and Critical pull requests (spec 007 FR-004) |
  | Long-horizon, Self-improving | High and Critical pull requests (constitution risk table; spec 007 FR-005 "elevated-risk review MUST stay with humans", read as High and Critical (inferred)) |
- **FR-026**: Gateway MUST take a pull request's risk class from the class that spec 006's classifier computed for the pull request's current head commit. The computed-class record schema is owned by spec 009. The gateway MUST:
  - use the higher class when a risk label is also present;
  - never derive risk from issue-body or comment text (Constitution Art. III; spec 001 FR-006);
  - treat the pull request as Critical when no computed class is recorded for the current head (inferred: fail closed, Constitution Art. IV);
  - ignore a label or text that claims a lower class than the computed one (spec 006 FR-015);
  - when the audit trail shows that an agent actor set a lowering label, count it as an unauthorized-action attempt by that actor (inferred). Lowering text, and a label a person set, are ignored but not counted, because no agent actor is attributable.

**Identities and accounts**

- **FR-027**: Gateway MUST limit Jev to read tools, its own comments, and adding or removing labels in the `jev/` scope. That scope is every label whose name begins with `jev/`: the summary labels `jev/warning`, `jev/stuck` and `jev/parked`, and the nine role labels from `jev/lead/warning` to `jev/review/parked` (project intake, R8). Jev's write permission stays as the Jev report puts it: "Jev's write set should stay at its own comments and its `jev/*` labels." (research report §Jev proposes the stop; the policy owner carries it out). R8 names the 12 labels and does not change that permission. Reading the `jev/` scope as the name prefix, not Gitea's narrower exclusive scope of each label (FR-034), is inferred. Jev never posts a commit status (FR-038). At startup it MUST confirm that Gitea reports the Jev account can neither push nor merge on the default branch. If either check fails, it MUST refuse every call made as Jev (research report §Least privilege).
- **FR-028**: Gateway MUST confirm at startup that no bot account it holds is an administrator or can bypass branch protection. It MUST refuse to act for an account that fails the check (Constitution Art. VI) (inferred).
- **FR-029**: Every call from a subagent MUST carry the subagent's identity and its parent session, as registered in the control plane's capacity registry (spec 001 FR-034). The identity's fields are defined in spec 009's schemas. Gateway MUST refuse a subagent call whose registration is missing or whose parent session is not active.
- **FR-030**: Gateway MUST refuse calls from a subagent when they would make more than 2 subagents active under one role's bot account. The refusal MUST name the cap: "At most 2 subagents per container, per role and per Gitea bot account." (project intake Q18). This check is a backstop to the registry's own refusal (spec 001 FR-034) (inferred).
- **FR-031**: When Lead holds the write lease for an issue as an implementation worker, the gateway MUST give Lead the PSE row of FR-005 on that issue only. Spec 003 FR-010 decides who may put Lead in that mode: the owner, a person, approves each grant, per issue (project intake, R2). On that issue's pull requests, the gateway MUST refuse Lead's `gitea.pr.request_review` and `gitea.pr.enable_auto_merge` (spec 003 FR-010). No other actor holds those tools, so for those pull requests a person requests the review and schedules the merge in Gitea directly, under the same branch protection (inferred, matching spec 003 FR-010, where disputes on that issue go to a person). The refusal MUST say so.

**Shared records and models**

- **FR-032**: Gateway MUST keep idempotency records in the control plane's idempotency store (spec 001), under the record schema owned by spec 009, rather than in a store of its own. A key replayed through either the gateway or the control plane then yields one external effect.
- **FR-033**: Gateway MUST make every authority, mode, risk and lease decision in deterministic code. The decision MUST be the same whatever model the caller runs: Claude, or Ollama in the cloud or locally ("Ollama (cloud and local) alongside Claude Code models.", project intake Q7; Constitution Art. III).

**Labels, comments and checks**

- **FR-034**: Gateway MUST handle labels as follows (research report §Labels accept IDs or names):
  - send labels to Gitea only as IDs, never mixing IDs and names;
  - resolve names through a name-to-ID map built from every page of the repository's and the organization's labels;
  - refuse a call that names an unknown label, rather than let Gitea drop it silently;
  - refuse as ambiguous a call that names a label defined in both the repository and the organization, and name both labels, because Gitea would add both (research report §Labels accept IDs or names) (inferred: refuse rather than pick one, Constitution Art. IV);
  - add labels with Gitea's additive operation, never its replace-all operation, which would remove labels set by people or other agents;
  - remove labels one ID at a time;
  - confirm that the returned label set holds the expected IDs, and that the only labels gone are the ones the call removed and, for an added label in an exclusive scope, the other labels of that scope, which Gitea replaces (FR-014).

  An exclusive label's scope is the part of its name before the last `/` (Assumptions: Gitea 28.x API facts). The scope of `jev/stuck` is therefore `jev`, and the scope of `jev/pse/stuck` is `jev/pse`. Adding a role label never removes the summary label, adding the summary label never removes a role label, and each role's three labels replace each other (project intake, R8).
- **FR-035**: Gateway MUST embed a marker in every comment it posts: the call's upsert key when one is given, otherwise its idempotency key. When a call carries an upsert key, the gateway MUST edit the caller's own comment that carries that marker in place, instead of posting a new one. To find that comment, it uses the comment ID it recorded and falls back to the issue's full comment list, which Gitea does not paginate. The gateway MUST never edit a comment written by another account (research report §Comments never paginate; §Deterministic episode keys).
- **FR-036**: `gitea.pr.checks` and `gitea.commit.checks` MUST compute a commit's combined check state over every reported check, not over one returned page, using Gitea's own combination rule (research report §One status call judges the head). The combined state counts the `lease-epoch` status as Gitea does, because once a person makes it a required check it takes part in deciding the merge (FR-038). Both tools MUST also return each context's latest status, as Gitea counts it (Assumptions: Gitea 28.x API facts): its context, state, status id, description and commit. A consumer may then leave a context out of its own reading, as spec 008 FR-020 leaves `lease-epoch` out of a head's CI state and status count (inferred, project intake R7).

**Human-approved plan writes**

- **FR-037**: The person chose both ways to apply the Spec Kit–Gitea bridge's dry-run plan (spec 004 FR-022) in Shadow mode: "Both Create issues by hand and Approve; gateway writes it" (project intake R3). For the second way, the gateway MUST carry out a write that a person approved as part of the bridge's plan, although FR-024 otherwise refuses agent mutations in Shadow mode. The intake records that this answer changes FR-024 and spec 007 FR-002 (project intake R3). These rules apply:
  - **Actor**: the call comes from the Lead session that runs the bridge, or from its subagent within the Lead session's authority (spec 004 FR-021), with `actor_role` `lead`. The gateway writes through Lead's bot account, so spec 004 FR-025 adopts the created issues as Lead's (inferred).
  - **Approval**: the envelope carries the plan approval's reference (FR-010). The gateway MUST verify that the approval:
    - was given by a person's Gitea account, never by a bot account (the same test as FR-009);
    - names the plan by a fingerprint over every planned write and its idempotency key;
    - holds an entry whose tool, `issue_id`, payload and `idempotency_key` match the call exactly.

    How the person records the approval is left to planning (inferred).
  - **Scope**: the approval lifts the mode refusal for its plan's entries only: issue creation, dependency links, labels, milestone and board placement (spec 004 FR-022). Every other rule still applies: Lead's row of the matrix (FR-005), the envelope (FR-010), idempotency (FR-011), the version check (FR-012) and verification (FR-014). A call that matches no entry is refused with the mode named. The approval never covers auto-merge, reviews, review requests, branch creation or lease grants (inferred).
  - **Audit**: the audit record holds the approval reference, the approving person's account and the plan fingerprint (FR-022), and marks the write as human-approved, so spec 007's scorecard can count it as a human action rather than an agent mutation (inferred).
  - **Other modes**: the same rule applies in Agent implementation and Guarded autonomous modes, where spec 004 FR-023 also has a person apply the plan (inferred).

**Lease-epoch status**

- **FR-038**: The person answered "Both" to where the lease-epoch fence lives, and the intake records that answer as two fences (project intake, R7). The coordination-layer fence stays: a write or lease check that presents an older epoch is refused (FR-007; spec 001 FR-032). A lease-epoch commit status that branch protection requires is added, so that, as the intake records the person's goal, "a commit from a stale epoch can never merge" (project intake, R7; Jev research report §Leases need an epoch fence, not just a TTL). What this spec's mechanism guarantees is narrower; the limits are stated below. The control plane, acting as `system` through its own bot account (spec 001 FR-031), judges each new head of an agent branch and posts the status, the duty spec 001 FR-038 gives it. It compares the lease epoch the commit records, for example in a commit trailer the session writes (spec 003 FR-039), with the current epoch of that issue or part (spec 001 FR-032). It posts `lease-epoch` failure when the recorded epoch is missing or older (fail closed, Constitution Art. IV) and success otherwise. Everything in this requirement beyond the two fences themselves is inferred: who judges and posts, how a commit records its epoch, the failure rule and the tool's limits below. Gateway MUST carry that status only through `gitea.commit.set_lease_epoch_status`, and MUST:
  - let only `system` call the tool, writing through the control plane's bot account (FR-005, FR-017) (inferred);
  - write the status context `lease-epoch` and no other. The tool's input has no context field, and a call that carries a context or any field outside the tool's schema is refused (inferred);
  - accept only the states `success` and `failure` (inferred);
  - post only on a commit that is the current head of an agent branch named `agent/<role>/<issue>-<slug>` (spec 001 FR-019) for the envelope's `issue_id`, and refuse any other commit before any Gitea write (inferred);
  - refuse `success` unless the lease service (FR-004) confirms that the epoch the call presents for the commit is the current epoch of that issue or part (inferred: a second, deterministic check, FR-033; fail closed, Constitution Art. IV);
  - re-read the commit's statuses after posting and confirm that `lease-epoch` holds the posted state (FR-014).

  The gateway's mode check applies to this tool as to every other `system` write (FR-024) (inferred). A head that has no `lease-epoch` status cannot pass a required check (Assumptions: Gitea 28.x API facts), so a refused or missing post never lets a commit merge. Jev never posts a status and holds no new right (FR-027). A person adds `lease-epoch` to branch protection's required status checks (Constitution Art. VI). The gateway never writes branch protection (FR-002).

  With `lease-epoch` required, what the gateway guarantees is this: an agent-branch head that records a missing or older epoch when the control plane judges it cannot merge. The person's goal stays as the R7 record states it, but these limits remain (inferred; spec 001 FR-038 states the first):
  - The status judges the head commit only. A commit from a stale epoch beneath a later head that records the current epoch is not judged by it.
  - A head is judged when it is new. A head judged success before Lead revoked its lease keeps that success, so this status does not stop it from merging.
  - This spec leaves both cases to spec 001's recovery assessment, which reads the branch and its commits (spec 001 FR-017), and to its re-dispatch branch-head check (spec 001 FR-037).
  - The fence holds only while no credential an agent can reach can post a commit status. Gitea counts the latest status of a context, so such a credential could overwrite a `lease-epoch` failure (Assumptions: Branches). This tool is limited to `system` (FR-005); keeping every other credential that can post a status away from agents is a planning matter.

  [NEEDS CLARIFICATION: Branch protection applies a required check to every pull request into the protected branch, and it can require the branch to be current (US4). Two kinds of head record no lease epoch: the head of a branch a person pushed, and a commit a person adds to an agent branch, such as the merge commit of Gitea's update-branch action (no gateway tool updates a branch). This tool posts only on agent-branch heads and fails a missing epoch, and FR-024 refuses `system` writes in Shadow mode, so neither pull request could merge. Should the control plane also post `lease-epoch` success on a head commit that a person's account pushed or made, in every mode, or should those pull requests meet the check another way the person names? The first option adds a success path for heads people make, outside the missing-epoch failure rule; SC-011 and the edge case "Commit with no recorded epoch" would then exclude those heads.]

### Key Entities

- **Tool**: a named semantic operation, with its input schema, the actors allowed to call it, whether it needs a lease and whether it mutates.
- **Actor**: an `actor_role` value (lead, pse, review, system or jev) bound to one Gitea bot account. Each person and agent has one identity (data-model intake Q2). A subagent is an actor of its parent's role and carries its parent session. People act in Gitea directly and are never gateway callers; this includes the person who acts as Smokey (inferred from project intake Q13).
- **Bot Account**: one Gitea account per role, plus Jev's and the control plane's. The gateway holds its credential and checks its Gitea permissions at startup. The control plane's account needs write access to the repository's code, because Gitea requires it to post the `lease-epoch` status (Assumptions).
- **Actor Permission Matrix**: for each actor, the tools, labels and board moves it may use (FR-005).
- **Mutation Envelope**: `actor_role`, `session_id`, `issue_id`, `expected_version`, `idempotency_key` and `reason` (Constitution Art. III). It also carries the lease epoch for writes under a lease, the subagent identity when present, and the plan-approval reference for a human-approved plan write (FR-037). The schema is owned by spec 009 and shared with spec 001.
- **Issue Version**: the per-issue version the control plane keeps. It increases with every transition, label change and lease change it records (spec 001 FR-024). `expected_version` is checked against it, because Gitea issues have no native version counter.
- **Lease**: the control plane's record (spec 001), with its kind (write lease or non-write claim), holder and epoch. When Lead holds a write lease on an issue, Lead is acting as an implementation worker for that issue. The epoch fences writes and lease checks in the coordination layer (FR-007) and merges through the `lease-epoch` status (FR-038; project intake, R7).
- **Lease-Epoch Status**: the commit status with context `lease-epoch`, which branch protection requires once a person adds it (project intake, R7). It is posted on the head of an agent branch: failure when the commit records no lease epoch or an older one, success otherwise; only `system` posts it, through `gitea.commit.set_lease_epoch_status` (inferred, FR-038; spec 001 FR-038).
- **Idempotency Record**: the key, a payload fingerprint, the first outcome and the time it was recorded. It lives in the control plane's store (spec 001), its schema is owned by spec 009, and it is kept as long as events (FR-013).
- **Authority Decision**: allow or refuse, with the rule, the reason and the mode in effect.
- **Plan Approval**: a person's approval of one bridge plan (spec 004 FR-022), given from a person's Gitea account. It names the plan by a fingerprint over every planned write and its idempotency key, and lists the entries it covers (FR-037; project intake R3). Its schema is owned by spec 009, whose FR-002 lists it among the shared types the gateway uses and has the mutation envelope reference it. That it is a shared type owned there is inferred, and spec 009 FR-002 marks it so too.
- **Active Mode**: the autonomy mode read from the mode record (spec 007; schema from spec 009). When no mode is recorded, the active mode is Shadow.
- **Computed Risk Class**: the class the classifier assigned to a pull request's head commit (spec 006; schema from spec 009).
- **Comment Marker**: the upsert or idempotency key embedded in a comment body, which finds the comment again after a retry.
- **Label Map**: the name-to-ID map of repository and organization labels, built at startup, with each label's exclusive scope (FR-034).
- **Verified Result**: the observed Gitea state after a mutation, and whether it matched the intended change.
- **Audit Record**: one tool call with its envelope, caller identity, mode, authority decision, Gitea operations and verified result, plus the approval reference, approving account and plan fingerprint for a human-approved plan write. The schema is owned by spec 009, which serves "Track who did what" (data-model intake Q13). Only the gateway writes audit records, and every actor in the tenant may read them (data-model intake Q9: the owning role alone changes a record; inferred that the gateway is the owner).
- **Untrusted Content**: any Gitea free text returned to an agent, wrapped and labeled.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: A permission-containment suite records 0 successful unauthorized mutations. The suite covers every pair of actor and tool, in every autonomy mode. The actors are lead, pse, review, system, jev, and each role's subagents. Each pair is tried with and without leases, with current and older lease epochs, and with Lead acting and not acting as an implementation worker.
- **SC-002**: Replaying each mutation in a 500-call suite between two and five times produces exactly one external Gitea effect per idempotency key (100%). This includes keys first used by the control plane's own write path.
- **SC-003**: 100% of mutations return an observed post-state. In a fault-injection suite where Gitea silently drops at least 20 writes, 100% of those writes are reported as verification failures.
- **SC-004**: Before release, a scan of every agent-visible tool output, log and error from the containment, replay and fault suites finds 0 Gitea credentials for any bot account. After release, monitoring finds 0 in every 30-day window.
- **SC-005**: In the containment and fault-injection suites, the gateway accepts 0 auto-merge requests for a pull request that lacks the human approval its mode and computed risk class require, including requests whose issue text or labels claim a lower risk. In the same suites, 0 gateway calls cause a merge before required checks and branch-protection rules pass.
- **SC-006**: 100% of tool calls, including refused ones, appear in the audit trail within 5 seconds at the peak load of "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20) on the single host fixed in Assumptions (project intake Q22).
- **SC-007**: At the same peak load, 95% of read tools return within 2 seconds when Gitea itself responds within 1 second.
- **SC-008**: With Shadow mode active, or no mode recorded, 0 Gitea mutations by Lead, PSE, Review, the control plane or their subagents succeed in the containment suite, other than writes that match an entry of a bridge plan a person approved (FR-037; project intake R3). 100% of the refusals name the mode. 100% of the writes that do succeed carry an approval from a person's account, match one of its entries exactly and have an audit record naming the approver and the plan.
- **SC-009**: In a replay suite that repeats each marked comment call and each label call 2 to 5 times, including restarts between the Gitea write and its record, every marker ends with exactly one comment. 0 label calls remove or drop a label the caller did not name, other than a label in the same exclusive scope as a label the call adds, which Gitea replaces by design (Assumptions) (100%).
- **SC-010**: In 100% of startup trials where the Jev account is given push or merge permission, or any bot account is given administrator rights, the gateway acts for that account 0 times.
- **SC-011**: In the containment suite, 100% of calls to `gitea.commit.set_lease_epoch_status` are refused when they come from an actor other than `system`, carry a status context, ask for any state other than success or failure, target a commit that is not the current head of an agent branch, target an agent branch of an issue other than the envelope's `issue_id`, or ask for success with an epoch the lease service does not confirm as current. 0 gateway calls write any commit status other than `lease-epoch`. With `lease-epoch` required by branch protection, 0 agent-branch heads that record a missing or older lease epoch merge in the containment and fault-injection suites (FR-038; project intake, R7).

## Assumptions

- **Protocols and models**: the gateway speaks the Model Context Protocol to the role agents in the LangGraph service (project intake Q2), and the Gitea REST API to Gitea. Agents never call Gitea directly. Role agents may run on Claude or on Ollama, cloud or local (project intake Q7, Q14; constitution v1.1.0), so the gateway is model-agnostic.
- **Gitea operations**: Gitea 28.x supports every operation the tools need: issue, label, dependency, project-column, branch-creation, pull-request, review, changed-files, commit-status, merge-status and scheduled-merge (report §Gitea as the real-time engineering control plane). Issue search by identifier or label and milestone lookup by name are assumed to be supported too (inferred; project intake R4).
- **Gitea 28.x API facts** behind FR-034 to FR-036 and FR-038 (research report `docs/research/reports/Jev watchdog for coding agents.md`, except the facts marked as read from the Gitea v28.2.0 source for this pass):
  - The issue-labels endpoint takes integer IDs or string names, never both; a mixed list is rejected.
  - Unknown label names are silently dropped.
  - Removing a label takes only an ID.
  - `POST` adds labels; `PUT` replaces the whole set.
  - The label model has no unique name index, so bots never create labels.
  - The comments list has no pagination (only `since` and `before` filters).
  - The research could not confirm any idempotency header on comments, so the gateway assumes none.
  - On an exclusive scoped label, adding a label removes any other label in the same scope from the issue.
  - An exclusive label's scope is the part of its name before the last `/` (read from the source: `models/issues/label.go`, `ExclusiveScope`).
  - A label name defined in both the repository and the organization adds both labels.
  - The combined commit status covers only the returned page, which holds at most 50 entries.
  - Branch protection can require a status context through `enable_status_check` and `status_check_contexts`.
  - A required status context with no status on the head leaves the required state pending, so the pull request cannot merge (read from the source: `services/pull/commit_status.go`, `MergeRequiredContextsCommitStatus`).
  - Posting a commit status needs write access to the repository's code (read from the source: `routers/api/v1/api.go`).
  - For each status context, Gitea counts only the latest status posted on the commit (read from the source: `models/git/commit_status.go`, `GetLatestCommitStatus`).
  - Gitea 28.2 has no built-in REST rate limiter.
- **Human-owned setup**: people set up branch protection, label definitions and bot-account permissions outside the agent system, and all three are read-only to it. This includes:
  - the 12 exclusive scoped `jev/` labels, which a person creates once (project intake, R8; spec 008): the summary labels `jev/warning`, `jev/stuck` and `jev/parked`, and the role labels `jev/lead/warning`, `jev/lead/stuck`, `jev/lead/parked`, `jev/pse/warning`, `jev/pse/stuck`, `jev/pse/parked`, `jev/review/warning`, `jev/review/stuck` and `jev/review/parked`;
  - adding `lease-epoch` to branch protection's required status checks (project intake, R7; Constitution Art. VI);
  - giving the control plane's bot account write access to the repository's code, so it can post that status (inferred from the Gitea fact above). The gateway still exposes no push tool (FR-002), and the credential never leaves the gateway (FR-016).
- **Branches**: the control plane creates agent branches through `gitea.branch.create` (spec 001 FR-018). Pushes go through git under branch protection, not through the gateway. Each commit a session pushes records its lease epoch, for example in a commit trailer, so the control plane can judge the head (FR-038) (inferred). Planning decides how the PSE account's push credential is held without reaching the model (inferred). That credential must not be able to post a commit status either, because any account with write access to the code can, and Gitea counts the latest status of a context, so a session that could post one could overwrite its own `lease-epoch` failure (inferred).
- **Retry defaults**: 5 attempts with exponential backoff capped at 2 minutes, matching spec 001. These are proposed defaults the owner has not confirmed.
- **Success-criteria numbers**: the numeric targets in Success Criteria are proposed defaults. The person set the project's headline target, "+30% in 3 months (Recommended)" for accepted issues per week (project intake, R5; spec 007 SC-004), but no answer sets this gateway's own targets. The load the targets must hold at is the person's peak capacity (project intake Q20). The 3 agent sessions are "One per role (Recommended)": one session each for Lead, PSE and Review, with at most one issue in build at a time (project intake, R1), so the 6 subagents are at most 2 per role (project intake Q18). That is the same set of agents as the first-year scale of "10 Agents and 1 User" (data-model intake Q8): 3 sessions, 6 subagents and Jev make 10 (inferred).
- **Risk class and mode inputs**: spec 006's classifier computes the risk class, and spec 007 sets the active mode. Neither spec is a build dependency of this one: the gateway reads both through record schemas owned by spec 009. Until specs 006 and 007 exist, a missing class means Critical and a missing mode means Shadow, so this spec can be built and tested first (inferred).
- **Host**: Gitea, the LangGraph service, SQLite and local Ollama all run on one MacBook Pro M4 Pro with 24 GB RAM, about 18 GB of it usable after macOS (project intake Q22; data-model intake Q14). The gateway runs there too (inferred).
- **Stack**: "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." (project intake Q10). The authority and policy core is in OCaml, reading "Defaults" as the question's recommended option (inferred). Audit and idempotency records are stored in SQLite (project intake Q9) under spec 009's schemas. Planning decides the rest.

## Dependencies

- **Upstream**:
  - **001-engineering-control-plane**: 002 consumes the following from 001:
    - the lease service: claim, renew, release, revoke and epoch checks (FR-004, FR-007), including the current epoch of an issue or part that the `lease-epoch` status is judged against (spec 001 FR-032, FR-038; this spec's FR-038);
    - the shared idempotency store and its semantics (FR-032);
    - the per-issue version (spec 001 FR-024);
    - the transition table, with each move's owning actor;
    - the `system` actor whose writes the gateway carries (spec 001 FR-031), including the `lease-epoch` status it judges and posts (spec 001 FR-038; this spec's FR-038; project intake, R7);
    - the capacity registry of subagents (spec 001 FR-034).
  - **009-metadata-data-model**: 002 consumes the versioned schemas for the mutation envelope, idempotency records, audit records, actor and bot-account identities, the active-mode record, the computed-risk-class record and the plan-approval record that a human-approved plan write cites (FR-037). Spec 009 FR-002 lists each of them as a shared type and owns their schemas.
- **Downstream**:
  - **003-role-agent-contracts**: 003 consumes the actor permission matrix that enforces contract permissions (spec 003 FR-003), and the review, review-request and auto-merge tools.
  - **004-speckit-gitea-bridge**: 004 consumes every Gitea read and write it makes: issue creation with labels resolved to IDs, dependencies, board placement, idempotency keys and Lead's authority. It also consumes the read-only issue search and milestone lookup (FR-001; project intake R4), and the human-approved plan write that carries out its dry-run plan in Shadow mode (FR-037; project intake R3).
  - **006-quality-evidence-gates**: 006 consumes the check, review and merge-status reads, and the policy-respecting auto-merge tool with its mode and risk refusals.
  - **008-jev-progress-watchdog**: 008 consumes Jev's bot account and its tools:
    - combined commit checks, and each context's latest status, from which spec 008 FR-020 leaves `lease-epoch` out of a head's CI state (FR-036);
    - comment upsert by marker (FR-035);
    - the 12 `jev/` labels, summary and role labels, added by ID with their exclusive scopes respected (FR-027, FR-034; project intake, R8);
    - the startup check that Jev can neither push nor merge (FR-027);
    - the `lease-epoch` status, the forge-side half of the epoch fence behind its stop ladder's backstop (spec 008 FR-029 step 5; FR-038; project intake, R7). Jev itself never posts it.
- **Constitution**:
  - Art. II: no self-approval; separated authority.
  - Art. III: narrow tools, the mutation envelope, verified state, untrusted text.
  - Art. IV: a verification failure is never a success; an unknown mode or risk fails closed; an agent-branch head with no recorded lease epoch fails `lease-epoch`.
  - Art. VI: no branch-protection write or force merge; tool changes are Critical risk; a person, not an agent, makes `lease-epoch` a required check.
  - Art. IX: audit records join decision traces through session and idempotency key.

## Clarifications

### Session 2026-10-22

- Q: The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target? → A: Gitea only (project intake Q1)
- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service (project intake Q2)
- Q: Which models and embeddings should the RAG and reasoning chains use? → A: "Ollama (cloud and local) alongside Claude Code models." (project intake Q7)
- Q: Your stack lists 'a vector DB' and 'knowledge graphs' with SQLite, but no product. Which stores should the specs and code use? → A: "SQLite with sqlite-vec and custom Python Vector Databases. I want to create the Meta Data Schema and Structure. Create a new Data Modell that can scale for all current and future users when using this applications." (project intake Q9)
- Q: Which parts are OCaml and which stay Python? → A: "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." (project intake Q10)
- Q: Is Smokey an autonomous agent or an account a person controls? Art. VI says agents may not authorize changes to their own authority. → A: A person's account (project intake Q13)
- Q: The constitution allows Claude only, through the official SDK. Adding Ollama (cloud and local) amends it. How should I handle that? → A: Amend to v1.1.0 (project intake Q14)
- Q: How should agents authenticate to Gitea (spec 002)? → A: "Each role gets its own Gitea bot account." (project intake Q15)
- Q: How long are raw deliveries and normalized events kept (spec 001 FR-007)? → A: "Events have no time limit." (project intake Q16)
- Q: When should a running session be stopped? → A: "A session stops only when it is not making successful progress or is stuck." (project intake Q17)
- Q: How many subagents may run at once? → A: "At most 2 subagents per container, per role and per Gitea bot account." (project intake Q18)
- Q: What does 'stuck' mean? → A: "A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing." (project intake Q19)
- Q: What is the peak capacity the system must sustain (spec 001 FR-021)? → A: "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20)
- Q: Where should Gitea, the LangGraph service and the local Ollama models run? → A: All on the MacBook (project intake Q22)
- Q: Who counts as a 'user' of the data model? → A: People and agents (data-model intake Q2)
- Q: How many people and agents should the data model support in its first year? → A: "10 Agents and 1 User" (data-model intake Q8)
- Q: Who may change a metadata record once it exists? → A: Its owning role only (data-model intake Q9)
- Q: After finding related knowledge, which job should the data model take on next? → A: Track who did what (data-model intake Q13)
- Q: Which technical limits must the data model respect? → A: "Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption." (data-model intake Q14)
- Q: Spec 004: in Shadow mode, the Spec Kit→Gitea bridge only produces a dry-run plan. How should a person apply that plan? → A: "Both Create issues by hand and Approve; gateway writes it" — both paths: a person creates the issues by hand (the bridge reports them unconfirmed for Lead to confirm), or a person approves the plan and the gateway carries it out as a human-approved write (changes spec 002 FR-024 and spec 007 FR-002) (project intake, R3)
- Q: Spec 004: do you approve adding read-only issue search (by feature/task ID or label) and milestone lookup to the Gitea gateway? → A: "Approve read-only search (Recommended)" — a person approved it (Art. VI; spec 002 FR-003) (project intake, R4)
- Q: Spec 001 caps the team at 3 agent sessions. How should those 3 be split between Lead, PSE and Review? → A: "One per role (Recommended)" — one session each for Lead, PSE and Review; at most one issue in build at a time (project intake, R1)
- Q: Spec 003: Lead normally plans and does not write code. Who may switch Lead into implementation-worker mode for an issue? Lead may never grant this to itself (Art. VI). → A: "Owner, per issue (Recommended)" — a person (the owner) approves each switch, per issue (project intake, R2)
- Q: Spec 007's headline goal: what should autonomy deliver? The guardrails (escaped defects, reverts, security incidents, human recovery cost no worse than the Shadow-mode baseline) apply whichever is picked. → A: "+30% in 3 months (Recommended)" — accepted issues per week rise by at least 30% within 3 months of reaching Guarded autonomous mode, compared with Shadow mode, at the fixed capacity of 3 sessions, 6 subagents and Jev (project intake, R5)
- Q: Spec 008: when a stale session's lease is revoked, where should the epoch fence live? (Coordination layer only, or also a required commit status.) → A: "Both" (the person's own answer) — read as: the coordination-layer fence (spec 001 FR-032) and also a lease-epoch commit status that branch protection requires, so a commit from a stale epoch can never merge; which component posts the status is (inferred) (project intake, R7)
- Q: Several sessions can work on one issue, but jev/* labels are exclusive. What should the issue's label show? → A: "All three" (the person's own answer), confirmed in a follow-up as "Role labels + summary (Recommended)" — each role's session gets its own label (jev/pse/stuck, jev/review/warning, …) showing its latest verdict, and the summary label jev/warning, jev/stuck or jev/parked shows the most severe; a person creates the 12 labels once (project intake, R8)
