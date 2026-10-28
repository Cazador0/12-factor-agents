# Intake: Engineering team of coding-agent sessions (Lead, PSE, Review)

**Status**: Answered — 5 open items
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
| C2 | Principles | Sufficient | report §Final recommended operating doctrine (eleven invariants); report §Safe autonomous merge ("Agents may operate autonomously inside the rules; they may not autonomously weaken the rules"); Q3 | — |
| C3 | Quality bar | Sufficient | report §Independent quality assurance and engineering gates; §Merge evidence gate ("Not run" must never silently mean "passed") | — |
| C4 | Constraints | Sufficient | Q1 (Gitea only); Q2 (LangGraph service); report §Gitea as the real-time engineering control plane (narrow MCP tool surface, mutation envelope); Q1, Q2 | — |
| C5 | Workflow & approvals | Sufficient | report §Risk-based escalation table; §Spec Kit stage ownership table; §Progressive autonomy | — |
| C6 | Governance | Partial | report §Safe autonomous merge (agents never self-authorize changes to policy, gates or permissions) | who besides the owner may approve constitution amendments; versioning scheme rests on unconfirmed D6 |

### Spec rows: spec-ready

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| S1 | Problem & context | Sufficient | report §Executive architecture (free-chatting agents are unsafe; conversations are transient, not the system of record); Q5 | — |
| S2 | People & roles | Sufficient | report §The three-agent operating model (Lead, PSE, Review authority table); human owner at product intent and elevated-risk review (§Progressive autonomy) | — |
| S3 | Primary journey | Sufficient | report §Lead contract (execution loop); §Review contract (PSE → PR → Review loop); first release runs in Shadow mode per report §Progressive autonomy | — |
| S4 | Later journeys | Sufficient | report §Progressive autonomy: Agent implementation → Guarded autonomous → Long-horizon → Self-improving modes, in that order | — |
| S5 | Capabilities & scope | Sufficient | report §Reference implementation blueprint (five components); Q4 (constitution plus full spec set: control plane, forge gateway, role contracts, Spec Kit bridge, context/RAG, quality gates, autonomy); Q4 | — |
| S6 | Information | Sufficient | report: implementation evidence, review verdict, normalized event, issue contract, task-issue map, session checkpoint, lease, write-set estimate, quality gate manifest; Q3 (decision traces + visible reasoning chains); Q3 | — |
| S7 | Trust, privacy & rules | Sufficient | report §Safe autonomous merge (protected `main`, no force-merge tool, risk classes); §Gitea MCP (no unrestricted request tool); OWASP ASVS 5.0.0, NIST SSDF 1.1, SLSA cited in §Independent quality assurance | — |
| S8 | Edge cases | Sufficient | report §Agentic-framework verification (idempotency, ordering, concurrency, prompt injection, long-horizon recovery, failure recovery, RAG grounding) | — |
| S9 | Success | Partial | report §Core metrics lists the scorecard but sets no numbers or timeframes | a headline target with a number and a timeframe the person confirms |
| S10 | Constraints & dependencies | Partial | Q1 (Gitea 28.x); Q2 (LangGraph service); report §Gitea 28.2.0 current release | time, budget and who operates the Gitea instance |

### Plan rows: plan-ready

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| T1 | Platform & form | Sufficient | Q2 (LangGraph service hosting the three roles); report §Reference implementation blueprint (webhook gateway, event store, state machine, scheduler, Gitea MCP gateway); Q2 | — |
| T2 | Stack | Sufficient | Q6; Q7; Q10; Q14 | — |
| T3 | Storage | Sufficient | Q9; Q16; metadata-data-model intake (spec 009) | — |
| T4 | Testing | Sufficient | report §Verification layers table; §Agentic-framework verification; "every recurring agent mistake becomes a regression fixture, then an evaluation" | — |
| T5 | Performance & scale | Sufficient | Q18; Q20; metadata-data-model intake Q8 (10 agents and 1 user) | — |
| T6 | Technical constraints | Sufficient | Q1; Q22; metadata-data-model intake Q14 (MacBook Pro M4 Pro, about 18 GB usable) | — |

## Assumptions

- ~~D1: The LangGraph service, gateways and engines are written in Python 3.12+.~~ overturned by Q6 and Q10 (OCaml, Rust where applicable, Python for all data work)
- ~~D2: Role agents call Claude (`claude-opus-5-5`) through the official `anthropic` SDK from inside LangGraph nodes.~~ revised by Q7 and Q14: Ollama (cloud and local) alongside Claude models; constitution v1.1.0
- D3: The retrieval index runs offline by default: lexical BM25 plus hashed dense vectors, with an optional external embedder. — confirmed in part by Q9 (stored in SQLite with sqlite-vec and a custom Python vector backend; spec 009)
- D4: This repository hosts the skill catalog through `bin/intakespec`; `../intakeSpec` is used when present. — unconfirmed (Q8 skipped)
- D5: Spec Kit v1.2.2 with the intake, assess, bug and agent-context extensions; the git extension is left out because cloud sessions stay on one assigned branch. — agent setup choice, unconfirmed
- D6: The constitution uses semantic versioning with a Sync Impact Report, the Spec Kit default. — confirmed by Q14
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
- [x] **Other**: OCaml and Python; Markdown; a vector DB; SQLite; knowledge graphs.

**Answer**: Other — "OCaml and Python; Markdown; a vector DB; SQLite; knowledge graphs." — answered after round 2
**Note**: Answered after the session; was ~~Open — skipped in round 1 (the person sent the attached files instead); D1 applies until confirmed~~

### Q7 · Models · T2, T6 · impact medium × uncertainty medium

Which models and embeddings should the RAG and reasoning chains use?

- [ ] **A. Claude plus offline embeddings** — Claude via langchain-anthropic for reasoning. Local BM25 plus fastembed vectors, so retrieval works with no extra API key. *(Recommended: works in every cloud session with no extra secret)*
- [ ] **B. Claude plus Voyage AI** — Anthropic's recommended embedding partner. Better retrieval quality but needs a VOYAGE_API_KEY secret.
- [ ] **C. Provider-agnostic** — Any LangChain chat model and embedder chosen by config. Most flexible but more setup per session.
- [x] **Other**: Ollama (cloud and local) alongside Claude Code models.

**Answer**: Other — "Ollama (cloud and local) alongside Claude Code models." — answered after round 2
**Note**: Answered after the session; was ~~Open — skipped in round 1; D2 and D3 apply until confirmed~~

### Q8 · Catalog · T3 · impact low × uncertainty medium

Your route skill expects the Cazador0/intakeSpec catalog, which this session can't reach. What should the new router index instead?

- [ ] **A. Local skills plus Spec Kit** — Index every SKILL.md in the repo, ~/.claude/skills, and Spec Kit commands. Works offline and in every cloud session. *(Recommended: no access grant needed)*
- [ ] **B. intakeSpec when present** — Keep the ../intakeSpec contract and fall back to local skills when it's missing. I'll need you to grant repo access.
- [ ] **C. Add intakeSpec now** — You grant this session access to the private repo so I can clone and index its 377 skills.
- [ ] **Other**: ____

**Answer**: Open — deferred by the person; kept as a to-do in Open Items — after round 2
**Note**: Answered after the session: the skill catalog is deferred (handoff record).

### Q9 · Data stores · T3 · impact high × uncertainty high

Your stack lists 'a vector DB' and 'knowledge graphs' with SQLite, but no product. Which stores should the specs and code use?

- [ ] **A. SQLite with sqlite-vec** — One SQLite file holds vectors (sqlite-vec) and graph tables. *(Recommended: zero extra services)*
- [ ] **B. LanceDB and Kùzu** — Embedded vector DB plus an embedded property-graph DB.
- [ ] **C. Decide during planning** — /speckit-plan researches the stores within your limits.
- [x] **Other**: SQLite with sqlite-vec and custom Python Vector Databases. I want to create the Meta Data Schema and Structure. Create a new Data Modell that can scale for all current and future users when using this applications.

**Answer**: Other — "SQLite with sqlite-vec and custom Python Vector Databases. I want to create the Meta Data Schema and Structure. Create a new Data Modell that can scale for all current and future users when using this applications." — after round 2
**Note**: Opened the feature intake .specify/intakes/metadata-data-model/intake.md (spec 009).

### Q10 · Languages · T2 · impact high × uncertainty high

Which parts are OCaml and which stay Python?

- [ ] **A. Python engines stay** — Python engines stay; OCaml for the typed event and message schemas and the policy and decision core. *(Recommended: typed core, Python data work)*
- [ ] **B. All OCaml** — Rewrite the engines in OCaml.
- [ ] **C. All Python** — Keep everything in Python; OCaml later.
- [x] **Other**: Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management.

**Answer**: Other — "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." — after round 2
**Note**: 'Defaults' read as the recommended option (Python engines stay; OCaml for the typed event and message schemas and the policy and decision core) (inferred from the question's recommendation). Question asked before the handoff; wording reconstructed from the handoff record.

### Q11 · Top approver · C5 · impact high × uncertainty high

Who may approve promotion to the Long-horizon and Self-improving autonomy modes (spec 007 FR-009)?

- [ ] **A. Owner only** — Only the project owner approves. *(Recommended: Art. VI)*
- [ ] **B. Lead agent** — The Lead approves.
- [ ] **C. Two people** — Two people must approve.
- [x] **Other**: an agent called Smokey, and Smokey should be the only one

**Answer**: Other — "an agent called Smokey, and Smokey should be the only one" — after round 2
**Note**: Question asked before the handoff; wording reconstructed from the handoff record. Clarified by Q12 and Q13.

### Q12 · Smokey role · C5 · impact high × uncertainty high

You said Smokey 'should be the only one'. The only one who may do what? (I read Jev and Smokey as two different agents: Jev watches sessions, Smokey approves.)

- [x] **A. Sole top-mode approver** — Only Smokey may approve promotion to Long-horizon and Self-improving modes (spec 007 FR-009). *(Recommended: matches the current reading)*
- [ ] **B. Approves every promotion** — Only Smokey may approve any promotion.
- [ ] **C. Sole high-risk approver** — Smokey approves all promotions and every High and Critical risk merge.
- [ ] **Other**: ____

**Answer**: A. Sole top-mode approver — after round 2
**Note**: The question stated the reading that Jev and Smokey are two different agents; the person picked an option without objecting (inferred confirmation).

### Q13 · Smokey type · C5, C6 · impact high × uncertainty high

Is Smokey an autonomous agent or an account a person controls? Art. VI says agents may not authorize changes to their own authority.

- [x] **A. A person's account** — A person acts as Smokey in Gitea; Art. VI stands unchanged. *(Recommended: no amendment needed)*
- [ ] **B. Agent with your sign-off** — Smokey recommends; each promotion needs your confirmation.
- [ ] **C. Fully autonomous agent** — Smokey decides alone; needs an Art. VI exception.
- [ ] **Other**: ____

**Answer**: A. A person's account — after round 2

### Q14 · Ollama · C4, T2 · impact high × uncertainty high

The constitution allows Claude only, through the official SDK. Adding Ollama (cloud and local) amends it. How should I handle that?

- [x] **A. Amend to v1.1.0** — Minor version bump with a Sync Impact Report: Ollama cloud and local become allowed alongside Claude. *(Recommended: keeps decisions in code)*
- [ ] **B. Ollama local only** — Allow self-hosted Ollama only.
- [ ] **C. Hold the amendment** — Keep Claude-only for now.
- [ ] **Other**: ____

**Answer**: A. Amend to v1.1.0 — after round 2

### Q15 · Gitea bots · C4, S7 · impact high × uncertainty medium

How should agents authenticate to Gitea (spec 002)?

- [ ] **A. Answer as recorded** — Each role gets its own Gitea bot account. *(Recommended: the person's answer)*
- [ ] **B. Decide during planning** — Planning decides.
- [x] **Other**: Each role gets its own Gitea bot account.

**Answer**: Other — "Each role gets its own Gitea bot account." — after round 2
**Note**: Question asked before the handoff; wording reconstructed from the handoff record; answer recorded as written in the handoff.

### Q16 · Event limit · T3 · impact high × uncertainty medium

How long are raw deliveries and normalized events kept (spec 001 FR-007)?

- [ ] **A. Answer as recorded** — Events have no time limit. *(Recommended: the person's answer)*
- [ ] **B. Decide during planning** — Planning decides.
- [x] **Other**: Events have no time limit.

**Answer**: Other — "Events have no time limit." — after round 2
**Note**: Question asked before the handoff; wording reconstructed from the handoff record; answer recorded as written in the handoff.

### Q17 · Stopping · S8 · impact high × uncertainty medium

When should a running session be stopped?

- [ ] **A. Answer as recorded** — A session stops only when it is not making successful progress or is stuck. *(Recommended: the person's answer)*
- [ ] **B. Decide during planning** — Planning decides.
- [x] **Other**: A session stops only when it is not making successful progress or is stuck.

**Answer**: Other — "A session stops only when it is not making successful progress or is stuck." — after round 2
**Note**: Question asked before the handoff; wording reconstructed from the handoff record; answer recorded as written in the handoff.

### Q18 · Subagents · T5 · impact high × uncertainty medium

How many subagents may run at once?

- [ ] **A. Answer as recorded** — At most 2 subagents per container, per role and per Gitea bot account. *(Recommended: the person's answer)*
- [ ] **B. Decide during planning** — Planning decides.
- [x] **Other**: At most 2 subagents per container, per role and per Gitea bot account.

**Answer**: Other — "At most 2 subagents per container, per role and per Gitea bot account." — after round 2
**Note**: Question asked before the handoff; wording reconstructed from the handoff record; answer recorded as written in the handoff.

### Q19 · Stuck · S8 · impact high × uncertainty medium

What does 'stuck' mean?

- [ ] **A. Answer as recorded** — A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing. *(Recommended: the person's answer)*
- [ ] **B. Decide during planning** — Planning decides.
- [x] **Other**: A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing.

**Answer**: Other — "A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing." — after round 2
**Note**: Question asked before the handoff; wording reconstructed from the handoff record; answer recorded as written in the handoff.

### Q20 · Capacity · T5 · impact high × uncertainty medium

What is the peak capacity the system must sustain (spec 001 FR-021)?

- [ ] **A. Answer as recorded** — 3 agent sessions + 6 subagents + the Jev agent. *(Recommended: the person's answer)*
- [ ] **B. Decide during planning** — Planning decides.
- [x] **Other**: 3 agent sessions + 6 subagents + the Jev agent.

**Answer**: Other — "3 agent sessions + 6 subagents + the Jev agent." — after round 2
**Note**: Question asked before the handoff; wording reconstructed from the handoff record; answer recorded as written in the handoff.

### Q21 · Stuck action · S8 · impact high × uncertainty high

When a session is stuck: stop it automatically, or escalate to the user or Smokey first?

- [x] **A. Checkpoint stop escalate** — Checkpoint and stop, then escalate. *(Recommended: safe and recoverable)*
- [ ] **B. Escalate first** — Ask the user or Smokey before stopping.
- [ ] **C. Stop only** — Stop without escalating.
- [ ] **Other**: ____

**Answer**: A. Checkpoint stop escalate — after round 2
**Note**: "Yes - But if "Answers" number "2." and "3." are still unclear to you or if you any questions ask th euser." (the person's words; "Yes" read as the recommended option)

### Q22 · Hosting · T1, T6 · impact high × uncertainty high

Where should Gitea, the LangGraph service and the local Ollama models run?

- [x] **A. All on the MacBook** — Gitea, the service, SQLite and local Ollama share the about 18 GB usable RAM. *(Recommended: fits 10 agents and 1 user)*
- [ ] **B. Mac plus another machine** — Gitea and Ollama on a second machine.
- [ ] **C. Cloud sessions plus Mac** — Coding sessions in Claude Code cloud.
- [ ] **Other**: ____

**Answer**: A. All on the MacBook — after round 2
**Note**: Machine: MacBook Pro M4 Pro, 24 GB RAM, about 18 GB usable after macOS (metadata-data-model intake Q14, revised).

### Q23 · Cost gate · S9 · impact medium × uncertainty high

Spec 007 asks: should a cost ceiling per accepted issue block promotion to a higher autonomy mode?

- [x] **A. Inform Smokey only** — Cost per accepted issue is on the scorecard Smokey sees; it never blocks promotion by itself. *(Recommended: the report's target excludes cost)*
- [ ] **B. Block above a ceiling** — Promotion is refused above a ceiling.
- [ ] **C. Leave cost out** — Promotion ignores cost.
- [ ] **Other**: ____

**Answer**: A. Inform Smokey only — after round 2

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
- Q: Which language should the skills' source code (LangChain/LangGraph/RAG) be written in? → A: "OCaml and Python; Markdown; a vector DB; SQLite; knowledge graphs." (answered after the session)
- Q: Which models and embeddings should the RAG and reasoning chains use? → A: "Ollama (cloud and local) alongside Claude Code models." (answered after the session)
- Q: Your route skill expects the Cazador0/intakeSpec catalog, which this session can't reach. What should the new router index instead? → A: Deferred; record it as a to-do in Open Items (answered after the session)
- Q: Your stack lists 'a vector DB' and 'knowledge graphs' with SQLite, but no product. Which stores should the specs and code use? → A: "SQLite with sqlite-vec and custom Python Vector Databases. I want to create the Meta Data Schema and Structure. Create a new Data Modell that can scale for all current and future users when using this applications." (answered after the session; detailed in the metadata-data-model intake)
- Q: Which parts are OCaml and which stay Python? → A: "Defaults + OCaml, Rust where applicable, and Python for all Data Science, Data Engineering, Data Operations, and full scale Data Management." (answered after the session)
- Q: Who may approve promotion to the Long-horizon and Self-improving autonomy modes (spec 007 FR-009)? → A: "an agent called Smokey, and Smokey should be the only one" (answered after the session)
- Q: You said Smokey 'should be the only one'. The only one who may do what? (I read Jev and Smokey as two different agents: Jev watches sessions, Smokey approves.) → A: Sole top-mode approver (answered after the session)
- Q: Is Smokey an autonomous agent or an account a person controls? Art. VI says agents may not authorize changes to their own authority. → A: A person's account (answered after the session)
- Q: The constitution allows Claude only, through the official SDK. Adding Ollama (cloud and local) amends it. How should I handle that? → A: Amend to v1.1.0 (answered after the session)
- Q: How should agents authenticate to Gitea (spec 002)? → A: "Each role gets its own Gitea bot account." (answered after the session)
- Q: How long are raw deliveries and normalized events kept (spec 001 FR-007)? → A: "Events have no time limit." (answered after the session)
- Q: When should a running session be stopped? → A: "A session stops only when it is not making successful progress or is stuck." (answered after the session)
- Q: How many subagents may run at once? → A: "At most 2 subagents per container, per role and per Gitea bot account." (answered after the session)
- Q: What does 'stuck' mean? → A: "A command, the terminal, thought-chaining or reasoning stops making progress, or bad code keeps failing." (answered after the session)
- Q: What is the peak capacity the system must sustain (spec 001 FR-021)? → A: "3 agent sessions + 6 subagents + the Jev agent." (answered after the session)
- Q: When a session is stuck: stop it automatically, or escalate to the user or Smokey first? → A: Checkpoint and stop, then escalate (answered after the session)
- Q: Where should Gitea, the LangGraph service and the local Ollama models run? → A: All on the MacBook (answered after the session)
- Q: Spec 007 asks: should a cost ceiling per accepted issue block promotion to a higher autonomy mode? → A: Inform Smokey only (answered after the session)

## Session Log

| Round | Questions | Answered | Rows sufficient | Notes |
|---|---|---|---|---|
| 0 | — | — | 12 of 22 | Drawn from the attached report. Settled before the first question: C1, C2, C3, C5, S1, S2, S3, S4, S6, S7, S8, T4. No constitution or prior decisions existed. |
| 1 | Q5, Q6, Q7, Q8 | 1 of 4 | 12 of 22 | The person answered by attaching the files (Q5); Q6–Q8 were skipped. |
| 2 | Q1, Q2, Q3, Q4 | 4 of 4 | 15 of 22 | C4, S5 and T1 became Sufficient. Session ended: the person asked for the constitution and specs; remaining rows set Open. |
| revision after 2 | Q6 | 1 | 17 of 22 | Person revised an earlier answer. |
| revision after 2 | Q7 | 1 | 17 of 22 | Person revised an earlier answer. |
| after round 2 | Q6–Q23 | 17 | 19 of 22 | Answers given after the session (handoff record and later rounds); one deferred to-do (Q8). |

## Open Items

- ~~[NEEDS CLARIFICATION: implementation language for the LangGraph service, gateways and engines] — for planning — Python 3.12+ is assumed (D1) but the person skipped the question — cites Q6 — UNVERIFIED until the person confirms~~ resolved by Q6, Q10
- ~~[NEEDS CLARIFICATION: Claude model and embedding backend for the role agents and retrieval index] — for planning — `claude-opus-5-5` with offline hybrid retrieval is assumed (D2, D3) — cites Q7 — UNVERIFIED until the person confirms~~ resolved by Q7, Q14, Q9
- [NEEDS CLARIFICATION: which skill catalog the router indexes] — for planning — this repository as host is assumed (D4) — cites Q8 — UNVERIFIED until the person confirms or grants intakeSpec access — TO-DO: deferred by the person (Q8)
- [NEEDS CLARIFICATION: whether this GitHub-hosted repository is mirrored into the Gitea instance] — for planning — Gitea now runs on the MacBook with everything else (Q22) — cites Q1, Q22 — UNVERIFIED until a Gitea instance answers the gateway's version check
- [NEEDS CLARIFICATION: how per-session isolation and lifecycle hooks (the report's Codex worktrees and hooks) map onto the LangGraph service] — for planning — the runtime answer replaced the harness the report assumed — cites Q2 — UNVERIFIED until a first PSE run in Shadow mode
- ~~[NEEDS CLARIFICATION: headline success target with a number and a timeframe] — for specify (spec 007) — the report names the scorecard metrics but no targets; spec success criteria carry proposed defaults — cites Q4~~ resolved by R5 (Phase Refinements)
- ~~[NEEDS CLARIFICATION: expected scale — concurrent sessions, issues per week, events per day] — for planning — no numbers in the report — cites none (row T5 never asked)~~ resolved by Q18, Q20 (issues per week and events per day remain planning estimates)
- ~~[NEEDS CLARIFICATION: where the event store, leases and retrieval index are stored] — for planning — the report fixes the systems of record but not the control plane's own storage — cites none (row T3 never asked)~~ resolved by Q9, Q16 (spec 009)
- [NEEDS CLARIFICATION: who besides the owner may approve constitution amendments, and the time and budget for the first release] — for constitution and planning — the report rules out agent self-amendment but names no approvers, time or budget — cites none (rows C6, S10 never asked)

## Phase Refinements

<!-- Written by the refine command: ### <Phase> · YYYY-MM-DD, then the decision ledger
     | # | Decision | Where | Group | Question | Answer | -->

### Specify · 2026-10-22

| # | Decision | Where | Group | Question | Answer |
|---|---|---|---|---|---|
| R1 | How the 3 agent sessions are divided among Lead, PSE and Review | spec 001 FR-035 | Unbacked | Spec 001 caps the team at 3 agent sessions. How should those 3 be split between Lead, PSE and Review? | "One per role (Recommended)" — one session each for Lead, PSE and Review; at most one issue in build at a time |
| R2 | Who may switch Lead into implementation-worker mode | spec 003 (Lead contract) | Unbacked | Spec 003: Lead normally plans and does not write code. Who may switch Lead into implementation-worker mode for an issue? Lead may never grant this to itself (Art. VI). | "Owner, per issue (Recommended)" — a person (the owner) approves each switch, per issue |
| R3 | How a person applies the bridge's dry-run plan in Shadow mode | spec 004 FR-022; spec 002 FR-024; spec 007 FR-002 | Unbacked | Spec 004: in Shadow mode, the Spec Kit→Gitea bridge only produces a dry-run plan. How should a person apply that plan? | "Both Create issues by hand and Approve; gateway writes it" — both paths: a person creates the issues by hand (the bridge reports them unconfirmed for Lead to confirm), or a person approves the plan and the gateway carries it out as a human-approved write (changes spec 002 FR-024 and spec 007 FR-002) |
| R4 | Adding read-only issue search and milestone lookup to the gateway | spec 004; spec 002 tool set | Unbacked (Critical-risk change, needs a person) | Spec 004: do you approve adding read-only issue search (by feature/task ID or label) and milestone lookup to the Gitea gateway? | "Approve read-only search (Recommended)" — a person approved it (Art. VI; spec 002 FR-003) |
| R5 | The headline autonomy target | spec 007 SC-004 | Unbacked | Spec 007's headline goal: what should autonomy deliver? The guardrails (escaped defects, reverts, security incidents, human recovery cost no worse than the Shadow-mode baseline) apply whichever is picked. | "+30% in 3 months (Recommended)" — accepted issues per week rise by at least 30% within 3 months of reaching Guarded autonomous mode, compared with Shadow mode, at the fixed capacity of 3 sessions, 6 subagents and Jev |
| R6 | Jev's durable-progress (spinning) window | spec 008 FR-015 | Unbacked | Spec 008: Jev calls a session spinning after a window with no durable progress. The research suggests 60 minutes; no source fixes it. How should it be set? | "60 min, per role later (Recommended)" — 60 minutes for every role now; after the first weeks of scan history, values per role (Lead, PSE, Review) are proposed and a person approves the change |
| R7 | Where the lease epoch fence lives | spec 008 FR-029 step 5; spec 001 FR-032 | Unbacked (branch protection is set by a person, Art. VI) | Spec 008: when a stale session's lease is revoked, where should the epoch fence live? (Coordination layer only, or also a required commit status.) | "Both" (the person's own answer) — read as: the coordination-layer fence (spec 001 FR-032) and also a lease-epoch commit status that branch protection requires, so a commit from a stale epoch can never merge; which component posts the status is (inferred) |
| R8 | What the issue's jev/* label shows when several sessions share an issue | spec 008 FR-036 | Unbacked | Several sessions can work on one issue, but jev/* labels are exclusive. What should the issue's label show? | "All three" (the person's own answer), confirmed in a follow-up as "Role labels + summary (Recommended)" — each role's session gets its own label (jev/pse/stuck, jev/review/warning, …) showing its latest verdict, and the summary label jev/warning, jev/stuck or jev/parked shows the most severe; a person creates the 12 labels once |
