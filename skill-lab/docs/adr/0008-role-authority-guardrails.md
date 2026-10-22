# ADR-0008: Role authority through runtime profiles and permissions, as guardrails; the boundary is Gitea and the merge gate

## Status

Accepted

## Date

2026-10-22

## Context

The report separates three roles by objective and authority, not by persona (report
[§The three-agent operating model](../research/engineering-team-report.md#the-three-agent-operating-model)).
None of them may approve its own code or bypass branch protection. Review "should never silently
repair the PSE's production implementation and then approve the combined result". One PSE session
is the single write owner of its issue. CONVENTIONS §7 turns this into a table of what each role
may edit and must never do. The report's key invariant
([§Safe autonomous merge](../research/engineering-team-report.md#safe-autonomous-merge)):

> Agents may operate autonomously inside the rules; they may not autonomously weaken the rules
> that define their authority.

What the runtimes offer
([SOURCES.md, Zed](../research/SOURCES.md#zed-agent-skills); Zed `agent-profiles.md`,
`tool-permissions.md`, `tools.md`, `sandboxing.md`):

- **Zed profiles** (`agent.profiles`) decide which tools exist in a thread (`read_file`, `grep`,
  `edit_file`, `write_file`, `delete_path`, `terminal`, `fetch`, `skill`, `spawn_agent`, ...)
  and can set a `default_model`. A subagent from `spawn_agent` has the same tools as its parent.
- **Zed tool permissions** (`agent.tool_permissions`) allow, confirm or deny calls with Rust regex
  patterns matched against the command string (`terminal`), the path (edit tools) or the
  `SKILL.md` path (`skill`). `always_deny` has the highest priority after Zed's built-in rules.
  Chained shell commands are split and each part is checked. Tool permissions are **global**:
  they apply to every profile.
- Profiles and permissions **do not apply to External Agents or Terminal Threads**, and a user can
  approve any prompt with "Allow once".
- Zed's optional **OS sandbox** for `terminal` and `fetch` blocks outbound network unless a host is
  approved and keeps `.git` metadata read-only. It still lets commands write inside the project.
- **Claude Code** reads `.claude/settings.json` permission rules. The exact deny syntax for paths
  is to be verified (SPEC-201 synthesis D-23). **Codex** has no per-path deny in SOURCES.md. Its
  benchmark runs use `codex exec --sandbox read-only`.

An agent that has a terminal can write any file the operating system lets it write, for example
with `python3 -c`. No regex over command strings can rule that out.

## Decision

1. **Three Zed profiles ship as templates** in `skill-lab/config/zed/settings.example.jsonc`
   (SPEC-201 FR-039), each with its own `default_model` and tool set:

   | Profile | Tools on | Tools off | Why |
   |---|---|---|---|
   | Lead | read tools, edit tools, `terminal`, `skill`, `spawn_agent` | `fetch`, `search_web` | Edits specs, docs and issue contracts; may delegate read-heavy investigation |
   | PSE | read tools, edit tools, `terminal`, `skill` | `spawn_agent`, `fetch`, `search_web` | A subagent has the parent's write tools and would be a second writer on the leased branch (report [§PSE contract](../research/engineering-team-report.md#pse-contract)) |
   | Review | read tools, `terminal`, `skill`, `spawn_agent` | edit tools, `fetch`, `search_web` | The verifying session reads and re-runs; it does not edit what it verifies |

   Read tools are `read_file`, `grep`, `find_path`, `list_directory` and `diagnostics`. Edit tools
   are `edit_file`, `write_file`, `delete_path`, `move_path`, `copy_path` and `create_directory`.
   `fetch` and `search_web` are off everywhere: the skills work offline, and web pages are untrusted
   text (ADR-0012).

   CONVENTIONS §7 lets Review write test and eval code, but Zed cannot limit edit tools to test
   paths for one profile. So the verifying Review session gets no edit tools, and test code that
   Review authors is written in a separate session on a test-only branch
   (`agent/review/<issue>-<slug>`; report
   [§Review contract](../research/engineering-team-report.md#review-contract)). A missing test that
   blocks approval goes into the verdict as a blocker for PSE. Two mechanical checks back this up,
   because `terminal` can still write files: a verdict is refused when the reviewing session
   authored any commit in the reviewed range (`REVIEW_NOT_INDEPENDENT`), and Review's re-run checks
   count only when run at `reviewed_commit` on a clean tree, so a local "repair" cannot make a
   broken head look green (the clean-tree rule SPEC-202 synthesis D-9 sets for evidence).

2. **One global deny list protects the paths that define authority**, for every profile.
   `always_deny` on all edit tools for `.skill-policy.json`, `.skill-gitea.json` (R2),
   `.github/workflows/`, `.gitea/workflows/`, `.claude/settings.json`, `.zed/settings.json` and
   `CODEOWNERS`, plus terminal commands that name `.skill-policy.json`. `always_confirm` on
   terminal commands that pass `--apply`, `git push`, or call `curl`, `gh` or `tea`. The template
   is the authoritative list. This ADR fixes the principle: a path that defines an agent's
   authority is never writable by an agent.
3. **Claude Code and Codex get the closest equivalent.** The exported `.claude/settings.json`
   denies Edit and Write on the same paths (SPEC-201 FR-012). For Codex, `AGENTS.md` states what
   an agent may never do, and the merge gate is the only mechanical control.
4. **The Zed sandbox is recommended.** It blocks outbound network for terminal commands unless a
   specific host is approved, so a script reaching Gitea, `ollama.com` or `api.typesafe.ai`
   triggers a host-specific approval rather than silent access. It does not protect project files
   such as `.skill-policy.json`, so it complements the deny list rather than replacing it.
5. **All of the above are guardrails, not a security boundary**
   ([CONVENTIONS §7](../CONVENTIONS.md#7-roles-and-authority-zed-profiles)). No claim of safety rests
   on them. They stop the common accident, an agent "fixing" a failing gate by editing its
   criteria, and they make deliberate bypass visible.
6. **The security boundary is the forge plus deterministic gates**:
   - Gitea branch protection on the base branch: no direct push, no force push, no administrator
     bypass, at least one required approval, merge blocked on requested changes, stale approvals
     dismissed, head current with base, required CI contexts, protected file patterns (report
     §Safe autonomous merge);
   - `merge-policy-gate`, which classifies any diff that touches a policy path as `critical`, so
     the decision is `HUMAN_APPROVAL_REQUIRED` (SPEC-201 §Security lists the paths, including
     `skills/review-verifier/**`, the reviewer's own gates);
   - Review independence, checked by session ids and commit trailers (`REVIEW_NOT_INDEPENDENT`),
     and from R2 by separate Gitea identities per role (planned for ADR-0201);
   - the human merge in R1 and R2.
7. **Agents may not weaken the rules that define their authority.** `policy.change` is a
   `human-only` action. Thresholds, gates, CI, runtime settings, the policy module and the action
   catalog are critical paths. An agent may propose a change to them in a PR. Only a human merges
   it.

## Consequences

### Positive

- Cheap, visible friction exactly where accidents are most damaging.
- Role differences are concrete: a verifying Review session cannot use the editor tools, a PSE
  session cannot fan out writers, and a reviewer's approval is void if it committed to the range
  it reviews.
- The safety argument never depends on a model obeying instructions or on regexes being complete.

### Negative

- **Per-role path scoping is impossible in Zed today.** Tool permissions are global, so "PSE may
  edit `src/` but not `specs/`" cannot be expressed. Only tool availability differs per role, so
  much of the separation is enforced after the fact, on commits, verdicts and merges.
- Review needs a second session, with an editing profile, to author tests. That costs a session
  and a branch per test contribution.
- Deny regexes are brittle both ways: false positives block legitimate work, and obfuscated
  commands get through.
- Prompt fatigue. Confirm rules on `--apply` and `git push` ask the user often, and a tired user
  approves.
- The lab can validate the shipped template. It cannot see the user's live Zed settings, so
  drift between them goes unnoticed.

### Residual risks

| Risk | Why it remains | Mitigation |
|---|---|---|
| An agent writes a policy file through the terminal (`python3 -c`, `sed`, a redirect) | Terminal access is needed for scripts | Merge gate classifies the diff `critical`; branch protection blocks direct pushes; from R2 the effective level is read from the base branch, so a working-tree edit has no effect (SPEC-202 synthesis D-21) |
| Claude Code or Codex run inside Zed as External Agents, without Zed profiles | Zed applies profiles only to the Zed Agent | Their own permission settings apply; the forge boundary is unchanged |
| Codex has no per-path deny | Not in SOURCES.md | Weaker coverage is accepted and documented (SPEC-201 synthesis D-23) |
| Author and reviewer post from the same forge account (the GitHub factory repository) | One human account behind both sessions | Session-id and trailer proof (SPEC-201 FR-035); per-role Gitea identities in R2 |

## Alternatives considered

| Alternative | Why rejected |
|---|---|
| Persona prompts ("you are the reviewer, do not edit code") | The report replaces persona with permissions, evidence and mechanical constraints |
| Treat Zed profiles and deny rules as the boundary | A terminal defeats them, they do not apply to external agents, and users can approve prompts |
| One OS user or container per role | Strong isolation, but heavy for a single developer's machine. A later option on top of this design, not a replacement for the forge boundary |
| Give the Review profile edit tools so it can write tests in place | Zed cannot restrict them to test paths, so the verifying session could also edit production code, the collapse of independence the report warns about. The commit-range check would catch committed edits but not a dirty working tree that fools a local re-run |
| A Gitea MCP server with role-scoped tools as the boundary | The report's long-term direction, outside R1's offline-stdlib scope. The forge's own protections remain the boundary even then |

## Compliance

| Rule | Verified by | State on 2026-10-22 |
|---|---|---|
| `AUTO_MERGE` impossible for policy paths, high or critical risk, or failing gates | `merge-decision.v1` schema invariant; crafted invalid cases in `test_contracts.py` | enforced |
| Shipped Zed template: three profiles with the tool sets above | `test_configs.py::TestZedSettings::test_profiles_are_the_three_roles`, `test_configs.py::TestZedSettings::test_tool_sets_follow_adr_0008` | written by the config builder in parallel with this ADR |
| Shipped templates: authority paths denied for every file tool, even with loosened defaults; Claude Code edit rules | `test_configs.py::TestZedPermissions::test_file_decisions_hold_even_if_defaults_are_loosened`, `test_configs.py::TestZedPermissions::test_terminal_decisions`, `test_configs.py::TestClaudeSettings::test_edit_decisions` | written by the config builder in parallel with this ADR |
| The same rules as a validator check on any project's configs | `skill-lab validate --config zed,claude` (G-OFF-09; SPEC-201 T115) | planned |
| Policy paths are classified `critical` | `merge_decision.py` (SPEC-201 User Story 5, scenario 5) | planned |
| Review independence | `review_verdict.py` and `review_collect.py` exit 4 `REVIEW_NOT_INDEPENDENT` (SPEC-201 FR-035) | planned |
| Review's re-run checks count only at `reviewed_commit` on a clean tree | `check-run` with `head_commit` (R1) and `tree_clean` (SPEC-202 synthesis D-9); quality-gate input validation | planned (R2) |
| No mutation succeeds at `shadow`, whatever the runtime permits | `skill-lab policy containment` (G-OFF-07) | planned |
| Branch protection on the target base branch | Gitea settings; R2 `branch_audit.py` checks BP-01..BP-12 and reports a field the API omits as `unknown`, never `pass` (SPEC-202 synthesis D-12) | external now; planned (R2) |

The template tests check only the files this repository ships. Nothing checks the settings a user
actually runs, which is one more reason these controls are guardrails.

**Revisit when** Zed supports per-profile tool permissions or path scopes, when Codex gains per-path
controls, or when per-role OS isolation becomes practical.

## References

- Report [§The three-agent operating model](../research/engineering-team-report.md#the-three-agent-operating-model),
  [§Review contract](../research/engineering-team-report.md#review-contract),
  [§Safe autonomous merge](../research/engineering-team-report.md#safe-autonomous-merge),
  [§Agent configuration philosophy](../research/engineering-team-report.md#agent-configuration-philosophy)
- [CONVENTIONS §7](../CONVENTIONS.md#7-roles-and-authority-zed-profiles), [§8](../CONVENTIONS.md#8-autonomy-levels)
- [SPEC-201 R1](../../specs/201-release-shadow/spec.md) FR-012, FR-035, FR-039 and §Security;
  [SPEC-201 synthesis](../../specs/201-release-shadow/synthesis.md) D-23, R-1, R-4
- ADR-0005 (layers of refusal), ADR-0009 (Gitea), ADR-0012 (security model)
