# SPEC-008: Status, Observability, and Cost Accounting

Status: draft
Wave: 1
Classification: split
Owners: operations steward agent; human maintainer
Depends on: SPEC-004, SPEC-005, SPEC-006

## Decision

Status will be a deterministic projection of durable events and current external reconciliations, not a model-written narrative. Every agent and the human maintainer receive the same state vocabulary, while role-specific views reveal only needed fields. Structured logs, traces, metrics, budgets, and human-readable reports share correlation IDs.

## Context and current repository touchpoints

`researcher/scripts/loop_status.py` and generated status reports already expose the local loop. The new organization requires answers across source intake, work orders, evaluations, candidates, PRs, commands, feedback, notifications, adapters, and costs. It must also explain why something is not progressing.

## Goals

- Answer what is running, waiting, blocked, failed, approved, merged, and stale.
- Make every status line traceable to source events and reconciled external state.
- Detect cost, latency, quality, and queue regressions.
- Produce public redacted reports and private operator detail from one projection model.

## Non-goals

- A large monitoring vendor dependency in the local-first phase.
- Logging unlimited prompts, source text, secrets, or chain-of-thought.
- Using a model to infer missing state.

## Invariants

1. Every view states projection sequence, generation time, organization version, and repository commit.
2. Unknown is a valid visible state; it is not converted to failed or complete.
3. Budgets are checked before dispatch and accounted after receipts.
4. Private values are represented by identifiers and classifications.
5. A public metric must not allow reconstruction of private content.
6. Alerts create events or work orders and have deduplication and acknowledgement.

## Interfaces and data

Provide `status snapshot`, `status watch`, and `status explain <id>`. The projection includes organization health, source freshness, queue and critical path, work-order and attempt states, cancellation reconciliation, run verdicts, evaluation epochs, candidate comparisons, PR head/check/review state, command conflicts, feedback backlog, outbox state, adapter and environment health, costs, accepted public commit, and active deployment commit.

Logs use JSON with event, work order, run, candidate, evaluation, PR, and trace identifiers plus stable reason codes. Traces record stage timings and tool receipts, not hidden reasoning. Metrics cover reliability, latency, quality, cost, freshness, context composition, evaluation validity, and human workload.

Budgets are hierarchical: organization, workflow, run, work order, executor, and external service. Reservations prevent concurrent work from overspending a shared limit.

## State and failure behavior

A stale projector marks affected views stale and exposes the last processed sequence. Missing provider receipts create estimated cost with confidence until reconciled. Alert delivery failure stays visible in the outbox. Status generation must continue in degraded mode when one external provider is unavailable.

## Implementation sequence

1. Define metric, log, trace, budget, and reason-code registries.
2. Reproduce current loop status from the event journal.
3. Add queue, command, PR, evaluation, candidate, and outbox projections.
4. Add private terminal/dashboard view and generated public Markdown view.
5. Establish service targets only after measuring a baseline operating period.

## Migration and rollback

Run old and new status side by side and record discrepancies. Preserve dated reports as snapshots. Rollback switches the operator command to the prior generator without deleting event or metric data.

## Observability

The observability system observes itself: projector lag, missing spans, metric cardinality, log volume, report age, budget reconciliation error, and alert-delivery health are first-class signals.

## Verification

- Replaying the same events produces identical status.
- Every pending work-order fixture has a useful `why_not_running` explanation.
- Provider outage leaves local status available and explicitly stale where necessary.
- Seeded private data is absent from public outputs.
- Budget reservation prevents concurrent overspend.
- A merged PR can be traced from source lead through production commit.
- A retry, late result, and cancellation each resolve to the correct immutable attempt and context chain.
- Accepted public and active deployment commits can differ and are never mislabeled.

## Acceptance criteria

- [ ] One command explains any durable object and its blockers.
- [ ] Public and private views agree on non-private state.
- [ ] Cost and token usage resolve to work orders and candidates.
- [ ] Projection freshness is always visible.
- [ ] Unknown and reconciliation states are preserved.
- [ ] Existing local loop status remains available during migration.

## Pull-request evidence

Attach projection parity report, representative private and public snapshots, blocker explanations, budget-concurrency test, outage test, and an end-to-end trace.
