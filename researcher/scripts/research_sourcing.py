#!/usr/bin/env python3
"""Bounded, supervised multi-lane research discovery. No model or promotion path.

A brief states the information need and each query's purpose. The shared cache
serializes public observations, reuses exact completed inputs and enforces the
arXiv daily-query/three-second policy. Neither query variants nor repeated hits
are independent experiments or scientific corroboration.
"""

from __future__ import annotations

import argparse
import json
import re
import stat
import sys
import time
from contextlib import contextmanager
from datetime import UTC, datetime
from pathlib import Path
from typing import Any, Mapping
from urllib.parse import urlsplit, urlunsplit

if __package__:
    from . import research_pipeline as pipeline
    from .local_rehearsal import (
        RehearsalError,
        _atomic_write,
        _run_lock,
        _safe_run_directory,
    )
    from .research_context import build_context_pack
    from .research_discovery import build_discovery_packet
    from .research_articles import (
        ArticleError,
        retrieve_article,
        replay_article,
        replay_article_failure,
        reextract_article,
    )
    from .schema_contract import canonicalize, sha256_bytes
else:
    import research_pipeline as pipeline
    from local_rehearsal import (
        RehearsalError,
        _atomic_write,
        _run_lock,
        _safe_run_directory,
    )
    from research_context import build_context_pack
    from research_discovery import build_discovery_packet
    from research_articles import (
        ArticleError,
        retrieve_article,
        replay_article,
        replay_article_failure,
        reextract_article,
    )
    from schema_contract import canonicalize, sha256_bytes

ROOT = pipeline.ROOT
SCHEMA = "research-discovery-brief/v1"
SOURCES = frozenset({"arxiv", *pipeline.COMPANY_FEEDS})
DEFAULT_CACHE = ROOT / "researcher/runtime/source-discovery-cache"


class SourcingError(ValueError):
    pass


def _text(value: Any, maximum: int, *, empty: bool = False) -> str:
    if not isinstance(value, str) or (not value.strip() and not empty):
        raise SourcingError("missing discovery text")
    if len(value.encode("utf-8")) > maximum or any(ord(c) < 32 for c in value):
        raise SourcingError("discovery text exceeds bounds or contains controls")
    return " ".join(value.split())


def _load(path: Path) -> dict[str, Any]:
    # Read through the nonblocking regular-file reader, including for briefs.
    payload = pipeline._read_bytes(path)

    def pairs(items):
        result = {}
        for key, value in items:
            if key in result:
                raise SourcingError("duplicate input key")
            result[key] = value
        return result

    result = json.loads(payload, object_pairs_hook=pairs)
    if not isinstance(result, dict):
        raise SourcingError("input must be an object")
    canonicalize(result)
    return result


def _write(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_write(path, canonicalize(dict(value)))


def _private(path: Path) -> Path:
    result = _safe_run_directory(path)
    if stat.S_IMODE(result.stat().st_mode) & 0o077:
        raise SourcingError("sourcing directories must be owner-only")
    return result


def build_plan(brief: Mapping[str, Any]) -> dict[str, Any]:
    required = {"schema", "question", "skills", "lanes"}
    if (
        not isinstance(brief, dict)
        or not required <= brief.keys()
        or brief.keys() - required - {"max_packet_bytes", "x_queries", "compact"}
    ):
        raise SourcingError("unknown or missing brief fields")
    if brief["schema"] != SCHEMA:
        raise SourcingError("unsupported discovery brief")
    question = _text(brief["question"], 2048)
    skills = brief["skills"]
    if (
        not isinstance(skills, list)
        or not 1 <= len(skills) <= 6
        or any(
            not isinstance(s, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,63}", s)
            for s in skills
        )
        or len(set(skills)) != len(skills)
    ):
        raise SourcingError("select one to six distinct skill IDs")
    values = brief["lanes"]
    if not isinstance(values, list) or not 1 <= len(values) <= 8:
        raise SourcingError("select one to eight bounded discovery lanes")
    lanes, seen, ids = [], set(), set()
    for value in values:
        if not isinstance(value, dict) or set(value) != {
            "id",
            "facet",
            "source",
            "query",
            "match",
            "sort",
        }:
            raise SourcingError("lane fields must be explicit")
        lane_id = value["id"]
        if (
            not isinstance(lane_id, str)
            or not re.fullmatch(r"[a-z][a-z0-9-]{0,47}", lane_id)
            or lane_id in ids
        ):
            raise SourcingError("invalid or repeated lane ID")
        source = value["source"]
        if not isinstance(source, str) or source not in SOURCES:
            raise SourcingError("source has no authorized campaign adapter")
        facet = _text(value["facet"], 512)
        query = _text(value["query"], 512, empty=source != "arxiv")
        match, sort = value["match"], value["sort"]
        if (
            not isinstance(match, str)
            or match not in {"terms", "phrase"}
            or not isinstance(sort, str)
            or sort not in {"relevance", "submittedDate", "lastUpdatedDate"}
        ):
            raise SourcingError("invalid search configuration")
        if source != "arxiv" and (query or match != "terms" or sort != "submittedDate"):
            raise SourcingError("company feed is a window, not a provider query")
        key = (source, query, match, sort)
        if key in seen:
            raise SourcingError("duplicate provider query does not add a lane")
        seen.add(key)
        ids.add(lane_id)
        lanes.append(
            dict(
                id=lane_id,
                facet=facet,
                source=source,
                query=query,
                match=match,
                sort=sort,
            )
        )
    maximum = brief.get("max_packet_bytes", 131072)
    if type(maximum) is not int or not 16384 <= maximum <= 262144:
        raise SourcingError("packet budget must be 16384 through 262144 bytes")
    x_queries = brief.get("x_queries", [])
    if not isinstance(x_queries, list) or len(x_queries) > 2:
        raise SourcingError("at most two staged X queries")
    x_queries = [_text(q, 512) for q in x_queries]
    compact = brief.get("compact", False)
    if type(compact) is not bool:
        raise SourcingError("compact must be a boolean")
    plan = {
        "schema": "local-research-sourcing-plan/v1",
        "authority": "none",
        "question": question,
        "skills": list(skills),
        "lanes": lanes,
        "max_packet_bytes": maximum,
        "x": {
            "queries": x_queries,
            "execution_enabled": False,
            "blocker": "Authenticated wire contract, resource-cost reservation and provider authorization are not accepted.",
        },
        "budget": {
            "max_http_attempts": sum(
                pipeline.source_limits(lane["source"]).max_requests for lane in lanes
            ),
            "max_response_bytes": sum(
                pipeline.source_limits(lane["source"]).max_bytes for lane in lanes
            ),
            "max_connector_seconds": sum(
                int(pipeline.source_limits(lane["source"]).max_seconds)
                for lane in lanes
            ),
            "max_politeness_seconds": 4
            * sum(lane["source"] == "arxiv" for lane in lanes),
            "model_calls": 0,
            "paid_calls": 0,
        },
    }
    if compact:
        plan["compact"] = True
    return plan


@contextmanager
def _arxiv_gate(cache: Path, signature: Mapping[str, Any], cache_key: str):
    """Caller owns cache lock through request completion. Unknown outcomes stop."""
    policies = _private(cache / "request-policy")
    day = datetime.now(UTC).date().isoformat()
    reservation = policies / (
        day + "-" + sha256_bytes(canonicalize(dict(signature))).split(":")[1] + ".json"
    )
    if reservation.exists() or reservation.is_symlink():
        raise SourcingError(
            "arXiv query already reserved today; reuse the completed cached observation or inspect its unknown outcome"
        )
    clock_path = policies / "clock.json"
    now = time.time_ns() // 1_000_000
    if clock_path.exists() or clock_path.is_symlink():
        clock_record = _load(clock_path)
        previous = clock_record.get("last_finished_ms")
        if type(previous) is not int or previous < 0 or previous > now:
            raise SourcingError("arXiv policy clock is invalid or moved backwards")
        # Epoch milliseconds fit the repository's interoperable integer JSON
        # profile. One extra millisecond covers downward clock quantization.
        delay_ms = max(0, previous + 3_001 - now)
        if delay_ms:
            time.sleep(delay_ms / 1_000)
    _write(
        reservation,
        {
            "schema": "arxiv-query-reservation/v1",
            "cache_key": cache_key,
            "signature": dict(signature),
            "reserved_at": pipeline._now(),
        },
    )
    _write(clock_path, {"last_finished_ms": time.time_ns() // 1_000_000})
    try:
        yield
    finally:
        _write(clock_path, {"last_finished_ms": time.time_ns() // 1_000_000})


def _lane_inputs(
    identity: Mapping[str, Any], lane: Mapping[str, Any]
) -> dict[str, Any]:
    plan = identity["plan"]
    return {
        "query": lane["query"] or plan["question"],
        "source": lane["source"],
        "match": lane["match"],
        "sort": lane["sort"],
        "skills": plan["skills"],
        "implementation": identity["implementation"],
        "context_digest": identity["context_digest"],
        "provenance": True,
    }


def _lane_key(manifest: Mapping[str, Any], inputs: Mapping[str, Any]) -> str:
    return manifest["cache_day"] + "-" + sha256_bytes(canonicalize(dict(inputs)))[7:]


def _check_child_inputs(config: Mapping[str, Any], inputs: Mapping[str, Any]) -> None:
    expected = {
        "query": inputs["query"],
        "implementation": inputs["implementation"],
        "skills": inputs["skills"],
        "sources": [inputs["source"]],
        "context_digest": inputs["context_digest"],
        "arxiv_search": {
            "scope": "title_abstract",
            "match": inputs["match"],
            "sort": inputs["sort"],
            "include_provenance": True,
        },
    }
    if canonicalize({key: config[key] for key in expected}) != canonicalize(expected):
        raise SourcingError("cache entry does not match its key")


def _existing_private_directory(path: Path) -> Path:
    # Unlike _private, verification must never create a missing directory.
    if (
        not path.is_absolute()
        or not path.is_dir()
        or path.resolve() != path
        or stat.S_IMODE(path.stat().st_mode) & 0o077
    ):
        raise SourcingError("campaign directory is missing, aliased or not private")
    return path


@contextmanager
def _existing_run_lock(directory: Path):
    # Read first to reject a missing lock instead of letting _run_lock repair it.
    # Cooperative local verification is not isolation from a hostile same-UID writer.
    pipeline._read_bytes(directory / ".run.lock")
    with _run_lock(directory):
        yield


def verify_sourcing_campaign(campaign_dir: Path) -> dict[str, Any]:
    """Replay a completed private campaign with zero retrieval or state repair.

    Historical source identities are bound to their child captures, not compared
    with today's code hash. Current parsers must still reproduce the saved data.
    This verifies provenance and integrity, not research quality or acceptance.
    """
    try:
        output = _existing_private_directory(Path(campaign_dir).absolute())
        with _existing_run_lock(output):
            manifest = _load(output / "manifest.json")
            if (
                set(manifest) != {"schema", "identity", "started_at", "cache_day"}
                or manifest["schema"] != "local-research-sourcing-run/v1"
                or datetime.strptime(
                    manifest["started_at"], "%Y-%m-%dT%H:%M:%SZ"
                ).strftime("%Y-%m-%dT%H:%M:%SZ")
                != manifest["started_at"]
                or datetime.strptime(manifest["cache_day"], "%Y-%m-%d").strftime(
                    "%Y-%m-%d"
                )
                != manifest["cache_day"]
            ):
                raise SourcingError("invalid campaign manifest")
            identity = manifest["identity"]
            if not isinstance(identity, dict) or set(identity) != {
                "plan",
                "implementation",
                "context_digest",
                "cache_root",
            }:
                raise SourcingError("invalid campaign identity")
            implementation = identity["implementation"]
            if (
                not isinstance(implementation, dict)
                or not 1 <= len(implementation) <= 256
                or any(
                    re.fullmatch(r"researcher/scripts/[a-zA-Z0-9_]+\.py", name) is None
                    or not isinstance(digest, str)
                    or re.fullmatch(r"sha256:[0-9a-f]{64}", digest) is None
                    for name, digest in implementation.items()
                )
                or not isinstance(identity["context_digest"], str)
                or re.fullmatch(r"sha256:[0-9a-f]{64}", identity["context_digest"])
                is None
            ):
                raise SourcingError("invalid campaign source or context identity")
            plan = identity["plan"]
            expected_plan = build_plan(
                {
                    "schema": SCHEMA,
                    "question": plan["question"],
                    "skills": plan["skills"],
                    "lanes": plan["lanes"],
                    "max_packet_bytes": plan["max_packet_bytes"],
                    "x_queries": plan["x"]["queries"],
                    "compact": plan.get("compact", False),
                }
            )
            if canonicalize(plan) != canonicalize(expected_plan):
                raise SourcingError("campaign plan differs from its declared controls")
            cache = _existing_private_directory(Path(identity["cache_root"]))
            result = _load(output / "result.json")
            manifest_digest = sha256_bytes(canonicalize(manifest))
            children, observations = [], []
            with _existing_run_lock(cache):
                for lane in plan["lanes"]:
                    inputs = _lane_inputs(identity, lane)
                    key = _lane_key(manifest, inputs)
                    intent = _load(output / ("lane-" + lane["id"] + ".json"))
                    if canonicalize(intent) != canonicalize(
                        {"manifest_sha256": manifest_digest, "cache_key": key}
                    ):
                        raise SourcingError("campaign lane intent changed")
                    child = _existing_private_directory(cache / key)
                    config = _load(child / "manifest.json")["identity"]
                    _check_child_inputs(config, inputs)
                    record = pipeline.read_verified_observation(child, read_only=True)
                    children.append(
                        {
                            "lane_id": lane["id"],
                            "cache_key": key,
                            "record_sha256": sha256_bytes(canonicalize(record)),
                            "run_id": record["run_id"],
                        }
                    )
                    observations.append(
                        {
                            "lane_id": lane["id"],
                            "facet": lane["facet"],
                            "query": lane["query"],
                            "record": record,
                        }
                    )
            packet = build_discovery_packet(
                plan["question"],
                observations,
                max_bytes=plan["max_packet_bytes"],
                compact=plan.get("compact", False),
            )
            expected_result = {
                "schema": "local-research-sourcing-result/v1",
                "authority": "none",
                "production_ready": False,
                "manifest_sha256": manifest_digest,
                "children": children,
                "packet_sha256": sha256_bytes(canonicalize(packet)),
                "model_calls": 0,
                "paid_calls": 0,
                "x": plan["x"],
            }
            if canonicalize(result) != canonicalize(expected_result) or canonicalize(
                _load(output / "discovery-packet.json")
            ) != canonicalize(packet):
                raise SourcingError("completed campaign artifacts changed")
            return {
                "manifest": manifest,
                "result": result,
                "observations": observations,
                "packet": packet,
            }
    except SourcingError:
        raise
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        raise SourcingError("campaign evidence replay failed") from error


def run_sourcing(
    brief: Mapping[str, Any],
    runtime_dir: Path,
    *,
    live: bool = False,
    cache_dir: Path = DEFAULT_CACHE,
    root: Path = ROOT,
) -> dict[str, Any]:
    plan = build_plan(brief)
    if live is not True:
        raise SourcingError("discovery execution requires explicit live-public opt-in")
    # Validate all corpus/context requirements before opening a network path.
    context = build_context_pack(root, plan["skills"], 65536)
    implementation = pipeline._implementation_identity(root)
    output = _private(runtime_dir)
    cache = _private(cache_dir)
    identity = {
        "plan": plan,
        "implementation": implementation,
        "context_digest": context.digest,
        "cache_root": str(cache),
    }
    with _run_lock(output), _run_lock(cache):
        manifest_path = output / "manifest.json"
        if manifest_path.exists() or manifest_path.is_symlink():
            manifest = _load(manifest_path)
            if manifest.get("identity") != identity:
                raise SourcingError("campaign inputs changed; create a new campaign")
        else:
            if {p.name for p in output.iterdir()} != {".run.lock"}:
                raise SourcingError("nonempty campaign has no manifest")
            manifest = {
                "schema": "local-research-sourcing-run/v1",
                "identity": identity,
                "started_at": pipeline._now(),
                "cache_day": datetime.now(UTC).date().isoformat(),
            }
            _write(manifest_path, manifest)
        observations, children = [], []
        result_path = output / "result.json"
        completed = result_path.exists() or result_path.is_symlink()
        for lane in plan["lanes"]:
            inputs = _lane_inputs(identity, lane)
            key = _lane_key(manifest, inputs)
            child = cache / key
            checkpoint = child / "observation.json"
            cached = checkpoint.exists() or checkpoint.is_symlink()
            intent_path = output / ("lane-" + lane["id"] + ".json")
            lane_intent = {
                "manifest_sha256": sha256_bytes(canonicalize(manifest)),
                "cache_key": key,
            }
            if intent_path.exists() or intent_path.is_symlink():
                if _load(intent_path) != lane_intent or not cached:
                    raise SourcingError(
                        "previous lane lost its child or has an unknown outcome; no implicit retrieval"
                    )
            else:
                if completed:
                    raise SourcingError("completed campaign lost a lane intent")
                _write(intent_path, lane_intent)
            if cached:
                record = pipeline.read_verified_observation(child)
                child_manifest = _load(child / "manifest.json")["identity"]
                _check_child_inputs(child_manifest, inputs)
            else:
                if completed:
                    raise SourcingError(
                        "completed campaign lost a child; no implicit retrieval"
                    )
                kwargs = dict(
                    runtime_dir=child,
                    query=inputs["query"],
                    selected_skills=plan["skills"],
                    sources=[lane["source"]],
                    arxiv_scope="title_abstract",
                    arxiv_match=lane["match"],
                    arxiv_sort=lane["sort"],
                    include_provenance=True,
                    live=True,
                    root=root,
                )
                if lane["source"] == "arxiv":
                    signature = {
                        "query": lane["query"],
                        "scope": "title_abstract",
                        "match": lane["match"],
                        "sort": lane["sort"],
                        "limits": pipeline._plain(pipeline.asdict(pipeline.LIMITS)),
                    }
                    with _arxiv_gate(cache, signature, key):
                        record = pipeline.run_pipeline(**kwargs)
                else:
                    record = pipeline.run_pipeline(**kwargs)
            observations.append(
                {
                    "lane_id": lane["id"],
                    "facet": lane["facet"],
                    "query": lane["query"],
                    "record": record,
                }
            )
            children.append(
                {
                    "lane_id": lane["id"],
                    "cache_key": key,
                    "record_sha256": sha256_bytes(canonicalize(record)),
                    "run_id": record["run_id"],
                }
            )
        packet = build_discovery_packet(
            plan["question"],
            observations,
            max_bytes=plan["max_packet_bytes"],
            compact=plan.get("compact", False),
        )
        result = {
            "schema": "local-research-sourcing-result/v1",
            "authority": "none",
            "production_ready": False,
            "manifest_sha256": sha256_bytes(canonicalize(manifest)),
            "children": children,
            "packet_sha256": sha256_bytes(canonicalize(packet)),
            "model_calls": 0,
            "paid_calls": 0,
            "x": plan["x"],
        }
        if completed:
            if (
                _load(result_path) != result
                or _load(output / "discovery-packet.json") != packet
            ):
                raise SourcingError("completed campaign artifacts changed")
        else:
            if implementation != pipeline._implementation_identity(root):
                raise SourcingError("implementation changed during campaign")
            if context.digest != build_context_pack(root, plan["skills"], 65536).digest:
                raise SourcingError("corpus changed during campaign")
            _write(output / "discovery-packet.json", packet)
            _write(result_path, result)
        return result


def read_primary(
    runtime_dir: Path, url: str, *, live: bool = False, reextract: bool = False
) -> dict[str, Any]:
    """Explicit one-hop read selected from verified discovery, never a crawler."""
    if live is not True and reextract is not True:
        raise SourcingError("primary reading requires explicit live-public opt-in")
    output = _private(runtime_dir)
    with _run_lock(output):
        manifest = _load(output / "manifest.json")
        result = _load(output / "result.json")
        if result["manifest_sha256"] != sha256_bytes(canonicalize(manifest)):
            raise SourcingError("campaign manifest binding changed")
        plan = manifest["identity"]["plan"]
        cache = _private(Path(manifest["identity"]["cache_root"]))
        selected_from, observations = [], []
        if len(result["children"]) != len(plan["lanes"]):
            raise SourcingError("campaign child count changed")
        for lane, child in zip(plan["lanes"], result["children"], strict=True):
            if child["lane_id"] != lane["id"] or not re.fullmatch(
                r"\d{4}-\d{2}-\d{2}-[0-9a-f]{64}", child["cache_key"]
            ):
                raise SourcingError("invalid child reference")
            record = pipeline.read_verified_observation(cache / child["cache_key"])
            if (
                sha256_bytes(canonicalize(record)) != child["record_sha256"]
                or record["run_id"] != child["run_id"]
            ):
                raise SourcingError("campaign child changed")
            observations.append(
                {
                    "lane_id": lane["id"],
                    "facet": lane["facet"],
                    "query": lane["query"],
                    "record": record,
                }
            )
            for source in record["sources"]:
                for lead in source["leads"]:
                    candidates = {lead["url"]}
                    # The arXiv HTML endpoint is a representation choice for
                    # this exact discovered version, not invented evidence.
                    parsed = urlsplit(lead["url"])
                    if (
                        parsed.hostname == "arxiv.org"
                        and parsed.path.startswith("/abs/")
                        and not parsed.query
                        and not parsed.fragment
                    ):
                        candidates.add(
                            urlunsplit(
                                (
                                    "https",
                                    "arxiv.org",
                                    "/html/" + parsed.path[5:],
                                    "",
                                    "",
                                )
                            )
                        )
                    for key, value in lead["metadata"]:
                        if key in {
                            "external_url",
                            "expanded_url",
                            "unwound_url",
                            "article_url",
                        }:
                            candidates.add(value)
                    if url in candidates:
                        selected_from.append(
                            {
                                "lane_id": lane["id"],
                                "run_id": record["run_id"],
                                "lead_identity": lead["identity"],
                            }
                        )
        packet = build_discovery_packet(
            plan["question"],
            observations,
            max_bytes=plan["max_packet_bytes"],
            compact=plan.get("compact", False),
        )
        if (
            sha256_bytes(canonicalize(packet)) != result["packet_sha256"]
            or _load(output / "discovery-packet.json") != packet
        ):
            raise SourcingError("discovery packet changed")
        if not selected_from:
            raise SourcingError("article URL is not a selected discovery lead")
        articles = _private(output / "articles")
        directory = _private(articles / sha256_bytes(url.encode()).split(":")[1])
        store = pipeline.LocalResearchEvidenceStore(directory / "evidence")
        bound = {
            "source_url": url,
            "selected_from": selected_from,
            "campaign_sha256": sha256_bytes(canonicalize(result)),
        }
        saved = directory / "result.json"
        if reextract and not saved.is_file():
            raise SourcingError(
                "offline re-extraction requires a retained primary read"
            )
        if saved.exists() or saved.is_symlink():
            record = _load(saved)
            if record.get("input") != bound:
                raise SourcingError("article input changed")
            if reextract:
                # Preserve the old parser outcome. A new extraction is bound to
                # its original bytes and the current reader, with no HTTP path.
                common = {"schema", "authority", "input", "status"}
                fields = (
                    {"article"}
                    if record.get("status") == "observed"
                    else {"error_code", "captures", "failure_assessment"}
                )
                if (
                    record.get("schema") != "local-research-primary-read/v1"
                    or record.get("authority") != "none"
                    or record.get("status") not in {"observed", "failed"}
                    or set(record) != common | fields
                ):
                    raise SourcingError("invalid original primary read wrapper")
                captures = (
                    [record["article"]["capture"]]
                    if record["status"] == "observed"
                    else record["captures"]
                )
                if not isinstance(captures, list) or len(captures) != 1:
                    raise SourcingError(
                        "re-extraction requires one complete captured response"
                    )
                article = reextract_article(store, url, captures[0])
                replay_article(store, article)
                updated = {
                    "schema": "local-research-primary-reextraction/v1",
                    "authority": "none",
                    "input": bound,
                    "original_result_sha256": sha256_bytes(canonicalize(record)),
                    "new_http_attempts": 0,
                    "article": article,
                }
                target = directory / (
                    "reextracted-" + article["reader_sha256"].split(":")[1] + ".json"
                )
                if target.exists() or target.is_symlink():
                    if _load(target) != updated:
                        raise SourcingError("re-extraction artifact changed")
                else:
                    _write(target, updated)
                return updated
            expected = {
                "schema": "local-research-primary-read/v1",
                "authority": "none",
                "input": bound,
            }
            if record["status"] == "observed":
                expected.update(
                    status="observed", article=replay_article(store, record["article"])
                )
            elif record["status"] == "failed":
                assessment = replay_article_failure(
                    store, url, record["error_code"], record["captures"]
                )
                expected.update(
                    status="failed",
                    error_code=record["error_code"],
                    captures=record["captures"],
                    failure_assessment=assessment,
                )
            else:
                raise SourcingError("invalid article state")
            if record != expected:
                raise SourcingError("primary read wrapper changed")
            return record
        intent = directory / "intent.json"
        if intent.exists() or intent.is_symlink():
            raise SourcingError(
                "article request has unknown outcome; no implicit retry"
            )
        record = {
            "schema": "local-research-primary-read/v1",
            "authority": "none",
            "input": bound,
        }
        with _run_lock(cache):
            _write(intent, bound)
            try:
                if urlsplit(url).hostname == "arxiv.org":
                    with _arxiv_gate(cache, {"primary_url": url}, directory.name):
                        article = retrieve_article(url, store)
                else:
                    article = retrieve_article(url, store)
                replay_article(store, article)
                record.update(status="observed", article=article)
            except ArticleError as exc:
                captures = list(exc.captures)
                assessment = replay_article_failure(store, url, exc.code, captures)
                record.update(
                    status="failed",
                    error_code=exc.code,
                    captures=captures,
                    failure_assessment=assessment,
                )
            _write(saved, record)
        return record


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        command = sub.add_parser(name)
        command.add_argument("--brief", type=Path, required=True)
        if name == "run":
            command.add_argument("--runtime-dir", type=Path, required=True)
            command.add_argument("--live-public", action="store_true")
    read = sub.add_parser("read")
    read.add_argument("--runtime-dir", type=Path, required=True)
    read.add_argument("--url", required=True)
    read.add_argument("--live-public", action="store_true")
    reextract = sub.add_parser("reextract")
    reextract.add_argument("--runtime-dir", type=Path, required=True)
    reextract.add_argument("--url", required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "reextract":
            result = read_primary(args.runtime_dir, args.url, reextract=True)
        elif args.command == "read":
            result = read_primary(args.runtime_dir, args.url, live=args.live_public)
        else:
            brief = _load(args.brief.absolute())
            result = (
                build_plan(brief)
                if args.command == "plan"
                else run_sourcing(brief, args.runtime_dir, live=args.live_public)
            )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (
        OSError,
        ValueError,
        KeyError,
        TypeError,
        RehearsalError,
        pipeline.ConnectorError,
        ArticleError,
    ) as exc:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "error_type": type(exc).__name__,
                    "authority": "none",
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
