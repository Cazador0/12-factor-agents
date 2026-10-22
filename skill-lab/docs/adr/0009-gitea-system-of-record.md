# ADR-0009: Gitea 28.x is the system of record for execution state, behind a narrow, dry-run-first client

## Status

Accepted

## Date

2026-10-22

## Context

The report assigns durable knowledge to the repository and **durable execution state to Gitea**:
issues, dependencies, assignments, board state, pull requests, reviews, checks and merge status.
Agent conversations are transient (report
[§Executive architecture](../research/engineering-team-report.md#executive-architecture),
[§Current operational state](../research/engineering-team-report.md#current-operational-state)).
It also asks for:

- a **narrow semantic tool surface**, explicitly "avoid an unrestricted
  `gitea.request(method, path, body)` tool";
- every mutation to carry `actor_role`, `session_id`, `expected_version`, `idempotency_key` and
  `reason`, so a retried write cannot repeat itself;
- a Gitea-native replacement for Spec Kit's GitHub-only task-to-issue extension that "creates
  only missing issues" and writes the mapping back
  ([§Gitea integration for Spec Kit](../research/engineering-team-report.md#gitea-integration-for-spec-kit)).

Facts ([SOURCES.md, Gitea](../research/SOURCES.md#gitea) and
[Spec Kit](../research/SOURCES.md#spec-kit)):

- Gitea **28.2.0** (2026-10-18) is current. REST lives under `/api/v1`. Issue dependencies are
  `GET|POST|DELETE /repos/{owner}/{repo}/issues/{index}/dependencies` with an `IssueMeta` body.
  Webhooks carry `X-Gitea-Event`, `X-Gitea-Delivery` and `X-Gitea-Signature`.
- Project-board (column) API coverage differs between versions.
- Spec Kit's `github` extension titles issues `T001: <description>` and deduplicates by matching
  the task-id regex `\bT\d{3,}\b` against existing titles across **open and closed** issues.

There is no live Gitea server yet. The user will provide one later.

## Decision

1. **Gitea is the system of record for execution state.** Specs, plans, tasks, ADRs and the
   task-to-issue map live in the repository. Board state, assignment, dependencies, PRs, reviews
   and checks live in Gitea. A session re-reads Gitea at the start of every phase and before every
   write. Supported servers are 28.0.0 and later. An older server gets the warning
   `GITEA_VERSION_UNTESTED`.
2. **A narrow stdlib client, `_skillkit.gitea`** (SPEC-201 FR-008):
   - named read methods that issue only `GET`;
   - a single write path, `GiteaClient.send(operation)`, which calls
     `_skillkit.policy.require(operation.action)` before opening a connection;
   - from R2, an endpoint table that maps each allowed `(action, method, path template, body keys)`
     to a semantic operation, so anything else exits 4 with `UNSUPPORTED_OP` (SPEC-202 synthesis
     D-2);
   - **no generic request method**, and no plain merge: `gitea.pr.merge` is `human-only`. The only
     merge-related write is `merge_when_checks_succeed` with an exact body, at
     `guarded-autonomous` (R3);
   - the token comes from `GITEA_TOKEN`. R1 needs at most a read-scoped token. R2 uses one identity
     per role (planned for ADR-0201).
3. **Dry run by default.** A script that would write emits a `gitea-plan.v1`: every operation
   carries `op`, catalog `action`, `idempotency_key`, `request {method, path, body}` and `reason`,
   and `skipped[]` explains what is not done and why. It exits 0. `--apply` executes the plan,
   subject to the autonomy level. In R1 every write is refused with exit 4.
4. **Idempotency, in layers.** Applying the same plan twice must make zero additional writes:
   1. the committed `task-issue-map.v1` is consulted first;
   2. then the task-id regex `\bT\d{3,}\b` over the titles of **open and closed** issues, exactly
      like Spec Kit's `github` extension, so a closed task is never re-created;
   3. every operation has a deterministic key,
      `_skillkit.ids.idempotency_key(repository, feature, task_id, op)`;
   4. from R2: dedupe is re-run immediately before each create, each applied operation is
      journaled, and `expected_version` plus a digest of the observed state are re-read and
      compared before writing (SPEC-202 synthesis D-5, D-14).
5. **Capabilities are probed, not assumed.** `GET /api/v1/version` gives the server version, and
   `GET /swagger.v1.json` shows whether project-column endpoints exist.
6. **Board state lives in exclusive scoped labels.** The canonical machine state is exactly one
   `state/<name>` label per issue, one for each of the report's 10 states. Labels behave the same
   on every 28.x server and are read in one request. When the swagger shows project-column
   endpoints, a `move_issue` operation mirrors the state on the board, but the label stays
   authoritative. Zero or several `state/*` labels on one issue is an invalid state: the state
   machine refuses transitions on it, and sync reports it as drift. Labels come only from a fixed
   vocabulary (`state/*`, `spec/*`, `story/*`).
7. **Test double now, live server later.** `skill-lab/lab/gitea_double.py` (SPEC-201 FR-017)
   serves the read endpoints from a seed fixture over loopback, reports version `28.2.0`, logs
   every request as JSON lines, and answers every non-GET request with HTTP 405 in R1. The log makes
   "zero non-GET requests" observable for containment. R2 adds write endpoints and a mutation
   ledger, and a smoke test against a live server before the first live write (planned for
   ADR-0206). A live server is configured with `GITEA_URL` and `GITEA_TOKEN`. `skill-lab doctor`
   probes `$GITEA_URL/api/v1/version` without credentials.
8. **Webhooks are hints until verified.** A delivery drives nothing until its HMAC signature is
   verified and its delivery id is new (ADR-0012). From R3 every decision is made from live state
   that the event only prompts the scripts to re-read (SPEC-203).

## Consequences

### Positive

- Works the same on every 28.x server, with or without project-board APIs.
- Plans are reviewable before anything happens, and re-runs are byte-identical, so a dry run is
  a reliable preview.
- The whole write path is testable offline against the double. Containment is measured, not
  asserted.
- Closed and existing issues are never duplicated, which is the main long-horizon failure the
  report warns about.

### Negative

- The double encodes our reading of Gitea's API. Field names and pagination may differ on a real
  server until they are checked against `/swagger.v1.json` (SPEC-201 risk R-10).
- Label-based state adds visible labels that humans may also edit by hand. Hand edits surface as
  drift, which costs attention.
- Title-regex dedupe treats any issue whose title contains `T004` as task T004's issue, including
  one a human created for something else. The committed map takes precedence, and sync reports
  `title_mismatch`, but the first run in a messy repository needs a human look.
- No server-side transactions: a multi-operation plan can stop half-way. R2's journal and
  re-planning make it resumable, not atomic.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| Endpoint or field drift between the double and a real 28.x server | No live server and no published swagger in the build container | T023 and T025 check against `/swagger.v1.json` when reachable; R2 smoke test before the first live write |
| A token with more scope than needed | Users create tokens by hand | Read-scoped token in R1; per-role identities in R2; `doctor` reports only whether the token is set |
| Rate limits or pagination truncate an issue list, so dedupe misses an existing issue | Large repositories | The client follows pagination to the end (total-count header, verified at T023); a short list is an error, not an empty result |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| GitHub as the control plane | The user chose Gitea, and the skills are Gitea-only. The factory repository on GitHub is handled by the orchestrator, not the skills (SPEC-202 synthesis D-4) |
| A local database (SQLite) as state | Invisible to humans and to other sessions; duplicates what Gitea already stores |
| A generic `request(method, path, body)` helper | Exactly what the report says to avoid; it erases the semantic authority boundary |
| The `tea` CLI | An extra binary with its own auth configuration, driven through a shell |
| Project columns as the primary state | Coverage varies by Gitea version; labels work everywhere |
| Apply immediately, no dry run | Removes the human checkpoint that shadow mode is built on, and makes containment unmeasurable |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Plans and maps are valid contracts | `gitea-plan.v1`, `task-issue-map.v1`, `mutation-request.v1` schemas and examples (`test_contracts.py::TestExamples::test_every_example_validates`) | enforced |
| Deterministic idempotency keys | `test_skillkit_ids.py::TestIdempotencyKey::test_matches_documented_derivation` | enforced |
| Doctor probes Gitea without leaking the URL's credentials | `test_lab_core_doctor.py::TestChecks::test_gitea_probe_uses_the_configured_url_without_printing_it` | enforced |
| Read client sends only GET; `send()` calls `require()` first | `skill-lab/tests/test_gitea_client.py` (SPEC-201 T025) | planned |
| The double: version 28.2.0, request log, 405 on non-GET | `skill-lab/tests/test_gitea_double.py` (SPEC-201 T023) | planned |
| Exactly the missing issues; closed tasks skipped; second run byte-identical; `--apply` exits 4 with zero non-GET requests | SPEC-201 User Story 3, scenarios 3 and 4 (integration test against the double) | planned |
| No unsupported operation reaches the network | `UNSUPPORTED_OP` tests for the endpoint table (SPEC-202 T029) | planned (R2) |
| Re-apply makes zero writes against a live server | SPEC-202 smoke test and live idempotency check | planned (R2) |

**Revisit when** a live Gitea is available (run the swagger check and the smoke test, then update
SOURCES.md), when Gitea's project API stabilises across versions, or when an MCP gateway replaces
the in-script client.

## References

- [SOURCES.md: Gitea](../research/SOURCES.md#gitea), [Spec Kit](../research/SOURCES.md#spec-kit)
- Report [§Gitea as the real-time engineering control plane](../research/engineering-team-report.md#gitea-as-the-real-time-engineering-control-plane),
  [§Kanban state machine](../research/engineering-team-report.md#kanban-state-machine),
  [§Gitea integration for Spec Kit](../research/engineering-team-report.md#gitea-integration-for-spec-kit)
- [SPEC-201 R1](../../specs/201-release-shadow/spec.md) FR-008, FR-017, FR-021..FR-023 and the `gitea-plan` op vocabulary;
  [SPEC-201 plan](../../specs/201-release-shadow/plan.md) (Gitea test double)
- ADR-0004 (contracts and idempotency keys), ADR-0005 (layers of refusal), ADR-0012 (webhooks)
