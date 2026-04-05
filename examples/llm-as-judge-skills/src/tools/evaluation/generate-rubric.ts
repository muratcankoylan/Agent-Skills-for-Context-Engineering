import { tool } from 'ai';
import { z } from 'zod';
import { openai } from '@ai-sdk/openai';
import { generateText } from 'ai';
import { config } from '../../config/index.js';

export const GenerateRubricInputSchema = z.object({
  criterionName: z.string().describe('Name of the criterion'),
  criterionDescription: z.string().describe('What this criterion measures'),
  scale: z.enum(['1-3', '1-5', '1-10']).optional().default('1-5'),
  domain: z.string().optional().describe('Domain context'),
  includeExamples: z.boolean().optional().default(true),
  strictness: z.enum(['lenient', 'balanced', 'strict']).optional().default('balanced')
});

export type GenerateRubricInput = z.infer<typeof GenerateRubricInputSchema>;

export const GenerateRubricOutputSchema = z.object({
  success: z.boolean(),
  criterion: z.object({
    name: z.string(),
    description: z.string()
  }),
  scale: z.object({
    min: z.number(),
    max: z.number(),
    type: z.string()
  }),
  levels: z.array(z.object({
    score: z.number(),
    label: z.string(),
    description: z.string(),
    characteristics: z.array(z.string()),
    example: z.string().optional()
  })),
  scoringGuidelines: z.array(z.string()),
  edgeCases: z.array(z.object({
    situation: z.string(),
    guidance: z.string()
  })),
  metadata: z.object({
    domain: z.string().nullable(),
    strictness: z.string(),
    generationTimeMs: z.number()
  })
});

export type GenerateRubricOutput = z.infer<typeof GenerateRubricOutputSchema>;

export async function executeGenerateRubric(input: GenerateRubricInput): Promise<GenerateRubricOutput> {
  const startTime = Date.now();
  const [minScore, maxScore] = input.scale.split('-').map(Number);

  const systemPrompt = `You are an expert in creating evaluation rubrics.
Create clear, actionable rubrics with distinct boundaries between levels.
Strictness: ${input.strictness}
- lenient: Lower bar for passing scores
- balanced: Fair, typical expectations
- strict: High standards, critical evaluation`;

  const userPrompt = `Create a scoring rubric for:

**Criterion**: ${input.criterionName}
**Description**: ${input.criterionDescription}
**Scale**: ${input.scale} (${minScore} = lowest, ${maxScore} = highest)
${input.domain ? `**Domain**: ${input.domain}` : ''}
**Include Examples**: ${input.includeExamples}

Generate a rubric with:
1. Clear descriptions for each score level
2. Specific characteristics that define each level
3. ${input.includeExamples ? 'Brief example text for each level' : 'No examples needed'}
4. General scoring guidelines
5. Edge cases with guidance

Respond with valid JSON:
{
  "levels": [
    {
      "score": ${minScore},
      "label": "Label (e.g., Poor)",
      "description": "Detailed description of this level",
      "characteristics": ["characteristic 1", "characteristic 2"],
      "example": ${input.includeExamples ? '"Brief example text"' : 'null'}
    }
    // ... all levels from ${minScore} to ${maxScore}
  ],
  "scoringGuidelines": [
    "General guideline 1",
    "General guideline 2"
  ],
  "edgeCases": [
    {
      "situation": "Edge case description",
      "guidance": "How to handle it"
    }
  ]
}`;

  try {
    const result = await generateText({
      model: openai(config.openai.model),
      system: systemPrompt,
      prompt: userPrompt,
      temperature: 0.4
    });

    const parsed = JSON.parse(result.text);

    return {
      success: true,
      criterion: {
        name: input.criterionName,
        description: input.criterionDescription
      },
      scale: {
        min: minScore,
        max: maxScore,
        type: input.scale
      },
      levels: parsed.levels,
      scoringGuidelines: parsed.scoringGuidelines,
      edgeCases: parsed.edgeCases,
      metadata: {
        domain: input.domain || null,
        strictness: input.strictness,
        generationTimeMs: Date.now() - startTime
      }
    };
  } catch {
    return {
      success: false,
      criterion: {
        name: input.criterionName,
        description: input.criterionDescription
      },
      scale: {
        min: minScore,
        max: maxScore,
        type: input.scale
      },
      levels: [],
      scoringGuidelines: [],
      edgeCases: [],
      metadata: {
        domain: input.domain || null,
        strictness: input.strictness,
        generationTimeMs: Date.now() - startTime
      }
    };
  }
}

export const generateRubricTool = tool({
  description: `Generate a scoring rubric for an evaluation criterion.
Creates detailed descriptions for each score level.
Use to establish consistent evaluation standards.`,
  parameters: GenerateRubricInputSchema,
  execute: executeGenerateRubric
});
