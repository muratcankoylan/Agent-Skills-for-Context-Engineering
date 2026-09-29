# Standalone cloud research service

Runtime update, September 10: the
[OpenAI Agents API architecture](openai-agents-research-architecture.md) is the
preferred execution direction. This document describes the earlier native-call
preview and reusable application responsibilities. The managed API owns the agent
loop, not our evidence, evaluation, scheduling or release authority. Managed live
tests and unattended activation remain unverified.

Date: 10 September 2026. Status: implementation direction and pre-release contract, not a production attestation. This supersedes the laptop-first and Codex-scheduled target in earlier product plans. It does not rewrite historical measurements, accept a specification, select a billable cloud provider, or enable automatic merge.

## Product and first release

Build an open-source service that runs without an interactive developer: scheduled research needs become captured evidence, mechanism hypotheses, critical review, tested skill changes, draft GitHub PRs and useful notifications. Native provider APIs and registered MCP tools are replaceable integrations. Codex can help develop or inspect it, but supplies neither runtime, scheduler, memory nor canonical state.

The first release is a single-tenant cloud service with bounded data-only agents and automatic proposal/delivery within explicit operator configuration. It is not merely a replay tool. It can execute configured providers in development; fake and live observations remain distinct. Production readiness requires actual deployment, provider, recovery, effect and usefulness evidence. The first developmental code slice is not full conformance to the draft specification program.

The existing [architecture paper](research-harness-architecture-paper.md), [September 8 results](living-organization-results-2026-09-08.md) and [paper protocol](portable-harness-paper-protocol.md) remain evidence and methodology references. Their zero-call packet experiment is a useful regression control, not the complete product. Current prototype recovery limitations remain binding until repaired and tested.

## Smallest coherent vertical slice

```text
service-owned schedule or authenticated research request
  -> durable admission, reservations and attempt identity
  -> bounded source/MCP retrieval and captured evidence
  -> researcher dossier -> critic findings -> skill-editor candidate
  -> frozen baseline/candidate evaluation -> review packet
  -> GitHub proposal outbox -> reconciled draft PR
  -> notification outbox -> delivered/not-delivered/unknown receipt
```

Human acceptance of repository changes and deployment of a new service revision remain separate. An automatic PR may contain a proposed skill update; neither an open PR nor a critic's favorable opinion changes accepted skills. New research failures and rejected candidates return to the archive with their evidence and costs.

### Responsibilities, not one service per agent

| Owner | Inputs and outputs | Boundary |
| --- | --- | --- |
| Coordinator | Research need, schedule, configuration and budget to bounded attempts and reconciled results | One durable work/effect writer; no model-defined permissions |
| Source workers | Explicit queries or registered read tools to captured bytes, normalized leads and provenance | Treat tool output as data; no automatic source instructions or arbitrary crawling |
| Researcher | Evidence plus current skills/mechanisms to a falsifiable mechanism dossier | Cite captured evidence, distinguish abstract claims from verified results, preserve counterevidence and missingness |
| Critic | Dossier and permitted evidence to narrow support, contradiction and testability findings | Cannot approve itself, apply changes or stand in for a sealed independent evaluator |
| Skill editor | Dossier, critique and exact editable surface to a candidate patch and proposed tests | Data-only patch; no shell, plugin installation, evaluator modification or main-branch write |
| Evaluator | Frozen baseline/candidate and evaluator-owned tasks to complete paired observations | Separate input control; author assertions and shared packet summaries are not score oracles |
| Effect adapters | Exact approved repository/destination operations to provider receipts | Only GitHub/notification outboxes; no merge, rule changes or unchecked resend |
| Operator UI/API | Authenticated requests and owner projections | Inspect, pause, reject, diagnose and recover; never an alternative state database |

The role output contracts must be registered and reconciled with SPEC-013/014; the older prompt compiler's builder/verifier-only contract is not silently relabeled. Start with sequential data dependencies and bounded parallel source retrieval. Extra critics or agent consensus require a measured gain, not an agent-count target.

## Reuse and new ownership

| Existing component | Reuse | Required bridge |
| --- | --- | --- |
| `research_sourcing.build_plan`, `run_sourcing`, `verify_sourcing_campaign` | Bounded lanes, capture/replay and source policy | Coordinator owns campaign work; existing private run stores remain evidence, not competing workflow authorities |
| `research_context`, `research_discovery`, `research_articles` | Explicit corpus selection, budgeted packets, inert extracted spans | Dossier links to exact evidence and omissions; primary attachments must be explicitly included, not assumed present |
| `LocalResearchEvidenceStore`, `ArtifactStore`, `CandidateFreezer` | Immutable bytes, private bindings and frozen candidate materialization | Portable service storage/configuration and complete input lineage |
| `prompt_compiler`, repository validators | Typed prompt identity and deterministic candidate checks | New data-only role contracts plus separately controlled effectiveness tasks |
| `research_experiment`, `research_evolution` | Exact comparison, negative controls, unknown-outcome and source-oracle regression patterns | Do not present the Boolean compact experiment as semantic skill evaluation |
| `local_scheduler`, `event_store` | Fencing, recovery tests and journal primitives | One accepted work/effect owner; no production restoration through the known incomplete prototype recovery path |
| `apps/control-center` | Real observation view, reusable presentation and security checks | Authenticated service projections/commands; existing fixture controls stay visibly non-operational |

### Minimal durable contracts

- A research need binds objective, repository/base identity, source policy, target skills, schedule/slot identity, stop rules and total resource ceilings.
- An attempt binds role, provider/model, prompt/context/tool-schema digests, parent inputs, fence, reservation and terminal output or unknown outcome. A context or policy change creates a different attempt, not a reset budget.
- An evidence dossier binds sources, exact spans, claim status, mechanism, limitations, counterevidence, proposed test and unknowns. Multiple citations to the same work do not count as independent support.
- A candidate binds exact base tree, allowlisted data surfaces, complete patch, provenance, predicted effect and frozen materialization. Accepted corpus, evaluator and authority paths are excluded.
- An evaluation binds dataset/split/exposure identity, baseline and candidate, evaluator/runtime, all planned rows, failures and decision rule. No result is inferred from file existence or model confidence.
- An outbox operation binds kind, repository or destination reference, request digest, stable operation identity, effect class, receipt and reconciliation state. A lost response is not permission to send again.

Artifacts are immutable; one coordinator applies state transactionally. Run stage, scientific decision and external-effect state are separate: a completed execution may be unsupported, rejected or awaiting evaluation, and an eligible proposal may still have unknown PR delivery. Knowledge transfer between roles uses attributed dossiers and frozen context, not copied chat history or shared mutable agent memory.

## Providers, MCP and credentials

Configure model-provider adapters per role with model ID, supported output contract, private endpoint binding, credential reference, timeout, retry/repair ceiling and explicit resource reservation. Support native APIs through tested adapters; do not claim every provider is compatible with one guessed wire format. Provider changes are experimental/configuration changes and cannot occur silently after failure.

Register read-only MCP servers and tools explicitly. Pin server/tool/schema identity and approved network/process boundary, limit arguments and output, and deny automatic server installation, sampling, write-tool discovery or scope expansion. A server's read-only annotation is not a security guarantee. General-purpose MCP is not the GitHub or notification write channel. Source responses, MCP output and model text cannot authorize another action.

Development config may name an environment variable or private mounted secret; it never includes the secret value in public examples. No ambient Codex, shell or home-directory configuration is loaded. Planned production adapters support cloud secret stores and workload identity/OIDC with audience, issuer, expiry and scope checks. Use a scoped GitHub App and destination-specific delivery credentials. Provider availability and possession of a key are distinct from authorized scope and remaining budget.

Automatic proposal and notification scopes are configured once by the operator and checked for each effect. They need not ask the operator to approve every routine allowed event. Destination changes, broader tools, merge, release and production activation are not implied by that standing configuration. Initially prefer one reviewed private notification destination and one repository sandbox for effect canaries.

## Deployment and recovery

The initial target is the same pinned Python service image under local Docker and an ordinary Linux cloud VM service/container supervisor. One coordinator owns SQLite on persistent local disk and private content-addressed artifacts. Keep frontend ingress separate from database/credential access. Local ports bind loopback; cloud operator endpoints require reviewed TLS and authentication. No cloud account, region, instance size or monthly bill has been chosen.

Do not mount host Docker sockets or execute candidate code on this trusted node. Data-only roles may call native APIs and approved read tools; later executable candidates require a distinct attested isolation provider. Multiple readers/workers do not imply multiple state writers. Do not place SQLite on a cross-host shared filesystem. Move to managed PostgreSQL or a Temporal adapter only when measured contention, availability or cross-host coordination requirements justify a migration.

Schedule admission persists due-slot identity, bounded catch-up policy, pause state, reservations and attempts independently of the service process. The existing Codex heartbeat and dormant launchd scripts are not deployment dependencies. A cloud timer may wake admission; it cannot directly call models, push commits or send messages.

Backup closes journal tail, transitive artifact bytes, schema/config/policy generations, pending effects, reservations and active release identity in one verified barrier. Encrypt off-host copies; keep recovery keys separate and restore no live capability. Restore to a fresh namespace, verify lineage, reconcile uncertain remote effects, and explicitly authorize reopening. A valid older backup alone cannot prove preservation of later accepted work. Rollback must retain new journal events; irreversible migrations require forward recovery.

## Executable milestone map

The developmental package is `researcher/service`: contracts and SQLite store; provider/tool and knowledge adapters; role prompts/workflow; GitHub outbox; CLI and authenticated API. Its first candidate operation is one exact skill-body replacement, frozen as an artifact, not arbitrary code execution. The two-order pairwise model comparison is an order-sensitivity pilot, not independent downstream effectiveness evidence. The existing Control Center is not claimed connected to this service until that integration is verified.

Developmental entry points use ordinary Python, not a Codex task. Use a new private state directory for the offline demo, and replace the absolute paths below with operator-selected locations:

```sh
python -m researcher.service --help
python -m researcher.service demo --state /absolute/private/new-demo-state --repo /absolute/repository
python -m researcher.service serve --config /absolute/private/service.json --state /absolute/private/service-state --repo /absolute/repository --live
```

The CLI exposes initialization, status, pause/resume, enqueue, tick, work, demo and foreground service operations. The authenticated API is a separate `api` command, bound to `127.0.0.1:8787` by default; cloud exposure needs a reviewed TLS/authentication boundary, not a public bearer token in browser code. `serve` owns the tick/work loop. `--live` plus explicit config selects real adapters; the offline demo supplies no scientific result. Actual completed commands and measurements belong in the release verification receipt, not inferred from this CLI listing.

The proposed Docker runtime uses the same foreground entry point with read-only configuration/repository inputs and a private writable state volume:

```text
python -m researcher.service serve --config /config/service.json --state /state --repo /repo --live
```

Do not publish a credential in the configuration, expose the state volume, or enable GitHub/delivery merely because `--live` is present. Those effects require their explicit operation/destination configuration. The following milestones are acceptance workloads, not claims that a cloud environment or all command paths have already passed verification.

| Milestone | Bounded implementation | Required observation |
| --- | --- | --- |
| C0: independent service | Durable coordinator, configured roles, fake provider, explicit state directory, pause/status and local entry point | Starts outside Codex; restart preserves identities; duplicates and unknown outcomes do not re-execute; no production-authority claim |
| C1: real research path | Existing source capture plus configured native API and registered read-only MCP | Real dossier/critique/candidate from one need; exact citations; recorded provider/tool failures and costs; repeat with another query and a no-answer case |
| C2: tested skill proposal | Frozen data patch, structural checks and separately controlled baseline/candidate task evaluation | All planned cases retained; irrelevant/malicious source, fabricated citation, invalid patch and no-improvement controls rejected; no candidate code execution |
| C3: automatic effects | Transactional GitHub and private-notification outboxes | One sandbox draft PR and notification; crash/lost-response reconciliation; merge/default-branch/recipient escape denied; human edits preserved |
| C4: cloud pre-release | Pinned image, single cloud coordinator, private persistence, authenticated operator surface | Clean install without developer home; host restart, disk-full, outage, encrypted restore and operator pause/recover tasks actually exercised |
| C5: production candidate | Accepted owner integration, reproducible release, isolation where required and frozen canary policy | Independent usefulness and recovery evidence, exact-tree review, actual scheduled interval/costs, explicit production activation |

C0 is not completion of C1; fake role text proves wiring only. C1 is not scientific effectiveness; a generated patch is not a validated improvement. C3 demonstrates proposal automation, not automatic merge. Each milestone inherits applicable owner contracts; draft edits and pre-release tests do not advance lifecycle status.

## Research and performance evaluation

Retain the existing deterministic replay/packing case study and its later `insufficient_evidence` outcome as historical evidence. For new work, freeze underlying research needs/failure families before retrieval. Paper versions, query variants and model repetitions remain nested, not independent samples. Compare literal search, facet/recency lanes and optional MCP retrieval at matched request, packet and reviewer ceilings; measure known-target recall only where the gold pool is adequate, and keep unjudged fractions visible.

Compare no-skill, incumbent skill, candidate skill and matched-length unrelated-change controls on held-out tasks with pinned model/tools/context. Prefer trusted deterministic task outcomes; use blinded independently controlled semantic labels for relevance, mechanism support, counterevidence and applicability. A critic role in the same proposal loop is not that independent judge. Keep development, selection and sealed final populations separate, with exposure recorded across candidate ancestry.

Use a development-only variance/cost pilot before fixing sample size and practical-effect thresholds. Predeclare paired need-level analysis, multiplicity, stopping and missingness. Archive/random/evidence-guided search comparisons use the same candidate grammar and maximum budgets; archive preparation and unsuccessful attempts count. Report negative/no-answer, invalid, failed, timed-out, cancelled and unknown cases, not only successful completions. Follow the [paper protocol](portable-harness-paper-protocol.md); selecting between two known compact settings is not adaptive search evidence.

Record requests, transferred/captured bytes, model input/output tokens, retries, repairs, CPU/wall time, artifact growth, reviewer time and integer currency micros. Separate forecasts, reservations, observed usage and reconciled billing. Freeze ceilings before live calls; unknown usage retains conservative reservation. Measure end-to-end useful proposals and held-out task outcomes, not just cheaper prompts or higher source counts. No completion percentage, ETA, cloud bill, uptime or research-superiority claim is inferred from the present prototype.

## Review boundary

The [cloud PR plan](cloud-pr-plan-2026-09-10.md) separates plan updates, reusable local work, runtime implementation and external-effect canaries. SPEC-014/024/025 remain draft. Foundation replacement/acceptance, SPEC-013 role alignment, SPEC-007 proposal and SPEC-015 delivery contracts still need their owner review. Historical local-only and Cursor-only documents must be clearly scoped or updated rather than silently treated as the new product requirements.
