# Provider credentials and scholarly discovery

Updated 2026-09-29 UTC. This is setup for the repo-owned harness, not activation
of the research campaign. The [daily retrieval runbook](../../researcher/service/DAILY_RETRIEVAL.md)
defines the current executable slice. The September 10 connector preflight is
historical; neither it nor local key presence proves current endpoint access.

The private project `.env.local` contains labeled fields. The operator has filled
six provider keys, all of which passed scoped live checks on September 29. See
[the verification and research-quality report](connector-verification-2026-09-29.md)
for exactly what was tested and what remains unverified. Existing credentials
were preserved. Keep this file gitignored and mode 0600. Put keys only
there or in the deployment's secret manager, never in chat, prompts, reports,
agent workspaces, browser JavaScript, or PRs. Do not commit the filled file.

Adding a credential does not register a connector, enable a job, grant publication
authority, or prove account/endpoint access. The service CLI now accepts explicit
`--env-file .env.local`. It parses a bounded private file as literal data, passes
only the credential names needed by the selected command/configuration, never
updates `os.environ`, and never falls back to ambient values when this flag is
used. Without this flag, the original explicit process-environment path remains
available for a deployment secret mechanism. The separate managed Agents CLI is
unchanged; do not assume the new flag exists on every command-line entry point.

## What to buy now

Optional telemetry now uses `RAINDROP_WRITE_KEY` and `RAINDROP_PROJECT_ID`.
Use a newly rotated ingestion key and an existing project slug. A key pasted
into chat must not be reused. No global installer, daemon, additional model key,
or mandatory new subscription is required by the local tracing implementation.
Review the [trace runbook](../../researcher/service/TRACING.md) before any upload.
The environment file contains blank fields; configuration alone sends nothing.

The operator has now purchased access. No additional purchase is recommended.
The table below retains the original minimum-setup guidance for new installations,
not a request to buy again. These links and billing descriptions were checked against official
documentation on the date above; confirm the actual account terms before payment.

| Service | Action | Field to fill | Purchase recommendation |
| --- | --- | --- | --- |
| OpenAlex | Create a free account and copy the key from [API settings](https://openalex.org/settings/api) | `OPENALEX_API_KEY` | No payment. The documented free account includes a daily allowance without a payment method. [Pricing](https://help.openalex.org/access/pricing/) |
| Official X API | Create an app in the [developer console](https://console.x.com/); obtain its **app-only Bearer Token** | `X_BEARER_TOKEN` | Allocate **at most $10 prepaid** from the existing shared experiment budget. This is our pilot allocation, not a vendor-required minimum. Disable auto-recharge and set the account spending limit. [Pricing and controls](https://docs.x.com/x-api/getting-started/pricing) |
| Parallel | [Sign up](https://platform.parallel.ai/signup), then copy an API key from Settings | `PARALLEL_API_KEY` | Start with the account's available free credits; do not subscribe or top up yet. Usage is visible in the platform. The daily adapter is still to be implemented. [Account setup](https://docs.parallel.ai/resources/faqs) |
| Firecrawl / Alexandria | Optional [free signup](https://www.firecrawl.dev/signin?view=signup), then [API keys](https://www.firecrawl.dev/app/api-keys) | `FIRECRAWL_API_KEY` | No paid plan now. Keep it for a later extraction comparison; the free plan is sufficient to start evaluating availability, not proof of task coverage. [Pricing](https://www.firecrawl.dev/pricing) |

OpenAI model-list authentication passed the September 29 live check; model
execution and Agents sessions were not tested in that diagnostic. No additional model-provider purchase is required for
retrieval-only mode. Leave Exa, Brave, Tavily, Jina, Semantic Scholar, Anthropic
and Gemini blank unless a specific evaluated need emerges. No vector database or
archive subscription is required for this local slice.

Important cost distinctions:

- X charges reads by returned resource, not one flat search-request price. Its
  documented billing-cycle spending limit blocks requests, but a prepaid balance
  can slightly overdraw. Do not treat prepayment as a mathematically exact cap.
  [X billing](https://docs.x.com/x-api/getting-started/pricing)
- Parallel's organization/app spending limits **only notify administrators**;
  they do not block requests. A future loop must enforce its own reservations and
  execution limits before calling it. [Parallel FAQ](https://docs.parallel.ai/resources/faqs)
- On a paid Firecrawl plan, setting the PAYG monthly limit to zero disables
  automatic PAYG credit additions; it does not cancel subscription fees or manual
  purchases. Stay on free for now. [Firecrawl billing](https://www.firecrawl.dev/pricing)

These volatile provider-policy statements have provenance entries in
`researcher/claims/index.jsonl`; they are setup observations, not skill promotion.

## Fill and validate the file

The existing `.env.local` has been updated in place without replacing existing
credentials. For new clones, [`.env.example`](../../.env.example) is a secret-free
template. Never copy it over an already-filled private file. Keep `.env.local`
mode `0600`. Use literal `KEY=value` or quoted literals; no `export`, shell
commands, interpolation, backslash escapes, multiline values or inline comments.

Fill **OpenAlex, X and Parallel** first. Firecrawl is optional. Leave request-cost
fields blank and monetary limits at zero until account prices and desired sources
are reviewed. These controls are deliberately separate from credentials.

From the integration repository root, this command reads keys privately and
prints only credential names/set-or-empty status plus configuration errors:

```sh
.venv/bin/python -m researcher.service preflight --env-file .env.local
```

`local_ready: true` means the explicitly selected **free profile** is locally
configured. This offline command does not test X/OpenAlex/Parallel credentials.
The report always includes `network_checked: false`,
`source_authentication_verified: false`, and `production_ready: false`.

To include X/OpenAlex later, explicitly add `x,openalex` to
`RESEARCH_RETRIEVAL_SOURCES`, verify the provider-specific queries, and fill:

- `RESEARCH_X_MAX_REQUEST_USD` and `RESEARCH_OPENALEX_MAX_REQUEST_USD`: total
  worst-case cost of one bounded request, accounting for the result count and any
  billable expansions. These are not per-result prices and are not auto-discovered.
- `RESEARCH_RETRIEVAL_RUN_BUDGET_USD` and `RESEARCH_RETRIEVAL_DAILY_BUDGET_USD`:
  explicit decimal-dollar reservation caps, no more than the shared authorized
  experiment allocation. Provider free allowances do not remove these checks.
- `RESEARCH_RETRIEVAL_RUN_REQUESTS` and `RESEARCH_RETRIEVAL_DAILY_REQUESTS`:
  sufficient request capacity for all selected cold-cache lanes/schedules.

These are per-run/daily controls, not a cumulative campaign ledger. Do not enable
an unattended month on the assumption that they enforce the earlier total budget.

When the preflight passes, generate a **new** private config at an absolute path
under an existing operator-owned directory:

```sh
.venv/bin/python -m researcher.service configure --env-file .env.local --output /absolute/private/retrieval-config.json
.venv/bin/python -m researcher.service preflight --env-file .env.local --config /absolute/private/retrieval-config.json
```

Generation is atomic, mode `0600`, contains variable names rather than keys, and
refuses to overwrite any existing output. Neither command initializes state,
contacts providers, buys credits, starts a scheduler, opens a PR, or dispatches
models. Configurations already bound to live state require a reviewed migration;
do not create another state directory to reset paid counters.

Subsequent one-shot service `work` or `api` commands can use the same `--env-file`
option. Only a separate, explicitly authorized `work ... --live` performs source
requests. Filling keys does not schedule that command.

## What to supply

| Variable | Purpose and priority | Current integration |
| --- | --- | --- |
| `OPENAI_API_KEY` | Model backend, not needed for retrieval-only | Model-list access passed; paid model execution and Agents session access untested |
| `PARALLEL_API_KEY` | Web search, extraction, deep-research tasks and authenticated Parallel MCP | Native Search/Extract diagnostics passed; daily adapter and Task/MCP canaries still pending |
| `X_BEARER_TOKEN` | Official X public-data research | Daily adapter passed authenticated search and capture replay; enriched fields present in the tested sample |
| `OPENALEX_API_KEY` | Scholarly search | Authenticated quota check plus daily publication-date/abstract adapter and replay passed |
| `FIRECRAWL_API_KEY` | Extraction comparison; also Alexandria | Account/credit check passed; scraping and daily integration not yet validated |
| `EXA_API_KEY`, `BRAVE_API_KEY`, `TAVILY_API_KEY`, `JINA_API_KEY` | Alternatives only; leave blank | No daily adapters; do not buy these now |
| `RESEARCH_GITHUB_TOKEN` | Repository-scoped staging draft-PR delivery | Repository read passed; publication remains disabled and write scope untested |
| `SEMANTIC_SCHOLAR_API_KEY` | Recommended optional scholarly fallback and citation graph | Proposed new adapter |
| `RESEARCH_CONTACT_EMAIL` | Optional non-secret contact identity for scholarly APIs | Proposed mapping to request identity, not a token |
| `ANTHROPIC_API_KEY` | Optional cross-provider evaluation only | Native adapter exists; not required for the OpenAI-only campaign |
| `GEMINI_API_KEY` | Optional cross-provider evaluation only | Native adapter exists; not required for the OpenAI-only campaign |
| `RESEARCH_OPERATOR_TOKEN` | Leave blank now; generate a random service secret during setup | Existing server-side operator authentication; not a provider credential |

Planned provider variables are not claims that those integrations are implemented.
The current setup profile generates retrieval-only configuration and never enables
models, MCP, GitHub publication or notifications.

`RESEARCH_PRIMARY_READ_LIMIT=0` is the new optional primary-HTML stage. Set it to
1 or 2 only in an explicitly reviewed retrieval configuration; leave enough
source-request capacity for those reads. It uses the existing restricted reader,
not paid Firecrawl or Parallel extraction, and does not enable a scheduler.

## Parallel

Create a key in the [Parallel platform](https://platform.parallel.ai). A Parallel
API key authenticates the direct Search/Extract/Task surfaces; the Task deep-
research example uses `x-api-key` on `POST /v1/tasks/runs`. The same provider key
is used as a Bearer token for authenticated Search MCP. Do not create redundant
search, extraction and deep-research secrets.
[Search MCP](https://docs.parallel.ai/integrations/mcp/search-mcp),
[Task deep research](https://docs.parallel.ai/task-api/examples/task-deep-research).

Proposed use: Search/Extract for bounded interactive retrieval; Task API for
explicitly budgeted asynchronous research. Task submission, polling, result
receipts, cancellation/reconciliation semantics and costs need their own adapter.
Research output is evidence to verify, not authority to change skills or publish.

`https://search.parallel.ai/mcp` permits anonymous lower-rate exploration and
Bearer-key authentication. Its `/mcp-oauth` alternative requires authentication.
For the cloud service, use explicit provider authentication and reviewed tool
allowlists, not developer OAuth state or anonymous production fallback. Test the
actual advertised result contracts before registering them in our strict bridge.
[Parallel MCP authentication](https://docs.parallel.ai/integrations/mcp/search-mcp).

## X

For the official X API, copy the app-only Bearer Token from the developer
console. Do not put the consumer API key, API secret, or OAuth user token into
`X_BEARER_TOKEN`. App-only authentication supports eligible public-data reads
without a user context; posting and user-context operations are not in scope.
Verify the account's search entitlement and billing separately.
[X Bearer tokens](https://docs.x.com/fundamentals/authentication/oauth-2-0/bearer-tokens),
[application-only authentication](https://docs.x.com/fundamentals/authentication/oauth-2-0/application-only).

If “XAPI” means a third-party provider rather than the official X API, identify
the provider before adding its key. Its origin, headers, data rights, pricing and
pagination need a separate adapter. Never send its key to `api.x.com` by default.

## A better search path for arXiv research

Interpretation: “archive” refers to arXiv, not long-term artifact storage.

Direction, still to be benchmarked for source quality:

1. **OpenAlex keyword search** for initial paper discovery and filtering.
2. **Semantic Scholar** for fallback keyword/bulk search and bounded
   reference/citation expansion.
3. Resolve selected works to **arXiv IDs/versions or DOI/publisher originals**.
4. Retrieve selected permitted full text explicitly, cache exact bytes, and
   retain provenance, depth, truncation and coverage-failure metadata.

This separates search availability from primary-source retrieval. Index results
may lag recent papers, omit records, or collapse versions. They do not replace
canonical version checks or make every paper's full text available.

Get an OpenAlex key from [account settings](https://openalex.org/settings/api).
The implemented keyword adapter sends a Bearer credential, never an API key in
the URL, and rejects known credential reflections before capture. Current
documentation recommends this header form. Semantic search and full-text
acquisition are not enabled by the adapter.
[OpenAlex authentication](https://help.openalex.org/api/authentication/).

Request the optional Semantic Scholar key through its
[API page](https://www.semanticscholar.org/product/api). It authenticates with
`x-api-key`. Its documented paper search operates on keywords in title/abstract;
the provider name should not be mistaken for an arbitrary semantic-search
guarantee. It adds paper recommendations and citation/reference relationships.
[Semantic Scholar tutorial](https://www.semanticscholar.org/product/api/tutorial).

The public arXiv query API needs no key. Its manual documents metadata, abstracts,
identifiers and links, not an unlimited full-text search service. Retain bounded
request spacing/backoff and make rate-limited coverage visible. Crossref public
metadata also needs no account API key; a contact email can identify polite-pool
requests. Crossref is optional DOI enrichment, not our first search backend.
[arXiv manual](https://info.arxiv.org/help/api/user-manual.html),
[Crossref authentication](https://www.crossref.org/documentation/retrieve-metadata/rest-api/access-and-authentication).

Selected cached full text is also available through OpenAlex where covered, with
separate costs and original rights. It is an optional retrieval route, not a
license bypass or completeness guarantee.
[OpenAlex full-text content](https://developers.openalex.org/download/full-text-pdfs).

Acceptance checks before declaring this better: recent-paper indexing delay,
known-paper recall, topic relevance, duplicate/version mapping, primary-text
coverage, qualifier retention, latency, rate-limit recovery and cost per usable
source. Compare the same query set and time window across providers. No superiority
claim or paid scholarly API benchmark follows from this documentation review.

## GitHub and cloud-only credentials

For staging, create a short-lived **fine-grained personal access token** owned by
the repository owner, selecting only
`muratcankoylan/Agent-Skills-for-Context-Engineering`. The current draft publication
operations need repository Contents read/write, Pull requests read/write and
Metadata read. Do not add administrator, workflow editing, or repository-deletion
permissions. Token permissions alone do not enforce “draft only” or “never
merge”; keep the credential outside agents and retain repository protections and
the gated effect owner.
[GitHub token setup](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens),
[endpoint permissions](https://docs.github.com/en/rest/authentication/permissions-required-for-fine-grained-personal-access-tokens).

For cloud operation, prefer a narrowly scoped GitHub App with rotating installation
tokens. The env file includes **commented, planned** App ID, installation ID,
private-key-file and webhook-secret fields. Leave these blank until that adapter
and inbound webhook handling exist. Keep the PEM in a private secret file/mount,
not multiline env text. Current code does not consume those planned App fields.

There is no universal MCP API key. Every server has its own authentication and
tool policy; Parallel uses the Parallel key. No vector database, Slack, email
delivery, or cloud administrator key is required for this local preparation.
GitHub review requests are the initial notification channel. Cloud workload
identity and storage credentials depend on the deployment target and should not
be provisioned as broad root/admin secrets in this file.

After values are supplied: validate presence and formatting without printing them,
repair existing connector failures, then run bounded endpoint-specific preflights.
Paid Task jobs, model sessions, X data reads and scholarly downloads need explicit
cost accounting within the shared experiment budget. Keep the campaign, recurring
admission and GitHub writes disabled until their gates pass.

## Setup verification, 29 September 2026 UTC

The current private file passes the no-network preflight for its selected free
arXiv/HN/Hugging Face profile. A read-only in-memory check selecting X/OpenAlex
correctly blocks on missing keys and per-request ceilings; it does not change the
file or activate those sources. OpenAI is present but unused by this profile.

The full service suite passed 457 tests, including private env/config parsing,
literal-only syntax, symlink/FIFO/race rejection, no ambient fallback, command
credential allowlists, exact budget arithmetic, exclusive config generation and
pre-reservation rejection of malformed source tokens. The inventory suite passed
119 tests. Ruff, strict repository validation, platform compatibility with the
reference validator and regenerated inventory checks passed. These are local
contract checks, not provider authentication or retrieval-quality benchmarks.

The private `.env.local` remains gitignored and mode `0600`; the existing OpenAI
assignment was not replaced. New public templates contain no keys. No provider
account purchase, credentialed connector canary, model campaign, GitHub write or
recurring service activation was performed. A documentation lookup through the
development Parallel CLI failed to connect; billing/access recommendations were
verified through official web documentation instead.
