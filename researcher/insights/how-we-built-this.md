# How We Built v2.3.0

> Historical, non-normative experiment and release narrative. Statements below
> about unattended launchd execution, HTTP retrieval, retry/quarantine
> automation, accepted closure, mechanism promotion, executed adversarial
> scenarios, and live SDK benchmarks describe earlier revisions, not the current
> repository boundary. Launchd entry points are inert; runtime ledgers require
> explicit initialization; the legacy loop has no network path, acceptance, or
> promotion authority; scenario records are catalog-only; the SDK runner is
> zero-call. Use the supervised runbook for current operator guidance.

A narrative companion to `auto-research-experiment.md`. That document captures the technical findings. This one captures the process: what we read, how we worked, what each session produced, what shipped, and how to talk about it without overselling.

If you want the engineering rationale, read `auto-research-experiment.md`. If you want the project story or templates for sharing it, read this.

## Origins

The starting question was small and concrete: how do we keep this skill repository alive without it becoming a one-person editorial backlog. The 10k stars made the answer matter; the absence of a curation pipeline made it urgent.

Three pieces of prior work shaped the design.

### Karpathy's autoresearch

[karpathy/autoresearch](https://github.com/karpathy/autoresearch) is the smallest interesting autonomous experimentation harness. It has one editable file (`train.py`), one locked evaluator (`prepare.py`), one scalar metric, a `results.tsv` results log, fixed wall-clock budgets, and `git` rollback on non-improving attempts. That is the entire harness.

The lesson it teaches is not that every loop needs one scalar metric. The lesson is that ambiguous feedback produces ambiguous autonomy. If the agent can change the evaluator, it will eventually optimize the benchmark instead of the task.

This became the architectural seed for our `locked-editable-surfaces` mechanism: classify every file as locked, editable, append-only, or human-controlled before the loop starts.

### Prime Intellect's auto-NanoGPT

[primeintellect.ai/auto-nanogpt](https://www.primeintellect.ai/auto-nanogpt) showed what durable agent state looks like in practice. Their `THREAD.md` pattern, the source queue files, the rejected-attempt log, the explicit handover summary at the bottom of each thread: these are not nice-to-haves. They are the difference between a loop that survives context compaction and one that does not.

This became our `durable-research-thread` mechanism and the run-directory layout we ship today: every run has `THREAD.md`, `sources/queue.jsonl`, `proposals/`, `reports/`, and `logs/`.

### Parallel deep research on autonomous research frameworks

We then ran a targeted deep-research query through Parallel (interaction `trun_64f5be03055a4b52adf17481e4b865bc`) asking specifically how to build an autonomous research-to-skill system inside a file-based repository. The raw output is preserved under the seed run's `sources/evidence/raw/` directory. The findings that survived rubric scoring became the v2.2.0 architecture:

- Deterministic validation harnesses as the locked evaluator.
- Durable scratchpads and THREAD-style logs for auditability.
- Novelty gates to prevent redundant skill revisions.
- Pairwise skill revision evaluation for competing drafts.
- Auto-PR workflows that prepare changes but never auto-merge.

All five made it into the published harness. The deep-research summary at `researcher/runs/20260515-035228-executable-autonomous-research-frameworks/sources/evidence/deep-research-summary.md` is the worked-example artifact.

## How We Worked

The collaboration ran across multiple sessions. The pattern that worked was always the same:

```
research -> plan -> implement -> review -> harden -> verify
```

### Mode switching

When the next step was unclear or had real architectural trade-offs, the conversation went into plan mode. The plan was written, the user approved it, then the conversation switched back to agent mode for execution. This matters because the plan became a contract that future steps could be checked against, and it stopped premature implementation on ambiguous goals.

### Subagent reviews

After every meaningful batch of implementation, a `code-reviewer` subagent was invoked with a tightly scoped prompt: "find only HIGH-CONFIDENCE issues that would cause incorrect behavior, data loss, runaway resource use, or security risk. Skip stylistic comments."

Those reviews found bugs the implementation pass missed:

- Closed runs would never be reaped (the loop would silently fill `parked.jsonl` until it halted).
- `write_jsonl` was non-atomic and could corrupt queue files on kill mid-write.
- `pop_inbox_item` released the lock before `init_run`, so two concurrent loop_step invocations could exceed `max_active_runs`.
- The HTTP fetcher accepted `file://` and `data:` schemes (SSRF/LFI risk).
- The launchd wrapper short-circuited the status refresh when `loop_step` exited 78 (no work).
- URL deduplication used the raw URL while `source_id` hashed the normalized form.

Each of these had a one-line root cause and a clean fix once surfaced. None would have shown up in unit tests of individual functions because they were interactions between components.

### Live execution as a deterministic gate

The continuous loop was built and then actually run for thirteen iterations during the session: discovered eight sources from a manual seed, initialized six runs (capped by the daily budget), fetched four sources via stdlib HTTP totalling about 1.7 MB, parked five runs at the correct gates, closed one run and watched the reaper move it to `done.jsonl`.

This is mundane in description but high-signal in practice. Half the bugs above were only obvious because the live execution exposed them. Paper review of orchestration code consistently misses interaction bugs.

### Tools that mattered

- `code-reviewer` subagent: caught the compound failures listed above.
- `code-explorer` subagent: mapped the existing skill corpus before designing the breakthrough roadmap.
- `code-architect` subagent: produced the first draft of the evaluation strategy that became the benchmark harness.
- Parallel deep research: provided the architectural recommendations that the rubrics later turned into accepted mechanisms.
- DeepWiki: already linked from the README; useful for reviewers who want a higher-level overview without reading every skill.

## Stage 2: The Description-Benchmark Loop Closes

The narrative above ends with v2.2.0 shipping the scaffolding. v2.3.0 is the chapter where the scaffolding produces measurements that change what gets written.

### The first run was honest about its own failures

The v2.2.0 router benchmark sweep ran 566 of 600 calls before the sequential runner stalled silently. The aggregate numbers across four models (composer-2, claude-opus-4-7, gpt-5.5, gemini-3.1-pro) clustered at ~88.6% top-1, which sounded fine until we looked at the per-skill confusion matrix.

One skill carried almost all of the routing failure: `context-fundamentals` was predicted correctly only 12 of 47 times. The rest split across `context-degradation` (12), `project-development` (12), `context-optimization` (8). A second pair, `tool-design` vs `project-development`, leaked symmetrically at ~25%. The other 11 skills were near-perfect.

### What we changed

Two interventions, both small:

- Rewrote `context-fundamentals` to be unambiguously about conceptual foundations. The old description claimed ownership of "designing agent architectures," "debugging context quality issues," and "setting context budgets" - all of which belong to other skills. The new description explicitly routes operational work to the specialized skills.
- Rewrote `tool-design` and `project-development` with explicit cross-references to each other. The old descriptions both mentioned "architectural" or "structuring" framings that overlapped. The new descriptions define the unit of work: tool-design owns single-tool decisions; project-development owns project-shape decisions; each routes the other.

We also fixed the runner so the next sweep would not silently die: bounded parallelism (concurrency=4), resume capability (scans results folder on startup), and per-run progress logging.

### What we measured

The second sweep ran 600/600 in 15 minutes (4x speedup from concurrency). Per-skill effect sizes for the three targeted descriptions:

- `context-fundamentals`: 0.255 -> 0.489 (**+23.4pp**)
- `project-development`: 0.750 -> 1.000 (**+25pp**, now perfect routing)
- `tool-design`: 0.729 -> 0.807 (**+7.8pp**)

Aggregate top-1: 0.888 -> 0.900. Three of four models gained on top-1; all four gained on top-3. Format compliance: 99.5% across 600 calls. Total Cursor SDK cost: ~$7.20.

### Why this matters more than the absolute numbers

The aggregate moved by ~1pp; individual skills moved by 25pp. **The aggregate is the wrong unit**. The confusion matrix tells you which descriptions need work and which directions the leakage goes. The delta-vs-baseline comparison tells you whether the fix worked. Without per-skill effect sizes, this entire feedback loop is invisible.

End to end from "the v2.2.0 benchmark finished" to "v2.3.0 measured the rewrites" was under two hours of focused work. This is the cheapest, highest-leverage feedback loop in the system. Future contributions should run it whenever a skill description changes.

### The shortcut we corrected

The first post-benchmark fix was too narrow: rewrite three descriptions, align those three bodies, and call the release ready. That improved the measured router surface, but it did not make the whole repo better through auto-research.

The correction was a corpus-wide hardening pass. Three read-only audits looked at activation boundaries, mechanism and claim coverage, and the skill-quality standard. Then every skill was brought under the same rule: explicit owned scope, explicit adjacent routes, practical guidance an agent can execute, examples, gotchas, integration as a boundary map, and machine-readable mechanisms/claims where the prose makes reusable or volatile claims.

Concrete result:

- `bdi-mental-states` and `hosted-agents` were no longer structural outliers; both gained missing practical guidance/examples and passed strict health.
- Mechanisms increased from 5 to 16, so every skill now owns at least one accepted behavior pattern.
- Claim provenance increased from 6 to 12, with concrete repo source paths replacing vague research-run summaries.
- Activation fixtures increased from 14 to 19, covering previously untested skills.
- `validate_repo.py --strict` now enforces full body sections and explicit non-activation boundaries.
- Skill health moved from 0.8111 with 2 flagged skills to 0.9117 with 0 flagged skills.
- A fresh 600-record router sweep on May 19 verified the corpus-wide pass did not introduce broad routing collapse: 0 format failures after retrying transient blanks, Gemini 0.920 top-1, Composer 0.913, GPT-5.5 0.913, Claude Opus 4.7 0.840. The remaining failures are still concentrated in ambiguous/negative-control prompts and the `context-fundamentals` catch-all boundary.

This is the release's real lesson: improving a skill corpus means changing prose, metadata, and gates together. A prettier SKILL.md without updated mechanisms, claims, corpus index, fixtures, and validators is not self-improving.

### What v2.3.0 inherits from v2.2.0

Everything that shipped in v2.2.0 is still here: the file-based researcher operating system, the run state machine, the continuous loop, the launchd service definitions, the deterministic gates, the adversarial benchmark scenarios. v2.3.0 adds the measured results and the description fixes that those results justified.

## What v2.3.0 Actually Ships

Five concrete pieces of infrastructure, plus a corpus-wide hardening pass across all 15 skills:

1. **Researcher operating system** under `researcher/`: source registry, content/skill/harness rubrics, pairwise revision rubric, mechanism registry, mechanism ledgers, claim provenance index, corpus index, activation regression fixtures, adversarial benchmark scenarios with goldens, append-only benchmark history.

2. **Run state machine**: every run has `run-state.json` with explicit transitions (`initialized -> retrieved -> evaluated -> proposed -> novelty_checked -> validated -> pr_ready -> closed`). `research_loop.py` advances state via subcommands; `validate_run.py` enforces publish readiness without false positives on intentionally incomplete runs.

3. **Continuous loop**: `loop_discover.py`, `loop_step.py`, `loop_daily.py`, `loop_status.py`. Backed by `researcher/queue/` (inbox, parked, done, quarantine) with atomic JSONL writes and `fcntl` locks. Runs unattended from launchd; never invokes paid LLMs; HTTP retrieval is stdlib-only with a 1.5 MB cap and a 30-second timeout.

4. **CI**: `.github/workflows/validate.yml` runs Python compile, `validate_repo.py --strict`, `check_activation_cases.py`, and `run_benchmarks.py` on every push and PR.

5. **Documentation**: `CHANGELOG.md`, refreshed `README.md` / `CLAUDE.md` / `CONTRIBUTING.md`, `AGENTS.md` for workspace memory, `researcher/runs/README.md` for operator orientation, and the two insight documents (this one and `auto-research-experiment.md`).

By the numbers: 15 published skills, **16 accepted mechanisms**, **12 provenance-tracked claims**, **19 activation cases** (up from 8), 7 adversarial benchmark scenarios, 1 worked-example seed run, 50 router benchmark prompts, **1,800 completed router benchmark records** across three sweeps (baseline, post-description rewrite, post-corpus hardening), 4 frontier models evaluated, 1 worked-example effectiveness task scaffolded, and a strict skill-health score of **0.9117 with 0 flagged skills**.

## What You Should Tell People

### What was built

A skill collection that can keep itself alive. Not a one-off skill drop. A file-based research-to-skill operating system that:

- Discovers candidate sources from a curated registry.
- Scores them against locked rubrics that the agent cannot relax.
- Extracts implementable mechanisms instead of generic takeaways.
- Promotes only behaviors that survive both deterministic checks and human review.
- Runs the whole thing in a continuous loop without spending a single LLM token on retrieval or judgment.
- Falls back to a human review queue for anything that needs judgment.

### Why it matters

Most public skill collections are anthologies. They accumulate good content and then drift, because there is no process for keeping them current and no machine-readable layer for compounding what they know. v2.2.0 is the bet that an open repository can be more than that: a source of truth that improves with use.

### Concrete artifacts you can point to

- The mechanism registry: `researcher/mechanisms/registry.jsonl`
- The claim provenance index: `researcher/claims/index.jsonl`
- The corpus index: `researcher/corpus/index.json`
- The run state machine in action: `researcher/runs/20260515-035228-executable-autonomous-research-frameworks/`
- The adversarial benchmark harness: `researcher/benchmarks/`
- The continuous loop scripts: `researcher/scripts/loop_*.py`
- The launchd daemon installer: `researcher/orchestration/launchd/install.sh`
- The runbooks: `researcher/runbooks/`
- The technical findings: `researcher/insights/auto-research-experiment.md`

### Sound bites that survive copy-paste

- "Activation scenarios beat keyword triggers." (Documented as finding #1.)
- "Deterministic gates before model judges." (The validator costs zero tokens and catches categorical failures the judge would miss.)
- "Mechanism registry as encyclopedia backbone." (Making behavior changes first-class data is the unlock.)
- "Closed-run reaping is non-negotiable." (Every queue needs an explicit exit path.)
- "Adversarial benchmarks before declaring the harness safe." (Write the attack before claiming the defense.)
- "Continuous operation is a separate milestone from per-task correctness."
- "Live execution is the highest-signal validation for orchestration code."

## Templates For Sharing

Use these as starting points, not as final copy. Strip what is not true for your audience.

### X / Twitter thread (8 tweets)

```
1/  Shipped v2.2.0 of the Agent Skills for Context Engineering repo.

It is no longer just a skill collection. It is a file-based research-to-skill operating system that keeps the corpus alive without becoming editorial debt.

github.com/muratcankoylan/Agent-Skills-for-Context-Engineering

2/  Origins: Karpathy's autoresearch showed that one editable file + one locked evaluator + a results log + git rollback is enough for autonomy. Prime Intellect's auto-nanoGPT showed why durable scratchpads matter. Parallel deep research filled in the rest.

3/  What it does: discovers sources from a curated registry, scores them against locked rubrics, extracts implementable mechanisms (not generic takeaways), promotes only behaviors that pass deterministic checks plus human review.

4/  Mechanism registry as encyclopedia backbone. Every accepted behavior change is a JSONL row with owning_skill, activation_scenario, behavior_change, evidence, and failure_modes. Novelty checks compare against the registry first, then the corpus.

5/  Claim provenance for every volatile number. BrowseComp variance, LoCoMo accuracy, multi-agent token multipliers: each has a claim_id, source_url, evidence_strength, volatility, and last_reviewed. Claims that rot will not silently propagate.

6/  Continuous loop runs from launchd on macOS. No paid LLMs. HTTP retrieval is stdlib-only. Atomic JSONL writes, fcntl locks, closed-run reaping, parked-review queue, daily ops with adversarial benchmarks against the harness itself.

7/  CI is the floor. validate_repo + run_benchmarks + check_activation_cases on every PR. The validator catches duplicate JSON keys, wrong rubric math, APPROVE on partial retrievals, manifest drift, and missing run artifacts before any model judge runs.

8/  Lessons in researcher/insights/. Headline findings: activation scenarios beat keyword triggers, deterministic gates before model judges, closed-run reapers are non-negotiable, adversarial benchmarks find what unit tests miss, live execution > paper review for orchestration.
```

### LinkedIn post

```
Released v2.2.0 of Agent Skills for Context Engineering: an open collection that now ships a file-based research-to-skill operating system with deterministic gates and a continuous loop.

The starting question was small: how do you keep a 10k-star skill repository alive without it becoming a one-person editorial backlog. The answer turned into infrastructure.

Three pieces of prior work shaped the design.

Andrej Karpathy's autoresearch repo demonstrated the minimal autonomy harness: one editable file, one locked evaluator, a results log, git rollback. The lesson is not that every loop needs a single scalar metric. It is that ambiguous feedback produces ambiguous autonomy.

Prime Intellect's auto-nanoGPT work showed why durable agent state matters in practice. Their THREAD.md pattern, source queues, and explicit handover summaries are the difference between a loop that survives context compaction and one that does not.

Targeted deep research filled in the missing pieces: deterministic validation as the locked evaluator, durable run directories, novelty gates, pairwise revision, human-controlled merge.

What shipped:
- Mechanism registry with gated promotion and append-only ledgers
- Claim provenance for volatile benchmark numbers
- Run state machine with enforceable transitions
- Activation regression tests for skill-boundary confusion
- Adversarial benchmark harness with append-only history
- Continuous loop scripts and launchd service definitions
- CI workflow running deterministic gates on every PR
- 15 skills, all migrated from keyword triggers to task-boundary scenarios

The technical findings and the full process narrative live in researcher/insights/. The repo: github.com/muratcankoylan/Agent-Skills-for-Context-Engineering

Honest scope: no LLM-judge adapter yet, no automated source discovery beyond the manual seed, no log rotation. Tracked at the end of CHANGELOG.md.
```

### Blog post outline

```
# Title: From Karpathy's autoresearch to a self-compounding skill encyclopedia

## 1. Why this exists
The 10k-star skill repository was at a fork: stay an anthology, or become infrastructure.

## 2. The three inputs
- Karpathy autoresearch: minimal autonomy harness, locked evaluator, results log
- Prime Intellect auto-nanoGPT: durable scratchpads, THREAD.md, handover discipline
- Parallel deep research on autonomous research frameworks: deterministic gates, novelty, pairwise, human-controlled merge

## 3. The breakthrough roadmap
- Split repo health from run readiness
- Mechanism registry as the unit of accumulated learning
- Claim provenance to prevent claim rot
- Activation regression for skill boundaries
- Adversarial benchmarks instead of self-congratulatory ones
- Corpus index as the machine-readable map

## 4. The continuous loop
- Queue + state machine + reaper + parked review
- launchd daemon, no paid LLMs, atomic writes, fcntl locks
- Live execution as the validation gate

## 5. The lessons
(17 findings from researcher/insights/auto-research-experiment.md)

## 6. What it does not solve yet
Honest list of out-of-scope items

## 7. How to use it
- Install the plugin (Claude Code, Cursor, Open Plugins)
- Install the daemon (macOS launchd)
- Read the runbook before extending
```

## How To Improve The Repo From Here

The 2.2.0 release deliberately left several things off. These are the obvious next steps in roughly the order they pay off:

1. **LLM-judge adapter** for the `retrieved -> evaluated` transition, gated by a per-day budget config. This is the single change that unlocks "the loop actually decides what to publish" instead of "the loop stages everything for human review."

2. **Automated source discovery adapters**. Parallel deep research, a Cohere/OpenAI/Anthropic engineering blog RSS, an arXiv author-watch list. Each is a self-contained file under `researcher/scripts/feeds/`.

3. **Log rotation and benchmark history pruning**. The current implementation appends forever. Acceptable for weeks, painful at one year.

4. **pytest suite** for the loop scripts. Smoke-tested via live execution is fine for v2.2.0; refactor safety needs unit and integration tests.

5. **More activation cases** as skill boundaries get challenged in the wild. Each confusion that shows up in user activations should become a fixture.

6. **More claim provenance**. The current 12 claims cover the highest-volatility ones; the corpus has additional softer claims that would benefit from explicit provenance.

7. **Self-spawning agents for parallel runs**. The loop currently processes one run per step. With proper locking and per-run budget tracking, parallel runs are safe and would amortize cost.

8. **Cross-skill integration tests**. The corpus index already maps skills to mechanisms; the next step is asserting that integration sections in each skill reference real skills and stay accurate as the corpus evolves.

If you want to contribute, look at the open items above. Each is scoped to fit in a single PR.

## Your Learnings (Best Inference From The Process)

This section is necessarily an inference. Adjust before sharing.

- A repository with this many stars is a public surface, and that surface benefits more from infrastructure than from more content. The instinct to add another skill is almost always less valuable than the instinct to add another gate.
- The cheapest way to compound a knowledge base is to make its units machine-readable. Mechanisms, claims, activation scenarios, run states, benchmark scenarios. Prose is publication, not memory.
- "Improve all skills" means improving the corpus substrate, not just editing Markdown. The mechanism registry, claim index, corpus index, activation cases, validators, and template have to move with the skill bodies.
- "Run it for days" is a real architectural milestone, not a feature flag. The system has to be designed for unattended operation from the beginning.
- Subagent code review is the cheapest way to find category-of-error bugs that you would otherwise hit in production.
- Plan mode for irreversible decisions, agent mode for everything else. Mixing them silently is how scope creep happens.
- An AI collaborator works best as a load-bearing technical lead, not as a writing assistant. Direct instructions, named subagents, explicit budgets, deterministic gates: this is how the work compounds rather than dissipates.

## Joint Findings From The Experiment

These are documented in detail in `auto-research-experiment.md`. The five most reusable across other projects:

1. Atomic file writes + fcntl locks are the default for any shared file the loop touches.
2. Closed-state reapers in every queue.
3. Split validators by question, not by artifact.
4. Adversarial benchmarks before model judges.
5. Live execution as the highest-signal validation for orchestration code.

## What This Document Is For

This file is the narrative version of the release. Use it when explaining what was built and why. Use `auto-research-experiment.md` when explaining the engineering decisions. Use `CHANGELOG.md` when you need the precise inventory.

Keep all three accurate as the next versions ship.
