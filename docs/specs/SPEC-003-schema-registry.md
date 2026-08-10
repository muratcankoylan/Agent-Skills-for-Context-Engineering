# SPEC-003: Schema registry and artifact identity

- Status: implemented
- Wave: 0
- Classification: split
- Depends on: SPEC-001, SPEC-002

## Decision

Every durable object exchanged across agents, scripts, runtimes, and the private control plane must resolve to a versioned registered schema before execution. Typed immutable identifiers and content digests replace paths, titles, and chat references as organization keys. Runtime sessions are never canonical state.

## Invariants

1. New identifiers are typed UUIDv7 values; deterministic UUIDv5 is reserved for declared legacy imports.
2. Exact blob bytes and canonical JSON records use different, explicit digest profiles.
3. Unknown kinds and unregistered major versions fail before execution and enter quarantine rather than receiving hidden defaults.
4. Each registry entry pins its schema file digest, owner spec, lifecycle state, compatibility rule, classifications, canonicalization profile, and goldens.
5. An `ArtifactEnvelope` resolves its declared target kind and version. Native envelopes carry a complete target record; legacy envelopes carry a digest-bound source record that validates through the declared adapter.
6. An `ArtifactRef` has no private locator, grants no read authority, and binds its target kind,
   version, typed-ID prefix, and native or legacy origin through the registry.
7. A successful private write is digest-verified, atomic, fsynced, and complete before a reference is published.
8. Classification may rise but cannot silently fall for the same content.
9. Candidate bytes are copied into CAS and frozen before evaluation. Revisions use new candidate IDs.
10. Credential references and durable grant specifications contain no secret value or capability token.
11. Legacy migration is pure, idempotent, reversible, non-in-place, and collision-aware.

## Bootstrap registry boundary

SPEC-003 registers:

- `SchemaRegistry`, `ArtifactEnvelope`, `ArtifactRef`, and private `StorageBinding`;
- the immutable SPEC-002 export record family;
- `CandidateArtifact` and `FreezeReceipt`;
- `CredentialRef` and `CapabilityGrantSpec`;
- `LegacyClaim`, `LegacyMechanism`, `LegacyRunState`, and `LegacyQueueRecord` adapters.

Later owner specs register events, work orders, commands, sources, context packages, evaluation observations, promotion records, execution environments, and contribution packets.

## Interfaces

- `SchemaRegistry.load()` meta-validates schemas, verifies exact file digests, and builds offline Draft 2020-12 validators.
- `parse_json_strict()` and `canonicalize()` implement `jcs-rfc8785-integer-v1` without injected defaults.
- `new_typed_id()` emits monotonic RFC 9562 UUIDv7 identifiers; `deterministic_import_id()` emits declared UUIDv5 imports.
- `LocalArtifactStore.put|get|head|verify|materialize` validates the declared registered body and typed ID, then separates reference, private binding, and authority. Reads resolve and validate the binding instead of deriving around it.
- `CandidateFreezer.freeze(candidate, root, expected_digest)` requires an authority-owned `EditableSurfacePolicy`, returns an immutable receipt, and stores exact bodies in CAS.
- `FakeCapabilityProvider.issue|resolve` checks digest, audience, operation, resource, provider-owned resource classification, work order, attempt, and expiry, then consumes a one-use token.
- `validate_schemas.py --check|--write|--json` owns registry, current-adapter, conformance, and generated-evidence validation.
- `migrate_legacy.py --dry-run` proposes deterministic envelopes without editing source files.

Public migration evidence reads an explicit committed source manifest and admits only Git-tracked source files. It never discovers `researcher/runs/*`, so local private runs cannot change public output or expose private commitments. Reports bind both exact source-line bytes and canonical source-record bytes. Unexpected implementation failures stop the migration rather than being mislabeled as record quarantine.

Migration groups proposed envelopes by deterministic ID. Conflicting source records quarantine every claimant; byte-distinct inputs with the same canonical legacy identity are represented once and recorded in a deterministic deduplication section. No ambiguous ID is reported as migrated.

## State and failure behavior

Schema lifecycle is `draft -> registered -> active -> deprecated -> retired`. Deprecated schemas remain readable and are not selected by new writers. Unknown kind, unsupported version, stale schema digest, invalid ID, duplicate key, unsafe number, digest mismatch, access denial, unavailable body, candidate mutation, and quarantine are distinct reason codes.

CAS writes use a same-filesystem temporary file, file `fsync`, atomic no-clobber link, existing-object verification, metadata atomic replace, and directory `fsync`. Concurrent writes of the same body are idempotent. A private reader is authorized before the store checks whether a body exists. The digest-level classification is a high-water mark: deduplication can raise it, and all references then require the raised ceiling. `head()` may inspect unavailable metadata, while body reads, verification, materialization, and idempotent writes deny non-available references.

Freeze hashes a UTF-16-sorted manifest of NFC POSIX path, entry type, executable bit, exact byte length, and exact body digest. The actual files must equal `declared_changed_surfaces`, fit the selected editable-surface roots, and avoid locked paths. Empty directories are not artifacts. Links, devices, traversal errors, NFD names, file or directory ASCII case-insensitive collisions, hardlinks, open-time substitution, mutation between passes, stale expected digests, tree size limits, and candidate-ID reuse deny. The receipt binds the candidate record, registry, base freeze policy, editable-surface policy, and production epoch.

## Acceptance criteria

- [x] Bootstrap kinds have registered schemas, owner specs, lifecycle, compatibility, classifications, and exact schema digests.
- [x] Canonical hashing and typed ID behavior are executable and cross-language vectors are committed.
- [x] Unknown kinds, unsupported majors, unknown fields, unsafe numbers, and stale schema files fail closed.
- [x] Current claims, mechanisms, run state, and queue records validate without source rewrites.
- [x] Migration and rollback are deterministic, pure, and quarantine malformed input.
- [x] Artifact reference, private binding, CAS integrity, concurrency, and classification behavior have negative tests.
- [x] Candidate freeze, immutable identity, and clean materialization are implemented before evaluator work.
- [x] Credential-reference and capability-grant contracts have a fake provider and scope/replay fixtures.
- [x] Python and TypeScript consume the same golden corpus and compare to one committed report.

Production credential resolution, hosted storage, workflow events, and searchable candidate experience remain downstream work. This layer defines their portable artifact boundary.
