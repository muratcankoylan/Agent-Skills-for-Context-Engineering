# Long-Horizon Organization Briefs

Version: bootstrap-v2
Status: bootstrap proposal
Owner specifications: SPEC-005, SPEC-012, SPEC-013, SPEC-014
Authority: none

This directory contains a supervised bootstrap prompt bundle for advancing the specification program. It is source material for a future prompt compiler, not a production role manifest and not an authorization mechanism.

The templates, a filled attempt manifest, a prompt, a model response, and an asserted mode all grant no authority. During bootstrap, authority comes only from the current human instruction intersected with protected-default-branch policy. In the future harness it comes from an authenticated policy decision and a reservation-bound runtime grant. The stricter result always wins.

## Components

| File | Purpose |
| --- | --- |
| `organization-root-brief.md` | Stable mission, definitions, invariants, orchestration policy, and return gate |
| `spec-work-brief.template.md` | Per-wake work contract for one exact authoritative spec or vertical slice |
| `attempt-manifest.template.md` | Harness-only template for one private immutable attempt manifest and its model-safe launch projection |
| `fresh-verifier-brief.md` | Independent adversarial review without builder history or prior verdicts |
| `resume-brief.template.md` | Start a new attempt from a reducer-accepted checkpoint without reopening the source attempt |

The dated readiness review at `docs/reviews/2026-08-15-autonomous-organization-readiness.md` records the evidence and limitations that motivated this split.

## Why this is a bundle

One perpetual model trajectory would mix authority, implementation history, evaluator context, and transient session memory. The intended organization instead performs bounded event-driven attempts:

```text
authoritative state + external event
  -> authority, dependency, and budget check
  -> builder reservation
  -> private builder-attempt manifest + safe launch projection
  -> bounded builder attempt descriptor and lease
  -> frozen candidate or typed blocker
  -> separate verifier reservation
  -> private verifier-attempt manifest + narrower safe launch projection
  -> fresh-context verifier attempt
  -> exact-SHA review packet
  -> human merge or scoped feedback
  -> accepted checkpoint envelope and next reservation
```

Session lifetime is never work lifetime. Chat history, framework memory, and a model's internal plan are not canonical state.

Builder and verifier work never share one attempt merely because they concern the same candidate. Each has its own SPEC-005 reservation, descriptor, principal, fencing token, budget, context profile, manifest, and terminal result. An independence receipt relates the attempts without exposing the builder transcript or another verifier's first-pass verdict.

## Bootstrap use

Before SPEC-005, SPEC-012, SPEC-013, and SPEC-014 are implemented, a human operator may prepare a bootstrap launch from:

- the protected default-branch constitution and specification bytes;
- a scoped user instruction from the current task;
- current Git, CI, and pull-request state;
- a fresh read of relevant repository artifacts;
- an explicit budget and editable-surface list.

The operator freezes one filled private attempt manifest outside model context, validates its referenced bytes, and renders only its allowlisted safe launch projection into the model-visible package. The raw manifest, private locators, capability evidence, denied-item details, secret references, evaluator material, and digests of structures containing them do not enter model context. A safe launch or public projection receives a new identity and digest over only allowlisted output fields; it never exposes a private input identity or digest.

Run the root brief and one filled work brief as the builder's prompt components. Use the verifier brief only through a separately reserved verifier attempt whose context omits builder reasoning and peer verdicts. A resume is another new attempt compiled from current authority and a reducer-accepted checkpoint; it never continues the old lease.

Unresolved template markers, an unaccepted implementation spec, a stale base, or missing capability evidence must be rejected by the bootstrap supervisor before launch. Prompt prose cannot reliably turn those conditions into an enforced `contract_blocked` result and does not authorize best-effort work.

Bootstrap supervision may authorize only explicitly scoped proposal work. It does not activate a production role, make a checkpoint canonical, prove verifier independence, or authorize merge or deployment.

## Future compiled use

The production harness will replace provisional fields with registered `WorkOrderSpec`, `AttemptReservation`, `AttemptDescriptor`, `ContextPackage`, role package, operation grant, event slice, evaluation epoch, `CheckpointEnvelope`, and typed checkpoint-payload records. It must enforce:

- default-branch authority and dependency status;
- actor identity, capabilities, locked and editable surfaces;
- budgets, leases, fencing, retries, idempotency, and timeouts;
- hidden-evaluation isolation;
- worktree isolation and one-writer ownership;
- exact-SHA pull-request attestation;
- human-only merge and deployment authority;
- secret resolution outside model context;
- durable checkpoints, wake triggers, cancellation, and a kill path.

Checkpoint ownership is singular. SPEC-005 owns the canonical `CheckpointEnvelope`, its acceptance lifecycle, and resumability projection. SPEC-012 registers `ContextCheckpointPayload` inside that envelope. The bundle must not invent a second envelope or `StructuredCheckpoint` lifecycle. A verifier result and a model-authored checkpoint proposal are evidence; the SPEC-005 reducer alone decides whether either changes a canonical projection.

The launch sequence is staged and fail-closed:

1. A template or compiled prompt has authority `none`.
2. A live SPEC-005 reservation allocates identity, fence, and preparation budget but grants no execution or external-effect authority.
3. The harness freezes the role, context, prompt, criteria, budget, surfaces, and private attempt manifest; it computes a safe launch projection for the model's accepted SPEC-012 profile.
4. The dispatcher intersects constitution, work order, role ceiling, mode policy, environment support, and broker-issued operation grants.
5. Only atomic SPEC-005 activation of the exact frozen bundle creates an executable descriptor and lease. Every external effect still requires its own exact operation grant and reconciliation protocol.

The prompt may explain objectives, invariants, output contracts, and evidence requirements. The harness must enforce identity, authority, information firewalls, role separation, budgets, locks, capabilities, effect idempotency, checkpoint acceptance, and termination. A hard boundary present only in prompt prose is advisory, not a production control.

Every builder or verifier attempt has one private immutable manifest. Its digest is not embedded in any member it hashes. It binds only that attempt's exact prompt components, context package and private receipt, criteria, evaluator epoch, thresholds, budget, surfaces, model, tool, adapter, authority inputs, and authoritative base. Changing a bound member creates a new attempt. Private reducers may bind the manifest to descriptors, results, receipts, and checkpoint envelopes. Model-visible and public artifacts receive safe new-identity projections instead of a private-manifest digest.

## Versioning

Freeze the private attempt manifest for one attempt. A proposed prompt change is a child candidate evaluated against a pinned parent; it never modifies the active attempt in place. Promote a prompt version only through the same candidate, evaluation, exact-SHA review, and human-merge path as other procedural artifacts.

## Verification status

The bundle has received iterative adversarial review, but this document asserts no current aggregate score. Any readiness claim must be regenerated from the exact current bundle, private-manifest template, safe projections, accepted owner specifications, and executable harness fixtures. A prompt-only rubric cannot establish runtime authority, firewall enforcement, attempt separation, or production safety.

Prior review identified blocker theater, self-asserted program completion, mutable attempt identity, self-referential checkpoint integrity, untyped contradiction/freshness fields, optional candidate audit, empty verifier coverage, ambiguous external-write recovery, self-initiated cancellation, shared builder/verifier attempts, and private-manifest leakage as failure classes. Their treatment in prose is evidence about the proposed contract only. It does not make the missing work-order, context-compiler, evaluator, credential, event, reducer, or scheduler enforcement operational.
