# sdd-harness

The engines behind three Claude Code skills for Spec-Driven Development, built on LangGraph, LangChain
runnables and a hybrid RAG layer with provenance.

| Skill | Built from | Engine | CLI |
|---|---|---|---|
| `sdd-intake-engine` | `speckit-intake-start` | `sdd_harness.intake` | `sdd-intake` (`bin/sdd intake`) |
| `sdd-skill-router` | `speckit-intake-route` | `sdd_harness.router` | `sdd-route` (`bin/sdd route`, `bin/intakespec`) |
| `sdd-decision-ledger` | `speckit-intake-refine` | `sdd_harness.ledger` | `sdd-refine` (`bin/sdd refine`) |

```
                 ┌──────────────────────── sdd_harness ────────────────────────┐
 Claude Code     │  intake/  LangGraph: ground → draft → plan_round ⇄ ask ⇄ record → finish
 skill  ──CLI──► │  router/  LangGraph: gate → retrieve → rank → explain
 (host model     │  ledger/  LangGraph: build_ledger → plan_round ⇄ ask ⇄ apply → finish
  writes the     │      │                     │                      │
  questions)     │      ▼                     ▼                      ▼
                 │  rag/        BM25 + dense vectors (RRF), structural chunks, provenance, staleness
                 │  reasoning/  DecisionTrace (durable) · VisibleReasoning (reviewable) · checkpoints
                 │  llm.py      Claude via the anthropic SDK as LangChain runnables (service mode)
                 └─────────────────────────────────────────────────────────────┘
                       ▲ files in git are the memory: intake.md, spec.md, ledger sidecars, traces
```

## Two modes

- **Inside Claude Code** (default): engines are deterministic. The host model drafts and sharpens the
  questions; the engines keep the files, the rules, the round order and the records consistent.
- **LangGraph service**: with `ANTHROPIC_API_KEY` (or `SDD_LLM=on`), Claude-backed nodes run. They draft
  intakes, pick among router candidates, and give grounded second opinions on borderline ledger verdicts.
  Calls use `claude-opus-5-5`, adaptive thinking, an explicit effort setting (`llm.effort`), structured
  outputs (`client.beta.messages.parse`), and the server-side refusal fallback (`fallbacks: "default"`).
  `SDD_LLM=off` forces deterministic mode.

## Retrieval

`rag/` indexes the repository on structural boundaries: Markdown headings, spec requirements, success
criteria and user stories, single tasks, skill cards and Python symbols. Every chunk carries provenance
(repo, commit SHA, path, heading, symbol, spec id, file hash). Search fuses BM25 with dense vectors by
reciprocal rank, filters by metadata, applies small explainable rerank boosts, and **rejects stale
chunks**: those whose commit is not an ancestor of HEAD, or whose file changed since indexing. Dense
embeddings default to offline feature hashing; set `retrieval.embeddings` to `fastembed` or `voyage`
(extras) for model embeddings.

```bash
bin/sdd index build
bin/sdd index query 'how are leases recovered' --spec SPEC-001 -k 5
```

## Reasoning

- **Decision traces** (`reasoning/trace.py`), the durable record: decision, rationale summary,
  evidence, assumptions, tool results, changed state, unresolved questions, next action. Append-only
  JSONL per run, plus session checkpoints (YAML) for handoff.
- **Visible reasoning chains** (`reasoning/chain.py`), reviewable artifacts that never authorize
  anything: numbered observation, inference, check and conclusion steps with citations. A grounding
  check flags any step whose citation matches no retrieved source. Deterministic engines narrate
  their rules through `ReasoningRecorder`; `reasoning_chain()` is the LCEL version for service mode.

Hidden model reasoning is never stored (Constitution Art. IX).

## Jev, the progress watchdog (spec 008)

`jev/` scans every supervised session every 10 minutes. Plain code decides its health: `decide()` is pure,
taking evidence and scan history and returning a verdict.

**Signals**

| Signal | When it fires |
|---|---|
| Dead | The lease heartbeat is older than its TTL. Jev tells the Lead at once. |
| Hung | 20 minutes of loop silence. Paused while a tool call is still inside its own timeout, while the session waits on a person, and during start-up grace. |
| Spinning | 60 minutes without durable progress. |
| Loop fingerprints | From the command log: an action-error pair repeated 3 times warns and 4 times is stuck; an action-observation pair repeated 4 times; a 6-step alternation; 3 command timeouts in a row. |
| CI not converging | 3 completed, non-cancelled failing runs. |

**From bad scans to escalation**

- One bad scan warns and nudges the session; two in a row mean the session is stuck.
- A scan Jev could not observe (for example, Gitea is unreachable) changes nothing.
- A stuck session goes up a ladder:
  1. Jev asks the session to stop.
  2. After one scan of grace, the Lead stops it.
  3. Jev pages a person if the Lead stays silent, or if the episode is still unresolved after three scans.
  4. After two restarts, Jev parks the session.

**What Jev may and may not do**

- Jev only comments and labels. It never edits code, pushes, approves or merges.
- It refuses to run if its token can push or merge.
- Each episode gets one living comment. Jev finds it by a hidden marker and edits it in place, and an intent record keeps this safe across crashes.
- Each episode gets one exclusive label, added by ID: `jev/warning`, `jev/stuck` or `jev/parked`.

**Messages and explanations**

- Messages follow the strict, frozen `JevMessage` model, which is exported to `schemas/jev-message.v1.json`. CI fails when the export is stale.
- Explanations written by a model (`--explain claude|ollama`) describe a verdict; they never decide it.
- The command log comes from `.claude/hooks/command_log.py`, which writes one JSON line per tool call to `.specify/sessions/commands/`. It stores output hashes, never output text.

```bash
sdd-jev scan --sessions sessions.json --dry-run   # decide and record locally; write nothing to Gitea
sdd-jev scan --sessions sessions.json             # token from $JEV_GITEA_TOKEN, URL from $JEV_GITEA_URL
sdd-jev history pse-184
sdd-jev schema --check
```

## Develop

```bash
uv sync --project packages/sdd-harness
uv run --project packages/sdd-harness pytest -q
uv run --project packages/sdd-harness ruff check src tests && uv run --project packages/sdd-harness ruff format --check src tests
```
