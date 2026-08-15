/**
 * Stage 3: Skill effectiveness benchmark.
 *
 * Hypothesis: loading a relevant skill improves outcome quality or token
 * efficiency on tasks the skill claims to address. Irrelevant skills should
 * have no effect (negative control).
 *
 * This revision validates the currently-built task set and prints a bounded
 * dry-run plan. Live execution requires a separate human-merged activation.
 */

import { join } from "node:path";
import { accessSync, constants, existsSync, lstatSync, readdirSync, readFileSync } from "node:fs";

import {
  RESEARCHER_DIR,
  assertBudget,
  buildRunPlan,
  checkedRunCardinality,
  forecastCost,
  loadSkillDescriptions,
  parseCliFlags,
  resolveConfig,
  runHeader,
} from "./common.ts";

interface EffectivenessTaskMetadata {
  id: string;
  slug: string;
  target_skill: string;
  irrelevant_skill: string;
  category: string;
  difficulty: "easy" | "medium" | "hard";
  notes?: string;
}

const CONDITIONS = ["control", "target", "negative", "full", "target_plus_one", "target_plus_unrelated"] as const;

const ESTIMATED_TOKENS_INPUT = 20_000;
const ESTIMATED_TOKENS_OUTPUT = 4_000;
const ESTIMATED_USD_PER_RUN = 0.18;
const LIVE_BLOCK_MESSAGE =
  "Stage 3 live execution is not implemented. See researcher/benchmarks/PLAN.md for the " +
  "manifest-bound activation contract; use --dry-run to validate the task set and plan.";

async function main(): Promise<number> {
  const flags = parseCliFlags(process.argv.slice(2));
  if (!flags.dryRun) {
    console.error(LIVE_BLOCK_MESSAGE);
    return 1;
  }
  const defaultFixture = join(RESEARCHER_DIR, "benchmarks", "effectiveness", "tasks");
  const config = resolveConfig(flags, defaultFixture);

  console.log(runHeader("Effectiveness Benchmark (Stage 3)"));
  const tasksDir = config.fixturePath;
  console.log(`tasks dir: ${tasksDir}`);
  console.log(`models: ${config.models.join(", ")}`);
  console.log(`reps per (task, condition, model): ${config.reps}`);
  console.log(`seed: ${config.seed}`);
  console.log(`dry-run: ${config.dryRun}`);

  if (!existsSync(tasksDir)) {
    console.error(`Tasks directory missing: ${tasksDir}`);
    return 1;
  }

  const skills = loadSkillDescriptions();
  const tasks = discoverTasks(tasksDir, skills.map((skill) => skill.name));
  console.log(`tasks discovered: ${tasks.length}`);

  if (tasks.length === 0) {
    console.error("No tasks present yet. Add at least one task under researcher/benchmarks/effectiveness/tasks/.");
    return 1;
  }

  const conditionItems = checkedRunCardinality(tasks.length, CONDITIONS.length, 1);
  const logicalRuns = checkedRunCardinality(conditionItems, config.models.length, config.reps);
  if (logicalRuns > config.maxRuns) {
    throw new Error(`Plan size ${logicalRuns} exceeds --max-runs ${config.maxRuns}.`);
  }
  const planIds: string[] = [];
  for (const task of tasks) {
    for (const condition of CONDITIONS) {
      planIds.push(`${task.id}|${condition}`);
    }
  }
  const plan = buildRunPlan(planIds, config.models, config.reps, config.seed);
  const forecast = forecastCost(plan, ESTIMATED_TOKENS_INPUT, ESTIMATED_TOKENS_OUTPUT, ESTIMATED_USD_PER_RUN);
  console.log(`planned runs: ${forecast.totalRuns}`);
  console.log(`conditions per task: ${CONDITIONS.length}`);
  console.log(`est. tokens per run: ${ESTIMATED_TOKENS_INPUT}in / ${ESTIMATED_TOKENS_OUTPUT}out`);
  console.log(`est. total cost: ${forecast.estimatedTotalUsd} USD`);

  assertBudget(plan, forecast, config);

  if (config.dryRun) {
    console.log("Dry-run: no SDK calls made.");
    console.log("First three tasks:");
    for (const task of tasks.slice(0, 3)) {
      console.log(`  - ${task.id} target=${task.target_skill} difficulty=${task.difficulty}`);
    }
    return 0;
  }

  throw new Error("unreachable: validated dry-run did not return");
}

function discoverTasks(tasksDir: string, skillNames: string[]): EffectivenessTaskMetadata[] {
  const tasks: EffectivenessTaskMetadata[] = [];
  const knownSkills = new Set(skillNames);
  const taskIds = new Set<string>();
  for (const entry of readdirSync(tasksDir).sort()) {
    const dir = join(tasksDir, entry);
    const directoryStat = lstatSync(dir);
    if (directoryStat.isSymbolicLink() || !directoryStat.isDirectory()) {
      throw new Error(`Unexpected non-directory task entry: ${dir}`);
    }
    const metaPath = join(dir, "metadata.json");
    const taskPath = join(dir, "task.md");
    const startingPath = join(dir, "starting");
    const verifyPath = join(dir, "verify.sh");
    for (const path of [metaPath, taskPath, verifyPath]) {
      if (!existsSync(path) || lstatSync(path).isSymbolicLink() || !lstatSync(path).isFile()) {
        throw new Error(`Task contract requires a regular file: ${path}`);
      }
    }
    if (
      !existsSync(startingPath) ||
      lstatSync(startingPath).isSymbolicLink() ||
      !lstatSync(startingPath).isDirectory()
    ) {
      throw new Error(`Task contract requires a regular starting directory: ${startingPath}`);
    }
    accessSync(verifyPath, constants.X_OK);
    let parsed: unknown;
    try {
      parsed = JSON.parse(readFileSync(metaPath, "utf-8"));
    } catch (error) {
      throw new Error(`Invalid task metadata ${metaPath}: ${(error as Error).message}`);
    }
    if (!parsed || typeof parsed !== "object" || Array.isArray(parsed)) {
      throw new Error(`Task metadata must be an object: ${metaPath}`);
    }
    const record = parsed as Record<string, unknown>;
    const knownKeys = new Set([
      "id",
      "slug",
      "target_skill",
      "irrelevant_skill",
      "category",
      "difficulty",
      "notes",
    ]);
    const unknownKeys = Object.keys(record).filter((key) => !knownKeys.has(key));
    if (unknownKeys.length) {
      throw new Error(`Task metadata ${entry} has unknown fields: ${unknownKeys.sort().join(", ")}.`);
    }
    for (const field of ["id", "slug", "target_skill", "irrelevant_skill", "category"] as const) {
      if (typeof record[field] !== "string" || !record[field].trim()) {
        throw new Error(`Task metadata ${entry} requires non-empty ${field}.`);
      }
    }
    if (!/^[0-9]{3}$/.test(record.id as string)) {
      throw new Error(`Task metadata ${entry} requires a three-digit id.`);
    }
    if (!/^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(record.slug as string)) {
      throw new Error(`Task metadata ${entry} has a noncanonical slug.`);
    }
    if (entry !== `${record.id}-${record.slug}`) {
      throw new Error(`Task directory ${entry} does not match metadata id and slug.`);
    }
    if (taskIds.has(record.id as string)) {
      throw new Error(`Task metadata contains duplicate id ${record.id}.`);
    }
    taskIds.add(record.id as string);
    if (!knownSkills.has(record.target_skill as string)) {
      throw new Error(`Task ${entry} names unknown target skill ${record.target_skill}.`);
    }
    if (!knownSkills.has(record.irrelevant_skill as string)) {
      throw new Error(`Task ${entry} names unknown irrelevant skill ${record.irrelevant_skill}.`);
    }
    if (record.target_skill === record.irrelevant_skill) {
      throw new Error(`Task ${entry} target and irrelevant skills must differ.`);
    }
    if (!new Set(["easy", "medium", "hard"]).has(record.difficulty as string)) {
      throw new Error(`Task ${entry} has invalid difficulty ${String(record.difficulty)}.`);
    }
    if (record.notes !== undefined && typeof record.notes !== "string") {
      throw new Error(`Task ${entry} notes must be a string when present.`);
    }
    tasks.push(record as unknown as EffectivenessTaskMetadata);
  }
  return tasks;
}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    console.error(error);
    process.exit(2);
  });
