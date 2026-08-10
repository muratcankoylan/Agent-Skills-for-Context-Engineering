from __future__ import annotations

import json
import tempfile
import unittest
import uuid
from pathlib import Path
from unittest.mock import patch

from researcher.scripts.schema_contract import (
    CANONICALIZATION_PROFILE,
    ContractError,
    SchemaRegistry,
    UUID7Generator,
    canonical_digest,
    canonicalize,
    deterministic_import_id,
    new_typed_id,
    parse_json_strict,
    sha256_bytes,
    uuid7_timestamp_ms,
    validate_typed_id,
)
from researcher.scripts.migrate_legacy import (
    _read_jsonl,
    current_legacy_records,
    legacy_records_from_manifest,
    migrate_record,
    migration_report,
    rollback_envelope,
)


ROOT = Path(__file__).resolve().parents[3]
SCHEMAS = ROOT / "researcher" / "schemas"


class ContractTestCase(unittest.TestCase):
    def assert_code(self, code: str, callback) -> None:
        with self.assertRaises(ContractError) as captured:
            callback()
        self.assertEqual(captured.exception.code, code)


class CanonicalizationTests(ContractTestCase):
    def test_committed_cross_language_vectors(self) -> None:
        suite = json.loads((SCHEMAS / "fixtures/canonicalization-v1.json").read_text(encoding="utf-8"))
        self.assertEqual(suite["profile"], CANONICALIZATION_PROFILE)
        for case in suite["cases"]:
            with self.subTest(case=case["id"]):
                if not case["valid"]:
                    self.assert_code(
                        case["expected_code"],
                        lambda case=case: canonicalize(parse_json_strict(case["input_json"])),
                    )
                    continue
                body = canonicalize(parse_json_strict(case["input_json"]))
                self.assertEqual(body.decode("utf-8"), case["expected_canonical"])
                self.assertEqual(sha256_bytes(body), case["expected_digest"])

    def test_object_order_and_whitespace_do_not_change_digest(self) -> None:
        left = parse_json_strict('{"b": [true, null], "a": 1}')
        right = parse_json_strict('{\n  "a": 1, "b": [true,null]}')
        self.assertEqual(canonical_digest(left), canonical_digest(right))

    def test_blob_digest_preserves_line_endings(self) -> None:
        self.assertNotEqual(sha256_bytes(b"line\n"), sha256_bytes(b"line\r\n"))

    def test_integrity_digest_excludes_only_digest_field(self) -> None:
        left = {"payload": {"x": 1}, "integrity": {"algorithm": "sha256", "digest": "old"}}
        right = {"payload": {"x": 1}, "integrity": {"algorithm": "sha256", "digest": "new"}}
        changed = {"payload": {"x": 2}, "integrity": {"algorithm": "sha256", "digest": "old"}}
        self.assertEqual(
            canonical_digest(left, exclude_integrity_digest=True),
            canonical_digest(right, exclude_integrity_digest=True),
        )
        self.assertNotEqual(
            canonical_digest(left, exclude_integrity_digest=True),
            canonical_digest(changed, exclude_integrity_digest=True),
        )

    def test_unsupported_runtime_values_fail(self) -> None:
        self.assert_code("UNSAFE_NUMBER", lambda: canonicalize({"value": 1.2}))
        self.assert_code("UNSAFE_NUMBER", lambda: canonicalize({"value": 2**53}))
        self.assert_code("INVALID_JSON", lambda: canonicalize({1: "not a JSON object"}))


class IdentifierTests(ContractTestCase):
    def test_uuid7_is_monotonic_under_clock_regression(self) -> None:
        clocks = iter([1000, 1000, 999, 1001])
        generator = UUID7Generator(clock_ms=lambda: next(clocks), random_bits=lambda _: 5)
        values = [generator.new() for _ in range(4)]
        self.assertEqual(values, sorted(values))
        self.assertEqual([value.version for value in values], [7, 7, 7, 7])
        self.assertEqual([uuid7_timestamp_ms(value) for value in values], [1000, 1000, 1000, 1001])

    def test_large_uuid7_batch_is_unique_and_sorted(self) -> None:
        generator = UUID7Generator(clock_ms=lambda: 123456789, random_bits=lambda _: 100)
        values = [generator.new() for _ in range(5000)]
        self.assertEqual(len(set(values)), len(values))
        self.assertEqual(values, sorted(values))

    def test_typed_id_prefix_and_version_are_enforced(self) -> None:
        value = new_typed_id("cand", generator=UUID7Generator(clock_ms=lambda: 1, random_bits=lambda _: 1))
        validate_typed_id(value, expected_prefix="cand")
        self.assert_code(
            "PREFIX_KIND_MISMATCH", lambda: validate_typed_id(value, expected_prefix="freeze")
        )

    def test_legacy_import_ids_are_deterministic_uuid5(self) -> None:
        namespace = uuid.UUID("5ea9f7a6-8f4e-4d37-a6f8-c9f4d5c22c90")
        first = deterministic_import_id("rec", namespace, "LegacyClaim:claim-example")
        second = deterministic_import_id("rec", namespace, "LegacyClaim:claim-example")
        self.assertEqual(first, second)
        validate_typed_id(first, expected_prefix="rec", id_origin="legacy_import")
        self.assert_code("INVALID_ID", lambda: validate_typed_id(first, expected_prefix="rec"))


class RegistryTests(ContractTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = SchemaRegistry.load()

    def test_bootstrap_registry_is_reduced_and_digest_pinned(self) -> None:
        kinds = {entry.kind for entry in self.registry.entries}
        self.assertEqual(len(self.registry.entries), 20)
        self.assertIn("ArtifactEnvelope", kinds)
        self.assertIn("CandidateArtifact", kinds)
        self.assertNotIn("Event", kinds)
        self.assertNotIn("WorkOrder", kinds)
        self.assertNotIn("EvaluationObservation", kinds)
        self.assertNotIn("ContextPackage", kinds)

    def test_all_registered_goldens_validate(self) -> None:
        for entry in self.registry.entries:
            for path in entry.golden_paths:
                with self.subTest(kind=entry.kind, path=path.name):
                    record = parse_json_strict(path.read_text(encoding="utf-8"))
                    self.registry.validate(record, kind=entry.kind, version=entry.version)

    def test_unknown_kind_and_version_are_typed_failures(self) -> None:
        self.assert_code("UNKNOWN_KIND", lambda: self.registry.resolve("UnknownThing", "1.0.0"))
        self.assert_code(
            "UNSUPPORTED_MAJOR", lambda: self.registry.resolve("ArtifactRef", "2.0.0")
        )

    def test_read_and_write_resolution_enforce_lifecycle(self) -> None:
        document = json.loads((SCHEMAS / "registry.json").read_text(encoding="utf-8"))
        artifact_ref = next(entry for entry in document["entries"] if entry["kind"] == "ArtifactRef")
        artifact_ref["status"] = "deprecated"
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            registry = SchemaRegistry.load(path)
            self.assertEqual(registry.resolve_for_read("ArtifactRef", "1.0.0").status, "deprecated")
            self.assert_code(
                "SCHEMA_INACTIVE",
                lambda: registry.resolve_for_write("ArtifactRef", "1.0.0"),
            )

        duplicate = dict(artifact_ref)
        duplicate["status"] = "active"
        duplicate["version"] = "1.0.1"
        duplicate.pop("id_prefix")
        artifact_ref["status"] = "active"
        document["entries"].append(duplicate)
        document["entries"].sort(key=lambda entry: (entry["kind"], entry["version"]))
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            self.assert_code("REGISTRY_INVALID", lambda: SchemaRegistry.load(path))

    def test_unknown_property_fails_closed(self) -> None:
        record = json.loads(
            (SCHEMAS / "fixtures/records/artifact-ref.json").read_text(encoding="utf-8")
        )
        record["private_locator"] = "/private/example"
        self.assert_code("SCHEMA_VALIDATION", lambda: self.registry.validate(record))

    def test_explicit_discriminators_must_match_the_record(self) -> None:
        manifest = json.loads(
            (SCHEMAS / "fixtures/records/export-manifest.json").read_text(encoding="utf-8")
        )
        self.assert_code(
            "DISCRIMINATOR_MISMATCH",
            lambda: self.registry.validate(
                manifest,
                kind="ExportValidation",
                version="1.0.0",
            ),
        )
        artifact_ref = json.loads(
            (SCHEMAS / "fixtures/records/artifact-ref.json").read_text(encoding="utf-8")
        )
        artifact_ref["schema_version"] = "9.0.0"
        self.assert_code(
            "DISCRIMINATOR_MISMATCH",
            lambda: self.registry.validate(
                artifact_ref,
                kind="ArtifactRef",
                version="1.0.0",
            ),
        )

    def test_artifact_reference_target_is_registry_bound(self) -> None:
        artifact_ref = json.loads(
            (SCHEMAS / "fixtures/records/artifact-ref.json").read_text(encoding="utf-8")
        )
        grant = json.loads(
            (SCHEMAS / "fixtures/records/capability-grant-spec.json").read_text(encoding="utf-8")
        )
        artifact_ref["artifact_id"] = grant["id"]
        self.assert_code("PREFIX_KIND_MISMATCH", lambda: self.registry.validate(artifact_ref))

        artifact_ref = json.loads(
            (SCHEMAS / "fixtures/records/artifact-ref.json").read_text(encoding="utf-8")
        )
        artifact_ref["artifact_id_origin"] = "legacy_import"
        self.assert_code("INVALID_ID", lambda: self.registry.validate(artifact_ref))

        artifact_ref = json.loads(
            (SCHEMAS / "fixtures/records/artifact-ref.json").read_text(encoding="utf-8")
        )
        artifact_ref["artifact_kind"] = "UnknownArtifact"
        self.assert_code("UNKNOWN_KIND", lambda: self.registry.validate(artifact_ref))

        artifact_ref["artifact_kind"] = "CandidateArtifact"
        artifact_ref["artifact_schema_version"] = "2.0.0"
        self.assert_code("UNSUPPORTED_MAJOR", lambda: self.registry.validate(artifact_ref))

    def test_artifact_envelope_target_and_payload_are_registry_bound(self) -> None:
        envelope = json.loads(
            (SCHEMAS / "fixtures/records/artifact-envelope.json").read_text(encoding="utf-8")
        )

        unknown = json.loads(json.dumps(envelope))
        unknown["artifact_kind"] = "UnknownArtifact"
        unknown["integrity"]["digest"] = canonical_digest(
            unknown,
            exclude_integrity_digest=True,
        )
        self.assert_code("UNKNOWN_KIND", lambda: self.registry.validate(unknown))

        unsupported = json.loads(json.dumps(envelope))
        unsupported["artifact_schema_version"] = "2.0.0"
        unsupported["integrity"]["digest"] = canonical_digest(
            unsupported,
            exclude_integrity_digest=True,
        )
        self.assert_code("UNSUPPORTED_MAJOR", lambda: self.registry.validate(unsupported))

        mismatched_kind = json.loads(json.dumps(envelope))
        mismatched_kind["payload"]["legacy_kind"] = "LegacyMechanism"
        mismatched_kind["integrity"]["digest"] = canonical_digest(
            mismatched_kind,
            exclude_integrity_digest=True,
        )
        self.assert_code(
            "ENVELOPE_PAYLOAD_INVALID",
            lambda: self.registry.validate(mismatched_kind),
        )

        invalid_source = json.loads(json.dumps(envelope))
        del invalid_source["payload"]["source_record"]["claim_text"]
        source_digest = canonical_digest(invalid_source["payload"]["source_record"])
        invalid_source["payload"]["source_digest"] = source_digest
        invalid_source["input_digests"] = [source_digest]
        invalid_source["integrity"]["digest"] = canonical_digest(
            invalid_source,
            exclude_integrity_digest=True,
        )
        self.assert_code("SCHEMA_VALIDATION", lambda: self.registry.validate(invalid_source))

        candidate = json.loads(
            (SCHEMAS / "fixtures/records/candidate-artifact.json").read_text(encoding="utf-8")
        )
        native = {
            "schema_version": "1.0.0",
            "id": new_typed_id("rec"),
            "id_origin": "native",
            "kind": "ArtifactEnvelope",
            "artifact_kind": "CandidateArtifact",
            "artifact_schema_version": "1.0.0",
            "created_at": "2026-08-10T12:00:00Z",
            "producer_actor_id": "platform_steward",
            "classification": "private_operational",
            "retention": "durable",
            "input_digests": [canonical_digest(candidate)],
            "aliases": [candidate["id"]],
            "payload": candidate,
            "integrity": {
                "algorithm": "sha256",
                "canonicalization_profile": CANONICALIZATION_PROFILE,
                "digest": "sha256:" + "0" * 64,
            },
        }
        native["integrity"]["digest"] = canonical_digest(
            native,
            exclude_integrity_digest=True,
        )
        self.assertEqual(self.registry.validate(native).kind, "ArtifactEnvelope")

        native["artifact_kind"] = "ArtifactEnvelope"
        native["integrity"]["digest"] = canonical_digest(
            native,
            exclude_integrity_digest=True,
        )
        self.assert_code("ENVELOPE_TARGET_INVALID", lambda: self.registry.validate(native))

    def test_in_process_mapping_cannot_bypass_canonical_value_profile(self) -> None:
        record = json.loads(
            (SCHEMAS / "fixtures/records/artifact-ref.json").read_text(encoding="utf-8")
        )
        record["size_bytes"] = 1.5
        self.assert_code("UNSAFE_NUMBER", lambda: self.registry.validate(record))
        record["size_bytes"] = 1
        record["created_by"] = "\ud800"
        self.assert_code("INVALID_UNICODE", lambda: self.registry.validate(record))

    def test_prefix_kind_mismatch_fails_after_schema_validation(self) -> None:
        record = json.loads(
            (SCHEMAS / "fixtures/records/artifact-ref.json").read_text(encoding="utf-8")
        )
        record["id"] = record["id"].replace("aref_", "cand_", 1)
        self.assert_code("SCHEMA_VALIDATION", lambda: self.registry.validate(record))

        candidate = json.loads(
            (SCHEMAS / "fixtures/records/candidate-artifact.json").read_text(encoding="utf-8")
        )
        candidate["parent_candidate_ids"] = ["cand_not-a-uuid"]
        self.assert_code("SCHEMA_VALIDATION", lambda: self.registry.validate(candidate))

    def test_non_z_timestamp_is_rejected(self) -> None:
        record = json.loads(
            (SCHEMAS / "fixtures/records/artifact-ref.json").read_text(encoding="utf-8")
        )
        record["created_at"] = "2026-08-10T08:00:00-04:00"
        self.assert_code("SCHEMA_VALIDATION", lambda: self.registry.validate(record))
        record["created_at"] = "2026-02-30T00:00:00Z"
        self.assert_code("SCHEMA_VALIDATION", lambda: self.registry.validate(record))

    def test_integrity_and_cross_field_semantics_fail_closed(self) -> None:
        envelope = json.loads(
            (SCHEMAS / "fixtures/records/artifact-envelope.json").read_text(encoding="utf-8")
        )
        envelope["payload"]["claim_id"] = "tampered"
        self.assert_code("INTEGRITY_MISMATCH", lambda: self.registry.validate(envelope))

        receipt = json.loads(
            (SCHEMAS / "fixtures/records/freeze-receipt.json").read_text(encoding="utf-8")
        )
        receipt["tree_digest"] = "sha256:" + "0" * 64
        self.assert_code("TREE_DIGEST_MISMATCH", lambda: self.registry.validate(receipt))
        receipt = json.loads(
            (SCHEMAS / "fixtures/records/freeze-receipt.json").read_text(encoding="utf-8")
        )
        receipt["entries"][0]["path"] = "../escape"
        receipt["tree_digest"] = canonical_digest(receipt["entries"])
        self.assert_code("TREE_MANIFEST_INVALID", lambda: self.registry.validate(receipt))
        receipt = json.loads(
            (SCHEMAS / "fixtures/records/freeze-receipt.json").read_text(encoding="utf-8")
        )
        first = {**receipt["entries"][0], "path": "A.txt"}
        second = {**receipt["entries"][0], "path": "a.txt"}
        receipt["entries"] = [first, second]
        receipt["file_count"] = 2
        receipt["total_size_bytes"] = first["size_bytes"] + second["size_bytes"]
        receipt["tree_digest"] = canonical_digest(receipt["entries"])
        self.assert_code("TREE_MANIFEST_INVALID", lambda: self.registry.validate(receipt))

        candidate = json.loads(
            (SCHEMAS / "fixtures/records/candidate-artifact.json").read_text(encoding="utf-8")
        )
        candidate["revision_of"] = new_typed_id("cand")
        self.assert_code("CANDIDATE_PARENT_MISMATCH", lambda: self.registry.validate(candidate))

        approval = json.loads(
            (SCHEMAS / "fixtures/records/export-approval.json").read_text(encoding="utf-8")
        )
        approval["state"] = "rejected"
        self.assert_code("EXPORT_DECISION_MISMATCH", lambda: self.registry.validate(approval))

    def test_stale_schema_digest_prevents_registry_startup(self) -> None:
        document = json.loads((SCHEMAS / "registry.json").read_text(encoding="utf-8"))
        document["entries"][0]["schema_digest"] = "sha256:" + "0" * 64
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            self.assert_code("SCHEMA_DIGEST_MISMATCH", lambda: SchemaRegistry.load(path))

    def test_malformed_registry_fails_before_fields_are_consumed(self) -> None:
        document = json.loads((SCHEMAS / "registry.json").read_text(encoding="utf-8"))
        document["entries"] = 7
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry.json"
            path.write_text(json.dumps(document), encoding="utf-8")
            self.assert_code("REGISTRY_INVALID", lambda: SchemaRegistry.load(path))


class LegacyMigrationTests(ContractTestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls.registry = SchemaRegistry.load()

    def test_current_legacy_corpus_migrates_and_rolls_back(self) -> None:
        records = current_legacy_records()
        report = migration_report(records, registry=self.registry)
        self.assertGreater(len(records), 0)
        self.assertEqual(report["input_count"], len(records))
        self.assertEqual(report["migrated_count"], len(records))
        self.assertEqual(report["deduplicated_count"], 0)
        self.assertEqual(report["quarantined_count"], 0)
        self.assertTrue(all(item["rollback"] == "pass" for item in report["migrated"]))

    def test_migration_is_pure_and_idempotent(self) -> None:
        kind, _, record, _, _ = current_legacy_records()[0]
        self.assertIsNotNone(record)
        before = json.loads(json.dumps(record))
        first = migrate_record(kind, record, registry=self.registry)
        second = migrate_record(kind, record, registry=self.registry)
        self.assertEqual(first, second)
        self.assertEqual(record, before)
        self.assertEqual(rollback_envelope(first, registry=self.registry), before)

    def test_envelope_tampering_breaks_rollback_before_source_recovery(self) -> None:
        kind, _, record, _, _ = current_legacy_records()[0]
        self.assertIsNotNone(record)
        envelope = migrate_record(kind, record, registry=self.registry)
        envelope["payload"]["source_record"]["claim_text"] = "tampered"
        self.assert_code(
            "INTEGRITY_MISMATCH",
            lambda: rollback_envelope(envelope, registry=self.registry),
        )

    def test_invalid_record_is_quarantined_without_crashing_report(self) -> None:
        invalid = {"claim_id": "claim-invalid"}
        report = migration_report(
            [("LegacyClaim", "fixture.jsonl", invalid)],
            registry=self.registry,
        )
        self.assertEqual(report["migrated_count"], 0)
        self.assertEqual(report["quarantined_count"], 1)
        self.assertEqual(report["quarantined"][0]["reason_code"], "SCHEMA_VALIDATION")

    def test_queue_import_ids_are_namespaced_by_source_path(self) -> None:
        queue = json.loads(
            (SCHEMAS / "fixtures/records/legacy-queue-record.json").read_text(encoding="utf-8")
        )
        first = migrate_record(
            "LegacyQueueRecord",
            queue,
            source_path="researcher/runs/run-a/sources/queue.jsonl",
            registry=self.registry,
        )
        second = migrate_record(
            "LegacyQueueRecord",
            queue,
            source_path="researcher/runs/run-b/sources/queue.jsonl",
            registry=self.registry,
        )
        self.assertNotEqual(first["id"], second["id"])

    def test_migration_id_conflicts_quarantine_every_claimant(self) -> None:
        kind, _, record, _, _ = current_legacy_records()[0]
        self.assertIsNotNone(record)
        conflicting = {**record, "claim_text": f"{record['claim_text']} Conflicting revision."}
        report = migration_report(
            [
                (kind, "claims/one.jsonl", record),
                (kind, "claims/two.jsonl", conflicting),
            ],
            registry=self.registry,
        )
        self.assertEqual(report["input_count"], 2)
        self.assertEqual(report["migrated_count"], 0)
        self.assertEqual(report["deduplicated_count"], 0)
        self.assertEqual(report["quarantined_count"], 2)
        self.assertEqual(
            {item["reason_code"] for item in report["quarantined"]},
            {"MIGRATION_ID_COLLISION"},
        )

    def test_exact_duplicate_migration_inputs_are_deduplicated(self) -> None:
        kind, _, record, _, _ = current_legacy_records()[0]
        self.assertIsNotNone(record)
        report = migration_report(
            [
                (kind, "claims/one.jsonl", record),
                (kind, "claims/two.jsonl", dict(record)),
            ],
            registry=self.registry,
        )
        self.assertEqual(report["input_count"], 2)
        self.assertEqual(report["migrated_count"], 1)
        self.assertEqual(report["deduplicated_count"], 1)
        self.assertEqual(report["quarantined_count"], 0)
        self.assertEqual(report["deduplicated"][0]["reason_code"], "MIGRATION_ID_DUPLICATE")

    def test_public_source_manifest_requires_git_tracked_inputs(self) -> None:
        manifest = {
            "schema_version": "1.0.0",
            "classification": "public",
            "sources": [
                {
                    "kind": "LegacyClaim",
                    "path": "researcher/claims/index.jsonl",
                    "format": "jsonl",
                }
            ],
        }
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "manifest.json"
            path.write_text(json.dumps(manifest), encoding="utf-8")
            with patch(
                "researcher.scripts.migrate_legacy._is_git_tracked",
                return_value=False,
            ):
                self.assert_code("SOURCE_NOT_PUBLIC", lambda: legacy_records_from_manifest(path))

    def test_programmer_errors_are_not_misreported_as_quarantine(self) -> None:
        _, source_path, record, raw_digest, _ = current_legacy_records()[0]
        self.assertIsNotNone(record)
        with patch(
            "researcher.scripts.migrate_legacy.migrate_record",
            side_effect=RuntimeError("injected"),
        ):
            with self.assertRaises(RuntimeError):
                migration_report(
                    [("LegacyClaim", source_path, record, raw_digest)],
                    registry=self.registry,
                )

    def test_malformed_jsonl_line_is_quarantined_with_exact_byte_digest(self) -> None:
        raw_line = b'{"claim_id":}\r\n'
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "malformed.jsonl"
            path.write_bytes(raw_line)
            record, raw_digest, ingestion_error = _read_jsonl(path)[0]
        self.assertIsNone(record)
        report = migration_report(
            [("LegacyClaim", "malformed.jsonl", record, raw_digest, ingestion_error)],
            registry=self.registry,
        )
        self.assertEqual(report["migrated_count"], 0)
        self.assertEqual(report["quarantined_count"], 1)
        self.assertEqual(report["quarantined"][0]["reason_code"], "INVALID_JSON")
        self.assertEqual(report["quarantined"][0]["source_bytes_digest"], sha256_bytes(raw_line))
        self.assertIsNone(report["quarantined"][0]["source_record_digest"])


if __name__ == "__main__":
    unittest.main()
