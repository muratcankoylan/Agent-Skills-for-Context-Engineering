/**
 * Stage 3: Skill effectiveness benchmark through Hermes/Headroom/Codex.
 *
 * Each condition runs in a fresh workspace. Skills are copied explicitly into
 * `.codex/skills/`, so no user/project skill leakage enters control or ablation
 * conditions.
 */

import { execFile } from "node:child_process";
import { createHash } from "node:crypto";
import {
  cpSync,
  existsSync,
  mkdirSync,
  readFileSync,
  readdirSync,
  rmSync,
  statSync,
  writeFileSync,
} from "node:fs";
import { join, resolve } from "node:path";
import { promisify } from "node:util";

import {
  RESEARCHER_DIR,
  REPO_ROOT,
  appendHistoryEntry,
  assertBudget,
  buildRunPlan,
  fixtureSha,
  forecastCost,
  loadSkillDescriptions,
  parseCliFlags,
  repoCommitSha,
  resolveConfig,
  resultFileName,
  runConcurrently,
  runHeader,
  runCodexPrompt,
  runtimeFingerprint,
  todayUtc,
  utcNow,
  writeJson,
} from "./common.ts";

interface EffectivenessTaskMetadata {
  id: string;
  slug: string;
  target_skill: string;
  irrelevant_skill: string;
  related_skill?: string;
  unrelated_skill?: string;
  category: string;
  difficulty: "easy" | "medium" | "hard";
  notes?: string;
  taskDir: string;
}

type Condition =
  | "control"
  | "target"
  | "negative"
  | "full"
  | "target_plus_one"
  | "target_plus_unrelated";

interface EffectivenessRunRecord {
  task_id: string;
  condition: Condition;
  model_id: string;
  rep: number;
  status: "finished" | "error" | "cancelled" | "dry_run";
  skills: string[];
  duration_ms: number;
  session_id?: string | undefined;
  final_text?: string;
  verify_exit_code?: number;
  verify_stdout?: string;
  verify_stderr?: string;
  verify_failure?: string;
  passed?: boolean;
  behavior_note?: string;
  verifier_sha: string;
  task_fixture_sha: string;
  workspace: string;
  notes?: string;
}

const execFileAsync = promisify(execFile);
const TASKS_DIR = join(RESEARCHER_DIR, "benchmarks", "effectiveness", "tasks");
const RESULTS_DIR = join(RESEARCHER_DIR, "benchmarks", "effectiveness", "results");
const HISTORY_PATH = join(RESEARCHER_DIR, "reports", "effectiveness-history.jsonl");
const CONDITIONS: Condition[] = [
  "control",
  "target",
  "negative",
  "full",
  "target_plus_one",
  "target_plus_unrelated",
];

const ESTIMATED_TOKENS_INPUT = 20_000;
const ESTIMATED_TOKENS_OUTPUT = 4_000;
const ESTIMATED_USD_PER_RUN = 0;

async function main(): Promise<number> {
  const flags = parseCliFlags(process.argv.slice(2));
  const config = resolveConfig(flags, TASKS_DIR);

  console.log(runHeader("Effectiveness Benchmark (Stage 3, Native Codex/Headroom)"));
  console.log(`tasks dir: ${TASKS_DIR}`);
  console.log(`models: ${config.models.join(", ")}`);
  console.log(`reps per (task, condition, model): ${config.reps}`);
  console.log(`seed: ${config.seed}`);
  console.log(`concurrency: ${config.concurrency}`);
  console.log(`resume: ${!config.noResume}`);
  console.log(`dry-run: ${config.dryRun}`);
  console.log(`runtime: ${runtimeFingerprint()}`);

  if (!existsSync(TASKS_DIR)) {
    console.error(`Tasks directory missing: ${TASKS_DIR}`);
    return 1;
  }
  const discoveredTasks = discoverTasks();
  const tasks = selectTasks(discoveredTasks, config.taskIds);
  const selectedConditions = selectConditions(config.conditions);
  console.log(`tasks discovered: ${discoveredTasks.length}; selected: ${tasks.length}`);
  console.log(`task filter: ${config.taskIds.length ? config.taskIds.join(",") : "all"}`);
  console.log(`condition filter: ${selectedConditions.join(",")}`);
  if (!tasks.length) {
    console.error("No effectiveness tasks selected.");
    return 1;
  }

  const planIds: string[] = [];
  for (const task of tasks) {
    const taskConditions = conditionsForTask(task, selectedConditions);
    if (!taskConditions.length) {
      throw new Error(
        `No selected conditions apply to task ${task.id}. Requested: ${selectedConditions.join(",")}`,
      );
    }
    for (const condition of taskConditions) {
      planIds.push(`${task.id}|${condition}`);
    }
  }
  const plan = buildRunPlan(planIds, config.models, config.reps, config.seed);
  const forecast = forecastCost(
    plan,
    ESTIMATED_TOKENS_INPUT,
    ESTIMATED_TOKENS_OUTPUT,
    ESTIMATED_USD_PER_RUN,
  );
  console.log(`planned runs: ${forecast.totalRuns}`);
  console.log(`selected conditions: ${selectedConditions.length}`);
  console.log(`est. marginal API cost through subscription route: ${forecast.estimatedTotalUsd} USD`);
  assertBudget(plan, forecast, config);

  if (config.dryRun) {
    console.log("Dry-run: no Hermes/Codex calls made.");
    for (const task of tasks.slice(0, 3)) {
      console.log(
        `  - ${task.id} target=${task.target_skill} conditions=${conditionsForTask(task, selectedConditions).join(",")}`,
      );
    }
    return 0;
  }

  const allSkills = loadSkillDescriptions().map((skill) => skill.name);
  const selection = {
    task_ids: tasks.map((task) => task.id),
    conditions: selectedConditions,
  };
  const selectionSuffix = config.taskIds.length || config.conditions.length
    ? `-${shortHash(JSON.stringify(selection))}`
    : "";
  const runDir = join(RESULTS_DIR, `${todayUtc()}-${config.seed}-codex${selectionSuffix}`);
  const workspacesDir = join(runDir, "workspaces");
  mkdirSync(workspacesDir, { recursive: true });
  const taskProvenance = new Map(
    tasks.map((task) => [task.id, provenanceForTask(task)] as const),
  );
  const plannedNames = new Set(
    plan.map((item) => resultFileName(item.promptId, item.modelId, item.rep)),
  );
  const existing = config.noResume
    ? new Map<string, EffectivenessRunRecord>()
    : loadExistingResults(runDir, plannedNames, taskProvenance);
  const remaining = plan.filter(
    (item) => !existing.has(resultFileName(item.promptId, item.modelId, item.rep)),
  );
  console.log(`resume: ${existing.size} prior results, ${remaining.length} runs remaining`);

  let completed = 0;
  const startedAt = Date.now();
  const newResults: EffectivenessRunRecord[] = [];
  await runConcurrently(remaining, config.concurrency, async (item) => {
    const [taskId, rawCondition] = item.promptId.split("|");
    const condition = rawCondition as Condition;
    const task = tasks.find((candidate) => candidate.id === taskId);
    if (!task) throw new Error(`Task missing from plan: ${taskId}`);
    const skills = skillsForCondition(task, condition, allSkills);
    const provenance = taskProvenance.get(task.id)!;
    const workspaceName = safeName(`${task.id}-${condition}-${item.modelId}-${item.rep}`);
    const workspace = join(workspacesDir, workspaceName);
    prepareWorkspace(task, workspace, skills);
    const record: EffectivenessRunRecord = {
      task_id: task.id,
      condition,
      model_id: item.modelId,
      rep: item.rep,
      status: "error",
      skills,
      duration_ms: 0,
      verifier_sha: provenance.verifier_sha,
      task_fixture_sha: provenance.task_fixture_sha,
      workspace,
    };
    const started = Date.now();
    try {
      const taskPrompt = readFileSync(join(task.taskDir, "task.md"), "utf-8");
      const prompt = [
        `Benchmark workspace: ${workspace}`,
        "Operate only inside that absolute directory. Treat it as the current working directory.",
        "Use tools when necessary and leave any requested files in that directory.",
        "",
        taskPrompt,
      ].join("\n");
      const result = await runCodexPrompt(prompt, {
        model: item.modelId,
        cwd: workspace,
        // Nested bwrap namespaces are unavailable in the deployment container.
        // Workspaces contain only benchmark fixtures and the prompt forbids external writes.
        sandbox: "danger-full-access",
        timeoutMs: 300_000,
      });
      record.status = "finished";
      if (result.sessionId) record.session_id = result.sessionId;
      record.final_text = result.finalText;
      writeFileSync(join(workspace, ".runner", "final.txt"), `${record.final_text}\n`);
      const verify = await runVerifier(task, workspace);
      record.verify_exit_code = verify.code;
      record.verify_stdout = verify.stdout;
      record.verify_stderr = verify.stderr;
      record.passed = verify.code === 0;
      if (!record.passed) {
        const verifyFailure = firstNonEmptyLine(verify.stderr) ?? firstNonEmptyLine(verify.stdout);
        if (verifyFailure) record.verify_failure = verifyFailure;
      }
      const notesPath = join(workspace, ".runner", "notes.txt");
      if (existsSync(notesPath)) record.behavior_note = readFileSync(notesPath, "utf-8").trim();
    } catch (error) {
      record.notes = (error as Error).message;
      record.passed = false;
    }
    record.duration_ms = Date.now() - started;
    writeJson(join(runDir, resultFileName(item.promptId, item.modelId, item.rep)), record);
    newResults.push(record);
    completed += 1;
    const elapsed = Date.now() - startedAt;
    const eta = completed ? Math.round((elapsed / completed) * (remaining.length - completed)) : 0;
    console.log(
      `[${completed}/${remaining.length}] ${task.id} ${condition} ${item.modelId} ` +
        `${record.passed ? "PASS" : "FAIL"} ${record.duration_ms}ms ETA=${Math.round(eta / 1000)}s`,
    );
  });

  const records = [...existing.values(), ...newResults];
  const summary = summarize(records);
  const metadata = {
    timestamp: utcNow(),
    runtime: runtimeFingerprint(),
    repo_sha: repoCommitSha(),
    task_fixtures: Object.fromEntries(taskProvenance),
    selection,
    seed: config.seed,
    models: config.models,
    reps: config.reps,
    tasks: tasks.length,
  };
  writeJson(join(runDir, "summary.json"), { ...metadata, summary, records });
  appendHistoryEntry(HISTORY_PATH, { ...metadata, summary });
  console.log("summary:", summary);
  console.log(`raw results in ${runDir}`);
  return records.some((record) => record.status === "error") ? 1 : 0;
}

function discoverTasks(): EffectivenessTaskMetadata[] {
  const tasks: EffectivenessTaskMetadata[] = [];
  for (const entry of readdirSync(TASKS_DIR).sort()) {
    const taskDir = join(TASKS_DIR, entry);
    if (!statSync(taskDir).isDirectory()) continue;
    const metadataPath = join(taskDir, "metadata.json");
    if (!existsSync(metadataPath)) continue;
    try {
      const metadata = JSON.parse(readFileSync(metadataPath, "utf-8")) as Omit<
        EffectivenessTaskMetadata,
        "taskDir"
      >;
      tasks.push({ ...metadata, taskDir });
    } catch (error) {
      console.warn(`Skipping ${entry}: invalid metadata.json (${(error as Error).message})`);
    }
  }
  return tasks;
}

function conditionsForTask(
  task: EffectivenessTaskMetadata,
  selected: Condition[] = CONDITIONS,
): Condition[] {
  const available: Condition[] = task.target_skill === "none"
    ? ["control", "full", "negative"]
    : CONDITIONS;
  return selected.filter((condition) => available.includes(condition));
}

function skillsForCondition(
  task: EffectivenessTaskMetadata,
  condition: Condition,
  allSkills: string[],
): string[] {
  const related = task.related_skill ?? "context-optimization";
  const unrelated = task.unrelated_skill ?? task.irrelevant_skill;
  switch (condition) {
    case "control":
      return [];
    case "target":
      return task.target_skill === "none" ? [] : [task.target_skill];
    case "negative":
      return task.irrelevant_skill === "none" ? [] : [task.irrelevant_skill];
    case "full":
      return allSkills;
    case "target_plus_one":
      return unique([task.target_skill, related].filter((value) => value !== "none"));
    case "target_plus_unrelated":
      return unique([task.target_skill, unrelated].filter((value) => value !== "none"));
  }
}

function prepareWorkspace(
  task: EffectivenessTaskMetadata,
  workspace: string,
  skills: string[],
): void {
  rmSync(workspace, { recursive: true, force: true });
  mkdirSync(workspace, { recursive: true });
  const starting = join(task.taskDir, "starting");
  if (existsSync(starting)) cpSync(starting, workspace, { recursive: true });
  mkdirSync(join(workspace, ".runner"), { recursive: true });
  for (const skill of skills) {
    const source = join(REPO_ROOT, "skills", skill);
    if (!existsSync(source)) throw new Error(`Condition skill missing: ${source}`);
    cpSync(source, join(workspace, ".codex", "skills", skill), { recursive: true });
  }
}

async function runVerifier(
  task: EffectivenessTaskMetadata,
  workspace: string,
): Promise<{ code: number; stdout: string; stderr: string }> {
  try {
    const result = await execFileAsync("bash", [resolve(task.taskDir, "verify.sh")], {
      cwd: workspace,
      maxBuffer: 4 * 1024 * 1024,
      timeout: 60_000,
    });
    return { code: 0, stdout: result.stdout, stderr: result.stderr };
  } catch (error) {
    const failure = error as Error & { code?: number; stdout?: string; stderr?: string };
    return {
      code: typeof failure.code === "number" ? failure.code : 1,
      stdout: failure.stdout ?? "",
      stderr: failure.stderr ?? failure.message,
    };
  }
}

function loadExistingResults(
  runDir: string,
  plannedNames: Set<string>,
  taskProvenance: Map<string, TaskProvenance>,
): Map<string, EffectivenessRunRecord> {
  const records = new Map<string, EffectivenessRunRecord>();
  if (!existsSync(runDir)) return records;
  for (const name of readdirSync(runDir)) {
    if (!name.endsWith(".json") || name === "summary.json") continue;
    if (!plannedNames.has(name)) continue;
    try {
      const record = JSON.parse(readFileSync(join(runDir, name), "utf-8")) as EffectivenessRunRecord;
      const expected = taskProvenance.get(record.task_id);
      if (
        expected &&
        record.condition &&
        record.model_id &&
        record.verifier_sha === expected.verifier_sha &&
        record.task_fixture_sha === expected.task_fixture_sha
      ) {
        records.set(name, record);
      }
    } catch {
      // Malformed partial artifacts are ignored and rerun.
    }
  }
  return records;
}

function summarizeConditions(records: EffectivenessRunRecord[]): Record<string, unknown> {
  const byCondition: Record<
    string,
    { total: number; passed: number; scratchUsed: number; durationMs: number }
  > = {};
  for (const record of records) {
    const bucket = byCondition[record.condition] ?? {
      total: 0,
      passed: 0,
      scratchUsed: 0,
      durationMs: 0,
    };
    bucket.total += 1;
    if (record.passed) bucket.passed += 1;
    if (record.behavior_note === "scratch_used") bucket.scratchUsed += 1;
    bucket.durationMs += record.duration_ms;
    byCondition[record.condition] = bucket;
  }
  const conditions: Record<string, unknown> = {};
  for (const [condition, bucket] of Object.entries(byCondition)) {
    conditions[condition] = {
      total: bucket.total,
      passed: bucket.passed,
      scratchUsed: bucket.scratchUsed,
      pass_rate: bucket.total ? Number((bucket.passed / bucket.total).toFixed(4)) : 0,
      scratch_use_rate: bucket.total ? Number((bucket.scratchUsed / bucket.total).toFixed(4)) : 0,
      average_duration_ms: bucket.total ? Math.round(bucket.durationMs / bucket.total) : 0,
    };
  }
  return conditions;
}

function summarize(records: EffectivenessRunRecord[]): Record<string, unknown> {
  const taskIds = [...new Set(records.map((record) => record.task_id))].sort();
  const tasks = Object.fromEntries(
    taskIds.map((taskId) => {
      const taskRecords = records.filter((record) => record.task_id === taskId);
      const passed = taskRecords.filter((record) => record.passed).length;
      return [
        taskId,
        {
          total_runs: taskRecords.length,
          passed,
          pass_rate: taskRecords.length ? Number((passed / taskRecords.length).toFixed(4)) : 0,
          conditions: summarizeConditions(taskRecords),
        },
      ];
    }),
  );
  return {
    total_runs: records.length,
    passed: records.filter((record) => record.passed).length,
    conditions: summarizeConditions(records),
    tasks,
  };
}

interface TaskProvenance {
  verifier_sha: string;
  task_fixture_sha: string;
}

function provenanceForTask(task: EffectivenessTaskMetadata): TaskProvenance {
  return {
    verifier_sha: fixtureSha(join(task.taskDir, "verify.sh")),
    task_fixture_sha: directorySha(task.taskDir),
  };
}

function directorySha(root: string): string {
  const hash = createHash("sha256");
  const visit = (directory: string, relative: string): void => {
    const entries = readdirSync(directory, { withFileTypes: true })
      .sort((left, right) => left.name.localeCompare(right.name));
    for (const entry of entries) {
      const absolute = join(directory, entry.name);
      const childRelative = relative ? join(relative, entry.name) : entry.name;
      if (entry.isDirectory()) {
        visit(absolute, childRelative);
      } else if (entry.isFile()) {
        hash.update(childRelative).update("\0").update(readFileSync(absolute)).update("\0");
      }
    }
  };
  visit(root, "");
  return hash.digest("hex").slice(0, 16);
}

function selectTasks(
  tasks: EffectivenessTaskMetadata[],
  requestedIds: string[],
): EffectivenessTaskMetadata[] {
  if (!requestedIds.length) return tasks;
  const available = new Set(tasks.map((task) => task.id));
  const unknown = requestedIds.filter((id) => !available.has(id));
  if (unknown.length) {
    throw new Error(
      `Unknown --task-ids value(s): ${unknown.join(",")}. Available task IDs: ${[...available].sort().join(",")}`,
    );
  }
  const requested = new Set(requestedIds);
  return tasks.filter((task) => requested.has(task.id));
}

function selectConditions(requested: string[]): Condition[] {
  if (!requested.length) return CONDITIONS;
  const unknown = requested.filter((condition) => !CONDITIONS.includes(condition as Condition));
  if (unknown.length) {
    throw new Error(
      `Unknown --conditions value(s): ${unknown.join(",")}. Available conditions: ${CONDITIONS.join(",")}`,
    );
  }
  return CONDITIONS.filter((condition) => requested.includes(condition));
}

function shortHash(value: string): string {
  return createHash("sha256").update(value).digest("hex").slice(0, 8);
}

function firstNonEmptyLine(value: string): string | undefined {
  return value.split("\n").map((line) => line.trim()).find(Boolean);
}

function safeName(value: string): string {
  return value.replace(/[^a-zA-Z0-9._-]+/g, "-");
}

function unique(values: string[]): string[] {
  return [...new Set(values)];
}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    console.error(error);
    process.exit(2);
  });
