# Connector verification, 2026-09-29

## Outcome and scope

The five configured non-OpenAI providers passed actual read operations. The
repo-native generic MCP bridge also completed a registered Parallel fetch after
a reproduced protocol-envelope bug was fixed. This is a bounded integration
canary, not a retrieval-quality benchmark, deployment approval, month-long soak,
or claim that every provider feature is supported.

OpenAI live execution belongs to the separate cumulative-budget campaign and is
not included here. No model calls, GitHub writes, PR creation, account changes,
deep-research tasks, automatic retries, or recurring activation occurred in this
connector pass. Provider credentials never appeared in command arguments,
reports, or error output. Provider content was treated as untrusted data.

## Configuration inventory

The private local environment was inspected using the literal safe loader. This
inventory records presence, not values or key fingerprints:

| Credential | Presence | What is integrated or tested |
| --- | --- | --- |
| `OPENAI_API_KEY` | Configured | Separate OpenAI owner/campaign, not called here |
| `X_BEARER_TOKEN` | Configured | Production recent-search adapter, one page |
| `OPENALEX_API_KEY` | Configured | Authenticated quota endpoint and production works search |
| `PARALLEL_API_KEY` | Configured | GA Search/Extract; authenticated MCP fetch |
| `FIRECRAWL_API_KEY` | Configured | Credits, Research Index search, one-page scrape |
| `RESEARCH_GITHUB_TOKEN` | Configured | Authenticated identity and target repository read |
| `X_CONSUMER_KEY`, `X_SECRET_KEY` | Configured | Not consumed by the app-only read adapter; not independently tested |
| `EXA_API_KEY`, `SEMANTIC_SCHOLAR_API_KEY` | Empty | Not tested |
| Brave, Tavily, Jina, Anthropic, Gemini keys | Absent | Not tested |
| `RESEARCH_OPERATOR_TOKEN` | Empty | Operator API authentication remains a deployment setup requirement |

No configured value matched the template-placeholder forms checked during this
inventory. `RESEARCH_X_MAX_REQUEST_USD` and
`RESEARCH_OPENALEX_MAX_REQUEST_USD` were empty: the canary uses its own fixed,
reviewed reservations. A successful canary does not populate deployment budgets.

Initially, the service config templates contained no MCP registrations or reads,
and no active external service-config path was supplied. Codex's own tool
catalog is not evidence that the repository service has an MCP integration.

## Live observations

| Operation | Observed result | Limitation |
| --- | --- | --- |
| X recent search | 10 posts; all 10 had timestamps, authors, conversation IDs, language and public metrics; 7 had entities; 5 had extended `note_tweet` text | One query/day window; not trend-quality or recall evaluation |
| OpenAlex works | 10 works, 9 reconstructed abstracts | Metadata/abstract discovery, not primary full text |
| OpenAlex authenticated quota | Valid quota response, available budget | Separate from works: a public works response alone would not verify key recognition |
| Parallel GA Search | 1 result | One fast-mode query, not comparative search quality |
| Parallel GA Extract | 1 result for the exact requested IANA URL, zero errors | Excerpts, not verified complete source content |
| Firecrawl credits | Successful typed response, credits available | No balance or billing identity retained |
| Firecrawl Research Index | 1 identified paper and abstract | Discovery only; not full-paper ingestion |
| Firecrawl scrape | 1 exact-source page, HTTP 200 in metadata, 2,372 UTF-8 markdown bytes | One basic markdown scrape, no browser actions or LLM extraction |
| GitHub identity | Authenticated identity response | Does not establish PR/write permission |
| GitHub repository | Exact target repository accessible | Read-only; no write test |
| Fixed Parallel MCP diagnostic | Initialize, list 2 tools, fetch once; 4 POSTs; 2,029 content bytes; valid structured output | Provider-specific diagnostic, not initially the generic service bridge |
| Generic registered Parallel MCP bridge | Actual isolated SDK worker returned 1 result, zero extraction errors, 1,935 canonical structured bytes | One operator-selected fetch, not unrestricted or daily autonomous MCP use |

X and OpenAlex were exercised through `retrieval_sources.collect` and their
private captures were verified through offline replay, not just account endpoints.
The fixed direct-HTTP probes validate bounded response contracts and persist only
aggregate results. Their extracted content is not silently inserted into the
research corpus.

## The failure found and fixed

The first generic SDK attempt was rejected, but its diagnostic collapsed the
safe error code. A distinct, explicitly admitted observation pass preserved the
typed reason: `INVALID_RECORD`, after the tool response had been received.
Both system and SDK trust stores verified credential-free TLS handshakes, so no
TLS-policy change was justified or made.

A real-SDK offline regression reproduced `INVALID_RECORD` when a valid MCP
response contained floating-point envelope metadata or a content annotation
priority. The bridge had applied the repository's integer-only canonical record
profile to the whole SDK response, including non-evidence protocol metadata.

The fix:

- Bounds the entire SDK-serialized JSON envelope, including ignored content.
- Preserves its byte count and SHA-256 digest for new receipts. This is explicitly
  an SDK serialization, **not** the original HTTP response bytes.
- Projects only the tool status and `structuredContent` into evidence validation.
- Still rejects floats in structured evidence; it does not silently remove or
  coerce source values.
- Preserves typed policy errors through AnyIO exception groups, with safe
  execution-phase fallbacks. Raw third-party exception text stays suppressed.

A final distinct live campaign using the actual isolated generic bridge passed.
The exact field responsible in the first failed response was not retained;
the reproducible failure mechanism and successful post-fix canary support this
remedy without claiming a recovered historical wire trace.

## Explicit MCP integration

The reviewed registration is
[`parallel-web-fetch.json`](../../researcher/service/registrations/parallel-web-fetch.json).
It pins the authenticated `/mcp-oauth` endpoint, `web_fetch`, protocol
`2025-11-25`, and the exact observed input/output schemas. The generic bridge
requires exact schema matching and retained all its validation gates. The
registered output cap is 32 KiB; session timeout is sixty seconds.

The registration can be used by an explicitly configured **research-mode**
schedule with `PARALLEL_API_KEY`, one selected URL, an explicit cost allowance,
and twelve reserved source HTTP requests. It does not activate itself. The
existing retrieval-only mode still intentionally rejects MCP reads. Daily
retrieval support, provider-specific provenance normalization, and broader
research-query evaluation are remaining work, not claims of this canary.
See [registration guidance](../../researcher/service/registrations/README.md).

## Budget, durable receipts and repeatability

All effects reserve capacity before dispatch and bind to the code/configuration
manifest. Each state directory is a separate, explicitly authorized experiment,
not a reset or automatic retry of an uncertain effect. Reusing a completed
unchanged manifest replays its receipt without provider calls. A changed
implementation deliberately invalidates dispatch/resume under an older manifest.

| Campaign | HTTP reservation ceiling | Conservative cost reservation | Result |
| --- | ---: | ---: | --- |
| Initial operations | 14 | $0.073 | All 11 checks passed |
| Initial generic bridge | 12 | $0.010 | Rejected; safe cause initially missing |
| Observable generic bridge | 12 | $0.010 | Rejected after response, `INVALID_RECORD` |
| Envelope-fix validation | 12 | $0.010 | Passed |
| Total | 50 | $0.103 | All reservations, including failures, retained |

The initial pass ceiling was twenty requests; the operator explicitly increased
it for each distinct generic validation, ultimately to fifty. Generic SDK HTTP
counts are ceilings, not measured usage. Two additional credential-free TLS
handshakes issued no HTTP requests. Invoice amounts and automatic account billing
behavior were not inspected; local reservations do not prove provider-side hard
spend caps. No billing settings were changed.

Private ledger directories under `researcher/runtime/`:

- `connector-operations-20260929`: manifest
  `sha256:34a6e34dcb76a41ce587a1632a84e8f8837293eb8425bab970be57a6c8614e0a`.
- `connector-registered-mcp-20260929`: manifest
  `sha256:18028af20d86103e2fbc153a6d894afce9672538911f62e34e95fb01a39bc5f1`.
- `connector-registered-mcp-observable-20260929`: manifest
  `sha256:8d56b4ed1eb7e0843b6605e3201457dad767b5a532bb7882699d58b549e04d06`.
- `connector-registered-mcp-envelope-20260929`: manifest
  `sha256:3e4543335cca305a38c7c56c75ec37784d31663f3929756e7993f607c503e525`.

The initial successful campaign and the final generic campaign both passed an
unchanged-manifest replay check with no new provider requests. Runtime state and
captures remain private and uncommitted.

## Verification and remaining gates

The final focused suite passed **127 tests** in **5.465 seconds**. It covers
connector contracts, query preservation, cost/request admission, safe credential
handling, no-retry/resume behavior, MCP protocol boundaries, exact live schema
compatibility, real SDK mock-transport round trips, isolated-worker handling,
float metadata projection and rejection of floats in structured evidence.

These results do not measure retrieval relevance, source diversity, novelty,
citation accuracy, trend detection, benchmark effectiveness, or skill-update
quality. Next engineering work should connect the validated operations to daily
retrieval with explicit source/time/rights qualifiers, capture/replay policies,
operator-visible budgets, calibrated evaluations, and cloud egress limits.

## Current official contracts used

Parallel GA Search fast mode and Extract are fixed at one result/URL in these
probes; current documented prices are $0.001 per fast search and $0.001 per
extracted URL. Task/deep-research endpoints were excluded.
[Pricing](https://docs.parallel.ai/getting-started/pricing),
[Search](https://docs.parallel.ai/api-reference/search/search),
[Extract](https://docs.parallel.ai/api-reference/extract/extract).

Parallel documents `web_fetch` and authenticated `/mcp-oauth`; the MCP transport
spec requires initialization and supports JSON or SSE responses. The fixed
diagnostic implements no automatic reconnection or server-request callbacks.
[Parallel MCP](https://docs.parallel.ai/integrations/mcp/search-mcp),
[MCP transport](https://modelcontextprotocol.io/specification/2025-11-25/basic/transports).

Firecrawl documents one credit per basic scrape and free Research Index paper
endpoints. The checked page describes pricing effective September 4, 2026.
Current scrape documentation says enhanced proxies have no surcharge, so older
five-credit proxy guidance should not be used. The canary explicitly selects
basic mode, no parsing/actions/LLM formats, and no cache insertion.
[Pricing](https://www.firecrawl.dev/pricing),
[Scrape](https://docs.firecrawl.dev/api-reference/endpoint/scrape),
[Research search](https://docs.firecrawl.dev/api-reference/endpoint/research-search-papers).

X currently documents $0.005 per returned post; this probe requests at most ten
posts and no expanded users. OpenAlex supports Bearer authentication and keyless
queries, motivating its separate authenticated quota check. GitHub's `/user`
endpoint checks authenticated identity independently from public repository read.
[X pricing](https://docs.x.com/x-api/getting-started/pricing),
[OpenAlex authentication](https://help.openalex.org/api/authentication/),
[GitHub authenticated user](https://docs.github.com/en/rest/users/users#get-the-authenticated-user).
