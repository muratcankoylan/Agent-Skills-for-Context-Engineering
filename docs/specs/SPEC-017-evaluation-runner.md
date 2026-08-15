# SPEC-017: Multi-Model Evaluation Runner and Statistical Gates

Status: draft
Revision: 1
Revises: none
Wave: 3
Classification: split
Owners: evaluation runner agent; independent evaluator agent
Depends on: SPEC-003, SPEC-005, SPEC-008, SPEC-013, SPEC-014, SPEC-016

## Decision

Evaluation will use a provider-neutral run and result schema with the existing Cursor SDK as the only initially approved paid execution surface. Consequential comparisons are preregistered, paired at the declared experimental unit, repeated according to a power or sensitivity rationale, budget-reserved, resumable, and blinded where practical. Results are reported per analysis unit, task family, skill, model, and failure type. Deterministic outcomes take precedence over model judges. Aggregate improvement cannot offset a critical regression.

## Context and current repository touchpoints

`researcher/benchmarks/sdk-runner/` already implements bounded concurrency, resume by result scan, progress logging, format retry, privacy settings, and cost forecasts. Router reporting already demonstrates per-skill effect and confusion analysis. This spec generalizes those strengths and adds experiment manifests, result binding, statistical analysis, judge calibration, and negative controls.

## Goals

- Compare baseline, production, candidate, and controls under one sealed epoch.
- Produce raw, resumable results and a reproducible analysis artifact.
- Account for missingness, stochasticity, cost, context, latency, and tail failure.
- Support multiple model families without silently changing settings.

## Non-goals

- Running paid benchmarks without explicit cost bounds.
- Declaring significance from unpaired aggregate averages alone.
- Automatically selecting a new judge during an active epoch.

## Invariants

1. An `EvaluationObservation` binds a SPEC-003 frozen candidate digest, epoch, task, seed, replication, model, execution environment, runtime, context chain, harness, tools, and adapter. It does not bind a later PR SHA.
2. Replication count follows the sealed epoch's power or sensitivity rationale; fewer than three stochastic replications is preliminary, while three repetitions alone never establishes adequate power or independent sample size.
3. Shared tasks use paired comparisons at the preregistered unit; repeated seeds, turns, attempts, and calls within one task group do not create independent units.
4. Fixed seeds, invalid results, timeouts, repairs, and retries are retained.
5. Model judges are independent of authors; first-round judges are blind to each other.
6. Pairwise judge order is swapped and calibration against human examples is reported.
7. Paid loops require concurrency, resume, progress, and cost gates before execution.
8. The scheduler atomically reserves worst-case run and retry cost before dispatch; the runner cannot spend an unreserved amount or transfer a reservation between candidates, epochs, or identities.
9. Hidden tasks are materialized only inside the eligible evaluator environment. Candidate, search, author, and general runner contexts receive opaque run IDs and allowed aggregate decisions, not hidden bodies or task-level diagnostics.
10. The score-bearing evaluator and final decision issuer are independent of candidate authors and search controllers; judge identity alone does not satisfy independence if they share disallowed context or workspace state.

## Interfaces and data

`EvaluationPlan` expands an epoch and frozen candidates into atomic run records and binds the experimental unit, analysis unit, pairing key, grouping factors, multiplicity family, stopping rule, and maximum attempts. A valid candidate freeze receipt is required before planning. Runner commands include `plan`, `dry-run`, `reserve`, `execute`, `resume`, `reconcile`, `analyze`, and `publish-report`. Required cost gates are `--max-runs` and `--max-budget-usd`, with a worst-case retry-aware forecast and an accepted SPEC-008 reservation before any SDK call. Dispatch consumes the reservation atomically; cancellation and provider reconciliation release only verified unused capacity.

`EvaluationObservation` is the only score-bearing record. It contains candidate content digest, sealed epoch and task, exact attempt and environment identities, raw result references, metric vector, uncertainty, integrity and missingness status, usage, and evaluator identity. SPEC-019 later proves that a PR tree exactly materializes this candidate and creates a separate attestation.

The matrix considers no-skill or no-intervention baseline, accepted production, candidate, unrelated-change negative control, target plus related skills, and target plus unrelated skills when context competition matters. Conditions span held-in, held-out, adversarial, and distribution-shift tasks within the epoch.

Analysis reports paired effect estimates at the declared unit, cluster-aware bootstrap confidence intervals or a justified alternative, practical-effect and non-inferiority decisions, multiplicity handling, sensitivity to missing and invalid outcomes, per-task-family and per-model effects, confusion matrices where relevant, failure taxonomy, cost, latency, tokens, and Pareto position. It never treats repeated calls from one grouped fixture as independent evidence.

## State and failure behavior

Atomic runs move `planned -> reservation_pending -> reserved -> running -> completed|invalid|timeout|failed|cancelled|unknown`, with terminal `budget_blocked` before dispatch. Resume skips terminal results with valid digests. Format repair is a separately counted and budgeted attempt. Provider ambiguity reconciles by stored request ID when possible; otherwise it remains unknown and is never imputed as success. No adaptive stop or extra run is permitted outside the sealed stopping rule and remaining reservation.

## Implementation sequence

1. Wrap existing router and effectiveness runs in the new plan and result schemas.
2. Add digest binding, paired analysis, bootstrap intervals, and failure accounting.
3. Add blinded pairwise judge protocol and calibration fixtures.
4. Run deterministic goldens and a bounded no-cost or minimal-cost pilot.
5. Publish a bridge report comparing old and new runner outputs.

## Migration and rollback

Existing results are imported read-only with provenance and missing-field annotations. The existing commands remain callable until bridge parity passes. Rollback restores the previous runner and leaves new result records intact.

## Observability

Track progress per atomic run, call duration, stall age, retries, format failures, invalid and missing rates, budget reservation and actual cost, provider errors, judge disagreement, and estimated time and cost remaining.

## Verification

- Interrupted plans resume without duplicate paid calls for valid terminal results.
- Tampering with candidate or context digest invalidates score binding.
- An unfrozen candidate or a child revision cannot reuse its parent's observations.
- Synthetic paired data reproduces known statistical decisions.
- Negative control catches a biased evaluator fixture.
- Reversed pairwise order reveals order-biased judge fixtures.
- Worst-case retry forecast respects the budget gate.
- Concurrent plans cannot oversubscribe an organization or evaluator budget, and restart reconstructs the remaining reservation from durable receipts.
- Hidden-task fixtures remain absent from proposer-visible prompts, files, progress, errors, and task-level reports.
- Treating replications as independent task units fails the analysis validator.

## Acceptance criteria

- [ ] Existing required runner safeguards remain present.
- [ ] Analysis is reproducible from raw results and the sealed epoch.
- [ ] Reports include per-unit effects and uncertainty, not only aggregates.
- [ ] Missing, invalid, timeout, repair, and retry results are explicit.
- [ ] Judge calibration and disagreement are reported when judges are used.
- [ ] No paid run starts without explicit plan and cost gates.
- [ ] No paid run starts without a durable worst-case reservation, and all reservation consumption and release reconcile after restart.
- [ ] Score-bearing observations bind frozen candidate content and execution environment, never an assumed future PR SHA.
- [ ] Statistical units, pairing, multiplicity, stopping, exclusions, and missing-data policy match the sealed epoch exactly.
- [ ] Hidden execution and final score decisions remain independent of candidate and search identities and contexts.

## Pull-request evidence

Attach bridge report, synthetic-statistics tests, resume and tamper tests, negative-control result, judge calibration example, and dry-run budget forecast. No large paid run is required for spec acceptance.
