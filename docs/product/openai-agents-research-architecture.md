# A repo-owned research organization on the OpenAI Agents API

Superseded runtime direction, 2026-09-29: new research/evaluation execution uses
the [Codex SDK](../../researcher/service/CODEX_SDK.md). This document preserves the
earlier managed-backend design and research protocol. New built-in managed
submissions are retired; retained session observation/cancellation remain. It
does not describe the current primary caller path.

This is an implementation and research protocol, not a launch approval or an
empirical effectiveness paper. It supersedes the native-model
loop as the preferred product runtime in `cloud-research-service.md`. Historical
results remain historical. The specification lifecycle is unchanged.

## Abstract

The objective is a public, inspectable context-engineering research organization
that discovers evidence, proposes changes to reusable agent skills, evaluates
those changes on tasks independent of their authors, and submits reviewable pull
requests. The objective is not autonomous activity, output volume, or dependence
on a developer's desktop. We adopt OpenAI's managed Agents API for model/tool
execution and conversational state, while retaining repository-owned evidence,
experimental design, permissions, candidate identity, and publication controls.
This document specifies the boundary, reports the implementation scope, and
defines experiments required before claiming that the organization improves
itself. No new live-model effectiveness result is claimed here.

## 1. Research questions and alternatives

The important uncertainty is whether managed context maintenance and delegation
improve task-level research utility enough to justify their costs and reduced
control over the runtime. More agents are not the success criterion. The primary
outcome is independently validated skill utility per unit of total operating cost.

Three credible architectures were considered:

| Architecture | Advantage | Cost and limitation | Decision |
| --- | --- | --- | --- |
| Application-owned native Responses loop | Explicit requests and per-response output ceilings; direct provider comparisons | We own compaction, delegation, tool coordination and recovery | Retain as a separately measured fallback/control, not the new primary runtime |
| OpenAI Agents SDK inside our service | Application deployment and agent-loop control; reusable agents/tools | We still own long-lived process/session infrastructure | Useful when hosted-state or residency constraints rule out the managed API |
| Managed Agents API plus our research control plane | Managed sessions, context maintenance and optional parallel research | Public beta; hosted state; asynchronous execution and incomplete cost visibility | Preferred direction, introduced through a data-only canary |

OpenAI distinguishes these products explicitly. The new API operates a managed
Codex harness; it is not a Codex desktop task, scheduled chat, or the older SDK.
The application still submits work, connects product tools, and receives results.[^1]
The launch announcement identifies this release as a public beta.[^2]

Engineering judgment: keep one small application coordinator. Do not introduce
Temporal, a message bus, a vector database, or an agent framework merely because
the task is long-running. Adopt additional infrastructure only after measured
restart, throughput, retrieval-quality, or multi-host requirements justify it.

## 2. Ownership and authority

```text
Repo scheduler / operator / approved issue
                  |
                  v
Evidence capture -> frozen context packet -> managed research session
       |                    |                  / root + optional subagents
       |                    |                 v
       +----------- provenance checks <- structured proposal
                                                |
                                                v
                         frozen candidate -> independent task evaluation
                                                |
                                                v
                         policy / export gates -> GitHub draft PR + notification
                                                |
                                      human review and merge
```

OpenAI owns the model/tool loop and conversational session. Our application owns
work admission, the exact inputs sent, local-to-remote identity, evidence artifacts,
comparison plans, candidate freezing, output validation, and external publication.
The repository is the source of truth for accepted skills. Neither an agent's
message nor a cloud session becoming idle changes that source of truth.

Managed subagents are collaborators within one trust domain. They are not
independent security principals: the documented defaults include inherited MCP
configuration and a shared environment. Native subagents do not support application
function tools. Tool-isolated evaluators therefore require separate sessions and
separate input/credential policies, not a prompt saying “be independent.”[^3]

The first managed implementation uses `environment.type=none`, no tools, no vaults,
and an explicit subagent concurrency limit. Zero is the initial default. This
allows us to measure context transfer and proposal validity before giving the
runtime network or executable workspace capabilities.

## 3. API contract and recovery

The adapter targets the documented `/v1/agents/sessions` surface and the
`OpenAI-Beta: agents=v1` header. The official SDK entry is
`client.beta.agents.sessions`, not the `openai-agents` package. We use a narrow,
stdlib HTTP boundary initially so the protocol tests do not depend on an
unverified minimum SDK release.[^4]

The local state transition is:

```text
prepared -> submitting -> running -> completed / failed / cancelled / invalid_output
                  |          |
                  +----------+----> reconciliation_required
```

Before create, persist the packet digest, submission intent, observation deadline,
and exactly-one-attempt identity. After create, persist the remote session ID
before interpreting other response fields. A lost create response cannot be
treated as a failed job eligible for another create. The initial implementation
quarantines that case; operator adoption of a discovered session is not yet built.

An idle session is not proof of successful work. The observer requires a completed
root turn, terminal subordinate turns, and a validated final-answer item belonging
to that root turn. It rejects unexpected application actions rather than executing
them. Failures in subordinate work remain visible.[^5]

Streams are live observations, not a replayable durable log. Our first observer
uses bounded pagination over saved turns and items. Future streaming UI recovery
must buffer a new stream while rebuilding saved state, not invent an event cursor
that the API does not provide. Missing intermediate coordination messages must
remain missing in research traces.[^6]

Cancellation is a request to stop the active turn. The event endpoint documents
an idempotency header, but this is not a documented session-create guarantee.
We persist one cancellation intent and observe the result; an HTTP acknowledgement
is not a terminal-state receipt. Local process death, timeout, and deployment pause
do not establish that remote execution stopped.[^7]

## 4. Evidence sourcing and context transfer

The existing local evidence collectors remain reusable research infrastructure.
arXiv discovery provides titles/abstracts and versioned source identities; company
feeds provide a recent window, not semantic completeness. X requires an explicit
provider account and allowed endpoint. No model should silently invent a provider,
assume platform search access, or treat an inaccessible source as negative evidence.

For each lane, preserve query, source version, retrieval time, outcome, retained
bytes and parser version. Discovery summaries are leads. A claim about experimental
methods or an effect size needs the corresponding primary source, not just its
abstract. Separate source credibility, methodological support, relevance, novelty,
and applicability; do not reduce them to one undocumented weighted score.

The managed context compiler takes the exact selected skill baselines and validated
evidence records. It checks hashes, UTF-8 byte spans, excerpt identities, duplicate
source IDs, and a total 128 KiB request-body ceiling. It retains the existing
retrieval omission map. URLs and arbitrary source metadata are kept in the local
provenance map rather than copied indiscriminately into model context.

The output contains research claims, a critique, and at most one scoped edit.
Every claim carries literal evidence references. Hashes and literal quote checks
establish identity and textual grounding, not authenticity or semantic entailment.
The editor cannot alter skill frontmatter or the activation/integration boundaries.
It returns data; it does not write the repository or run a proposed command.

For production, expose progressive retrieval through a small application broker:
search registered sources, read a captured excerpt, read a selected skill, and
submit a candidate artifact. The broker must bind each call to the work order,
source budget, destination and evidence receipt. Native MCP is appropriate only
when the server's exact tool set and effects have been reviewed. The Agents MCP
schema differs from Responses MCP; omitted `allowed_tools` must not become a
convenient way to grant every tool.[^8]

A skill/plugin bundle is a future context-delivery treatment, not an excuse to
mount the dirty developer checkout. Hosted environments should materialize only a
reviewed public artifact closure. Network policy must be explicit because hosted
sandbox networking is not default-deny. GitHub write credentials, application API
keys and evaluator gold answers never belong in that workspace.[^9]

## 5. Self-improvement without self-certification

The organization improves through a controlled learning loop:

1. Capture an observed failure or a falsifiable research hypothesis.
2. Turn it into a reproducible task with a locked outcome definition.
3. Generate a bounded candidate against an immutable baseline.
4. Evaluate the candidate outside the author's session and memory.
5. Retain accepted, rejected, inconclusive and failed outcomes.
6. Propose a publication containing the evidence and limitations.

The research critic is useful for finding unsupported claims before expensive
evaluation. It is not an independent judge. A majority vote among subagents sharing
the same evidence and model does not create additional independent evidence.

Accepted knowledge transfers across runs through versioned mechanism and claim
records. A cloud conversation is working memory, not the mechanism registry.
Compaction should preserve the current task; it cannot establish institutional
truth. Failed proposals remain discoverable so the system does not repeatedly
pay to rediscover the same unsuccessful change.

Promotion remains a separate owner operation. A successful managed run is still
`awaiting_independent_evaluation`. No executable path in this new slice merges a
PR, changes a policy, deploys itself, or marks a scientific claim accepted.

## 6. Evaluation protocol

### Units and controls

The initial paired design uses fresh sessions for three conditions: no skill,
the current skill, and the candidate skill. Hold model, task, evidence, output
contract and sampling policy fixed. Randomize condition order within each
task-replication block with a recorded seed. Bind every result to the complete
plan and item digest. Gold answers are absent from task prompts.

The deterministic scorer measures evidence-ID selection, literal quote grounding,
appropriate abstention and exact scoped edits on tasks with explicit golds. These
are narrow, reproducible outcomes, not a semantic-research-quality score. Public
fixture success must never be relabeled as performance on unseen tasks.

### Ablations and hypotheses

| Hypothesis | Comparison | Primary observation |
| --- | --- | --- |
| H1: structured evidence transfer reduces attribution loss | Raw text vs provenance-linked packet, same evidence | Wrong/missing evidence references per task |
| H2: progressive retrieval improves useful context efficiency | Full selected context vs budgeted retrieval | Task success and total input/tool bytes, including omissions |
| H3: delegation is worth its overhead | One managed agent vs two subordinate researchers | Paired success, wall time and total recorded usage |
| H4: a skill change improves behavior | No-skill/current/candidate conditions | Task-level candidate-minus-baseline effect |
| H5: retained failures reduce redundant work | Memory absent vs bounded failure ledger | Repeated rejected proposals and total cost |

These hypotheses are untested by the new live runtime at document creation.
Use development tasks for iteration, a sequestered validation set for selection,
and an untouched final test set for the paper. Split related tasks and source
families together to reduce leakage. Time-split volatile research topics.

Report all submitted attempts, malformed outputs, timeouts, unavailable sources,
unresolved costs and cancellations. Missing rows are failures of coverage, not
permission to average only successful outputs. Publish per-task effects and paired
uncertainty, cluster repeated trials by task, and distinguish exploratory sweeps
from the preregistered final comparison. A fixed seed makes plan order reproducible;
it does not make model output deterministic.

Promotion thresholds need pilot-based power and cost analysis, then freezing before
the final test. Do not invent a statistically supported threshold from fixture
accuracy. Mechanistic negative controls include fabricated quotations, stale
versions, impossible questions, source outages, prompt injection, no-op edits,
scope violations and evaluator contamination.

## 7. Costs, privacy and model changes

The session API exposes best-effort, nullable usage that may change. Count root
and subordinate work; do not add overlapping session and turn totals. Reasoning,
cached inputs, cache writes where applicable, tool use, sandbox compute and third-
party sources can all affect the bill. Recorded token counts are not an invoice.[^10]

No hard per-session spending or total-turn parameter was established in the
reviewed create contract. Therefore the old `ModelRequest` reservation formula is
not reused for managed sessions. The prototype caps create attempts and local
observation, requests cancellation on deadline, and requires explicit live/cost-risk
acknowledgement. Those are useful controls, not a monetary guarantee.

Before recurring deployment, configure and independently verify an isolated
project's hard monthly spending limit. Alerts alone do not stop traffic; hard-limit
enforcement can still slightly overshoot while it propagates. Do not give an admin
key to the research agent merely to automate billing configuration.[^11]

The documented Agents API currently stores session state, supports US data
residency and is not ZDR-eligible, including with a self-hosted sandbox. Upload
only approved research data and implement explicit retention/deletion procedures.
Do not describe this path as a no-retention private model call.[^12]

Use an explicit model ID and record observation date, request configuration,
returned model ID and runtime/API version. The reviewed GPT-6 Astra model page
lists `gpt-6-astra`; this is not evidence of a separately selectable immutable
dated snapshot. Test upgrades in a shadow comparison rather than automatically
moving the release to whatever model is newest.[^13]

## 8. Deployment and interaction

Recommended first topology: one Linux application host with private persistent
storage, an authenticated operator surface and a narrowly scoped GitHub App.
The managed agent runs in OpenAI's service. Only a later coding treatment needs
an isolated hosted or self-hosted execution environment. Cloud vendor, region,
volume encryption and recurring spend require a reviewed deployment manifest.

The existing service's cron-equivalent admission is repository code, not a Codex
automation. A production scheduler will create work orders; the session adapter
will start or observe remote work. The current managed canary CLI is deliberately
not wired into unattended admission until spending, stop/recovery and owner-contract
gates pass. The existing native-provider service remains available as a separate
preview and does not silently switch backends.

Results must appear as a run dossier: source coverage, candidate diff, independent
task results, missingness, costs, remote status, and required operator action.
GitHub notifications should link to that dossier and use a durable delivery key.
The current control-center service page does not yet display this new managed
session ledger. CLI `status`, `observe`, `watch` and `cancel` are the current
operator interface for the managed slice; hosted UI integration is a launch gate.

## 9. Rollout and release gates

| Gate | Required evidence | Current managed-slice scope |
| --- | --- | --- |
| G0: contract conformance | Exact wire fixtures, unsafe-input and timeout tests | Implemented tests; see run receipt for execution |
| G1: session lifecycle | Crash-after-intent, lost response, paginated recovery, cancellation races | Implemented deterministic drills; real API unverified |
| G2: live smoke | Scoped key, one approved session, result recovery, recorded usage | Blocked on credential and cost-control verification |
| G3: scientific utility | Independent paired tasks, failures included, held-out results | Planner/scorer implemented; live study not run |
| G4: evidence and publication | Capture replay, frozen candidate, export and GitHub App canary | Existing primitives; managed integration incomplete |
| G5: operations | Authenticated UI, unattended recovery, complete restore, notification drill | Not established for managed runtime |
| G6: launch | Reviewed commit/image/config, human activation, monitored canary | Not authorized by passing local fixtures |

Keep each change reviewable: adapter first; context/session integration second;
evaluation third; tool broker fourth; hosted operator/deployment fifth. Existing
specification PRs retain their dependency chain. Do not force-push the chain or
publish every untracked local artifact to make the launch look complete.

## 10. Limitations and next decisive experiment

The initial slice intentionally cannot perform open-ended web research, run
candidate code, accept a mechanism, publish a managed result automatically, or
prove ongoing cloud cost containment. The adapter does not implement the full
Agents API. Polling recovers persisted results, not a complete reasoning trace.
Per-directory submission identity is a canary boundary, not a global production
admission ledger. The two stores are explicitly developmental, not competing
sources of production authority.

The next decisive experiment is one environment-free session using a frozen
public evidence packet, followed by a real disconnect/recovery and cancellation
drill. Only after that should we spend on the paired context-transfer study.
If managed delegation provides no material utility improvement at a comparable
budget, keep the simpler single-agent configuration. If the required privacy or
cost boundary cannot be met, use the application-owned runtime for that workload.

## Sources

[^1]: [OpenAI: Agents API architecture, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/agents-api/architecture)
[^2]: [OpenAI: Introducing the Agents API, 2026-09-10](https://openai.com/index/introducing-the-agents-api/)
[^3]: [OpenAI: Multi-agent, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/agents-api/multi-agent)
[^4]: [OpenAI: Agents API quickstart, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/agents-api/quickstart)
[^5]: [OpenAI: Run and continue sessions, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/agents-api/sessions)
[^6]: [OpenAI: Events and items, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/agents-api/sessions/events)
[^7]: [OpenAI: Create an agent session event, accessed 2026-09-10](https://developers.openai.com/api/reference/resources/beta/subresources/agents/subresources/sessions/subresources/events/methods/create)
[^8]: [OpenAI: MCP connections, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/agents-api/tools/mcp)
[^9]: [OpenAI: Sandbox security, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/agents-api/environments/security)
[^10]: [OpenAI: Observability and usage, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/agents-api/observability)
[^11]: [OpenAI: Spend limits, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/spend-limits)
[^12]: [OpenAI: Agents API overview, accessed 2026-09-10](https://developers.openai.com/api/docs/guides/agents-api/overview)
[^13]: [OpenAI: GPT-6 Astra model, accessed 2026-09-10](https://developers.openai.com/api/docs/models/gpt-6-astra)

Execution evidence and remaining gates are recorded in the
[verification report](openai-agents-verification-2026-09-10.md).
