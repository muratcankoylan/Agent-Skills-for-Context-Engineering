import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, mkdirSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";

import {
  MAX_PLANNER_ITEMS,
  RUNNER_ROOT,
  checkedRunCardinality,
  parseCliFlags,
  resolveConfig,
} from "./common.ts";

test("planner configuration rejects ambiguous or lossy inputs", () => {
  assert.throws(
    () => resolveConfig(parseCliFlags(["--dry-run", "--reps", "1.5"]), "/fixture"),
    /--reps must be a positive safe integer/,
  );
  assert.throws(
    () =>
      resolveConfig(
        parseCliFlags(["--dry-run", "--models", "gpt-5.5,gpt-5.5"]),
        "/fixture",
      ),
    /--models must contain unique model ids/,
  );
  assert.throws(
    () => resolveConfig(parseCliFlags(["--dry-run", "--max-budget-usd", "NaN"]), "/fixture"),
    /--max-budget-usd must be a positive finite number/,
  );
});

test("planner cardinality is bounded before plan allocation", () => {
  assert.equal(checkedRunCardinality(56, 4, 3), 672);
  assert.throws(
    () => checkedRunCardinality(1, 1, MAX_PLANNER_ITEMS + 1),
    /exceeds the in-memory planner ceiling/,
  );
});

test("router dry-run rejects malformed fixture records", () => {
  const directory = mkdtempSync(join(tmpdir(), "router-fixture-"));
  try {
    const fixture = join(directory, "invalid.jsonl");
    writeFileSync(fixture, "{}\n", "utf-8");
    const result = spawnSync(
      process.execPath,
      [
        "--experimental-strip-types",
        "src/runRouter.ts",
        "--dry-run",
        "--fixture",
        fixture,
      ],
      { cwd: RUNNER_ROOT, encoding: "utf-8" },
    );
    assert.equal(result.status, 2);
    assert.match(result.stderr, /requires non-empty prompt_id/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("effectiveness dry-run honors and validates the supplied task root", () => {
  const directory = mkdtempSync(join(tmpdir(), "effectiveness-fixture-"));
  try {
    mkdirSync(join(directory, "tasks"));
    writeFileSync(join(directory, "tasks", "unexpected.txt"), "invalid\n", "utf-8");
    const result = spawnSync(
      process.execPath,
      [
        "--experimental-strip-types",
        "src/runEffectiveness.ts",
        "--dry-run",
        "--fixture",
        join(directory, "tasks"),
      ],
      { cwd: RUNNER_ROOT, encoding: "utf-8" },
    );
    assert.equal(result.status, 2);
    assert.match(result.stderr, /Unexpected non-directory task entry/);
  } finally {
    rmSync(directory, { recursive: true, force: true });
  }
});

test("Stage 2 non-dry execution is blocked before SDK import", () => {
  const result = spawnSync(
    process.execPath,
    [
      "--no-warnings",
      "--import",
      "./test/registerDenyCursorSdk.mjs",
      "--experimental-strip-types",
      "src/runRouter.ts",
    ],
    {
      cwd: RUNNER_ROOT,
      encoding: "utf-8",
      env: { ...process.env, CURSOR_API_KEY: "fixture-noncredential" },
    },
  );

  assert.equal(result.status, 1);
  assert.match(result.stderr, /Live Cursor execution is blocked pending an accepted audit and canary/);
  assert.doesNotMatch(result.stderr, /SDK_IMPORT_FORBIDDEN_DURING_DRY_RUN/);
});

test("Stage 3 non-dry execution fails closed without SDK import", () => {
  const result = spawnSync(
    process.execPath,
    [
      "--no-warnings",
      "--import",
      "./test/registerDenyCursorSdk.mjs",
      "--experimental-strip-types",
      "src/runEffectiveness.ts",
    ],
    {
      cwd: RUNNER_ROOT,
      encoding: "utf-8",
      env: { ...process.env, CURSOR_API_KEY: "fixture-noncredential" },
    },
  );

  assert.equal(result.status, 1);
  assert.match(result.stderr, /Stage 3 live execution is not implemented/);
  assert.doesNotMatch(result.stderr, /SDK_IMPORT_FORBIDDEN_DURING_DRY_RUN/);
});
