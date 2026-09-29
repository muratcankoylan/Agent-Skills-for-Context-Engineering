"""Explicit read-only connector checks with durable, non-repeating effects.

This is an operator diagnostic, not a scheduler or a research-quality benchmark.
One state directory owns one fixed campaign. Reusing it replays prior receipts;
an interrupted request is never retried, even when the key has changed.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import time

from researcher.scripts.schema_contract import canonicalize, parse_json_strict, sha256_bytes
from researcher.scripts.source_connectors import ConnectorError
from researcher.scripts.source_search import credential_value
from . import retrieval_sources
from .contracts import ServiceError, digest
from .environment import read_env_file
from .retrieval_setup import PROVIDER_NAMES
from .store import Store

SOURCE_PROBES = {
    "x": ("X_BEARER_TOKEN", 50_000, '"context engineering" -is:retweet lang:en'),
    "openalex": ("OPENALEX_API_KEY", 1_000, "agent memory retrieval"),
}


def implementation_digest():
    # Bind the repository modules implementing the diagnostic execution boundary.
    root = Path(__file__).resolve().parents[1]
    paths = [root / "service" / (name + ".py") for name in (
        "connector_campaign", "connector_checks", "connector_mcp", "mcp_tools", "mcp_worker", "mcp_evidence",
        "retrieval_sources", "store", "environment",
        "contracts", "retrieval_setup")]
    paths += [root / "scripts" / (name + ".py") for name in (
        "source_connectors", "source_search", "research_evidence", "schema_contract", "artifact_store")]
    paths.append(root / "service" / "registrations" / "parallel-web-fetch.json")
    return digest({str(p.relative_to(root)): sha256_bytes(p.read_bytes()) for p in paths})


def definitions():
    from .connector_checks import PROBES
    from .connector_mcp import ARGUMENTS, ENDPOINT, REQUEST_CEILING, RESERVE_MICRO_USD, TOOL, parallel_registration
    from .mcp_evidence import MAX_REQUESTS

    result = {}
    for name, probe in PROBES.items():
        row = asdict(probe)
        body = row.pop("payload")
        row["payload_sha256"] = sha256_bytes(body or b"")
        row["request_ceiling"] = 1
        result[name] = row
    for name, (key, micros, query) in SOURCE_PROBES.items():
        result[name] = {"name": name, "credential_env": key,
                        "reserve_micro_usd": micros, "query": query, "request_ceiling": 1,
                        "limits": asdict(retrieval_sources.source_limits(name))}
    result["parallel_mcp_fetch"] = {"name": "parallel_mcp_fetch", "credential_env": "PARALLEL_API_KEY",
        "reserve_micro_usd": RESERVE_MICRO_USD, "request_ceiling": REQUEST_CEILING,
        "endpoint": ENDPOINT, "tool": TOOL, "arguments": ARGUMENTS}
    result["parallel_registered_fetch"] = {"name": "parallel_registered_fetch", "credential_env": "PARALLEL_API_KEY",
        "reserve_micro_usd": RESERVE_MICRO_USD, "request_ceiling": MAX_REQUESTS,
        "registration": parallel_registration(), "arguments": ARGUMENTS}
    return result


def source_probe(name, credential, directory, *, end_time):
    """Exercise the production adapter, capture, and offline replay together."""
    _, _, query = SOURCE_PROBES[name]
    start = end_time - (86400 if name == "x" else 30 * 86400)
    result = {"schema": "connector-check/v1", "name": name,
              "classification": "transport_unknown", "http_status": None, "counts": {}}
    try:
        lane = retrieval_sources.collect(name, query, directory,
            start_time=start, end_time=end_time, credential=credential)
        retrieval_sources.verify(name, query, lane, directory, start_time=start, end_time=end_time)
        observations = lane["receipt"]["observations"]
        result["http_status"] = observations[-1]["status_code"] if observations else None
        result["classification"] = "rate_limited" if lane["state"] == "rate_limited" else "success"
        result["counts"] = {"items": len(lane["evidence"]),
                            "abstracts": sum(dict(x["metadata"]).get("summary_kind") == "openalex_abstract"
                                             for x in lane["evidence"]),
                            "offline_replays": 1}
        if name == "x":
            from researcher.scripts.research_evidence import LocalResearchEvidenceStore
            evidence = LocalResearchEvidenceStore(directory, read_only=True)
            rows = []
            # The replay above establishes correspondence to this exact capture.
            # Presence counts describe returned wire fields, not semantic quality.
            for capture in lane["captures"]:
                body = parse_json_strict(evidence.read_body(capture).decode("utf-8"))
                items = body.get("data", []) if isinstance(body, dict) else None
                if not isinstance(items, list) or any(not isinstance(item, dict) for item in items):
                    raise ServiceError("SOURCE_CAPTURE_INVALID")
                rows.extend(items)
            result["counts"]["x_posts"] = len(rows)
            for field in ("created_at", "public_metrics", "conversation_id", "author_id", "lang",
                          "entities", "note_tweet", "referenced_tweets"):
                result["counts"]["x_with_" + field] = sum(item.get(field) is not None for item in rows)
        # Captures stay private. A diagnostic receipt is not a research packet.
        return result
    except ConnectorError as error:
        observations = error.receipt.observations if error.receipt else ()
        status = observations[-1].status_code if observations else None
        result["http_status"] = status
        result["classification"] = {401: "auth_rejected", 402: "billing_blocked",
            403: "permission_denied", 429: "rate_limited", 404: "endpoint_unavailable"}.get(
                status, "schema_invalid" if status == 200 else "transport_unknown")
        return result
    except (ServiceError, ValueError):
        result["classification"] = "schema_invalid"
        return result


def _credentials(selected, values):
    keys = {}
    for name, row in selected.items():
        value = values.get(row["credential_env"])
        if value:
            try:
                credential_value(value)
            except ValueError:
                raise ServiceError("INVALID_SOURCE_CREDENTIAL") from None
            keys[name] = value
    return keys


def run_campaign(directory, values, *, names, max_budget_microusd, live=False,
                 concurrency=1, probe=None, source=None, mcp=None, registered_mcp=None, now=None, progress=None):
    """Reservations are conservative estimates, not provider invoice amounts.

    USD and request caps are fixed across all resumes. Unknown requests retain
    reservations. Concurrency is deliberately one for this small diagnostic.
    """
    from .connector_checks import PROBES, probe_request

    available = definitions()
    if (not isinstance(names, (tuple, list)) or not names or len(set(names)) != len(names)
            or any(name not in available for name in names)):
        raise ServiceError("INVALID_CONNECTOR_SELECTION")
    if type(concurrency) is not int or concurrency != 1:
        raise ServiceError("DIAGNOSTIC_CONCURRENCY_MUST_BE_ONE")
    if type(max_budget_microusd) is not int or not 0 <= max_budget_microusd <= 1_000_000:
        raise ServiceError("INVALID_DIAGNOSTIC_BUDGET")
    if sum(available[n]["reserve_micro_usd"] for n in names) > max_budget_microusd:
        raise ServiceError("DIAGNOSTIC_BUDGET_TOO_SMALL")
    request_ceiling = sum(available[n]["request_ceiling"] for n in names)
    if request_ceiling > 20:
        raise ServiceError("DIAGNOSTIC_REQUEST_LIMIT")
    selected = {n: available[n] for n in sorted(names)}
    config = {"schema": "connector-campaign/v1", "definitions": selected,
        "implementation_sha256": implementation_digest(),
        "limits": {"daily_model_calls": 0, "run_model_calls": 0,
                   "daily_budget_microusd": max_budget_microusd,
                   "run_budget_microusd": max_budget_microusd,
                   "daily_source_requests": request_ceiling, "run_source_requests": request_ceiling}}
    if not live:
        return {"schema": "connector-campaign-plan/v1", "network_checked": False,
                "request_ceiling": request_ceiling, "reserved_microusd_ceiling": sum(
                    row["reserve_micro_usd"] for row in selected.values()), "checks": sorted(names)}
    current = int(time.time()) if now is None else now
    if type(current) is not int or current < 31 * 86400:
        raise ServiceError("INVALID_CLOCK")
    # New campaigns reject malformed credentials without creating state. An
    # existing campaign is opened without repair and can replay its completed
    # receipt without resolving or validating today's credential values.
    initialize = not directory.exists()
    keys = _credentials(selected, values) if initialize else None
    store = Store(directory, config, initialize=initialize)
    probe = probe or probe_request
    source = source or source_probe
    if mcp is None:
        from .connector_mcp import parallel_mcp_probe
        mcp = parallel_mcp_probe
    if registered_mcp is None:
        from .connector_mcp import registered_parallel_probe
        registered_mcp = registered_parallel_probe
    progress = progress or (lambda value: None)
    job_id = "connector-checks"
    with store.worker_lock():
        store.recover()
        store.enqueue(job_id, config)
        old = store.checkpoint(job_id, "window", config)
        if old is None:
            old = store.checkpoint(job_id, "window", config, {"end_time": current - 60})
        manifest = {"config": digest(config), "end_time": old["end_time"]}
        report = store.checkpoint(job_id, "report", manifest)
        if report is not None:
            state = store.inspect(job_id)
            if any(effect["state"] != "completed" for effect in state["effects"]):
                raise ServiceError("DIAGNOSTIC_RECONCILIATION_REQUIRED")
            if state["job"]["status"] in {"queued", "running"}:
                # Report persistence and terminal status are separate commits.
                # Finalize their crash window without replaying provider work.
                store.finish(job_id, "retrieval_complete")
            elif state["job"]["status"] != "retrieval_complete":
                raise ServiceError("DIAGNOSTIC_RECONCILIATION_REQUIRED")
            return {**report, "replayed": True}
        if keys is None:
            keys = _credentials(selected, values)
        job = store.next_job()
        if job is None:
            raise ServiceError("DIAGNOSTIC_RECONCILIATION_REQUIRED")
        results = []
        for name, row in selected.items():
            inputs = {**manifest, "probe": row}
            cached = store.completed_effect(job_id, name, inputs)
            if cached is not None:
                results.append(cached)
                continue
            if name not in keys:
                results.append({"schema": "connector-check/v1", "name": name,
                                "classification": "not_configured", "http_status": None, "counts": {}})
                continue
            store.reserve(job_id, name, inputs, source_requests=row["request_ceiling"],
                          micros=row["reserve_micro_usd"])
            progress({"event": "connector_check_started", "name": name})
            try:
                if name in SOURCE_PROBES:
                    result = source(name, keys[name], directory / "captures" / name, end_time=old["end_time"])
                elif name == "parallel_mcp_fetch":
                    result = mcp(keys[name])
                elif name == "parallel_registered_fetch":
                    result = registered_mcp(keys[name])
                else:
                    result = probe(PROBES[name], keys[name])
                # Trusted adapters expose closed diagnostics, never source text.
                encoded = canonicalize(result)
                if any(value.encode() in encoded or json.dumps(value)[1:-1].encode() in encoded
                       for value in keys.values()):
                    raise ServiceError("CREDENTIAL_REFLECTED")
                store.complete_effect(job_id, name, result)
            except BaseException:
                store.fail_effect(job_id, name, "DIAGNOSTIC_OUTCOME_UNKNOWN")
                raise ServiceError("DIAGNOSTIC_RECONCILIATION_REQUIRED") from None
            results.append(result)
            progress({"event": "connector_check_finished", "name": name,
                      "classification": result["classification"]})
        report = {"schema": "connector-campaign-report/v1", "production_ready": False,
            "network_checked": any(row["classification"] != "not_configured" for row in results),
            "replayed": False, "results": results,
            "checked_at": current, "manifest_sha256": digest(manifest),
            "actual_charge_known": False, "recurring_activation": "none",
            "unconfigured_variables": sorted(n for n in PROVIDER_NAMES if not values.get(n)),
            "usage": store.status()["usage"]}
        store.checkpoint(job_id, "report", manifest, report)
        store.finish(job_id, "retrieval_complete")
        return report


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--env-file", type=Path, required=True)
    parser.add_argument("--state", type=Path, required=True)
    parser.add_argument("--checks", nargs="+", choices=sorted(definitions()), required=True)
    parser.add_argument("--max-budget-microusd", type=int, required=True)
    parser.add_argument("--concurrency", type=int, choices=[1], default=1)
    parser.add_argument("--live", action="store_true")
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        values = read_env_file(args.env_file)
        report = run_campaign(args.state.absolute(), values, names=args.checks,
            max_budget_microusd=args.max_budget_microusd, concurrency=args.concurrency,
            live=args.live, progress=lambda row: print(json.dumps(row), flush=True))
        # Exact provider schemas stay in the private ledger for reviewed, explicit
        # registration. Terminal output contains their digest and counts only.
        public = {**report}
        if "results" in report:
            public["results"] = [{key: value for key, value in row.items() if key != "observed_contract"}
                                 for row in report["results"]]
        print(json.dumps(public, sort_keys=True))
        return 0
    except (ServiceError, OSError, ValueError) as error:
        code = error.code if isinstance(error, ServiceError) else "CONNECTOR_CHECK_FAILED"
        print(json.dumps({"error": code, "retry_automatically": False}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
