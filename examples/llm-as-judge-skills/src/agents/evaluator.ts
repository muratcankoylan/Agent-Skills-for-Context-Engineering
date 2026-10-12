import { openai } from '@ai-sdk/openai';
import { generateText } from 'ai';
import { checkBudget, config, recordUsage, withRetries } from '../config/index.js';
import {
  executeDirectScore,
  executePairwiseCompare,
  executeGenerateRubric,
  type DirectScoreInput,
  type PairwiseCompareInput,
  type GenerateRubricInput
} from '../tools/evaluation/index.js';

export interface EvaluatorAgentConfig {
  model?: string;
  temperature?: number;
  maxTokens?: number;
}

export class EvaluatorAgent {
  private model: string;
  private temperature: number;

  constructor(agentConfig?: EvaluatorAgentConfig) {
    this.model = agentConfig?.model || config.openai.model;
    this.temperature = agentConfig?.temperature || 0.3;
  }

  /**
   * Score a response against defined criteria
   */
  async score(input: DirectScoreInput) {
    return executeDirectScore(input);
  }

  /**
   * Compare two responses and pick the better one
   */
  async compare(input: PairwiseCompareInput) {
    return executePairwiseCompare(input);
  }

  /**
   * Generate a rubric for a criterion
   */
  async generateRubric(input: GenerateRubricInput) {
    return executeGenerateRubric(input);
  }

  /**
   * Full evaluation workflow: generate rubric, then score
   */
  async evaluateWithGeneratedRubric(
    response: string,
    prompt: string,
    criteria: Array<{ name: string; description: string; weight?: number }>
  ) {
    // Generate rubrics for each criterion
    const rubrics = await Promise.all(
      criteria.map(c => this.generateRubric({
        criterionName: c.name,
        criterionDescription: c.description,
        scale: '1-5',
        includeExamples: false,
        strictness: 'balanced'
      }))
    );

    // Build combined rubric
    const levelDescriptions: Record<string, string> = {};
    rubrics[0]?.levels?.forEach(level => {
      levelDescriptions[String(level.score)] = level.description;
    });

    // Score using generated rubric
    return this.score({
      response,
      prompt,
      criteria: criteria.map((c) => ({
        name: c.name,
        description: c.description,
        weight: c.weight || 1
      })),
      rubric: {
        scale: '1-5',
        levelDescriptions
      }
    });
  }

  /**
   * Chat-based evaluation for custom queries
   */
  async chat(userMessage: string) {
    const budgetCheck = checkBudget('EvaluatorAgent.chat');
    if (!budgetCheck.ok) {
      return {
        text: `Evaluation blocked by budget guard: ${budgetCheck.reason}`,
        usage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 }
      };
    }

    if (config.budgets.dryRun) {
      recordUsage();
      return {
        text: '[dry-run] EvaluatorAgent.chat returned a stub because JUDGE_DRY_RUN is enabled.',
        usage: { promptTokens: 0, completionTokens: 0, totalTokens: 0 }
      };
    }

    const result = await withRetries('EvaluatorAgent.chat', () => generateText({
      model: openai(this.model),
      system: `You are an expert evaluator of AI-generated content.
Your role is to assess quality, identify issues, and provide actionable feedback.
Be objective, specific, and constructive in your evaluations.`,
      prompt: userMessage,
      temperature: this.temperature
    }));

    recordUsage(result.usage);

    return {
      text: result.text,
      usage: result.usage
    };
  }
}

// Default instance
export const evaluatorAgent = new EvaluatorAgent();

