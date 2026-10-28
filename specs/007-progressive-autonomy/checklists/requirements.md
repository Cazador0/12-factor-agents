# Specification Quality Checklist: Progressive Autonomy and the Engineering Scorecard

**Purpose**: Validate specification completeness and quality before proceeding to planning
**Created**: 2026-10-22
**Feature**: [spec.md](../spec.md)

## Content Quality

- [x] No implementation details (languages, frameworks, APIs)
- [x] Focused on user value and business needs
- [x] Written for non-technical stakeholders
- [x] All mandatory sections completed

## Requirement Completeness

- [x] No [NEEDS CLARIFICATION] markers remain
- [x] Requirements are testable and unambiguous
- [x] Success criteria are measurable
- [x] Success criteria are technology-agnostic (no implementation details)
- [x] All acceptance scenarios are defined
- [x] Edge cases are identified
- [x] Scope is clearly bounded
- [x] Dependencies and assumptions identified

## Feature Readiness

- [x] All functional requirements have clear acceptance criteria
- [x] User scenarios cover primary flows
- [ ] Feature meets measurable outcomes defined in Success Criteria
- [x] No implementation details leak into specification

## Notes

- **Ticked again: "No [NEEDS CLARIFICATION] markers remain."** The spec's only marker, in SC-004, is resolved by the person's answer "+30% in 3 months (Recommended)" (project intake R5). SC-004 now states it as the target, not as a proposed default: accepted issues per week rise by at least 30% within 3 months of reaching Guarded autonomous mode, compared with the Shadow-mode baseline, at the fixed capacity of "3 agent sessions + 6 subagents + the Jev agent". The guardrails stay (escaped defects, revert rate, security incidents and human recovery cost no worse than their Shadow-mode baselines). Which Shadow-mode windows form the baseline is left to the mode policy and marked inferred. The spec now has 0 markers.
- **Still unticked: "Feature meets measurable outcomes defined in Success Criteria."** The headline target is now the person's, but the other numbers are still labelled "proposed default" and await the owner: SC-002's 24 hours, SC-003's 4-week window and "at most 2 metrics", and SC-005's 40%. The 4-week window and the 20-accepted-issue minimum sample in Assumptions are also proposed defaults, and planning has yet to check that 20 accepted issues per 4 weeks is reachable with one PSE session and one issue in build at a time (R1). Until the owner confirms them, the spec cannot claim to meet confirmed outcomes.
- **Markers resolved:**
  - FR-009: Smokey, a person's account, is the sole approver of promotion to Long-horizon and Self-improving (project intake Q11–Q13). Art. VI is unchanged.
  - FR-017: cost per accepted issue is shown to Smokey and never blocks promotion by itself (project intake Q23).
  - SC-004: the headline target is "+30% in 3 months (Recommended)", with the guardrails kept (project intake R5).
- **Open dependency outside this spec (R7):** once a person makes `lease-epoch` a required check, a pull request whose head a person pushed or made carries no lease epoch, and in Shadow mode the control plane posts no status (spec 001 FR-030, which now lists the post as a consequential action, and FR-038). Spec 001 FR-038 and spec 002 FR-038 carry the open question, as clarification markers, of how such a pull request meets the check. Every such pull request, in any mode, depends on that answer, and so does every merge in Shadow mode. The Assumptions entry "Lease-epoch fences" now says the question is open and decided there; an earlier version wrongly said it was settled and limited it to Shadow mode. This spec adds no marker for it, because the decision belongs to specs 001 and 002.
- **Person's specify-phase answers now applied (project intake, Phase Refinements R1–R8):**
  - R5 resolves SC-004 (above). The Assumptions entry "Numeric targets" now says the headline target is the person's and lists the numbers that are still proposed defaults. US2's priority note points to SC-004.
  - R1 (one session per role, at most one issue in build at a time) was already in Assumptions (Scale, Windows) and SC-004. This round removed what still assumed concurrent builds: the "Duplicate-work incidents" row of FR-013 counted write-set conflicts. With one issue in build, a write-set hold only orders queued work (spec 001 FR-023, FR-035), so a note under the table says holds are not incidents, and the row now counts duplicate issues, competing lease claims and stale-epoch work the fences caught (inferred). That note said "two builds never overlap", which was wrong: a partitioned issue's parts may hold write leases at the same time (spec 001 FR-035, spec 003 FR-011). It now says two issues are never in build at once, and a partitioned issue counts as one. FR-006 says a Self-improving recurring agent is not a fourth session and waits for the one build slot (inferred), and US5 scenario 4 now tests that. FR-006 now also says which sessions may run a recurring agent: one whose PR changes production code or documentation runs in the PSE session or its subagents, or in Lead only under the owner's grant, and Review contributes only test-only changes (spec 003 FR-020) (inferred). Nothing else in the spec assumed two PSE sessions at once.
  - R7 ("Both" fences): FR-004's protected-branch gate covers the `lease-epoch` status once a person makes it a required check. This round corrected four things:
    - FR-004 and US4 scenario 3 had weakened the person's wording to "never merges automatically" / "does not merge automatically". Both now say a stale-epoch head "can never merge", and US4-3 says it cannot merge "automatically or by a person", as the R7 row and spec 001 FR-038 read.
    - FR-004 credited the missing-epoch failure to R7. R7 backs only the stale-epoch rule; the missing-epoch failure (fail closed) and how a head records its epoch come from spec 001 FR-038's inferred design and are now marked inferred. FR-004 also points to the mechanism's limits in specs 001 and 002.
    - The Assumptions entry "Lease-epoch fences" and US4-3 presented the control plane as the poster as if the person had said so. The entry now separates the person's choice (the two fences) from the inferred poster, and US4-3's When clause no longer names the poster; scenario 4 names it with "(the poster is inferred, spec 001 FR-038)".
    - Spec 007 supplies the per-mode rules (spec 001 FR-030, spec 002 FR-024) but never said which modes allow the status post. FR-003 now allows it in Agent implementation mode and every mode above it, and refuses it in Shadow mode (inferred, citing R7), and US4 scenario 4 tests it. FR-008 now makes `lease-epoch` being a required check a criterion for promotion to Guarded autonomous mode (inferred), and US2 scenario 7 tests it; the Assumptions entry records that until a person adds the check, only the person who merges stops a stale-epoch head in Agent implementation mode.
    The spec never called the forge-side fence itself an open question, so there was no such wording to remove. The open question it does carry is a different one: how a person's pull request meets the check (above).
  - R2 (owner approves Lead's implementation-worker switch per issue): the rule now has its own mode-independent requirement, FR-023, instead of sitting under FR-005's Long-horizon rules while claiming to hold "in this mode or any other". FR-023 says Lead never switches itself, reassigning recovered work to Lead needs the owner's grant, and under that grant Lead may act as a PSE would in Agent implementation mode and above, while in Shadow mode the grant changes nothing (inferred). FR-005's header is back to two Long-horizon rules, with a pointer to FR-023. The 003 dependency and the Art. VI line now cite FR-023. US5 scenario 3 tests a reassign to Lead without the grant (refused with "no implementation-worker grant", spec 001 FR-039).
  - R3: the earlier note said FR-002, US1, FR-016 and SC-001 matched spec 002 FR-037 "as they now read". That overclaimed: spec 002 FR-037's "Other modes" rule also applies the human-approved plan write in Agent implementation and Guarded autonomous modes (spec 004 FR-023), and this spec granted it only in Shadow mode. FR-003 now carries that rule (inferred, following spec 002 FR-037), FR-004 points to it, and FR-016's attribution covers it in every mode in which it applies. US1 also contradicted FR-002 and SC-001: its narrative, Independent Test and scenario 1 refused every agent mutation except an approved plan entry, so Jev's comment-and-label writes (labels are consequential under spec 001 FR-030) would have failed the test. All three now exempt Jev's observation writes (FR-002) (inferred).
  - Not applicable: R4 (the gateway's read-only search tools; this spec names no gateway tools), R6 (Jev's durable-progress window; this spec takes Jev's metrics from spec 008 FR-049 and sets no Jev threshold) and R8 (role and summary `jev/*` labels; this spec names no `jev/*` label). Its "parked work items a person resets" in human recovery cost agrees with spec 008 FR-036, under which a parked label stays until a person resets the breaker (FR-033). An earlier version of this note credited that rule to R8, whose answer covers only the role labels and the summary label.
  - Clarifications now hold R1, R2, R3, R5 and R7, each in the form "(project intake, R<n>)". The earlier R1 and R3 lines lacked the comma and were corrected.
- **Automatic demotion (FR-011) and the active-mode record design (FR-018) are proposals.** The report and the constitution describe promotion only, and neither says where the active mode is held. The spec marks these as inferred and records them in the Assumptions entry "Demotion and the active-mode record not confirmed": FR-011, FR-018's separate record and its writer rules, and the demotion edge cases. The owner should confirm them through `/speckit-intake-refine` before planning relies on them. An earlier version of this note said FR-018 was marked inferred when it was not. That is now fixed in the spec.
- **"Requirements are testable" and "All functional requirements have clear acceptance criteria" stay ticked after this round's fixes.** Before them, US1's Independent Test would have failed as soon as Jev recorded a verdict (see R3 above), and FR-005's R2 rule and FR-006's build-slot rule had no acceptance scenario. US1 now exempts Jev's observation writes, and US5 scenarios 3 and 4, US2 scenario 7 and US4 scenario 4 cover FR-023, FR-006, FR-008 and FR-003's status-post rule. Agent implementation mode still has no user story of its own; FR-003's other rules are covered by US2's promotion scenarios and US4 scenario 4 only.
- **"Requirements are testable" was ticked again after earlier fixes.** It was not true in the version before those:
  - The "Wrong stuck verdict" edge case said a wrong verdict counts toward the false-stuck rate and not the stuck rate, which contradicted FR-022 and spec 008 FR-049. It now counts in both, once per episode.
  - "Not applicable" had no closed list, so any metric could read it and SC-003 would still pass. FR-015 now names the Shadow-mode cases (the agent-attributed slices of escaped defects, revert/rollback rate and flaky-test rate). Any other case must be listed in the mode policy.
  - SC-007 required proposal and refusal traces to be linked from the active-mode record, which a refused or pending proposal never writes. FR-020 and SC-007 now link approval and demotion traces from the active-mode record, and proposal and refusal traces from the promotion proposal or request.
  - FR-019 now names who performs the compliance review: Review prepares it and the approving person confirms it (inferred). The blocking rule and the Article VIII handling are marked inferred.
  - FR-016's actors now include the control plane's own `system` actor (spec 001 FR-031). Subagent attribution cites spec 001 FR-034 and is marked inferred.
  - Earlier reasons still hold: "elevated risk" is High and Critical (FR-005, inferred, matching spec 002 FR-025); security incidents and human recovery cost are defined metrics (FR-013); human review time has a named source (FR-017).
- **Jev's metrics:** spec 008 is in `specs/` and defines the three metrics in FR-049. FR-022 now cites FR-049 and follows it: stuck rate is per session with at least one stuck episode, dead sessions are counted separately, and a wrong verdict counts once per episode.
- **Dependencies match the fixed map:**
  - Upstream: 001, 003, 006 and 008. Downstream: none.
  - Specs 002, 004 and 005 are not listed as "Related". Their records reach this spec through its upstreams and spec 009's shared schemas (Assumptions).
  - `specs/README.md` already matches the map: it has rows for 008 and 009, lists 007's upstreams as 001, 003, 006 and 008, and has the 008 → 007 edge.
- **Cross-references corrected:** the gateway's audit records are spec 002 FR-022, and its refusal counts are FR-023 (FR-013 sources).
- **Numeric targets and the mode policy:** thresholds, windows, per-metric minimum samples and demotion limits live in the mode policy (FR-008, FR-012, FR-015). The Success Criteria carry their own numbers. SC-004's headline target is the person's (R5). The numbers labelled as proposed defaults are SC-002's 24 hours, SC-003's 4-week window and "at most 2 metrics", and SC-005's 40%. SC-001, SC-006, SC-007 and SC-008 state 100% or 0, which follow from the requirements and are not labelled proposed defaults. An earlier version of this note said every number other than SC-004's was a proposed default. SC-004's guardrails now compare each row's whole value across all actors, because FR-015 leaves the agent-attributed slices with no Shadow-mode value, and the baseline windows are now listed in the Mode policy entity (both inferred). The Assumptions entry "Numeric targets" no longer says the guardrails apply "whichever target is picked"; R5 has picked it.
- **Escaped-defect target across specs:** spec 006 SC-006 sets the same bound as this spec, at or below the Shadow-mode baseline, and leaves any reduction target to the owner. There is no inconsistency between the two specs. An earlier note said spec 006 proposed a 25% fall; it does not.
- The scorecard has 22 metrics:
  - the report's 17;
  - security incidents and human recovery cost, from the report's target sentence;
  - stuck rate, false-stuck rate and recovery success, from spec 008.
