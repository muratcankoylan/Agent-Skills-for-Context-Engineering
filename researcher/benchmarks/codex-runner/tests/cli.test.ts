import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { test } from "node:test";
import { dirname, join } from "node:path";
import { fileURLToPath } from "node:url";

const RUNNER_DIR = dirname(dirname(fileURLToPath(import.meta.url)));

function run(script: "runEffectiveness.ts" | "runRouter.ts", args: string[]) {
  const result = spawnSync(
    process.execPath,
    ["--experimental-strip-types", join(RUNNER_DIR, "src", script), ...args],
    { cwd: RUNNER_DIR, encoding: "utf-8" },
  );
  return {
    code: result.status,
    output: `${result.stdout ?? ""}\n${result.stderr ?? ""}`,
  };
}

test("effectiveness filters produce the bounded pilot plan", () => {
  const result = run("runEffectiveness.ts", [
    "--dry-run",
    "--task-ids", "002,003,004",
    "--conditions", "control,target,negative",
    "--reps", "3",
    "--max-runs", "27",
  ]);
  assert.equal(result.code, 0, result.output);
  assert.match(result.output, /tasks discovered: 4; selected: 3/);
  assert.match(result.output, /planned runs: 27/);
  assert.match(result.output, /conditions=control,target,negative/);
});

test("CSV filters are trimmed and deduplicated", () => {
  const result = run("runEffectiveness.ts", [
    "--dry-run",
    "--task-ids", "002,002",
    "--conditions", "target,target,control",
    "--reps", "1",
    "--max-runs", "2",
  ]);
  assert.equal(result.code, 0, result.output);
  assert.match(result.output, /planned runs: 2/);
  assert.match(result.output, /condition filter: control,target/);
});

test("unknown task IDs fail with available values", () => {
  const result = run("runEffectiveness.ts", [
    "--dry-run",
    "--task-ids", "999",
    "--conditions", "control",
    "--max-runs", "1",
  ]);
  assert.equal(result.code, 2, result.output);
  assert.match(result.output, /Unknown --task-ids value\(s\): 999/);
  assert.match(result.output, /Available task IDs: 001,002,003,004/);
});

test("unknown conditions fail with available values", () => {
  const result = run("runEffectiveness.ts", [
    "--dry-run",
    "--task-ids", "002",
    "--conditions", "control,banana",
    "--max-runs", "2",
  ]);
  assert.equal(result.code, 2, result.output);
  assert.match(result.output, /Unknown --conditions value\(s\): banana/);
  assert.match(result.output, /Available conditions: control,target,negative,full,target_plus_one,target_plus_unrelated/);
});

test("router rejects effectiveness-only filters", () => {
  const result = run("runRouter.ts", ["--dry-run", "--task-ids", "002", "--max-runs", "1"]);
  assert.equal(result.code, 2, result.output);
  assert.match(result.output, /supported only by the effectiveness runner/);
});
