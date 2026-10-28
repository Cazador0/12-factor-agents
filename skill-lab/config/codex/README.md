# Codex configuration

[`config.example.toml`](config.example.toml) is deliberately small. It holds a model, one Ollama
provider block taken from Ollama's Codex integration page, and an approval and sandbox mode. Any key
that cannot be traced to a source is left out rather than guessed.

## Skills in Codex

- **Discovery.** Codex scans `.agents/skills/` from the working directory up to the repository root,
  and follows symlinks ([SOURCES.md](../../docs/research/SOURCES.md#codex-and-claude-code-skills)).
  Zed uses the same folder, so one install serves both:

  ```sh
  python3 skill-lab/bin/skill-lab install --runtime codex     # .agents/skills/<name> -> ../../skills/<name>
  python3 skill-lab/bin/skill-lab install --runtime codex --check
  ```

- **Invocation.** Type `$name`, for example `$lead-architect`, `$pse-implementer` or
  `$review-verifier`. Codex also picks a skill on its own when your request matches the skill's
  description. Codex uses `$`, not `/`. Spec Kit commands follow the same rule (`$speckit-specify`).
- **Script paths.** A skill's commands are relative to its folder, so in Codex they resolve under
  `.agents/skills/<name>/`, for example `python3 .agents/skills/lead-architect/scripts/<script>.py`.
  Each skill's `## Runtime notes` section says the same.
- **Instructions.** Codex reads the root [`AGENTS.md`](../../../AGENTS.md) natively.

## Ollama with Codex

Ollama documents three ways to use Codex. All of them come from
`docs/integrations/codex.mdx` in the Ollama repository:

| Way | Command | Notes |
|---|---|---|
| Quick setup | `ollama launch codex` | Ollama writes a dedicated Codex profile and a model catalog. `/model` switches between tool-capable models. `ollama launch codex --config` configures without launching; `--restore` removes the profile |
| Manual | `codex --oss -m gpt-oss:120b-cloud` | `--oss` targets the local Ollama daemon. Cloud tags need `ollama signin` |
| Profile file | `~/.codex/ollama-launch.config.toml`, then `codex --profile ollama-launch` | The example's keys follow this file. Ollama's version also sets `model_catalog_json` to a file that `ollama launch codex` generates |

Ollama says to "use a context window of at least 64k tokens for Codex". On a GPU under 24 GB that
rules out most local models at useful speed, which is one more reason the example uses a cloud tag
(cloud first, [SPEC-200](../../specs/200-release-roadmap/spec.md)).

## Guardrails

- `approval_policy = "on-request"` and `sandbox_mode = "workspace-write"` keep commands inside the
  workspace and ask before anything leaves the sandbox. These are long-standing Codex keys, but they
  were not checked against the current Codex config reference for this file. Confirm them with
  `codex --help` (`--ask-for-approval`, `--sandbox`).
- No per-path deny rule for Codex has been verified (SPEC-201 decision D-23). Protection of
  `.skill-policy.json`, CI workflows, contracts and benchmark criteria therefore rests on the
  `AGENTS.md` "Never" rules, on `merge-policy-gate` classifying those paths as critical, and on Gitea
  branch protection.
- The sandbox may block network access for `git push` and Gitea calls. Skill scripts then exit 3
  (external failure) and say so. Nothing is skipped silently.

## The lab's Codex runtime

`skill-lab bench --runtime codex-cli` (alias `codex`) runs agentic cases through
`codex exec --json --sandbox read-only` when `codex` is on `PATH`, and otherwise reports them
`skipped`. See the [benchmarks README](../../benchmarks/README.md).
