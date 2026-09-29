# ADR-0007: Amend SPEC-003 classification and reference invariants

- Status: accepted
- Date: 2026-08-15
- Spec: SPEC-003
- Lifecycle transition: SPEC-003@1 -> amended -> SPEC-003@2

## Context

SPEC-003 revision 1 established portable schema, identity, reference, envelope, storage, freeze, credential-reference, and legacy-migration contracts. Adversarial review of the merged implementation reproduced three gaps in its registry-aware validation boundary:

1. an `ArtifactRef` can target itself or another meta-reference, so a reference chain can evade the intended terminal-target boundary;
2. a public reference or envelope can name or contain a target whose registered classification is more restrictive, silently lowering the classification of the same content; and
3. a legacy-origin reference can name a target kind whose schema permits only native UUIDv7 identity, creating a reference to an impossible durable record.

These are contract defects, not merely implementation bugs. Revision 1 says classification cannot silently fall and that references bind target kind, version, prefix, and origin through the registry, but it does not state the closed reference graph and classification relation precisely enough for independent runtimes to converge on the same rejection behavior.

## Decision

SPEC-003 revision 1 enters the terminal `amended` state and names `SPEC-003@2` as its only replacement. Revision 2 must preserve the existing runtime-neutral registry and identity architecture while making the following invariants normative and cross-runtime:

- reference targets form a closed, acyclic graph; self-reference and undeclared meta-reference chains fail closed;
- an envelope, reference, or resolved target may retain or raise classification under one declared ordering, but it may never lower the classification of the same content;
- target identity origin is validated against the target schema contract, not inferred only from UUID shape or a caller-supplied origin label;
- public event or review surfaces cannot use an intermediate `ArtifactRef` or `ArtifactEnvelope` to launder a private target classification; and
- Python and TypeScript execute the same adversarial vectors and stable error codes for these invariants.

This decision authorizes only the lifecycle transition. It does not accept revision 2, modify schema bytes, or authorize implementation. The replacement must enter as a digest-linked draft and proceed through the normal architecture-review and acceptance transitions before code changes are eligible for implementation.

## Consequences

- Existing revision-1 bytes remain preserved in Git history and cannot be rewritten in place.
- Any record accepted only through the ambiguous reference behavior is not grandfathered into revision 2; it must be revalidated or quarantined.
- Later event, journal, graph, context, evaluation, and deployment specifications may rely on the corrected boundary only after revision 2 is accepted and implemented.
- The implementation PR must include Python and TypeScript parity, adversarial laundering fixtures, generated schema evidence, deterministic inventory regeneration, and public-boundary validation.

## Alternatives considered

- Patch validators without revising SPEC-003. Rejected because two conforming runtimes could otherwise make different decisions while both claiming revision-1 compliance.
- Allow bounded recursive references. Rejected for revision 2 because no current accepted contract requires them and recursive resolution adds cycle, availability, classification, and denial-oracle complexity.
- Treat classification as an unchecked annotation on references. Rejected because the public/private boundary would then depend on every downstream consumer remembering to resolve and reclassify the target.

## Verification

The transition PR must change only lifecycle metadata in SPEC-003, add this one-purpose accepted ADR, update its index, regenerate deterministic inventory outputs, and pass the base-aware lifecycle validator against the exact parent branch. The successor and implementation PRs must supply the contract and runtime tests described above.
