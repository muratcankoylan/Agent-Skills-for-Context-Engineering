---
name: comprehensive-research-agent
description: "Ensure thorough validation, error recovery, and transparent reasoning in research tasks with multiple tool calls"
---

# Comprehensive Research Agent Best Practices

This skill addresses common failures in multi-step research tasks: unhandled tool errors, missing validation, opaque reasoning, and premature conclusions. It provides structured protocols for source validation, error recovery, and thinking transparency that significantly improves research quality and reliability.

## When to Activate

- Task involves web research with search, read_url, or fetch operations
- Task requires gathering information from multiple sources
- Task has explicit requirements for completeness or verification
- Task includes file operations that need validation (save, write, read)
- Any research or information-gathering workflow with 3+ tool interactions

## Core Concepts

- Validation Checkpoints: Explicit verification steps at phase transitions to confirm tool outputs, source relevance, and information completeness before proceeding
- Error Recovery Protocols: Mandatory acknowledgment and handling of tool failures with fallback strategies rather than silent continuation
- Source Traceability: Maintaining clear tracking of which sources were actually retrieved vs. referenced from prior knowledge to prevent hallucination
- Substantive Thinking Blocks: Detailed reasoning traces that document insights, connections, gaps, and decision rationale at each step
- Cross-Source Validation: Verifying key claims against multiple sources and explicitly noting consensus, contradictions, and information gaps

## Patterns to Avoid

- *Silent Tool Failure**: A tool call returns an error (404, timeout, invalid URL) but the agent proceeds without acknowledging it, potentially missing critical information. Always log failures and attempt recovery or document the gap.
- *Vague Completion Claims**: Agent declares 'I have enough information' or 'research is comprehensive' without specifying what was learned, what sources support claims, or what gaps remain. Replace with specific summaries of coverage.
- *Unvalidated Source Selection**: Agent reads URLs from search results without evaluating relevance, credibility, or recency first. This wastes tool calls on low-quality sources. Always rank and prioritize sources before deep reading.
- *Generic Thinking Blocks**: Thinking contains only next-action descriptions ('Now I will search for X') without analysis of what was learned, how it connects to the goal, or what questions remain. Thinking should be substantive and reflective.
- *Verification Method Error**: Using list_directory to verify file creation can produce false negatives due to caching. Always use read_file for actual content verification.
- *Citation Without Retrieval**: Citing sources (URLs, paper titles) in the final report that were never successfully fetched or read. Track sources explicitly and prohibit citing unretrieved content.
- *Redundant Tool Calls**: Making overlapping searches or reading sources without tracking what has already been obtained. Maintain a 'found resources' tracker to avoid duplication.

## Recommended Practices

- *Implement Pre-Reading Source Evaluation**: Before reading URLs, rank search results by relevance, credibility, recency, and authority. Document selection rationale in thinking blocks.
- *Use Structured Thinking Blocks**: Each thinking block must include: (a) what was learned from the source/action, (b) how it connects to the research goal, (c) any contradictions/gaps identified, (d) strategic decisions made. Avoid generic next-action statements.
- *Add Mandatory Error Acknowledgment**: When any tool fails, the next thinking block must explicitly address it: note the failure type, propose a recovery strategy (retry, alternative source, or documented gap), and explain the chosen approach.
- *Create Pre-Completion Validation Checklist**: Before declaring research complete, verify: all required sections have specific evidence, all sources were successfully retrieved, key claims are cross-validated, and gaps are documented.
- *Implement Cross-Source Validation**: After gathering information from multiple sources, explicitly compare findings. Note where sources agree, where they contradict, and what remains unverified. Use this to assess overall confidence.
- *Maintain Source Tracking Table**: Create a simple table in thinking showing which URLs were fetched, which failed, and which were used for specific claims. Never cite unretrieved sources.
- *Use Read_File for Verification**: When confirming file writes, use read_file to verify actual content rather than list_directory, which can have caching issues causing false negatives.
- *Add Explicit Validation Phase**: After reading sources, write a brief synthesis that confirms usefulness, notes relevance to research goals, and identifies remaining gaps before proceeding to the next phase.

## Guidelines

1. After each tool call, explicitly check for errors in the response and acknowledge failures in the next thinking block with recovery strategy
2. Before reading URLs, rank sources by relevance/credibility and document selection rationale - never read results without evaluation
3. Thinking blocks must be 3-5+ sentences minimum and include: what was learned, connections to goal, gaps/contradictions, and next steps
4. Create a pre-completion checklist verifying: all requirements covered, sources retrieved, claims validated, gaps documented
5. Maintain source tracking - only cite URLs that were successfully fetched; prohibit citing unretrieved sources
6. When writing final reports, include 'Limitations & Gaps' section documenting what was attempted but failed or what remains unverified
7. Use read_file (not list_directory) to verify file content after save operations
8. Cross-validate key claims across at least 2 sources when possible; explicitly note consensus or contradictions
9. Track gathered information to avoid redundant searches - implement 'found resources' tracker for multi-phase research
10. Replace vague 'comprehensive' statements with specific summaries: 'Covered X sources on Y topic; missing Z aspects'

## Examples

- **Before (Anti-Pattern)**: 'I searched for context engineering and found several results. Now I'll read some URLs and then write the report. I have enough information to proceed.'

**After (Pattern)**: 'Search returned 15 results on context engineering. Evaluating relevance: Liu et al. (2024) appears most authoritative on 'lost in the middle' phenomenon; Anthropic documentation likely has current context window specs; Patel (2023) covers RAG best practices. Ranking these as top 3 priorities. Reading top result first. If the primary source fails (URL error), will try backup search for correct documentation URL and note the gap in final report.'
- **Before (Anti-Pattern)**: Tool returns 404 error for Anthropic context windows URL. Agent continues without acknowledgment. Later cites 'Claude has 200K context window' without showing source. Final report cites Google Research paper that was never fetched.

**After (Pattern)**: Tool returned 404 for Anthropic URL. Thinking: 'Primary source failed. Fallback: search for alternative Anthropic documentation URL or find archived version. If unavailable, note context window data from secondary sources only and add disclaimer about verification status.' Then: 'Cross-validated Claude context window: Anthropic blog (successfully read) and two developer documentation sources agree on 200K. Confident in this claim.' Source tracking table shows: Anthropic URL (failed, backup used), Blog (success), Dev docs (success).

---

## Score Expectations

Complex research tasks with multiple tools (6+) and multi-step reasoning chains typically achieve scores in the **65-75 range**. This is not a limitation of the prompt but reflects:

- Inherent variability in tool outputs affecting reasoning paths
- Multiple valid approaches leading to different intermediate scores
- Stochastic nature of long-horizon agent execution

**Focus on relative improvement and pattern elimination** rather than absolute scores. A 5-10% improvement from optimization is significant for complex tasks.

---

## Skill Metadata

**Generated**: 2026-01-11
**Source**: Reasoning Trace Optimizer
**Optimization Iterations**: 10
**Best Score Achieved**: 72/100 (iteration 4)
**Final Score**: 70.0/100
**Score Improvement**: 67.6 → 70.0 (+3.6%)
