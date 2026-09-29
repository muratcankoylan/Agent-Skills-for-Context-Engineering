# Research organization implementation and evidence plan

Status: scoped fixes implemented and locally exercised, 2026-09-29. This plan answers the request to
close the documentation audit findings, migrate missing learning behavior, and
show executed research scenarios and traces. It does not authorize publication,
deployment, automatic merge, or alteration of evaluation policy.

## Product contract

Build a repository-native research organization, independent of the Codex desktop:
scheduled source retrieval -> captured evidence -> research/critique/edit SDK roles
-> immutable candidate -> independent evaluation -> reviewable dossier.
Prior verified hypotheses inform later research without leaking evaluation labels.
Identical candidates are suppressed across different source jobs before repeat
evaluation only when the previous replay-verified evaluation completed under the
same evaluation-plan digest. New datasets, seeds or previously unevaluated
candidates are not suppressed. The existing cumulative OpenAI authority retains its $100 ceiling.
Raindrop is an observability sink, never state, budget, or publication authority.

## Implementation sequence and ownership

1. SDK security owner: close system/managed configuration before SDK startup,
   explicitly disable notification/export channels, and turn the confirmed
   marker/collector probes into deployment regressions.
2. SDK telemetry owner: retain cache-read, cache-write, and reasoning-token details
   in versioned receipts, with truthful unknown semantics and historical replay.
3. Learning owner: bind a bounded verified prior-hypothesis archive to researcher
   context and add cross-job exact candidate suppression, replay and fault tests.
4. Integration owner: update architecture and operator recipes, add multi-day
   scenarios and a human-readable output dossier, improve prompt/tool tests,
   reconcile existing spend, execute bounded live scenarios, and verify Raindrop
   export using the configured credential without exposing it.
5. Independent verification: review changes across owners, fix findings, freeze
   the integrated source, and run full deterministic and real-SDK loopback gates.

## Experiments

Keep three evidence classes separate:

- Deterministic fault simulation: advance explicit UTC days; use actual Stores,
  captures, checkpoints, learning records and trace emission; inject named source
  and provider failures. This measures orchestration, not research quality.
- Real SDK/local-provider scenarios: actual pinned SDK processes with bounded
  synthetic responses; inspect emitted request contracts and role isolation.
- Live provider research: current source reads and model calls through the
  existing authority, with a predeclared maximum call/cost allowance. Different
  historical retrieval windows are replay experiments, not days of elapsed uptime.

Required scenarios include novel evidence, repeated evidence/candidate, changed
baseline, conflicting evidence, prompt injection, source rate limit/outage,
malformed model output, missing usage, interrupted work, restart/replay, and pause.
Retain failed outcomes rather than replacing them with successful reruns.

## Visible outputs

The execution dossier must expose each scenario's query and date semantics,
source/tool outcomes, captured citations, agent-role output, candidate or abstention,
evaluation scope, latency, usage/reservations, replay behavior, and trace IDs.
Export only the reviewed trace projection to Raindrop. Verify ingestion separately
from local event creation and distinguish accepted ingestion from dashboard readback.
Never send credentials, raw private paths, or hidden reasoning to telemetry.

## Acceptance criteria

- Confirmed audit reproductions fail safely before unintended execution/export.
- Nonzero provider token details survive receipt, SDK, trace and restore paths.
- Later-day research receives only verified bounded prior hypotheses; evaluators
  receive neither that archive nor gold labels as task context.
- Identical candidate bytes do not trigger a second expensive evaluation under
  the same already-completed evaluation contract.
- Crashes and uncertain effects retain accounting and cannot silently resend.
- Simulated and live scenarios have inspectable outputs, including failures.
- Required tests execute without skips. Source/inventory/release checks pass or
  retain explicit pre-existing unrelated failures without destructive cleanup.
- Final status names what was implemented and measured, not just what was planned.

## Executed status and next gates

The [closure evidence](research-organization-closure-2026-09-29.md) records the
implemented security, learning, usage, retrieval and trace fixes; the complete
1,081-test service run; separate fault scenarios; actual-SDK three-day simulation;
and both live experiments, including failed outcomes. The three-day helper uses
synthetic responses and does not itself exercise every fault listed above.

The current local dossier is generated and private. Raindrop export of this
exercise awaits explicit approval for the configured `default` destination; no
current ingestion or dashboard readback is claimed. The exporter and deployment
templates are implemented, but no service was installed or enabled.

Remaining work is evidence-driven, not an automatic acceptance bypass:

1. Establish bounded full-methods coverage for papers that lack HTML or exceed
   the current wire limit; compare coverage and extraction fidelity against the
   existing primary reader before changing the evidence contract.
2. Freeze independently labeled, preregistered paired task families for the live
   hypotheses. Fixture comparisons must not become scientific claims.
3. On the selected deployment host, exercise service activation, operator access,
   backup/restore, explicit trace delivery and scoped publication review.
4. Package this unpublished integration work through the approved PR process.
   Nothing in a local test receipt authorizes pushing or merging.
