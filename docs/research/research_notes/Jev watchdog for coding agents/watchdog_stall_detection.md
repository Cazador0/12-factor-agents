# Watchdog and stall-detection patterns for long-running autonomous coding agents

Research date: 2026-10-22. Method note: most thresholds below were read directly from current source code or
documentation source files (GitHub `main`/`master` raw files fetched 2026-10-22), not from summaries. Several sites
(sre.google, arxiv.org, kubernetes.io rendered pages, developers.openai.com, docs.langchain.com, proceedings.neurips.cc)
were unreachable from the research environment; where a fact for those comes only from a search-engine summary or a
secondary write-up, it is marked **[secondary]**.

## 1. How production systems detect hung or stalled work (heartbeats, liveness vs readiness, progress deadlines, inactivity timeouts) and their defaults

### Takeaway
Production systems separate three questions: is the worker alive (heartbeat / liveness), is it able to take work
(readiness), and is the *job* advancing (progress deadline / no-output timeout). Defaults cluster around a 5-30 s
heartbeat, a 3-miss failure threshold, and a 5-10 minute "no progress" window, with a much longer hard wall-clock cap
(1-6 h for CI jobs). Several systems only *report* a stall and leave the action to a higher-level controller.

### Cited Findings

**Kubernetes**
- Probe field defaults (from the API type definitions): `timeoutSeconds` defaults to 1 s (min 1); `periodSeconds`
  defaults to 10 s (min 1); `successThreshold` defaults to 1 and "must be 1 for liveness and startup"; `failureThreshold`
  defaults to 3 (min 1). So a default liveness probe restarts a container after ~3 consecutive failures, i.e. ~30 s of
  failed checks. — [kubernetes/api core/v1/types.go, `type Probe struct`](https://github.com/kubernetes/api/blob/master/core/v1/types.go)
- Startup probes exist so slow initialisation does not force a loose liveness probe: "set up a startup probe with the same
  command ... with a `failureThreshold * periodSeconds` long enough to cover the worst case startup time." Documented
  example: liveness `failureThreshold: 1, periodSeconds: 10`; startup `failureThreshold: 30, periodSeconds: 10`, giving
  "a maximum of 5 minutes (30 * 10 = 300s) to finish its startup"; once the startup probe succeeds, the liveness probe
  takes over. — [Kubernetes: Configure Liveness, Readiness and Startup Probes](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-startup-probes) (doc source: [kubernetes/website](https://github.com/kubernetes/website/blob/main/content/en/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes.md))
- Exec probes: a built-in probe fails on timeout, and `timeoutSeconds` "defaults to 1s". — same Kubernetes probes page.
- Deployment progress deadline: `.spec.progressDeadlineSeconds` is "the number of seconds the Deployment controller waits
  before indicating (in the Deployment status) that the Deployment progress has stalled"; **defaults to 600** (10 min).
  On expiry it sets condition `type: Progressing, status: "False", reason: ProgressDeadlineExceeded`. "Kubernetes takes no
  action on a stalled Deployment other than to report a status condition ... Higher level orchestrators can take advantage
  of it and act accordingly, for example, rollback." The deadline stops applying once the rollout completes. —
  [Kubernetes: Deployments, Progress Deadline Seconds](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#progress-deadline-seconds) (source: [kubernetes/website deployment.md](https://github.com/kubernetes/website/blob/main/content/en/docs/concepts/workloads/controllers/deployment.md))
- Note: the progress deadline measures *progress* (new ReplicaSet pods becoming available), not liveness; the timer is
  reset whenever progress is made (this is the Deployment controller's documented semantics for "progressing"). —
  [Kubernetes: Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#progressing-deployment)

**Temporal (durable workflows)**
- Activity timeouts: Schedule-To-Start default is infinity; Start-To-Close "has no default value of its own"; Schedule-To-Close
  default is infinity. "For long running Activity Executions, we recommend also using Activity Heartbeats and Heartbeat
  Timeouts." — [Temporal: Detecting Activity failures](https://docs.temporal.io/encyclopedia/detecting-activity-failures)
- Heartbeat Timeout = "the maximum time between Activity Heartbeats". If reached, the Activity Task fails and is retried per
  the Retry Policy. Unset is stored as `0s`, which means *disabled* (never fails for a missed heartbeat), not "immediate".
  The Heartbeat Timeout is capped at the Start-To-Close Timeout. — same Temporal page.
- Guidance: "For long-running Activities, we recommend using a relatively short Heartbeat Timeout and a frequent
  Heartbeat." Heartbeats can carry a progress payload so a retry resumes from saved progress. Cancellation is only
  delivered to activities that heartbeat. — same Temporal page.
- Heartbeat throttling: the worker sends at most one heartbeat per throttle interval = min(`heartbeatTimeout * 0.8` if set,
  else `defaultHeartbeatThrottleInterval`; `maxHeartbeatThrottleInterval`). Defaults: `defaultHeartbeatThrottleInterval`
  30 s, `maxHeartbeatThrottleInterval` 60 s. — same Temporal page.
- Key design principle: "Heartbeating is best thought about not in terms of time, but in terms of 'How do you know you are
  making progress?'" Heartbeat when "your underlying task must be able to report definite progress" and when you need to
  know the worker "is still alive and has not run out of memory or silently crashed". — same Temporal page.

**CI systems**
- GitHub Actions: `jobs.<job_id>.timeout-minutes` = "maximum number of minutes to let a job run before GitHub automatically
  cancels it. **Default: 360**." Step-level `timeout-minutes` maximum is 360 for hosted and self-hosted runners; must be a
  positive integer. No native no-output/inactivity timeout is documented on this page. —
  [GitHub Docs: Workflow syntax](https://docs.github.com/en/actions/reference/workflows-and-actions/workflow-syntax#jobsjob_idtimeout-minutes) (source: [github/docs](https://github.com/github/docs/blob/main/content/actions/reference/workflows-and-actions/workflow-syntax.md))
- GitLab CI: project job timeout "Must be 10 minutes or more, and less than one month. **Default is 60 minutes**." Jobs that
  exceed it are marked failed; a runner maximum timeout can also apply. "Jobs without an output for one hour are dropped
  regardless of the timeout. To prevent this from happening, add a script to continuously output progress." —
  [GitLab Docs: CI/CD pipeline settings](https://docs.gitlab.com/ci/pipelines/settings/#set-a-limit-for-how-long-jobs-can-run); workaround: [gitlab issue 25359](https://gitlab.com/gitlab-org/gitlab/-/issues/25359#workaround)
- CircleCI: step `no_output_timeout` = "Elapsed time the command can run without output ... **The default is 10 minutes**";
  maximum governed by the job's max run time. — [CircleCI configuration reference](https://circleci.com/docs/reference/configuration-reference/) (source: [circleci-docs](https://github.com/circleci/circleci-docs/blob/main/docs/reference/modules/ROOT/pages/configuration-reference.adoc))
- Buildkite: command steps take `timeout_in_minutes`; default and maximum timeouts are set per pipeline/org in the UI, and a
  job's timeout can be updated dynamically while running. — [Buildkite: Command step](https://buildkite.com/docs/pipelines/configure/step_types/command_step), [Buildkite: Build timeouts](https://buildkite.com/docs/pipelines/configure/build-timeouts)

**Airflow (current `main`, Airflow 3.x config)**
- `[scheduler] task_instance_heartbeat_timeout` **default 300 s**: "Local task jobs periodically heartbeat to the DB. If the
  job has not heartbeat in this many seconds, the scheduler will mark the associated task instance as failed and will
  re-schedule the task." A separate `task_instance_heartbeat_timeout_detection_interval` controls how often the scheduler
  checks. — [Airflow config.yml](https://github.com/apache/airflow/blob/main/airflow-core/src/airflow/config_templates/config.yml); rendered: [Airflow configuration reference](https://airflow.apache.org/docs/apache-airflow/stable/configurations-ref.html)
- `job_heartbeat_sec` default 5 s; `task_instance_heartbeat_sec` default "0"; `scheduler_health_check_threshold` default 30 s
  (scheduler considered unhealthy if its last heartbeat is older; used by `/health` and `airflow jobs check`);
  `task_queued_timeout` default 600 s (time a task may sit queued before retry/fail); `default_task_execution_timeout`
  default empty (None, i.e. no wall-clock limit unless set). — same Airflow config.yml.

**Celery**
- "A single task can potentially run forever, if you have lots of tasks waiting for some event that'll never happen you'll
  block the worker ... The best way to defend against this scenario happening is enabling time limits." Hard limit
  (`--time-limit` / `task_time_limit`) kills and replaces the process; soft limit (`--soft-time-limit` /
  `task_soft_time_limit`) raises `SoftTimeLimitExceeded` so the task can clean up first. Limits can be changed at runtime
  via `app.control.time_limit(...)`. — [Celery: Workers Guide, Time Limits](https://docs.celeryq.dev/en/stable/userguide/workers.html#time-limits) (source: [celery workers.rst](https://github.com/celery/celery/blob/main/docs/userguide/workers.rst))

### Inferences
- A two-tier design is standard: a **soft** signal (Celery soft limit, Kubernetes `ProgressDeadlineExceeded` condition,
  Temporal heartbeat-timeout -> retry) that allows cleanup or escalation, and a **hard** wall-clock cap (Celery hard limit,
  GitHub 360 min, GitLab 60 min). For an agent session this maps to: "stalled" status + nudge/escalate first, kill later.
- "No output" timeouts (CircleCI 10 min default; GitLab 1 h drop) are cheap stall detectors but are defeated by any process
  that prints (GitLab even recommends printing to stay alive). For coding agents, raw stdout/token activity is therefore a
  liveness signal, not a progress signal.
- The Kubernetes startup-probe pattern (generous window during start, tight window afterwards) suggests a separate, longer
  grace period for agent session start-up (cloning, dependency install, context loading) before stall rules apply.
- Kubernetes deliberately reports rather than acts on stalls; this matches the repository's constitution ("agents propose
  and policy decides"): a watchdog should emit a status/condition and let a policy-owning component decide on kill/restart.

### Gaps
- Celery's default values for `task_time_limit`/`task_soft_time_limit` were not visible in the fetched excerpt (believed to
  be "no limit" but not verified this session).
- The Airflow 2.x name `scheduler_zombie_task_threshold` (predecessor of `task_instance_heartbeat_timeout`) and the version
  of the rename were not verified this session.
- No documented native "no output" timeout was found for GitHub Actions or Buildkite command steps.
- The rendered kubernetes.io pages could not be fetched; facts come from the docs' source files in kubernetes/website and
  kubernetes/api, which are the source of the rendered pages.

## 2. How agent frameworks and coding agents detect loops and bound runs (documented thresholds)

### Takeaway
Agent frameworks use two mechanisms: hard step/cost/call budgets (OpenHands 500 iterations, SWE-agent $3 per instance,
LangGraph recursion limit) and explicit pattern detectors for repeated identical actions/errors. OpenHands has the most
explicit stuck detector: 4 identical action-observation pairs, 3 identical action-error pairs, 3 consecutive agent
monologue messages, 6-cycle alternating pattern, within a 20-event scan window, and it nudges the agent at the error
threshold before declaring it stuck.

### Cited Findings

**OpenHands (current Software Agent SDK)**
- `StuckDetectionThresholds` defaults: `action_observation = 4`, `action_error = 3`, `monologue = 3`,
  `alternating_pattern = 6` (all configurable, `ge=1`). — [OpenHands SDK conversation/types.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/types.py)
- Detector scans only recent history: `MAX_EVENTS_TO_SCAN_FOR_STUCK_DETECTION = 20` ("4 repeats x 2 events per cycle = 8
  events minimum, plus buffer for user messages"), and only events *since the last user message*. Patterns: repeating
  action-observation, repeating action-error, agent monologue (repeated messages without user input), alternating
  action-observation (A/B ping-pong), and context-window-error loops (the latter currently disabled with a TODO). Event
  equality ignores IDs/metrics and compares tool name, action content and thought. — [OpenHands SDK stuck_detector.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py)
- Graduated response: when an action-error streak first *equals* the threshold (3), the SDK injects a nudge: "You've called
  `{tool}` with the same arguments {threshold} times in a row and gotten the same error each time ... Repeating the exact
  same call again will not work — review the error message and either correct the arguments or try a different
  approach." It declares stuck only when the streak is "one repeat past the threshold" (> 3). — same stuck_detector.py.
- `LocalConversation` defaults: `max_iteration_per_run = 500`, `stuck_detection = True`. — [OpenHands SDK local_conversation.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/impl/local_conversation.py)
- Legacy OpenHands (v0.59.0, older architecture) used the same numbers hard-coded: 4 repeated action/observation pairs, 3
  repeated errors / identical error lines, 3 agent messages, 6 alternating pairs, and a last-10 condensation-event check;
  `OH_MAX_ITERATIONS = 500`; `max_budget_per_task` default None. — [OpenHands 0.59.0 controller/stuck.py](https://github.com/All-Hands-AI/OpenHands/blob/0.59.0/openhands/controller/stuck.py), [config_utils.py](https://github.com/All-Hands-AI/OpenHands/blob/0.59.0/openhands/core/config/config_utils.py), [openhands_config.py](https://github.com/All-Hands-AI/OpenHands/blob/0.59.0/openhands/core/config/openhands_config.py) (older guidance; superseded by the SDK)

**SWE-agent**
- Tool execution: `execution_timeout = 30` s per command; `total_execution_timeout = 1800` s; `install_timeout = 300` s;
  `max_consecutive_execution_timeouts = 3` ("Maximum number of consecutive execution timeouts before the agent exits"). On
  a timeout the agent gets an observation "The command '{command}' was cancelled because it took more than {timeout}
  seconds"; after 3 consecutive timeouts: "Exiting agent due to too many consecutive execution timeouts". —
  [SWE-agent sweagent/tools/tools.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/tools/tools.py), [sweagent/agent/agents.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/agent/agents.py)
- Budgets: `per_instance_cost_limit` default **$3.00**; `total_cost_limit` default 0 (disabled); `per_instance_call_limit`
  default 0 (disabled). Exceeding raises a cost-limit exit. `max_requeries = 3` (re-asking the model after malformed/blocked
  output). Deployment liveness check `is_alive(timeout=10)`. — [SWE-agent sweagent/agent/models.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/agent/models.py), [agents.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/agent/agents.py)

**Aider**
- `max_reflections = 3`: after lint/test/edit-format failures Aider feeds the error back ("reflection") at most 3 times,
  then warns "Only 3 reflections allowed, stopping." — [Aider aider/coders/base_coder.py](https://github.com/Aider-AI/aider/blob/main/aider/coders/base_coder.py)

**LangGraph**
- `DEFAULT_RECURSION_LIMIT = int(getenv("LANGGRAPH_DEFAULT_RECURSION_LIMIT", "10007"))` on `main` (Oct 2026). — [langgraph _internal/_config.py](https://github.com/langchain-ai/langgraph/blob/main/libs/langgraph/langgraph/_internal/_config.py)
- The value changed from 10000 to 10007 on 2026-03-30 in "fix(langgraph): avoid recursion limit default sentinel collision
  (#7355)" (the default doubles as a sentinel; 10007 avoids colliding with a user-chosen 10000). — [langgraph commit 2fb367e9](https://github.com/langchain-ai/langgraph/commit/2fb367e9), [PR #7355](https://github.com/langchain-ai/langgraph/pull/7355)
- **Older guidance:** LangGraph historically documented a default recursion limit of 25 super-steps; that is no longer the
  library default on `main`, so a LangGraph agent today is effectively unbounded unless `recursion_limit` is set explicitly.
  (The 25 figure is from earlier LangGraph docs; the date of the 25 -> 10000 change was not established this session.)

**AutoGen (AgentChat)**
- `AssistantAgent.max_tool_iterations` default **1** (`ge=1`): the agent executes one round of tool calls and returns; set
  higher to allow multi-step tool loops; it stops when the model returns text instead of tool calls or the maximum is
  reached. — [autogen _assistant_agent.py](https://github.com/microsoft/autogen/blob/main/python/packages/autogen-agentchat/src/autogen_agentchat/agents/_assistant_agent.py)

**Claude Code (hooks as a watchdog surface)**
- Hook `timeout` defaults: 600 s for `command`, `http` and `mcp_tool` hooks; 30 s for `prompt`; 60 s for `agent`. Hooks can
  return `{"continue": false, "stopReason": "..."}`, and "Returning `decision: \"block\"` or `continue: false` stops the
  agentic loop before the next model call". `onFailure` (`"continue"` default, or `"block"`) controls what happens when a
  hook itself fails. — [Claude Code docs: Hooks reference](https://code.claude.com/docs/en/hooks)

**Long-running coding-agent guidance (vendors)**
- Anthropic (2025-11-26): long-running harness = an initializer agent writes `init.sh`, a `claude-progress.txt` log and an
  initial git commit; a JSON feature list (200+ features in the example) starts all `"passes": false`; coding sessions may
  only flip `passes`, work on one feature per session, commit with descriptive messages and update the progress file; each
  session starts by reading progress file + git log + feature list and running a basic end-to-end check. Observed failure
  modes: trying to one-shot the app (running out of context mid-feature), **declaring victory too early**, leaving broken
  or undocumented state, and marking features done without end-to-end testing. — [Anthropic Engineering: Effective harnesses for long-running agents](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- OpenAI (Codex): an OpenAI developer reports a ~25-hour Codex run that stayed on task, running tests, lint and typecheck at
  each milestone, with spec/plan/constraints/status kept in markdown files Codex revisits; framed as "an experiment, not a
  production rollout". **[secondary: search-engine summary; page not directly fetchable]** — [OpenAI Developers blog: Run long horizon tasks with Codex](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex), [OpenAI Cookbook: long horizon tasks](https://developers.openai.com/cookbook/examples/codex/long_horizon_tasks/)
- A 2026 preprint reports that both Claude Code and Codex over-predict their own runtimes and that their retrospective time
  estimates degrade when timestamps are removed. **[secondary: search summary only]** — [alphaXiv: "Your agents are not time-aware" (Aug 2026)](https://alphaxiv.org/abs/2608.your-agents-are-not-time-aware)

### Inferences
- The common loop thresholds are small integers: **3** for "same failure again" (OpenHands action-error, SWE-agent
  consecutive timeouts, SWE-agent requeries, Aider reflections) and **4-6** for "same action/observation cycle"
  (OpenHands 4 identical pairs, 6 for A/B alternation). Alternation needs a higher count because two-state cycles occur
  legitimately (edit -> test -> edit -> test).
- Detectors compare normalised actions (tool + args + thought, ignoring IDs and timestamps), and reset on new user input.
  An agent watchdog working from traces should normalise the same way (e.g., hash of tool name + canonicalised args +
  error text).
- Nudge-before-kill (OpenHands injects a corrective message at the threshold and declares stuck one step later) is the
  agent analogue of Celery soft/hard limits.
- Because LangGraph's default recursion limit is now effectively unbounded (10007), and AutoGen's tool-iteration cap is 1,
  framework defaults are not a reliable watchdog; an external, explicitly configured budget is needed.
- Agents' own sense of elapsed time is unreliable (secondary evidence), so wall-clock and progress timers must live in the
  supervisor, not in the agent's self-report.

### Gaps
- The SWE-agent paper (arXiv 2405.15793 / NeurIPS 2024) could not be fetched; its statistics on cascading failed edits,
  trajectory length of resolved vs unresolved runs, and cost-limit exhaustion are not included.
- No documented loop-detection thresholds were found for Claude Code or Codex themselves (beyond hooks, budgets and
  harness guidance). Claude Code `--max-turns` and Stop-hook loop-guard details were not verified this session.
- AutoGen's group-chat termination defaults (e.g., `MaxMessageTermination`) and the project's maintenance status were not
  verified this session.

## 3. Progress metrics for agents, and distinguishing slow-but-progressing from stuck

### Takeaway
Sources converge on measuring *durable, externally verifiable* progress (state transitions that persist) rather than
activity: Kubernetes counts newly available replicas, Temporal heartbeats should report "definite progress", and the
Anthropic and OpenAI long-running harnesses use git commits, a feature list whose tests flip from failing to passing, and
a progress/status file. Activity (output, tokens, tool calls) proves liveness only.

### Cited Findings
- Temporal: heartbeat design should start from "How do you know you are making progress?"; heartbeats can carry a progress
  payload (e.g., offset into a large file) that the next attempt resumes from. — [Temporal: Detecting Activity failures](https://docs.temporal.io/encyclopedia/detecting-activity-failures)
- Kubernetes: the progress deadline judges whether the rollout has advanced (new ReplicaSet scaled, pods available), and
  stops applying once the rollout completes; stalls are reported as a status condition. — [Kubernetes: Deployments](https://kubernetes.io/docs/concepts/workloads/controllers/deployment/#progress-deadline-seconds)
- GitLab explicitly recommends emitting periodic output to avoid the one-hour no-output drop, i.e. output is a liveness
  keep-alive, not proof of progress. — [GitLab Docs: pipeline settings](https://docs.gitlab.com/ci/pipelines/settings/#set-a-limit-for-how-long-jobs-can-run)
- Anthropic long-running harness progress artefacts: git commits per feature, `claude-progress.txt`, JSON feature list with
  per-feature `passes` flags (agents may only change `passes`; "It is unacceptable to remove or edit tests"), and an
  end-to-end smoke check at session start. Marking features done on unit tests + curl alone missed end-to-end failures;
  browser-automation testing "as a human user would" improved bug detection. — [Anthropic Engineering](https://www.anthropic.com/engineering/effective-harnesses-for-long-running-agents)
- OpenAI Codex long-horizon practice: milestones verified with tests, lint and typecheck; markdown spec/plan/status files as
  a stable definition of "done". **[secondary: search summary]** — [OpenAI Developers blog](https://developers.openai.com/blog/run-long-horizon-tasks-with-codex)
- OpenHands' detector treats repetition of identical (action, observation) or (action, error) pairs as non-progress even
  when the agent is very active. — [OpenHands SDK stuck_detector.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/stuck_detector.py)
- MAST taxonomy (multi-agent failures): "step repetition" (FM-1.3, system-design category) is reported as the most frequent
  failure mode at ~15.7%, ahead of reasoning-action mismatch (~13.2%) and "unaware of termination conditions" (~12.4%);
  the work analysed 1,600+ annotated traces across 7 frameworks and was published at NeurIPS 2025. **[secondary: figures
  from search summaries and write-ups; arXiv not reachable; percentages may differ between paper versions v1-v3]** —
  [alphaXiv overview of arXiv 2503.13657](https://www.alphaxiv.org/overview/2503.13657); dataset/repo: [MAST GitHub](https://github.com/multi-agent-systems-failure-taxonomy/MAST)

### Inferences
- A practical progress vector for a coding-agent session, ranked by strength: (1) a test/acceptance check flips from fail to
  pass, or a feature/task flag flips; (2) a new commit (non-empty diff) or a pushed branch/PR update; (3) a new
  progress/checkpoint entry or decision trace; (4) a new *distinct* tool call or a tool call whose result differs from the
  previous identical call; (5) any output/tokens (liveness only).
- Slow-but-progressing vs stuck: slow means level (1)-(3) signals still arrive, just with long gaps, and level (4) shows
  novelty; stuck means no (1)-(3) signal within the progress window *and* (4) shows repetition (identical action/error
  hashes) or A/B alternation. Long-running single tool calls (builds, test suites) are "slow" while the tool reports
  liveness and should be bounded by a per-command timeout (cf. SWE-agent 30 s default / 1800 s total) rather than by the
  session progress window.
- Tool-call success rate alone is ambiguous: a looping agent can succeed repeatedly at a no-op, and a progressing agent
  can fail many exploratory commands; use it together with novelty and durable-state signals.

### Gaps
- No primary source found that publishes a quantitative "commits per hour" or "tests passing per hour" threshold for
  declaring a coding agent stuck; any such number would be a local policy choice.
- No source found evaluating tool-call success rate as a stuck predictor for coding agents.

## 4. Evidence on false positives: why require N consecutive bad observations (debouncing / hysteresis)

### Takeaway
Every mature system surveyed requires repetition or duration before acting: Kubernetes restarts only after
`failureThreshold` (default 3) consecutive probe failures, Prometheus `for` holds an alert in "pending" until the condition
persists and `keep_firing_for` prevents flapping, Temporal throttles heartbeats to 0.8x the timeout so normal jitter does
not trip it, and agent frameworks use 3-6 repeats. The SRE literature adds that pure duration gating trades detection
time for precision, and recommends pairing a long window with a short confirmation window.

### Cited Findings
- Kubernetes probes: `failureThreshold` defaults to 3, `successThreshold` to 1 (must be 1 for liveness/startup), period
  10 s, timeout 1 s; so one slow response does not restart a container. Startup probes exist because a tight liveness
  probe on a slow-starting app would cause false restarts. — [kubernetes/api types.go](https://github.com/kubernetes/api/blob/master/core/v1/types.go); [Kubernetes probes task page](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/#define-startup-probes)
- Prometheus: the `for` clause makes Prometheus "check that the alert continues to be active during each evaluation for
  [the duration] before firing"; active-but-not-firing alerts are "pending"; rules without `for` fire on first evaluation.
  `keep_firing_for` keeps an alert firing after the condition clears, used "to prevent situations such as flapping alerts,
  false resolutions due to lack of data loss, etc." — [Prometheus: Alerting rules](https://prometheus.io/docs/prometheus/latest/configuration/alerting_rules/) (source: [prometheus docs](https://github.com/prometheus/prometheus/blob/main/docs/configuration/alerting_rules.md))
- Temporal: heartbeat throttling at 0.8x the heartbeat timeout (30 s default / 60 s max) suppresses heartbeats "that aren't
  necessary to prevent a Heartbeat Timeout", i.e. the timeout must exceed the heartbeat interval with margin. —
  [Temporal: Detecting Activity failures](https://docs.temporal.io/encyclopedia/detecting-activity-failures)
- Agent frameworks: OpenHands requires 4 identical action-observation pairs (6 for alternation) and nudges at 3 identical
  errors before declaring stuck at 4; SWE-agent exits only after 3 *consecutive* command timeouts (a successful command in
  between resets the counter `_n_consecutive_timeouts`). — [OpenHands SDK types.py](https://github.com/OpenHands/software-agent-sdk/blob/main/openhands-sdk/openhands/sdk/conversation/types.py), [SWE-agent agents.py](https://github.com/SWE-agent/SWE-agent/blob/main/sweagent/agent/agents.py)
- Google SRE Workbook, "Alerting on SLOs": evaluates alerting strategies on precision, recall, detection time and reset
  time; recommends multiwindow, multi-burn-rate alerts where the short window is 1/12 of the long window and both must
  exceed the threshold; suggested starting points page at 2% of error budget consumed in 1 h and 5% in 6 h, and ticket at
  10% in 3 days. **[secondary: workbook page unreachable; numbers from search summary and third-party write-ups]** —
  [Google SRE Workbook ch. 5: Alerting on SLOs](https://sre.google/workbook/alerting-on-slos/); [Google Cloud blog on Medium: How to alert on SLOs](https://medium.com/google-cloud/how-to-alert-on-slos-2a5ce8c4e7dd)

### Inferences
- Debounce on *consecutive* observations (reset on any good observation), as Kubernetes and SWE-agent do, rather than on a
  count within a window, unless the bad state can flicker; for flicker, add hysteresis (`keep_firing_for`-style hold, or a
  separate recovery threshold).
- Window length must exceed the longest legitimate quiet period by a margin. Temporal's 0.8 factor and Kubernetes' 3 x 10 s
  are examples; for coding agents, the longest legitimate quiet period is a long build/test run or a large-context model
  call, which argues for excluding in-flight tool calls with their own timeout from the stall clock.
- Combine a long window (sustained lack of durable progress) with a short window (current repetition/alternation) so the
  watchdog both catches real stalls and clears quickly once progress resumes, per the multiwindow pattern.
- A plausible default policy derived from the cited numbers (a design suggestion, not a sourced threshold): heartbeat or
  trace event every <=30 s; liveness failure after 3 consecutive misses; "stalled" condition after ~10 min without a durable
  progress signal (cf. Kubernetes 600 s, CircleCI 10 min, Airflow task heartbeat 300 s and queued 600 s); loop detection at
  3 identical errors (nudge) / 4 identical action-observation pairs (stuck) / 6 alternations; hard wall-clock and cost caps
  set per task (cf. SWE-agent $3, GitHub Actions 360 min, GitLab 60 min); report the condition and let policy decide
  restart vs escalation.

### Gaps
- Could not retrieve the SRE Workbook's exact text on the "incrementing alert duration" (`for`-clause) approach and its
  stated recall/reset-time drawbacks; reported here only via secondary summaries.
- The SRE Book chapter "Monitoring Distributed Systems" (symptoms vs causes, paging only on actionable conditions) was
  unreachable from this environment and is not cited.
- Nagios soft/hard state documentation (`max_check_attempts`) was unreachable; no quantitative false-positive rates for
  agent stall detectors were found in any source.
