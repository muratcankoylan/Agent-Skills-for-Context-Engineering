# SPEC-008: Status, Observability, and Cost Accounting

Status: draft
Revision: 1
Revises: none
Wave: 1
Classification: split
Owners: operations steward agent; human maintainer
Depends on: SPEC-000, SPEC-002, SPEC-003, SPEC-004, SPEC-005, SPEC-006, SPEC-007

## Decision

Canonical status is a deterministic projection of durable events and immutable receipts at an explicit event sequence and `as_of` time. It is never a model-written narrative and never performs an unrecorded provider read. A separately labeled live overlay may help an operator diagnose an outage, but it is noncanonical, cannot drive policy or scheduling, and disappears unless converted into a verified observation receipt.

Status and hierarchical budgets are delivered separately. SPEC-008A implements status, explanation, bounded telemetry, and public projection. SPEC-008B implements atomic reservation and receipt-based cost accounting after the work kernel is proven.

## Context and current repository touchpoints

`researcher/scripts/loop_status.py` and generated reports expose the current local loop. The organization needs the same inspectable vocabulary across sources, work orders, commands, feedback, pull requests, evaluations, candidates, notifications, adapters, costs, and deployments. It must explain why work is waiting without asking a model to infer missing state or querying a provider behind the projector.

## Goals

- Answer what is running, waiting, blocked, failed, reconciled, approved, merged, accepted, deployed, stale, or unknown.
- Trace every status field to a source sequence, immutable receipt, reason code, and projection version.
- Keep local status useful during provider outage and distinguish stale knowledge from negative facts.
- Bound logs, traces, metrics, and cardinality before continuous operation.
- Prevent concurrent work from overspending any configured budget scope.
- Publish useful aggregate status without redacting a private snapshot in place.

## Non-goals

- A monitoring SaaS dependency in the local-first phase.
- Logging prompts, source bodies, secrets, capability values, private reason text, or hidden chain-of-thought.
- Using current wall time, a network call, or a model to fill missing canonical state.
- Summing different currencies without a registered conversion receipt.
- Claiming a service target before a measured baseline exists.

## Invariants

1. Every canonical snapshot binds projection schema and code digests, registry digest, source sequence and chain digest, `as_of` observation, and typed repository-acceptance, organization-version, and deployment-pointer slots. A slot distinguishes `dependency_inactive`, `uninitialized`, `known`, `stale`, and `unknown` where applicable; it never fabricates a version, commit, or null-as-success.
2. Replaying the same durable prefix with the same `as_of` observation produces byte-identical canonical status.
3. Unknown, stale, blocked, failed, accepted, and deployed are distinct states. Missing data is never converted to zero, absent, failed, or complete.
4. Provider state affects canonical status only through a registered immutable observation or delivery receipt.
5. A public status record is a new allowlisted `public_derived` artifact with a new identity. It contains no private locator, input digest, grant, provider identifier, or low-cardinality combination that reconstructs private activity.
6. Money and usage are integers in declared units. Every monetary value binds ISO currency, scale, price-catalog digest, and evidence class.
7. A budget reservation is accepted atomically across every scope in its chain only if `spent + outstanding worst_case_reservations <= cap` for each resource and currency.
8. Ambiguous usage retains its worst-case reservation or is conservatively charged until a reconciliation receipt resolves it.
9. Telemetry keys, sizes, cardinality, retention, and sampling are allowlisted and bounded. Overflow is counted, not recursively logged with unbounded detail.
10. Alerts create deduplicated intents or work orders; delivery success is never inferred from alert creation.
11. Time-driven state changes use accepted logical clock observations from their declared clock domain. Raw event timestamps, provider dates, process wall time, and model statements cannot expire a lease, release a reservation, close a window, or satisfy freshness.

## Interfaces and data

### Canonical status

```text
StatusProjector.rebuild(registry_digest, to_sequence) -> ProjectionReceipt
Status.snapshot(to_sequence, as_of_observation_id, view_profile)
  -> StatusSnapshot, SnapshotGenerationReceipt
Status.explain(object_id, to_sequence, as_of_observation_id, view_profile)
  -> ExplanationRecord
Status.watch(after_sequence, view_profile) -> StatusDeltaPage
Status.live_overlay(snapshot_id, adapter_reads) -> NonCanonicalOverlay
```

`StatusSnapshot` includes snapshot ID, source sequence and event-chain digest, projector code/config/schema digests, explicit `as_of` observation and time, policy version, freshness state, the three dependency-aware state slots, and typed sections. It contains no wall-clock generation field. `RepositoryAcceptanceSlot` is `uninitialized{owner:SPEC-004}` until the explicit bootstrap, then `known{commit,tree,pointer_version,source_event}` and later follows SPEC-007 reconciliation. `OrganizationVersionSlot` is a tagged union: `uninitialized{owner:SPEC-004}`, `known_bootstrap{epoch,version,bootstrap_event}`, `known_promoted{epoch,version,source_acceptance_event,attestation_id,projector_version}`, or `stale|unknown` with a typed reason and last-safe source. Bootstrap carries no fake attestation or SPEC-019 projector field. `DeploymentPointerSlot` is `dependency_inactive{owner:SPEC-025,required_revision:1}` before that contract activates, then `known{epoch,commit,source_event}` or `stale|unknown`; the inactive form carries no fake digest or placeholder commit. A separate `SnapshotGenerationReceipt` binds the snapshot digest to the actual generation time without changing canonical snapshot bytes. Sections cover organization health, source freshness, work and critical path, attempts and reconciliation, research runs, commands and feedback, PR current head and human-review state, evaluation epochs, candidates, outbox, adapters, environment, costs, budgets, and incidents as their owner specs activate.

SPEC-008 consumes the SPEC-005 `LogicalClockObservation` and `ExpiryEligibility` contracts rather than creating a second time authority. It adds deterministic clock-health, freshness, and reconciliation projections for later status, budget, and notification consumers. DST and locale never enter the contract; unresolved backward or implausible forward jumps remain explicit blockers.

The `as_of` observation must be an accepted SPEC-005 `LogicalClockObservation` from the same journal chain and at or before `to_sequence`; its sequence and chain digest are part of the request. A future-prefix observation, another chain, unresolved jump, or another clock domain is rejected rather than used to time-travel a projection.

`ExplanationRecord` is deterministic causal data: current typed state, source events and receipts, last accepted transition, active blockers, unmet dependencies, relevant policy and budget decisions, reconciliation state, and next legal events. Optional human prose is a rendered view of these fields and is never canonical.

`NonCanonicalOverlay` states its adapters, read times, failures, freshness, and mismatch against the snapshot. It cannot be consumed by the scheduler, reducer, policy engine, evaluator, or public exporter. Persisting a fact requires the owner adapter to emit a schema-valid observation receipt through SPEC-004.

View profiles are allowlisted combinations of audience, classification ceiling, and field policy. A profile may omit fields but may not rename a private state into a misleading public state. Public export runs through SPEC-002 from registered projection inputs and records new output identity and digest without including private input digests.

SPEC-008 owns the new-identity `PublicDeploymentStatus` projection once SPEC-025 is active. It may expose only deployment epoch, accepted public commit, lifecycle state, compatibility class, and bounded health conclusion. It never carries a private deployment-manifest identity or digest, provider or destination reference, budget detail, capability fact, or secret-store state.

Before SPEC-019 or SPEC-025 activation, fixed-`as_of` snapshots preserve the exact SPEC-004 bootstrap epoch and the deployment `dependency_inactive` sentinel. Later slot changes come only from the owning contract: SPEC-019 deterministically projects organization versions over journaled SPEC-007 acceptance events plus immutable attestations, while SPEC-025 uses deployment-owner events. Deleting and rebuilding the SPEC-019 projection reproduces the same version and source bindings. Activating, rolling back, or temporarily losing a later projector cannot replace `dependency_inactive` with `unknown`, reuse a last-known commit as current, or invent version zero.

### Logs, traces, metrics, and alerts

Structured logs use registered event names, stable reason codes, severity, source sequence, trace ID, work-order and attempt IDs, and bounded object references. Traces record stage timings, tool and adapter receipts, queue delay, and result disposition, not hidden reasoning. Metrics are derived from receipts or bounded counters and declare unit, aggregation, dimensions, retention, and classification in a registry.

The telemetry registry sets maximum record bytes, attribute count and length, allowed keys and values, series cardinality per metric and time window, trace spans per attempt, retention, and sampling behavior. Dynamic source URLs, free text, artifact digests, actor IDs, provider request IDs, and full object IDs are not metric labels. Limit breaches increment fixed overflow counters and preserve the affected work or event reference in private bounded diagnostics.

An `AlertIntent` binds condition, first and last source sequence, deduplication key, severity, acknowledgement state, cooldown, escalation policy, and destination class but no private destination. SPEC-015 later owns rendering and delivery receipts.

### Budget and cost ledger

Budgets form an explicit scope chain, initially `organization -> workflow -> run -> work_order -> attempt`, with optional executor and external-service subscopes. Scope membership is frozen in the work-order and attempt descriptors; callers cannot select a cheaper scope at charge time.

```text
BudgetLedger.reserve(operation_id, exact_request_digest,
                     scope_chain, resource_vector, worst_case_cost,
                     price_catalog_digest, work_order_id, attempt_id,
                     expected_scope_versions, expires_at)
  -> ReservationReceipt
BudgetLedger.commit(operation_id, exact_request_digest,
                    reservation_id, usage_receipts, expected_scope_versions)
  -> ChargeReceipt
BudgetLedger.reconcile(operation_id, exact_request_digest,
                       reservation_id, provider_receipt, expected_scope_versions)
  -> ReconciliationReceipt
BudgetLedger.release(operation_id, exact_request_digest,
                     reservation_id, terminal_receipt, expected_scope_versions)
  -> ReleaseReceipt
```

Every ledger mutation uses a caller-stable operation ID plus the canonical digest of its complete normalized request. Same ID and bytes returns the original persisted receipt, including after a lost acknowledgement; same ID with different bytes is an operation collision. Reserve is one SPEC-004 batch transaction across all scopes. Resource vectors use integers such as input tokens, output tokens, external calls, wall-time milliseconds, storage bytes, and money micros by ISO 4217 currency. `PriceCatalog` is immutable and binds provider, model or service SKU, unit, integer rate and scale, currency, effective interval, source receipt, and digest. A usage receipt binds the catalog used at dispatch. Estimated, provider-reported, invoiced, and reconciled costs are separate evidence classes and are not silently substituted.

Cross-currency views remain a vector unless a registered `CurrencyConversionReceipt` pins source amounts, rates, provider, observation time, and output currency. Expired reservations release only after the attempt is fenced and every possible external effect is resolved; otherwise worst-case cost remains outstanding.

## State and failure behavior

A stale projector returns the last valid snapshot with `stale_projection`, last sequence, and lag; it does not generate a fresh-looking timestamp. A missing provider receipt leaves usage `estimated` or `unknown` with its retained reservation. Provider outage affects only sections whose latest durable observation exceeded its declared freshness window.

Snapshot construction fails on registry drift, projection corruption, missing mandatory receipt, unsafe classification, or nondeterministic ordering. A section-owner schema unsupported by the current projector quarantines that section and makes overall completeness explicit while unaffected sections remain available. Accepted public commit and active deployment commit may differ and are never collapsed.

Budget reserve conflicts retry only from a fresh scope version. Cap denial is a normal `blocked_budget` reason. Duplicate reserve, commit, reconcile, and release calls return their original receipts; same operation identity with different amounts is a conflict. Negative usage, floating-point money, unknown unit, unpinned price, or a cross-currency scalar total is rejected.

Clock sampler sleep, restart, backward correction, or a large forward jump produces a typed observation or reconciliation state, never an implicit cascade of expirations. Deadline reducers consume only the accepted domain's logical time and retain the prior state while a jump is unresolved.

## Implementation sequence

### SPEC-008A: deterministic status and explanation

1. Register clock-health/reconciliation projections, snapshot, explanation, view-profile, telemetry, freshness, alert-intent, and public-deployment-status contracts over the SPEC-005 time authority.
2. Reproduce current loop, journal, work-order, command, and PR fixture status from durable inputs only.
3. Implement `snapshot`, `explain`, and `watch` with exact `as_of` behavior and blocker reason coverage.
4. Enforce telemetry bounds and render private terminal plus new-identity public Markdown projections.
5. Measure a baseline period; do not encode service targets yet.

### SPEC-008B: hierarchical budgets and cost

1. Register budget scope, resource vector, price catalog, reservation, usage, charge, and reconciliation contracts.
2. Implement atomic multi-scope reserve using SPEC-004 batch append and integrate it into SPEC-005 lease.
3. Add receipt-based actual, estimated, ambiguous, and reconciled charging.
4. Exercise concurrency, expiry, provider outage, multi-currency, and replay before budget enforcement becomes a dispatch gate.

## Migration and rollback

Run old and new status side by side at pinned source points and record discrepancies. Preserve dated reports as historical snapshots rather than rewriting them as live truth. Rollback switches the operator command to the previous generator without deleting events, receipts, projections, or budget records.

Budget enforcement begins in observe mode, then shadow mode that records would-deny decisions, then proposal mode after reconciliation error and concurrency tests meet an accepted threshold. Rollback disables new reservations only after active reservations and attempts are reconciled; it never erases charged usage.

## Observability

The subsystem observes its own projection lag, replay time and digest, missing receipts, stale sections, metric cardinality, log and trace volume, overflow counters, report age, public-export failures, outstanding and ambiguous reservation age, budget reconciliation error, and alert-intent backlog. These signals obey the same bounds and classifications.

## Verification

- Replaying one event and receipt prefix with a fixed `as_of` produces identical status bytes.
- An `as_of` observation beyond the selected prefix, from another journal chain, or from another clock domain is rejected.
- Sleep, process restart, UTC/DST boundary, backward correction, and large forward-jump fixtures preserve monotonic logical time or block deadline transitions pending reconciliation.
- A live provider response cannot alter canonical state until its observation receipt is appended.
- Every nonterminal work-order fixture has a stable, useful blocker explanation and causal chain.
- Provider outage leaves local status available and marks only affected sections stale or unknown.
- Public projection has a new identity and excludes seeded private values, digests, identifiers, and reconstructive metric combinations.
- Telemetry fuzzing respects record, label, cardinality, span, and retention limits.
- Concurrent reservations that individually fit but jointly exceed a cap yield one success and one budget conflict.
- Lost-ack replay of one reserve operation returns one original reservation; same operation ID with different bytes conflicts under concurrency.
- Actual, estimated, ambiguous, refunded, and reconciled cost fixtures preserve integer arithmetic and catalog provenance.
- Different currencies cannot produce a scalar total without a conversion receipt.
- Accepted public and active deployment commits can differ and remain correctly labeled.
- Pre-SPEC-019 and pre-SPEC-025 fixtures distinguish bootstrap-known organization state, inactive deployment ownership, uninitialized state, unknown state, and stale state; post-activation and rollback replay never fabricate or silently retain a current pointer.

## Acceptance criteria

- [ ] Canonical status and explanation depend only on a pinned durable prefix and explicit `as_of` observation.
- [ ] Live overlay is visibly noncanonical and mechanically excluded from decisions and public export.
- [ ] Public and private views agree on shared non-private state without sharing private identities or digests.
- [ ] Unknown, stale, conflict, reconciliation, acceptance, and deployment states remain distinct.
- [ ] Dependency-inactive, uninitialized, known, stale, and unknown version/pointer slots are schema-distinct and replay-identical at a fixed `as_of` observation.
- [ ] Telemetry has executable bounds, stable reason codes, and no raw prompt, secret, private reason, or hidden reasoning fields.
- [ ] Atomic hierarchical reservations prevent concurrent overspend and costs retain exact unit, currency, catalog, and evidence class.
- [ ] Existing local loop status remains available throughout migration.

## Pull-request evidence

SPEC-008A attaches projection parity, fixed-`as_of` replay vectors, representative private and public snapshots, pre/post SPEC-019 and SPEC-025 slot-state vectors, rollback and projector-loss vectors, blocker explanations, provider-outage behavior, public canary tests, and telemetry-bound fuzzing. SPEC-008B separately attaches atomic concurrency tests, price and usage goldens, ambiguity and expiry reconciliation, multi-currency failures, shadow-denial comparison, and rollback results.
