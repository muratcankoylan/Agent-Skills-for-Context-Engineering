---
name: tool-design
description: Design tools that agents can use effectively. Use when creating new tools for agents, debugging tool-related failures, or optimizing existing tool sets.
---

# Tool Design for Agents

Tools are the primary mechanism through which agents interact with the world. They define the contract between deterministic systems and non-deterministic agents. Unlike traditional software APIs designed for developers, tool APIs must be designed for language models that reason about intent, infer parameter values, and generate calls from natural language requests. Poor tool design creates failure modes that no amount of prompt engineering can fix. Effective tool design follows specific principles that account for how agents perceive and use tools.

## When to Activate

Activate this skill when:
- Creating new tools for agent systems
- Debugging tool-related failures or misuse
- Optimizing existing tool sets for better agent performance
- Designing tool APIs from scratch
- Evaluating third-party tools for agent integration
- Standardizing tool conventions across a codebase

## Core Concepts

Tools are contracts between deterministic systems and non-deterministic agents. The consolidation principle states that if a human engineer cannot definitively say which tool should be used in a given situation, an agent cannot be expected to do better. Effective tool descriptions are prompt engineering that shapes agent behavior.

Key principles include: clear descriptions that answer what, when, and what returns; response formats that balance completeness and token efficiency; error messages that enable recovery; and consistent conventions that reduce cognitive load.

## Detailed Topics

### The Tool-Agent Interface

**Tools as Contracts**
Tools are contracts between deterministic systems and non-deterministic agents. When humans call APIs, they understand the contract and make appropriate requests. Agents must infer the contract from descriptions and generate calls that match expected formats.

This fundamental difference requires rethinking API design. The contract must be unambiguous, examples must illustrate expected patterns, and error messages must guide correction. Every ambiguity in tool definitions becomes a potential failure mode.

**Tool Description as Prompt**
Tool descriptions are loaded into agent context and collectively steer behavior. The descriptions are not just documentation—they are prompt engineering that shapes how agents reason about tool use.

Poor descriptions like "Search the database" with cryptic parameter names force agents to guess. Optimized descriptions include usage context, examples, and defaults. The description answers: what the tool does, when to use it, and what it produces.

**Namespacing and Organization**
As tool collections grow, organization becomes critical. Namespacing groups related tools under common prefixes, helping agents select appropriate tools at the right time.

Namespacing creates clear boundaries between functionality. When an agent needs database information, it routes to the database namespace. When it needs web search, it routes to web namespace.

### The Consolidation Principle

**Single Comprehensive Tools**
The consolidation principle states that if a human engineer cannot definitively say which tool should be used in a given situation, an agent cannot be expected to do better. This leads to a preference for single comprehensive tools over multiple narrow tools.

Instead of implementing list_users, list_events, and create_event, implement schedule_event that finds availability and schedules. The comprehensive tool handles the full workflow internally rather than requiring agents to chain multiple calls.

**Why Consolidation Works**
Agents have limited context and attention. Each tool in the collection competes for attention in the tool selection phase. Each tool adds description tokens that consume context budget. Overlapping functionality creates ambiguity about which tool to use.

Consolidation reduces token consumption by eliminating redundant descriptions. It eliminates ambiguity by having one tool cover each workflow. It reduces tool selection complexity by shrinking the effective tool set.

**When Not to Consolidate**
Consolidation is not universally correct. Tools with fundamentally different behaviors should remain separate. Tools used in different contexts benefit from separation. Tools that might be called independently should not be artificially bundled.

### Tool Description Engineering

**Description Structure**
Effective tool descriptions answer four questions:

What does the tool do? Clear, specific description of functionality. Avoid vague language like "helps with" or "can be used for." State exactly what the tool accomplishes.

When should it be used? Specific triggers and contexts. Include both direct triggers ("User asks about pricing") and indirect signals ("Need current market rates").

What inputs does it accept? Parameter descriptions with types, constraints, and defaults. Explain what each parameter controls.

What does it return? Output format and structure. Include examples of successful responses and error conditions.

**Default Parameter Selection**
Defaults should reflect common use cases. They reduce agent burden by eliminating unnecessary parameter specification. They prevent errors from omitted parameters.

### Response Format Optimization

Tool response size significantly impacts context usage. Implementing response format options gives agents control over verbosity.

Concise format returns essential fields only, appropriate for confirmation or basic information. Detailed format returns complete objects with all fields, appropriate when full context is needed for decisions.

Include guidance in tool descriptions about when to use each format. Agents learn to select appropriate formats based on task requirements.

### Error Message Design

Error messages serve two audiences: developers debugging issues and agents recovering from failures. For agents, error messages must be actionable. They must tell the agent what went wrong and how to correct it.

Design error messages that enable recovery. For retryable errors, include retry guidance. For input errors, include corrected format. For missing data, include what's needed.

### Tool Definition Schema

Use a consistent schema across all tools. Establish naming conventions: verb-noun pattern for tool names, consistent parameter names across tools, consistent return field names.

### Tool Collection Design

Research shows tool description overlap causes model confusion. More tools do not always lead to better outcomes. A reasonable guideline is 10-20 tools for most applications. If more are needed, use namespacing to create logical groupings.

Implement mechanisms to help agents select the right tool: tool grouping, example-based selection, and hierarchy with umbrella tools that route to specialized sub-tools.

### Testing Tool Design

Evaluate tool designs against criteria: unambiguity, completeness, recoverability, efficiency, and consistency. Test tools by presenting representative agent requests and evaluating the resulting tool calls.

## Practical Guidance

### Anti-Patterns to Avoid

Vague descriptions: "Search the database for customer information" leaves too many questions unanswered.

Cryptic parameter names: Parameters named x, val, or param1 force agents to guess meaning.

Missing error handling: Tools that fail with generic errors provide no recovery guidance.

Inconsistent naming: Using id in some tools, identifier in others, and customer_id in some creates confusion.

### Tool Selection Framework

When designing tool collections:
1. Identify distinct workflows agents must accomplish
2. Group related actions into comprehensive tools
3. Ensure each tool has a clear, unambiguous purpose
4. Document error cases and recovery paths
5. Test with actual agent interactions

## Examples

**Example 1: Well-Designed Tool**
```python
def get_customer(customer_id: str, format: str = "concise"):
    """
    Retrieve customer information by ID.
    
    Use when:
    - User asks about specific customer details
    - Need customer context for decision-making
    - Verifying customer identity
    
    Args:
        customer_id: Format "CUST-######" (e.g., "CUST-000001")
        format: "concise" for key fields, "detailed" for complete record
    
    Returns:
        Customer object with requested fields
    
    Errors:
        NOT_FOUND: Customer ID not found
        INVALID_FORMAT: ID must match CUST-###### pattern
    """
```

**Example 2: Poor Tool Design**

This example demonstrates several tool design anti-patterns:

```python
def search(query):
    """Search the database."""
    pass
```

**Problems with this design:**

1. **Vague name**: "search" is ambiguous - search what, for what purpose?
2. **Missing parameters**: What database? What format should query take?
3. **No return description**: What does this function return? A list? A string? Error handling?
4. **No usage context**: When should an agent use this versus other tools?
5. **No error handling**: What happens if the database is unavailable?

**Failure modes:**
- Agents may call this tool when they should use a more specific tool
- Agents cannot determine correct query format
- Agents cannot interpret results
- Agents cannot recover from failures

## Guidelines

1. Write descriptions that answer what, when, and what returns
2. Use consolidation to reduce ambiguity
3. Implement response format options for token efficiency
4. Design error messages for agent recovery
5. Establish and follow consistent naming conventions
6. Limit tool count and use namespacing for organization
7. Test tool designs with actual agent interactions
8. Iterate based on observed failure modes

## Integration

This skill connects to:
- [context-fundamentals](skills/context-fundamentals/SKILL.md) - How tools interact with context
- [multi-agent-patterns](skills/multi-agent-patterns/SKILL.md) - Specialized tools per agent
- [evaluation](skills/evaluation/SKILL.md) - Evaluating tool effectiveness

## References

Internal skills:
- [context-fundamentals](skills/context-fundamentals/SKILL.md) - Tool context interactions
- [evaluation](skills/evaluation/SKILL.md) - Tool testing patterns

External resources:
- MCP (Model Context Protocol) documentation
- Framework tool conventions
- API design best practices for agents

---

## Skill Metadata

**Created**: 2025-12-20
**Last Updated**: 2025-12-20
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 1.0.0
