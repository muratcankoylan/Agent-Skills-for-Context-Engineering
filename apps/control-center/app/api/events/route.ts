import {
  FixtureReadError,
  InvalidEventCursorError,
  InvalidEventLimitError,
  paginateFixtureEvents,
  parseFixtureMode,
  readControlCenterFixture,
} from "../../../lib/fixture-adapter.ts";
import {
  DuplicateQueryParameterError,
  errorResponse,
  fixtureHeaders,
  readOptionalSingleSearchParam,
} from "../../../lib/http.ts";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export function GET(request: Request): Response {
  const url = new URL(request.url);

  try {
    const mode = parseFixtureMode(
      readOptionalSingleSearchParam(url.searchParams, "state"),
    );
    const result = readControlCenterFixture(mode);
    if (result.kind === "permission_denied") {
      return errorResponse(result.reasonCode, result.detail, 403);
    }

    const page = paginateFixtureEvents({
      after: readOptionalSingleSearchParam(url.searchParams, "after"),
      limit: readOptionalSingleSearchParam(url.searchParams, "limit"),
      events: result.data.events,
      identity: result.data.identity,
    });

    return Response.json(
      {
        schemaVersion: "control-center-event-page.v1",
        ...page,
        notice:
          "Finite fixture page. This endpoint is not SSE, a live watch, or canonical operational status.",
      },
      { headers: fixtureHeaders },
    );
  } catch (error) {
    if (
      error instanceof InvalidEventCursorError ||
      error instanceof InvalidEventLimitError ||
      error instanceof DuplicateQueryParameterError
    ) {
      return errorResponse(error.code, error.message, 400);
    }
    if (error instanceof FixtureReadError) {
      return errorResponse(error.code, error.message, 503);
    }
    throw error;
  }
}
