---
name: context-benchmarking
description: Set up benchmarking feedback loops, prevent recall regressions, operationalize evaluation in CI...
---
# Context Benchmarking

Use this skill when you need to set up a benchmarking feedback loop for context engineering strategies, prevent regression in retrieval quality, or operationalize evaluation workflows in CI pipelines.

Context benchmarking is the practice of continuously measuring whether your context engineering strategies (compression, optimization, memory retrieval) are performing as expected — and catching regressions before they reach production.

---

## When to Use This Skill

- After modifying a `context-compression` or `context-optimization` strategy
- Before merging changes that affect retrieval logic or memory systems
- When you need to prove that a new skill doesn't degrade existing agent performance
- When setting up a production agent system that needs quality gates

---

## Core Concepts

### The Benchmarking Feedback Loop

A benchmarking feedback loop has four stages:

1. **Baseline** — Record current performance metrics before any changes
2. **Change** — Apply a new compression, optimization, or retrieval strategy
3. **Measure** — Run the same test set against the new strategy
4. **Compare** — Flag regressions if metrics drop below acceptable thresholds

Without a baseline, you cannot know if you improved or regressed. Always record a baseline first.

### Key Metrics

Two metrics are in tension in context engineering:

**Latency** — How fast does the agent respond?
- Measures: time-to-first-token, total response time
- Compression usually improves latency by reducing input tokens
- Target: no more than 10% latency increase after context changes

**Recall** — Does the agent retain the right information?
- Measures: whether key facts from the original context survive compression or retrieval
- Compression can hurt recall if implemented poorly
- Target: recall score above 0.85 on your test set

The fundamental tradeoff: aggressive compression improves latency but risks recall degradation. Benchmarking makes this tradeoff visible and measurable instead of invisible and dangerous.

### Regression Prevention

A regression is when a change makes performance worse than the baseline. Regressions in context engineering are especially dangerous because they are silent — the agent still responds, but with lower quality answers.

Regression prevention requires:
- A fixed test set that does not change between runs (changing the test set invalidates comparisons)
- A threshold below which a run is considered failing (e.g., recall < 0.80 fails)
- A record of historical scores to detect gradual drift, not just sudden drops

```python
# Pseudocode: regression check pattern
baseline_recall = load_baseline_score("recall")
current_recall = run_benchmark(test_set)

if current_recall < baseline_recall * 0.95:  # 5% tolerance
    raise RegressionError(f"Recall dropped: {baseline_recall} -> {current_recall}")
```

---

## Designing Your Test Set

A good benchmark test set has three properties:

**Coverage** — Test cases should exercise all the context strategies you care about. Include cases that specifically stress compression (long documents), retrieval (needle-in-haystack), and memory (multi-turn recall).

**Stability** — Test cases must not change between runs. Store them in a versioned file. If you need to update the test set, update the baseline at the same time.

**Ground truth** — Each test case needs an expected answer or a rubric. Without ground truth, you cannot automate scoring.

```
# Recommended test set structure
test_cases/
├── compression_tests.json    # Tests for context-compression skill
├── retrieval_tests.json      # Tests for memory-systems skill
└── optimization_tests.json   # Tests for context-optimization skill
```

Each test case should contain:
- `id` — unique identifier for tracking regressions to specific cases
- `input` — the context or document to process
- `question` — what the agent should be able to answer after processing
- `expected_facts` — the key facts that must survive compression/retrieval
- `rubric` — scoring criteria (used by the LLM judge)

---

## Using LLM-as-Judge for Scoring

Manual scoring does not scale. Use an LLM judge to score agent outputs against your rubric automatically. This is the pattern established in the `advanced-evaluation` and `evaluation` skills.

The judge prompt should:
1. Receive the original context, the compressed/retrieved output, and the expected facts
2. Score each expected fact as present (1) or missing (0)
3. Return a structured score with per-fact results for debuggability

```python
# Pseudocode: judge scoring pattern
def score_with_judge(original, output, expected_facts):
    prompt = f"""
    Original context: {original}
    Agent output: {output}
    Expected facts: {expected_facts}
    
    For each expected fact, score 1 if present in output, 0 if missing.
    Return JSON: {{"scores": [{{"fact": str, "score": int, "reason": str}}]}}
    """
    response = llm.complete(prompt)
    return parse_scores(response)
```

Recall score = (sum of fact scores) / (total expected facts)

---

## Safeguards for Automated Testing

Running benchmarks in CI requires cost controls. LLM API calls are not free.

**Trigger control** — Never run benchmarks on every push. Use:
- `workflow_dispatch` for manual runs only
- PR labels (e.g., `run-benchmark`) so only maintainers can trigger benchmark runs on PRs
- Scheduled runs (e.g., weekly) for baseline drift detection

**Token budgeting** — Estimate cost before running. A test set of 20 cases at 2000 tokens each = 40,000 input tokens per run. At typical API pricing, this is negligible, but larger test sets can surprise you.

**Timeout guards** — Set a maximum runtime. If a benchmark run exceeds it, fail loudly. Infinite loops in agent code can consume unbounded API budget.

**Result caching** — Cache judge scores for inputs that have not changed. If a test case input is identical to a previous run, reuse the cached score instead of calling the API again.

---

## Interpreting Results

After a benchmark run, you will have:
- An overall recall score
- Per-test-case scores (to identify which cases regressed)
- A latency measurement
- A pass/fail determination

A failing run should block merging. A passing run should update the recorded baseline only if the score improved — never overwrite a higher baseline with a lower one.

When a specific test case consistently fails, that case reveals a weakness in your context strategy. Treat it as a signal to improve the strategy, not to remove the test case.

---

## Connections to Other Skills

This skill operationalizes the theory established in:
- `context-compression` — benchmarking validates that compression preserves recall
- `context-optimization` — benchmarking measures the latency/recall tradeoff of optimization strategies
- `advanced-evaluation` — the LLM-as-judge scoring pattern used here comes from that skill
- `evaluation` — foundational evaluation framework this skill extends into CI

Start with `evaluation` and `advanced-evaluation` before implementing this skill. They establish the scoring primitives this skill builds on.

---

## Metadata

```
Created: 2026-03-06
Author: Agent Skills for Context Engineering Contributors
Version: 1.0.0
Triggers: "set up benchmarking", "prevent context regression", "automate evaluation", "CI benchmark", "measure recall degradation"
```