# Example: X-to-Book Multi-Agent System

This example demonstrates how the Agent Skills for Context Engineering can be applied to design a production multi-agent system. The system monitors X (Twitter) accounts and generates daily synthesized books from their content.

## The Problem

A user requested a multi-agent system that:
- Monitors target X accounts daily
- Extracts insights and patterns from tweets
- Produces structured book output

This is a non-trivial agent system because:
- High-volume data (hundreds of tweets per day)
- Long-form output requiring coherence
- Temporal awareness (tracking how narratives evolve)
- Quality requirements (accurate attribution, no hallucination)

## Skills Applied

### 1. multi-agent-patterns

**Decision**: Selected Supervisor/Orchestrator pattern over peer-to-peer swarm.

**Reasoning from skill**:
> "The supervisor pattern places a central agent in control, delegating to specialists and synthesizing results. The supervisor maintains global state and trajectory, decomposes user objectives into subtasks, and routes to appropriate workers."

**Application**: Book production has clear sequential phases (scrape → analyze → synthesize → write → edit) that benefit from central coordination. Quality gates between phases require explicit checkpoints.

**Failure mode addressed**:
> "Supervisor Bottleneck: The supervisor accumulates context from all workers, becoming susceptible to saturation and degradation."

**Mitigation applied**: Raw tweet data never passes through Orchestrator context. Scraper writes to file system, other agents read from file system. Orchestrator receives only phase summaries.

### 2. context-fundamentals

**Decision**: Strict context budgets per agent with progressive disclosure.

**Reasoning from skill**:
> "Context must be treated as a finite resource with diminishing marginal returns. Like humans with limited working memory, language models have an attention budget drawn on when parsing large volumes of context."

**Application**: Each agent has an explicit token budget:
- Orchestrator: 50k (routing only)
- Scraper: 20k (one account at a time)
- Writer: 80k (one chapter at a time)

**Principle applied**:
> "Progressive disclosure manages context efficiently by loading information only as needed."

**Application**: Book outline loads first (lightweight). Full chapter content loads only when Writer is working on that specific chapter.

### 3. memory-systems

**Decision**: Temporal Knowledge Graph over simple vector store.

**Reasoning from skill**:
> "Vector stores lose relationship information... Vector stores also struggle with temporal validity. Facts change over time, but vector stores provide no mechanism to distinguish 'current fact' from 'outdated fact'."

**Application**: The system needs to answer queries like:
- "What was @account's position on AI regulation in January?"
- "Which accounts agree/disagree on crypto?"

These require relationship traversal and temporal validity that vector stores cannot provide.

**Architecture from skill**:
> "Temporal knowledge graphs add validity periods to facts. Each fact has a 'valid from' and optionally 'valid until' timestamp."

**Application**: All relationships (DISCUSSES, AGREES_WITH, DISAGREES_WITH) have temporal validity periods.

### 4. context-optimization

**Decision**: Observation masking for tweet data.

**Reasoning from skill**:
> "Tool outputs can comprise 80%+ of token usage in agent trajectories. Much of this is verbose output that has already served its purpose."

**Application**: Daily tweet volume could reach 100k+ tokens. This data is:
1. Processed by Scraper
2. Written to file system (not passed through context)
3. Read by Analyzer in chunks
4. Summarized before reaching Synthesizer

**Compaction trigger from skill**:
> "Compaction is the practice of summarizing context contents when approaching limits."

**Application**: Phase outputs are compacted at 70% context utilization before passing to next phase.

### 5. tool-design

**Decision**: Three consolidated tools instead of 15+ narrow tools.

**Reasoning from skill**:
> "The consolidation principle states that if a human engineer cannot definitively say which tool should be used in a given situation, an agent cannot be expected to do better."

**Application**: Instead of separate tools for `fetch_timeline`, `fetch_thread`, `fetch_engagement`, `search_tweets`, we implement one `x_data_tool` with an action parameter.

**Tool description pattern from skill**:
> "Effective tool descriptions answer four questions: What does the tool do? When should it be used? What inputs does it accept? What does it return?"

**Application**: Each tool has explicit usage triggers, parameter documentation, and error recovery guidance.

### 6. evaluation

**Decision**: Multi-dimensional rubric with automated pipeline.

**Reasoning from skill**:
> "Agent quality is not a single dimension. It includes factual accuracy, completeness, coherence, tool efficiency, and process quality."

**Application**: Five evaluation dimensions weighted by importance:
- Source Accuracy (30%) - quotes match preserved source records with IDs and URLs
- Thematic Coherence (25%) - narrative flow
- Completeness (20%) - theme coverage
- Insight Quality (15%) - synthesis beyond restating
- Readability (10%) - prose quality

**Human review trigger from skill**:
> "Human evaluation catches what automation misses."

**Application**: Books scoring below 0.7 or with source accuracy below 0.8 are flagged for human review.

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     ORCHESTRATOR AGENT                          │
│  Context: 50k tokens (routing, checkpoints, no raw data)        │
│  Pattern: Supervisor with file-system coordination              │
└─────────────────────────────────────────────────────────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────┐ ┌─────────────┐ ┌─────────────┐ ┌─────────────┐
│   SCRAPER   │ │  ANALYZER   │ │   WRITER    │ │   EDITOR    │
│   20k ctx   │ │   80k ctx   │ │   80k ctx   │ │   60k ctx   │
│ Per-account │ │ Per-account │ │ Per-chapter │ │ Per-chapter │
└─────────────┘ └─────────────┘ └─────────────┘ └─────────────┘
         │              │              │              │
         ▼              ▼              ▼              ▼
┌─────────────────────────────────────────────────────────────────┐
│                     FILE SYSTEM STORAGE                          │
│  raw_data/{account}/{date}.json                                  │
│  analysis/{account}/{date}.json                                  │
│  drafts/{book_id}/chapter_{n}.md                                 │
└─────────────────────────────────────────────────────────────────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                 TEMPORAL KNOWLEDGE GRAPH                         │
│  Entities: Account, Tweet, Theme, Book, Chapter                  │
│  Relationships: POSTED, DISCUSSES, AGREES_WITH, SOURCES          │
│  All relationships have temporal validity periods                │
└─────────────────────────────────────────────────────────────────┘
```

## Key Patterns Demonstrated

| Pattern | Skill Source | Application |
|---------|--------------|-------------|
| Context isolation via sub-agents | multi-agent-patterns | Each agent has clean context for its phase |
| File system as coordination mechanism | multi-agent-patterns | Avoids context bloat from shared state passing |
| Progressive disclosure | context-fundamentals | Chapter content loads only when needed |
| Temporal knowledge graph | memory-systems | Tracks evolving positions over time |
| Observation masking | context-optimization | Raw tweets never enter orchestrator context |
| Tool consolidation | tool-design | 3 tools instead of 15+ |
| Source record provenance | tool-design + evaluation | Every quote traces to preserved source evidence |
| Multi-dimensional evaluation | evaluation | 5 weighted quality dimensions |

## Files

- [PRD.md](./PRD.md) - Complete Product Requirements Document
- [SKILLS-MAPPING.md](./SKILLS-MAPPING.md) - Detailed mapping of skills to design decisions
- [XQUIK-ADAPTER.md](./XQUIK-ADAPTER.md) - Concrete REST and MCP source adapter

## Using This Example

This example serves as a template for applying context engineering skills to new projects:

1. **Identify context challenges**: What are the volume constraints? What causes context saturation?
2. **Select architecture pattern**: Based on coordination needs, choose supervisor, swarm, or hierarchical
3. **Design memory system**: Based on query patterns, choose vector store, knowledge graph, or temporal graph
4. **Apply optimization techniques**: Observation masking, compaction, progressive disclosure as needed
5. **Build evaluation framework**: Define dimensions relevant to your use case

The skills provide the vocabulary and patterns; the application requires understanding your specific constraints.
