import assert from "node:assert/strict";
import test from "node:test";

test("pinned SDK imports and exposes the runner entry points", async () => {
  const sdk = await import("@cursor/sdk");
  assert.equal(typeof sdk.Agent.prompt, "function");
  assert.equal(typeof sdk.CursorAgentError, "function");
});
