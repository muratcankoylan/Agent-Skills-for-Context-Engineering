import assert from "node:assert/strict";
import { spawn } from "node:child_process";
import net from "node:net";
import { dirname, resolve } from "node:path";
import { fileURLToPath } from "node:url";

const applicationRoot = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const npmCommand = process.platform === "win32" ? "npm.cmd" : "npm";
const maxCapturedOutput = 32_768;
const startupTimeoutMs = 20_000;

function reserveEphemeralPort() {
  return new Promise((resolvePort, reject) => {
    const server = net.createServer();
    server.unref();
    server.once("error", reject);
    server.listen(0, "127.0.0.1", () => {
      const address = server.address();
      if (address === null || typeof address === "string") {
        server.close(() => reject(new Error("Could not reserve an IPv4 port.")));
        return;
      }
      server.close((error) => {
        if (error) reject(error);
        else resolvePort(address.port);
      });
    });
  });
}

function appendBounded(current, chunk) {
  const combined = current + chunk.toString();
  return combined.slice(-maxCapturedOutput);
}

function delay(milliseconds) {
  return new Promise((resolveDelay) => setTimeout(resolveDelay, milliseconds));
}

async function waitForReady(url, child, readOutput) {
  const deadline = Date.now() + startupTimeoutMs;
  while (Date.now() < deadline) {
    if (child.exitCode !== null) {
      throw new Error(
        `Standalone server exited with ${child.exitCode} before readiness.\n${readOutput()}`,
      );
    }
    try {
      const response = await fetch(`${url}/api/status`, {
        signal: AbortSignal.timeout(1_000),
      });
      if (response.ok) return;
    } catch {
      // The process may still be binding its socket.
    }
    await delay(100);
  }
  throw new Error(`Standalone server did not become ready.\n${readOutput()}`);
}

function extractAssetPaths(html) {
  return new Set(
    [...html.matchAll(/(?:href|src)="([^"?#]*\/_next\/static\/[^"?#]+)"/g)].map(
      (match) => match[1],
    ),
  );
}

function assertLandmarkReferencesResolve(html) {
  for (const match of html.matchAll(/aria-labelledby="([^"]+)"/g)) {
    for (const id of match[1].split(/\s+/)) {
      assert.match(html, new RegExp(`id="${id}"`), `missing landmark label #${id}`);
    }
  }
}

async function stopProcessTree(child) {
  if (child.exitCode !== null) return;

  if (process.platform !== "win32" && child.pid !== undefined) {
    try {
      process.kill(-child.pid, "SIGTERM");
    } catch {
      child.kill("SIGTERM");
    }
  } else {
    child.kill("SIGTERM");
  }

  const exited = await Promise.race([
    new Promise((resolveExit) => child.once("exit", () => resolveExit(true))),
    delay(3_000).then(() => false),
  ]);
  if (!exited && child.exitCode === null) {
    if (process.platform !== "win32" && child.pid !== undefined) {
      try {
        process.kill(-child.pid, "SIGKILL");
      } catch {
        child.kill("SIGKILL");
      }
    } else {
      child.kill("SIGKILL");
    }
  }
}

const port = await reserveEphemeralPort();
const baseUrl = `http://127.0.0.1:${port}`;
let stdout = "";
let stderr = "";
const server = spawn(npmCommand, ["run", "--silent", "start"], {
  cwd: applicationRoot,
  detached: process.platform !== "win32",
  env: {
    ...process.env,
    HOSTNAME: "127.0.0.1",
    NODE_ENV: "production",
    NEXT_TELEMETRY_DISABLED: "1",
    PORT: String(port),
  },
  stdio: ["ignore", "pipe", "pipe"],
});
server.stdout.on("data", (chunk) => {
  stdout = appendBounded(stdout, chunk);
});
server.stderr.on("data", (chunk) => {
  stderr = appendBounded(stderr, chunk);
});
const readOutput = () => `${stdout}\n${stderr}`.trim();

try {
  await waitForReady(baseUrl, server, readOutput);

  const homeResponse = await fetch(`${baseUrl}/`);
  const homeHtml = await homeResponse.text();
  assert.equal(homeResponse.status, 200);
  assert.match(homeResponse.headers.get("content-type") ?? "", /text\/html/);
  assert.match(homeHtml, /Agent Research Control Center/);
  assertLandmarkReferencesResolve(homeHtml);

  const csp = homeResponse.headers.get("content-security-policy") ?? "";
  assert.match(csp, /script-src [^;]*'nonce-([A-Za-z0-9_-]+)'/);
  assert.match(csp, /'strict-dynamic'/);
  assert.match(csp, /style-src-attr 'none'/);
  assert.doesNotMatch(csp, /'unsafe-inline'|'unsafe-eval'/);
  const nonce = csp.match(/'nonce-([A-Za-z0-9_-]+)'/)?.[1];
  assert.ok(nonce);
  const scriptTags = [...homeHtml.matchAll(/<script\b[^>]*>/g)].map(
    (match) => match[0],
  );
  assert.ok(scriptTags.length > 0, "expected Next.js script tags");
  for (const scriptTag of scriptTags) {
    assert.match(scriptTag, new RegExp(`nonce="${nonce}"`));
  }

  const assets = extractAssetPaths(homeHtml);
  assert.ok([...assets].some((asset) => asset.endsWith(".css")));
  assert.ok([...assets].some((asset) => asset.endsWith(".js")));
  for (const asset of assets) {
    const response = await fetch(new URL(asset, baseUrl));
    assert.equal(response.status, 200, `asset failed: ${asset}`);
    const body = await response.arrayBuffer();
    assert.ok(body.byteLength > 0, `asset was empty: ${asset}`);
    const contentType = response.headers.get("content-type") ?? "";
    if (asset.endsWith(".css")) assert.match(contentType, /text\/css/);
    if (asset.endsWith(".js")) assert.match(contentType, /javascript/);
  }

  const publicAssetResponse = await fetch(`${baseUrl}/runtime-smoke.txt`);
  assert.equal(publicAssetResponse.status, 200);
  assert.equal(
    (await publicAssetResponse.text()).trim(),
    "control-center-standalone-public-asset-v1",
  );

  const runsResponse = await fetch(`${baseUrl}/runs`);
  const runsHtml = await runsResponse.text();
  assert.equal(runsResponse.status, 200);
  assert.equal((runsHtml.match(/aria-current="page"/g) ?? []).length, 1);
  assert.match(
    runsHtml,
    /<a(?=[^>]*aria-current="page")(?=[^>]*href="\/runs")[^>]*>/,
  );
  assertLandmarkReferencesResolve(runsHtml);

  const apiResponse = await fetch(`${baseUrl}/api/status`);
  assert.equal(apiResponse.status, 200);
  assert.match(
    apiResponse.headers.get("content-security-policy") ?? "",
    /default-src 'none'/,
  );

  const duplicateStatusResponse = await fetch(
    `${baseUrl}/api/status?state=ready&state=ready`,
  );
  assert.equal(duplicateStatusResponse.status, 400);
  assert.equal(
    (await duplicateStatusResponse.json()).error.code,
    "duplicate_query_parameter",
  );

  const duplicateEventsResponse = await fetch(
    `${baseUrl}/api/events?limit=1&limit=1`,
  );
  assert.equal(duplicateEventsResponse.status, 400);
  assert.equal(
    (await duplicateEventsResponse.json()).error.code,
    "duplicate_query_parameter",
  );

  const eventSequences = [];
  let eventUrl = `${baseUrl}/api/events?state=stale&limit=3`;
  for (let pageNumber = 0; pageNumber < 10; pageNumber += 1) {
    const response = await fetch(eventUrl);
    assert.equal(response.status, 200);
    const page = await response.json();
    assert.equal(page.freshness.state, "stale");
    assert.equal(page.asOfObservationId, "clock-observation-fixture-20260824t184500z");
    eventSequences.push(...page.events.map((event) => event.sequence));
    if (page.endOfFixture) {
      assert.equal(page.hasMore, false);
      break;
    }
    assert.equal(page.hasMore, true);
    eventUrl = `${baseUrl}/api/events?state=stale&limit=3&after=${encodeURIComponent(page.nextCursor)}`;
  }
  assert.deepEqual(eventSequences, [1_141, 1_142, 1_143, 1_144, 1_145, 1_146, 1_147, 1_148]);

  for (const endpoint of ["/api/status", "/api/events"]) {
    for (const method of ["POST", "PUT", "PATCH", "DELETE"]) {
      const response = await fetch(`${baseUrl}${endpoint}`, { method });
      assert.equal(response.status, 405, `${method} ${endpoint}`);
    }
  }

  process.stdout.write(
    `Standalone runtime smoke passed on ${baseUrl} with ${assets.size} static assets.\n`,
  );
} finally {
  await stopProcessTree(server);
}
