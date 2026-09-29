/**
 * Private, pre-activation manifest for the Stage 2 router runner.
 *
 * `router-run-manifest/v1` is intentionally runner-local. It is not a claim
 * against the organization schema registry and grants no execution authority.
 * The manifest contains only portable, frozen evidence; its content address is
 * returned alongside it rather than embedded as a self-digest.
 */

import {
  DurableJsonError,
  canonicalFileBytes,
  canonicalJsonBytes,
  domainSeparatedDigest,
  parseCanonicalFile,
  parseJsonStrict,
  sha256Bytes,
} from "./durableJson.ts";
import type { JsonValue, Sha256Digest } from "./durableJson.ts";
import {
  assertVerifiedExactNamedInputCapture,
} from "./sourceFreeze.ts";
import type {
  ExactNamedInputCapture,
  StableFileCapture,
} from "./sourceFreeze.ts";

export const ROUTER_RUN_MANIFEST_SCHEMA = "router-run-manifest/v1" as const;
export const MAX_ROUTER_PLAN_ITEMS = 100_000;
export const MAX_ROUTER_FORMAT_ATTEMPTS = 2;
export const MAX_ROUTER_MANIFEST_BYTES = 64 * 1024 * 1024;
export const MAX_ROUTER_PORTABLE_ID_LENGTH = 256;
const MAX_RUNTIME_TOKEN_LENGTH = 128;

const PLAN_ITEM_DOMAIN = "router-run-plan-item/v1";
const PLAN_DOMAIN = "router-run-plan/v1";
const MANIFEST_DOMAIN = "router-run-manifest/v1";
const SHUFFLE_SEED_DOMAIN = "router-run-shuffle-seed/v1";
const SHA256_PATTERN = /^sha256:[0-9a-f]{64}$/;
const PORTABLE_ID_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._:/+|=-]*$/;
const RUNTIME_TOKEN_PATTERN = /^[A-Za-z0-9][A-Za-z0-9._+-]*$/;
const REQUIRED_CAPTURE_NAMES = [
  "fixture",
  "inventory",
  "package_lock",
  "prompt_template",
  "skill_catalog",
] as const;

export type RouterManifestErrorCode =
  | "BUDGET_EXCEEDED"
  | "FORECAST_MISMATCH"
  | "INVALID_DIGEST"
  | "INVALID_FIELD"
  | "INVALID_USD"
  | "MISSING_FIELD"
  | "PLAN_CARDINALITY_MISMATCH"
  | "PLAN_DIGEST_MISMATCH"
  | "PLAN_ITEM_ID_MISMATCH"
  | "SOURCE_NOT_CLEAN"
  | "UNKNOWN_FIELD";

export class RouterManifestError extends Error {
  readonly code: RouterManifestErrorCode;
  readonly safeMessage: string;

  constructor(code: RouterManifestErrorCode, safeMessage: string) {
    super(`[${code}] ${safeMessage}`);
    this.name = "RouterManifestError";
    this.code = code;
    this.safeMessage = safeMessage;
  }
}

export interface RouterPlanItemSeed {
  readonly prompt_id: string;
  readonly model_id: string;
  readonly rep: number;
  readonly shuffle_seed: number;
}

export interface RouterPlanItem extends RouterPlanItemSeed {
  readonly item_id: Sha256Digest;
}

export interface RouterRunManifest {
  readonly schema: typeof ROUTER_RUN_MANIFEST_SCHEMA;
  readonly source: {
    readonly git_object_format: "sha1" | "sha256";
    readonly proposal_commit_oid: string;
    readonly proposal_tree_oid: string;
    readonly worktree_clean: true;
    readonly inventory_source_tree_digest: Sha256Digest;
  };
  readonly inputs: {
    readonly fixture: {
      readonly sha256: Sha256Digest;
      readonly size_bytes: number;
      readonly record_count: number;
    };
    readonly inventory: {
      readonly sha256: Sha256Digest;
      readonly size_bytes: number;
      readonly source_count: number;
    };
    readonly prompt_template: {
      readonly sha256: Sha256Digest;
      readonly size_bytes: number;
      readonly template_count: number;
    };
    readonly skill_catalog: {
      readonly sha256: Sha256Digest;
      readonly size_bytes: number;
      readonly skill_count: number;
      readonly skill_ids: readonly string[];
    };
    readonly package_lock: {
      readonly sha256: Sha256Digest;
      readonly size_bytes: number;
      readonly package_count: number;
    };
  };
  readonly runtime: {
    readonly node_version: string;
    readonly cursor_sdk_version: string;
    readonly platform: string;
    readonly arch: string;
    readonly tools: readonly [];
    readonly setting_sources: readonly [];
    readonly sdk_retries: false;
  };
  readonly plan: {
    readonly prompt_ids: readonly string[];
    readonly models: readonly string[];
    readonly reps: number;
    readonly seed: number;
    readonly max_format_attempts: number;
    readonly item_count: number;
    readonly items: readonly RouterPlanItem[];
    readonly items_digest: Sha256Digest;
  };
  readonly cost: {
    readonly currency: "USD";
    readonly estimated_micro_usd_per_sdk_attempt: number;
    readonly forecast_sdk_invocations: number;
    readonly max_sdk_invocations: number;
    readonly forecast_micro_usd: number;
    readonly cap_micro_usd: number;
  };
}

export interface RouterManifestBuildInput {
  /** In-process branded output from `captureExactNamedInputs`. */
  readonly capture: ExactNamedInputCapture;
  readonly models: readonly string[];
  readonly reps: number;
  readonly seed: number;
  readonly maxFormatAttempts: number;
  readonly estimatedMicroUsdPerSdkAttempt: number;
  readonly maxSdkInvocations: number;
  readonly capMicroUsd: number;
}

export interface BuiltRouterRunManifest {
  readonly manifest: RouterRunManifest;
  /** Canonical durable file bytes, including the single terminating LF. */
  readonly canonicalBytes: Buffer;
  /** External, domain-separated content address; never embedded in the manifest. */
  readonly digest: Sha256Digest;
}

/** Exact decimal conversion; floating-point arithmetic is never involved. */
export function parseUsdToMicroUsd(value: string): number {
  if (value !== value.trim() || value.startsWith("+") || value.startsWith("-")) {
    throw new RouterManifestError("INVALID_USD", "USD input cannot contain whitespace or a sign");
  }
  const match = /^(0|[1-9][0-9]*)(?:\.([0-9]{1,6}))?$/.exec(value);
  if (!match) {
    throw new RouterManifestError(
      "INVALID_USD",
      "USD input must be unsigned plain decimal with at most six fractional digits",
    );
  }
  const whole = BigInt(match[1] as string);
  const fraction = BigInt((match[2] ?? "").padEnd(6, "0") || "0");
  const micros = whole * 1_000_000n + fraction;
  if (micros > BigInt(Number.MAX_SAFE_INTEGER)) {
    throw new RouterManifestError("INVALID_USD", "USD micros exceed the safe integer range");
  }
  return Number(micros);
}

/** Derive a deterministic PRNG seed without delimiter-based identity encoding. */
export function deriveRouterShuffleSeed(
  promptId: string,
  modelId: string,
  rep: number,
  baseSeed: number,
): number {
  const identity = {
    base_seed: baseSeed,
    model_id: modelId,
    prompt_id: promptId,
    rep,
  } satisfies JsonValue;
  const digest = domainSeparatedDigest(SHUFFLE_SEED_DOMAIN, canonicalJsonBytes(identity));
  return Number.parseInt(digest.slice("sha256:".length, "sha256:".length + 8), 16);
}

/** Build the complete canonical cross-product ordering used by the validator. */
export function buildRouterPlanSeeds(
  promptIds: readonly string[],
  models: readonly string[],
  reps: number,
  baseSeed: number,
): RouterPlanItemSeed[] {
  validateDistinctIds(promptIds, "prompt_ids");
  validateDistinctIds(models, "models");
  expectPositiveInteger(reps, "reps");
  expectSafeInteger(baseSeed, "seed");
  const count = checkedCardinality(promptIds.length, models.length, reps);
  const plan: RouterPlanItemSeed[] = [];
  if (count === 0) return plan;
  for (const promptId of promptIds) {
    for (const modelId of models) {
      for (let rep = 0; rep < reps; rep += 1) {
        plan.push({
          prompt_id: promptId,
          model_id: modelId,
          rep,
          shuffle_seed: deriveRouterShuffleSeed(promptId, modelId, rep, baseSeed),
        });
      }
    }
  }
  return plan;
}

/** Full content identity for one structured plan item. */
export function makeRouterPlanItem(seed: RouterPlanItemSeed): RouterPlanItem {
  validatePlanItemSeed(seed, "plan item");
  const identity = {
    model_id: seed.model_id,
    prompt_id: seed.prompt_id,
    rep: seed.rep,
    shuffle_seed: seed.shuffle_seed,
  } satisfies JsonValue;
  return {
    ...identity,
    item_id: domainSeparatedDigest(PLAN_ITEM_DOMAIN, canonicalJsonBytes(identity)),
  };
}

/** Build only from an authenticated clean-source capture and explicit run policy. */
export function buildRouterRunManifest(input: RouterManifestBuildInput): BuiltRouterRunManifest {
  // Authenticity is checked before any caller-controlled field can influence a
  // durable identity. A structurally identical object is not construction
  // authority.
  assertVerifiedExactNamedInputCapture(input.capture);
  const captured = requireRouterCaptures(input.capture);
  const catalog = parseSkillCatalog(captured.skill_catalog.bytes);
  const promptIds = parseRouterFixture(captured.fixture.bytes, new Set(catalog.skillNames));
  const inventoryMetadata = parseInventoryMetadata(captured.inventory.bytes);
  const packageMetadata = parsePackageLock(captured.package_lock.bytes);
  validatePromptTemplate(captured.prompt_template.bytes);

  const orderedPlan = buildRouterPlanSeeds(promptIds, input.models, input.reps, input.seed);
  const items = orderedPlan.map((item) => makeRouterPlanItem(item));
  const manifest: RouterRunManifest = {
    schema: ROUTER_RUN_MANIFEST_SCHEMA,
    source: {
      git_object_format: input.capture.repository.objectFormat,
      proposal_commit_oid: input.capture.repository.commit,
      proposal_tree_oid: input.capture.repository.tree,
      worktree_clean: true,
      inventory_source_tree_digest: inventoryMetadata.sourceTreeDigest,
    },
    inputs: {
      fixture: exactCapturedInput(captured.fixture, "record_count", promptIds.length),
      inventory: exactCapturedInput(
        captured.inventory,
        "source_count",
        inventoryMetadata.sourceCount,
      ),
      prompt_template: exactCapturedInput(captured.prompt_template, "template_count", 1),
      skill_catalog: {
        ...exactCapturedInput(
          captured.skill_catalog,
          "skill_count",
          catalog.skillNames.length,
        ),
        skill_ids: [...catalog.skillNames],
      },
      package_lock: exactCapturedInput(
        captured.package_lock,
        "package_count",
        packageMetadata.packageCount,
      ),
    },
    runtime: {
      node_version: process.version,
      cursor_sdk_version: packageMetadata.cursorSdkVersion,
      platform: process.platform,
      arch: process.arch,
      tools: [],
      setting_sources: [],
      sdk_retries: false,
    },
    plan: {
      prompt_ids: promptIds,
      models: [...input.models],
      reps: input.reps,
      seed: input.seed,
      max_format_attempts: input.maxFormatAttempts,
      item_count: items.length,
      items,
      items_digest: planDigest(items),
    },
    cost: {
      currency: "USD",
      estimated_micro_usd_per_sdk_attempt: input.estimatedMicroUsdPerSdkAttempt,
      forecast_sdk_invocations: checkedProduct(
        items.length,
        input.maxFormatAttempts,
        "forecast SDK invocations",
      ),
      max_sdk_invocations: input.maxSdkInvocations,
      forecast_micro_usd: checkedProduct(
        items.length,
        input.maxFormatAttempts,
        input.estimatedMicroUsdPerSdkAttempt,
        "forecast micro-USD",
      ),
      cap_micro_usd: input.capMicroUsd,
    },
  };
  const validated = validateRouterRunManifest(manifest as unknown as JsonValue);
  const canonicalBytes = canonicalFileBytes(validated as unknown as JsonValue);
  requireManifestSize(canonicalBytes);
  return Object.freeze({
    manifest: validated,
    canonicalBytes,
    digest: domainSeparatedDigest(MANIFEST_DOMAIN, canonicalBytes),
  });
}

export function parseRouterRunManifestFile(source: string | Uint8Array): BuiltRouterRunManifest {
  requireManifestSize(typeof source === "string" ? Buffer.from(source, "utf8") : source);
  const value = parseCanonicalFile(source);
  const manifest = validateRouterRunManifest(value);
  const canonicalBytes = canonicalFileBytes(manifest as unknown as JsonValue);
  requireManifestSize(canonicalBytes);
  return Object.freeze({
    manifest,
    canonicalBytes,
    digest: domainSeparatedDigest(MANIFEST_DOMAIN, canonicalBytes),
  });
}

export function routerRunManifestDigest(manifest: RouterRunManifest): Sha256Digest {
  const validated = validateRouterRunManifest(manifest as unknown as JsonValue);
  return domainSeparatedDigest(
    MANIFEST_DOMAIN,
    canonicalFileBytes(validated as unknown as JsonValue),
  );
}

/** Exact closed-field runtime validation with all derived values recomputed. */
export function validateRouterRunManifest(value: JsonValue): RouterRunManifest {
  const manifest = expectClosedObject(
    value,
    ["schema", "source", "inputs", "runtime", "plan", "cost"],
    "manifest",
  );
  expectLiteral(manifest.schema, ROUTER_RUN_MANIFEST_SCHEMA, "manifest.schema");

  const source = expectClosedObject(
    manifest.source,
    [
      "git_object_format",
      "proposal_commit_oid",
      "proposal_tree_oid",
      "worktree_clean",
      "inventory_source_tree_digest",
    ],
    "source",
  );
  if (source.git_object_format !== "sha1" && source.git_object_format !== "sha256") {
    invalid("source.git_object_format must be sha1 or sha256");
  }
  const oidLength = source.git_object_format === "sha1" ? 40 : 64;
  expectHexOid(source.proposal_commit_oid, oidLength, "source.proposal_commit_oid");
  expectHexOid(source.proposal_tree_oid, oidLength, "source.proposal_tree_oid");
  if (source.worktree_clean !== true) {
    throw new RouterManifestError("SOURCE_NOT_CLEAN", "manifest source must be observed clean");
  }
  expectDigest(source.inventory_source_tree_digest, "source.inventory_source_tree_digest");

  const inputs = expectClosedObject(
    manifest.inputs,
    ["fixture", "inventory", "prompt_template", "skill_catalog", "package_lock"],
    "inputs",
  );
  const fixture = validateExactInput(inputs.fixture, "record_count", "inputs.fixture");
  const inventory = validateExactInput(inputs.inventory, "source_count", "inputs.inventory");
  const template = validateExactInput(
    inputs.prompt_template,
    "template_count",
    "inputs.prompt_template",
  );
  const catalog = validateSkillCatalogInput(inputs.skill_catalog);
  const packageLock = validateExactInput(
    inputs.package_lock,
    "package_count",
    "inputs.package_lock",
  );
  if (template.template_count !== 1) {
    invalid("inputs.prompt_template.template_count must equal one");
  }

  const runtime = expectClosedObject(
    manifest.runtime,
    [
      "node_version",
      "cursor_sdk_version",
      "platform",
      "arch",
      "tools",
      "setting_sources",
      "sdk_retries",
    ],
    "runtime",
  );
  for (const [label, candidate] of [
    ["runtime.node_version", runtime.node_version],
    ["runtime.cursor_sdk_version", runtime.cursor_sdk_version],
    ["runtime.platform", runtime.platform],
    ["runtime.arch", runtime.arch],
  ] as const) {
    if (
      typeof candidate !== "string" ||
      candidate.length > MAX_RUNTIME_TOKEN_LENGTH ||
      !RUNTIME_TOKEN_PATTERN.test(candidate)
    ) {
      invalid(`${label} must be a non-empty portable token`);
    }
  }
  expectEmptyArray(runtime.tools, "runtime.tools");
  expectEmptyArray(runtime.setting_sources, "runtime.setting_sources");
  if (runtime.sdk_retries !== false) {
    invalid("runtime.sdk_retries must be false");
  }

  const plan = expectClosedObject(
    manifest.plan,
    [
      "prompt_ids",
      "models",
      "reps",
      "seed",
      "max_format_attempts",
      "item_count",
      "items",
      "items_digest",
    ],
    "plan",
  );
  const promptIds = expectStringArray(plan.prompt_ids, "plan.prompt_ids");
  const models = expectStringArray(plan.models, "plan.models");
  validateDistinctIds(promptIds, "plan.prompt_ids");
  validateDistinctIds(models, "plan.models");
  expectPositiveInteger(plan.reps, "plan.reps");
  expectSafeInteger(plan.seed, "plan.seed");
  expectPositiveInteger(plan.max_format_attempts, "plan.max_format_attempts");
  if ((plan.max_format_attempts as number) > MAX_ROUTER_FORMAT_ATTEMPTS) {
    invalid(`plan.max_format_attempts cannot exceed ${MAX_ROUTER_FORMAT_ATTEMPTS}`);
  }
  expectNonNegativeInteger(plan.item_count, "plan.item_count");
  if (!Array.isArray(plan.items)) {
    invalid("plan.items must be an array");
  }
  expectDigest(plan.items_digest, "plan.items_digest");

  if (fixture.record_count !== promptIds.length) {
    throw new RouterManifestError(
      "PLAN_CARDINALITY_MISMATCH",
      "fixture record count does not equal the prompt ID count",
    );
  }
  const expectedCount = checkedCardinality(promptIds.length, models.length, plan.reps as number);
  if (plan.item_count !== expectedCount || plan.items.length !== expectedCount) {
    throw new RouterManifestError(
      "PLAN_CARDINALITY_MISMATCH",
      "plan count does not equal the complete prompt/model/replication cross product",
    );
  }

  const validatedItems: RouterPlanItem[] = [];
  const itemIds = new Set<string>();
  let itemIndex = 0;
  for (const promptId of promptIds) {
    for (const modelId of models) {
      for (let rep = 0; rep < (plan.reps as number); rep += 1) {
        const item = validatePlanItem(plan.items[itemIndex] as JsonValue, itemIndex);
        const expectedSeed = deriveRouterShuffleSeed(promptId, modelId, rep, plan.seed as number);
        if (
          item.prompt_id !== promptId ||
          item.model_id !== modelId ||
          item.rep !== rep ||
          item.shuffle_seed !== expectedSeed
        ) {
          throw new RouterManifestError(
            "PLAN_CARDINALITY_MISMATCH",
            `plan item ${itemIndex} is not in the canonical full-plan order`,
          );
        }
        const expectedItem = makeRouterPlanItem(item);
        if (item.item_id !== expectedItem.item_id) {
          throw new RouterManifestError(
            "PLAN_ITEM_ID_MISMATCH",
            `plan item ${itemIndex} has an invalid content identity`,
          );
        }
        if (itemIds.has(item.item_id)) {
          throw new RouterManifestError(
            "PLAN_ITEM_ID_MISMATCH",
            "plan contains a duplicate item identity",
          );
        }
        itemIds.add(item.item_id);
        validatedItems.push(item);
        itemIndex += 1;
      }
    }
  }
  const expectedPlanDigest = planDigest(validatedItems);
  if (plan.items_digest !== expectedPlanDigest) {
    throw new RouterManifestError(
      "PLAN_DIGEST_MISMATCH",
      "plan digest does not match the ordered plan bytes",
    );
  }

  const cost = expectClosedObject(
    manifest.cost,
    [
      "currency",
      "estimated_micro_usd_per_sdk_attempt",
      "forecast_sdk_invocations",
      "max_sdk_invocations",
      "forecast_micro_usd",
      "cap_micro_usd",
    ],
    "cost",
  );
  expectLiteral(cost.currency, "USD", "cost.currency");
  expectPositiveInteger(
    cost.estimated_micro_usd_per_sdk_attempt,
    "cost.estimated_micro_usd_per_sdk_attempt",
  );
  expectNonNegativeInteger(cost.forecast_sdk_invocations, "cost.forecast_sdk_invocations");
  expectPositiveInteger(cost.max_sdk_invocations, "cost.max_sdk_invocations");
  expectNonNegativeInteger(cost.forecast_micro_usd, "cost.forecast_micro_usd");
  expectPositiveInteger(cost.cap_micro_usd, "cost.cap_micro_usd");
  const forecastInvocations = checkedProduct(
    expectedCount,
    plan.max_format_attempts as number,
    "forecast SDK invocations",
  );
  const forecastMicroUsd = checkedProduct(
    forecastInvocations,
    cost.estimated_micro_usd_per_sdk_attempt as number,
    "forecast micro-USD",
  );
  if (
    cost.forecast_sdk_invocations !== forecastInvocations ||
    cost.forecast_micro_usd !== forecastMicroUsd
  ) {
    throw new RouterManifestError(
      "FORECAST_MISMATCH",
      "stored forecast does not match the plan and integer cost model",
    );
  }
  if (
    forecastInvocations > (cost.max_sdk_invocations as number) ||
    forecastMicroUsd > (cost.cap_micro_usd as number)
  ) {
    throw new RouterManifestError(
      "BUDGET_EXCEEDED",
      "worst-case plan exceeds an invocation or micro-USD cap",
    );
  }

  // Construct a fresh object so validation never returns an input prototype or
  // an optional field smuggled through a type assertion.
  return deepFreezeManifest({
    schema: ROUTER_RUN_MANIFEST_SCHEMA,
    source: {
      git_object_format: source.git_object_format,
      proposal_commit_oid: source.proposal_commit_oid as string,
      proposal_tree_oid: source.proposal_tree_oid as string,
      worktree_clean: true,
      inventory_source_tree_digest: source.inventory_source_tree_digest as Sha256Digest,
    },
    inputs: {
      fixture,
      inventory,
      prompt_template: template,
      skill_catalog: catalog,
      package_lock: packageLock,
    },
    runtime: {
      node_version: runtime.node_version as string,
      cursor_sdk_version: runtime.cursor_sdk_version as string,
      platform: runtime.platform as string,
      arch: runtime.arch as string,
      tools: [],
      setting_sources: [],
      sdk_retries: false,
    },
    plan: {
      prompt_ids: promptIds,
      models,
      reps: plan.reps as number,
      seed: plan.seed as number,
      max_format_attempts: plan.max_format_attempts as number,
      item_count: expectedCount,
      items: validatedItems,
      items_digest: expectedPlanDigest,
    },
    cost: {
      currency: "USD",
      estimated_micro_usd_per_sdk_attempt:
        cost.estimated_micro_usd_per_sdk_attempt as number,
      forecast_sdk_invocations: forecastInvocations,
      max_sdk_invocations: cost.max_sdk_invocations as number,
      forecast_micro_usd: forecastMicroUsd,
      cap_micro_usd: cost.cap_micro_usd as number,
    },
  });
}

function deepFreezeManifest(manifest: RouterRunManifest): RouterRunManifest {
  const visit = (value: unknown): void => {
    if (value === null || typeof value !== "object" || Object.isFrozen(value)) return;
    if (Array.isArray(value)) {
      for (const entry of value) visit(entry);
    } else {
      for (const entry of Object.values(value as Record<string, unknown>)) visit(entry);
    }
    Object.freeze(value);
  };
  visit(manifest);
  return manifest;
}

interface RequiredRouterCaptures {
  readonly fixture: StableFileCapture;
  readonly inventory: StableFileCapture;
  readonly package_lock: StableFileCapture;
  readonly prompt_template: StableFileCapture;
  readonly skill_catalog: StableFileCapture;
}

function requireRouterCaptures(capture: ExactNamedInputCapture): RequiredRouterCaptures {
  const actualNames = Object.keys(capture.inputs).sort();
  if (
    actualNames.length !== REQUIRED_CAPTURE_NAMES.length ||
    actualNames.some((name, index) => name !== REQUIRED_CAPTURE_NAMES[index])
  ) {
    invalid(`capture must contain exactly ${REQUIRED_CAPTURE_NAMES.join(", ")}`);
  }
  return {
    fixture: capture.inputs.fixture as StableFileCapture,
    inventory: capture.inputs.inventory as StableFileCapture,
    package_lock: capture.inputs.package_lock as StableFileCapture,
    prompt_template: capture.inputs.prompt_template as StableFileCapture,
    skill_catalog: capture.inputs.skill_catalog as StableFileCapture,
  };
}

function exactCapturedInput(
  frozen: StableFileCapture,
  countKey: "record_count",
  count: number,
): RouterRunManifest["inputs"]["fixture"];
function exactCapturedInput(
  frozen: StableFileCapture,
  countKey: "source_count",
  count: number,
): RouterRunManifest["inputs"]["inventory"];
function exactCapturedInput(
  frozen: StableFileCapture,
  countKey: "template_count",
  count: number,
): RouterRunManifest["inputs"]["prompt_template"];
function exactCapturedInput(
  frozen: StableFileCapture,
  countKey: "skill_count",
  count: number,
): Omit<RouterRunManifest["inputs"]["skill_catalog"], "skill_ids">;
function exactCapturedInput(
  frozen: StableFileCapture,
  countKey: "package_count",
  count: number,
): RouterRunManifest["inputs"]["package_lock"];
function exactCapturedInput(
  frozen: StableFileCapture,
  countKey: "record_count" | "source_count" | "template_count" | "skill_count" | "package_count",
  count: number,
): Record<string, JsonValue> {
  const bytes = Buffer.from(frozen.bytes);
  return {
    sha256: sha256Bytes(bytes),
    size_bytes: bytes.length,
    [countKey]: count,
  };
}

function parseInventoryMetadata(bytes: Uint8Array): {
  readonly sourceTreeDigest: Sha256Digest;
  readonly sourceCount: number;
} {
  const document = expectObjectRecord(
    parseStrictJsonBytes(bytes, "inventory"),
    "inventory",
  );
  const schemaVersion = expectNonEmptyText(document.schema_version, "inventory.schema_version");
  if (!Array.isArray(document.sources) || document.sources.length === 0) {
    invalid("inventory.sources must be a non-empty array");
  }
  expectDigest(document.source_tree_digest, "inventory.source_tree_digest");
  const computed = sha256Bytes(
    canonicalJsonBytes({
      schema_version: schemaVersion,
      sources: document.sources,
    }),
  );
  if (document.source_tree_digest !== computed) {
    invalid("inventory.source_tree_digest does not match its canonical source records");
  }
  return {
    sourceTreeDigest: computed,
    sourceCount: document.sources.length,
  };
}

function parseSkillCatalog(bytes: Uint8Array): { readonly skillNames: readonly string[] } {
  const value = parseStrictJsonBytes(bytes, "skill catalog");
  if (!Array.isArray(value) || value.length === 0) {
    invalid("skill catalog must be a non-empty JSON array");
  }
  const skillNames: string[] = [];
  const seen = new Set<string>();
  for (const [index, entry] of value.entries()) {
    const record = expectClosedObject(
      entry,
      ["name", "description"],
      `skill catalog entry ${index + 1}`,
    );
    const name = expectPortableId(record.name, `skill catalog entry ${index + 1}.name`);
    expectNonEmptyText(record.description, `skill catalog entry ${index + 1}.description`);
    if (seen.has(name)) {
      invalid(`skill catalog contains duplicate name ${name}`);
    }
    seen.add(name);
    skillNames.push(name);
  }
  return { skillNames };
}

function parseRouterFixture(bytes: Uint8Array, skillNames: ReadonlySet<string>): string[] {
  const text = decodeUtf8(bytes, "fixture");
  const lines = text.split("\n");
  if (lines.at(-1) === "") lines.pop();
  if (lines.length === 0) {
    invalid("fixture must contain at least one JSONL record");
  }
  const promptIds: string[] = [];
  const seen = new Set<string>();
  for (const [index, line] of lines.entries()) {
    if (!line || !line.trim()) {
      invalid(`fixture line ${index + 1} must contain exactly one JSON object`);
    }
    const record = expectClosedObjectWithOptional(
      parseJsonStrict(line),
      ["prompt_id", "prompt", "expected_primary_skill"],
      ["acceptable_secondary_skills", "rejected_skills", "reason"],
      `fixture record ${index + 1}`,
    );
    const promptId = expectPortableId(record.prompt_id, `fixture record ${index + 1}.prompt_id`);
    expectNonEmptyText(record.prompt, `fixture record ${index + 1}.prompt`);
    const expected = expectPortableId(
      record.expected_primary_skill,
      `fixture record ${index + 1}.expected_primary_skill`,
    );
    const acceptable = expectOptionalPortableIdArray(
      record.acceptable_secondary_skills,
      `fixture record ${index + 1}.acceptable_secondary_skills`,
    );
    const rejected = expectOptionalPortableIdArray(
      record.rejected_skills,
      `fixture record ${index + 1}.rejected_skills`,
    );
    if (Object.hasOwn(record, "reason")) {
      expectNonEmptyText(record.reason, `fixture record ${index + 1}.reason`);
    }
    for (const skillName of [expected, ...acceptable, ...rejected]) {
      if (!skillNames.has(skillName)) {
        invalid(`fixture record ${promptId} references unknown skill ${skillName}`);
      }
    }
    const acceptableSet = new Set(acceptable);
    const rejectedSet = new Set(rejected);
    if (
      rejectedSet.has(expected) ||
      [...acceptableSet].some((skillName) => rejectedSet.has(skillName))
    ) {
      invalid(`fixture record ${promptId} has overlapping accepted and rejected skills`);
    }
    if (seen.has(promptId)) {
      invalid(`fixture contains duplicate prompt_id ${promptId}`);
    }
    seen.add(promptId);
    promptIds.push(promptId);
  }
  return promptIds;
}

function validatePromptTemplate(bytes: Uint8Array): void {
  if (!decodeUtf8(bytes, "prompt template").trim()) {
    invalid("prompt template must be non-empty UTF-8 text");
  }
}

function parsePackageLock(
  bytes: Uint8Array,
): { readonly packageCount: number; readonly cursorSdkVersion: string } {
  const document = expectObjectRecord(
    parseStrictJsonBytes(bytes, "package lock"),
    "package lock",
  );
  if (document.lockfileVersion !== 3) {
    invalid("package lock must use lockfileVersion 3");
  }
  const packages = expectObjectRecord(document.packages, "package lock.packages");
  const packageCount = Object.keys(packages).length;
  if (packageCount === 0) {
    invalid("package lock.packages must not be empty");
  }
  const rootPackage = expectObjectRecord(packages[""], "package lock root package");
  const dependencies = expectObjectRecord(
    rootPackage.dependencies,
    "package lock root dependencies",
  );
  const sdkPackage = expectObjectRecord(
    packages["node_modules/@cursor/sdk"],
    "package lock @cursor/sdk package",
  );
  const declaredVersion = dependencies["@cursor/sdk"];
  const installedVersion = sdkPackage.version;
  if (
    typeof declaredVersion !== "string" ||
    typeof installedVersion !== "string" ||
    declaredVersion !== installedVersion ||
    !RUNTIME_TOKEN_PATTERN.test(installedVersion)
  ) {
    invalid("package lock must pin and install one exact @cursor/sdk version");
  }
  return { packageCount, cursorSdkVersion: installedVersion };
}

function parseStrictJsonBytes(bytes: Uint8Array, label: string): JsonValue {
  return parseJsonStrict(decodeUtf8(bytes, label));
}

function decodeUtf8(bytes: Uint8Array, label: string): string {
  try {
    return new TextDecoder("utf-8", { fatal: true, ignoreBOM: true }).decode(bytes);
  } catch {
    throw new DurableJsonError("INVALID_JSON", `${label} is not valid UTF-8`);
  }
}

function validateExactInput(
  value: JsonValue | undefined,
  countKey: "record_count",
  label: string,
): RouterRunManifest["inputs"]["fixture"];
function validateExactInput(
  value: JsonValue | undefined,
  countKey: "source_count",
  label: string,
): RouterRunManifest["inputs"]["inventory"];
function validateExactInput(
  value: JsonValue | undefined,
  countKey: "template_count",
  label: string,
): RouterRunManifest["inputs"]["prompt_template"];
function validateExactInput(
  value: JsonValue | undefined,
  countKey: "skill_count",
  label: string,
): Omit<RouterRunManifest["inputs"]["skill_catalog"], "skill_ids">;
function validateExactInput(
  value: JsonValue | undefined,
  countKey: "package_count",
  label: string,
): RouterRunManifest["inputs"]["package_lock"];
function validateExactInput(
  value: JsonValue | undefined,
  countKey: "record_count" | "source_count" | "template_count" | "skill_count" | "package_count",
  label: string,
): Record<string, JsonValue> {
  const input = expectClosedObject(value, ["sha256", "size_bytes", countKey], label);
  expectDigest(input.sha256, `${label}.sha256`);
  expectPositiveInteger(input.size_bytes, `${label}.size_bytes`);
  expectPositiveInteger(input[countKey], `${label}.${countKey}`);
  return {
    sha256: input.sha256 as Sha256Digest,
    size_bytes: input.size_bytes as number,
    [countKey]: input[countKey] as number,
  };
}

function validateSkillCatalogInput(
  value: JsonValue | undefined,
): RouterRunManifest["inputs"]["skill_catalog"] {
  const input = expectClosedObject(
    value,
    ["sha256", "size_bytes", "skill_count", "skill_ids"],
    "inputs.skill_catalog",
  );
  expectDigest(input.sha256, "inputs.skill_catalog.sha256");
  expectPositiveInteger(input.size_bytes, "inputs.skill_catalog.size_bytes");
  expectPositiveInteger(input.skill_count, "inputs.skill_catalog.skill_count");
  const skillIds = expectStringArray(input.skill_ids, "inputs.skill_catalog.skill_ids");
  validateDistinctIds(skillIds, "inputs.skill_catalog.skill_ids");
  if (input.skill_count !== skillIds.length) {
    invalid("inputs.skill_catalog.skill_count must equal the skill ID count");
  }
  return {
    sha256: input.sha256 as Sha256Digest,
    size_bytes: input.size_bytes as number,
    skill_count: input.skill_count as number,
    skill_ids: skillIds,
  };
}

function validatePlanItem(value: JsonValue | undefined, index: number): RouterPlanItem {
  const item = expectClosedObject(
    value,
    ["item_id", "prompt_id", "model_id", "rep", "shuffle_seed"],
    `plan.items[${index}]`,
  );
  expectDigest(item.item_id, `plan.items[${index}].item_id`);
  const seed: RouterPlanItemSeed = {
    prompt_id: expectPortableId(item.prompt_id, `plan.items[${index}].prompt_id`),
    model_id: expectPortableId(item.model_id, `plan.items[${index}].model_id`),
    rep: expectNonNegativeInteger(item.rep, `plan.items[${index}].rep`),
    shuffle_seed: expectUint32(item.shuffle_seed, `plan.items[${index}].shuffle_seed`),
  };
  return { ...seed, item_id: item.item_id as Sha256Digest };
}

function validatePlanItemSeed(seed: RouterPlanItemSeed, label: string): void {
  expectPortableId(seed.prompt_id, `${label}.prompt_id`);
  expectPortableId(seed.model_id, `${label}.model_id`);
  expectNonNegativeInteger(seed.rep, `${label}.rep`);
  expectUint32(seed.shuffle_seed, `${label}.shuffle_seed`);
}

function planDigest(items: readonly RouterPlanItem[]): Sha256Digest {
  return domainSeparatedDigest(
    PLAN_DOMAIN,
    canonicalJsonBytes(items as unknown as JsonValue),
  );
}

function checkedCardinality(promptCount: number, modelCount: number, reps: number): number {
  const count = checkedProduct(promptCount, modelCount, reps, "plan cardinality");
  if (count > MAX_ROUTER_PLAN_ITEMS) {
    throw new RouterManifestError(
      "PLAN_CARDINALITY_MISMATCH",
      `plan cardinality exceeds ${MAX_ROUTER_PLAN_ITEMS}`,
    );
  }
  return count;
}

function checkedProduct(...valuesAndLabel: [...number[], string]): number {
  const label = valuesAndLabel[valuesAndLabel.length - 1] as string;
  const values = valuesAndLabel.slice(0, -1) as number[];
  let result = 1n;
  for (const value of values) {
    if (!Number.isSafeInteger(value) || value < 0) {
      invalid(`${label} contains an invalid integer`);
    }
    result *= BigInt(value);
    if (result > BigInt(Number.MAX_SAFE_INTEGER)) {
      invalid(`${label} exceeds the safe integer range`);
    }
  }
  return Number(result);
}

function expectClosedObject(
  value: JsonValue | undefined,
  keys: readonly string[],
  label: string,
): Record<string, JsonValue> {
  const record = expectObjectRecord(value, label);
  const required = new Set(keys);
  for (const key of Object.keys(record)) {
    if (!required.has(key)) {
      throw new RouterManifestError("UNKNOWN_FIELD", `${label} contains unknown field ${key}`);
    }
  }
  for (const key of keys) {
    if (!Object.hasOwn(record, key)) {
      throw new RouterManifestError("MISSING_FIELD", `${label} is missing field ${key}`);
    }
  }
  return record;
}

function expectClosedObjectWithOptional(
  value: JsonValue | undefined,
  requiredKeys: readonly string[],
  optionalKeys: readonly string[],
  label: string,
): Record<string, JsonValue> {
  const record = expectObjectRecord(value, label);
  const allowed = new Set([...requiredKeys, ...optionalKeys]);
  for (const key of Object.keys(record)) {
    if (!allowed.has(key)) {
      throw new RouterManifestError("UNKNOWN_FIELD", `${label} contains unknown field ${key}`);
    }
  }
  for (const key of requiredKeys) {
    if (!Object.hasOwn(record, key)) {
      throw new RouterManifestError("MISSING_FIELD", `${label} is missing field ${key}`);
    }
  }
  return record;
}

function expectObjectRecord(
  value: JsonValue | undefined,
  label: string,
): Record<string, JsonValue> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) {
    invalid(`${label} must be an object`);
  }
  return value as Record<string, JsonValue>;
}

function expectNonEmptyText(value: JsonValue | undefined, label: string): string {
  if (typeof value !== "string" || !value.trim()) {
    invalid(`${label} must be a non-empty string`);
  }
  return value;
}

function expectOptionalPortableIdArray(
  value: JsonValue | undefined,
  label: string,
): string[] {
  if (value === undefined) return [];
  if (!Array.isArray(value)) {
    invalid(`${label} must be an array when present`);
  }
  const result = value.map((entry, index) => expectPortableId(entry, `${label}[${index}]`));
  if (new Set(result).size !== result.length) {
    invalid(`${label} must contain unique values`);
  }
  return result;
}

function expectStringArray(value: JsonValue | undefined, label: string): string[] {
  if (!Array.isArray(value)) {
    invalid(`${label} must be an array`);
  }
  return value.map((entry, index) => expectPortableId(entry, `${label}[${index}]`));
}

function validateDistinctIds(values: readonly string[], label: string): void {
  if (values.length === 0) {
    invalid(`${label} must not be empty`);
  }
  const seen = new Set<string>();
  for (const [index, value] of values.entries()) {
    expectPortableId(value, `${label}[${index}]`);
    if (seen.has(value)) {
      invalid(`${label} must contain unique values`);
    }
    seen.add(value);
  }
}

function expectPortableId(value: unknown, label: string): string {
  if (
    typeof value !== "string" ||
    value.length > MAX_ROUTER_PORTABLE_ID_LENGTH ||
    !PORTABLE_ID_PATTERN.test(value)
  ) {
    invalid(`${label} must be a non-empty portable identifier`);
  }
  return value;
}

function expectDigest(value: unknown, label: string): asserts value is Sha256Digest {
  if (typeof value !== "string" || !SHA256_PATTERN.test(value)) {
    throw new RouterManifestError(
      "INVALID_DIGEST",
      `${label} must be a full lowercase SHA-256 digest`,
    );
  }
}

function expectHexOid(value: unknown, length: number, label: string): void {
  if (typeof value !== "string" || !new RegExp(`^[0-9a-f]{${length}}$`).test(value)) {
    invalid(`${label} must be a full lowercase Git object ID`);
  }
}

function expectLiteral(value: unknown, expected: string, label: string): void {
  if (value !== expected) {
    invalid(`${label} must equal ${expected}`);
  }
}

function expectEmptyArray(value: unknown, label: string): void {
  if (!Array.isArray(value) || value.length !== 0) {
    invalid(`${label} must be an empty array`);
  }
}

function expectSafeInteger(value: unknown, label: string): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || Object.is(value, -0)) {
    invalid(`${label} must be a non-negative-zero safe integer`);
  }
  return value;
}

function expectNonNegativeInteger(value: unknown, label: string): number {
  const integer = expectSafeInteger(value, label);
  if (integer < 0) {
    invalid(`${label} must be non-negative`);
  }
  return integer;
}

function expectPositiveInteger(value: unknown, label: string): number {
  const integer = expectSafeInteger(value, label);
  if (integer <= 0) {
    invalid(`${label} must be positive`);
  }
  return integer;
}

function expectUint32(value: unknown, label: string): number {
  const integer = expectNonNegativeInteger(value, label);
  if (integer > 0xffff_ffff) {
    invalid(`${label} must fit an unsigned 32-bit integer`);
  }
  return integer;
}

function invalid(message: string): never {
  throw new RouterManifestError("INVALID_FIELD", message);
}

function requireManifestSize(bytes: Uint8Array): void {
  if (bytes.byteLength > MAX_ROUTER_MANIFEST_BYTES) {
    invalid(`manifest exceeds ${MAX_ROUTER_MANIFEST_BYTES} bytes`);
  }
}
