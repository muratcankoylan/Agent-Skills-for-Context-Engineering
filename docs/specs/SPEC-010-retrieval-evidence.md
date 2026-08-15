# SPEC-010: Retrieval and Immutable Evidence Capture

Status: draft
Revision: 1
Revises: none
Wave: 2
Classification: split
Owners: retrieval agent; evidence steward agent
Depends on: SPEC-003, SPEC-005, SPEC-009

## Decision

Retrieval attempts, captured entity bytes, source captures, and extracted evidence documents will be separate immutable records. Search snippets, resolver probes, remembered text, and mutable URLs remain discovery or identity-resolution aids only. Every downstream claim must resolve to an integrity-verified `SourceCapture` and exact location in an `EvidenceDocument`, or to a citation-only record that states why content could not lawfully or technically be retained.

## Context and current repository touchpoints

The current loop performs bounded standard-library HTTP retrieval with a 1.5 MB cap and a 30-second timeout. Those values remain the default policy while the system adds exact byte semantics, version manifests, extractor identity, location references, restricted-content handling, and reducer-owned state transitions.

## Goals

- Reproduce the exact content made available to reviewers and evaluators.
- Separate network attempt, byte storage, source-version binding, extraction, and model interpretation.
- Detect content changes, duplicates, retractions, incomplete captures, and inaccessible sources.
- Bound transferred bytes, decoded bytes, redirects, assets, retries, time, and storage.
- Keep credentials and provider-sensitive metadata out of portable and public records.

## Non-goals

- Archiving the whole web.
- Circumventing paywalls, robots policy, authentication, or access controls.
- Declaring a source credible because retrieval or extraction succeeded.
- Treating parser or model output as a source assertion without a resolvable anchor.

## Invariants

1. Captured entity bytes are immutable and content-addressed; a re-fetch never overwrites prior bytes or metadata, and no extractor may read them before a successful integrity receipt is accepted.
2. A private `FetchAttemptReceipt` and a portable `SourceCapture` are different records with different disclosure policies.
3. Transfer bytes and decoded entity bytes have separate digests when both are observable. The `ArtifactRef` identifies the exact entity bytes after transfer and declared content codings are decoded once.
4. Extraction records pin the exact input artifact or manifest, parser or model identity, configuration, and output schema.
5. Truncation, missing assets, and parse loss are explicit and fail closed for completeness-sensitive uses. Future repository, PDF/OCR, archive, or model-assisted extractors inherit the same rule only after their isolated contracts activate.
6. Restricted content stays private or is represented by lawful metadata and a citation-only record.
7. Reducers, not retrievers or extractors, apply capture or evidence-document state after validating schema, expected version, authority, work-order fencing, and every required input and output integrity receipt.
8. External content is always treated as data. Instructions embedded in retrieved content cannot change tools, authority, system prompts, or extraction policy.

## Interfaces and data

Define runtime-neutral operations:

```text
Retriever.fetch(source_version_id, request_policy) -> FetchAttemptReceipt + EntityArtifactProposal
IntegrityVerifier.verify(artifact_ref) -> IntegrityResult
CaptureReducer.accept(capture_proposal, integrity_results, expected_version, fencing_token)
  -> SourceCapture
Extractor.extract(verified_source_capture_ref, extraction_policy)
  -> EvidenceDocumentProposal + ExtractedArtifactProposals
EvidenceReducer.accept(document_proposal, output_integrity_results,
                       expected_version, fencing_token) -> EvidenceDocument
```

`FetchAttemptReceipt` is private. It records attempt and work-order identities, fencing token, retriever version, start and end times, redacted request policy, status, redirect count and sanitized redirect evidence, declared and observed media types, transfer-byte count and digest when available, decoded-entity byte count and digest, validators, retry classification, limit decisions, and safe error codes. URLs, query parameters, headers, provider IDs, cookies, and error bodies are normalized or redacted by an allowlist before they can enter logs or exportable artifacts.

`EntityArtifactProposal` carries the decoded entity bytes to the SPEC-003 artifact freezer. The resulting `ArtifactRef` never contains a storage locator; a private validated `StorageBinding` resolves it. A transport digest is evidence about the fetch, not the portable content identity.

`SourceCapture` is the immutable portable binding from one SPEC-009 `SourceVersion` to either one exact entity artifact or a bounded `CaptureManifest`. It is created only after the reducer verifies successful integrity receipts for every referenced artifact. It records capture kind, capture policy digest, completeness and redistribution status, fetch-receipt reference, artifact references, byte semantics, safe citation metadata, predecessor capture, and the accepted integrity-receipt digests. A `304 Not Modified` receipt creates no new capture: the reducer may link it to a prior capture only after re-verifying that capture's artifact and validator relationship.

`CaptureManifest` names every asset needed for the declared completeness class and enforces limits on asset count, cumulative decoded bytes, nesting, compression ratio, recursion depth, and omitted components. Revision 1 registers bounded text, HTML, and JSON/API manifestation-specific completeness classes rather than one boolean.

`EvidenceDocument` is an immutable accepted extraction result. The extractor emits only a proposal and output artifact proposals. The evidence reducer freezes and verifies those artifacts before it can create the document. The document records structured sections, exact page, line, byte, table, code, or object anchors; references; extraction warnings; completeness class; parent capture and artifact digests; accepted output-integrity receipts; extractor binary or model digest; configuration and schema versions; and transform lineage. Model-assisted extraction is labeled and never changes the underlying capture.

Repository, PDF/OCR, archive, and other untrusted-parser record sketches are non-writable in revision 1. A separate post-SPEC-014 specification or digest-linked amendment must define their isolation, completeness, object/page relationships, parser identity, resource limits, and evidence fixtures before registration or activation.

## Limits and isolation

Request policies independently cap redirects, requests, transfer bytes, decoded entity bytes, decompression ratio, manifest assets, manifest bytes, extraction outputs, retries, and wall time. Exceeding any cap produces a terminal or explicitly partial proposal; no truncation is silently marked complete. Nested archives and recursive manifests are disabled unless a bounded policy enables them.

The revision-1 standard-library HTTP and bounded deterministic text, HTML, and JSON extraction path may run as trusted deterministic work. Complex PDF/OCR tooling, repository hooks, archive expansion, or any untrusted parser is excluded from this revision and must later execute through the SPEC-014 ephemeral isolated environment. No extractor receives ambient credentials or network access unless its exact work order grants them.

## State and failure behavior

Reducer projections move `queued -> fetch_attempted -> entity_frozen -> entity_integrity_verified -> captured -> extraction_attempted -> document_frozen -> document_integrity_verified -> extracted`. No transition may skip either integrity gate. Attempt outcomes include `not_modified`, `restricted`, `too_large`, `decompression_limit`, `manifest_limit`, `integrity_failed`, `transient_failed`, `permanent_failed`, `quarantined`, and `unknown`. Retries create new receipts and never alter an earlier attempt. An unknown or ambiguous transport outcome does not create a capture until reconciliation finds and verifies exact bytes.

Partial captures can be used only by policies that explicitly accept their completeness class. Integrity failure quarantines dependent extractions and marks downstream graph records for review; it never rewrites them.

## Implementation sequence

1. Define fetch receipt, entity artifact, capture, manifest, evidence document, and integrity schemas.
2. Wrap the existing bounded HTTP path and implement sanitization, byte-semantics, 304, decompression, pre-extraction integrity, and reducer-fencing tests.
3. Add content-addressed storage plus metadata-only and citation-only restricted records.
4. Add deterministic bounded text, HTML, and JSON extraction only; propose the isolated-extractor follow-on after SPEC-014 is active.
5. Re-fetch a sampled corpus and compare completeness, anchors, and downstream review behavior against the legacy path.

## Migration and rollback

Existing evaluations link to `legacy_unversioned` citation records until evidence is re-retrieved; unavailable bytes never receive invented hashes. Rollback pins a prior retriever or extractor and preserves every receipt, capture, manifest, and extraction. A bad extractor is superseded by a new extraction over the same capture, not by changing old output.

## Observability

Measure attempt and capture success separately; transfer and decoded bytes; decompression ratios; latency; redirects; content changes; 304 reuse; sanitization events; extraction warnings; restricted and citation-only records; completeness classes; retries; limit failures; storage growth; integrity failures; and result differences by retriever and extractor version.

## Verification

- Repeated identical decoded entity bytes deduplicate while preserving distinct fetch receipts.
- Encoded and decoded byte digests cannot be substituted for each other.
- A 304 can reuse only an integrity-verified prior capture with matching validator evidence.
- Redirects, errors, and provider metadata cannot leak secrets through receipts or logs.
- Truncated, decompression-limited, or asset-incomplete captures cannot be marked complete.
- Text, HTML, and JSON evidence retains exact byte/object anchors and declared completeness after refetch.
- Restricted fixtures export only approved metadata and citations.
- Corrupted stored bytes fail integrity verification and invalidate dependent future use.
- An extractor cannot start with a missing, failed, stale, or mismatched capture-integrity receipt, and a corrupt extracted artifact cannot become an `EvidenceDocument`.
- Prompt-like text in a source cannot expand extractor capabilities or alter policy.

## Acceptance criteria

- [ ] Fetch receipts, entity bytes, source captures, manifests, and evidence documents are mechanically distinct.
- [ ] Reviews cite an integrity-verified capture, exact location, and extractor lineage.
- [ ] Resolver probes and search snippets cannot satisfy evidence requirements.
- [ ] Transfer, decoded, decompressed, manifest, request, retry, and time limits fail closed.
- [ ] Secrets and unsafe provider metadata are excluded from portable records and structured logs.
- [ ] Restricted, partial, failed, and unknown outcomes have typed usable reason codes.
- [ ] Complex PDF/OCR, repository, archive, and untrusted-parser paths are unregistered and non-writable pending a post-SPEC-014 contract.
- [ ] All canonical capture transitions are reducer-owned and fencing-validated.
- [ ] Capture integrity precedes extraction, and output integrity precedes canonical evidence-document creation.

## Pull-request evidence

Attach schema goldens, sanitized fetch receipts, encoded-versus-decoded fixtures, 304 reuse and corruption tests, decompression and manifest-limit failures, bounded text/HTML/JSON extractor goldens, restricted export, prompt-injection non-interference test, negative unregistered-extractor fixtures, and legacy-link migration report.
