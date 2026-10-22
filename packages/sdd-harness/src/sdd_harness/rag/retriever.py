"""Hybrid retriever: BM25 + dense vectors fused by reciprocal rank, filtered, reranked, de-staled.

Implements LangChain's ``BaseRetriever`` so it drops into LCEL chains and LangGraph nodes. Every
returned ``Document`` carries its provenance and the scores that ranked it.
"""

from __future__ import annotations

from collections.abc import Callable
from pathlib import Path
from typing import Any

from langchain_core.callbacks import CallbackManagerForRetrieverRun
from langchain_core.documents import Document
from langchain_core.embeddings import Embeddings
from langchain_core.retrievers import BaseRetriever
from langchain_core.vectorstores import InMemoryVectorStore
from pydantic import ConfigDict, PrivateAttr

from .bm25 import BM25, tokenize
from .provenance import Provenance, head_sha, staleness


def rrf(rankings: list[list[int]], k: int = 60) -> dict[int, float]:
    """Reciprocal rank fusion: ``sum(1 / (k + rank))`` over every ranking an item appears in."""
    fused: dict[int, float] = {}
    for ranking in rankings:
        for rank, idx in enumerate(ranking):
            fused[idx] = fused.get(idx, 0.0) + 1.0 / (k + rank + 1)
    return fused


class HybridRetriever(BaseRetriever):
    """Lexical and semantic retrieval over provenance-stamped chunks."""

    model_config = ConfigDict(arbitrary_types_allowed=True)

    documents: list[Document]
    embeddings: Embeddings
    root: Path
    k: int = 8
    rrf_k: int = 60
    candidates: int = 50
    reject_stale: bool = True
    filters: dict[str, Any] = {}
    predicate: Callable[[Document], bool] | None = None

    _bm25: BM25 = PrivateAttr()
    _store: InMemoryVectorStore = PrivateAttr()
    _head: str | None = PrivateAttr(default=None)

    def model_post_init(self, __context: Any) -> None:
        self._bm25 = BM25([d.page_content for d in self.documents])
        self._store = InMemoryVectorStore(self.embeddings)
        if self.documents:
            ids = [str(i) for i in range(len(self.documents))]
            docs = [Document(page_content=d.page_content, metadata={"_i": i}) for i, d in enumerate(self.documents)]
            self._store.add_documents(docs, ids=ids)
        self._head = head_sha(self.root)

    def with_filters(self, **filters: Any) -> HybridRetriever:
        """A copy restricted by metadata equality (``kind="requirement"``, ``spec_id="SPEC-001"``…)."""
        clone = self.model_copy(update={"filters": {**self.filters, **filters}})
        clone._bm25, clone._store, clone._head = self._bm25, self._store, self._head
        return clone

    def _passes(self, doc: Document) -> bool:
        for key, want in self.filters.items():
            have = doc.metadata.get(key)
            if isinstance(want, (list, tuple, set, frozenset)):
                if have not in want:
                    return False
            elif key == "path_prefix":
                if not str(doc.metadata.get("path", "")).startswith(str(want)):
                    return False
            elif have != want:
                return False
        return self.predicate(doc) if self.predicate else True

    def _rerank_bonus(self, query: str, doc: Document) -> float:
        """Small, explainable boosts: exact IDs, heading overlap, whole-phrase hits."""
        q = query.lower()
        text = doc.page_content.lower()
        bonus = 0.0
        symbol = str(doc.metadata.get("symbol") or "").lower()
        if symbol and symbol in q:
            bonus += 0.02
        heading_terms = set(tokenize(str(doc.metadata.get("heading") or "")))
        query_terms = set(tokenize(query))
        if heading_terms and query_terms:
            bonus += 0.01 * len(heading_terms & query_terms) / len(query_terms)
        if len(q) > 12 and q in text:
            bonus += 0.02
        return bonus

    def search(self, query: str, k: int | None = None) -> list[Document]:
        k = k or self.k
        lexical = [i for i, _ in self._bm25.top(query, self.candidates)]
        dense_hits = self._store.similarity_search_with_score(query, k=min(self.candidates, len(self.documents)))
        dense = [int(d.metadata["_i"]) for d, _ in dense_hits]
        dense_score = {int(d.metadata["_i"]): float(s) for d, s in dense_hits}
        fused = rrf([lexical, dense], k=self.rrf_k)
        lex_rank = {idx: r for r, idx in enumerate(lexical)}
        ranked: list[tuple[float, int]] = []
        for idx, score in fused.items():
            doc = self.documents[idx]
            if not self._passes(doc):
                continue
            ranked.append((score + self._rerank_bonus(query, doc), idx))
        ranked.sort(reverse=True)
        out: list[Document] = []
        for score, idx in ranked:
            src = self.documents[idx]
            prov = Provenance.model_validate(src.metadata["provenance"])
            stale = staleness(self.root, prov, self._head) if self.reject_stale else None
            if stale:
                continue
            meta = {
                **src.metadata,
                "score": round(score, 6),
                "lexical_rank": lex_rank.get(idx),
                "dense_similarity": round(dense_score.get(idx, 0.0), 4),
            }
            out.append(Document(page_content=src.page_content, metadata=meta))
            if len(out) >= k:
                break
        return out

    def _get_relevant_documents(self, query: str, *, run_manager: CallbackManagerForRetrieverRun) -> list[Document]:
        return self.search(query)


def cite(doc: Document) -> str:
    """A compact citation: ``path › heading @ sha``."""
    prov = doc.metadata.get("provenance", {})
    where = prov.get("path", "?")
    if prov.get("heading"):
        where += f" › {prov['heading']}"
    sha = (prov.get("commit_sha") or "")[:8]
    return f"{where} @ {sha}" if sha else where
