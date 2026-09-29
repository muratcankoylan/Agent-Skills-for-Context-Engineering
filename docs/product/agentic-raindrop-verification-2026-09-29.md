# Agent orchestration and Raindrop transport evidence

Date: 29 September 2026. This is local integration evidence, not a cloud launch,
scientific effectiveness benchmark, or claim that all repository PRs are ready.
The work preserves the existing cumulative OpenAI authority and historical failures.

Correction after authenticated dashboard inspection on the same date: the configured
Production/default project still showed zero Events. The 246 acknowledgements below
are transport-level observations and did not establish a working Events integration.
They must not be used as a dashboard-readiness gate or rewritten as successful
event readback. The integration repair requires a new canary and visible UI evidence.

## Implemented architecture

The [architecture](research-organization-architecture.md),
[agent protocol](../../researcher/service/AGENT_ACTIONS.md), and
[operator runbook](../../researcher/service/ORGANIZATION.md) describe the executable
boundaries. The new profile is opt-in; existing fixed-role studies keep their
original prompt and receipt shapes.

```text
reviewed daily schedule -> budgeted discovery and primary capture
  -> immutable evidence packet + selected skill corpus
  -> researcher chooses typed action -> harness validates and dispatches
       inspect_context | read_span | ask_specialist | finish | stop
  -> separate critic -> scoped editor when justified
  -> candidate freeze -> supplied evaluation -> human review

each stage -> private structured journal -> post-cycle metadata export -> Raindrop ACK
full source/model outputs -> private dossier, never automatic cloud upload
```

The researcher may make four decisions and consult one methods/transfer advisor.
The subsequent critic and optional editor give at most seven turns before a
separately budgeted evaluation. Every paid decision is a fresh actual Codex SDK
turn with an immutable receipt. Evidence selection, consultation, and stopping
are model-selected; budgets, source provenance, citation resolution and acceptance
remain deterministic. There is no autonomous merge or authority expansion.

This is harness-dispatched function selection, not SDK-native dynamic tools.
The [official SDK documentation](https://learn.chatgpt.com/docs/codex-sdk) and
installed SDK/CLI informed this boundary: the current gateway admits exactly one
provider request per immutable turn. A native multi-request tool loop needs a
different spend/recovery contract before activation.

## Historical Raindrop transport acknowledgements

Raindrop acknowledged **246 real-operation spans in six export attempts**, with
zero rejections. The three inspected journals have no pending, unacknowledged,
unfinished or unknown exports at the final snapshot.

| Batch | Spans acknowledged |
| --- | ---: |
| Retained research authority backlog | 56 |
| Two retained live-source journals | 51 + 37 |
| First captured-action live study | 37 |
| Follow-up memory study, including failure path | 30 |
| Independent context-compression study | 35 |

The final three batches were sent automatically after Organization cycles, not
by a manually invoked exporter. The trusted coordinator preflights credentials,
closes the cycle span, and ticks up to two journals. Each due tick allows one
batch of at most 100 spans, a 60-second process-local cadence, and the existing
ten-second transport deadline. Unknown/partial/rejected delivery halts that pump;
durable intent prevents automatic resending of uncertain spans after restart.
A failed telemetry output sink cannot replace the research outcome.

The approved configured project was used. No installer, collector, daemon,
scheduler or remote settings change was needed. ACK establishes ingestion only:
authenticated dashboard readback and retention were not verified. Raw prompts,
source text, tool arguments/results, credentials and error bodies are excluded.
See [tracing](../../researcher/service/TRACING.md) for activation and inspection.

## Live studies, including negative outcomes

All three studies used SDK/CLI 0.159.0, `gpt-6-sol`, low reasoning, default service
tier and concurrency one. Each permitted at most five source requests: arXiv,
Hacker News, Hugging Face, and two primary HTML captures. The time window is a
daily scheduling slot, not proof the external feeds enforce that window.

| Study | Actual model attempts | Cycle time | Outcome |
| --- | ---: | ---: | --- |
| Agent memory, initial profile | 5 | 43.956 s | Four decisions plus critic completed; critic abstained |
| Agent memory, rubric/coverage revision | 2 | 13.264 s | First decision completed; second transport outcome unknown |
| Context compression, independent query | 4 | 40.954 s | All turns completed; contradictory final abstention rejected |

Reported wall times include post-cycle trace delivery and status collection, not
just model inference. No specialist consultation was selected in these paid
studies; that branch was exercised with the actual SDK and synthetic providers.

The first researcher proposed testing query-driven incremental memory construction
inspired by a video-memory paper. The critic did not approve transfer to the skill:
the available abstract/opening HTML did not establish the cross-session baseline,
held-out family, ablations, failure threshold or cost/latency case. No skill update
was accepted and no effectiveness improvement is claimed.

The follow-up exposed an opaque gateway error. Its reservation remains held, it
was not retried, and the old failure cannot be retrospectively classified. The
gateway now distinguishes closed HTTP, network/TLS, timeout, framing/type/size
and worker failure categories without copying provider data. Parent-side SDK
observation exports the corresponding `failure.kind`; classification never
releases budget or authorizes a retry.

The context-compression output correctly described missing transfer evidence but
combined `finish`, `abstain: true` and two cited research claims. The downstream
validator rejected that contradictory record. The action protocol had allowed
combinations its downstream contract forbids. The fix keeps the strict downstream
gate and makes the action interface explicit: a supported `finish` is distinct
from `stop(reason)`. The original paid output is retained as failed, not rewritten.
The final repair was verified with deterministic and actual-SDK fixture tests,
including credential-free replay without another call; it was not followed by
another paid quality trial.

These are interoperability/failure-discovery canaries, not paired quality trials.
Sources, code identities and prompts changed between studies. No causal accuracy,
latency, cost or scientific-quality comparison is warranted.

## Prompt and evidence improvements

The action decisions now retain the exact shared research rubric and validated
capture-coverage header, including primary links and omitted-content limits.
Inspection history no longer duplicates the source index already in every header.
One retained four-decision study contained 67,236 avoidable unescaped canonical
UTF-8 bytes across three later prompts. This is a measured input redundancy,
not measured token or cost savings. The [aggregate measurement](evidence/captured-action-context-2026-09-29.json)
is indexed in the claim ledger; private source content and input digests are omitted.

Completed action transcripts preserve decisions, exact revealed bytes, offsets,
hashes, specialist advice and receipt references. Pure replay validates tool
projections; Campaign replay separately authenticates model origins. Corrupt
existing sidecars fail before a new paid decision. Replay does not fabricate new
action-execution spans. A loop that fails before final grounding has no completed
transcript; earlier turns survive in Campaign checkpoints. The
[dossier](../../researcher/service/DOSSIER.md) documents that partial-history limit.

## Verification and expenditure

The final frozen build passed **1,177 / 1,177 service tests**, with zero failures,
errors, skips, expected failures or unexpected successes, in **276.024 seconds**.
Source bytes remained unchanged during the run. The retained verification receipt
binds implementation `sha256:e3baef0e8723bf444c9aa2c0193bc8ab100749983a3b5f78372ef0c2d5baf888`.
Actual pinned SDK subprocess tests use synthetic
loopback providers, without loading real provider credentials. The parent-network
guard is not an OS-level sandbox or a remote deployment attestation.

Strict repository validation and required-reference platform compatibility passed
for all 17 skills and four local install layouts. Changed-scope lint, diff checks,
derived-inventory reconciliation, skill health and 23 activation cases passed.
The benchmark entrypoint passed three catalog checks but executed **zero scenarios**;
it is not model-effectiveness evidence. The service suite and retained three-day
fixture are the executed orchestration evidence.

The existing three-day default-profile fixture separately exercised
`evaluated_not_accepted -> duplicate_candidate -> abstained`, prior-memory counts
0/1/2, and zero duplicate admissions on repeat cycles. That accelerated fixture is
not three elapsed production days and does not establish scientific effectiveness.

The cumulative $100 allowance was not reset. After these studies:

- Reserved upper bounds: **$7.715578**; available authority: **$92.284422**.
- Completed-call estimated upper cost: **$1.458973**, not invoice-verified spending.
- 51 total provider attempts, 48 completed, three unresolved effects retained.

## Deployment scope and next evidence

The repository-native coordinator and CLI can be deployed independently of this
Codex session. Cloud deployment and scheduler installation were not performed in
this change. `--trace-export` activates post-cycle delivery only with explicit live
execution and configuration; credentials alone do not start a process.

The next quality experiment is a preregistered comparison against the fixed-role
baseline on identical frozen inputs and independently labeled tasks, measuring
grounded-claim precision, evidence coverage, useful proposals, latency and cost.
The action profile currently reads captured bytes only, not omitted full papers
or arbitrary new URLs. Better full-paper exploration requires its own bounded
capture phase, not a permissive function that bypasses provenance.

No GitHub push, merge, accepted-skill promotion or cloud publication occurred.
