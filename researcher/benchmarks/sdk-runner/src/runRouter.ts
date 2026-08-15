/**
 * Stage 2 skill-router benchmark planner.
 *
 * This revision validates the fixture, constructs the deterministic plan, and
 * enforces the worst-case invocation and cost ceilings. Live execution is
 * deliberately absent. Reintroducing an SDK call requires a separate,
 * human-merged activation with manifest-bound provenance and crash-safe resume.
 */

import { join } from "node:path";

import {
  RESEARCHER_DIR,
  assertBudget,
  buildRunPlan,
  checkedRunCardinality,
  forecastCost,
  loadJsonl,
  loadSkillDescriptions,
  parseCliFlags,
  resolveConfig,
  runHeader,
  shuffleSeeded,
} from "./common.ts";

interface RouterPrompt {
  prompt_id: string;
  prompt: string;
  expected_primary_skill: string;
  acceptable_secondary_skills?: string[];
  rejected_skills?: string[];
  reason?: string;
}

const DEFAULT_FIXTURE = join(RESEARCHER_DIR, "benchmarks", "router", "prompts.jsonl");
const ESTIMATED_TOKENS_INPUT = 4000;
const ESTIMATED_TOKENS_OUTPUT = 400;
const ESTIMATED_USD_PER_RUN = 0.012;
const MAX_FORMAT_ATTEMPTS = 2;
const LIVE_BLOCK_MESSAGE =
  "Live Cursor execution is blocked pending an accepted audit and canary for the pinned SDK lock. " +
  "Use --dry-run; activation requires a separate human-merged change.";

async function main(): Promise<number> {
  const flags = parseCliFlags(process.argv.slice(2));
  if (!flags.dryRun) {
    console.error(LIVE_BLOCK_MESSAGE);
    return 1;
  }
  const config = resolveConfig(flags, DEFAULT_FIXTURE);

  console.log(runHeader("Router Benchmark (Stage 2)"));
  console.log(`fixture: ${config.fixturePath}`);
  console.log(`models: ${config.models.join(", ")}`);
  console.log(`reps per (prompt, model): ${config.reps}`);
  console.log(`seed: ${config.seed}`);
  console.log(`dry-run: ${config.dryRun}`);

  const prompts = loadJsonl<RouterPrompt>(config.fixturePath);
  console.log(`prompts loaded: ${prompts.length}`);
  if (!prompts.length) {
    console.error("No prompts in fixture; aborting.");
    return 1;
  }

  const skills = loadSkillDescriptions();
  console.log(`skills available: ${skills.length}`);
  const promptIds = validateRouterPrompts(prompts, skills.map((skill) => skill.name));

  const logicalRuns = checkedRunCardinality(promptIds.length, config.models.length, config.reps);
  const worstCaseInvocations = logicalRuns * MAX_FORMAT_ATTEMPTS;
  if (worstCaseInvocations > config.maxRuns) {
    throw new Error(
      `Worst-case SDK invocations ${worstCaseInvocations} exceeds --max-runs ${config.maxRuns}. ` +
        "Increase --max-runs or lower the plan size.",
    );
  }

  const plan = buildRunPlan(promptIds, config.models, config.reps, config.seed);
  const forecast = forecastCost(
    plan,
    ESTIMATED_TOKENS_INPUT,
    ESTIMATED_TOKENS_OUTPUT,
    ESTIMATED_USD_PER_RUN * MAX_FORMAT_ATTEMPTS,
  );
  console.log(`planned runs: ${forecast.totalRuns}`);
  console.log(`est. tokens per run: ${ESTIMATED_TOKENS_INPUT}in / ${ESTIMATED_TOKENS_OUTPUT}out`);
  console.log(`max attempts per run: ${MAX_FORMAT_ATTEMPTS}`);
  console.log(`max SDK invocations: ${worstCaseInvocations}`);
  console.log(`est. worst-case total cost: ${forecast.estimatedTotalUsd} USD`);

  assertBudget(plan, forecast, config);

  if (config.dryRun) {
    console.log("Dry-run: no SDK calls made.");
    if (plan[0]) {
      const sample = prompts.find((prompt) => prompt.prompt_id === plan[0]?.promptId);
      if (!sample) throw new Error("Planned prompt is missing from the validated fixture.");
      const shuffled = shuffleSeeded(
        skills.map((skill) => skill.name),
        plan[0].shuffleSeed,
      );
      console.log("sample plan item:", plan[0]);
      console.log("sample skill order:", shuffled);
      console.log("sample prompt:", sample.prompt);
    }
    return 0;
  }

  throw new Error("unreachable: validated dry-run did not return");
}

function validateRouterPrompts(prompts: RouterPrompt[], skillNames: string[]): string[] {
  const knownKeys = new Set([
    "prompt_id",
    "prompt",
    "expected_primary_skill",
    "acceptable_secondary_skills",
    "rejected_skills",
    "reason",
  ]);
  const knownSkills = new Set(skillNames);
  const promptIds = new Set<string>();
  for (const [index, candidate] of prompts.entries()) {
    if (!candidate || typeof candidate !== "object" || Array.isArray(candidate)) {
      throw new Error(`Router fixture record ${index + 1} must be an object.`);
    }
    const record = candidate as unknown as Record<string, unknown>;
    const unknownKeys = Object.keys(record).filter((key) => !knownKeys.has(key));
    if (unknownKeys.length) {
      throw new Error(
        `Router fixture record ${index + 1} has unknown fields: ${unknownKeys.sort().join(", ")}.`,
      );
    }
    for (const field of ["prompt_id", "prompt", "expected_primary_skill"] as const) {
      if (typeof record[field] !== "string" || !record[field].trim()) {
        throw new Error(`Router fixture record ${index + 1} requires non-empty ${field}.`);
      }
    }
    const promptId = record.prompt_id as string;
    if (promptIds.has(promptId)) {
      throw new Error(`Router fixture contains duplicate prompt_id ${promptId}.`);
    }
    promptIds.add(promptId);

    const expected = record.expected_primary_skill as string;
    if (!knownSkills.has(expected)) {
      throw new Error(`Router fixture ${promptId} names unknown expected skill ${expected}.`);
    }
    for (const field of ["acceptable_secondary_skills", "rejected_skills"] as const) {
      const value = record[field];
      if (value === undefined) continue;
      if (
        !Array.isArray(value) ||
        value.some((entry) => typeof entry !== "string" || !entry.trim()) ||
        new Set(value).size !== value.length
      ) {
        throw new Error(`Router fixture ${promptId} requires ${field} to be unique skill ids.`);
      }
      for (const skill of value) {
        if (!knownSkills.has(skill)) {
          throw new Error(`Router fixture ${promptId} names unknown skill ${skill} in ${field}.`);
        }
      }
    }
    const acceptable = new Set((record.acceptable_secondary_skills as string[] | undefined) ?? []);
    const rejected = new Set((record.rejected_skills as string[] | undefined) ?? []);
    if (rejected.has(expected) || [...acceptable].some((skill) => rejected.has(skill))) {
      throw new Error(`Router fixture ${promptId} has overlapping accepted and rejected skills.`);
    }
    if (record.reason !== undefined && typeof record.reason !== "string") {
      throw new Error(`Router fixture ${promptId} requires reason to be a string when present.`);
    }
  }
  return [...promptIds];
}

main()
  .then((code) => process.exit(code))
  .catch((error) => {
    console.error(error);
    process.exit(2);
  });
