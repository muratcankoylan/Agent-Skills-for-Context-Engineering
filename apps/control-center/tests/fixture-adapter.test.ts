import assert from "node:assert/strict";
import test from "node:test";
import {
  FixtureReadError,
  InvalidEventCursorError,
  InvalidEventLimitError,
  decodeEventCursor,
  encodeEventCursor,
  paginateFixtureEvents,
  parseFixtureMode,
  readControlCenterFixture,
} from "../lib/fixture-adapter.ts";

test("ready reads are isolated clones of the immutable fixture", () => {
  const first = readControlCenterFixture("ready");
  const second = readControlCenterFixture("ready");

  assert.equal(first.kind, "data");
  assert.equal(second.kind, "data");
  if (first.kind !== "data" || second.kind !== "data") return;

  assert.notStrictEqual(first.data, second.data);
  assert.deepEqual(first.data, second.data);
  assert.equal(first.data.identity.authority, "fixture_non_authoritative");
  assert.equal(first.data.repositoryAcceptance.state, "known");
  if (first.data.repositoryAcceptance.state === "known") {
    assert.match(first.data.repositoryAcceptance.value, /fabricated baseline fixture/);
  }
  assert.equal(first.data.deploymentPointer.state, "dependency_inactive");
  assert.deepEqual(
    {
      authoritative: first.data.readinessAssessment.authoritative,
      productionReady: first.data.readinessAssessment.productionReady,
      baselineCommit: first.data.readinessAssessment.baselineCommit,
      candidateState: first.data.readinessAssessment.candidateState,
      candidateCommit: first.data.readinessAssessment.candidateCommit,
    },
    {
      authoritative: false,
      productionReady: false,
      baselineCommit: "c6cd52017b247804373339e1c3c103d42554b0a1",
      candidateState: "uncommitted_worktree",
      candidateCommit: null,
    },
  );
});

test("fixture modes preserve empty, stale, permission, and error semantics", () => {
  const empty = readControlCenterFixture("empty");
  assert.equal(empty.kind, "data");
  if (empty.kind === "data") {
    assert.equal(empty.data.runs.length, 0);
    assert.equal(empty.data.reviewQueue.length, 0);
    assert.equal(empty.data.artifacts.length, 0);
    assert.equal(empty.data.events.length, 0);
    assert.equal(empty.data.identity.freshness.state, "unknown");
  }

  const stale = readControlCenterFixture("stale");
  assert.equal(stale.kind, "data");
  if (stale.kind === "data") {
    assert.equal(stale.data.identity.freshness.state, "stale");
  }

  const permission = readControlCenterFixture("permission");
  assert.deepEqual(permission, {
    kind: "permission_denied",
    reasonCode: "fixture_profile_forbidden",
    detail:
      "The selected fixture profile is outside this viewer's classification ceiling.",
  });

  assert.throws(() => readControlCenterFixture("error"), FixtureReadError);
});

test("unknown fixture scenarios fail into the deliberate error state", () => {
  assert.equal(parseFixtureMode(undefined), "ready");
  assert.equal(parseFixtureMode("stale"), "stale");
  assert.equal(parseFixtureMode("unexpected"), "error");
  assert.equal(parseFixtureMode(["ready", "stale"]), "error");
});

test("every declared mutation remains mechanically disabled", () => {
  const result = readControlCenterFixture("ready");
  assert.equal(result.kind, "data");
  if (result.kind !== "data") return;

  assert.equal(result.data.capabilities.length, 4);
  for (const capability of result.data.capabilities) {
    assert.equal(capability.enabled, false);
    assert.equal(capability.reasonCode, "dependency_inactive");
    assert.ok(capability.ownerSpecs.length > 0);
    assert.match(capability.reason, /grants no mutation authority/);
  }
});

test("event cursors round-trip only non-negative safe sequences", () => {
  assert.equal(encodeEventCursor(1_148), "cc-fixture-v1.1148");
  assert.equal(decodeEventCursor("cc-fixture-v1.1148"), 1_148);
  assert.throws(() => encodeEventCursor(-1), InvalidEventCursorError);
  assert.throws(
    () => decodeEventCursor("cc-fixture-v2.1148"),
    InvalidEventCursorError,
  );
  assert.throws(
    () => decodeEventCursor("cc-fixture-v1.001148"),
    InvalidEventCursorError,
  );
});

test("event pagination is strictly after-cursor, bounded, and finite", () => {
  const first = paginateFixtureEvents({ limit: 3 });
  assert.deepEqual(
    first.events.map((event) => event.sequence),
    [1_141, 1_142, 1_143],
  );
  assert.equal(first.afterCursor, "cc-fixture-v1.0");
  assert.equal(first.nextCursor, "cc-fixture-v1.1143");
  assert.equal(first.hasMore, true);
  assert.equal(first.endOfFixture, false);
  assert.equal(first.streamMode, "finite_fixture_page");

  const second = paginateFixtureEvents({ after: first.nextCursor, limit: 50 });
  assert.deepEqual(
    second.events.map((event) => event.sequence),
    [1_144, 1_145, 1_146, 1_147, 1_148],
  );
  assert.equal(second.nextCursor, "cc-fixture-v1.1148");
  assert.equal(second.hasMore, false);
  assert.equal(second.endOfFixture, true);

  const terminal = paginateFixtureEvents({ after: second.nextCursor });
  assert.equal(terminal.events.length, 0);
  assert.equal(terminal.nextCursor, second.nextCursor);
  assert.equal(terminal.endOfFixture, true);
});

test("event pagination rejects forged cursors and unbounded limits", () => {
  assert.throws(
    () => paginateFixtureEvents({ after: "cc-fixture-v1.1140" }),
    InvalidEventCursorError,
  );
  assert.throws(
    () => paginateFixtureEvents({ after: "cc-fixture-v1.9999" }),
    InvalidEventCursorError,
  );
  assert.throws(() => paginateFixtureEvents({ limit: 0 }), InvalidEventLimitError);
  assert.throws(
    () => paginateFixtureEvents({ limit: "51" }),
    InvalidEventLimitError,
  );
  assert.throws(
    () => paginateFixtureEvents({ limit: "3.5" }),
    InvalidEventLimitError,
  );
});

test("empty fixture pagination terminates without fabricating an event", () => {
  const empty = readControlCenterFixture("empty");
  assert.equal(empty.kind, "data");
  if (empty.kind !== "data") return;
  const page = paginateFixtureEvents({
    events: [],
    identity: empty.data.identity,
    limit: 5,
  });
  assert.deepEqual(page.events, []);
  assert.equal(page.nextCursor, "cc-fixture-v1.0");
  assert.equal(page.endOfFixture, true);
  assert.equal(page.freshness.state, "unknown");
  assert.equal(page.asOfObservationId, empty.data.identity.asOfObservationId);
});
