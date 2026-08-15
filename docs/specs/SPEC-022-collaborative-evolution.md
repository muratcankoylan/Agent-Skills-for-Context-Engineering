# SPEC-022: Collaborative Evolution and Community Contribution Packets

Status: draft
Revision: 1
Revises: none
Wave: 4
Classification: split
Owners: community research steward agent; independent evaluator agent; human maintainer
Depends on: SPEC-002, SPEC-005, SPEC-006, SPEC-014, SPEC-016, SPEC-018, SPEC-019, SPEC-021

## Decision

Revision 1 defines a closed packet and reproduction contract, not a public intake service. External instances and contributors may construct bounded, scope-typed adaptation packets relative to a common base and run the public validator locally. Organization-side trials use a fixed repository-authored packet set in private quarantine. The organization may decompose an admissible diff into candidate mechanisms, reproduce declared behavior fixes and breakages in an isolated environment, and evaluate the composed result locally. A contributor's local gate is an untrusted eligibility claim; it never supplies a global rank, score-bearing observation, hidden-evaluation input, authority, or bypass around repository evaluation and human merge. SPEC-023 later owns any public intake activation and its disclosure boundary.

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
8. Contributor code, archives, scripts, links, prompts, and results are never executed during parsing or validation and receive no network, credential, hidden-evaluation, or repository-write capability during reproduction.
9. Packet size, file count, decompressed bytes, reproduction attempts, model calls, money, and maintainer-review load are bounded and reserved before work begins.
10. Maintainer feedback applies to the exact packet or artifact by default. Broader workflow, source-family, skill, organization, or private-preference effects require an explicit SPEC-006 scope and confirmation; a rejection never silently changes global policy.
11. Contributor identity, reputation, popularity, and self-reported local score affect neither evidence weight nor gate thresholds.
12. Mechanism decomposition is a candidate hypothesis, not evidence that the mechanism caused an effect. Repository reproduction and, when causal attribution matters, an ablation are required before promotion use.

## Interfaces and data

`ContributionPacket` includes common-base commit, adaptation diff and digest, changed surfaces, target rung, declared home scope, compatible models and executors, sanitized behavior fixes, sanitized behavior breakages, local evaluation manifest and raw-result availability, data statement, source and mechanism links, privacy and redaction attestation, license, optional private contact reference, resource manifest, and declarative reproduction instructions. It cannot contain a capability grant, live credential reference, hidden-epoch identifier, claimed organization decision, or executable install hook. Raw packet and contact records remain private. Revision 1 exposes no GitHub issue, PR, upload, email, or network intake endpoint.

Intake performs byte-safe schema and archive-bound validation, license and classification checks, base resolution, complete diff inspection, restricted-surface check, mechanism decomposition, duplication search, local-evidence verification, sandbox reproduction, scoped evaluation, and independent decision. Local raw results remain contributor claims until organization reproduction. Community responses and maintainer feedback become graph and scoped feedback artifacts only through their owning reducers.

## State and failure behavior

Packets move `submitted -> quarantined_intake -> resource_checked -> admissible -> budget_reserved -> decomposed -> reproducing -> evaluated -> candidate_eligible|reproduction_complete|needs_information|scope_limited|rejected|quarantined`. `candidate_eligible` means only that the reproduced material may enter the normal candidate and evaluation path; `reproduction_complete` retains useful evidence without asserting candidate eligibility. Neither state is acceptance, promotion, or score-bearing authority. Unsupported base or missing artifacts yields `needs_information`. Restricted-surface, classification, archive-bound, license, or integrity issues quarantine before execution. A failed reproduction records its environment and may still produce a useful failure mechanism, but cannot become score-bearing without the normal evaluation path.

## Implementation sequence

1. Publish packet schema, examples, contributor guide, and local validator.
2. Validate repository-authored packets in observation mode with no public intake endpoint.
3. Add deterministic sandbox reproduction, mechanism hypotheses, and causal ablation where claimed.
4. Evaluate a small fixed packet set and measure review effort, cost, failure rate, and transfer value.

If the closed trial meets preregistered value, workload, and safety thresholds, SPEC-023 may later propose a public manifest-only lane plus a separate authenticated private channel. That activation is not part of this specification's lifecycle or acceptance.

## Migration and rollback

Existing external PRs remain normal public contributions. They may include only an explicitly public `PublicContributionManifest` whose bounded fields are safe at publication time and which contains no private contact, restricted body, raw archive, private identity, or private digest. Raw `ContributionPacket` records remain solely in the fixed private trial or a later SPEC-023 authenticated private lane. Closing that lane disables new automated intake but keeps ordinary GitHub contribution paths and archived packets.

## Observability

Track submissions, schema failures, time to response, reproduction rate, duplicate mechanisms, home-to-target transfer, accepted scope, evaluation cost, maintainer workload, licensing blocks, and later regressions.

## Verification

- A packet against the wrong base is rejected before evaluation.
- A local score without behavior cases cannot advance.
- A useful mechanism can be extracted from a whole-diff packet while unrelated changes are rejected.
- A home-scope improvement that fails transfer is classified scope-limited.
- A novel failure is absent from the currently active hidden epoch.
- Accepted packets still require a normal PR and human merge.
- Seeded executable hooks, archive bombs, traversal paths, secret references, hidden IDs, and restricted-surface changes are quarantined before execution.
- Rejecting one packet with a detailed reason does not alter other packets or organization policy without a confirmed broader feedback scope.
- Concurrent intake cannot exceed resource, evaluation, or maintainer-load reservations.

## Acceptance criteria

- [ ] Schema and local validation tools are public and deterministic.
- [ ] Base, diff, scope, behavior cases, data statement, and license are required.
- [ ] Local and organization evaluations remain distinct.
- [ ] Mechanism decomposition and duplicate search precede adoption.
- [ ] Fixture-ingestion boundaries prevent active-epoch contamination.
- [ ] Human merge remains the final authority.
- [ ] Revision 1 exposes no public intake endpoint; a later lane is owned and authorized by SPEC-023.
- [ ] Raw intake and private contact data are separated from new-identity public projections.
- [ ] Intake is bounded, non-executing, isolated on reproduction, and incapable of accessing credentials or hidden evaluation.
- [ ] Feedback scope follows SPEC-006 and defaults to the exact packet or artifact.

## Pull-request evidence

Attach valid, incomplete, wrong-base, scope-limited, and restricted-surface packet fixtures; one decomposition trace; one reproduction report; public local-validator documentation; and proof that no intake endpoint is active.
