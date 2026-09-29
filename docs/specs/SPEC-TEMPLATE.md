# SPEC-NNN: Title

Status: draft
Revision: 1
Revises: none
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

Lifecycle status changes are isolated from contract edits. The transition into `architecture_reviewed` adds `Dependency revisions: SPEC-NNN@revision, ...` for the exact direct dependency set, or `none`; this binding is immutable for the revision. A terminal `amended`, `superseded`, or `retired` revision adds `Lifecycle decision: ADR-NNNN`; amended and superseded revisions also add `Replacement: SPEC-NNN@next-revision`. The accepted ADR must include `Lifecycle transition: SPEC-NNN@revision -> amended|superseded|retired -> SPEC-NNN@next-revision|none` that matches the transition exactly. The next draft increments `Revision` and binds the exact terminal predecessor bytes in `Revises`.

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
