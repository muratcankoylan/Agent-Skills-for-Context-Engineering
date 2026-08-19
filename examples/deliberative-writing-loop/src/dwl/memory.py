"""Run memory: what the drafter is allowed to remember, and how it shrinks.

Three tiers, cheapest-first (mirrors RecurrentGPT's language-based LSTM and the
compaction-as-action framing in CompactionRL/SUPO, implemented as a
training-free harness policy):

1. Verbatim tail: only the immediately previous paragraph stays in context
   verbatim. Prose flow needs the actual sentences it must connect to;
   everything older gets compacted.
2. Commitments ledger (machine-readable, deterministic): claims made, terms
   defined, images used, and distinctive phrases already spent. The ledger is
   how the harness prevents self-repetition: a "spent" 4-gram is not available
   to be spent again. This replaces trusting the model to remember what it said.
3. Lessons (compacted critique traces): when the critic repeatedly flags the
   same failure, the finding is promoted into a standing lesson injected into
   every later draft prompt. The document run improves as it proceeds; this is
   the self-improvement loop scoped to a single artifact.

Everything is JSON-serializable so a run can resume from disk mid-document.
"""

from __future__ import annotations

from collections import Counter
from dataclasses import dataclass, field

from .textseg import ngrams, split_sentences, words

# Ubiquitous function-word grams never count as "distinctive".
_STOP_START = {
    "the", "a", "an", "and", "but", "or", "of", "in", "on", "at", "to", "it",
    "is", "are", "was", "were", "that", "this", "there", "i", "we", "you", "he",
    "she", "they", "as", "for", "with", "by", "be", "not", "have", "has", "had",
}


def distinctive_grams(text: str, n: int = 4) -> set[tuple[str, ...]]:
    """4-grams containing at least two non-stopword tokens: cheap proxy for
    'a phrase a reader would notice if repeated'."""
    result = set()
    for gram in ngrams(words(text), n):
        content = sum(1 for token in gram if token not in _STOP_START)
        if content >= 2:
            result.add(gram)
    return result


@dataclass
class ParagraphRecord:
    index: int
    summary: str
    text: str


@dataclass
class RunMemory:
    paragraphs: list[ParagraphRecord] = field(default_factory=list)
    claims: list[str] = field(default_factory=list)
    terms_defined: list[str] = field(default_factory=list)
    images_used: list[str] = field(default_factory=list)
    spent_phrases: set[tuple[str, ...]] = field(default_factory=set)
    lessons: list[str] = field(default_factory=list)
    _lesson_counter: Counter = field(default_factory=Counter)

    # ----- commit -----

    def commit_paragraph(self, index: int, text: str, summary: str, claims: list[str]) -> None:
        self.paragraphs.append(ParagraphRecord(index=index, summary=summary, text=text))
        self.claims.extend(claims)
        self.spent_phrases |= distinctive_grams(text)

    def observe_finding(self, category_key: str, lesson_text: str, threshold: int = 2) -> None:
        """Promote a repeated critique finding into a standing lesson."""
        self._lesson_counter[category_key] += 1
        if self._lesson_counter[category_key] >= threshold and lesson_text not in self.lessons:
            self.lessons.append(lesson_text)

    # ----- render -----

    def render_context(self, max_chars: int = 6000) -> str:
        """The drafter's view of the document so far. Structure over recency:
        summaries of everything, verbatim text only for the last paragraph."""
        blocks: list[str] = []
        if self.paragraphs:
            summaries = "\n".join(
                f"P{record.index + 1}: {record.summary}" for record in self.paragraphs
            )
            blocks.append("DOCUMENT SO FAR (summaries):\n" + summaries)
            blocks.append(
                "PREVIOUS PARAGRAPH (verbatim; your paragraph must follow from its last sentence):\n"
                + self.paragraphs[-1].text
            )
        if self.claims:
            blocks.append(
                "CLAIMS ALREADY MADE (do not restate, build on them):\n- "
                + "\n- ".join(self.claims[-12:])
            )
        if self.images_used:
            blocks.append("IMAGES/METAPHORS ALREADY USED (do not reuse): " + "; ".join(self.images_used[-8:]))
        if self.lessons:
            blocks.append("STANDING CORRECTIONS FROM EARLIER CRITIQUES:\n- " + "\n- ".join(self.lessons))
        context = "\n\n".join(blocks)
        if len(context) > max_chars:
            # Compaction under pressure: drop oldest summaries first, keep
            # ledger and lessons, always keep the verbatim tail.
            while len(context) > max_chars and len(self.paragraphs) > 1 and "\n" in context:
                first_newline = context.find("\nP")
                second_newline = context.find("\nP", first_newline + 1)
                if second_newline == -1:
                    break
                context = context[:first_newline] + context[second_newline:]
        return context

    def repeated_phrases_in(self, text: str) -> list[str]:
        """Distinctive phrases in `text` that were already spent earlier."""
        hits = distinctive_grams(text) & self.spent_phrases
        return [" ".join(gram) for gram in sorted(hits)]

    def fallback_summary(self, text: str) -> str:
        """Extractive fallback when no model is available: first sentence, clipped."""
        sentences = split_sentences(text)
        head = sentences[0] if sentences else text[:160]
        return head[:200]

    def to_dict(self) -> dict:
        return {
            "paragraphs": [
                {"index": p.index, "summary": p.summary, "text": p.text} for p in self.paragraphs
            ],
            "claims": self.claims,
            "terms_defined": self.terms_defined,
            "images_used": self.images_used,
            "spent_phrases": [list(gram) for gram in sorted(self.spent_phrases)],
            "lessons": self.lessons,
        }

    @classmethod
    def from_dict(cls, data: dict) -> RunMemory:
        memory = cls()
        for p in data.get("paragraphs", []):
            memory.paragraphs.append(
                ParagraphRecord(index=p["index"], summary=p["summary"], text=p["text"])
            )
        memory.claims = data.get("claims", [])
        memory.terms_defined = data.get("terms_defined", [])
        memory.images_used = data.get("images_used", [])
        memory.spent_phrases = {tuple(gram) for gram in data.get("spent_phrases", [])}
        memory.lessons = data.get("lessons", [])
        return memory
