# Router Benchmark (Stage 2)

Tests whether skill frontmatter descriptions are sufficient to route a user prompt to the intended skill. See `researcher/benchmarks/PLAN.md` for the methodology and the published-results interpretation rules.

This revision is zero-call and dry-run-only. It contains no live SDK executor, result writer, or resume path. A command without `--dry-run` exits before fixture, credential, SDK, or result-state access.

## Inputs

- `prompts.jsonl`: ground-truth records with `prompt_id`, `prompt`, `expected_primary_skill`, and optional `acceptable_secondary_skills`, `rejected_skills`, and `reason` fields.
- `routing-prompt.md`: the future execution template. It uses `{{SKILL_BLOCK}}`, `{{USER_PROMPT}}`, and `{{SKILL_COUNT}}` placeholders.
- skill descriptions: loaded from the repository corpus and each registered skill's frontmatter during dry-run validation.

Each fixture record must use known, non-empty skill identifiers. Prompt identifiers and optional skill lists must be unique, and accepted and rejected skill sets must not overlap.

## Current command

From the SDK runner:

```bash
cd researcher/benchmarks/sdk-runner
npm ci --ignore-scripts
npm run router:dry-run -- --models gpt-5.5 --reps 1 --max-runs 112 --max-budget-usd 2
```

The dry run validates the fixture and skill catalog, constructs the deterministic prompt x model x replication plan, reserves up to two format attempts per logical run in its invocation and cost ceilings, and prints a sample plan item. It makes no SDK call and writes no benchmark result or resume state.

`npm run router:run` is an intentional fail-closed check, not an execution command.

## Future activation gate

Live execution requires a separate reviewed and human-merged change. Before one concurrency-1 canary is authorized, that change must provide all of the following:

1. A canonical, content-addressed run manifest binding a clean source tree, fixture, routing template, skill catalog, package lock, runtime options, exact model set, replications, seed, complete plan, and retry policy.
2. An injected executor boundary with deterministic fake-executor tests proving call counts, retry accounting, terminal-status handling, and the absence of calls during preflight failures.
3. An explicit credential with confirmed Privacy Mode, plus a text-only SDK request using `tools: []`, `settingSources: []`, and `enableAgentRetries: false`; ambient credentials, tools, settings, and retries remain forbidden.
4. Exclusive crash-safe terminal-result writes and strict manifest- and plan-item-bound state validation. Malformed, foreign, ambiguous, or in-flight state must block automatic resume before a paid call.
5. A fresh dependency audit and an explicit containment decision for every unresolved production advisory.

No parallel or full sweep is authorized until the canary evidence is reviewed and accepted.
