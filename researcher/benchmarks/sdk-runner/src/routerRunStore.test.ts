import assert from "node:assert/strict";
import {
  link,
  mkdtemp,
  mkdir,
  readdir,
  rename,
  rm,
  symlink,
  writeFile,
} from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { afterEach, test } from "node:test";

import {
  canonicalFileBytes,
  canonicalJsonBytes,
  domainSeparatedDigest,
  sha256Bytes,
  type JsonValue,
} from "./durableJson.ts";
import {
  ROUTER_RUN_MANIFEST_SCHEMA,
  buildRouterPlanSeeds,
  makeRouterPlanItem,
  parseRouterRunManifestFile,
} from "./routerManifest.ts";
import {
  RouterRunStore,
  RouterRunStoreError,
  type RouterAttemptSettlement,
} from "./routerRunStore.ts";

const temporaryDirectories: string[] = [];

afterEach(async () => {
  await Promise.all(temporaryDirectories.splice(0).map((path) => rm(path, { recursive: true, force: true })));
});

async function workspace(): Promise<string> {
  const path = await mkdtemp(join(tmpdir(), "router-run-store-"));
  temporaryDirectories.push(path);
  await mkdir(join(path, "results"), { mode: 0o700 });
  return path;
}

function builtManifest(promptIds: readonly string[] = ["p001"]) {
  const models = ["model-a"];
  const reps = 1;
  const seed = 7;
  const maximumAttempts = 2;
  const unitCost = 10;
  const items = buildRouterPlanSeeds(promptIds, models, reps, seed).map(makeRouterPlanItem);
  const fixtureBytes = Buffer.from("fixture");
  const inventoryBytes = Buffer.from("inventory");
  const templateBytes = Buffer.from("template");
  const catalogBytes = Buffer.from("catalog");
  const packageLockBytes = Buffer.from("lock");
  const manifest = {
    schema: ROUTER_RUN_MANIFEST_SCHEMA,
    source: {
      git_object_format: "sha1",
      proposal_commit_oid: "1".repeat(40),
      proposal_tree_oid: "2".repeat(40),
      worktree_clean: true,
      inventory_source_tree_digest: `sha256:${"3".repeat(64)}`,
    },
    inputs: {
      fixture: {
        sha256: sha256Bytes(fixtureBytes),
        size_bytes: fixtureBytes.length,
        record_count: promptIds.length,
      },
      inventory: {
        sha256: sha256Bytes(inventoryBytes),
        size_bytes: inventoryBytes.length,
        source_count: 1,
      },
      prompt_template: {
        sha256: sha256Bytes(templateBytes),
        size_bytes: templateBytes.length,
        template_count: 1,
      },
      skill_catalog: {
        sha256: sha256Bytes(catalogBytes),
        size_bytes: catalogBytes.length,
        skill_count: 1,
        skill_ids: ["skill-a"],
      },
      package_lock: {
        sha256: sha256Bytes(packageLockBytes),
        size_bytes: packageLockBytes.length,
        package_count: 1,
      },
    },
    runtime: {
      node_version: "v22.13.0",
      cursor_sdk_version: "1.0.28",
      platform: "darwin",
      arch: "arm64",
      tools: [],
      setting_sources: [],
      sdk_retries: false,
    },
    plan: {
      prompt_ids: [...promptIds],
      models,
      reps,
      seed,
      max_format_attempts: maximumAttempts,
      item_count: items.length,
      items,
      items_digest: domainSeparatedDigest(
        "router-run-plan/v1",
        canonicalJsonBytes(items as unknown as JsonValue),
      ),
    },
    cost: {
      currency: "USD",
      estimated_micro_usd_per_sdk_attempt: unitCost,
      forecast_sdk_invocations: items.length * maximumAttempts,
      max_sdk_invocations: items.length * maximumAttempts,
      forecast_micro_usd: items.length * maximumAttempts * unitCost,
      cap_micro_usd: items.length * maximumAttempts * unitCost,
    },
  };
  return parseRouterRunManifestFile(canonicalFileBytes(manifest as unknown as JsonValue));
}

const FINISHED: RouterAttemptSettlement = {
  status: "finished",
  finished_at: "2026-08-15T12:00:02Z",
  duration_ms: 20,
  request_id: "request-1",
  resolved_model_id: "model-a",
  raw_text: '{"ranking":["skill-a"]}',
  ranking: ["skill-a"],
  confidence_millionths: 900_000,
  rationale: "skill-a is the closest match",
};

test("format retry, terminal materialization, and resume skip are manifest-bound", async () => {
  const root = await workspace();
  const store = new RouterRunStore(join(root, "results"), builtManifest());
  const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
  await store.initialize(lease);
  const item = store.manifest.manifest.plan.items[0]!;

  let state = await store.preflight(lease);
  assert.equal(state.pending[0]?.next_attempt, 1);
  const first = await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
  await assert.rejects(
    store.preflight(lease),
    (error: unknown) => error instanceof RouterRunStoreError && error.code === "RECONCILIATION_REQUIRED",
  );
  await store.settle(lease, first, {
    status: "format_failure",
    finished_at: "2026-08-15T12:00:02Z",
    duration_ms: 10,
    raw_text: "not-json",
    error_code: "FORMAT_FAILURE",
    error_message: "response was not strict router JSON",
  });

  state = await store.preflight(lease);
  assert.equal(state.pending[0]?.next_attempt, 2);
  assert.equal(state.claimed_invocations, 1);
  assert.equal(state.claimed_cost_microusd, 10);
  const second = await store.claim(lease, item.item_id, "2026-08-15T12:00:03Z");
  await store.settle(lease, second, { ...FINISHED, finished_at: "2026-08-15T12:00:04Z" });
  state = await store.preflight(lease);
  assert.deepEqual(state.pending, []);
  assert.deepEqual(state.terminal_pending.map((candidate) => candidate.item_id), [item.item_id]);
  await store.writeTerminal(lease, item.item_id);
  state = await store.preflight(lease);
  assert.deepEqual(state.completed_item_ids, [item.item_id]);
  assert.equal(state.claimed_invocations, 2);
  assert.equal(state.claimed_cost_microusd, 20);
  await assert.rejects(
    store.writeTerminal(lease, item.item_id),
    (error: unknown) => error instanceof RouterRunStoreError && error.code === "RESULT_CONFLICT",
  );
  await store.release(lease);
});

test("operational terminal outcomes are not retry eligible", async () => {
  const root = await workspace();
  const store = new RouterRunStore(join(root, "results"), builtManifest());
  const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
  await store.initialize(lease);
  const item = store.manifest.manifest.plan.items[0]!;
  const claim = await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
  await store.settle(lease, claim, {
    status: "provider_error",
    finished_at: "2026-08-15T12:00:02Z",
    duration_ms: 5,
    error_code: "PROVIDER_ERROR",
    error_message: "fixture failure",
  });
  const state = await store.preflight(lease);
  assert.deepEqual(state.pending, []);
  assert.deepEqual(state.terminal_pending.map((candidate) => candidate.item_id), [item.item_id]);
  await store.release(lease);
});

test("store settlement enforces the engine's status-specific outcome contract", async () => {
  const illegal: RouterAttemptSettlement[] = [
    {
      status: "finished",
      finished_at: FINISHED.finished_at,
      duration_ms: 1,
      ranking: ["skill-a"],
      confidence_millionths: 1,
      rationale: "x",
    },
    {
      status: "finished",
      finished_at: FINISHED.finished_at,
      duration_ms: 1,
      raw_text: "{}",
      ranking: ["skill-a"],
      confidence_millionths: 1,
      rationale: "x",
      error_code: "NOT_ALLOWED",
    },
    {
      status: "format_failure",
      finished_at: FINISHED.finished_at,
      duration_ms: 1,
    },
    {
      status: "provider_error",
      finished_at: FINISHED.finished_at,
      duration_ms: 1,
    },
    {
      status: "provider_error",
      finished_at: FINISHED.finished_at,
      duration_ms: 1,
      raw_text: "provider body",
      error_code: "PROVIDER_ERROR",
      error_message: "failed",
    },
    {
      status: "cancelled",
      finished_at: FINISHED.finished_at,
      duration_ms: 1,
      raw_text: "partial body",
    },
  ];
  for (const settlement of illegal) {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
    await store.initialize(lease);
    const item = store.manifest.manifest.plan.items[0]!;
    const claim = await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
    await assert.rejects(
      store.settle(lease, claim, settlement),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
    await store.release(lease);
  }
});

test("lease authority, timestamps, and catalog membership fail closed", async () => {
  {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    await assert.rejects(
      store.acquire("owner-a", "2026-02-31T12:00:00Z"),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
  }

  {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    const lease = await store.acquire("owner-a", "2026-08-15T12:00:02Z");
    assert.throws(() => {
      (lease as unknown as { owner_id: string }).owner_id = "forged-owner";
    }, TypeError);
    const exposedBody = lease.lock_body;
    exposedBody[0] = (exposedBody[0] as number) ^ 0x01;
    await assert.rejects(
      store.initialize(lease),
      (error: unknown) => error instanceof RouterRunStoreError && error.code === "RUN_LOCKED",
    );
  }

  {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    const lease = await store.acquire("owner-a", "2026-08-15T12:00:02Z");
    await store.initialize(lease);
    const item = store.manifest.manifest.plan.items[0]!;
    await assert.rejects(
      store.claim(lease, item.item_id, "2026-04-31T12:00:03Z"),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
    await assert.rejects(
      store.claim(lease, item.item_id, "2026-08-15T12:00:01Z"),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
    const claim = await store.claim(lease, item.item_id, "2026-08-15T12:00:03Z");
    assert.equal(claim.lock_generation, lease.lock_generation);
    await assert.rejects(
      store.settle(lease, claim, { ...FINISHED, finished_at: "2026-08-15T12:00:02Z" }),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
    await store.release(lease);
  }

  {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
    await store.initialize(lease);
    const item = store.manifest.manifest.plan.items[0]!;
    const claim = await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
    await assert.rejects(
      store.settle(lease, claim, { ...FINISHED, ranking: ["foreign-skill"] }),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
    await store.release(lease);
  }

  {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
    await store.initialize(lease);
    const item = store.manifest.manifest.plan.items[0]!;
    const claim = await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
    await assert.rejects(
      store.settle(lease, claim, { ...FINISHED, finished_at: "2026-02-29T12:00:02Z" }),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
    await store.release(lease);
  }
});

test("persisted chronology and retry provenance are revalidated during scan", async () => {
  {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
    await store.initialize(lease);
    const item = store.manifest.manifest.plan.items[0]!;
    const claim = await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
    const outcome = await store.settle(lease, claim, FINISHED);
    const outcomesDirectory = join(store.runDirectory, "attempt-outcomes");
    const [outcomeName] = await readdir(outcomesDirectory);
    assert.ok(outcomeName);
    await rm(join(outcomesDirectory, outcomeName));
    await writeFile(
      join(outcomesDirectory, outcomeName),
      canonicalFileBytes({ ...outcome, finished_at: "2026-08-15T12:00:00Z" } as unknown as JsonValue),
    );
    await assert.rejects(
      store.preflight(lease),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
  }

  {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
    await store.initialize(lease);
    const item = store.manifest.manifest.plan.items[0]!;
    const firstClaim = await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
    const firstOutcome = await store.settle(lease, firstClaim, {
      status: "provider_error",
      finished_at: "2026-08-15T12:00:02Z",
      duration_ms: 1,
      error_code: "PROVIDER_ERROR",
      error_message: "terminal provider failure",
    });
    const secondClaim = {
      ...firstClaim,
      attempt: 2,
      claimed_at: "2026-08-15T12:00:03Z",
    };
    const secondClaimBytes = canonicalFileBytes(secondClaim as unknown as JsonValue);
    const secondOutcome = {
      ...firstOutcome,
      attempt: 2,
      claim_digest: sha256Bytes(secondClaimBytes),
      status: "finished",
      finished_at: "2026-08-15T12:00:04Z",
      raw_text: '{"ranking":["skill-a"]}',
      ranking: ["skill-a"],
      confidence_millionths: 900_000,
      rationale: "skill-a is the closest match",
      error_code: null,
      error_message: null,
    };
    const secondName = attemptStateFileName(store.manifest.digest, item.item_id, 2);
    await writeFile(join(store.runDirectory, "attempt-claims", secondName), secondClaimBytes);
    await writeFile(
      join(store.runDirectory, "attempt-outcomes", secondName),
      canonicalFileBytes(secondOutcome as unknown as JsonValue),
    );
    await assert.rejects(
      store.preflight(lease),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "FOREIGN_STATE",
    );
  }

  {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest(["first", "second"]));
    const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
    await store.initialize(lease);
    const [first, second] = store.manifest.manifest.plan.items;
    assert.ok(first && second);
    const firstClaim = await store.claim(lease, first.item_id, "2026-08-15T13:00:00Z");
    await store.settle(lease, firstClaim, { ...FINISHED, finished_at: "2026-08-15T14:00:00Z" });
    await store.writeTerminal(lease, first.item_id);
    await assert.rejects(
      store.claim(lease, second.item_id, "2026-08-15T13:30:00Z"),
      (error: unknown) =>
        error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
    await store.release(lease);
  }
});

test("claims must follow canonical plan order", async () => {
  const root = await workspace();
  const store = new RouterRunStore(join(root, "results"), builtManifest(["first", "second"]));
  const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
  await store.initialize(lease);
  const [first, second] = store.manifest.manifest.plan.items;
  assert.ok(first && second);

  await assert.rejects(
    store.claim(lease, second.item_id, "2026-08-15T12:00:01Z"),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "RESULT_CONFLICT",
  );

  const firstClaim = await store.claim(lease, first.item_id, "2026-08-15T12:00:01Z");
  await store.settle(lease, firstClaim, FINISHED);
  await store.writeTerminal(lease, first.item_id);
  const secondClaim = await store.claim(lease, second.item_id, "2026-08-15T12:00:03Z");
  await store.settle(lease, secondClaim, { ...FINISHED, finished_at: "2026-08-15T12:00:04Z" });
  await store.writeTerminal(lease, second.item_id);

  const state = await store.preflight(lease);
  assert.deepEqual(state.pending, []);
  assert.deepEqual(state.completed_item_ids, [first.item_id, second.item_id]);
  await store.release(lease);
});

test("an unmatched claim remains permanently fail-closed", async () => {
  const root = await workspace();
  const store = new RouterRunStore(join(root, "results"), builtManifest());
  const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
  await store.initialize(lease);
  const item = store.manifest.manifest.plan.items[0]!;
  await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
  await assert.rejects(
    store.preflight(lease),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "RECONCILIATION_REQUIRED",
  );
  assert.equal("reconcileAmbiguousAttempt" in store, false);
  await store.release(lease);
});

test("a restarted process cannot ordinarily settle a persisted ambiguous claim", async () => {
  const root = await workspace();
  const manifest = builtManifest();
  const first = new RouterRunStore(join(root, "results"), manifest);
  const firstLease = await first.acquire("owner-a", "2026-08-15T12:00:00Z");
  await first.initialize(firstLease);
  const item = first.manifest.manifest.plan.items[0]!;
  const claim = await first.claim(firstLease, item.item_id, "2026-08-15T12:00:01Z");
  await first.release(firstLease);

  const restarted = new RouterRunStore(join(root, "results"), manifest);
  const restartedLease = await restarted.acquire("owner-b", "2026-08-15T12:00:02Z");
  await assert.rejects(
    restarted.settle(restartedLease, { ...claim }, FINISHED),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "RECONCILIATION_REQUIRED",
  );
  await assert.rejects(
    restarted.preflight(restartedLease),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "RECONCILIATION_REQUIRED",
  );
  await restarted.release(restartedLease);
});

test("stale run locks block a second process and exact release permits a new generation", async () => {
  const root = await workspace();
  const manifest = builtManifest();
  const first = new RouterRunStore(join(root, "results"), manifest);
  const second = new RouterRunStore(join(root, "results"), manifest);
  const lease = await first.acquire("owner-a", "2026-08-15T12:00:00Z");
  await assert.rejects(
    second.acquire("owner-b", "2026-08-15T12:00:01Z"),
    (error: unknown) => error instanceof RouterRunStoreError && error.code === "RUN_LOCKED",
  );
  await first.release(lease);
  const replacement = await second.acquire("owner-b", "2026-08-15T12:00:01Z");
  await second.release(replacement);
});

test("the same owner and timestamp can acquire and release distinct lock generations", async () => {
  const root = await workspace();
  const store = new RouterRunStore(join(root, "results"), builtManifest());
  const first = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
  await store.release(first);
  const second = await store.acquire("owner-a", "2026-08-15T12:00:00Z");

  assert.match(first.lock_generation, /^[0-9a-f]{64}$/);
  assert.match(second.lock_generation, /^[0-9a-f]{64}$/);
  assert.notEqual(second.lock_generation, first.lock_generation);
  assert.notDeepEqual(second.lock_body, first.lock_body);
  await store.release(second);
});

test("closed-world scan rejects extra, symlink, hardlinked, and wrongly named state", async () => {
  for (const variant of ["extra", "symlink", "hardlink", "wrong-name"] as const) {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    const lease = await store.acquire(`owner-${variant}`, "2026-08-15T12:00:00Z");
    await store.initialize(lease);
    const item = store.manifest.manifest.plan.items[0]!;
    if (variant === "extra") {
      await writeFile(join(store.runDirectory, "unexpected"), "x");
    } else if (variant === "symlink") {
      await symlink(join(store.runDirectory, "manifest.json"), join(store.runDirectory, "results", `${"a".repeat(64)}.json`));
    } else {
      await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
      const claims = join(store.runDirectory, "attempt-claims");
      const [name] = await readdir(claims);
      assert.ok(name);
      if (variant === "hardlink") {
        await link(join(claims, name), join(root, "claim-alias"));
      } else {
        await rename(join(claims, name), join(claims, `${"b".repeat(64)}.json`));
      }
    }
    await assert.rejects(store.preflight(lease));
  }
});

test("noncanonical, duplicate-key, and truncated claim files fail closed", async () => {
  for (const body of [
    '{"schema":"router-inflight-claim/v1"}\n\n',
    '{"schema":"router-inflight-claim/v1","schema":"router-inflight-claim/v1"}\n',
    '{"schema":',
  ]) {
    const root = await workspace();
    const store = new RouterRunStore(join(root, "results"), builtManifest());
    const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
    await store.initialize(lease);
    await writeFile(join(store.runDirectory, "attempt-claims", `${"c".repeat(64)}.json`), body);
    await assert.rejects(
      store.preflight(lease),
      (error: unknown) => error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
    );
  }
});

test("oversized outcomes are rejected before publication and cannot poison scans", async () => {
  const root = await workspace();
  const store = new RouterRunStore(join(root, "results"), builtManifest());
  const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
  await store.initialize(lease);
  const item = store.manifest.manifest.plan.items[0]!;
  const claim = await store.claim(lease, item.item_id, "2026-08-15T12:00:01Z");
  await assert.rejects(
    store.settle(lease, claim, {
      ...FINISHED,
      raw_text: "x".repeat(16 * 1024 * 1024),
    }),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "INVALID_RECORD",
  );
  assert.deepEqual(await readdir(join(store.runDirectory, "attempt-outcomes")), []);
  await assert.rejects(
    store.preflight(lease),
    (error: unknown) =>
      error instanceof RouterRunStoreError && error.code === "RECONCILIATION_REQUIRED",
  );
  await store.release(lease);
});

test("manifest and plan bytes are exact and cannot be replaced", async () => {
  const root = await workspace();
  const store = new RouterRunStore(join(root, "results"), builtManifest());
  const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
  await store.initialize(lease);
  await rm(join(store.runDirectory, "plan.json"));
  await writeFile(join(store.runDirectory, "plan.json"), "{}\n");
  await assert.rejects(
    store.preflight(lease),
    (error: unknown) => error instanceof RouterRunStoreError && error.code === "FOREIGN_STATE",
  );
});

test("public manifest and plan snapshots cannot mutate store authority", async () => {
  const root = await workspace();
  const store = new RouterRunStore(join(root, "results"), builtManifest());
  const exposed = store.manifest;
  assert.throws(() => {
    (exposed.manifest.cost as { max_sdk_invocations: number }).max_sdk_invocations = 99;
  }, TypeError);
  assert.throws(() => {
    (exposed.manifest.inputs.skill_catalog.skill_ids as string[]).push("foreign-skill");
  }, TypeError);
  exposed.canonicalBytes[0] = 0x00;
  const exposedPlan = store.planBytes;
  exposedPlan[0] = 0x00;

  const lease = await store.acquire("owner-a", "2026-08-15T12:00:00Z");
  await store.initialize(lease);
  const state = await store.preflight(lease);
  assert.equal(state.pending.length, 1);
  assert.equal(store.manifest.manifest.cost.max_sdk_invocations, 2);
  assert.deepEqual(store.manifest.manifest.inputs.skill_catalog.skill_ids, ["skill-a"]);
  await store.release(lease);
});

function attemptStateFileName(
  manifestDigest: string,
  itemId: string,
  attempt: number,
): string {
  const payload = canonicalJsonBytes({
    attempt,
    item_id: itemId,
    manifest_digest: manifestDigest,
  });
  return `${domainSeparatedDigest("router-attempt-state-file/v1", payload).slice("sha256:".length)}.json`;
}
