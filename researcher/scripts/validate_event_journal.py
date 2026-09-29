#!/usr/bin/env python3
"""Validate SPEC-004 schemas, migrations, journal, projector, and recovery."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from pathlib import Path
from typing import Any

try:
    from event_store import EventStore  # type: ignore[import-not-found]
    from run_projector import ResearchRunProjector  # type: ignore[import-not-found]
    from schema_contract import SchemaRegistry, canonical_digest, parse_json_strict, sha256_bytes  # type: ignore[import-not-found]
except ModuleNotFoundError:
    from researcher.scripts.event_store import EventStore
    from researcher.scripts.run_projector import ResearchRunProjector
    from researcher.scripts.schema_contract import (
        SchemaRegistry,
        canonical_digest,
        parse_json_strict,
        sha256_bytes,
    )


ROOT = Path(__file__).resolve().parents[2]
GENERATED_REPORT = ROOT / "researcher" / "event_journal" / "generated" / "conformance-report.json"
EVENT_FIXTURE = ROOT / "researcher" / "schemas" / "fixtures" / "records" / "organization-event.json"
MIGRATION_MANIFEST = ROOT / "researcher" / "event_journal" / "migrations" / "manifest.json"
FIXED_CLOCK = "2026-08-11T12:00:00Z"


def _pretty_json(value: Any) -> str:
    return json.dumps(value, ensure_ascii=False, sort_keys=True, indent=2) + "\n"


def _atomic_write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(
        prefix=f".{path.name}.", suffix=".tmp", dir=path.parent
    )
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary_name, path)
        directory = os.open(path.parent, os.O_RDONLY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    except Exception:
        try:
            os.unlink(temporary_name)
        except FileNotFoundError:
            pass
        raise


def build_report() -> dict[str, Any]:
    registry = SchemaRegistry.load()
    event = parse_json_strict(EVENT_FIXTURE.read_text(encoding="utf-8"))
    if not isinstance(event, dict):
        raise ValueError("OrganizationEvent golden is not an object")
    registry.resolve_for_write("OrganizationEvent", "1.0.0")
    registry.resolve_for_write("ResearchRunTransition", "1.0.0")
    registry.validate(event)
    manifest_body = MIGRATION_MANIFEST.read_bytes()
    manifest = parse_json_strict(manifest_body.decode("utf-8"))
    if not isinstance(manifest, dict):
        raise ValueError("event-journal migration manifest is not an object")

    with tempfile.TemporaryDirectory(prefix="event-journal-conformance-") as temporary:
        root = Path(temporary)
        store = EventStore(root / "journal.sqlite3", registry=registry, clock=lambda: FIXED_CLOCK)
        first = store.append(event, 0)
        duplicate = store.append(event, 0)
        integrity = store.verify_integrity()
        projector = ResearchRunProjector(store)
        first_projection = projector.rebuild()
        second_projection = projector.rebuild()
        if first_projection.state_digest != second_projection.state_digest:
            raise ValueError("event-journal projector replay is nondeterministic")
        backup_root = root / "backups"
        backup_receipt = store.backup(backup_root)
        backup_generation = backup_root / backup_receipt.backup_name
        restored = store.restore_verified(backup_generation, root / "restores")
        restored_integrity = restored.verify_integrity()
        if restored_integrity.last_entry_hash != integrity.last_entry_hash:
            raise ValueError("restored journal tail differs from the source")
        restored_projection = ResearchRunProjector(restored).rebuild()
        if (
            restored_projection.state_digest != first_projection.state_digest
            or restored_projection.last_sequence != first_projection.last_sequence
            or restored_projection.source_hash != first_projection.source_hash
        ):
            raise ValueError("restored projection differs from the source replay")

    return {
        "schema_version": "1.0.0",
        "result": "pass",
        "contracts": {
            "organization_event": "OrganizationEvent@1.0.0",
            "research_run_transition": "ResearchRunTransition@1.0.0",
            "event_digest": canonical_digest(event),
        },
        "migrations": {
            "application_id": manifest["application_id"],
            "latest_version": manifest["latest_version"],
            "manifest_digest": sha256_bytes(manifest_body),
            "migration_count": len(manifest["migrations"]),
            "migration_digests": [item["digest"] for item in manifest["migrations"]],
        },
        "append": {
            "entry_count": integrity.entry_count,
            "subject_count": integrity.subject_count,
            "first_sequence": first.sequence,
            "duplicate_sequence": duplicate.sequence,
            "duplicate_returned_original": duplicate.duplicate,
            "last_entry_hash": integrity.last_entry_hash,
        },
        "projection": {
            "projector": first_projection.projector_name,
            "projector_version": first_projection.projector_version,
            "projection_count": len(first_projection.projections),
            "quarantine_count": len(first_projection.quarantines),
            "state_digest": first_projection.state_digest,
            "replay_identical": True,
        },
        "backup_restore": {
            "backup_verified": True,
            "restore_verified": True,
            "source_last_sequence": backup_receipt.source_last_sequence,
            "source_last_entry_hash": backup_receipt.source_last_entry_hash,
            "restored_projection_digest": restored_projection.state_digest,
            "restored_projection_sequence": restored_projection.last_sequence,
            "restored_projection_source_hash": restored_projection.source_hash,
        },
        "verified_invariants": [
            "canonical-event-bytes",
            "exact-duplicate-idempotency",
            "transactional-subject-version",
            "contiguous-global-hash-chain",
            "deterministic-projector-replay",
            "verified-online-backup-and-fresh-restore",
        ],
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate and reject generated drift")
    mode.add_argument("--write", action="store_true", help="refresh deterministic conformance evidence")
    mode.add_argument("--json", action="store_true", help="print the expected report")
    args = parser.parse_args()
    report = build_report()
    body = _pretty_json(report)
    if args.write:
        _atomic_write(GENERATED_REPORT, body)
        print(
            "Event-journal evidence written: "
            f"{report['append']['entry_count']} entry, "
            f"projection {report['projection']['state_digest'][:19]}"
        )
        return 0
    if args.json:
        print(body, end="")
        return 0
    try:
        actual = GENERATED_REPORT.read_text(encoding="utf-8")
    except OSError:
        actual = ""
    if actual != body:
        print("Event-journal validation failed: generated conformance report is stale", file=sys.stderr)
        return 1
    print(
        "Event-journal validation passed: "
        f"{report['append']['entry_count']} entry, "
        f"projection {report['projection']['state_digest'][:19]}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
