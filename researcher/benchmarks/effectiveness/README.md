# Effectiveness Benchmark (Stage 3)

Real agent tasks executed through native Codex CLI, Headroom, and OpenAI ChatGPT/Codex OAuth. Each task runs under controlled skill-loading conditions; differences in deterministic success, behavior signals, and wall time measure skill effects.

See `researcher/benchmarks/PLAN.md`. The current preliminary task set is under `tasks/`:

- `001-filesystem-context-offload/`: retrieval and scratch-offload smoke fixture;
- `002-context-compression-handoff/`: bounded migration handoff with exact artifact and decision anchors;
- `003-debugging-artifact-trail/`: held-out debugging/error/artifact trail;
- `004-migration-constraint-retention/`: held-out early-constraint and late-decision retention.

## Task layout

```text
researcher/benchmarks/effectiveness/tasks/<NNN>-<slug>/
  README.md
  task.md
  metadata.json
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

# Three-task held-out pilot with three baseline conditions and three replications.
npm run effectiveness:dry-run -- --models gpt-5.5 --task-ids 002,003,004 --conditions control,target,negative --reps 3 --max-runs 27
```

Live execution requires an explicit hard cap. Resume is enabled by default.

## Reporting

The summary reports both corpus-level and per-task metrics. For each selected condition it includes:

- total runs;
- deterministic passes;
- pass rate;
- scratch-use count and rate when the verifier emits that signal;
- average wall-clock duration.

Each run record stores `verifier_sha`, `task_fixture_sha`, and the first verifier failure line when present. Filtered runs use isolated selection-hash result directories, and resume ignores stale records when either hash changes.

The current Hermes CLI does not expose provider-normalized token usage in quiet mode, so request count and wall time remain the portable cost proxies. Do not fabricate token counts.

Latest preliminary report: `results-published/2026-07-10-context-compression-preliminary.md`. It records a 27-run target/control/negative pilot; the direction is positive but underpowered, so it does not justify changing or promoting the skill.

## Adding a task

1. Copy the canonical directory layout.
2. Make `task.md` self-contained.
3. Make `verify.sh` deterministic and portable to any temporary workspace.
4. Specify target, irrelevant, related, and unrelated skills honestly.
5. Run typecheck and dry-run.
6. Start with one replication and a hard cap before any larger sweep.

For a negative-control task where no skill should help, set `target_skill` and `irrelevant_skill` to `none`; the runner limits the condition set accordingly.
