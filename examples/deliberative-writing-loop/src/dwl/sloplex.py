"""Corpus-derived slop detection via n-gram frequency ratios.

Follows the Antislop insight (arXiv:2510.15061): slop is not a fixed word list,
it is *overrepresentation* relative to a human baseline. Some patterns appear
1000x more often in LLM output than human text. We therefore profile candidate
text against the persona corpus and flag n-grams whose relative frequency is
implausibly high, instead of maintaining a stale keyword list.

Two deterministic checks complement the ratio profile because they are
structural rather than lexical:
- opener runs: 3+ consecutive sentences opening with the same word
  (the dominant repetitiveness failure in the Deft/DFT report's SFT samples);
- cross-paragraph echo: distinctive 4-grams reused across paragraphs
  (the mechanism behind "the model keeps saying the same thing").

A small seed list of contrastive frames ("not X, but Y" and relatives) is kept
because these are syntactic templates invisible to unigram ratios. The seed
list is data (JSON-serializable), overridable per persona, and empty entries
are allowed.
"""

from __future__ import annotations

import re
from collections import Counter
from dataclasses import dataclass, field

from .textseg import ngrams, split_paragraphs, split_sentences, words

# Syntactic templates, not vocabulary. Vocabulary overuse is caught by ratios.
DEFAULT_TEMPLATE_PATTERNS: dict[str, str] = {
    "not_x_but_y": r"\bnot (?:just |only |merely |simply )?[\w'\u2019 -]{1,40}?[,;]? but\b",
    "its_not_x_its_y": r"\bit(?:'|\u2019)s not [\w'\u2019 -]{1,40}?[,;.] it(?:'|\u2019)s\b",
    "more_than_just": r"\bmore than just\b",
    "isnt_about_its_about": r"\b(?:isn(?:'|\u2019)t|is not) about [\w'\u2019 -]{1,40}?[,;.] it(?:'|\u2019)s about\b",
    "whether_x_or_y_listicle": r"\bwhether (?:you(?:'|\u2019)re|it(?:'|\u2019)s) [\w'\u2019 -]{1,40} or\b",
}

# Minimum occurrences before a ratio is considered evidence rather than noise.
_MIN_CANDIDATE_COUNT = 2


@dataclass
class SlopFinding:
    kind: str  # "ngram_ratio" | "template" | "opener_run" | "echo"
    detail: str
    severity: float  # 0..1, comparative only
    location: str = ""  # sentence index or paragraph index when known

    def to_dict(self) -> dict:
        return {
            "kind": self.kind,
            "detail": self.detail,
            "severity": round(self.severity, 3),
            "location": self.location,
        }


@dataclass
class SlopReport:
    findings: list[SlopFinding] = field(default_factory=list)

    @property
    def score(self) -> float:
        """Sum of severities normalized per 1000 words is computed by the caller;
        here we expose the raw severity sum for aggregation."""
        return sum(f.severity for f in self.findings)

    def to_dict(self) -> dict:
        return {"score": round(self.score, 3), "findings": [f.to_dict() for f in self.findings]}


class SlopProfiler:
    """Profiles a reference corpus once, then scores candidates against it."""

    def __init__(
        self,
        reference_text: str,
        ratio_threshold: float = 8.0,
        template_patterns: dict[str, str] | None = None,
    ) -> None:
        self.ratio_threshold = ratio_threshold
        self._templates = {
            name: re.compile(pattern, re.IGNORECASE)
            for name, pattern in (template_patterns or DEFAULT_TEMPLATE_PATTERNS).items()
            if pattern
        }
        ref_tokens = words(reference_text)
        self._ref_total = max(len(ref_tokens), 1)
        self._ref_counts: dict[int, Counter] = {
            n: Counter(ngrams(ref_tokens, n)) for n in (1, 2, 3)
        }

    def _ratio_findings(self, tokens: list[str]) -> list[SlopFinding]:
        findings: list[SlopFinding] = []
        total = max(len(tokens), 1)
        for n in (1, 2, 3):
            cand_counts = Counter(ngrams(tokens, n))
            ref_counts = self._ref_counts[n]
            for gram, count in cand_counts.items():
                if count < _MIN_CANDIDATE_COUNT:
                    continue
                cand_rate = count / total
                # Add-one smoothing on the reference so unseen n-grams are
                # penalized in proportion to how often the candidate leans on them.
                ref_rate = (ref_counts.get(gram, 0) + 1) / (self._ref_total + 1)
                ratio = cand_rate / ref_rate
                if ratio >= self.ratio_threshold:
                    findings.append(
                        SlopFinding(
                            kind="ngram_ratio",
                            detail=(
                                f"'{' '.join(gram)}' appears {count}x "
                                f"({ratio:.0f}x the persona-corpus rate)"
                            ),
                            severity=min(ratio / (self.ratio_threshold * 4), 1.0),
                        )
                    )
        findings.sort(key=lambda f: f.severity, reverse=True)
        return findings[:20]

    def _template_findings(self, text: str) -> list[SlopFinding]:
        findings = []
        for name, pattern in self._templates.items():
            hits = pattern.findall(text)
            if hits:
                findings.append(
                    SlopFinding(
                        kind="template",
                        detail=f"contrastive template '{name}' used {len(hits)}x: {hits[0]!r}",
                        severity=min(0.4 * len(hits), 1.0),
                    )
                )
        return findings

    @staticmethod
    def _opener_run_findings(text: str) -> list[SlopFinding]:
        findings = []
        for p_idx, para in enumerate(split_paragraphs(text)):
            sentences = split_sentences(para)
            run_word, run_len = None, 0
            for s_idx, sentence in enumerate(sentences):
                toks = words(sentence)
                opener = toks[0] if toks else ""
                if opener and opener == run_word:
                    run_len += 1
                    if run_len == 3:
                        findings.append(
                            SlopFinding(
                                kind="opener_run",
                                detail=f"3+ consecutive sentences open with '{opener}'",
                                severity=0.6,
                                location=f"paragraph {p_idx + 1}, sentence {s_idx + 1}",
                            )
                        )
                else:
                    run_word, run_len = opener, 1
        return findings

    @staticmethod
    def _echo_findings(text: str) -> list[SlopFinding]:
        paragraphs = split_paragraphs(text)
        seen: dict[tuple[str, ...], int] = {}
        findings = []
        reported: set[tuple[str, ...]] = set()
        for p_idx, para in enumerate(paragraphs):
            for gram in set(ngrams(words(para), 4)):
                if gram in seen and gram not in reported:
                    findings.append(
                        SlopFinding(
                            kind="echo",
                            detail=f"phrase '{' '.join(gram)}' reused from paragraph {seen[gram] + 1}",
                            severity=0.5,
                            location=f"paragraph {p_idx + 1}",
                        )
                    )
                    reported.add(gram)
                else:
                    seen.setdefault(gram, p_idx)
        return findings[:10]

    def score(self, text: str) -> SlopReport:
        tokens = words(text)
        report = SlopReport()
        report.findings.extend(self._ratio_findings(tokens))
        report.findings.extend(self._template_findings(text))
        report.findings.extend(self._opener_run_findings(text))
        report.findings.extend(self._echo_findings(text))
        return report
