# Set up the Zed Agent with Ollama

From a fresh machine to `/lead-architect` running in Zed, using one Ollama daemon for both local and
cloud models. Expect about 20 minutes, most of it model downloads. The configuration is explained in
[skill-lab/config/zed/README.md](../../config/zed/README.md).

## 1. Install and start Ollama

Download Ollama from https://ollama.com/download. On macOS, open the app. On Linux, or from a shell:

```sh
ollama serve
```

The local API at `http://localhost:11434` needs no key.

## 2. Sign in for cloud models

```sh
ollama signin
curl http://localhost:11434/api/generate -d '{"model": "gpt-oss:120b-cloud", "prompt": "Say hi", "stream": false}'
```

After `ollama signin`, the local daemon serves cloud tags (`...-cloud`, `...:cloud`) through the same
local API (Ollama docs: `api/authentication.mdx`). That is how Zed reaches local and cloud models at
the same time through one provider. Cloud first ([SPEC-200](../../specs/200-release-roadmap/spec.md)):
the example profiles all default to `gpt-oss:120b-cloud`.

## 3. Pull a local model (optional for now)

Local models become profile defaults only after the L1 gate (SPEC-202). To try one by hand:

```sh
ollama pull gpt-oss:20b
ollama show gpt-oss:20b      # "tools" must appear under Capabilities
ollama ps                    # while loaded: PROCESSOR should read "100% GPU"
```

## 4. Context length

Zed sends `num_ctx` with every Ollama request, and its default is **4096**, which is too small: the
skill's procedure and tool output no longer fit. The example sets `context_window: 32768` (ADR-0003),
which suits a GPU under 24 GB. Because Zed sends `num_ctx`, Ollama's own default (4k below 24 GiB of
VRAM) does not apply to Zed. For other clients, raise it with `OLLAMA_CONTEXT_LENGTH=32768 ollama serve`
or the slider in the Ollama app. Cloud models always run at their maximum context.

## 5. Open the repository in Zed and trust it

Install Zed from https://zed.dev/download, then open the repository folder. Project-local skills load
only from a **trusted** worktree. Accept the trust prompt, or the catalog and the `/` commands stay
empty.

## 6. Install the skills

```sh
python3 skill-lab/bin/skill-lab install            # relative symlinks in .agents/skills/ and .claude/skills/
python3 skill-lab/bin/skill-lab install --check    # exit 1 if any link is missing or stale
```

Zed discovers `<worktree>/.agents/skills/<name>/SKILL.md`, one level deep, and follows the symlinks.
Edits to `SKILL.md` take effect without a restart.

## 7. Merge the settings

Open your user settings (`zed: open settings file`) and merge the `language_models` and `agent` keys
from [settings.example.jsonc](../../config/zed/settings.example.jsonc). If you prefer the UI, open the
Agent Panel, go to **Configure → LLM Providers → Ollama**, confirm the Host URL `http://localhost:11434`,
and select **Connect**. You still need the settings file for the profiles and tool permissions.

## 8. Pick a profile and invoke a skill

1. In the Agent Panel, open the profile selector and choose **Lead**, **PSE** or **Review**. Each
   profile's `default_model` is applied, and only its tools are available.
2. Type `/` and choose a skill, for example `/lead-architect`, `/pse-implementer` or
   `/review-verifier`. You can also type `@skill`. A skill you invoke yourself never prompts. When the
   model loads a skill on its own, Zed asks for permission unless the skill's path matches
   `agent.tool_permissions.tools.skill.always_allow`.
3. Give each role its own thread. If two threads might edit the same files, start one in its own git
   worktree from the worktree picker in the title bar, on an `agent/<role>/<issue>-<slug>` branch.
4. Before you stop or switch roles, ask for a session checkpoint (`/session-checkpoint`). The next
   session resumes from it.

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| No skills in the `/` menu | The worktree is not trusted, a link is broken, or a skill is nested one level too deep | Trust the worktree; run `skill-lab install --check`; skills must be direct children of `.agents/skills/` |
| Zed warns that skills were dropped from the catalog | All names and descriptions together exceed 50 KB, and Zed drops the skills that do not fit | `python3 skill-lab/bin/skill-lab catalog --check --pretty` reports `catalog_bytes` against `limit` (the lab warns from 40 KB). Shorten descriptions. Global skills in `~/.agents/skills/` count toward the same budget |
| A permission prompt every time the model loads a catalog skill | The `skill` allow pattern does not match the path shown in the prompt | Compare the absolute `SKILL.md` path in the prompt with the pattern. A copy install, or a path outside `.agents/skills/`, will not match |
| The model forgets the skill midway, repeats steps, cuts JSON short, or the thread compacts after a few turns | `num_ctx` is too small: the 4096 default, or `max_tokens` missing for the model | Set `context_window: 32768` and per-model `max_tokens`. `ollama ps` shows `CONTEXT` 32768 while the model is loaded |
| The model answers in prose and never calls `skill` or `terminal` | The model has no tool support, or `supports_tools` is `false` | `ollama show <model>` must list `tools`. Pick a tool-capable model |
| Very slow turns, `ollama ps` shows a CPU/GPU split | The model and context do not fit in VRAM | Use a smaller model, or a cloud tag |
| A cloud tag fails, or the daemon says to sign in | The daemon is not signed in | Run `ollama signin`, then repeat the curl from step 2 |
| A cloud model is missing from Zed's model list | Auto-discovery lists only what the daemon reports | Keep the model in `available_models`, as the example does |
| JSON-schema requests fail on `https://ollama.com` | Ollama Cloud does not support structured outputs | Expected. Skills get their JSON from scripts; only local Ollama accepts `format` |
