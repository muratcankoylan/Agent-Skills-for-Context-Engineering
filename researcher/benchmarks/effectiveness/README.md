# Effectiveness Benchmark (Stage 3)

Real agent tasks executed through native Codex CLI, Headroom, and OpenAI ChatGPT/Codex OAuth. Each task runs under controlled skill-loading conditions; differences in deterministic success, behavior signals, and wall time measure skill effects.

See `researcher/benchmarks/PLAN.md`. The current preliminary task set is under `tasks/`:

- `001-filesystem-context-offload/`: retrieval and scratch-offload smoke fixture;
- `002-context-compression-handoff/`: bounded migration handoff with exact artifact and decision anchors;
- `003-debugging-artifact-trail/`: retained ceiling fixture; excluded from the next comparative pilot;
- `004-migration-constraint-retention/`: held-out early-constraint and late-decision retention;
- `005-security-rotation-handoff/`: independent hard fixture with a predeclared 1,800-byte budget and partial-credit rubric;
- `006-failover-supersession-handoff/`: database failover with superseded replica, lag, and tenant decisions;
- `007-legal-hold-retention-handoff/`: legal-hold retention with superseded expiry and pilot values;
- `008-offline-auth-rollout-handoff/`: offline-auth rollout with superseded rollout percentage and cohort.

## Task layout

```text
researcher/benchmarks/effectiveness/tasks/<NNN>-<slug>/
  README.md
  task.md
  metadata.json
  rubric.json      # partial-credit anchors and categories (handoff tasks)
  starting/
  verify.sh
```

`metadata.json`:

```json
{
  "id": "001",
  "slug": "filesystem-context-offload",
  "target_skill": "filesystem-context",
  "irrelevant_skill": "bdi-mental-states",
  "related_skill": "context-optimization",
  "unrelated_skill": "bdi-mental-states",
  "category": "context-management",
  "difficulty": "easy"
}
```

## Conditions

| Condition | Project-local Codex skills |
|---|---|
| `control` | none |
| `target` | `target_skill` |
| `negative` | `irrelevant_skill` |
| `full` | all corpus skills |
| `target_plus_one` | target plus `related_skill` |
| `target_plus_unrelated` | target plus `unrelated_skill` |

All runs use a fresh workspace. The condition's skills are copied explicitly into `.codex/skills/`; control has no project-local skills. Global Codex plugins and hooks are disabled for benchmark execution.

## Execution

The runner:

1. copies `starting/` into a fresh per-condition workspace;
2. prepends the absolute workspace path to the task prompt;
3. invokes native `codex exec` through the configured Headroom route; this container requires `danger-full-access` because nested `bwrap` namespaces are unavailable, so only fixture-controlled tasks are permitted;
4. writes final text to `.runner/final.txt`;
5. executes `verify.sh` inside the workspace;
6. records verifier output, behavior notes, duration, condition, skills, and session ID;
7. writes an aggregate `summary.json` and append-only history entry.

## Running

```bash
cd researcher/benchmarks/codex-runner
npm install
npm run typecheck
npm test
npm run effectiveness:dry-run -- --models gpt-5.5 --reps 1 --max-runs 12
npm run effectiveness:run -- --models gpt-5.5 --reps 1 --max-runs 12

# Locked six-task promotion-gate dry-run. Live execution requires explicit approval for the 54-run cap.
npm run effectiveness:dry-run -- --models gpt-5.6-sol --task-ids 002,004,005,006,007,008 --conditions control,target,negative --reps 3 --max-runs 54
```

Live execution requires an explicit hard cap. Resume is enabled by default.

## Reporting

The summary reports both corpus-level and per-task metrics. For each selected condition it includes:

- total runs and deterministic pass rate;
- average wall-clock duration;
- scored-run count;
- anchors found / total and aggregate anchor-retention rate;
- per-category retention for intent, error, root cause, artifacts, decisions, current state, risks, constraints, and next actions;
- scratch-use count and rate when a task emits that signal.

Handoff verifiers write `.runner/score.json` on both PASS and FAIL. This preserves partial credit and all missing anchors instead of collapsing a nearly complete handoff to a binary zero. Rubrics may also declare forbidden stale facts; retaining a superseded value records a violation and fails deterministically even when every positive anchor is present. Each run record stores the full score, `verifier_sha`, `task_fixture_sha`, and the verifier failure line when present. The verifier SHA includes the shared scorer implementation, so scorer changes invalidate stale resume records.

Promotion criteria are locked in `acceptance-policy.json` and documented in `ACCEPTANCE.md`. `evaluate_promotion.py` can emit only `promotion_candidate` or `not_eligible`; human review is always required.

The current Hermes CLI does not expose provider-normalized token usage in quiet mode, so request count and wall time remain the portable cost proxies. Do not fabricate token counts.

Published reports:

- `results-published/2026-07-10-context-compression-preliminary.md`: initial GPT-5.5 binary pilot; direction positive but underpowered.
- `results-published/2026-07-10-context-compression-gpt56-partial.md`: GPT-5.6-sol partial-credit rerun with ceiling task replacement; target retained 147/147 anchors, but paired significance remained insufficient for promotion.
- `results-published/2026-07-10-context-compression-54run-gate.md`: locked six-task gate; target retained 309/309 with zero regressions, but precommitted effect-size and significance thresholds returned `not_eligible`.
- `results-published/2026-07-10-context-compression-xhigh-reasoning.md`: xhigh reasoning comparison after the three missing calls were completed; xhigh produced no runtime errors but did not beat the accepted medium gate, so the medium gate remains canonical promotion evidence.

## Adding a task

1. Copy the canonical directory layout.
2. Make `task.md` self-contained and freeze task difficulty before model execution.
3. Define `rubric.json` with categorized anchors, source SHA-256, heading floor, and byte budget.
4. Use the shared `verify_handoff.py` wrapper for handoff tasks; do not duplicate scoring logic.
5. Test a complete golden handoff and at least one partial/negative handoff deterministically.
6. Specify target, irrelevant, related, and unrelated skills honestly.
7. Run typecheck, `npm test`, and dry-run.
8. Start with three paired conditions and a hard cap before composition conditions or larger sweeps.

For a negative-control task where no skill should help, set `target_skill` and `irrelevant_skill` to `none`; the runner limits the condition set accordingly.
