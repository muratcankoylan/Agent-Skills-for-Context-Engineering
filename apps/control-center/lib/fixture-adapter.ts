import type {
  AdapterResult,
  ControlCenterEvent,
  ControlCenterSnapshot,
  EventPage,
  FixtureMode,
  MutationCapability,
  SnapshotIdentity,
} from "./domain.ts";
import { controlCenterFixture } from "./fixtures.ts";

const cursorPrefix = "cc-fixture-v1";
const cursorPattern = /^cc-fixture-v1\.(0|[1-9][0-9]{0,15})$/;
const fixtureModes = new Set<FixtureMode>([
  "ready",
  "empty",
  "stale",
  "error",
  "permission",
]);

export class FixtureReadError extends Error {
  readonly code = "fixture_read_failed";

  constructor() {
    super("The requested fixture scenario deliberately failed.");
    this.name = "FixtureReadError";
  }
}

export class InvalidEventCursorError extends Error {
  readonly code = "invalid_event_cursor";

  constructor(message: string) {
    super(message);
    this.name = "InvalidEventCursorError";
  }
}

export class InvalidEventLimitError extends Error {
  readonly code = "invalid_event_limit";

  constructor(message: string) {
    super(message);
    this.name = "InvalidEventLimitError";
  }
}

export function parseFixtureMode(
  value: string | readonly string[] | undefined,
): FixtureMode {
  if (value === undefined) {
    return "ready";
  }

  if (typeof value === "string" && fixtureModes.has(value as FixtureMode)) {
    return value as FixtureMode;
  }

  return "error";
}

function cloneFixture(): ControlCenterSnapshot {
  return structuredClone(controlCenterFixture) as ControlCenterSnapshot;
}

function emptyFixture(): ControlCenterSnapshot {
  const snapshot = cloneFixture();

  return {
    ...snapshot,
    identity: {
      ...snapshot.identity,
      freshness: {
        state: "unknown",
        reasonCode: "fixture_has_no_observation",
        detail: "The empty scenario contains no status observation.",
      },
    },
    health: [
      {
        id: "fixture",
        label: "Fixture data",
        value: "Empty",
        tone: "neutral",
        detail: "No operational records matched this preview scenario.",
      },
    ],
    runs: [],
    reviewQueue: [],
    artifacts: [],
    events: [],
  };
}

function staleFixture(): ControlCenterSnapshot {
  const snapshot = cloneFixture();

  return {
    ...snapshot,
    identity: {
      ...snapshot.identity,
      freshness: {
        state: "stale",
        observedAt: "2026-08-22T18:45:00Z",
        reasonCode: "fixture_observation_expired",
        detail:
          "The last fixture observation is outside its declared freshness window. Values remain visible but must not drive a decision.",
      },
    },
    health: snapshot.health.map((signal) =>
      signal.id === "repository"
        ? {
            ...signal,
            value: "Last known",
            tone: "warning",
            detail: "Repository status is stale in this preview scenario.",
          }
        : signal,
    ),
  };
}

export function readControlCenterFixture(
  mode: FixtureMode = "ready",
): AdapterResult<ControlCenterSnapshot> {
  if (mode === "error") {
    throw new FixtureReadError();
  }

  if (mode === "permission") {
    return {
      kind: "permission_denied",
      reasonCode: "fixture_profile_forbidden",
      detail:
        "The selected fixture profile is outside this viewer's classification ceiling.",
    };
  }

  if (mode === "empty") {
    return { kind: "data", data: emptyFixture() };
  }

  if (mode === "stale") {
    return { kind: "data", data: staleFixture() };
  }

  return { kind: "data", data: cloneFixture() };
}

export function getMutationCapability(
  snapshot: ControlCenterSnapshot,
  action: MutationCapability["action"],
): MutationCapability {
  const capability = snapshot.capabilities.find(
    (candidate) => candidate.action === action,
  );

  if (capability === undefined) {
    throw new Error(`Missing fail-closed capability declaration for ${action}`);
  }

  return capability;
}

export function encodeEventCursor(sequence: number): string {
  if (!Number.isSafeInteger(sequence) || sequence < 0) {
    throw new InvalidEventCursorError(
      "Event cursor sequence must be a non-negative safe integer.",
    );
  }

  return `${cursorPrefix}.${sequence}`;
}

export function decodeEventCursor(cursor: string): number {
  const match = cursorPattern.exec(cursor);
  if (match === null) {
    throw new InvalidEventCursorError(
      "Cursor must use the cc-fixture-v1.<sequence> format.",
    );
  }

  const sequence = Number.parseInt(match[1], 10);
  if (!Number.isSafeInteger(sequence)) {
    throw new InvalidEventCursorError("Cursor sequence is outside the safe range.");
  }

  return sequence;
}

function parseEventLimit(limit: string | number | undefined): number {
  if (limit === undefined) {
    return 20;
  }

  const parsed = typeof limit === "number" ? limit : Number(limit);
  if (!Number.isSafeInteger(parsed) || parsed < 1 || parsed > 50) {
    throw new InvalidEventLimitError(
      "Event page limit must be an integer between 1 and 50.",
    );
  }

  return parsed;
}

function assertCursorBelongsToFixture(
  afterSequence: number,
  events: readonly ControlCenterEvent[],
): void {
  if (afterSequence === 0) {
    return;
  }

  const known = events.some((event) => event.sequence === afterSequence);
  if (!known) {
    throw new InvalidEventCursorError(
      "Cursor does not identify an event in this finite fixture.",
    );
  }
}

export function paginateFixtureEvents(options: {
  readonly after?: string;
  readonly limit?: string | number;
  readonly events?: readonly ControlCenterEvent[];
  readonly identity?: SnapshotIdentity;
} = {}): EventPage {
  const events = options.events ?? controlCenterFixture.events;
  const identity = options.identity ?? controlCenterFixture.identity;
  const afterCursor = options.after ?? encodeEventCursor(0);
  const afterSequence = decodeEventCursor(afterCursor);
  const limit = parseEventLimit(options.limit);

  assertCursorBelongsToFixture(afterSequence, events);

  const remaining = events.filter((event) => event.sequence > afterSequence);
  const pageEvents = remaining.slice(0, limit);
  const nextSequence = pageEvents.at(-1)?.sequence ?? afterSequence;
  const hasMore = remaining.length > pageEvents.length;

  return {
    fixtureId: identity.fixtureId,
    authority: identity.authority,
    sourceSequence: identity.sourceSequence,
    asOfObservationId: identity.asOfObservationId,
    asOf: identity.asOf,
    freshness: identity.freshness,
    events: pageEvents,
    afterCursor,
    nextCursor: encodeEventCursor(nextSequence),
    hasMore,
    endOfFixture: !hasMore,
    streamMode: "finite_fixture_page",
  };
}
