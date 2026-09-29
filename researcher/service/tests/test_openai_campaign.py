"""Offline admission, recovery and gold-free execution contracts."""
from dataclasses import replace
from pathlib import Path
from tempfile import TemporaryDirectory
import unittest

from researcher.service.agents_evals import build_plan, fixture_dataset
from researcher.service.contracts import ServiceError
from researcher.service.openai_campaign import Campaign, PRICING, initialize
from researcher.service.providers import ModelResult, ProviderError


class CampaignTests(unittest.TestCase):
    def setUp(self):
        self.temp = TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name).resolve() / "authority"
        self.calls, self.events = [], []
        self.clock = 1790632800

    def model(self, request, *, credential):
        self.calls.append(request)
        return ModelResult('{"answer":true}', 12, 10, PRICING["model"],
                           "resp_" + str(len(self.calls)), "default")

    def campaign(self, cap=1000000, prior=0, **kwargs):
        initialize(self.directory, cap_microusd=cap, prior_spend_microusd=prior)
        return self.reopen(**kwargs)

    def reopen(self, **kwargs):
        return Campaign(self.directory, credential="fixture-secret", model_call=kwargs.pop("model_call", self.model),
                        progress=self.events.append, now=lambda: self.clock, **kwargs)

    def call(self, runner, item="one", **kwargs):
        return runner.call("test", item, instructions="Follow the schema.", prompt="Input.",
                           max_output_tokens=256, **kwargs)

    def code(self, expected, fn, *args, **kwargs):
        with self.assertRaises(ServiceError) as error:
            fn(*args, **kwargs)
        self.assertEqual(error.exception.code, expected)

    def test_resume_replays_without_credential_or_spend(self):
        runner = self.campaign()
        first = self.call(runner)
        second = Campaign(self.directory, model_call=self.model, progress=self.events.append)
        self.assertEqual(first, self.call(second))
        self.assertEqual(len(self.calls), 1)
        status = runner.status()
        self.assertEqual(status["attempted_calls"], 1)
        self.assertGreater(status["reserved_microusd"], status["observed_usage"]["estimated_upper_cost_microusd"])
        self.assertFalse(status["invoice_verified"])

    def test_default_native_executor_is_retired_before_admission(self):
        initialize(self.directory, cap_microusd=1000000, prior_spend_microusd=0)
        runner = Campaign(self.directory, credential="fixture-secret", progress=self.events.append,
                          now=lambda: self.clock)
        self.code("NATIVE_AGENT_EXECUTION_RETIRED_USE_CODEX_SDK", self.call, runner)
        self.assertEqual(runner.status()["attempted_calls"], 0)
        self.assertEqual(runner.store.status()["jobs"], [])

    def test_lifetime_cap_across_days_and_new_jobs(self):
        runner = self.campaign(cap=20000)
        self.call(runner)
        self.clock += 86400
        self.code("LIFETIME_BUDGET_EXHAUSTED", self.call, self.reopen(), "two")
        self.assertEqual(len(self.calls), 1)

    def test_prior_spend_consumes_same_ceiling(self):
        runner = self.campaign(cap=1000000, prior=990000)
        self.code("LIFETIME_BUDGET_EXHAUSTED", self.call, runner)
        self.assertFalse(self.calls)
        self.assertEqual(runner.status()["available_microusd"], 10000)

    def test_no_reset_and_no_parallel_worker(self):
        runner = self.campaign()
        self.code("BUDGET_AUTHORITY_ALREADY_EXISTS", initialize, self.directory,
                  cap_microusd=1000000, prior_spend_microusd=0)
        self.code("CAMPAIGN_CONCURRENCY_MUST_BE_ONE", self.reopen, concurrency=2)
        with runner.store.worker_lock():
            self.code("WORKER_ALREADY_RUNNING", self.call, self.reopen())
        self.assertFalse(self.calls)

    def test_drift_rejected_before_dispatch(self):
        runner = self.campaign()
        self.call(runner)
        self.code("EFFECT_INPUT_CHANGED", runner.call, "test", "one", instructions="Different.",
                  prompt="Input.", max_output_tokens=256)
        self.assertEqual(len(self.calls), 1)

    def test_unknown_retains_reservation_and_never_retries(self):
        def timeout(*args, **kwargs):
            self.calls.append("attempt")
            raise ProviderError("MODEL_WALL_TIMEOUT", "Unknown")
        runner = self.campaign(model_call=timeout)
        self.code("MODEL_WALL_TIMEOUT", self.call, runner)
        reserved = runner.status()["reserved_microusd"]
        self.code("EFFECT_RECONCILIATION_REQUIRED", self.call, self.reopen())
        self.assertEqual(len(self.calls), 1)
        self.assertEqual(runner.status()["reserved_microusd"], reserved)
        self.assertEqual(runner.status()["unresolved_calls"], 1)

    def test_receipt_model_tier_and_usage_fail_closed(self):
        for field, value in (("model", "other"), ("service_tier", "priority"),
                             ("input_tokens", 999999), ("output_tokens", 999999), ("request_id", None)):
            with self.subTest(field=field):
                directory = self.directory.parent / field
                initialize(directory, cap_microusd=1000000, prior_spend_microusd=0)
                def bad(request, *, credential):
                    return replace(self.model(request, credential=credential), **{field: value})
                runner = Campaign(directory, credential="fixture-secret", model_call=bad,
                                  progress=self.events.append, now=lambda: self.clock)
                self.code("MODEL_RECEIPT_OUT_OF_CONTRACT", self.call, runner)
                self.assertEqual(runner.status()["unresolved_calls"], 1)

    def test_context_secret_and_expired_pricing_before_dispatch(self):
        runner = self.campaign()
        self.code("CAMPAIGN_CONTEXT_LIMIT", runner.call, "test", "large",
                  instructions="x", prompt="x" * 131072)
        self.code("CREDENTIAL_IN_CONTEXT", runner.call, "test", "secret",
                  instructions="x", prompt="fixture-secret")
        self.clock = PRICING["valid_before_epoch"]
        self.code("PRICING_REVIEW_REQUIRED", self.call, runner)
        self.assertFalse(self.calls)

    def test_response_secret_never_persisted(self):
        def bad(request, *, credential):
            return replace(self.model(request, credential=credential), text=credential)
        runner = self.campaign(model_call=bad)
        self.code("CREDENTIAL_REFLECTION", self.call, runner)
        with runner.store._history_snapshot() as db:
            self.assertIsNone(db.execute("SELECT output FROM effects").fetchone()[0])

    def test_nested_json_escaped_key_rejected_before_persistence(self):
        import json
        from urllib.parse import quote
        runner = self.campaign()
        escaped = ''.join('\\u%04x' % ord(char) for char in 'fixture-secret')
        encoded = '{"field":"' + escaped + '"}'
        for index, prompt in enumerate((encoded, json.dumps({"nested": encoded}), quote(encoded))):
            self.code("CREDENTIAL_IN_CONTEXT", runner.call, "test", "escaped-" + str(index),
                      instructions="x", prompt=prompt)
        self.assertFalse(self.calls)
        self.assertEqual(runner.status()["attempted_calls"], 0)
        with runner.store._history_snapshot() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 0)

    def test_key_in_campaign_identity_cannot_enter_logs_or_manifest(self):
        runner = self.campaign()
        self.code("CREDENTIAL_IN_CONTEXT", runner.call, "fixture-secret", "one",
                  instructions="x", prompt="Harmless input.", max_output_tokens=256)
        self.code("CREDENTIAL_IN_CONTEXT", runner.call, "test", "fixture-secret",
                  instructions="x", prompt="Harmless input.", max_output_tokens=256)
        self.assertFalse(self.events)
        self.assertFalse(self.calls)
        with runner.store._history_snapshot() as db:
            self.assertEqual(db.execute("SELECT count(*) FROM jobs").fetchone()[0], 0)

    def test_nested_response_json_key_rejected_without_receipt(self):
        import json
        def bad(request, *, credential):
            escaped = ''.join('\\u%04x' % ord(char) for char in credential)
            return replace(self.model(request, credential=credential),
                text=json.dumps({"nested": '{"field":"' + escaped + '"}'}))
        runner = self.campaign(model_call=bad)
        self.code("CREDENTIAL_REFLECTION", self.call, runner)
        with runner.store._history_snapshot() as db:
            self.assertIsNone(db.execute("SELECT output FROM effects").fetchone()[0])

    def test_secret_scan_exhaustion_fails_closed(self):
        from researcher.service.openai_campaign import _reflected
        self.code("CREDENTIAL_SCAN_LIMIT", _reflected, [0] * 17000, "fixture-secret")
        self.assertFalse(_reflected({"ordinary": 'An unmatched "quote" and λ.'}, "fixture-secret"))

    def test_secret_in_response_identifier_never_persisted(self):
        def bad(request, *, credential):
            return replace(self.model(request, credential=credential), request_id=credential)
        runner = self.campaign(model_call=bad)
        self.code("CREDENTIAL_REFLECTION", self.call, runner)
        with runner.store._history_snapshot() as db:
            self.assertIsNone(db.execute("SELECT output FROM effects").fetchone()[0])

    def test_completed_receipt_interrupted_before_terminal_status_recovers(self):
        runner = self.campaign()
        first = self.call(runner)
        with runner.store._connect() as db:
            db.execute("UPDATE jobs SET status='running'")
        self.assertEqual(first, self.call(self.reopen()))
        self.assertEqual(runner.store.status()["jobs"][0]["status"], "execution_complete")
        self.assertEqual(len(self.calls), 1)

    def test_local_completion_error_preserves_paid_receipt_for_replay(self):
        from unittest.mock import patch
        runner = self.campaign()
        with patch.object(runner.store, "finish", side_effect=OSError("fixture disk fault")):
            self.code("MODEL_OUTCOME_UNKNOWN", self.call, runner)
        status = runner.status()
        self.assertEqual(status["completed_calls"], 1)
        self.assertEqual(status["unresolved_calls"], 0)
        self.assertEqual(runner.store.status()["jobs"][0]["status"], "reconciliation_required")
        self.call(self.reopen())
        self.assertEqual(runner.status()["reserved_microusd"], status["reserved_microusd"])
        self.assertEqual(runner.store.status()["jobs"][0]["status"], "execution_complete")
        self.assertEqual(len(self.calls), 1)

    def test_paired_executor_keeps_format_failures_and_no_gold(self):
        runner = self.campaign(cap=5000000)
        plan = build_plan(fixture_dataset(), baseline_skill="Baseline guidance.",
                          candidate_skill="Candidate guidance.", model=PRICING["model"],
                          replications=1, max_sessions=12)
        report = runner.evaluate("paired", plan, max_output_tokens=256)
        self.assertEqual(len(report["results"]), 12)
        self.assertEqual(len(self.calls), 12)
        self.assertFalse(report["held_out_effectiveness_demonstrated"])
        for request in self.calls:
            self.assertNotIn('"gold"', request.prompt)
            self.assertNotIn('"group_id"', request.prompt)
            self.assertNotIn('"condition"', request.prompt)
        again = runner.evaluate("paired", plan, max_output_tokens=256)
        self.assertEqual(again, report)
        self.assertEqual(len(self.calls), 12)

    def test_failed_calls_remain_in_paired_denominator(self):
        def timeout(*args, **kwargs):
            raise ProviderError("MODEL_WALL_TIMEOUT", "Unknown")
        runner = self.campaign(cap=5000000, model_call=timeout)
        plan = build_plan(fixture_dataset(), baseline_skill="Baseline.", candidate_skill="Candidate.",
                          model=PRICING["model"], replications=1, max_sessions=12)
        report = runner.evaluate("failed-paired", plan, max_output_tokens=256)
        self.assertEqual(len(report["results"]), 12)
        self.assertEqual(len(report["failures"]), 12)
        self.assertEqual(runner.status()["unresolved_calls"], 12)

    def test_invalid_research_citation_stops_before_paid_critic(self):
        import json
        from researcher.service.agents_context import compile_request
        from researcher.service.tests.test_agents_context import AgentsContextTests
        fixture = AgentsContextTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        research = fixture.result["research"]
        def invalid(request, *, credential):
            data = json.loads(request.prompt)
            research["claims"][0]["citations"][0] = {
                "evidence_id": fixture.corpus["excerpts"][0]["id"],
                "span_id": data["evidence"][0]["citation_spans"][0]["span_id"]}
            return replace(self.model(request, credential=credential), text=json.dumps(research))
        runner = self.campaign(model_call=invalid)
        request = compile_request(model=PRICING["model"], query=fixture.query,
                                  corpus=fixture.corpus, evidence=fixture.evidence)
        packet = {"schema": "managed-research-packet/v1", "model": PRICING["model"],
                  "query": fixture.query, "corpus": fixture.corpus, "evidence": fixture.evidence,
                  "max_subagents": 0, "fixture": True, "request": request}
        self.code("CITATION_SPAN_EVIDENCE_MISMATCH", runner.research, "invalid-corpus-citation", packet)
        self.assertEqual(len(self.calls), 1)
        self.assertIn("not research evidence", self.calls[0].system)

    def research_fixture(self, text=None):
        from researcher.service.agents_context import compile_request
        from researcher.service.tests.test_agents_context import AgentsContextTests
        from researcher.scripts.schema_contract import sha256_bytes
        fixture = AgentsContextTests()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        if text is not None:
            fixture.evidence[0]["text"] = text
            fixture.evidence[0]["sha256"] = sha256_bytes(text.encode())
        request = compile_request(model=PRICING["model"], query=fixture.query,
                                  corpus=fixture.corpus, evidence=fixture.evidence)
        packet = {"schema": "managed-research-packet/v1", "model": PRICING["model"],
                  "query": fixture.query, "corpus": fixture.corpus, "evidence": fixture.evidence,
                  "max_subagents": 0, "fixture": True, "request": request}
        return fixture, packet

    def test_span_research_resolves_exact_bytes_before_critic_and_replays(self):
        import json
        from researcher.service.tests.test_citation_spans import research
        from researcher.service.citation_spans import build_catalog
        fixture, packet = self.research_fixture("Reported λ🙂 mechanism\nwith an important qualifier.")
        catalog = build_catalog(json.loads(packet["request"]["input"])["evidence"])
        def select(request, *, credential):
            data = json.loads(request.prompt)
            if "Form one falsifiable" in request.system:
                self.assertNotIn("text", data["evidence"][0])
                self.assertEqual(data["citation_catalog_digest"], catalog["catalog_digest"])
                output = research(catalog)
            else:
                self.assertEqual(data["research"]["claims"][0]["citations"][0]["quote"], fixture.evidence[0]["text"])
                self.assertNotIn("span_id", data["research"]["claims"][0]["citations"][0])
                output = {"supported_claim_ids": ["claim"], "issues": ["Need independent measurement."],
                          "recommendation": "abstain"}
            return replace(self.model(request, credential=credential), text=json.dumps(output))
        runner = self.campaign(model_call=select)
        result = runner.research("exact-span", packet)
        self.assertIsNone(result["proposal"])
        self.assertEqual(len(self.calls), 2)
        runner.credential = None
        self.assertEqual(runner.research("exact-span", packet), result)
        self.assertEqual(len(self.calls), 2)
        with runner.store._history_snapshot() as db:
            raw_receipts = [json.loads(row["output"]) for row in db.execute("SELECT output FROM effects")]
            researcher = next(row for row in raw_receipts if "span_id" in row["response"]["text"])
            self.assertNotIn('"quote"', researcher["response"]["text"])
            self.assertIn(catalog["sources"][0]["spans"][0]["span_id"], researcher["response"]["text"])

    def test_legacy_quote_output_is_not_repaired_or_retried(self):
        import json
        fixture, packet = self.research_fixture()
        def legacy(request, *, credential):
            return replace(self.model(request, credential=credential), text=json.dumps(fixture.result["research"]))
        runner = self.campaign(model_call=legacy)
        self.code("INVALID_SPAN_RESEARCH_OUTPUT", runner.research, "legacy-quote", packet)
        self.code("INVALID_SPAN_RESEARCH_OUTPUT", runner.research, "legacy-quote", packet)
        self.assertEqual(len(self.calls), 1)

    def test_span_catalog_selection_respects_exact_prompt_envelope_limit(self):
        import json
        from dataclasses import asdict
        from researcher.scripts.schema_contract import canonicalize
        # A source close to the old packet limit forces finite selection. Quotes,
        # backslashes and Unicode exercise double-encoded request byte accounting.
        fixture, packet = self.research_fixture(('"\\λ\n' * 9400))
        selected = []
        def abstain(request, *, credential):
            self.assertLessEqual(len(canonicalize(asdict(request))), 131072)
            if "Form one falsifiable" in request.system:
                data = json.loads(request.prompt)
                selected.append(data["evidence"][0]["citation_selection"])
                output = {"hypothesis": "Insufficient evidence.", "test_plan": "Acquire an independent sample.",
                          "abstain": True, "claims": []}
            else:
                output = {"supported_claim_ids": [], "issues": [], "recommendation": "abstain"}
            return replace(self.model(request, credential=credential), text=json.dumps(output))
        runner = self.campaign(cap=5000000, model_call=abstain)
        runner.research("bounded-span", packet)
        self.assertGreater(selected[0]["omitted_bytes"], 0)
        self.assertGreater(selected[0]["selected_bytes"], 0)


if __name__ == "__main__":
    unittest.main()
