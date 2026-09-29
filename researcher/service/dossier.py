"""Read-only private research dossier. No model, network, or publication effects.

This is an operator projection of digest-checked local records, not receipt
replay, source qualification, promotion authority, or a public export.
"""
from __future__ import annotations

import argparse
from collections import Counter, defaultdict
from html import escape
import json
from pathlib import Path
import re

from researcher.scripts.schema_contract import parse_json_strict
from .candidate_review import _directory
from .contracts import ServiceError, digest
from .environment import _stable_bytes
from .research_pipeline import MAX_BYTES, OUTCOMES, PHASES, _result, _validate_actions_record
from .sdk_learning import validate_archive
from .trace_cli import journal_at
from .tracing import MAX_EXPORT

MAX_PIPELINES = 64
MAX_TOTAL_BYTES = 24 * 1024 * 1024
HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")


def _require(condition):
    if not condition:
        raise ServiceError("DOSSIER_BINDING_MISMATCH")


def _learning(record, state, phases):
    """Validate retained local links, never follow/replay historical sources."""
    _require(type(record) is dict and set(record) == {
        "schema", "authority", "sources", "archive", "candidates", "source_limit_omissions"}
        and record["schema"] == "sdk-learning-checkpoint/v1" and record["authority"] == "none"
        and type(record["sources"]) is list and len(record["sources"]) <= 32
        and type(record["candidates"]) is list and len(record["candidates"]) <= 32
        and type(record["source_limit_omissions"]) is int and 0 <= record["source_limit_omissions"] <= 10000)
    archive = validate_archive(record["archive"])
    origins, paths = {}, set()
    for source in record["sources"]:
        _require(type(source) is dict and set(source) == {"path", "result_digest", "omission"}
            and isinstance(source["path"], str) and 0 < len(source["path"].encode()) <= 4096
            and source["path"] not in paths and isinstance(source["result_digest"], str)
            and HASH.fullmatch(source["result_digest"])
            and source["omission"] in {None, "incompatible", "no_research"})
        paths.add(source["path"])
        if source["omission"] is None:
            origins[source["result_digest"]] = source
    _require(all(row["source_result_digest"] in origins for row in archive["entries"]))
    for candidate in record["candidates"]:
        _require(type(candidate) is dict and set(candidate) == {
            "baseline_commit", "corpus_digest", "path", "text_sha256", "source_result_digest", "evaluation_plan_digest"}
            and isinstance(candidate["baseline_commit"], str)
            and re.fullmatch(r"[0-9a-f]{40}", candidate["baseline_commit"])
            and all(isinstance(candidate[key], str) and HASH.fullmatch(candidate[key])
                    for key in ("corpus_digest", "text_sha256", "source_result_digest"))
            and candidate["source_result_digest"] in origins
            and (candidate["evaluation_plan_digest"] is None or isinstance(candidate["evaluation_plan_digest"], str)
                 and HASH.fullmatch(candidate["evaluation_plan_digest"]))
            and isinstance(candidate["path"], str) and 0 < len(candidate["path"].encode()) <= 4096)
    _require(archive["omissions"]["source_limit"] == record["source_limit_omissions"]
        and all(archive["omissions"][reason] == sum(row["omission"] == reason for row in record["sources"])
                for reason in ("incompatible", "no_research"))
        and len(archive["entries"]) + archive["omissions"]["entry_limit"] + archive["omissions"]["byte_limit"]
            == sum(row["omission"] is None for row in record["sources"]))
    summary = {"checkpoint_digest": digest(record), "included": len(archive["entries"]),
        "omissions": archive["omissions"], "candidate_identities": len(record["candidates"]),
        "semantic_novelty_assessed": False, "researcher_only": True}
    _require(digest(state.get("learning")) == digest(summary))
    if "packet" in phases:
        _require(digest(phases["packet"].get("researcher_feedback")) == digest(archive))
    return {**record, "sources": [{"path_digest": digest(row["path"]),
        "result_digest": row["result_digest"], "omission": row["omission"]} for row in record["sources"]],
        "historical_origin_verified": False, "checkpoint_digest": digest(record)}


def build(pipelines: list[Path], trace_states: list[Path]) -> dict:
    if (type(pipelines) is not list or type(trace_states) is not list
            or not 1 <= len(pipelines) <= MAX_PIPELINES or len(trace_states) > 8
            or any(not isinstance(path, Path) for path in pipelines + trace_states)):
        raise ServiceError("DOSSIER_INVALID_SELECTION")
    pipelines = [_directory(path, private=True) for path in pipelines]
    trace_states = [_directory(path, private=True) for path in trace_states]
    if len(set(pipelines)) != len(pipelines) or len(set(trace_states)) != len(trace_states):
        raise ServiceError("DOSSIER_INVALID_SELECTION")
    jobs, journals, total, read_bytes = [], [], 0, 0

    def record(path):
        nonlocal read_bytes
        raw = _stable_bytes(path, maximum=min(MAX_BYTES, MAX_TOTAL_BYTES - read_bytes),
                            private=True, prefix="DOSSIER")
        read_bytes += len(raw)
        value = parse_json_strict(raw.decode("utf-8"))
        _require(type(value) is dict and set(value) == {"record", "digest"}
                 and value["digest"] == digest(value["record"]))
        return value["record"]

    def retain(value):
        nonlocal total
        total += len(json.dumps(value, ensure_ascii=False).encode())
        if total > MAX_TOTAL_BYTES:
            raise ServiceError("DOSSIER_SIZE_LIMIT")
        return value

    for directory in pipelines:
        inputs, state = record(directory / "input.json"), record(directory / "state.json")
        result = record(directory / "result.json")
        if (not isinstance(inputs, dict) or not isinstance(state, dict) or not isinstance(result, dict)
                or inputs.get("schema") != "research-pipeline-input/v1" or inputs.get("authority") != "none"
                or state.get("schema") != "research-pipeline-state/v1"
                or type(state.get("fixture")) is not bool or type(state.get("created_at")) is not int
                or state["created_at"] < 0 or result.get("outcome") not in OUTCOMES
                or state.get("input_digest") != digest(inputs)
                or result.get("input_digest") != digest(inputs)
                or state.get("result_digest") != digest(result) or state.get("phase") != "terminal"
                or state.get("outcome") != result.get("outcome")
                or state.get("receipts") != result.get("receipts")
                or not isinstance(state.get("receipts"), dict)):
            raise ServiceError("DOSSIER_BINDING_MISMATCH")
        _require(digest(result) == digest(_result(state, result["outcome"], result.get("detail"))))
        phases = {}
        for phase, expected in state["receipts"].items():
            if phase not in PHASES:
                raise ServiceError("DOSSIER_UNKNOWN_PHASE")
            saved = record(directory / (phase + ".json"))
            if (type(saved) is not dict or set(saved) != {"schema", "phase", "input_digest", "output"}
                    or saved["schema"] != "research-pipeline-phase/v1" or digest(saved) != expected
                    or saved["phase"] != phase or type(saved["output"]) is not dict
                    or not isinstance(saved["input_digest"], str) or not HASH.fullmatch(saved["input_digest"])):
                raise ServiceError("DOSSIER_BINDING_MISMATCH")
            phases[phase] = retain(saved["output"])
            if phase == "packet":
                _require(saved["input_digest"] == digest({"input": digest(inputs)})
                    and state.get("packet_digest") == digest(saved["output"]))
            elif phase == "research":
                _require("packet" in state["receipts"] and saved["input_digest"] == digest({"packet_digest": state.get("packet_digest")}))
            elif phase == "candidate":
                research = record(directory / "research.json")
                _require("research" in state["receipts"] and digest(research) == state["receipts"]["research"]
                    and saved["input_digest"] == digest({"packet_digest": state.get("packet_digest"),
                        "result_digest": digest(research["output"]), "dataset_digest": inputs.get("dataset_digest"),
                        "options": inputs.get("options")}))
            elif phase == "evaluation":
                _require("candidate" in state["receipts"] and isinstance(saved["output"].get("plan_digest"), str)
                    and HASH.fullmatch(saved["output"]["plan_digest"])
                    and saved["input_digest"] == digest({"plan_digest": saved["output"]["plan_digest"]}))
        if result["outcome"] != "failed":
            expected = {"packet", "research"}
            if result["outcome"] not in {"abstained", "no_proposal"}:
                expected.add("candidate")
            if result["outcome"] == "evaluated_not_accepted":
                expected.add("evaluation")
            _require(set(phases) == expected)
        learning = None
        has_learning = (directory / "learning.json").exists() or (directory / "learning.json").is_symlink()
        _require(has_learning == ("learning" in state))
        if has_learning:
            learning = retain(_learning(record(directory / "learning.json"), state, phases))
        elif "packet" in phases:
            _require("researcher_feedback" not in phases["packet"])
        actions = None
        action_path = directory / "research-actions.json"
        has_actions = action_path.exists() or action_path.is_symlink()
        _require(has_actions == ("research_actions" in state))
        options = inputs.get("options", {})
        _require(type(options) is dict)
        profile = options.get("research_profile")
        _require(profile is None or profile == "captured-actions-v1")
        if "packet" in phases:
            _require(phases["packet"].get("research_profile") == profile)
        if has_actions:
            _require(profile == "captured-actions-v1" and "packet" in phases)
            checkpoint = record(action_path)
            _validate_actions_record(checkpoint, state, phases["packet"])
            if "research" in phases:
                _require(checkpoint["transcript"]["research_digest"] == digest(phases["research"].get("research")))
            actions = retain({**checkpoint, "historical_origin_verified": False})
        elif profile == "captured-actions-v1" and "research" in phases:
            raise ServiceError("DOSSIER_ACTIONS_REQUIRED")
        if result["outcome"] == "duplicate_candidate":
            detail = result.get("detail")
            _require(learning is not None and type(detail) is dict
                and set(detail) == {"identity", "source_result_digest", "learning_digest", "evaluation_plan_digest",
                                    "semantic_novelty_assessed"}
                and detail["semantic_novelty_assessed"] is False
                and detail["learning_digest"] == learning["checkpoint_digest"]
                and isinstance(detail["evaluation_plan_digest"], str) and HASH.fullmatch(detail["evaluation_plan_digest"])
                and type(detail["identity"]) is dict
                and {**detail["identity"], "source_result_digest": detail["source_result_digest"],
                     "evaluation_plan_digest": detail["evaluation_plan_digest"]} in learning["candidates"])
        elif result["outcome"] == "evaluated_not_accepted":
            detail = result.get("detail")
            _require(type(detail) is dict and set(detail) == {"comparison_digest", "dataset_kind", "held_out_verified"}
                and detail["held_out_verified"] is False
                and type(phases["evaluation"].get("comparison")) is dict
                and detail["comparison_digest"] == phases["evaluation"]["comparison"].get("comparison_digest"))
        jobs.append(retain({"pipeline": str(directory.absolute()), "input_digest": digest(inputs),
            "source_job": inputs.get("source_job"), "skills": inputs.get("skills"),
            "created_at": state.get("created_at"), "result": result,
            "phases": phases, "learning_record": learning, "action_record": actions}))
    for state in trace_states:
        journal, rows, cursor = journal_at(state), [], 0
        while True:
            page = journal.rows(limit=MAX_EXPORT, after=cursor)
            if not page:
                break
            rows.extend(retain(page))
            cursor = page[-1]["seq"]
            if len(rows) > 10000:
                raise ServiceError("DOSSIER_TRACE_LIMIT")
        deliveries, cursor = [], 0
        while True:
            page = journal.export_rows(limit=MAX_EXPORT, after=cursor)
            if not page:
                break
            deliveries.extend(retain(page))
            cursor = page[-1]["seq"]
            if len(deliveries) > 10000:
                raise ServiceError("DOSSIER_TRACE_LIMIT")
        timings = defaultdict(list)
        for row in rows:
            if row["duration_ns"] is not None:
                timings[row["operation"]].append(row["duration_ns"])
        journals.append({"state": str(state.absolute()), "status": journal.status(),
            "operations": {name: {"count": len(values), "total_ns": sum(values),
                "maximum_ns": max(values)} for name, values in sorted(timings.items())},
            "spans": rows, "deliveries": deliveries})
    value = {"schema": "research-operator-dossier/v1", "authority": "none", "private": True,
        "verification": "local_digest_consistency_only", "provider_readback_verified": False,
        "historical_origin_verified": False, "scientific_validity_verified": False,
        "traces_correlated_to_pipelines": False,
        "outcomes": dict(Counter(job["result"]["outcome"] for job in jobs)),
        "pipelines": jobs, "trace_journals": journals}
    # Nanosecond timestamps intentionally exceed the integer-only record
    # profile's interoperable range. This display is not a canonical receipt.
    if len(json.dumps(value, ensure_ascii=False, allow_nan=False).encode()) > MAX_TOTAL_BYTES:
        raise ServiceError("DOSSIER_SIZE_LIMIT")
    return value


def html(value: dict) -> str:
    """No scripts, remote assets, active URLs, or unescaped research text."""
    def block(data):
        return "<pre>" + escape(json.dumps(data, indent=2, ensure_ascii=False)) + "</pre>"

    sections = ["<h1>Research execution dossier</h1>",
        "<p>Private operator view. Local digest consistency is not scientific validation, "
        "historical receipt replay, provider dashboard readback, or approval to publish. "
        "Selected trace journals are not authenticated to these pipelines. Source and model text are untrusted.</p>",
        "<h2>Outcomes</h2>", block(value["outcomes"])]
    for number, job in enumerate(value["pipelines"], 1):
        result = job["result"]
        sections += [f"<h2>Scenario {number}: {escape(str(job['source_job']))}</h2>",
            block({"input_digest": job["input_digest"], "skills": job["skills"],
                   "created_at": job["created_at"], "result": result})]
        if job["learning_record"] is not None:
            sections += ["<details><summary>Cross-run learning and omissions</summary>",
                         block(job["learning_record"]), "</details>"]
        if job.get("action_record") is not None:
            sections += ["<details open><summary>Agent decisions, captured reads and specialist responses</summary>",
                         block(job["action_record"]), "</details>"]
        for phase, data in job["phases"].items():
            sections += ["<details><summary>" + escape(phase) + "</summary>", block(data), "</details>"]
    for number, journal in enumerate(value["trace_journals"], 1):
        sections += [f"<h2>Trace journal {number}</h2>", block(journal["status"]),
            "<h3>Operation latency</h3><p>Nested durations overlap; do not sum them as wall time.</p>",
            block(journal["operations"]), "<h3>Raindrop delivery receipts</h3>", block(journal["deliveries"]),
            "<details><summary>All local spans and trace IDs</summary>", block(journal["spans"]), "</details>"]
    page = ('<!doctype html><html lang="en"><meta charset="utf-8">'
        '<meta http-equiv="Content-Security-Policy" content="default-src \'none\'; style-src \'unsafe-inline\'">'
        '<title>Research execution dossier</title><style>body{max-width:1100px;margin:3rem auto;'
        'padding:0 1rem;font:16px/1.6 system-ui;background:#101820;color:#edf4fa}'
        'pre{white-space:pre-wrap;overflow-wrap:anywhere;background:#1b2935;padding:1rem;font-size:13px}'
        'summary{cursor:pointer;padding:.7rem;background:#233746}details{margin:1rem 0}</style>'
        + "".join(sections) + "</html>")
    if len(page.encode("utf-8")) > MAX_TOTAL_BYTES:
        raise ServiceError("DOSSIER_SIZE_LIMIT")
    return page


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--pipeline", type=Path, action="append", required=True)
    parser.add_argument("--trace-state", type=Path, action="append", default=[])
    parser.add_argument("--format", choices=("json", "html"), default="json")
    args = parser.parse_args(argv)
    try:
        value = build(args.pipeline, args.trace_state)
        output = html(value) if args.format == "html" else json.dumps(value, indent=2, ensure_ascii=False)
        if len(output.encode("utf-8")) > MAX_TOTAL_BYTES:
            raise ServiceError("DOSSIER_SIZE_LIMIT")
        print(output)
        return 0
    except (ServiceError, OSError, ValueError, KeyError, TypeError, RecursionError):
        print(json.dumps({"error": "DOSSIER_UNAVAILABLE_OR_INCONSISTENT"}))
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
