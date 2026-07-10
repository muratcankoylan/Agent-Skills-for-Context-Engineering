/**
 * Stage 2: Skill router benchmark.
 *
 * Hypothesis: the activation-scenario descriptions in v2.2.0 frontmatter let a
 * frontier model route prompts to the correct skill at high top-1 accuracy.
 *
 * Procedure (per the methodology in researcher/benchmarks/PLAN.md):
 *   1. Load 50+ ground-truth prompts from router/prompts.jsonl.
 *   2. For each (prompt, model, replication), build a routing prompt with the
 *      16 skill descriptions in deterministically-shuffled order.
 *   3. Call native Codex CLI in an isolated temporary cwd through Headroom
 *      with project rules, plugins, and hooks disabled.
 *   4. Parse strict JSON ranking. Score top-1 and top-3 accuracy.
 *   5. Persist per-run JSON + transcript; append a summary to history.
 *
 * Runs only execute when a hard invocation cap is provided.
 * --dry-run prints the plan and cost forecast and exits cleanly.
 */

import { join } from "node:path";
import {
  existsSync,
  mkdirSync,
  mkdtempSync,
  readdirSync,
  readFileSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";

import {
  RESEARCHER_DIR,
  appendHistoryEntry,
  assertBudget,
  buildRunPlan,
  fixtureSha,
  forecastCost,
  loadJsonl,
  loadSkillDescriptions,
  parseCliFlags,
  repoCommitSha,
  resolveConfig,
  resultFileName,
  runCodexPrompt,
  runConcurrently,
  runHeader,
  shuffleSeeded,
  runtimeFingerprint,
  todayUtc,
  utcNow,
  writeJson,
} from "./common.ts";

interface RouterPrompt {
  prompt_id: string;
  prompt: string;
  expected_primary_skill: string;
  acceptable_secondary_skills?: string[];
  rejected_skills?: string[];
  reason?: string;
}

interface RouterRunRecord {
  prompt_id: string;
  model_id: string;
  rep: number;
  shuffle_seed: number;
  attempts?: number;
  status: "format_failure" | "model_unavailable" | "finished" | "error" | "cancelled" | "dry_run";
  duration_ms?: number;
  predicted_primary?: string;
  predicted_top3?: string[];
  top1_correct?: boolean;
  top3_correct?: boolean;
  raw_text?: string;
  session_id?: string;
  notes?: string;
}

const DEFAULT_FIXTURE = join(RESEARCHER_DIR, "benchmarks", "router", "prompts.jsonl");
const ROUTING_PROMPT_TEMPLATE = join(RESEARCHER_DIR, "benchmarks", "router", "routing-prompt.md");
const RESULTS_DIR = join(RESEARCHER_DIR, "benchmarks", "router", "results");
const HISTORY_PATH = join(RESEARCHER_DIR, "reports", "router-history.jsonl");

const ESTIMATED_TOKENS_INPUT = 4000;
const ESTIMATED_TOKENS_OUTPUT = 400;
const ESTIMATED_USD_PER_RUN = 0;
const MAX_FORMAT_ATTEMPTS = 2;

async function main(): Promise<number> {
  const flags = parseCliFlags(process.argv.slice(2));
  const config = resolveConfig(flags, DEFAULT_FIXTURE);
  if (config.taskIds.length || config.conditions.length) {
    throw new Error("--task-ids and --conditions are supported only by the effectiveness runner.");
  }

  console.log(runHeader("Router Benchmark (Stage 2)"));
  console.log(`fixture: ${config.fixturePath}`);
  console.log(`models: ${config.models.join(", ")}`);
  console.log(`reps per (prompt, model): ${config.reps}`);
  console.log(`seed: ${config.seed}`);
  console.log(`concurrency: ${config.concurrency}`);
  console.log(`resume: ${!config.noResume}`);
  console.log(`dry-run: ${config.dryRun}`);
  console.log(`runtime: ${runtimeFingerprint()}`);

  const prompts = loadJsonl<RouterPrompt>(config.fixturePath);
  console.log(`prompts loaded: ${prompts.length}`);
  if (!prompts.length) {
    console.error("No prompts in fixture; aborting.");
    return 1;
  }

  const skills = loadSkillDescriptions();
  console.log(`skills available: ${skills.length}`);

  const plan = buildRunPlan(
    prompts.map((p) => p.prompt_id),
    config.models,
    config.reps,
    config.seed,
  );
  const forecast = forecastCost(
    plan,
    ESTIMATED_TOKENS_INPUT,
    ESTIMATED_TOKENS_OUTPUT,
    ESTIMATED_USD_PER_RUN * MAX_FORMAT_ATTEMPTS,
  );
  const worstCaseInvocations = plan.length * MAX_FORMAT_ATTEMPTS;
  console.log(`planned runs: ${forecast.totalRuns}`);
  console.log(`est. tokens per run: ${ESTIMATED_TOKENS_INPUT}in / ${ESTIMATED_TOKENS_OUTPUT}out`);
  console.log(`max attempts per run: ${MAX_FORMAT_ATTEMPTS}`);
  console.log(`max Codex invocations: ${worstCaseInvocations}`);
  console.log(`est. worst-case total cost: ${forecast.estimatedTotalUsd} USD`);

  if (worstCaseInvocations > config.maxRuns) {
    throw new Error(
      `Worst-case Hermes invocations ${worstCaseInvocations} exceeds --max-runs ${config.maxRuns}. ` +
        "Increase --max-runs or lower the plan size.",
    );
  }
  assertBudget(plan, forecast, config);

  if (config.dryRun) {
    console.log("Dry-run: no Hermes/Codex calls made.");
    if (plan[0]) {
      const sample = prompts.find((p) => p.prompt_id === plan[0].promptId)!;
      const shuffled = shuffleSeeded(skills.map((s) => s.name), plan[0].shuffleSeed);
      console.log("sample plan item:", plan[0]);
      console.log("sample skill order:", shuffled);
      console.log("sample prompt:", sample.prompt);
    }
    return 0;
  }

  const promptTemplate = await loadPromptTemplate();
  const runDir = join(RESULTS_DIR, `${todayUtc()}-${config.seed}`);
  mkdirSync(runDir, { recursive: true });

  const existingResults = config.noResume ? new Map<string, RouterRunRecord>() : loadExistingResults(runDir);
  const remaining = plan.filter((item) => !existingResults.has(resultFileName(item.promptId, item.modelId, item.rep)));
  if (existingResults.size) {
    console.log(`resume: ${existingResults.size} prior results found, ${remaining.length} runs remaining`);
  }

  const totalToExecute = remaining.length;
  const startedAt = Date.now();
  const isolationDir = mkdtempSync(join(tmpdir(), "researcher-router-codex-"));
  let completed = 0;
  const newResults: RouterRunRecord[] = [];
  const printLock = { value: Promise.resolve() };

  await runConcurrently(remaining, config.concurrency, async (item, _index) => {
    const prompt = prompts.find((p) => p.prompt_id === item.promptId);
    if (!prompt) return;
    const shuffledSkills = shuffleSeeded(skills, item.shuffleSeed);
    const filled = renderPrompt(promptTemplate, shuffledSkills, prompt.prompt);

    const record: RouterRunRecord = {
      prompt_id: item.promptId,
      model_id: item.modelId,
      rep: item.rep,
      shuffle_seed: item.shuffleSeed,
      attempts: 0,
      status: "error",
    };
    const started = Date.now();
    try {
      for (let attempt = 1; attempt <= MAX_FORMAT_ATTEMPTS; attempt++) {
        record.attempts = attempt;
        const result = await runCodexPrompt(filled, {
          model: item.modelId,
          cwd: isolationDir,
          sandbox: "read-only",
        });
        record.status = "finished";
        record.raw_text = result.finalText;
        if (result.sessionId) record.session_id = result.sessionId;
        const parsed = parseRouterJson(record.raw_text);
        if (parsed) {
          record.predicted_primary = parsed[0];
          record.predicted_top3 = parsed.slice(0, 3);
          record.top1_correct = parsed[0] === prompt.expected_primary_skill;
          record.top3_correct = parsed.slice(0, 3).includes(prompt.expected_primary_skill);
          break;
        }
        record.status = "format_failure";
        record.notes = attempt < MAX_FORMAT_ATTEMPTS ? "format failure; retrying once" : "format failure after retry";
      }
    } catch (error) {
      record.notes = (error as Error).message;
    }
    record.duration_ms = Date.now() - started;
    writeJson(join(runDir, resultFileName(item.promptId, item.modelId, item.rep)), record);
    newResults.push(record);

    completed++;
    const elapsedMs = Date.now() - startedAt;
    const avgMs = elapsedMs / completed;
    const remainingMs = Math.round(avgMs * (totalToExecute - completed));
    const top1 = record.top1_correct === true ? "T1" : record.top1_correct === false ? "  " : "??";
    const padded = String(completed).padStart(4, " ");
    const total = String(totalToExecute).padStart(4, " ");
    const line = `[${padded}/${total}] ${item.modelId.padEnd(20)} ${item.promptId} rep=${item.rep} ${record.status.padEnd(18)} ${(record.duration_ms ?? 0)
      .toString()
      .padStart(5, " ")}ms ${top1} ETA=${formatDuration(remainingMs)}`;
    // Serialize console writes so concurrent workers do not interleave lines.
    printLock.value = printLock.value.then(() => {
      console.log(line);
    });
  });
  rmSync(isolationDir, { recursive: true, force: true });

  const results: RouterRunRecord[] = [...existingResults.values(), ...newResults];

  const summary = summarize(results, prompts);
  const metadata = {
    timestamp: utcNow(),
    repo_sha: repoCommitSha(),
    fixture_sha: fixtureSha(config.fixturePath),
    seed: config.seed,
    models: config.models,
    reps: config.reps,
    prompts: prompts.length,
  };
  writeJson(join(runDir, "summary.json"), { ...metadata, summary });
  appendHistoryEntry(HISTORY_PATH, { ...metadata, summary });

  console.log("summary:", summary);
  console.log(`raw results in ${runDir}`);
  return 0;
}

async function loadPromptTemplate(): Promise<string> {
  const { readFileSync, existsSync } = await import("node:fs");
  if (!existsSync(ROUTING_PROMPT_TEMPLATE)) {
    throw new Error(`Routing prompt template missing: ${ROUTING_PROMPT_TEMPLATE}`);
  }
  return readFileSync(ROUTING_PROMPT_TEMPLATE, "utf-8");
}

function renderPrompt(
  template: string,
  shuffledSkills: Array<{ name: string; description: string }>,
  userPrompt: string,
): string {
  const skillBlock = shuffledSkills
    .map((skill, index) => `${index + 1}. ${skill.name}\n   ${skill.description}`)
    .join("\n\n");
  return template
    .replace("{{SKILL_BLOCK}}", skillBlock)
    .replace("{{USER_PROMPT}}", userPrompt)
    .replace("{{SKILL_COUNT}}", String(shuffledSkills.length));
}

function parseRouterJson(raw: string): string[] | null {
  const match = raw.match(/\{[\s\S]*\}/);
  if (!match) return null;
  try {
    const parsed = JSON.parse(match[0]);
    if (Array.isArray(parsed.ranking)) {
      return parsed.ranking.map((value: unknown) => String(value));
    }
    return null;
  } catch {
    return null;
  }
}

function loadExistingResults(runDir: string): Map<string, RouterRunRecord> {
  const map = new Map<string, RouterRunRecord>();
  if (!existsSync(runDir)) return map;
  for (const entry of readdirSync(runDir)) {
    if (entry === "summary.json" || !entry.endsWith(".json")) continue;
    try {
      const parsed = JSON.parse(readFileSync(join(runDir, entry), "utf-8")) as RouterRunRecord;
      if (parsed && parsed.prompt_id && parsed.model_id !== undefined && parsed.rep !== undefined) {
        map.set(entry, parsed);
      }
    } catch {
      // Skip malformed leftovers; next sweep will overwrite.
    }
  }
  return map;
}

function formatDuration(ms: number): string {
  if (!Number.isFinite(ms) || ms < 0) return "unknown";
  const totalSec = Math.round(ms / 1000);
  const h = Math.floor(totalSec / 3600);
  const m = Math.floor((totalSec % 3600) / 60);
  const s = totalSec % 60;
  if (h > 0) return `${h}h${m.toString().padStart(2, "0")}m`;
  if (m > 0) return `${m}m${s.toString().padStart(2, "0")}s`;
  return `${s}s`;
}

function summarize(results: RouterRunRecord[], prompts: RouterPrompt[]): Record<string, unknown> {
  const perModel: Record<string, { total: number; format_failures: number; top1: number; top3: number }> = {};
  for (const r of results) {
    const bucket = perModel[r.model_id] ?? { total: 0, format_failures: 0, top1: 0, top3: 0 };
    bucket.total += 1;
    if (r.status === "format_failure") bucket.format_failures += 1;
    if (r.top1_correct) bucket.top1 += 1;
    if (r.top3_correct) bucket.top3 += 1;
    perModel[r.model_id] = bucket;
  }
  const summary: Record<string, unknown> = {};
  for (const [model, b] of Object.entries(perModel)) {
    summary[model] = {
      total: b.total,
      format_failure_rate: Number((b.format_failures / b.total).toFixed(4)),
      top1_accuracy: Number((b.top1 / b.total).toFixed(4)),
      top3_accuracy: Number((b.top3 / b.total).toFixed(4)),
    };
  }
  summary["promptCount"] = prompts.length;
  return summary;
}

void writeFileSync;

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    console.error(error);
    process.exit(2);
  });
