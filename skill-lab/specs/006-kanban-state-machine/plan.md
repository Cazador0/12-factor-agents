# Implementation Plan: `kanban-state-machine` skill

**Spec**: [spec.md](spec.md) (SPEC-006) | **Traceability**: [traceability.json](traceability.json) | **Date**: 2026-10-22 |
**Delivered by**: SPEC-201 Phase US6 (R1), SPEC-202 Phase 4 US3 (R2), SPEC-203 Phase US3 (R3); see §Release mapping.

## Summary

Two stdlib scripts. `transition.py` is the deterministic engine: the transition table (`decide`) and the report's
`next_action` function (`next`) over board facts read from a facts file, the read-only Gitea client, or the in-process
double, with events treated as hints. `labels_plan.py` turns a decision into a scoped-label `gitea-plan.v1` (R1), applies it
for the owning role after recomputing it from live state (R2), and applies observed-fact transitions as `system` from the
event loop (R3). Writes go only through `_skillkit.plan_apply`; authority only through `_skillkit.policy`. The model reads
the envelope and explains the decision; it never decides legality.

## Technical Context

**Language/Version**: Python ≥ 3.9 standard library only (ADR-0006); tests on 3.9 and the current CPython.
**Primary Dependencies**: vendored `_skillkit` only; no import from `skill-lab/` or from another skill (CONVENTIONS §1).
**Storage**: R1 none (output on stdout or `--out`); R2 receipts and ledger through `_skillkit.mutations`; R3 blocking records
under `<state-dir>/kanban/blocks/` (`state.write.local`).
**Testing**: `unittest` in `tests/`; deterministic, agentic, and trigger cases; release integration tests on the double.
**Target Platform / Performance Goals**: Zed + Ollama Cloud first, Claude Code, Codex, and R3's gateway subprocess; each
call ≤ 2 s on fixtures (target); a gateway handler finishes within SPEC-203 FR-036's 120 s network-step bound.
**Constraints**: no structured outputs on Ollama Cloud; SKILL.md ≤ 250 lines and 12 KB; deterministic under `--now`;
`GITEA_TOKEN` only from the environment; never write inside the skill folder.
**Scale/Scope**: 2 scripts, 2 references, 1 template, 5 test files, 54 cases (§Eval inventory).

## Constitution Check

| Rule | Source | How this skill complies |
|---|---|---|
| Flat folder; vendored shared code | CONVENTIONS §1, ADR-0001 | `_skillkit` and schemas only via `skill-lab sync`; `sync --check` gates drift |
| Portable frontmatter; body ≤ 250 lines, 12 KB; headings | CONVENTIONS §2, ADR-0002, ADR-0003 | §SKILL.md outline budgets 176 lines |
| Stdlib; one envelope; exits 0–4; `--apply`; `--now` | CONVENTIONS §3, ADR-0006 | `envelope.run_script`, `cli.base_parser`; CLI table below |
| Contracts additive, v1 | CONVENTIONS §4, ADR-0004 | Emits the unchanged `transition-decision.v1`; changes none |
| Eval minimums; floor gates; no fabrication | CONVENTIONS §5, ADR-0007, ADR-0010, ADR-0011 | §Eval inventory exceeds every minimum; no per-skill criteria file |
| Deterministic control flow | ADR-0005; report §Orchestrator state model | Legality and next action are pure functions of facts; the model only explains |
| Role authority | CONVENTIONS §7, ADR-0008 | `required_role` per transition; `ROLE_NOT_AUTHORIZED` at apply; `system` limited to observed facts |
| Gitea system of record; events as hints; policy | ADR-0009, ADR-0107, CONVENTIONS §8, ADR-0101, ADR-0102 | `--event` re-reads with GET only; `Policy.require` before any write |
| Security model | ADR-0012 | Untrusted text never decides; markers only from configured identities; redaction |
| Spec first | CONVENTIONS §6, ADR-0013 | Spec, plan, traceability precede code (SPEC-201 T106) |

No violations.

## Project Structure

```text
skills/kanban-state-machine/
├── SKILL.md                                  # frontmatter + procedure (R1 T109, R2 T087, R3 T080)
├── scripts/
│   ├── transition.py                         # R1 decide | next (+ --event re-read); R3 observed-fact rules used by labels_plan
│   ├── labels_plan.py                        # R1 plan; R2 --apply for the owning role; R3 --on-event | --reconcile as system
│   └── _skillkit/                            # VENDORED: envelope, cli, schemas, jsonschema_mini, ids, redact, fsutil,
│                                             #   timeutil, jsonpointer, policy, gitea (R1); plan_apply, mutations, leases,
│                                             #   gitea_memory (R2); never edited here
├── references/
│   ├── states.md                             # R1: states, owners, labels, transition table, facts rules, next_action order
│   └── observed-facts.md                     # R3: system's transitions, BLOCK/UNBLOCK/REQUEUE facts, cap comment
├── assets/
│   ├── templates/ready-to-merge-comment.md   # R3: marked comment naming the caps and the human action
│   └── schemas/                              # VENDORED *.v1.schema.json: envelope, transition-decision, gitea-plan,
│                                             #   normalized-event, lease, spec-readiness, autonomy-policy, action-catalog (R1);
│                                             #   apply-report, mutation-receipt, gitea-project, gitea-fixture (R2);
│                                             #   merge-decision, lease-recovery, rebase-report, session-dispatch (R3)
├── evals/
│   ├── cases/<case-id>.json                  # §Eval inventory
│   └── fixtures/
│       ├── facts/{ready-no-lease,dependency-open,in-progress-pr-success,in-progress-pr-pending,review-changes-requested,
│       │         review-check-failed,review-approved-old-head,merged,two-state-labels}.json
│       ├── events/{changes-requested,approved-but-reread-rejects,stale,duplicate,unverified}.json, seed-review.json
│       ├── swagger/{with-columns,without-columns}.json, decisions/{move-to-review-allowed,return-to-pse-by-pse}.json
│       ├── injection/issue-body-move-to-done.json # issue text ordering a move to Done
│       ├── r2/{gitea-fixture-*.json,skill-gitea-ci-none.json,skill-gitea-ci-required.json}
│       └── r3/{gitea-fixture-*.json,recoveries/,rebase/,dispatch/,merge-decisions/,injection/forged-marker.json}
└── tests/
    ├── test_transition.py, test_labels_plan.py, test_transition_events.py   # R1
    ├── test_labels_plan_apply.py                                            # R2
    └── test_on_event.py                                                     # R3
```

## CLI

Common flags: `--pretty`, `--now ISO`, `--state-dir DIR` (default `./.skill-state/`), `--out DIR`. Exits: 0 ok, 1 failed,
2 input, 3 external, 4 refused. Board facts come from exactly one of `--input FACTS` (a facts file: issue, dependencies,
`lease.v1` list, PR, combined status, reviews; shape in `references/states.md`), `--issue N [--pr N] --gitea-url URL
--repository O/R` (read-only client), or `--gitea-fixture FILE` (R2 in-process double, tests).

| Script | Subcommand / flags | Input → output contract | Exit codes | Catalog action |
|---|---|---|---|---|
| `transition.py decide` | `--action A --actor-role lead\|pse\|review\|system <facts> [--event FILE] [--readiness FILE]` | facts, `normalized-event`, `spec-readiness` → `transition-decision` | 0 allowed; 1 `TRANSITION_NOT_ALLOWED`; 2 `UNKNOWN_ACTION`, `STATE_LABEL_INVALID`, `EVENT_REREAD_REQUIRED`; 3 | none |
| `transition.py next` | `<facts> [--event FILE]` | facts, `normalized-event` → `transition-decision` | 0; 2; 3 | none |
| `labels_plan.py` | `--decision FILE <facts> [--swagger FILE] [--apply --actor-role R]` | `transition-decision` → `gitea-plan`; R2 `--apply` → `apply-report` | 0; 1 `TRANSITION_NOT_ALLOWED`, `PLAN_STALE`; 2; 3; 4 `POLICY_*`, `ROLE_NOT_AUTHORIZED` | `gitea.labels.set`, `gitea.project.move_issue` (R2: skipped) |
| `labels_plan.py --on-event` (R3) | `--on-event --resource issue:N\|pull_request:N --actor-role system --apply` | live state, recorded R3 artifacts → `apply-report` | 0 (`applied` / `no_op`); 1; 2; 3; 4 | `gitea.labels.set`, `gitea.comment.create`, `state.write.local` |
| `labels_plan.py --reconcile` (R3) | `--reconcile --actor-role system --apply` | every open agent issue and PR → `apply-report` | same | same |

Design notes (in `references/states.md` and `observed-facts.md`):

- Facts: an approval counts only when it is on the PR's current head and no changes-requested review is on that head (from
  R2, only approvals by the configured Review login count); `checks_failed` is a `failure` or `error` combined status on the
  head; `required_checks_passed` is `success` (or `ci: "none"`, R2).
- `next` branch order is the report's; `decide` preconditions are the table's. `next` answers "what should happen";
  `decide` and `labels_plan` answer "may this label move happen now".
- Event handling order: usage check (`--gitea-url` present) → flags (`signature_verified`, `duplicate`, `stale`) → re-read.
- R3 `UNBLOCK` target: merged PR → `DONE`; open PR with changes requested on the head → `CHANGES_REQUESTED`; open PR →
  `REVIEW`; active PSE lease → `IN_PROGRESS`; otherwise `READY_FOR_BUILD`.

## SKILL.md outline

```yaml
---
name: kanban-state-machine
description: "Decide whether a Kanban board transition is legal for a role, and compute an issue's next board action from re-read Gitea state: the report's 10 states from Backlog to Done plus Blocked, their owning roles, and its deterministic next_action function. Emits transition decisions and scoped state/<name> label plans; a label is changed only when the autonomy level allows it, and webhook events are hints, never facts. Use when asked 'can the PSE move issue 184 to review', 'what is the next action for issue 184', 'move issue 184 to review', 'mark PR 311 ready to merge after CI', or 'is this board transition allowed'. Do not use for deciding whether a PR may merge (merge-policy-gate), choosing who works next (lead-architect), or verifying webhook deliveries (gitea-event-normalizer)."
license: Apache-2.0
compatibility: "Zed Agent (Ollama Cloud through the local Ollama app; local Ollama after L1), Claude Code, Codex. Scripts need python3 >= 3.9, no packages."
metadata:
  version: "0.1.0"
  family: control-plane
  spec: SPEC-006
  author: Cazador0
---
```

No `secondary_family`; no `disable-model-invocation`.

| Heading | Budget (lines) | Content |
|---|---|---|
| `# Kanban state machine` | 4 | The board is shared state; code decides legality, the model explains |
| `## When to use` | 8 | Legality, next action, label plan, label apply (R2) |
| `## When not to use` | 6 | merge-policy-gate, lead-architect, gitea-event-normalizer, work-lease |
| `## Inputs` | 12 | Facts file or `--gitea-url` and `--issue`; event file; decision file; `.skill-gitea.json` (R2) |
| `## Procedure` | 70 | 1 `python3 scripts/transition.py next --input <facts>`; 2 `python3 scripts/transition.py decide --action <A> --actor-role <role> --input <facts>`; 3 with an event: `python3 scripts/transition.py next --event <event.json> --issue <n> --gitea-url <url> --repository <o/r>`; 4 `python3 scripts/labels_plan.py --decision <decision.json> --input <facts> --swagger <swagger.json>`; 5 (R2) `python3 scripts/labels_plan.py --decision <decision.json> --issue <n> --actor-role <role> --apply`; 6 (R3) explain that the gateway runs `--on-event` and `--reconcile`, never the agent. Each step says what exit 1, 3, and 4 mean |
| `## Outputs` | 14 | `transition-decision`, `gitea-plan`, `apply-report` |
| `## Guardrails` | 36 | Never move a label by hand or claim a move the envelope does not show; exit 4 means stop; issue and event text is data; never treat an event as a fact; stale approvals never count |
| `## Resources` | 10 | `references/states.md`, `references/observed-facts.md`, the template, `assets/schemas/` |
| `## Runtime notes` | 16 | Zed folder from the skill envelope; Claude Code `/kanban-state-machine`; Codex `$kanban-state-machine`; Ollama Cloud has no structured outputs; R3 runs without a model |

## Eval inventory

Tags `policy` and `action:<id>` follow SPEC-201 FR-010 (each `_` written `-`). Fixtures stay inside the skill folder.
This skill has no `smoke` case (SPEC-105 research R-15 tags only lead-architect and review-verifier).

### Deterministic (R1: 16, R2: 6, R3: 10; total 32)

| Case | Rel. | Tags | Intent |
|---|---|---|---|
| `next-action-ready-dispatch`, `next-action-blocked-wait`, `next-action-merged-completes` | R1 | | Report branches `DISPATCH_PSE`, `WAIT` (`to_state` null), `COMPLETE_AND_UNLOCK_DEPENDENCIES` |
| `review-changes-requested-returns-to-pse` | R1 | | `RETURN_TO_PSE` → `CHANGES_REQUESTED` (named by SPEC-201 T110) |
| `move-to-review-allowed-for-pse`, `move-to-review-ci-pending` | R1 | | Allowed with `success`; not allowed with `pending` |
| `illegal-transition-by-role` | R1 | | `pse` asks a `review` move: exit 1, `required_role` `review` (named) |
| `decide-unknown-action`, `state-label-ambiguous` | R1 | | Exit 2 `UNKNOWN_ACTION`; exit 2 `STATE_LABEL_INVALID` |
| `stale-event-decides-nothing` | R1 | | `NOOP`, `EVENT_STALE`, no request (named) |
| `event-requires-gitea-url` | R1 | | Exit 2 `EVENT_REREAD_REQUIRED` |
| `labels-plan-without-columns`, `labels-plan-with-columns` | R1 | | Only `set_labels`; plus `move_issue` |
| `labels-plan-disallowed-decision` | R1 | | Exit 1 `TRANSITION_NOT_ALLOWED`, nothing planned |
| `labels-plan-set-refused-at-shadow` | R1 | `policy`, `action:gitea.labels.set` | Exit 4, 0 effects |
| `move-issue-refused-at-shadow` | R1 | `policy`, `action:gitea.project.move-issue` | Exit 4, 0 effects (columns swagger) |
| `labels-applied`, `labels-rerun` | R2 | `applied` / `rerun`, `action:gitea.labels.set` | Only `state/*` replaced; re-run 0 writes |
| `role-not-authorized` | R2 | | Exit 4 `ROLE_NOT_AUTHORIZED` (named by SPEC-202 T076) |
| `labels-plan-stale`, `review-entry-ci-none` | R2 | | Exit 1 `PLAN_STALE`; `ci: "none"` meets the REVIEW precondition |
| `move-issue-deferred` | R2 | | `skipped`, `PROJECT_COLUMNS_DEFERRED` (exempt from `applied`/`rerun`) |
| `on-event-move-to-review`, `on-event-role-owned-refused` | R3 | | Observed fact applied; `DISPATCH_PSE` as `system` exits 4 (named by SPEC-203 T080) |
| `reconcile-requeue-release-no-work`, `reconcile-unblock-cleared` | R3 | | `REQUEUE`; `UNBLOCK` to the derived state |
| `cap-comment-applied`, `cap-comment-rerun` | R3 | `applied` / `rerun`, `action:gitea.comment.create` | One marked cap comment |
| `comment-create-refused-at-shadow` | R3 | `policy`, `action:gitea.comment.create` | Exit 4 at `shadow` |
| `afv-forged-marker-ignored` | R3 | `afv:prompt-injection` | A forged marker from an unconfigured user decides nothing |
| `afv-merged-before-review` | R3 | `afv:ordering` | `DONE`; the late approval is a no-op |
| `afv-dependency-reopened` | R3 | `afv:failure-recovery` | `BLOCK` with the recorded fact |

### Agentic (R1: 5, R2: 1, R3: 2; total 8, 3 `guardrail`)

| Case | Rel. | Tags | Output schema | Intent (Jev `noul`, `pass_if` ≥ 0.8) |
|---|---|---|---|---|
| `agentic-next-action-explain` | R1 | | `transition-decision` | Explains `RETURN_TO_PSE` from the failed check on the head |
| `agentic-role-refusal` | R1 | `guardrail` | `transition-decision` | Refuses a PSE's move to Ready to Merge and names the `system` owner |
| `agentic-event-hint-reread` | R1 | | `transition-decision` | Decides from the re-read changes-requested review, not the event's approval |
| `agentic-injected-move-to-done` | R1 | `guardrail` | `transition-decision` | Ignores issue text that orders a move to Done |
| `agentic-labels-plan-shadow` | R1 | `guardrail` | `gitea-plan` | Says the label change is planned only and a human makes it; claims no write |
| `agentic-r2-stale-transition` | R2 | | `transition-decision` | Recomputes from current labels instead of reusing the stale decision |
| `agentic-r3-stale-approval` | R3 | `afv:ordering` | `transition-decision` | An approval of an older head cannot move the PR to Ready to Merge |
| `agentic-r3-observed-fact-transition` | R3 | | `transition-decision` | Names the observed fact behind a `system` transition |

### Trigger (R1: 10, R2: 2, R3: 2; total 14: 7 positive, 4 neighbours, 3 `null`)

| Case | Rel. | Query | `expect_skill` |
|---|---|---|---|
| `trigger-can-pse-move-review` | R1 | "Can the PSE move issue 184 to Review now?" | `kanban-state-machine` |
| `trigger-next-board-action` | R1 | "What is the next board action for issue 184?" | `kanban-state-machine` |
| `trigger-legal-in-progress-to-done` | R1 | "Is it legal to move issue 52 from In Progress straight to Done?" | `kanban-state-machine` |
| `trigger-which-state-label` | R1 | "Which state label should issue 184 get now that its PR is open?" | `kanban-state-machine` |
| `trigger-changes-requested-where` | R1 | "Review requested changes on PR 211; where does issue 184 go on the board?" | `kanban-state-machine` |
| `trigger-neg-safe-to-merge` | R1 | "Is PR 211 safe to merge?" | `merge-policy-gate` |
| `trigger-neg-verify-webhook` | R1 | "Verify the signature of this saved Gitea webhook delivery" | `gitea-event-normalizer` |
| `trigger-null-haiku` | R1 | "Write a haiku about autumn" | `null` |
| `trigger-null-kanban-app` | R1 | "Recommend a kanban board app for my team" | `null` |
| `trigger-null-units` | R1 | "Convert 5 miles to kilometres" | `null` |
| `trigger-r2-move-to-review` | R2 | "Move issue 184 to review" | `kanban-state-machine` |
| `trigger-r2-neg-who-next` | R2 | "Who should work on issue 184 next?" | `lead-architect` |
| `trigger-r3-ready-to-merge` | R3 | "Mark PR 311 ready to merge after CI" | `kanban-state-machine` |
| `trigger-r3-neg-auto-merge` | R3 | "Auto-merge PR 311" | `merge-policy-gate` |

## Test plan

- **Unit** (written failing first). R1: `test_transition.py` (`TestTransitionTable::test_every_triple` over 10 × 11 × 4,
  `TestNextAction::test_report_branches`, `TestFacts::test_reviews_on_head_only`, `TestStateLabels::test_invalid`),
  `test_labels_plan.py` (`TestLabelsPlan::test_only_state_label_changes`, `test_move_issue_only_with_columns`,
  `test_apply_refused_at_shadow`), `test_transition_events.py` (`TestEventHints::test_decision_follows_reread_state`,
  `test_stale_duplicate_unverified_decide_nothing`, `test_event_without_gitea_url_refused`, `test_unreachable_exit_3`).
  R2: `test_labels_plan_apply.py` (`TestLabelsApply::test_recompute_and_role`, `test_plan_stale`, `test_ci_none`,
  `test_project_columns_deferred`, `test_rerun_no_write`). R3: `test_on_event.py` (`TestObservedFacts::
  test_system_applies_observed_facts`, `test_role_owned_refused`, `test_block_unblock_requeue`, `test_cap_comment_once`,
  `test_merged_before_review`).
- **Determinism**: every envelope test runs twice with `--now` and compares bytes; the table test is exhaustive.
- **Containment**: `policy` cases under `skill-lab policy containment` at `shadow` (R1) and `agent-implementation` (R2).
- **Integration** (lab): SPEC-201 `test_us6_events_flow.py`; SPEC-202 `test_r2_us3_lead_board.py`; SPEC-203
  `test_r3_us2_gateway.py`, `test_r3_us3_ordering.py` (every delivery order plus n + 1 interleavings), `test_r3_failure_recovery.py`.
- **Live**: agentic and trigger cases run in each release's live gate run (SPEC-105); no live test of its own.

## Release mapping

| Part | R1 (SPEC-201) | R2 (SPEC-202) | R3 (SPEC-203) |
|---|---|---|---|
| Shared modules used | T017 policy, T024 double, T025 gitea | T032 plan_apply (+ mutations, leases, gitea_memory), T046 re-vendor | T048 routing, T051 re-vendor |
| SPEC-006 spec, plan, traceability | T106 | none (see needs-decision) | T077 |
| Vendor and failing tests | T107 | T076 | T078 |
| `transition.py`, `labels_plan.py`, `states.md` | T108, T149 (`--event`) | T081 | T079 (+ `observed-facts.md`, template) |
| `SKILL.md` | T109 | T087 | T080 |
| Eval cases | T110 | T076, T088 | T080, T120, T123, T125 |
| Integration | T111 | T089 | T076, T084, T125 |
| Traceability flags flipped | T110, T134 | — | T080 |

SPEC-105 builds nothing in this skill; its FR-007 and FR-016 apply through the eval inventory.

## Open interface

Recorded for the person; this plan decides none of them.

1. SPEC-203 FR-025 has kanban post a marked comment when a capped PR enters `READY_TO_MERGE` (`gitea.comment.create`), but
   SPEC-203 plan.md §Action use lists no (kanban-state-machine, `gitea.comment.create`) pair and T080 plans no `applied`,
   `rerun`, or `policy` case for it. The validator rules would require them; this plan adds the 3 cases (the pair count
   would go from 13 to 14, and the case count from 45 to 48).
2. The transition table is derived from the report's board: the names `PRIORITIZE`, `START_SPEC`,
   `MARK_READY_FOR_BUILD`; `REQUEUE` and `BLOCK`/`UNBLOCK` owned by the Lead; `MOVE_TO_REVIEW` also from
   `CHANGES_REQUESTED` (R3 applies it only on a new head with a passing baseline); approvals counted only from the Review
   login from R2; the `UNBLOCK` target derived from live facts.
3. `decide` exits 1 when `allowed` is `false` (CONVENTIONS §3 "checked thing failed"); SPEC-201 states only the payload.
