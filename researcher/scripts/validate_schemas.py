#!/usr/bin/env python3
"""Validate schema registry, cross-language vectors, adapters, and generated reports."""

from __future__ import annotations

import argparse
import json
import os
import sys
import tempfile
from collections import Counter
from pathlib import Path
from typing import Any, Mapping

try:
    from migrate_legacy import current_legacy_records, migration_report
    from schema_contract import (
        DEFAULT_REGISTRY_PATH,
        SCHEMA_ROOT,
        ContractError,
        SchemaRegistry,
        canonicalize,
        parse_json_strict,
        sha256_bytes,
    )
except ModuleNotFoundError:  # Imported as researcher.scripts.validate_schemas.
    from researcher.scripts.migrate_legacy import current_legacy_records, migration_report
    from researcher.scripts.schema_contract import (
        DEFAULT_REGISTRY_PATH,
        SCHEMA_ROOT,
        ContractError,
        SchemaRegistry,
        canonicalize,
        parse_json_strict,
        sha256_bytes,
    )


ROOT = Path(__file__).resolve().parents[2]
GENERATED_ROOT = SCHEMA_ROOT / "generated"
CONFORMANCE_PATH = GENERATED_ROOT / "conformance-report.json"
CURRENT_PATH = GENERATED_ROOT / "current-artifacts-report.json"
MIGRATION_PATH = GENERATED_ROOT / "migration-dry-run.json"
COMPATIBILITY_PATH = GENERATED_ROOT / "compatibility-matrix.md"


def _pretty_json(value: Mapping[str, Any]) -> str:
    return json.dumps(value, indent=2, sort_keys=True, ensure_ascii=False) + "\n"


def _atomic_write(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary_name = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    temporary = Path(temporary_name)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(body)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, path)
        if hasattr(os, "O_DIRECTORY"):
            directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
            try:
                os.fsync(directory)
            finally:
                os.close(directory)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def build_conformance_report(registry: SchemaRegistry) -> dict[str, Any]:
    suite_path = SCHEMA_ROOT / "fixtures/canonicalization-v1.json"
    suite = parse_json_strict(suite_path.read_text(encoding="utf-8"))
    if not isinstance(suite, dict) or not isinstance(suite.get("cases"), list):
        raise ContractError("FIXTURE_INVALID", "canonicalization suite is invalid")
    cases: list[dict[str, Any]] = []
    for case in suite["cases"]:
        try:
            body = canonicalize(parse_json_strict(case["input_json"]))
            actual = {
                "id": case["id"],
                "result": "pass",
                "canonical": body.decode("utf-8"),
                "digest": sha256_bytes(body),
            }
            if not case["valid"]:
                raise ContractError("FIXTURE_MISMATCH", "invalid canonicalization vector passed")
            if actual["canonical"] != case["expected_canonical"]:
                raise ContractError("FIXTURE_MISMATCH", "canonical bytes differ from golden")
            if actual["digest"] != case["expected_digest"]:
                raise ContractError("FIXTURE_MISMATCH", "canonical digest differs from golden")
        except ContractError as exc:
            if case["valid"] or exc.code != case["expected_code"]:
                raise
            actual = {"id": case["id"], "result": "reject", "reason_code": exc.code}
        cases.append(actual)

    golden_count = 0
    for entry in registry.entries:
        for path in entry.golden_paths:
            record = parse_json_strict(path.read_text(encoding="utf-8"))
            if not isinstance(record, dict):
                raise ContractError("FIXTURE_INVALID", "registered golden is not an object")
            registry.validate(record, kind=entry.kind, version=entry.version)
            golden_count += 1
    registry.validate(registry.document, kind="SchemaRegistry", version="1.0.0")
    return {
        "schema_version": "1.0.0",
        "canonicalization_profile": suite["profile"],
        "suite_digest": sha256_bytes(suite_path.read_bytes()),
        "registered_schema_count": len(registry.entries),
        "golden_record_count": golden_count,
        "cases": cases,
        "result": "pass",
    }


def build_current_artifacts_report(registry: SchemaRegistry) -> dict[str, Any]:
    records = current_legacy_records()
    counts: Counter[str] = Counter()
    source_paths: set[str] = set()
    record_digests: list[str] = []
    for kind, source_path, record, _, ingestion_error in records:
        if record is None:
            raise ContractError(
                ingestion_error or "LEGACY_PARSE",
                "public legacy source contains a malformed record",
            )
        registry.validate(record, kind=kind, version="1.0.0")
        counts[kind] += 1
        source_paths.add(source_path)
        record_digests.append(sha256_bytes(canonicalize(record)))
    return {
        "schema_version": "1.0.0",
        "result": "pass",
        "record_count": len(records),
        "counts_by_adapter": dict(sorted(counts.items())),
        "source_paths": sorted(source_paths),
        "records_digest": sha256_bytes(canonicalize(sorted(record_digests))),
    }


def build_compatibility_matrix(registry: SchemaRegistry) -> str:
    lines = [
        "# Generated schema compatibility matrix",
        "",
        "> Generated by `validate_schemas.py --write`. Do not edit manually.",
        "",
        "| Kind | Version | Owner | Status | Compatibility | ID prefix | Classifications |",
        "|---|---:|---|---|---|---|---|",
    ]
    for entry in registry.entries:
        lines.append(
            "| "
            + " | ".join(
                [
                    f"`{entry.kind}`",
                    entry.version,
                    entry.owner_spec,
                    entry.status,
                    entry.compatibility,
                    f"`{entry.id_prefix}`" if entry.id_prefix else "n/a",
                    ", ".join(f"`{value}`" for value in entry.classifications) or "n/a",
                ]
            )
            + " |"
        )
    lines.extend(
        [
            "",
            "Unknown kinds are quarantined. Unregistered major versions fail before execution.",
            "Deprecated schemas remain readable but cannot be selected by a new writer.",
            "",
        ]
    )
    return "\n".join(lines)


def generated_outputs(registry: SchemaRegistry) -> dict[Path, str]:
    return {
        CONFORMANCE_PATH: _pretty_json(build_conformance_report(registry)),
        CURRENT_PATH: _pretty_json(build_current_artifacts_report(registry)),
        MIGRATION_PATH: _pretty_json(migration_report(current_legacy_records(), registry=registry)),
        COMPATIBILITY_PATH: build_compatibility_matrix(registry),
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group()
    mode.add_argument("--check", action="store_true", help="validate and reject generated drift")
    mode.add_argument("--write", action="store_true", help="atomically refresh generated evidence")
    mode.add_argument("--json", action="store_true", help="print conformance report")
    parser.add_argument("--registry", type=Path, default=DEFAULT_REGISTRY_PATH)
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        registry = SchemaRegistry.load(args.registry)
        outputs = generated_outputs(registry)
        if args.write:
            for path, body in outputs.items():
                _atomic_write(path, body)
            print(
                f"Schema evidence written: {len(registry.entries)} contracts, "
                f"{build_current_artifacts_report(registry)['record_count']} legacy records"
            )
            return 0
        if args.json:
            print(outputs[CONFORMANCE_PATH], end="")
            return 0
        drift = []
        for path, expected in outputs.items():
            try:
                actual = path.read_text(encoding="utf-8")
            except OSError:
                actual = ""
            if actual != expected:
                drift.append(path.relative_to(ROOT).as_posix())
        if drift:
            raise ContractError(
                "GENERATED_DRIFT",
                f"{len(drift)} schema evidence file(s) differ; run validate_schemas.py --write",
            )
        conformance = build_conformance_report(registry)
        current = build_current_artifacts_report(registry)
        print(
            f"Schema validation passed: {len(registry.entries)} contracts, "
            f"{conformance['golden_record_count']} goldens, {current['record_count']} legacy records"
        )
        return 0
    except ContractError as exc:
        print(f"[{exc.code}] {exc.safe_message}", file=sys.stderr)
        return 1
    except OSError as exc:
        print(f"[IO_ERROR] {exc.__class__.__name__}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
