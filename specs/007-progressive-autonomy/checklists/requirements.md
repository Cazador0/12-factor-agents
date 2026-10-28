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

- [ ] No [NEEDS CLARIFICATION] markers remain
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

- **Unticked: "No [NEEDS CLARIFICATION] markers remain."** One marker remains, in SC-004. It asks for the headline target. The report and the project intake set no number or timeframe (row S9), and the intake's open item names spec 007 as the place to settle it. The proposed default (30% more accepted issues per week within 3 months of Guarded autonomous, measured against the Shadow-mode baseline) stays beside the marker. It is now measured with one session per role and at most one issue in build at a time (project intake R1). Resolve it with `/speckit-clarify` or `/speckit-intake-refine specify`.
- **Unticked: "Feature meets measurable outcomes defined in Success Criteria."** The outcomes are measurable, but their numbers are not confirmed. The headline target is still open (SC-004 marker). The other numbers are labelled "proposed default" and await the owner: SC-002's 24 hours, SC-003's 4-week window and "at most 2 metrics", and SC-005's 40%. Until the owner confirms them, the spec cannot claim to meet confirmed outcomes.
- **Markers resolved:**
  - FR-009: Smokey, a person's account, is the sole approver of promotion to Long-horizon and Self-improving (project intake Q11–Q13). Art. VI is unchanged.
  - FR-017: cost per accepted issue is shown to Smokey and never blocks promotion by itself (project intake Q23).
- **Person's specify-phase answers now applied:**
  - R3 changes FR-002: in Shadow mode a person may approve the bridge's dry-run plan, and the gateway carries out that plan's writes as human-approved writes. Every other agent mutation is still refused. US1, its scenarios, FR-016 attribution and SC-001 follow it, and it matches spec 002 FR-024 and FR-037. The answer is in Clarifications.
  - R1 (one session per role, at most one issue in build at a time) is recorded in Assumptions (Scale, Windows) and in SC-004's proposed default as the limit on throughput and sample size. It is in Clarifications.
- **Automatic demotion (FR-011) and the active-mode record design (FR-018) are proposals.** The report and the constitution describe promotion only, and neither says where the active mode is held. The spec marks these as inferred and records them in the Assumptions entry "Demotion and the active-mode record not confirmed": FR-011, FR-018's separate record and its writer rules, and the demotion edge cases. The owner should confirm them through `/speckit-intake-refine` before planning relies on them. An earlier version of this note said FR-018 was marked inferred when it was not. That is now fixed in the spec.
- **"Requirements are testable" is ticked again after these fixes.** It was not true in the previous version:
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
- **Numeric targets and the mode policy:** thresholds, windows, per-metric minimum samples and demotion limits live in the mode policy (FR-008, FR-012, FR-015). The Success Criteria carry their own numbers, which are labelled as proposed defaults.
- **Escaped-defect target across specs:** spec 006 SC-006 sets the same bound as this spec, at or below the Shadow-mode baseline, and leaves any reduction target to the owner. There is no inconsistency between the two specs. An earlier note said spec 006 proposed a 25% fall; it does not.
- The scorecard has 22 metrics:
  - the report's 17;
  - security incidents and human recovery cost, from the report's target sentence;
  - stuck rate, false-stuck rate and recovery success, from spec 008.
