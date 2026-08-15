# SPEC-020: Meta-Harness Experiment Laboratory

Status: draft
Revision: 1
Revises: none
Wave: 4
Classification: split
Owners: meta-harness scientist agent; independent evaluator agent; human maintainer
Depends on: SPEC-005, SPEC-008, SPEC-014, SPEC-016, SPEC-017, SPEC-018, SPEC-019

## Decision

Recursive improvement will operate as a shadow-only laboratory that proposes bounded artifact and process changes against a pinned production epoch. Shadow results cannot apply state, open PRs, deliver messages, or change active routing; a separately authorized proposal work order may later materialize a selected frozen candidate. Search cannot edit production, its evaluator, hidden tasks, promotion logic, authority, budgets, or editable-surface registry. A separate human-governance loop handles constitutional and evaluator changes. The initial search policy is preregistered, failure-driven, archive-aware, one-rung-at-a-time bounded heuristic search compared with human and equal-budget best-of-N baselines. Reinforcement learning is deferred.

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
9. Hidden evaluation is a terminal independent gate, never a search oracle. Task-level hidden results, diagnostics, counts, and exploit details cannot return to the active search controller.
10. Every experiment seals maximum candidates, generations, attempts, concurrent work, model calls, tokens, money, wall time, external calls, and evaluator looks, and receives durable worst-case reservations before dispatch.
11. Adaptive mutation, parent selection, early stopping, and allocation use only preregistered development observations; changing the search rule closes or versions the experiment.
12. A search result, archive rank, or model consensus cannot select itself for proposal; an independent analysis reducer applies the sealed selection rule.
13. One sealed experiment may select at most one terminal candidate and create at most one proposal work order or PR. Additional candidates require a new experiment and multiplicity budget.
14. Search begins at the lowest editable-surface rung capable of addressing the failure. Starting higher requires a preregistered infeasibility or accepted cost argument, not model preference.
15. Candidate qualification and search-policy qualification are different estimands. One candidate may pass one untouched gate; an optimizer may not claim superiority or edit rung 6 from that result.

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

`SearchExperiment` freezes production epoch, public evaluation epoch, development boundary, opaque hidden-gate reference, target failures, statistical and selection units, preservation set, allowed single rung and paths, proposer population, parent-selection rule, mutation operators, duplicate threshold, maximum candidate family, generations, evaluator looks, trial and cost budgets, multiplicity handling, stop conditions, and required baselines. It references durable SPEC-008 reservations, a passing proposer and executor capability-floor report, a public SPEC-016 target-surface coverage decision, an opaque independent hidden-readiness receipt, SPEC-014 environment attestation, and preregistered practical-effect, hidden non-inferiority, integrity, cost, and transfer gates. It contains no hidden manifest identity, digest, count, membership, or calibration detail.

Failure signatures record verifier outcome, causal status, reusable mechanism, recurrence, trace evidence, allowed addressable surfaces, and passing-behavior preservation set. Candidate proposals declare exact diff, hypothesis, expected effect, risks, and rollback.

Each candidate follows `proposed -> content_frozen -> development_evaluated -> archived`. Every score-bearing plan and run binds the already frozen candidate bytes under SPEC-017 and SPEC-018; mutation creates a new candidate identity and multiplicity unit.

Search starts with targeted one-surface proposals, mechanism diversity, archive-aware parent selection, trivial-diff rejection, conservative Pareto selection, and fixed reserved budgets. Adaptive or bandit allocation remains shadow-only, cannot consume hidden outcomes, and requires a later preregistered experiment showing adequate unbiased logged support against the fixed policy. It never updates production online.

`SearchPolicyEvaluation` is a sealed outer benchmark over multiple independent failure-family blocks. Its experimental unit is the block, not a candidate or repeated model call. It preregisters block sampling, assignment, equal information exposure, model-call/compute/token/money budgets, declared human-review and authoring time, censoring, timeout and missingness handling, multiplicity, and the inference used for policy-level claims. Human revision, fixed-policy best-of-N, and the tested optimizer receive comparable inputs and accounting. A useful candidate from one block may proceed independently, but rung-6 edits or claims that the optimizer is better require the outer benchmark's practical-effect and non-inferiority gates across the preregistered blocks.

## State and failure behavior

Experiments move `designed -> entry_gates_verified -> budget_reserved -> preregistered -> independently_reviewed -> sealed -> searching -> development_evaluated -> terminal_selection_frozen -> hidden_gate_requested -> analyzed -> candidate_selected|no_improvement|invalidated -> closed`. Search and development evaluation operate only on individually frozen candidates. The sealed selection rule then closes over development evidence and freezes the identity of exactly one already immutable terminal candidate before hidden dispatch. Hidden output can confirm or reject that selected candidate but cannot choose among candidates, change its bytes, reopen search, or steer another attempt in the same experiment. Experiments without all entry gates may run only as explicitly labeled method-development studies and cannot create promotion-eligible candidates. Integrity violation stops the search and retains all artifacts. Budget exhaustion closes incomplete and cannot select an unevaluated winner. A hidden-gate failure closes the search without returning task-level feedback. A production change during search does not rebase candidates; it closes or uses a preregistered bridge.

## Implementation sequence

1. Add locked/editable registry and verify SPEC-014 environment and capability enforcement.
2. Implement failure mining and one-rung candidate generation for skill and context changes.
3. Add bounded search controller over the candidate archive.
4. Compare against human revision and equal-budget best-of-N baselines.
5. Add organization-change runs and higher rungs only after lower-rung plateaus.

## Migration and rollback

No production migration is required. Initial trials reproduce historical skill revisions in a sandbox. Disabling the lab cancels shadow work and leaves production unchanged. Candidate branches are disposable; archive records are not.

## Observability

Measure search success rate, trials to first useful candidate, improvement and non-inferiority by preregistered dimension, diversity, duplicate rate, exploit rate, trace retrieval use, cost, latency, candidate size, human review burden, and transfer. The first implementation reports the complete outcome vector and does not collapse it into a hypervolume objective.

## Verification

- A candidate attempting to edit hidden tests or promotion code is blocked and recorded.
- Shadow execution cannot change production files or pointer.
- Shadow execution may materialize isolated private analysis projections, but no shadow reducer result can enter an authoritative or production projection, open or update a PR, enqueue a delivery, or alter active routing.
- Re-running a sealed experiment reproduces its plan and analysis.
- Equal-budget baselines are present.
- Capability floor, target-surface effectiveness coverage, hidden calibration, and transfer gates are sealed before search.
- A selected candidate has representative shadow evidence against its controls without a critical regression; this qualifies only that candidate.
- Search-policy qualification uses a sealed multi-block outer benchmark with equal information, compute, model-call, cost, and declared human-time accounting, plus preregistered censoring, missingness, and multiplicity.
- Removing raw traces reduces or does not improve search quality in an ablation.
- A production change mid-search triggers close or bridge, not silent rebase.
- Repeated hidden queries, search adaptation from hidden outcomes, and unreserved candidate fan-out are denied.
- Concurrent search attempts cannot oversubscribe any sealed budget, and restart reconciles reservations before new dispatch.

## Acceptance criteria

- [ ] Production, shadow, and human-governance loops are separate in identity and state.
- [ ] Locked surfaces are enforced outside model prompts.
- [ ] Search protocol is preregistered and budgeted.
- [ ] Search-space size, statistical and selection units, adaptive rules, stopping, multiplicity, evaluator looks, and worst-case reservations are sealed before search.
- [ ] Raw trace, candidate, evaluation, and decision lineage is complete.
- [ ] Human and best-of-N baselines exist.
- [ ] No candidate can promote itself.
- [ ] Promotion-eligible searches pass capability-floor, coverage, hidden, environment, equal-budget, integrity, cost, and transfer entry gates.
- [ ] A selected candidate has representative shadow evidence, not only development-set gain, while optimizer-level claims require the separate outer method evaluation.
- [ ] Hidden evaluation is independent and terminal: it can reject a candidate but cannot steer the same search.

## Pull-request evidence

Attach sealed experiment example, locked-surface attack tests, sandbox isolation proof, equal-budget baseline comparison, raw-trace ablation, and complete no-improvement or winning-candidate trace.
