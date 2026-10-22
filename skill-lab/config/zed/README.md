# Zed Agent configuration

[`settings.example.jsonc`](settings.example.jsonc) configures the Zed Agent for this repository's
skills. It sets up the Ollama provider, the three role profiles from
[CONVENTIONS §7](../../docs/CONVENTIONS.md#7-roles-and-authority-zed-profiles), and the tool-permission
guardrails that apply to every role. The step-by-step setup is in the
[Zed + Ollama runbook](../../docs/runbooks/zed-ollama-setup.md).

These settings are guardrails, not a security boundary. The boundary is Gitea branch protection
plus the deterministic gates: CI, `review-verifier`, and `merge-policy-gate`.

## Install

1. Open your user settings file (command palette: `zed: open settings file`).
2. Merge the `language_models` and `agent` keys from the example. If you already have `agent.profiles`
   or `agent.tool_permissions`, merge the entries instead of replacing the whole object.
3. Zed applies settings when you save. If Zed reports an unknown provider, choose the model once in
   the Agent Panel model selector, because that writes the exact `agent.default_model` Zed expects.

The file is JSONC: comments are allowed and trailing commas are not. The lab's test strips the
comments and parses the rest as strict JSON.

## Ollama: one provider, two patterns

Zed has one Ollama provider (`language_models.ollama`) with one `api_url`. There are two ways to
use it:

| Pattern | `api_url` | Auth | Reaches | Model names |
|---|---|---|---|---|
| **(a) Signed-in local daemon** (recommended, used in the example) | `http://localhost:11434` | `ollama signin` once. The local API needs no key | Local models **and** cloud models, at the same time | Local tags (`gpt-oss:20b`) and cloud tags (`gpt-oss:120b-cloud`, `gemma4:cloud`) |
| **(b) Direct cloud** | `https://ollama.com` | `OLLAMA_API_KEY`, or the key entered in the provider UI | Cloud models only | Names from `https://ollama.com/api/tags`, for example `gemma4:31b` |

Pattern (a) is the only way to have local and cloud inference in Zed at the same time. Ollama's
authentication docs (`api/authentication.mdx`, "Signing in") show that after `ollama signin`,
`ollama run gpt-oss:120b-cloud` works, and that "this also works through the local API", with
`curl http://localhost:11434/api/generate -d '{"model": "gpt-oss:120b-cloud", ...}'`. The cloud docs
add: "In the Ollama app or CLI, use `gemma4:cloud`", and the OpenAI-compatibility docs add: "Through a
signed-in local server, select a cloud model such as `gemma4:cloud`". Zed only ever talks to
`localhost`, and the daemon forwards cloud tags to ollama.com.

Pattern (b) is documented in Ollama's Zed integration page ("Connecting to ollama.com": set the API
URL to `https://ollama.com`) and in Zed's local-model page ("For remote Ollama services ... set the API
URL to the remote endpoint and provide an API key").

Ollama Cloud does not support structured outputs (`format`). That never affects a skill's results,
because the scripts produce the JSON. The lab's `ollama-cloud` benchmark runtime puts the schema in
the prompt and validates the reply instead.

## Models and context

- **Cloud first** ([SPEC-200](../../specs/200-release-roadmap/spec.md), inference step C1): every
  profile defaults to a cloud model. Local models are listed so you can try them by hand, but they
  become profile defaults only after the L1 gate (3 consecutive passing cloud benchmark runs plus your
  sign-off, SPEC-202).
- `context_window: 32768` is sent as `num_ctx`. Zed's default is 4096, and with that a skill's
  procedure falls out of context. 32768 fits a GPU under 24 GB (ADR-0003). Per-model `max_tokens`
  overrides it.
- `supports_tools` is `true` only for models that can call tools. Ollama's tool-calling docs use
  `qwen3`, and its Codex integration runs `gpt-oss:120b` and `gpt-oss:120b-cloud`, which require tool
  calls. Without tools a model cannot load skills, so `gemma4` stays `false` until
  `ollama show gemma4` lists `tools`.
- The names are examples. Run `ollama list`, `ollama show <model>` and, while a model is loaded,
  `ollama ps` (look for `100% GPU` and the `CONTEXT` column).

## Profiles

Profiles decide which tools exist in a thread. The tool sets are fixed by
[ADR-0008](../../docs/adr/0008-role-authority-guardrails.md). Each profile lists all 16 built-in
tools explicitly, so none of them depends on Zed's default for an unlisted tool.

| Tool | Lead | PSE | Review |
|---|---|---|---|
| `read_file`, `grep`, `find_path`, `list_directory`, `diagnostics` | yes | yes | yes |
| `terminal`, `skill` | yes | yes | yes |
| `edit_file`, `write_file`, `create_directory`, `delete_path`, `move_path`, `copy_path` | yes | yes | **no** |
| `spawn_agent` | yes | **no** | yes |
| `fetch`, `search_web` | no | no | no |

- **Lead** edits specs, docs, `AGENTS.md`, and issue contracts. It uses `lead-architect`,
  `speckit-gitea-taskstoissues`, `speckit-gitea-sync`, `kanban-state-machine`, `merge-policy-gate`, and
  `session-checkpoint`.
- **PSE** writes production code and tests on its own leased branch. It uses `pse-implementer`,
  `work-lease`, and `session-checkpoint`.
- **Review** reads, runs checks, and runs skill scripts. It uses `review-verifier`,
  `merge-policy-gate` (read), and `twelve-factor-audit`.
- `fetch` and `search_web` are off: skills work offline, and fetched pages are untrusted text. Turn
  `fetch` on for one profile only if you need it.
- A subagent (`spawn_agent`) gets the same tools as its parent thread. For PSE that would be a
  second writer on the leased branch, so PSE has none. Lead and Review use subagents for read-heavy
  investigation.

### Review and test code

CONVENTIONS §7 allows Review to edit test and eval code only. Zed cannot express that rule:

- A profile switches a tool on or off for **every** path.
- `agent.tool_permissions` is **global**. It has no per-profile section, so a path rule written for
  Review would also bind Lead and PSE.

The example therefore gives Review no file-editing tools at all (ADR-0008). Test and eval code that
Review authors is written in a separate session on a test-only branch, `agent/review/<issue>-<slug>`.
A missing test that blocks approval goes into the `review-verdict` as a blocker, and PSE writes it.
`terminal` stays on for Review because it must run tests, which means a shell could still write files.
That is one reason these settings are guardrails and not a boundary.

## Tool permissions (global)

Precedence, from highest: Zed's built-in rules, then `always_deny`, `always_confirm`, `always_allow`,
the tool's `default`, and finally the global `default`. Patterns are Rust regexes, matched
case-insensitively. Every default is `confirm`. The deny and confirm lists still apply if you loosen
a default to `allow`.

The lists follow ADR-0008. A path that defines an agent's authority is never writable by an agent,
so it is denied. Contracts, gates, templates and conventions may change, but only in a PR that a human
merges, so editing them asks first.

| Tool | Allowed without asking | Always asks | Always denied |
|---|---|---|---|
| `skill` | the 13 catalog skills under any worktree's `.agents/skills/` | other skills (the default) | none |
| `terminal` | read-only git; `python3 [<checkout>/].agents/skills/<catalog skill>/scripts/<x>.py`; `skill-lab validate`, `test`, `bench`, `doctor`, `score`, and `catalog`/`sync`/`install --check`; `python3 -m unittest` | `--apply`; `git push`/`commit`/`merge`/`rebase`/`reset`/`clean`/`restore`/`tag`/`worktree`; `git branch -d`; `sh -c`; `sudo`; `curl`, `wget`, `gh`, `tea`; package installs | force pushes (`-f`, `--force*`, `+refspec`); pushes to `main`/`master`; `--no-verify`; recursive `rm`; `curl`/`wget` piped to a shell, and a bare `sh`/`bash` reading stdin; any command naming `.skill-policy.json` |
| `edit_file`, `write_file`, `delete_path`, `move_path`, `copy_path` | none | `skill-lab/contracts/`, `skill-lab/benchmarks/criteria/`, `skill-lab/config/`, `skill-lab/shared/_skillkit/`, `CONVENTIONS.md`, `AGENTS.md`, `CLAUDE.md`, `skills/*/SKILL.md`, `.agents/`, `.claude/`, `.codex/` | paths that define an agent's authority: `.skill-policy.json`, `.skill-gitea.json`, `.github/workflows/`, `.gitea/workflows/`, `.claude/settings.json`, `.claude/settings.local.json`, `.zed/settings.json`, `CODEOWNERS`; vendored `skills/*/scripts/_skillkit/` and `skills/*/assets/schemas/`; generated `skills/CATALOG.json`; `.env*`; `*.pem`, `*.key`; `.git/` |

Notes:

- **Skill paths.** Zed matches the `skill` rule against the absolute path of `SKILL.md` as it was
  discovered, which here is `<checkout>/.agents/skills/<name>/SKILL.md`. That path goes through the
  symlink `skill-lab install` creates. The pattern matches that path in any worktree, including
  linked git worktrees. To limit it to this checkout, prefix it with `^<your checkout path>`. Only
  model-invoked skills prompt; typing `/lead-architect` yourself does not.
- **Skill scripts** are read-only unless they get `--apply` (CONVENTIONS §3), and `--apply` always asks.
  The allow rule refuses path segments that start with `.`, so `../` cannot point it outside the
  checkout. Scripts invoked as `cd <skill> && python3 scripts/x.py` prompt, because the `cd` part has
  no allow rule.
- **Chained commands.** Zed checks each sub-command of a chain separately. That is why the
  bare-shell rule exists: in `curl ... | sh`, the `sh` part is denied on its own.
- **Bypasses.** Argument patterns are best effort. For example, `git -c alias.x=push x` or a script
  that runs git itself is not caught. Gitea branch protection (no direct or force pushes to `main`) is
  the rule that actually holds.
- **Skill files.** Zed already refuses to let the agent edit `SKILL.md` and bundled skill files without
  your explicit authorization. The confirm rules cover the canonical `skills/<name>/` paths that the
  `.agents/skills` symlinks point to.

## Not verified here

Check these against your Zed build:

- The provider id `ollama` in `default_model`. The model selector writes the exact value (see Install).
- Whether Zed's Ollama provider honours `max_tokens` for `-cloud` tags. Cloud models run at their
  maximum context in any case.
- Whether a project-level `.zed/settings.json` may carry `agent` settings. The example assumes user
  settings only.
- There is no MCP server yet. Gitea is a test double, so `context_servers` is empty and
  `enable_all_context_servers` is `false` in every profile.
