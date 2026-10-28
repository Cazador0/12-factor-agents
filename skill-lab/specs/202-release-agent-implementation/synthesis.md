# Synthesis: R2 Agent implementation

**Spec ID**: SPEC-202 | **Delivery step**: 2 (Synthesize) | **Created**: 2026-10-22 | **Aligned**: 2026-10-22 with
SPEC-105 and the person's SPEC-201 refinement decisions (§8)

This document collects what R2 depends on, what was decided, and what is still open. Citations use these keys:

- **[R §x]**: `skill-lab/docs/research/engineering-team-report.md`, section heading x.
- **[S x]**: `skill-lab/docs/research/SOURCES.md`, section x.
- **[C §n]**: `skill-lab/docs/CONVENTIONS.md`, section n.
- **[RM]**: `skill-lab/specs/200-release-roadmap/spec.md`.
- **[R1 x]**: `skill-lab/specs/201-release-shadow/spec.md` or its `release-plan.md`, section or requirement x.
- **[K name]**: the canonical contract `skill-lab/contracts/schemas/<name>.v1.schema.json`, as written on 2026-10-22.
- **[Z page]**: the Zed docs page (zed-industries/zed `docs/src/ai/`) downloaded for SOURCES.md.
- **[O page]**: the Ollama docs page downloaded for SOURCES.md.
- **[105 x]**: `skill-lab/specs/105-jev-live-benchmarking/` (SPEC-105, Jev live benchmarking, delivered inside R1):
  its spec, plan, research (R-n), or data model, requirement or section x.
- **[I Qn]**: the person's answer to question n in `intakes/jev-live-benchmarking/intake.md`.

A claim with none of these keys is a design inference, and the text says so. A fact this release needs that no
source verifies is listed in §6 as "to verify", with the task that verifies it.

## 1. Findings

### 1.1 What the report asks of this autonomy level

- **F-1** Agent implementation mode: "PSE may branch, code, test, create PRs, and update assigned issues. Review performs
  independent automated review. Human remains the merge authority." [R §Progressive autonomy] The roadmap adds Lead issue
  creation and dependencies, Review posting reviews, and enforced leases [RM Releases].
- **F-2** Agents never get raw Gitea access: "Avoid an unrestricted `gitea.request(method, path, body)` tool. The point of
  the MCP layer is to establish semantic authority boundaries." Every mutation carries `actor_role`, `session_id`, the
  target, `expected_version`, `idempotency_key`, and `reason` [R §Gitea as the real-time engineering control plane].
- **F-3** The claiming sequence is: re-read the issue, re-read dependency state, verify Ready for Build, obtain the lease
  atomically, record the expected base SHA, create the isolated worktree and branch, transition to In Progress, start
  PSE. "Expiry must not automatically imply that another PSE may blindly continue in the same branch."
  [R §Claiming work safely]
- **F-4** Branch format `agent/pse/<issue>-<slug>`; Review normally needs no production branch [R §Claiming work safely].
- **F-5** The scheduler estimates a write set before parallel implementation and serializes overlaps
  [R §Protecting against cross-agent conflicts].
- **F-6** PSE invariants: "never mark evidence as passed unless executed", "verify external mutations after tool
  success", "never modify policy to make own work pass". PSE is the single write owner of its issue
  [R §Agent configuration philosophy; R §PSE contract].
- **F-7** Review "should never silently repair the PSE's production implementation and then approve the combined
  result"; its verdict is machine-readable [R §Review contract].
- **F-8** Recommended `main` policy: no direct push, no force push, no administrator bypass, at least 1 approval, block
  on requested changes, dismiss or ignore stale approvals, require the current base, required CI contexts, auto-merge
  only when policy passes, no force-merge tool for agents. The text adds blocking on outstanding review requests and
  protecting sensitive file patterns [R §Safe autonomous merge].
- **F-9** "Agents may operate autonomously inside the rules; they may not autonomously weaken the rules that define
  their authority." Changes to the orchestrator, CI policy, agent permissions, branch protection, and the Review agent's
  own gates are not self-authorized [R §Safe autonomous merge].
- **F-10** Gitea integration for Spec Kit: create only missing issues, set labels, create dependency relationships, write
  issue IDs back to a stable, committed mapping that "prevents repeated agent runs from creating duplicate issues". The
  sync reports drift "rather than silently rewriting the spec" [R §Gitea integration for Spec Kit].
- **F-11** Checkpoints persist decisions, evidence, blockers, and the next action, never chain-of-thought
  [R §Session checkpoint].
- **F-12** Agent-system verification must cover:
  - idempotency: a duplicated call leaves the external result correct;
  - ordering;
  - concurrency: "Can two PSE agents claim the same issue?";
  - permission containment;
  - prompt-injection resilience;
  - failure recovery.

  [R §Agentic-framework verification]
- **F-13** "'Not run' must never silently mean 'passed'"; the applicability decision must be explicit [R §Merge evidence
  gate]. [C §9] and ADR-0010 bind the same rule for the lab.
- **F-14** "LLM decides what it believes should happen. Policy code decides what it is allowed to make happen. Gitea
  enforces the final repository rules." [R §Orchestrator state model]
- **F-15** Board states and owners: In Progress (PSE) exits when the PR is ready. Review is entered when "CI baseline
  passes and PR submitted". Ready to Merge and Done are owned by System [R §Kanban state machine].
- **F-16** Core metrics include duplicate-work incidents, unauthorized-action attempts blocked, and resume or recovery
  success rate [R §Core metrics]. R2 produces the raw records (receipts, refusals) that R3's promotion logic will count.

### 1.2 Verified platform facts

- **F-17** Gitea 28.2.0 is current (2026-10-18). Issue dependencies are
  `GET|POST|DELETE /repos/{owner}/{repo}/issues/{index}/dependencies` with an `IssueMeta` body `{owner, repo, index}`.
  Project-board column coverage differs by version, so board state uses exclusive scoped labels `state/<name>`
  [S Gitea].
- **F-18** The Spec Kit `github` extension titles issues `T001: <description>` and deduplicates by matching existing
  titles against the task-ID regex `\bT\d{3,}\b` across open **and** closed issues [S Spec Kit].
- **F-19** Zed: skill scripts must never write inside their own skill folder; project-local skills load only from
  trusted worktrees; profiles decide which tools exist; `tool_permissions` decides allow, confirm, or deny, and
  `always_deny` wins [S Zed Agent skills]. Zed parses chained terminal commands and checks each sub-command
  [Z tool-permissions].
- **F-20** Zed has **one** Ollama provider with one `language_models.ollama.api_url` (`http://localhost:11434` local,
  `https://ollama.com` cloud). Context is sent as `num_ctx`, default **4096**, set per model with
  `available_models[].max_tokens` or globally with `context_window` [S Ollama with Zed; Z use-a-local-model]. A
  profile can set `default_model {provider, model}` [Z agent-profiles].
- **F-21** Ollama's default context is 4k under 24 GiB of VRAM and 32k at 24–48 GiB. Agents and coding tools "should
  be set to at least 64000 tokens". Cloud models run at maximum context. `ollama ps` shows whether the model is 100 %
  on GPU and which context it got [O context-length; S Ollama with Zed].
- **F-22** **Ollama Cloud does not support structured outputs**; local `/api/chat` accepts `format: "json"` or a JSON
  Schema [S Ollama with Zed]. In the Ollama app or CLI, cloud models are named like `gemma4:cloud`; API calls to
  ollama.com use names from `/api/tags`; cloud models can be retired [O cloud].
- **F-23** Zed worktree isolation creates new worktrees in detached HEAD; a `create_worktree` task hook runs after Zed
  creates a linked worktree [Z parallel-agents].
- **F-24** Jev: one narrow judgment per question; a noul near 0.5 means uncertain; responses report `usage`; typed
  output "guarantees the interface, not truth" [S TypeSafe AI "Jev"]. Bands: pass at or above the threshold, uncertain
  in [0.35, threshold), fail below 0.35. An uncertain `noul` judgment is re-asked once with the case's fixture contents
  and the skill's SKILL.md; a second uncertain value fails the judgment and flags it `needs_human` [105 FR-002; I Q5].
- **F-25** Codex discovers `.agents/skills` and invokes `$name`; Claude Code reads `.claude/skills/<name>` and invokes
  `/name`; Zed invokes Spec Kit skills as `/speckit-<command>` [S Codex and Claude Code skills]. So
  `/speckit-development` works verbatim in Zed and Claude Code, and as `$speckit-development` in Codex.
- **F-26** Spec Kit `converge` is append-only. It adds a `## Phase N: Convergence` section, never edits spec or plan,
  and leaves `tasks.md` byte-for-byte unchanged when nothing remains (upstream `templates/commands/converge.md` @ `dc2cec4`).

### 1.3 Facts from the foundation contracts

- **F-27** [K mutation-request]: `action` matches `^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$`; `target.type` ∈ issue,
  pull_request, project, branch, lease, label, comment, review; `expected_version` is `integer | null`; `params` is
  open.
- **F-28** [K gitea-plan]: operations carry a raw `request{method, path, body}` under `/api/v1/` and an `op` name.
  Replaying `request` verbatim would be the unrestricted tool F-2 forbids.
- **F-29** [K lease] already has `branch`, `base_commit`, `write_domains`, `resource.repository`, and an integer
  `version`. That is where the report's "expected base SHA" belongs.
- **F-30** Contract gaps the foundation leaves: [K benchmark-run] has `runtime`, `model`, `jev_mode`, and `notes`, but **no
  suite digest or commit**. [K implementation-evidence] checks have no per-check commit. [K sync-drift-report] has no
  comment field. [K merge-decision] gates are `pass | fail | not_run`. SPEC-105 closes the `benchmark-run` gap: it adds `suite_digest`,
  `commit`, `counts_toward_streak`, `exclusion_reasons`, `degraded`, `usage`, `cost`, `health_reports`, and `catalog` as
  fields [105 §Contracts].

### 1.4 Facts from SPEC-201 (R1), which R2 builds on

- **F-31** R1 ships the full catalog of **34 actions** in `_skillkit.policy.ACTION_CATALOG` (`catalog_version` 1.0.0)
  with `SUPPORTED_MAX_LEVEL = "shadow"`: "R1's catalog holds every action R2 performs and all 7 guarded actions R3
  enables, so R2 changes enforcement only." Later releases may add ids but may not lower a minimum level without a
  human-merged ADR; SPEC-203 adds two restrict-only ids in catalog 1.1.0 [R1 §Autonomy policy]. Notable levels:
  - `gitea.issue.close` is `guarded-autonomous`;
  - `gitea.pr.merge`, `gitea.branch_protection.update`, `gitea.webhook.create`, `git.push.protected`, and
    `policy.change` are `human-only`.
- **F-32** R1 already has the scripts whose `--apply` paths R2 enables, each refused at `shadow`:
  - lead-architect: `dispatch_recommend.py --apply`, `arbitrate.py --publish`;
  - pse-implementer and speckit-development: `delivery_plan.py --step worktree|branch|commit|push|pr` (plus
    `review-request|review-session` for speckit-development), each emitting `mutation-plan.v1`;
  - review-verifier: `review_verdict.py --comment-plan --post --apply`;
  - speckit-gitea-taskstoissues: `tasks_to_issues.py --apply`;
  - speckit-gitea-sync: `comment_plan.py`;
  - kanban-state-machine: `labels_plan.py --apply`;
  - work-lease: `lease.py --mirror`;
  - session-checkpoint: `checkpoint.py publish`;
  - merge-policy-gate: `merge_plan.py`.

  [R1 FR-018..FR-030]
- **F-33** R1 owns `check-run.v1` (`check_id`, `argv`, `head_commit`, `log_digest`, `env_removed`, …), produced by
  `_skillkit.checks`. That module strips secrets from child processes and denylists git write and forge CLI commands
  (FR-016). R1 also owns the review loop:
  - `review-request.v1` with forge `github | gitea`, round 1..3;
  - the verdict marker `<!-- skill-lab:review-verdict:v1 request_id=<id> head=<sha40> -->`;
  - `review_collect.py` with session-based independence through `Claude-Session:` trailers;
  - `review_local.py` (`claude -p --json-schema`, action `review.local.run`, allowed at `shadow`, never posts).

  Codes: `REVIEW_NOT_INDEPENDENT` (exit 4), `VERDICT_STALE` (exit 1), `CLAUDE_CLI_NOT_FOUND` (exit 3)
  [R1 FR-016, FR-034..FR-036].
- **F-34** R1 defines `release-gates.v1` and `skill-lab release check --spec <id> --stage merge|complete|post-review`,
  with gate IDs `G-(OFF|LIVE|POST)-NN`. Its live gates follow the person's floor model [R1 ledger row 1; 105 FR-005..FR-009]:
  - the defaults in `skill-lab/benchmarks/criteria/_defaults.json` are the floor: agentic pass rate ≥ 0.80, trigger
    accuracy ≥ 0.90, agentic schema-valid rate ≥ 0.95, and uncertain rate after the re-ask < 0.10;
  - they apply per skill and catalog-wide, and a per-skill criteria file may raise a gate but never lower it
    (`CRITERIA_BELOW_FLOOR`);
  - guardrail cases pass at 100 % per skill;
  - the live gates are merge-stage gates, which pass only on one fully passing counting live run [R1 ledger row 5].

  SPEC-201's earlier drafts used lowered per-skill rates and then counts of failed cases per skill. The person's gates
  decision ("More cases, both levels", 2026-10-22) replaced both, and R2 uses neither.
- **F-35** R1 ships `skill-lab/config/zed/local-ollama.disabled.jsonc` (`http://localhost:11434`, context ≥ 32,768),
  and `skill-lab install --inference local` exits 4 `LOCAL_INFERENCE_GATED` "(SPEC-202)". Every cloud profile uses
  provider `ollama` and a cloud model ID verified in `skill-lab/config/zed/cloud-models.json`, reached either through
  `api_url` `https://ollama.com` (shape b) or through a local daemon signed in to ollama.com at
  `http://localhost:11434` (shape a, the foundation template's current shape). The person chose shape (a) in SPEC-201's
  refinement (round 1): the Ollama app on the person's machine, signed in to ollama.com, serves the cloud models, so "one
  provider setting serves cloud now and local later" [R1 §Clarifications]. That settles V-5.
- **F-36** R1 makes R2's clamp raise conditional: "R2 raises it, after adding base-branch verification of the policy
  file" [R1 §Non-goals]. R1's `policy.load` reads only the working-tree file (FR-001) and has no escape hatch (FR-005).
- **F-37** R1 commits every live run under `skill-lab/benchmarks/runs/<run_id>/` and points its evidence at the run by
  digest [R1 §Clarifications, set 2; 105 FR-015]. `suite_digest` (over the selected case files and their skills'
  SKILL.md), `commit`, and `model` are fields of `benchmark-run.v1`, and `num_ctx` and `structured_output` are recorded
  per result [105 data-model; F-38]. R1 merges only after one fully passing counting live run [R1 ledger row 5], so R1
  has no live-pending state either. A run counts toward a streak only on the same model and suite digest, and editing
  or adding any case restarts the streak [105 FR-010; 105 §Clarifications]. R1 extends `merge-decision` with `uncapped_decision` and
  `autonomy_level`, and `review-verdict` with optional `request_id` and `reviewer{mode (cloud-session / cli-fallback /
  interactive-session), runtime, model?}`; the reviewer's session ID stays in the existing `reviewer_session` field
  [R1 §Contracts].

### 1.5 Facts from the foundation lab code (read 2026-10-22)

- **F-38** `skill-lab/lab/runtimes/` (SPEC-102) defines the runtimes `ollama-local`, `ollama-cloud`, `claude-cli`,
  `codex-cli`, and `replay`, with aliases `claude` and `codex`.
  - `ollama-local` posts to `$OLLAMA_HOST/api/chat` with `format` = the output schema, `num_ctx` 32768 by default
    (`DEFAULT_NUM_CTX`), and temperature 0. It records `structured_output`, `json_extraction`, `num_ctx`, and
    `done_reason`.
  - `ollama-cloud` has no structured outputs and runs a bounded repair loop (`max_repairs`).
  - Prompts come from a Zed skill-loading emulation, and results are labelled `<runtime>-zed-emulation`. Mirroring
    Zed's `select_catalog_skills`, the emulation leaves skills with `disable-model-invocation: true` out of the catalog
    the model sees.

  [code: `runtimes/__init__.py`, `runtimes/ollama_local.py`, `runtimes/ollama_cloud.py`, `runtimes/zed_emulation.py`]

### 1.6 Facts from SPEC-105 and the person's 2026-10-22 decisions

- **F-39** Live grading [105 FR-001..FR-004; 105 R-3]:
  - an uncertain Jev grade is re-asked once, then failed and flagged [I Q5];
  - a service failure after retries (connection error, HTTP 5xx, or 429 after retries) makes the case `errored`; the run
    finishes and does not count toward the streak (`outage`) [I Q6];
  - HTTP 401, 403, and 422 are configuration or case bugs, not outages [105 plan refinement];
  - invalid JSON after the 2 allowed repairs is a failed case, not an errored one;
  - a gate run has no time limit and runs to completion [I Q17].
- **F-40** Gates and minimums [105 FR-005..FR-008]: the floor of F-34, per skill and catalog-wide, with guardrail cases
  at 100 %. Every skill has at least 4 deterministic cases, at least 5 agentic cases (at least 1 tagged `guardrail`), and
  at least 10 trigger cases (at least 2 with `expect_skill: null`). `skill-lab validate` enforces the minimums.
- **F-41** Streak [105 FR-010..FR-012, US2]: `skill-lab streak` emits `benchmark-streak.v1` from the committed runs.
  - A counting run is live, complete, not degraded, and has no `errored` case.
  - `local_unlock_evidence` is true when 3 consecutive counting runs on the same model and suite digest pass every
    per-skill and catalog gate.
  - A case that passed and then failed breaks the streak and is listed as unstable [I Q13].
  - A model change or any case change restarts the streak.
  - Replay, partial, outage, and degraded runs neither extend nor break it.

  SPEC-105 names SPEC-202's L1 gate as the consumer of this streak, and leaves local parity runs to it [105 §Non-goals].
- **F-42** Monitoring [105 FR-019..FR-023; 105 R-9, R-11, R-12]:
  - `run-monitor` is skill 14 (SPEC-014, `metadata.family: control-plane`, `secondary_family: meta`, shipped in R1)
    [R1 §Clarifications];
  - bench writes a run log and runs `run-monitor` `snapshot` after each skill; the fixed limits in
    `skill-lab/benchmarks/monitor-limits.json` alone decide `degraded`, and a degraded run does not count;
  - one advisory agent call, on the run's own model, writes an `assessment` and never changes that decision;
  - a `null` figure (no `/proc`) can never mark a run degraded;
  - changes to `monitor-limits.json` need the person's approval [105 data-model];
  - the release reviewer posts its own `run-health.v1` report as a separate PR comment with its own marker.

  The person chose to monitor the benchmark container, the model sessions under test, and the reviewer session [I Q19],
  and later added their Rancher Desktop local containers, read from inside each container (F-46).
- **F-43** Storage, cost, and reporting [105 FR-013..FR-018]:
  - every result, run summary, run log, health report, and cassette is committed [I Q9];
  - cost comes only from the person-maintained `skill-lab/benchmarks/prices.json`, and without a price it is
    `usage-only`;
  - `skill-lab report --run` renders the PR comment, and the review request carries the run's digest [I Q2].
- **F-44** The person's SPEC-201 refinement decisions also bind R2 [R1 §Clarifications; R1 ledger]:
  - the release reviewer uses recorded evidence only, holds no Ollama or TypeSafe keys, and says so in its verdict;
  - CI runs offline on every PR, and live benchmarks run only when started manually;
  - at most 3 automated review rounds, then the person decides;
  - creating a Gitea webhook stays human-only at every level;
  - the runtime settings block agent edits to `.skill-policy.json`;
  - `set_by` is the person's GitHub username, `Cazador0`;
  - all four webhook replay-defence layers ship in R1: body-SHA-256 dedupe, a freshness guard on the signed
    `updated_at` and head SHA, events as hints (decisions re-read authoritative state), and secret hygiene, with
    `GITEA_WEBHOOK_SECRET_PREVIOUS` accepted for 7 days and body digests kept 90 days;
  - the Zed endpoint is shape (a) (F-35);
  - the engineering-team report is included in the private skill-factory repository;
  - agents may not edit `.skill-policy.json`, the criteria files, or `monitor-limits.json` (critical policy paths
    [R1 §Release gates; 105 data-model]).
- **F-45** Release sequencing (the person's decision, 2026-10-22, with the orchestrator's correction recorded in
  SPEC-200 open-questions.md): a release merges only after its live gates pass; the releases ship as **stacked PRs**
  [I A4]. R2's branch is created from `release/r1-shadow` once R1 has its independent `APPROVE` and its live gates
  passed; the R2 PR targets `release/r1-shadow` and is retargeted to `main` when R1 merges. R3 stacks on R2 the same
  way. Merges happen in order R1 → R2 → R3, each by a human. This answers OQ-05; the alignment run's "R2 entry = R1
  merged, branch from `main`" is withdrawn because it contradicted intake A4.
- **F-46** The person's release-alignment answers [{S}; SPEC-200 open-questions.md]:
  - no per-skill criteria file ships in R1 or R2; scoring uses `_defaults.json` (the floor), and only the person adds a
    file later to raise a skill's bar;
  - "run-monitor for Rancher Desktop local containers": the R2 local-inference runs happen inside one of the person's
    Rancher Desktop local containers, and `run-monitor` runs inside it and reads only that container's own CPU and
    memory limits and use (cgroup), disk free, and process count; no Docker or containerd socket; nothing else on the
    machine (Q-10, OQ-22);
  - the local model is decided at unlock time: list what fits the GPU at 32k context with tool support, verify it, and
    the person picks (Q-1, OQ-07);
  - the R2 defaults stay: 3 local parity runs (Q-4), L1 measured on the suite installed at unlock time (Q-9), one Gitea
    issue per task (Q-6), L1 alongside R3, blocking neither the R2 merge nor R3 (Q-5).

## 2. Decisions

| ID | Decision | Rationale | Alternatives rejected |
|---|---|---|---|
| D-1 | R2 changes enforcement, not vocabulary: raise `SUPPORTED_MAX_LEVEL` to `agent-implementation` and implement the `--apply` paths of the 19 actions at that level, using R1's action IDs and risk classes | F-31 is binding; it keeps one catalog | Adding R2-specific action names (would duplicate vocabulary and break R1's rule) |
| D-2 | Harden R1's `GiteaClient.send(operation)` with an endpoint table that maps each allowed (action, method, path template) to a semantic method. Any other operation is `UNSUPPORTED_OP`. The table has **no merge row**, and the client has no generic request method | F-2, F-28; makes "never auto-merge" structural, not only policy | Replaying `gitea-plan.request` verbatim; an MCP server (R2 must run offline as stdlib scripts, [C §3]) |
| D-3 | Per-role Gitea identities. Each session sets one `GITEA_TOKEN` (the env name stays as [C §3] has it; the value differs by role). `.skill-gitea.json` (`gitea-project.v1`) maps roles to logins and git emails. Review's login must differ (`CONFIG_INVALID` otherwise); Lead and PSE may share one. The client checks `GET /user` against the role before any write | Independence must hold at the forge, not only in prompts (F-7, F-9). Gitea's own self-approval refusal becomes a second line. On GitHub (factory repository), R1's session-based independence stays the only proof (F-33) | One shared bot token (makes independence unprovable); new env var names per role (more secrets to redact) |
| D-4 | The skills are Gitea-only. With forge `github` (R1's enum, F-33), the pr step writes `pr-request.v1` and stops with `next_action: orchestrator.create_pr`; the orchestrator creates the GitHub PR | User decision ("GitHub adapter? NO"); R1 scope note: factory delivery is the orchestrator's job | A GitHub adapter (a second write surface without a test double) |
| D-5 | Optimistic concurrency without a schema change: `expected_version` = the target's `updated_at` in Unix seconds (an integer, F-27), plus `params.expected_state_digest` = `ids.digest` of the observed state. The client re-reads immediately before writing, refuses on mismatch (`VERSION_CONFLICT`, exit 1), writes, re-reads, and verifies | The schema requires an integer; second resolution is coarse, and the digest makes it exact; re-read-and-verify meets F-6 | Changing `mutation-request` to accept a string; trusting write responses |
| D-6 | Idempotency ledger plus markers. Receipts (`mutation-receipt.v1`) are written atomically to `.skill-state/mutations/<key>.json` under `fsutil.file_lock`. Machine comments use R1's marker grammar: the verdict marker is unchanged, and other kinds use `key=` and `digest=` attributes. Dedupe searches only markers authored by configured identities | F-12 idempotency; a crash between write and ledger update cannot duplicate; a marker from an unknown author is untrusted (prompt injection, F-12) | Ledger only (lost on another host); markers only (extra reads, accepted anyway for comments) |
| D-7 | Lease authority stays R1's local store (single host, file lock, CAS `version`). `lease.py --mirror` posts the lease on the issue. Acquire refuses when the issue shows another session's unexpired active mirror. `_skillkit.leases` gives every skill a read-only `verify()` | Gitea offers no atomic compare-and-set we can rely on (V-3); conservative refusal is safe; R2 runs PSE on one host | Gitea as the authority (not atomic); a distributed lock service (R3 or later) |
| D-8 | The PSE session creates its own worktree (`delivery_plan.py --apply --step worktree`) at `<state-dir>/worktrees/<issue>-<slug>` from `lease.base_commit`. Dispatch records the base SHA in the lease but creates no worktree | The worktree must exist where the PSE runs; the report's order (F-3) is kept, with step 6 executed by the leased session | A dispatcher-created worktree (wrong host for cloud sessions; Zed sessions are human-started) |
| D-9 | Evidence is bound to R1's `check-run.v1`, extended additively with `tree_clean` and `worktree`. A check counts toward evidence for commit X only if it ran on X with a clean tree, so checks run **after** the commit. `evidence_manifest.py validate` adds 5 codes to R1's `CHECK_NOT_EXECUTED` | F-6, F-30, F-33; R1's contracts are unreleased, so additive optional fields follow R1's own pattern | A new R2 `check-run` contract (duplicates R1); accepting dirty-tree runs |
| D-10 | Push uses the exact refspec `refs/heads/B:refs/heads/B` (B = the leased `agent/pse/<issue>-<slug>`) and no force flag of any kind. The remote host must equal the `GITEA_URL` host, and URLs with credentials are refused. Git transport credentials are the user's own git configuration. The step verifies with `git ls-remote` | F-8, F-6, [C §3] secrets | `--force-with-lease` (still a force push; rebase is R3); a token in `http.extraHeader` (visible in the process list) |
| D-11 | Review posting is R1's `review_verdict.py --comment-plan --post --apply`. The verdict maps to a Gitea review event: `APPROVE` → `APPROVED` (only if `quality-gate.passed`), `CHANGES_REQUESTED` → `REQUEST_CHANGES`, `BLOCKED_BY_ENV` → `COMMENT`. Independence is R1's session rule plus R2's identity rule (reviewer login ≠ author, commit authors, and the PSE login), and freshness is checked at post time. The CLI fallback stays R1's read-only `review_local.py`, which never posts; posting needs a Review-identity session | F-7, F-9, F-33; an environment failure is not the author's fault, but a missing approval still blocks the merge | Posting from the CLI subprocess (it would inherit the author's token, violating D-3) |
| D-12 | The merge gate keeps R1's cap: `decision` is at most `HUMAN_APPROVAL_REQUIRED` at this level, `uncapped_decision` is recorded, and the reason `CAPPED_BY_AUTONOMY_LEVEL` is added. `branch_audit.py` checks BP-01..BP-12 through a data mapping file; a field the API omits is `unknown`, never `pass`. A non-compliant base is **advisory** at this level: the decision adds reason `BRANCH_PROTECTION_NONCOMPLIANT` (with the audit digest) and stays at most `HUMAN_APPROVAL_REQUIRED`, but the audit is not listed in `gates[]`, because [K merge-decision] `allOf[1]` forces `BLOCKED` whenever a listed gate is `fail` (SPEC-203 X-1). R3 makes compliance a real gate for `AUTO_MERGE` | [RM] R2 row; F-13; F-37 (`uncapped_decision` gives calibration data); a mapping file makes field renames a data fix; the advisory form keeps every envelope schema-valid | `BLOCKED` on non-compliance (blocks every unprotected repository while a human is the merge authority anyway); a failing listed gate with `HUMAN_APPROVAL_REQUIRED` (schema-invalid) |
| D-13 | `labels_plan.py --apply` recomputes the transition from live state with R1's `transition.py` and refuses differences (`PLAN_STALE`). Board state is exclusive `state/<kebab>` labels only. A `system` transition may be triggered by any session, because the deterministic engine decides it. The CI precondition for Review is explicit: a `success` combined status, or `ci: "none"` declared in config | F-13, F-14, F-15, F-17 | Trusting the input decision; project columns (version-dependent) |
| D-14 | One shared plan applier, `_skillkit.plan_apply`, executes every `gitea-plan` in R2 under per-skill op allow-lists: taskstoissues, sync comment plan, arbitration publish, verdict post, checkpoint publish, lease mirror, and kanban labels. It calls `require()` for all ops first (R1 FR-007), refuses on a changed source digest (`PLAN_STALE`), re-runs dedupe before each create (map, then title regex across open and closed issues, F-18), journals after every op, and stops at the first failure | F-10, F-18, F-28; one tested applier instead of seven | Per-skill appliers; skipping the per-op re-check (crash duplicates) |
| D-15 | `speckit-development` is a resumable step machine whose state is `delivery-record.v1`. It reuses R1's `dev_state.py`, `converge.py`, `pr_body.py`, `review_request.py`, `review_local.py`, and `review_collect.py`. Both `delivery_plan.py` scripts already plan per `--step` (SPEC-201: worktree, branch, commit, push, pr, plus review-request and review-session for speckit-development). R2 adds `--apply` to those same steps, backed by one shared `_skillkit.delivery`. Converge is bounded at 3 passes, after which it reports `NOT_CONVERGED` and escalates to Lead. `--step review-request` requests the Review login on Gitea (`gitea.pr.review.request`), and `--step review-session` writes the session dispatch (`review.session.request`). `review_request.py` stays R1's document producer | F-26, F-32, F-33; small models need one tool call per step [C §2]; no duplicate executor | One monolithic delivery script (opaque, not resumable); unbounded converge |
| D-16 | **Sign-off contract: a generic `human-signoff.v1`** (`subject.kind` ∈ `inference-enablement`, `autonomy-level-change`), plus a separate machine-computed **`inference-gate.v1`**. No bespoke `inference-signoff.v1` | The human attestation and the machine evidence have different authors and different trust. Keeping them apart stops a bug or an agent from folding "passed" into the human's record. The sign-off binds to evidence by run IDs and digests. R3's level promotions also need a human sign-off (critical risk, [RM]), so one generic contract serves both | `inference-signoff.v1` (single use; mixes evidence and attestation); a free-text approval file (not machine-checkable) |
| D-17 | L1 gate rules consume SPEC-105 (F-41). **Cloud entry**: `benchmark-streak.v1` for the cloud model has `local_unlock_evidence: true` on the current suite digest: 3 consecutive counting runs (runtime `ollama-cloud`, which SPEC-102 labels `ollama-cloud-zed-emulation`; `jev_mode: live`; all 14 skills' agentic and trigger tiers; complete; not degraded; no `errored` case) on the same model and suite digest, each passing every per-skill and catalog floor gate and every guardrail case, with no unstable case. Runs that do not count (replay, partial, outage, degraded) neither extend nor break the streak. A counting run that fails a gate, or a case that passed and then failed, breaks it. A model or suite change restarts it. `gate l1` recomputes the streak with `lab.streak` from the committed runs and never trusts a stored streak file. **Sign-off**: the person's `approve` `human-signoff.v1`, bound to the streak's run ids and digests. **Local parity**: the same floor gates on `ollama-local`, on the same suite digest, on 3 consecutive counting runs (Q-4, resolved: 3). Runs use cloud-parity mode (no `format`, the same bounded repair loop as `ollama-cloud`, F-38) and `num_ctx` ≥ 32768. Records are per `(runtime, model)`. R1's runs count only when their suite digest equals the suite being enabled. R2's added cases change the digest, so R2's own gate run starts the R2-suite streak | The person's decisions: 3 consecutive live runs plus a sign-off before local inference [I A3, Q3, Q13], and the streak is SPEC-105's, so L1 needs no second definition. "Reliable" applies to local the same way: the roadmap says the suite "then passes", and one pass at non-zero temperature proves little. The cloud runs cannot use `format` (F-22), so local runs that do would be graded on easier terms (F-38) | A separate L1 streak definition (it would drift from SPEC-105); count-based gates (overturned by the person, F-34); 1 local run (weaker, Q-4); counting replays (forbidden [I Q17]); counting R1 runs against a different suite |
| D-18 | Local enablement uses R1's `local-ollama.disabled.jsonc`, completed with the `Lead (local)`, `PSE (local)`, and `Review (local)` profiles and per-model `max_tokens: 32768`. `skill-lab install --runtime zed --inference local` keeps exiting 4 `LOCAL_INFERENCE_GATED` without an `ENABLED` record for the current suite digest and model. Every profile, cloud and local, uses provider `ollama` at `http://localhost:11434`, served by the local Ollama app signed in to ollama.com (shape a, the person's decision, F-35). The cloud profiles keep their `<model>:cloud` ids, and the `(local)` profiles switch the model ids to local models on the same provider. Cloud profiles stay installed as the fallback | ADR-0003 (about 32k context under 24 GB); F-20, F-21 (4096 and 4k defaults are too small; 64k does not fit this GPU class, ADR-0003); F-35 | Editing the person's live settings without the gate; dropping the cloud profiles; a second provider for cloud (shape b, not chosen) |
| D-19 | Live Gitea smoke test: a staged command (`lead`, `pse`, `review`, `cleanup`; one identity per stage) against a sandbox repository named `^[^/]+/skill-lab-smoke(-[a-z0-9-]+)?$`. The client refuses consequential writes to a non-loopback host until a passing `smoke-report.v1` exists for that host and Gitea version (`LIVE_SMOKE_REQUIRED`) | F-17 drift risk; "test double now, live later"; the first live write happens in a sandbox | An optional, unenforced smoke test; smoking against the target repository |
| D-20 | **One exit state**, as in R1 [R1 ledger row 5]. **Merged** = every merge-stage gate `pass`, offline and live (G-LIVE-01..G-LIVE-07 on one fully passing counting live run of the R2 suite, FR-047), an independent `APPROVE`, and a human merge. `not_run` keeps the PR open; there is no "merged, live-pending". "R2 complete" in SPEC-200 and SPEC-203 means R2 merged. Sequencing (F-45): stacked PRs [I A4]. R2 step 5 starts once R1 has its `APPROVE` and its live gates passed (E-1..E-3), on a branch created from `release/r1-shadow`; the R2 PR targets `release/r1-shadow` and is retargeted to `main` when R1 merges (E-6); R2 merges only after R1. R3 stacks on R2 the same way; promotion rules are SPEC-203's | The person's decision for R1 (the live run decides whether the PR is ready, and one fully passing run is enough [I Q1, Q15]), applied to every release on 2026-10-22 ("a release merges only when its live gates pass") and the stacked-PR decision [I A4] restored by the correction of 2026-10-22; [C §9]; [RM] "A release that misses a gate stays open; the next one does not start". Q-3 is resolved by it | Merging "live-pending" (overturned by the person); treating `not_run` as accepted; waiting for the previous release's merge before branching (it contradicted intake A4, correction 2026-10-22) |
| D-21 | **Base-branch verification of the policy file** (F-36). Above `shadow`, `policy.load` also reads `.skill-policy.json` from `refs/remotes/origin/<base_branch>` (from `.skill-gitea.json`, default `main`; refs under `agent/` are refused) with read-only `gitrepo`. The effective level is the minimum of the working tree, the base ref, and the clamp. A missing or invalid base copy yields `shadow` plus `POLICY_NOT_ON_BASE`. R2 adds no `git fetch` helper: a stale `origin/<base>` can only keep a level that a human can still lower instantly in the working tree (the minimum wins), and a raise needs a human `git fetch`; SPEC-203 adds `gitrepo.fetch_base()` | Agents can only push `agent/*` branches (D-10 plus BP-01), so the base copy changes only through a human-merged PR. A raise in a worktree therefore has no effect | Trusting the working-tree file (any PSE could raise its own level); signing the policy file (key management out of scope) |
| D-22 | `complete_issue.py` sets `state/done` (`gitea.labels.set`) and only reports `CLOSE_PENDING`; it does not close the issue. PR bodies carry `Closes #<issue>`, so the human merge closes it (to verify, V-1) | F-31: `gitea.issue.close` is `guarded-autonomous`; re-levelling needs a human-merged ADR | Lowering the close action's level via an ADR (not worth the authority change for R2) |
| D-23 | The double's state logic moves into `_skillkit/gitea_memory.py` (vendored), so deterministic cases are hermetic through `--gitea-fixture`. R1's `skill-lab/lab/gitea_double.py` becomes a thin HTTP wrapper over it, with write endpoints. `gitea-fixture.v1` supersedes R1's seed format | Skills must run their own deterministic cases after `git subtree split` ([C §1]); one engine serves both transports | A second, write-capable double in the lab only (deterministic cases would need a server) |
| D-24 | R2's release gates live in `gates.json` in R1's `release-gates.v1` format. The live gates use the floor model, per skill and catalog-wide (F-34, F-40), all in stage `merge`, and are computed from one committed counting run (FR-047). They never use counts of failed cases or lowered per-skill thresholds. The smoke gate (RT-01) and the L1 gates sit outside `gates.json`, because they do not decide the merge | F-34; one gate engine for every release; the person's gates decision | A separate R2 gate runner; count-based live gates (overturned by the person) |
| D-25 | ADR numbers 0201–0207 (R1 uses 0101–0109; R3 is expected to use 0301–0309) | Parallel planners must not collide | Global next-free numbering |
| D-26 | The 10 R2-changed skills keep model invocation enabled: no `disable-model-invocation: true`, although CONVENTIONS §2 would permit it now that they perform consequential writes. Writes stay behind the policy level, `--apply`, the runtime `always_confirm` rule on `--apply`, and the lease and identity checks | Zed leaves `disable-model-invocation` skills out of the catalog the model sees (F-38, Zed emulation), so the read-only R1 functions of these skills would stop routing, and the trigger gate G-LIVE-03 (per skill and catalog-wide) would fail by construction. The authority boundary is deterministic code, not whether a model may load instructions | Setting the flag (loses routing for planning and analysis; user-invoked only) |
| D-27 | **Run monitoring in R2.** Every live run R2 makes, cloud or local, follows SPEC-105: a run log, a `run-monitor` snapshot after each skill, the limits alone deciding `degraded`, and degraded or outage runs not counting (F-42). On `--runtime ollama-local`, which runs inside one of the person's Rancher Desktop local containers, bench calls `snapshot.py --target local-container` in that container (the target ships with SPEC-105 in R1 [105 R-9]): CPU and memory from the container's own cgroup v2 files (`cpu.stat`, `cpu.max`, `memory.current`, `memory.max`), cgroup v1 as a fallback, `null` with a note when neither is readable; disk free and process count as seen inside the container; no Docker or containerd socket, nothing else on the machine. The API and session figures still apply, because the person chose to monitor the model sessions under test [I Q19 B]. The advisory call on a local run uses the run's own runtime and model, as [105 R-11] chooses for cloud runs. `monitor-limits.json` is unchanged | The person's answer "run-monitor for Rancher Desktop local containers", read from inside each container (F-46; Q-10 resolved) | `snapshot.py --host-metrics off` (withdrawn: it left memory and disk trouble undetected); reading the host or a Docker or containerd socket (not chosen); calling the cloud model for the advisory on a local run (adds a cloud dependency to a local run) |
| D-28 | **Release review on recorded evidence.** The R2 release reviewer re-runs `release check --stage merge`. Its live gates read only the committed run named in `evidence/live-runs.json` (FR-047), so the reviewer holds no Ollama or TypeSafe keys, re-runs no live case, and says so in its verdict. It runs `run-monitor` `snapshot --target reviewer-session` in its own container and posts the report as a separate marked PR comment. CI runs only the offline gates on every PR; live benchmarks run only when started manually. At most 3 review rounds, then the person decides | F-44; [105 FR-018, FR-023, R-12] | Keys in the reviewer environment (not chosen); live tiers in CI (not chosen) |
| D-29 | **Critical policy paths stay human.** R2's commit step and merge-policy-gate keep SPEC-201's critical policy paths, among them `.skill-policy.json`, `skill-lab/benchmarks/monitor-limits.json`, and the criteria files `skill-lab/benchmarks/criteria/**`, and add `.skill-gitea.json`. No agent edits them, the runtime templates deny edits to them, and a diff touching them is `critical` | The person's decisions: agents may not edit `.skill-policy.json` [R1 §Clarifications, set 2]; changes to the limits need the person's approval [105 data-model]; the criteria are the floor [105 FR-005]; F-9 | Letting an agent tune limits or criteria after a failing run (it would weaken its own gate, F-9) |

## 3. Refinements to the capability partition (with reasons)

The user's partition and its level semantics are kept. These refinements fill gaps it leaves open:

1. **lead-architect** also gets `complete_issue.py`. After a human merge, *observed by polling*, it sets `state/done` and
   lists unblocked issues. It cannot close the issue (D-22), and nothing else closes the board loop until R3's events.
2. **pse-implementer** uses `gitea.pr.update` (already in R1's catalog) to refresh the evidence in the body during the
   Changes Requested → fix → push loop [R §Review contract].
3. **review-verifier** checks freshness *at post time* (reviewed commit = head) in R2. Invalidating earlier approvals on
   new-head events stays in R3 (`gitea.pr.review.dismiss`).
4. **kanban-state-machine** recomputes every decision at apply time (D-13), so a stale or forged `transition-decision`
   cannot move the board.
5. **speckit-gitea-sync** applies its comment plan through the shared applier (D-14), limited to `create_comment`,
   because [K sync-drift-report] has no comment field (F-30).
6. **lead-architect** also enables `arbitrate.py --publish --apply` (`gitea.comment.create`), which R1 lists as a
   requester. An arbitration record that cannot reach the PR cannot settle a PSE/Review disagreement.
7. **gitea-event-normalizer** is unchanged. R2 polls Gitea state at each step instead of consuming events. R1's four
   replay-defence layers (F-44) stay as R1 ships them, and R3's gateway builds on them. R2's own writes already re-read
   authoritative state before acting (FR-005), the same principle as "events as hints".
8. **The policy machinery** (not a skill) gains base-branch verification (D-21), because R1 made it a precondition of
   raising the clamp.
9. **run-monitor** (skill 14) gets no script change: bench uses its target `local-container` (SPEC-105, delivered in
   R1) on local runs, and its SKILL.md names that use (D-27). Its limits, schema, and decision rule are unchanged.

## 4. Trade-offs

| Trade-off | Chosen | Cost accepted |
|---|---|---|
| Strong independence vs. setup effort | Two or three Gitea bot accounts (D-3) | The user creates accounts and tokens before live use |
| Lease safety vs. multi-host parallelism | Single-host authority (D-7) | No PSE parallelism across machines until R3 or later |
| Exact concurrency vs. schema stability | Integer version plus digest in `params` (D-5) | A small race window between re-read and write (RK-2) |
| Reliability evidence vs. time to local | 3 + 3 consecutive counting live runs plus sign-off (D-17) | L1 needs at least 6 counting full live agentic and trigger runs (outage or degraded runs do not count and are re-run), plus Jev usage |
| Honest gates vs. merging early | One exit state: the live gates block the merge (D-20, the person's decision) | The R2 merge, R3's start, L1, and any promotion wait on the keys and the network allowlist; execution, offline gates, and the PR do not |
| Monitoring coverage vs. the person's choice | Local runs monitored only from inside their own Rancher Desktop container (D-27) | Nothing outside that container is seen; a container without readable cgroup files reports `null` CPU and memory |
| One forge client vs. dogfooding on GitHub | Gitea-only skills (D-4) | The factory repository's own PRs use the orchestrator, not the R2 skills |
| Base-branch policy check vs. offline simplicity | Read the base copy from the remote-tracking ref (D-21) | A fresh clone with no `origin/<base>` runs at `shadow` until fetched |

## 5. Residual risks

| ID | Risk | Residual after mitigation | Owner |
|---|---|---|---|
| RK-1 | Gitea 28.x shape drift (fields, review event names, branch-protection field names, label `exclusive`, auto-close on merge) | Low once V-1 and the live smoke test pass; medium until then | Lead |
| RK-2 | Lost update between re-read and write | Low: the lease serializes PSE writers; the Lead is a single session in R2 | Lead |
| RK-3 | Single-host lease store | Accepted for R2; ADR-0202 | Lead |
| RK-4 | Raw `git push` or raw HTTP from an agent's terminal | Runtime deny lists are guardrails, not a boundary [C §7]. The boundary is Gitea branch protection (BP-01, BP-02) plus least-privilege bot tokens | User (Gitea admin) |
| RK-5 | The R2 PR changes `policy.py` (the clamp), runtime permission configs, the merge gate, and `skills/review-verifier/**`: critical risk under F-9 and R1's critical path list | Human merge mandatory; reviewer checklist (T140); merge-policy-gate must classify the diff `critical` (SC-014) | Human |
| RK-6 | Local model cannot follow the procedures at 32k | The gate stays `NOT_ENABLED`; cloud remains the default | User |
| RK-7 | Ollama may silently truncate prompts longer than `num_ctx` | Unverified (V-6); the doctor probe and an over-length fixture detect it | Lead |
| RK-8 | CLI-fallback review: the same principal launches the reviewer | Recorded as `mode: cli-fallback` (R1 contract); the human sees it before merging | Human |
| RK-9 | Prompt injection through issue and PR text the agents now act on | Markers trusted only from configured identities; untrusted text never executed [C §3]; agentic injection cases (T058, T088) | Review |
| RK-10 | The Codex sandbox may block network for `git push` | V-7; runtime note; Codex gets exit 3, never a silent skip | Lead |
| RK-11 | The stacked R2 PR is retargeted from `release/r1-shadow` to `main` after R1 merges, which can change the diff; the R1 head can also change before R1 merges | Re-review whenever the diff changes (step 8, T142); a new R1 head means a rebase and new entry evidence (E-1..E-3) | Orchestrator |
| RK-12 | A forged `human-signoff.v1` (the attestation is not authentication) | Impact limited to local inference on the user's machine; reversible; demoted by the next failing run | User |
| RK-13 | No `origin/<base>` ref (fresh clone, offline) makes the effective level `shadow` | Intended fail-closed behaviour; documented in the runbook (`git fetch origin <base>`) | User |
| RK-14 | R2's added eval cases change the suite digest, so R1's streak does not carry over | Expected (F-41); the R2 gate run is the first run of the R2-suite streak | Lead |
| RK-15 | A Rancher Desktop container without readable cgroup files gives `null` CPU and memory figures during local runs (D-27), so memory trouble goes unnoticed | The note names the gap; cgroup v1 is read when v2 is absent; disk free, API error-rate, and no-progress limits still mark the run degraded | Person |

## 6. Facts to verify during execution (not assumed)

| ID | Fact needed | How and where it is verified | Blocks |
|---|---|---|---|
| V-1 | Gitea 28.2.0 endpoint paths, fields, and pagination for: issues (create, list with `state=all`, edit assignees, replace labels), comments, labels with `exclusive`, milestones, pulls (create, list, get, edit, commits, files, requested reviewers), reviews (event names), combined commit status, branch protections, `/version`, `/user`, `/swagger.v1.json`. Also whether `Closes #N` closes issues on merge into the base branch | T003: vendor Gitea's v28.2.0 swagger into `docs/research/vendor/` and add an endpoint table to SOURCES.md. If neither source nor a live instance is reachable, mark it "unverified" and rely on the live smoke test | Live use only (the double follows the table) |
| V-2 | Branch-protection field names for BP-01..BP-12. Candidates to confirm: `enable_push`, `enable_force_push`, `block_admin_merge_override`, `required_approvals`, `block_on_rejected_reviews`, `dismiss_stale_approvals`, `ignore_stale_approvals`, `block_on_outdated_branch`, `enable_status_check`, `status_check_contexts`, `block_on_official_review_requests`, `protected_file_patterns` | T003; recorded in `skills/merge-policy-gate/assets/branch-policy-map.json`; unknown fields report `unknown` | Correctness of live audits |
| V-3 | Whether Gitea supports conditional writes (ETag or `If-Match`) for issues | T003 (swagger). If yes, D-5 adds it; if no, D-5 stands | Nothing |
| V-4 | `claude -p` flags used by R1's `review_local.py` (`--output-format json`, `--json-schema`) in the installed version | T004 (`claude --help`), shared with SPEC-201's verification | CLI fallback only |
| V-5 | **Shape decided by the person: (a)** (F-35). Left to verify: the signed-in local Ollama app lists local model ids next to the `:cloud` ids under the one `ollama` provider at `http://localhost:11434`, and a Zed profile can pin either | T004 confirms it against R1's T112 record and records it in SOURCES.md. If it fails, T004 reports the failure and M-L1 stops; nothing moves to shape (b) without the person | M-L1 only |
| V-6 | Ollama behaviour when a prompt exceeds `num_ctx` (truncation or error), and whether `/api/ps` reports context length and VRAM split | T004 and T111 (doctor probe) | M-L1 only |
| V-7 | The Codex sandbox's network default for `git push` and HTTPS to Gitea | T004 | Codex runtime notes |

## 7. Open questions for the user

Consolidated, deduplicated, and prioritised across all three releases in
[SPEC-200 open-questions.md](../200-release-roadmap/open-questions.md). Mapping: Q-1 → OQ-07, Q-2 → OQ-06, Q-3 → OQ-05,
Q-4 → OQ-11, Q-5 → OQ-05 (sequencing) and OQ-23 (L1 alongside R3), Q-6 → OQ-20, Q-7 → OQ-14, Q-8 → OQ-21, Q-9 → OQ-12,
Q-10 → OQ-22. Q-3, Q-7, and Q-8 are resolved by the person's 2026-10-22 decisions, and Q-1, Q-4, Q-5, Q-6, Q-9, and
Q-10 by the answers recorded 2026-10-22, with sources in the table. Only Q-2 is open.

| ID | Question | Default if unanswered | Blocks | Status |
|---|---|---|---|---|
| Q-1 | Which local Ollama model(s) should the Lead, PSE, and Review profiles use, and exactly how much VRAM does the GPU have? The model must support tool calls in Zed (`supports_tools`) and fit fully on the GPU with a 32k context | None. The plan does not pick a model it cannot verify | **M-L1** (not the R2 PR) | **Resolved (answers recorded 2026-10-22): decide at unlock time.** List what fits the GPU at 32k context with tool support, verify it (L1-d), and the person picks |
| Q-2 | Gitea for live use: the instance URL, a sandbox repository `<owner>/skill-lab-smoke`, and bot accounts `agent-lead` and `agent-pse` (these may be one account) plus `agent-review` (must be separate), each with a personal access token holding the least scopes that allow the R2 actions (exact scope names to be verified, V-1) | Double only; the client refuses live writes (D-19) | **Live smoke test RT-01** and any live write | Open. The person confirmed "Gitea is a test double for now" [I A6] |
| Q-3 | May R2 merge on the offline gates while live gates are pending ("merged, live-pending"), with R3 execution starting at R2's `APPROVE` and R3 completion and any promotion waiting for R2 "complete"? | — | — | **Resolved, 2026-10-22: no.** A release merges only when its live gates pass; there is no "merged, live-pending" (D-20). Source: intake Q1 and Q15 (the live run decides whether the R1 PR is ready; one fully passing run), SPEC-201 refinement ledger row 5, and the person's 2026-10-22 decision applying this to every release. The start rule is settled too (OQ-05, F-45): stacked PRs. R2's branch is created from `release/r1-shadow` once R1 has its `APPROVE` and its live gates passed, its PR is retargeted to `main` when R1 merges, R3 stacks on R2 the same way, and merges happen in order R1 → R2 → R3. Source: intake A4, restored by the correction recorded 2026-10-22 in SPEC-200 open-questions.md |
| Q-4 | Local parity: 3 consecutive local runs (default, the same standard as cloud), or 1? | 3 (D-17) | Nothing | **Resolved (answers recorded 2026-10-22): 3** |
| Q-5 | L1 runs in parallel with R3 and blocks neither the R2 merge nor R3. Correct? | Yes (roadmap sequencing diagram) | Nothing | **Resolved (answers recorded 2026-10-22): yes.** L1 can run alongside R3 and blocks neither the R2 merge nor R3. The sequencing part is settled by F-45 (stacked PRs) |
| Q-6 | Issue granularity: one Gitea issue per task (SPEC-201's dry-run behaviour, matching the Spec Kit extension), or grouped issues as in the report's example? | SPEC-201's behaviour; R2 only applies plans | Nothing in R2 | **Resolved (answers recorded 2026-10-22): one Gitea issue per task** |
| Q-7 | Which signer identity goes into `human-signoff.v1` (for example the GitHub login `Cazador0`)? | — | — | **Resolved, 2026-10-22: `Cazador0`.** Source: SPEC-201 refinement, set 1 ("`set_by` is the person's GitHub username (Cazador0)"), which answers OQ-14, the question that consolidates SPEC-201 Q6 and this Q-7. Applied: `signer.github_login: "Cazador0"` (FR-035) |
| Q-8 | Should the R2 PR body include live benchmark artefacts (Jev request IDs, token usage), or only digests? | — | — | **Resolved, 2026-10-22: everything is committed, and the PR gets the report.** Every result file, run summary, run log, health report, and cassette is committed under `skill-lab/benchmarks/runs/<run_id>/`, and R2's evidence points at the run by digest. The R2 PR gets the `skill-lab report` comment (per-skill and catalog results, unsure and flagged cases, tokens and cost basis, the suite digest), and the review request carries the run's digest. Source: intake Q2, Q9, Q16 C; SPEC-105 FR-015 and FR-018; SPEC-201 refinement, set 2 |
| Q-9 | R1's live runs count toward the L1 streak only for an L1 evaluation of the **R1 suite** (D-17, agreed by SPEC-201). Do you want to enable L1 early on the R1 suite (the record goes stale when R2's suite lands, and must be re-earned), or wait for the R2 suite? | Evaluate on whatever suite is installed when 3 runs exist; `install --check` flags staleness | Nothing | **Resolved (answers recorded 2026-10-22): L1 is measured on the suite installed at unlock time.** Editing or adding any case, or a model change, restarts the streak (SPEC-105 FR-010) |
| Q-10 | R2's local parity runs (M-L1 step L1-e) run on your machine against local Ollama. Should `run-monitor` record CPU, memory, disk free, and process count during those runs, so that memory or disk trouble marks the run degraded? | No (the withdrawn `--host-metrics off`) | Nothing with the default; it concerns M-L1 only | **Resolved (answers recorded 2026-10-22): "run-monitor for Rancher Desktop local containers".** The runs happen inside a Rancher Desktop local container; `run-monitor` runs inside it with target `local-container` and reads only that container's own cgroup CPU and memory limits and use, disk free, and process count; no Docker or containerd socket; nothing else on the machine (D-27, FR-048) |

## 8. Alignment ledger (2026-10-22)

The person's final decisions of 2026-10-22, recorded in SPEC-201 §Clarifications (session 2026-10-22 and the
refinement ledger R1), in SPEC-105 (spec, plan, research, data model, tasks), and in
`intakes/jev-live-benchmarking/intake.md`, applied to R2. No row adds a product decision. Row 8 now applies the person's answer on monitoring (answers recorded 2026-10-22), and row 4 the
stacked-PR correction.

| # | Decision and source | R2 before | Applied in R2 |
|---|---|---|---|
| 1 | 14 skills: `run-monitor` is SPEC-014, family control-plane with secondary family meta, shipped in R1; its R1 capability is SPEC-105 FR-019..FR-023 [R1 ledger row 3; I Q22] | 13 skills; 26 export symlinks; ≥ 112 deterministic cases | SC-011 and RG-9 name 14 skills; G-OFF-05 ≥ 116 (R1's 14 × 4 = 56, plus 60); G-OFF-21 = 28 (14 × 2); `run-monitor` gets its R2 delta, one option (D-27, FR-048, T143, T144) |
| 2 | Floor gates: agentic ≥ 0.80, trigger ≥ 0.90, agentic schema-valid ≥ 0.95, uncertain after the re-ask < 0.10, per skill and catalog-wide; guardrail cases 100 %; per-skill criteria may only raise; minimums ≥ 4 deterministic, ≥ 5 agentic (≥ 1 guardrail), ≥ 10 trigger (≥ 2 expecting no skill) [105 FR-005..FR-008; R1 ledger row 1] | G-LIVE-01 and G-LIVE-03 counted failed cases (≤ 1 per skill); minimums of 3 agentic and 6 trigger cases | G-LIVE-01..G-LIVE-05 are the floor at both levels; G-OFF-06 adds `criteria.below_floor`; FR-043 keeps SPEC-105's minimums for every skill; D-24, F-34, F-40 |
| 3 | Live run rules: re-ask once then fail and flag; outage (5xx, 429 after retries) makes cases `errored` and the run not counting; 401/403/422 are not outages; degraded runs and replays never count; results committed under `skill-lab/benchmarks/runs/<run_id>/` and referenced by digest; cost from `prices.json`, usage only when a price is missing; `monitor-limits.json` changes need the person's approval [105 FR-001..FR-004, FR-010..FR-018, FR-022; 105 R-3; 105 plan refinement] | Runs recorded into `evidence/bench/`; suite digest through a `notes[]` fallback; no cost basis | FR-046, FR-047, FR-040; `evidence/live-runs.json` names runs by digest; plan.md §Benchmark plan; D-29 makes the limits and criteria critical policy paths; F-39, F-43 |
| 4 | A release merges only after its live gates pass; no "merged, live-pending"; stacked PRs: R2 starts once R1 has `APPROVE` and its live gates passed, on a branch from `release/r1-shadow`, its PR targets that branch and is retargeted to `main` when R1 merges; R3 stacks on R2 the same way; merges in order R1 → R2 → R3, each by a human [R1 ledger row 5; I Q1, Q15, A4; the correction recorded 2026-10-22] | Two exit states and a `complete` stage; then (alignment run) R2 entry = R1 merged, branch and PR on `main` | One exit state (D-20, F-45); live gates in stage `merge`; E-1..E-3 require R1's `APPROVE`, live gates passed, and the `release/r1-shadow` head; E-6 requires R1 merged before R2 merges; the R2 branch starts from `release/r1-shadow` and the PR is retargeted to `main` (T002, T139, T142); T145 evaluates the merge stage with the live gates; Q-3 resolved; RK-11 restored |
| 5 | The webhook replay defence ships complete in R1: body-SHA-256 dedupe, freshness guard, events as hints, secret hygiene with `GITEA_WEBHOOK_SECRET_PREVIOUS` for 7 days, digests kept 90 days; `normalized-event.v1` gains `body_sha256` and `stale` [R1 ledger row 2; R1 FR-025, FR-047] | R2 consumed no events | No change for `gitea-event-normalizer` in R2, with the reason (release-plan §5; §3 item 7); spec.md §Non-goals; the canary set covers every `SECRET_ENV_VARS` name, including both webhook secrets (G-OFF-18) |
| 6 | Zed endpoint shape (a): the local Ollama app signed in to ollama.com serves the cloud models; T112 only verifies model ids. L1 entry = SPEC-105 `local_unlock_evidence` for the cloud model plus the person's sign-off, then the same floor gates on `ollama-local`; L1 switches the profile model ids on the same provider [R1 §Clarifications round 1; R1 ledger row 7; 105 US2] | V-5 left (a) or (b) open; L1 had its own streak definition | F-35, V-5 (verify only), D-17, D-18; FR-036, FR-037; spec.md §Runtime compatibility; T004, T101, T106, T109 |
| 7 | The reviewer uses recorded evidence only, holds no keys, and posts its own `run-health.v1` as a separate marked comment; CI offline on every PR, live only manually; at most 3 rounds, then the person decides; `set_by` and signer `Cazador0`; the engineering-team report is in the private repository; creating Gitea webhooks is human-only; agents may not edit `.skill-policy.json`, criteria files, or `monitor-limits.json` [R1 §Clarifications; R1 ledger rows 8–10; 105 R-12] | The reviewer's environment and keys were not specified; the sign-off signer was open (Q-7) | D-28, D-29, F-44; FR-013, FR-035, FR-049; T127, T140; Q-7 resolved |
| 8 | "run-monitor for Rancher Desktop local containers", read from inside each container [answers recorded 2026-10-22] (earlier: the person did not choose to monitor their own machine [I Q19]) | `snapshot.py --host-metrics off` on local runs (alignment run) | D-27, FR-048: bench uses `run-monitor`'s target `local-container` (SPEC-105, R1) inside the container where the local runs happen; no socket, nothing else on the machine; T143, T144; Q-10 resolved |

Open after alignment: Q-2 (live Gitea). Resolved: Q-3, Q-7, Q-8 (the person's earlier decisions) and Q-1, Q-4, Q-5,
Q-6, Q-9, Q-10 (answers recorded 2026-10-22).
