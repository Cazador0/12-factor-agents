"""Hybrid retrieval with provenance: a retrieval accelerator, never a source of truth."""

from .embeddings import HashingEmbeddings, get_embeddings
from .index import build_retriever, collect_documents
from .provenance import Provenance, staleness
from .retriever import HybridRetriever, cite, rrf

__all__ = [
    "HashingEmbeddings",
    "HybridRetriever",
    "Provenance",
    "build_retriever",
    "cite",
    "collect_documents",
    "get_embeddings",
    "rrf",
    "staleness",
]
