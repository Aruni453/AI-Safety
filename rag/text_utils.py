"""Tiny shared text helpers (tokenizer + sentence splitter)."""
import re

STOPWORDS = {
    "a", "an", "the", "is", "are", "was", "were", "be", "to", "of", "and", "or", "in", "on", "at",
    "for", "with", "do", "does", "did", "i", "you", "your", "my", "me", "it", "its", "this", "that",
    "what", "who", "how", "when", "where", "which", "can", "could", "please", "there", "any", "by",
    "if", "as", "from", "about", "have", "has", "will", "s", "many", "much", "been", "than", "also",
    "whose", "whom", "were", "their", "they", "he", "she", "his", "her", "not", "no",
}

# Words so common in this KB that they carry no signal for matching.
DOMAIN_STOPWORDS = {"acme", "cloud"}


def _stem(tok: str) -> str:
    return tok[:-1] if len(tok) > 3 and tok.endswith("s") else tok


def tokenize(text: str, drop_domain: bool = False) -> list[str]:
    toks = [_stem(t) for t in re.findall(r"[a-z0-9]+", text.lower())]
    toks = [t for t in toks if t not in STOPWORDS and (len(t) > 1 or t.isdigit())]
    if drop_domain:
        toks = [t for t in toks if t not in DOMAIN_STOPWORDS]
    return toks


def split_sentences(text: str) -> list[str]:
    parts = re.split(r"(?<=[.!?])\s+|\n+", text)
    return [p.strip() for p in parts if p and p.strip()]
