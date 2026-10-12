import { tool } from 'ai';
import { z } from 'zod';
import { openai } from '@ai-sdk/openai';
import { generateText } from 'ai';
import { checkBudget, config, recordUsage, withRetries } from '../../config/index.js';

const CriterionSchema = z.object({
  name: z.string().describe('Name of the criterion'),
  description: z.string().describe('What this criterion measures'),
  weight: z.number().min(0).max(1).default(1).describe('Relative importance')
});

const RubricSchema = z.object({
  scale: z.enum(['1-3', '1-5', '1-10']).default('1-5'),
  levelDescriptions: z.record(z.string(), z.string()).optional()
});

export const DirectScoreInputSchema = z.object({
  response: z.string().describe('The LLM response to evaluate'),
  prompt: z.string().describe('The original prompt that generated the response'),
  context: z.string().optional().describe('Additional context'),
  criteria: z.array(CriterionSchema).min(1).describe('Evaluation criteria'),
  rubric: RubricSchema.optional()
});

export type DirectScoreInput = z.infer<typeof DirectScoreInputSchema>;

export const DirectScoreOutputSchema = z.object({
  success: z.boolean(),
  scores: z.array(z.object({
    criterion: z.string(),
    score: z.number(),
    maxScore: z.number(),
    justification: z.string(),
    evidence: z.array(z.string()),
    improvement: z.string()
  })),
  overallScore: z.number(),
  weightedScore: z.number(),
  summary: z.object({
    assessment: z.string(),
    strengths: z.array(z.string()),
    weaknesses: z.array(z.string()),
    priorities: z.array(z.string())
  }),
  metadata: z.object({
    evaluationTimeMs: z.number(),
    model: z.string(),
    criteriaCount: z.number()
  })
});

export type DirectScoreOutput = z.infer<typeof DirectScoreOutputSchema>;

export async function executeDirectScore(input: DirectScoreInput): Promise<DirectScoreOutput> {
  const startTime = Date.now();
  const scale = input.rubric?.scale || '1-5';
  const maxScore = parseInt(scale.split('-')[1]);

  const budgetCheck = checkBudget('executeDirectScore');
  if (!budgetCheck.ok) {
    return {
      success: false,
      scores: [],
      overallScore: 0,
      weightedScore: 0,
      summary: {
        assessment: `Evaluation blocked by budget guard: ${budgetCheck.reason}`,
        strengths: [],
        weaknesses: [],
        priorities: []
      },
      metadata: {
        evaluationTimeMs: Date.now() - startTime,
        model: config.openai.model,
        criteriaCount: input.criteria.length
      }
    };
  }

  if (config.budgets.dryRun) {
    recordUsage();
    return {
      success: true,
      scores: input.criteria.map(c => ({
        criterion: c.name,
        score: Math.ceil(maxScore / 2),
        maxScore,
        justification: '[dry-run] No live evaluation performed.',
        evidence: ['[dry-run] stub evidence'],
        improvement: 'Re-run with JUDGE_DRY_RUN=false for a real evaluation.'
      })),
      overallScore: Math.ceil(maxScore / 2),
      weightedScore: Math.ceil(maxScore / 2),
      summary: {
        assessment: '[dry-run] Evaluation stub returned because JUDGE_DRY_RUN is enabled.',
        strengths: ['[dry-run] No paid API call was made.'],
        weaknesses: [],
        priorities: ['Disable JUDGE_DRY_RUN to perform a real evaluation.']
      },
      metadata: {
        evaluationTimeMs: Date.now() - startTime,
        model: config.openai.model,
        criteriaCount: input.criteria.length
      }
    };
  }

  const systemPrompt = `You are an expert evaluator. Assess the response against each criterion.
For each criterion:
1. Find specific evidence in the response
2. Score according to the rubric (1-${maxScore} scale)
3. Justify your score
4. Suggest one improvement

Be objective and consistent. Base scores on explicit evidence.`;

  const userPrompt = `## Original Prompt
${input.prompt}

${input.context ? `## Context\n${input.context}\n` : ''}
## Response to Evaluate
${input.response}

## Criteria
${input.criteria.map((c, i) => `${i + 1}. **${c.name}** (weight: ${c.weight}): ${c.description}`).join('\n')}

${input.rubric?.levelDescriptions ? `## Rubric\n${Object.entries(input.rubric.levelDescriptions).map(([k, v]) => `- ${k}: ${v}`).join('\n')}` : ''}

Respond with valid JSON matching this structure:
{
  "scores": [
    {
      "criterion": "criterion name",
      "score": number,
      "evidence": ["quote or observation 1", "quote 2"],
      "justification": "why this score",
      "improvement": "specific suggestion"
    }
  ],
  "summary": {
    "assessment": "overall quality summary",
    "strengths": ["strength 1", "strength 2"],
    "weaknesses": ["weakness 1"],
    "priorities": ["most important improvement"]
  }
}`;

  try {
    const result = await withRetries('directScore', () => generateText({
      model: openai(config.openai.model),
      system: systemPrompt,
      prompt: userPrompt,
      temperature: 0.3
    }));

    recordUsage(result.usage);

    const parsed = JSON.parse(result.text);

    // Calculate scores
    const totalWeight = input.criteria.reduce((sum, c) => sum + c.weight, 0);
    const weightedSum = parsed.scores.reduce((sum: number, s: { criterion: string; score: number }) => {
      const criterion = input.criteria.find(c => c.name === s.criterion);
      return sum + (s.score * (criterion?.weight || 1));
    }, 0);

    const overallScore = parsed.scores.reduce((sum: number, s: { score: number }) => sum + s.score, 0) / parsed.scores.length;
    const weightedScore = weightedSum / totalWeight;

    return {
      success: true,
      scores: parsed.scores.map((s: { criterion: string; score: number; evidence?: string[]; justification: string; improvement: string }) => ({
        ...s,
        maxScore,
        evidence: s.evidence || []
      })),
      overallScore: Math.round(overallScore * 100) / 100,
      weightedScore: Math.round(weightedScore * 100) / 100,
      summary: parsed.summary,
      metadata: {
        evaluationTimeMs: Date.now() - startTime,
        model: config.openai.model,
        criteriaCount: input.criteria.length
      }
    };
  } catch (error) {
    return {
      success: false,
      scores: [],
      overallScore: 0,
      weightedScore: 0,
      summary: {
        assessment: `Evaluation failed: ${error instanceof Error ? error.message : 'Unknown error'}`,
        strengths: [],
        weaknesses: [],
        priorities: []
      },
      metadata: {
        evaluationTimeMs: Date.now() - startTime,
        model: config.openai.model,
        criteriaCount: input.criteria.length
      }
    };
  }
}

export const directScoreTool = tool({
  description: `Evaluate a response by scoring it against specific criteria.
Use for objective evaluations like accuracy, completeness, clarity.
Returns structured scores with justifications.`,
  parameters: DirectScoreInputSchema,
  execute: executeDirectScore
});

