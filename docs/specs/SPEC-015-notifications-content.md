# SPEC-015: Notification Outbox, Review Packets, and Content Drafts

Status: draft
Wave: 2
Classification: split
Owners: community editor agent; operations steward agent; human maintainer
Depends on: SPEC-002, SPEC-006, SPEC-007

## Decision

All messages to the human or community-facing channels will pass through a transactional outbox. Agents may prepare laptop and email notifications, research digests, community questions, and social-media drafts. Delivery follows channel policy; public posting remains a separate human-authorized command. A content rejection changes only that draft unless the human explicitly scopes the feedback more broadly.

## Context and current repository touchpoints

The current researcher produces local reports but lacks delivery receipts, acknowledgement, retry, public/private rendering, and a governed path from low-confidence research to a community question. The user wants agents to surface PRs, source decisions, and post suggestions without requiring constant supervision.

## Goals

- Deliver actionable, deduplicated notifications to local laptop and approved email targets.
- Generate evidence-linked review packets for PR and non-PR decisions.
- Turn unresolved high-value questions into shareable drafts without overstating evidence.
- Learn from rejected drafts with explicit feedback scope.

## Non-goals

- Autonomous posting to public social accounts in the initial system.
- Marketing copy disconnected from research evidence.
- Sending every low-value rejection or feed item to the human.

## Invariants

1. The state transition and outbox insert share one transaction.
2. Delivery uses a stable message and destination idempotency key.
3. Public drafts cite public evidence and label uncertainty, inference, and questions.
4. No destination address or credential appears in public artifacts.
5. Editing or rejecting a draft does not mutate its underlying research verdict.
6. A send or publish action records exact rendered digest and human authorization where required.

## Interfaces and data

`OutboxMessage` includes event and subject IDs, template version, audience, classification, channel, destination reference, priority, rendered artifact digest, deduplication window, send-after time, retry policy, acknowledgement requirement, and expiry.

Initial adapters are local macOS notification, approved email provider or SMTP relay, and GitHub comment or issue. Each supports `render`, `deliver`, `status`, and `reconcile`. Destination references resolve in the private control plane.

A review packet contains decision requested, recommendation, gate results, evidence for and against, contradictions, evaluation results, cost, changed artifacts, risks, and available commands. A social draft contains audience, thesis, evidence links, uncertainty, community question, platform variants, and prohibited unsupported claims.

## State and failure behavior

Messages move `pending -> rendered -> ready -> delivering -> delivered -> acknowledged`, with `retryable_failed`, `permanent_failed`, `expired`, or `cancelled`. Ambiguous sends reconcile by provider message ID. Drafts move `proposed -> evidence_checked -> human_review -> approved_for_manual_use|revision_requested|rejected|superseded`. Approval for manual use does not automatically invoke a public platform.

## Implementation sequence

1. Implement outbox storage, projector, renderer, and mock adapter.
2. Add local laptop notifications for high-priority operator events.
3. Add email delivery with private destination references.
4. Add review packet and daily or weekly digest templates.
5. Add evidence-checked social and community-question drafts plus feedback capture.

## Migration and rollback

Existing reports remain files and may be linked from new messages. Channel activation is allowlisted per destination. Rollback stops dispatch, preserves pending messages, and lets the human read generated packets locally.

## Observability

Track queue age, deliveries, retries, acknowledgements, deduplication, messages per priority, human review time, draft acceptance and revision reasons, source-to-notification latency, and channel cost.

## Verification

- A crash after provider send does not send a duplicate after reconciliation.
- Private destinations never appear in public review packets.
- Unsupported claims fail evidence checking.
- Rejecting a social draft leaves the source and mechanism decision unchanged.
- One feedback reason scoped to organization appears only after confirmation.
- Expired low-priority digests do not crowd urgent PR or failure notices.

## Acceptance criteria

- [ ] Notification delivery is durable, idempotent, and observable.
- [ ] Laptop and email adapters use private destination references.
- [ ] Review packets contain commands and decision-grade evidence.
- [ ] Social output is draft-only until a human-authorized publish integration is specified.
- [ ] Content and research verdict states are independent.
- [ ] Feedback scope is recorded and tested.

## Pull-request evidence

Attach mock and live-channel receipts with redacted targets, crash/reconcile test, sample review packet and social draft, evidence-check failure, and scoped-rejection trace.
