# ADR-0003: Ollama inference for Zed, a 32k context budget, and no dependence on structured outputs

## Status

Accepted. SPEC-200 sequences the two Ollama modes (cloud first, local after a measured gate). The
sequencing details are planned for ADR-0103 (SPEC-201 task T005) and ADR-0203 (SPEC-202).

## Date

2026-10-22

## Context

The priority runtime is the Zed Agent on Ollama, in two modes
([SOURCES.md, Ollama with Zed](../research/SOURCES.md#ollama-with-zed); Ollama `context-length.mdx`,
`cloud.mdx`, `structured-outputs.mdx`; Zed `use-a-local-model.md`):

- **Local**: a GPU with **less than 24 GB** of VRAM. Ollama defaults to a 4k context below 24 GiB,
  32k at 24–48 GiB and 256k at 48 GiB or more. It recommends at least 64,000 tokens for agents and
  coding tools, and warns that a larger context needs more memory. Zed sends the context length to
  Ollama as `num_ctx` and **defaults it to 4096** unless `context_window` (all models) or a model's
  `max_tokens` in `available_models` says otherwise. Local `/api/chat` accepts `format`, either
  `"json"` or a JSON Schema object.
- **Cloud**, reachable two ways. Directly: `https://ollama.com/api/*` with
  `Authorization: Bearer $OLLAMA_API_KEY`, using the model names `GET https://ollama.com/api/tags`
  returns. Or through a local daemon signed in once with `ollama signin`: it then authenticates cloud
  requests itself, and cloud models (tags such as `gpt-oss:120b-cloud`) work through the local API
  at `http://localhost:11434` (Ollama `api/authentication.mdx`). Cloud models run at their maximum
  context. **Ollama Cloud does not support structured outputs.** Prompts and responses are processed
  by Ollama, which states that it does not train on them.

Zed has one Ollama provider with one `api_url` (SPEC-202 synthesis F-20). Pointing it at a signed-in
local daemon is therefore the only way to reach local and cloud models from one Zed settings file.
Pointing it at `https://ollama.com` reaches cloud models only. A skill also has no way to set
`format` on the Zed agent's own model calls: neither SOURCES.md nor Zed's settings docs list such an
option. Inside Zed, every configuration therefore behaves as "no structured outputs" for the agent
loop.

The user decided "everything cloud first; local enabled second after cloud is reliable and
aligned to user intent" (SPEC-200, inference track C1 then L1).

## Decision

### Inference modes

1. **Ollama Cloud is the default for every Zed profile in R1** (Lead, PSE, Review; one model, so
   runs stay comparable, SPEC-201 synthesis D-14). The steady-state target after L1 is: cloud
   models for Lead and Review, whose planning and independent verification need the strongest
   model and long context; local models for PSE's script-driven step loops. That split is a
   target. It must be confirmed by benchmark data per role before any profile defaults change.
2. **Zed connects through a signed-in local daemon when one is available**: `api_url`
   `http://localhost:11434`, cloud models by their `-cloud` tags, and local models listed beside
   them. Machines without the Ollama app use `api_url` `https://ollama.com` with `OLLAMA_API_KEY`,
   which reaches cloud models only. The lab's `ollama-cloud` benchmark runtime always calls
   `https://ollama.com` directly with the key, so its results do not depend on a local daemon. Either
   way, cloud models are treated as having no structured outputs.
3. **Local models are not profile defaults** until SPEC-202's L1 gate passes: the same suite on
   `ollama-local` in cloud-parity mode, 3 consecutive runs. SPEC-201 FR-039 additionally keeps a
   separate local template disabled (planned: `skill-lab install --inference local` will exit 4
   `LOCAL_INFERENCE_GATED`).
4. **Local context is 32,768 tokens**, set explicitly in Zed (`max_tokens: 32768` per model, or
   `context_window`) and in the lab's `ollama-local` runtime (`DEFAULT_NUM_CTX`). The model is
   chosen to fit that context, not the context shrunk to fit the model: a local model qualifies
   only if it supports tool calls (`supports_tools: true`) and `ollama ps` shows it loaded with
   `CONTEXT 32768` and `PROCESSOR 100% GPU`. 64k is not the default because on this GPU class we
   expect it to leave room only for a much smaller model, or to force CPU offload. That is an
   inference from Ollama's own VRAM-tier defaults (32k is its default only from 24 GiB up), not a
   measurement, and `ollama ps` settles it for a given model. A user with more VRAM may raise the
   value; nothing in the skills depends on less.
5. **Model choice is configuration, never code.** Skills never name a model. Local candidates are
   verified with `ollama list` and `ollama ps`. Cloud candidates are verified with
   `curl https://ollama.com/api/tags` and recorded with the check date in
   `skill-lab/config/zed/cloud-models.json` (SPEC-201 T112). Bench takes `--model`, and a runtime
   reports `available() == False` with a reason when the model is not listed.

### Context budget for skills

6. **`SKILL.md` body at most 250 lines and 12 KB; each reference at most 300 lines.** This is a
   design allocation of the 32,768-token window, estimated at about 4 bytes per token for English
   Markdown. Tokenizers differ, so the lab measures the real numbers (Compliance).

   | Slot | Enforced limit | Approx. tokens |
   |---|---|---|
   | Catalog: name and description of our 13 skills | 1024 chars each (error), 350–900 target | 3,000–3,400 |
   | One `SKILL.md` body after loading | 250 lines, 12 KB | ~3,000 |
   | One reference file read on demand | 300 lines (warning) | 3,000–4,500 |
   | **Skill text subtotal** | | **9,000–11,000 (about 30 %)** |
   | Zed system prompt and tool schemas, user turns, script envelopes, model output | | the remaining ~22,000 |

   Zed's own guidance (500 lines) would roughly double the body's share and leave less room for
   the tool results a multi-step procedure accumulates.
7. **Procedures fit small models**: numbered steps, one tool call per step, each naming one script
   whose envelope is compact JSON by default (CONVENTIONS §2). No step relies on parallel tool calls
   or on the model carrying long intermediate state. `session-checkpoint` caps its lists so a
   handoff stays small.

### Structured output strategy

8. **No skill depends on structured outputs** (SPEC-201 synthesis D-15). Deterministic scripts
   produce every contract document. The model chooses the next step, relays the envelope and
   branches on `ok` and `errors[].code`.
9. **When a model must author JSON** (agentic benchmark cases, or a draft that a script then
   validates), the contract goes into the prompt, and the reply is parsed leniently: strict, inside
   a Markdown fence, or embedded in prose, with the mode recorded as `json_extraction`. It is then
   validated with `_skillkit.jsonschema_mini`. An invalid reply gets **at most 2 repair turns**,
   each quoting **at most 8 compact validation errors** (12-factor Factor 9). This is the
   `ollama-cloud` runtime's loop. Skills that ask the model for a draft use the same rule: run the
   validating script, read its compact errors, fix, and stop after two attempts.
10. **Local `format` is an optimisation, not a dependency.** The lab's `ollama-local` runtime sends
   `format` set to the output schema, and still puts the schema in the prompt. Gate runs for L1 use
   a cloud-parity mode (no `format`, same repair loop), so local models are not graded on easier
   terms than cloud ones (SPEC-202 synthesis D-17). The runtime does not offer that mode yet;
   SPEC-202 adds it.

## Consequences

### Positive

- Skills behave the same on cloud, local, Claude Code and Codex, because the JSON comes from code.
- A ~32k local model can follow every procedure. The budget is explicit, enforced and measurable.
- Cloud-first gets real capability data before anyone tunes for weaker local models.

### Negative

- Agentic JSON validity is a measured risk, not a guarantee (SPEC-201 RK-3). Repair turns cost
  latency and tokens.
- 250 lines and 12 KB force detail into `references/` and scripts. Some procedures need an extra
  tool call to read a reference.
- Cloud inference sends code, specs and issue text to a third party. Private projects must accept
  that or stay local after L1.
- One model for all roles in R1 gives up per-role specialisation until data justifies it.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| The 4-bytes-per-token estimate is wrong for the chosen model's tokenizer | Tokenizers differ | Bench records `tokens: in=… out=…` from Ollama's `prompt_eval_count` and `eval_count` on every agentic result; re-derive the budget from the first live run |
| Bench's agentic tier is a single turn without Zed's tool loop, so it under-counts real Zed context use | The emulation reproduces Zed's catalog and skill envelope, not its tool schemas or loop (SPEC-102 non-goals) | Treat bench token counts as a lower bound; T112 records a real Zed session's usage |
| Zed's single Ollama provider makes "local and cloud at once" awkward | One `api_url` per settings file | SPEC-202 V-5: a signed-in local daemon serving `:cloud` models, or Zed's OpenAI-compatible provider against `https://ollama.com/v1` |
| A cloud model is retired | Ollama retires cloud models with notice | `cloud-models.json` records ids and dates; L1 streaks are per model (SPEC-202 D-17) |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Rely on Ollama structured outputs (`format`) everywhere | Not available on Ollama Cloud, the R1 default, and not controllable from a skill inside Zed |
| Zed's default `num_ctx` of 4096 | Too small for a catalog plus one skill plus tool results; the procedure would be truncated |
| 64k local context, as Ollama recommends for agents | Does not fit a useful tool-capable model on a GPU under 24 GB without CPU offload |
| Zed's 500-line body guidance | Doubles the skill's share of a 32k window |
| Local first | User decision: cloud first, local only after measured reliability (SPEC-200) |
| Unbounded or long repair loops | They hide a skill that does not work and burn tokens; 2 repairs is enough to fix formatting slips |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| Body ≤ 250 lines and ≤ 12 KB | `body.too-many-lines`, `body.too-large`; `test_lab_core_validate.py::TestBodyRules::test_line_limit`, `test_lab_core_validate.py::TestBodyRules::test_byte_limit` | enforced |
| References ≤ 300 lines, contents table above 100 | `references.too-long`, `references.no-toc` (warnings); `test_lab_core_validate.py::TestReferenceRules::test_long_reference_without_toc_warns` | enforced |
| `ollama-local` sends `num_ctx` 32768, `format` and the schema | `test_runtimes_ollama.py::TestOllamaLocal::test_request_shape_with_schema`, `test_runtimes_ollama.py::TestOllamaLocal::test_custom_num_ctx_and_free_text` | enforced |
| `ollama-cloud` sends no `format` and no `num_ctx`, uses Bearer auth | `test_runtimes_ollama.py::TestOllamaCloud::test_no_format_no_num_ctx_and_bearer_auth` | enforced |
| Repairs bounded, with compact errors | `test_runtimes_ollama.py::TestOllamaCloud::test_repairs_are_bounded`, `test_runtimes_ollama.py::TestOllamaCloud::test_repair_loop_feeds_back_compact_errors` | enforced |
| A model that is not listed makes the runtime unavailable, never a pass | `test_runtimes_ollama.py::TestOllamaLocal::test_available_reasons`, `test_runtimes_ollama.py::TestOllamaCloud::test_available_needs_key_model_and_listing` | enforced |
| Cloud-parity mode for local gate runs (no `format`, same repair loop) | `ollama-local` option added by SPEC-202 (synthesis D-17) | planned (R2) |
| Zed template: signed-in local daemon, `context_window` 32768, local models at ≥ 32,768, every profile defaulting to a tool-capable cloud model | `test_configs.py::TestZedSettings::test_ollama_provider_uses_the_signed_in_local_daemon`, `test_configs.py::TestZedSettings::test_available_models_are_well_formed`, `test_configs.py::TestZedSettings::test_every_default_model_is_a_tool_capable_cloud_model` | written by the config builder in parallel with this ADR |
| Validator rule for runtime configs; local template not installable in R1 | `skill-lab validate --config zed` (G-OFF-09); `LOCAL_INFERENCE_GATED` (SPEC-201 FR-039) | planned (SPEC-201 T113–T115) |
| Budget holds on a real model | Agentic result notes `tokens: in=…`; L1 parity runs (SPEC-202 D-17) | not run (network to `ollama.com` blocked) |

**Revisit when** the user's GPU changes, Ollama Cloud gains structured outputs, Zed exposes
`format` or per-profile providers, or the first live run shows the budget estimate is off by more
than 25 %.

## References

- [SOURCES.md: Ollama with Zed](../research/SOURCES.md#ollama-with-zed)
- [SPEC-200 roadmap](../../specs/200-release-roadmap/spec.md) (inference track),
  [SPEC-201 R1](../../specs/201-release-shadow/spec.md) FR-039, FR-041 and §Runtime compatibility,
  [SPEC-202 synthesis](../../specs/202-release-agent-implementation/synthesis.md) D-17, D-18
- [SPEC-102 bench and runtimes](../../specs/102-bench-runtimes-graders/spec.md) FR-010, FR-011
- [CONVENTIONS §2 Body](../CONVENTIONS.md#2-skillmd-contract)
- 12-factor [Factor 3, own your context window](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-03-own-your-context-window.md),
  [Factor 9, compact errors](https://github.com/humanlayer/12-factor-agents/blob/main/content/factor-09-compact-errors.md)
