# SPEC-024: Private Control Plane, Identities, and Key Management

Status: draft
Wave: 5
Classification: split
Owners: human maintainer; operations steward agent
Depends on: SPEC-002, SPEC-003, SPEC-007, SPEC-008, SPEC-009, SPEC-014, SPEC-015, SPEC-017

## Decision

Private operations will use a replaceable control-plane interface outside Git history. It owns credential references, identity bindings, active queues and leases, private event and trace storage, hidden evaluations, notification destinations, provider billing receipts, and deployment configuration. Humans own credentials. Workers receive short-lived, operation-specific capabilities and opaque references, never raw reusable keys in prompts or persisted work orders.

## Context and current repository touchpoints

Runtime queues, locks, runs, loop reports, and snapshots are already ignored. Future operation adds GitHub App private keys, webhook secrets, Cursor SDK keys, X access, email credentials, personal destinations, hidden tests, and licensed source bodies. Public schemas and adapters should describe these classes without exposing their values.

## Goals

- Separate observer, proposer, validator, reconciler, delivery, and human identities.
- Resolve credentials only at the execution boundary and for the shortest practical time.
- Support local macOS operation first and later hosted operation without changing work orders.
- Back up and restore private state while exporting useful redacted manifests.

## Non-goals

- A full enterprise identity platform in the first release.
- Model-visible environment dumps or repository `.env` files.
- Sharing a personal access token across all functions.

## Invariants

1. Secret values never appear in prompts, skills, events, logs, result artifacts, public exports, or model-visible command output.
2. `credential_ref` names purpose, not value or storage location.
3. Each identity has minimum declared operations, repository or provider scope, owner, expiry or rotation, and revocation procedure.
4. GitHub proposer cannot merge, approve, change rules, write workflows, or write the default branch.
5. Test, shadow, and production identities and budgets are distinct.
6. Access and rotation events record references and results, not secret material.
7. A missing or expired credential blocks only affected work and never triggers silent fallback.

## Interfaces and data

SPEC-024 introduces and owns the production `CredentialBroker` interface. It resolves the SPEC-003 `CredentialRef` and `CapabilityGrantSpec` contracts and must remain conformant with the SPEC-003 fake capability provider's scope and replay semantics:

```text
describe(ref, actor) -> CapabilityMetadata
issue(ref, actor, operation, ttl, context) -> EphemeralCapability
revoke(capability_id, reason) -> RevocationReceipt
test(ref, non_mutating_probe) -> CredentialHealth
inventory() -> RedactedInventory
```

Initial identities are GitHub observer, proposer, validator/check writer, and promotion reconciler; source-feed readers; Cursor benchmark executor; notification sender; webhook verifier; and human maintainer. GitHub uses App installation tokens rather than a broad personal token. Hosted deployments prefer OIDC for vault or cloud access.

The local reference provider supports macOS Keychain or an equivalently scoped user-selected secret store through an adapter. Process environment receives an ephemeral value only for the child process that needs it. Private deployment manifest pins public core commit, schema versions, adapter-lock digest, policy-bundle digest, deployment identity, provider references, budgets, and backup policy.

## State and failure behavior

Credential references move `planned -> provisioned -> tested -> active -> rotation_due -> rotated|revoked`. Issued capabilities expire automatically. Provider unavailability yields `credential_unavailable`; a revoked capability cannot be refreshed by the worker. Suspected exposure pauses affected identities and creates a human review item.

## Implementation sequence

1. Inventory every current and planned external capability and owner.
2. Implement broker plus fake and local secret-store providers.
3. Configure separate GitHub App identities and webhook verification.
4. Move benchmark, feed, and delivery adapters to references.
5. Add rotation tests, encrypted backup, and hosted-provider/OIDC adapter only when deployment requires it.

## Migration and rollback

Existing environment-based keys are mapped one by one to references and rotated if previously exposed. Dual mode is time-bounded and warns on direct environment use. Rollback disables affected integrations and keeps deterministic local and manual paths available.

## Observability

Expose redacted inventory, owner, scope, last health test, issuance count, expiry, rotation due date, denied operation, provider availability, and per-identity cost. Never log secret length, prefix, or suffix.

## Verification

- Seeded secrets cannot appear in captured prompts, logs, events, public exports, or crash reports.
- Proposer identity receives permission denial for merge and ruleset operations.
- An expired capability cannot be reused.
- Provider outage blocks only dependent work with a useful status reason.
- Rotation succeeds while queued work reconciles safely.
- Backup and restore recover references and state without printing values.

## Acceptance criteria

- [ ] All external adapters consume credential references.
- [ ] Identity and operation scopes are documented and mechanically checked.
- [ ] GitHub proposer and validator identities are separate.
- [ ] Secret-store and fake-provider conformance tests pass.
- [ ] Rotation, revocation, outage, backup, and restore are exercised.
- [ ] Public deployment manifests reveal no private destination or secret.

## Pull-request evidence

Attach redacted inventory, identity matrix, seeded-secret scan, permission-denial proof, expiry and rotation tests, outage behavior, and backup/restore transcript.
