# ADR-0004: Make schemas, identity, and frozen bytes runtime-neutral

- Status: accepted for proposal
- Date: 2026-08-10
- Spec: SPEC-003

## Context

The repository already has useful JSON, JSONL, Markdown-frontmatter, and directory contracts. They are validated by different scripts, use paths or semantic keys as identity, and do not share canonical serialization or compatibility rules. Hermes, Temporal, and later executors cannot safely exchange those records if chat state or adapter-specific storage becomes the implicit contract.

## Decision

Durable cross-runtime records use Draft 2020-12 schemas registered with exact file digests. The bootstrap registry contains only contracts needed before the event journal and evaluator exist: the registry meta-schema, artifact envelope and reference, private storage binding, SPEC-002 export records, minimal candidate and freeze receipt, credential reference, capability grant specification, and four legacy adapters.

Event, work-order, command, source, context-package, evaluation, promotion, execution-environment, and contribution schemas are intentionally absent. Their owning specs must register them after their invariants are implemented. This avoids making draft architecture permanent through premature schemas.

JSON record digests use `jcs-rfc8785-integer-v1`, an executable subset of [RFC 8785](https://www.rfc-editor.org/rfc/rfc8785.html). It admits null, booleans, strings without lone surrogates, arrays, objects, and integers in the exact ECMAScript range. Floats, negative zero, duplicate keys, non-finite numbers, and unsafe integers deny. Blob digests remain SHA-256 over exact bytes with no text normalization.

New typed identifiers use `<prefix>_<UUIDv7>` following [RFC 9562](https://www.rfc-editor.org/rfc/rfc9562.html). Deterministic legacy imports use a fixed UUIDv5 namespace and declare `id_origin: legacy_import`. Existing claim, mechanism, source, and run keys remain aliases; migration does not rewrite their files.

An `ArtifactEnvelope` is not an untyped JSON bag. Its declared target resolves through the same registry. A native envelope payload is the complete target record. A legacy-import payload names the matching legacy adapter and semantic key, carries the canonical source digest and source record, and binds both through `input_digests` and `aliases`. Rollback revalidates the embedded source through that adapter before returning it.

`ArtifactRef`, `StorageBinding`, and authority are separate concepts. Portable references contain no private locator. A private binding maps a reference to storage and is validated on every read. Read authority is supplied independently and checked before existence. Possessing an ID or reference is never read permission. A reference declares whether its target ID is native or a legacy import, and validators resolve the target registry entry before accepting its kind, version, or prefix. A writer must validate the exact registered JSON body, its typed ID, kind, version, and classification before CAS publication.

Candidate freezing copies exact file bytes into the local CAS, hashes a UTF-16-sorted tree manifest, applies an explicit NFC POSIX and ASCII case-insensitive path profile, enforces an authority-owned editable-surface policy, and emits an immutable receipt before evaluation. A frozen candidate ID cannot be rebound; a revision receives a new candidate ID. Snapshot traversal, open-time identity, file count, and total bytes all fail closed.

## Consequences

- Python and TypeScript must produce the committed canonical vectors and schema results exactly.
- Current claims, mechanisms, run state, and queue records remain canonical in their existing formats during migration.
- Deterministic import-ID collisions quarantine every conflicting claimant; exact canonical duplicates are represented once and remain visible as deduplicated inputs.
- Private CAS objects and bindings are ignored runtime state. Public Git artifacts remain ordinary files.
- The fake capability provider proves scope and replay behavior without making a production secret broker part of this wave. Resource classification comes from provider-owned metadata, not the caller. Its grant digest is integrity-only, not issuer authentication; SPEC-024 owns real identity and credential resolution.
- SPEC-004 stores artifact references and events, not another blob body. SPEC-010 adapts retrieval snapshots to this CAS. SPEC-018 extends candidate history, and SPEC-019 promotes the exact freeze receipt.
- The integer-only profile is narrower than general RFC 8785. A future float-bearing schema requires a new canonicalization profile and cross-language vectors rather than silently broadening this one.

## Alternatives considered

- Hash ordinary `json.dumps` or `JSON.stringify` output. Rejected because key sorting and accepted numeric domains differ across runtimes.
- Put locators in `ArtifactRef`. Rejected because portable references would expose private topology and be confused with authority.
- Register every planned organization record now. Rejected because later specs have not made those contracts executable.
- Make paths the artifact key. Rejected because moves, public projections, and CAS materialization would change identity.
- Rewrite all JSONL records into envelopes immediately. Rejected because it would create a high-risk flag day and damage append-only history.

## Verification

The conformance suite covers duplicate keys, unsafe numbers, UTF-16 astral ordering, combining Unicode, control characters, typed-ID version and prefix checks, impossible timestamps, schema digest drift, current legacy records, pure migration and rollback, concurrent CAS writes, tampering, binding mismatch, classification high-water behavior, authority-before-existence, candidate path attacks, open-time substitution, editable surfaces, bounded snapshots, exact no-clobber materialization, and one-use capability scope.
