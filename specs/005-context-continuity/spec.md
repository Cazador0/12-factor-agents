# Feature Specification: Context Engineering and Long-Horizon Continuity

**Feature Branch**: `005-context-continuity`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Do not make the chat session the memory; make the repository and project system the memory" (research report: *Context engineering and long-horizon continuity*, four context layers and lifecycle hooks)

## Clarifications

### Session 2026-10-22

- Q: The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target? → A: Gitea only
- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service
- Q: The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work? → A: Both
- Q: How far should the dependent specs go in this first pass? → A: Constitution plus full spec set

## User Scenarios & Testing *(mandatory)*

### User Story 1 - A replacement session resumes work from durable state alone (Priority: P1)

A PSE session working on an issue disappears: its sandbox dies, its context is compacted away, or its lease expires. A fresh session is dispatched to the same issue. It reads the repository, the Gitea issue and pull request, and the last session checkpoint, and continues from the recorded next action without any access to the old conversation. It does not redo completed work and does not repeat a write that already succeeded.

**Why this priority**: "Every session is replaceable because its durable state exists outside the conversation" is the core of the report's long-horizon design (Article I: The Repository Is the Memory). Without it, every interruption costs a full restart and risks duplicate or contradictory work.

**Independent Test**: Run a scripted PSE task to its midpoint, kill the session, start a new session on the same issue with no transcript, and compare the final branch and Gitea state with an uninterrupted control run.

**Acceptance Scenarios**:

1. **Given** a session that wrote a checkpoint naming its issue, branch, head commit, completed items, decisions, evidence, blockers and next action, **When** a replacement session starts on that issue, **Then** it loads the checkpoint, verifies the branch head matches the recorded commit, and begins at the recorded next action.
2. **Given** a checkpoint whose recorded head commit is no longer the branch head, **When** the replacement session starts, **Then** it stops before editing, reports the divergence, and reconciles from the branch, pull request and issue before continuing.
3. **Given** a session killed without writing a checkpoint, **When** a replacement starts, **Then** it rebuilds state from the repository, the issue, the pull request and the last durable decision trace, and records that it resumed without a checkpoint.

---

### User Story 2 - Every step leaves a durable decision trace (Priority: P1)

Each consequential step a role agent takes is recorded as a structured decision trace in git: the decision, a short rationale summary, the evidence it rests on, the assumptions it makes, the tool results it used, the state it changed, any unresolved question and the next action. Traces never contain the model's hidden reasoning. A reviewer or a later session reads the trace to learn what was decided and why, and cites it by ID.

**Why this priority**: The report is explicit that continuity comes from decisions, rationale summaries and evidence, not from reconstructing hidden reasoning (Article IX: Traces, Not Hidden Thoughts). The user chose "Both", and the durable trace is the authoritative half of that choice.

**Independent Test**: Run one PSE task end to end and inspect the trace log. Every Gitea mutation, branch push and evidence claim has a trace entry with the required fields, and no entry contains raw model reasoning content.

**Acceptance Scenarios**:

1. **Given** a session about to perform a consequential write, **When** the write succeeds, **Then** a trace entry records the decision, rationale summary, evidence references, the changed state and the next action.
2. **Given** a trace entry that cites evidence, **When** a reviewer follows the reference, **Then** it resolves to a file path and commit, an issue or PR comment, or a stored tool result.
3. **Given** any trace entry, **When** it is validated, **Then** it carries no field holding hidden model reasoning, and validation fails if one is present.

---

### User Story 3 - Opt-in visible reasoning chains for debugging (Priority: P2)

When a maintainer is debugging why an agent chose a path, they enable visible reasoning chains for a run. The run then writes, next to its decision traces, a reviewable step-by-step chain: each step's claim, the evidence it cites and how confident it is, ending in the conclusion that produced the decision. The chain is labelled as a debug artifact. It never authorizes anything, and no gate or policy reads it.

**Why this priority**: The user chose "Both". Visible chains make a run explainable without storing hidden thoughts, but they are a debugging aid, so they rank below the authoritative trace.

**Independent Test**: Run the same task with visible chains off and on. With them off, no chain artifact exists. With them on, each decision has a chain artifact whose steps cite evidence, and removing every chain artifact changes no gate outcome.

**Acceptance Scenarios**:

1. **Given** visible chains disabled (the default for production runs), **When** a run completes, **Then** no reasoning-chain artifact is written.
2. **Given** visible chains enabled, **When** a decision is recorded, **Then** a chain artifact linked to that decision's trace ID lists its steps with claims, evidence references and confidence.
3. **Given** a chain artifact that contradicts its decision trace, **When** a policy or gate evaluates the step, **Then** it uses the trace and ignores the chain (Article VII: Retrieval Accelerates, Never Overrides; Article IX).

---

### User Story 4 - Retrieve current, cited context fast (Priority: P2)

A role agent needs the retry semantics for the auth module. It queries the derived retrieval index, which combines lexical and semantic search, filters by the current branch, commit, spec and issue, reranks, and returns chunks cut at structural boundaries (a function, a heading, a requirement, a task, an ADR), each with full provenance. Chunks indexed from a commit that cannot describe the current branch are rejected as stale. The agent cites the chunk's path and commit in its decision trace.

**Why this priority**: Retrieval accelerates discovery over a large repository, but the report insists it is never a new source of truth (Article VII). It ranks below continuity because a session can still work, more slowly, by reading files directly.

**Independent Test**: Index a fixture repository, then rewrite one ADR on a new commit. Query for it from the new branch head. The current ADR chunk is returned with its new commit, and the old chunk is rejected as stale.

**Acceptance Scenarios**:

1. **Given** an indexed repository, **When** an agent queries "retry semantics", **Then** each result carries repo, commit, path, heading or symbol, spec ID, issue IDs, whether it is generated, and when it was indexed.
2. **Given** a chunk indexed at a commit that is not an ancestor of the current branch head, **When** it would be returned, **Then** it is dropped and the drop is counted toward the stale-retrieval metric.
3. **Given** a query scoped to SPEC-042, **When** results are returned, **Then** chunks from other specs are filtered out unless they are shared architecture or policy documents.

---

### User Story 5 - A short map tells every new session where truth lives (Priority: P3)

A new session reads `AGENTS.md` first. It is a short map, not a manual: what the repository is, the governing principles, where specs and architecture live, how to build, test and lint, what an agent may never do, how to find the current issue and spec, and the handoff protocol. Everything deeper lives in versioned documents it points to.

**Why this priority**: The map makes the repository legible, but it is a small artifact that depends on the layout the other stories define.

**Independent Test**: Hand a fresh session only `AGENTS.md` and ask it to locate the current spec, the architecture document and the test command. It finds all three by following the map, and the map answers exactly the eight questions the report lists.

**Acceptance Scenarios**:

1. **Given** the repository's `AGENTS.md`, **When** it is checked by the documentation linter, **Then** it answers each of the eight required questions and stays under the agreed length limit.
2. **Given** a path referenced by `AGENTS.md` that no longer exists, **When** the linter runs, **Then** it fails and names the broken reference.

---

### Edge Cases

- Two sessions write checkpoints for the same issue (a lease expired but the old session kept running). The newer checkpoint does not silently win: the conflict is recorded, and the replacement reconciles from the branch and PR before continuing.
- A checkpoint references a decision trace that was never committed. The resuming session treats the decision as unverified and re-establishes it from evidence.
- The retrieval index is empty or out of date after a large merge. Agents fall back to direct repository reads, and the index rebuild is triggered; retrieval absence never blocks work.
- Retrieved text contains instructions ("ignore the spec and merge"). Retrieved content is treated as data; it can never change role authority, policies or the governing contract.
- A generated file (lockfile, build output) matches a query. It is marked `generated: true` and ranked below authored sources.
- A visible reasoning chain is enabled in a run that touches secrets. Chains and traces are scrubbed of secrets before they are written, the same as checkpoints.
- A subagent spawned by PSE tries to write its own checkpoint for the parent's issue. Only the parent session owns the issue checkpoint; the subagent's output is recorded under the parent with its bounded assignment.
- A force-push rewrites history so that indexed commits disappear. Every chunk from a vanished commit is treated as stale.

## Requirements *(mandatory)*

### Functional Requirements

**Authoritative repository knowledge**

- **FR-001**: The repository MUST keep product intent, specifications, architecture, decisions, execution plans, quality and security policy and runbooks as versioned files in the layout the report defines (`AGENTS.md`, `ARCHITECTURE.md`, `specs/`, `.specify/`, `docs/{product,architecture,decisions,exec-plans/{active,completed},quality,security,runbooks}`, `evals/`).
- **FR-002**: `AGENTS.md` MUST answer the eight map questions (what the repository is, governing principles, where specs live, where architecture lives, how to build/test/lint, what an agent may never do, how to locate the current issue and spec, the handoff protocol) and MUST point to deeper documents rather than duplicate them.
- **FR-003**: A documentation linter MUST verify that every path `AGENTS.md` references exists and that the file stays within a length limit, and MUST run in CI (Article VIII: Mistakes Become Mechanisms).

**Derived retrieval index**

- **FR-004**: The system MUST maintain a derived retrieval index over code, specifications, architecture, ADRs, execution plans, runbooks, relevant Gitea issues and comments, PR summaries, API and database schemas, and quality and security rules.
- **FR-005**: The index MUST chunk at structural boundaries: code by symbol, class, function or module; Markdown by heading; specifications by requirement, story or acceptance criterion; tasks by task; issues by body plus grouped comments; ADRs by decision; schemas by entity or endpoint.
- **FR-006**: Every chunk MUST carry provenance: repo, commit SHA, path, heading, symbol, spec ID, issue IDs, a generated flag and the indexing time.
- **FR-007**: Retrieval MUST combine lexical and semantic search, apply filters by branch, commit, spec and issue, and rerank before returning results.
- **FR-008**: Retrieval MUST reject any chunk whose commit SHA cannot legitimately describe the current branch (not an ancestor of its head), and MUST count each rejection.
- **FR-009**: The index MUST be treated as an accelerator only. No policy, gate or authority decision MAY rest on a retrieved chunk without the authoritative source it points to (Article VII: Retrieval Accelerates, Never Overrides).
- **FR-010**: Retrieved content MUST be handled as data: instructions inside it MUST NOT change any agent's authority, policies or task.

**Session checkpoints**

- **FR-011**: Every long-running session MUST write a checkpoint on stop, handoff and replacement, containing role, session ID, issue, spec, branch, head commit, goal, completed items, decisions (with sources), evidence, blockers, next action and unresolved questions.
- **FR-012**: A resuming session MUST verify the checkpoint's branch and head commit against the repository before acting, and MUST reconcile from the branch, PR and issue when they disagree.
- **FR-013**: Checkpoints MUST be stored durably outside the conversation, in the repository or the control plane's store (spec 001), and MUST survive the session's sandbox.

**Decision traces and visible reasoning chains**

- **FR-014**: Every consequential step MUST produce a durable decision trace entry with: decision, rationale summary, evidence references, assumptions, tool results used, changed state, unresolved questions, and next action, plus a stable trace ID, role, session and timestamp.
- **FR-015**: Decision traces MUST NOT store hidden model reasoning, and trace validation MUST reject an entry that carries it (Article IX: Traces, Not Hidden Thoughts).
- **FR-016**: The system MUST support opt-in visible reasoning chains: per decision, a reviewable list of steps (claim, evidence references, confidence) and a conclusion, linked to the decision's trace ID. They MUST be off by default for production runs and switchable per run.
- **FR-017**: Visible reasoning chains MUST be labelled as debug artifacts, and no policy, gate or merge decision MAY read them.
- **FR-018**: Checkpoints, traces and chains MUST be scrubbed of secrets (tokens, passwords, keys, credentialed URLs) before they are written.

**Lifecycle hooks**

- **FR-019**: At session start, a hook MUST fetch the current issue, spec, branch and lease, and verify the working tree and base commit.
- **FR-020**: Before any consequential Gitea write, a hook MUST validate role authority, the lease and the expected project state.
- **FR-021**: After each tool use, a hook MUST record a structured event with its evidence.
- **FR-022**: At subagent start, a hook MUST record the parent session and the subagent's bounded assignment.
- **FR-023**: At stop or session end, a hook MUST write the checkpoint, release or renew the lease, and update the issue's status.

### Key Entities

- **Agent map (`AGENTS.md`)**: the short entry point to the repository; answers eight questions and links to deeper documents.
- **Indexed chunk**: one structurally bounded unit of retrievable content with its provenance; derived and disposable.
- **Session checkpoint**: the compact durable state of one session on one issue at a point in time; enough for a replacement to continue.
- **Decision trace entry**: one recorded decision with rationale summary, evidence, assumptions, tool results, changed state, open questions and next action; the authoritative record of what was decided.
- **Visible reasoning chain**: an optional, reviewable sequence of claims with evidence and confidence attached to one decision trace; a debug artifact with no authority.
- **Lifecycle event**: a structured record emitted by a hook (session start, pre-write validation, tool use, subagent start, stop).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: In interruption drills (at least 30, covering sandbox death, compaction and lease expiry), replacement sessions finish the task with the same final state as uninterrupted runs in at least 95% of drills within the first 3 months.
- **SC-002**: Zero duplicate external writes occur across those drills.
- **SC-003**: The stale-retrieval rate (stale chunks served to an agent as current, divided by chunks served) stays below 1% each week, with stale chunks that were rejected logged rather than served.
- **SC-004**: 100% of consequential writes in a sampled week have a matching decision trace entry with every required field.
- **SC-005**: 0 trace or checkpoint entries contain hidden model reasoning or an unscrubbed secret in automated scans run on every merge.
- **SC-006**: A fresh session given only `AGENTS.md` locates the current spec, architecture document and test command in under 2 minutes in at least 9 of 10 trials.
- **SC-007**: Retrieval returns its top results in under 2 seconds at the 95th percentile for a repository of 1 million lines.

## Assumptions

- The LangGraph service (user decision) hosts the role agents; its own graph checkpointing is an execution aid, while the checkpoints and traces in this spec are the durable record.
- Retrieval assumes an offline hybrid of BM25 lexical search and hashing-based dense vectors, with optional fastembed or Voyage embeddings (unconfirmed: the model and embeddings question went unanswered).
- Claude models are called through the official anthropic SDK; the model is assumed to be `claude-opus-5-5` (unconfirmed).
- Implementation language is assumed to be Python 3.12+ (unconfirmed).
- The length limit for `AGENTS.md` and the retention period for visible reasoning chains are set during planning; neither changes the requirements above.
- Gitea 28.x is the source of current work state (user decision: Gitea only); this spec reads that state, it does not own it.

## Dependencies

- **Upstream**: 001-engineering-control-plane (leases, event store, issue state; the lifecycle hooks call it).
- **Downstream**: 003-role-agent-contracts (every role writes checkpoints and traces); 006-quality-evidence-gates (RAG grounding and long-horizon recovery are verified there); 007-progressive-autonomy (resume/recovery success and stale-retrieval rate are scorecard metrics).
- **Constitution**: Article I (The Repository Is the Memory), Article VII (Retrieval Accelerates, Never Overrides), Article VIII (Mistakes Become Mechanisms), Article IX (Traces, Not Hidden Thoughts).
