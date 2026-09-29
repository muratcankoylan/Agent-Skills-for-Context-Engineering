"""Adversarial accounting tests for router benchmark reporting."""

from __future__ import annotations

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory
from typing import Any

from researcher.scripts.render_router_report import (
    build_confusion,
    expected_shuffle_seed,
    load_summary_metadata,
    per_prompt_breakdown,
    render,
    load_run_records,
    stable_seed,
    summarize_per_model,
    validate_comparable_summaries,
    validate_comparable_record_sets,
    validate_records,
)


def record(
    status: str,
    *,
    model_id: str = "test-model",
    prompt_id: str = "p001",
    top1_correct: Any = None,
    top3_correct: Any = None,
    predicted_primary: str | None = None,
) -> dict[str, Any]:
    result: dict[str, Any] = {
        "model_id": model_id,
        "prompt_id": prompt_id,
        "rep": 0,
        "status": status,
    }
    if top1_correct is not None:
        result["top1_correct"] = top1_correct
    if top3_correct is not None:
        result["top3_correct"] = top3_correct
    if predicted_primary is not None:
        result["predicted_primary"] = predicted_primary
    return result


class RouterReportAccountingTests(unittest.TestCase):
    def test_cancelled_record_does_not_reduce_accuracy(self) -> None:
        records = [
            record(
                "finished",
                top1_correct=True,
                top3_correct=True,
                predicted_primary="expected-skill",
            ),
            record(
                "cancelled",
            ),
        ]

        summary = summarize_per_model(records)["test-model"]
        self.assertEqual(summary["total_records"], 2)
        self.assertEqual(summary["usable_records"], 1)
        self.assertEqual(summary["cancelled"], 1)
        self.assertEqual(summary["top1_accuracy"], 1.0)
        self.assertEqual(summary["top3_accuracy"], 1.0)
        self.assertEqual(summary["sdk_finished_rate"], 0.5)
        self.assertEqual(summary["usable_rate"], 0.5)

        prompts = {"p001": {"expected_primary_skill": "expected-skill"}}
        prompt_row = per_prompt_breakdown(records, prompts)[0]
        self.assertEqual(prompt_row["top1_rate"], 1.0)
        self.assertEqual(prompt_row["usable_rate"], 0.5)
        self.assertEqual(
            build_confusion(records, prompts),
            {"expected-skill": {"expected-skill": 1}},
        )

    def test_all_outcomes_are_accounted_without_entering_accuracy(self) -> None:
        records = [
            record("finished", top1_correct=False, top3_correct=True),
            record("format_failure"),
            record("error"),
            record("cancelled"),
            record("model_unavailable"),
            record("dry_run"),
            record("finished", top1_correct=True),
        ]

        stats = summarize_per_model(records)["test-model"]
        self.assertEqual(stats["total_records"], 7)
        self.assertEqual(stats["usable_records"], 1)
        self.assertEqual(stats["format_failures"], 1)
        self.assertEqual(stats["sdk_errors"], 1)
        self.assertEqual(stats["cancelled"], 1)
        self.assertEqual(stats["model_unavailable"], 1)
        self.assertEqual(stats["dry_runs"], 1)
        self.assertEqual(stats["invalid_finished_records"], 1)
        self.assertEqual(stats["sdk_finished_rate"], 0.4286)
        self.assertEqual(stats["usable_rate"], 0.1429)
        self.assertEqual(stats["top1_accuracy"], 0.0)
        self.assertEqual(stats["top3_accuracy"], 1.0)

    def test_finished_record_requires_actual_boolean_scores(self) -> None:
        records = [record("finished", top1_correct=1, top3_correct=True)]

        stats = summarize_per_model(records)["test-model"]
        self.assertEqual(stats["usable_records"], 0)
        self.assertEqual(stats["invalid_finished_records"], 1)
        self.assertIsNone(stats["top1_accuracy"])
        self.assertIsNone(stats["top3_accuracy"])

    def test_unknown_status_fails_closed(self) -> None:
        with self.assertRaisesRegex(ValueError, "unknown router result status 'timed_out'"):
            summarize_per_model([record("timed_out")])

    def test_bootstrap_seed_is_process_independent(self) -> None:
        self.assertEqual(stable_seed("test-model:top1"), 1973932665)
        self.assertEqual(stable_seed("test-model:top3"), 3196672486)

    def test_malformed_result_file_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "corrupt.json"
            path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid router result JSON"):
                load_run_records(Path(directory))

            path.write_text('{"status":"finished","status":"error"}\n', encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "duplicate JSON key 'status'"):
                load_run_records(Path(directory))

    def test_corrupt_or_mismatched_summary_fails_closed(self) -> None:
        with TemporaryDirectory() as directory:
            path = Path(directory) / "summary.json"
            path.write_text("{not-json}\n", encoding="utf-8")
            with self.assertRaisesRegex(ValueError, "invalid router summary JSON"):
                load_summary_metadata(path, "0123456789abcdef")
            path.write_text(
                '{"fixture_sha":"ffffffffffffffff","seed":1,"reps":1,"models":["m"]}\n',
                encoding="utf-8",
            )
            with self.assertRaisesRegex(ValueError, "fixture digest does not match"):
                load_summary_metadata(path, "0123456789abcdef")

    def test_result_identity_and_scores_are_recomputed_from_fixture(self) -> None:
        prompts = {"p001": {"expected_primary_skill": "expected-skill"}}
        summary = {
            "models": ["test-model"],
            "reps": 1,
            "seed": 1,
            "prompts": 1,
            "total_runs": 1,
        }
        valid = {
            "model_id": "test-model",
            "prompt_id": "p001",
            "rep": 0,
            "shuffle_seed": expected_shuffle_seed("p001", "test-model", 0, 1),
            "status": "finished",
            "predicted_primary": "expected-skill",
            "predicted_top3": ["expected-skill", "other-skill"],
            "top1_correct": True,
            "top3_correct": True,
        }
        validate_records([valid], prompts, summary)

        forged = {**valid, "top1_correct": False}
        with self.assertRaisesRegex(ValueError, "forged top1_correct"):
            validate_records([forged], prompts, summary)

        inconsistent = {**valid, "top3_correct": False}
        with self.assertRaisesRegex(ValueError, "forged top3_correct"):
            validate_records([inconsistent], prompts, summary)

        foreign = {**valid, "prompt_id": "foreign"}
        with self.assertRaisesRegex(ValueError, "foreign prompt_id"):
            validate_records([foreign], prompts, summary)

        with self.assertRaisesRegex(ValueError, "duplicate router result identity"):
            validate_records([valid, dict(valid)], prompts, summary)

    def test_partial_candidate_population_is_rejected(self) -> None:
        prompts = {
            "p001": {"expected_primary_skill": "expected-skill"},
            "p002": {"expected_primary_skill": "expected-skill"},
        }
        summary = {
            "models": ["test-model"],
            "reps": 1,
            "seed": 7,
            "prompts": 2,
            "total_runs": 2,
        }
        partial = [self._valid_result("p001", "test-model", 0, seed=7)]

        with self.assertRaisesRegex(ValueError, "complete expected plan"):
            validate_records(partial, prompts, summary)

    def test_matching_partial_candidate_and_baseline_are_rejected(self) -> None:
        prompts = {
            "p001": {"expected_primary_skill": "expected-skill"},
            "p002": {"expected_primary_skill": "expected-skill"},
        }
        summary = {
            "models": ["test-model"],
            "reps": 1,
            "seed": 11,
            "prompts": 2,
            "total_runs": 2,
        }
        candidate = [self._valid_result("p001", "test-model", 0, seed=11)]
        baseline = [dict(candidate[0])]

        validate_comparable_record_sets(candidate, baseline)
        for population in (candidate, baseline):
            with self.assertRaisesRegex(ValueError, "complete expected plan"):
                validate_records(population, prompts, summary)

    def test_summary_total_runs_must_match_expected_cardinality(self) -> None:
        prompts = {"p001": {"expected_primary_skill": "expected-skill"}}
        result = self._valid_result("p001", "test-model", 0, seed=1)
        summary = {
            "models": ["test-model"],
            "reps": 1,
            "seed": 1,
            "prompts": 1,
            "total_runs": 2,
        }

        with self.assertRaisesRegex(ValueError, "expected plan cardinality"):
            validate_records([result], prompts, summary)

    def test_complete_population_accepts_authentic_legacy_summary(self) -> None:
        prompts = {
            "p001": {"expected_primary_skill": "expected-skill"},
            "p002": {"expected_primary_skill": "expected-skill"},
        }
        legacy_summary = {
            "timestamp": "2026-05-15T00:00:00.000Z",
            "repo_sha": "0123456789abcdef",
            "fixture_sha": "0123456789abcdef",
            "seed": 23,
            "models": ["test-model"],
            "reps": 1,
            "prompts": 2,
            "summary": {
                "test-model": {
                    "total": 2,
                    "format_failure_rate": 0.0,
                    "top1_accuracy": 1.0,
                    "top3_accuracy": 1.0,
                },
                "promptCount": 2,
            },
        }
        records = [
            self._valid_result(prompt_id, "test-model", 0, seed=23)
            for prompt_id in prompts
        ]

        validate_records(records, prompts, legacy_summary)
        with self.assertRaisesRegex(ValueError, "complete expected plan"):
            validate_records(records[:1], prompts, legacy_summary)

    def test_full_cartesian_population_is_valid(self) -> None:
        prompts = {
            "p001": {"expected_primary_skill": "expected-skill"},
            "p002": {"expected_primary_skill": "expected-skill"},
        }
        models = ["model-a", "model-b"]
        reps = 2
        seed = 17
        summary = {
            "models": models,
            "reps": reps,
            "seed": seed,
            "prompts": len(prompts),
            "total_runs": len(prompts) * len(models) * reps,
        }
        records = [
            self._valid_result(prompt_id, model_id, rep, seed=seed)
            for prompt_id in prompts
            for model_id in models
            for rep in range(reps)
        ]

        validate_records(records, prompts, summary)

    @staticmethod
    def _valid_result(
        prompt_id: str,
        model_id: str,
        rep: int,
        *,
        seed: int,
    ) -> dict[str, Any]:
        return {
            "model_id": model_id,
            "prompt_id": prompt_id,
            "rep": rep,
            "shuffle_seed": expected_shuffle_seed(prompt_id, model_id, rep, seed),
            "status": "finished",
            "predicted_primary": "expected-skill",
            "predicted_top3": ["expected-skill"],
            "top1_correct": True,
            "top3_correct": True,
        }

    def test_delta_requires_matching_seed_reps_and_model_population(self) -> None:
        candidate = {"seed": 1, "reps": 3, "models": ["a", "b"]}
        validate_comparable_summaries(candidate, dict(candidate))
        for baseline, pattern in [
            ({**candidate, "seed": 2}, "baseline seed is not comparable"),
            ({**candidate, "reps": 2}, "baseline reps is not comparable"),
            ({**candidate, "models": ["a", "c"]}, "baseline models are not comparable"),
        ]:
            with self.subTest(baseline=baseline):
                with self.assertRaisesRegex(ValueError, pattern):
                    validate_comparable_summaries(candidate, baseline)

        candidate_records = [
            {
                "prompt_id": "p1",
                "model_id": "a",
                "rep": 0,
                "status": "finished",
                "top1_correct": True,
                "top3_correct": True,
            }
        ]
        validate_comparable_record_sets(candidate_records, [dict(candidate_records[0])])
        with self.assertRaisesRegex(ValueError, "record population is not comparable"):
            validate_comparable_record_sets(
                candidate_records,
                [{"prompt_id": "p2", "model_id": "a", "rep": 0}],
            )
        with self.assertRaisesRegex(ValueError, "usable population is not comparable"):
            validate_comparable_record_sets(
                candidate_records,
                [
                    {
                        "prompt_id": "p1",
                        "model_id": "a",
                        "rep": 0,
                        "status": "error",
                    }
                ],
            )

    def test_report_renders_model_with_no_usable_records(self) -> None:
        summary = summarize_per_model([record("error")])
        rendered = render(
            summary,
            {},
            per_prompt_breakdown([record("error")], {}),
            {
                "timestamp": "test",
                "models": ["test-model"],
                "total_runs": 1,
                "reps": 1,
            },
        )

        self.assertIn("| `test-model` | - | - | - | - | 0 / 1 |", rendered)
        self.assertNotIn("p001 |", rendered)


if __name__ == "__main__":
    unittest.main()
