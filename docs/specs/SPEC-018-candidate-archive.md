# SPEC-018: Candidate Archive, Failure Memory, and Lineage

Status: draft
Revision: 1
Revises: none
Wave: 3
Classification: split
Owners: meta-harness archivist agent; evaluation steward agent
Depends on: SPEC-003, SPEC-012, SPEC-016, SPEC-017

## Decision

Every evaluated change will be an immutable candidate in an append-only lineage graph. The archive retains development code, authorized development traces, failures, costs, results, reviewer decisions, and rejected or exploit candidates. Hidden evaluation material remains in a separately authorized evaluator archive and is never a candidate-search retrieval source. Candidates never acquire a mutable score; evaluations are observations under named epochs, and candidate-authored evidence is never accepted as an evaluation or promotion decision.

## Context and current repository touchpoints

SPEC-003 supplies the minimal identity and freeze contract required before evaluation. Current research runs and benchmark results preserve substantial evidence, but skill revisions, harness variants, failed attempts, evaluation observations, and organization changes do not yet share one searchable ancestry and experience archive. Meta-harness research depends on raw experience, including failures, rather than summaries or leaderboards alone.

## Goals

- Prevent rediscovery of rejected or exploitative changes without new evidence.
- Support parent selection, ablation, reproduction, and longitudinal analysis.
- Separate candidate content from evaluation and promotion decisions.
- Preserve full development traces while exporting safe public summaries.

## Non-goals

- Giving candidate authors access to hidden traces.
- Storing unrestricted chain-of-thought as public evidence.
- Deleting losing candidates to save leaderboard space.

## Invariants

1. Candidate content freezes when evaluation begins; revision creates a child.
2. Candidate identity includes artifact digest, parent IDs, root production epoch, target rung, and editable surfaces.
3. Raw trace, checkpoint, summary, and public report are distinct artifacts.
4. A score binds candidate, epoch, evaluator, and result digest.
5. Exploit and integrity failures remain searchable and become future adversarial fixtures only in later epochs.
6. Archive queries respect role firewalls and classification.
7. A candidate may carry a causal hypothesis, development evidence, and requested gates, but it cannot carry or infer hidden-task content, claim a hidden result, waive a gate, select its evaluator, or mark itself PR-eligible.
8. Proposer and search retrieval excludes current or prior hidden task-level traces, private attestation seals, evaluator diagnostics, and current-epoch exploit details that would contaminate the search.
9. Candidate similarity, lineage, popularity, or Pareto position is retrieval evidence only; none is authority or proof of quality.
10. A no-resuggest record names its evidence, scope, expiry or reconsideration trigger; materially new evidence creates a child proposal rather than erasing the prior rejection.
11. Pareto comparisons are valid only within the same sealed epoch, cost profile, and compatibility scope, or under an accepted bridge that makes the comparison explicit.
12. Search memory retains observable inputs, actions, tool receipts, artifacts, verifier outcomes, and decisions. Hidden model chain-of-thought is neither required evidence nor a condition of reproducibility.
13. Candidate lineage is a topologically appended DAG. A non-sentinel parent must already exist and be frozen under a compatible production root and base relation; orphan, forward, self, cyclic, and cross-root edges fail before storage.

## Interfaces and data

`Candidate.id` is a registered typed immutable identifier. The record binds the SPEC-003 freeze receipt and candidate-snapshot digest, exact base commit and tree, type, parents, production root, target editable-surface rung, complete editable-surface manifest, changed files or controls, failure clusters, causal hypothesis, expected effect, preservation obligations, regression risks, proposer model and harness, development-evidence references, required evaluations, budget request, and stop or rollback conditions. The frozen candidate snapshot contains every proposed base-to-head path change, including generated outputs, deletions, modes, and links, but it is not falsely described as the whole repository tree. The first implementation permits one parent, plus an explicit root or control sentinel; multi-parent recombination requires a later schema revision. Any content, base, parent, root, rung, or surface change creates a new candidate ID and freeze. Candidate evidence is explicitly labeled `author_supplied`, `development_observation`, or `independent_observation`; only observations issued through SPEC-017 under a sealed epoch are score-bearing.

`FailureSignature` contains verifier outcome, causal status, reusable mechanism, addressable surfaces, trace IDs, recurrence, and preservation set. Clustering uses mechanism and causal evidence, not error text alone.

The archive exposes `put_candidate`, `freeze`, evaluator-only `add_observation`, authority-checked `add_decision`, `lineage`, `similar`, `failure_clusters`, `pareto_frontier`, and `no_resuggest`. `put_candidate` resolves and locks the single legal root/control sentinel or a previously frozen parent, verifies production-root and base compatibility, and appends in topological journal order. Every query takes a context-profile and epoch boundary and returns a selection receipt. Overriding a no-resuggest decision requires a new child, new evidence, and an authorized reviewer receipt. Public export includes the complete public diff identity, hypothesis, allowlisted trace projections, public evaluation decisions, and decision rationale; private storage retains classified tool and development records subject to retention. Large trace bodies may expire only under a declared retention policy and immutable destruction receipt that preserves body digest, classification, reason, authority, and all surviving lineage. Public projections receive new identities and never expose private input digests, hidden membership, or private archive locators.

## State and failure behavior

Candidates move `draft -> frozen -> evaluating -> evaluated -> gate_review_pending -> proposal_eligible|rejected|parked|exploit|superseded`. Only the independent gate reducer may apply `proposal_eligible`. That state authorizes at most opening a draft proposal PR; it is not head attestation or merge readiness. Archive append failure blocks evaluation start. An incomplete trace limits the claims the evidence may support and cannot be cured by a summary. Corrupt artifacts quarantine the candidate and preserve prior valid records.

## Implementation sequence

1. Extend the SPEC-003 candidate core with observation, failure, trace, decision, search, and lineage archive schemas.
2. Import representative existing skill comparisons and research runs.
3. Add immutable freezing and evaluation binding.
4. Build archive retrieval, duplicate checks, and Pareto views.
5. Add public candidate reports and private trace retention policy.

## Migration and rollback

Historical imports are labeled and never treated as complete meta-harness trials unless required fields exist. Rollback keeps the archive read-only and returns candidate handling to current run artifacts.

## Observability

Track candidates by type and rung, lineage depth, duplicate rejection, failure clusters, archive retrieval use, trace completeness, exploit rate, time to decision, storage, and Pareto-front changes.

## Verification

- Candidate mutation after freeze changes the digest and is rejected.
- The same score cannot bind a revised child candidate.
- Rejected mechanisms appear in duplicate and no-resuggest queries.
- Hidden traces are unavailable to proposer contexts.
- Hidden identities, counts, diagnostics, and current-epoch exploit details are unavailable through similarity, failure-cluster, lineage, Pareto, and no-resuggest queries.
- Public export retains evidence while removing private tool payloads.
- Lineage and Pareto results rebuild deterministically.
- Orphan, forward, self, cyclic, and cross-production-root parents are rejected before append.
- Candidate-authored scores, gate waivers, evaluator selections, or proposal-eligibility claims are rejected.

## Acceptance criteria

- [ ] Every evaluated change has immutable identity and ancestry.
- [ ] Full development traces and summarized artifacts are not conflated.
- [ ] Rejected and exploit candidates remain queryable.
- [ ] Scores are immutable observations under epochs.
- [ ] Public/private archive boundaries pass fixtures.
- [ ] Failure clusters include causal and preservation information.
- [ ] Candidate-supplied, development, and independent evidence are mechanically distinct, and only sealed evaluator observations are score-bearing.
- [ ] Archive retrieval cannot contaminate a candidate search with hidden or current-epoch evaluator material.

## Pull-request evidence

Attach imported examples, freeze-tamper proof, candidate lineage view, failure-cluster fixture, public/private trace comparison, and deterministic Pareto report.
