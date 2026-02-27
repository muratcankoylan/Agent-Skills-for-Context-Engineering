"""
Example 3: Full Optimization Loop with Comprehensive Tools

Demonstrates the complete optimization cycle with realistic tools:
- Web search for finding information
- URL reading for fetching content
- File system operations (read, write, list)
- Note-taking for tracking findings

This example uses REAL URLs and realistic content to demonstrate
how the Reasoning Trace Optimizer works in production scenarios.
"""

import json
import os
import random
from datetime import datetime
from pathlib import Path

from dotenv import load_dotenv

from reasoning_trace_optimizer import (
    OptimizationLoop,
    LoopConfig,
    SkillGenerator,
)

# Load environment variables from the project root
env_path = Path(__file__).parent.parent / ".env"
load_dotenv(env_path)


# =============================================================================
# COMPREHENSIVE TOOL DEFINITIONS
# =============================================================================

TOOLS = [
    # Web Search Tool
    {
        "name": "web_search",
        "description": "Search the web for information. Returns a list of results with titles, URLs, and snippets. Use specific queries for better results.",
        "input_schema": {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query - be specific and use relevant keywords",
                },
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (1-10, default 5)",
                    "default": 5,
                },
            },
            "required": ["query"],
        },
    },
    # Read URL Tool
    {
        "name": "read_url",
        "description": "Fetch and read the content of a webpage. Returns the main text content. Use after web_search to get full details from a result.",
        "input_schema": {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The URL to fetch content from",
                },
            },
            "required": ["url"],
        },
    },
    # File Read Tool
    {
        "name": "read_file",
        "description": "Read the contents of a local file. Supports text files, markdown, JSON, etc.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path to the file to read",
                },
            },
            "required": ["path"],
        },
    },
    # File Write Tool
    {
        "name": "write_file",
        "description": "Write content to a local file. Creates the file if it doesn't exist, overwrites if it does.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Path where to write the file",
                },
                "content": {
                    "type": "string",
                    "description": "Content to write to the file",
                },
            },
            "required": ["path", "content"],
        },
    },
    # List Directory Tool
    {
        "name": "list_directory",
        "description": "List files and folders in a directory. Useful for exploring project structure.",
        "input_schema": {
            "type": "object",
            "properties": {
                "path": {
                    "type": "string",
                    "description": "Directory path to list (default: current directory)",
                    "default": ".",
                },
            },
            "required": [],
        },
    },
    # Save Note Tool
    {
        "name": "save_note",
        "description": "Save a research note with title and content. Use to track important findings during research.",
        "input_schema": {
            "type": "object",
            "properties": {
                "title": {
                    "type": "string",
                    "description": "Title of the note",
                },
                "content": {
                    "type": "string",
                    "description": "Content of the note",
                },
                "tags": {
                    "type": "array",
                    "items": {"type": "string"},
                    "description": "Optional tags for categorization",
                },
            },
            "required": ["title", "content"],
        },
    },
    # Calculator Tool
    {
        "name": "calculator",
        "description": "Perform mathematical calculations. Supports basic arithmetic and common functions.",
        "input_schema": {
            "type": "object",
            "properties": {
                "expression": {
                    "type": "string",
                    "description": "Mathematical expression to evaluate (e.g., '2 + 2', 'sqrt(16)', '100 * 0.15')",
                },
            },
            "required": ["expression"],
        },
    },
]


# =============================================================================
# REAL-WORLD SIMULATED DATA
# Based on actual documentation and research from AI companies
# =============================================================================

# Simulated web search results with REAL URLs
SEARCH_DATABASE = {
    "context engineering ai": [
        {
            "title": "Context Engineering for AI Agents - Anthropic",
            "url": "https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching",
            "snippet": "Prompt caching is a feature that optimizes API usage by allowing resuming from specific prefixes in your prompts. Cache the context you want to reuse across requests.",
        },
        {
            "title": "Building Effective AI Agents - Anthropic Research",
            "url": "https://www.anthropic.com/research/building-effective-agents",
            "snippet": "A comprehensive guide to building effective AI agents. Covers tool use, context management, error handling, and best practices for production deployments.",
        },
        {
            "title": "Large Language Models and Context Windows - OpenAI",
            "url": "https://platform.openai.com/docs/guides/text-generation",
            "snippet": "Understanding how context windows work in large language models. Learn about token limits, context management strategies, and optimizing for performance.",
        },
    ],
    "interleaved thinking agents": [
        {
            "title": "MiniMax M2.1 - Interleaved Thinking Model",
            "url": "https://www.minimax.io/platform/docs/M2.1",
            "snippet": "M2.1 introduces interleaved thinking - the ability for models to reason between tool calls, enabling better debugging and adaptability in agentic workflows.",
        },
        {
            "title": "Chain of Thought Prompting - Google Research",
            "url": "https://arxiv.org/abs/2201.11903",
            "snippet": "Chain-of-thought prompting enables complex reasoning in large language models. This paper explores how step-by-step reasoning improves model performance.",
        },
    ],
    "prompt optimization techniques": [
        {
            "title": "Prompt Engineering Guide - DAIR.AI",
            "url": "https://www.promptingguide.ai/techniques",
            "snippet": "Comprehensive guide to prompt engineering techniques including zero-shot, few-shot, chain-of-thought, and advanced methods for optimizing LLM outputs.",
        },
        {
            "title": "Best Practices for Prompt Engineering - OpenAI",
            "url": "https://platform.openai.com/docs/guides/prompt-engineering",
            "snippet": "Official OpenAI guide on prompt engineering best practices. Covers strategies for getting better results, handling edge cases, and iterative refinement.",
        },
    ],
    "agent debugging best practices": [
        {
            "title": "Debugging AI Agents - LangChain Documentation",
            "url": "https://python.langchain.com/docs/how_to/debugging",
            "snippet": "Learn how to debug LangChain agents effectively. Covers tracing, verbose mode, callbacks, and common debugging patterns for complex agent workflows.",
        },
        {
            "title": "LLM Observability and Tracing - Weights & Biases",
            "url": "https://docs.wandb.ai/guides/prompts",
            "snippet": "Track and debug LLM applications with W&B Prompts. Visualize chains, compare outputs, and identify failure patterns in your AI applications.",
        },
    ],
    "context window optimization": [
        {
            "title": "Claude's Context Window - Anthropic Documentation",
            "url": "https://docs.anthropic.com/en/docs/build-with-claude/context-windows",
            "snippet": "Claude supports context windows up to 200K tokens. Learn how to effectively use large context windows and optimize token usage for cost and performance.",
        },
        {
            "title": "Lost in the Middle: How Language Models Use Long Contexts",
            "url": "https://arxiv.org/abs/2307.03172",
            "snippet": "Research on how LLMs utilize information across long contexts. Models perform worse when relevant info is in the middle vs. beginning/end of context.",
        },
    ],
}

# Simulated webpage content based on REAL documentation
PAGE_CONTENT = {
    "https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching": """
# Prompt Caching - Anthropic Documentation

Prompt caching is a feature that optimizes API usage by allowing you to cache frequently used context.

## Overview

Prompt caching allows you to cache the system prompt, examples, and other static content that remains constant across multiple requests. This:

- **Reduces latency** by up to 85% for cached content
- **Lowers costs** by avoiding re-processing of identical context
- **Improves throughput** for high-volume applications

## How It Works

When you enable prompt caching, the API stores a hash of your prompt prefix. On subsequent requests with the same prefix, the cached computation is reused.

### Cache Breakpoints

You can specify cache breakpoints using the `cache_control` parameter:

```python
messages = [
    {
        "role": "user",
        "content": [
            {
                "type": "text",
                "text": "Your static context here...",
                "cache_control": {"type": "ephemeral"}
            }
        ]
    }
]
```

## Best Practices

1. **Cache stable content**: Put instructions and examples that don't change in the cached portion
2. **Place dynamic content last**: User queries and variable data should come after cached content
3. **Monitor cache hits**: Use the response headers to track cache efficiency
4. **Minimum cache size**: Content must be at least 1024 tokens to be cached

## Context Engineering Implications

Effective prompt caching is a key part of context engineering. By understanding what to cache:

- System prompts with role definitions
- Tool descriptions that remain constant
- Few-shot examples for consistent behavior
- Reference documentation the model needs

You reduce both latency and cost while maintaining quality.
""",
    "https://www.anthropic.com/research/building-effective-agents": """
# Building Effective AI Agents - Anthropic Research

This guide covers best practices for building reliable, effective AI agents using Claude.

## Core Principles

### 1. Start Simple, Add Complexity Gradually

Begin with the simplest possible agent architecture:
- Single tool with clear purpose
- Linear workflow without branching
- Explicit success criteria

Only add complexity when you have evidence it's needed.

### 2. Tool Design Matters

Well-designed tools make agents more reliable:

- **Clear descriptions**: Explain what the tool does AND when to use it
- **Typed inputs**: Use JSON Schema to define expected parameters
- **Informative outputs**: Return data the model can interpret and act on
- **Error messages**: Provide actionable guidance when things fail

### 3. Context Management

Context is your most precious resource:

- **Token efficiency**: Every token costs money and attention
- **Structured format**: Use consistent formatting for easier parsing
- **Progressive disclosure**: Load information on-demand
- **Summarization**: Compress long histories while preserving key facts

### 4. Error Handling

Agents will encounter errors. Design for recovery:

- Give the model explicit permission to retry
- Provide diagnostic information in error messages
- Set clear stopping conditions to prevent infinite loops
- Log everything for debugging

## Common Anti-Patterns

1. **Over-engineering**: Building complex multi-agent systems before validating single-agent performance
2. **Vague tools**: Tool descriptions that don't clarify when to use each tool
3. **Context overload**: Stuffing too much information into the prompt
4. **No exit conditions**: Letting agents run indefinitely without progress checks

## Debugging Strategies

### Trace Analysis

The key to debugging agents is understanding their reasoning:

1. Capture the full reasoning trace including thinking blocks
2. Identify where the agent's understanding diverged from reality
3. Look for patterns: tool confusion, goal drift, context loss
4. Iterate on prompts based on specific failure modes

### Interleaved Thinking

Models with interleaved thinking (reasoning between tool calls) provide better debugging insight because you can see:

- How they interpreted each tool result
- What alternatives they considered
- When and why they changed approach
""",
    "https://platform.openai.com/docs/guides/text-generation": """
# Text Generation - OpenAI Documentation

Learn how to generate text with OpenAI's models.

## Context Windows

Each model has a context window that determines the maximum number of tokens it can process:

| Model | Context Window |
|-------|----------------|
| GPT-4o | 128K tokens |
| GPT-4 Turbo | 128K tokens |
| GPT-3.5 Turbo | 16K tokens |

### Managing Context

For long conversations or documents:

1. **Truncation**: Remove oldest messages when approaching the limit
2. **Summarization**: Replace old messages with summaries
3. **Retrieval**: Use RAG to fetch only relevant content

### Token Counting

Use the tiktoken library to count tokens before sending requests:

```python
import tiktoken

encoding = tiktoken.encoding_for_model("gpt-4")
num_tokens = len(encoding.encode("Your text here"))
```

## Best Practices

### Structured Prompts

Organize your prompts with clear sections:
- System message: Role and general instructions
- Context: Background information needed
- Task: Specific request with format requirements
- Examples: Few-shot demonstrations if helpful

### Temperature and Sampling

- **temperature=0**: Deterministic, best for factual tasks
- **temperature=0.7**: Balanced creativity and coherence
- **temperature=1.0+**: More random, for creative tasks
""",
    "https://www.minimax.io/platform/docs/M2.1": """
# MiniMax M2.1 - Interleaved Thinking Model

M2.1 is a next-generation reasoning model that introduces **interleaved thinking** - continuous reasoning throughout task execution.

## What is Interleaved Thinking?

Traditional reasoning models think once at the start, then execute:
```
Think → Act → Act → Act → Done
```

M2.1 thinks between every action:
```
Think → Act → Think → Act → Think → Act → Done
```

## Why This Matters

### 1. Better Debugging

The thinking blocks expose the model's reasoning process. You can see:
- What it understood from tool results
- How it decided what to do next
- Where it might have gone wrong

### 2. Adaptive Behavior

By reasoning after each tool call, M2.1 can:
- React to unexpected outputs
- Recover from errors mid-execution
- Adjust strategy based on new information

### 3. Long-Horizon Tasks

For complex multi-step tasks, maintaining focus is crucial. Interleaved thinking:
- Reinforces the original goal
- Tracks progress toward completion
- Identifies when the task is done

## API Usage

### Anthropic SDK

```python
import anthropic

client = anthropic.Anthropic(
    api_key="your-key",
    base_url="https://api.minimax.io/anthropic"
)

response = client.messages.create(
    model="MiniMax-M2.1",
    max_tokens=4096,
    messages=[{"role": "user", "content": "Your task"}]
)

# Access thinking blocks
for block in response.content:
    if block.type == "thinking":
        print(f"Thinking: {block.thinking}")
    elif block.type == "text":
        print(f"Response: {block.text}")
```

## Best Practices

1. **Preserve full context**: Always include thinking blocks in message history
2. **Clear tool descriptions**: Help the model understand when to use each tool
3. **Explicit success criteria**: Define what "done" looks like
4. **Error guidance**: Give clear instructions for handling failures
""",
    "https://www.promptingguide.ai/techniques": """
# Prompt Engineering Techniques - DAIR.AI

A comprehensive guide to prompt engineering techniques for large language models.

## Basic Techniques

### Zero-Shot Prompting

Ask the model to perform a task without examples:

```
Classify this text as positive, negative, or neutral:
"I really enjoyed the movie but the ending was disappointing."
```

### Few-Shot Prompting

Provide examples to guide the model:

```
Classify sentiment:
"Great product!" → Positive
"Terrible service." → Negative
"It was okay." → Neutral
"I really enjoyed the movie but the ending was disappointing." →
```

## Advanced Techniques

### Chain-of-Thought (CoT)

Encourage step-by-step reasoning:

```
Solve this problem step by step:
If John has 5 apples and gives 2 to Mary, then buys 3 more, how many does he have?

Let's think through this:
1. John starts with 5 apples
2. He gives 2 to Mary: 5 - 2 = 3 apples
3. He buys 3 more: 3 + 3 = 6 apples
Answer: 6 apples
```

### Self-Consistency

Generate multiple reasoning paths and take the majority answer. Improves reliability for complex reasoning tasks.

### Tree of Thoughts

Explore multiple reasoning branches simultaneously, evaluating and pruning paths to find optimal solutions.

## Prompt Optimization

### Iterative Refinement

1. Start with a basic prompt
2. Test on representative examples
3. Analyze failures
4. Refine prompt based on patterns
5. Repeat until convergence

### Common Failure Patterns

| Pattern | Solution |
|---------|----------|
| Goal drift | Add explicit goal reminders |
| Hallucination | Require source citations |
| Incomplete output | Specify format requirements |
| Wrong tool usage | Improve tool descriptions |
""",
    "https://platform.openai.com/docs/guides/prompt-engineering": """
# Prompt Engineering Best Practices - OpenAI

Official guide to getting better results from large language models.

## Six Strategies

### 1. Write Clear Instructions

Be specific about what you want:
- Include details in your query
- Ask the model to adopt a persona
- Use delimiters to mark distinct sections
- Specify desired output format and length

### 2. Provide Reference Text

Reduce hallucinations:
- Instruct the model to answer using provided text
- Ask for citations from the source material
- Use retrieval to inject relevant context

### 3. Split Complex Tasks

Break down hard problems:
- Use intent classification to route queries
- Summarize long documents in chunks
- Break multi-step tasks into sequential prompts

### 4. Give the Model Time to Think

Improve reasoning:
- Ask for a chain of reasoning
- Use inner monologue to hide intermediate steps
- Ask if previous steps were correct

### 5. Use External Tools

Augment model capabilities:
- Use code execution for accurate calculations
- Use retrieval for up-to-date information
- Use APIs for specific functionality

### 6. Test Changes Systematically

Evaluate prompt effectiveness:
- Define comprehensive test cases
- Measure against gold-standard answers
- Track metrics over prompt iterations

## Anti-Patterns to Avoid

1. **Ambiguous instructions**: "Make it better" vs "Improve clarity by adding examples"
2. **Too much context**: Relevant info gets lost in noise
3. **No output format**: Model guesses what you want
4. **Assuming knowledge**: Model doesn't know your codebase/domain
""",
    "https://python.langchain.com/docs/how_to/debugging": """
# Debugging LangChain Agents

Learn effective debugging strategies for LangChain applications.

## Verbose Mode

Enable detailed logging:

```python
from langchain.globals import set_verbose

set_verbose(True)
```

This prints:
- Each step in the chain
- Inputs and outputs at every stage
- Tool calls and their results

## LangSmith Tracing

For production debugging, use LangSmith:

```python
import os
os.environ["LANGCHAIN_TRACING_V2"] = "true"
os.environ["LANGCHAIN_API_KEY"] = "your-key"
```

LangSmith provides:
- Visual trace of every step
- Latency breakdown
- Token usage tracking
- Failure analysis

## Common Debugging Patterns

### 1. Tool Selection Issues

The agent picks the wrong tool. Debug by:
- Checking tool descriptions for clarity
- Reviewing the prompt format
- Testing with simplified tool sets

### 2. Infinite Loops

Agent repeats the same action. Fix by:
- Adding max_iterations limit
- Including progress checks in prompts
- Implementing early stopping conditions

### 3. Context Loss

Agent forgets earlier information. Address by:
- Checking context window limits
- Implementing conversation summarization
- Using retrieval for long-term memory

### 4. Hallucination

Agent makes up information. Reduce by:
- Requiring citations
- Validating outputs against sources
- Using temperature=0 for factual tasks

## Trace Analysis

The most powerful debugging technique is analyzing the full trace:

1. Capture all inputs, outputs, and reasoning
2. Find the exact step where things went wrong
3. Identify the pattern (tool confusion, goal drift, etc.)
4. Update prompts to address the specific failure
""",
    "https://arxiv.org/abs/2307.03172": """
# Lost in the Middle: How Language Models Use Long Contexts

Liu et al., 2023

## Abstract

While large language models support increasingly long context windows, we find they struggle to effectively use information in the middle of long contexts. This "lost in the middle" phenomenon has important implications for RAG systems and context engineering.

## Key Findings

### 1. U-Shaped Performance Curve

When relevant information is placed at different positions in a long context:
- **Beginning**: High performance (recency effect)
- **Middle**: Significantly degraded performance
- **End**: High performance (primacy effect)

### 2. Performance Degrades with Context Length

Even when information is at optimal positions, performance decreases as total context length increases.

### 3. Model Size Doesn't Fix It

Larger models show the same pattern. This is a fundamental limitation of current architectures.

## Implications for Practitioners

### Context Engineering Strategies

1. **Place critical information at the start or end**
   - Instructions at the beginning
   - Task-specific context at the end

2. **Keep context focused**
   - Only include truly relevant information
   - Remove redundant or low-signal content

3. **Structure for attention**
   - Use clear section headers
   - Separate distinct topics
   - Front-load important details in each section

### RAG System Design

1. **Limit retrieved chunks**
   - Quality over quantity
   - Rank by relevance, not just similarity

2. **Position retrieved content strategically**
   - Most relevant chunks at boundaries
   - Less relevant in middle if needed

3. **Consider summarization**
   - Condense multiple sources
   - Preserve key information density
""",
}

# Simulated file system with realistic project structure
FILE_SYSTEM = {
    "./project/README.md": """# AI Agent Research Project

This project explores context engineering and agent optimization techniques.

## Structure
- research/ - Research notes and findings
- output/ - Generated reports and summaries
- data/ - Source materials and datasets

## Current Focus
1. Understanding context engineering principles
2. Exploring interleaved thinking for debugging
3. Developing prompt optimization strategies

## Resources
- Anthropic Documentation: https://docs.anthropic.com
- OpenAI Guides: https://platform.openai.com/docs
- MiniMax M2.1: https://www.minimax.io
""",
    "./project/research/notes.md": """# Research Notes

## Context Engineering

### Definition
Context engineering is the discipline of managing what information enters the AI model's context window. It goes beyond prompt engineering to consider:
- System prompts and instructions
- Tool definitions and descriptions
- Retrieved documents (RAG)
- Conversation history
- Tool outputs and intermediate results

### Key Insight: "Lost in the Middle"
Research shows LLMs struggle with information in the middle of long contexts. Place important information at the start or end.

### Best Practices
1. Quality over quantity - only include high-signal tokens
2. Structure matters - use clear formatting and hierarchies
3. Progressive disclosure - load information on-demand
4. Attention anchoring - place critical info at boundaries

## Interleaved Thinking

### What It Is
The ability for models to reason between tool calls, not just at the start.

### Benefits
- Full visibility into agent reasoning
- Better debugging and error recovery
- Adaptive behavior based on tool results

### MiniMax M2.1
- Implements interleaved thinking
- Exposes reasoning via `thinking` blocks
- Compatible with Anthropic SDK

## Open Questions
- How to measure context efficiency?
- Optimal strategies for tool descriptions?
- Balancing context size vs. quality?
""",
    "./project/research/references.md": """# References

## Papers
1. "Lost in the Middle: How Language Models Use Long Contexts" - Liu et al., 2023
2. "Chain-of-Thought Prompting Elicits Reasoning" - Wei et al., 2022

## Documentation
- Anthropic: https://docs.anthropic.com/en/docs
- OpenAI: https://platform.openai.com/docs
- MiniMax: https://www.minimax.io/platform/docs

## Guides
- Prompt Engineering Guide: https://www.promptingguide.ai
- LangChain Debugging: https://python.langchain.com/docs/how_to/debugging
""",
}

# Runtime state
saved_notes = []
written_files = {}


# =============================================================================
# TOOL EXECUTOR
# =============================================================================

def execute_tool(name: str, input_data: dict) -> str:
    """Execute a tool and return realistic results."""
    global saved_notes, written_files

    if name == "web_search":
        query = input_data.get("query", "").lower()
        num_results = min(input_data.get("num_results", 5), 10)

        # Find matching results
        results = []
        for key, items in SEARCH_DATABASE.items():
            # Check if any query words match the key
            query_words = set(query.split())
            key_words = set(key.split())
            if query_words & key_words:  # Intersection
                results.extend(items)

        # Deduplicate and limit
        seen_urls = set()
        unique_results = []
        for r in results:
            if r["url"] not in seen_urls:
                seen_urls.add(r["url"])
                unique_results.append(r)

        if not unique_results:
            # Return generic "no results" response
            return json.dumps({
                "query": query,
                "num_results": 0,
                "results": [],
                "message": "No results found. Try different keywords.",
            })

        return json.dumps({
            "query": query,
            "num_results": len(unique_results[:num_results]),
            "results": unique_results[:num_results],
        })

    elif name == "read_url":
        url = input_data.get("url", "")
        content = PAGE_CONTENT.get(url)

        if content:
            return json.dumps({
                "url": url,
                "status": "success",
                "content": content,
                "length": len(content),
            })
        else:
            return json.dumps({
                "url": url,
                "status": "error",
                "error": "Page not found or unable to fetch content",
            })

    elif name == "read_file":
        path = input_data.get("path", "")

        # Check mock file system first
        if path in FILE_SYSTEM:
            return json.dumps({
                "path": path,
                "status": "success",
                "content": FILE_SYSTEM[path],
            })

        # Check written files
        if path in written_files:
            return json.dumps({
                "path": path,
                "status": "success",
                "content": written_files[path],
            })

        return json.dumps({
            "path": path,
            "status": "error",
            "error": f"File not found: {path}",
        })

    elif name == "write_file":
        path = input_data.get("path", "")
        content = input_data.get("content", "")

        written_files[path] = content
        return json.dumps({
            "path": path,
            "status": "success",
            "message": f"Successfully wrote {len(content)} characters to {path}",
        })

    elif name == "list_directory":
        path = input_data.get("path", ".")

        # Simulate directory listing based on mock file system
        if path == "." or path == "./project":
            return json.dumps({
                "path": path,
                "entries": [
                    {"name": "README.md", "type": "file"},
                    {"name": "research", "type": "directory"},
                    {"name": "output", "type": "directory"},
                    {"name": "data", "type": "directory"},
                ],
            })
        elif path == "./project/research" or path == "research":
            return json.dumps({
                "path": path,
                "entries": [
                    {"name": "notes.md", "type": "file"},
                    {"name": "references.md", "type": "file"},
                ],
            })
        else:
            return json.dumps({
                "path": path,
                "entries": [],
                "message": "Directory is empty or does not exist",
            })

    elif name == "save_note":
        note = {
            "id": len(saved_notes) + 1,
            "title": input_data.get("title", "Untitled"),
            "content": input_data.get("content", ""),
            "tags": input_data.get("tags", []),
            "timestamp": datetime.now().isoformat(),
        }
        saved_notes.append(note)
        return json.dumps({
            "status": "success",
            "note_id": note["id"],
            "message": f"Note '{note['title']}' saved successfully",
        })

    elif name == "calculator":
        expression = input_data.get("expression", "")
        try:
            # Safe evaluation of mathematical expressions
            import math
            allowed_names = {
                "sqrt": math.sqrt,
                "sin": math.sin,
                "cos": math.cos,
                "tan": math.tan,
                "log": math.log,
                "log10": math.log10,
                "exp": math.exp,
                "pow": pow,
                "abs": abs,
                "round": round,
                "pi": math.pi,
                "e": math.e,
            }
            result = eval(expression, {"__builtins__": {}}, allowed_names)
            return json.dumps({
                "expression": expression,
                "result": result,
                "status": "success",
            })
        except Exception as e:
            return json.dumps({
                "expression": expression,
                "status": "error",
                "error": str(e),
            })

    return json.dumps({"error": f"Unknown tool: {name}"})


# =============================================================================
# MAIN OPTIMIZATION LOOP
# =============================================================================

def main():
    """Run the full optimization loop with comprehensive tools."""
    global saved_notes, written_files

    # Reset state
    saved_notes = []
    written_files = {}

    # Configuration for optimization
    # Note: Complex research tasks typically plateau around 65-75 scores
    # due to inherent variability in multi-tool reasoning chains
    config = LoopConfig(
        max_iterations=5,  # Usually converges within 3-5 iterations
        convergence_threshold=3.0,  # Stop when improvements become marginal
        min_score_threshold=75.0,  # Realistic target for complex research tasks
        regression_threshold=8.0,  # Detect significant score drops
        use_best_prompt=True,  # Always use the best-performing prompt
        max_prompt_growth=5.0,  # Prevent excessive prompt bloat
        save_artifacts=True,
        artifacts_dir="./optimization_artifacts",
        verbose=True,
    )

    # Initialize the optimization loop
    loop = OptimizationLoop(
        config=config,
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url="https://api.minimax.io/anthropic",
        model="MiniMax-M2.1",
    )

    # Complex research task requiring multiple tools
    task = """Research the topic of "context engineering for AI agents" and create a comprehensive summary.

Your research should:
1. Search for information about context engineering concepts and best practices
2. Read relevant sources to gather detailed information
3. Check the local project files for any existing research notes
4. Save important findings as notes for future reference
5. Write a final summary report to ./output/research_summary.md

The summary should include:
- Key concepts and definitions
- Best practices and techniques (including the "lost in the middle" problem)
- Practical recommendations for agent developers
- References to sources consulted (use actual URLs from your research)"""

    # Intentionally weak initial prompt to show optimization improvement
    initial_prompt = """You are a research assistant. Help with research tasks using the available tools."""

    print("=" * 70)
    print("COMPREHENSIVE OPTIMIZATION LOOP DEMONSTRATION")
    print("=" * 70)
    print(f"\nTask:\n{task}")
    print(f"\nInitial (weak) prompt:\n{initial_prompt}")
    print(f"\nTools available: {', '.join(t['name'] for t in TOOLS)}")
    print("\n" + "=" * 70)
    print("Starting optimization loop...")
    print("=" * 70)

    # Run the optimization loop
    result = loop.run(
        task=task,
        initial_prompt=initial_prompt,
        tools=TOOLS,
        tool_executor=execute_tool,
    )

    # Show results
    print("\n" + "=" * 70)
    print("OPTIMIZATION RESULTS")
    print("=" * 70)

    print(f"\nTotal Iterations: {result.total_iterations}")
    print(f"Converged: {result.converged}")
    print(f"Score Improvement: {result.initial_score:.1f} → {result.final_score:.1f} ({result.improvement_percentage:+.1f}%)")

    print("\n" + "=" * 70)
    print("ITERATION DETAILS")
    print("=" * 70)

    for iteration in result.iterations:
        print(f"\n{'─' * 50}")
        print(f"ITERATION {iteration.iteration}")
        print(f"{'─' * 50}")
        print(f"Task Completed: {iteration.task_completed}")
        print(f"Score: {iteration.analysis.overall_score:.1f}/100")
        print(f"Patterns Found: {len(iteration.analysis.patterns)}")
        print(f"Tool Calls Made: {len(iteration.trace.tool_calls)}")
        print(f"Thinking Blocks: {len(iteration.trace.thinking_blocks)}")

        if iteration.analysis.patterns:
            print("\nDetected Patterns:")
            for p in iteration.analysis.patterns:
                print(f"  [{p.severity.value.upper()}] {p.type.value}")
                print(f"       {p.description[:80]}...")
                print(f"       Suggestion: {p.suggestion[:80]}...")

        if iteration.analysis.strengths:
            print("\nStrengths:")
            for s in iteration.analysis.strengths[:3]:
                print(f"  + {s[:80]}...")

        if iteration.analysis.weaknesses:
            print("\nWeaknesses:")
            for w in iteration.analysis.weaknesses[:3]:
                print(f"  - {w[:80]}...")

        if iteration.optimization and iteration.optimization.key_changes:
            print("\nKey Changes Applied:")
            for change in iteration.optimization.key_changes[:3]:
                print(f"  • {change[:80]}...")

    print("\n" + "=" * 70)
    print("FINAL OPTIMIZED PROMPT")
    print("=" * 70)
    print(result.final_prompt)

    # Show tool usage summary
    print("\n" + "=" * 70)
    print("TOOL USAGE ACROSS ALL ITERATIONS")
    print("=" * 70)

    tool_usage = {}
    for iteration in result.iterations:
        for tc in iteration.trace.tool_calls:
            tool_usage[tc.name] = tool_usage.get(tc.name, 0) + 1

    for tool_name, count in sorted(tool_usage.items(), key=lambda x: -x[1]):
        print(f"  {tool_name}: {count} calls")

    # Show saved notes
    if saved_notes:
        print("\n" + "=" * 70)
        print("NOTES SAVED DURING RESEARCH")
        print("=" * 70)
        for note in saved_notes:
            print(f"\n[{note['id']}] {note['title']}")
            if note['tags']:
                print(f"   Tags: {', '.join(note['tags'])}")
            print(f"   {note['content'][:150]}...")

    # Show written files
    if written_files:
        print("\n" + "=" * 70)
        print("FILES WRITTEN DURING RESEARCH")
        print("=" * 70)
        for path, content in written_files.items():
            print(f"\n{path} ({len(content)} chars)")
            print(f"   Preview: {content[:200]}...")

    # Generate a shareable skill
    print("\n" + "=" * 70)
    print("GENERATING SHAREABLE SKILL")
    print("=" * 70)

    generator = SkillGenerator(
        api_key=os.getenv("ANTHROPIC_API_KEY"),
        base_url="https://api.minimax.io/anthropic",
        model="MiniMax-M2.1",
    )

    skill_path = generator.generate(
        result=result,
        skill_name="comprehensive-research-agent",
        output_dir="./generated_skills",
        title="Comprehensive Research Agent Best Practices",
    )

    print(f"\nGenerated skill at: {skill_path}")
    print("\nThis skill captures the learnings from optimization and can be shared")
    print("with other developers to improve their research agents!")

    # Final summary
    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    print(f"""
The optimization loop demonstrated:

1. INTERLEAVED THINKING
   - {sum(len(i.trace.thinking_blocks) for i in result.iterations)} thinking blocks captured across {result.total_iterations} iterations
   - Full visibility into agent reasoning between tool calls

2. PATTERN DETECTION
   - Identified patterns: {', '.join(set(p.type.value for i in result.iterations for p in i.analysis.patterns)) or 'None'}
   - Each pattern includes evidence and suggestions

3. PROMPT OPTIMIZATION
   - Initial score: {result.initial_score:.1f}
   - Final score: {result.final_score:.1f}
   - Improvement: {result.improvement_percentage:+.1f}%

4. SKILL GENERATION
   - Created shareable skill at: {skill_path}
   - Captures learnings for other developers

5. REAL-WORLD URLS USED
   - Anthropic: docs.anthropic.com
   - OpenAI: platform.openai.com
   - MiniMax: minimax.io
   - DAIR.AI: promptingguide.ai
   - Research papers: arxiv.org
""")


if __name__ == "__main__":
    main()
