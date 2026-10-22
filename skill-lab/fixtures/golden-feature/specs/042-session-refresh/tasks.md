# Tasks: Session refresh with token rotation

**Input**: Design documents from `/specs/042-session-refresh/`

## Format: `[ID] [P?] [Story] Description`

## Phase 1: Setup (Shared Infrastructure)

- [x] T001 Create `src/auth/tokens/` and `src/auth/refresh/` package structure
- [x] T002 [P] Add pytest database fixture in tests/conftest.py

---

## Phase 2: Foundational (Blocking Prerequisites)

- [ ] T003 Create migration for refresh_tokens and token_families in migrations/0042_refresh_tokens.py
- [ ] T004 [P] Add audit event type AUTH_REFRESH_REUSED in src/audit/events.py
- [ ] T005 Configure refresh settings (ttl, family limits) in src/auth/settings.py

---

## Phase 3: User Story 1 - Rotate refresh tokens on every refresh (Priority: P1) 🎯 MVP

- [ ] T006 [P] [US1] Implement 256-bit token generation in src/auth/tokens/generate.py
- [ ] T007 [P] [US1] Implement SHA-256 hashing and constant-time compare in src/auth/tokens/hashing.py
- [ ] T008 [US1] Implement rotation service in src/auth/refresh/service.py (depends on T006, T007)
- [ ] T009 [US1] Make rotation and family revocation one transaction in src/auth/refresh/service.py (depends on T008)
- [ ] T010 [US1] Add Idempotency-Key handling to POST /auth/refresh in src/auth/refresh/api.py

---

## Phase 4: User Story 2 - Revoke the token family on reuse (Priority: P2)

- [ ] T011 [P] [US2] Implement family revocation repository in src/auth/tokens/families.py
- [ ] T012 [US2] Reject revoked-family tokens in src/auth/refresh/service.py (depends on T011)

---

## Phase 5: Polish & Cross-Cutting Concerns

- [ ] T013 [P] Emit audit events and metrics in src/audit/refresh_audit.py
- [ ] T014 Add k6 load test for /auth/refresh in tests/load/refresh.js
