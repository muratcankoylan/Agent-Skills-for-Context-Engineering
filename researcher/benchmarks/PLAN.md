# Benchmark Architecture Plan

The current benchmark harness verifies that the researcher OS itself is hard to game (deterministic structural checks and seven adversarial scenarios). It does not yet measure the thing users actually care about: **do these skills make agents better at the tasks they claim to help with?**

This document is the plan to close that gap, in four staged releases, with research-paper-grade methodology and the Cursor SDK as the execution layer.

## Status

| Stage | Release | What it measures | Cost | Status |
| --- | --- | --- | --- | --- |
| 0 | v2.2.0 (shipped) | Harness resistance to gaming, structural validity | $0 | done |
| 1 | v2.3.0 (shipped) | Per-skill health metrics (deterministic) | $0 | done; corpus 0.814 aggregate, 2 of 15 flagged |
| 2 | v2.3.0 (shipped) | Skill router accuracy (LLM-as-router) | Cursor credits (~$7 per full sweep) | done; baseline + post-fix delta published |
| 3 | v2.4.0 | Skill effectiveness on real agent tasks | Cursor credits, larger | scaffolded, one task built |
| 4 | v2.5.0 | Cross-skill composition | Cursor credits | future |

### Shipped Stage 2 results (v2.3.0)

Two full 600-run sweeps across `composer-2`, `claude-opus-4-7`, `gpt-5.5`, `gemini-3.1-pro` at seed=1, 3 replications per (prompt, model):

- Baseline: `researcher/benchmarks/router/results-published/2026-05-15.md` (566 of 600; v1 runner died mid-sweep).
- Post-fix (description rewrites + hardened runner): `researcher/benchmarks/router/results-published/2026-05-15-v2.md` (600 of 600, includes delta-vs-baseline section).

Headline finding: targeted description rewrites moved `context-fundamentals` top-1 from 0.255 to 0.489 (+23.4pp) and `project-development` from 0.750 to 1.000 (+25pp, now perfect). Three of four models gained on top-1; all four gained on top-3.

## Goals And Non-Goals

### Goals

- Produce reproducible, model-agnostic evidence that skill loading improves agent behavior or, where it does not, surface that honestly.
- Make every measurement reproducible from a single CLI invocation plus a pinned config.
- Track results longitudinally so regressions are detectable.
- Disclose methodology fully: prompts, tasks, ground truth, scoring, raw outputs.
- Use deterministic checks first, model-judged measurements second, real task execution third.

### Non-Goals

- Build a general-purpose agent benchmarking framework. We benchmark this skill collection on representative tasks.
- Replace SWE-bench, BrowseComp, or other public benchmarks. We can subset them or use them as comparison points, not redo them.
- Train models. This is evaluation only.
- Run benchmarks that require paid APIs other than Cursor. Stage 2 and 3 spend Cursor credits via the SDK.

## Methodology Principles

These apply to every stage.

### Reproducibility

- Every benchmark run is described by a frozen config (model id, seed, fixture revision, repo commit SHA).
- Raw outputs (transcripts, judge JSON, task workspace diffs) are persisted with the run record.
- Each run appends a single line to a history JSONL with the config hash and pointers to raw artifacts.
- A CLI flag (`--seed`, `--config`) lets a third party reproduce a run exactly.

### Statistical Discipline

- Minimum 3 replications per condition (model x skill-state x task) for variance estimation.
- Report effect sizes with bootstrap 95% confidence intervals, not point estimates.
- Paired comparisons where possible (same task, different conditions) using a Wilcoxon signed-rank test on per-task differences.
- Sample size targets per stage are stated below; underpowered runs land as "preliminary" with that label visible in the dashboard.

### Bias Mitigation

- **Position bias** in router benchmarks: shuffle skill order across replications, report consistency.
- **Self-preference** in judge models: never use the same model as judge and candidate. Use a different family (e.g. Composer evaluates Claude outputs, GPT evaluates Composer outputs).
- **Length bias** in pairwise: include length-normalized scoring and a "shorter wins ties" rule.
- **Selection bias** in tasks: tasks include some where the relevant skill should not help (negative controls) so we can measure false-positive rates.

### Ablations

- Per-skill: with vs without each skill, holding all others constant.
- Leave-one-out: remove one skill at a time from the full corpus to find which skills carry the work.
- Order: run skill subsets in different orders to surface order-dependent effects.

### Disclosure

- All prompts published in `researcher/benchmarks/<stage>/`.
- All ground truth published as fixtures.
- All scoring code published in `researcher/scripts/`.
- Raw run outputs (with secrets redacted) committed under `researcher/benchmarks/<stage>/results/` or attached to release notes.

## Stage 1: Deterministic Skill Health (v2.2.1, $0)

The cheap and uncontroversial floor. Per-skill, deterministic scoring of structural quality. Catches drift, missing sections, stale claims, and underspecified gotchas before any user notices.

### Metrics

For each `skills/<name>/SKILL.md`:

- `line_count`: must be at or below 500. Fail above.
- `frontmatter_valid`: name matches directory, description present, description third-person, description length within 1024 chars.
- `required_sections`: When to Activate, Core Concepts, Practical Guidance, Gotchas, Integration, References.
- `gotcha_count`: number of numbered items in Gotchas. Target >= 3.
- `code_example_count`: fenced code blocks.
- `internal_links_resolved`: every `skills/<other>/SKILL.md` link resolves to a real file.
- `external_link_count`: presence only; reachability is opt-in (`--check-urls`) because it requires network.
- `claim_coverage`: numeric claims (regex `\b\d+(\.\d+)?%\b`, `\b\d+x\b`, benchmark names) divided by the number of those claims that have a `claim_id` referencing `researcher/claims/index.jsonl`.
- `mechanism_coverage`: number of mechanisms in `researcher/mechanisms/registry.jsonl` owned by this skill.
- `activation_case_coverage`: number of activation cases in `researcher/fixtures/activation-cases.jsonl` whose `expected_primary_skill` is this skill.

### Output

`researcher/reports/skill-health.json`, regenerated by `researcher/scripts/skill_health.py`. Per-skill scores plus a weighted aggregate per skill plus a corpus-wide aggregate.

`researcher/reports/skill-health-history.jsonl` for daily trend tracking, written by `loop_daily.py`.

### Scoring

Aggregate is a weighted sum with weights tuned to surface drift early:

```
0.20 * normalize(required_sections)
0.15 * normalize(gotcha_count, target=3)
0.10 * normalize(code_example_count, target=2)
0.15 * normalize(internal_links_resolved)
0.10 * normalize(activation_case_coverage)
0.15 * normalize(claim_coverage)
0.10 * normalize(mechanism_coverage)
0.05 * binary(frontmatter_valid)
```

Anything below 0.75 is flagged in the daily snapshot.

### Why this matters

Skill rot is invisible without metrics. A skill that loses its gotcha section, accumulates dead internal links, or drifts past 500 lines is structurally weaker; catching that in CI is cheap insurance.

## Stage 2: Skill Router Benchmark (v2.3.0, ~$5 per full run with Cursor SDK)

The first benchmark that exercises a real model. Tests whether the skill descriptions are good enough to route the right skill to a given task.

### Hypothesis

The activation-scenario descriptions in v2.2.0 frontmatter (replacing v2.1.x keyword triggers) should let a frontier model route prompts to the correct skill at high top-1 accuracy and very high top-3 accuracy.

### Procedure

1. **Fixture**: `researcher/benchmarks/router/prompts.jsonl` with 100 prompts. Each line: `{prompt_id, prompt, expected_primary_skill, acceptable_secondary_skills, rejected_skills, reason}`. Stage 1 ships with 50; expand to 100 over time.

2. **Routing prompt**: A standard template (`researcher/benchmarks/router/routing-prompt.md`) that presents the 15 skill descriptions (shuffled per replication) and the task, asks the model to return a strict-JSON ranked list with confidence.

3. **Runner**: `researcher/benchmarks/sdk-runner/src/runRouter.ts`. For each prompt x model x replication:
   - Build the routing prompt with shuffled skill order.
   - Call `Agent.prompt(routingPrompt, { settingSources: [], model: { id }, local: { cwd: temp } })`.
   - `settingSources: []` ensures the router agent has no skill loaded; the descriptions in the prompt are the only signal.
   - Parse JSON. If parse fails, record as `format_failure` (don't reward bad output).
   - Compare ranked list to ground truth. Record top-1 and top-3 accuracy.

4. **Models**: `composer-2`, `claude-opus-4-7`, `gpt-5.5`, `gemini-3.1-pro`. The list comes from `Cursor.models.list()` at run time; if a model is unavailable it is recorded as `model_unavailable` and the run continues.

5. **Replications**: 3 per (prompt, model). 100 prompts x 4 models x 3 reps = 1200 calls per full run.

### Cost analysis

- Routing prompt is small (~3-5k input tokens, ~500 output tokens).
- At Cursor's free-with-credits pricing: well under $5 per full run.
- Even at unfavorable retail rates: estimated $5-15 per full run.

### Reporting

- Per-model leaderboard: top-1 accuracy with 95% CI, top-3 accuracy, format-failure rate.
- Per-skill confusion matrix: which skills get confused with which.
- Per-prompt drill-down for failures: which models failed, with what alternative skill.
- Append to `researcher/reports/router-history.jsonl` with model, fixture rev, repo SHA, accuracy.

### Why this matters

Skill descriptions are the only signal a deployed agent uses to decide whether to load a skill. If they don't route correctly, the rest of the harness is academic. This benchmark directly validates the v2.2.0 activation-scenario refactor.

## Stage 3: Skill Effectiveness Benchmark (v2.4.0, ~$50-200 per full run)

The benchmark that proves skills actually help.

### Hypothesis

Loading a relevant skill into an agent's context improves outcome quality, token efficiency, or both, on tasks that the skill claims to address. Loading an irrelevant skill should have no effect or only mild noise.

### Procedure

1. **Fixture**: `researcher/benchmarks/effectiveness/tasks/<id>-<slug>/`. Each task directory has:
   - `task.md`: the prompt the agent receives.
   - `starting/`: workspace seed copied into a temp directory before the run.
   - `verify.sh`: deterministic ground-truth check returning exit code 0 if the task succeeded.
   - `metadata.json`: relevant skills, irrelevant skills (for negative control), category, expected difficulty.

2. **Conditions**: For each task, run six conditions:
   - `control`: `settingSources: []`. No skills loaded.
   - `target`: `settingSources: ["project"]` with only the target skill present. Other skills are temporarily moved out.
   - `negative`: `settingSources: ["project"]` with only a known-irrelevant skill present.
   - `full`: `settingSources: ["project"]` with all currently published skills present.
   - `target_plus_one`: target skill plus one related skill.
   - `target_plus_unrelated`: target skill plus one unrelated skill (interaction control).

3. **Runner**: `researcher/benchmarks/sdk-runner/src/runEffectiveness.ts`. For each task x condition x model x replication:
   - Build the task workspace from `starting/`.
   - Copy only the in-scope skills into `.cursor/skills/` of the task workspace.
   - Call `Agent.prompt(taskPrompt, { settingSources: ["project"], model: { id }, local: { cwd: taskWorkspace } })` (or local cloud option for parallel runs).
   - On completion, run `verify.sh`; record exit code, durationMs, transcript token counts (from `run.conversation()`).
   - Persist transcript JSON, workspace diff, verify output.

4. **Initial task set**: 20 tasks across categories:
   - **filesystem-context**: agent must offload a 5,000-line tool output then retrieve specific data from it.
   - **context-compression**: agent gets a 100k-token chat history and must produce a 2k-token handoff that preserves named entities.
   - **multi-agent-patterns**: agent must decide whether to use subagents for a parallelizable task and justify it.
   - **memory-systems**: agent must persist a user preference across two simulated sessions.
   - **tool-design**: agent must consolidate three overlapping tool calls into one.
   - **evaluation**: agent must produce a rubric for a given task description.
   - **advanced-evaluation**: agent must run a position-bias-mitigated pairwise comparison.
   - **harness-engineering**: agent must identify which of four agent configurations is missing a locked evaluator.
   - **context-degradation**: agent must place critical info at U-curve endpoints for a long context.
   - **context-optimization**: agent must mask tool outputs above 2k tokens.
   - **latent-briefing**: agent must decide whether KV cache compaction applies (positive case + negative case).
   - **bdi-mental-states**: agent must convert a small RDF graph into a structured belief state.
   - **hosted-agents**: agent must propose a warm-pool config for a multiplayer scenario.
   - **project-development**: agent must evaluate task-model fit and propose a pipeline.
   - **context-fundamentals**: agent must explain a context degradation pattern.
   - Plus 5 negative-control tasks where no skill should help (basic arithmetic, plain code reformatting, etc.).

5. **Models**: same as Stage 2.

6. **Replications**: 3 per (task, condition, model). 20 tasks x 6 conditions x 4 models x 3 reps = 1440 agent runs per full sweep.

### Cost analysis

- Average effectiveness task is larger than routing prompts: 10-50k input tokens, 1-5k output tokens, multiple tool calls.
- Cursor free-with-credits: should fit in monthly allotment for one full sweep.
- Retail equivalent estimate: $50-200 per full sweep depending on which models are active.

### Reporting

- Per-skill effect size: success rate delta, token cost delta, durationMs delta between control and target.
- Per-skill effect plot: bar chart with 95% CI.
- Negative-control validation: irrelevant skill should show effect size near zero; if not, the test is biased.
- Per-model leaderboard: which model benefits most from skills.
- Append to `researcher/reports/effectiveness-history.jsonl`.

### Why this matters

This is the headline result. "Loading filesystem-context reduces tokens by N% with zero quality loss on tasks where it applies" is the kind of claim that justifies the existence of the skill collection.

## Stage 4: Cross-Skill Composition (v2.5.0)

Composition is where curated collections add or destroy value compared to individual skills. Tests:

- Do two skills loaded together produce additive, synergistic, or conflicting guidance?
- Are integration sections accurate? When skill A's integration mentions skill B, does loading both actually compose?
- Are there ordering effects in how skills appear in context?

Deferred to v2.5.0 because it requires Stage 3 infrastructure plus task design specifically targeting interactions. Sketched here, not designed in detail.

## SDK Integration Details

### Why the Cursor SDK

- Free with the existing Cursor team credits the user already has.
- Same agent loop as the IDE and CLI, so results transfer to production usage.
- Multi-model: composer-2, claude-opus-4-7, gpt-5.5, gemini-3.1-pro through one interface.
- `settingSources` gives precise control over which skills load (this is the key affordance for ablation).
- Cloud runtime for parallel execution when local resources are insufficient.

### settingSources and skill loading

This is the central mechanism we exploit.

- `settingSources: []` (default): no on-disk settings load. Agent has no skills. Use this as the **control condition** and for the router benchmark where we want descriptions to be the only signal.
- `settingSources: ["project"]`: loads `.cursor/` from the cwd. Used to load only specific skills by copying them into a controlled workspace.
- `settingSources: ["project", "plugins"]`: also loads plugin skills. Less useful for benchmarks; we want full control.
- `settingSources: "all"`: loads everything including user and team settings. Avoid in benchmarks; it leaks the caller's environment.

For Stage 3, each task workspace is built fresh per condition: copy the `starting/` directory to a temp dir, then conditionally place skills into `.cursor/skills/`.

### Result schema we rely on

From the Cursor SDK reference:

```typescript
interface RunResult {
  id: string;
  status: "finished" | "error" | "cancelled";
  result?: string;          // final assistant text
  model?: ModelSelection;   // resolved model
  durationMs?: number;
  git?: RunGitInfo;
}
```

Plus `run.conversation(): Promise<ConversationTurn[]>` for the per-turn transcript. Token counts come from the conversation events (precise schema depends on SDK version; the runner abstracts this).

### Runtime choice per stage

- Stage 2 (router): local runtime, no cwd dependence beyond a temp dir. Fast.
- Stage 3 (effectiveness): local runtime for most tasks; cloud runtime for tasks that need filesystem isolation or parallel execution.
- Stage 4: cloud runtime by default for full parallelism.

### Safety

- Privacy Mode enabled on the Cursor account that runs benchmarks, per Cursor's [privacy docs](https://cursor.help/security-and-privacy/privacy.md). Eval data stays out of training.
- `apiKey` always passed explicitly, never relied on from env, so cross-tenant mistakes are impossible.
- `await using` syntax for every agent so disposal is automatic.
- Concrete rate-limit handling: backoff schedule per Cursor's docs, exponential 1s/2s/4s/8s/16s on 429.

### Cost gates

The runner implements per-run cost caps:

- `--max-runs N`: hard cap on total agent invocations.
- `--max-budget-usd N`: estimated cost cap, fail fast if exceeded.
- `--dry-run`: print plan, do not call.
- `--models <list>`: subset to one model for development.

Every runner prints a cost forecast before any agent call.

## Implementation Order

1. **Stage 1 (this PR, v2.2.1)**: `researcher/scripts/skill_health.py`, output file, integration with `loop_daily.py`. No API cost.

2. **SDK runner scaffolding (this PR)**: `researcher/benchmarks/sdk-runner/` with package.json, tsconfig, common utilities, dry-run mode. Compiles and exits cleanly without an API key.

3. **Router fixtures (this PR)**: 50 prompts in `researcher/benchmarks/router/prompts.jsonl`. Adversarial pairs for the v2.2.0 boundary-confusion cases (evaluation vs advanced-evaluation, etc.) plus single-skill positive controls.

4. **First effectiveness task (this PR)**: `researcher/benchmarks/effectiveness/tasks/001-filesystem-context-offload/` fully built. Pattern for the other 19.

5. **Verify (this PR)**: compile, run dry, run skill_health for real, all existing gates still pass.

6. **Execute Stage 1 in CI (next PR after merge)**: add to `loop_daily.py` so skill health updates daily.

7. **Execute Stage 2 (when env key provided)**: run router benchmark, publish results, iterate descriptions where confusions appear.

8. **Build remaining 19 effectiveness tasks (rolling)**: prioritized by which skills carry the most user-facing claims.

9. **Execute Stage 3 (when ready)**: full effectiveness sweep, publish per-skill effect sizes.

10. **Stage 4 design and execution (v2.5.0)**.

## Open Decisions

These need user input before Stage 2 execution. They do not block scaffolding.

1. **Privacy mode**: confirm enabled on the Cursor account that will run benchmarks.
2. **Higher rate limits**: confirm whether to email `leerob@cursor.com` for benchmark-grade limits per Cursor's docs, or rely on default limits for a smaller initial sweep.
3. **Models to include in v2.3.0 first run**: ship with composer-2 only, or include claude/gpt/gemini from day one?
4. **Publication policy**: full raw transcripts committed to the repo, or hosted separately and linked? Transcript size at full scale is multi-MB per sweep.
5. **Comparison points**: include public benchmark subsets (BrowseComp, SWE-bench) for cross-reference, or keep our task set self-contained for v2.4.0 and add cross-reference in v2.5.0?

## What This Plan Does Not Solve

- Tokens-per-task accounting depends on the per-turn data the SDK exposes. If `conversation()` does not include token counts we fall back to wall-clock and request-count as cost proxies until we instrument it.
- Cursor's model catalog is not stable across time; we record the resolved model id per run for reproducibility, but cross-version comparisons require care.
- The seed user-curated task set is small. Public credibility requires either growing it to 100+ tasks or aligning with an existing public benchmark.
- Real-world deployment differs from benchmark conditions. Effect sizes here are upper bounds, not guarantees.

## How To Read Results

When a future release shows benchmark numbers, the dashboard answers four questions in order:

1. **Did the harness pass deterministic gates?** (always required, Stage 0 + 1)
2. **Can the descriptions route the right skill?** (Stage 2, per model)
3. **Does the skill actually help?** (Stage 3, per skill x model x task)
4. **Do skills compose?** (Stage 4, future)

Skills that fail at any earlier stage do not need later stages to be justified for removal or rework.
