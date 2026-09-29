"""Paragraph drafting under contract, and targeted sentence repair.

The paragraph is the generation unit; the sentence is the repair unit. Whole
paragraphs get drafted so rhythm and transitions are composed, not stitched;
individual failing sentences get rewritten in place so a repair cannot degrade
sentences that already passed (the known failure of whole-document refinement,
which converges to model-preferred slop rather than the persona's register).
"""

from __future__ import annotations

from .adapters.base import LLMAdapter
from .persona import Persona
from .planner import ParagraphContract

_DRAFTER_SYSTEM = """You are ghostwriting as a specific author. You have their craft rules, rhythm
targets, and exemplar passages. You write one paragraph at a time under an
editor's contract. You never use filler, never restate what the document has
already established, and never reuse phrases marked as spent.

Write the paragraph only. No preamble, no title, no commentary, no markdown."""

_DRAFT_PROMPT = """{rules}

{exemplars}

{memory}

CONTRACT FOR THIS PARAGRAPH ({position}):
{contract}

Write the paragraph now, in the author's voice, obeying the contract."""

_REPAIR_PROMPT = """{rules}

CONTEXT: this paragraph appears in a longer piece. Paragraph as it stands:

{paragraph}

An editor flagged specific sentences. Rewrite ONLY the flagged sentences; keep every
other sentence exactly as written. Preserve the paragraph's argument and its
connections to what surrounds it.

FLAGS:
{flags}

Output the full corrected paragraph only. No commentary."""

_SUMMARY_PROMPT = """Summarize this paragraph in one sentence (what it establishes), then list any
new claims it makes and any images or metaphors it uses.

Output JSON only: {{"summary": "...", "claims": ["..."], "images": ["..."]}}

PARAGRAPH:
{paragraph}"""


def draft_paragraph(
    adapter: LLMAdapter,
    persona: Persona,
    contract: ParagraphContract,
    memory_context: str,
    position: str,
    temperature: float = 0.8,
) -> str:
    tags = ["opening"] if position == "opening" else (
        ["closing"] if position == "closing" else ["body", "punchy"]
    )
    prompt = _DRAFT_PROMPT.format(
        rules=persona.rules_block(),
        exemplars=persona.exemplar_block(tags=tags),
        memory=memory_context or "This is the first paragraph of the piece.",
        position=position,
        contract=contract.render(),
    )
    response = adapter.complete(
        system=_DRAFTER_SYSTEM,
        user=prompt,
        max_tokens=900,
        temperature=temperature,
        label=f"draft:{position}",
    )
    return response.text.strip()


def repair_paragraph(
    adapter: LLMAdapter,
    persona: Persona,
    paragraph: str,
    flags: list[str],
    temperature: float = 0.6,
) -> str:
    response = adapter.complete(
        system=_DRAFTER_SYSTEM,
        user=_REPAIR_PROMPT.format(
            rules=persona.rules_block(),
            paragraph=paragraph,
            flags="\n".join(f"- {flag}" for flag in flags),
        ),
        max_tokens=900,
        temperature=temperature,
        label="repair",
    )
    return response.text.strip()


def summarize_paragraph(adapter: LLMAdapter, paragraph: str) -> dict:
    from .persona import _parse_json_object

    response = adapter.complete(
        system="You are a precise note-taker. Output only JSON.",
        user=_SUMMARY_PROMPT.format(paragraph=paragraph),
        max_tokens=300,
        temperature=0.2,
        label="summarize",
    )
    try:
        data = _parse_json_object(response.text)
    except ValueError:
        return {"summary": "", "claims": [], "images": []}
    return {
        "summary": str(data.get("summary", ""))[:300],
        "claims": [str(c) for c in data.get("claims", [])][:4],
        "images": [str(i) for i in data.get("images", [])][:4],
    }
