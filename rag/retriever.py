"""SQLite-backed knowledge base access. Retrieval is SQL: FTS5 + BM25, with the access-control filter in the WHERE clause."""
import math
import re
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from .text_utils import STOPWORDS

DEFAULT_DB = Path(__file__).resolve().parent.parent / "data" / "bench.db"


@dataclass(frozen=True)
class Chunk:
    chunk_id: int
    article: str
    source: str          # 'squad' | 'synthetic_confidential' | 'synthetic_poison'
    classification: str  # 'public' | 'confidential'
    text: str


class Store:
    def __init__(self, db_path: str | Path = DEFAULT_DB):
        if not Path(db_path).exists():
            raise FileNotFoundError(f"{db_path} not found - run `python -m harness.build` first")
        self.conn = sqlite3.connect(str(db_path))
        self.conn.row_factory = sqlite3.Row

    def search(self, query: str, k: int = 3, public_only: bool = False) -> list[tuple[Chunk, float]]:
        words = [w for w in re.findall(r"[a-z0-9]+", query.lower()) if w not in STOPWORDS]
        if not words:
            return []
        match = " OR ".join(f'"{w}"' for w in dict.fromkeys(words))
        sql = (
            "SELECT c.chunk_id, c.article, c.source, c.classification, c.text, -bm25(chunks_fts) AS score "
            "FROM chunks_fts JOIN chunks c ON c.chunk_id = chunks_fts.rowid "
            "WHERE chunks_fts MATCH ? "
            + ("AND c.classification = 'public' " if public_only else "")
            + "ORDER BY bm25(chunks_fts) LIMIT ?"
        )
        rows = self.conn.execute(sql, (match, k)).fetchall()
        return [(Chunk(r["chunk_id"], r["article"], r["source"], r["classification"], r["text"]), r["score"])
                for r in rows]

    def idf(self, words: list[str]) -> dict[str, float]:
        """Inverse document frequency per word, from the FTS index (word is stemmed by FTS the same way as in search)."""
        n = self.conn.execute("SELECT COUNT(*) FROM chunks").fetchone()[0]
        out = {}
        for w in words:
            df = self.conn.execute("SELECT COUNT(*) FROM chunks_fts WHERE chunks_fts MATCH ?", (f'"{w}"',)).fetchone()[0]
            out[w] = math.log((n + 1) / (df + 1))
        return out

    def close(self):
        self.conn.close()
