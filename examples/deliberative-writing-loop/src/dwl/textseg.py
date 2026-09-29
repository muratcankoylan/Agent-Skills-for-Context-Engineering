"""Lightweight text segmentation shared by stylometry, slop profiling, and the critic.

Deliberately dependency-free. These segmenters are approximate; they are used to
compute *relative* statistics (candidate vs. persona corpus), where consistent
segmentation on both sides matters more than perfect linguistic accuracy.
"""

from __future__ import annotations

import re

_ABBREVIATIONS = {
    "mr", "mrs", "ms", "dr", "prof", "st", "jr", "sr", "vs", "etc", "eg", "ie",
    "e.g", "i.e", "fig", "no", "vol", "inc", "ltd", "co", "corp", "dept", "est",
    "approx", "cf", "al",
}

_SENTENCE_END = re.compile(r"([.!?][\"'\u201d\u2019)\]]*)\s+(?=[\"'\u201c\u2018(\[]*[A-Z0-9])")

_WORD = re.compile(r"[A-Za-z\u00c0-\u024f]+(?:['\u2019-][A-Za-z\u00c0-\u024f]+)*")


def split_paragraphs(text: str) -> list[str]:
    """Split on blank lines. Single newlines inside a paragraph are preserved."""
    parts = re.split(r"\n\s*\n", text.strip())
    return [p.strip() for p in parts if p.strip()]


def split_sentences(text: str) -> list[str]:
    """Approximate sentence splitter with abbreviation guarding."""
    text = " ".join(text.split())
    if not text:
        return []
    pieces: list[str] = []
    start = 0
    for match in _SENTENCE_END.finditer(text):
        candidate = text[start : match.end(1)]
        last_word = candidate.rstrip(".!?\"'\u201d\u2019)]").rsplit(" ", 1)[-1].lower()
        if last_word in _ABBREVIATIONS or (len(last_word) == 1 and last_word.isalpha()):
            continue
        pieces.append(candidate.strip())
        start = match.end()
    tail = text[start:].strip()
    if tail:
        pieces.append(tail)
    return pieces


def words(text: str) -> list[str]:
    """Lowercased word tokens; hyphenated and contracted forms kept whole."""
    return [w.lower() for w in _WORD.findall(text)]


def ngrams(tokens: list[str], n: int) -> list[tuple[str, ...]]:
    if n <= 0 or len(tokens) < n:
        return []
    return [tuple(tokens[i : i + n]) for i in range(len(tokens) - n + 1)]
