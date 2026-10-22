# Skill Lab

The lab builds, validates, installs, benchmarks, and scores the portable skills in
[`../skills/`](../skills/README.md). It is Python 3.9+ standard library only, like the skills. The two
folders are designed to split into separate repositories later (`git subtree split --prefix skills`
and `--prefix skill-lab`), so a skill never imports anything from here at runtime. It receives
`_skillkit` and the contracts as vendored copies instead.

The binding rules are in [docs/CONVENTIONS.md](docs/CONVENTIONS.md). Where this README and
CONVENTIONS disagree, CONVENTIONS wins.

## Quickstart

```sh
python3 skill-lab/bin/skill-lab doctor --pretty                  # toolchain, layout, installs, keys present, endpoints
python3 skill-lab/bin/skill-lab sync                             # vendor _skillkit + schemas into every skill
python3 skill-lab/bin/skill-lab validate --runtime all --pretty  # every [V] rule, for zed, claude and codex
python3 skill-lab/bin/skill-lab test                             # lab self-tests + every skill's unit tests
python3 skill-lab/bin/skill-lab bench --tier deterministic       # offline eval cases
python3 skill-lab/bin/skill-lab catalog                          # regenerate skills/CATALOG.json
python3 skill-lab/bin/skill-lab install                          # symlink skills into .agents/skills and .claude/skills
python3 skill-lab/bin/skill-lab score --skill review-verifier    # release gates for one skill
```

Run the commands from the repository root. Each prints exactly one `envelope.v1` JSON document on
stdout, and `--pretty` indents it. Logs go to stderr. `skill-lab --help` and `skill-lab <command> --help`
print plain text.

## Commands

| Command | What it does | Main options |
|---|---|---|
| `validate` | Checks skills against every **[V]** rule in CONVENTIONS: frontmatter, body budget, links, script contract, stdlib-only imports, evals, specs and traceability. Emits `validation-report.v1` | `--skill NAME`, `--runtime zed,claude,codex\|all`, `--no-run` |
| `sync` | Vendors the canonical `shared/_skillkit` and contract schemas into each skill | `--skill`, `--add-schema NAME`, `--check` (exit 1 on drift) |
| `install` | Links or copies skills into `.agents/skills/` (Zed, Codex) and `.claude/skills/` (Claude Code). Never touches paths it does not manage | `--runtime`, `--global` or `--project DIR`, `--mode symlink\|copy`, `--dry-run`, `--check`, `--force` |
| `catalog` | Generates `skills/CATALOG.json` and its byte count against Zed's 50 KB catalog budget | `--check` (exit 1 when stale) |
| `new` | Scaffolds `skills/<name>/` and `specs/NNN-<name>/` from `templates/skill/`, with `TODO(scaffold)` marking every blank. Takes the spec number and family from the CONVENTIONS §6 table and keeps a spec written first | `name`, `--family`, `--spec`, `--description`, `--author`, `--dry-run` |
| `doctor` | Reports Python, git, layout, install parity, whether keys are present (never their values), and reachability of Jev, Ollama Cloud, local Ollama and Gitea | `--offline` |
| `test` | Runs the lab suite and every skill's `tests/` in separate subprocesses, and aggregates the counts | `--skill` or `--lab-only`, `--timeout` |
| `bench` | Runs eval cases by tier and grades them; writes `benchmark-result.v1` files and a `benchmark-run.v1` | `--tier`, `--skill`, `--tag`, `--runtime`, `--model`, `--jev live\|replay\|off`, `--record`, `--cassettes`, `--out` |
| `score` | Scores one skill against its release gates; emits `skill-score.v1` with `release_ready` | `--skill` (required), `--run`, `--criteria`, `--strict`, `--no-tests` |

Every command also takes `--pretty`, `--now ISO-8601` (fixed clock for deterministic output) and
`--repo DIR`. The details, and the flags not listed here, are in each command's `--help` and in
[SPEC-101](specs/101-lab-core/spec.md) (validate, sync, install, catalog, new, doctor, test),
[SPEC-102](specs/102-bench-runtimes-graders/spec.md) (bench), [SPEC-103](specs/103-jev-grader/spec.md)
(the Jev client), and [SPEC-104](specs/104-scoring-gates/spec.md) (score).

### Exit codes (every command and every skill script)

| Code | Meaning |
|---|---|
| 0 | Completed, and the checked thing is OK |
| 1 | Completed, and the checked thing failed (validation errors, drift, a failing gate) |
| 2 | Usage or input error |
| 3 | External dependency failure (network, Gitea, a model API) |
| 4 | Refused by policy or a guardrail |

## How scoring and gates work

1. **Tiers.** Each skill ships eval cases in `skills/<name>/evals/cases/` (CONVENTIONS §5):
   - `deterministic` runs a script offline and is graded by exit code, schema validity, and JSON
     assertions. Every skill has at least 4.
   - `agentic` runs a model with the skill loaded the way Zed loads it. The model must return JSON
     for a schema, which is graded by schema validity, assertions, and Jev judgments. At least 2.
   - `trigger` checks routing across the whole catalog: at least 3 positive and 1 negative query.
2. **Jev judgments.** Jev answers narrow typed questions with calibrated probabilities. A `noul`
   result passes at or above its threshold, counts as **uncertain** between 0.35 and the threshold,
   and fails below 0.35. An uncertain result counts as a fail and is flagged `needs_human`. Jev grades
   only what code cannot check ([ADR-0007](docs/adr/0007-jev-calibrated-grader.md)).
3. **Gates.** [`benchmarks/criteria/_defaults.json`](benchmarks/criteria/_defaults.json) sets the defaults
   for every skill: static score at least 90, 100 % unit tests, 100 % deterministic cases passing and
   schema-valid, at least 95 % agentic schema-valid, at least 80 % agentic quality, at least 90 %
   trigger routing, and at most 10 % uncertain Jev answers. `benchmarks/criteria/<skill>.json`
   (`success-criteria.v1`) can replace a default gate or add one. A threshold below the default needs
   the sample-size rationale and bounding aggregate gate of
   [ADR-0011 §6](docs/adr/0011-skill-scoring-and-release-gates.md#decision).
4. **Readiness.** `score` reports `release_ready: true` only when every gate that could run in this
   environment passed, and it lists every skipped gate with its reason. **A gate that did not run never
   counts as passed** ([ADR-0010](docs/adr/0010-definition-of-success.md),
   [ADR-0011](docs/adr/0011-skill-scoring-and-release-gates.md)). `--strict` requires every gate to
   have run. "100 % success" means 100 % of the explicitly defined gates passed. It never means
   "defect-free".
5. **No fabricated results.** Without network access or keys, model and Jev tiers report `skipped`.
   Replay uses only cassettes recorded during a real live run, and its results are labelled
   `jev_mode: "replay"`.

Details: [benchmarks/README.md](benchmarks/README.md). Live runs:
[docs/runbooks/live-benchmarks.md](docs/runbooks/live-benchmarks.md) and
[docs/runbooks/setup-jev.md](docs/runbooks/setup-jev.md).

## Layout

| Path | Contents |
|---|---|
| `bin/skill-lab` | CLI entry point |
| `lab/` | Command modules and benchmark runtimes (`lab/runtimes/`: `ollama-local`, `ollama-cloud`, `claude-cli`, `codex-cli`, `replay`) |
| `shared/_skillkit/` | Canonical shared library, vendored into every skill by `sync` |
| [`contracts/`](contracts/README.md) | JSON Schemas (`<name>.v1.schema.json`, the single source of truth) and examples |
| `benchmarks/` | `criteria/` gates; `runs/` holds git-ignored bench output |
| `config/` | Runtime templates: [Zed](config/zed/README.md), [Claude Code](config/claude/README.md), [Codex](config/codex/README.md) |
| `docs/` | [CONVENTIONS](docs/CONVENTIONS.md), [ADRs](docs/adr/), [verified sources](docs/research/SOURCES.md), runbooks |
| `specs/` | One spec per skill and lab component, each with a `traceability.json` |
| `templates/skill/` | What `skill-lab new` renders |
| `fixtures/` | The golden Spec Kit feature used by tests and evals |
| `tests/` | Lab self-tests |

## Specs and decisions

- Lab components: [SPEC-100](specs/100-contracts-skillkit/spec.md) (contracts and `_skillkit`),
  [SPEC-101](specs/101-lab-core/spec.md), [SPEC-102](specs/102-bench-runtimes-graders/spec.md),
  [SPEC-103](specs/103-jev-grader/spec.md), [SPEC-104](specs/104-scoring-gates/spec.md).
- Releases: [SPEC-200 roadmap](specs/200-release-roadmap/spec.md) (progressive autonomy, cloud-first
  inference), [SPEC-201 R1 Shadow](specs/201-release-shadow/spec.md),
  [SPEC-202 R2 Agent implementation](specs/202-release-agent-implementation/spec.md),
  [SPEC-203 R3 Guarded autonomous](specs/203-release-guarded-autonomous/spec.md).
- Architecture decisions: [docs/adr/](docs/adr/), for example
  [ADR-0003](docs/adr/0003-ollama-inference-and-context-budget.md) (Ollama and the 32k budget) and
  [ADR-0008](docs/adr/0008-role-authority-guardrails.md) (role guardrails).
- Runtime setup: [Zed + Ollama](docs/runbooks/zed-ollama-setup.md),
  [live benchmarks](docs/runbooks/live-benchmarks.md), [Jev](docs/runbooks/setup-jev.md).

## Testing the lab

```sh
python3 -m unittest discover -s skill-lab/tests -t skill-lab -v
python3 -m unittest discover -s skill-lab/tests -t skill-lab -p 'test_configs.py' -v   # runtime templates, docs, CI
```

CI ([`.github/workflows/skill-lab.yml`](../.github/workflows/skill-lab.yml)) runs `sync --check`,
`validate --runtime all`, `test`, `bench --tier deterministic`, and `catalog --check` on Python 3.9
and 3.13. A manual `live-bench` job runs the live tiers when the repository secrets are set.
