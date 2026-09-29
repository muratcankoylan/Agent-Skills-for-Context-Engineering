import assert from "node:assert/strict";
import test from "node:test";
import { parseServiceStatus, readServiceStatus, serviceMaxBytes, serviceTimeoutMs } from "../lib/service-reader.server.ts";

const token = "fixture-" + "s".repeat(40);
const now = Date.parse("2026-09-10T22:00:00Z");
const environment = { RESEARCH_SERVICE_ENABLED: "1", HOSTNAME: "127.0.0.1",
  RESEARCH_SERVICE_URL: "http://127.0.0.1:8787", RESEARCH_OPERATOR_TOKEN: token };

function fixture() {
  return { schema: "research-service-status/v1", production_ready: false, paused: false,
    jobs: [{ id: "api:fixture-job", status: "queued", created: 1789077500, updated: 1789077500, reason: null as string | null }],
    usage: [{ day: "2026-09-10", model_calls: 5, reserved_microusd: 12000, source_request_reservations: 1 }], last_event: 19 };
}

function response(body = JSON.stringify(fixture()), headers: Record<string, string> = {}) {
  return new Response(body, { status: 200, headers: { "content-type": "application/json", ...headers } });
}

function read(fetcher: typeof fetch, overrides: Record<string, string | undefined> = {}) {
  return readServiceStatus({ environment: { ...environment, ...overrides }, requestHost: "127.0.0.1:3000", now, fetcher });
}

test("retrieval completion is a valid status, not an acceptance or production claim", async () => {
  const input = fixture();
  input.jobs[0].status = "retrieval_complete";
  const result = await read(async () => response(JSON.stringify(input)));
  assert.equal(result.state, "current");
  assert.equal(result.data?.jobs[0].status, "retrieval_complete");
  assert.equal(result.data?.production_ready, false);
});

test("bounded model completion is visible without implying publication", async () => {
  const input = fixture();
  input.jobs[0].status = "execution_complete";
  const result = await read(async () => response(JSON.stringify(input)));
  assert.equal(result.state, "current");
  assert.equal(result.data?.jobs[0].status, "execution_complete");
  assert.equal(result.data?.production_ready, false);
});

test("service opt-in and loopback checks occur before any request", async () => {
  let calls = 0;
  const fetcher: typeof fetch = async () => { calls++; throw new Error("must not fetch"); };
  for (const overrides of [
    { RESEARCH_SERVICE_ENABLED: undefined }, { RESEARCH_SERVICE_ENABLED: "true" },
    { HOSTNAME: "0.0.0.0" }, { HOSTNAME: "localhost" },
  ]) {
    const result = await read(fetcher, overrides);
    assert.equal(result.state, "disabled");
    assert.equal(result.data, null);
  }
  for (const requestHost of [null, "localhost", "external.example", "127.0.0.1.evil", "127.0.0.1@evil", "127.0.0.1:0", "127.0.0.1:65536"]) {
    const result = await readServiceStatus({ environment, requestHost, fetcher, now });
    assert.equal(result.reason, "loopback_required");
  }
  assert.equal(calls, 0);
});

test("only the exact configured endpoint can receive an operator credential", async () => {
  let calls = 0;
  const fetcher: typeof fetch = async () => { calls++; return response(); };
  for (const endpoint of ["https://evil.test", "http://localhost:8787", "http://127.0.0.1:8788", "http://127.0.0.1:8787/",
    "http://127.0.0.1:8787@evil.test", "http://127.0.0.1:8787?secret=" + token]) {
    const result = await read(fetcher, { RESEARCH_SERVICE_URL: endpoint });
    assert.equal(result.reason, "service_endpoint_not_allowed");
    assert.equal(JSON.stringify(result).includes(token), false);
    assert.equal(JSON.stringify(result).includes(endpoint), false);
  }
  for (const operatorToken of ["short", "a".repeat(300), "x".repeat(32) + "\nAuthorization: other"]) {
    assert.equal((await read(fetcher, { RESEARCH_OPERATOR_TOKEN: operatorToken })).reason, "operator_credential_invalid");
  }
  assert.equal((await read(fetcher, { RESEARCH_OPERATOR_TOKEN: undefined })).state, "missing");
  assert.equal((await read(fetcher, { RESEARCH_SERVICE_URL: undefined })).state, "missing");
  assert.equal(calls, 0);
});

test("native status read is GET-only, noncached, bounded, and token is server-only", async () => {
  let calls = 0;
  const fetcher: typeof fetch = async (input, init) => {
    calls++;
    assert.equal(input, "http://127.0.0.1:8787/v1/status");
    assert.equal(init?.method, "GET");
    assert.equal(init?.cache, "no-store");
    assert.equal(init?.redirect, "error");
    assert.equal(new Headers(init?.headers).get("authorization"), "Bearer " + token);
    assert.equal(new Headers(init?.headers).get("origin"), null);
    assert.ok(init?.signal instanceof AbortSignal);
    return response();
  };
  const result = await read(fetcher);
  assert.equal(result.state, "current");
  assert.deepEqual(result.data, fixture());
  assert.equal(result.checked_at, new Date(now).toISOString());
  assert.equal(JSON.stringify(result).includes(token), false);
  assert.equal(calls, 1);
});

test("authorization and transport errors never expose remote bodies or exception text", async () => {
  for (const status of [301, 302, 307, 401, 403, 500]) {
    const result = await read(async () => new Response(token + " private error body", { status }));
    assert.equal(result.state, "unavailable");
    assert.equal(result.reason, "service_request_rejected");
    assert.equal(JSON.stringify(result).includes(token), false);
    assert.equal(result.data, null);
  }
  const result = await read(async () => { throw new Error(token + " private exception"); });
  assert.equal(result.reason, "service_read_failed");
  assert.equal(JSON.stringify(result).includes(token), false);
});

test("read expires after five seconds without a last-known-good fallback", async () => {
  const fetcher: typeof fetch = async (_input, init) => new Promise((_resolve, reject) => {
    init?.signal?.addEventListener("abort", () => reject(new Error(token + " delayed")), { once: true });
  });
  assert.equal(serviceTimeoutMs, 5000);
  const result = await read(fetcher);
  assert.equal(result.state, "unavailable");
  assert.equal(result.reason, "service_timeout");
  assert.equal(result.data, null);
  assert.equal(JSON.stringify(result).includes(token), false);
});

test("response media type, encoding, UTF8 and declared length are validated", async () => {
  const invalid = [
    response("{}", { "content-type": "text/html" }),
    response("{}", { "content-encoding": "gzip" }),
    response("{}", { "content-length": String(serviceMaxBytes + 1) }),
    response("{}", { "content-length": "NaN" }),
    response(JSON.stringify(fixture()), { "content-length": "2" }),
    new Response(new Uint8Array([0xff]), { headers: { "content-type": "application/json" } }),
  ];
  for (const output of invalid) {
    const result = await read(async () => output);
    assert.equal(result.state, "invalid");
    assert.equal(result.data, null);
  }
});

test("streaming byte cap cancels oversized responses without reading to completion", async () => {
  let cancelled = false;
  const stream = new ReadableStream<Uint8Array>({
    start(controller) { controller.enqueue(new Uint8Array(serviceMaxBytes + 1)); },
    cancel() { cancelled = true; },
  });
  const result = await read(async () => new Response(stream, { headers: { "content-type": "application/json" } }));
  assert.equal(result.reason, "service_response_too_large");
  assert.equal(result.data, null);
  assert.equal(cancelled, true);
});

test("reader refuses reflected credentials, including JSON-escaped reflections", async () => {
  const input = fixture();
  input.jobs[0].id = token;
  const serialized = JSON.stringify(input);
  for (const text of [serialized, serialized.replace(token, token.replaceAll("s", "\\u0073"))]) {
    const result = await read(async () => response(text));
    assert.equal(result.reason, "service_response_invalid");
    assert.equal(result.data, null);
    assert.equal(JSON.stringify(result).includes(token), false);
  }
});

test("status schema rejects unknown fields, duplicate keys, authority changes and invalid rows", () => {
  const baseline = JSON.stringify(fixture());
  for (const text of ["{}", "[]", baseline + " trailing", baseline.replace('"paused":false', '"paused":true,"paused":false'),
    baseline.replace('"production_ready":false', '"production_ready":true'),
    baseline.replace('"model_calls":5', '"model_calls":NaN'), "[".repeat(1000) + "]".repeat(1000)]) {
    assert.throws(() => parseServiceStatus(text));
  }
  const mutations: ((input: Record<string, any>) => void)[] = [
    (input) => { input.extra = "private"; },
    (input) => { input.jobs[0].status = "merged"; },
    (input) => { input.jobs[0].reason = "/private/key.txt"; },
    (input) => { input.jobs[0].id = "<script>alert(1)</script>"; },
    (input) => { input.jobs[0].created = 1.2; },
    (input) => { input.jobs[0].updated = input.jobs[0].created - 1; },
    (input) => { input.jobs[0].updated = Number.MAX_SAFE_INTEGER; },
    (input) => { input.usage[0].model_calls = "5"; },
    (input) => { input.usage[0].reserved_microusd = -1; },
    (input) => { input.usage[0].source_request_reservations = false; },
    (input) => { input.usage[0].day = "2026-02-30"; },
    (input) => { input.last_event = Number.MAX_SAFE_INTEGER + 1; },
    (input) => { input.jobs.push(input.jobs[0]); },
    (input) => { input.usage.push(input.usage[0]); },
    (input) => { input.jobs = Array(101).fill(input.jobs[0]); },
    (input) => { input.usage = Array(8).fill(input.usage[0]); },
  ];
  for (const mutate of mutations) {
    const input = fixture();
    mutate(input);
    assert.throws(() => parseServiceStatus(JSON.stringify(input)));
  }
});

test("empty status and explicit pause/reconciliation are retained as real service data", async () => {
  const empty = { ...fixture(), jobs: [], usage: [], last_event: 0 };
  assert.deepEqual(parseServiceStatus(JSON.stringify(empty)), empty);
  const input = fixture();
  input.paused = true;
  input.jobs[0].status = "reconciliation_required";
  input.jobs[0].reason = "PROCESS_INTERRUPTED";
  const result = await read(async () => response(JSON.stringify(input)));
  assert.deepEqual(result.data, input);
  const failedNext = await read(async () => { throw new Error("unavailable now"); });
  assert.equal(failedNext.data, null);
});
