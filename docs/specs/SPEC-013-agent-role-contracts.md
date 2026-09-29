# SPEC-013: Agent Roles, Prompts, Skills, and Capability Contracts

Status: draft
Revision: 1
Revises: none
Wave: 2
Classification: split
Owners: organization designer agent; human maintainer
Depends on: SPEC-000, SPEC-005, SPEC-006, SPEC-012

## Decision

Agents will be instantiated from versioned role manifests, not persistent personas or informal group chat. A role binds one primary responsibility, typed inputs and outputs, a capability ceiling, an accepted SPEC-012 context profile, prompt components, skill set, budgets, escalation policy, and independence requirements. Models and runtimes are replaceable assignments to roles. Coordination happens through work orders, events, and artifacts.

Role compilation cannot grant authority or define an information firewall. The compiler produces an immutable `RolePackage`; SPEC-005 creates an `AttemptReservation`; the dispatcher authorizes a reservation-bound `ContextRequest`; the context compiler produces a `ContextPackage`; prompt assembly binds the exact package; and SPEC-014 freezes the result into an `ExecutionAttemptBundle` before SPEC-005 activates the lease.

## Context and current repository touchpoints

The repository contains reusable skills and measurable activation descriptions but no organization-level role, assignment, or prompt-assembly contract. The organization needs scouts, independent reviewers, adjudicators, curators, authors, evaluators, PR stewards, community editors, operators, and meta-harness researchers whose information and authority differ intentionally and mechanically.

## Goals

- Make role behavior reproducible across conforming models and executors.
- Prevent authority growth through prompt wording, skill text, or runtime defaults.
- Enforce proposer, reviewer, evaluator, and adjudicator separation where required.
- Version every role, prompt component, skill selection, assignment, and compatibility observation.
- Let conformance and evaluation determine model-to-role fitness rather than one global model preference.

## Non-goals

- Simulating corporate personalities or unrestricted agent conversation.
- Giving each role permanent private memory.
- Defining firewall rules that belong to SPEC-012.
- Assuming a declared compatible model is empirically effective.

## Invariants

1. Capability comes from authenticated policy and runtime grants, never from a prompt, skill, role claim, or model output.
2. Each role has one primary responsibility and one typed deliverable family.
3. First-round reviewers are assigned distinct principals and cannot access each other's verdicts.
4. Candidate authors cannot access hidden evaluation data, hidden tasks, scoring code, or protected evaluator reasoning.
5. Evaluators receive only the context their accepted profile permits; persuasive author rationale is excluded unless the preregistered rubric requires it.
6. Role, profile, prompt, skill, model, harness, executor, tool, and context digests are recorded per attempt.
7. Agent-to-agent communication that affects work becomes a typed artifact or event.
8. Mode does not grant actions. Effective capabilities are the intersection of constitution, role ceiling, work order, deployment and mode policy, environment and executor support, and broker-issued operation grant.
9. A repair cannot expand context, authority, mode, budget class, or allowed outputs.
10. Two prompt roles in one process or session do not constitute organizational independence.
11. Role assignment is derived only from SPEC-005 reservation and attempt events; the role subsystem has no independent assignment writer.

## Interfaces and data

Create versioned public role manifests under `researcher/organization/roles/`. Required fields are role ID and version, mission, accepted work-order kinds, input schema, output schema, accepted context-profile ID and digest, prompt-component IDs, required and optional skills, capability ceiling, default and maximum budgets, independence constraints, escalation rules, model and executor requirements, and acceptance validator.

Initial role families are:

- source scout;
- methodology reviewer;
- evidence adjudicator;
- claim and mechanism curator;
- skill or harness change author;
- evaluation designer;
- independent evaluator;
- PR and release steward;
- community editor;
- context engineer;
- meta-harness experimenter;
- operations reconciler.

Multiple independent reviewers are assignments of the methodology-reviewer contract to distinct principals and attempts, not duplicated persona manifests.

`RolePackage` is a deterministic compiled artifact containing the role-manifest digest, resolved prompt-component and skill digests, capability ceiling, context-profile digest, input and output schema digests, independence requirements, budget envelope, escalation rules, and selected model/executor compatibility records. It contains no work-order secret and grants no action by itself.

`RoleAssignmentView` is a private deterministic projection, not a separately writable object. It is derived from the exact `RolePackage` reference and principal in a SPEC-005 `AttemptReservation`, the activated `AttemptDescriptor`, and later attempt suspension, completion, fencing, or revocation events. It binds role package, principal, work order, attempt, evaluator or proposer cohort, incompatibilities, and lease bounds. Its identity is distinct from the public role revision, but it has no create, update, or delete API. A principal can hold more than one role over time; the SPEC-005 reservation transaction rejects a conflicting active role in the same protected decision lineage unless governing policy supplies and records an explicit exception.

Prompt components are a stable constitutional preamble, role contract, typed task brief, authorized context map, output schema, and bounded recovery instructions. Each component has an ID, version, digest, owner, tests, and protected or editable classification. External evidence can appear only in typed context slots and cannot override protected components.

## Compile and dispatch protocol

The normative order is:

```text
RoleManifest -> RolePackage
RolePackage + WorkOrder + PrincipalGrant -> SPEC-005 AttemptReservation
RolePackage + AttemptReservation -> authorized ContextRequest
ContextRequest + AttemptReservation -> ContextPackage + private ContextCompilationReceipt
RolePackage + ContextPackage -> exact PromptPayload
PromptPayload + effective capability intersection -> ExecutionAttemptBundle
AttemptReservation + ExecutionAttemptBundle -> SPEC-005 AttemptDescriptor
```

Each arrow emits a receipt and validates all input digests. The reservation allocates the proposed attempt ID, generation, fence, preparation budget, and expiry but starts no executor. Activation verifies that role, context, prompt, bundle, reservation, and fence digests agree, then atomically creates the immutable attempt descriptor and active lease. Reordering is invalid because assembling a prompt before context authorization can leak denied information, while granting capabilities before environment and broker intersection can exceed effective authority.

Role compilation resolves required skills exactly and rejects missing, incompatible, or unaccepted profile references. Skill activation remains measurable through router and body-alignment benchmarks; a skill may be available to a role without being forced into every prompt.

## Lifecycle and compatibility

Public role revisions move `draft -> compatibility_tested -> accepted -> deprecated`. There is no public `active` state because activation is private attempt and deployment state. `RoleAssignmentView` reports `preparing`, `active`, `suspended`, `superseded`, `completed`, or `revoked` solely by projecting the corresponding SPEC-005 reservation and attempt events; no role-subsystem transition can diverge from work-order state.

Model and executor compatibility observations use `declared`, `conformance_passed`, `evaluation_qualified`, and `incompatible`. Declaration permits only offline compilation and conformance work. Production dispatch requires the level defined by the role and deployment policy. Compatibility is scoped to exact role, model, executor, tool, prompt, and profile versions; it is not inherited across versions without a bridge evaluation.

An output-schema failure may receive only the role contract's bounded repair calls. Each repair is a separately receipted model call with its own cost and token accounting, the same or narrower context chain and capability grant, and a typed repair reason. Repeated failure is terminal evaluation data. A repair is not a hidden retry that disappears from denominators.

## State and failure behavior

Compilation fails on unresolved profile or skill references, incompatible schemas, capability requests outside the role ceiling, unsatisfied independence constraints, or missing compatibility evidence. Dispatch fails before execution if the effective capability intersection is empty for a required operation.

Attempt suspension or fencing changes the derived assignment view and prevents execution without erasing historical output. Role deprecation prevents new SPEC-005 reservations and names its successor; pinned historical attempts remain replayable. A model or executor incident appends a scoped incompatibility observation and triggers SPEC-005 reconciliation of affected active attempts.

## Implementation sequence

1. Define role manifest, role package, derived assignment-view, prompt component, compatibility, and repair-receipt schemas.
2. Encode scout, reviewer, adjudicator, curator, author, evaluator, and PR steward roles against accepted context profiles.
3. Implement deterministic role and prompt compilers, SPEC-005 reservation and activation bindings, derived assignment views, and the effective-capability intersection.
4. Run conformance and leakage fixtures across at least two model families where available.
5. Add operational and meta-harness roles only after their work-order kinds and evaluators exist.

## Migration and rollback

Current script prompts become versioned `legacy` components and remain the control. Role activation occurs per workflow through SPEC-005 reservation and attempt activation. Rollback pins prior accepted role, prompt, profile, and compatibility records without deleting failed revisions or derived attempt history.

## Observability

Measure task success, format and repair failures, repair-inclusive cost, escalations, firewall leakage, denied-operation attempts, latency, inter-review agreement, independence violations, role-to-model compatibility, skill activation, prompt size, and result differences by role-package version.

## Verification

- A role or prompt request for a denied tool does not change the effective capability intersection.
- Blind reviewers have distinct principals and attempts and cannot access peer results.
- The same role package and context package compile identically across conforming dispatchers.
- A prompt-component, skill, or profile change produces a new role or prompt digest and lineage.
- Context authorization always occurs before prompt assembly.
- A role assignment cannot be created or changed outside the SPEC-005 reservation and attempt event stream, and conflicting concurrent reservations yield one winner.
- Repair calls retain or narrow authority and context, consume visible budget, and cannot disappear from results.
- A declared-only or incompatible model assignment cannot enter a production attempt.
- Agent handoff resumes from artifacts and reducer state without original session history.

## Acceptance criteria

- [ ] Initial roles have one responsibility, complete manifests, typed inputs, and typed outputs.
- [ ] Accepted context profiles, not role prose, enforce information firewalls.
- [ ] Authority intersection is enforced outside prompts and skills.
- [ ] Role and prompt compilation is deterministic and provenance-complete.
- [ ] Public role lifecycle is separate from the private assignment view, which is derived exclusively from SPEC-005 attempt events.
- [ ] Model and executor compatibility has declared, conformance, evaluation, and incompatible states.
- [ ] Bounded repairs are separately receipted and included in cost and quality metrics.
- [ ] No required coordination depends on conversational or executor-local memory.

## Pull-request evidence

Attach role manifests and compiled packages, prompt examples, reservation-to-attempt binding proof, profile-binding and denied-capability tests, concurrent independence-assignment fixture, cross-executor compilation result, compatibility matrix, repair-cost trace, and one artifact-only handoff.
