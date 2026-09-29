"""Security regressions for the hosted-agent sandbox manager example."""

from __future__ import annotations

import asyncio
import contextlib
import importlib.util
import io
import sys
import unittest
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch
from uuid import UUID


MODULE_PATH = Path(__file__).resolve().parents[1] / "scripts" / "sandbox_manager.py"
REFERENCE_PATH = (
    Path(__file__).resolve().parents[1] / "references" / "infrastructure-patterns.md"
)
SKILL_PATH = Path(__file__).resolve().parents[1] / "SKILL.md"
MODULE_NAME = "hosted_agents_sandbox_manager"
MODULE_SPEC = importlib.util.spec_from_file_location(MODULE_NAME, MODULE_PATH)
if MODULE_SPEC is None or MODULE_SPEC.loader is None:
    raise RuntimeError(f"Unable to load sandbox manager from {MODULE_PATH}")
SANDBOX_MANAGER = importlib.util.module_from_spec(MODULE_SPEC)
sys.modules[MODULE_NAME] = SANDBOX_MANAGER
MODULE_SPEC.loader.exec_module(SANDBOX_MANAGER)

PINNED_BASE_IMAGE = f"example@sha256:{'a' * 64}"


def _created_snapshot(
    snapshot_id: str,
    *,
    generation: int = 1,
    digest_character: str = "b",
) -> Any:
    return SANDBOX_MANAGER.CreatedSnapshot(
        snapshot_id=snapshot_id,
        generation=generation,
        content_digest=f"sha256:{digest_character * 64}",
    )


class RecordingSandbox(SANDBOX_MANAGER.Sandbox):
    def __init__(self, repository: str = "owner/repository") -> None:
        config = SANDBOX_MANAGER.SandboxConfig(
            repo_url=repository,
            base_image=PINNED_BASE_IMAGE,
        )
        super().__init__(
            id="sandbox-1",
            config=config,
            state=SANDBOX_MANAGER.SandboxState.READY,
            created_at=SANDBOX_MANAGER.datetime.utcnow(),
            resource_policy_attestation=(
                SANDBOX_MANAGER.ResourcePolicyAttestation(
                    attestation_id=UUID("00000000-0000-4000-8000-000000000050"),
                    config_digest=config.policy_digest(),
                )
            ),
        )
        self.calls: list[tuple[Any, Any]] = []
        self.file_writes: list[tuple[str, str]] = []

    async def _execute_command(
        self, spec: Any, *, credential: Any = None
    ) -> dict[str, Any]:
        self.calls.append((spec, credential))
        return {"stdout": "", "stderr": "", "exit_code": 0}

    async def write_file(self, path: str, content: str) -> None:
        self.file_writes.append((path, content))


class RecordingImageBuilder(SANDBOX_MANAGER.ImageBuilder):
    def __init__(self, provider: Any) -> None:
        super().__init__(provider)
        self.calls: list[tuple[Any, Any]] = []
        self.boundary_checks = 0
        self.quiescence_checks = 0
        self.finalized = False

    async def _verify_untrusted_build_boundary(self) -> None:
        self.boundary_checks += 1

    async def _assert_quiescent(self) -> None:
        self.quiescence_checks += 1

    async def _execute_build_step(
        self,
        spec: Any,
        *,
        credential: Any = None,
    ) -> None:
        self.calls.append((spec, credential))

    async def _get_commit_sha(self) -> str:
        return "a" * 40

    async def _finalize_image(self) -> str:
        self.finalized = True
        return "image-1"


class RecordingSnapshotBindingProvider:
    def __init__(self, bindings: dict[str, Any] | None = None) -> None:
        self.bindings = dict(bindings or {})
        self.operation_bindings: dict[UUID, Any] = {}
        self.resolved: list[tuple[str, str, str]] = []
        self.attested: list[tuple[str, str, str]] = []
        self.attestation_operations: list[UUID] = []
        self.reconciled_operations: list[UUID] = []

    async def resolve(
        self,
        snapshot_id: str,
        repository: str,
        principal_id: str,
    ):
        self.resolved.append((snapshot_id, repository, principal_id))
        return self.bindings.get(snapshot_id)

    async def attest_create_if_absent(
        self,
        operation_id: UUID,
        snapshot: Any,
        repository: str,
        principal_id: str,
    ):
        self.attested.append((snapshot.snapshot_id, repository, principal_id))
        self.attestation_operations.append(operation_id)
        operation_binding = self.operation_bindings.get(operation_id)
        if operation_binding is not None:
            if (
                operation_binding.snapshot_id != snapshot.snapshot_id
                or operation_binding.generation != snapshot.generation
                or operation_binding.content_digest != snapshot.content_digest
                or operation_binding.repository != repository
                or operation_binding.principal_id != principal_id
            ):
                raise SANDBOX_MANAGER.SnapshotBindingCollisionError(
                    "Snapshot binding collision."
                )
            return operation_binding
        existing = self.bindings.get(snapshot.snapshot_id)
        if existing is not None:
            if (
                existing.generation != snapshot.generation
                or existing.content_digest != snapshot.content_digest
                or existing.repository != repository
                or existing.principal_id != principal_id
            ):
                raise SANDBOX_MANAGER.SnapshotBindingCollisionError(
                    "Snapshot binding collision."
                )
            self.operation_bindings[operation_id] = existing
            return existing
        binding = SANDBOX_MANAGER.ResolvedSnapshotBinding(
            attestation_id=UUID("00000000-0000-4000-8000-000000000020"),
            snapshot_id=snapshot.snapshot_id,
            generation=snapshot.generation,
            content_digest=snapshot.content_digest,
            repository=repository,
            principal_id=principal_id,
        )
        self.bindings[snapshot.snapshot_id] = binding
        self.operation_bindings[operation_id] = binding
        return binding

    async def resolve_attestation(self, operation_id: UUID):
        self.reconciled_operations.append(operation_id)
        return self.operation_bindings.get(operation_id)


class RepositoryValidationTests(unittest.TestCase):
    def test_repository_slug_and_https_url_normalize_to_one_key(self) -> None:
        normalize = SANDBOX_MANAGER.normalize_github_repository
        self.assertEqual(normalize(" Owner/Repository "), "owner/repository")
        self.assertEqual(
            normalize("https://github.com/Owner/Repository.git"),
            "owner/repository",
        )
        self.assertEqual(
            SANDBOX_MANAGER.github_clone_url("Owner/Repository"),
            "https://github.com/owner/repository.git",
        )

    def test_malicious_or_credentialed_repository_values_are_rejected(self) -> None:
        secret = "TOP_SECRET_INSTALLATION_TOKEN"
        invalid = (
            "owner/repository; touch /tmp/pwned",
            "owner/repository\nmalicious",
            "../../etc/passwd",
            "git@github.com:owner/repository.git",
            "https://evil.example/owner/repository",
            "https://github.com/owner/repository?ref=main",
            f"https://x-access-token:{secret}@github.com/owner/repository",
        )

        for value in invalid:
            with self.subTest(value=value):
                with self.assertRaisesRegex(
                    ValueError,
                    r"^Invalid GitHub repository identifier\.$",
                ) as caught:
                    SANDBOX_MANAGER.normalize_github_repository(value)
                self.assertNotIn(secret, str(caught.exception))

    def test_sandbox_config_requires_pinned_image_and_bounded_integer_resources(
        self,
    ) -> None:
        config = SANDBOX_MANAGER.SandboxConfig(
            repo_url="Owner/Repository",
            base_image=PINNED_BASE_IMAGE,
            memory_mb=4096,
            cpu_cores=2,
            disk_gb=10,
            timeout_hours=4,
        )
        self.assertEqual(config.repo_url, "owner/repository")
        self.assertEqual(config.max_processes, 256)
        self.assertEqual(config.max_command_output_bytes, 16 * 1024 * 1024)
        self.assertEqual(config.network_mode, "none")
        self.assertEqual(config.max_network_egress_bytes, 0)
        self.assertRegex(config.policy_digest(), r"^sha256:[0-9a-f]{64}$")

        brokered = SANDBOX_MANAGER.SandboxConfig(
            repo_url="owner/repository",
            base_image=PINNED_BASE_IMAGE,
            network_mode="brokered",
            max_network_egress_bytes=1024,
            egress_policy_digest=f"sha256:{'e' * 64}",
        )
        self.assertEqual(brokered.max_network_egress_bytes, 1024)

        invalid = (
            {"base_image": "example:latest"},
            {"base_image": "example@sha256:abc"},
            {"memory_mb": True},
            {"memory_mb": 127},
            {"cpu_cores": 0},
            {"disk_gb": 0},
            {"timeout_hours": 0},
            {"max_processes": True},
            {"max_processes": 0},
            {"max_command_output_bytes": 1023},
            {"network_mode": "unrestricted"},
            {"max_network_egress_bytes": 1},
            {"network_mode": "brokered", "max_network_egress_bytes": 0},
            {
                "network_mode": "brokered",
                "max_network_egress_bytes": 1024,
                "egress_policy_digest": "sha256:bad",
            },
        )
        for overrides in invalid:
            values = {
                "repo_url": "owner/repository",
                "base_image": PINNED_BASE_IMAGE,
                **overrides,
            }
            with self.subTest(overrides=overrides):
                with self.assertRaises(ValueError):
                    SANDBOX_MANAGER.SandboxConfig(**values)

    def test_pool_and_build_cadence_require_finite_typed_bounds(self) -> None:
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        invalid_pool_args = (
            {"target_pool_size": True},
            {"target_pool_size": 65},
            {"max_age": "25 minutes"},
            {"max_age": SANDBOX_MANAGER.timedelta(0)},
            {"max_age": SANDBOX_MANAGER.timedelta(days=2)},
            {"sync_timeout": SANDBOX_MANAGER.timedelta(0)},
            {"sync_timeout": SANDBOX_MANAGER.timedelta(minutes=11)},
        )
        for kwargs in invalid_pool_args:
            with self.subTest(pool=kwargs):
                with self.assertRaises(ValueError):
                    SANDBOX_MANAGER.WarmPoolManager(builder, **kwargs)

        for interval in (
            "30 minutes",
            SANDBOX_MANAGER.timedelta(0),
            SANDBOX_MANAGER.timedelta(days=2),
        ):
            with self.subTest(build_interval=interval):
                with self.assertRaises(ValueError):
                    SANDBOX_MANAGER.SandboxManager(
                        [],
                        _unused_credential_provider,
                        build_interval=interval,
                    )


class CommandBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_command_boundary_rejects_shell_strings_and_shell_dispatch(
        self,
    ) -> None:
        sandbox = RecordingSandbox()

        with self.assertRaises(TypeError):
            await sandbox.execute_command("git status")
        with self.assertRaises(ValueError):
            await sandbox.execute_command(("sh", "-c", "touch /tmp/pwned"))
        with self.assertRaises(ValueError):
            SANDBOX_MANAGER.CommandSpec(("/bin/bash", "-c", "touch /tmp/pwned"))

        self.assertEqual(sandbox.calls, [])

    async def test_identity_is_normalized_and_passed_as_single_argv_values(
        self,
    ) -> None:
        shell_like_name = '--unset-all; touch /tmp/pwned; "'
        user = SANDBOX_MANAGER.UserIdentity(
            id=" User-01 ",
            name=shell_like_name,
            email="Alice.Developer@EXAMPLE.COM",
        )
        sandbox = RecordingSandbox()
        manager = SANDBOX_MANAGER.SandboxManager([], _unused_credential_provider)

        await manager._configure_for_user(sandbox, user)

        self.assertEqual(user.id, "user-01")
        self.assertEqual(user.email, "Alice.Developer@example.com")
        self.assertEqual(
            [call[0].argv for call in sandbox.calls],
            [
                ("git", "config", "--local", "--", "user.name", shell_like_name),
                (
                    "git",
                    "config",
                    "--local",
                    "--",
                    "user.email",
                    "Alice.Developer@example.com",
                ),
            ],
        )
        self.assertTrue(all(call[0].cwd == "/workspace" for call in sandbox.calls))

    async def test_repository_sync_uses_direct_argv_invocations(self) -> None:
        credential_requests: list[tuple[str, str, str]] = []

        @contextlib.asynccontextmanager
        async def provider(repository: str, operation: str, argv_digest: str):
            credential_requests.append((repository, operation, argv_digest))
            yield SANDBOX_MANAGER.EphemeralGitCredential(
                lease_id=UUID("00000000-0000-4000-8000-000000000004"),
                repository=repository,
                operation=operation,
                host="github.com",
                argv_digest=argv_digest,
                audience=(f"https://github.com/{repository}.git"),
                git_config_scope="provider-owned-clean",
                egress_policy_digest=(SANDBOX_MANAGER._GITHUB_EGRESS_POLICY_DIGEST),
            )

        sandbox = RecordingSandbox()
        warm = SANDBOX_MANAGER.WarmSandbox(
            sandbox=sandbox,
            repo_url="Owner/Repository",
            created_at=SANDBOX_MANAGER.datetime.utcnow(),
            image_version="image-1",
        )
        pool = SANDBOX_MANAGER.WarmPoolManager(SANDBOX_MANAGER.ImageBuilder(provider))

        await pool._sync_to_latest(warm)

        self.assertEqual(
            [call[0].argv for call in sandbox.calls],
            [
                (
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
                    "https://github.com/owner/repository.git",
                    "+refs/heads/main:refs/remotes/origin/main",
                ),
                ("git", "reset", "--hard", "origin/main", "--"),
            ],
        )
        self.assertTrue(all(call[0].cwd == "/workspace" for call in sandbox.calls))
        self.assertEqual(len(credential_requests), 1)
        self.assertEqual(credential_requests[0][:2], ("owner/repository", "fetch"))
        self.assertEqual(
            credential_requests[0][2],
            sandbox.calls[0][1].argv_digest,
        )
        self.assertEqual(sandbox.calls[0][1].operation, "fetch")
        self.assertIsNone(sandbox.calls[1][1])
        self.assertTrue(warm.sync_complete)

    async def test_malicious_origin_and_instead_of_cannot_receive_credential(
        self,
    ) -> None:
        class OriginRewritingSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.git_origin = "https://attacker.example/steal.git"
                self.local_instead_of = "file:///attacker"
                self.credential_destination: str | None = None

            async def _execute_command(
                self,
                spec: Any,
                *,
                credential: Any = None,
            ) -> dict[str, Any]:
                self.calls.append((spec, credential))
                if credential is not None:
                    separator = spec.argv.index("--")
                    remote = spec.argv[separator + 1]
                    if credential.git_config_scope != "provider-owned-clean":
                        self.credential_destination = self.local_instead_of
                    else:
                        self.credential_destination = (
                            self.git_origin if remote == "origin" else remote
                        )
                return {"stdout": "", "stderr": "", "exit_code": 0}

        sandbox = OriginRewritingSandbox()
        warm = SANDBOX_MANAGER.WarmSandbox(
            sandbox=sandbox,
            repo_url="owner/repository",
            created_at=SANDBOX_MANAGER.datetime.utcnow(),
            image_version="image-1",
        )
        pool = SANDBOX_MANAGER.WarmPoolManager(
            SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        )

        await pool._sync_to_latest(warm)

        fetch_spec, credential = sandbox.calls[0]
        self.assertEqual(
            sandbox.credential_destination,
            "https://github.com/owner/repository.git",
        )
        self.assertNotIn("attacker.example", repr(fetch_spec.argv))
        self.assertNotIn("origin", fetch_spec.argv)
        self.assertIn("http.followRedirects=false", fetch_spec.argv)
        self.assertEqual(credential.host, "github.com")
        self.assertEqual(credential.git_config_scope, "provider-owned-clean")
        self.assertEqual(
            credential.audience,
            "https://github.com/owner/repository.git",
        )
        self.assertEqual(
            credential.egress_policy_digest,
            SANDBOX_MANAGER._GITHUB_EGRESS_POLICY_DIGEST,
        )
        self.assertEqual(
            credential.argv_digest,
            SANDBOX_MANAGER._argv_digest(fetch_spec.argv),
        )

    async def test_credential_cannot_authorize_mutated_argv(self) -> None:
        authorized = (
            "git",
            "fetch",
            "--",
            "https://github.com/owner/repository.git",
            "+refs/heads/main:refs/remotes/origin/main",
        )
        credential = SANDBOX_MANAGER.EphemeralGitCredential(
            lease_id=UUID("00000000-0000-4000-8000-000000000005"),
            repository="owner/repository",
            operation="fetch",
            host="github.com",
            argv_digest=SANDBOX_MANAGER._argv_digest(authorized),
            audience="https://github.com/owner/repository.git",
            git_config_scope="provider-owned-clean",
            egress_policy_digest=SANDBOX_MANAGER._GITHUB_EGRESS_POLICY_DIGEST,
        )
        mutated = (*authorized[:-1], "+refs/heads/dev:refs/remotes/origin/dev")
        sandbox = RecordingSandbox()

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.CredentialLeaseError,
            r"^Credential argv scope does not match\.$",
        ):
            await sandbox.execute_command(mutated, credential=credential)

        self.assertEqual(sandbox.calls, [])

    async def test_agent_session_writes_exactly_once_without_sync_queue(self) -> None:
        sandbox = RecordingSandbox()
        session = SANDBOX_MANAGER.AgentSession(sandbox)

        self.assertFalse(hasattr(session, "pending_writes"))
        self.assertFalse(hasattr(session, "mark_sync_complete"))
        await session.write_file("/workspace/result.txt", "complete")

        self.assertEqual(
            sandbox.file_writes,
            [("/workspace/result.txt", "complete")],
        )

    async def test_invalid_identity_fields_fail_before_command_execution(self) -> None:
        sandbox = RecordingSandbox()

        invalid_fields = (
            {"id": "../../operator", "name": "Alice", "email": "alice@example.com"},
            {"id": "operator", "name": "Alice\nInjected", "email": "alice@example.com"},
            {
                "id": "operator",
                "name": "Alice\u202eInjected",
                "email": "alice@example.com",
            },
            {"id": "operator", "name": "Alice", "email": "alice@example.com\nInjected"},
            {"id": "operator", "name": "Alice", "email": "not-an-email"},
        )
        for fields in invalid_fields:
            with self.subTest(fields=fields):
                with self.assertRaises(ValueError):
                    SANDBOX_MANAGER.UserIdentity(**fields)

        self.assertEqual(sandbox.calls, [])


class CredentialBoundaryTests(unittest.IsolatedAsyncioTestCase):
    async def test_clone_uses_clean_url_and_ephemeral_opaque_credential(self) -> None:
        secret = "TOP_SECRET_INSTALLATION_TOKEN"
        leases: list[Any] = []

        @contextlib.asynccontextmanager
        async def provider(repository: str, operation: str, argv_digest: str):
            # A real broker owns the secret. The manager receives only this handle.
            self.assertEqual(repository, "owner/repository")
            self.assertEqual(operation, "clone")
            credential = SANDBOX_MANAGER.EphemeralGitCredential(
                lease_id=UUID("00000000-0000-4000-8000-000000000001"),
                repository=repository,
                operation=operation,
                host="github.com",
                argv_digest=argv_digest,
                audience=(f"https://github.com/{repository}.git"),
                git_config_scope="provider-owned-clean",
                egress_policy_digest=(SANDBOX_MANAGER._GITHUB_EGRESS_POLICY_DIGEST),
            )
            leases.append(credential)
            yield credential

        builder = RecordingImageBuilder(provider)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            image = await builder.build_image("https://github.com/Owner/Repository.git")

        clone_spec, clone_credential = builder.calls[0]
        self.assertEqual(
            clone_spec.argv,
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
                "https://github.com/owner/repository.git",
                "/workspace",
            ),
        )
        self.assertIs(clone_credential, leases[0])
        self.assertEqual(clone_credential.operation, "clone")
        self.assertEqual(image.repo_url, "owner/repository")
        self.assertNotIn("@github.com", clone_spec.argv[-2])

        observable = "\n".join(
            [output.getvalue(), repr(builder.calls), repr(builder.images), repr(leases)]
        )
        self.assertNotIn(secret, observable)
        self.assertNotIn("x-access-token", observable)
        self.assertNotIn("00000000", repr(leases[0]))

    async def test_build_pipeline_contains_no_shell_control_operators(self) -> None:
        builder = RecordingImageBuilder(_unused_credential_provider)
        await builder.build_image("owner/repository")

        specs = [spec for spec, _credential in builder.calls]
        self.assertEqual(len(specs), 4)
        for spec in specs:
            self.assertIsInstance(spec.argv, tuple)
            self.assertNotIn("&&", spec.argv)
            self.assertNotIn("||", spec.argv)
            self.assertNotIn("&", spec.argv)
            self.assertNotIn("cd", spec.argv)
            self.assertFalse(spec.background)
            self.assertTrue(spec.check)

        self.assertFalse(any(spec.argv[:3] == ("npm", "run", "dev") for spec in specs))
        self.assertFalse(any(spec.argv[0] == "sleep" for spec in specs))
        self.assertEqual(builder.boundary_checks, 1)
        self.assertEqual(builder.quiescence_checks, 1)
        self.assertTrue(builder.finalized)

    async def test_quiescence_failure_blocks_image_finalization(self) -> None:
        class NonQuiescentBuilder(RecordingImageBuilder):
            async def _assert_quiescent(self) -> None:
                self.quiescence_checks += 1
                raise RuntimeError("residual process detected")

        builder = NonQuiescentBuilder(_unused_credential_provider)
        with self.assertRaisesRegex(RuntimeError, "residual process detected"):
            await builder.build_image("owner/repository")

        self.assertEqual(builder.boundary_checks, 1)
        self.assertEqual(builder.quiescence_checks, 1)
        self.assertFalse(builder.finalized)

    async def test_missing_build_isolation_blocks_repository_code(self) -> None:
        class UnisolatedBuilder(RecordingImageBuilder):
            async def _verify_untrusted_build_boundary(self) -> None:
                self.boundary_checks += 1
                raise RuntimeError("build isolation unavailable")

        builder = UnisolatedBuilder(_unused_credential_provider)
        with self.assertRaisesRegex(RuntimeError, "build isolation unavailable"):
            await builder.build_image("owner/repository")

        self.assertEqual(builder.boundary_checks, 1)
        self.assertEqual(len(builder.calls), 1)
        self.assertEqual(builder.calls[0][0].argv[0], "git")
        self.assertIn("clone", builder.calls[0][0].argv)
        self.assertEqual(builder.quiescence_checks, 0)
        self.assertFalse(builder.finalized)

    async def test_user_identity_has_no_persisted_token_field(self) -> None:
        secret = "TOP_SECRET_USER_TOKEN"
        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )

        self.assertFalse(hasattr(user, "github_token"))
        with self.assertRaises((AttributeError, TypeError)):
            user.github_token = secret
        self.assertNotIn(secret, repr(user))

    async def test_provider_error_text_is_not_disclosed_by_build_loop(self) -> None:
        secret = "TOP_SECRET_PROVIDER_DETAIL"

        @contextlib.asynccontextmanager
        async def failing_provider(
            repository: str,
            operation: str,
            argv_digest: str,
        ):
            raise RuntimeError(f"broker response contained {secret}")
            yield  # pragma: no cover - preserves the async-generator contract

        manager = SANDBOX_MANAGER.SandboxManager(
            ["owner/repository"],
            failing_provider,
        )

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.CredentialLeaseError,
            r"^Credentialed Git operation failed\.$",
        ) as caught:
            await manager.image_builder.build_image("owner/repository")
        self.assertNotIn(secret, str(caught.exception))

        output = io.StringIO()
        with (
            patch.object(
                SANDBOX_MANAGER.asyncio,
                "sleep",
                new=AsyncMock(side_effect=asyncio.CancelledError),
            ),
            contextlib.redirect_stdout(output),
            self.assertRaises(asyncio.CancelledError),
        ):
            await manager.start_build_loop()

        self.assertNotIn(secret, output.getvalue())
        self.assertNotIn("broker response contained", output.getvalue())
        self.assertIn("CredentialLeaseError", output.getvalue())

    async def test_credential_scope_must_match_repository(self) -> None:
        @contextlib.asynccontextmanager
        async def wrong_scope_provider(
            repository: str,
            operation: str,
            argv_digest: str,
        ):
            yield SANDBOX_MANAGER.EphemeralGitCredential(
                lease_id=UUID("00000000-0000-4000-8000-000000000002"),
                repository="another/repository",
                operation=operation,
                host="github.com",
                argv_digest=argv_digest,
                audience=("https://github.com/another/repository.git"),
                git_config_scope="provider-owned-clean",
                egress_policy_digest=(SANDBOX_MANAGER._GITHUB_EGRESS_POLICY_DIGEST),
            )

        builder = RecordingImageBuilder(wrong_scope_provider)
        with self.assertRaisesRegex(
            SANDBOX_MANAGER.CredentialLeaseError,
            "Credential scope does not match",
        ):
            await builder.build_image("owner/repository")
        self.assertEqual(builder.calls, [])

    async def test_raw_credential_value_is_rejected_before_execution(self) -> None:
        secret = "TOP_SECRET_RAW_CREDENTIAL"

        @contextlib.asynccontextmanager
        async def unsafe_provider(
            repository: str,
            operation: str,
            argv_digest: str,
        ):
            yield secret

        builder = RecordingImageBuilder(unsafe_provider)
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            with self.assertRaisesRegex(
                SANDBOX_MANAGER.CredentialLeaseError,
                "invalid lease type",
            ):
                await builder.build_image("owner/repository")

        self.assertEqual(builder.calls, [])
        self.assertNotIn(secret, output.getvalue())

        with self.assertRaises(ValueError):
            SANDBOX_MANAGER.EphemeralGitCredential(
                lease_id=secret,
                repository="owner/repository",
                operation="clone",
                host="github.com",
                argv_digest=f"sha256:{'0' * 64}",
                audience="https://github.com/owner/repository.git",
                git_config_scope="provider-owned-clean",
                egress_policy_digest=(SANDBOX_MANAGER._GITHUB_EGRESS_POLICY_DIGEST),
            )

    async def test_sync_failure_never_enters_or_remains_in_warm_pool(self) -> None:
        class FetchFailSandbox(RecordingSandbox):
            async def _execute_command(
                self,
                spec: Any,
                *,
                credential: Any = None,
            ) -> dict[str, Any]:
                self.calls.append((spec, credential))
                raise RuntimeError("transport detail must not escape")

        class FixedSandboxPool(SANDBOX_MANAGER.WarmPoolManager):
            def __init__(self, builder: Any, sandbox: Any) -> None:
                super().__init__(builder, target_pool_size=1)
                self.created_sandbox = sandbox

            async def _create_sandbox_from_image(self, image: Any):
                return self.created_sandbox

        repository = "owner/repository"
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        builder.images[repository] = SANDBOX_MANAGER.RepositoryImage(
            repo_url=repository,
            image_id="image-1",
            commit_sha="a" * 40,
            built_at=SANDBOX_MANAGER.datetime.utcnow(),
        )
        sandbox = FetchFailSandbox()
        pool = FixedSandboxPool(builder, sandbox)

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.WarmSyncError,
            r"^Warm sandbox synchronization failed\.$",
        ) as caught:
            await pool.maintain_pool(repository)

        self.assertNotIn("transport detail", str(caught.exception))
        self.assertEqual(pool.pools[repository], [])
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)

    async def test_sync_timeout_is_typed_and_terminates_candidate(self) -> None:
        class HangingSandbox(RecordingSandbox):
            async def _execute_command(
                self,
                spec: Any,
                *,
                credential: Any = None,
            ) -> dict[str, Any]:
                self.calls.append((spec, credential))
                await asyncio.Event().wait()
                raise AssertionError("unreachable")

        class FixedSandboxPool(SANDBOX_MANAGER.WarmPoolManager):
            def __init__(self, builder: Any, sandbox: Any) -> None:
                super().__init__(
                    builder,
                    target_pool_size=1,
                    sync_timeout=SANDBOX_MANAGER.timedelta(milliseconds=1),
                )
                self.created_sandbox = sandbox

            async def _create_sandbox_from_image(self, image: Any):
                return self.created_sandbox

        repository = "owner/repository"
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        builder.images[repository] = SANDBOX_MANAGER.RepositoryImage(
            repo_url=repository,
            image_id="image-1",
            commit_sha="a" * 40,
            built_at=SANDBOX_MANAGER.datetime.utcnow(),
        )
        sandbox = HangingSandbox()
        pool = FixedSandboxPool(builder, sandbox)

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.WarmSyncError,
            r"^Warm sandbox synchronization timed out\.$",
        ):
            await pool.maintain_pool(repository)

        self.assertEqual(pool.pools[repository], [])
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)

    async def test_unsynced_sandbox_is_never_offered(self) -> None:
        repository = "owner/repository"
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        builder.images[repository] = SANDBOX_MANAGER.RepositoryImage(
            repo_url=repository,
            image_id="image-1",
            commit_sha="a" * 40,
            built_at=SANDBOX_MANAGER.datetime.utcnow(),
        )
        pool = SANDBOX_MANAGER.WarmPoolManager(builder)
        pool.pools[repository] = [
            SANDBOX_MANAGER.WarmSandbox(
                sandbox=RecordingSandbox(),
                repo_url=repository,
                created_at=SANDBOX_MANAGER.datetime.utcnow(),
                image_version="image-1",
                sync_complete=False,
            )
        ]

        self.assertIsNone(await pool.get_warm_sandbox(repository))

    async def test_stale_pool_cleanup_and_concurrent_maintenance_are_bounded(
        self,
    ) -> None:
        class CountingPool(SANDBOX_MANAGER.WarmPoolManager):
            def __init__(self, builder: Any) -> None:
                super().__init__(builder, target_pool_size=1)
                self.created = 0

            async def _create_sandbox_from_image(self, image: Any):
                self.created += 1
                await asyncio.sleep(0)
                return RecordingSandbox()

        repository = "owner/repository"
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        builder.images[repository] = SANDBOX_MANAGER.RepositoryImage(
            repo_url=repository,
            image_id="image-1",
            commit_sha="a" * 40,
            built_at=SANDBOX_MANAGER.datetime.utcnow(),
        )
        pool = CountingPool(builder)
        stale = SANDBOX_MANAGER.WarmSandbox(
            sandbox=RecordingSandbox(),
            repo_url=repository,
            created_at=SANDBOX_MANAGER.datetime.utcnow()
            - SANDBOX_MANAGER.timedelta(hours=1),
            image_version="image-1",
            sync_complete=True,
        )
        pool.pools[repository] = [stale]

        await asyncio.gather(
            pool.maintain_pool(repository),
            pool.maintain_pool(repository),
        )

        self.assertEqual(stale.sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)
        self.assertEqual(pool.created, 1)
        self.assertEqual(len(pool.pools[repository]), 1)
        self.assertTrue(pool.pools[repository][0].sync_complete)

    async def test_stale_cleanup_failure_is_quarantined_for_retry(self) -> None:
        class FlakyTerminationSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.failures_remaining = 1

            async def terminate(self) -> None:
                if self.failures_remaining:
                    self.failures_remaining -= 1
                    raise RuntimeError("provider cleanup failed")
                await super().terminate()

        repository = "owner/repository"
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        builder.images[repository] = SANDBOX_MANAGER.RepositoryImage(
            repo_url=repository,
            image_id="image-current",
            commit_sha="a" * 40,
            built_at=SANDBOX_MANAGER.datetime.utcnow(),
        )
        sandbox = FlakyTerminationSandbox()
        pool = SANDBOX_MANAGER.WarmPoolManager(builder, target_pool_size=0)
        pool.pools[repository] = [
            SANDBOX_MANAGER.WarmSandbox(
                sandbox=sandbox,
                repo_url=repository,
                created_at=SANDBOX_MANAGER.datetime.utcnow(),
                image_version="image-stale",
                sync_complete=True,
            )
        ]

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.SandboxCleanupError,
            r"^Sandbox cleanup requires supervised retry\.$",
        ):
            await pool.maintain_pool(repository)

        self.assertEqual(pool.quarantined_cleanup_count, 1)
        self.assertEqual(pool.pools[repository], [])
        self.assertEqual(await pool.retry_quarantined_cleanup(), 0)
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)

    async def test_stale_cleanup_cancellation_retains_serialized_ownership(
        self,
    ) -> None:
        class CancelOnceTerminationSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.termination_attempts = 0

            async def terminate(self) -> None:
                self.termination_attempts += 1
                if self.termination_attempts == 1:
                    raise asyncio.CancelledError
                await super().terminate()

        repository = "owner/repository"
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        builder.images[repository] = SANDBOX_MANAGER.RepositoryImage(
            repo_url=repository,
            image_id="image-current",
            commit_sha="a" * 40,
            built_at=SANDBOX_MANAGER.datetime.utcnow(),
        )
        sandbox = CancelOnceTerminationSandbox()
        pool = SANDBOX_MANAGER.WarmPoolManager(builder, target_pool_size=0)
        pool.pools[repository] = [
            SANDBOX_MANAGER.WarmSandbox(
                sandbox=sandbox,
                repo_url=repository,
                created_at=SANDBOX_MANAGER.datetime.utcnow(),
                image_version="image-stale",
                sync_complete=True,
            )
        ]

        with self.assertRaises(asyncio.CancelledError):
            await pool.maintain_pool(repository)

        self.assertEqual(pool.pools[repository], [])
        self.assertEqual(pool.quarantined_cleanup_count, 1)
        self.assertEqual(
            await asyncio.gather(
                pool.retry_quarantined_cleanup(),
                pool.retry_quarantined_cleanup(),
            ),
            [0, 0],
        )
        self.assertEqual(sandbox.termination_attempts, 2)
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)

    async def test_retry_cannot_overlap_blocked_initial_cleanup(self) -> None:
        class BarrierTerminationSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.entered = asyncio.Event()
                self.release = asyncio.Event()
                self.calls = 0
                self.active = 0
                self.max_active = 0

            async def terminate(self) -> None:
                self.calls += 1
                self.active += 1
                self.max_active = max(self.max_active, self.active)
                self.entered.set()
                try:
                    await self.release.wait()
                finally:
                    self.active -= 1
                await super().terminate()

        repository = "owner/repository"
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        builder.images[repository] = SANDBOX_MANAGER.RepositoryImage(
            repo_url=repository,
            image_id="image-current",
            commit_sha="a" * 40,
            built_at=SANDBOX_MANAGER.datetime.utcnow(),
        )
        sandbox = BarrierTerminationSandbox()
        pool = SANDBOX_MANAGER.WarmPoolManager(builder, target_pool_size=0)
        pool.pools[repository] = [
            SANDBOX_MANAGER.WarmSandbox(
                sandbox=sandbox,
                repo_url=repository,
                created_at=SANDBOX_MANAGER.datetime.utcnow(),
                image_version="image-stale",
                sync_complete=True,
            )
        ]

        initial_cleanup = asyncio.create_task(pool.maintain_pool(repository))
        await sandbox.entered.wait()
        concurrent_retry = asyncio.create_task(pool.retry_quarantined_cleanup())
        await asyncio.sleep(0)

        self.assertEqual(pool.quarantined_cleanup_count, 1)
        self.assertEqual(sandbox.calls, 1)
        self.assertEqual(sandbox.max_active, 1)
        self.assertFalse(concurrent_retry.done())

        sandbox.release.set()
        await initial_cleanup
        self.assertEqual(await concurrent_retry, 0)
        self.assertEqual(sandbox.calls, 1)
        self.assertEqual(sandbox.max_active, 1)
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)

    async def test_warm_sync_cleanup_failure_is_quarantined_for_retry(self) -> None:
        class FailingSyncAndCleanupSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.cleanup_failures = 1

            async def _execute_command(
                self,
                spec: Any,
                *,
                credential: Any = None,
            ) -> dict[str, Any]:
                raise RuntimeError("sync failed")

            async def terminate(self) -> None:
                if self.cleanup_failures:
                    self.cleanup_failures -= 1
                    raise RuntimeError("cleanup failed")
                await super().terminate()

        class FixedPool(SANDBOX_MANAGER.WarmPoolManager):
            def __init__(self, builder: Any, sandbox: Any) -> None:
                super().__init__(builder, target_pool_size=1)
                self.sandbox = sandbox

            async def _create_sandbox_from_image(self, image: Any):
                return self.sandbox

        repository = "owner/repository"
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        builder.images[repository] = SANDBOX_MANAGER.RepositoryImage(
            repo_url=repository,
            image_id="image-1",
            commit_sha="a" * 40,
            built_at=SANDBOX_MANAGER.datetime.utcnow(),
        )
        sandbox = FailingSyncAndCleanupSandbox()
        pool = FixedPool(builder, sandbox)

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.SandboxCleanupError,
            r"^Sandbox cleanup requires supervised retry\.$",
        ):
            await pool.maintain_pool(repository)

        self.assertEqual(pool.pools[repository], [])
        self.assertEqual(pool.quarantined_cleanup_count, 1)
        self.assertEqual(await pool.retry_quarantined_cleanup(), 0)
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)

    async def test_warm_sync_cleanup_cancellation_retains_ownership(self) -> None:
        class FailingSyncAndCancelledCleanupSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.termination_attempts = 0

            async def _execute_command(
                self,
                spec: Any,
                *,
                credential: Any = None,
            ) -> dict[str, Any]:
                raise RuntimeError("sync failed")

            async def terminate(self) -> None:
                self.termination_attempts += 1
                if self.termination_attempts == 1:
                    raise asyncio.CancelledError
                await super().terminate()

        class FixedPool(SANDBOX_MANAGER.WarmPoolManager):
            def __init__(self, builder: Any, sandbox: Any) -> None:
                super().__init__(builder, target_pool_size=1)
                self.sandbox = sandbox

            async def _create_sandbox_from_image(self, image: Any):
                return self.sandbox

        repository = "owner/repository"
        builder = SANDBOX_MANAGER.ImageBuilder(_unused_credential_provider)
        builder.images[repository] = SANDBOX_MANAGER.RepositoryImage(
            repo_url=repository,
            image_id="image-1",
            commit_sha="a" * 40,
            built_at=SANDBOX_MANAGER.datetime.utcnow(),
        )
        sandbox = FailingSyncAndCancelledCleanupSandbox()
        pool = FixedPool(builder, sandbox)

        with self.assertRaises(asyncio.CancelledError):
            await pool.maintain_pool(repository)

        self.assertEqual(pool.pools[repository], [])
        self.assertEqual(pool.quarantined_cleanup_count, 1)
        self.assertEqual(await pool.retry_quarantined_cleanup(), 0)
        self.assertEqual(sandbox.termination_attempts, 2)
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)


class SessionAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    class TestManager(SANDBOX_MANAGER.SandboxManager):
        def __init__(
            self,
            repositories: list[str],
            snapshot_bindings: dict[str, Any] | None = None,
        ) -> None:
            self.binding_provider = RecordingSnapshotBindingProvider(snapshot_bindings)
            super().__init__(
                repositories,
                _unused_credential_provider,
                snapshot_binding_provider=self.binding_provider,
            )
            self.cold_starts: list[str] = []
            self.cold_sandboxes: list[RecordingSandbox] = []
            self.restores: list[Any] = []

        async def _cold_start(self, repo_url: str):
            self.cold_starts.append(repo_url)
            sandbox = RecordingSandbox(repo_url)
            self.cold_sandboxes.append(sandbox)
            return sandbox

        async def _restore_from_snapshot(self, binding: Any):
            self.restores.append(binding)
            sandbox = RecordingSandbox(binding.repository)
            sandbox.restored_snapshot_attestation_id = binding.attestation_id
            sandbox.restored_snapshot_generation = binding.generation
            sandbox.restored_snapshot_content_digest = binding.content_digest
            return sandbox

    def _receipt(
        self,
        principal_id: str,
        repository: str,
        *,
        action: str = "session:start",
    ) -> Any:
        return SANDBOX_MANAGER.RepositoryAccessReceipt(
            receipt_id=UUID("00000000-0000-4000-8000-000000000010"),
            principal_id=principal_id,
            repository=repository,
            action=action,
            expires_at=SANDBOX_MANAGER.datetime.utcnow()
            + SANDBOX_MANAGER.timedelta(minutes=1),
        )

    async def test_start_session_rejects_unknown_cross_repo_and_cross_actor_access(
        self,
    ) -> None:
        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository", "other/repository"])

        manager.binding_provider.bindings.update(
            {
                "snapshot-1": SANDBOX_MANAGER.ResolvedSnapshotBinding(
                    attestation_id=UUID("00000000-0000-4000-8000-000000000021"),
                    snapshot_id="snapshot-1",
                    generation=1,
                    content_digest=f"sha256:{'1' * 64}",
                    repository="other/repository",
                    principal_id="operator",
                ),
                "snapshot-2": SANDBOX_MANAGER.ResolvedSnapshotBinding(
                    attestation_id=UUID("00000000-0000-4000-8000-000000000022"),
                    snapshot_id="snapshot-2",
                    generation=1,
                    content_digest=f"sha256:{'2' * 64}",
                    repository="owner/repository",
                    principal_id="another-user",
                ),
            }
        )

        cases = (
            (
                "unknown/repository",
                self._receipt("operator", "unknown/repository"),
                None,
            ),
            (
                "owner/repository",
                self._receipt("operator", "other/repository"),
                None,
            ),
            (
                "owner/repository",
                self._receipt("another-user", "owner/repository"),
                None,
            ),
            (
                "owner/repository",
                SANDBOX_MANAGER.RepositoryAccessReceipt(
                    receipt_id=UUID("00000000-0000-4000-8000-000000000011"),
                    principal_id="operator",
                    repository="owner/repository",
                    action="session:start",
                    expires_at=SANDBOX_MANAGER.datetime.utcnow()
                    - SANDBOX_MANAGER.timedelta(seconds=1),
                ),
                None,
            ),
            (
                "owner/repository",
                self._receipt(
                    "operator",
                    "owner/repository",
                    action="warm:prepare",
                ),
                None,
            ),
            (
                "owner/repository",
                self._receipt("operator", "owner/repository"),
                SANDBOX_MANAGER.SessionSnapshotRef(
                    snapshot_id="snapshot-1",
                ),
            ),
            (
                "owner/repository",
                self._receipt("operator", "owner/repository"),
                SANDBOX_MANAGER.SessionSnapshotRef(
                    snapshot_id="snapshot-2",
                ),
            ),
            (
                "owner/repository",
                self._receipt("operator", "owner/repository"),
                SANDBOX_MANAGER.SessionSnapshotRef(
                    snapshot_id="caller-forged-snapshot",
                ),
            ),
        )

        for repository, authorization, snapshot in cases:
            with self.subTest(repository=repository, snapshot=snapshot):
                with self.assertRaisesRegex(
                    SANDBOX_MANAGER.RepositoryAccessError,
                    r"^Repository access denied\.$",
                ):
                    await manager.start_session(
                        repository,
                        user,
                        authorization=authorization,
                        snapshot=snapshot,
                    )

        self.assertEqual(manager.cold_starts, [])
        self.assertEqual(manager.restores, [])

    async def test_valid_snapshot_is_bound_to_expected_repository_and_actor(
        self,
    ) -> None:
        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        binding = SANDBOX_MANAGER.ResolvedSnapshotBinding(
            attestation_id=UUID("00000000-0000-4000-8000-000000000023"),
            snapshot_id="snapshot-3",
            generation=7,
            content_digest=f"sha256:{'3' * 64}",
            repository="owner/repository",
            principal_id="operator",
        )
        manager = self.TestManager(
            ["owner/repository"],
            {"snapshot-3": binding},
        )
        snapshot = SANDBOX_MANAGER.SessionSnapshotRef(
            snapshot_id="snapshot-3",
        )

        allocation = await manager.start_session(
            "owner/repository",
            user,
            authorization=self._receipt("operator", "owner/repository"),
            snapshot=snapshot,
        )

        self.assertEqual(manager.restores, [binding])
        self.assertEqual(
            manager.binding_provider.resolved,
            [("snapshot-3", "owner/repository", "operator")],
        )
        self.assertEqual(allocation.sandbox.config.repo_url, "owner/repository")
        self.assertIn(allocation.handle, manager.active_sessions)

    async def test_resolve_restore_rebinding_is_detected_and_terminated(self) -> None:
        original = SANDBOX_MANAGER.ResolvedSnapshotBinding(
            attestation_id=UUID("00000000-0000-4000-8000-000000000024"),
            snapshot_id="snapshot-rebind",
            generation=1,
            content_digest=f"sha256:{'4' * 64}",
            repository="owner/repository",
            principal_id="operator",
        )
        rebound = SANDBOX_MANAGER.ResolvedSnapshotBinding(
            attestation_id=UUID("00000000-0000-4000-8000-000000000025"),
            snapshot_id="snapshot-rebind",
            generation=2,
            content_digest=f"sha256:{'5' * 64}",
            repository="owner/repository",
            principal_id="operator",
        )

        class RebindingProvider(RecordingSnapshotBindingProvider):
            async def resolve(
                self,
                snapshot_id: str,
                repository: str,
                principal_id: str,
            ):
                binding = await super().resolve(
                    snapshot_id,
                    repository,
                    principal_id,
                )
                self.bindings[snapshot_id] = rebound
                return binding

        class RebindingManager(self.TestManager):
            def __init__(self) -> None:
                super().__init__(["owner/repository"])
                self.binding_provider = RebindingProvider({"snapshot-rebind": original})
                self.snapshot_binding_provider = self.binding_provider
                self.restored: RecordingSandbox | None = None

            async def _restore_from_snapshot(self, binding: Any):
                # Simulate a buggy provider adapter that re-resolves the raw
                # locator after authorization and restores the rebound object.
                current = self.binding_provider.bindings[binding.snapshot_id]
                self.restored = RecordingSandbox(current.repository)
                self.restored.restored_snapshot_attestation_id = current.attestation_id
                self.restored.restored_snapshot_generation = current.generation
                self.restored.restored_snapshot_content_digest = current.content_digest
                return self.restored

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = RebindingManager()

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.RepositoryAccessError,
            r"^Repository access denied\.$",
        ):
            await manager.start_session(
                "owner/repository",
                user,
                authorization=self._receipt("operator", "owner/repository"),
                snapshot=SANDBOX_MANAGER.SessionSnapshotRef("snapshot-rebind"),
            )

        self.assertEqual(
            manager.restored.state,
            SANDBOX_MANAGER.SandboxState.TERMINATED,
        )
        self.assertEqual(manager.active_sessions, {})

    async def test_snapshot_attestation_collision_does_not_rebind(self) -> None:
        class SnapshottingSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.snapshot_creations = 0

            async def _prepare_snapshot_finalization(self) -> None:
                return None

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                self.snapshot_creations += 1
                return _created_snapshot("snapshot-collision")

        existing = SANDBOX_MANAGER.ResolvedSnapshotBinding(
            attestation_id=UUID("00000000-0000-4000-8000-000000000026"),
            snapshot_id="snapshot-collision",
            generation=3,
            content_digest=f"sha256:{'6' * 64}",
            repository="owner/repository",
            principal_id="operator",
        )
        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(
            ["owner/repository"],
            {"snapshot-collision": existing},
        )
        sandbox = SnapshottingSandbox()
        sandbox.current_user = user
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000043")
        )
        manager.active_sessions[handle] = sandbox

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.SnapshotBindingCollisionError,
            r"^Snapshot binding collision\.$",
        ):
            await manager.end_session(handle)

        self.assertIs(
            manager.binding_provider.bindings["snapshot-collision"],
            existing,
        )
        self.assertEqual(sandbox.snapshot_creations, 1)
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.READY)
        self.assertIs(manager.active_sessions[handle], sandbox)
        self.assertIn(handle, manager._teardown_operations)

    async def test_start_returns_handle_that_drives_complete_lifecycle(self) -> None:
        class SnapshottingSandbox(RecordingSandbox):
            async def _prepare_snapshot_finalization(self) -> None:
                return None

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                return _created_snapshot("snapshot-lifecycle")

        class LifecycleManager(self.TestManager):
            async def _cold_start(self, repo_url: str):
                return SnapshottingSandbox(repo_url)

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = LifecycleManager(["owner/repository"])

        allocation = await manager.start_session(
            "owner/repository",
            user,
            authorization=self._receipt("operator", "owner/repository"),
        )
        reference = await manager.end_session(allocation.handle)

        self.assertIsInstance(allocation.handle, SANDBOX_MANAGER.SessionHandle)
        self.assertIsInstance(allocation.handle.value, UUID)
        self.assertNotIn("operator", repr(allocation.handle))
        self.assertEqual(reference.snapshot_id, "snapshot-lifecycle")
        self.assertEqual(manager.active_sessions, {})
        self.assertEqual(
            allocation.sandbox.state,
            SANDBOX_MANAGER.SandboxState.TERMINATED,
        )

    async def test_forced_handle_collision_is_rejected_without_overwrite(self) -> None:
        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])
        fixed_handle = UUID("00000000-0000-4000-8000-000000000040")

        with patch.object(SANDBOX_MANAGER, "uuid4", return_value=fixed_handle):
            first = await manager.start_session(
                "owner/repository",
                user,
                authorization=self._receipt("operator", "owner/repository"),
            )
            with self.assertRaisesRegex(
                SANDBOX_MANAGER.SessionHandleCollisionError,
                r"^Session handle collision\.$",
            ):
                await manager.start_session(
                    "owner/repository",
                    user,
                    authorization=self._receipt("operator", "owner/repository"),
                )

        self.assertEqual(len(manager.active_sessions), 1)
        self.assertIs(manager.active_sessions[first.handle], first.sandbox)
        self.assertEqual(
            manager.cold_sandboxes[0].state,
            SANDBOX_MANAGER.SandboxState.READY,
        )
        self.assertEqual(
            manager.cold_sandboxes[1].state,
            SANDBOX_MANAGER.SandboxState.TERMINATED,
        )

    async def test_configuration_failure_terminates_acquired_sandbox(self) -> None:
        class FailingSandbox(RecordingSandbox):
            async def _execute_command(
                self,
                spec: Any,
                *,
                credential: Any = None,
            ) -> dict[str, Any]:
                raise RuntimeError("git configuration failed")

        class FailingManager(self.TestManager):
            def __init__(self) -> None:
                super().__init__(["owner/repository"])
                self.acquired = FailingSandbox()

            async def _cold_start(self, repo_url: str):
                return self.acquired

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = FailingManager()

        with self.assertRaisesRegex(RuntimeError, "git configuration failed"):
            await manager.start_session(
                "owner/repository",
                user,
                authorization=self._receipt(
                    "operator",
                    "owner/repository",
                ),
            )

        self.assertEqual(
            manager.acquired.state,
            SANDBOX_MANAGER.SandboxState.TERMINATED,
        )
        self.assertEqual(manager.active_sessions, {})

    async def test_configuration_cleanup_failure_is_quarantined_for_retry(
        self,
    ) -> None:
        class FailingConfigureAndCleanupSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.cleanup_failures = 1

            async def _execute_command(
                self,
                spec: Any,
                *,
                credential: Any = None,
            ) -> dict[str, Any]:
                raise RuntimeError("git configuration failed")

            async def terminate(self) -> None:
                if self.cleanup_failures:
                    self.cleanup_failures -= 1
                    raise RuntimeError("cleanup failed")
                await super().terminate()

        class FailingManager(self.TestManager):
            def __init__(self) -> None:
                super().__init__(["owner/repository"])
                self.acquired = FailingConfigureAndCleanupSandbox()

            async def _cold_start(self, repo_url: str):
                return self.acquired

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = FailingManager()

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.SandboxCleanupError,
            r"^Sandbox cleanup requires supervised retry\.$",
        ):
            await manager.start_session(
                "owner/repository",
                user,
                authorization=self._receipt("operator", "owner/repository"),
            )

        self.assertEqual(manager.active_sessions, {})
        self.assertEqual(manager.quarantined_cleanup_count, 1)
        self.assertEqual(await manager.retry_quarantined_cleanup(), 0)
        self.assertEqual(
            manager.acquired.state,
            SANDBOX_MANAGER.SandboxState.TERMINATED,
        )

    async def test_acquired_cleanup_cancellation_retains_ownership(self) -> None:
        class FailingConfigureAndCancelledCleanupSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.termination_attempts = 0

            async def _execute_command(
                self,
                spec: Any,
                *,
                credential: Any = None,
            ) -> dict[str, Any]:
                raise RuntimeError("git configuration failed")

            async def terminate(self) -> None:
                self.termination_attempts += 1
                if self.termination_attempts == 1:
                    raise asyncio.CancelledError
                await super().terminate()

        class FailingManager(self.TestManager):
            def __init__(self) -> None:
                super().__init__(["owner/repository"])
                self.acquired = FailingConfigureAndCancelledCleanupSandbox()

            async def _cold_start(self, repo_url: str):
                return self.acquired

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = FailingManager()

        with self.assertRaises(asyncio.CancelledError):
            await manager.start_session(
                "owner/repository",
                user,
                authorization=self._receipt("operator", "owner/repository"),
            )

        self.assertEqual(manager.active_sessions, {})
        self.assertEqual(manager.quarantined_cleanup_count, 1)
        self.assertEqual(await manager.retry_quarantined_cleanup(), 0)
        self.assertEqual(manager.acquired.termination_attempts, 2)
        self.assertEqual(
            manager.acquired.state,
            SANDBOX_MANAGER.SandboxState.TERMINATED,
        )

    async def test_unattested_resource_policy_is_rejected_before_exposure(
        self,
    ) -> None:
        class UnattestedManager(self.TestManager):
            def __init__(self) -> None:
                super().__init__(["owner/repository"])
                self.acquired = RecordingSandbox()
                self.acquired.resource_policy_attestation = (
                    SANDBOX_MANAGER.ResourcePolicyAttestation(
                        attestation_id=UUID("00000000-0000-4000-8000-000000000051"),
                        config_digest=f"sha256:{'f' * 64}",
                    )
                )

            async def _cold_start(self, repo_url: str):
                return self.acquired

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = UnattestedManager()

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.RepositoryAccessError,
            r"^Repository access denied\.$",
        ):
            await manager.start_session(
                "owner/repository",
                user,
                authorization=self._receipt("operator", "owner/repository"),
            )

        self.assertEqual(
            manager.acquired.state,
            SANDBOX_MANAGER.SandboxState.TERMINATED,
        )

    async def test_missing_principal_is_cleaned_up_before_error(self) -> None:
        manager = self.TestManager(["owner/repository"])
        sandbox = RecordingSandbox()
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000041")
        )
        manager.active_sessions[handle] = sandbox

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.MalformedSessionError,
            r"^Session state is invalid\.$",
        ):
            await manager.end_session(handle)

        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)
        self.assertEqual(manager.active_sessions, {})
        self.assertEqual(manager.binding_provider.attested, [])

    async def test_post_attestation_termination_retry_is_idempotent(self) -> None:
        class FlakyTerminationSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.snapshot_creations = 0
                self.termination_attempts = 0

            async def _prepare_snapshot_finalization(self) -> None:
                return None

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                self.snapshot_creations += 1
                return _created_snapshot("snapshot-retry")

            async def terminate(self) -> None:
                self.termination_attempts += 1
                if self.termination_attempts == 1:
                    raise RuntimeError("provider termination failed")
                await super().terminate()

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])
        sandbox = FlakyTerminationSandbox()
        sandbox.current_user = user
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000042")
        )
        manager.active_sessions[handle] = sandbox

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.SessionTerminationError,
            r"^Session termination failed\.$",
        ):
            await manager.end_session(handle)

        self.assertIn(handle, manager.active_sessions)
        second = await manager.end_session(handle)
        third = await manager.end_session(handle)

        self.assertEqual(second, third)
        self.assertEqual(second.snapshot_id, "snapshot-retry")
        self.assertEqual(sandbox.snapshot_creations, 1)
        self.assertEqual(sandbox.termination_attempts, 2)
        self.assertEqual(
            manager.binding_provider.attested,
            [("snapshot-retry", "owner/repository", "operator")],
        )
        self.assertEqual(manager.active_sessions, {})

    async def test_commit_then_timeout_reconciles_same_teardown_operation(
        self,
    ) -> None:
        class CommitThenTimeoutProvider(RecordingSnapshotBindingProvider):
            async def attest_create_if_absent(
                self,
                operation_id: UUID,
                snapshot: Any,
                repository: str,
                principal_id: str,
            ):
                await super().attest_create_if_absent(
                    operation_id,
                    snapshot,
                    repository,
                    principal_id,
                )
                raise TimeoutError("response lost after commit")

        class SnapshottingSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.snapshot_creations = 0

            async def _prepare_snapshot_finalization(self) -> None:
                return None

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                self.snapshot_creations += 1
                return _created_snapshot("snapshot-commit-timeout")

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])
        manager.binding_provider = CommitThenTimeoutProvider()
        manager.snapshot_binding_provider = manager.binding_provider
        sandbox = SnapshottingSandbox()
        sandbox.current_user = user
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000044")
        )
        manager.active_sessions[handle] = sandbox

        reference = await manager.end_session(handle)
        repeated = await manager.end_session(handle)

        self.assertEqual(reference, repeated)
        self.assertEqual(reference.snapshot_id, "snapshot-commit-timeout")
        self.assertEqual(sandbox.snapshot_creations, 1)
        self.assertEqual(len(manager.binding_provider.attestation_operations), 1)
        self.assertEqual(
            manager.binding_provider.reconciled_operations,
            manager.binding_provider.attestation_operations,
        )
        self.assertEqual(manager.active_sessions, {})

    async def test_unresolved_attestation_never_repeats_snapshot_or_create(
        self,
    ) -> None:
        class AmbiguousProvider(RecordingSnapshotBindingProvider):
            async def attest_create_if_absent(
                self,
                operation_id: UUID,
                snapshot: Any,
                repository: str,
                principal_id: str,
            ):
                self.attested.append((snapshot.snapshot_id, repository, principal_id))
                self.attestation_operations.append(operation_id)
                raise TimeoutError("unknown remote outcome")

        class SnapshottingSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.snapshot_creations = 0
                self.termination_attempts = 0

            async def _prepare_snapshot_finalization(self) -> None:
                return None

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                self.snapshot_creations += 1
                return _created_snapshot("snapshot-unresolved")

            async def terminate(self) -> None:
                self.termination_attempts += 1
                await super().terminate()

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])
        manager.binding_provider = AmbiguousProvider()
        manager.snapshot_binding_provider = manager.binding_provider
        sandbox = SnapshottingSandbox()
        sandbox.current_user = user
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000045")
        )
        manager.active_sessions[handle] = sandbox

        for _ in range(2):
            with self.assertRaisesRegex(
                SANDBOX_MANAGER.SnapshotReconciliationRequiredError,
                r"^Snapshot attestation requires reconciliation\.$",
            ):
                await manager.end_session(handle)

        self.assertEqual(sandbox.snapshot_creations, 1)
        self.assertEqual(sandbox.termination_attempts, 0)
        self.assertEqual(len(manager.binding_provider.attestation_operations), 1)
        self.assertEqual(len(manager.binding_provider.reconciled_operations), 2)
        self.assertIn(handle, manager.active_sessions)

    async def test_end_session_attests_binding_and_returns_locator_only(self) -> None:
        class SnapshottingSandbox(RecordingSandbox):
            async def _prepare_snapshot_finalization(self) -> None:
                return None

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                return _created_snapshot("snapshot-new")

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])
        sandbox = SnapshottingSandbox()
        sandbox.current_user = user
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000030")
        )
        manager.active_sessions[handle] = sandbox

        reference = await manager.end_session(handle)

        self.assertEqual(
            reference,
            SANDBOX_MANAGER.SessionSnapshotRef(snapshot_id="snapshot-new"),
        )
        self.assertFalse(hasattr(reference, "repository"))
        self.assertFalse(hasattr(reference, "principal_id"))
        self.assertEqual(
            manager.binding_provider.attested,
            [("snapshot-new", "owner/repository", "operator")],
        )
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.TERMINATED)

    async def test_snapshot_finalization_failure_prevents_snapshot_and_attestation(
        self,
    ) -> None:
        class NonQuiescentSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.snapshot_created = False

            async def _prepare_snapshot_finalization(self) -> None:
                raise RuntimeError("residual process detected")

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                self.snapshot_created = True
                return _created_snapshot("unsafe-snapshot")

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])
        sandbox = NonQuiescentSandbox()
        sandbox.current_user = user
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000031")
        )
        manager.active_sessions[handle] = sandbox

        with self.assertRaisesRegex(RuntimeError, "residual process detected"):
            await manager.end_session(handle)

        self.assertFalse(sandbox.snapshot_created)
        self.assertEqual(manager.binding_provider.attested, [])
        self.assertEqual(sandbox.state, SANDBOX_MANAGER.SandboxState.READY)
        self.assertIs(manager.active_sessions[handle], sandbox)
        self.assertIn(handle, manager._teardown_operations)

    async def test_finalization_cancellation_retains_session_and_operation(
        self,
    ) -> None:
        class CancelOnceSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.finalization_attempts = 0
                self.snapshot_operations: list[UUID] = []

            async def _prepare_snapshot_finalization(self) -> None:
                self.finalization_attempts += 1
                if self.finalization_attempts == 1:
                    raise asyncio.CancelledError

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                self.snapshot_operations.append(operation_id)
                return _created_snapshot("snapshot-finalization-cancel")

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])
        sandbox = CancelOnceSandbox()
        sandbox.current_user = user
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000060")
        )
        manager.active_sessions[handle] = sandbox

        with self.assertRaises(asyncio.CancelledError):
            await manager.end_session(handle)

        operation_id = manager._teardown_operations[handle].operation_id
        self.assertIs(manager.active_sessions[handle], sandbox)
        self.assertEqual(sandbox.snapshot_operations, [])

        reference = await manager.end_session(handle)

        self.assertEqual(reference.snapshot_id, "snapshot-finalization-cancel")
        self.assertEqual(sandbox.snapshot_operations, [operation_id])
        self.assertEqual(sandbox.finalization_attempts, 2)
        self.assertEqual(manager.active_sessions, {})

    async def test_snapshot_commit_then_cancel_reconciles_without_replay(
        self,
    ) -> None:
        class CommitThenCancelSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.created_by_operation: dict[UUID, Any] = {}
                self.snapshot_operations: list[UUID] = []
                self.reconciled_operations: list[UUID] = []

            async def _prepare_snapshot_finalization(self) -> None:
                return None

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                self.snapshot_operations.append(operation_id)
                snapshot = _created_snapshot("snapshot-create-cancel")
                self.created_by_operation[operation_id] = snapshot
                raise asyncio.CancelledError

            async def _resolve_created_snapshot(
                self,
                operation_id: UUID,
            ) -> Any:
                self.reconciled_operations.append(operation_id)
                return self.created_by_operation.get(operation_id)

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])
        sandbox = CommitThenCancelSandbox()
        sandbox.current_user = user
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000061")
        )
        manager.active_sessions[handle] = sandbox

        with self.assertRaises(asyncio.CancelledError):
            await manager.end_session(handle)

        operation_id = manager._teardown_operations[handle].operation_id
        self.assertIs(manager.active_sessions[handle], sandbox)
        self.assertEqual(sandbox.snapshot_operations, [operation_id])
        self.assertEqual(sandbox.reconciled_operations, [operation_id])

        reference = await manager.end_session(handle)

        self.assertEqual(reference.snapshot_id, "snapshot-create-cancel")
        self.assertEqual(sandbox.snapshot_operations, [operation_id])
        self.assertEqual(manager.active_sessions, {})

    async def test_attestation_commit_then_cancel_reconciles_without_replay(
        self,
    ) -> None:
        class CommitThenCancelProvider(RecordingSnapshotBindingProvider):
            async def attest_create_if_absent(
                self,
                operation_id: UUID,
                snapshot: Any,
                repository: str,
                principal_id: str,
            ):
                await super().attest_create_if_absent(
                    operation_id,
                    snapshot,
                    repository,
                    principal_id,
                )
                raise asyncio.CancelledError

        class SnapshottingSandbox(RecordingSandbox):
            def __init__(self) -> None:
                super().__init__()
                self.snapshot_operations: list[UUID] = []

            async def _prepare_snapshot_finalization(self) -> None:
                return None

            async def _create_snapshot(self, operation_id: UUID) -> Any:
                self.snapshot_operations.append(operation_id)
                return _created_snapshot("snapshot-attest-cancel")

        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])
        manager.binding_provider = CommitThenCancelProvider()
        manager.snapshot_binding_provider = manager.binding_provider
        sandbox = SnapshottingSandbox()
        sandbox.current_user = user
        handle = SANDBOX_MANAGER.SessionHandle(
            UUID("00000000-0000-4000-8000-000000000062")
        )
        manager.active_sessions[handle] = sandbox

        with self.assertRaises(asyncio.CancelledError):
            await manager.end_session(handle)

        operation_id = manager._teardown_operations[handle].operation_id
        self.assertIs(manager.active_sessions[handle], sandbox)
        self.assertEqual(sandbox.snapshot_operations, [operation_id])
        self.assertEqual(
            manager.binding_provider.reconciled_operations,
            [operation_id],
        )

        reference = await manager.end_session(handle)

        self.assertEqual(reference.snapshot_id, "snapshot-attest-cancel")
        self.assertEqual(sandbox.snapshot_operations, [operation_id])
        self.assertEqual(
            manager.binding_provider.attestation_operations,
            [operation_id],
        )
        self.assertEqual(manager.active_sessions, {})

    async def test_predictive_warmup_requires_warm_prepare_receipt(self) -> None:
        user = SANDBOX_MANAGER.UserIdentity(
            id="operator",
            name="Operator",
            email="operator@example.com",
        )
        manager = self.TestManager(["owner/repository"])

        with self.assertRaisesRegex(
            SANDBOX_MANAGER.RepositoryAccessError,
            r"^Repository access denied\.$",
        ):
            await manager.on_user_typing(
                user,
                "owner/repository",
                authorization=self._receipt("operator", "owner/repository"),
            )


class ReferenceSecurityTests(unittest.TestCase):
    def test_reference_uses_argv_and_opaque_broker_patterns(self) -> None:
        reference = REFERENCE_PATH.read_text(encoding="utf-8")

        for forbidden in (
            "os.system(",
            "x-access-token:",
            "github_token",
            '"Authorization"',
            "sandbox.exec(f",
            'sandbox.exec("cd ',
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, reference)

        for required in (
            "validated argument vectors",
            "GIT_ASKPASS",
            "github_effect",
            "contains no bearer credential",
        ):
            with self.subTest(required=required):
                self.assertIn(required, reference)

    def test_skill_and_reference_forbid_raw_token_workflows(self) -> None:
        skill = SKILL_PATH.read_text(encoding="utf-8")
        reference = REFERENCE_PATH.read_text(encoding="utf-8")
        combined = f"{skill}\n{reference}"

        for forbidden in (
            "Generate GitHub app installation tokens",
            "Obtain user tokens for PR creation",
            "API uses user's GitHub token",
            "API creates PR using user token",
            "which operations use app tokens",
            "Implement token refresh logic",
            "github_token",
            "x-access-token:",
            "check=False",
            "blocked_commands",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, combined)

        for required in (
            "opaque",
            "short-lived",
            "credential broker",
            "preparatory",
        ):
            with self.subTest(required=required):
                self.assertIn(required, combined.casefold())

        self.assertNotIn("Architecture handles hundreds", skill)
        self.assertIn("unmeasured capacity target", skill)
        self.assertIn("origin allowlist", skill)
        self.assertIn("classification and redaction", skill)
        self.assertIn("user preview", skill)

    def test_reference_removes_unsafe_top_level_examples(self) -> None:
        reference = REFERENCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "modal.Sandbox.restore",
            ".pip_install(",
            "user_identity: dict",
            '"snapshot_id": snapshot_id',
            "class MetricsAggregator",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, reference)

        for required in (
            "authoritative snapshot-binding provider",
            "immutable image record",
            "snapshot reference is an untrusted",
            "numerator, denominator, sample size",
        ):
            with self.subTest(required=required):
                self.assertIn(required, reference)

    def test_slack_repository_choice_is_authenticated_and_authorized_first(
        self,
    ) -> None:
        reference = REFERENCE_PATH.read_text(encoding="utf-8")
        slack = reference.split("### Slack Bot with Repository Classification", 1)[1]
        slack = slack.split("### Chrome Extension DOM Extraction", 1)[0]

        authenticate = slack.index("authenticate_slack_user")
        authorize = slack.index("authorize_repository_access")
        start = slack.index("start_session(")
        self.assertLess(authenticate, authorize)
        self.assertLess(authorize, start)
        self.assertIn("if not access.allowed", slack[authorize:start])
        self.assertIn("authorization=access.receipt", slack[start:])

    def test_durable_object_boundary_is_fail_closed(self) -> None:
        reference = REFERENCE_PATH.read_text(encoding="utf-8")
        durable = reference.split(
            "### Cloudflare Durable Objects for Session State",
            1,
        )[1]
        durable = durable.split("### Real-Time Event Streaming", 1)[0]

        for required in (
            "authenticateRequest",
            "authorizeSessionAccess",
            "validateMessagePayload",
            "idempotencyKey",
            "allowedOrigins",
            "MAX_MESSAGE_BYTES",
            "classification",
            "canonical request digest",
            "pending intent",
            "outbox",
            "idempotency collision",
            "per connection",
        ):
            with self.subTest(required=required):
                self.assertIn(required, durable)

        self.assertNotIn("const { content, author } = await request.json()", durable)
        self.assertNotIn("data: event.data", reference)

        events = reference.split("### Real-Time Event Streaming", 1)[1]
        events = events.split("## Client Integration Patterns", 1)[0]
        for required in (
            "POST /internal/event",
            "authenticated service identity",
            "attested sandbox-to-session binding",
            "MAX_EVENT_BYTES",
            "classifyAndRedactEvent",
        ):
            with self.subTest(event_required=required):
                self.assertIn(required, events)

    def test_reference_removes_unsafe_copyable_client_and_multiplayer_snippets(
        self,
    ) -> None:
        reference = REFERENCE_PATH.read_text(encoding="utf-8")
        for forbidden in (
            "document.querySelectorAll",
            "class MultiplayerSession",
            "PromptContext:",
            "SLACK_BOT_TOKEN",
            "blocked_commands",
        ):
            with self.subTest(forbidden=forbidden):
                self.assertNotIn(forbidden, reference)

        for required in (
            "explicit user selection",
            "Bound traversal",
            "server-attested principal",
            "one mutation owner at a time",
            "request digest",
        ):
            with self.subTest(required=required):
                self.assertIn(required, reference)

    def test_reference_build_contract_blocks_unsafe_snapshot_finalization(self) -> None:
        reference = REFERENCE_PATH.read_text(encoding="utf-8")
        image_build = reference.split("### Image Build Pipeline", 1)[1]
        image_build = image_build.split("### Warm Pool Management", 1)[0]

        for required in (
            "assert_untrusted_build_boundary",
            "stop_and_reap_all",
            "assert_quiescent",
        ):
            self.assertIn(required, image_build)
        self.assertNotIn("check=False", image_build)
        self.assertNotIn("spawn_argv", image_build)

    def test_source_contains_no_dropped_warm_sync_or_indefinite_wait(self) -> None:
        source = MODULE_PATH.read_text(encoding="utf-8")
        self.assertNotIn("asyncio.create_task", source)
        self.assertNotIn("def _wait_for_sync", source)
        self.assertIn("asyncio.timeout", source)
        self.assertIn("async def prepare_snapshot_finalization(self)", source)
        self.assertIn("async def create_snapshot(self, operation_id: UUID)", source)
        self.assertIn("async def resolve_snapshot_creation(", source)


@contextlib.asynccontextmanager
async def _unused_credential_provider(
    repository: str,
    operation: str,
    argv_digest: str,
):
    yield SANDBOX_MANAGER.EphemeralGitCredential(
        lease_id=UUID("00000000-0000-4000-8000-000000000003"),
        repository=repository,
        operation=operation,
        host="github.com",
        argv_digest=argv_digest,
        audience=f"https://github.com/{repository}.git",
        git_config_scope="provider-owned-clean",
        egress_policy_digest=SANDBOX_MANAGER._GITHUB_EGRESS_POLICY_DIGEST,
    )


if __name__ == "__main__":
    unittest.main()
