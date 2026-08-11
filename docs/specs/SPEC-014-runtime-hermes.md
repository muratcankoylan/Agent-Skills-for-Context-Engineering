# SPEC-014: Execution Environment, Executor Protocol, and Hermes Integration

Status: draft
Wave: 2
Classification: split
Owners: runtime integration agent; operations steward agent
Depends on: SPEC-005, SPEC-013

## Decision

Every execution will run under a versioned `ExecutionEnvironment` contract. Hermes Agent will be the first interactive and scheduled agent executor integrated through the runtime-neutral adapter. It will receive a frozen work attempt, context chain, capability grant, attested environment, and structured output contract. Hermes sessions, memory, cron state, and internal delegation traces are execution details, not canonical organizational state. The organization must remain operable through a reference local executor if Hermes is removed.

## Context and current repository touchpoints

The current loop is repo-native, Python-based, and launchd-scheduled. Hermes adds a capable agent harness, tool use, sessions, and scheduled entry points, but coupling state to those conveniences would prevent replay, cross-harness evaluation, and later Temporal migration.

## Goals

- Execute the same work order through Hermes and a deterministic reference adapter.
- Preserve exact inputs, outputs, receipts, tool events, checkpoints, and cancellation state.
- Use Hermes for operator interaction and bounded agent work without letting it own the queue.
- Make runtime differences measurable through conformance and evaluation.
- Make mounts, network, resources, process boundary, secrets, reset, cleanup, and artifact extraction reproducible.

## Non-goals

- Forking Hermes or embedding organization policy inside it.
- Making Hermes cron the sole durable scheduler.
- Allowing Hermes memory to write canonical semantic or preference state.

## Invariants

1. Adapter inputs and outputs use SPEC-003 schemas.
2. Executors can emit results and receipts but cannot apply organizational state.
3. Each run pins Hermes version or commit, adapter version, model, configuration digest, and tool-policy digest.
4. Environments and workspaces are unique per attempt and are never reused without attested reset and identity checks.
5. Timeout, cancellation, and unknown outcomes are distinct.
6. Internal subagents may help a Hermes execution, but their relevant outputs and traces are returned under the parent work order.
7. Cron may wake the dispatcher; it does not replace work-order durability.
8. `trusted_local` may run reviewed deterministic repository code but cannot run untrusted community or self-modifying candidate code or own hidden-evaluation isolation.
9. Only declared output paths are extracted; environment destruction or retention returns a receipt.

## Interfaces and data

Define `ExecutorAdapter`:

```text
capabilities() -> ExecutorCapabilities
prepare(work_order, context_package, capability_grant) -> ExecutionHandle
start(handle) -> StartReceipt
poll(handle) -> ExecutionStatus
checkpoint(handle) -> CheckpointRef
cancel(handle, reason) -> CancelReceipt
collect(handle) -> StructuredResult
reconcile(handle) -> ReconciliationResult
cleanup(handle, retention_policy) -> CleanupReceipt
```

Define `EnvironmentProvider`:

```text
capabilities() -> EnvironmentCapabilities
provision(environment_manifest, attempt_id) -> EnvironmentHandle
attest(handle) -> EnvironmentAttestation
materialize(handle, input_artifact_refs) -> MaterializationReceipt
collect_outputs(handle, declared_paths) -> ArtifactRefs
reset(handle, reset_policy) -> ResetReceipt
destroy(handle, retention_policy) -> DestructionReceipt
```

`ExecutionEnvironment` pins provider and version, platform, root filesystem or image digest, isolation class, read-only input mounts, read-write attempt workspace, declared output paths, default-deny or explicit network policy, tool and process policy, CPU, memory, process, disk and wall-time limits, credential references, reset and cleanup policy, and retention. `EnvironmentAttestation` reports the effective values observed before execution and fails on mismatch.

Initial environment classes are `trusted_local` for existing deterministic commands and `ephemeral_isolated` for candidate code, community contributions, and hidden evaluation. The latter has no ambient credentials, accepts only the attempt's capability grant, resets from a pinned image or root, and exports only declared artifacts. The specific container or sandbox provider remains replaceable behind conformance.

Implement `reference-local` for deterministic trusted commands and `hermes-cli` for agent work. The Hermes adapter launches a pinned CLI or supported process interface inside the attested environment, passes task and context by immutable files, receives only broker-resolved operation capabilities, requests JSON output matching the work order, captures process and tool receipts, and normalizes exit conditions. Until SPEC-024, live credentials are explicitly supervised and continuous credentialed routing remains disabled; fake references cover conformance.

Hermes operator commands create normal `Command` records. Hermes scheduled tasks call the dispatcher tick with a stable identity and do not directly run research mutations.

## State and failure behavior

Environment states are `requested -> provisioned -> attested -> materialized -> active -> collecting -> destroyed|retained`, with terminal `mismatch`, `failed`, or `unknown`. Execution states are `prepared`, `starting`, `running`, `checkpointed`, `completed`, `failed`, `cancellation_requested`, `cancelled`, and `unknown`. Lost process, environment, or transport enters `unknown` and then reconciliation. A malformed result receives at most the role contract's bounded repair. Unsupported capabilities or environment mismatch fail before start.

## Implementation sequence

1. Freeze environment and executor protocols and build trusted-local, fake-isolated, and reference-executor conformance tests.
2. Implement one ephemeral isolated provider with attestation, materialization, output extraction, reset, and destruction.
3. Pin and inventory a Hermes release, CLI surface, config, and license.
4. Implement Hermes capability discovery, isolated execution, polling, cancellation, and collection.
5. Run deterministic and research work orders through both adapters and environment classes.
6. Add operator command and scheduled wake entry points after state parity.

## Migration and rollback

Hermes starts in shadow for selected work-order kinds. The current loop remains executable. Rollback disables Hermes routing, cancels or reconciles active handles, and reschedules retryable work on the reference or prior executor.

## Observability

Record queue-to-start latency, provisioning and cleanup, environment and policy mismatches, effective resources and limits, execution duration, model and tool calls, network denials, tokens, cost, output conformance, checkpoint rate, cancellation latency, unknown outcomes, workspace retention, and result differences by adapter and environment.

## Verification

- One work order produces schema-equivalent results on reference and Hermes adapters.
- Kill and resume uses the organizational checkpoint, not chat memory.
- Hermes cannot apply a result directly or expand its capability grant.
- Cancellation and unknown outcome reconcile correctly.
- Removing Hermes leaves discovery, validation, status, and manual operation functional.
- Adapter conformance runs offline except for an explicitly marked live test.
- Environment root, mounts, network, process and resource limits, and secret absence match the manifest.
- Undeclared output paths are not extracted; reset and destruction remove attempt state according to policy.
- Candidate and community-code fixtures cannot use `trusted_local`.

## Acceptance criteria

- [ ] Adapter protocol has a public conformance suite.
- [ ] Hermes version, configuration, model, tools, and receipts are pinned in provenance.
- [ ] Canonical state survives session deletion.
- [ ] Hermes cron is only a wake mechanism.
- [ ] A non-Hermes executor remains usable.
- [ ] Live smoke tests cover start, checkpoint, completion, cancellation, and recovery.
- [ ] A versioned environment provider passes provision, attest, isolate, limit, collect, reset, destroy, and crash conformance.
- [ ] Candidate, community, and hidden-evaluation jobs require an eligible ephemeral environment.

## Pull-request evidence

Attach version and license inventory, environment and adapter conformance reports, effective-environment attestation, isolation and resource-limit tests, output-extraction and cleanup receipts, live Hermes smoke trace, session-deletion recovery, cancellation test, and Hermes-removal fallback demonstration.
