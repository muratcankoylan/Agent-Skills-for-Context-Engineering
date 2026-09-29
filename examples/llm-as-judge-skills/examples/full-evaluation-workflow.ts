/**
 * Full Evaluation Workflow Example
 * 
 * Demonstrates a complete evaluation workflow:
 * 1. Generate rubrics for criteria
 * 2. Score a response using generated rubrics
 * 3. Compare with an alternative response
 * 
 * Run: npx tsx examples/full-evaluation-workflow.ts
 */

import { EvaluatorAgent } from '../src/agents/evaluator.js';
import { validateConfig } from '../src/config/index.js';

async function main() {
  validateConfig();

  const agent = new EvaluatorAgent();
  const startTime = Date.now();

  console.log('=== Full Evaluation Workflow ===\n');

  const prompt = 'Explain how vaccines work to prevent disease';

  const response = `
    Vaccines work by training your immune system to recognize and fight specific pathogens
    without causing the disease itself.
    
    Here's the process:
    
    1. **Introduction**: The vaccine introduces a weakened, killed, or partial version of
       the pathogen (or instructions to make a piece of it, like mRNA vaccines).
    
    2. **Immune Response**: Your immune system detects these foreign substances (antigens)
       and mounts a response. This includes producing antibodies and training T-cells.
    
    3. **Memory Formation**: Some immune cells become "memory cells" that remember
       how to fight this specific pathogen.
    
    4. **Future Protection**: If you're exposed to the real pathogen later, your immune
       system recognizes it immediately and can fight it off before you get sick.
    
    This is why vaccines are so effective - they give your immune system a "practice run"
    without the risks of actual infection.
  `;

  // Step 1: Generate rubrics
  console.log('Step 1: Generating rubrics...\n');

  const criteria = [
    { name: 'Scientific Accuracy', description: 'Correctness of biological/medical information' },
    { name: 'Completeness', description: 'Covers the key steps and concepts' },
    { name: 'Accessibility', description: 'Understandable by general audience' }
  ];

  const rubrics = await Promise.all(
    criteria.map(c => agent.generateRubric({
      criterionName: c.name,
      criterionDescription: c.description,
      scale: '1-5',
      domain: 'health education',
      includeExamples: false,
      strictness: 'balanced'
    }))
  );

  console.log('Generated rubrics for:');
  rubrics.forEach(r => {
    if (r.success) {
      console.log(`  - ${r.criterion.name} (${r.levels.length} levels)`);
    }
  });

  // Step 2: Score the response
  console.log('\nStep 2: Scoring the response...\n');

  const scoreResult = await agent.score({
    response,
    prompt,
    criteria: criteria.map((c, i) => ({
      name: c.name,
      description: c.description,
      weight: i === 0 ? 0.4 : 0.3 // Weight accuracy higher
    })),
    rubric: {
      scale: '1-5',
      levelDescriptions: rubrics[0].success 
        ? Object.fromEntries(rubrics[0].levels.map(l => [String(l.score), l.label]))
        : undefined
    }
  });

  if (scoreResult.success) {
    console.log('Scores:');
    scoreResult.scores.forEach(s => {
      console.log(`  ${s.criterion}: ${s.score}/${s.maxScore}`);
    });
    console.log(`\nOverall: ${scoreResult.overallScore} | Weighted: ${scoreResult.weightedScore}`);
  }

  // Step 3: Compare with an alternative
  console.log('\nStep 3: Comparing with alternative response...\n');

  const alternativeResponse = `
    Vaccines prevent disease by helping your body build immunity. When you get
    vaccinated, your body learns to fight the germ. Then if you're exposed to
    the real disease, your body already knows how to protect itself.
  `;

  const comparisonResult = await agent.compare({
    responseA: response,
    responseB: alternativeResponse,
    prompt,
    criteria: ['accuracy', 'depth', 'clarity'],
    allowTie: true,
    swapPositions: true
  });

  if (comparisonResult.success) {
    console.log(`Comparison Result: Response ${comparisonResult.winner} is better`);
    console.log(`Confidence: ${(comparisonResult.confidence * 100).toFixed(0)}%`);
    console.log('\nKey differences:');
    comparisonResult.differentiators.slice(0, 3).forEach(d => console.log(`  - ${d}`));
  }

  // Summary
  const totalTime = Date.now() - startTime;
  console.log('\n=== Workflow Complete ===');
  console.log(`Total time: ${totalTime}ms`);
  console.log(`Rubrics generated: ${rubrics.filter(r => r.success).length}`);
  console.log(`Final score: ${scoreResult.success ? scoreResult.overallScore : 'N/A'}`);
  console.log(`Better response: ${comparisonResult.success ? comparisonResult.winner : 'N/A'}`);
}

main().catch(error => {
  console.error(error instanceof Error ? error.message : 'Example failed.');
  process.exitCode = 1;
});
