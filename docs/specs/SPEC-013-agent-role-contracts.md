# SPEC-013: Agent Roles, Prompts, Skills, and Capability Contracts

Status: draft
Wave: 2
Classification: public
Owners: organization designer agent; human maintainer
Depends on: SPEC-000, SPEC-005, SPEC-012

## Decision

Agents will be instantiated from versioned role manifests, not persistent personas or informal group chat. A role binds objective, input and output schemas, allowed capabilities, information-firewall profile, prompt components, skill set, budgets, escalation policy, and evaluator independence. Models and runtimes are replaceable assignments to roles. Coordination happens through work orders and artifacts.

## Context and current repository touchpoints

The repository contains reusable skills and activation descriptions, but it does not yet define organization-level roles or prompt assembly. The organization needs scouts, independent reviewers, adjudicators, curators, authors, evaluators, PR stewards, community editors, operators, and meta-harness researchers with intentionally different information and authority.

## Goals

- Make role behavior reproducible across models and runtimes.
- Prevent accidental authority growth through prompt wording.
- Enforce independent review and proposer/evaluator separation.
- Version every prompt component and skill selection in run provenance.

## Non-goals

- Simulating corporate personalities or unrestricted agent conversation.
- Giving each role a permanent private memory.
- Assuming one model is best for every role.

## Invariants

1. Capability comes from the constitution and runtime grant, never from a prompt claim.
2. Each role has one primary responsibility and a typed deliverable.
3. First-round source reviewers are blind to each other's verdicts.
4. Candidate authors cannot see hidden evaluation data or scoring code.
5. Evaluators receive candidate identity and artifacts but no persuasive author rationale unless the rubric explicitly requires it.
6. Prompt, skill, model, runtime, tool, and context digests are recorded per execution.
7. Agent-to-agent communication that matters becomes an artifact or event.

## Interfaces and data

Create public manifests under `researcher/organization/roles/`. Required fields are role ID and version, mission, accepted work-order kinds, input schema, output schema, context profile, prompt component IDs, required and optional skills, capability requests, default and maximum budgets, independence constraints, escalation rules, compatible models and executors, and acceptance validator.

Initial roles:

- source scout;
- methodology reviewer A and B;
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

Prompts are assembled from a stable constitutional preamble, role contract, typed task brief, context map, output schema, and limited recovery instructions. Each component has an ID, version, digest, tests, owner, and protected/editable classification. Skill activation remains measurable through the router and body-alignment benchmarks.

## State and failure behavior

Role revisions move `draft -> compatibility_tested -> accepted -> active -> deprecated`. An incompatible model or executor assignment prevents dispatch. Output-schema failure receives one bounded repair attempt using the same authority and context; repeated failure is terminal and retained as evaluation data.

## Implementation sequence

1. Define manifest and prompt-component schemas.
2. Encode scout, reviewer, curator, author, evaluator, and PR steward roles.
3. Add a role compiler that resolves skills, context profile, and capabilities.
4. Run conformance across at least two model families where available.
5. Add remaining operational and meta-harness roles after their work-order kinds exist.

## Migration and rollback

Current script prompts become versioned `legacy` components and remain the control. Activate role manifests by workflow. Rollback pins the prior role and prompt digests without deleting failed revisions.

## Observability

Measure task success, format failures, escalations, context leakage, tool-denial attempts, latency, cost, inter-review agreement, role-to-model compatibility, and skill activation by role version.

## Verification

- Capability-denied tools remain denied even if a prompt requests them.
- Blind reviewers cannot access peer results.
- The same role package runs through two conforming executors.
- A prompt-component change produces a new digest and candidate lineage.
- Schema repair cannot expand permissions or context.
- Agent handoff resumes from artifacts without original session history.

## Acceptance criteria

- [ ] Initial roles have complete manifests and typed outputs.
- [ ] Authority and information firewalls are enforced outside prompts.
- [ ] Prompt assembly is deterministic and provenance-complete.
- [ ] Model and executor compatibility is explicit.
- [ ] Existing skill activation and body checks remain mandatory.
- [ ] No required coordination depends on private conversational memory.

## Pull-request evidence

Attach role manifests, compiled prompt examples, firewall and denied-capability tests, cross-executor result, model compatibility matrix, and one artifact-only handoff trace.
