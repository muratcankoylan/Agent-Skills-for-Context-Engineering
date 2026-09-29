# Private Attempt Manifest and Safe Launch Projection

Template version: bootstrap-v2
Classification: private dispatcher record
Owner contracts: SPEC-005, SPEC-012, SPEC-013, and SPEC-014 after activation

This template defines the immutable dispatcher-side record for one current attempt and the safe projection delivered to its model. It is a bootstrap contract, not authority by itself. A builder and verifier always use different manifests created at different lifecycle points. The filled manifest, private receipt, hidden-evaluation bindings, capability records, effect destinations, and credential references never enter model context or a public review artifact.

## Exact-byte bootstrap profile

During bootstrap, the canonical manifest is a standalone YAML document produced from the first code block below, not this Markdown wrapper. Its profile is `attempt-manifest-exact-bytes-v1`:

- encode as UTF-8 without BOM, use LF line endings, and include exactly one final LF;
- retain the key order and two-space indentation in this template; tabs, comments, directives, tags, anchors, aliases, merge keys, duplicate keys, and implicit map keys are forbidden;
- quote every string, encode conditional absence as unquoted `null`, use unquoted lower-case `true` and `false`, and encode every integer as unsigned base-10 without leading zeroes;
- array order is significant; object and byte identities are full lower-case hexadecimal where their registered type requires it;
- perform no Unicode, path, Git, scalar, or newline normalization after filling; and
- compute SHA-256 over the exact final YAML bytes and record it only in the separate `AttemptManifestIssueReceipt`.

The canonical YAML contains no `manifest_digest`, signature over itself, receipt that depends on its digest, or projection field that embeds either value. The work brief, prompt payload, execution bundle, and safe projection bound inside it also omit this manifest's identity, digest, and any receipt derived from them. Adding one would create a self-hashing cycle. The trusted compiler freezes those members, the YAML, and model-safe projection first. An authenticated issuer then creates the external receipt over both exact byte strings. Any edit, reserialization, reordered list, or changed line ending creates a new manifest and launch identity.

## Canonical private manifest body

```yaml
profile: "attempt-manifest-exact-bytes-v1"
template_version: "bootstrap-v2"
classification: "private"
manifest_id: "{{required opaque non-content-derived ID}}"
launch_class: "{{normal|effect_reconciliation|budget_reconciliation|cancellation_reconciliation}}"
created_at: "{{required RFC3339 UTC}}"

issuance:
  request_id: "{{required opaque ID}}"
  issuer_principal_id: "{{required authenticated principal ID}}"
  issuer_authentication_receipt_ref: "{{required private reference independent of these manifest bytes}}"
  constitution_decision_ref: "{{required private allow-decision reference}}"
  runtime_grant_ref: "{{required private issue-manifest grant reference}}"
  issue_operation_key: "{{required stable opaque key}}"
  expected_dispatcher_version: "{{required unsigned integer}}"

authority:
  repository_id: "{{required registered identity}}"
  default_branch: "{{required full branch ref}}"
  authority_source:
    kind: "{{bootstrap_exact_git|spec_004_baseline|spec_007_reconciled}}"
    version: "{{required unsigned integer}}"
    private_source_ref: "{{required private receipt or projection reference}}"
    source_digest: "{{required sha256 digest}}"
    later_source_absent_ref: "{{required private proof for bootstrap_exact_git or spec_004_baseline; otherwise null}}"
  bootstrap_exact_git:
    commit: "{{required full object ID only for bootstrap_exact_git; otherwise null}}"
    tree: "{{required full object ID only for bootstrap_exact_git; otherwise null}}"
    local_default_ref_observation_ref: "{{required only for bootstrap_exact_git; otherwise null}}"
    authenticated_human_acceptance_ref: "{{required only for bootstrap_exact_git; otherwise null}}"
  constitution_version: "{{required}}"
  constitution_digest: "{{required sha256 digest}}"
  authority_vocabulary_digest: "{{required sha256 digest}}"
  policy_context_digest: "{{required sha256 digest}}"

repository_state:
  observed_default_branch_head:
    commit: "{{required full object ID}}"
    tree: "{{required full object ID}}"
    observation_ref: "{{required immutable provider or exact-Git observation}}"
    observed_at: "{{required RFC3339 UTC}}"
  accepted_public:
    commit: "{{required full object ID}}"
    tree: "{{required full object ID}}"
    pointer_version: "{{required unsigned integer}}"
    acceptance_ref: "{{required authority-source-owned reference}}"
    relation_to_observed_head: "{{equal|behind|diverged|unknown}}"
  promoted_quality:
    status: "{{not_established|current|lineage_gap|unknown}}"
    root_commit: "{{required full object ID when established; otherwise null}}"
    root_tree: "{{required full object ID when established; otherwise null}}"
    organization_version: "{{required unsigned integer when established; otherwise null}}"
    promotion_record_ref: "{{required when established; otherwise null}}"
    parent_promotion_ref: "{{required when established beyond bootstrap; otherwise null}}"
    accepted_interval_gap: "{{none|unattested_acceptance|incomplete_reconciliation|unknown|not_applicable}}"
  active_deployment:
    status: "{{not_established|inactive|active|degraded|paused|unknown}}"
    deployment_ref: "{{required private SPEC-025 reference when established; otherwise null}}"
    accepted_commit: "{{required full object ID when established; otherwise null}}"
    promotion_record_ref: "{{required when established; otherwise null}}"
    deployment_manifest_digest: "{{required deployment-manifest digest when established; otherwise null}}"
    configuration_digest: "{{required when established; otherwise null}}"
    rollback_pointer_ref: "{{required when established; otherwise null}}"

work_order:
  id: "{{required registered ID}}"
  version: "{{required unsigned integer}}"
  digest: "{{required sha256 digest}}"
  kind: "{{required registered kind and version}}"
  classification: "{{required}}"
  input_set_digest: "{{required sha256 digest}}"
  accepted_commit_guard: "{{required repository_state.accepted_public.commit}}"
  organization_version_guard: "{{required version or bootstrap epoch}}"
  policy_context_digest: "{{required authority.policy_context_digest}}"
  assignment_spec_id: "{{required canonical SPEC-NNN}}"
  assignment_spec_revision: "{{required unsigned integer greater than zero}}"
  assignment_revises: "{{required predecessor digest or none}}"
  assignment_spec_digest: "{{required sha256 digest}}"
  assignment_spec_status: "{{required canonical lifecycle status}}"
  assignment_layer: "{{research|design|implementation|verification|external_coordination}}"
  lifecycle_decision_ref: "{{required private reference when applicable; otherwise null}}"
  lifecycle_receipt_ref: "{{required immutable private receipt}}"
  requested_transition: "{{required canonical transition or none}}"
  transition_editable_fields_digest: "{{required sha256 digest over the exact allowed field set}}"
  accepted_spec_proof_ref: "{{required for implementation or implementation verification; otherwise null}}"
  dependency_revisions: "{{required exact ordered SPEC-NNN@revision bindings or none}}"
  dependency_stage_floor_receipt_ref: "{{required immutable receipt}}"
  dependency_closure_digest: "{{required sha256 digest}}"
  acceptance_contract_digest: "{{required sha256 digest}}"

review_cycle:
  id: "{{required opaque ID}}"
  generation: "{{required unsigned integer}}"
  phase: "{{building|verifying}}"
  candidate_parent_ref: "{{required frozen parent candidate or null}}"
  source_builder_attempt_id: "{{current attempt ID for phase building; closed source attempt ID for phase verifying}}"
  source_builder_attempt_ref: "{{current reservation for phase building; immutable closed attempt for phase verifying}}"
  source_builder_context_digest: "{{current context digest for phase building; prior builder context digest for phase verifying}}"
  frozen_candidate_ref: "{{required only for phase verifying; otherwise null}}"
  current_verifier_attempt_id: "{{current attempt ID only for phase verifying; otherwise null}}"
  distinct_identity_and_context_receipt_ref: "{{required only for phase verifying; otherwise null}}"
  verifier_reservation_state: "{{not_created_before_candidate_freeze for phase building|current_attempt for phase verifying}}"
  forbidden_information_flows: "builder reasoning to verifier; verifier identity or verdict to builder before freeze; peer first-pass verdicts; hidden evaluation material to either unauthorized role"
  repair_policy: "new candidate identity, new verifier attempt, and new review-cycle generation"

current_attempt:
  role: "{{builder|verifier}}"
  reservation_ref: "{{required immutable reservation for this attempt only}}"
  attempt_id: "{{required registered current-attempt ID}}"
  ordinal: "{{required unsigned integer}}"
  lease_generation: "{{required unsigned integer}}"
  fence: "{{required opaque fencing value}}"
  principal_id: "{{required authenticated current principal}}"
  role_package_digest: "{{required sha256 digest or bootstrap role digest}}"
  activation_deadline_ref: "{{required accepted logical-clock proof}}"
  execution_bundle_ref: "{{required immutable bundle or bootstrap executor envelope}}"
  execution_bundle_digest: "{{required sha256 digest}}"
  executor_id: "{{required}}"
  environment_digest: "{{required sha256 digest}}"
  model_id: "{{required or deterministic-no-model}}"
  harness_digest: "{{required sha256 digest}}"
  tool_registry_digest: "{{required sha256 digest}}"

prompt_members:
  role_component_policy: "builder requires root brief, filled work brief, and output schema; verifier requires fresh-verifier brief, a filled verifier work brief bound to the frozen candidate, and output schema; resume brief is included only for an accepted-checkpoint launch"
  ordered_members:
    - identity: "{{required immutable role-applicable component reference}}"
      purpose: "{{root|work_brief|verifier_contract|frozen_candidate_task|resume|output_schema}}"
      sha256: "{{required exact-byte digest}}"
      byte_length: "{{required unsigned integer}}"
  exact_prompt_payload_digest: "{{required sha256 digest over the registered assembly contract and ordered members}}"

context_bindings:
  current_visible_package_ref: "{{required}}"
  current_visible_package_digest: "{{required sha256 digest}}"
  current_private_compilation_receipt_ref: "{{required private reference}}"
  source_builder_package_digest: "{{required only for verifier and must differ from current package; otherwise null}}"
  verifier_exclusion_receipt_ref: "{{required only for verifier; otherwise null}}"
  ordered_source_snapshot_digest: "{{required private sha256 digest}}"
  contradiction_closure_receipt_ref: "{{required}}"
  editable_surface_digest: "{{required sha256 digest}}"
  locked_surface_digest: "{{required sha256 digest}}"
  context_firewall_receipt_ref: "{{required}}"

operation_intersection:
  requested_operations:
    - operation_id: "{{required stable ID}}"
      action: "{{required registered action}}"
      resource: "{{required registered resource}}"
      target_scope_digest: "{{required sha256 digest}}"
      effect_class: "{{none|isolated_local|repository_local|external_proposal|production}}"
      required_for_predicate: "{{required boolean}}"
      operands:
        constitution_decision_ref: "{{required allow or deny decision}}"
        role_ceiling_ref: "{{required}}"
        work_order_scope_ref: "{{required}}"
        deployment_and_mode_policy_ref: "{{required}}"
        environment_and_executor_ref: "{{required}}"
        runtime_operation_grant_ref: "{{required}}"
      human_command:
        requirement: "{{required|not_required}}"
        command_ref: "{{required authenticated private command iff required; otherwise null}}"
        command_digest: "{{required sha256 digest iff required; otherwise null}}"
        bound_action: "{{required iff required; otherwise null}}"
        bound_resource: "{{required iff required; otherwise null}}"
        bound_request_digest: "{{required iff required; otherwise null}}"
        bound_accepted_commit: "{{required iff required; otherwise null}}"
        expires_at: "{{required iff required; otherwise null}}"
      resolution: "{{effective|denied}}"
      reason_code: "{{required stable reason}}"
  effective_operation_ids: "{{required exact ordered subset of requested operation IDs}}"
  denied_operation_ids: "{{required exact ordered complement}}"
  intersection_receipt_ref: "{{required authenticated reducer receipt}}"

budget_bindings:
  accounting_scope: "work_order_cumulative"
  clock_domain: "{{required accepted logical clock domain}}"
  work_order_ceiling:
    attempts: "{{required unsigned integer}}"
    deadline_micros: "{{required unsigned integer}}"
    tokens: "{{required unsigned integer}}"
    tool_calls: "{{required unsigned integer}}"
    paid_calls: "{{required unsigned integer}}"
    external_calls: "{{required unsigned integer}}"
    cost_micros_by_currency: "{{required ISO-4217-to-unsigned-integer mapping}}"
    subagents: "{{required unsigned integer}}"
    repairs: "{{required unsigned integer}}"
    retries_by_class: "{{required mapping of unsigned integers}}"
  charged_before_reservation: "{{required same-dimension receipt-backed mapping}}"
  active_reservations_before_current: "{{required same-dimension receipt-backed mapping}}"
  current_attempt_reservation: "{{required same-dimension mapping}}"
  remaining_after_all_reservations: "{{required same-dimension mapping}}"
  uncertain_charges: "{{required [] for normal launch; otherwise exact reconciliation refs}}"
  arithmetic_receipt_ref: "{{required authenticated budget-controller receipt}}"
  current_attempt_meter_ref: "{{required private meter reference}}"
  exhaustion_receipt_ref: "{{required only for an exhausted terminal state; otherwise null}}"

evaluation_bindings:
  public_epoch_ref: "{{required public reference or null}}"
  private_hidden_epoch_ref: "{{required private reference or null}}"
  private_hidden_manifest_digest: "{{required sha256 digest or null}}"
  activation_and_seal_ref: "{{required private reference or null}}"
  exposure_family_ref: "{{required private reference or null}}"
  hidden_runner_principal_id: "{{required distinct authenticated principal or null}}"
  evaluator_policy_digest: "{{required sha256 digest or not-applicable}}"
  rubric_digest: "{{required sha256 digest or not-applicable}}"
  threshold_digest: "{{required sha256 digest or not-applicable}}"
  selection_grant_ref: "{{required private reference or null}}"
  cumulative_exposure_and_budget_ref: "{{required private reference or null}}"
  opaque_eligibility_projection_ref: "{{required new-identity safe reference or null}}"
  allowed_outcome_projection_schema_ref: "{{required safe schema or null}}"
  forbidden_projection_fields: "private epoch or manifest identity or digest; task identity; membership; count; look budget; raw result; task-level error; latency oracle; private evaluator identity; private input-derived equality value"

external_effect_bindings:
  credential_broker_policy_digest: "{{required sha256 digest or not-applicable}}"
  credential_refs: "{{required private references only, never secret values, or []}}"
  effects:
    - effect_id: "{{required stable ID}}"
      effective_operation_id: "{{must resolve to operation_intersection.effective_operation_ids}}"
      adapter_id: "{{required registered adapter and version}}"
      adapter_digest: "{{required sha256 digest}}"
      private_target_ref: "{{required private bounded destination or resource reference}}"
      canonical_request_ref: "{{required immutable private byte reference}}"
      canonical_request_digest: "{{required sha256 digest}}"
      stable_operation_key: "{{required opaque key}}"
      expected_remote_version: "{{required or none}}"
      effect_intent_required: true
      prior_effect_intent_ref: "{{required for resume or reconciliation; otherwise null}}"
      prior_state: "{{not_intended|intent_recorded|dispatching|confirmed_applied|confirmed_absent|reconciling|collision|abandoned_unknown}}"
      reconciliation_policy_ref: "{{required}}"
      human_disposition_ref: "{{required only after shared ambiguous-effect disposition; otherwise null}}"

cancellation_and_recovery:
  cancellation_state: "{{none|requested|authenticated|ambiguous|reconciled}}"
  cancellation_request_ref: "{{required private authenticated reference when present; otherwise null}}"
  cancellation_work_order_digest: "{{required when present; otherwise null}}"
  effect_closure_refs: "{{required one conclusive disposition per issued intent, or []}}"
  accepted_checkpoint_ref: "{{required immutable checkpoint or null}}"
  checkpoint_payload_digest: "{{required sha256 digest or null}}"
  resume_parent_attempt_id: "{{required distinct prior attempt or null}}"
  stale_fence_denial_ref: "{{required for resume after fencing; otherwise null}}"

release_and_deployment_lineage:
  candidate_base_commit: "{{required full object ID}}"
  candidate_base_tree: "{{required full object ID}}"
  candidate_head_commit: "{{required full object ID or null before freeze}}"
  candidate_head_tree: "{{required full object ID or null before freeze}}"
  current_promoted_root_commit: "{{required full object ID or null when not established}}"
  current_promoted_root_tree: "{{required full object ID or null when not established}}"
  accepted_first_parent_interval_ref: "{{required exact interval or null}}"
  promotion_lineage_mode: "{{not_applicable|contiguous|cumulative_reconciliation|required_but_missing}}"
  complete_delta_impact_manifest_ref: "{{required for release work; otherwise null}}"
  promotion_attestation_ref: "{{required only after current exact-head attestation; otherwise null}}"
  deployment_activation_request_ref: "{{required only for exact production work; otherwise null}}"
  complete_deployment_promotion_lineage_ref: "{{required only for deployment work; otherwise null}}"
  canary_and_health_receipt_refs: "{{required only after canary completion; otherwise []}}"

review_outputs:
  private_evidence_packet_schema_ref: "{{required private schema}}"
  private_evidence_destination_ref: "{{required private storage binding}}"
  public_review_projection_schema_ref: "{{required public schema}}"
  public_projection_transform_ref: "{{required allowlisted new-identity transform}}"
  public_projection_policy_decision_ref: "{{required}}"
  public_forbidden_fields: "private manifest ID or digest; private source ID or digest; capability, command, credential, locator, destination, hidden, private effect, installation, ruleset, or equality-oracle data"

safe_launch_projection:
  id: "{{required new-identity ID}}"
  schema_ref: "{{required model-safe projection schema}}"
  exact_bytes_ref: "{{required immutable bytes prepared before manifest receipt}}"
  sha256: "{{required exact-byte digest}}"
  byte_length: "{{required unsigned integer}}"
  intended_role: "{{must equal current_attempt.role}}"
  allowed_field_set_digest: "{{required sha256 digest}}"
  projection_transform_ref: "{{required allowlisted transform}}"
  prohibited_fields: "manifest identity or digest; filled-work-brief digest; private receipt identities; raw grants or commands; credentials or locators; private targets; hidden bindings; peer identity or verdict; private evidence; denied-item identities or counts"

preflight_contract:
  required_checks: "exact-byte and issue receipt; staged authority source; observed/accepted/promoted/deployed separation; exact lifecycle and dependency bindings plus accepted-spec proof only for implementation; reservation, attempt, fence, review independence, prompt and context bindings; effective-operation intersection and conditional human commands; cumulative budget arithmetic and uncertain charges; hidden projection firewall; prior effects, collisions, cancellation, release and deployment lineage"
  normal_launch_requires_zero_uncertain_charges: true
  reconciliation_launch_may_only_narrow_operations: true
  failure_disposition: "launch_rejected"
  failure_effect: "no executor activation, model call, external effect, or execution-budget charge"
```

## External authenticated receipts

The following receipts are separate records and are not members of the canonical manifest bytes.

`AttemptManifestIssueReceipt` binds:

- `manifest_id`, the SHA-256 digest and byte length of the exact manifest, and `attempt-manifest-exact-bytes-v1`;
- the exact safe-launch-projection ID, digest, byte length, schema, and transform;
- exact work-order, review-cycle, selected attempt, reservation, lease generation, and fence;
- issuer principal, authentication receipt, constitution decision, runtime grant, operation key, expected dispatcher version, and issue time; and
- trusted dispatcher identity, receipt version, and an authenticated append or signature envelope. The envelope may digest the frozen receipt bytes; the receipt body never contains its own digest.

The receipt is valid only when its issuer and dispatcher are authenticated independently of prompt text and its action/resource are allowed. Exact replay returns the first receipt. Reusing the issue operation key or manifest ID with changed manifest or projection bytes is an issuance collision and launches nothing.

`AttemptLaunchReceipt` is a private record created only after every preflight check succeeds. It binds the issue receipt; current authority-source, repository-pointer, work-order, attempt, fence, context, operation-intersection, budget, evaluator-firewall, and effect-state versions; and the exact safe projection selected for the executor. It never enters model context.

A separate `SafeLaunchAuthorizationProjection` is derived from that receipt with a new identity and an allowlisted transform. Its body exposes only `launch_allowed`; the exact safe-launch-projection ID and digest; current attempt ID, lease generation, and fence; issue and expiry time; and a public verification-key or safe journal-proof reference. A separate authenticated envelope digests or signs those frozen projection bytes; the projection body does not contain its own digest. It contains no private receipt, manifest, source, evaluator, effect, target, budget-component, capability, command, credential, or denied-item identity or digest. This safe projection and envelope are the only launch proof delivered to a model.

`AttemptLaunchRejected` is created on any failed preflight. It binds the issue receipt when issuance succeeded, exact failed versions, stable reason codes, safe operator-facing diagnostics, and proof that no attempt activation or effect receipt was created. It does not enter model context because no model launches. A retry requires a newly compiled manifest and projection unless exact receipt replay proves that no input changed and policy explicitly permits re-evaluation.

## Projection and lifecycle rules

The model receives only the safe launch projection, filled work brief, permitted context package, and `SafeLaunchAuthorizationProjection`. It never receives either private receipt. A builder manifest covers only the builder attempt and records `verifier_reservation_state: not_created_before_candidate_freeze`; it cannot bind a future verifier identity, reservation, context, prompt, or budget. After candidate freeze, a separately compiled verifier manifest relates its current verifier attempt to the closed source builder and frozen candidate through the review-cycle and independence receipt. A repair creates a new candidate and review-cycle generation, invalidating the former verifier inputs. The builder never receives the verifier's private identity, context, first-pass verdict, hidden-evaluation bindings, or private manifest digest.

The builder reports `candidate_frozen_pending_verification` and terminates its attempt. The verifier later reports `verifier_result_reported` and terminates its distinct attempt. Neither disposition is a successful work-order terminal state. The reducer alone accepts the result, schedules repair, or emits a terminal candidate or blocker decision.

For `phase: building`, `current_attempt.role` and `source_builder_attempt_id` identify the same builder attempt, the current and source-builder context digests agree, and `frozen_candidate_ref`, `current_verifier_attempt_id`, and the independence receipt are `null`. For `phase: verifying`, the source builder is closed, `frozen_candidate_ref` names its exact frozen output, `current_attempt.role` is `verifier`, `current_verifier_attempt_id` equals the current attempt and differs from the source builder, and the independence receipt proves distinct principals, attempts, contexts, and prohibited information flows. Any other combination rejects launch.

`authority_source` advances only `bootstrap_exact_git -> spec_004_baseline -> spec_007_reconciled`. The observed default-branch head may advance without either accepted or promoted state. SPEC-007 alone advances accepted public state after it takes ownership. SPEC-019 alone advances the promoted-quality root from a complete contiguous or cumulative attestation. SPEC-025 alone advances the active deployment after complete promotion lineage and human activation. Preflight denies a stale source, conflated pointer, or uncovered accepted interval.

An adapter may execute only after the reducer durably records an `EffectIntent` over the exact manifest-bound request, operation key, target, effective operation, work order, attempt, fence, expected remote version, budget reservation, and required human command. A same-key/different-byte request is a collision. An ambiguous response remains `reconciling`; authoritative read precedes any retry, and only `confirmed_absent` can make a new fenced attempt eligible. Cancellation cannot erase an issued intent. `abandoned_unknown` is permanently non-retryable.

Budget arithmetic is cumulative at work-order scope. In every dimension, the ceiling must equal charged usage plus prior active reservations plus the current reservation plus remaining capacity; all values are nonnegative and one receipt owns each charge or reservation exactly once. Attempt, repair, retry, verifier, evaluator, subagent, reconciliation, and ambiguous provider charges all consume or reserve that ceiling. A normal launch requires zero uncertain charges. Reconciliation-only launches receive narrowed no-new-effect operations and a separately bounded administration reservation. Neither a model nor a timeout can issue cancellation or budget exhaustion; those terminal states require authenticated external receipts and conclusive effect or charge closure.

The private review evidence packet may resolve manifest, hidden, budget, effect, and deployment references. Its public projection must have a new identity and an allowlisted transform receipt. It cannot contain the private manifest identity or digest or any value that serves as a private-input equality oracle. Merge remains human-only. A promotion record never claims deployment, and a deployment request must prove a complete current SPEC-019 lineage rather than merely naming the latest accepted commit.
