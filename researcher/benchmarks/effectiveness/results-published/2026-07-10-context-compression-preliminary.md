# Context Compression Effectiveness Pilot — Preliminary

**Date:** 2026-07-10
**Status:** preliminary; not sufficient for a skill-effect claim
**Repository commit:** `deaf8830797811551cea9beeaabe03b2c6e27d6c`
**Runtime:** native Codex CLI 0.144+ → Headroom localhost → ChatGPT/Codex OAuth
**Model:** `gpt-5.5`
**Seed:** `1`
**Marginal direct API cost:** `$0`

## Design

The bounded pilot used three independent `context-compression` tasks (`002`, `003`, `004`), three conditions (`control`, `target`, `negative`), and three replications:

```text
3 tasks × 3 conditions × 3 replications = 27 runs
```

Every run used a fresh workspace. The target condition loaded only `context-compression`; negative loaded only `bdi-mental-states`; control loaded no project-local skill. Every record contains verifier and full task-fixture hashes.

## Aggregate results

| Condition | Passed | Pass rate | Average duration |
|---|---:|---:|---:|
| control | 6/9 | 66.7% | 71,790 ms |
| target | 7/9 | 77.8% | 65,492 ms |
| negative | 6/9 | 66.7% | 78,345 ms |

Target minus control:

- pass-rate delta: **+11.1 percentage points**;
- average-duration delta: **−6,298 ms (−8.8%)**.

Negative minus control pass-rate delta: **0.0 percentage points**.

## Per-task results

| Task | Control | Target | Negative | Interpretation |
|---|---:|---:|---:|---|
| 002 migration handoff | 2/3 | 2/3 | 2/3 | No measured pass-rate effect |
| 003 debugging artifact trail | 3/3 | 3/3 | 3/3 | Ceiling effect; task too easy for binary grading |
| 004 early constraint retention | 1/3 | 2/3 | 1/3 | Directionally positive target result on the hardest task |

## Paired outcome analysis

Pairing by identical task and replication:

| Comparison | Improvements | Regressions | Ties | Exact two-sided McNemar p |
|---|---:|---:|---:|---:|
| target vs control | 1 | 0 | 8 | 1.0 |
| negative vs control | 1 | 1 | 7 | 1.0 |

The aggregate direction is favorable, but there is only one discordant target/control pair. The pilot is severely underpowered and does not establish statistical significance.

## Failure modes

All eight failures were deterministic anchor omissions:

- `184 charges`: 3 runs;
- `2,304,118 events`: 4 runs;
- `SCHEMA_COMPATIBILITY_BREAK E1904`: 1 run.

Risk quantities were the dominant compression loss. Task 003 passed under every condition, so its binary verifier contributes no discrimination.

## Decision

Do **not** change or promote the `context-compression` skill from this pilot.

Before another capped model run:

1. report partial anchor retention, not only binary pass/fail;
2. preserve per-category scores for intent, artifacts, decisions, state, risks, constraints, and next actions;
3. replace or harden the ceiling task 003;
4. add more held-out tasks before increasing replications;
5. keep the same target/control/negative pairing and provenance hashes.

Raw runtime results remain gitignored. A complete summary copy and machine-readable analysis are stored in the contextlab workspace audit directory.
