# Engineering Team of Coding Agent Sessions: Lead, PSE, and Review

## Executive architecture

The strongest design is **not three autonomous coding agents freely chatting with one another**. It is a three-role engineering organization operating over shared, durable systems of record, with explicit authority boundaries:

**Lead = control plane and technical/product authority**  
**PSE = implementation plane**  
**Review = independent assurance plane**

The repository should be the authoritative source for product intent, specifications, architecture, implementation, engineering policy, and long-lived decisions. Gitea should be the authoritative source for **current work state**: issues, dependencies, assignments, project/Kanban state, pull requests, reviews, checks, and merge status. Agent conversations are transient execution contexts, not the system of record. This closely matches OpenAI's experience with long-running coding agents: OpenAI reports that its agent-first repository moved knowledge into structured, version-controlled repository artifacts, kept `AGENTS.md` as a short map rather than an encyclopedia, versioned execution plans and decisions, and mechanically checked documentation and architecture for drift. citeturn19view3

The resulting topology should look conceptually like this:

```text
                         USER / PRODUCT INTENT
                                  │
                                  ▼
                         ┌─────────────────┐
                         │      LEAD       │
                         │ Architect       │
                         │ Spec authority  │
                         │ Scheduler       │
                         │ Repo manager    │
                         └───────┬─────────┘
                                 │
               plan / issues / dependencies / assignments
                                 │
                 ┌───────────────▼────────────────┐
                 │        GITEA CONTROL PLANE     │
                 │ Issues • Project • PRs • CI    │
                 │ Reviews • Webhooks • Policies  │
                 └───────┬───────────────┬────────┘
                         │               │
                 assignment         review request
                         │               │
                         ▼               ▼
                ┌────────────────┐ ┌────────────────┐
                │      PSE       │ │     REVIEW     │
                │ Implementation │ │ Independent QA │
                │ + unit tests   │ │ + verification │
                └───────┬────────┘ └────────┬───────┘
                        │                   │
                        └──── PR / evidence ┘
                                  │
                                  ▼
                        POLICY-MEDIATED MERGE
                                  │
                             protected main
```

This architecture fits the capabilities now available in OpenAI's agent stack. As of October 22, 2026, the Agents API is in public beta and uses the Codex harness for durable sessions, tool use, context management, sandboxed execution, and multi-agent delegation. OpenAI specifically describes automatic context compaction for long sessions and subagents with independent contexts coordinated by a parent agent. citeturn23search0 Codex itself can run specialized subagents in parallel; OpenAI recommends using that parallelism readily for read-heavy work while being more cautious with concurrent write-heavy work because simultaneous edits increase conflict and coordination overhead. citeturn19view2 Git worktrees are therefore a natural isolation mechanism: Codex documents worktrees specifically as a way to run independent chats in the same project without interfering with one another. citeturn17search7turn17search19

A crucial terminology correction will make the implementation cleaner: **Gitea issues do not get merged. Pull requests get merged.** Issues are created, edited, assigned, linked through dependencies, commented on, moved across project columns, and closed. Pull requests carry code integration and are reviewed and merged. Gitea's API exposes these as distinct operations. citeturn4view1

I would therefore define your desired "continuous autonomous development" as:

> The Lead continuously converts validated product intent into specifications and an issue dependency graph; PSE sessions claim eligible issues and produce tested pull requests; Review independently verifies them; Gitea's protected-branch policy and CI determine merge eligibility; qualifying pull requests are automatically merged; webhooks advance project state and unlock dependent work.

That is much safer and more scalable than granting every session unrestricted merge authority.

One other design change is important: **do not encode "went to the top schools in the world" into the personas.** It has no operational meaning. Replace pedigree claims with observable competencies, permissions, required evidence, quality thresholds, and evaluation suites. OpenAI's agent-first engineering experience similarly emphasizes tooling, scaffolding, repository legibility, mechanical constraints, and feedback loops rather than persona biography as the mechanisms that make agents dependable. citeturn19view3

And "100 percent accurate" should mean **100 percent of explicitly defined acceptance gates are satisfied**, not an impossible guarantee that software is defect-free. A rigorous system can establish deterministic evidence that specified requirements, tests, reviews, and policies passed; it cannot prove that arbitrary production software contains no unknown defect.

## The three-agent operating model

The three roles should share technical sophistication but have deliberately different **objectives and authority**. That separation is what prevents the team from becoming three copies of the same coding agent validating one another's assumptions.

| Dimension | Lead | PSE | Review |
|---|---|---|---|
| Organizational role | Principal Architect + Repository Manager | Principal Software Engineer | Principal Quality Assurance Engineer |
| Primary objective | Ensure the **right system** is being built in the right sequence | Build the specified system correctly | Independently establish whether it is actually correct |
| Owns | Intent, constitution, architecture, specifications, task DAG, assignment, repo structure, merge policy | Production implementation, developer tests, migrations, documentation affected by implementation | Verification strategy, QA checklist, adversarial tests, PR verdict, quality evidence |
| Gitea authority | Issues, dependencies, project state, assignment, reviews, policy-mediated merge | Assigned issues, branches, PRs, issue comments, implementation-state transitions | PR review, QA comments, QA issues, review-state transitions |
| May modify production code | Only when explicitly operating as an implementation worker | Yes | Preferably no; test/eval code is acceptable |
| May approve own code | No | No | No |
| May bypass branch protection | No | No | No |
| Completion condition | Feature/workstream has converged against user intent | Assigned issue satisfies acceptance criteria and is PR-ready | Independent evidence supports approval |
| Escalation condition | Ambiguous intent, conflicting architecture, critical-risk action | Spec ambiguity or dependency conflict | Unprovable requirement, security concern, insufficient evidence |

### Lead contract

The Lead is the **principal architect, repository manager, program scheduler, and keeper of intent**. It should be an excellent engineer capable of coding, but coding is not its default job. The Lead's scarce resource is global awareness.

OpenAI's guidance on subagents gives a useful rationale: keeping the coordinating thread focused on requirements, constraints, and decisions prevents noisy exploration, logs, test output, and implementation detail from crowding out the core task. citeturn19view2 In your organization, Lead should play exactly that role.

Lead's permanent responsibilities should be:

**Intent ownership.** Convert the user's request into explicit goals, non-goals, constraints, acceptance criteria, measurable success conditions, and unresolved questions. Once clarified, these become versioned artifacts.

**Specification authority.** Drive the complete Spec Kit process through an implementation-ready and internally consistent state before delegating significant work.

**Architecture authority.** Own architectural boundaries, interfaces, data models, security boundaries, dependency direction, reliability requirements, and architectural decision records. Architecture rules that can be expressed mechanically should become linters or structural tests, not prose alone. OpenAI reports using custom linters and structural tests to enforce architectural invariants in agent-heavy repositories. citeturn19view3

**Dependency planning.** Convert `tasks.md` into a DAG rather than an undifferentiated backlog. The Lead decides which tasks are parallelizable, which are serialized, and which require prerequisite artifacts.

**Dynamic delegation.** Dispatch independent issues to PSE sessions only when dependencies are satisfied and no other active lease owns the same unit of work.

**Repository management.** Maintain `AGENTS.md`, architecture documentation, specs, plans, quality policy, security policy, and engineering conventions.

**Conflict arbitration.** When PSE and Review disagree, neither should simply override the other. Lead reconciles the disagreement against the specification, architecture, and evidence.

**Merge authorization.** Lead should not manually "force merge." Instead, it selects the applicable merge policy, while Gitea mechanically decides whether all required conditions are satisfied.

A Lead session's ideal execution loop is:

```text
Observe repository + project
        ↓
Reconstruct current intent and dependency graph
        ↓
Find highest-priority unblocked work
        ↓
Verify specification readiness
        ↓
Create/update issue + acceptance contract
        ↓
Acquire orchestration lease
        ↓
Dispatch PSE
        ↓
Observe PR / CI / Review events
        ↓
Resolve conflicts or missing specification
        ↓
Authorize policy-mediated merge
        ↓
Close/move issue and unlock descendants
        ↓
Repeat
```

### PSE contract

PSE is the **production engineering specialist**. Its unit of ownership should normally be one coherent Gitea issue and one isolated branch/worktree at a time.

PSE begins by reading—not editing—the governing intent, feature specification, architecture, task record, relevant decisions, issue acceptance criteria, and branch state. It then creates an implementation plan scoped to its issue, verifies that no unresolved ambiguity would require inventing product behavior, and only then changes code.

Every PSE implementation should produce an **evidence package**, not merely a diff:

```yaml
implementation_evidence:
  issue: 184
  spec_id: SPEC-042
  task_ids: [T031, T032, T034]
  base_commit: "<sha>"
  head_commit: "<sha>"
  changed_components:
    - api/auth
    - web/session
  acceptance_criteria:
    AC-01: passed
    AC-02: passed
    AC-03: passed
  tests:
    unit: passed
    integration: passed
    typecheck: passed
    lint: passed
  migrations:
    present: false
  known_risks: []
  unresolved_questions: []
```

This becomes part of the PR description or a generated artifact attached to it.

PSE should have the engineering breadth you described—full-stack implementation, distributed systems, agent frameworks, retrieval systems, mathematical reasoning, observability, performance, infrastructure, and product-aware engineering—but these should be encoded as **skills and acceptance behavior**. For example:

> "When designing an asynchronous system, identify consistency model, ordering assumptions, idempotency boundaries, retry behavior, backpressure, failure recovery, and observability before implementation."

That instruction is materially useful; "you attended an elite university" is not.

PSE should also be allowed to use specialized subagents for bounded jobs: codebase exploration, dependency analysis, unit-test generation, log analysis, benchmark design, migration analysis, or documentation. OpenAI specifically recommends bounded subagent work to keep the primary thread focused and reduce context pollution. citeturn19view2turn17search13 However, one PSE session should remain the **single write owner** of its issue unless the Lead has deliberately partitioned the implementation into non-overlapping worktrees.

### Review contract

Review is not "PSE with a QA prompt." It should have PSE-level technical understanding but an **opposing objective function**:

> PSE asks, "How do I satisfy this specification?"  
> Review asks, "What evidence would prove that this implementation fails to satisfy the specification?"

Review independently reconstructs expectations from the specification rather than accepting PSE's interpretation. It examines the diff, but also tests the running behavior, architectural compatibility, security boundaries, regressions, failure modes, operational impact, and evidence completeness.

Its verdict should be machine-readable:

```yaml
review_verdict:
  pr: 211
  reviewed_commit: "<sha>"
  result: APPROVE  # APPROVE | CHANGES_REQUESTED | BLOCKED_BY_ENV
  requirements:
    covered: 14
    failed: 0
    unverified: 0
  blockers: []
  non_blocking_findings:
    - "Consider reducing duplicate serialization logic."
  evidence:
    - artifact: "e2e-results.json"
    - artifact: "security-report.sarif"
    - artifact: "benchmark.json"
```

Review should never silently repair the PSE's production implementation and then approve the combined result. That collapses independence. The safer loop is:

```text
PSE → PR → Review → CHANGES_REQUESTED
 ↑                         │
 └──────── fix + evidence ─┘

PSE → PR → Review → APPROVE → policy merge
```

Review may author QA infrastructure, test harnesses, fuzzers, regression tests, fixtures, evaluation datasets, or a separate test-only branch. Production remediation normally returns to PSE.

## Gitea as the real-time engineering control plane

As of October 22, 2026, Gitea 28.2.0 is the current release shown by Gitea's release feed; it was published October 18 and includes security fixes, so a system granting autonomous agents repository authority should stay current rather than building against an old Gitea deployment. citeturn18search1turn18search3

Gitea already exposes the major primitives required for this design through its API: issue operations, comments, assignments, dependencies/blockers, project/column operations, moving issues across project columns, pull request creation and updates, reviews, changed-file inspection, merge status, and pull-request merge operations. citeturn4view1

The missing piece is an **agent-safe orchestration layer**.

I recommend putting a small "Engineering Control Plane" between agent sessions and raw Gitea administration:

```text
Gitea
  │
  │ signed webhooks
  ▼
Webhook Gateway
  │
  ├─ verify authenticity
  ├─ deduplicate delivery
  ├─ normalize event
  ▼
State Machine / Scheduler
  │
  ├─ issue dependency graph
  ├─ leases
  ├─ retries
  ├─ risk policy
  ├─ role permissions
  └─ dispatch decisions
  │
  ├───────────────┬────────────────┐
  ▼               ▼                ▼
Lead session     PSE session      Review session
  │               │                │
  └───────────────┴────────────────┘
                  │
                  ▼
             Gitea MCP
                  │
                  ▼
             Gitea REST API
```

MCP is appropriate for the agent-facing interface because OpenAI supports MCP as a mechanism for connecting Codex/agents to external systems and tool sets. citeturn10view4turn23search0 The **MCP server should wrap the Gitea REST API**, not give agents database access, arbitrary administrator access, or a generic unrestricted shell command for manipulating Gitea.

A useful initial tool surface is intentionally narrow:

```text
gitea.issue.get
gitea.issue.create
gitea.issue.update
gitea.issue.comment
gitea.issue.assign
gitea.issue.dependencies.get
gitea.issue.dependencies.set

gitea.project.get
gitea.project.move_issue

gitea.pr.get
gitea.pr.create
gitea.pr.changed_files
gitea.pr.request_review
gitea.pr.review
gitea.pr.checks
gitea.pr.enable_auto_merge

gitea.branch.protection.get

coordination.lease.claim
coordination.lease.renew
coordination.lease.release
```

Avoid an unrestricted `gitea.request(method, path, body)` tool. The point of the MCP layer is to establish **semantic authority boundaries**.

Every mutation should carry:

```json
{
  "actor_role": "pse",
  "session_id": "sess_...",
  "issue_id": 184,
  "expected_version": 7,
  "idempotency_key": "pse-184-move-review-001",
  "reason": "Implementation complete; PR 211 created"
}
```

This guards against one of the most important long-horizon failure modes: an agent or retried event repeating a write after it has already succeeded.

### Kanban state machine

I recommend a deliberately explicit board:

| State | Owner | Entry condition | Exit condition |
|---|---|---|---|
| Backlog | Lead | Candidate work exists | Prioritized |
| Ready for Spec | Lead | Worth pursuing | Specification session starts |
| Specifying | Lead | Intent being formalized | Spec gates pass |
| Ready for Build | Lead | Spec/tasks/analyze are clean | PSE lease acquired |
| In Progress | PSE | PSE assigned | PR is ready |
| Review | Review | CI baseline passes and PR submitted | Approve or reject |
| Changes Requested | PSE | Blocking review finding | Updated PR ready |
| Ready to Merge | System | Review and policy gates pass | Merge completes |
| Done | System | PR merged / issue acceptance satisfied | Terminal |
| Blocked | Lead | External/dependency blocker | Blocker resolved |

`Blocked` is best treated as an exceptional status or label rather than normal progress.

The issue itself should contain enough structure that an agent can reconstruct its contract without reading a chat transcript:

```markdown
## Intent
Why this work exists.

## Spec
SPEC-042 / User Story 3

## Tasks
T031, T032, T034

## Acceptance criteria
- [ ] AC-01 ...
- [ ] AC-02 ...
- [ ] AC-03 ...

## Non-goals
...

## Dependencies
Blocked by #177

## Risk
medium

## Required verification
unit, integration, browser-e2e, security-baseline

## Ownership
Lead: ...
PSE: ...
Review: ...

## Current PR
#211
```

### Event-driven communication

"Real-time communication" should be **event-driven coordination**, not three agents maintaining an unstructured group chat.

Gitea webhooks should trigger state changes such as:

```text
issue.created
issue.assigned
issue.dependency_resolved
pull_request.opened
pull_request.synchronized
review.approved
review.changes_requested
check.success
check.failure
pull_request.merged
```

Gitea supports repository, organization, user, and system webhook scopes and provides delivery/event metadata and signature verification; its documentation describes HMAC-SHA256 verification of webhook bodies. citeturn12view1

Normalize those events before agents consume them:

```json
{
  "schema_version": 1,
  "event_type": "review.changes_requested",
  "repository": "acme/factory",
  "issue": 184,
  "pull_request": 211,
  "actor_role": "review",
  "session_id": "review-184-03",
  "commit": "abc123...",
  "summary": "Retry path is not idempotent.",
  "evidence": [
    "tests/integration/test_retry.py::test_duplicate_delivery"
  ],
  "blocking": true,
  "next_action": "pse.remediate",
  "event_id": "evt_...",
  "timestamp": "..."
}
```

This gives each new session a compact, queryable history without requiring it to infer project state from prose.

### Safe autonomous merge

Gitea's current protected-branch controls are well suited to **policy-mediated autonomy**. Gitea can prohibit direct pushes and force pushes, require approvals, dismiss or ignore stale approvals, prevent merges after requested changes, block outstanding review requests, require a PR to be up to date, force administrators to obey branch-protection rules, protect sensitive file patterns, and require matching CI status checks to report success before merging. citeturn19view0

That should be the foundation of autonomous merge.

Recommended `main` policy:

```text
Direct push                         DENY
Force push                          DENY
Administrator bypass                DENY

Required Review approval            >= 1
Block requested-changes reviews     YES
Dismiss/ignore stale approvals      YES
Require current base branch         YES
Required CI contexts                YES

Auto-merge                          ALLOWED WHEN POLICY PASSES
Force-merge tool for agents         NOT EXPOSED
```

Gitea's PR API supports merge operations including the ability to schedule merging when checks succeed, so the orchestration system can request auto-merge without bypassing the repository's gates. citeturn15view1turn15view2turn15view3

I would add risk-based escalation:

| Risk class | Examples | Autonomous merge |
|---|---|---|
| Low | Docs, local refactor, non-sensitive UI | Review + CI |
| Medium | Normal feature/API implementation | Review + complete CI |
| High | Auth, permissions, DB migration, agent tools, deployment | Review + CI + human approval |
| Critical | Secrets, security boundary, billing, destructive data migration, branch-policy changes | Human approval mandatory |

In particular, changes to the orchestrator, Gitea MCP server, CI policy, agent permissions, branch protection, secret-handling logic, and the Review agent's own gates should **not** be autonomously self-authorized by the same agent system.

That creates an important invariant:

> Agents may operate autonomously inside the rules; they may not autonomously weaken the rules that define their authority.

## Spec Kit and specification-driven delivery

Your `.specify` idea is directionally right, but the workflow should use the **current Spec Kit semantics**, and there is an important 2026 syntax change to account for.

Spec Kit is currently an open-source toolkit from GitHub for structuring agentic software development around specifications, reusable processes, templates, and documented outputs. citeturn17search0turn17search12

For Codex specifically, modern Spec Kit integrations use skills. In current Codex skills mode, commands are invoked with the **`$speckit-*` form**, while slash/hyphen syntax is used by other integrations. A current Spec Kit issue demonstrates `$speckit-specify` and notes that slash-prefixed output is invalid for Codex in that setup; Spec Kit's integration documentation also distinguishes invocation syntax among integrations. citeturn21search0turn21search2

So, for a Codex-based implementation, design around:

```text
$speckit-constitution
$speckit-specify
$speckit-clarify
$speckit-plan
$speckit-checklist
$speckit-tasks
$speckit-analyze
$speckit-implement
$speckit-converge
```

rather than hard-coding `/speckit-*` into the architecture.

The current full SDD path is effectively:

```text
CONSTITUTION
     ↓
SPECIFY
     ↓
CLARIFY
     ↓
PLAN
     ↓
CHECKLIST
     ↓
TASKS
     ↓
ANALYZE
     ↓
IMPLEMENT
     ↓
CONVERGE ── gaps ──→ IMPLEMENT
     │                   ▲
     └── Converged ──────┘
```

Spec Kit's current `analyze` step is explicitly read-only and checks consistency across `spec.md`, `plan.md`, and `tasks.md`; `implement` executes tasks in dependency order; and `converge` evaluates the resulting code against the spec, plan, and tasks and can append missed work until the feature reports converged. citeturn19view1

For your team, however, I would **split ownership across roles instead of letting one agent run the whole flow**:

| Spec Kit stage | Primary owner | Independent participant |
|---|---|---|
| Constitution | Lead | Review validates testability |
| Specify | Lead | Review challenges ambiguity |
| Clarify | Lead | PSE may flag technical ambiguity |
| Plan | Lead | PSE assesses implementability |
| Checklist | Review | Lead resolves requirement gaps |
| Tasks | Lead | PSE checks granularity/dependencies |
| Analyze | Lead + Review | Must be clean before build |
| Implement | PSE | Review remains independent |
| Converge | Review | PSE fixes appended gaps |
| Final acceptance | Review + Lead | Merge policy evaluates gates |

That division aligns particularly well with Spec Kit's own semantics: the implementation command treats checklist state as a gate and is not supposed to silently approve a reviewer-owned custom checklist. citeturn19view1

### Definition of "complete specification"

Instead of telling Lead to "complete 100 percent of `.specify` documentation," define a verifiable completeness contract.

No feature may become `Ready for Build` until it has:

```text
Product intent
User stories / use cases
Functional requirements
Non-functional requirements
Acceptance criteria
Explicit non-goals
Data/API contracts where relevant
Error and failure semantics
Authorization/security requirements
Observability requirements
Performance/SLO requirements where relevant
Migration/compatibility requirements where relevant
Architecture plan
Dependency map
Task DAG
Reviewer checklist
No unresolved critical clarification
Clean Spec Kit analyze report
Traceability from requirement → task → expected verification
```

This can be enforced by a CI linter that validates required headings, IDs, cross-references, and traceability.

### Gitea integration for Spec Kit

There is an important gap worth designing around rather than hiding: current Spec Kit's task-to-issue extension documented in the Agentic SDD reference is **GitHub-specific**. The old core `taskstoissues` command is deprecated, while the recommended extension creates GitHub issues and depends on a GitHub origin/MCP integration. citeturn19view1

Therefore, for Gitea you should build a small native Spec Kit extension or workflow—conceptually:

```text
$speckit-gitea-taskstoissues
```

Its responsibilities:

```text
Read specs/<feature>/tasks.md
        ↓
Parse task IDs and dependency markers
        ↓
Lookup existing Gitea issues by task ID
        ↓
Create only missing issues
        ↓
Set labels / milestone / assignee class
        ↓
Create dependency relationships
        ↓
Add to project board
        ↓
Write issue IDs back to a machine-readable mapping
```

The mapping should be stable and committed:

```yaml
feature: SPEC-042
tasks:
  T031:
    gitea_issue: 184
  T032:
    gitea_issue: 185
    blocked_by: [T031]
  T034:
    gitea_issue: 187
    blocked_by: [T031]
```

That gives Lead a deterministic bridge from specification to project execution and prevents repeated agent runs from creating duplicate issues.

A second command should synchronize in the opposite direction:

```text
$speckit-gitea-sync
```

It should check that every active issue still corresponds to a valid task, detect stale/missing mappings, and report drift rather than silently rewriting the spec.

## Context engineering and long-horizon continuity

The most important principle for long-horizon agent engineering is:

> **Do not make the chat session the memory. Make the repository and project system the memory.**

OpenAI's agent-first engineering report describes exactly this approach: structured repository documentation is treated as the system of record, plans and decision logs are versioned, and information that is not accessible to the running agent is effectively unavailable to it. citeturn19view3

Your context architecture should therefore have four layers.

### Authoritative repository knowledge

Recommended structure:

```text
/
├── AGENTS.md
├── ARCHITECTURE.md
├── specs/
│   └── <feature>/
│       ├── spec.md
│       ├── plan.md
│       ├── tasks.md
│       ├── checklists/
│       └── task-issue-map.yaml
│
├── .specify/
│   ├── memory/
│   ├── templates/
│   └── ...
│
├── .agents/
│   └── skills/
│       ├── speckit-*/
│       └── gitea-*/
│
├── docs/
│   ├── product/
│   ├── architecture/
│   ├── decisions/
│   ├── exec-plans/
│   │   ├── active/
│   │   └── completed/
│   ├── quality/
│   ├── security/
│   └── runbooks/
│
├── evals/
├── orchestrator/
│   ├── webhook/
│   ├── scheduler/
│   ├── policy/
│   ├── leases/
│   └── gitea_mcp/
│
└── .gitea/
    └── workflows/
```

OpenAI's own pattern similarly uses a short `AGENTS.md` as an entry-point/map and deeper structured documentation for architecture, product specifications, execution plans, quality, reliability, and security. citeturn19view3

`AGENTS.md` should answer only:

```text
What is this repository?
What are the governing engineering principles?
Where do I find product specifications?
Where do I find architecture?
How do I build/test/lint?
What may an agent never do?
How do I locate the current issue/spec?
What is the required handoff protocol?
```

Do not turn it into a thousand-line universal prompt.

### Current operational state

Gitea holds:

```text
Work priority
Issue status
Dependencies
Current assignee/session
Project board state
PR identity
Review state
CI state
Merge state
Blocking discussion
```

This information changes frequently, so a session should re-read it at the beginning of every meaningful execution phase rather than rely on a stale prompt.

### Derived retrieval index

RAG should be a **retrieval accelerator, not a new source of truth**.

Index:

```text
Code
Specifications
Architecture
ADRs
Execution plans
Runbooks
Relevant Gitea issues/comments
PR summaries
API schemas
Database schemas
Quality/security rules
```

Every indexed chunk should carry provenance:

```json
{
  "repo": "acme/factory",
  "commit_sha": "abc123",
  "path": "docs/architecture/runtime.md",
  "heading": "Retry semantics",
  "symbol": null,
  "spec_id": "SPEC-042",
  "issue_ids": [184],
  "generated": false,
  "indexed_at": "..."
}
```

Semantic vector search is appropriate for meaning-based retrieval; OpenAI's retrieval tooling uses vector stores as semantic-search indices, while embeddings encode semantic relationships useful for search and related retrieval tasks. citeturn16search0turn16search11

But do not naively split everything into fixed-size chunks. Recommended structural boundaries are:

```text
Source code       → symbol / class / function / module
Markdown          → heading and subsection
Specifications    → requirement / story / acceptance criterion
Tasks             → individual task
Issues            → issue body + semantically grouped event comments
ADRs              → one decision
Schemas           → logical entity / endpoint
```

Use lexical and semantic retrieval together, then filter by branch/commit/spec/issue and rerank before placing content in the active context.

A retrieval result should be rejected as stale when its indexed `commit_sha` cannot legitimately describe the current branch.

### Session checkpoint

Every long-running session should produce a compact, durable checkpoint on stop, handoff, or replacement:

```yaml
session_checkpoint:
  role: pse
  session_id: "..."
  issue: 184
  spec: SPEC-042
  branch: agent/pse/184-session-refresh
  head_commit: "<sha>"

  goal:
    "Implement AC-01 through AC-04."

  completed:
    - "Added refresh token rotation."
    - "Added duplicate-use invalidation."

  decisions:
    - id: D-01
      summary: "Token family invalidation is transactional."
      source: "docs/decisions/ADR-021.md"

  evidence:
    - "pytest tests/auth -q: pass"
    - "npm test -- session: pass"

  blockers: []

  next_action:
    "Open PR after full integration suite."

  unresolved_questions: []
```

This is deliberately **not chain-of-thought**.

Do not attempt to store or reconstruct an agent's hidden reasoning process as "thought chaining." Persist the artifacts actually useful to engineering continuity:

**decision, rationale summary, evidence, assumption, tool result, changed state, unresolved question, next action.**

That produces reproducibility without coupling your architecture to inaccessible internal reasoning.

OpenAI's Agents API now automatically compacts earlier context as long sessions approach their limits, preserving information needed for continuation across multiple context windows. citeturn23search0 That reduces—but does not eliminate—the need for external state. Your external checkpoint is what allows a replacement session, a different role, or a recovery after infrastructure failure to reconstruct reality without depending on one model conversation.

Codex hooks can also run scripts or MCP tools during lifecycle events, making them appropriate for things such as validation, logging, secret scanning, and persistent summary behavior. citeturn17search4 I would use them to enforce things such as:

```text
Session start:
  fetch current issue/spec/branch/lease
  verify working tree and base SHA

Before consequential Gitea write:
  validate role authority
  validate lease
  validate expected project state

After tool use:
  record structured event/evidence

Subagent start:
  record parent + bounded assignment

Stop/session end:
  write checkpoint
  release or renew lease
  update Gitea status
```

This architecture lets a session disappear and another session continue without losing organizational memory.

## Independent quality assurance and engineering gates

Review should test not only ordinary application correctness but the **agentic development system itself**.

Its quality model should have several layers.

| Verification layer | Review responsibility |
|---|---|
| Specification | Requirement is explicit, internally consistent, testable |
| Static quality | Format, lint, types, dependency boundaries, forbidden patterns |
| Unit | Core behavior and edge cases |
| Property/fuzz | Invariants across broad input domains where appropriate |
| Integration | DB, queues, APIs, Gitea/MCP adapters, external-service contracts |
| End-to-end | Real user journeys through browser/API |
| Data | Migrations, forward/backward compatibility, rollback |
| Reliability | Retry, timeout, concurrency, idempotency, partial failure |
| Security | Authn/authz, secrets, injection, dependency, trust boundaries |
| Performance | Latency/throughput/resource regressions against stated targets |
| Agent behavior | Tool selection, permission boundaries, context recovery, RAG grounding |
| Supply chain | Dependency and artifact provenance where required |

For web applications and services, OWASP ASVS 5.0.0 provides a current framework of security requirements for designing, developing, and testing web applications and web services. citeturn22search17turn22search9 NIST's final SSDF version 1.1 provides high-level secure software-development practices intended to be integrated into development lifecycles. citeturn22search0turn22search4 For releasable artifacts, SLSA provenance can record which build platform and build definition produced an artifact, allowing downstream provenance verification. citeturn22search2turn22search18

### Agentic-framework verification

Because your PSE specializes in "software factories" and agent frameworks, Review needs an additional agent-system suite.

For each agent capability, test at least:

**Intent preservation.** Does the agent's final action still satisfy the original user goal after many intermediate operations?

**Tool correctness.** Does it select the right tool, provide valid arguments, and verify resulting external state rather than assuming a successful tool response means the entire objective succeeded?

**Permission containment.** Can a PSE invoke a Review-only operation? Can a session bypass branch protections? Can nested subagents acquire more authority than their parent?

**Prompt-injection resilience.** What happens when repository text, issue comments, retrieved documents, logs, or external pages contain instructions that conflict with the governing contract?

**Long-horizon recovery.** Can a fresh session correctly resume from repository state + Gitea + checkpoint after compaction or interruption?

**Idempotency.** If a webhook or tool call is delivered twice, does the external result remain correct?

**Ordering.** What happens if `PR_UPDATED` arrives before a delayed `REVIEW_APPROVED` webhook?

**Concurrency.** Can two PSE agents claim the same issue? Can two issues concurrently modify the same architectural boundary?

**RAG grounding.** Is retrieved evidence from the current commit? Can the agent distinguish an obsolete ADR from a current one? Does it cite the source used for decisions?

**Failure recovery.** What happens when CI is unavailable, Gitea returns a transient error, the sandbox dies, a lease expires, or a dependency changes midway through work?

OpenAI explicitly recommends systematic evals for agent skills rather than treating prompts and skills as untestable configuration. citeturn17search17

The testing philosophy should therefore be:

```text
Every recurring agent mistake
         ↓
becomes a regression fixture
         ↓
then an evaluation
         ↓
then, where possible,
a mechanical constraint
```

This mirrors OpenAI's reported pattern of feeding review feedback and failures back into repository documentation and tooling so recurrent mistakes become enforceable rules. citeturn19view3

### Merge evidence gate

Before Review can return `APPROVE`, require an evidence manifest:

```yaml
quality_gate:
  reviewed_commit: "<sha>"

  requirements_traceability:
    complete: true

  checks:
    format: pass
    lint: pass
    types: pass
    architecture: pass
    unit: pass
    integration: pass
    e2e: pass
    security: pass
    dependency_scan: pass

  regressions:
    known: []

  review:
    blocking_findings: 0
    unresolved_questions: 0

  spec:
    converged: true

  branch:
    current_with_base: true
```

Different repositories can make categories conditional, but the applicability decision itself must be explicit. "Not run" must never silently mean "passed."

For bugs, every confirmed defect should ideally produce a regression test that first demonstrates the failure and then proves the repair. That converts discovered defects into permanent institutional memory.

## Reference implementation blueprint and rollout

The complete system can be built as five cooperating components rather than one enormous "super-agent."

```text
┌────────────────────────────────────────────────────────────┐
│ Engineering Control Plane                                  │
│                                                            │
│  Webhook Gateway  →  Event Store  →  State Machine         │
│                              │                             │
│                         Scheduler                           │
│                    ┌─────────┼─────────┐                    │
│                    ▼         ▼         ▼                    │
│                  Lead       PSE      Review                 │
│                    │         │         │                    │
│                    └─────────┼─────────┘                    │
│                              ▼                             │
│                     Gitea MCP Gateway                       │
│                              │                             │
└──────────────────────────────┼─────────────────────────────┘
                               ▼
                        Gitea 28.x REST API
```

OpenAI's current Agents API is well matched to the session layer because it exposes the Codex harness, long-running context management, hosted or external execution environments, MCP tools, and multi-agent support rather than requiring you to recreate the entire agent loop yourself. citeturn23search0 For local or hybrid Codex deployments, worktrees provide independent checkouts for parallel sessions. citeturn17search7turn17search19

### Orchestrator state model

The orchestrator should be deterministic even though the agents are probabilistic.

A simplified transition function:

```python
def next_action(issue, project, pull_request, checks, review):
    if issue.blocked_dependencies:
        return "WAIT"

    if issue.state == "READY_FOR_BUILD" and not issue.active_lease:
        return "DISPATCH_PSE"

    if issue.state == "IN_PROGRESS" and pull_request is not None:
        return "MOVE_TO_REVIEW"

    if issue.state == "REVIEW":
        if checks.failed:
            return "RETURN_TO_PSE"

        if review.changes_requested:
            return "RETURN_TO_PSE"

        if review.approved and checks.all_required_passed:
            return "EVALUATE_MERGE_POLICY"

    if pull_request and pull_request.merged:
        return "COMPLETE_AND_UNLOCK_DEPENDENCIES"

    return "NOOP"
```

The model may recommend actions; a deterministic policy engine decides whether the action is legal.

That separation is foundational:

```text
LLM decides what it believes should happen.
Policy code decides what it is allowed to make happen.
Gitea enforces the final repository rules.
```

### Claiming work safely

Before dispatching PSE:

```text
1. Re-read issue.
2. Re-read dependency state.
3. Verify issue is Ready for Build.
4. Atomically obtain lease:
      issue=184
      role=pse
      session=sess_xyz
      expires=...
5. Record expected repository base SHA.
6. Create isolated worktree/branch.
7. Transition to In Progress.
8. Start PSE.
```

A lease should have a TTL and heartbeat, but expiry must not automatically imply that another PSE may blindly continue in the same branch. Recovery first checks the branch, current commits, PR, and last checkpoint.

Recommended branch format:

```text
agent/lead/<issue>-<slug>
agent/pse/<issue>-<slug>
agent/review/<issue>-<slug>
```

Normally Review would not need a production branch.

### Protecting against cross-agent conflicts

The scheduler should compute a **write set estimate** before allowing aggressive parallel implementation:

```yaml
issue: 184
expected_write_domains:
  - packages/auth/**
  - apps/api/session/**
```

If issue `#185` also claims `packages/auth/**`, Lead should normally serialize them unless the work has deliberately separable boundaries.

This reflects OpenAI's current guidance: parallel subagents are especially appropriate for independent/read-heavy work, while parallel writing should be used with more care because conflicts and coordination costs rise. citeturn19view2

### Agent configuration philosophy

A role definition should look more like an operating contract than role-play:

```yaml
agent:
  id: pse
  mission:
    "Implement assigned, specification-backed Gitea issues with
     production-quality code and verifiable evidence."

  authoritative_sources:
    - current_user_intent
    - specs
    - repository
    - architecture
    - gitea_issue
    - gitea_pr

  permissions:
    repository:
      read: true
      branch_write: assigned_only
      protected_branch_write: false

    gitea:
      issues: assigned_scope
      projects: implementation_transitions_only
      pull_requests: create_update
      review_approval: false
      force_merge: false

  invariants:
    - never invent missing product requirements
    - never bypass failing checks
    - never approve own work
    - never modify policy to make own work pass
    - never mark evidence as passed unless executed
    - verify external mutations after tool success

  required_outputs:
    - implementation
    - tests
    - documentation_delta
    - evidence_manifest
    - session_checkpoint
```

Lead and Review should have equivalent contracts with different authority.

### Core metrics

Do not measure the system by "number of agent actions" or lines of generated code. Measure accepted engineering outcomes.

A compact scorecard should include:

| Domain | Metric |
|---|---|
| Delivery | Ready-to-Done cycle time |
| Delivery | Accepted issues per period |
| Review | First-pass approval rate |
| Quality | Escaped defects |
| Quality | Revert/rollback rate |
| Quality | Flaky-test rate |
| Specification | Requirements changed after implementation began |
| Specification | Average convergence passes |
| Coordination | Duplicate-work incidents |
| Coordination | Merge-conflict rate |
| Context | Stale-retrieval rate |
| Context | Resume/recovery success rate |
| Agent | Tool-call failure rate |
| Agent | Incorrect-action/block rate |
| Economics | Cost per accepted issue |
| Human load | Escalations per accepted issue |
| Security | Unauthorized-action attempts blocked |

The target is not maximum autonomy. It is **higher accepted throughput without worsening escaped defects, security incidents, reverts, or human recovery cost**.

### Progressive autonomy

Do not begin with unrestricted autonomous merge. Promote autonomy only after the same workflow demonstrates reliability.

**Shadow mode:** Lead, PSE, and Review analyze real work and produce plans/recommendations; humans perform consequential mutations.

**Agent implementation mode:** PSE may branch, code, test, create PRs, and update assigned issues. Review performs independent automated review. Human remains the merge authority.

**Guarded autonomous mode:** low-risk PRs automatically merge when protected-branch, CI, Review, freshness, and dependency gates all pass. Medium/high-risk work still requires human approval.

**Long-horizon mode:** Lead autonomously decomposes validated specifications, populates Gitea, assigns eligible tasks, recovers interrupted sessions, sequences dependencies, and closes completed work. Humans operate primarily at product intent, architecture exceptions, and elevated-risk review.

**Self-improving engineering mode:** recurring agents inspect technical debt, stale documentation, repeated review findings, flaky tests, retrieval quality, and architectural drift, then open ordinary PRs to improve the factory itself. OpenAI has described a similar recurring "doc-gardening" approach and notes that increasing autonomy creates repository entropy that itself needs systematic cleanup. citeturn19view3

### Final recommended operating doctrine

The completed organization should follow these invariants:

> **Lead owns truth about what should be built.**

> **PSE owns producing a correct implementation of an assigned contract.**

> **Review owns proving, independently, whether that contract has actually been satisfied.**

> **The repository owns durable engineering knowledge.**

> **Gitea owns durable execution state.**

> **RAG accelerates discovery but never overrides authoritative artifacts.**

> **Webhooks communicate state changes; unstructured agent-to-agent chat does not define project state.**

> **Agents may propose consequential actions; deterministic policies authorize them.**

> **Protected branches, CI, and independent Review—not confidence expressed by an agent—decide whether code is mergeable.**

> **Every session is replaceable because its durable state exists outside the conversation.**

> **Every repeated mistake should eventually become a test, evaluation, documented rule, or mechanical constraint.**

This design gives you the long-horizon "engineering team of Coding Agent Sessions" you described without depending on fragile persona prompts or one immortal context window. It uses the capabilities now available in Codex and the Agents API—subagents, isolated worktrees, MCP, hooks, long-session context management—and combines them with Gitea's project/issue/PR APIs, protected branches, required reviews and status checks, plus Spec Kit's current specification → analysis → implementation → convergence workflow. citeturn23search0turn19view2turn17search7turn17search4turn19view0turn19view1

The key architectural choice is that **autonomy should be implemented as a state machine with evidence and permissions, not as a powerful prompt telling three agents to collaborate indefinitely**. That is what turns Lead, PSE, and Review from three coding personalities into an actual autonomous software-engineering organization.