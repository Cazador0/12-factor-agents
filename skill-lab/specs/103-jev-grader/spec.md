# Feature Specification: Jev grader client (TypeSafe System One)

**Spec**: SPEC-103

**Component**: `skill-lab/lab/jev.py`, with its recording in `skill-lab/lab/cassette.py` (family: lab)

**Created**: 2026-10-22

**Status**: Implemented

**Input**: CONVENTIONS §5 (judgments are Jev questions with pass rules; uncertain counts as a fail and
needs a human), SOURCES.md "TypeSafe AI Jev", and the official `typesafe-sdk` 0.7.5 wire models vendored
at `docs/research/vendor/typesafe-wire-models.py`. The user calls the key "the Jev API key".

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Agentic outputs are judged by narrow, typed questions (Priority: P1)

Bench sends a case's judgments (noul, score, choice) about the model's output to `POST /v1/systemone`
and gets typed answers it can grade by fixed rules.

**Why this priority**: agentic and routing quality cannot be graded by assertions alone; typed judgments
make the grade machine-checkable.

**Independent Test**: a fake TypeSafe API on 127.0.0.1 returns one answer of each type; the client sends
the documented request and parses `NoulAnswer`, `ChoiceAnswer` and `ScoreAnswer`.

**Acceptance Scenarios**:

1. **Given** `TYPESAFE_API_KEY` is set, **When** the client asks three questions, **Then** one POST carries `{"model", "state", "questions"}` with Bearer auth, JSON content type and accept, and a `skill-lab/<version>` user agent.
2. **Given** a 200 response, **When** it is parsed, **Then** each answer is typed, `x-typesafe-request-id` is kept, and usage is read.

---

### User Story 2 - Transient failures are retried; permanent ones are explicit (Priority: P1)

**Why this priority**: a benchmark must neither crash on a rate limit nor hide an authentication problem
as a failed skill.

**Independent Test**: the fake API answers 429 with `retry-after: 2`, then 503 with `retry-after-ms`,
then 200; the injected sleep records the waits. 401, 403 and 422 raise their own errors at once.

**Acceptance Scenarios**:

1. **Given** a 429 with `retry-after: 2`, **When** the client retries, **Then** it waits 2 s, sends `X-TypeSafe-Retry-Count: 1`, and succeeds.
2. **Given** a 422 with a `detail` list, **When** the client asks, **Then** `JevValidationError.detail` holds the `{loc, msg, type}` entries and no retry happens.
3. **Given** a server that echoes the key in a 401 body, **When** the error is raised, **Then** the key appears only as `***`.

---

### User Story 3 - Wrong answers to the interface are protocol errors, not grades (Priority: P2)

**Why this priority**: "typed output guarantees the interface, not truth"; anything that breaks the
interface must stop grading instead of producing a guessed pass or fail.

**Independent Test**: crafted responses with an unknown answer type, a type mismatch, a missing or extra
answer, a choice outside the labels, or a probability outside [0, 1] all raise `JevProtocolError`.

**Acceptance Scenarios**:

1. **Given** an answer of type `box` to a noul question, **When** the response is parsed, **Then** `JevProtocolError` is raised with the request id.

### Edge Cases

- No key: `JevConfigError` before any request; bench treats Jev as off.
- `TYPESAFE_API_KEY` blank but `JEV_API_KEY` set: the latter is used.
- A choice question whose criteria are empty, a score question without levels, or an unknown question type: refused locally (`JevConfigError`) without a request.
- A non-JSON 200 body: `JevProtocolError`.
- A `retry-after` longer than 60 s: no retry; the response is reported as `JevHTTPError`.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The client MUST call `POST {base}/v1/systemone` and `GET {base}/v1/models`, with `base` from `TYPESAFE_BASE_URL` (default `https://api.typesafe.ai`), the key from `TYPESAFE_API_KEY` or else `JEV_API_KEY`, the model from `TYPESAFE_DEFAULT_MODEL` (default `jev-latest`), a 30 s default timeout, and the headers `Authorization: Bearer <key>`, `Content-Type: application/json`, `Accept: application/json` and `User-Agent: skill-lab/<version>`.
- **FR-002**: The client MUST retry HTTP 429, 500, 502, 503 and 504 and connection errors up to 3 times with deterministic exponential backoff, honour `retry-after-ms` and `retry-after` (seconds or HTTP date), send `X-TypeSafe-Retry-Count` on retries, and use an injectable sleep.
- **FR-003**: Failures MUST map to typed errors with compact, redacted messages and the `x-typesafe-request-id` when present: 401/403 `JevAuthError` (`JEV_AUTH`), 422 `JevValidationError` (`JEV_REQUEST_INVALID`, with `detail`), other statuses `JevHTTPError` (`JEV_HTTP_ERROR`), no response `JevConnectionError` (`JEV_UNREACHABLE`), configuration `JevConfigError` (`JEV_NOT_CONFIGURED`), bad 200 bodies `JevProtocolError` (`JEV_PROTOCOL`).
- **FR-004**: Responses MUST be parsed strictly into `NoulAnswer`, `ChoiceAnswer` and `ScoreAnswer`: exactly one answer per question, of the question's type; `noul`, `confidence` and every probability finite numbers in [0, 1]; a choice among the question's labels; a score within its levels; usage counts non-negative integers. Unknown answer types and any violation MUST raise `JevProtocolError`.
- **FR-005**: The key MUST never appear in logs, error messages, results or cassettes: messages pass through `_skillkit.redact` and the client also masks its own key; cassettes never store headers.
- **FR-006**: The module MUST build questions from `benchmark-case` judgments (`question_for`: type, instructions, criteria; the judgment `id` is the question name and is not sent to the model, so instructions carry the full meaning), the state from `state_from` (`build_state`: `skill`, `prompt`, `fixtures`, `output`), and the routing question (`routing_question`: every catalog skill name with its description plus `none`).
- **FR-007**: Bench MUST batch judgments into one request per distinct `state_from` set (`judgment_batches`), so judgments that share their state are answered in parallel by one call.
- **FR-008**: Jev exchanges MUST be recordable and replayable through `CassetteTransport`; a replaying client needs no key, and an unrecorded request raises `CassetteMiss`.
- **FR-009**: Bench MUST resolve the Jev mode once per run: `--jev off`; `--jev replay` (requires `--cassettes`); otherwise (`--jev live` or no flag) live only when a key is set and an un-retried `GET /v1/models` probe succeeds within 5 s, else off with the reason recorded in the run notes and in each affected result's `skip_reason`.
- **FR-010**: The client MUST refuse, before any request, an empty question set, an unsupported question type, a choice question without labels and a score question without levels.
- **FR-011**: `list_models` MUST return `ModelInfo(name, description, release_date)` entries and reject malformed listings.

### Key Entities

- **Question**: `{type, instructions, criteria}` keyed by a name of the caller's choosing.
- **Answer**: `NoulAnswer(noul)`, `ChoiceAnswer(choice, confidence, probabilities)`, `ScoreAnswer(score, confidence, legend, probabilities)`.
- **SystemOneResult**: `model`, `answers`, `usage`, `request_id`.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Every request the client sends matches the vendored wire models (verified field by field against a fake server).
- **SC-002**: 0 occurrences of the configured key in any log line, error message or cassette produced by the tests.
- **SC-003**: 100% of the crafted interface violations raise `JevProtocolError`; none produces a grade.
- **SC-004**: A case with N judgments that share `state_from` makes exactly 1 request.

## Assumptions

- The vendored `typesafe-sdk` 0.7.5 models describe the live API; network access to `api.typesafe.ai` is blocked in the build container, so the client is verified against a fake server only. The user will allowlist the host and run it live.
- Extra, unknown fields in a response are ignored, like the SDK's Pydantic models do; missing or mistyped required fields are errors.
- A noul answer near 0.5 means uncertain; bench applies the CONVENTIONS §5 band with the 0.35 floor.

## Non-goals

- `box` questions, image assets and multipart requests.
- Async clients, connection pooling and response compression.
- Deciding pass or fail: that is the graders' job (SPEC-102).

## Contracts

Consumes: `benchmark-case.v1` judgments. Produces: typed answers that bench turns into
`benchmark-result.v1` `judgments[]` entries (`value`, `confidence`, `band`, `needs_human`, `request_id`).
The external contract is TypeSafe's OpenAPI document, as vendored.

## Error semantics

| Error | Code | When | Retried |
|---|---|---|---|
| `JevConfigError` | `JEV_NOT_CONFIGURED` | No or malformed key; invalid questions | no request |
| `JevConnectionError` | `JEV_UNREACHABLE` | No HTTP response after the retries | yes |
| `JevAuthError` | `JEV_AUTH` | HTTP 401, 403 | no |
| `JevValidationError` | `JEV_REQUEST_INVALID` | HTTP 422 (`detail`) | no |
| `JevHTTPError` | `JEV_HTTP_ERROR` | Other statuses, and retryable ones once retries are spent | 429/5xx yes |
| `JevProtocolError` | `JEV_PROTOCOL` | A 200 body that does not match the wire models | no |

Bench reports these as result `error` with the code; in replay a missing recording is `skipped`
(`CASSETTE_MISS`), never an error and never an answer.

## Security

- The key is read only from the environment, sent only in the `Authorization` header, and masked from
  every message (redaction plus the client's own scrub); headers are never recorded.
- State sent to Jev is the case's declared parts only (`state_from`); fixtures with secrets must not be used.
- Judgment IDs must not contain credential words (`token`, `auth`, `secret`, `password`, `api key`),
  because redaction masks values under such keys in recorded responses.

## Runtime compatibility

- Python >= 3.9 standard library only (`urllib`, `json`, `dataclasses`).
- The base URL, key and model are environment variables, so the same client serves CI, local runs and
  Zed-hosted sessions; `HTTPS_PROXY` and the system CA store apply as for any `urllib` request.
