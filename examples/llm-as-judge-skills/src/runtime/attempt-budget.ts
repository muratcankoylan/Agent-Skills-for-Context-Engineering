import { closeSync, constants, fstatSync, fsyncSync, lstatSync, mkdirSync, openSync, readFileSync, writeFileSync } from 'node:fs';
import { isAbsolute, join } from 'node:path';

function checkLimit(value: number): void {
  if (!Number.isSafeInteger(value) || value < 0 || value > 100_000) {
    throw new Error('Attempt limit must be an integer from 0 to 100000.');
  }
}

function syncDirectory(directory: string): void {
  const fd = openSync(directory, constants.O_RDONLY | constants.O_DIRECTORY | constants.O_NOFOLLOW);
  try { fsyncSync(fd); } finally { closeSync(fd); }
}

/**
 * A non-refunding attempt cap for cooperating processes on one local POSIX disk.
 * Each exclusive slot creation is persisted BEFORE invoking a provider. No
 * check-then-increment race, expiring lock, retry refund, or daily reset exists.
 * The owner must preserve this private directory; this is not an account cap or
 * protection from a process that can delete/replace the ledger itself.
 */
export class LocalAttemptBudget {
  readonly maxAttempts: number;
  private readonly device: number;
  private readonly inode: number;

  static create(directory: string, maxAttempts: number): LocalAttemptBudget {
    checkLimit(maxAttempts);
    if (!isAbsolute(directory)) throw new Error('Budget directory must be absolute.');
    // Exclusive directory creation: existing/partial state is never reset.
    mkdirSync(directory, { mode: 0o700 });
    const fd = openSync(join(directory, 'policy.json'), 'wx', 0o600);
    try {
      writeFileSync(fd, JSON.stringify({ version: 1, maxAttempts }) + '\n');
      fsyncSync(fd);
    } finally { closeSync(fd); }
    syncDirectory(directory);
    syncDirectory(join(directory, '..'));
    return new LocalAttemptBudget(directory, maxAttempts);
  }

  constructor(private readonly directory: string, maxAttempts: number) {
    checkLimit(maxAttempts);
    if (!isAbsolute(directory)) throw new Error('Budget directory must be absolute.');
    const info = lstatSync(directory);
    if (!info.isDirectory() || (info.mode & 0o077) !== 0) {
      throw new Error('Budget requires a private, non-symlink directory.');
    }
    this.device = info.dev;
    this.inode = info.ino;
    this.maxAttempts = maxAttempts;
    this.checkPolicy();
  }

  private checkPolicy(): void {
    const info = lstatSync(this.directory);
    if (!info.isDirectory() || info.dev !== this.device || info.ino !== this.inode || (info.mode & 0o077) !== 0) {
      throw new Error('Budget directory changed.');
    }
    const fd = openSync(join(this.directory, 'policy.json'), constants.O_RDONLY | constants.O_NOFOLLOW);
    try {
      const stat = fstatSync(fd);
      if (!stat.isFile() || stat.size > 1024 || (stat.mode & 0o077) !== 0) throw new Error('Invalid budget policy.');
      const policy: unknown = JSON.parse(readFileSync(fd, 'utf8'));
      if (JSON.stringify(policy) !== JSON.stringify({ version: 1, maxAttempts: this.maxAttempts })) {
        throw new Error('Budget policy mismatch.');
      }
    } finally { closeSync(fd); }
  }

  reserve(): number {
    this.checkPolicy();
    for (let slot = 1; slot <= this.maxAttempts; slot++) {
      let fd: number;
      try {
        fd = openSync(join(this.directory, `attempt-${slot}`), 'wx', 0o600);
      } catch (error) {
        if ((error as NodeJS.ErrnoException).code === 'EEXIST') continue;
        throw new Error('Attempt reservation failed.');
      }
      // A crash, timeout, parse failure, or fsync failure still consumes this slot.
      try { fsyncSync(fd); } finally { closeSync(fd); }
      syncDirectory(this.directory);
      return slot;
    }
    throw new Error('Attempt budget exhausted.');
  }
}
