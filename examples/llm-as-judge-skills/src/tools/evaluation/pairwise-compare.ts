import { tool } from 'ai';
import { z } from 'zod';
import { openai } from '@ai-sdk/openai';
import { generateText } from 'ai';
import { checkBudget, config, recordUsage, withRetries } from '../../config/index.js';

export const PairwiseCompareInputSchema = z.object({
  responseA: z.string().describe('First response to compare'),
  responseB: z.string().describe('Second response to compare'),
  prompt: z.string().describe('The original prompt both responses address'),
  context: z.string().optional().describe('Additional context'),
  criteria: z.array(z.string()).min(1).describe('Comparison criteria'),
  allowTie: z.boolean().optional().default(true).describe('Allow tie verdict'),
  swapPositions: z.boolean().optional().default(true).describe('Swap positions to reduce bias')
});

export type PairwiseCompareInput = z.infer<typeof PairwiseCompareInputSchema>;

export const PairwiseCompareOutputSchema = z.object({
  success: z.boolean(),
  winner: z.enum(['A', 'B', 'TIE']),
  confidence: z.number().min(0).max(1),
  comparison: z.array(z.object({
    criterion: z.string(),
    winner: z.enum(['A', 'B', 'TIE']),
    aAssessment: z.string(),
    bAssessment: z.string(),
    reasoning: z.string()
  })),
  analysis: z.object({
    responseA: z.object({
      strengths: z.array(z.string()),
      weaknesses: z.array(z.string())
    }),
    responseB: z.object({
      strengths: z.array(z.string()),
      weaknesses: z.array(z.string())
    })
  }),
  differentiators: z.array(z.string()),
  positionConsistency: z.object({
    consistent: z.boolean(),
    firstPassWinner: z.enum(['A', 'B', 'TIE']).optional(),
    secondPassWinner: z.enum(['A', 'B', 'TIE']).optional()
  }).optional(),
  metadata: z.object({
    evaluationTimeMs: z.number(),
    model: z.string(),
    positionsSwapped: z.boolean()
  })
});

export type PairwiseCompareOutput = z.infer<typeof PairwiseCompareOutputSchema>;

async function evaluatePair(
  first: string,
  second: string,
  prompt: string,
  criteria: string[],
  context?: string,
  allowTie: boolean = true
): Promise<{ winner: 'A' | 'B' | 'TIE'; confidence: number; comparison: PairwiseCompareOutput['comparison']; analysis: PairwiseCompareOutput['analysis'] }> {
  const systemPrompt = `You are an expert evaluator comparing two AI responses.

IMPORTANT:
- Do NOT prefer responses because they are longer
- Do NOT prefer responses based on position (first vs second)
- Focus only on quality according to the criteria
- ${allowTie ? 'Ties are acceptable when responses are genuinely equivalent' : 'You must choose a winner'}`;

  const userPrompt = `## Original Prompt
${prompt}

${context ? `## Context\n${context}\n` : ''}
## Response A
${first}

## Response B
${second}

## Criteria to Compare
${criteria.map((c, i) => `${i + 1}. ${c}`).join('\n')}

First analyze each response independently, then compare them.
Respond with valid JSON:
{
  "analysis": {
    "responseA": { "strengths": [...], "weaknesses": [...] },
    "responseB": { "strengths": [...], "weaknesses": [...] }
  },
  "comparison": [
    {
      "criterion": "criterion name",
      "winner": "A" | "B" | "TIE",
      "aAssessment": "brief assessment of A",
      "bAssessment": "brief assessment of B",
      "reasoning": "why this winner"
    }
  ],
  "result": {
    "winner": "A" | "B" | "TIE",
    "confidence": 0.0-1.0,
    "reasoning": "overall reasoning"
  }
}`;

  const result = await withRetries('pairwiseCompare.evaluatePair', () => generateText({
    model: openai(config.openai.model),
    system: systemPrompt,
    prompt: userPrompt,
    temperature: 0.3
  }));

  recordUsage(result.usage);

  const parsed = JSON.parse(result.text);

  return {
    winner: parsed.result.winner,
    confidence: parsed.result.confidence,
    comparison: parsed.comparison,
    analysis: parsed.analysis
  };
}

export async function executePairwiseCompare(input: PairwiseCompareInput): Promise<PairwiseCompareOutput> {
  const startTime = Date.now();

  const budgetCheck = checkBudget('executePairwiseCompare');
  if (!budgetCheck.ok) {
    return {
      success: false,
      winner: 'TIE',
      confidence: 0,
      comparison: [],
      analysis: {
        responseA: { strengths: [], weaknesses: [] },
        responseB: { strengths: [], weaknesses: [] }
      },
      differentiators: [],
      metadata: {
        evaluationTimeMs: Date.now() - startTime,
        model: config.openai.model,
        positionsSwapped: input.swapPositions
      }
    };
  }

  if (config.budgets.dryRun) {
    recordUsage();
    const comparisonStub = input.criteria.map(c => ({
      criterion: c,
      winner: 'TIE' as const,
      aAssessment: '[dry-run] No live assessment performed.',
      bAssessment: '[dry-run] No live assessment performed.',
      reasoning: '[dry-run] JUDGE_DRY_RUN is enabled.'
    }));
    return {
      success: true,
      winner: 'TIE',
      confidence: 0.5,
      comparison: comparisonStub,
      analysis: {
        responseA: { strengths: ['[dry-run] No paid API call was made.'], weaknesses: [] },
        responseB: { strengths: ['[dry-run] No paid API call was made.'], weaknesses: [] }
      },
      differentiators: [],
      positionConsistency: {
        consistent: true,
        firstPassWinner: 'TIE',
        secondPassWinner: 'TIE'
      },
      metadata: {
        evaluationTimeMs: Date.now() - startTime,
        model: config.openai.model,
        positionsSwapped: input.swapPositions
      }
    };
  }

  try {
    if (input.swapPositions) {
      // First pass: A first, B second
      const pass1 = await evaluatePair(
        input.responseA,
        input.responseB,
        input.prompt,
        input.criteria,
        input.context,
        input.allowTie
      );

      // Second pass: B first, A second
      const pass2 = await evaluatePair(
        input.responseB,
        input.responseA,
        input.prompt,
        input.criteria,
        input.context,
        input.allowTie
      );

      // Map pass2 result back
      const pass2WinnerMapped = pass2.winner === 'A' ? 'B' : pass2.winner === 'B' ? 'A' : 'TIE';
      const consistent = pass1.winner === pass2WinnerMapped;

      // Determine final winner
      let finalWinner: 'A' | 'B' | 'TIE';
      let finalConfidence: number;

      if (consistent) {
        finalWinner = pass1.winner;
        finalConfidence = (pass1.confidence + pass2.confidence) / 2;
      } else {
        // Inconsistent - return tie with lower confidence
        finalWinner = 'TIE';
        finalConfidence = 0.5;
      }

      // Merge comparisons
      const mergedComparison = pass1.comparison.map((c, i) => {
        const c2 = pass2.comparison[i];
        const c2WinnerMapped = c2.winner === 'A' ? 'B' : c2.winner === 'B' ? 'A' : 'TIE';
        return {
          ...c,
          winner: c.winner === c2WinnerMapped ? c.winner : 'TIE' as const
        };
      });

      // Find differentiators
      const differentiators = mergedComparison
        .filter(c => c.winner !== 'TIE')
        .map(c => `${c.criterion}: ${c.winner === 'A' ? 'Response A' : 'Response B'} wins - ${c.reasoning}`);

      return {
        success: true,
        winner: finalWinner,
        confidence: Math.round(finalConfidence * 100) / 100,
        comparison: mergedComparison,
        analysis: pass1.analysis,
        differentiators,
        positionConsistency: {
          consistent,
          firstPassWinner: pass1.winner,
          secondPassWinner: pass2WinnerMapped
        },
        metadata: {
          evaluationTimeMs: Date.now() - startTime,
          model: config.openai.model,
          positionsSwapped: true
        }
      };
    } else {
      // Single pass without swap
      const result = await evaluatePair(
        input.responseA,
        input.responseB,
        input.prompt,
        input.criteria,
        input.context,
        input.allowTie
      );

      const differentiators = result.comparison
        .filter(c => c.winner !== 'TIE')
        .map(c => `${c.criterion}: ${c.winner === 'A' ? 'Response A' : 'Response B'} wins - ${c.reasoning}`);

      return {
        success: true,
        winner: result.winner,
        confidence: result.confidence,
        comparison: result.comparison,
        analysis: result.analysis,
        differentiators,
        metadata: {
          evaluationTimeMs: Date.now() - startTime,
          model: config.openai.model,
          positionsSwapped: false
        }
      };
    }
  } catch {
    return {
      success: false,
      winner: 'TIE',
      confidence: 0,
      comparison: [],
      analysis: {
        responseA: { strengths: [], weaknesses: [] },
        responseB: { strengths: [], weaknesses: [] }
      },
      differentiators: [],
      metadata: {
        evaluationTimeMs: Date.now() - startTime,
        model: config.openai.model,
        positionsSwapped: input.swapPositions
      }
    };
  }
}

export const pairwiseCompareTool = tool({
  description: `Compare two responses and select the better one.
Use for subjective evaluations like tone, persuasiveness, style.
More reliable than direct scoring for preferences.`,
  parameters: PairwiseCompareInputSchema,
  execute: executePairwiseCompare
});

