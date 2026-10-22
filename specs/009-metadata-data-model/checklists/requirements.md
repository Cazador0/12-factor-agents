# Specification Quality Checklist: Metadata Schema and Scalable Data Model

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [ ] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [ ] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [ ] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [x] Feature meets measurable outcomes defined in Success Criteria
- [ ] No implementation details leak into specification

## Notes

- **Unticked: "No implementation details (languages, frameworks, APIs)"**. This item is not true. The spec names technology because the data model is the person's own technology request. The idea text reads "SQLite with sqlite-vec and custom Python Vector Databases. I want to create the Meta Data Schema and Structure." Every named technology was fixed by the person:
  - SQLite, sqlite-vec and the custom Python vector backend behind one interface (project intake Q9; data-model intake Q7);
  - versioned JSON Schemas in `schemas/` and numbered migrations in git (data-model intake Q10);
  - Python, OCaml and Rust (project intake Q10; data-model intake Q18);
  - Claude and Ollama (project intake Q7, Q14);
  - FileVault and database file encryption (data-model intake Q25);
  - the MacBook Pro M4 Pro host (data-model intake Q14, revised; project intake Q22);
  - `git-history.md`, the person's own file name (data-model intake Q13, Q20, Q26).

  This does not block planning.
- **Unticked: "Success criteria are technology-agnostic"**. This item is not true either. The person made some technology-bound targets the release measures:
  - SC-003 names Python, OCaml and Rust ("One schema three languages", Q18);
  - SC-001 and SC-004 are measured on the MacBook Pro M4 Pro host (Q4, Q14, Q18);
  - SC-013 names FileVault and database file encryption (Q25).

  Rewriting them in technology-neutral terms would weaken the person's own measures, so they stay as written.
- **Unticked: "No implementation details leak into specification"**. This item is not true, for the same reason as its sibling "No implementation details": the requirements name technology the person fixed (SQLite, sqlite-vec, the custom Python vector backend, versioned JSON Schemas, Python, OCaml and Rust, Claude and Ollama, FileVault and database file encryption, the MacBook Pro M4 Pro host). An earlier pass ticked it by reading it as "no technology the person did not fix". That redefined the item, and even that reading did not hold: some requirements carry inferred mechanisms, such as the content fingerprint in FR-014, the configuration setting that picks the backend in FR-016 and the restart-safe queue in FR-019. Each of these is marked "(inferred)" in the spec and listed below for the person. The other planning choices stay in Assumptions: the embedding model, the lexical method, the approximate-nearest-neighbor method, quantization, the 768-dimension example, commit trailers for session attribution, and how the anonymization lookup works. "SQLCipher-style" appears in FR-027 only inside the person's chosen option text (Q25 D). This does not block planning.
- **Unticked: "Written for non-technical stakeholders"**. The readers are the engineering owner and the role agents. The requirements use terms that the constitution or the person fixed: schema version, migration, commit reachability, provenance and tenant. The User Stories stay in plain language. This does not block planning.
- **No markers**. The intake's two open items are feasibility questions for planning, not choices the person still has to make. They appear in Assumptions as UNVERIFIED planning risks:
  - whether sqlite-vec meets p95 under 200 ms at 1 million chunks (cites Q4, Q7, Q8, Q14), UNVERIFIED until benchmarked;
  - whether an encrypted SQLite build still loads sqlite-vec, with the same protection for the custom backend's files (cites Q7, Q25), UNVERIFIED until a first install is tried.

  The third open item, how `git-history.md` is versioned, was resolved by Q26 (Generated and gitignored). If the first benchmark shows that the custom backend should become the default, that change goes back to the person through `/speckit-intake-refine`.
- **The revised answers drive the spec**. The person revised three answers after round 5. The spec uses only the revised answers. The superseded ones appear in Clarifications marked "superseded by the revision below".
  - Q20: "At the start of every Coding Agent Session and after every git push." This is FR-024, US2 AS-2 and AS-3, and SC-006. The earlier answer was "After every commit".
  - Q8: "10 Agents and 1 User". This is FR-028. The earlier answer was "Up to 100 users".
  - Q14: "Macbook Pro M4 Pro Chip 24 gigs of Ram (18 gigs of Ram operatinally after the MacOS memory consumption.", together with the four limits kept by Q25. These are FR-026, FR-027, FR-028, SC-001 and SC-013.
- **Reading of Q25**: option C's text said "no separate database encryption", and the person also picked D. The spec requires both layers, as the decision record states ("all four kept"). This reading is marked inferred in Assumptions.
- **Every functional requirement has an acceptance criterion**. An earlier pass added US1 AS-8, AS-9 and US2 AS-8, so that FR-018, FR-011 and FR-029 no longer rest on Edge Cases alone. This pass added US2 AS-9 for FR-008. Before it, the identity fields and the rule that only a person changes an identity had no direct scenario.

  | Requirement | Acceptance criteria |
  |---|---|
  | FR-001 | US1 Independent Test, US2, SC-005 |
  | FR-002 | US3 AS-4, SC-012 |
  | FR-003 | US3 AS-1, SC-003 |
  | FR-004 | US3 AS-2, AS-3, SC-012 |
  | FR-005 | US3 AS-5 |
  | FR-006 | US3 AS-6, Edge Cases (hidden model reasoning) |
  | FR-007 | US1 AS-4, Edge Cases (missing or partial tenant), SC-005 |
  | FR-008 | US2 AS-9, US2 AS-1, Edge Cases (subagent writes) |
  | FR-009 | US2 AS-6, SC-007 |
  | FR-010 | US2 AS-7, SC-011 |
  | FR-011 | US1 AS-9 |
  | FR-012 | US2 AS-1, SC-006 |
  | FR-013 | US1 AS-1, SC-005 |
  | FR-014 | US1 AS-2, AS-3, Edge Cases (stale result, force-push), SC-005 |
  | FR-015 | US3 AS-2, SC-002 |
  | FR-016 | US1 AS-6 |
  | FR-017 | US1 Independent Test, SC-001 |
  | FR-018 | US1 AS-8 |
  | FR-019 | US1 AS-5, SC-008 |
  | FR-020 | US1 AS-7, SC-010 |
  | FR-021 | SC-004 |
  | FR-022 | US2 AS-5, SC-006 |
  | FR-023 | US2 Independent Test, SC-006 |
  | FR-024 | US2 AS-2, AS-3, SC-006 |
  | FR-025 | US2 AS-4, SC-006 |
  | FR-026 | Edge Cases (network down), SC-009 |
  | FR-027 | Edge Cases (encrypted database), SC-013 |
  | FR-028 | SC-001, SC-004 |
  | FR-029 | US2 AS-8 |

- **"Feature meets measurable outcomes" is ticked with a caveat**. The tick means that requirements cover every Success Criterion. It does not mean that every Success Criterion is shown to be achievable. Two are not yet shown, and both are UNVERIFIED planning risks in Assumptions, not gaps in the spec:
  - SC-001 (p95 under 200 ms at 1 million chunks) on the default backend. The spec already allows the custom Python backend behind the same interface (FR-016).
  - SC-013 (database file encryption on top of FileVault) with sqlite-vec loaded.

  Nothing here claims they pass before the benchmark and the first install have run (Art. IV).
- **Success Criteria origin**:
  - The person's targets: 200 ms p95 at 1 million chunks (Q4); zero orphan records, one schema in three languages, and a full re-index within 10 minutes (Q18); and "stale results never appear" (Q17).
  - Inferred: the 100% and 0 rates; the weekly live sample (SC-005); the co-running condition and the split with spec 005 SC-007 (SC-001); the encryption checks (SC-013); and the reference repository for SC-004.
- **Inferred rules awaiting the person**. The person did not state these. They are marked "(inferred)" in the spec and should go back through `/speckit-intake-refine`:
  - FR-001: the data model is the source of truth for metadata, while the repository and Gitea stay the authority for content. Code content (code files as documents and chunks) is in the first version's retrieval (Q3), while the code and skills metadata of Q5's option D (repositories, commits, files and symbols as records of their own, and the skills catalog) comes later. Until then, commits, files and symbols appear as records only through `git-history.md`.
  - FR-002: raw webhook deliveries count as shared metadata. Unlisted record types keep their field sets in their own specs. The Jev message fields are a minimum ("at least"), because the existing `schemas/jev-message.v1.json` also has `episode_id` and `evidence`. The field list itself comes from the decision record, as spec 008 FR-042 cites it, not from the Jev research report.
  - FR-003: every shared type is usable from Rust.
  - FR-004: readers refuse unknown schema versions.
  - FR-005: ids are unique across machines.
  - FR-007: records that span repositories carry an explicit scope value.
  - FR-008: the `system` actor gets an identity, and only a person changes identities.
  - FR-009: a refused change is recorded with the caller's identity, role and session (Q9 says who may change a record, not that refusals are recorded). Anonymization and migrations are the only operations that cross owners. The Record ownership rows beyond Q9's four owners (Lead, PSE, Review, Jev) are inferred; the migrations row rests on the constitution's risk-class table (High, with human approval; Critical when destructive), not on Art. VI.
  - FR-010: the placeholder is stable, it is applied to rebuilt `git-history.md` files and the knowledge graph, and only a person starts an anonymization.
  - FR-012: lineage keeps every change, not only the last.
  - FR-014: the stored inputs of the staleness rule (branch and content fingerprint).
  - FR-015: a write that would create an orphan is refused at write time (Q18 asked only for a nightly check that finds zero orphans), the source of a runtime record, and edges link existing entities.
  - FR-016: the active backend is a configuration setting.
  - FR-017: the filters beyond tenant and commit.
  - FR-018: vectors from different models or dimensions are never compared.
  - FR-019: the queue survives a restart.
  - FR-020: sensitive records never fall back to a cloud model, and who marks a record sensitive.
  - FR-021: a re-index never drops authoritative runtime records.
  - FR-022: the entity and edge kinds.
  - FR-025: a rebuild lists exactly git log's commits.
  - FR-026: the list of operations that keep working offline.
  - FR-027: the custom backend's files get the same protection, and the data model never falls back to an unencrypted file.
  - FR-029: retention of records other than events and Jev's dedup records.
  - US2 AS-8: a housekeeping run.
  - US2 AS-6 and AS-9, SC-007 and the Edge Case "Write by a role that does not own the record": a refused change is recorded as well as refused (FR-009).
  - SC-013: database file encryption extends to the custom backend's vector files (FR-027).
  - Edge Cases: an orphan refused at write time, duplicate indexing at the same commit, an empty result in place of a stale one, a change of embedding model, subagent writes, commits made by the person, death after a push, and the backend fallback when encryption blocks sqlite-vec.
  - Assumptions: the readings of Q10, Q8 and Q25; 1 user = the person; the existing artifacts as starting points; and session attribution in commits.
- **Dependencies** match the fixed dependency map exactly:
  - Upstream: none.
  - Downstream: 001, 002, 005 and 008, one line each, saying what is consumed. Each line cites the consuming FRs.
  - The 001 line no longer claims that 001 consumes identities and tenant ids. Spec 001 never mentions tenants, and none of the cited 001 FRs uses identities or tenant ids; 001's own 009 line lists only the event, lease, envelope, idempotency, trace and checkpoint schemas. The line keeps the anonymization claim, which 001's Edge Cases support, and notes as inferred that 001's records carry the tenant (FR-007).
  - Spec 008 now exists. Its 009 line matches 009's 008 line, and 009's 008 line now cites 008 FR-005, FR-010, FR-039, FR-040, FR-042, FR-045 and FR-051.
  - Specs 003, 006 and 007 are listed only as Related, not as build edges, as spec 005 does.
- **Clarifications** copy all 25 "- Q: … → A: …" lines of the data-model intake in its order, each with the intake and Q number. The superseded Q20, Q8 and Q14 lines are kept and marked "superseded by the revision below". Fifteen project-intake lines this spec rests on come first: Q1, Q2, Q3, Q6, Q7, Q8, Q9, Q10, Q13, Q14, Q15, Q16, Q18, Q20 and Q22.
  - This pass added Q8, because Non-goals rely on it ("The skill catalog is deferred").
  - Every project-intake question the spec body cites now has its line here.
  - The intake's "(answered after the session)" suffixes are replaced by the intake and Q number.
- **Outside this task's files** (for the specs' owners):
  - `specs/README.md` now lists 008 and 009 in its index, with 009 first in the build order, and its shared vocabulary marks the event, lease, envelope, checkpoint, trace and Jev message formats as "(schema: 009)". No change is needed there.
  - Spec 001's Non-goals say "Write or index `git-history.md`, which belongs to spec 009", while spec 005 FR-026 has the session keep the file current. FR-024 here reconciles the two: 009 owns the entry format, the rebuild and append, and the ingestion, and 005 owns when the session calls them. No edit to 001 or 005 is needed, but their wording could cite FR-024.
  - Spec 003 FR-019 owns the Review verdict's field set. FR-002 here does not claim it, and only the verdict's stored rows carry 009's common fields.
  - The existing `schemas/jev-message.v1.json` also has `episode_id` and `evidence` fields beyond the fields listed in FR-002. Planning reconciles the schema with spec 008 (Assumptions: existing artifacts).
- **This pass (2026-10-22)**: the spec already existed, untracked, from an earlier pass of this workflow. It was rebuilt against the answered data-model intake, the decision record and the fixed dependency map. No FR or SC id was renumbered or withdrawn, and it still has FR-001 to FR-029 and SC-001 to SC-013. Changes in this pass:
  - a "Stale result" edge case, so that stale results are listed as their own case and not only under force-push;
  - the tenant edge case renamed to cover tenant isolation;
  - US2 AS-9 for FR-008;
  - the Jev message fields in FR-002 read as a minimum;
  - the 001 dependency line now cites 001's Edge Cases for anonymization;
  - the project-intake Q8 line in Clarifications.
- **Review fixes (2026-10-22, later pass)**: a review found nine issues, and all were fixed in the spec and this checklist:
  - FR-001, FR-017, the Assumptions, the Non-goals, US1 and the Document version entity now separate code content (indexed for retrieval in the first version, Q3; spec 005 FR-004, FR-005, FR-025) from the code and skills metadata of Q5's option D (later). Before this, FR-001 left code out of retrieval, against Q3 and spec 005, and FR-017 was ambiguous about code chunks, so "Requirements are testable and unambiguous" and "Scope is clearly bounded" did not hold. They hold now and stay ticked.
  - "No implementation details leak into specification" is unticked (above).
  - Migrations are no longer cited as an Art. VI matter. The ownership table and the Constitution dependency bullets cite the risk-class table for them, as FR-004 does.
  - FR-002 cites the decision record for the Jev message fields and marks "at least" as inferred.
  - "(inferred)" markers were added to US2 AS-6 and AS-9, FR-009, FR-015, SC-007, SC-013 and two Edge Cases.
  - The 001 and 008 dependency lines and the notes on files outside this task were corrected (above).
- `/speckit-plan` can proceed. The four unticked items are explained above, and none of them blocks planning.
