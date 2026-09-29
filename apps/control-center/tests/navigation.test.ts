import assert from "node:assert/strict";
import test from "node:test";
import { isCurrentRoute, primaryNavigation } from "../lib/navigation.ts";

test("primary navigation declares unique destinations", () => {
  assert.equal(new Set(primaryNavigation.map((item) => item.href)).size, 7);
  assert.equal(primaryNavigation[0].href, "/");
  assert.equal(primaryNavigation.at(-1)?.href, "/service");
});

test("current-route matching is exact at the root and nested elsewhere", () => {
  assert.equal(isCurrentRoute("/", "/"), true);
  assert.equal(isCurrentRoute("/runs", "/"), false);
  assert.equal(isCurrentRoute("/runs", "/runs"), true);
  assert.equal(isCurrentRoute("/runs/example", "/runs"), true);
  assert.equal(isCurrentRoute("/runner", "/runs"), false);
});
