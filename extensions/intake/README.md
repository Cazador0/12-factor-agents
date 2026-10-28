# Spec Intake extension

A Spec Kit extension that sits in front of `/speckit.specify` and behind every phase:

| Command | Skill in Claude Code | What it does |
|---|---|---|
| `speckit.intake.start` | `/speckit-intake-start` | Writes `.specify/intakes/<slug>/intake.md`, then asks multiple-choice rounds until the constitution, spec and plan rows are sufficient or the person stops. |
| `speckit.intake.route` | `/speckit-intake-route` | Finds the right skill for a task in the intakeSpec catalog (`bin/intakespec find`), or sends a rough idea to intake. Read-only. |
| `speckit.intake.refine` | `/speckit-intake-refine` | After a phase runs, builds a decision ledger (Backed, Delegated, Unbacked, Conflicting) and puts the unbacked decisions to the person. |

Hooks: `start` runs (mandatory) before `/speckit.constitution` and `/speckit.specify`; `refine` is offered after every phase except `clarify`.

## Install

```bash
specify extension add --dev extensions/intake
```

## Engines

The commands are prompt-only and work in any Spec Kit integration. In this repository three skills back them with
deterministic engines in `packages/sdd-harness` (LangGraph graphs, hybrid RAG, decision traces):

- `.claude/skills/sdd-intake-engine` for `start`
- `.claude/skills/sdd-skill-router` for `route` (also behind `bin/intakespec`)
- `.claude/skills/sdd-decision-ledger` for `refine`

## Configuration

`.specify/extensions/intake/intake-config.yml`; a `local-config.yml` beside it wins. See `intake-config.template.yml`.
