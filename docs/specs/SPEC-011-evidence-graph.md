# SPEC-011: Evidence Graph, Claims, Mechanisms, and Decisions

Status: draft
Wave: 2
Classification: public
Owners: evidence steward agent; mechanism curator agent; human maintainer
Depends on: SPEC-010

## Decision

Research knowledge will be represented as a provenance graph whose primary promoted units are testable claims and reusable mechanisms. Positive, negative, contradictory, superseded, and reproduction evidence remain queryable. Repeated secondary coverage never counts as independent support. Skills and harness candidates must cite graph nodes rather than free-form bibliography alone.

## Context and current repository touchpoints

`researcher/claims/index.jsonl`, `researcher/mechanisms/registry.jsonl`, accepted and rejected mechanism ledgers, novelty checks, corpus index, and source evaluation fixtures already implement much of this discipline. This spec unifies their identities and edges and adds contradiction completion, decision records, and experiment linkage.

## Goals

- Make every important statement traceable to exact evidence.
- Prevent duplicate mechanisms and citation-count inflation.
- Preserve failed ideas so agents do not rediscover them without new evidence.
- Support exact, graph, lexical, and later semantic retrieval.

## Non-goals

- A general-purpose public knowledge graph service.
- Replacing expert judgment with one weighted score.
- Erasing uncertain or conflicting evidence through forced consensus.

## Invariants

1. Claims distinguish source assertion, observed result, inference, recommendation, and volatile fact.
2. Evidence edges include location, polarity, independence group, and reviewer decision.
3. Mechanism novelty is behavioral and semantic; lexical similarity is only a screen.
4. Rejections and negative results are append-only records with reason and reconsideration trigger.
5. A promoted mechanism states activation, procedure, expected effect, failure modes, counterindications, and testable predictions.
6. Numeric and volatile claims remain indexed and reviewable.
7. A private service may recommend a semantic decision, but only reconciliation of an exact human-merged PR can create or change a public `accepted`, `rejected`, `superseded`, or `retracted` record.

## Interfaces and data

Graph node kinds are source, source version, evidence location, claim, mechanism, failure mode, skill, prompt, workflow, harness, benchmark, task, result, compatibility record, candidate, run, decision, feedback, and community response.

Core edges include `version_of`, `derived_from`, `supports`, `contradicts`, `reproduces`, `fails_to_reproduce`, `supersedes`, `implements`, `maps_to_skill`, `tested_by`, `duplicates_mechanism`, `refines_mechanism`, `accepted_as`, `rejected_because`, and `responds_to_question`.

The initial implementation uses canonical JSONL node and edge ledgers plus generated indexes, not a required graph database. APIs are `get(id)`, `neighbors(id, edge_types, depth)`, `evidence_for(claim)`, `contradictions(id)`, `nearest_mechanisms(text|id)`, and `impact(id)`.

Promotion uses sequential gates: admissibility, source value, mechanism completeness and novelty, experiment worthiness, and evaluation. Each gate stores dimension results, vetoes, uncertainty, and decision, not just a scalar score. Gate completion produces a private `review_recommended` decision and candidate export. Public decision edges are materialized only from the exact merged commit that contains them.

## State and failure behavior

Private working states include `proposed`, `under_review`, `review_recommended`, `contested`, and `review_due`. Public states include `accepted`, `rejected`, `superseded`, and `retracted` and record the merge commit and PR. New contrary evidence marks affected nodes `review_due`; it does not silently reverse decisions. Broken edges fail generation and block promotion.

## Implementation sequence

1. Import current claims, mechanisms, and ledgers with stable IDs.
2. Add edge ledger, independence groups, contradiction links, and generated indexes.
3. Extend novelty and validators to graph-aware checks.
4. Add claim and mechanism recommendation commands that create candidate branch artifacts with reviewer identity, never direct public acceptance.
5. Compile graph neighborhoods into contexts and public evidence cards.

## Migration and rollback

Migration is append-only with an import manifest. Existing files remain readable until generated parity passes. Rollback restores old readers while retaining new nodes and edges for inspection.

## Observability

Track ungrounded claims, unsupported mechanisms, contradiction backlog, duplicate candidates, independence-group concentration, review age, broken edges, source-to-skill latency, and reuse across skills.

## Verification

- Multiple articles about one paper count as one independence group.
- A contradiction query returns both sides and their exact evidence.
- Rejected mechanisms appear in novelty search.
- Superseding a source marks dependent claims for review.
- Every accepted mechanism passes structural and provenance validation.
- Attempting to mark a public node accepted without a reconciled human merge is rejected.
- A `review_recommended` node becomes public only when its exact artifact digest appears in the merged commit.
- Existing claim, mechanism, corpus, and run validators retain parity.

## Acceptance criteria

- [ ] Current claims and mechanisms have graph identities and valid edges.
- [ ] Contradiction and negative-evidence retrieval are first-class.
- [ ] Independence grouping prevents citation inflation.
- [ ] Gate decisions and reviewer identities are durable.
- [ ] No accepted mechanism lacks a testable prediction and failure boundary.
- [ ] Graph indexes rebuild deterministically.
- [ ] Every public semantic decision resolves to the exact human-merged PR and commit.

## Pull-request evidence

Attach import manifest, parity report, contradiction and duplicate fixtures, a complete source-to-mechanism trace, and generated graph integrity report.
