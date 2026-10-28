# Golden feature fixture

A complete, internally consistent Spec Kit feature (`042-session-refresh`) used as
the shared ground truth for skill evals. It is the report's running example:
refresh-token rotation with duplicate-use invalidation.

Skills copy the files they need into their own `evals/fixtures/`, so each skill
stays self-contained once installed. When this fixture changes, re-copy it and
re-run the deterministic benchmarks.

| File | Used by |
|---|---|
| `specs/042-session-refresh/spec.md` | lead-architect (readiness), review-verifier (requirements matrix), pse-implementer (contract) |
| `specs/042-session-refresh/plan.md` | lead-architect (readiness) |
| `specs/042-session-refresh/tasks.md` | lead-architect (DAG), speckit-gitea-taskstoissues, speckit-gitea-sync |
| `specs/042-session-refresh/checklists/requirements.md` | lead-architect (readiness), review-verifier |

Known facts that evals may assert:

- 14 tasks, `T001`–`T014`. Phases: Setup (T001–T002), Foundational (T003–T005),
  US1 (T006–T010), US2 (T011–T012), Polish (T013–T014).
- Parallel-marked tasks: T002, T004, T006, T007, T011, T013.
- Explicit inline dependencies: T008 depends on T006 and T007; T009 depends on T008; T012 depends on T011.
- Write-domain conflict: T006 and T007 are both `[P]` and both touch `src/auth/tokens/`,
  so a correct planner serialises them or flags the conflict.
- Requirements: FR-001…FR-008 and NFR-001…NFR-004. Success criteria: SC-001…SC-004.
- Every FR maps to at least one task; FR-008 (audit log) maps only to T013.
