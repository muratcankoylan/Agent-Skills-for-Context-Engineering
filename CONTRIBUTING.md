# Contributing to Agent Skills for Context Engineering

Thank you for your interest in contributing to this collection of Agent Skills for Context Engineering. This document provides guidelines and instructions for contributing.

## How to Contribute

### Reporting Issues

If you find errors, unclear explanations, or missing topics, please open an issue with:
- A clear description of the problem
- The skill and section where the issue was found
- Suggested improvements if you have them

### Submitting Changes

For substantive changes, please:

1. Fork the repository
2. Create a feature branch for your changes
3. Make changes following the skill template structure
4. Ensure SKILL.md files remain under 500 lines
5. Add references or scripts as appropriate
6. Submit a pull request with a clear description of changes

### Adding New Skills

When adding new skills:

1. Use the template in `template/SKILL.md`
2. Follow naming conventions (lowercase with hyphens)
3. Include both SKILL.md and appropriate references/scripts
4. Update the root README.md to include the new skill
5. Update root `SKILL.md`, `.claude-plugin/marketplace.json`, and `.plugin/plugin.json` when publishing the skill
6. Update `researcher/corpus/index.json` with the new skill's name, activation scenarios, mechanism IDs, and claim IDs
7. Add at least one entry to `researcher/fixtures/activation-cases.jsonl`; include rejected or adjacent skills when the boundary is easy to confuse
8. Ensure content is platform-agnostic (works across Cursor, Claude Code, etc.)
9. Run the unit tests and deterministic gates before opening a PR:
   - `python3 -m unittest researcher.scripts.tests.test_skill_frontmatter`
   - `python3 researcher/scripts/validate_platform_compat.py --require-reference-validator`
   - `python3 researcher/scripts/validate_repo.py --strict`
   - `python3 researcher/scripts/skill_health.py --strict --no-history`
   - `python3 researcher/scripts/check_activation_cases.py`
   - `python3 researcher/scripts/run_benchmarks.py`

## Researcher Operating System Contributions

The repository ships with a file-based research-to-skill operating system in `researcher/`. Contributions that introduce skill changes derived from external research should flow through it.

### Run lifecycle

```
initialized -> retrieved -> evaluated -> proposed -> novelty_checked -> validated -> pr_ready -> closed
```

Use `researcher/scripts/research_loop.py` subcommands rather than editing `run-state.json` by hand. Each transition appends to the run's thread log and updates the state machine atomically.

### Mechanism promotion

New behavior changes proposed for the corpus go through `researcher/mechanisms/registry.jsonl`. The promotion path is gated:

1. Author the proposal in the run's `proposals/mechanism-proposal.jsonl`.
2. Pass `validate_run.py --run-dir <run>`.
3. Run `research_loop.py promote-mechanisms --run-dir <run> --reviewed-by <handle>`. This appends to the registry and to `researcher/mechanisms/ledgers/accepted.jsonl`.

Rejected mechanisms append to `ledgers/rejected.jsonl` so future agents do not rediscover them.

### Claim provenance

Any numeric, benchmark, or volatile claim added to a published skill should also receive an entry in `researcher/claims/index.jsonl` with `claim_id`, `owning_skill`, `section`, `source_url`, `retrieved_at`, `evidence_strength`, `volatility`, and `last_reviewed`. The validator checks ownership and source paths.

### Parked runs

Runs that hit human-review gates land in `researcher/queue/parked.jsonl` and the dashboard at `researcher/reports/parked-review.md`. Reviewers should:

1. Read `researcher/runs/<run-id>/THREAD.md` and `sources/evidence/`.
2. Complete the next required step (retrieve, evaluate, propose, novelty, validate-run, or pr-ready).
3. Close the run with `research_loop.py close --status accepted|rejected|reference-only|abandoned --reason <text> --reviewed-by <handle>`.

The continuous loop will reap closed runs into `researcher/queue/done.jsonl` on the next iteration.

### Runtime state is not committed

`researcher/runs/*/` (except the seed run), `researcher/queue/*.jsonl`, and `researcher/reports/{logs,snapshots,loop-events.jsonl,loop-failures.jsonl,status.md,parked-review.md}` are gitignored. PRs should not introduce new committed runs; bug fixtures belong in `researcher/fixtures/` instead.

## Skill Structure Requirements

Each skill must include:

- YAML frontmatter with `name` and `description` fields. Quote `description` values that contain colons (`:`) so strict YAML parsers used by Cursor, Claude Code, and Codex can load the skill. Run `python3 researcher/scripts/validate_repo.py --strict` before opening a PR.
- `## When to Activate` with positive triggers and an explicit `Do not activate` boundary for adjacent skills
- `## Core Concepts` focused on behavior-changing mechanisms, not generic background
- `## Practical Guidance` with an executable workflow, checklist, decision table, or operating rule
- `## Examples` with at least one worked artifact, before/after, or boundary example
- `## Guidelines`, `## Gotchas`, `## Integration`, and `## References`
- Integration notes that explain routing and composition boundaries, not only topical relationships

Any numeric, benchmark, volatile, or vendor-performance claim in a published skill must either reference a `claim-*` ID from `researcher/claims/index.jsonl` or be softened and moved to dated reference material. Any reusable behavior pattern should be represented in `researcher/mechanisms/registry.jsonl` and linked from `researcher/corpus/index.json`.

Optional additions:

- `references/` directory with additional documentation
- `scripts/` directory with executable examples
- Multiple markdown files for complex skills

## Content Guidelines

### Writing Style

- Be direct and precise
- Use technical terminology appropriately
- Include specific guidance, not vague recommendations
- Provide concrete examples
- Point out complexity and trade-offs

### Avoiding Platform Specificity

Skills should work across agent platforms. Avoid:
- Platform-specific tool names without abstraction
- Vendor-locked examples
- Features specific to one agent product

### Keeping Skills Focused

Each skill should have a single focus. If a topic grows too large, consider splitting into multiple skills with clear dependencies.

## Code of Conduct

This project follows a professional, technical collaboration model. Be respectful of different perspectives and focus on improving the collective knowledge base.

## Questions

For questions about contributing, please open an issue for discussion.

