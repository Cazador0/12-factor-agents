# Feature Specification: Progressive Autonomy and the Engineering Scorecard

**Feature Branch**: `007-progressive-autonomy`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Do not begin with unrestricted autonomous merge. Promote autonomy only after the same workflow demonstrates reliability" (research report: *Reference implementation blueprint and rollout* → *Core metrics* and *Progressive autonomy*)

## Clarifications

### Session 2026-10-22

- Q: The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target? → A: Gitea only
- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service
- Q: The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work? → A: Both
- Q: How far should the dependent specs go in this first pass? → A: Constitution plus full spec set

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the agent team in Shadow mode first (Priority: P1)

The repository owner turns the system on for the first time. It starts in Shadow mode: Lead, PSE and Review analyze real work and produce plans, issue drafts, implementation proposals and review verdicts, but every consequential mutation (creating issues, pushing branches, approving, merging) is performed by a human. The scorecard records what the agents recommended next to what the humans did, building the baseline every later promotion is judged against.

**Why this priority**: Every later mode is earned against this baseline. Starting anywhere else violates the report's central rollout rule and Article III (Agents Propose, Policy Decides).

**Independent Test**: Enable Shadow mode on a repository and have agents process 10 real issues. The gateway rejects every agent mutation with "mode: shadow", the scorecard holds 10 recommendation records, and humans performed every merge.

**Acceptance Scenarios**:

1. **Given** the system in Shadow mode, **When** an agent attempts any consequential Gitea mutation, **Then** the gateway (spec 002) refuses it, names the active mode, and logs the attempt.
2. **Given** Shadow mode, **When** a human completes an issue the agents planned, **Then** the scorecard records the agents' recommendation, the human's action and whether they agreed.
3. **Given** a fresh install, **When** no mode has been set, **Then** the active mode is Shadow.

---

### User Story 2 - Promote and demote modes on evidence, not confidence (Priority: P1)

Each mode has written promotion criteria tied to the scorecard and an observation window. When the criteria hold, the system proposes a promotion with the evidence attached; a human approves it, and the policy records the new mode. When a guardrail metric worsens past its limit (escaped defects, reverts, security incidents, human recovery cost), the system demotes itself one mode immediately and opens an issue explaining why. No agent can promote itself.

**Why this priority**: The target is "higher accepted throughput without worsening escaped defects, security incidents, reverts, or human recovery cost". Promotion and demotion rules are how that target becomes mechanical (Article VI: Rules Are Not Self-Amendable).

**Independent Test**: Feed the policy a scorecard that meets Agent-implementation criteria; it proposes promotion and waits for a human. Then feed it a week with two reverts of agent-merged PRs; it demotes from Guarded autonomous to Agent implementation without waiting for anyone.

**Acceptance Scenarios**:

1. **Given** criteria met for the next mode, **When** the evaluation runs, **Then** a promotion proposal is created with the metric values and window, and the mode does not change until a human approves.
2. **Given** a guardrail metric past its demotion limit, **When** the evaluation runs, **Then** the mode drops one level at once, and an issue records the metric, the window and the triggering events.
3. **Given** an agent that edits the mode policy file to raise its own mode, **When** the PR is classified, **Then** it is Critical risk (spec 006) and cannot merge without a human, and the attempt is counted as an unauthorized-action attempt.

---

### User Story 3 - Read one scorecard that measures accepted outcomes (Priority: P1)

The owner opens the scorecard. It does not count agent actions or lines of code. It shows accepted engineering outcomes across delivery, review, quality, specification, coordination, context, agent behavior, economics, human load and security, each with its definition, data source, current value, trend and target direction, over selectable windows.

**Why this priority**: Promotion decisions and the user's trust both rest on these numbers; without a defined scorecard, "autonomy is working" is an assertion (Article IV: Evidence Over Assertion).

**Independent Test**: Load a fixture event history covering 30 days and 40 issues. The scorecard shows all 17 metrics with values matching a hand calculation, and each metric links to the events it was computed from.

**Acceptance Scenarios**:

1. **Given** 30 days of events, **When** the scorecard is computed, **Then** every metric in the scorecard table has a value or an explicit "insufficient data", never a blank or a zero standing in for missing data.
2. **Given** any metric value, **When** the owner drills in, **Then** it resolves to the issues, PRs, verdicts or events it was computed from.

---

### User Story 4 - Guarded autonomous merge for low-risk work (Priority: P2)

After promotion to Guarded autonomous mode, low-risk PRs merge automatically when protected-branch rules, CI, Review, branch freshness and dependency gates all pass. Medium-, high- and critical-risk PRs still need a human approval.

**Why this priority**: It is the first mode that removes humans from routine merges, and therefore the first that pays back the investment, but it depends on Stories 1–3 and on spec 006's gates.

**Independent Test**: In Guarded autonomous mode, submit one docs-only PR and one medium-risk feature PR, both with passing manifests. The docs PR merges without a human; the feature PR waits for a human approval.

**Acceptance Scenarios**:

1. **Given** Guarded autonomous mode and a Low-risk PR with a passing manifest, **When** all gates pass, **Then** auto-merge is requested through the gateway and the PR merges.
2. **Given** the same mode and a Medium-risk PR, **When** all gates pass, **Then** the PR waits for a human approval.

---

### User Story 5 - Long-horizon and self-improving modes (Priority: P3)

In Long-horizon mode the Lead decomposes validated specifications, populates Gitea through the bridge (spec 004), assigns eligible tasks, recovers interrupted sessions, sequences dependencies and closes completed work; humans work at product intent, architecture exceptions and elevated-risk review. In Self-improving mode, recurring agents look for technical debt, stale documentation, repeated review findings, flaky tests, retrieval quality and architectural drift, and open ordinary PRs that go through the same gates as any other change.

**Why this priority**: These modes are the destination, but each is only safe once the earlier modes have demonstrated reliability on the same workflow.

**Independent Test**: In Self-improving mode, seed a flaky test and a stale document. The recurring agents open two ordinary PRs, each classified and gated like human work, and neither touches a protected policy path.

**Acceptance Scenarios**:

1. **Given** Long-horizon mode and an analyzed spec, **When** the Lead runs, **Then** issues are created, assigned and sequenced without human action, and only elevated-risk PRs wait for a human.
2. **Given** Self-improving mode, **When** a recurring agent proposes a change to its own gates, **Then** the PR is Critical risk and needs a human (Article VI).

---

### Edge Cases

- A metric has too little data in its window (fewer than the minimum sample). It reads "insufficient data", and a promotion that depends on it cannot be proposed.
- A demotion fires while a PR is mid-merge under the old mode. The merge completes only if it also satisfies the new mode's rules; otherwise auto-merge is cancelled and the PR waits for a human.
- Two guardrail metrics trip in the same evaluation. The system demotes one level per evaluation, records both triggers, and re-evaluates on the next cycle.
- A human manually promotes past several modes at once. The policy requires each intermediate mode's criteria to have held; otherwise the request is refused with the missing criteria named.
- The event store is unavailable when the evaluation runs. No promotion is proposed; demotion falls back to the last known values, never upward.
- An incident is caused by a human-merged PR in Guarded mode. It counts toward quality metrics but is attributed to its merge actor, so agent and human outcomes stay distinguishable.

## Requirements *(mandatory)*

### Functional Requirements

**Autonomy modes**

- **FR-001**: The system MUST support five ordered modes: Shadow, Agent implementation, Guarded autonomous, Long-horizon and Self-improving, and MUST start in Shadow.
- **FR-002**: In Shadow mode, agents MUST be limited to analysis and recommendations; every consequential mutation MUST be performed by a human, and the gateway (spec 002) MUST refuse agent mutations.
- **FR-003**: In Agent implementation mode, PSE MAY branch, code, test, create PRs and update its assigned issues; Review MUST perform independent automated review; a human MUST remain the merge authority.
- **FR-004**: In Guarded autonomous mode, Low-risk PRs MAY merge automatically when protected-branch, CI, Review, freshness and dependency gates all pass; Medium, High and Critical PRs MUST still require a human approval.
- **FR-005**: In Long-horizon mode, the Lead MAY decompose validated specs, populate Gitea, assign eligible tasks, recover interrupted sessions, sequence dependencies and close completed work; elevated-risk review MUST stay with humans.
- **FR-006**: In Self-improving mode, recurring agents MAY open ordinary PRs that improve the factory (debt, stale docs, repeated findings, flaky tests, retrieval quality, architectural drift), and those PRs MUST pass the same gates and risk classification as any other change.
- **FR-007**: The active mode MUST be enforced by deterministic policy code and the gateway, not by agent prompts (Article III: Agents Propose, Policy Decides).

**Promotion and demotion**

- **FR-008**: Each mode above Shadow MUST have written promotion criteria that reference scorecard metrics, thresholds and an observation window, versioned in the repository.
- **FR-009**: Promotion MUST be proposed by the system with its evidence and MUST take effect only after a human approves; approval for promotion to Long-horizon or Self-improving mode requires [NEEDS CLARIFICATION: who may approve the two highest modes — the repository owner alone, or the owner plus a second named reviewer?].
- **FR-010**: Promotion MUST move one mode at a time, and each intermediate mode's criteria MUST have held for its full window.
- **FR-011**: The system MUST demote one mode immediately, without waiting for a human, when a guardrail metric (escaped defects, revert rate, security incidents, escalations per accepted issue) crosses its demotion limit, and MUST open an issue recording the trigger.
- **FR-012**: No agent MAY change the active mode, the promotion criteria, the demotion limits or the metric definitions; such changes are Critical risk and require a human (Article VI: Rules Are Not Self-Amendable).

**Scorecard**

- **FR-013**: The system MUST compute the following metrics from the control plane's event store (spec 001), Gitea, Review verdicts and evidence manifests (spec 006), and session records (spec 005), each with a written definition, data source and target direction:

  | Domain | Metric | Target direction |
  |---|---|---|
  | Delivery | Ready-to-Done cycle time | lower |
  | Delivery | Accepted issues per period | higher |
  | Review | First-pass approval rate | higher |
  | Quality | Escaped defects | lower |
  | Quality | Revert/rollback rate | lower |
  | Quality | Flaky-test rate | lower |
  | Specification | Requirements changed after implementation began | lower |
  | Specification | Average convergence passes | lower |
  | Coordination | Duplicate-work incidents | lower |
  | Coordination | Merge-conflict rate | lower |
  | Context | Stale-retrieval rate | lower |
  | Context | Resume/recovery success rate | higher |
  | Agent | Tool-call failure rate | lower |
  | Agent | Incorrect-action/block rate | lower |
  | Economics | Cost per accepted issue | lower |
  | Human load | Escalations per accepted issue | lower |
  | Security | Unauthorized-action attempts blocked | all blocked |

- **FR-014**: The scorecard MUST NOT use counts of agent actions or generated lines of code as success measures.
- **FR-015**: Every metric value MUST link back to the records it was computed from, and MUST read "insufficient data" when its window lacks the minimum sample.
- **FR-016**: Quality and human-load metrics MUST attribute each outcome to the actor who merged or acted (agent role or human), so agent and human performance stay separable.
- **FR-017**: Cost per accepted issue MUST include model usage, compute and human review time for all work on the issue, including rejected attempts, and its target is [NEEDS CLARIFICATION: is there a cost ceiling per accepted issue that should block promotion, or is cost tracked without a limit?].

### Key Entities

- **Autonomy mode**: one of five ordered levels of agent authority; has permitted actions, promotion criteria and demotion limits.
- **Mode policy**: the versioned, human-owned file that defines modes, criteria, windows and limits; read by policy code and the gateway.
- **Promotion proposal**: a system-generated request to move up one mode, carrying the metric values and window; resolved by a human.
- **Demotion record**: an automatic one-level drop with its trigger metric, window and events.
- **Scorecard metric**: a named measure with definition, source, window, attribution and target direction.
- **Scorecard snapshot**: the computed values of all metrics for one window, linked to their source records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of installations start in Shadow mode, and 0 agent-initiated mutations succeed while Shadow is active.
- **SC-002**: 0 promotions take effect without a recorded human approval; 100% of guardrail breaches trigger a demotion within one evaluation cycle (at most 24 hours).
- **SC-003**: All 17 scorecard metrics are computed for every weekly window within 1 month of rollout, with fewer than 2 metrics reading "insufficient data" after the first month.
- **SC-004**: After reaching Guarded autonomous mode, accepted issues per week rise by at least 30% within 3 months while escaped defects, revert rate and security incidents stay at or below their Shadow-mode baselines.
- **SC-005**: Escalations per accepted issue fall by at least 40% between Agent implementation mode and Long-horizon mode.
- **SC-006**: 100% of unauthorized-action attempts in each quarter are blocked and appear in the scorecard.

## Assumptions

- Gitea 28.x hosts work state and enforces protected-branch rules (user decision: Gitea only); the gateway of spec 002 is the enforcement point for modes.
- The role agents run in the LangGraph service (user decision); the mode is read by the service at dispatch time and again by the gateway at write time.
- Default observation windows are 4 weeks per promotion step with a minimum sample of 20 accepted issues; exact thresholds are set in planning and versioned in the mode policy.
- Model usage cost is read from the provider's usage reporting; models are assumed to be Claude models called through the official anthropic SDK (`claude-opus-5-5` assumed; unconfirmed).
- Implementation language is assumed to be Python 3.12+ (unconfirmed).

## Dependencies

- **Upstream**: 001-engineering-control-plane (event store and state transitions feed every delivery and coordination metric; the mode is part of dispatch policy); 003-role-agent-contracts (which actions each role may take in each mode); 006-quality-evidence-gates (risk classes, merge evidence manifests and verdicts feed quality and review metrics; Guarded mode requires them).
- **Related**: 002-gitea-mcp-gateway (enforces the active mode on every mutation); 004-speckit-gitea-bridge (Long-horizon mode depends on autonomous issue population; "requirements changed after implementation began" comes from its records); 005-context-continuity (stale-retrieval and resume/recovery metrics).
- **Constitution**: Article III (Agents Propose, Policy Decides), Article IV (Evidence Over Assertion), Article VI (Rules Are Not Self-Amendable), Article VIII (Mistakes Become Mechanisms).
