# Product blueprint: Agent Skills and Research Control Center

Status: non-normative product design

For current GitHub deployment and merge preparation, start with the
[September 29 release plan](github-release-plan-2026-09-29.md). It supersedes the
persistent-host default as the target topology, links all 36 head-pinned PR
reviews, and specifies durable admission, managed API execution, credential
separation, scenarios and sequential merge/activation gates. Neither it nor the
new secret-free CI workflow claims an activated production worker.

For the current shareable overview, read [Research system: current architecture
and production path (September 29, 2026)](research-system-architecture-2026-09-29.md)
and the [production preparation exercise](production-exercise-2026-09-29.md).
They distinguish implemented supervised execution, measured connector/model
observations, deterministic simulation and unproven research quality. They are
not release, merge, specification-acceptance or production attestations.

The [September 11 overview](living-research-repository-architecture-2026-09-11.md)
is historical. Its 36-open-PR inventory is a dated metadata snapshot, not the
current merge list. Earlier snapshots and this blueprint remain design context.

Historical blueprint assessment baseline: proposed stack tip
`c6cd52017b247804373339e1c3c103d42554b0a1`.

Current development evidence is from the integrated uncommitted worktree.
The September 29 additions must not be attributed to that historical baseline
SHA; exact private source/configuration manifests bind the exercised bytes.

The version 1 readiness validator is deliberately blocked-assessment-only. It
checks that the declaration is internally consistent and fail-closed; it cannot
turn `production_ready` on. A future readiness transition requires an accepted
attestation schema and an external exact-candidate verifier.

Intended first customer: one organization operated by the repository maintainer

> This document is a product and deployment proposal. It is not an accepted specification, authority record, work order, capability grant, promotion, or deployment activation. It cannot authorize implementation of a draft specification. It cannot activate a runtime, external delivery, GitHub mutation, model call, credential, or production environment. The lifecycle and human-merge rules in [`docs/specs/README.md`](../specs/README.md) remain controlling.

The historical [status and PR review plan](status-and-merge-plan-2026-09-08.md)
records open PRs as of September 8. The [August 25 audit](pr-audit-2026-08-25.md)
is retained as historical semantic review, not current merge approval.

The [architecture paper](research-harness-architecture-paper.md) describes the
implemented data path, invariants, agent responsibilities, measured case study,
and limits. The [portable operations design](research-harness-operations.md)
specifies the proposed deployment, scheduling, results, interaction and recovery
boundaries. Both are non-normative technical documents, not production activation.

The [living-organization delivery plan](living-organization-plan.md) maps all
specifications to ordered implementation slices, fault tests and rollback. Its
[machine-checkable execution plan](spec-execution-plan.json) binds current source
bytes and acceptance criteria, but cannot certify completion or grant authority.
The [September 8 development results](living-organization-results-2026-09-08.md)
record the implemented integrity repairs, verification and remaining release gates.

The historical September 7 local architecture review is
[`architecture-review-2026-09-07.md`](architecture-review-2026-09-07.md), with a
machine-readable [architecture status](architecture-status.json). Its then-missing
source-to-report/evaluation integration is superseded in part by the explicit
September 29 pipeline below; neither document advances owner-specification status.
The August PR audit remains historical.
The [local observation runbook](local-observation-runbook.md) explains current
commands, replay semantics, private outputs, and the bounded 72-hour experiment.

## September 29 implemented preview

The service lives in this open-source repository and can run without Codex. The
funded path is explicit and supervised:

```text
captured daily discovery -> primary HTML -> replay-verified evidence bundle
  -> shared cumulative OpenAI Campaign -> researcher -> critic -> optional editor
  -> research_pipeline / candidate_review -> exact frozen candidate + structural checks
  -> supplied gold-free evaluation tasks -> durable private result / human review
```

- One existing Campaign authority covers the user's $100 cumulative model
  allowance across roles, evaluations, dates and restarts. Failed and unknown
  effects retain reservations; creating another directory does not add allowance.
- The managed Agents backend remains separate. Verified retrieval preparation
  makes no provider call; a completed managed result can enter `review_managed()`
  for exact candidate freeze, structural checks and an optional evaluation plan.
  Managed session spending is not bounded by native call reservations.
- Live connector checks included X, OpenAlex, Parallel, Firecrawl Research Index
  and actual basic scrape, GitHub reads and the registered Parallel MCP bridge.
  The initial 11 checks used 14 HTTP requests; later MCP investigations brought
  the total reservation ceiling to 50 HTTP requests and $0.103, not an invoice
  or measured aggregate request count. These are not daily adapters for every
  checked provider and do not establish retrieval relevance.
- Closed recovery bundles retain the registered database/capture/candidate
  closure, explicitly named managed ledgers and a separately snapshotted budget
  authority. Isolated restore remains paused and preserves unknown effects and
  reservations. It does not copy arbitrary private files or activate a worker.
- The real read-only `/service` UI is separate from fixture product-design pages.
  It does not grant merge or deployment authority. The repository-native
  [organization coordinator](../../researcher/service/ORGANIZATION.md) connects
  bounded daily retrieval to the shared-budget pipeline with durable outcomes
  and restart tests; no recurring service has been activated.

See the [service runbook](../../researcher/service/README.md),
[pipeline](../../researcher/service/RESEARCH_PIPELINE.md),
[candidate review](../../researcher/service/CANDIDATE_REVIEW.md),
[connector record](connector-verification-2026-09-29.md), and
[recovery contract](../../researcher/runbooks/service-recovery.md).
Actual gold-free task execution now exists; representative independent held-out
data, calibrated grading and downstream skill-effectiveness evidence remain
missing. Accepted owner contracts, publication approval and cloud activation
remain separate gates.

## Product decision

September 7 product update: the research harness and control-center software are
open-source components, independent of Codex. "Private" below refers to tenant
operations, credentials and evidence, not a proprietary code distribution. The
[portable harness design and runbook](portable-harness.md),
[local evidence](portable-harness-results.md) and
[paper protocol](portable-harness-paper-protocol.md) define the new bounded
experiment slice. Existing production authority and release gates still apply.

Build one suite with two separately releasable products:

1. **Agent Skills Distribution** is the public product. It distributes reviewed context-engineering and harness-engineering skills through GitHub and supported plugin layouts, with evidence, compatibility checks, benchmarks, and versioned releases.
2. **Research Harness and Control Center** is open-source software deployed with private organization state. The target product lets an organization nominate research, run capability-bounded agents, inspect evidence and evaluations, prepare exact-candidate pull requests, and operate or stop the system. The current funded pipeline executes bounded model calls, produces inert exact candidates and can run supplied evaluations; it does not publish or accept its result. Optional draft-PR delivery belongs to the separate native compatibility workflow. The control center never owns merge authority.

The products share schemas and evidence but not authority or release cadence. The public repository is not an operational database. The private control plane is not a second source of truth for public releases. A control-center result becomes public only through a SPEC-002 projection and, when it changes the repository, a human-merged SPEC-019 release path.

The smallest credible product is one complete, supervised path:

```text
human nominates a source
  -> immutable retrieval and evidence
  -> bounded research attempt
  -> independent evaluation
  -> frozen candidate and review packet
  -> draft pull request
  -> human merge
  -> separate human-authorized deployment canary
```

Do not build multi-tenancy, general-purpose agent hosting, autonomous social publishing, or weight training into the first product. Those choices enlarge the security and operational problem without proving the core outcome.

## Product assumptions and decisions to validate

The initial product hypothesis is intentionally narrow:

- One organization, one protected GitHub repository, one primary maintainer, and at most five invited reviewers/operators.
- A maximum of four concurrent attempts is a hosted-beta hypothesis, not the current execution setting. The funded Campaign permits one active model call; any untrusted attempt requires its own reviewed isolation boundary.
- Manual source nomination plus one allowlisted primary-source connector is sufficient for the first end-to-end workflow.
- GitHub remains the public review and merge surface. The private UI improves visibility and control but cannot merge.
- The local pilot is supervised and best effort. Hosted beta targets continuous availability, but it is not a high-availability or multi-region product.
- English-only UI and content are acceptable for MVP.
- Results are asynchronous. The UI acknowledges a command quickly, then exposes progress, blockers, artifacts, cost, and terminal disposition.
- Model and provider spend is reserved per work order. There is no unbounded retry or background model loop.

These are product hypotheses, not inherited requirements. Before hosted beta, the maintainer must explicitly decide data residency, retention, support expectations, acceptable providers, monthly spend, and whether the single-organization boundary still holds.

## Users and jobs to be done

| Persona | Primary job | Successful outcome | Authority boundary |
| --- | --- | --- | --- |
| Skill consumer | Install the collection and have the right skill activate for a task | Correct installation, useful activation, traceable guidance | Reads public releases only |
| Agent developer | Select and adapt a skill without importing stale or unsupported claims | Reproducible example, compatible package, evidence-linked decision | May propose changes; cannot promote them |
| Product owner / human maintainer | Decide what the organization should investigate and what may ship | Clear priorities, bounded spend, evidence-complete review packet, reversible release | Sole merge and production-activation authority |
| Research curator | Turn a source nomination into claims, mechanisms, contradictions, and candidate changes | Immutable source evidence and explicit disposition | Cannot activate, merge, or lower classification |
| Builder agent | Produce a typed candidate from an exact work order and context package | Frozen candidate, receipts, tests, and complete handoff | Writes only its granted attempt workspace and proposal surfaces |
| Independent evaluator | Test a frozen candidate without builder leakage | Reproducible observations and exact-candidate verdict | Cannot edit the candidate or self-attest authored work |
| Release attestor | Verify the exact pull-request head and required gates | Attestation that invalidates on any head change | Cannot merge or activate |
| Runtime operator | Keep the system healthy, bounded, backed up, and recoverable | Explainable queue, safe pause, tested restore and rollback | Operational commands only; production activation remains human-only |
| Community contributor | Submit a source, correction, fixture, or mechanism proposal | Evidence-based acceptance, rejection, or request for more information | No private data or direct runtime access |
| Public follower | Inspect skills, methods, benchmark reports, decisions, and corrections | Useful public artifact with no private correlation data | Public read-only |

Specification owner names are design roles until SPEC-013 and SPEC-024 bind them to versioned role manifests and authenticated identities.

## Product outcomes and success measures

Targets below are planning thresholds for a single-organization beta. A target is
not evidence. `Not measured` means the named production outcome has not been
demonstrated, not that no implementation exists. The September 29 exercise adds
local integration evidence without satisfying these production or scientific
targets.

| Outcome | Metric | Beta target | Current measurement |
| --- | --- | ---: | --- |
| Correct skill discovery | Top-1 router accuracy by supported model, with no skill hidden by aggregate scoring | At least 0.90 for every release-gating model and no per-skill regression over the preregistered bound | Published 2026-05-19 snapshot: Gemini 0.920, Composer 0.913, GPT-5.5 0.913, Claude Opus 4.7 0.840; target not yet met for every model |
| Skill usefulness | Paired Stage-3 effectiveness lift on held-out tasks | Positive preregistered lower confidence bound for each changed skill | One effectiveness task exists; insufficient |
| Composition safety | Cross-skill task regressions and interaction failures | No blocking regression on a representative composition suite | Not implemented |
| Traceability | Candidate PRs with complete source, context, evaluation, cost, and exact-head lineage | 100% | Not measured end to end |
| Human control | External effects with authenticated intent, expected version, idempotency key, and receipt | 100% | Not implemented in a production command path |
| Recoverability | Restore and rollback drills meeting the declared RPO/RTO | 100% of release candidates before activation | Actual isolated artifact/budget restore and offline fault tests passed; representative RPO/RTO, encrypted off-host recovery and deployment rollback remain unmeasured |
| Operator comprehension | Active or blocked work items with a stable `why_not_running` reason | 100% | Not implemented in an event-derived UI |
| Spend containment | Attempts that remain within their immutable reservation | 100%; zero unreserved provider calls | Bounded native Campaign and cumulative-budget fault tests exist; legacy Cursor benchmark activation remains disabled; account-wide/managed-session containment is not established |
| Security boundary | Seeded-secret, authority, SSRF, isolation, and export suites | Zero blocking findings | Repository and integrated service adversarial tests exist; deployed identity/egress/isolation still require validation |
| Release safety | Human-merged exact candidate before public promotion and separate deployment activation | 100% | Constitutional intent exists; end-to-end control plane not implemented |

The router numbers are from the local published report [`researcher/benchmarks/router/results-published/2026-05-19.md`](../../researcher/benchmarks/router/results-published/2026-05-19.md). They must not be generalized to skill effectiveness.

## Capability and status matrix

This matrix tracks specification/production-owner readiness, not the existence
of the supervised September 29 preview described above. `Available` means usable
on the assessed candidate. `Preparatory` means code or contracts cannot yet satisfy
the production owner contract. `Planned` means the owning specification remains
draft even where a bounded preview exists. None of these labels grants activation.

| Capability | Product | Current state | Owning specs | Production gate |
| --- | --- | --- | --- | --- |
| Skill source collection | Skills Distribution | Available in the repository | SPEC-001, SPEC-003 | Current release candidate reaches protected `main`; package and generated inventory agree |
| Claude/Open Plugins packaging | Skills Distribution | Available | SPEC-001, SPEC-002, SPEC-003 | Cross-platform reference validator and clean-install fixtures pass on exact release bytes |
| Deterministic repository gates | Skills Distribution | Available | SPEC-000 through SPEC-003 | Required status check is enforced by branch rules and cannot be bypassed by the proposer |
| Router evaluation | Skills Distribution | Historical measured reports; current runner only validates dry-run plans | SPEC-016, SPEC-017 | Accepted evaluation epoch and live adapter, same-seed comparison, per-skill effects, and human release decision |
| Effectiveness evaluation | Skills Distribution | Preparatory; one task | SPEC-016, SPEC-017 | Representative positive, negative, adversarial, and held-out tasks for changed skills |
| Composition evaluation | Skills Distribution | Not implemented | SPEC-016, SPEC-017 | Cross-skill suite, preregistered analysis, and regression policy |
| Public documentation | Skills Distribution | Repository documentation and one educational site exist | SPEC-002, SPEC-015, SPEC-023 | Versioned release docs, accessibility checks, correction path, and public/private scan |
| Constitutional authorization | Control Center | Revision 1 is terminal `amended` on this candidate | SPEC-000 | Human-merged replacement revision accepted and implemented before dependent runtime work |
| Repository inventory | Both | Revision 1 is terminal `amended`; current builder is useful preparatory evidence | SPEC-001 | Human-merged replacement revision and reproducible candidate inventory |
| Public/private export boundary | Both | Revision 1 is terminal `amended`; export tooling exists | SPEC-002 | Human-merged replacement revision, adversarial leak suite, and correction drill |
| Schemas and artifact identity | Both | Revision 1 is terminal `amended`; cross-runtime tooling exists | SPEC-003 | Human-merged replacement revision and exact-byte compatibility/migration evidence |
| Legacy research loop | Control Center | Supervised migration only: integrated launchd installer/wrappers are inert, network fetch is absent, accepted closure and promotion fail closed | Precursor to SPEC-004 through SPEC-010 | Journal/work-order migration and accepted owner contracts before any operational pilot; the separate local rehearsal is observation-only |
| Event journal and projections | Control Center | Planned | SPEC-004 | Accepted and implemented 004A/004B; replay, corruption, crash, backup, and shadow-parity gates |
| Work orders, leases, budgets, checkpoints | Control Center | Planned | SPEC-005 | Model-free kernel, fenced attempts, recovery, ambiguous-effect reconciliation |
| Command and feedback boundary | Control Center | Planned | SPEC-006 | Authenticated deterministic command path and immutable feedback ledger |
| GitHub App and PR reconciliation | Control Center | Planned | SPEC-007 | Least-privilege identities, signature/replay tests, polling reconciliation, no merge permission |
| Status, traces, metrics, and cost | Control Center | Planned | SPEC-008 | Event-derived projections with freshness and stable blocker reasons |
| Source registry | Control Center | Planned | SPEC-009 | Versioned feed policy, legal/classification controls, connector health |
| Retrieval and immutable evidence | Control Center | Planned | SPEC-010 | SSRF-safe retrieval, bounded capture, extraction receipts, CAS integrity |
| Evidence graph | Control Center | Planned | SPEC-011 | Claim/mechanism/contradiction lineage and deterministic decision reconciliation |
| Context compiler and memory planes | Control Center | Planned | SPEC-012 | Deterministic packing, information firewalls, token budgets, private compilation receipt |
| Roles, prompts, skills, capabilities | Control Center | Planned | SPEC-013 | Versioned role manifests, separation constraints, compiled capability intersection |
| Executor protocol and isolation | Control Center | Planned | SPEC-014 | Provider-neutral conformance and attested trusted/untrusted environments |
| Notification outbox and review packets | Control Center | Planned | SPEC-015 | Durable destination-specific approval, deduplication, redaction, and reconciliation |
| Evaluation registry | Both | Planned owner contract; legacy benchmark fixtures exist | SPEC-016 | Sealed epochs, hidden-test firewall, rubric and split provenance |
| Evaluation runner | Both | Planned owner contract; native gold-free Campaign executor exists, legacy SDK activation remains disabled | SPEC-017 | Multi-model statistical gates, representative independent data, bounded cost and missing-data policy |
| Candidate archive and failure memory | Both | Planned | SPEC-018 | Immutable lineage, rejection memory, archive retention and export boundary |
| Promotion and release | Both | Planned | SPEC-019 | Exact-head attestation, cumulative lineage, human merge, one promotion record |
| Meta-harness laboratory | Control Center | Planned, shadow only | SPEC-020 | Accepted experiment surface, locked evaluator, non-production candidate archive |
| Adaptive routing | Control Center | Planned, shadow only | SPEC-021 | Cross-model transfer evidence and independent production routing decision |
| Collaborative evolution | Both | Planned | SPEC-022 | Sanitized contribution packets, provenance, independence, abuse controls |
| Open-source governance | Skills Distribution | Planned | SPEC-023 | Versioned contribution, correction, moderation, and stewardship workflows |
| Private identities and credential broker | Control Center | Planned | SPEC-024 | Dedicated identities, short-lived attempt-bound grants, rotation/revocation/restore tests |
| Deployment and durable operations | Control Center | Planned owner contract; single-host templates and paused artifact-complete recovery exist | SPEC-025 | Accepted deployment decision, canary, encrypted off-host restore, measured RPO/RTO, upgrade/rollback, kill drills |
| Training / RL laboratory | Control Center | Explicitly deferred | SPEC-026 | New human-merged revision after every readiness gate; revision 1 cannot enable training |
| Operator web UI | Control Center | Real read-only service-status page plus separate fixture product pages; non-authoritative | SPEC-006, SPEC-008, SPEC-015, SPEC-024, SPEC-025 | Complete live dossier projections and authenticated commands, reviewed ingress/identity, accessibility and failure-state tests against real adapters |

The first four specs are terminal amended revisions in this candidate, not current operational contracts. Downstream implementation must begin with lawful replacement revisions and lifecycle transitions. Draft SPEC-004 through SPEC-026 cannot be implemented or activated on the strength of this blueprint.

## Core user journeys

### 1. Install and use a public skill

1. A consumer selects the versioned collection or one skill.
2. The install path validates the host layout and required files.
3. The host activates a skill from its public description.
4. The consumer can inspect the skill's evidence, examples, compatibility, and release notes.
5. A problem links to a correction workflow and the exact affected version.

The product promise is not merely that a skill can be installed. It is that activation is reliable, the skill improves the intended task, and regressions are visible before release.

### 2. Nominate evidence and receive a candidate

1. The maintainer creates a source nomination with purpose, classification ceiling, budget, and expected owner version.
2. The command bus authenticates the actor and records the exact intent.
3. Retrieval resolves an allowlisted source version, captures immutable bytes and receipts, and rejects unsafe or incomplete retrievals.
4. Curators create claims, mechanisms, contradictions, and an evidence disposition.
5. The context compiler builds an allowlisted package for a role-bound attempt.
6. A builder runs in an attested environment and returns typed artifacts, not a conversational claim of completion.
7. Independent evaluation runs on the exact frozen candidate.
8. The UI presents evidence, diff, tests, cost, uncertainty, and blockers in one review packet.
9. If authorized, the proposer opens or updates a draft PR. Any head change invalidates prior attestation.
10. A human reviews and merges. The system records public promotion separately from private deployment.

### 3. Review a candidate

The reviewer sees the objective, non-counting outcomes, source provenance, candidate tree digest, editable surfaces, evaluation epoch, observations, statistical decision, security checks, cost, independent attestor, and remaining uncertainty. The primary actions are request changes, reject with a reusable reason, authorize a draft-PR mutation, or leave the candidate parked. Merge occurs only in GitHub under protected-branch policy.

### 4. Operate and recover the organization

The operator starts from health and critical path, not raw logs. Every blocked item exposes `why_not_running`. Pause stops new dispatch and credential issuance without hiding ambiguous effects. Doctor checks identity, storage, journal, projections, queues, environments, budgets, backups, and external reconcilers. Restore occurs into a clean environment, verifies the journal/CAS closure, rebuilds projections, and requires a human-authorized canary before an active pointer can move.

### 5. Submit a community contribution

A contributor supplies a public source, correction, fixture, or bounded proposal. The system classifies and sanitizes it, preserves provenance, runs abuse and license checks, and returns an evidence-backed disposition. Community content never enters hidden evaluations, private memory, credentials, or production routing without the accepted SPEC-022/023 workflow.

## Interaction and result-delivery model

### Interaction channels

- **Private web UI:** primary product surface for status, evidence, review, budgets, commands, and recovery.
- **`orgctl`:** authoritative operator interface for local recovery and automation-safe commands. It uses the same command grammar and expected-version semantics as the UI.
- **GitHub:** public review, checks, human merge, releases, issues, and public correction history.
- **Notifications:** an attention layer only. Email or chat messages contain an allowlisted summary and a link to the private review packet. They do not carry secret values, hidden evaluations, or executable authority.
- **Conversational assistant:** optional after deterministic command infrastructure exists. It may explain state and propose a parsed intent; privileged mutations require explicit confirmation through the command bus.

### Result contract

Every terminal attempt returns a typed result envelope containing:

- work-order, attempt, role, context-package, and immutable candidate identities;
- terminal disposition and stable reason codes;
- produced artifact references and classification;
- evidence and evaluation references;
- verification command receipts and exact code/tree identity;
- reserved, consumed, and released budget;
- external-effect and reconciliation status;
- limitations, uncertainty, and exact next permissible action.

The UI renders the envelope. It does not parse stdout as canonical state. Large bodies remain in the artifact store and are loaded through authorized references. Public results receive new public identities through allowlisted projections; private locators and input digests never become correlation tokens.

### Attention and escalation

An item enters the review inbox only when a human decision is necessary: source approval, classification conflict, ambiguous external effect, candidate review, budget increase, credential administration, merge, production activation, disaster-prefix recovery, or break-glass action. Routine successful steps remain searchable in the timeline without generating notifications.

## UI information architecture

The UI is a client of status projections and the authenticated command bus. It never writes the journal, queue, Git repository, credential store, or provider APIs directly.

The fixture product-design pages in [`apps/control-center`](../../apps/control-center)
implement overview, runs, review, artifacts and deployment routes with finite
read-only status/event fixtures. Their fabricated states remain non-authoritative;
they show separate accepted-repository and active-deployment identities and disable
mutations. Separately, `/service` reads the real authenticated loopback service API
server-side, with no fixture fallback or browser credential. `/observations` reads
a separate bounded local summary. These implemented readers do not provide the
complete dossier/command interface below, public identity/TLS, managed-session
controls, deployment activation or acceptance authority.

| Surface | Key information | Allowed interactions |
| --- | --- | --- |
| Overview | Active deployment versus accepted public commit, health, queue, critical path, spend, backup age, incidents | Pause request, open blocker, inspect change |
| Inbox | Decisions requiring a human, sorted by risk and expiry | Approve bounded intent, reject, request evidence, park |
| Work | Work-order DAG, attempts, leases, checkpoints, retries, budgets, `why_not_running` | Create bounded work order, cancel, retry eligible attempt, resolve ambiguity |
| Research | Sources, retrieval receipts, evidence bodies, claims, mechanisms, contradictions | Nominate source, classify, request review, reject evidence |
| Candidates | Frozen diff, lineage, editable surface, tests, evaluations, comparisons, cost | Request changes, reject, authorize draft-PR operation |
| Releases | PR head, check runs, attestations, human merge, promotion and deployment lineage | Open GitHub review; no merge button in the control center |
| Agents | Role version, executor, context package, capability grant, environment attestation, current activity | Inspect, cancel, quarantine environment |
| Operations | Journal/projection health, queues, connectors, backup/restore, version skew, incidents | Doctor, reconcile, backup, restore plan, rollback plan, emergency pause |
| Security | Redacted identities, grants, denials, rotation due, audit correlation | Rotation request, revoke/stop request, break-glass workflow |
| Settings | Source policy, budgets, notification destinations, environment policy, feature flags | Versioned expected-state updates with audit preview |

Global UI requirements:

- Show freshness and source sequence on every projection.
- Distinguish requested, authorized, scheduled, running, externally ambiguous, completed, promoted, and deployed states.
- Display accepted public commit and active deployment commit side by side.
- Require exact-target confirmation for destructive or recovery operations.
- Preserve keyboard navigation, visible focus, semantic labels, contrast, responsive layouts, and reduced-motion preferences.
- Render provider outages, stale projections, partial results, and policy denials as first-class states.
- Never render secret material or hidden-evaluation contents, even to an administrator; show references, ownership, and health instead.

## Environments

| Environment | Purpose | Data | External effects | Exit gate |
| --- | --- | --- | --- | --- |
| Developer | Local code, deterministic tests, fake providers | Synthetic/public fixtures | None by default | Unit/static checks and clean candidate boundary |
| Local pilot | One maintainer, supervised end-to-end rehearsals | Private pilot data in an isolated runtime root | Explicit per-operation approval | Accepted owner specs, recovery drills, zero critical findings |
| Hosted development | Integration of GCP adapters with fake or synthetic data | Non-production project | No public or human-destination writes | Contract, security, and infrastructure tests |
| Hosted staging / shadow | Production-shaped data under classification limits | Separate private project and keys | Effects terminate at shadow sinks | Replay parity, fault injection, load/cost bounds, restore |
| Hosted proposal beta | Single organization, real evidence, bounded candidates | Production private project | Draft PR and approved notification intents only | Human activation, canary, SLOs, rollback, incident readiness |
| Public release | Versioned skills, docs, benchmarks, safe projections | Public only | Human merge and release | Exact-head checks, public-boundary scan, provenance |
| Recovery | Clean project/directory used for restore drills | Encrypted backup copy | Disabled until reconciliation and canary | Digest parity, declared RPO/RTO, human activation |

Development, staging, and production use separate cloud projects, service accounts, secrets, databases, buckets, queues, and GitHub App installations. No environment promotes mutable state by copying a database. Promotion moves an exact code/configuration identity after verification; runtime state is migrated through registered events and artifacts.

## Delivery plan aligned with SPEC-000 through SPEC-026

Each phase begins only after its owner specifications have advanced through the repository lifecycle. One implementation PR should normally implement one accepted specification or its named ordered slice. The plan below is sequencing, not authorization.

| Phase | Specs | Product increment | Proof before advancing |
| --- | --- | --- | --- |
| 0. Authoritative foundation repair | SPEC-000 through SPEC-003 | Human-merge the reviewed PR train, then create lawful replacement revisions for the terminal amended contracts | Protected-main identity, lifecycle validation, authority, inventory, export, schema, migration, and public-boundary gates |
| 1. Durable supervised control | SPEC-004 through SPEC-008 | Journal, projections, model-free work kernel, local commands, GitHub observation/proposal lifecycle, explainable status/cost | Replay, concurrency, crash matrix, mirror parity, command authorization, webhook/poll reconciliation, restore |
| 2. Evidence-to-agent vertical slice | SPEC-009 through SPEC-015 | One source class to immutable evidence, context-compiled role, isolated executor, and private review packet | SSRF and capture limits, evidence lineage, context firewall, executor conformance, notification reconciliation |
| 3. Evaluated candidate-to-PR | SPEC-016 through SPEC-019 | Sealed evaluation epoch, independent runner, failure archive, exact-head release attestation | Split/fixture integrity, paired analysis, candidate tamper denial, full-tree lineage, human merge observation |
| 4. Shadow improvement laboratory | SPEC-020 through SPEC-022 | Bounded meta-harness and routing experiments plus sanitized community proposals | Locked evaluator, negative controls, cross-model transfer, independence, zero direct production mutation |
| 5. Sustainable operation | SPEC-023 through SPEC-025 | SPEC-023 adds public governance; SPEC-024/025 add private identities/broker, local pilot, and a separately accepted hosted-beta deployment amendment | Contribution/correction controls where enabled; credential rotation/revocation, clean restore, failed upgrade rollback, canary, kill path, SLO and cost evidence |
| 6. Optional training research | SPEC-026 | Readiness dossier only while activation remains deferred | Every executable readiness gate plus a new human-merged revision before any data/provider action |

### Spec-by-spec product increments

| Spec | Product responsibility |
| --- | --- |
| SPEC-000 | Define the closed authority vocabulary and human-only powers used by every UI and runtime action. |
| SPEC-001 | Bind the distributable repository and generated product inventory to exact source bytes. |
| SPEC-002 | Keep public releases, notifications, and UI projections from leaking private identities, locators, or inputs. |
| SPEC-003 | Give every event, artifact, candidate, receipt, and cross-runtime payload a portable immutable identity. |
| SPEC-004 | Establish the append-only event journal, deterministic projections, backup, and legacy shadow bridge. |
| SPEC-005 | Make work resumable through immutable work orders, fenced attempts, budgets, checkpoints, and reducers. |
| SPEC-006 | Convert human UI/CLI input into authenticated, replayable commands and scoped feedback. |
| SPEC-007 | Observe and reconcile GitHub events and produce proposal-only PR effects through a least-privilege App. |
| SPEC-008 | Supply the UI with fresh status, traces, blockers, health, latency, and cost projections. |
| SPEC-009 | Define which research sources are eligible, versioned, licensed, classified, and healthy. |
| SPEC-010 | Capture bounded immutable source evidence with retrieval and extraction receipts. |
| SPEC-011 | Connect evidence to claims, mechanisms, contradictions, decisions, and merged outcomes. |
| SPEC-012 | Compile the smallest authorized context and preserve memory-plane ownership and firewalls. |
| SPEC-013 | Bind product roles to versioned prompts, skills, tools, capabilities, and separation constraints. |
| SPEC-014 | Run attempts through a provider-neutral executor protocol and attested isolation profiles. |
| SPEC-015 | Deliver redacted review packets and content drafts through a durable approved outbox. |
| SPEC-016 | Freeze evaluation suites, splits, rubrics, judge policy, and hidden-test boundaries. |
| SPEC-017 | Execute reproducible multi-model comparisons with statistical, missing-data, and cost gates. |
| SPEC-018 | Retain accepted and rejected candidate lineage so the product learns from failures without rewriting history. |
| SPEC-019 | Bind quality evidence to one exact PR head, human merge, public promotion, and cumulative lineage. |
| SPEC-020 | Experiment on harness changes only in a bounded, independently evaluated laboratory. |
| SPEC-021 | Test adaptive routing and cross-model transfer before any routing change can reach production. |
| SPEC-022 | Ingest community proposals through classification, provenance, independence, and abuse boundaries. |
| SPEC-023 | Make contribution, correction, release, and stewardship workflows sustainable for the public product. |
| SPEC-024 | Bind authenticated identities, secrets, destinations, and one-use attempt capabilities in a private control plane. |
| SPEC-025 | Package install, activation, canary, pause, backup, restore, upgrade, rollback, and durable-workflow escalation. |
| SPEC-026 | Keep training deferred until evidence, privacy, power, budget, independence, and rollback gates justify a new revision. |

## Product-level test strategy

Testing follows the cheapest mechanism capable of falsifying each claim. Deterministic checks precede model judges. Every production incident becomes a regression fixture where possible.

### Public product gates

- Schema, frontmatter, package-manifest, generated-inventory, public/private export, license, and secret scans.
- Clean installation in every supported host layout on pinned platform references.
- Router tests with per-skill confusion matrices, same-seed comparisons, and format-failure accounting.
- Effectiveness tests with positive, negative, adversarial, held-out, and task-family-grouped fixtures.
- Composition tests that exercise plausible skill combinations and conflicting instructions.
- Documentation link, accessibility, responsive-layout, and version-consistency tests.
- Reproducible package build, artifact digest, changelog, rollback, and correction drills.

### Control-plane gates

- Authority decision coverage, actor impersonation, stale constitution, missing/expired/replayed grant, and protected-surface denial.
- Schema golden tests and Python/TypeScript canonicalization parity.
- Event property tests, duplicate and reordered delivery, optimistic conflicts, hash corruption, deterministic replay, and projection rebuild.
- Lease, fence, checkpoint, cancellation, retry, clock, budget, and ambiguous-external-effect fault injection.
- Retrieval SSRF, redirect, DNS rebinding, timeout, size, MIME, truncation, license, classification, and corrupted-CAS tests.
- Context determinism, contradiction completion, stale-summary invalidation, hidden-evaluation firewall, and capability-denied tool calls.
- Environment attestation, no ambient secrets, read/write mounts, egress allowlists, resource exhaustion, cancellation, output filtering, and sandbox escape fixtures.
- Evaluation split leakage, candidate tamper, judge order bias, calibration, missing/invalid results, repeated paired analysis, and negative controls.
- GitHub webhook signature, duplicate/missed delivery, polling reconciliation, stale PR head, ambiguous mutation, and no-merge-permission tests.
- Notification destination approval, deduplication, redaction, retry, revocation, and ambiguous delivery tests.
- UI contract, expected-version conflict, stale projection, keyboard/accessibility, responsive layout, error recovery, and degraded-provider tests.
- Deployment dual-leader, queue redelivery, process kill, network loss, disk exhaustion, backup corruption, clean restore, failed upgrade, canary failure, rollback, and emergency-stop drills.

### End-to-end release gate

The beta gate runs one nominated primary source through immutable capture, two appropriately separated reviews, a frozen candidate, deterministic and model evaluation, exact-head attestation, draft PR, human merge, public promotion, hosted canary, notification, and rollback. The trace must reconstruct every decision, byte identity, cost, external effect, and human action without reading chat history.

## Open product decisions

These decisions must be resolved before their dependent implementation or procurement:

1. Data residency and retention for raw/restricted evidence, prompts, traces, and provider inputs.
2. Model/provider allowlist, privacy settings, training-use terms, and maximum attempt/monthly spend.
3. Whether hosted beta amends the local-first decision in SPEC-025 or follows an operational local pilot first.
4. Required availability and support window. A 99.5% beta target is materially different from a 24/7 multi-region commitment.
5. Whether GKE Autopilot plus gVisor satisfies the accepted SPEC-014 threat model for every enabled work kind.
6. Exact GitHub App permission split between observer, proposer, check reporter, and reconciler identities.
7. Notification provider and which destinations may receive which classifications.
8. Retention, deletion, legal hold, and public correction policy for community and research evidence.
9. Stage-3 task coverage and effect-size policy sufficient to claim that each skill is useful, not merely routable.
10. Whether a conversational interface materially improves operator outcomes after the deterministic UI and CLI are usable.

## Production definition of done

The suite is ready for a single-organization production beta only when all of the following are true:

- Required specifications are `operational` on protected `main`; draft or terminal amended predecessors do not count.
- The exact deployment commit has a complete promoted-quality lineage and a human activation record.
- Branch protection requires the canonical checks, proposer identities cannot merge, and emergency administration is audited.
- The public package passes compatibility, router, effectiveness, composition, provenance, and public-boundary gates.
- The control center completes the end-to-end trace with no authority or classification bypass.
- Every enabled executor profile has current isolation and capability conformance evidence.
- Backup, clean restore, failed upgrade, rollback, emergency stop, and ambiguous-effect reconciliation drills pass.
- SLOs, cost ceilings, on-call ownership, retention, incident response, and provider status are visible in the UI.
- No critical or high security finding is open; accepted residual risks have owners and expiry dates.
- The human maintainer can explain and reverse the active state without relying on an agent session.

Until those conditions hold, `production_ready` and every activation flag remain false in [`production-readiness.json`](production-readiness.json).
