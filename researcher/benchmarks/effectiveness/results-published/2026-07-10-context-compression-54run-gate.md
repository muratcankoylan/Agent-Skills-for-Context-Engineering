# Context Compression Locked 54-Run Gate

**Date:** 2026-07-10
**Status:** `not_eligible`
**Generation repository commit:** `9e09182e68e8bc245b1deada580adc79f7f1bacb`
**Model:** `gpt-5.6-sol`
**Design:** 6 tasks × 3 conditions × 3 paired replications = 54 runs
**Marginal direct API cost:** `$0`

## Grading correction

The first grading attempt used literal substring matching. It incorrectly rejected semantically exact Markdown such as `tenant \`cobalt\`` against the rubric anchor `tenant cobalt`. That grading and its policy output are retained as rejected evidence.

The scorer was corrected to ignore Markdown inline-code markers and insignificant whitespace while retaining exact content matching. All 54 frozen outputs were then regraded offline with zero new model calls. No task, output, threshold, or condition was changed.

## Accepted regraded result

| Condition | Passed | Pass rate | Anchors | Retention | Forbidden violations |
|---|---:|---:|---:|---:|---:|
| control | 15/18 | 83.33% | 306/309 | 99.03% | 0/21 |
| target | 18/18 | 100.00% | 309/309 | 100.00% | 0/21 |
| negative | 16/18 | 88.89% | 307/309 | 99.35% | 0/21 |

Target preserved every required anchor in all nine categories and introduced no superseded fact.

## Locked policy outcome

`not_eligible`

| Gate | Result | Threshold | Status |
|---|---:|---:|---|
| Target retention | 100% | ≥97% | PASS |
| Target − control pass rate | +16.67 pp | ≥+10 pp | PASS |
| Target − negative pass rate | +11.11 pp | ≥+5 pp | PASS |
| Target − control retention | +0.97 pp | ≥+1.0 pp | FAIL |
| Target − negative retention | +0.65 pp | ≥+1.0 pp | FAIL |
| Target/control paired p | 0.25 | ≤0.05 | FAIL |
| Target/negative paired p | 0.5 | ≤0.05 | FAIL |
| Target regressions | 0 | 0 | PASS |
| Target forbidden violations | 0 | 0 | PASS |

Paired outcomes:

- target vs control: 3 improvements, 0 regressions, 15 ties;
- target vs negative: 2 improvements, 0 regressions, 16 ties.

## Decision

Do not modify or promote `context-compression`. The target condition was perfect and directionally superior, but effect-size and significance gates were precommitted and did not pass. Thresholds remain unchanged.

A future study should add independent tasks rather than selectively rerun or drop current tasks. The current frozen outputs and both grading attempts remain available for audit.
