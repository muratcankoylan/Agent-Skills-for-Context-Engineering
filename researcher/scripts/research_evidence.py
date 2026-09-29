#!/usr/bin/env python3
"""Private exact-byte discovery captures, outside accepted SPEC artifact state.

Records here prove which HTTP bytes a local connector observed. They neither
accept a paper nor issue an ArtifactRef, StorageBinding, or publication grant.
"""

from __future__ import annotations

import contextlib
import fcntl
import hashlib
import ipaddress
import json
import os
from pathlib import Path
import re
import secrets
import stat
from dataclasses import asdict, dataclass
from typing import Iterator, Mapping
from urllib.parse import urlsplit

if __package__:
    from .source_connectors import (
        ABSOLUTE_MAX_BYTES,
        SAFE_RESPONSE_HEADERS,
        ResponseObservation,
    )
else:
    from source_connectors import (
        ABSOLUTE_MAX_BYTES,
        SAFE_RESPONSE_HEADERS,
        ResponseObservation,
    )

MAX_METADATA_BYTES = 32_768
_FORMAT = "local-research-observation-v1"
_DIGEST = re.compile(r"sha256:[0-9a-f]{64}\Z")


class ResearchEvidenceError(RuntimeError):
    def __init__(self, code: str, message: str):
        super().__init__(message)
        self.code = code


def _error(code: str = "EVIDENCE_INVALID") -> ResearchEvidenceError:
    return ResearchEvidenceError(code, "private research evidence failed validation")


def _digest(body: bytes) -> str:
    return "sha256:" + hashlib.sha256(body).hexdigest()


@dataclass(frozen=True, slots=True)
class CapturedEvidence:
    body_sha256: str
    metadata_sha256: str
    size_bytes: int
    observation_only: bool = True
    authoritative: bool = False

    def __post_init__(self) -> None:
        if any(
            not isinstance(value, str) or not _DIGEST.fullmatch(value)
            for value in (self.body_sha256, self.metadata_sha256)
        ):
            raise _error()
        if (
            type(self.size_bytes) is not int
            or not 0 <= self.size_bytes <= ABSOLUTE_MAX_BYTES
        ):
            raise _error()
        if self.observation_only is not True or self.authoritative is not False:
            raise _error()

    def as_record(self) -> dict[str, object]:
        return asdict(self)

    @classmethod
    def from_record(cls, record: Mapping[str, object]) -> CapturedEvidence:
        if not isinstance(record, Mapping) or set(record) != {
            "body_sha256",
            "metadata_sha256",
            "size_bytes",
            "observation_only",
            "authoritative",
        }:
            raise _error()
        return cls(**dict(record))


def _bounded_string(value: object, maximum: int, *, allow_empty: bool = False) -> str:
    if (
        not isinstance(value, str)
        or len(value) > maximum
        or (not value and not allow_empty)
        or any(ord(character) < 32 or ord(character) == 127 for character in value)
    ):
        raise _error()
    return value


def _observation_record(observation: ResponseObservation) -> dict[str, object]:
    if not isinstance(observation, ResponseObservation):
        raise _error()
    url = _bounded_string(observation.request_url, 8_192)
    try:
        parsed = urlsplit(url)
        if (
            parsed.scheme != "https"
            or not parsed.hostname
            or parsed.query
            or parsed.fragment
            or parsed.username is not None
            or parsed.password is not None
            or parsed.port not in (None, 443)
        ):
            raise _error()
    except ValueError:
        raise _error() from None
    if (
        type(observation.query_redacted) is not bool
        or type(observation.truncated) is not bool
    ):
        raise _error()
    if (
        not isinstance(observation.resolved_ips, tuple)
        or not 1 <= len(observation.resolved_ips) <= 32
    ):
        raise _error()
    try:
        for address in observation.resolved_ips:
            if not ipaddress.ip_address(_bounded_string(address, 64)).is_global:
                raise _error()
    except ValueError:
        raise _error() from None
    if observation.connected_ip not in observation.resolved_ips:
        raise _error()
    for value, minimum, maximum in (
        (observation.status_code, 100, 599),
        (observation.response_bytes, 0, ABSOLUTE_MAX_BYTES),
        (observation.elapsed_ms, 0, 3_600_000),
    ):
        if type(value) is not int or not minimum <= value <= maximum:
            raise _error()
    if not isinstance(observation.response_sha256, str) or not _DIGEST.fullmatch(
        observation.response_sha256
    ):
        raise _error()
    _bounded_string(observation.media_type, 256, allow_empty=True)
    if (
        not isinstance(observation.safe_headers, tuple)
        or len(observation.safe_headers) > 64
    ):
        raise _error()
    for header in observation.safe_headers:
        if not isinstance(header, tuple) or len(header) != 2:
            raise _error()
        name, value = header
        if name not in SAFE_RESPONSE_HEADERS:
            raise _error()
        _bounded_string(value, 4_096, allow_empty=True)
    return asdict(observation)


def _canonical_record(observation: ResponseObservation) -> bytes:
    record = {
        "format": _FORMAT,
        "observation_only": True,
        "authoritative": False,
        "observation": _observation_record(observation),
    }
    body = json.dumps(
        record, sort_keys=True, separators=(",", ":"), ensure_ascii=True
    ).encode("ascii")
    if len(body) > MAX_METADATA_BYTES:
        raise _error("EVIDENCE_METADATA_LIMIT")
    return body


def _strict_object(pairs: list[tuple[str, object]]) -> dict[str, object]:
    record: dict[str, object] = {}
    for key, value in pairs:
        if key in record:
            raise _error()
        record[key] = value
    return record


def _decode_observation(body: bytes) -> ResponseObservation:
    try:
        record = json.loads(body, object_pairs_hook=_strict_object)
        if (
            not isinstance(record, dict)
            or set(record)
            != {"format", "observation_only", "authoritative", "observation"}
            or record["format"] != _FORMAT
            or record["observation_only"] is not True
            or record["authoritative"] is not False
        ):
            raise _error()
        value = record["observation"]
        if not isinstance(value, dict):
            raise _error()
        value["resolved_ips"] = tuple(value["resolved_ips"])
        value["safe_headers"] = tuple(tuple(pair) for pair in value["safe_headers"])
        observation = ResponseObservation(**value)
        # Canonical re-encoding also rejects unknown, missing or unbounded fields.
        if _canonical_record(observation) != body:
            raise _error()
        return observation
    except (ValueError, TypeError, KeyError, UnicodeError, RecursionError):
        raise _error() from None


def _directory_flags() -> int:
    if not hasattr(os, "O_NOFOLLOW") or not hasattr(os, "O_DIRECTORY"):
        raise _error("EVIDENCE_PLATFORM_UNSUPPORTED")
    return os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW


def _open_root(path: Path, *, create: bool) -> int:
    """Walk lexical components through dirfds; never resolve through a symlink."""
    if not path.is_absolute() or ".." in path.parts:
        raise _error("EVIDENCE_PATH_INVALID")
    descriptor = os.open(path.anchor, _directory_flags())
    try:
        for component in path.parts[1:]:
            if create:
                try:
                    os.mkdir(component, mode=0o700, dir_fd=descriptor)
                except FileExistsError:
                    pass
            child = os.open(component, _directory_flags(), dir_fd=descriptor)
            os.close(descriptor)
            descriptor = child
        info = os.fstat(descriptor)
        if info.st_mode & 0o077:
            raise _error("EVIDENCE_PATH_NOT_PRIVATE")
        return descriptor
    except BaseException:
        os.close(descriptor)
        raise


def _open_child(parent: int, name: str, *, create: bool = False) -> int:
    if create:
        try:
            os.mkdir(name, mode=0o700, dir_fd=parent)
        except FileExistsError:
            pass
    descriptor = os.open(name, _directory_flags(), dir_fd=parent)
    if os.fstat(descriptor).st_mode & 0o077:
        os.close(descriptor)
        raise _error("EVIDENCE_PATH_NOT_PRIVATE")
    return descriptor


class LocalResearchEvidenceStore:
    """Small private CAS. All writes are immutable, deduplicated local captures.

    Pass an absolute path with no symlink components. Existing roots must be
    private (0700); new roots are created privately. Each operation revalidates
    the root inode, walks children without following links, and takes a lock.
    """

    def __init__(self, root: Path | str, *, read_only: bool = False):
        if type(read_only) is not bool:
            raise _error("EVIDENCE_PATH_INVALID")
        self.read_only = read_only
        self.root = Path(root)
        try:
            descriptor = _open_root(self.root, create=not read_only)
            try:
                info = os.fstat(descriptor)
                self._identity = (info.st_dev, info.st_ino)
                for name in ("bodies", "observations"):
                    child = _open_child(descriptor, name, create=not read_only)
                    os.close(child)
                if read_only:
                    lock = os.open(
                        ".lock",
                        os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK,
                        dir_fd=descriptor,
                    )
                else:
                    try:
                        lock = os.open(
                            ".lock",
                            os.O_CREAT
                            | os.O_EXCL
                            | os.O_RDWR
                            | os.O_NOFOLLOW
                            | os.O_NONBLOCK,
                            0o600,
                            dir_fd=descriptor,
                        )
                    except FileExistsError:
                        lock = os.open(
                            ".lock",
                            os.O_RDWR | os.O_NOFOLLOW | os.O_NONBLOCK,
                            dir_fd=descriptor,
                        )
                try:
                    lock_info = os.fstat(lock)
                    if (
                        not stat.S_ISREG(lock_info.st_mode)
                        or lock_info.st_nlink != 1
                        or lock_info.st_mode & 0o077
                        or lock_info.st_size > 4096
                    ):
                        raise _error("EVIDENCE_PATH_INVALID")
                    self._lock_identity = (lock_info.st_dev, lock_info.st_ino)
                finally:
                    os.close(lock)
                if not read_only:
                    os.fsync(descriptor)
            finally:
                os.close(descriptor)
        except OSError:
            raise _error("EVIDENCE_PATH_INVALID") from None

    @contextlib.contextmanager
    def _locked(self, *, write: bool) -> Iterator[int]:
        if write and self.read_only:
            raise _error("EVIDENCE_READ_ONLY")
        root = lock = None
        try:
            root = _open_root(self.root, create=False)
            info = os.fstat(root)
            if (info.st_dev, info.st_ino) != self._identity:
                raise _error("EVIDENCE_ROOT_CHANGED")
            lock = os.open(
                ".lock",
                (os.O_RDONLY if self.read_only else os.O_RDWR)
                | os.O_NOFOLLOW
                | os.O_NONBLOCK,
                dir_fd=root,
            )
            info = os.fstat(lock)
            if (
                not stat.S_ISREG(info.st_mode)
                or info.st_nlink != 1
                or info.st_mode & 0o077
                or info.st_size > 4096
                or (info.st_dev, info.st_ino) != self._lock_identity
            ):
                raise _error("EVIDENCE_PATH_INVALID")
            flags = fcntl.LOCK_EX if write else fcntl.LOCK_SH
            fcntl.flock(lock, flags | (fcntl.LOCK_NB if self.read_only else 0))
            yield root
        except OSError:
            raise _error("EVIDENCE_IO") from None
        finally:
            if lock is not None:
                os.close(lock)
            if root is not None:
                os.close(root)

    @staticmethod
    def _read_blob(directory: int, digest: str, maximum: int) -> bytes:
        if not isinstance(digest, str) or not _DIGEST.fullmatch(digest):
            raise _error()
        descriptor = os.open(
            digest[7:], os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=directory
        )
        try:
            before = os.fstat(descriptor)
            if (
                not stat.S_ISREG(before.st_mode)
                or before.st_nlink != 1
                or before.st_mode & 0o077
                or before.st_size > maximum
            ):
                raise _error("EVIDENCE_CORRUPT")
            chunks: list[bytes] = []
            received = 0
            while received <= maximum:
                chunk = os.read(descriptor, min(65_536, maximum + 1 - received))
                if not chunk:
                    break
                chunks.append(chunk)
                received += len(chunk)
            after = os.fstat(descriptor)
            data = b"".join(chunks)
            if (
                (
                    before.st_dev,
                    before.st_ino,
                    before.st_size,
                    before.st_mtime_ns,
                    before.st_ctime_ns,
                )
                != (
                    after.st_dev,
                    after.st_ino,
                    after.st_size,
                    after.st_mtime_ns,
                    after.st_ctime_ns,
                )
                or received > maximum
                or _digest(data) != digest
            ):
                raise _error("EVIDENCE_DIGEST_MISMATCH")
            return data
        finally:
            os.close(descriptor)

    @classmethod
    def _put_blob(cls, directory: int, body: bytes, digest: str, maximum: int) -> None:
        temporary = ".capture-" + secrets.token_hex(16)
        descriptor = os.open(
            temporary,
            os.O_CREAT | os.O_EXCL | os.O_WRONLY | os.O_NOFOLLOW,
            0o600,
            dir_fd=directory,
        )
        try:
            with os.fdopen(descriptor, "wb", closefd=True) as handle:
                handle.write(body)
                handle.flush()
                os.fsync(handle.fileno())
            try:
                os.link(
                    temporary,
                    digest[7:],
                    src_dir_fd=directory,
                    dst_dir_fd=directory,
                    follow_symlinks=False,
                )
            except FileExistsError:
                if cls._read_blob(directory, digest, maximum) != body:
                    raise _error("EVIDENCE_DIGEST_MISMATCH")
        finally:
            os.unlink(temporary, dir_fd=directory)
        os.fsync(directory)
        if cls._read_blob(directory, digest, maximum) != body:
            raise _error("EVIDENCE_DIGEST_MISMATCH")

    def capture(
        self, observation: ResponseObservation, body: bytes
    ) -> CapturedEvidence:
        if not isinstance(body, bytes) or len(body) > ABSOLUTE_MAX_BYTES:
            raise _error("EVIDENCE_BODY_LIMIT")
        metadata = _canonical_record(observation)
        body_digest = _digest(body)
        if (
            observation.response_sha256 != body_digest
            or observation.response_bytes != len(body)
        ):
            raise _error("EVIDENCE_DIGEST_MISMATCH")
        record = CapturedEvidence(body_digest, _digest(metadata), len(body))
        with self._locked(write=True) as root:
            for name, data, digest, maximum in (
                ("bodies", body, record.body_sha256, ABSOLUTE_MAX_BYTES),
                ("observations", metadata, record.metadata_sha256, MAX_METADATA_BYTES),
            ):
                directory = _open_child(root, name)
                try:
                    self._put_blob(directory, data, digest, maximum)
                finally:
                    os.close(directory)
        return record

    def read(
        self, capture: CapturedEvidence | Mapping[str, object]
    ) -> tuple[ResponseObservation, bytes]:
        record = (
            capture
            if isinstance(capture, CapturedEvidence)
            else CapturedEvidence.from_record(capture)
        )
        with self._locked(write=False) as root:
            directory = _open_child(root, "observations")
            try:
                metadata = self._read_blob(
                    directory, record.metadata_sha256, MAX_METADATA_BYTES
                )
            finally:
                os.close(directory)
            observation = _decode_observation(metadata)
            if (
                observation.response_sha256 != record.body_sha256
                or observation.response_bytes != record.size_bytes
            ):
                raise _error("EVIDENCE_BINDING_MISMATCH")
            directory = _open_child(root, "bodies")
            try:
                body = self._read_blob(
                    directory, record.body_sha256, ABSOLUTE_MAX_BYTES
                )
            finally:
                os.close(directory)
            if len(body) != record.size_bytes:
                raise _error("EVIDENCE_BINDING_MISMATCH")
        return observation, body

    def read_body(self, capture: CapturedEvidence | Mapping[str, object]) -> bytes:
        return self.read(capture)[1]

    def read_observation(
        self, capture: CapturedEvidence | Mapping[str, object]
    ) -> ResponseObservation:
        return self.read(capture)[0]


__all__ = ["CapturedEvidence", "LocalResearchEvidenceStore", "ResearchEvidenceError"]
