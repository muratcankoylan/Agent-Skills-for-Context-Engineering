---
name: evaluation
description: This skill should be used when the user asks to "evaluate agent performance", "build test framework", "measure agent quality", "create evaluation rubrics", or mentions LLM-as-judge, multi-dimensional evaluation, agent testing, or quality gates for agent pipelines.
---

# Evaluation Methods for Agent Systems

Evaluate agent systems differently from traditional software because agents make dynamic decisions, are non-deterministic between runs, and often lack single correct answers. Build evaluation frameworks that account for these characteristics, provide actionable feedback, catch regressions, and validate that context engineering choices achieve intended effects.

## When to Activate

Activate this skill when:
- Testing agent performance systematically
- Validating context engineering choices
- Measuring improvements over time
- Catching regressions before deployment
- Building quality gates for agent pipelines
- Comparing different agent configurations
- Evaluating production systems continuously

## Core Concepts

Focus evaluation on outcomes rather than execution paths, because agents may find alternative valid routes to goals. Judge whether the agent achieves the right outcome via a reasonable process, not whether it followed a specific sequence of steps.

Use multi-dimensional rubrics instead of single scores because one number hides critical failures in specific dimensions. Capture factual accuracy, completeness, citation accuracy, source quality, and tool efficiency as separate dimensions, then weight them for the use case.

Deploy LLM-as-judge for scalable evaluation across large test sets while supplementing with human review to catch edge cases, hallucinations, and subtle biases that automated evaluation misses.

**Performance Drivers: The 95% Finding**

Apply the BrowseComp research finding when designing evaluation budgets: three factors explain 95% of browsing agent performance variance.

| Factor | Variance Explained | Implication |
|--------|-------------------|-------------|
| Token usage | 80% | More tokens = better performance |
| Number of tool calls | ~10% | More exploration helps |
| Model choice | ~5% | Better models multiply efficiency |

Act on these implications when designing evaluations:
- **Set realistic token budgets**: Evaluate agents with production-realistic token limits, not unlimited resources, because token usage drives 80% of variance.
- **Prioritize model upgrades over token increases**: Upgrading model versions provides larger gains than doubling token budgets on previous versions because better models use tokens more efficiently.
- **Validate multi-agent architectures**: The finding supports distributing work across agents with separate context windows, so evaluate multi-agent setups against single-agent baselines.

## Detailed Topics

### Evaluation Challenges

**Handle Non-Determinism and Multiple Valid Paths**

Design evaluations that tolerate path variation because agents may take completely different valid paths to reach goals. One agent might search three sources while another searches ten; both may produce correct answers. Avoid checking for specific steps. Instead, define outcome criteria (correctness, completeness, quality) and score against those, treating the execution path as informational rather than evaluative.

**Test Context-Dependent Failures**

Evaluate across a range of complexity levels and interaction lengths because agent failures often depend on context in subtle ways. An agent might succeed on simple queries but fail on complex ones, work well with one tool set but fail with another, or degrade after extended interaction as context accumulates. Include simple, medium, complex, and very complex test cases to surface these patterns.

**Score Composite Quality Dimensions Separately**

Break agent quality into separate dimensions (factual accuracy, completeness, coherence, tool efficiency, process quality) and score each independently because an agent might score high on accuracy but low on efficiency, or vice versa. Then compute weighted aggregates tuned to use-case priorities. This approach reveals which dimensions need improvement rather than averaging away the signal.

### Evaluation Rubric Design

**Build Multi-Dimensional Rubrics**

Define rubrics covering key dimensions with descriptive levels from excellent to failed. Include these core dimensions and adapt weights per use case:

- Factual accuracy: Claims match ground truth (weight heavily for knowledge tasks)
- Completeness: Output covers requested aspects (weight heavily for research tasks)
- Citation accuracy: Citations match claimed sources (weight for trust-sensitive contexts)
- Source quality: Uses appropriate primary sources (weight for authoritative outputs)
- Tool efficiency: Uses right tools a reasonable number of times (weight for cost-sensitive systems)

**Convert Rubrics to Numeric Scores**

Map dimension assessments to numeric scores (0.0 to 1.0), apply per-dimension weights, and calculate weighted overall scores. Set passing thresholds based on use-case requirements, typically 0.7 for general use and 0.9 for high-stakes applications. Store individual dimension scores alongside the aggregate because the breakdown drives targeted improvement.

### Evaluation Methodologies

**Use LLM-as-Judge for Scale**

Build LLM-based evaluation prompts that include: clear task description, the agent output under test, ground truth when available, an evaluation scale with explicit level descriptions, and a request for structured judgment with reasoning. LLM judges provide consistent, scalable evaluation across large test sets. Use a different model family than the agent being evaluated to avoid self-enhancement bias.

**Supplement with Human Evaluation**

Route edge cases, unusual queries, and a random sample of production traffic to human reviewers because humans notice hallucinated answers, system failures, and subtle biases that automated evaluation misses. Track patterns across human reviews to identify systematic issues and feed findings back into automated evaluation criteria.

**Apply End-State Evaluation for Stateful Agents**

For agents that mutate persistent state (files, databases, configurations), evaluate whether the final state matches expectations rather than how the agent got there. Define expected end-state assertions and verify them programmatically after each test run.

### Test Set Design

**Select Representative Samples**

Start with small samples (20-30 cases) during early development when changes have dramatic impacts and low-hanging fruit is abundant. Scale to 50+ cases for reliable signal as the system matures. Sample from real usage patterns, add known edge cases, and ensure coverage across complexity levels.

**Stratify by Complexity**

Structure test sets across complexity levels to prevent easy examples from inflating scores:
- Simple: single tool call, factual lookup
- Medium: multiple tool calls, comparison logic
- Complex: many tool calls, significant ambiguity
- Very complex: extended interaction, deep reasoning, synthesis

Report scores per stratum alongside overall scores to reveal where the agent actually struggles.

### Context Engineering Evaluation

**Validate Context Strategies Systematically**

Run agents with different context strategies on the same test set and compare quality scores, token usage, and efficiency metrics. This isolates the effect of context engineering from other variables and prevents anecdote-driven decisions.

**Run Degradation Tests**

Test how context degradation affects performance by running agents at different context sizes. Identify performance cliffs where context becomes problematic and establish safe operating limits. Feed these limits back into context management strategies.

### Continuous Evaluation

**Build Automated Evaluation Pipelines**

Integrate evaluation into the development workflow so evaluations run automatically on agent changes. Track results over time, compare versions, and block deployments that regress on key metrics.

**Monitor Production Quality**

Sample production interactions and evaluate them continuously. Set alerts for quality drops below warning (0.85 pass rate) and critical (0.70 pass rate) thresholds. Maintain dashboards showing trend analysis over time windows to detect gradual degradation.

## Practical Guidance

### Building Evaluation Frameworks

Follow this sequence to build an evaluation framework, because skipping early steps leads to measurements that do not reflect real quality:

1. Define quality dimensions relevant to the use case before writing any evaluation code, because dimensions chosen later tend to reflect what is easy to measure rather than what matters.
2. Create rubrics with clear, descriptive level definitions so evaluators (human or LLM) produce consistent scores.
3. Build test sets from real usage patterns and edge cases, stratified by complexity, with at least 50 cases for reliable signal.
4. Implement automated evaluation pipelines that run on every significant change.
5. Establish baseline metrics before making changes so improvements can be measured against a known reference.
6. Run evaluations on all significant changes and compare against the baseline.
7. Track metrics over time for trend analysis because gradual degradation is harder to notice than sudden drops.
8. Supplement automated evaluation with human review on a regular cadence.

### Avoiding Evaluation Pitfalls

Guard against these common failures that undermine evaluation reliability:

- **Overfitting to specific paths**: Evaluate outcomes, not specific steps, because agents find novel valid paths.
- **Ignoring edge cases**: Include diverse test scenarios covering the full complexity spectrum.
- **Single-metric obsession**: Use multi-dimensional rubrics because a single score hides dimension-specific failures.
- **Neglecting context effects**: Test with realistic context sizes and histories rather than clean-room conditions.
- **Skipping human evaluation**: Automated evaluation misses subtle issues that humans catch reliably.

## Examples

**Example 1: Simple Evaluation**
```python
def evaluate_agent_response(response, expected):
    rubric = load_rubric()
    scores = {}
    for dimension, config in rubric.items():
        scores[dimension] = assess_dimension(response, expected, dimension)
    overall = weighted_average(scores, config["weights"])
    return {"passed": overall >= 0.7, "scores": scores}
```

**Example 2: Test Set Structure**

Test sets should span multiple complexity levels to ensure comprehensive evaluation:

```python
test_set = [
    {
        "name": "simple_lookup",
        "input": "What is the capital of France?",
        "expected": {"type": "fact", "answer": "Paris"},
        "complexity": "simple",
        "description": "Single tool call, factual lookup"
    },
    {
        "name": "medium_query",
        "input": "Compare the revenue of Apple and Microsoft last quarter",
        "complexity": "medium",
        "description": "Multiple tool calls, comparison logic"
    },
    {
        "name": "multi_step_reasoning",
        "input": "Analyze sales data from Q1-Q4 and create a summary report with trends",
        "complexity": "complex",
        "description": "Many tool calls, aggregation, analysis"
    },
    {
        "name": "research_synthesis",
        "input": "Research emerging AI technologies, evaluate their potential impact, and recommend adoption strategy",
        "complexity": "very_complex",
        "description": "Extended interaction, deep reasoning, synthesis"
    }
]
```

## Guidelines

1. Use multi-dimensional rubrics, not single metrics
2. Evaluate outcomes, not specific execution paths
3. Cover complexity levels from simple to complex
4. Test with realistic context sizes and histories
5. Run evaluations continuously, not just before release
6. Supplement LLM evaluation with human review
7. Track metrics over time for trend detection
8. Set clear pass/fail thresholds based on use case

## Gotchas

1. **Overfitting evals to specific code paths**: Tests pass but the agent fails on slight input variations. Write eval criteria against outcomes and semantics, not surface patterns, and rotate test inputs periodically.
2. **LLM-judge self-enhancement bias**: Models rate their own outputs higher than independent judges do. Use a different model family as the evaluation judge than the model being evaluated.
3. **Test set contamination**: Eval examples leak into training data or prompt templates, inflating scores. Keep eval sets versioned and separate from any data used in prompts or fine-tuning.
4. **Metric gaming**: Optimizing for the metric rather than actual quality produces agents that score well but disappoint users. Cross-validate automated metrics against human judgments regularly.
5. **Single-dimension scoring**: One aggregate number hides critical failures in specific dimensions. Always report per-dimension scores alongside the overall score, and fail the eval if any single dimension falls below its minimum threshold.
6. **Eval set too small**: Fewer than 50 examples produces unreliable signal with high variance between runs. Scale the eval set to at least 50 cases and report confidence intervals.
7. **Not stratifying by difficulty**: Easy examples inflate overall scores, masking failures on hard cases. Report scores per complexity stratum and weight the overall score to prevent easy-case dominance.
8. **Treating eval as one-time**: Evaluation must be continuous, not a launch gate. Agent quality drifts as models update, tools change, and usage patterns evolve. Run evals on every change and on a regular production cadence.

## Integration

This skill connects to all other skills as a cross-cutting concern:

- context-fundamentals - Evaluating context usage
- context-degradation - Detecting degradation
- context-optimization - Measuring optimization effectiveness
- multi-agent-patterns - Evaluating coordination
- tool-design - Evaluating tool effectiveness
- memory-systems - Evaluating memory quality

## References

Internal reference:
- [Metrics Reference](./references/metrics.md) - Read when: designing specific evaluation metrics, choosing scoring scales, or implementing weighted rubric calculations

Internal skills:
- All other skills connect to evaluation for quality measurement

External resources:
- LLM evaluation benchmarks - Read when: selecting or building benchmark suites for agent comparison
- Agent evaluation research papers - Read when: adopting new evaluation methodologies or validating current approach
- Production monitoring practices - Read when: setting up alerting, dashboards, or sampling strategies for live systems

---

## Skill Metadata

**Created**: 2025-12-20
**Last Updated**: 2026-03-17
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 1.1.0
