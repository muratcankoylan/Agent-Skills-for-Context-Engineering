# SPEC-004: Event Journal and State Projections

Status: draft
Revision: 1
Revises: none
Wave: 1
Classification: split
Owners: orchestration steward agent; human maintainer
Depends on: SPEC-000, SPEC-001, SPEC-002, SPEC-003

## Decision

Every new journal-native durable state change is accepted only as a registered immutable event and projected deterministically. A portable `OrganizationEvent` is separate from the backend-assigned `JournalEntry` that orders accepted writes. The bounded research-run shadow bridge is an explicit legacy exception: `run-state.json` remains file-authoritative through revision 1, and its already-authorized transitions are mirrored before any journal-dependent downstream effect may consume them. The first backend is local SQLite in WAL mode behind a narrow `EventStore` interface. Repository artifacts remain canonical for public knowledge and releases.

The implementation has two independently reviewable slices. SPEC-004A establishes a generic authorized journal, event-family registry, replay, and backup without changing live run authority. SPEC-004B mirrors the existing file-authoritative research-run lifecycle and proves recovery before any authority cutover.

## Context and current repository touchpoints

`researcher/scripts/research_loop.py` and `run-state.json` currently own research-run transitions. Queue files, loop events, status reports, and launchd jobs provide local durability but do not form one causal record for commands, work, pull requests, late results, or external observations. The journal must generalize that system without converting a mutable snapshot into false immutable history.

## Goals

- Record the cause, trusted actor, authorization, inputs, and versions of every journal-native transition and every mirrored legacy research-run transition.
- Add event families without changing the `OrganizationEvent` major version.
- Rebuild projections from exact journal bytes and a digest-pinned registry.
- Make duplicate delivery, stale writes, partial failure, and corruption explicit.
- Produce public projections without exposing private records or their digests.
- Establish one explicit human-authorized repository and organization baseline so pre-GitHub work never reads ambient `HEAD` or fabricates an accepted-commit guard.

## Non-goals

- Event-sourcing repository file contents.
- Introducing a hosted database, queue, or consensus system.
- Treating a webhook, model output, artifact reference, or caller-authored authority claim as a state change.
- Replacing `run-state.json` authority in SPEC-004A or SPEC-004B.

## Invariants

1. Events and journal entries are append-only; a correction is a later typed event.
2. Every event family resolves through an immutable registry version and exact registry digest before append or replay.
3. The store derives the actor from a trusted principal and accepts authorization separately; an event cannot authorize itself.
4. A native append requires a matching allow decision and runtime grant. A legacy import requires a distinct, narrowly scoped migration grant and is never represented as a native allow decision.
5. Subject version, idempotency identity, event bytes, and journal-chain update commit in one transaction. A batch is all-or-nothing across its subjects.
6. Reusing an idempotency identity with different normalized event bytes is a collision, not a duplicate.
7. A projector can be deleted and rebuilt without changing source events.
8. State-changing projection fields are inline and typed. An optional detail reference is evidentiary and cannot be required to reconstruct core state.
9. `occurred_at`, backend `received_at`, and external observation time remain distinct.
10. A stored-event digest mismatch, broken sequence, or hash-chain mismatch stops append and replay until explicit recovery.
11. The store canonicalizes and strict-parses caller input into a detached immutable value before validation; later mutation of the caller's object cannot alter indexed fields or receipts.
12. Integrity verification and every dependent read use one explicit SQLite read snapshot. A page high-water mark, returned rows, cursor, control tail, and subject versions cannot come from different concurrent commits.
13. Migration digests bind the exact in-memory SQL bytes that execute, and the runtime compares the complete audited SQLite schema fingerprint rather than a trigger-name subset.
14. The first accepted-repository pointer and organization epoch are created exactly once by a human-authorized bootstrap event. Later work binds that immutable state; an absent baseline blocks mutation.

## Interfaces and data

The public contracts are:

```text
EventStore.append_native(proposal, expected_subject_version,
                         trusted_principal, policy_decision, runtime_grant)
  -> AppendReceipt
EventStore.append_import(proposal, expected_subject_version,
                         trusted_principal, migration_grant)
  -> AppendReceipt
EventStore.append_batch(batch_id, ordered_requests_digest, requests, trusted_principal,
                        per_request_authorization_inputs, batch_runtime_grant)
  -> BatchAppendReceipt
EventStore.seal_native_append(proposal, expected_subject_version,
                              trusted_principal, policy_decision, runtime_grant)
  -> PendingAppendTicket
EventStore.consume_native_ticket(ticket_id, exact_event_digest, durable_file_proof)
  -> AppendReceipt
OrganizationBootstrap.initialize(request, trusted_principal,
                                 policy_decision, runtime_grant)
  -> RepositoryAcceptanceBaseline + OrganizationEpoch | BootstrapConflict
EventStore.read(after_sequence, limit, filters) -> EventPage
EventStore.subject_version(subject_id) -> integer
Projector.rebuild(registry_digest, to_sequence?) -> ProjectionReceipt
```

`EventFamilyRegistry` is a registered immutable artifact. Each family entry pins:

- family name and major version;
- owner specification and subject kind;
- payload schema kind, version, and schema digest;
- permitted classifications;
- permitted reference fields and direct target kinds;
- required constitution action and resource;
- whether the family is native, import-only, or both; and
- projector compatibility and public-export transform, if any.

`OrganizationEvent` is generic. It contains a typed event ID, family and registry digest, subject ID and next subject version, occurred time, scoped idempotency-key digest, correlation and causation IDs, repository and organization versions when applicable, a projection-sufficient payload and payload digest, optional detail reference, classification, trusted actor snapshot, and authorization snapshot. Event-family dispatch performs the payload validation; no untyped placeholder payload is accepted.

`RepositoryAcceptanceBaseline` is the pre-SPEC-007 accepted-pointer seed and `OrganizationEpoch` is the pre-SPEC-019 organization-version seed. One immutable `RepositoryAcceptanceBootstrapRequest` binds repository identity, default branch and Git object format; exact commit and tree; a local exact-Git observation receipt; SPEC-001 source-tree and inventory digests; expected absent pointer and version zero; epoch identity and version zero; current constitution and authority-vocabulary digests; authenticated human principal; stable operation key; and request digest. Only `initialize_repository_acceptance/repository_acceptance` may create it. The reducer verifies that the commit and tree are reachable from the named local default-branch ref and that the request is current, then atomically writes the baseline pointer, bootstrap event, and organization epoch. Exact replay returns the first receipt; any second initialization, stale ref, changed bytes, nonhuman actor, wrong policy/grant, or missing inventory proof writes nothing. This is an explicit human acceptance fact, not an inference from ambient `HEAD`.

SPEC-005 and SPEC-006 bind this baseline pointer and epoch before SPEC-007 is active. SPEC-007 adopts the same pointer and becomes the sole ongoing repository-acceptance reconciler; it does not import a second epoch-zero record. SPEC-019 later advances organization versions from the exact bootstrap epoch when a qualifying reconciled merge is promoted. An external proposal, release, or deployment additionally requires the relevant later owner contract; possession of the baseline grants no GitHub, promotion, or production effect.

The store constructs the trusted actor and authorization snapshots from the separate inputs after checking that all of the following agree: authenticated principal, action, resource, subject, organization and constitution versions, policy context digest, work order and attempt when present, grant audience and operations, expiry, and event-family registry digest. The capability value is never stored. A caller-supplied actor or decision snapshot is rejected. Import snapshots record the migration grant and declared legacy provenance without inventing an historical policy decision.

`JournalEntry` is backend-owned. It adds the global sequence, received time, prior-entry digest, entry digest, transaction ID, and accepted event bytes. Backend sequence is not part of portable event identity. Batch order is the request order and all causation references must resolve to an existing event or an earlier event in that batch.

`BatchPurposeRegistry` is a digest-pinned extension registry. Each purpose entry names its owner specification, allowed event families and classifications, maximum entries and bytes, required atomicity, identity derivation profile, and authorization requirements. A caller-selected `batch_id` must resolve to a typed `BatchIdentity` derived from the exact batch-purpose-registry digest, registered purpose, purpose version, producer, and stable operation ID; it is not an arbitrary UUID or a grant. Adding a purpose does not add an append API or relax per-event authorization.

`BatchAppendReceipt` is persisted in the same transaction as its entries and binds the validated batch identity, exact batch-purpose-registry digest, purpose version, canonical digest of the ordered requests including their expected versions, entry order, and every append receipt. After authenticating that the caller may observe that batch, exact `batch_id`, registry digest, and request-digest redelivery returns the original receipt before mutable policy, grant, or subject-version checks. Registry drift is not an exact replay: reusing the ID with a different registry digest, identity field, or ordered byte is `BATCH_IDEMPOTENCY_CONFLICT` and writes nothing.

`PendingAppendTicket` is a private store-owned, non-transferable record for the SPEC-004B file-first bridge. Sealing it performs the native policy and grant checks once and binds the detached exact event bytes, expected subject version, transition identity, principal, authorization snapshot, and one allowed file-proof contract. It is not an accepted organization event and cannot be used for any other bytes. Consumption requires the matching durable file proof and atomically appends the bound event once; exact retry returns the original receipt. The store retains an unresolved ticket across process restart and original grant expiry until it is consumed or an authorized reconciliation proves the file transition absent and cancels it.

An optional detail reference must resolve directly to an allowed domain artifact and obey classification high-water rules. It cannot target `ArtifactRef`, `ArtifactEnvelope`, `StorageBinding`, an event, a registry record, a credential reference, or a capability-grant record. This local restriction remains mandatory even if a broader SPEC-003 erratum later centralizes the rule.

SPEC-004A cannot activate until SPEC-003 negative fixtures also reject an `ArtifactRef` targeting itself or another reference record and a lower-classification envelope around a higher-classification target or storage binding. Event validation applies the same direct-target and classification checks to every reference field declared by a payload family; nesting a forbidden meta-reference inside a payload is not an escape.

The database and native events live in ignored private runtime state. Public output is a new SPEC-002 `public_derived` projection with an allowlisted schema, transform, identity, and output digest. It contains no private source digest, locator, grant, decision context, or private actor data.

## State and failure behavior

Validation order is deterministic. The store first strict-parses and detaches bytes, resolves the registry and schema, validates references, authenticates the principal, and verifies journal-tail health. It then looks up event, idempotency, or batch identity and compares exact canonical bytes. A matching prior append returns its original receipt after a receipt-visibility check, even when its original mutation grant expired or the subject advanced. A collision fails. Only an unseen identity proceeds to current policy and grant evaluation, expected-version checks, and transactional append. A same-key/different-bytes request, stale version, denied policy, invalid grant, unsupported family, or unavailable reference receives a distinct reason code and writes no event.

Journal and projection storage use separate SQLite files or immutable generations. Projectors persist their last sequence, source-chain digest, registry digest, projector version, and projection digest. An unsupported but valid family quarantines only the affected projector or subject; it does not corrupt the journal. Missing, malformed, or corrupt projection storage raises a rebuild-required projector error and cannot make an otherwise valid journal read report global corruption. Journal integrity failure is global and durably latches an operator halt across process restart in a minimal private safety ledger outside the halted journal. The latch preserves the halted generation identity, last fully verified sequence and chain digest, observed tail bounds, detection receipt, and every later recovery attempt; a failed repair cannot erase the best evidence of a possible suffix.

Normal append cannot clear that latch. Recovery first repairs or restores into a separately staged generation and completes a full audit. A one-use `JournalRecoveryTicket` under `recover_journal/event_journal` binds the halted generation and last-known verified tail, staged generation and recovered cutoff/tail, exact continuation proof, audit receipt, recovery class, authenticated human principal, current policy decision, and runtime grant. `continuous_reopen` is valid only when the staged chain proves exact continuity through every accepted sequence up to at least the halted last-known tail and no known suffix is omitted. A dedicated recovery transaction is the sole bypass: it verifies the external latch and ticket, appends `journal.reopened` as the first permitted new event, and returns a receipt. The safety ledger then marks the latch cleared against that receipt; a crash between journal commit and ledger acknowledgement reconciles idempotently from the exact recovery event.

An older backup or repaired prefix without a verified continuation cannot use `continuous_reopen` and cannot claim that accepted events were preserved. The halted generation remains immutable. A `disaster_prefix` path requires the distinct human-only `authorize_disaster_recovery/event_journal` action; ordinary `recover_journal` authority cannot publish it. That path creates a distinct recovery generation and requires a `DisasterRecoveryDeclaration` in the safety ledger binding recovered cutoff/hash, halted last-known tail/bounds, explicit possible-loss interval, recovery-point objective class, missing-continuation evidence, affected subject/effect inventory, reconciliation incident, and exact SPEC-025 deployment-pointer authorization. Its first event imports that declaration and marks the organization degraded; it never rewrites or silently clears the lost interval. Operational activation remains blocked until SPEC-025 supplies the backup-generation barrier, deployment pointer transition, and external-effect reconciliation. SPEC-004 tests the state machine and bytes but does not present a prefix restore as ordinary healthy reopen.

Detection, failed-audit, restore, disaster-declaration, and emergency-operation receipts remain in the safety ledger and are imported into the journal only after reopening. Full integrity scans run on open, audit, replay, and backup; the append transaction validates the schema and migration fingerprints, journal tail, affected subject tails, and new entries rather than rescanning history.

Backup uses SQLite's consistent backup interface. A backup is a closed private generation containing the journal database and digest-bound receipt with exact sequence and chain cutoff; projections are disposable and rebuilt. Restore verifies it in a separate staging generation so a database is never paired with stale WAL files. Publication as a continuous live generation requires exact continuation through the recovery ticket. An isolated older generation remains a test/inspection artifact unless SPEC-025's explicit disaster path is authorized.

## Implementation sequence

### SPEC-004A: generic journal

1. Register `EventFamilyRegistry`, generic `OrganizationEvent`, authorization snapshot, journal receipt, repository/organization bootstrap records, and the initial research-run payload family.
2. Implement native, import, pending-ticket, batch-identified, and one-time bootstrap atomic append with a fake trusted-principal and capability provider.
3. Implement read, subject versions, exact duplicate handling, deterministic replay, corruption detection, and a research-run test projector.
4. Exercise crash-safe backup and restore. Do not connect the store to live transition code.

### SPEC-004B: file-authoritative shadow mirror

1. Add a per-run lock around every file transition and mirror operation.
2. Extend each new `state_history` entry with every field needed to reconstruct the exact event plus its pre-sealed pending-ticket ID: family, registry version and digest, event and idempotency identities, subject version, occurred time, actor and import provenance, authorization snapshot, organization and constitution versions, correlation and causation, classification, repository context, projection payload and digest, and optional detail reference. The capability value is never written.
3. While holding the lock, validate the old state, ask the store to seal the exact native append ticket, append the complete history record, write a same-directory temporary file, `fsync` it, replace the state file, and `fsync` the directory. Only after the file is durable may the ticket be consumed. If file publication fails, the bridge reconciles and cancels the unused ticket.
4. Repair scans history under the same lock and consumes a missing ticket using the exact event digest and durable file proof. It never synthesizes fields from current mutable state or reauthorizes the event under a later grant.
5. Mirror initialization and all legal transitions. `closed` is terminal and may be reached from any valid non-closed state with an explicit verdict and reason.
6. Compare file and projection state for a measured shadow period and render the allowlisted public event projection.

Authority remains file-first after SPEC-004B. Moving transition authority to the journal requires a later accepted amendment with migration evidence.

A file transition with an unconsumed pending ticket is durably accepted only in the legacy file domain. Scheduler, command, PR, notification, and other journal-dependent reducers treat that run transition as `mirror_pending` and cannot launch downstream effects until the exact mirror receipt exists. Repair closes the gap; it does not create a second transition.

## Migration and rollback

Existing history is imported with declared deterministic UUIDv5 identities, fixed import constants, and a narrow migration grant. Repository acceptance is not inferred from that history: an authenticated human creates the one bootstrap baseline from exact Git and SPEC-001 inventory evidence. A mutable `run-state.json` snapshot is never wrapped as immutable history under a stable run ID. Entries that lack enough information for deterministic reconstruction are quarantined or handled by a versioned legacy adapter; missing facts are not guessed.

The state file plus its store-owned pending ticket form the shadow bridge. A crash after the durable file replace but before journal append leaves a repairable, already-authorized gap; a crash before durable replace leaves no accepted transition and an unused ticket that reconciliation may cancel. Rollback disables mirroring, reconciles every ticket, retains the journal for inspection, and continues file-only operation.

## Observability

SPEC-004A exposes sequence and subject counts, database and schema versions, replay digest, projection source sequence, quarantine count, integrity state, and backup receipt age. SPEC-004B adds mirror gaps, repair outcomes, and file/projection divergence. SPEC-008 owns durable latency, cost, cardinality, and alert policy.

## Verification

- Unknown families and family/schema digest drift fail before append.
- A forged inline actor or allow decision cannot produce an accepted event.
- Wrong principal, action, resource, work order, attempt, expiry, or grant operation fails independently.
- Repository bootstrap accepts one exact human-authorized current commit/tree and organization epoch; ambient `HEAD`, nonhuman initialization, stale ref, second initialization, changed-byte replay, or missing SPEC-001 proof cannot create or move the pointer.
- Exact redelivery has one journal effect; same idempotency identity with different bytes is quarantined.
- Lost acknowledgements for single and batch append return the original receipts after subject versions advance; batch-ID/request-digest collisions fail.
- Batch-purpose-registry drift changes `BatchIdentity`; replay under a different registry digest is denied without reinterpreting the original purpose.
- Concurrent subject updates yield one success and typed conflicts; a multi-subject batch is fully atomic.
- Replay is byte-deterministic across a fresh projection database.
- Corrupt projection tables rebuild; corrupt journal bytes stop append and replay.
- A journal halt survives reopen and cannot be cleared without a successful full audit and authorized clear; projection-only corruption never latches it.
- An old backup or missing-continuation fixture cannot ordinary-reopen; continuous recovery proves the complete known chain, while disaster-prefix simulation preserves the halted generation and records an exact possible-loss interval without claiming event preservation.
- Ordinary `recover_journal` authority cannot publish a lossy prefix; only the distinct disaster action plus declaration, incident, and SPEC-025 transition can create the degraded generation.
- Backup and restore survive killed-writer and stale-WAL fixtures.
- 004B tests kill points before temporary write, after file `fsync`, after replace, after directory `fsync`, before journal append, and after append before acknowledgement.
- The post-directory-`fsync` kill test is resumed after the original runtime grant expires and consumes the exact pre-sealed event digest once.
- Initialization, every run transition, closure from each non-closed state, duplicate repair, and concurrent repair converge.
- Public export excludes seeded private values and private digests.

## Acceptance criteria

- [ ] Every accepted event resolves through a digest-pinned event-family definition and payload schema.
- [ ] Native and import authorization paths are separate and mechanically enforced.
- [ ] A single explicit repository/organization bootstrap supplies pre-SPEC-007 commit and version guards without granting proposal, merge, promotion, or deployment authority.
- [ ] Append, subject versions, idempotency, batches, and hash-chain update are transactional.
- [ ] Full replay reproduces identical projections and integrity failures fail closed.
- [ ] Shadow mirroring never makes the journal authoritative and repairs every tested file-first crash gap.
- [ ] Run projection matches file state throughout the declared shadow window.
- [ ] Backup, restore, and the public projection pass SPEC-002 and SPEC-003 checks.
- [ ] Recovery distinguishes exact continuous reopen from declared-prefix disaster recovery; no older audited backup can silently truncate accepted history.

## Pull-request evidence

SPEC-004A attaches schemas and registry goldens, cross-runtime validation, authority-negative fixtures, repository-bootstrap exact-replay/stale/nonhuman/second-initialization tests, append and batch concurrency tests, replay and corruption reports, exact-continuation recovery, old-backup denial, missing-continuation, disaster-prefix/possible-loss, and backup/restore transcripts. SPEC-004B separately attaches the atomic-write kill-point matrix, deterministic import and repair report, transition and closure coverage, shadow-divergence report, rollback exercise, and redacted public projection.
