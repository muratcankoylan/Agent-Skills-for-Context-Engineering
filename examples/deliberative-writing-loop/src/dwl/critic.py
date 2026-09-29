"""Sentence-level critique: deterministic gates first, rubric judgment second.

Ordering is a design principle, not an optimization. Unguided self-critique
converges to model-preferred text (the recursive-refinement fixed-point
result), and LLM judges fail to detect slop reliably (arXiv:2509.19163). So the
critic runs code-level checks that cannot drift: slop frequency ratios against
the persona corpus, opener runs, cross-paragraph echo, spent-phrase reuse, and
rhythm deviation from the persona profile. Only findings that survive those
gates are joined by one bounded rubric pass using the persona's own extracted
rules, and every rubric flag must name its sentence and its violated rule so
the repair step stays targeted.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from .adapters.base import LLMAdapter
from .memory import RunMemory
from .persona import Persona, _parse_json_object
from .planner import ParagraphContract
from .sloplex import SlopProfiler
from .stylometry import compute_profile
from .textseg import split_sentences, words

_RUBRIC_SYSTEM = (
    "You are a demanding line editor enforcing a specific author's craft rules. You flag "
    "only concrete violations of the given rules or contract, one flag per sentence, and "
    "you quote the sentence you are flagging. If nothing violates a rule, you pass the "
    "paragraph. You never invent rules and never flag matters of taste outside the rules. "
    "Output only JSON."
)

_RUBRIC_PROMPT = """AUTHOR RULES:
{rules}

PARAGRAPH CONTRACT:
{contract}

PARAGRAPH (sentences numbered):
{numbered}

Check each sentence against the rules and the contract. Output JSON:
{{"flags": [{{"sentence": <number>, "rule": "<the specific rule violated>",
"problem": "<what is wrong, in one clause>", "instruction": "<how to fix it, imperative>"}}],
"verdict": "pass" | "repair"}}

Flag at most {max_flags} sentences: the worst offenders only. Empty flags list means pass."""


@dataclass
class Critique:
    verdict: str  # "pass" | "repair"
    flags: list[str] = field(default_factory=list)  # human-readable repair instructions
    deterministic: dict = field(default_factory=dict)
    rubric: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {
            "verdict": self.verdict,
            "flags": self.flags,
            "deterministic": self.deterministic,
            "rubric": self.rubric,
        }


def _rhythm_flags(paragraph: str, persona: Persona, contract: ParagraphContract) -> list[str]:
    flags: list[str] = []
    sentences = split_sentences(paragraph)
    if not sentences:
        return ["paragraph is empty or unparseable"]
    if abs(len(sentences) - contract.target_sentences) > max(contract.target_sentences // 2, 2):
        flags.append(
            f"contract asks for about {contract.target_sentences} sentences, paragraph has {len(sentences)}"
        )
    profile = compute_profile(paragraph)
    target = persona.style
    if target.sentence_len_std >= 4 and profile.sentence_len_std < target.sentence_len_std * 0.4:
        flags.append(
            "sentence lengths are too uniform for this author: vary rhythm "
            f"(author std {target.sentence_len_std:.0f} words, paragraph std {profile.sentence_len_std:.0f})"
        )
    em_target = target.punct_rates.get("em_dash", 0.0)
    em_actual = profile.punct_rates.get("em_dash", 0.0)
    if em_actual > max(em_target * 2, 2.0) and em_actual > 0:
        n_words = max(len(words(paragraph)), 1)
        flags.append(
            f"em-dash overuse: {em_actual * n_words / 1000:.0f} in one paragraph exceeds the "
            f"author's rate of {em_target:.1f} per 1000 words"
        )
    return flags


def deterministic_critique(
    paragraph: str,
    persona: Persona,
    contract: ParagraphContract,
    memory: RunMemory,
    profiler: SlopProfiler,
) -> tuple[list[str], dict]:
    """Returns (repair flags, machine-readable report)."""
    flags: list[str] = []
    slop = profiler.score(paragraph)
    for finding in slop.findings:
        if finding.severity >= 0.4:
            flags.append(f"{finding.kind}: {finding.detail}")
    reused = memory.repeated_phrases_in(paragraph)
    for phrase in reused[:5]:
        flags.append(f"spent phrase reused from an earlier paragraph: '{phrase}'")
    rhythm = _rhythm_flags(paragraph, persona, contract)
    flags.extend(rhythm)
    report = {
        "slop": slop.to_dict(),
        "reused_phrases": reused,
        "rhythm_flags": rhythm,
    }
    return flags, report


def rubric_critique(
    adapter: LLMAdapter,
    paragraph: str,
    persona: Persona,
    contract: ParagraphContract,
    max_flags: int = 3,
) -> tuple[list[str], dict]:
    sentences = split_sentences(paragraph)
    numbered = "\n".join(f"{i + 1}. {s}" for i, s in enumerate(sentences))
    response = adapter.complete(
        system=_RUBRIC_SYSTEM,
        user=_RUBRIC_PROMPT.format(
            rules=persona.rules_block(),
            contract=contract.render(),
            numbered=numbered,
            max_flags=max_flags,
        ),
        max_tokens=800,
        temperature=0.2,
        label="rubric",
    )
    try:
        data = _parse_json_object(response.text)
    except ValueError:
        return [], {"error": "rubric output unparseable", "raw": response.text[:400]}
    flags = []
    for flag in data.get("flags", [])[:max_flags]:
        idx = flag.get("sentence")
        quoted = ""
        if isinstance(idx, int) and 1 <= idx <= len(sentences):
            quoted = f" [sentence {idx}: {sentences[idx - 1][:120]!r}]"
        flags.append(
            f"rule violation: {flag.get('rule', '?')} - {flag.get('problem', '?')}. "
            f"Fix: {flag.get('instruction', '?')}{quoted}"
        )
    return flags, data


def critique_paragraph(
    adapter: LLMAdapter,
    paragraph: str,
    persona: Persona,
    contract: ParagraphContract,
    memory: RunMemory,
    profiler: SlopProfiler,
) -> Critique:
    det_flags, det_report = deterministic_critique(paragraph, persona, contract, memory, profiler)
    rub_flags, rub_report = rubric_critique(adapter, paragraph, persona, contract)
    all_flags = det_flags + rub_flags
    return Critique(
        verdict="repair" if all_flags else "pass",
        flags=all_flags,
        deterministic=det_report,
        rubric=rub_report,
    )
