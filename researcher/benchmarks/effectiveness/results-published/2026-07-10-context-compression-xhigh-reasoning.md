# Context Compression XHigh Reasoning Comparison

**Date:** 2026-07-10
**Status:** `published_evidence_not_promotion`
**Baseline evidence:** `results-published/2026-07-10-context-compression-54run-gate.md`
**Model:** `gpt-5.6-sol`
**Compared factor:** Codex `model_reasoning_effort=medium` versus `xhigh`
**Design:** 6 tasks x 2 conditions x 3 paired replications = 36 xhigh runs, compared against the accepted offline-regraded medium gate records for the same tasks, conditions, and reps.
**Marginal direct API cost:** `$0` through the subscription route

## Result

The xhigh rerun completed the three previously missing model calls and produced no runtime errors. It does not improve on the accepted medium gate evidence.

| Effort | Condition | Passed | Pass rate | Anchors | Retention | Avg duration |
|---|---|---:|---:|---:|---:|---:|
| medium | control | 15/18 | 83.33% | 306/309 | 99.03% | 34,706 ms |
| medium | target | 18/18 | 100.00% | 309/309 | 100.00% | 35,799 ms |
| xhigh | control | 15/18 | 83.33% | 306/309 | 99.03% | 85,553 ms |
| xhigh | target | 17/18 | 94.44% | 308/309 | 99.68% | 55,948 ms |

No run retained a forbidden superseded fact.

## Paired comparison

| Comparison | Complete pairs | Improvements | Regressions | Ties | Exact two-sided p | Mean retention delta | Median duration ratio |
|---|---:|---:|---:|---:|---:|---:|---:|
| xhigh control vs medium control | 18/18 | 3 | 3 | 12 | 1.0 | -0.0167 pp | 2.5083 |
| xhigh target vs medium target | 18/18 | 0 | 1 | 17 | 1.0 | -0.3089 pp | 1.4766 |
| xhigh target vs xhigh control | 18/18 | 2 | 0 | 16 | 0.5 | +0.6178 pp | 0.7295 |

The target skill still helps within xhigh, but xhigh does not beat the accepted medium target run. The only medium-to-xhigh target delta is a regression on task `008`, rep `0`, missing the current-state anchor `76 passed, 2 failing`.

## XHigh verifier failures

| Task | Condition | Rep | Missing anchor |
|---|---|---:|---|
| 006 | control | 0 | `68 passed, 2 failing` |
| 006 | control | 2 | `REPLICA_TIMELINE_DIVERGED E8206` |
| 008 | control | 0 | `76 passed, 2 failing` |
| 008 | target | 0 | `76 passed, 2 failing` |

## Decision

Do not promote xhigh as a better benchmark setting for this context-compression gate. The accepted medium gate remains the canonical promotion evidence. Xhigh is valid as an execution mode, but in this sweep it was slower and slightly worse on the target condition.

Do not modify `context-compression` based on the xhigh result.

## Validation

Deterministic no-API gates were run after publishing the xhigh evidence. `agentskills` was provided by a temporary `skills-ref` venv at `/tmp/contextlab-skills-ref-venv`, while repository Python checks were executed with Hermes' Python to avoid dependency skew.

| Gate | Result |
|---|---|
| `npm run typecheck` | PASS |
| `npm test` | PASS: 6 Node runner tests + 12 Python scorer tests |
| `python3 -m unittest discover -s researcher/scripts/tests -p 'test_*.py'` | PASS: 29 tests |
| `validate_platform_compat.py --require-reference-validator` | PASS: 16 skills, 4 local install layouts |
| `validate_repo.py --strict` | PASS: 0 errors, 0 warnings, 16 skills |
| `skill_health.py --strict --no-history` | PASS: corpus 0.9172, flagged 0, 16 skills |
| `check_activation_cases.py` | PASS: 21 cases, 0 failures |
| `run_benchmarks.py` | PASS: 3 checks, 0 failures, 7 scenarios |

## Evidence

Raw and derived artifacts:

- xhigh summary: `/home/hermesadmin/work/contextlab/changes/codex-runner/researcher/benchmarks/effectiveness/results/2026-07-10-3-codex-4ba69074/summary.json`
- accepted medium regraded summary: `/home/hermesadmin/work/contextlab/audits/2026-07-10-codex-migration/context-compression-54run-regraded-summary.json`
- comparison JSON: `/home/hermesadmin/work/contextlab/audits/2026-07-10-codex-migration/context-compression-medium-vs-xhigh-comparison.json`

Commands:

```bash
npm run effectiveness:run -- --models gpt-5.6-sol --task-ids 002,004,005,006,007,008 --conditions control,target --reps 3 --seed 3 --reasoning-effort xhigh --max-runs 3 --concurrency 1
python3 researcher/benchmarks/effectiveness/compare_reasoning.py /home/hermesadmin/work/contextlab/audits/2026-07-10-codex-migration/context-compression-54run-regraded-summary.json /home/hermesadmin/work/contextlab/changes/codex-runner/researcher/benchmarks/effectiveness/results/2026-07-10-3-codex-4ba69074/summary.json --output /home/hermesadmin/work/contextlab/audits/2026-07-10-codex-migration/context-compression-medium-vs-xhigh-comparison.json
```
