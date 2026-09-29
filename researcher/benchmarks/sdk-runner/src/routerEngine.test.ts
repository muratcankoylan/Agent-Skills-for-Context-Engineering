import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import { mkdtempSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { mkdir, mkdtemp, rm } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join, sep } from "node:path";
import { test, type TestContext } from "node:test";

import {
  NodeDurableFileSystem,
  type DurableDirectoryEntry,
  type DurableFileSystem,
  type DurablePathStat,
} from "./durableFs.ts";
import { canonicalJsonBytes, sha256Bytes, type JsonValue } from "./durableJson.ts";
import {
  RouterReconciliationRequiredError,
  createRouterManifestSourceGuard,
  runRouterEngine,
  type RouterEngineOptions,
  type RouterEngineStore,
  type RouterExecutor,
  type RouterOutputValidator,
} from "./routerEngine.ts";
import {
  buildRouterRunManifest,
  type BuiltRouterRunManifest,
} from "./routerManifest.ts";
import {
  RouterRunStore,
  RouterRunStoreError,
} from "./routerRunStore.ts";
import { captureExactNamedInputs } from "./sourceFreeze.ts";

const NOW = "2026-08-15T12:00:00Z";
const UNIT_COST_MICRO_USD = 12_000;
const clock = { now: (): string => NOW };
const sourceGuard = { revalidate: (): void => undefined };
const GIT_ENV = {
  ...process.env,
  GIT_AUTHOR_DATE: "2026-01-01T00:00:00Z",
  GIT_COMMITTER_DATE: "2026-01-01T00:00:00Z",
};

async function resultsWorkspace(context: TestContext): Promise<string> {
  const root = await mkdtemp(join(tmpdir(), "router-engine-"));
  context.after(async () => rm(root, { recursive: true, force: true }));
  const resultsRoot = join(root, "results");
  await mkdir(resultsRoot, { mode: 0o700 });
  return resultsRoot;
}

function builtManifest(promptIds: readonly string[]): BuiltRouterRunManifest {
  const models = ["model-a"];
  const reps = 1;
  const seed = 17;
  const maximumAttempts = 2;
  const maximumInvocations = promptIds.length * models.length * reps * maximumAttempts;
  const captureRoot = mkdtempSync(join(tmpdir(), "router-engine-capture-"));
  try {
    const paths = writeManifestInputs(captureRoot, promptIds);
    git(captureRoot, "init", "--quiet");
    git(captureRoot, "config", "user.name", "Router Engine Test");
    git(captureRoot, "config", "user.email", "router-engine@example.invalid");
    git(captureRoot, "add", ".");
    git(captureRoot, "commit", "--quiet", "-m", "engine manifest inputs");
    const capture = captureExactNamedInputs(captureRoot, paths);
    return buildRouterRunManifest({
      capture,
      models,
      reps,
      seed,
      maxFormatAttempts: maximumAttempts,
      estimatedMicroUsdPerSdkAttempt: UNIT_COST_MICRO_USD,
      maxSdkInvocations: maximumInvocations,
      capMicroUsd: maximumInvocations * UNIT_COST_MICRO_USD,
    });
  } finally {
    rmSync(captureRoot, { recursive: true, force: true });
  }
}

function sourceGuardWorkspace(
  context: TestContext,
  promptIds: readonly string[],
): {
  readonly root: string;
  readonly paths: Readonly<Record<string, string>>;
  readonly manifest: BuiltRouterRunManifest;
} {
  const root = mkdtempSync(join(tmpdir(), "router-engine-source-"));
  context.after(() => rmSync(root, { recursive: true, force: true }));
  const paths = writeManifestInputs(root, promptIds);
  git(root, "init", "--quiet");
  git(root, "config", "user.name", "Router Engine Test");
  git(root, "config", "user.email", "router-engine@example.invalid");
  git(root, "add", ".");
  git(root, "commit", "--quiet", "-m", "engine source guard inputs");
  const capture = captureExactNamedInputs(root, paths);
  const maximumInvocations = promptIds.length * 2;
  return {
    root,
    paths,
    manifest: buildRouterRunManifest({
      capture,
      models: ["model-a"],
      reps: 1,
      seed: 17,
      maxFormatAttempts: 2,
      estimatedMicroUsdPerSdkAttempt: UNIT_COST_MICRO_USD,
      maxSdkInvocations: maximumInvocations,
      capMicroUsd: maximumInvocations * UNIT_COST_MICRO_USD,
    }),
  };
}

function writeManifestInputs(
  root: string,
  promptIds: readonly string[],
): Readonly<Record<string, string>> {
  const skillCatalog = join(root, "skill-catalog.json");
  const fixture = join(root, "fixture.jsonl");
  const promptTemplate = join(root, "prompt-template.txt");
  const packageLock = join(root, "package-lock.json");
  const inventory = join(root, "inventory.json");
  writeFileSync(skillCatalog, JSON.stringify([
    { name: "skill-a", description: "Routes the deterministic engine fixture" },
  ]));
  writeFileSync(fixture, `${promptIds.map((promptId) => JSON.stringify({
    prompt_id: promptId,
    prompt: `Route ${promptId}`,
    expected_primary_skill: "skill-a",
  })).join("\n")}\n`);
  writeFileSync(promptTemplate, "Route this request: {{USER_PROMPT}}\n");
  writeFileSync(packageLock, JSON.stringify({
    lockfileVersion: 3,
    packages: {
      "": { dependencies: { "@cursor/sdk": "1.0.28" } },
      "node_modules/@cursor/sdk": { version: "1.0.28" },
    },
  }));
  const inventoryCore = {
    schema_version: "1",
    sources: [{ path: "SKILL.md", sha256: sha256Bytes("skill source") }],
  } satisfies JsonValue;
  writeFileSync(inventory, JSON.stringify({
    ...inventoryCore,
    source_tree_digest: sha256Bytes(canonicalJsonBytes(inventoryCore)),
  }));
  return {
    fixture,
    inventory,
    package_lock: packageLock,
    prompt_template: promptTemplate,
    skill_catalog: skillCatalog,
  };
}

function git(root: string, ...arguments_: string[]): void {
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
}

function validOutput(skill = "skill-a"): string {
  return JSON.stringify({
    ranking: [skill],
    confidence: 0.9,
    rationale: `${skill} is the closest match`,
  });
}

const strictOutputValidator: RouterOutputValidator = {
  validate(rawText) {
    let value: unknown;
    try {
      value = JSON.parse(rawText);
    } catch {
      return { valid: false, reason: "unparseable" };
    }
    if (!isRecord(value) || !hasExactKeys(value, [
      "ranking",
      "confidence",
      "rationale",
    ])) {
      return { valid: false, reason: "schema_invalid" };
    }
    const ranking = value.ranking;
    const confidence = value.confidence;
    const rationale = value.rationale;
    if (
      !Array.isArray(ranking) ||
      ranking.length === 0 ||
      ranking.some((entry) => typeof entry !== "string" || entry.length === 0) ||
      new Set(ranking).size !== ranking.length ||
      typeof confidence !== "number" ||
      !Number.isFinite(confidence) ||
      confidence < 0 ||
      confidence > 1 ||
      !Number.isSafeInteger(confidence * 1_000_000) ||
      typeof rationale !== "string" ||
      rationale.length === 0
    ) {
      return { valid: false, reason: "schema_invalid" };
    }
    return {
      valid: true,
      ranking: ranking as string[],
      confidence_millionths: confidence * 1_000_000,
      rationale,
    };
  },
};

test("fake validator matches the exact bound routing prompt example", () => {
  const template = readFileSync(
    new URL("../../router/routing-prompt.md", import.meta.url),
    "utf8",
  );
  const example = template.split("\n").find((line) => line.startsWith('{"ranking"'));
  assert.ok(example, "routing prompt must contain its canonical JSON example");
  const item = builtManifest(["prompt-alignment"]).manifest.plan.items[0]!;
  const result = strictOutputValidator.validate(example, item);
  assert.equal(result.valid, true);
  if (result.valid) assert.equal(result.confidence_millionths, 820_000);
});

function isRecord(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === "object" && !Array.isArray(value);
}

function hasExactKeys(value: Record<string, unknown>, expected: readonly string[]): boolean {
  const actual = Object.keys(value).sort();
  const sortedExpected = [...expected].sort();
  return actual.length === sortedExpected.length &&
    actual.every((key, index) => key === sortedExpected[index]);
}

function engineOptions(
  store: RouterEngineStore,
  ownerId: string,
  executor: RouterExecutor,
  overrides: Partial<Pick<RouterEngineOptions, "sourceGuard" | "outputValidator">> = {},
): RouterEngineOptions {
  return {
    store,
    ownerId,
    clock,
    sourceGuard: overrides.sourceGuard ?? sourceGuard,
    executor,
    outputValidator: overrides.outputValidator ?? strictOutputValidator,
  };
}

test("call matrix is 1/2/2/1 and a completed restart makes zero calls", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const manifest = builtManifest(["one", "two", "three", "four"]);
  const calls = new Map<string, number>();
  const executor: RouterExecutor = {
    async execute({ item, attempt }) {
      calls.set(item.prompt_id, (calls.get(item.prompt_id) ?? 0) + 1);
      if (item.prompt_id === "one") {
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      }
      if (item.prompt_id === "two") {
        return {
          status: "finished",
          raw_text: attempt === 1 ? "not-json" : validOutput(),
          duration_ms: 2,
        };
      }
      if (item.prompt_id === "three") {
        return {
          status: "finished",
          raw_text: attempt === 1 ? "" : '{"ranking":[]}',
          duration_ms: 3,
        };
      }
      return {
        status: "provider_error",
        error_code: "PROVIDER_ERROR",
        error_message: "closed provider failure",
        duration_ms: 4,
      };
    },
  };

  const final = await runRouterEngine(
    engineOptions(new RouterRunStore(resultsRoot, manifest), "owner-matrix", executor),
  );
  assert.deepEqual(
    ["one", "two", "three", "four"].map((id) => calls.get(id)),
    [1, 2, 2, 1],
  );
  assert.deepEqual(final.pending, []);
  assert.deepEqual(final.terminal_pending, []);
  assert.equal(final.completed_item_ids.length, 4);
  assert.equal(final.claimed_invocations, 6);
  assert.equal(final.claimed_cost_microusd, 6 * UNIT_COST_MICRO_USD);

  let resumedCalls = 0;
  const resumed = await runRouterEngine(
    engineOptions(new RouterRunStore(resultsRoot, manifest), "owner-resume", {
      async execute() {
        resumedCalls += 1;
        throw new Error("terminal records must make the executor unreachable");
      },
    }),
  );
  assert.equal(resumedCalls, 0);
  assert.equal(resumed.completed_item_ids.length, 4);
  assert.equal(resumed.claimed_invocations, 6);
});

test("durable claim publication is visible before source guard and executor", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const manifest = builtManifest(["claim-order"]);
  const fileSystem = new ClaimObservingFileSystem(resultsRoot);
  const store = new RouterRunStore(resultsRoot, manifest, fileSystem);
  let guardCalls = 0;
  let executorCalls = 0;

  await runRouterEngine(engineOptions(store, "owner-order", {
    async execute() {
      executorCalls += 1;
      assert.equal(fileSystem.durableClaimWrites, 1);
      assert.equal(guardCalls, 1);
      return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
    },
  }, {
    sourceGuard: {
      revalidate() {
        guardCalls += 1;
        assert.equal(fileSystem.durableClaimWrites, 1);
      },
    },
  }));

  assert.equal(guardCalls, 1);
  assert.equal(executorCalls, 1);
});

test("source revalidation failure makes zero calls and leaves restart-blocking ambiguity", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const manifest = builtManifest(["guard-failure"]);
  let executorCalls = 0;

  await assert.rejects(
    runRouterEngine(engineOptions(new RouterRunStore(resultsRoot, manifest), "owner-guard", {
      async execute() {
        executorCalls += 1;
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      },
    }, {
      sourceGuard: {
        revalidate() {
          throw new Error("frozen source changed");
        },
      },
    })),
    (error: unknown) =>
      error instanceof RouterReconciliationRequiredError &&
      error.stage === "source_revalidation",
  );
  assert.equal(executorCalls, 0);

  await assert.rejects(
    runRouterEngine(engineOptions(new RouterRunStore(resultsRoot, manifest), "owner-guard-restart", {
      async execute() {
        executorCalls += 1;
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      },
    })),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "RECONCILIATION_REQUIRED",
  );
  assert.equal(executorCalls, 0);
});

test("concrete source guard blocks changed bound bytes before executor reachability", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const cleanResultsRoot = await resultsWorkspace(context);
  const source = sourceGuardWorkspace(context, ["guard-bound"]);
  const guard = createRouterManifestSourceGuard({
    repoRoot: source.root,
    inputPaths: source.paths,
    manifest: source.manifest,
  });
  let cleanCalls = 0;
  await runRouterEngine(engineOptions(
    new RouterRunStore(cleanResultsRoot, source.manifest),
    "owner-clean-guard",
    {
      async execute() {
        cleanCalls += 1;
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      },
    },
    { sourceGuard: guard },
  ));
  assert.equal(cleanCalls, 1);
  writeFileSync(source.paths.prompt_template!, "changed after manifest capture\n");
  let executorCalls = 0;
  await assert.rejects(
    runRouterEngine(engineOptions(
      new RouterRunStore(resultsRoot, source.manifest),
      "owner-bound-guard",
      {
        async execute() {
          executorCalls += 1;
          return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
        },
      },
      { sourceGuard: guard },
    )),
    (error: unknown) =>
      error instanceof RouterReconciliationRequiredError &&
      error.stage === "source_revalidation",
  );
  assert.equal(executorCalls, 0);
});

test("concrete source guard rejects a store for a different manifest", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const sourceA = sourceGuardWorkspace(context, ["manifest-a"]);
  const sourceB = sourceGuardWorkspace(context, ["manifest-b"]);
  assert.notEqual(sourceA.manifest.digest, sourceB.manifest.digest);
  const wrongGuard = createRouterManifestSourceGuard({
    repoRoot: sourceB.root,
    inputPaths: sourceB.paths,
    manifest: sourceB.manifest,
  });
  let executorCalls = 0;
  await assert.rejects(
    runRouterEngine(engineOptions(
      new RouterRunStore(resultsRoot, sourceA.manifest),
      "owner-mismatched-guard",
      {
        async execute() {
          executorCalls += 1;
          return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
        },
      },
      { sourceGuard: wrongGuard },
    )),
    (error: unknown) =>
      error instanceof RouterReconciliationRequiredError &&
      error.stage === "source_revalidation",
  );
  assert.equal(executorCalls, 0);
  await assert.rejects(
    runRouterEngine(engineOptions(
      new RouterRunStore(resultsRoot, sourceA.manifest),
      "owner-mismatched-restart",
      {
        async execute() {
          executorCalls += 1;
          return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
        },
      },
      { sourceGuard: wrongGuard },
    )),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "RECONCILIATION_REQUIRED",
  );
  assert.equal(executorCalls, 0);
});

test("executor throw leaves an unmatched claim and restart makes zero calls", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const manifest = builtManifest(["executor-throw"]);
  let calls = 0;

  await assert.rejects(
    runRouterEngine(engineOptions(new RouterRunStore(resultsRoot, manifest), "owner-throw", {
      async execute() {
        calls += 1;
        throw new Error("outcome unknown");
      },
    })),
    (error: unknown) =>
      error instanceof RouterReconciliationRequiredError && error.stage === "executor",
  );
  assert.equal(calls, 1);

  await assert.rejects(
    runRouterEngine(engineOptions(new RouterRunStore(resultsRoot, manifest), "owner-throw-restart", {
      async execute() {
        calls += 1;
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      },
    })),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "RECONCILIATION_REQUIRED",
  );
  assert.equal(calls, 1);
});

test("provider, cancellation, and unavailable outcomes are terminal without retry", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const manifest = builtManifest(["provider", "cancelled", "unavailable"]);
  const calls = new Map<string, number>();
  const final = await runRouterEngine(engineOptions(
    new RouterRunStore(resultsRoot, manifest),
    "owner-operational",
    {
      async execute({ item }) {
        calls.set(item.prompt_id, (calls.get(item.prompt_id) ?? 0) + 1);
        if (item.prompt_id === "provider") {
          return {
            status: "provider_error",
            error_code: "PROVIDER_ERROR",
            error_message: "provider failed",
            duration_ms: 1,
          };
        }
        if (item.prompt_id === "cancelled") {
          return { status: "cancelled", duration_ms: 1 };
        }
        return {
          status: "model_unavailable",
          error_code: "MODEL_UNAVAILABLE",
          error_message: "model is unavailable",
          duration_ms: 1,
        };
      },
    },
  ));

  assert.deepEqual(
    ["provider", "cancelled", "unavailable"].map((id) => calls.get(id)),
    [1, 1, 1],
  );
  assert.equal(final.claimed_invocations, 3);
  assert.equal(final.completed_item_ids.length, 3);
});

test("a settled first format failure resumes exactly at attempt two", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const manifest = builtManifest(["resume-format"]);
  const store = new RouterRunStore(resultsRoot, manifest);
  const lease = await store.acquire("owner-prepare", NOW);
  await store.initialize(lease);
  const item = store.manifest.manifest.plan.items[0]!;
  const firstClaim = await store.claim(lease, item.item_id, NOW);
  await store.settle(lease, firstClaim, {
    status: "format_failure",
    finished_at: NOW,
    duration_ms: 1,
    raw_text: "not-json",
    error_code: "FORMAT_UNPARSEABLE",
    error_message: "finished output was not parseable",
  });
  await store.release(lease);

  let calls = 0;
  const final = await runRouterEngine(engineOptions(
    new RouterRunStore(resultsRoot, manifest),
    "owner-format-resume",
    {
      async execute({ attempt }) {
        calls += 1;
        assert.equal(attempt, 2);
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      },
    },
  ));
  assert.equal(calls, 1);
  assert.equal(final.claimed_invocations, 2);
  assert.equal(final.completed_item_ids.length, 1);
});

test("store budget rejection happens before executor reachability", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const manifest = builtManifest(["budget"]);
  const actual = new RouterRunStore(resultsRoot, manifest);
  const budgetRejecting: RouterEngineStore = {
    acquire: actual.acquire.bind(actual),
    initialize: actual.initialize.bind(actual),
    preflight: actual.preflight.bind(actual),
    async claim() {
      throw new RouterRunStoreError("BUDGET_EXHAUSTED", "injected manifest budget exhaustion");
    },
    settle: actual.settle.bind(actual),
    writeTerminal: actual.writeTerminal.bind(actual),
    release: actual.release.bind(actual),
  };
  let calls = 0;

  await assert.rejects(
    runRouterEngine(engineOptions(budgetRejecting, "owner-budget", {
      async execute() {
        calls += 1;
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      },
    })),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "BUDGET_EXHAUSTED",
  );
  assert.equal(calls, 0);
});

test("invalid pending and claim attempts fail closed before executor reachability", async (context) => {
  const manifest = builtManifest(["attempt-boundary"]);
  const invalidPendingRoot = await resultsWorkspace(context);
  const pendingStore = new RouterRunStore(invalidPendingRoot, manifest);
  let pendingClaimCalls = 0;
  let executorCalls = 0;
  const invalidPendingStore: RouterEngineStore = {
    acquire: pendingStore.acquire.bind(pendingStore),
    initialize: pendingStore.initialize.bind(pendingStore),
    async preflight(lease) {
      const state = await pendingStore.preflight(lease);
      return {
        ...state,
        pending: state.pending.map((entry) => ({ ...entry, next_attempt: 3 })),
      };
    },
    async claim(lease, itemId, claimedAt) {
      pendingClaimCalls += 1;
      return pendingStore.claim(lease, itemId, claimedAt);
    },
    settle: pendingStore.settle.bind(pendingStore),
    writeTerminal: pendingStore.writeTerminal.bind(pendingStore),
    release: pendingStore.release.bind(pendingStore),
  };

  await assert.rejects(
    runRouterEngine(engineOptions(invalidPendingStore, "owner-invalid-pending", {
      async execute() {
        executorCalls += 1;
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      },
    })),
    (error: unknown) =>
      error instanceof TypeError && error.message.includes("pending attempt must be an integer"),
  );
  assert.equal(pendingClaimCalls, 0);
  assert.equal(executorCalls, 0);

  const mismatchedClaimRoot = await resultsWorkspace(context);
  const claimStore = new RouterRunStore(mismatchedClaimRoot, manifest);
  const mismatchedClaimStore: RouterEngineStore = {
    acquire: claimStore.acquire.bind(claimStore),
    initialize: claimStore.initialize.bind(claimStore),
    preflight: claimStore.preflight.bind(claimStore),
    async claim(lease, itemId, claimedAt) {
      const claim = await claimStore.claim(lease, itemId, claimedAt);
      return { ...claim, attempt: claim.attempt + 1 };
    },
    settle: claimStore.settle.bind(claimStore),
    writeTerminal: claimStore.writeTerminal.bind(claimStore),
    release: claimStore.release.bind(claimStore),
  };

  await assert.rejects(
    runRouterEngine(engineOptions(mismatchedClaimStore, "owner-mismatched-claim", {
      async execute() {
        executorCalls += 1;
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      },
    })),
    (error: unknown) =>
      error instanceof RouterReconciliationRequiredError && error.stage === "claim_validation",
  );
  assert.equal(executorCalls, 0);
});

test("two coordinators sharing a run can reach the executor only once", async (context) => {
  const resultsRoot = await resultsWorkspace(context);
  const manifest = builtManifest(["coordinator-race"]);
  const firstStore = new RouterRunStore(resultsRoot, manifest);
  const secondStore = new RouterRunStore(resultsRoot, manifest);
  let calls = 0;
  const started = deferred<void>();
  const permitCompletion = deferred<void>();

  const firstRun = runRouterEngine(engineOptions(firstStore, "owner-first", {
    async execute() {
      calls += 1;
      started.resolve();
      await permitCompletion.promise;
      return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
    },
  }));
  await started.promise;

  await assert.rejects(
    runRouterEngine(engineOptions(secondStore, "owner-second", {
      async execute() {
        calls += 1;
        return { status: "finished", raw_text: validOutput(), duration_ms: 1 };
      },
    })),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "RUN_LOCKED",
  );
  permitCompletion.resolve();
  await firstRun;
  assert.equal(calls, 1);
});

function deferred<T>(): {
  readonly promise: Promise<T>;
  readonly resolve: (value: T | PromiseLike<T>) => void;
} {
  let resolve!: (value: T | PromiseLike<T>) => void;
  const promise = new Promise<T>((fulfill) => {
    resolve = fulfill;
  });
  return { promise, resolve };
}

class ClaimObservingFileSystem implements DurableFileSystem {
  readonly delegate: NodeDurableFileSystem;
  durableClaimWrites = 0;

  constructor(root: string) {
    this.delegate = new NodeDurableFileSystem(root);
  }

  ensurePrivateDirectory(path: string): Promise<void> {
    return this.delegate.ensurePrivateDirectory(path);
  }

  listDirectory(path: string): Promise<readonly DurableDirectoryEntry[]> {
    return this.delegate.listDirectory(path);
  }

  statPath(path: string): Promise<DurablePathStat | null> {
    return this.delegate.statPath(path);
  }

  readRegularNoFollow(path: string, maximumBytes: number): Promise<Uint8Array> {
    return this.delegate.readRegularNoFollow(path, maximumBytes);
  }

  async writeExclusiveDurable(path: string, body: Uint8Array): Promise<void> {
    await this.delegate.writeExclusiveDurable(path, body);
    if (path.includes(`${sep}attempt-claims${sep}`)) {
      this.durableClaimWrites += 1;
    }
  }

  removeExactDurable(path: string, expectedBody: Uint8Array): Promise<void> {
    return this.delegate.removeExactDurable(path, expectedBody);
  }
}
