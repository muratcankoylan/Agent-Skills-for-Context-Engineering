"""Offline setup/preflight: configuration readiness is not provider validation."""

from copy import deepcopy
import json
import unittest
from unittest.mock import patch

from researcher.service.contracts import ServiceError, load_config
from researcher.service.demo import demo_config
from researcher.service.retrieval_setup import (
    build_config, configured_credential_names, preflight, validate_capacity,
)


def values(**changes):
    result = {
        "RESEARCH_RETRIEVAL_SOURCES": "hacker_news,huggingface",
        "RESEARCH_RETRIEVAL_QUERY": "Evidence provenance in agent retrieval",
        "RESEARCH_HN_QUERY": "agent retrieval",
        "RESEARCH_RETRIEVAL_DAILY_BUDGET_USD": "0",
        "RESEARCH_RETRIEVAL_RUN_BUDGET_USD": "0",
        "RESEARCH_RETRIEVAL_DAILY_REQUESTS": "20",
        "RESEARCH_RETRIEVAL_RUN_REQUESTS": "7",
    }
    result.update(changes)
    return result


def paid_values(**changes):
    return values(**{
        "RESEARCH_RETRIEVAL_SOURCES": "x,openalex",
        "RESEARCH_X_QUERY": "agent memory -is:retweet",
        "RESEARCH_OPENALEX_QUERY": "episodic agent memory",
        "RESEARCH_RETRIEVAL_DAILY_BUDGET_USD": "1",
        "RESEARCH_RETRIEVAL_RUN_BUDGET_USD": "0.1",
        "RESEARCH_X_MAX_REQUEST_USD": "0.01",
        "RESEARCH_OPENALEX_MAX_REQUEST_USD": "0.001",
        **changes,
    })


class RetrievalSetupTests(unittest.TestCase):
    def test_free_configuration_needs_no_models_secrets_or_spending(self):
        settings = values()
        original = deepcopy(settings)
        config = build_config(settings)
        self.assertEqual(settings, original)
        self.assertEqual(load_config(json.dumps(config)), config)
        self.assertEqual(config["models"], {})
        self.assertEqual(config["source_credentials"], {})
        self.assertEqual(config["source_cost_microusd"], {})
        self.assertFalse(config["github"]["enabled"])
        self.assertFalse(config["github"]["notify"])
        self.assertEqual(config.get("mcp_tools", []), [])
        for field in ("daily_model_calls", "run_model_calls", "daily_budget_microusd", "run_budget_microusd"):
            self.assertEqual(config["limits"][field], 0)
        schedule = config["schedules"][0]
        self.assertEqual(schedule["mode"], "retrieve")
        self.assertEqual(schedule["interval_seconds"], 86400)
        self.assertEqual(schedule["sources"], ["hacker_news", "huggingface"])
        self.assertEqual(schedule["source_queries"], {"hacker_news": "agent retrieval", "huggingface": ""})

    def test_sources_and_capacity_flags_are_explicit_not_ambient_defaults(self):
        required = ("RESEARCH_RETRIEVAL_SOURCES", "RESEARCH_RETRIEVAL_QUERY",
                    "RESEARCH_RETRIEVAL_DAILY_BUDGET_USD", "RESEARCH_RETRIEVAL_RUN_BUDGET_USD",
                    "RESEARCH_RETRIEVAL_DAILY_REQUESTS", "RESEARCH_RETRIEVAL_RUN_REQUESTS")
        for key in required:
            settings = values()
            settings.pop(key)
            with self.subTest(key=key), self.assertRaises(ServiceError):
                build_config(settings)
            report = preflight(settings)
            self.assertFalse(report["local_ready"])
            self.assertIn(key, report["missing_variables"])

    def test_duplicate_unsupported_empty_and_nontext_sources_rejected(self):
        for sources in ("", "hacker_news,hacker_news", "hacker_news,brave", "x,", ",hacker_news",
                        "hacker_news,,arxiv", ["hacker_news"], True):
            with self.subTest(sources=sources), self.assertRaises(ServiceError):
                build_config(values(RESEARCH_RETRIEVAL_SOURCES=sources))
            with self.subTest(preflight_sources=sources):
                report = preflight(values(RESEARCH_RETRIEVAL_SOURCES=sources))
                self.assertFalse(report["local_ready"])
                self.assertTrue(report["error_codes"])

    def test_operator_queries_are_preserved_and_not_heuristically_rewritten(self):
        query = '("agent memory" OR episodic) -is:retweet lang:en'
        config = build_config(paid_values(RESEARCH_X_QUERY=query))
        self.assertEqual(config["schedules"][0]["source_queries"]["x"], query)
        config = build_config(values(RESEARCH_RETRIEVAL_SOURCES="arxiv", RESEARCH_ARXIV_QUERY="memory consolidation"))
        self.assertEqual(config["schedules"][0]["source_queries"], {"arxiv": "memory consolidation"})

    def test_selected_search_sources_require_their_own_query(self):
        for source, variable in (("hacker_news", "RESEARCH_HN_QUERY"), ("arxiv", "RESEARCH_ARXIV_QUERY"),
                                 ("x", "RESEARCH_X_QUERY"), ("openalex", "RESEARCH_OPENALEX_QUERY")):
            settings = paid_values(RESEARCH_RETRIEVAL_SOURCES=source)
            settings.pop(variable, None)
            with self.subTest(source=source), self.assertRaises(ServiceError):
                build_config(settings)
            report = preflight(settings)
            self.assertFalse(report["local_ready"])
            self.assertIn(variable, report["missing_variables"])

    def test_money_converts_exactly_to_integer_microdollars(self):
        config = build_config(paid_values(RESEARCH_X_MAX_REQUEST_USD="0.000001",
                                         RESEARCH_OPENALEX_MAX_REQUEST_USD="0.000002",
                                         RESEARCH_RETRIEVAL_RUN_BUDGET_USD="0.000003",
                                         RESEARCH_RETRIEVAL_DAILY_BUDGET_USD="0.000003"))
        self.assertEqual(config["source_cost_microusd"], {"x": 1, "openalex": 2})
        self.assertEqual(config["limits"]["run_budget_microusd"], 3)
        self.assertEqual(config["limits"]["daily_budget_microusd"], 3)
        self.assertEqual(type(config["limits"]["run_budget_microusd"]), int)

    def test_money_rejects_float_exponent_expression_and_precision_injection(self):
        for value in (0.1, True, "1e-3", "NaN", "Infinity", "-1", "0.0000001", "1+1", "$(echo 1)"):
            with self.subTest(value=value), self.assertRaises(ServiceError):
                build_config(values(RESEARCH_RETRIEVAL_DAILY_BUDGET_USD=value))
        for key, value in (("RESEARCH_RETRIEVAL_DAILY_BUDGET_USD", "100.000001"),
                           ("RESEARCH_RETRIEVAL_RUN_BUDGET_USD", "10.000001")):
            with self.subTest(key=key), self.assertRaises(ServiceError):
                build_config(values(**{key: value}))
        config = build_config(values(RESEARCH_RETRIEVAL_DAILY_BUDGET_USD="100",
                                     RESEARCH_RETRIEVAL_RUN_BUDGET_USD="10"))
        self.assertEqual(config["limits"]["daily_budget_microusd"], 100_000_000)
        self.assertEqual(config["limits"]["run_budget_microusd"], 10_000_000)

    def test_paid_request_ceiling_required_positive_and_integer_backed(self):
        for variable in ("RESEARCH_X_MAX_REQUEST_USD", "RESEARCH_OPENALEX_MAX_REQUEST_USD"):
            for invalid in (None, "", "0", "-0.01", "1e-2", "0.0000001"):
                settings = paid_values()
                if invalid is None:
                    settings.pop(variable)
                else:
                    settings[variable] = invalid
                with self.subTest(variable=variable, invalid=invalid), self.assertRaises(ServiceError):
                    build_config(settings)

    def test_request_limits_reject_bool_float_zero_or_exponents(self):
        for key in ("RESEARCH_RETRIEVAL_DAILY_REQUESTS", "RESEARCH_RETRIEVAL_RUN_REQUESTS"):
            for invalid in (True, 3.5, "0", "1.0", "1e2", "1001", "-1"):
                with self.subTest(key=key, invalid=invalid), self.assertRaises(ServiceError):
                    build_config(values(**{key: invalid}))

    def test_aggregate_paid_cost_must_fit_run_and_daily_caps(self):
        for changes in ({"RESEARCH_RETRIEVAL_RUN_BUDGET_USD": "0.01"},
                        {"RESEARCH_RETRIEVAL_DAILY_BUDGET_USD": "0.01"}):
            with self.subTest(changes=changes), self.assertRaises(ServiceError):
                build_config(paid_values(**changes))  # 0.01 + 0.001, not each independently.

    def test_aggregate_request_demand_must_fit_run_and_daily_caps(self):
        for key in ("RESEARCH_RETRIEVAL_DAILY_REQUESTS", "RESEARCH_RETRIEVAL_RUN_REQUESTS"):
            with self.subTest(key=key), self.assertRaises(ServiceError):
                build_config(values(**{key: "1"}))  # Two one-page sources.

    def test_capacity_counts_all_daily_schedules_without_assuming_cache_hits(self):
        config = build_config(paid_values(RESEARCH_RETRIEVAL_SOURCES="x",
                                         RESEARCH_RETRIEVAL_DAILY_BUDGET_USD="0.01"))
        repeated = deepcopy(config["schedules"][0])
        repeated["id"] += "-second"
        config["schedules"].append(repeated)
        with self.assertRaises(ServiceError):
            validate_capacity(config)
        config["limits"]["daily_budget_microusd"] = 20_000
        validate_capacity(config)
        config["limits"]["daily_source_requests"] = 1
        with self.assertRaises(ServiceError):
            validate_capacity(config)

    def test_build_can_stage_paid_configuration_but_preflight_requires_credentials(self):
        settings = paid_values()
        config = build_config(settings)
        self.assertEqual(config["source_credentials"], {"x": "X_BEARER_TOKEN", "openalex": "OPENALEX_API_KEY"})
        report = preflight(settings, config=config)
        self.assertFalse(report["local_ready"])
        self.assertIn("X_BEARER_TOKEN", report["missing_variables"])
        self.assertIn("OPENALEX_API_KEY", report["missing_variables"])
        self.assertEqual(report["credentials"]["X_BEARER_TOKEN"], "empty")
        self.assertEqual(report["credentials"]["OPENALEX_API_KEY"], "empty")

    def test_ready_preflight_is_local_only_and_never_emits_credentials(self):
        secret_x, secret_openalex = "fixture-x-secret-never-live", "fixture-openalex-secret-never-live"
        settings = paid_values(X_BEARER_TOKEN=secret_x, OPENALEX_API_KEY=secret_openalex)
        config = build_config(settings)
        report = preflight(settings, config=config)
        self.assertTrue(report["local_ready"])
        self.assertFalse(report["network_checked"])
        self.assertFalse(report["production_ready"])
        self.assertEqual(report["error_codes"], [])
        self.assertEqual(report["missing_variables"], [])
        self.assertTrue(all(value in {"set", "empty"} for value in report["credentials"].values()))
        encoded = json.dumps({"config": config, "report": report})
        for secret in (secret_x, secret_openalex):
            self.assertNotIn(secret, encoded)

    def test_selected_paid_credentials_fail_local_syntax_check(self):
        for invalid in ("short", "bad token"):
            for supplied_config in (False, True):
                settings = paid_values(X_BEARER_TOKEN=invalid,
                                       OPENALEX_API_KEY="synthetic-openalex-credential")
                config = build_config(settings) if supplied_config else None
                with self.subTest(invalid=invalid, supplied_config=supplied_config):
                    report = preflight(settings, config=config)
                    self.assertFalse(report["local_ready"])
                    self.assertIn("INVALID_SOURCE_CREDENTIAL", report["error_codes"])
                    self.assertNotIn(invalid, json.dumps(report))

    def test_custom_paid_credential_alias_gets_same_syntax_check(self):
        config = build_config(paid_values(RESEARCH_RETRIEVAL_SOURCES="x"))
        config["source_credentials"]["x"] = "CUSTOM_X_TOKEN"
        for invalid in ("short", "bad token"):
            settings = {"CUSTOM_X_TOKEN": invalid, "X_BEARER_TOKEN": "valid-but-unused-synthetic-token"}
            with self.subTest(invalid=invalid):
                report = preflight(settings, config=config)
                self.assertFalse(report["local_ready"])
                self.assertIn("INVALID_SOURCE_CREDENTIAL", report["error_codes"])
                self.assertNotIn(invalid, json.dumps(report))
        report = preflight({"CUSTOM_X_TOKEN": "valid-synthetic-custom-token"}, config=config)
        self.assertTrue(report["local_ready"])

    def test_inactive_malformed_optional_credentials_do_not_block_free_profile(self):
        settings = values(X_BEARER_TOKEN="short", OPENALEX_API_KEY="bad token")
        for config in (None, build_config(settings)):
            report = preflight(settings, config=config)
            self.assertTrue(report["local_ready"])
            self.assertEqual(report["error_codes"], [])
            self.assertEqual(report["credentials"]["X_BEARER_TOKEN"], "set")
            self.assertEqual(report["credentials"]["OPENALEX_API_KEY"], "set")

    def test_inactive_credentials_are_status_only_and_do_not_enable_providers(self):
        settings = values(X_BEARER_TOKEN="inactive-x-secret", OPENALEX_API_KEY="inactive-openalex-secret",
                          OPENAI_API_KEY="inactive-openai-secret", PARALLEL_API_KEY="inactive-parallel-secret")
        config = build_config(settings)
        report = preflight(settings, config=config)
        self.assertTrue(report["local_ready"])
        self.assertEqual(config["schedules"][0]["sources"], ["hacker_news", "huggingface"])
        self.assertEqual(configured_credential_names(config, "work"), frozenset())
        self.assertEqual(report["credentials"]["X_BEARER_TOKEN"], "set")
        self.assertEqual(report["credentials"]["OPENALEX_API_KEY"], "set")
        for secret in ("inactive-x-secret", "inactive-openalex-secret", "inactive-openai-secret", "inactive-parallel-secret"):
            self.assertNotIn(secret, json.dumps(report))

    def test_control_commands_do_not_resolve_provider_credentials(self):
        config = build_config(paid_values())
        for command in ("init", "status", "inspect", "pause", "resume", "enqueue", "tick", "backup", "configure", "preflight"):
            self.assertEqual(configured_credential_names(config, command), frozenset(), command)
        expected = frozenset({"X_BEARER_TOKEN", "OPENALEX_API_KEY"})
        self.assertEqual(configured_credential_names(config, "work"), expected)
        self.assertEqual(configured_credential_names(config, "serve"), expected)
        self.assertEqual(configured_credential_names(config, "api"), frozenset({"RESEARCH_OPERATOR_TOKEN"}))
        self.assertEqual(configured_credential_names(config, "api", token_env="CUSTOM_OPERATOR_TOKEN"),
                         frozenset({"CUSTOM_OPERATOR_TOKEN"}))

    def test_native_research_credentials_only_when_research_is_scheduled(self):
        config = demo_config()
        names = set()
        for role, model in config["models"].items():
            model["credential_env"] = "FIXTURE_" + role.upper()
            names.add(model["credential_env"])
        self.assertEqual(configured_credential_names(config, "work"), frozenset(names))
        config["github"]["enabled"] = True
        self.assertEqual(configured_credential_names(config, "serve"), frozenset(names | {"RESEARCH_GITHUB_TOKEN"}))

    def test_unused_registered_credential_alias_does_not_get_resolved(self):
        config = build_config(values())
        config["source_credentials"] = {"x": "UNUSED_X_TOKEN", "openalex": "UNUSED_OPENALEX_TOKEN"}
        self.assertEqual(configured_credential_names(config, "work"), frozenset())

    def test_pure_setup_does_not_read_ambient_environment_network_or_subprocess(self):
        class NoAmbient(dict):
            def get(self, *args, **kwargs):
                raise AssertionError("ambient environment read")
            def __getitem__(self, key):
                raise AssertionError("ambient environment read")
            def __iter__(self):
                raise AssertionError("ambient environment read")
        with patch("os.environ", NoAmbient()), \
             patch("socket.socket.connect", side_effect=AssertionError("network")), \
             patch("subprocess.run", side_effect=AssertionError("subprocess")):
            config = build_config(values())
            self.assertTrue(preflight(values(), config=config)["local_ready"])

    def test_preflight_errors_do_not_echo_malformed_values(self):
        secret = "synthetic-private-marker-do-not-echo"
        report = preflight(values(RESEARCH_RETRIEVAL_DAILY_BUDGET_USD=secret, OPENAI_API_KEY=secret))
        self.assertFalse(report["local_ready"])
        self.assertTrue(report["error_codes"])
        self.assertNotIn(secret, json.dumps(report))


if __name__ == "__main__":
    unittest.main()
