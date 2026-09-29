# SPEC-016: Evaluation Registry, Rubric Epochs, and Fixtures

Status: draft
Revision: 1
Revises: none
Wave: 3
Classification: split
Owners: evaluation designer agent; human maintainer
Depends on: SPEC-006, SPEC-011, SPEC-012, SPEC-013

## Decision

Every evaluation will run under an immutable preregistered epoch that freezes hypotheses, estimands, experimental and analysis units, task and split hashes, rubric and scorer versions, models and settings, context compiler, harness, tools, adapters, seeds, replications, stopping and missing-data rules, multiplicity family, budgets, practical-effect thresholds, and non-inferiority margins. Public development fixtures and private hidden fixtures have separate identities, authorities, storage, and execution paths. Changing any causal evaluation component creates a new epoch; cross-epoch claims require a preregistered bridge run.

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
9. Hidden task bodies, labels, membership, counts, selection logic, scorer diagnostics, and per-task results never enter proposer, optimizer, candidate-author, router-training, or first-round reviewer context.
10. Repeated attempts, seeds, turns, and model calls are measurements within their declared experimental unit, not independent samples unless the epoch justifies that claim.
11. Confirmatory hypotheses, analysis populations, exclusions, stopping rules, comparison families, effect thresholds, and missing-data handling are sealed before the first score-bearing run.
12. The identity that authors a candidate or controls its search cannot be the identity that activates the hidden epoch, materializes hidden tasks, or issues the final evaluation decision.
13. Calibration and confirmatory hidden examples are separate split identities. Any example used to tune a rubric, scorer, judge, threshold, or policy is calibration-only for that epoch and can never contribute a score-bearing confirmatory observation.
14. An evaluator-owned exposure ledger counts every hidden execution and every externally observable decision across all experiments. A new experiment ID cannot reset an epoch or related-lineage look budget.

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

An epoch manifest freezes all evaluation inputs and defines confirmatory and exploratory claims, estimands, experimental unit, analysis unit, grouping and blocking factors, target metrics, critical dimensions, practical-effect and non-inferiority gates, power or sensitivity rationale, replications, comparison and multiplicity method, exclusion and missing-data policy, stopping rule, maximum looks, and a reserved cost ceiling. Exploratory analyses are labeled and cannot silently become promotion gates.

Every dataset declares distinct `development`, `calibration`, and `confirmatory_hidden` split identities plus a group/source/template graph. The graph enforces disjointness across near duplicates, provenance families, and generator templates. Calibration output may establish reliability or tune a judge, but the calibrated examples and their groups are permanently excluded from confirmatory scoring in that epoch.

Before hidden materialization, an independent evaluator creates `ExposureFamilyAssignment`. It derives a private family identity from the candidate's ancestry closure, production root, targeted failure and surface set, mechanism/effect hypothesis, normalized changed-content evidence, and search lineage. Candidate authors and search controllers may supply evidence but cannot select the family key. Exact siblings and descendants join the same family; rename, whitespace, rerooting, new experiment IDs, and byte-distinct semantically equivalent changes do not create a fresh family. When equivalence is uncertain, the evaluator conservatively merges families or denies the look until independent review; it never grants a new hidden bit by default.

`HiddenExposureLedger` is a private evaluator-owned append-only record keyed by epoch, split, evaluator-assigned exposure family, production root, and search lineage closure. In one atomic decision it checks and increments execution looks and disclosure looks. A disclosure includes any allow/deny bit, public gate projection, no-resuggest consequence, timing class, or other result that can reach a proposer, archive query, router, or search controller. Once a disclosed result influences a family, the candidate and every related child, sibling experiment, rerooted candidate, or semantically equivalent search may not query that split again. Further adaptation requires a fresh untouched split or epoch; renaming the experiment or candidate does not reset exposure.

`EvaluationIndependencePlan` maps proposer, evaluation designer, epoch sealer, hidden runner, analyzer, release attestor, and human decision authority to distinct authenticated principals, attempts, capability sets, context profiles, workspaces, and prohibited information flows. Assigning different prompt roles inside one session or letting sibling subagents share ambient context does not establish independence. Consequential semantic judging uses a different model family or a calibrated multi-judge panel when feasible; when that is not feasible, the limitation and human calibration requirement are preregistered and the result cannot silently claim stronger independence.

Public task, rubric, scorer, and epoch artifacts become active through a human-merged PR. A private hidden-manifest authority is held by an independent evaluator identity and requires recorded human authorization before activation. Private activation and seal records bind the exact public commit and hidden-manifest digest. Hidden material is resolved directly into an eligible isolated evaluator environment through an opaque selection grant; it is not compiled into a proposer-visible `ContextPackage`, work-order body, error, log, progress count, or public report. Their public projection has a new opaque public identity and exposes only the public epoch identity, lifecycle status, activation time, and public commit. It never exposes a private input digest or a value derived from one. The proposer namespace has no method or credential for sealing, enumeration, materialization, or activation.

SPEC-016 owns a private-channel SPEC-006 command family with this canonical shape:

```text
/org authorize-hidden-epoch <epoch-id> --public-commit <full-sha> --private-manifest <opaque-id> --private-manifest-digest <sha256-digest> --expected-version <unsigned-integer> --independence-plan <plan-id> --max-execution-looks <unsigned-integer> --max-disclosure-looks <unsigned-integer> --max-budget-micros <unsigned-integer> --operation-key <opaque-id> --reason <bounded-text-to-end-of-line>
```

The command is accepted only from an authenticated human maintainer over the classified private operator ingress. Before this family can activate, the human-merged SPEC-000 revision 2 `AuthorityVocabularyRegistry` must register human `authorize_hidden_evaluation/evaluation_epoch` and the separate independent-sealer `seal_hidden_evaluation/evaluation_epoch`; no existing query, evaluator, or deployment authority is repurposed. `HiddenEpochAuthorizationRequest` binds the canonical intent, current accepted commit, expected epoch version, exact private manifest identity and digest, independence plan, split and look ceilings, budget ceiling, stable operation key, current constitution and policy decision, and the human principal. Its reducer may perform only `independently_reviewed -> human_authorized`. The distinct epoch-sealer principal then consumes that exact current authorization under `seal_hidden_evaluation/evaluation_epoch` and a narrower selection grant. One atomic reducer transition moves the epoch `human_authorized -> active` and writes its immutable activation seal and receipt; `sealed` is a record property, not an independently observable state. The sealer action cannot create human authorization, change any bound byte, widen a split/look/budget ceiling, reopen a closed epoch, or authorize itself. Exact command or sealer retry returns the first decision/receipt, while stale versions, another principal, changed bytes under the same key, or a wider manifest, split, look, or budget scope fail before materialization. Crashes after human authorization or the atomic activation-seal append reconcile by their separate operation keys and each apply once.

A private `CoverageReport` maps each target surface and claimed scope to real task constructs, activation and non-activation cases, negative controls, failure modes, model and executor families, held-in development coverage, independently calibrated hidden coverage, non-inferiority sensitivity, and unresolved gaps. Its public projection exposes only allowlisted development coverage and a new-identity hidden-readiness decision, never hidden counts, membership, digests, or gap details. Autonomous PR eligibility requires a passing coverage decision for the particular surface and claim. Merely adding several tasks, passing routing, or reaching an aggregate sample count is insufficient.

## State and failure behavior

Tasks move `proposed -> construct_reviewed -> fixture_reviewed -> calibration_only|confirmatory_ready -> active -> deprecated`. Epochs move `draft -> independently_reviewed -> human_authorized -> active -> closed`; entry to `active` atomically writes the immutable seal. Once active/sealed, an epoch is immutable. Leakage suspicion immediately prevents new hidden dispatch, closes the affected split, invalidates related claims and attestations, and creates an incident plus replacement epoch. A failed hidden result may reject the candidate, but its task-level details cannot feed the same search. Even an aggregate decision consumes the related-lineage exposure budget; learning from it requires a later development artifact and a fresh untouched epoch after the search closes.

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
- Candidate and search roles cannot infer hidden membership or outcomes through counts, timing, errors, selection receipts, logs, context exclusions, or repeated queries.
- Two sequential experiments cannot use the same candidate lineage to extract two decisions from one hidden split; the second atomic exposure request is denied.
- Sibling, new-root, rename-only, whitespace-only, and independently submitted semantic-equivalence fixtures converge to one evaluator-owned exposure family or conservatively deny another look.
- Calibration fixtures and every related group are absent from confirmatory score-bearing observations.
- Candidate and search identities cannot seal or activate epochs.
- Agent, search, evaluator, and runtime-operator identities cannot create hidden-epoch human authorization; stale, widened, or same-key/different-byte authorization commands fail, and crash retry applies once.
- Human authority cannot execute the sealer action, and the independent sealer cannot create or widen human authorization; wrong-action/principal, stale-authorization, altered-manifest, reopen, and crash-retry fixtures fail or converge exactly once.
- One session with several role prompts cannot satisfy the independence plan.
- An epoch without independent review, human authorization, and bound public and private digests cannot run hidden evaluation.
- A bridge run quantifies an intentional model or scorer change.
- Registered historical router reports resolve to exact inputs.
- An effectiveness task can fail despite successful routing.
- Clustered fixtures and repeated-run fixtures recover the declared analysis unit and reject pseudoreplication.
- Optional stopping, post-result exclusion, and unregistered multiple comparisons invalidate a confirmatory decision.

## Acceptance criteria

- [ ] Current benchmarks and validators are represented without losing provenance.
- [ ] Hidden and development data have distinct access paths.
- [ ] Epochs freeze thresholds and all causal runtime components.
- [ ] Epochs preregister hypotheses, estimands, statistical units, comparison families, stopping, exclusions, missingness, sensitivity, and budget before scoring.
- [ ] Stage 3 expansion has reviewed constructs, calibrated tasks, negative cases, and decision power for each initially enabled target surface.
- [ ] Leakage response and bridge-run procedures are executable.
- [ ] Coverage gaps are visible as blockers, not ignored.
- [ ] Every autonomously proposed change class has a passing target-surface coverage report, not only a task count.
- [ ] Hidden evaluation is materialized only for an independent evaluator and exposes no task-level side channel to the candidate or search loop.
- [ ] Every private hidden activation resolves to one current human authorization, exact manifest and public commit, bounded looks and budget, and a distinct authorized sealer.

## Pull-request evidence

Attach registry import report, epoch examples, split-leakage fixtures, one bridge-run dry run, coverage matrix, prioritized Stage 3 task designs, command-parser goldens, human/agent authorization negatives, sealer-principal/action and no-widen/no-reopen fixtures, stale/collision cases, and separate authorization/seal crash-retry receipts.
