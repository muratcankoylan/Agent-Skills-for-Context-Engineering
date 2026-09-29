# Published Router Benchmark Results

> Historical result archive. The current SDK runner has no live executor, so
> reproduction commands in dated reports are not executable in this revision.
> A future live run requires a separate reviewed activation. Runtime history
> and raw results remain gitignored.

Each `<date>.md` file in this directory is a committed snapshot of a router benchmark sweep. Raw per-run JSON outputs live under `researcher/benchmarks/router/results/<date>-<seed>/` and are gitignored; only the curated summary published here is tracked in the repo.

Every report includes:

- Run metadata (timestamp, repo commit, fixture SHA, seed, model list, replications).
- Executive summary calling out the actually meaningful findings.
- Per-model leaderboard with bootstrap 95% CIs.
- Per-skill confusion matrix.
- Hardest-prompts breakdown.
- Reproduction command.

The historical workflow followed a routing failure by editing the activation
description, rerunning with the same fixture, and comparing the delta. Do not
attempt that live step with the current zero-call runner.

The historical live runner appended cross-run summaries to
`researcher/reports/router-history.jsonl` (gitignored). The current zero-call
runner does not write history or live results.
