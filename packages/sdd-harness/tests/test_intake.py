"""Intake engine: draft, cards, rounds, sufficiency, finish, and the LangGraph session."""

from __future__ import annotations

from pathlib import Path

import pytest
from langgraph.checkpoint.memory import InMemorySaver
from langgraph.types import Command

from sdd_harness.config import Settings
from sdd_harness.intake import document as doc
from sdd_harness.intake import session
from sdd_harness.intake.cards import lint_card, read_answer, to_card
from sdd_harness.intake.graph import build_graph
from sdd_harness.intake.model import Option, Question

IDEA = "an app that reminds me to water my plants"


def _q(**kw) -> Question:
    base = dict(
        id="Q1",
        header="People",
        row="S2",
        text="Who should the first version serve?",
        options=[
            Option(label="One person", description="Just me.", recommended=True, why="simplest"),
            Option(label="A small team", description="Shared records."),
        ],
    )
    return Question(**{**base, **kw})


def test_slug_and_redaction():
    assert session.slugify("An app that reminds me to water my plants") == "reminds-water-plants"
    assert session.normalize_slug("../My Slug!") == "my-slug"
    red = session.redact("token=abc123 https://bob:pw@host/x sk-ant-abcdefghijklmnopqrstu")
    assert "abc123" not in red and "pw@" not in red and "sk-ant-abc" not in red


def test_card_lint_rules():
    good = to_card(_q())
    assert good["options"][0]["label"].endswith("(Recommended)")
    assert lint_card(good) == []
    bad = {
        "question": "Target audience",
        "header": "A very long header",
        "options": [{"label": "Other", "description": ""}],
    }
    problems = " ".join(lint_card(bad))
    for frag in ("ending with '?'", "1–12 characters", "2–4 options", "no hand-made 'Other'", "implication"):
        assert frag in problems


def test_read_answer_maps_labels_delegation_and_unknowns():
    q = _q()
    assert read_answer(q, "One person (Recommended)").letters == ["A"]
    assert read_answer(q, "you decide").state == "delegated"
    assert read_answer(q, "not sure").state == "unknown"
    other = read_answer(q, "my 12 houseplants")
    assert other.state == "other" and other.words == "my 12 houseplants"
    multi = _q(multi_select=True)
    assert read_answer(multi, "One person, A small team").letters == ["A", "B"]


def test_render_parse_roundtrip(project):
    path, problems = session.create(Settings.load(project), IDEA)
    assert problems == []
    text = path.read_text()
    intake = doc.parse(text)
    assert intake.scope == "feature" and intake.feature == "pending"
    assert intake.idea == IDEA and intake.status == "Draft"
    assert {r.id for r in intake.rows} >= {"S1", "S10", "T6"} and not any(r.id.startswith("C") for r in intake.rows)
    assert intake.session_log[0]["Round"] == "0"
    assert doc.parse(doc.render(intake)).model_dump() == intake.model_dump()


def test_project_scope_when_constitution_is_a_template(project):
    (project / ".specify/memory/constitution.md").write_text("# [PROJECT_NAME] Constitution\n")
    path, _ = session.create(Settings.load(project), "a team wiki")
    assert any(r.id == "C1" for r in doc.parse(path.read_text()).rows)


def test_never_overwrites_an_intake(project):
    s = Settings.load(project)
    a, _ = session.create(s, IDEA, slug="plants")
    b, _ = session.create(s, IDEA, slug="plants")
    assert a.parent.name == "plants" and b.parent.name == "plants-2"


def test_round_record_and_sufficiency(project):
    s = Settings.load(project)
    path, _ = session.create(s, IDEA)
    plan = session.plan_round(s, path)
    assert plan.kind == "questions" and len(plan.questions) == 4
    assert {q.row for q in plan.questions} == {"S1", "S2", "S3", "S9"}  # round 1 foundations
    answers = {
        plan.questions[0].text: "Prevents mistakes",
        plan.questions[1].text: "One person (Recommended)",
        plan.questions[2].text: "you decide",
        plan.questions[3].text: "not sure",
    }
    result = session.record(s, path, plan, answers, {plan.questions[1].text: "just me and 12 plants"})
    assert result["answered"] == 3
    intake = doc.parse(path.read_text())
    rows = {r.id: r for r in intake.rows}
    assert rows["S1"].status == "Sufficient" and rows["S2"].status == "Sufficient"
    assert rows["S3"].status == "Partial"  # delegated once, but the journey row needs two answers
    assert rows["S9"].status == "Missing"  # "not sure" settles nothing; it is asked again next round
    q2 = intake.question(plan.questions[1].id)
    assert q2.note == "just me and 12 plants" and q2.chosen == ["A"]
    assert intake.question(plan.questions[2].id).answer.startswith("Delegated — agent chose")
    assert any(c.endswith("→ A: Prevents mistakes") for c in intake.clarifications)
    assert any("One person — note: just me and 12 plants" in c for c in intake.clarifications)
    assert intake.status == "In session (round 1)"
    nxt = session.plan_round(s, path)
    assert plan.questions[3].id in [q.id for q in nxt.questions]  # the unknown gets a second try
    texts = [q.text for q in doc.parse(path.read_text()).questions if q.row == "S3"]
    assert len(texts) == len(set(texts))  # the follow-up is a new question, never a re-ask


def test_unknown_twice_becomes_open_and_finish_lists_it(project):
    s = Settings.load(project)
    path, _ = session.create(s, IDEA)
    for _ in range(2):
        plan = session.plan_round(s, path)
        target = next(q for q in plan.questions if q.row == "S1")
        session.record(s, path, plan, {target.text: "don't know"})
    intake = doc.parse(path.read_text())
    assert intake.question(target.id).state == "open"
    out = session.finish(s, path)
    assert out["status"].startswith("Answered — ")
    final = doc.parse(path.read_text())
    assert any("NEEDS CLARIFICATION" in o for o in final.open_items)
    assert all(q.state not in {"pending", "unknown"} for q in final.questions)


def test_stop_word_finishes(project):
    s = Settings.load(project)
    path, _ = session.create(s, IDEA)
    plan = session.plan_round(s, path)
    out = session.record(s, path, plan, {plan.questions[0].text: "that's enough, wrap up"})
    assert out["stopped"] and out["status"].startswith("Answered")


def test_host_draft_questions_are_linted(project):
    draft = session.DraftInput.from_host(
        {
            "title": "Plant reminders",
            "rows": {"S1": {"status": "Sufficient", "evidence": "idea text"}},
            "questions": [
                {
                    "header": "Way too long header",
                    "row": "S2",
                    "text": "Who",
                    "options": [{"label": "A", "description": "x"}],
                }
            ],
        }
    )
    path, problems = session.create(Settings.load(project), IDEA, draft=draft)
    assert problems and "header" in problems[0]
    assert doc.parse(path.read_text()).row("S1").status == "Sufficient"


def test_checkin_every_five_rounds(project):
    s = Settings.load(project)
    path, _ = session.create(s, IDEA)
    text = path.read_text()
    for n in range(1, 6):
        text = doc.append_log(
            text, {"Round": str(n), "Questions": "", "Answered": "0", "Rows sufficient": "", "Notes": ""}
        )
    path.write_text(text)
    plan = session.plan_round(s, path)
    assert plan.kind == "checkin" and "Keep going" in plan.card["questions"][0]["options"][0]["label"]
    out = session.record(s, path, plan, {"x": "Wrap up now"})
    assert out["status"].startswith("Answered")


def test_graph_interrupts_and_resumes(project):
    graph = build_graph(InMemorySaver())
    cfg = {"configurable": {"thread_id": "t1"}}
    out = graph.invoke({"root": str(project), "idea": IDEA, "slug": "plants", "scope": "auto"}, cfg)
    payload = out["__interrupt__"][0].value
    assert payload["round"] == 1 and len(payload["card"]["questions"]) == 4
    answers = {c["question"]: c["options"][0]["label"] for c in payload["card"]["questions"]}
    out = graph.invoke(Command(resume={"answers": answers}), cfg)
    assert out["__interrupt__"][0].value["round"] == 2
    intake_path = Path(payload["intake"])
    assert "In session (round 1)" in intake_path.read_text()
    assert (project / ".specify/traces/intake-plants/trace.jsonl").is_file()
    assert (project / ".specify/traces/intake-plants/reasoning/round-1-selection.md").is_file()


@pytest.mark.parametrize("software", [True, False])
def test_plan_rows_na_without_software(project, software):
    path, _ = session.create(Settings.load(project), "a volunteer rota", draft=session.DraftInput(software=software))
    t1 = doc.parse(path.read_text()).row("T1")
    assert (t1.status == "N/A") is (not software)


def test_question_feeding_two_rows_settles_both(project):
    s = Settings.load(project)
    draft = session.DraftInput.from_host(
        {
            "questions": [
                {
                    "header": "Platform",
                    "row": "T1, T6",
                    "text": "Where should the reminders run and under which limits?",
                    "options": [
                        {"label": "Phone app", "description": "Runs on the phone.", "recommended": True, "why": "x"},
                        {"label": "Website", "description": "Runs in a browser."},
                    ],
                }
            ]
        }
    )
    path, problems = session.create(s, IDEA, draft=draft)
    assert problems == []
    q = doc.parse(path.read_text()).questions[0]
    assert q.rows == ["T1", "T6"]
    plan = session.plan_round(s, path)
    plan.questions = [q]
    session.record(s, path, plan, {q.text: "Phone app"})
    rows = {r.id: r.status for r in doc.parse(path.read_text()).rows}
    assert rows["T1"] == rows["T6"] == "Sufficient"


def test_row_with_a_drafted_question_gets_followups_not_the_opener(project):
    s = Settings.load(project)
    draft = session.DraftInput.from_host(
        {
            "questions": [
                {
                    "header": "First job",
                    "row": "S3",
                    "text": "Which job should the model do well first?",
                    "options": [
                        {"label": "Find knowledge", "description": "Search.", "recommended": True, "why": "x"},
                        {"label": "Track lineage", "description": "Audit."},
                    ],
                }
            ]
        }
    )
    path, _ = session.create(s, IDEA, draft=draft)
    plan = session.plan_round(s, path)
    first = next(q for q in plan.questions if q.row == "S3")
    session.record(s, path, plan, {first.text: "Find knowledge"})
    session.plan_round(s, path)
    s3 = [q for q in doc.parse(path.read_text()).questions if "S3" in q.rows]
    opener = "Which journey should the first version get right before anything else?"
    assert opener not in [q.text for q in s3]
    assert any(q.header == "Acceptance" for q in s3)


def test_cli_accepts_long_inline_json(project):
    from sdd_harness.intake.cli import _read_json

    long = '{"text": "' + "x" * 600 + '"}'
    assert _read_json(long)["text"].startswith("x")


def test_multiselect_marks_every_recommended_pick_first():
    q = _q(
        multi_select=True,
        options=[
            Option(label="Code", description="c"),
            Option(label="Specs", description="s", recommended=True),
            Option(label="Runtime", description="r", recommended=True),
        ],
    )
    labels = [o["label"] for o in to_card(q)["options"]]
    assert labels == ["Specs (Recommended)", "Runtime (Recommended)", "Code"]
    assert read_answer(q, "Specs (Recommended), Code").letters == ["A", "B"]


def test_pick_plus_own_words_keeps_both():
    q = _q()
    r = read_answer(q, "One person (Recommended) and also log every session")
    assert r.state == "answered" and r.letters == ["A"] and "and also log every session" in r.note
    multi = _q(multi_select=True)
    r = read_answer(multi, "Then A small team last,One person (Recommended)")
    assert r.state == "answered" and r.letters == ["A"] and "Then A small team last" in r.note


def test_no_checkin_when_every_row_is_settled(project):
    s = Settings.load(project)
    path, _ = session.create(s, IDEA, draft=session.DraftInput(software=False))
    text = path.read_text()
    intake = doc.parse(text)
    for row in intake.rows:
        if row.status != "N/A":
            text = doc.update_row(text, row.model_copy(update={"status": "Sufficient", "evidence": "idea text"}))
    for n in range(1, 6):
        text = doc.append_log(
            text, {"Round": str(n), "Questions": "", "Answered": "0", "Rows sufficient": "", "Notes": ""}
        )
    path.write_text(text)
    assert session.plan_round(s, path).kind == "done"


def test_revise_supersedes_but_keeps_the_earlier_answer(project):
    s = Settings.load(project)
    path, _ = session.create(s, IDEA)
    plan = session.plan_round(s, path)
    q = next(q for q in plan.questions if q.row == "S2")
    session.record(s, path, plan, {q.text: "One person (Recommended)"})
    out = session.revise(s, path, q.id, "my 12 houseplants and my partner")
    assert "superseded" not in out["answer"] and out["superseded"].startswith("A. One person")
    revised = doc.parse(path.read_text()).question(q.id)
    assert revised.state == "other" and '"my 12 houseplants and my partner"' in revised.answer
    assert "~~A. One person" in revised.note
    assert any("(revised; supersedes: A. One person" in c for c in doc.parse(path.read_text()).clarifications)
