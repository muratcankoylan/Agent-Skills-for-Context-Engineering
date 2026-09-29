import { readdirSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { APICallError } from 'ai';
import { MockLanguageModelV1 } from 'ai/test';
import { describe, expect, it, vi } from 'vitest';
import { EvaluatorAgent, JudgeRuntime, LocalAttemptBudget, validateConfig } from '../src/index.js';
import { fixtureRuntime, response } from './fixtures.js';

const request = { system: 'system', prompt: 'prompt' };

describe('one admitted attempt per SDK provider invocation', () => {
  it('denies the default agent even when an ambient API key exists', async () => {
    vi.stubEnv('OPENAI_API_KEY', 'fake-ambient-key');
    try {
      expect(() => validateConfig()).toThrow('disabled');
      await expect(new EvaluatorAgent().chat('hello')).rejects.toThrow('disabled');
    } finally { vi.unstubAllEnvs(); }
  });
  it.each(['maxOutputTokens', 'maxInputBytes', 'timeoutMs', 'maxConcurrent'] as const)('rejects invalid %s without admission', field => {
    for (const invalid of [0, -1, 1.5, NaN, Infinity]) {
      expect(() => fixtureRuntime(['ok'], 1, { [field]: invalid })).toThrow('positive');
    }
  });
  it('reserves before the provider, enforces output cap, preserves temperature zero, and reports model', async () => {
    const fixture = fixtureRuntime(['unused'], 1);
    const model = new MockLanguageModelV1({ modelId: 'specific-model', doGenerate: async input => {
      expect(readdirSync(fixture.directory)).toContain('attempt-1');
      expect(input.maxTokens).toBe(128);
      expect(input.temperature).toBe(0);
      expect(input.abortSignal).toBeDefined();
      return response('bounded');
    } });
    const runtime = new JudgeRuntime({ model, budget: fixture.budget, maxOutputTokens: 128, maxInputBytes: 512, timeoutMs: 1000 });
    const agent = new EvaluatorAgent({ runtime, temperature: 0 });
    expect((await agent.chat('hello')).text).toBe('bounded');
    expect(runtime.modelId).toBe('specific-model');
  });
  it('does not let SDK retry a retryable provider failure or refund the uncertain attempt', async () => {
    const call = vi.fn(async () => { throw new APICallError({ message: 'sensitive-provider-body', url: 'https://invalid.test', requestBodyValues: {}, statusCode: 500, isRetryable: true }); });
    const fixture = fixtureRuntime(['unused'], 1, { model: new MockLanguageModelV1({ doGenerate: call }) });
    await expect(fixture.runtime.generate(request)).rejects.toThrow('reservation retained');
    await expect(fixture.runtime.generate(request)).rejects.toThrow('exhausted');
    expect(call).toHaveBeenCalledTimes(1);
  });
  it('retains a timed-out attempt without retrying', async () => {
    const call = vi.fn(async (input) => new Promise<ReturnType<typeof response>>((_resolve, reject) => {
      input.abortSignal.addEventListener('abort', () => reject(new Error('timeout-secret')), { once: true });
    }));
    const fixture = fixtureRuntime(['unused'], 1, { model: new MockLanguageModelV1({ doGenerate: call }), timeoutMs: 10 });
    await expect(fixture.runtime.generate(request)).rejects.toThrow('reservation retained');
    expect(call).toHaveBeenCalledTimes(1);
    expect(() => new LocalAttemptBudget(fixture.directory, 1).reserve()).toThrow('exhausted');
  });
  it('bounds concurrent callers without oversubscribing the shared cap', async () => {
    const fixture = fixtureRuntime(['ok'], 3, { maxConcurrent: 20 });
    const outcomes = await Promise.allSettled(Array.from({ length: 20 }, () => fixture.runtime.generate(request)));
    expect(outcomes.filter(outcome => outcome.status === 'fulfilled')).toHaveLength(3);
    expect(fixture.calls()).toBe(3);
  });
  it('fails fast on in-flight capacity and does not refund or free an ignored abort', async () => {
    let release!: () => void;
    const call = vi.fn(async () => { await new Promise<void>(resolve => { release = resolve; }); return response('done'); });
    const fixture = fixtureRuntime(['unused'], 2, { model: new MockLanguageModelV1({ doGenerate: call }), timeoutMs: 10 });
    const first = fixture.runtime.generate(request);
    await vi.waitFor(() => expect(call).toHaveBeenCalledTimes(1));
    await new Promise(resolve => setTimeout(resolve, 20));
    await expect(fixture.runtime.generate(request)).rejects.toThrow('concurrency');
    expect(readdirSync(fixture.directory).filter(name => name.startsWith('attempt-'))).toHaveLength(1);
    release();
    await first;
  });
  it('refuses oversized UTF-8 input and corrupt policy before provider execution', async () => {
    const fixture = fixtureRuntime(['ok'], 1, { maxInputBytes: 10 });
    await expect(fixture.runtime.generate({ system: '', prompt: 'é'.repeat(6) })).rejects.toThrow('byte limit');
    expect(fixture.calls()).toBe(0);
    writeFileSync(join(fixture.directory, 'policy.json'), '{');
    await expect(fixture.runtime.generate({ system: '', prompt: 'ok' })).rejects.toThrow();
    expect(fixture.calls()).toBe(0);
  });
});
