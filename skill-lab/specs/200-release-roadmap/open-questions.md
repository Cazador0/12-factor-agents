# Open questions for the user: R1, R2, R3

**Roadmap**: [SPEC-200](spec.md) | **Created**: 2026-10-22 | **Status**: Answered except OQ-02, OQ-06, and OQ-14's `signer` default (2026-10-22)

This is the single list to answer. It merges the questions in the three release syntheses
([SPEC-201 §5](../201-release-shadow/synthesis.md), [SPEC-202 §7](../202-release-agent-implementation/synthesis.md),
[SPEC-203 §7](../203-release-guarded-autonomous/synthesis.md)), drops duplicates, and orders them by what they block.
Every question has a default. Work proceeds on the default until you answer, except where "Blocks" says otherwise.
No default ever turns a gate that did not run into a pass.

On 2026-10-22 you answered the intake `intakes/jev-live-benchmarking/intake.md` (cited as "intake Qn"), SPEC-105, and
the refinement of R1 (SPEC-201 §Clarifications, cited as "round 1", "set 1", "set 2"). Questions those answers settle are
marked **Resolved** with their source; where an answer differs from the earlier default, the answer applies. The
release-alignment answers at the end of this file (rounds 1–2, cited as "answers recorded 2026-10-22") and the
correction below them resolve OQ-05 (stacked PRs), OQ-07..OQ-09, OQ-11..OQ-13, OQ-17..OQ-20, and OQ-22..OQ-26.

Priority:

- **P1**: blocks a release step (PR, merge) or a release's "complete" state.
- **P2**: blocks a milestone or a live capability (local inference, live Gitea, promotion, headless runners), or changes
  release sequencing.
- **P3**: has a safe default and blocks nothing.

## Summary

| ID | Priority | Question (short) | Blocks | Default | Merges |
|---|---|---|---|---|---|
| OQ-01 | P1 | When are `ollama.com` and `api.typesafe.ai` reachable, with keys set? | **Resolved**: you allowlist both hosts and set both keys (intake A7, D5). The live run is now the R1 merge gate (intake Q1, Q15), so it blocks the **R1 merge** until it passes | — ("merged, live-pending" withdrawn) | R1 Q1 |
| OQ-02 | P1 | Create `Cazador0/skill-factory` and grant push access | **R1 step 6** (T140), so every PR after it | Wait; T140 stays open | R1 Q3 |
| OQ-03 | P1 | Are GitHub Actions allowed on the private repo? | **Resolved**: offline CI on every PR; live benchmarks only when started manually (round 1) | — | R1 Q5 |
| OQ-04 | P1 | Is the live-run volume within your Ollama and TypeSafe plans? Cost cap? | **Resolved**: report cost only, no cap (intake Q7); cost from your price table, usage only when a price is missing (SPEC-105 FR-014) | — | R1 Q8, R3 Q-9 |
| OQ-05 | P2 | Confirm one sequencing rule for every release pair | **Resolved** (stacked PRs, intake A4; correction recorded 2026-10-22): R1 merges only after one fully passing counting live run; R2's branch starts from `release/r1-shadow` once R1 has `APPROVE` and its live gates passed, its PR targets `release/r1-shadow` and is retargeted to `main` when R1 merges; R3 stacks on R2 the same way; merges in order R1 → R2 → R3, each by a human | — | R2 Q-3, Q-5 (sequencing part); R3 Q-4 |
| OQ-06 | P2 | Live Gitea: URL, sandbox, bot accounts, webhook, branch protection, tracking issue | RT-01 (live writes, R2), RT-02 (live auto-merge, R3), P-7 (promotion) | Test double only; live writes refused | R2 Q-2, R3 Q-2 |
| OQ-07 | P2 | Which local model(s), and how much VRAM? | **Resolved** (answers recorded 2026-10-22): decided at unlock time; list what fits the GPU at 32k context with tool support, verify it, and you pick. Still gates **M-L1** until you pick | — | R2 Q-1 |
| OQ-08 | P2 | Accept the promotion thresholds and the 7-day observation lag? | **Resolved** (answers recorded 2026-10-22): the listed values stand | — | R3 Q-1, Q-11 |
| OQ-09 | P2 | May role runners start headless `claude -p` sessions with edit rights? | **Resolved** (answers recorded 2026-10-22): no; outbox plus human-started sessions | — | R3 Q-7 |
| OQ-10 | P3 | Which Ollama Cloud model, and which Zed endpoint shape? | **Resolved**: one model for all roles, chosen by SPEC-105 research R-14 at SPEC-201 T112 (intake Q11); endpoint: the local Ollama app signed in to ollama.com (round 1) | — | R1 Q2 |
| OQ-11 | P3 | Local parity: 3 consecutive local runs, or 1? | **Resolved** (answers recorded 2026-10-22): 3 | — | R2 Q-4 |
| OQ-12 | P3 | Enable L1 early on the R1 suite? | **Resolved** (answers recorded 2026-10-22): L1 is measured on the suite installed at unlock time | — | R2 Q-9 |
| OQ-13 | P3 | Dispatch limits and merge-schedule TTL | **Resolved** (answers recorded 2026-10-22): 1 PSE (max 2), 10/day (max 20), 30 min | — | R3 Q-3 |
| OQ-14 | P3 | Which identity string names you in human-owned records? | **Resolved** for `set_by`: `Cazador0` (set 1). `signer` in `human-signoff.v1` keeps its default | `signer.name` from `git config user.name` plus `github_login: Cazador0` | R1 Q6, R2 Q-7 |
| OQ-15 | P3 | May the reviewer session hold the live keys for a spot check? | **Resolved**: no; recorded evidence only (round 1) | — | R1 Q4 |
| OQ-16 | P3 | Include your research report in the factory repo? | **Resolved**: include it (set 1) | — | R1 Q7 |
| OQ-17 | P3 | Low-risk paths for auto-merge | **Resolved** (answers recorded 2026-10-22): `docs/**` and Markdown outside agent and policy paths, ≤ 400 changed lines; no built-in additions | — | R3 Q-5 |
| OQ-18 | P3 | Demotion triggers and escaped-defect labelling | **Resolved** (answers recorded 2026-10-22): all 5 triggers; `Caused-by: #<pr>`; unattributed labels also demote | — | R3 Q-6, Q-10 |
| OQ-19 | P3 | Auto-merge style | **Resolved** (answers recorded 2026-10-22): merge commit | — | R3 Q-8 |
| OQ-20 | P3 | One Gitea issue per task, or grouped issues? | **Resolved** (answers recorded 2026-10-22): one per task | — | R2 Q-6 |
| OQ-21 | P3 | Live benchmark artefacts in PR bodies? | **Resolved**: the release PR carries the live run's report (per-skill and catalog results, unsure and flagged cases, tokens and cost basis, suite digest), and every result file is committed in the private repo (intake Q2, Q9, Q16; SPEC-105 FR-018) | — | R2 Q-8 |
| OQ-22 | P3 | Should run monitoring watch your own machine during R2's local parity runs? | **Resolved** (answers recorded 2026-10-22): run-monitor for your Rancher Desktop local containers, from inside each container (target kind `local-container`: that container's own cgroup CPU and memory limits and use, disk free, process count; no Docker or containerd socket; nothing else on the machine) | — | R2 Q-10 |
| OQ-23 | P3 | May L1 (local enablement) run alongside R3? | **Resolved** (answers recorded 2026-10-22): yes; L1 blocks neither the R2 merge nor R3 | — | R2 Q-5 (L1 part) |
| OQ-24 | P2 | How many counting live runs before R3 may merge: 3 in a row, or 1 as for R1? | **Resolved** (answers recorded 2026-10-22): 3 consecutive counting runs on one model and the R3 suite (SPEC-203 G-LIVE-08) | — | R3 Q-12 |
| OQ-25 | P3 | Should run monitoring watch the R3 webhook gateway host (possibly your machine)? | **Resolved** (answers recorded 2026-10-22): the gateway runs in a Rancher Desktop local container, and run-monitor watches that container from inside it on every reconcile tick (target kind `local-container`); nothing else on the machine | — | R3 Q-13 |
| OQ-26 | P2 | Promotion criterion P-8: streak on the profiles' model, and demotion on a later failing run? | **Resolved** (answers recorded 2026-10-22): (a) the installed profiles' model; (b) no new demotion trigger, hold re-promotion only | — | R3 Q-14 |

## P1: blocks a release step or a release's "complete" state

### OQ-01 Network and keys for live runs (resolved)

- **Question**: When will `ollama.com` and `api.typesafe.ai` be reachable from the session that runs benchmarks, with
  `OLLAMA_API_KEY` and `TYPESAFE_API_KEY` (or its alias `JEV_API_KEY`) set?
- **Answer**: you allowlist both hosts and add both keys as environment secrets (intake A7). There is no calendar
  deadline: the first live gate run happens as soon as they are in place (intake D5, confirmed by Q17).
- **Consequence**: the first live run decides whether the R1 PR is ready (intake Q1), and one fully passing,
  counting run is enough for R1 (intake Q15). The live gates therefore block the **R1 merge** until they pass, and
  the earlier default ("merge as merged, live-pending; follow-up evidence PR") is withdrawn. `not_run` still never
  counts as `pass`, and nothing is fabricated or replayed in its place.

### OQ-02 The factory repository

- **Question**: Please create `Cazador0/skill-factory` (private) with an initial commit on `main` (a README is enough)
  and attach it to the build session with push access. Alternatively, authorize the orchestrator to push a bootstrap
  commit to an empty `main`. If this is already done, confirm that the session can push; T140 checks with
  `git ls-remote` before it pushes.
- **Why it matters**: every release PR is opened on this repository. R1 targets `main`; R2 is stacked on
  `release/r1-shadow` and R3 on `release/r2-agent-implementation`, each retargeted to `main` when the previous release
  merges, so all three PRs wait on it.
- **Blocks**: R1 step 6 (T140), and therefore R1 steps 7 and 8 and the PR steps of R2 and R3.
- **Recommended default**: wait. T140 stays open, and steps 1–5 continue.

### OQ-03 GitHub Actions on the private repository (resolved)

- **Question**: Are GitHub Actions allowed on `Cazador0/skill-factory`, within your minutes budget?
- **Answer** (round 1): offline CI on every PR (validate, tests on Python 3.9 and the current Python, deterministic
  benchmarks); live benchmarks only when started manually. The workflow holds no merge step. G-POST-01 requires this
  CI to be green on the PR head before the human merge.

### OQ-04 Live-run volume and cost (resolved)

- **Question**: Is the live-run volume within your Ollama and TypeSafe plans? Should a cost cap apply?
- **Answer**: report cost only, with no spending cap (intake Q7, delegated). Cost comes from a price table you maintain
  (`skill-lab/benchmarks/prices.json`); a run with any missing price reports token usage only (SPEC-105 FR-014 and its
  plan refinement). Live runs happen on demand and once per release PR (intake Q8).
- **Volume for reference**: one R1 gate run covers at least 70 agentic cases (14 skills × 5, at most 2 repair turns
  each), at least 140 routing cases (14 × 10), about one Jev request per agentic case plus at most one re-ask per
  uncertain judgment, and 14 advisory health assessments. R1 needs one counting run; L1 needs 3 consecutive counting
  runs on the same model and suite. R2 and R3 volumes are in their specs.

## P2: blocks a milestone or a live capability, or changes sequencing

### OQ-05 One sequencing rule for every release pair (resolved)

- **Question**: Which sequencing rule applies between releases?
- **Answer** (your decisions, 2026-10-22, with the correction recorded below the answers): R1 merges only after one
  fully passing, counting live run, with the live gates at the merge stage; there is no "merged, live-pending" state.
  The releases ship as **stacked PRs** (intake A4): R2's branch is created from `release/r1-shadow` once R1 has an
  independent `APPROVE` and its live gates passed; the R2 PR targets `release/r1-shadow` and is retargeted to `main`
  when R1 merges. R3 stacks on R2 the same way (it starts after R2's `APPROVE` and R2's live gates passed). Merges
  happen in order R1 → R2 → R3, each by a human, and each release's own merge still requires its own live gates. A
  live gate that has not run blocks like a failed one. No project is promoted to `guarded-autonomous` before R3 is
  merged.
- **Consequence**: the earlier rule 1 ("merge on offline gates while live gates are pending") is withdrawn, and so is
  the alignment run's "branch from `main` after the previous release merges", which contradicted intake A4. A PR whose
  diff changes on retargeting is reviewed again.

### OQ-06 Live Gitea

- **Question**: For live use, please provide:
  1. the Gitea instance URL (28.x);
  2. a sandbox repository `<owner>/skill-lab-smoke`, whose default branch carries a committed `.skill-policy.json` at
     `agent-implementation`;
  3. bot accounts: `agent-lead` and `agent-pse` (they may be one account), `agent-review` (must be separate), and for R3
     a `system` account that is not a repository admin and differs from the PSE account (or confirm the Lead account,
     if it differs from PSE). Each needs a least-scope token; the exact scope names are verified at SPEC-202 T003;
  4. for R3, the webhook (a human-only action) pointing at the gateway URL, with its secret in `GITEA_WEBHOOK_SECRET`,
     and the gateway host allowed in Gitea's `[webhook] ALLOWED_HOST_LIST` if your instance needs that (SPEC-203 V-7);
  5. branch protection on each target repository meeting BP-01..BP-12, including "auto-merge allowed" (BP-09) for R3;
  6. for R3, an autonomy tracking issue.
- **Why it matters**: the client refuses consequential writes to any non-loopback host until the staged smoke test has
  passed on the sandbox for that host and Gitea version (RT-01), and refuses live auto-merge until the `merge` smoke
  stage has passed (RT-02). Separate Review and system identities make independence and "an author never triggers its
  own merge" hold at the forge, not only in prompts.
- **Blocks**: RT-01 and every live Gitea write (R2), RT-02 and every live auto-merge (R3), promotion criterion P-7. Not
  any release PR.
- **Recommended default**: the Gitea test double only; live writes and live auto-merge stay refused.

### OQ-07 Local model and GPU (resolved)

- **Question**: Which local Ollama model(s) should the Lead, PSE, and Review profiles use, and exactly how much VRAM does
  the GPU have? The model must support tool calls in Zed and fit fully on the GPU with a 32k context.
- **Why it matters**: L1's local streak runs the same suite on `ollama-local`. `skill-lab doctor` refuses a context below
  32,768 and reports GPU residency. ADR-0003's 32k budget assumes a GPU under 24 GB. The foundation template lists
  `gpt-oss:20b` and `qwen3:8b` as examples only; neither is verified on your GPU.
- **Blocks**: milestone M-L1 only.
- **Recommended default**: none. The plans do not pick a model they cannot verify.
- **Answer** (answers recorded 2026-10-22): decide at unlock time. List what fits the GPU at 32k context with tool support, verify it
  (`skill-lab doctor --runtime ollama-local`), and you pick. M-L1 waits for your pick.

### OQ-08 Promotion thresholds and observation lag (resolved)

- **Question**: Do you accept these promotion criteria for moving a project to `guarded-autonomous`?
  - P-1: at least 30 agent PRs, merged by a human at `agent-implementation` at least 7 days before the scorecard, whose
    recorded uncapped decision was `AUTO_MERGE`.
  - P-2: 0 escaped defects and 0 reverts in the window.
  - P-3: at most 1 human disagreement with an uncapped `AUTO_MERGE`.
  - P-4: first-pass approval rate at least 0.70 over at least 30 reviewed agent PRs.
  - P-6: 0 unauthorized actions that were not blocked, and at most 0.2 blocked attempts per accepted issue.
  - The observation lag is 7 days.
- **Why it matters**: the thresholds are code constants on a critical path, so changing them later needs a PR and an
  ADR. P-1 follows the rule of three: 0 failures in 30 trials bounds the per-PR failure rate at about 10 % with 95 %
  confidence. The lag lets defects surface before a PR counts.
- **Blocks**: milestone M-PROMO only (not the R3 PR).
- **Recommended default**: the values above.
- **Answer** (answers recorded 2026-10-22): the thresholds and the 7-day lag stand as listed.

### OQ-09 Headless role runners (resolved)

- **Question**: May role runners start headless `claude -p` sessions with edit permissions in a target repository (PSE
  remediation and rebase, Review re-review), once their flags are verified (SPEC-203 V-10)?
- **Why it matters**: without it, every dispatch is written to an outbox and a human opens the prompt in a Zed thread
  with the matching profile. The event loop still works, but each session needs a person. A runner holds only its
  role's token, and every write still passes policy, lease, identity, and scope checks.
- **Blocks**: the `claude-cli` runner only.
- **Recommended default**: no. Runner `none`, human-started sessions.
- **Answer** (answers recorded 2026-10-22): no headless edit sessions; outbox plus human-started sessions.

### OQ-24 Live runs before the R3 merge (resolved)

- **Question**: Must R3 pass 3 consecutive counting live runs on one model and the R3 suite before it merges
  (`benchmark-streak.v1` length ≥ 3, SPEC-203 G-LIVE-08), or one fully passing counting run, as for R1?
- **Why it matters**: you settled one fully passing run for R1 (intake Q15) and said the 3-run streak gates the
  local-inference unlock. R3 is the first release where model output can lead to an unattended merge, so its plan
  keeps the stricter reading until you decide.
- **Blocks**: nothing with the default; it sets how many live runs the R3 PR waits for.
- **Recommended default**: 3 consecutive counting runs (SPEC-203 Q-12, D-24).
- **Answer** (answers recorded 2026-10-22): three in a row, the same bar that unlocks local inference. G-LIVE-08 stays.

### OQ-26 Promotion evidence from the benchmark streak (resolved)

- **Question**: (a) Must the streak behind promotion criterion P-8 be on the model the project's installed profiles
  use, or is the factory's gate model enough? (b) Should a failing counting run or an unstable case after a promotion
  demote the project automatically, instead of only holding re-promotion?
- **Why it matters**: P-8 reads SPEC-105's `benchmark-streak.v1` (SPEC-203 D-30); a streak on another model says little
  about the model the project actually runs.
- **Blocks**: **M-PROMO** only.
- **Recommended default**: (a) the installed profiles' model; (b) no new demotion trigger: report it and hold
  re-promotion (SPEC-203 Q-14).
- **Answer** (answers recorded 2026-10-22): (a) the streak must be on the installed profiles' model; (b) no extra demotion trigger for a
  failing run or an unstable case after promotion.

## P3: safe defaults, nothing blocked

### OQ-10 Cloud model and Zed endpoint shape (resolved)

- **Question**: (a) Which Ollama Cloud model(s) should the Lead, PSE, and Review profiles default to? (b) Which Zed
  endpoint shape?
- **Answer**: (a) one model for all profiles (intake Q11, delegated), chosen when the network is allowlisted by SPEC-105
  research R-14: the largest general model whose Ollama page lists tool support, from `https://ollama.com/api/tags`,
  recorded with its date in SOURCES.md and `cloud-models.json` at SPEC-201 T112. (b) The local Ollama app signed in to
  ollama.com (`http://localhost:11434`) serves cloud models in R1 (round 1: "one provider setting serves cloud now and
  local later"). T112 verifies the model ids only; it does not choose the endpoint. L1 later switches the profile model
  ids to local models on the same provider.

### OQ-11 Local parity runs (resolved)

- **Question**: Should local parity need 3 consecutive local runs (the same bar as cloud) or 1?
- **Why it matters**: one pass at non-zero temperature proves little, and the roadmap's "reliable" is defined by 3 runs.
- **Blocks**: nothing (it sets M-L1's duration).
- **Recommended default**: 3.
- **Answer** (answers recorded 2026-10-22): 3 consecutive local runs.

### OQ-12 L1 on the R1 suite (resolved)

- **Question**: Do you want L1 evaluated early on the R1 suite? Such a record goes stale when R2's suite lands and must
  be earned again.
- **Why it matters**: R1's runs count toward the L1 streak only for the R1 suite's digest (SPEC-202 D-17).
- **Blocks**: nothing.
- **Recommended default**: evaluate on whatever suite is installed when 3 eligible runs exist; `install --check` flags a
  stale record.
- **Answer** (answers recorded 2026-10-22): L1 is measured on the suite installed at unlock time.

### OQ-13 Dispatch limits and merge-schedule TTL (resolved)

- **Question**: Are these limits acceptable: 1 concurrent PSE session (maximum 2), 10 dispatches a day (maximum 20), and
  a merge-schedule TTL of 30 minutes (range 5–60)?
- **Why it matters**: one PSE session matches R2's single-host lease authority. 10 a day bounds cost and human recovery
  load while cost per issue is unmeasured. 30 minutes is three times the 10-minute CI target, so a healthy re-run
  finishes inside it and a stuck one becomes a human decision.
- **Blocks**: nothing.
- **Recommended default**: these values.
- **Answer** (answers recorded 2026-10-22): these values: 1 PSE (max 2), 10 a day (max 20), merge schedule expires after 30 minutes.

### OQ-14 Your identity in human-owned records (resolved for `set_by`)

- **Question**: Which identity string should name you in `.skill-policy.json` (`set_by`) and in `human-signoff.v1`
  (`signer`)?
- **Answer** (set 1): `set_by: Cazador0`. The `signer` default stands until you say otherwise: `signer.name` from
  `git config user.name` plus `github_login: Cazador0`.

### OQ-15 Live keys in the reviewer session (resolved)

- **Question**: May the reviewer cloud session's environment hold `OLLAMA_API_KEY` and `TYPESAFE_API_KEY`?
- **Answer** (round 1): no. The reviewer checks committed live-run results and recordings only, does not re-run live
  cases, holds no keys, and says so in its verdict. It also posts its own `run-health.v1` report as a separate marked
  PR comment (intake Q23).

### OQ-16 Research report in the factory repository (resolved)

- **Question**: Should `skill-lab/docs/research/engineering-team-report.md` be exported into the private factory
  repository?
- **Answer** (set 1): include it.

### OQ-17 Low-risk paths for auto-merge (resolved)

- **Question**: The default low-risk set is `docs/**` and Markdown outside agent and policy paths, with at most 400
  changed lines. Should any project also treat "non-sensitive UI" paths as low risk (the report's example)?
- **Why it matters**: only low-risk PRs auto-merge. 400 lines is about 4k tokens, an eighth of the 32k context that
  bounds local models, so one review round can hold the whole diff plus the spec.
- **Blocks**: nothing.
- **Recommended default**: no built-in additions; a project adds paths through a human-merged policy change, and never
  where a built-in critical or high pattern matches.
- **Answer** (answers recorded 2026-10-22): docs-only auto-merge paths, at most 400 changed lines; no built-in additions.

### OQ-18 Demotion triggers and escaped-defect labelling (resolved)

- **Question**: (a) Keep the three demotion triggers beyond your rule (escaped defect, revert): containment breach,
  gate-integrity violation, and lease violation? (b) Humans label escaped defects `incident/escaped-defect` with a
  `Caused-by: #<pr>` line in the issue body; should an unattributed defect label also demote?
- **Why it matters**: each extra trigger means a guard failed. Demotion is the safe direction, and only a human
  re-promotes.
- **Blocks**: nothing.
- **Recommended default**: keep all five triggers; use the `Caused-by:` convention; unattributed labels also demote.
- **Answer** (answers recorded 2026-10-22): all five triggers, the `Caused-by:` convention, and unattributed labels also demote.

### OQ-19 Auto-merge style (resolved)

- **Question**: Merge commit or squash for auto-merges?
- **Why it matters**: a merge commit keeps the PR's commits, which revert attribution and post-merge audits use.
- **Blocks**: nothing.
- **Recommended default**: merge commit.
- **Answer** (answers recorded 2026-10-22): merge commits.

### OQ-20 Issue granularity (resolved)

- **Question**: One Gitea issue per Spec Kit task (the Spec Kit `github` extension's behaviour, which R1's dry run
  follows), or grouped issues as in the report's example?
- **Why it matters**: it decides how many issues, leases, and PRs a feature produces.
- **Blocks**: nothing in R2, which only applies R1's plans.
- **Recommended default**: one issue per task.
- **Answer** (answers recorded 2026-10-22): one Gitea issue per task.

### OQ-21 Live artefacts in PR bodies (resolved)

- **Question**: Should PR bodies include live benchmark artefacts (Jev request IDs, token usage), or digests only?
- **Answer**: scores are posted on the release PR for you and the reviewer (intake Q2), every result file is committed
  in the private repository (intake Q9), and tokens and cost are reported on every run (intake Q16). The release PR
  therefore carries the live run's report (per-skill and catalog results, unsure and flagged cases, unstable cases,
  tokens and cost basis, degraded or outage status, suite digest; SPEC-105 FR-018), and the full results stay in the
  repository, referenced by digest. Only skill-factory's own fixtures, skill instructions, and model outputs are ever
  sent to the live services (intake Q4).

### OQ-22 Monitoring your own machine during local parity runs (resolved)

- **Question**: If R2's local parity runs (L1, `--runtime ollama-local`) happen on your machine, should `run-monitor`
  also record that machine's CPU, memory, disk, and processes?
- **Why it matters**: the monitoring you chose watches the benchmark container, the model sessions under test, and the
  reviewer session (intake Q19); you did not choose your own machine. Local parity runs may run where the local models
  are, which could be your machine.
- **Blocks**: nothing with the default; it concerns M-L1's local runs only, never a release PR.
- **Earlier default** (withdrawn): no machine monitoring (`snapshot.py --host-metrics off`).
- **Answer** (answers recorded 2026-10-22): "run-monitor for Rancher Desktop local containers", read from inside each container. R2's local
  parity runs happen inside one of your Rancher Desktop local containers; bench calls `run-monitor` `snapshot.py
  --target local-container` there after each skill. It reads that container's own cgroup v2 CPU and memory limits and
  use (`/sys/fs/cgroup`: `cpu.stat`, `cpu.max`, `memory.current`, `memory.max`; cgroup v1 fallback; `null` plus a note
  when unavailable), plus disk free and process count as seen inside the container. It opens no Docker or containerd
  socket and reads nothing else on the machine (SPEC-105 R-9; SPEC-202 FR-048, D-27). The `--host-metrics off` option
  is withdrawn.

### OQ-23 L1 alongside R3 (resolved)

- **Question**: May L1 (local inference enablement, milestone M-L1) run alongside R3, blocking neither the R2 merge nor
  R3?
- **Why it matters**: L1's entry is settled (SPEC-105's `local_unlock_evidence` for the cloud model plus your sign-off,
  then the floor gates on `--runtime ollama-local`); only the overlap with R3 was open.
- **Blocks**: nothing.
- **Recommended default**: yes (SPEC-202 Q-5).
- **Answer** (answers recorded 2026-10-22): yes. L1 can run alongside R3 and blocks neither the R2 merge nor R3.

### OQ-25 Monitoring the R3 webhook gateway host (resolved)

- **Question**: R3's live webhook gateway is a service you run, possibly on your machine. Should `run-monitor` watch
  the gateway host?
- **Why it matters**: the monitoring you chose watches the benchmark container, the model sessions under test, and the
  reviewer session (intake Q19), not your machine.
- **Blocks**: nothing.
- **Earlier default** (withdrawn): no; `run-monitor` gets no R3 change.
- **Answer** (answers recorded 2026-10-22): "run-monitor for Rancher Desktop local containers". The gateway runs inside one of your Rancher
  Desktop local containers. On every reconcile tick, `normalize.py serve` runs `run-monitor` `snapshot.py --target
  local-container` as a subprocess inside that container and keeps the `run-health.v1` report in its state folder; the
  report advises and never changes a gateway decision. Only that container's own figures are read; no Docker or
  containerd socket, nothing else on the machine (SPEC-203 FR-058, D-29).

## Source mapping

| Release question | Consolidated as |
|---|---|
| SPEC-201 Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8 | OQ-01, OQ-10, OQ-02, OQ-15, OQ-03, OQ-14, OQ-16, OQ-04 |
| SPEC-202 Q-1, Q-2, Q-3, Q-4, Q-5, Q-6, Q-7, Q-8, Q-9, Q-10 | OQ-07, OQ-06, OQ-05, OQ-11, OQ-05 (sequencing) and OQ-23 (L1 alongside R3), OQ-20, OQ-14, OQ-21, OQ-12, OQ-22 |
| SPEC-203 Q-1, Q-2, Q-3, Q-4, Q-5, Q-6, Q-7, Q-8, Q-9, Q-10, Q-11, Q-12, Q-13, Q-14 | OQ-08, OQ-06, OQ-13, OQ-05, OQ-17, OQ-18, OQ-09, OQ-19, OQ-04, OQ-18, OQ-08, OQ-24, OQ-25, OQ-26 |

## Answers recorded 2026-10-22 (release alignment, rounds 1–2)

The person's answers, verbatim where they typed their own words. They resolve the questions named.

- Q: Agents may not edit the per-skill criteria files, yet R1 planned one per skill. Who writes them? → A: Ship none in R1: R1 ships no per-skill criteria files; scoring falls back to the shared defaults (the floor); later only the person adds a file to raise a skill's bar.
- Q: Should run-monitor also watch your own machine when work runs there (R2 local-inference runs, R3 webhook gateway)? → A: "run-monitor for Rancher Desktop local containers". (Resolves OQ-22, OQ-25.)
- Q: How should run-monitor read your Rancher Desktop local containers? → A: From inside each container: run-monitor runs inside the container doing the work and reads that container's own CPU and memory limits and use; no Docker or containerd socket access; nothing else on the machine is read.
- Q: How many fully passing live runs must the R3 PR wait for before it can merge? → A: Three in a row (the same bar that unlocks local inference). (Resolves OQ-24.)
- Q: Which local model should the profiles use once local inference unlocks? → A: Decide at unlock time: list what fits the GPU at 32k context with tool support, verify it, and the person picks. (Resolves OQ-07.)
- Q: Which R2 defaults should stay as written? → A: All four: three local parity runs (OQ-11); L1 measured on the suite installed at unlock time (OQ-12); one Gitea issue per task (OQ-20); L1 can run alongside R3 and blocks neither the R2 merge nor R3 (OQ-23).
- Q: Which R3 defaults should stay as written (set 1)? → A: All four: the promotion thresholds and 7-day lag (OQ-08); no headless edit sessions, outbox plus human-started sessions (OQ-09); dispatch limits 1 PSE (max 2), 10/day (max 20), merge schedule expires after 30 min (OQ-13); docs-only auto-merge paths, at most 400 changed lines (OQ-17).
- Q: Which R3 defaults should stay as written (set 2)? → A: All four: five demotion triggers with the `Caused-by:` convention and unattributed labels also demoting (OQ-18); merge commits (OQ-19); the promotion streak must be on the installed profiles' model (OQ-26a); no extra demotion trigger for a failing run or unstable case after promotion (OQ-26b).

Correction (orchestrator, 2026-10-22): the release-alignment run of 2026-10-22 changed R2 and R3 to branch from `main` after the previous release merges. That contradicted the person's decision that the releases ship as **stacked PRs** (intake A4). Restored: R2's branch is created from `release/r1-shadow` once R1 has an APPROVE verdict and its live gates passed, its PR targets `release/r1-shadow`, and it is retargeted to `main` when R1 merges. R3 stacks on R2 the same way. Merges happen in order R1 → R2 → R3, each by a human.
