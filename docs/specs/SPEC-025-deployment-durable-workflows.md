# SPEC-025: Deployment, Recovery, and Durable Workflow Migration

Status: draft
Wave: 5
Classification: split
Owners: operations steward agent; human maintainer
Depends on: SPEC-024

## Decision

The first production deployment will remain local-first on the maintainer's machine, using the existing launchd foundation plus supervised dispatcher, webhook, worker, outbox, and reconciliation processes. Deployment state is pinned and recoverable. Temporal is the preferred future durable-workflow adapter, but adoption occurs only after measured triggers show the local control plane is the bottleneck. Artifact and adapter contracts remain unchanged by that migration.

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

## Interfaces and data

Provide `orgctl install|start|stop|pause|resume|status|doctor|backup|restore|upgrade|rollback|reconcile`. The local deployment runs:

- scheduler and work-order dispatcher;
- event and projection service;
- GitHub webhook receiver or polling bridge;
- deterministic and Hermes workers;
- notification outbox dispatcher;
- periodic source, PR, credential, cost, and projection reconcilers.

`DeploymentManifest` pins public core commit, organization and constitution versions, schema registry, adapter lock, executor and model compatibility, private policy bundle, enabled connectors, budget policy, process versions, and backup generation.

Temporal adoption review is mandatory when any one severe incident occurs, or when at least two of these persist for a measured operating window: more than one worker host or scheduler; approvals or workflows routinely wait days; hundreds of concurrent in-flight runs; costly duplicate side effects; custom lease/retry/cancellation/reconciliation code dominates maintenance; cross-host replay, query, or backpressure is required; file locking is measured as a bottleneck.

If adopted, a research run maps to a Workflow; retrieval, model calls, GitHub writes, and delivery map to idempotent Activities; human decisions map to Signals or Updates; fan-out maps to Child Workflows; and status reads map to Queries. Histories store stable artifact references and hashes, not large bodies.

## State and failure behavior

Deployment states are `stopped`, `starting`, `healthy`, `degraded`, `paused`, `upgrading`, `rollback_required`, and `failed`. Supervisors use bounded restart backoff. Ambiguous external actions enter reconciliation. A failed migration leaves the prior deployment manifest and data backup available.

## Implementation sequence

1. Package current loop under `orgctl` while preserving existing launchd scripts.
2. Add process health, leadership lease, pause, doctor, and reconciliation.
3. Add atomic deployment manifests, backup, restore, upgrade, and rollback.
4. Run sleep, network-loss, process-kill, and partial-side-effect drills.
5. Measure trigger metrics and write a Temporal ADR only when a trigger threshold is met.

## Migration and rollback

Installers never delete existing launchd jobs until new health checks pass. Upgrade snapshots database, deployment manifest, active leases, and private artifact index. Rollback stops new dispatch, restores compatible binaries and projections, reconciles in-flight external work, and preserves events created under the failed version.

## Observability

Show process health, leadership, wake delay, scheduler lag, queue age, restart count, reconciliation backlog, backup age and verification, version skew, disk use, file-lock wait, incident count, and Temporal trigger indicators.

## Verification

- Kill every process at each external-effect boundary and recover without duplicate application.
- Laptop sleep produces visible delayed schedules and catches up within budget.
- Network loss leaves local status and queue available.
- Backup restores onto a clean test directory and reproduces projection digests.
- Failed upgrade rolls back without losing new events.
- A reference Temporal mapping passes adapter contract tests without becoming required.

## Acceptance criteria

- [ ] One documented command installs and diagnoses the local organization.
- [ ] Pause, resume, backup, restore, upgrade, and rollback are exercised.
- [ ] Leadership and duplicate-scheduler behavior are safe.
- [ ] Sleep and offline behavior are explicit.
- [ ] Temporal adoption uses measured triggers and an ADR.
- [ ] Removing Temporal or Hermes would not invalidate canonical artifacts.

## Pull-request evidence

Attach install and doctor output, process-kill matrix, sleep and network-loss results, clean-directory restore proof, failed-upgrade rollback, trigger dashboard, and draft Temporal mapping.
