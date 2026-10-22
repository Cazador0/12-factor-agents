# Architecture decision records

Each record states one decision, why it was made, what it costs, what was rejected, and how the lab
checks that the decision still holds. Together with [CONVENTIONS](../CONVENTIONS.md) they are the
"constitution" that specs and plans check themselves against. The system they describe is in
[architecture.md](../architecture.md).

## Index

| ADR | Decision | Main checks |
|---|---|---|
| [0001](0001-two-folder-monorepo.md) | Two folders, `skills/` and `skill-lab/`, each splittable with `git subtree`; skills never import the lab; shared code and schemas are vendored | `sync --check`, `vendor.*` rules, `scripts.import-third-party` |
| [0002](0002-portable-skill-format-and-runtime-priority.md) | One Agent Skills folder for Zed, Claude Code and Codex; strict frontmatter subset; Zed's limits or stricter; symlink install; `create-skill` reserved | `frontmatter.*`, `zed.*`, catalog budget, `install --check` |
| [0003](0003-ollama-inference-and-context-budget.md) | Ollama Cloud first, local at 32k context after a measured gate; `SKILL.md` ≤ 250 lines and 12 KB; no dependence on structured outputs; bounded repair loop | `body.*` rules, runtime request-shape tests, L1 gate |
| [0004](0004-json-contracts.md) | Versioned JSON contracts in a JSON Schema subset are the only state-bearing channel; one envelope per script; closed objects; compact errors; idempotency keys; JSON, not YAML | `test_contracts.py`, envelope tests, differential tests |
| [0005](0005-deterministic-control-flow.md) | Scripts decide every state transition; the model proposes, policy refuses, Gitea enforces; scripts are stateless reducers | deterministic tier at 100 %, containment |
| [0006](0006-stdlib-only-python-39.md) | Python ≥ 3.9 standard library only, for skills and lab | `scripts.*` rules, source-rule tests, CI on 3.9 |
| [0007](0007-jev-calibrated-grader.md) | Jev grades only what code cannot; uncertain is a fail that needs a human; never fabricate; calibrate before relying on thresholds | grader and bench tests; calibration (gap) |
| [0008](0008-role-authority-guardrails.md) | Lead, PSE and Review profiles plus global deny rules are guardrails; Gitea branch protection, the merge gate and the human merge are the boundary | config rules, merge-decision invariants |
| [0009](0009-gitea-system-of-record.md) | Gitea 28.x holds execution state behind a narrow, dry-run-first client; idempotent plans; swagger probing; `state/<name>` labels; test double now | contract tests; double and client tests (planned) |
| [0010](0010-definition-of-success.md) | "100 %" means 100 % of explicit gates; `not_run` never passes; merged versus complete | score and bench tests; `release check` (planned) |
| [0011](0011-skill-scoring-and-release-gates.md) | Static rubric, tests and three tiers; default thresholds; per-skill overrides with sample-size rationale | score tests, eval minimums |
| [0012](0012-security-model.md) | Untrusted text is data; verified and deduplicated webhooks; secrets only from the environment and always redacted; path guards; injection evals | redaction, path and validator tests; HMAC tests (planned) |
| [0013](0013-spec-first-delivery.md) | Spec Kit-shaped specs with traceability for every skill, lab component and release; no `.specify/` folder here | `spec.*` rules, G-OFF-08 |

All thirteen are **Accepted** (2026-10-22).

## Numbering

| Range | Owner | Status |
|---|---|---|
| 0001–0099 | Foundation (this set) | 0001–0013 accepted |
| 0101–0109 | R1 Shadow (SPEC-201) | 0101 autonomy policy file, 0102 action catalog, 0103 cloud-first inference, 0104 independent review loop, 0105 standalone export: planned (SPEC-201 T003–T007) |
| 0201–0209 | R2 Agent implementation (SPEC-202) | 0201–0207 planned (SPEC-202 FR-045) |
| 0301–0309 | R3 Guarded autonomous (SPEC-203) | planned; ADR-0301 amends decision 2 of ADR-0009 |

Release-scoped blocks let parallel planners add records without collisions (SPEC-201 synthesis
D-22). Later records cite earlier ones by number, for example "ADR-0301 amends ADR-0009 §2", where
§*n* is the decision's number in the `## Decision` section.

## Format

Every record uses these level-2 headings, in this order:

1. `# ADR-NNNN: <title>` as the only level-1 heading
2. `## Status`: `Proposed`, `Accepted`, `Superseded by ADR-NNNN` or `Deprecated`, optionally
   followed by one sentence of context
3. `## Date`: `YYYY-MM-DD` of the latest status change
4. `## Context`: the forces, with facts cited from
   [SOURCES.md](../research/SOURCES.md) and the
   [engineering-team report](../research/engineering-team-report.md) by section name
5. `## Decision`: numbered, so others can cite "§*n*"
6. `## Consequences`: `### Positive`, `### Negative`, and `### Residual risks` when any remain
7. `## Alternatives considered`: each with the reason it was rejected
8. `## Compliance`: a table of rule, the check that verifies it (command, validator rule or test
   id), and its state; then a **Revisit when** line
9. `## References`

Compliance states mean:

| State | Meaning |
|---|---|
| enforced | The check exists and runs in `skill-lab test`, `validate`, `sync --check` or bench today |
| planned | A spec or task names the check, but it is not built yet |
| external | Enforced outside the lab, by Gitea settings or a human |
| not run | The check exists but needs network access or keys this environment does not have |
| gap | Nothing checks it yet, and no task is scheduled. Each gap is listed below |

## Rules for changing records

- A decision is not rewritten. A new record supersedes it, and the old one's status becomes
  `Superseded by ADR-NNNN`. Fixing a broken link, a typo or a stale test name is not a new
  decision.
- A change that breaks a CONVENTIONS rule needs an ADR that amends CONVENTIONS in the same commit.
- When a fact in SOURCES.md changes upstream, update SOURCES.md and every ADR that cites it in the
  same commit.
- Links in these records stay inside `skill-lab/`, so they still resolve after
  `git subtree split --prefix skill-lab` (ADR-0001). Paths under `skills/` and the repository root
  are written as code, not as links. Test ids are written as `file::Class::method` relative to
  `skill-lab/tests/`.

## Open compliance gaps

These are the `gap` rows in the records above, kept here so they are not lost:

| ADR | Gap | Proposed check |
|---|---|---|
| 0001 | A skill copied alone may still depend on the lab (for example in its tests) | Copy each skill to an empty folder; run its tests and deterministic cases there |
| 0005 | Time-based authority (lease expiry, schedule expiry) may trust a caller's `--now` | Refuse a `--now` that differs from the system clock under `--apply` above `shadow` |
| 0007 | Jev thresholds are not calibrated on labelled data | A fixed-output judging mode in bench plus calibration sets; needs a SPEC-103 amendment and a CONVENTIONS §1 location |
| 0011 | A per-skill criteria file can lower a default threshold without a rationale | Enforce a floor, or require a rationale field; resolve SPEC-104's "defaults stay the floor" wording |
| 0012 | `GITEA_WEBHOOK_SECRET` is not in `SECRET_ENV_VARS`; webhook dedupe keys only on the unsigned delivery id | Add the variable to `_skillkit.redact` in R1; key the seen set on the body digest too |
| 0013 | Nothing fails if a `.specify/` folder appears, and nothing checks ADR-0001..0013's format | A lab test for both, alongside SPEC-201's `test_adrs_r1.py` |
