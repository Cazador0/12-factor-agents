# Benchmarks

How the lab measures skills: `skill-lab bench` runs eval cases and writes graded results
([SPEC-102](../specs/102-bench-runtimes-graders/spec.md)), Jev judges model outputs
([SPEC-103](../specs/103-jev-grader/spec.md)), and `skill-lab score` turns everything into release
gates ([SPEC-104](../specs/104-scoring-gates/spec.md)). Nothing is ever fabricated: a case that
needs a model or Jev that is not reachable is `skipped` with a reason, and a gate that did not run
never passes.

## Layout

```text
benchmarks/
  criteria/_defaults.json   # gates every skill must meet (lab format, see below)
  criteria/<skill>.json     # success-criteria.v1: per-skill thresholds and extra gates
  runs/<run_id>/            # git-ignored output of skill-lab bench
    benchmark-run.json      # benchmark-run.v1 (all results + per-tier summary + notes)
    results/<skill>/<case_id>.json   # benchmark-result.v1, one per case
```

Cases live with their skill: `skills/<name>/evals/cases/<case-id>.json` (`benchmark-case.v1`,
CONVENTIONS §5).

## Running

```sh
# Offline, every skill, CI default
python3 skill-lab/bin/skill-lab bench --tier deterministic

# One skill, cases tagged "guardrail"
python3 skill-lab/bin/skill-lab bench --skill review-verifier --tag guardrail

# Zed + local Ollama (GPU under 24 GB: keep num_ctx at 32768)
python3 skill-lab/bin/skill-lab bench --tier agentic,trigger --runtime ollama-local --model qwen3:14b

# Ollama Cloud with Jev, recording a cassette for later replay
OLLAMA_API_KEY=... TYPESAFE_API_KEY=... python3 skill-lab/bin/skill-lab bench \
  --tier agentic,trigger --runtime ollama-cloud --model gpt-oss:120b --jev live --record skill-lab/benchmarks/cassettes/r1

# Replay that recording anywhere, with no network or keys
python3 skill-lab/bin/skill-lab bench --tier agentic,trigger --runtime replay --model gpt-oss:120b \
  --jev replay --cassettes skill-lab/benchmarks/cassettes/r1

# Score one skill (exit 0 = release-ready for the gates that could run here)
python3 skill-lab/bin/skill-lab score --skill review-verifier
python3 skill-lab/bin/skill-lab score --skill review-verifier --strict   # every gate must have run
```

| Flag | Meaning |
|---|---|
| `--tier` | `deterministic` (default), `agentic`, `trigger`, `all`; repeatable or comma-separated |
| `--skill`, `--tag` | Select skills (default all) and cases carrying every given tag |
| `--runtime` | `ollama-local`, `ollama-cloud`, `claude-cli` (`claude`), `codex-cli` (`codex`), `replay` |
| `--model`, `--num-ctx`, `--max-repairs` | Model name; local context (default 32768); cloud repair turns (default 2) |
| `--jev` | `live`, `replay` or `off`; default live when a key is set and the API answers, else off |
| `--router` | Trigger routing: `auto` (Jev when available, else the runtime), `jev`, `runtime` |
| `--record DIR`, `--cassettes DIR` | Record live exchanges; replay source |
| `--out DIR`, `--now`, `--repo`, `--pretty` | Output folder, fixed timestamp (deterministic `run_id`), repository root, indentation |

Environment: `OLLAMA_HOST` (local base URL), `OLLAMA_API_KEY` (cloud), `TYPESAFE_API_KEY` or
`JEV_API_KEY`, `TYPESAFE_BASE_URL`, `TYPESAFE_DEFAULT_MODEL`. Keys are read only from the
environment and redacted from every output and cassette.

## What each tier measures

- **deterministic**: the script runs with `sys.executable`, cwd = the skill folder, a minimal
  environment, stdin from `stdin_file`, and a 60 s timeout. `{tmp}` in args or env is a fresh per-case
  folder; use it for `--state-dir` so a case never writes into the skill. Graded by exit code, envelope
  and payload validity (canonical contracts) and assertions.
- **agentic**: one model turn that sees the skill the way the Zed Agent does: Zed's `<available_skills>`
  catalog in the system prompt and the `<skill_content>` envelope, then the fixture files, then the
  task, in the user prompt (`lab/runtimes/zed_emulation.py`, mirrored from Zed's source). Results are
  labelled `<runtime>-zed-emulation`: an emulation of Zed's skill loading, not Zed itself. Graded by
  JSON validity against `output_schema`, assertions, then Jev judgments, one request per case.
- **trigger**: the query is routed across the whole catalog, by a Jev choice question (every skill's
  description plus `none`) or by the model naming a skill. `routed_skill`, the method and the
  probabilities are recorded.

Ollama Cloud has no structured outputs, so the schema goes in the prompt and an invalid reply gets up
to two repair turns with the compact validation errors. Ollama local also receives the schema as
`format`.

## Gates

`criteria/_defaults.json` holds the default gates for every skill:

| Gate | Metric | Rule | When unmeasured |
|---|---|---|---|
| `static-score` | `static.score` | >= 90 | not_run (blocks) |
| `unit-tests` | `tests.pass_rate` | = 1.0 | not_run (blocks) |
| `deterministic-all-pass` | `bench.deterministic.pass_rate` | = 1.0 | not_run (blocks) |
| `deterministic-schema-valid` | `bench.deterministic.schema_valid_rate` | = 1.0 | not_run (blocks) |
| `agentic-schema-valid` | `bench.agentic.schema_valid_rate` | >= 0.95 | skipped, with reason |
| `agentic-quality` | `bench.agentic.pass_rate` | >= 0.8 | skipped, with reason |
| `trigger-routing` | `bench.trigger.accuracy` | >= 0.9 | skipped, with reason |
| `jev-uncertain` | `bench.jev.uncertain_rate` | <= 0.1 | skipped, with reason |

The defaults file is a lab format: success-criteria gates plus `optional_when_unavailable` and a
required `optional_reason`. A skill's `criteria/<skill>.json` is a plain `success-criteria.v1`: each of
its gates replaces the default with the same `id`, or else the default on the same `metric`, and keeps
that default's optionality; any other gate is added and is mandatory. The static rubric, the metric
vocabulary and the readiness rules are in SPEC-104.

`release_ready: true` means every gate that could run here passed (CONVENTIONS §9.6); the envelope then
lists skipped gates and adds `RELEASE_READY_OFFLINE`. `--strict` requires every gate to have run.
