# Feature Specification: Session refresh with token rotation

**Feature Branch**: `042-session-refresh`

**Created**: 2026-10-01

**Status**: Ready

**Spec ID**: SPEC-042

**Input**: User description: "Signed-in users stay signed in safely: rotate refresh tokens on every use and kill the whole token family if a refresh token is reused."

## Intent

Long-lived sessions currently reuse one refresh token for 30 days, so a stolen token
stays valid for weeks. This feature rotates the refresh token on every refresh and
treats reuse of an already-rotated token as theft, revoking every token in its family.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Rotate refresh tokens on every refresh (Priority: P1)

A signed-in user's client exchanges its refresh token for a new access token and a new
refresh token. The old refresh token stops working immediately.

**Why this priority**: It removes the long validity window that makes a stolen refresh token dangerous.

**Independent Test**: Call the refresh endpoint twice in sequence with the token returned each time; both succeed, and the first token is rejected afterwards.

**Acceptance Scenarios**:

1. **Given** a valid refresh token R1, **When** the client refreshes, **Then** it receives access token A2 and refresh token R2, and R1 is marked rotated.
2. **Given** R1 was rotated to R2, **When** the client refreshes with R2, **Then** it receives R3 and R2 is marked rotated.
3. **Given** an expired refresh token, **When** the client refreshes, **Then** the response is 401 with error code `refresh_expired` and no token is issued.

---

### User Story 2 - Revoke the token family on reuse (Priority: P2)

If a refresh token that was already rotated is presented again, the system assumes it was
stolen and revokes every token in that family, signing the user out on all devices of that session.

**Why this priority**: Rotation alone does not detect theft; reuse detection turns rotation into a theft alarm.

**Independent Test**: Rotate R1 to R2, then present R1 again; every token in the family is rejected and an audit event is written.

**Acceptance Scenarios**:

1. **Given** R1 was rotated to R2, **When** R1 is presented again, **Then** the response is 401 `refresh_reused`, and R2 and every later token in the family are revoked.
2. **Given** a family was revoked, **When** any token of that family is presented, **Then** the response is 401 `refresh_revoked`.

---

### Edge Cases

- Two refresh requests with the same token arrive concurrently: exactly one succeeds; the other is treated as reuse only if it arrives after the rotation committed.
- The database commit for a rotation fails: no new token is returned and the old token stays valid.
- Clock skew between API nodes of up to 5 seconds must not cause false `refresh_expired` errors.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: System MUST issue a new refresh token on every successful refresh and mark the presented token as rotated.
- **FR-002**: System MUST reject a rotated refresh token with HTTP 401 and error code `refresh_reused`.
- **FR-003**: System MUST revoke every token in a token family when reuse is detected, in the same transaction that records the reuse.
- **FR-004**: System MUST reject tokens of a revoked family with HTTP 401 `refresh_revoked`.
- **FR-005**: System MUST reject expired refresh tokens with HTTP 401 `refresh_expired` without issuing tokens.
- **FR-006**: System MUST make rotation idempotent per request id, so a retried request with the same `Idempotency-Key` returns the same token pair.
- **FR-007**: System MUST store only a SHA-256 hash of each refresh token, never the token itself.
- **FR-008**: System MUST write an audit event for every reuse detection and family revocation.

### Non-Functional Requirements

- **NFR-001** (Performance): p95 latency of the refresh endpoint ≤ 120 ms at 200 requests/second.
- **NFR-002** (Reliability): A failed commit leaves the previous token valid (no partial rotation).
- **NFR-003** (Observability): Emit metrics `auth_refresh_total{result}` and `auth_family_revocations_total`.
- **NFR-004** (Security): Tokens are 256-bit random values; comparison of hashes is constant-time.

### Key Entities

- **RefreshToken**: hash, family_id, parent_hash, status (active | rotated | revoked), issued_at, expires_at.
- **TokenFamily**: id, user_id, session_id, status (active | revoked), revoked_at, revoke_reason.

### Data and API Contracts

- `POST /auth/refresh` with body `{"refresh_token": "..."}` and optional `Idempotency-Key` header.
  Returns `200 {"access_token", "refresh_token", "expires_in"}` or `401 {"error": "refresh_expired" | "refresh_reused" | "refresh_revoked"}`.

### Error and Failure Semantics

- All 401 responses use the error codes above; no other information about the family is revealed.
- On database failure the endpoint returns 503 `refresh_unavailable` and changes nothing.

### Authorization and Security

- Only the holder of a refresh token can refresh; no admin bypass. Revocation is user-scoped.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of refreshes issue a new refresh token (verified by integration test over 1,000 refreshes).
- **SC-002**: 100% of reuse attempts revoke the family within the same transaction (verified by fault-injection test).
- **SC-003**: p95 refresh latency ≤ 120 ms at 200 rps in the load test.
- **SC-004**: Zero refresh tokens stored in plaintext (verified by schema check and a database scan test).

## Non-goals

- Changing access-token lifetime or format.
- Device management UI.
- Admin-initiated session revocation (separate feature).

## Assumptions

- Access tokens stay short-lived (15 minutes) and are out of scope.
- The existing `users` and `sessions` tables are unchanged.

## Traceability

| Requirement | Tasks | Verification |
|---|---|---|
| FR-001 | T006, T008 | integration: test_rotation_issues_new_token |
| FR-002 | T008, T009 | integration: test_rotated_token_rejected |
| FR-003 | T009 | fault-injection: test_family_revoked_atomically |
| FR-004 | T011, T012 | integration: test_revoked_family_rejected |
| FR-005 | T008 | unit: test_expired_token_rejected |
| FR-006 | T010 | integration: test_idempotent_retry_same_pair |
| FR-007 | T003, T007 | unit: test_only_hash_stored |
| FR-008 | T013 | integration: test_audit_event_written |
| NFR-001 | T014 | load: refresh_p95_under_120ms |
| NFR-002 | T009 | fault-injection: test_failed_commit_keeps_old_token |
| NFR-003 | T013 | unit: test_metrics_emitted |
| NFR-004 | T007 | unit: test_constant_time_compare |
