# Run the live benchmarks

How to run the model-graded benchmark tiers (agentic and trigger) for real. Use Ollama Cloud for
inference and Jev for grading, first in a Claude Code cloud session and then on your own machine.
Getting a Jev key, and what Jev measures, is covered in [setup-jev.md](setup-jev.md).

Nothing in these tiers is ever simulated. Without network access or keys, every model-graded case is
reported as `skipped` with a reason (`LIVE_PREREQ_MISSING: ...`), and a gate that did not run never
counts as passed (CONVENTIONS §5, ADR-0010).

## What runs where

| Tier | Needs | Runs in |
|---|---|---|
| `deterministic` | Python 3.9 or later only | anywhere, offline (CI runs it on every push) |
| `agentic` | a model runtime, plus Jev for judgments | wherever the runtime is reachable |
| `trigger` | Jev (`choice` routing) or a model runtime | wherever either one is reachable |

Inference is cloud first ([SPEC-200](../../specs/200-release-roadmap/spec.md)): run `--runtime ollama-cloud`
until its gates pass on 3 consecutive live runs. After that, run the same suite on `ollama-local`.

## A. Claude Code cloud session

### 1. Allow the two hosts

Open the environment for editing: select the caret after the session title, then
**Edit cloud environment**. Under **Network access**, choose **Custom** and add one host per line to
**Allowed domains**:

```text
api.typesafe.ai
ollama.com
```

Tick **Also include default list of common package managers** so the usual registries keep working.
Running sessions follow a network-access change within about a minute. Reference:
https://code.claude.com/docs/en/cloud-environments#network-access

### 2. Add the keys

In the same dialog, add both keys to **Environment variables** (`.env` format, one per line):

```text
TYPESAFE_API_KEY=<your Jev key>
OLLAMA_API_KEY=<your key from https://ollama.com/settings/keys>
```

- A session reads these values when it starts, so **start a new session** after you change them.
- Anyone who uses the environment can read these values. Never paste a key into chat, a file, a
  commit, or an issue. The lab reads keys only from the environment and redacts them from all output.
- `JEV_API_KEY` is accepted as an alias. `TYPESAFE_API_KEY` wins if both are set.
- Network secrets (the agent proxy adds the header, and the key never enters the VM) are not supported
  by the lab yet. The Jev client and the `ollama-cloud` runtime need the variable to be present, and
  without it they report `skipped`.

### 3. Check the environment

```sh
python3 skill-lab/bin/skill-lab doctor --pretty
```

You want `env.typesafe-key` and `env.ollama-key` to show as present (doctor never prints values), the
Jev probe to answer (200 means the key works, 401 means the host is reachable but the key is wrong),
and `ollama.com` to answer. The `localhost:11434` probe fails in a cloud container. That is expected:
a cloud container can never reach the Ollama on your machine.

### 4. Offline gates first

```sh
python3 skill-lab/bin/skill-lab bench --tier deterministic --pretty
```

If anything fails here, fix it before you spend live calls.

### 5. Pick a cloud model

The `ollama-cloud` runtime needs `--model`. Without it, every agentic and trigger case is `skipped`.
List the models the API offers and choose one that supports tools:

```sh
curl -s https://ollama.com/api/tags | python3 -c "import json,sys; print('\n'.join(m['name'] for m in json.load(sys.stdin)['models']))"
```

Ollama's docs use `gemma4:31b` as a direct-API example. Use the exact name from the list, without the
`-cloud` suffix, which only applies through a signed-in local daemon. Write the model and the date
into your run notes.

### 6. Run every tier live and record cassettes

```sh
python3 skill-lab/bin/skill-lab bench --tier all --runtime ollama-cloud --model gemma4:31b \
  --jev live --record skill-lab/benchmarks/cassettes --pretty
```

- Results go to `skill-lab/benchmarks/runs/<run_id>/` (git-ignored): one `benchmark-result.v1` per
  case and a `benchmark-run.v1` summary.
- `--record` stores the real Jev and runtime exchanges, without secrets, so the run can be replayed
  offline later. A replay is labelled `jev_mode: "replay"` and never satisfies a live gate.
- Ollama Cloud has no structured outputs, so the runtime puts the schema in the prompt and gives an
  invalid reply up to 2 repair turns (`--max-repairs`).
- To narrow a run, add `--skill <name>` (repeatable) or use `--tier agentic,trigger`.

### 7. Score every skill

`score` takes one skill at a time and reads the latest run that has results for it:

```sh
for dir in skills/*/; do
  python3 skill-lab/bin/skill-lab score --skill "$(basename "$dir")" --pretty
done
```

Each `skill-score.v1` reports `release_ready`, every gate with its measured value, and the gates that
were skipped and why. Add `--strict` to require every gate to have run.

### 8. Replay later, offline

```sh
python3 skill-lab/bin/skill-lab bench --tier agentic,trigger --runtime replay --model gemma4:31b \
  --jev replay --cassettes skill-lab/benchmarks/cassettes --pretty
```

A request that was never recorded fails with a cassette miss. Replay never invents an answer.

## B. Your own machine (Ollama local)

On your machine the lab can reach your local Ollama. These runs are the L1 evidence for enabling
local inference (SPEC-202). They count only after the cloud gates pass.

```sh
ollama serve                         # or open the Ollama app
ollama pull gpt-oss:20b              # any tool-capable model that fits your GPU; check `ollama ps`
export TYPESAFE_API_KEY=...          # in your shell only, never in a file in the repo
python3 skill-lab/bin/skill-lab doctor --pretty
python3 skill-lab/bin/skill-lab bench --tier all --runtime ollama-local --model gpt-oss:20b \
  --jev live --record skill-lab/benchmarks/cassettes --pretty
```

- The local runtime sends `num_ctx` 32768 (`--num-ctx` changes it) and passes the case's JSON Schema
  as `format`, which local Ollama supports.
- Set `OLLAMA_HOST` if Ollama is not at `localhost:11434`.
- The cloud variant (section A, steps 5 to 7) also works here: export `OLLAMA_API_KEY` and use
  `--runtime ollama-cloud`.
- Then score each skill as in step 7.

## C. GitHub Actions (manual)

The `live-bench` job in [`.github/workflows/skill-lab.yml`](../../../.github/workflows/skill-lab.yml)
runs only through **Run workflow** (`workflow_dispatch`), and only after the offline job passes. It
asks for the cloud model as an input.

1. In the repository settings, under **Secrets and variables → Actions**, add the repository secrets
   `TYPESAFE_API_KEY` and `OLLAMA_API_KEY`.
2. **Actions → skill-lab → Run workflow**, then enter the model (for example `gemma4:31b`).
3. The job runs `bench --tier all --runtime ollama-cloud --model "$MODEL" --jev live --record ...`, scores every skill,
   and uploads the runs and cassettes as an artifact. If either secret is missing, it skips with a
   notice instead of failing. GitHub-hosted runners reach both hosts directly, so no allowlist is
   needed.

## Troubleshooting

| Symptom | Fix |
|---|---|
| Every agentic and trigger case `skipped`, `--model is required` | Add `--model` (step 5) |
| `OLLAMA_API_KEY is not set`, or doctor shows a key absent | Add it (step 2) and start a new session |
| Proxy `403` or `CONNECT tunnel failed` | The host is not in Allowed domains (step 1) |
| `model ... is not offered by https://ollama.com/api/tags` | Use a name exactly as listed in step 5 |
| Jev 401 or 403 | The key is wrong or not activated; see [setup-jev.md](setup-jev.md) |
| Gates show `not_run` or `skipped` | Correct behaviour when a tier could not run. Fix access, never the thresholds |
| Agentic cases fail schema validation on Ollama Cloud | Read the case's `benchmark-result` notes. Persistent failures are real findings about the skill or the model |
