---
name: context-engineering-collection
description: A comprehensive collection of Agent Skills for context engineering, multi-agent architectures, and production agent systems. Use when building, optimizing, or debugging agent systems that require effective context management.
---

# Agent Skills for Context Engineering

This collection provides structured guidance for building production-grade AI agent systems through effective context engineering.

## When to Activate

Activate these skills when:
- Building new agent systems from scratch
- Optimizing existing agent performance
- Debugging context-related failures
- Designing multi-agent architectures
- Creating or evaluating tools for agents
- Implementing memory and persistence layers

## Skill Map

### Foundational Context Engineering

**Understanding Context Fundamentals**
Context is not just prompt text—it is the complete state available to the language model at inference time, including system instructions, tool definitions, retrieved documents, message history, and tool outputs. Effective context engineering means understanding what information truly matters for the task at hand and curating that information for maximum signal-to-noise ratio.

**Recognizing Context Degradation**
Language models exhibit predictable degradation patterns as context grows: the "lost-in-middle" phenomenon where information in the center of context receives less attention; U-shaped attention curves that prioritize beginning and end; context poisoning when errors compound; and context distraction when irrelevant information overwhelms relevant content.

### Architectural Patterns

**Multi-Agent Coordination**
Production multi-agent systems converge on three dominant patterns: supervisor/orchestrator architectures with centralized control, peer-to-peer swarm architectures for flexible handoffs, and hierarchical structures for complex task decomposition. The critical insight is that sub-agents exist primarily to isolate context rather than to simulate organizational roles.

**Memory System Design**
Memory architectures range from simple scratchpads to sophisticated temporal knowledge graphs. Vector RAG provides semantic retrieval but loses relationship information. Knowledge graphs preserve structure but require more engineering investment. The file-system-as-memory pattern enables just-in-time context loading without stuffing context windows.

**Tool Design Principles**
Tools are contracts between deterministic systems and non-deterministic agents. Effective tool design follows the consolidation principle (prefer single comprehensive tools over multiple narrow ones), returns contextual information in errors, supports response format options for token efficiency, and uses clear namespacing.

### Operational Excellence

**Context Optimization**
Techniques include compaction (summarizing context near limits), observation masking (replacing verbose tool outputs with references), prefix caching (reusing KV blocks across requests), and strategic context partitioning (splitting work across sub-agents with isolated contexts).

**Evaluation Frameworks**
Production agent evaluation requires multi-dimensional rubrics covering factual accuracy, completeness, tool efficiency, and process quality. Effective patterns include LLM-as-judge for scalability, human evaluation for edge cases, and end-state evaluation for agents that mutate persistent state.

## Core Concepts

The collection is organized around three core themes. First, context fundamentals establish what context is, how attention mechanisms work, and why context quality matters more than quantity. Second, architectural patterns cover the structures and coordination mechanisms that enable effective agent systems. Third, operational excellence addresses the ongoing work of optimizing and evaluating production systems.

## Practical Guidance

Each skill can be used independently or in combination. Start with fundamentals to establish context management mental models. Branch into architectural patterns based on your system requirements. Reference operational skills when optimizing production systems.

The skills are platform-agnostic and work with Claude Code, Cursor, or any agent framework that supports custom instructions or skill-like constructs.

## Integration

This collection integrates with itself—skills reference each other and build on shared concepts. The fundamentals skill provides context for all other skills. Architectural skills (multi-agent, memory, tools) can be combined for complex systems. Operational skills (optimization, evaluation) apply to any system built using the foundational and architectural skills.

## References

Internal skills in this collection:
- [context-fundamentals](skills/context-fundamentals/SKILL.md)
- [context-degradation](skills/context-degradation/SKILL.md)
- [multi-agent-patterns](skills/multi-agent-patterns/SKILL.md)
- [memory-systems](skills/memory-systems/SKILL.md)
- [tool-design](skills/tool-design/SKILL.md)
- [context-optimization](skills/context-optimization/SKILL.md)
- [evaluation](skills/evaluation/SKILL.md)

External resources on context engineering:
- Research on attention mechanisms and context window limitations
- Production experience from leading AI labs on agent system design
- Framework documentation for LangGraph, AutoGen, and CrewAI

---

## Skill Metadata

**Created**: 2025-12-20
**Last Updated**: 2025-12-20
**Author**: Agent Skills for Context Engineering Contributors
**Version**: 1.0.0
