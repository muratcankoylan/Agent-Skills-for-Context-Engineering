"""Offline, non-authoritative skill-candidate freeze and review preparation.

Only an inert exact Markdown replacement can differ from the reviewed checkout.
Trusted repository validators run with bounded resources on an isolated copy.
They are not a sandbox for untrusted validator code. No model, network, registry,
Git write, publication, or acceptance operation is provided here.
"""

from __future__ import annotations

from datetime import UTC, datetime
import os
from pathlib import Path, PurePosixPath
import re
import resource
import signal
import stat
import subprocess
import sys
import tempfile

from researcher.scripts.artifact_store import (
    ArtifactAuthority, CandidateFreezer, EditableSurfacePolicy,
    LocalContentAddressedStore, _atomic_write_bytes, _stable_file_read, snapshot_tree,
)
from researcher.scripts.schema_contract import canonicalize, new_typed_id, parse_json_strict, sha256_bytes
from .agents_context import validate_result
from .agents_evals import build_plan
from .contracts import ServiceError, digest
from .knowledge import _read as read_skill
from .workflow import apply_edit
from .tracing import instrument

MAX_FILES = 2048
MAX_FILE_BYTES = 4 * 1024 * 1024
MAX_TREE_BYTES = 64 * 1024 * 1024
MAX_OUTPUT_BYTES = 1024 * 1024
VALIDATORS = (
    ("repository", "validate_repo.py", "--strict"),
    ("platform", "validate_platform_compat.py", "--require-reference-validator"),
    ("activation", "check_activation_cases.py"),
    ("inventory", "build_inventory.py", "--check"),
)
DERIVED_PATHS = ("researcher/corpus/inventory.json", "researcher/generated/corpus-summary.md")
DERIVATION = ("inventory-derivation", "build_inventory.py", "--write")


def _directory(path: Path, *, private: bool = False) -> Path:
    path = path.absolute()
    if path.resolve() != path or not path.is_dir():
        raise ServiceError("CANDIDATE_UNSAFE_DIRECTORY")
    info = path.stat()
    if private and (info.st_uid != os.getuid() or stat.S_IMODE(info.st_mode) != 0o700):
        raise ServiceError("CANDIDATE_PRIVATE_DIRECTORY_REQUIRED")
    return path


def _environment(scratch: Path) -> dict:
    # No credential, proxy, PYTHONPATH or Git configuration is inherited.
    return {"PATH": str(Path(sys.executable).absolute().parent) + ":/usr/bin:/bin",
            "HOME": str(scratch), "TMPDIR": str(scratch), "LANG": "C.UTF-8",
            "PYTHONDONTWRITEBYTECODE": "1", "GIT_CONFIG_NOSYSTEM": "1",
            "GIT_CONFIG_GLOBAL": os.devnull, "GIT_OPTIONAL_LOCKS": "0"}


def _git(root: Path, *args: str) -> bytes:
    try:
        # A reviewed checkout mounted read-only may belong to a different UID.
        # Trust only this explicit root, never a wildcard or ambient Git config.
        response = subprocess.run(["git", "-c", f"safe.directory={root}",
            "-c", "core.fsmonitor=false", "-c", "core.hooksPath=/dev/null", "-C", str(root), *args],
            stdin=subprocess.DEVNULL, capture_output=True, timeout=10,
            env=_environment(root), check=False)
    except (OSError, subprocess.TimeoutExpired):
        raise ServiceError("CANDIDATE_REPOSITORY_UNAVAILABLE") from None
    if response.returncode or len(response.stdout) > MAX_OUTPUT_BYTES:
        raise ServiceError("CANDIDATE_REPOSITORY_UNAVAILABLE")
    return response.stdout


def _head(root: Path) -> str:
    value = _git(root, "rev-parse", "HEAD").decode("ascii").strip()
    if not re.fullmatch(r"[0-9a-f]{40}", value):
        raise ServiceError("CANDIDATE_REPOSITORY_UNAVAILABLE")
    return value


def _paths(root: Path) -> list[str]:
    raw = _git(root, "ls-files", "--cached", "--others", "--exclude-standard", "-z")
    try:
        paths = sorted(set(raw.decode("utf-8").rstrip("\0").split("\0")))
    except UnicodeError:
        raise ServiceError("CANDIDATE_UNSAFE_SOURCE_PATH") from None
    if not 1 <= len(paths) <= MAX_FILES:
        raise ServiceError("CANDIDATE_SOURCE_LIMIT")
    retained = []
    for value in paths:
        path = PurePosixPath(value)
        if (not value or path.is_absolute() or path.as_posix() != value
                or any(part in {"", ".", "..", ".git"} for part in path.parts)
                or (path.name.startswith(".env") and path.name != ".env.example")
                or path.suffix.lower() in {".pem", ".key", ".p12", ".pfx"}
                or any(part in {".secrets", ".ssh", ".aws", ".azure", ".kube"} for part in path.parts)
                or value.startswith("researcher/runtime/")
                or (value.startswith("researcher/runs/")
                    and not value.startswith("researcher/runs/20260515-035228-executable-autonomous-research-frameworks/")
                    and value != "researcher/runs/README.md")):
            raise ServiceError("CANDIDATE_UNSAFE_SOURCE_PATH")
        candidate = root / value
        if candidate.is_symlink():
            raise ServiceError("CANDIDATE_UNSAFE_SOURCE_PATH")
        # A tracked deletion is part of the current worktree, not a request to
        # resurrect HEAD bytes. The final path-set check detects reappearance.
        if candidate.exists():
            retained.append(value)
    if not retained:
        raise ServiceError("CANDIDATE_SOURCE_LIMIT")
    return retained


def _snapshot(root: Path, paths: list[str], destination: Path | None = None) -> dict:
    entries, total = [], 0
    for relative in paths:
        path = root / relative
        if path.resolve() != path:
            raise ServiceError("CANDIDATE_UNSAFE_SOURCE_PATH")
        body, info = _stable_file_read(path, MAX_FILE_BYTES)
        total += len(body)
        if total > MAX_TREE_BYTES:
            raise ServiceError("CANDIDATE_SOURCE_LIMIT")
        executable = bool(info.st_mode & 0o111)
        entries.append({"path": relative, "sha256": sha256_bytes(body),
                        "size_bytes": len(body), "executable": executable})
        if destination is not None:
            _atomic_write_bytes(destination / relative, body, mode=0o700 if executable else 0o600)
    return {"files": entries, "files_digest": digest(entries), "total_bytes": total}


def _limits():
    resource.setrlimit(resource.RLIMIT_CPU, (60, 60))
    resource.setrlimit(resource.RLIMIT_FSIZE, (MAX_OUTPUT_BYTES, MAX_OUTPUT_BYTES))
    resource.setrlimit(resource.RLIMIT_NOFILE, (128, 128))
    if sys.platform != "darwin":
        resource.setrlimit(resource.RLIMIT_AS, (1536 * 1024 * 1024, 1536 * 1024 * 1024))


def _run_validator(overlay: Path, command: tuple[str, ...], logs: Path) -> dict:
    name, script, *flags = command
    path = overlay / "researcher/scripts" / script
    # Repository scripts use sibling imports. -E/-s suppress ambient Python
    # configuration while retaining that trusted script directory (-I would not).
    argv = [sys.executable, "-E", "-s", "-B", str(path), *flags]
    with tempfile.TemporaryDirectory(prefix="validator-", dir=logs) as temporary:
        scratch = Path(temporary)
        with tempfile.TemporaryFile(dir=scratch) as output:
            try:
                child = subprocess.Popen(argv, cwd=overlay, stdin=subprocess.DEVNULL,
                    stdout=output, stderr=subprocess.STDOUT, env=_environment(scratch),
                    start_new_session=True, preexec_fn=_limits)
            except OSError:
                raise ServiceError("CANDIDATE_VALIDATOR_UNAVAILABLE") from None
            status = "completed"
            try:
                child.wait(timeout=90)
            except subprocess.TimeoutExpired:
                os.killpg(child.pid, signal.SIGKILL)
                child.wait()
                status = "timeout"
            except BaseException:
                if child.poll() is None:
                    os.killpg(child.pid, signal.SIGKILL)
                    child.wait()
                raise
            output.seek(0)
            body = output.read(MAX_OUTPUT_BYTES + 1)
            if len(body) >= MAX_OUTPUT_BYTES:
                status = "output_limit"
            # Private output is bounded; do not reflect it in operator JSON.
            _atomic_write_bytes(logs / (name + ".log"), body[:MAX_OUTPUT_BYTES])
    return {"name": name, "script": "researcher/scripts/" + script,
            "argv": list(flags), "status": status, "exit_code": child.returncode,
            "passed": status == "completed" and child.returncode == 0,
            "output_digest": sha256_bytes(body[:MAX_OUTPUT_BYTES]),
            "output_bytes": min(len(body), MAX_OUTPUT_BYTES)}


@instrument("candidate.review")
def review_candidate(root: Path, destination: Path, *, corpus: dict, evidence: list,
                     output: dict, source_binding: dict, dataset: dict | None = None,
                     model: str | None = None, seed: int = 1,
                     replications: int = 3, max_sessions: int = 144) -> dict:
    """Freeze a supplied native/managed packet; caller supplies independent labels.

    source_binding is exactly {baseline_commit, manifest_digest, result_digest}.
    result_digest hashes output, not a containing provider envelope. This API
    verifies bindings, not the provenance of a caller-supplied native result.
    review_managed additionally verifies the completed managed ledger envelope.
    A fresh destination is mandatory. Partial failed artifacts never count as resume.
    """
    root = _directory(root)
    try:
        encoded = canonicalize({"corpus": corpus, "evidence": evidence, "output": output,
                                "source_binding": source_binding, "dataset": dataset})
        if len(encoded) > 8 * 1024 * 1024:
            raise ValueError("input limit")
        inputs = parse_json_strict(encoded.decode("utf-8"))
        corpus, evidence, output, source_binding, dataset = (
            inputs[key] for key in ("corpus", "evidence", "output", "source_binding", "dataset"))
    except (ValueError, TypeError, UnicodeError, RecursionError):
        raise ServiceError("CANDIDATE_INPUT_LIMIT_OR_ENCODING") from None
    if (not isinstance(source_binding, dict)
            or set(source_binding) != {"baseline_commit", "manifest_digest", "result_digest"}
            or not re.fullmatch(r"[0-9a-f]{40}", str(source_binding["baseline_commit"]))
            or any(not re.fullmatch(r"sha256:[0-9a-f]{64}", str(source_binding[key]))
                   for key in ("manifest_digest", "result_digest"))
            or source_binding["result_digest"] != digest(output)):
        raise ServiceError("CANDIDATE_SOURCE_BINDING_INVALID")
    if _head(root) != source_binding["baseline_commit"]:
        raise ServiceError("CANDIDATE_BASELINE_CHANGED")
    checked = validate_result(canonicalize(output).decode("utf-8"), corpus, evidence)
    proposal = checked["proposal"]
    if proposal is None:
        raise ServiceError("CANDIDATE_PROPOSAL_REQUIRED")
    for document in corpus["documents"]:
        if read_skill(root, document["path"]) != document["text"].encode("utf-8"):
            raise ServiceError("CANDIDATE_BASELINE_CHANGED")
    original, changed = apply_edit(proposal, corpus, checked["critic"]["supported_claim_ids"])
    if dataset is None and model is not None or dataset is not None and model is None:
        raise ServiceError("CANDIDATE_EVAL_INPUTS_REQUIRED")
    # Validate caller-owned labels before creating any artifact; never invent gold.
    if dataset is not None:
        build_plan(dataset, baseline_skill=original, candidate_skill=changed, model=model,
                   seed=seed, replications=replications, max_sessions=max_sessions)
    destination = destination.absolute()
    _directory(destination.parent, private=True)
    if destination.resolve() != destination or destination == root or root in destination.parents:
        raise ServiceError("CANDIDATE_UNSAFE_DESTINATION")
    paths = _paths(root)
    if proposal["path"] not in paths:
        raise ServiceError("CANDIDATE_UNREGISTERED_SKILL")
    destination.mkdir(mode=0o700, exist_ok=False)
    overlay = destination / "overlay"
    overlay.mkdir(mode=0o700)
    baseline = _snapshot(root, paths, overlay)
    indexed = {row["path"]: row for row in baseline["files"]}
    if any(indexed.get(document["path"], {}).get("sha256") != document["sha256"]
           for document in corpus["documents"]):
        raise ServiceError("CANDIDATE_BASELINE_CHANGED")
    draft = destination / "draft"
    _atomic_write_bytes(draft / proposal["path"], changed.encode("utf-8"))
    _, tree_digest = snapshot_tree(draft)
    cas = LocalContentAddressedStore(destination / "candidate-cas")
    freezer = CandidateFreezer(cas, editable_surface_policy=EditableSurfacePolicy(
        policy_id="service-data-only-skill-body-v1",
        roots_by_surface={"skill-body": [proposal["path"]]}))
    candidate = {"schema_version": "1.0.0", "kind": "CandidateArtifact",
        "id": new_typed_id("cand"), "candidate_type": "skill_change",
        "parent_candidate_ids": [],
        "root_production_epoch": "inactive-development:" + source_binding["baseline_commit"],
        "target_editable_surface": "skill-body", "declared_changed_surfaces": [proposal["path"]],
        "artifact_ref_ids": [], "draft_tree_digest": tree_digest,
        "causal_hypothesis_ref": digest(proposal),
        "preservation_obligations": ["frontmatter", "activation-boundary", "integration-boundary"],
        "proposed_by": "research-service-candidate-review", "classification": "private_operational",
        "created_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")}
    receipt = freezer.freeze(candidate, draft, expected_draft_digest=tree_digest)
    authority = ArtifactAuthority("service-candidate-review", frozenset({"artifact.read"}),
                                 frozenset({candidate["id"]}), "private_operational")
    freezer.materialize(receipt, destination / "frozen", authority)
    frozen = read_skill(destination / "frozen", proposal["path"])
    if frozen != changed.encode("utf-8"):
        raise ServiceError("CANDIDATE_FROZEN_BYTES_CHANGED")
    _atomic_write_bytes(overlay / proposal["path"], frozen)
    overlay_manifest = _snapshot(overlay, paths)
    expected = {row["path"]: row for row in baseline["files"]}
    expected[proposal["path"]] = {"path": proposal["path"], "sha256": sha256_bytes(frozen),
                                 "size_bytes": len(frozen), "executable": False}
    if overlay_manifest["files"] != [expected[path] for path in paths]:
        raise ServiceError("CANDIDATE_OVERLAY_DRIFT")
    if not set(DERIVED_PATHS) <= set(paths):
        raise ServiceError("CANDIDATE_DERIVATION_INPUTS_MISSING")
    logs = destination / "validator-logs"
    logs.mkdir(mode=0o700)
    derivation_check = _run_validator(overlay, DERIVATION, logs)
    derived_manifest = _snapshot(overlay, paths)
    derived_index = {row["path"]: row for row in derived_manifest["files"]}
    if any(derived_index[path] != expected[path] for path in paths if path not in DERIVED_PATHS):
        raise ServiceError("CANDIDATE_DERIVATION_UNAUTHORIZED_WRITE")
    files, overlay_tree = snapshot_tree(overlay, maximum_file_bytes=MAX_FILE_BYTES,
        maximum_tree_bytes=MAX_TREE_BYTES, maximum_tree_files=MAX_FILES)
    if {item.path for item in files} != set(paths):
        raise ServiceError("CANDIDATE_DERIVATION_UNAUTHORIZED_WRITE")
    derivation = {"schema": "candidate-derived-inventory/v1", "authority": "none",
        "purpose": "deterministic_inventory_projection_only", "check": derivation_check,
        "before_files_digest": overlay_manifest["files_digest"],
        "after_files_digest": derived_manifest["files_digest"],
        "outputs": [{"path": path, "before": expected[path], "after": derived_index[path]}
                    for path in DERIVED_PATHS], "non_derived_files_unchanged": True,
        "candidate_tree_digest": receipt["tree_digest"], "semantic_claims_assessed": False}
    overlay_manifest = derived_manifest
    checks = [_run_validator(overlay, command, logs) for command in VALIDATORS]
    _, verified_tree = snapshot_tree(overlay, maximum_file_bytes=MAX_FILE_BYTES,
        maximum_tree_bytes=MAX_TREE_BYTES, maximum_tree_files=MAX_FILES)
    if (verified_tree != overlay_tree or _snapshot(overlay, paths) != overlay_manifest or _paths(root) != paths
            or _snapshot(root, paths) != baseline or _head(root) != source_binding["baseline_commit"]):
        raise ServiceError("CANDIDATE_SOURCE_OR_OVERLAY_CHANGED")
    plan = None if dataset is None else build_plan(dataset, baseline_skill=original,
        candidate_skill=frozen.decode("utf-8"), model=model, seed=seed,
        replications=replications, max_sessions=max_sessions)
    core = {"schema": "candidate-review/v1", "authority": "none", "production_ready": False,
        "source_binding": source_binding, "proposal_digest": digest(proposal),
        "corpus_digest": digest(corpus), "evidence_digest": digest(evidence),
        "baseline_files_digest": baseline["files_digest"],
        "overlay_files_digest": overlay_manifest["files_digest"],
        "candidate": candidate, "freeze_receipt": receipt,
        "derivation": derivation, "validators": checks,
        "structural_checks_passed": derivation_check["passed"] and all(row["passed"] for row in checks),
        "evaluation": "planned_not_executed" if plan is not None else "unplanned_missing_dataset",
        "evaluation_plan_digest": plan["plan_digest"] if plan is not None else None,
        "held_out_verified": False, "semantic_effectiveness_measured": False,
        "multi_surface_consistency_assessed": False, "model_calls": 0,
        "disposition": "awaiting_independent_evaluation" if derivation_check["passed"] and all(row["passed"] for row in checks)
                       else "structural_validation_failed"}
    result = {**core, "review_digest": digest(core)}
    for name, value in (("source.json", {"corpus": corpus, "evidence": evidence, "output": output}),
                        ("baseline-files.json", baseline), ("overlay-files.json", overlay_manifest),
                        ("review.json", result)):
        _atomic_write_bytes(destination / name, canonicalize(value))
    if plan is not None:
        _atomic_write_bytes(destination / "evaluation-plan.json", canonicalize(plan))
    return result


@instrument("candidate.review")
def review_managed(root: Path, ledger_directory: Path, destination: Path, **kwargs) -> dict:
    """Load a completed local managed ledger, never contact its remote session."""
    from .agents_runtime import SessionLedger, _read, _validate_packet
    ledger = SessionLedger(ledger_directory)
    with ledger.lock():
        packet, state = ledger.load()
        _validate_packet(packet)
        if state["phase"] != "completed":
            raise ServiceError("CANDIDATE_MANAGED_RESULT_NOT_COMPLETED")
        result = _read(ledger.directory / "result.json")
        if (set(result) != {"schema", "manifest_digest", "session_id", "turn_id", "result",
                            "production_ready", "independent_evaluation"}
                or result["schema"] != "managed-research-result/v1"
                or result["manifest_digest"] != digest(packet)
                or result["session_id"] != state["session_id"]
                or result["production_ready"] is not False
                or result["independent_evaluation"] != "not_run"):
            raise ServiceError("CANDIDATE_MANAGED_RESULT_BINDING_INVALID")
        binding = {"baseline_commit": packet["baseline_commit"],
                   "manifest_digest": digest(packet), "result_digest": digest(result["result"])}
        reviewed = review_candidate(root, destination, corpus=packet["corpus"],
            evidence=packet["evidence"], output=result["result"], source_binding=binding, **kwargs)
        _atomic_write_bytes(destination / "managed-origin.json", canonicalize({
            "schema": "candidate-managed-origin/v1", "authority": "none",
            "packet_digest": digest(packet), "result_envelope_digest": digest(result),
            "review_digest": reviewed["review_digest"], "fixture": packet["fixture"]}))
        return reviewed
