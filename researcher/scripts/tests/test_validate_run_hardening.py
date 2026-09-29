"""Focused adversarial coverage for the run-validation trust boundary."""

from __future__ import annotations

import copy
import hashlib
import json
import os
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

from researcher.scripts.validate_run import (
    LEGACY_REFERENCE_RUN_ID,
    MAX_EVIDENCE_FILES,
    ROOT,
    RunValidator,
    source_evaluation_shape_errors,
    validate_state_document,
)


LOCKED_SURFACES = [
    "researcher/rubrics/content-curation.md",
    "researcher/rubrics/skill-change.md",
    "researcher/rubrics/harness-change.md",
    "researcher/mechanisms/registry.jsonl",
    ".claude-plugin/marketplace.json",
    ".plugin/plugin.json",
    "researcher/scripts/validate_repo.py",
]
TIMESTAMP = "2026-08-17T00:00:00+00:00"


class RunValidatorHardeningTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.counter = 0

    def tearDown(self) -> None:
        self.temp.cleanup()

    def make_run_dir(self) -> Path:
        self.counter += 1
        run_dir = self.root / "researcher" / "runs" / f"run-{self.counter}"
        for child in (
            run_dir / "sources" / "evaluations",
            run_dir / "sources" / "evidence" / "raw",
            run_dir / "proposals",
            run_dir / "reports",
        ):
            child.mkdir(parents=True, exist_ok=True)
        return run_dir

    @staticmethod
    def history(states: list[str], run_dir: Path) -> list[dict[str, str]]:
        entries = []
        for index, state in enumerate(states):
            root = run_dir.parents[2]
            evidence_paths = {
                "initialized": run_dir,
                "retrieved": run_dir / "sources" / "evidence" / "raw",
                "evaluated": run_dir / "sources" / "evaluations" / "source-evaluation.json",
                "proposed": run_dir / "proposals" / "skill-proposal.md",
                "novelty_checked": run_dir / "reports" / "novelty-result.json",
                "validated": run_dir / "reports" / "run-readiness.json",
                "pr_ready": run_dir / "reports" / "pr-readiness.md",
                "closed": run_dir / "reports" / "closure.json",
            }
            evidence = str(evidence_paths[state].relative_to(root))
            reason = f"entered {state}"
            if state == "closed":
                reason = "terminal decision"
            entries.append(
                {
                    "state": state,
                    "timestamp": f"2026-08-17T00:00:{index:02d}+00:00",
                    "reason": reason,
                    "evidence": evidence,
                }
            )
        return entries

    def state(
        self,
        run_dir: Path,
        states: list[str],
        *,
        close_status: str | None = None,
        manifest: list[dict[str, object]] | None = None,
    ) -> dict[str, object]:
        state: dict[str, object] = {
            "run_id": run_dir.name,
            "source_id": "S001",
            "title": "Exact source",
            "source_url": "https://example.test/source",
            "current_state": states[-1],
            "close_status": close_status,
            "close_reason": "terminal decision" if close_status else None,
            "locked_surfaces": LOCKED_SURFACES,
            "editable_surfaces": [
                f"researcher/runs/{run_dir.name}/sources/",
                f"researcher/runs/{run_dir.name}/proposals/",
                f"researcher/runs/{run_dir.name}/reports/",
                f"researcher/runs/{run_dir.name}/logs/",
            ],
            "state_history": self.history(states, run_dir),
            "created_at": TIMESTAMP,
            "updated_at": self.history(states, run_dir)[-1]["timestamp"],
        }
        if manifest is not None:
            state["retrieval_evidence"] = manifest
            retrieved = next(
                entry
                for entry in state["state_history"]  # type: ignore[union-attr]
                if entry["state"] == "retrieved"
            )
            retrieved["evidence"] = ", ".join(
                str(item["path"]) for item in manifest
            )
        return state

    @staticmethod
    def queue_record(**updates: object) -> dict[str, object]:
        record: dict[str, object] = {
            "id": "S001",
            "url": "https://example.test/source",
            "title": "Exact source",
            "author_or_org": "Exact Org",
            "source_type": "paper",
            "retrieval_status": "retrieved",
        }
        record.update(updates)
        return record

    @staticmethod
    def evaluation(**source_updates: object) -> dict[str, object]:
        source = {
            "url": "https://example.test/source",
            "title": "Exact source",
            "author_or_org": "Exact Org",
            "retrieval_status": "retrieved",
            "source_type": "paper",
            "primary_or_secondary": "primary",
        }
        source.update(source_updates)
        return {
            "evaluation_id": "00000000-0000-4000-8000-000000000001",
            "timestamp": TIMESTAMP,
            "source": source,
            "gatekeeper": {
                "G1_mechanism_specificity": {"pass": True, "evidence": "mechanism"},
                "G2_implementable_artifacts": {"pass": True, "evidence": "artifacts"},
                "G3_beyond_basics": {"pass": True, "evidence": "advanced"},
                "G4_source_verifiability": {"pass": True, "evidence": "verified"},
                "verdict": "PASS",
            },
            "scoring": {
                "D1_technical_depth_actionability": {"score": 2, "reasoning": "deep"},
                "D2_repo_relevance": {"score": 2, "reasoning": "relevant"},
                "D3_evidence_rigor": {"score": 2, "reasoning": "rigorous"},
                "D4_novelty_insight": {"score": 2, "reasoning": "novel"},
                "weighted_total": 2,
            },
            "decision": {
                "verdict": "APPROVE",
                "override_triggered": None,
                "confidence": "high",
                "justification": "The exact evidence supports the mechanism.",
            },
            "extraction": {
                "mechanism": "A concrete deterministic mechanism.",
                "implementable_artifacts": ["validator"],
                "failure_modes": ["stale input"],
                "candidate_skill_target": "existing skill",
                "candidate_skill_name": "harness-engineering",
                "taxonomy_category": "harness_engineering",
                "estimated_complexity": "medium",
            },
        }

    def write_json(self, path: Path, data: object) -> None:
        path.write_text(json.dumps(data) + "\n", encoding="utf-8")

    def add_evidence(self, run_dir: Path, payload: bytes = b"immutable evidence") -> list[dict[str, object]]:
        digest = hashlib.sha256(payload).hexdigest()
        path = run_dir / "sources" / "evidence" / "raw" / digest
        path.write_bytes(payload)
        path.chmod(0o400)
        relative = str(path.relative_to(self.root))
        manifest: list[dict[str, object]] = [
            {
                "path": relative,
                "sha256": f"sha256:{digest}",
                "size_bytes": len(payload),
            }
        ]
        self.write_json(
            run_dir / "sources" / "queue.jsonl",
            self.queue_record(
                raw_evidence=[relative],
                raw_evidence_sha256=[f"sha256:{digest}"],
                raw_evidence_size_bytes=[len(payload)],
            ),
        )
        return manifest

    def write_valid_proposal(self, run_dir: Path) -> None:
        fields = {
            "URL": "https://example.test/source",
            "Title": "Exact source",
            "Author or organization": "Exact Org",
            "Source type": "paper",
            "Retrieval status": "retrieved",
            "Evaluation file": str(
                (
                    run_dir
                    / "sources"
                    / "evaluations"
                    / "source-evaluation.json"
                ).relative_to(self.root)
            ),
            "Decision": "APPROVE",
            "Target path": "skills/harness-engineering/SKILL.md",
            "Activation scenario": "exact activation",
            "Verdict": "pass",
            "Max mechanism overlap": "0.0",
            "Top mechanism overlaps": "none",
            "Human-review rationale": "none",
            "Evidence limitations": "none beyond the recorded artifact",
            "Possible duplication": "none",
            "Required human review": "yes",
        }
        text = "# Skill Proposal: Exact source\n\n" + "\n".join(
            f"- {field}: {value}" for field, value in fields.items()
        )
        (run_dir / "proposals" / "skill-proposal.md").write_text(
            text + "\n", encoding="utf-8"
        )

    def make_accepted_run(self) -> tuple[Path, list[dict[str, object]]]:
        run_dir = self.make_run_dir()
        manifest = self.add_evidence(run_dir)
        states = [
            "initialized",
            "retrieved",
            "evaluated",
            "proposed",
            "novelty_checked",
            "validated",
            "pr_ready",
            "closed",
        ]
        state = self.state(run_dir, states, close_status="accepted", manifest=manifest)
        self.write_json(run_dir / "run-state.json", state)
        self.write_json(
            run_dir / "sources" / "evaluations" / "source-evaluation.json",
            self.evaluation(),
        )
        queue_path = run_dir / "sources" / "queue.jsonl"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue.update(
            {
                "evaluation_file": str(
                    (
                        run_dir
                        / "sources"
                        / "evaluations"
                        / "source-evaluation.json"
                    ).relative_to(self.root)
                ),
                "evaluation_decision": "APPROVE",
            }
        )
        self.write_json(queue_path, queue)
        self.write_valid_proposal(run_dir)
        self.write_json(
            run_dir / "reports" / "novelty-result.json",
            {
                "verdict": "pass",
                "threshold": 0.18,
                "max_score": 0.0,
                "max_mechanism_score": 0.0,
                "top_mechanism_overlaps": [],
                "max_corpus_score": 0.0,
                "top_overlaps": [],
            },
        )
        self.write_json(
            run_dir / "reports" / "run-readiness.json",
            {
                "ok": True,
                "run_dir": str(run_dir.relative_to(self.root)),
                "summary": {"errors": 0, "warnings": 0},
                "findings": [],
            },
        )
        (run_dir / "reports" / "pr-readiness.md").write_text(
            "# PR Readiness Notes\n\n"
            "## Summary\n\nReady.\n\n"
            "## Test Plan\n\nRun all gates.\n\n"
            "## Risks\n\nKnown risk recorded.\n\n"
            "Merge requires human approval.\n",
            encoding="utf-8",
        )
        closed_at = state["state_history"][-1]["timestamp"]  # type: ignore[index]
        self.write_json(
            run_dir / "reports" / "closure.json",
            {
                "status": "accepted",
                "reason": "terminal decision",
                "closed_at": closed_at,
                "reviewed_by": "reviewer",
            },
        )
        return run_dir, manifest

    def validator(self, run_dir: Path, *, integrity_only: bool = False) -> RunValidator:
        validator = RunValidator(run_dir, integrity_only=integrity_only)
        validator.root = self.root
        return validator

    def test_complete_state_document_contract_and_expected_run_id(self) -> None:
        run_dir = self.make_run_dir()
        data = self.state(run_dir, ["initialized"])
        self.assertEqual(
            validate_state_document(data, expected_run_id=run_dir.name),
            [],
        )
        data["run_id"] = "alias"
        data["source_url"] = None
        data["editable_surfaces"] = ["same", "same"]
        errors = validate_state_document(data, expected_run_id=run_dir.name)
        self.assertIn(
            f"run_id must equal managed directory name ({run_dir.name})", errors
        )
        self.assertIn("source_url must be a string", errors)
        self.assertIn("editable_surfaces must not contain duplicates", errors)

    def test_duplicate_keys_fail_closed_in_state_and_source_queue(self) -> None:
        run_dir = self.make_run_dir()
        state = self.state(run_dir, ["initialized"])
        payload = json.dumps(state).rstrip("}") + ',"current_state":"closed"}\n'
        (run_dir / "run-state.json").write_text(payload, encoding="utf-8")
        (run_dir / "sources" / "queue.jsonl").write_text(
            '{"id":"S001","id":"S002","title":"Exact source",'
            '"url":"https://example.test/source"}\n',
            encoding="utf-8",
        )
        result = self.validator(run_dir, integrity_only=True).run()
        self.assertFalse(result["ok"])
        messages = [item["message"] for item in result["findings"]]
        self.assertTrue(
            any("duplicate JSON key: current_state" in message for message in messages)
        )
        self.assertTrue(any("duplicate JSON key: id" in message for message in messages))

    def test_integrity_only_accepts_initialized_run_without_future_artifacts(self) -> None:
        run_dir = self.make_run_dir()
        self.write_json(run_dir / "run-state.json", self.state(run_dir, ["initialized"]))
        self.write_json(run_dir / "sources" / "queue.jsonl", self.queue_record())
        self.assertTrue(self.validator(run_dir, integrity_only=True).run()["ok"])
        full = self.validator(run_dir).run()
        self.assertFalse(full["ok"])
        self.assertTrue(
            any("completed source evaluation missing" in item["message"] for item in full["findings"])
        )

    def test_accepted_closure_is_rejected_even_with_full_artifacts(self) -> None:
        run_dir, _ = self.make_accepted_run()
        result = self.validator(run_dir).run()
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(
                "accepted closure is unsupported" in item["message"]
                for item in result["findings"]
            )
        )

    def test_accepted_artifact_validation_still_checks_full_readiness_and_evidence(self) -> None:
        run_dir = self.make_run_dir()
        states = [
            "initialized",
            "retrieved",
            "evaluated",
            "proposed",
            "novelty_checked",
            "validated",
            "pr_ready",
            "closed",
        ]
        state = self.state(run_dir, states, close_status="accepted")
        self.write_json(run_dir / "run-state.json", state)
        self.write_json(run_dir / "sources" / "queue.jsonl", self.queue_record())
        self.write_json(
            run_dir / "reports" / "closure.json",
            {
                "status": "accepted",
                "reason": "terminal decision",
                "closed_at": state["state_history"][-1]["timestamp"],  # type: ignore[index]
                "reviewed_by": "reviewer",
            },
        )
        result = self.validator(run_dir).run()
        messages = [item["message"] for item in result["findings"]]
        self.assertIn("retrieved lifecycle requires a retrieval_evidence manifest", messages)
        self.assertTrue(any("completed source evaluation" in message for message in messages))
        self.assertTrue(
            any(
                item["path"].endswith("proposals/skill-proposal.md")
                for item in result["findings"]
            )
        )
        self.assertTrue(
            any(
                item["path"].endswith("reports/pr-readiness.md")
                for item in result["findings"]
            )
        )

    def test_integrity_only_requires_artifacts_already_claimed_by_active_state(self) -> None:
        run_dir = self.make_run_dir()
        manifest = self.add_evidence(run_dir)
        self.write_json(
            run_dir / "run-state.json",
            self.state(
                run_dir,
                ["initialized", "retrieved", "evaluated"],
                manifest=manifest,
            ),
        )
        evaluation_path = run_dir / "sources" / "evaluations" / "source-evaluation.json"
        self.write_json(evaluation_path, self.evaluation())
        queue_path = run_dir / "sources" / "queue.jsonl"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue.update(
            {
                "evaluation_file": str(evaluation_path.relative_to(self.root)),
                "evaluation_decision": "APPROVE",
            }
        )
        self.write_json(queue_path, queue)
        self.assertTrue(self.validator(run_dir, integrity_only=True).run()["ok"])
        evaluation_path.unlink()
        result = self.validator(run_dir, integrity_only=True).run()
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(
                "completed source evaluation missing" in item["message"]
                for item in result["findings"]
            )
        )

    def test_accepted_legacy_artifacts_remain_unsupported_in_both_modes(self) -> None:
        run_dir, _ = self.make_accepted_run()
        for integrity_only in (False, True):
            result = self.validator(run_dir, integrity_only=integrity_only).run()
            self.assertFalse(result["ok"])
            self.assertTrue(
                any(
                    "accepted closure is unsupported" in item["message"]
                    for item in result["findings"]
                )
            )

    def test_reduced_terminal_corruption_is_nonblocking_only_when_recorded(self) -> None:
        for records_failure in (False, True):
            with self.subTest(records_failure=records_failure):
                run_dir = self.make_run_dir()
                manifest = self.add_evidence(run_dir)
                evidence_path = self.root / str(manifest[0]["path"])
                evidence_path.chmod(0o400)
                evidence_path.unlink()
                state = self.state(
                    run_dir,
                    ["initialized", "retrieved", "closed"],
                    close_status="abandoned",
                    manifest=manifest,
                )
                self.write_json(run_dir / "run-state.json", state)
                self.write_json(
                    run_dir / "reports" / "closure.json",
                    {
                        "status": "abandoned",
                        "reason": "terminal decision",
                        "closed_at": state["state_history"][-1]["timestamp"],  # type: ignore[index]
                        "reviewed_by": "",
                        "integrity_errors": [],
                    },
                )
                if records_failure:
                    probe = self.validator(run_dir, integrity_only=True)
                    state_data = probe.validate_state()
                    queue_record = probe.validate_queue()
                    probe.validate_source_identity(state_data, queue_record)
                    claimed = probe.validate_claimed_integrity(
                        state_data,
                        queue_record,
                    )
                    exact_errors = [
                        f"{item.path}: {item.message}"
                        for item in claimed
                        if item.severity == "error"
                    ]
                    closure_path = run_dir / "reports" / "closure.json"
                    closure = json.loads(closure_path.read_text(encoding="utf-8"))
                    closure["integrity_errors"] = exact_errors
                    self.write_json(closure_path, closure)
                result = self.validator(run_dir).run()
                self.assertEqual(result["ok"], records_failure)
                if records_failure:
                    self.assertGreater(result["summary"]["warnings"], 0)
                    self.assertEqual(result["summary"]["errors"], 0)
                else:
                    self.assertTrue(
                        any(
                            "integrity_errors differ from observed" in item["message"]
                            for item in result["findings"]
                        )
                    )

    def test_clean_reduced_terminal_accepts_empty_integrity_error_list(self) -> None:
        run_dir = self.make_run_dir()
        state = self.state(
            run_dir,
            ["initialized", "closed"],
            close_status="rejected",
        )
        self.write_json(run_dir / "run-state.json", state)
        self.write_json(run_dir / "sources" / "queue.jsonl", self.queue_record())
        self.write_json(
            run_dir / "reports" / "closure.json",
            {
                "status": "rejected",
                "reason": "terminal decision",
                "closed_at": state["state_history"][-1]["timestamp"],  # type: ignore[index]
                "reviewed_by": "",
                "integrity_errors": [],
            },
        )
        self.assertTrue(self.validator(run_dir).run()["ok"])

    def test_evidence_size_mode_and_file_count_are_fail_closed(self) -> None:
        run_dir = self.make_run_dir()
        empty_digest = hashlib.sha256(b"").hexdigest()
        empty_path = run_dir / "sources" / "evidence" / "raw" / empty_digest
        empty_path.write_bytes(b"")
        empty_path.chmod(0o400)
        relative = str(empty_path.relative_to(self.root))
        zero_manifest = [
            {
                "path": relative,
                "sha256": f"sha256:{empty_digest}",
                "size_bytes": 0,
            }
        ]
        validator = self.validator(run_dir)
        validator.validate_evidence(
            {"retrieval_evidence": zero_manifest},
            self.queue_record(
                raw_evidence=[relative],
                raw_evidence_sha256=[f"sha256:{empty_digest}"],
                raw_evidence_size_bytes=[0],
            ),
        )
        self.assertTrue(any("size_bytes[0] is invalid" in item.message for item in validator.findings))

        run_dir = self.make_run_dir()
        manifest = self.add_evidence(run_dir)
        evidence_path = self.root / str(manifest[0]["path"])
        evidence_path.chmod(0o600)
        queue = json.loads((run_dir / "sources" / "queue.jsonl").read_text(encoding="utf-8"))
        validator = self.validator(run_dir)
        validator.validate_evidence({"retrieval_evidence": manifest}, queue)
        self.assertTrue(
            any("no write permission bits" in item.message for item in validator.findings)
        )

        validator = self.validator(run_dir)
        validator.validate_evidence(
            {"retrieval_evidence": []},
            self.queue_record(
                raw_evidence=["unused"] * (MAX_EVIDENCE_FILES + 1),
                raw_evidence_sha256=["sha256:" + "0" * 64]
                * (MAX_EVIDENCE_FILES + 1),
                raw_evidence_size_bytes=[1] * (MAX_EVIDENCE_FILES + 1),
            ),
        )
        messages = [
            item.message
            for item in validator.findings
            if "file-count limit" in item.message
        ]
        self.assertEqual(messages, ["retrieval evidence file-count limit exceeded"])

    def test_exact_source_identity_is_required_across_all_surfaces(self) -> None:
        run_dir, _ = self.make_accepted_run()
        queue_path = run_dir / "sources" / "queue.jsonl"
        queue = json.loads(queue_path.read_text(encoding="utf-8"))
        queue["url"] = "https://example.test/different"
        self.write_json(queue_path, queue)
        evaluation_path = run_dir / "sources" / "evaluations" / "source-evaluation.json"
        evaluation = json.loads(evaluation_path.read_text(encoding="utf-8"))
        evaluation["source"]["title"] = "Different title"
        self.write_json(evaluation_path, evaluation)
        messages = [item["message"] for item in self.validator(run_dir).run()["findings"]]
        self.assertIn("queue url differs from state source_url", messages)
        self.assertIn("evaluation source title differs from queue title", messages)

    def test_pr_readiness_sections_require_nonempty_bodies(self) -> None:
        run_dir = self.make_run_dir()
        path = run_dir / "reports" / "pr-readiness.md"
        path.write_text(
            "## Summary\n\n## Test Plan\n\nreal tests\n\n## Risks\n\nrisks\n\n"
            "human approval required\n",
            encoding="utf-8",
        )
        validator = self.validator(run_dir)
        validator.validate_pr_readiness()
        self.assertTrue(
            any("section is blank: ## Summary" in item.message for item in validator.findings)
        )

    def test_source_evaluation_shape_uses_content_curation_contract(self) -> None:
        evaluation = self.evaluation()
        evaluation["scoring"]["weighted_total"] = 0  # type: ignore[index]
        errors = source_evaluation_shape_errors(evaluation)
        self.assertTrue(any("does not match recomputed" in message for message in errors))

    def test_future_state_and_evaluation_timestamps_fail_closed(self) -> None:
        run_dir = self.make_run_dir()
        state = self.state(run_dir, ["initialized"])
        state["created_at"] = "2099-01-01T00:00:00+00:00"
        state["updated_at"] = "2099-01-01T00:00:00+00:00"
        state["state_history"][0]["timestamp"] = "2099-01-01T00:00:00+00:00"  # type: ignore[index]
        state_errors = validate_state_document(state, expected_run_id=run_dir.name)
        self.assertIn("state_history[0].timestamp is future-dated", state_errors)
        self.assertIn("created_at is future-dated", state_errors)
        self.assertIn("updated_at is future-dated", state_errors)

        evaluation = self.evaluation()
        evaluation["timestamp"] = "2099-01-01T00:00:00+00:00"
        self.assertIn(
            "timestamp must not postdate evaluation validation",
            source_evaluation_shape_errors(evaluation),
        )

    def test_state_authority_surfaces_are_exact_and_run_local(self) -> None:
        run_dir = self.make_run_dir()
        baseline = self.state(run_dir, ["initialized"])
        cases = {
            "missing lock": {
                "locked_surfaces": LOCKED_SURFACES[:-1],
            },
            "extra lock": {
                "locked_surfaces": [*LOCKED_SURFACES, "governance/"],
            },
            "reordered locks": {
                "locked_surfaces": list(reversed(LOCKED_SURFACES)),
            },
            "escaped edit surface": {
                "editable_surfaces": [
                    f"researcher/runs/{run_dir.name}/sources/",
                    "researcher/scripts/",
                    "governance/",
                    f"researcher/runs/{run_dir.name}/logs/",
                ],
            },
        }
        for label, updates in cases.items():
            with self.subTest(label=label):
                state = copy.deepcopy(baseline)
                state.update(updates)
                errors = validate_state_document(
                    state,
                    expected_run_id=run_dir.name,
                )
                self.assertTrue(
                    any(
                        "canonical" in error
                        for error in errors
                    ),
                    errors,
                )

    def test_source_evaluation_rejects_nonfinite_dimension_scores(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                evaluation = copy.deepcopy(self.evaluation())
                evaluation["scoring"]["D1_technical_depth_actionability"][  # type: ignore[index]
                    "score"
                ] = value
                errors = source_evaluation_shape_errors(evaluation)
                self.assertIn(
                    "D1_technical_depth_actionability.score must be one of 0, 1, or 2",
                    errors,
                )

    def test_source_evaluation_rejects_fractional_dimension_scores(self) -> None:
        evaluation = self.evaluation()
        for dimension in (
            "D1_technical_depth_actionability",
            "D2_repo_relevance",
            "D3_evidence_rigor",
            "D4_novelty_insight",
        ):
            evaluation["scoring"][dimension]["score"] = 1.5  # type: ignore[index]
        evaluation["scoring"]["weighted_total"] = 1.5  # type: ignore[index]
        errors = source_evaluation_shape_errors(evaluation)
        self.assertEqual(
            sum("score must be one of 0, 1, or 2" in error for error in errors),
            4,
        )

    def test_source_evaluation_rejects_nonfinite_weighted_totals(self) -> None:
        for value in (float("nan"), float("inf"), float("-inf")):
            with self.subTest(value=value):
                evaluation = copy.deepcopy(self.evaluation())
                evaluation["scoring"]["weighted_total"] = value  # type: ignore[index]
                errors = source_evaluation_shape_errors(evaluation)
                self.assertIn("scoring.weighted_total must be numeric", errors)

    def test_durable_evaluation_rejects_nonfinite_json_constants(self) -> None:
        for constant in ("NaN", "Infinity", "-Infinity"):
            run_dir = self.make_run_dir()
            path = run_dir / "sources" / "evaluations" / "source-evaluation.json"
            payload = json.dumps(self.evaluation()).replace(
                '"weighted_total": 2', f'"weighted_total": {constant}'
            )
            path.write_text(payload, encoding="utf-8")
            validator = self.validator(run_dir)
            with self.subTest(constant=constant):
                self.assertIsNone(validator.load_json(path))
                self.assertIn(
                    f"invalid JSON: non-finite JSON number is not permitted: {constant}",
                    [item.message for item in validator.findings],
                )

    def test_proposal_requires_exactly_one_human_review_rationale(self) -> None:
        cases = {
            "missing": (
                "- Human-review rationale: none\n",
                "",
                "proposal field is missing: - Human-review rationale:",
            ),
            "duplicate": (
                "- Human-review rationale: none\n",
                "- Human-review rationale: none\n- Human-review rationale: none\n",
                "proposal field is duplicated: Human-review rationale",
            ),
            "contradictory": (
                "- Human-review rationale: none\n",
                "- Human-review rationale: manual review is needed\n",
                "proposal Human-review rationale differs from novelty result",
            ),
        }
        novelty = {
            "verdict": "pass",
            "max_mechanism_score": 0.0,
            "top_mechanism_overlaps": [],
        }
        for name, (old, new, expected) in cases.items():
            with self.subTest(case=name):
                run_dir = self.make_run_dir()
                self.write_valid_proposal(run_dir)
                proposal = run_dir / "proposals" / "skill-proposal.md"
                proposal.write_text(
                    proposal.read_text(encoding="utf-8").replace(old, new),
                    encoding="utf-8",
                )
                validator = self.validator(run_dir)
                validator.validate_proposal("retrieved", novelty_data=novelty)
                self.assertIn(expected, [item.message for item in validator.findings])

    def test_proposal_rationale_exactly_matches_nonpass_novelty_result(self) -> None:
        run_dir = self.make_run_dir()
        self.write_valid_proposal(run_dir)
        proposal = run_dir / "proposals" / "skill-proposal.md"
        text = proposal.read_text(encoding="utf-8")
        text = text.replace("- Verdict: pass", "- Verdict: human_review")
        text = text.replace(
            "- Human-review rationale: none",
            "- Human-review rationale: visible overlap requires review",
        )
        proposal.write_text(text, encoding="utf-8")
        novelty = {
            "verdict": "human_review",
            "max_mechanism_score": 0.0,
            "top_mechanism_overlaps": [],
            "human_review_rationale": "different rationale",
        }
        validator = self.validator(run_dir)
        validator.validate_proposal("retrieved", novelty_data=novelty)
        self.assertIn(
            "proposal Human-review rationale differs from novelty result",
            [item.message for item in validator.findings],
        )

    def test_pass_novelty_result_rejects_a_review_rationale(self) -> None:
        run_dir, _ = self.make_accepted_run()
        path = run_dir / "reports" / "novelty-result.json"
        novelty = json.loads(path.read_text(encoding="utf-8"))
        novelty["human_review_rationale"] = "contradicts a passing verdict"
        self.write_json(path, novelty)
        result = self.validator(run_dir).run()
        self.assertIn(
            "pass novelty verdict must not carry human_review_rationale",
            [item["message"] for item in result["findings"]],
        )

    def test_every_consumed_artifact_rejects_symlinks(self) -> None:
        relative_paths = (
            "run-state.json",
            "sources/queue.jsonl",
            "sources/evidence/raw/{digest}",
            "sources/evaluations/source-evaluation.json",
            "proposals/skill-proposal.md",
            "reports/novelty-result.json",
            "reports/run-readiness.json",
            "reports/pr-readiness.md",
            "reports/closure.json",
        )
        for relative_template in relative_paths:
            with self.subTest(relative_template=relative_template):
                run_dir, manifest = self.make_accepted_run()
                digest = str(manifest[0]["sha256"]).removeprefix("sha256:")
                target = run_dir / relative_template.format(digest=digest)
                outside = self.root / f"outside-{self.counter}"
                outside.write_bytes(target.read_bytes())
                mode = target.stat().st_mode & 0o777
                target.unlink()
                target.symlink_to(outside)
                outside.chmod(mode)
                result = self.validator(run_dir).run()
                self.assertFalse(result["ok"])
                self.assertTrue(
                    any(
                        "must not be a symlink" in item["message"]
                        for item in result["findings"]
                    )
                )

    def test_every_consumed_file_rejects_hardlink_aliases(self) -> None:
        relative_paths = (
            "run-state.json",
            "sources/queue.jsonl",
            "sources/evaluations/source-evaluation.json",
            "proposals/skill-proposal.md",
            "reports/novelty-result.json",
            "reports/run-readiness.json",
            "reports/pr-readiness.md",
            "reports/closure.json",
        )
        for relative in relative_paths:
            with self.subTest(relative=relative):
                run_dir, _ = self.make_accepted_run()
                target = run_dir / relative
                outside = self.root / f"hardlink-{self.counter}-{target.name}"
                os.link(target, outside)
                result = self.validator(run_dir).run()
                self.assertFalse(result["ok"])
                self.assertTrue(
                    any(
                        "exactly one hard link" in item["message"]
                        for item in result["findings"]
                    )
                )

    def test_run_directory_alias_is_rejected_without_resolution(self) -> None:
        run_dir = self.make_run_dir()
        alias = self.root / "alias-run"
        alias.symlink_to(run_dir, target_is_directory=True)
        result = self.validator(alias, integrity_only=True).run()
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("must not be a symlink" in item["message"] for item in result["findings"])
        )

        parent_alias = self.root / "alias-parent"
        parent_alias.symlink_to(run_dir.parent, target_is_directory=True)
        result = self.validator(
            parent_alias / run_dir.name,
            integrity_only=True,
        ).run()
        self.assertFalse(result["ok"])
        self.assertTrue(
            any("must not be a symlink" in item["message"] for item in result["findings"])
        )

    def test_integrity_only_cli_path_executes(self) -> None:
        run_dir = self.make_run_dir()
        self.write_json(run_dir / "run-state.json", self.state(run_dir, ["initialized"]))
        self.write_json(run_dir / "sources" / "queue.jsonl", self.queue_record())
        completed = subprocess.run(
            [
                sys.executable,
                str(ROOT / "researcher" / "scripts" / "validate_run.py"),
                "--run-dir",
                str(run_dir),
                "--integrity-only",
                "--json",
            ],
            cwd=ROOT,
            check=False,
            capture_output=True,
            text=True,
        )
        self.assertEqual(completed.returncode, 0, completed.stdout + completed.stderr)
        self.assertTrue(json.loads(completed.stdout)["ok"])

    def test_committed_legacy_reference_run_remains_compatible(self) -> None:
        run_dir = ROOT / "researcher" / "runs" / LEGACY_REFERENCE_RUN_ID
        result = RunValidator(run_dir).run()
        self.assertTrue(result["ok"], result["findings"])


if __name__ == "__main__":
    unittest.main()
