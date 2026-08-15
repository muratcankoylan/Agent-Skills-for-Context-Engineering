# SPEC-011: Evidence Graph, Claims, Mechanisms, and Decisions

Status: draft
Revision: 1
Revises: none
Wave: 2
Classification: split
Owners: evidence steward agent; mechanism curator agent; human maintainer
Depends on: SPEC-002, SPEC-004, SPEC-005, SPEC-006, SPEC-007, SPEC-010

## Decision

Research knowledge will use immutable claim assertions, evidence relations, mechanism records, decision proposals, and reducer-accepted scoped graph decisions. Private proposal and review graphs may contain restricted evidence, candidate identities, feedback, and working recommendations. Public graph projections introduce safe new identities and content, but cannot claim their own future merge commit or acceptance. After a human merge, the SPEC-011 graph projector derives acceptance mappings from the exact SPEC-007 repository-acceptance event and merged tree; it does not ask the repository reconciler to write graph state.

Positive, negative, contradictory, superseded, and failed-reproduction evidence remain queryable. Repeated coverage does not count as independent support merely because it uses different URLs. Skills and harness candidates must cite graph identities and exact evidence locations rather than a free-form bibliography alone.

## Context and current repository touchpoints

`researcher/claims/index.jsonl`, `researcher/mechanisms/registry.jsonl`, accepted and rejected mechanism ledgers, novelty checks, corpus index, and source-evaluation fixtures already implement much of this discipline. This spec separates assertions from verdicts, unifies their identities and edges, and adds contradiction completion, scoped decisions, safe public projection, and experiment linkage.

## Goals

- Make every important assertion traceable to exact captured evidence and location.
- Prevent duplicate mechanisms, citation-count inflation, and self-asserted acceptance.
- Preserve rejected and failed paths with explicit reconsideration triggers.
- Keep restricted review state private while making accepted public knowledge auditable.
- Support exact, graph, lexical, and later evaluated semantic retrieval.

## Non-goals

- A general-purpose graph service.
- Replacing expert judgment with one weighted score.
- Erasing uncertainty or conflicting evidence through forced consensus.
- Treating a citation, source class, or mechanism proposal as an accepted fact by itself.

## Invariants

1. Assertions, evidence relations, decision proposals, and accepted decisions are immutable records with independent identities; correction creates a superseding record.
2. Claims distinguish source assertion, observed result, inference, recommendation, and volatile fact, including applicable scope and conditions.
3. Evidence relations bind exact SPEC-010 capture locations, polarity, relevance, qualifications, reviewer, and a justified independence group.
4. Independence is an evidence relation. Shared authors, datasets, code, funding, evaluation sets, or derivation constrain independence even when publications differ.
5. Mechanism novelty is behavioral and semantic; lexical similarity is only a screen.
6. Rejections and negative results are append-only and state the scope, reason, evidence, and reconsideration trigger.
7. Citation-only evidence cannot be the sole support for a volatile, numeric, safety-relevant, or promotion-critical assertion.
8. A candidate cannot assert a merge SHA, acceptance state, or authority it does not yet have.
9. Only deterministic verification of exact bytes in a SPEC-007-accepted human merge creates a public acceptance mapping; merge never retroactively mutates the proposed records.
10. Agents and executors submit graph proposals only. One graph reducer owns accepted private decisions, while one pure SPEC-011 projector owns post-merge acceptance mappings and has no pointer, GitHub, promotion, or deployment write surface.

## Interfaces and data

Core immutable records are:

- `ClaimAssertion`: assertion kind, normalized statement, scope and population, units, boundary conditions, volatility class, authoring principal, creation cause, and evidence requirements.
- `EvidenceRelation`: assertion or mechanism subject, SPEC-010 capture and exact location, relation kind (`supports`, `contradicts`, `fails_to_reproduce`, `qualifies`, or `citation_only`), polarity, relevance scope, strength rationale, limitations, independence-group ID and justification, and reviewer provenance.
- `MechanismRecord`: activation conditions, procedure, expected effect, causal account or engineering rationale, failure modes, counterindications, testable predictions, related mechanisms, and scope.
- `GraphDecisionProposal`: exact subject and input digests, proposed decision kind and scope, gate results and vetoes, uncertainty, reason, reviewer principal, attempt and fencing references, causing event, reconsideration trigger, and optional decision proposed for supersession. It has no accepted authority or state-changing effect.
- `GraphDecision`: the reducer-accepted form of one proposal, with checked subject version, decision scope, authority reference, application event, reducer version, and optional superseded decision.
- `PublicGraphProjection`: public-safe new identities, assertions, mechanisms, relations, and citations. It contains neither acceptance state nor a prospective merge or PR identity.
- `AcceptanceMapping`: a registered deterministic SPEC-011 projection record binding one public graph-projection digest to the source SPEC-007 `RepositoryAcceptanceEvent`, merged tree and commit, PR identity, accepted scope, and projector version. It is rebuilt from the immutable repository-acceptance event plus exact merged tree and is neither a second acceptance event nor a caller-authored mutation. One repository merge may yield zero or more mappings; none is required to advance the repository pointer.
- `PublicAcceptanceLedger`: a deterministic new-identity public projection of prior acceptance mappings. Each entry binds a public graph-projection identity and output digest, accepted scope, human merge PR and commit, projection version, and ledger cutoff. It contains no private record identity or digest. A later agent-opened maintenance PR may publish entries for already reconciled merges; its own new bytes remain `pending_reconciliation` until a later ledger entry exists.

Other graph node kinds include work identity, manifestation, source version, capture, evidence document, failure mode, skill, prompt, workflow, harness, benchmark, task, result, compatibility record, candidate, run, feedback, and community response. Node kinds do not imply public classification.

Core edges include `version_of`, `manifestation_of`, `captured_as`, `derived_from`, `supports`, `contradicts`, `reproduces`, `fails_to_reproduce`, `qualifies`, `supersedes`, `implements`, `maps_to_skill`, `tested_by`, `duplicates_mechanism`, `refines_mechanism`, `decision_about`, `accepted_as`, `rejected_because`, and `responds_to_question`.

The first implementation uses append-only repository JSONL for graph content plus deterministic generated indexes. Private decision proposals and accepted decisions are journal events with reducer projections; acceptance mappings are rebuildable SPEC-011 projection records derived from the immutable SPEC-007 acceptance events and exact repository trees. None is a repository JSONL assertion. The live accepted graph view deterministically joins an exact repository tree with the journal prefix containing its repository-acceptance sources. A public-clone view joins the tree with `PublicAcceptanceLedger` and labels any newer or unmapped public record `pending_reconciliation`, never accepted by file presence alone. Required query APIs are `get(id)`, `neighbors(id, edge_types, depth)`, `evidence_for(assertion_id)`, `contradictions(id)`, `nearest_mechanisms(text|id)`, `decision_history(id)`, and `impact(id)`. Live responses carry repository graph root, journal sequence and chain digest; public-clone responses carry repository graph root and ledger cutoff. Both carry query implementation version.

## Review and acceptance protocol

Promotion uses separately recorded gates: admissibility, source and capture fitness, assertion completeness, mechanism completeness and novelty, experiment worthiness, and evaluation evidence when applicable. Gates store dimension results, vetoes, uncertainty, reviewer identity, and exact inputs rather than one scalar alone.

Agent review can submit a private `GraphDecisionProposal` such as `recommend_public_projection`, `reject_in_scope`, or `request_evidence`. The graph reducer validates the work order, attempt fence, expected subject version, evidence integrity, reviewer assignment, authority, and decision schema before appending `GraphDecision`; a stale or denied proposal remains evidence but has no graph effect. A proposal PR contains only the safe `PublicGraphProjection`. Its records remain ineligible for accepted downstream use until SPEC-007 emits the exact contiguous `RepositoryAcceptanceEvent` and the SPEC-011 projector verifies their digests in that merged tree and derives `AcceptanceMapping`. A later public export projects prior mappings into `PublicAcceptanceLedger` under new identities; no record is rewritten to add its own historical merge SHA.

Acceptance is scoped. A mechanism may be accepted as an experiment candidate without being accepted as an effective skill change; a claim may be accepted for one population, version, or time window without becoming universal. Consumers must request a decision scope and cannot infer a stronger one.

## State and failure behavior

Private review projections include `proposed`, `under_review`, `recommended`, `contested`, and `review_due`. They are graph-reducer projections over proposals and decisions. Public projection presence and derived `AcceptanceMapping` existence are separate facts, not mutable node states. Deleting the graph projection database and replaying the same repository-acceptance prefix reproduces identical mappings. New contrary evidence appends relations and causes the reducer to mark affected subjects review-due; it never reverses a prior decision silently.

Broken identities, missing captures, invalid anchors, prospective merge fields, self-referential records, or edges outside their allowed node kinds fail generation and block promotion. Restricted input raises the private review graph's classification; a safe public projection must be produced as a new artifact under SPEC-002 rather than relabeling the private graph.

## Implementation sequence

1. Define assertion, evidence relation, mechanism, decision-proposal, reducer decision, public projection, and deterministic acceptance-mapping schemas.
2. Import current claims, mechanisms, and ledgers with stable identities and an explicit mapping manifest.
3. Add independence groups, contradiction links, decision history, and deterministic generated indexes.
4. Add recommendation commands that create private decision proposals and public projection candidates without acceptance metadata; add the single graph reducer and stale-fence tests.
5. Project exact human-merge acceptance events into zero or more deterministic mappings, compile live accepted neighborhoods, and generate the public acceptance ledger for a later maintenance PR.

## Migration and rollback

Migration is append-only and preserves legacy identifiers through an import map. Existing readers remain available until generated parity passes. Rollback pins an older index or reader while retaining new records. Incorrect graph content is corrected by superseding assertions, relations, decisions, or identity maps, never by editing accepted history.

## Observability

Track ungrounded assertions, citation-only critical claims, unsupported mechanisms, contradiction backlog, duplicate candidates, independence-group concentration, decision age, review-due age, broken edges, restricted-to-public projection failures, reconciliation lag, source-to-skill latency, and mechanism reuse across skills.

## Verification

- Multiple articles derived from one paper remain one independence group unless reviewed evidence proves otherwise.
- A contradiction query returns both sides, exact capture locations, qualifications, and decision scope.
- A fresh public clone resolves every claimed accepted public record and scope from public tree/history plus the acceptance ledger; unmapped files remain `pending_reconciliation`.
- Rejected mechanisms and failed reproductions appear in novelty search.
- Superseding a source version marks dependent assertions for review without rewriting them.
- A citation-only relation cannot solely promote a volatile or promotion-critical assertion.
- A candidate containing its own alleged merge SHA or accepted state is rejected.
- A public projection becomes eligible only after its exact digest is reconciled from a human-merged tree.
- An agent-authored decision, stale-fenced proposal, or repository-authored acceptance mapping cannot change the accepted graph view.
- Rebuilding from one repository-acceptance event and merged tree yields the same zero-or-more mapping set; the graph projector cannot advance the accepted pointer or append a second acceptance event.
- Restricted review inputs cannot leak through a reused digest or mutable classification field.
- Existing claim, mechanism, corpus, and run validators retain parity after import.

## Acceptance criteria

- [ ] Current claims and mechanisms have immutable graph identities and valid provenance relations.
- [ ] Contradiction, qualification, rejection, and negative-evidence retrieval are first-class.
- [ ] Independence grouping uses explicit evidence and prevents citation inflation.
- [ ] Decisions are scoped, immutable, attributable, and separate from assertions.
- [ ] Decision proposals, reducer-accepted decisions, and projector-derived acceptance mappings have separate schemas and single owners.
- [ ] No accepted mechanism lacks activation, procedure, prediction, and failure boundaries.
- [ ] Private review graphs and public projections have enforceable classification boundaries.
- [ ] Graph indexes rebuild deterministically from a pinned snapshot.
- [ ] Every accepted public semantic record resolves through an exact post-merge acceptance mapping.

## Pull-request evidence

Attach schema goldens, import manifest and parity report, contradiction and independence fixtures, citation-only gate failure, proposal/decision stale-fence tests, private-to-public projection test, prospective-merge and repository-mapping rejection, exact post-merge journal reconciliation proof, and a complete capture-to-mechanism trace.
