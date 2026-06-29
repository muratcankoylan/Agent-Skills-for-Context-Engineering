# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Agent Skills for Context Engineering: an open collection of 15 Agent Skills teaching context engineering and harness engineering principles for production AI agent systems. Skills are platform-agnostic (Claude Code, Cursor, GitHub Copilot, any Open Plugins-conformant tool). v2.2.0 ships a file-based researcher operating system with deterministic gates and a continuous loop.

Context engineering is the discipline of curating everything that enters a model's context window (system prompts, tool definitions, retrieved documents, message history, tool outputs) to maximize signal within limited attention budget.

## Repository Structure

- `skills/` - 15 skill directories, each containing a `SKILL.md` with YAML frontmatter (`name`, `description`) and optional `references/` and `scripts/` subdirectories
- `examples/` - 5 complete demonstration projects (digital-brain-skill, llm-as-judge-skills, book-sft-pipeline, x-to-book-system, interleaved-thinking)
- `docs/` - Research materials and reference documentation
- `researcher/` - File-based research-to-skill operating system: rubrics, mechanism registry, claim provenance, corpus index, run state machine, adversarial benchmarks, continuous loop, launchd service definitions
- `template/SKILL.md` - Canonical skill template (use when creating new skills)
- `SKILL.md` (root) - Collection-level metadata and skill map
- `.claude-plugin/marketplace.json` - Claude Code marketplace manifest (single bundled plugin, v2.2.0)
- `.plugin/plugin.json` - Open Plugins format manifest (v2.2.0)

## Build & Test Commands

No top-level build system. Repo-level gates and per-project tooling below.

### Top-level deterministic gates (run on every PR via CI)

```
python3 -m unittest researcher.scripts.tests.test_skill_frontmatter # parser and strict-YAML regression tests
python3 researcher/scripts/validate_platform_compat.py --require-reference-validator # Agent Skills reference validator + Cursor/Claude/Codex install-layout simulation
python3 researcher/scripts/validate_repo.py --strict       # corpus structure, manifests, rubric math, mechanism registry, claims, corpus index, activation cases, benchmark scenarios, run artifacts
python3 researcher/scripts/skill_health.py --strict --no-history  # deterministic skill-body quality gate
python3 researcher/scripts/run_benchmarks.py               # adversarial benchmark harness + repo + activation gates
python3 researcher/scripts/check_activation_cases.py       # skill-boundary regression fixtures
```

### Per-run readiness (active runs only)

```
python3 researcher/scripts/validate_run.py --run-dir researcher/runs/<run-id>
```

### Continuous loop (manual or launchd)

```
python3 researcher/scripts/loop_discover.py
python3 researcher/scripts/loop_step.py --allow-fetch
python3 researcher/scripts/loop_daily.py
python3 researcher/scripts/loop_status.py

researcher/orchestration/launchd/install.sh    # macOS daemon
researcher/orchestration/launchd/uninstall.sh
```

### Example projects

#### examples/llm-as-judge-skills (TypeScript, Node >= 18)
```
cd examples/llm-as-judge-skills
npm install
npm run build        # tsc
npm test             # vitest (19 tests)
npm run lint         # eslint
npm run format       # prettier
npm run typecheck    # tsc --noEmit
```

#### examples/interleaved-thinking (Python >= 3.10)
```
cd examples/interleaved-thinking
pip install -e ".[dev]"
pytest               # pytest + pytest-asyncio
ruff check .         # linting (100 char line length)
```

#### examples/digital-brain-skill (Node.js)
```
cd examples/digital-brain-skill
npm run setup
npm run weekly-review
npm run content-ideas
npm run stale-contacts
```

## Skill Authoring Rules

When creating or editing skills:

1. **SKILL.md must stay under 500 lines**: move detailed content to `references/` directory
2. **YAML frontmatter is required**: must include `name` and `description` fields
3. **Folder naming**: lowercase with hyphens (e.g., `context-fundamentals`)
4. **Write in third person**: descriptions are injected into system prompts; inconsistent POV causes discovery issues
5. **Platform-agnostic**: no vendor-locked examples or platform-specific tool names without abstraction
6. **Token-conscious**: challenge each paragraph and assume an advanced audience
7. **Body standard**: include `When to Activate`, `Core Concepts`, `Practical Guidance`, `Examples`, `Guidelines`, `Gotchas`, `Integration`, and `References`
8. **Explicit boundaries**: every `When to Activate` section needs positive triggers plus a `Do not activate` block routing adjacent work to the right skill
9. **Include a Gotchas section**: experience-derived failure modes are the highest-signal content in any skill
10. **Update root README.md** when adding new skills
11. **Update marketplace/plugin manifests** when adding skills (`.claude-plugin/marketplace.json`, `.plugin/plugin.json`)
12. **Update the corpus index** (`researcher/corpus/index.json`) to map the new skill to activation scenarios, mechanism IDs, and claim IDs
13. **Update mechanisms and claims**: add registry entries for reusable behavior changes and `claim-*` provenance for numeric, benchmark, volatile, or vendor-performance claims
14. **Run `validate_platform_compat.py --require-reference-validator`, `validate_repo.py --strict`, `skill_health.py --strict --no-history`, `check_activation_cases.py`, and `run_benchmarks.py`** before committing skill changes

## Researcher OS Rules

When working through the researcher operating system:

1. **Initialize runs via `research_loop.py init`**: it creates `run-state.json`, queue entry, thread log, source evaluation scaffold, and mechanism proposal template
2. **Advance state explicitly**: use `retrieve`, `evaluate`, `propose`, `novelty`, `validate-run`, `pr-ready`, `close` subcommands; do not edit `run-state.json` by hand
3. **Promote mechanisms only after run readiness**: `research_loop.py promote-mechanisms` requires `--reviewed-by` and a passing run-readiness check
4. **Add claim provenance** to `researcher/claims/index.jsonl` for any numeric, benchmark, or volatile claim added to a skill
5. **Never invoke paid LLMs from the continuous loop**: HTTP retrieval is stdlib-only, judge adapters are explicitly out of scope until budget-gated
6. **Never commit runtime queue/report files**: `.gitignore` covers `researcher/queue/*.jsonl`, `researcher/reports/{logs,snapshots,loop-events.jsonl,loop-failures.jsonl,status.md,parked-review.md}`, and `researcher/runs/*/` except the seed run

## Plugin Architecture

All 15 skills are distributed as a single plugin (`context-engineering`) in the marketplace manifest. This avoids cache duplication: Claude Code caches each plugin's `source` directory separately, so multiple plugins pointing to `source: "./"` would each cache a full copy of the repo.

Progressive disclosure pattern: only skill names/descriptions load at startup; full content loads on activation.

## Key Design Principles

- **Context quality over quantity**: attention scarcity and lost-in-middle behavior mean more context is not always better
- **Sub-agents isolate context**: they exist to manage attention budget, not simulate org roles
- **Skills reference each other**: use plain text skill names (not links) in Integration sections to avoid cross-directory reference issues
- **Examples use Python pseudocode**: conceptual demonstrations that work across environments, not production-ready implementations
- **Deterministic first, model-judged second**: structure, schema, rubric math, manifest sync, retrieval status, and registry shape must pass before any LLM judge is invoked
- **Human-controlled merge**: agents may prepare PRs and pass gates, but push and merge always require explicit human approval
