# SPEC-006: Command Bus and Human Feedback Ledger

Status: draft
Revision: 1
Revises: none
Wave: 1
Classification: split
Owners: governance agent; orchestration steward agent; human maintainer
Depends on: SPEC-000, SPEC-002, SPEC-003, SPEC-004, SPEC-005

## Decision

Human instructions will cross an explicit, replayable boundary before they can affect state. A channel delivery, authenticated ingress receipt, strictly parsed command intent, policy decision, scheduled work order, and applied event are different records. Privileged verbs use a bounded deterministic grammar; a model may propose an interpretation of ordinary feedback but can neither authenticate a sender nor create command authority.

Human verbatim feedback is immutable. Scope, classification, interpretation, confirmation, and operational effect are separate fields and separate decisions. One comment never silently becomes organization-wide policy.

## Context and current repository touchpoints

Current commands are local script subcommands while review reasoning often remains in GitHub or chat. The organization must respond when the maintainer approves, rejects, requests revision, pauses work, or explains why a source, candidate, or content draft is unsuitable. The transcript is evidence, not the database, and an interface label is not proof of identity or authority.

## Goals

- Normalize the same command semantics across local CLI, GitHub, and later authenticated adapters.
- Bind every mutating instruction to a trusted actor, exact target version, accepted commit, and policy decision.
- Make duplicate delivery harmless and stale or conflicting intent visible.
- Preserve verbatim feedback, structured interpretation, confidence, scope, classification, and confirmation independently.
- Apply confirmed lessons only to declared future work and organization versions.

## Non-goals

- Free-form natural language with privileged authority.
- Bulk conversion of historical chat into commands.
- Automatic global preference learning from review comments.
- Posting content, merging a pull request, or amending the constitution.
- Letting a content rejection overturn a research or evaluation verdict.

## Invariants

1. Raw channel content never mutates state and never supplies its own trusted actor.
2. Privileged parsing is deterministic, length-bounded, versioned, and model-free.
3. Each mutating command binds the current accepted public commit, exact target version, and an operation key. Pull-request commands also bind the current head SHA.
4. Authentication, parsing, authorization, scheduling, and application are separately recorded and can fail independently.
5. Authorization is re-evaluated at application against current policy and runtime grant; an earlier allow is not a bearer capability.
6. Exact redelivery applies once. The same delivery identity with different bytes is quarantined. A semantic repeat at a new delivery is still version-checked.
7. Human verbatim feedback is immutable; interpretations and confirmations supersede by new records.
8. Feedback scope does not imply classification. Classification does not imply publication authority.
9. Confirmed feedback changes only a declared future organization version, work order, or evaluation epoch. It never mutates an active attempt or sealed evaluation.
10. Approval records organizational readiness only. It cannot merge, post, deploy, publish a release, or expand authority.

## Interfaces and data

### Ingress chain

```text
ChannelDelivery
  -> IngressReceipt
  -> CommandIntent
  -> AuthorizationDecision
  -> WorkOrderSpec
  -> CommandApplied | CommandRejected | CommandConflict
```

`ChannelDelivery` is the exact received bytes plus adapter namespace, repository or workspace ID, channel-native delivery ID, sender claim, edit lineage, received time, and classification. Raw bodies are private by default and stored by reference.

`IngressReceipt` records signature or local-peer verification, trusted adapter identity, mapping from channel identity to organizational principal, content digest, parser eligibility, and reason code. Authentication derives the actor; it does not copy the sender claim.

`CommandIntent` contains command kind and grammar major, typed target, desired state, expected target version, accepted-commit guard, optional PR head guard, opaque human reason reference, parser digest, deterministic command ID, and operation key. For one-command deliveries, the command ID is UUIDv5 over adapter namespace, repository ID, immutable delivery ID, edit generation, and parser major. Multi-command delivery is rejected rather than assigned ambiguous authority.

`AuthorizationDecision` is produced by the SPEC-000 oracle from the trusted principal and exact intent. A mutating allow schedules a SPEC-005 work order with the intent and decision digests. The reducer rechecks target, accepted commit, head, constitution, grant, and operation key before appending the applied event. Read-only status may return a deterministic query receipt without scheduling a state-changing work order.

Before SPEC-007 activation, the accepted-commit guard resolves only to the explicit human-authorized SPEC-004 `RepositoryAcceptanceBaseline`; it is never inferred from the process worktree or ambient `HEAD`. After SPEC-007 activation, the same guard resolves to the current accepted-pointer version descended from that baseline. A missing, stale, divergent, or unknown pointer blocks mutation. The SPEC-004 organization epoch similarly supplies the initial version guard until SPEC-019 advances it.

The currently implemented constitution does not yet define exact actions and resources for this command set, so default deny remains correct. Before SPEC-006A can activate, the pre-Wave 1 human-merged SPEC-000 revision 2 `AuthorityVocabularyRegistry` and governance-policy update must register and test, at minimum, `query_status/status_projection`, `pause_run|resume_run|park_run|close_run/research_run`, `cancel_work/work_order`, `resolve_ambiguous_effect/external_effect`, and `reconcile_clock/clock_domain`. SPEC-007 later requires `record_pr_decision/pull_request`; SPEC-015 requires `create_content_draft|record_draft_decision|export_approved_draft/content_draft`, while any external destination additionally requires the existing destination-specific human authority. The existing `publish_draft` action cannot be repurposed: agent creation of a reviewable draft, local export for manual use, and delivery to an external destination are different effects. Unknown or not-yet-registered actions remain denied.

### Command grammar

`CommandFamilyRegistry` is a registered, digest-pinned extension registry. Each entry owns one canonical verb, grammar major and parser digest, exact target kind/version, minimum dependency specifications, constitution action and resource, required guards, reducer operation, result schema, and classification policy. The core parser dispatches only entries whose target contract and reducer are active; an unknown, unavailable, ambiguous, or digest-drifted entry fails closed. A later specification may register a command family without modifying the core parser, but it owns the grammar fixtures and reducer conformance for that family.

The initial SPEC-006 grammar is ASCII for verbs and flags, UTF-8 for bounded reason text, and one command per delivery. It contains only dependency-available local targets:

```text
/org status [run <id> | work <id> | queue]
/org pause <run-id> <guard> --reason <text-to-end-of-line>
/org resume <run-id> <guard> --reason <text-to-end-of-line>
/org park <run-id> <guard> --reason <text-to-end-of-line>
/org close <run-id> <guard> --verdict <registered-value> --reason <text-to-end-of-line>
/org cancel-work <work-id> <guard> --reason <text-to-end-of-line>
/org resolve-ambiguous-effect <effect-id> <guard> --disposition <confirmed_absent|confirmed_applied|abandoned_unknown> --evidence <artifact-id> --operation-key <opaque-id> --reason <text-to-end-of-line>
/org reconcile-clock <clock-domain-id> <guard> --prior-observation <id> --current-observation <id> --prior-boot <id> --current-boot <id> --lower-bound-micros <unsigned-integer> --upper-bound-micros <unsigned-integer> --effective-micros <unsigned-integer> --max-advance-micros <unsigned-integer> --operation-key <opaque-id> --reason <text-to-end-of-line>

<guard> := --expected-version <unsigned-integer> --accepted-commit <full-sha>
```

Flags before `--reason` have one canonical order; the reason consumes the remainder after UTF-8 and length validation. Abbreviations, implicit targets, shell expansion, Markdown aliases, model repair, multiple commands, and unknown flags are rejected. Channel adapters may expose structured UI, but must emit the same canonical intent and parser fixtures.

`resolve-ambiguous-effect` is the sole human ingress to the SPEC-005 `AmbiguousEffectDispositionRequest`. Its target is the registered unresolved external-effect record; `<guard>` binds its expected version and current accepted commit; evidence is a resolvable classified artifact; and the operation key is stable across delivery retry. The SPEC-005 reducer revalidates effect, work order, attempt, fence, adapter receipts, disposition, evidence, policy decision, and runtime grant. Exact command replay returns the first receipt; editing disposition, evidence, reason, target, or guard under the same delivery or operation key collides. No internal caller, adapter, executor, agent, or runtime operator may synthesize the request outside authenticated ingress.

`reconcile-clock` is the sole human ingress to the SPEC-005 `ClockReconciliationRequest`. The command binds the exact clock domain, expected clock-state version and accepted commit, prior accepted and current quarantined observation identities, boot transition, bounded bridge interval, effective logical time, maximum authorized advance, operation key, and human reason. The reducer resolves the immutable observations and binds their digests before constructing the request; it rejects a wrong domain, stale version, missing quarantine, nonmonotonic or out-of-bounds effective time, changed bytes under the same key, or a policy/grant mismatch. `ClockAuthority.reconcile(...)` is the internal reducer boundary, not an alternate ingress, and remains unreachable until this registered command family and its human-only `reconcile_clock/clock_domain` authority are active. Samplers, supervisors, agents, adapters, and runtime operators cannot synthesize reconciliation.

SPEC-007 separately registers `pr-status` plus head-bound `approve-pr` and `reject-pr` families when its PR reducer is active. SPEC-015 registers `approve-draft-for-manual-use`, `request-draft-revision`, `reject-draft`, and `export-draft` only after its frozen-draft reducer and export destination policy are active. No command family may merge, post social content, activate deployment, or expand authority.

### Feedback ledger

`FeedbackAtom` points to the exact delivery and artifact digest and contains:

- a verbatim reference and its independent classification and retention;
- typed subject and effect scope (`artifact`, `source_family`, `skill`, `workflow`, or `organization`);
- independent classification plus an optional private preference-owner reference, neither of which changes effect scope;
- human-supplied reason codes, if any;
- a separately versioned interpretation, model and prompt digests, confidence, and contradictions;
- proposed operational delta and affected retrieval or evaluation domain;
- confirmation state, confirmer, and first applicable accepted commit or evaluation epoch, plus the current SPEC-004 organization epoch and any later SPEC-019 promotion version; and
- supersession or override lineage.

A public feedback summary is a new SPEC-002 projection with a new identity. Neither a public scope nor a public target makes a private verbatim record public. Organization-scoped operational deltas require explicit human confirmation; constitutional changes additionally require a merged amendment.

## State and failure behavior

Command processing is:

```text
received -> authenticated -> parsed -> authorized -> scheduled -> applied
received|authenticated|parsed|authorized|scheduled
  -> rejected | expired | conflict | quarantined
scheduled -> retry_wait | reconciling -> scheduled | applied | rejected | expired
```

The journal records each completed boundary, not a mutable command row. A stale target version, accepted commit, PR head, constitution version, grant, or operation key becomes a typed conflict or denial; it is never last-write-wins. A transient scheduling or application failure remains retryable under the same operation identity or enters reconciliation when the remote outcome is ambiguous; it never becomes an unexplained terminal `failed`. A conflict creates a reconciliation work order only when policy permits.

Feedback moves through `captured -> interpreted -> confirmed | local_only | rejected_interpretation`, then may become `effective -> superseded`. Rejecting an interpretation preserves the verbatim record. A confirmed record is retrieved only when effect scope, classification, accepted commit or epoch, and receiving role all permit it. Active or sealed work retains its starting context and records later feedback only as future evidence.

## Implementation sequence

### SPEC-006A: deterministic local command path

1. Register delivery, ingress, intent, authorization, outcome, and feedback contracts.
2. Land the prerequisite SPEC-000 revision 2 authority vocabulary, then implement the exact grammar, canonical serializer, deterministic IDs, and negative fixtures.
3. Use a fake authenticated local adapter to schedule and apply the core `status`, `pause`, `resume`, `park`, `close`, `cancel`, `resolve-ambiguous-effect`, and `reconcile-clock` commands through SPEC-005.
4. Capture human-coded feedback without model interpretation and prove scoped future retrieval.

Extension delivery belongs to the specification that owns the target: SPEC-007 adds GitHub ingress and PR commands, SPEC-014 may add model-proposed feedback interpretations, and SPEC-015 adds frozen-draft commands. Each extension inherits all dependencies of its owning specification and must pass this specification's parser, authentication, authorization, idempotency, and reducer conformance suite. SPEC-006 itself does not forward-depend on those extensions.

## Migration and rollback

Do not import old chat. Selected historical PR decisions may be captured as immutable `legacy_import` feedback with exact links, explicit classification, and no reconstructed command authority. Rollback disables external adapters while preserving local CLI ingress, journal facts, and every captured feedback record.

## Observability

Expose deliveries by adapter, authentication and parser failures, authorization denials, version and head conflicts, application latency, duplicate and collision rates, feedback awaiting confirmation, interpretation disagreement, scope and classification distribution, and the future work or epoch that consumed a feedback atom. Raw reason text is not a log attribute.

## Verification

- Every accepted grammar form round-trips to one canonical intent; malformed, reordered, multiple, and overlong forms fail with stable reasons.
- Exact redelivery applies once; a delivery-ID/content mismatch quarantines both claims.
- An old target version, accepted commit, or PR head cannot apply.
- A forged sender claim, stale allow decision, wrong runtime grant, or unauthorized pause is denied independently.
- Clock reconciliation denies an agent, sampler, runtime operator, wrong domain, stale state, missing quarantine, unbounded bridge, or changed-byte replay; a crash retry applies one bounded bridge once.
- Ambiguous-effect disposition denies nonhuman callers, stale effect state, missing evidence, and operation-key collisions; each permitted disposition is replayed exactly once without reopening an old attempt.
- Core command families cannot invoke merge, publish, or deployment; later family fixtures prove the same boundary for every extension.
- Artifact-scoped feedback cannot affect another artifact or organization policy.
- Scope and classification cross-product fixtures prevent public projection of private feedback.
- Confirmed feedback enters only a declared future context or epoch; sealed and active work is byte-unchanged.

## Acceptance criteria

- [ ] The delivery-to-applied-event chain is complete, typed, and replayable.
- [ ] Privileged commands have exact deterministic parsing, identity, policy, and version checks.
- [ ] Every active command family resolves to a constitution action/resource pair and exhaustive allow/deny fixtures; no family relies on an unknown action or repurposes `publish_draft`.
- [ ] Duplicate, edited, stale, conflicting, and unauthorized commands are safe.
- [ ] Clock reconciliation and ambiguous-effect disposition have one authenticated human ingress each; internal APIs cannot mint their requests.
- [ ] Feedback retains verbatim, classification, scope, interpretation, confirmation, and effect separately.
- [ ] The family registry rejects unavailable targets and every core or extended approval command grants no merge, posting, deployment, or release authority.
- [ ] Confirmed rejection reasons influence only declared future scopes and can be traced to consumers.

## Pull-request evidence

SPEC-006A attaches registry and grammar goldens, unavailable-family and adversarial fixtures, ID vectors, authorization and stale-guard tests, end-to-end local command traces, feedback scope/classification matrix, and proof that no command can merge or post. Later owner specifications attach their adapter, grammar, target-reducer, identity-mapping, and public-export evidence without reopening the core parser.
