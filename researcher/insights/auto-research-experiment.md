# Auto-Research Experiment: Lessons From Building The Researcher OS

> Historical, non-normative experiment record. Claims below about unattended
> scheduling, HTTP retrieval, retry/quarantine automation, accepted closure,
> mechanism promotion, and executed adversarial scenarios are not current
> capabilities. Launchd entry points are inert; runtime ledgers require explicit
> initialization; evidence attachment is manual; accepted closure and mechanism
> promotion fail closed; scenario records are catalog-only. Use the supervised
> runbook for current operator guidance.

This document records what was actually learned across the multi-session experiment that built the v2.2.0 researcher operating system. It is meant to be read alongside `researcher/README.md` and `runbooks/continuous-operation.md`, not in place of them.

## Context

The experiment started with a published skill collection (v2.0/v2.1) and a single question: how do we keep this corpus alive without turning it into a one-person editorial job. The answer became an autonomous research-to-skill operating system with a continuous loop, deterministic gates, mechanism promotion, claim provenance, and explicit run states.

The goal was not autonomy for its own sake. The goal was compounding: each run should leave the next run better off.

## Findings That Changed The Architecture

### 1. Activation scenarios beat keyword triggers

The original skill frontmatter used quoted keyword lists like `"design agent tools"`, `"reduce tool complexity"`, etc. Those decayed fast: any rewording broke discovery, and the model could not distinguish neighboring skills with overlapping vocabularies.

Switching every skill description to a task-boundary statement let `check_activation_cases.py` actually measure routing. The first run of that checker immediately failed on `evaluation` vs `advanced-evaluation` and `project-development` vs `harness-engineering`. Those failures pointed at real wording problems, not contrived edge cases.

Takeaway: trigger lists feel concrete but are unstable scaffolding. Activation scenarios scale because they describe what the skill is for.

### 2. The mechanism registry became the encyclopedia backbone

The mechanism registry started as a way to make novelty detection smarter than token overlap. By the time it was wired through `novelty_check.py`, `validate_repo.py`, `corpus/index.json`, and the run state machine, it had become the canonical map of which behavior changes the corpus actually endorses.

Once mechanisms were first-class data with ledgers (`accepted.jsonl`, `rejected.jsonl`) and gated promotion, future runs gained free institutional memory. A new proposal can be compared against accepted patterns, candidate patterns, and explicitly rejected patterns from prior runs.

Takeaway: making the unit of knowledge machine-readable is the actual unlock. Markdown is a publication target, not a memory layer.

### 3. Deterministic gates caught the categorical failures

Every time `validate_repo.py` was tightened, it caught real bugs that had already shipped:

- Duplicate JSON keys in `source-evaluation.json`.
- Incorrect rubric math (recorded `weighted_total` did not match the dimension scores).
- `APPROVE` decisions on `partial` or `failed` retrievals.
- Mechanism registry entries with broken evidence paths.
- Activation cases pointing at unpublished skills.
- Run artifacts missing required pieces.
- Raw research dumps left at the repo root.

None of these required model judgment. They were structural. Spending tokens on judges before these gates exist was the wrong order of operations.

Takeaway: deterministic verification is cheaper than LLM judgment and catches a different class of failures. Build the structural validator first.

### 4. Prose logs are not enforceable

`THREAD.md` was useful for humans reading the history of a run. It was useless for telling another agent what the run was actually doing or whether it was safe to advance. The fix was `run-state.json` with explicit transitions and `state_history`, plus `validate_run.py` to enforce publish readiness independent of the prose log.

The first version of the state machine still passed validation while runs were intentionally incomplete. Splitting "is the corpus healthy" (`validate_repo`) from "is this run ready to ship" (`validate_run`) eliminated that ambiguity.

Takeaway: machine-readable state with explicit transitions is the difference between "the run looks ready" and "the run is ready". Prose logs should be the human surface, not the source of truth.

### 5. Closed-run reaping was the obvious bug

The first continuous loop would have parked closed runs forever. `loop_step.py` only advanced active runs, so a run that transitioned to `closed` via `research_loop.py close` would sit in `parked.jsonl` until the parked queue filled and the loop halted.

`reap_closed_runs()` is six lines. The missing piece was not complexity; it was recognizing that "the loop will eventually pick it up" was wishful thinking when no path existed.

Takeaway: queue-based systems need an explicit reaper for every state that exits the queue. Audit every terminal state and ask "who removes this entry?"

### 6. Concurrency bugs are invisible until you assume the daemon

`loop_discover.py` appended to `inbox.jsonl`. `loop_step.py` read `inbox.jsonl`, popped one item, and wrote the rest back. With manual usage this was fine. With launchd running both on overlapping schedules, discovery's appended items could be silently overwritten.

The fix was atomic writes (`tempfile` + `os.replace`) plus `fcntl` exclusive locks scoped per queue family. Cost was a small dependency on `fcntl` (Unix only, acceptable for macOS). The lock also had to be held through the subprocess that initialized the run, not released right after the pop, because otherwise two concurrent invocations would each pass the budget check and exceed `max_active_runs`.

Takeaway: as soon as the same files are touched by two cron jobs, append/replace patterns need atomic semantics and locks. There is no halfway design.

### 7. Adversarial benchmarks tested the harness, not the outputs

The benchmark harness exists to ask "what would it look like if someone tried to game this loop?" The scenarios are concrete attacks: duplicate mechanism with different wording, credible-author-but-generic content, unretrieved source cited as evidence, valid JSON with wrong rubric math, verbose skill draft that adds no behavior change, proposal that modifies the rubric used to approve itself.

Writing the attack first showed which gates were missing. Most of the validator hardening came from staring at adversarial scenarios and asking "would the current code catch this?"

Takeaway: write the failure modes before claiming the defense works. Adversarial fixtures are the cheapest way to find category-level gaps.

### 8. Claim provenance prevents claim rot

Skills accumulate numeric claims: BrowseComp variance percentages, LoCoMo accuracy numbers, multi-agent token multipliers, masking gain estimates. These age fast and humans never notice until the source is gone.

`researcher/claims/index.jsonl` makes each claim auditable: source URL, evidence strength, volatility, last reviewed date. `loop_daily.py` can flag high-volatility claims that have not been reviewed today. The validator enforces that owning skills exist and source paths resolve.

Takeaway: any claim that could rot needs explicit provenance. Burying them in prose is a guarantee that future agents will repeat them without checking.

### 9. Subagent reviews are a deterministic gate too

Multiple times in this experiment, an implementation was declared complete, then a `code-reviewer` subagent flagged concrete bugs: closed-run reaping, scheme allowlist on fetch, race condition on the inbox lock, dead config flags, redundant heuristics that silently passed broken runs. Each review pass moved the implementation from "looks right" to "is right".

This is cheap. A single review pass typically costs less than what it saves in production debugging. The review prompt that worked best was: "Focus only on HIGH-CONFIDENCE issues that would cause incorrect behavior, data loss, runaway resource use, or security risk. Skip stylistic comments."

Takeaway: treat code review as part of the build pipeline. Even adversarial scenarios miss class-of-error bugs that a fresh reader catches in minutes.

### 10. Live execution caught what paper review missed

After building the continuous loop, running it for 13 iterations live exposed:

- The pre-existing seed run got parked at "needs evaluation" because its source URL pointed at a Parallel research interaction, not the actual evidence files.
- Daily-budget timing depended on the test runs counting against the same day.
- Status dashboard short-circuited the launchd wrapper when loop_step exited 78 (no-op), preventing dashboard refresh on idle iterations.

None of these were visible from reading the code. All were obvious within minutes of running it.

Takeaway: end-to-end execution is the highest-signal validation for orchestration code. Unit tests of pieces will not catch state-machine timing or wrapper exit-code interactions.

### 11. Continuous operation is a separate architectural concern

The breakthrough roadmap delivered the right per-task primitives: validate_run, mechanism promotion, claim provenance, activation tests, benchmarks, corpus index. None of those answered "what runs this loop when no one is at the keyboard."

That answer required different machinery: queue, source discovery, scheduler (launchd), budgets, parking, reaping, status surfaces, runbook. Features and continuous operation are orthogonal concerns. Treating them as the same milestone hid the gap.

Takeaway: per-task correctness and continuous operation are different problems. Design them as separate layers and only couple them through file-based state.

### 12. Terminal states convert technical debt into documentation

The seed run started this experiment in flight, with a draft evaluation and a template proposal. Each repo-validation pass had to special-case it. Closing it as `reference-only` with a clear rationale converted it from "incomplete work" into "worked example of the lifecycle." Same files, different framing.

Takeaway: when in-flight artifacts will not be completed, give them a terminal state with an explicit reason. They become useful as examples instead of remaining as debt.

### 13. Token cost of structural validation is near zero

Validating the entire 14-skill corpus, all rubrics, all manifests, the mechanism registry, the claims index, the corpus index, activation cases, benchmark scenarios, and all run artifacts takes under a second of CPU and zero LLM tokens. There is no excuse for not running these checks on every PR and on every loop iteration.

Takeaway: cheap structural checks are the right floor. Spend model attention only on what cannot be deterministically verified.

### 14. The description-benchmark loop closes in ~2 hours and is the highest-leverage feedback loop in the system

This was the v2.3.0 finding. Stage 2 of the benchmark plan shipped real numbers across four frontier models, then we rewrote two skill descriptions based on the confusion matrix, then we re-ran the benchmark and measured the delta. End to end:

- Baseline benchmark: 50 prompts x 4 models x 3 reps = 600 runs (sequential, ~60 min; killed at 566 on first attempt and resumed via results-folder scan).
- Description rewrites for `context-fundamentals`, `tool-design`, `project-development` based on the baseline confusion matrix: ~10 minutes of focused writing.
- Re-run benchmark with same seed, same fixture: 600/600 runs in ~15 minutes (concurrency=4) with per-run progress logging.
- Delta report generation: 1 minute.

Total wall time end-to-end: under 2 hours including discussion. Result: `context-fundamentals` top-1 +23.4pp, `project-development` top-1 +25pp (now perfect), `tool-design` top-1 +7.8pp, three of four models gained on top-1, all four gained on top-3.

Three properties of the loop matter:

1. **Same seed, same fixture, same shuffles**. The only changing variable across the two runs was the descriptions. This is what lets the delta be attributed to the rewrites, not luck.
2. **Per-skill effect size is the unit of action**. Aggregate accuracy moves by ~1pp; individual skills move by 25pp. Reporting only the aggregate hides which descriptions need work.
3. **The confusion matrix tells you what to rewrite**. The baseline showed `context-fundamentals` leaking specifically to `context-degradation`, `project-development`, and `context-optimization`. The rewrite was guided by the exact direction of each leak. It is much harder to fix a description by re-reading it; it is straightforward to fix one by looking at which other skill claimed its territory.

Takeaway: for any system where description quality matters (skill routers, tool routers, RAG document selection), invest in a measurement loop early. The first run identifies the failures; the second run proves whether the fix worked. Without the second run, you do not actually know.

### 15. Description rewrites are incomplete without body alignment, and the router benchmark cannot catch that

The first v2.3.0 description-rewrite pass changed the one-line frontmatter `description` for three skills. The router benchmark validated that change (top-1 rates improved as predicted). The mistake was assuming the work was done.

The frontmatter description is what gets injected into a routing prompt. The SKILL.md body (`When to Activate`, `Practical Guidance`, `Examples`, `Integration`, `Gotchas`) is what gets loaded into the agent's context once the skill activates. These are two different surfaces with two different audiences. A description can route correctly while the body still steers the agent toward the wrong work.

Concrete instance: after the description rewrite, `context-fundamentals` correctly routed to itself for foundational prompts, but its body still listed "Optimizing context usage to reduce token costs or improve performance" as a `When to Activate` trigger. The moment the skill activated for a real task, the agent saw operational ownership claims that contradicted the description that got it there. The router benchmark (which runs with `settingSources: []` and only sees descriptions) had no way to surface this gap.

Three fixes:

1. Treat "rewrite the description" and "align the body" as two work items, not one. The first is cheap and benchmark-measurable; the second is cheaper still but invisible to the router benchmark and only measurable in Stage 3 effectiveness tests where the body actually loads.
2. The `When to Activate` body section is the highest-leverage body content. It is loaded immediately, parsed by the model, and acts as a second routing surface inside the skill. A `When to Activate` that contradicts the frontmatter `description` is worse than no `When to Activate` at all.
3. The `Integration` section is the cross-reference layer. After every description rewrite, every sibling skill's `Integration` should be checked for stale routing claims. A skill that says "for X, go to old-skill-name" when X has been re-homed introduces real routing damage.

Takeaway: any time a skill's scope is narrowed at the description level, audit the body the same day. A skill is a multi-surface artifact; consistency across surfaces is part of the change.

### 16. Concurrency, resume, and per-run logging are the three non-negotiable runner features

The v1 router runner ran sequentially, had no resume capability, and printed nothing per-run. The sweep died at 566 of 600 and we did not know:

- That it had died (no per-run output meant the stalled state was invisible).
- How far it had gotten (had to count files in the results directory).
- That we would have to redo everything (no resume meant any restart was a full do-over).

The v2 runner has all three. The v2 sweep ran in 15 minutes with full visibility and complete coverage. Same code path, same SDK, same models. The May 19 corpus-hardening sweep added one more operational lesson: transient empty/format-failed SDK responses should be retried once before being counted. The full 600-record sweep initially had 15 format failures, all of which completed successfully when rerun through resume. The runner now has an automatic format-failure retry.

Takeaway: any runner that calls a paid API in a loop needs: bounded parallelism with a concurrency flag; resume that scans the results directory and skips completed work; per-run progress logging that surfaces stalls in less than the time it takes to finish one call; and one retry for transient empty or unparsable outputs. These are not optimization. They are baseline competence.

### 17. A skill is not improved until the corpus metadata improves with it

The user was right to call out the shortcut. Rewriting descriptions and aligning three skill bodies was not enough. It improved the router surface, but it left the rest of the corpus with uneven body standards, missing mechanism ownership, weak claim provenance, and untested activation boundaries.

The corpus-wide hardening pass changed the unit of work from "fix the skills the benchmark complained about" to "make every skill pass the same publication standard." That meant:

- Every skill body got explicit ownership boundaries and adjacent `Do not activate` routes.
- Structurally weak bodies (`bdi-mental-states`, `hosted-agents`) gained practical guidance and examples.
- Every skill was mapped to at least one accepted mechanism in `researcher/mechanisms/registry.jsonl`.
- Volatile numeric/vendor claims were softened or tied to `claim-*` IDs with concrete source paths.
- Activation fixtures grew to cover previously untested skills, not just the benchmark-confused ones.
- `validate_repo.py --strict` was tightened so required body sections and non-activation boundaries are enforced.

The result was measurable without another paid SDK sweep: skill health moved from 0.8111 with two flagged skills to 0.9117 with zero flagged skills; strict validation passed with zero warnings; activation cases passed 19/19; adversarial deterministic benchmarks passed 7/7 scenarios.

Takeaway: auto-research should improve three layers at once: prose, metadata, and gates. If only the prose changes, the corpus becomes prettier but not more self-improving.

## What This Experiment Did Not Solve

Honest list, not aspirations:

- **No LLM judge adapter**: `retrieved -> evaluated` and `proposed -> novelty_checked` still require human or future judge action. The contract is in place; the cost-gated implementation is not.
- **No automated source discovery beyond the manual seed**: feed adapters for Parallel deep research, web search, RSS, and academic preprints are placeholders.
- **No log rotation**: per-script logs grow indefinitely. Acceptable for weeks, not years.
- **No pytest suite**: scripts are smoke-tested via live execution and the deterministic gates. Real unit/integration tests would catch refactor regressions earlier.
- **No full-body effectiveness benchmark yet**: deterministic health now measures skill-body structure, but Stage 3 still needs real agent tasks with and without full skills loaded.

## Reusable Patterns For Future Work

Patterns from this experiment that are worth carrying into other agentic systems:

1. **Run state in a JSON file plus an append-only thread log**. State governs automation, thread governs humans.
2. **Queue + inbox + parked + done + quarantine** as the minimum durable surface for any agent that processes work.
3. **Atomic writes (`tempfile` + `os.replace`) plus `fcntl` locks** as the default whenever two processes share a file.
4. **Mechanism registry with gated promotion** as the way to accumulate "what we have learned" without ad hoc edits.
5. **Activation regression fixtures** for any skill-router style component that uses descriptions to route tasks.
6. **Adversarial benchmarks before model judges** for any harness that decides whether to publish or merge.
7. **Closed-state reaper** in every queue.
8. **Split validators by question** ("is the corpus healthy" vs "is this run ready") instead of one validator per artifact.
9. **Run live before declaring done** for any orchestration code.
10. **Treat continuous operation as a separate milestone** from per-task correctness.
11. **The description-benchmark loop** for any system where natural-language descriptions affect routing: baseline benchmark, read the confusion matrix, rewrite based on specific leak directions, re-run with the same seed and fixture, publish the delta.
12. **Resume-by-results-folder-scan + bounded concurrency + per-run progress logging + format-failure retry** as the non-negotiable runner features for any paid-API loop.
13. **Audit the body the same day the description changes.** A skill is a multi-surface artifact; the `When to Activate` body section is a second routing surface and must not contradict the frontmatter description. The router benchmark cannot catch body-vs-description inconsistencies because router prompts only contain descriptions.
14. **Update prose, metadata, and gates together.** A skill improvement is incomplete until the body text, mechanism registry, claim provenance, corpus index, activation fixtures, and validators all agree.

## How To Use This Document

When extending the researcher OS or designing similar systems, read this before writing new infrastructure. Most of the friction in this experiment came from making the same shape of mistake (silent failure modes, missing reapers, prose-only state, deterministic checks deferred) in different concrete forms. Knowing the shape lets you skip the mistake.

If a future change here invalidates one of these findings, update this file in the same PR.
