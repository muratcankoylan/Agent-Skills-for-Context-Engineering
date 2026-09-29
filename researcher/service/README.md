# Standalone research service

The integrated research/evaluation executor is the **Codex SDK**. Start with the
[SDK runbook](CODEX_SDK.md) and
[migration contracts](../../docs/product/codex-sdk-runtime-migration.md).
Pinned workers use a tool-free, commit-before-delivery gateway under the original
cumulative authority. Real SDK fixture tests exercise scheduled/manual pipelines,
candidate evaluation and recovery. The earlier
[managed research architecture](../../docs/product/openai-agents-research-architecture.md)
and [managed canary runbook](AGENTS_API.md) remain compatibility documentation.
New default native and managed model submissions are retired. Historical receipt
replay and retained managed-session observation/cancellation remain compatibility
paths. No native or managed fallback is selected when an SDK turn fails.

Status: pre-release, 29 September 2026. A repo-owned Python service, not a Codex
automation. No desktop session or hosted scheduler is required.
The [current architecture](../../docs/product/research-organization-architecture.md),
[research protocol](../../docs/product/cloud-research-protocol.md), and
[deployment runbook](DEPLOYMENT.md) define the target and open release gates.

## What runs today

The [bounded OpenAI campaign](OPENAI_CAMPAIGN.md) now supplies cumulative budget
admission under the user's $100 model allowance and actual gold-free evaluation
execution. All funded research roles and evaluation items share one authority
directory across dates and restarts, retain failed/unknown
reservations and replay completed receipts without dispatch. The
[candidate reviewer](CANDIDATE_REVIEW.md) freezes exact inert edits, derives only
declared generated inventory files, and checks an isolated full-checkout overlay.
[Artifact-complete recovery](../runbooks/service-recovery.md) restores explicit
state closures paused, including the budget authority. These are repo-native
capabilities, not Codex automations or publication authority.
[`research_pipeline.py`](RESEARCH_PIPELINE.md) connects these boundaries into an
explicit resumable operation, with bound phase receipts and legitimate terminal
abstention. It requires an existing budget authority and does not enable recurrence.
The [organization coordinator](ORGANIZATION.md) connects bounded retrieval slots
to that pipeline with one supplied cumulative authority, explicit policy and
durable outcomes. Its tests include daily restart and compressed month dispatch;
no recurring service is activated by installing these modules.

The opt-in [captured-action profile](AGENT_ACTIONS.md) replaces only the fixed
researcher turn with model-selected context inspection, exact evidence-span reads,
one optional methods/transfer specialist and finish/stop decisions. These are
typed harness-dispatched functions across budget-admitted SDK turns, not native
SDK shell/network tools. Immutable decision receipts, replay-verified transcripts
and the existing critic/editor/evaluation gates remain separate responsibilities.
Organization can deliver bounded metadata batches to Raindrop after cycles with
`--trace-export`; see [tracing](TRACING.md) for explicit project approval and
uncertain-delivery handling. Keys alone enable neither research nor export.

The [private dossier viewer](DOSSIER.md) exposes terminal research, critique,
candidate/evaluation output, learning omissions, latency and trace delivery receipts.
It performs no model or network calls and is not a public export.

```text
eligible replay-verified retrieval + existing cumulative CodexCampaign
  -> research_pipeline: researcher -> grounding -> critic -> optional editor
  -> candidate_review: exact freeze -> full-checkout structural checks
  -> supplied evaluation plan -> CodexCampaign.evaluate: gold-free fresh SDK threads
  -> evaluated_not_accepted / abstention / explicit failure
```

The [daily retrieval-only mode](DAILY_RETRIEVAL.md) stops at a replay-verified,
bounded discovery digest and optional primary HTML evidence cards, with zero
model, MCP and GitHub effects. It adds HN
Algolia/OpenAlex discovery and enriched X recent search alongside arXiv/company
feeds. Credentialed lanes require explicit source policy; they are not activated
by the free example. The native research path below remains separate.

The [September 29 connector record](../../docs/product/connector-verification-2026-09-29.md)
contains 11 initial live checks using 14 HTTP requests. With subsequent registered
MCP investigations and canaries, the combined reservation ceiling was 50 HTTP
requests and $0.103, not measured aggregate usage or an invoice. The separate
[production preparation exercise](../../docs/product/production-exercise-2026-09-29.md)
records arXiv primary-reading scenarios, source failures, funded model execution,
recovery and deterministic simulation. Successful capture/extraction is not
measured research relevance. The
managed path now has an explicit capture-verified retrieval-to-packet handoff.
Preparation makes no provider call and is not recurring model execution or
automatic publication. See the dated [integration verification report](../../docs/product/research-integration-verification-2026-09-29.md)
for focused/full-suite results and remaining gates.

### Historical native-provider compatibility workflow

The following describes retained receipts and fixture coverage. New built-in
model calls through this workflow are refused. Use Organization with
`CodexCampaign` for new research; deterministic retrieval remains supported.

```text
service schedule / authenticated enqueue
  -> durable job and conservative effect reservation
  -> arXiv / official feed / registered MCP observations
  -> bounded corpus retrieval -> researcher -> critic -> skill editor
  -> frozen candidate -> two reversed-order model reviews
  -> private report -> optional draft GitHub PR + review request
```

Four native agent responsibilities share one coordinator process. They have separate
prompts and inputs, not four independent services. Each role can use a different
explicit OpenAI, Anthropic, or Gemini model. Native model requests run in a
credential-isolated child process with an absolute deadline. There is no model
shell, arbitrary code execution, ambient MCP discovery, or automatic merge.

The preview proposes one exact replacement in an existing skill body. Frontmatter,
activation and integration sections are locked. It freezes and re-materializes
the candidate through the existing artifact contracts before review. The new
candidate-review path adds the full-checkout structural overlay; it does not
yet synchronize all claim/mechanism/index surfaces, run every possible evaluation,
or prove downstream effectiveness. A draft
PR is unfinished review work, not an accepted improvement.

### Historical managed research boundary

New built-in session submission is refused. Preparation, inspection, `watch` and
`cancel` of existing identities remain available. The old `run` instructions are
historical compatibility documentation, not an alternate production entrypoint.

[`agents_runtime.py`](agents_runtime.py) owns one prepared request and at most
one session-create attempt per private directory. `run` submits and supervises
that session; `watch` and `cancel` operate on the retained identity without
creating another session. The provider owns its internal turns and optional
subagents. A researcher/critic/proposal object returned by one session is not an
independent evaluation, even when internal subagents are enabled.

[`retrieval_handoff.py`](retrieval_handoff.py) accepts an eligible completed daily
job, replays source and primary captures, reconstructs the exact report and prepares
a fresh managed directory. Every discovery lane must be observed, with no unresolved
or failed effects, and at least one primary card must be present. Window age is
bounded and rechecked before submission. Fixtures cannot submit. The handoff retains
discovery-to-primary links, coverage and omission counts; it does not fetch again.

The compiler strips private locators and preserves evidence depth, exact quoted
bytes and omission qualifiers. Manual evidence-file preparation remains available,
but capture verification is then the caller's responsibility. The result stops at
`AWAITING_INDEPENDENT_EVALUATION` until explicitly handed to candidate review.
[`candidate_review.review_managed()`](CANDIDATE_REVIEW.md) verifies the completed
packet/session/result bindings, freezes the inert exact edit and runs structural
overlay checks. It can prepare the same optional three-arm evaluation plan used
by the native pipeline; it makes no model call and does not publish.
[`agents_evals.py`](agents_evals.py) plans no-skill/current/candidate comparisons
and grades narrow objective answer contracts; the pure module does not execute
sessions. `openai_campaign.py` executes its gold-free projections using bounded
Responses calls, not managed sessions. No managed scheduler, cross-directory
managed duplicate prevention, managed-session global spending containment or
GitHub delivery is implied. Follow [AGENTS_API.md](AGENTS_API.md)
for supervised use; native model reservations are not managed-session hard caps.

## Install and exercise offline

From a reviewed checkout, use Python 3.11 or newer and an isolated environment:

```sh
python3 -m venv .venv
.venv/bin/python -m pip install --require-hashes -r requirements-dev.txt
.venv/bin/python -m unittest discover -s researcher/service/tests -p 'test_*.py'
.venv/bin/python -m researcher.service demo --state /absolute/private/new-demo-state --repo /absolute/repository
```

The demo requires a new private directory after implementation changes. It uses
synthetic source/model adapters, performs zero paid model or source calls, writes
only private runtime state, and does not change a checked-out skill. Its scripted
verdict proves wiring only. Output is JSON Lines: effect progress followed by the
command result. A fixture flag cannot select real providers or MCP.

## Configure real execution

Operation tracing is local and metadata-only by default. The
[trace runbook](TRACING.md) covers hierarchy, latency/usage records, safe failure
handling, inspection, explicit Raindrop export, managed snapshot projection and
retention. API keys never enable automatic uploads. Traces are diagnostics,
not budget, execution, evaluation or publication authority.

For retrieval-only setup, use the secret-free root `.env.example` as a template
without overwriting an existing `.env.local`. Run `preflight --env-file .env.local`
before generating a private configuration with `configure --env-file .env.local
--output /absolute/private/service.json`. These two commands need no state store
and cannot call providers or start jobs. The [setup guide](../../docs/product/provider-credentials.md)
distinguishes implemented providers, optional purchases and explicit budget gates.
Other service commands also accept `--env-file`; it is literal, selective and
authoritative, with no shell evaluation, global environment mutation or fallback.

Create a retrieval-only configuration using
[`config.retrieval.example.json`](config.retrieval.example.json), or `configure`.
Keep model-call budgets zero and publishing/notifications off. `config.example.json`
describes the retired native model route, not the SDK launch recipe. Put only
environment-variable names in configuration, never keys.

Pin explicit tested model IDs per role. Selecting a newly released model requires
a bounded compatibility/quality canary before changing deployed configuration;
there is no `latest` alias or silent upgrade. Keep GitHub disabled for the first
research canary. The existing Cursor benchmark runner remains independently
zero-call: this service does not reopen that activation path.

Prices are integer **micro-US dollars per million tokens**. For example, a
verified price of one dollar per million input tokens is encoded as `1000000`.
This unit example is not a vendor price claim. Budgets are integer micro-US
dollars. Input UTF-8 bytes plus a framing allowance provide a conservative token
forecast; the provider's recorded usage is separately checked. Reservations are
not invoices and are never refunded automatically after uncertainty.

```sh
.venv/bin/python -m researcher.service init --config /private/service.json --state /private/service-state --repo /absolute/repository
.venv/bin/python -m researcher.service.organization init \
  --repo /absolute/repository --sdk-python /opt/context-research/codex-venv/bin/python \
  --source-config /private/service.json --source-state /private/service-state \
  --authority /private/existing-openai-authority \
  --policy /private/organization-policy.json --state /private/new-organization
```

Supply the schedule-to-skill policy described in [ORGANIZATION.md](ORGANIZATION.md).
Then run the same organization command with `cycle` instead of `init`, adding
`--live --env-file /private/service.env`. It executes retrieval and actual SDK
roles using the existing cumulative spending authority. It does not create a new
model allowance, activate a daemon, publish a PR, or promote a skill. First install
and verify the [isolated SDK runtime](deploy/CODEX_RUNTIME.md).

Configuration is bound to the state directory. Changing configuration or job
inputs cannot silently reset budgets or replay an earlier effect. An approved
configuration/state migration procedure is still a release gate; do not evade it
by starting parallel state directories against the same external budget.

`researcher.service.organization serve ... --live` owns foreground admission. Schedules
coalesce missed intervals to the current UTC slot, rather than replaying a backlog
of billable jobs. Job IDs are deterministic per due slot. The durable worker lock
permits one active coordinator. `max_runs_per_tick` bounds sequential work, not
parallel model concurrency. Current model concurrency is one.

## Sources and knowledge transfer

The active retrieval path uses bounded arXiv title/abstract search and official
DeepMind, Hugging Face and Microsoft Research feeds. It permits ten items
for arXiv, HN, X and OpenAlex and six per company feed; the
[daily runbook](DAILY_RETRIEVAL.md) specifies its window and budget semantics.
Feeds are bounded windows, not query-complete search. Captured bytes are
re-extracted before use, rather than trusting a normalized record's hash alone.
Daily query slots persist across process restarts; arXiv requests also enforce
shared minimum spacing. No-answer and rate-limited observations are explicit.

Selected skill baselines are byte-bound; BM25 section retrieval exposes exact
offsets, retained excerpts, and omitted sections under a canonical JSON byte
budget. This is a lexical baseline, not a validated semantic retriever. The
researcher passes narrow claim IDs, exact source quotes, limitations and a proposed
test to the critic. The editor receives only critic-supported claims. Independent
evaluation tasks receive neither researcher memory nor gold answers as task
context. Literal citation matching is not entailment.

The researcher also receives a checkpointed, bounded archive of up to five prior
hypotheses for the same baseline, corpus, schedule and compatible runtime. Fixture
and live histories remain separate; evaluator answers and raw traces are excluded.
Exact repeated candidate bytes skip another evaluation only when the same frozen
evaluation plan has previously completed and been replay-verified. Research,
critique and editing are not retroactively skipped. This path does not publish PRs.
This is duplicate suppression and a small experimental memory, not semantic novelty
detection or an independently evaluated archive-search algorithm.

The retrieval-only workflow can now select up to two eligible primary HTML URLs,
capture and replay their bytes, and expose exact normalized-text excerpts through
[`primary_context.py`](primary_context.py). It does not follow arbitrary social
links, resolve all DOI targets, read PDFs/OCR, or prove that a full paper was read.
Source-reported assertions and unresolved method/limitation assessments stay
separate. Paid Parallel Search/Extract and Firecrawl Research Index search/basic
scrape have bounded live one-shot diagnostics, not daily retrieval adapters.
The Firecrawl scrape returned exact-source markdown; Research Index returned
paper metadata and an abstract. Neither result proves full-paper ingestion or
comparative research quality. The registered Parallel MCP bridge also completed
a real isolated fetch under explicit registration and reservation.

The explicit `research_pipeline.py` path consumes eligible verified discovery
and primary cards, including X/HN/OpenAlex, without buying the same retrieval
again. The compatibility workflow does not automatically acquire these lanes.
Historical managed preparation can reuse the same bundle without creating a
session; new default managed submission is retired. An operator can register a
reviewed read-only MCP endpoint for research-mode sources; endpoint availability,
access rights and cost must be established before use. Retrieval-only mode does
not execute MCP tools, and the Organization coordinator rejects MCP configuration.
These boundaries are not complete research-source coverage.

### Optional registered MCP reads

Install the separately pinned optional dependencies from `requirements-mcp.txt`.
The bridge deliberately targets SDK 1.30.0 and protocol `2025-11-25`; it does not
claim compatibility with every newer server or the SDK 2.x API.

Add `mcp_tools` entries with `registration`, `credential_env` (or null), and
`max_cost_microusd`. Registration contains exactly `id`, `url`, `tool`,
`input_schema`, `output_schema`, `max_output_bytes`, `timeout_seconds`, and
`protocol_version`. URLs must be HTTPS public endpoints; schemas are explicit and
cannot fetch remote references. Add `mcp_reads: [{"id": "registered-id",
"arguments": {}}]` to a schedule. The arguments must satisfy its registered schema.
Up to two registrations/reads are allowed; there is no model-generated tool list.
The sum of MCP output ceilings in a schedule cannot exceed 32 KiB, reserving room
for source evidence and provenance. The complete evidence packet is still checked
against its 64 KiB cap after retrieval; excessive content is rejected, not silently
truncated.

Each invocation reserves its declared cost and twelve source HTTP requests before
entering the bridge. This is a transport ceiling, not a claim of twelve actual
requests. Zero cost is appropriate only for a tool whose operator has verified
that it is free. Read-only authority must also be enforced by the remote service
credential. MCP annotations alone cannot prove read-only behavior. Output carries
`authority: none`, stays untrusted, and cannot become a policy or instruction.

The SDK output cap applies after parsing. DNS is checked but not socket-pinned.
Live reads use a dedicated process with an absolute deadline, bounded stdout and
SDK logging disabled. This prevents third-party error logs from echoing credential-
bearing malformed responses. The raw gateway is an internal adapter, not a safe
credential-bearing service entry point on its own.
MCP deployment therefore requires an egress policy blocking private/metadata
destinations and process memory limits. Do not enable an unreviewed endpoint on
the assumption that the Python adapter provides a network sandbox.

## Results, PRs and interaction

Runtime state is a private SQLite database plus evidence captures and frozen
candidate artifacts in the operator-selected directory. Never place it in a
public checkout. `status` returns job states and reservation totals; `inspect`
returns a selected job's private report. Progress events expose stage names,
hashed job IDs and elapsed time, not credentials or raw prompts.

The private API runs separately with `api ...`, bound to `127.0.0.1:8787`, using
`RESEARCH_OPERATOR_TOKEN` (32–256 URL-safe characters). It has authenticated
status, pause and configured-schedule enqueue endpoints. It rejects browser
Origin headers and streaming bodies. It is not a public ingress server.

The Next.js control center's `/service` page can read that API server-side with:
`RESEARCH_SERVICE_ENABLED=1`, `HOSTNAME=127.0.0.1`,
`RESEARCH_SERVICE_URL=http://127.0.0.1:8787`, and the operator-token environment
variable. Tokens never enter browser code. The page is read-only and has no
fixture fallback. Use CLI/API for commands; cloud access needs a reviewed private
tunnel or TLS/identity gateway.

The UI currently lists native/retrieval job states and reservations, not full
decision dossiers or managed SessionLedger records. `/observations` reads a
separate bounded local summary; the other fixture control pages must not be
mistaken for live job controls. Report-detail navigation, managed cancellation
and authenticated public access remain integration work.

The legacy GitHub delivery adapter requires `github.enabled=true` and a separately scoped credential
for the configured repository. It creates a new candidate branch and **draft** PR,
optionally requests the configured user's review, and rechecks the base commit.
No force update, default-branch write, merge, arbitrary notification recipient, or
workflow modification is available. A review request is a GitHub notification
attempt, not proof the user received/read it. Delivery adapters have contract
tests, but a live sandbox PR/notification canary is still required. It is not
automatically connected to SDK pipeline output, and Organization requires
publication/notification configuration to remain disabled.

## Recovery and remaining release gates

Completed effects replay from retained outputs without new credentials or cost.
Retrieval can continue available source lanes after bounded expected source-effect
failures, preserving `source_failures` and coverage gaps. Unknown/blocked outcomes
still require reconciliation; credential/configuration/integrity failures are not
silently treated as an empty successful source. A report with source failures is
not eligible for SDK research handoff; ordinary bounded-page coverage remains
partial even when every source is observed.
If a process dies during a remote effect, the job becomes
`reconciliation_required`; it is not automatically retried. Unknown outcomes
retain reservations. The preview intentionally lacks an unsafe “force retry”
switch. Remote reconciliation and operator resolution need further integration.

Pause stops new admission/effects, not a request already on the wire. A backward
wall clock change blocks budget/schedule progress. Trusted host time remains an
operational assumption. The original `backup` command is a private SQLite
inspection snapshot only. Use `recovery_bundle.py` for consistent SQLite plus the
registered capture/candidate closure and explicitly selected managed ledgers;
the Campaign authority has its own narrow closure. Source/configuration and
per-file hashes are verified before restoring to a fresh private destination.
Unknown effects and cumulative reservations survive; databases are already paused
before materialization, with no credential read or worker start. Unregistered
pipeline/coordinator files are not included implicitly. Fence original writers
and reconcile post-snapshot effects before any resumed dispatch. See the
[recovery runbook](../runbooks/service-recovery.md); neither backup form grants
activation.

The [dated production exercise](../../docs/product/production-exercise-2026-09-29.md)
now includes live bounded model calls, a registered
MCP read, full candidate structural overlays and paused artifact-complete restore.
Before unattended release: accepted ownership contracts, semantic candidate metadata
integration, held-out effectiveness evaluations, sandbox PR delivery,
operator reconciliation of uncertain effects, encrypted
artifact-complete restore, cloud installation/resource limits/egress, and a
multi-day soak must pass. Do not claim an autonomous research organization or
self-improvement result from fixture success or two favorable model opinions.
The source/API canaries already recorded are scoped evidence, not a reason to
repeat paid checks or a substitute for those remaining gates.
