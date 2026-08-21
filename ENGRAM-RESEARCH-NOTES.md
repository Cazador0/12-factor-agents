# Engram research notes — what this fork contributed

This repository was read as a **research input** for building *Engram*, a
local-first agentic application with OS-inspired tiered memory. Nothing here was
modified: that research phase was explicitly read-only, and this file is the only
change on this branch.

The application lives in `Cazador0/mem0` at `examples/engram/`, branch
`claude/agentic-framework-research-7yr94s`. Full architecture:
`examples/engram/docs/HANDOFF-SPEC.md`.

This repo contributed **the shape of the agent loop itself** — more of Engram's
control flow comes from here than from any other source.

## What was harvested, and where it landed

| Pattern found here | Source read | Where it is in Engram |
|---|---|---|
| **Thread as an append-only event log** unifying business and execution state; status *derived* from the log tail, never stored | `workshops/2025-05/final/src/agent.ts`, `content/factor-05-unify-execution-state.md` | `src/agent/thread.ts` — `deriveStatus`/`awaitingApproval`/`awaitingHumanResponse`/`isSleeping` all read the tail. `threads.status_hint` exists but is a display cache only, and the constitution forbids treating it as authoritative |
| **Two-switch split**: a policy switch that decides continue/pause/approve, and a pure executor that only runs an already-recorded call | `final/src/agent.ts`, `content/factor-08-own-your-control-flow.md` | `routeIntent()` in `src/agent/intents.ts` (sync/gated/break/terminal) vs `executeStep()` in `src/agent/execute.ts`. This split is what makes approval replay possible at all |
| **Tools are structured outputs; humans are just another intent** — `request_more_information` and `done_for_now` sit in the same union as real tools | `final/baml_src/agent.baml`, `content/factor-04-tools-are-structured-outputs.md` | `src/agent/intents.ts` — one Zod discriminated union where `request_human_input`, `needs_clarification`, `sleep_until` and `complete_task` are peers of `archival_search` and `memory_update` |
| **Own your context window** — custom XML-ish single-message serialization, tag chosen from `data.intent`; stored form decoupled from prompted form | `final/src/agent.ts`, `content/factor-03-own-your-context-window.md` | `src/agent/render.ts`, the single seam that decides what the model sees. Compaction, redaction, error-hiding and memory injection all happen there, read-side only — the canonical log is never mutated by rendering |
| **Pre-fetch deterministic context** (appendix 13): run predictable tools *before* the call and inject the results, instead of spending a turn on a fetch tool | `content/appendix-13-pre-fetch.md` | `src/memory/prefetch.ts` — archival recall is injected at loop entry. Deliberate divergence: pre-fetched memories carry **no** integer refs, so the ref map stays derivable from the log alone |
| **Compact errors into context, with a consecutive-error budget** — tool failures become error events the model can self-heal from; escalate to a human at ~3 | `content/factor-09-compact-errors.md` | `compactError()` in `src/agent/render.ts`, `consecutiveErrors()` in `src/agent/thread.ts`, `escalateIfStuck()` in `src/agent/loop.ts`. Engram's version skips background annotations so a concurrent extraction cannot reset the count |
| **Small, focused agents** with a bounded step budget | `content/factor-10-small-focused-agents.md` | `maxSteps` per agent, counted **per turn** rather than per lifetime — a lifetime count permanently bricks a long-lived thread. Turn boundaries are documented as a spec rule because every new channel must honor them |
| **Launch/pause/resume by id from any channel** | `final/src/server.ts`, `content/factor-06-launch-pause-resume.md` | `src/server/routes.ts` (HTTP) and `src/channels/cli-turn.ts` (CLI) drive the identical thread machinery; resume payloads are validated against the thread's *derived* status |
| **Prompt-as-code with fixture assertions** — serialized threads are the test fixtures, `@@assert` pins the chosen intent at each stage | `final/baml_src/agent.baml`, `sections/04-baml-tests/README.md` | The model for Engram's prompt-eval harness: fixture threads serialized exactly as `render.ts` does, with recorded replies so it runs in CI without an API key |

## Divergences worth recording

- **Resume is a synchronous REST endpoint, not a webhook.** The workshop's
  `/webhook` handler is an unfinished stub (`sections/12-humanlayer-webhook/`),
  and the finished path in `final/src/server.ts:83` is the synchronous one.
  Engram implements the latter and does not pretend to the former.
- **`via_human` instead of transport state.** The workshop carries
  `{state:{thread_id}}` in the callback so the resume needs no correlation
  table. Engram keeps everything in the log instead and marks human decisions
  with a `via_human` flag on the appended `tool_response`, which both channels
  set identically — so approval chains reset the step budget the same way
  regardless of transport.
- **Factor 12 (stateless reducer) is honored literally**: `agentLoop(threadId,
  deps) -> Thread`. Everything needed to resume is in SQLite; nothing lives in
  process memory between turns.

## Reading the result

Memory tiering, extraction and hybrid scoring come from mem0; the storage
substrate from bun; the constitution/gates from spec-kit; subagent summary
discipline from BMAD-METHOD. `HANDOFF-SPEC.md` §2 attributes every pattern.
