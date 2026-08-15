# Per-Wake Specification Work Brief

Template version: bootstrap-v2
Classification: model-safe private projection

This template is filled by a trusted bootstrap compiler and, after activation, by the SPEC-005, SPEC-012, and SPEC-013 work-order and context compilers. Do not ask a model to invent a field. The model receives this brief, an `AttemptLaunchProjection`, and a separate new-identity safe launch-authorization projection. The dispatcher alone receives the private `AttemptManifest` and full receipts from `attempt-manifest.template.md`.

## Launch envelope

```yaml
work_order:
  projection_id: "{{required new-identity model-safe work-order projection}}"
  version: "{{required unsigned integer}}"
  projection_digest: "{{required sha256 digest over only the model-safe projection bytes}}"
  kind: "{{required registered kind and version}}"
  private_binding: "verified_not_disclosed"
  issued_at: "{{required RFC3339 UTC}}"
  review_cycle_id: "{{required opaque ID}}"

attempt:
  current_role: "{{builder|verifier}}"
  launch_class: "{{normal|effect_reconciliation|budget_reconciliation|cancellation_reconciliation}}"
  id: "{{required registered attempt ID}}"
  ordinal: "{{required unsigned integer}}"
  lease_generation: "{{required unsigned integer}}"
  fence: "{{required opaque fencing value}}"
  reservation_projection_id: "{{required model-safe reference}}"
  activation_deadline_projection: "{{required model-safe clock-proof reference}}"
  review_cycle_phase: "{{building|verifying}}"
  source_builder_attempt_projection_id: "{{equals attempt.id for a builder; opaque prior-attempt projection for a verifier}}"
  frozen_candidate_projection_id: "{{required only for verifier; otherwise null}}"
  verifier_attempt_projection_id: "{{equals attempt.id only for verifier; null for builder}}"
  distinct_attempts_receipt: "{{required new-identity safe receipt only for verifier; null for builder}}"
  future_verifier_state: "{{not_reserved_before_candidate_freeze for builder|current_attempt for verifier}}"
  peer_verdict_visibility: "denied"

launch_projection:
  id: "{{required new-identity model-safe projection ID}}"
  digest: "{{required sha256 digest of projection bytes}}"
  private_manifest_binding: "verified_not_disclosed"
  authorization_projection_delivery: "separate_new_identity_safe_envelope_member"
  preflight_success_required: true
  preflight_failure_disposition: "launch_rejected_before_executor_start"

mode:
  requested: "{{observe|shadow|proposal|production}}"
  authorized_ceiling: "{{observe|shadow|proposal|production}}"
  ordering: "observe<shadow<proposal<production"

authority:
  default_branch: "{{required}}"
  authority_source:
    kind: "{{bootstrap_exact_git|spec_004_baseline|spec_007_reconciled}}"
    version: "{{required unsigned integer}}"
    projection_id: "{{required authenticated model-safe reference}}"
    later_source_absence_projection_id: "{{required model-safe proof only for bootstrap_exact_git or spec_004_baseline; otherwise null}}"
  constitution:
    version: "{{required}}"
    public_digest: "{{required sha256 digest}}"
  actor_projection_id: "{{required model-safe authenticated-principal projection}}"
  decision_projection_id: "{{required model-safe policy-decision projection}}"
  effective_operations:
    - operation_id: "{{stable attempt-local ID}}"
      action: "{{exact registered action}}"
      resource: "{{exact registered resource}}"
      target_scope: "{{model-safe exact path or opaque bounded resource handle}}"
      effect_class: "{{none|isolated_local|repository_local|external_proposal|production}}"
      mode_ceiling: "{{observe|shadow|proposal|production}}"
      intersection:
        constitution: "included"
        role_ceiling: "included"
        work_order_scope: "included"
        deployment_and_mode_policy: "included"
        environment_and_executor: "included"
        runtime_operation_grant: "included"
      intersection_receipt: "{{required authenticated model-safe receipt}}"
      human_command:
        requirement: "{{required|not_required}}"
        receipt_projection_id: "{{required opaque current receipt iff requirement is required; otherwise null}}"
        bound_action_and_resource: "{{required iff requirement is required; otherwise null}}"
        expires_at: "{{required iff requirement is required; otherwise null}}"
  denied_operations: "{{required exact safe list, including merge and production activation during bootstrap}}"

assignment:
  spec_id: "{{required canonical SPEC-NNN}}"
  spec_path: "{{required public path}}"
  revision: "{{required positive integer}}"
  revises: "{{required predecessor digest or none}}"
  spec_digest: "{{required sha256 digest}}"
  authoritative_status: "{{required canonical lifecycle status}}"
  lifecycle_decision: "{{required accepted decision projection when applicable; otherwise none}}"
  lifecycle_receipt: "{{required model-safe immutable receipt projection}}"
  acceptance_proof: "{{required for implementation or verification of an implementation; otherwise null}}"
  dependency_revisions: "{{required exact direct SPEC-NNN@revision bindings or none}}"
  dependency_statuses: "{{required mapping with stage-floor evidence}}"
  allowed_transition: "{{required canonical transition or none}}"
  transition_editable_fields: "{{required exact metadata fields or []}}"
  vertical_slice: "{{required exact name}}"
  work_layer: "{{research|design|implementation|verification|external_coordination}}"
  objective: "{{required outcome}}"
  artifact_predicate: "{{required falsifiable predicate}}"
  definitions: "{{required load-bearing terms, units, empty/duplicate/stale/partial cases}}"
  non_counting_outcomes: "{{required assignment-specific refusal list}}"
  adversarial_failure_modes: "{{required domain-specific list including circularity analogue}}"

surfaces:
  editable: "{{required ordered paths or patterns}}"
  append_only: "{{required ordered paths or patterns, or []}}"
  locked: "{{required ordered paths or patterns}}"
  human_controlled: "{{required ordered paths and actions}}"
  classification_ceiling: "{{required}}"

repository:
  repository_id: "{{required public or model-safe identity}}"
  observed_default_branch_head:
    commit: "{{required full object ID}}"
    tree: "{{required full object ID}}"
    observation_projection_id: "{{required reference}}"
    observed_at: "{{required RFC3339 UTC}}"
  accepted_public:
    commit: "{{required full object ID}}"
    tree: "{{required full object ID}}"
    pointer_version: "{{required unsigned integer}}"
    acceptance_projection_id: "{{required reference from authority_source}}"
    relation_to_observed_head: "{{equal|behind|diverged|unknown}}"
  promoted_quality:
    status: "{{not_established|current|lineage_gap|unknown}}"
    root_commit: "{{required full object ID when established; otherwise null}}"
    root_tree: "{{required full object ID when established; otherwise null}}"
    organization_version: "{{required when established; otherwise null}}"
    public_promotion_record: "{{required public reference when established; otherwise null}}"
    accepted_interval_gap: "{{none|unattested_acceptance|incomplete_reconciliation|unknown|not_applicable}}"
  active_deployment:
    status: "{{not_established|inactive|active|degraded|paused|unknown}}"
    public_or_opaque_projection_id: "{{required safe reference or null when not established}}"
    accepted_commit: "{{safe full object ID when disclosure is permitted; otherwise null}}"
    promotion_root: "{{safe full object ID when disclosure is permitted; otherwise null}}"
    configuration_projection_id: "{{safe opaque reference or null}}"
  workspace:
    branch: "{{required}}"
    base_sha: "{{required full SHA; normally accepted_public.commit}}"
    expected_head_sha: "{{required full SHA or null for new local work}}"
    pull_request: "{{required public number plus head SHA, or null}}"
    worktree_mode: "{{read_only|single_writer|isolated_writer}}"
    existing_changes: "{{required path inventory and ownership}}"

context:
  package_id: "{{required model-visible package or bootstrap ID}}"
  package_digest: "{{required sha256 digest}}"
  ordered_visible_artifacts: "{{required identities and digests}}"
  contradictions:
    - id: "{{stable model-safe identity}}"
      participants: "{{visible artifact or claim identities and digests}}"
      authority_order: "{{applicable precedence with evidence}}"
      disposition: "{{resolved|unresolved}}"
      evidence: "{{required visible references}}"
      blocking: "{{true for unresolved authority, scope, evaluator, or predicate conflicts}}"
  rejected_routes: "{{required list or []}}"
  freshness:
    authoritative_git_sha: "{{required accepted_public.commit}}"
    external_event_cursor_projection: "{{required model-safe reference or bootstrap marker}}"
    sources:
      - id: "{{visible source identity}}"
        observed_at: "{{required RFC3339 UTC}}"
        maximum_age_seconds: "{{required unsigned integer}}"
        expires_at: "{{required RFC3339 UTC}}"
  exclusions_summary: "{{required bounded reason categories with no denied identity, count, or digest}}"
  previous_checkpoint: "{{required accepted checkpoint reference or null}}"

verification:
  required_visible_gates: "{{required exact non-hidden commands and predicates}}"
  candidate_freeze_contract: "{{required exact-tree and editable-surface contract}}"
  independent_verifier_policy: "{{required safe policy; builder does not preallocate a verifier, and verifier launch proves a distinct attempt and context after candidate freeze}}"
  hidden_evaluation_projection:
    status: "{{not_applicable|eligible|scheduled|decision_available|closed}}"
    public_epoch_or_opaque_id: "{{required safe new-identity reference or null}}"
    eligibility_projection_id: "{{required safe new-identity reference or null}}"
    permitted_outcome_schema: "{{required allowlisted aggregate or decision schema, or null}}"
    private_binding: "dispatcher_and_independent_evaluator_only"
    prohibited_disclosures: "hidden identity, membership, count, input digest, look budget, raw result, task-level error, timing oracle, private evaluator identity"
  migration_obligation: "{{required}}"
  rollback_obligation: "{{required}}"
  observability_obligation: "{{required}}"
  operator_note_obligation: "{{required}}"

budget:
  accounting_scope: "work_order_cumulative"
  clock_domain: "{{required accepted logical clock domain}}"
  work_order_ceiling:
    attempts: "{{required unsigned integer}}"
    wall_clock_deadline: "{{required deadline plus clock-proof projection}}"
    tokens: "{{required unsigned integer}}"
    tool_calls: "{{required unsigned integer}}"
    paid_calls: "{{required unsigned integer, normally 0}}"
    external_calls: "{{required unsigned integer}}"
    cost_micros_by_currency: "{{required ISO-4217-to-unsigned-integer mapping}}"
    subagents: "{{required unsigned integer}}"
    repairs: "{{required unsigned integer}}"
    retries_by_class: "{{required mapping}}"
  consumed_before_reservation: "{{required same-dimension receipt-backed mapping}}"
  reserved_for_current_attempt: "{{required same-dimension mapping}}"
  remaining_after_reservation: "{{required same-dimension mapping}}"
  outstanding_uncertain_charges: "{{required []; nonempty must reject launch or force reconciliation}}"
  budget_controller_projection_id: "{{required authenticated model-safe reference}}"
  current_attempt_limits: "{{required bounds no wider than reserved_for_current_attempt}}"

external_state:
  observed_at: "{{required RFC3339 UTC}}"
  github_projection: "{{required safe branches, checks, reviews, commands, and delivery states}}"
  wake_event_projection: "{{required safe reference}}"
  event_cursor_projection: "{{required last durable model-safe event reference or bootstrap marker}}"
  cancellation:
    status: "{{none|requested|authenticated|ambiguous|reconciled}}"
    event_projection_id: "{{required safe reference or null}}"
    issued_effects_closed: "{{true|false}}"
  effects:
    - effect_id: "{{stable attempt-local ID}}"
      effective_operation_id: "{{must resolve to authority.effective_operations}}"
      effect_intent_projection_id: "{{required before adapter call; null only before intent creation}}"
      adapter_handle: "{{required opaque attempt-scoped handle}}"
      target_handle: "{{required opaque bounded handle}}"
      request_binding_projection_id: "{{required new-identity safe binding before intent creation}}"
      operation_key_projection: "{{required opaque collision-detecting reference}}"
      state: "{{not_intended|intent_recorded|dispatching|confirmed_applied|confirmed_absent|reconciling|collision|abandoned_unknown}}"
      retry_allowed: "{{true only after confirmed_absent under a new fenced attempt; otherwise false}}"
      receipt_projection_id: "{{required safe reference when a receipt exists; otherwise null}}"

release_and_deployment:
  candidate_base_matches_accepted: "{{true|false}}"
  promotion_lineage_mode: "{{not_applicable|contiguous|cumulative_reconciliation|required_but_missing}}"
  promoted_root_to_target_coverage: "{{required public proof projection or null}}"
  unresolved_accepted_interval: "{{required list or []}}"
  deployment_activation_requested: "{{true|false; false unless exact production operation and human command are effective}}"
  deployment_lineage_projection: "{{required only for an authorized deployment verification or activation; otherwise null}}"
```

## Preflight contract

The dispatcher must reject before executor start unless all role-applicable template markers are resolved and all exact versions agree. A conditional `null` above is resolved when its condition requires `null`; it is not an unresolved marker. Preflight checks the private manifest issue receipt and exact role-specific prompt bytes; staged `authority_source`; separate observed, accepted, promoted, and deployed facts; accepted-spec proof for implementation; dependency and surface closure; current attempt reservation and fence; the review-cycle phase; context firewall and hidden-evaluation projection; structured effective-operation intersection; every conditionally required human command; cumulative budget arithmetic; and every prior effect intent and collision state. Builder preflight rejects a preallocated verifier. Verifier preflight requires a frozen candidate and a new-identity receipt proving that the current attempt and context differ from the source builder.

Failure emits a durable typed `launch_rejected` receipt and never activates the reserved attempt, calls a model, or performs an effect. A launched model receives only a new-identity safe authorization projection with status `launch_allowed`; it never receives the full private launch receipt or any private digest. If runtime drift later contradicts the projection, stop before the affected action and return `contract_blocked` with visible evidence.

## Assignment-specific instructions

`{{Insert only instructions needed for this slice. Reference canonical specs and runbooks instead of copying them. Do not include private manifest fields, capability values, credentials, locators, hidden-evaluation facts, peer verdicts, or private destinations.}}`

## Required output

Return a private machine-readable `ExecutionRecord` plus a concise model-safe human summary containing:

1. attempt disposition, any reducer-issued work-order terminal state, and launch-projection identity;
2. staged authority source and separate observed, accepted, promoted, and deployment facts;
3. dependency and accepted-spec proof appropriate to the work layer;
4. exact artifacts produced and their classification;
5. approach registry and blocked-route changes;
6. changed paths and complete impact classification;
7. verification evidence bound to the frozen candidate;
8. review-cycle phase and, for verification, new-identity proof of a distinct verifier attempt and context plus the current non-stale verdict;
9. cumulative work-order usage, current-attempt usage, reservations, and remaining safe budget projection;
10. every effect-intent projection, receipt, collision, and reconciliation state;
11. unresolved risks, lineage gaps, exact next action, and wake condition; and
12. proposed fields for the allowlisted `PublicReviewPacketProjection`.

The harness enriches the private `ReviewEvidencePacket` from the dispatcher manifest, hidden evaluator, budget controller, and effect ledger. The model must not request or reconstruct those private bindings. The public projector creates a new-identity packet from an explicit allowlist; never copy or redact the private packet into a PR body.

If any visible required value remains a template marker, is stale, or conflicts with current state, do not continue. Return `contract_blocked` with the exact visible field and evidence. Any unresolved contradiction over authority, scope, evaluator, success predicate, fence, budget, or effect state is blocking. Reject a requested mode above its ceiling. For each intended mutation, resolve one exact `effective_operations` entry and, when its `human_command.requirement` is `required`, its current matching receipt projection. A role, work kind, mode, or capability reference alone is insufficient.

A builder returns `candidate_frozen_pending_verification`; a verifier returns `verifier_result_reported`. Neither is a work-order terminal state or success claim. The reducer alone may emit `candidate_ready_local` or `pr_open_waiting_human`, and only after a non-stale `ready` verdict bound to the exact candidate and review cycle. Release readiness additionally requires complete contiguous or cumulative SPEC-019 lineage from the current promoted root. It never implies SPEC-025 deployment.

A blocker or human-gate state requires a non-stale `blocker_valid` verdict or deterministic scheduler receipt. `cancelled` requires an authenticated external cancellation projection and conclusive disposition of every issued effect intent. `budget_exhausted_incomplete` requires a budget-controller receipt over cumulative usage with no uncertain charge. Ambiguous cancellation, usage, cost, or external effect remains in reconciliation and cannot be reported as cancellation, budget exhaustion, or safe retry. No terminal-state audit may be omitted.
