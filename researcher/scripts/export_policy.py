#!/usr/bin/env python3
"""Allowlisted, deterministic projections across the public/private boundary."""

from __future__ import annotations

import base64
import json
import os
import re
import shutil
import stat
import tempfile
import unicodedata
from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Mapping

try:
    import yaml
except ImportError as exc:  # pragma: no cover - CI installs requirements-dev.txt
    raise RuntimeError("PyYAML is required to load governance/export-policy.yaml") from exc

try:
    from build_inventory import (
        DuplicateKeyError,
        atomic_write_text,
        parse_json_text,
        pretty_json,
        record_digest,
        sha256_bytes,
    )
except ModuleNotFoundError:  # Imported as researcher.scripts.export_policy.
    from researcher.scripts.build_inventory import (
        DuplicateKeyError,
        atomic_write_text,
        parse_json_text,
        pretty_json,
        record_digest,
        sha256_bytes,
    )


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_POLICY_PATH = ROOT / "governance" / "export-policy.yaml"
SCHEMA_VERSION = "1.0.0"
EXPORT_ID = re.compile(r"^export_[0-9A-Za-z_-]+$")
ENTRY_ID = re.compile(r"^entry_[0-9A-Za-z_-]+$")
PROJECTION_ID = re.compile(r"^proj_[0-9A-Za-z_-]+$")
PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----")
AUTHORIZATION_PATTERN = re.compile(r"(?i)authorization\s*:\s*(?:bearer|basic)\s+\S+")
SIGNED_URL_PATTERN = re.compile(r"(?i)[?&](?:x-amz-signature|signature|access_token)=[^&\s]+")
PRIVATE_PATH_PATTERN = re.compile(r"(?:/Users/[^/\s]+/|/home/[^/\s]+/|[A-Za-z]:\\Users\\[^\\\s]+\\)")


class ExportBoundaryError(ValueError):
    """Typed failure that never includes matched secret content."""

    def __init__(self, code: str, message: str) -> None:
        super().__init__(f"{code}: {message}")
        self.code = code
        self.safe_message = message


@dataclass(frozen=True)
class StableFile:
    body: bytes
    digest: str
    size_bytes: int


def _require_exact_keys(value: Mapping[str, Any], allowed: set[str], location: str) -> None:
    unknown = set(value) - allowed
    missing = allowed - set(value)
    if unknown:
        raise ExportBoundaryError("UNKNOWN_FIELD", f"{location} has unknown fields: {sorted(unknown)}")
    if missing:
        raise ExportBoundaryError("UNKNOWN_FIELD", f"{location} is missing fields: {sorted(missing)}")


def _require_nonempty_string(value: Any, location: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ExportBoundaryError("UNKNOWN_FIELD", f"{location} must be a non-empty string")
    return value


def normalize_relative_path(value: Any, location: str) -> str:
    raw = _require_nonempty_string(value, location)
    if "\x00" in raw or "\\" in raw:
        raise ExportBoundaryError("PATH_ESCAPE", f"{location} must use normalized POSIX syntax")
    if unicodedata.normalize("NFC", raw) != raw:
        raise ExportBoundaryError("PATH_COLLISION", f"{location} must use NFC Unicode")
    path = PurePosixPath(raw)
    if path.is_absolute() or any(part in {"", ".", ".."} for part in path.parts):
        raise ExportBoundaryError("PATH_ESCAPE", f"{location} must remain relative")
    return path.as_posix()


def _walk_without_symlinks(root: Path, relative: str) -> Path:
    if root.is_symlink():
        raise ExportBoundaryError("PATH_ESCAPE", "private root must not be a symlink")
    current = root.resolve(strict=True)
    if not current.is_dir():
        raise ExportBoundaryError("PATH_ESCAPE", "private root must be a regular directory")
    for part in PurePosixPath(relative).parts:
        current = current / part
        if current.is_symlink():
            raise ExportBoundaryError("PATH_ESCAPE", "source path contains a symlink")
    try:
        resolved = current.resolve(strict=True)
        resolved.relative_to(root.resolve(strict=True))
    except (OSError, ValueError) as exc:
        raise ExportBoundaryError("PATH_ESCAPE", "source is unavailable or escapes its private root") from exc
    return resolved


def read_stable_file(root: Path, relative: str, max_bytes: int) -> StableFile:
    path = _walk_without_symlinks(root, relative)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        raise ExportBoundaryError("PATH_ESCAPE", "source could not be opened safely") from exc
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode):
            raise ExportBoundaryError("PATH_ESCAPE", "source must be a regular file")
        if before.st_nlink != 1:
            raise ExportBoundaryError("PATH_ESCAPE", "source must not be hardlinked")
        if before.st_size > max_bytes:
            raise ExportBoundaryError("SOURCE_TOO_LARGE", "source exceeds policy byte limit")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(64 * 1024, max_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > max_bytes:
                raise ExportBoundaryError("SOURCE_TOO_LARGE", "source exceeds policy byte limit")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    identity_before = (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns)
    identity_after = (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns)
    if identity_before != identity_after or total != after.st_size:
        raise ExportBoundaryError("SOURCE_CHANGED", "source changed while it was being read")
    body = b"".join(chunks)
    return StableFile(body=body, digest=sha256_bytes(body), size_bytes=len(body))


class ExportPolicy:
    def __init__(self, document: Mapping[str, Any], digest: str, source: Path) -> None:
        self.document = dict(document)
        self.digest = digest
        self.source = source
        self.version = _require_nonempty_string(document.get("policy_version"), "policy_version")
        self._validate()

    @classmethod
    def load(cls, path: Path = DEFAULT_POLICY_PATH) -> "ExportPolicy":
        try:
            raw = path.read_bytes()
            document = yaml.safe_load(raw.decode("utf-8"))
        except (OSError, UnicodeError, yaml.YAMLError) as exc:
            raise ExportBoundaryError("POLICY_INVALID", "export policy could not be loaded") from exc
        if not isinstance(document, dict):
            raise ExportBoundaryError("POLICY_INVALID", "export policy root must be a mapping")
        return cls(document, sha256_bytes(raw), path.resolve())

    @property
    def classifications(self) -> Mapping[str, Any]:
        return self.document["classifications"]

    @property
    def transforms(self) -> Mapping[str, Any]:
        return self.document["transforms"]

    @property
    def artifact_kinds(self) -> Mapping[str, Any]:
        return self.document["artifact_kinds"]

    @property
    def max_source_bytes(self) -> int:
        return int(self.document.get("max_source_bytes", 1_500_000))

    def _validate(self) -> None:
        required = {
            "schema_version",
            "policy_version",
            "default_export",
            "classifications",
            "public_output_classifications",
            "artifact_kinds",
            "transforms",
            "forbidden_public_fields",
            "allowed_public_digest_fields",
            "public_manifest_fields",
            "public_manifest_entry_fields",
            "supplementary_detectors",
            "correction_policy",
        }
        optional = {"max_source_bytes"}
        unknown = set(self.document) - required - optional
        missing = required - set(self.document)
        if unknown or missing:
            raise ExportBoundaryError(
                "POLICY_INVALID", f"policy fields differ: unknown={sorted(unknown)} missing={sorted(missing)}"
            )
        if self.document["schema_version"] != SCHEMA_VERSION:
            raise ExportBoundaryError("POLICY_INVALID", "unsupported export policy schema")
        if self.document["default_export"] != "deny":
            raise ExportBoundaryError("POLICY_INVALID", "default_export must be deny")
        if not isinstance(self.document.get("max_source_bytes"), int) or self.max_source_bytes < 1:
            raise ExportBoundaryError("POLICY_INVALID", "max_source_bytes must be a positive integer")
        if not isinstance(self.classifications, dict) or not self.classifications:
            raise ExportBoundaryError("POLICY_INVALID", "classifications must be a non-empty mapping")
        if self.classifications.get("secret_reference", {}).get("exportable") is not False:
            raise ExportBoundaryError("POLICY_INVALID", "secret_reference must not be exportable")
        public_classes = self.document["public_output_classifications"]
        if not isinstance(public_classes, list) or set(public_classes) - set(self.classifications):
            raise ExportBoundaryError("POLICY_INVALID", "public output classifications are invalid")
        if not isinstance(self.transforms, dict) or not isinstance(self.artifact_kinds, dict):
            raise ExportBoundaryError("POLICY_INVALID", "transforms and artifact_kinds must be mappings")
        for kind, descriptor in self.artifact_kinds.items():
            if not isinstance(descriptor, dict):
                raise ExportBoundaryError("POLICY_INVALID", f"artifact kind {kind} must be a mapping")
            normalize_relative_path(descriptor.get("output_prefix"), f"artifact_kinds.{kind}.output_prefix")
            transform_ids = descriptor.get("allowed_transforms")
            if not isinstance(transform_ids, list) or not transform_ids:
                raise ExportBoundaryError("POLICY_INVALID", f"artifact kind {kind} needs transforms")
            if set(transform_ids) - set(self.transforms):
                raise ExportBoundaryError("POLICY_INVALID", f"artifact kind {kind} references unknown transform")
        for transform_id, descriptor in self.transforms.items():
            if not isinstance(descriptor, dict):
                raise ExportBoundaryError("POLICY_INVALID", f"transform {transform_id} must be a mapping")
            source_classes = descriptor.get("source_classifications")
            if not isinstance(source_classes, list) or set(source_classes) - set(self.classifications):
                raise ExportBoundaryError("POLICY_INVALID", f"transform {transform_id} has invalid source classes")
            for field_name in ["required_source_fields", "allowed_source_fields", "output_fields"]:
                fields = descriptor.get(field_name)
                if not isinstance(fields, list) or not all(isinstance(field, str) for field in fields):
                    raise ExportBoundaryError("POLICY_INVALID", f"transform {transform_id}.{field_name} is invalid")
                if len(fields) != len(set(fields)):
                    raise ExportBoundaryError(
                        "POLICY_INVALID", f"transform {transform_id}.{field_name} contains duplicates"
                    )
            if set(descriptor["required_source_fields"]) - set(descriptor["allowed_source_fields"]):
                raise ExportBoundaryError(
                    "POLICY_INVALID", f"transform {transform_id} required fields are not allowed"
                )
            required_output = {
                "schema_version",
                "id",
                "kind",
                "classification",
                "retention",
            } | set(descriptor["required_source_fields"])
            if required_output - set(descriptor["output_fields"]):
                raise ExportBoundaryError("POLICY_INVALID", f"transform {transform_id} omits required output fields")
            if set(descriptor["output_fields"]) & set(self.document["forbidden_public_fields"]):
                raise ExportBoundaryError("POLICY_INVALID", f"transform {transform_id} emits forbidden fields")

    def validate_route(self, source_classification: str, artifact_kind: str, transform_id: str) -> None:
        classification = self.classifications.get(source_classification)
        if not isinstance(classification, dict) or classification.get("exportable") is not True:
            raise ExportBoundaryError("CLASSIFICATION_DENIED", "source classification cannot be exported")
        kind = self.artifact_kinds.get(artifact_kind)
        if not isinstance(kind, dict):
            raise ExportBoundaryError("UNKNOWN_ARTIFACT_KIND", "artifact kind is not allowlisted")
        if transform_id not in kind["allowed_transforms"]:
            raise ExportBoundaryError("UNAPPROVED_TRANSFORM", "transform is not allowed for artifact kind")
        transform = self.transforms.get(transform_id)
        if not isinstance(transform, dict) or source_classification not in transform["source_classifications"]:
            raise ExportBoundaryError("CLASSIFICATION_DENIED", "transform is not allowed for source class")


REQUEST_FIELDS = {"schema_version", "id", "kind", "classification", "retention", "entries"}
REQUEST_ENTRY_FIELDS = {
    "entry_id",
    "projection_id",
    "source_path",
    "source_classification",
    "artifact_kind",
    "transformation_id",
    "output_path",
}
PLAN_FIELDS = {
    "schema_version",
    "id",
    "kind",
    "state",
    "classification",
    "retention",
    "policy_version",
    "policy_digest",
    "request_digest",
    "entries",
}
PLAN_ENTRY_FIELDS = REQUEST_ENTRY_FIELDS | {"source_digest", "source_size_bytes"}


def _parse_json_object(body: bytes, location: str) -> dict[str, Any]:
    try:
        value = parse_json_text(body.decode("utf-8"))
    except (UnicodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        raise ExportBoundaryError("SOURCE_INVALID", f"{location} must be strict UTF-8 JSON") from exc
    if not isinstance(value, dict):
        raise ExportBoundaryError("SOURCE_INVALID", f"{location} must be a JSON object")
    return value


def _validate_ids_and_paths(entries: list[dict[str, Any]], policy: ExportPolicy) -> None:
    entry_ids: set[str] = set()
    projection_ids: set[str] = set()
    output_paths: set[str] = set()
    collision_keys: set[str] = set()
    for index, entry in enumerate(entries):
        entry_id = _require_nonempty_string(entry.get("entry_id"), f"entries[{index}].entry_id")
        projection_id = _require_nonempty_string(
            entry.get("projection_id"), f"entries[{index}].projection_id"
        )
        if not ENTRY_ID.fullmatch(entry_id) or not PROJECTION_ID.fullmatch(projection_id):
            raise ExportBoundaryError("INVALID_ID", "export entry or projection ID has invalid form")
        if entry_id in entry_ids or projection_id in projection_ids:
            raise ExportBoundaryError("DUPLICATE_ID", "export entry and projection IDs must be unique")
        entry_ids.add(entry_id)
        projection_ids.add(projection_id)
        output_path = normalize_relative_path(entry.get("output_path"), f"entries[{index}].output_path")
        if output_path == "export-manifest.json":
            raise ExportBoundaryError("PATH_COLLISION", "output path collides with export manifest")
        collision_key = unicodedata.normalize("NFC", output_path).casefold()
        if output_path in output_paths or collision_key in collision_keys:
            raise ExportBoundaryError("PATH_COLLISION", "output paths collide after normalization")
        output_paths.add(output_path)
        collision_keys.add(collision_key)
        kind = entry.get("artifact_kind")
        if kind not in policy.artifact_kinds:
            raise ExportBoundaryError("UNKNOWN_ARTIFACT_KIND", "artifact kind is not allowlisted")
        prefix = policy.artifact_kinds[kind]["output_prefix"]
        if not output_path.startswith(prefix):
            raise ExportBoundaryError("UNAPPROVED_DESTINATION", "output path is outside artifact prefix")
        if not output_path.endswith(".json"):
            raise ExportBoundaryError("UNAPPROVED_DESTINATION", "current transforms require .json output")


def plan_export(request: Mapping[str, Any], private_root: Path, policy: ExportPolicy) -> dict[str, Any]:
    _require_exact_keys(request, REQUEST_FIELDS, "ExportRequest")
    if request["schema_version"] != SCHEMA_VERSION or request["kind"] != "ExportRequest":
        raise ExportBoundaryError("UNKNOWN_SCHEMA", "unsupported ExportRequest version or kind")
    export_id = _require_nonempty_string(request["id"], "ExportRequest.id")
    if not EXPORT_ID.fullmatch(export_id):
        raise ExportBoundaryError("INVALID_ID", "ExportRequest.id has invalid form")
    if request["classification"] not in {"private_operational", "private_human"}:
        raise ExportBoundaryError("CLASSIFICATION_DENIED", "ExportRequest must remain private")
    _require_nonempty_string(request["retention"], "ExportRequest.retention")
    raw_entries = request["entries"]
    if not isinstance(raw_entries, list) or not raw_entries:
        raise ExportBoundaryError("UNKNOWN_FIELD", "ExportRequest.entries must be non-empty")
    entries: list[dict[str, Any]] = []
    for index, raw_entry in enumerate(raw_entries):
        if not isinstance(raw_entry, dict):
            raise ExportBoundaryError("UNKNOWN_FIELD", f"entries[{index}] must be an object")
        _require_exact_keys(raw_entry, REQUEST_ENTRY_FIELDS, f"entries[{index}]")
        source_path = normalize_relative_path(raw_entry["source_path"], f"entries[{index}].source_path")
        source_class = _require_nonempty_string(
            raw_entry["source_classification"], f"entries[{index}].source_classification"
        )
        artifact_kind = _require_nonempty_string(
            raw_entry["artifact_kind"], f"entries[{index}].artifact_kind"
        )
        transform_id = _require_nonempty_string(
            raw_entry["transformation_id"], f"entries[{index}].transformation_id"
        )
        policy.validate_route(source_class, artifact_kind, transform_id)
        stable = read_stable_file(private_root, source_path, policy.max_source_bytes)
        source = _parse_json_object(stable.body, f"entries[{index}].source")
        transform = policy.transforms[transform_id]
        missing_source = set(transform["required_source_fields"]) - set(source)
        if missing_source:
            raise ExportBoundaryError(
                "SOURCE_INVALID", f"entries[{index}] lacks required fields: {sorted(missing_source)}"
            )
        entries.append(
            {
                **raw_entry,
                "source_path": source_path,
                "output_path": normalize_relative_path(
                    raw_entry["output_path"], f"entries[{index}].output_path"
                ),
                "source_digest": stable.digest,
                "source_size_bytes": stable.size_bytes,
            }
        )
    _validate_ids_and_paths(entries, policy)
    return {
        "schema_version": SCHEMA_VERSION,
        "id": export_id,
        "kind": "ExportPlan",
        "state": "planned",
        "classification": "private_operational",
        "retention": "review_cycle",
        "policy_version": policy.version,
        "policy_digest": policy.digest,
        "request_digest": record_digest(dict(request)),
        "entries": entries,
    }


def validate_plan(plan: Mapping[str, Any], policy: ExportPolicy) -> None:
    _require_exact_keys(plan, PLAN_FIELDS, "ExportPlan")
    if (
        plan["schema_version"] != SCHEMA_VERSION
        or plan["kind"] != "ExportPlan"
        or plan["state"] != "planned"
    ):
        raise ExportBoundaryError("UNKNOWN_SCHEMA", "unsupported ExportPlan")
    if plan["classification"] != "private_operational":
        raise ExportBoundaryError("CLASSIFICATION_DENIED", "ExportPlan must remain private")
    if plan["policy_version"] != policy.version or plan["policy_digest"] != policy.digest:
        raise ExportBoundaryError("POLICY_MISMATCH", "ExportPlan is pinned to another policy")
    if not EXPORT_ID.fullmatch(_require_nonempty_string(plan["id"], "ExportPlan.id")):
        raise ExportBoundaryError("INVALID_ID", "ExportPlan.id has invalid form")
    entries = plan["entries"]
    if not isinstance(entries, list) or not entries:
        raise ExportBoundaryError("UNKNOWN_FIELD", "ExportPlan.entries must be non-empty")
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ExportBoundaryError("UNKNOWN_FIELD", f"entries[{index}] must be an object")
        _require_exact_keys(entry, PLAN_ENTRY_FIELDS, f"entries[{index}]")
        policy.validate_route(
            entry["source_classification"], entry["artifact_kind"], entry["transformation_id"]
        )
        if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(entry["source_digest"])):
            raise ExportBoundaryError("UNKNOWN_FIELD", "source_digest is invalid")
        if not isinstance(entry["source_size_bytes"], int) or entry["source_size_bytes"] < 0:
            raise ExportBoundaryError("UNKNOWN_FIELD", "source_size_bytes is invalid")
    _validate_ids_and_paths(entries, policy)


def _validate_source_field_types(source: Mapping[str, Any], fields: Iterable[str]) -> None:
    list_fields = {"authors", "evidence_links"}
    for field in fields:
        if field not in source:
            continue
        value = source[field]
        if field in list_fields:
            if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
                raise ExportBoundaryError("SOURCE_INVALID", f"{field} must be a string list")
        elif not isinstance(value, str):
            raise ExportBoundaryError("SOURCE_INVALID", f"{field} must be a string")


def project_source(
    source: Mapping[str, Any], projection_id: str, artifact_kind: str, transform: Mapping[str, Any]
) -> dict[str, Any]:
    required = set(transform["required_source_fields"])
    if required - set(source):
        raise ExportBoundaryError("SOURCE_INVALID", "source lacks a required projection field")
    _validate_source_field_types(source, transform["allowed_source_fields"])
    kind_name = {"citation_metadata": "CitationMetadata", "research_summary": "ResearchSummary"}.get(
        artifact_kind
    )
    if kind_name is None:
        raise ExportBoundaryError("UNKNOWN_ARTIFACT_KIND", "projector does not implement artifact kind")
    projection: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "id": projection_id,
        "kind": kind_name,
        "classification": "public_derived",
        "retention": "durable",
    }
    for field in transform["allowed_source_fields"]:
        if field in source:
            projection[field] = source[field]
    if set(projection) - set(transform["output_fields"]):
        raise ExportBoundaryError("POLICY_INVALID", "projector emitted a field absent from policy")
    return projection


def canary_variants(canaries: Iterable[str]) -> list[bytes]:
    variants: set[bytes] = set()
    for canary in canaries:
        if not canary:
            continue
        raw = canary.encode("utf-8")
        variants.add(raw)
        variants.add(raw.hex().encode("ascii"))
        variants.add(base64.b64encode(raw))
        variants.add(base64.urlsafe_b64encode(raw).rstrip(b"="))
    return sorted(variants)


def _scan_public_value(value: Any, policy: ExportPolicy, location: str) -> None:
    if isinstance(value, dict):
        forbidden = set(policy.document["forbidden_public_fields"])
        allowed_digests = set(policy.document["allowed_public_digest_fields"])
        for key, child in value.items():
            if key in forbidden or (key.endswith("digest") and key not in allowed_digests):
                raise ExportBoundaryError("PRIVATE_METADATA", f"forbidden public field at {location}")
            if key == "classification" and child not in policy.document["public_output_classifications"]:
                raise ExportBoundaryError("CLASSIFICATION_DENIED", f"non-public classification at {location}")
            if key == "kind" and child in {"CredentialRef", "CapabilityToken", "StorageBinding"}:
                raise ExportBoundaryError("PRIVATE_METADATA", f"private record kind at {location}")
            _scan_public_value(child, policy, f"{location}.{key}")
    elif isinstance(value, list):
        for index, child in enumerate(value):
            _scan_public_value(child, policy, f"{location}[{index}]")
    elif isinstance(value, str):
        scan_supplementary_text(value, policy)


def scan_supplementary_text(text: str, policy: ExportPolicy) -> None:
    detectors = policy.document["supplementary_detectors"]
    patterns = [
        ("pem_private_key", PRIVATE_KEY_PATTERN),
        ("authorization_header", AUTHORIZATION_PATTERN),
        ("signed_url", SIGNED_URL_PATTERN),
        ("private_absolute_path", PRIVATE_PATH_PATTERN),
    ]
    for detector, pattern in patterns:
        if detectors.get(detector) and pattern.search(text):
            raise ExportBoundaryError("SECRET_PATTERN", f"supplementary detector triggered: {detector}")


def scan_public_bytes(
    body: bytes,
    policy: ExportPolicy,
    *,
    canaries: Iterable[str] = (),
    media_type: str = "application/json",
) -> Any:
    for variant in canary_variants(canaries):
        if variant and variant in body:
            raise ExportBoundaryError("SECRET_CANARY", "seeded private canary detected")
    try:
        text = body.decode("utf-8")
    except UnicodeError as exc:
        raise ExportBoundaryError("OUTPUT_INVALID", "public output must be UTF-8") from exc
    scan_supplementary_text(text, policy)
    if media_type == "application/json":
        try:
            value = parse_json_text(text)
        except (json.JSONDecodeError, DuplicateKeyError) as exc:
            raise ExportBoundaryError("OUTPUT_INVALID", "public JSON is invalid") from exc
        _scan_public_value(value, policy, "public")
        return value
    return text


def _write_staged_file(root: Path, relative: str, body: bytes) -> None:
    target = root.joinpath(*PurePosixPath(relative).parts)
    target.parent.mkdir(parents=True, exist_ok=True)
    with target.open("xb") as handle:
        handle.write(body)
        handle.flush()
        os.fsync(handle.fileno())


def render_export(
    plan: Mapping[str, Any],
    private_root: Path,
    staging_directory: Path,
    policy: ExportPolicy,
    *,
    canaries: Iterable[str] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    staging_directory = staging_directory.absolute()
    staging_directory.parent.mkdir(parents=True, exist_ok=True)
    reservation = staging_directory.parent / f".{staging_directory.name}.render-lock"
    try:
        reservation.mkdir(mode=0o700)
    except FileExistsError as exc:
        raise ExportBoundaryError("OUTPUT_BUSY", "another render owns the staging reservation") from exc
    try:
        return _render_export_reserved(
            plan,
            private_root,
            staging_directory,
            policy,
            canaries=canaries,
        )
    finally:
        try:
            reservation.rmdir()
        except FileNotFoundError:
            pass


def _render_export_reserved(
    plan: Mapping[str, Any],
    private_root: Path,
    staging_directory: Path,
    policy: ExportPolicy,
    *,
    canaries: Iterable[str] = (),
) -> tuple[dict[str, Any], dict[str, Any]]:
    validate_plan(plan, policy)
    if staging_directory.exists():
        raise ExportBoundaryError("OUTPUT_EXISTS", "staging directory must not already exist")
    temporary = Path(tempfile.mkdtemp(prefix=f".{staging_directory.name}.", dir=staging_directory.parent))
    manifest_entries: list[dict[str, Any]] = []
    receipt_sources: list[dict[str, Any]] = []
    try:
        for index, entry in enumerate(plan["entries"]):
            stable = read_stable_file(private_root, entry["source_path"], policy.max_source_bytes)
            if stable.digest != entry["source_digest"] or stable.size_bytes != entry["source_size_bytes"]:
                raise ExportBoundaryError("SOURCE_CHANGED", f"source for entry {index} changed after planning")
            source = _parse_json_object(stable.body, f"entries[{index}].source")
            transform = policy.transforms[entry["transformation_id"]]
            projection = project_source(source, entry["projection_id"], entry["artifact_kind"], transform)
            body = pretty_json(projection).encode("utf-8")
            scan_public_bytes(body, policy, canaries=canaries)
            output_digest = sha256_bytes(body)
            _write_staged_file(temporary, entry["output_path"], body)
            manifest_entries.append(
                {
                    "entry_id": entry["entry_id"],
                    "projection_id": entry["projection_id"],
                    "artifact_kind": entry["artifact_kind"],
                    "transformation_id": entry["transformation_id"],
                    "transformation_digest": record_digest(transform),
                    "output_path": entry["output_path"],
                    "output_digest": output_digest,
                    "media_type": transform["output_media_type"],
                    "size_bytes": len(body),
                }
            )
            receipt_sources.append(
                {
                    "entry_id": entry["entry_id"],
                    "source_digest": stable.digest,
                    "source_size_bytes": stable.size_bytes,
                }
            )
        manifest = {
            "schema_version": SCHEMA_VERSION,
            "id": plan["id"],
            "kind": "ExportManifest",
            "state": "rendered",
            "classification": "public_derived",
            "retention": "durable",
            "policy_version": policy.version,
            "policy_digest": policy.digest,
            "entries": sorted(manifest_entries, key=lambda item: item["entry_id"]),
        }
        manifest_body = pretty_json(manifest).encode("utf-8")
        scan_public_bytes(manifest_body, policy, canaries=canaries)
        _write_staged_file(temporary, "export-manifest.json", manifest_body)
        check_staging(temporary, policy, canaries=canaries)
        receipt = {
            "schema_version": SCHEMA_VERSION,
            "id": plan["id"],
            "kind": "ExportRenderReceipt",
            "state": "rendered",
            "classification": "private_operational",
            "retention": "review_cycle",
            "policy_version": policy.version,
            "policy_digest": policy.digest,
            "plan_digest": record_digest(dict(plan)),
            "manifest_digest": sha256_bytes(manifest_body),
            "sources": receipt_sources,
        }
        os.replace(temporary, staging_directory)
        if hasattr(os, "O_DIRECTORY"):
            directory_fd = os.open(staging_directory.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory_fd)
            finally:
                os.close(directory_fd)
        return manifest, receipt
    except Exception:
        shutil.rmtree(temporary, ignore_errors=True)
        raise


def validate_public_manifest(manifest: Mapping[str, Any], policy: ExportPolicy) -> None:
    _require_exact_keys(manifest, set(policy.document["public_manifest_fields"]), "ExportManifest")
    if (
        manifest["schema_version"] != SCHEMA_VERSION
        or manifest["kind"] != "ExportManifest"
        or manifest["state"] != "rendered"
        or manifest["classification"] != "public_derived"
        or manifest["retention"] != "durable"
    ):
        raise ExportBoundaryError("UNKNOWN_SCHEMA", "unsupported ExportManifest")
    if manifest["policy_version"] != policy.version or manifest["policy_digest"] != policy.digest:
        raise ExportBoundaryError("POLICY_MISMATCH", "manifest policy pin does not match")
    if not EXPORT_ID.fullmatch(_require_nonempty_string(manifest["id"], "ExportManifest.id")):
        raise ExportBoundaryError("INVALID_ID", "ExportManifest.id has invalid form")
    entries = manifest["entries"]
    if not isinstance(entries, list) or not entries:
        raise ExportBoundaryError("UNKNOWN_FIELD", "ExportManifest.entries must be non-empty")
    seen_entries: set[str] = set()
    seen_projections: set[str] = set()
    collision_keys: set[str] = set()
    for index, entry in enumerate(entries):
        if not isinstance(entry, dict):
            raise ExportBoundaryError("UNKNOWN_FIELD", f"entries[{index}] must be an object")
        _require_exact_keys(
            entry, set(policy.document["public_manifest_entry_fields"]), f"entries[{index}]"
        )
        entry_id = entry["entry_id"]
        if not isinstance(entry_id, str) or not ENTRY_ID.fullmatch(entry_id) or entry_id in seen_entries:
            raise ExportBoundaryError("DUPLICATE_ID", "manifest entry IDs must be unique and valid")
        seen_entries.add(entry_id)
        projection_id = entry["projection_id"]
        if (
            not isinstance(projection_id, str)
            or not PROJECTION_ID.fullmatch(projection_id)
            or projection_id in seen_projections
        ):
            raise ExportBoundaryError("DUPLICATE_ID", "manifest projection IDs must be unique and valid")
        seen_projections.add(projection_id)
        output_path = normalize_relative_path(entry["output_path"], f"entries[{index}].output_path")
        collision_key = unicodedata.normalize("NFC", output_path).casefold()
        if collision_key in collision_keys:
            raise ExportBoundaryError("PATH_COLLISION", "manifest outputs collide after normalization")
        collision_keys.add(collision_key)
        kind = policy.artifact_kinds.get(entry["artifact_kind"])
        transform = policy.transforms.get(entry["transformation_id"])
        if not isinstance(kind, dict):
            raise ExportBoundaryError("UNKNOWN_ARTIFACT_KIND", "manifest artifact kind is not allowlisted")
        if not isinstance(transform, dict) or entry["transformation_id"] not in kind["allowed_transforms"]:
            raise ExportBoundaryError("UNAPPROVED_TRANSFORM", "manifest transform is not allowlisted")
        prefix = kind["output_prefix"]
        if not output_path.startswith(prefix):
            raise ExportBoundaryError("UNAPPROVED_DESTINATION", "manifest output is outside artifact prefix")
        for digest_field in ["transformation_digest", "output_digest"]:
            if not re.fullmatch(r"sha256:[0-9a-f]{64}", str(entry[digest_field])):
                raise ExportBoundaryError("UNKNOWN_FIELD", f"{digest_field} is invalid")
        if entry["transformation_digest"] != record_digest(transform):
            raise ExportBoundaryError("POLICY_MISMATCH", "transformation digest is stale")
        if entry["media_type"] != transform["output_media_type"]:
            raise ExportBoundaryError("UNKNOWN_FIELD", "manifest media type disagrees with transform")
        if not isinstance(entry["size_bytes"], int) or entry["size_bytes"] < 0:
            raise ExportBoundaryError("UNKNOWN_FIELD", "manifest byte size is invalid")


def check_staging(
    staging_directory: Path,
    policy: ExportPolicy,
    *,
    canaries: Iterable[str] = (),
) -> dict[str, Any]:
    if not staging_directory.is_dir() or staging_directory.is_symlink():
        raise ExportBoundaryError("PATH_ESCAPE", "staging directory must be a regular directory")
    manifest_path = staging_directory / "export-manifest.json"
    if not manifest_path.is_file() or manifest_path.is_symlink():
        raise ExportBoundaryError("MISSING_OUTPUT", "export-manifest.json is missing")
    try:
        manifest_stable = read_stable_file(
            staging_directory, "export-manifest.json", policy.max_source_bytes
        )
        manifest_body = manifest_stable.body
        manifest = parse_json_text(manifest_body.decode("utf-8"))
    except (OSError, UnicodeError, json.JSONDecodeError, DuplicateKeyError) as exc:
        raise ExportBoundaryError("OUTPUT_INVALID", "export manifest is invalid") from exc
    if not isinstance(manifest, dict):
        raise ExportBoundaryError("OUTPUT_INVALID", "export manifest must be an object")
    validate_public_manifest(manifest, policy)
    scan_public_bytes(manifest_body, policy, canaries=canaries)

    expected = {"export-manifest.json"}
    expected.update(entry["output_path"] for entry in manifest["entries"])
    actual: set[str] = set()
    collision_keys: set[str] = set()
    for path in sorted(staging_directory.rglob("*")):
        if path.is_symlink():
            raise ExportBoundaryError("PATH_ESCAPE", "staged tree contains a symlink")
        if path.is_dir():
            continue
        if not path.is_file():
            raise ExportBoundaryError("PATH_ESCAPE", "staged tree contains a non-regular entry")
        if path.stat().st_nlink != 1:
            raise ExportBoundaryError("PATH_ESCAPE", "staged tree contains a hardlinked file")
        relative = path.relative_to(staging_directory).as_posix()
        normalized = normalize_relative_path(relative, "staged output")
        collision_key = unicodedata.normalize("NFC", normalized).casefold()
        if collision_key in collision_keys:
            raise ExportBoundaryError("PATH_COLLISION", "staged paths collide after normalization")
        collision_keys.add(collision_key)
        actual.add(normalized)
    extra = actual - expected
    missing = expected - actual
    if extra:
        raise ExportBoundaryError("UNAPPROVED_OUTPUT", f"staging contains {len(extra)} extra file(s)")
    if missing:
        raise ExportBoundaryError("MISSING_OUTPUT", f"staging lacks {len(missing)} file(s)")

    checked_outputs: list[dict[str, Any]] = []
    for entry in manifest["entries"]:
        path = staging_directory.joinpath(*PurePosixPath(entry["output_path"]).parts)
        stable = read_stable_file(staging_directory, entry["output_path"], policy.max_source_bytes)
        body = stable.body
        if stable.digest != entry["output_digest"] or stable.size_bytes != entry["size_bytes"]:
            raise ExportBoundaryError("DIGEST_MISMATCH", "staged output does not match manifest")
        value = scan_public_bytes(body, policy, canaries=canaries, media_type=entry["media_type"])
        if not isinstance(value, dict):
            raise ExportBoundaryError("OUTPUT_INVALID", "current projected output must be an object")
        transform = policy.transforms[entry["transformation_id"]]
        allowed = set(transform["output_fields"])
        if set(value) - allowed:
            raise ExportBoundaryError("UNKNOWN_FIELD", "projected output has fields absent from transform")
        base_required = {"schema_version", "id", "kind", "classification", "retention"}
        required = base_required | set(transform["required_source_fields"])
        if required - set(value):
            raise ExportBoundaryError("UNKNOWN_FIELD", "projected output lacks required fields")
        if value.get("id") != entry["projection_id"]:
            raise ExportBoundaryError("DIGEST_MISMATCH", "projection ID disagrees with manifest")
        checked_outputs.append(
            {
                "entry_id": entry["entry_id"],
                "output_path": entry["output_path"],
                "output_digest": entry["output_digest"],
            }
        )
    return {
        "schema_version": SCHEMA_VERSION,
        "id": manifest["id"],
        "kind": "ExportValidation",
        "state": "validated",
        "classification": "public_derived",
        "retention": "durable",
        "policy_version": policy.version,
        "policy_digest": policy.digest,
        "manifest_digest": sha256_bytes(manifest_body),
        "outputs": checked_outputs,
        "result": "pass",
    }


def ensure_private_record_path(path: Path, repository_root: Path = ROOT) -> None:
    absolute = path.absolute()
    try:
        relative = absolute.relative_to(repository_root.resolve())
    except ValueError:
        return
    allowed = [PurePosixPath("Private"), PurePosixPath("researcher/exports/private")]
    relative_posix = PurePosixPath(relative.as_posix())
    if not any(relative_posix == prefix or prefix in relative_posix.parents for prefix in allowed):
        raise ExportBoundaryError(
            "PRIVATE_DESTINATION_REQUIRED",
            "private export records inside the repository must use Private/ or researcher/exports/private/",
        )


def write_private_json(path: Path, value: Mapping[str, Any]) -> None:
    ensure_private_record_path(path)
    atomic_write_text(path, pretty_json(dict(value)))
    try:
        path.chmod(0o600)
    except OSError:
        pass
