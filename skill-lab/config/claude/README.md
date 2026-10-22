# Claude Code configuration

[`settings.example.json`](settings.example.json) is a permissions template for Claude Code.
Claude Code settings files are strict JSON, and a `//` comment there is a settings error. That is why
all the explanations live in this file.

## Install the skills

```sh
python3 skill-lab/bin/skill-lab install --runtime claude          # .claude/skills/<name> -> ../../skills/<name>
python3 skill-lab/bin/skill-lab install --runtime claude --check  # exit 1 if a link is missing or stale
```

Claude Code loads project skills from `.claude/skills/<name>/SKILL.md`. It follows a symlinked folder
to its target and loads a skill only once, even when several locations point to it. Use `--global` to
install into `~/.claude/skills/` instead. Skills in the home folder do not load in cloud sessions.

## Use the settings

Copy the file to one of these locations, or merge it into the file that is already there:

| File | Who it applies to |
|---|---|
| `.claude/settings.json` | Everyone working in the repository (commit it) |
| `.claude/settings.local.json` | Only you. Claude Code keeps the file out of git when it creates it; if you create it by hand, add it to `.gitignore` yourself |

Start Claude Code at the repository root. Project rules that begin with `/` anchor at the session's
primary working directory, so `Edit(/AGENTS.md)` means the root `AGENTS.md`. When more than one
settings file sets `permissions.allow`, `ask`, or `deny`, Claude Code combines the lists.

## What the rules do

Rule semantics, from Claude Code's [permissions docs](https://code.claude.com/docs/en/permissions):
deny beats ask, and ask beats allow. `*` matches any text. `:*` at the very end means the same as a
trailing ` *`, which also matches the bare command. Compound commands (`&&`, `||`, `;`, `|`) are
split, so every part must be allowed on its own, while a deny or ask rule fires if any part matches.

| List | Rules | Why |
|---|---|---|
| allow | `Bash(python3 .claude/skills/*/scripts/*.py:*)` | Skill scripts are read-only without `--apply` (CONVENTIONS §3) |
| allow | `skill-lab validate`, `test`, `bench`, `doctor`, `score`, `catalog --check`, `sync --check`, `install --check`; `python3 -m unittest`; `git status`, `diff`, `log`, `show` | Checks that change nothing, or write only git-ignored output |
| allow | `Skill(<name>)` for each of the 13 catalog skills | Model-invoked catalog skills run without a prompt. Use `Skill(name *)` to cover calls with arguments |
| ask | `Bash(python3 .claude/skills/* --apply*)` | Every external mutation needs a human. The autonomy policy still decides (CONVENTIONS §8) |
| ask | `Bash(git push:*)`, `curl`, `wget`, `gh`, `tea` | Pushes, network clients and forge CLIs stay visible (ADR-0008) |
| ask | `Edit(...)` on `skill-lab/contracts/`, `skill-lab/benchmarks/criteria/`, `skill-lab/config/`, `skill-lab/shared/_skillkit/`, `CONVENTIONS.md`, `AGENTS.md`, `CLAUDE.md`, `skills/*/SKILL.md`, `.claude/`, `.agents/` | Contracts, gates, templates and conventions change only in a PR that a human merges |
| deny | force pushes (`--force*`, `-f`, `+refspec`), pushes to `main`/`master`, `--no-verify` | Agents never bypass branch protection or hooks |
| deny | `rm -rf`, `rm -fr`, `rm -r`, `rm -R`, `rm -Rf`, `rm --recursive` | No recursive deletes |
| deny | `Bash(sh)`, `Bash(bash)`, `sh -s`, `bash -s` | Blocks the shell half of `curl ... \| sh` |
| deny | `Edit` on `.skill-policy.json`, `.skill-gitea.json`, `.github/workflows/`, `.gitea/workflows/`, `.claude/settings.json`, `.claude/settings.local.json`, `.zed/settings.json`, `CODEOWNERS` | A path that defines an agent's authority is never writable by an agent (ADR-0008). Only a human sets the autonomy level (CONVENTIONS §8) |
| deny | `Edit` on vendored `skills/*/scripts/_skillkit/`, `skills/*/assets/schemas/`, generated `skills/CATALOG.json` | Regenerate them with `skill-lab sync` and `skill-lab catalog` |
| deny | `Read(./.env)`, `Read(./.env.*)` | Secrets come only from environment variables |

Notes:

- Path rules use `Edit(...)`, never `Write(...)`. Claude Code checks file permissions only against
  `Edit` and `Read` rules, and an `Edit` rule covers every built-in tool that edits files. A
  `Write(path)` rule is accepted but never consulted.
- Allow rules in a committed `.claude/settings.json` take effect only after you trust the folder.
  Deny and ask rules apply immediately.
- These are guardrails. Command patterns that try to constrain arguments are fragile: the docs note
  that `Bash(git push *)` does not match `git -C . push origin main`. Read and Edit rules do not stop
  a Python script that opens files itself. For OS-level enforcement, enable Claude Code's sandbox. The
  real boundary is Gitea branch protection and the merge gates.
- Claude Code may warn at startup about the wildcard in the first argument of
  `Bash(python3 .claude/skills/*/scripts/*.py:*)`. The rule still applies. List one rule per skill if
  you prefer.

## Invoke skills

- Type `/lead-architect`, `/pse-implementer`, `/review-verifier`, and so on at the start of a
  message. Claude also loads a skill on its own when your request matches its description.
- Skill commands are relative to the skill folder, which Claude Code resolves as
  `.claude/skills/<name>/`.
- Instructions: Claude Code v2.1.277 and later read the root [`AGENTS.md`](../../../AGENTS.md) when there
  is no `CLAUDE.md`. If you add a `CLAUDE.md`, it replaces `AGENTS.md`, so put `@AGENTS.md` in it to
  import the map.

## Back Claude Code with Ollama

From Ollama's Claude Code integration page (`docs/integrations/claude-code.mdx`):

```sh
ollama launch claude                                    # picks a local or cloud model through the local daemon
ollama launch claude --model gemma4:cloud --yes -- -p "how does this repository work?"
```

The page also documents a manual setup against the local daemon (`ANTHROPIC_BASE_URL=http://localhost:11434`,
`ANTHROPIC_AUTH_TOKEN=ollama`, `ANTHROPIC_API_KEY=""`), and direct cloud access
(`ANTHROPIC_BASE_URL=https://ollama.com`, `ANTHROPIC_AUTH_TOKEN="$OLLAMA_API_KEY"`). Choose a model that
supports tools, and give local models at least 64k of context. On a GPU under 24 GB that points to
cloud models (cloud first, [SPEC-200](../../specs/200-release-roadmap/spec.md)).

The lab's `claude-cli` benchmark runtime runs `claude -p --output-format json` when `claude` is on
`PATH`. See the [benchmarks README](../../benchmarks/README.md).
