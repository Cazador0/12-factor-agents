# Set up Jev for live benchmarks

How to get from "the Jev tiers say `skipped`" to graded live benchmark runs. Expect about
10 minutes once you have a TypeSafe key.

## 1. What Jev is and why the lab uses it

Jev is TypeSafe AI's **System One** model. It does not generate prose. It takes a `state` (text or
JSON) and a set of named questions, and returns **typed, calibrated answers**:

| Question type | Answer | How the lab uses it |
|---|---|---|
| `noul` | probability that a statement is true, 0–1 | "The verdict cites the failing requirement IDs": pass at ≥ 0.8, uncertain between 0.35 and 0.8, fail below 0.35 |
| `choice` | one label, its confidence, and the full probability distribution | Trigger benchmarks: which installed skill should handle this request, or "none" |
| `score` | a probability-weighted position on ordered levels | Graded quality dimensions, such as how specific the acceptance criteria are |

- Endpoint: `POST https://api.typesafe.ai/v1/systemone` (list models with `GET /v1/models`).
- Model: `jev-latest` unless you set `TYPESAFE_DEFAULT_MODEL`.
- Auth: `Authorization: Bearer <key>`.
- Client: `skill-lab/lab/jev.py` (stdlib only, built from the official SDK's OpenAPI wire models,
  vendored at `skill-lab/docs/research/vendor/typesafe-wire-models.py`).

Jev grades only what code cannot check. Exit codes, schema validity, and JSON assertions are graded
deterministically first, and Jev is never the only gate for a deterministic property (ADR-0007).
Typed output guarantees the answer's shape, not its truth, so thresholds are checked against our own
labelled cases before anyone relies on them.

## 2. Get a TypeSafe API key

1. Sign in to the TypeSafe console at `console.typesafe.ai` and open **API Keys**. Access may still
   be waitlisted; if so, join the waitlist on `typesafe.ai` and wait for the console invite.
2. Create a key and copy it once. You will paste it into the environment settings in step 4, and
   nowhere else.

## 3. Allow the hosts (Claude Code cloud environments)

Cloud sessions reach the internet through an egress proxy that denies hosts not on the
environment's allowlist. The lab needs two hosts:

| Host | Used by |
|---|---|
| `api.typesafe.ai` | Jev grading (`--jev live`), `doctor` probe |
| `ollama.com` | Ollama Cloud inference (`--runtime ollama-cloud`), `doctor` probe |

Open the environment's settings (cloud environment menu in the session title bar → **Edit** →
**Network access**). Either choose a broader access level, or add both hosts under **Allowed
domains** and leave **Allow package managers** ticked. Steps:
https://code.claude.com/docs/en/cloud-environments#network-access

## 4. Add the keys as environment secrets

In the same environment settings, add:

| Secret | Value |
|---|---|
| `TYPESAFE_API_KEY` | your Jev key (`JEV_API_KEY` is accepted as an alias; `TYPESAFE_API_KEY` wins if both are set) |
| `OLLAMA_API_KEY` | an Ollama key from https://ollama.com/settings/keys |

Never paste a key into a chat, a commit, an issue, or a file in the repo. The lab reads keys only
from the environment and redacts them from every JSON output (`_skillkit.redact`). Cassettes
recorded with `--record` contain no secrets.

Start a new session after changing secrets so the environment picks them up.

## 5. Verify

```sh
python3 skill-lab/bin/skill-lab doctor --pretty
```

`doctor` reports whether each variable is present (never its value) and probes
`https://api.typesafe.ai/v1/models`, `https://ollama.com/api/tags`, and `http://localhost:11434/api/tags`
with a 5-second timeout. You want:

- `TYPESAFE_API_KEY` present, and the TypeSafe probe answering (200 means the key works; 401 means
  the host is reachable but the key is wrong).
- `OLLAMA_API_KEY` present, and `ollama.com` answering.
- `localhost:11434` failing is expected in a cloud container (see step 7).

## 6. Run live (cloud first)

Inference is cloud-first (SPEC-200). Run everything against Ollama Cloud with live Jev grading, and
record cassettes so later runs can be replayed offline:

```sh
python3 skill-lab/bin/skill-lab bench --tier all --runtime ollama-cloud --model gemma4:31b --jev live \
  --record skill-lab/benchmarks/cassettes --pretty
for dir in skills/*/; do
  python3 skill-lab/bin/skill-lab score --skill "$(basename "$dir")" --pretty
done
```

- `--model` is required: without it every agentic and trigger case is `skipped`. Use a model name
  exactly as `https://ollama.com/api/tags` lists it ([live-benchmarks.md](live-benchmarks.md) step 5).
- `bench` writes one `benchmark-result.v1` per case and a `benchmark-run.v1` summary under
  `skill-lab/benchmarks/runs/<run_id>/`.
- `score` takes one skill (`--skill`, required) and combines validation, unit tests, and the latest
  run into its `skill-score.v1`, with `release_ready` and every gate that did not run, and why.
- Narrow a run with `--skill <name>` (repeatable) or `--tier deterministic|agentic|trigger`.
- For a release-gate run, add `--strict` to `score`. A gate that is optional when its network or
  key is unavailable then reports `not_run` instead of `skipped`, and `release_ready` stays false,
  so a gate run can never pass on gates that did not run.
- Trigger (routing) cases are routed by Jev whenever it is available (`--router auto`, the
  default); `--router runtime` asks the model under test instead, and each result records which
  method was used.

Local inference turns on only after this cloud suite passes its agentic and trigger gates on
**3 consecutive live runs** and you sign off that the results match your intent (SPEC-200, SPEC-202).

## 7. Local-machine variant

On your own machine, where Ollama runs and your GPU has under 24 GB, use the local runtime. It sends
`num_ctx` 32768; Zed's default of 4096 is too small for skills:

```sh
ollama serve            # or open the Ollama app
python3 skill-lab/bin/skill-lab bench --tier all --runtime ollama-local --model gpt-oss:20b --jev live --pretty
```

Use any tool-capable model you have pulled (`ollama list`). Set `OLLAMA_HOST` if Ollama is not on `localhost:11434`. A cloud container can never reach your
machine's `localhost:11434`, so local benchmarks always run on your machine, never in a Claude Code
cloud session.

## 8. Troubleshooting

| Symptom | Meaning | Fix |
|---|---|---|
| `CONNECT tunnel failed, response 403`, or a proxy 403 in `doctor` | The egress proxy denied the host | Add the host to Allowed domains (step 3), then start a new session |
| TypeSafe 401 or 403 (`JevAuthError`) | The host is reachable, but the key is missing, wrong, or not allowed | Re-check the `TYPESAFE_API_KEY` secret (step 4) |
| TypeSafe 422 (`JevValidationError`) | The request shape was rejected; `detail` lists `loc` / `msg` | A bug in a case's judgment definition. Fix the case JSON; the lab pre-checks most of these |
| TypeSafe 429 or 5xx | Rate limited or temporarily down | The client retries up to 3 times, honouring `retry-after-ms` / `retry-after`. Re-run later if it still fails |
| Tiers or gates reported `skipped` / `not_run` | No network or no key for that tier | This is correct behaviour. A skipped tier never counts as passed, and `score` lists it under skipped gates. Fix the network or key; do not hide it |
| `OLLAMA_API_KEY is not set` | The cloud runtime has no key | Add the secret (step 4) |
| Agentic cases fail with schema errors on Ollama Cloud | Cloud has no structured outputs, so the runtime asks for JSON in the prompt and repairs at most twice | Inspect the case's `benchmark-result` notes. Persistent failures are real findings about the skill or the model |
| `CassetteMiss` in replay | The request was never recorded live | Record it with a live run (`--jev live --record ...`). Replay never invents answers |

Related: [live-benchmarks.md](live-benchmarks.md) (full benchmark runbook),
[zed-ollama-setup.md](zed-ollama-setup.md) (editor setup), ADR-0007 (Jev as grader).
