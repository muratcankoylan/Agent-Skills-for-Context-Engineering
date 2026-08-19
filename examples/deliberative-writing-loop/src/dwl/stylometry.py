"""Deterministic stylometric profiling.

A persona's measurable fingerprint: sentence rhythm, punctuation habits,
function-word profile, opener diversity, and lexical variety. Computed by code,
never by a model, so the critic's structural gates are reproducible and cheap.

The profile doubles as the target distribution for the writing loop: the same
statistics computed over generated text yield a distance score against the
persona corpus. This is a distribution-matching objective enforced at inference
time instead of training time.
"""

from __future__ import annotations

import math
import statistics
from collections import Counter
from dataclasses import asdict, dataclass, field

from .textseg import split_paragraphs, split_sentences, words

# Closed-class words carry authorial signal (classic authorship-attribution
# result) and are topic-independent, unlike content vocabulary.
FUNCTION_WORDS = [
    "the", "a", "an", "and", "but", "or", "nor", "so", "yet", "for",
    "of", "in", "on", "at", "by", "to", "from", "with", "without", "into",
    "over", "under", "between", "through", "about", "against", "during",
    "is", "are", "was", "were", "be", "been", "being",
    "that", "which", "who", "whom", "whose", "this", "these", "those",
    "it", "its", "he", "she", "they", "we", "you", "i",
    "not", "no", "never", "very", "quite", "rather", "just", "only",
    "if", "then", "than", "because", "while", "although", "though", "however",
    "there", "here", "when", "where", "how", "what", "all", "some", "any",
    "one", "would", "could", "should", "may", "might", "must", "can", "will",
]

_PUNCT_KEYS = {
    "em_dash": ("\u2014", "--"),
    "semicolon": (";",),
    "colon": (":",),
    "comma": (",",),
    "question": ("?",),
    "exclamation": ("!",),
    "paren_open": ("(",),
    "quote": ('"', "\u201c"),
}


@dataclass
class StyleProfile:
    """All rates are per 1000 words unless stated otherwise."""

    word_count: int = 0
    sentence_count: int = 0
    paragraph_count: int = 0
    sentence_len_mean: float = 0.0
    sentence_len_std: float = 0.0
    # Share of sentences in length bands: short (<8 words), mid (8-24), long (>24).
    sentence_band_short: float = 0.0
    sentence_band_mid: float = 0.0
    sentence_band_long: float = 0.0
    sentences_per_paragraph_mean: float = 0.0
    punct_rates: dict[str, float] = field(default_factory=dict)
    function_word_rates: dict[str, float] = field(default_factory=dict)
    # Share of sentences claimed by the single most common opening word.
    top_opener_share: float = 0.0
    # Distinct opening words / sentences (1.0 = every sentence opens differently).
    opener_diversity: float = 0.0
    # Moving-average type-token ratio, window of 100 words.
    mattr_100: float = 0.0
    contraction_rate: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> StyleProfile:
        return cls(**data)


def _mattr(tokens: list[str], window: int = 100) -> float:
    if not tokens:
        return 0.0
    if len(tokens) <= window:
        return len(set(tokens)) / len(tokens)
    total = 0.0
    count = 0
    # Stride to keep cost linear-ish on large corpora without changing the estimate much.
    stride = max(1, window // 4)
    for start in range(0, len(tokens) - window + 1, stride):
        chunk = tokens[start : start + window]
        total += len(set(chunk)) / window
        count += 1
    return total / count


def compute_profile(text: str) -> StyleProfile:
    paragraphs = split_paragraphs(text)
    sentences: list[str] = []
    for para in paragraphs:
        sentences.extend(split_sentences(para))
    tokens = words(text)
    n_words = len(tokens)
    profile = StyleProfile(
        word_count=n_words,
        sentence_count=len(sentences),
        paragraph_count=len(paragraphs),
    )
    if not sentences or n_words == 0:
        return profile

    lens = [len(words(s)) for s in sentences]
    lens = [max(length, 1) for length in lens]
    profile.sentence_len_mean = statistics.fmean(lens)
    profile.sentence_len_std = statistics.pstdev(lens) if len(lens) > 1 else 0.0
    profile.sentence_band_short = sum(1 for x in lens if x < 8) / len(lens)
    profile.sentence_band_mid = sum(1 for x in lens if 8 <= x <= 24) / len(lens)
    profile.sentence_band_long = sum(1 for x in lens if x > 24) / len(lens)
    profile.sentences_per_paragraph_mean = len(sentences) / max(len(paragraphs), 1)

    per_kw = 1000.0 / n_words
    for key, marks in _PUNCT_KEYS.items():
        profile.punct_rates[key] = sum(text.count(m) for m in marks) * per_kw

    counts = Counter(tokens)
    profile.function_word_rates = {
        fw: counts.get(fw, 0) * per_kw for fw in FUNCTION_WORDS
    }

    openers = Counter()
    for sentence in sentences:
        toks = words(sentence)
        if toks:
            openers[toks[0]] += 1
    if openers:
        profile.top_opener_share = openers.most_common(1)[0][1] / len(sentences)
        profile.opener_diversity = len(openers) / len(sentences)

    profile.mattr_100 = _mattr(tokens)
    profile.contraction_rate = sum(
        1 for t in tokens if "'" in t or "\u2019" in t
    ) * per_kw
    return profile


# Weights sum to 1.0. Rhythm and punctuation dominate because they are the
# most reliable author signals at paragraph scale; function words need more
# text to stabilize so they get less weight per-paragraph comparisons.
_DISTANCE_WEIGHTS = {
    "rhythm": 0.35,
    "punctuation": 0.25,
    "function_words": 0.20,
    "openers": 0.10,
    "lexical": 0.10,
}


def _rel_diff(a: float, b: float, floor: float = 1e-9) -> float:
    """Symmetric relative difference in [0, 1]."""
    denom = max(abs(a), abs(b), floor)
    return min(abs(a - b) / denom, 1.0)


def style_distance(candidate: StyleProfile, target: StyleProfile) -> float:
    """Weighted distance in [0, 1]. 0 means indistinguishable on these features.

    Interpret comparatively (candidate A vs. candidate B against the same
    target), not as an absolute authorship verdict.
    """
    rhythm = statistics.fmean([
        _rel_diff(candidate.sentence_len_mean, target.sentence_len_mean),
        _rel_diff(candidate.sentence_len_std, target.sentence_len_std),
        abs(candidate.sentence_band_short - target.sentence_band_short),
        abs(candidate.sentence_band_mid - target.sentence_band_mid),
        abs(candidate.sentence_band_long - target.sentence_band_long),
    ])
    punct_keys = sorted(_PUNCT_KEYS)
    punctuation = statistics.fmean([
        _rel_diff(candidate.punct_rates.get(k, 0.0), target.punct_rates.get(k, 0.0))
        for k in punct_keys
    ])
    # Cosine distance over the function-word rate vector.
    cv = [candidate.function_word_rates.get(w, 0.0) for w in FUNCTION_WORDS]
    tv = [target.function_word_rates.get(w, 0.0) for w in FUNCTION_WORDS]
    dot = sum(x * y for x, y in zip(cv, tv))
    norm = math.sqrt(sum(x * x for x in cv)) * math.sqrt(sum(y * y for y in tv))
    function_words = 1.0 - (dot / norm) if norm > 0 else 1.0
    openers = statistics.fmean([
        abs(candidate.top_opener_share - target.top_opener_share),
        abs(candidate.opener_diversity - target.opener_diversity),
    ])
    lexical = statistics.fmean([
        _rel_diff(candidate.mattr_100, target.mattr_100),
        _rel_diff(candidate.contraction_rate, target.contraction_rate),
    ])
    return (
        _DISTANCE_WEIGHTS["rhythm"] * rhythm
        + _DISTANCE_WEIGHTS["punctuation"] * punctuation
        + _DISTANCE_WEIGHTS["function_words"] * function_words
        + _DISTANCE_WEIGHTS["openers"] * openers
        + _DISTANCE_WEIGHTS["lexical"] * lexical
    )


def describe_rhythm(profile: StyleProfile) -> str:
    """Render the rhythm targets as plain instructions for the drafter prompt."""
    return (
        f"Average sentence length about {profile.sentence_len_mean:.0f} words with "
        f"standard deviation about {profile.sentence_len_std:.0f} (vary lengths that much). "
        f"Roughly {profile.sentence_band_short:.0%} short sentences (under 8 words), "
        f"{profile.sentence_band_mid:.0%} medium (8-24), {profile.sentence_band_long:.0%} long (over 24). "
        f"About {profile.sentences_per_paragraph_mean:.0f} sentences per paragraph. "
        f"Em-dash rate {profile.punct_rates.get('em_dash', 0):.1f} and semicolon rate "
        f"{profile.punct_rates.get('semicolon', 0):.1f} per 1000 words; do not exceed these."
    )
