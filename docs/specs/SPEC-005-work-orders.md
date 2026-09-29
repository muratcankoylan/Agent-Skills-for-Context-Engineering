# SPEC-005: Work Orders, Scheduling, Leases, and Recovery

Status: draft
Revision: 1
Revises: none
Wave: 1
Classification: split
Owners: orchestration steward agent; runtime operator
Depends on: SPEC-000, SPEC-003, SPEC-004

## Decision

All autonomous work will execute as immutable, typed, budgeted work orders. A deterministic scheduler derives readiness, a dispatcher creates one fenced attempt descriptor per lease, an executor can emit only append-only attempt records and immutable results, and a reducer alone changes canonical organizational projections. Session lifetime is never work lifetime, and no model is part of the first vertical slice.

## Context and current repository touchpoints

The JSONL queue, file locks, atomic writes, launchd loop, and research-run state machine provide a safe single-process baseline. They do not yet separate approved intent from an execution lease, distinguish an executor report from an accepted result, or reconcile late and ambiguous effects across runtimes. This specification preserves the local-first design and makes those boundaries explicit before Hermes or another model runtime is introduced.

## Goals

- Resume after process, laptop, or executor failure without duplicating an effect.
- Make dependencies, readiness, policy, budgets, retries, cancellation, and blocking reasons deterministic and queryable.
- Reject stale or conflicting results without deleting their evidence.
- Support any executor through the same narrow attempt and result contracts.
- Reconcile a possibly completed external operation before retrying or cancelling it.

## Non-goals

- Distributed consensus or multi-host scheduling.
- Inferring work from chat transcripts or model reasoning.
- Letting an executor edit a queue, run state, budget, or projection directly.
- Treating repeated inference as independent review.
- Blind retry of an external write.

## Responsibility boundary

```text
authorized submitter -> immutable WorkOrderSpec -> journal
journal -> deterministic scheduler -> readiness projection
dispatcher -> AttemptReservation -> typed extensions -> immutable AttemptDescriptor -> executor
executor -> AttemptEvent / CheckpointEnvelope / AttemptResult -> journal
journal -> reducer -> canonical work, run, and artifact projections
```

The scheduler, dispatcher, executor, and reducer may share one process initially, but their interfaces and authority do not collapse. Executor output is evidence submitted to the reducer, not canonical state.

## Invariants

1. A `WorkOrderSpec` is immutable. Changed inputs, scope, capabilities, output contract, or acceptance criteria create a new causally linked work order.
2. Every attempt begins with one immutable reservation that allocates its attempt ID, lease generation, and fencing token but grants no execution authority. Exactly one activation may turn it into one immutable descriptor and active lease. A retry is a new attempt.
3. Every executor record binds the work-order digest, attempt ID, fencing token, input-set digest, and output schema.
4. A stale or late result is retained but cannot apply after lease generation, work-order version, input, policy, or accepted-commit changes.
5. Only the reducer writes canonical projections; scheduler and executor APIs append authorized facts or proposals.
6. External writes require a stable operation key and adapter receipt. An ambiguous outcome enters reconciliation and cannot be retried automatically.
7. Per-work-order budget is reserved before lease and charged from immutable receipts. Concurrent reservations cannot exceed the ceiling.
8. Cancellation is a request. Work with a possible external effect cannot become `cancelled` until reconciliation proves the effect absent.
9. Canonical time transitions occur from recorded clock observations or expiry events, never from an implicit call to wall-clock `now` during replay.
10. Dependency cycles, missing dependencies, incompatible outputs, and impossible budgets fail before dispatch.

## Interfaces and data

### Immutable contracts

`WorkOrderSpec` contains:

- work kind and schema version, priority class, submitter, and creation authority;
- classification, retention class, and permitted public-projection route;
- exact dependency work-order IDs and required terminal outcomes;
- immutable input artifact references and an input-set digest;
- exact SPEC-004 accepted-repository pointer and organization epoch, constitution version, and policy-context digest;
- executor constraints and an optional map of typed extension references;
- budget ceilings for attempts, time, tokens, integer money micros by ISO currency, and external calls;
- retry, backoff, cancellation, checkpoint, reconciliation, and retention policies; and
- expected output kind, schema version, and acceptance contract.

The SPEC-005A model-free slice omits role, context-package, model, and runtime-harness extensions. Its repository and organization guards come from the explicit human-authorized SPEC-004 bootstrap, never ambient `HEAD` or a fabricated version. An extension is accepted only after its owning specification has registered the exact kind and version; unregistered role names, free-form context, prompt strings, or capability labels fail closed. SPEC-012, SPEC-013, and SPEC-014 later add typed context, role, and execution-bundle references without changing kernel ownership.

`AttemptReservation` is created after readiness, policy, dependency, and budget checks pass. It allocates the work-order digest and version, attempt ID and ordinal, lease generation, fencing token, reserved budget, activation deadline, and extension requirements. A reservation cannot be dispatched, call an adapter, or produce an external effect. It gives SPEC-012 and SPEC-013 a stable attempt identity and fence against which to compile and authorize typed extensions.

`AttemptDescriptor` is created only by atomically activating a live reservation after every required typed extension is frozen. It additionally binds the lease owner and interval, executor and environment identities, model and harness identities when present, exact context-package chain, role package, granted operations, output path policy, and dispatcher decision. Activation rechecks work, policy, dependency, budget, accepted commit, extension digests, and reservation version; concurrent activation produces exactly one descriptor and one typed loser. Renewing a lease appends a lease event; it does not rewrite the descriptor.

Granted operations are the intersection of the constitution allow, work-order requirements, deployment-mode ceiling, executor and environment ceiling, and runtime grant. A later SPEC-013 role ceiling can only narrow that set. The descriptor records the contributing policy and configuration digests so no executor can infer an unlisted capability from the work kind.

`AttemptEvent` covers lease activation, execution started, heartbeat observed, checkpoint proposed or accepted, cancellation requested or acknowledged, external operation started, reconciliation observed, and execution stopped. Each event has a registered payload family owned by this specification.

`CheckpointEnvelope` is the single SPEC-005-owned attempt checkpoint contract. It is immutable and content-addressed and binds the attempt identity, fence, payload kind/version/digest, resumable artifact references, operation identity, and policy context. Owning specifications register typed payloads; SPEC-012 owns `ContextCheckpointPayload`, not a second envelope or lifecycle. The reducer accepts an envelope only after validating its registered payload and current fence. A resumed execution receives a new attempt descriptor pointing to the accepted envelope; an old attempt is never reopened.

`AttemptResult` is immutable. It contains declared terminal outcome, output artifacts, validation receipts, usage and cost receipts, external operation receipts, errors, and executor completion time. It does not claim application. `ResultApplication` records the reducer's decision, checked versions, reason code, applied event IDs, and projection digest.

SPEC-005 owns the minimal time authority needed for leasing. `LogicalClockObservation` is written only by the attested supervisor clock sampler under `sample_clock/clock_domain` and binds clock domain and source, integer UTC microseconds, monotonic tick and unit, boot identity, acquisition receipt, uncertainty bound, authenticated principal, prior accepted observation, and classification. That action can append one observation only; it cannot reconcile a jump, prove a deadline, or mutate another target. The clock reducer requires nondecreasing logical UTC per domain, increasing monotonic ticks within one boot, and an explicit restart bridge. A backward correction or forward jump beyond the accepted skew bound enters `clock_reconciliation_required`; expiry and replacement block until a human-authorized bounded bridge is accepted. Every activation deadline, lease interval, heartbeat threshold, backoff, and reservation expiry names the same domain.

Clock reconciliation is a distinct human command, not part of runtime-operator or sampler authority. Before it can activate, the pre-Wave 1 human-merged SPEC-000 revision 2 `AuthorityVocabularyRegistry` must register the exact human-only pair `reconcile_clock/clock_domain`; the existing query, work, deployment-operation, and emergency actions do not grant it. Unknown actors or mappings default deny. The command's immutable `ClockReconciliationRequest` binds the clock domain, expected clock-state version, prior accepted and current quarantined observation identities and digests, a one-use `ClockBridge`, reason code and human explanation, current accepted public commit, stable operation key and exact request digest, and authenticated human principal. `ClockBridge` binds its prior and current boot identities, lower and upper logical-UTC microsecond bounds, one effective logical-UTC microsecond value inside those bounds, and the policy maximum advance. Its lower bound equals the prior accepted logical UTC, its upper bound cannot exceed that value plus the authorized maximum advance, and it is valid only for the named domain, observations, and expected version.

`ClockReconciliationDecision` records allow or deny, the exact `reconcile_clock/clock_domain` constitution decision and version, matched rule, policy-context digest, accepted-commit check, reason, request digest, and requesting authenticated human. Only an allowed decision can produce `clock.reconciliation_accepted`. That event binds the request, decision, prior and current observations, bridge, operation key, resulting state version, and append receipt. In one compare-and-append transaction the reducer verifies the expected version and current observation chain, records the decision and event, advances the domain version exactly once, and accepts the effective logical value. The new logical value must be greater than or equal to the previous accepted value; neither a bridge nor replay can move it backward, rewrite observations, broaden a clock domain, or expire a reservation or lease by itself. A subsequent `ExpiryEligibility` remains necessary.

Clock reconciliation is idempotent and crash-recoverable. Repeating an operation key with byte-identical request and authority inputs returns the original receipt; the same key with different bytes is an operation collision. A crash before the transaction leaves the domain blocked at its prior version. A crash after commit reconstructs the one accepted bridge from the journal receipt. Stale versions, mismatched observation ancestry, a non-human or unauthenticated principal, wrong action or resource, stale accepted commit, decreasing or out-of-policy bounds, and a bridge for another domain are durable denials and never mutate clock state.

`ClockDeadlineEligibility` is the reusable SPEC-005 time-proof contract, emitted only by the trusted clock reducer under `prove_clock_deadline/clock_domain`. It binds a registered purpose, exact target kind, ID and expected version, integer deadline, accepted clock observation and domain, uncertainty decision, clock-state version, and proof-reducer version. It proves only that one declared deadline is eligible under the accepted logical timeline; its action cannot mutate the target. Purpose registration restricts the target kinds and owning reducer. `ExpiryEligibility` is its lease/reservation specialization and additionally binds the prior fence. Only that specialization plus the owning work reducer can move a reservation to `expired_no_effect` or fence an expired lease. SPEC-015 later registers a notification-window-close purpose without creating another clock or time-proof authority. Raw `occurred_at`, journal receipt time, provider dates, process wall time, and model output are not deadline evidence.

`AmbiguousEffectDispositionRequest` is the single shared contract for a human decision about an external effect that bounded reconciliation cannot resolve. It binds work order, attempt and fence, exact effect and adapter identities, operation key and collision digest, every reconciliation receipt and evidence reference, expected work/effect versions, accepted public commit, one disposition from `confirmed_absent|confirmed_applied|abandoned_unknown`, bounded reason, stable decision operation key, authenticated human principal, and request digest. Before this API can activate, SPEC-000 revision 2 must register human-only `resolve_ambiguous_effect/external_effect`. The allow decision and runtime grant are separate from the request bytes.

One compare-and-append reducer creates `AmbiguousEffectDisposition`. `confirmed_absent` may make a new fenced attempt eligible but never reopens the old attempt; `confirmed_applied` must bind a result or provider-evidence contract that the owning reducer can validate; `abandoned_unknown` is permanently terminal and cannot authorize retry. Exact request replay returns the original receipt. Same-key/different-byte, stale target version, wrong effect/attempt, agent, daemon, adapter, or runtime-operator principal, stale accepted commit, missing evidence, or unknown disposition fails without changing work. A crash before commit leaves the effect unresolved; a crash after commit reconstructs the one disposition. The API is the reducer boundary, not a human-authentication bypass: until SPEC-006 activates its canonical `resolve-ambiguous-effect` family, every ambiguous effect remains blocked. SPEC-014 executors and SPEC-015 delivery adapters consume this record and cannot invent adapter-local human authority.

### Public interfaces

```text
WorkKernel.submit(spec, trusted_principal, policy_decision, runtime_grant)
  -> SubmissionReceipt
Scheduler.ready(as_of_event, source_sequence, limit) -> ReadinessPlan
Dispatcher.reserve(work_order_id, expected_version, trusted_principal,
                   policy_decision, runtime_grant, budget_request)
  -> AttemptReservation
Dispatcher.activate(reservation_id, expected_reservation_version,
                    typed_extension_refs, trusted_principal,
                    policy_decision, runtime_grant)
  -> AttemptDescriptor
Dispatcher.expire(reservation_or_attempt_id, expected_version,
                  clock_observation_id, trusted_principal, runtime_grant)
  -> ExpiryEligibility, AppendReceipt
ClockAuthority.reconcile(request, trusted_principal,
                         policy_decision, runtime_grant)
  -> ClockReconciliationDecision, AppendReceipt
ClockAuthority.prove_deadline(purpose, target_ref, expected_target_version,
                              deadline_micros, clock_observation_id,
                              trusted_principal, runtime_grant)
  -> ClockDeadlineEligibility
WorkKernel.resolve_ambiguous_effect(request, trusted_principal,
                                    policy_decision, runtime_grant)
  -> AmbiguousEffectDisposition, AppendReceipt
AttemptSink.append(attempt_event, trusted_principal, runtime_grant)
  -> AppendReceipt
AttemptSink.report(result, trusted_principal, runtime_grant)
  -> AppendReceipt
Reducer.reduce(to_sequence?) -> ReductionReceipt
```

`ReadinessPlan` is a deterministic ordered view, not a mutation. Reservation atomically rechecks its premises, reserves the attempt budget, allocates the attempt and fence, increments the lease generation, and appends the required events without granting execution authority. Activation is a second compare-and-append transaction. A reservation that expires or is cancelled before activation has no possible external effect and releases its local reservation directly. Hierarchical organization and service reservations are added by SPEC-008B; this specification enforces the local work-order ceiling.

### State machines

The machine-readable transition registry is canonical. It must represent at least these work-order states:

```text
submitted
blocked_dependency | blocked_policy | blocked_budget | ready
active | cancellation_requested | reconciling | retry_wait | result_pending
applied | failed | cancelled | dependency_failed | budget_exhausted
conflict | quarantined | unknown_terminal
```

reservation and attempt states are:

```text
reserved -> leased | expired_no_effect | cancelled_no_effect
leased -> running
leased|running -> result_reported | cancellation_requested | lease_expired
cancellation_requested|lease_expired -> cancelled_no_effect
cancellation_requested|lease_expired + possible_effect_recorded -> reconciling
reconciling -> result_reported | retryable_failed | failed | unknown_terminal
result_reported -> accepted | retryable_failed | failed | rejected_stale | rejected_conflict
```

Every nonterminal work-order state exposes a stable `why_not_running` or `why_not_applied` reason. The transition registry records whether a possible effect has occurred and forbids `reconciling` without that fact. Cancellation or expiry before activation or before `external_operation_started` terminates directly as no-effect. `unknown_terminal` is terminal for automatic execution and changes only through a valid SPEC-005 `AmbiguousEffectDisposition`; no ordinary work order or adapter callback can supersede it. A declared transient executor, dependency, or validation result with no possible external effect moves `result_reported -> retryable_failed`, closes that attempt, appends a bounded backoff decision, and moves the work order to `retry_wait`; a terminal failure moves both attempt and work order to `failed`. An accepted result moves the work order to `result_pending` until reducer application produces `applied` or a typed conflict. Expiry creates a new readiness event before another attempt can be reserved.

Activation is one SPEC-004 batch transition from `reserved` to `leased`: descriptor, lease fact, reservation consumption, and work-order state commit together. No externally visible `activated` intermediate state exists. A crash before commit leaves only the non-dispatchable reservation; a crash after commit reconstructs the one descriptor and lease from the receipt. Dispatcher handoff occurs only after that receipt is durable.

## State and failure behavior

Dependency readiness is evaluated over a versioned DAG. A required dependency failure produces `dependency_failed`; an optional or alternative dependency follows its explicit predicate. New dependency edges never mutate an active work order.

Failures are typed as deterministic input, policy, budget, transient dependency, executor, validation, concurrency conflict, stale result, ambiguous external effect, or terminal. Only declared transient classes retry, within both attempt and budget limits. Jitter is recorded in the retry decision so replay does not resample it. Policy changes may unblock a new attempt but do not rewrite the decision used by an old attempt.

Lease expiry requires a current `ClockDeadlineEligibility` with the registered lease-expiry purpose and valid `ExpiryEligibility` specialization, then fences the old executor before creating a replacement attempt. Wrong-domain, stale, uncertain, or jump-blocked observations cannot prove eligibility or expire work. A late heartbeat, checkpoint, or result receives a durable rejected disposition. Duplicate results return the original application receipt. If an external effect may have occurred, the reducer schedules a reconciliation work order using the same operation key; no retry or terminal cancellation is allowed until a conclusive adapter receipt or valid `AmbiguousEffectDisposition` resolves it.

## Implementation sequence

### SPEC-005A: model-free kernel

1. Land the pre-Wave 1 human-merged SPEC-000 revision 2 authority vocabulary with `reconcile_clock/clock_domain`; clock reconciliation remains disabled until that exact registry entry is effective.
2. Register work-order, attempt, checkpoint, result, application, logical-clock, clock-reconciliation request/decision/event, generic deadline-eligibility and lease-expiry specialization, ambiguous-effect request/disposition, transition, and reason-code contracts.
3. Implement the reducer, clock-reconciliation and ambiguous-effect compare-and-append APIs, and deterministic readiness planner over SPEC-004.
4. Implement two-phase reservation and activation, fencing, per-work-order budget reservation, heartbeat, expiry, retry, cancellation, and result application.
5. Execute one deterministic repository-validation work order with a fake executor. Exercise restart and replay from a fresh projection database.

### SPEC-005B: adapter and migration boundary

1. Convert one deterministic retrieval step and one validation step without changing the outer research-run authority.
2. Add an idempotent fake external adapter and ambiguous-outcome reconciler.
3. Mirror legacy queue work into imported work orders and compare scheduling outcomes.
4. Publish an executor conformance suite for SPEC-014 and future runtimes.

Hermes, model prompts, ambient memory, live credentials, and multi-host dispatch remain outside this specification.

## Migration and rollback

Existing queue records receive deterministic imported work-order IDs through a versioned adapter. Each observed legacy execution becomes a closed import attempt; no current mutable queue record is presented as a native attempt. New workers initially consume only explicitly enabled kinds.

Rollback stops new leasing, fences executors, reconciles active external operations, and lets the legacy loop continue from its last valid outer state. Journaled work, attempts, and results remain available for replay and inspection.

## Observability

Project queue depth and age by kind, dependency blockers, lease and heartbeat age, attempts per work order, retry and rejection reasons, cancellation and reconciliation age, outstanding reservations, charged usage, checkpoint age, executor latency, and critical path. Every count binds a source sequence and every pending item exposes a stable reason code.

## Verification

- A cycle, missing dependency, failed required dependency, incompatible input, and impossible budget each fail with distinct reasons.
- Concurrent leasing creates one active attempt and one fenced loser.
- Concurrent activation of one reservation creates exactly one descriptor and one active lease; crash-expired reservations never dispatch.
- Early, stale, wrong-domain, backward-jump, and implausible-forward-jump expiry attempts are denied or held for clock reconciliation; a restart bridge cannot create a replacement while prior lease eligibility is unproven.
- Clock reconciliation denies an agent, daemon, sampler, unauthenticated principal, wrong constitution action or resource, stale accepted commit, stale expected clock-state version, mismatched observation ancestry, other-domain bridge, decreasing effective value, and bridge beyond the authorized bound without changing the domain version.
- One authenticated human request with a current `reconcile_clock/clock_domain` allow accepts exactly one bounded bridge; exact replay returns its receipt, changed bytes under the same operation key collide, and crashes before and after the compare-and-append reconstruct zero or one transition respectively.
- Replaying clock observations and accepted bridges preserves a nondecreasing per-domain logical timeline and cannot directly make a lease or reservation expire.
- A deadline proof with an unregistered purpose, wrong target kind/version, stale clock-state version, wrong domain, or insufficient uncertainty bound is denied and cannot be reused by another reducer.
- Sampler and deadline-prover action/grant fixtures prove each trusted non-human principal can emit only its narrow record and cannot reconcile time or mutate the target; every other actor/action pairing is denied.
- Killing the worker after an accepted checkpoint resumes through a new attempt without reopening the old one.
- An expired executor cannot apply a heartbeat, checkpoint, result, or external receipt.
- Exact duplicate completion has one application; different results for one attempt create a conflict.
- A transient no-external-effect executor or validation failure follows `result_reported -> retryable_failed -> retry_wait`, closes the old attempt, and can reserve only a new fenced attempt after its recorded backoff eligibility.
- Retry count, backoff, reservation, usage, and total worst-case cost remain inside the work-order ceiling.
- Cancellation or expiry before a recorded possible effect terminates directly; after a possible effect it enters reconciliation and may resolve to completed, cancelled, or unknown.
- Ambiguous external creation reconciles by operation key and never creates a second effect.
- Ambiguous-effect disposition denies agent, daemon, adapter, operator, stale-version, wrong-effect, missing-evidence, and same-key/different-byte requests; exact human replay applies once, crash boundaries converge, and only `confirmed_absent` can enable a new fenced attempt.
- Replaying the same event prefix produces identical readiness and work-order projections.
- Before SPEC-007 and SPEC-019, a work order binds the exact SPEC-004 repository baseline and organization epoch; after those owners activate, stale baseline or organization versions are rejected rather than inferred from the worktree.

## Acceptance criteria

- [ ] Work intent, attempt lease, executor events, result evidence, and reducer application are separate registered objects.
- [ ] Legal transitions and reason codes are mechanically enforced and replay-deterministic.
- [ ] Executors cannot mutate canonical organizational state.
- [ ] Crash, stale-fence, duplicate, conflict, dependency, budget, cancellation, and ambiguous-effect tests pass.
- [ ] Clock reconciliation is disabled until the human-only `reconcile_clock/clock_domain` constitution amendment is effective, and every accepted bridge binds the current accepted commit and authenticated human decision.
- [ ] Positive, denial, replay, collision, stale-version, cross-domain, nondecreasing-time, and crash-boundary clock-reconciliation fixtures pass.
- [ ] Non-reconcilable effects remain blocked until the shared human-only disposition contract resolves them; adapter-local authority, old-attempt reopening, and implicit retry are impossible.
- [ ] Every retry has a distinct attempt, descriptor, fence, context chain, receipts, cost, and terminal disposition.
- [ ] Existing research runs and the legacy queue remain resumable during migration.
- [ ] The model-free vertical slice runs end to end before any model runtime is integrated.
- [ ] Wave-1 work orders use the explicit SPEC-004 bootstrap guards and migrate without identity drift to later reconciled repository and organization versions.

## Pull-request evidence

SPEC-005A attaches schemas, full transition and reason-code coverage, DAG fixtures, concurrent lease and reservation tests, kill-and-resume transcript, replay digest, stale-worker proof, and deterministic validation-work trace. It also attaches the effective SPEC-000 vocabulary reference; positive authenticated-human and negative agent, daemon, sampler, wrong-action/resource, stale-commit, stale-version, ancestry, bound, and domain fixtures; exact replay and operation-collision receipts; a nondecreasing reducer replay digest; pre-commit/post-commit clock-reconciliation crash transcripts; and ambiguous-effect disposition allow/deny, collision, stale-target, evidence, retry-gating, and crash receipts. SPEC-005B separately attaches migrated-job parity, external-effect reconciliation, executor conformance, and rollback results.
