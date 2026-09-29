import { mkdtempSync, rmSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';
import { afterEach } from 'vitest';
import { MockLanguageModelV1 } from 'ai/test';
import { JudgeRuntime, LocalAttemptBudget, type JudgeRuntimeOptions } from '../src/index.js';

const directories: string[] = [];
export function fixtureDirectory(): string {
  const directory = mkdtempSync(join(tmpdir(), 'judge-gate-test-'));
  directories.push(directory);
  return directory;
}
afterEach(() => { for (const directory of directories.splice(0)) rmSync(directory, { recursive: true }); });

export function response(text: string) {
  return { text, finishReason: 'stop' as const, usage: { promptTokens: 1, completionTokens: 1 }, rawCall: { rawPrompt: null, rawSettings: {} } };
}

export function fixtureRuntime(texts: string[], attempts = 20, options: Partial<JudgeRuntimeOptions> = {}) {
  let calls = 0;
  const prompts: string[] = [];
  const directory = join(fixtureDirectory(), 'budget');
  const budget = LocalAttemptBudget.create(directory, attempts);
  const model = new MockLanguageModelV1({
    modelId: 'offline-fixture',
    doGenerate: async input => {
      prompts.push(JSON.stringify(input.prompt));
      return response(texts[Math.min(calls++, texts.length - 1)]);
    }
  });
  const runtime = new JudgeRuntime({ model, budget, maxOutputTokens: 512, maxInputBytes: 32_000, timeoutMs: 1000, ...options });
  return { runtime, budget, directory, prompts, calls: () => calls };
}

export function pairwise(winner: 'A' | 'B' | 'TIE' = 'A', criteria = ['quality']) {
  return JSON.stringify({
    result: { winner, confidence: 0.8 },
    comparison: criteria.map(criterion => ({ criterion, winner, aAssessment: 'a', bAssessment: 'b', reasoning: 'evidence' })),
    analysis: { responseA: { strengths: ['a'], weaknesses: [] }, responseB: { strengths: ['b'], weaknesses: [] } }
  });
}

export function score(criteria = ['quality'], values = [4]) {
  return JSON.stringify({ scores: criteria.map((criterion, index) => ({ criterion, score: values[index], evidence: ['quote'], justification: 'evidence', improvement: 'clearer' })), summary: { assessment: 'good', strengths: ['a'], weaknesses: [], priorities: [] } });
}

export function rubric(prefix = 'quality') {
  return JSON.stringify({ levels: Array.from({ length: 5 }, (_, index) => ({ score: index + 1, label: 'level', description: `${prefix}-${index + 1}`, characteristics: ['specific'], example: null })), scoringGuidelines: ['evidence'], edgeCases: [] });
}
