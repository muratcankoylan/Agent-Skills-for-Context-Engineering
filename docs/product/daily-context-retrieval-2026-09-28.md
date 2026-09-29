# Daily context retrieval: architecture, provider decisions and evaluation plan

Date: 28 September 2026. Status: implemented local retrieval slice, not a launched
service or an accepted implementation of the complete specification program.
This document distinguishes source discovery from evidence qualification and
skill acceptance. The [operator runbook](../../researcher/service/DAILY_RETRIEVAL.md)
describes the executable configuration and limits.

## Objective and non-goals

The objective is better evidence available to research agents, not more API calls,
larger prompts, more agents, or a feed ranked by engagement. A useful daily system
must expose what it searched, what it missed, what changed, and how an observation
can be traced back to captured source bytes. A tweet about a paper and the paper
itself are related manifestations, not two independent replications.

The immediate measurable properties are bounded effects, replay identity,
preservation of content depth and truncation, topic-specific queries, visible
coverage gaps, and restart behavior. Relevance, scientific quality and downstream
skill effectiveness require separate labeled evaluations. Passing the first set
does not demonstrate the second.

No cloud resources, recurring desktop tasks, GitHub writes, self-approved skill
updates, unrestricted crawling or production schedules are activated by this work.
Source text is untrusted data. A discovered tool or article cannot change
credentials, budgets, allowed destinations, evaluation rules or publication policy.

## Decision: layered retrieval, one coordinator

Three credible approaches were considered:

| Approach | Advantage | Main limitation | Decision |
| --- | --- | --- | --- |
| One broad search/deep-research provider | Small integration surface; natural-language queries | Provider-specific coverage, costs and summaries obscure primary-source completeness | Candidate for one bounded web lane, not the sole evidence system |
| Every source as an autonomous agent | Flexible exploration | Duplicate discovery, unpredictable spend, poorly comparable traces | Reject as the default daily architecture |
| Typed source lanes, shared captures and context selection | Inspectable source contracts and costs; independent replacement and replay | Requires explicit discovery-to-evidence handoff | Implement incrementally |

```text
repo-owned daily admission + durable SQLite reservations
  -> source-specific queries / fixed observation window
  -> bounded source request -> exact response capture -> offline re-extraction
  -> discovery records + coverage + content-depth qualifiers
  -> bounded, source-diverse context digest + prior-observation comparison
  -> private report / read-only operator status

next, separately gated:
  selected leads -> primary-content acquisition -> evidence qualification
  -> research agent -> falsifiable experiment -> independent evaluation
  -> frozen skill candidate -> repository validators -> human-reviewed PR
```

Scheduling remains in the repo-native service, not Codex. One foreground
coordinator owns scheduling and external effects; SQLite and captures live on a
private persistent local disk. The initial cloud topology remains a single Linux
host with private operator access, as described in the
[deployment contract](../../researcher/service/DEPLOYMENT.md). This change does
not select a cloud account or turn the deployment templates into a running service.

## Implemented contracts

- `retrieve` schedules are explicit and daily. Existing `research` schedules keep
  their previous behavior. Retrieval returns before model, MCP or GitHub effects.
- The requested observation window is the previous completed UTC day. Source
  coverage records state whether that window was actually applied and at what
  precision. Missing days coalesce; this is not a complete historical backfill.
- Each source has its own query, one request/page ceiling, response-size limit,
  no-redirect policy, and retained capture. Paid lanes require configured
  credential-variable names and operator-verified positive cost reservations.
- Capture replay is checked before digest construction and cached reuse. An unknown
  external outcome retains its reservation; it is not retried automatically.
- The digest retains observation identities and omission reasons even when text
  does not fit. It selects exact UTF-8 excerpts, with original and excerpt hashes,
  offsets, declared content format and both upstream and selection truncation.
- Provider-reported publication times are retained as observations, not proof of
  freshness. Company feeds and arXiv explicitly report unapplied time filters.
- Source round-robin prevents one high-volume lane from filling every slot.
  Within a lane, lexical overlap, declared format and observed novelty order
  records. This is a transparent baseline, not a semantic quality model.
- DOI/arXiv/outbound-link relationships retain distinct source manifestations.
  Seven earlier completed windows bound reobservation history. No independent
  corroboration, trend significance or universal novelty is asserted.
- The managed context compiler preserves known evidence qualifiers and rejects
  contradictory metadata. This is context-transfer support, not automatic
  dispatch of daily digests into managed sessions.
- The operator UI recognizes `retrieval_complete` without labeling it accepted
  research or production readiness. Full digest inspection remains CLI-based.

## Provider assessment

These are documented capabilities and engineering judgments, not measured provider
rankings. Access, terms and pricing must be checked for the actual account before
activation. Do not buy or enable all candidates by default.

| System | Role and evidence | Our decision / important boundary |
| --- | --- | --- |
| OpenAlex | Scholarly keyword discovery, identifiers and abstract records. [Search](https://help.openalex.org/api/searching/), [filtering](https://help.openalex.org/api/filtering/), [full text](https://help.openalex.org/access/fulltext/) | Implemented keyword/publication-day adapter. Publication date is not ingestion/update time; no claim of complete daily synchronization. Full-text acquisition is not enabled. |
| arXiv | Direct primary-paper discovery and versioned identifiers | Existing adapter now sorted by submission date in this lane. Abstracts only; requested date window is not applied. Keep for discovery, add tested overlap/backfill and selected paper acquisition separately. |
| X | Recent post search, query operators, cursor pagination, conversation IDs and public metrics. [Recent search](https://docs.x.com/x-api/posts/search/quickstart/recent-search), [pagination](https://docs.x.com/x-api/posts/search/integrate/paginate) | Implemented explicit-window enrichment. One page is not complete coverage; engagement is not scientific quality. No automatic thread or linked-page fetch. Account entitlement and billing need a live canary. |
| Hacker News | Time-filtered story discovery through [Algolia's API](https://hn.algolia.com/api) | Implemented query-specific story search. Discussion is a lead, not evidence for linked-paper claims; linked article bodies are not fetched. |
| Parallel | Objective-oriented web discovery and focused URL extraction. [Search](https://docs.parallel.ai/search/search-quickstart), [Extract](https://docs.parallel.ai/extract/extract-quickstart) | Leading candidate for the next paired web-provider experiment. Documentation lookup worked in development; the daily service is not integrated with Parallel. Deep research should be a separately budgeted escalation for unresolved questions. |
| Firecrawl / Alexandria | Search can combine web results with specialized tools; tool records describe capabilities, contracts and prices. [Alexandria documentation](https://docs.firecrawl.dev/features/alexandria) | Candidate for reviewed specialized retrieval and extraction. Discovering a tool does not authorize it. Execution can require separate third-party terms; no automatic terms acceptance or ambient MCP installation. |
| Exa | Search filters and content retrieval, including configurable freshness/cache behavior. [Search](https://exa.ai/docs/reference/search), [contents](https://exa.ai/docs/contents/quickstart), [snapshot](https://exa.ai/docs/search/snapshot) | Alternative broad-web lane. Its content snapshot feature is not a replay of historical ranking signals; retain our own captures for reproducibility. |
| Brave | Search and source-linked context chunks with explicit output controls. [Web search](https://api-dashboard.search.brave.com/app/documentation/web-search), [LLM context](https://api-dashboard.search.brave.com/documentation/services/llm-context) | Independent-index candidate for coverage diversity. Test provenance and primary-source yield; publication/update freshness fields do not establish original publication priority. |
| Tavily | Search/extraction with explicit depth and date controls. [Search contract](https://docs.tavily.com/documentation/api-reference/endpoint/search) | Optional challenger. Pin automatic parameters off in comparisons; undated-result handling and inferred dates need explicit evaluation. |
| Jina Reader | URL/PDF-to-text extraction and cache/browser controls. [Reader](https://jina.ai/reader/) | Candidate fallback extractor. A readable text response is not proof of complete figures, tables or methods. Hosted access and model-weight licenses are separate questions. |
| Semantic Scholar | Paper graph, citations, recommendations and datasets. [API](https://webflow.semanticscholar.org/product/api), [current API license](https://api.semanticscholar.org/license/) | Useful citation-expansion candidate. Verify the issued account's agreement for the intended commercial/public deployment before activation; do not assume product marketing and API terms are interchangeable. |

Default recommendation: OpenAlex plus arXiv for paper identities, X/HN for leads,
official company feeds for primary announcements, and **one measured broad-web
provider**. Add a fallback only when traces demonstrate distinct missed coverage
or extraction failures. This avoids paying multiple providers to repeat the same
announcement without improving evidence.

## Query and context policy

Keep topic families explicit in reviewed configuration rather than maintaining a
global keyword relevance blacklist. For example, memory provenance, retrieval
evaluation, tool reliability and skill learning can be separate daily schedules,
with short provider-specific queries. X expressions and paper search syntax are
not interchangeable. Feed queries are empty because those lanes observe feeds,
not search results.

The next evidence-acquisition layer must follow an allowed primary URL under its
own request/cost limit, preserve paper version/DOI and extraction method, and
retain relevant methods, limitations and negative results. It must not silently
convert a search snippet, social thread or model-written summary into full-paper
evidence. References to author reports must remain attributed reports.

Trend detection should operate on canonical works and mechanism claims, not raw
post counts. A later evaluation must separate new primary work, reposts, author
promotion, discussion and independent replication. The implemented observation
counters are deliberately insufficient to make those judgments.

## Evaluation protocol before choosing more providers

The largest unresolved question is whether another provider produces more usable
primary evidence per unit cost and context, rather than more overlapping URLs.
Use a paired, captured query experiment before adding embeddings, rerankers or
additional research agents.

1. Freeze task families and query intent before seeing provider results. Include
   recent papers, older foundational work, obscure negative results, company
   technical reports, social leads, no-answer cases and adversarial pages.
2. Separate pilot queries from a held-out test set. Issue paired queries within
   the same observation window, randomize provider order and record exact
   parameters, response bytes, timestamps, costs and failure states.
3. Pool and deduplicate works for blinded human relevance/evidence-depth labels.
   Record annotator disagreement. Pooled relevance does not estimate universal
   web recall; report only recall against the explicitly constructed judged pool.
4. Measure primary-source precision, judged relevant works per query, accessible
   evidence-depth yield, unique relevant works beyond baseline, duplicate ratio,
   date coverage, extraction fidelity, cost per usable work and latency.
5. Measure context utility at equal byte/token budgets and fixed model settings.
   Use held-out factual/mechanism questions with attributable supporting spans,
   abstention cases, contradictions and source-instruction attacks. Deterministic
   quote checks precede calibrated semantic judges; quote identity is not truth.
6. Ablate source round-robin, novelty preference, extraction fallback and optional
   semantic reranking. Cluster confidence intervals by query/task, not by result
   URL. Determine sample size from pilot variance and a predeclared minimum useful
   effect; do not choose the stopping rule after seeing significance.
7. Keep acquisition-quality and downstream skill-effectiveness claims separate.
   Skill proposals require frozen candidates, independent evaluations and the
   repository's multi-surface validators before any acceptance decision.

No provider quality win or improved research accuracy is claimed by this change.
The older total experiment budget is not an instruction to spend it all; new
paid campaigns require explicit per-provider ceilings within the shared budget.

## Local verification record

Completed 28 September Toronto / 29 September 2026 UTC. These are operational
checks against the dirty local integration checkout, not a signed clean release,
an accepted benchmark result or proof of scientific quality.

- Service suite: 392 tests passed. Relevant connector/discovery/article suites:
  175 tests passed, including some service-adapter tests already counted above.
  Do not sum these into a unique-test total.
- Control Center: 51 tests passed; TypeScript typecheck passed. The React-guided
  UI change stays server-rendered and read-only, with explicit retrieval versus
  research-acceptance language. No visual browser acceptance test was performed.
- Changed Python modules/tests: Ruff passed. Strict repository validation and
  platform compatibility with the reference validator passed. The first platform
  invocation could not locate the already-installed CLI; using the venv PATH
  resolved that environment issue without installing dependencies.
- The 30-logical-day offline simulation completed 30 jobs, 28 populated days,
  one empty day and one rate-limited day. Six content revisions were observed.
  Restart after a retained effect added a verification but no source request.
  History stayed within seven earlier windows. All model/network/MCP/GitHub
  calls were forbidden; reservations were synthetic, not spend.

The live canary used the real coordinator, store, capture and replay code with
`fixture=false`, no credentials and no model routes. One HN schedule, one arXiv
schedule, one Hugging Face schedule and one combined HN/feed schedule yielded
four completed jobs from only three HTTP requests. The combined job reused the
same-window source captures.

| Source | Response | Captured bytes | Observations | Actual depth |
| --- | --- | --- | --- | --- |
| arXiv | HTTP 200 | 26,717 | 10 | Abstracts |
| HN Algolia | HTTP 200 | 9,498 | 10 | Nine titles and one story body |
| Hugging Face | HTTP 200 | 256,576 | 6 | Titles only |

All five lane references replayed with sockets disabled. Four digests rebuilt
byte-identically, from 8,062 to 27,321 canonical JSON bytes, with no omitted
observations in this small canary. Repeated tick/drain/restart produced no new
work, requests or usage. Counters remained three source reservations, zero model
calls and zero reserved monetary cost. No scheduler process or notification ran.
X and OpenAlex were not live-tested.

The requested window was 28 September 00:00 to 29 September 00:00 UTC. Only HN
applied that time filter; every lane reported partial coverage. The initial
canary driver's reuse of an earlier timestamp triggered `CLOCK_MOVED_BACKWARDS`;
receipt finalization used current time offline and made no additional requests.

**Important result:** 15 of 26 source observations were title-only. Successful
transport is not sufficient context for research. This supports prioritizing
selected primary-content acquisition and extraction-fidelity evaluation next,
not simply adding more discovery providers. It is a single bounded observation,
not an estimate of provider quality across topics or time.

Private source artifacts include `summary.json` and `results.json` in the
operator's private September 28 canary directory, with the bounded driver,
offline verifier and captured state. The local locator is not a public artifact.
The retained full-results SHA-256 is
`8767d7164768a416d62e06e87077a56771e31b46c19d49d07d703d240d3de1f1`.
Temporary artifact retention is not the production archive/backup policy.

## Next implementation gates

1. Credentialed X/OpenAlex entitlement and response-contract canaries, with no
   model or GitHub effects. Verify total-request price bounds, not just per-result
   rates, and preserve redacted receipts.
2. One Parallel/Exa/Brave paired pilot, then primary-content extraction with
   measured fidelity and source rights. Register Alexandria capabilities only
   after reviewing their exact provider contract and terms.
3. Pagination completeness and overlapping requery/backfill policies. Late-indexed
   papers and sources with unapplied windows are current coverage limitations.
4. Cross-source work resolution, evidence qualification and assessed claim-level
   novelty. Current URL/DOI/arXiv keys are conservative partial identity handling.
5. Explicit verified digest-to-managed-session handoff, separate independent
   evaluation, bounded archive search and candidate-overlay validators.
6. Cloud release/state migration, egress containment, retention/deletion policy,
   credential rotation, alerting and multi-day live canaries before unattended
   operation. Current failures outside captured rate limits stop the job; other
   lanes are not guaranteed to continue after a failing source.

All of these remain visible launch gates, not implied completed capabilities.

## Research artifacts

Documentation was checked through official provider pages and Parallel search /
extraction. Local development outputs are
`/tmp/daily-retrieval-provider-docs-20260928.json` and
`/tmp/daily-retrieval-api-contracts-20260928.json`; they are not repository release
artifacts. One search and a three-URL extraction were used for documentation
research, not a retrieval-quality benchmark or paid model campaign.
