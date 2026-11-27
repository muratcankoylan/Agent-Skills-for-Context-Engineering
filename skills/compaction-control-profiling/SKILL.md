---
name: compaction-control-profiling
description: "This skill should be used when deciding, for a specific model and workload, whether the harness or the model should control compaction, and when qualifying or calibrating that choice with measurements: context-budget sweeps that compare harness-driven and model-driven compaction on one harness, the context-pressure regime where delegation pays, a per-model compaction behavior profile (interface uptake, compression factor per call, reopen rate of archived content, context fill at first compaction, response to pressure warnings), context anxiety and timing-instruction calibration, reversible collapse-and-archive interfaces, and re-qualification after a model or prompt change. Route the editable-file protocol, harness invariants, and edit-position cache cost of self-editing agents to self-managed-context, summary content to context-compression, harness thresholds and cache layout to context-optimization, and general evaluation design to evaluation."
---

# Compaction Control Profiling

This skill covers the decision that comes before any self-compacting agent design: for this model, on this workload, should the harness or the model decide when and what to compact? The answer is measured, not assumed. In a cross-model study that gave four current models one compaction interface and one set of instructions, one model nearly tripled its score at a tight context budget while another called the interface in a small minority of tasks and trailed the harness baseline until budgets were large (claim-compaction-control-tight-budget-gain, claim-compaction-control-uptake-variance).

The operating rule: treat compaction control as a property of one model at one context pressure under one prompt. The study saw the outcome change across models, across budgets, and with a single timing sentence. It did not test model versions or alternative wordings, so re-qualifying on those changes is a precaution this skill adds, not a measured result. Qualify the model with a budget sweep and a behavior profile, calibrate the timing instruction, assign control per model and pressure regime, and re-qualify when the model or the prompt changes.

## When to Activate

Activate this skill when:

- Choosing between a harness threshold, a model-called compaction interface, or a hybrid for a specific model and workload
- Onboarding a new model, model version, or system prompt into a harness that exposes compaction to the model
- Designing an experiment that compares compaction policies across context budgets
- An agent with a compaction interface never calls it, calls it at low fill, or returns an answer when warned that context is filling
- Calibrating a compaction timing instruction or the wording of a context-pressure warning
- Specifying the telemetry of a reversible compaction interface: range collapse, archived originals, retrieval by tag
- Checking whether a run that used fewer tokens was cheaper to serve

Do not activate this skill for adjacent work owned by other skills:

- Building the self-editing harness (context as an editable file and the invariants around it), edit-position cache cost, and training a context-editing strategy: `self-managed-context`. This skill decides whether a model qualifies for that control and at which settings.
- What the summary written at a collapse must preserve: `context-compression`.
- Harness-side threshold policy, masking, and cache-stable layout: `context-optimization`.
- Diagnosing why output quality degrades inside a long context: `context-degradation`.
- General evaluation design, rubrics, and regression suites: `evaluation`.
- Early stopping that traces to the task brief instead of a context warning: `long-horizon-prompting`.

## Core Concepts

### Control Is a Per-Model Property

Read a model's compaction behavior on four axes together, never one alone: whether it calls the interface, how much each call removes, whether it goes back for what it removed, and when it starts. Models given an identical interface diverge on all four (claim-compaction-control-uptake-variance, claim-compaction-control-compression-reopen, claim-compaction-control-context-anxiety). In the study, uptake was similar across the three models that used the interface, yet their gains differed; the one that gained most had the largest shrink per call and the highest reopen rate. Uptake alone is not the goal.

The table below is an operating rule derived from those results. The study observed the signals; it did not test the actions.

| Signal | Reading | Action |
| --- | --- | --- |
| Low uptake, score at or below the harness baseline at tight budgets | The model is declining control | Keep harness-driven, or hybrid with a harness fallback |
| Low uptake, tasks end below the timing threshold | Compaction was never needed | Not a failure; the budget is loose for this task |
| First compaction far below the instructed threshold, or at low fill with no instruction | Context anxiety | Compare accuracy at large budgets with and without a timing floor. Add or raise the floor where early compaction costs accuracy; where accuracy holds, the floor is optional |
| Uptake collapses when a timing instruction is added | The instruction may be suppressing use | Check whether those tasks reach the warning or the fallback; if they do, lower the threshold or pair the floor with an explicit expectation to act |
| Large shrink per call with a high reopen rate | Aggressive, recovering through the archive | Acceptable; count the tokens spent on reopens |
| Large shrink per call, low reopen rate, score drop | State lost and not recovered | Require richer summaries; route summary content to context-compression |
| First pressure warning resolves as a returned answer | Warning read as a stop signal | Reword the warning to name compaction as the expected action |

### Context Pressure Sets the Payoff

Estimate context pressure, the ratio of what the task needs to what the window holds, before choosing a policy. Delegated control pays where pressure is high: the strongest gains appeared at tight budgets and shrank as budgets grew, and the one model that trailed the harness baseline caught up only at large budgets. On a second benchmark, whose tasks the authors believe need far less context, the effect was much smaller and confined to the tightest budgets (claim-compaction-control-tight-budget-gain, claim-compaction-control-low-demand-benchmark). When an unconstrained run peaks well inside the window, keep the harness policy: delegation has little to buy and an anxious model can only lose state.

### The Budget Sweep

Qualify a model with a sweep, never a single budget, because the ranking of policies changes with pressure. Run both policies on the same harness, model, tools, tasks, and grader across a ladder of hard context budgets that brackets the task's natural peak (claim-compaction-control-study-setup).

| Condition | Definition |
| --- | --- |
| Harness-driven | At a fixed fraction of the budget, the harness summarizes earlier history and keeps the initial instructions and a fixed number of recent events verbatim |
| Model-driven | The model receives the compaction interface, a live usage readout, a timing instruction, and a pressure warning near the limit |
| Overflow fallback, both conditions | A request over the hard budget drops the oldest events and retries; after a fixed number of failures the task scores as failed |

Shrinking the budget stands in for longer tasks. It is a proxy, and the fallback that keeps runs alive at the smallest budgets is a context policy of its own that can move scores.

### The Behavior Profile

Log five metrics per budget. Definitions follow the study so results stay comparable with it.

| Metric | Definition | What it separates |
| --- | --- | --- |
| Uptake | Share of tasks with at least one compaction call | Using control from declining it |
| Compression factor | Input tokens of the request in which the model decided to compact, divided by input tokens of the next request | Aggressive from timid calls; below one means the context grew |
| Reopen rate | Share of compaction calls whose archived events were later retrieved | Recovered state from state that was unneeded or lost; a lower bound |
| First-compaction fill | Fraction of the budget in use at the first compaction call in a task; median over tasks | Timely from anxious |
| Warning resolution | From the first pressure warning to episode end: returned an answer, compacted at once, read interface docs then compacted, inspected history then compacted, other | Compacting from wrapping up |

### Context Anxiety and the Timing Instruction

Calibrate the timing instruction per model, in both directions. Context anxiety is compaction that starts while ample space remains. With an instruction to consider compacting only past a high usage threshold, most models in the study waited until near it. Without it, two models started at under half of the budget and scored below the harness baseline at large budgets, and a third, which almost never compacted with the instruction, compacted early and regularly (claim-compaction-control-context-anxiety). The timing instruction is therefore a per-model dial that can err in two directions: absent, some models over-compact; present, one model in the study all but stopped compacting. The study reports no accuracy change for that model either way, so treat suppressed uptake as a signal to investigate, not as a demonstrated loss. One hypothesized cause of early compaction is training that penalizes long rollouts (claim-compaction-control-rollout-penalty). Treat the cause as conjecture and the behavior as measurable. Early compaction is the signal; its accuracy cost is a separate measurement, and the study found that cost in two of the three models that compacted early.

### Reversible Collapse Is the Interface Under Test

Profile against an interface where compaction is reversible: the model replaces a tagged range of events with a summary it writes, the harness archives the originals, and any archived event stays retrievable by its original tag (claim-compaction-control-reference-interface). Reversibility is what makes aggressive compaction safe to allow, and it makes the cost observable once the harness logs every read of an archived event. The reference harness does not log those reads itself; the study counted them from traces. A delete-only interface hides the same loss inside repeated tool calls.

Interface properties that keep the measurements clean:

- Tags are stable and visible in the transcript; a summary carries its range tag and a one-line retrieval hint.
- A collapse that overlaps existing summaries flattens into one summary; rewriting a summary is an explicit operation, not a side effect.
- Interface documentation is short and reachable on demand. One model read it before compacting in most first-warning episodes (claim-compaction-control-warning-response); every lookup is a full-context turn spent under pressure.
- The usage readout refreshes at least as often as the model is expected to act on it. A readout refreshed every few turns makes first-compaction fill measure refresh cadence.
- Every collapse logs its range, tokens before and after, and fill. Every read path that can return an archived event (lookup by tag, index access, history query) logs a reopen.

### Tokens Are Not Cost

Price a compaction policy in recomputed tokens, not only in tokens sent. A model-driven run can reach equal or better accuracy with fewer cumulative input tokens (claim-compaction-control-token-savings), but cumulative input counts every input token on every turn, cached or not. Under prefix caching an edit invalidates everything after it, so a shorter context is not automatically cheaper. A serving prototype that reused the cached state of the unchanged suffix reduced prefill per request with no measurable accuracy change, most where the surviving suffix was large (claim-compaction-control-suffix-kv-reuse). Report tokens and, where the serving stack is observable, prefill compute. Route edit placement and suffix reuse mechanics to self-managed-context.

## Practical Guidance

### Qualification Workflow

1. Estimate pressure. Run the task set at the largest available budget and record peak and cumulative context per task.
2. Fix the comparison. Use the same harness, model, tools, tasks, and grader for both policies. Write down the harness threshold and retention rule, and the model-driven interface docs, readout, timing instruction, and warning text. Version the prompt text; it is part of the result.
3. Sweep budgets. Use a geometric ladder of hard request limits that brackets the natural peak from step 1, with at least two rungs below it. Define the overflow fallback, count its firings, and score errors as failures.
4. Replicate each cell and report the spread. Treat differences inside the spread as no difference.
5. Log the behavior profile per budget. Never pool timing metrics across budgets.
6. Ablate the timing instruction at one tight and one loose budget: with it, without it, and at a second threshold if uptake collapses.
7. Classify with the signal table and assign control per model and pressure regime.
8. Price the result in cumulative input tokens, and in prefill compute where serving is observable.
9. Record the assignment with the model version and a hash of the prompt surfaces. Re-qualify when either changes.

### Control Assignment

These assignments, including hybrid layering, are design inferences from the study's results. The study compared the two policies separately and tested none of them as interventions.

| Regime | Profile | Assignment |
| --- | --- | --- |
| Low pressure | Any | Harness threshold as backstop; if the interface is exposed, keep a timing floor so an anxious model does not compact needlessly |
| High pressure | Calls the interface near the threshold and recovers what it needs | Model-driven, with the overflow fallback kept |
| High pressure | Declines control or wraps up on the warning | Harness-driven, or hybrid once a reworded warning restores uptake |
| Any | Compacts early without a timing instruction | Model-driven with a calibrated timing floor wherever early compaction costs accuracy at large budgets; where accuracy holds, the floor is optional and the extra edits are priced instead |

For a hybrid, order the triggers so they cannot race: the model's timing threshold sits below the pressure warning, the warning below the harness fallback threshold, and the fallback below the hard limit. The harness then acts only when the model has declined to. Check that order at every budget: at tight budgets one large tool output is a large share of the window, which can push the warning and the fallback below a floor calibrated as a fraction of the budget. Lower the floor, cap tool output size, or run a single policy at that budget.

### Wording Under Test

The study's instruction and warning text are not reproduced in the report or its companion post, so treat wording as an experimental variable and re-measure after every change.

- State the threshold in the unit the readout reports, so the model can check it.
- When uptake collapses under a floor-only instruction, test a paired form: do not compact before the threshold; at or past it, compacting settled work is expected.
- When warnings resolve as returned answers, test a warning that names the action and rules out the misreading: compact and continue; this is not a request to finish.
- Keep compaction how-to text out of low-fill messages; tiered nudges belong to self-managed-context.

### Reporting

- Plot score against budget for both policies with replicate ranges, one panel per model.
- Tabulate the five profile metrics per budget and the fallback firings per condition.
- State task count, replicate count, and which gaps exceed the replicate spread.
- Attach the prompt surfaces, model version, and harness commit. A profile without them cannot be re-run or compared.

## Examples

**Example 1: Behavior profile from run traces**

```python
def behavior_profile(tasks, budget):
    calls = [c for t in tasks for c in t.compactions]
    idle = [t for t in tasks if not t.compactions]
    med = lambda values: median(values) if values else None   # no calls at a budget is a result
    return {
        "uptake": len([t for t in tasks if t.compactions]) / len(tasks),
        "declined": len([t for t in idle if t.warned or t.fallback_fired]) / len(tasks),
        "never_needed": len([t for t in idle if not (t.warned or t.fallback_fired)]) / len(tasks),
        "compression_factor": med(
            [c.input_tokens_at_decision / c.input_tokens_next_request for c in calls]
        ),
        "reopen_rate": (
            len([c for c in calls if c.archived_tags & c.tags_retrieved_later]) / len(calls) if calls else None
        ),
        "first_compaction_fill": med(
            [t.compactions[0].input_tokens_at_decision / budget for t in tasks if t.compactions]
        ),
        "warning_resolution": Counter(t.first_warning_outcome for t in tasks if t.warned),
        "fallback_firings": sum(t.fallback_count for t in tasks),
    }
```

**Example 2: Reversible collapse with reopen telemetry**

```python
class Events:
    def collapse(self, start_tag, end_tag, summary_text=None):
        span = self.active_range(start_tag, end_tag)        # inclusive; flattens nested summaries
        for event in span:
            self.archive[event.tag] = event                 # archived, never deleted
        tag = f"{span[0].first}..{span[-1].last}"
        self.replace(span, Summary(tag, summary_text, children=[e.tag for e in span]))
        self.log("collapse", tag=tag, fill=self.fill(), tokens_removed=count(span))
        return tag

    def get(self, tag):
        if tag in self.archive:
            self.log("reopen", tag=tag, fill=self.fill())   # numerator of reopen rate
            return self.archive[tag]
        return self.active.get(tag)
```

**Example 3: Instruction pair under test**

Authored for this skill as a starting point for the ablation, not quoted from the study. `{floor}` is set per model from the sweep.

```text
Timing instruction (floor plus expectation):
  The context readout shows usage as a share of the budget. Do not compact below {floor}.
  At or above {floor}, collapse settled work into a summary and continue the task.

Pressure warning:
  Context is at {fill} of the budget. Collapse completed work now and keep working.
  This is not a request to finish early. Archived events stay retrievable by tag.
```

**Example 4: Assignment record**

```yaml
model: <model id and version>
prompt_hash: <hash of interface docs, timing instruction, warning text>
workload: document research; natural peak several times the production budget
profile:                      # illustrative values
  uptake: 0.44
  declined: 0.03
  first_compaction_fill: 0.83
  compression_factor: 2.4
  reopen_rate: 0.08
timing_ablation: without the floor, first compaction moves to low fill and the large-budget score drops
assignment: model-driven with timing floor; harness fallback above the warning
requalify_on: [model version, prompt_hash, interface change]
```

## Guidelines

1. Qualify per model, per model version, and per prompt; never carry an assignment across any of the three.
2. Compare policies on the same harness, tools, tasks, and grader, across a ladder of hard budgets that brackets the natural peak.
3. Estimate context pressure first; do not delegate control where the task fits the window.
4. Log all five profile metrics per budget and read them together.
5. Split zero-compaction tasks into never needed and declined before interpreting uptake.
6. Ablate the timing instruction in both directions before fixing a threshold.
7. Expose compaction as a reversible collapse with archived originals, and log every reopen.
8. Refresh the usage readout at least as often as the model is expected to act on it.
9. Keep an overflow fallback under every policy, count its firings, and score errors as failures.
10. Report replicate spread and benchmark size beside every difference.
11. Report cumulative input tokens and, where observable, prefill compute; never context length alone.
12. Record model version and prompt hash with the assignment, and re-qualify on change.

## Gotchas

1. **Reputation is not disposition**: One of the four models in the study called the interface in a small minority of tasks and trailed the harness baseline at tight budgets, under the same instructions the others used (claim-compaction-control-uptake-variance). Nothing about a model's general standing says which way it will go; do not assign control from leaderboard position or from another model's profile.
2. **Zero uptake has two causes**: A task can end before compaction is needed, or the model can reach the warning and decline. Only the second is a control failure. Split them with the warning and fallback logs.
3. **One instruction, opposite effects**: The timing floor that held two models back from compacting at under half of the budget coincided with near-zero use in another, which compacted early and regularly once the floor was removed (claim-compaction-control-context-anxiety). Test both directions per model.
4. **Warning read as a stop signal**: One model mostly returned an answer after the first pressure warning instead of compacting (claim-compaction-control-warning-response). A premature answer scores as a normal completion, so inspect warning resolution, not only the task score.
5. **Compression factor is not summary size**: The denominator is the next request, which also carries the output of the call that compacted. The factor understates the edit and can fall below one.
6. **Reopen rate is a lower bound**: The study's authors say so of their own count without giving the reason. Two reasons a harness should expect: a model can recover lost state by re-running a search or re-reading a file, and archived events can be reachable through a read path the reopen counter does not instrument. Instrument every such path, and pair reopen rate with repeated-tool-call counts after each compaction.
7. **The fallback writes part of the score**: Drop-oldest at the hard limit is a third policy running under both conditions, and the study's authors note it can affect scores. Report firings per condition before attributing a gap to the policy under test.
8. **A shrunken budget is not a long task**: It reproduces pressure, not the drift, staleness, or multi-session structure of real long-horizon work. Confirm the assignment on at least one task at natural length.
9. **Pooling hides timing**: First-compaction fill is relative to the budget. Pooled across budgets it mixes regimes; report it per budget.
10. **Small benchmarks, large-looking gaps**: With tens of tasks, small differences between strategies or models may not be significant, as the study's authors say of their own results (claim-compaction-control-study-setup). Report the replicate spread and treat gaps inside it as no difference.
11. **Fewer tokens, same bill**: Cumulative input counts cached tokens, and each edit invalidates the cached suffix. Token savings become cost savings only where re-prefill is small or the suffix cache is reused (claim-compaction-control-suffix-kv-reuse).
12. **Stale readout, false anxiety**: A usage readout refreshed every few turns lets a model act on an old value. Verify the refresh cadence before reading first-compaction fill.
13. **Documentation lookup tax**: Models may read interface documentation before the first call. Under pressure that is a full-context turn; keep the essential signature in the readout line.
14. **Profiles expire**: The explanation offered for the strongest model's results is a conjecture about training, not a tested claim. Expect a model update or a prompt edit to move every metric.

## Integration

This skill connects to:

- self-managed-context - Owns the self-editing harness protocol, edit-position cost, and strategy training; this skill decides whether a model qualifies for that control and supplies the profile that tells its scheduled fallback when to engage
- context-compression - Owns what the summary written at a collapse must preserve
- context-optimization - Owns the harness threshold policy that serves as baseline and fallback
- evaluation - Owns general experiment design; this skill supplies the compaction-specific conditions and metrics
- harness-engineering - The compaction interface, timing instruction, and warning text are versioned harness surfaces
- tool-design - Owns the quality of the interface documentation the model reads on demand
- long-horizon-prompting - Owns stop and return conditions in the brief; this skill covers stops induced by context warnings
- context-degradation - Explains why a full window hurts; high pressure is the regime where this skill's decision matters

## References

Internal references:
- [Evidence](./references/evidence.md) - Read when: citing a number, checking an experimental setup, or reading the study's limitations
- [Profiling protocol](./references/profiling-protocol.md) - Read when: implementing the sweep, the trace schema, the metric formulas, the report, or the collapse interface

Related skills in this collection:
- self-managed-context - Read when: the model qualifies and the self-editing harness must be built
- context-compression - Read when: designing what a collapse summary preserves
- evaluation - Read when: building the surrounding regression suite and quality gates

External resources:
- Paper: [Letting Models Manage Their Own Context: Where We Stand](https://arxiv.org/abs/2611.34147)
- Companion post: [Model-driven context management](https://nvidia-nemo.github.io/Applied-Research/dev-notes/posts/2026-11-23-model-driven-context-management/)
- Code: [NVIDIA-NeMo/labs-OO-Agents](https://github.com/NVIDIA-NeMo/labs-OO-Agents)

---

## Skill Metadata

**Created**: 2026-11-26
**Last Updated**: 2026-11-26
**Author**: Agent Skills for Context Engineering Contributors; primary technical source Devoto et al., Letting Models Manage Their Own Context: Where We Stand (arXiv 2611.34147) and the public NOOA harness code
**Version**: 1.0.0
