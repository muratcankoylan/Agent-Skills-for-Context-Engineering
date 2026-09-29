"""Offline retrieval setup: explicit sources, bounded budgets, no activation.

Only configured credential names can reach the runtime. Provider presence is
not authentication, entitlement, pricing verification or production readiness.
"""

from __future__ import annotations

import json
import os
from pathlib import Path
import re
import secrets
import stat

from .contracts import PAID_SOURCES, RETRIEVAL_SOURCES, ServiceError, load_config

PROVIDER_NAMES = (
    "OPENAI_API_KEY",
    "OPENALEX_API_KEY",
    "X_BEARER_TOKEN",
    "PARALLEL_API_KEY",
    "FIRECRAWL_API_KEY",
    "EXA_API_KEY",
    "BRAVE_API_KEY",
    "TAVILY_API_KEY",
    "JINA_API_KEY",
    "SEMANTIC_SCHOLAR_API_KEY",
    "ANTHROPIC_API_KEY",
    "GEMINI_API_KEY",
    "RESEARCH_GITHUB_TOKEN",
    "RESEARCH_OPERATOR_TOKEN",
)
SOURCE_KEYS = {"x": "X_BEARER_TOKEN", "openalex": "OPENALEX_API_KEY"}
SOURCE_COSTS = {
    "x": "RESEARCH_X_MAX_REQUEST_USD",
    "openalex": "RESEARCH_OPENALEX_MAX_REQUEST_USD",
}
SOURCE_QUERIES = {
    "arxiv": "RESEARCH_ARXIV_QUERY",
    "hacker_news": "RESEARCH_HN_QUERY",
    "x": "RESEARCH_X_QUERY",
    "openalex": "RESEARCH_OPENALEX_QUERY",
}
REQUIRED = (
    "RESEARCH_RETRIEVAL_SOURCES",
    "RESEARCH_RETRIEVAL_QUERY",
    "RESEARCH_RETRIEVAL_DAILY_BUDGET_USD",
    "RESEARCH_RETRIEVAL_RUN_BUDGET_USD",
    "RESEARCH_RETRIEVAL_DAILY_REQUESTS",
    "RESEARCH_RETRIEVAL_RUN_REQUESTS",
)


def _required(values, name):
    value = values.get(name, "")
    if not isinstance(value, str) or not value.strip():
        raise ServiceError("SETUP_VARIABLE_REQUIRED")
    return value


def _present(values, name):
    value = values.get(name)
    return isinstance(value, str) and bool(value.strip())


def _sources(values):
    raw = _required(values, "RESEARCH_RETRIEVAL_SOURCES")
    names = [part.strip() for part in raw.split(",")]
    if (
        not 1 <= len(names) <= len(RETRIEVAL_SOURCES)
        or len(set(names)) != len(names)
        or any(name not in RETRIEVAL_SOURCES for name in names)
    ):
        raise ServiceError("INVALID_SETUP_SOURCES")
    return names


def _usd(values, name, maximum, *, positive=False):
    text = _required(values, name)
    if not re.fullmatch(r"(?:0|[1-9][0-9]{0,3})(?:\.[0-9]{1,6})?", text):
        raise ServiceError("INVALID_SETUP_BUDGET")
    whole, _, fraction = text.partition(".")
    micros = int(whole) * 1_000_000 + int(fraction.ljust(6, "0"))
    if micros > maximum or (positive and micros == 0):
        raise ServiceError("INVALID_SETUP_BUDGET")
    return micros


def _requests(values, name):
    text = _required(values, name)
    if not re.fullmatch(r"[1-9][0-9]{0,3}", text) or int(text) > 1000:
        raise ServiceError("INVALID_SETUP_REQUEST_LIMIT")
    return int(text)


def validate_capacity(config):
    """Conservative cold-cache capacity for every configured daily schedule."""
    if any(s.get("mode", "research") != "retrieve" for s in config["schedules"]):
        raise ServiceError("RETRIEVAL_SETUP_ONLY")
    limits = config["limits"]
    total_requests, total_cost = 0, 0
    for schedule in config["schedules"]:
        count = len(schedule["sources"]) + schedule.get("primary_read_limit", 0)
        cost = sum(
            config.get("source_cost_microusd", {}).get(s, 0)
            for s in schedule["sources"]
        )
        if (
            count > limits.get("run_source_requests", 28)
            or cost > limits["run_budget_microusd"]
        ):
            raise ServiceError("SETUP_RUN_CAPACITY_EXCEEDED")
        total_requests += count
        total_cost += cost
    if (
        total_requests > limits["daily_source_requests"]
        or total_cost > limits["daily_budget_microusd"]
    ):
        raise ServiceError("SETUP_DAILY_CAPACITY_EXCEEDED")


def build_config(values):
    sources = _sources(values)
    primary_limit = values.get("RESEARCH_PRIMARY_READ_LIMIT", "0")
    if not isinstance(primary_limit, str) or primary_limit not in {"0", "1", "2"}:
        raise ServiceError("INVALID_PRIMARY_READ_LIMIT")
    queries = {
        s: _required(values, SOURCE_QUERIES[s]) if s in SOURCE_QUERIES else ""
        for s in sources
    }
    cost = {
        s: _usd(values, SOURCE_COSTS[s], 10_000_000, positive=True)
        for s in sources
        if s in PAID_SOURCES
    }
    config = {
        "schema": "research-service/v1",
        "repository": values.get(
            "RESEARCH_REPOSITORY", "muratcankoylan/Agent-Skills-for-Context-Engineering"
        ),
        "base_branch": "main",
        "models": {},
        "limits": {
            "daily_model_calls": 0,
            "run_model_calls": 0,
            "daily_budget_microusd": _usd(
                values, "RESEARCH_RETRIEVAL_DAILY_BUDGET_USD", 100_000_000
            ),
            "run_budget_microusd": _usd(
                values, "RESEARCH_RETRIEVAL_RUN_BUDGET_USD", 10_000_000
            ),
            "context_bytes": 65536,
            "max_output_tokens": 256,
            "timeout_seconds": 30,
            "max_runs_per_tick": 1,
            "daily_source_requests": _requests(
                values, "RESEARCH_RETRIEVAL_DAILY_REQUESTS"
            ),
            "run_source_requests": _requests(values, "RESEARCH_RETRIEVAL_RUN_REQUESTS"),
        },
        "schedules": [
            {
                "id": "daily-context-observations",
                "mode": "retrieve",
                "interval_seconds": 86400,
                "query": _required(values, "RESEARCH_RETRIEVAL_QUERY"),
                "sources": sources,
                "source_queries": queries,
                "primary_read_limit": int(primary_limit),
            }
        ],
        "github": {
            "enabled": False,
            "credential_env": "RESEARCH_GITHUB_TOKEN",
            "reviewer": "muratcankoylan",
            "notify": False,
        },
        "mcp_tools": [],
        "source_credentials": {s: SOURCE_KEYS[s] for s in sources if s in PAID_SOURCES},
        "source_cost_microusd": cost,
    }
    encoded = json.dumps(config, sort_keys=True)
    # Configuration deliberately transfers only reviewed non-secret fields.
    # Refuse even an accidental paste of a known key into a query/repository field.
    for name in PROVIDER_NAMES:
        secret = values.get(name)
        if secret and (secret in encoded or json.dumps(secret)[1:-1] in encoded):
            raise ServiceError("CREDENTIAL_IN_SETUP_CONFIG")
    checked = load_config(encoded)
    validate_capacity(checked)
    return checked


def configured_credential_names(config, command, token_env="RESEARCH_OPERATOR_TOKEN"):
    if command == "api":
        if not re.fullmatch(r"[A-Z][A-Z0-9_]{0,95}", token_env):
            raise ServiceError("INVALID_TOKEN_ENV")
        return frozenset({token_env})
    if command not in {"work", "serve"}:
        return frozenset()
    names = set()
    research = [
        s for s in config["schedules"] if s.get("mode", "research") == "research"
    ]
    if research:
        names.update(m["credential_env"] for m in config["models"].values())
        if config["github"]["enabled"]:
            names.add(config["github"]["credential_env"])
        reads = {r["id"] for s in research for r in s.get("mcp_reads", [])}
        names.update(
            m["credential_env"]
            for m in config.get("mcp_tools", [])
            if m["registration"]["id"] in reads and m["credential_env"] is not None
        )
    for schedule in config["schedules"]:
        if schedule.get("mode") == "retrieve":
            names.update(
                config["source_credentials"][s]
                for s in schedule["sources"]
                if s in PAID_SOURCES
            )
    return frozenset(names)


def preflight(values, config=None):
    """No network, filesystem, state, or credential-value output."""
    missing, errors, sources = [], [], []
    try:
        if config is None:
            missing = [name for name in REQUIRED if not _present(values, name)]
            sources = _sources(values)
            required = list(REQUIRED) + [
                SOURCE_QUERIES[s] for s in sources if s in SOURCE_QUERIES
            ]
            required += [SOURCE_COSTS[s] for s in sources if s in PAID_SOURCES]
            required += [SOURCE_KEYS[s] for s in sources if s in PAID_SOURCES]
            missing = [name for name in required if not _present(values, name)]
            config = build_config(values)
        else:
            config = load_config(json.dumps(config))
            validate_capacity(config)
            sources = sorted(
                {s for schedule in config["schedules"] for s in schedule["sources"]}
            )
        required_keys = configured_credential_names(config, "work")
        missing += [name for name in required_keys if not _present(values, name)]
        from researcher.scripts.source_search import credential_value

        for schedule in config["schedules"]:
            for source in schedule["sources"]:
                if source not in PAID_SOURCES:
                    continue
                name = config["source_credentials"][source]
                if _present(values, name):
                    try:
                        credential_value(values[name])
                    except ValueError:
                        raise ServiceError("INVALID_SOURCE_CREDENTIAL") from None
    except ServiceError as exc:
        errors.append(exc.code)
    return {
        "schema": "research-retrieval-preflight/v1",
        "local_ready": not missing and not errors,
        "production_ready": False,
        "network_checked": False,
        "source_authentication_verified": False,
        "sources": sources,
        "missing_variables": sorted(set(missing)),
        "error_codes": errors,
        "credentials": {
            name: "set" if values.get(name) else "empty" for name in PROVIDER_NAMES
        },
        "activation": "none",
        "checks": "local_configuration_presence_and_token_syntax",
    }


def write_config(path: Path, config: dict):
    """Publish a complete private config exclusively; never replace an old one.

    Directory-FD traversal prevents symlink redirection. Linking a fully synced
    temporary file gives atomic no-clobber publication, unlike os.replace.
    """
    checked = load_config(json.dumps(config))
    validate_capacity(checked)
    if not path.is_absolute():
        raise ServiceError("UNSAFE_CONFIG_OUTPUT")
    absolute = path
    if ".." in absolute.parts or not absolute.name:
        raise ServiceError("UNSAFE_CONFIG_OUTPUT")
    parent_fd, temporary, created = None, None, False
    try:
        flags = os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW
        parent_fd = os.open(absolute.anchor, flags)
        for part in absolute.parts[1:-1]:
            child = os.open(part, flags, dir_fd=parent_fd)
            os.close(parent_fd)
            parent_fd = child
        info = os.fstat(parent_fd)
        if info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) & 0o022:
            raise ServiceError("UNSAFE_CONFIG_OUTPUT")
        temporary = ".retrieval-config-" + secrets.token_hex(16)
        fd = os.open(
            temporary,
            os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
            0o600,
            dir_fd=parent_fd,
        )
        created = True
        with os.fdopen(fd, "wb") as handle:
            handle.write(
                (json.dumps(checked, sort_keys=True, indent=2) + "\n").encode()
            )
            handle.flush()
            os.fsync(handle.fileno())
        os.link(
            temporary,
            absolute.name,
            src_dir_fd=parent_fd,
            dst_dir_fd=parent_fd,
            follow_symlinks=False,
        )
        os.fsync(parent_fd)
    except FileExistsError:
        raise ServiceError("CONFIG_OUTPUT_EXISTS") from None
    except OSError:
        raise ServiceError("CONFIG_OUTPUT_FAILED") from None
    finally:
        if parent_fd is not None:
            try:
                if created:
                    try:
                        os.unlink(temporary, dir_fd=parent_fd)
                    except FileNotFoundError:
                        pass
            finally:
                os.close(parent_fd)
