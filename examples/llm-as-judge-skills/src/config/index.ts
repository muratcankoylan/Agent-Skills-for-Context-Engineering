import 'dotenv/config';

export interface BudgetConfig {
  maxCalls?: number;
  maxTokens?: number;
  maxCostUsd?: number;
  costPer1kInputTokensUsd: number;
  costPer1kOutputTokensUsd: number;
  dryRun: boolean;
}

export interface RetryConfig {
  maxRetries: number;
  baseDelayMs: number;
  maxDelayMs: number;
}

function parseOptionalInt(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const parsed = parseInt(value, 10);
  return Number.isNaN(parsed) || parsed <= 0 ? undefined : parsed;
}

function parseOptionalFloat(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const parsed = parseFloat(value);
  return Number.isNaN(parsed) || parsed <= 0 ? undefined : parsed;
}

export const config = {
  openai: {
    apiKey: process.env.OPENAI_API_KEY || '',
    model: process.env.OPENAI_MODEL || 'gpt-4o'
  },
  anthropic: {
    apiKey: process.env.ANTHROPIC_API_KEY || ''
  },
  budgets: {
    maxCalls: parseOptionalInt(process.env.JUDGE_MAX_CALLS),
    maxTokens: parseOptionalInt(process.env.JUDGE_MAX_TOKENS),
    maxCostUsd: parseOptionalFloat(process.env.JUDGE_MAX_COST_USD),
    costPer1kInputTokensUsd: parseFloat(process.env.JUDGE_COST_PER_1K_INPUT_USD || '0.005'),
    costPer1kOutputTokensUsd: parseFloat(process.env.JUDGE_COST_PER_1K_OUTPUT_USD || '0.015'),
    dryRun: process.env.JUDGE_DRY_RUN === 'true'
  } satisfies BudgetConfig,
  maxRetries: {
    maxRetries: parseInt(process.env.JUDGE_MAX_RETRIES || '3', 10),
    baseDelayMs: parseInt(process.env.JUDGE_RETRY_BASE_DELAY_MS || '1000', 10),
    maxDelayMs: parseInt(process.env.JUDGE_RETRY_MAX_DELAY_MS || '60000', 10)
  } satisfies RetryConfig
};

export interface UsageRecord {
  promptTokens?: number;
  completionTokens?: number;
}

let budgetState = {
  totalCalls: 0,
  totalTokens: 0,
  estimatedCostUsd: 0
};

export function resetBudget(): void {
  budgetState = { totalCalls: 0, totalTokens: 0, estimatedCostUsd: 0 };
}

export function getBudgetState(): Readonly<typeof budgetState> {
  return budgetState;
}

export function recordUsage(usage?: UsageRecord): void {
  budgetState.totalCalls += 1;
  if (!usage) return;
  const promptTokens = usage.promptTokens || 0;
  const completionTokens = usage.completionTokens || 0;
  budgetState.totalTokens += promptTokens + completionTokens;
  const inputCost = promptTokens * config.budgets.costPer1kInputTokensUsd / 1000;
  const outputCost = completionTokens * config.budgets.costPer1kOutputTokensUsd / 1000;
  budgetState.estimatedCostUsd += inputCost + outputCost;
}

export function checkBudget(label?: string): { ok: boolean; reason?: string } {
  const budgets = config.budgets;
  if (budgets.dryRun) {
    return { ok: true };
  }
  if (budgets.maxCalls && budgetState.totalCalls >= budgets.maxCalls) {
    return {
      ok: false,
      reason: `call budget exceeded (${budgetState.totalCalls}/${budgets.maxCalls})${label ? ` at ${label}` : ''}`
    };
  }
  if (budgets.maxTokens && budgetState.totalTokens >= budgets.maxTokens) {
    return {
      ok: false,
      reason: `token budget exceeded (${budgetState.totalTokens}/${budgets.maxTokens})${label ? ` at ${label}` : ''}`
    };
  }
  if (budgets.maxCostUsd && budgetState.estimatedCostUsd >= budgets.maxCostUsd) {
    return {
      ok: false,
      reason: `cost budget exceeded ($${budgetState.estimatedCostUsd.toFixed(4)}/$${budgets.maxCostUsd.toFixed(4)})${label ? ` at ${label}` : ''}`
    };
  }
  return { ok: true };
}

export async function withRetries<T>(
  label: string,
  fn: () => Promise<T>,
  retryConfig: RetryConfig = config.maxRetries
): Promise<T> {
  let lastError: unknown;
  for (let attempt = 0; attempt <= retryConfig.maxRetries; attempt += 1) {
    try {
      return await fn();
    } catch (error) {
      lastError = error;
      const isRetryable =
        error instanceof Error &&
        (error.message.includes('429') ||
          error.message.toLowerCase().includes('rate limit') ||
          error.message.toLowerCase().includes('too many requests') ||
          error.message.toLowerCase().includes('timeout') ||
          error.message.toLowerCase().includes('econnreset') ||
          error.message.toLowerCase().includes('etimedout'));
      if (!isRetryable || attempt >= retryConfig.maxRetries) {
        throw error;
      }
      const delay = Math.min(
        retryConfig.baseDelayMs * 2 ** attempt,
        retryConfig.maxDelayMs
      );
      const jitter = Math.random() * delay;
      console.warn(`[${label}] attempt ${attempt + 1} failed, retrying in ${Math.round(jitter)}ms: ${error instanceof Error ? error.message : String(error)}`);
      await new Promise(resolve => setTimeout(resolve, jitter));
    }
  }
  throw lastError;
}

export function validateConfig(): void {
  if (!config.openai.apiKey) {
    throw new Error('OPENAI_API_KEY is required. Create a .env file with your API key.');
  }
}

