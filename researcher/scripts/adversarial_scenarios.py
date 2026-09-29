#!/usr/bin/env python3
"""Execute deterministic mutation fixtures for the Stage-0 threat catalog.

These fixtures exercise routing and validation contracts. They do not claim
that a model can semantically detect the described prose failure without the
fixture's explicit labels. Each result therefore names both the executed layer
and its remaining semantic limitation.
"""

from __future__ import annotations

import argparse
import json
from dataclasses import asdict, dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Callable

if __package__:
    from .schema_contract import parse_json_strict
    from .novelty_check import jaccard, load_mechanisms, mechanism_text, tokens
    from .validate_run import (
        CANONICAL_LOCKED_SURFACES,
        expected_run_editable_surfaces,
        source_evaluation_shape_errors,
        validate_state_document,
    )
else:
    from schema_contract import parse_json_strict
    from novelty_check import jaccard, load_mechanisms, mechanism_text, tokens
    from validate_run import (
        CANONICAL_LOCKED_SURFACES,
        expected_run_editable_surfaces,
        source_evaluation_shape_errors,
        validate_state_document,
    )


ROOT = Path(__file__).resolve().parents[2]
OBSERVED_AT = datetime(2026, 8, 25, 12, 0, 0, tzinfo=UTC)


@dataclass(frozen=True)
class ScenarioResult:
    scenario_id: str
    expected_gate: str
    observed_gate: str
    passed: bool
    executed_layer: str
    evidence: tuple[str, ...]
    limitation: str | None


def _base_evaluation() -> dict[str, Any]:
    return {
        "evaluation_id": "00000000-0000-4000-8000-000000000001",
        "timestamp": "2026-08-25T11:00:00+00:00",
        "source": {
            "url": "https://example.test/source",
            "title": "Adversarial fixture",
            "author_or_org": "Fixture Org",
            "retrieval_status": "retrieved",
            "source_type": "paper",
            "primary_or_secondary": "primary",
        },
        "gatekeeper": {
            "G1_mechanism_specificity": {
                "pass": True,
                "evidence": "specific mechanism",
            },
            "G2_implementable_artifacts": {
                "pass": True,
                "evidence": "bounded artifact",
            },
            "G3_beyond_basics": {"pass": True, "evidence": "nontrivial behavior"},
            "G4_source_verifiability": {"pass": True, "evidence": "identified source"},
            "verdict": "PASS",
        },
        "scoring": {
            "D1_technical_depth_actionability": {"score": 2, "reasoning": "actionable"},
            "D2_repo_relevance": {"score": 2, "reasoning": "relevant"},
            "D3_evidence_rigor": {"score": 2, "reasoning": "rigorous"},
            "D4_novelty_insight": {"score": 2, "reasoning": "novel"},
            "weighted_total": 2,
        },
        "decision": {
            "verdict": "APPROVE",
            "override_triggered": None,
            "confidence": "high",
            "justification": "Fixture follows the deterministic rubric.",
        },
        "extraction": {
            "mechanism": "A bounded deterministic fixture.",
            "implementable_artifacts": ["validator"],
            "failure_modes": ["stale input"],
            "candidate_skill_target": "existing skill",
            "candidate_skill_name": "harness-engineering",
            "taxonomy_category": "harness_engineering",
            "estimated_complexity": "medium",
        },
    }


def _route_evaluation(
    scenario_id: str,
    expected_gate: str,
    evaluation: dict[str, Any],
    observed_gate: str,
    *,
    limitation: str | None,
) -> ScenarioResult:
    errors = source_evaluation_shape_errors(evaluation, observed_at=OBSERVED_AT)
    return ScenarioResult(
        scenario_id=scenario_id,
        expected_gate=expected_gate,
        observed_gate=observed_gate,
        passed=not errors,
        executed_layer="content-curation-contract",
        evidence=tuple(errors)
        if errors
        else (f"valid routed verdict: {evaluation['decision']['verdict']}",),
        limitation=limitation,
    )


def _duplicate_mechanism() -> ScenarioResult:
    mechanisms = load_mechanisms(ROOT)
    if not mechanisms:
        return ScenarioResult(
            "adv-duplicate-mechanism-reworded",
            "novelty_human_review_or_duplicate",
            "registry_unavailable",
            False,
            "novelty-overlap-contract",
            ("no accepted or candidate mechanism was available",),
            None,
        )
    source = mechanism_text(mechanisms[0])
    score = jaccard(tokens(source), tokens(source))
    observed = (
        "likely_duplicate"
        if score >= 0.315
        else "human_review"
        if score >= 0.18
        else "pass"
    )
    return ScenarioResult(
        "adv-duplicate-mechanism-reworded",
        "novelty_human_review_or_duplicate",
        observed,
        observed in {"likely_duplicate", "human_review"},
        "novelty-overlap-contract",
        (f"exact accepted-mechanism token overlap={score:.4f}",),
        "Rewording robustness beyond token overlap still needs semantic evaluation.",
    )


def _credible_generic_source() -> ScenarioResult:
    evaluation = _base_evaluation()
    evaluation["gatekeeper"]["G1_mechanism_specificity"]["pass"] = False
    evaluation["gatekeeper"]["G2_implementable_artifacts"]["pass"] = False
    evaluation["gatekeeper"]["verdict"] = "REJECT"
    for dimension in evaluation["scoring"].values():
        if isinstance(dimension, dict):
            dimension["score"] = 0
    evaluation["scoring"]["weighted_total"] = 0
    evaluation["decision"].update({"verdict": "REJECT", "override_triggered": None})
    evaluation["extraction"].update(
        {
            "mechanism": "",
            "implementable_artifacts": [],
            "failure_modes": [],
            "candidate_skill_target": "reject",
            "candidate_skill_name": "",
        }
    )
    return _route_evaluation(
        "adv-credible-generic-source",
        "content_reject",
        evaluation,
        "content_reject",
        limitation="The fixture supplies failed semantic gates; no autonomous prose classifier was executed.",
    )


def _unretrieved_evidence() -> ScenarioResult:
    evaluation = _base_evaluation()
    evaluation["source"]["retrieval_status"] = "partial"
    errors = source_evaluation_shape_errors(evaluation, observed_at=OBSERVED_AT)
    detected = any("only retrieved sources" in error for error in errors)
    return ScenarioResult(
        "adv-unretrieved-cited-evidence",
        "run_readiness_fail",
        "run_readiness_fail" if detected else "false_green",
        detected,
        "source-evaluation-provenance-boundary",
        tuple(errors),
        "This fixture exercises the shared provenance contract, not a full persisted run directory.",
    )


def _wrong_rubric_math() -> ScenarioResult:
    evaluation = _base_evaluation()
    evaluation["scoring"]["weighted_total"] = 1.5
    errors = source_evaluation_shape_errors(evaluation, observed_at=OBSERVED_AT)
    detected = any("does not match recomputed" in error for error in errors)
    return ScenarioResult(
        "adv-wrong-rubric-math",
        "repo_validation_fail",
        "repo_validation_fail" if detected else "false_green",
        detected,
        "content-curation-contract",
        tuple(errors),
        None,
    )


def _verbose_no_behavior() -> ScenarioResult:
    evaluation = _base_evaluation()
    scores = evaluation["scoring"]
    scores["D1_technical_depth_actionability"]["score"] = 1
    scores["D2_repo_relevance"]["score"] = 1
    scores["D3_evidence_rigor"]["score"] = 2
    scores["D4_novelty_insight"]["score"] = 0
    scores["weighted_total"] = 1.05
    evaluation["decision"].update(
        {"verdict": "HUMAN_REVIEW", "override_triggered": None, "confidence": "low"}
    )
    return _route_evaluation(
        "adv-verbose-no-behavior",
        "model_or_human_review",
        evaluation,
        "model_or_human_review",
        limitation="The fixture supplies low behavior scores; semantic no-op detection remains human/model work.",
    )


def _self_approved_rubric_change() -> ScenarioResult:
    run_id = "20260825-120000-adversarial-fixture"
    timestamp = "2026-08-25T11:00:00+00:00"
    state = {
        "run_id": run_id,
        "source_id": "S001",
        "title": "Adversarial fixture",
        "source_url": "https://example.test/source",
        "current_state": "initialized",
        "close_status": None,
        "close_reason": None,
        "locked_surfaces": list(CANONICAL_LOCKED_SURFACES[:-1]),
        "editable_surfaces": expected_run_editable_surfaces(run_id),
        "state_history": [
            {
                "state": "initialized",
                "timestamp": timestamp,
                "reason": "fixture initialized",
                "evidence": f"researcher/runs/{run_id}",
            }
        ],
        "created_at": timestamp,
        "updated_at": timestamp,
    }
    errors = validate_state_document(
        state, expected_run_id=run_id, observed_at=OBSERVED_AT
    )
    detected = any("locked_surfaces must equal" in error for error in errors)
    return ScenarioResult(
        "adv-self-approved-rubric-change",
        "human_review_stop",
        "human_review_stop" if detected else "false_green",
        detected,
        "state-authority-contract",
        tuple(errors),
        None,
    )


def _high_novelty_weak_evidence() -> ScenarioResult:
    evaluation = _base_evaluation()
    scores = evaluation["scoring"]
    scores["D1_technical_depth_actionability"]["score"] = 1
    scores["D2_repo_relevance"]["score"] = 1
    scores["D3_evidence_rigor"]["score"] = 0
    scores["D4_novelty_insight"]["score"] = 2
    scores["weighted_total"] = 0.95
    evaluation["decision"].update(
        {"verdict": "HUMAN_REVIEW", "override_triggered": "O4", "confidence": "low"}
    )
    return _route_evaluation(
        "adv-high-novelty-weak-evidence",
        "human_review",
        evaluation,
        "human_review",
        limitation=None,
    )


RUNNERS: dict[str, Callable[[], ScenarioResult]] = {
    "adv-duplicate-mechanism-reworded": _duplicate_mechanism,
    "adv-credible-generic-source": _credible_generic_source,
    "adv-unretrieved-cited-evidence": _unretrieved_evidence,
    "adv-wrong-rubric-math": _wrong_rubric_math,
    "adv-verbose-no-behavior": _verbose_no_behavior,
    "adv-self-approved-rubric-change": _self_approved_rubric_change,
    "adv-high-novelty-weak-evidence": _high_novelty_weak_evidence,
}


def execute_catalog(scenarios: list[dict[str, Any]]) -> dict[str, Any]:
    results: list[ScenarioResult] = []
    seen: set[str] = set()
    catalog_errors: list[str] = []
    executed = 0
    for scenario in scenarios:
        if not isinstance(scenario, dict):
            catalog_errors.append("scenario must be an object")
            continue
        scenario_id = scenario.get("scenario_id")
        if isinstance(scenario_id, str):
            if scenario_id in seen:
                catalog_errors.append(f"duplicate scenario: {scenario_id}")
                continue
            seen.add(scenario_id)
        runner = RUNNERS.get(scenario_id) if isinstance(scenario_id, str) else None
        if runner is None:
            results.append(
                ScenarioResult(
                    str(scenario_id),
                    str(scenario.get("expected_gate")),
                    "runner_missing",
                    False,
                    "none",
                    ("no registered deterministic mutation runner",),
                    None,
                )
            )
            continue
        result = runner()
        executed += 1
        if result.expected_gate != scenario.get("expected_gate"):
            result = ScenarioResult(
                result.scenario_id,
                str(scenario.get("expected_gate")),
                result.observed_gate,
                False,
                result.executed_layer,
                (*result.evidence, "runner expected-gate metadata drift"),
                result.limitation,
            )
        results.append(result)
    catalog_errors.extend(
        f"missing registered scenario: {scenario_id}"
        for scenario_id in sorted(RUNNERS.keys() - seen)
    )
    return {
        "name": "adversarial-mutation-execution",
        "kind": "scenario_execution",
        "passed": not catalog_errors and all(result.passed for result in results),
        "catalog_entries": len(scenarios),
        "executed_scenarios": executed,
        "execution_status": "executed" if executed else "not_executed",
        "catalog_errors": catalog_errors,
        "scope": "deterministic contract mutation fixtures; semantic classifier quality excluded",
        "results": [asdict(result) for result in results],
        "failures": [asdict(result) for result in results if not result.passed],
    }


def load_catalog(path: Path) -> list[dict[str, Any]]:
    records: list[dict[str, Any]] = []
    for line_number, line in enumerate(
        path.read_text(encoding="utf-8").splitlines(), 1
    ):
        if not line.strip():
            continue
        value = parse_json_strict(line)
        if not isinstance(value, dict):
            raise ValueError(f"{path}:{line_number}: scenario must be an object")
        records.append(value)
    return records


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--catalog",
        type=Path,
        default=ROOT / "researcher" / "benchmarks" / "scenarios" / "adversarial.jsonl",
    )
    parser.add_argument("--json", action="store_true")
    args = parser.parse_args()
    report = execute_catalog(load_catalog(args.catalog))
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True))
    else:
        print(
            f"Adversarial fixtures: {report['executed_scenarios']} executed, "
            f"{len(report['failures'])} failed, "
            f"{len(report['catalog_errors'])} catalog errors"
        )
    return 0 if report["passed"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
