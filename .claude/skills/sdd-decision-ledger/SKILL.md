---
name: sdd-decision-ledger
description: "Build the decision ledger for a Spec Kit phase and put every decision the phase made without the person's backing to them as multiple-choice rounds: extract decisions from the artifact (spec requirements and success criteria, plan Technical Context, research decisions, checklist items, tasks, analyze findings, unplanned implementation changes), check each against intake answers, confirmed assumptions, the constitution, earlier clarifications and supplied source documents, and sort them into Backed, Delegated, Unbacked or Conflicting with cited evidence. Use this whenever /speckit-intake-refine runs in this repository, after /speckit-specify, /speckit-plan, /speckit-checklist, /speckit-tasks, /speckit-analyze, /speckit-implement or /speckit-converge, or whenever someone asks what a phase decided on its own, whether a spec matches what they asked for, or to review a spec against a brief."
compatibility: "Requires the Spec Kit project in this repository and packages/sdd-harness (uv sync --project packages/sdd-harness)."
metadata:
  based_on: speckit-intake-refine
  engine: packages/sdd-harness/src/sdd_harness/ledger
---

# Decision ledger

`/speckit-intake-refine` defines refinement: find the phase, its artifact and its intake; build the
ledger before asking; ask in multiple-choice rounds; record after every round; finish. This skill
runs it with the ledger engine (`bin/sdd refine …`, a LangGraph state machine) and tells you where
your judgment still matters. Read `.claude/skills/speckit-intake-refine/SKILL.md` once per session.

## The loop

```
1. bin/sdd refine start <phase> [--feature-dir specs/###-name] [--source brief.md] [--findings report.md]
2. returns {"status": "awaiting_answers", "progress": …, "card": {"questions": [...], "lint": {...}}}
3. review the ledger; sharpen generic cards (below)
4. AskUserQuestion(questions = card.questions)        ← lead with the "progress" line
5. bin/sdd refine answer <phase> [--feature-dir …] --answers '<the tool result as JSON>'
6. apply every item in "artifact_edits"; repeat 3–5 until {"status": "finished", …}
```

`<phase>` is the one that just ran: `constitution | specify | plan | checklist | tasks | analyze |
implement | converge`. Without `--feature-dir` the engine asks
`.specify/scripts/bash/check-prerequisites.sh` for `FEATURE_DIR`.

- `--source` adds a document the person supplied (the brief or report the feature came from) as
  backing; repeat it for several. Without it, lines that trace only to that document read Unbacked.
- `--findings` is required for `analyze`, which writes no file: save its report and pass it.
- `--base <git ref>` scopes `implement` to changes since the tasks were written.

`bin/sdd refine ledger <phase> [--json]` builds and shows the ledger without asking anything.

## What the engine decides, and what you decide

The engine writes the ledger first: a JSON sidecar beside the intake (`refine-<phase>.json`) and a
table under the intake's `## Phase Refinements → ### <Phase> · <date>`. It links an `Answered`
feature intake still reading `**Feature**: pending` to `FEATURE_DIR` when its idea matches the spec.
The project intake's answers (Scope: project) back every feature.

| Group | Engine rule | Your job |
|---|---|---|
| Conflicting | A number differs from a recorded answer, assumption, rule or requirement on the same topic, or the line restates an overturned assumption | Asked first. After "Follow the earlier decision", rewrite the artifact line from `artifact_edits` |
| Unbacked | `[NEEDS CLARIFICATION]`, an unchecked checklist item, a CRITICAL/HIGH analyze finding, a task tracing to no story or requirement, or no recorded decision covering ≥ 45% of the line's terms | Skim: if the evidence column shows a line really is backed, say so in the card rather than asking blindly |
| Delegated | The best backing is a `Delegated — agent chose …` answer | Leave it; reopen only if it breaks a limit the person set |
| Backed | Traced requirement, or a recorded decision covers the line | Leave it |

Lexical matching is deliberately conservative: a spec line that adds detail nobody chose stays
Unbacked, which is the point of refinement. Semantic contradictions that share no numbers are for
you to spot. In service mode, Claude gives a grounded second opinion on borderline lines.

### Cards

Questions come in ledger order: Conflicting first, then Unbacked by impact × uncertainty. Low-impact
defaults and assumptions go into one multi-select "Which of these defaults should stay as written?"
card with nothing recommended. The generic options are:

- unbacked line: **Keep as written** (recommended) · Mark it open · Decide during <next phase>
- conflict: **Follow the earlier decision** (recommended) · Keep the new line · Mark it open
- open point: **Decide during <next phase>** (recommended) · Leave it open · Drop it from scope
- checklist item: **Not yet** (recommended: never self-approve) · Yes I checked it · Not applicable

When a concrete alternative exists ("Postgres" vs "plain files in git"), rewrite the card so one
click settles one line, keeping the card rules (`card.lint` lists any problem).

### Recording

`answer` writes the ledger's Answer cells, a `- Q: … → A: …` line under the phase's refinement
heading, a Session Log row, and for `specify` the same line under `spec.md` → `## Clarifications` →
`### Session <date>`. It edits artifacts only where the edit is mechanical: a `[NEEDS CLARIFICATION]`
marker for "Mark it open", a ticked checklist item for "Yes I checked it". Everything that changes
meaning comes back as `artifact_edits` for you to apply in the artifact's own format, keeping the
person's strength of wording. Every 5 rounds the engine returns a keep-going card.

## Finish

On `finished`, reread the changed artifacts once for contradictions the answers introduced, then reply
with the counts the engine returned (Backed, Delegated, still open), the files changed, and the next
phase in plain words. Starting it is the person's call.

**Limits**: refinement edits only the current phase's artifacts and the intake. It never deletes,
installs or pushes; constitution edits follow the constitution's amendment rules.

## Traces

`.specify/traces/refine-<phase>-<feature>/trace.jsonl` records the ledger build and each round;
`reasoning/ledger.md` holds one visible reasoning chain per decision (best backing, coverage, clash
checks, verdict). Chains explain verdicts; the person's answers decide (Constitution Art. IX).
