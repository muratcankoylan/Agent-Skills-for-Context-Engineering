# Portable research harness: deployment and operator design

Origin: 8 September 2026. Synchronized 10 September 2026 with the [standalone cloud service plan](cloud-research-service.md), which supersedes earlier laptop-first, Codex-scheduled and product-wide zero-call assumptions. This is non-normative deployment/operator guidance, not infrastructure provisioning or a production attestation. The separate developer-preview service supports explicitly configured native provider calls; historical zero-call experiments remain unchanged. Accepted skill promotion and production activation are not enabled by this document.

See the [architecture paper](research-harness-architecture-paper.md), [status and merge plan](status-and-merge-plan-2026-09-08.md), and [existing specification lifecycle](../specs/README.md).

## 1. Deployment decision

Build and test the same standalone Python service under local Docker and on one dedicated, single-tenant Linux cloud VM. One coordinator owns SQLite on persistent local disk and private artifact storage; native API roles and registered read-only tools exchange bounded attributed data. The authenticated operator surface includes inspect, pause/resume and configured research admission. Keep candidate-authored executable code off this node. Add an independently isolated executable evaluator only after its threat model, budget protocol and canary are accepted.

This is a recommendation to reduce operational complexity, not a claim that a plain VM is an adequate hostile-code sandbox. Hardware size, cloud provider, region, retention, monthly ceiling, and RPO/RTO remain unresolved requirements. Measure them in the clean-install pilot; do not invent a production price or reliability SLA from the current small dataset.

Draft SPEC-014/024/025 now name this standalone-cloud direction. The former mandatory maintainer-machine/launchd topology is superseded, not an outstanding host-selection fork. The specs remain drafts and the current service is a developmental subset, not complete owner conformance. Local Docker is a reproducibility/development target, not evidence that a cloud canary has run. No billable provider, region or machine size is selected here.

The [earlier managed Google Cloud design](deployment.md) remains a possible scale-out topology. Its many services, managed queue, database, and sandbox cluster are not initial MVP requirements. Select those services only when throughput, multiple writers, isolation, or operational support justifies them. No Kubernetes, vector database, multi-region replication, or event-streaming platform is necessary to demonstrate the present data-only adapter.

## 2. Where components and agents run

| Component | First portable target | State and authority |
| --- | --- | --- |
| Public corpus, schemas, code and paper artifacts | Protected GitHub repository and release distribution | Human-merged version is public release identity |
| Trusted coordinator | Standalone foreground Python service, dedicated Linux account, one active writer | Private development workflow owner now; accepted kernel integration remains separate |
| Source adapters | Bounded trusted processes with fixed outbound policy | One shared cache/reservation owner; credentials only when separately provisioned |
| Current data-policy evaluator | Ordinary bounded local process | Data only; no candidate code, models, or release authority |
| Researcher, critic, skill editor | Configured native model adapters; data-only roles | Durable reservations and closed outputs; no direct release, tool escalation or candidate-code execution |
| Future executable candidate | Disposable independently isolated worker | Read-only frozen inputs, constrained output path, no ambient host/repository/cloud credentials |
| Independent evaluator | Separate evaluator-controlled materialization/principal | Hidden tasks and grader inputs inaccessible to candidate author |
| UI/query API | Preview loopback bearer API; future reviewed TLS/user-identity ingress | Status and bounded commands; Control Center connection is not presumed complete |
| Repository proposer | Explicit least-privilege GitHub binding and effect owner | Standing configuration may permit draft PRs; never merge, force-update protected refs or alter rules |
| Release/deployment operator | Authenticated maintainer outside the proposer | Separate reviewed merge and activation decisions |

Do not equate process separation with evaluator independence. Hostile code must not share a writable filesystem, privileged socket, secret-bearing environment, or unrestricted network with control services. The actual sandbox technology remains an accepted-executor decision, not a checkbox satisfied by an ordinary container.

## 3. State ownership and migration

Local source runs have private scheduler/evidence stores, the standalone event journal has its own lifecycle, and experiments have private manifests/intents/outcomes. The new service has one SQLite development workflow store and reuses captured artifacts and candidate freezing. These are explicit development boundaries, not multiple accepted work owners or one already integrated production database. Earlier stores are evidence/import sources, not second writers to the service's work population.

The production target needs one accepted work/result owner, with transactional reservations and dispatch/outbox records. Workers submit bounded outcomes; they do not independently update canonical projections. Public Git history owns released corpus state. Private evidence bodies belong in content-addressed storage with access-controlled bindings. The UI is a reconstructable view.

Migration sequence:

1. Freeze current formats and retain worked examples, rejected outcomes and replay tests.
2. Accept the missing ownership and transition contracts; register the permitted record kinds.
3. Import legacy/private observations as historical, non-authoritative evidence with original identities.
4. Run the new reducer in isolated shadow state and compare projections with the retained records.
5. Reconcile every in-flight or unknown effect before assigning the new writer an active epoch.
6. Keep the old loop inert. Never run two competing acceptors against the same work population.

A database copy alone is not promotion. Changing a storage path or code version cannot reset deduplication, budget, or exposure history.

## 4. Scheduling and cron semantics

The earlier bounded Codex heartbeat was a development observation mechanism, not the product scheduler or evidence of service uptime. Its current status is owned by its automation record, not this document. Historical daily source-campaign policy applies to that workflow; it does not define service deployment.

`python -m researcher.service serve` owns the foreground admission/work loop independently of Codex. An OS/container supervisor keeps that process running; an optional external timer may wake admission but cannot bypass it. Admission checks schedule identity, due slot, work identity, clock, reservations, budget, prior outcome and pause. A missed tick must not cause unbounded catch-up. The preview's single-worker lock and SQLite receipts are not full normative lease/fence conformance.

```text
timer tick -> admission and reservation -> durable intent -> bounded dispatch
          -> terminal receipt or reconciliation-required
          -> recorded outcome -> derived projection -> scoped proposal/delivery
```

The checked-in legacy launchd wrappers remain inert. Unknown outcomes stay stopped until reconciled; “retry after timeout” is not safe when a provider may already have completed or charged the operation. Source observations, model completion, pilot preference, draft publication and human acceptance remain distinct outcomes. See the cloud plan for CLI/configuration entry points; listing a command is not evidence of successful cloud installation.

## 5. Prompts, context and model execution

Prompt text is only one input to an attempt. A complete execution descriptor must bind role/template version, objective, context artifact, allowed tools, editable surfaces, evaluator exposure, runtime identity, output schema, stopping rules and hard resource reservation. The preview's `researcher/service/prompts.py`, contracts and workflow supply a bounded data-only path; the older prompt compiler and full SPEC-013/014 descriptor remain separate contracts to reconcile.

Research prompts should request falsifiable mechanisms, supporting and contradicting evidence, explicit missing information, and expected downstream tests. Builder prompts should name one constrained change and preservation obligations. Critic prompts should evaluate narrow criteria independently instead of issuing a single broad quality score. Report assembly should consume verified outcomes rather than a candidate's success narrative.

Before a configured development model run, require explicit credentials and provider/data scope, bounded execution, cumulative reservation, exact resume identities, stall visibility and uncertain-outcome handling. Production canaries additionally require accepted owner/deployment policies. Keys never enter prompts or committed artifacts. Native adapters are explicit tested integrations, not universal wire compatibility. Register MCP servers/tools separately with schema/output limits and least-privilege credentials; enforce deployment egress and process caps rather than trusting a remote read-only annotation. The existing zero-call benchmark runner is unchanged.

## 6. Results and human interaction

### Available now

- CLI JSON/Markdown reports, immutable captures, manifests and replayable outcomes.
- A local read-only observation view showing actual runs, source/capture counts, context sizes, blockers and report digests.
- Separate fixture controls illustrating future interaction, not issuing production commands.
- A data-policy comparison report with both outcomes and an inert proposal/rejection.
- A standalone preview CLI and loopback API for status, health, pause/resume and configured-schedule enqueue; typed role prompts, frozen one-body-edit candidates and a draft-only GitHub adapter. These implementation paths require their own current test/canary receipts, not extrapolation from the September 8 results.

The two-order pairwise model judgment is a proposal-review pilot, not sealed independent task evaluation. Registered MCP is a restricted adapter surface; mere module existence does not establish a campaign-to-MCP end-to-end run. The operator UI is not claimed connected until actual service-backed interaction tests pass.

### Required operator product

| Operator question | Required interface evidence |
| --- | --- |
| What is it doing? | Current work/attempt identity, stage, source/evaluator version and next operation |
| Why did it stop? | Stable blocking reason, last terminal receipt, unresolved intent and permitted recovery |
| What did we learn? | Supported claims, counterevidence, omitted sources, paired evaluation and uncertainty |
| What will change? | Exact candidate diff, editable-surface check, baseline/candidate digests and affected skills |
| What did it cost? | Reserved/used/remaining requests, bytes, model tokens, currency, compute and reviewer time |
| Can I stop it? | Pause admission, cancel permitted work, quarantine ambiguity; no false “cancelled” claim |
| Can I undo it? | Accepted prior version, rollback procedure, proof that data/external effects are reconciled |

The UI must distinguish observed, partial, unknown, rejected, proposal-ready, accepted and deployed. It must not style proposal-ready as released. Authentication and command authorization are separate from showing a login screen.

GitHub remains the review/merge surface. Explicit standing operator configuration may permit bounded automatic draft PRs and notification effects; it does not authorize merge or recipient expansion. Notifications should carry approved projections, not raw source bodies or credentials. Email/chat/social delivery needs a registered destination-specific adapter and observed delivery/unknown receipts; a GitHub reviewer request is not a general notification service. The bearer token stays in a trusted server-side client, never browser JavaScript, and public exposure requires reviewed TLS/user authentication.

## 7. Budgets, metrics and stopping rules

Historical source/packet caps remain controlling for their adapters. The service adds explicit model-call and integer currency reservations; complete operations still need a resource vector, not only a maximum token field:

```text
R = (HTTP attempts, transferred/captured bytes, pages, model calls,
     input/output tokens, currency micros, CPU time, wall time,
     memory, process count, artifact bytes, reviewer minutes)
```

Report captured bytes separately from transferred bytes. A response rejected before complete capture can consume traffic and time while contributing zero captured bytes. Charge unsuccessful attempts and retries. Report the difference between a forecast, a reserved ceiling, an observed usage record, and an unavailable provider receipt.

Instrument admission latency, execution latency by stage, source failure/empty/partial rates, queue age, unknown intents, reservation exhaustion, invalid candidate rate, evaluator disagreement, accepted useful changes, regression rate, and review burden. Pin denominators and alert on transitions. Do not page the operator for unchanged routine replay.

Stop automatically for authority mismatch, source/candidate identity mismatch, unbound evaluator input, budget exhaustion, secret exposure, unknown external outcome, missing state, or a critical regression. Proposer confidence is not a recovery action.

## 8. Deployment gates and tests

| Gate | Required evidence before activation |
| --- | --- |
| Release identity | Reviewed exact Git tree, lockfiles, required CI and no unpublished runtime state |
| Clean portability | Install and CLI execution on clean declared Linux/macOS targets; documented unsupported Windows behavior |
| State recovery | Crash injection around intent/outcome, duplicate delivery, stale fence, clock rollback and disk exhaustion |
| Backup/restore | Encrypted off-host backup, restore to a fresh environment, digest/replay checks and external-effect reconciliation |
| Isolation | Seeded-secret, denied-tool/egress, filesystem escape, resource-limit and credential-separation tests |
| Provider activation | Accepted adapter, explicit credential, hard budgets, concurrency-one canary and ambiguous-charge handling |
| Semantic utility | Frozen need-level study and downstream tasks, independently graded, with no critical regression |
| Operator readiness | Representative pause, inspect, reject, recover and rollback tasks; measured errors and intervention time |
| Long duration | Real timestamps, admitted/missed/failed cycles and recovery receipts over the declared canary period |
| Promotion | Reviewed reversible narrow-surface change, external maintainer authorization, separate deployment identity |

RPO, RTO, availability, latency and budget thresholds must be chosen and frozen before the production canary. They are not measured today. A successful restore test must not send notifications, repeat paid attempts, or reactivate an old writer automatically.

## 9. Immediate delivery order

1. Reconcile the foundation train and updated cloud direction against exact current heads; retain lifecycle blockers without mislabeling development work as acceptance.
2. Review the standalone service as a bounded pre-release: independent scheduling, typed roles, captured evidence, frozen text edits, private state and tested denials.
3. Exercise explicitly configured providers with a useful query, a different mechanism query and a no-answer case; retain costs, failures and pilot limitations.
4. Run draft-PR and notification canaries only in the configured repository/destination scope, including lost-response and duplicate-effect tests.
5. Prove clean Docker/cloud installation, ingress controls, restart, encrypted artifact-complete restore and operator tasks. Select actual hosting and cost ceilings through the deployment decision.
6. Conduct the held-out usefulness study and complete work/evidence/evaluation/promotion owner integration in dependency order.
7. Activate a separately approved, bounded production canary only after exact release, recovery, semantic and operator gates pass.

This sequence supplies no new permissions. Development calls and proposal/delivery effects use explicit operator authorization and scope; production infrastructure, human merge and activation remain separate decisions. A passing local test suite is neither completed cloud operation nor demonstrated scientific utility.
