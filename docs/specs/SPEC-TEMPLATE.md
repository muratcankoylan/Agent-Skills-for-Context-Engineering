# SPEC-NNN: Title

Status: draft
Wave: N
Classification: public | private | split
Owners: human maintainer; named agent role
Depends on: SPEC-NNN

## Decision

State the binding architectural decision in one paragraph. This section must be understandable without reading implementation details.

## Context and current repository touchpoints

Explain the problem and name existing artifacts that will be retained, migrated, generated, or superseded. Distinguish observed facts from design assumptions.

## Goals

- A testable outcome.
- A durable contract.
- An operator-visible behavior.

## Non-goals

- Explicitly excluded adjacent work.
- Deferred optimization or vendor choice.

## Invariants

List properties that must remain true across implementations, failures, retries, runtime changes, and later specifications.

## Interfaces and data

Define commands, events, schemas, API methods, files, or adapter methods. Include versioning, ownership, classification, idempotency, and error semantics. Prefer concrete examples where ambiguity would otherwise reach implementation.

## State and failure behavior

Define the state machine, legal transitions, retry behavior, timeouts, reconciliation, recovery, and terminal states. State who may cause each privileged transition.

## Implementation sequence

1. Schema and validation.
2. Read path or observation mode.
3. Write path behind a feature gate.
4. Migration and shadow comparison.
5. Activation and cleanup.

## Migration and rollback

Define how existing artifacts are imported, how dual-read or dual-write is bounded, how integrity is checked, and how rollback preserves newly written data. Never use destructive migration as the only path.

## Observability

Name events, metrics, logs, traces, status projections, budgets, and alerts. Logs must use identifiers and structured reasons, not secret values or unbounded model transcripts.

## Verification

### Deterministic tests

- Schema and invariant tests.
- State-transition and idempotency tests.
- Migration and replay tests.

### Integration tests

- One real vertical path.
- One dependency or adapter failure.
- One crash and resume scenario.

### Evaluation, if applicable

- Baseline and candidate identity.
- Dataset and rubric epoch.
- Statistical and cost gate.
- Leakage check and negative-control result.

## Acceptance criteria

- [ ] Each criterion is observable and binary.
- [ ] Required repository validators pass.
- [ ] Documentation and runbook match behavior.
- [ ] Rollback has been exercised.
- [ ] Human authority and private/public boundaries are tested.

## Pull-request evidence

List required attachments: work order, change-impact manifest, test report, benchmark report, cost summary, migration report, screenshots or status projections, and unresolved-risk register.

## Open decisions

Only include decisions that can safely remain open during acceptance. Assign an owner and decision deadline or trigger. Do not use this section for missing core design.
