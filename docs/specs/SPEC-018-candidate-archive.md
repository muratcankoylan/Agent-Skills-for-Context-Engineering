# SPEC-018: Candidate Archive, Failure Memory, and Lineage

Status: draft
Wave: 3
Classification: split
Owners: meta-harness archivist agent; evaluation steward agent
Depends on: SPEC-003, SPEC-017

## Decision

Every evaluated change will be an immutable candidate in an append-only lineage graph. The archive retains development code, full development traces, failures, costs, results, reviewer decisions, and rejected or exploit candidates. Hidden evaluation traces remain in a separate evaluator archive. Candidates never acquire a mutable score; evaluations are observations under named epochs.

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

## Interfaces and data

`Candidate` includes type, parents, production root, target editable-surface rung, changed files or controls, failure clusters, causal hypothesis, expected effect, preservation obligations, regression risks, proposer model and harness, artifact digest, required evaluations, budget, and stop or rollback conditions.

`FailureSignature` contains verifier outcome, causal status, reusable mechanism, addressable surfaces, trace IDs, recurrence, and preservation set. Clustering uses mechanism and causal evidence, not error text alone.

The archive exposes `put_candidate`, `freeze`, `add_observation`, `add_decision`, `lineage`, `similar`, `failure_clusters`, `pareto_frontier`, and `no_resuggest`. Public export includes diff, hypothesis, safe traces, results, and decision rationale; private storage retains complete tool and development records subject to retention.

## State and failure behavior

Candidates move `draft -> frozen -> evaluating -> evaluated -> pr_eligible|rejected|parked|exploit|superseded`. Archive append failure blocks evaluation start. An incomplete trace marks evidence quality but does not fabricate missing steps. Corrupt artifacts quarantine the candidate and preserve prior valid records.

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
- Public export retains evidence while removing private tool payloads.
- Lineage and Pareto results rebuild deterministically.

## Acceptance criteria

- [ ] Every evaluated change has immutable identity and ancestry.
- [ ] Full development traces and summarized artifacts are not conflated.
- [ ] Rejected and exploit candidates remain queryable.
- [ ] Scores are immutable observations under epochs.
- [ ] Public/private archive boundaries pass fixtures.
- [ ] Failure clusters include causal and preservation information.

## Pull-request evidence

Attach imported examples, freeze-tamper proof, candidate lineage view, failure-cluster fixture, public/private trace comparison, and deterministic Pareto report.
