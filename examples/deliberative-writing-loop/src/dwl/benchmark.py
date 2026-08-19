"""Benchmark harness: DWL vs one-shot vs whole-document self-refine.

Design constraints carried over from this repository's benchmark discipline:
- deterministic metrics first; LLM-judge preferences are reported per-item with
  the judging model named, never as a single blended score;
- cross-judging: each piece is judged by BOTH providers, because LLM judges
  favor their own outputs (Panickssery 2024; PNAS 2025). Same-provider
  preferences are reported but marked self-judged;
- detector scores (Pangram) are a diagnostic column, never a target;
- resume by default: items with existing result files are skipped;
- budget gates are mandatory arguments of the run, not optional flags.

Conditions:
- oneshot: single call, persona rules + brief in the prompt. The strongest
  honest baseline: same model, same information, no loop.
- selfrefine: oneshot then two whole-document refine rounds (Self-Refine
  style), same call count ceiling as DWL's repair budget.
- dwl: the full deliberative loop.
"""

from __future__ import annotations

import json
import time
from dataclasses import dataclass
from pathlib import Path

from .adapters.base import Budget, LLMAdapter
from .adapters.pangram import PangramClient
from .harness import RunConfig, WritingRun
from .persona import Persona, _parse_json_object
from .sloplex import SlopProfiler
from .stylometry import compute_profile, style_distance

_ONESHOT_SYSTEM = (
    "You are ghostwriting as a specific author, following their craft rules exactly. "
    "Write the piece only: no title unless asked, no preamble, no markdown headers."
)

_ONESHOT_PROMPT = """{rules}

{exemplars}

BRIEF:
{brief}

Write the complete piece (about {target_words} words) in the author's voice."""

_REFINE_PROMPT = """{rules}

Here is a draft of a piece:

{draft}

Critique it against the author rules above, then output an improved full revision.
Output only the revised piece, no commentary."""

_JUDGE_SYSTEM = (
    "You are judging which of two texts is better writing for the same brief in the same "
    "target author's voice. Judge craft, fidelity to the voice, and freedom from formulaic "
    "AI patterns. Output only JSON."
)

_JUDGE_PROMPT = """BRIEF:
{brief}

AUTHOR RULES:
{rules}

TEXT A:
{text_a}

TEXT B:
{text_b}

Which text is better on each dimension? Output JSON:
{{"voice_fidelity": "A"|"B", "freshness": "A"|"B", "coherence": "A"|"B", "overall": "A"|"B"}}"""


@dataclass
class BenchItem:
    brief_id: str
    brief: str
    persona_name: str
    condition: str
    provider: str


def generate_oneshot(adapter: LLMAdapter, persona: Persona, brief: str, target_words: int) -> str:
    response = adapter.complete(
        system=_ONESHOT_SYSTEM,
        user=_ONESHOT_PROMPT.format(
            rules=persona.rules_block(),
            exemplars=persona.exemplar_block(limit=3),
            brief=brief,
            target_words=target_words,
        ),
        max_tokens=2400,
        temperature=0.8,
        label="oneshot",
    )
    return response.text.strip()


def generate_selfrefine(
    adapter: LLMAdapter, persona: Persona, brief: str, target_words: int, rounds: int = 2
) -> str:
    text = generate_oneshot(adapter, persona, brief, target_words)
    for _ in range(rounds):
        response = adapter.complete(
            system=_ONESHOT_SYSTEM,
            user=_REFINE_PROMPT.format(rules=persona.rules_block(), draft=text),
            max_tokens=2400,
            temperature=0.6,
            label="selfrefine",
        )
        text = response.text.strip() or text
    return text


def generate_dwl(
    adapter: LLMAdapter, persona: Persona, brief: str, target_words: int, runs_dir: Path
) -> str:
    run = WritingRun(
        adapter,
        persona,
        brief,
        RunConfig(target_words=target_words, runs_dir=runs_dir),
    )
    return run.run()


_GENERATORS = {
    "oneshot": generate_oneshot,
    "selfrefine": generate_selfrefine,
}


def deterministic_metrics(text: str, persona: Persona) -> dict:
    profile = compute_profile(text)
    slop = SlopProfiler(persona.corpus_text).score(text)
    words_total = max(profile.word_count, 1)
    return {
        "word_count": profile.word_count,
        "style_distance": round(style_distance(profile, persona.style), 4),
        "slop_score_per_kw": round(slop.score * 1000 / words_total, 3),
        "slop_finding_count": len(slop.findings),
        "top_opener_share": round(profile.top_opener_share, 3),
        "mattr_100": round(profile.mattr_100, 4),
        "em_dash_per_kw": round(profile.punct_rates.get("em_dash", 0.0), 2),
    }


def judge_pair(
    judge: LLMAdapter, brief: str, persona: Persona, text_a: str, text_b: str
) -> dict:
    """One ordered comparison. Callers must also run the swapped order and keep
    only order-stable verdicts (position-bias mitigation)."""
    response = judge.complete(
        system=_JUDGE_SYSTEM,
        user=_JUDGE_PROMPT.format(
            brief=brief, rules=persona.rules_block(), text_a=text_a, text_b=text_b
        ),
        max_tokens=200,
        temperature=0.0,
        label="judge",
    )
    try:
        return _parse_json_object(response.text)
    except ValueError:
        return {"error": "unparseable judge output"}


def judge_symmetric(
    judge: LLMAdapter, brief: str, persona: Persona, text_a: str, text_b: str
) -> dict:
    """Both orders; a dimension counts only if the verdict survives the swap."""
    forward = judge_pair(judge, brief, persona, text_a, text_b)
    backward = judge_pair(judge, brief, persona, text_b, text_a)
    stable: dict[str, str] = {}
    for key in ("voice_fidelity", "freshness", "coherence", "overall"):
        f_verdict = forward.get(key)
        b_verdict = backward.get(key)
        if f_verdict in ("A", "B") and b_verdict in ("A", "B") and f_verdict != b_verdict:
            # e.g. forward says A, backward says B: same underlying text won twice.
            stable[key] = f_verdict
        else:
            stable[key] = "unstable"
    return {"stable": stable, "forward": forward, "backward": backward}


def run_item(
    item: BenchItem,
    adapter: LLMAdapter,
    persona: Persona,
    results_dir: Path,
    target_words: int = 900,
    pangram: PangramClient | None = None,
) -> dict:
    """Generate one (brief, persona, condition, provider) cell and score it."""
    out_path = results_dir / f"{item.brief_id}__{item.persona_name}__{item.condition}__{item.provider}.json"
    if out_path.exists():
        return json.loads(out_path.read_text(encoding="utf-8"))
    started = time.time()
    if item.condition == "dwl":
        text = generate_dwl(
            adapter, persona, item.brief, target_words, results_dir / "dwl-runs"
        )
    else:
        text = _GENERATORS[item.condition](adapter, persona, item.brief, target_words)
    result = {
        "item": item.__dict__,
        "text": text,
        "metrics": deterministic_metrics(text, persona),
        "elapsed_s": round(time.time() - started, 1),
        "budget": getattr(adapter, "budget", Budget()).summary(),
    }
    if pangram is not None and pangram.available:
        result["pangram"] = pangram.score(text)
    results_dir.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps(result, indent=2), encoding="utf-8")
    return result
