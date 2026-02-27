# Reasoning Trace Optimizer

<p align="center">
  <strong>Debug and optimize AI agents by analyzing reasoning traces with MiniMax M2.1's interleaved thinking</strong>
</p>

<p align="center">
  <a href="#key-features">Features</a> |
  <a href="#quick-start">Quick Start</a> |
  <a href="#how-it-works">How It Works</a> |
  <a href="#examples">Examples</a> |
  <a href="#api-reference">API Reference</a>
</p>

---

## The Problem

Traditional AI agents fail in opaque ways. You see the final output, but not **why** decisions were made. When an agent:
- Calls the wrong tool
- Loses track of the goal
- Makes up information

...you're left guessing where things went wrong.

## The Solution

**Reasoning Trace Optimizer** uses MiniMax M2.1's unique **interleaved thinking** capability to expose the agent's reasoning process between every tool call. This enables:

1. **Deep Debugging** - See exactly where reasoning diverged from expected behavior
2. **Pattern Detection** - Automatically identify failure modes (context degradation, tool confusion, etc.)
3. **Automated Optimization** - Generate improved prompts based on detected issues
4. **Shareable Skills** - Convert learnings into reusable Agent Skills for team sharing

## Why MiniMax M2.1?

M2.1's **interleaved thinking** is fundamentally different from traditional reasoning models:

```
Traditional:  Think → Act → Act → Act → Done
              ↑
              (reasoning only at start)

M2.1:         Think → Act → Think → Act → Think → Act → Done
              ↑            ↑              ↑
              (continuous reasoning between each tool call)
```

This matters for agents because:
- **Long tasks** require maintaining focus across many turns
- **Tool outputs** introduce unexpected information requiring adaptation
- **Debugging** needs visibility into decision-making, not just outputs

The `thinking` block (Anthropic SDK) or `reasoning_details` field (OpenAI SDK) exposes this reasoning for analysis.

---

## Key Features

| Component | Description |
|-----------|-------------|
| **TraceCapture** | Wrap M2.1 API to capture all thinking blocks with full context |
| **TraceAnalyzer** | Detect patterns like context degradation, tool confusion, instruction drift |
| **PromptOptimizer** | Generate improved prompts based on analysis using M2.1 |
| **OptimizationLoop** | Automated capture → analyze → improve → re-run cycle |
| **SkillGenerator** | Convert learnings into shareable Agent Skills |

### Pattern Detection

The analyzer automatically identifies these failure patterns:

| Pattern | Description | Severity |
|---------|-------------|----------|
| `context_degradation` | Model loses information over long contexts | High |
| `tool_confusion` | Model misunderstands tool capabilities | High |
| `instruction_drift` | Model deviates from original instructions | Medium |
| `hallucination` | Model generates unsupported information | Critical |
| `goal_abandonment` | Model stops pursuing the original goal | High |
| `circular_reasoning` | Model repeats similar actions without progress | Medium |
| `premature_conclusion` | Model concludes before completing task | Medium |
| `missing_validation` | Model doesn't verify results | High |

Each detected pattern includes:
- **Evidence** - Specific excerpts from thinking blocks
- **Severity** - Critical/High/Medium/Low
- **Suggestion** - Concrete improvement for the prompt
- **Confidence** - How certain the detection is

---

## Quick Start

### Installation

```bash
cd examples/interleaved-thinking
pip install -e .
```

### Configuration

Set your MiniMax API key:

```bash
export ANTHROPIC_API_KEY=your_minimax_api_key
export ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
```

Or create a `.env` file:

```env
ANTHROPIC_API_KEY=your_minimax_api_key
ANTHROPIC_BASE_URL=https://api.minimax.io/anthropic
```

### Basic Usage

```python
from reasoning_trace_optimizer import TraceCapture, TraceAnalyzer

# Capture reasoning trace
capture = TraceCapture()
trace = capture.run(
    task="Explain quantum computing",
    system_prompt="You are a science educator."
)

print(f"Captured {len(trace.thinking_blocks)} thinking blocks")

# Analyze the reasoning
analyzer = TraceAnalyzer()
analysis = analyzer.analyze(trace)

print(f"Overall Score: {analysis.overall_score}/100")
for pattern in analysis.patterns:
    print(f"  [{pattern.severity.value}] {pattern.type.value}")
    print(f"    Suggestion: {pattern.suggestion}")
```

---

## How It Works

### The Optimization Loop

```
┌─────────────────────────────────────────────────────────────────────────┐
│                       OPTIMIZATION LOOP                                 │
│                                                                         │
│   ┌──────────┐    ┌──────────┐    ┌──────────┐    ┌──────────┐          │
│   │  Agent   │───▶│ Capture  │───▶│ Analyze  │───▶│ Optimize │          │
│   │ Execute  │    │ Traces   │    │ Patterns │    │  Prompt  │          │
│   └──────────┘    └──────────┘    └──────────┘    └──────────┘          │
│        ▲                                               │                │
│        └───────────────────────────────────────────────┘                │
│                       (loop until converged or max iterations)          │
│                                                                         │
│   Convergence: Score improvement < threshold OR score > target          │
└─────────────────────────────────────────────────────────────────────────┘
```

### What Gets Captured

For each agent execution, we capture:

1. **Thinking Blocks** - M2.1's reasoning before each action
2. **Tool Calls** - What tools were called with what inputs
3. **Tool Results** - What each tool returned
4. **Final Response** - The agent's output
5. **Metadata** - Tokens used, turns taken, success/failure

### What Gets Analyzed

The analyzer examines thinking blocks to understand:

- **Current Understanding** - What does the agent believe about the task?
- **Tool Interpretation** - How did it interpret each tool result?
- **Alternatives Considered** - What options did it evaluate?
- **Goal Awareness** - Is it still pursuing the original objective?

---

## Examples

### Example 1: Basic Trace Capture

```python
# examples/01_basic_capture.py
from reasoning_trace_optimizer import TraceCapture

capture = TraceCapture()
trace = capture.run(
    task="Explain what interleaved thinking is and why it matters for AI agents.",
    system_prompt="You are an AI researcher explaining concepts clearly."
)

# Output:
# Captured 1 thinking block
# Turn 0: "The user is asking me to explain 'interleaved thinking'..."
```

### Example 2: Tool Usage with Analysis

```python
# examples/02_tool_usage.py
from reasoning_trace_optimizer import TraceCapture, TraceAnalyzer

# Define tools
tools = [
    {
        "name": "get_weather",
        "description": "Get current weather for a city",
        "input_schema": {...}
    }
]

capture = TraceCapture()
trace = capture.run(
    task="Compare the weather in San Francisco and New York",
    tools=tools,
    tool_executor=execute_tool
)

# Analyze
analyzer = TraceAnalyzer()
analysis = analyzer.analyze(trace)

# Output:
# Score: 85/100
# Thinking Blocks: 3
# Tool Calls: 4 (get_weather x2, get_forecast x2)
# Patterns: None detected
```

### Example 3: Full Optimization Loop

This example demonstrates a complex research task with 7 tools (web search, file operations, note-taking):

```python
# examples/03_full_optimization.py
from reasoning_trace_optimizer import OptimizationLoop, LoopConfig, SkillGenerator

config = LoopConfig(
    max_iterations=3,
    min_score_threshold=85.0,
    convergence_threshold=5.0,
    save_artifacts=True,
)

loop = OptimizationLoop(config=config)
result = loop.run(
    task="""Research "context engineering for AI agents" and create a summary...""",
    initial_prompt="You are a research assistant.",
    tools=TOOLS,
    tool_executor=execute_tool,
)

# Generate shareable skill
generator = SkillGenerator()
skill_path = generator.generate(result, skill_name="research-agent")
```

**Actual Output from Example 3:**

```
======================================================================
OPTIMIZATION RESULTS
======================================================================

Total Iterations: 3
Converged: Yes

ITERATION 1 (Score: 69/100)
├── Task Completed: Yes
├── Thinking Blocks: 6
├── Tool Calls: 16
├── Patterns Found: 2
│   ├── [LOW] missing_validation
│   └── [LOW] incomplete_reasoning
├── Strengths: Excellent goal adherence, thorough source diversity
└── Warning: Prompt grew too large (2979 chars), limiting growth

ITERATION 2 (Score: 60/100)  ← Regression detected!
├── Task Completed: Yes
├── Thinking Blocks: 8
├── Tool Calls: 16
├── Patterns Found: 3
│   ├── [MEDIUM] incomplete_reasoning
│   ├── [MEDIUM] missing_validation
│   └── [LOW] tool_misuse

ITERATION 3 (Score: 66/100)
├── Task Completed: Yes
├── Thinking Blocks: 8
├── Tool Calls: 16
└── Patterns Found: 3

→ Using best prompt from iteration 1 (score: 67.6)

TOOL USAGE ACROSS ALL ITERATIONS:
├── read_url: 20 calls
├── web_search: 12 calls
├── list_directory: 7 calls
├── save_note: 6 calls
└── write_file: 3 calls

NOTES SAVED: 6 research notes with tagged findings
FILES WRITTEN: ./output/research_summary.md (11,357 chars)

GENERATED SKILL: ./generated_skills/comprehensive-research-agent/SKILL.md
```

**Key Features Demonstrated:**

1. **Prompt Growth Limiting** - Prevents prompt bloat by limiting expansion to 3x original size
2. **Best Score Tracking** - Automatically uses the best-performing prompt, even if later iterations regress
3. **Regression Detection** - Warns when scores drop and can stop after consecutive regressions

---

## Generated Artifacts

### Optimization Artifacts

Each optimization run creates artifacts for inspection:

```
optimization_artifacts/
├── summary.json              # Overall results
├── final_prompt.txt          # The optimized prompt
├── iteration_1/
│   ├── trace.json            # Full reasoning trace
│   ├── analysis.json         # Pattern detection results
│   └── optimization.json     # Prompt changes made
├── iteration_2/
│   └── ...
└── iteration_3/
    └── ...
```

### Generated Skills

The SkillGenerator converts optimization learnings into shareable Agent Skills:

```
generated_skills/
└── comprehensive-research-agent/
    ├── SKILL.md              # The shareable skill
    └── references/
        ├── optimization_summary.json
        ├── optimized_prompt.txt
        └── patterns_found.json
```

**Example Generated Skill Content:**

```markdown
## Patterns to Avoid

- **Missing Validation**: Accepting tool responses at face value without
  verifying the actual state change occurred.
- **Hallucinating Sources**: Citing sources that failed to load.
- **Ignoring Contradictions**: Proceeding when tool results conflict.

## Recommended Practices

- After every tool call, state the outcome explicitly
- Track sources separately: 'attempted' vs 'successful'
- Implement error recovery with alternative approaches
- Cross-reference key claims against multiple sources
```

---

## API Reference

### TraceCapture

```python
capture = TraceCapture(
    api_key="...",                              # MiniMax API key
    base_url="https://api.minimax.io/anthropic", # API endpoint
    model="MiniMax-M2.1"                        # Model to use
)

trace = capture.run(
    task="...",                    # The task to execute
    system_prompt="...",           # System prompt
    tools=[...],                   # Tool definitions (Anthropic format)
    tool_executor=fn,              # Function to execute tools
    max_turns=10,                  # Maximum conversation turns
    max_tokens=4096                # Max tokens per response
)
```

### TraceAnalyzer

```python
analyzer = TraceAnalyzer(
    api_key="...",
    base_url="https://api.minimax.io/anthropic",
    model="MiniMax-M2.1"
)

analysis = analyzer.analyze(trace)
# Returns: AnalysisResult with patterns, scores, recommendations

quick_score = analyzer.quick_score(trace)
# Returns: float (0-100) for fast feedback
```

### OptimizationLoop

```python
config = LoopConfig(
    # Iteration control
    max_iterations=5,           # Maximum optimization iterations
    convergence_threshold=3.0,  # Stop if improvement < this %
    min_score_threshold=75.0,   # Stop if score exceeds this
    regression_threshold=8.0,   # Warn if score drops by this much

    # Optimization behavior
    use_best_prompt=True,       # Use best-performing prompt, not final
    max_prompt_growth=5.0,      # Limit prompt expansion to 5x original

    # Output options
    save_artifacts=True,        # Save traces and analyses
    artifacts_dir="./artifacts" # Where to save
)

loop = OptimizationLoop(config=config)
result = loop.run(task, initial_prompt, tools, tool_executor)
# Returns: LoopResult with iterations, final_prompt, scores
```

**Optimization Safeguards:**

- **Best Prompt Tracking**: Keeps the prompt that produced the highest score
- **Prompt Growth Limiting**: Prevents prompt bloat by limiting size expansion
- **Regression Detection**: Warns on score drops, stops after consecutive regressions

**Score Expectations:**

| Task Complexity | Typical Score Range | Notes |
|-----------------|---------------------|-------|
| Simple (1-2 tools) | 80-95 | Straightforward tasks converge quickly |
| Medium (3-5 tools) | 70-85 | Multiple tool coordination adds variability |
| Complex (6+ tools, multi-step) | 60-75 | Inherent variance in long reasoning chains |

Complex research tasks with many tools and steps typically plateau around **65-75** due to:
- Tool output variability affecting reasoning paths
- Multiple valid approaches leading to different scoring
- The stochastic nature of multi-step agent execution

The optimizer focuses on **relative improvement** and **pattern elimination** rather than achieving a specific absolute score.

### SkillGenerator

```python
generator = SkillGenerator()
skill_path = generator.generate(
    result=loop_result,           # From OptimizationLoop
    skill_name="my-skill",        # Lowercase with hyphens
    output_dir="./generated_skills",
    title="Human Readable Title"
)
```

---

## CLI Usage

```bash
# Capture a reasoning trace
rto capture "Explain interleaved thinking" -s "You are an AI researcher."

# Analyze a task and output results
rto analyze "Debug this code snippet" -o analysis.txt

# Run full optimization loop
rto optimize "Research AI papers" --max-iterations 5 --generate-skill

# Generate skill from previous optimization
rto generate-skill my-skill-name --artifacts-dir ./optimization_artifacts
```

---

## Real-World Sources Used

Example 3 uses real documentation URLs for realistic simulation:

| Source | URL |
|--------|-----|
| Anthropic Docs | `docs.anthropic.com/en/docs/build-with-claude/*` |
| Anthropic Research | `anthropic.com/research/building-effective-agents` |
| OpenAI Docs | `platform.openai.com/docs/guides/*` |
| MiniMax M2.1 | `minimax.io/platform/docs/M2.1` |
| DAIR.AI | `promptingguide.ai/techniques` |
| LangChain | `python.langchain.com/docs/how_to/debugging` |
| arXiv Papers | `arxiv.org/abs/2307.03172` (Lost in the Middle) |

---

## Robustness Features

The optimizer includes several safeguards to handle real-world variability:

### Parsing Resilience

LLM responses don't always produce valid JSON. The system handles this gracefully:

| Component | Fallback Behavior |
|-----------|-------------------|
| **Analyzer** | Extracts scores via regex patterns when JSON fails; defaults to 50/100 (not 0) |
| **Optimizer** | Multi-strategy prompt extraction: JSON → regex → marker detection → code blocks |
| **Loop** | Warns when final prompt is unchanged; tracks best-performing iteration |

### Extended Test Results (10 iterations)

Real-world testing revealed important insights:

```
Iteration  Score   Patterns  Tool Calls  Notes
────────────────────────────────────────────────
1          69/100    4         22        Baseline
2          66/100    3         14        -
3          61/100    3         17        -
4          72/100    3         20        ← Best score
5          59/100    4         16        -
6          50/100*   0         15        *Parser fallback activated
7          70/100    3         12        Recovery
8          64/100    3         14        -
9          64/100    3         18        -
10         70/100    3         19        Final

* Iteration 6: JSON parsing failed, fallback returned neutral score
```

**Key Learnings:**
- Scores fluctuate ±15 points between iterations due to stochastic model behavior
- Best score (72) was achieved mid-run, not at the end
- `use_best_prompt=True` correctly selected iteration 4's prompt
- Parsing failures now handled gracefully instead of returning 0 scores

---

## Architecture

```
reasoning_trace_optimizer/
├── __init__.py          # Public API exports
├── models.py            # Data models (Pydantic)
│   ├── ThinkingBlock    # Single reasoning segment
│   ├── ToolCall         # Tool invocation record
│   ├── ReasoningTrace   # Complete execution trace
│   ├── Pattern          # Detected failure pattern
│   ├── AnalysisResult   # Full analysis output
│   └── LoopResult       # Optimization loop result
├── capture.py           # TraceCapture - M2.1 API wrapper
├── analyzer.py          # TraceAnalyzer - Pattern detection (with fallback parsing)
├── optimizer.py         # PromptOptimizer - Prompt improvement (with fallback extraction)
├── loop.py              # OptimizationLoop - Full cycle (with best-score tracking)
├── skill_generator.py   # SkillGenerator - Create skills
└── cli.py               # Command-line interface
```

---

## Integration

### Claude Code Skill

This project includes a Claude Code skill (`SKILL.md`) enabling:

- **Auto-trigger on failure** - Analyze when agent tasks fail
- **On-demand analysis** - Use `/reasoning-trace-optimizer` command
- **Session analysis** - Analyze thinking from current conversation

### Python Library

```python
from reasoning_trace_optimizer import (
    TraceCapture,
    TraceAnalyzer,
    PromptOptimizer,
    OptimizationLoop,
    LoopConfig,
    SkillGenerator,
)
```

---

## Contributing

This project is part of the [Agent Skills for Context Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) collection.

---

## License

MIT License

---

## References

- [MiniMax M2.1 Documentation](https://www.minimax.io/platform/docs)
- [MiniMax API Reference](https://www.minimax.io/platform/docs/M2.1)
- [Interleaved Thinking Guide](./docs/interleavedthinking.md)
- [Agent Generalization Research](./docs/agentthinking.md)
- [Anthropic API Compatibility](./docs/m2-1.md)

---

<p align="center">
  <strong>Built in partnership with MiniMax AI</strong><br>
  Showcasing the power of interleaved thinking for agent debugging
</p>
