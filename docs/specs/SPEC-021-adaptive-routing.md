# SPEC-021: Adaptive Harness Routing and Cross-Model Transfer

Status: draft
Wave: 4
Classification: public
Owners: harness routing scientist agent; evaluation designer agent
Depends on: SPEC-020

## Decision

The organization may maintain a small common harness plus scoped variants and a versioned router when evidence shows that one expanding universal harness causes interference. Routing uses only features observable at real dispatch time and is evaluated against a single-harness baseline. Variants are model-, executor-, domain-, source-, or complexity-scoped, carry maintenance cost, and are retired when they no longer provide a Pareto benefit.

## Context and current repository touchpoints

The repository already measures skill routing and confusion across model families. Two engineering hypotheses motivate this specification: repeatedly adding behavior to one dense harness may create measurable cross-task interference, and deeper recursive inference may have diminishing or negative returns. Neither is assumed true for this repository. Variant routing activates only if preregistered comparisons against the single-harness and shallower-depth baselines demonstrate a practical benefit.

## Goals

- Specialize context, skills, workflows, and harnesses without uncontrolled growth.
- Measure transfer and interference across model families and executors.
- Route direct, externalized depth-0, and recursive depth-1 inference conditions.
- Keep dispatch explainable and reproducible.

## Non-goals

- A model choosing arbitrary code at runtime.
- Routing from hidden benchmark labels or post-outcome information.
- Enabling recursive depth greater than one by default.

## Invariants

1. Route features exist before execution and are recorded.
2. The router cannot see hidden task identity beyond production-observable features.
3. Every variant has a common-base commit, declared scope, compatibility record, size, owner, and retirement test.
4. Fallback is explicit and measured; silent model or harness substitution is forbidden.
5. Router, variant, context compiler, and model versions bind each result.
6. A routed system must beat or provide a justified Pareto trade against the best simple baseline.
7. Production routing requires hidden non-inferiority, transfer-scope evidence, representative shadow decisions, exact-SHA attestation, and human merge.

## Interfaces and data

`HarnessVariant` records common base, diff digest, changed surfaces, intended scope, compatible models and executors, required capabilities, evidence, cost and size deltas, known breakages, and retirement criteria.

`RouteRequest` includes role, task type, source class, domain, context size and structure, required tools, model and executor, latency and cost class, and policy constraints. `RouteDecision` records candidate variants, scores or rule matches, chosen variant, fallback, router version, feature digest, and explanation codes.

Initial router is a deterministic rule or calibrated classifier trained only on development data. Bandit allocation is shadow-only until counterfactual evaluation and exploration budgets exist. RLM conditions are `direct`, `externalized_depth_0`, and `recursive_depth_1`, each with maximum subcalls, tokens, cost, latency, and output guards.

## State and failure behavior

Variants move `proposed -> evaluated -> shadow_available -> attested -> accepted_scope`, then a private deployment may move `inactive -> canary -> active`; later states are `degraded`, `deprecated`, and `retired`. A route incompatibility falls back only to a declared compatible baseline and emits an event. Unknown features use the conservative base. Router updates are candidates under SPEC-020 and affect production only through SPEC-019 attestation and human merge.

## Implementation sequence

1. Build compatibility records and a single-harness control.
2. Create two evidence-backed variants from known divergent behavior.
3. Implement deterministic route decisions and fallback.
4. Evaluate transfer, interference, and complexity across model families.
5. Add contextual allocation only if route history supports an unbiased offline evaluation.

## Migration and rollback

Production initially routes everything to the current base. Shadow decisions are logged and scored before activation. Rollback pins the base and retains variant and route history.

## Observability

Track route distribution, fallback and incompatibility, per-route success, regret estimates, transfer effects, variant size, context competition, recursion use, cost and latency, and stale compatibility records.

## Verification

- Hidden fixture labels cannot influence route features.
- Unknown and incompatible requests choose the declared base.
- A variant improving one scope but harming another remains scoped.
- Depth-1 recursion cannot exceed call or cost guards.
- Router and universal-harness baselines use equal budgets.
- Hidden non-inferiority and representative shadow-routing fixtures meet preregistered gates before attestation.
- A route with aggregate gain but a critical scoped regression cannot become production-scoped.
- Retiring a variant leaves historical decisions reproducible.

## Acceptance criteria

- [ ] Production-observable route schema and explanation codes exist.
- [ ] Every variant has compatibility, maintenance, and retirement metadata.
- [ ] Single-harness and direct-inference baselines remain available.
- [ ] Cross-model transfer and interference are reported per scope.
- [ ] No hidden or outcome-derived feature reaches routing.
- [ ] Recursive depth greater than one remains experiment-only.
- [ ] The routed system demonstrates a preregistered useful Pareto benefit against the best simple baseline with no critical regression.
- [ ] Hidden, transfer, and representative shadow-routing gates pass before an exact-SHA human-merged production scope exists.

## Pull-request evidence

Attach route-feature audit, two scoped variant evaluations, fallback tests, equal-budget baseline, cross-model matrix, and one variant retirement simulation.
