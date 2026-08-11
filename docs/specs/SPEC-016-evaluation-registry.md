# SPEC-016: Evaluation Registry, Rubric Epochs, and Fixtures

Status: draft
Wave: 3
Classification: split
Owners: evaluation designer agent; human maintainer
Depends on: SPEC-011, SPEC-012

## Decision

Every evaluation will run under an immutable epoch that freezes task and split hashes, rubric and scorer versions, models and settings, context compiler, harness, tools, adapters, seeds, replications, budgets, practical-effect thresholds, and non-inferiority margins. Public development fixtures and private hidden fixtures have separate authorities and storage. Changing any causal evaluation component creates a new epoch; cross-epoch claims require a bridge run.

## Context and current repository touchpoints

The benchmark program already defines Stages 0 through 4, strict deterministic validators, a mature router benchmark, staged effectiveness and composition work, published results, and a Cursor SDK runner. Stage 3 effectiveness coverage is the main methodological bottleneck: one effectiveness task cannot justify autonomous skill evolution.

## Goals

- Register what each evaluation measures and what decision it can support.
- Prevent data leakage and evaluator drift during candidate search.
- Expand effectiveness, composition, harness, and meta-harness coverage methodically.
- Preserve reproducibility across models, runtimes, and time.

## Non-goals

- One leaderboard score for the organization.
- Generating hidden tests from the candidate's own failures during the same search.
- Replacing task execution with model judgment when deterministic outcomes exist.

## Invariants

1. The optimizer cannot read or edit hidden fixtures, scoring code, score binding, or promotion thresholds.
2. Every task states construct, unit of analysis, oracle, failure taxonomy, contamination risks, and applicability scope.
3. Dataset splits are grouped to prevent near-duplicate, source-family, or template leakage.
4. A candidate's development failures can enter a future epoch only after the current search closes.
5. Thresholds are preregistered in the epoch, not selected after results.
6. Invalid, missing, timeout, and format-failure outcomes remain visible.
7. Candidate proposers and search controllers cannot seal, activate, reopen, or replace an evaluation epoch.
8. Task count is never accepted as a substitute for target-surface construct and coverage evidence.

## Interfaces and data

Create `researcher/evaluations/registry.yaml`, `epochs/`, `tasks/`, `datasets/`, `rubrics/`, and private hidden-manifest counterparts. `EvaluationTask` includes stage, mechanism, real-world objective, input and output schema, oracle, metrics, fixtures, split group, negative controls, adversarial variants, budget, and minimum useful decision.

Stages are:

- 0: format, schema, platform, repository, and run integrity;
- 1: per-skill health, consistency, provenance, and activation coverage;
- 2: routing and confusion across model families;
- 3: loaded-skill effectiveness on task outcomes;
- 4: composition, order, interference, and context competition;
- 5: harness, context, recovery, cost, and long-horizon behavior;
- 6: meta-harness search, transfer, reward-hacking resistance, and longitudinal performance.

An epoch manifest freezes all evaluation inputs and defines target metrics, critical dimensions, practical-effect and non-inferiority gates, replications, comparison method, missing-data policy, and cost ceiling.

Public task, rubric, scorer, and epoch artifacts become active through a human-merged PR. A private hidden-manifest authority is held by an independent evaluator identity and requires recorded human authorization before activation. Private activation and seal records bind the exact public commit and hidden-manifest digest. Their public projection has a new opaque public identity and exposes only the public epoch identity, lifecycle status, activation time, and public commit. It never exposes a private input digest or a value derived from one. The proposer namespace has no method or credential for sealing or activation.

A `CoverageReport` maps each target surface and claimed scope to real task constructs, activation and non-activation cases, negative controls, failure modes, model and executor families, held-in development coverage, calibrated hidden coverage, non-inferiority sensitivity, and unresolved gaps. Autonomous PR eligibility requires a passing coverage report for the particular surface and claim. Merely adding several tasks, passing routing, or reaching an aggregate sample count is insufficient.

## State and failure behavior

Tasks move `proposed -> construct_reviewed -> fixture_reviewed -> calibrated -> active -> deprecated`. Epochs move `draft -> independently_reviewed -> human_authorized -> sealed -> active -> closed`. Once sealed, an epoch is immutable. Leakage suspicion closes the affected split, invalidates related claims, and creates an incident plus replacement epoch.

## Implementation sequence

1. Register current Stage 0-3 fixtures and published router epochs without altering results.
2. Define split grouping, hidden-store interface, and leakage checks.
3. Build target-surface Stage 3 tasks and coverage reports across distinct mechanisms before autonomous change; prioritize quality and decision power over task count.
4. Add Stage 4 composition and Stage 5 context/harness fixtures.
5. Add Stage 6 only with the meta-harness lab.

## Migration and rollback

Existing dated reports become closed epoch records with documented missing fields. Existing result files remain immutable. Rollback retains the registry in read-only mode and runs the current benchmark commands.

## Observability

Report coverage by skill, mechanism, stage, task family, model, runtime, and failure type; split similarity; invalid-result rate; judge calibration; epoch age; and decisions blocked by insufficient coverage.

## Verification

- Hash changes create a new epoch.
- Near-duplicate fixture groups cannot cross splits.
- Candidate roles cannot read hidden manifests.
- Candidate and search identities cannot seal or activate epochs.
- An epoch without independent review, human authorization, and bound public and private digests cannot run hidden evaluation.
- A bridge run quantifies an intentional model or scorer change.
- Registered historical router reports resolve to exact inputs.
- An effectiveness task can fail despite successful routing.

## Acceptance criteria

- [ ] Current benchmarks and validators are represented without losing provenance.
- [ ] Hidden and development data have distinct access paths.
- [ ] Epochs freeze thresholds and all causal runtime components.
- [ ] Stage 3 expansion has reviewed constructs, calibrated tasks, negative cases, and decision power for each initially enabled target surface.
- [ ] Leakage response and bridge-run procedures are executable.
- [ ] Coverage gaps are visible as blockers, not ignored.
- [ ] Every autonomously proposed change class has a passing target-surface coverage report, not only a task count.

## Pull-request evidence

Attach registry import report, epoch examples, split-leakage fixtures, one bridge-run dry run, coverage matrix, and prioritized Stage 3 task designs.
