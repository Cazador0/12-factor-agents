# Synthesis: R3 Guarded autonomous

**Spec ID**: SPEC-203 | **Delivery step**: 2 (Synthesize) | **Created**: 2026-10-22

This document collects what R3 depends on, what was decided, what is still open, and where the earlier release
plans need alignment. Citations use these keys:

- **[R §x]**: `skill-lab/docs/research/engineering-team-report.md`, section heading x.
- **[S x]**: `skill-lab/docs/research/SOURCES.md`, section x.
- **[C §n]**: `skill-lab/docs/CONVENTIONS.md`, section n.
- **[RM]**: `skill-lab/specs/200-release-roadmap/spec.md`.
- **[R1 x]**, **[R2 x]**: `skill-lab/specs/201-release-shadow/` and `skill-lab/specs/202-release-agent-implementation/`
  (spec, synthesis, plan, or release-plan), section or requirement x, as written on 2026-10-22.
- **[K name]**: the canonical contract `skill-lab/contracts/schemas/<name>.v1.schema.json`, as written on 2026-10-22.
- **[U]**: the user's decisions for this build, as relayed in the planning instructions (for example the Gitea merge
  call shape and the demotion rule).

A claim with none of these keys is a design inference, and the text says so. A fact R3 needs that no source verifies is
listed in §6 as "to verify", with the task that verifies it. Nothing in this release depends on an unverified fact
without a fail-closed default.

## 1. Findings

### 1.1 What the report asks of this autonomy level

- **F-1** Guarded autonomous mode: "low-risk PRs automatically merge when protected-branch, CI, Review, freshness, and
  dependency gates all pass. Medium/high-risk work still requires human approval." [R §Progressive autonomy]. The
  roadmap row adds event-driven dispatch and lease recovery, and keeps "High- and critical-risk merges, any change to
  policy, CI, agent permissions, or the gates themselves" human [RM Releases].
- **F-2** The risk table lists Medium as "Review + complete CI" [R §Safe autonomous merge], while the progressive
  autonomy text says medium "still requires human approval" at this level. The user decided "AUTO_MERGE only for low
  risk" [U]. R3 follows the progressive-autonomy text and the user: low only (D-2).
- **F-3** Safe autonomous merge rests on Gitea's protected-branch controls: no direct or force push, no admin bypass,
  required approvals, block on requested changes, dismiss or ignore stale approvals, block on outstanding review
  requests, require an up-to-date branch, required status checks, protected file patterns. "Gitea's PR API supports
  merge operations including the ability to schedule merging when checks succeed, so the orchestration system can
  request auto-merge without bypassing the repository's gates." "Force-merge tool for agents: NOT EXPOSED"
  [R §Safe autonomous merge]. The Lead "should not manually 'force merge.' Instead, it selects the applicable merge
  policy, while Gitea mechanically decides whether all required conditions are satisfied" [R §Lead contract].
- **F-4** The invariant: "Agents may operate autonomously inside the rules; they may not autonomously weaken the rules
  that define their authority." Changes to "the orchestrator, Gitea MCP server, CI policy, agent permissions, branch
  protection, secret-handling logic, and the Review agent's own gates" are not self-authorized [R §Safe autonomous
  merge].
- **F-5** The control plane: "Webhook Gateway → verify authenticity → deduplicate delivery → normalize event → State
  Machine / Scheduler (dependency graph, leases, retries, risk policy, role permissions, dispatch decisions)"
  [R §Gitea as the real-time engineering control plane]. Gitea "provides delivery/event metadata and signature
  verification; its documentation describes HMAC-SHA256 verification of webhook bodies" [R §Event-driven
  communication].
- **F-6** The event list (`issue.created`, `issue.assigned`, `issue.dependency_resolved`, `pull_request.opened`,
  `pull_request.synchronized`, `review.approved`, `review.changes_requested`, `check.success`, `check.failure`,
  `pull_request.merged`) and the normalized event shape with `blocking` and `next_action` [R §Event-driven
  communication]. "Webhooks communicate state changes; unstructured agent-to-agent chat does not define project
  state" [R §Final recommended operating doctrine].
- **F-7** "The orchestrator should be deterministic even though the agents are probabilistic", with the `next_action`
  function (`WAIT`, `DISPATCH_PSE`, `MOVE_TO_REVIEW`, `RETURN_TO_PSE`, `EVALUATE_MERGE_POLICY`,
  `COMPLETE_AND_UNLOCK_DEPENDENCIES`, `NOOP`). "LLM decides what it believes should happen. Policy code decides what
  it is allowed to make happen. Gitea enforces the final repository rules." [R §Orchestrator state model]
- **F-8** The Lead loop includes "Acquire orchestration lease", "Observe PR / CI / Review events", "Authorize
  policy-mediated merge", and "Close/move issue and unlock descendants" [R §Lead contract].
- **F-9** Leases: "A lease should have a TTL and heartbeat, but expiry must not automatically imply that another PSE
  may blindly continue in the same branch. Recovery first checks the branch, current commits, PR, and last
  checkpoint." [R §Claiming work safely]
- **F-10** Write sets: overlapping `expected_write_domains` are serialized unless deliberately separable
  [R §Protecting against cross-agent conflicts]. Parallel subagents suit read-heavy work; concurrent writes need care
  [R §Executive architecture].
- **F-11** Core metrics: cycle time, accepted issues, first-pass approval rate, escaped defects, revert/rollback rate,
  flaky-test rate, requirements changed after implementation began, average convergence passes, duplicate-work
  incidents, merge-conflict rate, stale-retrieval rate, resume/recovery success rate, tool-call failure rate,
  incorrect-action/block rate, cost per accepted issue, escalations per accepted issue, unauthorized-action attempts
  blocked. "The target is not maximum autonomy. It is higher accepted throughput without worsening escaped defects,
  security incidents, reverts, or human recovery cost." [R §Core metrics]
- **F-12** "Do not begin with unrestricted autonomous merge. Promote autonomy only after the same workflow
  demonstrates reliability." [R §Progressive autonomy]
- **F-13** Agentic-framework verification must test, for each capability: intent preservation, tool correctness
  ("verify resulting external state rather than assuming a successful tool response means the entire objective
  succeeded"), permission containment ("Can nested subagents acquire more authority than their parent?"),
  prompt-injection resilience, long-horizon recovery, idempotency, ordering ("What happens if `PR_UPDATED` arrives
  before a delayed `REVIEW_APPROVED` webhook?"), concurrency, RAG grounding, and failure recovery ("CI is
  unavailable, Gitea returns a transient error, the sandbox dies, a lease expires, or a dependency changes midway").
  "Every recurring agent mistake becomes a regression fixture, then an evaluation, then, where possible, a mechanical
  constraint." [R §Agentic-framework verification]
- **F-14** Board owners: Ready to Merge and Done are owned by System; Ready to Merge is entered when "Review and policy
  gates pass" [R §Kanban state machine].
- **F-15** Session-start hooks should "fetch current issue/spec/branch/lease" and "verify working tree and base SHA";
  before a consequential write "validate role authority, validate lease, validate expected project state"
  [R §Session checkpoint].
- **F-16** "Not run must never silently mean passed", and applicability must be explicit [R §Merge evidence gate].
- **F-17** "RAG should be a retrieval accelerator, not a new source of truth", and a result is stale when its
  `commit_sha` cannot describe the current branch [R §Derived retrieval index]. The skills ship no retrieval index;
  the analogue they do have is evidence (verdicts, checkpoints, check runs) bound to commits.
- **F-18** The long-horizon and self-improving modes come after guarded autonomy [R §Progressive autonomy]; they are
  not in this roadmap.

### 1.2 Verified platform facts

- **F-19** Gitea 28.2.0 is current (2026-10-18). Webhook headers are `X-Gitea-Event`, `X-Gitea-Delivery`, and
  `X-Gitea-Signature` (hex HMAC-SHA256 of the raw body). Project-column coverage varies, so the board uses exclusive
  scoped `state/<name>` labels [S Gitea].
- **F-20** The merge call the user specified: `POST /repos/{owner}/{repo}/pulls/{index}/merge` with
  `merge_when_checks_succeed` and `head_commit_id`, never a force-merge [U]. The report confirms the scheduling
  capability [R §Safe autonomous merge]. The other body fields (the merge style key, `force_merge`,
  `delete_branch_after_merge`), the response for a scheduled versus an immediate merge, and the cancel endpoint are
  **not** in SOURCES.md (V-1, V-2).
- **F-21** Zed: skill scripts must never write inside their own skill folder; project skills load only from trusted
  worktrees; `tool_permissions` decides allow, confirm, or deny with regex patterns, and `always_deny` wins
  [S Zed Agent skills]. Nothing in SOURCES.md documents a headless way to start a Zed agent thread, so Zed sessions are
  human-started (D-18).
- **F-22** Ollama Cloud does not support structured outputs; cloud models run at maximum context; Zed's default
  `num_ctx` is 4096 [S Ollama with Zed]. The gateway and the merge gate use no model.
- **F-23** Jev: one narrow judgment per question; a noul near 0.5 is uncertain; "typed output guarantees the interface,
  not truth" [S TypeSafe AI "Jev"]. Uncertain [0.35, threshold) counts as fail and is flagged `needs_human` [C §5].
- **F-24** Codex invokes `$name` from `.agents/skills`; Claude Code invokes `/name` from `.claude/skills`
  [S Codex and Claude Code skills].
- **F-25** Spec Kit `converge` is append-only and leaves `tasks.md` byte-identical when nothing remains; task lines
  follow `- [ ] T001 [P] [US1] Description` with optional `(depends on …)` [S Spec Kit].

### 1.3 Facts from the foundation contracts

- **F-26** [K merge-decision]: `decision` ∈ `AUTO_MERGE`, `HUMAN_APPROVAL_REQUIRED`, `BLOCKED`. The schema already
  forbids `AUTO_MERGE` unless `risk_class` is low **or medium**, every gate passes, and no policy path is touched, and
  it forces `BLOCKED` whenever any gate is `fail`. `head_commit` is optional.
- **F-27** [K normalized-event]: `signature_verified`, `duplicate`, `commit`, `blocking`, `next_action`; consumers must
  ignore events with `signature_verified: false` or `duplicate: true`.
- **F-28** [K lease]: `resource.type` includes `orchestration`; `status` includes `expired`; `version` increases on
  every change (CAS); "Expiry does not by itself let another session continue on the same branch."
- **F-29** [K session-checkpoint]: `predecessor_session`, `head_commit`, `next_action`, capped lists, no
  chain-of-thought. [K transition-decision]: `actor_role` includes `system`; `allowed` only with every precondition met.
- **F-30** [K review-verdict]: `reviewed_commit`; APPROVE has no blockers and no failed or unverified requirements.
  [K quality-gate]: `passed` only when every applicable category passed and `branch.current_with_base` holds.
- **F-31** `_skillkit.redact.SECRET_ENV_VARS` (working tree) lists `GITEA_TOKEN`, `TYPESAFE_API_KEY`, `JEV_API_KEY`,
  `OLLAMA_API_KEY`, `GITHUB_TOKEN`, `GH_TOKEN`, `ANTHROPIC_API_KEY`, `OPENAI_API_KEY`, but **not**
  `GITEA_WEBHOOK_SECRET`, which R1's normalizer reads [R1 FR-025].

### 1.4 Facts from SPEC-201 (R1) and SPEC-202 (R2)

- **F-32** R1 ships 34 catalog actions, including the 7 `guarded-autonomous` ones R3 enables:
  `git.push.force_own_branch`, `gitea.issue.close`, `gitea.pr.review.dismiss`, `gitea.pr.merge_when_checks_succeed`,
  `lease.takeover`, `dispatch.session.start`, `events.gateway.serve`; and 5 `human-only` ones: `policy.change`,
  `git.push.protected`, `gitea.pr.merge`, `gitea.branch_protection.update`, `gitea.webhook.create`. "Later releases
  may add action ids (bumping `catalog_version`) but may not lower an existing minimum level without a human-merged
  ADR." [R1 §Autonomy policy]
- **F-33** R1 D-4 makes overrides restrict-only and says "An expiry (auto-demotion) is useful but belongs with R3's
  promotion and demotion machinery." R1 FR-005: no environment variable, flag, `--state-dir` content, or skill-local
  file may influence the effective level; `policy.py` never reads `os.environ`. The policy is loaded once per process.
- **F-34** R1 adds `uncapped_decision` and `autonomy_level` to `merge-decision` "so R3 promotion is evidence-based"
  (D-24), and R1's normalizer already verifies HMAC with `compare_digest` and keeps a seen set; `serve` exits 4 below
  `guarded-autonomous` [R1 FR-025, FR-026].
- **F-35** R2 verifies the policy file against `origin/<base>` (D-21); uses per-role Gitea identities (Lead and PSE may
  share one, Review must differ, D-3); keeps lease authority local to one host (D-7); has an endpoint table with **no
  merge row** (D-2); moves the double's engine to `_skillkit.gitea_memory` (D-23); adds receipts, markers, and the
  shared applier (D-5, D-6, D-14).
- **F-36** R2's `review-post.v1` records the posted verdict, its independence and freshness proof, and
  `reviewer.mode`; `branch-protection-audit.v1` evaluates BP-01..BP-12, with BP-09 ("auto-merge allowed when policy
  passes") informational in R2 and reserved for R3 [R2 §Release gates].
- **F-37** R2's `complete_issue.py` sets `state/done` and reports `CLOSE_PENDING`, because closing is R3 [R2 FR-029].
  R2's `delivery-record.v1` records the merge decision at handoff [R2 FR-034].
- **F-38** R2's `human-signoff.v1` has `subject.kind` `autonomy-level-change` "for R3 level promotion"; "No skill script
  creates a sign-off" [R2 FR-035, D-16].
- **F-39** R2's exit states: merged, then complete. After the cross-release consistency pass, R2 D-20 applies SPEC-201's
  sequencing rule to R3: R3 step 5 may start at R2's independent `APPROVE` with every merge-stage gate passing, unless an
  R2 live gate ran and failed; R3 complete and any promotion need R2 complete [R2 D-20, release-plan X-5].
- **F-40** R1's and R2's live thresholds: per skill ≤ 1 failed agentic case (`bench.agentic.failed`), guardrail 1.0, per
  skill ≤ 1 misrouted trigger case (`bench.trigger.failed`), catalog trigger ≥ 0.90, 0 errors or skips [R1 §Release gates;
  R2 §Release gates]. Their first drafts used the rates 0.67 and 0.83; X-2 below is why they now use counts.

## 2. Decisions

| ID | Decision | Rationale | Alternatives rejected |
|---|---|---|---|
| D-1 | R3 raises `SUPPORTED_MAX_LEVEL` to `guarded-autonomous`, enables the 7 guarded actions, and adds exactly **2** actions (catalog 1.1.0, 36 actions): `autonomy.demote` (min `shadow`, scope `policy`, risk low) and `gitea.pr.merge_schedule.cancel` (min `agent-implementation`, scope `forge`, risk low). No existing level changes | F-32 allows additions. Demotion only lowers authority, so it must work at every level. Cancelling a merge schedule must keep working after a demotion to `agent-implementation`, so it cannot be a guarded action. ADR-0009 names `merge_when_checks_succeed` as the only merge-related write; ADR-0301 amends it to add this one restrictive cancel row | Reusing `policy.change` for demotion (it is `human-only` and would make automatic demotion impossible); making cancellation guarded (a demoted project could not withdraw its own schedules) |
| D-2 | `AUTO_MERGE` only for **low** risk. Medium, high, and critical are `HUMAN_APPROVAL_REQUIRED` at every level. The ceiling is a code constant, not configurable. `merge-decision.v1` keeps its "low or medium" schema clause | F-1, F-2, [U]. Narrowing the schema enum is a breaking change by the contracts README (v2 for every consumer); the code and an exhaustive test enforce the stricter rule, and the schema stays a backstop against high and critical | A `merge-decision.v2`; a policy-file setting for the auto-merge risk ceiling (a human-merged config edit would then re-level authority without an ADR) |
| D-3 | **All-gates rule.** At `guarded-autonomous` the decision evaluates 13 evidence gates (plan.md §Merge decision): `pr-open`, `review-approved-current-head`, `quality-gate`, `no-changes-requested`, `no-outstanding-review-requests`, `ci-required-success`, `up-to-date-with-base`, `mergeable`, `dependencies-closed`, `branch-protection-compliant`, `merge-identity`, `intent-chain`, `evidence-head`. Any `fail` or `not_run` → `BLOCKED`. Then 6 caps (`CAPPED_BY_AUTONOMY_LEVEL`, `AUTONOMY_DEMOTED`, `RISK_NOT_LOW`, `POLICY_PATHS_TOUCHED`, `FACTORY_REPOSITORY`, `NOT_AGENT_PR`) → `HUMAN_APPROVAL_REQUIRED`. Otherwise `AUTO_MERGE`. The decision function is pure and tested exhaustively | F-1, F-3, F-16, [U] list of gates. A gate that cannot be evaluated is a fail, never a pass. Caps are not gates, because a capped decision with all gates passing is `HUMAN_APPROVAL_REQUIRED`, and [K merge-decision] forces `BLOCKED` on any failed gate (F-26). 2^13 × 4 risk classes = 32,768 combinations is small enough to test every one | Sampling the matrix; treating `not_run` as neutral; trusting Gitea's merge button state alone |
| D-4 | The only merge call is `POST /repos/{owner}/{repo}/pulls/{index}/merge` with `merge_when_checks_succeed: true`, `head_commit_id` = the head the decision was computed on, the merge style from the base-branch policy (default `merge`), and `delete_branch_after_merge: false`. The endpoint row's body validator refuses any other key, so `force_merge` cannot be sent; `merge-execution.v1` has no such property. `merge_plan.py --apply` recomputes the decision from live state in the same process immediately before the call | F-3, F-20, [U]. Recomputing in-process closes the decision-to-call window to milliseconds, and `head_commit_id` plus branch protection close the rest. Keeping the branch preserves the commits that revert attribution and post-merge audits need | An immediate merge row (no CI wait; contradicts [U]); trusting a decision file produced earlier |
| D-5 | **Merge schedule lifecycle.** A schedule is cancelled (`DELETE …/pulls/{index}/merge`, V-2) on a new head, changes requested, a check failure, PR close, demotion, or when it is older than `limits.merge_schedule_ttl_minutes` (default 30, range 5–60). TTL expiry also posts a marked comment and escalates to a human | RK-2: Gitea executes a schedule on its own, after our evidence may be stale. 30 minutes bounds that window; it is three times SPEC-201's 10-minute CI budget for a full suite (an assumption for target projects, Q-3), so a healthy re-run finishes inside it, and an unhealthy one becomes a human decision instead of a silent late merge | Never cancelling (relies only on Gitea's head binding, unverified, V-6); an unbounded schedule |
| D-6 | The merge is scheduled by the **system** identity: `identities.system` in `.skill-gitea.json` (optional, default the Lead login). At `guarded-autonomous` that login must not be a repository admin (`permissions.admin` false; unknown → refuse), and must differ from the PR author and every commit author and committer | Admins can bypass protections in some Gitea configurations (BP-03 exists for that reason); an author never triggers its own merge. R2 lets Lead and PSE share one login (F-35), so such projects must configure a distinct system login before promotion | Merging as the Review identity (concentrates approval and merge authority); merging as the PSE |
| D-7 | **Caps that no gate can lift.** `FACTORY_REPOSITORY` when the repository is `Cazador0/skill-factory` or the base tree contains `skill-lab/shared/_skillkit/policy.py`; `NOT_AGENT_PR` unless the head branch matches `^agent/pse/[0-9]+-`. The skills also stay Gitea-only (R2 D-4), so the GitHub-hosted factory has no merge path at all | [RM] non-goal: "Agents merging the skill-factory repository's own PRs." Structural detection covers forks and renames. Only agent PRs carry the evidence chain the gates read | A repository allowlist in config (a config edit could remove it) |
| D-8 | **Risk** = max(path classification, issue-contract risk, `risk/*` labels on the PR and the linked issue). Paths: built-in critical patterns (R1's policy paths plus R3's: the merge gate, gateway, kanban, lease skills, vendored `_skillkit`, schemas, `.skill-autonomy/**`, `.agents/**`, `.claude/**`, secrets patterns), built-in high patterns (auth, permissions, migrations, deployment, dependency manifests, `**/SKILL.md`, `AGENTS.md`, `CLAUDE.md`), then the low allowlist (default `docs/**` and Markdown not matched above), else medium. More than 400 changed lines forces at least medium. A base-branch policy may add low paths only where no built-in critical or high pattern matches. PR text never lowers risk | [R §Safe autonomous merge] examples; F-4. 400 lines at about 10 tokens per line is about 4 k tokens, an eighth of the 32 k context that bounds local models (ADR-0003), so one review round can hold the whole diff plus the spec | Classifying by PR description (prompt-injectable); a size-free rule |
| D-9 | **Gateway.** stdlib HTTP server, loopback by default; a non-loopback bind requires TLS (`--tls-cert`, `--tls-key`). Pipeline: method and path → `Content-Length` ≤ 5 MiB → headers → HMAC over the raw bytes (`hmac.compare_digest`) **before** JSON parsing → strict parse → dedupe by `X-Gitea-Delivery` under a file lock → normalize → durable `event-record.v1` write → `202`. One worker drains the inbox in order. More than 1,000 unprocessed records → `503` | F-5, F-19, F-27. Verifying before parsing keeps unauthenticated bytes away from the parser. Acknowledging only after the write means an acknowledged event is never lost. 5 MiB is an assumption sized for large push payloads, and bounds memory per request. The 1,000-record bound is about 3 hours of backlog at one event every 10 s; past that, backpressure is safer than unbounded growth, and the reconcile sweep repairs anything Gitea gives up on | Parsing first; processing inside the request (Gitea's delivery timeout is unverified, V-7); multiple workers (reordering) |
| D-10 | **Level-triggered processing with an ordering guard.** Events are hints that name a resource. Every handler re-reads live Gitea state and decides from it. The guard classifies each event `in_order`, `stale_commit` (its commit is not the PR head), `superseded` (older than the resource's high-water mark and adding nothing), `duplicate`, or `unverified`. For `stale_commit` and `superseded`, progress routes (merge evaluation, forward transitions) are skipped; cancel and re-evaluate routes still run. A reconcile tick every 300 s re-evaluates all open agent work | F-13 ordering. Deciding from live state makes the final outcome independent of delivery order; the guard keeps a stale fact (an approval of an old head) from triggering progress. 300 s bounds the delay a lost webhook can cause, at a cost of one list call per open issue and PR per tick | Edge-triggered state from payloads (order-dependent); vector clocks (Gitea provides none) |
| D-11 | **Routing table in code.** `_skillkit.eventloop.ROUTES` maps each normalized event type to an ordered list of handlers; each handler is a fixed (skill, script, argument template). The processor runs the sibling skill's script as a subprocess with list arguments built only from schema-typed fields (issue and PR numbers, SHAs, enum values), with a 120 s timeout, and records every handler envelope's digest, exit code, and error code. An in-process mode exists for tests only | Each script keeps its own policy, identity, and lease checks, so routing grants no authority. A code constant is vendored and drift-checked like R1's catalog (R1 D-5). 120 s is the network-step bound below (D-17) | A data-file routing table (a second policy surface to protect); importing other skills' modules (skills are self-contained, [C §1]) |
| D-12 | **One control-plane identity per process.** The gateway runs with the system token and performs only control-plane actions (system transitions, dispatch and assignment, merge scheduling and cancellation, issue close, demotion). Role work (PSE remediation and rebase, Review re-review and dismissal) is written as `session-dispatch.v1` and started by **role runners** that run with that role's token | R2 D-3: one `GITEA_TOKEN` per session; a gateway holding several tokens would concentrate authority. Dismissing a Review approval as the Review identity keeps review state attributable | A multi-token gateway; new per-role environment variable names (more secrets) |
| D-13 | `kanban-state-machine` lets `system` apply **observed-fact transitions** only: `MOVE_TO_REVIEW` (PR open and CI success), `RETURN_TO_PSE` (changes requested or CI failure), `EVALUATE_MERGE_POLICY` → `READY_TO_MERGE` (all merge gates pass), `COMPLETE_AND_UNLOCK_DEPENDENCIES` (merged), `BLOCK` and `UNBLOCK` (a dependency reopened, a recovery escalated, a rebase conflict, exhausted dispatch attempts, or the fact cleared), and `REQUEUE` (a `release_no_work` recovery). Each is recomputed from live state and recorded facts at apply time (R2 PLAN_STALE rule), and these are the only board writes R3 adds. This extends R2 FR-025's `actor_role == required_role` rule | F-7, F-14, [R2 D-13]: the deterministic engine decides; the board records facts Gitea already shows. Role-owned *work* is never performed by `system` | Letting `system` apply any transition; keeping events out of the board |
| D-14 | **Demotion latch.** `autonomy_guard.py --apply` (action `autonomy.demote`) writes one `autonomy-demotion.v1` file per demotion under `<main worktree>/.skill-state/autonomy/demotions/`, located through `git rev-parse --git-common-dir` and never through `--state-dir`. `policy.load` clamps to `agent-implementation` while any record is not cleared by the base-branch promotion block, and also when a record is unreadable or the directory is not a real directory. The guard then cancels every system-scheduled merge and mirrors the demotion on the Gitea autonomy tracking issue (marked comment plus label `autonomy/demoted`). The merge gate re-checks that label and open `incident/*` issues on every decision | F-11 target metrics; [U] automatic demotion. A fixed location that worktrees share closes the "run from a fresh worktree or state dir" escape; fail-closed reading closes the "corrupt the file" escape; the forge mirror closes the "delete the file" escape for merges, because agents have no action that removes a label from the tracking issue or deletes a comment | Editing `.skill-policy.json` automatically (`policy.change` is `human-only`); a latch under `--state-dir` (escapable by flag); a Gitea-only latch (`policy.load` cannot call the network) |
| D-15 | **Promotion is human-only and base-branch bound.** The effective level is `guarded-autonomous` only when the base copy of `.skill-policy.json` declares it **and** carries `promotion{signoff_path, signoff_digest, scorecard_path, scorecard_digest, clears_demotions[]}` whose files exist on the base ref under `.skill-autonomy/`, match their digests, and validate: a `human-signoff.v1` with `subject.kind: autonomy-level-change` from `agent-implementation` to `guarded-autonomous`, decision `approve`, signed within 7 days after the scorecard, binding the scorecard digest; and an `autonomy-scorecard.v1` with `promotion.eligible: true` whose criteria are consistent with the code's thresholds. At this level `.skill-gitea.json` must also match its base copy. Otherwise `PROMOTION_UNVERIFIED` and `agent-implementation` | F-12, [RM] (raising the level is critical risk), F-38 (sign-offs come from the lab, not from skill scripts). The base branch changes only through a human merge (R2 D-21), so no agent path can satisfy this; the sign-off adds the human's explicit attestation of the evidence | Auto-promotion on metrics; a sign-off without a scorecard; a promotion that ignores outstanding demotions |
| D-16 | **Scorecard.** `autonomy-scorecard.v1` reports the report's 17 metrics plus 4 calibration and incident metrics, each with an explicit applicability and source coverage. Decision records are written at **every** level from R3 install onward (`merge_decision.py --record`), so the human-merged PRs at `agent-implementation` become the calibration sample. Promotion criteria P-1..P-8 (spec.md §Autonomy policy) gate eligibility; demotion triggers D-T1..D-T5 are counted since the active promotion. Thresholds are code constants in `_skillkit.autonomy`, a critical path | F-11, F-12, R1 D-24. Code constants travel with the vendored module and are drift-checked (R1 D-5). `stale-retrieval rate` is explicitly not applicable (F-17) | Thresholds in a data file; gating on cost, which no runtime reports reliably (Q-9) |
| D-17 | **Lease recovery.** Constants: TTL 1,800 s, heartbeat at most every TTL/3, takeover grace 600 s. Every delivery step is bounded: checks by R1's 600 s timeout, network steps by 120 s. `lease.py recover` applies rules R-0..R-9 (plan.md §Recovery rules) to an inspection of branch, commits and trailers, push receipts, PR, checkpoint, worktree, and mirror, and emits `lease-recovery.v1` with `blind_continuation: false`. Only `resume_from_checkpoint` and `resume_with_reverification` permit a takeover, which only a successor session holding a recovery record no older than 300 s may perform (CAS on the lease version) | F-9, F-28. A step started under the old lease finishes within 600 s, so after expiry plus grace no write from the old session can still be in flight; its next step fails R2's lease check. Push receipts (R2 D-6) show which commits were pushed under the lease. A missing checkpoint with commits present goes to a human, because intent cannot be reconstructed safely at this level | Takeover on expiry; adopting a dirty worktree; trusting commit timestamps (author-controlled) |
| D-18 | **Dispatch.** `dispatch_recommend.py --on-event` runs R2's claiming sequence for newly unblocked issues, up to `limits.max_concurrent_pse_sessions` (default 1, maximum 2) and `limits.max_dispatches_per_day` (default 10, maximum 20), and at most 3 attempts per issue in 24 h. `dispatch_session.py write` records `session-dispatch.v1` plus a rendered prompt; `dispatch_session.py run --role <r>` (a runner with that role's token) starts sessions: runner `claude-cli` (flags verified at T004, V-10), `stub` (tests), or none (a human opens the prompt in Zed). A Codex runner stays disabled until `codex exec` is verified | F-10, F-21. One concurrent PSE session matches R2's single-host lease authority (R2 D-7); 2 is the smallest parallelism that exercises the write-set guard, and more belongs to the long-horizon mode. 10 dispatches a day bounds cost and human recovery load while cost per issue is unmeasured (Q-3, Q-9). 3 attempts separates a transient failure from a systematic one | Unlimited dispatch; a gateway that spawns sessions with its own token |
| D-19 | **Authority narrowing.** `_skillkit.authority.narrow(parent, child)` refuses (`AUTHORITY_ESCALATION`, exit 4) unless child level ≤ parent level, the child role is one the parent role may dispatch (system and lead → pse or review; review → read-only review helpers; pse → none, matching ADR-0008's PSE profile without `spawn_agent`, because a PSE child would be a second writer on the leased branch), child actions ⊆ parent actions ∩ the child role's actions, and child write domains ⊆ the parent's lease domains | F-13 nested authority. Structurally, a nested subagent inherits its parent's token, lease, and policy and can raise none of them; the explicit check covers dispatch records, which are the only place a child's authority is written down | Trusting prompts to limit subagents |
| D-20 | **Stale approvals.** On a new head, `invalidate.py` always marks verdicts for other commits stale locally; a Review-identity session dismisses stale Review approvals (`gitea.pr.review.dismiss`, V-3). BP-06 (dismiss or ignore stale approvals) is required at this level, and the merge gate requires an approval whose `commit_id` is the head regardless | F-3, F-13 ordering. Three independent layers; none depends on the dismissal succeeding | Relying on BP-06 alone; dismissing as `system` (misattributes review state) |
| D-21 | **Rebase.** `--step rebase` rebases the leased worktree onto `origin/<base>`; on conflict it runs `git rebase --abort`, exits 1 `REBASE_CONFLICT`, and escalates to a human. `--step push --force-with-lease` pushes only the leased branch with `--force-with-lease=refs/heads/B:<recorded pre-rebase remote SHA>`, only after the checks and evidence were rebuilt for the new head | [U] partition: "still human for conflicts"; F-3 (force-push denied on protected branches, not on the agent's own branch). The expected SHA makes the push fail if anyone else moved the branch | Gitea's update-branch API (unverified, V-4; rebuilds the head server-side before local evidence exists); merging the base into the branch (changes the history Review saw) |
| D-22 | `speckit-development` hands off and never merges: at `guarded-autonomous` its handoff records `merge_handoff{decision, decision_digest, uncapped_decision, mode}` (spec.md §Contracts) and sets `next_action: merge_gate.event_loop` when the decision (not only the uncapped one) is `AUTO_MERGE`, otherwise a human merge | Independence: the author side never triggers its own merge; R2 FR-034 stays true | Letting the delivery skill call `merge_plan.py` |
| D-23 | **AFV suites are release gates.** Ten suites, tagged `afv:<suite>` (hyphenated, because benchmark-case tags have no `_`, [R1 FR-010]), with minimums of 45 deterministic and 14 agentic cases, plus integration tests and a deterministic soak test (≥ 40 issues, enumerated faults). `skill-lab afv run` emits `afv-report.v1` | F-13: every dimension the report lists, with RAG grounding mapped to evidence grounding (F-17). Enumerated faults keep the soak deterministic ([C §3] "no randomness") | Sampling with random seeds; a single "agent safety" score |
| D-24 | **Live gates.** Per-skill agentic **failures ≤ 1** (`bench.agentic.failed`) and trigger **misroutes ≤ 1** (`bench.trigger.failed`, SPEC-104's name) (counts, X-2, now shared with SPEC-201 and SPEC-202), guardrail 1.0, catalog trigger ≥ 0.90, AFV agentic ≥ 0.90 over ≥ 14 cases, 0 errors or skips, and all of these on **3 consecutive** complete eligible `ollama-cloud` runs (R2 D-17 eligibility) for R3 complete. Live Gitea auto-merge per host additionally needs a passing `merge` smoke stage (RT-02) | [U] "reliable" means agentic and trigger gates pass on 3 consecutive live runs. R3 is the first release where a model's output (Review's verdict) can lead to a merge without a human, so one run is not enough. 13/14 = 0.929 passes and 12/14 = 0.857 fails, so the AFV bar tolerates exactly one judgment miss | Rate thresholds that round against small case counts (X-2); 1 run |
| D-25 | Two exit states, as in R1 and R2. No project may be promoted before R3 is complete (P-8 reads the factory's complete-stage gate report) | [C §9]; F-39 | Promoting on merged, live-pending code |
| D-26 | ADR numbers 0301–0309 | R1 and R2 reserved this block (R2 D-25) | — |
| D-27 | The gateway is an operator service, not an agent tool call: a human starts `normalize.py serve`; the runtime configs deny it in agent terminals; SKILL.md says so | A server that never returns would block an agent turn, and a model should not decide when the control plane runs | Starting the gateway from a Zed thread |
| D-28 | The Gitea test double gains merge-when-checks-succeed semantics (immediate merge when checks and protections pass, otherwise a schedule; no merge when the head differs from `head_commit_id`; cancel; dismissal; close) and signed webhook emission with delay, reorder, duplicate, drop, and tamper faults | Offline first [U]; the double is the oracle for every R3 integration test. Where live behaviour is unverified, the double implements the conservative reading and RT-02 checks the real one | Testing only against a live Gitea |

## 3. Refinements to the capability partition (with reasons)

The user's partition and its level semantics are kept. These refinements fill gaps it leaves open:

1. **merge-policy-gate** also owns the autonomy scorecard and the demotion guard. It is the one gate auto-merge
   passes through, so it must consult demotion state on every decision, and keeping the guard beside it means one
   skill holds the whole promotion and demotion logic. The latch check itself lives in `_skillkit.policy`, so it
   applies to every guarded action, not only merges.
2. **merge-policy-gate** records its decisions at every level (`--record`, `state.write.local`). That turns R1's
   `uncapped_decision` (F-34) into the calibration sample promotion criterion P-1 counts.
3. **gitea-event-normalizer** gets `ingest`, `process`, and `reconcile` besides `serve`, so the same code paths run
   offline from files (tests, replays) and live from HTTP.
4. **lead-architect** owns session dispatch (`dispatch_session.py`) and closes issues (`gitea.issue.close`), because
   the report gives the Lead assignment and "close/move issue and unlock descendants" (F-8).
5. **review-verifier** splits invalidation into a local part (any role may mark its own records stale) and a forge
   part that only a Review-identity session performs (D-12, D-20).
6. **work-lease** owns the orchestration lease that keeps a second gateway from processing the same repository
   (F-8; [K lease] `orchestration`).
7. **speckit-gitea-sync** writes a drift state file that dispatch reads, so an issue whose task drifted is not
   dispatched until a human or the Lead resolves the drift.
8. **The policy machinery** (not a skill) gains promotion verification, the demotion latch, and authority narrowing.

## 4. Trade-offs

| Trade-off | Chosen | Cost accepted |
|---|---|---|
| Throughput vs. safety at first promotion | Low risk only; 1 concurrent PSE; 10 dispatches a day | Most real work still waits for a human merge |
| Evidence before promotion vs. time to autonomy | ≥ 30 calibration PRs, a 7-day observation lag, and R3 complete (P-1, P-2, P-8) | Weeks of `agent-implementation` use before the first promotion |
| Strict demotion vs. false alarms | Any one escaped defect, revert, containment breach, gate-integrity violation, or lease violation demotes | A mislabelled issue demotes the project until a human re-promotes (safe direction, RK-14) |
| Level-triggered robustness vs. API load | Re-read live state for every event plus a 300 s sweep | More Gitea reads than an edge-triggered design |
| One token per process vs. latency | Role work goes through role runners | A PSE fix waits for the PSE runner (or a human in Zed) |
| Exhaustive tests vs. CI time | 32,768-row decision matrix, ≤ 756 ordering schedules, 40-issue soak | A few extra minutes of CI per run |
| Code-constant thresholds vs. flexibility | Thresholds change only by a human-merged code change | Tuning needs a PR and an ADR |

## 5. Residual risks

| ID | Risk | Residual after mitigation | Owner |
|---|---|---|---|
| RK-1 | Gitea's merge-when-checks-succeed semantics differ from the double (fields, response codes, behaviour on a new push, whether a schedule obeys protection) | Low once V-1, V-2, V-6 and RT-02 pass; until then live auto-merge is refused per host | Lead |
| RK-2 | A schedule outlives its evidence between events | Bounded by cancel-on-event, the 30-minute TTL, `head_commit_id`, and BP-06/BP-07 | Lead |
| RK-3 | An agent deletes or edits the local latch, or runs from another clone | Merges: none, because the gate re-checks the Gitea mirror. Other guarded actions: until the next guard evaluation (≤ 300 s). R3 supports one control-plane clone per host (documented) | User |
| RK-4 | A human promotes after a superficial look | Policy code still requires an eligible scorecard consistent with code thresholds and a sign-off bound to it | User |
| RK-5 | Escaped defects need a label to be seen | Reverts are detected automatically; unattributed defect labels still demote; convention in the promotion runbook (Q-10) | User |
| RK-6 | The gateway is network-exposed | Loopback by default, TLS required otherwise, HMAC before parse, 5 MiB limit, bounded inbox; the Gitea webhook itself is created by a human (`human-only`) | User (Gitea admin) |
| RK-7 | Small models in dispatched sessions misbehave with more autonomy | Every write still goes through policy, lease, identity, and scope checks; refusals are counted (P-6); containment breaches demote | Review |
| RK-8 | A headless runner gets edit rights in the target repository | Off by default (Q-7); the runner's token is the role's own; commits are scope-checked by R2 | User |
| RK-9 | Cost per accepted issue is not measured | Report-only metric with `unavailable` status; budget caps D-18 | User |
| RK-10 | The network allowlist delays R3 complete | Merged, live-pending state; no promotion before complete | User |
| RK-11 | The R3 PR changes the policy clamp, the gates, and the gateway (critical) | Human merge; G-OFF-26 self-classification; reviewer checklist | Human |
| RK-12 | Prompt injection through webhook payloads, issue text, or commit messages | Handlers receive only typed fields; untrusted text is never routed, executed, or used to lower risk; AFV prompt-injection suite | Review |
| RK-13 | Clock and multi-host effects | Single host, as R2 D-7; lease expiry uses only the local clock | User |
| RK-14 | Hostile or mistaken incident labels cause a demotion (denial of autonomy) | Fails safe; a human re-promotes after review | User |
| RK-15 | Raw API calls with the system token bypass the scripts (for example a `curl` merge with `force_merge`) | The system identity is not an admin and BP-03 denies admin bypass; whether Gitea reserves `force_merge` for admins is verified (V-1, smoke M-6), not assumed; branch protection is the boundary; runtime deny rules are guardrails | User (Gitea admin) |

## 6. Facts to verify during execution (not assumed)

| ID | Fact needed | How and where it is verified | Blocks |
|---|---|---|---|
| V-1 | The merge body fields besides the two [U] names: the merge-style key and values (Gitea's form is expected to use `Do`), `force_merge`, `delete_branch_after_merge`, title and message fields; the response for an immediate merge versus a scheduled one; the status when `head_commit_id` differs from the head | T003 against the vendored Gitea 28.2.0 swagger from R2 T003; recorded in SOURCES.md and in the endpoint table | Live use only (the double follows the plan's table; RT-02 checks the real server) |
| V-2 | The cancel endpoint for a scheduled auto-merge (expected `DELETE /repos/{owner}/{repo}/pulls/{index}/merge`) | T003 | Live cancel; without it, D-5 falls back to escalation plus Gitea's own head binding |
| V-3 | Review dismissal (expected `POST /repos/{owner}/{repo}/pulls/{index}/reviews/{id}/dismissals`) and the permission it needs | T003; smoke stage `merge` step M-5 | Live dismissal only (D-20 has two other layers) |
| V-4 | Review fields `commit_id`, `stale`, `dismissed`, `official`; pull fields `merge_base`, `mergeable`, `merged`, `merge_commit_sha` or equivalent; requested reviewers and teams; the update-branch API | T003 | Live gate inputs (the double defines them) |
| V-5 | `permissions{admin, push, pull}` for the token user in `GET /repos/{owner}/{repo}` | T003 | Live merge identity check (unknown → refuse) |
| V-6 | Live schedule behaviour: does a schedule obey required approvals, requested changes, outdated-branch blocking, and required contexts; does it ever merge a head other than `head_commit_id`; what happens to it on a new push | Smoke stage `merge`, steps M-1..M-6, on the sandbox repository | RT-02 for each host |
| V-7 | Webhook delivery: timeout, retries, redelivery and its delivery ID, the event header names and payload shapes for reviews and commit status (consumed through R1's mapping), and whether `[webhook] ALLOWED_HOST_LIST` blocks loopback or private targets by default | T003 (Gitea docs); live gateway setup | Live gateway setup (Q-2) |
| V-8 | A commit-to-PR lookup (expected `GET /repos/{owner}/{repo}/commits/{sha}/pull`) | T003 | Revert attribution fallback only (the primary path uses R3's own merge records) |
| V-9 | The branch-protection field behind BP-09 (auto-merge allowed) and any repository-level auto-merge setting | T003; recorded in `skills/merge-policy-gate/assets/branch-policy-map.json` | Live audits (unknown → `fail` at this level) |
| V-10 | `claude -p` flags for a headless PSE or Review runner (permission mode, allowed tools, turn limit) and the usage or cost fields of `--output-format json`; whether `codex exec` exists and how it is sandboxed | T004 (`claude --help`, `codex --help`) | The `claude-cli` runner (Q-7) and the cost metric |
| V-11 | Issue listing filters (`labels`, `state`, `since`) | T003 | Incident and demotion-mirror queries (fallback: page through all issues) |

## 7. Open questions for the user

Consolidated, deduplicated, and prioritised across all three releases in
[SPEC-200 open-questions.md](../200-release-roadmap/open-questions.md). Mapping: Q-1 → OQ-08, Q-2 → OQ-06, Q-3 → OQ-13,
Q-4 → OQ-05, Q-5 → OQ-17, Q-6 → OQ-18, Q-7 → OQ-09, Q-8 → OQ-19, Q-9 → OQ-04, Q-10 → OQ-18, Q-11 → OQ-08.

| ID | Question | Default if unanswered | Blocks |
|---|---|---|---|
| Q-1 | Promotion thresholds: ≥ 30 calibration PRs whose recorded uncapped decision was `AUTO_MERGE` (P-1), 0 escaped defects and 0 reverts with a 7-day observation lag (P-2), ≤ 1 human disagreement (P-3), first-pass approval ≥ 0.70 (P-4), ≤ 0.2 blocked unauthorized attempts per accepted issue (P-6). Acceptable? | These defaults | **M-PROMO** only (not the R3 PR) |
| Q-2 | Live Gitea for R3: (a) a `system` bot account that is not a repository admin and differs from the PSE account (or confirm the Lead account, if it differs from PSE); (b) you create the webhook (human-only) pointing at the gateway URL with a secret in `GITEA_WEBHOOK_SECRET`, and allow the gateway host in `ALLOWED_HOST_LIST` if needed (V-7); (c) branch protection meeting BP-01..BP-12, including auto-merge allowed; (d) the sandbox `<owner>/skill-lab-smoke` for the merge smoke stage; (e) an autonomy tracking issue | Double only; live auto-merge refused (RT-02) | **RT-02** and any live auto-merge |
| Q-3 | Dispatch limits: 1 concurrent PSE session (maximum 2), 10 dispatches a day (maximum 20), merge schedule TTL 30 minutes. Acceptable? | These defaults | Nothing |
| Q-4 | May R3 step 5 start at R2's independent `APPROVE` (R2 "merged" or awaiting merge, live gates `not_run`), with R3 completion and any promotion forbidden until both R2 and R3 are complete? This is the rule SPEC-201 applies to R2 | Yes: the roadmap rule, now uniform across releases (E-4, SPEC-202 D-20). Answer "no" to make R3 wait for R2 complete | Nothing with the default; **R3 step 5** if the stricter rule is chosen |
| Q-5 | Low-risk paths: default `docs/**` and Markdown outside agent and policy paths, ≤ 400 changed lines. Should any project also treat "non-sensitive UI" paths as low (report example)? | No; a project adds paths through a human-merged policy change | Nothing |
| Q-6 | Demotion triggers: your rule (escaped defect, revert) plus containment breach, gate-integrity violation, and lease violation. Keep the three extras? | Keep | Nothing |
| Q-7 | May role runners start headless `claude -p` sessions with edit permissions in a target repository? | No: runner none (outbox), sessions human-started | The `claude-cli` runner only |
| Q-8 | Merge style for auto-merges: merge commit (keeps PR commits for audits and revert attribution) or squash? | Merge commit | Nothing |
| Q-9 | R3 complete needs 3 consecutive full live runs, each about ≥ 76 agentic model calls (plus at most one repair turn each), ≥ 118 routing calls, and ≥ 76 Jev requests (spec.md §Release gates counts). Within your Ollama and TypeSafe plans? Should a cost cap apply once a runner reports usage? | Proceed; cost reported, not gated | R3 complete, if the answer is no |
| Q-10 | Escaped defects: who applies `incident/escaped-defect`, and is a `Caused-by: #<pr>` line in the issue body the attribution convention? Should an unattributed defect label also demote? | Humans label; `Caused-by:` convention; unattributed also demotes | Nothing |
| Q-11 | Observation lag before a merged PR counts toward P-1 and P-2: 7 days? | 7 days | M-PROMO only |

## 8. Cross-release findings (alignment items for SPEC-201 and SPEC-202)

R3 does not edit R1's or R2's documents. Each item names what R3 assumes and which task checks it.

**Status after the cross-release consistency pass (2026-10-22).** X-1: resolved in SPEC-202 FR-022 and D-12 (advisory
reason `BRANCH_PROTECTION_NONCOMPLIANT`, not a listed gate, so every decision validates). X-2: resolved; SPEC-201 and
SPEC-202 G-LIVE-01/03 use `bench.agentic.failed` and `bench.trigger.failed` ≤ 1, and the per-skill criteria files replace
SPEC-104's optional rate defaults by id. X-3: resolved; SPEC-201 T022 adds `GITEA_WEBHOOK_SECRET` to
`SECRET_ENV_VARS` (T050 keeps its "if still missing" check). X-4: resolved (row below). X-5: SPEC-202 D-21 now states why
it ships no fetch helper (fail-safe); R3 still adds `gitrepo.fetch_base()`. X-6: SPEC-201 FR-024 now defines the TTL
(1,800 s, the same constant as D-17); heartbeat cadence and grace stay R3's. X-10: SPEC-201 FR-025 now names the
vocabulary, including every type in plan.md §Routing table. X-7, X-8, and X-9 are R3 extensions and need no upstream
change. T002 still records the as-built status of each item.

| ID | Finding | R3 assumption | Checked by |
|---|---|---|---|
| X-1 | R2 D-12 and FR-022 keep a **failing** `branch_protection` gate with decision `HUMAN_APPROVAL_REQUIRED`, but [K merge-decision] `allOf[1]` makes any failed gate force `BLOCKED`, so that envelope is schema-invalid | At `guarded-autonomous` a non-compliant audit is a failing gate and the decision is `BLOCKED`. Below it, R3 keeps whatever schema-valid form R2 ships | T002, T064 |
| X-2 | R1 and R2 justify `G-LIVE-01 ≥ 0.67` as "tolerates exactly 1 miss" for 3 to 6 cases, but 2/3 = 0.667 < 0.67 and 4/6 = 0.667 < 0.67, so at 3 cases it tolerates **no** miss and at 6 exactly one | R3 uses count metrics: per-skill agentic failures ≤ 1, trigger misroutes ≤ 1 (D-24) | T053 |
| X-3 | `GITEA_WEBHOOK_SECRET` is read by R1's normalizer but missing from `redact.SECRET_ENV_VARS` (F-31) | R3 adds it if still missing (T050) and strips it from every handler environment | T002, T050 |
| X-4 | R2 D-20 ("R3 execution waits for R2 complete") was stricter than the roadmap ("R3 starts only after the R2 PR does") and than SPEC-201's rule for R2 | Resolved: SPEC-202 D-20 and E-4 now use one rule for both release pairs; OQ-05 offers the stricter option | T001 |
| X-5 | R2's base-branch check reads `origin/<base>` but no release adds a `git fetch` helper; R1's read-only allowlist has no `fetch` | R3 adds `gitrepo.fetch_base()` (fixed refspec) unless R2 ships one | T002, T050 |
| X-6 | Lease TTL, heartbeat, and grace are undefined in R1 and R2 | R3 defines them (FR-036); R2 may adopt them earlier | T002, T044 |
| X-7 | `gitea-project.v1` has no `system` identity | R3 adds optional `identities.system` (default the Lead login) | T021 |
| X-8 | R2 FR-025 requires `actor_role == required_role` for every label transition | R3 permits `system` for the observed-fact transitions only (D-13) | T079 |
| X-9 | [K merge-decision] permits `AUTO_MERGE` for medium risk | R3 caps at low in code (D-2) and keeps the schema | T036, T064 |
| X-10 | The event type names R3 routes on (for example the normalized name of a push to the base branch, of a review dismissal, of a label change) are R1's normalizer vocabulary, which is not yet written down as a table | T002 records R1's mapping; `ROUTES` uses those exact names, and an unknown type is recorded and routed nowhere | T002, T048 |
