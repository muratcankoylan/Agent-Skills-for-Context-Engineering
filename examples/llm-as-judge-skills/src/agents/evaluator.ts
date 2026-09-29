import { JudgeRuntime, requireJudgeRuntime } from '../runtime/judge-runtime.js';
import { 
  executeDirectScore, 
  executePairwiseCompare, 
  executeGenerateRubric,
  DirectScoreInputSchema,
  type DirectScoreInput,
  type PairwiseCompareInput,
  type GenerateRubricInput
} from '../tools/evaluation/index.js';

export interface EvaluatorAgentConfig {
  runtime?: JudgeRuntime;
  temperature?: number;
}

export class EvaluatorAgent {
  private runtime?: JudgeRuntime;
  private temperature: number;

  constructor(agentConfig?: EvaluatorAgentConfig) {
    this.runtime = agentConfig?.runtime;
    this.temperature = agentConfig?.temperature ?? 0.3;
  }

  /**
   * Score a response against defined criteria
   */
  async score(input: DirectScoreInput) {
    return executeDirectScore(input, this.runtime);
  }

  /**
   * Compare two responses and pick the better one
   */
  async compare(input: PairwiseCompareInput) {
    return executePairwiseCompare(input, this.runtime);
  }

  /**
   * Generate a rubric for a criterion
   */
  async generateRubric(input: GenerateRubricInput) {
    return executeGenerateRubric(input, this.runtime);
  }

  /**
   * Full evaluation workflow: generate rubric, then score
   */
  async evaluateWithGeneratedRubric(
    response: string,
    prompt: string,
    criteria: Array<{ name: string; description: string; weight?: number }>
  ) {
    criteria = DirectScoreInputSchema.parse({
      response, prompt, criteria: criteria.map(c => ({ ...c, weight: c.weight ?? 1 }))
    }).criteria;
    if (!criteria.length || new Set(criteria.map(c => c.name)).size !== criteria.length) {
      throw new Error('Criteria must be non-empty and unique.');
    }
    if (!criteria.some(c => (c.weight ?? 1) > 0)) throw new Error('Criteria must have positive total weight.');
    // Sequential work provides backpressure and stops before downstream spend
    // when any required rubric is denied or invalid.
    const rubrics = [];
    for (const c of criteria) {
      const rubric = await this.generateRubric({
        criterionName: c.name,
        criterionDescription: c.description,
        scale: '1-5',
        includeExamples: false,
        strictness: 'balanced'
      });
      if (!rubric.success) throw new Error('Required rubric unavailable; scoring not attempted.');
      rubrics.push(rubric);
    }

    // Build combined rubric
    const levelDescriptions: Record<string, string> = {};
    for (const rubric of rubrics) {
      for (const level of rubric.levels) {
        const key = String(level.score);
        levelDescriptions[key] = (levelDescriptions[key] ?? '') + `${rubric.criterion.name}: ${level.description}\n`;
      }
    }

    // Score using generated rubric
    return this.score({
      response,
      prompt,
      criteria: criteria.map((c) => ({
        name: c.name,
        description: c.description,
        weight: c.weight ?? 1
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
    const result = await requireJudgeRuntime(this.runtime).generate({
      system: `You are an expert evaluator of AI-generated content.
Your role is to assess quality, identify issues, and provide actionable feedback.
Be objective, specific, and constructive in your evaluations.`,
      prompt: userMessage,
      temperature: this.temperature
    });

    return {
      text: result.text,
      usage: result.usage
    };
  }
}

// Default instance
export const evaluatorAgent = new EvaluatorAgent();
