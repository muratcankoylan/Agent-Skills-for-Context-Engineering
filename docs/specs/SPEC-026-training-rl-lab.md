# SPEC-026: Future Training and Reinforcement-Learning Laboratory

Status: draft
Activation: deferred
Wave: 6
Classification: split
Owners: training research lead; independent evaluator; human maintainer
Depends on: SPEC-022, SPEC-025

## Decision

Weight-level learning is a separate future laboratory, not the first form of recursive improvement. It may begin only after artifact-level search has produced a stable, provenance-complete experience archive, repeated failure mechanisms, sealed hidden evaluations, and evidence that prompt, context, skill, workflow, routing, and harness interventions have plateaued. Training runs require explicit human authorization. A trained checkpoint is an immutable candidate and reaches production only through independent evaluation, a configuration PR, and human merge.

## Context and current repository touchpoints

The repository's highest-value near-term work is broader effectiveness evaluation and bounded harness improvement. Current evidence does not justify training costs or a reward function. The earlier specs create the dataset needed to decide later: typed work orders, context packages, tool receipts, failure signatures, candidate lineage, human decisions, cross-model results, and protected evaluation splits.

Prime Intellect or another training platform may later provide an execution adapter. No provider defines the dataset, reward, authority, or promotion protocol. Provider selection requires an ADR covering interface, reproducibility, data handling, model license, checkpoint portability, cost, and exit path.

## Goals

- Convert audited organizational experience into governed offline datasets.
- Test whether learning in weights adds value beyond inference-time harness improvements.
- Prevent reward hacking, hidden-test training, evaluation contamination, and irreversible deployment.
- Preserve reproducible training and checkpoint lineage.

## Non-goals

- Online self-updating production weights.
- Training on unfiltered transcripts or private data by default.
- Using one proxy reward as the organization's objective.
- Beginning training to compensate for weak evaluation coverage.

## Entry gates

All gates are required:

1. Stages 0-5 have sufficient coverage for the targeted behavior and Stage 6 can evaluate the training search itself.
2. Dataset completeness, independence, contamination, licensing, and statistical-power reports pass human review.
3. The same failure mechanisms recur across independent tasks, epochs, and at least two execution configurations.
4. Lower-rung interventions have a documented plateau or unacceptable inference-time cost.
5. Verifiable outcomes or calibrated human preferences exist; no reward depends solely on an uncalibrated model judge.
6. A base model's license permits the intended training and redistribution.
7. Compute, provider, privacy, checkpoint, and rollback budgets are approved.
8. The human maintainer authorizes a sealed training experiment.

No fixed trajectory count substitutes for the power and coverage report.

## Invariants

1. Hidden evaluation data and current-epoch attacks never enter training.
2. Raw chain-of-thought is not required as a training target; retain observable task state, actions, tool receipts, artifacts, and outcomes.
3. Dataset, code, base checkpoint, hyperparameters, environment, reward components, and random seeds are versioned and hashed.
4. Reward is multi-dimensional with hard integrity constraints; one aggregate reward cannot offset a critical violation.
5. Checkpoints never overwrite a base or production model.
6. Training identity cannot publish or change the production route.
7. Comparisons include equal-budget inference-time and artifact-level alternatives.

## Interfaces and data

`TrainingExample` records source work-order and trace IDs, observable state and context package, permitted action or artifact delta, tool receipts, verifier outcomes, human or evaluator decisions, failure signature, outcome vector, cost, policy and epoch, classification, license, and redaction transform. Preference examples bind exact candidate pairs, presentation order, rubric dimensions, annotator or calibrated judge, and disagreement.

`TrainingExperiment` freezes dataset manifest and splits, base model digest, method, code and environment, hyperparameters, reward specification, integrity constraints, seeds, compute and cost budget, checkpoints, evaluation epochs, lower-rung baselines, stop rules, and publication policy.

Methods advance cautiously:

1. supervised fine-tuning on reviewed structured outputs or tool policies;
2. preference optimization on calibrated pairwise decisions;
3. offline or sandbox reinforcement learning only for tasks with execution-grounded rewards;
4. online learning remains out of scope until separately specified.

`TrainingProviderAdapter` implements capability discovery, dataset staging by digest, start, status, checkpoint receipt, cancel, collect, cost receipt, and deletion or retention attestation. Checkpoint packaging uses an open or documented format when the model license permits it.

## State and failure behavior

Experiments move `proposed -> data_audited -> preregistered -> human_authorized -> training -> checkpointed -> independently_evaluated -> rejected|parked|pr_eligible -> closed`. Data or reward integrity failure stops the run. Provider ambiguity enters reconciliation. Budget exhaustion retains the latest valid checkpoint but does not make it eligible.

## Implementation sequence

1. Build read-only dataset exporter and contamination/license audit.
2. Publish a dataset card and reproduce an artifact-level baseline.
3. Run a small supervised pilot on a non-production model under a hard budget.
4. Compare checkpoint, base plus best harness, and base plus equal inference budget.
5. Consider preference or RL methods only when the pilot reveals a specific residual failure.

## Migration and rollback

No production migration occurs during laboratory stages. Deployment adds a checkpoint only through a human-merged routing or model manifest. Rollback pins the prior model and harness, and retains the checkpoint as a rejected or superseded candidate.

## Observability

Track dataset composition and exclusions, contamination signals, training and validation curves, reward components, integrity violations, compute and cost, checkpoint drift, held-in and held-out effects, worst-model and worst-task effects, inference cost, transfer, and post-deployment regression.

## Verification

- Seeded hidden examples are detected and excluded.
- Dataset export can be reproduced from allowed archive records and transforms.
- Reward-hacking fixtures score poorly on hard integrity dimensions.
- Cancelling a provider run retains reconciled receipts and immutable checkpoints.
- The checkpoint is compared with lower-rung equal-budget alternatives.
- Training credentials cannot alter production routing or publish a release.

## Acceptance criteria

- [ ] Every entry gate has evidence and human approval.
- [ ] Dataset and model licensing support the intended use.
- [ ] Hidden-test and private-data boundaries are tested.
- [ ] Training is reproducible from a sealed manifest.
- [ ] Independent evaluation uses untouched epochs and meaningful baselines.
- [ ] Deployment and rollback require a normal PR and human merge.

## Pull-request evidence

Attach entry-gate dossier, dataset card and audit, provider ADR and conformance report, sealed experiment, cost authorization, independent evaluation, checkpoint lineage, and rollback demonstration.
