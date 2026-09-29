# SPEC-014: Execution Environment, Executor Protocol, and Provider Adapters

Status: draft
Revision: 1
Revises: none
Wave: 2
Classification: split
Owners: runtime integration agent; operations steward agent
Depends on: SPEC-003, SPEC-005, SPEC-006, SPEC-008, SPEC-012, SPEC-013

## Decision

Every model or tool execution will consume one immutable `ExecutionAttemptBundle` compiled against a SPEC-005 `AttemptReservation` and run under a versioned `ExecutionEnvironment` contract. SPEC-005 activates the lease only after it verifies and binds that bundle. The reference deployment is a standalone open-source Python application using the Codex SDK and its local app-server runtime for model-driven research, critique, editing and independent evaluation roles. It receives frozen work, role, context, operation grants, environment, mode, and output contracts. The Codex desktop app is an optional development client, not the service scheduler; the pinned SDK runtime is an application dependency. Hermes and other agent harnesses are optional adapters; their sessions, ambient configuration, memory, cron state, and internal delegation are never canonical organizational state.

The repository-owned service retains deterministic admission, retrieval, evidence storage, candidate freezing, scoring, accounting and publication authority outside SDK threads. The initial implementation pins `openai-codex==0.159.0` and its matching CLI dependency. Each role starts with fresh task context; an independent evaluator does not reuse proposer or critic session state. Actual provider requests pass through the service-owned gateway and the existing cumulative budget authority before dispatch. A logical SDK turn is not one provider request. The initial slice permits one tool-free request per turn and refuses further requests; future tool use, retries or multi-request turns require separately verified grants and per-request accounting. Direct native completions and managed Agents sessions are not fallback paths for new production role execution.

The [Codex SDK runtime migration](../product/codex-sdk-runtime-migration.md) defines the current target and its staged evidence gates. The [managed research architecture](../product/openai-agents-research-architecture.md) and historical native/managed receipts remain migration evidence, not activation of the retired direction. Known historical managed sessions retain bounded observation and cancellation compatibility; an unknown prior outcome cannot authorize a new create, SDK retry or provider substitution. SDK process exit is likewise not proof that a dispatched provider request stopped.

## Context and current repository touchpoints

The legacy loop is repo-native Python migration code whose launchd activation and network retrieval are disabled. Existing source capture, context packing, candidate freezing, prompt compilation and deterministic evaluation are reusable components. The developmental SDK worker, gateway and campaign exercise the data-only `researcher -> critic -> skill_editor` path and fresh evaluation tasks in private state. Their receipts and local tests do not by themselves implement this complete draft contract, prove research effectiveness or activate accepted work. Tool-free startup and native-tool isolation are separate gates; local macOS evidence does not establish clean-Linux native-tool containment. Role schemas and SPEC-013 must agree before those roles acquire normative execution authority.

## Goals

- Execute equivalent work-order contracts through credential-free SDK fixtures, the pinned SDK runtime and separately reviewed optional adapters.
- Preserve exact bundles, calls, outputs, costs, tool effects, checkpoints, cancellation, and reconciliation receipts.
- Keep the queue, journal, reducers, and accepted decisions outside the harness.
- Make runtime, model, tool, and environment differences measurable.
- Make mounts, network, resources, process boundaries, credentials, reset, cleanup, and output extraction attestable.

## Non-goals

- Forking a model SDK or agent harness, or embedding organizational policy inside it.
- Making Codex tasks, harness cron, session storage, or model memory the durable scheduler or source of truth.
- Letting an executor apply reducer state, accept a decision, merge a PR, or broaden its own grant.
- Treating internal subagents or differently named model roles as independent organizational reviewers.

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
10. Ambient runtime memory, configuration, skills, plugins, MCP servers, and user or project settings are disabled by default or pinned explicitly in the bundle.
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

Implement `reference-local` for allowlisted deterministic commands and a pinned SDK executor for data-only agent work. The initial researcher emits an evidence-linked mechanism dossier, the critic emits narrow support/counterevidence findings, and the skill editor emits a bounded candidate patch without applying it. A critic is not automatically an independent score-bearing evaluator; evaluation uses fresh SDK threads, frozen candidate inputs and a gold-free task projection, with deterministic grading outside the worker. Candidate-authored code, shell commands, plugins and tests are never executed by this initial path; their execution requires the separately attested isolated environment and SPEC-017 evaluation boundary. Reviewed repository validators may inspect candidate data without loading candidate executables.

The SDK worker owns the local thread/turn lifecycle, with a private clean home, explicit configuration and no provider credential. The parent gateway holds the credential and validates the exact allowed model, projected task input, tool exposure, generation parameters and resource ceilings before reserving each actual request in the existing accounting store. It commits the validated provider receipt before delivering completion to the worker, then binds the SDK result to that receipt and the recorded thread/turn. Durable start without a matching result, including provider completion followed by lost SDK output, is quarantined rather than replayed. Neither a new worker nor a new gateway may reset accumulated spend or unknown liability. `ModelProvider.generate` remains a historical transport/control contract; wrapping an SDK turn behind one such call does not establish per-request accounting. Provider-reported usage and cost estimates are evidence, not an independently verified account-wide bill.

Historical `ManagedSessionAdapter` compatibility implements observation/reconciliation of retained locators, not new production submission or `ModelProvider.generate`. Its private locator binds the exact request and local create intent to a remote session and its root/subagent turns. A known ID is persisted before interpreting a successful result; an unknown create outcome cannot create again. Saved-turn/item pagination recovers results without inventing replayable event-stream cursors. Cancellation acknowledgement is distinct from observed terminal work, and remains available after local clock rollback. Nullable, mutable session usage is never counted as zero or as final billing. Any executor lacking a required bundle cost, token or deadline ceiling reports that capability unavailable; production activation remains denied until an accepted containment design resolves it.

`ToolGateway.invoke(tool_ref, arguments, attempt_grant, operation_identity)` is a separate boundary. Initial MCP integration permits only operator-registered read operations with pinned server/tool/schema identity, approved HTTPS destination or pinned local executable, bounded arguments/output/time and a private credential binding. Server-provided tool annotations are untrusted descriptions, not proof of read-only behavior. Tool discovery cannot auto-install a server, widen scope, enable sampling, or add a writable tool. Source/tool responses are inert evidence with provenance, never instructions or capabilities. GitHub proposal writes and notification delivery use their owner outboxes, not model-visible general-purpose MCP tools.

An optional `hermes-cli` or other harness adapter must suppress ambient state and pass the same bundle, effect, isolation and receipt tests. Removing it must leave the SDK reference path and deterministic service authority operational. Public records do not contain private endpoint or credential locators.

Fake credential references and an injected gateway transport cover credential-free SDK contract tests. Separately authorized developmental SDK calls and registered read-only MCP retrieval may run under bounded non-production profiles with explicit credential references, destination policy, cumulative budgets and retained receipts. The existing OpenAI authority, including prior spend and unresolved reservations, must be reused without reset; its limit is not a cap on unrelated provider accounts. This evidence does not attest full SPEC-014 conformance. Production credentialed execution remains gated on SPEC-024 authenticated brokering and SPEC-025 accepted deployment and recovery. Historical zero-call benchmark commands retain their existing behavior until their separate activation change.

CLI, UI and optional harness operator input enter the SPEC-006 authenticated path as `ChannelDelivery -> IngressReceipt -> CommandIntent`; clients cannot construct a trusted command intent directly. The service-owned timer emits a SPEC-005 admission request with stable schedule/slot identity. An external timer may wake admission but cannot dispatch model/tool effects directly.

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
2. Implement the standalone Python coordinator, isolated SDK worker and tool-free model gateway with an injected provider transport; prove complete inputs, bounded outputs and durable failure/unknown-outcome accounting without paid calls or ambient credentials.
3. Route researcher, critic, editor and independent evaluation tasks through the same SDK/accounting boundary. Keep retrieval and registered read-only MCP operations service-owned, and pin their explicit configuration, grants and cumulative budgets. Refuse native/managed role fallback and prove credential-free completed-result replay.
4. Run a bounded, separately authorized SDK/provider canary on public development inputs. Record actual thread/turn and provider identities, model, usage, failures and source/frozen-candidate/evaluation bindings; fixture outputs do not satisfy this evidence requirement. Native tools require a separate clean-Linux isolation and egress gate before activation.
5. Add proposal effects, authenticated commands and scheduled service admission only after reducer, private-control and deployment dependencies are active. GitHub and notification owners retain effect authority.
6. Add an isolated candidate-code evaluator or optional agent-harness adapter only through its reviewed conformance, attestation, reset, destruction and crash-reconciliation evidence. Neither is required for the initial data-only role path.

## Migration and rollback

New adapters start in shadow for selected work-order kinds. The legacy launchd loop remains inert. Rollback disables new routing to the adapter, fences and reconciles active handles, and creates new attempts on a prior compatible executor from validated checkpoints. It never reassigns a live attempt handle across adapters or substitutes a provider after an uncertain charge. Historical private development records remain non-authoritative imported evidence.

## Observability

Record queue-to-start, provisioning, attestation, materialization, freeze, reset, and cleanup latency; effective resources; policy mismatches; model and tool calls; network and operation denials; tokens and cost including repair; checkpoint rate; cancellation latency; unknown outcomes; reconciliation result; workspace retention; ambient-state suppressions; and result differences by adapter and environment.

## Verification

- One frozen work-order fixture produces schema-conformant receipts through the actual SDK against injected transport and through a separately authorized provider canary; label these evidence classes distinctly and do not require identical model text.
- A bundle compiled for an expired, superseded, mismatched, or unactivated attempt reservation is rejected before any provider effect.
- Kill and recovery create a new attempt from reducer state, not from chat or harness memory.
- A provider, tool, or internal subagent cannot apply state, widen a grant, or satisfy independence.
- Shadow outputs can reach only isolated shadow reducers and indexes, never authoritative reducers, active indexes, outbox, GitHub, or accepted decisions.
- Cancellation, ambiguous effects, and unknown outcomes reconcile according to adapter class.
- Exact lost-ack replay of prepare, start, checkpoint, cancel, collect, cleanup, provision, materialize, freeze, reset, and destroy returns one original receipt; key/digest collisions perform no effect.
- Every registered execution and environment transition has positive, illegal-edge, missing-guard, crash, and cleanup-obligation coverage.
- Removing the Codex desktop app and optional harnesses leaves service scheduling, discovery, SDK execution, validation and status functional; removing the pinned SDK denies new model roles without disabling deterministic status or introducing fallback.
- Environment roots, mounts, network, processes, limits, and credential absence match the manifest.
- Path traversal, hardlink, symlink, device, socket, excess-count, sparse-file, and race fixtures cannot escape output policy.
- Candidate, community, and hidden-evaluation fixtures cannot use `trusted_local`.
- Undeclared ambient settings, memory, skills, tools, MCP schema changes and unregistered endpoints cause conformance failure.
- Researcher/critic/editor outputs cannot execute code or write repository, evaluator, credential or outbox state; malformed citations and candidate paths fail validation.
- Provider timeout after possible execution retains unknown outcome and reserved cost; restart, key rotation and budget exhaustion cannot silently retry or switch providers. Durable SDK start without an effect and completed provider receipt without SDK completion both remain visible unresolved turns; recovery preserves them without creating a new worker request.
- Every actual SDK-origin provider request is admitted before dispatch; duplicate/retry requests, request-shape drift and unsupported tools are denied. SDK result replay verifies the committed provider output and thread/turn identity; failed evaluation attempts remain in the denominator across repeated evaluation and origin verification.
- A supposedly read-only MCP tool attempting writes, redirect escape, credential reflection, sampling or tool-set expansion is denied by the effective gateway boundary.

## Acceptance criteria

- [ ] Executor and environment protocols have public offline conformance suites.
- [ ] Every call consumes one immutable provenance-complete `ExecutionAttemptBundle`.
- [ ] SPEC-005 activation binds the exact reservation and bundle before any runtime mutation.
- [ ] SDK and CLI versions, model IDs, effective configuration, tool schemas and receipts are pinned; optional harnesses use the same contracts and cannot activate silent native/managed fallback.
- [ ] Canonical state survives session and workspace deletion.
- [ ] Mode ceilings and operation grants are mechanically independent.
- [ ] Standalone service admission works without Codex desktop or harness cron and external wakes cannot bypass reservation or fencing; the pinned SDK is the model-role runtime dependency.
- [ ] Output freezing and environment lifecycle pass adversarial filesystem and crash tests.
- [ ] All mutating runtime operations have stable operation keys, collision digests, persistent receipts, and declared ambiguity behavior.
- [ ] A machine-readable transition registry rejects illegal edges and requires terminal cleanup or retention receipts.
- [ ] Candidate, community, and hidden-evaluation jobs require eligible isolation.
- [ ] Continuous credentialed operation remains gated on SPEC-024 and SPEC-025.
- [ ] Data-only researcher, critic and skill editor roles have bounded output contracts and no candidate-code execution or direct effect authority.
- [ ] Registered read-only MCP conformance rejects tool/schema drift, ungranted operations, unsafe output and ambient server discovery.
- [ ] SDK jobs bind durable start, effective task/configuration, thread/turn and committed gateway/result receipts; crash cuts, disconnects and cancellation ambiguity cannot duplicate work or fabricate stopped state, including during recovery of historical managed sessions.
- [ ] Each actual SDK-origin provider request uses the existing cumulative budget authority before dispatch; missing usage, unknown liability and unsupported containment remain explicit, and fresh independent evaluation preserves failed outcomes without exposing hidden labels.

## Pull-request evidence

Attach version and license inventory, bundle golden, environment and adapter conformance reports, effective-environment attestation, ambient-state suppression test, mode-isolation tests, adversarial output-freezing suite, cleanup receipts, actual-SDK/injected-transport tests, separately authorized provider and read-only MCP canary receipts, process-loss recovery, cancellation and unknown-outcome tests, and a standalone no-desktop/no-Hermes demonstration with the pinned SDK installed. Distinguish tool-free startup from native-tool containment, local macOS evidence from clean-Linux evidence, and public deterministic fixtures from held-out effectiveness. Mark unimplemented isolation or optional adapters unavailable; development tests are not full draft-spec conformance or production acceptance.
