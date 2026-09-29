# Portable research-to-proposal harness: paper evaluation protocol

Status: proposed preregistration, not an executed study or an autonomy claim. Dated September 7, 2026.
This protocol becomes a completed preregistration only when the pilot-derived sample size, resource ceilings, practical-effect thresholds, split manifest and analysis code are frozen before final-set access.
It follows [the benchmark methodology](../../researcher/benchmarks/PLAN.md), [SPEC-017](../specs/SPEC-017-evaluation-runner.md) and the existing freeze/authority boundaries; it does not activate those draft contracts.

## Claim boundary and research questions

The current adapter evaluates one data-only `packet-policy/v1` boolean, `compact`, using a pure deterministic evaluator and a private frozen-candidate orchestrator. Candidate files are never executed. There is no accepted paid provider, independent scientific judge, automatic skill promotion or automated merge.
The present experiment can establish exact byte budgets, retained source provenance, selected-work coverage and reproducibility on supplied finite inputs. It cannot establish semantic retrieval quality, improved agent task performance, general self-evolution or statistical independence.
The proposed paper separates three questions:

- RQ1: Does the harness preserve evidence and candidate identity, reject invalid proposals and recover without duplicate application?
- RQ2: At matched resource ceilings, does an evidence-guided search policy find more useful, independently supported proposals than fixed alternatives?
- RQ3: Do selected skill or harness changes improve held-out agent task outcomes without critical regressions?

RQ1 is available to deterministic experimentation now. RQ2 and RQ3 require additional accepted execution, dataset and evaluation boundaries. A compact-toggle demonstration is an integration case study, not evidence that an adaptive search algorithm outperforms random search.

## Experimental units, sampling and partitions

The sampling unit is an underlying research need or failure family, defined before retrieval. A need specifies its user task, failure mechanism, admissible evidence and downstream success criteria.
Paper versions, crossposts, query variants, retrieved passages, candidate revisions and repeated runs within a need are nested observations, not independent samples. Record their shared ancestry. A caller-supplied `group_id` is a declaration requiring review, not proof of independence.
Construct a sampling frame covering positive, no-answer, same-topic/wrong-mechanism, differently-worded/same-mechanism, conflicting-evidence, stale-source and distribution-shift needs. Publish inclusion/exclusion rules and sampling probabilities where applicable.
Split by need/failure family and near-duplicate task ancestry, not by individual documents or paraphrases. Assign all related items to the same partition before candidate generation:

1. **Development:** exposed tasks, labels and failures for building the harness, search space and evaluator.
2. **Selection:** disjoint needs used for candidate selection under the frozen search budget; all resulting adaptation is recorded.
3. **Sealed final:** one evaluation of the frozen selected candidates and baselines, with no feedback to search until the study is closed.

Reserve separate development-only needs for variance and feasibility pilots. Pilot examples never become final examples. Final failures are retained for this study and may become development data only in a newly identified future study.

## Arms and fixed-resource comparison

Use the same initial evidence snapshots, candidate grammar, editable surfaces, safety constraints, evaluator and per-need resource ceilings in every search arm. Randomize arm execution order within each need and pair stochastic seeds where meaningful.

| Arm | Frozen behavior | Cost treatment |
| --- | --- | --- |
| Incumbent | Use the preregistered current policy unchanged; no adaptation. | Charge its evaluation and operating cost; report unused search allowance, do not waste it to simulate equality. |
| Archive selection | Select from a digest-frozen pre-study archive using only development/selection evidence and a fixed rule; no new candidates. | Report archive creation/exposure cost separately and amortized under a preregistered reuse assumption; do not present it as free knowledge. |
| Random search | Sample from the same valid candidate grammar with a fixed distribution and seed schedule, without evaluator-directed proposals. | Count duplicates, invalid draws, evaluations and retries under the same ceilings; freeze deduplication and replacement rules. |
| Evidence-guided search | Use evidence and permitted selection feedback to generate or choose candidates under the frozen update rule. | Include retrieval, proposal generation, evaluation, memory/archive lookup, retries and human effort. |

Freeze maximum candidate attempts, evaluator calls, HTTP requests/bytes, tokens, integer currency micros, CPU time, elapsed time and human-review minutes. Match ceilings rather than hiding unequal actual expenditure. Report both quality-at-budget and quality/cost curves at preregistered checkpoints.
Any offline pretraining, curated archive, prior successful candidate or extra human correction must be disclosed as an asymmetric resource. A supplementary equal-exposure comparison tests whether that advantage explains the result.
The current two-value compact grammar permits exhaustive enumeration. Include that exact optimum as a sanity oracle; do not claim a meaningful search-efficiency advantage from choosing between two known values.

## Exposure, leakage and evaluator independence

Before execution, freeze a ledger of which principal, model, process and dataset partition can access each artifact. Log prompt/context digests, source access, feedback releases, archive membership and rejected attempts. Record known model-training contamination and uncertainty; absence of detected overlap is not proof of no exposure.
Keep final tasks, labels, verifier bodies and task-level diagnostics outside author/search workspaces. Use separate evaluator-controlled materializations and a reviewed read boundary. A different agent name, model family or subprocess sharing writable files does not establish independence.
Independent score-bearing semantic judges are evaluator-owned, separately authenticated participants, not proposer-facing proposal reviewers. They receive shuffled opaque candidate/arm IDs and only the task and evidence needed for their assigned judgment under a scoped grant and recorded exposure. They cannot see search ranking, claimed gains, author identity, persuasive author rationale, unrelated hidden items or other judges' first-round labels. Retain version identifiers privately so evidence remains resolvable; labels and diagnostics cannot flow back to active search.
Use at least two qualified reviewers on every score-bearing semantic item, then adjudicate disagreements with a separately recorded rationale. Freeze a calibration set and rubric before final labeling; report pre-adjudication agreement and uncertainty, not only consensus.
Audit blindability: record guesses about arm identity, unavoidable formatting clues and any accidental unmasking. Correctness tests, calibration and label disagreement are not replaced by a model judge. A future model judge requires separately authorized execution and calibration against human labels.

## Outcomes and failure accounting

Freeze one primary endpoint per research question and every denominator before final execution; do not substitute a more favorable proxy afterward.

| Layer | Primary endpoint / mandatory conditions | Secondary outcomes and interpretation |
| --- | --- | --- |
| Mechanical RQ1 | Valid evidence/candidate/result binding and exact recovery disposition for every preregistered scenario; any critical unauthorized effect fails the gate. | False accepts/rejects, missing artifacts, duplicate attempts/effects, replay equality, budget compliance and operator recovery time. |
| Packet adapter | Paired lexicographic `(selected_works, -packet_bytes)` under each fixed byte budget, only after complete reference/provenance/text checks pass. | Unique works, explicit omissions and preserved occurrences. These are not relevance, recall or independent corroboration. |
| Research utility RQ2 | Supported useful proposals per sampled need within budget, judged with the frozen rubric and evidence requirements. | Judged precision/nDCG, known-target recall only where gold coverage permits, unjudged fraction, counterevidence coverage and reviewer minutes. |
| Skill effectiveness RQ3 | Mean downstream task-success difference per need/failure family versus incumbent on sealed tasks, subject to preregistered non-inferiority and safety gates. | Per-skill/family effects, unsupported-claim rate, latency tails, tokens, cost and context competition. Routing and structural health are separate proxies. |

For semantic proposal utility, label topical relevance, implementable mechanism, local evidence support and preservation obligations separately. An abstract-stated result is reported evidence, not a reproduced result. Citation count or repeated appearances never establish independent support.
Record every planned trial: succeeded, invalid, rejected, no-answer, timeout, cancelled, budget-blocked and unknown. Unknown is never imputed as success. Preserve raw outcomes, retries, repairs, exclusions and reasons; no silent best-of-attempt selection.
For end-to-end task utility, unavailable outcomes contribute no demonstrated success to the primary denominator; also report conditional quality among completed cases and preregistered missingness sensitivity bounds. Operational failure must remain distinguishable from an incorrect semantic answer.
Record actual resource receipts, unsuccessful attempts, archive maintenance, human intervention and provider reconciliation. Zero paid calls does not mean zero compute, labor or research acquisition cost.

## Pilot, power and inferential plan

Choose the minimally useful effect and allowable regression margins from product requirements before inspecting pilot arm differences. Freeze the numerical values and justification in the study manifest; do not infer them from a convenient observed gain.
Run a bounded development-only pilot to estimate task difficulty, between-need variance, within-need correlation, disagreement, missingness and costs. Use a separately frozen sensitivity grid to simulate the paired grouped design, targeting 90% power at the useful effect while allowing multiplicity and attrition. Report assumptions and feasible alternatives before selecting the final number of needs.
For stochastic conditions, start pilot variance estimation with at least three replications per condition as required by the benchmark plan, then justify additional replications quantitatively. Repetitions do not increase the count of independent needs. Deterministic duplicate executions are repeatability checks, not new quality samples.
Preregister paired effect estimates and 95% intervals using resampling at the need/failure-family cluster, with nested stochastic replications retained within each cluster. Preserve pairing across arms. Report per-family effects and sensitivity to influential groups and missing outcomes; do not bootstrap individual papers or calls as independent units.
Define the confirmatory comparison family before execution, including all three search-baseline contrasts and any co-primary task outcomes. Apply Holm correction at familywise alpha 0.05; label other model/skill/subgroup analyses exploratory. Preregister critical regression gates that aggregate gains cannot offset.
Use fixed-horizon final evaluation: stop only at the frozen budget/sample boundary or a preregistered safety/futility condition. No significance peeking or additional candidates after final exposure. Any inferential early stopping requires a separately frozen alpha-spending or valid sequential design before execution.
Report every interim look and protocol deviation. Restarting after a failure does not reset spending, sample counts, multiplicity or exposure. An underpowered or prematurely terminated study remains preliminary/inconclusive.

## Held-out transfer and safe ablations

For RQ3, compare no-skill, incumbent, selected candidate and unrelated-change controls on freshly materialized held-out tasks. Add target-plus-related and target-plus-unrelated skill conditions only when their interaction hypotheses and additional comparison costs were preregistered.
Freeze task instructions, expected behavior, deterministic verifiers, model/runtime identities and allowed tools. Execute only after the corresponding provider, containment and cost authorization is accepted. The current zero-call runner cannot supply these observations.
Ablate evidence-guided selection, archive access, query/facet variants, context budget and compact representation separately, holding other factors fixed. Report component and end-to-end effects rather than attributing every gain to the agent architecture.
Test replay versus hash-only verification on inert captured fixtures and deliberate data mutations. Test freeze, authority and isolation failures through denied operations or simulations inside disposable containment. Never disable host guards, expose secrets, run untrusted candidate code on the maintainer's host or relax merge/promotion authority to create an ablation.

## Runtime and operator evaluation

Predeclare crash points around intent, capture, freeze, result publication and verification. Test process restart, missing/corrupt files, stale fences, clock rollback, duplicate invocation, storage exhaustion and unknown outcomes in disposable private runs. Recovery must preserve evidence and fail closed without implicit network/model retries.
Measure actual elapsed scheduling observations, lateness and bounded catch-up; simulated clock ticks are not a multi-day soak. Verify backup/restore and clean replay on the specifically supported platforms before claiming portability or durability.
Give representative operators blinded tasks: inspect evidence, explain why a proposal was rejected, identify an unknown outcome, stop work and recover. Record completion, errors, interventions and time; a dashboard screenshot is not a usability study.
Report platform-specific filesystem/locking assumptions. Portable records and provider-neutral interfaces do not imply Windows support, authenticated deployment or operating multi-host agents.

## Reproducibility, publication and release gates

Publish frozen code/config/schema/evaluator digests, dependency lock, OS/filesystem/CPU/runtime versions, seeds, pairing and split commitments, candidate ancestry, raw measurements and an analysis command. Include unsuccessful candidates and a protocol-deviation ledger. Another operator should reproduce deterministic results from a clean supported environment without Codex or a paid provider.
Keep private locators, credentials, licensed full text, personal data and sealed labels out of public artifacts. Record source licenses and redistribution permissions; distribute public-safe fixtures, permitted excerpts and retrieval instructions when raw redistribution is unavailable. Document the resulting reproducibility limitation rather than silently replacing evidence.
Redacted public exports require separate digest bindings and validation; never imply that changed public bytes retain the private artifact hash. Raw runtime artifacts remain private/ignored unless the existing export policy explicitly permits release.
Publish the protocol commitment before final-set access and the completed analysis afterward, including negative or inconclusive results. A paper may claim only the tested adapter, population, environment and exposure regime. Proposal readiness is not deployment readiness; publication, corpus acceptance, merge and production activation remain separate authorized decisions.
