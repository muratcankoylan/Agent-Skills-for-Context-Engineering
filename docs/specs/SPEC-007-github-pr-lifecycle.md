# SPEC-007: GitHub App and Pull-Request Lifecycle

Status: draft
Revision: 1
Revises: none
Wave: 1
Classification: split
Owners: release steward agent; human maintainer
Depends on: SPEC-000, SPEC-002, SPEC-003, SPEC-004, SPEC-005, SPEC-006

## Decision

GitHub is the public proposal and human-merge ledger. An automated proposer may create candidate branches, push commits, open draft pull requests, request review, apply allowlisted labels, and add immutable evidence comments. It never edits a PR body after creation or creates trusted check runs. It may not update the default branch, merge, approve or dismiss review, administer rulesets, publish a release, or create credentials.

Permission minimization alone cannot enforce that boundary. The proposer needs GitHub `Contents: write` to create and push branches, and that permission is also accepted by the merge endpoint. Human-only merge therefore requires an enforced default-branch ruleset that excludes the App from update and bypass authority, the SPEC-000 denial, continuous configuration reconciliation, and a live sandbox proof that the App receives a denial when it attempts merge. Human review readiness and human merge remain separate facts.

## Context and current repository touchpoints

The repository already has CI, release manifests, and PR conventions, but the research loop stops at PR-ready artifacts. The organization must observe checks, reviews, comments, requested changes, closures, synchronizations, and merges; preserve human edits; and recover from missed or reordered delivery. A webhook is a trigger to reconcile, never final truth.

## Goals

- Let agents prepare and maintain high-quality, evidence-complete proposal PRs.
- Bind every check, review, command, and organizational approval to an exact head SHA.
- Converge after missed, duplicated, edited, or reordered webhook delivery.
- Enforce human-only default-branch update through both organizational policy and GitHub configuration.
- Reflect unknown external merges truthfully while quarantining their downstream effects for reconciliation.

## Non-goals

- Agent merge, auto-merge, approval, review dismissal, or ruleset administration.
- Treating a personal access token as a production identity.
- Deciding evaluation validity, promotion eligibility, or release attestation; SPEC-019 owns those decisions.
- Treating a PR comment, webhook body, or cached projection as trusted current GitHub state.
- Continuous credentialed operation before SPEC-024 and SPEC-025.

## Invariants

1. The accepted public commit advances only one contiguous default-branch transition at a time from its exact current pointer. An authoritative GitHub read must prove that transition is a merge into the default branch, its base or first parent equals the current accepted commit, and its actor is a verified human in the accepted authority set. Other updates advance only the observed head and enter incident reconciliation.
2. Review and check conclusions bind a named check or reviewer, exact head SHA, and observation receipt. A new head invalidates prior readiness.
3. Webhooks are signature-verified, deduplicated, stored by reference, and followed by authoritative GitHub reads.
4. The proposer App is absent from every default-branch update or bypass allowlist. Configuration drift disables automated writes and creates an incident work order.
5. The organizational grant and write adapter deny merge even though the App token's `Contents: write` permission could reach the merge endpoint; the default-branch ruleset provides the independent remote denial.
6. Every automated PR identifies the automated proposer, supervising human, candidate ID, work order, base commit, head SHA, and evidence-manifest digest.
7. Human-authored regions of the PR body and human commits are never overwritten or force-pushed.
8. A previously unknown PR merge advances the accepted public commit only when an authoritative read proves both the verified-human authority and the complete contiguous transition from the current accepted pointer. The organization then quarantines promotion and deployment work until candidate, checks, and provenance are reconciled. An unknown or unauthorized actor, direct update, ancestry rewrite, skipped intermediate commit, or later human merge based on an unresolved divergent head advances only the observed head.
9. Active deployment is a separate projection and cannot precede acceptance of the merged commit.

## Interfaces and data

### Pure reconciliation contracts

`GitHubDelivery` retains delivery ID, repository and installation IDs, event and action, claimed actor, received time, signature result, body digest, and private body reference. A valid delivery creates a SPEC-006 ingress receipt when it contains a supported command, but does not directly create a command intent or PR transition.

`GitHubObservationReceipt` is an immutable result of a read adapter. It binds repository ID, requested resources, API version, adapter version, observation time, provider ETag or resource revision where exposed, response digests, rate-limit state, and normalized snapshot. The snapshot covers default-branch head, PR base and head, commits, changed-file manifest, checks, reviews, comments, labels, mergeability, closure, merge actor, merge commit, and repository rules relevant to this specification. Every field declares its source resource and revision. Terminal facts use an explicit monotonic lattice; incomparable or apparently regressive partial observations schedule a full reread and quarantine rather than replacing a newer field.

```text
GitHubNormalizer.verify(delivery_bytes, headers, adapter_config)
  -> GitHubDelivery | IngressRejection
GitHubReader.observe(reconciliation_request, trusted_principal, runtime_grant)
  -> GitHubObservationReceipt
PRProjector.reduce(observation_receipts, source_sequence) -> PRProjectionReceipt
PRReconciler.plan(pr_projection, trigger) -> ReconciliationPlan
RepositoryAcceptanceReconciler.apply(request, policy_decision, runtime_grant)
  -> RepositoryAcceptanceEvent + AcceptedPublicCommitReceipt | AcceptanceConflict
```

The projector consumes only journaled observation receipts and local proposal receipts. It never performs a network read. A webhook, periodic poll, command, ambiguous write, or configuration check may schedule a read work order through SPEC-005.

`RepositoryAcceptanceRequest` is the only autonomous input that may advance `accepted_public_commit`. It binds the expected pointer and pointer version; repository, default branch, ruleset and accepted-human-authority-set digests; a complete first-parent/default-branch interval beginning at the expected pointer; immutable GitHub observation IDs, provider revisions and response digests for every interval element; exact PR, base, head, merge commit and tree; verified merge actor; current accepted commit and policy context; and stable operation key and request digest. The dedicated repository reconciler, not the proposer App, acts under the narrow `reconcile_repository_acceptance/repository_acceptance` entry. Its maximum effect is one SPEC-007-owned `RepositoryAcceptanceEvent` and one matching accepted-pointer transition. It cannot push, merge, submit review, attest, promote, deploy, create an evidence-graph acceptance mapping, or accept a gap. SPEC-011 may later consume this event and emit zero or more projection-specific `AcceptanceMapping` records under its own contract; a repository merge does not imply that any such mapping exists.

The reducer advances exactly the next contiguous verified-human merge. If observations arrive in a batch, it evaluates and records each authorized transition separately in first-parent order. A direct push, force or ancestry rewrite, skipped or unattributed intermediate, base mismatch, stale expected pointer, ruleset or authority-set drift, reordered provider revision, or human merge whose base already contains an unresolved divergent commit leaves the accepted pointer unchanged and opens an incident. Resolving such a divergence requires a future exact human-authorized full-tree acceptance contract; ordinary reconciliation never imports the divergence merely because a later merge actor is authorized. Exact request replay returns the first receipt, while the same operation key or observation identity with different bytes collides before mutation.

This specification registers three SPEC-006 command families with parser digests and byte fixtures:

```text
/org pr-status <number>
/org approve-pr <number> --head-sha <full-lowercase-sha> --expected-version <unsigned-integer> --accepted-commit <full-lowercase-sha> --reason <bounded-text-to-end-of-line>
/org reject-pr <number> --head-sha <full-lowercase-sha> --expected-version <unsigned-integer> --accepted-commit <full-lowercase-sha> --reason <bounded-text-to-end-of-line>
```

The grammar permits one ASCII command per delivery, canonical single spaces and flag order, a positive decimal PR number without leading zeroes, repository-configured 40- or 64-hex lowercase full SHAs, and one UTF-8 length-bounded reason consuming the remainder. Missing, reordered, repeated, uppercase, abbreviated, or unknown tokens fail; parser goldens cover every boundary and canonical intent serialization. `pr-status` maps to `query_status/status_projection`. Both decision commands bind the exact current head SHA, expected PR projection version, accepted public commit, operation identity, and `record_pr_decision/pull_request`. Their reducer records organizational readiness or rejection only; neither family can submit a GitHub review, invoke merge, alter rules, or change the default branch. They remain unavailable until the human-merged SPEC-000 revision 2 authority-vocabulary entry is current.

### Lifecycle

The base transport lifecycle is:

```text
candidate_ready -> branch_planned -> branch_pushed -> draft_pr_open
-> checks_pending -> reviewable
-> changes_requested | approved_waiting_human_merge
-> synchronized -> checks_pending
-> merged | closed_unmerged | superseded | reconciliation_required
```

`approved_waiting_human_merge` requires the current head, required checks, organizational command state, and human review state to agree. It is not promotion eligibility and does not authorize a merge. SPEC-019 later attaches a separate head-bound release attestation and required check; SPEC-007 neither fabricates nor evaluates that attestation.

The App writes the initial PR body exactly once at PR creation. After creation it never patches the body, because GitHub does not provide a body compare-and-swap that can close the read/write race with a human edit. New proposer evidence is added through immutable digest-bound comments; a superseding machine summary is a new comment that references the prior comment. Trusted check results, when SPEC-019 is active, come only from its separate release-attestor identity. Human body edits therefore remain byte-for-byte outside the automated write surface. Unexpected commits, base changes, deleted markers, or conflicting evidence enters `reconciliation_required`; the App never force-pushes around it.

### App and branch boundary

The proposer App requests only the repository permissions required for the enabled slice: metadata read, checks read, pull-requests write, contents write, and administration read solely to inspect effective branch protection and rulesets. Optional issue/comment or workflow permissions are separate, denied by default, and require evidence before activation. The App receives no administration write, ruleset mutation, secret, environment, member, release, or deployment authority.

The default-branch ruleset must require pull requests, required checks and human review, block deletion and force push, restrict updates to the named human maintainer or human team, and give the App no bypass path. Startup and periodic reconciliation bind the exact ruleset IDs, normalized rules, effective actor set, default branch, repository ID, and configuration digest. A missing or weaker rule fails closed for all App writes.

Branch creation, push, PR creation, labels, review requests, and comments use stable operation keys. The proposer has no check-write or post-creation PR-body operation. An ambiguous response schedules a read and searches by candidate marker, branch, head, and operation marker before retry. No write retry occurs while the remote outcome is unknown.

## State and failure behavior

Duplicate and reversed deliveries converge by provider revision plus the field-specific monotonic lattice, not delivery or local observation order. A new reviewable commit returns the PR to `checks_pending`; prior check and review facts remain in history but no longer satisfy current-head readiness. A stale command becomes a SPEC-006 conflict. Incomparable partial reads cannot regress merge, close, head, check, or review state and remain unresolved until a complete authoritative read arrives.

A GitHub-confirmed unknown PR merge by a verified authorized human advances `accepted_public_commit` only through the exact contiguous acceptance reducer above, then enters reconciliation quarantine until inventory, candidate provenance, checks, and attestation are classified. If the App, an unknown actor, or an unauthorized human performed the merge, or if any intermediate/default-branch ancestry fact is unresolved, `observed_default_branch_head` advances but `accepted_public_commit` does not; the organization records a constitutional incident, suspends the relevant credential when applicable, and blocks promotion and deployment. A direct, unattributed, rewritten, or gap-containing default-branch update follows the same observed-but-not-accepted path.

Revocation, rate limiting, GitHub outage, stale observation, ambiguous write, ruleset drift, and body divergence remain visible states. None is converted to success or absence.

## Implementation sequence

### SPEC-007A: credential-free lifecycle and reconciler

1. Register delivery, observation, proposal receipt, lifecycle, configuration-snapshot, repository-acceptance request/event, and accepted-pointer receipt contracts.
2. Implement signature, duplicate, edited-delivery, and normalization fixtures without live credentials.
3. Replay reordered webhook triggers plus authoritative read fixtures through the pure projector and contiguous acceptance reducer, including divergence and ancestry-rewrite fixtures.
4. Generate one initial PR body in a temporary repository, then prove all later proposer evidence uses comments and a human body edit is never patched or force-pushed.

### SPEC-007B: sandbox proposer App

1. Configure a sandbox App and branch ruleset from a reviewed permission manifest.
2. Reconcile the live effective ruleset and run a sandbox merge-denial test before enabling proposal writes.
3. Create one proposal branch and draft PR, reconcile ambiguous API fixtures, and process supported GitHub commands through SPEC-006.
4. Add periodic read reconciliation and the narrow `reconcile_repository_acceptance/repository_acceptance` compare-and-append path. Keep continuous credential use disabled until SPEC-024 and supervised operation disabled until SPEC-025.

## Migration and rollback

Adopt the exact SPEC-004 `RepositoryAcceptanceBaseline` as the current pointer and version; do not import or infer a second epoch-zero record. Import open organization PRs through observation receipts and the reconciler, not fabricated webhooks. Historical reviews retain their original heads. Rollback disables dispatch, revokes or suspends the App installation, reconciles in-flight writes, and leaves open branches and PRs available for human handling. Accepted public and active deployment commits do not move during rollback unless a real contiguous authorized-human merge is reconciled.

## Observability

Expose delivery verification failures, reconciliation lag and drift, read and write rate limits, ambiguous operations, ruleset digest and drift, PRs by lifecycle state, current-head checks and reviews, stale approvals, human-edit divergence, time awaiting human action, observed default head, accepted public commit, and incident quarantine. SPEC-008 may later join that accepted pointer with SPEC-025 deployment state; this specification does not own or expose an active-deployment pointer. Raw webhook bodies, installation IDs, and private human data are not public metrics.

## Verification

- Invalid signatures and delivery-ID/body collisions fail before parsing.
- Duplicate, reversed, partial, and stale observations converge without regressing a field; incomparable revisions trigger reread or quarantine.
- Ambiguous branch, push, and PR creation find an existing remote effect before any retry.
- A push after approval invalidates current-head readiness and reruns required checks.
- A human edit inserted after PR creation remains byte-for-byte unchanged because the App has no post-creation body-write path.
- Ruleset removal or bypass drift disables App writes.
- On an otherwise merge-eligible sandbox PR, the App merge call is denied and a human merge succeeds.
- A contiguous unknown human merge advances accepted public commit once and blocks downstream work pending reconciliation; an App or unauthorized merge advances only observed head.
- Direct push, skipped intermediate, later human merge on a divergent base, force or ancestry rewrite, reordered observation, stale pointer, and ruleset or authority-set drift all preserve the prior accepted pointer and create an incident.
- Exact repository-acceptance replay returns the first receipt; changed bytes under the same operation or observation identity collide, and a crash around pointer commit produces zero or one transition.
- The repository reconciler can append only `RepositoryAcceptanceEvent` plus the matching pointer receipt and is denied push, merge, review, evidence-graph mapping, attestation, promotion, and deployment effects.

## Acceptance criteria

- [ ] Credential-free fixtures prove deterministic normalization, lifecycle projection, and reconciliation.
- [ ] Agents can open and maintain evidence-complete draft PRs through the sandbox proposer App.
- [ ] Human-only default-branch update is enforced by policy, effective ruleset, App exclusion, and live merge denial.
- [ ] Checks, reviews, commands, and organizational readiness bind the exact head SHA.
- [ ] Missed, duplicated, edited, reordered, and ambiguous GitHub events converge without duplicate writes.
- [ ] Human edits and commits are preserved, and App revocation leaves the repository operable by humans.
- [ ] Unknown merges and direct updates are reflected truthfully and fail closed for promotion and deployment.
- [ ] Accepted-commit reconciliation proves a gap-free first-parent interval from the current pointer and cannot silently import an unauthorized intermediate commit.

## Pull-request evidence

SPEC-007A attaches schema goldens, signature and delivery fixtures, lifecycle replay, PR-body preservation tests, ambiguous-operation plans, and repository-acceptance fixtures for exact replay, stale/colliding operations, reordered observations, direct push, skipped intermediate, divergence-base merge, ancestry rewrite, unauthorized actor, ruleset drift, and crash recovery. SPEC-007B separately attaches the App permission manifest, effective ruleset snapshot, periodic drift result, live sandbox merge-denial transcript, one draft-PR trace, command-ingress trace, reconciler allow/deny receipts, revocation exercise, and proof that SPEC-019 attestation was not simulated by this layer.

## Normative external references

- GitHub REST API, [Pull requests](https://docs.github.com/en/rest/pulls/pulls), including create, update, and merge permission requirements.
- GitHub REST API, [Protected branches](https://docs.github.com/en/rest/branches/branch-protection), for required-review, update, and bypass enforcement. Verified 2026-08-15; the live permission/ruleset conformance test remains authoritative if documentation or provider behavior changes.
