# SPEC-023: Open-Source Governance and Project Growth

Status: draft
Wave: 5
Classification: public
Owners: human maintainer; community steward agent
Depends on: SPEC-007, SPEC-015, SPEC-019, SPEC-022

## Decision

The public repository will be managed as an evidence-centered open-source project under transparent governance. The founder remains final merge authority until a human-merged governance amendment delegates it. Agents may triage, review, reproduce, draft, label, and open PRs, but are identified as automated contributors and cannot become the sole human approval. Project growth is measured through useful contributions, replications, corrections, evaluation coverage, and adoption evidence, not stars or content volume.

## Context and current repository touchpoints

The repository already has an MIT license and substantial `CONTRIBUTING.md`, documentation, examples, changelog, validation workflows, and plugin packaging. It needs governance, maintainer roles, decision and specification processes, structured contribution lanes, release/deprecation policy, and explicit treatment of agent-authored work.

## Goals

- Make it easy to nominate, verify, reproduce, implement, evaluate, and correct knowledge.
- Keep maintainer decisions legible and appealable through new evidence.
- Grow human contributors without weakening claim or promotion standards.
- Publish useful research digests, benchmark reports, and open questions from canonical artifacts.

## Non-goals

- Governance by popularity, token ownership, or agent vote.
- Treating contributor reputation as evidence quality.
- Promising immediate review of unlimited agent-generated PRs.

## Invariants

1. Human merge remains the release and specification-acceptance event.
2. All contributors use the same claim, mechanism, evaluation, and licensing gates.
3. Reputation may change routing and reviewer load, never evidence weight.
4. Material corrections are append-only and linked from affected artifacts.
5. Agent-authored or agent-reviewed artifacts disclose tool role and provenance.
6. Historical specifications and decisions remain accessible after supersession.
7. Public content derives from canonical evidence and receives normal review.

## Interfaces and data

Add or reconcile `GOVERNANCE.md`, `MAINTAINERS.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CODEOWNERS`, issue forms, PR templates, decision-record template, specification process, release/deprecation policy, dependency and license policy, and agent-contribution disclosure.

Contribution lanes are source nomination, claim verification or contradiction, result reproduction, mechanism proposal, activation/adversarial/effectiveness/composition fixture, example or guide, skill or harness candidate, collaborative adaptation packet, spec review, and stale-claim or regression report.

Each lane defines minimum artifact, automated checks, reviewer role, expected outcomes, escalation, and closure reason. A public project registry exposes current specs, open research questions, benchmark coverage gaps, review-needed items, releases, and beginner-suitable tasks.

The contributor ladder is participant, contributor, reviewer, domain reviewer, and human maintainer. Advancement requires a public evidence record and human decision. Automated agents are service identities, not human maintainers.

## State and failure behavior

Specifications use the program's single canonical lifecycle exactly: `draft -> architecture_reviewed -> accepted -> implementing -> implemented -> verified -> operational -> amended|superseded|retired`. An idea is intake metadata, public review is review metadata, and release or observation is a derived project projection rather than a second specification state. Any new lifecycle state requires a human-merged amendment to the canonical program plus an explicit migration for existing records. Contributions use lane-specific state but always retain a closure reason. Abusive, spam, or duplicate automated submissions can be rate-limited without changing the evidence status of a legitimate source.

## Implementation sequence

1. Reconcile current contribution guidance with the new artifact and authority model.
2. Add governance, maintainer, decision, release, and correction documents.
3. Add issue and PR forms for the initial contribution lanes.
4. Generate public project status and research digest from canonical records.
5. Pilot collaborative adaptation and contributor-ladder reviews before broader promotion.

## Migration and rollback

Existing issues and PRs retain their original state and can be labeled into new lanes. The MIT license remains unless changed through a separate human decision. Rollback removes automation, not contribution rights or historical records.

## Observability

Measure time to first successful contribution, review latency, closure reasons, repeat contributors, independent replications, correction latency, effectiveness coverage, reproducible artifacts, maintainer load, agent-to-human submission ratio, and decisions changed by community evidence.

## Verification

- Every issue form produces a schema-valid intake artifact.
- An agent PR is visibly disclosed and cannot satisfy human review alone.
- A first-time and high-reputation contributor face the same evidence gates.
- A correction updates affected indexes and creates a public record.
- Superseded specs remain linked and readable.
- Generated project status contains no private data.

## Acceptance criteria

- [ ] Governance, maintainer, contribution, decision, release, and correction paths are public.
- [ ] Human and automated identities are distinguishable.
- [ ] Initial contribution lanes have templates and validators.
- [ ] Maintainer delegation requires a merged governance change.
- [ ] Growth metrics prioritize quality and contributor success.
- [ ] Public digests and calls to action resolve to canonical artifacts.

## Pull-request evidence

Attach governance document map, rendered issue and PR forms, agent-disclosure example, correction drill, generated project status, and a complete first-time-contributor walkthrough.
