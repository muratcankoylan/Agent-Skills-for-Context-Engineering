import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  linkSync,
  mkdtempSync,
  mkdirSync,
  rmSync,
  symlinkSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  SourceFreezeError,
  assertVerifiedExactNamedInputCapture,
  captureCleanRepository,
  captureExactNamedInputs,
  revalidateExactNamedInputs,
  stableReadRegularFile,
} from "./sourceFreeze.ts";

const GIT_ENV = {
  ...process.env,
  GIT_AUTHOR_DATE: "2026-01-01T00:00:00Z",
  GIT_COMMITTER_DATE: "2026-01-01T00:00:00Z",
};

test("clean repository and exact named inputs capture and revalidate", () => {
  withRepository((root) => {
    const identity = captureCleanRepository(root);
    assert.match(identity.objectFormat, /^(?:sha1|sha256)$/);
    const objectIdLength = identity.objectFormat === "sha1" ? 40 : 64;
    assert.equal(identity.commit.length, objectIdLength);
    assert.equal(identity.tree.length, objectIdLength);
    assert.match(identity.commit, /^[0-9a-f]+$/);
    assert.match(identity.tree, /^[0-9a-f]+$/);

    const capture = captureExactNamedInputs(root, { fixture: join(root, "fixture.jsonl") });
    assert.doesNotThrow(() => assertVerifiedExactNamedInputCapture(capture));
    assert.deepEqual(capture.repository, identity);
    assert.equal(capture.inputs.fixture?.size, 6);
    assert.match(capture.inputs.fixture?.digest ?? "", /^sha256:[0-9a-f]{64}$/);
    revalidateExactNamedInputs(root, { fixture: join(root, "fixture.jsonl") }, capture);
  });
});

test("deserialized or caller-fabricated input captures have no construction authority", () => {
  withRepository((root) => {
    const capture = captureExactNamedInputs(root, { fixture: join(root, "fixture.jsonl") });
    const fabricated = structuredClone(capture);
    assertSourceError(
      () => assertVerifiedExactNamedInputCapture(fabricated),
      "CAPTURE_UNVERIFIED",
    );
  });
});

test("an injected Git command runner cannot mint construction authority", () => {
  withRepository((root) => {
    const capture = captureExactNamedInputs(
      root,
      { fixture: join(root, "fixture.jsonl") },
      {
        commandRunner(repository, arguments_) {
          const result = spawnSync("git", arguments_, {
            cwd: repository,
            encoding: "buffer",
            env: GIT_ENV,
          });
          assert.ifError(result.error);
          return {
            status: result.status ?? 1,
            stdout: result.stdout ?? Buffer.alloc(0),
            stderr: result.stderr ?? Buffer.alloc(0),
          };
        },
      },
    );
    assertSourceError(
      () => assertVerifiedExactNamedInputCapture(capture),
      "CAPTURE_UNVERIFIED",
    );
  });
});

for (const [label, mutate] of [
  ["unstaged tracked", (root: string) => writeFileSync(join(root, "source.txt"), "changed\n")],
  [
    "staged",
    (root: string) => {
      writeFileSync(join(root, "source.txt"), "changed\n");
      git(root, "add", "source.txt");
    },
  ],
  ["untracked", (root: string) => writeFileSync(join(root, "untracked.txt"), "new\n")],
] as const) {
  test(`clean capture rejects ${label} changes`, () => {
    withRepository((root) => {
      mutate(root);
      assertSourceError(() => captureCleanRepository(root), "REPOSITORY_DIRTY");
    });
  });
}

test("clean capture rejects assume-unchanged and skip-worktree index flags", () => {
  for (const flag of ["--assume-unchanged", "--skip-worktree"]) {
    withRepository((root) => {
      git(root, "update-index", flag, "source.txt");
      writeFileSync(join(root, "source.txt"), "hidden mutation\n");
      assertSourceError(() => captureCleanRepository(root), "INDEX_FLAG_UNSUPPORTED");
    });
  }
});

test("ambient Git repository variables cannot redirect source attestation", () => {
  withRepository((legitimate) => {
    withRepository((decoy) => {
      writeFileSync(join(legitimate, "source.txt"), "decoy-controlled bytes\n");
      writeFileSync(join(decoy, "source.txt"), "decoy-controlled bytes\n");
      git(decoy, "add", "source.txt");
      git(decoy, "commit", "--quiet", "-m", "decoy identity");

      const priorGitDir = process.env.GIT_DIR;
      const priorGitWorkTree = process.env.GIT_WORK_TREE;
      try {
        process.env.GIT_DIR = join(decoy, ".git");
        process.env.GIT_WORK_TREE = legitimate;
        assertSourceError(() => captureCleanRepository(legitimate), "REPOSITORY_DIRTY");
      } finally {
        restoreEnvironment("GIT_DIR", priorGitDir);
        restoreEnvironment("GIT_WORK_TREE", priorGitWorkTree);
      }
    });
  });
});

test("clean capture rejects sparse checkout configuration", () => {
  withRepository((root) => {
    git(root, "config", "core.sparseCheckout", "true");
    assertSourceError(() => captureCleanRepository(root), "SPARSE_CHECKOUT_UNSUPPORTED");
  });
});

test(
  "clean capture rejects tracked symlinks",
  { skip: process.platform === "win32" },
  () => {
    withRepository((root) => {
      symlinkSync("source.txt", join(root, "tracked-link"));
      git(root, "add", "tracked-link");
      git(root, "commit", "-m", "add tracked symlink");
      assertSourceError(() => captureCleanRepository(root), "TRACKED_SYMLINK_UNSUPPORTED");
    });
  },
);

test("clean capture rejects a Git submodule entry", () => {
  withRepository((root) => {
    const commit = git(root, "rev-parse", "HEAD").stdout.toString("utf8").trim();
    git(root, "update-index", "--add", "--cacheinfo", `160000,${commit},vendor/submodule`);
    git(root, "commit", "-m", "add gitlink");
    assertSourceError(() => captureCleanRepository(root), "SUBMODULE_UNSUPPORTED");
  });
});

test(
  "stable read rejects symlinks and hardlinks",
  { skip: process.platform === "win32" },
  () => {
    const root = mkdtempSync(join(tmpdir(), "source-freeze-links-"));
    try {
      const original = join(root, "original.txt");
      const symlink = join(root, "symlink.txt");
      const hardlink = join(root, "hardlink.txt");
      writeFileSync(original, "same bytes\n");
      symlinkSync("original.txt", symlink);
      assertSourceError(() => stableReadRegularFile(symlink, 1024), "INPUT_UNSUPPORTED");
      linkSync(original, hardlink);
      assertSourceError(() => stableReadRegularFile(original, 1024), "INPUT_UNSUPPORTED");
      assertSourceError(() => stableReadRegularFile(hardlink, 1024), "INPUT_UNSUPPORTED");
    } finally {
      rmSync(root, { recursive: true, force: true });
    }
  },
);

test("two-pass capture rejects a same-size ignored-input mutation", () => {
  withRepository((root) => {
    const ignored = join(root, "ignored-input.bin");
    writeFileSync(ignored, "alpha");
    assertSourceError(
      () =>
        captureExactNamedInputs(
          root,
          { fixture: ignored },
          {
            hooks: {
              afterFirstInputPass: () => writeFileSync(ignored, "bravo"),
            },
          },
        ),
      "INPUT_CHANGED",
    );
  });
});

test("capture rejects source mutation before its final repository pass", () => {
  withRepository((root) => {
    assertSourceError(
      () =>
        captureExactNamedInputs(
          root,
          { fixture: join(root, "fixture.jsonl") },
          {
            hooks: {
              beforeFinalRepositoryCapture: () =>
                writeFileSync(join(root, "source.txt"), "changed after inputs\n"),
            },
          },
        ),
      "REPOSITORY_DIRTY",
    );
  });
});

test("revalidation rejects changed bytes and changed logical input sets", () => {
  withRepository((root) => {
    const ignored = join(root, "ignored-input.bin");
    writeFileSync(ignored, "alpha");
    const capture = captureExactNamedInputs(root, { fixture: ignored });
    writeFileSync(ignored, "bravo");
    assertSourceError(
      () => revalidateExactNamedInputs(root, { fixture: ignored }, capture),
      "INPUT_CHANGED",
    );
    writeFileSync(ignored, "alpha");
    assertSourceError(
      () => revalidateExactNamedInputs(root, { renamed: ignored }, capture),
      "INPUT_SET_CHANGED",
    );
  });
});

test("stable file metadata is independent of the source path", () => {
  const root = mkdtempSync(join(tmpdir(), "source-freeze-paths-"));
  try {
    const first = join(root, "one", "input.bin");
    const second = join(root, "two", "renamed.bin");
    mkdirSync(join(root, "one"));
    mkdirSync(join(root, "two"));
    writeFileSync(first, "path-independent\n");
    writeFileSync(second, "path-independent\n");
    assert.deepEqual(stableReadRegularFile(first, 1024), stableReadRegularFile(second, 1024));
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("stable read enforces its byte limit", () => {
  const root = mkdtempSync(join(tmpdir(), "source-freeze-limit-"));
  try {
    const input = join(root, "input.bin");
    writeFileSync(input, "12345");
    assertSourceError(() => stableReadRegularFile(input, 4), "INPUT_TOO_LARGE");
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

function withRepository(run: (root: string) => void): void {
  const root = mkdtempSync(join(tmpdir(), "source-freeze-repository-"));
  try {
    git(root, "init", "--quiet");
    git(root, "config", "user.name", "Source Freeze Test");
    git(root, "config", "user.email", "source-freeze@example.invalid");
    writeFileSync(join(root, ".gitignore"), "ignored-input.bin\n");
    writeFileSync(join(root, "source.txt"), "source\n");
    writeFileSync(join(root, "fixture.jsonl"), "{}\n{}\n");
    git(root, "add", ".gitignore", "source.txt", "fixture.jsonl");
    git(root, "commit", "--quiet", "-m", "fixture repository");
    run(root);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
}

function git(root: string, ...arguments_: string[]) {
  const result = spawnSync("git", arguments_, {
    cwd: root,
    encoding: "buffer",
    env: GIT_ENV,
  });
  assert.ifError(result.error);
  assert.equal(
    result.status,
    0,
    `git ${arguments_.join(" ")} failed: ${(result.stderr ?? Buffer.alloc(0)).toString("utf8")}`,
  );
  return result;
}

function assertSourceError(run: () => unknown, code: string): void {
  assert.throws(run, (error: unknown) => {
    assert.ok(error instanceof SourceFreezeError);
    assert.equal(error.code, code);
    return true;
  });
}

function restoreEnvironment(key: string, value: string | undefined): void {
  if (value === undefined) delete process.env[key];
  else process.env[key] = value;
}
