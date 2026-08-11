# SPEC-012: Context Compiler and Memory Planes

Status: draft
Wave: 2
Classification: split
Owners: context engineer agent; evaluation steward agent
Depends on: SPEC-003, SPEC-005, SPEC-011

## Decision

Context will be compiled as a versioned runtime-neutral artifact before any Hermes integration. A typed request passes through a role information firewall, exact and policy lookup, graph traversal with contradiction completion, lexical retrieval, optional semantic retrieval, authority and freshness ranking, deterministic budget packing, and immutable package generation. The exact package and selection log are retained for evaluation and replay.

## Context and current repository touchpoints

The repository already externalizes skills, claims, mechanisms, runs, rubrics, and benchmark fixtures. What is missing is one contract that decides what an agent sees, proves why it saw it, separates memory authorities, survives handoff, and measures context as an independent system component.

## Goals

- Produce reproducible role-bounded context packages.
- Retrieve contradictions, rejected paths, and superseding evidence when relevant.
- Keep large evidence external and progressively disclosed.
- Support direct, depth-0 externalized, and depth-1 recursive inference experiments.
- Allow itemized context improvement without monolithic memory rewrites.

## Non-goals

- One universal vector database or memory prompt.
- Persisting chain-of-thought as semantic knowledge.
- Recursive depth greater than one outside an accepted experiment.

## Invariants

1. Chat and session state are never canonical memory.
2. Constitutional, evidence, semantic, procedural, episodic, working, preference, and compatibility memory each have one canonical writer.
3. Models propose semantic, procedural, or preference deltas; deterministic or human-controlled writers accept them.
4. Summaries retain parent hashes and invalidation rules and cannot replace evidence.
5. Hidden evaluations and another first-round reviewer's verdict cannot cross role firewalls.
6. Inclusion, exclusion, compression, ordering, and truncation decisions are logged.
7. Every model call binds to one attempt and an exact ordered context package plus delta chain.
8. Wall-clock issuance metadata is not part of deterministic context content identity.

## Interfaces and data

`ContextRequest` includes work-order ID, attempt ID, causing-event ID, role, objective and output schema, required artifact IDs, query terms, graph roots, time cutoff, authority floor, contradiction policy, classification ceiling, token and section budgets, freshness policy, and exclusions. It also pins repository commit; constitution, corpus, rubric, and evaluation epochs; model and tokenizer; harness; adapter and tool-schema digests; compiler version; and index epoch. An unresolved or incompatible pin fails before retrieval.

`ContextPackageContent` includes request hash, attempt ID, epoch digest, compiler version, ordered included artifacts with digests, authority, freshness, selection reasons and token counts, derived sections with complete transform chains, excluded candidates and reasons, total tokens, remaining budget, serialized payload, and content digest. It contains no compilation time. `ContextIssuance` separately records issuance time, worker, channel, package digest, and call correlation. The packaged task brief starts with objective, constraints, exact state, success criteria, available-artifact map, and output contract.

`ContextDelta` represents any later retrieval or compaction inside the same attempt. It records call ID, parent package or delta digest, delta request, included and excluded artifacts, transforms, token change, ordered payload, and content digest. A model result records the exact ordered context chain. A context chain is append-only; replacement creates a new attempt.

`StructuredCheckpoint` contains objective and success predicate, work-order and attempt state, causing event, authority and human constraints, accepted decisions, rejected paths, unresolved contradictions, active artifact IDs and digests, branch and commit where applicable, files changed, validation and evaluation status, lease and budgets, exact next action, stop condition, and raw trace ranges. Every compaction record names its parent, covered trace range, transform, lossiness class, and invalidation inputs. Canonical fields are filled or checked deterministically; an abstractive summary is orientation only.

Memory write authorities are fixed: human merge writes constitutional and accepted procedural or semantic state; the evidence pipeline appends captured evidence; the event writer appends episodic state; the assigned attempt writes working state; confirmed feedback processing writes scoped preferences; and evaluators write compatibility observations. Models submit proposals to these writers.

Define pluggable retrievers for exact ID, graph, full-text search, and semantic search. The first operational version requires exact, graph, and SQLite FTS; semantic retrieval remains an evaluated optional stage. Packing uses stable section priorities and tie breakers so the same snapshot produces the same package.

Run-local playbook entries follow a separate itemized-delta schema with stable ID, scope, evidence pointers, helpful and harmful counters, last validation, and supersession. They must not be confused with per-call `ContextDelta` artifacts. Whole-playbook rewrites are rejected.

## State and failure behavior

Compilation moves `requested -> pins_resolved -> authorized -> retrieved -> contradiction_completed -> packed -> frozen -> issued`. Missing required artifacts fail. Optional retrieval failures create an explicit degraded package only when policy permits. A source or policy change invalidates dependent packages for future use but never rewrites the historical package. A checkpoint moves `proposed -> canonical_fields_verified -> probe_validated -> resumable`, with terminal `invalid` or `superseded`.

## Implementation sequence

1. Define memory authorities, attempt-scoped request, deterministic package content, issuance, delta, selection-log, and checkpoint schemas.
2. Implement exact and graph retrieval plus contradiction completion.
3. Add FTS, freshness, authority, role filters, and deterministic packing.
4. Add immutable per-call deltas, structured checkpoints, compaction chains, and fresh-context probe validation.
5. Build context evaluation fixtures before enabling semantic search or RLM routing.

## Migration and rollback

Existing prompts and skill loading remain the control condition. Shadow runs build packages without changing agent inputs, then compare expected inclusions. Activation is per role and work-order kind. Rollback returns to the pinned control and retains packages for analysis.

## Observability

Measure required-fact recall, irrelevant-context precision, contradiction recall, stale-item rate, role leakage, tokens by section, exclusions by reason, retrieval calls, delta-chain length, compaction loss, checkpoint probe failures, latency, cost, task success, order sensitivity, handoff recovery, and cross-model transfer.

## Verification

- Same fully pinned request and artifact snapshot produce identical content bytes and digest; issuance events may have different times.
- Every model call resolves to one attempt and exact package-plus-delta chain.
- Reviewer fixtures cannot retrieve peer verdicts or hidden evals.
- Contradictory evidence is included when policy requires it.
- Stale summaries invalidate when parent digests change.
- Required evidence exceeding budget fails visibly rather than truncating silently.
- Depth-0 and depth-1 experiments obey call and cost limits.
- A fresh process resumes from a checkpoint and correctly answers objective, authority, state, human decisions, active artifacts, contradictions, completed tests, next action, and external-action permission.
- A checkpoint that disagrees with the event journal or repository cannot become resumable.

## Acceptance criteria

- [ ] Every executor receives a `ContextPackage`, not ad hoc transcript memory.
- [ ] All eight memory classes have explicit canonical writers.
- [ ] Role firewalls have positive and negative fixtures.
- [ ] Exact, graph, FTS, and packing stages are replayable.
- [ ] Package identity excludes nondeterministic issuance metadata.
- [ ] Context deltas and checkpoints have immutable provenance, validation, and invalidation contracts.
- [ ] Context quality has a pinned baseline and evaluation dataset.
- [ ] Semantic retrieval and recursive depth remain gated until they beat controls.

## Pull-request evidence

Attach compiler conformance report, deterministic-package proof, firewall tests, contradiction fixture, context baseline, handoff recovery result, and package provenance example.
