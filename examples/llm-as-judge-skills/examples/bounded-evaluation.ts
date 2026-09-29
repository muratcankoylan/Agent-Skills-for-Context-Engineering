import { createOpenAI } from '@ai-sdk/openai';
import { EvaluatorAgent, JudgeRuntime, LocalAttemptBudget } from '../src/index.js';

/**
 * Explicit construction only: no top-level calls, dotenv import, or key lookup.
 * Provision the budget once with LocalAttemptBudget.create in a trusted parent
 * directory. Reopen it on subsequent runs. Never recreate it to resume a run.
 * This example has an unsupported SDK dependency graph; see README before use.
 */
export function createBoundedEvaluator(apiKey: string, model: string, budgetDirectory: string, maxAttempts: number) {
  if (!apiKey.trim() || !model.trim()) throw new Error('Explicit credentials and model are required.');
  const runtime = new JudgeRuntime({
    model: createOpenAI({ apiKey })(model),
    budget: new LocalAttemptBudget(budgetDirectory, maxAttempts),
    maxOutputTokens: 1024,
    maxInputBytes: 32_000,
    timeoutMs: 30_000,
    maxConcurrent: 1
  });
  return new EvaluatorAgent({ runtime });
}
