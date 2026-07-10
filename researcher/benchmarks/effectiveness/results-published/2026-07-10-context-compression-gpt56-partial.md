# Context Compression Partial-Credit Pilot — GPT-5.6-sol

**Date:** 2026-07-10
**Status:** preliminary, directionally positive, not statistically significant
**Repository commit:** `dd95636fe4726f5516031f00b2ae3a9f981627f7`
**Runtime:** native Codex CLI 0.144+ → Headroom localhost → ChatGPT/Codex OAuth
**Model:** `gpt-5.6-sol`
**Seed:** `2`
**Marginal direct API cost:** `$0`

## Design

This rerun addressed two limitations in the initial GPT-5.5 pilot:

1. deterministic partial-credit scoring now records all retained and missing anchors by category on both PASS and FAIL;
2. ceiling task `003` was retained as historical evidence but replaced by independently designed hard task `005` before any task-005 model output was observed.

The bounded design was:

```text
3 tasks (002, 004, 005)
× 3 conditions (control, target, negative)
× 3 paired replications
= 27 runs
```

Target loaded only `context-compression`. Negative loaded only `bdi-mental-states`. Control loaded no project-local skill. Every record includes the full partial score, shared scorer/verifier hash, task-fixture hash, repository SHA, and native Codex session ID.

## Aggregate results

| Condition | Passed | Pass rate | Anchors | Retention | Average duration | Average handoff bytes |
|---|---:|---:|---:|---:|---:|---:|
| control | 7/9 | 77.8% | 145/147 | 98.64% | 48,099 ms | 1,754.67 |
| target | 9/9 | 100.0% | 147/147 | 100.00% | 39,503 ms | 1,652.78 |
| negative | 8/9 | 88.9% | 145/147 | 98.64% | 59,432 ms | 1,849.11 |

Target deltas:

| Comparison | Pass-rate delta | Retention delta | Duration delta | Size delta |
|---|---:|---:|---:|---:|
| target vs control | +22.22 pp | +1.3605 pp | −17.87% | −5.81% |
| target vs negative | +11.11 pp | +1.3605 pp | −33.53% | −10.62% |

## Category retention

Target retained every scored anchor in all nine categories:

- intent;
- error;
- root cause;
- artifacts;
- decisions;
- current state;
- risks;
- constraints;
- next actions.

Control lost one `current_state` anchor and one `risks` anchor. Negative lost one `current_state` anchor and one `decisions` anchor. All conditions retained every artifact, constraint, error, intent, next-action, and root-cause anchor.

## Deterministic failures

| Condition | Task | Missing anchors | Retention |
|---|---|---|---:|
| control | 002 | `37 passed, 2 failing` | 13/14 |
| control | 004 | `2,304,118 events` | 15/16 |
| negative | 005 | `20-minute overlap window`; `73 passed, 2 failing` | 17/19 |

No target run failed.

## Paired outcome analysis

Pairing identical task and replication:

| Comparison | Improvements | Regressions | Ties | Exact two-sided p |
|---|---:|---:|---:|---:|
| target vs control | 2 | 0 | 7 | 0.5 |
| target vs negative | 1 | 0 | 8 | 1.0 |

The direction is consistently favorable and there are no observed target regressions, but there are too few discordant pairs for statistical significance.

## Interpretation

The richer metric prevents nearly complete handoffs from being treated as zero and shows that GPT-5.6-sol is near ceiling on these fixtures. Target achieved perfect retention while also producing shorter outputs and lower average wall time, but the absolute retention effect is only 1.36 percentage points.

This run is not directly comparable to the initial GPT-5.5 pilot as a model delta because the scorer, task selection, fixture hashes, and seed changed.

## Decision

Do **not** modify or promote `context-compression` from this pilot.

Before another model sweep:

1. increase the number of independent hard tasks rather than only adding replications;
2. include tasks where compression requires prioritizing conflicting facts under tighter budgets;
3. predeclare difficulty and rubrics before observing outputs;
4. retain paired target/control/negative conditions;
5. treat pass rate, anchor retention, category retention, duration, and output size as separate endpoints;
6. define promotion thresholds and a held-out no-regression set before changing the skill.

Raw runtime outputs remain gitignored. Complete machine-readable copies are stored in the contextlab workspace audit directory.
