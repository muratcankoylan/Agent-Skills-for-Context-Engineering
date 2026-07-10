# Benchmark Architecture Plan

The current benchmark harness verifies that the researcher OS itself is hard to game (deterministic structural checks and seven adversarial scenarios). It does not yet measure the thing users actually care about: **do these skills make agents better at the tasks they claim to help with?**

This document is the plan to close that gap, in four staged releases, with research-paper-grade methodology and native Codex CLI through Headroom as the execution layer.

## Status

| Stage | Release | What it measures | Cost | Status |
| --- | --- | --- | --- | --- |
| 0 | v2.2.0 (shipped) | Harness resistance to gaming, structural validity | $0 | done |
| 1 | v2.3.0 (shipped) | Per-skill health metrics (deterministic) | $0 | done; corpus 0.814 aggregate, 2 of 15 flagged |
| 2 | v2.3.0 (shipped) | Skill router accuracy (LLM-as-router) | Codex subscription route; $0 marginal API spend | migrated; historical Cursor results preserved |
| 3 | v2.4.0 | Skill effectiveness on real agent tasks | Codex subscription route | initial 27-run pilot published; partial-credit scorer and non-ceiling rerun ready |
| 4 | v2.5.0 | Cross-skill composition | Codex subscription route | future |

### Shipped Stage 2 results (v2.3.0)

Two historical 600-run Cursor sweeps covered `composer-2`, `claude-opus-4-7`, `gpt-5.5`, and `gemini-3.1-pro` at seed=1 with 3 replications per (prompt, model). They remain immutable provenance; new runs use native Codex CLI through Headroom:

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
- Run benchmarks through direct metered API keys. Stage 2 and 3 use native Codex CLI with the configured Headroom provider and ChatGPT/Codex OAuth session.

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

## Stage 2: Skill Router Benchmark (v2.3.0, Codex subscription route)

The first benchmark that exercises a real model. Tests whether the skill descriptions are good enough to route the right skill to a given task.

### Hypothesis

The activation-scenario descriptions in v2.2.0 frontmatter (replacing v2.1.x keyword triggers) should let a frontier model route prompts to the correct skill at high top-1 accuracy and very high top-3 accuracy.

### Procedure

1. **Fixture**: `researcher/benchmarks/router/prompts.jsonl` with 100 prompts. Each line: `{prompt_id, prompt, expected_primary_skill, acceptable_secondary_skills, rejected_skills, reason}`. Stage 1 ships with 50; expand to 100 over time.

2. **Routing prompt**: A standard template (`researcher/benchmarks/router/routing-prompt.md`) that presents all 16 skill descriptions (shuffled per replication) and the task, asks the model to return a strict-JSON ranked list with confidence.

3. **Runner**: `researcher/benchmarks/codex-runner/src/runRouter.ts`. For each prompt x model x replication:
   - Build the routing prompt with shuffled skill order.
   - Call native `codex exec` in a temporary directory outside the repository with read-only sandboxing, plugins/hooks disabled, and `--ignore-rules`.
   - The isolated cwd contains no project-local skills; descriptions in the prompt are the only routing signal.
   - Parse JSON. If parse fails, record as `format_failure` (don't reward bad output).
   - Compare ranked list to ground truth. Record top-1 and top-3 accuracy.

4. **Models**: native Codex model IDs passed with `--models`; the deployment default is `gpt-5.5`. Every result records the requested model ID.

5. **Replications**: 3 per (prompt, model). 100 prompts x 4 models x 3 reps = 1200 calls per full run.

### Cost analysis

- Routing prompt is small (~3-5k input tokens, ~500 output tokens).
- Marginal direct API spend is `$0` on the approved Codex subscription route.
- A hard `--max-runs` gate is still required because subscription access does not remove rate, time, or quota risk.

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

2. **Conditions**: For each task, run six conditions in fresh Codex workspaces with only the condition's skills copied into `.codex/skills/`:
   - `control`: no skills loaded.
   - `target`: only the target skill.
   - `negative`: only a known-irrelevant skill.
   - `full`: all 16 skills.
   - `target_plus_one`: target skill plus one related skill.
   - `target_plus_unrelated`: target skill plus one unrelated skill (interaction control).

3. **Runner**: `researcher/benchmarks/codex-runner/src/runEffectiveness.ts`. For each task x condition x model x replication:
   - Filter tasks and conditions before building the run plan (`--task-ids`, `--conditions`), with a mandatory hard cap over the selected plan.
   - Build the task workspace from `starting/`.
   - Copy only the in-scope skills into the fresh workspace under `.codex/skills/`.
   - Call native `codex exec` with `-C <workspace>` and the deployment-compatible sandbox.
   - On completion, stage `.runner/final.txt`, run `verify.sh`, and record exit code, duration, behavior note, failure reason, and session ID.
   - For rubric-backed handoff tasks, write `.runner/score.json` on PASS and FAIL with full anchor retention and per-category retention.
   - Persist final text, verifier evidence, condition metadata, verifier/scorer SHA, full task-fixture SHA, and partial-credit score.
   - Isolate filtered selections in deterministic selection-hash result directories; resume only records in the current plan whose provenance hashes still match.

4. **Initial task set**: 20 tasks across categories. Five preliminary fixtures are executable: `001` is a smoke fixture; `002` and `004` are retained context-compression tasks; `003` is retained as published ceiling evidence but excluded from the next comparative pilot; `005` is an independent hard replacement with a predeclared budget and rubric. Remaining categories are planned:
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
- Marginal direct API spend is `$0` on the Codex subscription route.
- Request caps, bounded concurrency, resume, and progress logs remain mandatory.

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

## Native Codex/Headroom Integration Details

### Why this runtime

- It is the server's installed first-party Codex CLI agent loop.
- OpenAI ChatGPT/Codex OAuth is managed by Codex CLI; benchmark code never reads credentials.
- Headroom remains on the localhost route used by production.
- Isolated workspaces plus project-local `.codex/skills/` provide controlled routing and ablation conditions.
- No separate Cursor account, API key, or vulnerable SDK dependency is required.

### Skill loading and isolation

- Router: temporary cwd outside the repository, read-only sandbox, no project-local skills.
- Control: fresh workspace with no `.codex/skills/` entries.
- Target and ablations: copy only the curated skill directories into `.codex/skills/`.
- Full: copy all corpus skills into `.codex/skills/`.
- Never run benchmark conditions with ambient project/user rules enabled.

For Stage 3, each condition receives a fresh workspace copied from `starting/`. The task prompt includes the absolute workspace path, final text is written to `.runner/final.txt`, and the locked `verify.sh` executes inside that workspace.

### Runtime result contract

The runner records:

```typescript
interface CodexPromptResult {
  finalText: string;
  stdout: string;
  stderr: string;
  sessionId?: string;
}
```

Effectiveness records add condition, loaded skills, duration, final text, verifier exit/stdout/stderr, behavior notes, and workspace path. Request count and wall time remain the stable cross-version cost proxies.

### Runtime choice per stage

- Stage 2: isolated native Codex prompts in a read-only temporary cwd.
- Stage 3: native Codex runs in fresh `workspace-write` sandboxes.
- Stage 4: the same condition mechanism extended to composition tasks.

### Safety

- OAuth credentials stay inside `/home/hermesadmin/.codex`; the runner only selects `CODEX_HOME`.
- Headroom is bound to localhost.
- `--max-runs` is required for every live execution.
- Concurrency is bounded and defaults to 1.
- Resume skips completed result records by default.
- Every run logs progress and an ETA.
- Deterministic verifiers remain outside agent-editable surfaces.

### Cost gates

The runner implements:

- `--max-runs N`: hard invocation cap;
- `--max-budget-usd N`: marginal-cost forecast cap;
- `--dry-run`: plan without model calls;
- `--models <list>`: explicit native Codex model subset;
- `--concurrency N`: bounded subprocess concurrency.

Every runner prints the runtime fingerprint and forecast before any model call.

## Implementation Order

1. **Stage 1 (this PR, v2.2.1)**: `researcher/scripts/skill_health.py`, output file, integration with `loop_daily.py`. No API cost.

2. **Codex runner**: `researcher/benchmarks/codex-runner/` with package.json, TypeScript utilities, dry-run mode, router executor, and effectiveness executor. It compiles and exits cleanly without direct API keys.

3. **Router fixtures (this PR)**: 50 prompts in `researcher/benchmarks/router/prompts.jsonl`. Adversarial pairs for the v2.2.0 boundary-confusion cases (evaluation vs advanced-evaluation, etc.) plus single-skill positive controls.

4. **First effectiveness task (this PR)**: `researcher/benchmarks/effectiveness/tasks/001-filesystem-context-offload/` fully built. Pattern for the other 19.

5. **Verify (this PR)**: compile, run dry, run skill_health for real, all existing gates still pass.

6. **Execute Stage 1 in CI (next PR after merge)**: add to `loop_daily.py` so skill health updates daily.

7. **Execute Stage 2 (with approved hard cap)**: run through native Codex CLI and Headroom, publish results, and iterate descriptions only when repeated confusions appear.

8. **Build remaining 19 effectiveness tasks (rolling)**: prioritized by which skills carry the most user-facing claims.

9. **Execute Stage 3 (when ready)**: full effectiveness sweep, publish per-skill effect sizes.

10. **Stage 4 design and execution (v2.5.0)**.

## Open Decisions

These need user input before large or published sweeps. They do not block local capped runs.

1. **Replication budget**: approve the hard request cap for statistically meaningful repeated runs.
2. **Models**: use only the deployed `gpt-5.6-sol` runtime or add other Hermes-configured models for cross-model evidence.
3. **Publication policy**: commit redacted raw outputs, attach them to releases, or keep them local and publish aggregates.
4. **Comparison points**: include public benchmark subsets or keep the task set self-contained until Stage 4.

## What This Plan Does Not Solve

- Hermes quiet-mode output does not currently expose provider-normalized token counts; wall-clock and request count are the portable cost proxies until that telemetry is added.
- Model aliases can change across Hermes/provider versions; every run records the requested model ID and repository SHA, but cross-version comparisons still require care.
- The seed user-curated task set is small. Public credibility requires either growing it to 100+ tasks or aligning with an existing public benchmark.
- Real-world deployment differs from benchmark conditions. Effect sizes here are upper bounds, not guarantees.

## How To Read Results

When a future release shows benchmark numbers, the dashboard answers four questions in order:

1. **Did the harness pass deterministic gates?** (always required, Stage 0 + 1)
2. **Can the descriptions route the right skill?** (Stage 2, per model)
3. **Does the skill actually help?** (Stage 3, per skill x model x task)
4. **Do skills compose?** (Stage 4, future)

Skills that fail at any earlier stage do not need later stages to be justified for removal or rework.
