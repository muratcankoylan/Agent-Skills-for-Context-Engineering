"""End-to-end harness run over the mock adapter with a scripted call sequence.

Call order for a 2-paragraph plan where both drafts pass critique:
    1 plan -> 2 draft p1 -> 3 rubric p1 -> 4 summary p1
           -> 5 draft p2 -> 6 rubric p2 -> 7 summary p2
"""

import json
from pathlib import Path

import pytest

from dwl.adapters.base import Budget, BudgetExceeded, MockAdapter
from dwl.harness import RunConfig, WritingRun
from dwl.persona import compile_persona

CORPUS_DIR = Path(__file__).parent.parent / "personas" / "sample-essayist" / "corpus"

PLAN = {
    "thesis": "Judgment, not process, is the deliverable.",
    "title": "The Ledger of Decisions",
    "paragraphs": [
        {
            "job": "Establish the test for a real decision.",
            "must_carry": [],
            "entry": "cold open",
            "exit": "reader suspects their own calendar",
            "target_sentences": 4,
        },
        {
            "job": "Land the practice-over-acquisition point.",
            "must_carry": [],
            "entry": "picks up from blame",
            "exit": "imperative close",
            "target_sentences": 4,
        },
    ],
}

# Drafts are built to pass deterministic gates: varied lengths and openers,
# no repeated content n-grams, no em-dashes, no cross-paragraph echo.
DRAFT_P1 = (
    "The test is simple. Ask what the meeting decided, and who will carry the work "
    "home before Friday. Nobody enjoys the exercise, because every decision has a name "
    "attached to it, and names can be blamed when boards get cut. Judgment is the deliverable."
)
DRAFT_P2 = (
    "Practice beats acquisition. A journeyman learns his craft by copying the master "
    "until both hands stop asking permission. No catalog sells that, though every spring "
    "brings new machinery and fresh promises of progress. Buy less, build more."
)

RUBRIC_PASS = json.dumps({"flags": [], "verdict": "pass"})
SUMMARY_P1 = json.dumps(
    {"summary": "Defines the test for a real decision.", "claims": ["Judgment is the deliverable"], "images": []}
)
SUMMARY_P2 = json.dumps(
    {"summary": "Lands practice over acquisition.", "claims": [], "images": ["catalog"]}
)


def _run(tmp_path) -> tuple[WritingRun, str, MockAdapter]:
    persona = compile_persona("sample", CORPUS_DIR)
    adapter = MockAdapter(
        responses=[
            json.dumps(PLAN),
            DRAFT_P1, RUBRIC_PASS, SUMMARY_P1,
            DRAFT_P2, RUBRIC_PASS, SUMMARY_P2,
        ]
    )
    run = WritingRun(
        adapter, persona, "Write about decisions.",
        RunConfig(target_words=200, runs_dir=tmp_path),
    )
    final = run.run()
    return run, final, adapter


def test_full_run_produces_document(tmp_path):
    _run_obj, final, adapter = _run(tmp_path)
    assert DRAFT_P1 in final and DRAFT_P2 in final
    assert final.count("\n\n") == 1
    # All queued responses consumed in order; no extra calls made.
    assert adapter.responses == []
    labels = [c["label"] for c in adapter.calls]
    assert labels == ["plan", "draft:opening", "rubric", "summarize", "draft:closing", "rubric", "summarize"]


def test_artifacts_on_disk(tmp_path):
    run, _, _ = _run(tmp_path)
    d = run.run_dir
    for rel in [
        "brief.md", "plan.json", "final.md", "metrics.json", "memory.json",
        "persona-snapshot.json", "budget.json",
        "paragraphs/p01/draft-v1.md", "paragraphs/p01/critique-v1.json",
        "paragraphs/p01/trace-summary.md", "paragraphs/p02/draft-v1.md",
    ]:
        assert (d / rel).exists(), rel
    metrics = json.loads((d / "metrics.json").read_text())
    assert "style_distance_to_persona" in metrics
    assert metrics["word_count"] > 50


def test_memory_carries_between_paragraphs(tmp_path):
    _, _, adapter = _run(tmp_path)
    p2_draft_prompt = adapter.calls[4]["user"]
    # The drafter for paragraph 2 sees paragraph 1's summary and verbatim text.
    assert "Defines the test for a real decision." in p2_draft_prompt
    assert "Judgment is the deliverable." in p2_draft_prompt
    assert "CLAIMS ALREADY MADE" in p2_draft_prompt


def test_repair_path_and_residual_flags(tmp_path):
    persona = compile_persona("sample", CORPUS_DIR)
    plan_one = {
        "thesis": "t", "title": "t",
        "paragraphs": [{"job": "one paragraph", "target_sentences": 4}],
    }
    # Draft with an opener run: deterministic critique flags it regardless of rubric.
    bad = (
        "Smith's plan was simple. Smith's methods were not. Smith's creditors knew both. "
        "The bank learned last."
    )
    rubric = json.dumps({"flags": [], "verdict": "pass"})
    adapter = MockAdapter(
        responses=[
            json.dumps(plan_one),
            bad, rubric,            # v1 draft + rubric; deterministic flags force repair
            bad, rubric,            # repair returns same bad text; flagged again
            bad, rubric,            # second repair; still bad; loop exhausts
            json.dumps({"summary": "s", "claims": [], "images": []}),
        ]
    )
    run = WritingRun(
        adapter, persona, "brief",
        RunConfig(target_words=100, max_repairs_per_paragraph=2, runs_dir=tmp_path),
    )
    run.run()
    assert (run.run_dir / "paragraphs/p01/residual-flags.json").exists()
    residual = json.loads((run.run_dir / "paragraphs/p01/residual-flags.json").read_text())
    assert any("opener" in flag for flag in residual["flags"])
    # The repeated finding was promoted to a standing lesson.
    assert run.memory.lessons


def test_budget_exceeded_stops_run(tmp_path):
    persona = compile_persona("sample", CORPUS_DIR)
    adapter = MockAdapter(responses=[json.dumps(PLAN), DRAFT_P1])
    adapter.budget = Budget(max_calls=2, max_usd=1.0)
    run = WritingRun(adapter, persona, "brief", RunConfig(runs_dir=tmp_path))
    with pytest.raises(BudgetExceeded):
        run.run()
