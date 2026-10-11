"""Knowledge-base loading and a dependency-free TF-IDF retriever (paragraph-level chunks)."""
import math
import re
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from .text_utils import tokenize


@dataclass(frozen=True)
class Chunk:
    doc_id: str
    title: str
    classification: str  # "public" | "confidential"
    idx: int
    text: str


def load_kb(kb_dir: str | Path) -> list[Chunk]:
    chunks: list[Chunk] = []
    for path in sorted(Path(kb_dir).glob("*.md")):
        raw = path.read_text(encoding="utf-8")
        header, _, body = raw.partition("\n---\n")
        meta = {}
        for line in header.splitlines():
            if ":" in line:
                k, v = line.split(":", 1)
                meta[k.strip()] = v.strip()
        paras = [p.strip() for p in re.split(r"\n\s*\n", body) if p.strip()]
        for i, p in enumerate(paras):
            chunks.append(Chunk(path.stem, meta.get("title", path.stem),
                                meta.get("classification", "public"), i, p))
    return chunks


class Retriever:
    def __init__(self, chunks: list[Chunk]):
        self.chunks = chunks
        self._tf = [Counter(tokenize(c.text, drop_domain=True)) for c in chunks]
        df = Counter()
        for tf in self._tf:
            df.update(tf.keys())
        n = len(chunks)
        self._idf = {t: math.log((n + 1) / (d + 1)) + 1.0 for t, d in df.items()}
        self._norms = [self._norm(tf) for tf in self._tf]

    def _norm(self, tf: Counter) -> float:
        return math.sqrt(sum((c * self._idf.get(t, 1.0)) ** 2 for t, c in tf.items())) or 1.0

    def search(self, query: str, k: int = 3, allow=None) -> list[tuple[Chunk, float]]:
        q_tf = Counter(tokenize(query, drop_domain=True))
        q_norm = self._norm(q_tf)
        scored = []
        for chunk, tf, norm in zip(self.chunks, self._tf, self._norms):
            if allow is not None and not allow(chunk):
                continue
            dot = sum(c * self._idf.get(t, 1.0) * tf[t] * self._idf.get(t, 1.0)
                      for t, c in q_tf.items() if t in tf)
            if dot > 0:
                scored.append((chunk, dot / (norm * q_norm)))
        scored.sort(key=lambda x: -x[1])
        return scored[:k]
