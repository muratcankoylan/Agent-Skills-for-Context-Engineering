/**
 * Fail-closed source and input capture for benchmark run manifests.
 *
 * The boundary protects against accidental worktree changes, corrupt inputs,
 * and cooperative concurrent writers. A malicious process running as the same
 * OS user can modify this process or race pathname resolution and is outside
 * the threat model.
 */

import { createHash } from "node:crypto";
import {
  closeSync,
  constants,
  fstatSync,
  lstatSync,
  openSync,
  readSync,
  realpathSync,
} from "node:fs";
import { resolve } from "node:path";
import { spawnSync } from "node:child_process";

export interface RepositoryCapture {
  readonly commit: string;
  readonly tree: string;
  readonly objectFormat: "sha1" | "sha256";
}

export interface StableFileCapture {
  readonly bytes: Buffer;
  readonly size: number;
  readonly digest: string;
}

export interface ExactNamedInputCapture {
  readonly repository: RepositoryCapture;
  readonly inputs: Readonly<Record<string, StableFileCapture>>;
}

export interface GitCommandResult {
  readonly status: number;
  readonly stdout: Buffer;
  readonly stderr: Buffer;
}

export type GitCommandRunner = (
  repoRoot: string,
  arguments_: readonly string[],
) => GitCommandResult;

export interface SourceFreezeHooks {
  /** Runs after the first clean repository capture and before any input read. */
  readonly afterInitialRepositoryCapture?: () => void;
  /** Runs after every input has been read once and before the verification pass. */
  readonly afterFirstInputPass?: () => void;
  /** Runs after both input passes and before the final clean repository capture. */
  readonly beforeFinalRepositoryCapture?: () => void;
}

export interface ExactNamedInputOptions {
  readonly commandRunner?: GitCommandRunner;
  readonly hooks?: SourceFreezeHooks;
  readonly maximumBytesPerInput?: number;
}

export class SourceFreezeError extends Error {
  readonly code: string;

  constructor(
    code: string,
    message: string,
  ) {
    super(message);
    this.name = "SourceFreezeError";
    this.code = code;
  }
}

export const DEFAULT_MAXIMUM_INPUT_BYTES = 8 * 1024 * 1024;

const GIT_BASE_ARGUMENTS = [
  "-c",
  "core.fsmonitor=false",
  "-c",
  "core.untrackedCache=false",
  "-c",
  "submodule.recurse=false",
] as const;
const READ_CHUNK_BYTES = 64 * 1024;
const OBJECT_ID = /^[0-9a-f]{40}(?:[0-9a-f]{24})?$/;
const VERIFIED_EXACT_CAPTURES = new WeakSet<object>();

/**
 * Capture an exact clean Git commit/tree pair.
 *
 * Staged, unstaged, unmerged, and non-ignored untracked entries are rejected.
 * Index optimizations that can hide working-tree mutations are also rejected.
 */
export function captureCleanRepository(
  repoRoot: string,
  commandRunner: GitCommandRunner = defaultGitCommandRunner,
): RepositoryCapture {
  const lexicalRoot = resolve(repoRoot);
  let rootInfo;
  try {
    rootInfo = lstatSync(lexicalRoot, { bigint: true });
  } catch (error) {
    throw freezeError("REPOSITORY_INVALID", `Repository root is unavailable: ${lexicalRoot}`, error);
  }
  if (!rootInfo.isDirectory() || rootInfo.isSymbolicLink()) {
    throw new SourceFreezeError(
      "REPOSITORY_INVALID",
      `Repository root must be a real directory: ${lexicalRoot}`,
    );
  }

  const canonicalRoot = realpathSync(lexicalRoot);
  const topLevel = gitText(
    runGit(canonicalRoot, ["rev-parse", "--show-toplevel"], commandRunner),
    "REPOSITORY_INVALID",
    "Git could not resolve the repository root",
  );
  if (realpathSync(topLevel) !== canonicalRoot) {
    throw new SourceFreezeError(
      "REPOSITORY_INVALID",
      `Expected repository root ${canonicalRoot}, but Git resolved ${topLevel}`,
    );
  }

  const before = readRepositoryIdentity(canonicalRoot, commandRunner);
  assertRepositoryState(canonicalRoot, commandRunner);
  const after = readRepositoryIdentity(canonicalRoot, commandRunner);
  assertRepositoryState(canonicalRoot, commandRunner);
  if (
    before.commit !== after.commit ||
    before.tree !== after.tree ||
    before.objectFormat !== after.objectFormat
  ) {
    throw new SourceFreezeError(
      "REPOSITORY_CHANGED",
      "Repository HEAD changed during the clean-source capture",
    );
  }
  return Object.freeze(after);
}

/** Read one regular, single-link file through a stable non-following descriptor. */
export function stableReadRegularFile(path: string, maximumBytes: number): StableFileCapture {
  requireMaximumBytes(maximumBytes);
  const lexicalPath = resolve(path);
  let initial;
  try {
    initial = lstatSync(lexicalPath, { bigint: true });
  } catch (error) {
    throw freezeError("INPUT_UNAVAILABLE", `Input is unavailable: ${lexicalPath}`, error);
  }
  assertSupportedFile(initial, maximumBytes, lexicalPath, "INPUT_UNSUPPORTED");

  if (typeof constants.O_NOFOLLOW !== "number") {
    throw new SourceFreezeError(
      "PLATFORM_UNSUPPORTED",
      "The runtime does not expose O_NOFOLLOW for stable input capture",
    );
  }

  let descriptor: number;
  try {
    descriptor = openSync(lexicalPath, constants.O_RDONLY | constants.O_NOFOLLOW);
  } catch (error) {
    throw freezeError("INPUT_CHANGED", `Input could not be opened without following links: ${lexicalPath}`, error);
  }

  let before;
  let after;
  const chunks: Buffer[] = [];
  let total = 0;
  try {
    before = fstatSync(descriptor, { bigint: true });
    assertSupportedFile(before, maximumBytes, lexicalPath, "INPUT_UNSUPPORTED");
    if (!sameFileIdentity(initial, before)) {
      throw new SourceFreezeError(
        "INPUT_CHANGED",
        `Input changed before its stable open: ${lexicalPath}`,
      );
    }

    while (true) {
      const remaining = maximumBytes + 1 - total;
      if (remaining <= 0) {
        throw new SourceFreezeError(
          "INPUT_TOO_LARGE",
          `Input exceeds ${maximumBytes} bytes: ${lexicalPath}`,
        );
      }
      const buffer = Buffer.allocUnsafe(Math.min(READ_CHUNK_BYTES, remaining));
      const count = readSync(descriptor, buffer, 0, buffer.length, null);
      if (count === 0) break;
      chunks.push(buffer.subarray(0, count));
      total += count;
      if (total > maximumBytes) {
        throw new SourceFreezeError(
          "INPUT_TOO_LARGE",
          `Input exceeds ${maximumBytes} bytes: ${lexicalPath}`,
        );
      }
    }
    after = fstatSync(descriptor, { bigint: true });
  } finally {
    closeSync(descriptor);
  }

  let final;
  try {
    final = lstatSync(lexicalPath, { bigint: true });
  } catch (error) {
    throw freezeError("INPUT_CHANGED", `Input disappeared during its stable read: ${lexicalPath}`, error);
  }
  assertSupportedFile(final, maximumBytes, lexicalPath, "INPUT_CHANGED");
  if (
    !sameFileIdentity(before, after) ||
    !sameFileIdentity(after, final) ||
    BigInt(total) !== after.size
  ) {
    throw new SourceFreezeError("INPUT_CHANGED", `Input changed during its stable read: ${lexicalPath}`);
  }

  const bytes = Buffer.concat(chunks, total);
  return Object.freeze({
    bytes,
    size: bytes.length,
    digest: sha256(bytes),
  });
}

/**
 * Capture an exact logical-name-to-input map between two clean repository
 * captures. Absolute source paths are intentionally omitted from the result.
 */
export function captureExactNamedInputs(
  repoRoot: string,
  inputPaths: Readonly<Record<string, string>>,
  options: ExactNamedInputOptions = {},
): ExactNamedInputCapture {
  const names = validateInputMap(inputPaths);
  const maximumBytes = options.maximumBytesPerInput ?? DEFAULT_MAXIMUM_INPUT_BYTES;
  requireMaximumBytes(maximumBytes);
  const runner = options.commandRunner ?? defaultGitCommandRunner;
  const mayAuthorizeConstruction = options.commandRunner === undefined;

  const initialRepository = captureCleanRepository(repoRoot, runner);
  options.hooks?.afterInitialRepositoryCapture?.();
  const firstPass = readNamedInputs(names, inputPaths, maximumBytes);
  options.hooks?.afterFirstInputPass?.();
  const secondPass = readNamedInputs(names, inputPaths, maximumBytes);
  assertExactInputCaptures(firstPass, secondPass);
  options.hooks?.beforeFinalRepositoryCapture?.();
  const finalRepository = captureCleanRepository(repoRoot, runner);
  if (
    initialRepository.commit !== finalRepository.commit ||
    initialRepository.tree !== finalRepository.tree ||
    initialRepository.objectFormat !== finalRepository.objectFormat
  ) {
    throw new SourceFreezeError(
      "REPOSITORY_CHANGED",
      "Repository identity changed while named inputs were captured",
    );
  }

  const capture = Object.freeze({
    repository: finalRepository,
    inputs: firstPass,
  });
  // An injected command runner is a test seam and can synthesize arbitrary
  // Git output. Its captures remain useful for boundary tests, but never gain
  // authority to construct durable manifests.
  if (mayAuthorizeConstruction) VERIFIED_EXACT_CAPTURES.add(capture);
  return capture;
}

/**
 * Construction-time authenticity guard for records derived in this process.
 * Persisted captures remain independently revalidated with
 * `revalidateExactNamedInputs`; they do not acquire construction authority by
 * deserialization alone.
 */
export function assertVerifiedExactNamedInputCapture(
  capture: ExactNamedInputCapture,
): void {
  if (!VERIFIED_EXACT_CAPTURES.has(capture)) {
    throw new SourceFreezeError(
      "CAPTURE_UNVERIFIED",
      "Named-input capture was not produced by this process's verified capture boundary",
    );
  }
  validateCapturedInputSet(capture);
}

/** Re-capture and compare the exact logical input set without trusting paths stored in state. */
export function revalidateExactNamedInputs(
  repoRoot: string,
  inputPaths: Readonly<Record<string, string>>,
  expected: ExactNamedInputCapture,
  options: ExactNamedInputOptions = {},
): void {
  validateCapturedInputSet(expected);
  const actual = captureExactNamedInputs(repoRoot, inputPaths, options);
  if (
    actual.repository.commit !== expected.repository.commit ||
    actual.repository.tree !== expected.repository.tree ||
    actual.repository.objectFormat !== expected.repository.objectFormat
  ) {
    throw new SourceFreezeError(
      "REPOSITORY_CHANGED",
      "Repository identity no longer matches the captured source",
    );
  }
  assertExactInputCaptures(expected.inputs, actual.inputs);
}

function readNamedInputs(
  names: readonly string[],
  inputPaths: Readonly<Record<string, string>>,
  maximumBytes: number,
): Readonly<Record<string, StableFileCapture>> {
  const captures: Record<string, StableFileCapture> = Object.create(null) as Record<
    string,
    StableFileCapture
  >;
  for (const name of names) {
    captures[name] = stableReadRegularFile(inputPaths[name] as string, maximumBytes);
  }
  return Object.freeze(captures);
}

function assertExactInputCaptures(
  expected: Readonly<Record<string, StableFileCapture>>,
  actual: Readonly<Record<string, StableFileCapture>>,
): void {
  const expectedNames = Object.keys(expected).sort();
  const actualNames = Object.keys(actual).sort();
  if (
    expectedNames.length !== actualNames.length ||
    expectedNames.some((name, index) => name !== actualNames[index])
  ) {
    throw new SourceFreezeError("INPUT_SET_CHANGED", "Named input set changed during capture");
  }
  for (const name of expectedNames) {
    const left = expected[name] as StableFileCapture;
    const right = actual[name] as StableFileCapture;
    if (
      left.size !== left.bytes.length ||
      left.digest !== sha256(left.bytes) ||
      left.size !== right.size ||
      left.digest !== right.digest ||
      !left.bytes.equals(right.bytes)
    ) {
      throw new SourceFreezeError("INPUT_CHANGED", `Named input changed during capture: ${name}`);
    }
  }
}

function validateCapturedInputSet(capture: ExactNamedInputCapture): void {
  if (!capture || typeof capture !== "object") {
    throw new SourceFreezeError("CAPTURE_INVALID", "Expected named-input capture is invalid");
  }
  if (
    (capture.repository.objectFormat !== "sha1" &&
      capture.repository.objectFormat !== "sha256") ||
    !isObjectIdForFormat(capture.repository.commit, capture.repository.objectFormat) ||
    !isObjectIdForFormat(capture.repository.tree, capture.repository.objectFormat)
  ) {
    throw new SourceFreezeError("CAPTURE_INVALID", "Expected repository identity is invalid");
  }
  assertExactInputCaptures(capture.inputs, capture.inputs);
}

function validateInputMap(inputPaths: Readonly<Record<string, string>>): string[] {
  if (!inputPaths || typeof inputPaths !== "object" || Array.isArray(inputPaths)) {
    throw new SourceFreezeError("INPUT_SET_INVALID", "Named inputs must be an object map");
  }
  const names = Object.keys(inputPaths).sort();
  for (const name of names) {
    if (!name.trim() || /[\u0000-\u001f\u007f]/u.test(name)) {
      throw new SourceFreezeError("INPUT_SET_INVALID", "Input names must be non-empty printable strings");
    }
    const path = inputPaths[name];
    if (typeof path !== "string" || !path.trim()) {
      throw new SourceFreezeError("INPUT_SET_INVALID", `Input path is invalid for ${name}`);
    }
  }
  return names;
}

function readRepositoryIdentity(
  root: string,
  runner: GitCommandRunner,
): RepositoryCapture {
  const commit = gitText(
    runGit(root, ["rev-parse", "--verify", "HEAD^{commit}"], runner),
    "REPOSITORY_INVALID",
    "Git could not resolve HEAD",
  );
  const tree = gitText(
    runGit(root, ["rev-parse", "--verify", "HEAD^{tree}"], runner),
    "REPOSITORY_INVALID",
    "Git could not resolve the HEAD tree",
  );
  const objectFormat = gitText(
    runGit(root, ["rev-parse", "--show-object-format"], runner),
    "REPOSITORY_INVALID",
    "Git could not resolve the object format",
  );
  if (objectFormat !== "sha1" && objectFormat !== "sha256") {
    throw new SourceFreezeError(
      "REPOSITORY_INVALID",
      `Git returned an unsupported object format ${JSON.stringify(objectFormat)}`,
    );
  }
  if (!isObjectIdForFormat(commit, objectFormat) || !isObjectIdForFormat(tree, objectFormat)) {
    throw new SourceFreezeError("REPOSITORY_INVALID", "Git returned an invalid object identifier");
  }
  return { commit, tree, objectFormat };
}

function assertRepositoryState(root: string, runner: GitCommandRunner): void {
  const sparse = runGitRaw(root, ["config", "--bool", "--get", "core.sparseCheckout"], runner);
  if (sparse.status === 0) {
    if (sparse.stdout.toString("utf8").trim() === "true") {
      throw new SourceFreezeError("SPARSE_CHECKOUT_UNSUPPORTED", "Sparse checkouts cannot be frozen");
    }
  } else if (sparse.status !== 1) {
    throw gitFailure("REPOSITORY_INVALID", "Git could not inspect sparse-checkout state", sparse);
  }

  const flags = runGit(root, ["ls-files", "-v", "-z"], runner).stdout;
  for (const entry of splitNul(flags)) {
    if (entry[0] !== 0x48 || entry[1] !== 0x20) {
      const flag = entry.length ? String.fromCharCode(entry[0] as number) : "?";
      throw new SourceFreezeError(
        "INDEX_FLAG_UNSUPPORTED",
        `Tracked entry has unsupported Git index flag ${JSON.stringify(flag)}`,
      );
    }
  }

  const staged = runGit(root, ["ls-files", "--stage", "-z"], runner).stdout;
  for (const entry of splitNul(staged)) {
    const mode = entry.subarray(0, 6).toString("ascii");
    if (mode === "120000") {
      throw new SourceFreezeError("TRACKED_SYMLINK_UNSUPPORTED", "Tracked symlinks cannot be frozen");
    }
    if (mode === "160000") {
      throw new SourceFreezeError("SUBMODULE_UNSUPPORTED", "Git submodules cannot be frozen");
    }
    if (mode !== "100644" && mode !== "100755") {
      throw new SourceFreezeError(
        "TRACKED_ENTRY_UNSUPPORTED",
        `Tracked entry has unsupported mode ${mode}`,
      );
    }
  }

  const status = runGit(
    root,
    [
      "status",
      "--porcelain=v2",
      "-z",
      "--untracked-files=all",
      "--ignore-submodules=none",
    ],
    runner,
  ).stdout;
  if (status.length !== 0) {
    throw new SourceFreezeError(
      "REPOSITORY_DIRTY",
      "Repository has staged, unstaged, unmerged, or untracked changes",
    );
  }
}

function runGit(
  root: string,
  arguments_: readonly string[],
  runner: GitCommandRunner,
): GitCommandResult {
  const result = runGitRaw(root, arguments_, runner);
  if (result.status !== 0) {
    throw gitFailure("GIT_COMMAND_FAILED", `Git command failed: git ${arguments_.join(" ")}`, result);
  }
  return result;
}

function runGitRaw(
  root: string,
  arguments_: readonly string[],
  runner: GitCommandRunner,
): GitCommandResult {
  return runner(root, [...GIT_BASE_ARGUMENTS, ...arguments_]);
}

function defaultGitCommandRunner(root: string, arguments_: readonly string[]): GitCommandResult {
  const environment = { ...process.env };
  // Repository-discovery variables can redirect a command away from `root`
  // while preserving a plausible worktree path. Source identity must come
  // only from the explicitly supplied repository, never ambient Git state.
  for (const key of Object.keys(environment)) {
    if (key.startsWith("GIT_")) delete environment[key];
  }
  const result = spawnSync("git", arguments_, {
    cwd: root,
    encoding: "buffer",
    env: {
      ...environment,
      GIT_OPTIONAL_LOCKS: "0",
      LC_ALL: "C",
      LANG: "C",
    },
    maxBuffer: 32 * 1024 * 1024,
  });
  if (result.error) {
    throw freezeError("GIT_COMMAND_FAILED", "Git could not be executed", result.error);
  }
  return {
    status: result.status ?? 1,
    stdout: result.stdout ?? Buffer.alloc(0),
    stderr: result.stderr ?? Buffer.alloc(0),
  };
}

function gitText(result: GitCommandResult, code: string, context: string): string {
  if (result.status !== 0) throw gitFailure(code, context, result);
  const value = result.stdout.toString("utf8").trim();
  if (!value) throw new SourceFreezeError(code, `${context}: command returned no value`);
  return value;
}

function gitFailure(code: string, context: string, result: GitCommandResult): SourceFreezeError {
  const detail = result.stderr.toString("utf8").trim();
  return new SourceFreezeError(code, detail ? `${context}: ${detail}` : context);
}

function splitNul(body: Buffer): Buffer[] {
  const entries: Buffer[] = [];
  let start = 0;
  for (let index = 0; index < body.length; index += 1) {
    if (body[index] !== 0) continue;
    if (index > start) entries.push(body.subarray(start, index));
    start = index + 1;
  }
  if (start !== body.length) {
    throw new SourceFreezeError("GIT_OUTPUT_INVALID", "NUL-delimited Git output is truncated");
  }
  return entries;
}

type StableStats = ReturnType<typeof lstatSync> & {
  readonly dev: bigint;
  readonly ino: bigint;
  readonly mode: bigint;
  readonly nlink: bigint;
  readonly size: bigint;
  readonly mtimeNs: bigint;
  readonly ctimeNs: bigint;
};

function assertSupportedFile(
  stats: StableStats,
  maximumBytes: number,
  path: string,
  code: string,
): void {
  if (!stats.isFile() || stats.isSymbolicLink() || stats.nlink !== 1n) {
    throw new SourceFreezeError(code, `Input must be a regular, single-link file: ${path}`);
  }
  if (stats.size > BigInt(maximumBytes)) {
    throw new SourceFreezeError("INPUT_TOO_LARGE", `Input exceeds ${maximumBytes} bytes: ${path}`);
  }
}

function sameFileIdentity(left: StableStats, right: StableStats): boolean {
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

function requireMaximumBytes(maximumBytes: number): void {
  if (!Number.isSafeInteger(maximumBytes) || maximumBytes < 0) {
    throw new SourceFreezeError(
      "INPUT_LIMIT_INVALID",
      "Maximum input size must be a non-negative safe integer",
    );
  }
}

function sha256(bytes: Buffer): string {
  return `sha256:${createHash("sha256").update(bytes).digest("hex")}`;
}

function isObjectIdForFormat(value: string, objectFormat: "sha1" | "sha256"): boolean {
  return OBJECT_ID.test(value) && value.length === (objectFormat === "sha1" ? 40 : 64);
}

function freezeError(code: string, message: string, cause: unknown): SourceFreezeError {
  const error = new SourceFreezeError(code, message);
  if (cause instanceof Error) error.cause = cause;
  return error;
}
