# Open questions for the user: R1, R2, R3

**Roadmap**: [SPEC-200](spec.md) | **Created**: 2026-10-22 | **Status**: Open

This is the single list to answer. It merges the questions in the three release syntheses
([SPEC-201 §5](../201-release-shadow/synthesis.md), [SPEC-202 §7](../202-release-agent-implementation/synthesis.md),
[SPEC-203 §7](../203-release-guarded-autonomous/synthesis.md)), drops duplicates, and orders them by what they block.
Every question has a default. Work proceeds on the default until you answer, except where "Blocks" says otherwise.
No default ever turns a gate that did not run into a pass.

Priority:

- **P1**: blocks a release step (PR, merge) or a release's "complete" state.
- **P2**: blocks a milestone or a live capability (local inference, live Gitea, promotion, headless runners), or changes
  release sequencing.
- **P3**: has a safe default and blocks nothing.

## Summary

| ID | Priority | Question (short) | Blocks | Default | Merges |
|---|---|---|---|---|---|
| OQ-01 | P1 | When are `ollama.com` and `api.typesafe.ai` reachable, with keys set? | R1, R2, R3 **complete**; M-L1; M-PROMO. No merge | Merge as "live-pending"; run live as soon as reachable | R1 Q1 |
| OQ-02 | P1 | Create `Cazador0/skill-factory` and grant push access | **R1 step 6** (T140), so every PR after it | Wait; T140 stays open | R1 Q3 |
| OQ-03 | P1 | Are GitHub Actions allowed on the private repo? | **Every release merge** if "no" (G-POST-01) | Offline-only CI; live bench manual | R1 Q5 |
| OQ-04 | P1 | Is the live-run volume within your Ollama and TypeSafe plans? Cost cap? | Live gates if "no" | Proceed; report cost, do not gate on it | R1 Q8, R3 Q-9 |
| OQ-05 | P2 | Confirm one sequencing rule for every release pair | Nothing with the default; **R3 step 5** if you choose the stricter rule | Roadmap rule: next release starts at the previous `APPROVE` | R2 Q-3, Q-5; R3 Q-4 |
| OQ-06 | P2 | Live Gitea: URL, sandbox, bot accounts, webhook, branch protection, tracking issue | RT-01 (live writes, R2), RT-02 (live auto-merge, R3), P-7 (promotion) | Test double only; live writes refused | R2 Q-2, R3 Q-2 |
| OQ-07 | P2 | Which local model(s), and how much VRAM? | **M-L1** only | None | R2 Q-1 |
| OQ-08 | P2 | Accept the promotion thresholds and the 7-day observation lag? | **M-PROMO** only | The listed values | R3 Q-1, Q-11 |
| OQ-09 | P2 | May role runners start headless `claude -p` sessions with edit rights? | The `claude-cli` runner only | No (outbox; human-started sessions) | R3 Q-7 |
| OQ-10 | P3 | Which Ollama Cloud model, and which Zed endpoint shape? | Nothing | One model for all roles; endpoint shape per T112 | R1 Q2 |
| OQ-11 | P3 | Local parity: 3 consecutive local runs, or 1? | Nothing | 3 | R2 Q-4 |
| OQ-12 | P3 | Enable L1 early on the R1 suite? | Nothing | Evaluate on the installed suite | R2 Q-9 |
| OQ-13 | P3 | Dispatch limits and merge-schedule TTL | Nothing | 1 PSE (max 2), 10/day (max 20), 30 min | R3 Q-3 |
| OQ-14 | P3 | Which identity string names you in human-owned records? | Nothing | Forge username `Cazador0` | R1 Q6, R2 Q-7 |
| OQ-15 | P3 | May the reviewer session hold the live keys for a spot check? | Nothing | No | R1 Q4 |
| OQ-16 | P3 | Include your research report in the factory repo? | Nothing | Yes | R1 Q7 |
| OQ-17 | P3 | Low-risk paths for auto-merge | Nothing | `docs/**` and Markdown outside agent and policy paths, ≤ 400 lines | R3 Q-5 |
| OQ-18 | P3 | Demotion triggers and escaped-defect labelling | Nothing | Keep all 5 triggers; `Caused-by: #<pr>`; unattributed also demotes | R3 Q-6, Q-10 |
| OQ-19 | P3 | Auto-merge style | Nothing | Merge commit | R3 Q-8 |
| OQ-20 | P3 | One Gitea issue per task, or grouped issues? | Nothing | One per task | R2 Q-6 |
| OQ-21 | P3 | Live benchmark artefacts in PR bodies? | Nothing | Digests and request IDs only | R2 Q-8 |

## P1: blocks a release step or a release's "complete" state

### OQ-01 Network and keys for live runs

- **Question**: When will `ollama.com` and `api.typesafe.ai` be reachable from the session that runs benchmarks, with
  `OLLAMA_API_KEY` and `TYPESAFE_API_KEY` (or its alias `JEV_API_KEY`) set?
- **Why it matters**: every live gate (G-LIVE-*) needs both services. Without them the gates are `not_run`, and
  `not_run` never counts as `pass` (CONVENTIONS §9, ADR-0010). Nothing is fabricated or replayed in their place.
- **Blocks**: R1 complete (1 complete run), R2 complete (1 run of the R2 suite), R3 complete (3 consecutive runs,
  G-LIVE-07), milestone M-L1 (3 cloud runs before local), and M-PROMO (promotion criterion P-8 needs R3 complete). It
  blocks no merge.
- **Recommended default**: merge each release as "merged, live-pending". Run the live benchmark as soon as both hosts
  answer. Evidence from a run after a merge lands through a follow-up evidence-only PR (for R1:
  `release/r1-live-evidence` → `main`), reviewed the same way.

### OQ-02 The factory repository

- **Question**: Please create `Cazador0/skill-factory` (private) with an initial commit on `main` (a README is enough)
  and attach it to the build session with push access. Alternatively, authorize the orchestrator to push a bootstrap
  commit to an empty `main`. If this is already done, confirm that the session can push; T140 checks with
  `git ls-remote` before it pushes.
- **Why it matters**: every release PR targets this repository. R2 stacks on `release/r1-shadow` and R3 on
  `release/r2-agent-implementation`, so all three PRs wait on it.
- **Blocks**: R1 step 6 (T140), and therefore R1 steps 7 and 8 and the PR steps of R2 and R3.
- **Recommended default**: wait. T140 stays open, and steps 1–5 continue.

### OQ-03 GitHub Actions on the private repository

- **Question**: Are GitHub Actions allowed on `Cazador0/skill-factory`, within your minutes budget?
- **Why it matters**: G-POST-01 requires CI to be green on the PR head before a human merge. The planned workflow runs
  only offline gates (validate, sync, unit tests, deterministic bench, containment, export check) on Python 3.9 and the
  current Python for every push and PR. Its targets are about 10 minutes per Python version for R1 and about 20 minutes
  for R2's offline release check (SPEC-201 and SPEC-202 plan.md). The live-bench job runs only on manual dispatch with
  secrets, and the workflow holds no merge step.
- **Blocks**: the merge of every release if the answer is "no". Without CI, G-POST-01 is `not_run`, which blocks.
- **Recommended default**: enable the offline-only workflow; keep the live job manual. If Actions cannot be used, the
  alternative is a human-recorded run of the same commands accepted as CI evidence. That changes a gate, so it needs an
  ADR and your explicit choice.

### OQ-04 Live-run volume and cost

- **Question**: Is this volume within your Ollama and TypeSafe plans? Should a cost cap apply once a runner reports
  usage?
  - One R1 run: about 39 agentic model calls (plus at most 39 repair turns), at least 78 routing calls, and about 39 Jev
    requests.
  - One R2 run: about 52 agentic calls (R2 adds 13 agentic cases), at least 98 routing calls, about 52 Jev requests.
  - One R3 run: at least 76 agentic calls (plus at most one repair turn each), at least 118 routing calls, and at least
    76 Jev requests.
  - Minimum runs: R1 1, R2 1, R3 3 consecutive. M-L1 needs 3 consecutive cloud runs on one suite (R2's or R3's runs
    count when the suite digest matches) plus 3 local runs, which cost only Jev requests.
- **Why it matters**: the live gates and L1 cannot pass without these runs, and a failed or partial run restarts a
  3-run streak.
- **Blocks**: the live gates, if the answer is "no".
- **Recommended default**: proceed. Each recorded run reports Jev token usage and case durations; cost is reported, not
  gated, because no runtime reports cost reliably yet.

## P2: blocks a milestone or a live capability, or changes sequencing

### OQ-05 One sequencing rule for every release pair

- **Question**: Do you confirm this rule, which the three plans now share?
  1. A release merges on its offline gates while its live gates are pending ("merged, live-pending").
  2. The next release's step 5 starts once this release's PR has an independent `APPROVE` with every `merge`-stage gate
     passing. Its merge waits for this release's merge, and its "complete" waits for this release's "complete".
  3. A live gate that ran and **failed** stops the next release from starting; a live gate that has not run does not.
  4. No project is promoted to `guarded-autonomous` before R3 is complete. L1 runs in parallel with R3 and blocks
     neither the R2 merge nor R3.
- **Why it matters**: the drafts disagreed. SPEC-201 let R2 start at R1's `APPROVE`, while SPEC-202 made R3 wait for R2
  "complete". With the stricter rule, R3 cannot start until the network allowlist (OQ-01) lands. The roadmap says "R3
  starts only after the R2 PR has an APPROVE verdict", which is rule 2. Promotion still waits for every live gate, so the
  lenient start rule adds no autonomy risk.
- **Blocks**: nothing with the default. If you choose the stricter rule ("R3 waits for R2 complete"), R3 step 5 waits
  for OQ-01.
- **Recommended default**: the rule above.

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

### OQ-07 Local model and GPU

- **Question**: Which local Ollama model(s) should the Lead, PSE, and Review profiles use, and exactly how much VRAM does
  the GPU have? The model must support tool calls in Zed and fit fully on the GPU with a 32k context.
- **Why it matters**: L1's local streak runs the same suite on `ollama-local`. `skill-lab doctor` refuses a context below
  32,768 and reports GPU residency. ADR-0003's 32k budget assumes a GPU under 24 GB. The foundation template lists
  `gpt-oss:20b` and `qwen3:8b` as examples only; neither is verified on your GPU.
- **Blocks**: milestone M-L1 only.
- **Recommended default**: none. The plans do not pick a model they cannot verify.

### OQ-08 Promotion thresholds and observation lag

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

### OQ-09 Headless role runners

- **Question**: May role runners start headless `claude -p` sessions with edit permissions in a target repository (PSE
  remediation and rebase, Review re-review), once their flags are verified (SPEC-203 V-10)?
- **Why it matters**: without it, every dispatch is written to an outbox and a human opens the prompt in a Zed thread
  with the matching profile. The event loop still works, but each session needs a person. A runner holds only its
  role's token, and every write still passes policy, lease, identity, and scope checks.
- **Blocks**: the `claude-cli` runner only.
- **Recommended default**: no. Runner `none`, human-started sessions.

## P3: safe defaults, nothing blocked

### OQ-10 Cloud model and Zed endpoint shape

- **Question**: (a) Which Ollama Cloud model(s) should the Lead, PSE, and Review profiles default to? (b) Do you run the
  Ollama app signed in to ollama.com, so Zed reaches cloud models through `http://localhost:11434` (shape a, what the
  foundation template ships), or should Zed call `https://ollama.com` directly with `OLLAMA_API_KEY` (shape b)?
- **Why it matters**: one model for all three roles keeps the 3-run streaks cheaper and makes cloud and local runs
  comparable. Cloud model IDs are not in SOURCES.md, and a retired model resets a streak. Both endpoint shapes keep
  inference on Ollama Cloud; shape (a) also lets L1 add local models later on Zed's single Ollama provider (SPEC-202 V-5).
- **Blocks**: nothing.
- **Recommended default**: (a) one model for all three roles: the largest tool-capable general model the live service
  lists at SPEC-201 T112, recorded with its date in SOURCES.md and `cloud-models.json` (the foundation template's example
  is `gpt-oss:120b-cloud`, unverified). (b) The shape T112 verifies; shape (a) if both work.

### OQ-11 Local parity runs

- **Question**: Should local parity need 3 consecutive local runs (the same bar as cloud) or 1?
- **Why it matters**: one pass at non-zero temperature proves little, and the roadmap's "reliable" is defined by 3 runs.
- **Blocks**: nothing (it sets M-L1's duration).
- **Recommended default**: 3.

### OQ-12 L1 on the R1 suite

- **Question**: Do you want L1 evaluated early on the R1 suite? Such a record goes stale when R2's suite lands and must
  be earned again.
- **Why it matters**: R1's runs count toward the L1 streak only for the R1 suite's digest (SPEC-202 D-17).
- **Blocks**: nothing.
- **Recommended default**: evaluate on whatever suite is installed when 3 eligible runs exist; `install --check` flags a
  stale record.

### OQ-13 Dispatch limits and merge-schedule TTL

- **Question**: Are these limits acceptable: 1 concurrent PSE session (maximum 2), 10 dispatches a day (maximum 20), and
  a merge-schedule TTL of 30 minutes (range 5–60)?
- **Why it matters**: one PSE session matches R2's single-host lease authority. 10 a day bounds cost and human recovery
  load while cost per issue is unmeasured. 30 minutes is three times the 10-minute CI target, so a healthy re-run
  finishes inside it and a stuck one becomes a human decision.
- **Blocks**: nothing.
- **Recommended default**: these values.

### OQ-14 Your identity in human-owned records

- **Question**: Which identity string should name you in `.skill-policy.json` (`set_by`) and in `human-signoff.v1`
  (`signer`): the GitHub login `Cazador0`, another name, or both?
- **Why it matters**: the records are attestations, not authentication; a consistent identity keeps the audit trail
  readable.
- **Blocks**: nothing.
- **Recommended default**: `set_by: Cazador0`; `signer.name` from `git config user.name` plus `github_login: Cazador0`.

### OQ-15 Live keys in the reviewer session

- **Question**: May the reviewer cloud session's environment hold `OLLAMA_API_KEY` and `TYPESAFE_API_KEY`, so it can
  re-run one skill's live cases as a spot check?
- **Why it matters**: it would let the reviewer reproduce a live result instead of reading recorded evidence, at the
  cost of exposing two more secrets to another session.
- **Blocks**: nothing.
- **Recommended default**: no. The reviewer checks live evidence from recorded runs and cassettes, and says so in
  `non_blocking_findings`.

### OQ-16 Research report in the factory repository

- **Question**: Should `skill-lab/docs/research/engineering-team-report.md` be exported into the private factory
  repository?
- **Why it matters**: every release spec cites it by section; without it the citations do not resolve in the factory.
- **Blocks**: nothing.
- **Recommended default**: include it.

### OQ-17 Low-risk paths for auto-merge

- **Question**: The default low-risk set is `docs/**` and Markdown outside agent and policy paths, with at most 400
  changed lines. Should any project also treat "non-sensitive UI" paths as low risk (the report's example)?
- **Why it matters**: only low-risk PRs auto-merge. 400 lines is about 4k tokens, an eighth of the 32k context that
  bounds local models, so one review round can hold the whole diff plus the spec.
- **Blocks**: nothing.
- **Recommended default**: no built-in additions; a project adds paths through a human-merged policy change, and never
  where a built-in critical or high pattern matches.

### OQ-18 Demotion triggers and escaped-defect labelling

- **Question**: (a) Keep the three demotion triggers beyond your rule (escaped defect, revert): containment breach,
  gate-integrity violation, and lease violation? (b) Humans label escaped defects `incident/escaped-defect` with a
  `Caused-by: #<pr>` line in the issue body; should an unattributed defect label also demote?
- **Why it matters**: each extra trigger means a guard failed. Demotion is the safe direction, and only a human
  re-promotes.
- **Blocks**: nothing.
- **Recommended default**: keep all five triggers; use the `Caused-by:` convention; unattributed labels also demote.

### OQ-19 Auto-merge style

- **Question**: Merge commit or squash for auto-merges?
- **Why it matters**: a merge commit keeps the PR's commits, which revert attribution and post-merge audits use.
- **Blocks**: nothing.
- **Recommended default**: merge commit.

### OQ-20 Issue granularity

- **Question**: One Gitea issue per Spec Kit task (the Spec Kit `github` extension's behaviour, which R1's dry run
  follows), or grouped issues as in the report's example?
- **Why it matters**: it decides how many issues, leases, and PRs a feature produces.
- **Blocks**: nothing in R2, which only applies R1's plans.
- **Recommended default**: one issue per task.

### OQ-21 Live artefacts in PR bodies

- **Question**: Should PR bodies include live benchmark artefacts (Jev request IDs, token usage), or digests only?
- **Why it matters**: prompts and outputs may contain repository content that should not leave the repository.
- **Blocks**: nothing.
- **Recommended default**: digests and Jev request IDs only; no prompts or outputs.

## Source mapping

| Release question | Consolidated as |
|---|---|
| SPEC-201 Q1, Q2, Q3, Q4, Q5, Q6, Q7, Q8 | OQ-01, OQ-10, OQ-02, OQ-15, OQ-03, OQ-14, OQ-16, OQ-04 |
| SPEC-202 Q-1, Q-2, Q-3, Q-4, Q-5, Q-6, Q-7, Q-8, Q-9 | OQ-07, OQ-06, OQ-05, OQ-11, OQ-05, OQ-20, OQ-14, OQ-21, OQ-12 |
| SPEC-203 Q-1, Q-2, Q-3, Q-4, Q-5, Q-6, Q-7, Q-8, Q-9, Q-10, Q-11 | OQ-08, OQ-06, OQ-13, OQ-05, OQ-17, OQ-18, OQ-09, OQ-19, OQ-04, OQ-18, OQ-08 |
