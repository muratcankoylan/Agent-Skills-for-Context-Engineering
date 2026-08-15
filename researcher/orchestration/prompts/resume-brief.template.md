# Resume from Structured Checkpoint

Template version: bootstrap-v1

## Objective

Resume one bounded specification-program attempt without relying on conversation history. Revalidate the checkpoint against authoritative repository and external state before continuing.

## External checkpoint envelope

The envelope is stored separately from the payload it hashes. During bootstrap, `payload_digest` is SHA-256 over the checkpoint payload's exact UTF-8 bytes. The digest never appears inside those bytes. A future registered `StructuredCheckpoint` may replace this with the repository canonical JSON profile.

```yaml
checkpoint_envelope_id: "{{required stable identity}}"
attempt_manifest_digest: "{{required external attempt manifest digest}}"
payload_digest: "{{required sha256 digest of exact payload bytes}}"
digest_profile: "sha256-exact-utf8-v1"
```

## Required checkpoint payload

```yaml
checkpoint_id: "{{required}}"
created_at: "{{required RFC3339 UTC}}"
terminal_state: "{{candidate_ready_local|pr_open_waiting_human|human_gate|contract_blocked|external_dependency_blocked|budget_exhausted_incomplete|cancelled}}"

objective: "{{required}}"
success_predicate: "{{required}}"
work_layer: "{{required}}"

authority:
  authoritative_commit: "{{required full SHA}}"
  constitution_digest: "{{required digest}}"
  decision_record: "{{required reference}}"
  spec_id: "{{required}}"
  spec_digest: "{{required digest}}"
  spec_status: "{{required}}"
  dependency_statuses: "{{required}}"

repository:
  branch: "{{required}}"
  base_sha: "{{required}}"
  head_sha: "{{required or null}}"
  pull_request: "{{required number/head or null}}"
  tree_digest: "{{required or null}}"
  changed_paths: "{{required with ownership/classification}}"
  staged_paths: "{{required list}}"
  untracked_paths: "{{required list}}"

context:
  attempt_manifest_digest: "{{required}}"
  root_prompt_digest: "{{required}}"
  work_brief_digest: "{{required}}"
  verifier_prompt_digest: "{{required}}"
  resume_prompt_digest: "{{required}}"
  context_package_digest: "{{required}}"
  criteria_digest: "{{required}}"
  evaluator_epoch: "{{required identity and digest or not-applicable}}"
  thresholds_digest: "{{required digest or not-applicable}}"
  ordered_artifacts: "{{required}}"
  contradictions: "{{required typed list with authority order, disposition, evidence, and blocking status, or []}}"

event_position:
  last_sequence: "{{required integer or bootstrap marker}}"
  last_event_id: "{{required identity or null}}"
  last_event_digest: "{{required digest or null}}"

external_effects:
  - effect_id: "{{stable identity}}"
    action: "{{push|open_pr|update_pr|comment|notify|other}}"
    target: "{{exact resource}}"
    idempotency_key: "{{required}}"
    intent_digest: "{{required}}"
    status: "{{intended|unknown_after_attempt|committed|reconciled_no_effect|failed_terminal}}"
    receipt: "{{provider identity/delivery reference or null}}"
    reconciled_at: "{{required for reconciled/committed, otherwise null}}"

decisions: "{{required decision ledger}}"
approach_registry: "{{required ideas, evidence, status}}"
blocked_routes: "{{required route, failure mechanism, reopening condition}}"
feedback_applied: "{{required scoped feedback atoms or []}}"

verification:
  completed: "{{commands, candidate identity, exit, artifacts}}"
  failed: "{{same shape or []}}"
  invalidated: "{{same shape or []}}"
  independent_audit: "{{reference/verdict or null}}"

budget:
  original: "{{required}}"
  consumed: "{{required}}"
  remaining: "{{required}}"

unresolved_findings: "{{required list or []}}"
exact_next_action: "{{required single action}}"
wake_condition: "{{required event or command}}"
stop_conditions: "{{required}}"
```

## Resume protocol

1. Resolve the external envelope and verify its exact payload digest before parsing the checkpoint or resolving referenced artifacts.
2. Compare protected-default-branch, spec status, dependencies, constitution, durable event position, branch, PR head, checks, reviews, and external deliveries with the checkpoint.
3. Classify every difference as expected wake progress, harmless drift, invalidated assumption, authority change, conflicting external write, or corruption.
4. Recompile a new per-wake work brief and external attempt manifest from current authoritative state. Do not reuse stale capabilities, budgets, approvals, evaluator epochs, thresholds, prompt components, or editable surfaces.
5. Reconcile every `unknown_after_attempt` or unreceipted external effect by idempotency key, intent digest, and provider state before retrying. Never infer failure from a missing local receipt.
6. Invalidate evidence whose candidate, environment, criterion, or evaluator identity changed.
7. Continue only the exact next action if it remains authorized and useful. Otherwise emit a new typed blocker checkpoint.

An abstractive summary may orient the resumed agent, but it cannot replace any referenced authority or evidence artifact. If checkpoint integrity or identity resolution fails, stop with `contract_blocked` or an integrity halt as specified by the owning runtime.
