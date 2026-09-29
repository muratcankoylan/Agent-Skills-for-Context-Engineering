# Research system: current architecture and production path

**Historical snapshot.** For the current architecture, runtime ownership,
cross-run learning, tracing and deployment contract, read
[Repository-owned research organization](research-organization-architecture.md).
The native/managed branches below describe the earlier implementation epoch,
not active new-execution instructions.

Later runtime update: the [Codex SDK migration](codex-sdk-runtime-migration.md)
and [implemented runtime runbook](../../researcher/service/CODEX_SDK.md) supersede
the native/managed executor direction in this snapshot. The first SDK reference
topology is a persistent Linux coordinator; GitHub provides reviewed source, CI
and eventual separately authorized publication. The earlier
[GitHub release plan](github-release-plan-2026-09-29.md) retains dated PR and
control-plane evidence, not proof of a deployed SDK organization.

Date: 2026-09-29. Scope: the integrated repository-owned implementation and its
target product, not a claim that all changes are merged, deployed or scientifically
validated. This document does not advance specification lifecycle states.

## 1. Product objective and success criteria

The product is an open-source research service that turns explicit research needs
into source-grounded decision dossiers and reviewable improvements to the skill
corpus. The desired loop is research, falsifiable hypothesis, frozen experiment,
independent evaluation and human-controlled change. Producing more links or more
agent messages is not the objective.

A useful dossier must distinguish source assertions, researcher interpretation,
competing evidence, missing evidence, the exact proposed behavior change, and its
measured effect. Improvement means better held-out task outcomes under declared
cost/context budgets, not higher self-assigned confidence or two favorable votes.

The repository owns scheduling, evidence, state, permissions, evaluation and
publication policy. Codex is a development client, not a deployed scheduler.
The preferred managed execution direction is the OpenAI Agents API. The current
funded research/evaluation executor uses bounded native OpenAI Responses calls;
the older OpenAI/Anthropic/Gemini role workflow remains a separate compatibility
and comparison path. Provider choice does not transfer merge or acceptance
authority to a model.

## 2. Current implementation versus target

| Surface | Implemented now | Still required |
| --- | --- | --- |
| Admission | Python foreground coordinator, deterministic schedule slots, transactional reservations, exclusive worker and cumulative OpenAI campaign authority | Managed-session admission and containment of clients outside the service |
| Discovery | Seven registered daily sources, fixed requests, captured bytes, offline extraction replay | Measured retrieval relevance/coverage; selected fallback providers |
| Primary reading | Optional bounded arXiv/company HTML reads, replay and exact excerpt cards | Broader permitted formats and independent scientific assessment |
| Native research | Separate researcher, critic and editor calls, early grounding gate, durable pipeline and gold-free evaluation executor | Representative held-out effectiveness and automatic evidence follow-up policy |
| Managed research | Capture-verified handoff, one-create session ledger, observation/cancellation, final-result validation and candidate-review handoff | Shared session spending containment and owner-store/UI linkage |
| Candidate handling | SPEC-003 freeze, materialization, full-checkout overlay, restricted inventory derivation and four structural checks | Synchronized semantic claim/mechanism surfaces and accepted promotion |
| Delivery | Optional native draft PR and GitHub review request | Live sandbox delivery canary and production-scoped identity |
| Operator experience | CLI, authenticated loopback API, real read-only `/service` status | Dossier browsing, managed state/actions, public identity/TLS boundary |
| Deployment | Linux/systemd templates; verified ARM64 MCP runtime-image build/offline smoke; paused Store/budget restore; compressed month fault simulation | Approved source-release execution, chosen host, encrypted operational backups and wall-clock cloud soak |

The source-verification [record](connector-verification-2026-09-29.md) is dated
evidence: the initial 11 connector checks used 14 HTTP requests. Subsequent
generic-MCP investigations and validation brought the combined reservation
ceiling to 50 HTTP requests and $0.103, including failed attempts; that ceiling
is not measured HTTP usage or a provider invoice. X and OpenAlex captures also
replayed. Separate arXiv primary-reading scenarios, source failures and model
observations belong to the [production preparation exercise](production-exercise-2026-09-29.md).
These are not model-quality, long-running reliability or end-to-end improvement
results.
Historical [router results](../../researcher/benchmarks/router/results-published/2026-05-19.md)
measure a different surface: skill-description routing, not this service.

### September 29 integration status

The following bounded changes are implemented and have focused regression tests.
The dated [integration verification report](research-integration-verification-2026-09-29.md)
records their validation scope and any pending gates; this is not a production
release declaration:

1. `retrieval_handoff.py` prepares a managed packet from a replay-verified,
   completed retrieval job with at least one primary card, without fetching or
   submitting a session. Its source/primary/report identity and tamper tests pass.
2. Retrieval-specific failure isolation retains expected source failures and
   allows available lanes to produce a partial report. Unknown or blocked effects
   require reconciliation; they do not authorize a retry or managed preparation.
3. The provider adapter accepts HTTP 201 on create, and the compiler explicitly
   disables programmatic tool calling rather than assuming an empty tool list
   disables it. The managed CLI also accepts an explicit private `--env-file`
   without ambient fallback.

These changes do not authorize a new paid campaign, unattended research, source
qualification, publication or acceptance.

### Funded production exercise

The subsequently authorized campaign now has an executable
[research pipeline](../../researcher/service/RESEARCH_PIPELINE.md) and
[cumulative OpenAI authority](../../researcher/service/OPENAI_CAMPAIGN.md).
One existing authority covers the user's $100 cumulative model allowance across
research roles, evaluation items, dates and restarts. Failed and unknown effects
retain their reservations; a new directory is not a new allowance.
The [dated exercise report](production-exercise-2026-09-29.md) separates live
provider/model observations, compressed deterministic simulation, fixture
evaluation and unperformed scientific validation. Successful API access is not
evidence of useful research; the live critic's abstention is preserved.

The funded backend uses bounded Responses calls with separate role contexts.
Official managed-session interfaces do not establish a caller-controlled hard
session cost bound, so the same local dollar reservation must not be presented
as containment for an autonomous managed session. This is a backend contract
decision, not a dependency on the desktop that developed the service.

## 3. End-to-end flow and process ownership

```text
operator research need + reviewed config
  -> coordinator admission -> Store job/effect journal
  -> discovery capture -> extraction replay -> bounded discovery digest
  -> optional primary HTML capture/replay -> exact evidence excerpts
  -> verified evidence handoff [preparation itself makes no provider call]
  -> managed research packet -> explicit one-session execution -> structured proposal
  -> review_managed -> candidate freeze + structural overlay + evaluation plan
  -> separately admitted gold-free task execution -> human review

funded bounded pipeline:
  verified completed retrieval -> cumulative OpenAI admission
  -> researcher -> deterministic grounding -> critic -> optional editor
  -> exact frozen candidate -> derived inventory + structural overlay validation
  -> supplied gold-free paired task execution -> private dossier / human review

native compatibility branch:
  captured arXiv/feed/MCP evidence -> researcher -> critic -> skill editor
  -> frozen candidate -> two reversed-order model reviews -> optional draft PR
```

The compatibility branch has optional draft-PR delivery; its paired review is
not a scientific effectiveness gate. The funded pipeline connects research,
candidate review and actual supplied-task execution, but does not publish.
The managed branch is the preferred direction; `review_managed()` connects its
validated outputs to the same candidate contract and an optional evaluation plan.
Neither candidate review nor that plan executes a managed session or grants
publication authority. Do not combine branch status labels into a fictional
automatically published or accepted pipeline. The
[organization coordinator](../../researcher/service/ORGANIZATION.md) now connects
bounded daily source admission to this shared-budget pipeline, with immutable
bindings, terminal receipts, pause controls and exact restart. Its 30-day
compressed dispatch test is fixture evidence, not a month of hosted availability.
Recurrence requires explicit foreground-service activation; no desktop scheduler
is involved and no recurring service was activated in this exercise.

| Responsibility | Current execution | Authority boundary |
| --- | --- | --- |
| Coordinator | One local Python process with a worker lock | Admits configured work; models cannot change budgets or schedules |
| Source adapters | Bounded synchronous effects | Observe approved endpoints; source text cannot authorize another fetch |
| Researcher | Native role call, or managed structured result | Proposes claims/hypothesis with exact evidence IDs and quotes |
| Critic | Separate native prompt; managed result contains a critique field | Challenges support; no evidence/acceptance promotion |
| Skill editor | Native scoped role; managed proposal field | One exact permitted body replacement, not arbitrary code |
| Evaluator | Legacy paired model reviews; shared pure task planner/scorer plus `Campaign.evaluate()` gold-free execution | Actual task execution exists; representative independently labeled held-out data, calibrated scoring and effectiveness evidence remain missing |
| Publisher | Deterministic GitHub adapter under explicit config | New branch/draft PR only; never merge or default-branch overwrite |
| Operator | CLI/private API, human review | Approves spend, reconciliation, deployment and final merge |

Native roles are responsibilities with separate inputs, not four services. Managed
subagents run within a provider session when explicitly enabled. Their concurrency
limit is not a cap on total model calls or cost. A session returning its own
critique is not an independent evaluator.

## 4. Evidence depth, selection and provenance

Evidence has several distinct layers:

1. **Discovery observation:** a post, story, title, abstract or feed excerpt.
2. **Primary observation:** captured article bytes and bounded extracted spans.
3. **Assessed assertion:** a source-reported mechanism/result with limitations and
   an explicit researcher interpretation. Current primary cards leave these
   assessments unresolved.
4. **Independent experimental result:** a frozen intervention compared on held-out
   tasks with failures and cost retained.
5. **Accepted corpus change:** a separately authorized, validated human merge.

A hash proves byte identity, not truth. Replay proves that a parser derives the
record from retained bytes, not that the source is scientifically sound. Multiple
URLs, versions or social cross-posts do not imply independent corroboration.

| Source | Current daily output | Important limit |
| --- | --- | --- |
| arXiv | Title/abstract search, submission-date ordering | Bounded page; requested daily window is not enforced by this lane |
| DeepMind, Hugging Face, Microsoft Research | Feed observations | Recent feed window, not semantic or query-complete search |
| Hacker News | Story search and available story text | Social discussion/lead, not the linked article body |
| X | Recent posts with requested metadata when returned | Bounded recent window; no automatic thread or outbound-page reconstruction |
| OpenAlex | Publication-date search and reconstructed available abstracts | Not full text or a complete ingestion/update feed |
| Restricted primary reader | Eligible arXiv/company HTML | No generic recursive crawl, arbitrary DOI resolution or PDF/OCR |
| Registered MCP | Explicit native research reads | Remote credential must enforce read-only authority; registration is not trust |

Parallel Search/Extract and Firecrawl Research Index search/basic scrape have
bounded live one-shot diagnostics, but are not daily retrieval adapters. The
registered Parallel MCP bridge also completed a real isolated `web_fetch`;
enabling it still requires an explicit research-mode registration, request and
reservation. These checks do not establish comparative search quality or full
paper ingestion. Other credential names do not create connectors. Provider setup
is documented in [provider credentials](provider-credentials.md), without copying
secrets here.

Discovery requests are one-page bounded effects. The daily digest retains at most
20 observations under a 32 KiB canonical-JSON ceiling; text omissions are explicit.
Optional primary reads are limited to two, one per host, with a separate 32 KiB
card budget. The selected text spans remain byte-addressable. The
[daily runbook](../../researcher/service/DAILY_RETRIEVAL.md) owns detailed limits.

Current corpus retrieval is BM25-style lexical section selection; discovery and
primary selection also use lexical overlap. These are inspectable baselines, not
validated semantic relevance classifiers. The published primary case review
already showed that topical overlap can retrieve an adjacent application rather
than direct evidence of a harness improvement. Selection quality needs labels.

## 5. Implemented connection: a verified evidence bundle

Use the completed retrieval report as the observation boundary and reuse existing
projections. Discovery `context_digest.items` already carries compatible evidence
IDs, text, digests, scope and qualifiers. `project_primary_evidence()` converts
replayed primary cards into the same compiler contract without private locators.
`prepare_packet()` and `SessionLedger.prepare()` already freeze a managed request.

`retrieval_handoff.verified_bundle()` verifies job/report/checkpoint identity,
reconstructs source queries and windows, replays captured discovery/primary bytes,
rebuilds selected projections and the exact report, and binds the destination
packet to the source manifest/report. It rejects tampered spans, fabricated
derived leads, missing captures, incompatible inputs and fixture/live mixing.
An inspection JSON export is not this verification.

Eligibility is deliberately narrower than retrieval completion: every discovery
lane must be `observed`, with no failed/unknown effects or source-failure entries,
and at least one replayed primary card. A known captured HTTP 429 is retained
retrieval evidence but is not eligible for this handoff. Coverage can still be
partial because requests are bounded pages and primary extraction is incomplete.
The source window must be within the configured age bound: two days by default,
at most seven days. Submission rechecks freshness. Fixture packets cannot submit.

`prepare_from_retrieval()` creates a fresh private destination ledger with no
network/model effects. The packet retains discovery-to-primary excerpt links,
omission counts, window/coverage limits and source-depth qualifiers. The managed
research rubric asks for a mechanism, transfer assumptions, counterevidence and a
falsifiable paired held-out test; it does not claim that test was performed.
The command and its eligibility checks are in the [managed runbook](../../researcher/service/AGENTS_API.md).

| Alternative | Benefit | Cost/risk | Decision |
| --- | --- | --- | --- |
| Reuse a verified evidence bundle | Same captured inputs, reproducible comparison, no second retrieval purchase | Requires a strict report/capture loader | Implemented zero-call managed preparation and explicit native research-pipeline consumption |
| Retrieve again inside each agent/backend | Backend-local convenience and newer observations | Different evidence across comparisons, duplicate cost and retry/egress policies | Avoid as the default; use only a separately declared experiment |
| Rewrite around a new distributed agent framework | Could unify APIs at once | Replaces working replay/freeze/state code before measuring a bottleneck | Not justified by current workload |

The target has one application admission owner. Managed session files may remain
leaf recovery records linked by exact identities, not a competing accepted-state
plane. Today duplicate create suppression is per destination ledger only. Preparing
the same source into another directory is not globally prevented; the bridge does
not add shared admission, account-wide reservations or scheduled managed dispatch.

## 6. State, triggers and failure behavior

`Store` owns the native/retrieval job queue, input-bound checkpoints, conservative
effect reservations, source slots and terminal dispositions in private SQLite.
Captures and candidate CAS bytes live alongside it. One host and one worker lock
are the supported ownership model, not multi-host leader election.

`serve --live` is the foreground scheduler/executor. `tick` only admits due work;
`work` drains bounded work. Schedule/UTC-slot identities prevent duplicate
admission. Missed slots coalesce rather than replaying a billable backlog. Manual
enqueue and authenticated API enqueue use explicit operation identities. Do not
install a second cron/desktop scheduler around the same work.

An external effect is reserved before execution. Completed outputs replay;
uncertain outcomes retain their reservation and require reconciliation. Admission
pause does not recall an HTTP request or stop a remote managed session. Retrieval
isolates bounded expected source-effect failures, continues available lanes and
records `source_failures`. Unknown/blocked source outcomes set
`reconciliation_required`; configuration, credential and integrity errors still
fail closed. `collection_completed` means the collection pass finished, not that
all sources succeeded or the search is exhaustive. Reports with source failures
are inspectable but cannot cross the strict managed handoff gate. Bounded-page
coverage remains partial even for an eligible all-observed report.

`SessionLedger` currently owns one managed create intent and recovery pointer.
It never retries an unknown create. Effective session configuration is checked;
watch failure/deadline exhaustion requests cancellation. Cancellation acknowledgement
is not observed termination. A supervisor crash can leave remote work running,
which is why managed recurrence is not enabled by the current canary.

Native compatibility per-run/daily microUSD reservations are not invoices or a
cumulative experiment budget. The separate `Campaign` authority adds a durable
$100 cumulative ceiling for admitted bounded Responses calls, including declared
prior spend and retained failed/unknown reservations. Neither mechanism establishes
a provider-enforced managed-session cap or covers clients outside that authority.
The managed create contract has no documented per-session hard dollar/token cap;
local deadlines only trigger cancellation attempts. The data-only request
explicitly disables provider-default programmatic tool calling and verifies the
effective configuration. See the [provider contract and spend references](../../researcher/service/AGENTS_API.md#provider-contract-boundaries).
An accelerated replay tests state transitions, not thirty elapsed days
of uptime, provider volatility or actual billing behavior.

## 7. Research, experiments and skill changes

An explicit research brief should name target behavior, competing mechanisms,
inclusion/exclusion criteria, counterevidence and a falsifiable task outcome.
The current native researcher emits claims, literal citations, limitations,
hypothesis and test plan. The critic selects supported claim IDs. The editor
cannot modify evaluator policy, frontmatter, activation or integration boundaries.

Native candidate bytes are frozen using the existing SPEC-003 artifact contract
and materialized for review; mutable worktree text is not the evaluated candidate.
Prior hypothesis memory is bounded, same-baseline/schedule and excludes evaluator
answers. Exact duplicate candidate bytes are suppressed. Neither feature measures
semantic novelty or grants accepted knowledge.

Two reversed-order native model reviews are an order-bias pilot, not held-out
effectiveness. The shared planner defines no-skill/current/candidate arms,
manifest-bound prompts/results and deterministic quote/ID/abstention/scoped-edit
checks. `Campaign.evaluate()` executes only gold-free task projections as fresh
bounded Responses calls and retains failures in the denominator. Candidate review
binds the frozen edit to that plan; `research_pipeline.py` binds its phases and
replays completed terminal work without new calls. Without a supplied dataset it
stops at `awaiting_dataset`, rather than manufacturing labels. Gold labels,
environment restrictions, execution receipts and frozen candidate linkage must
remain outside candidate control. Representative independently labeled datasets,
grader calibration and measured downstream gains remain unproven; the dated live
A/A fixture exercise proves execution wiring, not an improvement effect.

The [research protocol](cloud-research-protocol.md) and
[paper evaluation protocol](portable-harness-paper-protocol.md) define the next
measurement program: grouped research needs, separate development/selection/sealed
final sets, fixed-cost baselines, complete failures and cost, blinded independent
labels, leakage accounting, predeclared comparisons and stopping rules. A pilot
must estimate variance before selecting sample size; no power or quality claim
can be inferred from successful wiring tests.

## 8. Results, interaction and publishing

Today an operator reads private reports through `inspect`, observes reservations
and job state through `status`, and uses the authenticated loopback API for pause
and configured enqueue. The Next.js `/service` page reads current API status
server-side without a fixture fallback or browser credential. It does not yet
read managed ledgers or detailed dossiers. `/observations` consumes a separate
bounded local summary; fixture control pages are not live product controls.

The target operator view should expose source coverage, selected/omitted evidence,
primary-read gaps, packet/model identities, research claims, exact candidate diff,
evaluation outcomes, uncertain effects, reserved versus observed cost and safe
next actions. Report freshness and partial status must be visible. Adding this
projection is preferable to letting a browser read SQLite or private captures.

`github.publish_proposal()` can create a new branch and draft PR under explicit
configuration, recheck the base, and request one configured review. It cannot
merge, force-update the base, change workflows or treat a notification attempt as
delivery confirmation. A repository-read diagnostic does not prove write scope.
Managed results have no publication path yet. Human merge and full multi-surface
corpus validation remain separate gates even after publication integration.

## 9. Optional persistent-host profile

For this optional profile, the smallest topology is a dedicated Linux host with local persistent
disk: one Python coordinator, a separate loopback API, and optional same-host
Next.js UI reached through a restricted operator tunnel. The managed model runs
remotely at the provider; repo-owned source/evaluation/control components stay
under the operator's deployment. No vendor/account/region/VM has been selected.

Existing [deployment templates](../../researcher/service/DEPLOYMENT.md) support
native/retrieval service processes and the shared-budget organization coordinator,
not a completed managed-session supervisor. The MCP-enabled ARM64 dependency
image built and passed an offline nonroot import/lock smoke; this did not run an
approved source release or a cloud service.
Systemd is the simplest initial process owner on a Linux VM. The Docker option
builds a dependency/runtime image and mounts a separate reviewed read-only source
clone plus a private writable state volume. Record both release and image identity.
SQLite must not be put on NFS, a shared object mount or ephemeral container storage.

Use a nonroot service identity, read-only reviewed release, pinned dependencies,
separate worker/operator secrets, explicit egress policy and resource limits.
The current UI reader requires loopback and the same network namespace; a Docker
bridge service name is not a supported substitute. Public exposure requires a
reviewed TLS and user-authentication layer, not a token in browser JavaScript.

Managed Postgres, Temporal, distributed workers and Kubernetes are alternatives
only when measured concurrency, availability or recovery requirements justify
their operational cost. No current measurement requires them. Optional MCP also
needs network containment: its bridge does not constitute a complete sandbox.

The original SQLite `backup` command is inspection-only. The implemented
[artifact-complete recovery bundle](../../researcher/runbooks/service-recovery.md)
captures the registered Store/capture/candidate closure and explicitly selected
managed ledgers, with source/configuration identity and exact file hashes. The
cumulative budget authority has a separate narrow closure. Restore requires a new
private destination and trusted manifest digest, verifies the closure, preserves
unknown effects/reservations and writes an already-paused Store; it starts no
worker and reads no credential. Unregistered files and credential files are
excluded, not copied recursively. This does not automatically include every new
pipeline or coordinator ledger. Original writers must be fenced and all
post-snapshot effects reconciled before any resumption. Encryption, off-host
retention, measured RPO/RTO, disk/queue alerts and secret-manager integration are
not provisioned by the current templates.

## 10. Staged launch gates

| Stage | Evidence required before advancing |
| --- | --- |
| G0: reproducible release | Clean approved source/dependency identity; deterministic suites, schema/inventory and repository gates; no private runtime or keys in export |
| G1: verified handoff | Real retained source scenario plus tamper/fault tests; exact replay-to-packet identity; preserved gaps; zero model effects during prepare |
| G2: supervised managed canary | Explicit spend containment and bounded single session; observed effective configuration; restart, cancellation, uncertain-create and failed-poll scenarios; no automatic resubmission |
| G3: independent improvement experiment | Frozen baseline/candidate; declared control/held-out tasks; verified execution receipts; complete failure/cost reporting; independently labeled scientific relevance |
| G4: reviewable delivery | Complete candidate overlay and corpus validators; separate publication approval; sandbox draft-PR/notification test; base drift and unknown-write recovery |
| G5: deployed service | Reviewed host/image/secret/ingress/egress configuration; unified operational view; alerting; artifact-complete isolated restore and rollback |
| G6: bounded recurrence | Explicit shared cumulative budget and stop conditions; real elapsed soak with outages/restarts; no duplicate effects or silently lost uncertain work |

Do not turn these into a completion percentage. A failed canary is evidence to
retain and convert into a regression test. Quantitative quality thresholds and
acceptable latency/cost must be agreed before tuning and evaluated on the declared
held-out population. Until then, the honest release position is a supervised
research workbench with bounded retrieval and developmental proposal workflows.

## Code and operator map

- [Service runbook](../../researcher/service/README.md), [daily retrieval](../../researcher/service/DAILY_RETRIEVAL.md), [managed canary](../../researcher/service/AGENTS_API.md).
- [Workflow/admission](../../researcher/service/workflow.py), [Store](../../researcher/service/store.py), [source adapters](../../researcher/service/retrieval_sources.py).
- [Discovery digest](../../researcher/service/context_digest.py), [primary context](../../researcher/service/primary_context.py), [corpus/citation contracts](../../researcher/service/knowledge.py).
- [Verified retrieval handoff](../../researcher/service/retrieval_handoff.py), [research brief/provenance contract](../../researcher/service/research_brief.py).
- [Managed compiler](../../researcher/service/agents_context.py), [session runtime](../../researcher/service/agents_runtime.py), [objective eval planner](../../researcher/service/agents_evals.py).
- [Cumulative Campaign](../../researcher/service/OPENAI_CAMPAIGN.md), [explicit research pipeline](../../researcher/service/RESEARCH_PIPELINE.md), [native/managed candidate review](../../researcher/service/CANDIDATE_REVIEW.md), [paused artifact recovery](../../researcher/runbooks/service-recovery.md).
- [Publication adapter](../../researcher/service/github.py), [operator API](../../researcher/service/api.py), [Control Center](../../apps/control-center/README.md).
- [Specification execution plan](spec-execution-plan.json): development planning and unassessed acceptance criteria, not promotion authority.
