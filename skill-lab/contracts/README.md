# JSON contracts

The canonical machine-readable contracts between scripts, roles, the control
plane and the lab. `schemas/<name>.v1.schema.json` is the single source of
truth (JSON Schema draft 2020-12, `$id` `urn:skill-lab:schema:<name>:v1`).
`examples/<name>.v1.example.json` holds one realistic document per contract;
the examples are illustrative and never stand in for recorded model or Jev
output. Specification: [SPEC-100](../specs/100-contracts-skillkit/spec.md).

Skills never read this folder at runtime. `skill-lab sync` vendors the schemas a
skill emits or consumes into `skills/<name>/assets/schemas/`, and
`_skillkit.schemas.load_schema()` finds them there.

## Catalog

| Contract | Purpose | Producer | Consumer |
|---|---|---|---|
| `envelope` | The one JSON document every script prints on stdout: kind, producer, payload, compact errors | every skill script | any caller (agent, bench, CI) |
| `mutation-request` | A consequential write with authority, optimistic concurrency and an idempotency key | any role | control plane |
| `task-graph` | The DAG from `tasks.md`: tasks, edges, parallel waves, cycles | lead `plan_dag.py` | lead, taskstoissues |
| `spec-readiness` | Whether a feature may enter Ready for Build, with checks and traceability | lead `spec_readiness.py` | lead |
| `issue-contract` | Everything needed to reconstruct an issue's contract without a transcript | lead | Gitea, PSE |
| `implementation-evidence` | PSE evidence package: commits, per-criterion status, every check with command, exit code and log digest | PSE | review |
| `review-verdict` | Review's verdict on one commit: APPROVE, CHANGES_REQUESTED or BLOCKED_BY_ENV | review | lead, merge gate |
| `quality-gate` | Merge evidence manifest with explicit per-category applicability | review | merge gate |
| `session-checkpoint` | Compact handoff so a successor session can resume (not chain-of-thought) | any role | successor session |
| `normalized-event` | A verified, de-duplicated, normalised Gitea webhook delivery | event normalizer | state machine |
| `lease` | An exclusive, expiring claim on a unit of work | work-lease | all roles |
| `transition-decision` | The state machine's ruling on one requested board action | kanban-state-machine | lead, system |
| `merge-decision` | The merge gate's policy decision: AUTO_MERGE, HUMAN_APPROVAL_REQUIRED or BLOCKED | merge-policy-gate | lead, system |
| `task-issue-map` | Stable, committed task ID to Gitea issue mapping | taskstoissues | sync |
| `sync-drift-report` | Drift between `tasks.md`, the map and Gitea (reported, never auto-fixed) | sync | lead |
| `gitea-plan` | Dry-run plan of Gitea REST calls, each with an idempotency key and reason | taskstoissues | human, `--apply` |
| `twelve-factor-scorecard` | A 12-factor-agents audit: twelve factors scored 0–3 with evidence | twelve-factor-audit | human, CI |
| `validation-report` | `skill-lab validate` findings per skill and runtime profile | lab validate | CI |
| `benchmark-case` | One eval case: deterministic, agentic or trigger tier | skill evals | lab bench |
| `benchmark-result` | Graded outcome of one case on one runtime | lab bench | lab score |
| `benchmark-run` | One bench invocation: all results plus per-tier totals | lab bench | lab score, CI |
| `success-criteria` | A skill's explicit release gates | lab (per skill) | lab score |
| `skill-score` | Release readiness: static, tests, bench tiers, every gate with its actual value | lab score | human, CI |

## Rules every schema follows

- **Identity.** Payloads carry `"schema_version": 1`. Two documents are
  identified by a `schema` URN instead, as CONVENTIONS shows them: `envelope`
  and `benchmark-case` (which also accepts an optional `schema_version: 1`).
- **Closed objects.** Every object schema declares `additionalProperties`:
  `false` for records, or a value schema for maps keyed by IDs. Maps cannot
  constrain key format inside the keyword subset (no `propertyNames`); their
  `description` states the key pattern and producers enforce it. Exactly four
  slots are deliberately open (`additionalProperties: true`):
  `envelope.payload` (validated separately against `kind_schema`),
  `mutation-request.params`, `gitea-plan` request `body`, and Jev instruction
  objects in `benchmark-case`.
- **Keyword subset.** Only the keywords `_skillkit.jsonschema_mini` supports
  (CONVENTIONS §4), `$ref` only to `#/$defs/...` in the same file, and
  `format` only for `date-time`. Shared fragments such as `git_sha` or
  `task_id` are therefore copied into each file's `$defs`; a test keeps every
  copy identical.
- **Invariants are encoded.** Where the report demands it, the schema makes
  the bad state unrepresentable with `anyOf`/`oneOf`/`allOf`/`not`, for
  example: `envelope` with `ok: true` has no errors and an object payload;
  `review-verdict` APPROVE has no blockers and no failed or unverified
  requirements; `quality-gate` cannot pass with an applicable `not_run`
  category; `merge-decision` cannot AUTO_MERGE high-risk work, policy paths or
  non-passing gates; `benchmark-result` cannot carry judgments with `jev_mode:
  "off"`; `skill-score` cannot pass a gate with no measured value.
- **Compact text.** One-line fields are at most 500 characters and contain no
  line breaks; envelope messages are at most 300. `session-checkpoint` caps its
  lists so a handoff stays small for 32k-context local models.

## Versioning

1. A contract version is its file: `<name>.v1.schema.json` is immutable in
   meaning once released. Adding an **optional** field, loosening a limit, or
   adding documentation is a compatible change and stays in v1.
2. Anything a v1 consumer could reject or misread is breaking: a new required
   field, a removed or renamed field, a narrowed enum, pattern or limit, a
   changed meaning. Breaking changes create `<name>.v2.schema.json` with `$id`
   `urn:skill-lab:schema:<name>:v2`; producers emit `kind_schema` v2 and
   `schema_version: 2`.
3. v1 stays in this folder until no producer emits it. Consumers accept every
   version still listed here and dispatch on `schema_version` or `kind_schema`.
4. Every change ships with an updated example, passes
   `python3 -m unittest discover -s skill-lab/tests -t skill-lab`, and is
   re-vendored with `skill-lab sync` in the same commit. Adding a contract
   also adds a row to this table and an example (both are tested); a contract
   that every skill depends on also belongs in the `docs/CONVENTIONS.md` §4
   catalog.

## Validating

```sh
# Canonical copy, from the repository root
python3 - <<'EOF'
import json, sys
sys.path.insert(0, "skill-lab/shared")
from _skillkit import schemas
doc = json.load(open("skill-lab/contracts/examples/review-verdict.v1.example.json"))
print(schemas.validate_payload("review-verdict", doc))   # [] means valid
EOF
```

From a skill script, `schemas.validate_envelope(envelope, exit_code=code)`
checks an envelope and, when `ok` is true or the exit code is 1, its payload.
