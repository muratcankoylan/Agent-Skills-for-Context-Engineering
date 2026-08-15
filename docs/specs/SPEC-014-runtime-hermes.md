# SPEC-014: Execution Environment, Executor Protocol, and Hermes Integration

Status: draft
Revision: 1
Revises: none
Wave: 2
Classification: split
Owners: runtime integration agent; operations steward agent
Depends on: SPEC-003, SPEC-005, SPEC-006, SPEC-008, SPEC-012, SPEC-013

## Decision

Every model or tool execution will consume one immutable `ExecutionAttemptBundle` compiled against a SPEC-005 `AttemptReservation` and run under a versioned `ExecutionEnvironment` contract. SPEC-005 activates the lease only after it verifies and binds that bundle. Hermes Agent will be the first interactive and scheduled agent harness integrated through the runtime-neutral executor protocol. It receives frozen work, role, context, operation grants, environment, mode, and output contracts. Hermes sessions, ambient configuration, memory, cron state, and internal delegation are never canonical organizational state.

The organization remains operable through a reference local executor if Hermes is removed. Lost or restarted execution is not resumed from chat or harness memory: the old attempt is reconciled and closed, and a new attempt is created from reducer state and a validated checkpoint.

## Context and current repository touchpoints

The current loop is repo-native, Python-based, and launchd-scheduled. Hermes can add model and tool execution, operator interaction, and bounded internal delegation, but coupling authority or state to those conveniences would prevent replay, cross-harness evaluation, safe recovery, and later workflow-engine comparison.

## Goals

- Execute equivalent work-order contracts through Hermes and a reference adapter.
- Preserve exact bundles, calls, outputs, costs, tool effects, checkpoints, cancellation, and reconciliation receipts.
- Keep the queue, journal, reducers, and accepted decisions outside the harness.
- Make runtime, model, tool, and environment differences measurable.
- Make mounts, network, resources, process boundaries, credentials, reset, cleanup, and output extraction attestable.

## Non-goals

- Forking Hermes or embedding organizational policy inside it.
- Making Hermes cron, session storage, or memory the durable scheduler or source of truth.
- Letting an executor apply reducer state, accept a decision, merge a PR, or broaden its own grant.
- Treating Hermes internal subagents as independent organizational reviewers.

## Invariants

1. Adapter inputs and outputs use registered SPEC-003 schemas and immutable artifact references.
2. Executors emit results, effect proposals, and receipts; reducers alone apply organizational state.
3. Every call pins attempt and work-order versions, role and context chain, model, harness, adapter, tools, environment, output contract, and effective operation grant.
4. Workspaces are unique per attempt and cannot be reused without a verified reset and new attestation.
5. Timeout, cancellation requested, cancelled, failed, lost, and unknown outcomes are distinct.
6. Internal subagents inherit a subset of the parent bundle and cannot satisfy proposer-reviewer or evaluator independence requirements.
7. Cron or any harness scheduler may wake the dispatcher only; it cannot own leases, cursors, retries, or research mutations.
8. `trusted_local` runs only allowlisted reviewed deterministic repository code. Candidate, community, self-modifying, and hidden-evaluation code requires eligible isolation.
9. Only declared outputs are frozen and collected; extraction, retention, reset, and destruction each return a receipt.
10. Ambient Hermes memory, configuration, skills, plugins, MCP servers, and user or project settings are disabled by default or pinned explicitly in the bundle.
11. Each side-effecting adapter operation uses a stable operation key plus canonical collision digest and declares whether it is provider-idempotent, reconcilable, or non-reconcilable.
12. Exact operation-key and collision-digest replay returns the original receipt; reuse with a different digest is a collision and performs no effect.

## ExecutionAttemptBundle

The immutable bundle includes:

- attempt-reservation ID and digest, work-order and proposed-attempt IDs and versions, causing event, expected stream version, preparation expiry, and fencing token;
- exact `RolePackage`, accepted profile, prompt payload, `ContextPackage`, and any narrowing-delta digests;
- mode and exact effective operation grants, including resource and destination scopes;
- environment manifest and input artifact manifest;
- output schema, declared output paths, maximum output count and bytes, and retention policy;
- model, tokenizer, harness, adapter, tool, plugin, skill, and tool-schema versions and digests;
- network, process, filesystem, credential-reference, call, retry, repair, token, time, and currency ceilings;
- checkpoint policy, cancellation deadline, reconciliation policy, and result-classification policy; and
- operation-key namespace, canonical collision-digest algorithm, and the adapter effect-class registry digest.

The bundle contains portable credential references, never values or provider locators. Before activation, its reservation, role, context, prompt, environment, grant, fence, and budget digests must match the reservation exactly. SPEC-005 then binds the bundle digest into the immutable `AttemptDescriptor`; a bundle from an expired, superseded, or different reservation is never executable. No executor or environment mutation may run before that activation receipt exists and matches the bundle. A private `ExecutionLocator` binds the activated bundle and attempt to the provider instance, process or remote handle, attestation, and reconciliation metadata. It is reconstructable from private reducer state after a supervisor restart and cannot grant authority by possession.

Effective capabilities are the intersection of constitutional policy, role ceiling, work order, deployment and mode policy, environment and executor support, and broker-issued operation grant. Any required operation absent from that intersection fails before start.

## Modes and effects

The normative lattice is `observe < shadow < proposal < production`. Mode is a maximum effect class, not a capability grant.

- `observe` may inspect explicitly granted inputs and emit receipts and local results.
- `shadow` may execute the same computation, but its outputs remain in an isolated namespace and may reach only shadow reducers and indexes; they cannot reach authoritative reducers, active indexes, the outbox, GitHub, or accepted decisions.
- `proposal` may create candidate artifacts, branches, PRs, or review packets only when each operation is explicitly granted.
- `production` permits approved operational effects within the same explicit grant; it never permits human-only merge.

Moving upward requires deployment policy and evidence; lowering mode cannot be bypassed through a tool alias or internal subagent.

## Interfaces and data

Define `ExecutorAdapter`:

```text
capabilities() -> ExecutorCapabilities
prepare(execution_attempt_bundle, operation_key, collision_digest)
  -> ExecutionHandle + PrepareReceipt
start(handle, operation_key, collision_digest) -> StartReceipt
poll(handle) -> ExecutionStatus
checkpoint(handle, operation_key, collision_digest)
  -> SPEC-005 CheckpointEnvelope + CheckpointOperationReceipt
cancel(handle, reason, operation_key, collision_digest) -> CancelReceipt
collect(handle, operation_key, collision_digest)
  -> StructuredResult + CollectionReceipt
reconcile(execution_locator) -> ReconciliationResult
cleanup(handle, retention_policy, operation_key, collision_digest)
  -> CleanupReceipt
```

Define `EnvironmentProvider`:

```text
capabilities() -> EnvironmentCapabilities
provision(environment_manifest, attempt_id, operation_key, collision_digest)
  -> EnvironmentHandle + ProvisionReceipt
attest(handle) -> EnvironmentAttestation
materialize(handle, input_manifest, operation_key, collision_digest)
  -> MaterializationReceipt
freeze_outputs(handle, declared_output_policy, operation_key, collision_digest)
  -> ArtifactManifest + OutputFreezeReceipt
reset(handle, reset_policy, operation_key, collision_digest) -> ResetReceipt
destroy(handle, retention_policy, operation_key, collision_digest)
  -> DestructionReceipt
reconcile(execution_locator) -> EnvironmentReconciliation
```

The operation key is stable over process restart and unique to attempt, adapter, operation kind, and declared ordinal or purpose. The collision digest covers every semantic request input, including policy. Every mutating call returns an operation receipt in addition to any domain result. An adapter persists the key, digest, effect class, outcome knowledge, exact domain-result identity, and receipt before acknowledging success. Exact replay returns the same result and receipt. A key/digest collision fails closed. A lost response follows the declared provider-idempotent or reconciliation path; a non-reconcilable ambiguity becomes terminal and is never retried automatically.

`ExecutionEnvironment` pins provider and version, platform, root filesystem or image digest, isolation class, immutable input mounts, attempt workspace, output policy, default-deny or explicit network policy, process and tool policy, CPU, memory, process, file, disk and wall-time limits, credential references, reset, cleanup, and retention. `EnvironmentAttestation` reports effective values before any model or tool starts; a mismatch fails closed.

Initial environment classes are `trusted_local` and `ephemeral_isolated`. The isolated class has no ambient credentials, accepts only bundle-authorized operations, starts from a pinned root, and exports only frozen declared artifacts. The provider remains replaceable behind conformance tests.

Implement `reference-local` for allowlisted deterministic commands and `hermes-cli` for agent work. The Hermes adapter launches a pinned supported process interface inside the attested environment; supplies bundle, prompt, and context through immutable files or an equivalently attested channel; requests typed output; captures model, process, tool, and cost receipts; and normalizes exit conditions. Ambient Hermes memory, user settings, project skills, and global tool discovery are off unless every included source is enumerated and digested in the bundle.

Until SPEC-024, fake credential references cover conformance and live credentials require one supervised invocation. Continuous credentialed execution remains disabled until SPEC-024 supplies authenticated brokering and SPEC-025 supplies supervised deployment and recovery.

Hermes operator input enters the SPEC-006 authenticated path as `ChannelDelivery -> IngressReceipt -> CommandIntent`; Hermes cannot construct a trusted command intent directly. Scheduled Hermes tasks call a SPEC-008-observable dispatcher tick with stable identity and no direct mutation path.

## Output freezing

Output collection resolves every declared path beneath the attempt workspace using the SPEC-003 artifact freezer. It rejects path traversal, symlink and hardlink escapes, device nodes, sockets, unexpected file types, path and inode races, excess files, excess bytes, and sparse-file accounting violations. The collection receipt binds the pre-freeze workspace attestation, path-policy version, complete output manifest, and omitted or rejected paths. A model-reported path is never trusted without this resolution.

## State and failure behavior

`ExecutionTransitionRegistry` is a registered immutable machine-readable artifact. Every entry binds machine kind and version, source state, event family, target state, required receipt and guard schemas, permitted effect class, terminal flag, cleanup obligation, and projector version. Reducers reject an event absent from the pinned registry or missing its guard receipt. A registry change creates a new compatibility version; it never changes historical replay.

The initial environment machine contains at least:

```text
requested -> provisioned -> attested -> materialized -> active
active -> freezing -> frozen
frozen -> retained
frozen -> destroying -> destroyed
requested|provisioned|attested|materialized|active|freezing
  -> failed | unknown
unknown -> reconciling -> provisioned | active | frozen | failed | unknown_terminal
failed|unknown_terminal -> retained
failed|unknown_terminal -> destroying -> destroyed
```

The initial execution machine contains at least:

```text
prepared -> starting -> running -> completion_reported -> collecting -> completed
running -> checkpoint_proposed -> running
prepared|starting|running|completion_reported|collecting
  -> cancellation_requested -> cancelling
cancelling -> cancelled | unknown
starting|running|completion_reported|collecting -> lost | unknown
lost|unknown -> reconciling
reconciling -> completion_reported | cancelled | failed | unknown_terminal
prepared|starting|running|completion_reported|collecting -> failed
```

`checkpoint_proposed` is an event-backed transient projection; the returned object is the SPEC-005 checkpoint envelope with a registered SPEC-012 payload, not a second runtime-owned checkpoint type. `completed`, `cancelled`, `failed`, and `unknown_terminal` are terminal for that attempt. Every terminal execution state has a deterministic environment retention or destruction obligation, and no terminal state may retain a live unfenced process.

Lost process, environment, or transport state enters `unknown`; the dispatcher performs bounded reconciliation before any retry. A retry after an ambiguous side effect requires adapter-specific reconciliation. Non-reconcilable ambiguity enters `unknown_terminal` and remains blocked until a SPEC-006 authenticated human command produces the shared SPEC-005 `AmbiguousEffectDisposition`. The runtime owns no human-disposition action. `confirmed_absent` may make a new fenced attempt eligible; `confirmed_applied` must pass the owning result reducer; `abandoned_unknown` remains permanently terminal. No transition reopens or retries the same attempt.

After a process or supervisor loss, the old attempt is fenced, reconciled, and closed. A new attempt receives a new fencing token, newly authorized context and bundle, and reducer-validated checkpoint. Harness session reuse may be an implementation optimization only if its content is reset and attested; it never preserves organizational identity or authority.

A malformed result receives only the bounded repair policy from SPEC-013, with separate call and cost receipts and no grant expansion. Unsupported capabilities, unpinned ambient configuration, environment mismatch, or invalid output policy fail before execution or collection.

## Implementation sequence

1. Freeze bundle, environment, locator, executor, operation-identity, transition-registry, and receipt schemas; build reference and fake-provider conformance tests.
2. Implement one isolated provider with attestation, bounded materialization, output freezing, reset, destruction, and crash reconciliation.
3. Pin and inventory an eligible Hermes release, process surface, defaults, configuration inputs, and license.
4. Implement Hermes capability discovery, ambient-state suppression, execution, polling, SPEC-005 checkpoint-envelope proposal, cancellation, collection, transition reduction, and reconciliation.
5. Run deterministic and research fixtures through reference and Hermes adapters in observe and shadow modes.
6. Add proposal effects, operator commands, and scheduled wakes only after reducer and private-control dependencies are active.

## Migration and rollback

Hermes starts in shadow for selected work-order kinds. The current loop remains executable. Rollback disables new Hermes routing, fences and reconciles active handles, and creates new attempts on the prior executor from validated checkpoints. It never reassigns a live attempt handle across adapters.

## Observability

Record queue-to-start, provisioning, attestation, materialization, freeze, reset, and cleanup latency; effective resources; policy mismatches; model and tool calls; network and operation denials; tokens and cost including repair; checkpoint rate; cancellation latency; unknown outcomes; reconciliation result; workspace retention; ambient-state suppressions; and result differences by adapter and environment.

## Verification

- One work-order fixture produces schema-equivalent results on reference and Hermes adapters.
- A bundle compiled for an expired, superseded, mismatched, or unactivated attempt reservation is rejected before any provider effect.
- Kill and recovery create a new attempt from reducer state, not from chat or Hermes memory.
- Hermes, a tool, or an internal subagent cannot apply state, widen a grant, or satisfy independence.
- Shadow outputs can reach only isolated shadow reducers and indexes, never authoritative reducers, active indexes, outbox, GitHub, or accepted decisions.
- Cancellation, ambiguous effects, and unknown outcomes reconcile according to adapter class.
- Exact lost-ack replay of prepare, start, checkpoint, cancel, collect, cleanup, provision, materialize, freeze, reset, and destroy returns one original receipt; key/digest collisions perform no effect.
- Every registered execution and environment transition has positive, illegal-edge, missing-guard, crash, and cleanup-obligation coverage.
- Removing Hermes leaves discovery, validation, status, and manual operation functional.
- Environment roots, mounts, network, processes, limits, and credential absence match the manifest.
- Path traversal, hardlink, symlink, device, socket, excess-count, sparse-file, and race fixtures cannot escape output policy.
- Candidate, community, and hidden-evaluation fixtures cannot use `trusted_local`.
- Undeclared ambient Hermes settings, memory, skills, or tools cause conformance failure.

## Acceptance criteria

- [ ] Executor and environment protocols have public offline conformance suites.
- [ ] Every call consumes one immutable provenance-complete `ExecutionAttemptBundle`.
- [ ] SPEC-005 activation binds the exact reservation and bundle before any runtime mutation.
- [ ] Hermes version, configuration sources, model, tools, and receipts are pinned.
- [ ] Canonical state survives session and workspace deletion.
- [ ] Mode ceilings and operation grants are mechanically independent.
- [ ] Hermes cron is only a wake mechanism and a non-Hermes executor remains usable.
- [ ] Output freezing and environment lifecycle pass adversarial filesystem and crash tests.
- [ ] All mutating runtime operations have stable operation keys, collision digests, persistent receipts, and declared ambiguity behavior.
- [ ] A machine-readable transition registry rejects illegal edges and requires terminal cleanup or retention receipts.
- [ ] Candidate, community, and hidden-evaluation jobs require eligible isolation.
- [ ] Continuous credentialed operation remains gated on SPEC-024 and SPEC-025.

## Pull-request evidence

Attach version and license inventory, bundle golden, environment and adapter conformance reports, effective-environment attestation, ambient-state suppression test, mode-isolation tests, adversarial output-freezing suite, cleanup receipts, live supervised Hermes smoke trace, process-loss recovery, cancellation and unknown-outcome tests, and Hermes-removal fallback demonstration.
