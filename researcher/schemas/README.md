# Schema registry and canonical artifacts

This directory is the runtime-neutral interchange boundary for durable organization records. It does not replace readable skills, research ledgers, or Git history.

## Layout

- `registry.json`: active registry with exact schema-file digests.
- `registry.schema.json`: registry meta-schema.
- `v1/`: SPEC-003-owned Draft 2020-12 schemas.
- `fixtures/`: shared Python and TypeScript conformance records.
- `generated/`: checked compatibility, current-corpus, migration, and conformance evidence.
- `public-legacy-sources.json`: the exact public fixture set allowed into generated migration evidence.
- `typescript/`: independent Ajv and canonicalization consumer with a reusable compiled runtime registry.

SPEC-002 export schemas remain in `researcher/exports/schemas/` and are imported by exact digest. A schema owner keeps its file; the registry provides the common lookup surface.

## Canonical bytes

`jcs-rfc8785-integer-v1` is an RFC 8785-compatible subset:

- strings are UTF-8, are not Unicode-normalized, and reject lone surrogates;
- object properties sort by UTF-16 code units;
- arrays retain order;
- numbers are integers from `-9007199254740991` through `9007199254740991`;
- floats, negative zero, NaN, Infinity, duplicate keys, and hidden parser coercions fail.

JSON record digests hash those canonical bytes. Blob digests hash exact bytes. LF and CRLF therefore differ. `ArtifactEnvelope.integrity.digest` is excluded from its own digest calculation and no other field is excluded.

## Identity and compatibility

Native identifiers are `<registered-prefix>_<UUIDv7>`. Legacy imports use UUIDv5 under the fixed migration namespace and declare `id_origin: legacy_import`. Existing semantic IDs remain aliases.

Consumers require an exact registered kind and supported version. Explicit validator routing parameters must equal the record's embedded discriminators; they cannot select a sibling schema that happens to share a JSON Schema resource. `resolve_for_read` / `resolveForRead` admit active and deprecated contracts; `resolve_for_write` / `resolveForWrite` admit only the single active writer version. The initial registry does not implement permissive minor-version parsing: a schema must explicitly declare and test additive compatibility before a new version is accepted. Retired versions do not resolve.

Python `SchemaRegistry` and TypeScript `LoadedRuntimeRegistry` canonicalize in-process values before schema validation. Both retain compiled validators, enforce classification and typed IDs, and run the same post-schema semantics. Shared goldens include an astral-versus-BMP freeze manifest so both runtimes prove UTF-16 ordering.

Envelope and reference targets are registry-aware. A native `ArtifactEnvelope.payload` is a complete registered target record. A `legacy_import` envelope instead carries an exact adapter kind, semantic key, canonical source digest, and source record; both runtimes revalidate that source record through the declared adapter. `ArtifactRef` resolves the target entry and enforces its ID prefix and native or legacy origin.

## Commands

```bash
python researcher/scripts/validate_schemas.py --check
python researcher/scripts/validate_schemas.py --write
python researcher/scripts/migrate_legacy.py --dry-run
cd researcher/schemas/typescript && npm ci && npm test
```

`--write` updates only deterministic public evidence. It never migrates canonical inputs. Runtime CAS, bindings, quarantine details, and private receipts remain under ignored private roots.

Generated migration evidence never scans `researcher/runs/*`. It reads only Git-tracked files explicitly named by `public-legacy-sources.json`, so an ignored private run cannot affect a public diff or publish a private commitment. Operators may pass a `private_operational` source manifest and keep its output under `researcher/schemas/reports/runtime/`.
