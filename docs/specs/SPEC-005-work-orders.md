# SPEC-005: Work Orders, Scheduling, Leases, and Recovery

Status: draft
Wave: 1
Classification: split
Owners: orchestration steward agent; runtime operator
Depends on: SPEC-003, SPEC-004

## Decision

All autonomous work will execute as typed, budgeted work orders with immutable inputs, explicit dependencies, leases, heartbeats, checkpoints, and idempotent result application. A scheduler decides readiness; an executor performs work; a reducer alone applies valid results to organizational state. Session lifetime is never the work lifetime.

## Context and current repository touchpoints

The current JSONL queue and launchd loop already provide safe local scheduling with locks and atomic files. `research_loop.py` provides a useful outer run state. This spec generalizes that foundation for heterogeneous research, evaluation, PR, notification, and meta-harness jobs while preserving the current outer lifecycle.

## Goals

- Resume after process, laptop, or executor failure without duplicate effects.
- Make dependencies, budgets, retries, and blocking reasons queryable.
- Run the same work order on Hermes or another conforming executor.
- Reconcile ambiguous remote outcomes before retrying.

## Non-goals

- Global distributed scheduling in the first implementation.
- Inferring work from chat transcripts.
- Retrying non-idempotent external actions blindly.

## Invariants

1. Inputs include exact artifact digests, repo commit, context request, policy version, evaluator epoch where relevant, executor, model, harness, and adapter versions.
2. A lease has one owner, expiry, and fencing token.
3. A late result is recorded but cannot apply after lease or input version changes.
4. External writes use stable idempotency keys or enter reconciliation before retry.
5. Budgets include time, attempts, tokens, money, and external calls.
6. Checkpoints are immutable and content-addressed.
7. Every lease or retry is a distinct immutable attempt; an old attempt is never reopened.
8. Running work with a possible external side effect cannot become terminally cancelled until reconciliation.

## Interfaces and data

A `WorkOrder` contains kind, priority, dependencies, input references and hashes, requested role, context request, capability scope, budget, retry policy, checkpoint policy, expected subject version, and desired output schema.

A `WorkAttempt` contains attempt and work-order IDs, ordinal, starting work-order version, lease owner, fencing token and expiry, executor and environment handles, model and harness versions, context package and delta-chain digests, checkpoints, start and heartbeat events, external operation IDs and receipts, output artifacts, usage and cost, error classification, reconciliation history, and terminal result. Attempts are append-only records linked to journal events.

State is:

```text
work order: created -> ready -> in_progress -> completed -> applied
ready -> cancelled | budget_exhausted | quarantined | policy_blocked

attempt: created -> leased -> running -> completed | retryable_failed | failed
leased|running -> unknown -> reconciling -> completed|retryable_failed|failed|unknown
leased|running -> cancellation_requested -> reconciling -> cancelled|completed|unknown
```

Scheduler methods are `submit`, `create_attempt`, `lease`, `heartbeat`, `checkpoint`, `complete`, `fail`, `request_cancel`, `reconcile`, and `apply`. Attempt mutations take attempt ID, current fencing token, and expected version. A retry terminates the old attempt, returns the work order to `ready`, and creates a new attempt with a new fencing token and causation link.

## State and failure behavior

Retries are classified: deterministic input failures do not retry; transient dependency failures use bounded exponential backoff with jitter; ambiguous external writes reconcile first; policy failures wait for a new command or policy version. A cancellation request stops new child work and asks the executor to stop, but remains nonterminal until receipts and remote state are reconciled. Dead-lettered work retains its attempts and artifacts and can be cloned into a new work order with a causation link.

## Implementation sequence

1. Define work-order, work-attempt, and reducer schemas over the event journal and existing local queue.
2. Add lease, fencing, heartbeat, budgets, checkpoint references, and per-attempt executor handles.
3. Convert one deterministic retrieval job and one validation job.
4. Add executor dispatch and result-application boundary.
5. Migrate current loop steps incrementally and retain compatibility commands.

## Migration and rollback

Existing queue records receive deterministic imported work-order IDs; each observed execution receives a `legacy_import` attempt. New workers initially consume only new work-order kinds. Rollback stops new dispatch, reconciles active attempts, and lets the legacy loop continue from its last valid outer state.

## Observability

Project queue depth and age by kind, attempts per work order, lease utilization, heartbeat gaps, retry causes, cancellation reconciliation age, unknown outcomes, budget consumption, checkpoint age, executor latency, and critical-path blockers. Each pending item exposes a plain-language `why_not_running` reason.

## Verification

- Kill a worker after checkpoint and resume on another executor.
- Expire a lease and prove the stale worker cannot apply.
- Duplicate completion has one state effect.
- Ambiguous PR creation reconciles instead of opening a second PR.
- Dependency cycle and impossible budget are rejected at submission.
- Each retry has a distinct attempt, context chain, receipts, cost, and terminal result.
- Cancellation of an in-flight external action passes through request and reconciliation and preserves a possible completed or unknown outcome.

## Acceptance criteria

- [ ] Every autonomous action can be represented as a work order.
- [ ] Legal transitions and retry classes are mechanically enforced.
- [ ] Crash, stale-lease, duplicate-result, and ambiguous-write tests pass.
- [ ] Status explains blocked and waiting work.
- [ ] Existing research runs remain resumable.
- [ ] Executors cannot directly mutate canonical state.
- [ ] Attempt lineage unambiguously separates retries, late results, checkpoints, receipts, and costs.

## Pull-request evidence

Attach state-transition coverage, kill-and-resume transcript, stale-worker proof, migrated-job examples, budget report, and legacy compatibility results.
