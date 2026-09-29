import assert from "node:assert/strict";
import test from "node:test";
import * as eventsRoute from "../app/api/events/route.ts";
import * as statusRoute from "../app/api/status/route.ts";

test("status endpoint is an explicitly non-authoritative finite fixture", async () => {
  const response = statusRoute.GET(new Request("http://control.test/api/status"));
  const body = await response.json();

  assert.equal(response.status, 200);
  assert.equal(
    response.headers.get("x-control-center-authority"),
    "fixture-non-authoritative",
  );
  assert.equal(response.headers.get("cache-control"), "no-store, max-age=0");
  assert.equal(body.authority, "fixture_non_authoritative");
  assert.deepEqual(body.fixture, {
    finite: true,
    live: false,
    mutationCapable: false,
  });
});

test("status endpoint preserves permission and error states", async () => {
  const denied = statusRoute.GET(
    new Request("http://control.test/api/status?state=permission"),
  );
  assert.equal(denied.status, 403);
  assert.equal((await denied.json()).error.code, "fixture_profile_forbidden");

  const failed = statusRoute.GET(
    new Request("http://control.test/api/status?state=error"),
  );
  assert.equal(failed.status, 503);
  assert.equal((await failed.json()).error.code, "fixture_read_failed");
});

test("status endpoint rejects repeated state keys", async () => {
  const response = statusRoute.GET(
    new Request("http://control.test/api/status?state=ready&state=ready"),
  );
  assert.equal(response.status, 400);
  const body = await response.json();
  assert.equal(body.error.code, "duplicate_query_parameter");
  assert.match(body.error.message, /state/);
});

test("events endpoint exposes cursor-paged JSON, never a live stream", async () => {
  const firstResponse = eventsRoute.GET(
    new Request("http://control.test/api/events?limit=2"),
  );
  const first = await firstResponse.json();

  assert.equal(firstResponse.status, 200);
  assert.equal(
    firstResponse.headers.get("x-control-center-stream"),
    "finite-json-page-not-live",
  );
  assert.equal(first.streamMode, "finite_fixture_page");
  assert.equal(first.events.length, 2);
  assert.equal(first.hasMore, true);
  assert.match(first.notice, /not SSE/);

  const secondResponse = eventsRoute.GET(
    new Request(
      `http://control.test/api/events?limit=2&after=${encodeURIComponent(first.nextCursor)}`,
    ),
  );
  const second = await secondResponse.json();
  assert.equal(second.events[0].sequence, first.events[1].sequence + 1);
});

test("events endpoint rejects malformed pagination and supports empty state", async () => {
  const invalidCursor = eventsRoute.GET(
    new Request("http://control.test/api/events?after=latest"),
  );
  assert.equal(invalidCursor.status, 400);
  assert.equal((await invalidCursor.json()).error.code, "invalid_event_cursor");

  const invalidLimit = eventsRoute.GET(
    new Request("http://control.test/api/events?limit=5000"),
  );
  assert.equal(invalidLimit.status, 400);
  assert.equal((await invalidLimit.json()).error.code, "invalid_event_limit");

  const empty = eventsRoute.GET(
    new Request("http://control.test/api/events?state=empty"),
  );
  const body = await empty.json();
  assert.equal(empty.status, 200);
  assert.deepEqual(body.events, []);
  assert.equal(body.endOfFixture, true);
  assert.equal(body.freshness.state, "unknown");
  assert.equal(body.asOf, "2026-08-24T18:45:00Z");
});

test("events pages carry the selected snapshot freshness and identity", async () => {
  const readyResponse = eventsRoute.GET(
    new Request("http://control.test/api/events?state=ready&limit=1"),
  );
  const staleResponse = eventsRoute.GET(
    new Request("http://control.test/api/events?state=stale&limit=1"),
  );
  const ready = await readyResponse.json();
  const stale = await staleResponse.json();

  assert.equal(readyResponse.status, 200);
  assert.equal(staleResponse.status, 200);
  assert.equal(ready.fixtureId, "control-center-fixture-v1");
  assert.equal(ready.authority, "fixture_non_authoritative");
  assert.equal(ready.sourceSequence, 1_148);
  assert.equal(ready.asOfObservationId, "clock-observation-fixture-20260824t184500z");
  assert.equal(ready.asOf, "2026-08-24T18:45:00Z");
  assert.equal(ready.freshness.state, "current");
  assert.equal(stale.freshness.state, "stale");
  assert.equal(stale.freshness.observedAt, "2026-08-22T18:45:00Z");
  assert.notDeepEqual(stale, ready);
});

test("events endpoint rejects every repeated supported query key", async () => {
  for (const query of [
    "state=ready&state=stale",
    "limit=2&limit=2",
    "after=cc-fixture-v1.1141&after=cc-fixture-v1.1141",
  ]) {
    const response = eventsRoute.GET(
      new Request(`http://control.test/api/events?${query}`),
    );
    assert.equal(response.status, 400, query);
    assert.equal((await response.json()).error.code, "duplicate_query_parameter");
  }
});

test("route modules export no mutating HTTP methods", () => {
  const forbiddenMethods = ["POST", "PUT", "PATCH", "DELETE"];
  for (const method of forbiddenMethods) {
    assert.equal(method in statusRoute, false, `status route exports ${method}`);
    assert.equal(method in eventsRoute, false, `events route exports ${method}`);
  }
});
