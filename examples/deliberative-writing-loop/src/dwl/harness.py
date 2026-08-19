"""The loop controller. Every artifact lands on disk; every run is resumable.

State machine per document:
    PLAN -> [for each paragraph: DRAFT -> CRITIQUE -> (REPAIR -> CRITIQUE)*k -> COMMIT] -> FINAL

Bounded repair (default 2 rounds) is a finding from the refinement literature,
not a cost shortcut: trajectories saturate in a few iterations and further
rounds drift toward model-preferred text. If a paragraph still fails after k
rounds, the harness keeps the best version by deterministic flag count and
records the residual flags: an honest artifact beats a silently polished one.

Repeated critique categories are compacted into standing lessons (RunMemory),
so paragraph N+1 is drafted under corrections learned from paragraphs 1..N.
"""

from __future__ import annotations

import json
import re
import time
import uuid
from dataclasses import dataclass
from pathlib import Path

from .adapters.base import LLMAdapter
from .critic import critique_paragraph, deterministic_critique
from .drafter import draft_paragraph, repair_paragraph, summarize_paragraph
from .memory import RunMemory
from .persona import Persona
from .planner import Plan, make_plan
from .sloplex import SlopProfiler
from .stylometry import compute_profile, style_distance


@dataclass
class RunConfig:
    target_words: int = 1000
    max_repairs_per_paragraph: int = 2
    runs_dir: Path = Path("runs")


def _category_of(flag: str) -> str:
    """Stable category key for lesson promotion: the flag kind, plus the flagged
    token for ratio findings so lessons stay specific."""
    head = flag.split(":", 1)[0].strip()
    match = re.search(r"'([^']+)'", flag)
    return f"{head}:{match.group(1)}" if match else head


class WritingRun:
    def __init__(
        self,
        adapter: LLMAdapter,
        persona: Persona,
        brief: str,
        config: RunConfig | None = None,
        run_id: str | None = None,
    ) -> None:
        self.adapter = adapter
        self.persona = persona
        self.brief = brief
        self.config = config or RunConfig()
        self.run_id = run_id or time.strftime("%Y%m%d-%H%M%S-") + uuid.uuid4().hex[:6]
        self.run_dir = self.config.runs_dir / self.run_id
        self.memory = RunMemory()
        self.profiler = SlopProfiler(persona.corpus_text)
        self.plan: Plan | None = None

    # ----- artifact helpers -----

    def _write(self, relative: str, payload: str | dict) -> None:
        path = self.run_dir / relative
        path.parent.mkdir(parents=True, exist_ok=True)
        if isinstance(payload, dict):
            path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
        else:
            path.write_text(payload, encoding="utf-8")

    # ----- stages -----

    def run(self) -> str:
        self._write("brief.md", self.brief)
        self._write("persona-snapshot.json", {
            "name": self.persona.name,
            "corpus_hash": self.persona.corpus_hash,
            "style": self.persona.style.to_dict(),
            "tacit": self.persona.tacit,
        })
        self.plan = make_plan(self.adapter, self.persona, self.brief, self.config.target_words)
        self._write("plan.json", self.plan.to_dict())

        final_paragraphs: list[str] = []
        n = len(self.plan.contracts)
        for index, contract in enumerate(self.plan.contracts):
            position = "opening" if index == 0 else ("closing" if index == n - 1 else f"body {index + 1}/{n}")
            text = self._paragraph_loop(index, position, contract)
            final_paragraphs.append(text)
            self._commit(index, text)

        final = "\n\n".join(final_paragraphs)
        self._write("final.md", final)
        self._write("metrics.json", self._final_metrics(final))
        self._write("memory.json", self.memory.to_dict())
        budget = getattr(self.adapter, "budget", None)
        if budget is not None:
            self._write("budget.json", budget.summary())
        return final

    def _paragraph_loop(self, index: int, position: str, contract) -> str:
        prefix = f"paragraphs/p{index + 1:02d}"
        draft = draft_paragraph(
            self.adapter, self.persona, contract, self.memory.render_context(), position
        )
        self._write(f"{prefix}/draft-v1.md", draft)

        best_text, best_flag_count = draft, None
        for round_number in range(1, self.config.max_repairs_per_paragraph + 2):
            critique = critique_paragraph(
                self.adapter, draft, self.persona, contract, self.memory, self.profiler
            )
            self._write(f"{prefix}/critique-v{round_number}.json", critique.to_dict())
            for flag in critique.flags:
                category = _category_of(flag)
                self.memory.observe_finding(
                    category, f"Recurring issue in this piece, avoid it: {flag[:180]}"
                )
            det_count = len(critique.deterministic.get("rhythm_flags", [])) + len(
                critique.deterministic.get("reused_phrases", [])
            ) + len(critique.deterministic.get("slop", {}).get("findings", []))
            if best_flag_count is None or det_count < best_flag_count:
                best_text, best_flag_count = draft, det_count
            if critique.verdict == "pass" or round_number > self.config.max_repairs_per_paragraph:
                if critique.verdict != "pass":
                    self._write(
                        f"{prefix}/residual-flags.json",
                        {"flags": critique.flags, "kept_version": "best-by-deterministic-count"},
                    )
                    draft = best_text
                break
            draft = repair_paragraph(self.adapter, self.persona, draft, critique.flags)
            self._write(f"{prefix}/draft-v{round_number + 1}.md", draft)
        return draft

    def _commit(self, index: int, text: str) -> None:
        summary_data = summarize_paragraph(self.adapter, text)
        summary = summary_data["summary"] or self.memory.fallback_summary(text)
        self.memory.commit_paragraph(index, text, summary, summary_data["claims"])
        self.memory.images_used.extend(summary_data["images"])
        self._write(f"paragraphs/p{index + 1:02d}/trace-summary.md", summary)

    def _final_metrics(self, final: str) -> dict:
        candidate_profile = compute_profile(final)
        slop = self.profiler.score(final)
        # A dummy contract for whole-document deterministic reporting.
        from .planner import ParagraphContract

        _, det_report = deterministic_critique(
            final,
            self.persona,
            ParagraphContract(job="whole document", target_sentences=candidate_profile.sentence_count),
            RunMemory(),  # fresh memory: echo within the doc is caught by the profiler
            self.profiler,
        )
        return {
            "word_count": candidate_profile.word_count,
            "style_distance_to_persona": round(
                style_distance(candidate_profile, self.persona.style), 4
            ),
            "slop_score": round(slop.score, 3),
            "slop_findings": [f.to_dict() for f in slop.findings],
            "deterministic_report": det_report,
            "lessons_learned": self.memory.lessons,
        }
