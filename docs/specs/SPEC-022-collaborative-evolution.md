# SPEC-022: Collaborative Evolution and Community Contribution Packets

Status: draft
Wave: 4
Classification: public
Owners: community research steward agent; independent evaluator agent; human maintainer
Depends on: SPEC-014, SPEC-021

## Decision

External instances and contributors may submit scope-typed adaptation packets relative to a common base. The organization decomposes each diff into candidate mechanisms, validates declared behavior fixes and breakages, and evaluates the composed result locally. A contributor's local gate makes a packet eligible for consideration but never supplies a global rank or bypasses repository evaluation and human merge.

## Context and current repository touchpoints

The public repository already accepts skills and examples through normal GitHub contribution. This specification tests an engineering hypothesis: scope-typed local adaptation packets can transfer useful mechanisms without transferring all local data when base revision, behavior, evidence, limitations, and regressions are explicit. Local acceptance is never treated as evidence of global transfer; repository-side evaluation decides whether the contribution generalizes.

## Goals

- Let developers share validated local harness, context, prompt, and skill adaptations.
- Extract reusable mechanisms rather than blindly merging whole forks.
- Record local-data limitations, transfer scope, licensing, and known regressions.
- Grow public evaluation coverage from real failures after quarantine and review.

## Non-goals

- Federated weight training or private-gradient exchange.
- Trusting self-reported scores without artifacts.
- Automatically executing or merging contributor code.

## Invariants

1. Every packet names the exact common-base commit and diff digest.
2. Declared home scope, available data, evaluation manifest, privacy and redaction attestation, and license are mandatory.
3. Behavior fixes and breakages are concrete sanitized cases, not only a score.
4. Contributions are decomposed and evaluated as normal candidates.
5. Local evidence informs eligibility and scope, not global ranking.
6. Novel failures enter development fixtures only after review and never contaminate an active hidden epoch.
7. Acceptance still requires agent or human PR review and human merge.

## Interfaces and data

`ContributionPacket` includes common-base commit, adaptation diff and digest, changed surfaces, target rung, declared home scope, compatible models and executors, sanitized behavior fixes, sanitized behavior breakages, local evaluation manifest and raw-result availability, data statement, source and mechanism links, privacy and redaction attestation, license, maintainer contact, and reproduction instructions.

Intake performs schema and license validation, base resolution, diff inspection, restricted-surface check, mechanism decomposition, duplication search, local-evidence verification, sandbox reproduction, scoped evaluation, and decision. Community responses and maintainer feedback become graph and feedback artifacts.

## State and failure behavior

Packets move `submitted -> admissible -> decomposed -> reproducing -> evaluated -> accepted_candidate|needs_information|scope_limited|rejected|quarantined`. Unsupported base or missing artifacts yields `needs_information`. Restricted-surface or integrity issues quarantine. A failed reproduction records its environment and may still produce a useful failure mechanism.

## Implementation sequence

1. Publish packet schema, examples, contributor guide, and local validator.
2. Build intake as an issue or PR workflow in observation mode.
3. Add deterministic sandbox reproduction and mechanism decomposition.
4. Evaluate a small set of repository-authored example packets.
5. Open the lane publicly only after review workload and cost are measured and SPEC-023 contribution, disclosure, moderation, and maintainer rules are active.

## Migration and rollback

Existing external PRs remain normal contributions and can opt into the packet format. Closing the lane disables new automated intake but keeps GitHub contribution paths and archived packets.

## Observability

Track submissions, schema failures, time to response, reproduction rate, duplicate mechanisms, home-to-target transfer, accepted scope, evaluation cost, maintainer workload, licensing blocks, and later regressions.

## Verification

- A packet against the wrong base is rejected before evaluation.
- A local score without behavior cases cannot advance.
- A useful mechanism can be extracted from a whole-diff packet while unrelated changes are rejected.
- A home-scope improvement that fails transfer is classified scope-limited.
- A novel failure is absent from the currently active hidden epoch.
- Accepted packets still require a normal PR and human merge.

## Acceptance criteria

- [ ] Schema and local validation tools are public and deterministic.
- [ ] Base, diff, scope, behavior cases, data statement, and license are required.
- [ ] Local and organization evaluations remain distinct.
- [ ] Mechanism decomposition and duplicate search precede adoption.
- [ ] Fixture-ingestion boundaries prevent active-epoch contamination.
- [ ] Human merge remains the final authority.
- [ ] External intake remains feature-gated until SPEC-023 governance is active.

## Pull-request evidence

Attach valid, incomplete, wrong-base, scope-limited, and restricted-surface packet fixtures; one decomposition trace; one reproduction report; and public contributor documentation.
