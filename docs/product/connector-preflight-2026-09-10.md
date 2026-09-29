# Connector preflight: 2026-09-10

Status: **blocked for an integrated managed campaign or production launch**.
This is a diagnostic snapshot, not a deployment, benchmark result, or authorization
to publish. Checks ran on September 10 in America/Toronto, September 11 UTC.
The integrated checkout was on `codex/local-production-rehearsal`, base commit
`c6cd52017b247804373339e1c3c103d42554b0a1`, with pre-existing uncommitted work.

No paid model inference, managed session creation, X request, GitHub write,
notification, recurring admission, or cloud deployment was performed. The approved
$100 experiment has not started. Secrets were neither printed nor persisted in
diagnostic receipts. Synthetic credentials were used for negative security probes.

## Development tools are not product runtime tools

Codex has working development subagents, web access, and a local GitHub CLI.
Three subagents audited source retrieval, MCP, and publication independently.
There is no dedicated GitHub MCP exposed to this development session. GitHub REST
through the CLI provides repository/PR access without requiring an MCP plugin.
Neither those tools nor the developer's CLI authentication are inherited by a
managed Agents API session or a cloud deployment.

The repository currently has two separate execution paths:

1. Native service: registered collectors, capture replay, native model calls,
   candidate freeze, paired review, and optionally draft-only publication.
2. Managed canary: manually supplied evidence, corpus/context compilation,
   isolated Agents API transport, single-session recovery ledger, and a validated
   result that still awaits independent evaluation.

They are not one integrated production workflow. The managed compiler explicitly
emits `tools=[]`, `vault_ids=[]`, and `environment={"type":"none"}`. Subagents
default to zero; an explicit compiler argument supports up to three. There is no
automatic source broker, GitHub delivery, or operator-UI integration for that path.
The public native example likewise has no MCP registrations and disables GitHub.

## Live checks

| Surface | Observation | What this establishes |
| --- | --- | --- |
| OpenAI key | `GET /v1/models`: HTTP 200; Astra, Terra and Luna listed | Authentication and model-list visibility, not inference/tool access |
| Agents API read endpoint | Independent `GET /v1/agents/sessions?limit=1`: HTTP 200 | Read endpoint access; no session created or session contents disclosed |
| Actual managed transport | Same read through existing `AgentsClient` worker failed with `MALFORMED_TRANSPORT` | A real adapter compatibility blocker, despite authentication working |
| GitHub developer connection | Repository and draft PR #134 readable; the harness-pinned API version also accepted | Developer CLI read access, not cloud credential provisioning or publication verification |
| Official docs MCP | Anonymous initialization and tool listing succeeded; protocol `2025-11-25` | Real SDK transport works; three protocol HTTP requests, zero tool invocations |
| arXiv | HTTP 429, no Retry-After, zero leads | Rate-limited, not a negative research result; no retry attempted |
| DeepMind | HTTP 200, six leads | Five title-only items and one RSS description |
| Hugging Face | HTTP 200, six leads | Six title-only items |
| Microsoft Research | HTTP 200, six leads | Six feed-embedded article texts, two explicitly parser-truncated |

The source checks made exactly four requests, retaining 605,186 response bytes.
All four captured outcomes replayed successfully through the actual parsers with
socket connections forbidden. These were discovery reads, not independent
full-paper or article fetches. Company lanes read latest-feed windows with empty
provider queries; they are not topic-search engines.

After replay verification, the eighteen normalized evidence records compiled
directly into a managed packet for `memory-systems`, without schema conversion:
121,179 canonical request bytes, `gpt-6-astra`, zero subagents, zero remote calls.
This proves local input compatibility only. `prepare_packet` itself does not
replay captures, assess semantic relevance, or enforce sufficient source coverage.
Even the empty arXiv evidence list compiles syntactically.

## Release-blocking findings

### 1. Managed HTTP transport rejects an observed non-framing header duplicate

The authenticated live response included repeated, case-variant
`access-control-expose-headers`. Its inspected framing was otherwise:
`content-type: application/json`, `content-length: 96`, no content encoding and
no transfer encoding. The transport's blanket normalized-header uniqueness check
rejects this response. The HTTP status was 200.

An offline reproduction held HTTP status, JSON and body length constant: the
single-header control passed; adding only the differently cased non-framing
duplicate produced `MALFORMED_TRANSPORT`. A duplicate Content-Type control still
failed as required. This reproduces the local mechanism behind the live rejection.

The correction needs a field-aware policy and regression coverage. Preserve
strict rejection of ambiguous security/framing headers; do not solve this by
silently accepting arbitrary duplicated Content-Length, Content-Type, encoding,
or transfer fields. Re-run the actual isolated transport after the correction.
See `researcher/service/openai_agents.py`, `_native` and `AgentsClient._request`.
This also affects the code carried by draft PR #134.

### 2. GitHub publication lacks credential-reflection guards

Three extra, offline synthetic-credential probes reproduced unsafe behavior:

- A credential already present in the configured repository name entered the
  outgoing URL and retained effect metadata.
- A credential already present in candidate text entered the blob payload.
- A reflected credential in an extra response field entered the retained effect.

These are demonstrated boundary failures under supplied inputs/response reflection,
not evidence that an attacker obtained a real key. No actual credential or network
was used. All three probes failed their safety expectations. Existing happy-path
and failure tests did not cover them.

Reject credential material before dispatch or effect reservation, and validate
responses before persistence. Add input, response, resume, and rejection-before-
write regressions. Keep publication disabled until the probes pass.
Relevant boundaries: `github.py:169`, `github.py:191`, and `workflow.py:230`.

### 3. A reachable MCP server is not a compatible registered connector

The five tools advertised by `https://developers.openai.com/mcp` all omitted
`outputSchema`. Our native bridge requires exact agreement with an operator-
registered object output schema. An offline replay confirmed
`TOOL_SCHEMA_MISMATCH`, with no tool invocation attempted. Do not weaken this
silently or label the endpoint production-ready from its successful handshake.

Choose an explicit, versioned adapter for the server's real result contract, or
expose our own schema-stable research broker. Pin tool names and input/output
contracts and verify actual tool calls separately. No production MCP endpoint or
cost allowance was configured during this audit. Tool annotations alone do not
establish read-only authority or a price guarantee.

### 4. Evidence depth, budget, and qualifier transfer are incomplete

Eleven of eighteen live leads contain only titles. They cannot support detailed
claims about methods, results, or skill-effectiveness improvements. Explicit
one-hop primary reading exists, but is not automatically connected to managed
preparation.

Microsoft's captured evidence contains 72,410 text bytes alone. The native
workflow's complete serialized evidence ceiling is 65,536 bytes, so this fresh
lane cannot proceed there unchanged. Increasing the limit is not a retrieval
strategy. Introduce explicit selection, bounded excerpts and omission receipts.

Managed projection currently removes `summary_kind` and `summary_truncated`.
The two truncated Microsoft excerpts therefore lose their specific truncation
flags before inference, although they retain the broad `discovery_summary` label.
Preserve depth, truncation, coverage failures and source-outcome qualifiers in the
model-facing contract. See `workflow.py:376` and `agents_context.py:189`.

### 5. X and cloud credentials are not configured

Only `OPENAI_API_KEY` was present among the inspected connector variables in the
project's `.env.local` and current process environment. The file is private
(mode 0600), regular, single-linked and gitignored. The check did not search
unrelated secret stores, shell profiles, or other project directories.

`RESEARCH_GITHUB_TOKEN`, `X_BEARER_TOKEN`, and `RESEARCH_OPERATOR_TOKEN` were
absent from those locations. The sample native Anthropic/Gemini credentials were
also absent; those providers are optional, not requirements for an OpenAI-only
campaign. Runtime commands do not automatically load `.env.local`.

X recent-search code exists in the connector library but is not registered in
the service, sourcing campaign, or older pipeline. Its provider minimum of ten
results also conflicts with the service's six-item limit. A key alone does not
complete that integration. Contacts enrichment is explicitly disabled.

The older pipeline's GitHub-commit and Hacker News sources, arbitrary RSS
registrations, and generic connector-library variants were not live-tested here.
They are not configured managed-runtime connectors. No live broad-web research,
X retrieval, notification delivery, or cloud operator identity was demonstrated.

## Verification boundaries

| Test group | Result | Evidence class |
| --- | --- | --- |
| Source connectors and source sourcing | 92 passed | Fixture tests, separate from four live reads |
| MCP bridge, SDK, worker and evidence | 71 passed | Injected SDK/transport and local worker tests |
| GitHub, managed context and managed runtime | 83 passed | 19 + 23 + 41 offline tests |
| Operator API and native cross-component integration | 24 passed | Actual temporary loopback HTTP and injected dependencies |
| Managed HTTP adapter | 39 passed | Existing injected-transport suite |
| Additional GitHub security probes | Three safety failures reproduced | Fake credentials, fake transport, no effects outside memory |
| Additional HTTP-header probe | Non-framing duplicate rejected; two controls passed | New compatibility failure reproduced offline |
| MCP absent-output-schema probe | Rejected before tool call | Expected fail-closed compatibility result |

The first five rows cover 309 distinct tests. The MCP reviewer also reran the 64
context/runtime tests; these are not counted twice. Passing these tests does not
erase the newly discovered live-transport, security, or content-transfer failures.
No downstream semantic-effectiveness benchmark was executed.

## Smallest next integration sequence

1. Fix the observed HTTP and GitHub boundary failures and encode reproductions
   into regression tests. Repeat the non-mutating live preflight.
2. Unify source admission with managed preparation: capture, replay, select,
   retain qualifiers, and bind evidence plus coverage receipts to the work order.
   Handle rate limiting as an explicit retry/degraded-coverage state.
3. Register a narrow read-only research MCP broker and, separately, optional
   built-in web search. Check real contracts and per-tool effect/cost limits.
4. Test zero versus bounded subagents after tool access, effective configuration,
   billing containment, and cancellation/recovery gates pass. Use separate
   evaluator sessions; collaborating children are not independent judges.
5. Connect validated output to existing candidate freeze, independent evaluation,
   validation/export receipts, then an explicitly authorized draft-delivery intent.
   Keep GitHub write credentials outside research agents. Provision a narrowly
   scoped GitHub App for cloud delivery rather than inheriting developer auth.
6. Connect managed job/session status to the operator API and UI. Only then start
   a supervised bounded canary before the month-equivalent experiment. Do not
   activate unattended scheduling or claim production readiness from this audit.

No new scheduler or agent framework is needed to close these specific gaps.
The missing work is integration and verification of existing ownership boundaries.

Official contract references: [Agents MCP](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp),
[web search](https://developers.openai.com/api/docs/guides/agents-api/tools/web-search),
[multi-agent tools and inheritance](https://developers.openai.com/api/docs/guides/agents-api/multi-agent),
[list sessions](https://developers.openai.com/api/reference/python/resources/beta/subresources/agents/subresources/sessions/methods/list),
[list models](https://developers.openai.com/api/reference/resources/models/methods/list).
The official contracts distinguish configuration capabilities from account access;
subagents inherit configured MCP and web search but do not support application
function tools. MCP `allowed_tools` and startup requirements must be explicit.
