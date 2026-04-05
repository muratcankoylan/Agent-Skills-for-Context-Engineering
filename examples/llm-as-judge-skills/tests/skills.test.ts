import { describe, it, expect, beforeAll, beforeEach } from 'vitest';
import { EvaluatorAgent } from '../src/agents/evaluator.js';
import { validateConfig } from '../src/config/index.js';

const hasOpenAIKey = Boolean(process.env.OPENAI_API_KEY);
const describeLive = hasOpenAIKey ? describe : describe.skip;

/**
 * Tests for skills implementation based on LLM-as-a-Judge research
 */

describeLive('LLM Evaluator Skill Tests', () => {
  let agent: EvaluatorAgent;

  beforeAll(() => {
    validateConfig();
  });

  beforeEach(() => {
    agent = new EvaluatorAgent();
  });

  describe('Direct Scoring Skill', () => {
    it('should use chain-of-thought in scoring', async () => {
      const result = await agent.score({
        response: 'Machine learning is a type of artificial intelligence that allows computers to learn from data.',
        prompt: 'Define machine learning',
        criteria: [
          { name: 'Accuracy', description: 'Factual correctness', weight: 1 }
        ]
      });

      expect(result.success).toBe(true);
      // Should have justification (evidence of CoT)
      if (result.scores.length > 0) {
        expect(result.scores[0].justification.length).toBeGreaterThan(20);
      }
    }, 60000);

    it('should handle multiple weighted criteria', async () => {
      const result = await agent.score({
        response: 'The mitochondria is the powerhouse of the cell. It produces ATP.',
        prompt: 'Explain the function of mitochondria',
        criteria: [
          { name: 'Accuracy', description: 'Scientific correctness', weight: 0.5 },
          { name: 'Completeness', description: 'Covers key points', weight: 0.3 },
          { name: 'Clarity', description: 'Easy to understand', weight: 0.2 }
        ]
      });

      expect(result.success).toBe(true);
      expect(result.scores).toHaveLength(3);
      expect(result.weightedScore).toBeDefined();
    }, 60000);
  });

  describe('Pairwise Comparison Skill', () => {
    it('should mitigate position bias with swap', async () => {
      const response1 = 'Water boils at 100 degrees Celsius at sea level.';
      const response2 = 'Water boils at 100°C (212°F) at standard atmospheric pressure (sea level).';

      const result = await agent.compare({
        responseA: response1,
        responseB: response2,
        prompt: 'At what temperature does water boil?',
        criteria: ['accuracy', 'completeness'],
        allowTie: true,
        swapPositions: true
      });

      expect(result.success).toBe(true);
      expect(result.positionConsistency).toBeDefined();
    }, 120000);

    it('should identify clear winner for quality difference', async () => {
      const good = `The Earth revolves around the Sun in an elliptical orbit, 
        taking approximately 365.25 days to complete one revolution. 
        This is why we have leap years every 4 years.`;
      
      const poor = 'The earth goes around the sun.';

      const result = await agent.compare({
        responseA: good,
        responseB: poor,
        prompt: 'How does the Earth orbit the Sun?',
        criteria: ['completeness', 'accuracy', 'detail'],
        allowTie: true,
        swapPositions: true
      });

      expect(result.success).toBe(true);
      expect(result.winner).toBe('A');
      expect(result.confidence).toBeGreaterThan(0.5);
    }, 120000);
  });

  describe('Rubric Generation Skill', () => {
    it('should generate domain-specific rubrics', async () => {
      const result = await agent.generateRubric({
        criterionName: 'Code Readability',
        criterionDescription: 'How easy the code is to understand and maintain',
        scale: '1-5',
        domain: 'software engineering',
        includeExamples: true,
        strictness: 'balanced'
      });

      expect(result.success).toBe(true);
      expect(result.levels.length).toBe(5);
      expect(result.metadata.domain).toBe('software engineering');
      
      // Should have code-specific terminology
      const allText = result.levels.map(l => l.description + l.characteristics.join(' ')).join(' ');
      expect(allText.toLowerCase()).toMatch(/variable|function|comment|name|structure|code|read/i);
    }, 60000);

    it('should provide edge case guidance', async () => {
      const result = await agent.generateRubric({
        criterionName: 'Factual Accuracy',
        criterionDescription: 'Whether claims are factually correct',
        scale: '1-5',
        includeExamples: false,
        strictness: 'strict'
      });

      expect(result.success).toBe(true);
      expect(result.edgeCases.length).toBeGreaterThan(0);
      result.edgeCases.forEach(ec => {
        expect(ec.situation).toBeDefined();
        expect(ec.guidance).toBeDefined();
      });
    }, 60000);
  });

  describe('Context Fundamentals Skill Application', () => {
    it('should utilize provided context in evaluation', async () => {
      const context = `The user is a medical professional asking about drug interactions.
        Technical terminology is appropriate.`;

      const result = await agent.score({
        response: 'Combining SSRIs with MAOIs can lead to serotonin syndrome, a potentially life-threatening condition.',
        prompt: 'What are the risks of combining antidepressants?',
        context,
        criteria: [
          { name: 'Accuracy', description: 'Medical accuracy', weight: 0.5 },
          { name: 'Appropriateness', description: 'Appropriate for audience', weight: 0.5 }
        ]
      });

      expect(result.success).toBe(true);
      // Technical response should score well given medical context
      expect(result.overallScore).toBeGreaterThanOrEqual(2);
    }, 60000);
  });
});

describeLive('Skill Input/Output Validation', () => {
  let agent: EvaluatorAgent;

  beforeAll(() => {
    validateConfig();
    agent = new EvaluatorAgent();
  });

  it('should validate DirectScore input schema', async () => {
    const result = await agent.score({
      response: 'Test response',
      prompt: 'Test prompt',
      criteria: [{ name: 'Test', description: 'Test criterion', weight: 1 }]
    });
    
    expect(result).toHaveProperty('success');
    expect(result).toHaveProperty('scores');
    expect(result).toHaveProperty('overallScore');
    expect(result).toHaveProperty('summary');
    expect(result).toHaveProperty('metadata');
  }, 60000);

  it('should validate PairwiseCompare output structure', async () => {
    const result = await agent.compare({
      responseA: 'Response A content',
      responseB: 'Response B content',
      prompt: 'Test prompt',
      criteria: ['quality'],
      allowTie: true,
      swapPositions: false
    });

    expect(result).toHaveProperty('success');
    expect(result).toHaveProperty('winner');
    expect(['A', 'B', 'TIE']).toContain(result.winner);
    expect(result).toHaveProperty('confidence');
    expect(result.confidence).toBeGreaterThanOrEqual(0);
    expect(result.confidence).toBeLessThanOrEqual(1);
    expect(result).toHaveProperty('comparison');
    expect(result).toHaveProperty('metadata');
  }, 60000);

  it('should validate GenerateRubric output structure', async () => {
    const result = await agent.generateRubric({
      criterionName: 'Test',
      criterionDescription: 'Test criterion',
      scale: '1-5',
      includeExamples: false,
      strictness: 'balanced'
    });

    expect(result).toHaveProperty('success');
    expect(result).toHaveProperty('criterion');
    expect(result).toHaveProperty('scale');
    expect(result).toHaveProperty('levels');
    expect(result).toHaveProperty('scoringGuidelines');
    expect(result).toHaveProperty('edgeCases');
    expect(result).toHaveProperty('metadata');
  }, 60000);
});
