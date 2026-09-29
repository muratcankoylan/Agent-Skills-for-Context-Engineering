import { generateText, type LanguageModel } from 'ai';
import { LocalAttemptBudget } from './attempt-budget.js';

export interface JudgeRuntimeOptions {
  model: LanguageModel;
  budget: LocalAttemptBudget;
  maxOutputTokens: number;
  maxInputBytes: number;
  timeoutMs: number;
  /** Per runtime instance. Attempt admission is shared across ledger users. */
  maxConcurrent?: number;
}

export class JudgeRuntime {
  private readonly options: Readonly<JudgeRuntimeOptions>;
  private inFlight = 0;

  constructor(options: JudgeRuntimeOptions) {
    if (!options.model || options.model.specificationVersion !== 'v1' ||
        typeof options.model.modelId !== 'string' || !options.model.modelId ||
        typeof options.model.doGenerate !== 'function') {
      throw new Error('An explicit compatible SDK model is required.');
    }
    for (const [name, value] of Object.entries({
      maxOutputTokens: options.maxOutputTokens, maxInputBytes: options.maxInputBytes,
      timeoutMs: options.timeoutMs, maxConcurrent: options.maxConcurrent ?? 1
    })) {
      if (!Number.isSafeInteger(value) || value <= 0 || value > 2_147_483_647) {
        throw new Error(`${name} must be a positive bounded integer.`);
      }
    }
    if (!(options.budget instanceof LocalAttemptBudget)) throw new Error('A local attempt budget is required.');
    this.options = Object.freeze({ ...options, maxConcurrent: options.maxConcurrent ?? 1 });
  }

  get modelId(): string { return this.options.model.modelId; }

  async generate(input: { system: string; prompt: string; temperature?: number }) {
    const { budget, model, maxInputBytes, maxOutputTokens, timeoutMs, maxConcurrent } = this.options;
    const temperature = input.temperature ?? 0.3;
    if (!Number.isFinite(temperature) || temperature < 0 || temperature > 2) throw new Error('Invalid temperature.');
    if (Buffer.byteLength(input.system, 'utf8') + Buffer.byteLength(input.prompt, 'utf8') > maxInputBytes) {
      throw new Error('Judge input exceeds byte limit.');
    }
    if (this.inFlight >= maxConcurrent!) throw new Error('Judge concurrency limit reached.');
    budget.reserve();
    this.inFlight++;
    try {
      const result = await generateText({
        model, system: input.system, prompt: input.prompt, temperature,
        maxTokens: maxOutputTokens,
        maxRetries: 0,
        maxSteps: 1,
        experimental_continueSteps: false,
        abortSignal: AbortSignal.timeout(timeoutMs),
        experimental_telemetry: { isEnabled: false, recordInputs: false, recordOutputs: false }
      });
      return { text: result.text, usage: result.usage };
    } catch {
      // Provider errors can contain request bodies/headers. Do not reflect them.
      throw new Error('Judge provider attempt failed; reservation retained.');
    } finally {
      // A timeout is not a refund and a provider that ignores abort stays in flight.
      this.inFlight--;
    }
  }
}

export function requireJudgeRuntime(runtime?: JudgeRuntime): JudgeRuntime {
  if (!(runtime instanceof JudgeRuntime)) {
    throw new Error('Automatic live execution is disabled. Supply an explicit bounded JudgeRuntime.');
  }
  return runtime;
}
