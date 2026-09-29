import assert from "node:assert/strict";
import { spawnSync } from "node:child_process";
import {
  mkdirSync,
  mkdtempSync,
  rmSync,
  writeFileSync,
} from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import { after, test } from "node:test";

import {
  DurableJsonError,
  canonicalFileBytes,
  canonicalJsonBytes,
  sha256Bytes,
} from "./durableJson.ts";
import type { JsonValue } from "./durableJson.ts";
import {
  RouterManifestError,
  buildRouterPlanSeeds,
  buildRouterRunManifest,
  deriveRouterShuffleSeed,
  makeRouterPlanItem,
  parseRouterRunManifestFile,
  parseUsdToMicroUsd,
  routerRunManifestDigest,
  validateRouterRunManifest,
} from "./routerManifest.ts";
import type {
  BuiltRouterRunManifest,
  RouterManifestBuildInput,
  RouterRunManifest,
} from "./routerManifest.ts";
import {
  SourceFreezeError,
  captureExactNamedInputs,
} from "./sourceFreeze.ts";
import type { ExactNamedInputCapture } from "./sourceFreeze.ts";

const GIT_ENV = {
  ...process.env,
  GIT_AUTHOR_DATE: "2026-01-01T00:00:00Z",
  GIT_COMMITTER_DATE: "2026-01-01T00:00:00Z",
};

interface CaptureFixture {
  readonly root: string;
  readonly capture: ExactNamedInputCapture;
  readonly files: Readonly<Record<CaptureFileName, Buffer>>;
  readonly inventoryDigest: string;
}

type CaptureFileName =
  | "fixture"
  | "inventory"
  | "package_lock"
  | "prompt_template"
  | "skill_catalog";

function validCaptureFiles(): {
  readonly files: Record<CaptureFileName, Buffer>;
  readonly inventoryDigest: string;
} {
  const sources = [{ digest: sha256Bytes("source"), path: "skills/example/SKILL.md" }];
  const inventoryDigest = sha256Bytes(
    canonicalJsonBytes({ schema_version: "1.0.0", sources }),
  );
  const fixtureRecords = [
    {
      prompt_id: "prompt-a",
      prompt: "Route the first prompt.",
      expected_primary_skill: "skill-a",
      acceptable_secondary_skills: ["skill-b"],
      rejected_skills: [],
      reason: "First routing case.",
    },
    {
      prompt_id: "prompt-b",
      prompt: "Route the second prompt.",
      expected_primary_skill: "skill-b",
      acceptable_secondary_skills: [],
      rejected_skills: ["skill-a"],
      reason: "Second routing case.",
    },
  ];
  return {
    inventoryDigest,
    files: {
      fixture: Buffer.from(`${fixtureRecords.map((record) => JSON.stringify(record)).join("\n")}\n`),
      inventory: Buffer.from(
        `${JSON.stringify({
          schema_version: "1.0.0",
          source_tree_digest: inventoryDigest,
          sources,
        })}\n`,
      ),
      package_lock: Buffer.from(
        `${JSON.stringify({
          name: "runner-fixture",
          lockfileVersion: 3,
          requires: true,
          packages: {
            "": { dependencies: { "@cursor/sdk": "1.0.28" } },
            "node_modules/@cursor/sdk": { version: "1.0.28" },
            "node_modules/dependency": { version: "2.0.0" },
          },
        })}\n`,
      ),
      prompt_template: Buffer.from("Skills:\n{{SKILL_BLOCK}}\nPrompt: {{USER_PROMPT}}\n"),
      skill_catalog: Buffer.from(
        `${JSON.stringify([
          { name: "skill-a", description: "Routes the first class." },
          { name: "skill-b", description: "Routes the second class." },
        ])}\n`,
      ),
    },
  };
}

function createCaptureFixture(
  overrides: Partial<Record<CaptureFileName, Uint8Array>> = {},
  logicalNames: Readonly<Record<string, CaptureFileName>> = {
    fixture: "fixture",
    inventory: "inventory",
    package_lock: "package_lock",
    prompt_template: "prompt_template",
    skill_catalog: "skill_catalog",
  },
): CaptureFixture {
  const root = mkdtempSync(join(tmpdir(), "router-manifest-repository-"));
  git(root, "init", "--quiet");
  git(root, "config", "user.name", "Router Manifest Test");
  git(root, "config", "user.email", "router-manifest@example.invalid");

  const defaults = validCaptureFiles();
  const files = Object.fromEntries(
    Object.entries(defaults.files).map(([name, bytes]) => [
      name,
      Buffer.from(overrides[name as CaptureFileName] ?? bytes),
    ]),
  ) as Record<CaptureFileName, Buffer>;
  const inputPaths: Record<string, string> = {};
  mkdirSync(join(root, "inputs"));
  for (const [name, bytes] of Object.entries(files) as Array<[CaptureFileName, Buffer]>) {
    const path = join(root, "inputs", `${name}.data`);
    writeFileSync(path, bytes);
  }
  for (const [logicalName, fileName] of Object.entries(logicalNames)) {
    inputPaths[logicalName] = join(root, "inputs", `${fileName}.data`);
  }
  git(root, "add", "inputs");
  git(root, "commit", "--quiet", "-m", "fixture inputs");
  return {
    root,
    capture: captureExactNamedInputs(root, inputPaths),
    files,
    inventoryDigest: defaults.inventoryDigest,
  };
}

const BASE = createCaptureFixture();
after(() => rmSync(BASE.root, { recursive: true, force: true }));

function buildInput(capture: ExactNamedInputCapture = BASE.capture): RouterManifestBuildInput {
  return {
    capture,
    models: ["model-a", "model-b"],
    reps: 2,
    seed: 17,
    maxFormatAttempts: 2,
    estimatedMicroUsdPerSdkAttempt: 12_000,
    maxSdkInvocations: 16,
    capMicroUsd: 2_000_000,
  };
}

function git(root: string, ...arguments_: string[]) {
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
  return result;
}

function assertManifestCode(source: () => unknown, code: string): void {
  assert.throws(
    source,
    (error: unknown) => error instanceof RouterManifestError && error.code === code,
  );
}

function assertDurableCode(source: () => unknown, code: string): void {
  assert.throws(
    source,
    (error: unknown) => error instanceof DurableJsonError && error.code === code,
  );
}

function mutableManifest(manifest: RouterRunManifest): Record<string, JsonValue> {
  return structuredClone(manifest) as unknown as Record<string, JsonValue>;
}

function nested(record: Record<string, JsonValue>, key: string): Record<string, JsonValue> {
  return record[key] as Record<string, JsonValue>;
}

test("builder derives source, semantics, runtime, full plan, and integer forecast", () => {
  const built = buildRouterRunManifest(buildInput());
  assert.equal(built.manifest.schema, "router-run-manifest/v1");
  assert.equal(built.manifest.source.git_object_format, BASE.capture.repository.objectFormat);
  assert.equal(built.manifest.source.proposal_commit_oid, BASE.capture.repository.commit);
  assert.equal(built.manifest.source.proposal_tree_oid, BASE.capture.repository.tree);
  assert.equal(built.manifest.source.worktree_clean, true);
  assert.equal(built.manifest.source.inventory_source_tree_digest, BASE.inventoryDigest);
  assert.equal(built.manifest.runtime.node_version, process.version);
  assert.equal(built.manifest.runtime.cursor_sdk_version, "1.0.28");
  assert.equal(built.manifest.runtime.platform, process.platform);
  assert.equal(built.manifest.runtime.arch, process.arch);
  assert.deepEqual(built.manifest.runtime.tools, []);
  assert.deepEqual(built.manifest.runtime.setting_sources, []);
  assert.equal(built.manifest.runtime.sdk_retries, false);
  assert.deepEqual(built.manifest.plan.prompt_ids, ["prompt-a", "prompt-b"]);
  assert.equal(built.manifest.plan.item_count, 8);
  assert.equal(built.manifest.cost.forecast_sdk_invocations, 16);
  assert.equal(built.manifest.cost.forecast_micro_usd, 192_000);
  assert.equal(built.manifest.inputs.fixture.sha256, sha256Bytes(BASE.files.fixture));
  assert.equal(built.manifest.inputs.fixture.size_bytes, BASE.files.fixture.length);
  assert.equal(built.manifest.inputs.fixture.record_count, 2);
  assert.equal(built.manifest.inputs.inventory.sha256, sha256Bytes(BASE.files.inventory));
  assert.equal(built.manifest.inputs.inventory.source_count, 1);
  assert.equal(built.manifest.inputs.prompt_template.template_count, 1);
  assert.equal(built.manifest.inputs.skill_catalog.skill_count, 2);
  assert.equal(built.manifest.inputs.package_lock.package_count, 3);
  assert.equal(built.canonicalBytes.at(-1), 0x0a);
  assert.notEqual(built.canonicalBytes.at(-2), 0x0a);
  assert.match(built.digest, /^sha256:[0-9a-f]{64}$/);
  assert.equal(routerRunManifestDigest(built.manifest), built.digest);

  const reparsed = parseRouterRunManifestFile(built.canonicalBytes);
  assert.deepEqual(reparsed, built);
  assert.deepEqual(
    built.canonicalBytes,
    canonicalFileBytes(built.manifest as unknown as JsonValue),
  );
});

test("exact inventory bytes participate in manifest identity", () => {
  const root = mkdtempSync(join(tmpdir(), "router-manifest-inventory-identity-"));
  try {
    git(root, "init", "--quiet");
    git(root, "config", "user.name", "Router Manifest Test");
    git(root, "config", "user.email", "router-manifest@example.invalid");
    writeFileSync(join(root, ".gitignore"), "inputs/\n");
    git(root, "add", ".gitignore");
    git(root, "commit", "--quiet", "-m", "fixed source identity");

    const defaults = validCaptureFiles();
    const inputRoot = join(root, "inputs");
    mkdirSync(inputRoot);
    const paths: Record<string, string> = {};
    for (const [name, bytes] of Object.entries(defaults.files)) {
      const path = join(inputRoot, `${name}.data`);
      writeFileSync(path, bytes);
      paths[name] = path;
    }
    const firstCapture = captureExactNamedInputs(root, paths);
    const first = buildRouterRunManifest(buildInput(firstCapture));

    const inventoryDocument = JSON.parse(defaults.files.inventory.toString("utf8")) as JsonValue;
    writeFileSync(paths.inventory!, `${JSON.stringify(inventoryDocument, null, 2)}\n`);
    const secondCapture = captureExactNamedInputs(root, paths);
    const second = buildRouterRunManifest(buildInput(secondCapture));

    assert.deepEqual(secondCapture.repository, firstCapture.repository);
    assert.equal(
      second.manifest.source.inventory_source_tree_digest,
      first.manifest.source.inventory_source_tree_digest,
    );
    assert.notEqual(second.manifest.inputs.inventory.sha256, first.manifest.inputs.inventory.sha256);
    assert.notEqual(second.digest, first.digest);
  } finally {
    rmSync(root, { recursive: true, force: true });
  }
});

test("builder is invariant across cwd, time, randomness, and option insertion order", () => {
  const first = buildRouterRunManifest(buildInput());
  const scratch = mkdtempSync(join(tmpdir(), "router-manifest-cwd-"));
  const priorCwd = process.cwd();
  const priorNow = Date.now;
  const priorRandom = Math.random;
  try {
    process.chdir(scratch);
    Date.now = () => 1_999_999_999_999;
    Math.random = () => 0.999999;
    const original = buildInput();
    const reordered = {
      capMicroUsd: original.capMicroUsd,
      maxSdkInvocations: original.maxSdkInvocations,
      estimatedMicroUsdPerSdkAttempt: original.estimatedMicroUsdPerSdkAttempt,
      maxFormatAttempts: original.maxFormatAttempts,
      seed: original.seed,
      reps: original.reps,
      models: original.models,
      capture: original.capture,
    } satisfies RouterManifestBuildInput;
    const second = buildRouterRunManifest(reordered);
    assert.deepEqual(second.canonicalBytes, first.canonicalBytes);
    assert.equal(second.digest, first.digest);
    assert.equal(second.canonicalBytes.includes(Buffer.from(scratch)), false);
  } finally {
    Date.now = priorNow;
    Math.random = priorRandom;
    process.chdir(priorCwd);
    rmSync(scratch, { recursive: true, force: true });
  }
});

test("plan identities use full structured digests and separate delimiter collisions", () => {
  const left = makeRouterPlanItem({
    prompt_id: "a|b",
    model_id: "c",
    rep: 0,
    shuffle_seed: 7,
  });
  const right = makeRouterPlanItem({
    prompt_id: "a",
    model_id: "b|c",
    rep: 0,
    shuffle_seed: 7,
  });
  assert.notEqual(left.item_id, right.item_id);
  assert.match(left.item_id, /^sha256:[0-9a-f]{64}$/);
  assert.notEqual(
    deriveRouterShuffleSeed("a|b", "c", 0, 1),
    deriveRouterShuffleSeed("a", "b|c", 0, 1),
  );
});

test("closed validator rejects unknown, missing, ambient, and unclean fields", () => {
  const built = buildRouterRunManifest(buildInput());

  const unknown = mutableManifest(built.manifest);
  unknown.created_at = "2026-08-15T00:00:00Z";
  assertManifestCode(() => validateRouterRunManifest(unknown), "UNKNOWN_FIELD");

  const missing = mutableManifest(built.manifest);
  delete nested(missing, "runtime").arch;
  assertManifestCode(() => validateRouterRunManifest(missing), "MISSING_FIELD");

  const tool = mutableManifest(built.manifest);
  nested(tool, "runtime").tools = ["shell"];
  assertManifestCode(() => validateRouterRunManifest(tool), "INVALID_FIELD");

  const settings = mutableManifest(built.manifest);
  nested(settings, "runtime").setting_sources = ["project"];
  assertManifestCode(() => validateRouterRunManifest(settings), "INVALID_FIELD");

  const retries = mutableManifest(built.manifest);
  nested(retries, "runtime").sdk_retries = true;
  assertManifestCode(() => validateRouterRunManifest(retries), "INVALID_FIELD");

  const dirty = mutableManifest(built.manifest);
  nested(dirty, "source").worktree_clean = false;
  assertManifestCode(() => validateRouterRunManifest(dirty), "SOURCE_NOT_CLEAN");

  const badDigest = mutableManifest(built.manifest);
  nested(nested(badDigest, "inputs"), "fixture").sha256 = "sha256:short";
  assertManifestCode(() => validateRouterRunManifest(badDigest), "INVALID_DIGEST");
});

test("validator recomputes plan order, IDs, digest, cardinality, and forecast", () => {
  const built = buildRouterRunManifest(buildInput());

  const badId = mutableManifest(built.manifest);
  const badIdItems = nested(badId, "plan").items as Array<Record<string, JsonValue>>;
  badIdItems[0]!.item_id = sha256Bytes("forged-item");
  assertManifestCode(() => validateRouterRunManifest(badId), "PLAN_ITEM_ID_MISMATCH");

  const reordered = mutableManifest(built.manifest);
  const reorderedItems = nested(reordered, "plan").items as JsonValue[];
  [reorderedItems[0], reorderedItems[1]] = [reorderedItems[1]!, reorderedItems[0]!];
  assertManifestCode(() => validateRouterRunManifest(reordered), "PLAN_CARDINALITY_MISMATCH");

  const badPlanDigest = mutableManifest(built.manifest);
  nested(badPlanDigest, "plan").items_digest = sha256Bytes("forged-plan");
  assertManifestCode(() => validateRouterRunManifest(badPlanDigest), "PLAN_DIGEST_MISMATCH");

  const badCount = mutableManifest(built.manifest);
  nested(badCount, "plan").item_count = 7;
  assertManifestCode(() => validateRouterRunManifest(badCount), "PLAN_CARDINALITY_MISMATCH");

  const badFixtureCount = mutableManifest(built.manifest);
  nested(nested(badFixtureCount, "inputs"), "fixture").record_count = 3;
  assertManifestCode(
    () => validateRouterRunManifest(badFixtureCount),
    "PLAN_CARDINALITY_MISMATCH",
  );

  const badForecast = mutableManifest(built.manifest);
  nested(badForecast, "cost").forecast_micro_usd = 1;
  assertManifestCode(() => validateRouterRunManifest(badForecast), "FORECAST_MISMATCH");

  const overBudget = mutableManifest(built.manifest);
  nested(overBudget, "cost").cap_micro_usd = 191_999;
  assertManifestCode(() => validateRouterRunManifest(overBudget), "BUDGET_EXCEEDED");

  const overInvocation = mutableManifest(built.manifest);
  nested(overInvocation, "cost").max_sdk_invocations = 15;
  assertManifestCode(() => validateRouterRunManifest(overInvocation), "BUDGET_EXCEEDED");
});

test("builder generates the complete plan internally and caps format attempts at two", () => {
  const input = buildInput();
  const built = buildRouterRunManifest(input);
  const expected = buildRouterPlanSeeds(
    ["prompt-a", "prompt-b"],
    input.models,
    input.reps,
    input.seed,
  );
  assert.deepEqual(
    built.manifest.plan.items.map(({ item_id: _itemId, ...seed }) => seed),
    expected,
  );
  assertManifestCode(
    () =>
      buildRouterRunManifest({
        ...input,
        maxFormatAttempts: 3,
        maxSdkInvocations: 24,
      }),
    "INVALID_FIELD",
  );
});

test("builder denies fabricated, cloned, mutated, missing, and extra captures", () => {
  const fabricated = structuredClone(BASE.capture) as ExactNamedInputCapture;
  assert.throws(
    () => buildRouterRunManifest(buildInput(fabricated)),
    (error: unknown) => error instanceof SourceFreezeError && error.code === "CAPTURE_UNVERIFIED",
  );

  const mutated = createCaptureFixture();
  try {
    mutated.capture.inputs.fixture!.bytes[0] ^= 0x01;
    assert.throws(
      () => buildRouterRunManifest(buildInput(mutated.capture)),
      (error: unknown) => error instanceof SourceFreezeError && error.code === "INPUT_CHANGED",
    );
  } finally {
    rmSync(mutated.root, { recursive: true, force: true });
  }

  for (const logicalNames of [
    {
      fixture: "fixture",
      package_lock: "package_lock",
      prompt_template: "prompt_template",
      skill_catalog: "skill_catalog",
    },
    {
      fixture: "fixture",
      inventory: "inventory",
      package_lock: "package_lock",
      prompt_template: "prompt_template",
      skill_catalog: "skill_catalog",
      unexpected: "inventory",
    },
  ] as Array<Record<string, CaptureFileName>>) {
    const fixture = createCaptureFixture({}, logicalNames);
    try {
      assertManifestCode(
        () => buildRouterRunManifest(buildInput(fixture.capture)),
        "INVALID_FIELD",
      );
    } finally {
      rmSync(fixture.root, { recursive: true, force: true });
    }
  }
});

test("builder rejects semantic claims that do not derive from exact input bytes", () => {
  const duplicateFixture = Buffer.from(
    [
      {
        prompt_id: "duplicate",
        prompt: "First.",
        expected_primary_skill: "skill-a",
      },
      {
        prompt_id: "duplicate",
        prompt: "Second.",
        expected_primary_skill: "skill-b",
      },
    ].map((record) => JSON.stringify(record)).join("\n") + "\n",
  );
  const invalidInventory = Buffer.from(
    `${JSON.stringify({
      schema_version: "1.0.0",
      source_tree_digest: sha256Bytes("forged"),
      sources: [{ path: "source", digest: sha256Bytes("source") }],
    })}\n`,
  );
  const mismatchedLock = Buffer.from(
    `${JSON.stringify({
      lockfileVersion: 3,
      packages: {
        "": { dependencies: { "@cursor/sdk": "1.0.28" } },
        "node_modules/@cursor/sdk": { version: "1.0.27" },
      },
    })}\n`,
  );
  const catalogWithUnknownField = Buffer.from(
    `${JSON.stringify([
      { name: "skill-a", description: "A", authority: "forged" },
    ])}\n`,
  );

  for (const [name, overrides, expectedCode] of [
    ["duplicate fixture ids", { fixture: duplicateFixture }, "INVALID_FIELD"],
    ["forged inventory digest", { inventory: invalidInventory }, "INVALID_FIELD"],
    ["mismatched SDK versions", { package_lock: mismatchedLock }, "INVALID_FIELD"],
    ["open skill entry", { skill_catalog: catalogWithUnknownField }, "UNKNOWN_FIELD"],
    ["empty template", { prompt_template: Buffer.from(" \n") }, "INVALID_FIELD"],
  ] as const) {
    const fixture = createCaptureFixture(overrides);
    try {
      assertManifestCode(
        () => buildRouterRunManifest(buildInput(fixture.capture)),
        expectedCode,
      );
    } finally {
      rmSync(fixture.root, { recursive: true, force: true });
    }
    assert.ok(name);
  }

  for (const [overrides, expectedCode] of [
    [
      {
        fixture: Buffer.from(
          '{"prompt_id":"one","prompt_id":"two","prompt":"x","expected_primary_skill":"skill-a"}\n',
        ),
      },
      "DUPLICATE_KEY",
    ],
    [{ prompt_template: Buffer.from([0xff]) }, "INVALID_JSON"],
  ] as const) {
    const fixture = createCaptureFixture(overrides);
    try {
      assertDurableCode(
        () => buildRouterRunManifest(buildInput(fixture.capture)),
        expectedCode,
      );
    } finally {
      rmSync(fixture.root, { recursive: true, force: true });
    }
  }
});

test("USD conversion is exact and rejects ambiguous or inexact syntax", () => {
  assert.equal(parseUsdToMicroUsd("0"), 0);
  assert.equal(parseUsdToMicroUsd("1"), 1_000_000);
  assert.equal(parseUsdToMicroUsd("1.2"), 1_200_000);
  assert.equal(parseUsdToMicroUsd("0.000001"), 1);
  assert.equal(parseUsdToMicroUsd("9007199254.740991"), Number.MAX_SAFE_INTEGER);

  for (const source of [
    "",
    "+1",
    "-1",
    " 1",
    "1 ",
    "01",
    ".1",
    "1.",
    "1.0000000",
    "1e0",
    "1E6",
    "9007199254.740992",
  ]) {
    assertManifestCode(() => parseUsdToMicroUsd(source), "INVALID_USD");
  }
});

test("manifest parser rejects noncanonical durable bytes", () => {
  const built: BuiltRouterRunManifest = buildRouterRunManifest(buildInput());
  const withoutLf = built.canonicalBytes.subarray(0, built.canonicalBytes.length - 1);
  assert.throws(
    () => parseRouterRunManifestFile(withoutLf),
    (error: unknown) => error instanceof DurableJsonError && error.code === "NON_CANONICAL",
  );
  const pretty = `${JSON.stringify(built.manifest, null, 2)}\n`;
  assert.throws(
    () => parseRouterRunManifestFile(pretty),
    (error: unknown) => error instanceof DurableJsonError && error.code === "NON_CANONICAL",
  );
});
