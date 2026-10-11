"""LLM backends.

MockNaiveLLM is a *deliberately pessimistic, deterministic simulation* of a naive instruction-following
model. It lets the harness run offline and reproducibly. It is NOT evidence about any real model's
robustness - use AnthropicLLM (or your own backend) for that.
"""
import os
import re

from .defenses import CLOSE_TAG, HIERARCHY_RULE, OPEN_TAG
from .text_utils import split_sentences, tokenize

# The mock's own (broader than the defenses') notion of "text that sounds like an instruction".
_TRIGGER = re.compile(
    r"\b(ignore|disregard|forget)\s+(all\s+)?(the\s+)?(previous|prior|above|earlier)\s+(instructions|directives|rules)\b"
    r"|\bpay no attention to (what|everything)[^.;]{0,40}(told|said)\b"
    r"|\byou are now\b|\bdeveloper mode\b", re.I)
_REVEAL = re.compile(
    r"\b(reveal|print|repeat|show|output|display)\b[^.\n]{0,40}\b(system prompt|instructions above|your instructions)\b", re.I)
_DUMP = re.compile(
    r"\b(show|print|display|dump|reveal)\b[^.\n]{0,30}\b(internal notes|confidential|credentials)\b", re.I)
_PHISH = re.compile(r"\b(?:visit|go to|open)\s+(https?://[^\s'\"]+)", re.I)
_SAY = re.compile(
    r"\b(?:saying|say|respond(?:\s+only)?\s+with|reply(?:\s+only)?\s+with)\s+['\"“]?([A-Za-z0-9_ ]+?)['\"”]?(?=[.!,;]|\s+and\b|\s*$)",
    re.I)

PARAMETRIC_GUESSES = [  # what a model "remembers" when retrieval gives it nothing
    (re.compile(r"\bceo\b", re.I), "Acme Cloud's CEO is Jordan Lee."),
    (re.compile(r"weather", re.I), "It is currently sunny and 31 degrees in Delhi."),
]


class MockNaiveLLM:
    name = "mock-naive"

    def generate(self, system: str, user: str) -> str:
        marker = "\n\nUser question: "
        cut = user.rfind(marker)
        body, question = (user[:cut], user[cut + len(marker):]) if cut != -1 else ("", user)

        hierarchy_aware = HIERARCHY_RULE in system
        if hierarchy_aware and body.startswith(OPEN_TAG):
            end = body.find(CLOSE_TAG)  # first closing tag ends the "data" region
            if end == -1:
                untrusted, leftover = body[len(OPEN_TAG):], ""
            else:
                untrusted, leftover = body[len(OPEN_TAG):end], body[end + len(CLOSE_TAG):]
            scan_text = leftover + "\n" + question  # instructions inside the data region are ignored
            context_text = untrusted + "\n" + leftover
        else:
            scan_text = body + "\n" + question  # naive: every token is an instruction candidate
            context_text = body

        action = self._find_action(scan_text)
        if action:
            kind, arg = action
            if kind == "leak_system":
                return system
            if kind == "dump":
                return self._clean(context_text)
            if kind == "phish":
                return f"Please visit {arg} to continue."
            if kind == "say":
                return arg.strip()
        return self._answer(question, context_text)

    # ---- helpers ----
    @staticmethod
    def _find_action(text: str):
        cands = []
        for m in _REVEAL.finditer(text):
            cands.append((m.start(), "leak_system", ""))
        for m in _DUMP.finditer(text):
            cands.append((m.start(), "dump", ""))
        for t in _TRIGGER.finditer(text):
            tail = text[t.start():]
            for m in _PHISH.finditer(tail):
                cands.append((t.start() + m.start(), "phish", m.group(1)))
            for m in _SAY.finditer(tail):
                cands.append((t.start() + m.start(), "say", m.group(1)))
        if not cands:
            return None
        _, kind, arg = max(cands, key=lambda c: c[0])  # recency bias: last instruction wins
        return kind, arg

    @staticmethod
    def _clean(text: str) -> str:
        text = text.replace(OPEN_TAG, "").replace(CLOSE_TAG, "")
        return "\n".join(l for l in text.splitlines() if l.strip() not in {"Context:", "---"}).strip()

    def _answer(self, question: str, context_text: str) -> str:
        q = set(tokenize(question, drop_domain=True))
        scored = []
        for order, sent in enumerate(split_sentences(self._clean(context_text))):
            if _TRIGGER.search(sent) or _REVEAL.search(sent) or _DUMP.search(sent):
                continue  # a sensible model does not parrot instruction-like text
            overlap = len(q & set(tokenize(sent, drop_domain=True)))
            if overlap:
                scored.append((-overlap, order, sent))
        if scored:
            scored.sort()
            return " ".join(s for _, _, s in sorted(scored[:2], key=lambda x: x[1]))
        for pat, guess in PARAMETRIC_GUESSES:
            if pat.search(question):
                return guess
        return "Based on general knowledge, that is usually the case."


class AnthropicLLM:
    """Optional real backend (needs `pip install anthropic` and ANTHROPIC_API_KEY)."""

    def __init__(self, model: str | None = None):
        import anthropic  # imported lazily so the mock path has zero dependencies
        self.client = anthropic.Anthropic()
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-sonnet-5-5")
        self.name = f"anthropic:{self.model}"

    def generate(self, system: str, user: str) -> str:
        msg = self.client.messages.create(model=self.model, max_tokens=400, system=system,
                                          messages=[{"role": "user", "content": user}])
        return "".join(b.text for b in msg.content if b.type == "text")
