# Effectiveness Benchmark (Stage 3)

Real agent tasks executed via the Cursor SDK. Each task is run under multiple skill-loading conditions; the difference in outcome quality, token cost, and wall time is the skill's measured effect size.

See `researcher/benchmarks/PLAN.md` for methodology and `researcher/benchmarks/effectiveness/tasks/001-filesystem-context-offload/` for the canonical task template.

## Task layout

```
researcher/benchmarks/effectiveness/tasks/<NNN>-<slug>/
  README.md         # human-readable task description and grading criteria
  task.md           # the exact prompt given to the agent
  metadata.json     # machine-readable metadata (target_skill, difficulty, category)
  starting/         # workspace seed copied into a temp directory before each run
  verify.sh         # deterministic check returning exit 0 on success
```

`metadata.json` shape:

```json
{
  "id": "001",
  "slug": "filesystem-context-offload",
  "target_skill": "filesystem-context",
  "irrelevant_skill": "bdi-mental-states",
  "category": "context-management",
  "difficulty": "easy",
  "notes": "Optional rationale for picking this task."
}
```

## Conditions

For each task, six conditions are evaluated per model:

| Condition | settingSources | Skills present in `.cursor/skills/` |
| --- | --- | --- |
| `control` | `[]` | none (no skills loaded) |
| `target` | `["project"]` | only `target_skill` |
| `negative` | `["project"]` | only `irrelevant_skill` (negative control) |
| `full` | `["project"]` | all currently published skills |
| `target_plus_one` | `["project"]` | `target_skill` plus one related skill |
| `target_plus_unrelated` | `["project"]` | `target_skill` plus one unrelated skill (interaction control) |

The runner builds a fresh task workspace per (task, condition, model, replication) by copying `starting/` to a temp dir and then placing only the in-scope skills into `.cursor/skills/`.

## Reporting

After each run the runner calls `verify.sh`. Exit code 0 means the task succeeded. Tokens are read from `run.conversation()` and durationMs from the SDK result. The runner persists:

- per-condition raw result JSON
- workspace diff before/after
- verify.sh stdout/stderr
- summary.json with per-task per-condition aggregates

Aggregated results land in `researcher/reports/effectiveness-history.jsonl` as a single line per benchmark sweep.

## Adding a task

1. Create a new directory under `tasks/` with a 3-digit ID and slug.
2. Copy the structure from `001-filesystem-context-offload/`.
3. Write `task.md` so the agent has a self-contained prompt referencing the workspace.
4. Write `verify.sh` so it can be run inside any temp directory and exits 0 on success.
5. Fill `metadata.json` honestly: pick a real `irrelevant_skill` that genuinely should not help.
6. Validate by running `npm run effectiveness:dry-run`.

Negative-control tasks (where no skill should help) live alongside positive tasks. Set `target_skill: "none"` and `irrelevant_skill: "none"` to mark them; the runner skips the `target` and `target_plus_*` conditions and runs only `control`, `full`, and a sanity check.
