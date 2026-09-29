# SPEC-009: Source Registry and Feed Policy

Status: draft
Revision: 1
Revises: none
Wave: 2
Classification: split
Owners: research director agent; source steward agent
Depends on: SPEC-003, SPEC-005, SPEC-008

## Decision

Discovery, intellectual-work identity, published manifestations, and immutable source versions will be represented by separate records. Stateless connectors produce discovery leads and receipts; they do not resolve identity, advance cursors, or enqueue research directly. Reducers validate connector output and atomically record accepted leads, quarantines, explicit gaps, and the next cursor under the active work-order fencing token.

X and Hacker News are lead generators, not evidence authorities. Engagement is retained only as quarantined discovery telemetry and cannot enter methodological-quality, claim-strength, or promotion scores.

## Context and current repository touchpoints

`researcher/source-registry.md` and `researcher/discovery/manual-seed.jsonl` establish a curated starting point. The autonomous organization needs executable connector policy, stable identities across manifestations, replayable cursor transitions, and source-specific admissibility, retention, and export behavior without treating a mutable URL as a canonical source.

## Goals

- Discover current papers, code, specifications, engineering reports, and community signals.
- Deduplicate one intellectual work across URLs, versions, repositories, reposts, and summaries without collapsing materially different manifestations.
- Keep daily incremental work separate from bounded historical backfill.
- Measure why each feed and query exists, what it costs, and what downstream value it produces.
- Preserve ambiguous identity cases for review instead of forcing a lossy merge.

## Non-goals

- Treating every retrieved item as a review candidate.
- Scraping authenticated pages outside an approved connector.
- Treating popularity, author reputation, publication venue, or retrieval success as claim evidence.
- Letting connector-local state become canonical organizational state.

## Invariants

1. A `DiscoveryLead` is not evidence and does not itself identify an intellectual work.
2. `WorkIdentity`, `Manifestation`, and `SourceVersion` have distinct stable identifiers; a capture is a later SPEC-010 record.
3. Origin, admissibility, redistribution permission, and claim-specific evidence strength are independent dimensions.
4. Evidentiary independence is an explicit relation justified per claim, not a property inferred from URLs, citations, authors, or source class.
5. Connector cursors and provider request metadata are private operational state. Connector definitions, public query rationale, and safe aggregate yield reports may be public.
6. A connector call is stateless. Only a reducer may accept its output, advance its cursor, or create downstream work.
7. Feed changes, resolver changes, aliases, merges, and splits are versioned and attributable.
8. Engagement telemetry is excluded from quality and promotion inputs by schema, not only by prompt instruction.

## Interfaces and data

Create registry records under `researcher/sources/` using SPEC-003 schemas:

- `DiscoveryLead`: connector, connector version, query epoch, partition, lane, external item identifier, observed URL, discovery time, minimal display metadata, and receipt reference. Provider engagement fields, when retained at all, live in a separately classified telemetry attachment.
- `WorkIdentity`: the stable identity of an intellectual contribution, with normalized titles, contributors, dates, topics, and accepted alias decisions.
- `Manifestation`: a paper, repository, specification, report, talk, discussion, or other expression of a work. A secondary manifestation links to the primary manifestation when established but remains independently addressable.
- `SourceVersion`: one immutable version of a manifestation, with normalized DOI, arXiv, OpenReview, repository, release, or specification identifiers; publication and revision dates; predecessor links; origin category; access status; admissibility status; redistribution policy; and expected capture policy.
- `ResolutionDecision`: an immutable alias, attach, merge, split, or unresolved decision over the exact registry snapshot, with evidence, algorithm or reviewer identity, confidence, and reconsideration trigger.

Claim evidence strength and independence are recorded by SPEC-011 `EvidenceRelation` records. The registry may record whether a manifestation is primary, secondary, author-reported, independently produced, or community commentary, but those origin facts do not predetermine a claim verdict.

A connector exposes one required operation:

```text
discover(cursor, query_epoch, limits) -> LeadPage(items, next_cursor, receipt)
```

`cursor` identity includes connector ID and version, query epoch, partition, and lane. `limits` binds item, byte, page, request, and time ceilings. `LeadPage` is a proposal: the reducer atomically records accepted leads, quarantined records, declared provider gaps, and `next_cursor` using the work-order fencing token and expected stream version. A crash before that append leaves the previous cursor authoritative; replay uses the same page identity and is idempotent.

Identity resolution is a separate deterministic or reviewed operation:

```text
resolve(lead, registry_snapshot, resolver_version) -> ResolutionProposal
```

A bounded `ResolverProbe` may fetch identifier metadata needed to propose a match. Its response is provenance for the resolution decision only and cannot satisfy downstream evidence requirements. Accepting a resolution proposal is a reducer action with an immutable decision record.

Initial connector definitions cover arXiv, OpenReview, allowlisted GitHub releases and tags, official lab and standards feeds, the Hacker News official API, and manual nomination. X is defined but disabled until approved access, query policy, and cost ceilings exist.

## Modes and activation

The organizational mode lattice is `observe < shadow < proposal < production`. Mode is a ceiling on effects, never an action grant. Observation can generate receipts for inspection. Shadow output may enter only isolated private shadow reducers and indexes; it cannot reach authoritative reducers, the active queue, outbox, GitHub, or accepted decisions. Proposal mode may create review candidates only when the work order and capability grant permit that action. Production connector polling and cursor advancement require explicit grants.

Fixture and local observation work may begin after this spec's dependencies. Polling real feeds is not continuously activated until SPEC-024 supplies authenticated private capabilities and SPEC-025 supplies supervised scheduling, backlog policy, and recovery.

## State and failure behavior

Lead projection states are `observed -> validated -> unresolved|resolution_proposed -> queued|deduplicated|parked|rejected`. These are reducer projections, not connector mutations. Malformed or policy-incompatible items are quarantined with bounded safe metadata. A provider gap must be explicit and scoped; absence of a page is never interpreted as an empty page. Rate limits and transient failures preserve the confirmed cursor and emit retry timing without connector-side checkpointing.

Identity decisions are append-only. A later split or merge supersedes an earlier decision and records a migration map; it never rewrites historical lead, capture, claim, or evaluation references.

## Implementation sequence

1. Define the five record types, cursor identity, connector limits, and reducer command schemas.
2. Convert manual seeds into leads and resolution proposals without changing prior verdicts.
3. Implement arXiv, OpenReview, Hacker News, GitHub, and manual connectors against fixtures in observation and shadow modes.
4. Add deterministic normalization, reviewed ambiguous resolution, and alias/merge/split migrations.
5. Measure feed utility before enabling proposal queues; activate live schedules only after SPEC-024 and SPEC-025.

## Migration and rollback

Existing registry entries receive deterministic work, manifestation, and version identities through an import manifest. Unresolvable entries remain explicit unresolved leads. Connector rollback disables future calls and preserves receipts, cursor events, resolution history, and downstream references. Resolver rollback pins the previous resolver without undoing accepted decisions; corrections use superseding decisions.

## Observability

For each connector, query epoch, partition, and lane, report leads inspected, validation denominator, unique works, new manifestations and versions, duplicates, unresolved items, quarantines, explicit gaps, capture conversion, downstream review conversion, accepted contributions, coverage, novelty yield, unresolved yield, discovery-to-decision lag, byte/request/time/currency cost, and cursor age. Feed-retention decisions must include those denominators plus downstream value and a bounded exploration budget; raw popularity is never a retention-quality metric.

## Verification

- One paper discovered through arXiv, Hacker News, X, and GitHub can resolve to one work with distinct manifestations and immutable versions.
- Materially different artifacts are not collapsed merely because titles or authors overlap.
- Changing engagement telemetry cannot change quality, evidence, or promotion results.
- Crash and replay preserve the confirmed cursor and do not duplicate reducer effects.
- A forged, stale-fenced, or mismatched page cannot advance a cursor.
- Resolver probes cannot satisfy claim evidence requirements.
- Alias, merge, and split decisions preserve referential history.
- Disabled, rate-limited, unaffordable, and gapped connectors degrade visibly.

## Acceptance criteria

- [ ] Discovery, work identity, manifestation, version, and capture concepts are mechanically distinct.
- [ ] Initial connectors conform to the stateless interface and reducer-owned cursor protocol.
- [ ] Cross-channel identity resolution has positive, ambiguous, merge, and split fixtures.
- [ ] Daily, archive, and exploration budgets are independent and observable.
- [ ] Admissibility and redistribution policy exist for every enabled manifestation type.
- [ ] Feed retention uses denominated cost, coverage, novelty, lag, unresolved yield, and downstream-value measures.
- [ ] Social sources and engagement telemetry cannot directly satisfy a claim or promotion gate.
- [ ] Live connector activation remains gated on SPEC-024 and SPEC-025.

## Pull-request evidence

Attach schema goldens, connector conformance results, identity-resolution and split fixtures, reducer cursor replay and stale-fence tests, one explicit-gap trace, engagement non-interference test, and a denominated feed-policy report.
