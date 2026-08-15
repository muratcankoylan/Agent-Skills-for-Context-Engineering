# SPEC-025: Deployment, Recovery, and Durable Workflow Migration

Status: draft
Revision: 1
Revises: none
Wave: 5
Classification: split
Owners: operations steward agent; human maintainer
Depends on: SPEC-004, SPEC-005, SPEC-008, SPEC-014, SPEC-015, SPEC-019, SPEC-024

## Decision

The first production deployment will remain local-first on the maintainer's machine. One launchd-supervised `orgd` process hosts the journal, projections, scheduler, GitHub polling, reconciler, and outbox dispatcher in-process; model and untrusted-tool executions run as separately attested child processes. Components split into additional daemons only after a measured isolation, reliability, resource, or multi-host requirement pays for the coordination cost. Deployment state is pinned, event-replayable, and recoverable without session or ambient-process memory. Continuous autonomous operation remains disabled until install, pause, budget, backup, restore, replay, reconciliation, upgrade, rollback, and kill-switch drills pass. Temporal is only a future durable-workflow adapter candidate: crossing a trigger requires a review and comparison, not adoption, and any adoption still requires a human-merged ADR.

## Context and current repository touchpoints

`researcher/orchestration/launchd/` already installs daily discovery, stepping, and status loops. The new organization adds several processes and external waits. A deployment design is required before continuous autonomous operation, but a hosted workflow engine would add avoidable complexity while one laptop and a small queue are sufficient.

## Goals

- Install, start, stop, pause, resume, upgrade, diagnose, back up, and restore the organization predictably.
- Survive process termination, sleep, network loss, and partial external effects.
- Pin public core, private policy, adapters, schemas, models, and organization epoch.
- Make a future Temporal migration a workflow-adapter change rather than a rewrite.

## Non-goals

- High availability or multi-region hosting in the initial release.
- Keeping a laptop awake solely to satisfy a nominal schedule.
- Assuming Temporal removes the need for idempotent activities.

## Invariants

1. Every process is restartable and derives work from durable state.
2. Only one active scheduler holds the deployment leadership lease.
3. Sleep and downtime create delayed work, not fabricated on-time completion.
4. Upgrades pin exact versions and have a rollback pointer.
5. External writes remain idempotent and reconciled regardless of workflow engine.
6. Operator pause stops new dispatch without corrupting running checkpoints.
7. A clean install can restore public state from Git and private state from backup.
8. Daemons use explicit identities, immutable deployment configuration, fixed working directories, minimal environment and capabilities, bounded restart backoff, and no model-visible secret or ambient user-session state.
9. Leadership, work leases, and budget reservations are fenced and reconstructible after restart; two schedulers cannot dispatch or reserve the same work.
10. Binary or configuration rollback against a surviving live journal never rewinds or replaces that journal and therefore has zero accepted-event loss. Disaster restore from a backup guarantees only its declared recovery-point cutoff unless a separately verified later journal source exists.
11. Upgrade and rollback preserve events written by the newer deployment. An irreversible schema or artifact migration blocks automatic rollback and requires an accepted forward-recovery plan.
12. Operator pause, emergency stop, and process termination are distinct: pause stops new dispatch, emergency stop revokes issuance and delivery, and neither fabricates cancellation or completion of in-flight effects.
13. Deployment consumes a contiguous SPEC-019 promoted-quality lineage, not merely the latest accepted commit or latest attestation. Accepted-but-unpromoted bytes cannot enter an active epoch through a later PR base.

## Interfaces and data

Provide `orgctl install|activate-deployment|start|stop|pause|resume|status|doctor|backup|verify-backup|restore|replay|upgrade|rollback|reconcile|emergency-stop`. Every command has a stable operation identity, authenticated principal, separately evaluated authorization, and idempotent receipt. Under a healthy journal, state-changing receipts append through SPEC-004. Initial bootstrap and commands needed while the journal is unavailable or halted first write the separate authenticated safety ledger: `restore` and `emergency-stop` must remain durable and fail closed without pretending a journal append succeeded. `change_deployment/production_deployment` authorizes `restore` to stage and verify a generation only; it cannot publish/open it, clear a journal halt, or substitute for `recover_journal/event_journal`. A halted-journal restore must compose with the exact SPEC-004 last-known-tail, continuation audit, one-use recovery ticket, and dedicated reopen transaction. A prefix without continuation additionally requires the explicit disaster-recovery declaration and deployment transition below. After a verified reopen, safety-ledger receipts are imported or bound once under the recovery event. Fault fixtures exercise unreadable-journal restore and emergency stop, crash/retry, idempotent import, and wrong-action attempts to bypass recovery.

The existing constitution already reserves human `activate_production/production_deployment` and `emergency_disable/emergency_control`. Before other mutating commands activate, the human-merged SPEC-000 revision 2 `AuthorityVocabularyRegistry` must register `operate_deployment/production_deployment` for the authenticated runtime operator inside one current activation epoch, `change_deployment/production_deployment` for an authenticated human maintainer, and `attest_canary_health/deployment_canary` for the independent canary-health attestor. `start`, `stop`, `pause`, `resume`, `replay`, `reconcile`, `backup`, and `verify-backup` use the former and cannot change the epoch; `install`, `upgrade`, `rollback`, and `restore` use the latter; activation or manifest/epoch changes require the existing human-only activation action; emergency stop uses only the existing emergency action. The health-attestor action can emit one conclusion for an exact closed observation interval and cannot create a canary, change its policy, or advance a deployment pointer. `status` and `doctor` use the accepted query action and remain non-mutating. Unknown mappings default deny.

The local deployment runs one `orgd` supervisor with in-process scheduler, event store, projections, GitHub polling, outbox, and periodic source, PR, credential, cost, and projection reconciliation. It launches deterministic or Hermes executor children through SPEC-014. A webhook listener, dedicated dispatcher, or remote worker is absent until its measured split criterion is accepted.

Each schedule declares `miss_policy: skip|coalesce_latest|replay_bounded`, maximum backlog, maximum replay count, maximum lateness, and budget behavior. Sleep or downtime applies that policy deterministically; it never emits an unbounded catch-up burst.

`DeploymentManifest` pins public core commit, organization and constitution versions, schema registry, journal and projection schema versions, adapter lock, executor and model compatibility, private policy bundle, enabled connectors, hierarchical budget and reservation policy, daemon identities and capability sets, process versions, backup generation, replay checkpoint, and rollback compatibility window.

`activate-deployment` has one canonical authenticated command contract. It binds deployment identity, accepted public commit, SPEC-019 promotion record, its exact promoted-root parent and covered acceptance interval, a complete promotion-lineage proof from the current active promotion root or bootstrap anchor to the target, exact manifest and configuration digests, requested scope and mode, expected deployment version, stable operation ID and exact request digest, current constitution and policy decision, runtime grant, canary policy and budget, and rollback pointer. The proof is a contiguous chain of valid promotion records or one valid cumulative-reconciliation record that closes the whole gap; an accepted-but-unpromoted commit not covered by such a record is a hard denial. Only an authenticated human with a current `activate_production/production_deployment` allow may create `DeploymentActivationRequest`; agents and daemon identities are denied. Same operation ID and bytes returns the original receipt, while changed bytes collide.

The accepted request first creates a strictly bounded `CanaryEpoch` under those exact bytes without changing the active pointer. Canary attempts can receive only the requested narrowed mode, budget, destinations, and capabilities. `CanaryHealthReceipt` is immutable and binds the epoch and activation-request digests; accepted commit, promotion, manifest, configuration and policy digests; preregistered gate set and evaluator version; observation start and end sequence; accepted SPEC-005 clock-domain observations and deadline/currentness proofs; every raw measurement `ArtifactRef`; bounded aggregate measurements; expected deployment version; prior active pointer; conclusion `pass|fail|expired|insufficient_evidence`; stable operation key and receipt digest; and the authenticated independent health-attestor identity, exact `attest_canary_health/deployment_canary` decision, and runtime grant. The observation interval must be closed, current, and produced only by the authorized canary; every required gate must resolve to its frozen definition and evidence. Exact replay returns the first receipt, while the same operation or epoch conclusion identity with different bytes collides.

On a passing receipt, one reducer transaction revalidates the current accepted commit, deployment version and prior pointer; the complete current promotion lineage and absence of any unresolved accepted interval; request, epoch, policy, clock proofs, evidence closure, attestor decision and grant; and exact pass conclusion before it creates the private `DeploymentActivation` and advances the active pointer. A stale lineage parent, missing promotion record, ordinary attestation built on an unpromoted base, uncovered accepted commit, forged cumulative reconciliation, stale, self-attested, wrong-policy, incomplete, expired, or missing-evidence receipt cannot mutate deployment state. Failure, expiry, or insufficient evidence closes the canary and leaves the prior epoch unchanged. The final activation binds request, human authorization, accepted commit, promotion record and lineage proof, manifest/configuration, canary and health receipts, active deployment commit, rollback pointer, and state. `orgd` start, restart, or resume may reconstruct only that exact existing epoch and cannot mint one, widen mode, or change commit. Crash/retry fixtures cover request append, canary start/result, health-attestation commit, and final pointer commit.

`BackupGenerationBarrier` is the one cross-store cutoff. It binds journal sequence and chain digest; transitive CAS/artifact closure and byte digests; private index, policy, schema, adapter, and deployment-manifest generations; accepted and active commits; active leases and reservations; pending append tickets; outbox and ambiguous-effect inventory; creation authority; encryption envelope; and recovery-point objective classification. Publication succeeds only when every named component is closed and verified at that barrier. The generation contains no live capability and its recovery key is stored separately.

After a baseline period, the deployment manifest records numeric review thresholds and windows for dispatch/recovery SLO misses, lock-wait fraction, duplicate-effect incidents, in-flight work, and orchestration maintenance budget. A Temporal comparison is required when a second host becomes necessary, a confirmed duplicate external effect is caused by local coordination, cross-host query/replay/backpressure becomes a requirement, or an accepted threshold remains exceeded for its declared consecutive windows. Crossing a trigger opens an ADR and benchmark; it does not predetermine adoption.

If adopted, a research run maps to a Workflow; retrieval, model calls, GitHub writes, and delivery map to idempotent Activities; human decisions map to Signals or Updates; fan-out maps to Child Workflows; and status reads map to Queries. Histories store stable artifact references and hashes, not large bodies.

## State and failure behavior

Deployment states are `stopped`, `activation_requested`, `canary`, `starting`, `replaying`, `reconciling`, `healthy`, `degraded`, `paused`, `emergency_stopped`, `upgrading`, `rollback_required`, and `failed`. Final activation requires the exact human request, current accepted commit, promotion reference, manifest match, and passing canary receipt. Supervisors use bounded restart backoff and trip a visible crash-loop circuit breaker. Ambiguous external actions enter reconciliation and block duplicate dispatch. A failed migration leaves the prior compatible binaries and manifest plus a verified backup available, but never restores an older journal over newer accepted events.

## Implementation sequence

1. Package the current loop under `orgctl` while preserving existing launchd scripts, and implement authenticated command parsing plus the exact action/resource mapping.
2. Implement `activate-deployment` request validation, expected-version compare-and-append, operation-key replay/collision handling, bounded `CanaryEpoch`, policy-frozen measurement closure, independent `CanaryHealthReceipt` attestation, and atomic final active-pointer transition. Keep `start`, `restart`, and `resume` limited to reconstructing an already activated epoch.
3. Add `orgd` health, leadership lease, schedule miss policies, pause, doctor, and reconciliation.
4. Add atomic deployment manifests, backup, restore, upgrade, and rollback.
5. Run activation, failed-canary, sleep, network-loss, process-kill, and partial-side-effect drills, including every activation transaction boundary.
6. Measure trigger metrics and open a Temporal comparison ADR only when a trigger threshold is met.

## Migration and rollback

Installers never delete existing launchd jobs until new health checks pass. Upgrade records a consistent generation barrier, verified backup, deployment manifest, active leases and reservations, ambiguity inventory, and private artifact closure before a canary start. Rollback while the live journal survives stops dispatch, restores compatible binaries and rebuildable projections, replays that complete journal, reconciles in-flight external work, and preserves every event created under the failed version. Disaster restore starts in a fresh generation, restores only through the backup's declared sequence, and replays later events only from a separately verified continuation source whose first link matches the barrier chain digest. Continuous publication requires the SPEC-004 `continuous_reopen` ticket. If no continuation exists, a human must separately authorize SPEC-004 `disaster_prefix` plus the exact DeploymentManifest/pointer transition; acknowledged work after the recovery point is reported as a bounded possible-loss interval and becomes an incident plus external-reconciliation input. It is never claimed to have been preserved, and state remains degraded until reconciliation closes. Restored projections are compared with a clean replay digest before health can become `healthy`.

## Observability

Show process health, leadership, wake delay, scheduler lag, queue age, restart count, reconciliation backlog, backup age and verification, version skew, disk use, file-lock wait, incident count, and Temporal trigger indicators.

## Verification

- Kill every process at each external-effect boundary and recover without duplicate application.
- Laptop sleep produces visible delayed schedules and catches up within budget.
- Network loss leaves local status and queue available.
- Backup restores onto a clean test directory and reproduces projection digests.
- Failed upgrade rolls back without losing new events.
- Corrupt, incomplete, stale, or wrong-key backups fail before replacing live state.
- `change_deployment` alone cannot clear a journal halt or publish a staged restore; exact continuous recovery requires the SPEC-004 ticket, while an older prefix requires the explicit possible-loss disaster path and cannot become healthy prematurely.
- Rollback against the surviving live journal preserves post-backup events; a standalone disaster restore stops at its exact recovery point and cannot claim later events without a verified continuation source.
- A generation with a missing artifact, mismatched private-index generation, active capability, unbound lease/reservation, or incomplete ambiguity inventory fails before publication or restore.
- Duplicate schedulers, crash loops, stale leases, and stale budget reservations cannot dispatch or overspend.
- An otherwise valid `activate-deployment` request from an agent or daemon is denied; only an authenticated human with a current `activate_production/production_deployment` allow can create the request.
- A stale expected deployment version is denied without creating a canary or changing the active pointer. Exact operation-key replay returns the original receipt, while different request bytes under the same key produce a collision.
- A passing `CanaryHealthReceipt` advances the active pointer exactly once and the resulting activation preserves every commit, manifest, configuration, scope, mode, capability, budget, policy, evidence, clock, and rollback binding from the authorized request and canary.
- An accepted-but-unattested merge followed by an ordinary attested PR remains undeployable. Only a SPEC-019 cumulative-reconciliation record covering the complete last-promoted-tree-to-target-tree delta can close that lineage gap.
- A missing, reordered, stale-parent, forked, or partially covered promotion chain is denied before canary creation and again before active-pointer mutation.
- A forged, self-issued, stale, wrong-policy, wrong-epoch, open-interval, missing-gate, missing-measurement, wrong-clock, or changed-byte health receipt is denied before pointer mutation; exact receipt replay returns the first result.
- A failing or expired `CanaryEpoch` closes with its typed disposition and leaves the prior active pointer byte-identical; it cannot create `DeploymentActivation`.
- Crashes before and after request append, canary creation, canary-health receipt, and final active-pointer commit recover to zero or one instance of each fact and never duplicate or partially advance activation.
- `orgd` start, restart, and resume without an accepted activation cannot mint an epoch; with one, they reconstruct its exact commit, manifest, mode, scope, capabilities, and budget and deny any attempted widening or commit substitution.
- Emergency stop prevents new credential issuance, external delivery, and dispatch while leaving ambiguous effects visible for reconciliation.
- A reference Temporal mapping passes adapter contract tests without becoming required.

## Acceptance criteria

- [ ] One documented command installs and diagnoses the local organization.
- [ ] Pause, resume, backup, restore, upgrade, and rollback are exercised.
- [ ] Leadership and duplicate-scheduler behavior are safe.
- [ ] The `activate-deployment` path is exercised end to end from authenticated human request through bounded `CanaryEpoch` and atomic final pointer transition.
- [ ] Agent and daemon activation, stale expected version, changed-byte operation replay, failed or expired canary, and start/resume minting or widening are mechanically denied without changing the prior active pointer.
- [ ] Activation crash-boundary and exact-replay tests prove idempotent recovery and one active deployment version.
- [ ] Canary health is attested by the narrow independent principal against a closed, current, policy-frozen evidence set; neither the candidate, proposer, daemon, nor activating human can self-issue the conclusion.
- [ ] Activation proves a complete SPEC-019 promoted-quality lineage from the active or bootstrap root to the target; accepted-but-unpromoted bytes and ordinary attestations based on them are mechanically undeployable.
- [ ] Daemon identities, capabilities, environments, working directories, restart ceilings, and crash-loop behavior are explicit and tested.
- [ ] Sleep and offline behavior are explicit.
- [ ] Temporal adoption uses measured triggers and an ADR.
- [ ] Removing Temporal or Hermes would not invalidate canonical artifacts.
- [ ] Restore and rollback are verified by immutable-event replay and external reconciliation, never journal rewind.
- [ ] Budget reservations, leases, pause, and emergency stop survive restart without duplicate work or fabricated terminal state.

## Pull-request evidence

Attach install and doctor output; the parsed `activate-deployment` request and human `activate_production/production_deployment` decision; agent and daemon denial receipts; stale-version, exact-replay, and changed-byte collision fixtures; valid contiguous lineage, accepted-unattested-gap denial, cumulative-reconciliation pass, and missing/reordered/stale-parent lineage denials; passing, failing, expired, forged, stale, self-issued, wrong-policy, wrong-clock, open-interval, and missing-evidence `CanaryHealthReceipt` fixtures with before/after active-pointer digests; request-append, canary-create, measurement-close, health-attestation, and final-pointer crash/recovery evidence; start/restart/resume non-minting and no-widening fixtures; process-kill matrix; sleep and network-loss results; clean-directory restore proof; failed-upgrade rollback; trigger dashboard; and draft Temporal mapping.
