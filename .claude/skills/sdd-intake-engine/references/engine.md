# Intake engine internals

## Graph (`sdd_harness/intake/graph.py`)

```
START ─┬─ ground ─ draft ─ plan_round ─┬─ ask (interrupt) ─ record ─┐
       └───────────────────┘           │            ▲               │
                                       └─ finish    └── plan_round ─┘
```

| Node | Does | Writes |
|---|---|---|
| `ground` | Hybrid retrieval (BM25 + hashing vectors, RRF) over the constitution, `AGENTS.md`, `.agents/*.md` for the idea | citations into state |
| `draft` | Host draft JSON, or a Claude draft in service mode; renders the template | `intake.md` (Draft), Round 0 log, trace `D-01` |
| `plan_round` | Re-rates rows, adds scaffolds for rows with no open question, ranks, picks ≤ `per_round`; check-in every `checkin_every` rounds; assumption check near the end | new scaffolds into the file, reasoning `round-N-selection.md`, trace |
| `ask` | `interrupt(payload)` → the caller shows the cards | — |
| `record` | Reads answers onto options, records in place, re-rates, logs | question blocks, clarifications, row cells, log row, Status, trace |
| `finish` | Unsettled rows → `Open` items; pending questions → `Open`; Status | Open Items, Status, trace |

`START` routes straight to `plan_round` when the state already names an existing intake file, which is
how a fresh process resumes without a checkpoint.

## File contract

The file follows `.specify/extensions/intake/templates/intake-template.md`. The engine parses:

- `**Status**`, `**Scope**`, `**Feature**`, `**Slug**`, `**Created**`, `**Idea type**` lines;
- the three row tables (`#`, `Row`, `Status`, `Evidence`, `Still needed`);
- question headings `### Q# · Header · Row · impact X × uncertainty Y`, option lines
  `- [x] **A. Label** — implication *(Recommended: why)*`, `- [ ] **Other**: …`, `**Answer**: …`,
  `**Note**: …`, `*Multi-select.*`, `*Generic scaffold …*`;
- `- Q: … → A: …` clarification lines, the Session Log table and Open Items bullets.

Edits are in place: a question block, a table row, a log row or a bullet at a time. `## Phase
Refinements` belongs to the refine engine and is never touched here.

## Sufficiency rules (`sufficiency.py`)

- Answers needed per row: S3 two (journey + acceptance), S8 three (edge cases), S9 two, others one.
- Any pending or "not sure" question on a row keeps it `Partial`.
- All settling answers delegated → `Delegated`. "Not sure" twice → question `Open`, row `Open`.
- Evidence that is not a question reference (constitution article, prior decision, source document)
  is preserved and counts as one answer.

## Answer reading (`cards.py`)

Labels match with or without the `(Recommended)` suffix; letters `A`–`D` also work; multi-select
answers split on commas (labels never contain commas). Free text is `Other` verbatim, unless it is a
delegation ("you decide", "your call", "decide during …"), an unknown ("not sure", "don't know",
"skip") or a stop ("that's enough", "wrap up").
