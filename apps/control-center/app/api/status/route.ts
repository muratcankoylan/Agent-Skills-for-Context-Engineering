import {
  FixtureReadError,
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

    return Response.json(
      {
        schemaVersion: "control-center-status.v1",
        authority: "fixture_non_authoritative",
        fixture: {
          finite: true,
          live: false,
          mutationCapable: false,
        },
        status: result.data,
      },
      { headers: fixtureHeaders },
    );
  } catch (error) {
    if (error instanceof DuplicateQueryParameterError) {
      return errorResponse(error.code, error.message, 400);
    }
    if (error instanceof FixtureReadError) {
      return errorResponse(error.code, error.message, 503);
    }
    throw error;
  }
}
