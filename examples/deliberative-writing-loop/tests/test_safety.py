"""Offline admission, crash, and cache regressions. No provider calls."""
import json
import socket
from dataclasses import replace
from pathlib import Path

import pytest

from dwl import cli, state
from dwl.adapters import AnthropicAdapter, OpenAIAdapter, PangramClient
from dwl.adapters.base import Budget, BudgetExceeded, LiveExecutionDisabled, MockAdapter
from dwl.benchmark import BenchItem, run_item
from dwl.env import load_env
from dwl.harness import RunConfig, WritingRun
from dwl.persona import compile_persona

CORPUS = Path(__file__).parent.parent / "personas/sample-essayist/corpus"


def persona():
    return compile_persona("sample", CORPUS)


def item(condition="oneshot"):
    return BenchItem("b00", "Write about ledgers.", "sample", condition, "mock")


@pytest.mark.parametrize("value", [float("nan"), float("inf"), -float("inf"), -1, True, "invalid"])
def test_budget_rejects_invalid_dollars(value):
    with pytest.raises(ValueError):
        Budget(max_usd=value)


@pytest.mark.parametrize("value", [True, -1, 10001, 1.5])
def test_budget_rejects_invalid_call_limit(value):
    with pytest.raises(ValueError):
        Budget(max_calls=value)


def test_pending_reservations_survive_restart_and_count_before_effect(tmp_path):
    ledger = tmp_path / "budget.json"
    budget = Budget(max_calls=20, max_usd=.001, ledger_path=ledger)
    for _ in range(3):
        budget.charge("openai", 100, 0)
    restarted = Budget(max_calls=20, max_usd=.001, ledger_path=ledger)
    assert restarted.summary()["liability_microusd"] == 900
    assert restarted.summary()["unknown_calls"] == 3
    with pytest.raises(BudgetExceeded):
        restarted.charge("openai", 100, 0)
    assert restarted.calls == 3
    with pytest.raises(ValueError, match="identity"):
        Budget(max_calls=20, max_usd=.002, ledger_path=ledger)


def test_settlement_identity_validation_and_ceiling_breach(tmp_path):
    budget = Budget(max_usd=1, ledger_path=tmp_path / "budget.json")
    reservation = budget.charge("openai", 100, 0)
    with pytest.raises(ValueError):
        budget.settle("openai", float("nan"), 0, "invalid", reservation)
    assert budget.summary()["unknown_calls"] == 1
    with pytest.raises(ValueError):
        budget.settle("anthropic", 1, 0, "wrong provider", reservation)
    budget.settle("openai", 101, 0, "ceiling breach", reservation)
    assert budget.summary()["liability_microusd"] == 303
    with pytest.raises(ValueError):
        budget.settle("openai", 101, 0, "duplicate", reservation)
    with pytest.raises(BudgetExceeded, match="exceeded estimate"):
        budget.charge("mock", 0, 0)


def test_reservation_failure_does_not_grant_admission(tmp_path, monkeypatch):
    from dwl.adapters import base
    budget = Budget(ledger_path=tmp_path / "budget.json")
    write = base.atomic_json
    def fail(*args):
        raise OSError("fixture disk failure")
    monkeypatch.setattr(base, "atomic_json", fail)
    with pytest.raises(OSError):
        budget.charge("openai", 100, 0)
    monkeypatch.setattr(base, "atomic_json", write)
    assert Budget(ledger_path=tmp_path / "budget.json").calls == 0


@pytest.mark.parametrize("changed", ["brief", "target_words", "model", "persona", "limits", "source"])
def test_cache_identity_changes_refuse_before_call(tmp_path, monkeypatch, changed):
    original = item()
    run_item(original, MockAdapter(responses=["Original ledger text."]), persona(), tmp_path, 100)
    candidate, adapter, writer, target = original, MockAdapter(), persona(), 100
    if changed == "brief":
        candidate = replace(original, brief="A different brief.")
    elif changed == "target_words":
        target = 999
    elif changed == "model":
        adapter.model = "mock-2"
    elif changed == "persona":
        writer.tacit = {"different": "content"}
    elif changed == "limits":
        adapter.budget = Budget(max_calls=9999, max_usd=1)
    else:
        monkeypatch.setattr(state, "source_digest", lambda: "different-source")
    with pytest.raises(ValueError, match="identity"):
        run_item(candidate, adapter, writer, tmp_path, target)
    assert adapter.calls == []


def test_unknown_effect_and_receipt_commit_failure_never_replay(tmp_path, monkeypatch):
    receipt = tmp_path / "operation.json"
    effects = []
    write = state.atomic_json
    def fail_completion(path, value):
        if value["status"] == "completed":
            raise OSError("fixture completion failure")
        write(path, value)
    monkeypatch.setattr(state, "atomic_json", fail_completion)
    with pytest.raises(OSError):
        state.run_once(receipt, {"input": 1}, lambda: effects.append("effect"))
    monkeypatch.setattr(state, "atomic_json", write)
    with pytest.raises(RuntimeError, match="unknown"):
        state.run_once(receipt, {"input": 1}, lambda: effects.append("duplicate"))
    assert effects == ["effect"]


def test_corrupt_completed_receipt_refused(tmp_path):
    receipt = tmp_path / "operation.json"
    state.run_once(receipt, {"input": 1}, lambda: {"answer": "one"})
    record = state.read_json(receipt)
    record["result"]["answer"] = "tampered"
    state.atomic_json(receipt, record)
    with pytest.raises(ValueError, match="malformed"):
        state.run_once(receipt, {"input": 1}, lambda: pytest.fail("must not repeat"))


def test_invalid_cell_path_and_legacy_cache_refused(tmp_path):
    with pytest.raises(ValueError):
        run_item(replace(item(), brief_id="../escape"), MockAdapter(), persona(), tmp_path)
    (tmp_path / "b00__sample__oneshot__mock.json").write_text('{"text":"old"}')
    with pytest.raises(ValueError):
        run_item(item(), MockAdapter(), persona(), tmp_path)


def test_writing_run_completed_cache_and_changed_repairs(tmp_path, monkeypatch):
    calls = []
    monkeypatch.setattr(WritingRun, "_execute", lambda self: calls.append(1) or "finished")
    def run(repairs=2):
        return WritingRun(MockAdapter(), persona(), "brief",
                          RunConfig(100, repairs, tmp_path), run_id="fixed").run()
    assert run() == run() == "finished"
    assert calls == [1]
    with pytest.raises(ValueError, match="identity"):
        run(3)


def judge_fixture(tmp_path):
    result_dir, personas = tmp_path / "results", tmp_path / "personas"
    writer = persona()
    persona_dir = personas / "sample"
    persona_dir.mkdir(parents=True)
    writer.save(persona_dir / "persona.json")
    for condition in ("dwl", "oneshot"):
        record = {"item": item(condition).__dict__, "text": condition + " text"}
        state.run_once(result_dir / f"b00__sample__{condition}__mock.json",
                       {"fixture": condition}, lambda record=record: record)
    return result_dir, personas


def test_repeated_judge_ignores_aggregate_and_reuses_exact_pair(tmp_path, monkeypatch):
    results, personas = judge_fixture(tmp_path)
    calls = []
    def adapter(provider, model, budget):
        result = MockAdapter(responses=['{"overall":"A"}', '{"overall":"B"}'], budget=budget)
        calls.append(result)
        return result
    monkeypatch.setattr(cli, "make_adapter", adapter)
    args = ["judge", "--results", str(results), "--personas", str(personas), "--judges", "mock"]
    assert cli.main(args) == cli.main(args) == 0
    assert [len(a.calls) for a in calls] == [2, 0]
    ledger = Budget(200, 10, results / ".state/judge-budget.json")
    assert ledger.calls == 2
    assert json.loads((results / "judgments.json").read_text())[0]["stable"]["overall"] == "A"
    writer = persona()
    writer.tacit = {"new": "rules"}
    writer.save(personas / "sample/persona.json")
    with pytest.raises(ValueError, match="identity"):
        cli.main(args)
    assert calls[-1].calls == []


def test_partial_judge_pair_blocks_repeated_calls(tmp_path, monkeypatch):
    results, personas = judge_fixture(tmp_path)
    calls = []
    class Interrupted(MockAdapter):
        def complete(self, *args, **kwargs):
            response = super().complete(*args, **kwargs)
            calls.append(1)
            if len(calls) == 2:
                raise OSError("fixture lost response")
            return response
    monkeypatch.setattr(cli, "make_adapter", lambda provider, model, budget: Interrupted(budget=budget))
    args = ["judge", "--results", str(results), "--personas", str(personas), "--judges", "mock"]
    with pytest.raises(OSError):
        cli.main(args)
    with pytest.raises(RuntimeError, match="unknown"):
        cli.main(args)
    assert len(calls) == 2


def test_paid_adapters_and_detector_refuse_even_with_keys(tmp_path, monkeypatch):
    for key in ("OPENAI_API_KEY", "ANTHROPIC_API_KEY", "PANGRAM_API_KEY"):
        monkeypatch.setenv(key, "synthetic-not-a-secret")
    monkeypatch.setattr(socket, "socket", lambda *a, **kw: pytest.fail("network forbidden"))
    for adapter in (OpenAIAdapter(), AnthropicAdapter()):
        with pytest.raises(LiveExecutionDisabled):
            adapter.complete("system", "user")
        assert adapter.budget.calls == 0
    detector = PangramClient(enabled=True)
    assert not detector.available
    with pytest.raises(LiveExecutionDisabled):
        detector.score("fixture")
    generation = MockAdapter()
    with pytest.raises(LiveExecutionDisabled, match="detector"):
        run_item(item(), generation, persona(), tmp_path, pangram=detector)
    assert generation.calls == []
    with pytest.raises(LiveExecutionDisabled):
        cli.main(["compile-persona", "--name", "sample", "--corpus", str(CORPUS), "--provider", "openai"])


def test_model_and_endpoint_resolve_after_env_load(tmp_path, monkeypatch):
    # Adapter modules have already been imported above, before this file is loaded.
    names = ["DWL_OPENAI_MODEL", "DWL_OPENAI_URL", "DWL_ANTHROPIC_MODEL", "DWL_ANTHROPIC_URL"]
    for name in names:
        monkeypatch.delenv(name, raising=False)
    env_file = tmp_path / "fixture.env"
    env_file.write_text("\n".join(f"{name}=fixture-{name}" for name in names))
    load_env(env_file)
    try:
        assert OpenAIAdapter().model == "fixture-DWL_OPENAI_MODEL"
        assert OpenAIAdapter().endpoint == "fixture-DWL_OPENAI_URL"
        assert AnthropicAdapter().model == "fixture-DWL_ANTHROPIC_MODEL"
        assert AnthropicAdapter().endpoint == "fixture-DWL_ANTHROPIC_URL"
    finally:
        for name in names:
            monkeypatch.delenv(name, raising=False)


def test_forecast_rejects_nonfinite_budget_without_reading_inputs():
    with pytest.raises(ValueError):
        cli.main(["write", "--persona", "missing", "--brief", "missing", "--max-usd", "nan", "--dry-run"])
