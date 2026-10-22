# Synthesis: R2 Agent implementation

**Spec ID**: SPEC-202 | **Delivery step**: 2 (Synthesize) | **Created**: 2026-10-22

This document collects what R2 depends on, what was decided, and what is still open. Citations use these keys:

- **[R §x]**: `skill-lab/docs/research/engineering-team-report.md`, section heading x.
- **[S x]**: `skill-lab/docs/research/SOURCES.md`, section x.
- **[C §n]**: `skill-lab/docs/CONVENTIONS.md`, section n.
- **[RM]**: `skill-lab/specs/200-release-roadmap/spec.md`.
- **[R1 x]**: `skill-lab/specs/201-release-shadow/spec.md` or its `release-plan.md`, section or requirement x.
- **[K name]**: the canonical contract `skill-lab/contracts/schemas/<name>.v1.schema.json`, as written on 2026-10-22.
- **[Z page]**: the Zed docs page (zed-industries/zed `docs/src/ai/`) downloaded for SOURCES.md.
- **[O page]**: the Ollama docs page downloaded for SOURCES.md.

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
  in [0.35, threshold), fail below 0.35; uncertain counts as fail and is flagged `needs_human` [C §5].
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
  comment field. [K merge-decision] gates are `pass | fail | not_run`.

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
  with gate IDs `G-(OFF|LIVE|POST)-NN` and live thresholds: per skill ≤ 1 failed agentic case (`bench.agentic.failed`),
  guardrail 1.0, per skill ≤ 1 misrouted trigger case (`bench.trigger.failed`), catalog trigger ≥ 0.90, 0 errored or
  skipped [R1 §Release gates]. (SPEC-201's first draft used rates 0.67 and 0.83; the cross-release consistency pass
  replaced them with counts after SPEC-203 X-2 showed that 2/3 = 0.667 fails 0.67.)
- **F-35** R1 ships `skill-lab/config/zed/local-ollama.disabled.jsonc` (`http://localhost:11434`, context ≥ 32,768),
  and `skill-lab install --inference local` exits 4 `LOCAL_INFERENCE_GATED` "(SPEC-202)". Every cloud profile uses
  provider `ollama` and a cloud model ID verified in `skill-lab/config/zed/cloud-models.json`, reached either through
  `api_url` `https://ollama.com` (shape b) or through a local daemon signed in to ollama.com at
  `http://localhost:11434` (shape a, the foundation template's current shape). R1's T112 decides which, keeping (a)
  when both work [R1 FR-039; R1 plan §Zed configuration shape]. That choice is the starting point for V-5.
- **F-36** R1 makes R2's clamp raise conditional: "R2 raises it, after adding base-branch verification of the policy
  file" [R1 §Non-goals]. R1's `policy.load` reads only the working-tree file (FR-001) and has no escape hatch (FR-005).
- **F-37** R1 records its live runs with the suite digest (SHA-256 over every SKILL.md and eval case file), commit, and
  `num_ctx`, through strict `notes[]` lines when `benchmark-run.v1` has no field for them. Those runs count toward the
  L1 streak "only for the same suite (SPEC-202 D-17)". R2 cannot be "complete" while R1 is live-pending
  [R1 release-plan §4; R1 record-run task]. R1 extends `merge-decision` with `uncapped_decision` and
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
| D-17 | L1 gate rules. An **eligible** cloud run has runtime `ollama-cloud` (SPEC-102 labels it `ollama-cloud-zed-emulation`), `jev_mode: live`, the agentic and trigger tiers for all 13 skills, a recorded suite digest, the same suite digest and model as its streak, and no skipped or errored case. It **passes** when G-LIVE-01..05 pass on that run alone. A failed, errored, or partially skipped run resets the streak; a run where a tier was skipped entirely (no network) is ignored. **Local parity** means the same gates on `ollama-local` with the same suite digest on 3 consecutive runs, in cloud-parity mode: no `format`, and the same bounded repair loop as `ollama-cloud` (F-38). Records are per `(runtime, model)`. R1's runs count exactly when their suite digest equals the suite being enabled (F-37) | User decision (3 consecutive live runs). "Reliable" applies to local the same way: the roadmap says the suite "then passes", and one pass at non-zero temperature proves little. The cloud runs cannot use `format` (F-22), so local runs that do would be graded on easier terms (F-38). A suite change or a model retirement invalidates old evidence | 1 local run (weaker, Q-4); counting replays (forbidden by [C §5]); counting R1 runs against a different suite |
| D-18 | Local enablement uses R1's `local-ollama.disabled.jsonc`, completed with the `Lead (local)`, `PSE (local)`, and `Review (local)` profiles and per-model `max_tokens: 32768`. `skill-lab install --runtime zed --inference local` keeps exiting 4 `LOCAL_INFERENCE_GATED` without an `ENABLED` record for the current suite digest and model. Cloud profiles stay installed. Provider coexistence (F-20, F-35: both use provider `ollama`) is decided by V-5 | ADR-0003 (about 32k context under 24 GB); F-20, F-21 (4096 and 4k defaults are too small; 64k does not fit this GPU class, ADR-0003); F-35 | Editing the user's live settings without the gate; dropping the cloud profiles |
| D-19 | Live Gitea smoke test: a staged command (`lead`, `pse`, `review`, `cleanup`; one identity per stage) against a sandbox repository named `^[^/]+/skill-lab-smoke(-[a-z0-9-]+)?$`. The client refuses consequential writes to a non-loopback host until a passing `smoke-report.v1` exists for that host and Gitea version (`LIVE_SMOKE_REQUIRED`) | F-17 drift risk; "test double now, live later"; the first live write happens in a sandbox | An optional, unenforced smoke test; smoking against the target repository |
| D-20 | Two exit states, as in R1. **Merged**: stage `merge` gates, an independent `APPROVE`, and a human merge. **Complete**: stage `complete` gates, plus R1 complete. The sequencing rule is the one SPEC-201 applies to R2 (SPEC-200 §Release index): R3 step 5 may start at R2's independent `APPROVE` with every `merge`-stage gate `pass`; R3 step 8 needs R2 merged; R3 complete needs R2 complete; no project is promoted before R3 complete (SPEC-203 P-8). A live gate that ran and failed is a missed gate and stops R3 from starting; `not_run` is pending | [C §9]; [RM] "R3 starts only after the R2 PR does" and "A release that misses a gate stays open; the next one does not start"; F-37. The first draft made R3 wait for R2 complete, which read `not_run` as "missed" for R2→R3 but not for R1→R2; one rule for both pairs removes that asymmetry, and promotion still waits for every live gate (OQ-05 lets the user choose the stricter rule) | Blocking the merge on the network allowlist; treating `not_run` as accepted; a stricter start rule for R2→R3 than for R1→R2 |
| D-21 | **Base-branch verification of the policy file** (F-36). Above `shadow`, `policy.load` also reads `.skill-policy.json` from `refs/remotes/origin/<base_branch>` (from `.skill-gitea.json`, default `main`; refs under `agent/` are refused) with read-only `gitrepo`. The effective level is the minimum of the working tree, the base ref, and the clamp. A missing or invalid base copy yields `shadow` plus `POLICY_NOT_ON_BASE`. R2 adds no `git fetch` helper: a stale `origin/<base>` can only keep a level that a human can still lower instantly in the working tree (the minimum wins), and a raise needs a human `git fetch`; SPEC-203 adds `gitrepo.fetch_base()` | Agents can only push `agent/*` branches (D-10 plus BP-01), so the base copy changes only through a human-merged PR. A raise in a worktree therefore has no effect | Trusting the working-tree file (any PSE could raise its own level); signing the policy file (key management out of scope) |
| D-22 | `complete_issue.py` sets `state/done` (`gitea.labels.set`) and only reports `CLOSE_PENDING`; it does not close the issue. PR bodies carry `Closes #<issue>`, so the human merge closes it (to verify, V-1) | F-31: `gitea.issue.close` is `guarded-autonomous`; re-levelling needs a human-merged ADR | Lowering the close action's level via an ADR (not worth the authority change for R2) |
| D-23 | The double's state logic moves into `_skillkit/gitea_memory.py` (vendored), so deterministic cases are hermetic through `--gitea-fixture`. R1's `skill-lab/lab/gitea_double.py` becomes a thin HTTP wrapper over it, with write endpoints. `gitea-fixture.v1` supersedes R1's seed format | Skills must run their own deterministic cases after `git subtree split` ([C §1]); one engine serves both transports | A second, write-capable double in the lab only (deterministic cases would need a server) |
| D-24 | R2's release gates live in `gates.json` in R1's `release-gates.v1` format, with R1's live thresholds re-justified for the R2 case counts. The smoke gate (RT-01) and the L1 gates sit outside `gates.json`, because they decide neither the merge nor completion | F-34; one gate engine for every release | A separate R2 gate runner |
| D-25 | ADR numbers 0201–0207 (R1 uses 0101–0109; R3 is expected to use 0301–0309) | Parallel planners must not collide | Global next-free numbering |
| D-26 | The 10 R2-changed skills keep model invocation enabled: no `disable-model-invocation: true`, although CONVENTIONS §2 would permit it now that they perform consequential writes. Writes stay behind the policy level, `--apply`, the runtime `always_confirm` rule on `--apply`, and the lease and identity checks | Zed leaves `disable-model-invocation` skills out of the catalog the model sees (F-38, Zed emulation), so the read-only R1 functions of these skills would stop routing, and G-LIVE-03 and G-LIVE-04 would fail by construction. The authority boundary is deterministic code, not whether a model may load instructions | Setting the flag (loses routing for planning and analysis; user-invoked only) |

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
7. **gitea-event-normalizer** is unchanged. R2 polls Gitea state at each step instead of consuming events.
8. **The policy machinery** (not a skill) gains base-branch verification (D-21), because R1 made it a precondition of
   raising the clamp.

## 4. Trade-offs

| Trade-off | Chosen | Cost accepted |
|---|---|---|
| Strong independence vs. setup effort | Two or three Gitea bot accounts (D-3) | The user creates accounts and tokens before live use |
| Lease safety vs. multi-host parallelism | Single-host authority (D-7) | No PSE parallelism across machines until R3 or later |
| Exact concurrency vs. schema stability | Integer version plus digest in `params` (D-5) | A small race window between re-read and write (RK-2) |
| Reliability evidence vs. time to local | 3 + 3 consecutive live runs plus sign-off (D-17) | L1 needs at least 6 full live agentic and trigger runs, plus Jev usage |
| Honest gates vs. merging early | Two exit states (D-20) | R2 and R3 completion, L1, and any promotion wait on the user's network allowlist; execution does not |
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
| RK-11 | A stacked PR retarget after R1 merges changes the diff | Re-review whenever the diff changes (step 8) | Orchestrator |
| RK-12 | A forged `human-signoff.v1` (the attestation is not authentication) | Impact limited to local inference on the user's machine; reversible; demoted by the next failing run | User |
| RK-13 | No `origin/<base>` ref (fresh clone, offline) makes the effective level `shadow` | Intended fail-closed behaviour; documented in the runbook (`git fetch origin <base>`) | User |

## 6. Facts to verify during execution (not assumed)

| ID | Fact needed | How and where it is verified | Blocks |
|---|---|---|---|
| V-1 | Gitea 28.2.0 endpoint paths, fields, and pagination for: issues (create, list with `state=all`, edit assignees, replace labels), comments, labels with `exclusive`, milestones, pulls (create, list, get, edit, commits, files, requested reviewers), reviews (event names), combined commit status, branch protections, `/version`, `/user`, `/swagger.v1.json`. Also whether `Closes #N` closes issues on merge into the base branch | T003: vendor Gitea's v28.2.0 swagger into `docs/research/vendor/` and add an endpoint table to SOURCES.md. If neither source nor a live instance is reachable, mark it "unverified" and rely on the live smoke test | Live use only (the double follows the table) |
| V-2 | Branch-protection field names for BP-01..BP-12. Candidates to confirm: `enable_push`, `enable_force_push`, `block_admin_merge_override`, `required_approvals`, `block_on_rejected_reviews`, `dismiss_stale_approvals`, `ignore_stale_approvals`, `block_on_outdated_branch`, `enable_status_check`, `status_check_contexts`, `block_on_official_review_requests`, `protected_file_patterns` | T003; recorded in `skills/merge-policy-gate/assets/branch-policy-map.json`; unknown fields report `unknown` | Correctness of live audits |
| V-3 | Whether Gitea supports conditional writes (ETag or `If-Match`) for issues | T003 (swagger). If yes, D-5 adds it; if no, D-5 stands | Nothing |
| V-4 | `claude -p` flags used by R1's `review_local.py` (`--output-format json`, `--json-schema`) in the installed version | T004 (`claude --help`), shared with SPEC-201's verification | CLI fallback only |
| V-5 | Zed with local and cloud Ollama together: (a) a local daemon signed in to ollama.com serves `<model>:cloud` through `http://localhost:11434`, or (b) Zed's OpenAI-compatible provider works against `https://ollama.com/v1` with tool calls | Start from R1's T112 finding (F-35). T004 verifies coexistence and records it in SOURCES.md. D-18 picks (a) if it works, else (b) | M-L1 only |
| V-6 | Ollama behaviour when a prompt exceeds `num_ctx` (truncation or error), and whether `/api/ps` reports context length and VRAM split | T004 and T111 (doctor probe) | M-L1 only |
| V-7 | The Codex sandbox's network default for `git push` and HTTPS to Gitea | T004 | Codex runtime notes |

## 7. Open questions for the user

Consolidated, deduplicated, and prioritised across all three releases in
[SPEC-200 open-questions.md](../200-release-roadmap/open-questions.md). Mapping: Q-1 → OQ-07, Q-2 → OQ-06, Q-3 → OQ-05,
Q-4 → OQ-11, Q-5 → OQ-05, Q-6 → OQ-20, Q-7 → OQ-14, Q-8 → OQ-21, Q-9 → OQ-12.

| ID | Question | Default if unanswered | Blocks |
|---|---|---|---|
| Q-1 | Which local Ollama model(s) should the Lead, PSE, and Review profiles use, and exactly how much VRAM does the GPU have? The model must support tool calls in Zed (`supports_tools`) and fit fully on the GPU with a 32k context | None. The plan does not pick a model it cannot verify | **M-L1** (not the R2 PR) |
| Q-2 | Gitea for live use: the instance URL, a sandbox repository `<owner>/skill-lab-smoke`, and bot accounts `agent-lead` and `agent-pse` (these may be one account) plus `agent-review` (must be separate), each with a personal access token holding the least scopes that allow the R2 actions (exact scope names to be verified, V-1) | Double only; the client refuses live writes (D-19) | **Live smoke test RT-01** and any live write |
| Q-3 | May R2 merge on the offline gates while live gates are pending ("merged, live-pending"), with R3 execution starting at R2's `APPROVE` and R3 completion and any promotion waiting for R2 "complete"? | Yes (D-20, same rule as R1 → R2) | Nothing |
| Q-4 | Local parity: 3 consecutive local runs (default, the same standard as cloud), or 1? | 3 (D-17) | Nothing |
| Q-5 | L1 runs in parallel with R3 and blocks neither the R2 merge nor R3. Correct? | Yes (roadmap sequencing diagram) | Nothing |
| Q-6 | Issue granularity: one Gitea issue per task (SPEC-201's dry-run behaviour, matching the Spec Kit extension), or grouped issues as in the report's example? | SPEC-201's behaviour; R2 only applies plans | Nothing in R2 |
| Q-7 | Which signer identity goes into `human-signoff.v1` (for example the GitHub login `Cazador0`)? | The `git config user.name` of whoever runs `skill-lab signoff create`, plus the GitHub login if given | M-L1 only |
| Q-8 | Should the R2 PR body include live benchmark artefacts (Jev request IDs, token usage), or only digests? | Digests and request IDs; no prompts or outputs that may contain repository content | Nothing |
| Q-9 | R1's live runs count toward the L1 streak only for an L1 evaluation of the **R1 suite** (D-17, agreed by SPEC-201). Do you want to enable L1 early on the R1 suite (the record goes stale when R2's suite lands, and must be re-earned), or wait for the R2 suite? | Evaluate on whatever suite is installed when 3 runs exist; `install --check` flags staleness | Nothing |
