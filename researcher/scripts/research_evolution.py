#!/usr/bin/env python3
"""Portable, zero-call development experiments over frozen packet policies.

This private proposal runner is not an accepted organization state machine.
Candidate files are data, never imported or executed. Run it from any working
directory with an absolute script path; no Codex or model provider is required.
"""

from __future__ import annotations

import argparse
import functools
import importlib.metadata
import json
import stat
import sys
import time
from pathlib import Path
from typing import Any, Mapping, Sequence

if not __package__:
    sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from researcher.scripts import research_pipeline as pipeline
from researcher.scripts import research_sourcing as sourcing
from researcher.scripts.artifact_store import (
    ArtifactAuthority,
    CandidateFreezer,
    EditableSurfacePolicy,
    LocalContentAddressedStore,
    _atomic_write_bytes,
    snapshot_tree,
)
from researcher.scripts.research_experiment import (
    compare_evaluations,
    evaluate_policy,
    validate_dataset,
    validate_policy,
)
from researcher.scripts.schema_contract import (
    canonicalize,
    new_typed_id,
    parse_json_strict,
    sha256_bytes,
)

ROOT = pipeline.ROOT
POLICY_PATH = "researcher/experiments/packet-policy.json"
ARMS = ("baseline", "candidate")
MAX_INPUT_BYTES = 4 * 1024 * 1024


class EvolutionError(ValueError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _require(condition: bool, code: str, message: str) -> None:
    if not condition:
        raise EvolutionError(code, message)


def _public_boundary(function):
    """Expose one stable failure type without leaking source text or paths."""

    @functools.wraps(function)
    def wrapped(*args, **kwargs):
        try:
            return function(*args, **kwargs)
        except EvolutionError:
            raise
        except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
            raise EvolutionError(
                getattr(error, "code", "EXPERIMENT_INVALID"),
                "experiment input or integrity validation failed",
            ) from error

    return wrapped


def _digest(value: Any) -> str:
    return sha256_bytes(canonicalize(value))


def _same(left: Any, right: Any) -> bool:
    # Python equality conflates false/0 and true/1; these are distinct records.
    return canonicalize(left) == canonicalize(right)


def _load(path: Path) -> dict[str, Any]:
    value = parse_json_strict(pipeline._read_bytes(path).decode("utf-8"))
    _require(isinstance(value, dict), "INVALID_RECORD", "record must be an object")
    return value


def _fresh(path: Path, value: Mapping[str, Any]) -> None:
    _atomic_write_bytes(
        path, canonicalize(dict(value)), no_clobber=True, secure_parent=False
    )


class _ExperimentStore(LocalContentAddressedStore):
    """Bound reads for this small data-only experiment, not arbitrary CAS users."""

    def __init__(self, root: Path, *, existing: bool = False):
        if existing:
            # Only _existing_store uses this path after complete preflight.
            # The general CAS constructor mkdir/chmods even existing folders.
            self.root = root
        else:
            super().__init__(root)

    def _load_label(self, digest):
        path = self._metadata_path(digest)
        if not path.exists() and not path.is_symlink():
            return None
        value = _load(path)
        _require(
            set(value) == {"schema_version", "digest", "classification", "size_bytes"}
            and value["digest"] == digest
            and value["schema_version"] == "1.0.0"
            and value["classification"] == "private_operational"
            and type(value["size_bytes"]) is int
            and 0 <= value["size_bytes"] <= MAX_INPUT_BYTES,
            "STORE_CORRUPT",
            "invalid experiment blob metadata",
        )
        return value

    def _read_verified_blob(self, path, expected_digest, expected_size):
        body = pipeline._read_bytes(path)
        _require(
            len(body) == expected_size and sha256_bytes(body) == expected_digest,
            "DIGEST_MISMATCH",
            "experiment blob differs from frozen bytes",
        )
        return body


def _existing_store(output: Path) -> _ExperimentStore:
    """Inspect before constructors, which otherwise create missing directories.

    No cooperative verifier repairs a partial store. The owner-writable local
    filesystem is not an isolation boundary against another process of its UID.
    """
    root = output / "cas"
    for name in ("", "sha256", "metadata", "locks", "freeze-receipts"):
        directory = root / name
        _require(
            directory.is_dir()
            and directory.resolve() == directory
            and stat.S_IMODE(directory.stat().st_mode) == 0o700,
            "STORE_CORRUPT",
            "required experiment store directory is missing or aliased",
        )
    pending, count, total = [root], 0, 0
    while pending:
        directory = pending.pop()
        for path in directory.iterdir():
            count += 1
            _require(
                count <= 64,
                "STORE_CORRUPT",
                "experiment store exceeds file-count limit",
            )
            info = path.lstat()
            if stat.S_ISDIR(info.st_mode):
                pending.append(path)
            else:
                _require(
                    stat.S_ISREG(info.st_mode) and info.st_nlink == 1,
                    "STORE_CORRUPT",
                    "experiment store contains a non-regular or aliased file",
                )
                total += info.st_size
                _require(
                    total <= MAX_INPUT_BYTES + 1024 * 1024,
                    "STORE_CORRUPT",
                    "experiment store exceeds byte limit",
                )
    return _ExperimentStore(root, existing=True)


def _implementation_identity() -> dict[str, Any]:
    files = pipeline._implementation_identity(ROOT)
    for path in sorted((ROOT / "researcher/schemas").rglob("*.json")):
        files[path.relative_to(ROOT).as_posix()] = sha256_bytes(
            pipeline._read_bytes(path)
        )
    return {
        "files": files,
        "python": sys.version,
        "jsonschema": importlib.metadata.version("jsonschema"),
        "canonicalization": "jcs-rfc8785-integer-v1",
        "platform_scope": "local_unix_private_development",
    }


def _surface_policy() -> EditableSurfacePolicy:
    return EditableSurfacePolicy(
        policy_id="local-packet-policy-data-only-v1",
        roots_by_surface={"packet-policy": (POLICY_PATH,)},
        locked_paths=("researcher/scripts", "researcher/schemas", ".git", ".github"),
    )


@_public_boundary
def plan_experiment(
    dataset: dict[str, Any],
    baseline_policy: dict[str, Any],
    *,
    max_evaluations: int,
    max_seconds: int = 60,
) -> dict[str, Any]:
    data = validate_dataset(dataset)
    baseline = validate_policy(baseline_policy)
    _require(
        type(max_evaluations) is int and 1 <= max_evaluations <= 96,
        "INVALID_BUDGET",
        "evaluation ceiling must be an integer from one to 96",
    )
    _require(
        type(max_seconds) is int and 1 <= max_seconds <= 300,
        "INVALID_BUDGET",
        "time ceiling must be an integer from one to 300 seconds",
    )
    count = 2 * sum(len(case["packet_budgets"]) for case in data["cases"])
    _require(
        count <= max_evaluations,
        "BUDGET_EXCEEDED",
        "complete paired population exceeds budget",
    )
    _require(
        len(canonicalize(data)) <= MAX_INPUT_BYTES,
        "INPUT_TOO_LARGE",
        "input exceeds adapter cap",
    )
    return {
        "schema": "private-packet-search-plan/v1",
        "authority": "none",
        "dataset_digest": _digest(data),
        "policies": [
            baseline,
            {"schema": "packet-policy/v1", "compact": not baseline["compact"]},
        ],
        "required_evaluations": count,
        "max_evaluations": max_evaluations,
        "max_seconds": max_seconds,
        "candidate_count": 2,
        "time_budget_scope": "cooperative_run_invocation_before_terminal_publication",
        "evaluation_budget_scope": "unique_policy_case_budget_rows_replays_not_counted",
        "editable_surface_digest": _surface_policy().digest,
        "decision_rule": "paired-lexicographic-coverage-then-bytes-no-regressions/v1",
        "stopping_rule": "evaluate_both_predeclared_data_policies_once",
        "measurement_scope": "finite_development_population_not_semantic_effectiveness",
        "model_calls": 0,
        "paid_calls": 0,
        "network_calls": 0,
    }


@_public_boundary
def dataset_from_campaigns(
    campaign_dirs: Sequence[Path],
    packet_budgets: Sequence[int] = (65536, 131072, 262144),
) -> tuple[dict[str, Any], dict[str, Any]]:
    _require(
        not isinstance(campaign_dirs, (str, bytes)) and 1 <= len(campaign_dirs) <= 8,
        "INVALID_CAMPAIGNS",
        "provide one to eight completed source campaigns",
    )
    cases, bindings = [], []
    for requested in campaign_dirs:
        directory = Path(requested).absolute()
        # The sourcing owner replays the entire campaign envelope, lane intents,
        # query/context bindings and captured bytes. Never call the live runner.
        verified = sourcing.verify_sourcing_campaign(directory)
        manifest, result, packet = (
            verified[key] for key in ("manifest", "result", "packet")
        )
        observations = verified["observations"]
        manifest_digest = _digest(manifest)
        plan = manifest["identity"]["plan"]
        children = [
            {"cache_key": child["cache_key"], "record_sha256": child["record_sha256"]}
            for child in result["children"]
        ]
        case_id = "campaign-" + manifest_digest[7:23]
        # A conservative lexical grouping hint, not proof of independent needs.
        group_id = (
            "need-" + _digest(" ".join(plan["question"].casefold().split()))[7:23]
        )
        cases.append(
            {
                "case_id": case_id,
                "group_id": group_id,
                "question": plan["question"],
                "observations": observations,
                "packet_budgets": list(packet_budgets),
            }
        )
        bindings.append(
            {
                "case_id": case_id,
                "campaign_directory": str(directory),
                "manifest_digest": manifest_digest,
                "result_digest": _digest(result),
                "children": children,
                "packet_digest": _digest(packet),
            }
        )
    dataset = validate_dataset(
        {"schema": "packet-experiment-input/v1", "authority": "none", "cases": cases}
    )
    return dataset, {
        "schema": "private-experiment-input-provenance/v1",
        "authority": "none",
        "mode": "replay_verified_source_campaigns",
        "campaigns": bindings,
        "hidden_holdout": False,
        "independence_verified": False,
    }


def _provenance(
    value: dict[str, Any] | None, dataset: dict[str, Any]
) -> dict[str, Any]:
    if value is None:
        return {
            "schema": "private-experiment-input-provenance/v1",
            "authority": "none",
            "mode": "provided_unverified_development_input",
            "hidden_holdout": False,
            "independence_verified": False,
        }
    _require(
        isinstance(value, dict)
        and value.get("mode") == "replay_verified_source_campaigns",
        "INVALID_PROVENANCE",
        "unsupported input provenance",
    )
    campaigns = value.get("campaigns")
    _require(
        isinstance(campaigns, list) and len(campaigns) == len(dataset["cases"]),
        "INVALID_PROVENANCE",
        "provenance population differs",
    )
    budgets = dataset["cases"][0]["packet_budgets"]
    _require(
        all(case["packet_budgets"] == budgets for case in dataset["cases"]),
        "INVALID_PROVENANCE",
        "campaign import must use a common paired budget set",
    )
    verified, receipt = dataset_from_campaigns(
        [Path(item["campaign_directory"]) for item in campaigns], budgets
    )
    _require(
        _same(verified, dataset) and _same(receipt, value),
        "EVIDENCE_MISMATCH",
        "claimed provenance does not replay",
    )
    return receipt


def _store_dataset(
    store: LocalContentAddressedStore, dataset: dict[str, Any]
) -> dict[str, Any]:
    blob = store.put_bytes(canonicalize(dataset), classification="private_operational")
    return {"digest": blob.digest, "size_bytes": blob.size_bytes}


def _read_dataset(
    store: LocalContentAddressedStore, reference: dict[str, Any]
) -> dict[str, Any]:
    _require(
        set(reference) == {"digest", "size_bytes"},
        "INVALID_RECORD",
        "invalid input blob reference",
    )
    authority = ArtifactAuthority(
        "local-fixed-evaluator",
        frozenset({"artifact.read"}),
        frozenset({reference["digest"]}),
        "private_operational",
    )
    body = store.get_bytes(reference["digest"], authority)
    _require(
        len(body) == reference["size_bytes"] <= MAX_INPUT_BYTES,
        "INPUT_MISMATCH",
        "frozen input size differs",
    )
    return validate_dataset(parse_json_strict(body.decode("utf-8")))


def _policy_from_freeze(
    store: LocalContentAddressedStore,
    freezer: CandidateFreezer,
    outcome: dict[str, Any],
) -> dict[str, Any]:
    candidate, receipt = outcome["candidate"], outcome["freeze_receipt"]
    freezer.registry.validate(candidate)
    freezer.registry.validate(receipt)
    _require(
        receipt["candidate_id"] == candidate["id"]
        and receipt["candidate_record_digest"] == _digest(candidate)
        and receipt["tree_digest"] == candidate["draft_tree_digest"]
        and receipt["freeze_policy_digest"] == freezer.freeze_policy_digest
        and receipt["schema_registry_digest"]
        == sha256_bytes(pipeline._read_bytes(freezer.registry.path)),
        "FREEZE_MISMATCH",
        "candidate receipt binding differs",
    )
    _require(
        candidate["target_editable_surface"] == "packet-policy"
        and candidate["declared_changed_surfaces"] == [POLICY_PATH]
        and len(receipt["entries"]) == 1
        and receipt["entries"][0]["path"] == POLICY_PATH
        and receipt["entries"][0]["executable"] is False,
        "SURFACE_DENIED",
        "candidate is not the single data-only policy surface",
    )
    stored_receipt = _load(freezer._receipt_path(candidate["id"]))
    _require(
        _same(stored_receipt, receipt),
        "FREEZE_MISMATCH",
        "stored freeze receipt differs",
    )
    authority = ArtifactAuthority(
        "local-fixed-evaluator",
        frozenset({"artifact.read"}),
        frozenset({candidate["id"]}),
        "private_operational",
    )
    entry = receipt["entries"][0]
    body = store.get_bytes(entry["digest"], authority, resource=candidate["id"])
    _require(
        len(body) == entry["size_bytes"] <= 1024,
        "SURFACE_DENIED",
        "policy exceeds data limit",
    )
    return validate_policy(parse_json_strict(body.decode("utf-8")))


def _check_outcome(
    output: Path,
    manifest: dict[str, Any],
    store: LocalContentAddressedStore,
    freezer: CandidateFreezer,
    dataset: dict[str, Any],
    arm: str,
) -> dict[str, Any]:
    index = ARMS.index(arm)
    directory = output / "attempts" / arm
    intent = _load(directory / "intent.json")
    outcome = _load(directory / "outcome.json")
    expected_intent = {
        "schema": "private-packet-attempt-intent/v1",
        "authority": "none",
        "manifest_digest": _digest(manifest),
        "arm": arm,
        "policy_digest": _digest(manifest["identity"]["plan"]["policies"][index]),
    }
    _require(
        _same(intent, expected_intent),
        "ATTEMPT_MISMATCH",
        "attempt intent binding differs",
    )
    _require(
        set(outcome)
        == {
            "schema",
            "authority",
            "manifest_digest",
            "arm",
            "candidate",
            "freeze_receipt",
            "evaluation",
            "elapsed_ms",
        }
        and outcome["schema"] == "private-packet-attempt-outcome/v1"
        and outcome["authority"] == "none"
        and outcome["manifest_digest"] == _digest(manifest)
        and outcome["arm"] == arm
        and type(outcome["elapsed_ms"]) is int
        and 0
        <= outcome["elapsed_ms"]
        <= manifest["identity"]["plan"]["max_seconds"] * 1000,
        "ATTEMPT_MISMATCH",
        "attempt outcome binding differs",
    )
    policy = _policy_from_freeze(store, freezer, outcome)
    _require(
        policy == manifest["identity"]["plan"]["policies"][index],
        "POLICY_MISMATCH",
        "frozen candidate differs from planned policy",
    )
    _require(
        outcome["candidate"]["root_production_epoch"]
        == "local-experiment:" + _digest(manifest)
        and outcome["candidate"]["causal_hypothesis_ref"]
        == "packet-coverage:" + _digest(manifest),
        "FREEZE_MISMATCH",
        "candidate local lineage differs",
    )
    files, tree_digest = snapshot_tree(
        directory / "materialized",
        maximum_file_bytes=1024,
        maximum_tree_bytes=1024,
        maximum_tree_files=1,
    )
    _require(
        tree_digest == outcome["freeze_receipt"]["tree_digest"]
        and len(files) == 1
        and files[0].path == POLICY_PATH,
        "FREEZE_MISMATCH",
        "materialized candidate differs from frozen bytes",
    )
    _require(
        _same(outcome["evaluation"], evaluate_policy(policy, dataset)),
        "EVALUATION_MISMATCH",
        "saved evaluation does not replay",
    )
    return outcome


def _report(
    manifest: dict[str, Any], outcomes: list[dict[str, Any]], dataset: dict[str, Any]
) -> dict[str, Any]:
    comparison = compare_evaluations(
        outcomes[0]["evaluation"], outcomes[1]["evaluation"], dataset=dataset
    )
    disposition = comparison["decision"]
    status = "proposal_ready" if disposition == "candidate_dominates" else disposition
    proposal = None
    if status == "proposal_ready":
        proposal = {
            "target_path": POLICY_PATH,
            "baseline_policy": manifest["identity"]["plan"]["policies"][0],
            "candidate_policy": manifest["identity"]["plan"]["policies"][1],
            "candidate_id": outcomes[1]["candidate"]["id"],
            "freeze_receipt_digest": _digest(outcomes[1]["freeze_receipt"]),
            "apply_enabled": False,
        }
    return {
        "schema": "private-packet-search-result/v1",
        "authority": "none",
        "status": status,
        "manifest_digest": _digest(manifest),
        "comparison": comparison,
        "attempts": [
            {"arm": value["arm"], "outcome_digest": _digest(value)}
            for value in outcomes
        ],
        "proposal": proposal,
        "source_provenance": manifest["source_provenance"],
        "model_calls": 0,
        "paid_calls": 0,
        "network_calls": 0,
        "production_ready": False,
        "semantic_effectiveness": False,
        "independence_verified": False,
    }


def _markdown(result: dict[str, Any]) -> bytes:
    return (
        "# Frozen packet-policy experiment\n\n"
        f"Disposition: `{result['status']}`.\n\n"
        "This is a finite development experiment, not semantic effectiveness or an accepted promotion.\n\n"
        f"Manifest: `{result['manifest_digest']}`. Both predeclared policies were evaluated.\n\n"
        "Candidate bytes were frozen and materialized; only strict JSON data was read. No candidate code, "
        "network request, paid API, repository edit or production action was executed.\n\n"
        "See `result.json` for the complete paired comparison and `attempts/*/outcome.json` for "
        "all per-case results, including failures. Candidate authors did not supply scores. "
        "All fixtures were development-visible; separate evaluator identities and hidden holdouts were not used.\n\n"
        "A proposal is inert. Applying or publishing it requires separate review and authorization.\n"
    ).encode()


def _read_manifest(output: Path) -> dict[str, Any]:
    manifest = _load(output / "manifest.json")
    _require(
        set(manifest)
        == {
            "schema",
            "authority",
            "created_at",
            "identity",
            "dataset_blob",
            "source_provenance",
        }
        and manifest["schema"] == "private-packet-search-manifest/v1"
        and manifest["authority"] == "none",
        "INVALID_MANIFEST",
        "invalid private experiment manifest",
    )
    _require(
        _same(manifest["identity"]["code_identity"], _implementation_identity()),
        "IDENTITY_CHANGED",
        "evaluator, dependency or runtime identity changed",
    )
    return manifest


def _verify_locked(output: Path) -> dict[str, Any]:
    started = time.monotonic_ns()
    manifest = _read_manifest(output)
    store = _existing_store(output)
    dataset = _read_dataset(store, manifest["dataset_blob"])
    plan = manifest["identity"]["plan"]
    expected_plan = plan_experiment(
        dataset,
        plan["policies"][0],
        max_evaluations=plan["max_evaluations"],
        max_seconds=plan["max_seconds"],
    )
    _require(
        _same(plan, expected_plan)
        and manifest["identity"]["dataset_digest"] == _digest(dataset)
        and manifest["identity"]["provenance_digest"]
        == _digest(manifest["source_provenance"]),
        "INPUT_MISMATCH",
        "frozen experiment inputs differ",
    )
    provenance = manifest["source_provenance"]
    _require(
        _same(
            _provenance(
                None
                if provenance["mode"] == "provided_unverified_development_input"
                else provenance,
                dataset,
            ),
            provenance,
        ),
        "EVIDENCE_MISMATCH",
        "input provenance does not replay",
    )

    def check_deadline():
        _require(
            time.monotonic_ns() - started <= plan["max_seconds"] * 1_000_000_000,
            "BUDGET_EXCEEDED",
            "cooperative replay deadline exceeded",
        )

    check_deadline()
    freezer = CandidateFreezer(
        store, editable_surface_policy=_surface_policy(), initialize=False
    )
    outcomes = []
    for arm in ARMS:
        outcomes.append(_check_outcome(output, manifest, store, freezer, dataset, arm))
        check_deadline()
    expected = _report(manifest, outcomes, dataset)
    _require(
        _same(_load(output / "result.json"), expected),
        "RESULT_MISMATCH",
        "result does not replay",
    )
    _require(
        pipeline._read_bytes(output / "report.md") == _markdown(expected),
        "RESULT_MISMATCH",
        "report text does not match result",
    )
    _require(
        _implementation_identity() == manifest["identity"]["code_identity"],
        "IDENTITY_CHANGED",
        "evaluator changed during replay",
    )
    check_deadline()
    return expected


@_public_boundary
def verify_experiment(runtime_dir: Path) -> dict[str, Any]:
    output = Path(runtime_dir).absolute()
    _require(
        output.is_dir() and output.resolve() == output,
        "INVALID_RUNTIME",
        "experiment directory is missing or aliased",
    )
    with sourcing._existing_run_lock(output):
        return _verify_locked(output)


@_public_boundary
def run_experiment(
    runtime_dir: Path,
    dataset: dict[str, Any],
    baseline_policy: dict[str, Any],
    *,
    max_evaluations: int,
    max_seconds: int = 60,
    provenance: dict[str, Any] | None = None,
) -> dict[str, Any]:
    started = time.monotonic_ns()
    plan = plan_experiment(
        dataset,
        baseline_policy,
        max_evaluations=max_evaluations,
        max_seconds=max_seconds,
    )

    def check_deadline():
        _require(
            time.monotonic_ns() - started <= max_seconds * 1_000_000_000,
            "BUDGET_EXCEEDED",
            "cooperative experiment deadline exceeded",
        )

    data = validate_dataset(dataset)
    source_provenance = _provenance(provenance, data)
    identity = {
        "plan": plan,
        "dataset_digest": _digest(data),
        "provenance_digest": _digest(source_provenance),
        "code_identity": _implementation_identity(),
    }
    check_deadline()
    output = sourcing._private(Path(runtime_dir).absolute())
    if (output / "manifest.json").exists():
        pipeline._read_bytes(output / ".run.lock")
    with pipeline._run_lock(output):
        if (output / "manifest.json").exists():
            manifest = _read_manifest(output)
            _require(
                _same(manifest["identity"], identity)
                and _same(manifest["source_provenance"], source_provenance),
                "IDENTITY_CHANGED",
                "resume inputs differ from frozen experiment",
            )
            if (output / "result.json").exists():
                result = _verify_locked(output)
                check_deadline()
                return result
        else:
            _require(
                {item.name for item in output.iterdir()} <= {".run.lock"},
                "UNKNOWN_OUTCOME",
                "unbound partial initialization requires inspection",
            )
            store = _ExperimentStore(output / "cas")
            CandidateFreezer(store, editable_surface_policy=_surface_policy())
            manifest = {
                "schema": "private-packet-search-manifest/v1",
                "authority": "none",
                "created_at": pipeline._now(),
                "identity": identity,
                "dataset_blob": _store_dataset(store, data),
                "source_provenance": source_provenance,
            }
            _fresh(output / "manifest.json", manifest)
        store = _existing_store(output)
        frozen_data = _read_dataset(store, manifest["dataset_blob"])
        _require(_same(frozen_data, data), "INPUT_MISMATCH", "frozen dataset differs")
        freezer = CandidateFreezer(
            store, editable_surface_policy=_surface_policy(), initialize=False
        )
        attempts = sourcing._private(output / "attempts")
        outcomes = []
        elapsed_ms = 0
        for arm, policy in zip(ARMS, plan["policies"], strict=True):
            check_deadline()
            directory = sourcing._private(attempts / arm)
            if (directory / "outcome.json").exists():
                outcome = _check_outcome(
                    output, manifest, store, freezer, frozen_data, arm
                )
                outcomes.append(outcome)
                elapsed_ms += outcome["elapsed_ms"]
                check_deadline()
                continue
            _require(
                not (directory / "intent.json").exists(),
                "UNKNOWN_OUTCOME",
                "attempt has no terminal outcome; inspection required before any repeat",
            )
            _require(
                not list(directory.iterdir()),
                "UNKNOWN_OUTCOME",
                "partial attempt has no intent",
            )
            _require(
                elapsed_ms < max_seconds * 1000,
                "BUDGET_EXCEEDED",
                "experiment time ceiling reached",
            )
            _require(
                _implementation_identity() == identity["code_identity"],
                "IDENTITY_CHANGED",
                "evaluator changed before candidate execution",
            )
            _fresh(
                directory / "intent.json",
                {
                    "schema": "private-packet-attempt-intent/v1",
                    "authority": "none",
                    "manifest_digest": _digest(manifest),
                    "arm": arm,
                    "policy_digest": _digest(policy),
                },
            )
            begin = time.monotonic_ns()
            draft = sourcing._private(directory / "draft")
            parent = sourcing._private(
                sourcing._private(draft / "researcher") / "experiments"
            )
            _fresh(parent / "packet-policy.json", policy)
            _, tree_digest = snapshot_tree(
                draft,
                maximum_file_bytes=1024,
                maximum_tree_bytes=1024,
                maximum_tree_files=1,
            )
            candidate = {
                "schema_version": "1.0.0",
                "id": new_typed_id("cand"),
                "kind": "CandidateArtifact",
                "candidate_type": "harness_change",
                "parent_candidate_ids": [],
                "root_production_epoch": "local-experiment:" + _digest(manifest),
                "target_editable_surface": "packet-policy",
                "declared_changed_surfaces": [POLICY_PATH],
                "artifact_ref_ids": [],
                "draft_tree_digest": tree_digest,
                "causal_hypothesis_ref": "packet-coverage:" + _digest(manifest),
                "preservation_obligations": [
                    "exact source text",
                    "complete provenance",
                    "fixed paired population",
                ],
                "proposed_by": "bounded-boolean-policy-enumerator",
                "classification": "private_operational",
                "created_at": manifest["created_at"],
            }
            receipt = freezer.freeze(
                candidate, draft, expected_draft_digest=tree_digest
            )
            authority = ArtifactAuthority(
                "local-fixed-evaluator",
                frozenset({"artifact.read"}),
                frozenset({candidate["id"]}),
                "private_operational",
            )
            freezer.materialize(receipt, directory / "materialized", authority)
            materialized_policy = validate_policy(
                _load(directory / "materialized" / POLICY_PATH)
            )
            _require(
                materialized_policy == policy,
                "POLICY_MISMATCH",
                "materialized policy differs",
            )
            evaluation = evaluate_policy(materialized_policy, frozen_data)
            check_deadline()
            duration = (time.monotonic_ns() - begin) // 1_000_000
            elapsed_ms += duration
            _require(
                elapsed_ms <= max_seconds * 1000,
                "BUDGET_EXCEEDED",
                "experiment time ceiling exceeded",
            )
            _require(
                _implementation_identity() == identity["code_identity"],
                "IDENTITY_CHANGED",
                "evaluator changed during candidate execution",
            )
            outcome = {
                "schema": "private-packet-attempt-outcome/v1",
                "authority": "none",
                "manifest_digest": _digest(manifest),
                "arm": arm,
                "candidate": candidate,
                "freeze_receipt": receipt,
                "evaluation": evaluation,
                "elapsed_ms": duration,
            }
            _fresh(directory / "outcome.json", outcome)
            outcomes.append(outcome)
            print(
                json.dumps(
                    {
                        "progress": "policy_evaluated",
                        "arm": arm,
                        "completed_policies": len(outcomes),
                        "planned_policies": 2,
                    }
                ),
                file=sys.stderr,
                flush=True,
            )
        # Re-read the frozen surface and replay both outputs before publishing.
        # All replay work shares this invocation's cooperative time ceiling.
        outcomes = [
            _check_outcome(output, manifest, store, freezer, frozen_data, arm)
            for arm in ARMS
        ]
        check_deadline()
        result = _report(manifest, outcomes, frozen_data)
        _require(
            _implementation_identity() == identity["code_identity"],
            "IDENTITY_CHANGED",
            "evaluator changed before report",
        )
        check_deadline()
        # Result is published last. A crash between these writes cannot expose a
        # result with missing text, and resume verifies the prior text exactly.
        if (output / "report.md").exists():
            _require(
                pipeline._read_bytes(output / "report.md") == _markdown(result),
                "RESULT_MISMATCH",
                "partial report differs",
            )
        else:
            _atomic_write_bytes(
                output / "report.md",
                _markdown(result),
                no_clobber=True,
                secure_parent=False,
            )
        _fresh(output / "result.json", result)
        return result


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)
    for name in ("plan", "run"):
        command = sub.add_parser(name)
        inputs = command.add_mutually_exclusive_group(required=True)
        inputs.add_argument(
            "--input",
            type=Path,
            help="unverified development dataset; not accepted source evidence",
        )
        inputs.add_argument(
            "--campaign",
            type=Path,
            action="append",
            help="completed source campaign to replay",
        )
        command.add_argument("--baseline-policy", type=Path, required=True)
        command.add_argument("--max-evaluations", type=int, required=True)
        command.add_argument("--max-seconds", type=int, default=60)
        if name == "run":
            command.add_argument("--runtime-dir", type=Path, required=True)
    verify = sub.add_parser("verify")
    verify.add_argument("--runtime-dir", type=Path, required=True)
    args = parser.parse_args(argv)
    try:
        if args.command == "verify":
            result = verify_experiment(args.runtime_dir)
        else:
            if args.campaign:
                dataset, provenance = dataset_from_campaigns(args.campaign)
            else:
                dataset, provenance = _load(args.input.absolute()), None
            baseline = _load(args.baseline_policy.absolute())
            if args.command == "plan":
                result = plan_experiment(
                    dataset,
                    baseline,
                    max_evaluations=args.max_evaluations,
                    max_seconds=args.max_seconds,
                )
            else:
                result = run_experiment(
                    args.runtime_dir,
                    dataset,
                    baseline,
                    max_evaluations=args.max_evaluations,
                    max_seconds=args.max_seconds,
                    provenance=provenance,
                )
        print(json.dumps(result, ensure_ascii=True, indent=2))
        return 0
    except (ValueError, OSError, KeyError, TypeError, RuntimeError) as error:
        print(
            json.dumps(
                {
                    "status": "failed",
                    "authority": "none",
                    "production_ready": False,
                    "code": getattr(error, "code", "EXPERIMENT_INVALID"),
                }
            ),
            file=sys.stderr,
        )
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
