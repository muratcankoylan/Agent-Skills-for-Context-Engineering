# SPEC-009: Source Registry and Feed Policy

Status: draft
Wave: 2
Classification: public
Owners: research director agent; source steward agent
Depends on: SPEC-003

## Decision

All discovery channels will resolve into a canonical source registry before retrieval or scoring. The registry distinguishes source identity, source version, discovery lead, feed cursor, evidence tier, redistribution terms, and operational cost. X and Hacker News are lead generators, not evidence authorities. Popularity is never part of methodological quality.

## Context and current repository touchpoints

`researcher/source-registry.md` and `researcher/discovery/manual-seed.jsonl` establish a useful curated starting point. The autonomous organization needs executable connector policy, cursor state, canonical identifiers, version detection, and source-specific retention and export behavior.

## Goals

- Discover current papers, code, specifications, engineering reports, and community signals.
- Deduplicate the same work across URLs, versions, reposts, and secondary summaries.
- Keep daily incremental work separate from historical backfill.
- Record why each feed and query exists, its cost, and its observed yield.

## Non-goals

- Treating every retrieved item as a review candidate.
- Scraping authenticated pages outside an approved connector.
- Using engagement counts as evidence strength.

## Invariants

1. Every source has a stable `source_id`; every capture has a distinct version ID.
2. Discovery channel and evidence authority are separate fields.
3. A secondary discussion links to the primary artifact when resolvable.
4. Connector cursors are private operational state; connector definitions and query rationale are public.
5. Terms, redistribution status, and raw-content retention are evaluated per source class.
6. Feed changes are versioned and their effect on yield is measurable.

## Interfaces and data

Create `researcher/sources/registry.yaml` and connector definitions under `researcher/sources/connectors/`. A source records canonical URL, normalized DOI/arXiv/OpenReview/repository/spec identifiers, title, authors, class, dates, discovered-via links, topics, redistribution policy, and versions.

A connector exposes:

```text
discover(cursor, query_version, budget) -> LeadPage
resolve(lead) -> SourceIdentity | UnresolvedLead
checkpoint() -> CursorReceipt
health() -> ConnectorHealth
```

Initial connectors:

- arXiv categories and targeted queries;
- OpenReview API for selected venues;
- GitHub releases and repository tags for an allowlisted watch set;
- official lab, standards, and framework feeds;
- Hacker News official API for incremental items and bounded archive backfill;
- X official recent or archive search, enabled only when access and budget exist;
- manual GitHub issue or registry nomination.

Source classes are A primary/independently reproduced, B detailed preprint or official technical report, C credible production or author report, D community lead or summary, and E unverifiable or unretrieved. Class limits downstream use but does not predetermine relevance.

## State and failure behavior

Leads move `discovered -> normalized -> resolved|unresolved -> queued|deduplicated|parked|rejected`. Connector failure preserves the last confirmed cursor. A malformed item is quarantined without advancing beyond it unless the connector records a gap. Rate limits reschedule with provider reset metadata.

## Implementation sequence

1. Convert the manual registry into schema-valid records without changing verdicts.
2. Implement arXiv, OpenReview, HN, GitHub, and manual connectors in observation mode.
3. Add canonical resolution and cross-channel deduplication.
4. Measure yield and then enable daily queues.
5. Add X only with approved access, query policy, and cost ceiling.

## Migration and rollback

Existing manual seeds retain provenance and receive deterministic IDs. Connector activation uses per-source feature gates. Rollback disables a connector and keeps its leads, cursor receipts, and yield history.

## Observability

Track leads, resolved primary artifacts, duplicates, unresolved links, retrieval conversion, later acceptance, cost, rate limits, cursor age, and topic coverage by connector and query version.

## Verification

- The same paper discovered through arXiv, HN, X, and GitHub resolves to one source graph.
- HN or X engagement changes do not change evidence tier.
- Restart resumes from the confirmed cursor without duplicate effects.
- Revised arXiv and OpenReview records create versions, not overwrites.
- Disabled or unaffordable connectors degrade cleanly.

## Acceptance criteria

- [ ] Initial connectors conform to one interface and use recorded cursors.
- [ ] Cross-channel identity resolution has reviewed fixtures.
- [ ] Daily and archive budgets are independent.
- [ ] Redistribution policy exists for every enabled source class.
- [ ] Yield metrics can justify retaining or removing a feed.
- [ ] Social sources cannot directly enter a skill or claim as primary evidence.

## Pull-request evidence

Attach connector conformance results, identity-resolution fixtures, one restart trace, yield baseline, and a source-policy table.
