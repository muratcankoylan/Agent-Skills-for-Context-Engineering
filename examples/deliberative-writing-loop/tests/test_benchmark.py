import json
from pathlib import Path

from dwl.adapters.base import MockAdapter
from dwl.benchmark import (
    BenchItem,
    deterministic_metrics,
    generate_selfrefine,
    judge_symmetric,
    run_item,
)
from dwl.persona import compile_persona

CORPUS_DIR = Path(__file__).parent.parent / "personas" / "sample-essayist" / "corpus"


def _persona():
    return compile_persona("sample", CORPUS_DIR)


def test_deterministic_metrics_shape():
    metrics = deterministic_metrics(
        "The invoice tells the truth. Brochures promise; ledgers record.", _persona()
    )
    for key in ("style_distance", "slop_score_per_kw", "word_count", "mattr_100"):
        assert key in metrics


def test_selfrefine_uses_rounds():
    adapter = MockAdapter(responses=["draft zero", "draft one", "draft two"])
    text = generate_selfrefine(adapter, _persona(), "brief", 200, rounds=2)
    assert text == "draft two"
    assert [c["label"] for c in adapter.calls] == ["oneshot", "selfrefine", "selfrefine"]


def test_run_item_writes_and_resumes(tmp_path):
    item = BenchItem(
        brief_id="b00", brief="Write about ledgers.", persona_name="sample",
        condition="oneshot", provider="mock",
    )
    adapter = MockAdapter(responses=["The ledger never lies. It only waits."])
    result = run_item(item, adapter, _persona(), tmp_path, target_words=100)
    out = tmp_path / "b00__sample__oneshot__mock.json"
    assert out.exists()
    assert result["metrics"]["word_count"] > 0
    # Resume: a second call must not touch the adapter.
    adapter2 = MockAdapter(responses=[])
    cached = run_item(item, adapter2, _persona(), tmp_path, target_words=100)
    assert cached["text"] == result["text"]
    assert adapter2.calls == []


def test_judge_symmetric_requires_order_stability():
    # Forward says A, backward says B: the same underlying text won both orders -> stable.
    stable_judge = MockAdapter(responses=[
        json.dumps({"voice_fidelity": "A", "freshness": "A", "coherence": "A", "overall": "A"}),
        json.dumps({"voice_fidelity": "B", "freshness": "B", "coherence": "B", "overall": "B"}),
    ])
    verdicts = judge_symmetric(stable_judge, "brief", _persona(), "text one", "text two")
    assert verdicts["stable"]["overall"] == "A"

    # Forward says A, backward says A: position-biased judge -> unstable.
    biased_judge = MockAdapter(responses=[
        json.dumps({"voice_fidelity": "A", "freshness": "A", "coherence": "A", "overall": "A"}),
        json.dumps({"voice_fidelity": "A", "freshness": "A", "coherence": "A", "overall": "A"}),
    ])
    verdicts = judge_symmetric(biased_judge, "brief", _persona(), "text one", "text two")
    assert verdicts["stable"]["overall"] == "unstable"
