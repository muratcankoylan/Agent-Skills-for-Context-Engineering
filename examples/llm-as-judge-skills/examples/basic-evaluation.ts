/**
 * Basic Evaluation Example
 * 
 * Demonstrates how to use the EvaluatorAgent to score responses.
 * 
 * Run: npx tsx examples/basic-evaluation.ts
 */

import { EvaluatorAgent } from '../src/agents/evaluator.js';
import { validateConfig } from '../src/config/index.js';

async function main() {
  // Validate API key is configured
  validateConfig();

  const agent = new EvaluatorAgent();

  console.log('=== Direct Scoring Example ===\n');

  const response = `
    Machine learning is a subset of artificial intelligence that enables systems 
    to learn and improve from experience without being explicitly programmed. 
    It focuses on developing algorithms that can access data and use it to learn for themselves.
    
    There are three main types of machine learning:
    1. Supervised learning - learns from labeled data
    2. Unsupervised learning - finds patterns in unlabeled data  
    3. Reinforcement learning - learns through trial and error
  `;

  const result = await agent.score({
    response,
    prompt: 'Explain what machine learning is to a beginner',
    criteria: [
      {
        name: 'Accuracy',
        description: 'Factual correctness of the explanation',
        weight: 0.4
      },
      {
        name: 'Clarity',
        description: 'Easy to understand for a beginner',
        weight: 0.3
      },
      {
        name: 'Completeness',
        description: 'Covers the key concepts adequately',
        weight: 0.3
      }
    ],
    rubric: {
      scale: '1-5',
      levelDescriptions: {
        '1': 'Poor - Major issues',
        '2': 'Below Average - Several issues',
        '3': 'Average - Some issues',
        '4': 'Good - Minor issues only',
        '5': 'Excellent - No issues'
      }
    }
  });

  if (result.success) {
    console.log('Evaluation Results:');
    console.log('-------------------');
    
    result.scores.forEach(score => {
      console.log(`\n${score.criterion}: ${score.score}/${score.maxScore}`);
      console.log(`Justification: ${score.justification}`);
      console.log(`Improvement: ${score.improvement}`);
    });

    console.log('\n-------------------');
    console.log(`Overall Score: ${result.overallScore}`);
    console.log(`Weighted Score: ${result.weightedScore}`);
    console.log(`\nAssessment: ${result.summary.assessment}`);
    console.log(`\nStrengths:`);
    result.summary.strengths.forEach(s => console.log(`  - ${s}`));
    console.log(`\nWeaknesses:`);
    result.summary.weaknesses.forEach(w => console.log(`  - ${w}`));
    console.log(`\nEvaluation Time: ${result.metadata.evaluationTimeMs}ms`);
  } else {
    console.error('Evaluation failed:', result.summary.assessment);
  }
}

main().catch(error => {
  console.error(error instanceof Error ? error.message : 'Example failed.');
  process.exitCode = 1;
});
