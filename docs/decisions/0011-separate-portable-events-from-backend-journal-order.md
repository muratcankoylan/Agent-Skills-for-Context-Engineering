# ADR-0011: Separate portable events from backend journal order

- Status: proposed
- Date: 2026-08-11
- Spec: SPEC-004

## Context

The organization needs one durable event identity across the local harness,
future Hermes and Temporal adapters, public projections, and deterministic
repair. SQLite must also assign a total acceptance order, receipt time, and
hash-chain link. Treating those backend fields as part of portable event
identity would make retry and migration depend on the store that happened to
accept the event.

The existing research loop is file-authoritative and can crash after replacing
`run-state.json` but before publishing an outbox item. A random native event ID
created after that replacement cannot be reconstructed. At the same time,
wiring a shadow bridge before proving append, idempotency, projection, and
recovery would combine two independent failure domains.

## Decision

Only `OrganizationEvent` and its projection-sufficient
`ResearchRunTransition` payload are registered portable SPEC-004 records in
this slice. An event carries its occurred time, subject version, actor and
authority snapshot, channel-scoped idempotency-key digest, correlation and
causation, repository context, canonical payload digest, and an optional
locator-free detail reference.

`JournalEntry` and `AppendReceipt` remain backend-owned interface values. The
SQLite store assigns sequence, receipt time, previous-entry hash, and entry
hash without changing portable event bytes. Exact duplicate delivery returns
the original immutable receipt before optimistic-concurrency evaluation.

SQLite is the first local backend. It stores exact canonical event bytes in a
bounded BLOB, uses WAL, `synchronous=FULL`, foreign keys, STRICT tables, one
connection per operation, and `BEGIN IMMEDIATE` for writes. Append, subject
version, and chain-head movement are one transaction. Reads, append, replay,
backup, and restore fail globally when the journal chain, canonical bytes,
duplicated indexes, schema ledger, control tail, or subject-version index is
inconsistent.

The research-run projector keeps projection data rebuildable. Cross-event state
divergence quarantines only that subject while the immutable journal remains
readable. Its state digest excludes rebuild clocks and binds separately to the
source sequence and entry hash.

Implementation proceeds in two slices. Slice 004A proves the portable contract,
store, projector, and recovery without changing current run authority. Slice
004B atomically replaces file state first, derives every mirror event from the
append-only history slot and fixed constants using UUIDv5, repairs any missing
suffix through a private outbox, and compares the projection with the file.
The bridge cannot emit a distinct repair event on the research-run subject;
repair must deliver the exact intended transition bytes.

The fixed file-history construction is part of the contract, not adapter
configuration. It uses namespace `b5a8ef43-d10b-5dd9-9406-31c558426e6d`,
UUIDv5 name `research-run-transition/v1:<run_id>:<history_index>`, reserved
scope `research_loop_file_shadow`, and idempotency preimage
`research-run-transition-idempotency/v1:<run_id>:<history_index>`. All
file-derived events use `file_state_history`; import, mirror, and repair are
delivery modes outside portable identity. The fixed actor is
`research-loop-file-shadow` / `legacy_file_bridge`; authority records that
legacy authority was unavailable, classification is private operational, and
repository/detail fields are null. Native events cannot occupy the reserved
scope.

Append does not rescan the whole journal under its writer lock. Full integrity
audits occur on open, explicit verification, reads, replay, and backup. The
append transaction verifies the digest-pinned schema fingerprint and migration
ledger, the control and SQLite tails, the current subject tail, and the new
entry. This preserves bounded writer-lock duration while a detected historical
corruption remains a global halt.

Backup and restore use private generation directories. Each backup generation
contains only a database and receipt, with `0700`/`0600` permissions, and is
published by one directory rename after file and directory fsync. Restore
verifies a closed generation and publishes a distinct fresh live generation,
which prevents stale sibling WAL or SHM files from changing verified state.

## Consequences

- Portable event identity is runtime-neutral; SQLite sequence is not.
- Projection replay never depends on CAS availability because the minimal
  state transition is inline. Larger or classified detail can remain behind a
  registered artifact reference.
- Full integrity verification is linear in journal length in this first local
  slice, but append is bounded to schema and tail state so building a journal
  is not quadratic. Checkpointed historical verification requires an
  authenticated external anchor before it can provide the same guarantee.
- The SHA-256 chain is tamper-evident, not authenticated. A privileged writer
  who can rewrite all database bytes can forge another chain.
- WAL requires a local filesystem and permits one writer. A hosted or
  distributed backend must implement the same narrow EventStore contract
  rather than sharing this database over a network filesystem.
- ADR-0011 and SPEC-004 remain non-authoritative proposals until the required
  human-merged lifecycle transitions. Shadow parity and public projection are
  still required before SPEC-004 can become verified.

## Alternatives considered

- Register `JournalEntry`, `AppendReceipt`, and a separate authority record as
  portable artifacts now. Rejected because it would expose backend order as an
  interchange contract and expand SPEC-000 before a consumer requires that
  persisted authority identity.
- Store only an artifact reference to transition detail. Rejected because a
  projector could no longer replay when private CAS detail is unavailable.
- Use UUIDv7 for file-shadow events. Rejected because a crash after the file
  commit can lose the only copy of the random identity.
- Wire file mirroring in the same implementation step as the store. Rejected
  because crash-repair defects could be misdiagnosed as journal defects and
  would make rollback less local.
- Introduce Kafka, Temporal persistence, or a hosted database immediately.
  Rejected because the current bounded organization needs inspectable local
  durability, not distributed operations.

## Verification

Python and TypeScript reject payload, routing, provenance, authority, and
causation mismatches with matching stable codes. Store tests cover exact
duplicates after subject advancement, identity and idempotency collisions,
competing writers, process death before commit, failure after commit, canonical
size limits, filtered cursor progress, immutable-row triggers, database and
index corruption, subject-local projection quarantine, deterministic replay,
transactional rebuild rollback, online backup, receipt-bound fresh restore,
and post-restore append. Deterministic evidence is committed under
`researcher/event_journal/generated/`.
