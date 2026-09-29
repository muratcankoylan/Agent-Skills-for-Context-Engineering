# Codex SDK runtime migration

Status: target architecture and executable migration requirements, 2026-09-29. Not a production acceptance, merge recommendation, or authorization to spend. This document supersedes the runtime choice in earlier product plans, not their historical evidence or specification lifecycle.

Implementation update, later on 2026-09-29: the local integration now contains the
pinned worker, buffered budget gateway, SDK research/evaluation callers, durable
origin verification, strict recovery and private operator status. See the
[runtime runbook](../../researcher/service/CODEX_SDK.md). The audit snapshot below
is retained as the original gap analysis, not current implementation status.
Real SDK tests against synthetic upstreams establish wiring, not live research
quality. Native tools, cloud activation, UI reconciliation and paid effectiveness
evidence remain separate requirements; the entire migration is not declared done.

## Decision and completion boundary

The product is a standalone, open-source research organization whose production agents run through the **Codex SDK**. It continuously collects research, constructs source-bound context, investigates mechanisms, critiques hypotheses, proposes scoped skill changes, and tests frozen candidates before preparing a reviewable proposal. The Codex desktop app is optional. Neither desktop automation nor a custom Python Responses loop is the target agent runtime.

“All agents use the SDK” includes researcher, critic, skill editor, any model-based evaluator, and the task-solving agents used in independent effectiveness experiments. Installing the SDK, wrapping an unchanged native role loop, or adding one SDK canary does not satisfy this requirement. Deterministic retrieval, scheduling, accounting, replay, freezing, scoring, and publishing do not need to become agents.

At this audit snapshot, production-shaped callers still select native model adapters or the separate managed Agents API. SDK worker and budget-gateway implementation is in progress; their eventual presence is not evidence that all callers have migrated. Existing tests and live receipts retain their actual backend labels. There is no measured SDK skill-effectiveness result or completed SDK production soak established by this document.

## Runtime choice and verified external contracts

The official Python package `openai-codex` is described as stable and controls a local Codex app-server over JSON-RPC. Published builds include a pinned CLI runtime dependency; an explicit `codex_bin` override is a separate runtime choice. This fits the existing Python coordinator without a second TypeScript service. Lock the selected package and runtime, record their effective identities, and test that exact combination. The TypeScript SDK is a credible alternative, but requires an additional process/language boundary here. [Official Codex SDK documentation](https://learn.chatgpt.com/docs/codex-sdk).

App-server is the richer client protocol for authentication, history, approvals, and events; SDK is the documented choice for jobs and CI. Keep SDK-owned stdio private. Do not expose app-server directly as a replacement for the authenticated operator API: its WebSocket transport is documented as experimental and unsupported for production. [Official app-server documentation](https://learn.chatgpt.com/docs/app-server).

Custom Codex providers can route to a configured base URL, but project-local configuration cannot set provider/authentication overrides. Use a dedicated private worker home, not the developer's home or untrusted repository config, to select the gateway. A Responses-compatible wire protocol inside the SDK is not the same thing as a hand-written Responses agent loop. Native Anthropic or Gemini adapters are not automatically compatible with this interface. [Official advanced configuration](https://learn.chatgpt.com/docs/config-file/config-advanced).

Provider request and stream retries are separate settings with nonzero documented defaults. Explicitly configure and test the selected retry policy; never assume one SDK turn means one HTTP request. The gateway must account for every request it actually admits, including retries or agent continuations. [Official configuration reference](https://learn.chatgpt.com/docs/config-file/config-reference).

The official `openai/codex-action` installs the CLI and runs `codex exec`; with an API key it starts a Responses proxy. It is not this repository's SDK coordinator or durable budget authority. A production GitHub workflow should invoke our reviewed SDK entrypoint and authority/recovery path. The official action can remain a separately authorized review tool, not an alternate path around those controls. [Official GitHub Action documentation](https://learn.chatgpt.com/docs/github-action).

## Smallest coherent architecture

```text
timer / authenticated command / reviewed CI dispatch
  -> repo coordinator + durable Store + source admission
  -> bounded collectors -> captured bytes -> verified context and primary spans
  -> SDK researcher -> deterministic grounding -> SDK critic -> SDK skill editor
       each SDK provider request -> local gateway -> same cumulative authority
  -> exact edit -> frozen candidate -> trusted overlay validators
  -> fresh SDK evaluation threads -> deterministic grading / calibrated review
  -> report + proposal outbox -> separately authorized draft PR / notification

operator API/UI: inspect, pause, reconcile, approve scoped external actions
telemetry: closed metadata only; never the authority or recovery ledger
```

Use one coordinator and one writable SQLite authority on persistent local disk initially. Isolated SDK workers are bounded children, not additional schedulers. The gateway alone holds the model-provider credential. Source connectors and the publisher have separate scoped credentials and effect contracts. No agent owns the budget database, accepted corpus, deployment configuration, or GitHub write credential.

Reuse the verified evidence bundle across research and evaluation preparation. A parallel SDK-specific crawler would duplicate provenance, freshness, spending, and replay logic. Conversely, a wholesale replacement of deterministic infrastructure would discard existing failure tests without proving better research. The required change is substantial at the execution boundary, but narrow at the source and authority boundaries.

## Current caller inventory and required changes

Paths below are source locations, not assertions that migration has shipped. Function names are useful anchors while line numbers change.

| Surface and current entrypoints | Existing behavior to preserve | Required SDK completion proof |
| --- | --- | --- |
| [`__main__.py`](../../researcher/service/__main__.py), `Workflow` construction, `work` / `serve` | Explicit configuration, private state, bounded admission, operator pause | Production selection reaches only the SDK role executor; native execution is not an implicit default or fallback. |
| [`organization.py`](../../researcher/service/organization.py), `Organization.cycle`, `_run`, `serve` | UTC slots, source pause, at most one research admission per cycle, durable job outcomes | A real scheduled and a manual source job traverse the same SDK pipeline after restart; no desktop scheduler required. |
| [`research_pipeline.py`](../../researcher/service/research_pipeline.py), `run_pipeline` | Source/config/corpus/dataset binding; phase receipts; abstention; commit-gap recovery | Backend/runtime identity is frozen before effects; research and evaluation use SDK tasks; terminal replay makes no new calls. |
| [`workflow.py`](../../researcher/service/workflow.py), `ask`, `execute`, `drain` | Researcher, critic, skill-editor roles, prior-feedback isolation, exact edit validation | Replace every native `ask`, including both evaluator-order calls. Retire or quarantine the weaker paired-pilot publication path behind the common candidate/evaluation gates. |
| [`openai_campaign.py`](../../researcher/service/openai_campaign.py), `Campaign.call`, `research`, `evaluate`, CLI | Existing cumulative authority, pre-effect reservation, citation validation, complete failure accounting | Role execution uses SDK workers; each admitted SDK wire request uses the same authority. Existing native records remain distinguishable and replayable. |
| [`providers.py`](../../researcher/service/providers.py), `complete`; [`model_worker.py`](../../researcher/service/model_worker.py), `bounded_complete` | Bounded transport, credential discipline, timeout quarantine | Not reachable as a production agent executor after cutover. Explicit archival/controlled comparison only; transport reuse must not recreate the native agent loop. |
| [`retrieval_handoff.py`](../../researcher/service/retrieval_handoff.py), `verified_bundle`, `prepare_from_retrieval` | Capture/primary replay, exact report reconstruction, freshness and complete-source gates | Compile the same verified bundle into SDK tasks without fetching it again. Preserve omissions, partial coverage, and parent-to-primary links. |
| [`agents_context.py`](../../researcher/service/agents_context.py), [`citation_spans.py`](../../researcher/service/citation_spans.py), [`knowledge.py`](../../researcher/service/knowledge.py) | Bounded corpus/evidence packing and exact source-span selectors | SDK receives inert evidence, not source instructions. Version changed envelopes; source and citation identities survive projection. Literal grounding remains narrower than scientific truth. |
| [`retrieval_sources.py`](../../researcher/service/retrieval_sources.py), [`primary_context.py`](../../researcher/service/primary_context.py), [`context_digest.py`](../../researcher/service/context_digest.py) | Registered arXiv, company, HN, X, OpenAlex collection; bounded primary profiles; replay | Remain deterministic. Demonstrate source credentials and paid-source reservations cannot be accessed or bypassed by SDK workers. Discovery is not full-text evidence. |
| [`mcp_tools.py`](../../researcher/service/mcp_tools.py), [`mcp_worker.py`](../../researcher/service/mcp_worker.py) | Registered read-only tools and bounded results | Explicit reviewed SDK tool grants route through existing capture/effect policies; no ambient MCP servers or arbitrary tool discovery. Tool-free first slice is not full MCP migration. |
| [`candidate_review.py`](../../researcher/service/candidate_review.py), `review_candidate`, `review_managed`; `Workflow.freeze`, `frozen_text` | SPEC-003 freeze, exact edit, trusted overlay validation, derived inventory receipts | Verify SDK result origin and digest before review. Validators read frozen bytes. Keep managed-result verification for old records, not as an SDK alias. |
| [`agents_evals.py`](../../researcher/service/agents_evals.py), `build_plan`, `task_request`, `make_result`, `compare_results` | No-skill/current/candidate arms; gold-free requests; objective scoring; missing failures | Every live task uses a fresh SDK thread and isolated context. Bind backend/thread/turn/runtime to each result and recompute grades; no researcher access to held-out labels. |
| [`store.py`](../../researcher/service/store.py), `reserve`, `recover`, `prior_feedback`, `candidate_seen` | Single accounting plane, unknown effects consume capacity, same-baseline bounded memory | Add typed SDK effect/turn records without resetting budgets or adding accepted-knowledge authority. History is visible to research only, never an evaluation answer key. |
| [`agents_runtime.py`](../../researcher/service/agents_runtime.py), `SessionLedger`, `ManagedResearch`, CLI; [`openai_agents.py`](../../researcher/service/openai_agents.py) | Separate managed session create/observe/watch/cancel and unknown-create protection | Disable new production managed submissions after cutover. Retain explicit old-session inspection/cancellation; never convert session IDs into SDK thread IDs. |
| [`recovery_bundle.py`](../../researcher/service/recovery_bundle.py), `snapshot`, `restore` | Complete private authority backup, strict schema checks, no empty-state recovery | Add SDK authority/turn/session files with closed validation; recover in a new directory with no duplicate provider effect. Managed/native backup tests do not establish SDK recovery. |
| [`tracing.py`](../../researcher/service/tracing.py), [`trace_cli.py`](../../researcher/service/trace_cli.py), [`managed_traces.py`](../../researcher/service/managed_traces.py) | Closed metadata, token accounting, durable export attempts, telemetry failure isolation | Project SDK events with honest completeness and backend labels. Do not relabel the managed trace reader or publish prompts, tool payloads, keys, or raw private paths. |
| [`api.py`](../../researcher/service/api.py), [`apps/control-center`](../../apps/control-center) | Loopback authenticated service API and server-side status/artifact readers | Show actual SDK backend, thread/turn state, reservations, unknown effects, frozen candidate and pending evaluation. Add scoped operations and tests; fixture pages are not operational UI. |
| [`deploy/launch.py`](../../researcher/service/deploy/launch.py), [`deploy/Dockerfile`](../../researcher/service/deploy/Dockerfile), systemd templates | Clean release identity, nonroot processes, private persistent state, one writer | Pin/install SDK and CLI runtime in the image; run the SDK coordinator rather than the old native command; test restart, stop, isolation, rollback and restore on Linux. |
| [Release rehearsal workflow](../../.github/workflows/release-rehearsal.yml), [`release_scenarios.py`](../../researcher/service/release_scenarios.py) | Secret-free PR CI, bounded scenarios, sanitized aggregate artifacts | Add real installed-SDK tests against an injected local provider. A separate protected workflow may invoke the SDK coordinator; rehearsal remains non-production and credential-free. |
| [`github.py`](../../researcher/service/github.py), `publish_proposal` | Explicit GitHub enablement, exact base/candidate binding, draft PR, no auto-merge | Publisher consumes the evaluated proposal under separate approval. SDK cannot publish directly. Requested reviewers are not a general delivery/notification service. |
| [`benchmarks/sdk-runner`](../../researcher/benchmarks/sdk-runner), [`PLAN.md`](../../researcher/benchmarks/PLAN.md) | Historical Cursor results; current zero-call Stage 2/3 planners | Keep the live block. A new SDK benchmark needs its own approved executor, frozen epoch, containment and canary; do not relabel May results or dry-run plans. |
| [`research_experiment.py`](../../researcher/scripts/research_experiment.py), [`research_evolution.py`](../../researcher/scripts/research_evolution.py) | Pure finite packet-policy evaluation and private proposal records | Remain deterministic; changing them into agents would not satisfy a missing runtime requirement. Their compactness scores are not skill effectiveness. |

Repository examples are a separate, visible boundary. [`examples/interleaved-thinking`](../../examples/interleaved-thinking) contains native Anthropic/MiniMax agent calls; [`examples/llm-as-judge-skills`](../../examples/llm-as-judge-skills) contains AI SDK model execution. Either migrate an example when it is promoted into the supported product, or label and isolate it as a non-production teaching example. Do not describe every historical example as SDK-based. Credential diagnostics such as model-list GET requests are not agent execution.

## Required execution contracts

These are design requirements for the implementation, not newly accepted shared schemas.

1. **Immutable task.** Bind role, backend `codex_sdk`, exact model/reasoning configuration, SDK/runtime identities, effective permission/config digest, prompt/output-schema digest, source/corpus references, and applicable candidate/evaluation item before execution. Keep paths, credentials, gold labels, and authority-granting objects out of model-visible task data.
2. **Origin-verifiable receipt.** Record local thread/turn identity, task digest, admitted effect IDs, output digest, terminal state, usage availability, and cancellation/reconciliation status. Preserve the distinction between output obtained, locally validated, independently evaluated, and approved. A JSON object that merely claims an SDK backend is not proof.
3. **One spend authority.** The gateway uses the existing Campaign Store/config and lifetime cap, not a new funded account. Admission is per actual provider HTTP request with the configured one-request job limit. Hold the authority worker lock across recovery, reserve, dispatch and receipt commit. Commit the effect receipt before forwarding terminal stream completion. Reservations are conservative forecasts, not a provider-side dollar guarantee.
4. **Unknown turn quarantine.** Persist a turn/effect tombstone before dispatch. Any unknown request blocks successor requests for that turn, including SDK internal retries. A restart cannot allocate a fresh identity to escape it. Resume a known local thread only when the recorded turn disposition permits it. Cancellation, process death, missing output, and transport timeout never imply no charge.
5. **Credential and host isolation.** SDK receives only a narrowly scoped local gateway capability, never the provider or GitHub key. Use a private worker home and minimal environment, disable ambient tools/settings/authentication discovery, and explicitly constrain filesystem and network access. Read-only sandbox mode alone is not proof that held-out labels or unrelated host files are unreadable. Test containment against real pinned runtime behavior.
6. **Tools remain grants.** Default first-slice tools off; later enable only registered read-only retrieval/MCP with independent cost and capture policies. Reject unexpected tool requests and permission escalation. Candidate code execution, unrestricted shell access, arbitrary network fetches and writes to the real checkout are separate capabilities, not implied by using Codex.
7. **No authority in model output.** Strict role schema and citation validation precede later paid roles. Abstention is a valid terminal outcome. Frozen candidates pass overlay validators and the declared independent evaluation before a separate publisher considers them. A critic recommendation, self-reported score or model-generated test result cannot advance acceptance.
8. **Exact recovery.** Source, config, implementation, runtime, dataset and frozen bytes must match before resumed effects. Preserve valid result artifacts when terminal bookkeeping fails. Quarantine incomplete or conflicting artifacts; do not repair by initializing an empty authority or rerunning a paid turn.

## Requirement-to-proof checklist

Every row remains a release gate until its own evidence exists. Reusing an implemented deterministic component does not mark the whole requirement complete.

| Requirement | Reusable implementation | Evidence required for SDK release |
| --- | --- | --- |
| All supported agent roles use SDK | Role prompts, strict schemas, pipeline phases | Caller inventory test plus actual installed SDK subprocess tests; no direct native/managed agent call reachable from production commands. |
| Research operates on real captured sources | Collectors, replay, primary/context projections | Bounded fresh-source canary through SDK research with source/primary IDs and omission/freshness records; failures preserved, not silently replaced by fixtures. |
| Useful knowledge transfer, not only citation formatting | Corpus retrieval, exact span validation | Preregistered held-out task outcomes with controls; separate exact-grounding measures from semantic correctness and transfer. |
| Candidate is immutable and scoped | CandidateFreezer, overlay validators | SDK result-to-candidate provenance, tamper tests, validator receipts, unchanged forbidden surfaces, safe failure/abstention. |
| Independent evaluation is actually independent | Pure paired plan and deterministic grader | Fresh SDK threads, no label/history exposure, fixed task/runtime manifests, all planned failures counted, blinded calibrated labels where objective grading is insufficient. |
| Costs remain within admitted authority | Transactional Store reservations | Multiple SDK requests, retries, concurrent attempts, clock changes and timeouts cannot bypass cumulative limits; unknown usage never becomes zero. |
| Restart does not repeat external effects | Native/managed recovery patterns | Kill at every SDK/gateway boundary, restore elsewhere, prove no resend; distinguish pre-effect snapshot from a snapshot stale after an external effect. |
| Scheduled cloud operation is repo-owned | Foreground Organization and service templates | One persistent deployment exercises timer/manual triggers, source/provider outage, pause, signal shutdown, bounded queues, rollback and complete restore. |
| Operator can understand and intervene | Authenticated API, service and observation pages | Real SDK job inspection and scoped pause/cancel/reconcile actions; unknown versus stopped visible; no secrets in client bundle or public artifacts. |
| PR and notification actions are controlled | Draft publisher and effect wrappers | Evaluated artifact/base binding, duplicate prevention, permission-denied and ambiguous-send tests; human merge boundary; explicit notification delivery receipts. |
| Traces support failure-to-eval learning | Closed local telemetry and export journal | Correlate SDK role/turn/effects without content leakage; telemetry outage cannot change execution outcome; important failures become deterministic regressions. |
| Portable reproducibility | Clean-release launcher, locked Python/image inputs | Fresh Linux install/build and SDK/runtime identity, license/dependency record, private-state restore, documented credential-free rehearsal and operator prerequisites. |
| No scientific or governance overclaim | Spec validator, benchmark methodology | New runtime epoch, complete failure/cost accounting, unchanged historical reports, no implied accepted specification or automated promotion. |

## Ordered delivery and rollback

### 1. Prove the SDK boundary and gateway

Implement the pinned SDK worker and local gateway, initially one tool-free role and concurrency one. Exercise the real installed SDK against a fake local provider, not only a fake SDK class: strict outputs, extra requests, partial streams, retry attempts, interrupted turns, wrong capabilities, malicious local configuration and credential containment. Preserve deterministic fixtures as fixtures. The rollback is disabling new SDK admission; old uncertain effects remain quarantined.

### 2. Migrate the actual research callers

Wire researcher, critic and editor through the same task/receipt interface in both the foreground organization pipeline and any retained direct workflow command. Reuse `verified_bundle`, span selectors and existing prompts where their semantics match. Route every SDK request through the original authority. Remove implicit native/managed fallbacks from supported production configuration. Only then can the product claim an SDK research loop, still without independent effectiveness proof.

### 3. Close candidate and evaluation paths

Add SDK receipt verification to candidate review; carry exact frozen bytes into fresh SDK evaluation threads. Reuse the three-arm objective plan, but version runtime-specific identity and isolation contracts. A supplied synthetic dataset proves integration only. A held-out dataset requires independently authored labels, exposure accounting and task-based grouping; seed/replications alone do not prove independence. Preserve abstention, parse failure, timeouts and incomplete rows in denominators.

For research claims follow the [benchmark methods plan](../../researcher/benchmarks/PLAN.md) and [paper protocol](portable-harness-paper-protocol.md): development/selection/sealed-final split, task-group variance and power pilot, predeclared stopping/multiplicity, cost-matched incumbent/archive/random-search baselines where applicable, and complete costs/failures. Compare new runtime conditions in a new epoch. Do not pool native, managed and SDK results as interchangeable replicates.

### 4. Make recovery, operators and deployment SDK-aware

Extend closed backup schemas before enabling durable SDK work. Bind local thread storage and gateway authority together without exporting credentials or telemetry as authority. Finish the real API/UI status and stop/reconciliation path. Build the locked SDK/runtime into the nonroot image and verify the systemd/container command reaches it.

The first reference topology is a single persistent Linux host/container with persistent local disk. No billable provider, region or machine is selected here. A protected GitHub workflow can dispatch to that coordinator or run a bounded SDK task with complete authority restoration and exclusive ownership. An ephemeral runner cannot replace persistence by uploading only a final answer. Never run secret-bearing production jobs on untrusted PR code; retain the separate secret-free release rehearsal.

### 5. Bounded live validation, then elapsed observation

After the offline gates, obtain explicit live authorization and use the existing cumulative cap for one source-to-research-to-candidate/evaluation pilot. Do not add another authority or broaden tools to obtain a successful result. Record a truthful abstention or rejected candidate as such. Expand only with measured value/cost and operational reliability. A compressed 30-day slot simulation demonstrates scheduler behavior, not 30 days of production uptime or scientific yield.

## Documentation, specifications and release boundaries

The current numbered specification set has 27 files: SPEC-000 through SPEC-003 are `amended`, and SPEC-004 through SPEC-026 are `draft`, all at revision 1 at this audit. This document changes none of those states and grants no default-branch authority.

| Existing statement or artifact | Required follow-up, not silently completed here |
| --- | --- |
| [SPEC-014](../specs/SPEC-014-runtime-hermes.md) and [SPEC-025](../specs/SPEC-025-deployment-durable-workflows.md) select managed Agents API as primary and say Codex is not runtime | Review their draft decisions, acceptance criteria and titles against SDK dependency versus optional desktop distinction. Preserve portable artifacts, cancellation, containment and durable deployment requirements. |
| [SPEC-005](../specs/SPEC-005-work-orders.md), [SPEC-016](../specs/SPEC-016-evaluation-registry.md), [SPEC-024](../specs/SPEC-024-private-control-plane.md) | Reuse work-order, evaluation-epoch and authority boundaries; clarify historical laptop/Hermes assumptions where relevant, without making runtime threads the source of authority. |
| [Machine execution plan](spec-execution-plan.json) | Reconcile exact source digests and changed criteria only after reviewed spec edits; retain `unassessed` states and honest verification methods. |
| [Earlier Agents architecture](openai-agents-research-architecture.md), service runbooks, cloud plans and app README | Mark earlier backend/deployment directions as superseded and add the actual SDK entrypoint once implemented. Preserve dated measurements and explicit compatibility commands. |
| Managed packet/result/recovery schema names | Add versioned SDK identities; do not reinterpret existing artifacts or overwrite old manifests. |
| Published router reports and private native/managed run receipts | Keep unchanged and attributable to their actual source/runtime. They are not evidence of SDK migration. |

The current PR refresh has two distinct release tracks. Foundation/governance and narrow maintenance repairs can be reviewed and stacked on their own exact heads, with their own tests. For example, installer containment, agent-frontmatter compatibility and calculator parsing fixes do not require waiting for agent-runtime migration. They also do not prove SDK readiness. The existing managed transport PR and its tests remain useful historical/compatibility work, not the new primary runtime by renaming.

The SDK implementation series must contain the worker/gateway, caller migration, independent evaluation/provenance, recovery/operators, and deployment validation changes described above, with explicit dependencies and exact-head receipts. Neither this plan nor the maintenance patch package means every open PR is merge-ready. Remote author ownership, stale bases, CI, review, dependency order and the user's push/merge authorization remain separate checks.

## Review evidence and limits

This document is based on static inspection of the linked integrated sources, the benchmark plan, current draft spec headers and official documentation. It adds no model call, scheduler activation, deployment, PR mutation or new benchmark result. The SDK implementation is being developed separately; record its actual executed tests and release identity in a dated verification receipt rather than retroactively changing this audit into a completion claim.
