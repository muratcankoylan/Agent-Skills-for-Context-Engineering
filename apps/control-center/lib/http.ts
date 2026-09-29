import type { ApiError } from "./domain.ts";

export const fixtureHeaders = {
  "Cache-Control": "no-store, max-age=0",
  "X-Content-Type-Options": "nosniff",
  "X-Control-Center-Authority": "fixture-non-authoritative",
  "X-Control-Center-Stream": "finite-json-page-not-live",
} as const;

export class DuplicateQueryParameterError extends Error {
  readonly code = "duplicate_query_parameter";
  readonly parameter: string;

  constructor(parameter: string) {
    super(`Query parameter "${parameter}" must appear at most once.`);
    this.name = "DuplicateQueryParameterError";
    this.parameter = parameter;
  }
}

export function readOptionalSingleSearchParam(
  searchParams: URLSearchParams,
  parameter: string,
): string | undefined {
  const values = searchParams.getAll(parameter);
  if (values.length > 1) {
    throw new DuplicateQueryParameterError(parameter);
  }
  return values[0];
}

export function errorResponse(
  code: string,
  message: string,
  status: number,
): Response {
  const body: ApiError = { error: { code, message } };
  return Response.json(body, { status, headers: fixtureHeaders });
}
