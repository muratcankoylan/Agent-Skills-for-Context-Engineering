# SPEC-010: Retrieval and Immutable Evidence Capture

Status: draft
Wave: 2
Classification: split
Owners: retrieval agent; evidence steward agent
Depends on: SPEC-009

## Decision

Retrieval will create immutable, content-addressed source snapshots and structured extraction records before any model review. Search snippets, remembered text, and mutable URLs are discovery aids only. Every downstream claim must resolve to an exact snapshot or to a citation record that explains why raw content cannot be retained.

## Context and current repository touchpoints

The current loop performs bounded standard-library HTTP retrieval and source evaluation. It has a 1.5 MB cap and 30-second timeout. Those safeguards remain default policy while the system adds version capture, extractor identity, location references, and license-aware storage.

## Goals

- Reproduce the exact evidence shown to reviewers and evaluators.
- Separate retrieval, parsing, extraction, and model interpretation.
- Detect content changes, duplicates, retractions, and inaccessible sources.
- Bound bytes, time, redirects, retries, and storage.

## Non-goals

- Archiving the whole web.
- Circumventing paywalls or access controls.
- Declaring a source credible because retrieval succeeded.

## Invariants

1. Snapshot bytes are immutable and keyed by a cryptographic digest.
2. HTTP and provider receipts retain final URL, status, time, content type, byte count, validators, and redirect chain.
3. Extraction records name parser version and exact input digest.
4. Truncation, missing pages, OCR, or parse loss is explicit.
5. Restricted content stays private or is represented by lawful metadata and citations.
6. Re-fetch never overwrites an earlier version.

## Interfaces and data

Define:

```text
Retriever.fetch(source_id, version_hint, policy) -> FetchReceipt
SnapshotStore.put(bytes, classification) -> SnapshotRef
Extractor.extract(snapshot_ref, extractor_version) -> EvidenceDocument
Verifier.verify(snapshot_ref) -> IntegrityResult
```

`SourceSnapshot` records source and version IDs, retrieval time, request policy, response metadata, content digest, a raw-body `ArtifactRef`, redistribution status, and completeness. The portable snapshot never contains a storage locator; only the private SPEC-003 `StorageBinding` resolves that artifact reference to bytes. A final source URL remains response and citation metadata, not artifact storage authority. `EvidenceDocument` records structured sections, page or line anchors, tables, code references, references, extraction warnings, and parent digest.

PDFs preserve page anchors. Repository evidence pins commit and paths. Dynamic API results retain query parameters and response IDs. A manifest can group multiple assets required to understand one source.

## State and failure behavior

Retrieval moves `queued -> fetching -> captured -> extracted -> integrity_verified`, with `not_modified`, `restricted`, `too_large`, `transient_failed`, `permanent_failed`, or `quarantined`. Retries never alter the prior receipt. Partial content is not silently promoted to complete.

## Implementation sequence

1. Wrap existing HTTP retrieval behind the interface and capture receipts.
2. Add content-addressed storage and metadata-only restricted records.
3. Add HTML, text, JSON, PDF, and Git repository extractors with version manifests.
4. Create integrity and completeness checks.
5. Re-fetch a sample corpus and compare model review changes.

## Migration and rollback

Existing source evaluations link to a `legacy_unversioned` record until re-retrieved. Do not invent hashes for unavailable evidence. Rollback keeps snapshots and returns the loop to prior extraction while recording the older extractor version.

## Observability

Measure retrieval success, bytes, latency, redirects, content changes, extraction warnings, restricted captures, truncation, retry causes, storage growth, and integrity failures.

## Verification

- Repeated identical content deduplicates while preserving receipts.
- Changed content creates a new version and supersession edge.
- A truncated PDF cannot be marked complete.
- Repository evidence resolves to an exact commit after the default branch moves.
- Restricted fixtures export metadata only.
- Corrupted stored bytes fail integrity verification.

## Acceptance criteria

- [ ] Reviews can cite exact source locations and input digests.
- [ ] Search snippets cannot satisfy evidence requirements.
- [ ] Retrieval and extraction versions are independently recorded.
- [ ] Existing byte and timeout caps remain enforced or explicitly overridden per source.
- [ ] Restricted and failed sources have usable reason codes.
- [ ] Snapshot integrity is checked before context compilation.

## Pull-request evidence

Attach retrieval receipts, content-change and deduplication examples, extractor goldens, restricted-source export, corruption test, and legacy-link migration report.
