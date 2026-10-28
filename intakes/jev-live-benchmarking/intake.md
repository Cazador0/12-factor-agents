# Intake: Jev live benchmarking

**Status**: Answered — 3 open items
**Scope**: feature
**Feature**: skill-lab/specs/105-jev-live-benchmarking
**Slug**: jev-live-benchmarking
**Created**: 2026-10-22
**Idea type**: new-capability

## Idea (verbatim)

> "Jev live benchmarking. Then Research => Plan => Refine with user => Create implementation Plan => Build Engineering tasks => /speckit-development skill call to implement the plan => Code Review and Feedback => Create Pull Request. That is what I would like to see for the "Whole skill-factory product" after delivering "Jev live benchmarking (Recommended)."

The first sentence is the idea for this intake. The rest is the person's expected delivery flow for
the whole skill-factory product, which they scheduled as a separate, later intake once this feature is
delivered.

## Working interpretation

Run skill-factory's agentic and routing benchmarks live against one Ollama Cloud model, graded by
TypeSafe's Jev model, as the R1 release gate. The scores are posted on the release PR for the person
and the independent reviewer session. Runs go to completion under system logging and monitoring, and
a new run-monitor skill checks container, API, and session health after each skill. The same runs,
3 in a row at ≥ 80% agentic and ≥ 90% routing, are the evidence that unlocks local inference later.

## Scope note

No `.specify/memory/constitution.md` exists, which would normally make this a project intake. The
person scheduled the whole-product (project) intake as the next session, after this feature ships,
so this intake is scoped to the feature. Its constitution rows are N/A here (inferred from the idea).
Until that project intake exists, the interim constitution-equivalent is
`skill-lab/docs/CONVENTIONS.md`, ADR-0001…0013 and SPEC-200. Those are agent-authored except where
the confirmed assumptions below cite a person's decision.

## Sufficiency Check

### Constitution rows

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| C1–C6 | Constitution | N/A | Deferred to the whole-product intake the person scheduled next | — |

### Spec rows: spec-ready

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| S1 | Problem & context | Sufficient | Q1: the first live run is the R1 release gate; A3 cloud-first gate | — |
| S2 | People & roles | Sufficient | Q2: the person and the independent reviewer session read scores posted on the release PR; the person runs benchmarks (A7) | — |
| S3 | Primary journey | Sufficient | Q1: live-graded R1 gate run on Ollama Cloud with Jev (first because it gates R1 and the local-inference unlock, inferred from Q1 and A3). Steps: doctor → live bench → score → scores posted on the R1 PR → reviewer reads them (Q2). Outcomes: unsure grade is re-asked once, then failed and flagged (Q5); an outage marks cases errored and the run does not count toward the streak (Q6) | — |
| S4 | Later journeys | Sufficient | Q10 + Q14: model comparison is next and ships right after the first release; local parity follows its A3 gate (inferred from A3); whole-product intake after this feature (idea) | — |
| S5 | Capabilities & scope | Sufficient | **Includes**: live R1 gate run grading agentic + trigger cases with Jev (Q1); one cloud model for every profile (Q11 Delegated); unsure grades re-asked once, then failed and flagged (Q5); outage cases errored, run continues (Q6); a case that flips breaks the streak and is flagged (Q13); tokens and estimated cost reported, no cap (Q7 Delegated, Q16); every result committed (Q9); system logging and monitoring of per-case time/tokens/cost, container CPU/memory/disk, API latency/errors and agent session metrics (Q18), watching the benchmark container, model sessions under test and the reviewer session (Q19); a health check after each skill (Q20) by a new run-monitor skill (Q22; a 14th skill, inferred from Q22); the reviewer session runs the monitor in its own container and posts the report with its verdict (Q23); a detected problem warns and marks the run degraded (Q21), with limits Delegated: standard limits, tuned after the smoke run (Q24). **Leaves out**: model comparison (Q14), local parity runs (A3, Q10), trend dashboard (not chosen in Q10, inferred), monitoring of the person's local machine (not chosen in Q19) | — |
| S6 | Information | Sufficient | Keeps benchmark-case, benchmark-result, benchmark-run, skill-score and cassettes, all committed (Q9); results relate run → case → skill | — |
| S7 | Trust, privacy & rules | Sufficient | Q4: only skill-factory's own fixtures, skill instructions and model outputs are sent; A7 keys as env secrets only | — |
| S8 | Edge cases | Sufficient | Q5 unsure answers re-asked once then failed and flagged; Q6 outage marks cases errored and the run does not count; Q13 a case that flips between runs breaks the streak and is flagged unstable | — |
| S9 | Success | Sufficient | Headline (Q3): ≥ 80% agentic pass and ≥ 90% trigger accuracy, on 3 consecutive runs to unlock local inference; R1 needs one fully passing run (Q15). Per run (Q16): ≥ 95% agentic JSON valid; < 10% of judgments unsure after re-ask; tokens and estimated cost reported for every run | — |
| S10 | Constraints & dependencies | Sufficient | Dependencies: TypeSafe key (possibly waitlisted), Ollama Cloud plan, allowlist + secrets (A7); budget Delegated, report cost only (Q7); no calendar deadline (D5 confirmed by Q17) | — |

### Plan rows: plan-ready

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| T1 | Platform & form | Sufficient | A command-line harness in `skill-lab/`, run in Claude Code cloud sessions and on the person's machine (A2, A3, A7) | — |
| T2 | Stack | Sufficient | D4 confirmed by Q17: stdlib-only Python ≥ 3.9 | — |
| T3 | Storage | Sufficient | Q9: every result file and cassette is committed to the repo | — |
| T4 | Testing | Sufficient | Q12: automated tests against fake TypeSafe and Ollama servers, plus one small live smoke run the person looks at | — |
| T5 | Performance & scale | Sufficient | Q8: on demand plus once per release PR; cost ceiling Delegated (Q7); Q17: no time limit, runs go to completion; Q20: performance check after each skill's cases finish | — |
| T6 | Technical constraints | Sufficient | Hosting: Claude Code cloud sessions + the person's machine (A3, A7); data boundary (Q4); cost Delegated, report only (Q7); Ollama Cloud has no structured outputs (SOURCES.md) | — |

## Assumptions

Confirmed decisions (the person stated these earlier in the build session; they count toward sufficiency):

- **A1**: One private repo, `Cazador0/skill-factory`, holds `skills/` and `skill-lab/`. *Source: person's answer, 2026-10-22.*
- **A2**: Runtime priority is the Zed Agent with Ollama first, then Claude Code and Codex. *Source: person's answer, 2026-10-22.*
- **A3**: Inference is cloud first. Local Ollama (GPU under 24 GB) is enabled only after cloud passes 3 consecutive live runs and the person signs off. *Source: person's answer, 2026-10-22; SPEC-200.*
- **A4**: Three autonomy releases (R1 Shadow, R2 Agent implementation, R3 Guarded autonomous) ship as stacked PRs, each reviewed by a separate Claude Code cloud session that posts review-verdict JSON; a human merges. *Source: person's answers, 2026-10-22.*
- **A5**: "Jev" means TypeSafe AI's System One model, used as the calibrated benchmark grader. *Source: person's link to docs.typesafe.ai, 2026-10-22.*
- **A6**: Gitea is a test double for now. *Source: person's answer, 2026-10-22.*
- **A7**: The person allowlists `api.typesafe.ai` and `ollama.com` and adds `TYPESAFE_API_KEY` and `OLLAMA_API_KEY` as environment secrets. *Source: person's answer and handoff, 2026-10-22.*
- **A8**: Model, Jev and benchmark results are never fabricated; skipped and failed gates are reported honestly. *Source: handoff rules, 2026-10-22.*

Defaults pending the person's check (they do not count toward sufficiency until confirmed):

- ~~**D1**: A Jev yes/no answer between 0.35 and the pass threshold counts as a fail and is flagged for human review.~~ overturned by Q5: re-ask Jev once, then fail and flag if still unsure.
- **D2**: Replay from recorded cassettes never counts toward a release gate; only live runs do. *Confirmed by Q17.*
- ~~**D3**: Run summaries are committed to the repo, and raw per-case results are kept as CI artifacts.~~ overturned by Q9: every result file is committed.
- **D4**: The benchmark harness stays stdlib-only Python ≥ 3.9. *Confirmed by Q17.*
- **D5**: There is no calendar deadline; the first live gate run happens as soon as the keys and network allowlist are in place. *Confirmed by Q17.*
- ~~**D6**: One full live run (all skills, agentic + trigger tiers) may take up to 60 minutes.~~ overturned by Q17: "Run to completion with system logging, system monitoring, and periodic Agent skill calls to evaluate the performance of all containers and Agent Session performance".

## Question Bank

### Q1 (S1, S3) — What should the first live benchmark run prove?
- [x] **A. R1 release gate** — Grade every skill's agentic and trigger cases live on Ollama Cloud with Jev; the result decides whether the R1 PR is ready.
- [ ] **B. Pick cloud models** — Compare several Ollama Cloud models on the same cases to choose the default model for each Zed profile.
- [ ] **C. Calibrate Jev first** — Check Jev's verdicts against hand-labeled cases before trusting any threshold.
- [ ] **Other**: ____

**Answer**: A. R1 release gate — round 1

### Q2 (S2) — Who should read the live results and act on them?
- [x] **A. You and the reviewer** — Scores are posted on the release PR, and the independent reviewer session reads them before its verdict.
- [ ] **B. Only you** — A local report you read and act on yourself.
- [ ] **C. CI as a gate** — Every PR runs live benchmarks automatically and fails when gates fail.
- [ ] **Other**: ____

**Answer**: A. You and the reviewer — round 1

### Q3 (S9) — Which target should count as "cloud is reliable"?
- [x] **A. 80% agentic and 90% trigger** — At least 80% of agentic cases pass and at least 90% of skill-routing checks are right, on 3 runs in a row.
- [ ] **B. 90% agentic and 95% trigger** — Stricter: fewer runs will pass, but enabling local inference rests on stronger evidence.
- [ ] **C. 100% of agentic cases** — Every case must pass on every run. Very strict for probabilistic models; expect many reruns.
- [ ] **Other**: ____

**Answer**: A. 80% agentic and 90% trigger — round 1

### Q4 (S7) — What content may be sent to TypeSafe and Ollama Cloud during live runs?
- [x] **A. Only repo fixtures** — Only skill-factory's own fixtures, skill instructions, and model outputs. No code from other projects.
- [ ] **B. Other repos too** — Also code from other repositories you audit, such as the 12-factor audit run on real projects.
- [ ] **C. Ask each time** — The harness asks before sending anything outside skill-factory's fixtures.
- [ ] **Other**: ____

**Answer**: A. Only repo fixtures — round 1

### Q5 (S8, S3) — When Jev is unsure (between 0.35 and the pass threshold), what should happen?
- [ ] **A. Fail and flag** — Counts as a fail and is flagged for your review. This is the current default, D1.
- [ ] **B. Re-ask once** — Ask Jev again with more context, then fail and flag if it is still unsure.
- [ ] **C. Exclude it** — Leave uncertain answers out of the pass rate and list them separately.
- [x] **Other**: RE-ask once, then Fail and flag (Recommended)

**Answer**: Other — "RE-ask once, then Fail and flag (Recommended)" — round 2

### Q6 (S8) — If TypeSafe or Ollama Cloud goes down in the middle of a run, what should happen?
- [x] **A. Mark errored and continue** — Affected cases are errored, the rest finish, and the run does not count toward the 3-in-a-row streak.
- [ ] **B. Abort the run** — Stop at the first outage and report a partial run.
- [ ] **C. Retry later** — Pause and retry the failed cases after a delay before finishing.
- [ ] **Other**: ____

**Answer**: A. Mark errored and continue — round 2

### Q7 (S10, T5) — Should a live run stop at a spending limit?
- [ ] **A. Hard cap per run** — The run stops when estimated spend reaches a limit you set; unfinished cases are reported as skipped.
- [ ] **B. Report cost only** — No limit; every run reports its token usage and estimated cost.
- [x] **C. Decide during planning** — Planning picks a limit once real per-case costs are measured.
- [ ] **Other**: ____

**Answer**: Delegated — agent chose B. Report cost only: no measured per-case cost exists yet, so planning sets any cap from the first live run's real usage — round 2

### Q8 (T5) — How often should live benchmark runs happen?
- [x] **A. On demand and per release** — You run it when you choose, plus once for every release PR.
- [ ] **B. Nightly** — A scheduled run every night, so trends appear over time.
- [ ] **C. Every PR** — CI runs it on each pull request.
- [ ] **Other**: ____

**Answer**: A. On demand and per release — round 3

### Q9 (T3, S6) — Where should live results and recordings be kept?
- [ ] **A. Summaries in repo** — Commit run summaries and cassettes; keep raw per-case results as CI artifacts. This is default D3.
- [x] **B. Everything in repo** — Commit every result file so the full history lives in git.
- [ ] **C. Nothing in repo** — Keep everything as CI artifacts or local files only.
- [ ] **Other**: ____

**Answer**: B. Everything in repo — round 3

### Q10 (S4) — After the first live run, which journey comes next?
- [ ] **A. Local parity runs** — Run the same suite on local Ollama once the cloud gate passes, to unlock local inference.
- [x] **B. Model comparison** — Compare cloud models to tune each profile's default.
- [ ] **C. Trend dashboard** — A page showing scores across runs and releases.
- [ ] **Other**: ____

**Answer**: B. Model comparison — round 3

### Q11 (S5) — Which cloud model setup should the first run use?
- [ ] **A. One model for all** — One Ollama Cloud model for every profile, as a simple baseline.
- [ ] **B. Large for Lead and Review** — A larger model for Lead and Review, a smaller one for PSE.
- [x] **C. Decide during planning** — Choose after listing what your Ollama plan offers.
- [ ] **Other**: ____

**Answer**: Delegated — agent chose A. One model for all: a single model keeps the first R1 gate run to one variable; the concrete model is picked during planning from the person's Ollama plan (`/api/tags`) — round 2

### Q12 (T4) — How should the benchmarking feature itself be checked before you rely on it?
- [x] **A. Tests and one live smoke run** — Automated tests against fake servers, plus one small live run you look at.
- [ ] **B. Tests only** — Automated tests against fake servers; no live check before use.
- [ ] **C. Full live run reviewed** — A complete live run whose results you review case by case.
- [ ] **Other**: ____

**Answer**: A. Tests and one live smoke run — round 4

### Q13 (S8) — If a case passes in one live run and fails in another, what should happen?
- [x] **A. Break streak and flag** — Any failure breaks the 3-in-a-row streak; the case is flagged as unstable.
- [ ] **B. Best 2 of 3** — Within the 3 runs, a case counts as passing when it passed at least twice.
- [ ] **C. Rerun the case** — Rerun that case up to 2 more times within the run; flaky only if it keeps flipping.
- [ ] **Other**: ____

**Answer**: A. Break streak and flag — round 3

### Q14 (S4, S5) — Should model comparison ship in this feature's first release, or right after the gate run works?
- [x] **A. Right after** — The first release is the live R1 gate run only; model comparison follows as its own small release.
- [ ] **B. Same release** — Gate run and model comparison ship together.
- [ ] **Other**: ____

**Answer**: A. Right after — round 4

### Q15 (S9) — Does the R1 PR need 3 passing live runs in a row, or is one passing run enough for R1?
- [x] **A. One run for R1** — One fully passing live run makes the R1 PR ready; the 3-in-a-row streak gates only the local-inference unlock.
- [ ] **B. Three runs for R1** — R1 waits for 3 consecutive passing runs.
- [ ] **Other**: ____

**Answer**: A. One run for R1 — round 4

### Q16 (S9, multi-select) — Which of these should also count as success for live benchmarks?
- [x] **A. JSON valid 95%** — At least 95% of agentic outputs parse and match their contract, after at most 2 repair attempts on Ollama Cloud.
- [x] **B. Unsure under 10%** — Fewer than 10% of Jev judgments stay unsure after the one re-ask.
- [x] **C. Cost on every run** — Every live run reports tokens and estimated cost per case and in total.
- [ ] **D. Every skill graded** — All 13 skills have at least 2 agentic and 3 routing cases graded live in each run.
- [ ] **Other**: ____

**Answer**: A. JSON valid 95%; B. Unsure under 10%; C. Cost on every run — round 4

### Q17 (assumption check, multi-select) — Which of these defaults should stay as written?
- [x] **A. Replay never gates** — D2.
- [x] **B. Stdlib Python 3.9+** — D4.
- [x] **C. No calendar deadline** — D5.
- [ ] **D. Run up to 60 minutes** — D6.
- [x] **Other**: Run to completion with system logging, system monitoring, and periodic Agent skill calls to evaluate the performance of all containers and Agent Session performance

**Answer**: A. Replay never gates; B. Stdlib Python 3.9+; C. No calendar deadline; Other — "Run to completion with system logging, system monitoring, and periodic Agent skill calls to evaluate the performance of all containers and Agent Session performance" — round 5

### Q18 (S5, multi-select) — What should the run's system logging and monitoring record?
- [x] **A. Per-case time tokens cost** — Wall time, input and output tokens, estimated cost, retries, and repair attempts per case.
- [x] **B. Container CPU memory disk** — CPU, memory, disk free, and process count of each machine running work, sampled through the run.
- [x] **C. API latency and errors** — Request latency, status codes, rate-limit hits, and retry waits for TypeSafe and Ollama.
- [x] **D. Agent session metrics** — Turns, tool calls, context used versus its limit, stalls, and how each agent session ended.
- [ ] **Other**: ____

**Answer**: A. Per-case time tokens cost; B. Container CPU memory disk; C. API latency and errors; D. Agent session metrics — round 6

### Q19 (S5, multi-select) — Which machines and sessions should the monitoring watch?
- [x] **A. Benchmark container** — The Claude Code cloud container running skill-lab during the live run.
- [x] **B. Model sessions under test** — Each agentic case's model conversation on Ollama Cloud, plus its Jev grading calls.
- [x] **C. Reviewer session** — The separate Claude Code cloud session that reviews the release PR.
- [ ] **D. Your local machine** — Your machine during local Ollama runs.
- [ ] **Other**: ____

**Answer**: A. Benchmark container; B. Model sessions under test; C. Reviewer session — round 6

### Q20 (T5) — How often should the periodic agent-skill performance check run during a live run?
- [x] **A. After each skill** — Check when each skill's cases finish; 13 checks per full run.
- [ ] **B. Every 10 minutes** — A fixed clock interval.
- [ ] **C. Every 25 cases** — A fixed case-count interval.
- [ ] **Other**: ____

**Answer**: A. After each skill — round 6

### Q21 (S8, S5) — When a periodic check finds a problem, what should happen?
- [x] **A. Warn and mark degraded** — Log, warn, keep running to completion; the run is degraded and does not count toward the 3-in-a-row streak.
- [ ] **B. Warn only** — Log and warn; the run still counts if its cases pass.
- [ ] **C. Pause for you** — Pause until the person decides.
- [ ] **Other**: ____

**Answer**: A. Warn and mark degraded — round 6

### Q22 (S5) — Which skill should the agent call for the periodic performance check after each skill's cases?
- [x] **A. New run-monitor skill** — A dedicated skill that snapshots containers, API health, and session metrics and returns one JSON health report.
- [ ] **B. Built into skill-lab** — The bench command collects metrics; an existing skill reads the report.
- [ ] **C. Decide during planning** — Planning picks the design.
- [ ] **Other**: ____

**Answer**: A. New run-monitor skill — round 7

### Q23 (S5) — How should the reviewer session's own container be monitored?
- [x] **A. Reviewer reports itself** — The reviewer runs the same monitor in its own container and posts the health report alongside its verdict JSON.
- [ ] **B. Session-level only** — Only status, duration, turns, and model from the session API.
- [ ] **Other**: ____

**Answer**: A. Reviewer reports itself — round 7

### Q24 (S5, S8) — Which limits should mark a live run degraded?
- [ ] **A. Standard limits** — Memory ≥ 90%, disk free < 1 GB, API error rate ≥ 5% within a skill, or a session with no progress for 10 minutes.
- [ ] **B. Stricter limits** — Memory ≥ 80%, disk free < 2 GB, API error rate ≥ 2%, or no progress for 5 minutes.
- [x] **C. Decide during planning** — Planning sets limits after the live smoke run measures normal levels.
- [ ] **Other**: ____

**Answer**: Delegated — agent chose A. Standard limits as the starting values: they are common defaults, and planning tunes them after the live smoke run (Q12) measures normal levels, as the chosen option says — round 7

## Clarifications

### Session 2026-10-22

- Q: In one short sentence, what idea should this intake capture? → A: "Jev live benchmarking." Then, for the whole skill-factory product after this feature ships: "Research => Plan => Refine with user => Create implementation Plan => Build Engineering tasks => /speckit-development skill call to implement the plan => Code Review and Feedback => Create Pull Request."
- Q: What should the first live benchmark run prove? → A: R1 release gate: grade every skill's agentic and trigger cases live on Ollama Cloud with Jev; the result decides whether the R1 PR is ready.
- Q: Who should read the live results and act on them? → A: The person and the reviewer: scores are posted on the release PR, and the independent reviewer session reads them before its verdict.
- Q: Which target should count as "cloud is reliable", the bar that unlocks local inference? → A: At least 80% of agentic cases pass and at least 90% of skill-routing checks are right, on 3 runs in a row.
- Q: What content may be sent to TypeSafe and Ollama Cloud during live runs? → A: Only skill-factory's own fixtures, skill instructions and model outputs; no code from other projects.
- Q: When Jev is unsure about a case (its yes-probability falls between 0.35 and the pass threshold), what should happen? → A: "RE-ask once, then Fail and flag (Recommended)"
- Q: If TypeSafe or Ollama Cloud goes down in the middle of a live run, what should happen? → A: Mark errored and continue: affected cases are errored, the rest finish, and that run does not count toward the 3-in-a-row streak.
- Q: Which Ollama Cloud model setup should the first live run use? → A: Delegated — agent chose one model for all profiles; the concrete model is picked during planning from the Ollama plan's model list.
- Q: Should a live run stop when it reaches a spending limit? → A: Delegated — agent chose report cost only; planning sets any cap from the first live run's measured usage.
- Q: If a case passes in one live run and fails in another, what should happen? → A: Break streak and flag: any failure breaks the 3-in-a-row streak, and the case is flagged as unstable.
- Q: How often should live benchmark runs happen? → A: On demand, plus once for every release PR.
- Q: Where should live results and recordings be kept? → A: Everything in repo: every result file is committed.
- Q: Once the first live gate run works, which journey should come next? → A: Model comparison: compare cloud models on the same cases to tune each profile's default.
- Q: Should model comparison ship in this feature's first release, or right after the gate run works? → A: Right after: the first release is the live R1 gate run only.
- Q: Does the R1 PR need 3 passing live runs in a row, or is one passing run enough for R1? → A: One run for R1; the 3-in-a-row streak gates only the local-inference unlock.
- Q: Which of these should also count as success for live benchmarks? → A: At least 95% of agentic outputs valid JSON for their contract; fewer than 10% of judgments unsure after the re-ask; tokens and estimated cost reported on every run.
- Q: How should the live-benchmarking feature itself be checked before you rely on it? → A: Automated tests against fake servers plus one small live smoke run the person looks at.
- Q: Which of these defaults should stay as written? → A: Replay never gates; stdlib Python 3.9+; no calendar deadline; and, in place of the 60-minute limit: "Run to completion with system logging, system monitoring, and periodic Agent skill calls to evaluate the performance of all containers and Agent Session performance".
- Q: What should the run's system logging and monitoring record? → A: Per-case time, tokens and cost; container CPU, memory and disk; API latency and errors; agent session metrics.
- Q: Which machines and sessions should the monitoring watch? → A: The benchmark container, the model sessions under test, and the reviewer session.
- Q: How often should the periodic agent-skill performance check run during a live run? → A: After each skill's cases finish.
- Q: When a periodic check finds a problem, what should happen? → A: Warn and mark the run degraded; keep running to completion; a degraded run does not count toward the 3-in-a-row streak.
- Q: Which skill should the agent call for the periodic performance check after each skill's cases? → A: A new run-monitor skill that returns one JSON health report.
- Q: How should the reviewer session's own container be monitored? → A: The reviewer runs the same monitor in its own container and posts the health report alongside its verdict JSON.
- Q: Which limits should mark a live run degraded? → A: Delegated — agent chose standard limits (memory ≥ 90%, disk free < 1 GB, API error rate ≥ 5% within a skill, no progress for 10 minutes) as starting values, tuned during planning after the live smoke run.

## Session Log

| Round | Questions | Rows sufficient after round | Note |
|---|---|---|---|
| 0 | Idea captured | 1 of 16 (T1) | Intake drafted |
| 1 | Q1–Q4 | 4 of 16 (S1, S2, S7, T1) | Purpose, audience, headline target, data boundary settled |
| 2 | Q5, Q6, Q11, Q7 | 6 of 16 (+S3, T6) | Unsure-grade and outage behaviour set; model setup and budget delegated |
| 3 | Q13, Q8, Q9, Q10 | 9 of 16 (+S6, S8, T3) | Flaky handling, frequency, storage, next journey settled |
| 4 | Q14, Q15, Q16, Q12 | 13 of 16 (+S4, S5, S9, T4) | First-release scope, R1 bar, extra measures, test approach settled |
| 5 | Q17 (assumption check) | 14 of 16 (+S10, T2; S5 back to Partial) | D2, D4, D5 confirmed; D6 replaced by run-to-completion with monitoring |
| check-in | after round 5 | 14 of 16 | Person chose "Keep going" |
| 6 | Q18–Q21 | 15 of 16 (+T5) | Monitoring records, watched targets, interval, problem handling settled |
| 7 | Q22–Q24 | 16 of 16 (+S5) | Monitor skill, reviewer self-report, degraded limits (delegated) settled |
| specify-refine 1 | RQ1–RQ4 | — | Agent check, streak restart, price source, re-ask context settled; 1 conflict resolved |
| specify-refine 2 | RQ5–RQ6 | — | Guardrail bar and four defaults confirmed; specify refinement done |
| plan-refine 1 | PQ1–PQ2 | — | Seven plan defaults confirmed; plan refinement done |

## Open Items

- ~~[NEEDS CLARIFICATION: How "estimated cost" is computed (Q16 C, Q7).~~ Resolved in specify refinement round 1: a price table the person maintains; usage only where no price is entered.
  ~~Original: The harness knows token counts from Ollama and TypeSafe responses, but not their prices. If either plan is subscription-based, cost may only be reportable as token usage against the plan's limits. Planning needs the price source, or must agree to report usage only.]~~
- [NEEDS CLARIFICATION: SPEC-201 (agent-authored, written before this intake) sets live gate thresholds of per-skill agentic ≥ 0.67, guardrail agentic = 1.0, per-skill trigger ≥ 0.83 and catalog trigger ≥ 0.90. The confirmed headline is ≥ 80% agentic and ≥ 90% routing (Q3), with one fully passing run for R1 (Q15). Planning must reconcile SPEC-201's gates with these answers, for example in a `speckit-intake-refine` pass on SPEC-201.]
- [NEEDS CLARIFICATION: Adding run-monitor (Q22) makes 14 skills; CONVENTIONS, the catalog, SPEC-200 and SPEC-201 all say 13. Planning must assign it a spec id and a release.]

## Phase Refinements

### Specify · 2026-10-22

Artifact: `skill-lab/specs/105-jev-live-benchmarking/spec.md` (SPEC-105). No `.specify/` scripts exist, so the
feature folder was taken directly. Backing: this intake, the person's 2026-10-22 decisions ("More cases, both
levels"; "All four layers in R1"), and CONVENTIONS / ADRs as the interim constitution-equivalent.

| # | Decision | Where | Group | Question | Answer |
|---|---|---|---|---|---|
| 1 | One model for every runtime case in a gate run | FR-001 | Delegated (Q11): one model keeps the gate to one variable | — | — |
| 2 | Re-ask once; a second unsure grade fails and is flagged | FR-002 | Backed (Q5) | — | — |
| 3 | The re-ask adds the case's fixture contents and the skill's SKILL.md body | FR-002 | Unbacked → Backed | RQ4 | Fixtures and skill text — refinement round 1 |
| 4 | Unsure band is 0.35 up to the pass threshold | FR-002 | Backed (Q5 wording) | — | — |
| 5 | Outage: case errored, run continues, run not counting | FR-003 | Backed (Q6) | — | — |
| 6 | HTTP 429 after retries counts as an outage | FR-003, Edge Cases | Unbacked → Backed | RQ6 assumption check | Kept as written — refinement round 2 |
| 7 | No time limit; runs go to completion | FR-004 | Backed (Q17) | — | — |
| 8 | Defaults are the floor; a skill may raise a gate, never lower it | FR-005 | Backed (gates decision, 2026-10-22) | — | — |
| 9 | Unsure rate after re-ask strictly below 10% | FR-005 | Backed (Q16) | — | — |
| 10 | Gates at per-skill and catalog level | FR-006 | Backed (gates decision) | — | — |
| 11 | ≥ 5 agentic and ≥ 10 routing cases per skill | FR-007 | Backed (gates decision) | — | — |
| 12 | ≥ 2 of the 10 routing cases expect no skill | FR-007 | Unbacked → Backed | RQ6 assumption check | Kept as written — refinement round 2 |
| 13 | Guardrail cases must pass at 100% per skill | FR-008 | Unbacked → Backed | RQ5 | 100% for guardrails — refinement round 2 |
| 14 | R1 gate passes on one fully passing counting run | FR-009 | Backed (Q15) | — | — |
| 15 | A change of model or of any case (suite digest) restarts the streak | FR-010, Edge Cases | Unbacked → Backed | RQ2 | Model or case change — refinement round 1 |
| 16 | Counting run = live, complete, not degraded, no errored case | FR-011 | Backed (D2, Q6, Q21); "complete" inferred | — | — |
| 17 | A flip from pass to fail breaks the streak and flags the case | FR-012 | Backed (Q13) | — | — |
| 18 | Tokens recorded in structured fields | FR-013 | Backed (Q16) | — | — |
| 19 | Cost only from a person-maintained price table, else usage only | FR-014 | Unbacked → Backed | RQ3 | Price table you maintain — refinement round 1 |
| 20 | Run logs and health reports are committed with the results | FR-015 | Backed (Q9, inferred: they are result files) | — | — |
| 21 | Data boundary enforced by refusing out-of-folder fixtures | FR-016 | Backed (Q4) | — | — |
| 22 | PR comment rendered by a new `skill-lab report` command | FR-018 | Backed (Q2); format is the agent's | — | — |
| 23 | Health check: bench runs the snapshot script itself; an agent driving a run follows the same procedure | FR-021 | **Conflicting** → Backed | RQ1 | Script decides, agent explains: limits decide degraded, then an agent call with run-monitor writes an assessment — refinement round 1 |
| 24 | Starting degraded limits in `monitor-limits.json` | FR-022 | Delegated (Q24) | — | — |
| 25 | Reviewer runs the monitor in its own container | FR-023 | Backed (Q23) | — | — |
| 26 | Smoke run = ≥ 1 agentic + ≥ 2 routing cases from ≥ 2 skills | FR-025 | Unbacked → Backed | RQ6 assumption check | Kept as written — refinement round 2 |
| 27 | Invalid JSON after 2 repairs is a failed case, not errored | Edge Cases | Unbacked → Backed | RQ6 assumption check | Kept as written — refinement round 2 |
| 28 | Cost is reported, never capped | FR-014 | Delegated (Q7) | — | — |

- Q: For the health check after each skill, how should the agent skill call work? → A: Script decides, agent explains: the snapshot's fixed limits decide whether the run is degraded; then an agent call (the run's Ollama Cloud model with the run-monitor skill) reads the report and writes an assessment and recommendations into the run.
- Q: What should restart the 3-in-a-row reliability streak? → A: A change of model, or editing or adding any benchmark case.
- Q: Where should the estimated cost on every run come from? → A: A price table the person maintains (prices.json); a service without a price shows usage only.
- Q: When Jev is re-asked about an unsure grade, what extra context should the second ask get? → A: The case's input files plus the skill's SKILL.md instructions.
- Q: Should guardrail cases have to pass at 100% per skill, stricter than the 80% agentic bar? → A: 100% for guardrails.
- Q: Which of these defaults should stay as written? → A: All four: a persisting rate limit is an outage; ≥ 2 no-skill routing cases per skill; smoke run of ≥ 1 agentic and ≥ 2 routing cases from ≥ 2 skills; invalid JSON after 2 repairs is a failed case.

Result: 28 decisions — 25 Backed (16 at the start, 9 settled in 2 rounds, including 1 conflict), 3 Delegated, 0 open.

### Plan · 2026-10-22

Artifacts: `plan.md`, `research.md`, `data-model.md`, `tasks.md` in `skill-lab/specs/105-jev-live-benchmarking/`.

| # | Decision | Where | Group | Question | Answer |
|---|---|---|---|---|---|
| P1 | Re-ask only noul judgments; score/choice have no unsure band | research R-1 | Backed (Q5, RQ4: the re-ask is for unsure yes/no grades) | — | — |
| P2 | 401/403/422 are configuration or case bugs, not outages | research R-3 | Unbacked → Backed | PQ1 assumption check | Kept as written — plan refinement round 1 |
| P3 | A partly priced run reports usage only, never a partial cost sum | research R-8 | Unbacked → Backed | PQ1 assumption check | Kept as written — plan refinement round 1 |
| P4 | Without /proc (macOS) CPU, memory and processes are null and cannot mark a run degraded | research R-9 | Unbacked → Backed | PQ1 assumption check | Kept as written — plan refinement round 1 |
| P5 | The advisory call uses the run's own cloud model | research R-11 | Backed (RQ1 wording) | — | — |
| P6 | The reviewer's health report is a separate marked PR comment, because the verdict comment allows one JSON block | research R-12 | Unbacked → Backed | PQ1 assumption check | Kept as written — plan refinement round 1 |
| P7 | One model: the largest tool-capable general model on the plan's list | research R-14 | Delegated (Q11) | — | — |
| P8 | Smoke cases come from lead-architect and review-verifier | research R-15 | Unbacked → Backed | PQ2 assumption check | Kept as written — plan refinement round 1 |
| P9 | The run log never stores request or response bodies | research R-13 | Unbacked → Backed | PQ2 assumption check | Kept as written — plan refinement round 1 |
| P10 | monitor-limits.json is a protected policy file: changing the limits needs the person's approval | data-model.md | Unbacked → Backed | PQ2 assumption check | Kept as written — plan refinement round 1 |
| P11 | snapshot.py is built by SPEC-105 tasks; SKILL.md, SPEC-014 and evals by SPEC-201 tasks | plan.md | Agent's (internal ownership, no product effect) | — | — |

- Q: Which of these plan defaults should stay as written (set 1)? → A: All four: 401/403/422 are not outages; a partly priced run reports usage only; missing /proc metrics never mark a run degraded; the reviewer's health report is a separate marked PR comment.
- Q: Which of these plan defaults should stay as written (set 2)? → A: All three: smoke cases from lead-architect and review-verifier; no request or response bodies in the run log; monitor-limits.json changes need the person's approval.

Result: 11 plan decisions — 2 Backed by earlier answers, 7 settled in 1 round (2 questions), 1 Delegated, 1 internal; 0 open.

Plan-phase items, not refined here: `run-monitor`'s skill spec number and family; the exact contract field types.
