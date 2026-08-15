# SPEC-021: Adaptive Harness Routing and Cross-Model Transfer

Status: draft
Revision: 1
Revises: none
Wave: 4
Classification: split
Owners: harness routing scientist agent; evaluation designer agent
Depends on: SPEC-008, SPEC-012, SPEC-016, SPEC-017, SPEC-019, SPEC-020

## Decision

The organization may maintain a small common harness plus the minimum justified scoped variants and a versioned router only when preregistered evidence shows that the accepted single harness causes material interference. The conservative base is always valid and remains the default. Routing uses an allowlist of immutable features observable before dispatch and is evaluated against the best simple single-harness baseline under equal reservations. Variants are narrowly scoped, carry an explicit maintenance and context cost, and are retired when they no longer provide a preregistered Pareto benefit.

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
2. The router cannot see hidden task identity, split membership, labels, or proxies derived from them; its allowlisted features are independently shown to exist before ordinary production dispatch.
3. Every variant has a common-base commit, declared scope, compatibility record, size, owner, and retirement test.
4. Fallback is explicit and measured; silent model or harness substitution is forbidden.
5. Router, variant, context compiler, and model versions bind each result.
6. A routed system must beat or provide a justified Pareto trade against the best simple baseline.
7. Production routing requires hidden non-inferiority, transfer-scope evidence, representative shadow decisions, exact-SHA attestation, and human merge.
8. Unknown, missing, stale, out-of-distribution, unaffordable, or policy-incompatible features select the conservative base; the router never guesses or silently substitutes.
9. Route features exclude hidden identity, outcome-derived values, model self-predictions made after dispatch, private feedback outside its confirmed scope, and raw source content not required by the schema.
10. Route and recursive-subcall budgets are reserved before dispatch. A route cannot begin when its worst-case calls, tokens, money, latency, or external operations do not fit the remaining reservation.
11. Production routing is immutable within an accepted router epoch. Online learning, production exploration, and automatic bandit updates are out of scope.
12. A causal regret or off-policy claim requires known nonzero behavior propensities or exhaustive counterfactual shadow outcomes over the claimed action support. Deterministic chosen-action logs alone support only descriptive replay.

## Interfaces and data

`HarnessVariant` records common base, diff digest, changed surfaces, intended scope, compatible models and executors, required capabilities, evidence, cost and size deltas, known breakages, and retirement criteria.

`RouteRequest` includes role, task type, source class, domain, context size and structure, required tools, model and executor, latency and cost class, policy constraints, compatibility epoch, and available reservation. Each field has a declared pre-dispatch producer, freshness rule, missing-value behavior, and classification. `RouteDecision` records eligible variants, deterministic scores or rule matches, chosen variant, conservative fallback, router version, feature digest, reservation decision, and explanation codes.

Accepted variant and router definitions are public. Live route requests, per-installation decisions, private policy inputs, reservations, and deployment health remain private operational records. Public route reports use allowlisted aggregates with new identities and cannot reveal private task, model, source, feedback, or hidden-evaluation membership.

The initial router is a deterministic rule set; a calibrated classifier is considered only after the rule baseline and feature audit expose a measured limitation. Any bandit allocation remains offline or shadow-only and frozen during an experiment; production exploration or online updates require a future human-merged specification amendment. RLM conditions are `direct`, `externalized_depth_0`, and `recursive_depth_1`, each with separately reserved maximum subcalls, tokens, cost, latency, and output guards.

Every offline policy estimate binds the behavior-policy identity, action set, known propensities or exhaustive shadow outcome matrix, overlap and positivity diagnostics, effective sample size, clipping or truncation rule, estimator, uncertainty method, and unsupported regions. If any candidate action has zero or unknown support in a claimed scope, the report labels the comparison descriptive and cannot claim causal regret, improvement, or policy value. Randomization remains shadow-only under a sealed evaluation.

## State and failure behavior

Variants move `proposed -> evaluated -> shadow_available -> independently_attested -> merge_pending -> accepted_scope`. `merge_pending` requires a current SPEC-019 attestation; only a verified human merge and its `PromotionRecord` can create `accepted_scope`. SPEC-021 owns no deployment transition. After SPEC-025 is active, a separately registered read-only `RouteBindingView` may show `inactive|canary|active|degraded|rollback_pending|retired` only by joining accepted router scope with exact SPEC-025 activation and deployment events; it is not part of revision-1 acceptance, and its reducer cannot activate, degrade, roll back, or retire deployment state. A route incompatibility or reservation denial falls back only to a declared compatible base when that base is authorized and budget-feasible, and emits an event; otherwise dispatch is visibly blocked. Router updates are candidates under SPEC-020 and affect production only through SPEC-019 full-tree attestation, human merge, and later SPEC-025 activation.

## Implementation sequence

1. Build compatibility records and a single-harness control.
2. Run the base-only router in shadow and measure predeclared interference, fallback, and feature-quality criteria.
3. Create one narrowly scoped variant only if that evidence crosses the preregistered practical threshold; otherwise close with no variant.
4. Evaluate deterministic route decisions, transfer, interference, fallback, and complexity across model families.
5. Add another variant or contextual allocation only when each addition has independent evidence and route history supports an unbiased offline evaluation.

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
- Concurrent route and recursive-call reservations cannot overspend, including after restart or fallback.
- Hidden non-inferiority and representative shadow-routing fixtures meet preregistered gates before attestation.
- A route with aggregate gain but a critical scoped regression cannot become production-scoped.
- Retiring a variant leaves historical decisions reproducible.
- Production observations cannot update router weights, rules, features, or exploration probabilities without a new frozen candidate and human-merged epoch.
- Deterministic production logs with zero support for unchosen variants are rejected for causal off-policy or regret claims; descriptive replay remains permitted.

## Acceptance criteria

- [ ] Production-observable route schema and explanation codes exist.
- [ ] Every variant has compatibility, maintenance, and retirement metadata.
- [ ] Single-harness and direct-inference baselines remain available.
- [ ] Cross-model transfer and interference are reported per scope.
- [ ] No hidden or outcome-derived feature reaches routing.
- [ ] Missing, stale, incompatible, out-of-distribution, and unaffordable requests conservatively fall back or block with a typed reason.
- [ ] Recursive depth greater than one remains experiment-only.
- [ ] The routed system demonstrates a preregistered useful Pareto benefit against the best simple baseline with no critical regression.
- [ ] Hidden, transfer, and representative shadow-routing gates pass before an exact-SHA human-merged production scope exists.
- [ ] The accepted router definition, scoped decision, and replay are frozen and non-exploratory. This specification claims no production dispatch evidence; any later production route must additionally bind an exact SPEC-025 activation, mode, and reservation policy.

## Pull-request evidence

Attach route-feature audit, base-only shadow report, any justified scoped-variant evaluation, fallback tests, equal-budget baseline, cross-model matrix, and one synthetic retirement simulation. A no-variant conclusion is a valid outcome.
