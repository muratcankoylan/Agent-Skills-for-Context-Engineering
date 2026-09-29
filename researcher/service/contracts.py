"""Closed configuration and model-output contracts for the data-only service."""

from __future__ import annotations

import re
from typing import Any

from jsonschema import Draft202012Validator

from researcher.scripts.schema_contract import canonicalize, parse_json_strict, sha256_bytes

ROLES = ("researcher", "critic", "skill_editor", "evaluator")
RESEARCH_SOURCES = ("arxiv", "deepmind", "huggingface", "microsoft_research")
RETRIEVAL_SOURCES = (*RESEARCH_SOURCES, "hacker_news", "x", "openalex")
PAID_SOURCES = ("x", "openalex")
SLUG = r"^[a-z][a-z0-9_-]{0,63}$"
ENV = r"^[A-Z][A-Z0-9_]{0,95}$"


class ServiceError(ValueError):
    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


def obj(properties: dict, required: list[str] | None = None) -> dict:
    return {"type": "object", "additionalProperties": False, "properties": properties,
            "required": list(properties) if required is None else required}


def string(maximum: int = 8192, minimum: int = 1, **kwargs) -> dict:
    return {"type": "string", "minLength": minimum, "maxLength": maximum, **kwargs}


def integer(minimum: int, maximum: int) -> dict:
    return {"type": "integer", "minimum": minimum, "maximum": maximum}


def array(items: dict, maximum: int = 32, minimum: int = 0) -> dict:
    return {"type": "array", "items": items, "minItems": minimum, "maxItems": maximum,
            "uniqueItems": True}


MODEL = obj({
    "provider": {"enum": ["openai", "anthropic", "gemini"]},
    "model": string(128), "credential_env": string(96, pattern=ENV),
    # Operator-supplied ceilings, not a bundled claim about current vendor prices.
    "input_microusd_per_million_tokens": integer(1, 1_000_000_000),
    "output_microusd_per_million_tokens": integer(1, 1_000_000_000),
})
SCHEDULE = obj({
    "id": string(64, pattern=SLUG), "interval_seconds": integer(3600, 2_592_000),
    "query": string(2048), "skills": array(string(64, pattern=SLUG), 3),
    "mode": {"enum": ["research", "retrieve"]},
    "primary_read_limit": integer(0, 2),
    "primary_read_profile": {"enum": ["large-paper-html-v1"]},
    "primary_selection_profile": {"enum": ["host-diversity-fill-v1"]},
    "sources": array({"enum": list(RETRIEVAL_SOURCES)}, 7, 1),
    "source_queries": obj({name: string(2048, 0) for name in RETRIEVAL_SOURCES}, []),
    "mcp_reads": array(obj({"id": string(64, pattern=SLUG), "arguments": {"type": "object"}}), 2),
}, ["id", "interval_seconds", "query", "sources"])
CONFIG_SCHEMA = obj({
    "schema": {"const": "research-service/v1"},
    "repository": string(200, pattern=r"^[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+$"),
    "base_branch": string(120, pattern=r"^[A-Za-z0-9][A-Za-z0-9_/-]*$"),
    "models": {"anyOf": [obj({role: MODEL for role in ROLES}), obj({})]},
    "limits": obj({
        "daily_model_calls": integer(0, 1000), "run_model_calls": integer(0, 20),
        "daily_budget_microusd": integer(0, 100_000_000),
        "run_budget_microusd": integer(0, 10_000_000),
        "context_bytes": integer(16384, 131072),
        "max_output_tokens": integer(256, 16384),
        "timeout_seconds": integer(5, 120),
        "max_runs_per_tick": integer(1, 4),
        "daily_source_requests": integer(1, 1000),
        "run_source_requests": integer(1, 1000),
    }, ["daily_model_calls", "run_model_calls", "daily_budget_microusd", "run_budget_microusd",
        "context_bytes", "max_output_tokens", "timeout_seconds", "max_runs_per_tick", "daily_source_requests"]),
    "schedules": array(SCHEDULE, 10, 1),
    "github": obj({"enabled": {"type": "boolean"},
                   "credential_env": string(96, pattern=ENV),
                   "reviewer": string(39, pattern=r"^[A-Za-z0-9][A-Za-z0-9-]{0,38}$"),
                   "notify": {"type": "boolean"}}),
    "mcp_tools": array(obj({"registration": {"type": "object"},
                             "credential_env": {"anyOf": [string(96, pattern=ENV), {"type": "null"}]},
                             "max_cost_microusd": integer(0, 10_000_000)}), 2),
    "source_credentials": obj({name: string(96, pattern=ENV) for name in PAID_SOURCES}, []),
    "source_cost_microusd": obj({name: integer(1, 10_000_000) for name in PAID_SOURCES}, []),
}, ["schema", "repository", "base_branch", "models", "limits", "schedules", "github"])

CITATION = obj({"evidence_id": string(160), "quote": string(1200)})
RESEARCH_SCHEMA = obj({
    "hypothesis": string(3000), "test_plan": string(3000), "abstain": {"type": "boolean"},
    "claims": array(obj({"id": string(64, pattern=SLUG), "statement": string(2000),
                         "citations": array(CITATION, 6, 1),
                         "limitations": array(string(1000), 8)}), 8),
})
CRITIC_SCHEMA = obj({
    "supported_claim_ids": array(string(64, pattern=SLUG), 8),
    "issues": array(string(1500), 8), "recommendation": {"enum": ["propose", "abstain"]},
})
EDIT_SCHEMA = obj({
    "path": string(200, pattern=r"^skills/[a-z][a-z0-9_-]*/SKILL\.md$"),
    "old_text": string(8000), "new_text": string(12000),
    "claim_ids": array(string(64, pattern=SLUG), 8, 1), "rationale": string(2000),
})
EVALUATION_SCHEMA = obj({
    "preference": {"enum": ["A", "B", "tie", "reject"]},
    "critical_regression": {"type": "boolean"}, "reason": string(3000),
})
OUTPUT_SCHEMAS = {"researcher": RESEARCH_SCHEMA, "critic": CRITIC_SCHEMA,
                  "skill_editor": EDIT_SCHEMA, "evaluator": EVALUATION_SCHEMA}


def validate(value: Any, schema: dict, code: str = "INVALID_RECORD") -> Any:
    try:
        canonicalize(value)  # Reject floats, booleans as integers, unsafe Unicode/integers.
        errors = list(Draft202012Validator(schema).iter_errors(value))
        if errors:
            raise ServiceError(code)
    except (TypeError, ValueError, RecursionError):
        raise ServiceError(code) from None
    return value


def load_config(text: str) -> dict:
    try:
        value = parse_json_strict(text)
        validate(value, CONFIG_SCHEMA, "INVALID_CONFIG")
        if len({s["id"] for s in value["schedules"]}) != len(value["schedules"]):
            raise ServiceError("DUPLICATE_SCHEDULE")
        research = [s for s in value["schedules"] if s.get("mode", "research") == "research"]
        if research and (set(value["models"]) != set(ROLES)
                         or value["limits"]["daily_model_calls"] < 1
                         or value["limits"]["run_model_calls"] < 5
                         or value["limits"]["daily_budget_microusd"] < 1
                         or value["limits"]["run_budget_microusd"] < 1):
            raise ServiceError("RESEARCH_MODEL_BUDGET_REQUIRED")
        for schedule in value["schedules"]:
            if schedule.get("mode", "research") == "research":
                if (not schedule.get("skills") or not set(schedule["sources"]) <= set(RESEARCH_SOURCES)
                        or "source_queries" in schedule or "primary_read_limit" in schedule
                        or "primary_read_profile" in schedule or "primary_selection_profile" in schedule):
                    raise ServiceError("INVALID_RESEARCH_SCHEDULE")
                continue
            if schedule["interval_seconds"] != 86400 or schedule.get("mcp_reads"):
                raise ServiceError("INVALID_RETRIEVAL_SCHEDULE")
            if ("primary_read_profile" in schedule or "primary_selection_profile" in schedule) and not schedule.get("primary_read_limit", 0):
                raise ServiceError("PRIMARY_PROFILE_REQUIRES_READ_LIMIT")
            queries = schedule.get("source_queries", {})
            if set(queries) != set(schedule["sources"]):
                raise ServiceError("EXPLICIT_SOURCE_QUERIES_REQUIRED")
            for source in schedule["sources"]:
                if source in {"arxiv", "x", "openalex", "hacker_news"} and not queries[source].strip():
                    raise ServiceError("SOURCE_QUERY_REQUIRED")
                if source in PAID_SOURCES and (
                    source not in value.get("source_credentials", {})
                    or source not in value.get("source_cost_microusd", {})
                    or value["source_cost_microusd"][source] > value["limits"]["run_budget_microusd"]
                ):
                    raise ServiceError("PAID_SOURCE_POLICY_REQUIRED")
        for model in value["models"].values():
            if ("latest" in model["model"].lower() or "REPLACE" in model["model"]
                    or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,127}", model["model"])):
                raise ServiceError("PIN_EXPLICIT_MODEL")
        if ".." in value["base_branch"] or "//" in value["base_branch"]:
            raise ServiceError("INVALID_BASE_BRANCH")
        tools = value.get("mcp_tools", [])
        registered = {}
        if tools or any(s.get("mcp_reads") for s in value["schedules"]):
            from .mcp_evidence import validate_read, validate_registration
            for item in tools:
                registration = item["registration"]
                validate_registration(registration)
                identity = registration.get("id", "")
                if (not isinstance(identity, str) or not re.fullmatch(SLUG, identity)
                        or identity in registered):
                    raise ServiceError("INVALID_MCP_REGISTRATION_ID")
                registered[identity] = item
                if item["max_cost_microusd"] > value["limits"]["run_budget_microusd"]:
                    raise ServiceError("MCP_COST_EXCEEDS_RUN_BUDGET")
            for schedule in value["schedules"]:
                seen = set()
                maximum_output = 0
                for read in schedule.get("mcp_reads", []):
                    if read["id"] not in registered or read["id"] in seen:
                        raise ServiceError("UNREGISTERED_OR_DUPLICATE_MCP_READ")
                    seen.add(read["id"])
                    validate_read(registered[read["id"]]["registration"], read["arguments"])
                    maximum_output += registered[read["id"]]["registration"]["max_output_bytes"]
                # Reserve half the evidence packet for fixed source lanes and
                # provenance. Actual aggregate size is still checked after read.
                if maximum_output > 32768:
                    raise ServiceError("MCP_CONTEXT_CEILING_EXCEEDED")
        return value
    except ServiceError:
        raise
    except (ValueError, TypeError, RecursionError):
        raise ServiceError("INVALID_CONFIG") from None


def digest(value: Any) -> str:
    return sha256_bytes(canonicalize(value))


def parse_output(text: str, role: str) -> dict:
    try:
        if len(text.encode("utf-8")) > 65536:
            raise ServiceError("MODEL_OUTPUT_LIMIT")
        return validate(parse_json_strict(text), OUTPUT_SCHEMAS[role], "INVALID_MODEL_OUTPUT")
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ServiceError("INVALID_MODEL_OUTPUT") from None


def model_reservation(config: dict, role: str, request_bytes: int) -> tuple[int, int]:
    # UTF-8 bytes conservatively bound ordinary byte-tokenized input. The framing
    # allowance is explicit; exceeding it is an accounting incident, not free work.
    tokens = request_bytes + 4096
    model, limits = config["models"][role], config["limits"]
    micros = ((tokens * model["input_microusd_per_million_tokens"]
               + limits["max_output_tokens"] * model["output_microusd_per_million_tokens"]
               + 999999) // 1_000_000)
    return tokens, micros
