# SPEC-004: Event Journal and State Projections

Status: draft
Wave: 1
Classification: split
Owners: orchestration steward agent; human maintainer
Depends on: SPEC-003

## Decision

The organization will record normalized immutable events before projecting operational state. A portable registered `OrganizationEvent` is distinct from the backend-assigned `JournalEntry` sequence that orders accepted writes. The first backend is a local SQLite event store in WAL mode behind a small `EventStore` interface; selected public events are exported as digested JSONL. Repository artifacts remain canonical for public knowledge and releases. Existing `run-state.json` remains authoritative for its current lifecycle during a bounded migration, with every transition mirrored and verified against the journal.

## Context and current repository touchpoints

`researcher/scripts/research_loop.py` controls the current run lifecycle, while `loop_common.py`, queue files, loop events, reports, and launchd jobs provide local durability. They work for a single file-based loop but cannot consistently explain GitHub reviews, human commands, multiple executors, late results, or reconstructed status.

## Goals

- Record causes, actors, inputs, and versions for every meaningful transition.
- Rebuild queue, run, PR, decision, outbox, and status projections.
- Tolerate duplicate and out-of-order external events.
- Preserve a public audit trail without publishing private payloads.

## Non-goals

- Event-sourcing all repository file contents.
- Introducing Kafka or a hosted database.
- Treating the event log as a substitute for Git history or source snapshots.

## Invariants

1. Events are append-only; correction is another event.
2. `event_id` and channel-specific idempotency keys are unique.
3. A projector can be deleted and rebuilt without changing source events.
4. Events reference large or classified payloads by ID and digest.
5. `occurred_at` and `received_at` are distinct.
6. A transition is rejected if expected subject version does not match.
7. External webhooks trigger reconciliation; they are not accepted as final truth.

## Interfaces and data

Define:

```text
EventStore.append(event, expected_subject_version) -> AppendReceipt
EventStore.read(after_sequence, filters) -> EventPage
EventStore.subject_version(subject_id) -> integer
Projector.apply(event) -> ProjectionDelta
Projector.rebuild(to_sequence?) -> ProjectionDigest
```

An `OrganizationEvent` is a registered target record that can be wrapped by or referenced from the SPEC-003 `ArtifactEnvelope` and `ArtifactRef` contracts. It includes event type, occurred time, subject ID and version, idempotency key, actor, authority decision, correlation and causation, repository commit, optional PR and head SHA, payload reference and digest, and classification. It never contains a storage locator. `JournalEntry` adds the journal-global sequence, received time, and prior-entry/hash-chain binding after the event is accepted; backend ordering is not part of the portable event identity.

The initial active payload contracts cover the existing research-run lifecycle and import/repair events only. Event names use past tense, such as `research_run.retrieved`. Source, work-order, attempt, context, evaluation, candidate, pull-request, command, feedback, notification, budget, policy, deployment, and organization-version namespaces are reserved for their owner specifications; SPEC-004 does not accept untyped placeholder payloads for them.

The database lives under ignored private runtime state. Schema and migrations are public. A public exporter writes only allowlisted event fields and refers to merged public artifacts.

## State and failure behavior

Append plus subject-version increment and journal-chain update is one transaction. Projectors track their last sequence and may replay independently. A valid registered event that a projector does not support quarantines that subject and stops only that projection. Schema-invalid events never enter the journal. A stored event digest mismatch, broken sequence, or hash-chain corruption is journal-global integrity failure and stops all append and replay until operator recovery. Database backup uses SQLite's consistent backup interface.

## Implementation sequence

1. Implement schema, append, read, uniqueness, and optimistic concurrency.
2. Mirror current research-run transitions without changing their authority.
3. Build run and loop-status projections and compare them with current files.
4. Add command, PR, work-order, and outbox projectors as their specs land.
5. Cut run lifecycle authority to projection only after a full shadow period.

## Migration and rollback

Import the append-only `state_history` transitions of existing runs with deterministic UUIDv5 event IDs and explicit `legacy_import` provenance. Do not import a mutable `run-state.json` snapshot through an immutable SPEC-003 envelope under a stable run ID. During dual operation, file state remains authoritative: transition code writes state atomically, then records a deterministic repairable outbox item, and a repair job closes any journal gap. Rollback disables mirroring, restores file-only operation, and retains journal data for inspection.

## Observability

Expose append latency, last sequence, projector lag, duplicate rate, concurrency conflicts, quarantine count, database size, backup age, and replay digest. Every status view states its source sequence.

## Verification

- Duplicate delivery creates one event effect.
- Out-of-order GitHub fixtures converge after reconciliation.
- Projectors rebuild to identical digests.
- Concurrent version updates yield one success and one typed conflict.
- A killed writer produces no partial event.
- Public export excludes seeded private payloads.

## Acceptance criteria

- [ ] All initial event families validate against registered schemas.
- [ ] Append, subject version, and idempotency are transactional.
- [ ] Run projection matches existing run state throughout shadow operation.
- [ ] Full replay reproduces operational projections.
- [ ] Backup and restore are exercised.
- [ ] Public event export passes SPEC-002.

## Pull-request evidence

Attach schema and migration, replay report, dual-state comparison, duplicate and crash tests, backup/restore transcript, and a redacted public export.
