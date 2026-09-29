# SPEC-026: Future Training and Reinforcement-Learning Laboratory

Status: draft
Revision: 1
Revises: none
Activation: deferred
Wave: 6
Classification: split
Owners: training research lead; independent evaluator; human maintainer
Depends on: SPEC-016, SPEC-017, SPEC-018, SPEC-019, SPEC-020, SPEC-022, SPEC-025

## Decision

Weight-level learning and distillation are a separate future laboratory, not the first form of recursive improvement. Revision 1 is a deferral contract: it implements only a machine-testable readiness dossier and deny-by-default validator. It installs no training SDK, credential, data uploader, provider job interface, or checkpoint deployment path. Moving `Activation` away from `deferred` requires a later human-merged specification revision after every entry gate passes. That later revision must seal dataset cutoff, statistical plan, bounded training search, evaluator looks, compute and provider budgets, stop rules, and publication policy before a provider receives data. Any eventual checkpoint remains an untrusted immutable candidate and could reach production only through independent evaluation, full-tree-attested configuration PR, human merge, canary activation, and event-replayable rollback.

## Context and current repository touchpoints

The repository's highest-value near-term work is broader effectiveness evaluation and bounded harness improvement. Current evidence does not justify training costs or a reward function. The earlier specs create the dataset needed to decide later: typed work orders, context packages, tool receipts, failure signatures, candidate lineage, human decisions, cross-model results, and protected evaluation splits.

Prime Intellect or another training platform may later provide an execution adapter. No provider defines the dataset, reward, authority, or promotion protocol. Provider selection requires an ADR covering interface, reproducibility, data handling, model license, checkpoint portability, cost, and exit path.

## Goals

- Produce a machine-testable readiness dossier and deny-by-default activation decision without creating a dataset.
- Determine whether evidence justifies proposing a later revision that would design governed datasets and test weight-level learning.
- Prevent reward hacking, hidden-test training, evaluation contamination, and irreversible deployment.
- Specify the provenance and lineage requirements a future activated revision must satisfy.

## Non-goals

- Online self-updating production weights.
- Training on unfiltered transcripts or private data by default.
- Using one proxy reward as the organization's objective.
- Beginning training to compensate for weak evaluation coverage.
- Installing or invoking a training provider while this revision is deferred.

## Entry gates

All gates are required:

1. Stages 0-5 have sufficient coverage for the targeted behavior and Stage 6 can evaluate the training search itself. A digest-bound simulation demonstrates at least 0.80 power for the preregistered minimum useful effect at the effective independent-group sample size under a sealed alpha, comparison family, multiplicity method, cluster correlation, attrition and missingness model, decision rule, and sensitivity range.
2. Source-corpus and dataset-feasibility reports cover prospective completeness, independence, contamination controls, licensing, consent, privacy, and statistical power and pass human review without materializing a training dataset.
3. The same residual failure mechanism recurs across at least three independent task families defined by the SPEC-016 group/source/template graph, two sealed evaluation epochs, and two materially distinct preregistered model or executor configurations.
4. Every applicable lower rung has a confirmatory experiment whose multiplicity-adjusted one-sided upper confidence bound is below the preregistered useful effect, or an accepted infeasibility/cost-ceiling record. A failed exploratory search is not a plateau.
5. Verifiable outcomes or calibrated human preferences exist; no reward depends solely on an uncalibrated model judge.
6. A base model's license permits the intended training and redistribution.
7. Compute, provider, privacy, checkpoint, and rollback budgets are approved.
8. The human maintainer authorizes proposing a digest-linked activation amendment for review. This is not authorization for an experiment, provider, export, or spend.
9. The prospective dataset plan defines a fixed future cutoff, grouping rules for related tasks and sources, train/evaluation leakage controls, and private-feedback scope, authorization, license, and retention requirements. Revision 1 validates the plan against existing archive metadata; it does not create or freeze dataset contents.
10. The training identity, provider, candidate author, search controller, and final evaluator are separated; the evaluator receives an untouched epoch and no persuasive trainer rationale.
11. A non-spendable capacity and cost-envelope dry run proves that worst-case compute, storage, checkpoint, evaluation, egress, and retry needs fit declared ceilings. Actual work orders and durable reservations are created only by a later activated experiment contract.

No fixed trajectory count substitutes for the power and coverage report.

## Invariants

1. Hidden evaluation data and current-epoch attacks never enter training.
2. Raw chain-of-thought is not required as a training target; retain observable task state, actions, tool receipts, artifacts, and outcomes.
3. Dataset, code, base checkpoint, hyperparameters, environment, reward components, and random seeds are versioned and hashed.
4. Reward is multi-dimensional with hard integrity constraints; one aggregate reward cannot offset a critical violation.
5. Checkpoints never overwrite a base or production model.
6. Training identity cannot publish or change the production route.
7. Comparisons include equal-budget inference-time and artifact-level alternatives.
8. Current and prior hidden task bodies, hidden membership, evaluator diagnostics, and current-epoch exploit traces never enter datasets, teacher prompts, reward models, distillation targets, or training-provider storage.
9. A hidden evaluation is a terminal independent decision for the sealed experiment. Failure cannot tune or resume that experiment; any lesson enters a later development dataset and epoch only after closure and review.
10. Training, teacher, reward-model, and provider outputs are untrusted data. They receive no credential, merge, publication, route-change, network, or production capability.
11. Online production learning, automatic checkpoint replacement, self-generated reward acceptance, and unbounded hyperparameter or checkpoint search remain prohibited.

## Interfaces and data

`TrainingExample` is a future contract sketch only. Revision 1 does not register or permit writing training examples, dataset manifests, preference datasets, teacher outputs, provider staging records, jobs, or checkpoints. A later activated revision must define their provenance, classification, license, consent, retention, and feedback-scope rules before any such record exists.

`TrainingReadinessDossier` binds the target behavior, evidence cutoff, archive and evaluation epochs, coverage and recurrence results, effective sample and power analysis, lower-rung comparisons, source-corpus feasibility, prospective cutoff and grouping plan, license/consent/privacy/contamination decisions, independence plan, cost and infrastructure estimates, rollback requirements, expiry, and one result per revision-1 readiness gate. It does not assert that a dataset exists. Its public projection contains only allowlisted gate conclusions under a new identity and no private input digest.

An activated future `TrainingExperiment` would need to freeze dataset manifest, cutoff and grouped splits, contamination and license report, base model digest, method, code and environment, bounded hyperparameter and checkpoint family, statistical and selection units, confirmatory hypotheses, reward specification, integrity constraints, seeds, multiplicity and stopping rules, maximum evaluator looks, durable compute and cost reservations, checkpoints, untouched evaluation epochs, lower-rung equal-budget baselines, stop rules, retention/deletion policy, and publication policy. This kind is unregistered and non-writable while activation is deferred.

If a later revision activates experimentation, methods advance cautiously:

1. supervised fine-tuning or distillation on reviewed structured outputs, bounded tool policies, or licensed teacher outputs with explicit provenance;
2. preference optimization on calibrated, scope-confirmed pairwise decisions;
3. offline or sandbox reinforcement learning only for tasks with execution-grounded, preregistered rewards;
4. online learning remains out of scope until separately specified.

An activated future revision may define a `TrainingProviderAdapter` for capability discovery, digest-bound staging, start, status, checkpoint receipt, cancellation, collection, cost receipt, and deletion or retention attestation. In revision 1 the provider adapter, dataset and example kinds, credential reference for training, outbound dataset operation, training job, and deployable checkpoint route are unregistered or explicitly non-writable, and the validator rejects every attempted use.

## State and failure behavior

Readiness dossiers move `draft -> evidence_bound -> independently_checked -> eligible|deferred|expired`. `eligible` means only that a later activation amendment may be proposed; it grants no provider, data-export, training, evaluation, or deployment action. Changed evidence, epoch, license, privacy decision, or cost estimate expires the dossier. No training-experiment runtime state is legal in revision 1.

A future activated revision must define at least `proposed -> data_audited -> budget_reserved -> preregistered -> independently_reviewed -> human_authorized -> staged -> training -> checkpointed -> hidden_gate_requested -> independently_evaluated -> rejected|parked|proposal_eligible -> draft_pr_open -> attested|denied -> closed`. It must keep provider ambiguity in reconciliation, close incomplete work on budget exhaustion, and prevent hidden-gate feedback from steering the same experiment. `proposal_eligible` permits only a draft PR; SPEC-019 attestation and human merge remain separate.

## Implementation sequence

1. Register `TrainingReadinessDossier`, gate-result, power-analysis, lower-rung-plateau, and deferral-decision contracts.
2. Implement a read-only validator over public and authorized private archive metadata; it emits exact unmet gates without exporting training examples.
3. Add synthetic passing and failing dossiers for coverage, effective sample size, power assumptions, recurrence independence, lower-rung exhaustion, source-corpus feasibility, prospective cutoff/grouping, license, contamination, independence, privacy, non-spendable capacity, and rollback readiness. A synthetic pass never implies that a dataset was created.
4. Prove that provider SDKs, credentials, dataset upload, job creation, checkpoint import, and route activation are absent or denied while `Activation: deferred`.
5. If a real dossier later passes, open a human-reviewed amendment for the experimental provider, dataset-export, training, evaluation, and deletion contracts before performing any pilot.

## Migration and rollback

Revision 1 creates no production or provider migration. Disabling its validator removes no evidence and changes no runtime route. A future activated revision must specify checkpoint migration and rollback; this deferred contract cannot be cited as authority to stage data or models.

## Observability

Revision 1 tracks dossier age, gate pass/fail/unknown, evidence cutoff and freshness, effective sample size, simulated power, recurrence scope, lower-rung uncertainty and cost, unresolved license/privacy/contamination issues, independence gaps, estimated resource envelope, and attempted deferred-operation denials. Any future training metrics require the activated revision that owns those operations.

## Verification

- Seeded contamination, grouped-split leakage, invalid effective sample size, weak power, unsupported license/consent, private-feedback scope expansion, and independence conflicts deny readiness.
- A lower-rung exploratory failure cannot satisfy the plateau gate; every applicable rung requires its preregistered multiplicity-adjusted one-sided uncertainty or an accepted infeasibility/cost-ceiling record.
- Power validation binds executable simulation code, alpha/comparison family, clustering, attrition, missingness, effective-unit calculation, decision rule, and sensitivity range.
- Changing any evidence-bound input expires the prior dossier rather than mutating it.
- Public readiness output omits hidden membership, private identities, private digests, and private feedback.
- Attempts to resolve a training credential, export a dataset, start a provider job, import a checkpoint, or alter routing are denied and recorded while deferred.
- A synthetic fully passing dossier produces only `eligible`; it cannot create an experiment, reserve spend, start training, or satisfy its own activation amendment.

## Acceptance criteria

- [ ] The readiness dossier reports every gate independently and fails closed on missing, stale, weakly powered, contaminated, unlicensed, non-independent, or privacy-ineligible evidence.
- [ ] Power, effective sample size, three-family recurrence, two-epoch/configuration coverage, and lower-rung plateau predicates are executable rather than prose claims.
- [ ] Hidden identities, task details, private feedback, and training examples are absent from public readiness projections.
- [ ] No provider SDK, training credential, dataset upload, job submission, checkpoint import, or deployment path is enabled by revision 1.
- [ ] `Activation: deferred` can change only through a new digest-linked revision and human merge.
- [ ] Synthetic activation dossiers still require a separately accepted provider, dataset, experiment, independent evaluation, full-tree attestation, canary, and event-replay rollback contract.

## Pull-request evidence

Attach the readiness schema and validator, synthetic pass/fail dossiers, power and effective-sample fixtures, lower-rung plateau counterexamples, license/contamination/independence/privacy failures, a safe public projection, and negative proof that deferred mode cannot load credentials, upload data, create a training job, import a checkpoint, or alter routing.
