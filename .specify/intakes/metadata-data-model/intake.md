# Intake: Metadata schema and scalable data model

**Status**: Answered — 2 open items
**Scope**: feature
**Feature**: specs/009-metadata-data-model
**Slug**: metadata-data-model
**Created**: 2026-10-22
**Idea type**: new-capability

## Idea

> SQLite with sqlite-vec and custom Python Vector Databases. I want to create the Meta Data Schema and Structure. Create a new Data Modell that can scale for all current and future users when using this applications.

**Sources read**: the person's answer in this session; project intake .specify/intakes/agent-engineering-team/intake.md (stack and model answers); constitution v1.0.0

## Working interpretation

Define one metadata schema and data model — a single source of truth shared by people and agents (Lead, PSE, Review, their subagents, Jev, and Smokey's account) — stored in SQLite with sqlite-vec and a custom Python vector backend behind one interface, sized for its first year at 10 agents and 1 user on a MacBook Pro M4 Pro with about 18 GB usable RAM. Its first job is finding related knowledge with source and commit on every result; its next is tracking who did what, fed by a git-history.md knowledge graph written at the start of every coding-agent session and after every git push. Tenant ids on every row and versioned migrations let it grow beyond that first-year size.

## Sufficiency check

<!-- Status is one of: Missing | Partial | Sufficient | Delegated | N/A | Open -->

### Spec rows: spec-ready

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| S1 | Problem & context | Sufficient | idea text (create the metadata schema and structure; scale for all current and future users); Q1 | — |
| S2 | People & roles | Sufficient | Q2 | — |
| S3 | Primary journey | Sufficient | Q3, Q17 | — |
| S4 | Later journeys | Sufficient | Q13 | — |
| S5 | Capabilities & scope | Sufficient | Q5 | — |
| S6 | Information | Sufficient | Q10, Q19, Q20, Q26 | — |
| S7 | Trust, privacy & rules | Sufficient | Q9 | — |
| S8 | Edge cases | Sufficient | Q11, Q12, Q22 | — |
| S9 | Success | Sufficient | Q4, Q18 | — |
| S10 | Constraints & dependencies | Sufficient | Q6, Q21 | — |

### Plan rows: plan-ready

| # | Row | Status | Evidence | Still needed |
|---|---|---|---|---|
| T1 | Platform & form | Sufficient | project intake Q2 (LangGraph service runtime) | — |
| T2 | Stack | Sufficient | prior decision (session 2026-10-22): OCaml, Rust where applicable, Python for all data science, data engineering, data operations and data management | — |
| T3 | Storage | Sufficient | idea text (SQLite with sqlite-vec and custom Python vector databases); Q7 | — |
| T4 | Testing | Sufficient | constitution Art. IV (evidence over assertion; automated tests gate work) | — |
| T5 | Performance & scale | Sufficient | Q6, Q8 | — |
| T6 | Technical constraints | Sufficient | Q14, Q25 | — |

## Assumptions

- D1: Every record carries created_at and updated_at in UTC and a stable id that never changes — confirmed by Q21
- D2: The JSON Schemas of shared types are exported to schemas/ so Python, OCaml and Rust read the same types — prior decision (session 2026-10-22: OCaml for typed schemas)
- D3: Embeddings are stored with the model name and dimension that produced them — confirmed by Q21

## Question bank

### Q1 · Problem · S1 · impact high × uncertainty medium

What should the data model make possible that is hard today?

- [x] **A. One source of truth** — Specs, runs, knowledge and code metadata live in one queryable model instead of scattered files. *(Recommended: your answer asks for one schema and structure for everything)*
- [ ] **B. Fast search everywhere** — Hybrid search across specs, code and traces in one place.
- [ ] **C. Grow past one repo** — Many teams and repositories share one model without collisions.
- [ ] **Other**: ____

**Answer**: A. One source of truth — round 1

### Q2 · Users · S2 · impact high × uncertainty high

Who counts as a 'user' of the data model?

- [x] **A. People and agents** — People, the Lead, PSE and Review agents, their subagents, Jev and Smokey's account each get an identity. *(Recommended: agents act on records as much as people do)*
- [ ] **B. People only** — Only human accounts are users; agents act under a person's identity.
- [ ] **C. Agents only** — The model serves agent sessions; people use Gitea and the repo directly.
- [ ] **Other**: ____

**Answer**: A. People and agents — round 1

### Q3 · First job · S3 · impact high × uncertainty high

Which job should the first version of the data model do well before anything else?

- [x] **A. Find related knowledge** — Hybrid retrieval across specs, code and traces with provenance on every result. *(Recommended: retrieval already exists and needs a durable home)*
- [ ] **B. Track who did what** — Audit and lineage: which session, role and commit produced each record.
- [ ] **C. Answer catalog questions** — Which specs depend on which, which skills exist, which agents own what.
- [ ] **Other**: ____

**Answer**: A. Find related knowledge — round 1

### Q4 · Success · S9 · impact high × uncertainty high

Which target should count as success for the first release of the data model?

- [x] **A. Queries under 200 ms** — 95% of hybrid searches return within 200 ms at 1 million chunks. *(Recommended: the clearest measure of a model that scales)*
- [ ] **B. No orphan records** — Every record links to a valid owner, tenant and source; a nightly check finds zero orphans.
- [ ] **C. One schema three languages** — Python, OCaml and Rust read and write the same types with no hand-written mapping.
- [ ] **Other**: ____

**Answer**: A. Queries under 200 ms — round 1

### Q5 · Scope · S5 · impact high × uncertainty high

Which kinds of metadata must the first version of the schema cover?
*Multi-select.*

- [x] **A. Specs and decisions** — Intakes, specs, requirements, clarifications and decision ledgers. *(Recommended: the knowledge your first job searches)*
- [x] **B. Agent runtime records** — Sessions, leases, events, decision traces and Jev scans. *(Recommended: lineage and Jev need them)*
- [x] **C. Knowledge and embeddings** — Documents, chunks, vectors, and knowledge-graph entities and edges. *(Recommended: retrieval is the first job)*
- [ ] **D. Code and skills** — Repositories, commits, files, symbols and the skills catalog.
- [ ] **Other**: ____

**Answer**: A. Specs and decisions; B. Agent runtime records; C. Knowledge and embeddings — round 2
**Note**: "Then Code and skills last,Specs and decisions (Recommended),Agent runtime records (Recommended),Knowledge and embeddings (Recommended)"

### Q6 · Tenancy · S10, T5 · impact high × uncertainty high

How should the data model keep different organizations and projects apart as users grow?

- [x] **A. Tenant id on every row** — Organization, project and repository ids on every record from day one; one SQLite file to start. *(Recommended: cheapest to add now and hardest to add later)*
- [ ] **B. One database per tenant** — A separate SQLite file per organization or project.
- [ ] **C. Single tenant for now** — One shared space; ids leave room to add tenants later.
- [ ] **Other**: ____

**Answer**: A. Tenant id on every row — round 2

### Q7 · Vector DBs · T3 · impact high × uncertainty high

What should 'custom Python vector databases' mean next to sqlite-vec?

- [x] **A. One interface two backends** — A vector-store interface with sqlite-vec as the default and our own Python index as a second backend. *(Recommended: keeps sqlite-vec and your own engine interchangeable)*
- [ ] **B. Own engine only** — Build our own Python vector index and use sqlite-vec only for prototyping.
- [ ] **C. Per-domain vector stores** — Separate vector collections for specs, code and traces, each with its own backend.
- [ ] **Other**: ____

**Answer**: A. One interface two backends — round 4

### Q8 · Scale · T5 · impact high × uncertainty high

How many people and agents should the data model support in its first year?

- [ ] **A. Up to 100 users** — SQLite handles this comfortably on one machine. *(Recommended: fits the 3 sessions plus 6 subagents plus Jev capacity with room to grow)*
- [ ] **B. Up to 1000 users** — Needs per-tenant files or sharding and a tested upgrade path.
- [ ] **C. 10000 or more users** — Plan a server database migration path from day one.
- [x] **Other**: 10 Agents and 1 User

**Answer**: Other — "10 Agents and 1 User" — revised after round 5
**Note**: Revised by the person; earlier answer superseded: ~~A. Up to 100 users — round 5~~

### Q9 · Access · S7 · impact high × uncertainty medium

Who may change a metadata record once it exists?

- [x] **A. Its owning role only** — Lead owns specs, PSE owns code records, Review owns verdicts, Jev owns scans; everyone in the tenant reads. *(Recommended: matches separated authority (Art. II))*
- [ ] **B. Any member writes** — Everyone in the tenant can change any record.
- [ ] **C. Per-record access lists** — Each record lists who may read and change it.
- [ ] **Other**: ____

**Answer**: A. Its owning role only — round 2

### Q10 · Changes · S6 · impact medium × uncertainty medium

How should the schema change over time without breaking existing data?

- [x] **A. Versioned migrations** — Numbered migrations in git; every shared type exports a versioned JSON Schema. *(Recommended: the repository is the memory (Art. I))*
- [ ] **B. Flexible JSON columns** — Core columns fixed; everything else in JSON with no migrations.
- [ ] **C. Decide during planning** — Planning picks the evolution strategy within your limits.
- [ ] **Other**: ____

**Answer**: A. Versioned migrations — round 3

### Q11 · History · S8 · impact medium × uncertainty high

When the same document is indexed again at a newer commit, what should the model keep?

- [x] **A. Keep both with commits** — Old and new versions stay; search filters to what describes the current commit. *(Recommended: matches stale-chunk rejection (Art. VII))*
- [ ] **B. Replace the old one** — Only the newest version is kept.
- [ ] **C. Latest per branch** — One version per branch; older ones are dropped.
- [ ] **Other**: ____

**Answer**: A. Keep both with commits — round 3

### Q12 · Removal · S8 · impact medium × uncertainty high

When a user or agent is removed, what should happen to the records they created?

- [ ] **A. Keep and mark inactive** — Records stay for audit and lineage; the identity is marked inactive. *(Recommended: durable history (Art. I))*
- [ ] **B. Delete their records** — Their records are removed.
- [x] **C. Anonymize them** — Records stay but the identity is replaced with a placeholder.
- [ ] **Other**: ____

**Answer**: C. Anonymize them — round 4

### Q13 · Later · S4 · impact high × uncertainty high

After finding related knowledge, which job should the data model take on next?

- [x] **A. Track who did what** — Audit and lineage: which session, role and commit produced each record. *(Recommended: Jev, leases and evidence gates all need lineage)*
- [ ] **B. Answer catalog questions** — Which specs depend on which, which skills exist, which agents own what.
- [ ] **C. Nothing more yet** — Ship retrieval alone first and decide the next job from use.
- [ ] **Other**: ____

**Answer**: A. Track who did what — round 2
**Note**: "Track who did what (Recommended) and also log a "git-history.md" that get consumed by a vector database for a Knowledge Graph tool to create a new Knowledge Graph for all current and future Agent Sessions"

### Q14 · Tech limits · T6 · impact medium × uncertainty high

Which technical limits must the data model respect?
*Multi-select.*

- [ ] **A. Works offline** — Every store runs embedded in a cloud session with no outside service; only embedding calls may go out. *(Recommended: cloud sessions are ephemeral containers)*
- [ ] **B. Sensitive text stays local** — Records marked sensitive are embedded only by local models (Ollama local or offline embeddings).
- [ ] **C. Encrypted at rest** — SQLite files and vector stores are encrypted on disk.
- [ ] **D. No special limits** — Ordinary hosting and file permissions are enough.
- [x] **Other**: Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption.

**Answer**: Other — "Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption." — revised after round 5
**Note**: Revised by the person; earlier answer superseded: ~~A. Works offline; B. Sensitive text stays local; C. Encrypted at rest — round 5~~

### Q15 · Journey · S3 · impact high × uncertainty high

Which journey should the first version get right before anything else?
*Generic scaffold — sharpen to the idea before asking.*

- [ ] **A. Create and track** — Someone adds an item and follows it to done. *(Recommended: the usual starting point)*
- [ ] **B. Find and review** — Someone searches existing records and checks them.
- [ ] **C. Get notified** — Someone is told when something needs attention.
- [ ] **Other**: ____

**Answer**: Not asked — resolved by Q3 (Q3 already chose the first job: find related knowledge)

### Q16 · Success · S9 · impact high × uncertainty high

Which target should count as success for the first three months?
*Generic scaffold — sharpen to the idea before asking.*

- [ ] **A. Half the time** — The main task takes half as long as today. *(Recommended: the usual starting point)*
- [ ] **B. Zero missed items** — Nothing falls through the cracks.
- [ ] **C. Weekly use** — Most intended people use it every week.
- [ ] **Other**: ____

**Answer**: Not asked — resolved by Q4 (Q4 already set the headline target: queries under 200 ms)

### Q17 · Acceptance · S3 · impact high × uncertainty medium

When an agent searches for related knowledge, what must every result carry for the search to count as working?

- [x] **A. Source and commit** — Path, heading, commit id and tenant on every result; stale results never appear. *(Recommended: provenance is what makes results trustworthy (Art. VII))*
- [ ] **B. Owner and lineage** — Who created the record, in which session, plus its source.
- [ ] **C. Score only** — A relevance score is enough; provenance is looked up on demand.
- [ ] **Other**: ____

**Answer**: A. Source and commit — round 3

### Q18 · Measures · S9 · impact medium × uncertainty high

Which other measures should the first release of the data model also be judged on?
*Multi-select.*

- [x] **A. Zero orphan records** — A nightly check finds no record without a valid owner, tenant and source.
- [x] **B. One schema three languages** — Python, OCaml and Rust read and write the same exported types.
- [x] **C. Index rebuilt in 10 minutes** — A full re-index of one repository finishes within 10 minutes.
- [ ] **Other**: ____

**Answer**: A. Zero orphan records; B. One schema three languages; C. Index rebuilt in 10 minutes — round 3

### Q19 · Git history · S6 · impact high × uncertainty high

What should each git-history.md entry record for the knowledge graph?
*Multi-select.*

- [x] **A. Commit and message** — Commit id, parent, author account, time and message. *(Recommended: the backbone of every lineage edge)*
- [x] **B. Session and role** — Which agent session, role (Lead, PSE, Review) and subagent made it. *(Recommended: the knowledge graph is for agent sessions)*
- [x] **C. Files and symbols** — Paths and code symbols the commit touched. *(Recommended: links commits to code knowledge)*
- [ ] **D. Spec task and issue** — The spec requirement, task id and Gitea issue the commit served.
- [ ] **Other**: ____

**Answer**: A. Commit and message; B. Session and role; C. Files and symbols — round 4

### Q20 · Log timing · S6 · impact medium × uncertainty high

When should git-history.md be written and fed to the vector store?

- [ ] **A. After every commit** — A post-commit hook appends the entry and indexes it right away. *(Recommended: the graph stays current for the next session)*
- [ ] **B. At session end** — Each session appends its commits when it stops or hands off.
- [ ] **C. On a schedule** — A periodic job such as the 10-minute Jev scan appends new commits.
- [x] **Other**: At the start of every Coding Agent Session and after every git push.

**Answer**: Other — "At the start of every Coding Agent Session and after every git push." — revised after round 5
**Note**: Revised by the person; earlier answer superseded: ~~A. After every commit — round 5~~

### Q21 · Defaults · S10 · impact medium × uncertainty medium

Which of these defaults should stay as written?
*Multi-select.*

- [x] **A. Keep D1** — Every record carries created_at and updated_at in UTC and a stable id that never changes
- [x] **B. Keep D3** — Embeddings are stored with the model name and dimension that produced them
- [ ] **Other**: ____

**Answer**: A. Keep D1; B. Keep D3 — round 4

### Q22 · Offline · S8 · impact medium × uncertainty high

If the embedding model (Ollama or Claude) is unreachable while records are being indexed, what should the data model do?

- [x] **A. Store now embed later** — Records are saved with text and metadata; vectors are queued and filled in when the model is back; keyword search works meanwhile. *(Recommended: no record is lost and search degrades gracefully)*
- [ ] **B. Use offline embeddings** — Fall back to the built-in offline hashing embeddings and re-embed later.
- [ ] **C. Fail the write** — Refuse to save until the model is reachable.
- [ ] **Other**: ____

**Answer**: A. Store now embed later — round 5

### Q25 · Mac limits · T6 · impact medium × uncertainty high

Your MacBook answer replaced the earlier limits. Which of these should still apply alongside the M4 Pro with about 18 GB usable RAM?
*Multi-select.*

- [x] **A. Works offline** — Every store runs on the Mac with no outside service; only cloud model calls (Claude or Ollama cloud) go out. *(Recommended: cloud models are allowed)*
- [x] **B. Sensitive text stays local** — Records marked sensitive are embedded only by local Ollama or the offline embeddings. *(Recommended: privacy)*
- [x] **C. FileVault encryption** — macOS full-disk encryption covers the SQLite and vector files; no separate database encryption. *(Recommended: zero setup)*
- [x] **D. Database file encryption** — The database files themselves are encrypted too (SQLCipher-style); needs a check that sqlite-vec still loads.
- [ ] **Other**: ____

**Answer**: A. Works offline; B. Sensitive text stays local; C. FileVault encryption; D. Database file encryption — after round 5

### Q26 · Git history · S6 · impact medium × uncertainty high

A git-history.md entry written after a push can't be inside that push. How should the file be kept?

- [x] **A. Generated and gitignored** — Rebuilt from git log at every session start and appended after each push; indexed for the knowledge graph but never committed. Git stays the source. *(Recommended: git is already the record)*
- [ ] **B. Committed at session start** — Each session regenerates and commits it first.
- [ ] **C. Committed after each push** — An extra commit and push after every push.
- [ ] **Other**: ____

**Answer**: A. Generated and gitignored — after round 5

## Clarifications

### Session 2026-10-22

- Q: Who counts as a 'user' of the data model? → A: People and agents
- Q: Which job should the first version of the data model do well before anything else? → A: Find related knowledge
- Q: Which target should count as success for the first release of the data model? → A: Queries under 200 ms
- Q: What should the data model make possible that is hard today? → A: One source of truth
- Q: Which kinds of metadata must the first version of the schema cover? → A: Specs and decisions; Agent runtime records; Knowledge and embeddings — note: "Then Code and skills last,Specs and decisions (Recommended),Agent runtime records (Recommended),Knowledge and embeddings (Recommended)"
- Q: After finding related knowledge, which job should the data model take on next? → A: Track who did what — note: "Track who did what (Recommended) and also log a "git-history.md" that get consumed by a vector database for a Knowledge Graph tool to create a new Knowledge Graph for all current and future Agent Sessions"
- Q: How should the data model keep different organizations and projects apart as users grow? → A: Tenant id on every row
- Q: Who may change a metadata record once it exists? → A: Its owning role only
- Q: When the same document is indexed again at a newer commit, what should the model keep? → A: Keep both with commits
- Q: When an agent searches for related knowledge, what must every result carry for the search to count as working? → A: Source and commit
- Q: Which other measures should the first release of the data model also be judged on? → A: Zero orphan records; One schema three languages; Index rebuilt in 10 minutes
- Q: How should the schema change over time without breaking existing data? → A: Versioned migrations
- Q: Which of these defaults should stay as written? → A: Keep D1; Keep D3
- Q: What should each git-history.md entry record for the knowledge graph? → A: Commit and message; Session and role; Files and symbols
- Q: When a user or agent is removed, what should happen to the records they created? → A: Anonymize them
- Q: What should 'custom Python vector databases' mean next to sqlite-vec? → A: One interface two backends
- Q: If the embedding model (Ollama or Claude) is unreachable while records are being indexed, what should the data model do? → A: Store now embed later
- Q: When should git-history.md be written and fed to the vector store? → A: After every commit
- Q: How many people and agents should the data model support in its first year? → A: Up to 100 users
- Q: Which technical limits must the data model respect? → A: Works offline; Sensitive text stays local; Encrypted at rest
- Q: When should git-history.md be written and fed to the vector store? → A: "At the start of every Coding Agent Session and after every git push." (revised; supersedes: A. After every commit — round 5)
- Q: How many people and agents should the data model support in its first year? → A: "10 Agents and 1 User" (revised; supersedes: A. Up to 100 users — round 5)
- Q: Which technical limits must the data model respect? → A: "Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption." (revised; supersedes: A. Works offline; B. Sensitive text stays local; C. Encrypted at rest — round 5)
- Q: Your MacBook answer replaced the earlier limits. Which of these should still apply alongside the M4 Pro with about 18 GB usable RAM? → A: Works offline; Sensitive text stays local; FileVault encryption; Database file encryption (follow-up after round 5)
- Q: A git-history.md entry written after a push can't be inside that push. How should the file be kept? → A: Generated and gitignored (follow-up after round 5)

## Session Log

| Round | Questions | Answered | Rows sufficient | Notes |
|---|---|---|---|---|
| 0 | — | — | 3 of 16 | Settled before asking: T1, T2, T4. Drawn from: .specify/memory/constitution.md › Agent Engineering Team Constitution › Additional Constraints @ bb2152b2; .specify/memory/constitution.md @ bb2152b2; .specify/memory/constitution.md › Agent Engineering Team Constitution › Core Principles › III. Agents Propose, Policy Decides @ bb2152b2; .specify/memory/constitution.md › Agent Engineering Team Constitution › Core Principles › V. Specification Before Build @ bb2152b2; AGENTS.md › AGENTS.md › Governing principles @ bb2152b2. |
| 1 | Q2, Q3, Q4, Q1 | 4 | 5 of 16 |  |
| 2 | Q5, Q13, Q6, Q9 | 4 | 9 of 16 |  |
| 3 | Q11, Q17, Q18, Q10 | 4 | 11 of 16 |  |
| 4 | Q21, Q19, Q12, Q7 | 4 | 12 of 16 |  |
| 5 | Q22, Q20, Q8, Q14 | 4 | 16 of 16 |  |
| revision after 5 | Q20 | 1 | 16 of 16 | Person revised an earlier answer. |
| revision after 5 | Q8 | 1 | 16 of 16 | Person revised an earlier answer. |
| revision after 5 | Q14 | 1 | 16 of 16 | Person revised an earlier answer. |
| follow-up after 5 | Q25, Q26 | 2 | 16 of 16 | Limits kept alongside the MacBook; git-history.md generated and gitignored. |

## Open Items

- [NEEDS CLARIFICATION: can sqlite-vec meet p95 under 200 ms at 1 million chunks?] — for planning — sqlite-vec searches by brute force, and 1 million 768-dimension vectors is about 3 GB to scan per query; quantization, smaller dimensions or the custom Python backend (an ANN index) may be needed; the target machine is a MacBook Pro M4 Pro with about 18 GB usable RAM (Q14, revised) — cites Q4, Q7, Q8, Q14 — UNVERIFIED until benchmarked
- [NEEDS CLARIFICATION: encryption at rest with sqlite-vec loaded] — for planning — an encrypted SQLite build (for example SQLCipher) must still load the sqlite-vec extension, and the custom Python backend's files need the same protection — cites Q7, Q25 (database file encryption kept alongside FileVault) — UNVERIFIED until a first install is tried
- ~~[NEEDS CLARIFICATION: how git-history.md is versioned] — for planning — it is written at the start of every coding-agent session and after every git push (Q20, revised), and an entry written after a push cannot be part of that push; choose between committing it with the next commit, keeping it untracked and indexed, or generating it from git log at session start — cites Q13, Q20 (inferred conflict)~~ resolved by Q26 (generated and gitignored)

## Phase Refinements
