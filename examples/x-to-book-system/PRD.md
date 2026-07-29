# PRD: X-to-Book Multi-Agent System

## Overview

A multi-agent system that monitors target X (Twitter) accounts daily, synthesizes their content, and generates structured books from accumulated insights. The system uses context engineering principles to handle high-volume social data while maintaining coherent long-form output.

## Problem Statement

Manual curation of insights from X accounts is time-consuming and inconsistent. Existing tools dump raw data without synthesis. We need a system that:
- Continuously monitors specified X accounts
- Extracts meaningful patterns and insights across time
- Produces structured, coherent daily book outputs
- Maintains temporal awareness of how narratives evolve

## Architecture

### Multi-Agent Pattern Selection: Supervisor/Orchestrator

Based on the context engineering patterns, we use a **supervisor architecture** because:
1. Book production has clear sequential phases (scrape, analyze, synthesize, write, edit)
2. Quality gates require central coordination
3. Human oversight points are well-defined
4. Context isolation per phase prevents attention saturation

```
User Config -> Orchestrator -> [Scraper, Analyzer, Synthesizer, Writer, Editor] -> Daily Book
```

### Agent Definitions

#### 1. Orchestrator Agent
**Purpose**: Central coordinator that manages workflow, maintains state, routes to specialists.

**Context Budget**: Reserved for task decomposition, quality gates, and synthesis coordination. Does not carry raw tweet data.

**Responsibilities**:
- Decompose daily book task into subtasks
- Route to appropriate specialist agents
- Implement checkpoint/resume for long-running operations
- Aggregate results without paraphrasing (avoid telephone game problem)

```python
class OrchestratorState(TypedDict):
    target_accounts: List[str]
    current_phase: str
    phase_outputs: Dict[str, Any]
    quality_scores: Dict[str, float]
    book_outline: str
    checkpoints: List[Dict]
```

#### 2. Scraper Agent
**Purpose**: Fetch and normalize content from target X accounts.

**Context Budget**: Minimal. Operates on one account at a time, outputs to file system.

**Tools**:
- `fetch_timeline(account_id, since_date, until_date)` - Retrieve tweets in date range
- `fetch_thread(tweet_id)` - Expand full thread context
- `fetch_engagement_metrics(tweet_ids)` - Get likes/retweets/replies
- `write_to_store(account_id, data)` - Persist to file system

**Output**: Append-only source records per account, written to the file system
and never passed through Orchestrator context.

### Source Provenance Contract

The Writer and Editor cannot verify quotes from previews or untyped provider
responses. Normalize every fetched post into a provider-neutral source record
before analysis:

```python
class SourceRecord(TypedDict):
    source_record_id: str
    tweet_id: str
    conversation_id: Optional[str]
    author_id: str
    author_username: str
    text: str
    created_at: str
    source_url: str
    fetched_at: str
    content_sha256: str
    engagement: Dict[str, int]
    raw_artifact: str
```

Apply these rules at the source boundary:

1. Write the original provider response to an append-only `raw_artifact`.
2. Compute `content_sha256` from the captured post before normalization.
3. Reject records missing the post ID, full text, author, timestamp, or URL.
4. Preserve `source_record_id` through analysis, outlines, drafts, and edits.
5. Use concise records for routing only. Load detailed records before quoting.
6. Verify each quote as an exact span of `text` and retain its ID and URL.

Refreshing a post creates a new source record. It never overwrites the evidence
used by a previously generated book.

#### 3. Analyzer Agent
**Purpose**: Extract patterns, themes, and insights from raw content.

**Context Budget**: Moderate. Processes one account's data at a time via file system reads.

**Responsibilities**:
- Topic extraction and clustering
- Sentiment analysis over time
- Key insight identification
- Thread narrative extraction
- Controversy/debate identification

**Output**: Structured analysis per account with:
- Top themes (ranked by frequency and engagement)
- Notable quotes (with context)
- Narrative arcs (multi-tweet threads)
- Temporal patterns (time-of-day, response patterns)

#### 4. Synthesizer Agent
**Purpose**: Cross-account pattern recognition and theme consolidation.

**Context Budget**: High. Receives summaries from all analyzed accounts.

**Responsibilities**:
- Identify cross-account themes
- Detect agreement/disagreement patterns
- Build narrative connections
- Generate book outline with chapter structure

**Output**: Book outline with:
- Chapter structure
- Theme assignments per chapter
- Source attribution map
- Suggested narrative flow

#### 5. Writer Agent
**Purpose**: Generate book content from outline and source material.

**Context Budget**: Per-chapter allocation. Works on one chapter at a time.

**Responsibilities**:
- Draft chapter content following outline
- Integrate quotes with proper attribution
- Maintain consistent voice and style
- Handle transitions between themes

**Output**: Draft chapters in markdown format.

#### 6. Editor Agent
**Purpose**: Quality assurance and refinement.

**Context Budget**: Per-chapter. Reviews one chapter at a time.

**Responsibilities**:
- Fact-check against source material
- Verify quote accuracy
- Check narrative coherence
- Flag potential issues for human review

**Output**: Edited chapters with revision notes.

---

## Memory System Design

### Architecture: Temporal Knowledge Graph

Based on the memory-systems skill, we need a **temporal knowledge graph** because:
- Facts about accounts change over time (opinions shift, topics evolve)
- We need time-travel queries ("What was @account's position on X in January?")
- Cross-account relationships require graph traversal
- Simple vector stores lose relationship structure

### Entity Types

```python
entities = {
    "Account": {
        "properties": ["handle", "display_name", "bio", "follower_count", "following_count"]
    },
    "Tweet": {
        "properties": ["content", "timestamp", "engagement_score", "thread_id"]
    },
    "Theme": {
        "properties": ["name", "description", "first_seen", "last_seen"]
    },
    "Book": {
        "properties": ["date", "title", "chapter_count", "word_count"]
    },
    "Chapter": {
        "properties": ["title", "theme", "word_count", "source_accounts"]
    }
}
```

### Relationship Types

```python
relationships = {
    "POSTED": {
        "from": "Account",
        "to": "Tweet",
        "temporal": True
    },
    "DISCUSSES": {
        "from": "Tweet",
        "to": "Theme",
        "temporal": True,
        "properties": ["sentiment", "stance"]
    },
    "RESPONDS_TO": {
        "from": "Tweet",
        "to": "Tweet"
    },
    "AGREES_WITH": {
        "from": "Account",
        "to": "Account",
        "temporal": True,
        "properties": ["on_theme"]
    },
    "DISAGREES_WITH": {
        "from": "Account",
        "to": "Account",
        "temporal": True,
        "properties": ["on_theme"]
    },
    "CONTAINS": {
        "from": "Book",
        "to": "Chapter"
    },
    "SOURCES": {
        "from": "Chapter",
        "to": "Tweet"
    }
}
```

### Memory Retrieval Patterns

```python
# What has @account said about AI in the last 30 days?
query_account_theme_temporal(account_id, theme="AI", days=30)

# Which accounts disagree on crypto?
query_disagreement_network(theme="crypto")

# What quotes should be in today's book about regulation?
query_quotable_content(theme="regulation", min_engagement=100)
```

---

## Context Optimization Strategy

### Challenge

X data is high-volume. A target account with 20 tweets/day across 10 accounts = 200 tweets/day. Each tweet with thread context averages 500 tokens. Daily raw context = 100k tokens before analysis.

### Optimization Techniques

#### 1. Observation Masking
Raw tweet data is processed by Scraper, written to file system, and never passed through Orchestrator context.

```python
# Instead of passing raw tweets through context
# Scraper writes to file system
scraper.write_to_store(account_id, raw_tweets)

# Analyzer reads from file system
raw_data = analyzer.read_from_store(account_id)
```

#### 2. Compaction Triggers

```python
COMPACTION_THRESHOLD = 0.7  # 70% context utilization

if context_utilization > COMPACTION_THRESHOLD:
    # Summarize older phase outputs
    phase_outputs = compact_phase_outputs(phase_outputs)
```

#### 3. Progressive Disclosure

Book outline loads first (lightweight). Full chapter content loads only when Writer is working on that chapter.

```python
# Level 1: Outline only
book_outline = {
    "chapters": [
        {"title": "Chapter 1", "themes": ["AI", "Regulation"], "word_count_target": 2000}
    ]
}

# Level 2: Full chapter context (only when writing)
chapter_context = load_chapter_context(chapter_id)
```

#### 4. KV-Cache Optimization

System prompt and tool definitions are stable across runs. Structure context for cache hits:

```python
context_order = [
    system_prompt,       # Stable, cacheable
    tool_definitions,    # Stable, cacheable
    account_config,      # Semi-stable
    daily_outline,       # Changes daily
    current_task         # Changes per call
]
```

---

## Tool Design

### Consolidation Principle Applied

Instead of multiple narrow tools, we implement comprehensive tools per domain:

#### X Data Tool (Consolidated)

```python
def x_data_tool(
    action: Literal["fetch_timeline", "fetch_thread", "fetch_engagement", "search"],
    account_id: Optional[str] = None,
    tweet_id: Optional[str] = None,
    query: Optional[str] = None,
    since_date: Optional[str] = None,
    until_date: Optional[str] = None,
    format: Literal["concise", "detailed"] = "concise"
) -> Dict:
    """
    Unified X data retrieval tool.
    
    Use when:
    - Fetching timeline for target account monitoring
    - Expanding thread context for full conversation
    - Getting engagement metrics for content prioritization
    - Searching for specific topics across accounts
    
    Actions:
    - fetch_timeline: Get tweets from account in date range
    - fetch_thread: Expand full thread from single tweet
    - fetch_engagement: Get likes/retweets/replies
    - search: Search across accounts for query
    
    Returns:
    - Both formats: source_record_id, tweet_id, source_url, fetched_at
    - concise: author_username, content_preview, timestamp, engagement_score
    - detailed: full SourceRecord, thread context, all engagement metrics,
      reply records
    
    Errors:
    - RATE_LIMITED: Wait {retry_after} seconds
    - PAYMENT_REQUIRED: Stop and surface the account action
    - DEPENDENCY_UNAVAILABLE: Retry with capped exponential backoff
    - ACCOUNT_PRIVATE: Cannot access private account
    - NOT_FOUND: Tweet/account does not exist
    """
```

#### Xquik Adapter

Xquik provides one concrete read adapter for `x_data_tool`. Keep it at the
source boundary. Normalize every response before agents consume it.

See [XQUIK-ADAPTER.md](./XQUIK-ADAPTER.md) for exact operations, field mapping,
pagination, errors, authentication, MCP usage, and implementation references.

#### Memory Tool (Consolidated)

```python
def memory_tool(
    action: Literal["store", "query", "update_validity", "consolidate"],
    entity_type: Optional[str] = None,
    entity_id: Optional[str] = None,
    relationship_type: Optional[str] = None,
    query_params: Optional[Dict] = None,
    as_of_date: Optional[str] = None
) -> Dict:
    """
    Unified memory system tool.
    
    Use when:
    - Storing new facts discovered from X data
    - Querying historical information about accounts/themes
    - Updating validity periods when facts change
    - Running consolidation to merge duplicate facts
    
    Actions:
    - store: Add new entity or relationship
    - query: Retrieve entities/relationships matching params
    - update_validity: Mark fact as expired with valid_until
    - consolidate: Merge duplicates and cleanup
    
    Returns entity/relationship data or query results.
    """
```

#### Writing Tool (Consolidated)

```python
def writing_tool(
    action: Literal["draft", "edit", "format", "export"],
    content: Optional[str] = None,
    chapter_id: Optional[str] = None,
    style_guide: Optional[str] = None,
    output_format: Literal["markdown", "html", "pdf"] = "markdown"
) -> Dict:
    """
    Unified book writing tool.
    
    Use when:
    - Drafting new chapter content
    - Editing existing content for quality
    - Formatting content for output
    - Exporting final book
    
    Actions:
    - draft: Create initial chapter draft
    - edit: Apply revisions to existing content
    - format: Apply styling and formatting
    - export: Generate final output file
    """
```

---

## Evaluation Framework

### Multi-Dimensional Rubric

Based on the evaluation skill, we define quality dimensions:

| Dimension | Weight | Excellent | Acceptable | Failed |
|-----------|--------|-----------|------------|--------|
| Source Accuracy | 30% | Every quote matches a source record with ID and URL | Minor non-quote attribution errors | Fabricated, altered, or untraceable quotes |
| Thematic Coherence | 25% | Clear narrative thread, logical flow | Some disconnected sections | No coherent narrative |
| Completeness | 20% | Covers all major themes from sources | Misses some themes | Major gaps |
| Insight Quality | 15% | Novel synthesis across sources | Restates obvious points | No synthesis |
| Readability | 10% | Engaging, well-structured prose | Adequate but dry | Unreadable |

### Automated Evaluation Pipeline

```python
def evaluate_daily_book(book: Book, source_data: Dict) -> EvaluationResult:
    scores = {}
    
    # Deterministic gate: exact text span plus source record ID and URL
    scores["source_accuracy"] = verify_quotes(book.chapters, source_data)
    
    # Thematic coherence: LLM-as-judge for narrative flow
    scores["thematic_coherence"] = judge_coherence(book)
    
    # Completeness: check theme coverage
    scores["completeness"] = calculate_theme_coverage(book, source_data)
    
    # Insight quality: LLM-as-judge for synthesis
    scores["insight_quality"] = judge_insights(book, source_data)
    
    # Readability: automated metrics + LLM judge
    scores["readability"] = assess_readability(book)
    
    overall = weighted_average(scores, DIMENSION_WEIGHTS)
    
    return EvaluationResult(
        passed=overall >= 0.7,
        scores=scores,
        overall=overall,
        flagged_issues=identify_issues(scores)
    )
```

### Human Review Triggers

- Overall score < 0.7
- Source accuracy < 0.8
- Any fabricated quote detected
- New account added (first book needs review)
- Controversial topic detected

---

## Data Flow

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                              DAILY PIPELINE                                  │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 1. SCRAPE PHASE                                                              │
│    Scraper Agent → X API → File System (raw_data/{account}/{date}.json)     │
│    Context: Minimal (tool calls only)                                        │
│    Output: Raw tweet data persisted to file system                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 2. ANALYZE PHASE                                                             │
│    Analyzer Agent → File System → Memory Store                               │
│    Context: One account at a time                                            │
│    Output: Structured analysis per account + Knowledge Graph updates         │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 3. SYNTHESIZE PHASE                                                          │
│    Synthesizer Agent → Analysis Summaries → Book Outline                     │
│    Context: Summaries from all accounts (compacted)                          │
│    Output: Book outline with chapter structure                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 4. WRITE PHASE                                                               │
│    Writer Agent → Outline + Relevant Sources → Draft Chapters                │
│    Context: One chapter at a time (progressive disclosure)                   │
│    Output: Draft markdown chapters                                           │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 5. EDIT PHASE                                                                │
│    Editor Agent → Draft + Sources → Final Chapters                           │
│    Context: One chapter at a time                                            │
│    Output: Edited chapters with revision notes                               │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 6. EVALUATE PHASE                                                            │
│    Evaluation Pipeline → Final Book → Quality Report                         │
│    Output: Pass/fail with scores, flagged issues                             │
└─────────────────────────────────────────────────────────────────────────────┘
                                      │
                                      ▼
┌─────────────────────────────────────────────────────────────────────────────┐
│ 7. PUBLISH (if passed) or HUMAN REVIEW (if flagged)                          │
└─────────────────────────────────────────────────────────────────────────────┘
```

---

## Failure Modes and Mitigations

### Failure: Orchestrator Context Saturation
**Symptom**: Orchestrator accumulates phase outputs, degrading routing decisions.
**Mitigation**: Phase outputs stored in file system, Orchestrator receives only summaries. Implement checkpointing to persist state.

### Failure: X API Rate Limiting
**Symptom**: Scraper hits rate limits, incomplete data.
**Mitigation**: 
- Implement circuit breaker with exponential backoff
- Checkpoint partial scrapes for resume
- Schedule scraping across time windows

### Failure: Quote Hallucination
**Symptom**: Writer generates quotes not in source material.
**Mitigation**:
- Strict source attribution in writing prompt
- Editor verifies every quote against the referenced source record
- Evaluation fails altered quotes, unknown record IDs, or missing source URLs

### Failure: Source Provenance Loss
**Symptom**: A claim cannot be traced after a post changes or disappears.
**Mitigation**:
- Store provider responses as append-only raw artifacts
- Carry source record IDs through every derived artifact
- Never replace the capture used by an existing book

### Failure: Theme Drift
**Symptom**: Book themes diverge from actual source content.
**Mitigation**:
- Synthesizer receives grounded summaries only
- Writer tool includes source verification step
- Evaluation checks theme-source alignment

### Failure: Coordination Overhead
**Symptom**: Agent communication latency exceeds content value.
**Mitigation**:
- Batch phase outputs
- Use file system for inter-agent data (no context passing for large payloads)
- Parallelize where possible (Scraper can run per-account in parallel)

---

## Configuration

```yaml
# config.yaml
target_accounts:
  - handle: "@account1"
    priority: high
    themes_of_interest: ["AI", "startups"]
  - handle: "@account2"
    priority: medium
    themes_of_interest: ["regulation", "policy"]

schedule:
  scrape_time: "06:00"  # UTC
  publish_time: "08:00"
  timezone: "UTC"

book_settings:
  target_word_count: 5000
  min_chapters: 3
  max_chapters: 7
  style: "analytical"  # analytical | narrative | summary

quality_thresholds:
  min_overall_score: 0.7
  min_source_accuracy: 0.8
  require_human_review_below: 0.75

memory:
  retention_days: 90
  consolidation_frequency: "weekly"
  
context_limits:
  orchestrator: 50000
  scraper: 20000
  analyzer: 80000
  synthesizer: 100000
  writer: 80000
  editor: 60000
```

---

## Implementation Phases

### Phase 1: Core Pipeline (Week 1-2)
- Orchestrator with basic routing
- Scraper with the Xquik source adapter
- File system storage
- Basic Writer producing markdown output

### Phase 2: Analysis Layer (Week 3-4)
- Analyzer agent with theme extraction
- Synthesizer with cross-account patterns
- Book outline generation

### Phase 3: Memory System (Week 5-6)
- Temporal knowledge graph implementation
- Entity and relationship storage
- Temporal queries for historical context

### Phase 4: Quality Layer (Week 7-8)
- Editor agent
- Evaluation pipeline
- Human review interface

### Phase 5: Production Hardening (Week 9-10)
- Checkpoint/resume
- Circuit breakers
- Monitoring and alerting
- Consolidation jobs

---

## Technical Stack (Recommended)

| Component | Technology | Rationale |
|-----------|------------|-----------|
| Agent Framework | LangGraph | Graph-based state machines with explicit nodes/edges |
| Knowledge Graph | Neo4j or Memgraph | Native temporal queries, relationship traversal |
| Vector Store | Weaviate or Pinecone | Hybrid search (semantic + metadata filtering) |
| X Data | Provider-neutral `x_data_tool` with an Xquik adapter | Exact read operations, pagination, and normalized source records |
| Storage | PostgreSQL + S3 | Structured data + blob storage for content |
| Orchestration | Temporal.io | Durable workflows with checkpoint/resume |

---

## Open Questions

1. **Source Retention**: How long should raw captures remain available after a
   post changes, becomes private, or is deleted?

2. **Book Format**: Pure prose vs mixed media (including original tweet embeds)?

3. **Attribution Model**: How prominent should account attribution be? Full quotes with handles vs paraphrased insights?

4. **Monetization**: If books are sold, what are the IP implications of synthesizing public tweets?

5. **Human-in-the-Loop**: How much editorial control? Full review of every book vs exception-based review?

---

## References

- [Agent Skills for Context Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) - Context engineering patterns
- Multi-agent patterns skill - Supervisor architecture selection
- Memory systems skill - Temporal knowledge graph design
- Context optimization skill - Observation masking and compaction strategies
- Tool design skill - Consolidation principle for tools
- Evaluation skill - Multi-dimensional rubrics
- [Xquik adapter](./XQUIK-ADAPTER.md) - Concrete REST and MCP source boundary

Xquik is an independent third-party service. Not affiliated with X Corp.
"Twitter" and "X" are trademarks of X Corp.
