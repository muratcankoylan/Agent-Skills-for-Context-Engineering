# Researcher SDK Runner

TypeScript planning and validation package for the router (Stage 2) and effectiveness (Stage 3) benchmarks. It pins and smoke-tests the [Cursor SDK](https://cursor.com/docs/sdk/typescript), but this revision contains no live SDK executor.

See `researcher/benchmarks/PLAN.md` for methodology, hypothesis, statistical design, and reproducibility rules.

## Setup

The pinned SDK requires Node.js 22.13 or newer. CI uses Node 22, and the package metadata declares older runtimes unsupported before a benchmark is scheduled.

```bash
cd researcher/benchmarks/sdk-runner
npm ci --ignore-scripts
```

No credential is required or consumed by the current planners. A later live-activation change must use an explicit `CURSOR_API_KEY`, require Privacy Mode, and prove that ambient SDK authentication cannot select another credential.

## Dependency containment

The SDK and lockfile are exact review inputs. Run `npm audit --omit=dev` during every dependency review and before any live benchmark activation. An audit finding is not silently rewritten with `npm audit fix`; update the SDK or its transport dependency only through a compatibility-tested pull request.

At the 1.0.28 lock review, the upstream transport graph retained unresolved `undici` advisories for which npm reported no compatible fix. CI and routine validation execute typechecking, zero-call import/live-block tests, and bounded `--dry-run` plans; they make no `Agent.prompt` call. Do not describe the dependency tree as vulnerability-free.

Live Stage 2 execution is hard-blocked and the former executor/resume path has been removed. A separate human-merged activation must add a content-addressed run manifest, exclusive crash-safe result writes, strict resume validation, a fresh dependency audit and containment decision, and deterministic fake-executor tests before authorizing one concurrency-1 canary. Do not run multiple benchmark processes against the same SDK state root until that canary is accepted.

## Commands

```bash
npm run typecheck
npm test

npm run router:dry-run       # print plan and cost forecast, no agent calls
npm run router:run           # fail closed; live execution is not implemented

npm run effectiveness:dry-run
npm run effectiveness:run    # fail closed; Stage 3 remains a scaffold
```

Flags shared by both runners:

- `--models <id,id,...>`: subset to specific models (default: `composer-2`).
- `--reps <N>`: replications per condition (default: 3).
- `--max-runs <N>`: hard cap on agent invocations.
- `--max-budget-usd <N>`: estimated cost cap; runner refuses to start if forecast exceeds.
- `--seed <N>`: deterministic shuffling of skill order and tie-breaking.
- `--fixture <path>`: alternate Router JSONL or Stage 3 task-root directory.
- `--dry-run`: print plan, do not call the SDK.

## Output

This revision writes no live result, history, or resume state. Its dry runs print the validated plan and worst-case forecast to standard output. Historical artifacts remain under:

- `researcher/reports/router-history.jsonl` (Stage 2)
- `researcher/reports/effectiveness-history.jsonl` (Stage 3)

Historical per-run raw outputs landed under:

- `researcher/benchmarks/router/results/<timestamp>-<seed>/`
- `researcher/benchmarks/effectiveness/results/<timestamp>-<seed>/`

Both `results/` directories are gitignored. Curated released results live in release notes or a published-results file. They are historical evidence, not resumable inputs to this revision.

## Cost gates

Both planners reject a plan above a fixed in-memory cardinality ceiling before allocating it. The Router forecast reserves up to two explicit format attempts per logical run; the Stage 3 scaffold forecasts one invocation per logical run. These checks are necessary but not sufficient for later live activation.

## Reproducibility

The current dry-run output is diagnostic, not a durable experimental receipt. The activation change must bind exact clean source-tree, fixture, routing-template, skill-catalog, lockfile, runtime, model, seed, plan, and retry-policy digests in one canonical manifest. Every terminal result must bind that manifest and its exact plan item. Malformed, foreign, in-flight, or ambiguous prior state must block automatic resume before any paid call.
