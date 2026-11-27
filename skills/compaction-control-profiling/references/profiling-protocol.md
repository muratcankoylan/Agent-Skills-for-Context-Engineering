# Profiling Protocol Reference

Implementation detail for the compaction-control-profiling skill. The condition definitions and metric definitions follow Devoto et al., "Letting Models Manage Their Own Context: Where We Stand" (arXiv 2611.34147), and the interface contract follows the public NOOA harness (`NVIDIA-NeMo/labs-OO-Agents`), both retrieved 2026-11-26. Everything marked "starting point" is an operating default authored for this skill, not a value from the study; replace it with a measured value once a sweep exists.

## 1. Pressure Estimate

Run the task set once at the largest budget the model supports, with no compaction, and record per task:

- `peak_context`: the largest request size in tokens.
- `cumulative_new`: the sum of tokens added to history across the run (tool outputs plus model turns).

Then, for a candidate production budget `B`:

```text
peak_pressure       = peak_context / B
cumulative_pressure = cumulative_new / B
```

Reading: `peak_pressure` below one means the task fits and no policy is exercised. `cumulative_pressure` of several means the agent must compact repeatedly to finish. The study reports no pressure ratios; it describes its largest gains qualitatively, at tight budgets where the agent has to manage its history repeatedly to make progress. Report the distribution over tasks, not only the mean; a benchmark can mix tasks that fit with tasks that do not.

## 2. Conditions

Write each condition down before the first run. A profile is not reproducible without all of these.

| Surface | Harness-driven | Model-driven |
| --- | --- | --- |
| Trigger | Fixed fraction of the budget | Model decision |
| Scope | Everything except the initial instructions and the most recent N events | Any tagged range the model selects |
| Summary author | A summarizer call issued by the harness | The acting model, inline |
| Model-visible surfaces | None | Interface docs, usage readout, timing instruction, pressure warning |
| Overflow fallback | Drop oldest, retry, fail after K attempts | Same |

Study values for orientation: trigger at 80%, N = 10, timing instruction at 85%, K = 3 (claim-compaction-control-study-setup). Hold the summarizer model constant across budgets in the harness-driven condition, or the baseline moves with the budget.

## 3. Budget Ladder

- Use a geometric ladder (each rung double the last). The study swept 8K to 512K in doublings, seven rungs on its document-research benchmark.
- Bracket the natural peak from section 1: at least two rungs below the median `peak_context` and one above its maximum, so the sweep shows the high-pressure regime, the crossover, and convergence.
- Enforce the budget as a hard limit on request size, measured with the same tokenizer that produces the usage readout.
- Count system prompt, tool definitions, and interface docs against the budget. At the smallest rungs they can consume most of it; record the fixed overhead per rung and drop rungs where the editable region is too small to hold one tool output.

## 4. Trace Schema

One JSON object per event, appended to a per-run log. Field names are suggestions; the content is required.

```text
request     {task, turn, input_tokens, budget, fill, cached_tokens?, prefill_tokens?}
compaction  {task, turn, range_tag, events_archived, input_tokens_at_decision,
             input_tokens_next_request, fill_at_decision, summary_tokens}
reopen      {task, turn, tag, parent_range_tag, fill}
warning     {task, turn, fill, text_version}
fallback    {task, turn, events_dropped, attempt}
doc_read    {task, turn, target}
episode_end {task, turn, outcome, score, error?}
```

`fill` is `input_tokens / budget`. Record `text_version` for every model-visible surface so a wording change is visible in the trace.

## 5. Metric Formulas

```text
uptake                 = tasks with >= 1 compaction / all tasks
never_needed           = tasks with 0 compactions, 0 warnings, 0 fallbacks / all tasks
declined               = tasks with 0 compactions and (>= 1 warning or >= 1 fallback) / all tasks
compression_factor(c)  = c.input_tokens_at_decision / c.input_tokens_next_request
reopen_rate            = compactions with >= 1 later reopen of an archived child / all compactions
first_compaction_fill  = median over tasks of fill_at_decision for the first compaction in the task
warning_resolution     = distribution over {answer, compact, docs_then_compact,
                         inspect_then_compact, other} for the first warning in each task
```

Notes:

- `compression_factor` uses the next request as denominator, so the output of the compacting call is included. Report the median and the 5th to 95th percentile; values below one are valid and mean the context grew.
- `reopen_rate` counts interface retrievals only. Add a companion count of tool calls after a compaction that repeat a call made inside the collapsed range; that captures recovery the archive log cannot see.
- Compute `first_compaction_fill` per budget. A budget where the model never compacted has no value, which is itself a result.
- For `warning_resolution`, follow the episode from the first warning until it ends with an accepted answer or a compaction call. Classify `docs_then_compact` and `inspect_then_compact` by whether a `doc_read` or a history query precedes the compaction.

## 6. Timing Ablation

Minimum design: two budgets (one tight, one loose) by two arms (timing instruction present, absent), same tasks, same seeds where the stack allows.

| Observation | Conclusion | Next arm |
| --- | --- | --- |
| Absent arm compacts at much lower fill, loose-budget score drops | Context anxiety with an accuracy cost; the floor is needed | Keep the floor; try one lower threshold to see where the score recovers |
| Absent arm compacts at much lower fill, loose-budget score holds | Context anxiety without a measured accuracy cost | The floor is optional; compare cumulative input and prefill between arms before keeping early compaction |
| Present arm has near-zero uptake, absent arm compacts | The instruction may be suppressing use; confirm that present-arm tasks reach the warning or the fallback | Test a lower threshold and the paired floor-plus-expectation wording |
| Both arms compact near the same fill | Model is insensitive to the instruction | Drop it; fewer prompt surfaces to maintain |
| Neither arm compacts and tasks reach the fallback | Model declines control | Harness-driven, or test a reworded warning |

The study observed the first-row pattern in two models. A third model compacted early without the instruction and showed no comparable accuracy change, the second-row pattern; with the instruction it almost never compacted, the third-row pattern. The companion post notes that this model often finishes before compaction is needed, so reading its third-row behavior as suppression is this skill's inference, not the study's. A fourth model was less sensitive to the instruction (claim-compaction-control-context-anxiety).

## 7. Classification Criteria

Criteria for the signal table in SKILL.md. Each is a comparison between arms or against replicate spread, not an absolute cutoff, because the study gives no thresholds and absolute values move with model, prompt, and workload. "Beyond spread" means larger than the min-to-max range of replicates in the same cell.

| Signal | Criterion |
| --- | --- |
| Declining control | At budgets where `peak_pressure` exceeds one, `declined` is non-trivial and the model-driven score is at or below the harness-driven score beyond spread |
| Never needed | Zero-compaction tasks are `never_needed`, and `peak_pressure` is below one for those tasks |
| Context anxiety | `first_compaction_fill` in the no-instruction arm is lower than in the instructed arm beyond spread, or the first compaction sits far below the level at which the fallback would act. This is a timing signal and needs no score change |
| Costly context anxiety | Context anxiety, and the loose-budget score of the early-compacting arm is below the harness baseline beyond spread. This is the case that requires a timing floor |
| Suppression | Uptake in the instructed arm is lower than in the no-instruction arm beyond spread, at a budget where tasks reach the warning |
| Aggressive calls | Median `compression_factor` is high relative to other models profiled on the same harness |
| Unrecovered loss | Aggressive calls, a low `reopen_rate`, few repeated tool calls after compaction, and a score drop beyond spread |
| Stop-on-warning | `answer` is the most common `warning_resolution` at a budget where `peak_pressure` exceeds one |

Orientation only, from one study on one harness: median compression factors ranged from 1.5x to 3.7x and reopen rates from 3.5% to 18.6% across four models (claim-compaction-control-compression-reopen). Do not use these as cutoffs.

## 8. Hybrid Layering

Not evaluated in the study. Order the triggers by fill so each layer acts only if the one below it did not:

```text
timing floor  <  pressure warning  <  harness fallback threshold  <  hard limit
```

Starting points, derived from the top down: fallback threshold one large tool output below the hard limit, warning one large tool output below the fallback threshold, and floor at the calibrated per-model value, capped so that it stays below the warning with room for at least one ordinary turn. Size "one large tool output" from the recent maximum, as the self-managed-context skill describes for urgent bands.

Check the order at every budget, not once. The warning and fallback are sized in tokens from the hard limit, while a calibrated floor is usually a fraction of the budget. At tight budgets one large tool output is a large share of the window, so an uncapped floor can land above the warning or the fallback and the layers race instead of stacking. Validate `floor < warning < fallback < hard limit` when the run is configured and refuse to start otherwise. If the cap pushes the floor so low that it invites early compaction, that budget is too tight for a hybrid: cap tool output size or run a single policy there.

Log which layer fired; a harness layer that fires in most tasks means the model has not taken control and the assignment should revert to harness-driven.

## 9. Interface Contract

Minimum contract for a reversible collapse interface. Collapse, archive, and retrieval semantics follow the reference harness (claim-compaction-control-reference-interface); reopen logging is this skill's addition, since the reference harness does not log reads of archived events.

| Operation | Behavior |
| --- | --- |
| `collapse(start_tag, end_tag, summary_text)` | Archive the inclusive range, insert one summary event at its position, return the range tag |
| `get(tag)`, index access, history query | Return active or archived events; every path that returns an archived event logs a reopen |
| `keys()` | List active tags, including range tags of summaries |
| Summary event | Carries range tag, children tags, summary text, and a one-line hint for expanding it |

Edge cases to decide explicitly:

- Overlap with an existing summary: flatten to one summary covering the union.
- Exact re-collapse of a summary: rewrite its text in place.
- Range strictly inside a summary: reject, leave history unchanged, and say how to rewrite.
- No summary text: the marker is still inserted, without text. Allow it as truncation and log it separately; truncation and summarization are different behaviors in the profile.
- Tool-call pairing: decide whether a collapse may separate a model response from the tool results it produced. If allowed, the request formatter must drop the orphaned half; if not, widen the range and report the widened tag.
- Role of the summary: a summary rendered in the assistant role reads as the model's own recap. Whatever role is chosen, apply the persistence-channel monitoring described in self-managed-context to summary text.

## 10. Cost Accounting

- `cumulative_input`: sum of `input_tokens` over all requests in a run, cached or not. This is the study's token metric on its document-research benchmark (its ML-engineering plots use total input plus output tokens) and the right basis for comparing context policies on input volume.
- `prefill_tokens`: tokens the engine recomputed for a request. Under standard prefix caching this is everything after the first changed token. Where the serving stack reports it, compare policies on this as well; where it does not, state that cost was not measured.
- Suffix KV reuse changes `prefill_tokens`, not `cumulative_input`. Its benefit scales with the size of the unchanged suffix after an edit (claim-compaction-control-suffix-kv-reuse), so estimate that size from traces before investing in serving changes.
- Summaries written inline by the acting model cost output tokens in the main loop; harness summarizer calls cost a separate request. Include both.

## 11. Report Template

```text
Model and version:
Harness commit:
Prompt surfaces (hash and text): interface docs, readout format, timing instruction, warning
Task set: name, task count, replicate count, grader
Pressure: distribution of peak_pressure and cumulative_pressure at the production budget

Per budget, per policy: score (mean, min, max), fallback firings, cumulative_input
Per budget, model-driven: uptake, never_needed, declined, compression_factor (median, p5, p95),
                          reopen_rate, first_compaction_fill, warning_resolution
Timing ablation: arms, budgets, first_compaction_fill and score per arm

Assignment: policy per pressure regime, timing floor, layer order
Gaps exceeding replicate spread:
Not measured:
Re-qualify on:
```

## 12. Re-Qualification Triggers

- Model or model version change, including a provider-side update under the same name.
- Any edit to interface docs, readout format or cadence, timing instruction, or warning text.
- A change to the overflow fallback or to the harness-driven threshold used as fallback.
- A shift in workload that moves `peak_pressure` across one.
- A serving change that alters cache behavior, when the assignment was justified on cost.
