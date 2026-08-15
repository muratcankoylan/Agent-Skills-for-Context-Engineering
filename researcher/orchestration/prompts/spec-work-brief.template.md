# Per-Wake Specification Work Brief

Template version: bootstrap-v1

This template is filled by a trusted human operator during bootstrap and by the context/work-order compiler after SPEC-005, SPEC-012, and SPEC-013. Do not ask a model to invent missing values.

## Launch envelope

```yaml
work_order_id: "{{required}}"
issued_at: "{{required RFC3339 UTC}}"
mode: "{{observe|proposal|shadow|production}}"
authorized_mode_ceiling: "{{required ceiling derived from accepted capabilities}}"

authority:
  default_branch: "{{required}}"
  authoritative_commit: "{{required full SHA}}"
  constitution_version: "{{required}}"
  constitution_digest: "{{required sha256 digest}}"
  decision_record: "{{required authority decision reference}}"
  actor_identity: "{{required authenticated identity reference}}"
  capability_grant: "{{required reference}}"
  allowed_actions: "{{required exact action list with resource scope}}"
  denied_actions: "{{required exact action list; must include merge/deploy during bootstrap}}"
  human_command: "{{optional authenticated command reference}}"

assignment:
  spec_id: "{{required canonical SPEC-NNN}}"
  spec_path: "{{required}}"
  spec_digest: "{{required sha256 digest}}"
  authoritative_status: "{{required}}"
  dependency_statuses: "{{required mapping}}"
  allowed_transition: "{{required or none}}"
  vertical_slice: "{{required exact name}}"
  work_layer: "{{research|design|implementation|verification|external_coordination}}"
  objective: "{{required outcome}}"
  artifact_predicate: "{{required falsifiable predicate}}"
  definitions: "{{required load-bearing terms, units, empty/duplicate/stale/partial cases}}"
  non_counting_outcomes: "{{required assignment-specific refusal list}}"
  adversarial_failure_modes: "{{required domain-specific list including circularity analogue}}"

surfaces:
  editable: "{{required ordered paths/patterns}}"
  append_only: "{{required ordered paths/patterns or []}}"
  locked: "{{required ordered paths/patterns}}"
  human_controlled: "{{required ordered paths/actions}}"
  classification_ceiling: "{{required}}"

repository:
  branch: "{{required}}"
  base_sha: "{{required full SHA}}"
  expected_head_sha: "{{required full SHA or null for new local work}}"
  pull_request: "{{required number and head SHA or null}}"
  worktree_mode: "{{read_only|single_writer|isolated_writer}}"
  existing_changes: "{{required path inventory and ownership}}"

context:
  package_id: "{{required reference or bootstrap identifier}}"
  package_digest: "{{required sha256 digest}}"
  ordered_artifacts: "{{required identities and digests}}"
  contradictions:
    - id: "{{stable identity}}"
      participants: "{{artifact/claim identities and digests}}"
      authority_order: "{{applicable precedence with evidence}}"
      disposition: "{{resolved|unresolved}}"
      evidence: "{{required references}}"
      blocking: "{{true for unresolved authority, scope, evaluator, or predicate conflicts}}"
  rejected_routes: "{{required list or []}}"
  freshness:
    authoritative_git_sha: "{{required full SHA}}"
    external_event_cursor: "{{required identity/digest or bootstrap marker}}"
    sources:
      - id: "{{source identity}}"
        observed_at: "{{required RFC3339 UTC}}"
        maximum_age_seconds: "{{required integer}}"
        expires_at: "{{required RFC3339 UTC}}"
  exclusions: "{{required with reasons}}"
  previous_checkpoint: "{{required reference or null}}"

verification:
  required_gates: "{{required exact commands/predicates}}"
  independent_verifier: "{{required identity policy}}"
  evaluation_epoch: "{{required reference or not-applicable}}"
  protected_evaluators: "{{required references or []}}"
  migration_obligation: "{{required}}"
  rollback_obligation: "{{required}}"
  observability_obligation: "{{required}}"
  operator_note_obligation: "{{required}}"

budget:
  wall_clock_deadline: "{{required}}"
  tool_calls: "{{required bound}}"
  paid_calls: "{{required bound, normally 0}}"
  cost_usd: "{{required bound}}"
  retries: "{{required bound by class}}"
  subagents: "{{required bound}}"

external_state:
  observed_at: "{{required}}"
  github_state: "{{required branches, checks, reviews, commands, deliveries}}"
  wake_event: "{{required}}"
  event_cursor: "{{required last durable event identity/digest or bootstrap marker}}"
  side_effects: "{{required intended/pending/completed effects with idempotency key, receipt, and reconciliation state, or []}}"
```

## Assignment-specific instructions

`{{Insert only instructions needed for this slice. Reference canonical specs and runbooks instead of copying them.}}`

## Required output

Return a machine-readable execution record plus a concise human review summary containing:

1. terminal state;
2. authority and dependency proof;
3. exact artifacts produced;
4. approach registry and blocked-route changes;
5. changed paths and classifications;
6. verification evidence bound to candidate identity;
7. external attempt-manifest identity;
8. independent audit identity and verdict for every candidate state;
9. budget consumed;
10. unresolved risks;
11. exact next action and wake condition.

If any required launch value remains a template marker, is stale, or conflicts with repository state, do not continue. Return `contract_blocked` with the exact missing or contradictory field. Any unresolved contradiction over authority, scope, evaluator, or success predicate is blocking. Reject `mode` when it exceeds `authorized_mode_ceiling`; then verify every intended action appears exactly in `allowed_actions` for the target resource. A capability reference without this resolved action view is insufficient.

`candidate_ready_local` and `pr_open_waiting_human` require a non-stale `ready` verdict bound to the exact candidate and attempt manifest. A blocker or human-gate state requires a non-stale `blocker_valid` verdict or deterministic scheduler receipt bound to the same attempt. `cancelled` requires an authenticated external cancellation event; `budget_exhausted_incomplete` requires an external budget-controller receipt. No terminal-state audit may be omitted.
