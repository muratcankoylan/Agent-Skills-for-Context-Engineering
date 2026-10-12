---
name: evaluator-agent
description: Assesses quality of LLM-generated responses using direct scoring and pairwise comparison
---

# Evaluator Agent

## Purpose

The Evaluator Agent assesses the quality of LLM-generated responses using configurable evaluation criteria. It implements the LLM-as-a-Judge pattern with support for both direct scoring and pairwise comparison.

## Agent Definition

```typescript
import { ToolLoopAgent } from "ai";
import { anthropic } from "@ai-sdk/anthropic";
import { evaluationTools } from "../tools";

export const evaluatorAgent = new ToolLoopAgent({
  name: "evaluator",
  model: anthropic("claude-sonnet-4-20250514"),
  instructions: `You are an expert evaluator of LLM-generated content.

Your role is to:
1. Assess response quality against specific criteria
2. Provide structured scores with justifications
3. Identify specific issues and strengths
4. Compare responses when asked for pairwise evaluation

Evaluation Guidelines:
- Be objective and consistent in your assessments
- Ground evaluations in specific evidence from the response
- Consider the context and requirements of the original task
- Avoid position bias - evaluate content not placement
- Do not favor verbose responses unless verbosity adds value

Always provide:
- Numerical scores for each criterion
- Specific examples supporting your assessment
- Actionable feedback for improvement`,
  
  tools: {
    directScore: evaluationTools.directScore,
    pairwiseCompare: evaluationTools.pairwiseCompare,
    extractCriteria: evaluationTools.extractCriteria,
    generateRubric: evaluationTools.generateRubric
  }
});
```

## Capabilities

### Direct Scoring
Evaluate a single response against defined criteria and rubric.

**Input:**
- Response to evaluate
- Original prompt/context
- Evaluation criteria
- Scoring rubric

**Output:**
- Score per criterion (1-5)
- Overall score
- Detailed justification
- Identified issues and strengths

### Pairwise Comparison
Compare two responses and select the better one.

**Input:**
- Response A
- Response B
- Original prompt/context
- Comparison criteria

**Output:**
- Winner selection (A, B, or Tie)
- Confidence score
- Comparative analysis
- Specific differentiators

### Criteria Extraction
Automatically extract evaluation criteria from a task description.

**Input:**
- Task description
- Domain context
- Quality expectations

**Output:**
- List of relevant criteria
- Criterion descriptions
- Suggested weights

### Rubric Generation
Generate a scoring rubric for specific criteria.

**Input:**
- Criterion name
- Quality dimensions
- Scale (default 1-5)

**Output:**
- Rubric with score descriptions
- Examples for each level
- Edge case guidance

## Configuration

```typescript
interface EvaluatorConfig {
  // Scoring configuration
  scoringMode: "direct" | "pairwise";
  useChainOfThought: boolean;
  nShotExamples: number;
  
  // Bias mitigation
  swapPositionsForPairwise: boolean;
  normalizeForLength: boolean;
  
  // Output configuration
  includeJustification: boolean;
  includeExamples: boolean;
  outputFormat: "structured" | "prose";
}

const defaultConfig: EvaluatorConfig = {
  scoringMode: "direct",
  useChainOfThought: true,
  nShotExamples: 2,
  swapPositionsForPairwise: true,
  normalizeForLength: false,
  includeJustification: true,
  includeExamples: true,
  outputFormat: "structured"
};
```

## Usage Example

```typescript
import { evaluatorAgent } from "./agents/evaluator-agent";

// Direct scoring
const evaluation = await evaluatorAgent.generate({
  prompt: `Evaluate the following response:

Original Question: "Explain quantum entanglement to a high school student"

Response: "${generatedResponse}"

Criteria:
1. Accuracy - Scientific correctness
2. Clarity - Understandable for target audience
3. Engagement - Interesting and memorable
4. Completeness - Covers key concepts

Provide scores and detailed feedback.`
});

// Pairwise comparison
const comparison = await evaluatorAgent.generate({
  prompt: `Compare these two responses to the same question.

Question: "What are the benefits of exercise?"

Response A: "${responseA}"

Response B: "${responseB}"

Which response is better? Explain your reasoning.`
});
```

## Integration Points

- **Content Generation Pipeline**: Evaluate outputs before delivery
- **Model Comparison**: Compare responses from different models
- **Quality Monitoring**: Track response quality over time
- **Fine-tuning Data**: Generate preference data for RLHF

