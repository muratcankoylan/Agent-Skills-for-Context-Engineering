/**
 * Pairwise Comparison Example
 * 
 * Demonstrates how to compare two responses and pick the better one.
 * 
 * Run: npx tsx examples/pairwise-comparison.ts
 */

import { EvaluatorAgent } from '../src/agents/evaluator.js';
import { validateConfig } from '../src/config/index.js';

async function main() {
  validateConfig();

  const agent = new EvaluatorAgent();

  console.log('=== Pairwise Comparison Example ===\n');

  const prompt = 'Explain the benefits of regular exercise';

  const responseA = `
    Regular exercise offers numerous health benefits that affect both body and mind.
    
    Physical benefits include:
    - Improved cardiovascular health and reduced heart disease risk
    - Stronger muscles and bones
    - Better weight management
    - Enhanced immune function
    
    Mental benefits include:
    - Reduced stress and anxiety
    - Improved mood through endorphin release
    - Better sleep quality
    - Enhanced cognitive function
    
    The CDC recommends at least 150 minutes of moderate aerobic activity per week,
    plus muscle-strengthening activities twice weekly.
  `;

  const responseB = `
    Working out is really good for you. It makes you healthier and feel better.
    You should try to exercise regularly if you can. Many people find that
    going to the gym or running helps them stay in shape.
  `;

  console.log('Prompt:', prompt);
  console.log('\n--- Response A ---');
  console.log(responseA.trim());
  console.log('\n--- Response B ---');
  console.log(responseB.trim());
  console.log('\n--- Comparison Results ---\n');

  const result = await agent.compare({
    responseA,
    responseB,
    prompt,
    criteria: ['accuracy', 'completeness', 'actionability', 'clarity'],
    allowTie: true,
    swapPositions: true // Mitigate position bias
  });

  if (result.success) {
    console.log(`Winner: Response ${result.winner}`);
    console.log(`Confidence: ${(result.confidence * 100).toFixed(0)}%`);
    
    if (result.positionConsistency) {
      console.log(`Position Consistency: ${result.positionConsistency.consistent ? 'Yes' : 'No'}`);
    }

    console.log('\nPer-Criterion Results:');
    result.comparison.forEach(c => {
      console.log(`\n  ${c.criterion}:`);
      console.log(`    Winner: ${c.winner}`);
      console.log(`    A: ${c.aAssessment}`);
      console.log(`    B: ${c.bAssessment}`);
    });

    console.log('\nKey Differentiators:');
    result.differentiators.forEach(d => console.log(`  - ${d}`));

    console.log('\nResponse A Analysis:');
    console.log('  Strengths:', result.analysis.responseA.strengths.join(', '));
    console.log('  Weaknesses:', result.analysis.responseA.weaknesses.join(', '));

    console.log('\nResponse B Analysis:');
    console.log('  Strengths:', result.analysis.responseB.strengths.join(', '));
    console.log('  Weaknesses:', result.analysis.responseB.weaknesses.join(', '));

    console.log(`\nEvaluation Time: ${result.metadata.evaluationTimeMs}ms`);
  } else {
    console.error('Comparison failed');
  }
}

main().catch(error => {
  console.error(error instanceof Error ? error.message : 'Example failed.');
  process.exitCode = 1;
});
