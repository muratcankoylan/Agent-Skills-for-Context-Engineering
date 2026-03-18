# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## What This Repo Is

A curated open-source collection of **Agent Skills** focused on context engineering — modular knowledge modules designed for progressive discovery and activation by AI agents. This is not a traditional service/API codebase; it's a skill marketplace where the primary artifacts are Markdown files organized for both AI instruction and human learning.

## Skill Structure (Canonical Pattern)

Every skill lives under `skills/<name>/` or `examples/<name>/` and follows:

```
skill-name/
├── SKILL.md          # Required: YAML frontmatter + skill content
├── references/       # Optional: supporting documentation
└── scripts/          # Optional: executable examples
```

**SKILL.md rules:**
- Must start with YAML frontmatter: `name`, `description`, and trigger keywords
- Keep under **500 lines** (100-line average for core skills)
- Skills reference each other by name, not by file path
- Use `template/SKILL.md` as the canonical starting point for new skills

## Plugin Marketplace

Plugins bundle related skills and are defined in `.claude-plugin/marketplace.json`. There are 5 bundles:
- `context-engineering-fundamentals` → context-fundamentals, context-degradation, context-compression, context-optimization
- `agent-architecture` → multi-agent-patterns, memory-systems, tool-design, filesystem-context, hosted-agents
- `agent-evaluation` → evaluation, advanced-evaluation
- `agent-development` → project-development
- `cognitive-architecture` → bdi-mental-states

Skills are discovered progressively: agents load names/descriptions first, then fetch full content only when a skill is activated for a relevant task.

## Commands

Most skills are documentation-only. The two subprojects with runnable code:

### `examples/llm-as-judge-skills/` (TypeScript)
```bash
cd examples/llm-as-judge-skills
npm install
npm test                    # Run all tests (vitest)
npm run test:watch          # Watch mode
npm run test:coverage       # With coverage
npm run lint                # ESLint
npm run typecheck           # tsc --noEmit (no emit)
npm run build               # Compile to dist/
npm run example:basic       # Run basic evaluation example
npm run example:full        # Run full evaluation workflow
```
Dependencies: `ai`, `@ai-sdk/anthropic`, `@ai-sdk/openai`, `zod`. Tests use Vitest (19 tests).

### `examples/interleaved_thinking/` (Python)
```bash
cd examples/interleaved_thinking
pip install -e .
rto                         # CLI entry point (reasoning_trace_optimizer.cli:main)
pytest tests/               # Run tests (asyncio_mode = auto)
ruff check .                # Lint (line-length 100)
```
Requires Python ≥ 3.10. Dependencies: `anthropic`, `pydantic`, `rich`.

### `examples/digital-brain-skill/` (Python scripts)
```bash
cd examples/digital-brain-skill
npm run weekly-review       # python3 agents/scripts/weekly_review.py
npm run content-ideas       # python3 agents/scripts/content_ideas.py
npm run stale-contacts      # python3 agents/scripts/stale_contacts.py
```

## Naming Conventions

- Skill directory names: lowercase with hyphens (`multi-agent-patterns`)
- File naming mirrors the skill name exactly
- New skills should mirror existing structure from `template/SKILL.md`
