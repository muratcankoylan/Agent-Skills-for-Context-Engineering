import assert from "node:assert/strict";
import { link, mkdir, mkdtemp, realpath, rm, symlink, writeFile } from "node:fs/promises";
import { tmpdir } from "node:os";
import { join } from "node:path";
import test from "node:test";
import { NextRequest } from "next/server.js";
import * as observationRoute from "../app/api/observations/route.ts";
import { readObservationView } from "../lib/observation-reader.server.ts";
import { isLoopbackHost, observationMaxBytes, parseObservationView } from "../lib/observation-view.ts";

const now = Date.parse("2026-09-07T22:00:00Z");

function fixture() {
  return {
    schema: "local-research-observation-view/v1", authority: "none", production_ready: false,
    generated_at: "2026-09-07T22:00:00Z",
    runs: [{
      run_id: "764b6e58-faf4-4d77-8c8b-7751c67f4245", query: "context engineering agents",
      status: "awaiting_researcher", observed_at: "2026-09-07T21:59:00Z",
      source_count: 2, capture_count: 3, context_bytes: 1234, model_calls: 0,
      report_digest: "sha256:" + "a".repeat(64),
      blockers: ["Researcher has not run.", "Independent evaluation has not run."],
    }],
  };
}

async function workspace() {
  const directory = await realpath(await mkdtemp(join(tmpdir(), "observation-reader-")));
  const file = join(directory, "summary.json");
  const environment = {
    RESEARCH_OBSERVATIONS_ENABLED: "1", HOSTNAME: "127.0.0.1", RESEARCH_OBSERVATION_FILE: file,
  };
  return { directory, file, environment, cleanup: () => rm(directory, { recursive: true, force: true }) };
}

test("observation opt-in and loopback checks precede filesystem access", async () => {
  for (const environment of [
    {}, { RESEARCH_OBSERVATIONS_ENABLED: "true" },
    { RESEARCH_OBSERVATIONS_ENABLED: "1", HOSTNAME: "0.0.0.0" },
    { RESEARCH_OBSERVATIONS_ENABLED: "1", HOSTNAME: "localhost" },
  ]) {
    const result = await readObservationView({ environment, requestHost: "127.0.0.1:3000", now });
    assert.equal(result.state, "disabled");
    assert.equal(result.data, null);
  }
  const rejected = await readObservationView({
    environment: { RESEARCH_OBSERVATIONS_ENABLED: "1", HOSTNAME: "127.0.0.1" },
    requestHost: "attacker.example", now,
  });
  assert.equal(rejected.reason, "loopback_required");
  for (const host of ["localhost", "127.0.0.1.example", "127.0.0.1:0", "127.0.0.1:65536", "127.0.0.1@evil", "[::1]"]) assert.equal(isLoopbackHost(host), false);
});

test("missing configuration and absent files remain missing without private paths", async () => {
  const workspaceValue = await workspace();
  try {
    const missing = await readObservationView({ environment: workspaceValue.environment, requestHost: "127.0.0.1", now });
    assert.equal(missing.state, "missing");
    assert.doesNotMatch(JSON.stringify(missing), new RegExp(workspaceValue.directory));
    const unconfigured = await readObservationView({ environment: { RESEARCH_OBSERVATIONS_ENABLED: "1", HOSTNAME: "127.0.0.1" }, requestHost: "127.0.0.1", now });
    assert.equal(unconfigured.reason, "observation_file_not_configured");
  } finally { await workspaceValue.cleanup(); }
});

test("valid summaries expose actual counts, including captures without leads", async () => {
  const value = fixture();
  value.runs[0].source_count = 0;
  value.runs[0].status = "failed";
  const parsed = parseObservationView(JSON.stringify(value), now);
  assert.equal(parsed.runs[0].source_count, 0);
  assert.equal(parsed.runs[0].capture_count, 3);
  assert.equal(parsed.runs[0].model_calls, 0);
});

test("reader refreshes each request and reports freshness independently from run status", async () => {
  const value = await workspace();
  try {
    const input = fixture();
    await writeFile(value.file, JSON.stringify(input));
    const first = await readObservationView({ environment: value.environment, requestHost: "127.0.0.1", now });
    assert.equal(first.state, "current");
    input.generated_at = "2026-09-07T19:00:00Z";
    input.runs[0].observed_at = "2026-09-07T18:59:00Z";
    input.runs[0].query = "updated observation";
    await writeFile(value.file, JSON.stringify(input));
    const second = await readObservationView({ environment: value.environment, requestHost: "127.0.0.1", now });
    assert.equal(second.state, "stale");
    assert.equal(second.data?.runs[0].query, "updated observation");
    assert.equal(second.data?.runs[0].status, "awaiting_researcher");
  } finally { await value.cleanup(); }
});

test("schema rejects forged authority, model calls, unknown fields, and invalid counts", () => {
  const invalid: unknown[] = [
    { ...fixture(), production_ready: true }, { ...fixture(), authority: "production" },
    { ...fixture(), raw_evidence: "/private/raw-source" },
    { ...fixture(), runs: [{ ...fixture().runs[0], model_calls: 1 }] },
    { ...fixture(), runs: [{ ...fixture().runs[0], raw_path: "/private/raw-source" }] },
    { ...fixture(), runs: [{ ...fixture().runs[0], source_count: true }] },
    { ...fixture(), runs: [{ ...fixture().runs[0], source_count: 1001 }] },
    { ...fixture(), runs: [{ ...fixture().runs[0], capture_count: 1001 }] },
    { ...fixture(), runs: [{ ...fixture().runs[0], context_bytes: -1 }] },
    { ...fixture(), runs: [{ ...fixture().runs[0], context_bytes: 1.5 }] },
    { ...fixture(), runs: [{ ...fixture().runs[0], query: "x".repeat(2049) }] },
    { ...fixture(), runs: [{ ...fixture().runs[0], status: "completed" }] },
    { ...fixture(), runs: [{ ...fixture().runs[0], blockers: [1] }] },
    { ...fixture(), runs: [fixture().runs[0], fixture().runs[0]] },
    { ...fixture(), runs: Array(51).fill(fixture().runs[0]) },
  ];
  for (const input of invalid) assert.throws(() => parseObservationView(JSON.stringify(input), now));
});

test("timestamps reject calendar normalization, absent UTC, future skew, and corrupt run times", () => {
  for (const generated_at of ["2026-02-30T22:00:00Z", "2026-09-07T22:00:00", "2026-09-07T22:00:00+00:00", "2026-09-07T22:01:01Z", "not-a-time"]) {
    assert.throws(() => parseObservationView(JSON.stringify({ ...fixture(), generated_at }), now));
  }
  assert.doesNotThrow(() => parseObservationView(JSON.stringify({ ...fixture(), generated_at: "2026-09-07T22:01:00Z" }), now));
  assert.throws(() => parseObservationView(JSON.stringify({ ...fixture(), runs: [{ ...fixture().runs[0], observed_at: "2026-09-07T23:00:00Z" }] }), now));
});

test("strict JSON rejects duplicate keys, trailing material, excessive depth, and malformed strings", () => {
  const original = JSON.stringify(fixture());
  for (const text of [
    original.replace('"production_ready":false', '"production_ready":true,"production_ready":false'),
    original.replace('"model_calls":0', '"model_calls":1,"model_calls":0'),
    original + " trailing", "[".repeat(1000) + "]".repeat(1000),
    original.replace("context engineering agents", "bad\u0000text"),
  ]) assert.throws(() => parseObservationView(text, now));
});

test("symlink leaves, symlink ancestors, hardlinks, and directories are not read", async () => {
  const value = await workspace();
  try {
    const target = join(value.directory, "target.json");
    await writeFile(target, JSON.stringify(fixture()));
    await symlink(target, value.file);
    assert.equal((await readObservationView({ environment: value.environment, requestHost: "127.0.0.1", now })).state, "invalid");
    await rm(value.file);
    await link(target, value.file);
    assert.equal((await readObservationView({ environment: value.environment, requestHost: "127.0.0.1", now })).state, "invalid");
    await rm(value.file);
    await mkdir(value.file);
    assert.equal((await readObservationView({ environment: value.environment, requestHost: "127.0.0.1", now })).state, "invalid");
    const alias = join(value.directory, "alias");
    await symlink(value.directory, alias);
    assert.equal((await readObservationView({ environment: { ...value.environment, RESEARCH_OBSERVATION_FILE: join(alias, "target.json") }, requestHost: "127.0.0.1", now })).state, "invalid");
  } finally { await value.cleanup(); }
});

test("oversized, malformed, and non-UTF8 files never become a last-known success", async () => {
  const value = await workspace();
  try {
    for (const contents of [Buffer.alloc(observationMaxBytes + 1, 32), Buffer.from("{}"), Buffer.from([0xff, 0xfe])]) {
      await writeFile(value.file, contents);
      const result = await readObservationView({ environment: value.environment, requestHost: "127.0.0.1", now });
      assert.equal(result.state, "invalid");
      assert.equal(result.data, null);
      assert.equal(JSON.stringify(result).includes(value.file), false);
    }
  } finally { await value.cleanup(); }
});

test("observation API is dynamic, nonmutating, uncached, and disabled without opt-in", async () => {
  const previous = process.env.RESEARCH_OBSERVATIONS_ENABLED;
  delete process.env.RESEARCH_OBSERVATIONS_ENABLED;
  try {
    const response = await observationRoute.GET(new Request("http://127.0.0.1/api/observations?file=/private/secret"));
    assert.equal(response.status, 403);
    assert.equal(response.headers.get("cache-control"), "no-store, max-age=0");
    const result = await response.json();
    assert.equal(result.authority, "none");
    assert.equal(result.production_ready, false);
    assert.equal(result.state, "disabled");
    assert.equal(result.data, null);
    assert.equal(JSON.stringify(result).includes("secret"), false);
    assert.equal(observationRoute.dynamic, "force-dynamic");
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) assert.equal(method in observationRoute, false);
  } finally {
    if (previous === undefined) delete process.env.RESEARCH_OBSERVATIONS_ENABLED;
    else process.env.RESEARCH_OBSERVATIONS_ENABLED = previous;
  }
});

test("enabled API accepts normalized NextRequest URLs only with an exact loopback Host", async () => {
  const value = await workspace();
  const keys = ["RESEARCH_OBSERVATIONS_ENABLED", "HOSTNAME", "RESEARCH_OBSERVATION_FILE"] as const;
  const previous = Object.fromEntries(keys.map((key) => [key, process.env[key]]));
  try {
    const input = fixture();
    input.generated_at = new Date().toISOString().replace(/\.\d{3}Z$/, "Z");
    input.runs[0].observed_at = input.generated_at;
    await writeFile(value.file, JSON.stringify(input));
    Object.assign(process.env, value.environment);
    const request = new NextRequest("http://127.0.0.1:3000/api/observations?file=/private/secret", {
      headers: { host: "127.0.0.1:3000", "x-forwarded-host": "foreign.example" },
    });
    // The real Next.js runtime normalizes the URL, but not the incoming Host.
    assert.equal(new URL(request.url).hostname, "localhost");
    const response = await observationRoute.GET(request);
    assert.equal(response.status, 200);
    const body = await response.json();
    assert.equal(body.state, "current");
    assert.equal(body.data.runs[0].query, input.runs[0].query);
    assert.equal(JSON.stringify(body).includes(value.directory), false);
    const deniedHeaders: ReadonlyArray<Record<string, string>> = [
      { host: "foreign.example" },
      { host: "foreign.example", "x-forwarded-host": "127.0.0.1:3000" },
      { host: "localhost:3000" },
      { "x-forwarded-host": "127.0.0.1:3000" },
      {},
    ];
    for (const headers of deniedHeaders) {
      const denied = await observationRoute.GET(new NextRequest("http://127.0.0.1:3000/api/observations", { headers }));
      assert.equal(denied.status, 403);
      const denial = await denied.json();
      assert.equal(denial.data, null);
      assert.equal(denial.reason, "loopback_required");
    }
    await writeFile(value.file, "invalid-json");
    const malformed = await observationRoute.GET(new NextRequest("http://127.0.0.1:3000/api/observations", { headers: { host: "127.0.0.1:3000" } }));
    assert.equal(malformed.status, 503);
    assert.equal((await malformed.json()).state, "invalid");
  } finally {
    for (const key of keys) {
      if (previous[key] === undefined) delete process.env[key];
      else process.env[key] = previous[key];
    }
    await value.cleanup();
  }
});
