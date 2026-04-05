import { describe, it, expect, beforeAll } from 'vitest';
import { 
  executeDirectScore, 
  executePairwiseCompare, 
  executeGenerateRubric,
  EvaluatorAgent
} from '../src/index.js';
import { validateConfig } from '../src/config/index.js';

const hasOpenAIKey = Boolean(process.env.OPENAI_API_KEY);
const describeLive = hasOpenAIKey ? describe : describe.skip;

// Test fixtures
const TEST_PROMPT = 'Explain quantum entanglement to a high school student';

const GOOD_RESPONSE = `Quantum entanglement is like having two magical coins that are connected in a special way. 
When you flip one coin and it lands on heads, the other coin will instantly show tails, 
no matter how far apart they are - even if one is on Earth and one is on Mars.

Here's what makes it special:
1. The connection is instantaneous - faster than light
2. You can't predict which side either coin will land on
3. But once you see one, you know exactly what the other shows

Scientists like Einstein called this "spooky action at a distance" because it seems impossible, 
but experiments have proven it's real. This phenomenon is now being used to develop 
super-secure communication systems and quantum computers.`;

const POOR_RESPONSE = `Quantum entanglement is when particles are connected. 
It's complicated physics stuff. Scientists study it.`;

const MEDIUM_RESPONSE = `Quantum entanglement happens when two particles become linked together. 
When you measure one particle, you instantly know something about the other particle, 
even if they're far apart. It's used in quantum computing research.`;

// Validate config once before all tests
beforeAll(() => {
  if (hasOpenAIKey) {
    validateConfig();
  }
});

describeLive('Direct Score Tool', () => {
  it('should score a response against criteria', async () => {
    const result = await executeDirectScore({
      response: GOOD_RESPONSE,
      prompt: TEST_PROMPT,
      criteria: [
        {
          name: 'Accuracy',
          description: 'Scientific correctness of the explanation',
          weight: 0.4
        },
        {
          name: 'Clarity',
          description: 'Understandable for a high school student',
          weight: 0.3
        },
        {
          name: 'Engagement',
          description: 'Interesting and memorable',
          weight: 0.3
        }
      ],
      rubric: {
        scale: '1-5'
      }
    });

    expect(result.success).toBe(true);
    expect(result.scores).toHaveLength(3);
    expect(result.overallScore).toBeGreaterThan(0);
    expect(result.overallScore).toBeLessThanOrEqual(5);
    expect(result.metadata.criteriaCount).toBe(3);
    
    // Good response should score reasonably well
    expect(result.overallScore).toBeGreaterThanOrEqual(3);
  }, 60000);

  it('should provide lower scores for poor responses', async () => {
    const goodResult = await executeDirectScore({
      response: GOOD_RESPONSE,
      prompt: TEST_PROMPT,
      criteria: [
        { name: 'Quality', description: 'Overall quality', weight: 1 }
      ]
    });

    const poorResult = await executeDirectScore({
      response: POOR_RESPONSE,
      prompt: TEST_PROMPT,
      criteria: [
        { name: 'Quality', description: 'Overall quality', weight: 1 }
      ]
    });

    expect(goodResult.success).toBe(true);
    expect(poorResult.success).toBe(true);
    expect(goodResult.overallScore).toBeGreaterThan(poorResult.overallScore);
  }, 120000);
});

describeLive('Pairwise Compare Tool', () => {
  it('should correctly identify the better response', async () => {
    const result = await executePairwiseCompare({
      responseA: GOOD_RESPONSE,
      responseB: POOR_RESPONSE,
      prompt: TEST_PROMPT,
      criteria: ['accuracy', 'clarity', 'completeness', 'engagement'],
      allowTie: true,
      swapPositions: true
    });

    expect(result.success).toBe(true);
    expect(result.winner).toBe('A');
    expect(result.confidence).toBeGreaterThan(0.5);
  }, 120000);

  it('should handle similar responses appropriately', async () => {
    const result = await executePairwiseCompare({
      responseA: MEDIUM_RESPONSE,
      responseB: MEDIUM_RESPONSE,
      prompt: TEST_PROMPT,
      criteria: ['quality'],
      allowTie: true,
      swapPositions: true
    });

    expect(result.success).toBe(true);
    // Same response should tie
    expect(result.winner).toBe('TIE');
  }, 120000);

  it('should provide comparison details for each criterion', async () => {
    const result = await executePairwiseCompare({
      responseA: GOOD_RESPONSE,
      responseB: MEDIUM_RESPONSE,
      prompt: TEST_PROMPT,
      criteria: ['accuracy', 'completeness'],
      allowTie: true,
      swapPositions: false
    });

    expect(result.success).toBe(true);
    expect(result.comparison).toHaveLength(2);
    result.comparison.forEach(c => {
      expect(c.criterion).toBeDefined();
      expect(['A', 'B', 'TIE']).toContain(c.winner);
      expect(c.reasoning).toBeDefined();
    });
  }, 60000);
});

describeLive('Generate Rubric Tool', () => {
  it('should generate a complete rubric', async () => {
    const result = await executeGenerateRubric({
      criterionName: 'Factual Accuracy',
      criterionDescription: 'How factually correct is the content',
      scale: '1-5',
      domain: 'educational content',
      includeExamples: true,
      strictness: 'balanced'
    });

    expect(result.success).toBe(true);
    expect(result.levels).toHaveLength(5);
    expect(result.scale.min).toBe(1);
    expect(result.scale.max).toBe(5);
    expect(result.scoringGuidelines.length).toBeGreaterThan(0);
    expect(result.edgeCases.length).toBeGreaterThan(0);

    // Check level structure
    result.levels.forEach(level => {
      expect(level.score).toBeGreaterThanOrEqual(1);
      expect(level.score).toBeLessThanOrEqual(5);
      expect(level.label).toBeDefined();
      expect(level.description).toBeDefined();
      expect(level.characteristics.length).toBeGreaterThan(0);
    });
  }, 60000);

  it('should respect strictness setting', async () => {
    const lenient = await executeGenerateRubric({
      criterionName: 'Code Quality',
      criterionDescription: 'Quality of code implementation',
      scale: '1-5',
      includeExamples: false,
      strictness: 'lenient'
    });

    const strict = await executeGenerateRubric({
      criterionName: 'Code Quality',
      criterionDescription: 'Quality of code implementation',
      scale: '1-5',
      includeExamples: false,
      strictness: 'strict'
    });

    expect(lenient.success).toBe(true);
    expect(strict.success).toBe(true);
    expect(lenient.metadata.strictness).toBe('lenient');
    expect(strict.metadata.strictness).toBe('strict');
  }, 120000);
});

describeLive('Evaluator Agent', () => {
  let agent: EvaluatorAgent;

  beforeAll(() => {
    agent = new EvaluatorAgent();
  });

  it('should provide integrated evaluation workflow', async () => {
    const result = await agent.evaluateWithGeneratedRubric(
      GOOD_RESPONSE,
      TEST_PROMPT,
      [
        { name: 'Accuracy', description: 'Scientific correctness' },
        { name: 'Accessibility', description: 'Appropriate for audience' }
      ]
    );

    expect(result.success).toBe(true);
    expect(result.scores.length).toBeGreaterThan(0);
  }, 120000);

  it('should support chat-based evaluation', async () => {
    const result = await agent.chat(`
      Please evaluate this response for accuracy:
      
      Question: What is photosynthesis?
      Response: Photosynthesis is how plants make food using sunlight, water, and carbon dioxide.
    `);

    expect(result.text).toBeDefined();
    expect(result.text.length).toBeGreaterThan(50);
  }, 60000);
});
