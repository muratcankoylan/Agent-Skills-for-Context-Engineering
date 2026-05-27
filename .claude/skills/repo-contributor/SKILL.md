---
name: repo-contributor
description: Internal operating guide for developing the Agent Skills for Context Engineering repository itself - its skill corpus, researcher OS, benchmarks, manifests, and deterministic gates. Use when editing skills, advancing research runs, updating mechanisms/claims/corpus index, running validators, or preparing PRs in this repo.
---

# Repo Contributor

Internal source-of-truth guide for working *on* this repository (not a published context-engineering skill). It encodes the architecture, conventions, gates, and failure modes so help stays project-specific instead of generic. Authoritative inputs: `CLAUDE.md`, `AGENTS.md`, root `SKILL.md`, `template/SKILL.md`, `researcher/`. When those files change, they win over this guide.

## When to Activate

- Creating or editing any skill under `skills/` (frontmatter, body, references, scripts)
- Advancing a research run or working through the `researcher/` operating system
- Adding/updating mechanisms, claim provenance, or the corpus index
- Running or interpreting the deterministic gates and benchmarks
- Updating version-bearing manifests (`.claude-plugin/marketplace.json`, `.plugin/plugin.json`, root `SKILL.md`)
- Preparing branches, commits, or PRs in this repo

**Do not activate** for:
- Teaching context-engineering concepts to an end user: route to the published `skills/` content (e.g. `context-fundamentals`, `harness-engineering`).
- Generic software tasks in unrelated repos.

## Core Concepts

This repo is an autonomous research-to-skill organization. It ships 15 platform-agnostic Agent Skills plus a file-based researcher OS that curates external AI research into skill updates through rubrics and deterministic gates. Current published version: **2.3.0** (kept in sync across both manifests and root `SKILL.md`).

Two distinct health questions, do not conflate them:
- **Repo health** - `validate_repo.py` / `skill_health.py` / `run_benchmarks.py` / `check_activation_cases.py` (CI runs these on every PR via `.github/workflows/validate.yml`).
- **Per-run readiness** - `validate_run.py --run-dir researcher/runs/<run-id>`.

Foundational principle enforced everywhere: **deterministic checks before model judges**. Structure, schema, rubric math, manifest sync, retrieval status, and registry shape must pass before any LLM judge runs.

**A skill is a multi-surface artifact.** Changing the frontmatter `description` is never enough on its own. The body `When to Activate` and `Integration` sections, the mechanism registry, claim index, corpus index, and activation fixtures must all agree the same day. The router benchmark only sees descriptions; body inconsistencies are invisible to it and only surface in Stage 3 effectiveness benchmarks.

## Repository Map

- `skills/` - 15 skill dirs, each a `SKILL.md` (+ optional `references/`, `scripts/`)
- `examples/` - 5 demo projects (digital-brain, llm-as-judge, book-sft-pipeline, x-to-book, interleaved-thinking)
- `researcher/` - file-based research OS:
  - `runs/<run-id>/run-state.json` - per-run state machine (only the seed run is committed)
  - `mechanisms/registry.jsonl` + `mechanisms/ledgers/` - reusable behavior-change encyclopedia
  - `claims/index.jsonl` - provenance for numeric/benchmark/volatile claims
  - `corpus/index.json` - machine-readable map of skills -> activation scenarios, mechanism IDs, claim IDs
  - `scripts/` - validators, benchmark harness, continuous loop (`loop_*.py`), `research_loop.py`
  - `benchmarks/` - staged methodology, `PLAN.md` is the source of truth; SDK runner in `benchmarks/sdk-runner/`
  - `insights/` - `auto-research-experiment.md` (engineering rationale), `how-we-built-this.md` (narrative)
- `template/SKILL.md` - canonical skill template
- `SKILL.md` (root) - collection metadata + skill map
- `.claude-plugin/marketplace.json`, `.plugin/plugin.json` - version-bearing manifests

## Skill Authoring Rules

1. SKILL.md body stays **under 500 lines**; push detail into `references/`.
2. YAML frontmatter required: `name` + `description`, written in **third person**.
3. Folder naming: lowercase-with-hyphens.
4. Platform-agnostic: no vendor-locked tool names without abstraction.
5. Token-conscious: assume an advanced audience; challenge every paragraph's token cost.
6. Required body sections: `When to Activate`, `Core Concepts`, `Practical Guidance`, `Examples`, `Guidelines`, `Gotchas`, `Integration`, `References`.
7. Every `When to Activate` needs positive triggers **plus** a `Do not activate` block routing adjacent work to the right skill.
8. Gotchas section is the highest-signal content - keep it experience-derived and specific.
9. Reference other skills as **plain text names**, never cross-directory links.
10. Numeric/benchmark/volatile/vendor-performance claims need an inline `claim-*` ID backed by `researcher/claims/index.jsonl`, or be softened and moved to dated reference material.

When adding/restructuring a skill, the full propagation set is: skill body + frontmatter, root `README.md`, both manifests, `researcher/corpus/index.json`, mechanism registry (for reusable behavior changes), and claim index (for tracked claims).

## Researcher OS Rules

1. Initialize runs via `research_loop.py init` - never hand-create run scaffolding.
2. Advance state **only** through subcommands (`retrieve`, `evaluate`, `propose`, `novelty`, `validate-run`, `pr-ready`, `close`). State path: `initialized -> retrieved -> evaluated -> proposed -> novelty_checked -> validated -> pr_ready -> closed`. Never hand-edit `run-state.json`.
3. Promote mechanisms only after run readiness: `research_loop.py promote-mechanisms` requires `--reviewed-by` and a passing readiness check.
4. Add claim provenance to `researcher/claims/index.jsonl` for any numeric/benchmark/volatile claim.
5. The continuous loop (`loop_*.py`) **never invokes paid LLMs**; HTTP retrieval is stdlib-only (1.5 MB cap, 30s timeout).
6. Never commit runtime state: `researcher/queue/*.jsonl`, `researcher/queue/.locks/`, `researcher/reports/{logs,snapshots,loop-events.jsonl,loop-failures.jsonl,status.md,parked-review.md}`, and `researcher/runs/*/` are gitignored. The seed run `20260515-035228-executable-autonomous-research-frameworks` is the only committed run (closed `reference-only`, a worked example).
7. Atomic writes (`tempfile` + `os.replace`) and `fcntl` locks for any shared file the loop touches; append-only ledgers for accepted/rejected mechanisms.

## Benchmarks

Staged in `researcher/benchmarks/` (`PLAN.md` = methodology truth):
- Stage 0 deterministic harness (shipped)
- Stage 1 per-skill health via `skill_health.py` (shipped; `reports/skill-health.json` gitignored)
- Stage 2 router (shipped; `benchmarks/router/results-published/`)
- Stage 3 effectiveness (scaffolded), Stage 4 composition (future)

Execution uses the Cursor SDK runner (`benchmarks/sdk-runner/`, TypeScript, `@cursor/sdk`). Cursor SDK is the **only** paid-API surface allowed, benchmarks only. Required before any SDK call: Privacy Mode, explicit per-call `apiKey`, never `settingSources: "all"` (use `[]` for control, `["project"]` for ablation), and a cost gate (`--max-runs`, `--max-budget-usd`, or `--dry-run`). Any looped paid-API runner needs bounded `--concurrency`, resume-via-results-scan, and per-run progress logging before running. Result artifacts and history JSONLs are gitignored; only `results-published/` is committed. When changing activation descriptions, re-run the router benchmark with the same seed/fixture and publish the per-skill delta and confusion matrix (aggregate accuracy is misleading).

## Practical Guidance

Standard skill-change workflow:
1. Read the current skill body, its references, and its corpus-index entry before editing. Analyze existing structure first; do not break architecture without need.
2. Make the edit across all surfaces (body, frontmatter, manifests, corpus index, mechanisms, claims, README) so they agree.
3. Run the gate stack:
   ```
   python3 researcher/scripts/validate_repo.py --strict
   python3 researcher/scripts/skill_health.py --strict --no-history
   python3 researcher/scripts/check_activation_cases.py
   python3 researcher/scripts/run_benchmarks.py
   ```
4. For active runs add `validate_run.py --run-dir researcher/runs/<run-id>`.
5. Do not call a change complete until prose, mechanism registry, claim index, corpus index, activation fixtures, and validators all agree.

Git rules (hard constraints from `AGENTS.md`):
- Develop on the assigned feature branch; create it locally if missing.
- `git push -u origin <branch>`; retry only on network errors with exponential backoff (2s/4s/8s/16s).
- **Never push or merge without explicit user approval.** Preparing branches/commits/PRs is allowed only for the specific action approved.
- Do not create a PR unless explicitly asked.

Tone for prose, commits, and PRs: technical CTO. Direct, state trade-offs and complexity upfront. No marketing language, no exclamation marks, no emojis, no em dashes. Do not put the model identifier in any committed artifact.

## Examples

**Adding a new skill (surfaces to touch):**
```
skills/<name>/SKILL.md            # body + frontmatter (third person, <500 lines)
README.md                         # skill map entry
.claude-plugin/marketplace.json   # bundled-plugin manifest
.plugin/plugin.json               # Open Plugins manifest
researcher/corpus/index.json      # activation scenarios + mechanism/claim IDs
researcher/mechanisms/registry.jsonl  # if it introduces reusable behavior
researcher/claims/index.jsonl     # if it carries numeric/benchmark claims
```

**Advancing a run (do, not):**
```
Do:  python3 researcher/scripts/research_loop.py evaluate --run-dir researcher/runs/<id>
Not: editing run-state.json "state" field by hand
```

## Guidelines

1. Run `validate_repo.py --strict` before claiming any change complete.
2. Keep version strings identical across both manifests and root `SKILL.md`.
3. Prefer mechanism-level criteria, rubrics, and evidence-backed validation over stale regex/keyword heuristics in skills and scripts.
4. Add an adversarial benchmark scenario whenever a new harness failure mode is discovered.
5. When scope spans multiple architectural decisions or irreversible changes, propose a plan before executing.
6. Treat API keys provided in chat as exposed; rotate after use.

## Gotchas

1. **Description-only edits silently rot the body.** The router benchmark passes on descriptions alone while the `When to Activate`/`Integration` body contradicts them. Audit the body the same day you change a description.
2. **Repo health vs run readiness are different checks.** A green `validate_repo.py` says nothing about a specific run; use `validate_run.py` for that, and vice versa.
3. **Hand-editing `run-state.json` corrupts the state machine.** Always use `research_loop.py` subcommands.
4. **Committing runtime artifacts breaks the gitignore contract.** Queue files, reports, and non-seed runs must never be committed.
5. **Forgetting the corpus index / manifests after a skill change** leaves validators or routing out of sync even when the body looks done.
6. **The continuous loop must stay free of paid LLMs.** Only the Cursor SDK benchmark runner may call a paid API, and only under cost gates and Privacy Mode.

## Integration

- Published `skills/` corpus - the content this repo ships; this guide governs how to edit it, not its subject matter.
- `harness-engineering` - the researcher OS is a concrete instance of its principles (locked metrics, durable logs, human-approval boundaries).
- `evaluation` / `advanced-evaluation` - inform the benchmark methodology and the deterministic-before-judge ordering.

## References

- `CLAUDE.md` - build/test commands, authoring rules, researcher OS rules, design principles
- `AGENTS.md` - durable workspace memory, learned preferences, operating defaults
- `template/SKILL.md` - canonical skill structure and body standard
- `researcher/benchmarks/PLAN.md` - benchmark methodology source of truth
- `researcher/insights/auto-research-experiment.md`, `researcher/insights/how-we-built-this.md` - harness rationale and narrative

---

## Skill Metadata

**Created**: 2026-05-27
**Last Updated**: 2026-05-27
**Author**: Repo maintainers
**Version**: 1.0.0
