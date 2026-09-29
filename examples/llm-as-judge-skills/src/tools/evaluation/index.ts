export { directScoreTool, executeDirectScore, DirectScoreInputSchema, DirectScoreOutputSchema } from './direct-score.js';
export type { DirectScoreInput, DirectScoreOutput } from './direct-score.js';

export { pairwiseCompareTool, executePairwiseCompare, PairwiseCompareInputSchema, PairwiseCompareOutputSchema } from './pairwise-compare.js';
export type { PairwiseCompareInput, PairwiseCompareOutput } from './pairwise-compare.js';

export { generateRubricTool, executeGenerateRubric, GenerateRubricInputSchema, GenerateRubricOutputSchema } from './generate-rubric.js';
export type { GenerateRubricInput, GenerateRubricOutput } from './generate-rubric.js';
import { tool } from 'ai';
import { JudgeRuntime } from '../../runtime/judge-runtime.js';
import { DirectScoreInputSchema, executeDirectScore } from './direct-score.js';
import { PairwiseCompareInputSchema, executePairwiseCompare } from './pairwise-compare.js';
import { GenerateRubricInputSchema, executeGenerateRubric } from './generate-rubric.js';

/** Bind every tool to the same authority; SDK tool-call options are not a runtime. */
export function createEvaluationTools(runtime: JudgeRuntime) {
  return {
    directScore: tool({ description: 'Score a response against criteria.', parameters: DirectScoreInputSchema, execute: input => executeDirectScore(input, runtime) }),
    pairwiseCompare: tool({ description: 'Compare responses with position swapping.', parameters: PairwiseCompareInputSchema, execute: input => executePairwiseCompare(input, runtime) }),
    generateRubric: tool({ description: 'Generate a rubric for an evaluation criterion.', parameters: GenerateRubricInputSchema, execute: input => executeGenerateRubric(input, runtime) })
  };
}

