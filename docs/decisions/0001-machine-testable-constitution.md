# ADR-0001: Machine-testable, deny-by-default authority

- Status: accepted for proposal
- Date: 2026-08-10
- Spec: SPEC-000

## Context

Authority currently exists across `AGENTS.md`, rubrics, runbooks, workflows, and user instructions. That is auditable by a person but cannot produce a deterministic authorization decision for future commands, workers, and repository events.

## Decision

Use a versioned YAML constitution with a small exact-match policy engine. Actors, actions, resource classes, and conditions are enumerated. Missing vocabulary and missing conditions deny. Explicit deny rules override allow rules. Only `human_maintainer` can receive an allow decision for merge or production activation.

The generated Markdown view is derived from the same policy. `effective_commit: "$SELF"` identifies the commit containing the constitution without introducing an impossible self-referential Git hash. Runtime consumers pin the file SHA-256.

## Alternatives considered

- Keep prose as the only authority. Rejected because command-time enforcement and exhaustive tests would be impossible.
- Embed policy in Python conditionals. Rejected because authority changes would be difficult to review as a coherent matrix.
- Adopt a general policy service now. Deferred because the current repository needs deterministic local checks, not a hosted dependency.
- Infer intent from branch names, prompts, or role labels. Rejected because those are claims, not authenticated authority.

## Consequences

- Every future privileged interface must call the policy evaluator or document why it is read-only.
- Policy changes modify a protected surface and require human review and merge.
- The initial engine intentionally supports only exact conditions. New operators require a constitution schema change and tests.
- Identity authentication and external enforcement remain adapter responsibilities; this layer decides authority after a trusted actor class is supplied.
- A later GitHub lifecycle spec must evaluate protected changes under the prior effective policy. A policy PR cannot establish its own external branch protection or satisfy its own human review requirement.
- Policy-decision persistence will use the immutable event journal in SPEC-004. Until that lands, `--decision` provides the normalized record but the pure evaluator performs no hidden write.

## Verification

CI validates the policy, decision fixtures, deny-overrides behavior, digest pinning, path classification, and the full actor/action/resource cross-product. A generated authority table is checked byte-for-byte.
