# Feature Specification: Progressive Autonomy and the Engineering Scorecard

**Feature Branch**: `007-progressive-autonomy`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: "Do not begin with unrestricted autonomous merge. Promote autonomy only after the same workflow demonstrates reliability" (research report: *Reference implementation blueprint and rollout* → *Core metrics* and *Progressive autonomy*)

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run the agent team in Shadow mode first (Priority: P1)

The repository owner turns the system on for the first time. It starts in Shadow mode. Lead, PSE and Review analyze real work and produce plans, issue drafts, implementation proposals and review verdicts. A human performs every consequential mutation: creating issues, pushing branches, approving and merging. There is one exception, which the person chose: a person may approve the Spec Kit–Gitea bridge's dry-run plan, and the gateway then carries out that plan's writes as human-approved writes ("Both Create issues by hand and Approve; gateway writes it", project intake R3). The scorecard records what the agents recommended next to what the humans did. This builds the baseline that every later promotion is judged against.

**Why this priority**: Every later mode is earned against this baseline. Starting anywhere else breaks the report's central rollout rule ("Do not begin with unrestricted autonomous merge"). It also breaks the constitution's Development Workflow ("Progressive autonomy starts in Shadow mode"), under which each promotion is a Critical-risk change (Article VI).

**Independent Test**: Enable Shadow mode on a repository and have agents process 10 real issues. Every agent mutation that is not part of a bridge plan a person approved is refused with "mode: shadow", by the control plane's autonomy-mode gate and by the gateway's mode check. The scorecard holds 10 recommendation records, and humans performed every merge.

**Acceptance Scenarios**:

1. **Given** the system in Shadow mode, **When** an agent attempts any consequential Gitea mutation that is not an entry of a bridge plan a person approved, **Then** the mutation is refused, the refusal names the active mode, and the attempt is logged and counted (FR-002).
2. **Given** Shadow mode, **When** a human completes an issue the agents planned, **Then** the scorecard records the agents' recommendation, the human's action and whether they agreed.
3. **Given** a fresh install, **When** no mode has been set, or the active-mode record cannot be read, **Then** the active mode is Shadow (FR-018).
4. **Given** Shadow mode and a bridge dry-run plan that a person's Gitea account approved, **When** the Lead's bridge run sends one of that plan's writes with the approval reference, **Then** the gateway carries it out as a human-approved write, and the scorecard attributes it to the approving person, not to an agent (FR-002, FR-016; spec 002 FR-037; project intake R3).

---

### User Story 2 - Promote and demote modes on evidence, not confidence (Priority: P1)

Each mode has written promotion criteria tied to the scorecard and an observation window. When the criteria hold, the system proposes a promotion. The proposal carries the evidence and a constitution compliance review. A human approves it. For the two highest modes, Long-horizon and Self-improving, that human is Smokey, a person's account, and no one else. Policy code then records the new active mode. When a guardrail metric worsens past its limit, policy code lowers the active mode by one step at once and opens an issue explaining why. The guardrails are the report's list: escaped defects, reverts, security incidents and human recovery cost. Automatic demotion, and the separate active-mode record that policy code writes, are proposed mechanisms that the owner has not yet confirmed (FR-011, FR-018). No agent can promote itself.

**Why this priority**: The target is "higher accepted throughput without worsening escaped defects, security incidents, reverts, or human recovery cost". Promotion and demotion rules make that target mechanical (Article VI: Rules Are Not Self-Amendable).

**Independent Test**: Feed the policy a scorecard that meets Agent-implementation criteria. It proposes promotion and waits for a human. Then set the fixture's revert-rate demotion limit to "more than one revert of an agent-merged PR in the window". This limit is test configuration, not a product threshold. Feed the policy a window with two such reverts. It demotes from Guarded autonomous to Agent implementation without waiting for anyone.

**Acceptance Scenarios**:

1. **Given** criteria met for the next mode, **When** the evaluation runs, **Then** a promotion proposal is created with the metric values, the window and a compliance review result, and the mode does not change until a human approves.
2. **Given** a guardrail metric past its demotion limit, **When** the evaluation runs, **Then** the mode drops one level at once, and an issue records the metric, the window and the triggering events.
3. **Given** an agent that edits the mode policy file to raise its own mode, **When** the PR is classified, **Then** it is Critical risk (spec 006) and cannot merge without a human, and the attempt is counted as an unauthorized-action attempt.
4. **Given** criteria met for Long-horizon mode, **When** any account other than Smokey's approves the proposal, **Then** the approval is refused and recorded, and the mode does not change (FR-009).
5. **Given** a promotion proposal whose compliance review finds an article violated, **When** a human tries to approve it, **Then** the promotion is blocked and the violation is handled as a defect under Article VIII (FR-019).
6. **Given** a demotion out of Guarded autonomous mode, **When** promotion back to Guarded autonomous is next evaluated, **Then** the evaluation replays the demotion's regression fixture (FR-021).

---

### User Story 3 - Read one scorecard that measures accepted outcomes (Priority: P1)

The owner opens the scorecard, and so does Smokey, who approves the two highest modes. It does not count agent actions or lines of code. It shows accepted engineering outcomes across these areas: delivery, review, quality, specification, coordination, context, agent behavior, progress (Jev), economics, human load and security. Each metric shows its definition, data source, current value, trend and target direction, over selectable windows.

**Why this priority**: Promotion decisions and the user's trust both rest on these numbers. Without a defined scorecard, "autonomy is working" is an assertion (Article IV: Evidence Over Assertion).

**Independent Test**: Load a fixture event history covering 30 days and 40 issues. The scorecard shows all 22 metrics of FR-013 with values that match a hand calculation. Each metric links to the events it was computed from.

**Acceptance Scenarios**:

1. **Given** 30 days of events, **When** the scorecard is computed, **Then** every metric in the scorecard table shows one of three things: a value, "insufficient data" with its sample size, or "not applicable" with its reason. It never shows a blank, or a zero standing in for missing data.
2. **Given** any metric value, **When** the owner drills in, **Then** it resolves to the issues, PRs, verdicts, Jev episodes or events it was computed from.
3. **Given** a window with model usage from Claude, Ollama cloud and Ollama local, **When** cost per accepted issue is computed, **Then** it is shown per provider and in total. Changing cost alone never changes the outcome of a promotion evaluation (FR-017).

---

### User Story 4 - Guarded autonomous merge for low-risk work (Priority: P2)

After promotion to Guarded autonomous mode, low-risk PRs merge automatically once every gate passes: protected-branch rules, CI, Review, branch freshness and dependency gates. Medium-, High- and Critical-risk PRs still need a human approval.

**Why this priority**: It is the first mode that removes humans from routine merges, so it is the first that pays back the investment. It depends on Stories 1–3 and on spec 006's gates.

**Independent Test**: In Guarded autonomous mode, submit one docs-only PR and one Medium-risk feature PR, both with passing manifests. The docs PR merges without a human. The feature PR waits for a human approval.

**Acceptance Scenarios**:

1. **Given** Guarded autonomous mode and a Low-risk PR with a passing manifest, **When** all gates pass, **Then** auto-merge is requested through the gateway and the PR merges.
2. **Given** the same mode and a Medium-risk PR, **When** all gates pass, **Then** the PR waits for a human approval.

---

### User Story 5 - Long-horizon and self-improving modes (Priority: P3)

In Long-horizon mode the Lead runs the work without a human in the loop for routine steps. Under its role contract (spec 003) it decomposes validated specifications, populates Gitea and assigns eligible tasks. It recovers interrupted sessions, including sessions stopped because they were stuck. It sequences dependencies and closes completed work. Humans work at product intent, architecture exceptions and elevated-risk review, meaning High- and Critical-risk PRs (inferred). In Self-improving mode, recurring agents look for technical debt, stale documentation, repeated review findings, flaky tests, retrieval quality and architectural drift. They open ordinary PRs that go through the same gates as any other change.

**Why this priority**: These modes are the destination. Each is safe only once the earlier modes have shown reliability on the same workflow.

**Independent Test**: The two modes are tested separately.

- Long-horizon: give the Lead an analyzed spec with three dependent tasks. The issues are created, assigned and sequenced without human action. A Medium-risk PR merges once Review and complete CI pass, and a High-risk PR waits for a human.
- Self-improving: seed a flaky test and a stale document. The recurring agents open two ordinary PRs, each classified and gated like human work, and neither touches a protected policy path.

**Acceptance Scenarios**:

1. **Given** Long-horizon mode and an analyzed spec, **When** the Lead runs, **Then** issues are created, assigned and sequenced without human action, and only High- and Critical-risk PRs wait for a human.
2. **Given** Self-improving mode, **When** a recurring agent proposes a change to its own gates, **Then** the PR is Critical risk and needs a human (Article VI).

---

### Edge Cases

- **Too little data**: a metric's window holds fewer than its minimum sample. It reads "insufficient data" with the sample size, and no promotion that depends on it can be proposed.
- **Agent-merge metrics in Shadow mode**: agents merge nothing while Shadow is active. The agent-attributed slices of escaped defects, revert/rollback rate and flaky-test rate read "not applicable: mode shadow" for those windows, not zero. Every row of FR-013 as a whole is still computed (FR-015).
- **Demotion during a merge**: a demotion fires while a PR is mid-merge under the old mode. The merge completes only if it also satisfies the new mode's rules. Otherwise auto-merge is cancelled and the PR waits for a human.
- **Two guardrails at once**: two guardrail metrics trip in the same evaluation. The system demotes one level per evaluation, records both triggers, and re-evaluates on the next cycle.
- **Skipping modes**: a human tries to promote past several modes at once. The policy requires each intermediate mode's criteria to have held. Otherwise the request is refused with the missing criteria named.
- **Wrong approver**: any account other than Smokey's approves a promotion to Long-horizon or Self-improving. The approval is refused and recorded.
- **Smokey not available**: Smokey's account has not acted on a proposal for one of the two highest modes. The proposal waits. It never falls back to another approver, and it never becomes approved by timing out (inferred from "Smokey should be the only one"). Demotion never waits for Smokey.
- **Event store unavailable**: the event store cannot be read when the evaluation runs. The evaluation is recorded as "not run" with the reason, and no promotion is proposed. Demotion is evaluated only against the last complete scorecard snapshot. Nothing in that evaluation can raise the active mode.
- **Incident from a human merge**: an incident is caused by a human-merged PR in Guarded mode. It counts toward quality metrics but is attributed to the actor who merged it (FR-016), so agent and human outcomes stay distinguishable.
- **Wrong stuck verdict**: Jev marks a session stuck that was in fact making progress, and the Lead or a person records the verdict as wrong. The episode still counts toward the stuck rate, and it also counts in the false-stuck rate's numerator, once per episode (FR-022; spec 008 FR-049).

## Requirements *(mandatory)*

### Functional Requirements

**Autonomy modes**

- **FR-001**: The system MUST support five ordered modes: Shadow, Agent implementation, Guarded autonomous, Long-horizon and Self-improving. It MUST start in Shadow.
- **FR-002**: In Shadow mode, agents MUST be limited to analysis and recommendations, and a human MUST perform every consequential mutation, with one exception the person chose. A person MAY approve the Spec Kit–Gitea bridge's dry-run plan (spec 004 FR-022), and the gateway then carries out that plan's writes as human-approved writes ("Both Create issues by hand and Approve; gateway writes it", project intake R3; spec 002 FR-037). The approval covers only the entries of the plan it names. It never covers auto-merge, reviews, review requests, branch creation or lease grants (spec 002 FR-037, inferred there). Every other agent mutation MUST be refused by the control plane's autonomy-mode gate (spec 001 FR-030) and, at write time, by the gateway's mode check (spec 002 FR-024). Both read the active-mode record (FR-018). Jev's comment-and-label writes record observations, not engineering work, and are not refused in any mode (spec 002 FR-024; spec 008) (inferred).
- **FR-003**: In Agent implementation mode, PSE MAY branch, code, test, create PRs and update its assigned issues. Review MUST perform an independent automated review. A human MUST remain the merge authority.
- **FR-004**: In Guarded autonomous mode, Low-risk PRs MAY merge automatically once all of these gates pass: protected-branch, CI, Review, freshness and dependency. Medium, High and Critical PRs MUST still require a human approval.
- **FR-005**: In Long-horizon mode, the Lead MAY decompose validated specs, populate Gitea, assign eligible tasks, recover interrupted sessions, sequence dependencies and close completed work. Interrupted sessions include sessions stopped because they were not making successful progress or were stuck (project intake Q17, Q19, Q21). Two further rules apply in this mode:
  - Elevated-risk review MUST stay with humans. Elevated risk means High- and Critical-risk PRs as spec 006 classifies them (inferred).
  - Long-horizon is the first mode in which Medium-risk PRs MAY merge automatically, and only with Review and complete CI, as the constitution's risk table allows (inferred).
- **FR-006**: In Self-improving mode, recurring agents MAY open ordinary PRs that improve the factory: technical debt, stale docs, repeated findings, flaky tests, retrieval quality and architectural drift. Those PRs MUST pass the same gates and risk classification as any other change. Recurring agents run within the fixed capacity of "3 agent sessions + 6 subagents + the Jev agent" (project intake Q20). Jev is not one of them, because Jev never edits code (spec 008).
- **FR-007**: The active mode MUST be enforced by deterministic policy code (the control plane's autonomy-mode gate and the gateway's mode check), not by agent prompts (Article III: Agents Propose, Policy Decides).

**Promotion and demotion**

- **FR-008**: Each mode above Shadow MUST have written promotion criteria that reference scorecard metrics, thresholds and an observation window. The criteria MUST be versioned in the repository (Article I).
- **FR-009**: The system MUST propose each promotion with its evidence. A promotion MUST take effect only after a human approves it. Promotion to Long-horizon or Self-improving mode MUST be approved by Smokey and by no one else (project intake Q11: "Smokey should be the only one"; Q12: sole top-mode approver). Smokey is a person's account, not an autonomous agent (project intake Q13), so Article VI stands unchanged.
- **FR-010**: Promotion MUST move one mode at a time. Each intermediate mode's criteria MUST have held for its full window.
- **FR-011**: When a guardrail metric crosses its demotion limit in the mode policy, the system MUST demote one mode immediately, without waiting for a human, and MUST open an issue recording the trigger. The guardrail metrics are the report's list: escaped defects, revert/rollback rate, security incidents and human recovery cost. Policy code performs the demotion, never Jev or a role agent. This mechanism is proposed (inferred): the report describes promotion only, and the owner has not confirmed it.
- **FR-012**: No agent MAY change the active mode, the promotion criteria, the demotion limits or the metric definitions. Changes to the mode policy are Critical risk and require a human (Article VI: Rules Are Not Self-Amendable). The only change to the active mode that does not wait for a human is the one-step demotion of FR-011. Policy code writes it to the active-mode record (FR-018), and it can only lower the mode.
- **FR-018**: The active mode MUST be held in an active-mode record, in the record schema that spec 009 owns. The control plane's autonomy-mode gate and the gateway's mode check read this record. A missing or unreadable record MUST be read as Shadow (Article IV; the constitution's Development Workflow: "Progressive autonomy starts in Shadow mode"). The rest of this requirement is a proposed design (inferred): neither the person nor the report gave it, and it goes back to the owner with FR-011 (Assumptions):
  - the record is separate from the human-owned mode policy;
  - only the mode evaluation's policy code writes it, in two cases:
    - one step down on a demotion (FR-011);
    - one step up, and only against a recorded human approval of a promotion proposal (FR-009);
  - every write is versioned and traced (FR-020).
- **FR-019**: Every promotion proposal MUST include a constitution compliance review result covering Articles I–IX. The constitution requires the review: "Compliance is reviewed … at every progressive-autonomy promotion" (Governance). It does not say who reviews. Review prepares the result as a recommendation on the proposal, and the person who approves the promotion confirms it as part of the approval: Smokey, for Long-horizon and Self-improving (inferred). A violation in the confirmed result MUST block the promotion and MUST be handled as a defect under Article VIII (inferred: the constitution requires the review, not the block, and names Article VIII only for a violation found in merged work).
- **FR-020**: Every promotion proposal, approval, refusal and demotion MUST record a decision trace in the decision-trace schema that spec 009 owns (Article IX). Approval and demotion traces MUST be linked from the active-mode record version they set. Proposal and refusal traces MUST be linked from the promotion proposal or promotion request they concern (inferred). A visible reasoning chain MAY be kept beside the trace as an optional debug artifact, never as the record (project intake Q3: "Both").
- **FR-021**: The events behind each demotion MUST be kept as a regression fixture. The evaluation that next proposes promotion back to the lost mode MUST replay that fixture (Article VIII: Mistakes Become Mechanisms) (inferred).

**Scorecard**

- **FR-013**: The system MUST compute the metrics below. Each MUST have a written definition, a data source and a target direction. The definitions are versioned with the mode policy (FR-012). The sources are the records of this spec's upstreams:
  - the control plane's event store and transitions (spec 001);
  - role evidence packages, review verdicts and escalations (spec 003);
  - risk classes and merge evidence manifests (spec 006);
  - Jev's scans and episodes (spec 008).

  They also include records that reach this spec through those upstreams (see Assumptions): the gateway's audit records and refusal counts (spec 002 FR-022, FR-023), session checkpoint and retrieval records, model usage per provider, and human time recorded against issues (FR-017). The per-metric sources below are inferred from the report's design.

  | Domain | Metric | Source | Target direction |
  |---|---|---|---|
  | Delivery | Ready-to-Done cycle time | board transitions (001) | lower |
  | Delivery | Accepted issues per period | transitions to Done (001) | higher |
  | Review | First-pass approval rate | review verdicts (003) | higher |
  | Quality | Escaped defects | defect issues linked to merged work (001) | lower |
  | Quality | Revert/rollback rate | revert commits and PRs (001) | lower |
  | Quality | Flaky-test rate | check results across reruns of one commit (001, 006) | lower |
  | Specification | Requirements changed after implementation began | repository history of the feature's spec files after the issue entered In Progress (001) | lower |
  | Specification | Average convergence passes | spec convergence in merge evidence manifests (006) | lower |
  | Coordination | Duplicate-work incidents | lease and write-set conflicts, duplicate issues (001) | lower |
  | Coordination | Merge-conflict rate | PR mergeability events (001) | lower |
  | Context | Stale-retrieval rate | stale results rejected, recorded in role decision traces (003) | lower |
  | Context | Resume/recovery success rate | recovery assessments and their outcomes (001 FR-017) | higher |
  | Agent | Tool-call failure rate, per provider | gateway audit records and role decision traces (002, 003) | lower |
  | Agent | Incorrect-action/block rate | refused proposals and refused tool calls (001, 002) | lower |
  | Progress | Stuck rate | Jev episodes (008) | lower |
  | Progress | False-stuck rate | Jev episodes and their resolution (008) | lower |
  | Progress | Recovery success | Jev episodes and their resolution (008) | higher |
  | Economics | Cost per accepted issue, per provider | model usage, compute and human time (FR-017) | lower |
  | Human load | Escalations per accepted issue | escalation records (003, 008) | lower |
  | Human load | Human recovery cost | human interventions to recover agent work (001, 008) | lower |
  | Security | Unauthorized-action attempts blocked | gateway refusal counts and control-plane refusals (002 FR-023, 001) | all blocked |
  | Security | Security incidents | issues a person classifies as security incidents, attributed to the merge or action that caused them (001) | lower |

  The table has 22 metrics:
  - 17 are the report's scorecard: every row except the three Progress rows, "Human recovery cost" and "Security incidents".
  - The three Progress rows are Jev's metrics from spec 008 (FR-022).
  - "Security incidents" and "Human recovery cost" come from the report's target sentence. They are added so that every guardrail of FR-011 has a definition (inferred).
  - Human recovery cost counts, per accepted issue, the human interventions needed to recover agent work: reverts a person performs, recovery outcomes a person records, Jev escalations that reach a person, and parked work items a person resets (inferred).
- **FR-014**: The scorecard MUST NOT use counts of agent actions or generated lines of code as success measures.
- **FR-015**: Every metric value MUST link back to the records it was computed from. These links never expire, because events have no time limit (project intake Q16; spec 001 FR-007). A metric MUST read "insufficient data", with its sample size, when its window lacks the minimum sample set for that metric in the mode policy. It MUST read "not applicable", with the reason, only where the active mode leaves it no possible subject. In Shadow mode, every row of FR-013 is computed as a whole, and only these read "not applicable: mode shadow", because agents merge nothing (inferred):
  - the agent-attributed slices (FR-016) of escaped defects, revert/rollback rate and flaky-test rate.

  Every other row and slice shows a value or "insufficient data". Any other mode-based "not applicable" case MUST be listed, with its reason, in the mode policy (inferred). A metric MUST never show a blank, or a zero standing in for missing data (Article IV).
- **FR-016**: Quality and human-load metrics MUST attribute each outcome to the actor who merged or acted, so that agent and human performance stay separable. The possible actors are:
  - a role, identified by its own Gitea bot account (project intake Q15). A subagent's outcome is attributed to its parent session's role and account, because a subagent works under its parent's bot account (spec 001 FR-034) (inferred);
  - the control plane, acting as `system` through its own Gitea bot account, for the moves the control plane's transition table assigns to it (spec 001 FR-031). Its outcomes count on the agent side, not the human side (inferred);
  - Jev, identified by its own bot account;
  - a human, including Smokey's account. A human-approved plan write (FR-002) is attributed to the person who approved the plan, with Lead's bot account recorded beside it (spec 002 FR-037) (inferred).
- **FR-017**: Cost per accepted issue MUST include all work on the issue, including rejected attempts:
  - model usage per provider: Claude, Ollama cloud and Ollama local (project intake Q7). Ollama local has no billed usage, so its cost is counted as compute on the host (inferred);
  - compute;
  - human review time, taken from time a person records against the issue (inferred). When no human time is recorded, the metric says so rather than counting it as zero (Article IV).

  Cost per accepted issue MUST be shown to Smokey on the scorecard and MUST NOT block promotion by itself (project intake Q23: "Inform Smokey only").
- **FR-022**: The scorecard MUST take Jev's stuck rate, false-stuck rate and recovery success from spec 008 as inputs, per role and per session, over a window. Spec 008 FR-049 defines them (inferred there, not the person's words). In short:
  - **stuck rate**: the share of supervised sessions with at least one episode that reached `health.stuck` for a reason other than dead. Dead sessions are counted separately;
  - **false-stuck rate**: the share of stuck episodes that the Lead or a person records as wrong, because the session was making progress. A stuck verdict counts once per episode, however many stuck scans the episode holds. A wrong episode is therefore also in the stuck rate;
  - **recovery success**: the share of stuck episodes that end with durable progress resumed, without the work item being parked.

  Where this summary and spec 008 FR-049 differ, spec 008 wins.

### Key Entities

- **Autonomy mode**: one of five ordered levels of agent authority. It has permitted actions, promotion criteria and demotion limits.
- **Mode policy**: the versioned, human-owned file that defines modes, criteria, windows, per-metric minimum samples, demotion limits and metric definitions. Changes to it are Critical risk.
- **Active-mode record**: the current mode, its version, and the approval or demotion that set it, with that decision's trace (FR-020). The control plane's gate and the gateway read it. Keeping it separate from the mode policy, with only policy code writing it, is a proposed design (FR-018, inferred).
- **Promotion proposal**: a system-generated request to move up one mode. It carries the metric values, the window, a constitution compliance review result (FR-019) and links to its proposal and refusal traces (FR-020). A human resolves it, and only Smokey resolves proposals for Long-horizon and Self-improving.
- **Demotion record**: an automatic one-level drop with its trigger metric, window, events and regression fixture.
- **Scorecard metric**: a named measure with a definition, source, window, minimum sample, attribution and target direction.
- **Scorecard snapshot**: the computed values of all metrics for one window, linked to their source records.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of installations start in Shadow mode, and 0 agent-initiated mutations succeed while Shadow is active, other than the human-approved plan writes and Jev's observation writes that FR-002 names.
- **SC-002**: 0 promotions take effect without a recorded human approval. 0 promotions to Long-horizon or Self-improving take effect without Smokey's recorded approval. 100% of guardrail breaches trigger a demotion within one evaluation cycle (proposed default: at most 24 hours).
- **SC-003**: From the first full observation window after rollout (proposed default: 4 weeks), every metric in FR-013 is computed for every window. Each shows a value, "insufficient data" with its sample size, or "not applicable" with its reason. "Not applicable" appears only in the cases FR-015 lists or the mode policy lists under FR-015, and 0 show a blank or a zero for missing data. After the first two windows outside Shadow mode, at most 2 metrics read "insufficient data" in any window that meets the accepted-issue minimum sample (proposed default).
- **SC-004**: [NEEDS CLARIFICATION: the headline target. The report and the intake set no number or timeframe (project intake row S9 and its open item "for specify (spec 007)"). Confirm or replace the proposed default below.]
  - Proposed default: after the system reaches Guarded autonomous mode, accepted issues per week rise by at least 30% within 3 months, compared with the Shadow-mode baseline. This is measured at the fixed capacity of "3 agent sessions + 6 subagents + the Jev agent" (project intake Q20), split one session per role with at most one issue in build at a time (project intake R1). The rise therefore has to come from less waiting and rework per issue, not from more issues in build at once (inferred).
  - Guardrails: escaped defects, revert rate, security incidents and human recovery cost stay at or below their Shadow-mode baselines (the report's "without worsening").
- **SC-005**: Escalations per accepted issue fall by at least 40% between Agent implementation mode and Long-horizon mode (proposed default).
- **SC-006**: 100% of unauthorized-action attempts in each quarter are blocked and appear in the scorecard.
- **SC-007**: 100% of promotion proposals carry a compliance review result. 100% of proposals, approvals, refusals and demotions have a decision trace (FR-020). Every approval and demotion trace is linked from the active-mode record version it set, and every proposal and refusal trace from the promotion proposal or request it concerns.
- **SC-008**: In a replay suite, changing only cost per accepted issue changes 0 promotion outcomes (project intake Q23).

## Assumptions

- **Forge and enforcement**: Gitea 28.x hosts work state and enforces protected-branch rules (project intake Q1: Gitea only). The control plane's autonomy-mode gate (spec 001 FR-030) and the gateway's mode check enforce the active mode. The gateway's mode check is spec 002 FR-024, with the approval table in FR-025.
- **Runtime**: the role agents run in the LangGraph service (project intake Q2). The mode is read at dispatch time by the control plane and again at write time by the gateway.
- **Host**: everything runs on one MacBook Pro M4 Pro with 24 GB RAM, about 18 GB of it usable after macOS (project intake Q22; data-model intake Q14, revised). Gitea, the LangGraph service, SQLite, local Ollama and the scorecard computation all share it.
- **Scale**: first-year scale is "10 Agents and 1 User" (data-model intake Q8, revised), the same as the capacity of "3 agent sessions + 6 subagents + the Jev agent" (project intake Q20). The fixed capacity bounds throughput, so SC-004 cannot be met by adding sessions (inferred). The person split the 3 agent sessions "One per role (Recommended)": one session each for Lead, PSE and Review, with at most one issue in build at a time (project intake R1). That is the tighter limit on accepted issues per period, and so on the sample sizes below and on SC-004 (inferred). With one user, the person who approves lower promotions and the person acting as Smokey may be the same. Promotions to the two highest modes must still come from Smokey's account (inferred).
- **Windows**: the default observation window is 4 weeks per promotion step, with a minimum sample of 20 accepted issues. Both are proposed defaults (inferred). Per-metric minimum samples and exact thresholds are set in planning and versioned in the mode policy. Planning checks whether 20 accepted issues per 4 weeks is reachable with one PSE session and at most one issue in build at a time (project intake R1).
- **Demotion and the active-mode record not confirmed**: automatic demotion (FR-011), the separate active-mode record and its writer rules (FR-018), and the edge cases that depend on them are proposed, not confirmed. The report and the constitution describe promotion only, and neither says where the active mode is held. `/speckit-intake-refine` puts these mechanisms back to the owner.
- **Numeric targets**: the numeric targets in Success Criteria are proposed defaults. The owner has not confirmed a headline target (project intake row S9). The guardrail side follows the report ("without worsening"): at or below the Shadow-mode baseline. Spec 006 SC-006 sets the same bound for escaped defects, at or below the Shadow-mode baseline, and leaves any reduction target to the owner.
- **Models**: models are Claude and Ollama, both cloud and local ("Ollama (cloud and local) alongside Claude Code models.", project intake Q7; constitution v1.1.0 per Q14). Billed model cost is read from each provider's usage reporting. Ollama local cost is compute on the MacBook (inferred). Health, policy and authority decisions stay in plain code (Article III).
- **Stack**: the reading of project intake Q10 puts the mode evaluation, the policy and decision core, in OCaml (inferred from the question's recommended option). The scorecard computation is data work, so it is in Python ("Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management.", Q10). Storage is SQLite (project intake Q9) under the data model of spec 009.
- **Data from specs without a direct edge**: specs 002, 004, 005 and 009 are not direct dependencies of this spec under the fixed dependency map. Records that originate in them reach this spec through its upstreams (001, 003, 006, 008) and the shared record schemas that spec 009 owns (inferred). These include the gateway's audit records (002 FR-022), with the human-approved mark on plan writes (002 FR-037), its refusal counts (002 FR-023), and the session checkpoint and retrieval records. The Long-horizon Lead populates Gitea under its role contract (spec 003). This spec does not depend on the Spec Kit–Gitea bridge (spec 004). FR-002 only names the bridge's approved plan as a Shadow-mode exception, which the gateway enforces (spec 002 FR-037).

## Dependencies

- **Upstream**:
  - **001-engineering-control-plane**: 007 consumes the event store and board transitions for the delivery, quality, coordination and human-load metrics. It also consumes the recovery assessments (001 FR-017) for resume/recovery success, and the autonomy-mode gate (001 FR-030), which applies the active mode and per-mode rules this spec supplies. It also consumes the `system` actor and its own bot account (001 FR-031) and the subagent rule (001 FR-034) for attribution (FR-016).
  - **003-role-agent-contracts**: 007 consumes the role contracts as the ceiling each autonomy mode restricts (003 FR-029). It also consumes the roles' measured outcomes (evidence packages, review verdicts, escalations and decision traces) for the review, context, agent and human-load metrics.
  - **006-quality-evidence-gates**: 007 consumes risk classes, merge evidence manifests and the merge evidence gate. These feed the quality and review metrics. Guarded autonomous mode requires them (FR-004), and so does the elevated-risk rule of Long-horizon mode (FR-005).
  - **008-jev-progress-watchdog**: 007 consumes Jev's stuck rate, false-stuck rate and recovery success (008 FR-049), with the episodes and escalations they are computed from. These are scorecard inputs (FR-022), and they also feed human recovery cost (FR-013).
- **Downstream**: none. No spec depends on 007.
- **Build order**: 009 → 001 → 002, 005 → 003, 004 → 006, 008 → 007. This spec is built last.
- **Constitution** (v1.1.0):
  - Art. I: the mode policy and metric definitions are versioned in the repository (FR-008).
  - Art. II: no agent promotes itself, and approval is separated from the work it judges (FR-009, FR-012).
  - Art. III: modes are enforced by deterministic policy code, not prompts (FR-007).
  - Art. IV: metrics read "insufficient data" or "not applicable" rather than a false zero, and a missing mode reads as Shadow (FR-015, FR-018).
  - Art. VI: promotion and mode-policy changes are Critical risk and need a human (FR-012).
  - Art. VIII: demotions become regression fixtures (FR-021), and compliance violations found at promotion become defects (FR-019) (both inferred).
  - Art. IX: decision traces for every mode decision (FR-020).
  - Development Workflow: Shadow mode first, one step at a time. The person's one Shadow-mode exception, the human-approved plan write, still needs a person's approval for every write (FR-002; project intake R3).
  - Governance: a compliance review at every promotion (FR-019).

## Clarifications

### Session 2026-10-22

- Q: The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target? → A: Gitea only (project intake Q1)
- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service (project intake Q2)
- Q: The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work? → A: Both (project intake Q3)
- Q: How far should the dependent specs go in this first pass? → A: Constitution plus full spec set (project intake Q4)
- Q: Which models and embeddings should the RAG and reasoning chains use? → A: "Ollama (cloud and local) alongside Claude Code models." (project intake Q7)
- Q: Your stack lists 'a vector DB' and 'knowledge graphs' with SQLite, but no product. Which stores should the specs and code use? → A: "SQLite with sqlite-vec and custom Python Vector Databases. I want to create the Meta Data Schema and Structure. Create a new Data Modell that can scale for all current and future users when using this applications." (project intake Q9)
- Q: Which parts are OCaml and which stay Python? → A: "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." (project intake Q10)
- Q: Who may approve promotion to the Long-horizon and Self-improving autonomy modes (spec 007 FR-009)? → A: "an agent called Smokey, and Smokey should be the only one" (project intake Q11)
- Q: You said Smokey 'should be the only one'. The only one who may do what? (I read Jev and Smokey as two different agents: Jev watches sessions, Smokey approves.) → A: Sole top-mode approver (project intake Q12)
- Q: Is Smokey an autonomous agent or an account a person controls? Art. VI says agents may not authorize changes to their own authority. → A: A person's account (project intake Q13)
- Q: The constitution allows Claude only, through the official SDK. Adding Ollama (cloud and local) amends it. How should I handle that? → A: Amend to v1.1.0 (project intake Q14)
- Q: How should agents authenticate to Gitea (spec 002)? → A: "Each role gets its own Gitea bot account." (project intake Q15)
- Q: How long are raw deliveries and normalized events kept (spec 001 FR-007)? → A: "Events have no time limit." (project intake Q16)
- Q: When should a running session be stopped? → A: "A session stops only when it is not making successful progress or is stuck." (project intake Q17)
- Q: How many subagents may run at once? → A: "At most 2 subagents per container, per role and per Gitea bot account." (project intake Q18)
- Q: What does 'stuck' mean? → A: "A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing." (project intake Q19)
- Q: What is the peak capacity the system must sustain (spec 001 FR-021)? → A: "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20)
- Q: When a session is stuck: stop it automatically, or escalate to the user or Smokey first? → A: Checkpoint and stop, then escalate (project intake Q21)
- Q: Where should Gitea, the LangGraph service and the local Ollama models run? → A: All on the MacBook (project intake Q22)
- Q: Spec 007 asks: should a cost ceiling per accepted issue block promotion to a higher autonomy mode? → A: Inform Smokey only (project intake Q23)
- Q: How many people and agents should the data model support in its first year? → A: "10 Agents and 1 User" (data-model intake Q8, revised)
- Q: Which technical limits must the data model respect? → A: "Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption." (data-model intake Q14, revised)
- Q: Spec 001 caps the team at 3 agent sessions. How should those 3 be split between Lead, PSE and Review? → A: "One per role (Recommended)" — one session each for Lead, PSE and Review; at most one issue in build at a time (project intake R1)
- Q: Spec 004: in Shadow mode, the Spec Kit→Gitea bridge only produces a dry-run plan. How should a person apply that plan? → A: "Both Create issues by hand and Approve; gateway writes it" — both paths: a person creates the issues by hand (the bridge reports them unconfirmed for Lead to confirm), or a person approves the plan and the gateway carries it out as a human-approved write (changes spec 002 FR-024 and spec 007 FR-002) (project intake R3)
