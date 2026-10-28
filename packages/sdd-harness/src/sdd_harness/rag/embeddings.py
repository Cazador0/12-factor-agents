"""Dense embeddings behind LangChain's ``Embeddings`` interface.

``hashing`` (default) is offline and deterministic: signed feature hashing of word unigrams, bigrams
and character trigrams. It needs no download and no key, so retrieval works in every cloud session.
``fastembed`` (local ONNX model) and ``voyage`` (Anthropic's recommended embedding partner, needs
``VOYAGE_API_KEY``) are optional extras for higher-quality semantic recall.
"""

from __future__ import annotations

import hashlib
import math
import os
import re

from langchain_core.embeddings import Embeddings

from .bm25 import tokenize


class HashingEmbeddings(Embeddings):
    def __init__(self, dim: int = 768):
        self.dim = dim

    def _bucket(self, feature: str) -> tuple[int, float]:
        h = hashlib.blake2b(feature.encode("utf-8"), digest_size=8).digest()
        idx = int.from_bytes(h[:4], "little") % self.dim
        sign = 1.0 if h[4] & 1 else -1.0
        return idx, sign

    def _embed(self, text: str) -> list[float]:
        vec = [0.0] * self.dim
        words = tokenize(text)
        feats: list[tuple[str, float]] = [(f"w:{w}", 1.0) for w in words]
        feats += [(f"b:{a}_{b}", 0.7) for a, b in zip(words, words[1:], strict=False)]
        squashed = re.sub(r"\s+", " ", text.lower())
        feats += [(f"c:{squashed[i : i + 3]}", 0.15) for i in range(max(0, len(squashed) - 2))]
        for feat, weight in feats:
            idx, sign = self._bucket(feat)
            vec[idx] += sign * weight
        norm = math.sqrt(sum(v * v for v in vec)) or 1.0
        return [v / norm for v in vec]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [self._embed(t) for t in texts]

    def embed_query(self, text: str) -> list[float]:
        return self._embed(text)


class FastEmbedEmbeddings(Embeddings):  # pragma: no cover - optional extra, downloads a model
    def __init__(self, model: str = "BAAI/bge-small-en-v1.5"):
        from fastembed import TextEmbedding

        self._model = TextEmbedding(model_name=model)

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return [list(map(float, v)) for v in self._model.embed(texts)]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]


class VoyageEmbeddings(Embeddings):  # pragma: no cover - optional extra, needs VOYAGE_API_KEY
    def __init__(self, model: str = "voyage-code-3"):
        import voyageai

        self._client = voyageai.Client()
        self._model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        return self._client.embed(texts, model=self._model, input_type="document").embeddings

    def embed_query(self, text: str) -> list[float]:
        return self._client.embed([text], model=self._model, input_type="query").embeddings[0]


def get_embeddings(name: str | None = None) -> Embeddings:
    name = (name or os.environ.get("SDD_EMBEDDINGS") or "hashing").lower()
    if name == "fastembed":
        return FastEmbedEmbeddings()
    if name == "voyage":
        return VoyageEmbeddings(os.environ.get("SDD_VOYAGE_MODEL", "voyage-code-3"))
    return HashingEmbeddings()
