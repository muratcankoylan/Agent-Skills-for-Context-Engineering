# GPT-5.6-sol Medium vs XHigh Reasoning Experiment

**Status:** precommitted; no xhigh comparison outputs observed
**Purpose:** measure the reasoning-effort factor separately from the `context-compression` skill factor

## Frozen factors

- model: `gpt-5.6-sol`;
- seed: `3`;
- tasks: `002,004,005,006,007,008`;
- conditions: `control,target`;
- replications: `3`;
- xhigh hard cap: `36` model calls;
- xhigh concurrency: maximum `3`;
- medium baseline: accepted offline regrade of the already completed 54-run seed-3 experiment;
- scorer: Markdown-insensitive exact-anchor scorer;
- marginal direct API cost: `$0` through the subscription route.

The negative condition is excluded because this experiment estimates reasoning effort and the residual target-skill effect, not irrelevant-skill bias.

## Provenance equivalence

Medium generation commit: `9e09182e68e8bc245b1deada580adc79f7f1bacb`.

Frozen Git tree objects match the current experiment branch:

| Surface | Tree SHA |
|---|---|
| `skills/context-compression` | `97c3332d5bbe273636f293988c49a5bd7eec322a` |
| task 002 | `d8a05b023a263f52916393819634df46332ae35f` |
| task 004 | `5fe1cc8a83e7a2648555af3f8c54782cf44e1092` |
| task 005 | `a1d3b27f648d0bc36e56d45cbaa7386ea7d9900a` |
| task 006 | `b99db2183fb9e49bd47003a56e008d6b862fe053` |
| task 007 | `734eef309f536386c9127a09001bac43f2b77721` |
| task 008 | `bef2f5043efd869350c1cf3f5ff983ff05f60f11` |

The runner records equivalent SHA-256 provenance for loaded skill directories in every new xhigh record and rejects stale resume records whose skill hashes differ.

## Comparisons

1. `xhigh control` vs `medium control`: raw reasoning-effort effect without project-local skills.
2. `xhigh target` vs `xhigh control`: residual effect of `context-compression` at maximum reasoning.
3. `xhigh target` vs `medium target`: maximum-reasoning quality and latency trade-off when the skill is loaded.

Pairing key: `(task_id, replication)`.

## Endpoints

Primary quality endpoints:

- deterministic pass rate;
- aggregate anchor retention;
- per-category retention;
- forbidden stale-fact violations;
- paired improvements, regressions, and ties.

Secondary operational endpoints:

- average duration;
- output bytes;
- runtime errors and unsupported-effort failures.

No token-count claim will be made because the current quiet Codex route does not expose provider-normalized usage.

## Interpretation rules

- This is an exploratory model-factor experiment, not a skill-promotion gate.
- `xhigh` is considered quality-improving only if it has at least one paired improvement and zero paired regressions against the corresponding medium condition.
- A quality tie with higher duration means xhigh is not operationally better for this task family.
- Any target-vs-control regression at xhigh is reported and cannot be hidden by aggregate retention.
- Exact paired p-values are reported, but the study is not powered for significance because medium control has only three observed failures available for improvement.
- Existing tasks, outputs, scorer thresholds, and pair membership may not be changed after xhigh execution begins.
- Results remain separate from the locked medium promotion evidence.

## Commands

```bash
cd researcher/benchmarks/codex-runner
npm run effectiveness:dry-run -- \
  --models gpt-5.6-sol \
  --reasoning-effort xhigh \
  --task-ids 002,004,005,006,007,008 \
  --conditions control,target \
  --reps 3 \
  --seed 3 \
  --concurrency 3 \
  --max-runs 36
```

The live command is identical except `effectiveness:run` replaces `effectiveness:dry-run` and adds `--no-resume` for the first execution.
