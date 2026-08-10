# ADR-0002: Treat the corpus inventory as a checked derived view

- Status: accepted for proposal
- Date: 2026-08-10
- Spec: SPEC-001

## Context

Repository facts are distributed across skill files, registries, append-only ledgers, fixtures, benchmark tasks, manifests, and a curated corpus relationship index. Live prose had drifted from those files. A committed inventory must be deterministic, but embedding its own future Git commit would create a self-reference.

## Decision

`researcher/corpus/inventory.json` is a generated cache, not a source of truth. It lists canonical input paths and exact byte digests and binds them with a `source_tree_digest`. It excludes wall-clock time, dirty-worktree state, its own output, and the Git commit that will contain it. CI reports Git revision separately.

`researcher/corpus/index.json` remains the curated source for non-derivable relationships such as activation scenarios and cross-skill claim use. The inventory verifies it against actual skills, claim ownership, mechanism ownership, fixtures, and manifests. It does not infer structured semantics by scraping arbitrary prose.

Live documents link to the generated summary. Dated benchmark reports, release notes, and project narratives retain their historical values. Missing and weak ledger provenance is repaired only by new append-only reconciliation records with original source commits; old events are not rewritten.

## Alternatives considered

- Make the generated inventory canonical. Rejected because a cache must not overrule its inputs.
- Embed `HEAD`. Rejected because a commit cannot contain its own final hash without perpetual drift.
- Generate the corpus index from Markdown. Rejected because free-text activation meaning and related-claim use are curated semantics.
- Rewrite historical reports with current totals. Rejected because that would falsify dated evidence.
- Ignore incomplete mechanism ledgers. Rejected because future agents would treat missing history as missing decisions.

## Consequences

- A canonical input change requires `build_inventory.py --write` in the same pull request.
- Generated drift and reference failures have stable, domain-specific reason codes.
- The effectiveness runner is reported as `scaffold`, independently of its available task count.
- Validator ownership is explicit. Overlapping checks remain defense in depth, but the inventory owns cross-artifact completeness.
- A later schema-registry spec may replace the bootstrap sorted-key JSON profile. That migration must update the inventory schema version and regenerate the view.

## Verification

Unit tests cover byte stability, generated-output exclusion, source-digest sensitivity, duplicate identifiers, dangling relationships, ledger completeness, golden reconciliation, task structure, manifest parity, version parity, duplicate JSON keys, symlink escape, and interrupted atomic replacement.
