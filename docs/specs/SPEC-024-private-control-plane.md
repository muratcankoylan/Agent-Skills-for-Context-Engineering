# SPEC-024: Private Control Plane, Identities, and Key Management

Status: draft
Revision: 1
Revises: none
Wave: 5
Classification: split
Owners: human maintainer; operations steward agent
Depends on: SPEC-002, SPEC-003, SPEC-004, SPEC-005, SPEC-006, SPEC-007, SPEC-008, SPEC-009, SPEC-014, SPEC-015, SPEC-016, SPEC-017, SPEC-019

## Decision

Private operations will use a replaceable, version-controlled control-plane module in the standalone open-source Python cloud service, composed over the SPEC-003 artifact store, SPEC-004 journal and owner-controlled private indexes. The initial single coordinator uses SQLite on persistent local disk; cloud deployment does not imply a second workflow database or a distributed broker. Library code, schemas, fake providers and conformance tests are public; instantiated state, provider bindings, manifests, credentials and receipts remain outside Git history. The service resolves credential references, authenticated identities, hidden evaluations, notification destinations, provider billing receipts and deployment configuration through public runtime-neutral contracts. Humans own credential provisioning and break-glass authority. Workers receive short-lived, attempt-bound, operation-specific capabilities at the execution boundary, never raw reusable keys, provider locators, or live capability tokens in prompts, context packages, persisted work orders, events, logs, checkpoints or result artifacts.

## Context and current repository touchpoints

Runtime queues, locks, runs, loop reports and snapshots are already ignored. Operation adds GitHub App private keys, webhook secrets, configurable native model-provider credentials, registered MCP bindings, X access, delivery credentials, personal destinations, hidden tests and licensed source bodies. Public schemas describe purpose and scope without exposing values. Codex credentials, task sessions and the developer's ambient accounts are not service dependencies.

## Goals

- Separate observer, proposer, validator, reconciler, delivery, and human identities.
- Resolve credentials only at the execution boundary and for the shortest practical time.
- Support local Docker development and a single-tenant cloud VM without changing work orders or depending on a developer session.
- Back up and restore private state while exporting useful redacted manifests.

## Non-goals

- A full enterprise identity platform in the first release.
- Model-visible environment dumps or repository `.env` files.
- Sharing a personal access token across all functions.
- A second queue, lease, event, or workflow authority beside SPEC-004 and SPEC-005.
- A separately deployed broker or mandatory cloud-vendor SDK when the in-process authenticated adapter boundary suffices.

## Invariants

1. Secret values never appear in prompts, skills, events, logs, result artifacts, public exports, or model-visible command output.
2. `credential_ref` names purpose, not value or storage location.
3. Each identity has minimum declared operations, repository or provider scope, owner, expiry or rotation, and revocation procedure.
4. GitHub proposer cannot merge, approve, change rules, write workflows, or write the default branch.
5. Test, shadow, and production identities and budgets are distinct.
6. Access and rotation events record references and results, not secret material.
7. A missing or expired credential blocks only affected work and never triggers silent fallback.
8. Every capability binds issuer, authenticated actor, work order, attempt, fencing token, audience, exact operation and resource, classification ceiling, issue and expiry, use limit, budget reservation, and policy digest. Widening any field requires a new authorization.
9. Broker description and denial responses reveal no secret presence, provider locator, key metadata, hidden-resource membership, or reusable oracle to an unauthorized actor.
10. Resolution occurs only in an attested eligible child boundary. Models receive narrow tool operations or opaque one-use handles, not environment dumps or broker APIs.
11. Break-glass use is human-authenticated, time-limited, reason-bound, separately notified, and incapable of changing constitutional authority or merge policy.
12. Private backups are encrypted and authenticated; recovery material is stored separately and is never exported with the backup or deployment manifest.
13. Every broker method authenticates its caller. Actor identity is derived from the trusted supervisor or adapter boundary, never accepted as a caller-supplied string.
14. A grant digest proves byte integrity only. Issuance authority comes from the authenticated broker decision and attestation, not possession of a record or digest.
15. Restored backups contain no live capability. All pre-backup ephemeral or scoped capabilities remain expired or revoked and new work must obtain a fresh fenced issuance.

## Interfaces and data

SPEC-024 introduces and owns the production `CredentialBroker` interface. It resolves the SPEC-003 `CredentialRef` and `CapabilityGrantSpec` contracts and must remain conformant with the SPEC-003 fake capability provider's scope and replay semantics:

```text
describe(authenticated_call_context, ref) -> CapabilityMetadata
issue(authenticated_call_context, ref, work_order, attempt, fencing_token,
      operation, resource, reservation, ttl, context) -> Capability
revoke(authenticated_call_context, capability_id, reason) -> RevocationReceipt
test(authenticated_call_context, ref, non_mutating_probe) -> CredentialHealth
inventory(authenticated_call_context, filters) -> RedactedInventory
```

`authenticated_call_context` is an unforgeable in-process or authenticated-transport context constructed by the trusted supervisor or adapter boundary. It is not a serialized principal value that a worker, model, request body, or caller can supply.

Revision 1 capability classes are `ephemeral_one_use` and `attempt_scoped_session`. The first is the default. An attempt-scoped session is available only to an attested supervisor-owned adapter, binds one work order, attempt, fence, audience, operation set, and reservation, never crosses into a model or worker-visible boundary, and expires no later than that attempt lease. Every provider effect still carries a stable operation identity and receipt. Reusable service capabilities are out of scope and require a later human-merged revision with an independently reviewed service-identity and revocation contract; a worker cannot request a class upgrade.

The initial machine principals are supervisor/reconciler, GitHub proposer, evaluation designer, epoch sealer, hidden runner, analyzer, independent release attestor/check writer, and delivery adapter, plus the human maintainer. Candidate proposer and every role declared distinct by the active SPEC-016 `EvaluationIndependencePlan` receive different authenticated principals, workspaces and capability sets for that candidate; a principal cannot combine roles through another profile. Developmental researcher, critic and skill-editor labels do not alone establish independent evaluation. Feed, benchmark and provider operations are scoped profiles unless a provider or independence boundary requires a separate identity. GitHub uses App installation tokens rather than a shared personal token. Hosted operator login and workload identities may use reviewed OIDC adapters with issuer, audience, subject, expiry and replay validation; accepting a token or caller-supplied role string is not authorization.

The independent canary-health attestor is also a distinct machine principal. Its only production conclusion authority is `attest_canary_health/deployment_canary` for one exact SPEC-025 epoch, policy, closed observation interval, and evidence set. It has no candidate, proposer, activation, daemon-operation, credential-administration, deployment-change, or pointer-write capability. Identity conformance rejects any workspace, credential reference, runtime grant, or principal mapping that combines it with the candidate, proposer, daemon, activating human, or another role whose independence is required.

Reference adapters support an explicitly selected development environment-variable or mounted-secret reference and a reviewed cloud secret-store/workload-identity binding. Keychain is optional, not the deployment model. A development config names the variable or private mounted reference, never its value; the trusted provider adapter resolves it only when admitting the configured operation. The process has a minimal environment allowlist, no model-visible environment inspection and no default loading of home-directory, Codex, shell or project credentials. Production deployment must demonstrate the accepted broker and effective isolation boundary; an environment reference alone does not establish either.

SPEC-024 owns the private `ProviderBindingSet`: provider adapter and private endpoint, model allowlist, credential purpose, registration/version and permitted operations for MCP, destination reference, rotation policy and broker configuration. Arbitrary configured providers are extensibility points, not authorization to contact arbitrary URLs or execute discovered tools. Authentication headers cannot be forwarded across redirects or unrelated hosts. Read-only MCP and research APIs receive no GitHub or delivery credential. SPEC-025 owns the private `DeploymentManifest` consuming the binding-set reference; SPEC-008 owns its new-identity public status projection. Public records expose no private manifest/binding identity or digest, provider locator, destination, budget detail or secret-store fact.

Standing operator configuration may authorize bounded automatic draft-PR creation and notification to named private destinations. Each effect still needs its exact owner-issued operation/grant and durable outbox identity; model text cannot add a repository, recipient, channel or permission. This is automatic proposal/delivery within configured scope, not automatic merge, release or deployment. A provider canary, destination test or repository sandbox is itself an explicitly bounded external operation, not a secret-validation shortcut with unrestricted effects.

Credential lifecycle mutation uses three exact authority boundaries in the human-merged SPEC-000 vocabulary. `manage_credential_binding/credential_binding` lets an authenticated human provision, test-and-activate, rotate, or manually revoke one exact `CredentialRef`/provider binding under an expected binding version, accepted commit, policy and provider configuration digest, stable operation key, and bounded reason; it cannot issue a capability or widen the referenced operation set. `revoke_capability/capability` lets the dedicated credential reconciler append one stop-only revocation for an exact capability or affected identity set, expected version, evidence/cause, policy context, and operation key; it cannot issue, replace, rotate, or re-enable anything. `invoke_break_glass/credential_binding` is human-only and creates one time-bounded, reason-bound, destination- and operation-scoped break-glass authorization with an expiry, notification intent, expected binding version, accepted commit, explicit maximum effect, and stable operation key. It cannot change the constitution, provider scope, merge rules, hidden-evaluation policy, or create reusable authority.

Capability issuance itself does not receive a fourth ambient action. `CredentialBroker.issue` accepts only a current policy allow and runtime grant for the underlying requested operation/resource, verifies attempt, fence, reservation, audience and classification, and derives a strictly narrower capability. If any field is wider than the existing allow/grant or no exact operation is authorized, issuance denies. Possession of a credential reference, binding, broker method, or prior capability cannot mint authority.

## State and failure behavior

Credential references move `planned -> provisioned -> tested -> active -> rotation_due -> rotated|revoked|compromise_suspected`. Every transition is compare-and-append against the exact binding version. Exact operation replay returns the first receipt; the same key with changed bytes collides, and crash recovery reconstructs zero or one transition. Issued capabilities expire automatically and are never refreshed by a worker; active work reconciles under the old receipt or receives a newly authorized attempt after rotation. Provider unavailability yields `credential_unavailable`; a revoked capability cannot be refreshed or replaced by another credential class. Suspected exposure immediately invokes only the stop-side `revoke_capability/capability` reducer, pauses affected identities, cancels new issuance, creates a human review item, and preserves evidence without logging suspected secret material. Re-enabling or rotating remains a separate human credential-binding decision.

## Implementation sequence

1. Inventory every current and planned external capability and owner, including canary-health and credential-control principals.
2. Register credential-management, stop-only revocation, break-glass, and derived-issuance contracts with exact authority profiles and receipts.
3. Implement broker plus fake, explicit development-reference and reviewed cloud secret-store/workload-identity adapters without coupling canonical state to a vendor.
4. Configure separate GitHub App identities and webhook verification.
5. Move native-model, read-only MCP, feed, evaluation and delivery adapters to independent scoped references; retain the legacy benchmark runner's zero-call boundary until separately changed.
6. Add OIDC/authenticated operator binding, rotation and revocation tests, encrypted backup and clean-cloud restore before production admission.

## Migration and rollback

Existing environment-based keys are mapped one by one to explicit development references and rotated if previously exposed. Production migration selects the reviewed secret-store and workload-identity binding without rewriting public work orders. Rollback disables affected integrations, preserves unknown outcomes and keeps credential-free status, replay and diagnosis available; it cannot fall back to a developer's ambient credential or reset consumed budgets.

## Observability

Expose redacted inventory, owner, scope, last health test, issuance count, expiry, rotation due date, denied operation, provider availability, and per-identity cost. Never log secret length, prefix, or suffix.

## Verification

- Seeded secrets cannot appear in captured prompts, logs, events, public exports, or crash reports.
- Proposer identity receives permission denial for merge and ruleset operations.
- An expired capability cannot be reused.
- A capability for another attempt, fence, audience, operation, resource, classification, or reservation is denied, and one-use replay fails.
- A caller-supplied principal field cannot influence broker identity, and an attempt-scoped adapter handle cannot enter a worker/model environment or survive its lease.
- Provider outage blocks only dependent work with a useful status reason.
- Rotation succeeds while queued work reconciles safely.
- Human credential administration, stop-only compromise revocation, and break-glass deny a wrong principal/action, stale version, widened scope, missing guard, changed-byte replay, and expiry; crash boundaries produce zero or one receipt.
- Derived issuance is denied without a matching underlying operation allow and grant and can only narrow actor, attempt, fence, audience, operation, resource, classification, budget, use count, and expiry.
- Canary-health identity fixtures prove the attestor cannot share a principal, workspace, credential binding, or capability set with the candidate, proposer, daemon, activating human, or release roles declared independent.
- Backup and restore recover references and state without printing values.
- Seeded values and secret-presence canaries remain absent from prompts, context packages, process listings captured by agents, tool errors, denial timing classes, checkpoints, traces, crash reports, and public projections.
- Break-glass, broker outage, compromise pause, and mid-attempt rotation preserve least privilege and reconciled state.
- Wrong OIDC issuer/audience/subject, expired sessions, revoked roles and request-supplied principals cannot access another run, secret binding or effect destination.
- Configured native-model, MCP, GitHub and notification adapters cannot borrow each other's credentials; unsafe endpoints, redirects, tool/schema drift and changed-byte operation replay fail before an effect.
- Removing Codex and the developer's home-directory configuration does not change admitted service work; missing explicit references fail only dependent operations.

## Acceptance criteria

- [ ] All external adapters consume credential references.
- [ ] Identity and operation scopes are documented and mechanically checked.
- [ ] GitHub proposer and validator identities are separate.
- [ ] Secret-store and fake-provider conformance tests pass.
- [ ] Rotation, revocation, outage, backup, and restore are exercised.
- [ ] Credential lifecycle, stop-only compromise response, break-glass, and derived issuance each have one non-overlapping authority path with stale, replay, collision, crash, expiry, and wrong-principal fixtures.
- [ ] New-identity public deployment status projections reveal no private manifest identity or digest, destination, provider reference, or secret-store fact.
- [ ] Capability issuance is attempt-, fence-, operation-, resource-, classification-, use-, reservation-, and expiry-bound and denies silent fallback.
- [ ] Recovery keys are separated from encrypted backups and restore evidence exposes neither values nor provider locators.
- [ ] Development references and cloud identity/secret-store adapters use one portable binding contract without ambient credential fallback.
- [ ] Authenticated operator configuration scopes automated PR and notification effects to exact repositories, destinations, permissions and budgets.

## Pull-request evidence

Attach redacted inventory, identity and non-combinability matrix, seeded-secret scan, permission-denial proof, credential-management/revocation/break-glass allow and denial receipts, derived-issuance narrowing fixtures, stale/replay/collision/crash/expiry tests, canary-attestor separation proof, outage behavior, and backup/restore transcript.
