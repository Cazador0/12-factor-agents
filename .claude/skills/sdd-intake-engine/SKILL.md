---
name: sdd-intake-engine
description: "Run a spec intake session with the deterministic engine: write .specify/intakes/<slug>/intake.md, then drive multiple-choice rounds through AskUserQuestion until every constitution, spec and plan row is sufficient or the person stops. Use this whenever /speckit-intake-start runs in this repository, whenever someone hands over a rough idea, a hunch, a 'what if', a brief or a long document to turn into a spec, before /speckit-specify or /speckit-constitution, or when an intake must be resumed in a fresh session. It keeps the file, the card rules, the sufficiency check, round selection, check-ins, decision traces and visible reasoning consistent so you can focus on writing good questions."
compatibility: "Requires the Spec Kit project in this repository (.specify/) and packages/sdd-harness (uv sync --project packages/sdd-harness)."
metadata:
  based_on: speckit-intake-start
  engine: packages/sdd-harness/src/sdd_harness/intake
---

# Intake engine

`/speckit-intake-start` says **what** an intake session must do. This skill is **how** to run one here
without losing anything. The engine (`bin/sdd intake …`, a LangGraph state machine) owns the mechanics:
the file, the rows, card linting, the order of questions, recording answers in place, check-ins,
`Open` items, decision traces. You own the judgment: reading the idea, writing questions that fit
it, and deciding when a row's evidence is really enough.

Read `.claude/skills/speckit-intake-start/SKILL.md` once per session for the rules. Everything below
assumes them, and nothing here overrides them.

## The loop

```
1. draft.json  →  bin/sdd intake start "<idea, verbatim>" --draft draft.json
2. returns {"status": "awaiting_answers", "progress": …, "card": {"questions": [...]}, "intake": path}
3. sharpen any generic scaffold   →  bin/sdd intake questions <slug> --replace Q7 --json '{…}'
4. AskUserQuestion(questions = card.questions)       ← lead with the "progress" line
5. bin/sdd intake answer <slug> --answers '<the tool result as JSON>'
6. repeat 3–5 until {"status": "finished", …}
```

### 1. Draft before asking

Write `draft.json` from the idea (and anything it points at: a URL, a document, this repo). Every
field is optional; whatever you leave out, the engine fills with honest defaults (rows `Missing`,
generic scaffold questions).

```json
{
  "title": "Plant watering reminders",
  "interpretation": "Reminders for one person's houseplants so none are over- or under-watered.",
  "idea_type": "new-capability",
  "sources": "none",
  "software": true,
  "rows": {"S1": {"status": "Partial", "evidence": "idea text", "still_needed": "why now"}},
  "assumptions": ["Reminders use the device's local time zone — unconfirmed"],
  "questions": [
    {"header": "People", "row": "S2", "impact": "high", "uncertainty": "high",
     "text": "Who should the first version of the plant reminders serve?",
     "options": [
       {"label": "People with houseplants", "description": "One person's own plants at home.",
        "recommended": true, "why": "the idea says 'my plants'"},
       {"label": "Community gardens", "description": "Shared beds; needs roles."}]}
  ]
}
```

Draft about 12 questions aimed at the Missing and Partial rows (step 3e of the start command). The
engine lints every card against step 3f and reports problems in `lint`; fix them before asking.
Constitution articles and prior decisions (`.agents/memory.md`, `AGENTS.md`) that settle a row go
in as `Sufficient` rows with the citation as evidence, and as assumptions ending in the citation
instead of `— unconfirmed`. The engine also retrieves the constitution and prior decisions for the
idea and records what it found in the Round 0 log, so check that row.

Non-interactive hook runs: `bin/sdd intake start "<idea>" --no-ask` writes
`Status: Draft — needs a session` and returns.

### 2–4. Each round

- The engine picks the round: constitution rows first (project scope), round 1's foundations
  (S1, S2, S3, S9), then impact × uncertainty, then scope → security → experience → technical.
  It asks at most `session.per_round` questions (`.specify/extensions/intake/intake-config.yml`).
- Questions marked *Generic scaffold* in the file were made up by the engine for a row nobody had
  drafted a question for. **Rewrite them to fit the idea before asking**, with
  `bin/sdd intake questions <slug> --replace Q# --json '{…}'`. Keep the row, sharpen the text and
  options. Answered questions are never rewritten.
- Pass `card.questions` to `AskUserQuestion` unchanged; lead with the `progress` line.
- Every fifth round the engine returns a check-in card instead (`kind: "checkin"`); ask it as is.

### 5. Recording

Pass the tool result straight back: `{"answers": {...}, "annotations": {...}}`. The engine:

- ticks options, fills `**Answer**` lines, keeps notes, appends `- Q: … → A: …` clarifications;
- records "you decide" / "Decide during planning" as `Delegated — agent chose <recommended>: <why>`;
- records "not sure" once, asks again next round, and marks the question `Open` the second time;
- stops on "wrap up" / "that's enough" and finishes the intake;
- re-rates every row (a row is never Sufficient while a question feeding it is open) and logs the round.

Between rounds, use your judgment where the engine can't:

| Situation | Command |
|---|---|
| An answer settled another question | `bin/sdd intake resolve <slug> Q5 --by Q2 --reason "…"` |
| An answer opened a new gap | `bin/sdd intake questions <slug> --json '[{…}]'` |
| Evidence is enough even though no question fed the row | `bin/sdd intake rate <slug> S6 Sufficient --evidence "Q3 note"` |
| A default worth recording | `bin/sdd intake assume <slug> "…" [--citation "constitution Art. III"]` |

When the spec rows are nearly settled and unconfirmed assumptions remain, the engine adds the
multi-select assumption check ("Which of these defaults should stay as written?") on its own.

### 6. Finish

The engine sets `Status: Answered` or `Answered — N open items`, turns unsettled rows into one-line
`[NEEDS CLARIFICATION: …]` items, and closes every pending question. You still do step 6 of the
start command yourself: reread the file for contradictions and tool/limit conflicts, refresh the
Working interpretation, then reply with the path and the counts the engine returned.

## Resuming

Sessions survive process exits (LangGraph SQLite checkpoints in `.specify/sessions/`, gitignored).
In a fresh cloud session the checkpoint is gone, but the intake file is the memory: `bin/sdd intake
next <slug>` recomputes the waiting round from the file, and `answer` replays it before recording.
`bin/sdd intake status <slug>` shows the rows.

## Traces and reasoning

Every node writes a decision trace (`.specify/traces/intake-<slug>/trace.jsonl`): decision, rationale
summary, evidence, changed state, next action. Round selection also writes a visible reasoning chain
(`reasoning/round-N-selection.md`) when `reasoning.visible` is on. Traces are the durable record;
reasoning chains explain, they never authorize (Constitution Art. IX).

## Service mode

As a LangGraph service (`from sdd_harness.intake import build_graph`), with `ANTHROPIC_API_KEY` set
(or `SDD_LLM=on`), the draft node asks Claude (`claude-opus-5-5`, adaptive thinking, structured output,
server-side refusal fallback) to write the interpretation, row ratings and question bank from the
idea plus retrieved constitution text. Inside Claude Code the engine stays deterministic and you are
the drafter. See `references/engine.md` for the graph, the state and the file contract.
