# SPEC-012: Context Compiler and Memory Planes

Status: draft
Revision: 1
Revises: none
Wave: 2
Classification: split
Owners: context engineer agent; evaluation steward agent
Depends on: SPEC-003, SPEC-004, SPEC-005, SPEC-006, SPEC-008, SPEC-010, SPEC-011

## Decision

Context will be compiled as a versioned runtime-neutral artifact before runtime integration. SPEC-012 owns the information-firewall contract through an accepted `ContextProfile`; SPEC-013 roles bind to profiles rather than defining firewall policy themselves. An authorized request passes through exact lookup, graph traversal with bounded contradiction completion, lexical retrieval, optional evaluated semantic retrieval, authority and freshness ranking, deterministic budget packing, and immutable package generation.

The model-visible `ContextPackage` contains only the ordered authorized content needed for the call. A separate private `ContextCompilationReceipt` records the candidate universe, denials, exclusions, scores, transforms, diagnostics, and snapshot details. Denied identities, counts, and reasons never enter model context unless a separately classified safe projection explicitly permits them.

## Context and current repository touchpoints

The repository externalizes skills, claims, mechanisms, runs, rubrics, and benchmark fixtures. It lacks one contract that decides what a principal may inspect, proves how visible content was selected, separates memory authorities, survives handoff, and lets evaluation change context policy without coupling it to a particular harness.

## Goals

- Produce reproducible principal-, role-, and audience-bounded context packages.
- Retrieve contradictions, rejected paths, superseding evidence, and authority limits when policy requires them.
- Keep large evidence external and progressively disclosed through explicit artifact maps.
- Make context selection, packing, compaction, and handoff independently evaluable.
- Support direct, depth-0 externalized, and bounded depth-1 recursive inference experiments.

## Non-goals

- One universal vector database or memory prompt.
- Persisting hidden chain-of-thought as semantic knowledge.
- Allowing model-visible packages to explain what confidential material was denied.
- Recursive depth greater than one outside an accepted experiment.

## Invariants

1. Chat, session, and executor memory are never canonical organizational state.
2. Constitutional, evidence, knowledge, episodic, working, preference, and compatibility memory are the seven canonical memory classes. Each has exactly one declared writer path.
3. Models and executors emit immutable proposals, results, graph assertions, SPEC-005 checkpoint envelopes, cursor receipts, and delivery receipts. Reducers alone apply canonical state after schema, authority, expected-version, and fencing validation.
4. A `ContextProfile` constrains every retrieval stage and cannot be widened by a work order, prompt, retriever, model, or delta.
5. Hidden evaluations, peer first-round verdicts, private feedback, and restricted candidate identities cannot cross their profile boundaries.
6. The compilation receipt records inclusion, exclusion, compression, ordering, truncation, and diagnostics; those details are not automatically model-visible.
7. Every model call binds to one attempt, one exact ordered package, and any permitted narrowing-delta chain.
8. A context delta may narrow or compact existing visible content but cannot add identities, raise classification, lower authority requirements, or expand the profile. Expansion requires a new request under a new SPEC-005 attempt reservation.
9. Private compilation lineage retains exact parent digests and invalidation rules. Model-visible lineage includes a parent digest only when that exact parent identity and content are independently visible under the same profile; otherwise it uses a new safe derived identity and anchor. Summaries remain orientation aids and never replace evidence.
10. Wall-clock issuance metadata is excluded from deterministic context content identity.

## ContextProfile and authorization

`ContextProfile` is a versioned accepted policy artifact with principal and audience classes; allow and deny domains; classification ceiling; authority floor; permitted memory planes and retrieval stages; hidden-evaluation and peer-review rules; contradiction policy; freshness policy; per-stage and total budgets; allowed transform classes; public-projection policy; and failure behavior. Deny rules take precedence. A profile has conformance fixtures and an acceptance mapping; a role may reference only an accepted compatible version.

Context preparation starts only after SPEC-005 has created an immutable `AttemptReservation`. A reservation allocates the proposed attempt ID, work-order version, lease generation, fencing token, preparation budget, preparation deadline, and policy-context digest without starting an execution lease. The compiler neither creates nor renews the reservation. A failed, expired, or superseded reservation cannot issue a package; SPEC-005 owns its release and recovery.

`ContextRequest` includes the reservation ID and digest, work-order and proposed-attempt IDs and versions, causing-event ID, fencing token, requesting principal, accepted context-profile digest, objective and output schema, required artifact IDs, safe query terms, graph roots, cutoff, budget request, exclusions, and desired retrieval stages. A `role_package_digest` is an optional registered extension until SPEC-013 is active and is mandatory for role-based execution thereafter; standalone SPEC-012 conformance uses a registered requester-contract fixture instead of inventing a role. Authorization intersects the profile with the constitution, reserved work order, current mode and deployment policy, and principal grant. The request cannot relax the profile or outlive the reservation.

The request pins repository tree; constitution, corpus, graph, and feedback epochs; source and artifact cutoffs; compiler; retriever implementations; SQLite library, FTS version and tokenizer configuration; collation and normalization rules; index root; and stable tie-breakers. Tokenizer is required whenever a token budget is enforced. Role package, model, semantic-retrieval model, rubric, and evaluation-epoch pins are feature-dependent: their registered fields use an explicit `not_applicable` value until the owning later contract is active, never a fabricated digest. An unresolved, incompatible, or mutable required pin fails before retrieval.

## Compilation artifacts

`ContextPackage` is model-visible and private by default. It includes only a safe profile-projection version, compiler version, typed task brief, ordered authorized content items with their safe IDs and content digests, evidence anchors, authority and freshness annotations when permitted, derived sections with safe derived identities, conditionally visible parent anchors, and transform classes, token counts by visible section, remaining budget, serialized payload, and package digest. A parent digest appears only if that exact parent is itself visible under the same profile; denied or restricted parents remain bound solely in the private receipt. Exact request, reservation, profile, repository, index, and epoch roots remain only in the private compilation receipt and attempt descriptor; their digests are not exposed as equality oracles across a firewall. The package contains no excluded candidate list, denial count, secret locator, compilation time, worker identity, unsafe diagnostic, or digest of a structure containing any of those fields. It becomes executable only if SPEC-005 atomically activates the same reservation and privately binds the receipt and package digests into the immutable attempt descriptor; activation failure leaves the package historical but unusable.

`ContextCompilationReceipt` is a private audit artifact. It includes the complete inspected candidate universe; allow and deny decisions; exclusion reasons; retrieval scores and tie-break inputs; contradiction frontier and stopping reason; truncation and transform details; index and implementation pins; warnings; compiler diagnostics; and the resulting package digest. Its classification is the join of every inspected input and diagnostic, even if the final visible package contains only public material. A safe public or model-visible report must be rendered as a new projection with a new identity and policy check.

`ContextIssuance` separately records issuance time, worker, channel, package digest, attempt, call correlation, and delivery result. Reissuing identical content can produce distinct issuance records without changing the package digest.

`ContextNarrowingDelta` records a call ID, parent package or delta digest, removed or compacted visible items, transform lineage, token change, ordered payload, and digest. It cannot retrieve new content. A model result records the exact package and delta chain it observed.

The task brief starts with objective, constraints, exact reducer-projected state, success criteria, available-artifact map, human decisions, effective authority, and output contract. External source text is placed in typed evidence sections as data; it never occupies constitutional, role, tool, or policy instruction slots.

## Retrieval and packing

Required retrievers are exact ID, graph, and SQLite FTS. Semantic retrieval remains an optional evaluated stage with a pinned model and index. Each stage operates on the same immutable snapshot and produces deterministic candidate records before authorization and packing.

Contradiction completion has a mandatory independent budget, bounded depth, edge allowlist, visited-set rule, and stable ordering. The receipt proves frontier exhaustion or the exact stopping condition. If a required contradiction cannot fit or cannot be inspected, compilation fails. Where policy permits degradation, the visible package contains only a generic policy-approved `relevant_material_withheld` marker that reveals neither identity nor count, and the private receipt contains the reason.

Packing uses stable section priorities, token accounting, collation, and final tie-breakers. Required material that exceeds its budget fails visibly. Optional material can be omitted only with a receipt entry. Order sensitivity is evaluated; it is never dismissed as an implementation detail.

## Checkpoint payload and memory writes

SPEC-005 exclusively owns the `CheckpointEnvelope`, its lifecycle, acceptance event, and resumability projection. SPEC-012 registers `ContextCheckpointPayload` as one payload kind inside that envelope; it does not redefine or append a second checkpoint object. The payload contains objective and success predicate, accepted human decisions, rejected paths, unresolved contradictions, active artifact IDs and digests, branch and commit where applicable, files changed, validation and evaluation status, budget usage, exact next action, stop condition, and trace ranges. Envelope fields supply work-order and attempt references, causation, expected version, authority, and fencing token.

The SPEC-012 payload validator checks artifact integrity, repository consistency, context lineage, compaction lineage, and required fields, then returns a validation receipt to the SPEC-005 reducer. Only that reducer may accept the envelope and create resumable working state. Compaction records name their parent, covered trace range, transform, lossiness class, and invalidation inputs. Canonical fields are reducer-derived or checked; abstractive summaries remain orientation only.

The seven memory classes and their sole writer paths are:

1. `constitutional`: the constitution projector is the sole canonical writer and consumes only protected human-merge reconciliation events;
2. `evidence`: one evidence-memory reducer is the sole canonical writer and consumes integrity-verified SPEC-010 captures and SPEC-011 evidence decisions without granting those producers direct plane access;
3. `knowledge`: one knowledge-memory reducer is the sole canonical writer and consumes accepted claim, mechanism, skill, prompt, and procedure records plus their human-merge acceptance mappings;
4. `episodic`: SPEC-004 journal append is the sole fact writer and deterministic projectors produce views;
5. `working`: the SPEC-005 work-order reducer, including accepted checkpoint envelopes, is the sole canonical writer;
6. `preference`: the SPEC-006 feedback reducer writes only confirmed, scoped, future-effective preferences; and
7. `compatibility`: one compatibility-memory reducer is the sole canonical writer and consumes scoped conformance and evaluation observations for models, executors, skills, and harnesses.

`MemoryDeltaProposal` is the only model-originated memory-change contract. It binds memory class, base version or root, proposed operation, content artifact references, evidence, scope, classification, attempt and fence, invalidation inputs, and requested owning reducer. It grants no write authority. The relevant sole writer either rejects it or emits a separately identified accepted record after schema, authority, expected-version, evidence, and fencing checks. A model cannot submit an accepted memory record, confirmation, acceptance mapping, or constitutional event directly.

Run-local playbook changes use `PlaybookDeltaProposal`, a typed `MemoryDeltaProposal` subtype with stable item ID, scope, evidence pointers, helpful and harmful counters, last validation, and supersession. They are not per-call context deltas, cannot write the playbook directly, and whole-playbook rewrite proposals are rejected.

## State and failure behavior

Compilation moves `reservation_bound -> requested -> pins_resolved -> authorized -> retrieved -> contradiction_completed -> packed -> frozen -> activation_bound -> issued`, with terminal `reservation_expired`, `invalid`, or `unbound`. `activation_bound` requires the SPEC-005 activation receipt for the exact reservation, package, bundle, and fence; no model-visible issuance precedes it. Missing required artifacts, profile conflicts, snapshot drift, unbounded contradiction frontiers, incompatible pins, reservation expiry, or fence drift fail. Optional stage failure yields a degraded package only when the profile permits it. Source or policy changes invalidate a historical package for future issuance but never alter its bytes.

Context-checkpoint payload validation returns `valid` or `invalid` only; SPEC-005 owns `proposed`, accepted, resumable, superseded, and terminal checkpoint state. A stale-fenced envelope or one that disagrees with journal or repository state cannot become resumable.

## Implementation sequence

1. Define `ContextProfile`, reservation-bound authorization, request, visible package, private compilation receipt, issuance, narrowing delta, `ContextCheckpointPayload`, and memory-delta proposal schemas.
2. Implement exact and graph retrieval, mandatory bounded contradiction completion, and profile firewalls.
3. Add pinned FTS snapshotting, freshness and authority filters, deterministic packing, and classification joins.
4. Add SPEC-005 checkpoint-envelope payload validation, compaction chains, memory-writer conformance, and fresh-context recovery probes.
5. Build context evaluation fixtures before semantic retrieval or recursive routing is eligible for activation.

## Migration and rollback

Existing prompts and skill loading remain the control condition. Shadow compilation writes only isolated packages, receipts, and shadow comparison projections; it cannot affect authoritative reducers or active contexts. Activation is per accepted profile and work-order kind. Rollback pins the prior profile and compiler and retains every package and receipt for comparison.

## Observability

Measure required-fact recall, irrelevant-context precision, contradiction recall and completion status, stale-item rate, firewall leakage, tokens by visible section, private exclusions by reason, retrieval calls, delta-chain length, compaction loss, checkpoint rejection and probe failures, latency, cost, task success, order sensitivity, handoff recovery, and cross-model transfer. Public telemetry uses safe aggregates that cannot reveal denied identities or counts.

## Verification

- The same pinned request, profile, implementation versions, and snapshot produce identical package bytes and digest; issuance times may differ.
- FTS library, tokenizer, collation, graph-root, or tie-breaker changes change the compilation epoch or fail replay.
- Every model call resolves to one attempt and exact package-plus-narrowing chain.
- A context request cannot precede, outlive, or bind a different SPEC-005 attempt reservation, and only activation of that reservation makes the package executable.
- Reviewer fixtures cannot infer peer verdict identities, hidden evaluations, private feedback, or denied-item counts.
- Two denied or restricted parents producing the same allowed summary expose identical safe lineage metadata; changing an independently visible parent changes its visible lineage binding.
- Required contradictions are included or compilation fails; permitted withheld markers reveal no protected identity or count.
- The compilation receipt classification joins all inspected inputs even when the visible package is lower-classified.
- A delta that adds an artifact or broadens access is rejected and requires a new attempt.
- A model-originated memory delta cannot bypass its class's sole writer or become an accepted memory record directly.
- Stale summaries invalidate when parent digests change.
- A fresh process resumes from a SPEC-005 checkpoint envelope containing a validated context payload without session history.
- A checkpoint envelope whose context payload disagrees with the journal, repository, authority, or fencing state is rejected by the SPEC-005 reducer.

## Acceptance criteria

- [ ] Every executor receives an authorized `ContextPackage`, not ad hoc transcript memory.
- [ ] `ContextProfile` is runtime-neutral, accepted, versioned, and tested independently of role manifests.
- [ ] Visible packages and private compilation receipts have distinct schemas and classification behavior.
- [ ] All seven memory classes have exactly one reducer or human-merge-controlled writer path.
- [ ] Models can emit only `MemoryDeltaProposal`; accepted memory records always have a distinct writer-owned identity.
- [ ] Exact, graph, FTS, contradiction, and packing stages are replayable from fully pinned snapshots.
- [ ] Package identity excludes issuance metadata and protected exclusion details.
- [ ] Deltas can only narrow; expansion creates a new authorized attempt.
- [ ] Reservation, compilation, issuance, and attempt activation order is enforced across crashes and concurrent dispatch.
- [ ] Context quality has a pinned baseline and firewall dataset.
- [ ] Semantic retrieval and recursive depth remain gated until they beat controls.

## Pull-request evidence

Attach profile and compiler conformance reports, attempt-reservation ordering and expiry tests, deterministic-package proof, classification-join and denied-identity tests, contradiction exhaustion and budget fixtures, FTS replay test, context-delta expansion rejection, seven-writer and model-delta negative fixtures, SPEC-005 checkpoint-payload validation, handoff recovery result, and package-versus-receipt provenance example.
