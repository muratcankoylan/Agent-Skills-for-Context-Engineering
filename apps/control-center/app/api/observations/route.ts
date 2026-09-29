import { readObservationView } from "../../../lib/observation-reader.server.ts";

export const dynamic = "force-dynamic";
export const runtime = "nodejs";

export async function GET(request: Request): Promise<Response> {
  // NextRequest normalizes loopback URL hostnames to localhost. Require the
  // incoming Host instead; missing and forwarded hosts never grant access.
  const result = await readObservationView({
    requestHost: request.headers.get("host"),
  });
  return Response.json(result, {
    status: result.state === "disabled" ? 403 : result.state === "missing" || result.state === "invalid" ? 503 : 200,
    headers: {
      "Cache-Control": "no-store, max-age=0", "X-Control-Center-Authority": "none",
      "X-Control-Center-Source": "local-observation-summary", "X-Content-Type-Options": "nosniff",
    },
  });
}
