# Stage 3 Context-Compression Acceptance Policy

This policy is locked before the next comparative sweep. It prevents threshold selection after observing results.

Machine-readable source: `acceptance-policy.json`.

## Required design

- model: `gpt-5.6-sol`;
- at least 6 independent held-out tasks;
- conditions: control, target, and negative;
- at least 3 paired replications per task and condition;
- at least 54 completed scored runs;
- fresh workspaces and matching repository, task-fixture, verifier, and scorer hashes.

## Primary gates

All gates must pass:

| Gate | Threshold |
|---|---:|
| Target anchor retention | ≥ 97% |
| Target − control retention | ≥ +1.0 pp |
| Target − negative retention | ≥ +1.0 pp |
| Target − control pass rate | ≥ +10.0 pp |
| Target − negative pass rate | ≥ +5.0 pp |
| Exact paired target/control p | ≤ 0.05 |
| Exact paired target/negative p | ≤ 0.05 |
| Target pairwise regressions | 0 |
| Target forbidden stale-fact violations | 0 |

The exact paired test is the two-sided sign/McNemar test over identical task and replication keys. A run pair is an improvement when target passes and the comparator fails, a regression for the reverse, and otherwise a tie.

## Category gates

For every scored category:

- target retention must be at least 95%;
- target may not trail control by more than 1.0 pp;
- target may not trail negative by more than 1.0 pp.

Duration and output size are secondary endpoints. They are reported but cannot rescue a quality-gate failure.

## Decision boundary

Passing all automated gates creates a **promotion candidate**, not an accepted skill change. Human review, held-out no-regression evidence, and an explicit promotion decision remain mandatory.

The following are forbidden:

- modifying `context-compression` before the policy passes;
- changing thresholds after a live sweep begins;
- dropping failed tasks or replications after observing results;
- replacing deterministic evidence with an LLM judge;
- claiming cross-model improvement from runs with different fixtures, seeds, or scorer versions.
