// Node-only credential boundary. Never import into a Client Component.
import { clearTimeout, setTimeout } from "node:timers";
import { isLoopbackHost, strictJson } from "./observation-view.ts";

export const serviceMaxBytes = 128 * 1024;
export const serviceTimeoutMs = 5000;
const serviceEndpoint = "http://127.0.0.1:8787";
const statuses = ["queued", "running", "retrieval_complete", "execution_complete", "proposal_ready", "rejected", "failed", "published", "reconciliation_required"] as const;

export interface ServiceJob {
  readonly id: string;
  readonly status: typeof statuses[number];
  readonly created: number;
  readonly updated: number;
  readonly reason: string | null;
}

export interface ServiceUsage {
  readonly day: string;
  readonly model_calls: number;
  readonly reserved_microusd: number;
  readonly source_request_reservations: number;
}

export interface ServiceStatus {
  readonly schema: "research-service-status/v1";
  readonly production_ready: false;
  readonly paused: boolean;
  readonly jobs: readonly ServiceJob[];
  readonly usage: readonly ServiceUsage[];
  readonly last_event: number;
}

export interface ServiceReadResult {
  readonly state: "disabled" | "missing" | "unavailable" | "invalid" | "current";
  readonly reason: string;
  readonly checked_at: string;
  readonly data: ServiceStatus | null;
}

function record(value: unknown, keys: readonly string[]): Record<string, unknown> {
  if (value === null || typeof value !== "object" || Array.isArray(value)) throw new Error("invalid_status");
  const actual = Object.keys(value);
  if (actual.length !== keys.length || actual.some((key) => !keys.includes(key))) throw new Error("invalid_status");
  return value as Record<string, unknown>;
}

function integer(value: unknown): number {
  if (typeof value !== "number" || !Number.isSafeInteger(value) || value < 0) throw new Error("invalid_status");
  return value;
}

function timestamp(value: unknown): number {
  const result = integer(value);
  if (result > 253402300799) throw new Error("invalid_timestamp");
  return result;
}

export function parseServiceStatus(text: string): ServiceStatus {
  if (Buffer.byteLength(text, "utf8") > serviceMaxBytes) throw new Error("status_too_large");
  const root = record(strictJson(text), ["schema", "production_ready", "paused", "jobs", "usage", "last_event"]);
  if (root.schema !== "research-service-status/v1" || root.production_ready !== false || typeof root.paused !== "boolean") throw new Error("invalid_status");
  if (!Array.isArray(root.jobs) || root.jobs.length > 100 || !Array.isArray(root.usage) || root.usage.length > 7) throw new Error("invalid_status");
  const jobs = root.jobs.map((value): ServiceJob => {
    const job = record(value, ["id", "status", "created", "updated", "reason"]);
    if (typeof job.id !== "string" || !/^[A-Za-z0-9][A-Za-z0-9:._-]{0,199}$/.test(job.id)) throw new Error("invalid_job");
    if (typeof job.status !== "string" || !statuses.includes(job.status as ServiceJob["status"])) throw new Error("invalid_job");
    if (job.reason !== null && (typeof job.reason !== "string" || !/^[A-Z][A-Z0-9_]{0,99}$/.test(job.reason))) throw new Error("invalid_job");
    const created = timestamp(job.created), updated = timestamp(job.updated);
    if (updated < created) throw new Error("invalid_job_time");
    return { id: job.id, status: job.status as ServiceJob["status"], created, updated, reason: job.reason as string | null };
  });
  const usage = root.usage.map((value): ServiceUsage => {
    const row = record(value, ["day", "model_calls", "reserved_microusd", "source_request_reservations"]);
    if (typeof row.day !== "string" || !/^\d{4}-\d{2}-\d{2}$/.test(row.day)
      || !Number.isFinite(Date.parse(row.day)) || new Date(row.day).toISOString().slice(0, 10) !== row.day) throw new Error("invalid_usage_day");
    return { day: row.day, model_calls: integer(row.model_calls), reserved_microusd: integer(row.reserved_microusd),
      source_request_reservations: integer(row.source_request_reservations) };
  });
  if (new Set(jobs.map((job) => job.id)).size !== jobs.length || new Set(usage.map((row) => row.day)).size !== usage.length) throw new Error("duplicate_status_row");
  return { schema: "research-service-status/v1", production_ready: false, paused: root.paused,
    jobs, usage, last_event: integer(root.last_event) };
}

export async function readServiceStatus({
  environment = process.env, requestHost, fetcher = fetch, now = Date.now(),
}: {
  readonly environment?: Readonly<Record<string, string | undefined>>;
  readonly requestHost: string | null;
  readonly fetcher?: typeof fetch;
  readonly now?: number;
}): Promise<ServiceReadResult> {
  const checked_at = new Date(now).toISOString();
  const unavailable = (state: Exclude<ServiceReadResult["state"], "current">, reason: string): ServiceReadResult => ({ state, reason, checked_at, data: null });
  if (environment.RESEARCH_SERVICE_ENABLED !== "1") return unavailable("disabled", "service_not_enabled");
  if (environment.HOSTNAME !== "127.0.0.1" || !isLoopbackHost(requestHost)) return unavailable("disabled", "loopback_required");
  if (!environment.RESEARCH_SERVICE_URL || !environment.RESEARCH_OPERATOR_TOKEN) return unavailable("missing", "service_not_configured");
  if (environment.RESEARCH_SERVICE_URL !== serviceEndpoint) return unavailable("invalid", "service_endpoint_not_allowed");
  const token = environment.RESEARCH_OPERATOR_TOKEN;
  if (!/^[A-Za-z0-9_-]{32,256}$/.test(token)) return unavailable("invalid", "operator_credential_invalid");
  const controller = new AbortController();
  let expired = false;
  const deadline = setTimeout(() => { expired = true; controller.abort(); }, serviceTimeoutMs);
  let reader: ReadableStreamDefaultReader<Uint8Array> | undefined;
  try {
    const response = await fetcher(serviceEndpoint + "/v1/status", {
      method: "GET", headers: { Authorization: `Bearer ${token}`, Accept: "application/json", "Cache-Control": "no-cache" },
      redirect: "error", cache: "no-store", signal: controller.signal,
    });
    if (response.status !== 200 || response.redirected) {
      await response.body?.cancel();
      return unavailable("unavailable", "service_request_rejected");
    }
    if (response.headers.get("content-type")?.split(";", 1)[0].trim().toLowerCase() !== "application/json"
      || (response.headers.get("content-encoding") ?? "identity") !== "identity" || response.body === null) {
      await response.body?.cancel();
      return unavailable("invalid", "service_response_invalid");
    }
    const contentLength = response.headers.get("content-length");
    if (contentLength !== null && (!/^\d{1,10}$/.test(contentLength) || Number(contentLength) > serviceMaxBytes)) {
      await response.body.cancel();
      return unavailable("invalid", "service_response_too_large");
    }
    reader = response.body.getReader();
    const chunks: Uint8Array[] = [];
    let size = 0;
    while (true) {
      const { done, value } = await reader.read();
      if (expired) throw new Error("expired");
      if (done) break;
      size += value.byteLength;
      if (size > serviceMaxBytes) return unavailable("invalid", "service_response_too_large");
      chunks.push(value);
    }
    if (contentLength !== null && Number(contentLength) !== size) return unavailable("invalid", "service_response_truncated");
    const bytes = Buffer.concat(chunks, size);
    const text = new TextDecoder("utf-8", { fatal: true }).decode(bytes);
    // A reflected credential is never rendered, even if a compromised service
    // inserts it into otherwise valid status fields.
    if (text.includes(token)) return unavailable("invalid", "service_response_invalid");
    const data = parseServiceStatus(text);
    if (JSON.stringify(data).includes(token)) return unavailable("invalid", "service_response_invalid");
    return { state: "current", reason: "service_status_read", checked_at, data };
  } catch {
    return unavailable(expired ? "unavailable" : "invalid", expired ? "service_timeout" : "service_read_failed");
  } finally {
    clearTimeout(deadline);
    controller.abort();
    if (reader !== undefined) {
      try { await reader.cancel(); } catch { /* Cancellation has no user-visible details. */ }
      reader.releaseLock();
    }
  }
}
