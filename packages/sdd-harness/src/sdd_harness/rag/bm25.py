"""Okapi BM25 over a light tokenizer. Lexical recall for IDs, names and exact terms."""

from __future__ import annotations

import math
import re
from collections import Counter

_TOKEN = re.compile(r"[a-z0-9]+(?:[-_][a-z0-9]+)*")
STOPWORDS = frozenset(
    "a an and are as at be by for from has have if in into is it its of on or that the their this to was "
    "were will with what when which who why how not no do does can should may must".split()
)


def _stem(tok: str) -> str:
    for suffix in ("ations", "ation", "ings", "ing", "ies", "ers", "ed", "es", "s"):
        if len(tok) > len(suffix) + 3 and tok.endswith(suffix):
            return tok[: -len(suffix)] + ("y" if suffix == "ies" else "")
    return tok


def tokenize(text: str) -> list[str]:
    out: list[str] = []
    for raw in _TOKEN.findall(text.lower()):
        if raw in STOPWORDS:
            continue
        out.append(_stem(raw))
        if "-" in raw or "_" in raw:  # also index the parts of fr-001, speckit-intake-start
            out.extend(_stem(p) for p in re.split(r"[-_]", raw) if p and p not in STOPWORDS)
    return out


class BM25:
    def __init__(self, docs: list[str], k1: float = 1.5, b: float = 0.75):
        self.k1, self.b = k1, b
        self.tfs = [Counter(tokenize(d)) for d in docs]
        self.lens = [sum(tf.values()) for tf in self.tfs]
        self.avg = (sum(self.lens) / len(self.lens)) if self.lens else 0.0
        df: Counter[str] = Counter()
        for tf in self.tfs:
            df.update(tf.keys())
        n = len(docs)
        self.idf = {t: math.log(1 + (n - f + 0.5) / (f + 0.5)) for t, f in df.items()}

    def scores(self, query: str) -> list[float]:
        terms = tokenize(query)
        out = []
        for tf, length in zip(self.tfs, self.lens, strict=True):
            s = 0.0
            for t in terms:
                f = tf.get(t)
                if not f:
                    continue
                denom = f + self.k1 * (1 - self.b + self.b * length / (self.avg or 1))
                s += self.idf.get(t, 0.0) * f * (self.k1 + 1) / denom
            out.append(s)
        return out

    def top(self, query: str, n: int) -> list[tuple[int, float]]:
        scored = [(i, s) for i, s in enumerate(self.scores(query)) if s > 0]
        scored.sort(key=lambda x: x[1], reverse=True)
        return scored[:n]
