"""Bounded, source-replayed research memory. Never evaluation or acceptance state.

Only the researcher receives the public projection. Frozen candidate identities
are exact byte comparisons, not novelty judgments. Paths and evaluation records
remain private. Existing receipts, not this projection, retain authority.
"""

from __future__ import annotations

from pathlib import Path
import re

from researcher.scripts.schema_contract import canonicalize, sha256_bytes
from .contracts import ServiceError, digest

MAX_SOURCES = 32
MAX_ENTRIES = 5
MAX_ARCHIVE_BYTES = 32768
MAX_HISTORY_BYTES = 64 * 1024 * 1024
_HASH = re.compile(r"sha256:[0-9a-f]{64}\Z")


def source_paths(sources, *, current: Path | None = None):
    if not isinstance(sources, list) or len(sources) > MAX_SOURCES:
        raise ServiceError("LEARNING_SOURCE_LIMIT")
    from .candidate_review import _directory
    paths = []
    for value in sources:
        if not isinstance(value, Path) or not value.is_absolute():
            raise ServiceError("LEARNING_UNSAFE_SOURCE")
        path = _directory(value, private=True)
        if path == current or path in paths:
            raise ServiceError("LEARNING_DUPLICATE_SOURCE")
        paths.append(path)
    return paths


def validate_archive(value):
    """Closed prompt projection; no labels, results, answers, traces or paths."""
    keys = {"schema", "authority", "role", "semantic_novelty_assessed", "entries", "omissions"}
    if (type(value) is not dict or set(value) != keys
            or value["schema"] != "sdk-researcher-memory/v1" or value["authority"] != "none"
            or value["role"] != "researcher" or value["semantic_novelty_assessed"] is not False
            or type(value["entries"]) is not list or len(value["entries"]) > MAX_ENTRIES
            or type(value["omissions"]) is not dict
            or set(value["omissions"]) != {"incompatible", "no_research", "entry_limit", "byte_limit", "source_limit"}
            or any(type(n) is not int or n < 0 or n > 10000 for n in value["omissions"].values())):
        raise ServiceError("LEARNING_INVALID_ARCHIVE")
    seen = set()
    for row in value["entries"]:
        if (type(row) is not dict or set(row) != {"source_job_digest", "source_result_digest",
                "packet_digest", "hypothesis", "test_plan", "research_outcome", "evidence_references"}
                or any(not isinstance(row[k], str) or not _HASH.fullmatch(row[k])
                       for k in ("source_job_digest", "source_result_digest", "packet_digest"))
                or row["source_result_digest"] in seen
                or row["research_outcome"] not in {"abstained", "no_proposal", "proposed"}
                or any(not isinstance(row[k], str) or not 1 <= len(row[k].encode("utf-8")) <= 16384
                       for k in ("hypothesis", "test_plan"))
                or type(row["evidence_references"]) is not list or len(row["evidence_references"]) > 128):
            raise ServiceError("LEARNING_INVALID_ARCHIVE")
        seen.add(row["source_result_digest"])
        for ref in row["evidence_references"]:
            if (type(ref) is not dict or set(ref) != {"id", "sha256"}
                    or not isinstance(ref["id"], str) or not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,159}", ref["id"])
                    or not isinstance(ref["sha256"], str) or not _HASH.fullmatch(ref["sha256"])):
                raise ServiceError("LEARNING_INVALID_ARCHIVE")
    if len(canonicalize(value)) > MAX_ARCHIVE_BYTES:
        raise ServiceError("LEARNING_ARCHIVE_LIMIT")
    return value


def frozen_identity(directory, packet, output, review):
    """Match exact frozen bytes to the authenticated proposal and baseline."""
    from . import research_pipeline as pipeline
    from .workflow import apply_edit
    proposal = output["proposal"]
    if proposal is None:
        raise ServiceError("LEARNING_CANDIDATE_BINDING")
    expected = {"baseline_commit": packet["baseline_commit"], "manifest_digest": digest(packet),
                "result_digest": digest(output)}
    if (review.get("source_binding") != expected or review.get("proposal_digest") != digest(proposal)
            or review.get("corpus_digest") != digest(packet["corpus"])
            or review.get("evidence_digest") != digest(packet["evidence"])
            or review["candidate"]["declared_changed_surfaces"] != [proposal["path"]]):
        raise ServiceError("LEARNING_CANDIDATE_BINDING")
    pipeline._review_plan(directory, review)
    _, changed = apply_edit(proposal, packet["corpus"], output["critic"]["supported_claim_ids"])
    frozen = pipeline._stable_bytes(directory / "candidate-review/frozen" / proposal["path"],
        maximum=131072, private=True, prefix="LEARNING_FROZEN")
    if changed.encode("utf-8") != frozen:
        raise ServiceError("LEARNING_CANDIDATE_BINDING")
    return {"baseline_commit": packet["baseline_commit"], "corpus_digest": digest(packet["corpus"]),
            "path": proposal["path"], "text_sha256": sha256_bytes(frozen)}


def _source(directory, *, root, store, campaign, packet, current_job):
    from . import research_pipeline as pipeline
    from .agents_context import validate_result
    from .agents_runtime import prepare_packet
    from .retrieval_handoff import verified_bundle
    inputs = pipeline._record(directory / "input.json")
    state = pipeline._record(directory / "state.json")
    result = pipeline._record(directory / "result.json")
    if (inputs.get("schema") != "research-pipeline-input/v1"
            or state.get("schema") != "research-pipeline-state/v1"
            or state.get("input_digest") != digest(inputs) or state.get("phase") != "terminal"
            or state.get("result_digest") != digest(result) or state.get("outcome") != result.get("outcome")
            or type(state.get("created_at")) is not int or state["created_at"] < 0
            or type(state.get("receipts")) is not dict or set(state["receipts"]) - set(pipeline.PHASES)
            or any(not isinstance(value, str) or not _HASH.fullmatch(value) for value in state["receipts"].values())
            or result.get("outcome") not in pipeline.OUTCOMES):
        raise ServiceError("LEARNING_SOURCE_BINDING")
    pipeline._same(result, pipeline._result(state, result["outcome"], result.get("detail")), "LEARNING_SOURCE_BINDING")
    pipeline._verify_receipts(directory, state)
    # Compatibility is deliberately narrower than semantic relatedness. A new
    # corpus/runtime needs a new study, not an automatic history migration.
    expected = {"root_digest": digest(str(root)), "baseline_commit": packet["baseline_commit"],
        "implementation_digest": packet["implementation_digest"],
        "source_directory_digest": digest(str(store.directory)), "source_config_digest": digest(store.config),
        "authority_directory_digest": digest(str(campaign.directory)),
        "authority_config_digest": digest(campaign.store.config), "runtime": campaign.execution_identity()}
    if (any(inputs.get(k) != v for k, v in expected.items())
            or inputs.get("options", {}).get("fixture") is not packet["fixture"]
            or inputs.get("options", {}).get("research_profile") != packet.get("research_profile")
            or inputs.get("source_job") == current_job
            or state["created_at"] > packet["retrieval_context"]["verified_at"]):
        return None, "incompatible"
    if result["outcome"] == "failed" or "research" not in state["receipts"]:
        return None, "no_research"
    if campaign.backend != "codex_sdk" and not packet["fixture"]:
        raise ServiceError("LEARNING_SDK_ORIGIN_REQUIRED")
    with store.worker_lock():
        bundle = verified_bundle(store, inputs["source_job"], now=state["created_at"],
            maximum_age_seconds=inputs["options"]["maximum_age_seconds"], fixture=packet["fixture"])
    original = prepare_packet(root, model=packet["model"], skills=inputs["skills"],
                              max_subagents=0, fixture=packet["fixture"], **bundle)
    if packet.get("research_profile") is not None:
        original["research_profile"] = packet["research_profile"]
    saved_packet = pipeline._record(directory / "packet.json")
    if "researcher_feedback" in saved_packet["output"]:
        previous = pipeline._record(directory / "learning.json")
        original["researcher_feedback"] = validate_archive(previous["archive"])
    pipeline._same(saved_packet, {"schema": "research-pipeline-phase/v1", "phase": "packet",
        "input_digest": digest({"input": digest(inputs)}), "output": original}, "LEARNING_SOURCE_PACKET_CHANGED")
    with store._history_snapshot() as db:
        schedules = []
        for job in (inputs["source_job"], current_job):
            row = db.execute("SELECT * FROM jobs WHERE id=?", (job,)).fetchone()
            if row is None:
                raise ServiceError("LEARNING_SOURCE_BINDING")
            schedules.append(store._retrieval_manifest(row)["schedule"])
    if digest(original) != state["packet_digest"]:
        raise ServiceError("LEARNING_SOURCE_PACKET_CHANGED")
    if (digest(original["corpus"]) != digest(packet["corpus"]) or schedules[0] != schedules[1]
            or original["retrieval_context"]["window_end"] > packet["retrieval_context"]["window_end"]):
        return None, "incompatible"
    research = pipeline._record(directory / "research.json")
    pipeline._same(research, {"schema": "research-pipeline-phase/v1", "phase": "research",
        "input_digest": digest({"packet_digest": digest(original)}), "output": research["output"]}, "LEARNING_SOURCE_BINDING")
    output = validate_result(canonicalize(research["output"]).decode(), original["corpus"], original["evidence"])
    pipeline._verify_actions(directory, state, original, campaign, "pipeline-" + digest(inputs)[7:47],
                             required=original.get("research_profile") is not None)
    if campaign.backend == "codex_sdk":
        # Replay-only verification cannot submit a missing role or retry a
        # provider effect; SDK origin receipts authenticate the proposed text.
        campaign.verify_research("pipeline-" + digest(inputs)[7:47], original, output)
    identity = None
    if output["proposal"] is not None and "candidate" in state["receipts"]:
        phase = pipeline._record(directory / "candidate.json")
        pipeline._same(phase["input_digest"], digest({"packet_digest": digest(original),
            "result_digest": digest(output), "dataset_digest": inputs["dataset_digest"], "options": inputs["options"]}),
            "LEARNING_CANDIDATE_BINDING")
        identity = frozen_identity(directory, original, output, phase["output"])
        identity["evaluation_plan_digest"] = None
        if result["outcome"] == "evaluated_not_accepted":
            from .agents_evals import compare_results
            plan = pipeline._review_plan(directory, phase["output"])
            if plan is None or "evaluation" not in state["receipts"]:
                raise ServiceError("LEARNING_EVALUATION_BINDING")
            evaluated = pipeline._record(directory / "evaluation.json")
            execution = evaluated["output"]
            pipeline._same(evaluated, {"schema": "research-pipeline-phase/v1", "phase": "evaluation",
                "input_digest": digest({"plan_digest": plan["plan_digest"]}), "output": execution},
                "LEARNING_EVALUATION_BINDING")
            comparison = compare_results(plan, execution["results"])
            if execution.get("plan_digest") != plan["plan_digest"]:
                raise ServiceError("LEARNING_EVALUATION_BINDING")
            pipeline._same(execution["comparison"], comparison, "LEARNING_EVALUATION_BINDING")
            if campaign.backend == "codex_sdk":
                campaign.verify_evaluation("pipeline-" + digest(inputs)[7:47] + "-evaluation", plan, execution)
            identity["evaluation_plan_digest"] = plan["plan_digest"]
    # No critic text, evaluation status/scores, gold or task answers cross this
    # projection. References remain prior observations, not present support.
    entry = {"source_job_digest": digest(inputs["source_job"]), "source_result_digest": digest(result),
        "packet_digest": digest(original), "hypothesis": output["research"]["hypothesis"],
        "test_plan": output["research"]["test_plan"],
        "research_outcome": "proposed" if output["proposal"] else
            "abstained" if output["research"]["abstain"] else "no_proposal",
        "evidence_references": [{"id": row["id"], "sha256": row["sha256"]} for row in original["evidence"]]}
    return {"entry": entry, "candidate": identity, "result_digest": digest(result)}, None


def build(root, store, campaign, packet, current_job, sources, *, source_limit_omissions=0):
    """Read/replay at most 32 caller-selected terminal studies; no writes/calls."""
    from . import research_pipeline as pipeline
    paths = source_paths(sources)
    if type(source_limit_omissions) is not int or not 0 <= source_limit_omissions <= 10000:
        raise ServiceError("LEARNING_SOURCE_LIMIT")
    archive = {"schema": "sdk-researcher-memory/v1", "authority": "none", "role": "researcher",
        "semantic_novelty_assessed": False, "entries": [], "omissions": {
            "incompatible": 0, "no_research": 0, "entry_limit": 0, "byte_limit": 0,
            "source_limit": source_limit_omissions}}
    origins, candidates, total = [], [], 0
    for path in paths:
        # A total bound complements per-artifact readers. Never recurse through
        # overlays, environments, or candidate code.
        for name in ("input", "state", "result", "packet", "research", "candidate", "evaluation", "learning", "research-actions"):
            file = path / (name + ".json")
            if file.exists() or file.is_symlink():
                total += len(pipeline._stable_bytes(file, maximum=pipeline.MAX_BYTES, private=True, prefix="LEARNING"))
                if total > MAX_HISTORY_BYTES:
                    raise ServiceError("LEARNING_HISTORY_BYTE_LIMIT")
        with pipeline._lock(path, create=False):
            row, reason = _source(path, root=root, store=store, campaign=campaign,
                                  packet=packet, current_job=current_job)
            result_digest = digest(pipeline._record(path / "result.json"))
        origins.append({"path": str(path), "result_digest": result_digest,
                        "omission": reason})
        if reason:
            archive["omissions"][reason] += 1
            continue
        if row["candidate"] is not None:
            candidates.append({**row["candidate"], "source_result_digest": row["result_digest"]})
        if len(archive["entries"]) >= MAX_ENTRIES:
            archive["omissions"]["entry_limit"] += 1
            continue
        archive["entries"].append(row["entry"])
        # Reserve room for all later omission counters growing to their bound.
        if len(canonicalize(archive)) > MAX_ARCHIVE_BYTES - 128:
            archive["entries"].pop()
            archive["omissions"]["byte_limit"] += 1
    validate_archive(archive)
    return {"schema": "sdk-learning-checkpoint/v1", "authority": "none", "sources": origins,
            "archive": archive, "candidates": candidates, "source_limit_omissions": source_limit_omissions}


def duplicate(checkpoint, identity, *, evaluation_plan_digest=None):
    # Seeing bytes is not completing their evaluation. A new dataset or a
    # previously unevaluated candidate must still reach independent evaluation.
    if evaluation_plan_digest is None:
        return None
    for row in checkpoint["candidates"]:
        if (all(row.get(key) == value for key, value in identity.items())
                and row.get("evaluation_plan_digest") == evaluation_plan_digest):
            return {"identity": identity, "source_result_digest": row["source_result_digest"],
                    "learning_digest": digest(checkpoint), "evaluation_plan_digest": evaluation_plan_digest,
                    "semantic_novelty_assessed": False}
    return None
