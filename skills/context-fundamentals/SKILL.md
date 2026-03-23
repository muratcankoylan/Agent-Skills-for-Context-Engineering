---
name: context-fundamentals
description: This skill should be used when the user asks to "understand context", "explain context windows", "design agent architecture", "debug context issues", "optimize context usage", or discusses context components, attention mechanics, progressive disclosure, or context budgeting. Provides foundational understanding of context engineering for AI agent systems.
---

# Context Engineering Fundamentals

Context is the complete state available to a language model at inference time — system instructions, tool definitions, retrieved documents, message history, and tool outputs. Context engineering is the discipline of curating the smallest high-signal token set that maximizes the likelihood of desired outcomes. Every paragraph below earns its tokens by teaching a non-obvious technique or providing an actionable threshold.

## When to Activate

Activate this skill when:
- Designing new agent systems or modifying existing architectures
- Debugging unexpected agent behavior that may relate to context
- Optimizing context usage to reduce token costs or improve performance
- Onboarding new team members to context engineering concepts
- Reviewing context-related design decisions

## Core Concepts

Treat context as a finite attention budget, not a storage bin. Every token added competes for the model's attention and depletes a budget that cannot be refilled mid-inference. The engineering problem is maximizing utility per token against three constraints: the hard token limit, the softer effective-capacity ceiling (typically 60-70% of the advertised window), and the U-shaped attention curve that penalizes information placed in the middle of context.

Apply four principles when assembling context:

1. **Informativity over exhaustiveness** — include only what matters for the current decision; design systems that can retrieve additional information on demand.
2. **Position-aware placement** — place critical constraints at the beginning and end of context, where recall accuracy runs 85-95%; the middle drops to 76-82% (the "lost-in-the-middle" effect).
3. **Progressive disclosure** — load skill names and summaries at startup; load full content only when a skill activates for a specific task.
4. **Iterative curation** — context engineering is not a one-time prompt-writing exercise but an ongoing discipline applied every time content is passed to the model.

## Detailed Topics

### The Anatomy of Context

**System Prompts**
Organize system prompts into distinct sections using XML tags or Markdown headers (background, instructions, tool guidance, output format). System prompts persist throughout the conversation, so place the most critical constraints at the beginning and end where attention is strongest.

Calibrate instruction altitude to balance two failure modes. Too-low altitude hardcodes brittle logic that breaks when conditions shift. Too-high altitude provides vague guidance that fails to give concrete signals for desired behavior. Aim for heuristic-driven instructions: specific enough to guide behavior, flexible enough to generalize — for example, numbered steps with room for judgment at each step.

Start minimal, then add instructions reactively based on observed failure modes rather than preemptively stuffing edge cases. Curate diverse, canonical few-shot examples that portray expected behavior instead of listing every possible scenario.

**Tool Definitions**
Write tool descriptions that answer three questions: what the tool does, when to use it, and what it returns. Include usage context, parameter defaults, and error cases — agents cannot disambiguate tools that a human engineer cannot disambiguate either.

Keep the tool set minimal. Consolidate overlapping tools because bloated tool sets create ambiguous decision points and consume disproportionate context after JSON serialization (tool schemas typically inflate 2-3x compared to equivalent plain-text descriptions).

**Retrieved Documents**
Maintain lightweight identifiers (file paths, stored queries, web links) and load data into context dynamically using just-in-time retrieval. This mirrors human cognition — maintain an index, not a copy. Strong identifiers (e.g., `customer_pricing_rates.json`) let agents locate relevant files even without search tools; weak identifiers (e.g., `data/file1.json`) force unnecessary loads.

When chunking large documents, split at natural semantic boundaries (section headers, paragraph breaks) rather than arbitrary character limits that sever mid-concept.

**Message History**
Message history serves as the agent's scratchpad memory for tracking progress, maintaining task state, and preserving reasoning across turns. For long-running tasks, it can grow to dominate context usage — monitor and apply compaction before it crowds out active instructions.

Cyclically refine history: once a tool has been called deep in the conversation, the raw result rarely needs to remain verbatim. Replace stale tool outputs with compact summaries or references to reduce low-signal bulk.

**Tool Outputs**
Tool outputs typically dominate context — research shows observations can reach 83.9% of total tokens in agent trajectories. Apply observation masking: replace verbose outputs with compact references once the agent has processed the result. Retain only the five most recently accessed file contents; compress or evict older ones.

### Context Windows and Attention Mechanics

**The Attention Budget**
For n tokens, the attention mechanism computes n-squared pairwise relationships. As context grows, the model's ability to maintain these relationships degrades — not as a hard cliff but as a performance gradient. Models trained predominantly on shorter sequences have fewer specialized parameters for context-wide dependencies, creating an effective ceiling well below the nominal window size.

Design for this gradient: assume effective capacity is 60-70% of the advertised window. A 200K-token model starts degrading around 120-140K tokens, and complex retrieval accuracy can drop to as low as 15% at extreme lengths.

**Position Encoding Limits**
Position encoding interpolation extends sequence handling beyond training lengths but introduces degradation in positional precision. Expect reduced accuracy for information retrieval and long-range reasoning at extended contexts compared to performance on shorter inputs.

**Progressive Disclosure in Practice**
Implement progressive disclosure at three levels:

1. **Skill selection** — load only names and descriptions at startup; activate full skill content on demand.
2. **Document loading** — load summaries first; fetch detail sections only when the task requires them.
3. **Tool result retention** — keep recent results in full; compress or evict older results.

Keep the boundary crisp: if a skill or document is activated, load it fully rather than partially — partial loads create confusing gaps that degrade reasoning quality.

### Context Quality Versus Quantity

Reject the assumption that larger context windows solve memory problems. Processing cost grows disproportionately with context length — not just linear cost scaling, but degraded model performance beyond effective capacity thresholds. Long inputs remain expensive even with prefix caching.

Apply the signal-density test: for each piece of context, ask whether removing it would change the model's output. If not, remove it. Redundant content does not merely waste tokens — it actively dilutes attention from high-signal content.

## Practical Guidance

### File-System-Based Access

Agents with filesystem access implement progressive disclosure naturally. Store reference materials, documentation, and data externally. Load files only when the current task requires them. Leverage the filesystem's own structure as metadata: file sizes suggest complexity, naming conventions hint at purpose, timestamps serve as proxies for relevance.

### Hybrid Context Strategies

Pre-load stable context for speed (CLAUDE.md files, project rules, core instructions) but enable autonomous exploration for dynamic content. The decision boundary depends on content volatility:

- **Low volatility** (project conventions, team standards): pre-load at session start.
- **High volatility** (code state, external data, user-specific info): retrieve just-in-time to avoid stale context.

For complex multi-hour tasks, maintain a structured notes file (e.g., NOTES.md) that the agent updates as it works. This enables coherence across context resets without keeping everything in the active window.

### Context Budgeting

Allocate explicit budgets per component and monitor during development. Implement compaction triggers at 70-80% utilization — do not wait for the window to fill. Design systems that degrade gracefully: when compaction fires, preserve architectural decisions, unresolved bugs, and implementation details while discarding redundant outputs.

For sub-agent architectures, enforce a compression ratio: a sub-agent may explore using tens of thousands of tokens but must return a condensed summary of 1,000-2,000 tokens. This converts exploration breadth into context-efficient results.

## Examples

**Example 1: Organizing System Prompts**
```markdown
<BACKGROUND_INFORMATION>
You are a Python expert helping a development team.
Current project: Data processing pipeline in Python 3.9+
</BACKGROUND_INFORMATION>

<INSTRUCTIONS>
- Write clean, idiomatic Python code
- Include type hints for function signatures
- Add docstrings for public functions
- Follow PEP 8 style guidelines
</INSTRUCTIONS>

<TOOL_GUIDANCE>
Use bash for shell operations, python for code tasks.
File operations should use pathlib for cross-platform compatibility.
</TOOL_GUIDANCE>

<OUTPUT_DESCRIPTION>
Provide code blocks with syntax highlighting.
Explain non-obvious decisions in comments.
</OUTPUT_DESCRIPTION>
```

**Example 2: Progressive Document Loading**
```markdown
# Instead of loading all documentation at once:

# Step 1: Load summary
docs/api_summary.md          # Lightweight overview

# Step 2: Load specific section as needed
docs/api/endpoints.md        # Only when API calls needed
docs/api/authentication.md   # Only when auth context needed
```

## Guidelines

1. Treat context as a finite resource with diminishing returns
2. Place critical information at attention-favored positions (beginning and end)
3. Use progressive disclosure to defer loading until needed
4. Organize system prompts with clear section boundaries
5. Monitor context usage during development
6. Implement compaction triggers at 70-80% utilization
7. Design for context degradation rather than hoping to avoid it
8. Prefer smaller high-signal context over larger low-signal context

## Gotchas

1. **Nominal window is not effective capacity**: A model advertising 200K tokens begins degrading around 120-140K. Budget for 60-70% of the nominal window as usable capacity. Exceeding this threshold causes sudden accuracy drops, not gradual degradation — test at realistic context sizes, not toy examples.

2. **Character-based token estimates silently drift**: The ~4 characters/token heuristic for English prose breaks down for code (2-3 chars/token), URLs and file paths (each slash, dot, and colon is a separate token), and non-English text (often 1-2 chars/token). Use the provider's actual tokenizer (e.g., tiktoken for OpenAI models, Anthropic's token counting API) for any budget-critical calculation.

3. **Tool schemas inflate 2-3x after JSON serialization**: A tool definition that looks compact in source code expands significantly when serialized — brackets, quotes, colons, and commas each consume tokens. Ten tools with moderate schemas can consume 5,000-8,000 tokens before a single message is sent. Audit serialized tool token counts, not source-code line counts.

4. **Message history balloons silently in agentic loops**: Each tool call adds both the request and the full response to history. After 20-30 iterations, history can consume 70-80% of the window while the agent shows no visible symptoms until reasoning quality collapses. Set a hard token ceiling on history and trigger compaction proactively.

5. **Critical instructions in the middle get lost**: The U-shaped attention curve means the middle of context receives 10-40% less recall accuracy than the beginning and end. Never place safety constraints, output format requirements, or behavioral guardrails in the middle of a long system prompt — anchor them at the top or bottom.

6. **Progressive disclosure that loads too eagerly defeats its purpose**: Loading every "potentially relevant" skill or document at the first hint of relevance recreates the context-stuffing problem. Set strict activation thresholds — a skill should load only when the task explicitly matches its trigger conditions, not when the topic is merely adjacent.

7. **Mixing instruction altitudes causes inconsistent behavior**: Combining hyper-specific rules ("always use exactly 3 bullet points") with vague directives ("be helpful") in the same prompt creates conflicting signals. Group instructions by altitude level and keep each section internally consistent — either heuristic-driven or prescriptive, not both interleaved.

## Integration

This skill provides foundational context that all other skills build upon. It should be studied first before exploring:

- context-degradation - Understanding how context fails
- context-optimization - Techniques for extending context capacity
- multi-agent-patterns - How context isolation enables multi-agent systems
- tool-design - How tool definitions interact with context

## References

Internal reference:
- [Context Components Reference](./references/context-components.md) - Read when: debugging a specific context component (system prompts, tool definitions, message history, tool outputs) or implementing chunking, observation masking, or budget allocation tables

Related skills in this collection:
- context-degradation - Read when: agent performance drops as conversations grow or context fills beyond 60% capacity
- context-optimization - Read when: token costs are too high or compaction/compression strategies are needed

External resources:
- Anthropic's "Effective Context Engineering for AI Agents" — production patterns for compaction, sub-agents, and hybrid retrieval
- Research on transformer attention mechanisms and the lost-in-the-middle effect
- Tokenomics research on agentic software engineering token distribution

---

## Skill Metadata

**Created**: 2025-12-20
**Last Updated**: 2026-03-17
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 2.0.0
