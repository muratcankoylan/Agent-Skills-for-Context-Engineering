"""Explicit, resumable retrieval-to-evaluation coordination, without promotion.

The shared Campaign remains the only paid-call/budget authority. These private
phase receipts are leaf recovery records, not another accepted-state registry.
No credentials, environment reads, direct provider calls or publication API.
"""

from __future__ import annotations

import contextlib
import fcntl
import os
from pathlib import Path
import re
import time

from researcher.scripts.artifact_store import _atomic_write_bytes
from researcher.scripts.schema_contract import canonicalize, parse_json_strict, sha256_bytes
from .agents_context import validate_result
from .agents_evals import _dataset, _plan, compare_results
from .agents_runtime import prepare_packet
from .candidate_review import _directory, review_candidate
from .contracts import ServiceError, digest
from .environment import _stable_bytes
from .openai_campaign import Campaign, PRICING, _reflected, implementation_digest as campaign_implementation
from .retrieval_handoff import verified_bundle
from .store import Store
from .shutdown import check_stop
from .workflow import git_head, implementation
from .tracing import annotate, instrument, current_span

MAX_BYTES = 8 * 1024 * 1024
PHASES = ("packet", "research", "candidate", "evaluation")
OUTCOMES = {"abstained", "no_proposal", "structural_validation_failed", "awaiting_dataset",
            "evaluated_not_accepted", "duplicate_candidate", "failed"}


def _read(path: Path):
    raw = _stable_bytes(path, maximum=MAX_BYTES, private=True, prefix="PIPELINE")
    try:
        return parse_json_strict(raw.decode("utf-8"))
    except (ValueError, UnicodeError, RecursionError):
        raise ServiceError("PIPELINE_INVALID_JSON") from None


def _write(path: Path, value):
    body = canonicalize(value)
    if len(body) > MAX_BYTES:
        raise ServiceError("PIPELINE_ARTIFACT_LIMIT")
    if path.exists() or path.is_symlink():
        _read(path)  # Never follow or overwrite an unsafe pre-existing alias.
    _atomic_write_bytes(path, body)


def _envelope(record):
    return {"record": record, "digest": digest(record)}


def _record(path):
    value = _read(path)
    if (not isinstance(value, dict) or set(value) != {"record", "digest"}
            or value["digest"] != digest(value["record"])):
        raise ServiceError("PIPELINE_RECEIPT_DIGEST_MISMATCH")
    return value["record"]


@contextlib.contextmanager
def _lock(directory, *, create):
    path = directory / "pipeline.lock"
    if not create:
        _stable_bytes(path, maximum=0, private=True, prefix="PIPELINE_LOCK")
    flags = os.O_RDWR | os.O_NOFOLLOW | (os.O_CREAT | os.O_EXCL if create else 0)
    fd = os.open(path, flags, 0o600)
    try:
        try:
            fcntl.flock(fd, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            raise ServiceError("PIPELINE_ALREADY_RUNNING") from None
        yield
    finally:
        os.close(fd)


def _same(actual, expected, code="PIPELINE_INPUT_CHANGED"):
    if canonicalize(actual) != canonicalize(expected):
        raise ServiceError(code)


def _no_credential(value, campaign):
    credential = campaign.credential
    if isinstance(credential, str) and credential and _reflected(value, credential):
        raise ServiceError("PIPELINE_CREDENTIAL_IN_ARTIFACT")


def _verify_receipts(directory, state):
    for name, expected in state["receipts"].items():
        record = _record(directory / (name + ".json"))
        if (record.get("schema") != "research-pipeline-phase/v1"
                or record.get("phase") != name or digest(record) != expected):
            raise ServiceError("PIPELINE_PHASE_BINDING_MISMATCH")


def _clock(now):
    value = int(time.time()) if now is None else now
    if type(value) is not int or value < 0:
        raise ServiceError("PIPELINE_INVALID_CLOCK")
    return value


def _binding(root, store, job, campaign, skills, dataset, options):
    return {"schema": "research-pipeline-input/v1", "authority": "none",
        "root_digest": digest(str(root)), "baseline_commit": git_head(root),
        "implementation_digest": implementation(root),
        "source_directory_digest": digest(str(store.directory)), "source_job": job,
        "source_config_digest": digest(store.config),
        "authority_directory_digest": digest(str(campaign.directory)),
        "authority_config_digest": digest(campaign.store.config),
        "campaign_implementation_digest": campaign_implementation(),
        "runtime": campaign.execution_identity(),
        "skills": skills, "dataset": dataset, "dataset_digest": digest(dataset),
        "options": options}


def _save(directory, state):
    _write(directory / "state.json", _envelope(state))


@instrument("pipeline.phase")
def _phase(directory, state, name, inputs, operation):
    if current_span() is not None:
        current_span().reference("operation_ref", name)
    path = directory / (name + ".json")
    input_digest = digest(inputs)
    if name in state["receipts"] or path.exists() or path.is_symlink():
        record = _record(path)
        if (set(record) != {"schema", "phase", "input_digest", "output"}
                or record["schema"] != "research-pipeline-phase/v1"
                or record["phase"] != name or record["input_digest"] != input_digest
                or name in state["receipts"] and state["receipts"][name] != digest(record)):
            raise ServiceError("PIPELINE_PHASE_BINDING_MISMATCH")
        # Reconcile the crash window between phase receipt and state checkpoint.
        state["receipts"][name] = digest(record)
        if state["outcome"] is None:
            state["phase"] = name + "_complete"
        _save(directory, state)
        annotate(outcome="replayed", replayed=True)
        return record["output"]
    check_stop()
    if name == "candidate" and (directory / "candidate-review").exists():
        raise ServiceError("PIPELINE_CANDIDATE_REVIEW_INTERRUPTED")
    state["phase"] = name + "_running"
    _save(directory, state)
    output = operation()
    annotate(outcome="completed")
    record = {"schema": "research-pipeline-phase/v1", "phase": name,
              "input_digest": input_digest, "output": output}
    _write(path, _envelope(record))
    state["receipts"][name] = digest(record)
    state["phase"] = name + "_complete"
    _save(directory, state)
    return output


def _result(state, outcome, detail=None):
    result = {"schema": "research-pipeline-result/v1", "authority": "none",
        "production_ready": False, "input_digest": state["input_digest"],
        "packet_digest": state.get("packet_digest"), "outcome": outcome,
        "receipts": dict(state["receipts"]), "detail": detail,
        "fixture": state["fixture"], "execution_backend": state.get("execution_backend", "bounded_native_responses"),
        "scientific_improvement_demonstrated": False, "publication": "not_attempted"}
    if "learning" in state:
        result["learning"] = state["learning"]
    if "research_actions" in state:
        result["research_actions"] = state["research_actions"]
    return result


def _terminal_state(directory, state, result):
    """A committed result is not invalidated by a failed local index write."""
    outcome = result["outcome"]
    state.update(phase="terminal", outcome=outcome, result_digest=digest(result))
    try:
        _save(directory, state)
    except OSError:
        raise ServiceError("PIPELINE_CHECKPOINT_INTERRUPTED") from None
    return result


def _finish(directory, state, outcome, *, detail=None):
    result = _result(state, outcome, detail)
    path = directory / "result.json"
    try:
        if path.exists() or path.is_symlink():
            # Never overwrite a previous success, failure or malformed receipt.
            _same(_record(path), result, "PIPELINE_RESULT_CHANGED")
        else:
            _write(path, _envelope(result))
    except OSError:
        raise ServiceError("PIPELINE_CHECKPOINT_INTERRUPTED") from None
    return _terminal_state(directory, state, result)


def _candidate(directory, packet, output, dataset, options, root):
    return review_candidate(root, directory / "candidate-review", corpus=packet["corpus"],
        evidence=packet["evidence"], output=output, source_binding={
            "baseline_commit": packet["baseline_commit"], "manifest_digest": digest(packet),
            "result_digest": digest(output)}, dataset=dataset,
        model=PRICING["model"] if dataset is not None else None,
        seed=options["seed"], replications=options["replications"], max_sessions=options["max_sessions"])


def _validate_actions_record(record, state, packet, *, allow_uncheckpointed=False):
    """Pure local validation; receipt references do not authenticate model origin."""
    from .agent_actions import verify_transcript
    from .openai_campaign import _research_inputs
    if packet.get("research_profile") != "captured-actions-v1":
        raise ServiceError("PIPELINE_ACTIONS_PROFILE_MISMATCH")
    prepared = _research_inputs(packet)
    if (type(record) is not dict or set(record) != {"schema", "authority", "input_digest",
                                                  "packet_digest", "transcript"}
            or record["schema"] != "research-pipeline-actions/v1" or record["authority"] != "none"
            or record["input_digest"] != state["input_digest"] or record["packet_digest"] != digest(packet)):
        raise ServiceError("PIPELINE_ACTIONS_BINDING_MISMATCH")
    verify_transcript(record["transcript"], prepared["context"], prepared["catalog"],
                      feedback=prepared["feedback"], binding=prepared["binding"])
    summary = {"profile": "captured-actions-v1", "checkpoint_digest": digest(record),
               "transcript_digest": digest(record["transcript"])}
    if "research_actions" in state:
        _same(state["research_actions"], summary, "PIPELINE_ACTIONS_CHANGED")
    elif not allow_uncheckpointed:
        raise ServiceError("PIPELINE_ACTIONS_CHANGED")
    return summary


def _actions_checkpoint(directory, state, packet, campaign, transcript=None, *, required=False):
    """Bind an inspectable projection, not a second authority for SDK actions.

    Pure tools are rederived here. Authentic model origin is checked separately
    through Campaign's committed SDK receipts before terminal or learning reuse.
    """
    path = directory / "research-actions.json"
    present = path.exists() or path.is_symlink()
    if packet.get("research_profile") != "captured-actions-v1":
        if present or "research_actions" in state or transcript is not None:
            raise ServiceError("PIPELINE_ACTIONS_PROFILE_MISMATCH")
        return None
    if transcript is None and not present:
        if required or "research_actions" in state:
            raise ServiceError("PIPELINE_ACTIONS_REQUIRED")
        return None
    record = (_record(path) if transcript is None else {
        "schema": "research-pipeline-actions/v1", "authority": "none",
        "input_digest": state["input_digest"], "packet_digest": digest(packet), "transcript": transcript})
    summary = _validate_actions_record(record, state, packet, allow_uncheckpointed=transcript is not None)
    if transcript is not None:
        _no_credential(record, campaign)
        if present:
            _same(_record(path), record, "PIPELINE_ACTIONS_CHANGED")
        else:
            _write(path, _envelope(record))
        state["research_actions"] = summary
        _save(directory, state)
    return record["transcript"]


def _verify_actions(directory, state, packet, campaign, identity, *, required=False, reconcile=False):
    path = directory / "research-actions.json"
    if reconcile and "research_actions" not in state and (path.exists() or path.is_symlink()):
        record = _record(path)
        summary = _validate_actions_record(record, state, packet, allow_uncheckpointed=True)
        if campaign is not None and campaign.backend == "codex_sdk":
            campaign.verify_actions(identity, packet, record["transcript"])
        elif packet["fixture"] is not True:
            raise ServiceError("PIPELINE_CODEX_SDK_REQUIRED")
        # Only the narrow receipt-before-state window is repairable. For SDK
        # execution the model receipts must already exist: verification cannot
        # admit a missing decision or specialist call.
        state["research_actions"] = summary
        _save(directory, state)
    transcript = _actions_checkpoint(directory, state, packet, campaign, required=required)
    if transcript is not None and campaign is not None and campaign.backend == "codex_sdk":
        campaign.verify_actions(identity, packet, transcript)
    return transcript


def _review_plan(directory, review):
    report = _read(directory / "candidate-review/review.json")
    _same(report, review, "PIPELINE_CANDIDATE_REVIEW_CHANGED")
    if report["review_digest"] != digest({k: v for k, v in report.items() if k != "review_digest"}):
        raise ServiceError("PIPELINE_CANDIDATE_REVIEW_CHANGED")
    frozen_path = directory / "candidate-review/frozen" / report["candidate"]["declared_changed_surfaces"][0]
    frozen = _stable_bytes(frozen_path, maximum=131072, private=True, prefix="PIPELINE_FROZEN")
    if report["freeze_receipt"]["entries"][0]["digest"] != sha256_bytes(frozen):
        raise ServiceError("PIPELINE_FROZEN_CANDIDATE_CHANGED")
    if report["evaluation_plan_digest"] is None:
        return None
    plan = _plan(_read(directory / "candidate-review/evaluation-plan.json"))
    if (plan["plan_digest"] != report["evaluation_plan_digest"]
            or frozen.decode("utf-8") != plan["skills"]["candidate"]):
        raise ServiceError("PIPELINE_EVALUATION_PLAN_CHANGED")
    return plan


def _terminal_result(directory, state, packet, dataset, options, *, campaign=None, identity=None):
    """Validate a retained completion before reconciling its state checkpoint.

    The caller has replayed source captures and rebound the packet. Successful
    outcomes additionally require the exact saved research/candidate/evaluation
    phases; this path never invokes a missing phase or makes a model call.
    """
    result = _record(directory / "result.json")
    if not isinstance(result, dict) or result.get("outcome") not in OUTCOMES:
        raise ServiceError("PIPELINE_RESULT_CHANGED")
    _same(result, _result(state, result["outcome"], result.get("detail")), "PIPELINE_RESULT_CHANGED")
    if (state["outcome"] is not None and (state["outcome"] != result["outcome"]
            or state["result_digest"] != digest(result))
            or state["outcome"] is None and state["result_digest"] is not None):
        raise ServiceError("PIPELINE_RESULT_CHANGED")

    def saved(name, inputs):
        if name not in state["receipts"]:
            raise ServiceError("PIPELINE_TERMINAL_PHASE_MISSING")
        record = _record(directory / (name + ".json"))
        expected = {"schema": "research-pipeline-phase/v1", "phase": name,
                    "input_digest": digest(inputs), "output": record.get("output")}
        _same(record, expected, "PIPELINE_PHASE_BINDING_MISMATCH")
        if digest(record) != state["receipts"][name]:
            raise ServiceError("PIPELINE_PHASE_BINDING_MISMATCH")
        return record["output"]

    review = plan = None
    _verify_actions(directory, state, packet, campaign, identity, required="research" in state["receipts"]
                    and packet.get("research_profile") is not None)
    if "candidate" in state["receipts"]:
        research = saved("research", {"packet_digest": digest(packet)})
        review = saved("candidate", {"packet_digest": digest(packet), "result_digest": digest(research),
            "dataset_digest": digest(dataset), "options": options})
        plan = _review_plan(directory, review)
    if result["outcome"] == "failed":
        failure = _record(directory / "failure.json")
        phases = {"initialized", *(name + suffix for name in PHASES for suffix in ("_running", "_complete"))}
        if (not isinstance(failure, dict) or set(failure) != {"schema", "authority", "input_digest",
                "phase", "code", "automatic_retry"}
                or failure["schema"] != "research-pipeline-failure/v1" or failure["authority"] != "none"
                or failure["input_digest"] != state["input_digest"] or failure["phase"] not in phases
                or not isinstance(failure["code"], str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", failure["code"])
                or failure["automatic_retry"] is not False):
            raise ServiceError("PIPELINE_FAILURE_BINDING_MISMATCH")
        _same(result["detail"], {"code": failure["code"]}, "PIPELINE_FAILURE_BINDING_MISMATCH")
    else:
        output = saved("research", {"packet_digest": digest(packet)})
        output = validate_result(canonicalize(output).decode(), packet["corpus"], packet["evidence"])
        if campaign is not None and campaign.backend == "codex_sdk":
            campaign.verify_research(identity, packet, output)
        expected_phases, detail = {"packet", "research"}, None
        if output["proposal"] is None:
            outcome = "abstained" if output["research"]["abstain"] or output["critic"]["recommendation"] == "abstain" else "no_proposal"
        elif review is None:
            raise ServiceError("PIPELINE_TERMINAL_PHASE_MISSING")
        elif review["structural_checks_passed"] is not True:
            expected_phases.add("candidate")
            outcome = "structural_validation_failed"
        elif "learning" in state and (match := _duplicate(directory, packet, output, review)) is not None:
            expected_phases.add("candidate")
            outcome, detail = "duplicate_candidate", match
        elif dataset is None:
            expected_phases.add("candidate")
            outcome = "awaiting_dataset"
        else:
            if plan is None:
                raise ServiceError("PIPELINE_EVALUATION_PLAN_CHANGED")
            expected_phases.update(("candidate", "evaluation"))
            execution = saved("evaluation", {"plan_digest": plan["plan_digest"]})
            if execution.get("plan_digest") != plan["plan_digest"]:
                raise ServiceError("PIPELINE_EVALUATION_BINDING_MISMATCH")
            comparison = compare_results(plan, execution["results"])
            _same(execution["comparison"], comparison, "PIPELINE_EVALUATION_BINDING_MISMATCH")
            if campaign is not None and campaign.backend == "codex_sdk":
                campaign.verify_evaluation(identity + "-evaluation", plan, execution)
            outcome = "evaluated_not_accepted"
            detail = {"comparison_digest": comparison["comparison_digest"],
                      "dataset_kind": plan["dataset"]["kind"], "held_out_verified": False}
        if set(state["receipts"]) != expected_phases:
            raise ServiceError("PIPELINE_TERMINAL_PHASE_MISMATCH")
        _same(result, _result(state, outcome, detail), "PIPELINE_RESULT_CHANGED")
    return _terminal_state(directory, state, result)


def run_pipeline(root: Path, source_store: Store, job: str, directory: Path, *,
                 campaign: Campaign, skills: list[str], dataset: dict | None = None,
                 seed: int = 1, replications: int = 3, max_sessions: int = 144,
                 maximum_age_seconds: int = 172800, fixture: bool = False,
                 live: bool = False, now: int | None = None,
                 learning_sources: list[Path] | None = None, learning_omissions: int = 0,
                 research_profile: str | None = None) -> dict:
    if not isinstance(campaign, Campaign):
        raise ServiceError("PIPELINE_SHARED_AUTHORITY_REQUIRED")
    parent = current_span()
    tracer = parent.tracer if parent is not None else campaign.tracer
    with tracer.span("pipeline.run") as span:
        span.reference("operation_ref", job)
        result = _run_pipeline(root, source_store, job, directory, campaign=campaign,
            skills=skills, dataset=dataset, seed=seed, replications=replications,
            max_sessions=max_sessions, maximum_age_seconds=maximum_age_seconds,
            fixture=fixture, live=live, now=now, learning_sources=learning_sources,
            learning_omissions=learning_omissions, research_profile=research_profile)
        # Durable failures return normally for recovery. That must not make the
        # enclosing workflow appear successful in the operator's trace view.
        outcome = result["outcome"]
        if outcome in {"failed", "structural_validation_failed"}:
            span.set_status("error")
            span.annotate(outcome="failed")
        else:
            span.annotate(outcome="abstained" if outcome in {"abstained", "no_proposal"}
                else "rejected" if outcome == "duplicate_candidate"
                else "prepared" if outcome == "awaiting_dataset" else "completed")
        return result


def _duplicate(directory, packet, output, review):
    from .sdk_learning import duplicate, frozen_identity
    return duplicate(_record(directory / "learning.json"),
                     frozen_identity(directory, packet, output, review),
                     evaluation_plan_digest=review["evaluation_plan_digest"])


def _run_pipeline(root: Path, source_store: Store, job: str, directory: Path, *,
                  campaign: Campaign, skills: list[str], dataset: dict | None = None,
                  seed: int = 1, replications: int = 3, max_sessions: int = 144,
                  maximum_age_seconds: int = 172800, fixture: bool = False,
                  live: bool = False, now: int | None = None,
                  learning_sources: list[Path] | None = None, learning_omissions: int = 0,
                  research_profile: str | None = None) -> dict:
    """Run or resume one bound proposal study; never create a budget authority.

    SDK calls use the supplied shared CodexCampaign. This compiles the
    same capture-bound context packet as managed preparation but creates no
    managed session. Explicit fixture adapters are for tests only.
    """
    if not isinstance(campaign, Campaign) or not isinstance(source_store, Store):
        raise ServiceError("PIPELINE_SHARED_AUTHORITY_REQUIRED")
    if type(fixture) is not bool or type(live) is not bool:
        raise ServiceError("PIPELINE_INVALID_EXECUTION_MODE")
    if fixture and not campaign.fixture_execution:
        raise ServiceError("PIPELINE_FIXTURE_PROVIDER_FORBIDDEN")
    if not fixture and not live:
        raise ServiceError("PIPELINE_LIVE_APPROVAL_REQUIRED")
    if not fixture and campaign.backend != "codex_sdk":
        raise ServiceError("PIPELINE_CODEX_SDK_REQUIRED")
    if research_profile is not None and research_profile != "captured-actions-v1":
        raise ServiceError("INVALID_RESEARCH_PROFILE")
    root = _directory(root)
    directory = directory.absolute()
    _directory(directory.parent, private=True)
    if directory.resolve() != directory or directory == root or root in directory.parents:
        raise ServiceError("PIPELINE_UNSAFE_DIRECTORY")
    if (not isinstance(job, str) or not 1 <= len(job.encode("utf-8")) <= 200
            or not isinstance(skills, list) or not 1 <= len(skills) <= 32
            or any(not isinstance(skill, str) or not re.fullmatch(r"[a-z][a-z0-9-]{0,95}", skill) for skill in skills)
            or len(set(skills)) != len(skills)
            or type(maximum_age_seconds) is not int or not 60 <= maximum_age_seconds <= 604800):
        raise ServiceError("PIPELINE_INVALID_INPUT")
    for value, lower, upper in ((seed, 0, 2**31-1), (replications, 1, 10), (max_sessions, 1, 480)):
        if type(value) is not int or not lower <= value <= upper:
            raise ServiceError("PIPELINE_INVALID_EVALUATION_OPTIONS")
    current = _clock(now)
    options = {"seed": seed, "replications": replications, "max_sessions": max_sessions,
               "maximum_age_seconds": maximum_age_seconds, "fixture": fixture}
    if research_profile is not None:
        options["research_profile"] = research_profile
    if learning_sources is not None:
        from . import sdk_learning
        learning_sources = sdk_learning.source_paths(learning_sources, current=directory)
        if type(learning_omissions) is not int or not 0 <= learning_omissions <= 10000:
            raise ServiceError("LEARNING_SOURCE_LIMIT")
        options["learning_sources"] = [str(path) for path in learning_sources]
        options["learning_omissions"] = learning_omissions
    elif learning_omissions != 0:
        raise ServiceError("LEARNING_SOURCE_LIMIT")
    inputs = _binding(root, source_store, job, campaign, skills, dataset, options)
    _no_credential(inputs, campaign)
    # Bound/deep-copy before storing. No caller mutation may change later phases.
    body = canonicalize(inputs)
    if len(body) > MAX_BYTES:
        raise ServiceError("PIPELINE_ARTIFACT_LIMIT")
    inputs = parse_json_strict(body.decode("utf-8"))
    dataset, skills = inputs["dataset"], inputs["skills"]
    created = not directory.exists()
    if created:
        directory.mkdir(mode=0o700, exist_ok=False)
    else:
        _directory(directory, private=True)
    with _lock(directory, create=created):
        if created:
            state = {"schema": "research-pipeline-state/v1", "input_digest": digest(inputs),
                     "execution_backend": campaign.backend,
                     "created_at": current, "fixture": fixture, "phase": "initialized",
                     "receipts": {}, "outcome": None, "result_digest": None}
            _write(directory / "input.json", _envelope(inputs))
            _save(directory, state)
        else:
            _same(_record(directory / "input.json"), inputs)
            state = _record(directory / "state.json")
            if (state.get("schema") != "research-pipeline-state/v1"
                    or state.get("input_digest") != digest(inputs)
                    or state.get("fixture") is not fixture
                    or type(state.get("created_at")) is not int
                    or not isinstance(state.get("receipts"), dict)
                    or set(state["receipts"]) - set(PHASES)):
                raise ServiceError("PIPELINE_STATE_BINDING_MISMATCH")
        try:
            _verify_receipts(directory, state)
            if dataset is not None:
                _dataset(dataset)
                if len(dataset["tasks"]) * replications * 3 > max_sessions:
                    raise ServiceError("EVAL_SESSION_LIMIT")
            # Every invocation replays source captures. Freeze verified_at so
            # clock movement cannot silently generate a different packet.
            with source_store.worker_lock():
                bundle = verified_bundle(source_store, job, now=state["created_at"],
                    maximum_age_seconds=maximum_age_seconds, fixture=fixture)
            packet = prepare_packet(root, model=PRICING["model"], skills=skills,
                                    max_subagents=0, fixture=fixture, **bundle)
            if research_profile is not None:
                packet["research_profile"] = research_profile
            _no_credential(packet, campaign)
            if (packet["implementation_digest"] != inputs["implementation_digest"]
                    or packet["baseline_commit"] != inputs["baseline_commit"]):
                raise ServiceError("PIPELINE_IMPLEMENTATION_CHANGED")
            if learning_sources is not None:
                from . import sdk_learning
                learning = sdk_learning.build(root, source_store, campaign, packet, job, learning_sources,
                                             source_limit_omissions=learning_omissions)
                _no_credential(learning, campaign)
                path = directory / "learning.json"
                if path.exists() or path.is_symlink():
                    _same(_record(path), learning, "PIPELINE_LEARNING_CHANGED")
                else:
                    _write(path, _envelope(learning))
                packet["researcher_feedback"] = learning["archive"]
                summary = {"checkpoint_digest": digest(learning), "included": len(learning["archive"]["entries"]),
                    "omissions": learning["archive"]["omissions"], "candidate_identities": len(learning["candidates"]),
                    "semantic_novelty_assessed": False, "researcher_only": True}
                if "learning" in state:
                    _same(state["learning"], summary, "PIPELINE_LEARNING_CHANGED")
                state["learning"] = summary
            expected_packet = packet
            packet = _phase(directory, state, "packet", {"input": digest(inputs)}, lambda: packet)
            _same(packet, expected_packet, "PIPELINE_PACKET_CHANGED")
            state["packet_digest"] = digest(packet)
            _save(directory, state)
            identity = "pipeline-" + digest(inputs)[7:47]
            if state["outcome"] is not None or (directory / "result.json").exists() or (directory / "result.json").is_symlink():
                return _terminal_result(directory, state, packet, dataset, options, campaign=campaign, identity=identity)
            def fresh():
                actual = _clock(now)
                if (actual < state["created_at"] or actual - bundle["retrieval_context"]["window_end"] > maximum_age_seconds):
                    raise ServiceError("PIPELINE_SOURCE_STALE")
                _same(_binding(root, source_store, job, campaign, skills, dataset, options), inputs)
            fresh()
            # Existing/corrupt local artifacts must fail before another model
            # admission, even if no completed research phase exists yet.
            _verify_actions(directory, state, packet, campaign, identity, reconcile=True)
            research_options = {}
            if research_profile is not None:
                research_options = {"research_profile": research_profile,
                    "action_sink": lambda transcript: _actions_checkpoint(
                        directory, state, packet, campaign, transcript)}
            output = _phase(directory, state, "research", {"packet_digest": digest(packet)},
                            lambda: campaign.research(identity, packet, **research_options))
            output = validate_result(canonicalize(output).decode(), packet["corpus"], packet["evidence"])
            _verify_actions(directory, state, packet, campaign, identity, required=research_profile is not None)
            if campaign.backend == "codex_sdk":
                campaign.verify_research(identity, packet, output)
            if output["proposal"] is None:
                return _finish(directory, state, "abstained" if output["research"]["abstain"]
                    or output["critic"]["recommendation"] == "abstain" else "no_proposal")
            review = _phase(directory, state, "candidate", {"packet_digest": digest(packet),
                "result_digest": digest(output), "dataset_digest": digest(dataset), "options": options},
                lambda: _candidate(directory, packet, output, dataset, options, root))
            if review["structural_checks_passed"] is not True:
                return _finish(directory, state, "structural_validation_failed")
            if learning_sources is not None:
                match = _duplicate(directory, packet, output, review)
                if match is not None:
                    return _finish(directory, state, "duplicate_candidate", detail=match)
            if dataset is None:
                return _finish(directory, state, "awaiting_dataset")
            plan = _review_plan(directory, review)
            fresh()
            execution = _phase(directory, state, "evaluation", {"plan_digest": plan["plan_digest"]},
                lambda: campaign.evaluate(identity + "-evaluation", plan))
            if execution.get("plan_digest") != plan["plan_digest"]:
                raise ServiceError("PIPELINE_EVALUATION_BINDING_MISMATCH")
            _same(execution["comparison"], compare_results(plan, execution["results"]),
                  "PIPELINE_EVALUATION_BINDING_MISMATCH")
            if campaign.backend == "codex_sdk":
                campaign.verify_evaluation(identity + "-evaluation", plan, execution)
            return _finish(directory, state, "evaluated_not_accepted", detail={
                "comparison_digest": execution["comparison"]["comparison_digest"],
                "dataset_kind": plan["dataset"]["kind"], "held_out_verified": False})
        except Exception as error:
            if (getattr(error, "code", None) == "PIPELINE_CHECKPOINT_INTERRUPTED"
                    or state["outcome"] is not None
                    or (directory / "result.json").exists() or (directory / "result.json").is_symlink()):
                # Invalid retained completions require reconciliation, not an
                # overwrite with a newly manufactured failure result.
                raise
            # An exception's arbitrary text may contain source/model/provider
            # material. Persist only a closed-shape stable code and stage.
            code = getattr(error, "code", "PIPELINE_LOCAL_FAILURE")
            if not isinstance(code, str) or not re.fullmatch(r"[A-Z0-9_]{1,100}", code):
                code = "PIPELINE_LOCAL_FAILURE"
            failure = {"schema": "research-pipeline-failure/v1", "authority": "none",
                       "input_digest": state["input_digest"], "phase": state["phase"],
                       "code": code, "automatic_retry": False}
            failure_path = directory / "failure.json"
            if failure_path.exists() or failure_path.is_symlink():
                _same(_record(failure_path), failure, "PIPELINE_FAILURE_BINDING_MISMATCH")
            else:
                _write(failure_path, _envelope(failure))
            return _finish(directory, state, "failed", detail={"code": code})
