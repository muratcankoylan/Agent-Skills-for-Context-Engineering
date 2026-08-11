# SPEC-019: Pull-Request Quality Gate, Promotion, and Release

Status: draft
Wave: 3
Classification: public
Owners: release attestor agent; human maintainer
Depends on: SPEC-007, SPEC-018

## Decision

A candidate becomes PR-eligible only after sequential hard gates and a Pareto review. Evaluation observations bind immutable candidate content. An independent release attestor then proves that the current PR tree and head SHA exactly materialize that candidate and that current checks satisfy its gates. An agent may open and maintain the PR. Only human merge promotes it. A post-merge promotion record describes what was accepted; private deployment status is tracked separately.

## Context and current repository touchpoints

Current CI already requires platform compatibility, strict repository validation, strict skill health, benchmarks, and activation cases. Plugin manifests share a prepared version. This spec preserves those checks, adds candidate/evaluation binding, expands surface-specific gates, and makes release state event-driven.

## Goals

- Prevent stale or unrelated results from approving a changed PR.
- Apply distinct gates to sources, mechanisms, skills, harnesses, and organization changes.
- Make production identity and rollback unambiguous.
- Keep the human review packet concise while retaining full evidence.

## Non-goals

- Auto-merge, agent release publication, or bypassing required reviews.
- One global weighted score.
- Requiring the same expensive evaluation for a typo and a harness change.

## Invariants

1. Admissibility, locked-surface, schema, repository, and provenance gates are hard vetoes.
2. The targeted failure improves by a preregistered practical amount and hidden behavior meets its non-inferiority bound.
3. At least one important dimension improves; no critical dimension regresses.
4. Negative controls remain stable and uncertainty is reported.
5. Cost, latency, context, and complexity remain within caps or form an explicitly accepted Pareto trade.
6. New skills require a distinct activation surface and maintenance justification.
7. Any new commit invalidates attestation until relevant checks rerun.
8. Promotion occurs only on human merge.
9. Evaluation observations, pre-merge attestation, and post-merge promotion are distinct immutable records.
10. Accepted public commit and active deployment commit are never collapsed into one field.

## Interfaces and data

`EvaluationObservation` is defined by SPEC-017 and binds the candidate content digest and epoch without assuming a PR.

`PromotionAttestation` is a public record created before merge. It includes candidate and parent IDs, candidate tree digest, exact PR and head SHA, deterministic proof that the PR tree equals the frozen candidate plus declared generated metadata, required-check conclusions and issuers, new-identity public evaluation-decision and gate-projection IDs, practical-effect and non-inferiority decisions, critical-dimension status, provenance completeness, compatibility classification, cost and complexity deltas, attestor identity, creation and expiry, and policy version. A separate private `AttestationEvidenceSeal` binds the raw evaluation observations, hidden epoch and tasks, and their digests. The public attestation contains no private observation identity or digest and no merged commit.

`PromotionRecord` is created only after a reconciled human merge. It includes the public attestation ID and digest, PR and attested head SHA, merge event and merged commit, accepted public commit, organization version, schema and artifact inventory, compatibility scope, human merger, and rollback parent. It exposes no private observation identity, private seal identity, or private digest, and it does not claim that a private deployment is already active.

Because a record containing a merge SHA cannot be inside the commit it describes, the immediate canonical record is appended to the operational journal and linked as an immutable-digest status or comment on the merged PR. A deterministic public promotion-ledger snapshot can be included in a later agent-opened maintenance PR. That later snapshot does not cause or retroactively authorize the original promotion.

`DeploymentActivation` is a private operational record containing deployment identity, accepted public commit, active deployment commit and configuration digest, activation scope and time, health, and rollback state. It can lag public acceptance. Changing the accepted configuration still requires a human-merged PR.

Gate policy maps change surfaces to required stages. Skill prose requires Stages 0-3 plus routing delta when activation changes. Composition-sensitive changes require Stage 4. Context, workflow, recovery, or harness changes require Stage 5. Optimizer changes require Stage 6. A community question follows its own relevance, uncertainty, answerability, and human-publication gates.

## State and failure behavior

Attestation moves `requested -> candidate_tree_verified -> inputs_verified -> gates_evaluated -> attested|denied|expired`. PR state follows SPEC-007. A mismatch in candidate digest, tree, head SHA, epoch, or required checks denies attestation. A new head SHA expires it. After merge, public release projection moves `merged -> promotion_recorded -> accepted`, while private deployment moves independently through `pending -> canary|active -> degraded|rollback_pending|superseded`.

## Implementation sequence

1. Generate change-impact manifests and map surfaces to gates.
2. Bind raw evaluation observations to candidate content in a private evidence seal, derive public evaluation-decision projections, and prove candidate-tree equivalence for a PR head.
3. Implement independent exact-SHA attestation and current-check verification.
4. Generate a separate promotion record after an observed human merge.
5. Add accepted-public versus active-deployment projections, version and compatibility updates, and rollback runbook.

## Migration and rollback

The current default branch becomes accepted public epoch zero with an imported promotion record, while the local deployment separately records its active commit. Existing releases receive best-effort historical records. Operational rollback is a human-merged revert or corrective PR when the accepted configuration changes, plus a new deployment activation record, never history rewriting.

## Observability

Show gate outcomes, attestation expiry, stale evidence, time in checks and human review, regression causes, promotion latency, accepted public commit, active deployment commit, version skew, rollback frequency, and deployment health across installations.

## Verification

- A commit after successful attestation invalidates attestation; unchanged evaluation observations remain attached only to their frozen candidate digest.
- A candidate with aggregate gain but critical provenance regression is denied.
- A new skill without distinct activation evidence is denied.
- The proposer cannot act as sole attestor.
- Human merge produces one promotion record bound to the attested head and merge commit.
- Public promotion-ledger export avoids circular commit hashing and reproduces the immediate post-merge record.
- A PR SHA cannot appear in an evaluation observation, and a merged commit cannot appear in a pre-merge attestation.
- Accepted public and active deployment commits may differ without losing status clarity.
- A rollback drill restores the prior compatible production state through a PR.

## Acceptance criteria

- [ ] Every PR-eligible candidate has exact-SHA evidence and independent attestation.
- [ ] Required gates depend on changed surfaces and are machine-checkable.
- [ ] Existing strict validators remain required.
- [ ] Human merge is the only promotion trigger.
- [ ] Accepted public version, active deployment version, and rollback pointer are independently queryable.
- [ ] Release and plugin manifest consistency is validated.

## Pull-request evidence

Attach gate matrix, change-impact examples, candidate-to-tree proof, stale-SHA denial, critical-regression denial, separate sandbox observation, attestation, promotion, and deployment records, version-consistency result, and rollback drill.
