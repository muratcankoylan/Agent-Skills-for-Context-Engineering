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
```

## Commands

```bash
npm run router:dry-run -- --models gpt-5.5 --reps 1 --max-runs 106
npm run router:run -- --models gpt-5.5 --reps 1 --max-runs 106

npm run effectiveness:dry-run -- --models gpt-5.5 --reps 1 --max-runs 6
npm run effectiveness:run -- --models gpt-5.5 --reps 1 --max-runs 6
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

Result directories and runtime histories are gitignored. Every record includes model, condition, duration, final response, verifier evidence, and the native Codex session ID when available.

## Safety

- Live execution refuses to start without a cost/run gate.
- Router retries are included in the worst-case invocation cap.
- Concurrency is bounded.
- Existing records are resumed by default.
- Credentials are managed by native Codex OAuth and are never read or written by the runner.
- The runner never modifies the installed contextlab profile or pinned skill corpus.
