# SPEC-002: Public and private boundary

- Status: implementing
- Wave: 0
- Classification: split
- Depends on: SPEC-000

## Decision

The public repository contains reproducible skills, rubrics, mechanisms, claims, public evidence metadata, evaluations, decisions, schemas, and sanitized examples. Private control-plane state contains credentials, identity material, personal destinations, restricted raw data, hidden evaluations, unreleased traces, and private human notes.

Private-to-public movement creates a new allowlisted projection. It never republishes a private record in place.

## Classifications

- `public`: authored for unrestricted repository publication.
- `public_derived`: a reviewed projection produced from another class.
- `private_operational`: queues, plans, receipts, traces, costs, and deployment state.
- `private_human`: private feedback, notes, and review context.
- `restricted_source`: raw content whose redistribution is limited.
- `secret_reference`: an opaque credential or capability reference; never exportable.

Each new export record declares classification and retention. Legacy artifact envelopes are registered and migrated by SPEC-003 rather than rewritten in this layer.

## Invariants

1. Public manifests contain no private input digest, source path, storage locator, credential reference, capability token, or private destination.
2. Restricted raw content may produce citation metadata through a registered transform but may not enter the staged public tree.
3. Unknown classifications, artifact kinds, transforms, fields, destinations, and files deny.
4. Rendering does not mutate sources and verifies the exact source bytes pinned by the private plan.
5. Staging becomes visible only after complete-tree validation; symlinks, non-regular files, traversal, collisions, extras, and missing outputs fail.
6. A public projection has a new identity. Its reference is provenance, not access authority.
7. Publication is not reversible; correction and tombstone records supersede prior artifacts without rewriting ordinary Git history.

## Interfaces

- `governance/export-policy.yaml`: classifications, retention defaults, routes, transformations, public fields, and correction rules.
- `validate_export.py plan`: create a private immutable source-bound plan.
- `validate_export.py render`: project into a fresh public staging tree and persist a private receipt.
- `validate_export.py check`: verify manifest closure, digests, policy pins, schemas, and supported detectors without private-source access.
- `researcher/exports/schemas/export-records.schema.json`: bootstrap request, plan, and manifest contract.

## Acceptance criteria

- [x] Export routes and classifications are allowlisted and versioned.
- [x] Secret-reference sources cannot enter a supported public projection.
- [x] Public records expose no private hash or locator.
- [x] Restricted-source raw bodies are structurally excluded while citation metadata remains useful.
- [x] Rendering is deterministic across fresh directories and atomic at the tree boundary.
- [x] Public staging closure, private canaries, source mutation, and path attacks fail closed.
- [x] Correction and removal procedures are documented.
- [x] A committed restricted-source example validates in CI.

This boundary does not claim full security hardening or universal detection of unknown semantic disclosures. Its guarantee is limited to registered transforms and validated staging paths.
