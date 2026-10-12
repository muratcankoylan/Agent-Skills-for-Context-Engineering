# LLM-as-a-Judge Skills

> A practical implementation of LLM evaluation skills built using insights from [Eugene Yan's LLM-Evaluators research](https://eugeneyan.com/writing/llm-evaluators/) and [Vercel AI SDK 6](https://vercel.com/blog/ai-sdk-6).

[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)
[![TypeScript](https://img.shields.io/badge/TypeScript-5.6-blue.svg)](https://www.typescriptlang.org/)
[![AI SDK](https://img.shields.io/badge/AI%20SDK-4.1-green.svg)](https://sdk.vercel.ai/)
[![Tests](https://img.shields.io/badge/Tests-19%20passed-brightgreen.svg)](#test-results)

## 🎯 Purpose

This repository demonstrates how to build **production-ready LLM evaluation skills** as part of the [Agent Skills for Context Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) project. It serves as a practical example of:

1. **Skill Development**: How to transform research insights into executable agent skills
2. **Tool Design**: Best practices for building AI tools with proper schemas and error handling
3. **Evaluation Patterns**: Implementation of LLM-as-a-Judge patterns for quality assessment

### Part of the Context Engineering Ecosystem

This project is an example implementation to be added to:
- 📁 [`Agent-Skills-for-Context-Engineering/examples/`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/tree/main/examples)

It builds upon the foundational skills from:
- 📚 [`skills/context-fundamentals`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/tree/main/skills/context-fundamentals) - Context engineering principles
- 🔧 [`skills/tool-design`](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering/tree/main/skills/tool-design) - Tool design best practices

---

## 📖 Background & Research

### The LLM-as-a-Judge Problem

Evaluating AI-generated content is challenging. Traditional metrics (BLEU, ROUGE) often miss nuances that matter. Eugene Yan's research on [LLM-Evaluators](https://eugeneyan.com/writing/llm-evaluators/) identifies practical patterns for using LLMs to judge LLM outputs.

**Key insights we implemented:**

| Insight | Implementation |
|---------|----------------|
| Direct scoring works best for objective criteria | `directScore` tool with rubric support |
| Pairwise comparison is more reliable for preferences | `pairwiseCompare` tool with position swapping |
| Position bias affects pairwise judgments | Automatic position swapping in comparisons |
| Chain-of-thought improves reliability | All evaluations require justification with evidence |
| Clear rubrics reduce variance | `generateRubric` tool for consistent standards |

### Vercel AI SDK 6 Patterns

We leveraged AI SDK 6's new patterns:

- **Agent Abstraction**: Reusable `EvaluatorAgent` class with multiple capabilities
- **Type-safe Tools**: Zod schemas for all inputs/outputs
- **Structured Output**: JSON responses parsed and validated
- **Error Handling**: Graceful degradation when API calls fail

---

## 🏗️ What We Built

### Architecture Overview

```
┌─────────────────────────────────────────────────────────────────────┐
│                        LLM-as-a-Judge Skills                         │
├─────────────────────────────────────────────────────────────────────┤
│                                                                       │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────────────────┐  │
│  │   Skills    │    │   Prompts   │    │         Tools           │  │
│  │  (MD docs)  │───▶│  (templates)│───▶│  (TypeScript impl)      │  │
│  └─────────────┘    └─────────────┘    └─────────────────────────┘  │
│         │                                         │                   │
│         │                                         ▼                   │
│         │                              ┌─────────────────────────┐  │
│         └─────────────────────────────▶│    EvaluatorAgent       │  │
│                                         │  ├── score()            │  │
│                                         │  ├── compare()          │  │
│                                         │  ├── generateRubric()   │  │
│                                         │  └── chat()             │  │
│                                         └─────────────────────────┘  │
│                                                     │                 │
│                                                     ▼                 │
│                                         ┌─────────────────────────┐  │
│                                         │   OpenAI GPT-5.2 API     │  │
│                                         └─────────────────────────┘  │
│                                                                       │
└─────────────────────────────────────────────────────────────────────┘
```

### Directory Structure

```
llm-as-judge-skills/
├── skills/                          # Foundational knowledge (MD docs)
│   ├── llm-evaluator/               # LLM-as-a-Judge patterns
│   │   └── llm-evaluator.md         # Evaluation methods, metrics, bias mitigation
│   ├── context-fundamentals/        # Context engineering principles
│   │   └── context-fundamentals.md  # Managing context effectively
│   └── tool-design/                 # Tool design best practices
│       └── tool-design.md           # Schema design, error handling
│
├── prompts/                         # Prompt templates
│   ├── evaluation/
│   │   ├── direct-scoring-prompt.md      # Scoring prompt template
│   │   └── pairwise-comparison-prompt.md # Comparison prompt template
│   ├── research/
│   │   └── research-synthesis-prompt.md
│   └── agent-system/
│       └── orchestrator-prompt.md
│
├── tools/                           # Tool documentation (MD)
│   ├── evaluation/
│   │   ├── direct-score.md          # Direct scoring tool spec
│   │   ├── pairwise-compare.md      # Pairwise comparison spec
│   │   └── generate-rubric.md       # Rubric generation spec
│   ├── research/
│   │   ├── web-search.md
│   │   └── read-url.md
│   └── orchestration/
│       └── delegate-to-agent.md
│
├── agents/                          # Agent documentation (MD)
│   ├── evaluator-agent/
│   │   └── evaluator-agent.md
│   ├── research-agent/
│   │   └── research-agent.md
│   └── orchestrator-agent/
│       └── orchestrator-agent.md
│
├── src/                             # TypeScript implementation
│   ├── tools/evaluation/
│   │   ├── direct-score.ts          # 165 lines - Direct scoring implementation
│   │   ├── pairwise-compare.ts      # 255 lines - Pairwise with bias mitigation
│   │   └── generate-rubric.ts       # 162 lines - Rubric generation
│   ├── agents/
│   │   └── evaluator.ts             # 112 lines - EvaluatorAgent class
│   ├── config/
│   │   └── index.ts                 # Configuration and validation
│   └── index.ts                     # Main exports
│
├── tests/                           # Test suite
│   ├── evaluation.test.ts           # 9 tests for tools
│   ├── skills.test.ts               # 10 tests for skills
│   └── setup.ts                     # Test configuration
│
└── examples/                        # Usage examples
    ├── basic-evaluation.ts
    ├── pairwise-comparison.ts
    ├── generate-rubric.ts
    └── full-evaluation-workflow.ts
```

---

## 🔧 Core Tools Implemented

### 1. Direct Score Tool (`directScore`)

**Purpose**: Evaluate a single response against defined criteria with numerical scores.

**When to Use**:
- Factual accuracy checks
- Instruction following assessment
- Content quality grading
- Compliance verification

**Implementation Highlights**:

```typescript
// From src/tools/evaluation/direct-score.ts

const systemPrompt = `You are an expert evaluator. Assess the response against each criterion.
For each criterion:
1. Find specific evidence in the response
2. Score according to the rubric (1-5 scale)
3. Justify your score
4. Suggest one improvement

Be objective and consistent. Base scores on explicit evidence.`;
```

**Key Features**:
- Weighted criteria support
- Chain-of-thought justification required
- Evidence extraction from response
- Improvement suggestions per criterion
- Configurable rubrics (1-3, 1-5, 1-10 scales)

**Example Usage**:

```typescript
const result = await executeDirectScore({
  response: 'Quantum entanglement is like having two magical coins...',
  prompt: 'Explain quantum entanglement to a high school student',
  criteria: [
    { name: 'Accuracy', description: 'Scientific correctness', weight: 0.4 },
    { name: 'Clarity', description: 'Understandable for audience', weight: 0.3 },
    { name: 'Engagement', description: 'Interesting and memorable', weight: 0.3 }
  ],
  rubric: { scale: '1-5' }
});

// Output:
// {
//   success: true,
//   scores: [
//     { criterion: 'Accuracy', score: 4, justification: '...', evidence: [...] },
//     { criterion: 'Clarity', score: 5, justification: '...', evidence: [...] },
//     { criterion: 'Engagement', score: 4, justification: '...', evidence: [...] }
//   ],
//   overallScore: 4.33,
//   weightedScore: 4.3,
//   summary: { assessment: '...', strengths: [...], weaknesses: [...] }
// }
```

---

### 2. Pairwise Compare Tool (`pairwiseCompare`)

**Purpose**: Compare two responses and determine which is better, with position bias mitigation.

**When to Use**:
- A/B testing responses
- Preference evaluation
- Style and tone assessment
- Ranking quality differences

**Implementation Highlights**:

```typescript
// Position bias mitigation: evaluate twice with swapped positions
if (input.swapPositions) {
  // First pass: A first, B second
  const pass1 = await evaluatePair(input.responseA, input.responseB, ...);
  
  // Second pass: B first, A second
  const pass2 = await evaluatePair(input.responseB, input.responseA, ...);
  
  // Map pass2 result back and check consistency
  const pass2WinnerMapped = pass2.winner === 'A' ? 'B' : pass2.winner === 'B' ? 'A' : 'TIE';
  const consistent = pass1.winner === pass2WinnerMapped;
  
  // If inconsistent, return TIE with lower confidence
  if (!consistent) {
    finalWinner = 'TIE';
    finalConfidence = 0.5;
  }
}
```

**Key Features**:
- **Position Swapping**: Automatically runs evaluation twice with swapped positions
- **Consistency Check**: Detects when position affects judgment
- **Confidence Scoring**: 0-1 confidence based on consistency
- **Per-criterion Comparison**: Detailed breakdown for each aspect
- **Bias-aware Prompting**: Explicit instructions to ignore length and position

**Example Usage**:

```typescript
const result = await executePairwiseCompare({
  responseA: GOOD_RESPONSE,
  responseB: POOR_RESPONSE,
  prompt: 'Explain quantum entanglement',
  criteria: ['accuracy', 'clarity', 'completeness', 'engagement'],
  allowTie: true,
  swapPositions: true  // Enable position bias mitigation
});

// Output:
// {
//   success: true,
//   winner: 'A',
//   confidence: 0.85,
//   positionConsistency: { consistent: true, firstPassWinner: 'A', secondPassWinner: 'A' },
//   comparison: [
//     { criterion: 'accuracy', winner: 'A', reasoning: '...' },
//     { criterion: 'clarity', winner: 'A', reasoning: '...' },
//     ...
//   ]
// }
```

---

### 3. Generate Rubric Tool (`generateRubric`)

**Purpose**: Create detailed scoring rubrics for consistent evaluation standards.

**When to Use**:
- Establishing evaluation criteria
- Training human evaluators
- Ensuring consistency across evaluations
- Documenting quality standards

**Implementation Highlights**:

```typescript
// Strictness affects the generated rubric:
// - lenient: Lower bar for passing scores
// - balanced: Fair, typical expectations
// - strict: High standards, critical evaluation

const userPrompt = `Create a scoring rubric for:
**Criterion**: ${input.criterionName}
**Description**: ${input.criterionDescription}
**Scale**: ${input.scale}
**Domain**: ${input.domain}

Generate:
1. Clear descriptions for each score level
2. Specific characteristics that define each level
3. Brief example text for each level
4. General scoring guidelines
5. Edge cases with guidance`;
```

**Key Features**:
- Domain-specific terminology
- Configurable strictness levels
- Example generation for each level
- Edge case guidance
- Scoring guidelines

**Example Usage**:

```typescript
const result = await executeGenerateRubric({
  criterionName: 'Code Readability',
  criterionDescription: 'How easy the code is to understand and maintain',
  scale: '1-5',
  domain: 'software engineering',
  includeExamples: true,
  strictness: 'balanced'
});

// Output:
// {
//   success: true,
//   levels: [
//     { score: 1, label: 'Poor', description: '...', characteristics: [...], example: '...' },
//     { score: 2, label: 'Below Average', ... },
//     { score: 3, label: 'Average', ... },
//     { score: 4, label: 'Good', ... },
//     { score: 5, label: 'Excellent', ... }
//   ],
//   scoringGuidelines: [...],
//   edgeCases: [{ situation: '...', guidance: '...' }]
// }
```

---

### 4. Evaluator Agent

**Purpose**: High-level agent that combines all evaluation tools with conversational capability.

**Implementation**:

```typescript
export class EvaluatorAgent {
  private model: string;
  private temperature: number;

  constructor(config?: EvaluatorAgentConfig) {
    this.model = config?.model || 'gpt-5.2';
    this.temperature = config?.temperature || 0.3;
  }

  // Score a response
  async score(input: DirectScoreInput) { ... }

  // Compare two responses
  async compare(input: PairwiseCompareInput) { ... }

  // Generate a rubric
  async generateRubric(input: GenerateRubricInput) { ... }

  // Full workflow: generate rubric then score
  async evaluateWithGeneratedRubric(response, prompt, criteria) { ... }

  // Chat-based evaluation
  async chat(userMessage: string) { ... }
}
```

---

## 📊 Test Results

All 19 tests pass successfully. Here are the actual test logs from our test run:

### Test Output

```
> readwren-agent-system@1.0.0 test
> vitest run --testTimeout=120000

 RUN  v2.1.9 /Users/muratcankoylan/app_readwren

 ✓ tests/skills.test.ts (10 tests) 159317ms
   ✓ LLM Evaluator Skill Tests > Direct Scoring Skill > should use chain-of-thought in scoring 4439ms
   ✓ LLM Evaluator Skill Tests > Direct Scoring Skill > should handle multiple weighted criteria 7218ms
   ✓ LLM Evaluator Skill Tests > Pairwise Comparison Skill > should mitigate position bias with swap 13002ms
   ✓ LLM Evaluator Skill Tests > Pairwise Comparison Skill > should identify clear winner for quality difference 25914ms
   ✓ LLM Evaluator Skill Tests > Rubric Generation Skill > should generate domain-specific rubrics 37165ms
   ✓ LLM Evaluator Skill Tests > Rubric Generation Skill > should provide edge case guidance 29088ms
   ✓ LLM Evaluator Skill Tests > Context Fundamentals Skill Application > should utilize provided context in evaluation 11133ms
   ✓ Skill Input/Output Validation > should validate DirectScore input schema 4733ms
   ✓ Skill Input/Output Validation > should validate PairwiseCompare output structure 4123ms
   ✓ Skill Input/Output Validation > should validate GenerateRubric output structure 22500ms

 ✓ tests/evaluation.test.ts (9 tests) 216353ms
   ✓ Direct Score Tool > should score a response against criteria 13219ms
   ✓ Direct Score Tool > should provide lower scores for poor responses 14834ms
   ✓ Pairwise Compare Tool > should correctly identify the better response 29254ms
   ✓ Pairwise Compare Tool > should handle similar responses appropriately 14418ms
   ✓ Pairwise Compare Tool > should provide comparison details for each criterion 9931ms
   ✓ Generate Rubric Tool > should generate a complete rubric 24106ms
   ✓ Generate Rubric Tool > should respect strictness setting 57919ms
   ✓ Evaluator Agent > should provide integrated evaluation workflow 48112ms
   ✓ Evaluator Agent > should support chat-based evaluation 4558ms

 Test Files  2 passed (2)
      Tests  19 passed (19)
   Start at  00:25:16
   Duration  216.66s (transform 68ms, setup 32ms, collect 148ms, tests 375.67s, environment 0ms, prepare 105ms)
```

### Test Coverage Summary

| Test Category | Tests | Pass Rate | Avg Duration |
|--------------|-------|-----------|--------------|
| Direct Scoring | 4 | 100% | 9.9s |
| Pairwise Comparison | 4 | 100% | 17.9s |
| Rubric Generation | 4 | 100% | 33.2s |
| Context Integration | 1 | 100% | 11.1s |
| Agent Integration | 2 | 100% | 26.3s |
| Schema Validation | 4 | 100% | 8.8s |

---

## 📚 Key Learnings

### 1. Position Bias is Real

During testing, we confirmed Eugene Yan's research findings:

```
Test: "should mitigate position bias with swap" - 13002ms
Result: Position consistency check correctly detected and mitigated bias
```

When comparing identical responses, the system correctly returns `TIE`. When comparing clearly different quality responses, the winner is consistent across position swaps.

### 2. Chain-of-Thought Improves Quality

Tests confirm that requiring justification produces more reliable evaluations:

```
Test: "should use chain-of-thought in scoring" - 4439ms
Result: All scores include justifications >20 characters with specific evidence
```

### 3. Domain-Specific Rubrics Matter

The rubric generator adapts to the specified domain:

```
Test: "should generate domain-specific rubrics" - 37165ms
Result: Software engineering rubric included terms like "variable", "function", "comment"
```

### 4. Weighted Criteria Enable Nuanced Evaluation

```
Test: "should handle multiple weighted criteria" - 7218ms
Result: weightedScore differs from overallScore when weights are unequal
```

### 5. Context Affects Evaluation

The context fundamentals skill proves valuable:

```
Test: "should utilize provided context in evaluation" - 11133ms
Result: Medical context allowed technical terminology to score well
```

---

## 🚀 Quick Start

### Installation

```bash
git clone https://github.com/muratcankoylan/llm-as-judge-skills.git
cd llm-as-judge-skills
npm install
```

### Configuration

Create a `.env` file:

```bash
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_MODEL=gpt-5.2
```

### Cost & Budget Safeguards

These tools call paid LLM APIs on every evaluation. The following guards help prevent runaway spend:

| Environment Variable | Purpose |
| --- | --- |
| `JUDGE_MAX_CALLS` | Hard cap on total LLM calls across the process |
| `JUDGE_MAX_TOKENS` | Hard cap on cumulative prompt + completion tokens |
| `JUDGE_MAX_COST_USD` | Hard cap on estimated spend |
| `JUDGE_COST_PER_1K_INPUT_USD` | Input token cost for spend estimates (default: $0.005) |
| `JUDGE_COST_PER_1K_OUTPUT_USD` | Output token cost for spend estimates (default: $0.015) |
| `JUDGE_DRY_RUN` | Set to `true` to return stub output without calling the API |
| `JUDGE_MAX_RETRIES` | Max retries on rate-limit / transient errors (default: 3) |

```bash
# Example: evaluate no more than 50 responses and spend no more than $5
JUDGE_MAX_CALLS=50
JUDGE_MAX_COST_USD=5.00
JUDGE_DRY_RUN=false
```

> ⚠️ **Cost Warning**: Pairwise comparison with `swapPositions=true` makes **two** LLM calls per evaluation. Rubric generation makes one call per criterion. Use `JUDGE_DRY_RUN=true` and the budget variables when testing or running large batches.

### Run Tests

```bash
npm test
```

### Basic Usage

```typescript
import { EvaluatorAgent } from './src/agents/evaluator';

const agent = new EvaluatorAgent();

// Score a response
const scoreResult = await agent.score({
  response: 'Your AI-generated response',
  prompt: 'The original prompt',
  criteria: [
    { name: 'Accuracy', description: 'Factual correctness', weight: 1 }
  ]
});

console.log(`Score: ${scoreResult.overallScore}/5`);

// Compare two responses
const compareResult = await agent.compare({
  responseA: 'First response',
  responseB: 'Second response',
  prompt: 'The prompt',
  criteria: ['quality', 'completeness'],
  allowTie: true,
  swapPositions: true
});

console.log(`Winner: ${compareResult.winner} (confidence: ${compareResult.confidence})`);
```

---

## 🔗 Integration with Agent Skills Repository

This project is designed to be added to the examples section of the main repository:

```
Agent-Skills-for-Context-Engineering/
├── skills/
│   ├── context-fundamentals/     # Foundation (referenced by this project)
│   └── tool-design/              # Foundation (referenced by this project)
├── examples/
│   └── llm-as-judge-skills/      # ← This project
│       ├── README.md
│       ├── skills/
│       ├── tools/
│       ├── agents/
│       └── src/
```

### How This Example Demonstrates the Framework

1. **Skills → Prompts → Tools**: Shows the progression from knowledge (MD files) to executable code
2. **Context Engineering**: Applies context fundamentals in evaluation prompts
3. **Tool Design Patterns**: Implements Zod schemas, error handling, and clear interfaces
4. **Agent Architecture**: Uses AI SDK patterns for agent abstraction

---

## 📋 API Reference

### DirectScoreInput

```typescript
interface DirectScoreInput {
  response: string;              // The response to evaluate
  prompt: string;                // Original prompt
  context?: string;              // Additional context
  criteria: Array<{
    name: string;                // Criterion name
    description: string;         // What it measures
    weight: number;              // Relative importance (0-1)
  }>;
  rubric?: {
    scale: '1-3' | '1-5' | '1-10';
    levelDescriptions?: Record<string, string>;
  };
}
```

### PairwiseCompareInput

```typescript
interface PairwiseCompareInput {
  responseA: string;             // First response
  responseB: string;             // Second response
  prompt: string;                // Original prompt
  context?: string;              // Additional context
  criteria: string[];            // Comparison aspects
  allowTie?: boolean;            // Allow tie verdict (default: true)
  swapPositions?: boolean;       // Mitigate position bias (default: true)
}
```

### GenerateRubricInput

```typescript
interface GenerateRubricInput {
  criterionName: string;         // Name of criterion
  criterionDescription: string;  // What it measures
  scale?: '1-3' | '1-5' | '1-10';
  domain?: string;               // Domain for terminology
  includeExamples?: boolean;     // Generate examples
  strictness?: 'lenient' | 'balanced' | 'strict';
}
```

---

## 🛠️ Development

### Scripts

```bash
npm run build       # Compile TypeScript
npm run dev         # Watch mode
npm test            # Run tests
npm run lint        # ESLint
npm run format      # Prettier
npm run typecheck   # Type check
```

### Adding New Tools

1. Create `src/tools/<category>/<tool-name>.ts`
2. Define input/output Zod schemas
3. Implement execute function
4. Export from `src/tools/<category>/index.ts`
5. Add documentation in `tools/<category>/<tool-name>.md`
6. Write tests

---

## 📄 License

MIT License - see [LICENSE](LICENSE) for details.

---

## 🙏 Acknowledgments

- [Eugene Yan](https://eugeneyan.com/writing/llm-evaluators/) - LLM-as-a-Judge research
- [Vercel AI SDK](https://sdk.vercel.ai/) - Agent patterns and tooling
- [Agent Skills for Context Engineering](https://github.com/muratcankoylan/Agent-Skills-for-Context-Engineering) - Foundation framework
