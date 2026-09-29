/**
 * Minimal durable filesystem primitives for benchmark run state.
 *
 * The threat boundary is cooperative processes running as the same OS user.
 * Permissions, no-follow opens, inode checks, no-clobber publication, and
 * directory fsyncs prevent accidental races and crash-shaped partial state;
 * they are not a defense against a malicious process with the same UID.
 */

import { createHash, randomUUID, timingSafeEqual } from "node:crypto";
import {
  constants,
  lstatSync,
  realpathSync,
  type BigIntStats,
  type Dirent,
  type Stats,
} from "node:fs";
import {
  chmod,
  link,
  lstat,
  mkdir,
  open,
  opendir,
  unlink,
} from "node:fs/promises";
import { dirname, join, relative, resolve, sep } from "node:path";

export type DurableFsErrorCode =
  | "BOUNDS_INVALID"
  | "DIRECTORY_INVALID"
  | "DIRECTORY_TOO_LARGE"
  | "EXCLUSIVE_TARGET_EXISTS"
  | "FILE_CHANGED"
  | "FILE_INVALID"
  | "FILE_TOO_LARGE"
  | "LOCK_BODY_MISMATCH"
  | "LOCK_RELEASE_REPLAY"
  | "PATH_ESCAPE"
  | "PLATFORM_UNSUPPORTED";

export class DurableFsError extends Error {
  readonly code: DurableFsErrorCode;

  constructor(code: DurableFsErrorCode, message: string, options?: ErrorOptions) {
    super(`[${code}] ${message}`, options);
    this.name = "DurableFsError";
    this.code = code;
  }
}

export interface DurablePathStat {
  readonly kind: "directory" | "file" | "symlink" | "other";
  readonly mode: number;
  readonly size: bigint;
  readonly links: bigint;
  readonly device: bigint;
  readonly inode: bigint;
}

export interface DurableDirectoryEntry {
  readonly name: string;
  readonly kind: "directory" | "file" | "symlink" | "other";
}

export interface DurableFileSystem {
  ensurePrivateDirectory(path: string): Promise<void>;
  /** Implementations must stop enumeration once maximumEntries is exceeded. */
  listDirectory(path: string, maximumEntries: number): Promise<readonly DurableDirectoryEntry[]>;
  statPath(path: string): Promise<DurablePathStat | null>;
  readRegularNoFollow(path: string, maximumBytes: number): Promise<Uint8Array>;
  writeExclusiveDurable(path: string, body: Uint8Array): Promise<void>;
  removeExactDurable(path: string, expectedBody: Uint8Array): Promise<void>;
}

const READ_CHUNK_BYTES = 64 * 1024;
const MAX_LOCK_BYTES = 64 * 1024;
const DEFAULT_MAX_DIRECTORY_ENTRIES = 1_000_000;

export class NodeDurableFileSystem implements DurableFileSystem {
  readonly confinementRoot: string;
  private readonly physicalRoot: string;
  private readonly rootDevice: bigint;
  private readonly rootInode: bigint;

  constructor(confinementRoot: string) {
    this.confinementRoot = resolve(confinementRoot);
    let lexicalInfo: BigIntStats;
    try {
      lexicalInfo = lstatSync(this.confinementRoot, { bigint: true });
    } catch (error) {
      throw new DurableFsError(
        "DIRECTORY_INVALID",
        `durable state root must already exist: ${this.confinementRoot}`,
        { cause: error },
      );
    }
    if (!lexicalInfo.isDirectory() || lexicalInfo.isSymbolicLink()) {
      throw new DurableFsError(
        "DIRECTORY_INVALID",
        `durable state root is not a real directory: ${this.confinementRoot}`,
      );
    }
    try {
      this.physicalRoot = realpathSync.native(this.confinementRoot);
    } catch (error) {
      throw new DurableFsError(
        "DIRECTORY_INVALID",
        `durable state root cannot be resolved: ${this.confinementRoot}`,
        { cause: error },
      );
    }
    const physicalInfo = lstatSync(this.physicalRoot, { bigint: true });
    if (
      !physicalInfo.isDirectory() ||
      physicalInfo.isSymbolicLink() ||
      physicalInfo.dev !== lexicalInfo.dev ||
      physicalInfo.ino !== lexicalInfo.ino
    ) {
      throw new DurableFsError(
        "DIRECTORY_INVALID",
        `durable state root changed while resolving: ${this.confinementRoot}`,
      );
    }
    this.rootDevice = physicalInfo.dev;
    this.rootInode = physicalInfo.ino;
  }

  async ensurePrivateDirectory(path: string): Promise<void> {
    const target = this.confined(path);
    const suffix = relative(this.physicalRoot, target);
    const components = suffix ? suffix.split(sep) : [];
    let current = this.physicalRoot;
    await this.secureRootDirectory();
    for (const component of components) {
      const parent = current;
      current = join(current, component);
      await this.ensureOneDirectory(current, parent);
    }
  }

  async listDirectory(
    path: string,
    maximumEntries = DEFAULT_MAX_DIRECTORY_ENTRIES,
  ): Promise<readonly DurableDirectoryEntry[]> {
    assertMaximumEntries(maximumEntries);
    const confined = this.confined(path);
    await this.assertDirectoryAncestors(confined, false);
    const info = await lstatBigInt(confined, "benchmark state directory");
    if (!info.isDirectory() || info.isSymbolicLink()) {
      throw new DurableFsError("DIRECTORY_INVALID", `cannot list non-directory state path: ${path}`);
    }
    const directory = await opendir(confined);
    const entries: DurableDirectoryEntry[] = [];
    try {
      while (true) {
        const entry = await directory.read();
        if (entry === null) break;
        if (entries.length >= maximumEntries) {
          throw new DurableFsError(
            "DIRECTORY_TOO_LARGE",
            `directory exceeds the ${maximumEntries}-entry limit: ${path}`,
          );
        }
        entries.push({ name: entry.name, kind: direntKind(entry) });
      }
    } finally {
      await directory.close();
    }
    return entries.sort((left, right) => left.name.localeCompare(right.name));
  }

  async statPath(path: string): Promise<DurablePathStat | null> {
    path = this.confined(path);
    await this.assertDirectoryAncestors(path, true);
    let info: BigIntStats;
    try {
      info = await lstat(path, { bigint: true });
    } catch (error) {
      if (isErrno(error, "ENOENT")) return null;
      throw error;
    }
    return {
      kind: statsKind(info),
      mode: Number(info.mode & 0o777n),
      size: info.size,
      links: info.nlink,
      device: info.dev,
      inode: info.ino,
    };
  }

  async readRegularNoFollow(path: string, maximumBytes: number): Promise<Uint8Array> {
    path = this.confined(path);
    await this.assertDirectoryAncestors(path, true);
    assertMaximum(maximumBytes);
    const initial = await lstatBigInt(path, "durable record");
    assertRegularSingleLink(initial, path);
    if (initial.size > BigInt(maximumBytes)) {
      throw new DurableFsError("FILE_TOO_LARGE", `durable record exceeds ${maximumBytes} bytes: ${path}`);
    }

    const flags = constants.O_RDONLY | noFollowFlag();
    let handle;
    try {
      handle = await open(path, flags);
    } catch (error) {
      if (isErrno(error, "ELOOP") || isErrno(error, "ENOENT")) {
        throw new DurableFsError("FILE_CHANGED", `durable record changed before open: ${path}`, {
          cause: error,
        });
      }
      throw error;
    }

    try {
      const before = await handle.stat({ bigint: true });
      assertRegularSingleLink(before, path);
      if (!sameIdentity(initial, before)) {
        throw new DurableFsError("FILE_CHANGED", `durable record changed before stable open: ${path}`);
      }

      const chunks: Buffer[] = [];
      let total = 0;
      while (true) {
        const remaining = maximumBytes + 1 - total;
        const buffer = Buffer.allocUnsafe(Math.min(READ_CHUNK_BYTES, remaining));
        const result = await handle.read(buffer, 0, buffer.length, null);
        if (result.bytesRead === 0) break;
        chunks.push(buffer.subarray(0, result.bytesRead));
        total += result.bytesRead;
        if (total > maximumBytes) {
          throw new DurableFsError(
            "FILE_TOO_LARGE",
            `durable record exceeds ${maximumBytes} bytes: ${path}`,
          );
        }
      }

      const after = await handle.stat({ bigint: true });
      const final = await lstatBigInt(path, "durable record");
      assertRegularSingleLink(after, path);
      assertRegularSingleLink(final, path);
      if (!sameIdentity(before, after) || !sameIdentity(after, final)) {
        throw new DurableFsError("FILE_CHANGED", `durable record changed while reading: ${path}`);
      }
      const body = Buffer.concat(chunks, total);
      if (BigInt(body.length) !== after.size) {
        throw new DurableFsError("FILE_CHANGED", `durable record size changed while reading: ${path}`);
      }
      return body;
    } finally {
      await handle.close();
    }
  }

  async writeExclusiveDurable(path: string, body: Uint8Array): Promise<void> {
    const requestedParent = dirname(path);
    path = this.confined(path);
    const parent = dirname(path);
    await this.ensurePrivateDirectory(requestedParent);
    const targetName = path.slice(parent.length + (parent.endsWith("/") ? 0 : 1));
    const temporary = join(parent, `.${targetName}.${process.pid}.${randomUUID()}.tmp`);
    let handle;
    let published = false;
    try {
      handle = await open(
        temporary,
        constants.O_WRONLY | constants.O_CREAT | constants.O_EXCL | noFollowFlag(),
        0o600,
      );
      const buffer = Buffer.from(body);
      let offset = 0;
      while (offset < buffer.length) {
        const result = await handle.write(buffer, offset, buffer.length - offset, offset);
        if (result.bytesWritten <= 0) {
          throw new DurableFsError("FILE_CHANGED", `zero-byte write while publishing: ${path}`);
        }
        offset += result.bytesWritten;
      }
      await handle.sync();
      await handle.close();
      handle = undefined;
      try {
        await link(temporary, path);
      } catch (error) {
        if (isErrno(error, "EEXIST")) {
          throw new DurableFsError(
            "EXCLUSIVE_TARGET_EXISTS",
            `durable target already exists: ${path}`,
            { cause: error },
          );
        }
        throw error;
      }
      published = true;
      await unlink(temporary);
      await fsyncDirectory(parent);
    } finally {
      if (handle !== undefined) await handle.close().catch(() => undefined);
      if (!published) await unlink(temporary).catch(() => undefined);
    }
  }

  async removeExactDurable(path: string, expectedBody: Uint8Array): Promise<void> {
    const requestedPath = path;
    path = this.confined(path);
    await this.assertDirectoryAncestors(path, true);
    const actual = await this.readRegularNoFollow(
      requestedPath,
      Math.max(MAX_LOCK_BYTES, expectedBody.length),
    );
    const left = Buffer.from(actual);
    const right = Buffer.from(expectedBody);
    if (left.length !== right.length || !timingSafeEqual(left, right)) {
      throw new DurableFsError("LOCK_BODY_MISMATCH", `lock body does not match owner: ${path}`);
    }
    const requestedReleaseDirectory = join(this.confinementRoot, ".released-locks");
    await this.ensurePrivateDirectory(requestedReleaseDirectory);
    const releaseDirectory = this.confined(requestedReleaseDirectory);
    const releaseId = createHash("sha256").update(expectedBody).digest("hex");
    const tombstone = join(releaseDirectory, releaseId);
    try {
      await link(path, tombstone);
    } catch (error) {
      if (isErrno(error, "EEXIST")) {
        throw new DurableFsError(
          "LOCK_RELEASE_REPLAY",
          `lock generation was already released: ${path}`,
          { cause: error },
        );
      }
      throw error;
    }
    const targetInfo = await lstatBigInt(path, "lock target");
    const tombstoneInfo = await lstatBigInt(tombstone, "lock release tombstone");
    if (targetInfo.dev !== tombstoneInfo.dev || targetInfo.ino !== tombstoneInfo.ino) {
      throw new DurableFsError("FILE_CHANGED", `lock changed during release: ${path}`);
    }
    await unlink(path);
    await fsyncDirectory(dirname(path));
  }

  private confined(path: string): string {
    const candidate = resolve(path);
    const suffix = relative(this.confinementRoot, candidate);
    if (suffix === ".." || suffix.startsWith(`..${sep}`) || suffix.startsWith(sep)) {
      throw new DurableFsError("PATH_ESCAPE", `path escapes durable state root: ${path}`);
    }
    return suffix ? join(this.physicalRoot, suffix) : this.physicalRoot;
  }

  private async secureRootDirectory(): Promise<void> {
    await this.assertPhysicalRoot();
    await chmod(this.physicalRoot, 0o700);
    const secured = await this.assertPhysicalRoot();
    if (Number(secured.mode & 0o777n) !== 0o700) {
      throw new DurableFsError(
        "DIRECTORY_INVALID",
        `durable state directory is not mode 0700: ${this.physicalRoot}`,
      );
    }
  }

  private async assertPhysicalRoot(): Promise<BigIntStats> {
    const info = await lstatBigInt(this.physicalRoot, "durable state root");
    if (
      !info.isDirectory() ||
      info.isSymbolicLink() ||
      info.dev !== this.rootDevice ||
      info.ino !== this.rootInode
    ) {
      throw new DurableFsError(
        "DIRECTORY_INVALID",
        `durable state root identity changed: ${this.physicalRoot}`,
      );
    }
    return info;
  }

  private async ensureOneDirectory(path: string, parent: string): Promise<void> {
    await this.createPrivateDirectory(path);
    const info = await lstatBigInt(path, "benchmark state directory");
    if (!info.isDirectory() || info.isSymbolicLink()) {
      throw new DurableFsError(
        "DIRECTORY_INVALID",
        `benchmark state path is not a real directory: ${path}`,
      );
    }
    await this.applyPrivateDirectoryMode(path);
    const secured = await lstatBigInt(path, "benchmark state directory");
    if (!secured.isDirectory() || secured.isSymbolicLink() || Number(secured.mode & 0o777n) !== 0o700) {
      throw new DurableFsError(
        "DIRECTORY_INVALID",
        `benchmark state directory is not mode 0700: ${path}`,
      );
    }
    // Persist both newly created and concurrently observed directories. A
    // process that lost the mkdir race cannot assume the creator completed
    // its fsyncs before this process reaches an external effect.
    await this.syncPrivateDirectory(path);
    await this.syncPrivateDirectory(parent);
  }

  protected async createPrivateDirectory(path: string): Promise<boolean> {
    try {
      await mkdir(path, { mode: 0o700 });
      return true;
    } catch (error) {
      if (isErrno(error, "EEXIST")) return false;
      throw error;
    }
  }

  protected async applyPrivateDirectoryMode(path: string): Promise<void> {
    await chmod(path, 0o700);
  }

  protected async syncPrivateDirectory(path: string): Promise<void> {
    await fsyncDirectory(path);
  }

  private async assertDirectoryAncestors(path: string, excludeLeaf: boolean): Promise<void> {
    const suffix = relative(this.physicalRoot, path);
    const components = suffix ? suffix.split(sep) : [];
    if (excludeLeaf) components.pop();
    let current = this.physicalRoot;
    await this.assertPhysicalRoot();
    for (const component of components) {
      current = join(current, component);
      const info = await lstatBigInt(current, "durable state ancestor");
      if (!info.isDirectory() || info.isSymbolicLink()) {
        throw new DurableFsError(
          "DIRECTORY_INVALID",
          `durable state ancestor is not a real directory: ${current}`,
        );
      }
    }
  }
}

function assertMaximum(maximumBytes: number): void {
  if (!Number.isSafeInteger(maximumBytes) || maximumBytes < 0) {
    throw new DurableFsError("BOUNDS_INVALID", "maximum byte count must be a non-negative safe integer");
  }
}

function assertMaximumEntries(maximumEntries: number): void {
  if (!Number.isSafeInteger(maximumEntries) || maximumEntries < 0) {
    throw new DurableFsError(
      "BOUNDS_INVALID",
      "maximum directory entry count must be a non-negative safe integer",
    );
  }
}

function noFollowFlag(): number {
  if (typeof constants.O_NOFOLLOW !== "number") {
    throw new DurableFsError(
      "PLATFORM_UNSUPPORTED",
      "durable state requires O_NOFOLLOW support",
    );
  }
  return constants.O_NOFOLLOW;
}

async function lstatBigInt(path: string, label: string): Promise<BigIntStats> {
  try {
    return await lstat(path, { bigint: true });
  } catch (error) {
    throw new DurableFsError("FILE_INVALID", `${label} is unavailable: ${path}`, { cause: error });
  }
}

function assertRegularSingleLink(info: BigIntStats, path: string): void {
  if (!info.isFile() || info.isSymbolicLink() || info.nlink !== 1n) {
    throw new DurableFsError(
      "FILE_INVALID",
      `durable record must be a single-link regular file: ${path}`,
    );
  }
}

function sameIdentity(left: BigIntStats, right: BigIntStats): boolean {
  return (
    left.dev === right.dev &&
    left.ino === right.ino &&
    left.mode === right.mode &&
    left.nlink === right.nlink &&
    left.size === right.size &&
    left.mtimeNs === right.mtimeNs &&
    left.ctimeNs === right.ctimeNs
  );
}

function statsKind(info: Stats | BigIntStats): DurablePathStat["kind"] {
  if (info.isSymbolicLink()) return "symlink";
  if (info.isDirectory()) return "directory";
  if (info.isFile()) return "file";
  return "other";
}

function direntKind(entry: Dirent): DurableDirectoryEntry["kind"] {
  if (entry.isSymbolicLink()) return "symlink";
  if (entry.isDirectory()) return "directory";
  if (entry.isFile()) return "file";
  return "other";
}

async function fsyncDirectory(path: string): Promise<void> {
  const handle = await open(path, constants.O_RDONLY | directoryFlag());
  try {
    await handle.sync();
  } finally {
    await handle.close();
  }
}

function directoryFlag(): number {
  return typeof constants.O_DIRECTORY === "number" ? constants.O_DIRECTORY : 0;
}

function isErrno(error: unknown, code: string): error is NodeJS.ErrnoException {
  return error instanceof Error && (error as NodeJS.ErrnoException).code === code;
}
