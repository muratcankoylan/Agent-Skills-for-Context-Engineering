# Repository-owned research organization

Implementation contract, 29 September 2026. This supersedes the executor direction
in the earlier dated architecture snapshot. Test results belong to dated execution
receipts, not this design. No specification is promoted by this document.

## Objective and measurable boundary

Continuously discover useful context-engineering research, retain its provenance,
form falsifiable interventions, and prepare independently evaluated skill changes.
The product is versioned open-source code and a separately deployed service. It is
not a Codex desktop automation. More agent messages, links, or favorable critiques
are not measures of improvement.

Measure grounded-claim precision, useful-primary-source yield, held-out task
effectiveness, duplicate work avoided, latency, retained spending reservations,
unknown effects, and recovery without duplicate execution. These measurements
have different denominators. Never substitute connector authentication or fixture
accuracy for real research quality.

## Runtime topology

```text
reviewed source config + research policy + existing budget authority
  -> single foreground Organization coordinator, UTC admission and pause controls
  -> source Store: arXiv / X / HN / OpenAlex / company feeds
  -> bounded captures -> offline parser replay -> restricted primary HTML
  -> immutable evidence + selected skill context + verified prior research archive
  -> CodexCampaign: researcher -> grounding -> critic -> optional scoped editor
     opt-in researcher: decide -> inspect/read/consult -> decide -> finish/stop
     each role = fresh official SDK thread/turn -> bounded tool-free gateway
     gateway = existing cumulative reservation -> one OpenAI request -> receipt
  -> exact candidate freeze -> repository validators -> exact duplicate check
  -> supplied frozen evaluation plan, gold-free independent SDK threads
  -> terminal receipt + private dossier -> operator review

all stages -> local metadata trace journal -> explicit root Event + associated OTLP
  -> separate durable phase receipts -> authenticated dashboard/read API verification
```

The initial production profile uses `openai-codex==0.159.0` and matching CLI-bin,
`gpt-6-sol`, default service tier, and model concurrency one. Pricing is an expiring
reviewed policy, not a live price discovery service. Roles cannot change the model,
allowance, endpoints, schedules, source policy, or publication permissions.

There is no native/managed fallback for new pipeline execution. Historical native
and managed receipts remain historical records. The legacy GitHub publisher is
not a hidden continuation of this SDK pipeline.
Some versioned research payloads retain historical `managed-*` schema names for
receipt compatibility. The explicit execution backend and admitted SDK receipt,
not a cosmetic schema rename, establish which runtime executed. New SDK work does
not rewrite old records or turn managed receipts into SDK evidence.

## Responsibilities and trust boundaries

| Module | Responsibility | Explicit exclusion |
| --- | --- | --- |
| `organization.py` | Daily slots, durable dispatch, pause and restart | No allowance creation, model-selected schedule or merge |
| `store.py` | Transactional effect reservations, captures and checkpoints | Not a provider invoice or cross-account spending control |
| `retrieval_sources.py`, `primary_context.py` | Fixed requests, captured bytes, extraction replay and coverage flags | No arbitrary recursive browsing; source text cannot authorize tools |
| `sdk_learning.py` | Bounded verified previous studies, explicit omissions, exact frozen-candidate identity | No evaluation labels/results in researcher context; no semantic novelty claim |
| `codex_worker.py`, configuration boundary | Private worker context, SDK lifecycle, ambient-policy checks, explicit denials | No global config/policy modification or silent privilege relaxation |
| `codex_gateway.py` | Immutable task, one admitted provider attempt, complete validated response | No autonomous model tool calls or forwarding ambient SDK metadata |
| `agent_actions.py` | Four model-selected typed decisions and one optional specialist over captured packet spans | No arbitrary I/O, omitted full-paper reading, SDK-native tool authority or paid repair loop |
| `research_pipeline.py` | Grounding, phase recovery, candidate freeze, validation and evaluation | No accepted-state or automatic publication authority |
| `dossier.py` | Private read-only output/trace viewer | Not source replay, independent validation, or public export |
| `tracing.py`, `trace_events.py`, `trace_export.py`, `trace_pump.py` | Typed metadata, operational Events, associated spans, latency/usage and separate durable delivery receipts | No prompts, raw tool bodies, credentials, or budget authority; ACK is not readback |

SDK configuration isolation is a prerequisite, not a prompt instruction. On a host
with administrator-provided configuration the executor refuses to start rather
than overriding policy. Clean private HOME alone is insufficient. The deployment
must also pin a read-only image, dedicated UID, mounts, process limits and egress.
Native-tool sandbox support is separate from tool-free SDK execution.

The optional `captured-actions-v1` policy makes evidence-reading decisions
agent-selected while preserving one budget-admitted request per SDK turn.
`inspect_context`, `read_span`, `ask_specialist`, `finish`, and `stop` are closed
harness functions. The investigator can select a methods or transfer advisor
once; its advisory output is not independent evidence or an evaluation score.
The subsequent critic/editor and candidate/evaluation gates remain separate.
The [action contract](../../researcher/service/AGENT_ACTIONS.md) records alternatives,
cost/termination limits, provenance and replay. SDK-native dynamic tools were
considered but are not enabled under the single-request gateway contract.

## Context and learning contracts

Discovery evidence and primary observations remain untrusted data. Exact source
quotes and citation IDs are checked before paying for a critic. The research prompt
requires a mechanism, assumptions, transfer conditions, counterevidence, confounders,
paired baseline, held-out task family, ablations and failure criteria. Missing methods
or unsupported cross-domain transfer should produce abstention with a next experiment.

Cross-run feedback is frozen before dispatch. Only compatible, replay-verified prior
research contributes to the researcher archive; critic/editor/evaluator do not inherit
that archive. It is bounded in entries and bytes, with omission counts. Previous
research is not new external evidence. Exact duplicate suppression compares frozen
bytes and their baseline/corpus/path, before paid evaluation. Suppression also
requires a previous completed, replay-verified evaluation with the identical
evaluation-plan digest. A candidate previously stopped at `awaiting_dataset`, or
a changed dataset, seed or evaluation contract, still receives its first/new
evaluation. It is not semantic
deduplication and does not retroactively avoid the researcher/critic/editor costs.

Baseline changes and implementation changes create new identities. Do not rewrite
old receipts to claim successful migration or broaden archive eligibility. Preserve
history, omit incompatible entries explicitly, and re-establish compatibility using
a reviewed migration if cross-version learning becomes necessary.

## Sources and tool policy

arXiv supplies bounded title/abstract search; its lane does not enforce the requested
daily window. X and HN are leads, not scientific corroboration. OpenAlex supplies
metadata and available reconstructed abstracts, not universal full text. Company
feeds are bounded feed windows. The primary reader currently supports restricted
HTML, not general PDF/OCR. Coverage, continuation, unavailable text and omitted
excerpts remain visible in evidence packets.

Default primary selection retains one URL per host. The explicit
`primary_selection_profile: "host-diversity-fill-v1"` first selects distinct hosts,
then fills unused slots with distinct eligible URLs from already selected hosts,
within the configured maximum of two. Selection is bound before effects, not
changed in response to a failed fetch. arXiv discovery and primary reads allow
one three-second local pre-dispatch spacing wait; HTTP failures and uncertain
effects are not automatically retried. A 404 or wire-size refusal remains a gap.

Parallel and Firecrawl have bounded standalone diagnostic adapters, and Parallel
has a registered MCP read check. They are not active Organization daily source
lanes; Organization rejects MCP configuration. Successful authentication does not
grant an SDK agent unconstrained MCP access. Model-facing tools must have reviewed
contracts, effect budgets, provenance,
adversarial tests and explicit capability grants before enablement. Deterministic
retrieval already executes those external effects without giving research text a
route to shell, secret, or publication authority.

## Observation and operator experience

Every registered operation produces typed spans where instrumented. SDK receipts
record thread/turn identities privately; exported references are opaque. Total tokens
and reported cache/read/write/reasoning counters remain distinguishable from unknown
values. Nested span durations overlap and are not additive wall time.
Terminal failure receipts mark pipeline and Organization spans as errors even
when Python returns normally. Valid abstention is a successful execution with an
explicit `abstained` outcome. Foreground serving emits one cycle span per cycle.

External OpenAI response metadata may contain finite JSON floats. The transport
decoder accepts those values under byte/structure bounds, while usage counters
and durable receipts retain their strict integer-only contracts. External metadata
is not copied wholesale into a trusted receipt or SDK response.

Raindrop export uses explicit configured project/write credentials, durable intent,
bounded payload and one POST. Accepted ingestion, partial rejection, unknown delivery
and dashboard readback are separate facts. No ingestion acknowledgement is presented
as an authenticated dashboard query. Raw research outputs stay in the private dossier.
Explicit `--trace-export` enables a post-cycle pump for both known journals;
configuration alone does not. Each pump has a 100-span batch ceiling, 60-second
process-local cadence and failure latch. It preserves uncertain delivery claims
and does not change research recovery or spend authority.

The read-only Control Center exposes service state; `dossier.py` adds complete local
research phase output, learning records, candidate/evaluation decisions, latency and
trace IDs. It does not add deployment authentication or SDK reconciliation controls.
Generate a private dossier with explicit pipeline and trace-state paths; do not commit
it or run it through public export without review.

## Evaluation and optimization loop

1. Reproduce a concrete failure from captures/receipts/traces.
2. Add a deterministic regression or actual-SDK local-provider scenario.
3. Change the smallest prompt, tool contract, context selector or runtime boundary.
4. Re-run the same scenario plus adversarial and restart cases.
5. Use bounded live provider runs to test external interoperability and output quality.
6. Use frozen paired, independently labeled held-out tasks before claiming improvement.

Accelerated UTC days test admission and learning across windows, not elapsed uptime.
Actual SDK plus synthetic responses tests runtime integration, not model intelligence.
Public fixture task results are smoke tests, not publishable effectiveness findings.
Report rejected candidates and abstentions; do not tune against hidden evaluation gold.
The runtime does not establish independent labeling or preregistration merely by
receiving a dataset. Current comparison receipts keep `held_out_verified: false`.
Independent provenance and the reviewed acceptance process are required before an
effectiveness or accepted-skill claim.

## Deployment and release

Recommended first topology: one persistent Linux coordinator with local durable disk,
read-only reviewed release, separate application and SDK virtual environments, private
operator API, and explicit Raindrop exporter. GitHub hosts source, PR review and CI.
Do not turn GitHub ephemeral job storage into the authoritative budget ledger.

Provision using [deployment](../../researcher/service/DEPLOYMENT.md) and
[SDK runtime](../../researcher/service/deploy/CODEX_RUNTIME.md) instructions. Activate
[Organization](../../researcher/service/ORGANIZATION.md) only after a deployment-specific
canary. Keep publication disabled until scoped GitHub identity, review gates, rollback,
secret rotation, backup restore and operator access are demonstrated on that host.
No host provider, deployment, automatic PR publication, accepted skill change or
month-long reliability claim is implied by this reference architecture.

The [implementation plan](research-organization-implementation-plan-2026-09-29.md)
tracks this closure sequence. Official contracts: [Codex SDK](https://learn.chatgpt.com/docs/codex-sdk),
[configuration](https://learn.chatgpt.com/docs/config-file/config-basic),
[model pricing](https://developers.openai.com/api/docs/models/gpt-6-sol).

Measured implementation and live-run outcomes are recorded separately in the
[closure evidence](research-organization-closure-2026-09-29.md).
