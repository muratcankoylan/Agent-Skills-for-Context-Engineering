# ADR-0008: Amend SPEC-000 for a closed authority vocabulary

- Status: accepted
- Date: 2026-08-15
- Spec: SPEC-000
- Lifecycle transition: SPEC-000@1 -> amended -> SPEC-000@2

## Context

SPEC-000 revision 1 established a deterministic, deny-by-default constitution and human-only merge, amendment, private-export, credential-destination, and weight-training authority. The later specification program makes durable state changes through typed event families whose append boundary must match an authenticated policy decision and runtime grant.

The revision-1 constitution does not define a complete, versioned catalog for those state-changing action and resource pairs. Treating every later command family as an ad hoc policy edit would make cross-spec review and replay ambiguous. Reusing broad research or execution permissions for protected effects would create privilege escalation paths, while leaving new effects unlisted would make accepted downstream contracts impossible to implement under default deny.

The roadmap therefore introduced a pre-Wave-1 requirement for a digest-pinned authority vocabulary, exact actor and maximum-effect profiles, mandatory decision context, dependency floors, grant operations, and executable allow and deny fixtures. That requirement changes the normative authority contract and cannot be added to an implemented revision in place.

## Decision

SPEC-000 revision 1 enters the terminal `amended` state and names `SPEC-000@2` as its only replacement. Revision 2 must retain deny-by-default and human-only merge authority while defining one closed, machine-validated authority catalog for every state-changing or privileged effect known to the specification program, plus an explicitly separate nonmutating read layer.

The replacement contract must bind the catalog schema, version, canonical path, and exact digest. It must require an exhaustive fixture manifest and, before implementation, a deterministic conformance receipt proving that the effective constitution neither denies declared valid operations nor permits undeclared or widened operations. Unknown pairs, inactive dependency owners, wrong actors, missing guards, widened effects, wrong grants, alternate permissive rules, and state-changing use of read authority must fail closed.

This decision authorizes only the lifecycle transition. It does not accept revision 2, create the registry, change the effective constitution, or authorize any runtime operation. Revision 2 must enter as a digest-linked draft and complete architecture review and acceptance before implementation.

## Consequences

- The current revision-1 constitution and policy remain historical implementation evidence; no existing rule is silently reinterpreted as a revision-2 authority profile.
- The exact currently effective `governance/constitution.yaml` remains the sole decision oracle under the prior policy until a successor is human-merged and becomes effective; this terminal specification decision neither revokes that oracle nor grants revision-2 authority.
- SPEC-004 and later revisions cannot enter architecture review until a human-merged SPEC-000 revision 2 supplies the validated registry and exact dependency floor required by the lifecycle gate.
- Authority-vocabulary changes are constitutional revisions with explicit downstream impact, not an ordinary runtime extension mechanism.
- The revision-2 implementation must close the policy allow-rule set structurally and execute cross-product negative cases, rather than relying only on a finite happy-path fixture list.
- Human merge, default-branch update, production activation, private export, credential administration, hidden evaluation, journal recovery, and weight training remain distinct protected effects.

## Alternatives considered

- Keep adding unregistered action strings to the YAML policy. Rejected because runtime event families and independent validators could not prove that they resolve to the same bounded authority semantics.
- Reuse broad `execute_work` or `research` permissions for later control-plane effects. Rejected because that would let a general executor acquire merge, recovery, credential, evaluation, or deployment authority by choosing a different resource label.
- Treat the registry as authority by itself. Rejected because the constitution decision, exact runtime grant, target and version guards, owner reducer, and dependency floor must all independently allow the effect.
- Patch the lifecycle validator without revising SPEC-000. Rejected because the validator would then enforce a contract absent from the authoritative specification.

## Verification

The transition PR must change only lifecycle metadata in SPEC-000, add this one-purpose accepted ADR, update its index, regenerate deterministic inventory outputs, and pass the base-aware lifecycle validator against the exact parent branch. The revision-2 draft and implementation must separately supply registry, fixture, policy-closure, conformance-receipt, migration, rollback, and cross-surface parity evidence.
