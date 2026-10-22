# Feature Specification: Jev, the Progress Watchdog for Agent Sessions

**Feature Branch**: `008-jev-progress-watchdog`

**Created**: 2026-10-22

**Status**: Draft

**Input**: User description: the person's answers in the project intake: "A session stops only when it is not making successful progress or is stuck." (Q17); "A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing." (Q19); "3 agent sessions + 6 subagents + the Jev agent." (Q20); and "Checkpoint and stop, then escalate" (Q21). The design comes from the research report [`docs/research/reports/Jev watchdog for coding agents.md`](../../docs/research/reports/Jev%20watchdog%20for%20coding%20agents.md), called "the Jev report" below, as adopted in the project's decision record for spec 008.

## User Scenarios & Testing *(mandatory)*

Jev is the team's fourth role. It is a watchdog with comment-and-label authority only (spec 003 FR-028). Every 10 minutes it reads what each live session has actually done: its lease, decision traces, checkpoints and command log, and for a PSE its branch and CI. Plain code then decides whether the session is healthy, hung, spinning or dead. Jev proposes, and the Lead, as policy owner, decides and carries out any hard stop (Constitution Art. III). Jev never edits code. Everything runs on one MacBook (project intake Q22), at a peak of "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20). One person reads every escalation that reaches the top level.

### User Story 1 - Detect a hung or spinning session and escalate without false alarms (Priority: P1)

The person wants sessions to keep working while they make progress, and to stop only when they don't: "A session stops only when it is not making successful progress or is stuck." (Q17). In the person's words, stuck means "A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing." (Q19).

Jev tells three failures apart:

- a **dead** session, whose lease heartbeat stopped;
- a **hung** session, whose agent loop went silent although the process lives;
- a **spinning** session, whose loop is busy while nothing durable changes.

It also recognizes repetition loops, repeated command timeouts and CI that keeps failing. One bad scan earns a warning and a nudge. A second consecutive bad scan is a stuck verdict, which goes to the Lead. None of these count against a session: long builds, waiting on a person, start-up, cancelled CI runs and missing CI.

**Why this priority**: Every other part of Jev acts on this verdict. A missed stall keeps a session holding a lease and a share of one machine's capacity. A false stuck verdict stops a session that was progressing, which Q17 forbids. Precision outranks speed here. A hung session burns no tokens while it waits, and loops are caught first inside the session (Jev report §Two consecutive scans confirm, and the first one should nudge).

**Independent Test**: Replay labelled evidence fixtures through the decision function, with no Gitea and no live session. Each fixture puts traces, command logs, lease states, branch heads and CI statuses on a timeline, and its verdict sequence must match its label:

- hung and spinning fixtures warn on the first bad scan and are stuck on the second;
- loop and timeout fixtures are stuck on the scan that sees the pattern;
- healthy long-work fixtures stay ok.

**Acceptance Scenarios**:

1. **Given** a PSE session whose last agent-loop event was 21 minutes ago, with no tool call in flight and no wait on a person, **When** Jev scans, **Then** it records `health.warn` with reason hung, nudges the session (L0) and adds `jev/warning`. **When** the next observed scan still finds no agent-loop event, **Then** Jev records `health.stuck`, replaces the label with `jev/stuck` and notifies the Lead (L1) (FR-014, FR-023, FR-032, FR-036).
2. **Given** a session whose runtime heartbeat renews its lease every minute, but whose agent loop has logged nothing for 25 minutes, **When** Jev scans, **Then** the session counts as hung, not dead. Heartbeats prove only that the process is alive (FR-006, FR-012).
3. **Given** a build that started 30 minutes ago with its own 45-minute timeout, and durable progress 35 minutes ago, **When** Jev scans, **Then** the command log shows the call as started but not ended, the hung clock is paused, and the verdict is `health.ok`. **Given** the same build with no durable progress for longer than the progress window, **Then** the session can still be found spinning, because an in-flight call pauses only the hung clock (FR-010, FR-014, FR-015, FR-018).
4. **Given** a session that asked the person a question 3 hours ago and is still waiting, **When** Jev scans, **Then** the stall clocks, the loop rules and the CI rule are all paused, and the verdict is `health.ok` (FR-014, FR-015, FR-018).
5. **Given** a session that started 12 minutes ago and has written no agent-loop event yet, **When** Jev scans, **Then** it is in start-up grace and is not judged hung (FR-014).
6. **Given** a session that runs a tool call every minute but has pushed nothing, written no checkpoint and flipped no test for longer than the progress window, **When** Jev scans twice, **Then** the first scan warns with reason spinning and the second records `health.stuck`. An ok scan in between that shows activity but no durable progress does not reset the count (FR-009, FR-015, FR-023).
7. **Given** the last 20 events end with the same call failing with the same error 3 times, **When** Jev scans, **Then** it warns and nudges. **Given** a 4th identical failure, **Then** the scan that sees it records `health.stuck` without waiting for a second bad scan (FR-016).
8. **Given** any of these patterns, **When** Jev scans, **Then** the session is stuck (FR-010, FR-016):
   - 4 identical call-and-result pairs;
   - 6 events alternating between two calls;
   - 3 consecutive agent messages with no tool call.

   **Given** a test rerun three times with three different results, **Then** no loop rule fires.
9. **Given** 3 consecutive command timeouts, **When** Jev scans, **Then** the session is stuck. A successful command between timeouts resets the count (FR-017).
10. **Given** a loop rule fired in the last observed scan and the session has completed no tool call since, **When** Jev scans again, **Then** the loop and timeout rules are not applied a second time to the same calls (FR-018).
11. **Given** a PSE branch whose last 3 head commits each finished CI with a real failure, and whose set of failing checks did not shrink, **When** Jev scans, **Then** the scan is bad with reason CI not converging (FR-019, FR-020). These do not count:
    - a cancelled run;
    - a head with no CI status at all;
    - a commit whose set of failing checks shrank.

    A success resets the count.
12. **Given** the CI rule's first bad scan, **When** the session pushes another commit whose CI also fails, **Then** that push does not reset the CI rule's debounce, and the next bad scan is stuck (FR-025).
13. **Given** 6 failing commands in one scan, **When** the same scan is bad under another rule, **Then** the failures are added to it as a supporting reason. **When** no other rule makes the scan bad, **Then** the failures do not make it bad, whether or not it shows durable progress (FR-021).
14. **Given** Gitea is unreachable during a scan, **When** Jev scans, **Then** it records `health.unknown` with the reason (FR-011, FR-024):
    - no label, comment, count, baseline or episode changes;
    - the next observed scan measures "since the last scan" from the last observed scan.
15. **Given** a session whose lease heartbeat is older than its lease TTL, **When** Jev scans, **Then** it records the session as dead and notifies the Lead. It requests no stop, because lease expiry already frees the work (FR-013).
16. **Given** a Review session, which has no branch, **When** Jev scans, **Then** the session is judged on its lease, traces, checkpoints and command log only. **Given** a PSE session that names no branch, **Then** its scan is reported as an error for that session alone (FR-005, FR-008, FR-046).
17. **Given** one session's evidence, earlier scan records and thresholds, **When** the decision function runs on them twice, including once on another machine, **Then** both runs return the same kind, reasons, next action and episode. The decision function reads nothing else (FR-003).

---

### User Story 2 - Stop a stuck session safely (Priority: P2)

When a session is stuck, the person chose "Checkpoint and stop, then escalate" (Q21). Jev stops nothing itself. The ladder runs like this:

1. Jev asks the session to stop.
2. The session gets one scan to write its checkpoint and release its lease.
3. If it does not, Jev hands the hard stop to the policy owner, the Lead, who revokes the lease (spec 001 FR-032).

Lease expiry and the lease-epoch fence are the backstop: a stopped session's late write through the control plane or the gateway is refused (spec 001 FR-032). A `git push` passes through neither, so whether a stopped session's late push can land or merge depends on where the fence lives, which is still open (FR-029). If the Lead stays silent, or the episode stays unresolved, a person is paged. A stopped session's episode is resolved once the work item's recovery outcome is recorded (FR-052). A work item that keeps getting stuck after automatic restarts is parked until a person resets it.

**Why this priority**: Detection without a safe stop leaves a stuck session holding its lease and its branch. The stop must also never turn into Jev grading or repairing work itself (Art. II, Art. III). The Jev report §Jev proposes the stop; the policy owner carries it out makes this point, citing [OWASP LLM06:2025](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) on excessive agency.

**Independent Test**: Use a fixture control plane and a Gitea test instance. Drive a session into a stuck verdict, then play out four endings:

- the session obeys within the grace window;
- it ignores the request until the Lead revokes its lease;
- the Lead stays silent;
- the work item is restarted twice and gets stuck again.

Each ending produces the expected messages, labels and escalation level, and a write through the control plane or the gateway that presents the revoked epoch is refused.

**Acceptance Scenarios**:

1. **Given** a PSE session's first stuck verdict, **When** Jev records it, **Then** (FR-002, FR-029, FR-032):
   - the episode's living comment carries a `health.stuck` message whose next action is "request stop";
   - the work item carries `jev/stuck`;
   - the Lead is notified (L1);
   - Jev changes no code, lease or board state.
2. **Given** the session writes a checkpoint at or after the request and releases its lease within one scan, **When** Jev scans, **Then** it records `session.stop` with next action "notify Lead", and the Lead's recovery assessment follows (spec 001 FR-017). Whatever its signals say afterwards, the session is never reported as recovered and never flagged hung again (FR-030).
3. **Given** one scan has passed since the request without a checkpoint and a lease release, **When** Jev scans, **Then** the next action becomes "hard stop", addressed to the Lead. **When** the Lead revokes the lease (spec 001 FR-032), **Then** Jev's next scan records `session.stop`, and a later write through the control plane or the gateway that presents the stopped session's old epoch is refused (spec 001 FR-032; FR-029, FR-030). A late `git push` passes through neither. Whether its commits can merge depends on where the epoch fence lives, which is still open (FR-029). Spec 001's recovery assessment and re-dispatch head check find such commits (spec 001 FR-017, FR-037).
4. **Given** the Lead has not acknowledged the stuck verdict within 1 scan, or the episode is still unresolved 3 scans after its first stuck verdict, **When** Jev scans, **Then** it pages the person (L2) once, by editing the living comment (FR-032, FR-034).
5. **Given** a work item whose sessions have been restarted automatically 2 times, **When** its session is stuck again, **Then** Jev adds `jev/parked` and pages the person. No automatic restart follows until a person resets the breaker (FR-033).
6. **Given** the stuck session is the Lead's own, **When** Jev records the stuck verdict, **Then** the escalation goes straight to the person, who carries out any hard stop (FR-031).
7. **Given** a session that has pushed a commit every 40 minutes for 6 hours, whose head CI passes, and on which no hung, loop or timeout rule fires, **When** Jev scans, **Then** no stop is ever requested, however long the session runs (FR-028).
8. **Given** a session that pushes WIP commits during its stop grace window, **When** their CI fails, **Then** those commits do not count toward the CI rule (FR-019).
9. **Given** a stopped session's episode (FR-030), **When** the work item's recovery outcome is recorded (spec 001 FR-017), **Then** Jev's next observed scan resolves the episode: it removes `jev/stuck`, marks the comment resolved as stopped with the outcome, and sends no further L2 re-notification (FR-034, FR-052). **Given** the work item is parked, **Then** `jev/parked` stays until a person resets the breaker (FR-033).

---

### User Story 3 - Keep an auditable, idempotent record (Priority: P3)

The person and the Lead read one living comment per stall episode on the work item, edited in place as the episode moves. One `jev/*` label shows the episode's current state. Jev's scan history answers "what did Jev see, when, and why did it decide that". Its messages follow one schema, which the typed core in OCaml reads too. A Jev that crashes and retries never posts twice, never pages twice, and never acts with more rights than it should have.

**Why this priority**: Stories 1 and 2 deliver value even if comments are duplicated. This story makes Jev quiet, trustworthy and reviewable over months of operation (Art. IV, Art. IX), and it feeds the scorecard's progress metrics (spec 007 FR-022).

**Independent Test**: Against a Gitea test instance, run an episode through warn, stuck, stop requested and stopped. Along the way, inject crashes at each recovery point, delete the comment, make a label write fail and run one scan slot twice. Afterwards:

- the work item has exactly one Jev comment for the episode and the right label;
- scan history has one record per session per slot;
- the exported schema check passes.

**Acceptance Scenarios**:

1. **Given** an episode that moves through warn, stuck, stop requested and stopped over 4 scans, **When** the person opens the work item, **Then** they find (FR-035, FR-036, FR-037):
   - exactly one Jev comment for the episode, edited in place;
   - in it, the episode's marker, its latest message as fenced JSON and a plain-language explanation;
   - exactly one `jev/*` label.
2. **Given** Jev crashed after posting a comment but before recording its id, **When** the scan is retried, **Then** Jev finds its own comment by its account and the episode marker and edits it. No second comment appears (FR-037, FR-039).
3. **Given** a person deleted Jev's comment, **When** the next scan updates the episode, **Then** Jev creates the comment again (FR-037).
4. **Given** the comment write succeeds and the label write fails, or the reverse, **When** later scans run, **Then** each write is retried on its own until it succeeds, and neither blocks the other (FR-037).
5. **Given** the same scan slot runs twice after a crash, **When** both runs finish, **Then** scan history holds one record per (session, scan), and both runs used the same episode ids and idempotency keys (FR-026, FR-039, FR-045, FR-046).
6. **Given** a healthy or unobservable session, **When** Jev scans, **Then** the `health.ok` or `health.unknown` message is recorded only in scan history, and nothing is written to Gitea (FR-035).
7. **Given** an episode whose session then shows an ok scan with durable progress, **When** the next observed scan is also ok, **Then** the episode is resolved: its label is removed and its comment marked resolved (FR-026, FR-027).
   - If Gitea refuses the write, it is retried on later scans until it succeeds.
   - **Given** a relapse inside the one-scan hold instead, **Then** the relapse joins the same episode and comment.
8. **Given** a change that makes the type Jev publishes differ from `schemas/jev-message.v1.json`, **When** CI runs, **Then** the schema check fails. **Given** 1,000 messages Jev produced, **When** the OCaml side reads them through the exported schema, **Then** 100% decode with identical values (FR-042, FR-044).
9. **Given** a message with an unknown field, a wrong type, or a kind outside the five kinds, **When** it is built or read, **Then** it is refused, never coerced (FR-042, FR-043).
10. **Given** any of these at the start of a scan run, **When** the run starts, **Then** Jev refuses to run, reports which right is wrong and writes nothing to Gitea (FR-040, FR-041):
    - Jev's account has repository push or admin permission;
    - it can push or merge the default branch;
    - its rights cannot be read.
11. **Given** `jev/stuck` is defined as an organisation label and `jev/warning` as a repository label, **When** Jev applies them, **Then** it finds both and applies each by its ID. It keeps every other label on the work item and confirms the result holds the expected ID (FR-036, FR-038).
12. **Given** the explanation model is unreachable, or writes text that contradicts the verdict, **When** Jev posts, **Then** the verdict, reasons, next action and labels are unchanged. A plain template explanation is used when no model text is available (FR-004).
13. **Given** a scan run is still running when the next slot starts, **When** the second run starts, **Then** the two runs never scan at the same time (FR-046).
14. **Given** Jev's operating contract in the repository, **When** it is checked against spec 003's contract format, **Then** it states every field of FR-001. Its permissions are exactly read access, its own comments and its `jev/*` labels (FR-001, FR-002).
15. **Given** a stuck verdict, **When** Jev records it, **Then** the scan record links a decision trace that holds the decision, the evidence facts, the thresholds version, the changed labels and comment, and the next action. No hidden model reasoning is stored (FR-051).
16. **Given** a 4-week window with 10 supervised sessions, **When** Jev computes its metrics, **Then** the results match a hand calculation from the episodes (FR-049, FR-050):
    - 4 sessions each had one episode that reached `health.stuck`, so the stuck rate is 40%;
    - the Lead recorded 1 of those 4 stuck episodes as wrong, so the false-stuck rate is 25%;
    - 2 of the 4 episodes resumed durable progress without parking, so recovery success is 50%.

    The wrong verdict exists as a replay fixture before any threshold change is accepted.

---

### Edge Cases

- **In-flight long tool call**: a test suite or build runs for 50 minutes inside its own 60-minute timeout. The hung clock is paused for as long as the call stays inside its timeout. Once the call overruns its timeout, the hung clock resumes. The spinning clock keeps running throughout, because an in-flight call pauses only the hung clock (FR-014, FR-018). A call that names no timeout gets the harness's default tool timeout (Assumptions).
- **Waiting on a human**: the session has asked the person a question and is waiting. Waiting is healthy, not hung (Jev report §Silence catches hangs, citing [Anthropic: Measuring agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy)). These are all paused for as long as the wait lasts (FR-018):
  - the hung and spinning clocks;
  - the loop rules;
  - the CI rule.

  Jev never escalates a session for waiting (inferred).
- **Start-up**: clone, dependency install and context loading produce no agent-loop event yet. The session is exempt from the hung check until its first agent-loop event or 2 scans, whichever comes first (FR-014).
- **CI cancelled runs**: Gitea records a cancelled Actions job as `failure`, for example when a newer push supersedes it. Jev recognizes the cancellation from the job's own status description ("Canceled after …"). The cancelled run counts neither for nor against the session. Failures reported by external CI still count (FR-020).
- **Zero-status pending**: a head with no CI statuses reads `pending`, with a total count of 0. That means "no CI reported", not "CI running", and it counts neither way (FR-019).
- **Gitea unreachable**: the scan is `health.unknown` with the reason. It changes nothing, and nothing is posted (FR-011, FR-024).
- **Duplicate scans after a crash**: Jev restarts mid-scan, and the same slot runs again. The retry reuses these, so it adds no second record, comment or page (FR-026, FR-039, FR-045, FR-046):
  - the scan id;
  - the episode ids;
  - the idempotency keys;
  - the stored comment ids.
- **Relapse within the hold**: the session recovers, then goes bad again in the next observed scan. The relapse joins the open episode and its comment, and the escalation resumes where it stood instead of starting again at L0 (FR-026).
- **All sessions pending: a shared runner outage**: every supervised PSE head reads zero-status pending. Jev raises one dependency alert in place of one verdict per session. The CI rule and spinning clock of those sessions are unobservable until a status appears (FR-022).
- **Jev's own token gains push rights**: someone widens Jev's account or team. The next scan run's self-check sees it and refuses to run, and the gateway also refuses to act as Jev (spec 002 FR-027). Jev never uses the excess right to report the problem (FR-041).
- **Session restarted**: a new incarnation of the session starts on the same work item. Commits, CI results, command-log events, traces and checkpoints from before its start time are ignored (FR-007).
- **Sessions without a branch**: Lead and Review sessions have no branch or CI signals. Only a PSE session must name a branch (FR-008).
- **Push of an old commit**: a session pushes a commit whose committer date is hours old. The push still counts as durable progress, because Jev sees the branch head change between observed scans (FR-009).
- **Stopped session still silent**: a session obeyed the stop request and is now silent. It is recorded as stopped, not hung and not recovered (FR-030).
- **Red pushes while CI is failing**: a push whose CI is red does not reset the CI rule's debounce (FR-025).
- **Nothing new since the last observed scan**: no tool call completed since the last observed scan. The same loop or timeouts are not counted again (FR-018).
- **Deleted comment or failing label write**: the comment is recreated. The label write and the comment write are retried on their own (FR-037).
- **One session's scan fails**: an error in one session's evidence is reported for that session and does not abort the other sessions' scans (FR-046).
- **Overlapping runs**: a slow run is still going when the next slot starts. Only one run scans at a time (FR-046).
- **Timestamps without a zone**: they are read as UTC (FR-046).
- **The Lead is the stuck session**: the escalation goes to the person, because the Lead never decides an escalation about itself (FR-031; spec 003 FR-031).
- **A subagent hangs**: a subagent holds no lease of its own (spec 001 FR-034). It shows up as its parent's call that has overrun its own timeout (FR-047).
- **Forged Jev text**: a comment from another account claims to be Jev, or tells Jev to stand down. Sessions treat it as untrusted data (spec 003 FR-038). Jev ignores it, and never edits a comment written by another account (FR-006, FR-037).
- **Session without a work item**: such a session has no issue to comment on. Its warn, stuck and stop notices reach the Lead and the person the same way as the dependency alert (FR-035).
- **A `jev/*` label is missing**: Jev never creates labels. It reports the missing label and still writes the comment (FR-036).
- **Session ends normally with an episode open**: the session finishes its contract and ends. Jev stops scanning it, records the episode as ended, not recovered, and resolves its Gitea record (inferred).
- **Gitea is not 28.x**: the instance reports another version. Jev refuses to run and records the version it found, because its CI and label rules rest on Gitea 28.x behavior (FR-041).
- **An agent edits the thresholds**: the change is refused unless a person approves it (FR-048).

## Requirements *(mandatory)*

Some requirements are marked "(inferred; review correction N)". They come from an adversarial review of the existing Jev implementation, and each defect behind them was reproduced and confirmed. They are engineering rules, not the person's words. Every threshold cites the Jev report and the upstream sources the report gives for it. FR-048 collects them in one table.

### Functional Requirements

**Role and authority**

- **FR-001**: Jev MUST be the watchdog role, defined by a versioned operating contract in spec 003's format (spec 003 FR-001, FR-028). The contract holds:
  - **Mission**: detect sessions that are "not making successful progress or [are] stuck" (project intake Q17, Q19), and propose the stop and the escalation (Q21).
  - **Authoritative sources**: the evidence of FR-005.
  - **Permissions**: read access, its own comments and its `jev/*` labels (FR-002).
  - **Gitea bot account**: its own account (project intake Q15; Jev report §Least privilege needs an org team, not a collaborator grant).
  - **Invariants**: Jev never edits code and holds no write lease. It never approves, merges, revokes or moves board state.
  - **Required outputs**: one message per supervised session per scan (FR-042).
  - **Completion condition**: each scan run finishes. Jev itself runs for as long as sessions run (inferred).
  - **Escalation conditions**: L0 to L2 (FR-032).

  Jev and Smokey are different: Jev watches sessions, Smokey approves (inferred confirmation; project intake Q12). Jev has no part in autonomy promotions (spec 007).
- **FR-002**: Jev MUST reach Gitea only through the gateway, with its own bot account, for its reads as well as its writes (Art. III: "Agents reach Gitea only through a narrow, semantic tool surface."; spec 002 FR-016, FR-027). It MUST write only its own comments and add or remove labels in the `jev/` scope. It MUST NOT do any of these (Art. II, Art. III, Art. VI; Jev report §Jev proposes the stop; the policy owner carries it out, citing [OWASP LLM06:2025](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/)):
  - edit code, push, approve or merge;
  - create labels or write branch protection;
  - claim, renew, release or revoke leases;
  - change board state;
  - restart sessions.
- **FR-003**: Plain code MUST decide a session's health. A pure decision function with no I/O reads one scan's evidence, the session's earlier observed scan records and the thresholds (FR-048). It returns the kind, reasons, next action and episode. The same inputs MUST always give the same verdict. No model output may decide or change a verdict (Art. III; constitution, Additional Constraints: Runtime).
- **FR-004**: A model call MAY write the plain-language explanation shown beside a verdict, and nothing else. The model may be Claude or Ollama, cloud or local (project intake Q7, Q14).
  - The call receives the verdict and its evidence facts only. It never receives raw command text, file contents, or text marked sensitive (data-model intake Q25: "Sensitive text stays local") (inferred).
  - The explanation MUST NOT change the kind, reasons, next action, episode, labels or JSON block. The JSON block is authoritative, and the explanation is labelled as model-written (inferred).
  - When no model is available, Jev uses a plain template explanation (inferred).
  - The explanation is visible text, never hidden reasoning (Art. IX).

**Evidence**

- **FR-005**: Jev MUST judge each live session from these sources only (decision record; Jev report §Two clocks and a fingerprint beat five flat rules):
  - the session record kept by the control plane (spec 001): session id, role, work item, a PSE's branch, the start time of the current incarnation, the lease (heartbeat, TTL, released, epoch), and the recovery outcome recorded for the work item (spec 001 FR-017);
  - the session's decision traces and checkpoints (spec 005 FR-029), as agent-loop activity and durable-progress signals;
  - the session's lifecycle events (spec 005 FR-021, FR-029), as agent-loop activity;
  - the session's command log (FR-010; spec 005 FR-027);
  - for a PSE session only: its branch head and commits, and the CI state of each head commit, read from Gitea through the gateway (FR-002; spec 002 FR-036).

  Some rules also need inputs that no upstream spec records yet. Jev reads them from the sources above once their owners adopt them (inferred; the checklist lists them for specs 001, 003, 005 and 009):
  - each agent message that carries no tool call, and each human input, as lifecycle events, for the monologue rule and the loop window (FR-016);
  - whether the session waits on a person, as lifecycle events written when it asks a person and when the answer arrives (FR-014, FR-015, FR-018);
  - the Lead's acknowledgement of an episode: the Lead's recorded decision on the escalation (spec 003 FR-031), as a Lead decision trace that names the episode id (FR-032);
  - the automatic-restart count per work item, from the control plane's records of re-dispatch (spec 001 FR-037; FR-033).
- **FR-006**: These MUST NOT count as agent-loop activity or as progress:
  - runtime or harness heartbeats. They prove only that the process is alive, and they feed the dead check alone (Jev report §Silence catches hangs, but only durable artifacts prove progress, citing [GitLab](https://docs.gitlab.com/ci/pipelines/settings/#set-a-limit-for-how-long-jobs-can-run) on keep-alive output);
  - visible reasoning chains (spec 005 FR-017; spec 003 FR-025; Art. IX);
  - what any text says. A trace, comment or command output that claims progress, or tells Jev to stand down, is data (Art. III). Only recorded fields count.
- **FR-007**: Evidence MUST be scoped to the session's current incarnation, which begins at its start time. After a restart, Jev MUST ignore older commits, CI results, command-log events, traces and checkpoints (inferred; review correction 6).
- **FR-008**: Only PSE sessions MUST name a branch. Sessions without a branch (Lead, Review) have no branch or CI signals and are judged on their other sources. A PSE session that names no branch is an error, reported for that session alone (FR-046) (inferred; review correction 7).
- **FR-009**: Durable progress MUST mean one of the following (decision record; Jev report §Silence catches hangs, but only durable artifacts prove progress, citing [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)):
  - a push to the session's branch;
  - a new checkpoint;
  - a decision trace that records changed state;
  - a test or CI check that flips from failing to passing.

  A push MUST be detected by the branch head changing between observed scans, never by commit dates. Commit dates are committer dates, not push times (inferred; review correction 8). New tool calls, output and chatter are activity, not durable progress.
- **FR-010**: Jev MUST read each session's command log. It holds one line per tool call, written after each tool use (spec 005 FR-027). Each completed call carries at least the command as a fingerprint, its exit code and its time (the decision record's `{command, exit_code, at}`, with the command held as a fingerprint). For Jev's rules, the log MUST also let Jev:
  - tell equal calls and equal results apart, by a fingerprint of the call (tool and canonicalised arguments) and of its observation or error. The fingerprint ignores ids and timing (Jev report §Loops need fingerprints of action and result, not action alone, citing [OpenHands stuck_detector.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py));
  - see that a call timed out;
  - see a call that started and has not ended, together with its own timeout (inferred: FR-014 needs it).

  The log MUST store calls and results as fingerprints, not text, so that a token in a command line never lands in it (inferred). Writing the log MUST never block or fail a tool call (inferred). Spec 005 owns the entry and spec 009 owns its schema; these additions are recorded here for them (inferred).
- **FR-011**: A scan that cannot observe a session MUST record `health.unknown` with the reason, and MUST NOT count as good or bad. Causes include a Gitea error, an unreadable trace or command log, and an unavailable session record. This follows Art. IV ("not run" never means passed) and the Jev report §Two consecutive scans confirm, and the first one should nudge. FR-024 says what an unknown scan may not change.

**Health states and rules**

- **FR-012**: Jev MUST tell apart three states (Jev report §Silence catches hangs, but only durable artifacts prove progress, citing [Temporal](https://docs.temporal.io/encyclopedia/detecting-activity-failures) and [Kubernetes: Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#progress-deadline-seconds)):
  - **dead**: the lease heartbeat is stale;
  - **hung**: the heartbeat is fresh, but the agent loop has logged no model response or tool event;
  - **spinning**: the loop is active, but nothing durable has changed.

  It also recognizes the repetition patterns of FR-016, FR-017 and FR-019. The person's definition of stuck maps onto these rules:

  | Q19 / Q17 wording | Jev rule |
  |---|---|
  | "A command … stops making progress" | command timeouts (FR-017); a call that overran its own timeout resumes the hung clock (FR-014) |
  | "the terminal … stops making progress" | hung (FR-014) |
  | "thought-chaining or reasoning stops making progress" | spinning (FR-015), plus monologue and repeated call-and-result loops (FR-016). Judged from decision traces and the command log, never from visible reasoning chains (FR-006) |
  | "bad code keeps failing" | CI not converging (FR-019); repeated call-and-error loops (FR-016); failing commands as a supporting signal (FR-021) |
  | "not making successful progress" (Q17) | spinning: no durable progress within the window (FR-015) |

- **FR-013**: A session MUST be dead when its lease is not released and its heartbeat is older than the lease TTL. Jev records `health.stuck` with reason dead and next action "notify Lead", on the scan that sees it (inferred: dead is reported under the stuck kind). Jev requests no stop. Lease expiry already frees the work and routes it to recovery (spec 001 FR-017; Jev report §Silence catches hangs, but only durable artifacts prove progress, for the dead state; §Leases need an epoch fence, not just a TTL, citing the [etcd Lease API](https://etcd.io/docs/v3.6/learning/api/#lease-api)).
- **FR-014**: A session MUST be hung when it has logged no agent-loop event for **20 minutes**. The Jev report §Silence catches hangs, but only durable artifacts prove progress gives this value. It cites [CircleCI](https://circleci.com/docs/reference/configuration-reference/) (10 min), [Airflow](https://github.com/apache/airflow/blob/main/airflow-core/src/airflow/config_templates/config.yml) (300 s) and [Temporal](https://docs.temporal.io/encyclopedia/detecting-activity-failures)'s margin of 0.8× the timeout over the sampling interval. The hung clock MUST pause:
  - while a tool call is still inside its own timeout (Jev report, citing [SWE-agent tools.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/tools/tools.py));
  - while the session waits on a person (Jev report, citing [Anthropic: Measuring agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy));
  - during start-up grace, until the first agent-loop event or **2 scans**, whichever comes first. The report's table row "Startup grace" calls this local policy and cites [Kubernetes startup probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-startup-probes).
- **FR-015**: A session MUST be spinning when it has shown no durable progress (FR-009) for the durable-progress window. The window runs from the later of the last durable progress and the incarnation's start. The default is **60 minutes**, and its final value is open: [NEEDS CLARIFICATION: the durable-progress window. The Jev report proposes 60 minutes as "a defensible starting point" and says no source fixes it. Should it stay 60 minutes for every role, or be set per role (Lead, PSE, Review) and recalibrated from Jev's first weeks of scan history?]
  - Sources: the Jev report §Silence catches hangs, but only durable artifacts prove progress, citing [Anthropic: Measuring agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy) (99.9th-percentile turn over 45 minutes), [GitLab](https://docs.gitlab.com/ci/pipelines/settings/#set-a-limit-for-how-long-jobs-can-run) (1 hour) and [Anthropic: Effective harnesses](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents).
  - The spinning clock pauses while the session waits on a person. An in-flight tool call does not pause it (FR-018).
- **FR-016**: Jev MUST fingerprint the last **20** completed events since the last human input (FR-005, FR-010) and apply these counts (decision record; Jev report §Loops need fingerprints of action and result, not action alone, citing [OpenHands types.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/types.py), [OpenHands stuck_detector.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py) and [Aider base_coder.py](https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py)):
  - the same call with the same error: **3** in a row gives a warning and a nudge, and **4** means stuck;
  - the same call with the same observation: **4** means stuck;
  - A/B alternation between two calls: **6** means stuck;
  - agent monologue, meaning consecutive agent messages with no tool call and no human input, as recorded in the session's lifecycle events (FR-005): **3** means stuck.

  A stuck count makes the scan that sees it stuck directly, without the two-scan debounce. The pattern already contains its own confirmation step: OpenHands nudges first and declares stuck one repeat later (inferred). A rerun that returns a different result is not a repeat.
- **FR-017**: **3** consecutive command timeouts MUST make the session stuck, and any successful command in between resets the count (Jev report table row "Consecutive command timeouts", citing [SWE-agent agents.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/agent/agents.py)). The scan that sees them is stuck without the two-scan debounce, as in FR-016 (inferred).
- **FR-018**: The rules MUST apply under these conditions (inferred; review correction 4):
  - The loop rules (FR-016) and the timeout rule (FR-017) re-apply only when new tool calls have completed since the last observed scan. A pattern already judged is never counted again.
  - Waiting on a person pauses the loop rules and the CI rule (FR-019), as well as the hung and spinning clocks.
  - An in-flight tool call pauses only the hung clock, not the spinning clock.
- **FR-019**: A PSE scan MUST be bad with reason "CI not converging" when **3** consecutive head commits of its branch completed CI with a non-cancelled failure (decision record; Jev report §Gitea reports cancelled runs as failures, which skews the CI rule). The report cites Gitea's [cancelled-to-failure mapping](https://github.com/go-gitea/gitea/blob/v28.2.0/services/actions/commit_status.go#L373), its [run conclusions](https://github.com/go-gitea/gitea/blob/v28.2.0/services/convert/convert.go#L445) and its [combine rule](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/commitstatus/commit_status.go#L67).
  - A success resets the count.
  - These count neither way: a cancelled run; still-running CI; a head with zero statuses, which Gitea reports as pending ([status.go](https://github.com/go-gitea/gitea/blob/v28.2.0/services/convert/status.go#L46)).
  - A commit whose set of failing checks is strictly smaller than the previous commit's is converging, and is skipped. The report flags this refinement as going beyond its sources.
  - WIP commits pushed during a stop grace window are excluded.
  - The CI rule follows the two-scan debounce (FR-023).
- **FR-020**: Jev MUST read CI evidence this way:
  - Read the head commit first, then query its status by commit id, so the verdict is pinned to the exact commit it judged (Jev report §One status call judges the head, if Jev checks the page size).
  - Compute a head's CI state over every reported check, using Gitea's own combination rule (spec 002 FR-036; Jev report, citing [status.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/status.go#L254)):
    - any error, failure or warning means failure;
    - any pending, or no status at all, means pending;
    - otherwise success, with skipped counted as success.
  - Choose the latest status per check by status id, never by the order the server returns (inferred; review correction 10).
  - Recognize a cancelled Gitea Actions job from its own status description ("Canceled after …"), so that failures reported by external CI still count (inferred; review correction 10).
- **FR-021**: Failing commands in a scan (**5** or more) MUST be a supporting signal only (decision record; Jev report §Loops need fingerprints of action and result, not action alone). They add the reason "failing commands (supporting)" to a scan that is already bad under another rule, and they never make a scan bad on their own (inferred reading of "supporting"). The report found no source that treats raw failure counts as a stall predictor; the detectors it surveyed count repetition ([OpenHands stuck_detector.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py)).
- **FR-022**: Jev MUST raise one dependency alert to the Lead, in place of a verdict per session, when every supervised PSE session's head reads zero-status pending in the same scan. This applies only when there are at least two such sessions (inferred). The source is the Jev report §Escalate when the Lead stays silent, not when Jev repeats itself, citing [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) inhibition.
  - For that scan, the CI rule and the spinning clock of those sessions are unobservable, so they neither advance nor reset an episode (inferred).
  - The dead, hung, loop and timeout rules still apply.
  - The alert is raised once per outage and resolved when any of those heads reports a status (inferred).

**Debounce and episodes**

- **FR-023**: One bad observed scan MUST give `health.warn` and an L0 nudge. Two consecutive bad observed scans MUST give `health.stuck` (decision record; Jev report §Two consecutive scans confirm, and the first one should nudge, citing [Kubernetes types.go](https://github.com/kubernetes/api/blob/master/core/v1/types.go) `failureThreshold`, [Prometheus alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) `for`, and the [SRE Workbook](https://sre.google/workbook/alerting-on-slos/)).
  - Only an observed scan with durable progress breaks the chain.
  - An ok scan without durable progress neither counts nor resets, because "Otherwise a chatty, looping session resets its own counter" (Jev report).
  - Dead (FR-013), loop (FR-016) and timeout (FR-017) verdicts are stuck on the scan that sees them.
- **FR-024**: "Since the last scan" MUST be measured from the last observed scan. An unknown scan MUST NOT do any of these (inferred; review correction 1):
  - use up the debounce lookback;
  - move a baseline: the last durable progress, the last loop judgement or the last CI comparison;
  - close or advance an episode.
- **FR-025**: A push whose head CI is red MUST NOT reset the debounce of the CI-not-converging rule, although a push is otherwise durable progress (inferred; review correction 3).
- **FR-026**: The bad scans of one session on one work item MUST form a stall episode (decision record; Jev report §Two consecutive scans confirm, and the first one should nudge, citing [Prometheus](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) `keep_firing_for`).
  - After the session recovers (FR-027), the episode stays open for **1** more observed scan.
  - A relapse inside that hold joins the same episode instead of starting a new escalation.
  - Episode ids MUST derive from the session and the scan slot in which the episode opened, so a retried scan reuses them (inferred; review correction 12).
- **FR-027**: Recovery MUST mean an ok observed scan with durable progress. Resolving an episode on Gitea means removing its `jev/*` label and marking its comment resolved. If that fails, it MUST be retried on later scans until it succeeds (inferred; review correction 5).

**Stop ladder**

- **FR-028**: Jev MUST request a stop only on a stuck verdict for a live session: hung, spinning, a loop or timeout rule, or CI not converging (FR-014 to FR-019, FR-023, FR-029). The person said "A session stops only when it is not making successful progress or is stuck." (project intake Q17). How long a session runs, what it costs and how many iterations it takes are never stop reasons on their own: Jev applies no wall-clock, cost or iteration cap (inferred from Q17; the Jev report's "Hard caps" row is not adopted). A session that keeps making durable progress, whose head CI is not failing under FR-019, and on which no hung, loop or timeout rule fires, is therefore never stopped, however long it runs.
- **FR-029**: On a stuck verdict for a live session, Jev MUST propose a stop through this ladder. The policy owner carries out every step that acts on the session. Sources: Q21 ("Checkpoint and stop, then escalate"), the decision record, and the Jev report §A stop is a request, a grace window, then a hard kill, which cites [Kubernetes pod termination](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination) (30 s), [systemd](https://github.com/systemd/systemd/blob/main/meson_options.txt) (90 s), [Claude Code hooks](https://code.claude.com/docs/en/hooks) (600 s) and [Temporal](https://docs.temporal.io/encyclopedia/detecting-activity-failures).
  1. **Request**: the living comment carries the stuck message with next action "request stop", from Jev's own bot account. The session honors it (spec 003 FR-038).
  2. **Grace**: **1 scan (10 minutes)**, configurable per role.
  3. **Checkpoint and lease release**, both done by the session (spec 005 FR-023; spec 001 cooperative release).
  4. **Hard stop**: if the grace window passes without both, the next action becomes "hard stop". It is addressed to the policy owner, the Lead, who revokes the lease with the stuck verdict as the reason (spec 001 FR-032; spec 003 FR-031).
  5. **Backstop**: lease expiry, and an epoch fence that rejects any write through the control plane or the gateway that presents an older lease epoch. A `git push` passes through neither (spec 001 FR-032; Jev report §Leases need an epoch fence, not just a TTL, citing [Kleppmann](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html) via [antirez](https://www.antirez.com/news/101), the [etcd Lease API](https://etcd.io/docs/v3.6/learning/api/#lease-api) and [Kubernetes Leases](https://kubernetes.io/docs/concepts/architecture/leases/)). [NEEDS CLARIFICATION: where the epoch fence lives. Should it stay only in the coordination layer, where spec 001 FR-032 already rejects older epochs on every write and lease check it handles? Or should it also be a required lease-epoch commit status in branch protection, so that commits from a stale epoch can never merge? The Jev report found no conditional writes in Gitea, and branch protection is set by a person (Art. VI).]

  The stop never waits for the person's or Smokey's approval. Escalation follows it (FR-032) (Q21; reading in Assumptions).
- **FR-030**: Jev MUST recognize a session as stopped in either of these cases, whatever the current signals say (inferred; review correction 2):
  - the session obeyed a stop request: it wrote a checkpoint at or after the request and released its lease;
  - the Lead revoked its lease after the request.

  Jev records `session.stop` with next action "notify Lead". The session MUST never be reported as recovered, and never flagged hung again.
- **FR-031**: When the stuck session is the Lead's own, Jev MUST escalate straight to the person (L2), who carries out any hard stop. The Lead never decides an escalation about itself (spec 003 FR-031; Art. II) (inferred).
- **FR-052**: An episode whose session was stopped (FR-030) or found dead (FR-013) MUST be resolved once the work item's recovery outcome (resume, reassign or block) is recorded (spec 001 FR-017; FR-005) (inferred). Resolving it means:
  - removing its `jev/*` label, except that `jev/parked` stays until a person resets the breaker (FR-033);
  - marking its comment resolved as stopped, with the recorded outcome;
  - moving its recovery point to resolved (FR-039).

  A write Gitea refuses is retried on later scans until it succeeds, as in FR-027. Until the outcome is recorded, the episode stays open and FR-032's L2 rule applies. A stopped episode is never resolved as recovered (FR-030).

**Escalation**

- **FR-032**: Jev MUST escalate on three levels (decision record; Jev report §Escalate when the Lead stays silent, not when Jev repeats itself, citing [PagerDuty](https://response.pagerduty.com/oncall/being_oncall/) and [Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)):
  - **L0, the session**: an in-band nudge on the first bad scan. It is advisory (spec 003 FR-038).
  - **L1, the Lead**: on the stuck verdict. The Lead acknowledges within **1 scan** and records one decision: re-plan, reassign or hard stop (spec 003 FR-031).
  - **L2, the person**, in any of these cases:
    - the Lead has not acknowledged within 1 scan of the first stuck verdict;
    - the episode is still unresolved (FR-027, FR-052) **3 scans** after its first stuck verdict;
    - the circuit breaker opens (FR-033);
    - at once, when the stuck session is the Lead's own (FR-031).

  The report calls the 1-scan and 3-scan values local policy. An acknowledgement is the Lead's recorded decision on the escalation (spec 003 FR-031), read from a Lead decision trace that names the episode id (FR-005) (inferred).
- **FR-033**: After **2** automatic restarts of the same work item, the next stuck verdict MUST park it (decision record; Jev report §Escalate when the Lead stays silent, not when Jev repeats itself, citing [Azure: Circuit Breaker](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker) and its "manual reset option"; the report calls the count of 2 local policy). Spec 001 has no automatic restart of its own: a re-dispatch (spec 001 FR-037) follows a recorded recovery outcome (spec 001 FR-017). An automatic restart is therefore a re-dispatch of the work item on a resume or reassign outcome that the Lead recorded, not one a person recorded. Jev counts them from the control plane's records of re-dispatch (FR-005) (inferred). Parking means:
  - Jev adds `jev/parked`;
  - Jev pages the person (L2);
  - Jev records that no automatic restart may follow.

  Only a person resets the breaker. Jev never restarts a session itself.
- **FR-034**: Jev MUST never post a second comment for an episode. While an episode stays at L2 and is still open, that is, not yet resolved under FR-027 or FR-052, Jev MAY re-notify the person no more often than every **4 hours**, by editing the living comment (Jev report table row "Repeat notification", citing [Alertmanager configuration](https://prometheus.io/docs/alerting/latest/configuration/) `repeat_interval`).

**The record on Gitea**

- **FR-035**: Jev MUST publish messages this way (decision record):
  - `health.warn`, `health.stuck` and `session.stop` are posted on the work item as a fenced JSON block of the message, inside the episode's living comment, with the explanation (FR-004);
  - `health.ok` and `health.unknown` are recorded only in scan history;
  - a session without a work item has no comment. Its warn, stuck and stop notices reach the Lead and the person the same way as the dependency alert (FR-022) (inferred).
- **FR-036**: Jev MUST use exactly three exclusive, scoped labels, created once by a person: `jev/warning`, `jev/stuck` and `jev/parked` (decision record; Jev report §Labels accept IDs or names, never both, and removal takes only IDs). The report cites Gitea's [issue_label.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/issue_label.go#L318), [label.go](https://github.com/go-gitea/gitea/blob/v28.2.0/models/issues/label.go#L374) and the [exclusive-scope rule](https://github.com/go-gitea/gitea/blob/v28.2.0/models/issues/issue_label.go#L64). Jev MUST:
  - look up each label in both the repository's and the organisation's labels, and apply it by its ID (inferred; review correction 10);
  - add labels and never replace the work item's label set, so labels set by people or other agents stay;
  - confirm that the returned set holds the expected ID;
  - never create a label. When a label is missing, Jev reports it and still writes the comment (FR-037).

  Because the scope is exclusive, an issue never shows two Jev states at once.
- **FR-037**: Jev MUST keep one living comment per episode per work item (owner/repo#issue), and edit it in place as the episode moves. The comment carries a marker derived from the episode (decision record; Jev report §Comments never paginate, so upsert by marker, citing [issue_comment.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/issue_comment.go#L28); inferred; review correction 11).
  - Jev finds the comment by the id it stored. If that fails, it looks in the issue's full comment list for a comment from its own account that carries the marker.
  - Jev never edits a comment written by another account, even one that carries the marker (spec 002 FR-035).
  - A deleted comment is recreated on the next scan that updates the episode.
  - The label write is independent of the comment write: either may succeed while the other is retried.
- **FR-038**: Every list read that Gitea pages MUST continue until the total count Gitea reports (`X-Total-Count`) is reached. A short page never counts as the end, because servers may clamp page size (inferred; review correction 10). Gitea reports the total separately from the page and silently clamps page sizes above 50 (Jev report §One status call judges the head, if Jev checks the page size and §Least privilege needs an org team, not a collaborator grant, citing [status.go](https://github.com/go-gitea/gitea/blob/v28.2.0/routers/api/v1/repo/status.go#L254) and [utils.go](https://github.com/go-gitea/gitea/blob/v28.2.0/services/convert/utils.go#L15)). Jev MUST throttle its own reads, because Gitea 28.2 has no built-in REST rate limiter (Jev report).
- **FR-039**: Every message MUST carry an idempotency key derived from the session, the episode and the escalation level, so that a fresh process regenerates the same key (Jev report §Deterministic episode keys make every comment idempotent, citing [Brandur Leach](https://brandur.org/idempotency-keys) and [Stripe](https://docs.stripe.com/api/idempotent_requests)).
  - Before posting, Jev MUST record an intent holding the key and its recovery point.
  - An episode moves through these recovery points: detected → nudged → escalated_L1 → stop_requested → checkpoint_seen → stopped → escalated_L2 → resolved. A Jev that crashes midway resumes from its recovery point without paging again.
  - Dedup records MUST be kept for at least **72 hours** (Brandur's figure; the report finds Stripe's 24 hours too short; spec 009 FR-029).

**Least privilege**

- **FR-040**: Jev MUST act through its own Gitea Bot-type account, placed in an organisation team, never through a collaborator grant. The team gives code read, issues write, pull requests write and actions read (Jev report §Least privilege needs an org team, not a collaborator grant, citing Gitea's [Bot user type](https://github.com/go-gitea/gitea/blob/v28.2.0/models/user/user.go#L977) and [team units](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/org_team.go)). Its token MUST carry exactly `read:repository`, `write:issue` and `read:user`, plus `read:organization` when organisation labels are used (Jev report, citing [access_token_scope.go](https://github.com/go-gitea/gitea/blob/v28.2.0/models/auth/access_token_scope.go#L56); `read:user` inferred; review correction 9).
- **FR-041**: At the start of every scan run, Jev MUST check its own rights and refuse to run in any of these cases (Jev report §Least privilege needs an org team, not a collaborator grant, citing [repo_branch.go](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/structs/repo_branch.go#L24); inferred; review correction 9):
  - the account has repository push or admin permission;
  - Gitea reports that the account can push or merge the default branch;
  - the rights cannot be read;
  - Gitea does not report a 28.x version (inferred from the Jev report §Conclusion: check the version "before it trusts any verdict").

  A refusal is recorded locally, naming the right to remove, and nothing is written to Gitea (inferred). This check is in addition to the gateway's own (spec 002 FR-027).

**Message contract and records**

- **FR-042**: Every message Jev publishes MUST be a Jev message in the shared schema that spec 009 owns, exported as `schemas/jev-message.v1.json` (decision record; spec 009 FR-002; data-model intake Q10).
  - It carries the schema version, kind, scan id, session id, work item (issue), reasons, next action and idempotency key (decision record). It also carries the episode id and short evidence facts (inferred; the existing schema has both).
  - The type is strict and closed. Unknown fields and wrong types are refused, nothing is coerced, and a built message cannot be changed (decision record).
  - Python and OCaml read and write the same type from the exported schema, with no hand-written mapping (spec 009 FR-003; project intake Q10).
  - Jev defines no second copy (spec 009 FR-002).
- **FR-043**: The kind MUST be exactly one of five (decision record):
  - `health.ok`: the session was observed and no rule fired;
  - `health.unknown`: the session could not be observed (FR-011);
  - `health.warn`: the first bad observed scan; next action "nudge session";
  - `health.stuck`: a stuck verdict, dead included. Next action "request stop", "hard stop", "notify Lead", "page person" or "park";
  - `session.stop`: the session has stopped under the ladder (FR-030); next action "notify Lead".

  The reasons are: dead, hung, spinning, repeated action and error, repeated action and observation, alternation, monologue, command timeouts, CI not converging, failing commands (supporting) and unobservable. The next actions are: none, nudge session, request stop, hard stop, notify Lead, page person and park. The reason and next-action names are inferred; the schema fixes their spelling.
- **FR-044**: CI MUST fail when the exported schema file differs from the type Jev publishes. A change to the type MUST raise the schema version (spec 009 FR-004; decision record; the version rule is inferred).
- **FR-045**: Jev MUST record every scan in SQLite (project intake Q9), under spec 009's scan-record schema, keyed by (session_id, scan_id) (decision record).
  - There is one record per session per scan. A retried scan writes the same key and never adds a second record (inferred; review correction 12).
  - A record holds the time, whether the scan observed the session (with the reason if not), the kind, reasons, next action, episode, whether durable progress was seen, the branch head seen (FR-009) and the evidence facts (inferred).
  - Jev owns its scans, and everyone in the tenant reads them (data-model intake Q9).
  - Scan history is never deleted because of its age (inferred from project intake Q16 and spec 009 FR-029).

**Operation**

- **FR-046**: Jev MUST scan every live session every **10 minutes**, scheduled by the LangGraph service's scheduler or by a system scheduler on the host (project intake Q2; decision record, which allows either, as Assumptions repeats; Jev report §Two clocks and a fingerprint beat five flat rules: "Jev scans every 10 minutes"). The scan runs MUST also meet these rules (inferred; review correction 12):
  - The scan id is the start of the 10-minute slot in UTC, so a retried scan reuses it.
  - Only one scan run may run at a time (a run lock).
  - An error in one session's scan MUST be reported for that session, and MUST NOT abort the others.
  - All times are UTC. A time without a zone is read as UTC.
- **FR-047**: Jev MUST supervise every live session at the peak of "3 agent sessions + 6 subagents + the Jev agent." (project intake Q20), on the single host (project intake Q22), and counts itself in the capacity registry (spec 001 FR-021).
  - A subagent holds no lease of its own (spec 001 FR-034). Its work counts as its parent session's activity, and a hung subagent shows up as the parent's call that has overrun its own timeout (inferred).
  - The cap "At most 2 subagents per container, per role and per Gitea bot account." (project intake Q18) is enforced by spec 001, not by Jev.
- **FR-048**: Jev's thresholds MUST live in a versioned policy in the repository, settable per role. Changing them changes when a session is stopped. An agent MAY propose a change based on scan history, but only a person approves it (inferred; Art. VI, Art. VIII). The defaults below all come from the [Jev report](../../docs/research/reports/Jev%20watchdog%20for%20coding%20agents.md) ("Recommended thresholds and sources" and the sections named), with the upstream sources it cites:

  | Threshold | Default | Jev report section | Upstream sources the report cites |
  |---|---|---|---|
  | Scan interval | 10 min | §Two clocks and a fingerprint beat five flat rules | local policy (decision record) |
  | Agent-loop silence (hung) | 20 min | §Silence catches hangs, but only durable artifacts prove progress | [CircleCI](https://circleci.com/docs/reference/configuration-reference/) 10 min; [Airflow](https://github.com/apache/airflow/blob/main/airflow-core/src/airflow/config_templates/config.yml) 300 s; [Kubernetes](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#progress-deadline-seconds) 600 s; [Temporal](https://docs.temporal.io/encyclopedia/detecting-activity-failures) 0.8× margin; [GitLab](https://docs.gitlab.com/ci/pipelines/settings/#set-a-limit-for-how-long-jobs-can-run) keep-alive |
  | Start-up grace | first agent-loop event or 2 scans | table row "Startup grace" (local policy) | [Kubernetes startup probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-startup-probes) |
  | In-flight tool call | hung clock paused inside the call's own timeout | §Silence catches hangs, but only durable artifacts prove progress | [SWE-agent tools.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/tools/tools.py) |
  | Durable progress (spinning) | 60 min, open (FR-015) | §Silence catches hangs, but only durable artifacts prove progress | [Anthropic: Measuring agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy); [GitLab](https://docs.gitlab.com/ci/pipelines/settings/#set-a-limit-for-how-long-jobs-can-run) 1 h; [Anthropic harness](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents) |
  | Loop window | last 20 events since the last human input | §Loops need fingerprints of action and result, not action alone | [OpenHands stuck_detector.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py) |
  | Same action, same error | 3 = warning and nudge; 4 = stuck | same | [OpenHands types.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/types.py); [stuck_detector.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py); [Aider](https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py) 3 reflections |
  | Same action, same observation | 4 = stuck | same | [OpenHands types.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/types.py) |
  | A/B alternation | 6 = stuck | same | [OpenHands stuck_detector.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py) |
  | Agent monologue | 3 = stuck | same | [OpenHands types.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/types.py) |
  | Consecutive command timeouts | 3 = stuck | table row "Consecutive command timeouts" | [SWE-agent agents.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/agent/agents.py) |
  | CI not converging | 3 consecutive head commits | §Gitea reports cancelled runs as failures, which skews the CI rule | Gitea [commit_status.go](https://github.com/go-gitea/gitea/blob/v28.2.0/services/actions/commit_status.go#L373); [convert.go](https://github.com/go-gitea/gitea/blob/v28.2.0/services/convert/convert.go#L445); [combine rule](https://github.com/go-gitea/gitea/blob/v28.2.0/modules/commitstatus/commit_status.go#L67); [status.go](https://github.com/go-gitea/gitea/blob/v28.2.0/services/convert/status.go#L46) |
  | Failing commands per scan | 5 or more, supporting only | §Loops need fingerprints of action and result, not action alone | no source supports failure counts; detectors count repetition ([OpenHands](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py)) |
  | Debounce | 1 bad = warning; 2 consecutive = stuck | §Two consecutive scans confirm, and the first one should nudge | [Kubernetes types.go](https://github.com/kubernetes/api/blob/master/core/v1/types.go); [Prometheus `for`](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/); [SRE Workbook](https://sre.google/workbook/alerting-on-slos/) |
  | Recovery hold | 1 scan | same | [Prometheus `keep_firing_for`](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) |
  | Stop grace window | 1 scan (10 min), per role | §A stop is a request, a grace window, then a hard kill | [Kubernetes](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination) 30 s; [systemd](https://github.com/systemd/systemd/blob/main/meson_options.txt) 90 s; [Claude Code hooks](https://code.claude.com/docs/en/hooks) 600 s |
  | L1 acknowledgement | 1 scan | §Escalate when the Lead stays silent, not when Jev repeats itself (local policy) | [PagerDuty](https://response.pagerduty.com/oncall/being_oncall/) 5 min |
  | L2 page | unresolved after 3 scans | same (local policy) | [PagerDuty](https://response.pagerduty.com/oncall/being_oncall/) |
  | Repeat notification | at most every 4 h, by editing | table row "Repeat notification" | [Alertmanager `repeat_interval`](https://prometheus.io/docs/alerting/latest/configuration/) |
  | Dedup retention | at least 72 h | §Deterministic episode keys make every comment idempotent | [Brandur](https://brandur.org/idempotency-keys) 72 h; [Stripe](https://docs.stripe.com/api/idempotent_requests) 24 h (secondary) |
  | Circuit breaker | 2 automatic restarts per work item; manual reset | §Escalate when the Lead stays silent, not when Jev repeats itself (count is local policy) | [Azure: Circuit Breaker](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker) |

- **FR-049**: Jev MUST compute these metrics for the scorecard (spec 007 FR-022), per role and per session, over a window. They refine spec 007's working definitions, which defer to this spec (inferred):
  - **stuck rate**: the share of supervised sessions with at least one episode that reached `health.stuck` for a reason other than dead. Dead sessions are counted separately;
  - **false-stuck rate**: the share of stuck episodes that the Lead or the person records as wrong, because the session was making progress. A stuck verdict counts once per episode, however many stuck scans the episode holds;
  - **recovery success**: the share of stuck episodes that end with durable progress resumed, without the work item being parked. Durable progress resumes either as an ok scan with durable progress in the same session, or as one in the next session on the same work item.
- **FR-050**: Every verdict recorded as wrong, and every stall Jev missed but the Lead or the person found later, MUST become a replay fixture for the decision function before the thresholds change (Art. VIII) (inferred).
- **FR-051**: Each warn, stuck, stop and escalation step MUST be recorded as a decision trace in spec 009's schema, linked from its scan record (Art. IX; project intake Q3). The trace holds the decision, the evidence facts, the thresholds version as its assumption, the changed state (labels and comment) and the next action. Jev stores no hidden model reasoning (Art. IX).

### Key Entities

- **Supervised session**: one incarnation of a Lead, PSE or Review session, as the control plane describes it. It has a session id, role, work item, a PSE's branch, its start time, its lease (heartbeat, TTL, released, epoch), and the recovery outcome recorded for its work item. Whether it waits on a person and the Lead's acknowledgements are inputs no upstream spec records yet (FR-005). A restart creates a new incarnation (FR-007).
- **Evidence snapshot**: everything one scan observed about one session. It is the decision function's only input besides history and thresholds (FR-003, FR-005).
- **Scan run and scan slot**: one pass over all live sessions. Its id is the start of its 10-minute slot in UTC, and only one run is active at a time (FR-046).
- **Scan record**: one row per (session_id, scan_id). It holds whether the scan observed the session, the kind, reasons, next action, episode, whether durable progress was seen, the branch head seen and the evidence facts (FR-045).
- **Stall episode**: the run of bad scans of one session on one work item. Its id derives from the session and its opening slot, and it moves through recovery points from detected to resolved. It is resolved by recovery, or, for a stopped or dead session, once the work item's recovery outcome is recorded (FR-026, FR-027, FR-039, FR-052).
- **Jev message**: the published verdict, in the shared schema owned by spec 009 (FR-042, FR-043).
- **Living comment**: the one comment per episode per work item that Jev edits in place. It carries the episode marker, the fenced JSON message and the explanation (FR-037).
- **Jev label**: one of `jev/warning`, `jev/stuck` and `jev/parked`. They are exclusive, scoped, created by a person and applied by ID (FR-036).
- **Intent (dedup) record**: an idempotency key with its recovery point and comment id, kept at least 72 hours (FR-039).
- **Thresholds policy**: the versioned, per-role values of FR-048. A person approves changes.
- **Work-item breaker**: the automatic-restart count per work item, counted from re-dispatches on a Lead-recorded outcome (spec 001 FR-037), and its parked flag. Only a person resets it (FR-033).
- **Dependency alert**: one alert per shared outage, in place of per-session verdicts (FR-022).
- **Command-log entry**: one tool call's start or end, with fingerprints, exit code, time, timeout and timed-out flag (FR-010).

### Non-goals

- Edit code, repair the stuck session's work, or judge the quality of its code. Review owns verdicts, and may cite Jev (spec 006 FR-026).
- Carry out a hard stop, revoke or release leases, restart sessions, or decide re-plan or reassign. Specs 001 and 003 own these.
- Detect loops inside the session at every iteration. That is the session runtime's job (Assumptions); Jev is the backstop that keeps the record.
- Approve autonomy promotions. That is Smokey's role (spec 007).
- Create label definitions, set up Jev's own account or team, or write branch protection. A person does these.
- Apply wall-clock, cost or iteration caps (project intake Q17).
- Define the message, scan-record, dedup, trace, checkpoint or command-log schemas. Spec 009 owns them.
- Read visible reasoning chains (spec 005 FR-017).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Jev is replayed on a labelled suite of at least 100 session histories, covering hung, spinning, looping, timing-out, CI-not-converging and healthy long-work sessions. It flags 100% of the stuck histories. Every hung history gets its warning 20 to 30 minutes after the last agent-loop event, and its stuck verdict 30 to 40 minutes after it (the Jev report's latency window).
- **SC-002**: On the same suite, 0 healthy histories get a stuck verdict. These include:
  - tool calls inside their own timeout;
  - sessions waiting on a person for up to 24 hours;
  - start-up;
  - flaky reruns with differing results;
  - cancelled CI runs;
  - heads with no CI status;
  - sessions that obeyed a stop request.
- **SC-003**: Over the first 4 weeks of live operation, at most 1 in 20 stuck episodes (5%) is later recorded as wrong by the Lead or the person. This is a proposed default the owner has not confirmed, and it feeds spec 007's false-stuck rate.
- **SC-004**: 100% of stop requests are settled within 2 scans (20 minutes): the session is recognized as stopped, or the hard stop has been handed to the policy owner. In a fault-injection run of at least 20 late pushes, 0 writes that present a stopped session's old lease epoch land.
- **SC-005**: 100% of stall episodes of sessions that have a work item have exactly 1 Jev comment on that work item. This holds in a fault-injection suite of at least 20 crashes and retries spread over every recovery point, with 0 duplicate pages to the person.
- **SC-006**: In 100% of scans that could not observe a session, labels, comments, debounce counts, baselines and episodes are unchanged.
- **SC-007**: In 100% of start-up trials where Jev's account has push, admin or merge rights, or its rights cannot be read, Jev performs 0 scans and 0 writes. Over the first 4 weeks, the audit trail shows 0 Jev writes other than its own comments and labels.
- **SC-008**: Over the first 4 weeks, 100% of Jev's published messages validate against the shared schema. The schema check blocks 100% of changes that would make the published type and the exported schema differ.
- **SC-009**: In a 24-hour soak at the peak of 3 agent sessions, 6 subagents and Jev on the single host, every scan of all live sessions finishes inside its 10-minute slot, and 0 slots run two scans at once.
- **SC-010**: In 100% of stuck episodes that the Lead has not acknowledged within 1 scan, the person is paged by the next scan. 0 people are paged for an episode the Lead acknowledged and resolved within 3 scans, except for the Lead's own session and parked work items. An episode is resolved when its session recovers (FR-027) or, for a stopped or dead session, when the work item's recovery outcome is recorded (FR-052).
- **SC-011**: 0 automatic restarts follow a parked work item until a person resets it.
- **SC-012**: From the first full scorecard window after Jev starts, the stuck rate, false-stuck rate and recovery success are available for 100% of windows, per role and per session.
- **SC-013**: In fault injection where one session's evidence cannot be read, or makes its scan fail, 100% of the other sessions' scans still complete and are recorded.
- **SC-014**: When every PSE head reads zero-status pending, exactly 1 dependency alert is raised per outage, and 0 per-session stuck verdicts rest on CI or spinning reasons while the outage lasts.

## Assumptions

- **Where the numbers come from**: every threshold comes from the Jev report and the project's decision record for spec 008, not from the person's words. The report itself calls several of them local policy: the 60-minute window, the start-up grace, the L1 and L2 timings, and the circuit-breaker count. SC-003's 5% and the suite sizes in SC-001, SC-004 and SC-005 are proposed defaults (inferred). The two open markers (FR-015, FR-029) are the person's to settle.
- **Reading of Q21**: the person chose "Checkpoint and stop, then escalate" over "Ask the user or Smokey before stopping". This spec reads that as: the stop never waits for the person's or Smokey's approval. The L1 notice to the Lead at the stuck verdict tells the policy owner to carry out the stop if the session does not, and the escalation to a person (L2) follows (inferred).
- **Forge**: Gitea 28.x (project intake Q1). The Jev report read Gitea's API from the v28.2.0 source, because docs.gitea.com was unreachable during the research. The forms this spec relies on are:
  - `GET /repos/{owner}/{repo}/commits/{sha}/status?limit=50` for a head, and `/statuses` with paging by the `X-Total-Count` header;
  - labels added with `POST` (never `PUT`, which replaces the set) and removed with `DELETE …/labels/{id}`, which takes an integer ID only;
  - unpaginated `GET …/issues/{index}/comments`, with only `since` and `before` filters;
  - `user_can_push` and `user_can_merge` from `GET /branches/{default}`, and the repository's `permissions` (push, admin), because on a protected branch the first two come from the protection rule;
  - `/api/v1/version` and `/swagger.v1.json` for the version check.
- **Runtime and schedule**: the LangGraph service's scheduler runs a scan every 10 minutes, or cron `*/10 * * * *` does (decision record). Everything runs on the MacBook Pro M4 Pro, with 24 GB RAM and about 18 GB usable after macOS (project intake Q22; data-model intake Q14, revised). Jev shares it with Gitea, SQLite, local Ollama and the sessions it watches.
- **Existing artifacts**: this spec adopts them as starting points, and the review corrections (FR-007, FR-008, FR-009, FR-018, FR-020, FR-024 to FR-027, FR-030, FR-036 to FR-038, FR-040, FR-041, FR-045, FR-046) are requirements on them:
  - the Python implementation in `packages/sdd-harness/src/sdd_harness/jev/`, run as `sdd-jev scan`;
  - the pure decision function `decide(evidence, history, thresholds)`;
  - the message type, a strict, frozen Pydantic model (`extra="forbid"`);
  - the exported `schemas/jev-message.v1.json`, which OCaml derives with `ppx_deriving_yojson`;
  - the currency check `sdd-jev schema --check`.
- **Language split**: the reading of project intake Q10 puts the policy and decision core in OCaml (inferred). Whether `decide()` moves to OCaml is a planning choice; the shared schema keeps both sides aligned meanwhile.
- **Schema reconciliation**: the existing schema carries `episode_id` and `evidence` beyond the field list in spec 009 FR-002. Planning reconciles them, as spec 009's checklist notes.
- **Command log**: the hook `.claude/hooks/command_log.py` writes `.specify/sessions/commands/<session_id>.jsonl`, which is gitignored and has mode 0600.
  - It is registered as a PostToolUse hook, as the decision record says. It is also registered for PreToolUse (call starts, with the call's own timeout) and PostToolUseFailure (failed calls).
  - It stores calls and results as short hashes, and always exits 0.
  - Decision traces live at `.specify/traces/<run>/trace.jsonl`.
  - A call that names no timeout gets the coding harness's default shell timeout of 2 minutes (inferred from the existing default).
- **Gateway path**: the existing implementation reads Gitea directly with Jev's token. FR-002 requires Jev's reads, like its writes, to go through the gateway (Art. III; spec 002 FR-016, which keeps every bot account's credential in the gateway, and FR-027, which limits Jev to read tools), so planning moves the reads. As read on 2026-10-22, spec 002 FR-001's read tools do not cover every read Jev needs: a branch's head and its commits, Jev's own repository permissions and whether it can push or merge the default branch (FR-041), and the Gitea version. Label lookup and comment upsert are already the gateway's (spec 002 FR-034, FR-035). Adding a read tool is a Critical-risk change that a person approves (spec 002 FR-003) (inferred).
- **Human-owned setup**: a person creates the three `jev/*` labels with `"exclusive": true`. A person also creates the Bot-type account and its organisation team (`repo.code: read`, `repo.issues: write`, `repo.pulls: write`, `repo.actions: read`) and sets the token scopes (Jev report; spec 002 Assumptions).
- **Nudge and stop delivery**: the nudge and the stop request reach the session as Jev's living comment from its own account (spec 003 FR-038). Delivering them in-band between tool calls is a planning choice. One option is a Claude Code hook that ends the loop with `{"continue": false, "stopReason": …}` (Jev report, citing [Claude Code hooks](https://code.claude.com/docs/en/hooks)).
- **In-session loop detection**: the Jev report puts the first line of loop defence inside the session. Examples are OpenHands' stuck detection and a Claude Code hook that halts at the third identical failure. That belongs to the session runtime (specs 003 and 005), not to this spec. Jev confirms the loop and keeps the record.
- **Paging**: an L2 page is a mention of the person's Gitea account in the living comment (inferred). First-year scale is "10 Agents and 1 User" (data-model intake Q8, revised), the same set as "3 agent sessions + 6 subagents + the Jev agent." (Q20). The one user receives every L2 page. Smokey is not part of Jev's escalations (inferred from project intake Q12 and Q13, which make Smokey the sole top-mode approver and a person's account).
- **Clean-up after a stop**: compensating steps after a hard stop belong to the Lead's recovery, not to Jev (spec 001 FR-017; Jev report §Leases need an epoch fence, not just a TTL, citing [Azure: Compensating Transaction](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction)). Examples are removing the in-progress label, marking the PR as draft and posting a summary.
- **Models**: explanations may come from Claude or from Ollama, cloud or local ("Ollama (cloud and local) alongside Claude Code models.", project intake Q7; constitution v1.1.0 per Q14). Health, policy and authority decisions stay in plain code (Art. III).

## Dependencies

- **Upstream**:
  - **001-engineering-control-plane**: 008 consumes the session and lease records (heartbeat, TTL, release and epoch), events, board state and the capacity registry. It also consumes cooperative lease release, Lead's hard-stop revocation with the epoch fence (001 FR-032) and the recovery assessment its stuck verdicts lead to (001 FR-017).
  - **002-gitea-mcp-gateway**: 008 consumes Jev's bot account and its tools: combined commit checks (002 FR-036), comment upsert by marker (002 FR-035), `jev/` labels added by ID (002 FR-034) and the startup check that Jev can neither push nor merge (002 FR-027).
  - **003-role-agent-contracts**: 008 consumes the contract format for Jev's own operating contract (003 FR-001, FR-028), every role's stuck, checkpoint and stop duties (003 FR-036, FR-038), and Lead's duty to decide Jev's escalations and carry out hard stops (003 FR-031).
  - **005-context-continuity**: 008 consumes decision traces and checkpoints as agent-loop activity and durable-progress signals (005 FR-029), lifecycle events as agent-loop activity (005 FR-021, FR-029), the command log written after each tool use (005 FR-027), and the checkpoint-on-stop behavior its stop ladder waits for (005 FR-023).
  - **009-metadata-data-model**: 008 consumes the Jev message schema (`schemas/jev-message.v1.json`), Jev scan records keyed by session and scan, dedup records kept at least 72 hours, Jev's identity and bot account, and the schemas for decision traces, checkpoints, lifecycle events and command-log entries, which it reads as evidence.
- **Downstream**:
  - **007-progressive-autonomy**: 007 consumes Jev's stuck rate, false-stuck rate and recovery success (FR-049), with the episodes and escalations they are computed from, as scorecard inputs (007 FR-022) and for human recovery cost (007 FR-013).
- **Build order**: 009 → 001 → 002, 005 → 003, 004 → 006, 008 → 007. 008 is built after 003, in parallel with 006, and before 007.
- **Constitution** (v1.1.0):
  - Art. I: Jev re-reads its evidence at every scan, and a stuck session checkpoints before it stops (FR-005, FR-029).
  - Art. II: Jev never edits, approves or stops anything itself, and the Lead never decides an escalation about its own session (FR-002, FR-031).
  - Art. III: plain code decides and models only explain. Text is data, Jev's tool surface is narrow, and messages carry deterministic idempotency keys (FR-003, FR-004, FR-006, FR-039).
  - Art. IV: an unknown scan is never ok or bad; cancelled runs are not failures, and missing CI is not a pass (FR-011, FR-019, FR-024).
  - Art. V: the thresholds are specified before build, and the open choices are marked (FR-015, FR-029, FR-048).
  - Art. VI: threshold, permission and label changes need a person, and Jev refuses to run with excess rights (FR-040, FR-041, FR-048).
  - Art. VII: verdicts rest on authoritative evidence scoped to the current incarnation, never on retrieved text (FR-005, FR-007).
  - Art. VIII: wrong and missed verdicts become replay fixtures, and thresholds are calibrated from scan history (FR-048, FR-050).
  - Art. IX: verdicts are recorded as decision traces, and no hidden reasoning is stored (FR-004, FR-051).

## Clarifications

### Session 2026-10-22

- Q: The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target? → A: Gitea only (project intake Q1)
- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service (project intake Q2)
- Q: The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work? → A: Both (project intake Q3)
- Q: Which models and embeddings should the RAG and reasoning chains use? → A: "Ollama (cloud and local) alongside Claude Code models." (project intake Q7)
- Q: Your stack lists 'a vector DB' and 'knowledge graphs' with SQLite, but no product. Which stores should the specs and code use? → A: "SQLite with sqlite-vec and custom Python Vector Databases. I want to create the Meta Data Schema and Structure. Create a new Data Modell that can scale for all current and future users when using this applications." (project intake Q9)
- Q: Which parts are OCaml and which stay Python? → A: "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." (project intake Q10)
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
- Q: Who may change a metadata record once it exists? → A: Its owning role only (data-model intake Q9)
- Q: How should the schema change over time without breaking existing data? → A: Versioned migrations (data-model intake Q10)
- Q: How many people and agents should the data model support in its first year? → A: "10 Agents and 1 User" (data-model intake Q8, revised; supersedes: A. Up to 100 users — round 5)
- Q: Which technical limits must the data model respect? → A: "Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption." (data-model intake Q14, revised; supersedes: A. Works offline; B. Sensitive text stays local; C. Encrypted at rest — round 5)
- Q: Your MacBook answer replaced the earlier limits. Which of these should still apply alongside the M4 Pro with about 18 GB usable RAM? → A: Works offline; Sensitive text stays local; FileVault encryption; Database file encryption (data-model intake Q25, follow-up after round 5)
