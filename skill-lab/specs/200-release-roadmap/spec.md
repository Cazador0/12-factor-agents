# Feature Specification: Release roadmap for progressive autonomy

**Spec ID**: SPEC-200

**Created**: 2026-10-22

**Status**: Accepted

**Input**: User decisions in the build session, 2026-10-22:
"All three options. Phase out each option as separate specs and define all release goals for each
option, then sequence each option and complete all tasks: Plan → Synthesize → Create Tasks as Spec →
Create Implementation Plan → Execute and deliver Implementation Plan as `/speckit-development` →
Create Pull Request → another Claude Code session reviews the changes."
"Everything cloud first. Local enabled second after cloud is reliable and performing as expected and
aligned to user intent."

## Intent

The skills bring the report's Lead / PSE / Review engineering organization to the Zed Agent,
Claude Code, and Codex. Autonomy is earned in steps, not granted at once. Each autonomy level the
report defines is a separate release with its own spec, release goals, and gates. A release ships
only after the previous release's gates have passed.

## Releases

| Release | Spec | Autonomy level shipped | What agents may do on their own | What stays human |
|---|---|---|---|---|
| R1 Shadow | SPEC-201 | `shadow` | Read, analyse, plan, and emit JSON plans, verdicts, and decisions. Every Gitea and git mutation is a plan (`gitea-plan`, `mutation-request`) | Every consequential write and every merge |
| R2 Agent implementation | SPEC-202 | `agent-implementation` | PSE branches, codes, tests, pushes its own branch, and opens a PR. Lead creates issues and dependencies. Review posts reviews. Leases are enforced | Merge (the merge gate never returns `AUTO_MERGE`) |
| R3 Guarded autonomous | SPEC-203 | `guarded-autonomous` | Low-risk PRs auto-merge through Gitea "merge when checks succeed" once Review, CI, freshness, and dependency gates pass. Event-driven dispatch, lease recovery | High- and critical-risk merges, any change to policy, CI, agent permissions, or the gates themselves |

A release supports its own level and every lower level. The active level for a project is set in
`.skill-policy.json` (contract `autonomy-policy.v1`, defined in SPEC-201). Raising the level is a
**critical-risk** change: it always needs a human, and no agent may make it. That follows the
report's invariant that agents may not autonomously weaken the rules that define their authority.

## Inference track

| Step | When | Configuration |
|---|---|---|
| C1 Cloud first | R1 | Every Zed profile (Lead, PSE, Review) defaults to an Ollama Cloud model. Benchmarks run `--runtime ollama-cloud --jev live` |
| L1 Local second | R2, gated | Local Ollama profiles ship disabled. They are enabled only after the C1 gates pass on 3 consecutive benchmark runs, the user confirms the output matches their intent, and the same suite then passes on `--runtime ollama-local` |

The gate for enabling local inference is measured. "Reliable" means the agentic and trigger gates
of every skill pass on Ollama Cloud with Jev judgments live, on 3 consecutive runs. "Aligned to user
intent" is a recorded human sign-off in `skill-lab/benchmarks/signoff/` (in SPEC-202).

## Delivery process (every release)

```text
1 Plan            release-plan.md   scope, release goals RG-n, entry and exit criteria
2 Synthesize      synthesis.md      research findings, decisions, risks, open questions
3 Tasks as spec   spec.md           FR-n, SC-n, acceptance scenarios, release gates
                  tasks.md          Spec Kit format, dependency-ordered, mapped to skills
4 Impl. plan      plan.md           technical context, architecture deltas, test strategy
5 Execute         /speckit-development drives tasks.md: implement → evidence → converge
6 Pull request    release branch → Cazador0/skill-factory
7 Review          a separate Claude Code cloud session runs review-verifier on the PR and
                  posts a review-verdict.v1 JSON comment
8 Merge           human merge after the verdict is APPROVE and CI is green
```

Steps 1 to 4 live in `skill-lab/specs/20N-release-<name>/`. Step 5 is the `speckit-development`
skill (SPEC-013), the 13th skill. In R1 it runs plan-and-evidence only; from R2 it delivers the PR
end to end. Step 7 never runs in the session that wrote the change, so the reviewer and the author
are always independent.

## Release goals (summary; each release spec is authoritative)

- **R1 (SPEC-201)**: all 13 skills install and validate on Zed, Claude Code, and Codex. The
  autonomy policy is enforced by `_skillkit.policy`, and at level `shadow` every mutation is refused
  with exit 4 or emitted as a plan. Deterministic gates pass 100 %. Cloud agentic and trigger
  benchmarks run as soon as the network is allowlisted. Zed profiles are configured cloud-first. The
  automated review loop (step 7) works on the R1 PR itself.
- **R2 (SPEC-202)**: PSE delivers a real PR from an isolated worktree under a lease, with evidence
  produced only from executed commands. `speckit-gitea-taskstoissues --apply` is idempotent against
  the Gitea test double, and against a live Gitea when one is configured. Review posts verdicts. The
  merge gate never auto-merges. Local inference L1 is enabled behind its gate.
- **R3 (SPEC-203)**: `AUTO_MERGE` for low risk only. Event-driven loop: verified and deduplicated
  webhook, then state machine, then dispatch. Lease-expiry recovery from checkpoints. Promotion and
  demotion between levels driven by the report's core metrics, with automatic demotion to
  `agent-implementation` after an escaped defect or a revert.

## Sequencing

```text
Foundation (SPEC-100..104) ──► R1 Shadow ──► R2 Agent implementation ──► R3 Guarded autonomous
                                  │                   │
                          C1 cloud gates ──3 runs──► L1 local enablement
```

R2 starts only after the R1 PR has an APPROVE verdict from the independent reviewer. R3 starts only
after the R2 PR does. A release that misses a gate stays open; the next one does not start.

## Success Criteria

- **SC-001**: Each release has release-plan.md, synthesis.md, spec.md, plan.md, and tasks.md, with every FR traced to tasks and verification.
- **SC-002**: Each release PR receives a review-verdict.v1 from a session other than the authoring session before merge.
- **SC-003**: At level `shadow`, 0 consequential mutations succeed across the full deterministic suite (every attempt exits 4 or emits a plan).
- **SC-004**: Local inference is enabled only with a passing L1 gate record.

## Non-goals

- Agents merging the skill-factory repository's own PRs. The factory's main branch is always merged by a human.
- Storing or reconstructing chain-of-thought.
- Persona pedigree prompts. Roles are defined by competencies, permissions, and evidence.
