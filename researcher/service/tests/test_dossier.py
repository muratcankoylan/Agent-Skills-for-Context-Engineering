import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

from researcher.service import dossier
from researcher.service.contracts import ServiceError, digest
from researcher.service.research_pipeline import _write, _envelope, _record, _result
from researcher.service.tracing import Tracer


class DossierTests(unittest.TestCase):
    def setUp(self):
        temporary = tempfile.TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.root = Path(temporary.name).resolve()
        self.pipeline = self.root / "pipeline"
        self.pipeline.mkdir(mode=0o700)
        inputs = {"schema": "research-pipeline-input/v1", "authority": "none",
                  "source_job": "daily", "skills": ["context-fundamentals"]}
        packet = {"schema": "research-pipeline-phase/v1", "phase": "packet",
                  "input_digest": digest({"input": digest(inputs)}), "output": {"fixture": True}}
        phase = {"schema": "research-pipeline-phase/v1", "phase": "research",
                 "input_digest": digest({"packet_digest": digest(packet["output"])}),
                 "output": {"hypothesis": "<script>alert(1)</script>"}}
        receipts = {"packet": digest(packet), "research": digest(phase)}
        state = {"schema": "research-pipeline-state/v1", "input_digest": digest(inputs),
                 "receipts": receipts, "outcome": "abstained", "fixture": True,
                 "packet_digest": digest(packet["output"]), "execution_backend": "codex_sdk",
                 "phase": "terminal", "created_at": 1}
        result = _result(state, "abstained")
        state["result_digest"] = digest(result)
        for name, value in (("input", inputs), ("packet", packet), ("research", phase), ("result", result), ("state", state)):
            _write(self.pipeline / (name + ".json"), _envelope(value))

    def rewrite(self, name, change, *, rebind=False):
        value = _record(self.pipeline / (name + ".json"))
        change(value)
        _write(self.pipeline / (name + ".json"), _envelope(value))
        if rebind:
            state = _record(self.pipeline / "state.json")
            if name in state["receipts"]:
                state["receipts"][name] = digest(value)
            result = _result(state, state["outcome"])
            state["result_digest"] = digest(result)
            _write(self.pipeline / "state.json", _envelope(state))
            _write(self.pipeline / "result.json", _envelope(result))

    def add_learning(self):
        archive = {"schema": "sdk-researcher-memory/v1", "authority": "none", "role": "researcher",
            "semantic_novelty_assessed": False, "entries": [], "omissions": {
                "incompatible": 1, "no_research": 0, "entry_limit": 0, "byte_limit": 0, "source_limit": 0}}
        learning = {"schema": "sdk-learning-checkpoint/v1", "authority": "none", "sources": [
            {"path": str(self.root / "not-opened-private-history"), "result_digest": digest("history"),
             "omission": "incompatible"}], "archive": archive, "candidates": [], "source_limit_omissions": 0}
        state = _record(self.pipeline / "state.json")
        state["learning"] = {"checkpoint_digest": digest(learning), "included": 0, "omissions": archive["omissions"],
                            "candidate_identities": 0, "semantic_novelty_assessed": False, "researcher_only": True}
        packet = _record(self.pipeline / "packet.json")
        packet["output"]["researcher_feedback"] = archive
        state["packet_digest"] = digest(packet["output"])
        research = _record(self.pipeline / "research.json")
        research["input_digest"] = digest({"packet_digest": state["packet_digest"]})
        state["receipts"] = {"packet": digest(packet), "research": digest(research)}
        result = _result(state, "abstained")
        state["result_digest"] = digest(result)
        for name, value in (("learning", learning), ("state", state), ("result", result),
                            ("packet", packet), ("research", research)):
            _write(self.pipeline / (name + ".json"), _envelope(value))
        return learning

    def test_read_only_projection_escapes_research_and_keeps_evidence_class(self):
        with patch("socket.socket.connect", side_effect=AssertionError("network")):
            value = dossier.build([self.pipeline], [])
        self.assertEqual(value["outcomes"], {"abstained": 1})
        self.assertFalse(value["provider_readback_verified"])
        self.assertFalse(value["historical_origin_verified"])
        self.assertFalse(value["scientific_validity_verified"])
        self.assertFalse(value["traces_correlated_to_pipelines"])
        page = dossier.html(value)
        self.assertNotIn("<script>", page)
        self.assertIn("&lt;script&gt;", page)
        self.assertIn("default-src 'none'", page)

    def test_phase_tampering_refused_even_with_new_inner_digest(self):
        _write(self.pipeline / "research.json", _envelope({"phase": "research", "output": {}}))
        with self.assertRaisesRegex(ServiceError, "BINDING"):
            dossier.build([self.pipeline], [])

    def test_phase_schema_and_input_binding_refused_even_after_rehashing(self):
        original = _record(self.pipeline / "research.json")
        for mutation in ({"schema": "fake/v1"}, {"input_digest": digest("other-packet")},
                         {"historical_origin_verified": True}):
            _write(self.pipeline / "research.json", _envelope(original))
            self.rewrite("research", lambda value: value.update(mutation), rebind=True)
            with self.subTest(mutation=mutation), self.assertRaises(ServiceError):
                dossier.build([self.pipeline], [])

    def test_production_and_scientific_authority_claims_refused_even_after_rehashing(self):
        original = _record(self.pipeline / "result.json")
        for mutation in ({"production_ready": True}, {"scientific_improvement_demonstrated": True},
                         {"schema": "fake-result/v1"}, {"publication": "published"}, {"authority": "accepted"}):
            value = {**original, **mutation}
            _write(self.pipeline / "result.json", _envelope(value))
            self.rewrite("state", lambda state: state.update(result_digest=digest(value)))
            with self.subTest(mutation=mutation), self.assertRaises(ServiceError):
                dossier.build([self.pipeline], [])

    def test_learning_current_shape_is_bound_without_reading_historical_paths(self):
        learning = self.add_learning()
        value = dossier.build([self.pipeline], [])
        projected = value["pipelines"][0]["learning_record"]
        self.assertEqual(projected["checkpoint_digest"], digest(learning))
        self.assertFalse(projected["historical_origin_verified"])
        self.assertNotIn("path", projected["sources"][0])
        self.assertNotIn("not-opened-private-history", dossier.html(value))
        self.assertEqual(projected["archive"], learning["archive"])

    def test_unbound_learning_extra_record_and_rehashed_checkpoint_refused(self):
        learning = self.add_learning()
        self.rewrite("learning", lambda value: value["archive"]["omissions"].update(source_limit=1))
        with self.assertRaises(ServiceError):
            dossier.build([self.pipeline], [])
        _write(self.pipeline / "learning.json", _envelope(learning))
        self.rewrite("state", lambda state: state.pop("learning"), rebind=True)
        with self.assertRaises(ServiceError):
            dossier.build([self.pipeline], [])

    def test_learning_schema_and_packet_feedback_mismatch_are_refused(self):
        self.add_learning()
        self.rewrite("learning", lambda value: value.update(schema="unrecognized/v1"))
        with self.assertRaises(ServiceError):
            dossier.build([self.pipeline], [])
        self.add_learning()
        packet = _record(self.pipeline / "packet.json")
        packet["output"]["researcher_feedback"] = {"semantic_novelty_assessed": True}
        _write(self.pipeline / "packet.json", _envelope(packet))
        self.rewrite("state", lambda state: state.update(packet_digest=digest(packet["output"])))
        self.rewrite("research", lambda row: row.update(input_digest=digest({"packet_digest": digest(packet["output"])})), rebind=True)
        self.rewrite("packet", lambda row: None, rebind=True)
        with self.assertRaises(ServiceError):
            dossier.build([self.pipeline], [])

    def test_actual_completed_fixture_pipeline_learning_shape_is_compatible(self):
        from researcher.service.tests.test_research_pipeline import PipelineTests
        fixture = PipelineTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        result = fixture.run_pipeline(learning_sources=[])
        calls = len(fixture.calls)
        value = dossier.build([fixture.destination], [])
        self.assertEqual(value["pipelines"][0]["result"], result)
        self.assertEqual(value["pipelines"][0]["learning_record"]["archive"]["entries"], [])
        self.assertEqual(len(fixture.calls), calls)
        self.assertFalse(value["historical_origin_verified"])

    def test_actual_evaluated_fixture_is_not_presented_as_accepted_or_held_out_verified(self):
        from researcher.service.agents_evals import fixture_dataset
        from researcher.service.tests.test_research_pipeline import PipelineTests
        fixture = PipelineTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        fixture.abstain = False
        result = fixture.run_pipeline(dataset=fixture_dataset())
        value = dossier.build([fixture.destination], [])
        self.assertEqual(value["pipelines"][0]["result"], result)
        self.assertEqual(result["outcome"], "evaluated_not_accepted")
        self.assertFalse(result["detail"]["held_out_verified"])
        result["detail"]["held_out_verified"] = True
        state = _record(fixture.destination / "state.json")
        state["result_digest"] = digest(result)
        _write(fixture.destination / "state.json", _envelope(state))
        _write(fixture.destination / "result.json", _envelope(result))
        with self.assertRaises(ServiceError):
            dossier.build([fixture.destination], [])

    def test_current_learning_candidate_plan_digest_field_is_private_and_typed(self):
        learning = self.add_learning()
        learning["sources"][0]["omission"] = None
        learning["archive"]["omissions"].update(incompatible=0, entry_limit=1)
        candidate = {"baseline_commit": "a" * 40, "corpus_digest": digest("corpus"),
                     "text_sha256": digest("text"), "path": "skills/context-fundamentals/SKILL.md",
                     "source_result_digest": digest("history"), "evaluation_plan_digest": None}
        learning["candidates"] = [candidate]
        state = {"learning": {"checkpoint_digest": digest(learning), "included": 0,
            "omissions": learning["archive"]["omissions"], "candidate_identities": 1,
            "semantic_novelty_assessed": False, "researcher_only": True}}
        value = dossier._learning(learning, state, {})
        self.assertIsNone(value["candidates"][0]["evaluation_plan_digest"])
        for invalid in (True, "verified", {}):
            learning["candidates"][0]["evaluation_plan_digest"] = invalid
            state["learning"]["checkpoint_digest"] = digest(learning)
            with self.subTest(invalid=invalid), self.assertRaises(ServiceError):
                dossier._learning(learning, state, {})

    def test_trace_ids_and_latency_retained_without_export(self):
        state = self.root / "trace-state"
        state.mkdir(mode=0o700)
        tracer = Tracer.at(state)
        with tracer.span("pipeline.run"):
            pass
        value = dossier.build([self.pipeline], [state])
        journal = value["trace_journals"][0]
        self.assertEqual(journal["operations"]["pipeline.run"]["count"], 1)
        self.assertEqual(len(journal["spans"][0]["trace_id"]), 32)
        self.assertEqual(journal["deliveries"], [])

    def test_alias_and_duplicate_selection_refused(self):
        with self.assertRaises(ServiceError):
            dossier.build([self.pipeline, self.pipeline], [])
        alias = self.root / "alias"
        alias.symlink_to(self.pipeline, target_is_directory=True)
        with self.assertRaises(ServiceError):
            dossier.build([alias], [])

    def test_size_budget_and_missing_terminal_refused(self):
        with patch.object(dossier, "MAX_TOTAL_BYTES", 1), self.assertRaises(ServiceError):
            dossier.build([self.pipeline], [])
        (self.pipeline / "result.json").unlink()
        with self.assertRaises((ServiceError, OSError)):
            dossier.build([self.pipeline], [])

    def test_html_bound_is_explicit_not_silent_truncation(self):
        value = dossier.build([self.pipeline], [])
        with patch.object(dossier, "MAX_TOTAL_BYTES", 100), self.assertRaisesRegex(ServiceError, "SIZE_LIMIT"):
            dossier.html(value)

    def test_file_symlink_and_hardlink_are_not_read(self):
        import os
        source = self.pipeline / "research.json"
        retained = self.root / "retained.json"
        source.rename(retained)
        for mode in ("symlink", "hardlink"):
            if source.is_symlink() or source.exists():
                source.unlink()
            source.symlink_to(retained) if mode == "symlink" else os.link(retained, source)
            with self.subTest(mode=mode), self.assertRaises(ServiceError):
                dossier.build([self.pipeline], [])
