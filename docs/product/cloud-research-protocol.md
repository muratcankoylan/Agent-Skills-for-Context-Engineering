# Evidence-governed evolution of a context-engineering repository

Research protocol and implementation analysis. 10 September 2026.
Status: proposed study, with a standalone service preview. Not a submitted paper,
accepted specification, cloud deployment, or measured self-improvement result.

## Abstract

We study whether a repository-owned research service can convert external
technical evidence and observed agent failures into useful, auditable skill
improvements. The unit of evolution is initially a constrained skill-body change,
not unrestricted executable self-modification. The service separates source
observation, claim support, candidate generation, evaluation and acceptance.
Durable attempt identities and conservative effect reservations support operation
outside a developer session. A development implementation connects four model
roles, explicit provider APIs, registered MCP reads, frozen artifacts, private
operator status, and optional draft GitHub delivery. Deterministic tests establish
selected integrity properties; model review is only a screening instrument.
The central empirical question, improvement on independent downstream tasks
under a fixed total budget, remains unmeasured by this implementation.

## 1. Objective and falsifiable questions

The objective is a useful living research repository, not the greatest number of
agents, papers, cron executions or generated pull requests. Success means useful
new mechanisms, fewer repeated failures, maintained skills, and manageable review
burden, with traceable costs and recoverable operation.

1. Does source-grounded knowledge transfer produce more supported, applicable
   changes than a model using only the current skills and task?
2. Does retrieving selected skill sections preserve useful qualifiers better than
   whole-corpus loading at a matched context budget?
3. Does a separate critic improve proposal precision enough to justify its cost?
4. Does a retained archive of unsuccessful hypotheses improve subsequent search,
   compared with latest-candidate-only and repeated independent generation?
5. Do improvements survive a change of execution model, tool environment, and
   held-out failure family?
6. Can repeated operation stay within effect/cost limits after restart, partial
   failure and lost responses, without silently duplicating external changes?

Working hypothesis: durable evidence and independent outcome tests matter more
than unconstrained reflection or adding more agent conversations. This is an
engineering hypothesis, not an established empirical result.

## 2. Prior evidence and limits of transfer

The [Darwin Gödel Machine](https://arxiv.org/html/2505.22954v3) combines an archive
of generated agents with empirical evaluation and reports benefits over variants
without self-improvement or open-ended exploration. Its demonstrated setting is
coding agents and coding benchmarks; the exploration mechanism itself remains
fixed. This motivates testing archive-based search here, not claiming that a
repository with a cron job has reproduced DGM or that coding-benchmark gains
transfer to research curation. Our initial editable surface is deliberately
smaller and does not execute generated code.

[Agentic Context Engineering](https://arxiv.org/html/2510.04618v1) motivates
incremental, structured context changes and a separation between experience,
reflection and curation. The design implication is a versioned, reviewable
knowledge delta with preserved provenance, rather than repeatedly rewriting one
large memory summary. Whether this improves our skills is a local experiment;
retaining more advice can also increase conflict and retrieval burden.

[ALCE](https://aclanthology.org/2023.emnlp-main.398/) treats citation quality as a
distinct evaluation problem. Accordingly, exact quote membership is only a
deterministic grounding check. It does not establish claim entailment, completeness,
source reliability or applicability to a different task population. Those require
separate labels and downstream outcomes.

[Judging the Judges](https://arxiv.org/abs/2406.07791) studies position bias in
model-based comparisons. Our pilot presents both orders in fresh contexts and
rejects order-dependent support. Reversing order does not eliminate shared model
bias, training contamination, verbosity preference or prompt injection. Two
favorable judgments therefore never constitute acceptance or independent evidence.

The [MCP security guidance](https://modelcontextprotocol.io/docs/2026-07-28/tutorials/security/security_best_practices)
describes trust-boundary failures including token forwarding and SSRF. We require
explicit endpoint/tool/schema registration and per-service credentials. Tool
output remains data. Python-side DNS checks do not establish network isolation;
deployment egress controls remain necessary. The compatibility-pinned bridge uses
an older explicit protocol version, rather than claiming universal compatibility.

## 3. Architecture alternatives and choice

| Alternative | Advantages | Material costs or limits | Decision |
| --- | --- | --- | --- |
| Hosted repository workflow for each research interval | Familiar GitHub operation; easy logs and review integration | Durable recovery and uncertain-effect reconciliation still needed; ephemeral filesystem; workflow credentials near execution | Useful future admission/CI adapter, not canonical state owner |
| One persistent service with explicit checkpoints and local SQLite | Small install surface; simple local/cloud parity; inspectable effects and pause state | Single-host availability; careful backup/migration; no horizontal writers | Initial implementation |
| Distributed workflow engine and separate workers | Cross-host durability, worker scaling, long-running workflows | More deployment and operational dependencies before workload justifies them | Reconsider after measured contention or availability need |

This is a choice of state ownership, not a ban on future cloud infrastructure.
The first cloud release can run on a single Linux VM with persistent storage.
Cloud provider, region, identity perimeter and actual capacity remain operator
choices. No cost or uptime estimate is asserted without a workload measurement.

The service's four roles are logical responsibilities with fresh contexts. They
need not be separate processes or microservices. Provider routes are explicit per
role; the judge can use a different model, but diversity is not independence.
Current model calls are sequential. Add concurrency only after measuring useful
latency reduction and shared-budget/attempt behavior under contention.

## 4. Knowledge boundaries and transfer protocol

| Representation | What it establishes | What it cannot establish |
| --- | --- | --- |
| Retained response bytes and observation receipt | What was retrieved through a bounded source path | Truth, relevance, licensing permission or full-paper coverage |
| Normalized evidence ID, source URL, text and digest | Stable addressable content for replay and citation | That normalization retained every qualifier |
| Claim plus exact quote, limitations and evidence IDs | Inspectable proposed interpretation | Entailment or novelty merely from matching strings |
| Critic-supported claim set | A separate model's screening decision | Independent evaluation or acceptance authority |
| Frozen candidate and baseline | Exact compared skill bytes and declared scope | Improved behavior when those bytes are used in an agent |
| Task outcomes and failure traces | Observed behavior under a specified workload | Generalization beyond the measured task/model/tool population |
| Human-merged change with required evidence | Accepted repository evolution | Permission to deploy a new runtime or alter its own gates |

Current corpus retrieval uses deterministic lexical section ranking, offsets,
content digests, a bounded packet, and explicit omissions. The initial implementation
includes selected skill baselines to make exact editing inspectable. A bounded
cross-run memory supplies prior hypotheses/outcomes for the same baseline and
schedule, without prior judge answers. Exact-byte candidate suppression prevents
repeated review of the same proposal. Neither this memory nor a richer
claim/mechanism graph has been evaluated for research effectiveness.

The next transfer layer should store small mechanism records: applicability,
prerequisites, supporting and contradicting evidence, failure cases, tested change,
exposure history and rejection reason. Retrieval should optimize observed task
usefulness, not the number of remembered records. Rejected and negative-result
records need first-class retrieval to prevent repeated failed proposals. Archive
content must never update the evaluator's rules or authorize publication.

## 5. Source acquisition experiment

The implemented default lanes are title/abstract arXiv retrieval and official
research feed windows. They preserve discovery-summary scope. A separate
registered MCP read may expose additional data under reviewed arguments and
credentials. Neither an available adapter nor an SDK unit test demonstrates
access to a real X account, licensed search endpoint or full-paper corpus.

Before comparing acquisition strategies, freeze a population of research needs.
Include source-known needs, terminology shifts, contradictory papers, null/no-answer
needs, stale versions, company-only engineering findings, and social posts that
link to primary evidence. Social commentary is a lead, not an independent paper.
Avoid treating duplicate arXiv versions, syndicated posts or multiple query
variants as independent discoveries.

Compare a literal-query baseline, predefined facet/recency lanes and an optional
registered search/MCP lane at matched request, context and reviewer budgets.
Use a documented relevance pool and measure unjudged coverage. For each need,
label source relevance, mechanism support, missing qualifiers, novelty against
the repository, and whether it yields a testable intervention. Do not report
recall against an incomplete pool as exhaustive web recall.

## 6. Evaluation hierarchy and statistical plan

**Integrity gates:** malformed schemas, fabricated quotes, duplicate identities,
changed frozen inputs, unauthorized paths, budget exhaustion, clock rollback,
restart ambiguity, hostile source instructions, secret reflection, provider
partial responses and publication target drift. Deterministic tests are preferred.
Tests should attempt the prohibited effect and prove denial before that boundary.

**Development pilot:** validate provider schemas, task feasibility, cost variance,
grader reliability and missingness. Include no-change, irrelevant-change and
always-first-choice judge controls. Current reversed-order review belongs here.
It cannot supply the paper's headline result.

**Effectiveness study:** compare no-skill, incumbent skill, candidate skill and a
matched-length unrelated-change control on separately held-out tasks. Keep model,
tools, token ceilings, timeouts and retries fixed. Prefer trusted task assertions;
use blinded semantic graders only for criteria without objective verification,
calibrated against independently labeled examples.

**Search study:** compare repeated independent generation, latest-only iteration,
and an evidence-guided archive with the same editable grammar and total budget.
Include candidate failures, archive preparation, failed retrievals, judge calls,
retries, and rejected changes in cost. Account for cumulative exposure to tasks
across candidate ancestry. The archive must not reveal sealed evaluation answers.

Choose primary estimands and practically meaningful thresholds before the final
study. Determine sample size from a development-only variance pilot and the
smallest worthwhile effect, not a convenient round number. Analyze paired
differences at the independent research-need/failure-family level. Query variants,
paper versions and model seeds are nested observations. Report uncertainty,
multiple-comparison policy and stopping rules. Do not discard invalid, timed-out,
cancelled or unknown runs from the denominator without a declared treatment.

For transfer, hold out failure families and evaluate compatible alternative model
routes. A new frontier model should be tested as a configuration change with
separate provenance, not silently substituted mid-experiment. Versioned fixtures,
prompts, model IDs, tool schemas, corpus and candidate digests belong in every
evaluation manifest.

## 7. Operations, effects and failure semantics

The coordinator durably reserves a bounded attempt before calling a model, source
or GitHub operation. It retains completed outputs for replay. A lost response is
an unknown outcome, not proof of failure and not permission to retry. A restarted
worker quarantines such jobs for reconciliation. Configuration changes cannot
erase reservations by silently rebinding the same state directory.

Draft PR creation and review requests are separate recorded effects; neither is
merge authority. Native provider subprocesses enforce a wall-clock deadline and
receive only the required credential through private stdin. That process boundary
does not sandbox candidate code; candidate code execution is currently absent.
MCP transport still requires deployment-level memory and egress controls.

The current SQLite backup is only an inspection artifact. Production recovery
must bind database tail, source captures, candidate CAS, configuration, schemas,
in-flight effects and release identity in one recoverable closure. Exercise a
restore without live credentials, reconcile remote effects, and require explicit
activation. Copying an old database must never manufacture a new spending budget.

## 8. Reproducibility and disclosure

Publish implementation and deterministic fixtures separately from private source
captures, credentials, operational journals and potentially restricted content.
Apply repository export policy before releasing experimental artifacts. Public
manifests should provide appropriate output/projection digests without exposing
private storage paths. Report source access limitations and retention/licensing
decisions instead of assuming all web text is freely redistributable.

Preserve negative results and exact evaluated trees. Historical router benchmark
results remain dated snapshots from a different runner and are not results for
this service. Do not aggregate fixture tests, model preferences and actual task
outcomes into a single “readiness” or “intelligence” percentage.

## 9. Release sequence

1. Integrate the service as an explicitly pre-release feature and complete its
   source-bound regression evidence.
2. Run native-model and registered-source canaries with declared credentials and
   budgets, multiple needs, an abstention case, and billing/timeout inspection.
3. Add full candidate overlay validation and multi-surface skill synchronization,
   followed by independent downstream tasks.
4. Demonstrate exactly one sandbox draft PR/review request, including lost-response
   reconciliation and protected target denial.
5. Select cloud host and private access boundary; test installation, restart,
   resource exhaustion, persistence, complete restore and operator recovery.
6. Run a bounded multi-day soak and the predeclared effectiveness study. Release
   the research claims only at the level supported by those observations.

The first implementation does not close all six stages. This protocol makes the
remaining work explicit so engineering progress cannot be mistaken for scientific
validation or production authorization.
