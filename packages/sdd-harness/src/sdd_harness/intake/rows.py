"""The sufficiency rows (C1–C6, S1–S10, T1–T6) and a fallback question scaffold for each.

Scaffolds are generic on purpose: they keep a session moving when nobody has drafted idea-specific
questions yet, and they are marked ``generic`` so the host model rewrites them to fit the idea.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class RowDef:
    id: str
    name: str
    group: str  # constitution | spec | plan
    feeds: str
    bar: str
    plain: str  # everyday words for check-in cards
    required_answers: int = 1
    priority: int = 9  # scope 1, security/privacy 2, experience 3, technical 4 (speckit.specify's order)
    scaffold: dict = field(default_factory=dict)
    followups: tuple = ()  # scaffolds for the 2nd, 3rd… answer a row needs


def _opts(*items: tuple[str, str]) -> list[dict]:
    return [{"label": label, "description": desc} for label, desc in items]


ROWS: tuple[RowDef, ...] = (
    RowDef(
        "C1",
        "Purpose & identity",
        "constitution",
        "Project name, preamble",
        "what the project is for and its name",
        "what the project is for",
        priority=1,
        scaffold={
            "header": "Purpose",
            "text": "What is this project for, in one line?",
            "options": _opts(
                ("Internal tool", "Serves your own team's work."),
                ("Product for customers", "Serves people outside your team."),
                ("Research or prototype", "Explores an idea before committing."),
            ),
        },
    ),
    RowDef(
        "C2",
        "Principles",
        "constitution",
        "Core Principles",
        "the 3–5 non-negotiable rules every feature obeys, each with its reason",
        "the rules every feature follows",
        required_answers=1,
        priority=1,
        scaffold={
            "header": "Principles",
            "multi_select": True,
            "text": "Which rules should every feature obey without exception?",
            "options": _opts(
                ("Tests before merge", "No change lands without passing automated tests."),
                ("Human approves risky changes", "Security and data changes wait for a person."),
                ("Plain files in git", "All state lives in versioned text files."),
                ("No secrets in code", "Credentials only come from a secret store."),
            ),
        },
    ),
    RowDef(
        "C3",
        "Quality bar",
        "constitution",
        "Core Principles, quality gates",
        "how work is checked before it counts as done",
        "how work gets checked",
        priority=2,
        scaffold={
            "header": "Quality",
            "text": "What has to pass before a change counts as done?",
            "options": _opts(
                ("Tests and review", "Automated tests plus an independent review."),
                ("Tests only", "Automated tests are the bar; review is optional."),
                ("Manual acceptance", "A person checks the result by hand."),
            ),
        },
    ),
    RowDef(
        "C4",
        "Constraints",
        "constitution",
        "Additional Constraints",
        "technology, security, privacy, compliance or cost rules that bind every feature",
        "limits every feature must respect",
        priority=2,
        scaffold={
            "header": "Limits",
            "text": "Which limits must every feature respect?",
            "multi_select": True,
            "options": _opts(
                ("Fixed tech stack", "Features use the languages and services already chosen."),
                ("Personal data rules", "Personal data is minimized and protected."),
                ("Cost ceiling", "Running costs stay under a set budget."),
                ("No limits yet", "Nothing binds every feature today."),
            ),
        },
    ),
    RowDef(
        "C5",
        "Workflow & approvals",
        "constitution",
        "Development Workflow",
        "which steps need a person's OK, and who reviews",
        "what needs your OK",
        priority=1,
        scaffold={
            "header": "Approvals",
            "text": "What should never happen without your OK?",
            "options": _opts(
                ("Merging to main", "A person approves every merge."),
                ("Risky changes only", "Low-risk changes merge on green checks."),
                ("Releases only", "Merges are automatic; releases need approval."),
            ),
        },
    ),
    RowDef(
        "C6",
        "Governance",
        "constitution",
        "Governance",
        "who may change the constitution and how changes are versioned",
        "who may change the rules",
        priority=3,
        scaffold={
            "header": "Governance",
            "text": "Who may change these project rules?",
            "options": _opts(
                ("Only you", "You approve every amendment; versions bump on each change."),
                ("Any maintainer", "Maintainers amend with a review."),
                ("Team vote", "Changes need agreement from the team."),
            ),
        },
    ),
    RowDef(
        "S1",
        "Problem & context",
        "spec",
        "Input, Assumptions",
        "the pain or opportunity, who feels it, and why now",
        "the problem it solves",
        priority=1,
        scaffold={
            "header": "Problem",
            "text": "What is the main problem this should solve first?",
            "options": _opts(
                ("Saves people time", "Removes a slow or repetitive step."),
                ("Prevents mistakes", "Stops an error that happens today."),
                ("Enables something new", "Makes possible what can't be done now."),
            ),
        },
    ),
    RowDef(
        "S2",
        "People & roles",
        "spec",
        "User Scenarios (actors)",
        "who it serves first, plus every other role that acts and what each may do",
        "who it serves",
        priority=3,
        scaffold={
            "header": "People",
            "text": "Who should the first version serve?",
            "options": _opts(
                ("One person", "A single user working on their own."),
                ("A small team", "Several people sharing the same records."),
                ("Outside customers", "People outside your organization."),
            ),
        },
    ),
    RowDef(
        "S3",
        "Primary journey",
        "spec",
        "User Story 1 (P1), acceptance scenarios",
        "the first journey (confirmed), its steps, why it comes first, and ≥2 confirmed acceptance outcomes",
        "the main thing people do with it",
        required_answers=2,
        priority=3,
        scaffold={
            "header": "Journey",
            "text": "Which journey should the first version get right before anything else?",
            "options": _opts(
                ("Create and track", "Someone adds an item and follows it to done."),
                ("Find and review", "Someone searches existing records and checks them."),
                ("Get notified", "Someone is told when something needs attention."),
            ),
        },
        followups=(
            {
                "header": "Acceptance",
                "text": "When someone finishes the first journey, what should tell them it worked?",
                "options": _opts(
                    ("A confirmation", "An explicit message that the step succeeded."),
                    ("The updated list", "The changed item shows up where they expect it."),
                    ("A notification later", "They hear back once the work is done."),
                ),
            },
        ),
    ),
    RowDef(
        "S4",
        "Later journeys",
        "spec",
        "User Stories P2, P3",
        "the next one or two journeys, ranked, and whether each ships first or later",
        "what comes after",
        priority=1,
        scaffold={
            "header": "Later",
            "text": "What should come after the first journey?",
            "options": _opts(
                ("Nothing yet", "Ship the first journey alone and learn."),
                ("Sharing", "Let other people see or join in."),
                ("Reports", "Summaries of what happened over time."),
            ),
        },
    ),
    RowDef(
        "S5",
        "Capabilities & scope",
        "spec",
        "Functional Requirements (FR-###)",
        "every capability P1/P2 need, each testable, plus what the first release leaves out",
        "what's in and out",
        priority=1,
        scaffold={
            "header": "Scope",
            "text": "What should the first release deliberately leave out?",
            "options": _opts(
                ("Integrations", "No connections to other tools yet."),
                ("Admin settings", "Defaults only; no configuration screens."),
                ("Mobile support", "Desktop or terminal first."),
            ),
        },
    ),
    RowDef(
        "S6",
        "Information",
        "spec",
        "Key Entities",
        "each thing it keeps or produces, its key details and how things relate",
        "what it keeps track of",
        priority=4,
        scaffold={
            "header": "Records",
            "text": "What is the main thing it needs to keep track of?",
            "options": _opts(
                ("Tasks or items", "Things with a status that move to done."),
                ("People", "Profiles, roles and contact details."),
                ("Nothing stored", "It works on inputs and keeps no records."),
            ),
        },
    ),
    RowDef(
        "S7",
        "Trust, privacy & rules",
        "spec",
        "Functional Requirements, Assumptions",
        "who can see and change what, sensitive data, and rules that apply",
        "who can see and change what",
        priority=2,
        scaffold={
            "header": "Access",
            "text": "Who should be able to change the records?",
            "options": _opts(
                ("Owners only", "Each person changes only their own records."),
                ("Any team member", "Everyone on the team can edit."),
                ("Admins approve", "Changes wait for an admin's approval."),
            ),
        },
    ),
    RowDef(
        "S8",
        "Edge cases",
        "spec",
        "Edge Cases",
        "the chosen behavior for at least three of the riskiest failure or boundary cases",
        "what happens when things go wrong",
        required_answers=3,
        priority=3,
        scaffold={
            "header": "Failures",
            "text": "When the same request arrives twice, what should happen?",
            "options": _opts(
                ("Ignore the duplicate", "The second copy changes nothing."),
                ("Warn the person", "Show that it was already done."),
                ("Process both", "Treat each copy as new work."),
            ),
        },
        followups=(
            {
                "header": "Offline",
                "text": "If something is due while the service it relies on is unreachable, what should happen?",
                "options": _opts(
                    ("Retry then warn", "Try again for a while and tell the person if it still fails."),
                    ("Fail right away", "Stop and report the problem immediately."),
                    ("Skip it silently", "Move on and catch up next time."),
                ),
            },
            {
                "header": "Conflicts",
                "text": "If two changes to the same record arrive at once, which one should win?",
                "options": _opts(
                    ("Ask the person", "Show both and let a person choose."),
                    ("Latest wins", "The most recent change replaces the other."),
                    ("Keep both", "Store both versions side by side."),
                ),
            },
        ),
    ),
    RowDef(
        "S9",
        "Success",
        "spec",
        "Success Criteria (SC-###)",
        "≥3 measurable outcomes with numbers and timeframes, including a confirmed headline target",
        "how you'll know it worked",
        required_answers=2,
        priority=3,
        scaffold={
            "header": "Success",
            "text": "Which target should count as success for the first three months?",
            "options": _opts(
                ("Half the time", "The main task takes half as long as today."),
                ("Zero missed items", "Nothing falls through the cracks."),
                ("Weekly use", "Most intended people use it every week."),
            ),
        },
        followups=(
            {
                "header": "Measures",
                "multi_select": True,
                "text": "Which other measures should the first release be judged on?",
                "options": _opts(
                    ("Setup under 5 minutes", "A new person is up and running within five minutes."),
                    ("Under 1 error per month", "Fewer than one reported error each month."),
                    ("Answers within 2 seconds", "Common actions respond within two seconds."),
                ),
            },
        ),
    ),
    RowDef(
        "S10",
        "Constraints & dependencies",
        "spec",
        "Assumptions",
        "time, budget, people, and outside systems or content it relies on",
        "time, budget and outside systems",
        priority=4,
        scaffold={
            "header": "Limits",
            "text": "What does it depend on that you don't control?",
            "multi_select": True,
            "options": _opts(
                ("An outside service", "Another system must be up and reachable."),
                ("A deadline", "It must ship by a fixed date."),
                ("Nothing outside", "It stands alone."),
            ),
        },
    ),
    RowDef(
        "T1",
        "Platform & form",
        "plan",
        "Target Platform, Project Type",
        "where it runs and what kind of thing it is",
        "where it runs",
        priority=4,
        scaffold={
            "header": "Platform",
            "text": "Where should this run: a website, a phone, or inside a tool you already use?",
            "options": _opts(
                ("Decide during planning", "Planning picks the platform within your limits."),
                ("A website", "People use it in a browser."),
                ("Inside an existing tool", "It lives in a tool you already use."),
                ("A command line tool", "It runs in a terminal or a pipeline."),
            ),
        },
    ),
    RowDef(
        "T2",
        "Stack",
        "plan",
        "Language/Version, Primary Dependencies",
        "the languages, frameworks or products to use, or to avoid",
        "the tools it's built with",
        priority=4,
        scaffold={
            "header": "Stack",
            "text": "Is there a language or product it must use or avoid?",
            "options": _opts(
                ("Decide during planning", "Planning researches the stack within your limits."),
                ("Match what we use", "Reuse the languages already in this repository."),
                ("No preference", "Any mainstream choice is fine."),
            ),
        },
    ),
    RowDef(
        "T3",
        "Storage",
        "plan",
        "Storage",
        "where its information lives, or N/A",
        "where records live",
        priority=4,
        scaffold={
            "header": "Storage",
            "text": "Where should its records live?",
            "options": _opts(
                ("Decide during planning", "Planning chooses storage within your limits."),
                ("Files in git", "Plain versioned files in the repository."),
                ("A database", "A managed database service."),
            ),
        },
    ),
    RowDef(
        "T4",
        "Testing",
        "plan",
        "Testing",
        "how the person wants it checked",
        "how it gets tested",
        priority=4,
        scaffold={
            "header": "Testing",
            "text": "How should it be checked before release?",
            "options": _opts(
                ("Automated and manual", "Automated tests plus a hands-on acceptance pass."),
                ("Automated only", "Tests in CI are the bar."),
                ("Manual only", "A person checks it by hand."),
            ),
        },
    ),
    RowDef(
        "T5",
        "Performance & scale",
        "plan",
        "Performance Goals, Scale/Scope",
        "expected users, volume and speed, as numbers",
        "how many people and how fast",
        priority=4,
        scaffold={
            "header": "Scale",
            "text": "How many people will use it in its first year?",
            "options": _opts(
                ("Under 10", "A handful of people."),
                ("10 to 1000", "A team or a small community."),
                ("Over 1000", "A broad audience; speed matters."),
            ),
        },
    ),
    RowDef(
        "T6",
        "Technical constraints",
        "plan",
        "Constraints",
        "hosting, cost, offline, security, accessibility or integration limits",
        "technical limits",
        priority=4,
        scaffold={
            "header": "Tech limits",
            "text": "Which technical limits must it respect?",
            "multi_select": True,
            "options": _opts(
                ("Works offline", "It keeps working without a network."),
                ("Self-hosted", "It runs on infrastructure you control."),
                ("Accessibility", "It meets accessibility guidelines."),
                ("No special limits", "Ordinary hosting and security are enough."),
            ),
        },
    ),
)

BY_ID = {r.id: r for r in ROWS}
GROUP_ORDER = {"constitution": 0, "spec": 1, "plan": 2}
OPENING_ROWS = ("S1", "S2", "S3", "S9")  # round 1's usual foundations


def rows_for(scope: str, software: bool = True) -> list[RowDef]:
    out = [r for r in ROWS if r.group != "constitution" or scope == "project"]
    return out if software else [r for r in out if r.group != "plan"] + [r for r in ROWS if r.group == "plan"]
