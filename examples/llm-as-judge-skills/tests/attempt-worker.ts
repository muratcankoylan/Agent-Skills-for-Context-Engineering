import { writeFileSync } from 'node:fs';
import { join } from 'node:path';
import { LocalAttemptBudget } from '../src/runtime/attempt-budget.js';

try {
  const budget = new LocalAttemptBudget(process.argv[2], Number(process.argv[3]));
  const slot = budget.reserve();
  // Represents a provider effect: only written after successful admission.
  writeFileSync(join(process.argv[4], `effect-${slot}`), String(process.pid), { flag: 'wx' });
} catch {
  process.exitCode = 2;
}
