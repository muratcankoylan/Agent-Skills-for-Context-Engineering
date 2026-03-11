---
name: multi-agent-patterns
description: Designs and implements multi-agent architectures including supervisor/orchestrator, swarm, and hierarchical patterns with context isolation, coordination protocols, and failure recovery. Use when asked to design multi-agent systems, implement supervisor patterns, create swarm architectures, coordinate multiple agents, set up agent handoffs, or build parallel agent execution pipelines.
---

# Multi-Agent Architecture Patterns

Sub-agents exist primarily to isolate context, not to anthropomorphize role division. Design decisions should follow from this principle.

## When to Use Multi-Agent vs Single-Agent

| Signal | Use Multi-Agent | Stay Single-Agent |
|--------|----------------|-------------------|
| Context filling up with mixed concerns | Yes | - |
| Parallelizable independent subtasks | Yes | - |
| Different subtasks need different tools/prompts | Yes | - |
| Simple sequential task | - | Yes |
| Coordination overhead > parallelization gain | - | Yes |
| Task fits comfortably in one context | - | Yes |

**Cost reality**: Multi-agent systems use ~15x tokens vs single-agent. Model upgrades often outperform token budget increases. Choose multi-agent only when the task structure demands it.

## Architectural Patterns

### Pattern 1: Supervisor/Orchestrator

Central agent delegates to specialists and synthesizes results.

```
User Query -> Supervisor -> [Specialist, Specialist, Specialist] -> Aggregation -> Final Output
```

**Use when**: Clear task decomposition, cross-domain coordination, human oversight needed.

**Key risk - Telephone Game**: Supervisors paraphrase sub-agent responses, losing fidelity (50% perf drop in LangGraph benchmarks). Fix with a `forward_message` tool:

```python
def forward_message(message: str, to_user: bool = True):
    """Forward sub-agent response directly, bypassing supervisor synthesis."""
    if to_user:
        return {"type": "direct_response", "content": message}
    return {"type": "supervisor_input", "content": message}
```

### Pattern 2: Peer-to-Peer/Swarm

No central control. Agents hand off to each other via explicit transfer functions.

```python
def transfer_to_agent_b():
    return agent_b  # Handoff via function return

agent_a = Agent(name="Agent A", functions=[transfer_to_agent_b])
```

**Use when**: Flexible exploration, emergent requirements, rigid planning is counterproductive.

**Key risk**: Divergence without central state. Mitigate with convergence constraints and time-to-live limits.

### Pattern 3: Hierarchical

Layered abstraction: strategy (goals) -> planning (decomposition) -> execution (atomic tasks).

**Use when**: Large-scale projects, enterprise workflows, mixed high-level/detailed execution.

## Context Isolation

The primary benefit of multi-agent systems. Choose isolation strategy per subtask:

| Strategy | When to Use | Trade-off |
|----------|-------------|-----------|
| Full context delegation | Complex tasks needing complete understanding | Defeats isolation purpose if overused |
| Instruction passing | Simple, well-defined subtasks | Limits sub-agent flexibility |
| File system coordination | Shared state across agents | Latency + consistency challenges |

## Consensus and Coordination

Simple majority voting fails because it weights hallucinations equally with reasoning. Use instead:

1. **Weighted voting**: Weight by `confidence * domain_expertise`
2. **Debate protocols**: Adversarial critique over multiple rounds (higher accuracy than collaborative consensus)
3. **Trigger-based intervention**: Monitor for stalls (no progress) and sycophancy (agents mimicking without unique reasoning)

## Implementation Workflow

Follow these steps when building a multi-agent system:

### Step 1: Validate the Need
- Confirm single-agent cannot handle the task (context overflow, parallelization needed, or tool specialization required)
- If the task fits in one context window, stop here

### Step 2: Choose Pattern
- **Supervisor** if you need centralized control and human oversight
- **Swarm** if tasks are exploratory with emergent requirements
- **Hierarchical** if the project has natural abstraction layers

### Step 3: Define Agent Boundaries
For each agent, specify:
- System prompt (focused, no unnecessary context)
- Tool set (only what this agent needs)
- Output schema (structured, validated before passing downstream)
- Time-to-live limit (prevent infinite loops)

### Step 4: Implement Coordination
```python
# Handoff with explicit state transfer
def handle_request(request):
    if request.type == "billing":
        return transfer_to(billing_agent, context=request.billing_context)
    elif request.type == "technical":
        return transfer_to(technical_agent, context=request.tech_context)
    else:
        return handle_general(request)
```

### Step 5: Add Failure Recovery
For each agent-to-agent boundary:
- Validate outputs before passing downstream (prevent error propagation)
- Implement circuit breakers: 3 failures -> reroute to backup agent
- Use exponential backoff on retries: `delay = min(2^attempt, 60)`
- Checkpoint supervisor state to avoid context accumulation

### Step 6: Verify
- [ ] Each agent's context stays focused (no cross-contamination)
- [ ] Supervisor uses `forward_message` where synthesis would lose fidelity
- [ ] Circuit breakers configured for all agents
- [ ] Time-to-live limits prevent runaway execution
- [ ] Output schemas validated at every handoff point

## References

- [Frameworks Reference](./references/frameworks.md) - LangGraph, AutoGen, CrewAI implementation patterns
- Related skills: context-fundamentals, memory-systems, context-optimization, tool-design
