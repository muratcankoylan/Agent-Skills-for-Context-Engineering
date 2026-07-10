# Researcher Codex Runner

TypeScript runner for Stage 2 routing and Stage 3 effectiveness benchmarks. It executes the production path used by this deployment:

```text
fixture -> native Codex CLI -> Headroom localhost -> OpenAI ChatGPT/Codex OAuth
```

The runner does not require `CURSOR_API_KEY`, does not depend on `@cursor/sdk`, and has no separately billed API dependency. Historical Cursor-generated benchmark reports remain valid provenance records, but new runs use this runtime.

See `researcher/benchmarks/PLAN.md` for methodology, statistical design, and acceptance rules.

## Prerequisites

- `codex` CLI 0.144 or newer is available on `PATH`;
- `/home/hermesadmin/.codex/config.toml` selects the `headroom` model provider;
- `/home/hermesadmin/.codex/auth.json` contains a valid ChatGPT/Codex OAuth session;
- Headroom is listening on `127.0.0.1:8787`.

The runner explicitly sets `HOME=/home/hermesadmin` and `CODEX_HOME=/home/hermesadmin/.codex`. This is required when invoked from an isolated Hermes profile whose own `HOME` points at `<profile>/home`.

```bash
cd researcher/benchmarks/codex-runner
npm install
npm run typecheck
npm test
```

## Commands

```bash
npm run router:dry-run -- --models gpt-5.5 --reps 1 --max-runs 106
npm run router:run -- --models gpt-5.5 --reps 1 --max-runs 106

npm run effectiveness:dry-run -- --models gpt-5.5 --reps 1 --max-runs 6
npm run effectiveness:run -- --models gpt-5.5 --reps 1 --max-runs 6

# Locked six-task promotion-gate plan. Live 54-run execution requires explicit approval.
npm run effectiveness:dry-run -- --models gpt-5.6-sol --task-ids 002,004,005,006,007,008 --conditions control,target,negative --reps 3 --max-runs 54
```

## Shared flags

- `--models <id,id,...>`: native Codex model IDs; default `gpt-5.5`.
- `--reps <N>`: replications per condition; default 3.
- `--max-runs <N>`: mandatory hard cap on live invocations.
- `--max-budget-usd <N>`: optional marginal-cost gate. Current subscription route forecasts `$0`; the hard run cap remains mandatory operational policy.
- `--seed <N>`: deterministic plan and skill-order seed.
- `--fixture <path>`: alternate fixture.
- `--dry-run`: print the plan without model calls.
- `--concurrency <N>`: bounded Codex subprocess concurrency; default 1.
- `--no-resume`: ignore saved per-run records and execute again.

Effectiveness-only filters:

- `--task-ids <id,id,...>`: run only the listed task IDs; unknown IDs fail with the available IDs.
- `--conditions <name,name,...>`: run only the listed conditions; accepted values are `control`, `target`, `negative`, `full`, `target_plus_one`, and `target_plus_unrelated`.

CSV values are trimmed and deduplicated. The router rejects these effectiveness-only flags instead of silently ignoring them.

## Isolation

Router runs use:

```text
codex -a never -s read-only -C <isolated-temp> exec --ephemeral --ignore-rules
```

No skill body is loaded; frontmatter descriptions in the routing prompt are the only routing signal.

Effectiveness runs in fresh fixture-only workspaces. The deployment container blocks Codex's nested `bwrap` namespace, so these runs use `danger-full-access` with an absolute workspace-only prompt. The runner copies only the condition's skills into `.codex/skills/`; control contains none. Final output is staged in `.runner/final.txt`, and `verify.sh` is executed deterministically. Do not use this mode on untrusted tasks or repositories.

## Conditions

- `control`: no skills;
- `target`: target skill only;
- `negative`: irrelevant skill only;
- `full`: all corpus skills;
- `target_plus_one`: target plus related skill;
- `target_plus_unrelated`: target plus unrelated skill.

## Output and resume

Per-run records are written under:

- `researcher/benchmarks/router/results/<date>-<seed>/`;
- `researcher/benchmarks/effectiveness/results/<date>-<seed>-codex/`.

History summaries append to:

- `researcher/reports/router-history.jsonl`;
- `researcher/reports/effectiveness-history.jsonl`.

Result directories and runtime histories are gitignored. Every record includes model, condition, duration, final response, verifier evidence, verifier SHA, full task-fixture SHA, partial anchor/category score when available, and the native Codex session ID.

Filtered selections use a deterministic selection-hash suffix in the results directory, so their summaries cannot overwrite or absorb an unfiltered run. Resume accepts only records in the current run plan whose verifier and task-fixture hashes still match; stale records are rerun. Summaries report aggregate and per-task condition metrics, average duration, anchor retention, and category retention.

## Safety

- Live execution refuses to start without a cost/run gate.
- Router retries are included in the worst-case invocation cap.
- Concurrency is bounded.
- Existing records are resumed by default.
- Credentials are managed by native Codex OAuth and are never read or written by the runner.
- The runner never modifies the installed contextlab profile or pinned skill corpus.
