# Intake: Engineering team of coding-agent sessions (Lead, PSE, Review)

**Status**: Answered — 9 open items
**Scope**: project
**Feature**: N/A (project scope)
**Slug**: agent-engineering-team
**Created**: 2026-10-22
**Idea type**: new-capability

## Idea

> "Write related and dependent new "spec" using the file I attached here."
>
> Attached: "Engineering Team of Coding Agent Sessions: Lead, PSE, and Review" — a three-role engineering organization (Lead = control plane and technical/product authority, PSE = implementation plane, Review = independent assurance plane) operating over shared durable systems of record, with Gitea as the real-time engineering control plane, Spec Kit as the specification workflow, policy-mediated autonomous merge, and progressive autonomy.

**Sources read**: `docs/research/agent-engineering-team.md` (the attached research report, committed for provenance) — the whole design (roles, Gitea control plane, Kanban state machine, event schema, merge policy, Spec Kit stage ownership, context architecture, quality gates, rollout); the person's four answers in this session (Q1–Q4); `.claude/skills/speckit-intake-start/SKILL.md` — the intake rules this file follows. No `.agents/memory.md` or `AGENTS.md` governance section existed, so no prior decisions were carried in.

## Working interpretation

Build an autonomous software-engineering organization of three role agents — Lead, PSE and Review — that run in a LangGraph service and coordinate only through the repository (durable knowledge) and a Gitea 28.x instance (durable work state), so that validated product intent becomes specified, implemented, independently verified and policy-merged work without depending on any one conversation. This first pass asks for a project constitution and the full set of dependent specifications.

## Sufficiency check

<!-- Status is one of: Missing | Partial | Sufficient | Delegated | N/A | Open -->

### Constitution rows: constitution-ready

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| C1 | Purpose & identity | Sufficient | report §Executive architecture; report title | — |
| C2 | Principles | Sufficient | report §Final recommended operating doctrine (eleven invariants); report §Safe autonomous merge ("Agents may operate autonomously inside the rules; they may not autonomously weaken the rules") | — |
| C3 | Quality bar | Sufficient | report §Independent quality assurance and engineering gates; §Merge evidence gate ("Not run" must never silently mean "passed") | — |
| C4 | Constraints | Sufficient | Q1 (Gitea only); Q2 (LangGraph service); report §Gitea as the real-time engineering control plane (narrow MCP tool surface, mutation envelope) | — (implementation language belongs to T2) |
| C5 | Workflow & approvals | Sufficient | report §Risk-based escalation table; §Spec Kit stage ownership table; §Progressive autonomy | — |
| C6 | Governance | Open | report §Safe autonomous merge (agents never self-authorize changes to policy, gates or permissions) | who besides the owner may approve constitution amendments; versioning scheme rests on unconfirmed D6 |

### Spec rows: spec-ready

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| S1 | Problem & context | Sufficient | report §Executive architecture (free-chatting agents are unsafe; conversations are transient, not the system of record) | — |
| S2 | People & roles | Sufficient | report §The three-agent operating model (Lead, PSE, Review authority table); human owner at product intent and elevated-risk review (§Progressive autonomy) | — |
| S3 | Primary journey | Sufficient | report §Lead contract (execution loop); §Review contract (PSE → PR → Review loop); first release runs in Shadow mode per report §Progressive autonomy | — |
| S4 | Later journeys | Sufficient | report §Progressive autonomy: Agent implementation → Guarded autonomous → Long-horizon → Self-improving modes, in that order | — |
| S5 | Capabilities & scope | Sufficient | report §Reference implementation blueprint (five components); Q4 (constitution plus full spec set: control plane, forge gateway, role contracts, Spec Kit bridge, context/RAG, quality gates, autonomy) | — |
| S6 | Information | Sufficient | report: implementation evidence, review verdict, normalized event, issue contract, task-issue map, session checkpoint, lease, write-set estimate, quality gate manifest; Q3 (decision traces + visible reasoning chains) | — |
| S7 | Trust, privacy & rules | Sufficient | report §Safe autonomous merge (protected `main`, no force-merge tool, risk classes); §Gitea MCP (no unrestricted request tool); OWASP ASVS 5.0.0, NIST SSDF 1.1, SLSA cited in §Independent quality assurance | — |
| S8 | Edge cases | Sufficient | report §Agentic-framework verification (idempotency, ordering, concurrency, prompt injection, long-horizon recovery, failure recovery, RAG grounding) | — |
| S9 | Success | Open | report §Core metrics lists the scorecard but sets no numbers or timeframes | a headline target with a number and a timeframe the person confirms |
| S10 | Constraints & dependencies | Open | Q1 (Gitea 28.x); Q2 (LangGraph service); report §Gitea 28.2.0 current release | time, budget and who operates the Gitea instance |

### Plan rows: plan-ready

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| T1 | Platform & form | Sufficient | Q2 (LangGraph service hosting the three roles); report §Reference implementation blueprint (webhook gateway, event store, state machine, scheduler, Gitea MCP gateway) | — |
| T2 | Stack | Open | Q6 skipped; D1, D2 unconfirmed | implementation language; model and embedding provider |
| T3 | Storage | Open | report: repository = durable knowledge, Gitea = durable work state | where the event store, leases and retrieval index live |
| T4 | Testing | Sufficient | report §Verification layers table; §Agentic-framework verification; "every recurring agent mistake becomes a regression fixture, then an evaluation" | — |
| T5 | Performance & scale | Open | — | concurrent sessions, issues per week and events per day, as numbers |
| T6 | Technical constraints | Open | Q1 (Gitea 28.x); report §Safe autonomous merge (`main` policy) | where Gitea runs and how it is reached from the LangGraph service; embeddings (Q7 skipped) |

## Assumptions

- D1: The LangGraph service, gateways and engines are written in Python 3.12+. — unconfirmed (Q6 skipped)
- D2: Role agents call Claude (`claude-opus-5-5`) through the official `anthropic` SDK from inside LangGraph nodes. — unconfirmed (Q7 skipped; the round-1 option named `langchain-anthropic`, later replaced by the official SDK during setup)
- D3: The retrieval index runs offline by default: lexical BM25 plus hashed dense vectors, with an optional external embedder. — unconfirmed (Q7 skipped)
- D4: This repository hosts the skill catalog through `bin/intakespec`; `../intakeSpec` is used when present. — unconfirmed (Q8 skipped)
- D5: Spec Kit v1.2.2 with the intake, assess, bug and agent-context extensions; the git extension is left out because cloud sessions stay on one assigned branch. — agent setup choice, unconfirmed
- D6: The constitution uses semantic versioning with a Sync Impact Report, the Spec Kit default. — unconfirmed
- D7: "100 percent accurate" means 100 percent of explicitly defined acceptance gates are satisfied, not a defect-free guarantee. — from report §Executive architecture
- D8: Role definitions carry no pedigree claims; competencies are encoded as skills, permissions, required evidence and evaluation suites. — from report §Executive architecture
- D9: The first release operates in Shadow mode: agents analyze and recommend; humans perform consequential mutations. — from report §Progressive autonomy
- D10: Hidden model reasoning is never stored; durable decision traces are the record and visible reasoning chains are optional, reviewable debug artifacts. — confirmed by Q3; report §Session checkpoint

## Question bank

### Q1 · Forge · C4, T6 · impact high × uncertainty high

The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target?

- [ ] **A. Forge adapter GitHub first** — One semantic tool interface with a GitHub adapter built now and a Gitea adapter specified as a dependent spec. Works in cloud sessions today. *(Recommended: runs end-to-end in this environment today)*
- [x] **B. Gitea only** — Follow the report exactly. Needs a reachable Gitea 28.x server and token before anything can run end-to-end.
- [ ] **C. GitHub only** — Drop Gitea from the specs entirely. Simplest, but departs from the report's design.
- [ ] **Other**: ____

**Answer**: B. Gitea only — round 2

### Q2 · Runtime · T1, C4 · impact high × uncertainty high

Where should the Lead, PSE and Review agents run?

- [ ] **A. Claude Code cloud sessions** — Roles as .claude/agents subagents plus separate cloud sessions per role, with hooks for checkpoints and leases. Replaces the report's Codex harness. *(Recommended: least new code to own)*
- [x] **B. LangGraph service** — A standalone LangGraph orchestrator calls Claude through the API. More control but runs outside Claude Code.
- [ ] **C. Both layered** — Deterministic LangGraph state machine decides legal moves while Claude Code sessions do the work. Most complete and most code.
- [ ] **Other**: ____

**Answer**: B. LangGraph service — round 2

### Q3 · Reasoning · S6, C2 · impact medium × uncertainty high

The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work?

- [ ] **A. Structured decision traces** — Each step records decision, rationale summary, evidence, assumption and next action in git. Matches the report's checkpoint doctrine. *(Recommended: matches report §Session checkpoint)*
- [ ] **B. Visible reasoning chains** — LangChain chains that write out step-by-step reasoning as reviewable artifacts alongside each decision.
- [x] **C. Both** — Traces are the durable record; visible reasoning chains are kept as optional debug artifacts.
- [ ] **Other**: ____

**Answer**: C. Both — round 2

### Q4 · Spec scope · S5 · impact high × uncertainty medium

How far should the dependent specs go in this first pass?

- [x] **A. Constitution plus full spec set** — Constitution plus ~7 numbered specs (control plane, forge gateway, role contracts, Spec Kit bridge, context/RAG, quality gates, autonomy) with a dependency map. *(Recommended: the report's five components need all seven to be buildable in order)*
- [ ] **B. Constitution plus core three** — Constitution plus control plane, role contracts and quality gates. The rest later.
- [ ] **C. Intake files first** — Run your intake-start flow on the report and write answered intakes before any spec.md.
- [ ] **Other**: ____

**Answer**: A. Constitution plus full spec set — round 2

### Q5 · Spec source · S1 · impact high × uncertainty high

Your attached spec file didn't reach this session (the upload folders are empty). What should the new specs be based on?

- [ ] **A. I'll paste it next** — I build the harness and skills now. Task 1 waits for the file you paste or re-upload in your next message. *(Recommended: the specs should come from the person's file)*
- [ ] **B. Use the three skills** — Treat the speckit-intake skills as the source and write specs for the intake/route/refine harness itself.
- [ ] **C. Use 12-factor-agents content** — Derive specs from this repo's 12 factors (e.g. an intake agent built on factors 1-12).
- [x] **Other**: "Here are the files." (the person attached the report and three skill files)

**Answer**: Other — "Here are the files." — round 1

### Q6 · Language · T2 · impact medium × uncertainty high

Which language should the skills' source code (LangChain/LangGraph/RAG) be written in?

- [ ] **A. Python** — LangGraph Python is the most complete. Matches your langgraph-supervisor-py fork and Spec Kit's own Python CLI. *(Recommended: most complete LangGraph and RAG ecosystem)*
- [ ] **B. TypeScript** — Matches this repo's BAML workshops and walkthroughgen package. LangGraph.js has fewer RAG integrations.
- [ ] **C. Both** — Python core plus a thin TypeScript client. Roughly doubles the code to maintain.
- [ ] **Other**: ____

**Answer**: Open — skipped in round 1 (the person sent the attached files instead); D1 applies until confirmed

### Q7 · Models · T2, T6 · impact medium × uncertainty medium

Which models and embeddings should the RAG and reasoning chains use?

- [ ] **A. Claude plus offline embeddings** — Claude via langchain-anthropic for reasoning. Local BM25 plus fastembed vectors, so retrieval works with no extra API key. *(Recommended: works in every cloud session with no extra secret)*
- [ ] **B. Claude plus Voyage AI** — Anthropic's recommended embedding partner. Better retrieval quality but needs a VOYAGE_API_KEY secret.
- [ ] **C. Provider-agnostic** — Any LangChain chat model and embedder chosen by config. Most flexible but more setup per session.
- [ ] **Other**: ____

**Answer**: Open — skipped in round 1; D2 and D3 apply until confirmed

### Q8 · Catalog · T3 · impact low × uncertainty medium

Your route skill expects the Cazador0/intakeSpec catalog, which this session can't reach. What should the new router index instead?

- [ ] **A. Local skills plus Spec Kit** — Index every SKILL.md in the repo, ~/.claude/skills, and Spec Kit commands. Works offline and in every cloud session. *(Recommended: no access grant needed)*
- [ ] **B. intakeSpec when present** — Keep the ../intakeSpec contract and fall back to local skills when it's missing. I'll need you to grant repo access.
- [ ] **C. Add intakeSpec now** — You grant this session access to the private repo so I can clone and index its 377 skills.
- [ ] **Other**: ____

**Answer**: Open — skipped in round 1; D4 applies until confirmed

## Clarifications

### Session 2026-10-22

- Q: Your attached spec file didn't reach this session (the upload folders are empty). What should the new specs be based on? → A: Other — "Here are the files." (the report and three skill files were attached)
- Q: Which language should the skills' source code (LangChain/LangGraph/RAG) be written in? → A: skipped (Open)
- Q: Which models and embeddings should the RAG and reasoning chains use? → A: skipped (Open)
- Q: Your route skill expects the Cazador0/intakeSpec catalog, which this session can't reach. What should the new router index instead? → A: skipped (Open)
- Q: The report uses Gitea as the control plane, but this repo and Claude Code Cloud Sessions run on GitHub. Which should the specs target? → A: Gitea only
- Q: Where should the Lead, PSE and Review agents run? → A: LangGraph service
- Q: The report warns against storing hidden chain-of-thought as 'thought chaining'. How should the thought-chaining tools work? → A: Both
- Q: How far should the dependent specs go in this first pass? → A: Constitution plus full spec set

## Session Log

| Round | Questions | Answered | Rows sufficient | Notes |
|---|---|---|---|---|
| 0 | — | — | 12 of 22 | Drawn from the attached report. Settled before the first question: C1, C2, C3, C5, S1, S2, S3, S4, S6, S7, S8, T4. No constitution or prior decisions existed. |
| 1 | Q5, Q6, Q7, Q8 | 1 of 4 | 12 of 22 | The person answered by attaching the files (Q5); Q6–Q8 were skipped. |
| 2 | Q1, Q2, Q3, Q4 | 4 of 4 | 15 of 22 | C4, S5 and T1 became Sufficient. Session ended: the person asked for the constitution and specs; remaining rows set Open. |

## Open Items

- [NEEDS CLARIFICATION: implementation language for the LangGraph service, gateways and engines] — for planning — Python 3.12+ is assumed (D1) but the person skipped the question — cites Q6 — UNVERIFIED until the person confirms
- [NEEDS CLARIFICATION: Claude model and embedding backend for the role agents and retrieval index] — for planning — `claude-opus-5-5` with offline hybrid retrieval is assumed (D2, D3) — cites Q7 — UNVERIFIED until the person confirms
- [NEEDS CLARIFICATION: which skill catalog the router indexes] — for planning — this repository as host is assumed (D4) — cites Q8 — UNVERIFIED until the person confirms or grants intakeSpec access
- [NEEDS CLARIFICATION: where the Gitea 28.x instance runs, who operates it, and whether this GitHub-hosted repository is mirrored into it] — for planning — Gitea only means nothing runs end-to-end until an instance is reachable from the LangGraph service — cites Q1, Q2 — UNVERIFIED until a Gitea instance answers the gateway's version check
- [NEEDS CLARIFICATION: how per-session isolation and lifecycle hooks (the report's Codex worktrees and hooks) map onto the LangGraph service] — for planning — the runtime answer replaced the harness the report assumed — cites Q2 — UNVERIFIED until a first PSE run in Shadow mode
- [NEEDS CLARIFICATION: headline success target with a number and a timeframe] — for specify (spec 007) — the report names the scorecard metrics but no targets; spec success criteria carry proposed defaults — cites Q4
- [NEEDS CLARIFICATION: expected scale — concurrent sessions, issues per week, events per day] — for planning — no numbers in the report — cites none (row T5 never asked)
- [NEEDS CLARIFICATION: where the event store, leases and retrieval index are stored] — for planning — the report fixes the systems of record but not the control plane's own storage — cites none (row T3 never asked)
- [NEEDS CLARIFICATION: who besides the owner may approve constitution amendments, and the time and budget for the first release] — for constitution and planning — the report rules out agent self-amendment but names no approvers, time or budget — cites none (rows C6, S10 never asked)

## Phase Refinements

<!-- Written by the refine command: ### <Phase> · YYYY-MM-DD, then the decision ledger
     | # | Decision | Where | Group | Question | Answer | -->
