import { tool } from 'ai';
import { z } from 'zod';
import { JudgeRuntime, requireJudgeRuntime } from '../../runtime/judge-runtime.js';

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

export async function executeDirectScore(input: DirectScoreInput, runtime?: JudgeRuntime): Promise<DirectScoreOutput> {
  input = DirectScoreInputSchema.parse(input);
  if (new Set(input.criteria.map(c => c.name)).size !== input.criteria.length || !input.criteria.some(c => c.weight > 0)) {
    throw new Error('Criteria must have unique names and positive total weight.');
  }
  const startTime = Date.now();
  const scale = input.rubric?.scale || '1-5';
  const maxScore = parseInt(scale.split('-')[1]);

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
    const result = await requireJudgeRuntime(runtime).generate({
      system: systemPrompt,
      prompt: userPrompt,
      temperature: 0.3
    });

    const parsed = z.object({
      scores: z.array(DirectScoreOutputSchema.shape.scores.element.omit({ maxScore: true }).extend({
        score: z.number().min(1).max(maxScore)
      })).length(input.criteria.length),
      summary: DirectScoreOutputSchema.shape.summary
    }).parse(JSON.parse(result.text));
    if (new Set(parsed.scores.map(s => s.criterion)).size !== input.criteria.length ||
        parsed.scores.some(s => !input.criteria.some(c => c.name === s.criterion))) {
      throw new Error('Judge returned mismatched criteria.');
    }
    
    // Calculate scores
    const totalWeight = input.criteria.reduce((sum, c) => sum + c.weight, 0);
    const weightedSum = parsed.scores.reduce((sum: number, s: { criterion: string; score: number }) => {
      const criterion = input.criteria.find(c => c.name === s.criterion);
      return sum + (s.score * (criterion?.weight ?? 1));
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
        model: runtime?.modelId ?? 'unconfigured',
        criteriaCount: input.criteria.length
      }
    };
  } catch {
    return {
      success: false,
      scores: [],
      overallScore: 0,
      weightedScore: 0,
      summary: {
        assessment: 'Evaluation unavailable or invalid. No automatic retry was attempted.',
        strengths: [],
        weaknesses: [],
        priorities: []
      },
      metadata: {
        evaluationTimeMs: Date.now() - startTime,
        model: runtime?.modelId ?? 'unconfigured',
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
  execute: input => executeDirectScore(input)
});
