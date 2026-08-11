# ADR-0005: Publish one machine-checked specification program

- Status: accepted
- Date: 2026-08-10
- Specs: SPEC-000 through SPEC-026

## Context

The first four implemented specifications are canonical under `docs/specs/`, while the remaining program was drafted under the local `outputs/` delivery directory. The local directory also retained older copies of SPEC-000 through SPEC-003 whose contracts conflict with the merged implementation. In particular, those drafts reintroduced self-referential inventory commits, private input commitments in public export records, locators in portable artifact references, and premature schema registration.

A public autonomous organization cannot depend on a local planning directory or tolerate two specification bodies for one identifier.

## Decision

`docs/specs/` is the only canonical specification program. The merged SPEC-000 through SPEC-003 bodies remain authoritative. SPEC-004 through SPEC-026 and the specification template are published there as drafts after reconciliation with implemented contracts.

Publishing a draft does not accept it. Acceptance requires an explicit lifecycle status change in a human-merged pull request. `Depends on` is the canonical dependency direction; derived views may compute unlock relationships but specifications do not maintain a second `Unlocks` field.

The generated corpus inventory records specification identity, lifecycle metadata, dependencies, path, and exact byte digest. It rejects duplicate identifiers, filename or title mismatches, invalid metadata, dangling dependencies, cycles, invalid wave ordering, index drift, and unindexed specification files.

`outputs/` remains an ignored local drafting and delivery surface. No file under that directory is a public source of truth. The long-form architecture document remains local until its volatile claims, current-state assertions, and provenance receive a separate review.

## Consequences

- Future agents can discover the entire roadmap from tracked repository state.
- Draft and implemented contracts cannot silently diverge under the same specification ID.
- A specification change affects the generated source-tree digest and must pass inventory validation.
- Roadmap dependencies are mechanically testable before orchestration code relies on them.
- Local user-facing deliverables cannot be staged accidentally by broad Git commands.

## Alternatives considered

- Commit the complete `outputs/` directory. Rejected because it includes obsolete duplicate specifications and unaudited architecture drafts.
- Replace merged specifications with the longer planning drafts. Rejected because it would regress executable decisions made during SPEC-000 through SPEC-003 implementation.
- Publish future specifications only when implemented. Rejected because the organization and contributors need a reviewable dependency graph before implementation begins.

## Verification

Inventory tests mutate headers, dependencies, filenames, index links, and graph topology and require stable typed failures. Repeated inventory builds must be byte-identical. CI also asserts that no `outputs/` path is tracked.
