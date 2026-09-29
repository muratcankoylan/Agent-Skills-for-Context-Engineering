"""Persona compilation: writer corpus -> reusable persona artifact.

Three layers, in order of trustworthiness:

1. Deterministic stylometry (code, no model): the measurable fingerprint and
   the target distribution the critic enforces. Reproducible on any machine.
2. Tacit knowledge (LLM extraction): craft rules that stylometry cannot see;
   how the writer opens, builds and lands arguments, what they refuse to do,
   stance, register, and characteristic moves. Extracted as *checkable*
   imperatives, because they become the critic's rubric verbatim.
3. Exemplar bank (code selects, model tags): real passages retrieved into the
   drafter prompt so style is shown, not only described. EMNLP 2025 findings
   ("Catch Me If You Can? Not Yet") show raw few-shot samples alone fail to
   transfer implicit style; explicit rules plus curated exemplars is the
   mitigation the literature points to. This stage is that mitigation.

The compiled artifact is a single persona.json, versioned with a content hash
of the corpus, so every run records exactly which persona snapshot it used.
"""

from __future__ import annotations

import hashlib
import json
import time
from dataclasses import dataclass, field
from pathlib import Path

from .adapters.base import LLMAdapter
from .stylometry import StyleProfile, compute_profile, describe_rhythm
from .textseg import split_paragraphs, split_sentences, words

_EXTRACTION_SYSTEM = (
    "You are a forensic writing analyst. You extract a writer's tacit craft knowledge "
    "from samples of their prose. You state only what the samples support. You write "
    "rules as short, checkable imperatives that a different writer could follow and an "
    "editor could verify. Never praise the writer. Never use generic advice that would "
    "apply to any competent writer."
)

_EXTRACTION_PROMPT = """Below are writing samples from one author.

Extract their tacit craft knowledge as JSON with exactly these keys:

- "voice": 2-4 sentences describing stance, register, and relationship to the reader.
- "argument_moves": list of 4-8 rules for how this author structures and advances a piece
  (how they open, how they escalate, how they use evidence, how they land endings).
- "sentence_moves": list of 4-8 rules at sentence level (syntax habits, rhythm tricks,
  how they handle emphasis, irony, qualification).
- "vocabulary": 2-3 sentences on word choice (register bands, concreteness, what fields
  they draw imagery from).
- "never_do": list of 4-8 things this author demonstrably avoids that a generic
  assistant would otherwise produce (hedging patterns, cliches, structures).
- "signature_risks": list of 2-4 ways an imitation of this author typically fails
  (overdoing a tic, flattening their range).

Every rule must be specific enough that a critic could mark a sentence as passing or
failing it. Output only the JSON object.

SAMPLES:
{samples}"""


@dataclass
class Persona:
    name: str
    corpus_hash: str
    compiled_at: float
    style: StyleProfile
    tacit: dict = field(default_factory=dict)
    exemplars: list[dict] = field(default_factory=list)
    corpus_text: str = ""  # retained for the slop profiler's reference distribution

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "corpus_hash": self.corpus_hash,
            "compiled_at": self.compiled_at,
            "style": self.style.to_dict(),
            "tacit": self.tacit,
            "exemplars": self.exemplars,
            "corpus_text": self.corpus_text,
        }

    @classmethod
    def from_dict(cls, data: dict) -> Persona:
        return cls(
            name=data["name"],
            corpus_hash=data["corpus_hash"],
            compiled_at=data["compiled_at"],
            style=StyleProfile.from_dict(data["style"]),
            tacit=data.get("tacit", {}),
            exemplars=data.get("exemplars", []),
            corpus_text=data.get("corpus_text", ""),
        )

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(self.to_dict(), indent=2), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> Persona:
        return cls.from_dict(json.loads(path.read_text(encoding="utf-8")))

    # ----- prompt rendering -----

    def rules_block(self) -> str:
        """The tacit layer rendered for drafter and critic prompts."""
        tacit = self.tacit or {}
        lines: list[str] = []
        if tacit.get("voice"):
            lines.append(f"VOICE: {tacit['voice']}")
        for key, title in [
            ("argument_moves", "ARGUMENT MOVES"),
            ("sentence_moves", "SENTENCE MOVES"),
            ("never_do", "NEVER DO"),
            ("signature_risks", "IMITATION RISKS (do not overcorrect into these)"),
        ]:
            items = tacit.get(key) or []
            if items:
                lines.append(title + ":")
                lines.extend(f"- {item}" for item in items)
        if tacit.get("vocabulary"):
            lines.append(f"VOCABULARY: {tacit['vocabulary']}")
        lines.append("RHYTHM TARGETS: " + describe_rhythm(self.style))
        return "\n".join(lines)

    def exemplar_block(self, tags: list[str] | None = None, limit: int = 3) -> str:
        pool = self.exemplars
        if tags:
            tagged = [e for e in pool if e.get("tag") in tags]
            pool = tagged or pool
        chosen = pool[:limit]
        if not chosen:
            return ""
        parts = [f"[{e.get('tag', 'passage')}]\n{e['text']}" for e in chosen]
        return "EXEMPLARS FROM THE AUTHOR (match texture, never copy phrases):\n\n" + "\n\n".join(parts)


def _select_exemplars(text: str, max_exemplars: int = 8) -> list[dict]:
    """Deterministic exemplar selection: paragraph-sized passages spanning the
    corpus, tagged by position (opening/body/closing) plus rhythm outliers."""
    paragraphs = [p for p in split_paragraphs(text) if 40 <= len(words(p)) <= 220]
    if not paragraphs:
        paragraphs = split_paragraphs(text)[:max_exemplars]
    exemplars: list[dict] = []
    if paragraphs:
        exemplars.append({"tag": "opening", "text": paragraphs[0]})
        if len(paragraphs) > 2:
            exemplars.append({"tag": "closing", "text": paragraphs[-1]})
        # Evenly spaced body passages.
        body = paragraphs[1:-1] if len(paragraphs) > 2 else []
        step = max(len(body) // max(max_exemplars - 4, 1), 1)
        for para in body[::step][: max_exemplars - 4]:
            exemplars.append({"tag": "body", "text": para})
        # One short-sentence-heavy passage, if the author has one: rhythm exemplar.
        punchy = [
            p for p in body
            if (sentences := split_sentences(p)) and sum(len(words(s)) for s in sentences) / len(sentences) < 12
        ]
        if punchy:
            exemplars.append({"tag": "punchy", "text": punchy[0]})
    return exemplars[:max_exemplars]


def read_corpus(corpus_dir: Path) -> str:
    files = sorted(corpus_dir.glob("*.txt")) + sorted(corpus_dir.glob("*.md"))
    if not files:
        raise FileNotFoundError(f"no .txt or .md files in {corpus_dir}")
    return "\n\n".join(f.read_text(encoding="utf-8").strip() for f in files)


def _sample_for_extraction(text: str, cap_chars: int = 24_000) -> str:
    """Give the extractor spread rather than a prefix: head, middle, tail."""
    if len(text) <= cap_chars:
        return text
    third = cap_chars // 3
    mid = len(text) // 2
    return "\n\n[...]\n\n".join(
        [text[:third], text[mid - third // 2 : mid + third // 2], text[-third:]]
    )


def compile_persona(
    name: str,
    corpus_dir: Path,
    adapter: LLMAdapter | None = None,
) -> Persona:
    """Compile a persona. The deterministic layers always succeed; the tacit
    layer requires an adapter and fails loudly (a persona without craft rules
    is a different, weaker artifact, and the caller should know)."""
    text = read_corpus(corpus_dir)
    corpus_hash = hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]
    persona = Persona(
        name=name,
        corpus_hash=corpus_hash,
        compiled_at=time.time(),
        style=compute_profile(text),
        exemplars=_select_exemplars(text),
        corpus_text=text,
    )
    if adapter is not None:
        response = adapter.complete(
            system=_EXTRACTION_SYSTEM,
            user=_EXTRACTION_PROMPT.format(samples=_sample_for_extraction(text)),
            max_tokens=2000,
            temperature=0.3,
            label=f"persona-extract:{name}",
        )
        persona.tacit = _parse_json_object(response.text)
    return persona


def _parse_json_object(raw: str) -> dict:
    """Extract the first JSON object from a model response, tolerating fences."""
    raw = raw.strip()
    if raw.startswith("```"):
        raw = raw.split("```", 2)[1]
        raw = raw.split("\n", 1)[1] if "\n" in raw else raw
    start, end = raw.find("{"), raw.rfind("}")
    if start == -1 or end <= start:
        raise ValueError(f"extractor did not return a JSON object: {raw[:200]!r}")
    return json.loads(raw[start : end + 1])
