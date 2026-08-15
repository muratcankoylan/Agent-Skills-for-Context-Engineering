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

Canonical status represents a merged normative revision, not transient delivery activity. `implementing` is therefore not a specification status: an open pull request is a derived GitHub/journal projection and merging that pull request closes it. The normative lifecycle is `draft -> architecture_reviewed -> accepted -> implemented -> verified -> operational`, with human-merged terminal decisions for amendment, supersession, or retirement.

Every revision declares its integer revision number and exact predecessor digest. Drafts may change in place. A lifecycle transition changes only status and the lifecycle metadata required by that transition; it cannot change the contract. A contract that has reached architecture review must first enter a human-merged terminal amendment or supersession state before a replacement draft can bind and increment it. A base-aware validator compares the candidate to the exact pull-request base and rejects deletion, skipped status, regression, combined contract/status change, mutable terminal metadata, or an unbound replacement.

This decision introduces that machinery after SPEC-000 through SPEC-003 were implemented. Its merge is a one-time adoption event, not invented history: PR #116 at `48bc565ab18512462e6773a7a724a130c7868a6f`, PR #117 at `4deb96cf1f54979fd572954bb983f20f6f4a125b`, PR #119 at `69bc429f6bd475f65fb3c0decd6afb2e2c3b885b`, and PR #120 at `6dbe1a1d868eab51a3bc9011b0f55e2891513e40` are recorded as the observed human merges for revision 1. No other specification receives the exception.

The generated corpus inventory records specification identity, lifecycle metadata, dependencies, path, and exact byte digest. It rejects duplicate identifiers, filename or title mismatches, invalid metadata, dangling dependencies, cycles, invalid wave ordering, index drift, and unindexed specification files.

`outputs/` remains an ignored local drafting and delivery surface. No file under that directory is a public source of truth. The long-form architecture document remains local until its volatile claims, current-state assertions, and provenance receive a separate review.

## Consequences

- Future agents can discover the entire roadmap from tracked repository state.
- Draft and implemented contracts cannot silently diverge under the same specification ID.
- A specification change affects the generated source-tree digest and must pass inventory validation.
- Roadmap dependencies are mechanically testable before orchestration code relies on them.
- Normative lifecycle and derived pull-request progress cannot be conflated by an agent or adapter.
- Accepted contract edits require a new digest-linked revision instead of silently changing an already authorized surface.
- Local user-facing deliverables cannot be staged accidentally by broad Git commands.

## Alternatives considered

- Commit the complete `outputs/` directory. Rejected because it includes obsolete duplicate specifications and unaudited architecture drafts.
- Replace merged specifications with the longer planning drafts. Rejected because it would regress executable decisions made during SPEC-000 through SPEC-003 implementation.
- Publish future specifications only when implemented. Rejected because the organization and contributors need a reviewable dependency graph before implementation begins.

## Verification

Inventory tests mutate headers, revisions, dependencies, filenames, index links, and graph topology and require stable typed failures. Base-aware lifecycle tests exercise legal transitions, skipped states, revision digests, accepted-body mutation, deletion, and the exact one-time adoption. Repeated inventory builds must be byte-identical. CI also asserts that no `outputs/` path is tracked.
