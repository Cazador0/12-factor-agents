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

## Develop

```bash
uv sync --project packages/sdd-harness
uv run --project packages/sdd-harness pytest -q
uv run --project packages/sdd-harness ruff check src tests && uv run --project packages/sdd-harness ruff format --check src tests
```
