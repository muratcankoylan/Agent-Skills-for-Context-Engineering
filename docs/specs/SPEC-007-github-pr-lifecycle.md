# SPEC-007: GitHub App and Pull-Request Lifecycle

Status: draft
Wave: 1
Classification: split
Owners: release steward agent; human maintainer
Depends on: SPEC-000, SPEC-004, SPEC-005, SPEC-006

## Decision

GitHub will be the public proposal, review, and promotion ledger. A limited proposer GitHub App may create branches, push candidate commits, open and update pull requests, request reviews, label state, and comment with evidence. It cannot write the default branch, approve, dismiss reviews, alter rulesets, create credentials, publish a release, or merge. Only a human merge of the current approved head SHA promotes a candidate.

## Context and current repository touchpoints

The repository already has CI and release manifests, but the autonomous loop stops at PR-ready artifacts. The organization must observe approvals, requested changes, comments, check changes, closures, and merges, and must trigger the correct follow-up without trusting one webhook delivery.

## Goals

- Let agents independently prepare and maintain high-quality PRs.
- Model GitHub state with exact head SHA and review identity.
- Reconcile missed, duplicated, and reordered webhooks.
- Enforce human-only promotion both by GitHub rules and organizational policy.

## Non-goals

- Agent merge, auto-merge, or branch-protection administration.
- Using a personal access token as the long-term identity.
- Treating a PR comment as trusted without channel authentication and policy checks.

## Invariants

1. Review and check state is bound to an exact head SHA.
2. A reviewable push invalidates the organization's prior approval projection.
3. Webhook payloads are signature-validated, deduplicated, stored, and reconciled through GitHub reads.
4. Candidate ID, work order, baseline, evaluation report, and head SHA are present on every organization-authored PR.
5. App permissions cannot merge or modify rulesets.
6. A merged default-branch commit is the only event that updates the accepted public commit. Active deployment is a separate projection and cannot precede that merge.
7. Every agent-authored PR identifies the automated proposer, candidate ID, and supervising human maintainer.

## Interfaces and data

Normalize GitHub deliveries into PR events for opened, synchronized, review submitted or dismissed, check suite changed, comment command, closed, reopened, and merged. Store delivery ID, repository ID, installation ID, PR number, actor, action, head/base SHA, received time, signature result, and raw-payload reference.

Lifecycle:

```text
candidate_validated -> branch_prepared -> branch_pushed -> pr_open
-> checks_running -> attestation_pending -> evidence_attested -> review_requested
-> changes_requested | approved_waiting_human_merge
-> pr_updated -> checks_running
-> merged | rejected | closed | superseded
```

The reconciler fetches authoritative PR, commits, checks, reviews, comments, and merge state on every relevant trigger and periodically while open. The `evidence_attested` projection is populated by SPEC-019 and bound to the current head SHA. PR body uses a generated evidence manifest and preserves a human-editable summary section.

## State and failure behavior

Branch push and PR creation use stable names and idempotency keys. An ambiguous API response triggers lookup by branch and candidate marker. Divergence or human edits cause `reconciliation_required`, never force-push. A closed unmerged PR retains its candidate and reason. A merged unknown PR triggers inventory and policy reconciliation before projection.

## Implementation sequence

1. Define lifecycle projector and replay it against webhook fixtures.
2. Configure a test proposer App with minimum repository permissions and SPEC-003 credential references.
3. Add webhook receiver, signature verification, durable receipt, and read reconciler.
4. Enable branch and draft-PR creation in proposal mode.
5. Add review-command handling and merged-commit projection; continuous credentialed operation remains disabled until SPEC-024.

## Migration and rollback

Import open organization PRs through the reconciler, not fabricated webhooks. Rollback revokes or suspends the App installation and leaves open branches and PRs for human handling. Production remains pinned to the last merged commit.

## Observability

Show delivery failures, reconciliation drift, webhook lag, App rate limits, PRs by lifecycle state, stale approvals, failing checks, time waiting for human, merged commit, accepted public commit, and any lagging active deployment commit.

## Verification

- Invalid webhook signatures are rejected before parsing.
- Duplicate and reversed deliveries converge to GitHub's current state.
- Ambiguous PR creation does not create a duplicate.
- A push after approval returns to checks and review.
- App credentials receive a permission-denied result for merge and ruleset changes.
- Human merge triggers exactly one promotion work order.

## Acceptance criteria

- [ ] Agents can open and update evidence-complete PRs through the proposer App.
- [ ] Human-only merge is enforced in policy and GitHub configuration.
- [ ] State binds approvals and checks to head SHA.
- [ ] Reconciler repairs missed and out-of-order deliveries.
- [ ] Human edits are preserved.
- [ ] Revoking the App leaves the repository operable by humans.

## Pull-request evidence

Attach App permission manifest, ruleset snapshot, lifecycle replay, invalid-signature and duplicate-delivery tests, one sandbox PR trace, and proof that the App cannot merge.
