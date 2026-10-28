# Verified sources and facts

Facts the skills and the lab depend on, each checked against a primary source on
2026-10-22. When a fact here changes upstream, update this file and the ADR that
cites it in the same commit.

## Zed Agent skills

Source: Zed docs `docs/src/ai/skills.md`, `tool-permissions.md`, `agent-profiles.md`,
`instructions.md`, `use-a-local-model.md` (zed-industries/zed `main`), and the parser in
`crates/agent_skills/agent_skills.rs`.

- Skill = folder with `SKILL.md`. Discovery roots: `~/.agents/skills/` (global) and
  `<worktree>/.agents/skills/` (project). **Flat only**: nested folders are not discovered.
  Symlinks are the documented way to point elsewhere.
- Frontmatter Zed reads: `name`, `description`, `disable-model-invocation`. The Rust
  `SkillMetadata` struct has no `deny_unknown_fields`, so other keys (`license`,
  `compatibility`, `metadata`) are ignored rather than rejected.
- `name`: 1–64 chars, `^[a-z0-9]+(-[a-z0-9]+)*$`, must match the folder name.
- `description`: ≤ 1024 chars (longer loads with a warning).
- `SKILL.md` ≤ 100 KB (`MAX_SKILL_FILE_SIZE`); body guidance ≤ 500 lines.
- Catalog budget: all names + descriptions ≤ 50 KB (`MAX_SKILL_DESCRIPTIONS_SIZE`); overflow is dropped with a UI warning.
- The agent loads a skill through the `skill` tool and reads bundled files with
  `read_file` / `list_directory`. Model-invoked skills prompt for permission unless
  allowed in `agent.tool_permissions.tools.skill` (matched against the absolute `SKILL.md` path).
- The agent **cannot edit `SKILL.md` or bundled resources** without explicit authorization,
  so skill scripts must never write inside their own skill folder.
- Project-local skills load only from **trusted** worktrees.
- Built-in skill `create-skill` exists (`/create-skill`). Do not reuse that name.
- Instructions: Zed loads the first of `.rules`, `.cursorrules`, `.windsurfrules`,
  `.clinerules`, `.github/copilot-instructions.md`, `AGENT.md`, `AGENTS.md`, `CLAUDE.md`, `GEMINI.md`.
- Profiles (`agent.profiles`) decide which tools exist; `agent.tool_permissions`
  decides allow / confirm / deny with regex patterns (`always_deny` wins).

## Ollama with Zed

Source: Zed `use-a-local-model.md`, Ollama docs `cloud.mdx`, `api/authentication.mdx`,
`capabilities/structured-outputs.mdx`, `context-length.mdx`, `integrations/zed.mdx`.

- Zed setting: `language_models.ollama.api_url` (`http://localhost:11434` local,
  `https://ollama.com` cloud), optional `auto_discover`, `available_models[]` with
  `max_tokens`, `supports_tools`, `supports_thinking`, `supports_images`, and `context_window`.
- Zed sends `num_ctx`; **default 4096**, too small for skills. Ollama recommends ≥ 64000
  for agents and coding tools. Ollama's own default is 4k under 24 GiB VRAM.
- Cloud: `Authorization: Bearer $OLLAMA_API_KEY` against `https://ollama.com/api/*`
  or `https://ollama.com/v1/*` (OpenAI-compatible). Cloud models run at max context.
- **Ollama Cloud does not support structured outputs.** Local `/api/chat` accepts
  `format: "json"` or a JSON Schema object.

## TypeSafe AI "Jev" (System One model)

Source: `typesafe-sdk` 0.7.5 wheel (OpenAPI-generated `_schemas/models.py`, vendored at
`vendor/typesafe-wire-models.py`) and the official `typesafe-ai/skills` SKILL.md.

- `POST {base}/v1/systemone`, `GET {base}/v1/models`; base default `https://api.typesafe.ai`.
- Auth: `Authorization: Bearer <key>`. Env vars: `TYPESAFE_API_KEY`, `TYPESAFE_BASE_URL`,
  `TYPESAFE_DEFAULT_MODEL` (default model `jev-latest`). Request id header: `x-typesafe-request-id`.
  Retry hints: `retry-after`, `retry-after-ms`.
- Request: `{"model", "state": str|object|array, "questions": {name: Question}, "assets"?}`.
- Question types: `noul` (instructions, criteria `{true, false}`), `choice` (instructions,
  criteria `{label: description}`), `score` (instructions, ordered `criteria[]`), `box` (images).
- Response: `{"model", "answers": {name: Answer}, "usage": {"input_tokens", "output_tokens"}}`.
  `noul` → `{"type":"noul","noul":p}`; `choice` → `choice`, `confidence`, `probabilities`;
  `score` → `score`, `confidence`, `legend`, `probabilities`.
- Errors: HTTP 422 `{"detail":[{"loc","msg","type"}]}`.
- Guidance: one narrow judgment per question; independent questions in one request run in
  parallel; question IDs are not sent to the model, so the instructions carry full meaning; a
  noul near 0.5 means uncertain; typed output guarantees the interface, not truth.

## Codex and Claude Code skills

- Codex scans `.agents/skills` from cwd up to the repo root, follows symlinks, and
  invokes skills as `$name`. Source: developers.openai.com/codex/skills.
- Claude Code reads `.claude/skills/<name>/SKILL.md` and invokes skills as `/name`.
- Spec Kit installs Zed and Codex skills to `.agents/skills/speckit-<command>/SKILL.md`
  (`docs/integrations/zed.md`, `codex.md`). Zed invokes them as `/speckit-specify`,
  Codex as `$speckit-specify`.

## Spec Kit

Source: `github/spec-kit` @ `dc2cec4` (2026-10-21).

- Commands: constitution, specify, clarify, plan, checklist, tasks, analyze, implement,
  **converge** (present upstream; absent in the `Cazador0/spec-kit` fork from 2026-05-01),
  and taskstoissues (core one deprecated in favour of the `github` extension).
- `tasks.md` line format: `- [ ] T001 [P] [US1] Description in path/file.py`, with an
  optional inline `(depends on T012, T013)`. Task ID regex `\bT\d{3,}\b`. Phases order
  dependencies: Setup → Foundational (blocks all stories) → user-story phases → Polish.
- The `github` extension titles issues `T001: <description>` and deduplicates by matching
  existing titles against the task-ID regex across open and closed issues.
- Extension manifest: `extension.yml` (`schema_version`, `extension.id`, `provides.commands[]`).

## Gitea

- Current release is **28.2.0** (2026-10-18), following 28.0.0 (2026-09-29) and 1.27.x.
  Source: Gitea blog and GitHub releases.
- REST under `/api/v1`. Issue dependencies:
  `GET|POST|DELETE /repos/{owner}/{repo}/issues/{index}/dependencies` (body `IssueMeta`
  `{owner, repo, index}`), plus `/blocks`. Webhook headers: `X-Gitea-Event`,
  `X-Gitea-Delivery`, `X-Gitea-Signature` (hex HMAC-SHA256 of the raw body).
- Project-board (column) API coverage differs between versions. The skills read
  `/swagger.v1.json` to discover it and otherwise fall back to exclusive scoped labels
  (`state/<name>`) for board state.
