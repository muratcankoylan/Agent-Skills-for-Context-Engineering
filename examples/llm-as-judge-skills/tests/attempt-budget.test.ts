import { chmodSync, mkdirSync, readFileSync, readdirSync, renameSync, symlinkSync, writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { spawn } from 'node:child_process';
import { fileURLToPath } from 'node:url';
import { describe, expect, it } from 'vitest';
import { LocalAttemptBudget } from '../src/index.js';
import { fixtureDirectory } from './fixtures.js';

describe('durable local attempt admission', () => {
  it.each([-1, 1.1, NaN, Infinity, 100001])('rejects invalid cap %s', limit => {
    expect(() => LocalAttemptBudget.create(join(fixtureDirectory(), 'budget'), limit)).toThrow();
  });
  it('treats zero as denial, not unlimited', () => {
    const budget = LocalAttemptBudget.create(join(fixtureDirectory(), 'budget'), 0);
    expect(() => budget.reserve()).toThrow('exhausted');
  });
  it('persists consumed attempts across reopened instances and never resets existing state', () => {
    const directory = join(fixtureDirectory(), 'budget');
    const first = LocalAttemptBudget.create(directory, 1);
    expect(first.reserve()).toBe(1);
    expect(() => new LocalAttemptBudget(directory, 1).reserve()).toThrow('exhausted');
    expect(() => LocalAttemptBudget.create(directory, 1)).toThrow();
    expect(() => new LocalAttemptBudget(directory, 2)).toThrow('mismatch');
  });
  it('fails closed for incomplete initialization, corrupt policy, or an occupied slot', () => {
    const directory = join(fixtureDirectory(), 'budget');
    const budget = LocalAttemptBudget.create(directory, 1);
    mkdirSync(join(directory, 'attempt-1'));
    expect(() => budget.reserve()).toThrow('exhausted');
    writeFileSync(join(directory, 'policy.json'), '{');
    expect(() => budget.reserve()).toThrow();
    expect(() => new LocalAttemptBudget(directory, 1)).toThrow();
  });
  it('rejects replaced directories, symlink policies, and non-private ledgers', () => {
    const parent = fixtureDirectory();
    const directory = join(parent, 'budget');
    const budget = LocalAttemptBudget.create(directory, 1);
    const policy = readFileSync(join(directory, 'policy.json'));
    renameSync(directory, join(parent, 'old'));
    LocalAttemptBudget.create(directory, 1);
    expect(() => budget.reserve()).toThrow('changed');
    renameSync(join(directory, 'policy.json'), join(directory, 'original.json'));
    symlinkSync(join(directory, 'original.json'), join(directory, 'policy.json'));
    expect(() => new LocalAttemptBudget(directory, 1)).toThrow();
    chmodSync(directory, 0o755);
    expect(() => new LocalAttemptBudget(directory, 1)).toThrow('private');
    expect(policy.length).toBeGreaterThan(0);
  });
  it('admits exactly three of twelve independent processes sharing one budget', async () => {
    const parent = fixtureDirectory();
    const directory = join(parent, 'budget');
    LocalAttemptBudget.create(directory, 3);
    const worker = fileURLToPath(new URL('./attempt-worker.ts', import.meta.url));
    const outcomes = await Promise.all(Array.from({ length: 12 }, () => new Promise<number | null>((resolve, reject) => {
      const child = spawn(process.execPath, ['--import', 'tsx', worker, directory, '3', parent], { env: {}, stdio: 'ignore' });
      child.on('error', reject);
      child.on('exit', resolve);
    })));
    expect(outcomes.filter(code => code === 0)).toHaveLength(3);
    expect(outcomes.filter(code => code === 2)).toHaveLength(9);
    expect(readdirSync(parent).filter(name => name.startsWith('effect-'))).toHaveLength(3);
    expect(readdirSync(directory).filter(name => name.startsWith('attempt-'))).toHaveLength(3);
  });
});
