# ADR-0010: Amend SPEC-002 for authoritative source binding and bounded public projections

- Status: accepted
- Date: 2026-08-15
- Spec: SPEC-002
- Lifecycle transition: SPEC-002@1 -> amended -> SPEC-002@2

## Context

SPEC-002 revision 1 established the public/private classification boundary, allowlisted new-identity projections, private source-bound plans and receipts, deterministic rendering, and closed public staging validation.

The revision does not identify the authoritative record from which a source kind, version, classification, retention, and exact bytes must be resolved. The current implementation consequently accepts a caller-supplied `source_classification` as the effective classification. A source record that declares `kind: CredentialRef` and `classification: secret_reference` can be presented to the planner as `private_operational`; an otherwise registered route can then emit an allowlisted public projection. A caller-controlled projection identity can likewise encode an exact private source digest even when the public body contains only allowlisted fields. These are normative ambiguities, not only implementation bugs: revision 1 does not define the classification high-water relation, the route's authoritative source binding, or a bounded noninterference rule for public identity and metadata.

Later evidence, context, promotion, governance, and credential contracts depend on public projections that do not expose private identities, membership facts, denial details, or equality oracles. They need one portable boundary that independent implementations can reproduce without claiming universal semantic data-loss prevention.

SPEC-000 revision 1 is also entering its amendment lifecycle. SPEC-002 revision 1 is frozen to `SPEC-000@1`; it cannot advance against the replacement constitution without its own revision and exact dependency binding.

## Decision

SPEC-002 revision 1 enters the terminal `amended` state and names `SPEC-002@2` as its only replacement. Revision 2 must preserve the allowlisted, new-identity projection architecture while defining one authoritative source-binding and bounded-declassification contract for lower-classified and public projections.

Every projection input must be privately bound to exact source bytes, registered source kind and version, effective classification, retention, and the authority-owned metadata from which those properties were resolved. A request-supplied classification or kind is a constraint only; it cannot establish, replace, or lower the authoritative value. Unknown sources, conflicting bindings, unresolved classifications, and unrepresentable joins fail closed. Effective classification is computed through one declared conservative join or high-water relation, and `secret_reference` is never declassifiable.

Every registered route must bind the source kind and version, effective source classification, output kind and version, exact transform version and digest, policy epoch, declared read set, and declassified output fields. Exact source identities, digests, locators, bindings, and classification evidence remain in the private plan and receipt. Public manifests and public checks remain independently verifiable without private-source access.

The projection guarantee is bounded and transform-local rather than a universal semantic data-loss-prevention claim. For a fixed route, public policy, public identity input, and declared declassified field values, changing an excluded private field must not change public bytes or public-facing metadata. Projection identities, paths, digests, lineage, statuses, and diagnostics must not encode a private identity, locator, digest, membership fact, denial detail, or other private-derived equality or existence oracle.

`public_derived` denotes a disclosure classification only. It does not imply evidence acceptance, human approval, promotion, deployment, read authority, or publication authority. Rendering and checking create a candidate projection. Publication or external delivery remains a separate exact-manifest authority decision under the then-effective constitution and the owning delivery specification.

Revision 2 must bind the current accepted constitution revision and provide adversarial fixtures for caller relabeling, provider high-water changes after planning, unregistered or mismatched source kinds with matching fields, reference or envelope laundering, private-derived projection identities and paths, equal-visible/different-hidden transform-local noninterference, and safe denial behavior.

This decision authorizes only the lifecycle transition. It does not accept revision 2, change policy or schema bytes, repair the exporter, authorize a private export, or permit publication. The replacement must enter as a digest-linked draft and complete ordinary architecture review and acceptance before implementation.

## Consequences

- Existing public exports must be revalidated under revision 2 before a later owner treats them as current evidence; ambiguous projections are quarantined rather than silently grandfathered.
- Later specifications may rely on authoritative projection identity, classification, and noninterference only after revision 2 is accepted and implemented.
- The successor implementation must add cross-runtime fixtures for classification joins, relabeling, source mutation, type laundering, identity and path oracles, public-denial behavior, deterministic replay, and rollback.
- SPEC-002 must be revised before it can advance against `SPEC-000@2` or satisfy later same-stage dependency floors.
- This terminal decision changes no current exporter, policy, schema, projection, or publication authority.

## Alternatives considered

- Patch only the current exporter. Rejected because another conforming implementation could still choose caller-provided classification or private-derived identity under the revision-1 text.
- Treat the request's classification as authoritative. Rejected because a requester cannot safely lower a classification owned by the source record or its registry.
- Promise universal semantic data-loss prevention. Rejected because it is neither mechanically decidable nor supported by the registered-transform architecture; the enforceable guarantee is route-bound and transform-local.

## Verification

The transition PR must change only lifecycle metadata in SPEC-002, add this one-purpose accepted ADR, update its index, preserve the active dependency-binding validator through a synthetic active fixture, regenerate deterministic inventory outputs, and pass the base-aware lifecycle validator against the exact parent branch. The successor and implementation PRs must separately provide the contract, fixtures, migration, rollback, and authority-separation evidence described above.
