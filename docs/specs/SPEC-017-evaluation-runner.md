# SPEC-017: Multi-Model Evaluation Runner and Statistical Gates

Status: draft
Wave: 3
Classification: split
Owners: evaluation runner agent; independent evaluator agent
Depends on: SPEC-003, SPEC-014, SPEC-016

## Decision

Evaluation will use a provider-neutral run and result schema with the existing Cursor SDK as the only initially approved paid execution surface. Consequential comparisons are paired, repeated, budgeted, resumable, blinded where practical, and reported per task, skill, model, and failure type. Deterministic outcomes take precedence over model judges. Aggregate improvement cannot offset a critical regression.

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
2. Default minimum is three stochastic replications per condition unless the report says preliminary.
3. Shared tasks use paired comparisons.
4. Fixed seeds, invalid results, timeouts, repairs, and retries are retained.
5. Model judges are independent of authors; first-round judges are blind to each other.
6. Pairwise judge order is swapped and calibration against human examples is reported.
7. Paid loops require concurrency, resume, progress, and cost gates before execution.

## Interfaces and data

`EvaluationPlan` expands an epoch and frozen candidates into atomic run records. A valid candidate freeze receipt is required before planning. Runner commands include `plan`, `dry-run`, `execute`, `resume`, `reconcile`, `analyze`, and `publish-report`. Required cost gates are `--max-runs` and `--max-budget-usd`, with a dry-run cost forecast before any SDK call.

`EvaluationObservation` is the only score-bearing record. It contains candidate content digest, sealed epoch and task, exact attempt and environment identities, raw result references, metric vector, uncertainty, integrity and missingness status, usage, and evaluator identity. SPEC-019 later proves that a PR tree exactly materializes this candidate and creates a separate attestation.

The matrix considers no-skill or no-intervention baseline, accepted production, candidate, unrelated-change negative control, target plus related skills, and target plus unrelated skills when context competition matters. Conditions span held-in, held-out, adversarial, and distribution-shift tasks within the epoch.

Analysis reports paired effect estimates, bootstrap confidence intervals, Wilcoxon signed-rank or a justified alternative, practical-effect and non-inferiority decisions, per-task and per-model effects, confusion matrices where relevant, failure taxonomy, missingness, cost, latency, tokens, and Pareto position.

## State and failure behavior

Atomic runs move `planned -> reserved -> running -> completed|invalid|timeout|failed|cancelled|unknown`. Resume skips terminal results with valid digests. Format repair is a separately counted attempt. Provider ambiguity reconciles by stored request ID when possible; otherwise it remains unknown and is never imputed as success.

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

## Acceptance criteria

- [ ] Existing required runner safeguards remain present.
- [ ] Analysis is reproducible from raw results and the sealed epoch.
- [ ] Reports include per-unit effects and uncertainty, not only aggregates.
- [ ] Missing, invalid, timeout, repair, and retry results are explicit.
- [ ] Judge calibration and disagreement are reported when judges are used.
- [ ] No paid run starts without explicit plan and cost gates.
- [ ] Score-bearing observations bind frozen candidate content and execution environment, never an assumed future PR SHA.

## Pull-request evidence

Attach bridge report, synthetic-statistics tests, resume and tamper tests, negative-control result, judge calibration example, and dry-run budget forecast. No large paid run is required for spec acceptance.
