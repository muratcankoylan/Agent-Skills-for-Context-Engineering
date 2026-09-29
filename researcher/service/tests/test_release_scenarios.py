"""The scenario report cannot turn empty/skipped work into a release result."""
import socket
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

from researcher.service import release_scenarios as module


class ReleaseScenarioTests(unittest.TestCase):
    def test_daily_restarts_include_coordinator_trace_and_shutdown_capabilities(self):
        self.assertIn("test_organization_capabilities", module.SCENARIOS["daily-restarts"])

    def row(self, name="runner-recovery"):
        return {"scenario": name, "passed": True, "planned": len(module.SCENARIOS[name]),
                "executed": len(module.SCENARIOS[name]), "elapsed_ms": 1,
                "modules": dict.fromkeys(module.SCENARIOS[name], 1),
                **{field: [] for field in module.OUTCOMES}}

    def test_catalog_has_distinct_real_test_modules(self):
        loader = unittest.TestLoader()
        modules = [name for group in module.SCENARIOS.values() for name in group]
        self.assertEqual(len(modules), len(set(modules)))
        for name in modules:
            with self.subTest(module=name):
                suite = loader.loadTestsFromName("researcher.service.tests." + name)
                self.assertGreater(suite.countTestCases(), 0)
        self.assertEqual(loader.errors, [])

    def test_empty_duplicate_and_unknown_scenarios_are_not_a_pass(self):
        for rows in ([], [{"scenario": "missing", "passed": True}],
                     [{"scenario": "managed-lifecycle", "passed": True}] * 2):
            with self.assertRaisesRegex(ValueError, "COVERAGE"):
                module.report(rows, {})

    def test_failure_is_in_denominator_and_no_live_or_hosted_claim(self):
        value = module.report([
            self.row("managed-lifecycle"),
            {"scenario": "runner-recovery", "passed": False, "elapsed_ms": 1,
             "reason": "SCENARIO_DEADLINE_EXCEEDED"}], {})
        self.assertFalse(value["passed"])
        self.assertEqual(value["planned_scenarios"], 2)
        self.assertEqual(value["executed_tests"], 2)
        self.assertFalse(value["complete_catalog"])
        self.assertFalse(value["live_provider_execution"])
        self.assertFalse(value["hosted_github_execution"])
        self.assertFalse(value["scientific_effectiveness_measured"])

    def test_invalid_request_never_starts_subprocess(self):
        with patch.object(module.subprocess, "Popen") as start:
            for name, timeout in (("missing", 1), ("managed-lifecycle", True),
                                  ("managed-lifecycle", 301)):
                with self.assertRaises(ValueError):
                    module.execute(name, None, timeout_seconds=timeout)
            start.assert_not_called()

    def test_no_traceback_or_fixture_text_in_worker_result(self):
        class Failing(unittest.TestCase):
            def runTest(self):
                raise ValueError("fixture-sensitive-diagnostic")
        with patch.object(module.unittest.TestLoader, "loadTestsFromName",
                          return_value=unittest.TestSuite([Failing()])):
            result = module._worker("runner-recovery")
        self.assertFalse(result["passed"])
        self.assertEqual(len(result["errors"]), 1)
        self.assertNotIn("fixture-sensitive-diagnostic", str(result))

    def test_empty_constituent_module_cannot_pass(self):
        with patch.object(module.unittest.TestLoader, "loadTestsFromName", side_effect=[
                unittest.TestSuite(), unittest.TestSuite([unittest.FunctionTestCase(lambda: None)])]):
            result = module._worker("managed-lifecycle")
        self.assertFalse(result["passed"])
        self.assertEqual(result["modules"]["test_agents_runtime"], 0)
        module.validate_row(result)

    def test_closed_result_contract_rejects_false_passes_and_sensitive_extra_fields(self):
        bad_rows = [{"scenario": "runner-recovery", "passed": True},
                    {**self.row(), "executed": 0}, {**self.row(), "planned": True},
                    {**self.row(), "private": "fixture-sensitive"},
                    {**self.row(), "skipped": ["test_case"]},
                    {**self.row(), "modules": {"test_github_runner_recovery": 0}},
                    {**self.row(), "errors": ["raw diagnostic/path"]},
                    {**self.row(), "elapsed_ms": -1}]
        for row in bad_rows:
            with self.subTest(row=row), self.assertRaisesRegex(ValueError, "INVALID_SCENARIO_RESULT"):
                module.report([row], {})

    def test_numeric_loopback_permitted_but_external_and_named_hosts_denied(self):
        with socket.socket() as connection:
            calls = []
            connect = module._loopback_only(lambda sock, address: calls.append(address))
            connect(connection, ("127.0.0.1", 1))
            for address in (("localhost", 1), ("8.8.8.8", 443), ("example.com", 443), "file"):
                with self.assertRaises(AssertionError):
                    connect(connection, address)
            self.assertEqual(calls, [("127.0.0.1", 1)])

    def test_import_discovery_is_inside_network_guard(self):
        def load(name):
            with socket.socket() as connection:
                connection.connect(("192.0.2.1", 443))
        with patch.object(module.unittest.TestLoader, "loadTestsFromName", side_effect=load):
            with self.assertRaisesRegex(AssertionError, "numeric loopback"):
                module._worker("runner-recovery")

    def test_source_identity_includes_generated_bytes_not_just_executable_code(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            generated = root / "generated.json"
            generated.write_text('{"version": 1}')
            with patch("researcher.service.candidate_review._paths", return_value=["generated.json"]), \
                 patch("researcher.service.workflow.git_head", return_value="a" * 40), \
                 patch("researcher.service.workflow.implementation", return_value="same-code"):
                before = module.source_identity(root)
                generated.write_text('{"version": 2}')
                after = module.source_identity(root)
            self.assertEqual(before["scenario_source_digest"], after["scenario_source_digest"])
            self.assertNotEqual(before["release_source_digest"], after["release_source_digest"])


if __name__ == "__main__":
    unittest.main()
