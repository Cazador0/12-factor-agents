# Safe stop and escalation patterns for stuck autonomous agents and automated workers

Research date: 2026-10-22. Method note: the research environment's egress proxy blocked most documentation hosts
(kubernetes.io, freedesktop.org, docs.stripe.com, docs.langchain.com, docs.temporal.io, sre.google, pagerduty.com,
learn.microsoft.com, cdn.openai.com, martin.kleppmann.com). Where a project publishes its docs from a Git repository,
the text was read from the current `main`/`master` source file on raw.githubusercontent.com on 2026-10-22, and the
rendered-page URL is cited with the source file alongside it. anthropic.com and code.claude.com were reachable directly.
Facts that come only from a search-engine extract or a secondary write-up are marked **[secondary]**.

## 1. Graceful termination: SIGTERM, grace period, SIGKILL; checkpoint-before-stop; saga/compensation; releasing locks and leases (TTL, fencing)

### Takeaway
Every mature runtime uses the same two-phase stop: a polite, catchable stop request, a bounded grace period for the worker
to save state and release what it holds, and then an uncatchable kill. The kill phase is the reason a stopped worker's
lock must not be trusted: a lease TTL bounds how long a dead or paused holder blocks others, and a fencing token checked
by the protected resource keeps a "zombie" that wakes up after its lease expired from writing. Work that already left
the system, such as a posted comment or a pushed branch, is undone by idempotent, resumable compensating steps, not by a
rollback.

### Cited Findings

**Kubernetes pod termination (the reference two-phase stop)**
- Design intent: Pods should "gracefully terminate when they are no longer needed (rather than being abruptly stopped
  with a `KILL` signal and having no chance to clean up)"; "be able to request deletion and know when processes
  terminate, but also be able to ensure that deletes eventually complete." — [Kubernetes: Pod Lifecycle, Termination of Pods](https://kubernetes.io/docs/concepts/workloads/pods/pod-lifecycle/#pod-termination) (source: [kubernetes/website pod-lifecycle.md](https://github.com/kubernetes/website/blob/main/content/en/docs/concepts/workloads/pods/pod-lifecycle.md))
- The kubelet first sends "a TERM (aka. SIGTERM) signal, with a grace period timeout, to the main process in each
  container"; many runtimes honour the image's `STOPSIGNAL` instead. "Once the grace period has expired, the KILL signal
  is sent to any remaining processes." If the kubelet or runtime restarts mid-wait, "the cluster retries from the start
  including the full original grace period." — same page.
- "The default `terminationGracePeriodSeconds` setting is 30 seconds." A `preStop` hook runs first, inside the same
  budget. If it is "still running after the grace period expires, the kubelet requests a small, one-off grace period
  extension of 2 seconds". "If the `preStop` hook needs longer to complete than the default grace period allows, you must
  modify `terminationGracePeriodSeconds` to suit this." — same page, Pod Termination Flow.
- While it shuts down, the Pod stops receiving new work: EndpointSlices mark terminating endpoints `ready: false`, and
  "ReplicaSets and other workload resources no longer treat the shutting-down Pod as a valid, in-service replica." — same
  page.
- Order among containers is not guaranteed: "the containers in the Pod receive the TERM signal at different times and in
  an arbitrary order. If the order of shutdowns matters, consider using a `preStop` hook to synchronize." — same page.
- When the grace period expires, "The container runtime sends `SIGKILL` to any processes still running", the Pod is
  moved to a terminal phase, and its API object is force-deleted (grace period 0). — same page.

**systemd**
- `KillMode=` defaults to `control-group`: on stop, "all remaining processes in the control group of this unit will be
  killed". `mixed` sends SIGTERM to the main process and SIGKILL to the rest of the cgroup. Setting `process` or `none`
  is "not recommended" because it "allows processes to escape the service manager's lifecycle ... and to remain running
  even while their service is considered stopped". — [systemd.kill(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.kill.html) (source: [systemd/systemd man/systemd.kill.xml](https://github.com/systemd/systemd/blob/main/man/systemd.kill.xml))
- Sequence: "Processes will first be terminated via SIGTERM ... If processes still remain after ... the delay configured
  via the TimeoutStopSec= has passed ... the termination request is repeated with the SIGKILL signal or the signal
  specified via FinalKillSignal=". `KillSignal=` "Defaults to SIGTERM", and "right after sending the signal ... systemd
  will always send SIGCONT, to ensure that even suspended tasks can be terminated cleanly." — same.
- `TimeoutStopSec=` bounds each `ExecStop=` command and then the wait for the service itself: "If it does not terminate
  in the specified time, it will be forcibly terminated by SIGKILL." It defaults to the manager's
  `DefaultTimeoutStopSec=`. — [systemd.service(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html) (source: [man/systemd.service.xml](https://github.com/systemd/systemd/blob/main/man/systemd.service.xml))
- The `ExecStop=` command "should hence be a synchronous operation, not an asynchronous one", because an asynchronous
  stop command "may not result in a clean stop". — same.
- `DefaultTimeoutStopSec=` is a build-time constant (`&DEFAULT_TIMEOUT_SEC;`); upstream's build option
  `default-timeout-sec` has `value : 90` ("default timeout for system unit start/stop"). So stock systemd waits 90 s
  between SIGTERM and SIGKILL, against Kubernetes' 30 s. — [systemd-system.conf(5)](https://www.freedesktop.org/software/systemd/man/latest/systemd-system.conf.html); [systemd meson_options.txt](https://github.com/systemd/systemd/blob/main/meson_options.txt)

**Checkpoint-before-stop and cooperative cancellation in durable-execution frameworks**
- Temporal: "Activity Cancellations are delivered to Activities from the Temporal Service when they Heartbeat.
  Activities that don't Heartbeat can't receive a Cancellation", and "Heartbeat throttling may lead to Cancellation
  getting delivered later than expected." — [Temporal: Detecting Activity failures](https://docs.temporal.io/encyclopedia/detecting-activity-failures) (source: [temporalio/documentation detecting-activity-failures.mdx](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/detecting-activity-failures.mdx))
- Temporal heartbeats double as checkpoints: "A Heartbeat can include an application layer payload that can be used to
  _save_ Activity Execution progress", and that progress "will be available during the next retry attempt, provided
  that the Worker itself did not crash before delivering it". "Heartbeating is best thought about not in terms of time,
  but in terms of 'How do you know you are making progress?'" — same.
- LangGraph: when an interrupt fires, "LangGraph saves the graph state using its persistence layer and waits
  indefinitely"; "the checkpointer writes the exact graph state so you can resume later, even when in an error state";
  the `thread_id` "is effectively your persistent cursor". Production use needs "a persistent checkpointer (e.g. backed
  by a database)". — [LangGraph: Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) (source: [langchain-ai/docs interrupts.mdx](https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/interrupts.mdx))
- OpenAI Agents SDK: a paused run is serialised as `RunState`, which "is designed to be durable. Use `state.to_json()`
  or `state.to_string()` to store pending work in a database or queue and recreate it later". — [OpenAI Agents SDK: Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/) (source: [openai/openai-agents-python docs/human_in_the_loop.md](https://github.com/openai/openai-agents-python/blob/main/docs/human_in_the_loop.md))
- Anthropic's long-running coding-agent harness makes the "checkpoint" an ordinary repository artifact. Each session
  must "make incremental progress ... while also leaving the environment in a clean state at the end of a session". The
  most reliable way to get that was "to ask the model to commit its progress to git with descriptive commit messages
  and to write summaries of its progress" in a `claude-progress.txt` file, so the next session "start[s] with a fresh
  context window" by reading the git log and progress file. — [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents)

**Compensation (saga) for work that cannot be rolled back**
- "Implement a compensating transaction that undoes the effects of completed steps in the original operation ...
  simply restor[ing] the system to its original state ... can overwrite changes from other concurrent application
  instances." "As the original operation runs, the system records information about each step and how to undo it. If
  the operation fails, the workflow rewinds through the completed steps and reverses each step." — [Azure Architecture Center: Compensating Transaction pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/compensating-transaction) (source: [MicrosoftDocs/architecture-center compensating-transaction.md](https://github.com/MicrosoftDocs/architecture-center/blob/main/docs/patterns/compensating-transaction.md))
- "Compensating transactions are eventually consistent operations and can fail. The system should record progress so
  that it can resume the compensating transaction from the point of failure. A step might run multiple times when
  retried, so design each step as an idempotent command." Compensation also "might not need to undo the work in the
  exact reverse order", and a single failed step does not always call for a full rollback. — same.

**Leases, TTLs and lock release**
- etcd: "Leases are a mechanism for detecting client liveness. The cluster grants leases with a time-to-live. A lease
  expires if the etcd cluster does not receive a keepAlive within a given TTL period." "When a lease expires or is
  revoked, all keys attached to that lease will be deleted." The TTL in a grant request is "the advisory time-to-live";
  the server returns the TTL it actually chose. — [etcd v3.6 API: Lease API](https://etcd.io/docs/v3.6/learning/api/#lease-api) (source: [etcd-io/website api.md](https://github.com/etcd-io/website/blob/main/content/en/docs/v3.6/learning/api.md))
- Kubernetes uses `coordination.k8s.io` Lease objects for node heartbeats (each heartbeat updates `spec.renewTime`)
  and for leader election. With the `ControllerManagerReleaseLeaderElectionLockOnExit` feature gate, kube-controller-manager
  "actively releases its leader election lock during leader transitions, rather than waiting for the lock's TTL to
  expire", which shortens leader hand-over. — [Kubernetes: Leases](https://kubernetes.io/docs/concepts/architecture/leases/) (source: [kubernetes/website leases.md](https://github.com/kubernetes/website/blob/main/content/en/docs/concepts/architecture/leases.md))
- **[secondary]** Kleppmann's argument ("How to do distributed locking", 2016): a GC pause, network delay or process
  pause can let a client keep acting on a lock that already expired. The fix is a fencing token, a number that grows
  with every lock grant and is sent with every write. The storage service rejects writes whose token is lower than the
  highest it has seen. He separates locks used for *efficiency* (a failure only causes duplicate work, so a single Redis
  node is fine) from locks used for *correctness* (a failure corrupts data, so real consensus such as ZooKeeper is needed,
  not Redlock). Original: [martin.kleppmann.com, 2016-02-08](https://martin.kleppmann.com/2016/02/08/how-to-do-distributed-locking.html) (not reachable here); summarised and quoted in [antirez's reply, "Is Redlock safe?"](https://www.antirez.com/news/101) and [surfingcomplexity: locks, leases, fencing tokens](https://surfingcomplexity.blog/2025/03/03/locks-leases-fencing-tokens-fizzbee/).
- **[secondary]** Production equivalents: Hazelcast `FencedLock` orders lock holders by "a monotonic fencing token,
  which increments each time the lock is assigned to a new owner" ([Hazelcast FencedLock javadoc](https://docs.hazelcast.org/docs/5.3.1/javadoc/com/hazelcast/cp/lock/FencedLock.html)).
  etcd's `contrib/lock` example shows a storage service refusing a write from a client holding an outdated lease
  version, and notes that lease mechanisms depend on the physical clocks of both the lock service and the client
  ([etcd contrib/lock README](https://github.com/etcd-io/etcd/blob/main/contrib/lock/README.md)).
- **[secondary]** Scope caveat: fencing matters only when a stale holder's write to shared state would do harm. Jobs
  that only send notifications can often use a plain lock. — [surfingcomplexity.blog](https://surfingcomplexity.blog/2025/03/03/locks-leases-fencing-tokens-fizzbee/); [hackernoon: the fencing gap](https://sia.hackernoon.com/the-fencing-gap-why-your-distributed-lock-isnt-safe-and-how-to-fix-it)

### Inferences
- A safe stop ladder for a stuck coding-agent session maps directly onto SIGTERM, grace, SIGKILL:
  (1) a *stop request* the session can see and act on (a control-plane message or label, the agent-level equivalent of
  SIGTERM / Temporal cancellation); (2) a bounded *grace window* in which the session commits WIP to its own branch,
  writes the progress note / `SessionCheckpoint`, and releases its claim (the `preStop` equivalent); (3) a *hard stop*
  of the session or container when the window expires. Defaults of 30 s (Kubernetes) and 90 s (systemd) are tuned for
  servers. An LLM session that has to finish a tool call and write a commit needs minutes, so this budget should be
  explicit and set per role.
- Like Temporal activities that do not heartbeat, a session stuck inside a long tool call may never see a cooperative
  stop request. A cooperative signal alone is not enough: the hard-stop phase, plus lease expiry, is what guarantees the
  stop happens.
- Releasing a claim on graceful exit (as kube-controller-manager now does) should be the normal path. Lease TTL expiry
  is the fallback for a session that was hard-killed or hangs. Neither covers a session that is "stopped" but still has
  an in-flight `git push` or API call. For that, the control plane must reject writes carrying a stale claim epoch
  (fencing): for example, the work-item claim records a monotonically increasing epoch, and the merge/push gate rejects
  work tagged with an older epoch.
- Coding-agent side effects on a forge (comments, labels, branches, PRs) cannot be rolled back. A stop that leaves
  partial work should run *compensations* (close the draft PR, remove the "in progress" label, post one summary
  comment), not try to restore earlier state, and each compensation must be idempotent and resumable.

### Gaps
- Could not reach Kleppmann's original article. Its claims are taken from secondary sources that agree with each other
  and with the etcd and Hazelcast docs.
- ZooKeeper's lock recipe (ephemeral sequential znodes, and sequence numbers used as fencing tokens) was not fetched; the
  docs path guessed on GitHub returned 404. Consul session/lock-delay docs were not fetched either.
- Found no source on whether Gitea 28.x exposes anything usable as a fencing check (for example, conditional updates or
  ETag/If-Match on the issue, label or branch APIs). This needs checking against the Gitea API before the epoch design
  above is chosen.

## 2. Idempotent side effects: idempotency keys for notifications/comments, at-least-once delivery and dedupe

### Takeaway
Under at-least-once delivery, a watchdog will retry, double-fire and race with itself. Every outbound side effect
(a page, a comment, a label change) therefore needs a deterministic idempotency or dedup key, a server-side record of
what that key already did, and a retention window long enough to cover retries. Stripe's API and Brandur's design give
the request-level pattern. PagerDuty's `dedup_key` and Alertmanager's grouping give the alerting-level pattern.

### Cited Findings
- Stripe (via search-engine extract of the official page): "we suggest using V4 UUIDs, or another random string with
  enough entropy to avoid collisions. Idempotency keys are up to 255 characters long." For API v1, Stripe "saves the
  status code and body of the first request made with a given idempotency key after endpoint execution begins. Retries
  with the same key return the saved response, including 500 errors." Keys can be removed "after they're at least 24
  hours old", and a reused key after pruning is treated as a new request. Reusing a key with different parameters is an
  error. "All POST requests accept idempotency keys"; GET and DELETE are idempotent by definition. With API v2,
  "retries don't repeat successful operations. Stripe retries failed or partially failed work to completion when
  possible." — **[secondary: search extract]** [Stripe API: Idempotent requests](https://docs.stripe.com/api/idempotent_requests)
- Brandur Leach (then at Stripe), "Implementing Stripe-like Idempotency Keys in Postgres" (2017-10-27): "An idempotency
  key is a unique value that's generated by a client and sent to an API along with a request ... If a request should
  fail partway through, the client retries with _the same_ idempotency key value, and the server uses it to look up the
  request's state and continue from where it left off." — [brandur.org/idempotency-keys](https://brandur.org/idempotency-keys) (source: [brandur/sorg idempotency-keys.md](https://github.com/brandur/sorg/blob/master/content/articles/idempotency-keys.md))
- Same article: calls to other systems are *foreign state mutations*. Some are idempotent by nature, some can be made
  idempotent with the remote side's own idempotency key, and the rest need care. Local changes are grouped into *atomic
  phases*, and "A ***recovery point*** is a name of a check point that we get to after having successfully executed any
  atomic phase _or_ foreign state mutation", so a retried request jumps back to "the point in the lifecycle just before
  the last attempt failed". A `locked_at` field marks a key "actively being worked", and concurrent lockers are
  serialised (one is aborted) by a `SERIALIZABLE` transaction. — same.
- Same article: a ***completer*** process finds requests "that look like they never finished ... and push[es] through
  to completion". A ***reaper*** deletes old keys, because keys guarantee idempotence and are "not ... a permanent
  archive". Brandur suggests keeping them "about 72 hours so that even if a bug is deployed on Friday ... a developer
  would have a chance to commit a fix" on Monday. — same.
- LangGraph's resume semantics force idempotency: on resume "the runtime restarts the entire node from the
  beginning—it does not resume from the exact line where `interrupt` was called", so "side effects called before
  `interrupt` must be idempotent". Recommended: "Use idempotent operations before `interrupt`" (e.g. upsert), "Place side
  effects after `interrupt` calls", "Separate side effects into separate nodes". Also: "Do not wrap `interrupt` calls in
  try/except", because the pause is a special exception that a bare `except` swallows. — [LangGraph: Interrupts, Rules of interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts) (source: [interrupts.mdx](https://github.com/langchain-ai/docs/blob/main/src/oss/langgraph/interrupts.mdx))
- Temporal Signals are "asynchronous write requests ... you cannot await any response or error" (fire-and-forget),
  while Updates are "synchronous, tracked write requests" whose sender "can wait for a response on completion or an
  error on failure", and an Update can be validated "before accepting it into the Workflow and its history". —
  [Temporal: Workflow message passing](https://docs.temporal.io/encyclopedia/workflow-message-passing) (source: [workflow-message-passing.mdx](https://github.com/temporalio/documentation/blob/main/docs/encyclopedia/workflow-message-passing/workflow-message-passing.mdx))
- **[secondary]** PagerDuty Events API v2: events that share a `dedup_key` are deduplicated into the same alert or
  incident, follow-up `acknowledge`/`resolve` events must reuse the trigger's key, and if the key is omitted each event
  creates a new incident. The API response echoes the `dedup_key` but no incident ID. — [Argo CD notifications: PagerDuty v2](https://argo-cd.readthedocs.io/en/stable/operator-manual/notifications/services/pagerduty_v2/); PagerDuty community forum threads in the same search. The official reference ([developer.pagerduty.com Events API v2](https://developer.pagerduty.com/docs/events-api-v2/overview/)) was not reachable.
- Alertmanager "takes care of deduplicating, grouping, and routing" alerts and of "silencing and inhibition".
  Notification state is replicated between HA instances. — [Prometheus: Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/) (source: [prometheus/alertmanager docs/alertmanager.md](https://github.com/prometheus/alertmanager/blob/main/docs/alertmanager.md))

### Inferences
- For a watchdog posting to Gitea, the dedup key should be *deterministic*, not a random UUID: for example
  `hash(session_id, stall_episode_id, action, escalation_level)`. A restarted watchdog then regenerates the same key
  for the same episode. Random v4 UUIDs (Stripe's advice) suit a client that keeps its key across retries. A stateless
  or restarted monitor needs a key derived from the event.
- Gitea issue comments have no idempotency-key header (not verified; see Gaps). The practical stand-in is Brandur's
  pattern: record `(dedup_key → comment_id, recovery_point)` in the repository or watchdog state *before* the external
  call, embed the key as a hidden marker in the comment body, and on retry search for the marker and *edit* (upsert)
  rather than post again. This mirrors LangGraph's "use upsert before the interrupt".
- Stop and escalate should be phased like Brandur's recovery points (`detected → stop_requested → checkpoint_seen →
  stopped → escalated → resolved`), so a watchdog that crashes mid-escalation resumes from the last recovery point and
  does not re-page.
- Keep dedup records for at least the longest escalation cycle plus a weekend. Brandur's 72 h is a sourced starting
  point; Stripe's 24 h is too short if a human does not respond until Monday.

### Gaps
- Could not confirm whether Gitea 28.x supports an `Idempotency-Key` header or conditional writes on comments and
  labels. No source was found.
- The PagerDuty `dedup_key` behaviour is from third-party docs and forum posts; the official Events API v2 reference
  page could not be fetched.

## 3. Escalation policy without alert fatigue: escalation levels, dedup, grouping, flapping suppression, HITL interrupts, circuit breakers

### Takeaway
Fatigue is avoided by paging only on actionable, novel, human-needing conditions; grouping and deduplicating
everything else; using hysteresis (`for` / `keep_firing_for`) against flapping; suppressing dependent alerts with
inhibition; and escalating on *non-acknowledgement within a timeout* rather than re-sending the same page. Agent
frameworks provide the "pause and wait for a human" mechanism (LangGraph `interrupt`, OpenAI Agents SDK approvals,
Temporal Signals/Updates). A circuit breaker with a manual reset is what stops endless automatic stop/restart loops.

### Cited Findings

**What deserves a page**
- **[secondary]** Google SRE book, ch. 6 "Monitoring Distributed Systems": every page should be actionable; a page that
  doesn't require human interaction or thought shouldn't be a page; pages should be about novel events; pages are
  "extremely fatiguing" and people can handle only a few a day; alert on symptoms over causes. —
  [sre.google: Monitoring Distributed Systems](https://sre.google/sre-book/monitoring-distributed-systems/) (not reachable), via [O'Reilly Radar reprint](https://www.oreilly.com/radar/monitoring-distributed-systems) and the chapter notes at [nds.srht.site](https://nds.srht.site/posts/sre-handbook-monitoring-distributed-systems/) and [bitmaybewise](https://bitmaybewise.substack.com/p/sre-book-notes-monitoring-distributed)

**Grouping, timing, inhibition, flapping**
- Alertmanager grouping "categorizes alerts of similar nature into a single notification". Example: group by cluster
  and alertname so an outage "sends a single compact notification". — [Prometheus: Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)
- Inhibition: "suppressing notifications for certain alerts if certain other alerts are already firing", e.g. a
  cluster-unreachable alert mutes all other alerts for that cluster. "This prevents notifications for hundreds or
  thousands of firing alerts that are unrelated to the actual issue." — same.
- Route timing defaults: `group_wait` 30s (wait before the first notification for a new group; "If an alert is resolved
  before group_wait has elapsed, no notification will be sent"), `group_interval` 5m (wait before notifying about new
  alerts added to a group), and `repeat_interval` 4h (wait before re-sending a notification that was already sent). —
  [Alertmanager configuration](https://prometheus.io/docs/alerting/latest/configuration/) (source: [docs/configuration.md](https://github.com/prometheus/alertmanager/blob/main/docs/configuration.md))
- Prometheus alerting rules' optional `keep_firing_for` "tells Prometheus to keep this alert firing for the specified
  duration after the firing condition was last met. This can be used to prevent situations such as flapping alerts,
  false resolutions due to lack of data loss". The `for` clause requires a condition to hold before firing. —
  [Prometheus: Alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) (source: [prometheus/prometheus alerting_rules.md](https://github.com/prometheus/prometheus/blob/main/docs/configuration/alerting_rules.md))

**Escalation levels and on-call practice**
- PagerDuty's own on-call guide: "Team alert escalation happens within 5 minutes, set/stagger your notification timeouts
  (push, SMS, phone, etc.) accordingly"; there are primary and backup on-call roles; "There should be no expectation to
  be the first to acknowledge _all_ of the alerts ... That's what we have the backup on-call and schedule for"; "If it
  does not look like a problem you are the expert for, then escalate to another team"; motto "Never hesitate to
  escalate." Noisy alerts are listed as something the on-call person should fix. — [PagerDuty Incident Response: Being On-Call](https://response.pagerduty.com/oncall/being_oncall/) (source: [PagerDuty/incident-response-docs being_oncall.md](https://github.com/PagerDuty/incident-response-docs/blob/master/docs/oncall/being_oncall.md))
- Opsgenie is being retired: end of sale 2025-06-04, end of support 2027-04-05, with customers pointed to Jira Service
  Management or Compass, so it is a poor target for new integrations. — **[secondary: search extract of Atlassian pages]** [Atlassian: Opsgenie migration](https://www.atlassian.com/software/opsgenie/migration); [Adaptavist summary](https://www.adaptavist.com/blog/atlassian-opsgenie-availability-changes-effective-june-4-2025)

**Human-in-the-loop interrupts in agent frameworks**
- LangGraph `interrupt()`: the graph saves state and "waits indefinitely until you resume execution with a response";
  the resume value passed via `Command(resume=...)` becomes `interrupt()`'s return value. A typed `response_schema`
  (Pydantic, TypedDict or dataclass) validates the human's answer; invalid input raises and "you can retry with a
  corrected `Command(resume=...)` using the same thread ID". Parallel branches can raise several interrupts that are
  resumed together by mapping interrupt IDs to resume values. — [LangGraph: Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- OpenAI Agents SDK: tools declare `needs_approval` (bool or per-call function). Pending approvals surface as
  `RunResult.interruptions`; the caller converts to `RunState`, calls `state.approve(...)`/`state.reject(...)`, and
  resumes. "Callable approval rules fail closed when the SDK cannot safely inspect the arguments." Sticky
  `always_approve`/`always_reject` decisions are scoped per agent and tool. Partial resolution is allowed: unresolved
  items stay in `interruptions`. — [OpenAI Agents SDK: Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/)
- OpenAI Agents SDK guardrails ("tripwires"): parallel guardrails (default) give the best latency, but "if the
  guardrail's tripwire is triggered, the agent may have already consumed tokens and executed tools before being
  cancelled". Blocking mode (`run_in_parallel=False`) means "the agent never executes, preventing token consumption and
  tool execution". On an output tripwire, "the runner asks the configured session to persist already-completed tool
  call and tool output items". — [OpenAI Agents SDK: Guardrails](https://openai.github.io/openai-agents-python/guardrails/) (source: [docs/guardrails.md](https://github.com/openai/openai-agents-python/blob/main/docs/guardrails.md))
- **[secondary]** OpenAI's "A practical guide to building agents" names two human-intervention triggers: *exceeding
  failure thresholds* ("Set limits on agent retries or actions. If the agent exceeds these limits ... escalate to human
  intervention") and *high-risk actions* (sensitive, irreversible or high-stakes actions keep human oversight "until the
  agent's reliability is proven"). — [OpenAI guide PDF](https://cdn.openai.com/business-guides-and-resources/a-practical-guide-to-building-agents.pdf) (not reachable), via [Cobus Greyling](https://cobusgreyling.substack.com/p/openai-ai-agent-design-guidance) and [ibl.ai](https://ibl.ai/blog/openai-a-practical-guide-to-building-agents.md)
- Claude Code hooks: a `Stop`/`SubagentStop` hook can return `{"decision": "block", "reason": "..."}`, which "Prevents
  Claude from stopping, continues the conversation", or `{"continue": false, "stopReason": "..."}` to halt. — [Claude Code: Hooks reference](https://code.claude.com/docs/en/hooks)

**Circuit breaker**
- Three states. Closed: count recent failures, and trip to Open past a threshold within a time window (the counter
  "automatically resets at periodic intervals" so occasional failures don't trip it). Open: fail immediately.
  Half-Open: let "a limited number of requests" through; success closes the breaker, and "If any invocation fails, the
  circuit breaker enters the Open state immediately". — [Azure Architecture Center: Circuit Breaker pattern](https://learn.microsoft.com/en-us/azure/architecture/patterns/circuit-breaker) (source: [circuit-breaker.md](https://github.com/MicrosoftDocs/architecture-center/blob/main/docs/patterns/circuit-breaker.md))
- Same doc: use "an increasing time-out timer" (seconds at first, then minutes). "Manual override: If the recovery time
  for a failing operation is extremely variable, you should provide a manual reset option that enables an administrator
  to close a circuit breaker and reset the failure counter", and to force it Open. Half-Open "helps prevent a recovering
  service from suddenly being flooded with requests". — same.

### Inferences
- A sourced escalation ladder for a stuck agent session: **L0** in-band nudge to the session itself (cheap, may fix a
  loop); **L1** the supervising agent (Lead), which may only *re-plan or reassign*; **L2** a human, paged only when L1
  has not acknowledged or resolved within a fixed timeout (PagerDuty uses 5 min for human tiers; agent tiers can be
  shorter). Escalate on missing acknowledgement, not by re-sending the same alert. Repeats follow a long
  `repeat_interval` (Alertmanager default 4 h).
- Anti-fatigue rules translated to agents: (a) group stall alerts per work item or per repo, not per heartbeat miss;
  (b) apply hysteresis (`for` before declaring stuck, `keep_firing_for` before declaring recovered) so a session that
  alternates between progress and stall doesn't flap; (c) inhibit per-session "stuck" alerts when a shared dependency
  alert is firing (Gitea down, model API outage, CI runner pool empty); (d) page humans only for the two OpenAI triggers
  (failure threshold exceeded, high-risk or irreversible next step) or when L1 has failed.
- The circuit breaker belongs on the *recovery* action, not the detector. After N automatic stop/restart cycles on the
  same work item within a window, the breaker opens: no more auto-restarts, the item is parked, and only a human
  (manual override) closes it. Using increasing open-timeouts avoids a tight restart loop.
- For pausing rather than killing, LangGraph `interrupt` and OpenAI `RunState` are the closest analogues to a "paused,
  awaiting human" agent state. Both persist state durably and resume via an explicit, schema-validated answer, which
  fits a typed escalation card (options: resume / reassign / abandon with compensation).

### Gaps
- Could not fetch the Google SRE book chapters directly (ch. 6 Monitoring, ch. 11 Being On-Call, ch. 29 Dealing with
  Interrupts). Quotes are from a reprint and secondary notes.
- PagerDuty escalation-policy product mechanics (number of levels, the "escalation timeout" minimum, round-robin
  layers, repeat-policy counts) were not fetched from PagerDuty's knowledge base. Only PagerDuty's internal on-call
  guide (5-minute team escalation) is sourced.
- No source gives proven escalation timeouts for *agent* supervisors (L1) specifically.

## 4. Separation of duties: why the watchdog should not fix code itself; read-only monitors; least-privilege bot accounts

### Takeaway
Across these sources the detector and the remediator are separate roles. The watchdog observes and reports, can at most
issue a stop/pause, and runs with a narrowly scoped identity. Fixing is done by the owning worker or a different role,
under the usual review gates. OWASP's "Excessive Agency" names the failure modes this prevents: excessive
functionality, permissions and autonomy.

### Cited Findings
- Kubernetes Deployments: on a stalled rollout, "Kubernetes takes no action on a stalled Deployment other than to report
  a status condition ... Higher level orchestrators can take advantage of it and act accordingly, for example,
  rollback." — [Kubernetes: Deployments, progress deadline](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#progress-deadline-seconds)
- Alertmanager's job is to deduplicate, group, route, silence and inhibit, then send "notifications through configured
  receivers". The alerting pipeline does not remediate. — [Prometheus: Alertmanager](https://prometheus.io/docs/alerting/latest/alertmanager/)
- OWASP Top 10 for LLM Applications 2025, LLM06 Excessive Agency, root causes: "excessive functionality; excessive
  permissions; excessive autonomy." Examples include an extension meant to read data whose identity "not only has
  SELECT permissions, but also UPDATE, INSERT and DELETE permissions", one using "a generic high-privileged identity",
  and an application that "fails to independently verify and approve high-impact actions". Mitigations include
  minimising extensions, functionality and permissions, and acting "with the minimum privileges necessary". —
  [OWASP GenAI: LLM06:2025 Excessive Agency](https://genai.owasp.org/llmrisk/llm062025-excessive-agency/) (source: [OWASP LLM06_ExcessiveAgency.md](https://github.com/OWASP/www-project-top-10-for-large-language-model-applications/blob/main/2_0_vulns/LLM06_ExcessiveAgency.md))
- GitHub Actions secure-use reference, "Principle of least privilege": "you should ensure that the credentials being
  used within workflows have the least privileges required", and the `GITHUB_TOKEN` should be "granted the minimum
  required permissions". — [GitHub Docs: Secure use reference](https://docs.github.com/en/actions/reference/security/secure-use) (source: [github/docs secure-use.md](https://github.com/github/docs/blob/main/content/actions/reference/security/secure-use.md))
- Anthropic's agent framework: "In Claude Code, humans can stop Claude whenever they want and redirect its approach. It
  has read-only permissions by default ... but must ask for human approval before taking any actions that modify code
  or systems." — [Anthropic: Our framework for developing safe and trustworthy agents](https://www.anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents)
- Anthropic's harness found that a later agent instance "would look around, see that progress had been made, and declare
  the job done". It used "strongly-worded instructions like 'It is unacceptable to remove or edit tests'" and a JSON
  feature list that agents may only edit "by changing the status of a passes field". In other words, the worker cannot
  be trusted to self-certify completion. — [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents)

### Inferences
- Reasons the watchdog should not fix code, taken from the findings: (a) a fix needs write permissions on code, which
  turns a monitor into a high-privilege actor (OWASP excessive permissions); (b) a watchdog that fixes and then judges
  whether the session is "unstuck" is grading its own work, the self-certification failure Anthropic's harness had to
  design around (and it conflicts with this repo's constitution: "nobody approves their own work", Article on separated
  authority in `.specify/memory/constitution.md`); (c) a stuck-detector runs on less context than the worker, so its
  "fix" is more likely to be wrong, and its edits would race with the worker's in-flight writes (the zombie-writer
  problem from section 1).
- Recommended capability set for a watchdog bot account: read on repos, issues, PRs and CI; write limited to (i) posting
  or editing its own deduplicated comments, (ii) setting a narrow set of state labels (e.g. `agent:stalled`,
  `agent:paused`), and (iii) calling the session stop/pause API. No push, no merge, no approve, no branch-protection
  access. A separate identity per role keeps audit trails clean.
- Stops and pauses are *proposals executed by policy*: the watchdog emits the event, and a policy gate (or the Lead)
  decides whether a hard stop is allowed (for example, not during a push or migration). This matches the
  "agents propose and policy decides" principle in the repo constitution.

### Gaps
- Could not fetch NIST SP 800-53 AC-5 (Separation of Duties) / AC-6 (Least Privilege) text for a formal citation.
- No source found on Gitea 28.x token scopes fine-grained enough to allow "comment + label but not push" on a
  per-repo basis. This needs verifying in Gitea's API/token-scope docs.
- Found no published case study of a production *agent watchdog* that is explicitly read-only. The separation argument
  here is built from general SRE and security sources plus Anthropic's harness findings.

## 5. AI-agent-specific guidance on pausing, stopping and handing off

### Takeaway
Agent-specific guidance agrees on: durable state so a pause can last indefinitely (LangGraph checkpointer, OpenAI
`RunState`); repository artifacts (git commits, progress file, feature list) as the hand-off medium between sessions;
human stop and redirect at any time; and treating agent-initiated "I'm stuck, asking" stops as a first-class oversight
signal alongside human interrupts. Anthropic's 2026 telemetry suggests experienced users move from per-action approval
to monitor-and-interrupt, which is what a watchdog automates.

### Cited Findings
- Anthropic, "Measuring AI agent autonomy in practice": among the longest Claude Code turns, the 99.9th-percentile turn
  duration "nearly doubled, from under 25 minutes to over 45 minutes" between October 2025 and January 2026. The median
  turn is about 45 seconds. — [Anthropic Research: Measuring agent autonomy](https://www.anthropic.com/research/measuring-agent-autonomy)
- Same: "Among new users, roughly 20% of sessions use full auto-approve, which increases to over 40% as users gain
  experience". Experienced users "auto-approve more frequently, but interrupt more often", shifting "from approving
  individual actions to monitoring what the agent does and intervening when needed." — same.
- Same: "On the most complex tasks, Claude Code stops to ask for clarification more than twice as often as humans
  interrupt it". "Training models to recognize their own uncertainty and surface issues to humans proactively is an
  important safety property that complements external safeguards like human approval flows and access restrictions."
  Recommendations: "Model and product developers should invest in post-deployment monitoring" and "Product developers
  should design for user oversight". — same.
- Anthropic, safe-agent framework: humans "should retain control over how their goals are pursued, particularly before
  high-stakes decisions are made". Claude Code shows "planned actions through a real-time to-do checklist, and users can
  jump in at any time". On transparency, "Too little information leaves humans unable to assess whether the agent is on
  track ... Too much can overwhelm them". — [Anthropic: Our framework for developing safe and trustworthy agents](https://www.anthropic.com/news/our-framework-for-developing-safe-and-trustworthy-agents)
- Anthropic harness for multi-context-window coding: an *initializer* session sets up `init.sh`, a `claude-progress.txt`
  log, a feature list with every item initially "failing", and an initial git commit. Every later *coding* session works
  on "only one feature at a time", commits with descriptive messages, and updates the progress file. "The key insight
  here was finding a way for agents to quickly understand the state of work when starting with a fresh context window,
  which is accomplished with the claude-progress.txt file alongside the git history." — [Anthropic: Effective harnesses for long-running agents](https://www.anthropic.com/research/effective-harnesses-for-long-running-agents)
- LangGraph interrupts persist the exact graph state and wait indefinitely; resume is keyed by `thread_id`. —
  [LangGraph: Interrupts](https://docs.langchain.com/oss/python/langgraph/interrupts)
- OpenAI Agents SDK: paused runs are durable `RunState` blobs that can be stored "in a database or queue", and the
  approval surface is "run-wide", covering hand-offs and nested `Agent.as_tool()` runs. — [OpenAI Agents SDK: Human-in-the-loop](https://openai.github.io/openai-agents-python/human_in_the_loop/)
- Claude Code `Stop` hooks can veto a stop (`decision: block`) or force one (`continue: false` with a `stopReason`). —
  [Claude Code: Hooks reference](https://code.claude.com/docs/en/hooks)

### Inferences
- For coding-agent sessions coordinating through a repository, the "checkpoint before stop" step is concrete and
  sourced: commit WIP to the session's branch, update the progress/hand-off note (in this repo, a
  `SessionCheckpoint` plus spec Clarifications), and leave the work item in a state the next session can read from git
  alone. A hard stop without this loses only the work since the last commit, which is an argument for frequent
  incremental commits as a watchdog precondition.
- A watchdog should treat an *agent-initiated* question or stop (asking for clarification, blocked on a decision) as a
  distinct, healthy state ("waiting on human"), not as "stuck". Escalation then routes the question to its owner rather
  than stopping the session. Anthropic's data show these agent-initiated pauses are common on hard tasks.
- Claude Code's `Stop` hook gives a watchdog-adjacent control point *inside* the session: a hook can block a premature
  "done" (the self-certification failure above) or end the session with a recorded `stopReason`. That reason can feed
  the hand-off note.
- Anthropic's recommendation to invest in post-deployment monitoring and design for user oversight, together with
  users' observed shift to monitor-and-interrupt, supports the watchdog as an *oversight aid that surfaces and pauses*,
  not an autonomous fixer.

### Gaps
- OpenAI's "A practical guide to building agents" PDF and OpenAI's Codex long-horizon posts were not reachable. Their
  escalation triggers are cited from secondary summaries only.
- LangGraph's "Durable execution" page could not be retrieved (source path 404). Its durability-mode details (e.g.
  `exit`/`async`/`sync` checkpoint modes) are not covered here.
- Found no Anthropic or OpenAI guidance that specifically covers an *external* watchdog stopping another agent session
  (as opposed to human interrupt or in-session hooks), or recommended grace periods for agent shutdown. That piece of
  the design is inferred from infrastructure practice (sections 1-3).
