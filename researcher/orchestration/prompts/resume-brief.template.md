# Resume from an Accepted SPEC-005 Checkpoint

Template version: bootstrap-v2

This Markdown and YAML are provisional bootstrap projections, not registered durable objects. They grant no authority and cannot make a checkpoint resumable. A production resume must consume one reducer-accepted SPEC-005 `CheckpointEnvelope` carrying a registered SPEC-012 `ContextCheckpointPayload`, then create and activate a new SPEC-005 attempt.

## Objective

Continue one bounded specification-program work order without relying on conversation history. Revalidate the accepted checkpoint against current authoritative repository, journal, budget, attempt, and provider state. Never reopen or reuse the source attempt.

## Durable checkpoint objects

The payload, envelope, payload-validation receipt, and checkpoint-acceptance receipt are distinct immutable objects. No digest appears inside the bytes it hashes.

### SPEC-005 CheckpointEnvelope

```yaml
checkpoint_envelope_id: "{{registered stable identity}}"
checkpoint_envelope_digest: "{{canonical envelope digest}}"
work_order_id: "{{required}}"
work_order_digest: "{{required}}"
work_order_version: "{{required integer}}"
source_attempt_id: "{{required}}"
source_attempt_descriptor_digest: "{{required}}"
source_lease_generation: "{{required integer}}"
source_fencing_token: "{{required}}"
checkpoint_kind: "{{periodic|pre_effect|terminal}}"
payload_kind: "ContextCheckpointPayload"
payload_schema_version: "{{accepted SPEC-012 version}}"
payload_digest: "{{canonical digest of exact payload bytes}}"
resumable_artifact_refs: ["{{registered ArtifactRef identities and digests}}"]
effect_intent_refs: ["{{EffectIntent identities and digests or []}}"]
policy_context_digest: "{{required}}"
proposal_operation_key: "{{stable checkpoint-proposal operation key}}"
proposal_collision_digest: "{{canonical collision digest over all proposal semantics}}"
```

`periodic` captures bounded progress. `pre_effect` must name the exact `EffectIntent` and be accepted before the adapter operation begins. `terminal` records the source attempt's proposed final checkpoint; only the owning reducer's accepted terminal transition closes the attempt. A checkpoint proposed by an expired, superseded, cancelled, or wrong-fence executor is historical evidence only and cannot become resumable.

### SPEC-012 ContextCheckpointPayload

```yaml
checkpoint_id: "{{required payload identity}}"
created_at: "{{required recorded clock observation reference, not ambient wall time}}"
activation_outcome: "{{in_progress|candidate_ready_local|pr_open_waiting_human|human_gate|contract_blocked|external_dependency_blocked|budget_exhausted_incomplete|cancelled}}"

objective: "{{required}}"
success_predicate: "{{required}}"
work_layer: "{{research|design|implementation|verification|external_coordination}}"

authority:
  source_stage: "{{bootstrap|journal|github_reconciled|other registered stage}}"
  source_owner: "{{accepted owning contract}}"
  source_receipt: "{{immutable identity and digest}}"
  protected_default_commit: "{{required full SHA}}"
  protected_default_tree: "{{required tree digest}}"
  constitution_digest: "{{required}}"
  policy_decision: "{{required identity and digest}}"
  accepted_public_commit: "{{full SHA and reconciler receipt}}"
  promoted_quality_root: "{{full SHA, tree, and promotion anchor or bootstrap anchor}}"
  promotion_lineage_mode: "{{contiguous|cumulative_reconciliation|not_applicable}}"
  promotion_lineage_proof: "{{complete proof reference or null}}"
  organization_epoch: "{{required identity, version, and source receipt}}"
  spec_id: "{{required SPEC-NNN}}"
  spec_revision: "{{required integer}}"
  revises: "{{predecessor digest or none}}"
  spec_digest: "{{required exact digest}}"
  spec_status: "{{required lifecycle status}}"
  dependency_revisions: "{{required exact SPEC-NNN@revision bindings or none}}"
  dependency_stage_floor_proof: "{{required}}"
  lifecycle_receipt: "{{required identity and digest}}"

repository:
  branch: "{{required}}"
  base_sha: "{{required}}"
  head_sha: "{{required or null}}"
  pull_request: "{{required number and head or null}}"
  tree_digest: "{{required or null}}"
  changed_paths: "{{required with ownership and classification}}"
  staged_paths: "{{required list}}"
  untracked_paths: "{{required list}}"
  impact_manifest_digest: "{{required or not_applicable}}"

source_attempt:
  reservation_projection_id: "{{required model-safe reference}}"
  activation_receipt_projection_id: "{{required model-safe reference}}"
  attempt_id: "{{required}}"
  principal_projection_id: "{{required authenticated model-safe principal reference}}"
  lease_generation: "{{required integer}}"
  fencing_token: "{{required}}"
  state: "{{required source-attempt state}}"
  fence_receipt_at_cutoff: "{{receipt if already fenced at the payload cutoff, otherwise null}}"

context:
  source_role: "{{builder|verifier|other accepted role}}"
  prompt_payload_digest: "{{required digest of this source attempt's exact model-visible prompt payload}}"
  prompt_components:
    - component_id: "{{each source-attempt component exactly once}}"
      component_role: "{{root|work_brief|role_contract|verifier|resume|other registered role}}"
      digest: "{{exact model-visible component digest}}"
  launch_projection_id: "{{required new-identity model-safe AttemptLaunchProjection ID}}"
  launch_projection_digest: "{{required digest over only allowlisted projection bytes}}"
  launch_issue_receipt_projection_id: "{{required authenticated model-safe receipt}}"
  private_manifest_binding: "verified_not_disclosed"
  context_package_digest: "{{required}}"
  context_compilation_receipt_projection_id: "{{required model-safe reference}}"
  role_package_projection_id: "{{required model-safe reference or not_applicable}}"
  execution_activation_projection_id: "{{required model-safe reference or not_applicable}}"
  criteria_digest: "{{required}}"
  evaluator_epoch: "{{allowed visible identity or not_applicable}}"
  thresholds_digest: "{{allowed visible digest or not_applicable}}"
  disclosed_evaluation_decision: "{{opaque allowed decision or not_applicable}}"
  ordered_artifacts: "{{required}}"
  contradictions: "{{typed list with authority order, disposition, evidence, and blocking status, or []}}"

event_position:
  journal_generation: "{{required immutable generation identity}}"
  cutoff_sequence: "{{required nonnegative integer}}"
  cutoff_event_id: "{{required identity or bootstrap marker}}"
  cutoff_chain_digest: "{{required digest or bootstrap marker}}"
  projection_versions: "{{required owner and sequence mappings}}"

external_effects:
  - effect_intent_id: "{{stable EffectIntent identity}}"
    effect_intent_digest: "{{exact immutable intent digest}}"
    effect_revision: "{{required integer}}"
    action: "{{push|open_pr|update_pr|comment|notify|other registered operation}}"
    target: "{{exact resource or private destination reference}}"
    adapter_id: "{{exact adapter and version}}"
    effect_class: "{{provider_idempotent|reconcilable|non_reconcilable}}"
    operation_key: "{{stable across restart}}"
    collision_digest_profile: "{{registered canonical profile}}"
    collision_digest: "{{digest of every semantic request input including policy}}"
    provider_idempotency_key: "{{required when supported, otherwise not_applicable}}"
    provider_request_id: "{{safe provider reference or null}}"
    start_event: "{{external_operation_started event identity or null}}"
    outcome_knowledge: "{{not_started|unknown_after_attempt|committed|confirmed_absent|failed_terminal|abandoned_unknown}}"
    operation_receipt: "{{immutable adapter receipt or null}}"
    reconciliation_receipts: ["{{ordered provider and reducer evidence or []}}"]
    human_disposition: "{{SPEC-005 AmbiguousEffectDisposition or null}}"
    executor_fenced: "{{true|false}}"

decisions: "{{required durable decision ledger}}"
approach_registry: "{{required ideas, evidence, and status}}"
blocked_routes: "{{required route, failure mechanism, and reopening condition}}"
feedback_applied: "{{required scoped feedback atoms or []}}"

verification:
  completed: "{{commands, criteria, candidate identity, environment, exit, and artifacts}}"
  failed: "{{same shape or []}}"
  invalidated: "{{same shape or []}}"
  independent_audit: "{{distinct verifier attempt, independence receipt, and verdict or null}}"

budget:
  ceiling:
    attempts: "{{required integer}}"
    logical_time: "{{required integer and unit}}"
    tokens: "{{required integer}}"
    money_micros_by_currency: "{{required ISO currency mapping}}"
    external_calls: "{{required integer}}"
  cumulative_charged: "{{all immutable usage receipts across every attempt}}"
  cumulative_reserved: "{{live reservations including reconciliation capacity}}"
  unresolved_effect_reserve: "{{capacity not releasable until provider reconciliation}}"
  remaining: "{{ceiling minus charged and live reserved, by dimension}}"
  source_attempt_usage: "{{required receipt references}}"
  next_attempt_maximum: "{{largest legal new reservation, by dimension}}"

unresolved_findings: "{{required list or []}}"
exact_next_action: "{{required single action or terminal_no_action}}"
wake_condition: "{{required accepted event or command}}"
stop_conditions: "{{required}}"
```

### Checkpoint acceptance record

```yaml
checkpoint_acceptance:
  acceptance_event_id: "{{SPEC-005 checkpoint.accepted event}}"
  acceptance_receipt_id: "{{immutable append/reducer receipt}}"
  acceptance_receipt_digest: "{{required}}"
  envelope_id: "{{exact CheckpointEnvelope identity}}"
  envelope_digest: "{{exact digest}}"
  payload_validation_receipt: "{{SPEC-012 validator identity and digest}}"
  expected_work_order_version: "{{required integer}}"
  expected_source_attempt_version: "{{required integer}}"
  authenticated_principal: "{{trusted source principal bound by the event}}"
  policy_decision: "{{exact allow decision and digest}}"
  runtime_grant: "{{exact checkpoint operation and audience binding}}"
  journal_generation: "{{accepted generation identity}}"
  journal_sequence: "{{acceptance sequence}}"
  journal_chain_digest: "{{chain digest through acceptance}}"
  reducer_version: "{{required}}"
  result: "accepted"
```

The acceptance receipt must authenticate and source-bind the envelope, payload validator, source attempt, current fence, work-order and attempt versions, policy decision, runtime grant, and exact journal generation and sequence. Executor output or a local file named checkpoint is not acceptance.

## Resume protocol

1. Resolve the currently active authority stage from the protected default branch and its owner receipt. Use the SPEC-004 bootstrap source only until the later accepted owner contract has cut over; after cutover, require the current reconciled owner receipt. Never infer authority from ambient `HEAD`, a branch, or a pull request.
2. Resolve the registered envelope and acceptance record. Verify the acceptance receipt, journal generation, sequence, chain digest, envelope identity, and envelope digest before parsing the payload. Then verify the registered payload kind, schema, exact payload digest, and SPEC-012 validation receipt.
3. Verify the exact specification revision, `Revises` binding, lifecycle receipt, frozen dependency revisions, and stage floors. Research and design may proceed under their allowed lifecycle state. Implementation requires the exact accepted revision and authorized vertical slice; a draft or architecture-reviewed revision remains non-authoritative for implementation.
4. Reconcile current accepted-public and promoted-quality roots. Preserve the gap if they differ. An ordinary continuation cannot treat accepted but unattested bytes as promoted; any release path over that gap requires complete cumulative reconciliation.
5. Compare work-order version, journal generation and tail, organization epoch, policy, dependencies, repository tree, branch, PR head, checks, reviews, evidence, budgets, and provider state with the accepted cutoff. Classify each difference as expected wake progress, harmless drift, invalidated assumption, authority change, conflicting external write, possible lost journal suffix, or corruption.
6. Prove the source attempt is terminal, expired, or otherwise fenced before replacement. A still-live source lease blocks a new activation. A stale fence can never submit a checkpoint, result, heartbeat, or external receipt.
7. Reconcile every effect whose `start_event` exists or whose outcome is not conclusively `not_started`, `committed`, `confirmed_absent`, `failed_terminal`, or validly `abandoned_unknown`. Match the exact `EffectIntent`, operation key, collision digest, adapter version, provider idempotency key or request ID, persisted receipt, and provider state. Never infer absence from a missing local response, reuse a key with changed bytes, or issue a retry while outcome knowledge is unknown.
8. Accept `cancelled` or `budget_exhausted_incomplete` as terminal only after all executors are fenced and every possible external effect is conclusively reconciled or has a valid SPEC-005 human disposition. Budget accounting remains cumulative across attempts; resume cannot reset attempt, token, time, money, call, retry, repair, or reconciliation consumption. Capacity tied to an unresolved effect is not released.
9. Invalidate evidence whose candidate, environment, criterion, evaluator decision, threshold, authority, dependency, or repository identity changed. Hidden evaluator material must not enter this general resume context; carry only the opaque allowed disclosed decision.
10. If the work order remains resumable, ask SPEC-005 to create a new `AttemptReservation` that binds the accepted checkpoint receipt, current work-order version, a new attempt ID, higher lease generation, new fencing token, current policy context, remaining cumulative budget, and all typed extension requirements. A reservation grants no execution or external-effect authority.
11. Compile a fresh SPEC-012 context package and required SPEC-013 and SPEC-014 extensions against that reservation. SPEC-005 may then atomically activate one new immutable `AttemptDescriptor` that binds the accepted checkpoint receipt, current authenticated principal and new lease, new fence, narrowed current capabilities, current authority, and exact extension digests. Do not reuse stale approvals, grants, evaluator epochs, thresholds, prompt components, editable surfaces, context packages, or budgets.
12. Continue the exact next action only after the new activation receipt is durable and only if the action remains authorized and useful. The source attempt stays closed and fenced forever. A retry, repair, verifier, or resumed builder is always a distinct attempt and cost-bearing record.
13. If integrity, authority, dependency, budget, effect reconciliation, or replacement eligibility fails, emit a new proposed checkpoint or typed blocker through the owning reducer. Do not hand-edit durable state or present this template as an accepted checkpoint.

An abstractive summary may orient the new attempt, but it cannot replace a referenced authority, event, effect, budget, or evidence artifact. A `terminal` checkpoint does not itself authorize another attempt: scheduler readiness, policy, dependency, fence, budget, and checkpoint-resume rules must all independently pass. Cancellation and permanent budget exhaustion close the work order; later work requires a new causally linked work order rather than reopening it.
