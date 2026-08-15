import assert from "node:assert/strict";
import { link, lstat, mkdir, readFile, realpath, symlink, unlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, test } from "node:test";
import { mkdtemp, rm } from "node:fs/promises";

import { DurableFsError, NodeDurableFileSystem } from "./durableFs.ts";

const temporaryDirectories: string[] = [];

afterEach(async () => {
  await Promise.all(temporaryDirectories.splice(0).map((path) => rm(path, { recursive: true, force: true })));
});

async function workspace(): Promise<string> {
  const path = await mkdtemp(join(tmpdir(), "router-durable-fs-"));
  temporaryDirectories.push(path);
  return path;
}

test("the confinement root must already exist and cannot itself be a symlink", async () => {
  const parent = await workspace();
  const missing = join(parent, "missing");
  assert.throws(
    () => new NodeDurableFileSystem(missing),
    (error: unknown) => error instanceof DurableFsError && error.code === "DIRECTORY_INVALID",
  );
  await assert.rejects(lstat(missing), /ENOENT/);

  const target = await workspace();
  const alias = join(parent, "root-alias");
  await symlink(target, alias);
  assert.throws(
    () => new NodeDurableFileSystem(alias),
    (error: unknown) => error instanceof DurableFsError && error.code === "DIRECTORY_INVALID",
  );
});

test("an ancestor alias is resolved once and cannot retarget the trust anchor", async () => {
  const parent = await workspace();
  const firstTarget = await workspace();
  const secondTarget = await workspace();
  await mkdir(join(firstTarget, "results"), { mode: 0o700 });
  await mkdir(join(secondTarget, "results"), { mode: 0o700 });
  const alias = join(parent, "ancestor-alias");
  await symlink(firstTarget, alias);
  const lexicalRoot = join(alias, "results");
  const fileSystem = new NodeDurableFileSystem(lexicalRoot);

  await unlink(alias);
  await symlink(secondTarget, alias);
  const body = Buffer.from("frozen-root\n");
  await fileSystem.writeExclusiveDurable(join(lexicalRoot, "record"), body);

  assert.deepEqual(await readFile(join(firstTarget, "results", "record")), body);
  await assert.rejects(lstat(join(secondTarget, "results", "record")), /ENOENT/);
});

test("private directories and exclusively published files have restrictive modes", async () => {
  const root = await workspace();
  const fileSystem = new NodeDurableFileSystem(root);
  const directory = join(root, "private", "nested");
  const path = join(directory, "record.json");
  const body = Buffer.from('{"value":1}\n');

  await fileSystem.ensurePrivateDirectory(directory);
  await fileSystem.writeExclusiveDurable(path, body);

  assert.equal((await lstat(directory)).mode & 0o777, 0o700);
  assert.equal((await lstat(path)).mode & 0o777, 0o600);
  assert.deepEqual(await readFile(path), body);
});

test("new private directories sync child metadata before the parent entry", async () => {
  const root = await workspace();
  const physicalRoot = await realpath(root);
  const first = join(physicalRoot, "private");
  const second = join(first, "nested");

  class ObservedDirectoryFileSystem extends NodeDurableFileSystem {
    readonly events: string[] = [];

    protected override async createPrivateDirectory(path: string): Promise<boolean> {
      const created = await super.createPrivateDirectory(path);
      if (created) this.events.push(`mkdir:${path}`);
      return created;
    }

    protected override async applyPrivateDirectoryMode(path: string): Promise<void> {
      await super.applyPrivateDirectoryMode(path);
      this.events.push(`chmod:${path}`);
    }

    protected override async syncPrivateDirectory(path: string): Promise<void> {
      await super.syncPrivateDirectory(path);
      this.events.push(`fsync:${path}`);
    }
  }

  const fileSystem = new ObservedDirectoryFileSystem(root);
  await fileSystem.ensurePrivateDirectory(join(root, "private", "nested"));

  assert.deepEqual(fileSystem.events, [
    `mkdir:${first}`,
    `chmod:${first}`,
    `fsync:${first}`,
    `fsync:${physicalRoot}`,
    `mkdir:${second}`,
    `chmod:${second}`,
    `fsync:${second}`,
    `fsync:${first}`,
  ]);
  assert.equal((await lstat(first)).mode & 0o777, 0o700);
  assert.equal((await lstat(second)).mode & 0o777, 0o700);
});

test("exclusive publication has one winner and never overwrites", async () => {
  const root = await workspace();
  const fileSystem = new NodeDurableFileSystem(root);
  const path = join(root, "state", "record.json");
  const first = Buffer.from("first\n");
  const second = Buffer.from("second\n");

  const outcomes = await Promise.allSettled([
    fileSystem.writeExclusiveDurable(path, first),
    fileSystem.writeExclusiveDurable(path, second),
  ]);
  assert.equal(outcomes.filter((result) => result.status === "fulfilled").length, 1);
  const rejection = outcomes.find((result) => result.status === "rejected");
  assert.ok(rejection?.status === "rejected");
  assert.ok(rejection.reason instanceof DurableFsError);
  assert.equal(rejection.reason.code, "EXCLUSIVE_TARGET_EXISTS");
  const persisted = await readFile(path);
  assert.ok(persisted.equals(first) || persisted.equals(second));

  await assert.rejects(
    fileSystem.writeExclusiveDurable(path, Buffer.from("replacement\n")),
    (error: unknown) => error instanceof DurableFsError && error.code === "EXCLUSIVE_TARGET_EXISTS",
  );
  assert.deepEqual(await readFile(path), persisted);
});

test("stable reads reject symlinks, hardlinks, and oversized records", async () => {
  const root = await workspace();
  const fileSystem = new NodeDurableFileSystem(root);
  const original = join(root, "original");
  const hard = join(root, "hard");
  const symbolic = join(root, "symbolic");
  await writeFile(original, "0123456789");
  await link(original, hard);
  await symlink(original, symbolic);

  for (const path of [original, hard, symbolic]) {
    await assert.rejects(
      fileSystem.readRegularNoFollow(path, 100),
      (error: unknown) => error instanceof DurableFsError && error.code === "FILE_INVALID",
    );
  }

  const large = join(root, "large");
  await writeFile(large, "0123456789");
  await assert.rejects(
    fileSystem.readRegularNoFollow(large, 5),
    (error: unknown) => error instanceof DurableFsError && error.code === "FILE_TOO_LARGE",
  );
});

test("exact lock removal cannot remove another owner's body", async () => {
  const root = await workspace();
  const fileSystem = new NodeDurableFileSystem(root);
  const path = join(root, "locks", "run.lock");
  const body = Buffer.from('{"owner":"one"}\n');
  await fileSystem.writeExclusiveDurable(path, body);

  await assert.rejects(
    fileSystem.removeExactDurable(path, Buffer.from('{"owner":"two"}\n')),
    (error: unknown) => error instanceof DurableFsError && error.code === "LOCK_BODY_MISMATCH",
  );
  assert.deepEqual(await readFile(path), body);

  await fileSystem.removeExactDurable(path, body);
  await assert.rejects(lstat(path), /ENOENT/);

  const replacement = Buffer.from('{"owner":"replacement"}\n');
  await fileSystem.writeExclusiveDurable(path, replacement);
  await assert.rejects(
    fileSystem.removeExactDurable(path, body),
    (error: unknown) => error instanceof DurableFsError && error.code === "LOCK_BODY_MISMATCH",
  );
  assert.deepEqual(await readFile(path), replacement);
});

test("a delayed stale releaser cannot unlink a newer lock generation", async () => {
  const root = await workspace();
  let releaseRead!: () => void;
  let continueRelease!: () => void;
  const readComplete = new Promise<void>((resolve) => { releaseRead = resolve; });
  const mayContinue = new Promise<void>((resolve) => { continueRelease = resolve; });

  class DelayedReleaseFileSystem extends NodeDurableFileSystem {
    override async readRegularNoFollow(path: string, maximumBytes: number): Promise<Uint8Array> {
      const body = await super.readRegularNoFollow(path, maximumBytes);
      if (path.endsWith("run.lock")) {
        releaseRead();
        await mayContinue;
      }
      return body;
    }
  }

  const normal = new NodeDurableFileSystem(root);
  const delayed = new DelayedReleaseFileSystem(root);
  const path = join(root, "locks", "run.lock");
  const first = Buffer.from('{"owner":"first"}\n');
  const second = Buffer.from('{"owner":"second"}\n');
  await normal.writeExclusiveDurable(path, first);

  const staleRelease = delayed.removeExactDurable(path, first);
  await readComplete;
  await normal.removeExactDurable(path, first);
  await normal.writeExclusiveDurable(path, second);
  continueRelease();

  await assert.rejects(
    staleRelease,
    (error: unknown) => error instanceof DurableFsError && error.code === "LOCK_RELEASE_REPLAY",
  );
  assert.deepEqual(await readFile(path), second);
});

test("directory listing exposes entry kinds without following links", async () => {
  const root = await workspace();
  const fileSystem = new NodeDurableFileSystem(root);
  const directory = join(root, "state");
  await mkdir(join(directory, "child"), { recursive: true });
  await writeFile(join(directory, "record"), "value");
  await symlink(join(directory, "record"), join(directory, "alias"));

  assert.deepEqual(await fileSystem.listDirectory(directory), [
    { name: "alias", kind: "symlink" },
    { name: "child", kind: "directory" },
    { name: "record", kind: "file" },
  ]);
});

test("directory listing stops at the explicit entry limit", async () => {
  const root = await workspace();
  const fileSystem = new NodeDurableFileSystem(root);
  const directory = join(root, "bounded-state");
  await mkdir(directory);
  for (const name of ["a", "b", "c", "d"]) {
    await writeFile(join(directory, name), name);
  }

  await assert.rejects(
    fileSystem.listDirectory(directory, 3),
    (error: unknown) =>
      error instanceof DurableFsError && error.code === "DIRECTORY_TOO_LARGE",
  );
  assert.deepEqual(
    (await fileSystem.listDirectory(directory, 4)).map((entry) => entry.name),
    ["a", "b", "c", "d"],
  );
  await assert.rejects(
    fileSystem.listDirectory(directory, -1),
    (error: unknown) => error instanceof DurableFsError && error.code === "BOUNDS_INVALID",
  );
});

test("directory creation rejects a symlink ancestor inside the confinement root", async () => {
  const root = await workspace();
  const outside = await workspace();
  const fileSystem = new NodeDurableFileSystem(root);
  await symlink(outside, join(root, "link"));

  await assert.rejects(
    fileSystem.ensurePrivateDirectory(join(root, "link", "child")),
    (error: unknown) => error instanceof DurableFsError && error.code === "DIRECTORY_INVALID",
  );
  await assert.rejects(lstat(join(outside, "child")), /ENOENT/);
});

test("reads and listings reject a symlink ancestor inside the confinement root", async () => {
  const root = await workspace();
  const outside = await workspace();
  const fileSystem = new NodeDurableFileSystem(root);
  await writeFile(join(outside, "record"), "external");
  await symlink(outside, join(root, "link"));

  await assert.rejects(
    fileSystem.readRegularNoFollow(join(root, "link", "record"), 100),
    (error: unknown) => error instanceof DurableFsError && error.code === "DIRECTORY_INVALID",
  );
  await assert.rejects(
    fileSystem.listDirectory(join(root, "link")),
    (error: unknown) => error instanceof DurableFsError && error.code === "DIRECTORY_INVALID",
  );
});
