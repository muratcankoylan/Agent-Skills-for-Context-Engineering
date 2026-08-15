# Effectiveness Benchmark (Stage 3)

Defines deterministic task fixtures for measuring whether loading a relevant skill improves verified task outcomes or efficiency relative to controls. See `researcher/benchmarks/PLAN.md` for the experimental design.

Stage 3 is currently a zero-call, dry-run-only scaffold. The planner validates the task set and constructs a bounded task x condition x model x replication plan. It does not create workspaces, copy skills, invoke the SDK, run task verifiers, collect transcripts or diffs, write results, or resume prior state. A command without `--dry-run` exits before those operations.

## Task contract

```text
researcher/benchmarks/effectiveness/tasks/<NNN>-<slug>/
  README.md         # human-readable task intent and grading criteria
  task.md           # future agent prompt
  metadata.json     # task identity, skill controls, category, and difficulty
  starting/         # non-empty workspace seed for a future isolated run
  verify.sh         # executable deterministic verifier for future activation
```

`metadata.json` uses this shape:

```json
{
  "id": "001",
  "slug": "filesystem-context-offload",
  "target_skill": "filesystem-context",
  "irrelevant_skill": "bdi-mental-states",
  "category": "context-management",
  "difficulty": "easy",
  "notes": "Optional task rationale."
}
```

The directory name must match the three-digit `id` and canonical slug. `target_skill` and `irrelevant_skill` must be distinct registered skill identifiers; sentinel values such as `"none"` are not supported by the current planner. Difficulty is one of `easy`, `medium`, or `hard`.

## Planned conditions

Every accepted task currently contributes these six plan identities:

| Condition | Intended future comparison |
| --- | --- |
| `control` | no project skill loaded |
| `target` | target skill only |
| `negative` | irrelevant skill only |
| `full` | reviewed full skill set |
| `target_plus_one` | target plus a reviewed related skill |
| `target_plus_unrelated` | target plus a reviewed unrelated skill |

These are plan labels only in this revision. Future activation must define and freeze the exact skill selection for every condition, including the two interaction controls; the current planner does not construct those workspaces.

## Current command

From the SDK runner:

```bash
cd researcher/benchmarks/sdk-runner
npm ci --ignore-scripts
npm run effectiveness:dry-run -- --models gpt-5.5 --reps 1 --max-runs 12 --max-budget-usd 2
```

The dry run rejects malformed task directories and metadata, unknown or duplicate skill controls, non-executable verifiers, and plans above the invocation, budget, or in-memory cardinality ceilings. It makes no SDK call and writes no benchmark result or resume state.

`npm run effectiveness:run` is an intentional fail-closed check, not an execution command.

## Adding a task fixture

1. Create a `<NNN>-<slug>` directory under `tasks/`, using the existing task as the structural example.
2. Write a self-contained `task.md` and a deterministic, executable `verify.sh`.
3. Provide a non-empty `starting/` directory without relying on ambient workspace state.
4. Set distinct registered target and irrelevant skills in `metadata.json`.
5. Run `npm run effectiveness:dry-run` with explicit cost and invocation ceilings.

Fixture validation is not evidence that the skill improves outcomes; that claim requires an activated, preregistered experiment.

## Future activation gate

Live execution requires a separate reviewed and human-merged change. Before one concurrency-1 canary is authorized, that change must provide all of the following:

1. A canonical, content-addressed manifest binding the clean source tree, exact task files and starting tree, condition-to-skill mapping, package lock, runtime and isolation policy, model set, replications, seed, complete plan, verifier digest, and retry policy.
2. A fresh isolated workspace per plan item, with only the condition's frozen skill set and settings sources, an explicit task-derived tool allowlist, and no ambient project configuration.
3. An injected executor and workspace boundary with deterministic tests for isolation, tool and settings selection, verifier invocation, call counts, retries, failures, and cleanup.
4. An explicit credential with confirmed Privacy Mode, SDK retries disabled, runner-owned cost accounting, and a fresh dependency audit with an explicit containment decision for unresolved production advisories.
5. Exclusive manifest-bound receipts for SDK outcomes, verifier output, usage, duration, transcript, and workspace diff. Malformed, foreign, ambiguous, or in-flight state must block automatic resume before a paid call.

No parallel or preregistered sweep is authorized until the canary evidence and task-isolation behavior are reviewed and accepted.
