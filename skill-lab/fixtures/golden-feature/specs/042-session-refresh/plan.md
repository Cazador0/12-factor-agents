# Implementation Plan: Session refresh with token rotation

**Branch**: `042-session-refresh` | **Spec**: [spec.md](spec.md)

## Summary

Add a `refresh_tokens` table keyed by token hash with family linkage, rotate on every
refresh inside one database transaction, and revoke the family on reuse.

## Technical Context

**Language/Version**: Python 3.12
**Primary Dependencies**: FastAPI, SQLAlchemy 2.x
**Storage**: PostgreSQL 16 (`refresh_tokens`, `token_families`)
**Testing**: pytest (unit, integration with a disposable database), k6 for load
**Target Platform**: Linux containers
**Project Type**: web service
**Performance Goals**: p95 ≤ 120 ms at 200 rps on `/auth/refresh`
**Constraints**: no plaintext token storage; serializable transaction for rotation
**Scale/Scope**: 2M active sessions

## Architecture

- `src/auth/tokens/` owns hashing, generation, and the repository.
- `src/auth/refresh/` owns the endpoint and the rotation service.
- `src/audit/` receives reuse and revocation events.
- Dependency direction: `refresh` → `tokens` → database; `refresh` → `audit`.

## Dependency Map

- Database migration (T003) before any repository code.
- Token hashing (T007) and generation (T006) before the rotation service (T008).

## Decisions

- ADR-021: Token family invalidation is transactional (rotation and revocation share one serializable transaction).
