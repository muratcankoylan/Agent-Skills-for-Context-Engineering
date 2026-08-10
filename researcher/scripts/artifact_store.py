#!/usr/bin/env python3
"""Private content-addressed storage, candidate freezing, and fake capabilities."""

from __future__ import annotations

import contextlib
import ctypes
import dataclasses
import errno
import fcntl
import os
import secrets
import shutil
import stat
import sys
import tempfile
import threading
import unicodedata
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path, PurePosixPath
from typing import Any, Iterable, Iterator, Mapping

try:
    from schema_contract import (
        CANONICALIZATION_PROFILE,
        ContractError,
        SchemaRegistry,
        ascii_casefold_path,
        canonical_digest,
        canonicalize,
        new_typed_id,
        parse_json_strict,
        sha256_bytes,
        utf16_sort_key,
        validate_digest,
        validate_typed_id,
    )
except ModuleNotFoundError:  # Imported as researcher.scripts.artifact_store.
    from researcher.scripts.schema_contract import (
        CANONICALIZATION_PROFILE,
        ContractError,
        SchemaRegistry,
        ascii_casefold_path,
        canonical_digest,
        canonicalize,
        new_typed_id,
        parse_json_strict,
        sha256_bytes,
        utf16_sort_key,
        validate_digest,
        validate_typed_id,
    )


CLASSIFICATION_RANK = {
    "public": 0,
    "public_derived": 0,
    "private_operational": 1,
    "private_human": 2,
    "restricted_source": 3,
    "secret_reference": 4,
}
MAX_FILE_BYTES = 16 * 1024 * 1024
MAX_TREE_BYTES = 128 * 1024 * 1024
MAX_TREE_FILES = 10_000
FREEZE_POLICY = {
    "schema_version": "1.0.0",
    "allowed_entry_types": ["file"],
    "path_profile": "nfc-posix-ascii-casefold-v1",
    "mode_profile": "executable-bit-only-v1",
    "maximum_file_bytes": MAX_FILE_BYTES,
    "maximum_tree_bytes": MAX_TREE_BYTES,
    "maximum_tree_files": MAX_TREE_FILES,
    "tree_canonicalization_profile": CANONICALIZATION_PROFILE,
}
FREEZE_POLICY_DIGEST = canonical_digest(FREEZE_POLICY)


def utc_now() -> str:
    return datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z")


def _require_aware_time(value: datetime) -> None:
    if not isinstance(value, datetime) or value.tzinfo is None or value.utcoffset() is None:
        raise ContractError("INVALID_TIME", "capability checks require a timezone-aware instant")


def _classification_rank(classification: str) -> int:
    try:
        return CLASSIFICATION_RANK[classification]
    except KeyError as exc:
        raise ContractError("UNKNOWN_CLASSIFICATION", "classification is not registered") from exc


def _fsync_directory(path: Path) -> None:
    if not hasattr(os, "O_DIRECTORY"):
        return
    descriptor = os.open(path, os.O_RDONLY | os.O_DIRECTORY)
    try:
        os.fsync(descriptor)
    finally:
        os.close(descriptor)


def _secure_directory(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True, mode=0o700)
    if path.is_symlink() or not path.is_dir():
        raise ContractError("STORE_PATH_INVALID", "artifact-store directory is not a real directory")
    try:
        path.chmod(0o700)
        mode = path.stat().st_mode & 0o777
    except OSError as exc:
        raise ContractError("STORE_PATH_INVALID", "artifact-store directory is not private") from exc
    if mode != 0o700:
        raise ContractError("STORE_PATH_INVALID", "artifact-store directory permissions are not private")


def _atomic_write_bytes(
    path: Path,
    body: bytes,
    *,
    mode: int = 0o600,
    no_clobber: bool = False,
    secure_parent: bool = True,
) -> None:
    if secure_parent:
        _secure_directory(path.parent)
    elif path.parent.is_symlink() or not path.parent.is_dir():
        raise ContractError("OUTPUT_PATH_INVALID", "output parent must be a real directory")
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        os.fchmod(descriptor, mode)
        with os.fdopen(descriptor, "wb", closefd=True) as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        if no_clobber:
            try:
                os.link(temporary, path, follow_symlinks=False)
            except FileExistsError as exc:
                raise ContractError("OUTPUT_EXISTS", "materialization destination must be fresh") from exc
            temporary.unlink()
        else:
            os.replace(temporary, path)
        _fsync_directory(path.parent)
    except Exception:
        try:
            os.close(descriptor)
        except OSError:
            pass
        temporary.unlink(missing_ok=True)
        raise


def _load_private_json(path: Path) -> dict[str, Any]:
    try:
        body = path.read_bytes()
        value = parse_json_strict(body.decode("utf-8"))
    except (OSError, UnicodeError) as exc:
        raise ContractError("ARTIFACT_UNAVAILABLE", "private artifact metadata is unavailable") from exc
    if not isinstance(value, dict):
        raise ContractError("STORE_CORRUPT", "private artifact metadata is not an object")
    return value


def _publish_directory_no_clobber(source: Path, destination: Path) -> None:
    """Atomically publish a same-filesystem directory without replacing a target."""

    libc = ctypes.CDLL(None, use_errno=True)
    source_bytes = os.fsencode(source)
    destination_bytes = os.fsencode(destination)
    if sys.platform == "darwin" and hasattr(libc, "renamex_np"):
        rename = libc.renamex_np
        rename.argtypes = [ctypes.c_char_p, ctypes.c_char_p, ctypes.c_uint]
        rename.restype = ctypes.c_int
        result = rename(source_bytes, destination_bytes, 0x00000004)  # RENAME_EXCL
    elif hasattr(libc, "renameat2"):
        rename = libc.renameat2
        rename.argtypes = [
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_int,
            ctypes.c_char_p,
            ctypes.c_uint,
        ]
        rename.restype = ctypes.c_int
        result = rename(-100, source_bytes, -100, destination_bytes, 0x00000001)
    else:
        raise ContractError(
            "ATOMIC_PUBLISH_UNAVAILABLE",
            "platform has no atomic no-clobber directory publish primitive",
        )
    if result == 0:
        return
    error_number = ctypes.get_errno()
    if error_number in {errno.EEXIST, errno.ENOTEMPTY}:
        raise ContractError("OUTPUT_EXISTS", "materialization destination must be fresh")
    raise OSError(error_number, os.strerror(error_number), str(destination))


@dataclass(frozen=True)
class BlobRef:
    digest: str
    size_bytes: int
    locator: str
    classification: str


@dataclass(frozen=True)
class ArtifactAuthority:
    """Explicit authority input. Artifact references are deliberately insufficient."""

    actor_id: str
    operations: frozenset[str]
    resources: frozenset[str]
    classification_ceiling: str

    def require(self, operation: str, resource: str) -> None:
        if operation not in self.operations:
            raise ContractError("ACCESS_DENIED", "artifact access is not authorized")
        if "*" not in self.resources and resource not in self.resources:
            raise ContractError("ACCESS_DENIED", "artifact access is not authorized")
        _classification_rank(self.classification_ceiling)


class LocalContentAddressedStore:
    """Exact-byte SHA-256 CAS with atomic, concurrent, classification-aware writes."""

    def __init__(self, root: Path):
        lexical_root = root.absolute()
        if lexical_root.exists() and lexical_root.is_symlink():
            raise ContractError("STORE_PATH_INVALID", "artifact-store root cannot be a symlink")
        self.root = lexical_root.resolve(strict=False)
        for child in (self.root, self.root / "sha256", self.root / "metadata", self.root / "locks"):
            _secure_directory(child)

    def _blob_path(self, digest: str) -> Path:
        validate_digest(digest)
        hexadecimal = digest.removeprefix("sha256:")
        return self.root / "sha256" / hexadecimal[:2] / hexadecimal

    def _metadata_path(self, digest: str) -> Path:
        validate_digest(digest)
        return self.root / "metadata" / f"{digest.removeprefix('sha256:')}.json"

    def _locator(self, digest: str) -> str:
        validate_digest(digest)
        return f"sha256/{digest[7:9]}/{digest[7:]}"

    @contextlib.contextmanager
    def _digest_lock(self, key: str) -> Iterator[None]:
        lock_name = sha256_bytes(key.encode("utf-8")).removeprefix("sha256:")
        lock_path = self.root / "locks" / f"{lock_name}.lock"
        descriptor = os.open(lock_path, os.O_CREAT | os.O_RDWR, 0o600)
        try:
            os.fchmod(descriptor, 0o600)
            fcntl.flock(descriptor, fcntl.LOCK_EX)
            yield
        finally:
            fcntl.flock(descriptor, fcntl.LOCK_UN)
            os.close(descriptor)

    def _read_verified_blob(self, path: Path, expected_digest: str, expected_size: int) -> bytes:
        try:
            info = path.lstat()
        except OSError as exc:
            raise ContractError("ARTIFACT_UNAVAILABLE", "content-addressed body is unavailable") from exc
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ContractError("STORE_CORRUPT", "content-addressed body has an invalid file type")
        if info.st_size != expected_size:
            raise ContractError("DIGEST_MISMATCH", "content-addressed body size has changed")
        flags = os.O_RDONLY
        if hasattr(os, "O_NOFOLLOW"):
            flags |= os.O_NOFOLLOW
        try:
            descriptor = os.open(path, flags)
        except OSError as exc:
            raise ContractError("ARTIFACT_UNAVAILABLE", "content-addressed body is unavailable") from exc
        try:
            before = os.fstat(descriptor)
            chunks: list[bytes] = []
            while True:
                chunk = os.read(descriptor, 1024 * 1024)
                if not chunk:
                    break
                chunks.append(chunk)
            after = os.fstat(descriptor)
        finally:
            os.close(descriptor)
        if (
            (info.st_dev, info.st_ino, info.st_size, info.st_mtime_ns, info.st_ctime_ns)
            != (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            or
            (before.st_dev, before.st_ino, before.st_size, before.st_mtime_ns, before.st_ctime_ns)
            != (after.st_dev, after.st_ino, after.st_size, after.st_mtime_ns, after.st_ctime_ns)
            or before.st_nlink != 1
        ):
            raise ContractError("DIGEST_MISMATCH", "content-addressed body changed while reading")
        body = b"".join(chunks)
        if sha256_bytes(body) != expected_digest:
            raise ContractError("DIGEST_MISMATCH", "content-addressed body digest has changed")
        return body

    def _verify_blob_path(self, path: Path, expected_digest: str, expected_size: int) -> None:
        self._read_verified_blob(path, expected_digest, expected_size)

    def _load_label(self, digest: str) -> dict[str, Any] | None:
        path = self._metadata_path(digest)
        if not path.exists():
            return None
        value = _load_private_json(path)
        required = {"schema_version", "digest", "classification", "size_bytes"}
        if set(value) != required or value["digest"] != digest:
            raise ContractError("STORE_CORRUPT", "content classification metadata is invalid")
        _classification_rank(value["classification"])
        return value

    def put_bytes(
        self,
        body: bytes,
        *,
        classification: str,
        expected_digest: str | None = None,
    ) -> BlobRef:
        if not isinstance(body, bytes):
            raise ContractError("BODY_TYPE", "artifact body must be exact bytes")
        _classification_rank(classification)
        digest = sha256_bytes(body)
        if expected_digest is not None and expected_digest != digest:
            raise ContractError("DIGEST_MISMATCH", "artifact body differs from expected digest")
        target = self._blob_path(digest)
        locator = self._locator(digest)
        with self._digest_lock(digest):
            label = self._load_label(digest)
            if label and _classification_rank(classification) < _classification_rank(label["classification"]):
                raise ContractError(
                    "CLASSIFICATION_DOWNGRADE",
                    "existing content cannot be rebound at a lower classification",
                )
            _secure_directory(target.parent)
            if target.exists():
                self._verify_blob_path(target, digest, len(body))
            else:
                descriptor, temporary_name = tempfile.mkstemp(prefix=".put.", dir=target.parent)
                temporary = Path(temporary_name)
                try:
                    os.fchmod(descriptor, 0o600)
                    with os.fdopen(descriptor, "wb", closefd=True) as handle:
                        handle.write(body)
                        handle.flush()
                        os.fsync(handle.fileno())
                    if sha256_bytes(temporary.read_bytes()) != digest:
                        raise ContractError("DIGEST_MISMATCH", "temporary artifact failed verification")
                    try:
                        os.link(temporary, target, follow_symlinks=False)
                    except FileExistsError:
                        self._verify_blob_path(target, digest, len(body))
                    finally:
                        temporary.unlink(missing_ok=True)
                    _fsync_directory(target.parent)
                except Exception:
                    try:
                        os.close(descriptor)
                    except OSError:
                        pass
                    temporary.unlink(missing_ok=True)
                    raise
            effective = classification
            if label and _classification_rank(label["classification"]) > _classification_rank(classification):
                effective = label["classification"]
            metadata = {
                "schema_version": "1.0.0",
                "digest": digest,
                "classification": effective,
                "size_bytes": len(body),
            }
            _atomic_write_bytes(self._metadata_path(digest), canonicalize(metadata) + b"\n")
            self._verify_blob_path(target, digest, len(body))
            return BlobRef(digest, len(body), locator, effective)

    def get_bytes(
        self,
        digest: str,
        authority: ArtifactAuthority,
        *,
        resource: str | None = None,
        locator: str | None = None,
    ) -> bytes:
        resource_id = resource or digest
        authority.require("artifact.read", resource_id)
        validate_digest(digest)
        label = self._load_label(digest)
        if label is None:
            raise ContractError("ARTIFACT_UNAVAILABLE", "content-addressed body is unavailable")
        if _classification_rank(label["classification"]) > _classification_rank(
            authority.classification_ceiling
        ):
            raise ContractError("ACCESS_DENIED", "artifact access is not authorized")
        if locator is not None and locator != self._locator(digest):
            raise ContractError("BINDING_MISMATCH", "storage binding does not match artifact digest")
        path = self._blob_path(digest)
        return self._read_verified_blob(path, digest, label["size_bytes"])

    def _verify_internal(self, digest: str) -> dict[str, Any]:
        label = self._load_label(digest)
        if label is None:
            return {"digest": digest, "result": "missing"}
        self._verify_blob_path(self._blob_path(digest), digest, label["size_bytes"])
        return {
            "digest": digest,
            "result": "verified",
            "size_bytes": label["size_bytes"],
            "classification": label["classification"],
        }

    def _head_internal(self, digest: str) -> dict[str, Any]:
        label = self._load_label(digest)
        if label is None:
            raise ContractError("ARTIFACT_UNAVAILABLE", "content-addressed body is unavailable")
        try:
            info = self._blob_path(digest).lstat()
        except OSError as exc:
            raise ContractError("ARTIFACT_UNAVAILABLE", "content-addressed body is unavailable") from exc
        if not stat.S_ISREG(info.st_mode) or info.st_nlink != 1:
            raise ContractError("STORE_CORRUPT", "content-addressed body has an invalid file type")
        if info.st_size != label["size_bytes"]:
            raise ContractError("DIGEST_MISMATCH", "content-addressed body size has changed")
        return label

    def verify(
        self,
        digest: str,
        authority: ArtifactAuthority,
        *,
        resource: str | None = None,
    ) -> dict[str, Any]:
        resource_id = resource or digest
        authority.require("artifact.read", resource_id)
        validate_digest(digest)
        label = self._load_label(digest)
        if label is not None and _classification_rank(label["classification"]) > _classification_rank(
            authority.classification_ceiling
        ):
            raise ContractError("ACCESS_DENIED", "artifact access is not authorized")
        return self._verify_internal(digest)


class LocalArtifactStore:
    """Storage-neutral artifact API backed by private reference and binding records."""

    def __init__(self, root: Path, *, registry: SchemaRegistry | None = None):
        self.cas = LocalContentAddressedStore(root)
        self.registry = registry or SchemaRegistry.load()
        self.records = self.cas.root / "records"
        self.refs = self.records / "refs"
        self.bindings = self.records / "bindings"
        _secure_directory(self.refs)
        _secure_directory(self.bindings)

    def _record_key(self, artifact_id: str) -> str:
        return sha256_bytes(artifact_id.encode("utf-8")).removeprefix("sha256:")

    def _record_paths(self, artifact_id: str) -> tuple[Path, Path]:
        key = self._record_key(artifact_id)
        return self.refs / f"{key}.json", self.bindings / f"{key}.json"

    def _validate_artifact_body(
        self,
        *,
        artifact_id: str,
        artifact_kind: str,
        artifact_schema_version: str,
        body: bytes,
        media_type: str,
        classification: str,
        for_write: bool,
    ) -> dict[str, Any]:
        if not isinstance(body, bytes):
            raise ContractError("BODY_TYPE", "artifact body must be exact bytes")
        entry = (
            self.registry.resolve_for_write(artifact_kind, artifact_schema_version)
            if for_write
            else self.registry.resolve_for_read(artifact_kind, artifact_schema_version)
        )
        if entry.id_prefix is None:
            raise ContractError(
                "ARTIFACT_ID_UNSUPPORTED",
                "registered artifact kind has no typed identity contract",
            )
        if media_type != "application/json":
            raise ContractError("MEDIA_TYPE_MISMATCH", "registered records require application/json")
        try:
            value = parse_json_strict(body.decode("utf-8"))
        except UnicodeError as exc:
            raise ContractError("INVALID_JSON", "artifact body is not UTF-8 JSON") from exc
        if not isinstance(value, dict):
            raise ContractError("SCHEMA_VALIDATION", "artifact body is not a record object")
        self.registry.validate(value, kind=artifact_kind, version=artifact_schema_version)
        validate_typed_id(
            artifact_id,
            expected_prefix=entry.id_prefix,
            id_origin=str(value.get("id_origin", "native")),
        )
        expected = {
            "id": artifact_id,
            "kind": artifact_kind,
            "schema_version": artifact_schema_version,
            "classification": classification,
        }
        if any(value.get(field) != expected_value for field, expected_value in expected.items()):
            raise ContractError(
                "ARTIFACT_IDENTITY_MISMATCH",
                "artifact metadata differs from its registered body",
            )
        return value

    def _load_binding(self, reference: Mapping[str, Any], binding_path: Path) -> dict[str, Any]:
        if not binding_path.exists():
            raise ContractError("STORE_CORRUPT", "artifact storage binding is missing")
        binding = _load_private_json(binding_path)
        self.registry.validate(binding)
        if (
            binding.get("artifact_ref_id") != reference.get("id")
            or binding.get("storage_class") != reference.get("storage_class")
            or binding.get("created_at") != reference.get("created_at")
            or binding.get("locator") != self.cas._locator(str(reference.get("digest")))
        ):
            raise ContractError("BINDING_MISMATCH", "storage binding disagrees with artifact reference")
        return binding

    def put(
        self,
        *,
        artifact_id: str,
        artifact_kind: str,
        artifact_schema_version: str,
        body: bytes,
        media_type: str,
        classification: str,
        created_by: str,
        provenance_parents: Iterable[str] = (),
        expected_digest: str | None = None,
        created_at: str | None = None,
    ) -> dict[str, Any]:
        artifact_body = self._validate_artifact_body(
            artifact_id=artifact_id,
            artifact_kind=artifact_kind,
            artifact_schema_version=artifact_schema_version,
            body=body,
            media_type=media_type,
            classification=classification,
            for_write=True,
        )
        ref_path, binding_path = self._record_paths(artifact_id)
        parents = sorted(set(provenance_parents), key=utf16_sort_key)
        with self.cas._digest_lock(f"artifact:{artifact_id}"):
            if ref_path.exists():
                existing = _load_private_json(ref_path)
                self.registry.validate(existing)
                self._load_binding(existing, binding_path)
                if existing["availability"] != "available":
                    raise ContractError("ARTIFACT_UNAVAILABLE", "artifact is not available for use")
                intended_digest = sha256_bytes(body)
                if expected_digest is not None and expected_digest != intended_digest:
                    raise ContractError("DIGEST_MISMATCH", "artifact body differs from expected digest")
                intended = {
                    "artifact_id": artifact_id,
                    "artifact_id_origin": str(artifact_body.get("id_origin", "native")),
                    "artifact_kind": artifact_kind,
                    "artifact_schema_version": artifact_schema_version,
                    "digest": intended_digest,
                    "media_type": media_type,
                    "size_bytes": len(body),
                    "classification": classification,
                    "created_by": created_by,
                    "provenance_parents": parents,
                    "storage_class": "private_content_addressed",
                    "availability": "available",
                }
                if any(existing.get(field) != value for field, value in intended.items()):
                    raise ContractError("IMMUTABLE_ID_CONFLICT", "artifact ID already binds other metadata")
                if created_at is not None and existing.get("created_at") != created_at:
                    raise ContractError("IMMUTABLE_ID_CONFLICT", "artifact ID already binds another time")
                if self.cas._verify_internal(existing["digest"])["result"] != "verified":
                    raise ContractError("ARTIFACT_UNAVAILABLE", "artifact body is unavailable")
                return existing
            blob = self.cas.put_bytes(
                body,
                classification=classification,
                expected_digest=expected_digest,
            )
            timestamp = created_at or utc_now()
            reference = {
                "schema_version": "1.0.0",
                "id": new_typed_id("aref"),
                "kind": "ArtifactRef",
                "artifact_id": artifact_id,
                "artifact_id_origin": str(artifact_body.get("id_origin", "native")),
                "artifact_kind": artifact_kind,
                "artifact_schema_version": artifact_schema_version,
                "digest": blob.digest,
                "media_type": media_type,
                "size_bytes": blob.size_bytes,
                "classification": classification,
                "storage_class": "private_content_addressed",
                "created_by": created_by,
                "created_at": timestamp,
                "provenance_parents": parents,
                "availability": "available",
            }
            binding = {
                "schema_version": "1.0.0",
                "id": new_typed_id("bind"),
                "kind": "StorageBinding",
                "artifact_ref_id": reference["id"],
                "storage_class": "private_content_addressed",
                "locator": blob.locator,
                "classification": "restricted_source"
                if _classification_rank(classification) >= _classification_rank("restricted_source")
                else "private_operational",
                "created_at": timestamp,
            }
            self.registry.validate(reference)
            self.registry.validate(binding)
            _atomic_write_bytes(binding_path, canonicalize(binding) + b"\n")
            _atomic_write_bytes(ref_path, canonicalize(reference) + b"\n")
            return reference

    def head(self, artifact_id: str, authority: ArtifactAuthority) -> dict[str, Any]:
        authority.require("artifact.read", artifact_id)
        ref_path, binding_path = self._record_paths(artifact_id)
        if not ref_path.exists():
            raise ContractError("ARTIFACT_UNAVAILABLE", "artifact is unavailable")
        reference = _load_private_json(ref_path)
        self.registry.validate(reference)
        if reference["artifact_id"] != artifact_id:
            raise ContractError("ARTIFACT_IDENTITY_MISMATCH", "artifact reference uses another identity")
        if _classification_rank(reference["classification"]) > _classification_rank(
            authority.classification_ceiling
        ):
            raise ContractError("ACCESS_DENIED", "artifact access is not authorized")
        self._load_binding(reference, binding_path)
        if reference["availability"] != "available":
            return reference
        label = self.cas._head_internal(reference["digest"])
        if label["size_bytes"] != reference["size_bytes"]:
            raise ContractError("STORE_CORRUPT", "artifact reference size disagrees with storage")
        if _classification_rank(label["classification"]) > _classification_rank(
            authority.classification_ceiling
        ):
            raise ContractError("ACCESS_DENIED", "artifact access is not authorized")
        return reference

    def get(self, artifact_id: str, authority: ArtifactAuthority) -> bytes:
        reference = self.head(artifact_id, authority)
        if reference["availability"] != "available":
            raise ContractError("ARTIFACT_UNAVAILABLE", "artifact is not available for use")
        _, binding_path = self._record_paths(artifact_id)
        binding = self._load_binding(reference, binding_path)
        body = self.cas.get_bytes(
            reference["digest"],
            authority,
            resource=artifact_id,
            locator=binding["locator"],
        )
        self._validate_artifact_body(
            artifact_id=artifact_id,
            artifact_kind=reference["artifact_kind"],
            artifact_schema_version=reference["artifact_schema_version"],
            body=body,
            media_type=reference["media_type"],
            classification=reference["classification"],
            for_write=False,
        )
        return body

    def verify(self, artifact_id: str, authority: ArtifactAuthority) -> dict[str, Any]:
        reference = self.head(artifact_id, authority)
        self.get(artifact_id, authority)
        result = self.cas.verify(reference["digest"], authority, resource=artifact_id)
        if result["result"] != "verified":
            raise ContractError("ARTIFACT_UNAVAILABLE", "artifact body is unavailable")
        return {"artifact_id": artifact_id, **result}

    def materialize(
        self,
        artifact_id: str,
        destination: Path,
        authority: ArtifactAuthority,
    ) -> dict[str, Any]:
        if destination.exists() or destination.is_symlink():
            raise ContractError("OUTPUT_EXISTS", "materialization destination must be fresh")
        body = self.get(artifact_id, authority)
        reference = self.head(artifact_id, authority)
        destination.parent.mkdir(parents=True, exist_ok=True)
        _atomic_write_bytes(
            destination,
            body,
            no_clobber=True,
            secure_parent=False,
        )
        if sha256_bytes(destination.read_bytes()) != reference["digest"]:
            destination.unlink(missing_ok=True)
            raise ContractError("DIGEST_MISMATCH", "materialized artifact failed verification")
        return {
            "artifact_id": artifact_id,
            "destination_digest": reference["digest"],
            "size_bytes": len(body),
            "result": "materialized",
        }


def _normalize_tree_path(path: str) -> str:
    if "\x00" in path or "\\" in path or unicodedata.normalize("NFC", path) != path:
        raise ContractError("INVALID_CANDIDATE_PATH", "candidate path is not normalized NFC POSIX")
    pure = PurePosixPath(path)
    if (
        pure.is_absolute()
        or not pure.parts
        or pure.as_posix() != path
        or any(part in {"", ".", ".."} for part in pure.parts)
    ):
        raise ContractError("INVALID_CANDIDATE_PATH", "candidate path is absolute or traversing")
    return pure.as_posix()


@dataclass(frozen=True)
class TreeFile:
    path: str
    executable: bool
    size_bytes: int
    digest: str
    body: bytes = dataclasses.field(repr=False, compare=False)

    def manifest_entry(self) -> dict[str, Any]:
        return {
            "path": self.path,
            "entry_type": "file",
            "executable": self.executable,
            "size_bytes": self.size_bytes,
            "digest": self.digest,
        }


def _stable_file_read(path: Path, maximum_bytes: int) -> tuple[bytes, os.stat_result]:
    try:
        initial = path.lstat()
    except OSError as exc:
        raise ContractError("CANDIDATE_MUTATED", "candidate changed during snapshot") from exc
    if not stat.S_ISREG(initial.st_mode) or initial.st_nlink != 1:
        raise ContractError("UNSUPPORTED_CANDIDATE_ENTRY", "candidate contains a link or non-file")
    if initial.st_size > maximum_bytes:
        raise ContractError("CANDIDATE_TOO_LARGE", "candidate file exceeds the configured limit")
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        descriptor = os.open(path, flags)
    except OSError as exc:
        if exc.errno in {errno.ELOOP, errno.ENOENT}:
            raise ContractError("CANDIDATE_MUTATED", "candidate changed during snapshot") from exc
        raise
    try:
        before = os.fstat(descriptor)
        if not stat.S_ISREG(before.st_mode) or before.st_nlink != 1:
            raise ContractError("UNSUPPORTED_CANDIDATE_ENTRY", "opened candidate is not a single-link file")
        initial_identity = (
            initial.st_dev,
            initial.st_ino,
            initial.st_mode,
            initial.st_nlink,
            initial.st_size,
            initial.st_mtime_ns,
            initial.st_ctime_ns,
        )
        opened_identity = (
            before.st_dev,
            before.st_ino,
            before.st_mode,
            before.st_nlink,
            before.st_size,
            before.st_mtime_ns,
            before.st_ctime_ns,
        )
        if initial_identity != opened_identity:
            raise ContractError("CANDIDATE_MUTATED", "candidate changed before its stable open")
        chunks: list[bytes] = []
        total = 0
        while True:
            chunk = os.read(descriptor, min(1024 * 1024, maximum_bytes + 1 - total))
            if not chunk:
                break
            chunks.append(chunk)
            total += len(chunk)
            if total > maximum_bytes:
                raise ContractError("CANDIDATE_TOO_LARGE", "candidate file exceeds the configured limit")
        after = os.fstat(descriptor)
    finally:
        os.close(descriptor)
    try:
        final = path.lstat()
    except OSError as exc:
        raise ContractError("CANDIDATE_MUTATED", "candidate changed during snapshot") from exc
    if not stat.S_ISREG(final.st_mode) or final.st_nlink != 1:
        raise ContractError("CANDIDATE_MUTATED", "candidate changed file type during snapshot")
    identity_before = (
        before.st_dev,
        before.st_ino,
        before.st_mode,
        before.st_nlink,
        before.st_size,
        before.st_mtime_ns,
        before.st_ctime_ns,
    )
    identity_after = (
        after.st_dev,
        after.st_ino,
        after.st_mode,
        after.st_nlink,
        after.st_size,
        after.st_mtime_ns,
        after.st_ctime_ns,
    )
    identity_final = (
        final.st_dev,
        final.st_ino,
        final.st_mode,
        final.st_nlink,
        final.st_size,
        final.st_mtime_ns,
        final.st_ctime_ns,
    )
    if identity_before != identity_after or identity_after != identity_final:
        raise ContractError("CANDIDATE_MUTATED", "candidate changed during snapshot")
    return b"".join(chunks), final


def snapshot_tree(
    root: Path,
    *,
    maximum_file_bytes: int = MAX_FILE_BYTES,
    maximum_tree_bytes: int = MAX_TREE_BYTES,
    maximum_tree_files: int = MAX_TREE_FILES,
) -> tuple[list[TreeFile], str]:
    root = root.absolute()
    if not root.is_dir() or root.is_symlink():
        raise ContractError("INVALID_CANDIDATE_ROOT", "candidate root must be a real directory")
    root_before = root.stat()
    discovered: list[Path] = []
    directory_snapshots: dict[Path, tuple[int, int, int, int]] = {}
    collision_keys: set[str] = set()

    def traversal_error(exc: OSError) -> None:
        raise ContractError("CANDIDATE_UNREADABLE", "candidate traversal could not read a subtree") from exc

    for directory_name, directory_names, file_names in os.walk(
        root,
        followlinks=False,
        onerror=traversal_error,
    ):
        directory = Path(directory_name)
        info = directory.lstat()
        if not stat.S_ISDIR(info.st_mode):
            raise ContractError("UNSUPPORTED_CANDIDATE_ENTRY", "candidate contains a linked directory")
        directory_snapshots[directory] = (info.st_dev, info.st_ino, info.st_mtime_ns, info.st_ctime_ns)
        for name in list(directory_names):
            candidate = directory / name
            if candidate.is_symlink():
                raise ContractError("UNSUPPORTED_CANDIDATE_ENTRY", "candidate contains a symlink")
            relative = _normalize_tree_path(candidate.relative_to(root).as_posix())
            collision = ascii_casefold_path(relative)
            if collision in collision_keys:
                raise ContractError(
                    "CANDIDATE_PATH_COLLISION",
                    "candidate paths collide after case folding",
                )
            collision_keys.add(collision)
        for name in file_names:
            candidate = directory / name
            if candidate.is_symlink():
                raise ContractError("UNSUPPORTED_CANDIDATE_ENTRY", "candidate contains a symlink")
            discovered.append(candidate)
            if len(discovered) > maximum_tree_files:
                raise ContractError("CANDIDATE_TOO_LARGE", "candidate exceeds the configured file count")

    files: list[TreeFile] = []
    total_size = 0
    for path in sorted(
        discovered,
        key=lambda item: utf16_sort_key(item.relative_to(root).as_posix()),
    ):
        relative = _normalize_tree_path(path.relative_to(root).as_posix())
        collision = ascii_casefold_path(relative)
        if collision in collision_keys:
            raise ContractError("CANDIDATE_PATH_COLLISION", "candidate paths collide after case folding")
        collision_keys.add(collision)
        body, info = _stable_file_read(path, maximum_file_bytes)
        total_size += len(body)
        if total_size > maximum_tree_bytes:
            raise ContractError("CANDIDATE_TOO_LARGE", "candidate exceeds the configured total size")
        files.append(
            TreeFile(
                path=relative,
                executable=bool(info.st_mode & 0o111),
                size_bytes=len(body),
                digest=sha256_bytes(body),
                body=body,
            )
        )

    # Re-read after the complete traversal. This prevents a multi-file freeze
    # from silently combining bytes from different draft epochs.
    for item in files:
        body, info = _stable_file_read(root.joinpath(*PurePosixPath(item.path).parts), maximum_file_bytes)
        if (
            sha256_bytes(body) != item.digest
            or len(body) != item.size_bytes
            or bool(info.st_mode & 0o111) != item.executable
        ):
            raise ContractError("CANDIDATE_MUTATED", "candidate changed during snapshot")

    for directory, expected in directory_snapshots.items():
        try:
            current = directory.lstat()
        except OSError as exc:
            raise ContractError("CANDIDATE_MUTATED", "candidate directory changed during snapshot") from exc
        actual = (current.st_dev, current.st_ino, current.st_mtime_ns, current.st_ctime_ns)
        if actual != expected:
            raise ContractError("CANDIDATE_MUTATED", "candidate directory changed during snapshot")
    try:
        root_after = root.stat()
    except OSError as exc:
        raise ContractError("CANDIDATE_MUTATED", "candidate root changed during snapshot") from exc
    if (root_before.st_dev, root_before.st_ino) != (root_after.st_dev, root_after.st_ino):
        raise ContractError("CANDIDATE_MUTATED", "candidate root changed during snapshot")
    manifest = [item.manifest_entry() for item in files]
    return files, canonical_digest(manifest)


def _path_is_within(path: str, root: str) -> bool:
    return path == root or path.startswith(f"{root}/")


class EditableSurfacePolicy:
    """Authority-owned, digest-bound path policy for candidate freezing."""

    def __init__(
        self,
        *,
        policy_id: str,
        roots_by_surface: Mapping[str, Iterable[str]],
        locked_paths: Iterable[str] = (),
    ) -> None:
        if not policy_id:
            raise ContractError("EDITABLE_POLICY_INVALID", "editable-surface policy ID is empty")
        normalized: dict[str, tuple[str, ...]] = {}
        for surface, roots in roots_by_surface.items():
            if not isinstance(surface, str) or not surface:
                raise ContractError("EDITABLE_POLICY_INVALID", "editable-surface name is invalid")
            if isinstance(roots, (str, bytes)):
                raise ContractError("EDITABLE_POLICY_INVALID", "editable-surface roots must be a list")
            root_values = tuple(roots)
            if not all(isinstance(root, str) for root in root_values):
                raise ContractError("EDITABLE_POLICY_INVALID", "editable-surface root is invalid")
            values = tuple(
                sorted({_normalize_tree_path(root) for root in root_values}, key=utf16_sort_key)
            )
            if not values:
                raise ContractError("EDITABLE_POLICY_INVALID", "editable surface has no allowed roots")
            normalized[surface] = values
        self.policy_id = policy_id
        self._roots_by_surface = normalized
        if isinstance(locked_paths, (str, bytes)):
            raise ContractError("EDITABLE_POLICY_INVALID", "locked paths must be a list")
        locked_values = tuple(locked_paths)
        if not all(isinstance(path, str) for path in locked_values):
            raise ContractError("EDITABLE_POLICY_INVALID", "locked path is invalid")
        self._locked_paths = tuple(
            sorted({_normalize_tree_path(path) for path in locked_values}, key=utf16_sort_key)
        )
        document = {
            "schema_version": "1.0.0",
            "policy_id": policy_id,
            "surfaces": [
                {"name": name, "roots": list(normalized[name])}
                for name in sorted(normalized, key=utf16_sort_key)
            ],
            "locked_paths": list(self._locked_paths),
        }
        self.digest = canonical_digest(document)

    def enforce(self, candidate: Mapping[str, Any], files: Iterable[TreeFile]) -> None:
        surface = str(candidate["target_editable_surface"])
        roots = self._roots_by_surface.get(surface)
        if roots is None:
            raise ContractError("EDITABLE_SURFACE_DENIED", "candidate editable surface is not authorized")
        declared = tuple(
            sorted(
                {_normalize_tree_path(str(path)) for path in candidate["declared_changed_surfaces"]},
                key=utf16_sort_key,
            )
        )
        actual = tuple(sorted((item.path for item in files), key=utf16_sort_key))
        if declared != actual:
            raise ContractError(
                "DECLARED_SURFACE_MISMATCH",
                "candidate tree differs from its declared changed surfaces",
            )
        for path in actual:
            if not any(_path_is_within(path, root) for root in roots):
                raise ContractError(
                    "EDITABLE_SURFACE_DENIED",
                    "candidate path is outside its editable surface",
                )
            if any(_path_is_within(path, locked) for locked in self._locked_paths):
                raise ContractError("EDITABLE_SURFACE_DENIED", "candidate path is locked by policy")


class CandidateFreezer:
    """Freeze candidate trees into CAS before evaluators can observe them."""

    def __init__(
        self,
        store: LocalContentAddressedStore,
        *,
        editable_surface_policy: EditableSurfacePolicy,
        registry: SchemaRegistry | None = None,
    ):
        self.store = store
        self.registry = registry or SchemaRegistry.load()
        self.editable_surface_policy = editable_surface_policy
        self.freeze_policy_digest = canonical_digest(
            {
                "base_policy_digest": FREEZE_POLICY_DIGEST,
                "editable_surface_policy_digest": editable_surface_policy.digest,
            }
        )
        self.receipts = self.store.root / "freeze-receipts"
        _secure_directory(self.receipts)

    def _receipt_path(self, candidate_id: str) -> Path:
        key = sha256_bytes(candidate_id.encode("utf-8")).removeprefix("sha256:")
        return self.receipts / f"{key}.json"

    def freeze(
        self,
        candidate: Mapping[str, Any],
        draft_root: Path,
        *,
        expected_draft_digest: str,
        frozen_at: str | None = None,
    ) -> dict[str, Any]:
        self.registry.validate(candidate)
        candidate_id = str(candidate["id"])
        candidate_record_digest = canonical_digest(dict(candidate))
        schema_registry_digest = sha256_bytes(self.registry.path.read_bytes())
        if candidate["draft_tree_digest"] != expected_draft_digest:
            raise ContractError("DRAFT_DIGEST_CONFLICT", "freeze expectation differs from candidate record")
        receipt_path = self._receipt_path(candidate_id)
        with self.store._digest_lock(f"freeze:{candidate_id}"):
            if receipt_path.exists():
                existing = _load_private_json(receipt_path)
                if (
                    existing.get("expected_draft_digest") != expected_draft_digest
                    or existing.get("candidate_record_digest") != candidate_record_digest
                    or existing.get("schema_registry_digest") != schema_registry_digest
                    or existing.get("freeze_policy_digest") != self.freeze_policy_digest
                ):
                    raise ContractError("FROZEN_CANDIDATE_CONFLICT", "candidate ID is already frozen")
                self.registry.validate(existing)
                for entry in existing["entries"]:
                    result = self.store._verify_internal(entry["digest"])
                    if result["result"] != "verified":
                        raise ContractError("ARTIFACT_UNAVAILABLE", "frozen candidate body is unavailable")
                return existing
            files, tree_digest = snapshot_tree(draft_root)
            if tree_digest != expected_draft_digest:
                raise ContractError("DRAFT_CHANGED", "candidate draft changed before freeze")
            self.editable_surface_policy.enforce(candidate, files)
            classification = str(candidate["classification"])
            for item in files:
                self.store.put_bytes(
                    item.body,
                    classification=classification,
                    expected_digest=item.digest,
                )
            receipt = {
                "schema_version": "1.0.0",
                "id": new_typed_id("freeze"),
                "kind": "FreezeReceipt",
                "candidate_id": candidate_id,
                "candidate_record_digest": candidate_record_digest,
                "root_production_epoch": candidate["root_production_epoch"],
                "expected_draft_digest": expected_draft_digest,
                "tree_digest": tree_digest,
                "schema_registry_digest": schema_registry_digest,
                "freeze_policy_digest": self.freeze_policy_digest,
                "entries": [item.manifest_entry() for item in files],
                "file_count": len(files),
                "total_size_bytes": sum(item.size_bytes for item in files),
                "classification": "private_operational",
                "frozen_at": frozen_at or utc_now(),
            }
            self.registry.validate(receipt)
            _atomic_write_bytes(receipt_path, canonicalize(receipt) + b"\n")
            return receipt

    def materialize(
        self,
        receipt: Mapping[str, Any],
        destination: Path,
        authority: ArtifactAuthority,
    ) -> dict[str, Any]:
        self.registry.validate(receipt)
        if receipt["freeze_policy_digest"] != self.freeze_policy_digest:
            raise ContractError("FREEZE_POLICY_MISMATCH", "freeze receipt uses another editable policy")
        if destination.exists() or destination.is_symlink():
            raise ContractError("OUTPUT_EXISTS", "candidate materialization destination must be fresh")
        parent = destination.absolute().parent
        parent.mkdir(parents=True, exist_ok=True)
        if parent.is_symlink() or not parent.is_dir():
            raise ContractError("OUTPUT_PATH_INVALID", "output parent must be a real directory")
        temporary = Path(tempfile.mkdtemp(prefix=f".{destination.name}.", dir=parent))
        try:
            for entry in receipt["entries"]:
                relative = _normalize_tree_path(entry["path"])
                body = self.store.get_bytes(
                    entry["digest"],
                    authority,
                    resource=receipt["candidate_id"],
                )
                if len(body) != entry["size_bytes"] or sha256_bytes(body) != entry["digest"]:
                    raise ContractError("DIGEST_MISMATCH", "frozen candidate body is inconsistent")
                target = temporary.joinpath(*PurePosixPath(relative).parts)
                _atomic_write_bytes(target, body, mode=0o700 if entry["executable"] else 0o600)
            _, materialized_digest = snapshot_tree(temporary)
            if materialized_digest != receipt["tree_digest"]:
                raise ContractError("DIGEST_MISMATCH", "materialized candidate tree differs from receipt")
            _publish_directory_no_clobber(temporary, destination)
            _fsync_directory(parent)
            return {
                "candidate_id": receipt["candidate_id"],
                "tree_digest": materialized_digest,
                "result": "materialized",
            }
        except Exception:
            shutil.rmtree(temporary, ignore_errors=True)
            raise


def grant_digest(grant: Mapping[str, Any]) -> str:
    body = {key: value for key, value in grant.items() if key != "grant_digest"}
    return canonical_digest(body)


@dataclass(frozen=True, repr=False)
class CredentialLease:
    credential_ref_id: str
    operation: str
    resource: str
    _value: str = dataclasses.field(repr=False)

    def __repr__(self) -> str:
        return (
            "CredentialLease(credential_ref_id="
            f"{self.credential_ref_id!r}, operation={self.operation!r}, resource={self.resource!r}, "
            "value=<redacted>)"
        )

    def value_for_adapter(self) -> str:
        return self._value


@dataclass(frozen=True)
class _IssuedCapability:
    token: str
    grant: Mapping[str, Any] = dataclasses.field(repr=False)


class FakeCapabilityProvider:
    """Non-authoritative, one-use conformance fake.

    The grant digest is an integrity check, not an issuer signature. Production
    actor authentication and credential resolution belong to SPEC-024.
    """

    def __init__(
        self,
        secrets_by_reference: Mapping[str, str],
        *,
        resource_classifications: Mapping[str, str],
    ):
        self._secrets = dict(secrets_by_reference)
        if not all(
            isinstance(reference, str)
            and reference
            and isinstance(value, str)
            for reference, value in self._secrets.items()
        ):
            raise ContractError("CAPABILITY_PROVIDER_INVALID", "credential fixture mapping is invalid")
        self._resource_classifications = dict(resource_classifications)
        if not all(
            isinstance(resource, str) and resource
            for resource in self._resource_classifications
        ):
            raise ContractError("CAPABILITY_PROVIDER_INVALID", "resource classification mapping is invalid")
        for classification in self._resource_classifications.values():
            if not isinstance(classification, str):
                raise ContractError(
                    "CAPABILITY_PROVIDER_INVALID",
                    "resource classification mapping is invalid",
                )
            _classification_rank(classification)
        self._issued: dict[str, _IssuedCapability] = {}
        self._lock = threading.Lock()

    def issue(
        self,
        grant: Mapping[str, Any],
        credential_ref: Mapping[str, Any],
        *,
        audience: str,
        now: datetime,
        registry: SchemaRegistry | None = None,
    ) -> str:
        _require_aware_time(now)
        schema_registry = registry or SchemaRegistry.load()
        schema_registry.validate(grant)
        schema_registry.validate(credential_ref)
        if grant["grant_digest"] != grant_digest(grant):
            raise ContractError("GRANT_DIGEST_MISMATCH", "capability grant digest is invalid")
        if grant["credential_ref_id"] != credential_ref["id"]:
            raise ContractError("CREDENTIAL_MISMATCH", "grant and credential reference differ")
        if audience != grant["audience"]:
            raise ContractError("AUDIENCE_MISMATCH", "capability audience is not authorized")
        if not set(grant["operations"]).issubset(set(credential_ref["allowed_operations"])):
            raise ContractError("OPERATION_DENIED", "grant exceeds credential operation policy")
        issued_at = datetime.fromisoformat(str(grant["issued_at"]).replace("Z", "+00:00"))
        expires_at = datetime.fromisoformat(str(grant["expires_at"]).replace("Z", "+00:00"))
        if issued_at > now or expires_at <= now or expires_at <= issued_at:
            raise ContractError("CAPABILITY_EXPIRED", "capability grant is outside its validity window")
        if credential_ref["id"] not in self._secrets:
            raise ContractError("CREDENTIAL_UNAVAILABLE", "credential reference cannot be resolved")
        if any(resource not in self._resource_classifications for resource in grant["resources"]):
            raise ContractError("RESOURCE_UNAVAILABLE", "grant resource has no authoritative classification")
        token = f"cap_{secrets.token_urlsafe(32)}"
        with self._lock:
            self._issued[token] = _IssuedCapability(token, dict(grant))
        return token

    def resolve(
        self,
        token: str,
        *,
        audience: str,
        operation: str,
        resource: str,
        work_order_id: str,
        attempt_id: str,
        now: datetime,
    ) -> CredentialLease:
        _require_aware_time(now)
        with self._lock:
            issued = self._issued.pop(token, None)
        if issued is None:
            raise ContractError("CAPABILITY_INVALID", "capability is invalid or already consumed")
        grant = issued.grant
        expires_at = datetime.fromisoformat(str(grant["expires_at"]).replace("Z", "+00:00"))
        checks = (
            (audience == grant["audience"], "AUDIENCE_MISMATCH"),
            (operation in grant["operations"], "OPERATION_DENIED"),
            (resource in grant["resources"], "RESOURCE_DENIED"),
            (work_order_id == grant["work_order_id"], "WORK_ORDER_MISMATCH"),
            (attempt_id == grant["attempt_id"], "ATTEMPT_MISMATCH"),
            (now < expires_at, "CAPABILITY_EXPIRED"),
        )
        for passed, code in checks:
            if not passed:
                raise ContractError(code, "capability scope check failed")
        resource_classification = self._resource_classifications.get(resource)
        if resource_classification is None:
            raise ContractError("RESOURCE_UNAVAILABLE", "resource classification is unavailable")
        if _classification_rank(resource_classification) > _classification_rank(
            grant["classification_ceiling"]
        ):
            raise ContractError("CLASSIFICATION_DENIED", "capability scope check failed")
        credential_ref_id = str(grant["credential_ref_id"])
        value = self._secrets.get(credential_ref_id)
        if value is None:
            raise ContractError("CREDENTIAL_UNAVAILABLE", "credential reference cannot be resolved")
        return CredentialLease(credential_ref_id, operation, resource, value)
