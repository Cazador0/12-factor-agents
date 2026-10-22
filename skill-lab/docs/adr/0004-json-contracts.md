# ADR-0004: Versioned JSON contracts are the only channel between agents and scripts

## Status

Accepted

## Date

2026-10-22

## Context

Lead, PSE, Review, the control-plane scripts and the lab exchange issue contracts, evidence,
verdicts, gates, events, leases and decisions. The report requires these to be machine-readable
("Its verdict should be machine-readable", the evidence package, the normalised event, the merge
evidence manifest) and says unstructured agent-to-agent chat must not define project state
(report [§Review contract](../research/engineering-team-report.md#review-contract),
[§Event-driven communication](../research/engineering-team-report.md#event-driven-communication),
[§Merge evidence gate](../research/engineering-team-report.md#merge-evidence-gate),
[§Final recommended operating doctrine](../research/engineering-team-report.md#final-recommended-operating-doctrine)).

Three forces shape the format:

- **Small models must branch, not parse.** A ~32k local model (ADR-0003) must decide the next step
  from one field such as `ok` or `errors[0].code`, never from prose or a stack trace
  (12-factor Factor 4: tools are structured outputs; Factor 9: compact errors).
- **Ollama Cloud has no structured outputs**, so validity cannot be delegated to the model
  provider. It must be checked after the fact, by deterministic code, against a schema.
- **Everything runs on the Python 3.9 standard library** (ADR-0006). The standard library has
  `json` and no YAML parser, and no full JSON Schema validator.

The report shows its examples (evidence, verdict, quality gate, checkpoint, and the committed
`task-issue-map.yaml`) in YAML.

## Decision

1. **JSON contracts are the only state-bearing channel.** Every document that crosses a script,
   role or process boundary validates against a canonical schema in
   `skill-lab/contracts/schemas/<name>.v1.schema.json`. Prose can accompany a document (a PR
   comment summary, a rendered issue body), but the JSON is authoritative. For example, a verdict
   comment carries exactly one marker line and exactly one fenced `json` block (SPEC-201 FR-035).
2. **Every script prints exactly one `envelope.v1` on stdout**: `schema`, `kind`, `kind_schema`,
   `ok`, `producer`, `created_at`, `idempotency_key`, `payload`, `errors`, `warnings`. `ok` is true
   exactly when the exit code is 0. The payload validates against `kind_schema` when `ok` is true
   and also when the exit code is 1, because a completed but failing check is still a valid
   result. Logs go to stderr ([CONVENTIONS §3](../CONVENTIONS.md#3-script-contract-v),
   [§4](../CONVENTIONS.md#4-json-contracts)).
3. **Identity and versions.** `$id` is `urn:skill-lab:schema:<name>:v<N>`. Payloads carry
   `schema_version: 1`. Two documents are identified by a `schema` URN instead: `envelope` and
   `benchmark-case`. A version is a file. Adding an optional field or loosening a limit stays in v1.
   Anything a v1 consumer could reject or misread creates `<name>.v2.schema.json`, and v1 stays
   until no producer emits it ([contracts README](../../contracts/README.md)).
4. **Closed objects.** `additionalProperties: false` at every level, except exactly four open
   slots: `envelope.payload` (validated separately against `kind_schema`),
   `mutation-request.params`, the `gitea-plan` request `body`, and the Jev instruction objects in
   `benchmark-case`. A typo, an invented field, or chain-of-thought smuggled into a checkpoint is a
   validation error.
5. **A keyword subset** that `_skillkit.jsonschema_mini` implements: `type`, `properties`,
   `required`, `additionalProperties`, `items`, `prefixItems`, `enum`, `const`, `pattern`,
   length, numeric and array bounds, `uniqueItems`, `oneOf`, `anyOf`, `allOf`, `not`, `$ref` to
   `#/$defs/...` in the same file, `format: date-time`, and `$defs`. Nothing else.
6. **Invariants live in the schema.** Where the report forbids a state, the schema makes it
   unrepresentable: `APPROVE` with blockers or unverified requirements; a passed quality gate with
   an applicable `not_run` category; `AUTO_MERGE` of high or critical risk, of policy paths, or
   with non-passing gates; Jev judgments with `jev_mode: "off"`; a passed score gate with no
   measured value.
7. **Compact errors.** `{code, message, path}`, where `code` matches `^[A-Z][A-Z0-9_]*$`,
   `message` is one line of at most 300 characters, and `path` is a JSON Pointer or `file:line`.
   Error lists stay short: the envelope schema allows at most 50 errors and 50 warnings, schema
   issues are cut at 20 followed by one `ISSUES_TRUNCATED` error, and lab commands end a cut list
   with `TRUNCATED`. An unexpected exception becomes one `INTERNAL` error with exit 2. A traceback
   goes to stderr only when `SKILLKIT_DEBUG=1`.
8. **Deterministic serialisation.** Sorted keys, compact separators, UTF-8 without ASCII
   escaping, NaN refused, trailing newline. Timestamps come from `--now` when given.
   `_skillkit.ids.canonical_json` and `digest` (`sha256:<hex>`) give stable digests.
9. **Idempotency keys** are `idem-` followed by 32 hex characters, derived from the inputs with
   `_skillkit.ids.idempotency_key(*parts)`. For example, taskstoissues derives one key per
   `(repository, feature, task_id, op)` (SPEC-201 FR-021). Every mutation request carries
   `actor_role`, `session_id`, `target`, `action`, `expected_version`, `idempotency_key` and
   `reason`: the fields the report lists in
   [§Gitea as the real-time engineering control plane](../research/engineering-team-report.md#gitea-as-the-real-time-engineering-control-plane),
   with `target` and `action` generalising its `issue_id`.
10. **Strict reading.** Inputs are parsed with `_skillkit.cli.read_json` or `loads_strict`, which
    reject duplicate keys, NaN and Infinity, overflowing numbers and pathological nesting.
11. **JSON, not YAML, for every machine artifact**, including the committed task-to-issue map
    (`task-issue-map.v1`, a JSON file), even though the report shows a YAML example. The reasons:
    - The standard library parses JSON and not YAML (ADR-0006).
    - One validator and one strict reader cover every document. A second format would need a
      second parser and a second set of edge-case tests.
    - YAML 1.1 implicit typing silently changes values (`no` becomes `false`, `012` an octal
      number, unquoted dates become timestamps). Parsers also differ on duplicate keys. A map that
      prevents duplicate issues must not have ambiguous keys.
    - JSON has one canonical form for digests and idempotency keys.

    The only YAML anywhere is the `SKILL.md` frontmatter, kept to a strict subset (ADR-0002).
    Spec Kit's own files in target projects are read as Markdown, not as YAML.

## Consequences

### Positive

- Every boundary is checkable offline. Bench grades scripts by exit code, schema validity and
  JSON-Pointer assertions, with no model involved.
- A small model only has to read `ok` and an error code. Errors fit in a context window.
- Illegal states (approval with blockers, `not_run` treated as passed) fail validation instead of
  depending on reviewers noticing them.
- Re-runs produce byte-identical payloads, which makes idempotency and caching testable.

### Negative

- Schema maintenance: 23 contracts today, and SPEC-201 adds 21 more.
- The keyword subset has limits. With no `propertyNames`, map keys such as `AC-01` or `T001`
  cannot be constrained by schema, so each map states its key pattern in its description and
  producers enforce it. With no cross-file `$ref`, shared fragments are copied into each file's
  `$defs`, and a test keeps the copies identical.
- With closed objects, adding an "optional" field is compatible only when producer and consumer
  upgrade together. An old consumer rejects the new field. Inside this repository `sync --check`
  guarantees they move together. An external consumer of v1 has no such guarantee.
- Because invariants live in schemas, a consumer that receives an internally inconsistent
  document (say, a verdict of `APPROVE` with a blocker) gets an input error (exit 2), not a
  policy decision. Eval authors must expect exit 2 for those cases.
- JSON is less pleasant than YAML to edit by hand and cannot carry comments. Committed maps are
  generated, sorted and indented (`fsutil.atomic_write_json`) so diffs stay readable.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| `jsonschema_mini` accepts or rejects something the standard would not | Hand-written validator | Differential tests against `jsonschema` 4.26.0 plus `rfc3339-validator` when installed (`TestDifferential`, over 150 instances), with known divergences (leap seconds) covered by unit tests (ADR-0006) |
| A schema-valid document is false (evidence that claims a check that never ran) | Schemas check shape, not truth | Evidence binds to `check-run` log digests and `CHECK_NOT_EXECUTED` (SPEC-201 FR-016, FR-019); Review re-runs checks |
| A model wraps JSON in prose or fences | Ollama Cloud cannot be forced to emit JSON | Lenient extraction records how the JSON was found; validation is strict (ADR-0003) |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| YAML for maps and evidence (the report's examples) | No stdlib parser; implicit typing and duplicate-key ambiguity; a second validator path |
| Markdown or prose handoffs | Not machine-checkable. The report rules out chat as the definition of state |
| Protocol Buffers, JSON-RPC or MCP tool schemas | Dependencies or code generation; scripts must run offline as stdlib CLIs. MCP may wrap these same contracts later |
| Full JSON Schema through the `jsonschema` package | Third-party, and its current versions depend on compiled extensions (ADR-0006). It is kept as a test oracle only |
| Open schemas (`additionalProperties: true`) | Typos and invented fields would pass, and checkpoints could fill with chain-of-thought, which the report forbids (report [§Session checkpoint](../research/engineering-team-report.md#session-checkpoint)) |
| Ad-hoc JSON per script, without an envelope | Every caller would need per-script parsing for success, errors and warnings |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Catalog complete; every contract has a schema, an example and crafted invalid cases | `test_contracts.py::TestCatalog::test_catalog_has_the_23_documented_contracts`, `test_contracts.py::TestCatalog::test_every_schema_has_an_example`, `test_contracts.py::TestCatalog::test_crafted_cases_cover_every_contract`, `test_contracts.py::TestExamples::test_every_example_validates` | enforced |
| Keyword subset, closed objects, identity rules | `test_contracts.py::TestSchemaFiles::test_only_the_keyword_subset`, `test_contracts.py::TestSchemaFiles::test_every_object_schema_is_explicitly_closed`, `test_contracts.py::TestSchemaFiles::test_open_object_allowlist_is_current`, `test_contracts.py::TestSchemaFiles::test_schema_version_rules` | enforced |
| Copied `$defs` stay identical | `test_contracts.py::TestSchemaFiles::test_common_definitions_agree_across_files` | enforced |
| The validator agrees with the reference implementation | `test_contracts.py::TestDifferential` (skips cleanly when `jsonschema` is not installed) | enforced where `jsonschema` is installed (Python 3.13 in the build container) |
| One envelope; `ok` equals exit 0; no traceback on stdout | `test_skillkit_envelope.py::TestRunScript::test_ok_is_exactly_exit_zero`, `test_skillkit_envelope.py::TestRunScript::test_unexpected_exception_is_internal_without_traceback`, `test_skillkit_envelope.py::TestRunScript::test_contract_violations_by_main_are_internal` | enforced |
| Compact error shape | `test_skillkit_envelope.py::TestErrorHelpers::test_error_code_must_be_upper_snake`, `test_skillkit_envelope.py::TestErrorHelpers::test_error_message_is_compacted` | enforced |
| Strict JSON input | `test_skillkit_cli.py::TestReadJson::test_duplicate_keys_are_rejected`, `test_skillkit_cli.py::TestReadJson::test_nan_and_infinity_are_rejected` | enforced |
| Stable digests and idempotency keys | `test_skillkit_ids.py::TestIdempotencyKey::test_deterministic_and_sensitive_to_parts`, `test_skillkit_ids.py::TestDigest::test_digest_is_stable_across_key_order` | enforced |
| Every script envelope in a benchmark validates, and `ok` matches the exit code | bench deterministic grader; `test_bench_graders.py::TestDeterministic::test_ok_must_match_exit_code`; default gate `deterministic-schema-valid` (`bench.deterministic.schema_valid_rate == 1.0`) | enforced (lab); per skill once skills exist |
| Eval cases and output schemas are canonical contracts | `evals.case-schema`, `evals.output-schema-unknown` | enforced |
| R1's 21 new contracts follow the same rules | `test_contracts_r1.py` (SPEC-201 FR-013) | planned (SPEC-201) |

**Revisit when** a consumer outside this repository needs v1 stability guarantees, or when the
keyword subset blocks a contract the report requires.

## References

- [CONVENTIONS §3](../CONVENTIONS.md#3-script-contract-v), [§4](../CONVENTIONS.md#4-json-contracts),
  [contracts README](../../contracts/README.md)
- [SPEC-100 contracts and skillkit](../../specs/100-contracts-skillkit/spec.md)
- 12-factor [Factor 4](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-04-tools-are-structured-outputs.md),
  [Factor 9](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-09-compact-errors.md)
- ADR-0003 (structured output strategy), ADR-0006 (stdlib), ADR-0009 (idempotent Gitea writes)
