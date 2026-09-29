# SPEC-015: Notification Outbox, Review Packets, and Content Drafts

Status: draft
Revision: 1
Revises: none
Wave: 2
Classification: split
Owners: community editor agent; operations steward agent; human maintainer
Depends on: SPEC-002, SPEC-003, SPEC-004, SPEC-005, SPEC-006, SPEC-007, SPEC-008, SPEC-011, SPEC-013, SPEC-014

## Decision

Messages to the human and any externally visible channel will originate as immutable `NotificationIntent` events in a transactional outbox. The event that creates a notification-worthy state transition and its intent are appended in one idempotent journal batch. Rendering and delivery are separate receipted stages. Adapter semantics are explicit; the system does not claim generic exactly-once delivery.

Agents may prepare laptop and email alerts, research digests, decision-grade review packets, community questions, and social-media drafts. The initial system supports `/org approve-draft-for-manual-use` and export, not autonomous posting. A public destination remains unsupported until a separate command contains exact human authorization for that destination and revision.

## Context and current repository touchpoints

The current researcher produces local reports but lacks transactional intent creation, delivery receipts, acknowledgement, ambiguity handling, public/private rendering, and a governed path from unresolved research to a community question. The user needs high-value PR, source, failure, and content decisions surfaced without turning every feed item into an interruption.

## Goals

- Deliver actionable, deduplicated notifications to the local laptop and approved private email targets.
- Generate evidence-linked review packets for PR and non-PR decisions.
- Turn unresolved high-value questions into shareable drafts without overstating evidence.
- Preserve exact rendered bytes, attempts, reconciliation, acknowledgement, and human response.
- Learn from rejected drafts only through explicit SPEC-006 feedback scope.

## Non-goals

- Autonomous posting to social accounts or public destinations in the initial system.
- Marketing copy disconnected from accepted evidence.
- Sending every rejection, candidate, failure retry, or feed item to the human.
- Promising exactly-once effects from SMTP or another non-idempotent provider.

## Invariants

1. A notification-causing state event and its `NotificationIntent` are appended atomically through one SPEC-004 batch carrying a registered stable batch identity and ordered-request digest.
2. Intent, rendered bytes, delivery attempts, final delivery knowledge, and acknowledgement are distinct immutable records.
3. Every render and delivery mutation uses a caller-stable operation key plus a canonical collision digest; delivery also uses a stable intent revision and destination-scoped provider idempotency key when the provider supports one. Retries follow the adapter's declared semantics.
4. An ambiguous non-reconcilable send becomes `unknown` and is not retried automatically.
5. Public drafts cite public-safe evidence and label reported results, inference, uncertainty, and questions.
6. Destination addresses, provider locators, credentials, restricted source identities, and private compilation diagnostics never appear in public artifacts.
7. Editing or rejecting a draft does not change its underlying source, claim, mechanism, or evaluation verdict.
8. Rendered bytes are frozen before delivery. Any content change creates a successor intent revision with a new digest and authorization requirement.
9. Shadow-mode output cannot enter the active outbox or any external adapter.
10. A send, export, approval, or later publish action records exact artifact digest, destination scope, principal, authority, and causing command.

## Transactional outbox

SPEC-015 uses the SPEC-004 batch interface directly rather than defining a second append API:

```text
EventStore.append_batch(batch_id, ordered_requests_digest, requests, trusted_principal,
                        per_request_authorization_inputs, batch_runtime_grant)
  -> BatchAppendReceipt
```

Each request carries its event proposal, expected subject version, and event idempotency identity. The caller-selected `batch_id` is stable for the registered batch purpose, and `ordered_requests_digest` is SPEC-004's canonical digest of the complete ordered requests including their expected subject versions. SPEC-004 persists that identity pair and receipt atomically with the events. Exact `batch_id` and request-digest replay returns the original receipt even after subject versions advance; reuse of the ID with different ordered bytes is a collision and appends nothing.

For a state change that requires notification, the batch contains both the business event and `NotificationIntent`. The intent's causing event must be an earlier request in that batch or an existing event. Projectors can rebuild pending delivery solely from the journal.

`NotificationIntent` includes intent and revision IDs, causing event and subject, template and input-artifact digests, audience, classification ceiling, channel, private destination reference, priority, coalescing key, deduplication window, not-before time, expiry, acknowledgement policy, adapter policy, mode, and exact authorization reference. It contains no rendered bytes or resolved destination.

`RenderReceipt` binds the intent revision, operation key and collision digest, renderer and template versions, safe input digests, exact MIME or platform bytes as an `ArtifactRef`, content digest, classification result, policy checks, and render time. A render discrepancy or changed input creates a new intent revision; an old authorization never transfers implicitly.

`DeliveryAttemptReceipt` records adapter class and version, destination reference, operation key and collision digest, provider idempotency key when applicable, rendered digest, timing, safe provider receipt, cost, and outcome. `DeliveryReceipt` records the strongest reconciled knowledge: `delivered`, `not_delivered`, or `unknown`, plus evidence. `Acknowledgement` is a separate human or provider event and cannot be inferred from successful transport alone.

## Adapter semantics

Every adapter declares one effect class:

- `provider_idempotent`: the provider contract guarantees repeated use of the same key cannot duplicate the effect within a declared window.
- `reconcilable`: the adapter can query a stable provider identity or deterministic marker before deciding whether retry is safe.
- `non_reconcilable`: an ambiguous attempt cannot be proven delivered or absent; it enters `unknown` and requires the shared SPEC-005 `AmbiguousEffectDisposition` through SPEC-006 authenticated human ingress. The adapter owns no parallel decision authority.

Raw SMTP is non-reconcilable unless the selected relay provides a durable queryable message identity and documented deduplication behavior. A locally generated Message-ID is not proof of non-delivery. GitHub comments or issues require marker-based reconciliation plus an exact human-authorized command before any external write. Local notification and provider API adapters declare their behavior from measured conformance, not assumed semantics.

Rendering is a separate `Renderer.render(intent, operation_key, collision_digest) -> RenderReceipt` operation. Delivery adapters expose `deliver(intent, render_receipt, destination_reference, operation_key, collision_digest) -> DeliveryAttemptReceipt` plus read-only `status` and `reconcile`, all against exact intent, render, and attempt identities. The collision digest binds every semantic input and policy; exact key-and-digest replay returns the original persisted receipt, while key reuse with different bytes performs no effect. Delivery credentials and destinations resolve through private capability grants. A renderer never receives delivery credentials, and a delivery adapter never recompiles content.

## Review packets and drafts

A review packet contains the decision requested; current recommendation and its scope; gate results; exact public-safe evidence for and against; contradictions; available evaluation results; cost; changed artifacts; risks; unresolved questions; decision deadline; and the exact permitted commands. Missing evaluation evidence before SPEC-017 or promotion evidence before SPEC-019 is labeled `not_available`, never fabricated or silently omitted.

A content draft contains audience, thesis, claim classes, public evidence links, uncertainty, community question, platform-specific variants, prohibited unsupported claims, and lineage to its review packet. The evidence checker consumes accepted SPEC-011 public graph projections and acceptance mappings; restricted evidence may inform a private packet but cannot leak into the public draft.

SPEC-015 owns and registers four immutable entries under the `notification_content.v1` namespace through the SPEC-006 command-family registry. Each entry pins owner spec, one verb, grammar digest, target and output schemas, required constitution action and resource, reason limits, guard requirements, reducer, and conformance fixtures. The registered grammar is:

```text
/org approve-draft-for-manual-use <draft-id> <guard>
/org request-draft-revision <draft-id> <guard>
  --reason <text-to-end-of-line>
/org reject-draft <draft-id> <guard>
  --reason <text-to-end-of-line>
/org export-draft <draft-id> <guard> --format <registered-format>

<guard> := --expected-version <unsigned-integer> --accepted-commit <full-sha>
```

This family registration is the sole canonical grammar definition for these four verbs and uses the SPEC-006 `<guard>` production byte-for-byte; it does not introduce a second parser implementation. Unknown formats, reordered flags, missing guards, multiline commands, and family-digest drift fail before authorization. Approval means the human may manually use the exact frozen revision. Export creates only an authorized immutable local artifact and receipt. Neither command authorizes an adapter to publish. A future publish command requires a separate spec or amendment defining destinations, confirmation, reconciliation, and revocation.

## Alert policy

Notification policy is versioned and includes per-priority rate limits, coalescing windows, acknowledgement deadlines, escalation ladders, maximum repeats, quiet hours, expiry, and loop detection. A coalescing window is closed only by an accepted SPEC-005 `LogicalClockObservation` and a SPEC-005 `ClockDeadlineEligibility` under the registered notification-window-close purpose for the exact window version, deadline, and clock domain, never an implicit wall clock. SPEC-008 projects clock health and status but does not own the time fact.

`NotificationWindowKey` is a deterministic private digest of policy version, audience, classification, channel, destination-reference digest, destination class, coalescing key, recorded window-start observation ID, clock domain, and configured integer duration and end deadline. Different destinations can never share a window. Every coalescible source event atomically creates an immutable member `NotificationIntent` in `held_for_window` state with that window key. Member intents are never individually renderable. The first journaled accepted SPEC-005 observation whose `ClockDeadlineEligibility` names that exact window version and proves the deadline in that domain is the unique close observation; a later observation cannot replace it.

At window close, membership is exactly the held intents whose causing-event sequence is at or before the close-observation sequence. The coalescer sorts them by causing-event sequence and intent ID and derives `NotificationGroupId` from the window key, close-observation ID, and exact ordered member digest. It submits one SPEC-004 batch containing `NotificationGroupClosed`, one composite `NotificationIntent`, and one `IntentSupersededByGroup` event per member. The batch uses a stable identity derived from the group ID and checks the window and member subject versions. Concurrent closes therefore yield one success; exact replay returns its receipt; different membership is a collision. A source event journaled after the close observation belongs to the next window even if the close batch has not yet committed, and cannot mutate the closed group. An immediate non-coalesced alert uses a deterministically closed singleton window, so the renderer has one eligibility rule.

Coalescing retains every causing event while rendering one composite summary. An escalation cannot recursively generate the same alert class, and an acknowledgement or terminal disposition closes its repeat chain.

Urgent operator failures, human merge or command reconciliation, expiring decisions, and unreconciled external effects have distinct policies. Low-priority digests cannot consume the urgent channel's rate or queue budget.

## State and failure behavior

Member intent projections move `pending -> held_for_window -> superseded_by_group`, with terminal `expired` or `cancelled` before window close where policy permits. Composite and singleton-group intents move `pending -> group_closed -> rendered -> ready -> delivering -> delivered|not_delivered|unknown`, with `acknowledged`, `expired`, `cancelled`, and `superseded` overlays where valid. Only `group_closed` intents can be rendered. Retryable transport failure returns to `ready` only within expiry, attempt, cost, and adapter-policy limits. `unknown` never automatically returns to `ready` for a non-reconcilable adapter. A shared disposition may confirm delivery, confirm absence and permit a new delivery attempt under current policy, or close as abandoned-unknown; it never reuses the ambiguous attempt.

Drafts move `proposed -> evidence_checked -> human_review -> approved_for_manual_use|revision_requested|rejected|superseded`. Revision creates a successor identity. Rejection records the exact draft and reason. If the human supplies a broader lesson, SPEC-006 records proposed scope and confirmation; only confirmed feedback may affect future retrieval or drafting. It cannot mutate the active research decision or already rendered content.

## Implementation sequence

Both slices inherit the complete dependency header; they differ only in delivery order and surface, not prerequisite authority:

1. `SPEC-015A`, after every declared dependency is active, delivers registered batch identities, outbox projection, deterministic group closing, renderer, mock adapter, local notification, private email adapter, delivery classes, reconciliation, rate limits, and loop detection.
2. `SPEC-015B` additionally requires the completed 015A slice and delivers registered `notification_content.v1` commands, review-packet templates, evidence-checked drafts, manual-use approval, export, and scoped rejection. SPEC-017 and SPEC-019 fields remain optional and explicitly unavailable until those specs are implemented.

External GitHub or public-channel delivery is not part of either initial slice without a later exact human-authorized command contract.

## Migration and rollback

Existing reports remain immutable files and may be referenced as legacy packet inputs. Channel activation is allowlisted per private destination and adapter. Rollback stops dispatch, fences in-flight attempts, reconciles ambiguous outcomes, preserves pending intents, and leaves packets readable locally. It never deletes an unknown delivery in order to retry it.

## Observability

Track intent and delivery queue age separately; render latency; delivered, not-delivered, unknown, and acknowledged counts; retries by adapter class; reconciliation latency; coalescing ratio and denominators; rate-limit drops; escalation depth; detected loops; messages by priority; human review time; draft acceptance and revision reasons; source-to-notification lag; and per-channel cost. Public telemetry excludes destination and protected identity cardinalities.

## Verification

- Fault injection between each batch-write boundary yields either both business event and intent or neither.
- Replaying an identical batch or projector cannot duplicate an intent.
- Concurrent coalescing closes create one composite intent with deterministic member order; a late member enters the next window and a membership collision appends nothing.
- Wrong-domain, stale-version, uncertainty-blocked, unregistered-purpose, and implicit-wall-clock window closes fail; exact replay of the first valid SPEC-005 `ClockDeadlineEligibility` preserves one close observation and one group.
- Provider-idempotent, reconcilable, and non-reconcilable adapters follow distinct retry behavior.
- Lost acknowledgements for render and delivery return the original persisted receipt on exact replay; operation-key collisions perform no effect.
- An ambiguous SMTP send becomes `unknown` and is not resent automatically.
- A changed template, input, or byte produces a new intent revision and invalidates prior approval.
- Private destinations and restricted evidence cannot appear in public packets, drafts, logs, or telemetry.
- Unsupported claims fail evidence checking; unavailable eval fields remain explicit.
- Rejecting a draft leaves source, graph, mechanism, and evaluation state unchanged.
- Broader feedback affects future work only after scoped confirmation.
- Coalescing, rate, escalation, expiry, acknowledgement, and loop fixtures prevent alert storms without suppressing urgent events.
- Shadow-mode runs cannot create an active outbox record.

## Acceptance criteria

- [ ] State event and notification intent use one idempotent atomic append batch.
- [ ] Batch and coalescing identities use SPEC-004 registered identity and collision semantics without a parallel append API.
- [ ] Intent, render, attempt, reconciled delivery, and acknowledgement records are separate and replayable.
- [ ] Every adapter has tested idempotency and reconciliation semantics; no generic exactly-once claim remains.
- [ ] Every render and delivery mutation has a stable operation key, canonical collision digest, and persistent replay receipt.
- [ ] Laptop and email adapters use private destination references and typed capability grants.
- [ ] Review packets contain explicit commands and decision-grade evidence.
- [ ] Every draft command resolves through the digest-pinned SPEC-006 command-family registry and exact target reducer.
- [ ] Social output is exact-revision manual-use or export only until a publishing amendment is accepted.
- [ ] Content, delivery, feedback, and research-verdict states remain independent.
- [ ] Rate limiting, coalescing, escalation, acknowledgement, expiry, and loop detection have adversarial fixtures.
- [ ] Every time-driven window transition binds a current SPEC-005 logical-clock observation and purpose-scoped deadline proof; SPEC-008 supplies status only.

## Pull-request evidence

Attach registered batch-identity atomicity and replay tests, concurrent and late-member coalescing fixtures, logical-clock/deadline-proof positive and wrong-domain/stale/uncertain/unregistered-purpose negatives, command-family parser and drift goldens, mock receipts for all three adapter classes, ambiguous-SMTP fixture, redacted live supervised channel receipt, exact-byte revision test, sample review packet and draft, evidence-check failure, scoped-rejection trace, shadow-isolation test, and alert-storm simulation.
