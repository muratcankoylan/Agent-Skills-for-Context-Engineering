# SPEC-020: Meta-Harness Experiment Laboratory

Status: draft
Wave: 4
Classification: split
Owners: meta-harness scientist agent; independent evaluator agent; human maintainer
Depends on: SPEC-014, SPEC-016, SPEC-018, SPEC-019

## Decision

Recursive improvement will operate as a shadow laboratory that proposes bounded artifact and process changes against a pinned production epoch. It cannot edit production, its evaluator, hidden tasks, promotion logic, authority, budgets, or editable-surface registry. A separate human-governance loop handles constitutional and evaluator changes. The initial search policy is failure-driven, archive-aware bounded heuristic search, compared with human and best-of-N baselines. Reinforcement learning is deferred.

## Context and current repository touchpoints

The repository already has skill comparison rubrics, deterministic health checks, router results, effectiveness scaffolding, adversarial fixtures, research runs, and a self-improvement-loops skill. The missing layer is a controlled experiment protocol that treats prompts, skills, context procedures, workflows, and harness code as candidates while retaining raw traces and evaluator independence.

## Goals

- Improve measurable capabilities without in-place self-editing.
- Identify causal failure mechanisms and the lowest effective intervention surface.
- Compare search methods, not only final candidates.
- Preserve passing behaviors, negative results, exploits, cost, and complexity.
- Support organization-change experiments with crash and recovery evidence.

## Non-goals

- An unconstrained self-modifying agent.
- Optimizing model weights.
- Letting the search controller decide what success means.

## Invariants

1. Production is pinned for the duration of a search.
2. Search and evaluation credentials, data, and workspaces are separate.
3. Constitution, hidden evaluations, scoring and result binding, promotion logic, raw human events, credential enforcement, and editable-surface policy are locked.
4. Each candidate declares one primary rung and causal hypothesis.
5. Candidate content freezes before evaluation.
6. Full development traces are retained and selectively retrieved; hidden traces are isolated.
7. A winner still needs independent attestation, an agent-opened PR, and human merge.
8. Search cannot begin for promotion-eligible work until the proposer capability floor, target-surface coverage, hidden calibration, execution environment, and equal-budget control gates pass.

## Interfaces and data

The editable-surface ladder is:

0. source query, retrieval, and context selection;
1. itemized playbook entry;
2. prompt, skill prose, and examples;
3. context-producing procedure or skill script;
4. workflow, role topology, retry, and tool policy;
5. harness and runtime-adapter code;
6. optimizer or search policy;
7. model weights, reserved for SPEC-026.

`SearchExperiment` freezes production epoch, evaluation epoch, development and hidden boundaries, target failures, preservation set, allowed rung and paths, proposer population, parent-selection rule, mutation operators, duplicate threshold, trial and cost budgets, stop conditions, and required baselines. It references a passing proposer and executor capability-floor report, SPEC-016 target-surface coverage report, hidden evaluator calibration, SPEC-014 environment attestation, and preregistered practical-effect, hidden non-inferiority, integrity, cost, and transfer gates.

Failure signatures record verifier outcome, causal status, reusable mechanism, recurrence, trace evidence, allowed addressable surfaces, and passing-behavior preservation set. Candidate proposals declare exact diff, hypothesis, expected effect, risks, and rollback.

Search starts with targeted one-surface proposals, mechanism diversity, archive-aware parent selection, trivial-diff rejection, Pareto selection, and fixed budgets. A contextual bandit may allocate trials only after enough unbiased history exists.

## State and failure behavior

Experiments move `designed -> entry_gates_verified -> preregistered -> independently_reviewed -> sealed -> searching -> evaluating -> analyzed -> candidate_selected|no_improvement|invalidated -> closed`. Experiments without all entry gates may run only as explicitly labeled method-development studies and cannot create promotion-eligible candidates. Integrity violation stops the search and retains all artifacts. Budget exhaustion closes normally. A production change during search does not rebase candidates; it closes or bridges the experiment.

## Implementation sequence

1. Add locked/editable registry and verify SPEC-014 environment and capability enforcement.
2. Implement failure mining and one-rung candidate generation for skill and context changes.
3. Add bounded search controller over the candidate archive.
4. Compare against human revision and equal-budget best-of-N baselines.
5. Add organization-change runs and higher rungs only after lower-rung plateaus.

## Migration and rollback

No production migration is required. Initial trials reproduce historical skill revisions in a sandbox. Disabling the lab cancels shadow work and leaves production unchanged. Candidate branches are disposable; archive records are not.

## Observability

Measure search success rate, trials to first useful candidate, improvement and non-inferiority, Pareto hypervolume, diversity, duplicate rate, exploit rate, trace retrieval use, cost, latency, candidate size, human review burden, and transfer.

## Verification

- A candidate attempting to edit hidden tests or promotion code is blocked and recorded.
- Shadow execution cannot change production files or pointer.
- Re-running a sealed experiment reproduces its plan and analysis.
- Equal-budget baselines are present.
- Capability floor, target-surface effectiveness coverage, hidden calibration, and transfer gates are sealed before search.
- Representative shadow execution beats or provides a preregistered useful Pareto trade against the simple and human controls without a critical regression.
- Removing raw traces reduces or does not improve search quality in an ablation.
- A production change mid-search triggers close or bridge, not silent rebase.

## Acceptance criteria

- [ ] Production, shadow, and human-governance loops are separate in identity and state.
- [ ] Locked surfaces are enforced outside model prompts.
- [ ] Search protocol is preregistered and budgeted.
- [ ] Raw trace, candidate, evaluation, and decision lineage is complete.
- [ ] Human and best-of-N baselines exist.
- [ ] No candidate can promote itself.
- [ ] Promotion-eligible searches pass capability-floor, coverage, hidden, environment, equal-budget, integrity, cost, and transfer entry gates.
- [ ] A selected candidate has representative shadow evidence, not only development-set gain.

## Pull-request evidence

Attach sealed experiment example, locked-surface attack tests, sandbox isolation proof, equal-budget baseline comparison, raw-trace ablation, and complete no-improvement or winning-candidate trace.
