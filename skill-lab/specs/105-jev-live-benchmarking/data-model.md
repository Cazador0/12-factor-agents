# Data model: Jev live benchmarking (SPEC-105)

Field-level design for the contracts and configuration files this feature adds or changes. Every
schema follows CONVENTIONS §4: draft 2020-12, `$id` `urn:skill-lab:schema:<name>:v1`, the
`jsonschema_mini` keyword subset, `additionalProperties: false`, and `schema_version` const 1. Additive
changes keep v1. Once written, the schemas in `skill-lab/contracts/schemas/` are authoritative.

## Changed: `benchmark-result.v1` (additive)

| Field | Type | Meaning |
|---|---|---|
| `usage` | object, optional | `{model_input_tokens, model_output_tokens, jev_input_tokens, jev_output_tokens}`, integers ≥ 0, each nullable when the service did not report it |
| `judgments[].reasked` | boolean, optional | `true` when R-1 re-asked this judgment |
| `judgments[].first_value` | number or null, optional | The first Jev value before the re-ask; the graded `value` is the second |
| `error.code` | existing string | Adds `RUNTIME_UNAVAILABLE`, `JEV_UNAVAILABLE` (outage, R-3) and `DATA_BOUNDARY` |

## Changed: `benchmark-run.v1` (additive)

| Field | Type | Meaning |
|---|---|---|
| `counts_toward_streak` | boolean | `true` only when live, complete, not degraded, and no case `errored` (FR-011) |
| `exclusion_reasons` | array of enum | `replay`, `partial`, `outage`, `degraded`; empty when counting |
| `degraded` | boolean | A health check crossed a limit (FR-022) |
| `usage` | object | `{by_skill: {<skill>: usage}, total: usage}`, the same shape as the result `usage` |
| `cost` | object | `{total_usd: number or null, basis: "price-table" or "usage-only", prices_digest: string or null}` |
| `suite_digest` | string `sha256:` | Digest of the selected case files plus their skills' `SKILL.md` (already computed; now a field instead of a note) |
| `commit` | string or null | Git HEAD of the repository |
| `health_reports` | array | `[{skill, path, sha256, status}]`, one per skill (FR-021) |
| `catalog` | object | `{agentic_pass_rate, trigger_accuracy, agentic_schema_valid_rate, uncertain_rate, guardrail_pass_rate}`, each number or null |
| `log` | object | `{path, sha256}` of `run.log.jsonl` |

## Changed: `success-criteria.v1` (additive)

| Field | Type | Meaning |
|---|---|---|
| `gates[].scope` | enum `skill`, `catalog`; optional, default `skill` | Which level the gate measures (R-5) |

## New: `benchmark-streak.v1`

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | const 1 | |
| `model` | string or null | Model of the current streak |
| `suite_digest` | string or null | Suite of the current streak |
| `length` | integer ≥ 0 | Consecutive counting runs passing every bench gate |
| `runs` | array | `[{run_id, started_at, passed}]` in the streak, oldest first |
| `local_unlock_evidence` | boolean | `length ≥ 3` |
| `unstable_cases` | array | `[{skill, case_id, passed_in, failed_in}]` |
| `excluded_runs` | array | `[{run_id, reasons[]}]` for non-counting runs |
| `broken_by` | object or null | `{run_id, reason (gate_failed, model_changed, suite_changed, unstable_case), detail}` for the run that ended the previous streak |
| `computed_at` | date-time | |

## New: `run-health.v1`

| Field | Type | Meaning |
|---|---|---|
| `schema_version` | const 1 | |
| `run_id` | string or null | Run being monitored; `null` for the reviewer session |
| `skill` | string or null | Skill whose cases just finished |
| `target` | object | `{kind: benchmark-container, model-session or reviewer-session, id}` |
| `container` | object | `{cpu_percent, memory_percent, disk_free_bytes, processes}`, each number or null, plus `notes[]` |
| `apis` | array | `[{service, requests, p50_ms, p95_ms, error_rate, rate_limited, retry_wait_ms}]` |
| `sessions` | array | `[{id, turns, tool_calls, context_used, context_limit, stalled, end_reason}]` |
| `limits` | object | The limits applied, copied from `monitor-limits.json` with its digest |
| `problems` | array | `[{code, metric, actual, limit, detail}]`, empty when healthy |
| `status` | enum `ok`, `degraded` | `degraded` iff `problems` is non-empty |
| `assessment` | object, optional | `{model, summary ≤ 1000, recommendations[≤ 10]}` from the advisory agent call |
| `assessment_error` | object, optional | `{code, message}` when the advisory call failed |
| `taken_at` | date-time | |

## Configuration: `skill-lab/benchmarks/prices.json` (person-maintained, lab format)

```json
{
  "schema_version": 1,
  "updated_at": "2026-10-22T00:00:00Z",
  "currency": "USD",
  "services": {
    "ollama-cloud": {"<model>": {"input_per_mtok": 0.0, "output_per_mtok": 0.0}},
    "typesafe": {"jev-latest": {"input_per_mtok": 0.0, "output_per_mtok": 0.0}}
  }
}
```

It ships with empty `services`, so every run reports `usage-only` until the person enters prices. The
lab never fills it in.

## Configuration: `skill-lab/benchmarks/monitor-limits.json` (lab format)

```json
{
  "schema_version": 1,
  "memory_percent_max": 90,
  "disk_free_bytes_min": 1073741824,
  "api_error_rate_max": 0.05,
  "no_progress_seconds_max": 600
}
```

These are the delegated starting values (Q24), tuned after the smoke run. The file is a critical policy
path, like the criteria files: an agent may propose a change after the smoke run, and it takes effect only
with the person's approval (confirmed in the plan refinement, 2026-10-22).

## Configuration: `skill-lab/benchmarks/criteria/_defaults.json` (changed)

- `jev-uncertain`: op `lt`, threshold 0.1 (was `lte`): "fewer than 10%", Q16.
- New gate `agentic-guardrail`: metric `bench.agentic.guardrail.pass_rate`, `eq 1.0`, scope `skill`, optional when unavailable.
- New catalog-scope copies of `agentic-quality`, `trigger-routing`, `agentic-schema-valid`, `jev-uncertain` and `agentic-guardrail`, with ids suffixed `-catalog`.
