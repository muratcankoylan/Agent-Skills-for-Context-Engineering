# Daily discovery context: operator runbook

Status: local implementation, 28 September 2026. No recurring run is installed or
enabled by this document. The [architecture and provider assessment](../../docs/product/daily-context-retrieval-2026-09-28.md)
records the rationale and remaining evaluation gates.

Setup update, 29 September UTC: the CLI now has explicit `--env-file`, no-network
`preflight`, and atomic no-overwrite `configure` commands. See the
[credential and purchasing guide](../../docs/product/provider-credentials.md).
The default `.env.example` profile selects only free sources and has zero spend.
The September 29 [connector verification and quality plan](../../docs/product/connector-verification-2026-09-29.md)
records scoped live API and MCP checks. The
[production exercise](../../docs/product/production-exercise-2026-09-29.md)
records primary-reading scenarios and the funded pipeline.
The [integration verification record](../../docs/product/research-integration-verification-2026-09-29.md)
separately records source-failure isolation and replay-to-managed preparation;
these changes do not enable recurring model execution.

## Minimal execution contract

Use [`config.retrieval.example.json`](config.retrieval.example.json) for a new,
isolated free-source canary. It has no models, zero model/spend budgets, no MCP
registrations and GitHub disabled. Do not use this isolated development example
to reset an existing production or paid-experiment budget.

The example runs HN story search and three company feeds. It does not exercise X,
OpenAlex, paid web search or full-paper acquisition. An `init` command creates
state; it does not begin recurring execution. From the repository root:

```sh
.venv/bin/python -m researcher.service init --config researcher/service/config.retrieval.example.json --state /absolute/private/retrieval-canary --repo /absolute/repository
.venv/bin/python -m researcher.service enqueue --config researcher/service/config.retrieval.example.json --state /absolute/private/retrieval-canary --repo /absolute/repository --schedule daily-context-observations --job-id retrieval-canary-001
.venv/bin/python -m researcher.service work --config researcher/service/config.retrieval.example.json --state /absolute/private/retrieval-canary --repo /absolute/repository --live
.venv/bin/python -m researcher.service inspect --config researcher/service/config.retrieval.example.json --state /absolute/private/retrieval-canary --repo /absolute/repository --job-id retrieval-canary-001
```

These are foreground one-shot commands, not a service activation instruction.
The state directory must be private, outside the public checkout and not a symlink.
Keep configuration unchanged once bound to state. The release's approved
configuration/state migration remains a separate deployment requirement.

For a reviewed deployed configuration, the existing `serve ... --live` coordinator
owns daily admission; do not add a second cron, desktop automation or scheduler.
Retrieval admits the prior completed UTC day after a short provider-end-time grace
period. Source windows are fixed in the manifest. Restarted ticks do not generate
another job for the same schedule/slot. Missed days are coalesced, not backfilled.

## Adding credentialed lanes

Only `x` and `openalex` have new credentialed native adapters. Put credential
**variable names**, never values, in JSON:

```json
{
  "source_credentials": {
    "x": "X_BEARER_TOKEN",
    "openalex": "OPENALEX_API_KEY"
  }
}
```

This is a configuration fragment, not a complete runnable configuration. Also:

1. Add each intended source to the schedule's `sources` and give it an explicit
   `source_queries` entry. Paper queries should be short topical phrases. X uses
   X query syntax. Do not pass one long research prompt to every provider.
2. Set `source_cost_microusd` for each paid-capable lane to a positive, independently
   verified **total maximum cost per request**. Include the full requested result
   count and account billing rules. No vendor price is hardcoded.
3. Increase `run_budget_microusd` and `daily_budget_microusd` deliberately within
   the shared authorized budget. Provider free credits do not remove the need for
   a worst-case reservation. One dollar is 1,000,000 micro-US dollars.
4. Inject only the selected environment variables through the deployment's private
   secret mechanism, or explicitly pass `--env-file /absolute/private/service.env`.
   There is no automatic dotenv discovery. With the flag, selected credentials
   come only from that private file, with no ambient fallback or shell evaluation.
   Credentials are not passed to replay, the digest or browser code.
5. Run one bounded live canary before enabling the daily configuration. A missing
   credential, entitlement error or undocumented response is a failed canary,
   not evidence that the connector works.

Parallel Search/Extract and Firecrawl account access have native one-shot
diagnostics, but no daily adapters in this configuration. Exa, Brave, Tavily,
Jina and Semantic Scholar remain researched alternatives. Their keys
alone do not activate them. Do not add an unreviewed tool through ambient MCP
discovery or bypass required provider terms.

## Optional primary HTML reading

Set `primary_read_limit` to 1 or 2 on a retrieval schedule, or set
`RESEARCH_PRIMARY_READ_LIMIT` before generating a new configuration. Default 0
means no primary reads. Budget source requests for the selected discovery lanes
plus the primary-read limit. The setup validator checks this cold-cache bound.
Existing state is config-bound and requires migration, not in-place changes.

The selector starts with query-matching observations in the replayed discovery
digest. By default it allows at most one URL per host, preserves arXiv versions when mapping
`/abs/` to `/html/`, and delegates final validation to the existing restricted
arXiv/company HTML reader. Unsupported sources and links remain explicit selection
omissions. DOI resolution, arbitrary outbound links, PDF/OCR, provider extraction
APIs and recursive crawling are not enabled here.

For a new reviewed configuration, opt into
`primary_selection_profile: "host-diversity-fill-v1"` to prefer different hosts,
then fill otherwise unused slots with distinct eligible same-host URLs, still
bounded by `primary_read_limit` (maximum two). Example schedule additions:

```json
{
  "primary_read_limit": 2,
  "primary_read_profile": "large-paper-html-v1",
  "primary_selection_profile": "host-diversity-fill-v1"
}
```

Selection is fixed before requests. A failed first URL does not change the selected
second URL or authorize a third request. Checkpoints, effect/cache policy, report
and offline replay bind the selected profile. Historical default receipts are not
silently reinterpreted. The env setup helper does not select this new profile;
review these fields in a new JSON configuration before initializing source state.

Each selected request has a prior effect reservation, a 15-second/500,000-byte
default transport bound, private capture and mandatory offline replay. An
explicit schedule `primary_read_profile: "large-paper-html-v1"` with a positive
`primary_read_limit` raises only the wire cap to 1.5 MB; retained normalized text
remains bounded to 100 KB. Its versioned policy binds both the unchanged base
reader and the larger-profile module. Historical default outcomes remain v1;
profile outcomes are v2, with no automatic fallback or retry. arXiv may wait
once for three seconds before discovery or a primary request to respect shared request
spacing. This is a local admission wait, not an HTTP retry. Continued contention
becomes a visible gap. A process crash with unknown outcome requires reconciliation;
restart never repeats the HTTP request. Known unsuccessful captures remain gaps.

`primary_context` is separate from the discovery digest and capped at 32 KiB.
Cards retain discovery/capture bindings, parser identity, exact normalized-text
spans, extraction omissions and at most two excerpts per document. Empty mechanism,
method, claim and limitation assessments are explicitly `unresolved`, not invented
scientific conclusions. `project_primary_evidence()` projects replayed cards into
the existing agent compiler's evidence contract, preserving primary-HTML scope and
truncation while excluding private capture metadata. It performs no model call.

Primary HTML is not automatically complete paper evidence. No quality qualification,
agent dispatch, skill acceptance, notification or publication follows from a card.

## Current limits and source semantics

| Boundary | Current behavior |
| --- | --- |
| Transport | One request/page per source, 500,000 response bytes, 30-second request budget, no redirects |
| Results | At most six items per company feed; ten per HN, X, OpenAlex or arXiv lane |
| Schedule | At most seven lanes and ten configured schedules; per-run/daily request reservations still apply |
| Context | Entire canonical digest at most 32,768 bytes; at most 20 selected observations; at most 4,096 bytes per selected excerpt |
| Primary HTML | Optional 0–2 reads; default one/host or explicit diversity-fill profile; 500,000 wire bytes by default or explicit 1.5 MB profile; 15 seconds/read, 100,000 retained text bytes, separate 32 KiB card packet |
| History | At most seven earlier completed windows of the same schedule and fixture class within the bound state store |
| Pagination | Continuation preserved for audit; never represented as complete coverage or an advanced watermark |
| X / HN | Explicit second-resolution window; posts/stories are social signals, not linked article bodies |
| OpenAlex | Publication-date window at day resolution, reconstructed abstracts; not an ingestion/update change feed |
| arXiv / company feeds | Bounded recent observations; requested date window is explicitly marked unapplied |

The digest byte/item caps are currently fixed by the retrieval workflow, not the
model-context setting. An oversized mandatory observation/omission index fails
explicitly rather than disappearing. Different topic schedules share the same
budget/state store; do not create parallel stores to multiply an account's limit.

Cost accounting is conservative reservation accounting, not an invoice or a
provider-enforced spending cap. Check provider usage separately. Known captured
rate limits yield an explicit gap. Bounded expected source-effect failures are
retained in `source_failures`, and the workflow continues other available lanes.
Unknown/blocked outcomes retain their reconciliation boundary; they are not
silently retried on restart. Configuration, credential, capture-integrity and
unexpected implementation errors still fail closed. Do not enqueue a new job or
delete state to force an uncertain request to run again.

## Reading results

`status` and `/service` expose `retrieval_complete` or `reconciliation_required`.
A completed report can include definitive source failures and primary-read gaps;
it is not a completed search or qualified finding. `collection_completed` means
the configured collection pass finished, not that every source succeeded.
`inspect --job-id ...` includes effect and
checkpoint records, including `research-retrieval-report/v1` and its
`research-context-digest/v1` packet. Review:

- `coverage`: state, applied window/resolution, bounded-page and rate-limit gaps.
- `source_failures` and `reconciliation_required`: retained failed/unknown/blocked
  source outcomes and whether operator resolution is still required.
- `items[].qualifiers`: summary format, provider truncation, selection truncation,
  exact byte span and provider-reported publication time when available.
- `observations` and `omissions`: what was seen and why text was not selected.
- `signals`: reobserved text versions/work keys in sampled history, not scientific
  trend significance or independent corroboration.
- `primary_context`: selected primary evidence cards, exact excerpts, unresolved
  assessment fields, unsupported targets and failed-read gaps.
- Usage/effects: source reservations, zero model calls for this mode, unresolved
  effects and retained report identity.

Do not infer source credibility from declared content format or a lexical score.
Inspect primary sources before making methods/results claims. Reports remain
private; no automatic notification or PR is sent.

## Verified handoff to SDK research

[`retrieval_handoff.py`](retrieval_handoff.py) can replay an eligible completed job
and prepare a frozen packet with no new source/model calls. The active path is
the [SDK research pipeline](RESEARCH_PIPELINE.md), dispatched manually or by
[Organization](ORGANIZATION.md) against the existing cumulative authority. Every
discovery lane must be observed, with no failed/unknown effects or source-failure
entries, and at least one replayed primary card is required. A rate-limited lane
or zero successful primary cards is rejected. Source windows must be within the
configured age bound (two days by default, seven days maximum); dispatch rechecks it.

The packet retains source depth, coverage, omitted-selection counts and links
between discovery observations and exact primary excerpts. It does not certify
source quality or imply full-paper reading. Fixture packets cannot authorize live work.
Preparation only prevents reuse of its own destination directory, not duplication
across service jobs or new directories. Organization's durable job admission and
the pipeline's separately verified same-evaluation candidate suppression provide
the current duplicate controls. Primary-content qualification, scientific
acceptance and publication are not conferred by preparation.

The [managed prepare/inspect interface](AGENTS_API.md#prepare-and-inspect) remains
historical compatibility. New default managed submissions are retired; it is not
the deployment recipe for the current SDK coordinator.

## Verification commands

```sh
.venv/bin/python -m unittest researcher.service.tests.test_daily_retrieval researcher.service.tests.test_context_digest researcher.service.tests.test_retrieval_sources researcher.scripts.tests.test_source_search -q
.venv/bin/python -m unittest researcher.service.tests.test_retrieval_handoff -q
.venv/bin/python -m unittest discover -s researcher/service/tests -p 'test_*.py' -q
```

The daily test suite includes a 30-logical-day fixture simulation using real store,
admission, reservation and history logic. It tests restart/idempotency and gaps,
not a month of real research or evidence-quality improvement. Paid-provider and
retrieval-quality benchmarks require the separate frozen evaluation protocol.
