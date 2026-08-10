# Schema migration, quarantine, and rollback

## Dry run

1. Run `python researcher/scripts/validate_schemas.py --check`.
2. Run `python researcher/scripts/migrate_legacy.py --dry-run --json`. The default reads only `researcher/schemas/public-legacy-sources.json`.
3. Review every `quarantined` reason code and every `deduplicated` input. Do not activate a writer while quarantine is non-empty.
4. Compare the report digest with `researcher/schemas/generated/migration-dry-run.json`.

The adapter never edits a claim, mechanism, run-state, queue record, or append-only ledger. A migrated envelope carries the original semantic key as an alias, the canonical source-record digest, and the original record in its migration payload. The report separately records the SHA-256 digest of the exact source line or JSON file bytes. Inputs that resolve to one deterministic ID and one canonical source identity are represented once and listed under `deduplicated`; conflicting source identities for one ID quarantine every claimant with `MIGRATION_ID_COLLISION`.

For private runtime records, create a `private_operational` source manifest, run with `--source-manifest`, and direct the report to ignored `researcher/schemas/reports/runtime/`. Public manifests reject files that are not Git-tracked. Never add a private run path or digest to the public source manifest or generated evidence.

## Activation

Activation of a new writer requires a later owner-spec PR. That PR names the old reader, new writer, compatibility window, rollback owner, and cutoff condition. Merely registering a schema does not activate a writer.

## Quarantine

Unknown kinds, unsupported major versions, schema failures, digest mismatches, and malformed legacy records produce typed quarantine entries without private payloads. Unexpected implementation exceptions stop the run and fail CI; they are never converted into quarantine. Correct the source through its existing owner workflow or register a reviewed adapter. Never weaken a schema to make an unexplained record pass.

## Rollback

`rollback_envelope()` returns the original record only after verifying the embedded source digest, target kind and version, legacy kind and key, provenance bindings, and adapter schema. Rollback restores the prior writer and reader configuration; it does not delete envelopes already produced. New-format records remain isolated for diagnosis and later replay.

If a schema file or registry digest was released incorrectly, supersede it with a new registry revision. Do not rewrite an effective registry artifact or reuse a schema version for different bytes.
