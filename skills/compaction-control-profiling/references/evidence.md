# Evidence Reference

Dated numbers behind the compaction-control-profiling skill. Primary source: Devoto, Vem, Safavi, Kariyappa, Tseng, Furgale, and Silveira Cabral, "Letting Models Manage Their Own Context: Where We Stand", NVIDIA technical report, arXiv 2611.34147v1 (2026-11-25), with its companion dev-notes post (2026-11-23) and the public NOOA harness code (`NVIDIA-NeMo/labs-OO-Agents`, Apache-2.0, `main` as retrieved). Retrieved 2026-11-26.

Every figure here is bound to a model version, a prompt, one harness, and one benchmark configuration. Read the setup before reusing a number, and do not transfer a number to another stack without re-measuring.

## What Is and Is Not Citable

The report has no numeric tables and no appendix. Its results are in prose and plots.

- Citable: values stated in the prose. Figure 6 bar labels are confirmed per model by the prose (which rounds them).
- Citable with a caveat: the per-model split in Figure 5. The prose gives the range for three models and the value for the fourth; the split is read from bar labels in axis order, the same order Figure 6 uses. Confirm against the plot before relying on which of the three models is highest.
- Not citable from text: per-budget scores in Figures 3, 4, 10, and 11; the minor segments of Figure 7; the per-benchmark, per-policy bars of Figure 13. Read the figures directly before quoting any of these.
- Not reproduced in the report or its companion post: the timing instruction text, the pressure warning text, and the experiment configurations. No public release of the suffix KV reuse prototype was found at retrieval. The public harness ships a default nearly-full line (see Reference Interface); whether the study used it as its pressure warning is not stated.

## Study Setup

claim-compaction-control-study-setup

| Element | Value |
| --- | --- |
| Harness | NOOA, one harness for both conditions |
| Harness-driven condition | At 80% of the context budget the harness summarizes earlier history, keeping the initial instructions and the 10 most recent events verbatim |
| Model-driven condition | Context API, live context-usage indicator, instruction to consider compacting only once usage reaches 85%, and a context-pressure warning added to the request near the limit |
| Budgets | 8K to 512K tokens, each a hard limit on request size. The OfficeQA Pro v2 plots show seven rungs in doublings; some MLE-bench Lite panels omit a rung for some models |
| Overflow fallback | Remove the oldest events and retry; after three failures the run counts as a wrong answer |
| Models | GPT-6.1 Sol, Kimi K3, DeepSeek V4 Pro, Claude Opus 5.5 |
| OfficeQA Pro v2 | 90 questions over a large pre-parsed document corpus; score is passed tasks over all 90 trials including errors; points are equal-weight replicate means with min to max bars |
| MLE-bench Lite | 22 Kaggle competitions; score is mean leaderboard percentile with missing scores counted as zero |

The harness-driven threshold (80%) and the model-driven instruction (85%) are different numbers. The two conditions were compared separately, not layered.

## Accuracy Against Budget

claim-compaction-control-tight-budget-gain

- GPT-6.1 Sol on OfficeQA Pro v2 at a 32K budget: 21% harness-driven to 56% model-driven, described as nearly 3x.
- Gains are largest at tight budgets and shrink as the budget grows.
- GPT-6.1 Sol and Kimi K3 are ahead of the harness baseline at small budgets. DeepSeek V4 Pro improves less. Claude Opus 5.5 trails the baseline until the budget is large enough that the strategies converge.
- The study applied no extra training. The authors state they do not know how the evaluated models were trained.

claim-compaction-control-low-demand-benchmark

- On MLE-bench Lite the effect is much smaller and limited to the tightest budgets. The authors' reading, hedged as probable, is that its tasks need far less context. They report no measurement of context demand, so this is a suggestive contrast with the result above, not a controlled comparison.

## Interface Uptake

claim-compaction-control-uptake-variance

Share of tasks with at least one compaction call, model-driven runs, all budgets pooled. The prose states that three models fall between 42% and 53% and that Claude Opus 5.5 is at 4%; the per-model split below is read from Figure 5 bar labels in axis order:

| Model | Tasks with a compaction |
| --- | --- |
| DeepSeek V4 Pro | 53% |
| Kimi K3 | 45% |
| GPT-6.1 Sol | 42% |
| Claude Opus 5.5 | 4% |

The companion post adds that Claude Opus 5.5 often finishes before compaction is needed. Pooled uptake therefore mixes two cases, never needed and declined, which is why the skill splits them.

## Aggressiveness and Reopening

claim-compaction-control-compression-reopen

| Model | Median compression factor per call | Compaction calls later reopened |
| --- | --- | --- |
| GPT-6.1 Sol | 3.7x | 18.6% |
| Kimi K3 | 2.1x | 6.9% |
| DeepSeek V4 Pro | 1.8x | 3.5% |
| Claude Opus 5.5 | 1.5x | 14.1%, noisy because calls are rare |

Reopen values are bar labels; the prose rounds them to 19%, 7%, 3%, and 14%.

Definitions as published:

- Compression factor: input tokens of the request in which the model decided to compact, divided by input tokens of the next request, which also carries the executed cell's output. Two means the context was halved; below one means it grew. All confirmed calls are pooled across budgets.
- Reopened: share of compaction calls whose archived events were later retrieved through the context API. The authors state this is a lower bound.

The authors read the combination for GPT-6.1 Sol (calls when needed, compacts most per call, retrieves when needed) as the profile most comfortable with the interface.

## Response to the First Pressure Warning

claim-compaction-control-warning-response

64K budget. Each episode is followed from the first context-pressure warning until it ends with an accepted final answer or a compaction call.

| Model | Dominant resolution |
| --- | --- |
| GPT-6.1 Sol | Reads the API docs, then compacts: 69% of episodes |
| Kimi K3 | Compacts straight away: 49% |
| DeepSeek V4 Pro | Inspects the event history, then compacts: 46% |
| Claude Opus 5.5 | Returns an answer in most episodes instead of compacting |

The prose gives no percentage for Claude Opus 5.5; do not quote one from the plot without reading it.

## Context Anxiety

claim-compaction-control-context-anxiety

Metric: fraction of the context budget in use at the first compaction call in a task; median over tasks; one value per budget.

| Model | With the 85% instruction | Without it |
| --- | --- | --- |
| Kimi K3, 128K budget | About 84% | 29% |
| DeepSeek V4 Pro, 256K budget | 83% | 40% |
| Claude Opus 5.5, 128K budget | Almost never compacts | Compacts regularly, median 16% |
| GPT-6.1 Sol | No value given | Described as less sensitive; no value given |

Accuracy cost: at budgets of 128K and above, the variants without the timing instruction score about 8 points below the harness baseline for Kimi K3 and DeepSeek V4 Pro. GPT-6.1 Sol and Claude Opus 5.5 show no comparable change.

The term follows Igbinedion et al., "Lost in Context: Addressing Context Anxiety in Large Language Models" (arXiv 2607.21616), on models that misjudge their remaining token budget. That paper was not retrieved for this skill and is cited here only as the origin of the term.

claim-compaction-control-rollout-penalty

The authors hypothesize that early compaction reflects training that rewards short contexts, and cite the Kimi K3 report (arXiv 2607.24653): trajectories exceeding a per-problem token budget receive a reward of -1. Evidence strength is secondary; the Kimi report was not retrieved, and the causal link is the authors' hypothesis.

## Token Usage

claim-compaction-control-token-savings

OfficeQA Pro v2, cumulative input tokens per run, counting all input tokens at every turn whether cached or not.

| Model and budget | Harness-driven | Model-driven |
| --- | --- | --- |
| Kimi K3, 32K | 62M tokens, 41% score | 36M tokens (41% fewer), 43% score |
| Kimi K3, 64K (benchmark not named in the sentence; metric and score scale match OfficeQA Pro v2) | 52% score | About 11% fewer tokens, 57% score |
| GPT-6.1 Sol | Baseline | No comparable saving |

Other models fall in between. Runs below 95% trace coverage were excluded from the OfficeQA Pro v2 token plot. The MLE-bench Lite plot uses a different metric, total input plus output tokens.

## Suffix KV Reuse

claim-compaction-control-suffix-kv-reuse

- Prototype in the SGLang serving engine with Qwen3.6-27B at a 32K context, compared with standard prefix caching.
- Paired with the model-driven context API, prefill compute per request fell by 4 to 15% across OfficeQA Pro, MLE-bench Lite, and the DeepSWE coding benchmark, and the prose reports no measurable impact on task accuracy.
- Figure 13 also plots the harness-driven policy. Its bars are not assigned to series here, but at least one prefill reduction is near 1%, so the 4 to 15% range does not describe both policies. Two of the six plotted reward deltas are larger in magnitude than their printed error; the prose summary is "no measurable impact". Read the figure before citing a per-benchmark or per-policy value.
- Savings were largest on OfficeQA Pro, where the suffix that survives an edit averages about 10K tokens, roughly 60% of the prompt, because tool calls retrieve long documents that stay in context.
- Scope: one open model, one engine, prefill compute only. End-to-end latency and cost were not measured, and suffix reuse is an approximation to full recomputation.

For the mechanism and a second, independent implementation, see the self-managed-context skill (Suffix Cache Reuse).

## Reference Interface

claim-compaction-control-reference-interface

Verified against the public harness source at retrieval:

- `EventsApi.collapse(start_tag, end_tag, summary_text=None)` archives an inclusive tag range into one summary event and returns the range tag, for example `"2..40"`. With `summary_text=None` the summary marker is still inserted, with no text; the harness calls this truncation.
- Archived originals remain readable by their own tags through `get` (returns nothing if missing) and index access (raises if missing); a summary lists its children tags.
- A collapse whose range overlaps existing summaries flattens to one summary. Re-collapsing a summary's exact range rewrites its text in place; a range strictly inside an existing summary raises an error and leaves history unchanged.
- The events interface is hidden from the model by default and is enabled per agent. When enabled, the agent prompt tells the model to read the interface documentation before first use.
- The usage readout renders tokens used over the usable window with a percentage, appends a one-line reminder of the collapse call, and adds a nearly-full line when utilization of the usable window exceeds 80% or when any context block or event has been evicted or dropped. It is part of the live context, which the default policy appends to history as a fresh snapshot at least every 5 turns, not every turn.
- The harness documentation notes that a collapse can separate a model response from the tool-call batch it issued; this is not rejected or auto-expanded, and incomplete batches are omitted from the request.

The harness reads archived events through more than one path (lookup by tag, index access, and history query), and none of them logs the read; the study counted reopens from traces, and reopen logging in this skill's interface contract is an addition. Whether the study changed any of these defaults is not stated in the report.

## Limitations Stated by the Authors

- Small benchmarks: 90 questions and 22 competitions, so small differences between strategies or models may not be significant.
- Simulated pressure: shrinking the budget is a proxy for long tasks and does not capture every property of long-horizon work; the drop-oldest fallback can itself affect scores.
- Four models with unknown training. The explanation for the strongest model's results (possible training on similar context-management features) is a conjecture, not a tested claim.
- Suffix KV reuse was evaluated with a single open model in one serving engine.

## Additional Limits for This Skill

- Single primary source. The report states that its tight-budget finding corroborates Context Language Models (arXiv 2609.37725), an empirical study of harness design for coding agents (arXiv 2609.20804), and MEMENTO (arXiv 2604.09852). Of those, only Context Language Models has been retrieved in this collection; the self-managed-context skill records its capability-dependence result on a different interface and different models.
- The signal table, control-assignment table, hybrid layering, and example wording in SKILL.md are operating rules derived from these results. The study did not evaluate them as interventions.
- The rule to re-qualify after a model version or prompt wording change is a precaution. The study varied models, budgets, and the presence of one timing sentence; it tested no version change and no alternative wording.
- The study reports no pressure ratios. The pressure estimate in the protocol is this skill's way to locate a workload relative to the regimes the study describes qualitatively.
