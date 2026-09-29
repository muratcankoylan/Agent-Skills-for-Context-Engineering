/**
 * Rubric Generation Example
 * 
 * Demonstrates how to generate evaluation rubrics for custom criteria.
 * 
 * Run: npx tsx examples/generate-rubric.ts
 */

import { EvaluatorAgent } from '../src/agents/evaluator.js';
import { validateConfig } from '../src/config/index.js';

async function main() {
  validateConfig();

  const agent = new EvaluatorAgent();

  console.log('=== Rubric Generation Example ===\n');

  // Generate a rubric for code review
  const result = await agent.generateRubric({
    criterionName: 'Code Readability',
    criterionDescription: 'How easy the code is to read, understand, and maintain',
    scale: '1-5',
    domain: 'software engineering',
    includeExamples: true,
    strictness: 'balanced'
  });

  if (result.success) {
    console.log(`Criterion: ${result.criterion.name}`);
    console.log(`Description: ${result.criterion.description}`);
    console.log(`Scale: ${result.scale.min}-${result.scale.max}`);
    console.log(`Domain: ${result.metadata.domain || 'General'}`);
    console.log(`Strictness: ${result.metadata.strictness}`);

    console.log('\n--- Score Levels ---\n');
    result.levels.forEach(level => {
      console.log(`[${level.score}] ${level.label}`);
      console.log(`    ${level.description}`);
      console.log(`    Characteristics:`);
      level.characteristics.forEach(c => console.log(`      - ${c}`));
      if (level.example) {
        console.log(`    Example: ${level.example.slice(0, 100)}...`);
      }
      console.log();
    });

    console.log('--- Scoring Guidelines ---');
    result.scoringGuidelines.forEach((g, i) => {
      console.log(`${i + 1}. ${g}`);
    });

    console.log('\n--- Edge Cases ---');
    result.edgeCases.forEach(ec => {
      console.log(`\nSituation: ${ec.situation}`);
      console.log(`Guidance: ${ec.guidance}`);
    });

    console.log(`\nGeneration Time: ${result.metadata.generationTimeMs}ms`);
  } else {
    console.error('Rubric generation failed');
  }
}

main().catch(error => {
  console.error(error instanceof Error ? error.message : 'Example failed.');
  process.exitCode = 1;
});
