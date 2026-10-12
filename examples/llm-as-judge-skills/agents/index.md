---
name: llm-as-judge-agents
description: Index of available LLM-as-a-Judge agents: evaluator, researcher, and orchestrator
---

# Agents Index

Agents are reusable AI components with defined capabilities, tools, and instructions.

## Available Agents

### Evaluator Agent
**Path**: `agents/evaluator-agent/evaluator-agent.md`
**Purpose**: Assess the quality of LLM-generated responses

**Capabilities**:
- Direct scoring against rubrics
- Pairwise comparison of responses
- Criteria extraction from task descriptions
- Rubric generation for evaluation

**Tools Used**:
- `directScore`
- `pairwiseCompare`
- `extractCriteria`
- `generateRubric`

**Best For**:
- Quality gates in content pipelines
- Model comparison studies
- RLHF preference data generation
- Output validation before delivery

---

### Research Agent
**Path**: `agents/research-agent/research-agent.md`
**Purpose**: Gather, verify, and synthesize information from multiple sources

**Capabilities**:
- Web search and result analysis
- URL content extraction
- Claim extraction and verification
- Research synthesis

**Tools Used**:
- `webSearch`
- `readUrl`
- `extractClaims`
- `verifyClaim`
- `synthesize`

**Best For**:
- Knowledge base building
- Fact checking
- Market research
- Technical documentation

---

### Orchestrator Agent
**Path**: `agents/orchestrator-agent/orchestrator-agent.md`
**Purpose**: Coordinate multi-agent workflows for complex tasks

**Capabilities**:
- Task decomposition and assignment
- Parallel task execution
- Result synthesis
- Error handling and recovery

**Tools Used**:
- `delegateToAgent`
- `parallelExecution`
- `waitForCompletion`
- `synthesizeResults`
- `handleError`

**Best For**:
- Complex multi-step tasks
- Cross-capability workflows
- Quality-assured pipelines
- Long-running operations

## Agent Interaction Patterns

### Sequential Pipeline
```
Input → Agent A → Agent B → Agent C → Output
```
Use when each step depends on the previous.

### Parallel Fan-Out
```
        ┌→ Agent A ─┐
Input ──┼→ Agent B ──┼→ Synthesis → Output
        └→ Agent C ─┘
```
Use for independent subtasks that can run concurrently.

### Iterative Refinement
```
Input → Agent → Evaluator ─┬→ Output (if pass)
                           └→ Agent (if fail, with feedback)
```
Use for quality-critical outputs.

## Adding New Agents

1. Create agent directory: `agents/<agent-name>/`
2. Create main file: `agents/<agent-name>/<agent-name>.md`
3. Define:
   - Purpose and role
   - System instructions
   - Tool assignments
   - Configuration options
   - Usage examples
4. Update this index
5. Register with orchestrator if applicable

