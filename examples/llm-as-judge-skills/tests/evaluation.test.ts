import { describe, expect, it } from 'vitest';
import { EvaluatorAgent, createEvaluationTools, executeDirectScore, executeGenerateRubric, executePairwiseCompare, type PairwiseCompareInput } from '../src/index.js';
import { fixtureRuntime, pairwise, rubric, score } from './fixtures.js';

const pair: PairwiseCompareInput = { responseA: 'a', responseB: 'b', prompt: 'p', criteria: ['quality'], swapPositions: true, allowTie: true };
const direct = { response: 'answer', prompt: 'p', criteria: [{ name: 'quality', description: 'quality', weight: 1 }] };
const generate = { criterionName: 'quality', criterionDescription: 'quality', scale: '1-5' as const, strictness: 'balanced' as const, includeExamples: false };

describe('all evaluation paths share the guarded runtime', () => {
  it('returns unsuccessful results without an explicit runtime', async () => {
    expect((await executeDirectScore(direct)).success).toBe(false);
    expect((await executePairwiseCompare(pair)).success).toBe(false);
    expect((await executeGenerateRubric(generate)).success).toBe(false);
  });
  it('does not start the second pairwise pass when only one attempt is available', async () => {
    const fixture = fixtureRuntime([pairwise('A')], 1);
    expect((await executePairwiseCompare(pair, fixture.runtime)).success).toBe(false);
    expect(fixture.calls()).toBe(1);
  });
  it('completes swapped comparison with exactly two admissions', async () => {
    const fixture = fixtureRuntime([pairwise('A'), pairwise('B')], 2);
    const result = await executePairwiseCompare(pair, fixture.runtime);
    expect(result.success).toBe(true);
    expect(result.winner).toBe('A');
    expect(result.positionConsistency?.consistent).toBe(true);
    expect(fixture.calls()).toBe(2);
    expect(result.metadata.model).toBe('offline-fixture');
  });
  it('uses one admission for comparison without swapping', async () => {
    const fixture = fixtureRuntime([pairwise('A')], 1);
    expect((await executePairwiseCompare({ ...pair, swapPositions: false }, fixture.runtime)).success).toBe(true);
    expect(fixture.calls()).toBe(1);
  });
  it('aligns returned criteria by identity, not response array order', async () => {
    const first = JSON.parse(pairwise('A', ['quality', 'clarity']));
    first.comparison[1].winner = 'B';
    const second = JSON.parse(pairwise('B', ['clarity', 'quality']));
    second.comparison[0].winner = 'A';
    const fixture = fixtureRuntime([JSON.stringify(first), JSON.stringify(second)], 2);
    const result = await executePairwiseCompare({ ...pair, criteria: ['quality', 'clarity'] }, fixture.runtime);
    expect(result.comparison.map(item => item.winner)).toEqual(['A', 'B']);
  });
  it('does not invent an allowed tie when callers require a winner', async () => {
    const fixture = fixtureRuntime([pairwise('A'), pairwise('A')], 2);
    expect((await executePairwiseCompare({ ...pair, allowTie: false }, fixture.runtime)).success).toBe(false);
  });
  it.each(['{', '{}', pairwise('A', ['unexpected'])])('rejects malformed/mismatched first pass without another call: %s', text => {
    const fixture = fixtureRuntime([text], 2);
    return executePairwiseCompare(pair, fixture.runtime).then(result => {
      expect(result.success).toBe(false);
      expect(fixture.calls()).toBe(1);
    });
  });
  it('preserves zero criterion weight and calculates finite weighted score', async () => {
    const fixture = fixtureRuntime([score(['quality', 'ignored'], [4, 1])], 1);
    const result = await executeDirectScore({ ...direct, criteria: [...direct.criteria, { name: 'ignored', description: 'ignore', weight: 0 }] }, fixture.runtime);
    expect(result.success).toBe(true);
    expect(result.weightedScore).toBe(4);
    expect(result.overallScore).toBe(2.5);
  });
  it('validates zero-total and duplicate criteria before spending', async () => {
    const fixture = fixtureRuntime([score()], 1);
    await expect(executeDirectScore({ ...direct, criteria: [{ ...direct.criteria[0], weight: 0 }] }, fixture.runtime)).rejects.toThrow('positive');
    await expect(executePairwiseCompare({ ...pair, criteria: ['quality', 'quality'] }, fixture.runtime)).rejects.toThrow('unique');
    expect(fixture.calls()).toBe(0);
  });
  it.each([score(['wrong']), score(['quality'], [6]), score([], [])])('rejects invalid score output without retry: %s', text => {
    const fixture = fixtureRuntime([text], 1);
    return executeDirectScore(direct, fixture.runtime).then(result => {
      expect(result.success).toBe(false);
      expect(fixture.calls()).toBe(1);
    });
  });
  it('accepts null examples as absent and rejects duplicate rubric levels', async () => {
    const invalid = JSON.parse(rubric());
    invalid.levels[1].score = 1;
    const fixture = fixtureRuntime([rubric(), JSON.stringify(invalid)], 2);
    expect((await executeGenerateRubric(generate, fixture.runtime)).success).toBe(true);
    expect((await executeGenerateRubric(generate, fixture.runtime)).success).toBe(false);
    expect(fixture.calls()).toBe(2);
  });
  it('runs generated-rubric workflow sequentially and includes every criterion rubric', async () => {
    const fixture = fixtureRuntime([rubric('quality'), rubric('clarity'), score(['quality', 'clarity'], [4, 5])], 3);
    const agent = new EvaluatorAgent({ runtime: fixture.runtime });
    const result = await agent.evaluateWithGeneratedRubric('answer', 'prompt', [{ name: 'quality', description: 'quality' }, { name: 'clarity', description: 'clarity' }]);
    expect(result.success).toBe(true);
    expect(fixture.calls()).toBe(3);
    expect(fixture.prompts[2]).toContain('quality-1');
    expect(fixture.prompts[2]).toContain('clarity-1');
  });
  it('stops the workflow if a required rubric is invalid or denied', async () => {
    const fixture = fixtureRuntime(['{}', rubric()], 2);
    const agent = new EvaluatorAgent({ runtime: fixture.runtime });
    await expect(agent.evaluateWithGeneratedRubric('a', 'p', direct.criteria)).rejects.toThrow('not attempted');
    expect(fixture.calls()).toBe(1);
  });
  it('binds all SDK tools and chat to one shared attempt authority', async () => {
    const fixture = fixtureRuntime([score(), pairwise(), rubric(), 'chat'], 4);
    const tools = createEvaluationTools(fixture.runtime);
    const options = { toolCallId: 'test', messages: [] };
    expect((await tools.directScore.execute!(direct, options)).success).toBe(true);
    expect((await tools.pairwiseCompare.execute!({ ...pair, swapPositions: false }, options)).success).toBe(true);
    expect((await tools.generateRubric.execute!(generate, options)).success).toBe(true);
    const agent = new EvaluatorAgent({ runtime: fixture.runtime });
    expect((await agent.chat('hello')).text).toBe('chat');
    await expect(agent.chat('again')).rejects.toThrow('exhausted');
    expect(fixture.calls()).toBe(4);
  });
  it('validates workflow criteria before generating any rubrics', async () => {
    const fixture = fixtureRuntime([rubric()], 1);
    const agent = new EvaluatorAgent({ runtime: fixture.runtime });
    await expect(agent.evaluateWithGeneratedRubric('a', 'p', [{ name: 'quality', description: 'q', weight: -1 }])).rejects.toThrow();
    await expect(agent.evaluateWithGeneratedRubric('a', 'p', [{ name: 'quality', description: 'q', weight: 0 }])).rejects.toThrow('positive');
    expect(fixture.calls()).toBe(0);
  });
});
