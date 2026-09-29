"""Hierarchical planning: brief -> thesis -> paragraph contracts.

The DOC finding (ACL 2023) drives this stage: shifting creative burden from
drafting to planning is what buys long-range coherence. A contract makes each
paragraph's job explicit so the drafter improvises texture, not structure, and
the critic has something objective to check against.
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field

from .adapters.base import LLMAdapter
from .persona import Persona, _parse_json_object

_PLANNER_SYSTEM = (
    "You are a senior editor planning a piece before it is written. You produce paragraph "
    "contracts: precise jobs, not vague topics. You think in arguments, not sections. "
    "Output only valid JSON."
)

_PLANNER_PROMPT = """Plan a piece of writing.

BRIEF:
{brief}

TARGET LENGTH: about {target_words} words.

AUTHOR PROFILE (the piece must be plannable in this voice):
{rules}

Output JSON with exactly these keys:
- "thesis": one sentence stating the piece's central claim or through-line.
- "title": a working title in the author's register.
- "paragraphs": a list of {n_paragraphs}-{n_paragraphs_max} objects, each with:
  - "job": what this paragraph must accomplish in the argument (one sentence,
    specific: not "discuss X" but "establish that X fails because Y").
  - "must_carry": list of 0-3 specific facts, examples, quotes, or images this
    paragraph must contain (from the brief; never invent facts).
  - "entry": how it picks up from the previous paragraph (one clause).
  - "exit": the state the reader should be in when it ends (one clause).
  - "target_sentences": integer, how many sentences (vary this across paragraphs;
    respect the author's rhythm profile).

The first paragraph must open the way this author opens. The last must land the
way this author lands. Output only the JSON object."""


@dataclass
class ParagraphContract:
    job: str
    must_carry: list[str] = field(default_factory=list)
    entry: str = ""
    exit: str = ""
    target_sentences: int = 5

    def to_dict(self) -> dict:
        return {
            "job": self.job,
            "must_carry": self.must_carry,
            "entry": self.entry,
            "exit": self.exit,
            "target_sentences": self.target_sentences,
        }

    def render(self) -> str:
        lines = [f"JOB: {self.job}"]
        if self.must_carry:
            lines.append("MUST CARRY: " + "; ".join(self.must_carry))
        if self.entry:
            lines.append(f"ENTRY: {self.entry}")
        if self.exit:
            lines.append(f"EXIT: {self.exit}")
        lines.append(f"TARGET: about {self.target_sentences} sentences.")
        return "\n".join(lines)


@dataclass
class Plan:
    thesis: str
    title: str
    contracts: list[ParagraphContract]

    def to_dict(self) -> dict:
        return {
            "thesis": self.thesis,
            "title": self.title,
            "paragraphs": [c.to_dict() for c in self.contracts],
        }

    @classmethod
    def from_dict(cls, data: dict) -> Plan:
        return cls(
            thesis=data.get("thesis", ""),
            title=data.get("title", ""),
            contracts=[
                ParagraphContract(
                    job=p.get("job", ""),
                    must_carry=list(p.get("must_carry", [])),
                    entry=p.get("entry", ""),
                    exit=p.get("exit", ""),
                    target_sentences=int(p.get("target_sentences", 5)),
                )
                for p in data.get("paragraphs", [])
            ],
        )


def make_plan(
    adapter: LLMAdapter,
    persona: Persona,
    brief: str,
    target_words: int = 1000,
) -> Plan:
    # Paragraph count derived from the persona's own paragraph density.
    words_per_para = max(
        persona.style.sentences_per_paragraph_mean * persona.style.sentence_len_mean, 60.0
    )
    n_paragraphs = max(int(target_words / words_per_para), 4)
    prompt = _PLANNER_PROMPT.format(
        brief=brief,
        target_words=target_words,
        rules=persona.rules_block(),
        n_paragraphs=n_paragraphs,
        n_paragraphs_max=n_paragraphs + 2,
    )
    last_error: Exception | None = None
    for attempt in range(2):
        response = adapter.complete(
            system=_PLANNER_SYSTEM,
            user=prompt if attempt == 0 else prompt + "\n\nYour previous output was not valid JSON. Output only the JSON object.",
            max_tokens=2000,
            temperature=0.5,
            label="plan",
        )
        try:
            plan = Plan.from_dict(_parse_json_object(response.text))
            if plan.contracts:
                return plan
            raise ValueError("plan has no paragraphs")
        except (ValueError, json.JSONDecodeError) as exc:
            last_error = exc
    raise RuntimeError(f"planner failed twice: {last_error}")
