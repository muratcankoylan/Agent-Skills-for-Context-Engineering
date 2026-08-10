from __future__ import annotations

import json
import os
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from datetime import UTC, datetime
from pathlib import Path
from unittest.mock import patch

from researcher.scripts import artifact_store as artifact_module
from researcher.scripts.artifact_store import (
    ArtifactAuthority,
    CandidateFreezer,
    EditableSurfacePolicy,
    FakeCapabilityProvider,
    LocalArtifactStore,
    LocalContentAddressedStore,
    grant_digest,
    snapshot_tree,
)
from researcher.scripts.migrate_legacy import current_legacy_records, migrate_record
from researcher.scripts.schema_contract import (
    ContractError,
    canonicalize,
    new_typed_id,
    sha256_bytes,
)


ROOT = Path(__file__).resolve().parents[3]
FIXTURES = ROOT / "researcher" / "schemas" / "fixtures" / "records"


class StoreTestCase(unittest.TestCase):
    def assert_code(self, code: str, callback) -> None:
        with self.assertRaises(ContractError) as captured:
            callback()
        self.assertEqual(captured.exception.code, code)

    def workspace(self) -> tuple[tempfile.TemporaryDirectory[str], Path]:
        temporary = tempfile.TemporaryDirectory()
        return temporary, Path(temporary.name)

    def authority(
        self,
        *resources: str,
        ceiling: str = "secret_reference",
        operations: tuple[str, ...] = ("artifact.read",),
    ) -> ArtifactAuthority:
        return ArtifactAuthority("test-reader", frozenset(operations), frozenset(resources), ceiling)

    def candidate_record(self, artifact_id: str | None = None) -> dict:
        record = json.loads((FIXTURES / "candidate-artifact.json").read_text(encoding="utf-8"))
        record["id"] = artifact_id or new_typed_id("cand")
        return record

    def editable_policy(self, *, roots: tuple[str, ...] = ("skills",)) -> EditableSurfacePolicy:
        if roots == ("skills",):
            fixture = json.loads(
                (FIXTURES.parent / "editable-surface-policy-v1.json").read_text(encoding="utf-8")
            )
            return EditableSurfacePolicy(
                policy_id=fixture["policy_id"],
                roots_by_surface={item["name"]: item["roots"] for item in fixture["surfaces"]},
                locked_paths=fixture["locked_paths"],
            )
        return EditableSurfacePolicy(
            policy_id="test-editable-surfaces-v1",
            roots_by_surface={"skill-body": roots},
            locked_paths=("skills/locked",),
        )


class ContentAddressedStoreTests(StoreTestCase):
    def test_exact_bytes_and_permissions_are_preserved(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalContentAddressedStore(root / "cas")
        lf = store.put_bytes(b"line\n", classification="private_operational")
        crlf = store.put_bytes(b"line\r\n", classification="private_operational")
        self.assertNotEqual(lf.digest, crlf.digest)
        self.assertEqual(store.get_bytes(lf.digest, self.authority(lf.digest)), b"line\n")
        blob = store.root / lf.locator
        self.assertEqual(blob.stat().st_mode & 0o777, 0o600)

    def test_concurrent_same_body_put_is_idempotent(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalContentAddressedStore(root / "cas")

        def put(_: int):
            return store.put_bytes(b"concurrent", classification="private_operational")

        with ThreadPoolExecutor(max_workers=12) as executor:
            results = list(executor.map(put, range(40)))
        self.assertEqual(len({result.digest for result in results}), 1)
        blobs = [path for path in (store.root / "sha256").rglob("*") if path.is_file()]
        self.assertEqual(len(blobs), 1)

    def test_expected_digest_mismatch_writes_nothing(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalContentAddressedStore(root / "cas")
        self.assert_code(
            "DIGEST_MISMATCH",
            lambda: store.put_bytes(
                b"body", classification="private_operational", expected_digest="sha256:" + "0" * 64
            ),
        )
        self.assertEqual([path for path in (store.root / "sha256").rglob("*") if path.is_file()], [])

    def test_classification_can_raise_but_not_drop(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalContentAddressedStore(root / "cas")
        store.put_bytes(b"same", classification="private_operational")
        store.put_bytes(b"same", classification="restricted_source")
        self.assert_code(
            "CLASSIFICATION_DOWNGRADE",
            lambda: store.put_bytes(b"same", classification="public"),
        )

    def test_digest_classification_high_water_mark_controls_all_reads(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalContentAddressedStore(root / "cas")
        reference = store.put_bytes(b"shared", classification="public")
        public_reader = self.authority(reference.digest, ceiling="public")
        self.assertEqual(store.get_bytes(reference.digest, public_reader), b"shared")
        store.put_bytes(b"shared", classification="restricted_source")
        self.assert_code("ACCESS_DENIED", lambda: store.get_bytes(reference.digest, public_reader))

    def test_existing_object_tampering_is_detected(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalContentAddressedStore(root / "cas")
        reference = store.put_bytes(b"original", classification="private_operational")
        (store.root / reference.locator).write_bytes(b"tampered")
        self.assert_code(
            "DIGEST_MISMATCH",
            lambda: store.verify(reference.digest, self.authority(reference.digest)),
        )

    def test_failed_publish_leaves_no_partial_readable_object(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalContentAddressedStore(root / "cas")
        with patch("researcher.scripts.artifact_store.os.link", side_effect=OSError("injected")):
            with self.assertRaises(OSError):
                store.put_bytes(b"crash-window", classification="private_operational")
        self.assertEqual([path for path in (store.root / "sha256").rglob("*") if path.is_file()], [])
        self.assertEqual(list((store.root / "metadata").glob("*.json")), [])

    def test_authority_is_checked_before_existence(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalContentAddressedStore(root / "cas")
        reference = store.put_bytes(b"private", classification="restricted_source")
        denied = self.authority(operations=())
        for digest in (reference.digest, "sha256:" + "f" * 64):
            with self.subTest(digest=digest):
                self.assert_code("ACCESS_DENIED", lambda digest=digest: store.get_bytes(digest, denied))
                self.assert_code("ACCESS_DENIED", lambda digest=digest: store.verify(digest, denied))
        self.assert_code(
            "ARTIFACT_UNAVAILABLE",
            lambda: store.get_bytes("sha256:" + "f" * 64, self.authority("sha256:" + "f" * 64)),
        )

    def test_classification_ceiling_is_enforced(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalContentAddressedStore(root / "cas")
        reference = store.put_bytes(b"restricted", classification="restricted_source")
        self.assert_code(
            "ACCESS_DENIED",
            lambda: store.get_bytes(
                reference.digest,
                self.authority(reference.digest, ceiling="private_operational"),
            ),
        )


class ArtifactStoreTests(StoreTestCase):
    def test_reference_has_no_locator_and_binding_is_private(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalArtifactStore(root / "artifacts")
        artifact_id = new_typed_id("cand")
        body = canonicalize(self.candidate_record(artifact_id))
        reference = store.put(
            artifact_id=artifact_id,
            artifact_kind="CandidateArtifact",
            artifact_schema_version="1.0.0",
            body=body,
            media_type="application/json",
            classification="private_operational",
            created_by="skill_builder",
            created_at="2026-08-10T12:00:00Z",
        )
        self.assertNotIn("locator", reference)
        self.assertNotIn("storage_binding", reference)
        binding_files = list(store.bindings.glob("*.json"))
        self.assertEqual(len(binding_files), 1)
        self.assertIn("sha256/", binding_files[0].read_text(encoding="utf-8"))
        authority = self.authority(artifact_id)
        self.assertEqual(store.get(artifact_id, authority), body)
        self.assertEqual(store.verify(artifact_id, authority)["result"], "verified")
        binding = json.loads(binding_files[0].read_text(encoding="utf-8"))
        (store.cas.root / binding["locator"]).unlink()
        self.assert_code("ARTIFACT_UNAVAILABLE", lambda: store.head(artifact_id, authority))

    def test_artifact_identifier_is_immutable(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalArtifactStore(root / "artifacts")
        artifact_id = new_typed_id("cand")
        first_record = self.candidate_record(artifact_id)
        arguments = dict(
            artifact_id=artifact_id,
            artifact_kind="CandidateArtifact",
            artifact_schema_version="1.0.0",
            media_type="application/json",
            classification="private_operational",
            created_by="skill_builder",
            created_at="2026-08-10T12:00:00Z",
        )
        store.put(body=canonicalize(first_record), **arguments)
        second_record = {**first_record, "causal_hypothesis_ref": "second"}
        self.assert_code(
            "IMMUTABLE_ID_CONFLICT",
            lambda: store.put(body=canonicalize(second_record), **arguments),
        )
        public_record = {**first_record, "classification": "public"}
        changed_classification = {**arguments, "classification": "public"}
        self.assert_code(
            "IMMUTABLE_ID_CONFLICT",
            lambda: store.put(body=canonicalize(public_record), **changed_classification),
        )

    def test_declared_legacy_import_identity_uses_uuid5(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        kind, source_path, legacy, _, _ = current_legacy_records()[0]
        self.assertIsNotNone(legacy)
        envelope = migrate_record(kind, legacy, source_path=source_path)
        body = canonicalize(envelope)
        store = LocalArtifactStore(root / "artifacts")
        reference = store.put(
            artifact_id=envelope["id"],
            artifact_kind="ArtifactEnvelope",
            artifact_schema_version="1.0.0",
            body=body,
            media_type="application/json",
            classification="public",
            created_by="legacy_adapter",
            created_at=envelope["created_at"],
        )
        self.assertEqual(reference["artifact_id_origin"], "legacy_import")
        self.assertEqual(store.get(envelope["id"], self.authority(envelope["id"], ceiling="public")), body)

    def test_materialization_is_fresh_and_verified(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalArtifactStore(root / "artifacts")
        artifact_id = new_typed_id("cand")
        body = canonicalize(self.candidate_record(artifact_id))
        store.put(
            artifact_id=artifact_id,
            artifact_kind="CandidateArtifact",
            artifact_schema_version="1.0.0",
            body=body,
            media_type="application/json",
            classification="private_operational",
            created_by="skill_builder",
            created_at="2026-08-10T12:00:00Z",
        )
        destination = root / "out/body.bin"
        destination.parent.mkdir()
        os.chmod(destination.parent, 0o755)
        receipt = store.materialize(artifact_id, destination, self.authority(artifact_id))
        self.assertEqual(receipt["result"], "materialized")
        self.assertEqual(destination.read_bytes(), body)
        self.assertEqual(destination.parent.stat().st_mode & 0o777, 0o755)
        self.assert_code(
            "OUTPUT_EXISTS",
            lambda: store.materialize(artifact_id, destination, self.authority(artifact_id)),
        )

    def test_declared_identity_and_registered_body_are_enforced_before_write(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalArtifactStore(root / "artifacts")
        artifact_id = new_typed_id("cand")
        record = self.candidate_record(artifact_id)
        common = dict(
            artifact_id=artifact_id,
            artifact_kind="CandidateArtifact",
            artifact_schema_version="1.0.0",
            media_type="application/json",
            classification="private_operational",
            created_by="skill_builder",
            created_at="2026-08-10T12:00:00Z",
        )
        mismatched = {**record, "id": new_typed_id("cand")}
        self.assert_code(
            "ARTIFACT_IDENTITY_MISMATCH",
            lambda: store.put(body=canonicalize(mismatched), **common),
        )
        self.assert_code(
            "PREFIX_KIND_MISMATCH",
            lambda: store.put(body=canonicalize(record), **{**common, "artifact_id": new_typed_id("rec")}),
        )
        self.assert_code(
            "UNKNOWN_KIND",
            lambda: store.put(body=canonicalize(record), **{**common, "artifact_kind": "Unknown"}),
        )
        self.assertEqual(list((store.cas.root / "sha256").rglob("*")), [])

    def test_missing_or_mismatched_binding_fails_closed(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalArtifactStore(root / "artifacts")
        artifact_id = new_typed_id("cand")
        body = canonicalize(self.candidate_record(artifact_id))
        reference = store.put(
            artifact_id=artifact_id,
            artifact_kind="CandidateArtifact",
            artifact_schema_version="1.0.0",
            body=body,
            media_type="application/json",
            classification="private_operational",
            created_by="skill_builder",
            created_at="2026-08-10T12:00:00Z",
        )
        ref_path, binding_path = store._record_paths(artifact_id)
        tampered_reference = {**reference, "artifact_id": new_typed_id("cand")}
        ref_path.write_bytes(canonicalize(tampered_reference) + b"\n")
        self.assert_code(
            "ARTIFACT_IDENTITY_MISMATCH",
            lambda: store.head(artifact_id, self.authority(artifact_id)),
        )
        ref_path.write_bytes(canonicalize(reference) + b"\n")
        binding = json.loads(binding_path.read_text(encoding="utf-8"))
        binding["artifact_ref_id"] = new_typed_id("aref")
        binding_path.write_bytes(canonicalize(binding) + b"\n")
        self.assert_code("BINDING_MISMATCH", lambda: store.head(artifact_id, self.authority(artifact_id)))
        binding_path.unlink()
        self.assert_code("STORE_CORRUPT", lambda: store.get(artifact_id, self.authority(artifact_id)))
        self.assertEqual(reference["artifact_id"], artifact_id)

    def test_non_available_reference_is_inspectable_but_not_readable(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        store = LocalArtifactStore(root / "artifacts")
        artifact_id = new_typed_id("cand")
        body = canonicalize(self.candidate_record(artifact_id))
        arguments = {
            "artifact_id": artifact_id,
            "artifact_kind": "CandidateArtifact",
            "artifact_schema_version": "1.0.0",
            "body": body,
            "media_type": "application/json",
            "classification": "private_operational",
            "created_by": "skill_builder",
            "created_at": "2026-08-10T12:00:00Z",
        }
        reference = store.put(**arguments)
        ref_path, _ = store._record_paths(artifact_id)
        unavailable = {**reference, "availability": "tombstoned"}
        ref_path.write_bytes(canonicalize(unavailable) + b"\n")
        authority = self.authority(artifact_id)

        self.assertEqual(store.head(artifact_id, authority)["availability"], "tombstoned")
        self.assert_code("ARTIFACT_UNAVAILABLE", lambda: store.get(artifact_id, authority))
        self.assert_code("ARTIFACT_UNAVAILABLE", lambda: store.verify(artifact_id, authority))
        self.assert_code(
            "ARTIFACT_UNAVAILABLE",
            lambda: store.materialize(artifact_id, root / "out/body.json", authority),
        )
        self.assert_code("ARTIFACT_UNAVAILABLE", lambda: store.put(**arguments))

        unavailable = {**reference, "availability": "unavailable"}
        ref_path.write_bytes(canonicalize(unavailable) + b"\n")
        store.cas._blob_path(reference["digest"]).unlink()
        self.assertEqual(store.head(artifact_id, authority)["availability"], "unavailable")
        self.assert_code("ARTIFACT_UNAVAILABLE", lambda: store.get(artifact_id, authority))
        self.assert_code("ARTIFACT_UNAVAILABLE", lambda: store.verify(artifact_id, authority))
        self.assert_code("ARTIFACT_UNAVAILABLE", lambda: store.put(**arguments))


class CandidateFreezeTests(StoreTestCase):
    def candidate(self, digest: str, *, candidate_id: str | None = None) -> dict:
        record = json.loads((FIXTURES / "candidate-artifact.json").read_text(encoding="utf-8"))
        record["id"] = candidate_id or new_typed_id("cand")
        record["draft_tree_digest"] = digest
        return record

    def test_tree_digest_is_order_independent_but_mode_and_bytes_sensitive(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        first = root / "first"
        second = root / "second"
        first.mkdir()
        second.mkdir()
        (first / "b.txt").write_bytes(b"b\n")
        (first / "a.txt").write_bytes(b"a\n")
        (second / "a.txt").write_bytes(b"a\n")
        (second / "b.txt").write_bytes(b"b\n")
        _, digest_first = snapshot_tree(first)
        _, digest_second = snapshot_tree(second)
        self.assertEqual(digest_first, digest_second)
        os.chmod(second / "b.txt", 0o700)
        _, executable_digest = snapshot_tree(second)
        self.assertNotEqual(digest_first, executable_digest)
        os.chmod(second / "b.txt", 0o600)
        (second / "b.txt").write_bytes(b"b\r\n")
        _, crlf_digest = snapshot_tree(second)
        self.assertNotEqual(digest_first, crlf_digest)

    def test_golden_receipt_binds_current_registry_and_editable_policy(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        receipt = json.loads((FIXTURES / "freeze-receipt.json").read_text(encoding="utf-8"))
        freezer = CandidateFreezer(
            LocalContentAddressedStore(root / "cas"),
            editable_surface_policy=self.editable_policy(),
        )
        self.assertEqual(receipt["freeze_policy_digest"], freezer.freeze_policy_digest)
        self.assertEqual(receipt["schema_registry_digest"], sha256_bytes(freezer.registry.path.read_bytes()))

    def test_freeze_is_idempotent_and_materializes_exact_tree(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        draft = root / "draft"
        target = draft / "skills/context-fundamentals/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"frozen\n")
        os.chmod(target, 0o700)
        _, digest = snapshot_tree(draft)
        store = LocalContentAddressedStore(root / "cas")
        freezer = CandidateFreezer(store, editable_surface_policy=self.editable_policy())
        candidate = self.candidate(digest)
        receipt = freezer.freeze(
            candidate, draft, expected_draft_digest=digest, frozen_at="2026-08-10T12:00:00Z"
        )
        repeated = freezer.freeze(candidate, draft, expected_draft_digest=digest)
        self.assertEqual(receipt, repeated)
        metadata_mutation = {**candidate, "causal_hypothesis_ref": "different-hypothesis"}
        self.assert_code(
            "FROZEN_CANDIDATE_CONFLICT",
            lambda: freezer.freeze(metadata_mutation, draft, expected_draft_digest=digest),
        )
        destination = root / "materialized"
        result = freezer.materialize(
            receipt,
            destination,
            self.authority(candidate["id"], ceiling="secret_reference"),
        )
        self.assertEqual(result["tree_digest"], digest)
        materialized = destination / "skills/context-fundamentals/SKILL.md"
        self.assertEqual(materialized.read_bytes(), b"frozen\n")
        self.assertTrue(materialized.stat().st_mode & 0o100)
        store._blob_path(receipt["entries"][0]["digest"]).write_bytes(b"tampered")
        self.assert_code(
            "DIGEST_MISMATCH",
            lambda: freezer.freeze(candidate, draft, expected_draft_digest=digest),
        )

    def test_changed_draft_and_reused_candidate_id_fail(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        draft = root / "draft"
        target = draft / "skills/context-fundamentals/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"one")
        _, first_digest = snapshot_tree(draft)
        store = LocalContentAddressedStore(root / "cas")
        freezer = CandidateFreezer(store, editable_surface_policy=self.editable_policy())
        candidate = self.candidate(first_digest)
        freezer.freeze(candidate, draft, expected_draft_digest=first_digest)
        target.write_bytes(b"two")
        _, second_digest = snapshot_tree(draft)
        revised_same_id = self.candidate(second_digest, candidate_id=candidate["id"])
        self.assert_code(
            "FROZEN_CANDIDATE_CONFLICT",
            lambda: freezer.freeze(revised_same_id, draft, expected_draft_digest=second_digest),
        )

    def test_source_change_after_expected_digest_fails(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        draft = root / "draft"
        target = draft / "skills/context-fundamentals/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"one")
        _, digest = snapshot_tree(draft)
        candidate = self.candidate(digest)
        target.write_bytes(b"two")
        freezer = CandidateFreezer(
            LocalContentAddressedStore(root / "cas"),
            editable_surface_policy=self.editable_policy(),
        )
        self.assert_code(
            "DRAFT_CHANGED",
            lambda: freezer.freeze(candidate, draft, expected_draft_digest=digest),
        )

    def test_symlink_hardlink_nfd_and_case_collisions_fail(self) -> None:
        for scenario in ("symlink", "hardlink", "nfd", "case"):
            with self.subTest(scenario=scenario):
                temporary, root = self.workspace()
                self.addCleanup(temporary.cleanup)
                draft = root / "draft"
                draft.mkdir()
                original = draft / "base.txt"
                original.write_bytes(b"body")
                if scenario == "symlink":
                    (draft / "link.txt").symlink_to(original)
                    expected = "UNSUPPORTED_CANDIDATE_ENTRY"
                elif scenario == "hardlink":
                    os.link(original, draft / "hard.txt")
                    expected = "UNSUPPORTED_CANDIDATE_ENTRY"
                elif scenario == "nfd":
                    (draft / "e\u0301.txt").write_bytes(b"nfd")
                    expected = "INVALID_CANDIDATE_PATH"
                else:
                    (draft / "BASE.TXT").write_bytes(b"collision")
                    expected = "CANDIDATE_PATH_COLLISION"
                    if (draft / "BASE.TXT").samefile(original):
                        # Default macOS volumes collapse the two names before
                        # the validator can observe a distinct collision. The
                        # same fixture exercises the denial on case-sensitive CI.
                        continue
                self.assert_code(expected, lambda draft=draft: snapshot_tree(draft))

    def test_directory_collisions_and_tree_limits_fail_closed(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        draft = root / "draft"
        draft.mkdir()
        lower = draft / "docs"
        upper = draft / "DOCS"
        lower.mkdir()
        upper.mkdir(exist_ok=True)
        if not lower.samefile(upper):
            self.assert_code("CANDIDATE_PATH_COLLISION", lambda: snapshot_tree(draft))

        limited = root / "limited"
        limited.mkdir()
        (limited / "a").write_bytes(b"a")
        (limited / "b").write_bytes(b"b")
        self.assert_code(
            "CANDIDATE_TOO_LARGE",
            lambda: snapshot_tree(limited, maximum_tree_files=1),
        )
        self.assert_code(
            "CANDIDATE_TOO_LARGE",
            lambda: snapshot_tree(limited, maximum_tree_bytes=1),
        )

    def test_mutation_between_tree_passes_is_detected(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        draft = root / "draft"
        draft.mkdir()
        target = draft / "file.txt"
        target.write_bytes(b"before")
        original_read = artifact_module._stable_file_read
        calls = 0

        def mutate_after_first(path: Path, maximum: int):
            nonlocal calls
            result = original_read(path, maximum)
            calls += 1
            if calls == 1:
                path.write_bytes(b"after!")
            return result

        with patch.object(artifact_module, "_stable_file_read", side_effect=mutate_after_first):
            self.assert_code("CANDIDATE_MUTATED", lambda: snapshot_tree(draft))

    def test_traversal_error_and_lstat_open_swap_fail_closed(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        draft = root / "draft"
        draft.mkdir()
        target = draft / "file.txt"
        target.write_bytes(b"before")

        def unreadable_walk(*args, **kwargs):
            kwargs["onerror"](PermissionError("injected"))
            return iter(())

        with patch.object(artifact_module.os, "walk", side_effect=unreadable_walk):
            self.assert_code("CANDIDATE_UNREADABLE", lambda: snapshot_tree(draft))

        original_open = artifact_module.os.open
        swapped = False

        def swap_before_open(path, flags, *args, **kwargs):
            nonlocal swapped
            if Path(path) == target and not swapped:
                replacement = draft / "replacement.txt"
                replacement.write_bytes(b"after!")
                os.replace(replacement, target)
                swapped = True
            return original_open(path, flags, *args, **kwargs)

        with patch.object(artifact_module.os, "open", side_effect=swap_before_open):
            self.assert_code("CANDIDATE_MUTATED", lambda: artifact_module._stable_file_read(target, 1024))

    def test_editable_surface_policy_rejects_undeclared_and_locked_paths(self) -> None:
        temporary, root = self.workspace()
        self.addCleanup(temporary.cleanup)
        draft = root / "draft"
        target = draft / "skills/context-fundamentals/SKILL.md"
        target.parent.mkdir(parents=True)
        target.write_bytes(b"body")
        extra = draft / "skills/other/SKILL.md"
        extra.parent.mkdir(parents=True)
        extra.write_bytes(b"extra")
        _, digest = snapshot_tree(draft)
        candidate = self.candidate(digest)
        freezer = CandidateFreezer(
            LocalContentAddressedStore(root / "cas"),
            editable_surface_policy=self.editable_policy(),
        )
        self.assert_code(
            "DECLARED_SURFACE_MISMATCH",
            lambda: freezer.freeze(candidate, draft, expected_draft_digest=digest),
        )

        extra.unlink()
        locked = draft / "skills/locked/SKILL.md"
        locked.parent.mkdir(parents=True)
        target.unlink()
        locked.write_bytes(b"locked")
        _, locked_digest = snapshot_tree(draft)
        locked_candidate = self.candidate(locked_digest)
        locked_candidate["declared_changed_surfaces"] = ["skills/locked/SKILL.md"]
        self.assert_code(
            "EDITABLE_SURFACE_DENIED",
            lambda: freezer.freeze(locked_candidate, draft, expected_draft_digest=locked_digest),
        )

    def test_editable_surface_policy_rejects_noncanonical_configuration(self) -> None:
        self.assert_code(
            "EDITABLE_POLICY_INVALID",
            lambda: EditableSurfacePolicy(
                policy_id="bad-roots",
                roots_by_surface={"skill-body": "skills"},
            ),
        )
        self.assert_code(
            "INVALID_CANDIDATE_PATH",
            lambda: EditableSurfacePolicy(
                policy_id="bad-path",
                roots_by_surface={"skill-body": ("skills//nested",)},
            ),
        )


class CapabilityTests(StoreTestCase):
    def records(self) -> tuple[dict, dict, datetime]:
        credential = json.loads((FIXTURES / "credential-ref.json").read_text(encoding="utf-8"))
        grant = json.loads((FIXTURES / "capability-grant-spec.json").read_text(encoding="utf-8"))
        now = datetime(2026, 8, 10, 12, 10, tzinfo=UTC)
        grant["grant_digest"] = grant_digest(grant)
        return credential, grant, now

    def issue(self):
        credential, grant, now = self.records()
        provider = FakeCapabilityProvider(
            {credential["id"]: "fake-secret-value"},
            resource_classifications={grant["resources"][0]: "private_operational"},
        )
        token = provider.issue(grant, credential, audience="github-adapter", now=now)
        return provider, token, credential, grant, now

    def test_grant_and_reference_serialize_without_credential_value(self) -> None:
        credential, grant, _ = self.records()
        body = json.dumps({"credential": credential, "grant": grant}, sort_keys=True)
        self.assertNotIn("fake-secret-value", body)
        self.assertNotIn("storage_locator", body)
        self.assertNotIn("cap_", body)

    def test_one_use_capability_resolves_to_redacted_lease(self) -> None:
        provider, token, credential, grant, now = self.issue()
        lease = provider.resolve(
            token,
            audience="github-adapter",
            operation="github.open_pr",
            resource=grant["resources"][0],
            work_order_id=grant["work_order_id"],
            attempt_id=grant["attempt_id"],
            now=now,
        )
        self.assertNotIn("fake-secret-value", repr(lease))
        self.assertEqual(lease.value_for_adapter(), "fake-secret-value")
        self.assert_code(
            "CAPABILITY_INVALID",
            lambda: provider.resolve(
                token,
                audience="github-adapter",
                operation="github.open_pr",
                resource=grant["resources"][0],
                work_order_id=grant["work_order_id"],
                attempt_id=grant["attempt_id"],
                now=now,
            ),
        )

    def test_wrong_audience_operation_resource_attempt_and_expiry_fail(self) -> None:
        scenarios = [
            ("audience", "wrong", "AUDIENCE_MISMATCH"),
            ("operation", "github.merge_pr", "OPERATION_DENIED"),
            ("resource", "repo:other/project", "RESOURCE_DENIED"),
            ("work_order_id", "other-work", "WORK_ORDER_MISMATCH"),
            ("attempt_id", "other-attempt", "ATTEMPT_MISMATCH"),
            ("now", datetime(2026, 8, 10, 14, 0, tzinfo=UTC), "CAPABILITY_EXPIRED"),
        ]
        for field, value, code in scenarios:
            with self.subTest(field=field):
                provider, token, _, grant, now = self.issue()
                arguments = {
                    "audience": "github-adapter",
                    "operation": "github.open_pr",
                    "resource": grant["resources"][0],
                    "work_order_id": grant["work_order_id"],
                    "attempt_id": grant["attempt_id"],
                    "now": now,
                }
                arguments[field] = value
                self.assert_code(code, lambda: provider.resolve(token, **arguments))

    def test_issue_rejects_expired_or_tampered_grants(self) -> None:
        credential, grant, now = self.records()
        provider = FakeCapabilityProvider(
            {credential["id"]: "fake-secret-value"},
            resource_classifications={grant["resources"][0]: "private_operational"},
        )
        grant["actor_id"] = "tampered"
        self.assert_code(
            "GRANT_DIGEST_MISMATCH",
            lambda: provider.issue(grant, credential, audience="github-adapter", now=now),
        )
        credential, grant, now = self.records()
        grant["expires_at"] = "2026-08-10T12:05:00Z"
        grant["grant_digest"] = grant_digest(grant)
        self.assert_code(
            "CAPABILITY_EXPIRED",
            lambda: provider.issue(grant, credential, audience="github-adapter", now=now),
        )

    def test_resource_classification_is_authoritative_provider_state(self) -> None:
        credential, grant, now = self.records()
        resource = grant["resources"][0]
        provider = FakeCapabilityProvider(
            {credential["id"]: "fake-secret-value"},
            resource_classifications={resource: "restricted_source"},
        )
        token = provider.issue(grant, credential, audience="github-adapter", now=now)
        self.assert_code(
            "CLASSIFICATION_DENIED",
            lambda: provider.resolve(
                token,
                audience="github-adapter",
                operation="github.open_pr",
                resource=resource,
                work_order_id=grant["work_order_id"],
                attempt_id=grant["attempt_id"],
                now=now,
            ),
        )

        missing = FakeCapabilityProvider(
            {credential["id"]: "fake-secret-value"},
            resource_classifications={},
        )
        self.assert_code(
            "RESOURCE_UNAVAILABLE",
            lambda: missing.issue(grant, credential, audience="github-adapter", now=now),
        )

    def test_provider_rejects_ambiguous_time_and_invalid_authority_maps(self) -> None:
        credential, grant, _ = self.records()
        provider = FakeCapabilityProvider(
            {credential["id"]: "fake-secret-value"},
            resource_classifications={grant["resources"][0]: "private_operational"},
        )
        self.assert_code(
            "INVALID_TIME",
            lambda: provider.issue(
                grant,
                credential,
                audience="github-adapter",
                now=datetime(2026, 8, 10, 12, 10),
            ),
        )
        self.assert_code(
            "CAPABILITY_PROVIDER_INVALID",
            lambda: FakeCapabilityProvider(
                {credential["id"]: "fake-secret-value"},
                resource_classifications={"": "private_operational"},
            ),
        )


if __name__ == "__main__":
    unittest.main()
