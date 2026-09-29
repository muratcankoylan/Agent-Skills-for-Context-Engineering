"""
Sandbox Manager for Hosted Agent Infrastructure.

Use when: building background coding agents that need sandboxed execution
environments with pre-built images, warm pools, and session snapshots.

This module provides composable building blocks for sandbox lifecycle
management. Each class handles one concern (image building, warm pools,
session coordination) and can be used independently or combined via
SandboxManager.

This is preparatory, non-production pseudocode. It does not implement a real
sandbox, credential broker, authorization boundary, or supervisor. Adapt and
verify those provider-specific components before deployment.
"""

from __future__ import annotations

import asyncio
import hashlib
import re
import unicodedata
from collections.abc import AsyncIterator, Sequence
from contextlib import AbstractAsyncContextManager, asynccontextmanager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum
from pathlib import PurePosixPath
from threading import Lock
from typing import Any, Callable, Literal, Optional, Protocol
from urllib.parse import urlsplit
from uuid import UUID, uuid4

__all__ = [
    "SandboxState",
    "CommandSpec",
    "CredentialLeaseError",
    "WarmSyncError",
    "RepositoryAccessError",
    "SnapshotBindingError",
    "SnapshotBindingCollisionError",
    "SnapshotReconciliationRequiredError",
    "SessionHandleCollisionError",
    "MalformedSessionError",
    "SessionTerminationError",
    "SandboxCleanupError",
    "EphemeralGitCredential",
    "RepositoryAccessReceipt",
    "SessionSnapshotRef",
    "CreatedSnapshot",
    "ResolvedSnapshotBinding",
    "SnapshotBindingProvider",
    "SessionHandle",
    "SessionAllocation",
    "UserIdentity",
    "SandboxConfig",
    "ResourcePolicyAttestation",
    "Sandbox",
    "RepositoryImage",
    "ImageBuilder",
    "WarmSandbox",
    "WarmPoolManager",
    "SandboxManager",
    "AgentSession",
    "normalize_github_repository",
    "github_clone_url",
]


_GITHUB_OWNER_PATTERN = re.compile(r"[A-Za-z0-9](?:[A-Za-z0-9-]{0,37}[A-Za-z0-9])?\Z")
_GITHUB_REPOSITORY_PATTERN = re.compile(r"[A-Za-z0-9._-]{1,100}\Z")
_IDENTITY_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.-]{0,63}\Z")
_PINNED_IMAGE_PATTERN = re.compile(
    r"[A-Za-z0-9][A-Za-z0-9._/:-]{0,254}@sha256:[0-9a-f]{64}\Z"
)
_SNAPSHOT_ID_PATTERN = re.compile(r"[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}\Z")
_CONTENT_DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}\Z")
_GITHUB_EGRESS_POLICY_DIGEST = (
    "sha256:"
    + hashlib.sha256(
        b"https-only|github.com:443|no-redirects|no-forwarding|resolved-address-check"
    ).hexdigest()
)
_EMAIL_PATTERN = re.compile(
    r"[A-Za-z0-9!#$%&'*+/=?^_`{|}~.-]{1,64}"
    r"@(?:[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?\.)+"
    r"[A-Za-z]{2,63}\Z"
)
_FORBIDDEN_SHELLS = frozenset(
    {"bash", "cmd", "cmd.exe", "dash", "fish", "powershell", "pwsh", "sh", "zsh"}
)


def _has_control_character(value: str) -> bool:
    return any(unicodedata.category(character).startswith("C") for character in value)


def normalize_github_repository(value: str) -> str:
    """Return one lower-case ``owner/repository`` identity.

    Accepted inputs are an owner/repository slug or a credential-free HTTPS
    GitHub URL. SSH syntax, userinfo, ports, query strings, fragments, encoded
    characters, control characters, and extra path components fail closed.
    Errors deliberately exclude the rejected input so a token-bearing URL is
    not reflected into logs.
    """
    error = ValueError("Invalid GitHub repository identifier.")
    if not isinstance(value, str) or len(value) > 2_048:
        raise error

    normalized = unicodedata.normalize("NFKC", value).strip()
    if (
        not normalized
        or _has_control_character(normalized)
        or "%" in normalized
        or "\\" in normalized
    ):
        raise error

    if "://" in normalized:
        try:
            parsed = urlsplit(normalized)
            port = parsed.port
        except ValueError:
            raise error from None
        if (
            parsed.scheme.casefold() != "https"
            or parsed.hostname is None
            or parsed.hostname.casefold() != "github.com"
            or parsed.username is not None
            or parsed.password is not None
            or port is not None
            or parsed.query
            or parsed.fragment
            or not parsed.path.startswith("/")
        ):
            raise error
        identifier = parsed.path[1:]
        if identifier.endswith("/"):
            identifier = identifier[:-1]
    else:
        identifier = normalized

    if identifier.casefold().endswith(".git"):
        identifier = identifier[:-4]

    parts = identifier.split("/")
    if len(parts) != 2:
        raise error

    owner, repository = parts
    if (
        _GITHUB_OWNER_PATTERN.fullmatch(owner) is None
        or _GITHUB_REPOSITORY_PATTERN.fullmatch(repository) is None
        or repository in {".", ".."}
    ):
        raise error

    return f"{owner.casefold()}/{repository.casefold()}"


def github_clone_url(repository: str) -> str:
    """Build a credential-free HTTPS clone URL from a validated identity."""
    return f"https://github.com/{normalize_github_repository(repository)}.git"


def _argv_digest(argv: Sequence[str]) -> str:
    """Hash an argv vector without ambiguous separator encoding."""
    normalized = _normalize_command_argv(argv)
    digest = hashlib.sha256()
    for argument in normalized:
        encoded = argument.encode("utf-8")
        digest.update(len(encoded).to_bytes(8, "big"))
        digest.update(encoded)
    return f"sha256:{digest.hexdigest()}"


def _normalize_identity_id(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid user identity id.")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if _IDENTITY_ID_PATTERN.fullmatch(normalized) is None or ".." in normalized:
        raise ValueError("Invalid user identity id.")
    return normalized.casefold()


def _normalize_identity_name(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid user identity name.")
    normalized = unicodedata.normalize("NFKC", value)
    if _has_control_character(normalized):
        raise ValueError("Invalid user identity name.")
    normalized = " ".join(normalized.split())
    if not normalized or len(normalized) > 100:
        raise ValueError("Invalid user identity name.")
    return normalized


def _normalize_identity_email(value: str) -> str:
    if not isinstance(value, str):
        raise ValueError("Invalid user identity email.")
    normalized = unicodedata.normalize("NFKC", value).strip()
    if (
        len(normalized) > 254
        or _has_control_character(normalized)
        or _EMAIL_PATTERN.fullmatch(normalized) is None
    ):
        raise ValueError("Invalid user identity email.")
    local, domain = normalized.rsplit("@", 1)
    if local.startswith(".") or local.endswith(".") or ".." in local:
        raise ValueError("Invalid user identity email.")
    return f"{local}@{domain.casefold()}"


def _normalize_command_argv(argv: Sequence[str]) -> tuple[str, ...]:
    if isinstance(argv, (str, bytes)):
        raise TypeError(
            "Commands must be passed as an argv sequence, not a shell string."
        )
    normalized = tuple(argv)
    if not normalized or not normalized[0]:
        raise ValueError("Command argv must contain a non-empty executable.")
    if any(
        not isinstance(argument, str) or _has_control_character(argument)
        for argument in normalized
    ):
        raise ValueError("Command argv contains an invalid argument.")

    executable = PurePosixPath(normalized[0]).name.casefold()
    if executable in _FORBIDDEN_SHELLS:
        raise ValueError("Shell interpreters are not accepted by the command boundary.")
    return normalized


def _normalize_command_cwd(cwd: Optional[str]) -> Optional[str]:
    if cwd is None:
        return None
    if (
        not isinstance(cwd, str)
        or not cwd
        or "\x00" in cwd
        or _has_control_character(cwd)
    ):
        raise ValueError("Command working directory is invalid.")
    path = PurePosixPath(cwd)
    if not path.is_absolute() or ".." in path.parts:
        raise ValueError(
            "Command working directory must be an absolute normalized path."
        )
    return path.as_posix()


@dataclass(frozen=True, slots=True)
class CommandSpec:
    """Validated command invocation with no shell parsing surface."""

    argv: tuple[str, ...]
    cwd: Optional[str] = None
    background: bool = False
    check: bool = True

    def __post_init__(self) -> None:
        object.__setattr__(self, "argv", _normalize_command_argv(self.argv))
        object.__setattr__(self, "cwd", _normalize_command_cwd(self.cwd))

    @classmethod
    def create(
        cls,
        argv: Sequence[str],
        *,
        cwd: Optional[str] = None,
        background: bool = False,
        check: bool = True,
    ) -> CommandSpec:
        if isinstance(argv, (str, bytes)):
            raise TypeError(
                "Commands must be passed as an argv sequence, not a shell string."
            )
        return cls(
            argv=tuple(argv),
            cwd=cwd,
            background=background,
            check=check,
        )


class CredentialLeaseError(RuntimeError):
    """Safe application-facing failure for a credentialed operation."""


class WarmSyncError(RuntimeError):
    """Safe, typed failure raised before a warm sandbox can be offered."""


class RepositoryAccessError(PermissionError):
    """Non-enumerating repository authorization failure."""


class SnapshotBindingError(RuntimeError):
    """Safe failure when a trusted snapshot binding cannot be established."""


class SnapshotBindingCollisionError(SnapshotBindingError):
    """Raised when create-if-absent finds a conflicting snapshot binding."""


class SnapshotReconciliationRequiredError(SnapshotBindingError):
    """Raised when an ambiguous remote attestation is not yet observable."""


class SessionHandleCollisionError(RuntimeError):
    """Raised when an opaque session handle collides during registration."""


class MalformedSessionError(RuntimeError):
    """Raised after an unusable active-session record is cleaned up."""


class SessionTerminationError(RuntimeError):
    """Typed retryable failure after session termination does not complete."""


class SandboxCleanupError(RuntimeError):
    """Raised when cleanup ownership moves to the supervised quarantine."""


GitOperation = Literal["clone", "fetch", "push"]
RepositoryAction = Literal["session:start", "warm:prepare"]


@dataclass(frozen=True, slots=True, repr=False)
class EphemeralGitCredential:
    """Opaque one-operation credential lease; never contains a token.

    The infrastructure adapter resolves this handle inside the child execution
    boundary and supplies the credential through a preinstalled ``GIT_ASKPASS``
    helper. The broker expires the lease when its async context closes.
    """

    lease_id: UUID
    repository: str
    operation: GitOperation
    host: str
    argv_digest: str
    audience: str
    git_config_scope: Literal["provider-owned-clean"]
    egress_policy_digest: str

    def __post_init__(self) -> None:
        if type(self.lease_id) is not UUID:
            raise ValueError("Invalid credential lease identifier.")
        object.__setattr__(
            self,
            "repository",
            normalize_github_repository(self.repository),
        )
        if self.operation not in {"clone", "fetch", "push"}:
            raise ValueError("Invalid credential lease operation.")
        if self.host != "github.com":
            raise ValueError("Invalid credential lease host.")
        if (
            not isinstance(self.argv_digest, str)
            or _CONTENT_DIGEST_PATTERN.fullmatch(self.argv_digest) is None
        ):
            raise ValueError("Invalid credential lease argv digest.")
        if self.audience != github_clone_url(self.repository):
            raise ValueError("Invalid credential lease audience.")
        if self.git_config_scope != "provider-owned-clean":
            raise ValueError("Invalid credential Git configuration scope.")
        if self.egress_policy_digest != _GITHUB_EGRESS_POLICY_DIGEST:
            raise ValueError("Invalid credential egress policy.")

    def __repr__(self) -> str:
        return "<EphemeralGitCredential redacted>"


GitCredentialProvider = Callable[
    [str, GitOperation, str],
    AbstractAsyncContextManager[EphemeralGitCredential],
]


class SandboxState(Enum):
    """Sandbox lifecycle states."""

    CREATING = "creating"
    SYNCING = "syncing"
    READY = "ready"
    EXECUTING = "executing"
    SNAPSHOTTING = "snapshotting"
    TERMINATED = "terminated"


@dataclass(frozen=True, slots=True)
class UserIdentity:
    """User identity for commit attribution.

    Use when: configuring sandbox git identity so commits are
    attributed to the prompting user, not the app.
    """

    id: str
    name: str
    email: str

    def __post_init__(self) -> None:
        object.__setattr__(self, "id", _normalize_identity_id(self.id))
        object.__setattr__(self, "name", _normalize_identity_name(self.name))
        object.__setattr__(self, "email", _normalize_identity_email(self.email))


@dataclass(frozen=True, slots=True)
class RepositoryAccessReceipt:
    """Verified authorization decision metadata with no embedded credential."""

    receipt_id: UUID
    principal_id: str
    repository: str
    action: RepositoryAction
    expires_at: datetime

    def __post_init__(self) -> None:
        if type(self.receipt_id) is not UUID:
            raise ValueError("Invalid repository access receipt.")
        if self.action not in {"session:start", "warm:prepare"}:
            raise ValueError("Invalid repository access receipt.")
        if type(self.expires_at) is not datetime or self.expires_at.tzinfo is not None:
            raise ValueError("Invalid repository access receipt.")
        object.__setattr__(
            self, "principal_id", _normalize_identity_id(self.principal_id)
        )
        object.__setattr__(
            self,
            "repository",
            normalize_github_repository(self.repository),
        )


@dataclass(frozen=True, slots=True)
class SessionSnapshotRef:
    """Untrusted opaque locator; binding comes from the trusted provider."""

    snapshot_id: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.snapshot_id, str)
            or _SNAPSHOT_ID_PATTERN.fullmatch(self.snapshot_id) is None
        ):
            raise ValueError("Invalid session snapshot reference.")


@dataclass(frozen=True, slots=True)
class CreatedSnapshot:
    """Immutable provider result used for collision-safe attestation."""

    snapshot_id: str
    generation: int
    content_digest: str

    def __post_init__(self) -> None:
        if (
            not isinstance(self.snapshot_id, str)
            or _SNAPSHOT_ID_PATTERN.fullmatch(self.snapshot_id) is None
            or type(self.generation) is not int
            or self.generation < 1
            or not isinstance(self.content_digest, str)
            or _CONTENT_DIGEST_PATTERN.fullmatch(self.content_digest) is None
        ):
            raise ValueError("Invalid created snapshot identity.")


@dataclass(frozen=True, slots=True)
class ResolvedSnapshotBinding:
    """Authoritative snapshot metadata returned by the configured provider."""

    attestation_id: UUID
    snapshot_id: str
    generation: int
    content_digest: str
    repository: str
    principal_id: str

    def __post_init__(self) -> None:
        if type(self.attestation_id) is not UUID:
            raise ValueError("Invalid snapshot binding attestation.")
        if (
            not isinstance(self.snapshot_id, str)
            or _SNAPSHOT_ID_PATTERN.fullmatch(self.snapshot_id) is None
            or type(self.generation) is not int
            or self.generation < 1
            or not isinstance(self.content_digest, str)
            or _CONTENT_DIGEST_PATTERN.fullmatch(self.content_digest) is None
        ):
            raise ValueError("Invalid snapshot binding attestation.")
        object.__setattr__(
            self,
            "repository",
            normalize_github_repository(self.repository),
        )
        object.__setattr__(
            self, "principal_id", _normalize_identity_id(self.principal_id)
        )


class SnapshotBindingProvider(Protocol):
    """Trusted persistence boundary for snapshot ownership attestations."""

    async def resolve(
        self,
        snapshot_id: str,
        repository: str,
        principal_id: str,
    ) -> Optional[ResolvedSnapshotBinding]:
        """Authorize a snapshot/repository/principal tuple from trusted state."""
        ...

    async def attest_create_if_absent(
        self,
        operation_id: UUID,
        snapshot: CreatedSnapshot,
        repository: str,
        principal_id: str,
    ) -> ResolvedSnapshotBinding:
        """Atomically create a binding or reject a conflicting existing one."""
        ...

    async def resolve_attestation(
        self,
        operation_id: UUID,
    ) -> Optional[ResolvedSnapshotBinding]:
        """Resolve the authoritative result of an ambiguous create call."""
        ...


@dataclass(frozen=True, slots=True, repr=False)
class SessionHandle:
    """Opaque, collision-resistant handle for one registered session."""

    value: UUID

    def __post_init__(self) -> None:
        if type(self.value) is not UUID:
            raise ValueError("Invalid session handle.")

    def __repr__(self) -> str:
        return "<SessionHandle redacted>"


@dataclass(frozen=True, slots=True)
class SessionAllocation:
    """A usable session result containing its teardown handle and sandbox."""

    handle: SessionHandle
    sandbox: Sandbox


@dataclass(slots=True)
class _TeardownOperation:
    """Local state for one idempotent teardown operation."""

    operation_id: UUID
    finalization_complete: bool = False
    snapshot: Optional[CreatedSnapshot] = None
    snapshot_ambiguous: bool = False
    binding: Optional[ResolvedSnapshotBinding] = None
    attestation_ambiguous: bool = False


@dataclass(frozen=True, slots=True)
class SandboxConfig:
    """Configuration for sandbox creation.

    Use when: defining resource limits and timeouts for a new sandbox
    to prevent cost runaway and resource exhaustion.
    """

    repo_url: str
    base_image: str
    memory_mb: int = 4096
    cpu_cores: int = 2
    disk_gb: int = 10
    timeout_hours: int = 4
    max_processes: int = 256
    max_command_output_bytes: int = 16 * 1024 * 1024
    network_mode: Literal["none", "brokered"] = "none"
    max_network_egress_bytes: int = 0
    egress_policy_digest: Optional[str] = None

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "repo_url",
            normalize_github_repository(self.repo_url),
        )
        if (
            not isinstance(self.base_image, str)
            or _PINNED_IMAGE_PATTERN.fullmatch(self.base_image) is None
        ):
            raise ValueError("Base image must be pinned by a SHA-256 digest.")

        resource_bounds = {
            "memory_mb": (128, 262_144),
            "cpu_cores": (1, 128),
            "disk_gb": (1, 4_096),
            "timeout_hours": (1, 24),
            "max_processes": (1, 4_096),
            "max_command_output_bytes": (1_024, 256 * 1024 * 1024),
            "max_network_egress_bytes": (0, 1024 * 1024 * 1024),
        }
        for field_name, (minimum, maximum) in resource_bounds.items():
            value = getattr(self, field_name)
            if type(value) is not int or not minimum <= value <= maximum:
                raise ValueError(f"Sandbox {field_name} is outside the allowed bounds.")
        if self.network_mode not in {"none", "brokered"}:
            raise ValueError("Sandbox network mode is invalid.")
        if self.network_mode == "none":
            if (
                self.max_network_egress_bytes != 0
                or self.egress_policy_digest is not None
            ):
                raise ValueError("Deny-all networking cannot grant egress.")
        elif (
            self.max_network_egress_bytes == 0
            or not isinstance(self.egress_policy_digest, str)
            or _CONTENT_DIGEST_PATTERN.fullmatch(self.egress_policy_digest) is None
        ):
            raise ValueError("Brokered networking requires a finite attested policy.")

    def policy_digest(self) -> str:
        """Digest the exact finite policy a provider must attest."""
        return _argv_digest(
            (
                self.repo_url,
                self.base_image,
                str(self.memory_mb),
                str(self.cpu_cores),
                str(self.disk_gb),
                str(self.timeout_hours),
                str(self.max_processes),
                str(self.max_command_output_bytes),
                self.network_mode,
                str(self.max_network_egress_bytes),
                self.egress_policy_digest or "none",
            )
        )


@dataclass(frozen=True, slots=True)
class ResourcePolicyAttestation:
    """Provider assertion that the exact requested finite policy is enforced."""

    attestation_id: UUID
    config_digest: str

    def __post_init__(self) -> None:
        if (
            type(self.attestation_id) is not UUID
            or not isinstance(self.config_digest, str)
            or _CONTENT_DIGEST_PATTERN.fullmatch(self.config_digest) is None
        ):
            raise ValueError("Invalid resource policy attestation.")


@dataclass
class Sandbox:
    """Represents a sandboxed execution environment.

    Use when: interacting with a running sandbox to execute commands,
    read/write files, or take snapshots for session continuity.
    """

    id: str
    config: SandboxConfig
    state: SandboxState
    created_at: datetime
    snapshot_id: Optional[str] = None
    current_user: Optional[UserIdentity] = None
    restored_snapshot_attestation_id: Optional[UUID] = None
    restored_snapshot_generation: Optional[int] = None
    restored_snapshot_content_digest: Optional[str] = None
    resource_policy_attestation: Optional[ResourcePolicyAttestation] = None

    # Event handlers
    on_state_change: Optional[Callable[[SandboxState], None]] = None

    def has_valid_resource_attestation(self) -> bool:
        """Return whether the provider attested the exact immutable config."""
        return (
            type(self.resource_policy_attestation) is ResourcePolicyAttestation
            and self.resource_policy_attestation.config_digest
            == self.config.policy_digest()
        )

    async def execute_command(
        self,
        argv: Sequence[str],
        *,
        cwd: Optional[str] = None,
        background: bool = False,
        check: bool = True,
        credential: Optional[EphemeralGitCredential] = None,
    ) -> dict[str, Any]:
        """Validate and execute one argv-based command in the sandbox.

        Use when: running shell commands (git, build tools, tests)
        inside the isolated environment.

        ``credential`` is an opaque one-operation lease. Infrastructure
        adapters resolve it only inside the child process boundary, inject the
        secret through a preinstalled ``GIT_ASKPASS`` helper, disable terminal
        prompting, use a provider-owned clean Git config/repository boundary,
        validate the helper's exact audience, enforce destination/address
        egress, redact command metadata, and revoke the lease on exit. They
        must never trust workspace Git config or serialize a token into argv,
        environment logs, URLs, snapshots, or result records.

        Returns:
            dict with keys "stdout", "stderr", "exit_code".
        """
        spec = CommandSpec.create(
            argv,
            cwd=cwd,
            background=background,
            check=check,
        )
        if credential is not None:
            if type(credential) is not EphemeralGitCredential:
                raise CredentialLeaseError("Command received an invalid lease type.")
            if credential.repository != self.config.repo_url:
                raise CredentialLeaseError("Credential scope does not match sandbox.")
            expected_operation = (
                next(
                    (
                        argument
                        for argument in spec.argv[1:]
                        if argument in {"clone", "fetch", "push"}
                    ),
                    None,
                )
                if spec.argv[0] == "git"
                else None
            )
            if credential.operation != expected_operation:
                raise CredentialLeaseError(
                    "Credential operation does not match the command."
                )
            if credential.host != "github.com":
                raise CredentialLeaseError("Credential host is not permitted.")
            if credential.argv_digest != _argv_digest(spec.argv):
                raise CredentialLeaseError("Credential argv scope does not match.")
            if credential.audience != github_clone_url(self.config.repo_url):
                raise CredentialLeaseError("Credential audience does not match.")
            url_arguments = tuple(
                argument
                for argument in spec.argv
                if "://" in argument or argument.startswith("file:")
            )
            if url_arguments != (credential.audience,):
                raise CredentialLeaseError("Credential command audience is invalid.")
            if credential.git_config_scope != "provider-owned-clean":
                raise CredentialLeaseError("Credential Git boundary is invalid.")
            if credential.egress_policy_digest != _GITHUB_EGRESS_POLICY_DIGEST:
                raise CredentialLeaseError("Credential egress policy is invalid.")
        return await self._execute_command(spec, credential=credential)

    async def _execute_command(
        self,
        spec: CommandSpec,
        *,
        credential: Optional[EphemeralGitCredential] = None,
    ) -> dict[str, Any]:
        """Execute a validated command (infrastructure-specific)."""
        pass

    async def read_file(self, path: str) -> str:
        """Read a file from the sandbox filesystem.

        Use only after the manager has completed repository synchronization
        and offered the sandbox as ready.
        """
        pass

    async def write_file(self, path: str, content: str) -> None:
        """Write a file to the sandbox filesystem.

        Use only after the manager has completed repository synchronization
        and offered the sandbox as ready.
        """
        pass

    async def prepare_snapshot_finalization(self) -> None:
        """Run the mandatory pre-snapshot finalization gate."""
        await self._prepare_snapshot_finalization()

    async def create_snapshot(self, operation_id: UUID) -> CreatedSnapshot:
        """Create once under a provider-idempotent operation identifier."""
        if type(operation_id) is not UUID:
            raise SnapshotBindingError("Snapshot operation is invalid.")
        self.state = SandboxState.SNAPSHOTTING
        snapshot = await self._create_snapshot(operation_id)
        if type(snapshot) is not CreatedSnapshot:
            raise SnapshotBindingError("Snapshot creation returned invalid identity.")
        self.snapshot_id = snapshot.snapshot_id
        self.state = SandboxState.READY
        return snapshot

    async def resolve_snapshot_creation(
        self,
        operation_id: UUID,
    ) -> Optional[CreatedSnapshot]:
        """Resolve an ambiguous provider snapshot operation without replay."""
        if type(operation_id) is not UUID:
            raise SnapshotBindingError("Snapshot operation is invalid.")
        snapshot = await self._resolve_created_snapshot(operation_id)
        if snapshot is not None and type(snapshot) is not CreatedSnapshot:
            raise SnapshotBindingError("Snapshot reconciliation returned invalid data.")
        if snapshot is not None:
            self.snapshot_id = snapshot.snapshot_id
            self.state = SandboxState.READY
        return snapshot

    async def _prepare_snapshot_finalization(self) -> None:
        """Reap processes and prove quiescence and credential absence."""
        raise NotImplementedError("A snapshot-finalization adapter is required.")

    async def _create_snapshot(self, operation_id: UUID) -> CreatedSnapshot:
        """Create-if-absent snapshot under ``operation_id`` (provider-specific)."""
        pass

    async def _resolve_created_snapshot(
        self,
        operation_id: UUID,
    ) -> Optional[CreatedSnapshot]:
        """Resolve one provider snapshot operation (infrastructure-specific)."""
        pass

    async def restore(self, snapshot_id: str) -> None:
        """Restore sandbox to a previous snapshot."""
        pass

    async def terminate(self) -> None:
        """Terminate the sandbox."""
        self.state = SandboxState.TERMINATED


@dataclass
class RepositoryImage:
    """Pre-built image for a repository.

    Use when: checking whether a cached environment image exists
    and whether it is recent enough to use.
    """

    repo_url: str
    image_id: str
    commit_sha: str
    built_at: datetime

    def __post_init__(self) -> None:
        self.repo_url = normalize_github_repository(self.repo_url)

    def is_stale(self, max_age: timedelta = timedelta(minutes=30)) -> bool:
        """Check if image is older than max age."""
        return datetime.utcnow() - self.built_at > max_age


class ImageBuilder:
    """Builds and manages repository images.

    Use when: setting up the periodic image build loop that
    pre-bakes development environments for fast sandbox spin-up.
    """

    def __init__(
        self,
        github_credential_provider: GitCredentialProvider,
    ) -> None:
        self.credential_provider = github_credential_provider
        self.images: dict[str, RepositoryImage] = {}

    @asynccontextmanager
    async def credential_lease(
        self,
        repo_url: str,
        operation: GitOperation,
        argv: Sequence[str],
    ) -> AsyncIterator[EphemeralGitCredential]:
        """Yield one validated repository- and operation-scoped lease.

        Provider failures are collapsed to a stable error because exception
        text can contain credential or transport details. The broker owns the
        underlying short-lived secret and revokes it when this context exits.
        """
        repository = normalize_github_repository(repo_url)
        argv_digest = _argv_digest(argv)
        audience = github_clone_url(repository)
        url_arguments = tuple(
            argument
            for argument in argv
            if "://" in argument or argument.startswith("file:")
        )
        if url_arguments != (audience,):
            raise CredentialLeaseError("Credential command audience is invalid.")
        try:
            async with self.credential_provider(
                repository,
                operation,
                argv_digest,
            ) as credential:
                if type(credential) is not EphemeralGitCredential:
                    raise CredentialLeaseError(
                        "Credential provider returned an invalid lease type."
                    )
                if credential.repository != repository:
                    raise CredentialLeaseError(
                        "Credential scope does not match repository."
                    )
                if credential.operation != operation:
                    raise CredentialLeaseError(
                        "Credential operation does not match request."
                    )
                if credential.host != "github.com":
                    raise CredentialLeaseError(
                        "Credential host does not match request."
                    )
                if credential.argv_digest != argv_digest:
                    raise CredentialLeaseError("Credential argv scope does not match.")
                if credential.audience != audience:
                    raise CredentialLeaseError("Credential audience does not match.")
                if credential.git_config_scope != "provider-owned-clean":
                    raise CredentialLeaseError("Credential Git boundary is invalid.")
                if credential.egress_policy_digest != _GITHUB_EGRESS_POLICY_DIGEST:
                    raise CredentialLeaseError("Credential egress policy is invalid.")
                yield credential
        except CredentialLeaseError:
            raise
        except Exception:
            raise CredentialLeaseError("Credentialed Git operation failed.") from None

    async def build_image(self, repo_url: str) -> RepositoryImage:
        """Build a new image for a repository.

        Use when: the current image is stale or no image exists yet.
        Runs clone, dependency install, build, and terminating verification.
        """
        repository = normalize_github_repository(repo_url)
        print(f"Building image for {repository}...")

        # The broker yields an opaque, scoped, one-operation handle. The
        # manager never receives or stores the underlying installation token.
        clone_spec = CommandSpec.create(
            (
                "git",
                "-c",
                "credential.helper=",
                "-c",
                "credential.useHttpPath=true",
                "-c",
                "http.followRedirects=false",
                "clone",
                "--no-recurse-submodules",
                "--",
                github_clone_url(repository),
                "/workspace",
            )
        )
        async with self.credential_lease(
            repository,
            "clone",
            clone_spec.argv,
        ) as credential:
            await self._execute_build_step(clone_spec, credential=credential)

        # The clone lease has expired before any repository-controlled code
        # runs. A provider adapter must prove the build child has no ambient
        # authority, direct egress, broker socket, or inherited secret.
        await self._verify_untrusted_build_boundary()

        build_steps = (
            CommandSpec.create(
                ("npm", "ci", "--ignore-scripts"),
                cwd="/workspace",
            ),
            CommandSpec.create(("npm", "run", "build"), cwd="/workspace"),
            CommandSpec.create(
                ("npm", "test", "--", "--run"),
                cwd="/workspace",
            ),
        )

        for step in build_steps:
            await self._execute_build_step(step)

        # Get current commit
        commit_sha: str = await self._get_commit_sha()

        # Finalization is forbidden while any repository process, writable
        # broker channel, or credential helper remains in the build boundary.
        await self._assert_quiescent()

        # Create and store image
        image = RepositoryImage(
            repo_url=repository,
            image_id=await self._finalize_image(),
            commit_sha=commit_sha,
            built_at=datetime.utcnow(),
        )

        self.images[repository] = image
        return image

    def get_latest_image(self, repo_url: str) -> Optional[RepositoryImage]:
        """Get the most recent image for a repository."""
        return self.images.get(normalize_github_repository(repo_url))

    async def _execute_build_step(
        self,
        spec: CommandSpec,
        *,
        credential: Optional[EphemeralGitCredential] = None,
    ) -> None:
        """Execute a validated build step (infrastructure-specific).

        A credential-aware adapter resolves the opaque handle at execution,
        passes the secret only to a preinstalled ``GIT_ASKPASS`` helper, and
        revokes it when the provider context exits. It must run credentialed
        Git in a provider-owned clean repository/config boundary, ignore all
        workspace/system/global Git config (including includes, proxies, and
        ``url.*.insteadOf``), validate the exact audience in ``GIT_ASKPASS``,
        and enforce the attested destination/address egress policy. Command
        logs contain only ``spec`` and never the helper's secret environment.
        """
        pass

    async def _verify_untrusted_build_boundary(self) -> None:
        """Prove repository code has no ambient authority before execution."""
        raise NotImplementedError("A build-isolation adapter is required.")

    async def _assert_quiescent(self) -> None:
        """Prove all child processes and credential helpers are gone."""
        raise NotImplementedError("A quiescence verifier is required.")

    async def _get_commit_sha(self) -> str:
        """Get current HEAD commit SHA."""
        pass

    async def _finalize_image(self) -> str:
        """Finalize and store the image, return image ID."""
        pass


@dataclass
class WarmSandbox:
    """A pre-warmed sandbox ready for use.

    Use when: tracking warm pool inventory and claiming a sandbox
    for an incoming user session.
    """

    sandbox: Sandbox
    repo_url: str
    created_at: datetime
    image_version: str
    is_claimed: bool = False
    sync_complete: bool = False

    def __post_init__(self) -> None:
        self.repo_url = normalize_github_repository(self.repo_url)


class WarmPoolManager:
    """Manages pools of pre-warmed sandboxes.

    Use when: reducing cold start latency by maintaining ready-to-use
    sandboxes that are pre-synced to the latest code.
    """

    def __init__(
        self,
        image_builder: ImageBuilder,
        target_pool_size: int = 3,
        max_age: timedelta = timedelta(minutes=25),
        sync_timeout: timedelta = timedelta(seconds=30),
    ) -> None:
        if type(target_pool_size) is not int or not 0 <= target_pool_size <= 64:
            raise ValueError("Warm pool target size is outside the allowed bounds.")
        if type(max_age) is not timedelta or not timedelta(
            seconds=1
        ) <= max_age <= timedelta(hours=24):
            raise ValueError("Warm pool maximum age is outside the allowed bounds.")
        if type(sync_timeout) is not timedelta or not timedelta(
            milliseconds=1
        ) <= sync_timeout <= timedelta(minutes=10):
            raise ValueError(
                "Warm synchronization timeout is outside the allowed bounds."
            )
        self.image_builder = image_builder
        self.target_size = target_pool_size
        self.max_age = max_age
        self.sync_timeout = sync_timeout
        self.pools: dict[str, list[WarmSandbox]] = {}
        self._pool_locks: dict[str, asyncio.Lock] = {}
        self._cleanup_quarantine: list[Sandbox] = []
        self._cleanup_in_flight: list[Sandbox] = []
        self._cleanup_registry_lock = Lock()
        self._cleanup_retry_lock = asyncio.Lock()

    @property
    def quarantined_cleanup_count(self) -> int:
        """Number of sandboxes still owned by the cleanup supervisor."""
        with self._cleanup_registry_lock:
            return len(self._cleanup_quarantine)

    def _mark_cleanup_in_flight(self, sandbox: Sandbox) -> None:
        """Retain ownership and exclude an active attempt from retries."""
        with self._cleanup_registry_lock:
            if all(candidate is not sandbox for candidate in self._cleanup_quarantine):
                self._cleanup_quarantine.append(sandbox)
            if all(candidate is not sandbox for candidate in self._cleanup_in_flight):
                self._cleanup_in_flight.append(sandbox)

    def _mark_cleanup_retryable(self, sandbox: Sandbox) -> None:
        """Expose one failed or ambiguous attempt to supervised retry."""
        with self._cleanup_registry_lock:
            self._cleanup_in_flight = [
                candidate
                for candidate in self._cleanup_in_flight
                if candidate is not sandbox
            ]

    def _release_cleanup(self, sandbox: Sandbox) -> None:
        """Release ownership only after provider termination returns."""
        with self._cleanup_registry_lock:
            self._cleanup_quarantine = [
                candidate
                for candidate in self._cleanup_quarantine
                if candidate is not sandbox
            ]
            self._cleanup_in_flight = [
                candidate
                for candidate in self._cleanup_in_flight
                if candidate is not sandbox
            ]

    def _cleanup_candidates(self) -> tuple[Sandbox, ...]:
        with self._cleanup_registry_lock:
            return tuple(
                sandbox
                for sandbox in self._cleanup_quarantine
                if all(
                    candidate is not sandbox for candidate in self._cleanup_in_flight
                )
            )

    async def _terminate_with_cleanup_ownership(self, sandbox: Sandbox) -> None:
        """Terminate while retaining the sandbox across every exceptional exit."""
        self._mark_cleanup_in_flight(sandbox)
        try:
            async with self._cleanup_retry_lock:
                await sandbox.terminate()
                self._release_cleanup(sandbox)
        except BaseException:
            self._mark_cleanup_retryable(sandbox)
            raise

    async def retry_quarantined_cleanup(self) -> int:
        """Retry every owned cleanup once; return the remaining count."""
        async with self._cleanup_retry_lock:
            for sandbox in self._cleanup_candidates():
                self._mark_cleanup_in_flight(sandbox)
                try:
                    await sandbox.terminate()
                except asyncio.CancelledError:
                    self._mark_cleanup_retryable(sandbox)
                    raise
                except Exception:
                    self._mark_cleanup_retryable(sandbox)
                    continue
                except BaseException:
                    self._mark_cleanup_retryable(sandbox)
                    raise
                self._release_cleanup(sandbox)
            return self.quarantined_cleanup_count

    async def get_warm_sandbox(self, repo_url: str) -> Optional[WarmSandbox]:
        """Get a pre-warmed sandbox if available.

        Use when: a user submits a prompt and needs a sandbox immediately.
        Returns None if no valid warm sandbox is available.
        """
        repository = normalize_github_repository(repo_url)
        if repository not in self.pools:
            return None

        for warm in self.pools[repository]:
            if not warm.is_claimed and self._is_valid(warm):
                warm.is_claimed = True
                return warm

        return None

    def _is_valid(self, warm: WarmSandbox) -> bool:
        """Check if a warm sandbox is still valid."""
        if not warm.sync_complete or not warm.sandbox.has_valid_resource_attestation():
            return False

        age: timedelta = datetime.utcnow() - warm.created_at
        if age > self.max_age:
            return False

        # Check if image is still current
        current = self.image_builder.get_latest_image(warm.repo_url)
        if not current or current.image_id != warm.image_version:
            return False

        return True

    async def maintain_pool(self, repo_url: str) -> None:
        """Ensure pool has target number of warm sandboxes.

        Use when: called periodically or after an image rebuild to
        keep the warm pool populated.
        """
        repository = normalize_github_repository(repo_url)
        lock = self._pool_locks.setdefault(repository, asyncio.Lock())
        async with lock:
            existing = self.pools.setdefault(repository, [])
            valid: list[WarmSandbox] = []
            stale_unclaimed: list[WarmSandbox] = []
            for warm in existing:
                if self._is_valid(warm):
                    valid.append(warm)
                elif not warm.is_claimed:
                    stale_unclaimed.append(warm)
                # Claimed sandboxes have moved to session ownership. Remove
                # them from pool accounting, but never terminate them here.

            self.pools[repository] = valid
            cleanup_failed = False
            for stale in stale_unclaimed:
                try:
                    await self._terminate_with_cleanup_ownership(stale.sandbox)
                except asyncio.CancelledError:
                    raise
                except Exception:
                    cleanup_failed = True
                except BaseException:
                    raise

            if cleanup_failed:
                raise SandboxCleanupError("Sandbox cleanup requires supervised retry.")

            available = len([warm for warm in valid if not warm.is_claimed])
            needed = self.target_size - available
            for _ in range(max(0, needed)):
                # _create_warm_sandbox returns only after bounded sync. A
                # failure propagates and the unsynced sandbox is never added.
                warm = await self._create_warm_sandbox(repository)
                self.pools[repository].append(warm)

    async def _create_warm_sandbox(self, repo_url: str) -> WarmSandbox:
        """Create a new warm sandbox."""
        repository = normalize_github_repository(repo_url)
        image: Optional[RepositoryImage] = self.image_builder.get_latest_image(
            repository
        )
        if not image:
            raise ValueError(f"No image available for {repo_url}")

        # Create sandbox from image
        sandbox: Sandbox = await self._create_sandbox_from_image(image)

        warm = WarmSandbox(
            sandbox=sandbox,
            repo_url=repository,
            created_at=datetime.utcnow(),
            image_version=image.image_id,
            sync_complete=False,
        )

        try:
            await self._sync_to_latest(warm)
        except BaseException as sync_error:
            try:
                await self._terminate_with_cleanup_ownership(sandbox)
            except asyncio.CancelledError:
                raise
            except Exception:
                if not isinstance(sync_error, Exception):
                    raise sync_error
                raise SandboxCleanupError(
                    "Sandbox cleanup requires supervised retry."
                ) from None
            except BaseException:
                raise
            raise
        return warm

    async def _sync_to_latest(self, warm: WarmSandbox) -> None:
        """Synchronize before publication or raise a bounded typed failure."""
        fetch_argv = (
            "git",
            "-c",
            "credential.helper=",
            "-c",
            "credential.useHttpPath=true",
            "-c",
            "http.followRedirects=false",
            "fetch",
            "--no-tags",
            "--no-recurse-submodules",
            "--",
            github_clone_url(warm.repo_url),
            "+refs/heads/main:refs/remotes/origin/main",
        )
        try:
            async with asyncio.timeout(self.sync_timeout.total_seconds()):
                # A clone lease has already expired. Private fetch requires a
                # new repository-, host-, operation-, and argv-scoped lease.
                # The adapter must combine the canonical URL with the lease's
                # provider-owned clean Git boundary; a URL alone is unsafe.
                async with self.image_builder.credential_lease(
                    warm.repo_url,
                    "fetch",
                    fetch_argv,
                ) as credential:
                    await warm.sandbox.execute_command(
                        fetch_argv,
                        cwd="/workspace",
                        credential=credential,
                    )
                await warm.sandbox.execute_command(
                    ("git", "reset", "--hard", "origin/main", "--"),
                    cwd="/workspace",
                )
        except TimeoutError:
            raise WarmSyncError("Warm sandbox synchronization timed out.") from None
        except Exception:
            raise WarmSyncError("Warm sandbox synchronization failed.") from None
        warm.sync_complete = True

    async def _create_sandbox_from_image(self, image: RepositoryImage) -> Sandbox:
        """Create a sandbox from an image (infrastructure-specific)."""
        pass


class SandboxManager:
    """Main manager for sandbox lifecycle.

    Use when: orchestrating the full sandbox lifecycle including
    image building, warm pools, and session management. This is the
    top-level entry point that composes ImageBuilder and WarmPoolManager.
    """

    def __init__(
        self,
        repositories: list[str],
        github_credential_provider: GitCredentialProvider,
        build_interval: timedelta = timedelta(minutes=30),
        snapshot_binding_provider: Optional[SnapshotBindingProvider] = None,
    ) -> None:
        if type(build_interval) is not timedelta or not timedelta(
            seconds=1
        ) <= build_interval <= timedelta(hours=24):
            raise ValueError("Build interval is outside the allowed bounds.")
        self.repositories = list(
            dict.fromkeys(normalize_github_repository(repo) for repo in repositories)
        )
        self._repository_set = frozenset(self.repositories)
        self.image_builder = ImageBuilder(github_credential_provider)
        self.warm_pool = WarmPoolManager(self.image_builder)
        self.build_interval = build_interval
        self.snapshot_binding_provider = snapshot_binding_provider
        self.active_sessions: dict[SessionHandle, Sandbox] = {}
        # Retain authoritative teardown results so a retry after an uncertain
        # response never creates or attests another snapshot. A production
        # adapter must persist these with a bounded idempotency retention.
        self._teardown_bindings: dict[SessionHandle, ResolvedSnapshotBinding] = {}
        self._teardown_operations: dict[SessionHandle, _TeardownOperation] = {}
        self._teardown_locks: dict[SessionHandle, asyncio.Lock] = {}

    async def start_build_loop(self) -> None:
        """Start the background image build loop.

        Use when: initializing the system. Runs indefinitely, rebuilding
        images every build_interval to keep environments fresh.
        """
        while True:
            for repo in self.repositories:
                try:
                    await self.image_builder.build_image(repo)
                    await self.warm_pool.maintain_pool(repo)
                except Exception as error:
                    # Do not reflect broker/provider exception text into logs;
                    # it may contain credential or transport details.
                    print(f"Failed to build {repo} ({type(error).__name__})")

            await asyncio.sleep(self.build_interval.total_seconds())

    async def start_session(
        self,
        repo_url: str,
        user: UserIdentity,
        *,
        authorization: RepositoryAccessReceipt,
        snapshot: Optional[SessionSnapshotRef] = None,
    ) -> SessionAllocation:
        """Start a new session for a user.

        Use when: a user submits a prompt. Tries warm pool first,
        then snapshot restore, then cold start as fallback.
        """
        repository = normalize_github_repository(repo_url)
        self._require_repository_access(
            repository,
            user,
            authorization,
            action="session:start",
        )
        resolved_snapshot: Optional[ResolvedSnapshotBinding] = None
        if snapshot is not None:
            # The caller supplies only a locator. Repository and actor binding
            # come from the configured authoritative provider.
            resolved_snapshot = await self._resolve_snapshot_binding(
                snapshot,
                repository,
                user,
            )
            sandbox = await self._restore_from_snapshot(resolved_snapshot)
        else:
            warm = await self.warm_pool.get_warm_sandbox(repository)
            sandbox = warm.sandbox if warm else await self._cold_start(repository)

        restored_identity_matches = resolved_snapshot is None or (
            sandbox.restored_snapshot_attestation_id == resolved_snapshot.attestation_id
            and sandbox.restored_snapshot_generation == resolved_snapshot.generation
            and sandbox.restored_snapshot_content_digest
            == resolved_snapshot.content_digest
        )
        if (
            sandbox.config.repo_url != repository
            or not sandbox.has_valid_resource_attestation()
            or not restored_identity_matches
        ):
            await self._terminate_acquired_or_quarantine(sandbox)
            raise RepositoryAccessError("Repository access denied.")

        # Do not leak an acquired sandbox when identity configuration fails.
        try:
            await self._configure_for_user(sandbox, user)
        except BaseException:
            await self._terminate_acquired_or_quarantine(sandbox)
            raise

        # Registration performs its collision check and insert synchronously,
        # with no await point between them. A collision never overwrites the
        # existing session or leaks the newly acquired sandbox.
        try:
            handle = self._register_session(sandbox)
        except BaseException:
            await self._terminate_acquired_or_quarantine(sandbox)
            raise

        return SessionAllocation(handle=handle, sandbox=sandbox)

    @property
    def quarantined_cleanup_count(self) -> int:
        """Number of acquired sandboxes awaiting supervised cleanup."""
        return self.warm_pool.quarantined_cleanup_count

    async def retry_quarantined_cleanup(self) -> int:
        """Retry every quarantined cleanup once."""
        return await self.warm_pool.retry_quarantined_cleanup()

    async def _terminate_acquired_or_quarantine(self, sandbox: Sandbox) -> None:
        """Terminate an unregistered sandbox or retain cleanup ownership."""
        try:
            await self.warm_pool._terminate_with_cleanup_ownership(sandbox)
        except asyncio.CancelledError:
            raise
        except Exception:
            raise SandboxCleanupError(
                "Sandbox cleanup requires supervised retry."
            ) from None
        except BaseException:
            raise

    async def on_user_typing(
        self,
        user: UserIdentity,
        repo_url: str,
        *,
        authorization: RepositoryAccessReceipt,
    ) -> None:
        """Called when user starts typing a prompt.

        Use when: implementing predictive warm-up. Starts preparing a
        sandbox so it is ready by the time the user submits.
        """
        repository = normalize_github_repository(repo_url)
        self._require_repository_access(
            repository,
            user,
            authorization,
            action="warm:prepare",
        )
        # The caller may schedule this method in a supervised task, but this
        # method itself owns and awaits pool maintenance so failures are not
        # dropped. Pool maintenance does not claim an available sandbox.
        await self.warm_pool.maintain_pool(repository)

    async def end_session(
        self,
        handle: SessionHandle,
    ) -> Optional[SessionSnapshotRef]:
        """End a session and return an opaque, authoritatively bound locator.

        Use when: a session completes. Snapshot and attestation effects use
        one stable operation identifier. Ambiguous or cancelled effects retain
        the active session for supervised reconciliation before termination.
        """
        if type(handle) is not SessionHandle:
            return None
        lock = self._teardown_locks.setdefault(handle, asyncio.Lock())
        try:
            async with lock:
                return await self._end_session_locked(handle)
        finally:
            if handle not in self.active_sessions:
                self._teardown_locks.pop(handle, None)

    async def _end_session_locked(
        self,
        handle: SessionHandle,
    ) -> Optional[SessionSnapshotRef]:
        """Execute one serialized teardown with explicit reconciliation."""
        binding = self._teardown_bindings.get(handle)
        sandbox = self.active_sessions.get(handle)
        if sandbox is None:
            return (
                SessionSnapshotRef(snapshot_id=binding.snapshot_id)
                if binding is not None
                else None
            )

        if (
            not isinstance(sandbox, Sandbox)
            or type(sandbox.config) is not SandboxConfig
            or type(sandbox.current_user) is not UserIdentity
        ):
            await self._cleanup_malformed_session(handle, sandbox)

        if binding is None:
            operation = self._teardown_operations.get(handle)
            if operation is None:
                operation = _TeardownOperation(operation_id=uuid4())
                self._teardown_operations[handle] = operation
            try:
                if not operation.finalization_complete:
                    await sandbox.prepare_snapshot_finalization()
                    operation.finalization_complete = True
                if operation.snapshot is None:
                    if operation.snapshot_ambiguous:
                        operation.snapshot = await self._resolve_ambiguous_snapshot(
                            sandbox,
                            operation.operation_id,
                        )
                    else:
                        try:
                            operation.snapshot = await sandbox.create_snapshot(
                                operation.operation_id
                            )
                        except asyncio.CancelledError:
                            operation.snapshot_ambiguous = True
                            resolved = await self._try_resolve_snapshot(
                                sandbox,
                                operation.operation_id,
                            )
                            if resolved is not None:
                                operation.snapshot = resolved
                            raise
                        except Exception:
                            operation.snapshot_ambiguous = True
                            operation.snapshot = await self._resolve_ambiguous_snapshot(
                                sandbox,
                                operation.operation_id,
                            )
                binding = await self._attest_snapshot_binding(
                    operation,
                    sandbox.config.repo_url,
                    sandbox.current_user.id,
                )
            except SnapshotReconciliationRequiredError:
                # Keep the sandbox and stable operation/snapshot identity. A
                # retry resolves the same remote effect and never resnapshots.
                raise
            except BaseException:
                # Finalization, creation, binding, and cancellation failures
                # retain the active sandbox and stable operation for a
                # supervised retry. Cleanup occurs only after a binding exists.
                raise

            # Persist the authoritative result before termination. If
            # termination fails, the next call skips snapshot and attestation.
            self._teardown_bindings[handle] = binding
            self._teardown_operations.pop(handle, None)

        try:
            await sandbox.terminate()
        except asyncio.CancelledError:
            raise
        except Exception:
            raise SessionTerminationError("Session termination failed.") from None

        self.active_sessions.pop(handle, None)
        return SessionSnapshotRef(snapshot_id=binding.snapshot_id)

    async def _try_resolve_snapshot(
        self,
        sandbox: Sandbox,
        operation_id: UUID,
    ) -> Optional[CreatedSnapshot]:
        """Best-effort resolution used while preserving cancellation."""
        try:
            return await sandbox.resolve_snapshot_creation(operation_id)
        except Exception:
            return None

    async def _resolve_ambiguous_snapshot(
        self,
        sandbox: Sandbox,
        operation_id: UUID,
    ) -> CreatedSnapshot:
        """Resolve a possibly committed snapshot without replaying creation."""
        snapshot = await self._try_resolve_snapshot(sandbox, operation_id)
        if snapshot is None:
            raise SnapshotReconciliationRequiredError(
                "Snapshot creation requires reconciliation."
            )
        return snapshot

    async def _cleanup_malformed_session(
        self,
        handle: SessionHandle,
        sandbox: object,
    ) -> None:
        """Remove an invalid record, terminating its sandbox when possible."""
        if isinstance(sandbox, Sandbox):
            try:
                await sandbox.terminate()
            except asyncio.CancelledError:
                raise
            except Exception:
                raise SessionTerminationError("Session termination failed.") from None
        self.active_sessions.pop(handle, None)
        self._teardown_operations.pop(handle, None)
        raise MalformedSessionError("Session state is invalid.")

    def _register_session(self, sandbox: Sandbox) -> SessionHandle:
        """Atomically register one random handle or reject its collision."""
        handle = SessionHandle(uuid4())
        if (
            handle in self.active_sessions
            or handle in self._teardown_bindings
            or handle in self._teardown_operations
        ):
            raise SessionHandleCollisionError("Session handle collision.")
        self.active_sessions[handle] = sandbox
        return handle

    def _require_repository_access(
        self,
        repository: str,
        user: UserIdentity,
        authorization: RepositoryAccessReceipt,
        *,
        action: RepositoryAction,
    ) -> None:
        """Validate a verified receipt without revealing repository existence."""
        allowed = (
            repository in self._repository_set
            and type(authorization) is RepositoryAccessReceipt
            and authorization.repository == repository
            and authorization.principal_id == user.id
            and authorization.action == action
            and authorization.expires_at > datetime.utcnow()
        )
        if not allowed:
            raise RepositoryAccessError("Repository access denied.")

    async def _configure_for_user(self, sandbox: Sandbox, user: UserIdentity) -> None:
        """Configure sandbox for a specific user."""
        sandbox.current_user = user

        # Set git identity
        await sandbox.execute_command(
            ("git", "config", "--local", "--", "user.name", user.name),
            cwd="/workspace",
        )
        await sandbox.execute_command(
            ("git", "config", "--local", "--", "user.email", user.email),
            cwd="/workspace",
        )

    async def _resolve_snapshot_binding(
        self,
        snapshot: SessionSnapshotRef,
        repository: str,
        user: UserIdentity,
    ) -> ResolvedSnapshotBinding:
        """Resolve and validate authoritative snapshot ownership."""
        if (
            type(snapshot) is not SessionSnapshotRef
            or self.snapshot_binding_provider is None
        ):
            raise RepositoryAccessError("Repository access denied.")
        try:
            binding = await self.snapshot_binding_provider.resolve(
                snapshot.snapshot_id,
                repository,
                user.id,
            )
        except Exception:
            raise RepositoryAccessError("Repository access denied.") from None
        if (
            type(binding) is not ResolvedSnapshotBinding
            or binding.snapshot_id != snapshot.snapshot_id
            or binding.repository != repository
            or binding.principal_id != user.id
        ):
            raise RepositoryAccessError("Repository access denied.")
        return binding

    async def _attest_snapshot_binding(
        self,
        operation: _TeardownOperation,
        repository: str,
        principal_id: str,
    ) -> ResolvedSnapshotBinding:
        """Create or reconcile one stable remote attestation operation."""
        if self.snapshot_binding_provider is None or operation.snapshot is None:
            raise SnapshotBindingError("Snapshot attestation failed.")
        if operation.binding is not None:
            binding = operation.binding
        elif operation.attestation_ambiguous:
            binding = await self._resolve_ambiguous_attestation(operation.operation_id)
        else:
            try:
                binding = await self.snapshot_binding_provider.attest_create_if_absent(
                    operation.operation_id,
                    operation.snapshot,
                    repository,
                    principal_id,
                )
            except SnapshotBindingCollisionError:
                raise
            except asyncio.CancelledError:
                operation.attestation_ambiguous = True
                resolved = await self._try_resolve_attestation(operation.operation_id)
                if resolved is not None:
                    self._validate_attested_snapshot(
                        resolved,
                        operation.snapshot,
                        repository,
                        principal_id,
                    )
                    operation.binding = resolved
                raise
            except Exception:
                operation.attestation_ambiguous = True
                binding = await self._resolve_ambiguous_attestation(
                    operation.operation_id
                )

        self._validate_attested_snapshot(
            binding,
            operation.snapshot,
            repository,
            principal_id,
        )
        operation.binding = binding
        return binding

    @staticmethod
    def _validate_attested_snapshot(
        binding: object,
        snapshot: CreatedSnapshot,
        repository: str,
        principal_id: str,
    ) -> None:
        """Reject an operation result that was rebound to another subject."""
        if (
            type(binding) is not ResolvedSnapshotBinding
            or binding.snapshot_id != snapshot.snapshot_id
            or binding.generation != snapshot.generation
            or binding.content_digest != snapshot.content_digest
            or binding.repository != repository
            or binding.principal_id != principal_id
        ):
            raise SnapshotBindingCollisionError("Snapshot binding collision.")

    async def _try_resolve_attestation(
        self,
        operation_id: UUID,
    ) -> Optional[ResolvedSnapshotBinding]:
        """Best-effort resolution used while preserving cancellation."""
        if self.snapshot_binding_provider is None:
            return None
        try:
            return await self.snapshot_binding_provider.resolve_attestation(
                operation_id
            )
        except Exception:
            return None

    async def _resolve_ambiguous_attestation(
        self,
        operation_id: UUID,
    ) -> ResolvedSnapshotBinding:
        """Resolve an ambiguous create without repeating its side effect."""
        if self.snapshot_binding_provider is None:
            raise SnapshotReconciliationRequiredError(
                "Snapshot attestation requires reconciliation."
            )
        try:
            binding = await self.snapshot_binding_provider.resolve_attestation(
                operation_id
            )
        except Exception:
            raise SnapshotReconciliationRequiredError(
                "Snapshot attestation requires reconciliation."
            ) from None
        if binding is None:
            raise SnapshotReconciliationRequiredError(
                "Snapshot attestation requires reconciliation."
            )
        return binding

    async def _restore_from_snapshot(
        self,
        binding: ResolvedSnapshotBinding,
    ) -> Sandbox:
        """Restore the exact authoritative generation and digest."""
        pass

    async def _cold_start(self, repo_url: str) -> Sandbox:
        """Return a fully synchronized cold sandbox or raise before exposure."""
        pass


class AgentSession:
    """Thin I/O wrapper for a sandbox that has already reached readiness.

    SandboxManager and WarmPoolManager must complete repository sync before
    constructing or offering this session. There is therefore no local write
    queue, polling loop, or second write path.
    """

    def __init__(self, sandbox: Sandbox) -> None:
        self.sandbox = sandbox

    async def read_file(self, path: str) -> str:
        """Read a file from a ready sandbox."""
        return await self.sandbox.read_file(path)

    async def write_file(self, path: str, content: str) -> None:
        """Write a file exactly once to a ready sandbox."""
        await self.sandbox.write_file(path, content)


if __name__ == "__main__":
    raise SystemExit(
        "Preparatory pseudocode only: supply verified provider adapters and tests "
        "before constructing a hosted-agent runtime."
    )
