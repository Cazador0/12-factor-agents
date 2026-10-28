"""Markdown edits, config layering, retrieval, reasoning traces and the Claude client."""

from __future__ import annotations

from types import SimpleNamespace

import pytest
from conftest import commit
from langchain_core.documents import Document

from sdd_harness import markdown as md
from sdd_harness.config import Settings
from sdd_harness.llm import FALLBACK_BETA, Claude, ClaudeRefusal
from sdd_harness.rag import HashingEmbeddings, HybridRetriever, build_retriever, rrf
from sdd_harness.rag.bm25 import BM25, tokenize
from sdd_harness.rag.chunking import chunk_spec, spec_id_for
from sdd_harness.reasoning import ReasoningRecorder, SessionCheckpoint, TraceLog, ground, reasoning_chain

# ---------------------------------------------------------------- markdown


def test_update_table_row_touches_only_that_row():
    text = "\n".join(md.render_table(["#", "Status"], [["S1", "Missing"], ["S2", "Missing"]])) + "\n"
    out = md.update_table_row(text, "#", "S2", {"Status": "Sufficient"})
    rows = md.parse_table(out)
    assert rows[0]["Status"] == "Missing" and rows[1]["Status"] == "Sufficient"


def test_append_to_section_keeps_neighbours():
    text = "## A\n\none\n\n## B\n\ntwo\n"
    out = md.append_to_section(text, "A", ["three"], level=2)
    assert out.index("three") < out.index("## B")
    assert "two" in out


def test_settings_local_config_wins(project):
    cfg = project / ".specify" / "extensions" / "intake"
    cfg.mkdir(parents=True)
    (cfg / "intake-config.yml").write_text("session:\n  per_round: 3\n")
    (cfg / "local-config.yml").write_text("session:\n  per_round: 2\n")
    assert Settings.load(project).per_round == 2


# ---------------------------------------------------------------- retrieval


def test_tokenize_splits_ids_and_stems():
    toks = tokenize("FR-001 requires planning")
    assert "fr-001" in toks and "001" in toks
    assert tokenize("plans") == tokenize("plan") and "the" not in tokenize("the plan")


def test_bm25_prefers_exact_terms():
    bm = BM25(["webhook signatures are verified", "leases expire after a timeout"])
    assert bm.top("verify webhook signature", 1)[0][0] == 0


def test_hashing_embeddings_are_deterministic_and_normalized():
    e = HashingEmbeddings(dim=64)
    a, b = e.embed_query("lease expiry"), e.embed_query("lease expiry")
    assert a == b
    assert abs(sum(x * x for x in a) - 1.0) < 1e-6


def test_rrf_rewards_agreement():
    fused = rrf([[1, 2, 3], [2, 1, 3]])
    assert fused[1] == fused[2] > fused[3]


def test_spec_chunks_carry_requirement_ids():
    text = "# Spec\n\n## Requirements\n\n- **FR-001**: System MUST verify signatures.\n"
    chunks = list(chunk_spec(text, "specs/001-x/spec.md"))
    reqs = [c for c in chunks if c.kind == "requirement"]
    assert reqs and reqs[0].symbol == "FR-001" and reqs[0].spec_id == "SPEC-001"
    assert spec_id_for("docs/x.md") is None


def test_hybrid_retriever_cites_and_rejects_stale(project):
    (project / "docs").mkdir()
    doc = project / "docs" / "leases.md"
    doc.write_text("# Leases\n\nA lease expires when its heartbeat stops for longer than the TTL.\n")
    commit(project)
    retriever = build_retriever(Settings.load(project), include=["docs/*.md"])
    hits = retriever.search("when does a lease expire")
    assert hits and hits[0].metadata["provenance"]["path"] == "docs/leases.md"
    assert hits[0].metadata["provenance"]["commit_sha"]
    doc.write_text("# Leases\n\nRewritten.\n")  # the indexed chunk no longer describes the tree
    assert retriever.search("when does a lease expire") == []
    assert retriever.model_copy(update={"reject_stale": False}).search("lease expire")


def test_retriever_filters(project):
    docs = [
        Document(
            page_content="alpha requirement",
            metadata={"kind": "requirement", "path": "a", "provenance": {"repo": "r", "path": "a"}},
        ),
        Document(
            page_content="alpha task", metadata={"kind": "task", "path": "b", "provenance": {"repo": "r", "path": "b"}}
        ),
    ]
    r = HybridRetriever(documents=docs, embeddings=HashingEmbeddings(), root=project, reject_stale=False)
    assert [d.metadata["kind"] for d in r.with_filters(kind="task").search("alpha")] == ["task"]


# ---------------------------------------------------------------- reasoning


def test_trace_log_and_checkpoint_roundtrip(tmp_path):
    log = TraceLog(tmp_path, "run-1", "pse")
    t = log.record("node", "Did X", "Because Y", evidence=["a.md"], next_action="Z")
    assert t.id == "D-01" and log.entries()[0].decision == "Did X"
    path = log.checkpoint(SessionCheckpoint(role="pse", session_id="s", goal="g", next_action="n"))
    assert TraceLog.load_checkpoint(path).goal == "g"


def test_recorder_and_grounding():
    r = ReasoningRecorder("q?")
    a = r.observe("seen", ["docs/a.md"])
    r.observe("made up", ["docs/missing.md"])
    out = r.conclude("done", builds_on=[a])
    doc = Document(page_content="x", metadata={"path": "docs/a.md", "provenance": {"path": "docs/a.md"}})
    grounded = ground(out, [doc])
    assert grounded.ungrounded_steps == [2]
    assert "⚠ ungrounded" in grounded.to_markdown()


class FakeClaude:
    def runnable(self, schema, system=None):
        from langchain_core.runnables import RunnableLambda

        def answer(prompt):
            assert "<source label=" in prompt
            return schema(
                question="q",
                steps=[{"n": 1, "kind": "observation", "claim": "c", "evidence": ["docs/a.md"]}],
                conclusion="ok",
            )

        return RunnableLambda(answer)


def test_reasoning_chain_is_lcel_and_grounded():
    doc = Document(page_content="text", metadata={"path": "docs/a.md", "provenance": {"path": "docs/a.md"}})

    class R:
        def invoke(self, q):
            return [doc]

    from langchain_core.retrievers import BaseRetriever

    class Ret(BaseRetriever):
        def _get_relevant_documents(self, query, *, run_manager):
            return [doc]

    out = reasoning_chain(Ret(), FakeClaude()).invoke({"question": "why?"})
    assert out.conclusion == "ok" and out.ungrounded_steps == []


# ---------------------------------------------------------------- llm


class FakeMessages:
    def __init__(self, response):
        self.response, self.kwargs = response, None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return self.response


def _client(response):
    msgs = FakeMessages(response)
    return SimpleNamespace(beta=SimpleNamespace(messages=msgs)), msgs


def test_claude_parse_sends_current_api_shape():
    from pydantic import BaseModel

    class Out(BaseModel):
        x: int

    client, msgs = _client(SimpleNamespace(stop_reason="end_turn", parsed_output=Out(x=1)))
    assert Claude(client=client).parse(Out, "hi").x == 1
    k = msgs.kwargs
    assert k["model"] == "claude-opus-5-5" and k["thinking"] == {"type": "adaptive"}
    assert k["fallbacks"] == "default" and k["betas"] == [FALLBACK_BETA]
    assert k["output_config"] == {"effort": "high"} and k["output_format"] is Out


def test_claude_refusal_raises():
    from pydantic import BaseModel

    class Out(BaseModel):
        x: int

    details = SimpleNamespace(category="cyber", explanation="no")
    client, _ = _client(SimpleNamespace(stop_reason="refusal", stop_details=details, parsed_output=None))
    with pytest.raises(ClaudeRefusal):
        Claude(client=client).parse(Out, "hi")
