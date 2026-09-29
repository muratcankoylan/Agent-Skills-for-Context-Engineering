"""Adversarial tests for the legacy research-run state machine."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from argparse import Namespace
from datetime import datetime, timezone
from pathlib import Path
from unittest import mock

from researcher.scripts import loop_common, research_loop
from researcher.scripts.validate_repo import Validator
from researcher.scripts.validate_run import RunValidator, validate_state_history


def write_stub_source_evaluation(run_dir: Path, *_args: object) -> None:
    (run_dir / "sources" / "evaluations" / "source-evaluation-draft.json").write_text(
        "{}\n",
        encoding="utf-8",
    )


def write_stub_skill_proposal(run_dir: Path, *_args: object) -> None:
    (run_dir / "proposals" / "skill-proposal.md").write_text(
        "# staged proposal\n",
        encoding="utf-8",
    )
    (run_dir / "proposals" / "mechanism-proposal.jsonl").write_text(
        "{}\n",
        encoding="utf-8",
    )


def run_state(states: list[str]) -> dict[str, object]:
    return {
        "current_state": states[-1],
        "state_history": [
            {
                "state": state,
                "timestamp": f"2026-08-17T00:00:{index:02d}+00:00",
                "reason": f"entered {state}",
                "evidence": "",
            }
            for index, state in enumerate(states)
        ],
        "locked_surfaces": research_loop.LOCKED_SURFACES,
    }


def attempt_close_transition(
    run_dir: str,
    root: str,
    researcher: str,
    lock_dir: str,
    ready: object,
    results: object,
) -> None:
    research_loop.ROOT = Path(root)
    research_loop.RESEARCHER = Path(researcher)
    loop_common.LOCK_DIR = Path(lock_dir)
    ready.set()  # type: ignore[attr-defined]
    try:
        research_loop.close_run(
            Namespace(
                run_dir=Path(run_dir),
                status="abandoned",
                reason="concurrent close",
                reviewed_by="",
            )
        )
    except Exception as exc:  # The losing transition must report the exact denial.
        results.put(("error", str(exc)))  # type: ignore[attr-defined]
    else:
        results.put(("success", ""))  # type: ignore[attr-defined]


class StateHistoryContractTests(unittest.TestCase):
    def test_repo_validator_rejects_symlinked_run_entries_without_traversal(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            runs = root / "researcher" / "runs"
            runs.mkdir(parents=True)
            outside = root / "outside"
            outside.mkdir()
            (outside / "run-state.json").write_text("{}\n", encoding="utf-8")
            (runs / "linked-run").symlink_to(outside, target_is_directory=True)
            validator = Validator(root)
            validator.validate_runs()
            self.assertTrue(
                any(
                    finding.message == "run entry must be a real directory"
                    for finding in validator.findings
                )
            )

    def test_skipped_transition_and_current_state_mismatch_fail(self) -> None:
        skipped = run_state(["initialized", "pr_ready"])
        self.assertIn(
            "state_history[1] has illegal transition initialized -> pr_ready",
            validate_state_history(skipped),
        )

        mismatched = run_state(["initialized", "retrieved"])
        mismatched["current_state"] = "evaluated"
        self.assertTrue(
            any(
                message.startswith("current_state must equal the final")
                for message in validate_state_history(mismatched)
            )
        )

    def test_history_entries_are_structural_and_begin_initialized(self) -> None:
        malformed = run_state(["initialized", "retrieved"])
        malformed["state_history"][0] = {  # type: ignore[index]
            "state": "retrieved",
            "timestamp": "",
            "reason": 4,
            "evidence": None,
        }
        errors = validate_state_history(malformed)
        self.assertIn("state_history[0].state must be initialized", errors)
        self.assertIn("state_history[0].timestamp must be a non-empty string", errors)
        self.assertIn("state_history[0].reason must be a non-empty string", errors)
        self.assertIn("state_history[0].evidence must be a string", errors)

    def test_legacy_terminal_close_edges_are_explicit_but_closed_is_terminal(self) -> None:
        self.assertEqual(validate_state_history(run_state(["initialized", "closed"])), [])
        self.assertEqual(
            validate_state_history(run_state(["initialized", "retrieved", "closed"])),
            [],
        )

    def test_accepted_closure_history_must_immediately_follow_pr_ready(self) -> None:
        forged = run_state(["initialized", "closed"])
        forged["close_status"] = "accepted"
        forged["close_reason"] = "forged"
        self.assertIn(
            "accepted closure must immediately follow pr_ready",
            validate_state_history(forged),
        )
        self.assertTrue(
            any(
                "illegal transition closed -> retrieved" in message
                for message in validate_state_history(
                    run_state(["initialized", "closed", "retrieved"])
                )
            )
        )

    def test_both_run_and_repo_validators_reject_skipped_history(self) -> None:
        with tempfile.TemporaryDirectory() as temp_dir:
            root = Path(temp_dir)
            run_dir = root / "researcher" / "runs" / "bad-run"
            (run_dir / "sources" / "evaluations").mkdir(parents=True)
            (run_dir / "sources" / "evidence" / "raw").mkdir(parents=True)
            (run_dir / "proposals").mkdir()
            (run_dir / "reports").mkdir()
            (run_dir / "THREAD.md").write_text("# thread\n", encoding="utf-8")
            (run_dir / "sources" / "queue.jsonl").write_text("{}\n", encoding="utf-8")
            (run_dir / "proposals" / "mechanism-proposal.jsonl").write_text(
                "", encoding="utf-8"
            )
            (run_dir / "run-state.json").write_text(
                json.dumps(run_state(["initialized", "pr_ready"])), encoding="utf-8"
            )

            run_validator = RunValidator(run_dir)
            run_validator.validate_state()
            self.assertTrue(
                any("illegal transition" in finding.message for finding in run_validator.findings)
            )

            repo_validator = Validator(root)
            repo_validator.validate_runs()
            self.assertTrue(
                any("illegal transition" in finding.message for finding in repo_validator.findings)
            )

    def test_pr_readiness_artifact_is_required_only_after_validated_state(self) -> None:
        ordered_states = [
            "initialized",
            "retrieved",
            "evaluated",
            "proposed",
            "novelty_checked",
            "validated",
            "pr_ready",
        ]
        for current_state, should_check_report, should_check_notes in [
            ("novelty_checked", False, False),
            ("validated", True, False),
            ("pr_ready", True, True),
        ]:
            with self.subTest(current_state=current_state), tempfile.TemporaryDirectory() as temp_dir:
                validator = RunValidator(Path(temp_dir))
                history = ordered_states[: ordered_states.index(current_state) + 1]
                state = {
                    "current_state": current_state,
                    "close_status": None,
                    "retrieval_evidence": [],
                    "state_history": [
                        {"state": state_name, "evidence": "fixture"}
                        for state_name in history
                    ],
                }
                with mock.patch.object(validator, "validate_evidence"), mock.patch.object(
                    validator,
                    "validate_source_evaluation",
                    return_value="retrieved",
                ), mock.patch.object(validator, "validate_proposal"), mock.patch.object(
                    validator, "validate_novelty"
                ), mock.patch.object(
                    validator, "validate_pr_readiness"
                ) as validate_pr_readiness, mock.patch.object(
                    validator, "validate_readiness_report"
                ) as validate_readiness_report, mock.patch.object(
                    validator, "validate_closure"
                ):
                    validator.validate_claimed_integrity(state, {})
                self.assertEqual(
                    validate_readiness_report.called,
                    should_check_report,
                )
                self.assertEqual(validate_pr_readiness.called, should_check_notes)


class ResearchLoopMutationTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name).resolve()
        self.researcher = self.root / "researcher"
        self.run_dir = self.researcher / "runs" / "test-run"
        for child in (
            self.run_dir / "sources" / "evaluations",
            self.run_dir / "sources" / "evidence" / "raw",
            self.run_dir / "proposals",
            self.run_dir / "reports",
        ):
            child.mkdir(parents=True, exist_ok=True)
        (self.run_dir / "THREAD.md").write_text("# test thread\n", encoding="utf-8")
        (self.run_dir / "sources" / "queue.jsonl").write_text(
            json.dumps(
                {
                    "id": "S001",
                    "title": "Test",
                    "url": "https://example.test/",
                    "author_or_org": "Example Org",
                    "source_type": "paper",
                    "retrieval_status": "partial",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        self.patches = [
            mock.patch.object(research_loop, "ROOT", self.root),
            mock.patch.object(research_loop, "RESEARCHER", self.researcher),
            mock.patch.object(loop_common, "LOCK_DIR", self.root / "locks"),
        ]
        for patcher in self.patches:
            patcher.start()
            self.addCleanup(patcher.stop)
        research_loop.write_state(
            self.run_dir,
            research_loop.initial_state(self.run_dir, "Test", "https://example.test/"),
        )

    def write_state_with_evidence(self, states: list[str]) -> dict[str, object]:
        payload = b"stable test evidence"
        digest = hashlib.sha256(payload).hexdigest()
        raw_path = self.run_dir / "sources" / "evidence" / "raw" / digest
        raw_path.write_bytes(payload)
        raw_path.chmod(0o400)
        relative = str(raw_path.relative_to(self.root))
        manifest = [
            {
                "path": relative,
                "sha256": f"sha256:{digest}",
                "size_bytes": len(payload),
            }
        ]
        queue = {
            "id": "S001",
            "title": "Test",
            "url": "https://example.test/",
            "author_or_org": "Example Org",
            "source_type": "paper",
            "retrieval_status": "retrieved",
            "raw_evidence": [relative],
            "raw_evidence_sha256": [f"sha256:{digest}"],
            "raw_evidence_size_bytes": [len(payload)],
        }
        if "evaluated" in states:
            queue.update(
                {
                    "evaluation_file": str(
                        (
                            self.run_dir
                            / "sources"
                            / "evaluations"
                            / "source-evaluation.json"
                        ).relative_to(self.root)
                    ),
                    "evaluation_decision": "APPROVE",
                }
            )
        (self.run_dir / "sources" / "queue.jsonl").write_text(
            json.dumps(queue) + "\n",
            encoding="utf-8",
        )
        state = run_state(states)
        evidence_by_state = {
            "initialized": str(self.run_dir.relative_to(self.root)),
            "retrieved": str(raw_path.relative_to(self.root)),
            "evaluated": str(
                (self.run_dir / "sources" / "evaluations" / "source-evaluation.json").relative_to(
                    self.root
                )
            ),
            "proposed": str(
                (self.run_dir / "proposals" / "skill-proposal.md").relative_to(self.root)
            ),
            "novelty_checked": str(
                (self.run_dir / "reports" / "novelty-result.json").relative_to(self.root)
            ),
            "validated": str(
                (self.run_dir / "reports" / "run-readiness.json").relative_to(self.root)
            ),
            "pr_ready": str(
                (self.run_dir / "reports" / "pr-readiness.md").relative_to(self.root)
            ),
            "closed": str(
                (self.run_dir / "reports" / "closure.json").relative_to(self.root)
            ),
        }
        for entry in state["state_history"]:  # type: ignore[index]
            entry["evidence"] = evidence_by_state[entry["state"]]
        state.update(
            {
                "run_id": self.run_dir.name,
                "source_id": "S001",
                "title": "Test",
                "source_url": "https://example.test/",
                "close_status": None,
                "close_reason": None,
                "editable_surfaces": [
                    f"researcher/runs/{self.run_dir.name}/sources/",
                    f"researcher/runs/{self.run_dir.name}/proposals/",
                    f"researcher/runs/{self.run_dir.name}/reports/",
                    f"researcher/runs/{self.run_dir.name}/logs/",
                ],
                "created_at": "2026-08-17T00:00:00+00:00",
                "updated_at": "2026-08-17T00:00:00+00:00",
                "retrieval_evidence": manifest,
            }
        )
        research_loop.write_state(self.run_dir, state)
        self.write_claimed_artifacts(states)
        return state

    def write_claimed_artifacts(self, states: list[str]) -> None:
        if "evaluated" not in states:
            return
        evaluation_path = (
            self.run_dir / "sources" / "evaluations" / "source-evaluation.json"
        )
        evaluation = {
            "evaluation_id": "00000000-0000-4000-8000-000000000001",
            "timestamp": "2026-08-17T00:00:00+00:00",
            "source": {
                "url": "https://example.test/",
                "title": "Test",
                "author_or_org": "Example Org",
                "retrieval_status": "retrieved",
                "source_type": "paper",
                "primary_or_secondary": "primary",
            },
            "gatekeeper": {
                "G1_mechanism_specificity": {"pass": True, "evidence": "mechanism"},
                "G2_implementable_artifacts": {"pass": True, "evidence": "artifact"},
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
                "justification": "The fixture evidence supports the mechanism.",
            },
            "extraction": {
                "mechanism": "A deterministic fixture mechanism.",
                "implementable_artifacts": ["validator"],
                "failure_modes": ["stale input"],
                "candidate_skill_target": "existing skill",
                "candidate_skill_name": "harness-engineering",
                "taxonomy_category": "harness_engineering",
                "estimated_complexity": "medium",
            },
        }
        evaluation_path.write_text(json.dumps(evaluation) + "\n", encoding="utf-8")
        if "proposed" not in states:
            return
        proposal_path = self.run_dir / "proposals" / "skill-proposal.md"
        fields = {
            "URL": "https://example.test/",
            "Title": "Test",
            "Author or organization": "Example Org",
            "Source type": "paper",
            "Retrieval status": "retrieved",
            "Evaluation file": str(evaluation_path.relative_to(self.root)),
            "Decision": "APPROVE",
            "Target path": "skills/harness-engineering/SKILL.md",
            "Activation scenario": "fixture activation",
            "Verdict": "pass",
            "Max mechanism overlap": "0.0",
            "Top mechanism overlaps": "none",
            "Human-review rationale": "none",
            "Evidence limitations": "fixture only",
            "Possible duplication": "none",
            "Required human review": "yes",
        }
        proposal_path.write_text(
            "# Skill Proposal: Test\n\n"
            + "\n".join(f"- {key}: {value}" for key, value in fields.items())
            + "\n",
            encoding="utf-8",
        )
        if "novelty_checked" not in states:
            return
        script = Path(research_loop.__file__).with_name("novelty_check.py")
        completed = subprocess.run(
            [
                sys.executable,
                str(script),
                "--root",
                str(self.root),
                "--file",
                str(proposal_path),
                "--json",
            ],
            text=True,
            capture_output=True,
            check=False,
        )
        novelty = json.loads(completed.stdout)
        if novelty["verdict"] != "pass":
            novelty["human_review_rationale"] = "fixture review rationale"
        replacements = {
            "Verdict": novelty["verdict"],
            "Max mechanism overlap": str(novelty["max_mechanism_score"]),
            "Top mechanism overlaps": ", ".join(
                item["mechanism_id"]
                for item in novelty["top_mechanism_overlaps"]
            ) or "none",
        }
        proposal = proposal_path.read_text(encoding="utf-8")
        for label, value in replacements.items():
            proposal = re.sub(
                rf"^- {re.escape(label)}:.*$",
                f"- {label}: {value}",
                proposal,
                flags=re.MULTILINE,
            )
        proposal_path.write_text(proposal, encoding="utf-8")
        (self.run_dir / "reports" / "novelty-result.json").write_text(
            json.dumps(novelty) + "\n",
            encoding="utf-8",
        )
        if "validated" in states:
            (self.run_dir / "reports" / "run-readiness.json").write_text(
                json.dumps(
                    {
                        "ok": True,
                        "run_dir": str(self.run_dir.relative_to(self.root)),
                        "summary": {"errors": 0, "warnings": 0},
                        "findings": [],
                    }
                )
                + "\n",
                encoding="utf-8",
            )
        if "pr_ready" in states:
            (self.run_dir / "reports" / "pr-readiness.md").write_text(
                "## Summary\n\nready\n\n"
                "## Test Plan\n\nrun tests\n\n"
                "## Risks\n\nfixture risk\n\nHuman approval required.\n",
                encoding="utf-8",
            )

    def tearDown(self) -> None:
        self.temp.cleanup()

    def test_create_run_rejects_symlinked_runs_root_before_external_write(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary).resolve()
            researcher = root / "researcher"
            researcher.mkdir()
            outside = root / "outside"
            outside.mkdir()
            (researcher / "runs").symlink_to(outside, target_is_directory=True)
            args = Namespace(
                title="escaped run",
                url="https://example.test/source",
                author_or_org="Example Org",
                source_type="paper",
                reason="fixture",
            )
            with mock.patch.object(research_loop, "ROOT", root), mock.patch.object(
                research_loop, "RESEARCHER", researcher
            ), self.assertRaisesRegex(ValueError, "managed runs root must be a real directory"):
                research_loop.create_run(args)
            self.assertEqual(list(outside.iterdir()), [])

    def test_validate_run_cli_preserves_lexical_symlink_for_rejection(self) -> None:
        linked_run = self.researcher / "runs" / "linked-run"
        linked_run.symlink_to(self.run_dir, target_is_directory=True)
        with mock.patch.object(
            sys,
            "argv",
            [
                "research_loop.py",
                "validate-run",
                "--run-dir",
                str(linked_run),
            ],
        ), self.assertRaisesRegex(
            ValueError, "outside the managed runs root|must not be a symlink"
        ):
            research_loop.main()

    def test_create_run_reports_initial_validation_failure_without_false_success(self) -> None:
        args = Namespace(
            title="validation failure fixture",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        before = {path.name for path in (self.researcher / "runs").iterdir()}
        with mock.patch.object(
            research_loop,
            "run_validator",
            return_value=1,
        ), mock.patch.object(
            research_loop,
            "create_source_evaluation",
            side_effect=write_stub_source_evaluation,
        ), mock.patch.object(
            research_loop,
            "create_skill_proposal",
            side_effect=write_stub_skill_proposal,
        ), self.assertRaisesRegex(RuntimeError, "published but failed deterministic validation"):
            research_loop.create_run(args)
        after = {path.name for path in (self.researcher / "runs").iterdir()}
        created = after - before
        self.assertEqual(len(created), 1)
        created_dir = self.researcher / "runs" / created.pop()
        self.assertTrue((created_dir / "run-state.json").is_file())

    def test_create_run_failure_before_publish_cleans_staging_and_live_run(self) -> None:
        args = Namespace(
            title="prepublish failure fixture",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        live_before = {path.name for path in (self.researcher / "runs").iterdir()}
        with mock.patch.object(
            research_loop,
            "create_source_evaluation",
            side_effect=RuntimeError("injected scaffold failure"),
        ), self.assertRaisesRegex(RuntimeError, "injected scaffold failure"):
            research_loop.create_run(args)
        self.assertEqual(
            {path.name for path in (self.researcher / "runs").iterdir()},
            live_before,
        )
        staging_root = self.researcher / research_loop.RUN_INIT_STAGING_NAME
        self.assertTrue(staging_root.is_dir())
        self.assertEqual(list(staging_root.iterdir()), [])

    def test_create_run_publish_failure_cleans_only_unpublished_staging(self) -> None:
        args = Namespace(
            title="rename failure fixture",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        live_before = {path.name for path in (self.researcher / "runs").iterdir()}
        with mock.patch.object(
            research_loop,
            "create_source_evaluation",
            side_effect=write_stub_source_evaluation,
        ), mock.patch.object(
            research_loop,
            "create_skill_proposal",
            side_effect=write_stub_skill_proposal,
        ), mock.patch.object(
            research_loop.os,
            "rename",
            side_effect=OSError("injected publish failure"),
        ), self.assertRaisesRegex(OSError, "injected publish failure"):
            research_loop.create_run(args)
        self.assertEqual(
            {path.name for path in (self.researcher / "runs").iterdir()},
            live_before,
        )
        self.assertEqual(
            list((self.researcher / research_loop.RUN_INIT_STAGING_NAME).iterdir()),
            [],
        )

    def test_create_run_rejects_staged_symlink_without_touching_target(self) -> None:
        outside = self.root / "outside-evaluation.json"
        outside.write_text('{"preserve": true}\n', encoding="utf-8")

        def inject_symlink(run_dir: Path, *_args: object) -> None:
            (
                run_dir
                / "sources"
                / "evaluations"
                / "source-evaluation-draft.json"
            ).symlink_to(outside)

        args = Namespace(
            title="staged symlink fixture",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        live_before = {path.name for path in (self.researcher / "runs").iterdir()}
        with mock.patch.object(
            research_loop,
            "create_source_evaluation",
            side_effect=inject_symlink,
        ), mock.patch.object(
            research_loop,
            "create_skill_proposal",
            side_effect=write_stub_skill_proposal,
        ), self.assertRaisesRegex(ValueError, "staged run artifact is invalid"):
            research_loop.create_run(args)
        self.assertEqual(outside.read_text(encoding="utf-8"), '{"preserve": true}\n')
        self.assertEqual(
            {path.name for path in (self.researcher / "runs").iterdir()},
            live_before,
        )
        self.assertEqual(
            list((self.researcher / research_loop.RUN_INIT_STAGING_NAME).iterdir()),
            [],
        )

    def test_create_run_parent_fsync_failure_reports_durability_uncertain(self) -> None:
        args = Namespace(
            title="runs root fsync fixture",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        real_fsync_directory = research_loop._fsync_directory

        def fail_runs_root(path: Path) -> None:
            if path == self.researcher / "runs":
                raise OSError("injected runs-root fsync failure")
            real_fsync_directory(path)

        live_before = {path.name for path in (self.researcher / "runs").iterdir()}
        with mock.patch.object(
            research_loop,
            "create_source_evaluation",
            side_effect=write_stub_source_evaluation,
        ), mock.patch.object(
            research_loop,
            "create_skill_proposal",
            side_effect=write_stub_skill_proposal,
        ), mock.patch.object(
            research_loop,
            "_fsync_directory",
            side_effect=fail_runs_root,
        ), self.assertRaisesRegex(
            loop_common.DurabilityUncertainError,
            "runs-root durability is uncertain",
        ):
            research_loop.create_run(args)
        created_names = {
            path.name for path in (self.researcher / "runs").iterdir()
        } - live_before
        self.assertEqual(len(created_names), 1)
        created = self.researcher / "runs" / created_names.pop()
        self.assertTrue((created / "run-state.json").is_file())
        self.assertEqual(
            list((self.researcher / research_loop.RUN_INIT_STAGING_NAME).iterdir()),
            [],
        )

    def test_create_run_rejects_symlinked_staging_root_without_external_write(self) -> None:
        outside = self.root / "outside-staging"
        outside.mkdir()
        staging_root = self.researcher / research_loop.RUN_INIT_STAGING_NAME
        staging_root.symlink_to(outside, target_is_directory=True)
        args = Namespace(
            title="staging escape fixture",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        live_before = {path.name for path in (self.researcher / "runs").iterdir()}
        with self.assertRaisesRegex(ValueError, "staging root must be a private real directory"):
            research_loop.create_run(args)
        self.assertEqual(list(outside.iterdir()), [])
        self.assertEqual(
            {path.name for path in (self.researcher / "runs").iterdir()},
            live_before,
        )

    def test_create_run_rejects_researcher_root_outside_repository_identity(self) -> None:
        alternate_researcher = self.root / "alternate-researcher"
        (alternate_researcher / "runs").mkdir(parents=True)
        args = Namespace(
            title="root escape fixture",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        with mock.patch.object(
            research_loop,
            "RESEARCHER",
            alternate_researcher,
        ), self.assertRaisesRegex(ValueError, "confined to the repository"):
            research_loop.create_run(args)
        self.assertEqual(list((alternate_researcher / "runs").iterdir()), [])
        self.assertFalse(
            (alternate_researcher / research_loop.RUN_INIT_STAGING_NAME).exists()
        )

    def test_create_run_publishes_complete_final_identity_in_one_rename(self) -> None:
        args = Namespace(
            title="atomic identity fixture",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        with mock.patch.object(
            research_loop,
            "create_source_evaluation",
            side_effect=write_stub_source_evaluation,
        ), mock.patch.object(
            research_loop,
            "create_skill_proposal",
            side_effect=write_stub_skill_proposal,
        ), mock.patch.object(
            research_loop,
            "run_validator",
            return_value=0,
        ):
            created = research_loop.create_run(args)
        state = json.loads((created / "run-state.json").read_text(encoding="utf-8"))
        final_relative = str(created.relative_to(self.root))
        self.assertEqual(state["run_id"], created.name)
        self.assertEqual(state["state_history"][0]["evidence"], final_relative)
        self.assertTrue(
            all(created.name in surface for surface in state["editable_surfaces"])
        )
        thread = (created / "THREAD.md").read_text(encoding="utf-8")
        self.assertIn(f"# Research Thread: {created.name}", thread)
        self.assertIn(f"evidence: {final_relative}", thread)
        self.assertEqual(
            list((self.researcher / research_loop.RUN_INIT_STAGING_NAME).iterdir()),
            [],
        )
        observed_files = {
            str(path.relative_to(created))
            for path in created.rglob("*")
            if path.is_file()
        }
        self.assertTrue(research_loop.INITIAL_RUN_FILES <= observed_files)

    def test_create_run_with_real_templates_publishes_complete_scaffold(self) -> None:
        source_templates = Path(__file__).resolve().parents[2] / "templates"
        shutil.copytree(source_templates, self.researcher / "templates")
        args = Namespace(
            title="real template fixture",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        with mock.patch.object(research_loop, "run_validator", return_value=0):
            created = research_loop.create_run(args)
        state = json.loads((created / "run-state.json").read_text(encoding="utf-8"))
        self.assertEqual(state["run_id"], created.name)
        evaluation = json.loads(
            (
                created
                / "sources"
                / "evaluations"
                / "source-evaluation-draft.json"
            ).read_text(encoding="utf-8")
        )
        self.assertEqual(evaluation["source"]["url"], "https://example.test/source")
        self.assertTrue((created / "proposals" / "skill-proposal.md").is_file())

    def test_create_run_existing_final_path_has_no_staging_side_effect(self) -> None:
        fixed_now = datetime(2026, 8, 17, 12, 34, 56, tzinfo=timezone.utc)
        final = self.researcher / "runs" / "20260817-123456-existing-run"
        final.mkdir()
        marker = final / "marker.txt"
        marker.write_text("preserve\n", encoding="utf-8")
        args = Namespace(
            title="existing run",
            url="https://example.test/source",
            author_or_org="Example Org",
            source_type="paper",
            reason="fixture",
        )
        with mock.patch.object(research_loop, "datetime") as datetime_mock, \
            self.assertRaisesRegex(FileExistsError, "run already exists"):
            datetime_mock.now.return_value = fixed_now
            research_loop.create_run(args)
        self.assertEqual(marker.read_text(encoding="utf-8"), "preserve\n")
        self.assertFalse(
            (self.researcher / research_loop.RUN_INIT_STAGING_NAME).exists()
        )

    def test_pr_ready_cannot_skip_from_initialized_or_write_artifact(self) -> None:
        args = Namespace(
            run_dir=self.run_dir,
            summary="summary",
            test_plan="tests",
            risks="risks",
        )
        with self.assertRaisesRegex(
            ValueError, "illegal run-state transition initialized -> pr_ready"
        ):
            research_loop.write_pr_readiness(args)
        self.assertFalse((self.run_dir / "reports" / "pr-readiness.md").exists())
        self.assertEqual(research_loop.load_state(self.run_dir)["current_state"], "initialized")

    def test_manual_evidence_is_content_addressed_and_never_name_overwritten(self) -> None:
        sources_dir = self.root / "operator-inputs"
        first_dir = sources_dir / "first"
        second_dir = sources_dir / "second"
        first_dir.mkdir(parents=True)
        second_dir.mkdir(parents=True)
        first = first_dir / "same-name.txt"
        second = second_dir / "same-name.txt"
        first.write_bytes(b"first exact evidence")
        second.write_bytes(b"second exact evidence")
        queue_path = self.run_dir / "sources" / "queue.jsonl"

        args = Namespace(
            run_dir=self.run_dir,
            file=[first, second],
            notes="manually reviewed attachments",
        )
        self.assertEqual(research_loop.retrieve_source(args), 0)

        expected_digests = [
            hashlib.sha256(first.read_bytes()).hexdigest(),
            hashlib.sha256(second.read_bytes()).hexdigest(),
        ]
        raw_dir = self.run_dir / "sources" / "evidence" / "raw"
        self.assertEqual({path.name for path in raw_dir.iterdir()}, set(expected_digests))
        self.assertEqual((raw_dir / expected_digests[0]).read_bytes(), first.read_bytes())
        self.assertEqual((raw_dir / expected_digests[1]).read_bytes(), second.read_bytes())
        queue_record = json.loads(queue_path.read_text(encoding="utf-8"))
        self.assertEqual(
            queue_record["raw_evidence_sha256"],
            [f"sha256:{digest}" for digest in expected_digests],
        )
        self.assertEqual(research_loop.load_state(self.run_dir)["current_state"], "retrieved")

    def test_manual_retrieval_requires_bytes_before_transition(self) -> None:
        args = Namespace(run_dir=self.run_dir, file=[], notes="no bytes")
        with self.assertRaisesRegex(ValueError, "at least one --file"):
            research_loop.retrieve_source(args)
        self.assertEqual(research_loop.load_state(self.run_dir)["current_state"], "initialized")

    def test_invalid_next_evaluation_and_proposal_never_commit_state(self) -> None:
        self.write_state_with_evidence(["initialized", "retrieved"])
        evaluation = self.run_dir / "sources" / "evaluations" / "source-evaluation.json"
        evaluation.write_text("{}\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "completed evaluation is invalid"):
            research_loop.mark_evaluated(Namespace(run_dir=self.run_dir))
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"],
            "retrieved",
        )
        queue = json.loads(
            (self.run_dir / "sources" / "queue.jsonl").read_text(encoding="utf-8")
        )
        self.assertNotIn("evaluation_file", queue)

        self.write_claimed_artifacts(["evaluated"])
        evaluation_data = json.loads(evaluation.read_text(encoding="utf-8"))
        evaluation_data["timestamp"] = "2099-01-01T00:00:00+00:00"
        evaluation.write_text(json.dumps(evaluation_data) + "\n", encoding="utf-8")
        with self.assertRaisesRegex(
            ValueError,
            "timestamp must not postdate evaluation validation",
        ):
            research_loop.mark_evaluated(Namespace(run_dir=self.run_dir))
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"],
            "retrieved",
        )

        for evidence in (
            self.run_dir / "sources" / "evidence" / "raw"
        ).iterdir():
            evidence.chmod(0o600)
            evidence.unlink()
        self.write_state_with_evidence(
            ["initialized", "retrieved", "evaluated"]
        )
        proposal = self.run_dir / "proposals" / "skill-proposal.md"
        proposal.write_text("# Skill Proposal: forged\n", encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "skill proposal is invalid"):
            research_loop.mark_proposed(Namespace(run_dir=self.run_dir))
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"],
            "evaluated",
        )

    def test_next_transition_revalidates_every_previously_claimed_artifact(self) -> None:
        self.write_state_with_evidence(
            [
                "initialized",
                "retrieved",
                "evaluated",
                "proposed",
                "novelty_checked",
                "validated",
            ]
        )
        evaluation = self.run_dir / "sources" / "evaluations" / "source-evaluation.json"
        evaluation.unlink()
        readiness = self.run_dir / "reports" / "pr-readiness.md"
        with self.assertRaisesRegex(
            ValueError,
            "run claimed-artifact integrity validation failed",
        ):
            research_loop.write_pr_readiness(
                Namespace(
                    run_dir=self.run_dir,
                    summary="summary",
                    test_plan="tests",
                    risks="risks",
                )
            )
        self.assertFalse(readiness.exists())
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"],
            "validated",
        )

    def test_reduced_terminal_close_records_exact_claimed_artifact_failures(self) -> None:
        self.write_state_with_evidence(
            ["initialized", "retrieved", "evaluated"]
        )
        evaluation = self.run_dir / "sources" / "evaluations" / "source-evaluation.json"
        evaluation.unlink()
        self.assertEqual(
            research_loop.close_run(
                Namespace(
                    run_dir=self.run_dir,
                    status="abandoned",
                    reason="artifact became unavailable",
                    reviewed_by="",
                )
            ),
            0,
        )
        closure = json.loads(
            (self.run_dir / "reports" / "closure.json").read_text(encoding="utf-8")
        )
        self.assertTrue(closure["integrity_errors"])
        self.assertTrue(
            all(": " in message for message in closure["integrity_errors"])
        )
        validator = RunValidator(self.run_dir)
        validator.root = self.root
        result = validator.run()
        self.assertTrue(result["ok"])
        self.assertGreater(result["summary"]["warnings"], 0)

    def test_empty_attachment_and_malformed_source_queue_fail_before_publication(self) -> None:
        empty = self.root / "empty.bin"
        empty.write_bytes(b"")
        with self.assertRaisesRegex(ValueError, "must not be empty"):
            research_loop.retrieve_source(
                Namespace(run_dir=self.run_dir, file=[empty], notes="empty")
            )
        raw_dir = self.run_dir / "sources" / "evidence" / "raw"
        self.assertEqual(list(raw_dir.iterdir()), [])

        queue = self.run_dir / "sources" / "queue.jsonl"
        queue.write_text(
            queue.read_text(encoding="utf-8")
            + json.dumps(
                {"id": "S002", "title": "Other", "url": "https://other.test/"}
            )
            + "\n",
            encoding="utf-8",
        )
        evidence = self.root / "evidence.bin"
        evidence.write_bytes(b"nonempty")
        with self.assertRaisesRegex(ValueError, "exactly one object record"):
            research_loop.retrieve_source(
                Namespace(run_dir=self.run_dir, file=[evidence], notes="bad queue")
            )
        self.assertEqual(list(raw_dir.iterdir()), [])
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"], "initialized"
        )

    def test_partial_attachment_failure_rolls_back_every_published_byte(self) -> None:
        source = self.root / "valid.bin"
        source.write_bytes(b"valid but incomplete batch")
        missing = self.root / "missing.bin"
        queue_path = self.run_dir / "sources" / "queue.jsonl"
        queue_before = queue_path.read_bytes()
        args = Namespace(
            run_dir=self.run_dir,
            file=[source, missing],
            notes="must commit as one batch",
        )
        with self.assertRaises(FileNotFoundError):
            research_loop.retrieve_source(args)
        self.assertEqual(queue_path.read_bytes(), queue_before)
        self.assertEqual(
            list((self.run_dir / "sources" / "evidence" / "raw").iterdir()),
            [],
        )
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"], "initialized"
        )

    def test_outside_run_and_symlinked_evidence_root_are_rejected_before_write(self) -> None:
        source = self.root / "source.bin"
        source.write_bytes(b"evidence")
        outside_run = self.root / "outside-run"
        outside_run.mkdir()
        with self.assertRaisesRegex(ValueError, "outside the managed runs root"):
            research_loop.retrieve_source(
                Namespace(run_dir=outside_run, file=[source], notes="outside")
            )
        self.assertEqual(list(outside_run.iterdir()), [])

        raw_dir = self.run_dir / "sources" / "evidence" / "raw"
        raw_dir.rmdir()
        escaped = self.root / "escaped-evidence"
        escaped.mkdir()
        raw_dir.symlink_to(escaped, target_is_directory=True)
        with self.assertRaisesRegex(ValueError, "must not be a symlink"):
            research_loop.retrieve_source(
                Namespace(run_dir=self.run_dir, file=[source], notes="alias")
            )
        self.assertEqual(list(escaped.iterdir()), [])

    def test_content_address_rejects_existing_symlink(self) -> None:
        source = self.root / "source.bin"
        source.write_bytes(b"evidence")
        raw_dir = self.run_dir / "sources" / "evidence" / "raw"
        raw_dir.mkdir(parents=True, exist_ok=True)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        outside = self.root / "outside.bin"
        outside.write_bytes(source.read_bytes())
        (raw_dir / digest).symlink_to(outside)
        with self.assertRaisesRegex(RuntimeError, "single-link regular file"):
            research_loop.publish_evidence_file(source, raw_dir)

    def test_existing_hardlink_is_rejected_without_chmod_side_effect(self) -> None:
        source = self.root / "source.bin"
        source.write_bytes(b"same exact bytes")
        outside = self.root / "outside.bin"
        outside.write_bytes(source.read_bytes())
        outside.chmod(0o600)
        digest = hashlib.sha256(source.read_bytes()).hexdigest()
        raw_dir = self.run_dir / "sources" / "evidence" / "raw"
        (raw_dir / digest).hardlink_to(outside)
        before_mode = outside.stat().st_mode & 0o777
        with self.assertRaisesRegex(RuntimeError, "single-link regular file"):
            research_loop.publish_evidence_file(source, raw_dir)
        self.assertEqual(outside.stat().st_mode & 0o777, before_mode)

    def test_evidence_tamper_blocks_next_transition_and_readiness(self) -> None:
        source = self.root / "source.bin"
        source.write_bytes(b"trusted evidence")
        research_loop.retrieve_source(
            Namespace(run_dir=self.run_dir, file=[source], notes="reviewed")
        )
        manifest = research_loop.load_state(self.run_dir)["retrieval_evidence"]
        evidence_path = self.root / manifest[0]["path"]
        evidence_path.chmod(0o600)
        evidence_path.write_bytes(b"tampered evidence")
        evidence_path.chmod(0o400)
        with self.assertRaisesRegex(
            ValueError,
            "evidence bytes or file identity do not match manifest",
        ):
            research_loop.mark_evaluated(Namespace(run_dir=self.run_dir))
        validator = RunValidator(self.run_dir)
        validator.root = self.root
        result = validator.run()
        self.assertFalse(result["ok"])
        self.assertTrue(
            any(
                "evidence bytes or file identity do not match manifest"
                in finding["message"]
                for finding in result["findings"]
            )
        )

    def test_corrupt_history_blocks_a_nominal_next_transition(self) -> None:
        state = run_state(["initialized", "pr_ready"])
        (self.run_dir / "run-state.json").write_text(json.dumps(state), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "invalid run state.*illegal transition"):
            research_loop.close_run(
                Namespace(
                    run_dir=self.run_dir,
                    status="abandoned",
                    reason="stop",
                    reviewed_by="",
                )
            )

    def test_atomic_write_failure_preserves_prior_state(self) -> None:
        state_path = self.run_dir / "run-state.json"
        before = state_path.read_bytes()
        with mock.patch.object(
            research_loop,
            "write_json",
            side_effect=OSError("injected atomic write failure"),
        ):
            with self.assertRaisesRegex(OSError, "injected atomic write failure"):
                research_loop.close_run(
                    Namespace(
                        run_dir=self.run_dir,
                        status="abandoned",
                        reason="atomic failure",
                        reviewed_by="",
                    )
                )
        self.assertEqual(state_path.read_bytes(), before)
        self.assertEqual(research_loop.load_state(self.run_dir)["current_state"], "initialized")

    def test_run_state_lock_rejects_hardlinked_alias(self) -> None:
        outside = self.root / "outside.lock"
        outside.touch()
        lock_path = self.run_dir / ".run-state.lock"
        os.link(outside, lock_path)
        with self.assertRaisesRegex(ValueError, "run-state lock must be a regular file"):
            with research_loop.run_state_lock(self.run_dir):
                pass

    def test_run_state_lock_reports_replaced_path_as_durability_uncertain(self) -> None:
        lock_path = self.run_dir / ".run-state.lock"
        with self.assertRaisesRegex(
            loop_common.DurabilityUncertainError,
            "lock pathname changed",
        ):
            with research_loop.run_state_lock(self.run_dir):
                lock_path.unlink()
                lock_path.touch(mode=0o600)

    @unittest.skipUnless(hasattr(multiprocessing, "get_context"), "multiprocessing unavailable")
    def test_concurrent_same_transition_has_one_winner_without_lost_state(self) -> None:
        context = multiprocessing.get_context("spawn")
        results = context.Queue()
        ready_events = [context.Event(), context.Event()]
        processes = [
            context.Process(
                target=attempt_close_transition,
                args=(
                    str(self.run_dir),
                    str(self.root),
                    str(self.researcher),
                    str(self.root / "locks"),
                    ready_events[index],
                    results,
                ),
            )
            for index in range(2)
        ]
        with research_loop.run_state_lock(self.run_dir):
            for process in processes:
                process.start()
            self.assertTrue(all(event.wait(timeout=5) for event in ready_events))
            self.assertTrue(all(process.is_alive() for process in processes))
        for process in processes:
            process.join(timeout=5)
            if process.is_alive():
                process.terminate()
                process.join(timeout=1)
                self.fail("concurrent transition process did not finish")
            self.assertEqual(process.exitcode, 0)

        outcomes = [results.get(timeout=1) for _ in processes]
        self.assertEqual(sum(kind == "success" for kind, _ in outcomes), 1)
        errors = [message for kind, message in outcomes if kind == "error"]
        self.assertEqual(len(errors), 1)
        self.assertIn("illegal run-state transition closed -> closed", errors[0])
        state = research_loop.load_state(self.run_dir)
        self.assertEqual(state["current_state"], "closed")
        self.assertEqual(state["close_status"], "abandoned")
        self.assertEqual(
            [entry["state"] for entry in state["state_history"]],
            ["initialized", "closed"],
        )
        closure = json.loads(
            (self.run_dir / "reports" / "closure.json").read_text(encoding="utf-8")
        )
        self.assertEqual(closure["status"], "abandoned")
        self.assertEqual(closure["reason"], state["close_reason"])

    def test_accepted_closure_requires_pr_ready_and_is_side_effect_free(self) -> None:
        args = Namespace(
            run_dir=self.run_dir,
            status="accepted",
            reason="accepted",
            reviewed_by="human",
        )
        with self.assertRaisesRegex(ValueError, "accepted closure is disabled"):
            research_loop.close_run(args)
        self.assertFalse((self.run_dir / "reports" / "closure.json").exists())

    def test_corrupt_evidence_can_be_truthfully_abandoned(self) -> None:
        source = self.root / "source.bin"
        source.write_bytes(b"evidence before corruption")
        research_loop.retrieve_source(
            Namespace(run_dir=self.run_dir, file=[source], notes="reviewed")
        )
        manifest = research_loop.load_state(self.run_dir)["retrieval_evidence"]
        evidence_path = self.root / manifest[0]["path"]
        evidence_path.chmod(0o600)
        evidence_path.write_bytes(b"corrupt")
        self.assertEqual(
            research_loop.close_run(
                Namespace(
                    run_dir=self.run_dir,
                    status="abandoned",
                    reason="evidence integrity failed",
                    reviewed_by="operator",
                )
            ),
            0,
        )
        closure = json.loads(
            (self.run_dir / "reports" / "closure.json").read_text(encoding="utf-8")
        )
        self.assertTrue(closure["integrity_errors"])
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"], "closed"
        )

    def test_pr_readiness_rejects_whitespace_sections_before_write(self) -> None:
        self.write_state_with_evidence(
            [
                "initialized",
                "retrieved",
                "evaluated",
                "proposed",
                "novelty_checked",
                "validated",
            ]
        )
        with self.assertRaisesRegex(ValueError, "--summary must contain"):
            research_loop.write_pr_readiness(
                Namespace(
                    run_dir=self.run_dir,
                    summary="  \n",
                    test_plan="tests",
                    risks="risks",
                )
            )
        self.assertFalse((self.run_dir / "reports" / "pr-readiness.md").exists())

    def test_validator_zero_exit_without_passing_json_does_not_advance(self) -> None:
        self.write_state_with_evidence(
            [
                "initialized",
                "retrieved",
                "evaluated",
                "proposed",
                "novelty_checked",
            ]
        )
        novelty = (
            self.run_dir / "reports" / "novelty-result.json"
        ).read_text(encoding="utf-8")
        novelty_data = json.loads(novelty)

        def command_result(command: list[str], **_kwargs: object) -> subprocess.CompletedProcess[str]:
            if any(str(part).endswith("novelty_check.py") for part in command):
                return subprocess.CompletedProcess(
                    command,
                    0 if novelty_data["verdict"] == "pass" else 2,
                    novelty,
                    "",
                )
            return subprocess.CompletedProcess(command, 0, "not json", "")

        with mock.patch.object(
            research_loop.subprocess,
            "run",
            side_effect=command_result,
        ):
            self.assertEqual(research_loop.run_run_validator(self.run_dir), 1)
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"],
            "novelty_checked",
        )
        report = json.loads(
            (self.run_dir / "reports" / "run-readiness.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(report["ok"])

    def test_novelty_malformed_output_does_not_advance(self) -> None:
        self.write_state_with_evidence(
            ["initialized", "retrieved", "evaluated", "proposed"]
        )
        args = Namespace(run_dir=self.run_dir, human_review_rationale="")
        with mock.patch.object(
            research_loop.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 0, "not json", ""),
        ):
            self.assertEqual(research_loop.run_novelty(args), 1)
        self.assertEqual(research_loop.load_state(self.run_dir)["current_state"], "proposed")
        report = json.loads(
            (self.run_dir / "reports" / "novelty-result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["verdict"], "error")

    def test_novelty_timeout_is_persisted_without_advancing(self) -> None:
        self.write_state_with_evidence(
            ["initialized", "retrieved", "evaluated", "proposed"]
        )
        args = Namespace(run_dir=self.run_dir, human_review_rationale="")
        with mock.patch.object(
            research_loop.subprocess,
            "run",
            side_effect=subprocess.TimeoutExpired(["novelty_check.py"], 300),
        ):
            self.assertEqual(research_loop.run_novelty(args), 124)
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"], "proposed"
        )
        report = json.loads(
            (self.run_dir / "reports" / "novelty-result.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertEqual(report["verdict"], "error")
        self.assertIn("timed out after 300 seconds", report["error"])

    def test_repo_validator_launch_failure_is_a_typed_report(self) -> None:
        with mock.patch.object(
            research_loop.subprocess,
            "run",
            side_effect=OSError("checker unavailable"),
        ):
            self.assertEqual(research_loop.run_validator(self.run_dir), 126)
        report = json.loads(
            (self.run_dir / "reports" / "validation-report.json").read_text(
                encoding="utf-8"
            )
        )
        self.assertFalse(report["ok"])
        self.assertIn("checker could not start", report["findings"][0]["message"])

    def test_nonpass_novelty_requires_rationale_before_committing_state(self) -> None:
        self.write_state_with_evidence(
            ["initialized", "retrieved", "evaluated", "proposed"]
        )
        result = json.dumps(
            {
                "verdict": "human_review",
                "threshold": 0.18,
                "max_score": 0.2,
                "max_mechanism_score": 0.0,
                "top_mechanism_overlaps": [],
                "max_corpus_score": 0.2,
                "top_overlaps": [],
            }
        )
        with mock.patch.object(
            research_loop.subprocess,
            "run",
            return_value=subprocess.CompletedProcess([], 2, result, ""),
        ):
            self.assertEqual(
                research_loop.run_novelty(
                    Namespace(run_dir=self.run_dir, human_review_rationale="")
                ),
                2,
            )
            self.assertEqual(
                research_loop.load_state(self.run_dir)["current_state"], "proposed"
            )
            self.assertEqual(
                research_loop.run_novelty(
                    Namespace(
                        run_dir=self.run_dir,
                        human_review_rationale="reviewed by operator",
                    )
                ),
                0,
            )
        self.assertEqual(
            research_loop.load_state(self.run_dir)["current_state"],
            "novelty_checked",
        )

    def test_mechanism_promotion_is_disabled_without_mutation(self) -> None:
        self.write_state_with_evidence(
            [
                "initialized",
                "retrieved",
                "evaluated",
                "proposed",
                "novelty_checked",
                "validated",
                "pr_ready",
            ]
        )
        (self.run_dir / "proposals").mkdir(exist_ok=True)
        (self.run_dir / "proposals" / "mechanism-proposal.jsonl").write_text(
            json.dumps(
                {
                    "mechanism_id": "new-mechanism",
                    "status_recommendation": "accepted",
                    "owning_skill": "test",
                    "activation_scenario": "test",
                    "behavior_change": "test",
                    "evidence_claim_ids": [],
                    "failure_modes": [],
                    "review_rationale": "reviewed",
                }
            )
            + "\n",
            encoding="utf-8",
        )
        mechanisms = self.researcher / "mechanisms"
        (mechanisms / "ledgers").mkdir(parents=True)
        (mechanisms / "registry.jsonl").write_text("", encoding="utf-8")
        (mechanisms / "ledgers" / "accepted.jsonl").write_text("", encoding="utf-8")
        (mechanisms / "ledgers" / "rejected.jsonl").write_text("", encoding="utf-8")

        args = Namespace(
            run_dir=self.run_dir,
            reviewed_by="human",
        )
        with self.assertRaisesRegex(ValueError, "legacy mechanism promotion is disabled"):
            research_loop.promote_mechanisms(args)
        self.assertEqual(research_loop.load_state(self.run_dir)["current_state"], "pr_ready")
        self.assertEqual((mechanisms / "registry.jsonl").read_text(encoding="utf-8"), "")
        self.assertEqual(
            (mechanisms / "ledgers" / "accepted.jsonl").read_text(encoding="utf-8"),
            "",
        )


if __name__ == "__main__":
    unittest.main()
