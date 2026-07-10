# Router Benchmark (Stage 2)

Tests whether the activation-scenario descriptions in v2.2.0 skill frontmatter are good enough to route the right skill to a given prompt.

See `researcher/benchmarks/PLAN.md` for full methodology.

## Files

- `prompts.jsonl`: ground-truth prompts. Each line has `prompt_id`, `prompt`, `expected_primary_skill`, optional `acceptable_secondary_skills` and `rejected_skills`, and a `reason`.
- `routing-prompt.md`: the template given to the LLM. Uses `{{SKILL_BLOCK}}`, `{{USER_PROMPT}}`, `{{SKILL_COUNT}}` placeholders.
- `results/<date>-<seed>/`: per-run JSON outputs (gitignored).

## Running

From the Codex runner:

```bash
cd researcher/benchmarks/codex-runner
npm install
npm run router:dry-run -- --models gpt-5.5 --reps 1 --max-runs 106
npm run router:run -- --models gpt-5.5 --reps 1 --max-runs 106
```

The live path is `native Codex CLI -> Headroom -> OpenAI ChatGPT/Codex OAuth`; no `CURSOR_API_KEY` is used.

## Ground truth

Initial fixtures are 50 prompts covering:

- Single-skill positive controls (one per skill, 15 cases)
- Adversarial boundary pairs from the v2.2.0 boundary-confusion list (15 cases across 5 pairs x 3 variants)
- Combined-skill prompts where multiple are acceptable (10 cases)
- Negative controls where no skill should fit well (5 cases)
- Subtle activation cases that should still resolve (5 cases)

Expand to 100 by adding prompts as new boundary confusions surface in the wild.
