# AGENTS.md

Workspace memory for agents collaborating on this repository. Keep entries durable and broadly applicable; one-off task state belongs in chat or in a run thread, not here.

## Learned User Preferences

- For autonomous research and repo-improvement work in this workspace, prefer proceeding through concrete research loops, subagents, validation, and edits when the scope is clear rather than asking broad process questions.
- Avoid stale regex or keyword-list heuristics in skills and scripts; prefer mechanism-level criteria, rubrics, and evidence-backed validation.
- Never push to GitHub or merge a PR without explicit user approval. Preparing branches, commits, and PRs is permitted only when the user has approved that specific action.
- Tone is technical CTO: direct, no marketing language, no exclamation marks, no emojis, no em dashes. State trade-offs and complexity upfront.
- When the scope spans multiple architectural decisions or irreversible changes, propose a plan first instead of executing.
- For benchmarks and evaluation work, hold to research-paper-grade methodology (statistical discipline, bias mitigation, ablations, reproducibility) over speed. Don't rush.

## Learned Workspace Facts

- This repo is an autonomous research-to-skill organization. External AI research is curated through rubrics and distilled into context-engineering and harness-engineering skill updates.
- `researcher/` is repo-native and file-based so agents can resume, audit, validate, and prepare PR-ready skill changes without a hosted scheduler.
- Per-run state lives in `researcher/runs/<run-id>/run-state.json` with explicit transitions (`initialized -> retrieved -> evaluated -> proposed -> novelty_checked -> validated -> pr_ready -> closed`). Use `research_loop.py` subcommands to advance state, never hand-edit `run-state.json`.
- Repo health (`validate_repo.py`) and per-run readiness (`validate_run.py`) are different questions. CI runs `validate_platform_compat.py --require-reference-validator`, `validate_repo.py --strict`, `skill_health.py --strict --no-history`, `run_benchmarks.py`, and `check_activation_cases.py` on every PR via `.github/workflows/validate.yml`.
- The mechanism registry (`researcher/mechanisms/registry.jsonl`) is the encyclopedia backbone. Promotion is gated by `research_loop.py promote-mechanisms` with a recorded reviewer; ledgers live under `researcher/mechanisms/ledgers/`.
- Claim provenance for numeric or volatile claims lives in `researcher/claims/index.jsonl`. Add an entry for any new benchmark or volatility-sensitive claim.
- The corpus index (`researcher/corpus/index.json`) is the machine-readable map of skills, activation scenarios, mechanisms, and claims. Update it when adding or restructuring skills.
- The continuous loop (`researcher/scripts/loop_*.py`) runs from launchd via `researcher/orchestration/launchd/`. It never invokes paid LLMs; HTTP retrieval is stdlib-only with a 1.5 MB cap and a 30-second timeout.
- Runtime state is not committed: `researcher/queue/*.jsonl`, `researcher/queue/.locks/`, `researcher/reports/{logs,snapshots,loop-events.jsonl,loop-failures.jsonl,status.md,parked-review.md}`, and `researcher/runs/*/` are gitignored. The seed run `20260515-035228-executable-autonomous-research-frameworks` is the only committed run; it is closed as `reference-only` and serves as a worked example.
- The current published version is 2.3.0 across `.claude-plugin/marketplace.json`, `.plugin/plugin.json`, and root `SKILL.md`. There are 15 skills (latent-briefing covers KV cache sharing between agents).
- Detailed lessons from building the researcher OS live in `researcher/insights/auto-research-experiment.md` (engineering rationale) and `researcher/insights/how-we-built-this.md` (project narrative and sharing templates); read both before extending the harness or writing release-facing prose.
- Benchmarks are staged in `researcher/benchmarks/`: Stage 0 deterministic harness (shipped), Stage 1 per-skill health via `researcher/scripts/skill_health.py` (shipped; output `researcher/reports/skill-health.json` is gitignored), Stage 2 router (shipped; results in `researcher/benchmarks/router/results-published/`), Stage 3 effectiveness (scaffolded, one task built), Stage 4 composition (future). `researcher/benchmarks/PLAN.md` is the methodology source of truth.
- Current corpus-hardening baseline: 16 accepted mechanisms, 12 provenance-tracked claims, 19 activation cases, and strict skill-health score 0.9117 with 0 flagged skills. Do not describe a skill improvement as complete unless the prose, mechanism registry, claim index, corpus index, activation fixtures, and validators all agree.
- Benchmark execution uses the Cursor SDK runner at `researcher/benchmarks/sdk-runner/` (TypeScript, `@cursor/sdk` 1.0.13). The runner supports `--concurrency N`, `--no-resume`, per-run progress logging, format-failure retry, and worst-case retry-aware cost forecasting; default behavior is to resume by skipping plan items that already have result files. Result artifacts under `researcher/benchmarks/{router,effectiveness}/results/` and history JSONLs (`router-history.jsonl`, `effectiveness-history.jsonl`) are gitignored.
- Published Stage 2 router-benchmark results: `researcher/benchmarks/router/results-published/2026-05-15.md` (baseline), `researcher/benchmarks/router/results-published/2026-05-15-v2.md` (post-rewrite with delta-vs-baseline table), and `researcher/benchmarks/router/results-published/2026-05-19.md` (post-corpus-hardening validation: 600/600 usable records, 0 format failures, top-1 Gemini 0.920 / Composer 0.913 / GPT-5.5 0.913 / Claude Opus 4.7 0.840). Headline finding: targeted description rewrites moved `context-fundamentals` top-1 by +23.4pp and `project-development` top-1 to 1.000; corpus-wide hardening did not cause broad routing collapse.

## Repository Operating Defaults

- Deterministic checks before model judges. Always run `validate_platform_compat.py --require-reference-validator` and `validate_repo.py --strict` before claiming a skill-format or packaging change is complete.
- Adversarial benchmarks before declaring the harness safe. Add a scenario when a new failure mode is discovered.
- Append-only ledgers for accepted and rejected mechanisms so future agents do not rediscover failed paths.
- Atomic writes (`tempfile` + `os.replace`) and `fcntl` locks for any shared file the loop touches.
- Live execution is the highest-signal validation for orchestration code; smoke-test changes against the actual loop before declaring them safe.
- Cursor SDK is the only paid-API surface allowed for benchmarks. Privacy Mode required, `apiKey` passed explicitly per call, never `settingSources: "all"` in benchmarks (use `[]` for control, `["project"]` with a curated `.cursor/skills/` for ablation). Cost gates (`--max-runs`, `--max-budget-usd`, or `--dry-run`) must be set before any SDK call.
- Description quality is measurable. When changing skill activation descriptions, re-run the router benchmark with the same seed and fixture and publish the delta. Aggregate accuracy is a misleading unit; per-skill effect sizes and the confusion matrix are the right view.
- A skill is a multi-surface artifact. Changing the frontmatter `description` is not enough; the SKILL.md body `When to Activate` and `Integration` sections must be audited the same day so the body does not contradict the description that routed the agent to it. The router benchmark only sees descriptions (`settingSources: []`) and cannot catch body inconsistencies; only Stage 3 effectiveness benchmarks (which actually load skill bodies) measure body-alignment impact.
- Any runner that calls a paid API in a loop must have three features before execution: bounded parallelism via `--concurrency`, resume capability via results-folder scan, and per-run progress logging that surfaces stalls inside one call's duration.
- API keys provided in chat should be considered exposed; rotate immediately after use. Runner enforces this via `apiKeyFingerprint()` which only logs the last 4 characters.
