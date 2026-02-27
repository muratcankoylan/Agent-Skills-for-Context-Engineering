---
name: reasoning-trace-optimizer
description: "Debug and optimize AI agents by analyzing reasoning traces. Activates on 'debug agent', 'optimize prompt', 'analyze reasoning', 'why did the agent fail', 'improve agent performance', or when diagnosing agent failures and context degradation."
---

# Reasoning Trace Optimizer

Debug and optimize AI agents by analyzing their reasoning traces. This skill uses MiniMax M2.1's interleaved thinking to provide deep insight into agent decision-making and generate concrete improvements.

## When to Activate

- User asks to "debug agent", "analyze reasoning", or "optimize prompt"
- Agent task fails and user wants to understand why
- User mentions "context degradation", "tool confusion", or "instruction drift"
- Request to improve agent performance or reduce errors
- User wants to generate shareable learnings from debugging sessions
- After repeated failures on similar tasks

## Core Concepts

### Interleaved Thinking

Unlike standard reasoning models that think once at the start, interleaved thinking allows reasoning BETWEEN each tool interaction. This is critical because:

1. **Long-horizon tasks** require maintaining focus across many turns
2. **External perturbations** (tool outputs, environment changes) need real-time adaptation
3. **Debugging** requires seeing HOW decisions were made, not just WHAT was output

### The Optimization Loop

```
Execute Agent → Capture Traces → Analyze Patterns → Optimize Prompt → Re-run
                                                          ↑____________|
```

Each iteration improves the prompt based on detected patterns until convergence.

### Pattern Detection

Common failure patterns the analyzer detects:

| Pattern | Description |
|---------|-------------|
| `context_degradation` | Model loses track of information over long contexts |
| `tool_confusion` | Model misunderstands tool capabilities or outputs |
| `instruction_drift` | Model gradually deviates from original instructions |
| `goal_abandonment` | Model stops pursuing the original goal |
| `circular_reasoning` | Model repeats similar actions without progress |
| `premature_conclusion` | Model concludes before completing the task |

## Usage Modes

### Mode 1: M2.1 Agent Debugging

Run a task through M2.1 and analyze its reasoning:

```python
from reasoning_trace_optimizer import TraceCapture, TraceAnalyzer

capture = TraceCapture()
trace = capture.run(
    task="Search for Python tutorials and summarize them",
    system_prompt="You are a research assistant.",
    tools=[search_tool],
    tool_executor=execute_search
)

analyzer = TraceAnalyzer()
analysis = analyzer.analyze(trace)

print(f"Score: {analysis.overall_score}/100")
for pattern in analysis.patterns:
    print(f"Found: {pattern.type.value} - {pattern.suggestion}")
```

### Mode 2: Full Optimization Loop

Automatically iterate until the prompt is optimized:

```python
from reasoning_trace_optimizer import OptimizationLoop, LoopConfig

config = LoopConfig(
    max_iterations=5,
    min_score_threshold=80.0,
)

loop = OptimizationLoop(config=config)
result = loop.run(
    task="Analyze this codebase and suggest improvements",
    initial_prompt="You are a code reviewer.",
    tools=[read_file_tool, search_tool],
    tool_executor=execute_tool
)

print(f"Improved: {result.initial_score} → {result.final_score}")
print(f"Final prompt:\n{result.final_prompt}")
```

### Mode 3: Universal Session Analysis

Analyze any agent's previous thinking (works with Claude, GPT, etc.):

When this skill is activated in Claude Code, it can analyze the current session's thinking blocks to identify issues and suggest improvements.

```
/reasoning-trace-optimizer analyze-session
```

### Mode 4: Generate Shareable Skills

Convert optimization learnings into reusable Agent Skills:

```python
from reasoning_trace_optimizer import SkillGenerator

generator = SkillGenerator()
skill_path = generator.generate(
    result=loop_result,
    skill_name="web-search-best-practices",
    output_dir="./skills"
)
```

## CLI Commands

```bash
# Capture reasoning trace
rto capture "Search for Python tutorials" -s "You are a helpful assistant."

# Analyze a task
rto analyze "Debug this code" -o analysis.txt

# Run optimization loop
rto optimize "Research AI papers" --max-iterations 5 --generate-skill

# Generate skill from artifacts
rto generate-skill my-skill-name --artifacts-dir ./optimization_artifacts
```

## Integration with Claude Code

### Auto-trigger on Failure

Add to your hooks to automatically analyze failures:

```json
{
  "hooks": {
    "post_tool_error": {
      "command": "rto analyze-session --last-error"
    }
  }
}
```

### On-demand Analysis

Use the slash command to analyze current session:

```
/reasoning-trace-optimizer
```

This will:
1. Extract thinking blocks from the current session
2. Identify patterns and issues
3. Suggest prompt improvements
4. Optionally update the system prompt

## Guidelines

1. **Preserve full context**: M2.1 requires full response history including thinking blocks for optimal performance
2. **Use appropriate tools**: Define tools clearly with unambiguous descriptions
3. **Set realistic convergence thresholds**: 5-10% improvement per iteration is typical
4. **Review generated skills**: Auto-generated skills should be reviewed before sharing
5. **Monitor token usage**: Each optimization iteration uses significant tokens

## Examples

### Before Optimization

```
System: You are a helpful assistant.

Issue: Agent called wrong tools, lost track of goal after 3 turns
Score: 45/100
Patterns: tool_confusion, goal_abandonment
```

### After Optimization

```
System: You are a research assistant focused on finding accurate information.

IMPORTANT GUIDELINES:
- Always verify search results before summarizing
- If a tool returns an error, try an alternative approach
- Keep track of your original goal throughout the task
- Validate findings against multiple sources when possible

Issue: None
Score: 85/100
Patterns: None detected
```

## References

- MiniMax M2.1 Documentation: https://platform.minimax.io/docs
- Interleaved Thinking Guide: See `docs/interleavedthinking.md`
- Agent Generalization: See `docs/agentthinking.md`

---

## Skill Metadata

**Created**: 2025-01-11
**Author**: Muratcan Koylan
**Version**: 0.1.0
**Powered by**: MiniMax M2.1
**Partnership**: Built in collaboration with MiniMax AI
