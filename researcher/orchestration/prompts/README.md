# Long-Horizon Organization Briefs

Status: bootstrap proposal
Owner specifications: SPEC-005, SPEC-012, SPEC-013
Authority: none until the owner specifications are accepted and implemented

This directory contains a supervised bootstrap prompt bundle for advancing the specification program. It is source material for a future prompt compiler, not a production role manifest and not an authorization mechanism.

## Components

| File | Purpose |
| --- | --- |
| `organization-root-brief.md` | Stable mission, definitions, invariants, orchestration policy, and return gate |
| `spec-work-brief.template.md` | Per-wake work contract for one exact authoritative spec or vertical slice |
| `fresh-verifier-brief.md` | Independent adversarial review without builder history or prior verdicts |
| `resume-brief.template.md` | Restart from a validated durable checkpoint |

The dated readiness review at `docs/reviews/2026-08-15-autonomous-organization-readiness.md` records the evidence and limitations that motivated this split.

## Why this is a bundle

One perpetual model trajectory would mix authority, implementation history, evaluator context, and transient session memory. The intended organization instead performs bounded event-driven attempts:

```text
authoritative state + external event
  -> authority and dependency check
  -> compiled work brief and context package
  -> bounded builder attempt
  -> frozen candidate or typed blocker
  -> fresh-context verification
  -> exact-SHA review packet
  -> human merge or scoped feedback
  -> durable checkpoint and next wake
```

Session lifetime is never work lifetime. Chat history, framework memory, and a model's internal plan are not canonical state.

## Bootstrap use

Before SPEC-005, SPEC-012, and SPEC-013 are implemented, a human operator may fill the work template from:

- the protected default-branch constitution and specification bytes;
- a scoped user instruction from the current task;
- current Git, CI, and pull-request state;
- a fresh read of relevant repository artifacts;
- an explicit budget and editable-surface list.

Run the root brief and one filled work brief together. Use the verifier brief in a fresh context that does not contain the builder transcript. If the attempt must resume, compile the resume brief from a checkpoint whose artifact identities and test evidence can be revalidated.

Unresolved template markers, an unaccepted implementation spec, a stale base, or missing capability evidence produce `contract_blocked`. They do not authorize best-effort work.

## Future compiled use

The production harness will replace provisional fields with registered `WorkOrder`, `ContextPackage`, role manifest, capability grant, event slice, evaluation epoch, and `StructuredCheckpoint` records. It must enforce:

- default-branch authority and dependency status;
- actor identity, capabilities, locked and editable surfaces;
- budgets, leases, fencing, retries, idempotency, and timeouts;
- hidden-evaluation isolation;
- worktree isolation and one-writer ownership;
- exact-SHA pull-request attestation;
- human-only merge and deployment authority;
- secret resolution outside model context;
- durable checkpoints, wake triggers, cancellation, and a kill path.

The prompt may explain these rules. It cannot substitute for their enforcement.

Every attempt also has one external immutable manifest. Its digest is not embedded in any member it hashes. The manifest binds the exact root, filled work brief, verifier, and resume prompt bytes; context package; criteria; evaluator epoch; thresholds; budget; editable and locked surfaces; model, tool, and adapter identities; and authoritative base. The checkpoint, verifier result, and review packet all reference that digest. Changing any member creates a new attempt.

## Versioning

Freeze the external attempt manifest for one attempt. A proposed prompt change is a child candidate evaluated against a pinned parent; it never modifies the active attempt in place. Promote a prompt version only through the same candidate, evaluation, exact-SHA review, and human-merge path as other procedural artifacts.

## Prompt-level red team

After three correction rounds, a fresh-context adversarial review scored bootstrap-v1 `20/20` on the `long-horizon-prompting` skill rubric: success predicate, definitions, non-counting outcomes, auditor checklist, persistence/verification pairing, return condition, diversity policy, reporting contract, contamination guards, and prompt/harness separation each scored `2/2`.

The review closed blocker theater, self-asserted program completion, mutable attempt identity, self-referential checkpoint integrity, untyped contradiction/freshness fields, optional candidate audit, empty verifier coverage, ambiguous external-write recovery, and self-initiated cancellation. This is evidence about the prompt contract only. It does not make the missing work-order, context-compiler, evaluator, credential, event, or scheduler enforcement operational.
