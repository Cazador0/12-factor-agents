---
name: speckit-intake-refine
description: Put unconfirmed decisions back as multiple-choice questions; write into intake.
compatibility: Requires spec-kit project structure with .specify/ directory
metadata:
  author: Cazador0
  source: intake:commands/refine.md
---

# Intake refinement

## User Input

```text
$ARGUMENTS
```

Consider the user input before proceeding (if not empty). It may name the phase to refine (`constitution`, `specify`, `plan`, `checklist`, `tasks`, `analyze`, `implement` or `converge`), or narrow the scope ("only the storage choices").

## Why this step exists

Every Spec Kit phase fills gaps on its own. `/speckit.specify` allows at most three `[NEEDS CLARIFICATION]` markers and assumes the rest; `/speckit.plan` picks technology; `/speckit.tasks` picks an order; `/speckit.implement` makes many small calls the plan never named. Each of those is a line nobody chose. The intake settled the big unknowns before the phase ran. Refinement catches what the phase decided by itself, while it is still cheap to change, and asks the person about it in the same multiple-choice form: a concrete recommendation first, so answering stays fast.

Spec Kit offers this command as an optional hook after each phase except `clarify`, which already asks multiple-choice questions. The person can also run it at any time.

## 1. Find the phase, the artifact and the intake

**Phase**: take it from the input. If the input is empty, use the Spec Kit command that just ran in this conversation. If neither settles it, ask one question.

**Feature directory**: run `.specify/scripts/bash/check-prerequisites.sh --json --paths-only` from the repository root and read `FEATURE_DIR`. Skip this step for `constitution`.

| Phase | Read | Write answers into |
|---|---|---|
| constitution | `.specify/memory/constitution.md` | the constitution, following its own amendment rules (version bump and Sync Impact note) |
| specify | `FEATURE_DIR/spec.md` | the requirement, scenario, entity or criterion the answer settles, plus a line under `## Clarifications` |
| plan | `plan.md`, `research.md`, `data-model.md`, `contracts/` | the Technical Context field or design artifact the answer settles |
| checklist | `FEATURE_DIR/checklists/*.md` | the checklist item: ticked only when the person confirms it |
| tasks | `tasks.md` | the task lines the answer changes |
| analyze | the analysis report in this conversation (analyze writes no file) | whichever artifact the chosen resolution edits |
| implement | the changes made since `tasks.md` was written, and `tasks.md` | the code or `tasks.md`, as the answer requires |
| converge | the tasks converge appended to `tasks.md` | `tasks.md` |

**The intake**: intakes live in `.specify/intakes/<slug>/intake.md` (or the `intakes.dir` in `.specify/extensions/intake/intake-config.yml`).
- For `constitution`, use the project intake: the one marked `**Scope**: project`.
- For every other phase, use the feature intake whose `**Feature**` line names `FEATURE_DIR`.
- If an Answered feature intake still reads `**Feature**: pending` and holds this feature's idea, link it: set its `**Feature**` line to `FEATURE_DIR`.
- If no intake exists, say in one line that the intake start command creates one. Then refine against the artifact alone, and record the answers in the artifact only.

## 2. Build the decision ledger before asking

Read the artifact against its backing: the intake's answers, confirmed assumptions and Clarifications; the constitution; earlier refinements; and what the person said in this conversation. Sort every decision the phase made into one of four groups:

- **Backed**: traceable to one of those sources. Leave it alone.
- **Delegated**: the person left this choice to the agent, either through an intake answer recorded as Delegated or through a "decide during planning" option. The phase's choice stands as the agent's decision. Record it with a one-line reason so the person can reverse it later. Ask again only if it breaks a limit the person set.
- **Unbacked**: a default, a guess, an invented number, a `[NEEDS CLARIFICATION]` marker, or a technology, scope, ordering or resolution choice the phase made on its own. These become questions.
- **Conflicting**: contradicts an answer, a confirmed assumption or the constitution. These always become questions, and they come first.

For `checklist`, every unchecked item is Unbacked: the checklist belongs to a human reviewer, and implementation must never self-approve it. For `analyze`, every CRITICAL or HIGH finding is Unbacked, and its options are the possible resolutions (fix the spec, fix the plan, accept it with a note).

Write the ledger into the intake before the first round, under `## Phase Refinements` → `### <Phase> · YYYY-MM-DD`, as a table: `| # | Decision | Where | Group | Question | Answer |`. Writing it first means each round is chosen from a record rather than improvised, and an interrupted session loses nothing.

Rank the Unbacked items by impact × uncertainty: how much the answer changes the artifact, times how unsure you are. Low-impact items with a safe default become assumptions. Put them to the person in one multi-select assumption check ("Which of these defaults should stay as written?"), with each default's full wording in its option description and no option marked recommended.

## 3. Ask in multiple-choice rounds

A round is one call to the multiple-choice tool with at most `session.per_round` questions (`.specify/extensions/intake/intake-config.yml`; a `local-config.yml` beside it wins; 4 when unset; a stricter limit stated in the project's constitution applies): `AskUserQuestion` in Claude Code, the host's equivalent elsewhere, or a numbered list with lettered options when no such tool exists. Lead each round with one line of progress, such as "Plan refinement, round 2: 5 of 9 decisions settled; now storage and testing."

Write every question so it survives as a card:
- A complete question that ends with "?" and makes sense on its own.
- 2–4 options, mutually exclusive unless the question is multi-select. Each option carries a one-line implication for the artifact. Prefer options that are candidate artifact lines, so that one click settles one line.
- Your recommended option comes first with the tool's "(Recommended)" suffix, and one line on why. It is only a recommendation until the person picks it.
- Every option must still be possible. Leave out options that the constitution, the intake or an earlier answer already rules out. A chosen option's description settles as much as its label does.
- A header of 12 characters or fewer. Option labels of 1–5 words, with no commas. No hand-made "Other": the tool adds a free-text choice.
- Plain language. Use the person's own words for their idea, not internal labels like row numbers.

**When the person leaves it to you** ("you decide", "your call", or a "Decide during …" option), make the decision: take your recommendation unless the answers so far point elsewhere. Record it as `Delegated — agent chose <label>: <one-line reason>`. It is now the agent's decision, clearly labeled, and the person can overturn it at any later refinement.

**Stop** when no Unbacked or Conflicting item of consequence remains, or when the person says to stop. After every 5 rounds, ask one keep-going card ("Keep going (Recommended)" or "Wrap up now"). If the person does not know an answer, try once more from a different angle. If it is still open, mark it `[NEEDS CLARIFICATION: …]` in the artifact and move on. Never loop on a gap the person can't answer.

## 4. Record after every round

Make small in-place edits, not rewrites, so earlier answers are never dropped.

1. **Intake**: fill the ledger's Answer cells; append one `- Q: <question> → A: <answer>` line per answer under the phase's refinement heading; add a row to the Session Log.
2. **Artifact**: apply each answer where it belongs, in the artifact's own format (see the table in step 1). For `spec.md`, also append the same `- Q: … → A: …` line under `## Clarifications` → `### Session YYYY-MM-DD`, the format `/speckit.clarify` uses, so later phases see it.
3. Keep the person's strength of wording: "a paper backup is fine" never becomes "must have a paper backup".
4. Never record your recommendation as the person's answer unless they chose it or delegated the choice.

## 5. Finish

Reread the changed artifact once for contradictions the answers introduced, and settle any that matter with one short follow-up round. Then reply with one line each on:
- questions asked over how many rounds;
- how many decisions ended Backed, Delegated or still open;
- which files changed.

Name the next Spec Kit phase in plain words, but leave starting it to the person.

**Limits**: refinement edits only the current phase's artifacts and the intake. It never deletes, installs or pushes. Constitution edits follow the constitution's own amendment rules.