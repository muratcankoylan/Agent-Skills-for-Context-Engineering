# ADR-0003: Publish allowlisted projections, not redacted private records

- Status: accepted for proposal
- Date: 2026-08-10
- Spec: SPEC-002

## Context

Future research feeds, human feedback, notification destinations, licensed source bodies, and operational traces cannot all be stored in the public repository. A generic redaction pass would be difficult to reason about and could publish private locators, low-entropy source hashes, or nested fields while appearing sanitized.

## Decision

Movement to the public repository creates a new projection artifact through a registered transform. The source remains private or restricted. Rendering accepts exact request fields, source classifications, artifact kinds, transforms, and output prefixes. Unknown routes deny.

Export state is split into immutable records:

- a private `ExportPlan` binds source paths and exact source digests;
- a public `ExportManifest` binds only new projection IDs, transformation digests, output paths, and output digests;
- a private render receipt retains source-to-projection audit data;
- public validation, later approval, merge receipt, correction, and tombstone records point backward rather than mutating earlier records.

Private source digests are deliberately absent from public manifests. Even a cryptographic hash can reveal the presence of a low-entropy private value through guessing. The public projection receives a new opaque ID.

Rendering occurs in a fresh sibling directory and becomes visible through atomic rename only after the complete tree validates. Structural field allowlists and complete-tree closure are the primary boundary. Seeded canaries and high-confidence pattern detectors are supplementary checks, not a universal data-loss-prevention claim.

## Alternatives considered

- Copy and redact arbitrary records. Rejected because unknown and nested fields fail open.
- Publish source hashes for auditability. Rejected because hashes can be existence oracles.
- Put private data on a private Git branch. Rejected because branch visibility is not a durable data classification boundary.
- Make scanning the only control. Rejected because encodings and semantic disclosures cannot be exhaustively detected.
- Mutate one manifest through planned, rendered, and merged states. Rejected because durable artifacts should be immutable and replayable.

## Consequences

- Adding an exportable artifact kind requires a reviewed policy and transform change.
- Public lineage is useful but intentionally does not let a public consumer resolve the private source.
- Real private plans and receipts stay outside Git or under ignored private paths.
- Publishing remains irreversible in practice. Corrections and tombstones supersede public artifacts but cannot undo disclosure.
- SPEC-003 registers these bootstrap records in the common schema and identity system; SPEC-024 later owns production credential and private-storage resolution.

## Verification

Tests cover unknown fields, classification denial, traversal, Unicode/case collisions, symlinks, source mutation, atomic staging, extra files, digest tampering, private manifest fields, plain/hex/base64 canaries, high-confidence credential structures, duplicate JSON keys, policy drift, unsupported output fields, and the restricted citation projection.
