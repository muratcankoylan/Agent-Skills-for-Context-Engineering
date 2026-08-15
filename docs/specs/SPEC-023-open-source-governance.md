# SPEC-023: Open-Source Governance and Project Growth

Status: draft
Revision: 1
Revises: none
Wave: 5
Classification: public
Owners: human maintainer; community steward agent
Depends on: SPEC-006, SPEC-007, SPEC-015, SPEC-019, SPEC-022

## Decision

The public repository will be managed as an evidence-centered open-source project under transparent governance. The founder remains final merge authority until a change accepted under the prior rules updates both the governance role and the SPEC-000 constitutional identity/authority binding, then reconciles the matching GitHub ruleset and bypass configuration. A contributor-ladder or maintainer-label change alone grants no merge authority. Agents may triage, review, reproduce, draft, label, and open PRs, but are identified as automated contributors and cannot become the sole human approval. Project growth is measured through useful contributions, replications, corrections, evaluation coverage, and adoption evidence, not stars or content volume.

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
8. Human feedback, rejection, correction, or preference applies only to its exact target by default. A broader effect requires an explicit SPEC-006 scope and confirmation; constitutional or gate changes require their normal human-merged amendment.
9. Agents cannot infer an organization-wide rule from conversation, one review, one rejected post, one closed PR, contributor reputation, or repeated engagement signals.
10. Automated intake, triage, review requests, comments, drafts, and PR creation obey per-lane rate, cost, and maintainer-load budgets and a human-operable pause.
11. A governance or constitution candidate is evaluated and authorized under the prior accepted rules. It cannot approve itself, redefine the evidence required for its own merge, or retroactively legitimize an action taken before acceptance.

## Interfaces and data

Add or reconcile `GOVERNANCE.md`, `MAINTAINERS.md`, `CODE_OF_CONDUCT.md`, `SECURITY.md`, `CODEOWNERS`, issue forms, PR templates, decision-record template, specification process, release/deprecation policy, dependency and license policy, and agent-contribution disclosure.

The initial intake has three lanes: `source_or_claim` for nominations, verification, contradictions, and stale-claim reports; `reproduction_or_eval` for result reproduction and evaluation fixtures; and `artifact_candidate` for skill, harness, code, example, guide, mechanism, adaptation, or specification candidates. Typed subcategories preserve the precise artifact contract without multiplying queues and reviewer policies. A new top-level lane requires measured evidence that the existing routing creates material latency, error, or maintainer burden, followed by a human-merged amendment.

Each lane defines minimum artifact, automated checks, reviewer role, expected outcomes, feedback scope, escalation, closure reason, resource ceiling, and overload behavior. A public project registry exposes current specs, open research questions, benchmark coverage gaps, review-needed items, releases, and beginner-suitable tasks. It never promises review capacity that has not been reserved.

If collaborative packet intake is activated after SPEC-022's closed trial, a native public GitHub form exposes only fields whose declared type is intrinsically safe to publish at receipt time. Client checks are advisory and organization validation occurs after GitHub publication, so that lane never claims prepublication rejection of arbitrary seeded private content. Raw archives, private contact, restricted evidence, credentials, hidden identifiers, or content represented as "private until validation" require a separately authenticated private submission service that validates into a private destination before it creates any bounded new-identity public projection. If that private preflight service is unavailable, the private lane is closed rather than falling back to a public form.

The contributor ladder is participant, contributor, reviewer, domain reviewer, and human maintainer. Advancement requires a public evidence record and human decision. Automated agents are service identities, not human maintainers. The ladder governs project roles and review routing only. Delegating merge authority additionally requires the human-merged SPEC-000 constitutional/identity amendment, current authority-policy update, and verified GitHub ruleset or bypass change under the prior merge authority; until all receipts reconcile, the new maintainer cannot merge for the organization.

## State and failure behavior

Specifications use the program's single canonical lifecycle exactly: `draft -> architecture_reviewed -> accepted -> implemented -> verified -> operational`, followed by a human-merged `amended|superseded|retired` terminal decision where applicable. Open pull requests, checks, blockers, releases, and observations are derived delivery projections rather than specification states. Any new lifecycle state requires a human-merged amendment to the canonical program plus an explicit migration for existing records. Contributions use lane-specific state but always retain a closure reason and immutable verbatim feedback reference. Abusive, spam, duplicate, or over-budget automated submissions can be rate-limited or paused without changing the evidence status of a legitimate source or creating an inferred global preference.

## Implementation sequence

1. Reconcile current contribution guidance with the new artifact and authority model.
2. Add governance, maintainer, decision, release, and correction documents.
3. Add issue and PR forms for the initial contribution lanes.
4. Generate public project status and research digest from canonical records.
5. Pilot collaborative adaptation and contributor-ladder reviews before broader promotion.
6. If the SPEC-022 closed trial justifies intake, separately review and activate the public-manifest/private-payload split with overload controls; otherwise keep the lane closed.

## Migration and rollback

Existing issues and PRs retain their original state and can be labeled into new lanes. The MIT license remains unless changed through a separate human decision. Rollback removes automation, not contribution rights or historical records.

## Observability

Measure time to first successful contribution, review latency, closure reasons, repeat contributors, independent replications, correction latency, effectiveness coverage, reproducible artifacts, maintainer load, agent-to-human submission ratio, and decisions changed by community evidence.

## Verification

- Every issue form produces a schema-valid intake artifact.
- An agent PR is visibly disclosed and cannot satisfy human review alone.
- A contributor-ladder promotion or governance-only edit cannot grant merge authority; the exact constitutional identity and GitHub-rule reconciliation receipts are both required.
- A first-time and high-reputation contributor face the same evidence gates.
- A correction updates affected indexes and creates a public record.
- Artifact-scoped rejection affects only that artifact; a proposed organization-scoped interpretation remains unapplied until explicit confirmation.
- Intake saturation pauses or queues automation without lowering evidence gates or fabricating review completion.
- Superseded specs remain linked and readable.
- Generated project status contains no private data.
- Native public forms omit raw-archive, private-contact, restricted-evidence, credential, and hidden-identifier fields by schema; seeded public misuse is quarantined and corrected after publication. Only the authenticated private submission service can reject private payloads before any public projection.

## Acceptance criteria

- [ ] Governance, maintainer, contribution, decision, release, and correction paths are public.
- [ ] Human and automated identities are distinguishable.
- [ ] Initial contribution lanes have templates and validators.
- [ ] Project-role delegation requires a merged governance change; merge-authority delegation additionally requires the prior-authority-approved SPEC-000 identity amendment and reconciled GitHub ruleset/bypass change.
- [ ] Growth metrics prioritize quality and contributor success.
- [ ] Public digests and calls to action resolve to canonical artifacts.
- [ ] Feedback preserves verbatim reason, interpretation, scope, confirmation, and first applicable version as separate records.
- [ ] Per-lane automation and maintainer-load budgets, overload behavior, and pause controls are public and tested.

## Pull-request evidence

Attach governance document map, rendered issue and PR forms, agent-disclosure example, correction drill, generated project status, and a complete first-time-contributor walkthrough.
