#!/usr/bin/env python3
"""Pure, idempotent legacy-record adapters for SPEC-003 dry-run migrations."""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any, Iterable, Mapping

try:
    from schema_contract import (
        CANONICALIZATION_PROFILE,
        ContractError,
        LEGACY_ADAPTER_KEY_FIELDS,
        SchemaRegistry,
        canonical_digest,
        deterministic_import_id,
        parse_json_strict,
        sha256_bytes,
        validate_digest,
    )
except ModuleNotFoundError:  # Imported as researcher.scripts.migrate_legacy.
    from researcher.scripts.schema_contract import (
        CANONICALIZATION_PROFILE,
        ContractError,
        LEGACY_ADAPTER_KEY_FIELDS,
        SchemaRegistry,
        canonical_digest,
        deterministic_import_id,
        parse_json_strict,
        sha256_bytes,
        validate_digest,
    )


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_SOURCE_MANIFEST = ROOT / "researcher/schemas/public-legacy-sources.json"
IMPORT_NAMESPACE = uuid.UUID("5ea9f7a6-8f4e-4d37-a6f8-c9f4d5c22c90")
LEGACY_CONFIG = {
    "LegacyClaim": {
        "key": LEGACY_ADAPTER_KEY_FIELDS["LegacyClaim"],
        "prefix": "rec",
        "classification": "public",
        "retention": "durable",
    },
    "LegacyMechanism": {
        "key": LEGACY_ADAPTER_KEY_FIELDS["LegacyMechanism"],
        "prefix": "rec",
        "classification": "public",
        "retention": "durable",
    },
    "LegacyRunState": {
        "key": LEGACY_ADAPTER_KEY_FIELDS["LegacyRunState"],
        "prefix": "rec",
        "classification": "private_operational",
        "retention": "review_cycle",
    },
    "LegacyQueueRecord": {
        "key": LEGACY_ADAPTER_KEY_FIELDS["LegacyQueueRecord"],
        "prefix": "rec",
        "classification": "private_operational",
        "retention": "review_cycle",
    },
}


def _created_at(kind: str, record: Mapping[str, Any]) -> str:
    value = record.get("created_at")
    if isinstance(value, str) and value:
        return value.replace("+00:00", "Z")
    if kind == "LegacyClaim":
        return f"{record['last_reviewed']}T00:00:00Z"
    # Existing mechanism records do not carry creation time. Epoch zero is an
    # explicit unknown sentinel, not a fabricated migration timestamp.
    return "1970-01-01T00:00:00Z"


def migrate_record(
    kind: str,
    record: Mapping[str, Any],
    *,
    source_path: str | None = None,
    registry: SchemaRegistry | None = None,
) -> dict[str, Any]:
    schema_registry = registry or SchemaRegistry.load()
    config = LEGACY_CONFIG.get(kind)
    if config is None:
        raise ContractError("UNKNOWN_LEGACY_KIND", "legacy adapter kind is not registered")
    schema_registry.validate(record, kind=kind, version="1.0.0")
    key = record.get(config["key"])
    if not isinstance(key, str) or not key:
        raise ContractError("LEGACY_ID_MISSING", "legacy record lacks its semantic key")
    if kind == "LegacyQueueRecord":
        if not source_path:
            raise ContractError("LEGACY_SCOPE_MISSING", "queue import requires its source path scope")
        identity_key = f"{source_path}:{key}"
    else:
        identity_key = key
    source_digest = canonical_digest(dict(record))
    envelope: dict[str, Any] = {
        "schema_version": "1.0.0",
        "id": deterministic_import_id(
            config["prefix"],
            IMPORT_NAMESPACE,
            f"{kind}:{identity_key}",
        ),
        "id_origin": "legacy_import",
        "kind": "ArtifactEnvelope",
        "artifact_kind": kind,
        "artifact_schema_version": "1.0.0",
        "created_at": _created_at(kind, record),
        "producer_actor_id": "legacy_adapter",
        "classification": config["classification"],
        "retention": config["retention"],
        "input_digests": [source_digest],
        "aliases": [key],
        "payload": {
            "legacy_kind": kind,
            "legacy_key": key,
            "source_digest": source_digest,
            "source_record": dict(record),
        },
        "integrity": {
            "algorithm": "sha256",
            "canonicalization_profile": CANONICALIZATION_PROFILE,
            "digest": "sha256:" + "0" * 64,
        },
    }
    if source_path is not None:
        envelope["payload"]["source_path"] = source_path
    envelope["integrity"]["digest"] = canonical_digest(
        envelope,
        exclude_integrity_digest=True,
    )
    schema_registry.validate(envelope)
    return envelope


def rollback_envelope(
    envelope: Mapping[str, Any],
    *,
    registry: SchemaRegistry | None = None,
) -> dict[str, Any]:
    schema_registry = registry or SchemaRegistry.load()
    schema_registry.validate(envelope)
    if envelope.get("id_origin") != "legacy_import":
        raise ContractError("ROLLBACK_UNSUPPORTED", "envelope is not a legacy import")
    payload = envelope.get("payload")
    if not isinstance(payload, dict) or not isinstance(payload.get("source_record"), dict):
        raise ContractError("ROLLBACK_INVALID", "legacy import payload is incomplete")
    source_record = dict(payload["source_record"])
    if canonical_digest(source_record) != payload.get("source_digest"):
        raise ContractError("ROLLBACK_DIGEST_MISMATCH", "legacy source record failed rollback verification")
    schema_registry.validate(
        source_record,
        kind=str(envelope["artifact_kind"]),
        version=str(envelope["artifact_schema_version"]),
    )
    return source_record


def _read_jsonl(path: Path) -> list[tuple[dict[str, Any] | None, str, str | None]]:
    records: list[tuple[dict[str, Any] | None, str, str | None]] = []
    for line_number, raw_line in enumerate(path.read_bytes().splitlines(keepends=True), start=1):
        if not raw_line.strip():
            continue
        raw_digest = sha256_bytes(raw_line)
        try:
            line = raw_line.decode("utf-8")
        except UnicodeError:
            records.append((None, raw_digest, "LEGACY_PARSE"))
            continue
        try:
            value = parse_json_strict(line)
        except ContractError as exc:
            records.append((None, raw_digest, exc.code))
            continue
        if not isinstance(value, dict):
            records.append((None, raw_digest, "LEGACY_PARSE"))
            continue
        records.append((value, raw_digest, None))
    return records


def _is_git_tracked(path: str) -> bool:
    try:
        result = subprocess.run(
            ["git", "-C", str(ROOT), "ls-files", "--error-unmatch", "--", path],
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError:
        return False
    return result.returncode == 0


def legacy_records_from_manifest(
    manifest_path: Path = DEFAULT_SOURCE_MANIFEST,
) -> list[tuple[str, str, dict[str, Any] | None, str, str | None]]:
    manifest = parse_json_strict(manifest_path.read_text(encoding="utf-8"))
    if not isinstance(manifest, dict) or set(manifest) != {
        "schema_version",
        "classification",
        "sources",
    }:
        raise ContractError("SOURCE_MANIFEST_INVALID", "legacy source manifest fields differ")
    if manifest["schema_version"] != "1.0.0" or manifest["classification"] not in {
        "public",
        "private_operational",
    }:
        raise ContractError("SOURCE_MANIFEST_INVALID", "legacy source manifest header is invalid")
    if not isinstance(manifest["sources"], list):
        raise ContractError("SOURCE_MANIFEST_INVALID", "legacy source manifest has no source list")
    is_public_manifest = manifest["classification"] == "public"
    records: list[tuple[str, str, dict[str, Any] | None, str, str | None]] = []
    seen: set[tuple[str, str]] = set()
    for source in manifest["sources"]:
        if not isinstance(source, dict) or set(source) != {"kind", "path", "format"}:
            raise ContractError("SOURCE_MANIFEST_INVALID", "legacy source entry fields differ")
        kind = source["kind"]
        relative = source["path"]
        source_format = source["format"]
        if kind not in LEGACY_CONFIG or source_format not in {"json", "jsonl"}:
            raise ContractError("SOURCE_MANIFEST_INVALID", "legacy source kind or format is invalid")
        if not isinstance(relative, str) or not relative:
            raise ContractError("SOURCE_MANIFEST_INVALID", "legacy source path is invalid")
        lexical_path = ROOT / relative
        path = lexical_path.resolve()
        try:
            normalized = path.relative_to(ROOT.resolve()).as_posix()
        except ValueError as exc:
            raise ContractError("PATH_ESCAPE", "legacy source path escapes the repository") from exc
        if lexical_path.is_symlink() or not path.is_file():
            raise ContractError("SOURCE_MANIFEST_INVALID", "legacy source must be a regular file")
        if is_public_manifest and not _is_git_tracked(normalized):
            raise ContractError(
                "SOURCE_NOT_PUBLIC",
                "public migration evidence may use only Git-tracked source files",
            )
        key = (kind, normalized)
        if key in seen:
            raise ContractError("SOURCE_MANIFEST_INVALID", "legacy source entry is duplicated")
        seen.add(key)
        if source_format == "jsonl":
            for record, raw_digest, ingestion_error in _read_jsonl(path):
                records.append((kind, normalized, record, raw_digest, ingestion_error))
        else:
            raw_body = path.read_bytes()
            raw_digest = sha256_bytes(raw_body)
            try:
                text = raw_body.decode("utf-8")
            except UnicodeError:
                records.append((kind, normalized, None, raw_digest, "LEGACY_PARSE"))
                continue
            try:
                value = parse_json_strict(text)
            except ContractError as exc:
                records.append((kind, normalized, None, raw_digest, exc.code))
                continue
            if not isinstance(value, dict):
                records.append((kind, normalized, None, raw_digest, "LEGACY_PARSE"))
                continue
            records.append((kind, normalized, value, raw_digest, None))
    return records


def current_legacy_records() -> list[tuple[str, str, dict[str, Any] | None, str, str | None]]:
    """Return only the explicitly public, committed migration fixture set."""

    return legacy_records_from_manifest(DEFAULT_SOURCE_MANIFEST)


def migration_report(
    records: Iterable[
        tuple[str, str, Mapping[str, Any]]
        | tuple[str, str, Mapping[str, Any], str]
        | tuple[str, str, Mapping[str, Any] | None, str, str | None]
    ],
    *,
    registry: SchemaRegistry | None = None,
) -> dict[str, Any]:
    schema_registry = registry or SchemaRegistry.load()
    proposed: list[dict[str, Any]] = []
    migrated: list[dict[str, Any]] = []
    deduplicated: list[dict[str, Any]] = []
    quarantined: list[dict[str, Any]] = []

    for source_item in records:
        if len(source_item) == 5:
            kind, source_path, record, source_bytes_digest, ingestion_error = source_item
        elif len(source_item) == 4:
            kind, source_path, record, source_bytes_digest = source_item
            ingestion_error = None
        else:
            kind, source_path, record = source_item
            source_bytes_digest = canonical_digest(dict(record))
            ingestion_error = None
        validate_digest(source_bytes_digest)
        if record is None:
            quarantined.append(
                {
                    "kind": kind,
                    "source_path": source_path,
                    "source_bytes_digest": source_bytes_digest,
                    "source_record_digest": None,
                    "reason_code": ingestion_error or "LEGACY_PARSE",
                }
            )
            continue
        source_record_digest: str | None = None
        try:
            source_record_digest = canonical_digest(dict(record))
            envelope = migrate_record(
                kind,
                record,
                source_path=source_path,
                registry=schema_registry,
            )
            rolled_back = rollback_envelope(envelope, registry=schema_registry)
            if rolled_back != dict(record):
                raise ContractError("ROLLBACK_MISMATCH", "migration rollback changed the legacy record")
            key = str(record[LEGACY_CONFIG[kind]["key"]])
            proposed.append(
                {
                    "kind": kind,
                    "legacy_key": key,
                    "source_path": source_path,
                    "source_bytes_digest": source_bytes_digest,
                    "source_record_digest": source_record_digest,
                    "new_id": envelope["id"],
                    "new_digest": envelope["integrity"]["digest"],
                    "rollback": "pass",
                }
            )
        except ContractError as exc:
            quarantined.append(
                {
                    "kind": kind,
                    "source_path": source_path,
                    "source_bytes_digest": source_bytes_digest,
                    "source_record_digest": source_record_digest,
                    "reason_code": exc.code,
                }
            )
    groups: dict[str, list[dict[str, Any]]] = {}
    for proposal in proposed:
        groups.setdefault(proposal["new_id"], []).append(proposal)
    for new_id in sorted(groups):
        group = sorted(
            groups[new_id],
            key=lambda item: (
                item["kind"],
                item["legacy_key"],
                item["source_path"],
                item["source_bytes_digest"],
            ),
        )
        identities = {
            (item["kind"], item["legacy_key"], item["source_record_digest"])
            for item in group
        }
        if len(identities) > 1:
            quarantined.extend(
                {
                    "kind": item["kind"],
                    "source_path": item["source_path"],
                    "source_bytes_digest": item["source_bytes_digest"],
                    "source_record_digest": item["source_record_digest"],
                    "new_id": new_id,
                    "reason_code": "MIGRATION_ID_COLLISION",
                }
                for item in group
            )
            continue
        migrated.append(group[0])
        deduplicated.extend(
            {
                "kind": item["kind"],
                "legacy_key": item["legacy_key"],
                "source_path": item["source_path"],
                "source_bytes_digest": item["source_bytes_digest"],
                "source_record_digest": item["source_record_digest"],
                "new_id": new_id,
                "duplicate_of_source_path": group[0]["source_path"],
                "reason_code": "MIGRATION_ID_DUPLICATE",
            }
            for item in group[1:]
        )
    migrated.sort(key=lambda item: (item["kind"], item["legacy_key"], item["source_path"]))
    deduplicated.sort(
        key=lambda item: (item["kind"], item["legacy_key"], item["source_path"])
    )
    quarantined.sort(
        key=lambda item: (
            item["kind"],
            item["source_record_digest"] or item["source_bytes_digest"],
            item["source_path"],
        )
    )
    report = {
        "schema_version": "1.0.0",
        "mode": "dry-run",
        "input_count": len(migrated) + len(deduplicated) + len(quarantined),
        "migrated_count": len(migrated),
        "deduplicated_count": len(deduplicated),
        "quarantined_count": len(quarantined),
        "migrated": migrated,
        "deduplicated": deduplicated,
        "quarantined": quarantined,
    }
    report["report_digest"] = canonical_digest(report)
    return report


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true", help="required: migration never edits legacy input")
    parser.add_argument("--json", action="store_true", help="emit the deterministic report")
    parser.add_argument("--source-manifest", type=Path, default=DEFAULT_SOURCE_MANIFEST)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    if not args.dry_run:
        print("[DRY_RUN_REQUIRED] legacy migration is proposal-only", file=sys.stderr)
        return 2
    try:
        report = migration_report(legacy_records_from_manifest(args.source_manifest))
    except ContractError as exc:
        print(f"[{exc.code}] {exc.safe_message}", file=sys.stderr)
        return 1
    except (OSError, UnicodeError) as exc:
        print(f"[IO_ERROR] {exc.__class__.__name__}", file=sys.stderr)
        return 1
    if args.json:
        print(json.dumps(report, indent=2, sort_keys=True, ensure_ascii=False))
    else:
        print(
            "Legacy migration dry run: "
            f"{report['migrated_count']} migrated, "
            f"{report['deduplicated_count']} deduplicated, "
            f"{report['quarantined_count']} quarantined, "
            f"digest {report['report_digest'][7:19]}"
        )
    return 1 if report["quarantined_count"] else 0


if __name__ == "__main__":
    raise SystemExit(main())
