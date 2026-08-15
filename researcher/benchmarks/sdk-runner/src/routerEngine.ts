/**
 * Injected, zero-call execution coordinator for the Stage 2 router protocol.
 *
 * This module deliberately knows nothing about the Cursor SDK or credentials.
 * The durable store owns claims, budgets, resume decisions, and terminal
 * publication. The engine only orders those operations around injected source
 * validation, output validation, and an executor supplied by a later adapter.
 */

import {
  buildRouterRunManifest,
  parseRouterRunManifestFile,
  type BuiltRouterRunManifest,
  type RouterPlanItem,
} from "./routerManifest.ts";
import { captureExactNamedInputs } from "./sourceFreeze.ts";
import type {
  RouterAttemptSettlement,
  RouterInflightClaim,
  RouterResumeState,
  RouterRunStore,
  RouterUsage as StoredRouterUsage,
} from "./routerRunStore.ts";

const MAX_ENGINE_FORMAT_ATTEMPTS = 2;

export interface RouterClock {
  now(): string;
}

export interface RouterExecutionContext {
  readonly item: RouterPlanItem;
  readonly attempt: number;
  readonly claim: RouterInflightClaim;
}

export interface RouterSourceRevalidationGuard {
  revalidate(context: RouterExecutionContext): void | Promise<void>;
}

export type RouterUsage = StoredRouterUsage;

interface RouterExecutorMetadata {
  readonly duration_ms: number;
  readonly request_id?: string;
  readonly resolved_model_id?: string;
  readonly usage?: RouterUsage;
}

export type RouterExecutorOutcome =
  | (RouterExecutorMetadata & {
      readonly status: "finished";
      readonly raw_text: string;
    })
  | (RouterExecutorMetadata & {
      readonly status: "provider_error";
      readonly error_code: string;
      readonly error_message: string;
    })
  | (RouterExecutorMetadata & {
      readonly status: "cancelled";
      readonly error_code?: string;
      readonly error_message?: string;
    })
  | (RouterExecutorMetadata & {
      readonly status: "model_unavailable";
      readonly error_code: string;
      readonly error_message: string;
    });

export interface RouterExecutor {
  execute(context: RouterExecutionContext): Promise<RouterExecutorOutcome>;
}

export type RouterOutputValidation =
  | {
      readonly valid: true;
      readonly ranking: readonly string[];
      readonly confidence_millionths: number;
      readonly rationale: string;
    }
  | {
      readonly valid: false;
      readonly reason: "unparseable" | "schema_invalid";
    };

export interface RouterOutputValidator {
  validate(rawText: string, item: RouterPlanItem): RouterOutputValidation;
}

export type RouterEngineStore = Pick<
  RouterRunStore,
  "acquire" | "initialize" | "preflight" | "claim" | "settle" | "writeTerminal" | "release"
>;

export interface RouterEngineOptions {
  readonly store: RouterEngineStore;
  readonly ownerId: string;
  readonly clock: RouterClock;
  readonly sourceGuard: RouterSourceRevalidationGuard;
  readonly executor: RouterExecutor;
  readonly outputValidator: RouterOutputValidator;
}

export interface RouterManifestSourceGuardOptions {
  readonly repoRoot: string;
  readonly inputPaths: Readonly<Record<string, string>>;
  readonly manifest: BuiltRouterRunManifest;
}

/**
 * Rebuild the full manifest from a fresh trusted clean-source capture before
 * executor reachability. This also binds the current Node/platform runtime.
 */
export function createRouterManifestSourceGuard(
  options: RouterManifestSourceGuardOptions,
): RouterSourceRevalidationGuard {
  const expected = parseRouterRunManifestFile(options.manifest.canonicalBytes);
  if (expected.digest !== options.manifest.digest) {
    throw new TypeError("source guard manifest bytes and digest disagree");
  }
  const repoRoot = options.repoRoot;
  const inputPaths = Object.freeze({ ...options.inputPaths });
  const expectedItems = new Map(
    expected.manifest.plan.items.map((item) => [item.item_id, item]),
  );
  return Object.freeze({
    revalidate(context: RouterExecutionContext): void {
      const expectedItem = expectedItems.get(context.item.item_id);
      if (
        context.claim.manifest_digest !== expected.digest ||
        context.claim.item_id !== context.item.item_id ||
        context.claim.attempt !== context.attempt ||
        context.attempt > expected.manifest.plan.max_format_attempts ||
        context.claim.estimated_cost_microusd !==
          expected.manifest.cost.estimated_micro_usd_per_sdk_attempt ||
        expectedItem === undefined ||
        !canonicalItemEqual(context.item, expectedItem)
      ) {
        throw new TypeError("execution context does not belong to the guarded manifest");
      }
      const capture = captureExactNamedInputs(repoRoot, inputPaths);
      const current = buildRouterRunManifest({
        capture,
        models: expected.manifest.plan.models,
        reps: expected.manifest.plan.reps,
        seed: expected.manifest.plan.seed,
        maxFormatAttempts: expected.manifest.plan.max_format_attempts,
        estimatedMicroUsdPerSdkAttempt:
          expected.manifest.cost.estimated_micro_usd_per_sdk_attempt,
        maxSdkInvocations: expected.manifest.cost.max_sdk_invocations,
        capMicroUsd: expected.manifest.cost.cap_micro_usd,
      });
      if (current.digest !== expected.digest) {
        throw new TypeError("current source, inputs, runtime, or plan differ from the manifest");
      }
    },
  });
}

function canonicalItemEqual(left: RouterPlanItem, right: RouterPlanItem): boolean {
  return left.item_id === right.item_id &&
    left.prompt_id === right.prompt_id &&
    left.model_id === right.model_id &&
    left.rep === right.rep &&
    left.shuffle_seed === right.shuffle_seed;
}

export type RouterEngineFailureStage =
  | "claim_validation"
  | "source_revalidation"
  | "executor"
  | "output_validator"
  | "settlement";

/**
 * A post-claim operation failed before a matching settlement was durable.
 * The unmatched claim is intentional evidence; a later preflight must block
 * rather than infer that the paid effect did or did not occur.
 */
export class RouterReconciliationRequiredError extends Error {
  readonly code = "RECONCILIATION_REQUIRED" as const;
  readonly stage: RouterEngineFailureStage;
  readonly itemId: string;
  readonly attempt: number;

  constructor(
    stage: RouterEngineFailureStage,
    claim: RouterInflightClaim,
    cause: unknown,
  ) {
    super(
      `[RECONCILIATION_REQUIRED] ${stage} failed after durable claim for ` +
        `${claim.item_id} attempt ${claim.attempt}`,
      { cause },
    );
    this.name = "RouterReconciliationRequiredError";
    this.stage = stage;
    this.itemId = claim.item_id;
    this.attempt = claim.attempt;
  }
}

/** Execute the manifest plan sequentially through the injected boundaries. */
export async function runRouterEngine(options: RouterEngineOptions): Promise<RouterResumeState> {
  const lease = await options.store.acquire(options.ownerId, options.clock.now());
  try {
    await options.store.initialize(lease);
    while (true) {
      const state = await options.store.preflight(lease);

      if (state.terminal_pending.length > 0) {
        for (const item of state.terminal_pending) {
          await options.store.writeTerminal(lease, item.item_id);
        }
        continue;
      }

      const next = state.pending[0];
      if (next === undefined) {
        return state;
      }
      requireEligibleAttempt(next.next_attempt);

      const claim = await options.store.claim(
        lease,
        next.item.item_id,
        options.clock.now(),
      );
      await afterClaim("claim_validation", claim, () => {
        if (claim.item_id !== next.item.item_id || claim.attempt !== next.next_attempt) {
          throw new TypeError("durable claim does not match the selected pending attempt");
        }
      });
      const context: RouterExecutionContext = {
        item: next.item,
        attempt: claim.attempt,
        claim,
      };

      await afterClaim("source_revalidation", claim, () =>
        options.sourceGuard.revalidate(context),
      );
      const outcome = await afterClaim("executor", claim, () =>
        options.executor.execute(context),
      );
      const settlement = await afterClaim("output_validator", claim, () =>
        settlementForOutcome(outcome, context, options.outputValidator, options.clock),
      );
      await afterClaim("settlement", claim, () =>
        options.store.settle(lease, claim, settlement),
      );
    }
  } finally {
    await options.store.release(lease);
  }
}

function requireEligibleAttempt(attempt: number): void {
  if (
    !Number.isSafeInteger(attempt) ||
    attempt < 1 ||
    attempt > MAX_ENGINE_FORMAT_ATTEMPTS
  ) {
    throw new TypeError(
      `pending attempt must be an integer from 1 through ${MAX_ENGINE_FORMAT_ATTEMPTS}`,
    );
  }
}

async function afterClaim<T>(
  stage: RouterEngineFailureStage,
  claim: RouterInflightClaim,
  operation: () => T | Promise<T>,
): Promise<T> {
  try {
    return await operation();
  } catch (error) {
    if (error instanceof RouterReconciliationRequiredError) throw error;
    throw new RouterReconciliationRequiredError(stage, claim, error);
  }
}

function settlementForOutcome(
  outcome: RouterExecutorOutcome,
  context: RouterExecutionContext,
  validator: RouterOutputValidator,
  clock: RouterClock,
): RouterAttemptSettlement {
  validateExecutorOutcome(outcome);
  const common = settlementMetadata(outcome, clock.now());

  if (outcome.status !== "finished") {
    return {
      ...common,
      status: outcome.status,
      ...optionalString("error_code", outcome.error_code),
      ...optionalString("error_message", outcome.error_message),
    };
  }

  if (outcome.raw_text.trim().length === 0) {
    return {
      ...common,
      status: "format_failure",
      error_code: "FORMAT_EMPTY",
      error_message: "finished output was empty",
    };
  }

  const validation = validator.validate(outcome.raw_text, context.item);
  validateOutputValidation(validation);
  if (!validation.valid) {
    const code =
      validation.reason === "unparseable" ? "FORMAT_UNPARSEABLE" : "FORMAT_SCHEMA_INVALID";
    return {
      ...common,
      status: "format_failure",
      raw_text: outcome.raw_text,
      error_code: code,
      error_message:
        validation.reason === "unparseable"
          ? "finished output was not parseable"
          : "finished output did not match the router output schema",
    };
  }

  return {
    ...common,
    status: "finished",
    raw_text: outcome.raw_text,
    ranking: [...validation.ranking],
    confidence_millionths: validation.confidence_millionths,
    rationale: validation.rationale,
  };
}

function settlementMetadata(
  outcome: RouterExecutorOutcome,
  finishedAt: string,
): Pick<
  RouterAttemptSettlement,
  "finished_at" | "duration_ms" | "request_id" | "resolved_model_id" | "usage"
> {
  return {
    finished_at: finishedAt,
    duration_ms: outcome.duration_ms,
    ...optionalString("request_id", outcome.request_id),
    ...optionalString("resolved_model_id", outcome.resolved_model_id),
    ...(outcome.usage === undefined ? {} : { usage: { ...outcome.usage } }),
  };
}

function optionalString<Key extends "request_id" | "resolved_model_id" | "error_code" | "error_message">(
  key: Key,
  value: string | undefined,
): Partial<Record<Key, string>> {
  return value === undefined ? {} : { [key]: value } as Partial<Record<Key, string>>;
}

function validateExecutorOutcome(outcome: RouterExecutorOutcome): void {
  if (!outcome || typeof outcome !== "object") {
    throw new TypeError("executor outcome must be an object");
  }
  if (!Number.isSafeInteger(outcome.duration_ms) || outcome.duration_ms < 0) {
    throw new TypeError("executor duration_ms must be a non-negative safe integer");
  }
  validateOptionalText(outcome.request_id, "executor request_id");
  validateOptionalText(outcome.resolved_model_id, "executor resolved_model_id");
  if (outcome.usage !== undefined) validateUsage(outcome.usage);

  switch (outcome.status) {
    case "finished":
      assertAllowedKeys(outcome, [
        "status", "duration_ms", "request_id", "resolved_model_id", "usage", "raw_text",
      ], "finished executor outcome");
      if (typeof outcome.raw_text !== "string") {
        throw new TypeError("finished executor outcome requires raw_text");
      }
      return;
    case "provider_error":
    case "model_unavailable":
      assertAllowedKeys(outcome, [
        "status", "duration_ms", "request_id", "resolved_model_id", "usage", "error_code",
        "error_message",
      ], `${outcome.status} executor outcome`);
      validateRequiredText(outcome.error_code, `${outcome.status} error_code`);
      validateRequiredText(outcome.error_message, `${outcome.status} error_message`);
      return;
    case "cancelled":
      assertAllowedKeys(outcome, [
        "status", "duration_ms", "request_id", "resolved_model_id", "usage", "error_code",
        "error_message",
      ], "cancelled executor outcome");
      validateOptionalText(outcome.error_code, "cancelled error_code");
      validateOptionalText(outcome.error_message, "cancelled error_message");
      return;
    default:
      throw new TypeError("executor outcome has an unsupported status");
  }
}

function validateOutputValidation(validation: RouterOutputValidation): void {
  if (!validation || typeof validation !== "object" || typeof validation.valid !== "boolean") {
    throw new TypeError("output validator result must be a tagged object");
  }
  if (!validation.valid) {
    assertExactKeys(validation, ["valid", "reason"], "output validator failure");
    if (validation.reason !== "unparseable" && validation.reason !== "schema_invalid") {
      throw new TypeError("output validator returned an invalid failure reason");
    }
    return;
  }
  assertExactKeys(
    validation,
    ["valid", "ranking", "confidence_millionths", "rationale"],
    "output validator success",
  );
  if (
    !Array.isArray(validation.ranking) ||
    validation.ranking.length === 0 ||
    validation.ranking.some((value) => typeof value !== "string" || !value.trim()) ||
    new Set(validation.ranking).size !== validation.ranking.length
  ) {
    throw new TypeError("output validator returned an invalid ranking");
  }
  if (
    !Number.isSafeInteger(validation.confidence_millionths) ||
    validation.confidence_millionths < 0 ||
    validation.confidence_millionths > 1_000_000
  ) {
    throw new TypeError("output validator returned an invalid confidence_millionths");
  }
  validateRequiredText(validation.rationale, "output validator rationale");
}

function validateUsage(usage: RouterUsage): void {
  if (!usage || typeof usage !== "object" || Array.isArray(usage)) {
    throw new TypeError("executor usage must be an object");
  }
  const fields = [
    "input_tokens",
    "output_tokens",
    "cache_read_tokens",
    "cache_write_tokens",
    "total_tokens",
    "reasoning_tokens",
  ] as const;
  assertExactKeys(usage, fields, "executor usage");
  for (const name of fields) {
    const value = usage[name];
    if (!Number.isSafeInteger(value) || value < 0) {
      throw new TypeError(`executor usage ${name} must be a non-negative safe integer`);
    }
  }
}

function assertAllowedKeys(value: object, allowed: readonly string[], label: string): void {
  const unexpected = Object.keys(value).find((key) => !allowed.includes(key));
  if (unexpected !== undefined) {
    throw new TypeError(`${label} contains unsupported field ${unexpected}`);
  }
}

function assertExactKeys(value: object, expected: readonly string[], label: string): void {
  const actual = Object.keys(value);
  if (
    actual.length !== expected.length ||
    actual.some((key) => !expected.includes(key))
  ) {
    throw new TypeError(`${label} fields do not match the closed contract`);
  }
}

function validateOptionalText(value: string | undefined, label: string): void {
  if (value !== undefined) validateRequiredText(value, label);
}

function validateRequiredText(value: string, label: string): void {
  if (typeof value !== "string" || !value.trim()) {
    throw new TypeError(`${label} must be a non-empty string`);
  }
}
