"""Capture-verified retrieval to managed research, preparation only.

The source Store remains the owner of collection. This reader uses one SQLite
snapshot and the immutable evidence store; it cannot retrieve, reserve, execute
models, publish, repair partial jobs, or silently substitute a newer daily report.
"""

from __future__ import annotations

import argparse
from dataclasses import asdict
import json
import os
from pathlib import Path
import re
import time

from researcher.scripts.schema_contract import canonicalize
from .contracts import ServiceError, digest, load_config
from .context_digest import build_context_digest
from .primary_context import (LIMITS, POLICY, build_primary_context,
                              project_primary_evidence, read_profile_binding, select_primary, verify_primary)
from .research_brief import validate_retrieval_context
from .retrieval_sources import source_limits, verify
from .store import Store


def _same(actual, expected, code):
    if canonicalize(actual) != canonicalize(expected):
        raise ServiceError(code)


def _step(steps, name, inputs):
    row = steps.get(name)
    if row is None:
        raise ServiceError("RETRIEVAL_HANDOFF_CHECKPOINT_MISSING")
    if row["input_digest"] != digest(inputs):
        raise ServiceError("RETRIEVAL_HANDOFF_INPUT_CHANGED")
    return Store._history_value(row["output"], row["output_digest"], 2_000_000)


def _observation(steps, effects, name, inputs):
    value = _step(steps, name, inputs)
    effect = effects.get(name)
    if (effect is None or effect["state"] != "completed"
            or effect["input_digest"] != digest(inputs)
            or effect["model_calls"] != 0):
        raise ServiceError("RETRIEVAL_HANDOFF_EFFECT_INVALID")
    _same(Store._history_value(effect["output"], effect["output_digest"], 2_000_000),
          value, "RETRIEVAL_HANDOFF_EFFECT_MISMATCH")
    return value


def verified_bundle(store: Store, job: str, *, now: int | None = None,
                    maximum_age_seconds: int = 172800, fixture: bool = False) -> dict:
    """Read/replay a specified completed job, with no credentials or network.

    Historical sampling signals are recomputed from their frozen checkpoint,
    not promoted as independent corroboration. They are not sent to the model.
    Freshness is the collection window, never proof of publication freshness.
    """
    current = int(time.time()) if now is None else now
    if (type(current) is not int or current < 0 or type(fixture) is not bool
            or type(maximum_age_seconds) is not int or not 60 <= maximum_age_seconds <= 604800):
        raise ServiceError("RETRIEVAL_HANDOFF_POLICY_INVALID")
    with store._history_snapshot() as db:
        row = db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
        if row is None:
            raise ServiceError("JOB_NOT_FOUND")
        manifest = store._retrieval_manifest(row)
        if (manifest.get("retrieval_policy") != "daily-observation-v1"
                or not re.fullmatch(r"sha256:[0-9a-f]{64}", str(manifest.get("implementation_digest", "")))
                or not re.fullmatch(r"[0-9a-f]{40}", str(manifest.get("baseline_commit", "")))):
            raise ServiceError("RETRIEVAL_HANDOFF_MANIFEST_INVALID")
        if row["status"] != "retrieval_complete":
            raise ServiceError("RETRIEVAL_HANDOFF_INCOMPLETE")
        if manifest["fixture"] != fixture:
            raise ServiceError("RETRIEVAL_HANDOFF_FIXTURE_MISMATCH")
        if (manifest["config_digest"] != digest(store.config)
                or manifest["schedule"] not in store.config["schedules"]):
            raise ServiceError("RETRIEVAL_HANDOFF_CONFIG_CHANGED")
        if not 30 <= current - manifest["window_end"] <= maximum_age_seconds:
            raise ServiceError("RETRIEVAL_HANDOFF_STALE")
        steps = {r["name"]: dict(r) for r in db.execute(
            "SELECT * FROM steps WHERE job=? LIMIT 129", (job,))}
        effects = {r["name"]: dict(r) for r in db.execute(
            "SELECT * FROM effects WHERE job=? LIMIT 129", (job,))}
        if len(steps) > 128 or len(effects) > 128:
            raise ServiceError("RETRIEVAL_HANDOFF_RECORD_LIMIT")
    schedule = manifest["schedule"]
    history_inputs = {"manifest": digest(manifest)}
    report = _step(steps, "report", history_inputs)
    prior = _step(steps, "prior-retrieval", history_inputs)
    if set(prior) != {"entries"}:
        raise ServiceError("RETRIEVAL_HANDOFF_HISTORY_INVALID")
    if (report.get("source_failures", []) or report.get("reconciliation_required", False)
            or report.get("collection_completed", True) is not True):
        raise ServiceError("RETRIEVAL_HANDOFF_INCOMPLETE")
    lanes, expected_effects = [], set()
    for source in schedule["sources"]:
        query = schedule["source_queries"][source]
        limits = asdict(source_limits(source))
        limits["max_milliseconds"] = int(limits.pop("max_seconds") * 1000)
        policy = {"policy": manifest["retrieval_policy"], "source": source, "query": query,
                  "window_start": manifest["window_start"], "window_end": manifest["window_end"],
                  "limits": limits}
        inputs = {"policy": policy, "manifest_digest": digest(manifest)}
        name = "retrieval-" + source
        lane = _observation(steps, effects, name, inputs)
        verify(source, query, lane, store.directory / "evidence",
               start_time=manifest["window_start"], end_time=manifest["window_end"])
        if lane["state"] != "observed":
            raise ServiceError("RETRIEVAL_HANDOFF_INCOMPLETE")
        lanes.append(lane)
        expected_effects.add(name)
    packet = build_context_digest(schedule["query"], lanes, max_bytes=32768,
                                  max_items=20, previous=prior["entries"])
    _same(packet, report.get("context_digest"), "RETRIEVAL_HANDOFF_DIGEST_MISMATCH")
    bound = {"manifest": digest(manifest), "discovery": digest(packet),
             "lanes": digest(lanes), "policy": POLICY}
    profile = schedule.get("primary_read_profile")
    profile_binding = read_profile_binding(profile)
    profile_kwargs = {} if profile is None else {"profile": profile}
    if profile_binding is not None:
        bound["reader_policy"] = profile_binding
    selection_profile = schedule.get("primary_selection_profile")
    if selection_profile is not None:
        bound["selection_profile"] = selection_profile
    selection = select_primary(lanes, packet, schedule.get("primary_read_limit", 0), profile=selection_profile)
    _same(selection, _step(steps, "primary-selection", bound), "RETRIEVAL_HANDOFF_SELECTION_MISMATCH")
    outcomes = []
    for index, selected in enumerate(selection["selected"]):
        url = selected["source_url"]
        policy = {"policy": POLICY, "url": url,
                  "limits": LIMITS if profile_binding is None else profile_binding["limits"],
                  "implementation_digest": manifest["implementation_digest"],
                  "query": schedule["query"], "window_start": manifest["window_start"],
                  "window_end": manifest["window_end"]}
        if profile_binding is not None:
            policy["reader_policy"] = profile_binding
        if selection_profile is not None:
            policy["selection_profile"] = selection_profile
        inputs = {"manifest": digest(manifest), "selection": selected, "policy": policy}
        name = "primary-" + str(index)
        outcome = _observation(steps, effects, name, inputs)
        verify_primary(url, outcome, store.directory / "primary-evidence", **profile_kwargs)
        outcomes.append(outcome)
        expected_effects.add(name)
    if set(effects) != expected_effects:
        raise ServiceError("RETRIEVAL_HANDOFF_UNEXPECTED_EFFECT")
    primary = build_primary_context(schedule["query"], selection, outcomes)
    _same(primary, _step(steps, "primary-context", bound), "RETRIEVAL_HANDOFF_PRIMARY_MISMATCH")
    expected = {"schema": "research-retrieval-report/v1", "job": job,
                "disposition": "retrieval_only", "evidence_qualified": False,
                "production_ready": False, "fixture": fixture, "schedule_id": schedule["id"],
                "window_start": manifest["window_start"], "window_end": manifest["window_end"],
                "context_digest": packet, "primary_context": primary,
                "sources": [{"source": lane["source"], "state": lane["state"],
                             "items": len(lane["evidence"])} for lane in lanes]}
    # Older complete reports predate collection-outcome fields; no partial
    # report is grandfathered because terminal state and every effect were read.
    for key, value in (("collection_completed", True), ("reconciliation_required", False),
                       ("source_failures", [])):
        if key in report:
            expected[key] = value
    _same(report, expected, "RETRIEVAL_HANDOFF_REPORT_MISMATCH")
    if not primary["cards"]:
        raise ServiceError("RETRIEVAL_HANDOFF_PRIMARY_REQUIRED")
    # Only narrow context fields are provider-visible. Capture locators, raw
    # metadata and the full discovery omission index stay in the private Store.
    fields = ("id", "source", "text", "sha256", "evidence_scope", "qualifiers")
    evidence = [{key: entry[key] for key in fields} for entry in packet["items"]]
    evidence += project_primary_evidence(primary)
    links = []
    for card in primary["cards"]:
        projected = project_primary_evidence({**primary, "cards": [card]})
        links.append({"discovery_id": card["selected_from"]["discovery_id"],
                      "source_text_digest": card["text_sha256"],
                      "excerpt_ids": [row["id"] for row in projected]})
    context = {"schema": "research-retrieval-context/v1", "authority": "none",
               "job_digest": digest(job), "manifest_digest": digest(manifest),
               "report_digest": digest(report), "evidence_digest": digest(evidence),
               "query_digest": digest(schedule["query"]),
               "window_start": manifest["window_start"], "window_end": manifest["window_end"],
               "verified_at": current, "maximum_age_seconds": maximum_age_seconds,
               "fixture": fixture, "capture_replayed": True,
               "scientific_quality_assessed": False, "full_paper_verified": False,
               "exhaustive_coverage": False, "independent_corroboration": False,
               "primary_cards": len(primary["cards"]), "primary_gaps": len(primary["gaps"]),
               "discovery_omissions": len(packet["omissions"]),
               "primary_selection_omissions": len(primary["selection_omissions"]),
               "primary_links": links,
               "sources": [{"source": lane["source"], "state": lane["state"],
                   "items": len(lane["evidence"]), **{key: lane["coverage"][key] for key in
                       ("window_applied", "window_resolution", "continuation_available", "partial")}}
                   for lane in lanes]}
    validate_retrieval_context(context, schedule["query"], evidence)
    return {"query": schedule["query"], "evidence": evidence, "retrieval_context": context}


def prepare_from_retrieval(store: Store, job: str, root: Path, destination: Path, *,
                           model: str, skills: list[str], max_subagents: int = 0,
                           now: int | None = None, maximum_age_seconds: int = 172800,
                           fixture: bool = False):
    from .agents_runtime import SessionLedger, prepare_packet

    with store.worker_lock():
        bundle = verified_bundle(store, job, now=now, maximum_age_seconds=maximum_age_seconds,
                                 fixture=fixture)
        packet = prepare_packet(root, model=model, skills=skills, max_subagents=max_subagents,
                                fixture=fixture, **bundle)
        return SessionLedger.prepare(destination.absolute(), packet)


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--config", type=Path, required=True)
    parser.add_argument("--source-state", type=Path, required=True)
    parser.add_argument("--job", required=True)
    parser.add_argument("--state", type=Path, required=True, help="Fresh private managed directory")
    parser.add_argument("--model", required=True)
    parser.add_argument("--skill", action="append", required=True)
    parser.add_argument("--max-subagents", type=int, default=0)
    parser.add_argument("--maximum-age-seconds", type=int, default=172800)
    parser.add_argument("--fixture", action="store_true")
    args = parser.parse_args(argv)
    os.umask(0o077)
    try:
        from .environment import read_config_file
        store = Store(args.source_state, load_config(read_config_file(args.config)))
        ledger = prepare_from_retrieval(store, args.job, args.repo, args.state,
            model=args.model, skills=args.skill, max_subagents=args.max_subagents,
            maximum_age_seconds=args.maximum_age_seconds, fixture=args.fixture)
        print(json.dumps(ledger.status(), sort_keys=True))
        return 0
    except Exception as exc:
        print(json.dumps({"error": getattr(exc, "code", "RETRIEVAL_HANDOFF_FAILED")}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
