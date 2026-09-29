import assert from "node:assert/strict";
import test from "node:test";
import { readControlCenterFixture } from "../lib/fixture-adapter.ts";
import {
  buildOverviewViewModel,
  formatBytes,
  humanizeIdentifier,
  shortDigest,
} from "../lib/view-model.ts";

function snapshotFor(mode: "ready" | "empty" | "stale") {
  const result = readControlCenterFixture(mode);
  assert.equal(result.kind, "data");
  if (result.kind !== "data") throw new Error("Expected fixture data");
  return result.data;
}

test("overview fails closed while deployment ownership is inactive", () => {
  const view = buildOverviewViewModel(snapshotFor("ready"));

  assert.equal(view.operationalState, "preproduction_blocked");
  assert.equal(view.mutationCapability.enabled, false);
  assert.equal(view.mutationCapability.action, "activate_deployment");
  assert.ok(view.blockers.some((blocker) => blocker.id === "deployment-contract"));
});

test("stale status degrades rather than re-labeling last-known data as current", () => {
  const view = buildOverviewViewModel(snapshotFor("stale"));
  assert.equal(view.operationalState, "degraded");
  assert.match(view.summary, /stale/i);
});

test("empty view-model counts are zero while the deployment blocker remains", () => {
  const view = buildOverviewViewModel(snapshotFor("empty"));
  assert.equal(view.metrics.find((metric) => metric.label === "Open runs")?.value, "0");
  assert.equal(view.metrics.find((metric) => metric.label === "Review queue")?.value, "0");
  assert.ok(view.blockers.some((blocker) => blocker.id === "deployment-contract"));
});

test("display helpers are deterministic and bounded", () => {
  assert.equal(formatBytes(0), "0 B");
  assert.equal(formatBytes(1_024), "1.0 KiB");
  assert.equal(formatBytes(1_048_576), "1.0 MiB");
  assert.equal(formatBytes(-1), "Unknown");
  assert.equal(humanizeIdentifier("blocked_dependency"), "blocked dependency");
  assert.equal(
    shortDigest("sha256:1234567890abcdef"),
    "sha256:1234567890ab…",
  );
});
