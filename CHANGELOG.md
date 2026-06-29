# Changelog

All notable changes to this project are documented here. Versions follow semantic versioning where practical, with skill content treated as data.

## [Unreleased]

### Fixed

- **Cross-platform YAML frontmatter**: 11 of 15 published skills used unquoted `description` values containing colons, which strict YAML parsers (Cursor, Claude Code, Codex, Agent Skills validators) reject. All skill descriptions now use YAML-safe quoting; `memory-systems` no longer uses a folded block scalar that repo validators misread as `">"`.
- **Shared frontmatter parser**: added `researcher/scripts/skill_frontmatter.py` and wired it into `validate_repo.py`, `skill_health.py`, `check_activation_cases.py`, and `compare_skill_revisions.py`. CI installs `pyyaml` for deterministic strict parsing. The parser handles LF/CRLF line endings, UTF-8 BOM, quoted scalars, and folded block scalars, and rejects empty, too-short, or indicator-only descriptions.
- **Unit tests**: added `researcher/scripts/tests/test_skill_frontmatter.py` (19 tests) covering parser edge cases, a strict-YAML regression guard for the unquoted-colon bug, format/parse round-trips, and a corpus integration test asserting every published skill parses clean. Wired into CI before the strict repo gate.
- **Example skills**: quoted the `description` fields in `examples/digital-brain-skill/SKILL.md` and `examples/book-sft-pipeline/SKILL.md`, which had the same unquoted-colon YAML hazard developers would copy.
- **Manifest validation**: `validate_repo.py --strict` now checks that `.plugin/plugin.json` and `.claude-plugin/marketplace.json` name the same bundled plugin and that Open Plugins `skills` discovery resolves to the same 15 published skills as the repository.
- **Platform compatibility gate**: added `researcher/scripts/validate_platform_compat.py`, which validates the published skills with the upstream `agentskills` CLI from `skills-ref`, checks Open Plugins and Claude marketplace discovery parity, and simulates directory-copy installs for `.cursor/skills`, `.claude/skills`, `.codex/skills`, and `.agents/skills`.
- **Platform install docs**: README now documents directory-based install paths for Cursor (`.cursor/skills/`), Claude Code (`.claude/skills/`), and Codex (`.codex/skills/`) instead of the broken flat-file `.md` pattern.
- **Open Plugins discovery**: `.plugin/plugin.json` now declares `"skills": "./skills/"`. The repository does not commit `.agents/skills` or `.cursor/skills` symlinks because symlinks are fragile on Windows and in plugin packaging.

## [2.3.0] - 2026-05-15

First release with measured benchmark results across four frontier models, closing the loop from "we wrote skill descriptions" to "we proved they route correctly."

### Added

#### Stage 2 router benchmark, executed end-to-end

- 600 of 600 runs completed across `composer-2`, `claude-opus-4-7`, `gpt-5.5`, `gemini-3.1-pro` at 3 replications per (prompt, model). Initial v2.2.0 baseline at `researcher/benchmarks/router/results-published/2026-05-15.md` (566 of 600 due to the v1 runner dying); updated run after the description fixes at `researcher/benchmarks/router/results-published/2026-05-15-v2.md` with full delta-vs-baseline table.
- 50 ground-truth router prompts at `researcher/benchmarks/router/prompts.jsonl` covering positive controls, adversarial boundary pairs, combined-skill prompts, and negative controls.
- `researcher/scripts/render_router_report.py` with `--baseline` flag for delta reports.
- `researcher/benchmarks/router/results-published/README.md` explains the committed-summary vs gitignored-raw split.

#### Hardened SDK runner (`researcher/benchmarks/sdk-runner/src/`)

- **Resume**: scans the destination directory on startup and skips plan items that already have a per-run JSON. A killed sweep can be picked up exactly where it stopped; no wasted credits, no duplicate runs.
- **Bounded parallelism**: `--concurrency N` runs N agent calls simultaneously. Cuts the 600-run sweep from ~60 minutes (sequential) to ~15 minutes (concurrency=4) with identical correctness.
- **Per-run progress logging**: every completed run prints `[N/total] model prompt rep=R status durationMs T1 ETA=duration`. The v1 sweep silently stalled at 566 of 600 with no signal; the v2 sweep would have surfaced the cause immediately.
- **Format-failure retry**: transient empty or unparsable SDK responses are retried once before being recorded as format failures. This was added after the May 19 sweep produced transient blank outputs that succeeded on rerun.
- `runConcurrently` helper in `common.ts`, reusable by future runners.

#### Skill description rewrites (data-driven)

Targeted at the two routing failures the v2.2.0 baseline benchmark surfaced:

- `context-fundamentals`: rewrote to be unambiguously about conceptual foundations and explicitly route operational work to the specialized skills. Top-1 rate went from **0.255 to 0.489** (+23.4pp).
- `project-development`: tightened with explicit cross-references to `tool-design`. Top-1 rate went from **0.750 to 1.000** (now perfect routing).
- `tool-design`: tightened with explicit cross-references to `project-development`. Top-1 rate went from **0.729 to 0.807** (+7.8pp).

#### Skill body alignment with new descriptions

The router benchmark only sees frontmatter `description` because `settingSources: []` excludes the SKILL.md body. The first description rewrite pass left the bodies (`When to Activate`, `Practical Guidance`, `Integration`) claiming the broader pre-rewrite scope, which would have steered the agent toward operational work the moment the skill actually activated in production. Aligned the bodies in a follow-up pass:

- `context-fundamentals` body: rewrote `When to Activate` to list conceptual triggers and explicit do-not-activate routing; removed the operational `File-System-Based Access` and `Context Budgeting` practical-guidance sections (owned by `filesystem-context` and `context-optimization` respectively); replaced with conceptual application advice plus a reading-order recommendation for new contributors; rewrote `Integration` as an explicit routing map across all 14 sibling skills. Internal version bump 2.0.0 -> 2.1.0.
- `tool-design` body: rewrote `When to Activate` to anchor on the unit of work (single tool or tool catalog) and listed adjacent decisions owned by `project-development`, `multi-agent-patterns`, `context-optimization`; rewrote `Integration` with explicit routing reasons. Internal version bump 2.0.0 -> 2.1.0.
- `project-development` body: rewrote `When to Activate` to anchor on project shape and pipeline; listed adjacent decisions owned by `tool-design`, `context-optimization`, `multi-agent-patterns`, `harness-engineering`; rewrote `Integration` with explicit routing reasons. Internal version bump 1.1.0 -> 1.2.0.

The body changes do not affect router-benchmark numbers (the router sees only descriptions) but they do affect what the agent loads when these skills activate. Stage 3 (effectiveness benchmark, which loads full bodies) is the right place to measure the impact of this alignment.

#### Corpus-wide skill hardening pass

After the targeted three-skill body alignment, every published skill was audited against the same standard: explicit ownership boundary, `Do not activate` routing, executable practical guidance, examples, gotchas, integration boundaries, mechanism coverage, claim provenance, and activation fixtures.

- Updated all 15 skill bodies with scoped improvements, including structural fixes for `bdi-mental-states` and `hosted-agents`, stronger negative routing across older skills, clearer examples for context failure modes, and claim-backed wording for volatile benchmark statements.
- Expanded `researcher/mechanisms/registry.jsonl` from 5 to 16 accepted mechanisms so every published skill owns at least one machine-readable behavior pattern.
- Expanded claim provenance from 6 to 12 records and replaced vague run-summary sources with concrete repo paths for BrowseComp, RULER/lost-in-middle, compression, d0, Latent Briefing, memory, and tool-output claims.
- Expanded activation regression coverage from 14 to 19 cases so every skill has deterministic routing coverage, including `bdi-mental-states`, `context-degradation`, `hosted-agents`, `latent-briefing`, and `multi-agent-patterns`.
- Tightened `validate_repo.py --strict` so `Core Concepts`, `Practical Guidance`, `Examples`, `References`, and explicit non-activation boundaries are now enforced rather than optional.
- Updated `template/SKILL.md` with the new corpus-wide standard: body/frontmatter alignment, mechanism registration, executable guidance, and `claim-*` provenance for volatile claims.
- Re-ran the no-API gates after the pass: `validate_repo.py --strict` passed with 0 errors / 0 warnings; `skill_health.py --strict --no-history` improved from corpus score 0.8111 / 2 flagged skills to 0.9117 / 0 flagged skills; `check_activation_cases.py` passed 19/19; `run_benchmarks.py` passed 3 checks and 7 adversarial scenarios.
- Re-ran the paid Stage 2 router benchmark after the corpus-wide pass: 600/600 usable records, 0 format failures after retrying transient format failures, published at `researcher/benchmarks/router/results-published/2026-05-19.md`. Per-model top-1: Gemini 0.920, Composer 0.913, GPT-5.5 0.913, Claude Opus 4.7 0.840. Remaining failures are concentrated in known ambiguous/negative-control prompts (`p046`, `p048`) and the `context-fundamentals` catch-all boundary.

#### Eleven new boundary regression cases

`researcher/fixtures/activation-cases.jsonl` grew from 8 to 19 cases. The first six new cases target specific confusions observed in the v2.2.0 baseline:

- `activation-fundamentals-vs-degradation`, `activation-fundamentals-onboarding`, `activation-fundamentals-vs-optimization`
- `activation-tool-vs-project-structured-output`, `activation-tool-individual-tool`, `activation-tool-consolidation`

These act as a tripwire so any future description change is held accountable.

The corpus-wide pass added five more cases for previously uncovered skills:

- `activation-bdi-vs-memory`
- `activation-degradation-poisoning`
- `activation-hosted-vs-harness`
- `activation-latent-briefing-vs-memory`
- `activation-multi-agent-topology`

#### Stage 1 skill health (still no API cost)

- `researcher/scripts/skill_health.py`: per-skill structural scoring. Initial corpus baseline: 0.8111 aggregate, 2 of 15 skills flagged (`bdi-mental-states` for missing required section, `hosted-agents` for multiple structural issues). After the corpus-wide hardening pass: 0.9117 aggregate, 0 flagged skills.
- Output at `researcher/reports/skill-health.json` (gitignored runtime artifact) + optional append to `skill-health-history.jsonl`.

### Changed

- Version bumped 2.2.0 -> 2.3.0 across `.claude-plugin/marketplace.json`, `.plugin/plugin.json`, root `SKILL.md`.
- `researcher/benchmarks/PLAN.md` status table reflects Stage 0/1/2 shipped, Stage 3/4 still scaffolded.

### Headline measured results

Per-model top-1 accuracy (baseline -> new descriptions, 600-run sweep at seed=1, fixture sha 8f974d9):

| Model | Baseline | New | Delta |
| --- | --- | --- | --- |
| composer-2 | 0.888 | 0.913 | +2.5pp |
| gpt-5.5 | 0.886 | 0.913 | +2.7pp |
| gemini-3.1-pro | 0.886 | 0.925 | +3.9pp |
| claude-opus-4-7 | 0.886 | 0.867 | -2.0pp |

Per-skill top-1 rate change for the three skills targeted by description rewrites:

| Skill | Baseline | New | Delta |
| --- | --- | --- | --- |
| `context-fundamentals` | 0.255 | 0.489 | +23.4pp |
| `project-development` | 0.750 | 1.000 | +25pp |
| `tool-design` | 0.729 | 0.807 | +7.8pp |

Format compliance: 99.5% (3 failures, all Gemini). Latency: Gemini ~9.1s median, others 3.3-4.2s. Total sweep cost approximately 7.20 USD against the 15 USD budget cap.

### Honest scope caveats

- `context-fundamentals` improved a lot but is still the weakest skill (0.489 top-1). Remaining failures route to `project-development` for generic onboarding prompts. One more description pass may push it past 0.75.
- Two prompts remain at 0.00 across all models: p046 (Python reformatting, negative control) and p048 (evaluate KV compaction, genuinely ambiguous). Should be re-labeled or removed from positive-routing tests.
- `advanced-evaluation` looks regressed (-18.3pp) but is largely an artifact of the v2.2.0 baseline missing 11 attempts when the runner died at 566/600. Absolute correct count: 48 baseline -> 47 new.
- Stage 3 (real agent tasks with and without skills loaded) is still scaffolded but not executed; that is the next investment.
- No LLM-judge adapter for the run state machine. No automated source discovery beyond manual seed.

## [2.2.0] - 2026-05-15

### Added

#### Researcher operating system

- **Mechanism registry** (`researcher/mechanisms/registry.jsonl`) seeded with five accepted mechanisms (`locked-editable-surfaces`, `durable-research-thread`, `deterministic-first-validation`, `structured-novelty-gate`, `pairwise-skill-revision`).
- **Mechanism ledgers** (`researcher/mechanisms/ledgers/accepted.jsonl`, `rejected.jsonl`) for append-only promotion events.
- **Claim provenance** (`researcher/claims/index.jsonl`) for six volatile or benchmark-backed claims across `evaluation`, `multi-agent-patterns`, `context-optimization`, `memory-systems`, `advanced-evaluation`, and `harness-engineering`.
- **Corpus index** (`researcher/corpus/index.json`) mapping skills to activation scenarios, mechanism IDs, and claim IDs.
- **Activation regression fixtures** (`researcher/fixtures/activation-cases.jsonl`) covering high-risk skill-boundary pairs.
- **Adversarial benchmark harness** (`researcher/benchmarks/scenarios/adversarial.jsonl` + goldens) with seven scenarios that try to game the loop.
- **Benchmark history** (`researcher/reports/benchmark-history.jsonl`) for longitudinal trend tracking.
- **Pairwise revision rubric and script** (`researcher/rubrics/pairwise-skill-revision.md`, `researcher/scripts/compare_skill_revisions.py`).
- **Run state machine** in `run-state.json` with explicit transitions: `initialized -> retrieved -> evaluated -> proposed -> novelty_checked -> validated -> pr_ready -> closed`.

#### Continuous loop

- **Queue infrastructure** (`researcher/queue/`): inbox, parked, done, quarantine.
- **Orchestration config** (`researcher/orchestration/config.json`) with daily/active/parked/failure budgets.
- **Discovery feeder** (`researcher/scripts/loop_discover.py`) reading from `researcher/discovery/manual-seed.jsonl`.
- **Loop step orchestrator** (`researcher/scripts/loop_step.py`) that reaps closed runs, pulls from inbox, retrieves via stdlib `urllib`, and parks at human-review gates.
- **Daily ops** (`researcher/scripts/loop_daily.py`) running validators, benchmarks, activation cases, and writing dated snapshots.
- **Status dashboard** (`researcher/scripts/loop_status.py`) plus parked-review surface.
- **launchd service definitions** (`researcher/orchestration/launchd/`) with install/uninstall scripts and per-script wrappers.
- **Continuous operation runbook** (`researcher/runbooks/continuous-operation.md`).

#### Scripts

- `researcher/scripts/validate_run.py`: per-run publish readiness, skips closed runs.
- `researcher/scripts/research_loop.py` subcommands: `retrieve`, `evaluate`, `propose`, `novelty`, `validate-run`, `pr-ready`, `close`, `promote-mechanisms`.
- `researcher/scripts/check_activation_cases.py`: deterministic activation regression checker.
- `researcher/scripts/run_benchmarks.py`: runs deterministic gates, scenarios, optional history recording.
- `researcher/scripts/loop_common.py`: shared atomic-write helpers and `fcntl` locks.

#### CI

- `.github/workflows/validate.yml` runs `validate_repo.py --strict`, `run_benchmarks.py`, `check_activation_cases.py`, and Python compile checks on every push and PR.

### Changed

- Skill activation surface refactored from keyword triggers to task-boundary descriptions in frontmatter and README. Affected: all 14 published skills plus the example skills in `examples/`.
- `validate_repo.py` hardened: duplicate JSON keys, exact doc sync, rubric IDs, run artifacts, registry schema, evidence paths, partial-retrieval approvals, root-level raw provenance, claims schema, corpus index consistency, activation cases, benchmark scenarios.
- `novelty_check.py` now compares mechanism registry overlap as the primary signal, with corpus overlap secondary.
- Mechanism registry evidence may now reference claim IDs from `researcher/claims/index.jsonl` in addition to URLs and repo paths.

### Hardened

- All queue mutations use atomic temp-file `os.replace` and `fcntl` exclusive locks scoped per queue family.
- `read_jsonl` is tolerant: malformed lines quarantine to `researcher/reports/jsonl-quarantine/` rather than crashing the loop.
- `fetch_url` allows only `http(s)://` and re-checks scheme after redirect.
- Closed runs are automatically reaped from `parked.jsonl` and recorded in `done.jsonl`.
- Inbox lock now held through `init_run` so concurrent loop_step invocations cannot exceed budgets.
- URL deduplication normalizes case before hashing.

### Repository policy

- Active research runs under `researcher/runs/*/` are runtime state and not committed. The seed run `20260515-035228-executable-autonomous-research-frameworks` is kept as a worked-example fixture.
- Runtime queue and report files (`researcher/queue/*.jsonl`, `researcher/reports/{logs,snapshots,loop-events.jsonl,loop-failures.jsonl,status.md,parked-review.md}`, `researcher/queue/.locks/`) are gitignored.

### Out of scope for 2.2.0

- LLM-judge adapters for advancing `retrieved -> evaluated` automatically.
- Automated source discovery beyond the manual seed file (Parallel deep research and web search adapters are placeholders behind config toggles).
- Log rotation; benchmark history pruning.

## [2.1.0] - 2026-05-14

### Added

- `harness-engineering` skill: locked/editable surface model, durable threads, novelty gates, rollback, human approval boundaries.
- `researcher/` directory v1: source registry, content/skill/harness rubrics, source-evaluation JSON template, skill-proposal template, autonomous research loop runbook, PR readiness runbook.

## [2.0.0] - earlier

Baseline corpus of 13 skills distributed as a single Claude Code plugin.
