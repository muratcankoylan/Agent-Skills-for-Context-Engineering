# SPEC-006: Command Bus and Human Feedback Ledger

Status: draft
Wave: 1
Classification: split
Owners: governance agent; orchestration steward agent; human maintainer
Depends on: SPEC-004, SPEC-005

## Decision

Human instructions from GitHub, local CLI, and approved conversational interfaces will be normalized into authenticated, idempotent commands before they change state. Reviews, rejections, corrections, and preferences will become durable feedback atoms with explicit scope. Models may interpret feedback and propose policy deltas; they may not silently turn one comment into global behavior.

## Context and current repository touchpoints

Current run commands are local script subcommands and human reasoning lives mainly in PR discussion or chat. The target organization must react when the maintainer merges, approves, rejects, asks for revision, pauses work, or explains why a source or post is unsuitable. Those events must affect future work without making a transcript the database.

## Goals

- Support one command contract across channels.
- Preserve exact human reason, structured interpretation, confidence, and applied scope.
- Make duplicate commands harmless and conflicting commands visible.
- Feed confirmed lessons into retrieval, authoring, and evaluation contexts.

## Non-goals

- Free-form natural language with unrestricted authority.
- Automatic global preference learning from every review comment.
- Letting a social-post rejection overturn a research verdict.

## Invariants

1. A command records actor, channel, target, expected version, reason, idempotency key, and policy decision.
2. Parsing is deterministic for privileged verbs.
3. Human verbatim feedback is immutable; interpretation is versioned separately.
4. Scope is one of artifact, source family, skill, workflow, organization, or private preference.
5. Global policy deltas require explicit confirmation and, if constitutional, a merged amendment.
6. Approval marks readiness but never merges a PR.

## Interfaces and data

Initial command grammar:

```text
/org status [run|pr|queue]
/org approve-pr <number> [head-sha]
/org reject-pr <number> --reason <text>
/org revise <artifact-id> --reason <text>
/org rerun <eval|stage> [scope]
/org pause [run-id|organization]
/org resume [run-id|organization]
/org park <run-id> --reason <text>
/org close <run-id> --verdict <value>
/org supersede <artifact-id> --by <artifact-id>
/org publish-draft <draft-id>
```

`Command` and `FeedbackAtom` use registered schemas. A feedback atom points to the exact artifact digest, channel record, private or public verbatim reference, reason codes, interpretation model and prompt, scope, confidence, proposed delta, confirmation state, and first applicable organization version.

## State and failure behavior

A command moves `received -> authenticated -> parsed -> authorized -> scheduled -> applied`, with terminal `rejected`, `expired`, `conflict`, or `failed`. Application is conditional on the target version. Conflicts create a reconciliation packet; they are not last-write-wins. Feedback moves `captured -> interpreted -> confirmed|local_only|rejected_interpretation -> applied|superseded`.

## Implementation sequence

1. Implement channel-neutral ingress, CLI normalization, and event recording.
2. Add feedback ledger and reason-code taxonomy with human confirmation.
3. Publish channel adapter fixtures; SPEC-007 implements GitHub ingress and SPEC-014 implements optional Hermes ingress.
4. Expose scoped feedback retrieval with stable query and result schemas; SPEC-012 later compiles those records into role-specific context.

## Migration and rollback

Do not bulk-convert old chat. Import selected historical PR decisions with links and explicit `legacy_import`. Rollback disables external adapters while retaining CLI and all captured events.

## Observability

Show command latency, authentication and authorization failures, conflicts, unapplied feedback, interpretation disagreement, scope distribution, and which future runs consumed a feedback atom.

## Verification

- The same command from two deliveries applies once.
- An approval for an old head SHA becomes a conflict.
- Unauthorized pause and merge-like commands are denied.
- Rejected interpretation leaves verbatim feedback intact.
- Artifact-scoped feedback does not alter organization-wide behavior.
- Confirmed feedback retrieval returns only records matching declared scope, effective organization version, and classification; SPEC-012 owns the context-package integration test.

## Acceptance criteria

- [ ] Privileged commands have deterministic parsing and policy checks.
- [ ] Duplicate and stale commands are safe.
- [ ] Feedback retains verbatim, interpretation, scope, and confirmation separately.
- [ ] `approve-pr` cannot cause merge.
- [ ] Human rejection reasons influence only declared future scopes.
- [ ] Status links decisions to affected work and artifacts.

## Pull-request evidence

Attach command fixtures for every channel and terminal state, a scoped-feedback trace, stale-SHA conflict example, and proof that no supported command grants merge authority.
